import Foundation

// Complete recovered singleplayer entry 0x46ac30 over native scene storage. Window
// presentation, audio bounds and DD flush are named native platform adapters.
// The retail startup/manager clock profile is a separate recovery boundary.
final class ClawNativeFrame {
    static let presentFunction: UInt32 = 0x70000001
    unowned let scene: ClawNativeScene
    private let owner: UInt32
    private var context = ClawGameFrameContext()
    private let serviceGlobals = UnsafeMutablePointer<ClawGameFrameServiceGlobals>.allocate(capacity: 1)
    private(set) var frameCount: UInt64 = 0, presentationCount: UInt64 = 0
    private(set) var events: [UInt32] = []
    private(set) var fault: UInt32 = 0

    // MARK: - Snapshot state

    struct SavedState: Codable, Equatable {
        let services: ClawSnapshotValue<ClawGameFrameServiceGlobals>
        let frameCount: UInt64, presentationCount: UInt64
        let events: [UInt32]
        let fault: UInt32, contextFault: UInt32
        let composeStage: UInt32, composeCamera: UInt32, composeSpatial: UInt32
    }
    func savedState() -> SavedState {
        SavedState(
            services: ClawSnapshotValue(serviceGlobals.pointee), frameCount: frameCount,
            presentationCount: presentationCount, events: events, fault: fault, contextFault: context.fault,
            composeStage: context.composeStage, composeCamera: context.composeCamera, composeSpatial: context.composeSpatial)
    }
    func restoreState(_ value: SavedState) {
        // All context pointers continue to name the new candidate scene's own
        // stable buffers. No host address is loaded from the archive.
        serviceGlobals.pointee = value.services.value
        frameCount = value.frameCount
        presentationCount = value.presentationCount
        events = value.events
        fault = value.fault
        context.fault = value.contextFault
        context.composeStage = value.composeStage
        context.composeCamera = value.composeCamera
        context.composeSpatial = value.composeSpatial
    }

    // MARK: - Frame storage and recovered scene construction

    init(
        scene: ClawNativeScene, owner: UInt32, parent: UInt32,
        stage: UnsafeMutablePointer<ClawSceneStageState>, actors: UnsafeMutablePointer<ClawSceneActorGlobals>
    ) {
        self.scene = scene
        self.owner = owner
        serviceGlobals.initialize(to: ClawGameFrameServiceGlobals())
        serviceGlobals.pointee.playerToken = stage.pointee.playerToken
        serviceGlobals.pointee.lastPose = (0x80000000, 0x80000000, 0x80000000, 0x80000000)
        serviceGlobals.pointee.rankingTimer = 500
        serviceGlobals.pointee.audioEnabled = 1
        serviceGlobals.pointee.overallVolume = 100
        serviceGlobals.pointee.overlayRect = (0, 0, 640, 480)  // Current native 640 x 480 source viewport profile.
        context.host = scene.camera!.runtimeHost
        context.stage = stage
        context.actors = actors
        context.camera = scene.camera!.globals
        context.composeStage = 1
        context.composeCamera = 0
        context.composeSpatial = 0
        let heap = scene.heap, ownerWords = heap.lookup(owner, words: 478)!
        let parentLink = ownerWords[3], managerLink = ownerWords[1]
        var startupGlobals = ClawSinglePlayerSceneGlobals()
        let constructed = withUnsafeMutablePointer(to: &startupGlobals) { pointer -> UInt32 in
            var startup = ClawSinglePlayerSceneContext()
            startup.host = scene.actorHost
            startup.globals = pointer
            return claw_single_player_scene_construct(owner, &startup, nil, nil)
        }
        precondition(constructed == owner)
        ownerWords[1] = managerLink
        ownerWords[3] = parentLink
        ownerWords[0x44 / 4] = .max
        ownerWords[0x48 / 4] = .max
        let manager = heap.lookup(ownerWords[1], words: 45)!
        manager[11] = owner
        manager[23] = heap.allocate(bytes: 8)
        let rendererToken = heap.allocate(bytes: 4), tableToken = heap.allocate(bytes: 56)
        heap.lookup(rendererToken, words: 1)![0] = tableToken
        heap.lookup(tableToken, words: 14)![13] = Self.presentFunction
        let parentWords = heap.lookup(parent, words: 12)!
        parentWords[3] = rendererToken  // Physical presentation; source holder is initialized by the PAL/display host.
    }
    deinit {
        serviceGlobals.deinitialize(count: 1)
        serviceGlobals.deallocate()
    }

