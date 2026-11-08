import Foundation

// Native service glue for verified bodies. The owning scene elects callbacks.
class ClawHumanoidActorServices {
    let token: UInt32, resources: ClawActorResources
    weak var scene: ClawNativeScene?
    let state = UnsafeMutablePointer<ClawGenericEnemy>.allocate(capacity: 1)
    let generic: UnsafeMutablePointer<ClawGenericEnemyContext>
    let states: ClawEnemyStateView
    private(set) var failure: String?
    private(set) var unresolved: Set<UInt32> = []
    enum NativeOwnerBinding: String, Codable { case loot, breakable }
    private(set) var nativeOwnerBinding: NativeOwnerBinding?
    var externalService: ((ClawGenericEnemyCall) -> UInt64?)? { didSet { sceneServiceBound = false; nativeOwnerBinding = nil } }
    func bindNativeOwner(_ kind: NativeOwnerBinding, service: ((ClawGenericEnemyCall) -> UInt64?)? = nil,
                         clock: (() -> (time: UInt32, delta: UInt32))? = nil) {
        externalService = service; frameClock = clock; nativeOwnerBinding = kind
    }
    private(set) var sceneServiceBound = false
    func bindSceneService(_ service: @escaping (ClawGenericEnemyCall) -> UInt64?) {
        externalService = service; sceneServiceBound = true
    }
    // Optional injected frame service for direct component execution. The scene
    // clock is used in normal scheduling; no timer or fixed-step loop is created.
    var frameClock: (() -> (time: UInt32, delta: UInt32))? { didSet { nativeOwnerBinding = nil } }
    let common: UnsafeMutablePointer<ClawGenericEnemyStatesContext>
    private let sounds = UnsafeMutablePointer<ClawGenericEnemyStateResource>.allocate(capacity: 2048)
    private var soundCount = 0
    private var actorIdentity: ClawTokenHeap.AllocationIdentity?
    init(snapshot: ClawInteractionActor, scene: ClawNativeScene, resources: ClawActorResources,
         generic: UnsafeMutablePointer<ClawGenericEnemyContext>, common: UnsafeMutablePointer<ClawGenericEnemyStatesContext>, states: ClawEnemyStateView) {
        if claw_native_v13_enabled() != 0 { claw_generic_enemy_states_use_v13() }
        self.token = snapshot.token; self.scene = scene; self.resources = resources
        actorIdentity = scene.heap.containingAllocationIdentity(at: snapshot.token, count: 4)
        self.generic = generic; self.common = common; self.states = states
        state.initialize(to: ClawGenericEnemy()); sounds.initialize(repeating: ClawGenericEnemyStateResource(), count: 2048)
        common.pointee.resources = UnsafePointer(sounds); accept(snapshot)
        generic.pointee.actorToken = token; generic.pointee.primaryToken = snapshot.actor.27
        generic.pointee.enemyToken = snapshot.primary.6; generic.pointee.sceneToken = snapshot.actor.3
        generic.pointee.playerToken = 0x10002000; generic.pointee.tileManagerToken = 0x60003000
        generic.pointee.soundRegistryToken = 0x63000020; generic.pointee.emptyStringToken = states.entries[0].nameToken
        generic.pointee.states = UnsafePointer(states.entries); generic.pointee.stateCount = states.count
    }
    deinit { state.deinitialize(count: 1); state.deallocate(); sounds.deinitialize(count: 2048); sounds.deallocate() }
    func registerAudioResource(_ sound:ClawAudioSound) {
        guard !(0..<soundCount).contains(where:{sounds[$0].token == sound.resourceToken}) else { return }
        guard soundCount < 2048 else { fail("Humanoid sound views exhausted");return }
        sounds[soundCount] = ClawGenericEnemyStateResource(token:sound.resourceToken,controllerToken:sound.voicePoolToken)
        soundCount += 1;common.pointee.resourceCount = soundCount
    }
    func fail(_ text: String) { if failure == nil { failure = text } }
    func unsupported(_ event: ClawGenericEnemyCall) -> UInt64 {
        if let service = externalService {
            flush()
            if let value = service(event) {
                if let snapshot = scene?.snapshotActor(token) { accept(snapshot) };reloadPrivate();return value
            }
        }
        unresolved.insert(event.function); return 0
    }
    func accept(_ value: ClawInteractionActor) {
        state.pointee.actor = value.actor; state.pointee.primary = value.primary
        state.pointee.secondary = value.secondary; state.pointee.contact = value.contact
    }
    func snapshot() -> ClawInteractionActor {
        var value = ClawInteractionActor(); value.token = token; value.actor = state.pointee.actor
        value.primary = state.pointee.primary; value.secondary = state.pointee.secondary; value.contact = state.pointee.contact; return value
    }
    func refresh() {
        guard let scene else { return }
        if let value = scene.snapshotActor(token) { accept(value) }
        generic.pointee.enemyToken = state.pointee.primary.6
        let clock = frameClock?() ?? (time:scene.gameTime,delta:scene.animationDelta)
        generic.pointee.tick = clock.time; generic.pointee.animationDelta = clock.delta
        generic.pointee.playerActor = scene.player.runtime.actor; generic.pointee.levelWord = scene.player.runtime.powerup
        generic.pointee.secondaryToken = state.pointee.actor.28; generic.pointee.contactToken = state.pointee.actor.30
        generic.pointee.platformActor = scene.snapshotActor(state.pointee.actor.32)?.actor ?? ClawInteractionActor().actor
        common.pointee.playerPrivate = scene.player.runtime.privateWords
        common.pointee.audioEnabled = scene.player.audio == nil ? 0 : 1; common.pointee.audioPosition = scene.player.audio?.routing.masterVolume ?? 0
        common.pointee.attackerToken = state.pointee.actor.29
        common.pointee.attackerActor = scene.snapshotActor(state.pointee.actor.29)?.actor ?? ClawInteractionActor().actor
    }
    func flush() {
        guard let scene, ownsActor else { return }; scene.write(snapshot())
        if common.pointee.attackerToken != 0, var actor = scene.snapshotActor(common.pointee.attackerToken) {
            actor.actor = common.pointee.attackerActor; scene.write(actor)
        }
    }
    // Internal dispatch must not refresh over a suspended original caller.
    func entry(_ function: UInt32, argument: UInt32) -> UInt32? { nil }

