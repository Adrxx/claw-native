import Foundation

// Native player host. The scene supplies actor scheduling, interactions and
// raw animation resources when attached; standalone checks retain their adapter.
final class ClawNativePlayer {
    // MARK: - Runtime and scene services

    let assets: ClawPlayerAssets
    var collision: ClawCollisionMap
    private(set) var runtime = ClawPlayerLocomotion()
    private(set) var playback: ClawAnimationPlayback?
    private(set) var sequence = "STAND"
    private(set) var failure: String?
    private(set) var unresolvedDependencies: Set<UInt32> = []
    var compressedDrawingCache: ClawPlayerDrawingCache?
    private var standing = ClawPlayerStandingContext(inputPressed: 0, randomState: 1, liftedWeaponVelocityX: 0)
    private var input = ClawPlayerInputContext()
    private var powerupClock = ClawPlayerPowerupContext()
    private var initialization = ClawPlayerInitializationContext()
    private var resourceBindings = ClawActorResourceBindings()
    private var primaryLogic = ClawWorldObjectRuntime().logic
    private(set) var imageOffsetY: [Int: Int32] = [:]
    private(set) var adaptedDependencies: Set<UInt32> = []
    private(set) var pendingCommands: [UInt32] = []
    let audioHeap = ClawTokenHeap()
    private(set) var audio: ClawNativeAudio?
    var sceneCandidates: (() -> [ClawPlayerAttackCandidate])?
    var sceneCollisionActors: (() -> [ClawCollisionActor])?
    var sceneRandom: (() -> UInt32)?
    var sceneCheckpoint: (() -> (x: UInt32, y: UInt32))?
    var sceneImage: ((UInt32) -> UInt32)?
    var sceneSequence: ((UInt32) -> UInt32)?
    var sceneSequenceName: ((UInt32) -> String?)?
    var sceneAnimation: ((UnsafeMutablePointer<ClawPlayerLocomotion>, UInt32, UInt32, UInt32) -> UInt32)?
    var sceneProjectileCommit: (() -> Void)?
    var sceneCarryDispatch: ((UnsafeMutablePointer<ClawPlayerLocomotion>, UnsafeMutablePointer<ClawPlayerInputContext>) -> UInt32)?
    var sceneDependency: ((UnsafeMutablePointer<ClawPlayerLocomotion>, UInt32, UInt32, UInt32, UInt32) -> UInt32?)?
    private let damage: UnsafeMutablePointer<ClawPlayerDamageContext> = {
        let buffer = UnsafeMutablePointer<ClawPlayerDamageContext>.allocate(capacity: 1)
        buffer.initialize(to: ClawPlayerDamageContext())
        return buffer
    }()
    // Callback-driven target/projectile writes share this stable C buffer.
    // Its allocation avoids overlapping Swift inout accesses during re-entry.
    let attack: UnsafeMutablePointer<ClawPlayerAttackContext> = {
        let buffer = UnsafeMutablePointer<ClawPlayerAttackContext>.allocate(capacity: 1)
        buffer.initialize(to: ClawPlayerAttackContext())
        return buffer
    }()

    // MARK: - Snapshot persistence

