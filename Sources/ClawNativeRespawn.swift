import Foundation

// Native binding for original application 0x426e30 and respawn 0x46be40. The
// recovered C bodies own all state gates, cleanup, frame order and clock stores.
final class ClawNativeRespawn {
    // MARK: - Native services and owned state

    struct Hooks {
        // Dispatch the live primary callback, including source state 23; import
        // the actor/primary/private heap before it and export all three after it.
        var playerPrimary: (UInt32) -> Bool
        // Actual 0x4c8fc0 scheduling, not ordinary 0x46ac30 or a fresh level load.
        var actorFrame: (UInt32, UInt32) -> Bool
        // Finite original-address service routing. nil means unavailable and
        // produces fault 4; zero is a legitimate original service return.
        var service: (ClawSceneActorCall) -> UInt32?
        // Capture/publish the same clock aliases used by ordinary root frames.
        var captureTiming: (inout ClawPlayerDeathCommandGlobals) -> Void
        var publishTiming: (ClawPlayerDeathCommandGlobals) -> Void
        // reset writes private+120 after rendering; import it without rewriting
        // that heap from a stale Swift player cache.
        var importPlayer: () -> Void
        var observe: (ClawSceneActorCall) -> Void = { _ in }
    }
    let heap: ClawTokenHeap
    let applicationToken: UInt32
    private let backing: ClawSceneActorHost
    private var hooks: Hooks
    private let globals: UnsafeMutablePointer<ClawPlayerDeathCommandGlobals>
    private let faultStorage = UnsafeMutablePointer<UInt32>.allocate(capacity: 1)
    private(set) var events: [ClawSceneActorCall] = []
    private(set) var unresolvedServices: Set<UInt32> = []
    private(set) var consumedCommands: [UInt32] = []
    var fault: UInt32 { faultStorage.pointee }
    var timing: ClawPlayerDeathCommandGlobals { globals.pointee }
    private var serviceFault: UInt32 = 0
    private var executing = false
    private var iterators: [UInt32: UnsafeMutablePointer<UInt32>] = [:]

    // MARK: - Snapshot persistence (property names are saved keys)

    struct SavedState: Codable, Equatable {
        let application: UInt32
        let timing: ClawSnapshotValue<ClawPlayerDeathCommandGlobals>
        let events: [ClawSnapshotValue<ClawSceneActorCall>]
        let unresolvedServices: Set<UInt32>, consumedCommands: [UInt32]
        let fault: UInt32, serviceFault: UInt32
    }
    func savedState() throws -> SavedState {
        guard !executing, iterators.isEmpty else { throw ClawSnapshotError.activeFrame }
        return .init(
            application: applicationToken, timing: ClawSnapshotValue(globals.pointee),
            events: events.map(ClawSnapshotValue.init), unresolvedServices: unresolvedServices,
            consumedCommands: consumedCommands, fault: fault, serviceFault: serviceFault)
    }
    func restoreState(_ saved: SavedState) throws {
        guard !executing, iterators.isEmpty else { throw ClawSnapshotError.activeFrame }
        guard saved.application == applicationToken else { throw ClawSnapshotError.invalidState }
        globals.pointee = saved.timing.value
        events = saved.events.map(\.value)
        unresolvedServices = saved.unresolvedServices
        consumedCommands = saved.consumedCommands
        faultStorage.pointee = saved.fault
        serviceFault = saved.serviceFault
    }

    // MARK: - Lifecycle

    init(
        heap: ClawTokenHeap, applicationToken: UInt32,
        globals: ClawPlayerDeathCommandGlobals, host: ClawSceneActorHost, hooks: Hooks
    ) {
        self.heap = heap
        self.applicationToken = applicationToken
        backing = host
        self.hooks = hooks
        self.globals = .allocate(capacity: 1)
        self.globals.initialize(to: globals)
        faultStorage.initialize(to: 0)
    }
    deinit {
        globals.deinitialize(count: 1)
        globals.deallocate()
        faultStorage.deinitialize(count: 1)
        faultStorage.deallocate()
    }

    // MARK: - Dequeued death and respawn commands