    var ownsActor: Bool {
        guard let scene, let actorIdentity else { return false }
        return scene.heap.containingAllocationIdentity(at: token, count: 4) === actorIdentity
    }
    func snapshotOwnerKey() throws -> ClawSnapshotOwnerKey {
        guard let actorIdentity else { throw ClawSnapshotError.invalidState }
        return .init(token: token, allocation: actorIdentity.snapshotID)
    }
    struct ServiceSavedState: Codable, Equatable {
        let token: UInt32, actor: ClawSnapshotWitness
        let state: ClawSnapshotValue<ClawGenericEnemy>
        let generic: [String: Data], common: [String: Data]
        let sounds: [ClawSnapshotValue<ClawGenericEnemyStateResource>]
        let states: ClawEnemyStateView.SavedState
        let sceneServiceBound: Bool
        let nativeOwnerBinding: NativeOwnerBinding?
        let failure: String?, unresolved: Set<UInt32>
    }
    func savedServiceState() throws -> ServiceSavedState {
        guard let scene, let actorIdentity, generic.pointee.bitWords == nil, generic.pointee.bitWordCount == 0,
              generic.pointee.states == UnsafePointer(states.entries), generic.pointee.stateCount == states.count,
              common.pointee.resources == UnsafePointer(sounds), common.pointee.resourceCount == soundCount,
              (externalService == nil || sceneServiceBound || nativeOwnerBinding != nil),
              (frameClock == nil || nativeOwnerBinding == .loot) else { throw ClawSnapshotError.invalidState }
        return ServiceSavedState(token: token,
            actor: ClawSnapshotWitness(heap: scene.heap, token: token, count: 4, identity: actorIdentity, interior: true),
            state: ClawSnapshotValue(state.pointee), generic: ClawEnemySnapshotFields.generic.capture(generic.pointee),
            common: ClawEnemySnapshotFields.common.capture(common.pointee),
            sounds: (0..<soundCount).map { ClawSnapshotValue(sounds[$0]) }, states: states.savedState(), sceneServiceBound: sceneServiceBound, nativeOwnerBinding: nativeOwnerBinding,
            failure: failure, unresolved: unresolved)
    }
    func restoreServiceState(_ saved: ServiceSavedState, heap plan: ClawTokenHeap.RestorePlan) throws {
        guard saved.nativeOwnerBinding == nativeOwnerBinding, saved.token == token, saved.actor.reference.token == token, saved.actor.reference.count == 4,
              saved.actor.reference.interior, saved.sounds.count <= 2048 else { throw ClawSnapshotError.invalidState }
        let identity = try saved.actor.resolve(in: plan)
        let genericValue = try ClawEnemySnapshotFields.generic.restoring(saved.generic, into: generic.pointee)
        let commonValue = try ClawEnemySnapshotFields.common.restoring(saved.common, into: common.pointee)
        try states.restoreState(saved.states)
        actorIdentity = identity; state.pointee = saved.state.value
        generic.pointee = genericValue; common.pointee = commonValue
        soundCount = saved.sounds.count; common.pointee.resourceCount = soundCount
        for (index, value) in saved.sounds.enumerated() { sounds[index] = value.value }
        failure = saved.failure; unresolved = saved.unresolved
    }
    static func savedActor(_ saved: ServiceSavedState) -> ClawInteractionActor {
        var actor = ClawInteractionActor(); actor.token = saved.token
        actor.actor = saved.state.value.actor; actor.primary = saved.state.value.primary
        actor.secondary = saved.state.value.secondary; actor.contact = saved.state.value.contact
        return actor
    }
    func dependency(_ event: ClawGenericEnemyCall) -> UInt64 {
        guard let scene else { fail("Missing actor scene"); return 0 }
        let a = event.arguments.0, b = event.arguments.1, c = event.arguments.2, d = event.arguments.3
        if event.receiver == generic.pointee.enemyToken, let value = entry(event.function, argument: a) { return UInt64(value) }
        if [UInt32(0x4c7fa0),0x4c8060,0x4c7970,0x4c7900,0x420a10].contains(event.function), event.receiver != token { return unsupported(event) }
        if [UInt32(0x4c8220),0x4c8260,0x4c82a0].contains(event.function), event.receiver != token &+ 0x188 { return unsupported(event) }
        if [UInt32(0x4cbb60),0x4cd800].contains(event.function), a != token { return unsupported(event) }
        do {
            switch event.function {
            case 0x4f63ec:
                let value = scene.heap.allocate(bytes: a)
                if a == 0x470 || a == 0x480 || a == 0x150 { generic.pointee.enemyToken = value }; return UInt64(value)
            case 0x4f6428: scene.heap.free(a); return 0
            case 0x4dba00: return UInt64(event.name.flatMap { states.ids[String(cString: $0)] } ?? 0)
            case 0x4a3050: return UInt64(scene.nextRandom())
            case 0x4c7fa0, 0x4c8060:
                guard let name = event.name else { fail("Missing logic binding name"); return 0 }
                var value = ClawActorResourceBindings(); value.actor = state.pointee.actor
                value.secondary = event.function == 0x4c7fa0 ? state.pointee.secondary : state.pointee.contact
                var context = ClawActorBindingContext(); context.logicRegistryToken = 0x63000030
                let result = event.function == 0x4c7fa0
                    ? claw_actor_bind_secondary_logic_name(&value, &context, name, humanoidBindingDependency, Unmanaged.passUnretained(self).toOpaque())
                    : claw_actor_bind_contact_logic_name(&value, &context, name, humanoidBindingDependency, Unmanaged.passUnretained(self).toOpaque())
                state.pointee.actor = value.actor
                if event.function == 0x4c7fa0 { state.pointee.secondary = value.secondary } else { state.pointee.contact = value.secondary }; return UInt64(result)
            case 0x4c7970, 0x4c7900:
                guard let name = event.name, let images = try resources.images(name: String(cString: name)) else { return 0 }
                var value = ClawActorResourceBindings(); value.actor = state.pointee.actor
                var context = ClawActorBindingContext(); context.image = images.binding(); context.imageRegistryToken = 0x63000040
                let result = event.function == 0x4c7970
                    ? claw_actor_bind_default_image(&value, &context, name, humanoidBindingDependency, Unmanaged.passUnretained(self).toOpaque())
                    : claw_actor_bind_indexed_image(&value, &context, name, Int32(bitPattern: a), humanoidBindingDependency, Unmanaged.passUnretained(self).toOpaque())
                state.pointee.actor = value.actor; return UInt64(result)
            case 0x4f6286:
                guard let name = event.name else { return 0 }; let key = String(cString: name)
                if event.receiver == 0x63000010 { return UInt64(try resources.sequence(name: key)?.token ?? 0) }
                if key == "GAME_BULLETS" || key == "LEVEL_MUSKETBALL" { return UInt64(try resources.images(name: key)?.token ?? 0) }
                let sound = scene.player.audio?.resolve(name: key)
                if let sound, !(0..<soundCount).contains(where: { sounds[$0].token == sound.resourceToken }) {
                    guard soundCount < 2048 else { fail("Humanoid sound views exhausted"); return 0 }
                    sounds[soundCount] = ClawGenericEnemyStateResource(token: sound.resourceToken, controllerToken: sound.voicePoolToken); soundCount += 1; common.pointee.resourceCount = soundCount
                }; return UInt64(sound?.resourceToken ?? 0)
            case 0x4b45f0: return UInt64(scene.player.audio?.playVoicePool(event.receiver, request: ClawAudioRequest(volume: a, pan: b, pitchPercent: c, looping: d)) ?? 0)
            case 0x4208e0: return UInt64(scene.player.audio?.play(resource: event.receiver, volume: a) ?? 0)
            case 0x4c8220, 0x4c8260, 0x420a10, 0x4c82a0:
                flush(); let result = scene.actorAnimation(function: event.function, receiver: event.receiver, argument0: a, argument1: b)
                if let updated = scene.snapshotActor(token) { accept(updated) }; return UInt64(result)
            case 0x4cbb60:
                var actor = ClawCollisionActor(snapshot: snapshot())
                let result = scene.player.collision.move(actor: &actor, x: b, y: c, options: d, otherActors: scene.collisionActors(excluding: token))
                applyCollision(actor); return UInt64(result)
            case 0x4cd800:
                var actor = ClawCollisionActor(snapshot: snapshot()); let result = scene.player.collision.placeOnGround(actor: &actor)
                applyCollision(actor); return UInt64(result)
            case 0x4207f0: return UInt64(scene.player.collision.footAttribute(x: a, y: b, bottom: 0, xOffset: 0))
            case 0x4cda10:
                let value = scene.player.collision.horizontalClear(x: a, y: b, targetX: c, step: d)
                if value.fault != 0 { fail("Humanoid horizontal query fault") }; return UInt64(value.result)
            case 0x4dbcd0, 0x4f6584, 0x48cf50:
                flush(); var call = ClawSceneActorCall(); call.function = event.function; call.receiver = event.receiver
                call.arguments = (a,b,c,d); call.argumentCount = UInt32(min(event.argumentCount,4))
                let result = scene.actorHost.call?(scene.actorHost.context, call) ?? 0
                reloadPrivate(); return UInt64(result)
            default: return unsupported(event)
            }
        } catch { fail(String(describing: error)); return 0 }
    }
    func reloadPrivate() {}
    func bind(_ context: UnsafeMutablePointer<ClawActorBindingContext>, _ event: ClawActorBindingCall) -> UInt32 {
        switch event.function {
        case 0x4f6286:
            if event.receiver == context.pointee.imageRegistryToken { return context.pointee.image.token }
            guard let name = event.name, let metadata = claw_logic_registry_find(name) else { return 0 }
            context.pointee.metadataCallback = metadata.pointee.callback; context.pointee.metadataFlags = metadata.pointee.flags
            return scene?.entry(named: String(cString: name)) ?? 0
        case 0x4f63ec: return scene?.heap.allocate(bytes: event.argument) ?? 0
        case 0x4f6428: scene?.heap.free(event.argument); return 0
        default: fail("Unimplemented humanoid binding service \(String(event.function,radix:16))"); return 0
        }
    }
    private func applyCollision(_ value: ClawCollisionActor) {
        withUnsafeMutableBytes(of: &state.pointee.actor) { raw in
            for (offset, word) in [(8,value.flags),(0x4c,value.x),(0x50,value.y),(0xcc,value.mode),(0x80,value.supportToken),(0x158,value.deltaX),(0x15c,value.deltaY)] { raw.storeBytes(of: word, toByteOffset: offset, as: UInt32.self) }
        }
    }
}
let humanoidDependency: ClawGenericEnemyDependency = { _,_,event,user in
    guard let event, let user else { return 0 }; return Unmanaged<ClawHumanoidActorServices>.fromOpaque(user).takeUnretainedValue().dependency(event.pointee)
}
private let humanoidBindingDependency: ClawActorBindingDependency = { _,context,event,user in
    guard let context, let event, let user else { return 0 }; return Unmanaged<ClawHumanoidActorServices>.fromOpaque(user).takeUnretainedValue().bind(context,event.pointee)
}