    // MARK: - Recovered frame scheduling

    func advance() -> UInt32 {
        events.removeAll(keepingCapacity: true)
        scene.statusMessages?.beginFrame()
        fault = 0
        context.fault = 0
        serviceGlobals.pointee.stageDelta = context.stage!.pointee.stage.deltaMilliseconds
        serviceGlobals.pointee.accumulatedTick = context.stage!.pointee.accumulatedMilliseconds
        var result: UInt32 = 0
        let completed = scene.heap.withStableFreedStorage {
            claw_game_frame_entry(0x46ac30, owner, &context, nil, nil, &result)
        }
        fault = max(fault, max(context.fault, scene.fault))
        if completed == 0 || result == 0 { fault = max(fault, 1) }
        frameCount &+= 1
        return fault == 0 ? 1 : 0
    }
    func record(_ function: UInt32) { events.append(function) }

    // MARK: - Presentation, audio and frame service dispatch

    func platform(_ call: ClawSceneActorCall) -> UInt32? {
        switch call.function {
        case 0x4025c0:
            if let ambient = scene.ambientAudio {
                let result = ambient.frame(call.receiver, x: call.arguments.0, y: call.arguments.1)
                fault = max(fault, ambient.fault)
                record(call.function)
                return result
            }
            guard let bounds = scene.heap.lookup(call.receiver, words: 2) else {
                fault = 1
                return 0
            }
            bounds[0] = call.arguments.0
            bounds[1] = call.arguments.1
            record(call.function)
            return 0
        case Self.presentFunction:
            record(call.function)
            presentationCount &+= 1
            return 1
        case 0x46c2c0, 0x4224f0, 0x40af90:
            record(call.function)
            // A save/contact can reset the live clocks during actor scanning.
            serviceGlobals.pointee.stageDelta = scene.stageDelta
            serviceGlobals.pointee.accumulatedTick = scene.gameTime
            var services = ClawGameFrameServiceContext(host: scene.actorHost, globals: serviceGlobals, composeMessages: 1, fault: 0)
            var result: UInt32 = 0
            _ = claw_game_frame_service_entry(
                call.function, call.receiver, call.arguments.0, &services, nativeFrameServicesDependency,
                Unmanaged.passUnretained(self).toOpaque(), &result)
            if services.fault != 0 { fault = services.fault }
            return result
        case 0x4b98b0:
            record(call.function)
            return 1
        default: return nil
        }
    }
    fileprivate func service(_ call: ClawGameFrameServiceCall) -> UInt32 {
        if let messages = scene.statusMessages, let result = messages.frameService(call) {
            fault = max(fault, messages.fault)
            return result
        }
        guard call.localMask == 0, call.bufferCount == 0, call.argumentCount <= 4 else {
            fault = 3
            return 0
        }
        // This legacy envelope has no local buffers. Reject those above
        // rather than silently dropping them while narrowing the call.
        var plain = ClawSceneActorCall()
        plain.function = call.function
        plain.receiver = call.receiver
        plain.argumentCount = call.argumentCount
        plain.arguments = (call.arguments.0, call.arguments.1, call.arguments.2, call.arguments.3)
        return scene.actorHost.call?(scene.actorHost.context, plain) ?? 0
    }
}

extension ClawGameFrameServiceGlobals: ClawSnapshotNativeValue {}
private let nativeFrameServicesDependency: ClawGameFrameServiceDependency = { context, event, user in
    guard let context, let user else { return 0 }
    let owner = Unmanaged<ClawNativeFrame>.fromOpaque(user).takeUnretainedValue()
    let result = owner.service(event)
    if owner.fault != 0 { context.pointee.fault = owner.fault }
    return result
}