    // Caller transfers a dequeued batch, outside the damage/scanner callback.
    // Unknown commands remain in the returned batch for the application host.
    @discardableResult func consume(commands: [UInt32]) -> [UInt32] {
        var remaining: [UInt32] = []
        for command in commands {
            if fault != 0 || !handle(command: command) { remaining.append(command) }
        }
        return remaining
    }
    @discardableResult func handle(command: UInt32) -> Bool {
        guard command == 0x803a || command == 0x8006 else { return false }
        precondition(!executing, "WM_COMMAND must be dequeued outside player callbacks")
        executing = true
        defer { executing = false }
        faultStorage.pointee = 0
        serviceFault = 0
        events.removeAll(keepingCapacity: true)
        hooks.captureTiming(&globals.pointee)
        // Cleanup can free records still read later in this synchronous command.
        let recognized = heap.withStableFreedStorage {
            claw_player_death_command(applicationToken, command, globals, host, faultStorage)
        }
        faultStorage.pointee = max(faultStorage.pointee, serviceFault)
        hooks.publishTiming(globals.pointee)
        hooks.importPlayer()
        consumedCommands.append(command)
        // A diagnosed partial command is consumed too; replay could repeat cleanup.
        return recognized != 0 || fault != 0
    }

    // MARK: - Recovered metadata and construction

    // Original 0x513c20 table, through the terminal word before 0x513c68.
    // Original .rdata identities need host spans for native virtual lookup.
    static let actorContainerVTable: [UInt32] = [
        0x4f701d, 0x4cf8a0, 0x4c9e30, 0x4c96b0, 0x4c9e30, 0x4cf080,
        0x4bd250, 0x4c89e0, 0x4cf890, 0x4c8fc0, 0x4c91d0, 0x4c9200,
        0x4c9230, 0x4c9280, 0x4c92d0, 0x4c89f0, 0x4c9390, 0,
    ]
    @discardableResult static func installActorContainerMetadata(heap: ClawTokenHeap) -> Bool {
        if let existing = heap.lookup(0x513c20, words: 18) {
            return Array(UnsafeBufferPointer(start: existing, count: 18)) == actorContainerVTable
        }
        guard heap.lookup(0x513c20, words: 1) == nil else { return false }
        let target = heap.store(token: 0x513c20, words: 18)
        actorContainerVTable.withUnsafeBufferPointer {
            target.update(from: $0.baseAddress!, count: 18)
        }
        return true
    }

    // Source constructor 0x4254a0 only. Window/configuration/current-state/scene
    // bindings remain the caller's declared profile; this does not run WinMain.
    static func constructApplication(heap: ClawTokenHeap, host: ClawSceneActorHost) -> UInt32? {
        guard host.readClock != nil, heap.lookup(0x52e1cc, words: 1) != nil,
            heap.lookup(0x541328, words: 5) != nil
        else { return nil }
        let token = heap.allocate(bytes: 0x134)
        var sourceGlobals = ClawSinglePlayerSceneGlobals()
        var result: UInt32 = 0
        let completed = withUnsafeMutablePointer(to: &sourceGlobals) { pointer -> UInt32 in
            var context = ClawSinglePlayerSceneContext()
            context.host = host
            context.globals = pointer
            let recognized = claw_single_player_scene_entry(
                0x4254a0, token, nil, 0, &context, nil, nil, &result)
            return recognized != 0 && context.fault == 0 ? 1 : 0
        }
        guard completed != 0, result == token else {
            heap.free(token)
            return nil
        }
        return token
    }
    // Original inline 0x428d81..0x428dce owner constructor, with source sparse stores.
    // Caller must link owner+4 application, owner+c scene, owner+2c palette.
    static func constructOwner(heap: ClawTokenHeap, host: ClawSceneActorHost) -> UInt32? {
        let token = heap.allocate(bytes: 0x778)
        var sourceGlobals = ClawSinglePlayerSceneGlobals()
        let result = withUnsafeMutablePointer(to: &sourceGlobals) { pointer -> UInt32 in
            var context = ClawSinglePlayerSceneContext()
            context.host = host
            context.globals = pointer
            return claw_single_player_scene_construct(token, &context, nil, nil)
        }
        guard result == token else {
            heap.free(token)
            return nil
        }
        return token
    }

    // MARK: - Synchronous host transport and dormant actor traversal