    // Player owner only. The enclosing scene transaction must separately
    // restore the shared heap, audio owner and all callback target owners.
    struct SavedState: Codable, Equatable {
        let runtime: ClawSnapshotValue<ClawPlayerLocomotion>
        let standing: ClawSnapshotValue<ClawPlayerStandingContext>
        let input: ClawSnapshotValue<ClawPlayerInputContext>
        let powerupClock: ClawSnapshotValue<ClawPlayerPowerupContext>
        let initialization: ClawSnapshotValue<ClawPlayerInitializationContext>
        let resourceBindings: ClawSnapshotValue<ClawActorResourceBindings>
        let logic: ClawSnapshotValue<ClawWorldObjectRuntime>
        let damage: ClawSnapshotValue<ClawPlayerDamageContext>
        let attack: ClawSnapshotValue<ClawPlayerAttackContext>
        let playback: ClawAnimationPlayback.SavedState?
        let sequence: String, failure: String?
        let unresolvedDependencies: [UInt32], adaptedDependencies: [UInt32]
        let pendingCommands: [UInt32], imageOffsetY: [Int: Int32]
        let collisionMaximumStep: UInt32
    }
    func savedState() -> SavedState {
        var logic = ClawWorldObjectRuntime()
        logic.logic = primaryLogic
        return SavedState(runtime: ClawSnapshotValue(runtime), standing: ClawSnapshotValue(standing),
                          input: ClawSnapshotValue(input), powerupClock: ClawSnapshotValue(powerupClock),
                          initialization: ClawSnapshotValue(initialization), resourceBindings: ClawSnapshotValue(resourceBindings),
                          logic: ClawSnapshotValue(logic), damage: ClawSnapshotValue(damage.pointee), attack: ClawSnapshotValue(attack.pointee),
                          playback: playback?.savedState(), sequence: sequence, failure: failure,
                          unresolvedDependencies: unresolvedDependencies.sorted(), adaptedDependencies: adaptedDependencies.sorted(),
                          pendingCommands: pendingCommands, imageOffsetY: imageOffsetY, collisionMaximumStep: collision.savedMaximumStep)
    }
    func restoreState(_ value: SavedState) throws {
        // Prepare potentially failing value/resource decodes before mutation.
        let playback = try value.playback.map { try ClawAnimationPlayback(savedState: $0) }
        var collision = self.collision
        try collision.restoreMaximumStep(value.collisionMaximumStep)
        runtime = value.runtime.value
        standing = value.standing.value
        input = value.input.value
        powerupClock = value.powerupClock.value
        initialization = value.initialization.value
        resourceBindings = value.resourceBindings.value
        primaryLogic = value.logic.value.logic
        damage.pointee = value.damage.value
        attack.pointee = value.attack.value
        self.playback = playback
        self.collision = collision
        sequence = value.sequence
        failure = value.failure
        unresolvedDependencies = Set(value.unresolvedDependencies)
        adaptedDependencies = Set(value.adaptedDependencies)
        pendingCommands = value.pendingCommands
        imageOffsetY = value.imageOffsetY
        compressedDrawingCache = nil
    }

    // MARK: - Lifecycle

    deinit {
        audio?.stopOutput()
        attack.deinitialize(count: 1)
        attack.deallocate()
        damage.deinitialize(count: 1)
        damage.deallocate()
    }

