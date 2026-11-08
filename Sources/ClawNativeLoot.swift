import Foundation

// Shared original loot table, creator/resource services and sound dedup globals.
final class ClawNativeLoot {
    weak var scene: ClawNativeScene?
    let resources: ClawActorResources
    let globals = UnsafeMutablePointer<ClawWorldLootGlobals>.allocate(capacity:1)
    let context = UnsafeMutablePointer<ClawWorldLootContext>.allocate(capacity:1)
    let itemContext = UnsafeMutablePointer<ClawItemPickupContext>.allocate(capacity:1)
    let player = UnsafeMutablePointer<ClawPlayerLocomotion>.allocate(capacity:1)
    private(set) var goodies: [UInt32:ClawNativeGoodie] = [:]
    private(set) var pickups: [UInt32:ClawNativePickup] = [:]
    private(set) var failure: String?
    private(set) var unresolved: Set<UInt32> = []
    var onCreated: ((ClawNativeGoodie)->Void)?, onRebound: ((ClawNativePickup)->Void)?
    var externalService: ((ClawItemPickupCall)->UInt32?)?
    // Root supplies a full runtime commit, including private ammo/counters.
    // Awards refuse to run without it instead of losing private write-back.
    var readPlayer: (() -> ClawPlayerLocomotion)?, writePlayer: ((ClawPlayerLocomotion)->Void)?
    var frameClock: (() -> (time:UInt32,animationDelta:UInt32,stageDelta:UInt32))?
    private var imageNames: [UInt32:String] = [:]
    private var configurationStorage:UInt32 = 0
    init(scene:ClawNativeScene,resources:ClawActorResources) throws {
        self.scene = scene;self.resources = resources
        globals.initialize(to:ClawWorldLootGlobals());context.initialize(to:ClawWorldLootContext());itemContext.initialize(to:ClawItemPickupContext());player.initialize(to:scene.player.runtime)
        claw_world_loot_defaults(globals);context.pointee.scene = scene.actorHost
        itemContext.pointee.scene = scene.actorHost;itemContext.pointee.loot = globals;itemContext.pointee.player = player
        itemContext.pointee.playerToken = scene.player.sceneSnapshot().token;itemContext.pointee.playerPrimaryToken = scene.player.sceneSnapshot().actor.27;itemContext.pointee.playerPrivateToken = scene.player.sceneSnapshot().primary.5
        // Explicit host configuration span; zero disables unrecovered glitter.
        configurationStorage = scene.heap.allocate(bytes:0x128);itemContext.pointee.managerToken = configurationStorage
        readPlayer = { [weak scene] in scene?.player.runtime ?? ClawPlayerLocomotion() };writePlayer = { [weak scene] value in scene?.writePlayerRuntime(value) }
        guard initialize() else { throw AssetError.invalid(failure ?? "Original loot initialization") }
    }
    deinit { scene?.heap.free(configurationStorage);globals.deinitialize(count:1);globals.deallocate();context.deinitialize(count:1);context.deallocate();itemContext.deinitialize(count:1);itemContext.deallocate();player.deinitialize(count:1);player.deallocate() }
    func fail(_ message:String) { if failure == nil { failure = message } }
    func word(_ index:Int) -> UInt32 { withUnsafeBytes(of:&globals.pointee.words) { $0.load(fromByteOffset:index*4,as:UInt32.self) } }
    @discardableResult func initialize() -> Bool {
        if let scene, let profile = scene.platforms?.profile {
            //4719e0 reads the first live word selected by537960. Level1's
            //source452b00 profile selects MAPPIECE through its odd word1.
            globals.pointee.configurationWord = scene.heap.lookup(profile.pointee.selectedToken,words:1)?.pointee ?? 0
        }
        let result = claw_world_loot_initialize(scene?.sceneIdentity ?? 0,globals,context,nativeLootDependency,Unmanaged.passUnretained(self).toOpaque())
        if result != 1 || context.pointee.fault != 0 { fail("Loot initialization fault \(context.pointee.fault)") };return result == 1 && context.pointee.fault == 0
    }
    @discardableResult func lootDrop(receiver:UInt32) -> Bool {
        guard let scene else { return false };globals.pointee.audioVolume = scene.player.audio?.routing.masterVolume ?? 0
        let result = claw_world_loot_drop(receiver,globals,context,nativeLootDependency,Unmanaged.passUnretained(self).toOpaque())
        if result != 1 || context.pointee.fault != 0 { fail("Loot drop fault \(context.pointee.fault)") };return result == 1 && context.pointee.fault == 0 && failure == nil
    }
    @discardableResult func rebind(_ token:UInt32,item:Int32) -> Bool {
        let result = claw_world_loot_rebind_actor(token,item,globals,context,nativeLootDependency,Unmanaged.passUnretained(self).toOpaque())
        if context.pointee.fault != 0 { fail("Loot rebind fault \(context.pointee.fault)") };return result == 1 && context.pointee.fault == 0
    }
    func remove(_ token:UInt32) { goodies.removeValue(forKey:token);pickups.removeValue(forKey:token) }
    func attachPickup(_ token: UInt32) {
        guard pickups[token] == nil else { return }
        let body = ClawNativePickup(token: token, loot: self); pickups[token] = body; onRebound?(body)
    }
    func playerSound(item: UInt32) -> UInt32? {
        guard let body = pickups[item] else { return nil }
        return body.callback(0x41d6f0)
    }
    @discardableResult func callback(_ token:UInt32,function:UInt32) -> UInt32 {
        if let body = goodies[token] {
            if function == 0x40e690 { body.tick();return body.failure == nil ? 1 : 0 }
            if function == 0x4dc830 || function == 0x4dc850 { return body.callback(function) }
        }
        if let body = pickups[token], ClawNativePickup.supported.contains(function) { return body.callback(function) }
        unresolved.insert(function);return 0
    }
    func privateDestructor(receiver:UInt32,flags:UInt32) -> UInt32? {
        guard let body = goodies.values.first(where:{$0.generic.pointee.enemyToken == receiver}) else { return nil }
        return body.callback(0x484d90,argument:flags)
    }
    func refreshItemContext() {
        guard let scene else { return }
        let frame = frameClock?() ?? (time:scene.gameTime,animationDelta:scene.animationDelta,stageDelta:scene.player.runtime.stageDelta)
        itemContext.pointee.tick = frame.time;itemContext.pointee.animationDelta = frame.animationDelta;itemContext.pointee.stageDelta = frame.stageDelta
        itemContext.pointee.audioEnabled = scene.player.audio == nil ? 0 : 1;itemContext.pointee.masterVolume = scene.player.audio?.routing.masterVolume ?? 0
    }
    func bindImage(_ token:UInt32,name:String) throws -> UInt32 {
        guard let scene, let snapshot = scene.snapshotActor(token),let images = try resources.images(name:name) else { return 0 }
        var binding = ClawActorResourceBindings();binding.actor = snapshot.actor
        var cx = ClawActorBindingContext();cx.image = images.binding();cx.imageRegistryToken = 0x63000040
        let value = name.withCString { claw_actor_bind_default_image(&binding,&cx,$0,{_,cx,event,_ in
            guard let cx,let event,event.pointee.function == 0x4f6286 else { return 0 };return cx.pointee.image.token
        },nil) }
        var changed = snapshot;changed.actor = binding.actor;scene.write(changed);return value
    }
    func lookup(_ name:String) throws -> UInt32 {
        guard let scene else { return 0 }
        if let metadata = name.withCString({claw_logic_registry_find($0)}) { _ = metadata;return scene.entry(named:name) }
        if let image = try resources.images(name:name) {
            let bytes = Array(name.utf8)+[UInt8(0)];guard bytes.count <= 64,let raw = scene.heap.lookup(image.token+0x24,words:16) else { throw AssetError.invalid("Loot resource name span \(name)") }
            let target = UnsafeMutableRawBufferPointer(start:raw,count:64);target.initializeMemory(as:UInt8.self,repeating:0);bytes.withUnsafeBytes { UnsafeMutableRawBufferPointer(rebasing:target.prefix(bytes.count)).copyMemory(from:$0) }
            imageNames[image.token+0x24] = name;return image.token
        }
        guard let sound = scene.player.audio?.resolve(name:name) else { return 0 }
        // Audio owns a separate stable token heap. Project the one actual root
        // field read by pickup41d6f0 into the scene, without guessing PCM data.
        let root = scene.heap.lookup(sound.resourceToken,words:5) ?? scene.heap.store(token:sound.resourceToken,words:5)
        root[4] = sound.voicePoolToken;return sound.resourceToken
    }
    func sourceService(_ event:ClawWorldLootCall) -> UInt32 {
        guard let scene else { return 0 };let a = event.arguments.0
        do {
            switch event.function {
            case 0x4f6286: guard let name = event.name else { return 0 };return try lookup(String(cString:name))
            case 0x4a3050: return scene.nextRandom()
            case 0x4208e0: return scene.player.audio?.play(resource:event.receiver,volume:a) ?? 0
            case 0x4c8da0:
                guard event.arguments.4 == 0x522cc0 else { unresolved.insert(event.function);return 0 };var fault:UInt32 = 0
                let token = claw_scene_actor_create(event.receiver,ClawSceneActorCreate(id:a,x:event.arguments.1,y:event.arguments.2,z:event.arguments.3,entryToken:scene.entry(named:"BouncingGoodie"),flags:event.arguments.5),scene.actorHost,&fault)
                guard fault == 0,let snapshot = scene.snapshotActor(token) else { fail("Goodie scene creation fault \(fault)");return 0 }
                let body = try ClawNativeGoodie(snapshot:snapshot,loot:self);goodies[token] = body;onCreated?(body);return token
            case 0x4c7970:
                guard let name = imageNames[a] ?? Self.literalNames[a] else { fail("Unresolved loot image name token \(String(a,radix:16))");return 0 }
                return try bindImage(event.receiver,name:name)
            case 0x40e690:
                guard let body = goodies[a] else { context.pointee.fault = 1;return 0 };body.tick()
                if let failure = body.failure { fail(failure);context.pointee.fault = 1;return 0 };return 1
            default:
                if ClawNativePickup.supported.contains(event.function) {
                    let body = pickups[a] ?? ClawNativePickup(token:a,loot:self);pickups[a] = body;onRebound?(body);return body.callback(event.function)
                }
                unresolved.insert(event.function);return 0
            }
        } catch { fail(String(describing:error));context.pointee.fault = 1;return 0 }
    }
}
private let nativeLootDependency:ClawWorldLootDependency = {_,_,event,user in
    guard let event,let user else { return 0 };return Unmanaged<ClawNativeLoot>.fromOpaque(user).takeUnretainedValue().sourceService(event.pointee)
}
extension ClawNativeLoot {
    static let literalNames: [UInt32:String] = [
        0x522864: "CursePowerup",
        0x522894: "AmmoPowerup",
        0x5228b0: "MagicPowerup",
        0x5228c0: "TreasurePowerup",
        0x52292c: "SpecialPowerup",
        0x52293c: "EndOfLevelPowerup",
        0x522950: "PowerupGlitter",
        0x522960: "HealthPowerup",
        0x5235d0: "GAME_DYNAMITE",
        0x5240d8: "GAME_CYCLE100",
        0x52418c: "GAME_MAGICCLAW",
        0x524d1c: "GAME_MAPPIECE",
        0x525f88: "GAME_TREASURE_CHALICES_PURPLE",
        0x525fa8: "GAME_TREASURE_CHALICES_BLUE",
        0x525fc4: "GAME_TREASURE_CHALICES_GREEN",
        0x525fe4: "GAME_TREASURE_CHALICES_RED",
        0x526000: "GAME_TREASURE_CROSSES_PURPLE",
        0x526020: "GAME_TREASURE_CROSSES_BLUE",
        0x52603c: "GAME_TREASURE_CROSSES_GREEN",
        0x526058: "GAME_TREASURE_CROSSES_RED",
        0x526074: "GAME_TREASURE_SCEPTERS_PURPLE",
        0x526094: "GAME_TREASURE_SCEPTERS_BLUE",
        0x5260b0: "GAME_TREASURE_SCEPTERS_GREEN",
        0x5260d0: "GAME_TREASURE_SCEPTERS_RED",
        0x5260ec: "GAME_TREASURE_GECKOS_PURPLE",
        0x526108: "GAME_TREASURE_GECKOS_BLUE",
        0x526124: "GAME_TREASURE_GECKOS_GREEN",
        0x526140: "GAME_TREASURE_GECKOS_RED",
        0x5279b8: "GAME_TREASURE_COINS",
        0x52a07c: "GAME_WARP",
        0x52a198: "GAME_POWERUP",
        0x52a1e0: "LEVEL_GEM",
        0x52a1ec: "GAME_POWERUPS_EXTRALIFE",
        0x52a204: "GAME_MAGICPOWERUP",
        0x52a23c: "GAME_VERTWARP",
        0x52a24c: "GAME_POWERUPS_PLASMASWORD",
        0x52a268: "GAME_POWERUPS_ICESWORD",
        0x52a280: "GAME_POWERUPS_LIGHTNINGSWORD",
        0x52a2a0: "GAME_POWERUPS_FIRESWORD",
        0x52a2b8: "GAME_EXTRALIFE",
        0x52a2c8: "GAME_POWERUPS_INVULNERABLE",
        0x52a2e4: "GAME_POWERUPS_GHOST",
        0x52a2f8: "GAME_TREASURE_JEWELEDSKULL_PURPLE",
        0x52a31c: "GAME_TREASURE_JEWELEDSKULL_BLUE",
        0x52a33c: "GAME_TREASURE_JEWELEDSKULL_GREEN",
        0x52a360: "GAME_TREASURE_JEWELEDSKULL_RED",
        0x52a380: "GAME_TREASURE_CROWNS_PURPLE",
        0x52a39c: "GAME_TREASURE_CROWNS_BLUE",
        0x52a3b8: "GAME_TREASURE_CROWNS_GREEN",
        0x52a3d4: "GAME_TREASURE_CROWNS_RED",
        0x52a3f0: "GAME_CURSES_FREEZE",
        0x52a404: "GAME_CURSE1",
        0x52a410: "GAME_CURSES_TREASURE",
        0x52a428: "GAME_CURSE4",
        0x52a434: "GAME_CURSES_LIFE",
        0x52a448: "GAME_CURSE5",
        0x52a454: "GAME_CURSES_HEALTH",
        0x52a468: "GAME_CURSE6",
        0x52a474: "GAME_CURSES_MAGIC",
        0x52a488: "GAME_CURSE2",
        0x52a494: "GAME_CURSES_AMMO",
        0x52a4a8: "GAME_CURSE3",
        0x52a4b4: "GAME_MAGIC_STARGLOW",
        0x52a4c8: "GAME_MAGIC_GLOW",
        0x52a4d8: "GAME_HEALTH_POTION2",
        0x52a4ec: "GAME_HEALTH_POTION1",
        0x52a500: "GAME_HEALTH_POTION3",
        0x52a514: "GAME_MILK",
        0x52a520: "LEVEL_HEALTH",
        0x52a530: "GAME_FOODITEM",
        0x52a540: "GAME_CATNIPS_NIP2",
        0x52a554: "GAME_CATNIPS_NIP1",
        0x52a568: "GAME_CATNMAG",
        0x52a578: "GAME_AMMO_SHOTBAG",
        0x52a58c: "GAME_AMMO_SHOT",
        0x52a59c: "GAME_AMMO_DEATHBAG",
        0x52a5b0: "GAME_AMMUNITION",
        0x52a5c0: "GAME_PICKUP2",
        0x52a5d0: "GAME_SCEPTER",
        0x52a5e0: "GAME_CROSS",
        0x52a5ec: "GAME_TREASURE_NECKLACE",
        0x52a604: "GAME_PICKUP1",
        0x52a614: "GAME_TREASURE_RINGS_PURPLE",
        0x52a630: "GAME_TREASURE_RINGS_BLUE",
        0x52a64c: "GAME_TREASURE_RINGS_GREEN",
        0x52a668: "GAME_TREASURE_RINGS_RED",
        0x52a680: "GAME_RINGS",
        0x52a68c: "GAME_TREASURE_GOLDBARS",
        0x52a6a4: "GAME_TREASURE",
        0x52a6b4: "GAME_COIN",
    ]
}

