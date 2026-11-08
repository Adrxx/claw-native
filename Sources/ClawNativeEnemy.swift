import Foundation

// Original Rat/RatBomb gameplay with explicit platform/resource adapters.
final class ClawNativeEnemy {
    enum Kind: String, Codable { case rat, bomb }
    let kind: Kind, token: UInt32, resources: ClawActorResources
    weak var scene: ClawNativeScene?
    let state = UnsafeMutablePointer<ClawGenericEnemy>.allocate(capacity: 1)
    let rat = UnsafeMutablePointer<ClawRatContext>.allocate(capacity: 1)
    let bomb = UnsafeMutablePointer<ClawRatBombContext>.allocate(capacity: 1)
    private let common = UnsafeMutablePointer<ClawGenericEnemyStatesContext>.allocate(capacity: 1)
    private let soundSlots = UnsafeMutablePointer<ClawGenericEnemyStateResource>.allocate(capacity: 2048)
    private var soundCount = 0
    private let states: ClawEnemyStateView
    private(set) var failure: String?
    private(set) var unresolved: Set<UInt32> = []
    private var actorIdentity: ClawTokenHeap.AllocationIdentity?

    var generic: UnsafeMutablePointer<ClawGenericEnemyContext> {
        UnsafeMutableRawPointer(kind == .rat ? UnsafeMutableRawPointer(rat) : UnsafeMutableRawPointer(bomb))
            .assumingMemoryBound(to: ClawGenericEnemyContext.self)
    }
    init(kind: Kind, snapshot: ClawInteractionActor, scene: ClawNativeScene, resources: ClawActorResources) {
        if claw_native_v13_enabled() != 0 { claw_generic_enemy_states_use_v13() }
        self.kind = kind; token = snapshot.token; self.scene = scene; self.resources = resources
        actorIdentity = scene.heap.containingAllocationIdentity(at: snapshot.token, count: 4)
        states = ClawEnemyStateView(registry: scene.stateRegistry!, inheritance: kind == .rat ? ["CEnemy", "Rat"] : ["Projectile", "RatBomb"])
        state.initialize(to: ClawGenericEnemy()); rat.initialize(to: ClawRatContext())
        bomb.initialize(to: ClawRatBombContext()); common.initialize(to: ClawGenericEnemyStatesContext())
        soundSlots.initialize(repeating: ClawGenericEnemyStateResource(), count: 2048)
        common.pointee.resources = UnsafePointer(soundSlots)
        if kind == .rat { claw_rat_context_defaults(rat) } else { claw_rat_bomb_context_defaults(bomb) }
        accept(snapshot)
        generic.pointee.actorToken = token; generic.pointee.sceneToken = snapshot.actor.3
        generic.pointee.primaryToken = snapshot.actor.27; generic.pointee.playerToken = 0x10002000
        generic.pointee.tileManagerToken = 0x60003000; generic.pointee.soundRegistryToken = 0x63000020
        generic.pointee.emptyStringToken = states.entries[0].nameToken
        generic.pointee.states = UnsafePointer(states.entries); generic.pointee.stateCount = states.count
        rat.pointee.sequenceRegistryToken = 0x63000010; rat.pointee.objectManagerToken = scene.containerToken
        bomb.pointee.sequenceRegistryToken = 0x63000010
    }
    deinit {
        state.deinitialize(count: 1); state.deallocate(); rat.deinitialize(count: 1); rat.deallocate()
        bomb.deinitialize(count: 1); bomb.deallocate(); common.deinitialize(count: 1); common.deallocate()
        soundSlots.deinitialize(count: 2048); soundSlots.deallocate()
    }
    func accept(_ value: ClawInteractionActor) {
        state.pointee.actor = value.actor; state.pointee.primary = value.primary
        state.pointee.secondary = value.secondary; state.pointee.contact = value.contact
    }
    func snapshot() -> ClawInteractionActor {
        var value = ClawInteractionActor(); value.token = token; value.actor = state.pointee.actor
        value.primary = state.pointee.primary; value.secondary = state.pointee.secondary; value.contact = state.pointee.contact
        return value
    }
    func refresh() {
        guard let scene else { return }
        if let value = scene.snapshotActor(token) { accept(value) }
        if generic.pointee.enemyToken != 0,
            let raw = scene.heap.lookup(generic.pointee.enemyToken, words: kind == .rat ? 264 : 92) {
            withUnsafeMutableBytes(of: &state.pointee.enemy) {
                UnsafeMutableRawBufferPointer(rebasing: $0.prefix(kind == .rat ? 1056 : 368)).copyMemory(from: UnsafeRawBufferPointer(start: raw, count: kind == .rat ? 1056 : 368))
            }
        }
        generic.pointee.tick = scene.gameTime; generic.pointee.animationDelta = scene.animationDelta
        generic.pointee.playerActor = scene.player.runtime.actor
        generic.pointee.secondaryToken = state.pointee.actor.28; generic.pointee.contactToken = state.pointee.actor.30
        if let platform = scene.snapshotActor(state.pointee.actor.32) { generic.pointee.platformActor = platform.actor }
        rat.pointee.playerPrivate = scene.player.runtime.privateWords
        rat.pointee.audioManagerAvailable = scene.player.audio == nil ? 0 : 1
        rat.pointee.masterVolume = scene.player.audio?.routing.masterVolume ?? 0
        bomb.pointee.audioManagerAvailable = rat.pointee.audioManagerAvailable
        bomb.pointee.masterVolume = rat.pointee.masterVolume
        common.pointee.playerPrivate = scene.player.runtime.privateWords
        common.pointee.audioEnabled = rat.pointee.audioManagerAvailable
        common.pointee.audioPosition = rat.pointee.masterVolume
        if let attacker = scene.snapshotActor(state.pointee.actor.29) {
            rat.pointee.attackerToken = attacker.token; rat.pointee.attackerActor = attacker.actor
            common.pointee.attackerToken = attacker.token; common.pointee.attackerActor = attacker.actor
        }
    }
    func flush() {
        guard let scene, ownsActor else { return }
        scene.write(snapshot())
        if let raw = scene.heap.lookup(generic.pointee.enemyToken, words: kind == .rat ? 264 : 92) {
            withUnsafeBytes(of: &state.pointee.enemy) {
                UnsafeMutableRawBufferPointer(start: raw, count: kind == .rat ? 1056 : 368).copyMemory(from: UnsafeRawBufferPointer(rebasing: $0.prefix(kind == .rat ? 1056 : 368)))
            }
        }
        if rat.pointee.attackerToken != 0, var attacker = scene.snapshotActor(rat.pointee.attackerToken) {
            attacker.actor = rat.pointee.attackerActor; scene.write(attacker)
        }
        if rat.pointee.fault != 0 || bomb.pointee.fault != 0 { failure = "Enemy context fault \(rat.pointee.fault)/\(bomb.pointee.fault)" }
    }
    func tick() {
        guard ownsActor else { failure = "Retired enemy owner"; return }
        refresh()
        let result = kind == .rat ? claw_rat_tick(state, rat, nativeEnemyDependency, Unmanaged.passUnretained(self).toOpaque())
            : claw_rat_bomb_tick(state, bomb, nativeEnemyDependency, Unmanaged.passUnretained(self).toOpaque())
        if result == 0 { failure = "Enemy callback did not complete" }
        flush()
    }
    func callback(_ function: UInt32, argument: UInt32 = 0) -> UInt32 {
        guard ownsActor else { failure = "Retired enemy owner"; return 0 }
        refresh(); let value = nativeEntry(function, argument: argument); flush(); return value ?? 0
    }
    private func nativeEntry(_ function: UInt32, argument: UInt32) -> UInt32? {
        let user = Unmanaged.passUnretained(self).toOpaque(); var result: UInt32 = 0
        let completed = kind == .rat ? claw_rat_entry(state, rat, function, argument, nativeEnemyDependency, user, &result)
            : claw_rat_bomb_entry(state, bomb, function, argument, nativeEnemyDependency, user, &result)
        if completed == 1 { return result }
        if claw_native_generic_enemy_state_entry(state, generic, common, function, argument, nativeEnemyDependency, user) == 1 { return 0 }
        if claw_generic_enemy_entry(state, generic, function, argument, nativeEnemyDependency, user) == 1 { return 0 }
        return nil
    }
    fileprivate func dependency(_ call: ClawGenericEnemyCall) -> UInt64 {
        guard let scene else { return 0 }
        let a = call.arguments.0, b = call.arguments.1, c = call.arguments.2, d = call.arguments.3
        if let result = nativeEntry(call.function, argument: a) { return UInt64(result) }
        do {
            switch call.function {
            case 0x4f63ec:
                let token = scene.heap.allocate(bytes: a)
                if a == 0x420 || a == 0x170 { generic.pointee.enemyToken = token }
                return UInt64(token)
            case 0x4f6428: scene.heap.free(a); return 0
            case 0x4dba00:
                return UInt64(call.name.flatMap { states.ids[String(cString: $0)] } ?? 0)
            case 0x4a3050: return UInt64(scene.nextRandom())
            case 0x461a00,0x461c40:
                flush()
                let args = withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
                return UInt64(scene.effects?.impactEntry(call.function,arguments:args) ?? 0)
            case 0x4c7fa0, 0x4c8060:
                guard let name = call.name else { return 0 }
                var binding = ClawActorResourceBindings(); binding.actor = state.pointee.actor
                binding.secondary = call.function == 0x4c7fa0 ? state.pointee.secondary : state.pointee.contact
                var context = ClawActorBindingContext(); context.logicRegistryToken = 0x63000030
                let result = call.function == 0x4c7fa0
                    ? claw_actor_bind_secondary_logic_name(&binding, &context, name, nativeEnemyBinding, Unmanaged.passUnretained(self).toOpaque())
                    : claw_actor_bind_contact_logic_name(&binding, &context, name, nativeEnemyBinding, Unmanaged.passUnretained(self).toOpaque())
                state.pointee.actor = binding.actor
                if call.function == 0x4c7fa0 { state.pointee.secondary = binding.secondary }
                else { state.pointee.contact = binding.secondary }
                return UInt64(result)
            case 0x4c7970, 0x4c7900:
                guard let name = call.name, let images = try resources.images(name: String(cString: name)) else { return 0 }
                var binding = ClawActorResourceBindings(); binding.actor = state.pointee.actor
                var context = ClawActorBindingContext(); context.image = images.binding(); context.imageRegistryToken = 0x63000040
                let result = call.function == 0x4c7970
                    ? claw_actor_bind_default_image(&binding, &context, name, nativeEnemyBinding, Unmanaged.passUnretained(self).toOpaque())
                    : claw_actor_bind_indexed_image(&binding, &context, name, Int32(bitPattern: a), nativeEnemyBinding, Unmanaged.passUnretained(self).toOpaque())
                state.pointee.actor = binding.actor
                rat.pointee.imageMinimum = Int32(images.minimum); bomb.pointee.imageMinimum = Int32(images.minimum)
                bomb.pointee.imageMaximum = Int32(images.maximum); bomb.pointee.minimumImageToken = images.table[images.minimum]
                setImageHeader(state.pointee.actor.93)
                return UInt64(result)
            case 0x40f680:
                let value = resources.images(token: call.receiver)?.identities[Int(a)] ?? 0
                setImageHeader(value); return UInt64(value)
            case 0x4f6286:
                guard let name = call.name else { return 0 }; let key = String(cString: name)
                if call.receiver == 0x63000010 { return UInt64(try resources.sequence(name: key)?.token ?? 0) }
                let sound = scene.player.audio?.resolve(name: key)
                if let sound, !(0..<soundCount).contains(where: { soundSlots[$0].token == sound.resourceToken }) {
                    precondition(soundCount < 2048)
                    soundSlots[soundCount] = ClawGenericEnemyStateResource(token: sound.resourceToken, controllerToken: sound.voicePoolToken)
                    soundCount += 1; common.pointee.resourceCount = soundCount
                }
                if key == "GAME_EEHH" { rat.pointee.soundPoolToken = sound?.voicePoolToken ?? 0 }
                if key == "GAME_BOINKJR" { bomb.pointee.bounceSoundPoolToken = sound?.voicePoolToken ?? 0 }
                if key == "GAME_BOMBEXP" { bomb.pointee.explosionSoundPoolToken = sound?.voicePoolToken ?? 0 }
                return UInt64(sound?.resourceToken ?? 0)
            case 0x4b45f0:
                return UInt64(scene.player.audio?.playVoicePool(call.receiver,
                    request: ClawAudioRequest(volume: a, pan: b, pitchPercent: c, looping: d)) ?? 0)
            case 0x4208e0: return UInt64(scene.player.audio?.play(resource: call.receiver, volume: a) ?? 0)
            case 0x4c8220, 0x4c8260, 0x420a10, 0x4c82a0:
                // Expose constructor/controller stores before the original
                // animation body and its sound callback, then retain its writes.
                flush()
                let result = scene.actorAnimation(function: call.function, receiver: call.receiver,
                    argument0: a, argument1: b)
                if let changed = scene.snapshotActor(token) { accept(changed) }
                return UInt64(result)
            case 0x4cbb60:
                var actor = collisionActor()
                let result = scene.player.collision.move(actor: &actor, x: b, y: c, options: d,
                    otherActors: scene.collisionActors(excluding: token))
                applyCollision(actor); return UInt64(result)
            case 0x4cd800:
                var actor = collisionActor(); let result = scene.player.collision.placeOnGround(actor: &actor)
                applyCollision(actor); return UInt64(result)
            case 0x4207f0: return UInt64(scene.player.collision.footAttribute(x: a, y: b, bottom: 0, xOffset: 0))
            case 0x4cda10:
                let value = scene.player.collision.horizontalClear(x: a, y: b, targetX: c, step: d)
                if value.fault != 0 { failure = "Enemy horizontal query fault" }; return UInt64(value.result)
            case 0x4c8da0:
                guard kind == .rat, call.name.map({ String(cString: $0) }) == "RatBomb" else { break }
                flush(); guard let child = try scene.createBomb(x: b, y: c, z: d, flags: call.arguments.5) else { return 0 }
                rat.pointee.projectileToken = child.token; copyProjectile(child); return UInt64(child.token)
            case 0x47d7d0:
                guard kind == .rat, let child = scene.enemies[a] else { return 0 }
                child.tick(); copyProjectile(child); return 1
            case 0x47e050:
                guard kind == .rat, let child = scene.enemies[rat.pointee.projectileToken] else { return 0 }
                child.state.pointee.actor = rat.pointee.projectileActor; child.state.pointee.primary = rat.pointee.projectilePrimary
                child.state.pointee.enemy = rat.pointee.projectileEnemy; child.flush()
                _ = child.callback(0x47e050); copyProjectile(child); return 0
            default: break
            }
        } catch { failure = String(describing: error) }
        unresolved.insert(call.function); return 0
    }
    private func copyProjectile(_ child: ClawNativeEnemy) {
        rat.pointee.projectileActor = child.state.pointee.actor; rat.pointee.projectilePrimary = child.state.pointee.primary
        rat.pointee.projectileEnemy = child.state.pointee.enemy; rat.pointee.projectileVisualActor = child.state.pointee.actor
        rat.pointee.projectileEnemyToken = child.generic.pointee.enemyToken; rat.pointee.projectileActivateFunction = 0x47e050
    }
    private func setImageHeader(_ image: UInt32) {
        guard let scene, let raw = scene.heap.lookup(image, words: 16) else { return }
        withUnsafeMutableBytes(of: &rat.pointee.imageHeader) { $0.copyMemory(from: UnsafeRawBufferPointer(start: raw, count: 64)) }
        bomb.pointee.imageHeader = rat.pointee.imageHeader
    }
    fileprivate func binding(_ context: UnsafeMutablePointer<ClawActorBindingContext>, call: ClawActorBindingCall) -> UInt32 {
        switch call.function {
        case 0x4f6286:
            if call.receiver == context.pointee.imageRegistryToken { return context.pointee.image.token }
            guard let name = call.name, let metadata = claw_logic_registry_find(name) else { return 0 }
            context.pointee.metadataCallback = metadata.pointee.callback; context.pointee.metadataFlags = metadata.pointee.flags
            return metadata.pointee.registrationOrdinal
        case 0x4f63ec: return scene?.heap.allocate(bytes: call.argument) ?? 0
        case 0x4f6428: scene?.heap.free(call.argument); return 0
        default: unresolved.insert(call.function); return 0
        }
    }
    private func word(_ offset: UInt32) -> UInt32 { claw_rat_actor_word(state, offset) }
    private func set(_ offset: UInt32,_ value: UInt32) { claw_rat_set_actor_word(state, offset, value) }
    private func collisionActor() -> ClawCollisionActor { ClawCollisionActor(snapshot: snapshot()) }
    private func applyCollision(_ value: ClawCollisionActor) {
        for (offset,word) in [(8,value.flags),(0x4c,value.x),(0x50,value.y),(0xcc,value.mode),
            (0x80,value.supportToken),(0x158,value.deltaX),(0x15c,value.deltaY)] { set(UInt32(offset),word) }
    }