    init(world: ClawWorld, assets: ClawPlayerAssets, enableAudioOutput: Bool = false, level: UInt32 = 1) throws {
        self.assets = assets
        collision = try ClawCollisionMap(world: world)
        audio = try ClawNativeAudio(root: assets.root, outputEnabled: enableAudioOutput, sharedHeap: audioHeap, level: level)
        guard let plane = world.planes.first(where: { $0.flags & 1 != 0 }) else {
            throw AssetError.invalid("Missing player collision plane")
        }
        let entry = "CaptainClaw".withCString { claw_logic_registry_find($0)!.pointee }
        var object = ClawWorldObjectRuntime()
        var context = ClawWorldObjectContext()
        // Native identities represent ownership; they are not original heap addresses.
        context.sceneToken = 0x10001000
        context.sceneDefaultType = 0x60003000
        context.actorToken = 0x10002000
        context.logicToken = 0x10003000
        context.entryToken = entry.registrationOrdinal
        context.entryCallback = entry.callback
        context.entryFlags = entry.flags
        // Original player caller46b41f supplies ID1,320/350/Z100,flags40002
        // before invoking CaptainClaw state0, which places the world spawn.
        claw_world_object_construct(&object, &context, 1)
        object.actor.2 = 0x40002
        guard claw_world_object_initialize(&object, &context, 320, 350, 100) == 1 else {
            throw AssetError.invalid("Cannot initialize CaptainClaw actor")
        }
        runtime.actor = object.actor
        primaryLogic = object.logic
        claw_physics_construct(&runtime.physics)
        initialization.worldWidth = UInt32(plane.width * plane.tileWidth)
        initialization.worldHeight = UInt32(plane.height * plane.tileHeight)
        audio?.routing.sceneWidth = UInt32(plane.width * plane.tileWidth)
        audio?.routing.playerPresent = 1
        runtime.audioPosition = audio?.routing.masterVolume ?? 0
        initialization.startX = UInt32(world.startX)
        initialization.startY = UInt32(world.startY)
        initialization.checkpointX = .max
        initialization.checkpointY = .max
        initialization.configurationToken = 0x10004000
        damage.pointee.configurationToken = initialization.configurationToken
        damage.pointee.windowToken = 1
        for index in 0..<7 {
            let id = 383 + index
            claw_player_set_initialization_image_word(&initialization, UInt32(index),
                                                      assets.sprites[id] == nil ? 0 : UInt32(id + 1),
                                                      UInt32(bitPattern: Int32(assets.sprites[id]?.offsetY ?? 0)))
        }
        claw_v13_player_construct_defaults(&runtime, &initialization)
        var startup = initialization, startupInput = input
        invoke { _ = claw_player_dispatch_initialization($0, &startup, &startupInput, nativePlayerDependency, $1) }
        initialization = startup
        input = startupInput
        for index in 0..<7 where assets.sprites[383 + index] != nil {
            imageOffsetY[383 + index] = Int32(bitPattern: claw_player_initialization_image_word(&initialization, UInt32(index)))
        }
        if let failure {
            throw AssetError.invalid(failure)
        }
    }

    // MARK: - Scene state exchange

    var x: Int32 { Int32(bitPattern: claw_player_actor_word(&runtime, 0x4c)) }
    var y: Int32 { Int32(bitPattern: claw_player_actor_word(&runtime, 0x50)) }
    var z: Int32 { Int32(bitPattern: claw_player_actor_word(&runtime, 0x64)) }
    var imageID: Int { Int(claw_player_actor_word(&runtime, 0x16c)) }
    var mirrored: Bool { claw_player_actor_word(&runtime, 0x40) & 2 != 0 }
    var mode: UInt32 { claw_player_actor_word(&runtime, 0xcc) }

    // Scene heap and scanner carry full logic snapshots, not just the state ID.
    func sceneSnapshot() -> ClawInteractionActor {
        var snapshot = ClawInteractionActor()
        snapshot.token = 0x10002000
        snapshot.actor = runtime.actor
        primaryLogic.7 = runtime.logicState
        primaryLogic.8 = damage.pointee.logicWord20
        primaryLogic.5 = initialization.privateToken
        primaryLogic.11 = input.minimumX
        primaryLogic.12 = input.maximumX
        primaryLogic.13 = input.minimumY
        primaryLogic.14 = input.maximumY
        primaryLogic.76 = input.invulnerabilityTimer
        snapshot.primary = primaryLogic
        snapshot.secondary = resourceBindings.secondary
        return snapshot
    }

    func acceptSceneSnapshot(_ snapshot: ClawInteractionActor, physics: ClawPlayerPhysics? = nil,
                             privateWords: UnsafePointer<UInt32>? = nil) {
        runtime.actor = snapshot.actor
        primaryLogic = snapshot.primary
        if let physics {
            runtime.physics = physics
        }
        if let privateWords {
            withUnsafeMutableBytes(of: &runtime.privateWords) {
                $0.copyMemory(from: UnsafeRawBufferPointer(start: privateWords, count: 312))
            }
        }
        runtime.logicState = primaryLogic.7
        damage.pointee.logicWord20 = primaryLogic.8
        input.minimumX = primaryLogic.11
        input.maximumX = primaryLogic.12
        input.minimumY = primaryLogic.13
        input.maximumY = primaryLogic.14
        input.invulnerabilityTimer = primaryLogic.76
        resourceBindings.actor = snapshot.actor
        resourceBindings.secondary = snapshot.secondary
        if let name = sceneSequenceName?(snapshot.actor.100) {
            sequence = name
        }
    }

