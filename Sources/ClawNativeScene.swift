import Foundation

// Recovered scheduling, input/camera and hit scanning share one token heap.
// Physical input/resources and unsupported WWD gameplay remain adapters.
final class ClawNativeScene {
    // MARK: - Scene storage and service owners

    let player: ClawNativePlayer
    let heap: ClawTokenHeap
    let windowInput: ClawNativeWindowInput?
    private(set) var windowReceiver: UInt32 = 0
    let containerToken: UInt32 = 0x60000000
    private let parentToken: UInt32 = 0x10001000
    private let ownerToken: UInt32 = 0x60002000
    private let mapToken: UInt32 = 0x60003000
    private let globals = UnsafeMutablePointer<ClawSceneActorGlobals>.allocate(capacity: 1)
    private let stage = UnsafeMutablePointer<ClawSceneStageState>.allocate(capacity: 1)
    private let readClock: () -> UInt32
    private let faultStorage = UnsafeMutablePointer<UInt32>.allocate(capacity: 1)
    private let destruction = UnsafeMutablePointer<ClawActorDestructionGlobals>.allocate(capacity: 1)
    private let core = UnsafeMutablePointer<ClawCoreRegistrationGlobals>.allocate(capacity: 1)
    private var held: UInt32 = 0, pressed: UInt32 = 0
    var fault: UInt32 { faultStorage.pointee }
    private(set) var unresolvedDependencies: Set<UInt32> = []
    private(set) var adaptedDependencies: Set<UInt32> = []
    private(set) var lastPassCount: UInt32 = 0
    private(set) var animationCounts: [UInt32: UInt64] = [:]
    // Only callbacks with real recovered implementations should be installed.
    var gameplay: [UInt32: (UInt32) -> Void] = [:]
    private(set) var objectConnections: ClawNativeObjectConnections?
    private var objectAllocationOwners: [ClawSceneObjectAllocationOwner] = []
    private(set) var enemies: [UInt32: ClawNativeEnemy] = [:]
    private(set) var humanoids: [UInt32: ClawNativeHumanoid] = [:]
    private(set) var bullets: [UInt32: ClawNativeBullet] = [:]
    private(set) var effects: ClawNativeEffects?
    private(set) var loot: ClawNativeLoot?
    private(set) var speech: ClawNativeSpeech?
    private(set) var platforms: ClawNativePlatforms?
    private(set) var pegs: ClawNativePegs?
    private(set) var soundTriggers: ClawNativeSoundTriggers?
    private(set) var singleCrates: ClawNativeSingleCrates?
    private(set) var checkpoints: ClawNativeCheckpoints?
    private(set) var ambientAudio: ClawNativeAmbientAudio?
    private(set) var curses: ClawNativeCurses?
    private(set) var specialPowerups: ClawNativeSpecialPowerups?
    private(set) var saves: ClawNativeSave?
    private(set) var statusMessages: ClawNativeStatusMessages?
    private(set) var hud: ClawNativeHUD?
    private(set) var projectiles: ClawNativeProjectiles?
    private(set) var flares: ClawNativeFlare?
    private(set) var palettes: ClawNativeLightPalette?
    private(set) var paletteResources: ClawNativePaletteResources?
    var playerPowerupGlobals: UnsafeMutablePointer<ClawPlayerPowerupGlobals>? { playerServices?.powerupGlobals }
    private(set) var breakables: ClawNativeBreakables?
    private(set) var carry: ClawNativeCarry?
    var coreGlobals: UnsafeMutablePointer<ClawCoreRegistrationGlobals> { core }
    private(set) var sceneryTokens: Set<UInt32> = []
    // Reviewed Level 1 class roots; reporting metadata does not establish app traces.
    // claw-progress-class-owner: scenery_logic 0x461730 0x461770 0x4617d0 0x4618e0 0x461970
    private static let sceneryCallbacks: Set<UInt32> = [0x461730, 0x461750, 0x461770, 0x4617d0, 0x461830, 0x461870, 0x4618e0, 0x461970]
    private var pendingPickupTokens: Set<UInt32> = []
    private(set) var objectResources: ClawActorResources?
    private(set) var stateRegistry: ClawNativeStateRegistry?
    private(set) var rendering: ClawNativeRendering?
    private(set) var frameRuntime: ClawNativeFrame?
    private(set) var respawn: ClawNativeRespawn?
    private var playerServices: ClawNativePlayerServices?
    private(set) var fadeRequests: [ClawSceneActorCall] = []
    private(set) var camera: ClawNativeCamera?
    private(set) var cameraActorToken: UInt32 = 0
    private(set) var uninstantiatedObjectCount = 0
    private(set) var uninstantiatedLogics: [String: Int] = [:]
    private var loadingWorld: ClawWorld?
    private var recordsByToken: [UInt32: ClawWorld.Object] = [:]
    private(set) var spatialCalls: [UInt32: UInt64] = [:]
    private(set) var objectLoadingFailure: String?
    private var registryEntries: [String: UInt32] = [:], namesByToken: [UInt32: String] = [:]
    private var bumpLogics: [UInt32: ClawNativeBumpLogic] = [:]
    private var bumpPeers: [UInt32: UInt32] = [:]
    private(set) var random: ClawNativeRandom!
    private var clockSnapshot = ClawClockState()
    private var snapshotFrameDepth = 0
    var sceneIdentity: UInt32 { parentToken }
    var worldIdentity: UInt32 { mapToken }
    var ownerIdentity: UInt32 { ownerToken }
    // The canonical callback and scene destruction share the same holder state.
    var objectDestructionGlobals: ClawActorDestructionGlobals {
        get { destruction.pointee }
        set { destruction.pointee = newValue }
    }
    // Source clocks stay separate: accumulated stage time and the two frame
    // deltas can be reset independently by gameplay services.
    var gameTime: UInt32 { stage.pointee.accumulatedMilliseconds }
    var animationDelta: UInt32 { globals.pointee.animation.deltaMilliseconds }
    var stageDelta: UInt32 { stage.pointee.stage.deltaMilliseconds }

    // MARK: - Scene construction and teardown

    init(
        player: ClawNativePlayer, windowInput: ClawNativeWindowInput? = ClawNativeWindowInput(),
        clock: @escaping () -> UInt32 = {
            UInt32(truncatingIfNeeded: UInt64(ProcessInfo.processInfo.systemUptime * 1000))
        }
    ) {
        heap = player.audioHeap
        self.player = player
        self.windowInput = windowInput
        readClock = clock
        faultStorage.initialize(to: 0)
        destruction.initialize(to: ClawActorDestructionGlobals(holderActorToken: 0, heldActorToken: 0, emptyStringToken: 0x52e1c4))
        core.initialize(to: ClawCoreRegistrationGlobals())
        claw_core_registration_defaults(core)
        globals.initialize(to: ClawSceneActorGlobals())
        stage.initialize(to: ClawSceneStageState())
        globals.pointee.animation.nowMilliseconds = clock()
        stage.pointee.playerToken = 0x10002000
        let container = heap.store(token: containerToken, words: 11)
        container[0] = 0x513c20
        container[3] = parentToken
        container[4] = 0x5107bc
        container[10] = 10
        let parent = heap.store(token: parentToken, words: 15)
        // Original 60-byte scene constructor. Later managers are joined
        // incrementally; complete 4cea10 startup remains separately scoped.
        var sourceSceneGlobals = ClawSinglePlayerSceneGlobals(), sourceCameraGlobals = ClawSceneCameraGlobals(),
            sourceSceneContext = ClawSinglePlayerSceneContext(), sourceSceneResult: UInt32 = 0
        sourceSceneContext.host = ClawSceneActorHost(
            context: Unmanaged.passUnretained(heap).toOpaque(),
            lookup: { u, t, n in
                guard let u else { return nil }
                return Unmanaged<ClawTokenHeap>.fromOpaque(u).takeUnretainedValue().lookup(t, words: n)
            }, allocate: nil, free: nil, call: nil, readClock: nil)
        let sourceSceneBuilt = withUnsafeMutablePointer(to: &sourceSceneGlobals) { g in
            withUnsafeMutablePointer(to: &sourceCameraGlobals) { camera in
                sourceSceneContext.globals = g
                sourceSceneContext.camera = camera
                return claw_single_player_scene_entry(0x4ce960, parentToken, nil, 0, &sourceSceneContext, nil, nil, &sourceSceneResult) == 1
                    && sourceSceneContext.fault == 0 && sourceSceneResult == parentToken
            }
        }
        precondition(sourceSceneBuilt)
        parent[2] = containerToken
        parent[9] = mapToken
        // Canonical object owners pin this physical dictionary header. Give it
        // scene lifetime: the old symbolic 0x62000000 could land inside the
        // temporary decoded WWD buffer and disappear when loading completed.
        parent[5] = heap.allocate(bytes: 20)
        parent[11] = 0x63000000
        heap.store(token: ownerToken, words: 478)[3] = parentToken
        _ = heap.store(token: mapToken, words: 56)
        // Canonical object joins pin the player's private behavior as a full
        // logic record; the player snapshot imports its first 78 words.
        _ = heap.store(token: 0x10005000, words: 93)
        // Original shared CString header at 0x52e1b8 and empty data at 0x52e1c4.
        heap.store(token: 0x52e1b8, words: 4)[0] = .max
        heap.store(token: 0x52e1cc, words: 1)[0] = 0x52e1c4
        _ = heap.store(token: 0x541328, words: 5)
        _ = heap.store(token: 0x53c260, words: 1)
        for (token, words) in clawLifecycleVTables {
            let target = heap.store(token: token, words: words.count)
            words.withUnsafeBufferPointer { target.update(from: $0.baseAddress!, count: $0.count) }
        }
        // BossStager's binary64 1.5 overlaps the trailing zero word of the
        // breakable lifecycle table. Publish both in one physical allocation
        // before breakable setup can claim the shorter source table alone.
        let stagerConstants = clawBreakableVTables[0x50f874]! + [0x3ff80000]
        let stagerSpan = heap.store(token: 0x50f874, words: stagerConstants.count)
        stagerConstants.withUnsafeBufferPointer { stagerSpan.update(from: $0.baseAddress!, count: $0.count) }
        // Object adapters and projectiles share source-image words, including
        // constants inside these tables. Publish the complete spans before WWD
        // attachment can claim a smaller overlapping span.
        for (token, words) in clawPlayerProjectileVTables {
            let target = heap.store(token: token, words: words.count)
            words.withUnsafeBufferPointer { target.update(from: $0.baseAddress!, count: $0.count) }
        }
        random = ClawNativeRandom(heap: heap)
        precondition(random.initialized && random.fault == 0)
        if let windowInput {
            windowReceiver = heap.allocate(bytes: 8)
            heap.lookup(windowReceiver, words: 2)![1] = windowInput.window
        }
        adopt(player.sceneSnapshot())
        player.sceneCandidates = { [weak self] in
            self?.actorTokens.compactMap { token in
                guard token != 0x10002000, let snapshot = self?.snapshotActor(token) else { return nil }
                var value = ClawPlayerAttackCandidate()
                value.token = token
                value.actor = snapshot.actor
                return value
            } ?? []
        }
        player.sceneCollisionActors = { [weak self] in self?.collisionActors(excluding: 0x10002000) ?? [] }
        player.collision.contactActors = { [weak self] in self?.proposedContactActors() ?? [] }
        player.collision.contactContext = Unmanaged.passUnretained(self).toOpaque()
        player.collision.contactCallback = { records, count, index, user in
            guard let records, let user, index < count else { return 0 }
            let scene = Unmanaged<ClawNativeScene>.fromOpaque(user).takeUnretainedValue()
            let record = records[Int(index)]
            scene.bumpPeers[record.actor.token] = record.otherToken
            return scene.bumpLogics[record.actor.token]?.invoke() ?? 0
        }
        player.collision.publishContacts = { [weak self] records in
            guard let self else { return }
            for record in records { self.bumpPeers[record.actor.token] = record.otherToken }
        }
        player.sceneRandom = { [weak self] in self?.nextRandom() ?? 0 }
        player.sceneCheckpoint = { [weak self] in
            guard let self, let owner = self.heap.lookup(self.ownerIdentity, words: 19) else { return (.max, .max) }
            return (owner[0x44 / 4], owner[0x48 / 4])
        }
    }
    deinit {
        globals.deinitialize(count: 1)
        globals.deallocate()
        stage.deinitialize(count: 1)
        stage.deallocate()
        faultStorage.deinitialize(count: 1)
        faultStorage.deallocate()
        destruction.deinitialize(count: 1)
        destruction.deallocate()
        core.deinitialize(count: 1)
        core.deallocate()
    }

    // MARK: - Borrowed heap and service callbacks

    // The C host borrows this scene. Lookup results point into its heap;
    // callback context does not transfer Swift ownership to recovered code.
    private var host: ClawSceneActorHost {
        ClawSceneActorHost(
            context: Unmanaged.passUnretained(self).toOpaque(),
            lookup: { context, token, words in
                guard let context else { return nil }
                return Unmanaged<ClawNativeScene>.fromOpaque(context).takeUnretainedValue().heap.lookup(token, words: words)
            },
            allocate: { context, bytes in
                guard let context else { return 0 }
                return Unmanaged<ClawNativeScene>.fromOpaque(context).takeUnretainedValue().heap.allocate(bytes: bytes)
            },
            free: { context, token in
                guard let context else { return }
                Unmanaged<ClawNativeScene>.fromOpaque(context).takeUnretainedValue().freeActorStorage(token)
            },
            call: { context, call in
                guard let context else { return 0 }
                return Unmanaged<ClawNativeScene>.fromOpaque(context).takeUnretainedValue().dispatch(call)
            },
            readClock: { context in
                guard let context else { return 0 }
                return Unmanaged<ClawNativeScene>.fromOpaque(context).takeUnretainedValue().readClock()
            })
    }

    var actorHost: ClawSceneActorHost { host }

    // Canonical enemy release 48cf50 and the existing actor-destruction
    // owner share the holder/held globals, including source writes.

    // MARK: - Actor ownership and destruction

    func synchronizeObjectDestructionGlobals(toHeap: Bool) -> Bool {
        guard let words = heap.lookup(0x53c9ac, words: 2) else { return false }
        if toHeap {
            words[0] = destruction.pointee.holderActorToken
            words[1] = destruction.pointee.heldActorToken
        } else {
            destruction.pointee.holderActorToken = words[0]
            destruction.pointee.heldActorToken = words[1]
        }
        return true
    }

    // Explicit opt-in for canonical constructors sharing this scene's heap.
    // Retain the physical owner for at least as long as the scene's actors.
    @discardableResult func registerObjectAllocationOwner(_ memory: ClawSceneObjectAllocationOwner) -> Bool {
        guard fault == 0, memory.sceneObjectHeap === heap, memory.canRegisterSceneObjectOwner,
            !objectAllocationOwners.contains(where: { $0 === memory })
        else { return false }
        objectAllocationOwners.append(memory)
        return true
    }

    private func freeActorStorage(_ token: UInt32) {
        bumpLogics.removeValue(forKey: token)
        bumpPeers.removeValue(forKey: token)
        guard !objectAllocationOwners.isEmpty else {
            heap.free(token)
            return
        }
        // CRT free(NULL) is valid. Every non-null scene free must retire a base.
        guard token != 0 else { return }
        let owners = objectAllocationOwners.filter { $0.claimsSceneObject(token) }
        if !owners.isEmpty {
            guard owners.count == 1, owners[0].releaseSceneObject(token) else {
                faultStorage.pointee = 1
                return
            }
        } else if !heap.freeSceneStorage(token) {
            faultStorage.pointee = 1
        }
    }

    // Adopt an already constructed actor. WWD instantiation is a separate step.
    func adopt(_ snapshot: ClawInteractionActor) {
        precondition(!actorTokens.contains(snapshot.token))
        let value = snapshot
        if heap.lookup(value.token, words: 128) == nil { _ = heap.store(token: value.token, words: 128) }
        for token in [value.actor.27, value.actor.28, value.actor.30] where token != 0 {
            if heap.lookup(token, words: 93) == nil { _ = heap.store(token: token, words: 93) }
        }
        write(value)
        claw_scene_actor_insert(containerToken, value.token, host, faultStorage)
        if value.token == 0x10002000, let updated = snapshotActor(value.token) { player.acceptSceneSnapshot(updated) }
    }

    func resetClock() {
        globals.pointee.animation.nowMilliseconds = readClock()
        globals.pointee.animation.deltaMilliseconds = 0
    }
    func nextRandom() -> UInt32 {
        let result = random.call(0x4a3050)
        if random.fault != 0 {
            faultStorage.pointee = random.fault
            unresolvedDependencies.formUnion(random.unresolved)
        }
        return result
    }
    func collisionActors(excluding token: UInt32) -> [ClawCollisionActor] {
        actorTokens.filter { $0 != token }.compactMap { snapshotActor($0).map(ClawCollisionActor.init(snapshot:)) }
    }

    // MARK: - World loading and resource installation

