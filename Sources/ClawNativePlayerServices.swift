import Foundation

// Source powerup calls over the scene's raw actor/private spans. A callback
// borrows the live player buffer; it never re-enters the player's Swift cache.
final class ClawNativePlayerServices {
    // The scene owns this service; source callbacks borrow it synchronously.
    unowned let scene: ClawNativeScene
    private let globals = UnsafeMutablePointer<ClawPlayerPowerupGlobals>.allocate(capacity: 1)
    private let deathGlobals = UnsafeMutablePointer<ClawPlayerDeathServiceGlobals>.allocate(capacity: 1)
    var powerupGlobals: UnsafeMutablePointer<ClawPlayerPowerupGlobals> { globals }
    private(set) var unresolved: Set<UInt32> = []
    private(set) var fault: UInt32 = 0
    private var activeDepth = 0

    // MARK: - Snapshot persistence

    // Keep stored names stable: synthesized Codable keys are part of the snapshot.
    struct SavedState: Codable, Equatable {
        let powerups: ClawSnapshotValue<ClawPlayerPowerupGlobals>
        let death: ClawSnapshotValue<ClawPlayerDeathServiceGlobals>
        let unresolved: Set<UInt32>, fault: UInt32
    }
    func savedState() throws -> SavedState {
        guard activeDepth == 0 else {
            throw ClawSnapshotError.activeFrame
        }
        return .init(powerups: ClawSnapshotValue(globals.pointee), death: ClawSnapshotValue(deathGlobals.pointee),
                     unresolved: unresolved, fault: fault)
    }
    func restoreState(_ saved: SavedState) throws {
        guard activeDepth == 0 else {
            throw ClawSnapshotError.activeFrame
        }
        guard saved.powerups.value.managerToken == globals.pointee.managerToken,
              saved.powerups.value.playerToken == globals.pointee.playerToken,
              saved.death.value.managerToken == deathGlobals.pointee.managerToken,
              saved.death.value.emptyStringToken == deathGlobals.pointee.emptyStringToken
        else {
            throw ClawSnapshotError.invalidState
        }
        globals.pointee = saved.powerups.value
        deathGlobals.pointee = saved.death.value
        unresolved = saved.unresolved
        fault = saved.fault
    }

    // MARK: - Lifecycle

    init(scene: ClawNativeScene) {
        self.scene = scene
        globals.initialize(to: ClawPlayerPowerupGlobals())
        globals.pointee.managerToken = scene.heap.lookup(scene.ownerIdentity, words: 2)![1]
        globals.pointee.playerToken = 0x10002000
        deathGlobals.initialize(to: ClawPlayerDeathServiceGlobals(managerToken: globals.pointee.managerToken,
                                                                  emptyStringToken: 0x52e1c4))
    }
    deinit {
        globals.deinitialize(count: 1)
        globals.deallocate()
        deathGlobals.deinitialize(count: 1)
        deathGlobals.deallocate()
    }

    // MARK: - Player service dispatch