final class ClawNativeGoodie:ClawHumanoidActorServices {
    weak var loot:ClawNativeLoot?
    let context = UnsafeMutablePointer<ClawBouncingGoodieContext>.allocate(capacity:1)
    private let ownGeneric = UnsafeMutablePointer<ClawGenericEnemyContext>.allocate(capacity:1)
    private let ownShared = UnsafeMutablePointer<ClawGenericEnemyStatesContext>.allocate(capacity:1)
    init(snapshot:ClawInteractionActor,loot:ClawNativeLoot, restoring: Bool = false) throws {
        guard let scene = loot.scene,let registry = scene.stateRegistry else { throw AssetError.invalid("Goodie state registry") }
        self.loot = loot
        let states = ClawEnemyStateView(registry:registry,inheritance:[])
        _ = registry.resolve(states.entries[0].state,table:0x5349e0);_ = registry.resolve(states.entries[states.count-1].state,table:0x5349e0)
        for i in 0..<states.count { states.entries[i].function = registry.resolve(states.entries[i].state,table:0x5349e0).function }
        context.initialize(to:ClawBouncingGoodieContext());ownGeneric.initialize(to:ClawGenericEnemyContext());ownShared.initialize(to:ClawGenericEnemyStatesContext());claw_generic_enemy_context_defaults(ownGeneric)
        super.init(snapshot:snapshot,scene:scene,resources:loot.resources,generic:ownGeneric,common:ownShared,states:states)
        context.pointee.generic = generic;context.pointee.shared = common;context.pointee.scene = scene.actorHost;context.pointee.loot = loot.globals
        context.pointee.sequenceRegistryToken = 0x63000010;context.pointee.states = UnsafePointer(states.entries);context.pointee.stateCount = states.count
        claw_bouncing_goodie_context_defaults(context)
        if !restoring && scene.heap.lookup(0x50b68c,words:10) == nil {
            let table = scene.heap.store(token:0x50b68c,words:10)
            withUnsafeBytes(of:&generic.pointee.virtualFunctions) { table.update(from:$0.bindMemory(to:UInt32.self).baseAddress!,count:10) }
        }
        bindNativeOwner(.loot, clock: { [weak loot,weak scene] in
            let frame = loot?.frameClock?();return (time:frame?.time ?? scene?.gameTime ?? 0,delta:frame?.animationDelta ?? scene?.animationDelta ?? 0)
        });reloadPrivate();updateImage()
    }
    deinit { context.deinitialize(count:1);context.deallocate();ownGeneric.deinitialize(count:1);ownGeneric.deallocate();ownShared.deinitialize(count:1);ownShared.deallocate() }
    override func refresh() { super.refresh();reloadPrivate();updateImage() }
    override func reloadPrivate() {
        guard let raw = scene?.heap.lookup(generic.pointee.enemyToken,words:104) else { return }
        withUnsafeMutableBytes(of:&state.pointee.enemy) { UnsafeMutableRawBufferPointer(rebasing:$0.prefix(416)).copyMemory(from:UnsafeRawBufferPointer(start:raw,count:416)) }
    }
    override func flush() {
        guard ownsActor else { return };super.flush();if let raw = scene?.heap.lookup(generic.pointee.enemyToken,words:104) {
            withUnsafeBytes(of:&state.pointee.enemy) { UnsafeMutableRawBufferPointer(start:raw,count:416).copyMemory(from:UnsafeRawBufferPointer(rebasing:$0.prefix(416))) }
        };if context.pointee.fault != 0 { fail("Goodie context fault \(context.pointee.fault)") }
    }
    private func updateImage() {
        guard let raw = scene?.heap.lookup(state.pointee.actor.93,words:16) else { return }
        withUnsafeMutableBytes(of:&context.pointee.imageHeader) { $0.copyMemory(from:UnsafeRawBufferPointer(start:raw,count:64)) }
    }
    func tick() {
        guard ownsActor else { fail("Retired goodie owner");return };guard loot != nil,scene != nil else { fail("Goodie owner lifetime ended");return }
        refresh()
        if state.pointee.primary.4 != 0x40e690,let loot { _ = loot.callback(token,function:state.pointee.primary.4);return }
        if claw_bouncing_goodie_callback(state,context,humanoidDependency,Unmanaged.passUnretained(self).toOpaque()) == 0 { fail("Goodie callback incomplete") };flush()
    }
    @discardableResult func callback(_ function:UInt32,argument:UInt32 = 0) -> UInt32 {
        guard ownsActor else { fail("Retired goodie owner");return 0 };guard loot != nil,scene != nil else { fail("Goodie owner lifetime ended");return 0 }
        refresh();let result = entry(function,argument:argument);if result == nil { var event = ClawGenericEnemyCall();event.function = function;_ = unsupported(event) };flush();return result ?? 0
    }
    override func entry(_ function:UInt32,argument:UInt32) -> UInt32? {
        guard loot != nil,scene != nil else { fail("Goodie owner lifetime ended");return nil }
        var result:UInt32 = 0
        if function == 0x4dc830 || function == 0x4dc850 {
            let slot = function == 0x4dc830 ? 5 : 6
            let method = withUnsafeBytes(of:&generic.pointee.virtualFunctions) { $0.load(fromByteOffset:slot*4,as:UInt32.self) }
            guard method == 0x4bb030 else { return nil }
            return claw_bouncing_goodie_entry(state,context,method,0,humanoidDependency,Unmanaged.passUnretained(self).toOpaque(),&result) == 1 ? result : nil
        }
        return claw_bouncing_goodie_entry(state,context,function,argument,humanoidDependency,Unmanaged.passUnretained(self).toOpaque(),&result) == 1 ? result : nil
    }
    override func dependency(_ event:ClawGenericEnemyCall) -> UInt64 {
        if event.function == 0x4719e0 { return loot?.initialize() == true ? 1 : 0 }
        if event.function == 0x473660 {
            flush();let result = loot?.rebind(event.arguments.0,item:Int32(bitPattern:event.arguments.1)) ?? false
            if let snapshot = scene?.snapshotActor(token) { accept(snapshot) };return result ? 1 : 0
        }
        let result = super.dependency(event);updateImage();return result
    }
}