// Frozen motion's inlined ledge probe needs pinned immutable world spans.
final class ClawHumanoidTiles {
    private static var cached: [URL: WeakTiles] = [:]
    private final class WeakTiles { weak var value: ClawHumanoidTiles?; init(_ value: ClawHumanoidTiles) { self.value = value } }
    let world = UnsafeMutablePointer<ClawCollisionWorld>.allocate(capacity: 1)
    private let cells: UnsafeMutablePointer<UInt32>, rows: UnsafeMutablePointer<UInt32>, descriptions: UnsafeMutablePointer<ClawTileDescription>
    private let cellCount: Int, rowCount: Int, descriptionCount: Int
    static func load(_ root: URL, level: UInt32 = 1) throws -> ClawHumanoidTiles {
        let file = root.appendingPathComponent("LEVEL\(level)/WORLDS/WORLD.WWD")
        if let value = cached[file]?.value { return value }
        let value = try ClawHumanoidTiles(ClawWorld(data: Data(contentsOf: file)))
        cached[file] = WeakTiles(value); return value
    }
    init(_ source: ClawWorld) throws {
        guard let plane = source.planes.first(where: { $0.flags & 1 != 0 }), plane.tileWidth.nonzeroBitCount == 1, plane.tileHeight.nonzeroBitCount == 1 else { throw AssetError.invalid("Humanoid collision plane") }
        cellCount = plane.tiles.count; rowCount = plane.height; descriptionCount = source.tileDescriptions.count
        cells = .allocate(capacity: max(1,cellCount)); rows = .allocate(capacity: max(1,rowCount)); descriptions = .allocate(capacity: max(1,descriptionCount))
        cells.initialize(repeating: 0,count:max(1,cellCount)); rows.initialize(repeating:0,count:max(1,rowCount)); descriptions.initialize(repeating:ClawTileDescription(),count:max(1,descriptionCount))
        for i in plane.tiles.indices { cells[i] = UInt32(bitPattern: Int32(plane.tiles[i])) }; for i in 0..<rowCount { rows[i] = UInt32(i * plane.width) }
        for i in source.tileDescriptions.indices { descriptions[i] = source.tileDescriptions[i].native }
        world.initialize(to: ClawCollisionWorld(cells: UnsafePointer(cells), rowOffsets: UnsafePointer(rows), width: Int32(plane.width * plane.tileWidth),height:Int32(plane.height * plane.tileHeight),shiftX:UInt32(plane.tileWidth.trailingZeroBitCount),shiftY:UInt32(plane.tileHeight.trailingZeroBitCount),descriptions:UnsafePointer(descriptions),descriptionCount:UInt32(descriptionCount),actors:nil,actorCount:0,maximumStepX:14,maximumStepY:14))
    }
    deinit { world.deinitialize(count:1);world.deallocate();cells.deinitialize(count:max(1,cellCount));cells.deallocate();rows.deinitialize(count:max(1,rowCount));rows.deallocate();descriptions.deinitialize(count:max(1,descriptionCount));descriptions.deallocate() }
}

