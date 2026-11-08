import Foundation

// Source-owned MultiStats hierarchy. Native resource dictionaries, allocation
// and physical graphics/audio are transports; HUD values/digits/lives remain
// in the frozen source callbacks and their actual child-list order.
final class ClawNativeHUD {
    unowned let scene: ClawNativeScene
    private let sharedGlobals = UnsafeMutablePointer<ClawCheckpointTimerGlobals>.allocate(capacity: 1)
    private let hudGlobals = UnsafeMutablePointer<ClawPlayerHUDGlobals>.allocate(capacity: 1)
    private let shared = UnsafeMutablePointer<ClawCheckpointTimerContext>.allocate(capacity: 1)
    private let context = UnsafeMutablePointer<ClawPlayerHUDContext>.allocate(capacity: 1)
    // Original 53c9f8 is shared by the timer callback and BossStager contact.
    var timerRemaining: UInt32 {
        get { sharedGlobals.pointee.remaining }
        set { sharedGlobals.pointee.remaining = newValue }
    }
    private(set) var token: UInt32 = 0
    private(set) var fault: UInt32 = 0
    private(set) var unresolved: Set<UInt32> = []
    private(set) var callbacks: [UInt32: UInt64] = [:]
    static let frames: Set<UInt32> = [0x4908b0, 0x490f80, 0x490c50, 0x4912a0, 0x491540]
    static let controllers: Set<UInt32> = [
        0x491ed0, 0x4919f0, 0x491b30, 0x490760, 0x490590, 0x490c40, 0x490c00, 0x40db30, 0x40db50, 0x4d3ef0, 0x4d3f20,
        0x4c9fc0, 0x4c9fe0, 0x4d3eb0, 0x4f5172, 0x4d3e50, 0x4d3ca0, 0x4c8f60, 0x4c8e00
    ]
    static let services = frames.union(controllers)
    // MARK: - HUD context lifetime

    init(scene: ClawNativeScene) {
        self.scene = scene
        let manager = scene.heap.lookup(scene.ownerIdentity, words: 2)![1]
        sharedGlobals.initialize(
            to: ClawCheckpointTimerGlobals(
                managerToken: manager, playerToken: 0x10002000,
                stageDelta: 0, animationDelta: 0, remaining: 0, initialDuration: 0, expired: 0, multiStatsToken: 0,
                left: 0, top: 0, right: 640, bottom: 480, audioPosition: scene.player.audio?.routing.masterVolume ?? 0))
        hudGlobals.initialize(
            to: ClawPlayerHUDGlobals(
                initialScore: scene.player.runtime.actor.62,
                initialHealth: scene.player.runtime.actor.67, powerupRemaining: 0, audioEnabled: 1))
        shared.initialize(
            to: ClawCheckpointTimerContext(
                scene: host, globals: sharedGlobals,
                composeAnimation: 1, composeImages: 1, composeHierarchy: 1, composeFormatting: 1, fault: 0))
        context.initialize(
            to: ClawPlayerHUDContext(
                scene: host, shared: shared, globals: hudGlobals,
                composeAnimation: 1, composeImages: 1, composeFormatting: 1, composeControllers: 1, fault: 0))
    }
    deinit {
        // Scene owns live graph teardown; deinit does not dereference its
        // unowned scene after the scene's own storage has begun destruction.
        context.deinitialize(count: 1)
        context.deallocate()
        shared.deinitialize(count: 1)
        shared.deallocate()
        sharedGlobals.deinitialize(count: 1)
        sharedGlobals.deallocate()
        hudGlobals.deinitialize(count: 1)
        hudGlobals.deallocate()
    }
    // MARK: - Borrowed scene services

    // These callbacks borrow the HUD for synchronous recovered calls. The
    // scene owns both the HUD graph and the heap spans returned by lookup.
    private var host: ClawSceneActorHost {
        ClawSceneActorHost(
            context: Unmanaged.passUnretained(self).toOpaque(),
            lookup: { u, t, n in
                guard let u else { return nil }
                return Unmanaged<ClawNativeHUD>.fromOpaque(u).takeUnretainedValue().scene.heap.lookup(t, words: n)
            },
            allocate: { u, n in
                guard let u else { return 0 }
                return Unmanaged<ClawNativeHUD>.fromOpaque(u).takeUnretainedValue().allocate(n)
            },
            free: { u, t in
                guard let u else { return }
                Unmanaged<ClawNativeHUD>.fromOpaque(u).takeUnretainedValue().scene.heap.free(t)
            },
            call: { u, e in
                guard let u else { return 0 }
                let h = Unmanaged<ClawNativeHUD>.fromOpaque(u).takeUnretainedValue()
                let args = withUnsafeBytes(of: e.arguments) {
                    Array($0.bindMemory(to: UInt32.self).prefix(Int(e.argumentCount)))
                }
                return h.dependency(e.function, receiver: e.receiver, args: args, name: nil)
            },
            readClock: { u in
                guard let u else { return 0 }
                let scene = Unmanaged<ClawNativeHUD>.fromOpaque(u).takeUnretainedValue().scene
                return scene.actorHost.readClock?(scene.actorHost.context) ?? 0
            })
    }
    private func allocate(_ bytes: UInt32) -> UInt32 {
        // Portable snapshots read 128 actor words; the original allocations
        // remain 0x1b4/0x1d0 bytes and only their padding is a native host extension.
        scene.heap.allocate(bytes: bytes == 0x1b4 || bytes == 0x1d0 ? 512 : bytes)
    }
    // MARK: - Source hierarchy and frame dispatch