extension ClawNativeGoodie {
    struct SavedState: Codable, Equatable { let service: ServiceSavedState, context: [String: Data] }
    func savedState() throws -> SavedState {
        guard nativeOwnerBinding == .loot else { throw ClawSnapshotError.invalidState }
        return .init(service: try savedServiceState(), context: Self.snapshotFields.capture(context.pointee))
    }
    static func restoring(_ saved: SavedState, loot: ClawNativeLoot, heap plan: ClawTokenHeap.RestorePlan) throws -> ClawNativeGoodie {
        let body = try ClawNativeGoodie(snapshot: savedActor(saved.service), loot: loot, restoring: true)
        try body.restoreServiceState(saved.service, heap: plan)
        body.context.pointee = try snapshotFields.restoring(saved.context, into: body.context.pointee)
        return body
    }
    private static let snapshotFields = ClawSnapshotFields<ClawBouncingGoodieContext>(fields: [
        .init("sequenceRegistryToken", \.sequenceRegistryToken),
        .init("imageMinimum", \.imageMinimum),
        .init("imageMaximum", \.imageMaximum),
        .init("minimumImageToken", \.minimumImageToken),
        .init("imageHeader", \.imageHeader),
        .init("fault", \.fault)
    ])
}

extension ClawNativeLoot {
    struct SavedState: Codable, Equatable {
        let globals: ClawSnapshotValue<ClawWorldLootGlobals>, player: ClawSnapshotValue<ClawPlayerLocomotion>
        let context: [String: Data], items: [String: Data]
        let goodies: [ClawNativeGoodie.SavedState], pickups: [ClawNativePickup.SavedState]
        let imageNames: [UInt32: String], configurationStorage: UInt32
        let failure: String?, unresolved: Set<UInt32>
    }
    func savedState() throws -> SavedState {
        guard scene != nil else { throw ClawSnapshotError.incompleteOwners }
        return .init(globals: ClawSnapshotValue(globals.pointee), player: ClawSnapshotValue(player.pointee),
            context: Self.contextFields.capture(context.pointee), items: Self.itemFields.capture(itemContext.pointee),
            goodies: try goodies.keys.sorted().map { try goodies[$0]!.savedState() },
            pickups: try pickups.keys.sorted().map { try pickups[$0]!.savedState() }, imageNames: imageNames,
            configurationStorage: configurationStorage, failure: failure, unresolved: unresolved)
    }
    func prepareRestore(_ saved: SavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws -> Void {
        guard let scene, saved.configurationStorage == configurationStorage,
              Set(saved.goodies.map { $0.service.token }).count == saved.goodies.count,
              Set(saved.pickups.map(\.token)).count == saved.pickups.count else { throw ClawSnapshotError.invalidState }
        try scene.heap.validateRestore(plan)
        let cx = try Self.contextFields.restoring(saved.context, into: context.pointee)
        let items = try Self.itemFields.restoring(saved.items, into: itemContext.pointee)
        let goodies = try Dictionary(uniqueKeysWithValues: saved.goodies.map { ($0.service.token, try ClawNativeGoodie.restoring($0, loot: self, heap: plan)) })
        let pickups = try Dictionary(uniqueKeysWithValues: saved.pickups.map { ($0.token, try ClawNativePickup.restoring($0, owner: self, heap: plan)) })
        return { [self] in
            try scene.heap.validateInstalledRestore(plan)
            globals.pointee = saved.globals.value; context.pointee = cx; itemContext.pointee = items
            // This is the loot participant's cached player, not the live player.
            player.pointee = saved.player.value
            self.goodies = goodies; self.pickups = pickups; imageNames = saved.imageNames
            failure = saved.failure; unresolved = saved.unresolved
        }
    }
    private static let contextFields = ClawSnapshotFields<ClawWorldLootContext>(fields: [
        .init("composeCreation", \.composeCreation),
        .init("fault", \.fault)
    ])
    private static let itemFields = ClawSnapshotFields<ClawItemPickupContext>(fields: [
        .init("playerToken", \.playerToken),
        .init("playerPrimaryToken", \.playerPrimaryToken),
        .init("playerPrivateToken", \.playerPrivateToken),
        .init("managerToken", \.managerToken),
        .init("animationDelta", \.animationDelta),
        .init("stageDelta", \.stageDelta),
        .init("tick", \.tick),
        .init("audioEnabled", \.audioEnabled),
        .init("masterVolume", \.masterVolume),
        .init("lastSoundTick", \.lastSoundTick),
        .init("lastSoundToken", \.lastSoundToken),
        .init("auxiliaryManagerToken", \.auxiliaryManagerToken),
        .init("auxiliarySceneToken", \.auxiliarySceneToken),
        .init("composeCreation", \.composeCreation),
        .init("fault", \.fault)
    ])
}
extension ClawWorldLootGlobals: ClawSnapshotNativeValue {}
