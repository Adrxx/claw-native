import Foundation
import CoreGraphics

// Original camera/input bodies over pinned native token spans. WWD-to-runtime
// decompression/resources and physical key delivery remain explicit adapters.
final class ClawNativeCamera {
    static let viewport = CGSize(width: 640, height: 480)
    let globals = UnsafeMutablePointer<ClawSceneCameraGlobals>.allocate(capacity: 1)
    private let faultStorage = UnsafeMutablePointer<UInt32>.allocate(capacity: 1)
    let heap: ClawTokenHeap
    let sceneHost: ClawSceneActorHost
    private let resources: ClawActorResources
    private(set) var nativeWorld: ClawNativeWorld?
    private let gridSetup: (UInt32, UInt32, UInt32) -> UInt32
    private(set) var planeAdapterCalls: Set<UInt32> = []
    private(set) var loaderFailure: String?
    let inputToken: UInt32, deviceToken: UInt32
    private(set) var planeTokens: [UInt32] = []
    private var mainIndex = 0
    private var physicalHeld: UInt32 = 0, lowLatch: UInt32 = 0
    private(set) var platformCalls: UInt64 = 0
    private(set) var unknownPlatformSlots: Set<UInt32> = []
    private(set) var postedCommands: [UInt32] = []
    var fault: UInt32 { faultStorage.pointee }
    var held: UInt32 { heap.lookup(inputToken, words: 29)![2] }
    var pressed: UInt32 { heap.lookup(inputToken, words: 29)![1] }

    // MARK: - Snapshot persistence

    struct SavedState: Codable, Equatable {
        let globals: ClawSnapshotValue<ClawSceneCameraGlobals>
        let fault: UInt32, physicalHeld: UInt32, lowLatch: UInt32
        let mainIndex: Int
        let planeTokens: [UInt32]
        let platformCalls: UInt64
        let planeAdapterCalls: Set<UInt32>, unknownPlatformSlots: Set<UInt32>
        let postedCommands: [UInt32]
        let loaderFailure: String?
    }
    func savedState() -> SavedState {
        SavedState(
            globals: ClawSnapshotValue(globals.pointee), fault: fault, physicalHeld: physicalHeld,
            lowLatch: lowLatch, mainIndex: mainIndex, planeTokens: planeTokens, platformCalls: platformCalls,
            planeAdapterCalls: planeAdapterCalls, unknownPlatformSlots: unknownPlatformSlots,
            postedCommands: postedCommands, loaderFailure: loaderFailure)
    }
    func restoreState(_ value: SavedState) throws {
        // Immutable world/resource bindings must be those of this candidate
        // scene. The shared heap and world loader are separate participants.
        guard value.mainIndex == mainIndex, value.planeTokens == planeTokens,
            value.globals.value.inputDeviceToken == deviceToken,
            value.globals.value.inputMappingToken == inputToken
        else { throw ClawSnapshotError.invalidState }
        globals.pointee = value.globals.value
        faultStorage.pointee = value.fault
        physicalHeld = value.physicalHeld
        lowLatch = value.lowLatch
        platformCalls = value.platformCalls
        planeAdapterCalls = value.planeAdapterCalls
        unknownPlatformSlots = value.unknownPlatformSlots
        postedCommands = value.postedCommands
        loaderFailure = value.loaderFailure
    }

    // MARK: - World and input setup