    func call(_ state: UnsafeMutablePointer<ClawPlayerLocomotion>, entry: UInt32,
              a: UInt32, b: UInt32, c: UInt32) -> UInt32? {
        activeDepth += 1
        defer { activeDepth -= 1 }
        if entry == 0x461a00 || entry == 0x461c40 {
            // PlayerDamage's three-argument dependency encodes the original
            // fixed scene/style/source operands. Publish the suspended actor
            // without re-entering its Swift cache, then run the complete root.
            guard let actor = scene.heap.lookup(0x10002000, words: 128), let primary = scene.heap.lookup(state.pointee.actor.27, words: 93) else {
                fault = 1
                return 0
            }
            withUnsafeBytes(of: &state.pointee.actor) {
                UnsafeMutableRawPointer(actor).copyMemory(from: $0.baseAddress!, byteCount: 512)
            }
            primary[7] = state.pointee.logicState
            let arguments: [UInt32] = entry == 0x461a00 ? [state.pointee.actor.3, a, b, c, 1, 0x10002000] : [state.pointee.actor.3, a, b, c]
            let value = scene.effects?.impactEntry(entry, arguments: arguments) ?? 0
            fault = scene.effects?.fault ?? 1
            return value
        }
        if entry == 0x158 || entry == 0x15c {
            // These dependency IDs represent the original direct read of the
            // supported actor's displacement, not executable function entries.
            guard let word = scene.heap.lookup(a &+ entry, words: 1) else {
                fault = 1
                return 0
            }
            return word.pointee
        }
        if ClawNativeSpeech.services.contains(entry), let speech = scene.speech {
            // The callback borrows the player's Swift runtime. Publish its raw
            // actor/state for speech gating without re-entering that cache.
            guard let actor = scene.heap.lookup(0x10002000, words: 128), let primary = scene.heap.lookup(state.pointee.actor.27, words: 93) else {
                fault = 1
                return 0
            }
            withUnsafeBytes(of: &state.pointee.actor) {
                UnsafeMutableRawPointer(actor).copyMemory(from: $0.baseAddress!, byteCount: 512)
            }
            primary[7] = state.pointee.logicState
            let count = (entry == 0x48ce40 || entry == 0x48ceb0) ? 3 : (entry == 0x48c820 || entry == 0x48c8a0) ? 2 : 1
            let value = speech.service(entry, arguments: Array([a, b, c].prefix(count))) ?? 0
            fault = speech.fault
            return value
        }
        if entry == 0x41ebd0 || entry == 0x4b7aa0 {
            return deathService(entry, argument: a)
        }
        if entry == 0x41d6f0 {
            return scene.loot?.playerSound(item: a)
        }
        guard entry == 0x41f990 || entry == 0x41fc30 else {
            return nil
        }
        let heap = scene.heap
        guard let actor = heap.lookup(0x10002000, words: 128), let priv = heap.lookup(0x10005000, words: 78),
              let primary = heap.lookup(actor[27], words: 93) else {
            fault = 1
            return 0
        }
        withUnsafeBytes(of: &state.pointee.actor) { source in
            UnsafeMutableRawPointer(actor).copyMemory(from: source.baseAddress!, byteCount: 512)
        }
        withUnsafeBytes(of: &state.pointee.privateWords) { source in
            UnsafeMutableRawPointer(priv).copyMemory(from: source.baseAddress!, byteCount: 312)
        }
        primary[7] = state.pointee.logicState
        globals.pointee.powerup = state.pointee.powerup
        let arguments: [UInt32] = entry == 0x41f990
            ? [0x10002000, actor[27], 0x10005000, a, b]
            : [0x10002000, actor[27], 0x10005000, a]
        var context = ClawPlayerPowerupRuntimeContext(scene: scene.actorHost, globals: globals, fault: 0)
        var result: UInt32 = 0
        // Arguments and the unretained service pointer are valid only during
        // this synchronous call. Copy source writes back after it returns.
        let completed = arguments.withUnsafeBufferPointer { args in
            claw_player_powerup_entry(entry, 0, args.baseAddress, UInt32(args.count), &context, { context, call, user in
                guard let context, let call, let user else {
                    return 0
                }
                let services = Unmanaged<ClawNativePlayerServices>.fromOpaque(user).takeUnretainedValue()
                if ClawNativeSpeech.services.contains(call.pointee.function), let speech = services.scene.speech {
                    let args = withUnsafeBytes(of: call.pointee.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(call.pointee.argumentCount))) }
                    let value = speech.service(call.pointee.function, receiver: call.pointee.receiver, arguments: args, name: call.pointee.name.map { String(cString: $0) }) ?? 0
                    if speech.fault != 0 {
                        context.pointee.fault = speech.fault
                        services.unresolved.formUnion(speech.unresolved)
                    }
                    return value
                }
                if let result = services.scene.effects?.service(call.pointee) {
                    return result
                }
                if call.pointee.function == 0x4c6130, let rendering = services.scene.rendering {
                    return rendering.setCompressedEffect(call.pointee.receiver, effect: call.pointee.arguments.0,
                                                         resource: call.pointee.arguments.1)
                }
                services.unresolved.insert(call.pointee.function)
                context.pointee.fault = 1
                return 0
            }, Unmanaged.passUnretained(self).toOpaque(), &result)
        }
        fault = context.fault
        withUnsafeMutableBytes(of: &state.pointee.actor) { destination in
            destination.copyMemory(from: UnsafeRawBufferPointer(start: actor, count: 512))
        }
        withUnsafeMutableBytes(of: &state.pointee.privateWords) { destination in
            destination.copyMemory(from: UnsafeRawBufferPointer(start: priv, count: 312))
        }
        state.pointee.powerup = globals.pointee.powerup
        if completed == 0 {
            unresolved.insert(entry)
        }
        return result
    }

    // MARK: - Death services

    private func deathService(_ entry: UInt32, argument: UInt32) -> UInt32 {
        var context = ClawPlayerDeathServiceContext(scene: scene.actorHost, globals: deathGlobals,
            temporaryStringToken: 0, fault: 0)
        var argument = argument, result: UInt32 = 0
        let completed = withUnsafePointer(to: &argument) { arguments in
            claw_player_death_service_entry(entry, 0, entry == 0x4b7aa0 ? arguments : nil,
                entry == 0x4b7aa0 ? 1 : 0, &context, { context, call, user in
                    guard let context, let call, let user else {
                        return 0
                    }
                    let services = Unmanaged<ClawNativePlayerServices>.fromOpaque(user).takeUnretainedValue()
                    // The actual owner vtable selects frozen40af90. Compose
                    // its source getter through the existing frame services.
                    if call.pointee.function == 0x40af90 {
                        var probe = ClawSceneActorCall()
                        probe.function = call.pointee.function
                        probe.receiver = call.pointee.receiver
                        return services.scene.actorHost.call?(services.scene.actorHost.context, probe) ?? 0
                    }
                    services.unresolved.insert(call.pointee.function)
                    context.pointee.fault = 1
                    return 0
                }, Unmanaged.passUnretained(self).toOpaque(), &result)
        }
        fault = context.fault
        if completed == 0 {
            unresolved.insert(entry)
        }
        return result
    }
}
extension ClawPlayerPowerupGlobals: ClawSnapshotNativeValue {}
extension ClawPlayerDeathServiceGlobals: ClawSnapshotNativeValue {}