    func loadRecoveredObjects(
        world: ClawWorld, root: URL, saveDirectory: URL? = nil, level: UInt32 = 1,
        objectElections: [ClawNativeObjectConnections.Election] = ClawNativeObjectConnections.elections
    ) throws {
        precondition(objectResources == nil)
        guard (1...14).contains(level) else { throw AssetError.invalid("Level must be in 1...14") }
        // Source application save boot precedes46aeb0's level seed. Loading a
        // file consumes the shared CRT RNG; the later level reseed must win.
        let directory =
            saveDirectory
            ?? FileManager.default.temporaryDirectory.appendingPathComponent("ClawNativeSave/" + UUID().uuidString, isDirectory: true)
        saves = try ClawNativeSave(heap: heap, random: random, storageDirectory: directory)
        platforms = ClawNativePlatforms(scene: self)
        guard platforms!.fault == 0 else { throw AssetError.invalid("Source Level1 profile initialization") }
        if level != 1 {
            guard claw_elevator_initialize_profile(level, platforms!.profile, nil, nil) == 1,
                let raw = heap.lookup(0x5378a0, words: 50),
                let scales = heap.lookup(0x5262b0, words: 3)
            else {
                throw AssetError.invalid("Source level profile initialization")
            }
            withUnsafeBytes(of: &platforms!.profile.pointee.words) {
                UnsafeMutableRawPointer(raw).copyMemory(from: $0.baseAddress!, byteCount: 192)
            }
            raw[48] = platforms!.profile.pointee.selectedToken
            raw[49] = platforms!.profile.pointee.levelWord
            withUnsafeBytes(of: &platforms!.profile.pointee.scaleWords) {
                UnsafeMutableRawPointer(scales).copyMemory(from: $0.baseAddress!, byteCount: 12)
            }
        }
        pegs = ClawNativePegs(scene: self)
        soundTriggers = ClawNativeSoundTriggers(scene: self)
        singleCrates = ClawNativeSingleCrates(scene: self)
        checkpoints = ClawNativeCheckpoints(scene: self)
        curses = ClawNativeCurses(scene: self)
        specialPowerups = ClawNativeSpecialPowerups(scene: self)
        breakables = ClawNativeBreakables(scene: self)
        let humanGlobals = ClawNativeHumanoidGlobals.shared(self)
        humanGlobals.difficulty = platforms!.profile.pointee.levelWord
        humanGlobals.damageScale = Float(bitPattern: platforms!.profile.pointee.scaleWords.0)
        humanGlobals.healthScale = Float(bitPattern: platforms!.profile.pointee.scaleWords.1)
        humanGlobals.rangeScale = Float(bitPattern: platforms!.profile.pointee.scaleWords.2)
        stateRegistry = try ClawNativeStateRegistry(afterInitialize: { [self] registry in
            withUnsafeBytes(of: &registry.pointee.errorGlobals) { source in
                withUnsafeMutableBytes(of: &core.pointee.words) { target in
                    UnsafeMutableRawBufferPointer(rebasing: target.prefix(60)).copyMemory(from: source)
                }
            }
            let result = claw_core_registration_initialize(core, host, faultStorage)
            withUnsafeBytes(of: &core.pointee.words) { source in
                withUnsafeMutableBytes(of: &registry.pointee.errorGlobals) { target in
                    target.copyMemory(from: UnsafeRawBufferPointer(rebasing: source.prefix(60)))
                }
            }
            return result == 1 && fault == 0
        })
        player.collision.setGameStageSteps()
        let resources = try ClawActorResources(
            root: root, heap: heap, level: level,
            resolveEvent: { [weak player] name in
                player?.audio?.resolve(name: name)?.resourceToken ?? 0
            })
        objectResources = resources
        try attachPlayerAnimation(resources)
        installObjectConnections(objectElections, registerGameplay: false)
        // claw-progress-class-owner: rat_logic 0x47c850
        for function: UInt32 in [0x47c850, 0x47d7d0] {
            gameplay[function] = { [weak self] token in self?.enemies[token]?.tick() }
        }
        for function: UInt32 in [0x4dc830, 0x4dc850] {
            gameplay[function] = { [weak self] token in
                guard let self else { return }
                if let body = self.enemies[token] {
                    _ = body.callback(function)
                } else if let body = self.humanoids[token] {
                    _ = body.callback(function)
                } else if let body = self.bullets[token] {
                    _ = body.callback(function)
                } else if self.projectiles?.tokens.contains(token) == true {
                    self.projectiles?.contact(function, actor: token)
                } else if self.flares?.tokens.contains(token) == true {
                    self.flares?.contact(function, actor: token)
                } else if let body = self.breakables?.bodies[token] {
                    _ = body.rawEntry(function, argument: 0)
                } else {
                    _ = self.loot?.callback(token, function: function)
                }
            }
        }
        // claw-progress-class-owner: officer_logic 0x462350
        gameplay[0x462350] = { [weak self] token in self?.humanoids[token]?.tick() }
        // claw-progress-class-owner: soldier_logic 0x48a980
        gameplay[0x48a980] = { [weak self] token in self?.humanoids[token]?.tick() }
        gameplay[0x40fec0] = { [weak self] token in self?.bullets[token]?.tick() }
        gameplay[0x40e690] = { [weak self] token in _ = self?.loot?.callback(token, function: 0x40e690) }
        for function in ClawNativePickup.supported {
            gameplay[function] = { [weak self] token in _ = self?.loot?.callback(token, function: function) }
        }
        for function in ClawNativeEffects.callbacks {
            gameplay[function] = { [weak self] token in _ = self?.effects?.callback(token, function: function) }
        }
        for function in ClawNativeBreakables.callbacks {
            gameplay[function] = { [weak self] token in
                guard let self else { return }
                _ = self.breakables?.callback(function, actor: token)
                if let component = self.breakables, component.fault != 0 { self.faultStorage.pointee = component.fault }
            }
        }
        gameplay[0x470430] = { [weak self] token in
            guard let self, let component = self.specialPowerups else { return }
            component.callback(token)
            if component.fault != 0 {
                self.faultStorage.pointee = component.fault
                self.unresolvedDependencies.formUnion(component.unresolved)
            }
        }
        gameplay[0x470a20] = { [weak self] token in
            guard let self else { return }
            self.curses?.callback(token)
            if let curses = self.curses, curses.fault != 0 { self.faultStorage.pointee = curses.fault }
        }
        loadingWorld = world
        camera = try ClawNativeCamera(
            heap: heap, host: host, world: world, ownerToken: ownerToken, worldToken: mapToken, resources: resources,
            gridSetup: { [weak self] plane, record, count in
                self?.constructPlaneGrid(plane, record: record, count: count) ?? 0
            })
        for function in ClawNativePlatforms.callbacks {
            gameplay[function] = { [weak self] token in
                guard let self else { return }
                _ = self.platforms?.callback(function, actor: token)
                if let platforms = self.platforms, platforms.fault != 0 { self.faultStorage.pointee = platforms.fault }
            }
        }
        for function in ClawNativePegs.callbacks {
            gameplay[function] = { [weak self] token in
                guard let self else { return }
                self.pegs?.callback(function, actor: token)
                if let pegs = self.pegs, pegs.fault != 0 { self.faultStorage.pointee = pegs.fault }
            }
        }
        for function in Self.sceneryCallbacks {
            gameplay[function] = { [weak self] token in self?.sceneryCallback(function, actor: token) }
        }
        for function in ClawNativeCheckpoints.callbacks.union([0x422ff0, 0x4231a0]) {
            gameplay[function] = { [weak self] token in
                guard let self else { return }
                self.checkpoints?.callback(function, actor: token)
                if let checkpoints = self.checkpoints, checkpoints.fault != 0 { self.faultStorage.pointee = checkpoints.fault }
            }
        }
        for function in ClawNativeSingleCrates.callbacks {
            gameplay[function] = { [weak self] token in
                self?.dispatchSingleCrate(function, actor: token)
            }
        }
        gameplay[0x4717e0] = { [weak self] token in
            self?.dispatchSingleCrate(0x4717e0, actor: token)
        }
        for function in ClawNativeSoundTriggers.callbacks {
            gameplay[function] = { [weak self] token in
                guard let self else { return }
                self.soundTriggers?.callback(function, actor: token)
                if let triggers = self.soundTriggers, triggers.fault != 0 { self.faultStorage.pointee = triggers.fault }
            }
        }
        for function in ClawNativeSpeech.callbacks {
            gameplay[function] = { [weak self] token in
                guard let self else { return }
                _ = self.speech?.service(function, arguments: [token])
                if let speech = self.speech, speech.fault != 0 { self.faultStorage.pointee = speech.fault }
            }
        }
        namesByToken[0x522e3c] = "CaptainClawScreenPosition"
        cameraActorToken = claw_plain_actor_create_named(
            containerToken,
            ClawPlainActorCreate(id: 0, z: 9999, entryToken: 0, flags: 0), 0x522e3c, host, faultStorage)
        namesByToken.removeValue(forKey: 0x522e3c)
        guard cameraActorToken != 0 && fault == 0 else { throw AssetError.invalid("Original camera actor creation") }
        for plane in camera!.planeTokens { _ = spatial(0x4d2030, receiver: plane) }
        guard fault == 0, objectLoadingFailure == nil else {
            throw AssetError.invalid(objectLoadingFailure ?? "Spatial startup fault \(fault)")
        }
        rendering = try ClawNativeRendering(scene: self, root: root)
        frameRuntime = ClawNativeFrame(scene: self, owner: ownerToken, parent: parentToken, stage: stage, actors: globals)
        configureRespawn()
        let owner = heap.lookup(ownerToken, words: 478)!, app = heap.lookup(owner[1], words: 77)!
        app[0x60 / 4] = saves!.managerToken
        app[0x64 / 4] = saves!.playerRecord
        // Caller profile of the currently loaded level. Full46aeb0/startup
        // ordering and selected-record restoration still require integration.
        owner[0x14 / 4] = level
        if app[0x48 / 4] == 0 { app[0x48 / 4] = heap.allocate(bytes: 0x12c) }
        statusMessages = ClawNativeStatusMessages(heap: heap, saves: saves!, application: owner[1])
        //The source display holder below elects the final drawing target.
        guard statusMessages!.fault == 0 else { throw AssetError.invalid("Original status-message configuration") }
        effects = ClawNativeEffects(scene: self, resources: resources)
        effects?.externalService = { [weak self] event in
            guard let self, event.arguments.count <= 4 else { return nil }
            var call = ClawSceneActorCall()
            call.function = event.function
            call.receiver = event.receiver
            call.argumentCount = UInt32(event.arguments.count)
            withUnsafeMutableBytes(of: &call.arguments) { words in
                for (index, value) in event.arguments.enumerated() { words.storeBytes(of: value, toByteOffset: index * 4, as: UInt32.self) }
            }
            return self.dispatch(call)
        }
        loot = try ClawNativeLoot(scene: self, resources: resources)
        loot!.itemContext.pointee.managerToken = heap.lookup(ownerToken, words: 2)![1]
        loot!.frameClock = { [weak self] in (self?.gameTime ?? 0, self?.animationDelta ?? 0, self?.stageDelta ?? 0) }
        loot!.externalService = { [weak self] call in self?.effects?.itemService(call) }
        for token in pendingPickupTokens { loot!.attachPickup(token) }
        paletteResources = try ClawNativePaletteResources(scene: self, root: root)
        statusMessages!.installDrawingBridge(target: rendering!.targetToken)
        palettes = try ClawNativeLightPalette(scene: self, root: root)
        projectiles = ClawNativeProjectiles(scene: self)
        guard projectiles!.fault == 0 else { throw AssetError.invalid("Original projectile bootstrap") }
        for function in ClawNativeProjectiles.callbacks {
            gameplay[function] = { [weak self] token in
                guard let self, let p = self.projectiles else { return }
                p.callback(function, actor: token)
                if p.fault != 0 {
                    self.faultStorage.pointee = p.fault
                    self.unresolvedDependencies.formUnion(p.unresolved)
                }
            }
        }
        flares = ClawNativeFlare(scene: self)
        guard flares!.fault == 0 else { throw AssetError.invalid("Original Flare bootstrap") }
        for function in ClawNativeFlare.callbacks {
            gameplay[function] = { [weak self] token in
                guard let self, let p = self.flares else { return }
                p.callback(function, actor: token)
                if p.fault != 0 {
                    self.faultStorage.pointee = p.fault
                    self.unresolvedDependencies.formUnion(p.unresolved)
                }
            }
        }
        player.sceneProjectileCommit = { [weak self] in self?.projectiles?.commitPlayerLaunch() }
        hud = ClawNativeHUD(scene: self)
        guard hud!.create() else {
            throw AssetError.invalid("Original MultiStats HUD creation fault \(hud!.fault), services \(hud!.unresolved)")
        }
        speech = ClawNativeSpeech(scene: self)
        guard speech!.createControllers() else { throw AssetError.invalid("Original dialog controller creation fault \(speech!.fault)") }
        ambientAudio = ClawNativeAmbientAudio(scene: self)
        guard ambientAudio!.fault == 0 && soundTriggers!.fault == 0 else {
            throw AssetError.invalid("Source ambient manager initialization")
        }
        pendingPickupTokens.removeAll()
        registerObjectConnectionGameplay()
        playerServices = ClawNativePlayerServices(scene: self)
        carry = ClawNativeCarry(scene: self)
        player.sceneCarryDispatch = { [weak self] state, input in
            guard let self, let carry = self.carry else { return 0 }
            let result = carry.dispatch(state, input: input)
            if carry.fault != 0 {
                self.faultStorage.pointee = carry.fault
                self.unresolvedDependencies.formUnion(carry.unresolved)
            }
            return result
        }
        player.sceneDependency = { [weak self] state, entry, a, b, c in
            guard let self, let services = self.playerServices else { return nil }
            if [UInt32(0x41c9f0), 0x41cab0, 0x41cb80, 0x41cc60].contains(entry), let p = self.projectiles {
                let result = p.emit(entry, state: state)
                if p.fault != 0 {
                    self.faultStorage.pointee = p.fault
                    self.unresolvedDependencies.formUnion(p.unresolved)
                }
                return result
            }
            if let value = self.carry?.call(state, entry: entry, a: a, b: b, c: c) {
                if let carry = self.carry, carry.fault != 0 {
                    self.faultStorage.pointee = carry.fault
                    self.unresolvedDependencies.formUnion(carry.unresolved)
                }
                return value
            }
            if entry == 0x4c8da0, ClawNativeProjectiles.names[a] != nil, let p = self.projectiles {
                let result = p.beginPlayerLaunch(state, name: a, x: b, y: c)
                if p.fault != 0 {
                    self.faultStorage.pointee = p.fault
                    self.unresolvedDependencies.formUnion(p.unresolved)
                }
                return result
            }
            if entry == 0x4c7970, let p = self.projectiles, p.tokens.contains(a) {
                let result = p.bindLaunchImage(actor: a, literal: b)
                if p.fault != 0 {
                    self.faultStorage.pointee = p.fault
                    self.unresolvedDependencies.formUnion(p.unresolved)
                }
                return result
            }
            let result = services.call(state, entry: entry, a: a, b: b, c: c)
            if result != nil && services.fault != 0 {
                self.faultStorage.pointee = services.fault
                self.unresolvedDependencies.formUnion(services.unresolved)
            }
            return result
        }
    }
    // Physical resource dictionary lookup (0x4f6286) as a resolved token. An
    // object adapter writes it to the original caller's output pointer.
    func resolveResource(dictionary: UInt32, name: UInt32) -> UInt32 {
        if let value = namesByToken[name] {
            if dictionary == 0x63000010 {
                do { return try objectResources?.sequence(name: value)?.token ?? 0 } catch {
                    faultStorage.pointee = 1
                    return 0
                }
            }
            if value.withCString({ claw_logic_registry_find($0) }) != nil { return entry(named: value) }
            return player.audio?.resolve(name: value)?.resourceToken ?? 0
        }
        if dictionary == 0x63000010 {
            if player.assets.sequenceNames[name] != nil { return playerSequence(name) }
            if let value = clawOriginalResourceNames[name] {
                do { return try objectResources?.sequence(name: value)?.token ?? 0 } catch {
                    faultStorage.pointee = 1
                    return 0
                }
            }
        }
        return 0
    }
    private func dispatchSingleCrate(_ function: UInt32, actor: UInt32) {
        guard let crates = singleCrates else {
            faultStorage.pointee = 1
            return
        }
        // FrontStatue's canonical callback and the existing native crate owner
        // see one global, including a later base crate and the CrateHit callback.
        if let variant = heap.lookup(0x52a194, words: 1) {
            crates.globals.pointee.crateImageChoice = variant[0]
        }
        crates.callback(function, actor: actor)
        heap.lookup(0x52a194, words: 1)?[0] = crates.globals.pointee.crateImageChoice
        if crates.fault != 0 { faultStorage.pointee = crates.fault }
        unresolvedDependencies.formUnion(crates.unresolved)
    }
    // Object adapters join through ClawNativeObjectConnections. Their gameplay
    // callbacks register after every other native owner and never displace one.

    // MARK: - Elected object callback connections