    init(
        heap: ClawTokenHeap, host: ClawSceneActorHost, world: ClawWorld,
        ownerToken: UInt32, worldToken: UInt32, resources: ClawActorResources,
        gridSetup: @escaping (UInt32, UInt32, UInt32) -> UInt32
    ) throws {
        self.heap = heap
        sceneHost = host
        self.resources = resources
        self.gridSetup = gridSetup
        inputToken = heap.allocate(bytes: 0x90)
        deviceToken = heap.allocate(bytes: 146 * 4)
        globals.initialize(to: ClawSceneCameraGlobals())
        faultStorage.initialize(to: 0)
        globals.pointee.playerToken = 0x10002000
        globals.pointee.inputDeviceToken = deviceToken
        globals.pointee.inputMappingToken = inputToken
        globals.pointee.forcedX = .max
        globals.pointee.forcedY = .max
        // 0x4254a0 initializes the actual 77-word application/timing object. The
        // window/configuration and scene links below remain a native profile.
        guard let managerToken = ClawNativeRespawn.constructApplication(heap: heap, host: host) else {
            throw AssetError.invalid("Original application constructor")
        }
        let configToken = heap.allocate(bytes: 56), windowToken = heap.allocate(bytes: 8)
        guard let manager = heap.lookup(managerToken, words: 77), let window = heap.lookup(windowToken, words: 2),
            let owner = heap.lookup(ownerToken, words: 478), let map = heap.lookup(worldToken, words: 25),
            let input = heap.lookup(inputToken, words: 36), let device = heap.lookup(deviceToken, words: 146)
        else {
            throw AssetError.invalid("Camera/input host allocation")
        }
        manager[1] = windowToken
        manager[19] = configToken
        window[1] = 1
        owner[1] = managerToken
        manager[5] = 0  // Explicit no-music-controller platform profile.
        let config = heap.lookup(configToken, words: 14)!
        config[9] = 5000
        config[10] = 2000  // Recovered 0x4222a0 callsite arguments.
        input[0] = deviceToken
        device[0] = .max
        // Observed unavailable-joystick startup profile. The recovered default
        // mapping still polls keyboard keys with device mode 0.
        let keys: [UInt32] = [0x25, 0x27, 0x26, 0x28, 0x20, 0x11, 0x12, 0x10, 0, 0, 0, 0]
        for (index, key) in keys.enumerated() { device[0x1dc / 4 + index] = key }
        _ = entry(0x430d30, receiver: inputToken)
        _ = entry(0x430d80, receiver: inputToken)
        _ = entry(0x4b3430, receiver: deviceToken, argument0: 2)
        _ = entry(0x431300, receiver: inputToken)
        // Source 0x46af09 seeds the shared CRT thread before world loading.
        // Wider retail resource/startup ordering remains separate integration.
        var seedCall = ClawSceneActorCall()
        seedCall.function = 0x4a3040
        seedCall.argumentCount = 1
        seedCall.arguments.0 = UInt32(CLAW_CRT_RANDOM_LEVEL_SEED)
        _ = sceneHost.call?(sceneHost.context, seedCall)
        // Whole source 0x4cb200 consumes the original compressed file, constructs
        // owned descriptions/planes and applies the actual header flags/center.
        let loader = ClawNativeWorld(
            heap: heap, worldToken: worldToken, parentToken: owner[3],
            host: sceneHost,
            populationPolicy:
                "Recovered Rat/Officer/Soldier, pickup, scenery, Elevator/peg, sound/dialog trigger and single-crate callbacks; other records explicitly excluded",
            hooks: .init(
                imageRoot: { [weak self] name in
                    try self?.resources.tileImages(name: name)?.token
                },
                gridSetup: { [weak self] batch in
                    self?.gridSetup(batch.planeToken, batch.firstRecordToken, batch.count)
                },
                service: { [weak self] call in
                    guard let self, let service = self.sceneHost.call else { return nil }
                    return service(self.sceneHost.context, call)
                }))
        nativeWorld = loader
        let compressed = try Data(
            contentsOf: resources.root.appendingPathComponent("LEVEL\(resources.level)/WORLDS/WORLD.WWD"))
        guard loader.construct(), loader.load(compressedWWD: compressed), loader.unresolvedServices.isEmpty,
            let main = loader.mainIndex
        else {
            throw AssetError.invalid(loader.failure ?? "Original compressed world load fault \(loader.fault)")
        }
        planeTokens = loader.planeTokens
        mainIndex = Int(main)
        guard !planeTokens.isEmpty, planeTokens.contains(map[23]) else {
            throw AssetError.invalid("Original main plane missing")
        }

        guard fault == 0 else { throw AssetError.invalid("Camera setup fault \(fault)") }
    }
    deinit {
        globals.deinitialize(count: 1)
        globals.deallocate()
        faultStorage.deinitialize(count: 1)
        faultStorage.deallocate()
    }
    // MARK: - Synchronous camera dispatch

    var runtimeHost: ClawSceneCameraHost { host }
    private var host: ClawSceneCameraHost {
        ClawSceneCameraHost(
            heap: sceneHost, platformContext: Unmanaged.passUnretained(self).toOpaque(),
            platform: { context, call in
                guard let context else { return 0 }
                return Unmanaged<ClawNativeCamera>.fromOpaque(context).takeUnretainedValue().platform(call)
            })
    }
    func setInput(held: UInt32, pressed: UInt32) {
        physicalHeld = held
        lowLatch |= pressed
    }
    // Stage and animation clocks come from the scene; this adapter does not
    // substitute wall time for either clock.
    func synchronize(stageDelta: UInt32, animationNow: UInt32, animationDelta: UInt32) {
        globals.pointee.stageDelta = stageDelta
        globals.pointee.animationNow = animationNow
        globals.pointee.animationDelta = animationDelta
    }
    @discardableResult func entry(_ function: UInt32, receiver: UInt32, argument0: UInt32 = 0, argument1: UInt32 = 0)
        -> UInt32
    {
        if let deadline = heap.lookup(0x53c260, words: 1) { globals.pointee.shakeUntil = deadline.pointee }
        var result: UInt32 = 0
        if claw_scene_camera_entry(function, receiver, argument0, argument1, globals, host, faultStorage, &result) == 0
        {
            faultStorage.pointee = 1
        }
        heap.lookup(0x53c260, words: 1)?.pointee = globals.pointee.shakeUntil
        return result
    }
    func projections() -> [Int: ClawSpriteProjection] {
        var result: [Int: ClawSpriteProjection] = [:]
        for (index, token) in planeTokens.enumerated() {
            var projection = ClawSpriteProjection()
            if claw_scene_camera_projection(token, sceneHost, &projection, faultStorage) == 1 {
                result[index] = projection
            }
        }
        return result
    }
    var mainProjection: ClawSpriteProjection? { projections()[mainIndex] }
    // MARK: - Physical key and window services

    private func platform(_ call: ClawSceneCameraPlatformCall) -> UInt32 {
        platformCalls &+= 1
        switch call.importSlot {
        case 0x546ce4:
            // Native lab controls map semantic actions onto the original
            // virtual-key profile: Space jump, Control attack, arrow movement.
            let keyMasks: [UInt32: UInt32] = [
                0x25: 0x01000000, 0x27: 0x02000000, 0x26: 0x04000000, 0x28: 0x08000000,
                0x20: 1, 0x11: 2, 0x12: 4, 0x10: 8, 0x5a: 0x20, 0x31: 0x40, 0x32: 0x80, 0x33: 0x100, 0x34: 0x200
            ]
            guard let mask = keyMasks[call.arguments.0] else { return 0 }
            let value: UInt32 = (physicalHeld & mask == 0 ? 0 : 0x8000) | (lowLatch & mask == 0 ? 0 : 1)
            lowLatch &= ~mask
            return value
        case 0x546d50:
            if call.arguments.1 == 0x111 { postedCommands.append(call.arguments.2) }
            return 1
        default:
            unknownPlatformSlots.insert(call.importSlot)
            faultStorage.pointee = 1
            return 0
        }
    }
}

extension ClawSceneCameraGlobals: ClawSnapshotNativeValue {}