    // The host borrows self. Iterator spans exist only until scanDormant returns;
    // heap tokens and the temporary iterator tokens remain guest identities.
    private var host: ClawSceneActorHost {
        ClawSceneActorHost(
            context: Unmanaged.passUnretained(self).toOpaque(),
            lookup: { raw, token, words in
                guard let raw else { return nil }
                let respawn = Unmanaged<ClawNativeRespawn>.fromOpaque(raw).takeUnretainedValue()
                if let iterator = respawn.iterators[token], words <= 17 { return iterator }
                return respawn.heap.lookup(token, words: words)
            },
            allocate: { raw, bytes in
                guard let raw else { return 0 }
                return Unmanaged<ClawNativeRespawn>.fromOpaque(raw).takeUnretainedValue().heap
                    .allocate(
                        bytes: bytes)
            },
            free: { raw, token in
                guard let raw else { return }
                Unmanaged<ClawNativeRespawn>.fromOpaque(raw).takeUnretainedValue().heap.free(token)
            },
            call: { raw, call in
                guard let raw else { return 0 }
                return Unmanaged<ClawNativeRespawn>.fromOpaque(raw).takeUnretainedValue().dispatch(
                    call)
            },
            readClock: { raw in
                guard let raw else { return 0 }
                let respawn = Unmanaged<ClawNativeRespawn>.fromOpaque(raw).takeUnretainedValue()
                guard let clock = respawn.backing.readClock else {
                    respawn.serviceFault = 4
                    respawn.faultStorage.pointee = 4
                    return 0
                }
                return clock(respawn.backing.context)
            })
    }
    // Original 0x4d51f0/0x4d5240: same three layers and exact recovered iterators.
    // Iterator bytes model original stack storage; their token is not allocated.
    @discardableResult func scanDormant(grid: UInt32, callback: UInt32) -> UInt32 {
        if callback == 0 { return 0 }
        let iteratorToken = UInt32(0x7fff_0000) &- UInt32(iterators.count) &* 0x100
        guard heap.lookup(iteratorToken, words: 1) == nil,
            let gridWords = heap.lookup(grid, words: 4)
        else {
            faultStorage.pointee = 1
            return 0
        }
        let iterator = UnsafeMutablePointer<UInt32>.allocate(capacity: 17)
        iterator.initialize(repeating: 0, count: 17)
        iterators[iteratorToken] = iterator
        defer {
            iterators.removeValue(forKey: iteratorToken)
            iterator.deinitialize(count: 17)
            iterator.deallocate()
        }
        var visitedCount: UInt32 = 0
        for layerIndex in 1...3 {
            iterator[0] = 0x513de0
            iterator[1] = 0
            iterator[2] = 0
            let layer = gridWords[layerIndex]
            var iteratorArguments = ClawSpatialGridArguments()
            iteratorArguments.words.0 = layer
            iteratorArguments.words.1 = 0
            iteratorArguments.count = 2
            var member: UInt32 = 0
            _ = claw_spatial_grid_entry(
                0x4f4860, iteratorToken, iteratorArguments, host, faultStorage, &member)
            while member != 0 && fault == 0 {
                guard let words = heap.lookup(member, words: 7) else {
                    faultStorage.pointee = 1
                    return visitedCount
                }
                var call = ClawSceneActorCall()
                call.function = callback
                call.argumentCount = 1
                call.arguments.0 = words[6]
                _ = dispatch(call)
                visitedCount &+= 1
                iteratorArguments.count = 0
                _ = claw_spatial_grid_entry(
                    0x4f49c0, iteratorToken, iteratorArguments, host, faultStorage, &member)
            }
            if fault != 0 { return visitedCount }
        }
        return visitedCount
    }

    // MARK: - Ordered service dispatch and fault propagation

    private func dispatch(_ call: ClawSceneActorCall) -> UInt32 {
        events.append(call)
        hooks.observe(call)
        switch call.function {
        case 0x4d51f0:
            guard call.argumentCount == 1 else {
                serviceFault = 4
                faultStorage.pointee = 4
                return 0
            }
            return scanDormant(grid: call.receiver, callback: call.arguments.0)
        case 0x46e340:
            claw_player_death_cleanup_actor(call.arguments.0, host, faultStorage)
            return 0
        case 0x415df0:
            guard call.argumentCount == 1, hooks.playerPrimary(call.arguments.0) else {
                serviceFault = 4
                faultStorage.pointee = 4
                return 0
            }
            return 0
        case 0x4c8fc0:
            guard call.argumentCount == 1, hooks.actorFrame(call.receiver, call.arguments.0) else {
                serviceFault = 4
                faultStorage.pointee = 4
                return 0
            }
            return 0
        default:
            if let result = hooks.service(call) { return result }
            unresolvedServices.insert(call.function)
            serviceFault = 4
            faultStorage.pointee = 4
            return 0
        }
    }
}
extension ClawPlayerDeathCommandGlobals: ClawSnapshotNativeValue {}