    private var connectionCallbacks: Set<UInt32> = []
    func installObjectConnections(
        _ elections: [ClawNativeObjectConnections.Election] = ClawNativeObjectConnections.elections,
        registerGameplay: Bool = true
    ) {
        for function in connectionCallbacks { gameplay.removeValue(forKey: function) }
        connectionCallbacks = []
        objectConnections = ClawNativeObjectConnections(scene: self, elections: elections)
        if let fault = objectConnections!.host.fault { faultStorage.pointee = fault.code }
        if registerGameplay { registerObjectConnectionGameplay() }
    }
    func registerObjectConnectionGameplay() {
        guard let connections = objectConnections else { return }
        if connections.adapter("boss_stager") is ClawNativeBossStager {
            guard gameplay[0x491fa0] == nil else {
                connections.reject(0x491fa0)
                faultStorage.pointee = UInt32(CLAW_FAULT_ABI)
                return
            }
            connectionCallbacks.insert(0x491fa0)
            gameplay[0x491fa0] = { [weak self] actor in
                guard let self, let connections = self.objectConnections,
                    let stager = connections.adapter("boss_stager") as? ClawNativeBossStager
                else { return }
                _ = stager.invoke(0x491fa0, actor: actor)
                if let fault = connections.host.fault {
                    self.faultStorage.pointee = fault.code
                    self.unresolvedDependencies.insert(fault.address)
                }
            }
        }
        if connections.adapter("boss_warp") is ClawNativeBossWarp {
            guard gameplay[0x4701b0] == nil else {
                connections.reject(0x4701b0)
                faultStorage.pointee = UInt32(CLAW_FAULT_ABI)
                return
            }
            connectionCallbacks.insert(0x4701b0)
            gameplay[0x4701b0] = { [weak self] actor in
                guard let self, let connections = self.objectConnections,
                    let warp = connections.adapter("boss_warp") as? ClawNativeBossWarp
                else { return }
                warp.childCallback(actor)
                if let fault = connections.host.fault {
                    self.faultStorage.pointee = fault.code
                    self.unresolvedDependencies.insert(fault.address)
                }
            }
        }
        if connections.adapter("break_plank") is ClawNativeBreakPlank {
            guard gameplay[0x488e30] == nil else {
                connections.reject(0x488e30)
                faultStorage.pointee = UInt32(CLAW_FAULT_ABI)
                return
            }
            connectionCallbacks.insert(0x488e30)
            gameplay[0x488e30] = { [weak self] actor in
                guard let self, let connections = self.objectConnections,
                    let plank = connections.adapter("break_plank") as? ClawNativeBreakPlank
                else { return }
                plank.childCallback(actor)
                if let fault = connections.host.fault {
                    self.faultStorage.pointee = fault.code
                    self.unresolvedDependencies.insert(fault.address)
                }
            }
        }
        for function in connections.callbacks.sorted() {
            guard gameplay[function] == nil else {
                connections.reject(function)
                faultStorage.pointee = UInt32(CLAW_FAULT_ABI)
                continue
            }
            connectionCallbacks.insert(function)
            gameplay[function] = { [weak self] actor in
                guard let self, let connections = self.objectConnections else { return }
                connections.callback(function, actor: actor)
                if let fault = connections.host.fault {
                    self.faultStorage.pointee = fault.code
                    self.unresolvedDependencies.insert(fault.address)
                }
            }
        }
    }
    @discardableResult func spatial(_ function: UInt32, receiver: UInt32, arguments: [UInt32] = []) -> UInt32 {
        precondition(arguments.count <= 8)
        var values = ClawSpatialGridArguments(), result: UInt32 = 0
        values.count = UInt32(arguments.count)
        withUnsafeMutableBytes(of: &values.words) { bytes in
            for (index, word) in arguments.enumerated() { bytes.storeBytes(of: word, toByteOffset: index * 4, as: UInt32.self) }
        }
        heap.withStableFreedStorage {
            if claw_spatial_grid_entry(function, receiver, values, host, faultStorage, &result) == 0 {
                unresolvedDependencies.insert(function)
            }
        }
        spatialCalls[function, default: 0] &+= 1
        return result
    }
    private func constructPlaneGrid(_ token: UInt32, record: UInt32, count: UInt32) -> UInt32 {
        guard let world = loadingWorld, let plane = heap.lookup(token, words: 86), Int(plane[1]) < world.planes.count else {
            faultStorage.pointee = 1
            return 0
        }
        let source = world.planes[Int(plane[1])]
        guard count == source.objects.count else {
            faultStorage.pointee = 1
            return 0
        }
        if let first = source.objects.first {
            let base = record &- UInt32(first.encodedRecordOffset)
            for object in source.objects { recordsByToken[base &+ UInt32(object.encodedRecordOffset)] = object }
        }
        return spatial(0x4d1620, receiver: token, arguments: [record, count])
    }
    private func loadGridObject(plane: UInt32, record: UInt32) -> UInt32 {
        guard let source = recordsByToken[record], let world = loadingWorld else {
            faultStorage.pointee = 1
            return 0
        }
        return loadGridObject(source, world: world, plane: plane)
    }
    @discardableResult func loadGridObject(_ source: ClawWorld.Object, world: ClawWorld, plane: UInt32) -> UInt32 {
        guard let resources = objectResources else {
            faultStorage.pointee = 1
            return 0
        }
        // Unsupported gameplay remains a declared partial-population boundary.
        // The real grid record loop advances exact validated WWD record bytes.
        let callback = source.logic.withCString { claw_logic_registry_find($0)?.pointee.callback ?? 0 }
        guard
            objectConnections?.callbacks.contains(callback) == true || source.logic == "Rat" || source.logic == "Officer"
                || source.logic == "Soldier" || ClawNativePickup.supported.contains(callback) || Self.sceneryCallbacks.contains(callback)
                || ClawNativePlatforms.callbacks.contains(callback) || ClawNativePegs.callbacks.contains(callback)
                || ClawNativeSoundTriggers.callbacks.contains(callback) || ClawNativeSingleCrates.callbacks.contains(callback)
                || ClawNativeCheckpoints.callbacks.contains(callback) || ClawNativeCurses.callbacks.contains(callback)
                || ClawNativeSpecialPowerups.callbacks.contains(callback) || ClawNativeBreakables.worldCallbacks.contains(callback)
        else {
            uninstantiatedObjectCount += 1
            uninstantiatedLogics[source.logic, default: 0] += 1
            return UInt32(source.encodedRecord.count)
        }
        do {
            let adapter = ClawNativeObjectLoader(scene: self, resources: resources)
            if let object = try adapter.load(source, world: world, planeToken: plane) {
                if objectConnections?.callbacks.contains(callback) == true {
                    if callback == 0x470870 {
                        // This finite BossWarp join elects original low detail,
                        // matching the native no-glitter configuration boundary.
                        // Publish the real option; canonical gem code reads it.
                        guard let manager = heap.lookup(ownerToken + 4, words: 1)?[0],
                            let detail = heap.lookup(manager + 0x124, words: 1)
                        else {
                            faultStorage.pointee = UInt32(CLAW_FAULT_MEMORY)
                            return 0
                        }
                        detail[0] = 0
                    }
                    objectConnections?.attach(object, callback: callback)
                    if let fault = objectConnections?.host.fault {
                        faultStorage.pointee = fault.code
                        unresolvedDependencies.insert(fault.address)
                        return 0
                    }
                } else if source.logic == "Rat" {
                    enemies[object.token] = ClawNativeEnemy(kind: .rat, snapshot: object, scene: self, resources: resources)
                } else if source.logic == "Officer" || source.logic == "Soldier" {
                    let body = try ClawNativeHumanoid(
                        kind: source.logic == "Soldier" ? .soldier : .officer,
                        snapshot: object, scene: self, resources: resources)
                    humanoids[object.token] = body
                    body.onBulletCreated = { [weak self] child in self?.bullets[child.token] = child }
                    body.bindSceneService { [weak self] call in self?.humanoidService(call) }
                } else if ClawNativeBreakables.worldCallbacks.contains(callback) {
                    breakables!.attach(object)
                } else if ClawNativeSpecialPowerups.callbacks.contains(callback) {
                    specialPowerups!.attach(object)
                } else if ClawNativeCurses.callbacks.contains(callback) {
                    curses!.attach(object)
                } else if ClawNativeCheckpoints.callbacks.contains(callback) {
                    checkpoints!.attach(object)
                } else if ClawNativeSingleCrates.callbacks.contains(callback) {
                    singleCrates!.attach(object)
                } else if ClawNativeSoundTriggers.callbacks.contains(callback) {
                    soundTriggers!.attach(object)
                } else if ClawNativePegs.callbacks.contains(callback) {
                    pegs!.attach(object.token)
                } else if ClawNativePlatforms.callbacks.contains(callback) {
                    platforms!.attach(object.token)
                } else if Self.sceneryCallbacks.contains(callback) {
                    sceneryTokens.insert(object.token)
                } else {
                    pendingPickupTokens.insert(object.token)
                }
            }
            return UInt32(source.encodedRecord.count)
        } catch {
            objectLoadingFailure = String(describing: error)
            faultStorage.pointee = 1
            return 0
        }
    }

    // MARK: - Player animation and secondary logic

    private func attachPlayerAnimation(_ resources: ClawActorResources) throws {
        let maximum = player.assets.images.keys.max()!, minimum = player.assets.images.keys.min()!
        let imageManager = heap.store(token: 0x10007000, words: 27)
        let tableToken = heap.allocate(bytes: UInt32((maximum + 1) * 4))
        let table = heap.lookup(tableToken, words: UInt32(maximum + 1))!
        for id in player.assets.images.keys {
            table[id] = try ClawActorResources.imageHeader(sprite: player.assets.sprites[id]!, heap: heap, offsetY: player.imageOffsetY[id])
        }
        player.sceneImage = { [weak self] id in
            guard id <= UInt32(maximum) else { return 0 }
            return self?.heap.lookup(tableToken, words: UInt32(maximum + 1))?[Int(id)] ?? 0
        }
        imageManager[5] = tableToken
        imageManager[6] = UInt32(maximum + 1)
        imageManager[25] = UInt32(minimum)
        imageManager[26] = UInt32(maximum)
        var snapshot = player.sceneSnapshot()
        snapshot.actor.93 = table[Int(snapshot.actor.91)]
        if let sequence = try resources.sequence(name: "CLAW_" + player.sequence) {
            let sequenceWords = heap.lookup(sequence.token, words: 5)!
            let records = heap.lookup(sequenceWords[3], words: sequenceWords[4])!
            guard snapshot.actor.102 < sequenceWords[4] else { throw AssetError.invalid("Player animation migration index") }
            snapshot.actor.100 = sequence.token
            snapshot.actor.101 = records[Int(snapshot.actor.102)]
            player.acceptSceneSnapshot(snapshot)
            write(snapshot)
        }
        player.sceneSequence = { [weak self] literal in self?.playerSequence(literal) ?? 0 }
        player.sceneSequenceName = { [weak resources] token in
            guard let name = resources?.sequence(token: token)?.name, name.hasPrefix("CLAW_") else { return nil }
            return String(name.dropFirst(5))
        }
        player.sceneAnimation = { [weak self] state, function, a, b in
            guard let self, let actor = self.heap.lookup(0x10002000, words: 128) else { return 0 }
            withUnsafeBytes(of: &state.pointee.actor) {
                UnsafeMutableRawBufferPointer(start: actor, count: 512).copyMemory(from: $0)
            }
            let receiver: UInt32 = [UInt32(0x4c8220), 0x4c8260, 0x420970, 0x4c82a0].contains(function) ? 0x10002188 : 0x10002000
            let result = self.actorAnimation(function: function, receiver: receiver, argument0: a, argument1: b)
            withUnsafeMutableBytes(of: &state.pointee.actor) {
                $0.copyMemory(from: UnsafeRawBufferPointer(start: actor, count: 512))
            }
            return result
        }
    }
    private func playerSequence(_ literal: UInt32) -> UInt32 {
        guard let name = player.assets.sequenceNames[literal], let resources = objectResources else { return 0 }
        do { return try resources.sequence(name: "CLAW_" + name)?.token ?? 0 } catch {
            faultStorage.pointee = 1
            return 0
        }
    }
    // Complete source named secondary binder over the actual raw actor/logic.
    // The callback publishes exact metadata and physical allocation identities.
    func bindSecondaryLogic(actor token: UInt32, name: String, contact: Bool = false) -> UInt32 {
        guard var snapshot = snapshotActor(token) else {
            faultStorage.pointee = 1
            return 0
        }
        var binding = ClawActorResourceBindings()
        binding.actor = snapshot.actor
        binding.secondary = contact ? snapshot.contact : snapshot.secondary
        var context = ClawActorBindingContext()
        context.logicRegistryToken = 0x63000030
        let result = name.withCString {
            let callback: ClawActorBindingDependency = { _, context, event, user in
                guard let context, let event, let user else { return 0 }
                let scene = Unmanaged<ClawNativeScene>.fromOpaque(user).takeUnretainedValue()
                switch event.pointee.function {
                case 0x4f6286:
                    guard let name = event.pointee.name, let metadata = claw_logic_registry_find(name) else { return 0 }
                    context.pointee.metadataCallback = metadata.pointee.callback
                    context.pointee.metadataFlags = metadata.pointee.flags
                    return scene.entry(named: String(cString: name))
                case 0x4f63ec: return scene.heap.allocate(bytes: event.pointee.argument)
                case 0x4f6428:
                    scene.freeActorStorage(event.pointee.argument)
                    return 0
                default:
                    scene.unresolvedDependencies.insert(event.pointee.function)
                    scene.faultStorage.pointee = 1
                    return 0
                }
            }
            return contact
                ? claw_actor_bind_contact_logic_name(&binding, &context, $0, callback, Unmanaged.passUnretained(self).toOpaque())
                : claw_actor_bind_secondary_logic_name(&binding, &context, $0, callback, Unmanaged.passUnretained(self).toOpaque())
        }
        snapshot.actor = binding.actor
        if contact { snapshot.contact = binding.secondary } else { snapshot.secondary = binding.secondary }
        write(snapshot)
        return result
    }
    func bindContactLogic(actor token: UInt32, name: String) -> UInt32 { bindSecondaryLogic(actor: token, name: name, contact: true) }
    // All 123 installed vtables of these 87 roots bind bump slot +0x20 to
    // original v1.3 0x40b630; checked against serialization-contract-review.json.
    private static let defaultBumpRoots: Set<UInt32> = [
        0x403100, 0x4041f0, 0x406400, 0x406dd0, 0x4073e0, 0x48d620, 0x409090, 0x409860,
        0x40e690, 0x40f7b0, 0x40fec0, 0x414b20, 0x414cc0, 0x415350, 0x421200, 0x431320,
        0x431cd0, 0x432570, 0x433070, 0x434190, 0x4379d0, 0x43a850, 0x43ca60, 0x4411b0,
        0x410100, 0x441be0, 0x457f00, 0x48d560, 0x443290, 0x4459d0, 0x446550, 0x448620,
        0x448d10, 0x4493c0, 0x449c40, 0x410280, 0x453b10, 0x453d30, 0x4553d0, 0x4559e0,
        0x4561c0, 0x456b00, 0x457620, 0x4101c0, 0x410040, 0x458680, 0x45a2e0, 0x45ff00,
        0x462350, 0x4633a0, 0x410400, 0x464f20, 0x465580, 0x4689b0, 0x40ff80, 0x46f1e0,
        0x474330, 0x47c850, 0x47d7d0, 0x47e210, 0x47f6e0, 0x410700, 0x410640, 0x482820,
        0x4842b0, 0x4847b0, 0x485270, 0x486e90, 0x4887b0, 0x488e30, 0x489730, 0x4104c0,
        0x48a800, 0x48a980, 0x48e4a0, 0x497eb0, 0x4922c0, 0x493eb0, 0x495d40, 0x495e00,
        0x496050, 0x4968d0, 0x410580, 0x49f0a0, 0x49fb30, 0x410340, 0x458010
    ]
    private func proposedContactActors() -> [ClawV13ContactActor] {
        let tokens = actorTokens, live = Set(tokens)
        bumpLogics = bumpLogics.filter { live.contains($0.key) }
        bumpPeers = bumpPeers.filter { live.contains($0.key) }
        return tokens.compactMap { token in
            guard let snapshot = snapshotActor(token) else { return nil }
            if Self.defaultBumpRoots.contains(snapshot.primary.4), bumpLogics[token] == nil {
                bumpLogics[token] = ClawNativeBumpLogic(identity: snapshot.actor.1, scene: sceneIdentity)
            }
            return ClawV13ContactActor(
                actor: ClawCollisionActor(snapshot: snapshot), mask: 0,
                otherToken: bumpPeers[token] ?? 0, hasCallback: bumpLogics[token] == nil ? 0 : 1)
        }
    }
    func entry(named name: String) -> UInt32 {
        if let token = registryEntries[name] { return token }
        guard let metadata = name.withCString({ claw_logic_registry_find($0)?.pointee }) else { return 0 }
        let token = heap.allocate(bytes: 20), words = heap.lookup(token, words: 5)!
        words[0] = metadata.originalNameAddress
        words[1] = metadata.registrationOrdinal
        words[2] = metadata.flags
        words[4] = metadata.callback
        registryEntries[name] = token
        return token
    }
    func createBomb(x: UInt32, y: UInt32, z: UInt32, flags: UInt32) throws -> ClawNativeEnemy? {
        guard let resources = objectResources else { return nil }
        let name = heap.allocate(bytes: 8)
        namesByToken[name] = "RatBomb"
        let token = claw_scene_actor_create_named(
            containerToken,
            ClawSceneActorCreate(id: 0, x: x, y: y, z: z, entryToken: 0, flags: flags), name, host, faultStorage)
        heap.free(name)
        namesByToken.removeValue(forKey: name)
        guard fault == 0, token != 0, let snapshot = snapshotActor(token) else { return nil }
        let enemy = ClawNativeEnemy(kind: .bomb, snapshot: snapshot, scene: self, resources: resources)
        enemies[token] = enemy
        return enemy
    }

    // Publish the platform's accumulated game clock before source callbacks.

    // MARK: - Frame scheduling and posted commands

    func publishGameTime(_ accumulated: UInt32) {
        stage.pointee.accumulatedMilliseconds = accumulated
        player.audio?.requestTick = accumulated
    }

    func advance(
        now: UInt32, delta: UInt32, accumulated: UInt32, held: UInt32, pressed: UInt32,
        clock: ClawClockState? = nil
    ) {
        snapshotFrameDepth += 1
        defer { snapshotFrameDepth -= 1 }
        if let clock {
            clockSnapshot = clock
        } else {
            clockSnapshot.nowMilliseconds = now
            clockSnapshot.deltaMilliseconds = delta
        }
        withUnsafeBytes(of: &clockSnapshot) {
            UnsafeMutableRawPointer(heap.lookup(0x541328, words: 5)!).copyMemory(from: $0.baseAddress!, byteCount: 20)
        }
        self.held = held
        self.pressed = pressed
        camera?.setInput(held: held, pressed: pressed)
        write(player.sceneSnapshot())
        stage.pointee.stage = ClawFrameClock(nowMilliseconds: now, deltaMilliseconds: delta)
        publishGameTime(accumulated)
        if let frameRuntime {
            lastPassCount = delta > 18 && delta < 100 ? delta / 18 + (delta % 18 == 0 ? 0 : 1) : 1
            if frameRuntime.advance() == 0 { faultStorage.pointee = frameRuntime.fault }
        } else {
            lastPassCount = heap.withStableFreedStorage {
                claw_scene_stage_update(ownerToken, stage, globals, host, faultStorage)
            }
        }
        // HUD callbacks can award lives after the player's own phase. Import
        // the source private buffer so the next frame preserves those writes.
        _ = importPlayerFromHeap()
    }

    // Posted WM_COMMANDs run after the source frame, outside player callbacks.
    // The caller publishes returned timing into the same platform clock adapter.
    @discardableResult func processPlayerCommands() -> Bool {
        guard let respawn else { return false }
        let commands = player.drainPendingCommands()
        guard !commands.isEmpty else { return false }
        player.returnPendingCommands(respawn.consume(commands: commands))
        if respawn.fault != 0 { faultStorage.pointee = respawn.fault }
        return true
    }