// Original shared globals are shared by every humanoid in a scene. The initial
// values below match the pinned EXE data (strike52713c=1, others zero).
final class ClawNativeHumanoidGlobals {
    var difficulty: UInt32 = 0, clockCountdown: UInt32 = 0, strongThrow: UInt32 = 0, strikeCounter: UInt32 = 1
    var damageScale: Float = 1, healthScale: Float = 1, rangeScale: Float = 1
    private final class WeakScope { weak var scene: ClawNativeScene?; weak var value: ClawNativeHumanoidGlobals?; init(_ scene: ClawNativeScene,_ value: ClawNativeHumanoidGlobals) { self.scene = scene; self.value = value } }
    private static var scopes: [ObjectIdentifier:WeakScope] = [:]
    static func shared(_ scene: ClawNativeScene) -> ClawNativeHumanoidGlobals {
        let key = ObjectIdentifier(scene)
        if let scope = scopes[key], scope.scene === scene, let value = scope.value { return value }
        let value = ClawNativeHumanoidGlobals();scopes[key] = WeakScope(scene,value);return value
    }
    struct SavedState: Codable, Equatable {
        let difficulty: UInt32, clockCountdown: UInt32, strongThrow: UInt32, strikeCounter: UInt32
        let damageScale: UInt32, healthScale: UInt32, rangeScale: UInt32
    }
    func savedState() -> SavedState {
        .init(difficulty: difficulty, clockCountdown: clockCountdown, strongThrow: strongThrow, strikeCounter: strikeCounter,
            damageScale: damageScale.bitPattern, healthScale: healthScale.bitPattern, rangeScale: rangeScale.bitPattern)
    }
    func restoreState(_ saved: SavedState) {
        difficulty = saved.difficulty; clockCountdown = saved.clockCountdown; strongThrow = saved.strongThrow
        strikeCounter = saved.strikeCounter; damageScale = Float(bitPattern: saved.damageScale)
        healthScale = Float(bitPattern: saved.healthScale); rangeScale = Float(bitPattern: saved.rangeScale)
    }
}