    func acceptRuntimeSnapshot(_ value: ClawPlayerLocomotion) {
        runtime = value
        primaryLogic.7 = value.logicState
        resourceBindings.actor = value.actor
    }
    func drainPendingCommands() -> [UInt32] {
        let result = pendingCommands
        pendingCommands.removeAll(keepingCapacity: true)
        return result
    }
    func returnPendingCommands(_ values: [UInt32]) { pendingCommands.insert(contentsOf: values, at: 0) }
    func postCommand(_ value: UInt32) { pendingCommands.append(value) }

    func recordDrawingState(_ actor: ClawSpriteDrawActor) {
        for (offset, value) in [(UInt32(0x40), actor.renderFlags), (0x44, actor.blinkRemaining),
                                (0x18, actor.drawX), (0x1c, actor.drawY), (0x20, actor.drawn.left),
                                (0x24, actor.drawn.top), (0x28, actor.drawn.right), (0x2c, actor.drawn.bottom),
                                (0x30, actor.drawWidth), (0x34, actor.drawHeight), (0x38, actor.drawStatus)] {
            claw_player_set_actor_word(&runtime, offset, value)
        }
    }

    // MARK: - Player updates

    func advance(direction: Int, vertical: Int = 0, jumpHeld: Bool = false, jumpPressed: Bool = false,
                 stageDelta: UInt32, animationDelta: UInt32) {
        var held: UInt32 = direction > 0 ? 0x02000000 : direction < 0 ? 0x01000000 : 0
        if jumpHeld {
            held |= 1
        }
        if vertical < 0 {
            held |= 0x04000000
        }
        if vertical > 0 {
            held |= 0x08000000
        }
        let pressed = (held & ~runtime.inputHeld) | (jumpPressed ? 1 : 0)
        advance(held: held, pressed: pressed, stageDelta: stageDelta, animationDelta: animationDelta)
    }

    func advance(held: UInt32, pressed: UInt32, stageDelta: UInt32, animationDelta: UInt32) {
        runtime.stageDelta = stageDelta
        runtime.animationDelta = animationDelta
        runtime.inputHeld = held
        input.pressed = pressed
        audio?.routing.defaultReferenceX = UInt32(bitPattern: x)
        audio?.routing.playerLogicState = runtime.logicState
        attack.pointee.pressed = pressed
        var context = input, initial = initialization
        if let checkpoint = sceneCheckpoint?() {
            initial.checkpointX = checkpoint.x
            initial.checkpointY = checkpoint.y
        }
        invoke {
            if $0.pointee.logicState == 0 || $0.pointee.logicState == 23 {
                _ = claw_player_dispatch_initialization($0, &initial, &context, nativePlayerDependency, $1)
            } else if [UInt32(28), 31, 5004, 5005].contains($0.pointee.logicState) {
                _ = claw_player_dispatch_damage($0, damage, &context, nativePlayerDependency, $1)
            } else if [UInt32(5000), 5001].contains($0.pointee.logicState), let sceneCarryDispatch {
                _ = sceneCarryDispatch($0, &context)
            } else {
                _ = claw_player_dispatch_input($0, &context, nativePlayerDependency, $1)
            }
        }
        input = context
        initialization = initial
    }

    // The generic hit scanner must elect this callback and supply the matching
    // attacker. There is deliberately no additional guessed immunity gate.
    func receiveHit(from attacker: inout ClawWorldObjectRuntime, token: UInt32) {
        damage.pointee.attackerToken = token
        damage.pointee.attackerActor = attacker.actor
        claw_player_set_actor_word(&runtime, 0x74, token)
        var context = input
        invoke { _ = claw_player_hit($0, damage, &context, nativePlayerDependency, $1) }
        input = context
        attacker.actor = damage.pointee.attackerActor
    }