    @discardableResult func create() -> Bool {
        guard token == 0 else { return false }
        token = entry(0x4c8f60, receiver: scene.containerToken, args: [0, 0, 0, 9999, 0x52297c, 0x200000])
        return token != 0 && fault == 0 && sharedGlobals.pointee.multiStatsToken == token
    }
    @discardableResult func entry(_ function: UInt32, receiver: UInt32 = 0, args: [UInt32]) -> UInt32 {
        sharedGlobals.pointee.stageDelta = scene.stageDelta
        sharedGlobals.pointee.animationDelta = scene.animationDelta
        hudGlobals.pointee.powerupRemaining = scene.playerPowerupGlobals?.pointee.remaining ?? 0
        var result: UInt32 = 0
        let accepted = args.withUnsafeBufferPointer { values -> UInt32 in
            if Self.frames.contains(function) {
                if claw_v13_lives_boss_enabled() == 0 {
                    return claw_player_hud_entry(
                        function, receiver, values.baseAddress, UInt32(args.count), context, nativeHUDDependency,
                        Unmanaged.passUnretained(self).toOpaque(), &result)
                }
                return claw_v13_player_hud_entry(
                    function, receiver, values.baseAddress, UInt32(args.count), context, nativeHUDDependency,
                    Unmanaged.passUnretained(self).toOpaque(), &result)
            }
            return claw_checkpoint_timer_entry(
                function, receiver, values.baseAddress, UInt32(args.count), shared, nativeHUDControllerDependency,
                Unmanaged.passUnretained(self).toOpaque(), &result)
        }
        callbacks[function, default: 0] &+= 1
        fault = max(fault, max(context.pointee.fault, shared.pointee.fault))
        if accepted != 1 {
            unresolved.insert(function)
            fault = max(fault, 1)
        }
        return result
    }
    var children: [UInt32] {
        guard token != 0 else { return [] }
        var node = scene.heap.lookup(token + 0x1b8, words: 1)?.pointee ?? 0, values: [UInt32] = []
        while node != 0, let p = scene.heap.lookup(node, words: 3) {
            values.append(p[2])
            node = p[0]
        }
        return values
    }
    // MARK: - Resource, image and audio services