final class ClawNativeHumanoid: ClawHumanoidActorServices {
    enum Kind: String, Codable { case officer, soldier }
    let kind: Kind
    let globals: ClawNativeHumanoidGlobals
    let officer = UnsafeMutablePointer<ClawOfficerContext>.allocate(capacity:1)
    let human = UnsafeMutablePointer<ClawHumanEnemyContext>.allocate(capacity:1)
    let combat = UnsafeMutablePointer<ClawHumanCombatContext>.allocate(capacity:1)
    let motion = UnsafeMutablePointer<ClawEnemyMotionAuxContext>.allocate(capacity:1)
    let soldier = UnsafeMutablePointer<ClawSoldierContext>.allocate(capacity:1)
    private let soldierTail = UnsafeMutablePointer<UInt32>.allocate(capacity:24)
    private let humanStates: ClawEnemyStateView, classStates: ClawEnemyStateView
    private let tiles: ClawHumanoidTiles
    private(set) var bullets: [UInt32:ClawNativeBullet] = [:]
    private struct BulletViewBinding {
        let token: UInt32, count: UInt32, identity: ClawTokenHeap.AllocationIdentity
        let pointer: UnsafeMutablePointer<UInt32>?
    }
    private var bulletViewBindings: [BulletViewBinding?] = [nil, nil, nil]
    var onBulletCreated: ((ClawNativeBullet)->Void)?
    // Explicit global/configuration adapters, supplied by the owning host.
    var difficulty: UInt32 { get { globals.difficulty } set { globals.difficulty = newValue } }
    var clockCountdown: UInt32 { get { globals.clockCountdown } set { globals.clockCountdown = newValue } }
    var strongThrow: UInt32 { get { globals.strongThrow } set { globals.strongThrow = newValue } }
    var strikeCounter: UInt32 { get { globals.strikeCounter } set { globals.strikeCounter = newValue } }
    var damageScale: Float { get { globals.damageScale } set { globals.damageScale = newValue } }
    var healthScale: Float { get { globals.healthScale } set { globals.healthScale = newValue } }
    var rangeScale: Float { get { globals.rangeScale } set { globals.rangeScale = newValue } }
    var privateWords: Int { kind == .soldier ? 288 : 284 }
    private var tail: UnsafeMutablePointer<UInt32> {
        if kind == .soldier { return soldierTail }
        return withUnsafeMutablePointer(to:&officer.pointee.privateTail) { UnsafeMutableRawPointer($0).assumingMemoryBound(to:UInt32.self) }
    }
    init(kind: Kind, snapshot: ClawInteractionActor, scene: ClawNativeScene, resources: ClawActorResources, restoring: Bool = false) throws {
        guard let registry = scene.stateRegistry else { throw AssetError.invalid("Humanoid state registry unavailable") }
        self.kind = kind; globals = ClawNativeHumanoidGlobals.shared(scene); tiles = try ClawHumanoidTiles.load(resources.root, level: resources.level)
        humanStates = ClawEnemyStateView(registry:registry,inheritance:["Human"])
        classStates = ClawEnemyStateView(registry:registry,inheritance:kind == .officer ? ["Officer"] : [])
        let states = ClawEnemyStateView(registry:registry,inheritance:["CEnemy"])
        if kind == .soldier {
            _ = registry.resolve(classStates.entries[0].state,table:0x53c328)
            _ = registry.resolve(classStates.entries[classStates.count-1].state,table:0x53c328)
            for i in 0..<classStates.count { classStates.entries[i].function = registry.resolve(classStates.entries[i].state,table:0x53c328).function }
        }
        officer.initialize(to:ClawOfficerContext());human.initialize(to:ClawHumanEnemyContext());combat.initialize(to:ClawHumanCombatContext());motion.initialize(to:ClawEnemyMotionAuxContext());soldier.initialize(to:ClawSoldierContext());soldierTail.initialize(repeating:0,count:24)
        claw_officer_context_defaults(officer)
        let generic = UnsafeMutableRawPointer(officer).assumingMemoryBound(to:ClawGenericEnemyContext.self)
        let common = withUnsafeMutablePointer(to:&officer.pointee.sharedStates) { $0 }
        super.init(snapshot:snapshot,scene:scene,resources:resources,generic:generic,common:common,states:states)
        human.pointee.generic = generic;human.pointee.sharedStates = common;human.pointee.privateTail = tail
        human.pointee.humanStates = UnsafePointer(humanStates.entries);human.pointee.humanStateCount = humanStates.count
        human.pointee.sequenceRegistryToken = 0x63000010
        combat.pointee.human = human;combat.pointee.actorContainerToken = scene.containerToken
        motion.pointee.human = human;motion.pointee.world = UnsafePointer(tiles.world)
        officer.pointee.patrolStates = UnsafePointer(states.entries);officer.pointee.patrolStateCount = states.count
        officer.pointee.officerStates = UnsafePointer(classStates.entries);officer.pointee.officerStateCount = classStates.count;officer.pointee.sequenceRegistryToken = 0x63000010
        soldier.pointee.human = human;soldier.pointee.combat = combat;soldier.pointee.motion = motion;soldier.pointee.actorContainerToken = scene.containerToken
        soldier.pointee.soldierStates = UnsafePointer(classStates.entries);soldier.pointee.soldierStateCount = classStates.count
        if kind == .soldier { claw_soldier_context_defaults(soldier) }
        let vtable: UInt32 = kind == .soldier ? 0x50f774 : 0x50ea0c
        if !restoring && scene.heap.lookup(vtable,words:43) == nil {
            let table = scene.heap.store(token:vtable,words:43)
            withUnsafeBytes(of:&generic.pointee.virtualFunctions) { table.update(from:$0.bindMemory(to:UInt32.self).baseAddress!,count:43) }
        }
        configureViews();reloadPrivate()
    }
    deinit {
        officer.deinitialize(count:1);officer.deallocate();human.deinitialize(count:1);human.deallocate();combat.deinitialize(count:1);combat.deallocate();motion.deinitialize(count:1);motion.deallocate();soldier.deinitialize(count:1);soldier.deallocate();soldierTail.deinitialize(count:24);soldierTail.deallocate()
    }
    private func configureViews() {
        human.pointee.damageScale = damageScale;human.pointee.healthScale = healthScale;human.pointee.rangeScale = rangeScale;human.pointee.clockCountdown = clockCountdown
        officer.pointee.damageScale = damageScale;officer.pointee.healthScale = healthScale;officer.pointee.rangeScale = rangeScale;officer.pointee.difficulty = difficulty
        soldier.pointee.difficulty = difficulty;motion.pointee.strongThrow = strongThrow;common.pointee.strikeCounter = strikeCounter;generic.pointee.forcedRandom = clockCountdown
        officer.pointee.audioManagerAvailable = common.pointee.audioEnabled;officer.pointee.masterVolume = common.pointee.audioPosition
        human.pointee.otherActorToken = common.pointee.attackerToken
        human.pointee.otherActor = withUnsafeMutablePointer(to:&common.pointee.attackerActor) { UnsafeMutableRawPointer($0).assumingMemoryBound(to:UInt32.self) }
        human.pointee.otherPrimary = withUnsafeMutablePointer(to:&officer.pointee.otherPrimary) { UnsafeMutableRawPointer($0).assumingMemoryBound(to:UInt32.self) }
        human.pointee.platformPrimary = withUnsafeMutablePointer(to:&officer.pointee.platformPrimary) { UnsafeMutableRawPointer($0).assumingMemoryBound(to:UInt32.self) }
        if let scene {
            officer.pointee.otherPrimary = scene.snapshotActor(common.pointee.attackerToken)?.primary ?? ClawInteractionActor().primary
            officer.pointee.platformPrimary = scene.snapshotActor(state.pointee.actor.32)?.primary ?? ClawInteractionActor().primary
        }
    }
    override func refresh() { super.refresh();configureViews();reloadPrivate();if let scene { bullets = bullets.filter { scene.heap.lookup($0.key,words:128) != nil } } }
    override func reloadPrivate() {
        guard let raw = scene?.heap.lookup(generic.pointee.enemyToken,words:UInt32(privateWords)) else { return }
        withUnsafeMutableBytes(of:&state.pointee.enemy) { $0.copyMemory(from:UnsafeRawBufferPointer(start:raw,count:1056)) }
        tail.update(from:raw.advanced(by:264),count:privateWords-264)
    }
    override func flush() {
        guard ownsActor else { return }
        super.flush()
        if let raw = scene?.heap.lookup(generic.pointee.enemyToken,words:UInt32(privateWords)) {
            withUnsafeBytes(of:&state.pointee.enemy) { UnsafeMutableRawBufferPointer(start:raw,count:1056).copyMemory(from:$0) };raw.advanced(by:264).update(from:tail,count:privateWords-264)
        }
        strikeCounter = common.pointee.strikeCounter
        if let scene, var platform = scene.snapshotActor(state.pointee.actor.32) { platform.primary = officer.pointee.platformPrimary; scene.write(platform) }
        if human.pointee.fault != 0 || officer.pointee.fault != 0 || combat.pointee.fault != 0 || motion.pointee.fault != 0 || soldier.pointee.fault != 0 { fail("Humanoid context fault \(human.pointee.fault)/\(officer.pointee.fault)/\(combat.pointee.fault)/\(motion.pointee.fault)/\(soldier.pointee.fault)") }
    }
    func tick() { guard ownsActor else { fail("Retired humanoid owner"); return }; refresh(); let result = kind == .officer ? claw_officer_tick(state,officer,humanoidDependency,Unmanaged.passUnretained(self).toOpaque()) : claw_soldier_tick(state,soldier,humanoidDependency,Unmanaged.passUnretained(self).toOpaque());if result == 0 { fail("Humanoid callback did not complete") };flush() }
    @discardableResult func callback(_ function: UInt32,argument: UInt32 = 0) -> UInt32 { guard ownsActor else { fail("Retired humanoid owner"); return 0 }; refresh();let result = entry(function,argument:argument);if result == nil { var event = ClawGenericEnemyCall();event.function = function;event.receiver = generic.pointee.enemyToken;event.arguments.0 = argument;_ = unsupported(event) };flush();return result ?? 0 }
    override func entry(_ function: UInt32,argument: UInt32) -> UInt32? {
        let user = Unmanaged.passUnretained(self).toOpaque();var result: UInt32 = 0
        if kind == .soldier {
            if claw_soldier_entry(state,soldier,function,argument,humanoidDependency,user,&result) == 1 { return result }
        } else if claw_officer_entry(state,officer,function,argument,humanoidDependency,user,&result) == 1 { return result }
        if claw_common_enemy_entry(state,human,function,argument,humanoidDependency,user,&result) == 1 { return result }
        if claw_human_combat_entry(state,combat,function,argument,humanoidDependency,user,&result) == 1 { return result }
        if claw_enemy_motion_aux_entry(state,motion,function,argument,humanoidDependency,user,&result) == 1 { return result }
        if claw_human_enemy_entry(state,human,function,argument,humanoidDependency,user,&result) == 1 { return result }
        if claw_native_generic_enemy_state_entry(state,generic,common,function,argument,humanoidDependency,user) == 1 { return 0 }
        if claw_generic_enemy_entry(state,generic,function,argument,humanoidDependency,user) == 1 { return 0 };return nil
    }
    override func dependency(_ event: ClawGenericEnemyCall) -> UInt64 {
        guard let scene else { return 0 }
        if event.receiver == generic.pointee.enemyToken, event.function == 0x43ee10 || event.function == 0x43eee0 {
            var context = ClawHumanoidStrikeContext()
            context.human = human; context.scene = scene.actorHost; context.composeAnimation = 1
            let sequence = event.name.map { String(cString: $0) } ?? clawOriginalResourceNames[event.arguments.0]
            let sound = clawOriginalResourceNames[event.arguments.2]
            let args = [event.arguments.0, event.arguments.1, event.arguments.2]
            var result: UInt32 = 0
            func execute(_ sequencePointer: UnsafePointer<CChar>?, _ soundPointer: UnsafePointer<CChar>?) -> UInt64 {
                context.sequenceName = sequencePointer; context.soundName = soundPointer
                let supported = args.withUnsafeBufferPointer {
                    claw_humanoid_strike_entry(state, &context, event.function, $0.baseAddress,
                        event.argumentCount, humanoidDependency, Unmanaged.passUnretained(self).toOpaque(), &result)
                }
                if supported != 1 || context.fault != 0 { fail("Humanoid strike fault \(context.fault)") }
                return UInt64(result)
            }
            func executeWithSound(_ sequencePointer: UnsafePointer<CChar>?) -> UInt64 {
                if let sound { return sound.withCString { execute(sequencePointer, $0) } }
                return execute(sequencePointer, nil)
            }
            if let sequence { return sequence.withCString { executeWithSound($0) } }
            return executeWithSound(nil)
        }
        if event.function == 0x4c8da0, event.name.map({String(cString:$0)}) == "Bullet" || (event.function == 0x4c8da0 && event.arguments.4 == 0x522e0c) {
            flush();var fault: UInt32 = 0
            let actor = claw_scene_actor_create(scene.containerToken,ClawSceneActorCreate(id:event.arguments.0,x:event.arguments.1,y:event.arguments.2,z:event.arguments.3,entryToken:scene.entry(named:"Bullet"),flags:event.arguments.5),scene.actorHost,&fault)
            guard fault == 0, let snapshot = scene.snapshotActor(actor) else { fail("Original Bullet scene creation fault \(fault)");return 0 }
            let child = ClawNativeBullet(snapshot:snapshot,scene:scene,resources:resources);if sceneServiceBound, let service = externalService { child.bindSceneService(service) } else { child.externalService = externalService };child.frameClock = frameClock;bullets[actor] = child;onBulletCreated?(child);soldier.pointee.bulletToken = actor;copyBullet(child);return UInt64(actor)
        }
        if event.function == 0x4c7970, let child = bullets[event.receiver], event.name.map({String(cString:$0)}) == "LEVEL_MUSKETBALL" {
            let result = child.callback(0x4c7970,argument:0x52c4a0);copyBullet(child);return UInt64(result)
        }
        if event.function == 0x40fec0, let child = bullets[event.arguments.0] { child.tick();copyBullet(child);return child.failure == nil ? 1 : 0 }
        return super.dependency(event)
    }
    private func copyBullet(_ child: ClawNativeBullet) {
        guard let scene else { return };child.flush();soldier.pointee.bulletToken = child.token
        soldier.pointee.bulletActor = scene.heap.lookup(child.token,words:128);soldier.pointee.bulletPrimary = scene.heap.lookup(child.state.pointee.actor.27,words:93)
        soldier.pointee.bulletPrivate = scene.heap.lookup(child.generic.pointee.enemyToken,words:84)
        let spans: [(UInt32, UInt32, UnsafeMutablePointer<UInt32>?)] = [
            (child.token, 4, soldier.pointee.bulletActor),
            (child.state.pointee.actor.27, 372, soldier.pointee.bulletPrimary),
            (child.generic.pointee.enemyToken, 336, soldier.pointee.bulletPrivate)
        ]
        bulletViewBindings = spans.map { token, count, pointer in
            guard let pointer, let identity = scene.heap.containingAllocationIdentity(at: token, count: count) else { return nil }
            return BulletViewBinding(token: token, count: count, identity: identity, pointer: pointer)
        }
    }
}