    private func configureRespawn() {
        let owner = heap.lookup(ownerToken, words: 478)!, application = owner[1]
        let app = heap.lookup(application, words: 77)!
        app[1] = windowReceiver
        app[0x2c / 4] = ownerToken
        app[0x30 / 4] = parentToken
        app[0x7c / 4] = 640
        app[0x80 / 4] = 480
        //The source PAL resource graph below publishes the real owner+2c
        //wrapper before any retained frame/respawn can inspect its presence.
        let soundRegistry = heap.allocate(bytes: 56)
        heap.lookup(parentToken, words: 12)![10] = soundRegistry
        heap.lookup(soundRegistry, words: 14)![13] = 0
        heap.lookup(soundRegistry, words: 13)![3] = parentToken  //Source registry+C → scene24 → map5c.
        var deathGlobals = ClawPlayerDeathCommandGlobals()
        deathGlobals.playerToken = 0x10002000
        deathGlobals.masterVolume = player.audio?.routing.masterVolume ?? 0
        deathGlobals.keyboardToken = camera!.inputToken
        respawn = ClawNativeRespawn(
            heap: heap, applicationToken: application, globals: deathGlobals, host: host,
            hooks: .init(
                playerPrimary: { [weak self] actor in
                    guard let self else { return false }
                    var call = ClawSceneActorCall()
                    call.function = 0x415df0
                    call.argumentCount = 1
                    call.arguments.0 = actor
                    _ = self.dispatch(call)
                    return self.fault == 0 && self.player.runtime.logicState == 24
                },
                actorFrame: { [weak self] container, refresh in
                    self?.actorFrame(container: container, refresh: refresh) ?? false
                },
                service: { [weak self] call in
                    guard let self else { return nil }
                    switch call.function {
                    case 0x4d2000, 0x4d1fd0, 0x4cb9b0, ClawNativeFrame.presentFunction, 0x4061b0, 0x4208e0:
                        return self.dispatch(call)
                    case 0x48fae0, 0x48fbe0:
                        self.fadeRequests.append(call)
                        self.adaptedDependencies.insert(call.function)
                        return 0  //Declared fade-request transport; source fade loop is pending.
                    default: return nil
                    }
                }, captureTiming: { [weak self] value in self?.captureDeathTiming(&value) },
                publishTiming: { [weak self] value in
                    guard let self else { return }
                    self.publishDeathTiming(value)
                    var clock = value.clock
                    withUnsafeBytes(of: &clock) { source in
                        UnsafeMutableRawPointer(self.heap.lookup(0x541328, words: 5)!).copyMemory(from: source.baseAddress!, byteCount: 20)
                    }
                }, importPlayer: { [weak self] in _ = self?.importPlayerFromHeap() }))
    }

    @discardableResult func importPlayerFromHeap() -> Bool {
        guard let snapshot = snapshotActor(0x10002000),
            let words = heap.lookup(snapshot.primary.5, words: 78)
        else {
            faultStorage.pointee = 1
            return false
        }
        player.acceptSceneSnapshot(snapshot, privateWords: UnsafePointer(words))
        return true
    }
    func writePlayerRuntime(_ value: ClawPlayerLocomotion) {
        player.acceptRuntimeSnapshot(value)
        write(player.sceneSnapshot())
    }
    @discardableResult func actorFrame(container: UInt32, refresh: UInt32) -> Bool {
        heap.withStableFreedStorage {
            claw_scene_actor_update(container, globals, refresh, host, faultStorage)
        }
        _ = importPlayerFromHeap()
        return fault == 0
    }
    func captureDeathTiming(_ value: inout ClawPlayerDeathCommandGlobals) {
        value.clock = clockSnapshot
        value.stage = stage.pointee.stage
        value.animation = globals.pointee.animation
    }
    func publishDeathTiming(_ value: ClawPlayerDeathCommandGlobals) {
        clockSnapshot = value.clock
        stage.pointee.stage = value.stage
        globals.pointee.animation = value.animation
        camera?.synchronize(
            stageDelta: value.stage.deltaMilliseconds,
            animationNow: value.animation.nowMilliseconds, animationDelta: value.animation.deltaMilliseconds)
    }
    var currentClockSnapshot: ClawClockState { clockSnapshot }

    // MARK: - Snapshot participants and scheduler state

    func savedPlayerServicesState() throws -> ClawNativePlayerServices.SavedState {
        guard snapshotFrameDepth == 0 else { throw ClawSnapshotError.activeFrame }
        guard let playerServices else { throw ClawSnapshotError.incompleteOwners }
        return try playerServices.savedState()
    }
    func restorePlayerServicesState(_ saved: ClawNativePlayerServices.SavedState) throws {
        guard snapshotFrameDepth == 0 else { throw ClawSnapshotError.activeFrame }
        guard let playerServices else { throw ClawSnapshotError.incompleteOwners }
        try playerServices.restoreState(saved)
    }

    struct ObjectServicesSavedState: Codable, Equatable {
        let platforms: ClawNativePlatforms.SavedState, pegs: ClawNativePegs.SavedState
        let crates: ClawNativeSingleCrates.SavedState, curses: ClawNativeCurses.SavedState
        let soundTriggers: ClawNativeSoundTriggers.SavedState, checkpoints: ClawNativeCheckpoints.SavedState
        let speech: ClawNativeSpeech.SavedState, ambient: ClawNativeAmbientAudio.SavedState
        let hud: ClawNativeHUD.SavedState, carry: ClawNativeCarry.SavedState
    }
    func savedObjectServicesState() throws -> ObjectServicesSavedState {
        guard snapshotFrameDepth == 0 else { throw ClawSnapshotError.activeFrame }
        guard let platforms, let pegs, let singleCrates, let curses, let soundTriggers, let checkpoints
        else { throw ClawSnapshotError.incompleteOwners }
        guard let speech, let ambientAudio, let hud, let carry else { throw ClawSnapshotError.incompleteOwners }
        return .init(
            platforms: platforms.savedState(), pegs: pegs.savedState(), crates: singleCrates.savedState(),
            curses: curses.savedState(), soundTriggers: soundTriggers.savedState(), checkpoints: checkpoints.savedState(),
            speech: speech.savedState(), ambient: ambientAudio.savedState(), hud: hud.savedState(), carry: try carry.savedState())
    }
    func restoreObjectServicesState(_ saved: ObjectServicesSavedState) throws {
        guard snapshotFrameDepth == 0 else { throw ClawSnapshotError.activeFrame }
        guard let platforms, let pegs, let singleCrates, let curses, let soundTriggers, let checkpoints
        else { throw ClawSnapshotError.incompleteOwners }
        guard let speech, let ambientAudio, let hud, let carry else { throw ClawSnapshotError.incompleteOwners }
        try checkpoints.restoreState(saved.checkpoints)
        try hud.restoreState(saved.hud)
        try ambientAudio.restoreState(saved.ambient)
        try carry.restoreState(saved.carry)
        platforms.restoreState(saved.platforms)
        pegs.restoreState(saved.pegs)
        singleCrates.restoreState(saved.crates)
        curses.restoreState(saved.curses)
        soundTriggers.restoreState(saved.soundTriggers)
        speech.restoreState(saved.speech)
    }