    fileprivate func dependency(_ function: UInt32, receiver: UInt32, args: [UInt32], name: String?) -> UInt32 {
        if Self.services.contains(function) { return entry(function, receiver: receiver, args: args) }
        switch function {
        case 0x4f63ec: return allocate(args[0])
        case 0x4f6428:
            scene.heap.free(args[0])
            return 0
        case 0x4f6286:
            guard let name = name ?? clawOriginalResourceNames[args[0]] ?? Self.logicNames[args[0]] else {
                fault = 1
                unresolved.insert(function)
                return 0
            }
            do {
                if name.withCString({ claw_logic_registry_find($0) }) != nil { return scene.entry(named: name) }
                if receiver == 0x63000010 { return try scene.objectResources?.sequence(name: name)?.token ?? 0 }
                if let image = try scene.objectResources?.images(name: name) { return image.token }
                return scene.player.audio?.resolve(name: name)?.resourceToken ?? 0
            } catch {
                fault = 1
                return 0
            }
        case 0x4c7970, 0x4c7900:
            guard let name = name ?? clawOriginalResourceNames[args[0]], var snapshot = scene.snapshotActor(receiver)
            else {
                fault = 1
                return 0
            }
            do {
                var bindings = ClawActorResourceBindings()
                bindings.actor = snapshot.actor
                var binding = ClawActorBindingContext()
                binding.image = try scene.objectResources?.images(name: name)?.binding() ?? ClawActorImageBinding()
                let ok = name.withCString { s -> UInt32 in
                    if function == 0x4c7900 {
                        return claw_actor_bind_indexed_image(
                            &bindings, &binding, s, Int32(bitPattern: args[1]),
                            { _, c, _, _ in c?.pointee.image.token ?? 0 }, nil)
                    }
                    return claw_actor_bind_default_image(
                        &bindings, &binding, s, { _, c, _, _ in c?.pointee.image.token ?? 0 }, nil)
                }
                if ok != 1 { fault = 1 }
                snapshot.actor = bindings.actor
                scene.write(snapshot)
                return ok
            } catch {
                fault = 1
                return 0
            }
        case 0x4c79e0:
            guard let name = name ?? clawOriginalResourceNames[args[0]] else {
                fault = 1
                return 0
            }
            return scene.namedAnimation(function: function, actor: receiver, name: name, eager: args[1])
        case 0x4c82a0:
            return scene.actorAnimation(function: function, receiver: receiver, argument0: args[0], argument1: 0)
        case 0x4c9e00:
            guard args.count == 1, let rendering = scene.rendering else {
                fault = 1
                return 0
            }
            var rawFault: UInt32 = 0
            let graphics = ClawPlaneRendererHost(scene: host, graphicsContext: nil, graphics: nil)
            _ = claw_plane_renderer_actor(receiver, args[0], graphics, &rawFault)
            fault = max(fault, rawFault)
            if rendering.fault != 0 { fault = rendering.fault }
            return 0
        case 0x4d2890: return scene.rendering?.drawActor(args[0], image: receiver, target: args[1]) ?? 0
        case 0x4b45f0:
            return scene.player.audio?.playVoicePool(
                receiver,
                request: ClawAudioRequest(volume: args[0], pan: args[1], pitchPercent: args[2], looping: args[3])) ?? 0
        default:
            guard args.count <= 4 else {
                unresolved.insert(function)
                fault = 1
                return 0
            }
            var e = ClawSceneActorCall(
                function: function, receiver: receiver, arguments: (0, 0, 0, 0), argumentCount: UInt32(args.count))
            withUnsafeMutableBytes(of: &e.arguments) { raw in args.withUnsafeBytes { raw.copyMemory(from: $0) } }
            return scene.performService(e)
        }
    }
    private static let logicNames: [UInt32: String] = [
        0x52297c: "MultiStats", 0x522994: "StatusNumberDigit", 0x5229d8: "ScoreFrame", 0x5229cc: "WeaponFrame",
        0x5229c0: "HealthFrame", 0x5229b4: "LivesFrame", 0x5229a8: "TimerFrame"
    ]
}
private let nativeHUDDependency: ClawPlayerHUDDependency = { _, e, u in
    guard let e, let u else { return 0 }
    let h = Unmanaged<ClawNativeHUD>.fromOpaque(u).takeUnretainedValue()
    let args = withUnsafeBytes(of: e.pointee.arguments) {
        Array($0.bindMemory(to: UInt32.self).prefix(Int(e.pointee.argumentCount)))
    }
    return h.dependency(
        e.pointee.function, receiver: e.pointee.receiver, args: args, name: e.pointee.name.map { String(cString: $0) })
}
private let nativeHUDControllerDependency: ClawCheckpointTimerDependency = { _, e, u in
    guard let e, let u else { return 0 }
    let h = Unmanaged<ClawNativeHUD>.fromOpaque(u).takeUnretainedValue()
    let args = withUnsafeBytes(of: e.pointee.arguments) {
        Array($0.bindMemory(to: UInt32.self).prefix(Int(e.pointee.argumentCount)))
    }
    return h.dependency(
        e.pointee.function, receiver: e.pointee.receiver, args: args, name: e.pointee.name.map { String(cString: $0) })
}

extension ClawNativeHUD {
    // MARK: - Snapshot persistence

    struct SavedState: Codable, Equatable {
        let token: UInt32, fault: UInt32, unresolved: Set<UInt32>, callbacks: [UInt32: UInt64]
        let shared: ClawSnapshotValue<ClawCheckpointTimerGlobals>, hud: ClawSnapshotValue<ClawPlayerHUDGlobals>
        let context: [String: Data], sharedContext: [String: Data]
    }
    func savedState() -> SavedState {
        .init(
            token: token, fault: fault, unresolved: unresolved, callbacks: callbacks,
            shared: ClawSnapshotValue(sharedGlobals.pointee), hud: ClawSnapshotValue(hudGlobals.pointee),
            context: Self.contextFields.capture(context.pointee),
            sharedContext: Self.sharedFields.capture(shared.pointee))
    }
    func restoreState(_ saved: SavedState) throws {
        guard saved.token == token else { throw ClawSnapshotError.invalidState }
        let restoredContext = try Self.contextFields.restoring(saved.context, into: context.pointee)
        let restoredShared = try Self.sharedFields.restoring(saved.sharedContext, into: shared.pointee)
        fault = saved.fault
        unresolved = saved.unresolved
        callbacks = saved.callbacks
        sharedGlobals.pointee = saved.shared.value
        hudGlobals.pointee = saved.hud.value
        context.pointee = restoredContext
        shared.pointee = restoredShared
    }
    private static let contextFields = ClawSnapshotFields<ClawPlayerHUDContext>(fields: [
        .init("composeAnimation", \.composeAnimation), .init("composeImages", \.composeImages),
        .init("composeFormatting", \.composeFormatting), .init("composeControllers", \.composeControllers),
        .init("fault", \.fault)
    ])
    private static let sharedFields = ClawSnapshotFields<ClawCheckpointTimerContext>(fields: [
        .init("composeAnimation", \.composeAnimation), .init("composeImages", \.composeImages),
        .init("composeHierarchy", \.composeHierarchy),
        .init("composeFormatting", \.composeFormatting), .init("fault", \.fault)
    ])
}
extension ClawCheckpointTimerGlobals: ClawSnapshotNativeValue {}
extension ClawPlayerHUDGlobals: ClawSnapshotNativeValue {}