    private var ownsActor: Bool {
        guard let scene, let actorIdentity else { return false }
        return scene.heap.containingAllocationIdentity(at: token, count: 4) === actorIdentity
    }
    struct SavedState: Codable, Equatable {
        let kind: Kind, token: UInt32
        let actor: ClawSnapshotWitness
        let state: ClawSnapshotValue<ClawGenericEnemy>
        let rat: [String: Data], bomb: [String: Data], ratGeneric: [String: Data], bombGeneric: [String: Data]
        let common: [String: Data]
        let sounds: [ClawSnapshotValue<ClawGenericEnemyStateResource>]
        let states: ClawEnemyStateView.SavedState
        let failure: String?, unresolved: Set<UInt32>
    }
    func savedState() throws -> SavedState {
        guard let scene, let actorIdentity, rat.pointee.generic.bitWords == nil, bomb.pointee.generic.bitWords == nil,
              generic.pointee.states == UnsafePointer(states.entries), generic.pointee.stateCount == states.count,
              common.pointee.resources == UnsafePointer(soundSlots), common.pointee.resourceCount == soundCount,
              rat.pointee.generic.bitWordCount == 0, bomb.pointee.generic.bitWordCount == 0
        else { throw ClawSnapshotError.invalidState }
        return SavedState(kind: kind, token: token,
            actor: ClawSnapshotWitness(heap: scene.heap, token: token, count: 4, identity: actorIdentity, interior: true),
            state: ClawSnapshotValue(state.pointee), rat: Self.ratFields.capture(rat.pointee), bomb: Self.bombFields.capture(bomb.pointee),
            ratGeneric: ClawEnemySnapshotFields.generic.capture(rat.pointee.generic),
            bombGeneric: ClawEnemySnapshotFields.generic.capture(bomb.pointee.generic),
            common: ClawEnemySnapshotFields.common.capture(common.pointee),
            sounds: (0..<soundCount).map { ClawSnapshotValue(soundSlots[$0]) }, states: states.savedState(),
            failure: failure, unresolved: unresolved)
    }
    static func restoring(_ saved: SavedState, scene: ClawNativeScene, resources: ClawActorResources,
                          heap plan: ClawTokenHeap.RestorePlan) throws -> ClawNativeEnemy {
        guard saved.actor.reference.token == saved.token, saved.actor.reference.count == 4,
              saved.actor.reference.interior, saved.sounds.count <= 2048 else { throw ClawSnapshotError.invalidState }
        var snapshot = ClawInteractionActor(); snapshot.token = saved.token
        snapshot.actor = saved.state.value.actor; snapshot.primary = saved.state.value.primary
        snapshot.secondary = saved.state.value.secondary; snapshot.contact = saved.state.value.contact
        let result = ClawNativeEnemy(kind: saved.kind, snapshot: snapshot, scene: scene, resources: resources)
        result.actorIdentity = try saved.actor.resolve(in: plan)
        result.state.pointee = saved.state.value
        result.rat.pointee = try ratFields.restoring(saved.rat, into: result.rat.pointee)
        result.bomb.pointee = try bombFields.restoring(saved.bomb, into: result.bomb.pointee)
        result.rat.pointee.generic = try ClawEnemySnapshotFields.generic.restoring(saved.ratGeneric, into: result.rat.pointee.generic)
        result.bomb.pointee.generic = try ClawEnemySnapshotFields.generic.restoring(saved.bombGeneric, into: result.bomb.pointee.generic)
        result.common.pointee = try ClawEnemySnapshotFields.common.restoring(saved.common, into: result.common.pointee)
        result.soundCount = saved.sounds.count; result.common.pointee.resourceCount = saved.sounds.count
        for (i, sound) in saved.sounds.enumerated() { result.soundSlots[i] = sound.value }
        try result.states.restoreState(saved.states)
        result.failure = saved.failure; result.unresolved = saved.unresolved
        return result
    }
    static let ratFields = ClawSnapshotFields<ClawRatContext>(fields: [
        .init("playerPrivate", \.playerPrivate), .init("attackerToken", \.attackerToken), .init("attackerActor", \.attackerActor),
        .init("damageScale", \.damageScale), .init("healthScale", \.healthScale), .init("rangeScale", \.rangeScale),
        .init("imageMinimum", \.imageMinimum), .init("imageHeader", \.imageHeader), .init("soundPoolToken", \.soundPoolToken),
        .init("audioManagerAvailable", \.audioManagerAvailable), .init("masterVolume", \.masterVolume),
        .init("projectileToken", \.projectileToken), .init("projectileActor", \.projectileActor),
        .init("projectilePrimary", \.projectilePrimary), .init("projectileEnemy", \.projectileEnemy),
        .init("sequenceRegistryToken", \.sequenceRegistryToken), .init("objectManagerToken", \.objectManagerToken),
        .init("projectileEnemyToken", \.projectileEnemyToken), .init("projectileActivateFunction", \.projectileActivateFunction),
        .init("projectileVisualActor", \.projectileVisualActor), .init("fault", \.fault)
    ])
    private static let bombFields = ClawSnapshotFields<ClawRatBombContext>(fields: [
        .init("sequenceRegistryToken", \.sequenceRegistryToken), .init("damageScale", \.damageScale),
        .init("imageMinimum", \.imageMinimum), .init("imageMaximum", \.imageMaximum),
        .init("minimumImageToken", \.minimumImageToken), .init("imageHeader", \.imageHeader),
        .init("audioManagerAvailable", \.audioManagerAvailable), .init("masterVolume", \.masterVolume),
        .init("bounceSoundPoolToken", \.bounceSoundPoolToken), .init("explosionSoundPoolToken", \.explosionSoundPoolToken), .init("fault", \.fault)
    ])
}