    // Dynamic actor participant, not a complete scene archive. The scene
    // transaction must also reconstruct every service, adapter and host before
    // publishing the candidate. All graph construction here is off screen.
    struct DynamicActorsSavedState: Codable, Equatable {
        let registry: ClawNativeStateRegistry.SavedState
        let globals: ClawNativeHumanoidGlobals.SavedState
        let enemies: [ClawNativeEnemy.SavedState]
        let humanoids: [ClawNativeHumanoid.SavedState]
        let bullets: [ClawNativeBullet.SavedState]
        let sceneBullets: [ClawSnapshotOwnerKey]
    }
    func savedDynamicActorsState() throws -> DynamicActorsSavedState {
        guard snapshotFrameDepth == 0 else { throw ClawSnapshotError.activeFrame }
        guard let stateRegistry else { throw ClawSnapshotError.incompleteOwners }
        var bulletGraph: [ClawSnapshotOwnerKey: ClawNativeBullet] = [:], bulletOrder: [ClawSnapshotOwnerKey] = []
        func visit(_ body: ClawNativeBullet) throws {
            let key = try body.snapshotOwnerKey()
            if let previous = bulletGraph[key] {
                guard previous === body else { throw ClawSnapshotError.invalidState }
            } else {
                bulletGraph[key] = body
                bulletOrder.append(key)
            }
        }
        for token in bullets.keys.sorted() { try visit(bullets[token]!) }
        for token in humanoids.keys.sorted() {
            let owner = humanoids[token]!
            for child in owner.bullets.keys.sorted() { try visit(owner.bullets[child]!) }
        }
        return DynamicActorsSavedState(
            registry: stateRegistry.savedState(), globals: ClawNativeHumanoidGlobals.shared(self).savedState(),
            enemies: try enemies.keys.sorted().map { try enemies[$0]!.savedState() },
            humanoids: try humanoids.keys.sorted().map { try humanoids[$0]!.savedState() },
            bullets: try bulletOrder.map { try bulletGraph[$0]!.savedState() },
            sceneBullets: try bullets.keys.sorted().map { try bullets[$0]!.snapshotOwnerKey() })
    }
    func reconstructDynamicActors(_ saved: DynamicActorsSavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws -> Void {
        guard snapshotFrameDepth == 0 else { throw ClawSnapshotError.activeFrame }
        guard let stateRegistry, let resources = objectResources else { throw ClawSnapshotError.incompleteOwners }
        try heap.validateRestore(plan)
        let enemyKeys = saved.enemies.map(\.token), humanKeys = saved.humanoids.map(\.service.token),
            bulletKeys = saved.sceneBullets.map(\.token)
        let allBulletKeys = saved.bullets.map {
            ClawSnapshotOwnerKey(token: $0.service.token, allocation: $0.service.actor.reference.identity)
        }
        guard Set(enemyKeys + humanKeys + bulletKeys).count == enemyKeys.count + humanKeys.count + bulletKeys.count,
            Set(allBulletKeys).count == allBulletKeys.count, allBulletKeys.count <= 16384,
            saved.sceneBullets.allSatisfy({ allBulletKeys.contains($0) }),
            enemyKeys.count + humanKeys.count + bulletKeys.count <= 16384
        else { throw ClawSnapshotError.invalidState }
        try stateRegistry.restoreState(saved.registry)
        let restoredEnemies = try Dictionary(
            uniqueKeysWithValues: saved.enemies.map {
                ($0.token, try ClawNativeEnemy.restoring($0, scene: self, resources: resources, heap: plan))
            })
        let restoredBullets = try Dictionary(
            uniqueKeysWithValues: saved.bullets.map {
                (
                    ClawSnapshotOwnerKey(token: $0.service.token, allocation: $0.service.actor.reference.identity),
                    try ClawNativeBullet.restoring($0, scene: self, resources: resources, heap: plan)
                )
            })
        let restoredHumanoids = try Dictionary(
            uniqueKeysWithValues: saved.humanoids.map {
                (
                    $0.service.token,
                    try ClawNativeHumanoid.restoring($0, scene: self, resources: resources, heap: plan, bullets: restoredBullets)
                )
            })
        // Building views may resolve names, but cannot change the saved registry
        // topology or consume allocations from the candidate's token heap.
        guard stateRegistry.savedState() == saved.registry else { throw ClawSnapshotError.invalidState }
        try heap.validateRestore(plan)
        return { [self] in
            try heap.validateInstalledRestore(plan)
            guard snapshotFrameDepth == 0 else { throw ClawSnapshotError.activeFrame }
            enemies = restoredEnemies
            humanoids = restoredHumanoids
            bullets = Dictionary(uniqueKeysWithValues: saved.sceneBullets.map { ($0.token, restoredBullets[$0]!) })
            ClawNativeHumanoidGlobals.shared(self).restoreState(saved.globals)
            for savedBody in saved.humanoids where savedBody.service.sceneServiceBound {
                humanoids[savedBody.service.token]!.bindSceneService { [weak self] call in self?.humanoidService(call) }
            }
            for savedBody in saved.bullets where savedBody.service.sceneServiceBound {
                let key = ClawSnapshotOwnerKey(token: savedBody.service.token, allocation: savedBody.service.actor.reference.identity)
                restoredBullets[key]!.bindSceneService { [weak self] call in self?.humanoidService(call) }
            }
            for body in humanoids.values {
                body.onBulletCreated = { [weak self] child in self?.bullets[child.token] = child }
            }
        }
    }

    // Scheduler/global participant only. This deliberately does not claim to
    // capture the native owner graph, which must be archived and reconstructed
    // separately before the candidate scene can replace the live scene.
    struct SchedulerSavedState: Codable, Equatable {
        let actors: ClawSnapshotValue<ClawSceneActorGlobals>
        let stage: ClawSnapshotValue<ClawSceneStageState>
        let destruction: ClawSnapshotValue<ClawActorDestructionGlobals>
        let core: ClawSnapshotValue<ClawCoreRegistrationGlobals>
        let clock: ClawSnapshotValue<ClawClockState>
        let held: UInt32, pressed: UInt32, fault: UInt32, lastPassCount: UInt32
        let unresolvedDependencies: Set<UInt32>, adaptedDependencies: Set<UInt32>
        let animationCounts: [UInt32: UInt64], spatialCalls: [UInt32: UInt64]
        let sceneryTokens: Set<UInt32>, pendingPickupTokens: Set<UInt32>
        let fadeRequests: [ClawSnapshotValue<ClawSceneActorCall>]
        let registryEntries: [String: UInt32], namesByToken: [UInt32: String]
        let windowReceiver: UInt32, cameraActorToken: UInt32
        let connectionCallbacks: Set<UInt32>
    }
    func savedSchedulerState() throws -> SchedulerSavedState {
        guard snapshotFrameDepth == 0 else { throw ClawSnapshotError.activeFrame }
        return SchedulerSavedState(
            actors: ClawSnapshotValue(globals.pointee), stage: ClawSnapshotValue(stage.pointee),
            destruction: ClawSnapshotValue(destruction.pointee), core: ClawSnapshotValue(core.pointee),
            clock: ClawSnapshotValue(clockSnapshot), held: held, pressed: pressed, fault: fault, lastPassCount: lastPassCount,
            unresolvedDependencies: unresolvedDependencies, adaptedDependencies: adaptedDependencies,
            animationCounts: animationCounts, spatialCalls: spatialCalls, sceneryTokens: sceneryTokens,
            pendingPickupTokens: pendingPickupTokens, fadeRequests: fadeRequests.map(ClawSnapshotValue.init),
            registryEntries: registryEntries, namesByToken: namesByToken, windowReceiver: windowReceiver,
            cameraActorToken: cameraActorToken, connectionCallbacks: connectionCallbacks)
    }
    func restoreSchedulerState(_ value: SchedulerSavedState) throws {
        guard snapshotFrameDepth == 0 else { throw ClawSnapshotError.activeFrame }
        guard value.windowReceiver == windowReceiver, value.cameraActorToken == cameraActorToken,
            value.connectionCallbacks == connectionCallbacks
        else { throw ClawSnapshotError.invalidState }
        globals.pointee = value.actors.value
        stage.pointee = value.stage.value
        destruction.pointee = value.destruction.value
        core.pointee = value.core.value
        clockSnapshot = value.clock.value
        held = value.held
        pressed = value.pressed
        faultStorage.pointee = value.fault
        lastPassCount = value.lastPassCount
        unresolvedDependencies = value.unresolvedDependencies
        adaptedDependencies = value.adaptedDependencies
        animationCounts = value.animationCounts
        spatialCalls = value.spatialCalls
        sceneryTokens = value.sceneryTokens
        pendingPickupTokens = value.pendingPickupTokens
        fadeRequests = value.fadeRequests.map(\.value)
        registryEntries = value.registryEntries
        namesByToken = value.namesByToken
    }

    // Complete source42abf0 reset, shared with the original special-command
    // controller. Checkpoint save runs this while the live scanner owns actors.

    // MARK: - Source clock and animation services

    func resetSourceClock(application: UInt32) -> UInt32 {
        var g = ClawSpecialCommandGlobals(), result: UInt32 = 0
        g.managerToken = application
        g.playerToken = 0x10002000
        g.clock = clockSnapshot
        g.stage = stage.pointee.stage
        g.animation = globals.pointee.animation
        let done = withUnsafeMutablePointer(to: &g) { p -> UInt32 in
            var context = ClawSpecialCommandContext(scene: actorHost, globals: p, fault: 0)
            let completed = claw_special_command_entry(0x42abf0, application, nil, 0, &context, nil, nil, &result)
            if context.fault != 0 { faultStorage.pointee = context.fault }
            return completed
        }
        if done != 1 {
            faultStorage.pointee = 1
            unresolvedDependencies.insert(0x42abf0)
        }
        var timing = ClawPlayerDeathCommandGlobals()
        timing.clock = g.clock
        timing.stage = g.stage
        timing.animation = g.animation
        publishDeathTiming(timing)
        withUnsafeBytes(of: &g.clock) {
            UnsafeMutableRawPointer(heap.lookup(0x541328, words: 5)!).copyMemory(from: $0.baseAddress!, byteCount: 20)
        }
        _ = importPlayerFromHeap()
        return result
    }

    func actorAnimation(function: UInt32, receiver: UInt32, argument0: UInt32, argument1: UInt32) -> UInt32 {
        animationCounts[function, default: 0] &+= 1
        var animationGlobals = ClawActorAnimationGlobals(
            animationDelta: animationDelta,
            audioPosition: player.audio?.routing.masterVolume ?? 0)
        var result: UInt32 = 0
        if claw_actor_animation_entry(
            function, receiver, argument0, argument1,
            &animationGlobals, host, faultStorage, &result) == 0
        {
            unresolvedDependencies.insert(function)
        }
        return result
    }

    func namedAnimation(function: UInt32, actor: UInt32, name: String, eager: UInt32 = 0) -> UInt32 {
        // Synchronous name transport keeps a real native token throughout the
        // source lookup. Resource dictionaries remain explicit host services.
        let bytes = Array(name.utf8) + [UInt8(0)], token = heap.allocate(bytes: UInt32(name.utf8.count + 1))
        guard token != 0, let span = heap.lookup(token, words: UInt32((bytes.count + 3) / 4)) else {
            faultStorage.pointee = 1
            return 0
        }
        bytes.withUnsafeBytes { UnsafeMutableRawPointer(span).copyMemory(from: $0.baseAddress!, byteCount: $0.count) }
        namesByToken[token] = name
        defer {
            namesByToken.removeValue(forKey: token)
            heap.free(token)
        }
        return actorAnimation(function: function, receiver: actor, argument0: token, argument1: eager)
    }
    private func sceneryCallback(_ function: UInt32, actor: UInt32) {
        var context = ClawSceneryLogicContext()
        context.scene = host
        context.composeAnimation = 1
        context.settingsToken = heap.lookup(ownerToken, words: 2)![1]
        context.animation = ClawActorAnimationGlobals(
            animationDelta: animationDelta, audioPosition: player.audio?.routing.masterVolume ?? 0)
        var result: UInt32 = 0
        if claw_scenery_logic_entry(function, actor, &context, &result) != 1 || context.fault != 0 {
            faultStorage.pointee = max(1, context.fault)
        }
    }

    // MARK: - Heap actor traversal and snapshot transfer

    var actorTokens: [UInt32] {
        guard let container = heap.lookup(containerToken, words: 11) else { return [] }
        var node = container[5], result: [UInt32] = [], visited: Set<UInt32> = []
        while node != 0 {
            guard visited.insert(node).inserted, let span = heap.lookup(node, words: 3) else { return [] }
            result.append(span[2])
            node = span[0]
        }
        return result
    }

    func snapshotActor(_ token: UInt32) -> ClawInteractionActor? {
        guard let actor = heap.lookup(token, words: 128) else { return nil }
        var result = ClawInteractionActor()
        result.token = token
        withUnsafeMutableBytes(of: &result.actor) { $0.copyMemory(from: UnsafeRawBufferPointer(start: actor, count: 512)) }
        func copy<T>(_ value: inout T, from token: UInt32) -> Bool {
            if token == 0 { return true }
            guard let source = heap.lookup(token, words: 93) else { return false }
            withUnsafeMutableBytes(of: &value) { $0.copyMemory(from: UnsafeRawBufferPointer(start: source, count: 372)) }
            return true
        }
        guard copy(&result.primary, from: actor[27]), copy(&result.secondary, from: actor[28]),
            copy(&result.contact, from: actor[30])
        else { return nil }
        return result
    }

    func write(_ value: ClawInteractionActor, copyPlayerPrivate: Bool = true) {
        guard let actor = heap.lookup(value.token, words: 128) else {
            faultStorage.pointee = 1
            return
        }
        var copy = value
        withUnsafeBytes(of: &copy.actor) { UnsafeMutableRawBufferPointer(start: actor, count: 512).copyMemory(from: $0) }
        for (token, offset) in [
            (actor[27], MemoryLayout<ClawInteractionActor>.offset(of: \.primary)!),
            (actor[28], MemoryLayout<ClawInteractionActor>.offset(of: \.secondary)!),
            (actor[30], MemoryLayout<ClawInteractionActor>.offset(of: \.contact)!)
        ] where token != 0 {
            guard let target = heap.lookup(token, words: 93) else {
                faultStorage.pointee = 1
                continue
            }
            withUnsafeBytes(of: &copy) { bytes in
                UnsafeMutableRawBufferPointer(start: target, count: 372).copyMemory(
                    from: UnsafeRawBufferPointer(rebasing: bytes[offset..<offset + 372]))
            }
        }
        if copyPlayerPrivate, value.token == 0x10002000, let target = heap.lookup(value.primary.5, words: 78) {
            withUnsafeBytes(of: player.runtime.privateWords) {
                UnsafeMutableRawBufferPointer(start: target, count: 312).copyMemory(from: $0)
            }
        }
    }

    // MARK: - Scene service dispatch

    func performService(_ call: ClawSceneActorCall) -> UInt32 { dispatch(call) }

    // Service checks are ordered: earlier owners may consume a shared entry.
    // Preserve each service result and its fault publication before proceeding.
    fileprivate func dispatch(_ call: ClawSceneActorCall) -> UInt32 {
        if call.function == 0x48e430, let connections = objectConnections,
            let stager = connections.adapter("boss_stager") as? ClawNativeBossStager
        {
            guard call.receiver == 0, call.argumentCount == 1 else {
                connections.reject(call.function)
                faultStorage.pointee = UInt32(CLAW_FAULT_ABI)
                return 0
            }
            let value = stager.invoke(call.function, actor: call.arguments.0) ?? 0
            if let fault = connections.host.fault {
                faultStorage.pointee = fault.code
                unresolvedDependencies.insert(fault.address)
            }
            return value
        }
        if call.function == 0x4b8910 {
            guard fault == 0, call.argumentCount == 2, call.receiver == windowReceiver,
                windowReceiver != 0, let windowInput
            else {
                unresolvedDependencies.insert(call.function)
                faultStorage.pointee = 1
                return 0
            }
            do {
                try windowInput.queue.drain(message: call.arguments.0, maximum: call.arguments.1) {
                    guard let receiver = self.heap.lookup(call.receiver, words: 2) else {
                        throw ClawNativeWindowInputQueue.Failure.missingWindow
                    }
                    return receiver[1]
                }
                adaptedDependencies.insert(call.function)
            } catch {
                unresolvedDependencies.insert(call.function)
                faultStorage.pointee = 1
            }
            return 0  // Semantic void, never a removed-count result.
        }
        if let value = frameRuntime?.platform(call) {
            if call.function != 0x4025c0 || ambientAudio == nil { adaptedDependencies.insert(call.function) }
            if let frameRuntime, frameRuntime.fault != 0 { faultStorage.pointee = frameRuntime.fault }
            return value
        }
        if ClawNativeSpeech.services.contains(call.function), let speech {
            let arguments = withUnsafeBytes(of: call.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(call.argumentCount))) }
            let value = speech.service(call.function, receiver: call.receiver, arguments: arguments) ?? 0
            if speech.fault != 0 { faultStorage.pointee = speech.fault }
            return value
        }
        if ClawNativeBreakables.owned.contains(call.function) && !ClawNativeBreakables.callbacks.contains(call.function),
            let component = breakables
        {
            let args = withUnsafeBytes(of: call.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(call.argumentCount))) }
            let result = component.invoke(call.function, receiver: call.receiver, arguments: args)
            if component.fault != 0 { faultStorage.pointee = component.fault }
            return result
        }
        if ClawNativeHUD.services.contains(call.function), let hud {
            let args = withUnsafeBytes(of: call.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(call.argumentCount))) }
            let result = hud.entry(call.function, receiver: call.receiver, args: args)
            if hud.fault != 0 {
                faultStorage.pointee = hud.fault
                unresolvedDependencies.formUnion(hud.unresolved)
            }
            return result
        }
        if call.function == 0x484d90, let p = projectiles, p.privateOwners[call.receiver] != nil {
            let result = p.entry(call.function, receiver: call.receiver, args: [call.arguments.0])
            if p.fault != 0 {
                faultStorage.pointee = p.fault
                unresolvedDependencies.formUnion(p.unresolved)
            }
            return result
        }
        if call.function == 0x484d90, let p = flares, p.privateOwners[call.receiver] != nil {
            let result = p.entry(call.function, receiver: call.receiver, args: [call.arguments.0])
            if p.fault != 0 {
                faultStorage.pointee = p.fault
                unresolvedDependencies.formUnion(p.unresolved)
            }
            return result
        }
        if let crazyHook = objectConnections?.adapter("crazy_hook") as? ClawNativeCrazyHook {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = crazyHook.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = crazyHook.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let pirate = objectConnections?.adapter("red_tail_pirate") as? ClawNativeRedTailPirate {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = pirate.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = pirate.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let redTail = objectConnections?.adapter("red_tail") as? ClawNativeRedTail {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = redTail.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = redTail.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let chameleon = objectConnections?.adapter("chameleon") as? ClawNativeChameleon {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = chameleon.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = chameleon.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let omar = objectConnections?.adapter("omar") as? ClawNativeOmar {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = omar.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = omar.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let raux = objectConnections?.adapter("raux") as? ClawNativeRaux {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = raux.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = raux.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let punkRat = objectConnections?.adapter("punk_rat") as? ClawNativePunkRat {
            if call.function == 0x4c9be0, let result = punkRat.destroyChildActor(call.receiver, flags: call.arguments.0) {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return result
            }
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = punkRat.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = punkRat.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let tigerGuard = objectConnections?.adapter("tiger_guard") as? ClawNativeTigerGuard {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = tigerGuard.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = tigerGuard.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let mercat = objectConnections?.adapter("mercat") as? ClawNativeMercat {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = mercat.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = mercat.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let parrot = objectConnections?.adapter("parrot") as? ClawNativeParrot {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = parrot.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = parrot.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let fish = objectConnections?.adapter("fish") as? ClawNativeFish {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = fish.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = fish.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let seagull = objectConnections?.adapter("seagull") as? ClawNativeSeagull {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = seagull.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = seagull.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let cutThroat = objectConnections?.adapter("cut_throat") as? ClawNativeCutThroat {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = cutThroat.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = cutThroat.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let guard1 = objectConnections?.adapter("town_guard1") as? ClawNativeTownGuard1 {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = guard1.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = guard1.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let robber = objectConnections?.adapter("robber_thief") as? ClawNativeRobberThief {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = robber.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = robber.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let hermit = objectConnections?.adapter("hermit_crab") as? ClawNativeHermitCrab {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = hermit.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = hermit.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let guard2 = objectConnections?.adapter("town_guard2") as? ClawNativeTownGuard2 {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = guard2.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = guard2.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if call.function == 0x4c9be0,
            let nest = objectConnections?.adapter("crab_nest") as? ClawNativeCrabNest,
            nest.prepareActorDestruction(call.receiver) == false
        {
            if let fault = objectConnections?.host.fault {
                faultStorage.pointee = fault.code
                unresolvedDependencies.insert(fault.address)
            }
            return 0
        }
        if call.function == 0x4c80c0 || call.function == 0x4c80e0,
            let nest = objectConnections?.adapter("crab_nest") as? ClawNativeCrabNest,
            nest.prepareLogicDestruction(call.receiver) == false
        {
            if let fault = objectConnections?.host.fault {
                faultStorage.pointee = fault.code
                unresolvedDependencies.insert(fault.address)
            }
            return 0
        }
        if call.function == 0x4c9be0,
            let vent = objectConnections?.adapter("goo_vent") as? ClawNativeGooVent,
            vent.prepareActorDestruction(call.receiver) == false
        {
            if let fault = objectConnections?.host.fault {
                faultStorage.pointee = fault.code
                unresolvedDependencies.insert(fault.address)
            }
            return 0
        }
        if call.function == 0x4c80c0 || call.function == 0x4c80e0,
            let vent = objectConnections?.adapter("goo_vent") as? ClawNativeGooVent,
            vent.prepareLogicDestruction(call.receiver) == false
        {
            if let fault = objectConnections?.host.fault {
                faultStorage.pointee = fault.code
                unresolvedDependencies.insert(fault.address)
            }
            return 0
        }
        if let button = objectConnections?.adapter("cannon_button") as? ClawNativeCannonButton {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = button.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = button.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let cannonSwitch = objectConnections?.adapter("cannon_switch") as? ClawNativeCannonSwitch {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = cannonSwitch.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = cannonSwitch.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let projectile = objectConnections?.adapter("t_projectile") as? ClawNativeTProjectile {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = projectile.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = projectile.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let jumpSwitch = objectConnections?.adapter("jump_switch") as? ClawNativeJumpSwitch {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = jumpSwitch.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = jumpSwitch.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let blower = objectConnections?.adapter("ground_blower") as? ClawNativeGroundBlower {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = blower.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = blower.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let crack = objectConnections?.adapter("aquatis_crack") as? ClawNativeAquatisCrack {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = crack.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = crack.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let stalactite = objectConnections?.adapter("aquatis_stalactite") as? ClawNativeAquatisStalactite {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = stalactite.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = stalactite.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let dynamite = objectConnections?.adapter("aquatis_dynamite") as? ClawNativeAquatisDynamite {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = dynamite.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = dynamite.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let wind = objectConnections?.adapter("red_tail_wind") as? ClawNativeRedTailWind {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = wind.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = wind.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let spikes = objectConnections?.adapter("red_tail_spikes") as? ClawNativeRedTailSpikes {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = spikes.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = spikes.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let geyser = objectConnections?.adapter("lava_geyser") as? ClawNativeLavaGeyser {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = geyser.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = geyser.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let hand = objectConnections?.adapter("lava_hand") as? ClawNativeLavaHand {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = hand.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = hand.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let mouth = objectConnections?.adapter("lava_mouth") as? ClawNativeLavaMouth {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = mouth.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = mouth.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let shake = objectConnections?.adapter("shake") as? ClawNativeShake {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = shake.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = shake.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let laser = objectConnections?.adapter("laser") as? ClawNativeLaser {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = laser.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = laser.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let floor = objectConnections?.adapter("marrow_floor") as? ClawNativeMarrowFloor {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = floor.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = floor.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let belt = objectConnections?.adapter("conveyor_belt") as? ClawNativeConveyorBelt {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = belt.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = belt.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let marrow = objectConnections?.adapter("marrow") as? ClawNativeMarrow {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = marrow.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = marrow.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let pegLeg = objectConnections?.adapter("peg_leg") as? ClawNativePegLeg {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = pegLeg.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = pegLeg.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let bearSailor = objectConnections?.adapter("bear_sailor") as? ClawNativeBearSailor {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = bearSailor.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = bearSailor.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let tentacle = objectConnections?.adapter("tentacle") as? ClawNativeTentacle {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = tentacle.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = tentacle.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let siren = objectConnections?.adapter("siren") as? ClawNativeSiren {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = siren.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = siren.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        if let stalactite = objectConnections?.adapter("stalactite") as? ClawNativeStalactite {
            let prepared: Bool?
            if call.function == 0x4c9be0 {
                prepared = stalactite.prepareActorDestruction(call.receiver)
            } else if call.function == 0x4c80c0 || call.function == 0x4c80e0 {
                prepared = stalactite.prepareLogicDestruction(call.receiver)
            } else {
                prepared = nil
            }
            if prepared == false {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return 0
            }
        }
        var result: UInt32 = 0
        if claw_actor_destruction_entry(
            call.function, call.receiver, call.arguments.0,
            destruction, host, faultStorage, &result) == 1
        {
            if call.function == 0x4c9be0 && heap.lookup(call.receiver, words: 1) == nil {
                enemies.removeValue(forKey: call.receiver)
                humanoids.removeValue(forKey: call.receiver)
                sceneryTokens.remove(call.receiver)
                bullets.removeValue(forKey: call.receiver)
                loot?.remove(call.receiver)
                effects?.remove(call.receiver)
                platforms?.remove(call.receiver)
                pegs?.remove(call.receiver)
                soundTriggers?.remove(call.receiver)
                singleCrates?.remove(call.receiver)
                checkpoints?.remove(call.receiver)
                breakables?.remove(call.receiver)
                projectiles?.remove(call.receiver)
                flares?.remove(call.receiver)
                objectConnections?.remove(call.receiver)
                (objectConnections?.adapter("boss_warp") as? ClawNativeBossWarp)?.remove(call.receiver)
                (objectConnections?.adapter("boss_stager") as? ClawNativeBossStager)?.remove(call.receiver)
            }
            return result
        }
        switch call.function {
        case 0x46c860, 0x486240:
            guard let camera else {
                adaptedDependencies.insert(call.function)
                return 0
            }
            camera.synchronize(
                stageDelta: stage.pointee.stage.deltaMilliseconds,
                animationNow: globals.pointee.animation.nowMilliseconds, animationDelta: animationDelta)
            let receiver = call.function == 0x486240 ? call.arguments.0 : call.receiver
            let result = camera.entry(call.function, receiver: receiver)
            if camera.fault != 0 { faultStorage.pointee = camera.fault }
            if call.function == 0x46c860 {
                held = camera.held
                pressed = camera.pressed
            }
            return result
        case 0x4cb9b0:
            frameRuntime?.record(call.function)
            rendering?.render(world: call.receiver, actors: call.arguments.1)
            if let rendering, rendering.fault != 0 { faultStorage.pointee = rendering.fault }
            return 0
        case 0x4d2890:
            return rendering?.drawActor(call.arguments.0, image: call.receiver, target: call.arguments.1) ?? 0
        case 0x4c9e30:
            return 0  // Original plain actor's empty draw method (RET4).
        case 0x4a3040, 0x4a7dc0:
            let args = withUnsafeBytes(of: call.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(call.argumentCount))) }
            let result = random.call(call.function, arguments: args)
            if random.fault != 0 { faultStorage.pointee = random.fault }
            return result
        case 0x4a3050: return nextRandom()
        case 0x4d1fd0, 0x4d2000:
            frameRuntime?.record(call.function)
            return spatial(call.function, receiver: call.receiver)
        case 0x4d17e0:
            return loadGridObject(plane: call.receiver, record: call.arguments.0)
        case 0x4c88e0:
            return player.audio?.playSpatial(
                resource: call.receiver, sourceX: call.arguments.0, referenceX: call.arguments.1, clampDistance: call.arguments.2,
                panDistance: call.arguments.3) ?? 0
        case 0x4208e0:
            return player.audio?.play(resource: call.receiver, volume: call.arguments.0) ?? 0
        case 0x4061b0:
            guard let name = clawOriginalResourceNames[call.arguments.0] else { return 0 }
            return player.audio?.resolve(name: name)?.resourceToken ?? 0
        case 0x496840:
            if let guard1 = objectConnections?.adapter("town_guard1") as? ClawNativeTownGuard1,
                let value = guard1.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return value
            }
            unresolvedDependencies.insert(call.function)
            faultStorage.pointee = UInt32(CLAW_FAULT_ABI)
            return 0
        case 0x49f020:
            if let elevator = objectConnections?.adapter("path_elevator") as? ClawNativePathElevator,
                let value = elevator.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return value
            }
            unresolvedDependencies.insert(call.function)
            faultStorage.pointee = UInt32(CLAW_FAULT_ABI)
            return 0
        case 0x407bd0:
            if let stalactite = objectConnections?.adapter("aquatis_stalactite") as? ClawNativeAquatisStalactite,
                let result = stalactite.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return result
            }
            unresolvedDependencies.insert(call.function)
            faultStorage.pointee = UInt32(CLAW_FAULT_ABI)
            return 0
        case 0x484d90:
            if let wind = objectConnections?.adapter("red_tail_wind") as? ClawNativeRedTailWind,
                let result = wind.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return result
            }
            if let spikes = objectConnections?.adapter("red_tail_spikes") as? ClawNativeRedTailSpikes,
                let result = spikes.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return result
            }
            if let geyser = objectConnections?.adapter("lava_geyser") as? ClawNativeLavaGeyser,
                let result = geyser.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return result
            }
            if let hand = objectConnections?.adapter("lava_hand") as? ClawNativeLavaHand,
                let result = hand.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return result
            }
            if let mouth = objectConnections?.adapter("lava_mouth") as? ClawNativeLavaMouth,
                let result = mouth.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return result
            }
            if let stalactite = objectConnections?.adapter("stalactite") as? ClawNativeStalactite,
                let result = stalactite.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return result
            }
            if let crack = objectConnections?.adapter("aquatis_crack") as? ClawNativeAquatisCrack,
                let result = crack.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return result
            }
            if let dynamite = objectConnections?.adapter("aquatis_dynamite") as? ClawNativeAquatisDynamite,
                let result = dynamite.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return result
            }
            if let floor = objectConnections?.adapter("marrow_floor") as? ClawNativeMarrowFloor,
                let value = floor.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return value
            }
            if let button = objectConnections?.adapter("cannon_button") as? ClawNativeCannonButton,
                let value = button.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return value
            }
            if let cannonSwitch = objectConnections?.adapter("cannon_switch") as? ClawNativeCannonSwitch,
                let value = cannonSwitch.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return value
            }
            if let projectile = objectConnections?.adapter("t_projectile") as? ClawNativeTProjectile,
                let value = projectile.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return value
            }
            if let belt = objectConnections?.adapter("conveyor_belt") as? ClawNativeConveyorBelt,
                let value = belt.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return value
            }
            if let nest = objectConnections?.adapter("crab_nest") as? ClawNativeCrabNest,
                let value = nest.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return value
            }
            if let vent = objectConnections?.adapter("goo_vent") as? ClawNativeGooVent,
                let value = vent.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return value
            }
            if let jumpSwitch = objectConnections?.adapter("jump_switch") as? ClawNativeJumpSwitch,
                let value = jumpSwitch.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return value
            }
            if let blower = objectConnections?.adapter("ground_blower") as? ClawNativeGroundBlower,
                let value = blower.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return value
            }
            if let laser = objectConnections?.adapter("laser") as? ClawNativeLaser,
                let value = laser.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return value
            }
            if let plank = objectConnections?.adapter("break_plank") as? ClawNativeBreakPlank,
                let value = plank.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return value
            }
            if let tower = objectConnections?.adapter("tower_cannon_right") as? ClawNativeTowerCannonRight,
                let value = tower.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault { faultStorage.pointee = fault.code }
                return value
            }
            if let tower = objectConnections?.adapter("tower_cannon_left") as? ClawNativeTowerCannonLeft,
                let value = tower.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault { faultStorage.pointee = fault.code }
                return value
            }
            if let cannon = objectConnections?.adapter("skull_cannon") as? ClawNativeSkullCannon,
                let value = cannon.destructHelper(call.receiver, flags: call.arguments.0)
            {
                if let fault = objectConnections?.host.fault {
                    faultStorage.pointee = fault.code
                    unresolvedDependencies.insert(fault.address)
                }
                return value
            }
            if let value = breakables?.stackDestructor(receiver: call.receiver, flags: call.arguments.0) {
                if let component = breakables, component.fault != 0 { faultStorage.pointee = component.fault }
                return value
            }
            if let enemy = enemies.values.first(where: { $0.generic.pointee.enemyToken == call.receiver }) {
                return enemy.callback(call.function, argument: call.arguments.0)
            }
            if let bullet = bullets.values.first(where: { $0.generic.pointee.enemyToken == call.receiver }) {
                return bullet.callback(call.function, argument: call.arguments.0)
            }
            if let result = loot?.privateDestructor(receiver: call.receiver, flags: call.arguments.0) { return result }
            unresolvedDependencies.insert(call.function)
            return 0
        case 0x462a00, 0x48afd0:
            guard let body = humanoids.values.first(where: { $0.generic.pointee.enemyToken == call.receiver }) else {
                unresolvedDependencies.insert(call.function)
                return 0
            }
            return body.callback(call.function, argument: call.arguments.0)
        case 0x4dc560:
            _ = claw_core_registration_entry(
                call.function, call.receiver, call.arguments.0,
                call.arguments.1, core, host, faultStorage, &result)
            return result
        case 0x4a49b0:
            freeActorStorage(call.arguments.0)
            return 0
        case 0x4f6286:
            return resolveResource(dictionary: call.receiver, name: call.arguments.0)
        case 0x415df0:
            guard call.arguments.0 == 0x10002000, let snapshot = snapshotActor(call.arguments.0) else {
                faultStorage.pointee = 1
                return 0
            }
            guard let words = heap.lookup(snapshot.primary.5, words: 78) else {
                faultStorage.pointee = 1
                return 0
            }
            player.acceptSceneSnapshot(snapshot, privateWords: UnsafePointer(words))
            player.advance(
                held: camera?.held ?? held, pressed: camera?.pressed ?? pressed, stageDelta: stage.pointee.stage.deltaMilliseconds,
                animationDelta: globals.pointee.animation.deltaMilliseconds)
            write(player.sceneSnapshot())
            return 0
        case 0x4c9390:
            runInteractions()
            return 0
        case 0x4bb030: return 0  // Recovered common no-op callback.
        case 0x4a35f0:
            // Process-exit registration remains a native lifetime service.
            adaptedDependencies.insert(call.function)
            return 0
        default:
            if let body = gameplay[call.function] {
                body(call.arguments.0)
                return 0
            }
            unresolvedDependencies.insert(call.function)
            return 0
        }
    }

    // MARK: - Interaction scan and callback publication

    private func runInteractions() {
        let tokens = actorTokens
        let buffers = UnsafeMutablePointer<ClawInteractionActor>.allocate(capacity: max(1, tokens.count))
        buffers.initialize(repeating: ClawInteractionActor(), count: max(1, tokens.count))
        defer {
            buffers.deinitialize(count: max(1, tokens.count))
            buffers.deallocate()
        }
        for (index, token) in tokens.enumerated() {
            guard let snapshot = snapshotActor(token) else {
                faultStorage.pointee = 1
                return
            }
            buffers[index] = snapshot
        }
        let completed = claw_actor_interactions(
            buffers, tokens.count,
            { actors, count, event, context in
                guard let actors, let event, let context else { return }
                Unmanaged<ClawNativeScene>.fromOpaque(context).takeUnretainedValue().interaction(actors, count: count, event: event.pointee)
            }, Unmanaged.passUnretained(self).toOpaque())
        if completed == 0 { faultStorage.pointee = 1 }
        for index in tokens.indices { write(buffers[index], copyPlayerPrivate: false) }
    }

    private func interaction(_ actors: UnsafeMutablePointer<ClawInteractionActor>, count: Int, event: ClawActorInteractionCall) {
        for index in 0..<count { write(actors[index], copyPlayerPrivate: false) }
        if event.function == 0x41ce80 && event.actorToken == 0x10002000,
            let defender = snapshotActor(event.actorToken), let attacker = snapshotActor(event.peerToken)
        {
            guard let privateWords = heap.lookup(defender.primary.5, words: 78) else {
                faultStorage.pointee = 1
                return
            }
            player.acceptSceneSnapshot(defender, privateWords: UnsafePointer(privateWords))
            if attacker.actor.52 == 0x100, let special = specialPowerups, special.originalRecords[event.peerToken] != nil {
                special.electedPlayerHit(event.peerToken)
                if special.fault != 0 {
                    faultStorage.pointee = special.fault
                    unresolvedDependencies.formUnion(special.unresolved)
                }
                for index in 0..<count { if let changed = snapshotActor(actors[index].token) { actors[index] = changed } }
                return
            }
            if let pickup = loot?.pickups[event.peerToken], !(attacker.actor.52 == 0x10000 && Int32(bitPattern: attacker.actor.63) > 100) {
                _ = pickup.electedPlayerHit()
                for index in 0..<count { if let changed = snapshotActor(actors[index].token) { actors[index] = changed } }
                return
            }
            var object = ClawWorldObjectRuntime()
            object.actor = attacker.actor
            object.logic = attacker.primary
            player.receiveHit(from: &object, token: event.peerToken)
            write(player.sceneSnapshot())
            var changed = attacker
            changed.actor = object.actor
            changed.primary = object.logic
            write(changed)
        } else if let body = gameplay[event.function] {
            body(event.actorToken)
        } else {
            unresolvedDependencies.insert(event.function)
        }
        for index in 0..<count {
            if let snapshot = snapshotActor(actors[index].token) { actors[index] = snapshot } else { faultStorage.pointee = 1 }
        }
    }

    private func humanoidService(_ call: ClawGenericEnemyCall) -> UInt64? {
        if call.function == 0x461a00 || call.function == 0x461c40, let effects {
            let arguments = withUnsafeBytes(of: call.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(call.argumentCount))) }
            let value = effects.impactEntry(call.function, arguments: arguments)
            if effects.fault != 0 { faultStorage.pointee = effects.fault }
            return UInt64(value)
        }
        if call.function == 0x42df90, let loot { return loot.lootDrop(receiver: call.receiver) ? 1 : 0 }
        if ClawNativeSpeech.services.contains(call.function), let speech {
            let arguments = withUnsafeBytes(of: call.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(call.argumentCount))) }
            if let value = speech.service(
                call.function, receiver: call.receiver, arguments: arguments, name: call.name.map { String(cString: $0) })
            {
                if speech.fault != 0 { faultStorage.pointee = speech.fault }
                return UInt64(value)
            }
        }
        return nil
    }
}

extension ClawSceneActorGlobals: ClawSnapshotNativeValue {}
extension ClawSceneStageState: ClawSnapshotNativeValue {}
extension ClawActorDestructionGlobals: ClawSnapshotNativeValue {}
extension ClawCoreRegistrationGlobals: ClawSnapshotNativeValue {}
extension ClawSceneActorCall: ClawSnapshotNativeValue {}

// Native application lifecycle boundary for the original error receiver.
// The first report latches before posting close; code/detail publish afterward.
// A physical service fault remains distinct from a completed error report.
final class ClawNativeApplicationError {
    let heap: ClawTokenHeap
    let receiver: UInt32
    private let postClose: ((UInt32) throws -> Void)?
    var observePostClose: ((UInt32) -> Void)?
    var physicalAvailable: ((UInt32) -> Bool)?
    private var closed = false
    private(set) var faultAddress: UInt32 = 0
    init(heap: ClawTokenHeap, receiver: UInt32, postClose: ((UInt32) throws -> Void)?) {
        self.heap = heap
        self.receiver = receiver
        self.postClose = postClose
    }
    func close() { closed = true }
    func service(_ q: ClawCall) -> UInt32? {
        guard q.function == 0x4b90b0 else { return nil }
        guard faultAddress == 0 else { return nil }
        guard !closed, q.receiver == receiver, q.argumentCount == 2, q.receiver2 == 0,
            q.x87ArgumentCount == 0, let record = heap.lookup(receiver, words: 0x254 / 4)
        else {
            faultAddress = q.function
            return nil
        }
        if record[0x248 / 4] != 0 { return 0 }
        record[0x248 / 4] = 1
        if record[1] != 0 {
            guard let window = heap.lookup(record[1], words: 4) else {
                faultAddress = q.function
                return nil
            }
            if window[3] == 0 {
                guard physicalAvailable?(0x546d50) != false, let postClose else {
                    faultAddress = 0x546d50
                    return nil
                }
                do {
                    try postClose(window[1])
                    observePostClose?(window[1])
                } catch {
                    faultAddress = 0x546d50
                    return nil
                }
            }
        }
        record[0x244 / 4] = 0
        record[0x24c / 4] = q.arguments.0
        record[0x250 / 4] = q.arguments.1
        return 0
    }
    func service(_ host: ClawNativeCanonicalHost, _ q: ClawCall) -> UInt32? {
        guard q.function == 0x4b90b0 else { return nil }
        guard host.heap === heap, host.fault == nil else {
            host.fail(UInt32(CLAW_FAULT_HOST), at: q.function)
            return nil
        }
        let result = service(q)
        if let result { return result }
        host.fail(UInt32(CLAW_FAULT_HOST), at: faultAddress)
        return nil
    }
}

// Menu startup owns a scene without a player, WWD, actor loader or level palette.
// The supplied literals are local asset metadata, extracted from the pinned
// reference by the test runner; binary-derived bytes are not embedded here.
final class ClawNativeMenuBase {
    let heap = ClawTokenHeap()
    weak var sharedMenuResources: ClawNativeMenuResources?
    let windowInput: ClawNativeWindowInput?
    private(set) var windowReceiver: UInt32 = 0
    private(set) var applicationToken: UInt32 = 0, sceneToken: UInt32 = 0, menuToken: UInt32 = 0
    private(set) var resourceRootToken: UInt32 = 0
    private(set) var soundManager: UInt32 = 0
    private(set) var audio: ClawNativeAudio?
    private(set) var soundLoadCount: UInt32 = 0
    private(set) var soundEvents: [UInt32] = []
    private(set) var resourceBlocks: [(token: UInt32, bytes: UInt32)] = []
    private(set) var soundResources: [UInt32: String] = [:]
    private(set) var soundEntries: [String: UInt32] = [:]
    private var resourceTables: Set<UInt32> = []
    private var soundAllocations: Set<UInt32> = []
    private let soundStack: UInt32 = 0x02008000
    private(set) var soundCleanupFault: UInt32 = 0
    private(set) var soundCleanupRemaining: Int = 0
    private(set) var palette: ClawNativePaletteResources?
    private(set) var calls: [UInt32] = [], fault: UInt32 = 0, boundary: UInt32 = 0
    private(set) var constructorAllocations: [(token: UInt32, bytes: UInt32)] = []
    private(set) var applicationResult: UInt32?
    private(set) var applicationErrors: ClawNativeApplicationError?
    private let image = UnsafeMutablePointer<ClawGameImageGlobals>.allocate(capacity: 1)
    private let sourceHost = UnsafeMutablePointer<ClawHost>.allocate(capacity: 1)
    private var directories: [UInt32: URL] = [:], directoryTokens: [String: UInt32] = [:]
    var resourceDirectories: [UInt32: String] { directories.mapValues { $0.path } }
    private var interfaceScratch: UInt32 = 0, interfaceFile: UInt32 = 0, interfaceArchive: UInt32 = 0
    private var initialized = false
    private var missingSpan: UInt32 = 0
    // Tests may remove one owner to check rejection; normal startup elects all.
    let missingOwner: UInt32?
    private static let ready: UInt32 = 0x6e130000

    init(
        root: URL, literals: [UInt32: Data], missingOwner: UInt32? = nil, audioAvailable: Bool = true,
        windowInput: ClawNativeWindowInput? = ClawNativeWindowInput()
    ) throws {
        self.missingOwner = missingOwner
        self.windowInput = windowInput
        image.initialize(to: ClawGameImageGlobals())
        sourceHost.initialize(to: ClawHost())
        sourceHost.pointee.user = Unmanaged.passUnretained(self).toOpaque()
        sourceHost.pointee.bytes = { u, t, n in
            guard let u else { return nil }
            return Unmanaged<ClawNativeMenuBase>.fromOpaque(u).takeUnretainedValue().heap.lookupBytes(t, count: n)
        }
        sourceHost.pointee.call = { u, q in
            guard let u, let q else { return 0 }
            return Unmanaged<ClawNativeMenuBase>.fromOpaque(u).takeUnretainedValue().constructorService(q.pointee)
        }
        sourceHost.pointee.maximumOperations = 10000
        // Shared empty CString and the actual literals required by the source
        // interface constructor and base formatter, each with its source token.
        for token: UInt32 in [0x5334f0, 0x52a004, 0x52c69c, 0x528b08, 0x52372c, 0x523ce0] {
            guard let data = literals[token], data.last == 0 else { throw AssetError.invalid("Missing menu literal metadata") }
            data.copyBytes(to: heap.storeBytes(token: token, count: UInt32((data.count + 3) & ~3)), count: data.count)
        }
        heap.store(token: 0x52e1b8, words: 4)[0] = .max
        heap.store(token: 0x52e1c8, words: 1)[0] = 0x52e1b8
        heap.store(token: 0x52e1cc, words: 1)[0] = 0x52e1c4
        _ = heap.storeBytes(token: 0x01ff0000, count: 0x20000)
        _ = heap.store(token: 0x532c10, words: 1)
        heap.store(token: 0x5138b4, words: 1)[0] = 0x4ca670
        for (token, value) in [(UInt32(0x534938), ""), (0x523728, "_"), (0x532c14, "%s%s%s")] {
            let bytes = Array(value.utf8) + [0]
            bytes.withUnsafeBytes {
                heap.storeBytes(token: token, count: UInt32(bytes.count)).update(
                    from: $0.baseAddress!.assumingMemoryBound(to: UInt8.self), count: bytes.count)
            }
        }
        _ = heap.store(token: 0x541328, words: 5)
        _ = heap.store(token: 0x537b58, words: 1)
        heap.store(token: 0x528a60, words: 1)[0] = 1000
        interfaceScratch = heap.allocate(bytes: 4)
        interfaceFile = heap.allocate(bytes: 40)
        interfaceArchive = heap.allocate(bytes: 68)
        applicationToken = heap.allocate(bytes: UInt32(CLAW_ORIGINAL_APPLICATION_BYTES))
        sceneToken = heap.allocate(bytes: 60)
        menuToken = heap.allocate(bytes: UInt32(CLAW_STATE_FIVE_BYTES))
        resourceRootToken = heap.allocate(bytes: 4)
        directories[resourceRootToken] = root
        var isDirectory: ObjCBool = false
        guard FileManager.default.fileExists(atPath: root.path, isDirectory: &isDirectory), isDirectory.boolValue else {
            throw AssetError.invalid("Missing native resource root")
        }
        guard baseEntry(0x4254a0, applicationToken, []) != nil,
            baseEntry(0x4ce960, sceneToken, []) != nil
        else { throw AssetError.invalid("Menu application/scene constructor") }
        let app = heap.lookup(applicationToken, words: 77)!
        if let windowInput {
            windowReceiver = heap.allocate(bytes: 16)
            heap.lookup(windowReceiver, words: 4)![1] = windowInput.window
            app[1] = windowReceiver
        }
        let errorReceiver = heap.allocate(bytes: 0x254), errorVTable = heap.allocate(bytes: 32)
        let error = heap.lookup(errorReceiver, words: 0x254 / 4)!
        // Native window creation replaces 0x4b8a1d, which enables idle frames.
        // State transitions and Pause subsequently own this same window flag.
        error[0] = errorVTable
        error[1] = windowReceiver
        error[0x244 / 4] = 1
        error[0x248 / 4] = 0
        error[0x24c / 4] = 0
        error[0x250 / 4] = 0
        heap.lookup(errorVTable, words: 8)![7] = 0x4b90b0
        app[2] = errorReceiver
        applicationErrors = ClawNativeApplicationError(
            heap: heap, receiver: errorReceiver,
            postClose: windowInput.map { input in
                { window in try input.queue.postClose(window: window) }
            })
        let nativeVT = heap.allocate(bytes: 16)
        heap.lookup(nativeVT, words: 4)![3] = Self.ready
        app[0] = nativeVT
        app[0x30 / 4] = sceneToken
        app[0x34 / 4] = resourceRootToken
        // This executes the same constructor body as retail state election.
        guard claw_application_menu_construct(menuToken, sourceHost) == 1, sourceHost.pointee.fault == 0 else {
            throw AssetError.invalid(
                "Menu constructor missing owner at \(String(sourceHost.pointee.faultAddress,radix:16)), span \(String(missingSpan,radix:16))"
            )
        }
        palette = try ClawNativePaletteResources(heap: heap, owner: menuToken, parent: sceneToken, image: image)
        // Native startup provides the dimensions of the display it just created.
        // The constructor leaves these zero; the native startup owner publishes
        // its completed display configuration before initializing a menu state.
        guard let display = palette?.display,
            let primary = heap.lookup(display.primaryToken, words: 12),
            primary[4] != 0, primary[5] != 0,
            [display.backToken, display.spareToken].allSatisfy({ token in
                guard let surface = heap.lookup(token, words: 12) else { return false }
                return surface[4] == primary[4] && surface[5] == primary[5]
            })
        else { throw AssetError.invalid("Menu display dimensions unavailable") }
        app[0x7c / 4] = primary[4]
        app[0x80 / 4] = primary[5]
        if audioAvailable {
            audio = try ClawNativeAudio(root: root, outputEnabled: !ClawNativeAudio.deterministicCheck, sharedHeap: heap, preload: false)
        }
        heap.lookup(sceneToken, words: 15)![8] = audio?.managerIdentity ?? 0
        // Native construction of the inline 4cea10 sound-manager component.
        // Poison uninitialized bytes: +0x30 must be written by 4ca280 below.
        soundManager = heap.allocate(bytes: 56)
        heap.lookupBytes(soundManager, count: 52)!.update(repeating: 0xa5, count: 52)
        guard baseEntry(0x45fde0, soundManager, [sceneToken, 0, 0]) != nil,
            baseEntry(0x4f5cbd, soundManager + 16, [10]) != nil
        else { throw AssetError.invalid("Sound manager constructor") }
        let sound = heap.lookup(soundManager, words: 14)!
        sound[0] = 0x513b00
        sound[11] = 0
        sound[13] = 0
        heap.lookup(sceneToken, words: 15)![10] = soundManager
        guard soundService(0x4ca280, soundManager, [1]) == 1, fault == 0 else { throw AssetError.invalid("Sound manager initialization") }
        initialized = true
    }
    deinit {
        shutdown()
        palette = nil
        image.deinitialize(count: 1)
        image.deallocate()
        sourceHost.deinitialize(count: 1)
        sourceHost.deallocate()
        // All menu/IFC/resource tokens are scoped to this heap. No original
        // state destructor is invoked for an initializer stopped at a boundary.
    }
    func transferInterfaceConstructorAllocations(to resources: ClawNativeMenuResources) throws {
        guard resources.heap === heap else { throw AssetError.invalid("Menu interface must share its constructor heap") }
        try resources.adoptConstructorAllocations(constructorAllocations)
        constructorAllocations.removeAll()
    }
    // The state-five object is a game allocation: the original state switch
    // deletes it through operator delete. Put it on the same ledger that owns
    // every other game allocation so that delete is honoured.
    func transferStateAllocation(to resources: ClawNativeMenuResources) throws {
        guard resources.heap === heap else { throw AssetError.invalid("Menu state must share its constructor heap") }
        try resources.adoptConstructorAllocations([(menuToken, UInt32(CLAW_STATE_FIVE_BYTES))])
    }
    func shutdown() {
        initialized = false
        applicationErrors?.close()
        if soundManager != 0 {
            // Preserve the initializer's diagnostic while completing actual source cleanup.
            let saved = (fault, boundary, sourceHost.pointee.fault, sourceHost.pointee.faultAddress)
            fault = 0
            sourceHost.pointee.fault = 0
            _ = soundService(0x4ca2e0, soundManager, [])
            soundCleanupFault = fault
            soundCleanupRemaining = soundAllocations.count
            heap.free(soundManager)
            soundManager = 0
            heap.lookup(sceneToken, words: 15)![10] = 0
            soundEntries.removeAll()
            for token in soundAllocations { heap.free(token) }
            soundAllocations.removeAll()
            audio = nil
            heap.lookup(sceneToken, words: 15)![8] = 0
            for block in resourceBlocks { heap.free(block.token) }
            resourceBlocks.removeAll()
            soundResources.removeAll()
            resourceTables.removeAll()
            (fault, boundary, sourceHost.pointee.fault, sourceHost.pointee.faultAddress) = saved
        }
        palette?.shutdown()
        for token in directories.keys { heap.free(token) }
        directories.removeAll()
        directoryTokens.removeAll()
        if let state = heap.lookup(menuToken, words: 9) {
            state[7] = 0
            state[8] = 0
        }
        if let app = heap.lookup(applicationToken, words: 14) { app[13] = 0 }
    }
    var actorHost: ClawSceneActorHost {
        ClawSceneActorHost(
            context: Unmanaged.passUnretained(self).toOpaque(),
            lookup: { u, t, n in
                guard let u else { return nil }
                let owner = Unmanaged<ClawNativeMenuBase>.fromOpaque(u).takeUnretainedValue()
                let span = owner.heap.lookup(t, words: n)
                if span == nil { owner.missingSpan = t }
                return span
            }, allocate: nil, free: nil,
            call: { u, q in
                guard let u else { return 0 }
                let owner = Unmanaged<ClawNativeMenuBase>.fromOpaque(u).takeUnretainedValue()
                guard q.function == 0x4b8910 else { return owner.reject(q.function) }
                return owner.drainWindowInput(
                    receiver: q.receiver, count: q.argumentCount,
                    message: q.arguments.0, maximum: q.arguments.1)
            },
            readClock: { _ in
                UInt32(truncatingIfNeeded: UInt64(ProcessInfo.processInfo.systemUptime * 1000))
            })
    }
    private func reject(_ address: UInt32) -> UInt32 {
        if fault != 0 { return 0 }
        fault = 1
        boundary = address
        sourceHost.pointee.fault = UInt32(CLAW_FAULT_HALT)
        sourceHost.pointee.faultAddress = address
        return 0
    }
    private func baseEntry(_ f: UInt32, _ receiver: UInt32, _ args: [UInt32]) -> UInt32? {
        var globals = ClawSinglePlayerSceneGlobals(), camera = ClawSceneCameraGlobals()
        var c = ClawSinglePlayerSceneContext(), out: UInt32 = 0
        c.host = actorHost
        let done = withUnsafeMutablePointer(to: &globals) { g in
            withUnsafeMutablePointer(to: &camera) { cam in
                c.globals = g
                c.camera = cam
                return args.withUnsafeBufferPointer {
                    claw_single_player_scene_entry(f, receiver, $0.baseAddress, UInt32($0.count), &c, nil, nil, &out)
                }
            }
        }
        return done == 1 && c.fault == 0 ? out : nil
    }
    private func constructorService(_ q: ClawCall) -> UInt32 {
        calls.append(q.function)
        if missingOwner == q.function { return reject(q.function) }
        if q.function == 0x4b90b0 {
            guard let owner = applicationErrors, let result = owner.service(q) else {
                return reject(applicationErrors?.faultAddress ?? q.function)
            }
            return result
        }
        if [UInt32(0x4c9bd0), 0x4d5720, 0x4d4280].contains(q.function) {
            return menuVirtualService(q) ?? reject(q.function)
        }
        let a = withUnsafeBytes(of: q.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(q.argumentCount))) }
        if [UInt32(0x40b5c0), 0x4f5cbd].contains(q.function) {
            guard let result = baseEntry(q.function, q.receiver, a) else { return reject(q.function) }
            return result
        }
        if q.function == 0x4dcc40 {
            var c = ClawInterfaceFileContext(), out: UInt32 = 0
            c.scene = actorHost
            c.stringScratchToken = interfaceScratch
            c.memoryFileToken = interfaceFile
            c.archiveToken = interfaceArchive
            c.maximumOperations = 10000
            let done = a.withUnsafeBufferPointer {
                claw_interface_file_entry(
                    q.function, q.receiver, $0.baseAddress, UInt32($0.count), &c,
                    { c, q, u in
                        guard let c, let q, let u else { return 0 }
                        let owner = Unmanaged<ClawNativeMenuBase>.fromOpaque(u).takeUnretainedValue()
                        if q.pointee.function == 0x4f63ec, q.pointee.argumentCount == 1 {
                            let bytes = q.pointee.arguments.0, token = owner.heap.allocate(bytes: bytes)
                            owner.constructorAllocations.append((token, bytes))
                            return token
                        }
                        if q.pointee.function == 0x4f6428, q.pointee.argumentCount == 1 {
                            owner.heap.free(q.pointee.arguments.0)
                            return 0
                        }
                        c.pointee.fault = 1
                        return owner.reject(q.pointee.function)
                    }, Unmanaged.passUnretained(self).toOpaque(), &out)
            }
            guard done == 1, c.fault == 0 else { return reject(q.function) }
            return out
        }
        // SetRect is a physical Win32 transport, not a game-service substitute.
        if q.function == 0x546d5c, a.count == 5, let rect = heap.lookup(a[0], words: 4) {
            rect[0] = a[1]
            rect[1] = a[2]
            rect[2] = a[3]
            rect[3] = a[4]
            return 1
        }
        return soundService(q.function, q.receiver, a, stack: q.stackPointer)
    }
    // The legacy menu adapter already owns its mapped source stack. Reuse that
    // host rather than installing a second canonical stack over the same heap.
    func menuVirtualService(_ q: ClawCall) -> UInt32? {
        guard initialized, fault == 0, sourceHost.pointee.fault == 0,
            missingOwner != q.function, q.receiver2 == 0, q.x87ArgumentCount == 0
        else { return nil }
        switch q.function {
        case 0x4c9bd0:
            guard q.receiver == menuToken, q.argumentCount == 0 else { return nil }
        case 0x4d5720:
            guard q.receiver == palette?.display?.primaryToken, q.argumentCount == 3 else { return nil }
        case 0x4d4280:
            guard let display = palette?.display,
                [display.backToken, display.spareToken].contains(q.receiver), q.argumentCount == 3
            else { return nil }
        default: return nil
        }
        var call = q, result: UInt32 = 0
        guard claw_canonical_dispatch(&call, sourceHost, &result) == 1 else { return nil }
        return result
    }
    private func resourceAllocation(_ size: UInt32) -> UInt32 {
        let token = heap.allocate(bytes: max(4, (size + 3) & ~3))
        resourceBlocks.append((token, max(4, (size + 3) & ~3)))
        return token
    }
    private func resourceString(_ value: String) -> UInt32 {
        let bytes = Array(value.utf8) + [0], token = resourceAllocation(UInt32(bytes.count))
        bytes.withUnsafeBufferPointer {
            heap.lookupBytes(token, count: UInt32(bytes.count))!.update(from: $0.baseAddress!, count: $0.count)
        }
        return token
    }
    private func resourceTable(_ table: UInt32, _ objects: [UInt32], offset: UInt32) {
        let buckets = resourceAllocation(16), words = heap.lookup(table, words: 2)!
        words[0] = 1
        words[1] = buckets
        heap.lookup(buckets, words: 4)![2] = objects.first.map { $0 + offset + 4 } ?? 0
        for (index, object) in objects.enumerated() {
            let node = heap.lookup(object + offset, words: 6)!
            node[0] = 0
            node[1] = index + 1 < objects.count ? objects[index + 1] + offset + 4 : 0
            node[2] = 0
            node[3] = table
            node[4] = 0
            node[5] = object
        }
    }
    private func materializeSounds(_ url: URL, token: UInt32) throws {
        if resourceTables.contains(token) { return }
        resourceTables.insert(token)
        heap.lookup(token, words: 1)![0] = resourceString(url.lastPathComponent)
        let files = try FileManager.default.contentsOfDirectory(at: url, includingPropertiesForKeys: [.isDirectoryKey]).sorted {
            $0.lastPathComponent < $1.lastPathComponent
        }
        var children: [UInt32] = [], resources: [UInt32] = []
        for file in files {
            if try file.resourceValues(forKeys: [.isDirectoryKey]).isDirectory == true {
                let child = resourceAllocation(76)
                children.append(child)
                try materializeSounds(file, token: child)
            } else if file.pathExtension.uppercased() == "WAV" {
                let data = try Data(contentsOf: file), resource = resourceAllocation(96)
                let archive = resourceAllocation(36), payload = resourceAllocation(UInt32(data.count)), type = resourceAllocation(4)
                data.copyBytes(to: heap.lookupBytes(payload, count: UInt32(data.count))!, count: data.count)
                heap.lookup(archive, words: 9)![8] = payload
                heap.lookup(type, words: 1)![0] = 0x574156
                let words = heap.lookup(resource, words: 24)!
                words[0] = resourceString(file.deletingPathExtension().lastPathComponent)
                words[2] = type
                words[5] = UInt32(data.count)
                words[9] = archive
                resources.append(resource)
                soundResources[resource] = file.path
            }
        }
        resourceTable(token + 60, children, offset: 36)
        var groups: [UInt32] = []
        if !resources.isEmpty {
            let group = resourceAllocation(36)
            groups.append(group)
            resourceTable(group + 28, resources, offset: 72)
        }
        resourceTable(token + 68, groups, offset: 4)
    }
    private func soundService(_ f: UInt32, _ receiver: UInt32, _ a: [UInt32], stack: UInt32 = 0) -> UInt32 {
        if missingOwner == f { return reject(f) }
        if let resources = sharedMenuResources,
            [UInt32(0x4b68e0), 0x4b6900, 0x4b6920, 0x4b6940, 0x4b6960, 0x4b6980, 0x4b61b0].contains(f)
        {
            let result = resources.invoke(f, receiver, a)
            return resources.fault == 0 ? result : reject(resources.faultAddress)
        }
        let semantic: Set<UInt32> = [
            0x4ca440, 0x4ca3b0, 0x4b68e0, 0x4b6900, 0x4b6920, 0x4b6940, 0x4b6960, 0x4b6980, 0x4b61b0, 0x4f6286, 0x4f62a8, 0x4c8850,
            0x4c88b0, 0x4ca670
        ]
        if semantic.contains(f) { soundEvents.append(f) }
        var out: UInt32 = 0
        if [UInt32(0x4ca440), 0x4ca3b0, 0x4ca670, 0x4ca690].contains(f) {
            let saved = sourceHost.pointee.entryStackPointer
            sourceHost.pointee.entryStackPointer = stack == 0 ? soundStack : stack
            defer { sourceHost.pointee.entryStackPointer = saved }
            let done = a.withUnsafeBufferPointer { args in
                if f == 0x4ca440 {
                    return claw_menu_sound_directory_entry(f, receiver, args.baseAddress, UInt32(args.count), sourceHost, &out)
                }
                if f == 0x4ca3b0 {
                    return claw_v13_native_overlay_entry(f, receiver, args.baseAddress, UInt32(args.count), sourceHost, &out)
                }
                return claw_menu_sound_entry_entry(f, receiver, args.baseAddress, UInt32(args.count), sourceHost, &out)
            }
            guard done == 1, sourceHost.pointee.fault == 0 else {
                if fault == 0 { return reject(sourceHost.pointee.faultAddress == 0 ? f : sourceHost.pointee.faultAddress) }
                return 0
            }
            if f == 0x4ca3b0, out != 0, let key = string(a[0]) { soundEntries[key] = out }
            return out
        }
        if f == 0x4ca280 {
            var c = ClawSceneStartupCompositionContext()
            c.scene = actorHost
            let done = a.withUnsafeBufferPointer {
                claw_scene_startup_composition_entry(f, receiver, $0.baseAddress, UInt32($0.count), &c, nil, nil, &out)
            }
            return done == 1 && c.fault == 0 ? out : reject(f)
        }
        if (0x4b68e0...0x4b6980).contains(f) {
            var c = ClawResourceNamespaceContext()
            c.scene = actorHost
            let done = a.withUnsafeBufferPointer {
                claw_resource_namespace_entry(f, receiver, $0.baseAddress, UInt32($0.count), &c, nil, nil, &out)
            }
            return done == 1 && c.fault == 0 ? out : reject(f)
        }
        if f == 0x4b61b0 {
            var c = ClawResourceDataContext()
            c.scene = actorHost
            let done = claw_resource_data_entry(f, receiver, nil, 0, &c, nil, nil, &out)
            return done == 1 && c.fault == 0 ? out : reject(f)
        }
        if f == 0x4c8850 || f == 0x4c88b0 {
            guard let audio else { return reject(f) }
            var audioFault: UInt32 = 0
            if f == 0x4c8850 {
                if let resources = sharedMenuResources {
                    guard resources.invoke(0x4b61c0, a[0]) != 0, resources.fault == 0 else { return reject(f) }
                    out = audio.loadSceneSound(receiver, resource: a[0], fault: &audioFault)
                    _ = resources.invoke(0x4b6230, a[0])
                    if resources.fault != 0 { return reject(resources.faultAddress) }
                } else {
                    out = audio.loadSceneSound(receiver, resource: a[0], fault: &audioFault)
                }
            } else {
                audio.unloadSceneSound(receiver, fault: &audioFault)
            }
            return audioFault == 0 ? out : reject(f)
        }
        if f == 0x4f6286 || f == 0x4f62a8 || f == 0x4f5db6 {
            var c = ClawImageControllerLoadingContext()
            c.scene = actorHost
            let done = a.withUnsafeBufferPointer {
                claw_image_controller_loading_entry(
                    f, receiver, $0.baseAddress, UInt32($0.count), &c,
                    { c, q, u in
                        guard let c, let q, let u else { return 0 }
                        let owner = Unmanaged<ClawNativeMenuBase>.fromOpaque(u).takeUnretainedValue(), e = q.pointee
                        let args = withUnsafeBytes(of: e.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(e.argumentCount))) }
                        let result = owner.soundService(e.function, e.receiver, args)
                        if owner.fault != 0 { c.pointee.fault = 1 }
                        return result
                    }, Unmanaged.passUnretained(self).toOpaque(), &out)
            }
            return done == 1 && c.fault == 0 ? out : reject(f)
        }
        if f == 0x4ca2e0 || f == 0x4ca300 || f == 0x4f61a1 {
            var c = ClawSceneLifecycleContext()
            c.scene = actorHost
            let done = claw_scene_lifecycle_entry(
                f, receiver, nil, 0, &c,
                { c, q, u in
                    guard let c, let q, let u else { return 0 }
                    let owner = Unmanaged<ClawNativeMenuBase>.fromOpaque(u).takeUnretainedValue(), e = q.pointee
                    let args = withUnsafeBytes(of: e.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(e.argumentCount))) }
                    let result = owner.soundService(e.function, e.receiver, args)
                    if owner.fault != 0 { c.pointee.fault = 1 }
                    return result
                }, Unmanaged.passUnretained(self).toOpaque(), &out)
            if done != 1 || c.fault != 0 {
                if let path = ProcessInfo.processInfo.environment["CLAW_REAL_SPEED_LOG"] {
                    let report:[String:Any] = ["function":String(f,radix:16),"fault":c.fault,"missing_span":String(missingSpan,radix:16),"boundary":String(boundary,radix:16)]
                    try? JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]).write(to:URL(fileURLWithPath:path).appendingPathComponent("sound-lifecycle-fault.json"))
                }
                return reject(f)
            }
            return out
        }
        // Native CRT/MFC storage transports preserve the published dictionary layout.
        if f == 0x4f63ec, a.count == 1 {
            let token = heap.allocate(bytes: a[0])
            soundAllocations.insert(token)
            return token
        }
        if f == 0x4f6428, a.count == 1 {
            soundAllocations.remove(a[0])
            heap.free(a[0])
            return 0
        }
        if f == 0x4f5aa8, a.count == 3, let head = heap.lookup(a[0], words: 1) {
            let block = soundService(0x4f63ec, 0, [4 + a[1] * a[2]])
            heap.lookup(block, words: 1)![0] = head[0]
            head[0] = block
            return block
        }
        if f == 0x4f5ac8 {
            var block = receiver
            while block != 0 {
                let next = heap.lookup(block, words: 1)![0]
                _ = soundService(0x4f6428, 0, [block])
                block = next
            }
            return 0
        }
        if f == 0x4f6433 { return 0x52e1cc }
        if f == 0x4a4a20, a.count == 3, let p = heap.lookupBytes(a[0], count: a[2]) {
            p.update(repeating: UInt8(truncatingIfNeeded: a[1]), count: Int(a[2]))
            return a[0]
        }
        if f == 0x4a4a80, a.count == 3, let p = heap.lookupBytes(a[0], count: a[2]), let q = heap.lookupBytes(a[1], count: a[2]) {
            memmove(p, q, Int(a[2]))
            return a[0]
        }
        if f == 0x4a3810, a.count == 2, let left = string(a[0]), let right = string(a[1]) {
            return left == right ? 0 : left < right ? .max : 1
        }
        if f == 0x4f6584,a.isEmpty,let cell = heap.lookup(receiver,words:1) {
            let text = cell.pointee
            if text != 0 && text != 0x52e1c4 {
                guard text >= 12,let header = heap.lookup(text-12,words:3),soundAllocations.contains(text-12) else {return reject(f)}
                if Int32(bitPattern:header[0]) <= 1 {_ = soundService(0x4f6428,0,[text-12])}
                else {header[0] -= 1}
            }
            cell.pointee = 0x52e1c4
            return 0
        }
        if f == 0x4f66cc, a.count == 1, let value = string(a[0]), let cell = heap.lookup(receiver, words: 1), cell[0] == 0x52e1c4 {
            let bytes = Array(value.utf8) + [0], block = soundService(0x4f63ec, 0, [UInt32(bytes.count) + 12])
            let header = heap.lookup(block, words: 3)!
            header[0] = 1
            header[1] = UInt32(bytes.count - 1)
            header[2] = header[1]
            bytes.withUnsafeBufferPointer {
                heap.lookupBytes(block + 12, count: UInt32(bytes.count))!.update(from: $0.baseAddress!, count: $0.count)
            }
            cell[0] = block + 12
            return receiver
        }
        if f == 0x4a3920, a.count == 5, string(a[1]) == "%s%s%s",
            let p = string(a[2]), let separator = string(a[3]), let name = string(a[4])
        {
            let bytes = Array((p + separator + name).utf8) + [0]
            guard let destination = heap.lookupBytes(a[0], count: UInt32(bytes.count)) else { return reject(f) }
            bytes.withUnsafeBufferPointer { destination.update(from: $0.baseAddress!, count: $0.count) }
            return UInt32(bytes.count - 1)
        }
        return reject(f)
    }
    // Run the actual initializer through the application size guard. Stop at the
    // next unowned service; false never implies menu readiness.
    @discardableResult func initializeBase(level: UInt32, parameter: UInt32 = 0, composeBase: Bool = true) -> Bool {
        fault = 0
        boundary = 0
        applicationResult = nil
        sourceHost.pointee.fault = 0
        sourceHost.pointee.faultAddress = 0
        var c = ClawStateFiveContext(), base = ClawSinglePlayerSceneContext(), g = ClawSinglePlayerSceneGlobals(), out: UInt32 = 0
        c.scene = actorHost
        c.maximumOperations = 10000
        c.composeBase = composeBase ? 1 : 0
        let args = [applicationToken, level, parameter]
        let done = withUnsafeMutablePointer(to: &g) { gp in
            withUnsafeMutablePointer(to: &base) { bp in
                bp.pointee.globals = gp
                c.base = bp
                return args.withUnsafeBufferPointer {
                    claw_state_five_entry(
                        0x45ace0, menuToken, $0.baseAddress, 3, &c,
                        { c, q, u in
                            guard let c, let q, let u else { return 0 }
                            let owner = Unmanaged<ClawNativeMenuBase>.fromOpaque(u).takeUnretainedValue()
                            let result = owner.initializerService(q.pointee)
                            if owner.fault != 0 { c.pointee.fault = owner.fault }
                            return result
                        }, Unmanaged.passUnretained(self).toOpaque(), &out)
                }
            }
        }
        fault = max(fault, c.fault)
        return done == 1 && fault == 0 && out != 0
    }
    private func string(_ token: UInt32) -> String? {
        var bytes: [UInt8] = []
        for i: UInt32 in 0..<1024 {
            guard let p = heap.lookupBytes(token + i, count: 1) else { return nil }
            if p.pointee == 0 { return String(bytes: bytes, encoding: .utf8) }
            bytes.append(p.pointee)
        }
        return nil
    }
    func sharedInitializerService(_ function: UInt32, _ receiver: UInt32, _ arguments: [UInt32]) -> UInt32? {
        // The shared menu dispatches application policy on its own mapped
        // stack, so resize descendants keep the same resource/physical owners.
        if function == 0x42a000, sharedMenuResources != nil { return nil }
        if function == 0x4b90b0, let resources = sharedMenuResources {
            var q = ClawCall()
            q.function = function
            q.receiver = receiver
            q.argumentCount = UInt32(arguments.count)
            guard arguments.count == 2 else { return reject(function) }
            q.arguments.0 = arguments[0]
            q.arguments.1 = arguments[1]
            guard let result = applicationErrors?.service(q) else { return resources.fail(applicationErrors?.faultAddress ?? function) }
            return result
        }
        guard [Self.ready, 0x42a000, 0x4ca440, 0x4ca300, 0x4b4b40, 0x4b8910].contains(function), arguments.count <= 3 else { return nil }
        if function == 0x4b4b40 {
            guard let audio, receiver == audio.managerIdentity, arguments.isEmpty else { return reject(function) }
            audio.stopAll()
            return audio.lifecycleFault == 0 ? 0 : reject(function)
        }
        let previous = sourceHost.pointee.entryStackPointer
        sourceHost.pointee.entryStackPointer = sharedMenuResources?.currentFrame ?? soundStack
        defer { sourceHost.pointee.entryStackPointer = previous }
        if function == 0x4ca300 {
            guard receiver == soundManager, arguments.isEmpty else { return reject(function) }
            return soundService(function, receiver, arguments, stack: sourceHost.pointee.entryStackPointer)
        }
        if function == 0x4ca440 {
            guard receiver == soundManager, arguments.count == 3 else { return reject(function) }
            soundLoadCount = soundService(function, receiver, arguments, stack: sourceHost.pointee.entryStackPointer)
            return soundLoadCount
        }
        var q = ClawStateFiveCall()
        q.function = function
        q.receiver = receiver
        q.argumentCount = UInt32(arguments.count)
        withUnsafeMutableBytes(of: &q.arguments) { dst in arguments.withUnsafeBytes { dst.copyBytes(from: $0) } }
        return initializerService(q)
    }
    func sharedSoundStorageService(_ q: ClawCall) -> UInt32? {
        guard q.receiver == soundManager + 16, [UInt32(0x4f6286), 0x4f62a8, 0x4f5db6].contains(q.function), q.argumentCount <= 2 else { return nil }
        let args = withUnsafeBytes(of: q.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(q.argumentCount))) }
        return soundService(q.function, q.receiver, args, stack: q.stackPointer)
    }
    func loadPackageSound(name:UInt32,resource:UInt32)->UInt32 {
        soundService(0x4ca3b0,soundManager,[name,resource],stack:sharedMenuResources?.currentFrame ?? soundStack)
    }
    func unloadPackageSound(name:String,sound:UInt32,original:UInt32) {
        _ = soundService(0x4ca670,sound,[1],stack:sharedMenuResources?.currentFrame ?? soundStack)
        if original == 0 {soundEntries.removeValue(forKey:name)} else {soundEntries[name] = original}
    }
    func initializerService(_ q: ClawStateFiveCall) -> UInt32 {
        calls.append(q.function)
        if missingOwner == q.function { return reject(q.function) }
        if q.function == 0x4b8910 {
            return drainWindowInput(
                receiver: q.receiver, count: q.argumentCount,
                message: q.arguments.0, maximum: q.arguments.1)
        }
        if q.function == 0x4ca440, q.argumentCount == 3 {
            guard q.receiver == soundManager, soundManager != 0 else { return reject(q.function) }
            soundLoadCount = soundService(q.function, q.receiver, [q.arguments.0, q.arguments.1, q.arguments.2])
            return soundLoadCount
        }
        if q.function == 0x42a000 {
            guard q.receiver == applicationToken, q.argumentCount == 1 else { return reject(q.function) }
            var argument = q.arguments.0, out: UInt32 = 0
            let done = claw_menu_application_entry(q.function, q.receiver, &argument, 1, sourceHost, &out)
            guard done == 1, sourceHost.pointee.fault == 0 else {
                // Preserve a deeper missing owner, such as the resize service.
                if fault == 0 { return reject(sourceHost.pointee.faultAddress) }
                return 0
            }
            applicationResult = out
            return out
        }
        if q.function == Self.ready, q.receiver == applicationToken, q.argumentCount == 0 {
            guard initialized, let display = palette?.display else { return 0 }
            return display.fault == 0
                && [display.primaryToken, display.backToken, display.spareToken].allSatisfy { $0 != 0 && heap.lookup($0, words: 12) != nil }
                ? 1 : 0
        }
        if q.function == 0x4a3920, q.argumentCount == 3, q.bufferCount == 1,
            [UInt32(0x52c69c), 0x52a004].contains(q.arguments.1),
            let format = string(q.arguments.1), let buffer = q.buffers.0
        {
            // Both reviewed source formats contain exactly one integer argument.
            let parts = format.components(separatedBy: "%i")
            guard parts.count == 2, parts.allSatisfy({ !$0.contains("%") }) else { return reject(q.function) }
            let bytes = Array((parts[0] + String(Int32(bitPattern: q.arguments.2)) + parts[1]).utf8) + [0]
            guard bytes.count <= q.bufferBytes.0 else { return reject(q.function) }
            bytes.withUnsafeBytes { buffer.copyMemory(from: $0.baseAddress!, byteCount: $0.count) }
            return UInt32(bytes.count - 1)
        }
        if [UInt32(0x4b7f20), 0x4b68c0].contains(q.function), q.argumentCount == 1,
            let directory = directories[q.receiver]
        {
            let components: [String]
            if q.function == 0x4b7f20, q.receiver == resourceRootToken,
                q.localMask == 1, q.bufferCount == 1, let buffer = q.buffers.0
            {
                let data = UnsafeRawBufferPointer(start: buffer, count: Int(q.bufferBytes.0))
                guard let end = data.firstIndex(of: 0), let name = String(bytes: data.prefix(end), encoding: .utf8),
                    name.hasPrefix("LEVEL"), !name.dropFirst(5).isEmpty,
                    name.dropFirst(5).allSatisfy({ $0.isASCII && $0.isNumber })
                else { return reject(q.function) }
                components = [name]
            } else if q.function == 0x4b7f20, q.receiver == resourceRootToken,
                q.localMask == 0, q.bufferCount == 0, q.arguments.0 == 0x528b08,
                string(q.arguments.0) == "STATES_MENU"
            {
                // The retail resource path separator is '_'. These are the
                // elected initializer requests, not a general archive API.
                components = ["STATES", "MENU"]
            } else if q.function == 0x4b68c0, q.localMask == 0, q.bufferCount == 0,
                q.receiver == heap.lookup(menuToken, words: 9)?[8],
                q.arguments.0 == 0x52372c, string(q.arguments.0) == "SOUNDS"
            {
                components = ["SOUNDS"]
            } else {
                return reject(q.function)
            }
            let url = components.reduce(directory) { $0.appendingPathComponent($1, isDirectory: true) }
            var isDirectory: ObjCBool = false
            guard FileManager.default.fileExists(atPath: url.path, isDirectory: &isDirectory), isDirectory.boolValue else { return 0 }
            if let token = directoryTokens[url.path] { return token }
            let token = heap.allocate(bytes: 76)
            directories[token] = url
            directoryTokens[url.path] = token
            if q.function == 0x4b68c0 {
                do { try materializeSounds(url, token: token) } catch { return reject(q.function) }
            }
            return token
        }
        return reject(q.function)
    }

    private func drainWindowInput(receiver: UInt32, count: UInt32, message: UInt32, maximum: UInt32) -> UInt32 {
        guard fault == 0, missingOwner != 0x4b8910, count == 2,
            receiver == windowReceiver, windowReceiver != 0, let windowInput
        else { return reject(0x4b8910) }
        do {
            try windowInput.queue.drain(message: message, maximum: maximum) {
                guard let words = self.heap.lookup(receiver, words: 2) else {
                    throw ClawNativeWindowInputQueue.Failure.missingWindow
                }
                return words[1]
            }
        } catch { return reject(0x4b8910) }
        return 0  // Reviewed callers ignore physical EAX.
    }
}