extension ClawNativeHumanoid {
    struct SavedState: Codable, Equatable {
        let kind: Kind
        let service: ServiceSavedState
        let officer: [String: Data], human: [String: Data], combat: [String: Data], motion: [String: Data], soldier: [String: Data]
        let soldierTail: [UInt32]
        let humanStates: ClawEnemyStateView.SavedState, classStates: ClawEnemyStateView.SavedState
        let bullets: [ClawSnapshotOwnerKey]
        let bulletViews: [ClawSnapshotWitness?]
    }
    func savedState() throws -> SavedState {
        // These optional external views are never installed by the scene join.
        // Reject injected component-test hosts instead of discarding their links.
        guard human.pointee.effectActor == nil, human.pointee.effectPrimary == nil, human.pointee.effectPrivate == nil,
              combat.pointee.scene.context == nil, soldier.pointee.scene.context == nil,
              let scene else { throw ClawSnapshotError.invalidState }
        let pointers = [soldier.pointee.bulletActor, soldier.pointee.bulletPrimary, soldier.pointee.bulletPrivate]
        let views: [ClawSnapshotWitness?] = try bulletViewBindings.enumerated().map { index, binding in
            guard let binding else {
                guard pointers[index] == nil else { throw ClawSnapshotError.invalidState }; return nil
            }
            guard pointers[index] == binding.pointer else { throw ClawSnapshotError.invalidState }
            let witness = ClawSnapshotWitness(heap: scene.heap, token: binding.token, count: binding.count, identity: binding.identity, interior: true)
            if witness.live, scene.heap.lookup(binding.token, words: binding.count / 4) != binding.pointer { throw ClawSnapshotError.invalidState }
            return witness
        }
        return SavedState(kind: kind, service: try savedServiceState(), officer: Self.officerFields.capture(officer.pointee),
            human: Self.humanFields.capture(human.pointee), combat: Self.combatFields.capture(combat.pointee),
            motion: Self.motionFields.capture(motion.pointee), soldier: Self.soldierFields.capture(soldier.pointee),
            soldierTail: Array(UnsafeBufferPointer(start: soldierTail, count: 24)), humanStates: humanStates.savedState(),
            classStates: classStates.savedState(), bullets: try bullets.keys.sorted().map { try bullets[$0]!.snapshotOwnerKey() }, bulletViews: views)
    }
    static func restoring(_ saved: SavedState, scene: ClawNativeScene, resources: ClawActorResources,
                          heap plan: ClawTokenHeap.RestorePlan, bullets: [ClawSnapshotOwnerKey: ClawNativeBullet]) throws -> ClawNativeHumanoid {
        guard saved.soldierTail.count == 24, saved.bulletViews.count == 3,
              Set(saved.bullets.map(\.token)).count == saved.bullets.count, saved.bullets.allSatisfy({ bullets[$0] != nil })
        else { throw ClawSnapshotError.invalidState }
        let result = try ClawNativeHumanoid(kind: saved.kind, snapshot: savedActor(saved.service), scene: scene, resources: resources, restoring: true)
        result.officer.pointee = try officerFields.restoring(saved.officer, into: result.officer.pointee)
        result.human.pointee = try humanFields.restoring(saved.human, into: result.human.pointee)
        result.combat.pointee = try combatFields.restoring(saved.combat, into: result.combat.pointee)
        result.motion.pointee = try motionFields.restoring(saved.motion, into: result.motion.pointee)
        result.soldier.pointee = try soldierFields.restoring(saved.soldier, into: result.soldier.pointee)
        saved.soldierTail.withUnsafeBufferPointer { result.soldierTail.update(from: $0.baseAddress!, count: 24) }
        try result.restoreServiceState(saved.service, heap: plan)
        try result.humanStates.restoreState(saved.humanStates); try result.classStates.restoreState(saved.classStates)
        let counts: [UInt32] = [4, 372, 336]
        result.bulletViewBindings = try saved.bulletViews.enumerated().map { index, witness in
            guard let witness else { return nil }
            guard witness.reference.count == counts[index], witness.reference.interior else { throw ClawSnapshotError.invalidState }
            let identity = try witness.resolve(in: plan)
            let pointer: UnsafeMutablePointer<UInt32>?
            if witness.live {
                guard let bytes = plan.bytes(for: witness.reference) else { throw ClawSnapshotError.invalidState }
                pointer = UnsafeMutableRawPointer(bytes).assumingMemoryBound(to: UInt32.self)
            } else { pointer = nil } // A stale view can never borrow replacement storage.
            return BulletViewBinding(token: witness.reference.token, count: witness.reference.count, identity: identity, pointer: pointer)
        }
        let pointers = result.bulletViewBindings.map { $0?.pointer }
        result.soldier.pointee.bulletActor = pointers[0]; result.soldier.pointee.bulletPrimary = pointers[1]
        result.soldier.pointee.bulletPrivate = pointers[2]
        result.bullets = Dictionary(uniqueKeysWithValues: saved.bullets.map { ($0.token, bullets[$0]!) })
        return result
    }
    private static let officerFields = ClawSnapshotFields<ClawOfficerContext>(fields: [
        .init("privateTail", \.privateTail), .init("damageScale", \.damageScale), .init("healthScale", \.healthScale),
        .init("rangeScale", \.rangeScale), .init("difficulty", \.difficulty), .init("sequenceRegistryToken", \.sequenceRegistryToken),
        .init("audioManagerToken", \.audioManagerToken), .init("audioManagerAvailable", \.audioManagerAvailable), .init("masterVolume", \.masterVolume),
        .init("effectToken", \.effectToken), .init("effectActor", \.effectActor), .init("effectPrimary", \.effectPrimary), .init("effectPrivate", \.effectPrivate),
        .init("otherActorToken", \.otherActorToken), .init("otherActor", \.otherActor), .init("otherPrimary", \.otherPrimary),
        .init("platformPrimary", \.platformPrimary), .init("fault", \.fault)
    ])
    static let humanFields = ClawSnapshotFields<ClawHumanEnemyContext>(fields: [
        .init("damageScale", \.damageScale), .init("healthScale", \.healthScale), .init("rangeScale", \.rangeScale),
        .init("sequenceRegistryToken", \.sequenceRegistryToken), .init("clockCountdown", \.clockCountdown),
        .init("effectToken", \.effectToken), .init("otherActorToken", \.otherActorToken), .init("fault", \.fault)
    ])
    private static let combatFields = ClawSnapshotFields<ClawHumanCombatContext>(fields: [
        .init("actorContainerToken", \.actorContainerToken), .init("fault", \.fault)
    ])
    static let motionFields = ClawSnapshotFields<ClawEnemyMotionAuxContext>(fields: [
        .init("strongThrow", \.strongThrow), .init("fault", \.fault)
    ])
    private static let soldierFields = ClawSnapshotFields<ClawSoldierContext>(fields: [
        .init("difficulty", \.difficulty), .init("actorContainerToken", \.actorContainerToken), .init("bulletToken", \.bulletToken), .init("fault", \.fault)
    ])
}