    private func invoke(_ body: (UnsafeMutablePointer<ClawPlayerLocomotion>, UnsafeMutableRawPointer) -> Void) {
        // The synchronous source call borrows both self and this runtime pointer.
        // Callbacks must use the supplied state rather than re-enter runtime.
        let context = Unmanaged.passUnretained(self).toOpaque()
        withUnsafeMutablePointer(to: &runtime) { body($0, context) }
    }

    // MARK: - Recovered dispatch and native services

    // Entry values are stable source dispatch identities. Scene services get
    // first refusal; standalone adapters below retain their original order.
    func dependency(_ state: UnsafeMutablePointer<ClawPlayerLocomotion>,
                    entry: UInt32, a: UInt32, b: UInt32, c: UInt32) -> UInt32 {
        if let result = sceneDependency?(state, entry, a, b, c) {
            return result
        }
        if [UInt32(0x4c79e0), 0x4c8220, 0x4c8260, 0x420a10, 0x420970, 0x4c82a0].contains(entry), let sceneAnimation {
            let result = sceneAnimation(state, entry, a, b)
            if let name = sceneSequenceName?(claw_player_actor_word(state, 0x190)) {
                sequence = name
            }
            return result
        }
        switch entry {
        case 0x417b00:
            claw_player_enter_fall_death(state, damage, a, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x417c50:
            claw_player_enter_spike_death(state, damage, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x546d50:
            // Original PostMessageA is asynchronous. The original command
            // host consumes this queue outside the damage callback.
            if b == 0x111 {
                pendingCommands.append(c)
            }
            adaptedDependencies.insert(entry)
            return 1
        case 0x4f63ec:
            // The host owns the fixed private-state allocation already.
            adaptedDependencies.insert(entry)
            return 0x10005000
        case 0x10:
            // Normal configuration mode; menu/configuration recovery is pending.
            adaptedDependencies.insert(entry)
            return 0
        case 0x4bc110:
            return 0 // Pinned original entry is a single RET; it stops no voices.
        case 0x4cd800:
            var actor = collisionActor(state)
            let result = collision.placeOnGround(actor: &actor)
            copyCollision(actor, into: state)
            return result
        case 0x4c7900, 0x4c7fa0:
            return bindResource(state, entry: entry, nameAddress: a, index: b)
        case 0x40f680:
            return a == 0x10007000 && assets.sprites[Int(b)] != nil ? b &+ 1 : 0
        case 0x4171d0:
            return claw_player_enter_stand(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
        case 0x417dd0:
            claw_player_enter_walk_left(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x417f20:
            claw_player_enter_walk_right(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x417590:
            claw_player_enter_jump(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x417930:
            claw_player_enter_fall(state, a, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x41c4e0:
            claw_player_cleanup_move(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x4170f0:
            claw_player_enter_climb(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x417380:
            claw_player_enter_attack_stand(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x41c5a0:
            claw_player_update_attack(state, attack, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            sceneProjectileCommit?()
            return 0
        case 0x4183e0:
            claw_player_update_walk_right(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x418790:
            claw_player_update_walk_left(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x41b630:
            claw_player_update_jump(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x418b40:
            claw_player_update_fall(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x419030:
            standing.inputPressed = input.pressed
            claw_player_update_stand(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque(), &standing)
            return 0
        case 0x419c80:
            claw_player_update_stand_edge(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x41bb70:
            var air = ClawPlayerAirInput(pressed: input.pressed)
            claw_player_update_climb(state, &air, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x4198d0:
            claw_player_update_land(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x419fd0:
            var pose = ClawPlayerPoseContext(inputPressed: input.pressed)
            claw_player_update_duck(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque(), &pose)
            return 0
        case 0x41a490:
            claw_player_update_lookup(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x41f4c0:
            claw_player_update_jump_hold(state)
            return 0
        case 0x41e710:
            return claw_player_left_ledge(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
        case 0x41e790:
            return claw_player_right_ledge(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
        case 0x417480:
            return UInt32(bitPattern: claw_player_enter_teeter(state, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque()))
        case 0x41fc30:
            claw_player_update_powerup_timer(state, &powerupClock, a, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
            return 0
        case 0x4cd1c0:
            let attribute = collision.footAttribute(x: claw_player_actor_word(state, 0x4c),
                                                    y: claw_player_actor_word(state, 0x50), bottom: claw_player_actor_word(state, 0x124) &+ 1, xOffset: a)
            return [UInt32(1), 2, 3].contains(attribute) ? 1 : 0
        case 0x4cd740:
            return collision.footAttribute(x: claw_player_actor_word(state, 0x4c),
                                           y: claw_player_actor_word(state, 0x50), bottom: claw_player_actor_word(state, 0x124), xOffset: a)
        case 0x4a3050:
            if let sceneRandom {
                return sceneRandom()
            }
            standing.randomState = standing.randomState &* 214013 &+ 2531011
            return (standing.randomState >> 16) & 0x7fff
        case 0x4bb030:
            return 0
        case 0x41d850:
            return claw_player_select_attack(state, attack, nativePlayerDependency, Unmanaged.passUnretained(self).toOpaque())
        case 0x41d750:
            let candidates = sceneCandidates?() ?? []
            return candidates.withUnsafeBufferPointer {
                UInt32(bitPattern: claw_player_nearest_attack_target(state, attack, $0.baseAddress, UInt32($0.count)))
            }
        case 0x4c79e0:
            guard let name = assets.sequenceNames[a] else {
                unresolvedDependencies.insert(entry)
                return 0
            }
            do {
                let retained = animationActor(state)
                playback = try assets.playback(name: name, startImmediately: false)
                playback?.synchronize(actor: retained, rate: 1)
                sequence = name
                copyAnimationState(state, token: a)
                if b != 0 {
                    advanceAnimation(state, delta: state.pointee.animationDelta)
                }
                return 1
            } catch {
                failure = String(describing: error)
                return 0
            }
        case 0x4c82a0:
            advanceAnimation(state, delta: a)
            return playback?.result ?? 0
        case 0x4cbb60:
            var actor = collisionActor(state)
            let result = collision.move(actor: &actor, x: a, y: b, options: c, otherActors: sceneCollisionActors?() ?? [])
            copyCollision(actor, into: state)
            return result
        case 0x4f6286, 0x4061b0:
            if assets.sequenceNames[a] != nil {
                return sceneSequence?(a) ?? a
            }
            guard let name = clawOriginalResourceNames[a] else {
                return 0
            }
            return audio?.resolve(name: name)?.resourceToken ?? 0
        case 0x420910:
            guard let name = clawOriginalResourceNames[a] else {
                return 0
            }
            return audio?.play(name: name) ?? 0
        case 0x4208e0:
            if let name = clawOriginalResourceNames[a], let sound = audio?.resolve(name: name) {
                return audio?.play(resource: sound.resourceToken, volume: b) ?? 0
            }
            return audio?.play(resource: a, volume: b) ?? 0
        case 0x4209d0:
            guard assets.images[Int(a)] != nil else {
                failure = "Missing player image \(a)"
                return 0
            }
            claw_player_set_actor_word(state, 0x16c, a)
            claw_player_set_actor_word(state, 0x174, sceneImage?(a) ?? a &+ 1)
            return 0
        case 0x4207f0:
            return collision.footAttribute(x: a, y: b, bottom: 0, xOffset: 0)
        case 0x4c8220, 0x420a10:
            guard assets.sequenceNames[a] != nil else {
                unresolvedDependencies.insert(entry)
                return 0
            }
            return dependency(state, entry: 0x4c79e0, a: a, b: b, c: c)
        default:
            unresolvedDependencies.insert(entry)
            return 0
        }
    }

    // MARK: - Resource, animation and collision adapters

    private func animationActor(_ state: UnsafePointer<ClawPlayerLocomotion>) -> ClawAnimationActor {
        ClawAnimationActor(imageID: claw_player_actor_word(state, 0x16c),
                           imageToken: claw_player_actor_word(state, 0x174), flags: claw_player_actor_word(state, 0x40),
                           x: claw_player_actor_word(state, 0x4c), y: claw_player_actor_word(state, 0x50),
                           moveX: claw_player_actor_word(state, 0x10), moveY: claw_player_actor_word(state, 0x14))
    }

    private func bindResource(_ state: UnsafeMutablePointer<ClawPlayerLocomotion>,
                              entry: UInt32, nameAddress: UInt32, index: UInt32) -> UInt32 {
        let name: String
        if entry == 0x4c7900 && nameAddress == 0x523734 {
            name = "CLAW"
        }
        else if entry == 0x4c7fa0 && nameAddress == 0x522e70 {
            name = "CaptainClawHit"
        }
        else {
            unresolvedDependencies.insert(entry)
            return 0
        }
        var binding = resourceBindings
        binding.actor = state.pointee.actor
        var context = ClawActorBindingContext()
        context.imageRegistryToken = 0x10008000
        context.logicRegistryToken = 0x10009000
        let minimum = assets.images.keys.min() ?? 0, maximum = assets.images.keys.max() ?? 0
        let tokens = (minimum...maximum).map { assets.images[$0] == nil ? UInt32(0) : (sceneImage?(UInt32($0)) ?? UInt32($0 + 1)) }
        let user = Unmanaged.passUnretained(self).toOpaque()
        let result = tokens.withUnsafeBufferPointer { frames -> UInt32 in
            context.image = ClawActorImageBinding(token: 0x10007000,
                                                  minimum: Int32(minimum), maximum: Int32(maximum), firstImageIndex: Int32(minimum),
                                                  images: frames.baseAddress, imageCount: frames.count)
            return name.withCString {
                if entry == 0x4c7900 {
                    return claw_actor_bind_indexed_image(&binding, &context, $0, Int32(bitPattern: index), nativePlayerBindingDependency, user)
                }
                return claw_actor_bind_secondary_logic_name(&binding, &context, $0, nativePlayerBindingDependency, user)
            }
        }
        state.pointee.actor = binding.actor
        resourceBindings = binding
        if result == 0 {
            failure = "Cannot bind player resource \(name)"
        }
        return result
    }

    fileprivate func bindingDependency(_ context: UnsafeMutablePointer<ClawActorBindingContext>,
                                       call: UnsafePointer<ClawActorBindingCall>) -> UInt32 {
        let event = call.pointee
        switch event.function {
        case 0x4f6286:
            guard let name = event.name else {
                return 0
            }
            if event.receiver == context.pointee.imageRegistryToken {
                return String(cString: name) == "CLAW" ? context.pointee.image.token : 0
            }
            guard let metadata = claw_logic_registry_find(name) else {
                return 0
            }
            context.pointee.metadataCallback = metadata.pointee.callback
            context.pointee.metadataFlags = metadata.pointee.flags
            return metadata.pointee.registrationOrdinal
        case 0x4f63ec:
            adaptedDependencies.insert(event.function)
            return 0x10006000
        default:
            unresolvedDependencies.insert(event.function)
            return 0
        }
    }

    private func advanceAnimation(_ state: UnsafeMutablePointer<ClawPlayerLocomotion>, delta: UInt32) {
        guard playback != nil else {
            return
        }
        playback?.synchronize(actor: animationActor(state), rate: Float(bitPattern: claw_player_actor_word(state, 0x1b0)))
        playback?.update(delta: delta, masterVolume: audio?.routing.masterVolume ?? 0)
        if let event = playback?.event, event.dispatched != 0,
           let name = playback?.eventNames[event.event] {
            _ = audio?.play(name: name, sourceX: event.spatial != 0 ? event.position : nil)
        }
        guard let actor = playback?.actor else {
            return
        }
        for (offset, value) in [(UInt32(0x16c), actor.imageID), (0x174, actor.imageToken), (0x40, actor.flags),
                                (0x4c, actor.x), (0x50, actor.y), (0x10, actor.moveX), (0x14, actor.moveY)] {
            claw_player_set_actor_word(state, offset, value)
        }
        copyAnimationState(state, token: claw_player_actor_word(state, 0x190))
    }

    private func copyAnimationState(_ state: UnsafeMutablePointer<ClawPlayerLocomotion>, token: UInt32) {
        guard let animation = playback?.state else {
            return
        }
        for (offset, value) in [(UInt32(0x190), token), (0x198, UInt32(bitPattern: animation.recordIndex)),
                                (0x19c, animation.remaining), (0x1a0, animation.timed), (0x1a4, animation.stopped),
                                (0x1a8, animation.code), (0x1ac, animation.previousCode), (0x1b0, animation.rate.bitPattern)] {
            claw_player_set_actor_word(state, offset, value)
        }
    }

    private func collisionActor(_ state: UnsafePointer<ClawPlayerLocomotion>) -> ClawCollisionActor {
        func word(_ byteOffset: UInt32) -> UInt32 { claw_player_actor_word(state, byteOffset) }
        func rect(_ byteOffset: UInt32) -> ClawPlayerRect {
            ClawPlayerRect(left: word(byteOffset), top: word(byteOffset + 4), right: word(byteOffset + 8), bottom: word(byteOffset + 12))
        }
        return ClawCollisionActor(flags: word(8), x: word(0x4c), y: word(0x50), mode: word(0xcc),
                                  type: word(0xd0), stepX: word(0xdc), stepY: word(0xe0), supportToken: word(0x80), token: 0x10002000,
                                  deltaX: word(0x158), deltaY: word(0x15c), moveRect: rect(0x118), hitRect: rect(0x128))
    }

    private func copyCollision(_ actor: ClawCollisionActor, into state: UnsafeMutablePointer<ClawPlayerLocomotion>) {
        for (offset, value) in [(UInt32(8), actor.flags), (0x4c, actor.x), (0x50, actor.y), (0xcc, actor.mode),
                                (0x80, actor.supportToken), (0x158, actor.deltaX), (0x15c, actor.deltaY)] {
            claw_player_set_actor_word(state, offset, value)
        }
    }
}

extension ClawPlayerLocomotion: ClawSnapshotNativeValue {}
extension ClawPlayerStandingContext: ClawSnapshotNativeValue {}
extension ClawPlayerInputContext: ClawSnapshotNativeValue {}
extension ClawPlayerPowerupContext: ClawSnapshotNativeValue {}
extension ClawPlayerInitializationContext: ClawSnapshotNativeValue {}
extension ClawActorResourceBindings: ClawSnapshotNativeValue {}
extension ClawWorldObjectRuntime: ClawSnapshotNativeValue {}
extension ClawPlayerDamageContext: ClawSnapshotNativeValue {}
extension ClawPlayerAttackContext: ClawSnapshotNativeValue {}

private let nativePlayerDependency: ClawPlayerLocomotionDependency = { state, entry, a, b, c, context in
    guard let state, let context else {
        return 0
    }
    return Unmanaged<ClawNativePlayer>.fromOpaque(context).takeUnretainedValue()
        .dependency(state, entry: entry, a: a, b: b, c: c)
}

private let nativePlayerBindingDependency: ClawActorBindingDependency = { _, bindingContext, call, user in
    guard let bindingContext, let call, let user else {
        return 0
    }
    return Unmanaged<ClawNativePlayer>.fromOpaque(user).takeUnretainedValue()
        .bindingDependency(bindingContext, call: call)
}