// Remaining native scene service participant. This is deliberately not a scene
// restore API: the elected adapter/canonical graph must join the same heap plan
// before any candidate may be published or advanced as a restored scene.
extension ClawNativeScene {
    struct RemainingServicesSavedState: Codable, Equatable {
        let loot: ClawNativeLoot.SavedState, effects: ClawNativeEffects.SavedState
        let breakables: ClawNativeBreakables.SavedState, projectiles: ClawNativeProjectiles.SavedState
        let flares: ClawNativeFlare.SavedState, special: ClawNativeSpecialPowerups.SavedState
        let save: ClawNativeSave.SavedState, status: ClawNativeStatusMessages.SavedState
        let palettes: ClawNativePaletteResources.SavedState, light: ClawNativeLightPalette.SavedState
    }
    func savedRemainingServicesState() throws -> RemainingServicesSavedState {
        guard snapshotFrameDepth == 0, objectConnections?.host.snapshotQuiescent == true else { throw ClawSnapshotError.activeFrame }
        guard let loot, let effects, let breakables, let projectiles, let flares, let specialPowerups,
            let saves, let statusMessages, let paletteResources, let palettes
        else { throw ClawSnapshotError.incompleteOwners }
        return try .init(
            loot: loot.savedState(), effects: effects.savedState(), breakables: breakables.savedState(),
            projectiles: projectiles.savedState(), flares: flares.savedState(), special: specialPowerups.savedState(),
            save: saves.savedState(), status: statusMessages.savedState(), palettes: paletteResources.savedState(),
            light: palettes.savedState())
    }
    func prepareRemainingServicesRestore(_ saved: RemainingServicesSavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws ->
        Void
    {
        guard snapshotFrameDepth == 0, objectConnections?.host.snapshotQuiescent == true else { throw ClawSnapshotError.activeFrame }
        guard let loot, let effects, let breakables, let projectiles, let flares, let specialPowerups,
            let saves, let statusMessages, let paletteResources, let palettes
        else { throw ClawSnapshotError.incompleteOwners }
        try heap.validateRestore(plan)
        let installLoot = try loot.prepareRestore(saved.loot, heap: plan)
        let installEffects = try effects.prepareRestore(saved.effects, heap: plan)
        let installBreakables = try breakables.prepareRestore(saved.breakables, heap: plan)
        return { [self] in
            guard snapshotFrameDepth == 0, objectConnections?.host.snapshotQuiescent == true else { throw ClawSnapshotError.activeFrame }
            try heap.validateInstalledRestore(plan)
            try installLoot()
            try installEffects()
            try installBreakables()
            try projectiles.restoreState(saved.projectiles)
            try flares.restoreState(saved.flares)
            try specialPowerups.restoreState(saved.special)
            try saves.restoreState(saved.save)
            try statusMessages.restoreState(saved.status)
            try paletteResources.restoreState(saved.palettes)
            try palettes.restoreState(saved.light)
        }
    }
}