// Shared explicit pointer-free projections. State/resource pointers and counts
// are rebound from their separately encoded views on the candidate graph.
enum ClawEnemySnapshotFields {
    static let generic = ClawSnapshotFields<ClawGenericEnemyContext>(fields: [
        .init("actorToken", \.actorToken), .init("primaryToken", \.primaryToken),
        .init("secondaryToken", \.secondaryToken), .init("contactToken", \.contactToken), .init("enemyToken", \.enemyToken),
        .init("sceneToken", \.sceneToken), .init("tileManagerToken", \.tileManagerToken),
        .init("soundRegistryToken", \.soundRegistryToken), .init("playerToken", \.playerToken),
        .init("playerActor", \.playerActor), .init("platformActor", \.platformActor),
        .init("tick", \.tick), .init("animationDelta", \.animationDelta), .init("levelWord", \.levelWord),
        .init("forcedRandom", \.forcedRandom), .init("hitMode", \.hitMode), .init("defaults", \.defaults),
        .init("virtualFunctions", \.virtualFunctions), .init("emptyStringToken", \.emptyStringToken), .init("bitHandlerToken", \.bitHandlerToken)
    ])
    static let common = ClawSnapshotFields<ClawGenericEnemyStatesContext>(fields: [
        .init("attackerToken", \.attackerToken), .init("attackerActor", \.attackerActor), .init("playerPrivate", \.playerPrivate),
        .init("strikeCounter", \.strikeCounter), .init("audioEnabled", \.audioEnabled), .init("audioPosition", \.audioPosition)
    ])
}
extension ClawGenericEnemy: ClawSnapshotNativeValue {}
extension ClawGenericEnemyStateResource: ClawSnapshotNativeValue {}
private let nativeEnemyDependency: ClawGenericEnemyDependency = { _,_,call,context in
    guard let call, let context else { return 0 }
    return Unmanaged<ClawNativeEnemy>.fromOpaque(context).takeUnretainedValue().dependency(call.pointee)
}
private let nativeEnemyBinding: ClawActorBindingDependency = { _,context,call,user in
    guard let context,let call,let user else { return 0 }
    return Unmanaged<ClawNativeEnemy>.fromOpaque(user).takeUnretainedValue().binding(context,call: call.pointee)
}

extension ClawCollisionActor {
    init(snapshot: ClawInteractionActor) {
        var snapshot = snapshot
        self = withUnsafeBytes(of: &snapshot.actor) { raw in
            func word(_ offset: Int) -> UInt32 { raw.load(fromByteOffset: offset, as: UInt32.self) }
            func rect(_ offset: Int) -> ClawPlayerRect {
                ClawPlayerRect(left: word(offset), top: word(offset+4), right: word(offset+8), bottom: word(offset+12))
            }
            return ClawCollisionActor(flags: word(8), x: word(0x4c), y: word(0x50), mode: word(0xcc), type: word(0xd0),
                stepX: word(0xdc), stepY: word(0xe0), supportToken: word(0x80), token: snapshot.token,
                deltaX: word(0x158), deltaY: word(0x15c), moveRect: rect(0x118), hitRect: rect(0x128))
        }
    }
}
