import Foundation

// Whole source PowderKeg/Crate/stack controllers share raw actor/private words.
// Common constructor/FSM/state bodies compose the existing frozen enemy layer.
final class ClawNativeBreakables {
    static let callbacks:Set<UInt32> = [0x46f1e0,0x433070,0x48d560,0x48d620]
    static let worldCallbacks:Set<UInt32> = [0x46f1e0,0x48d560,0x48d620]
    static let owned:Set<UInt32> = callbacks.union([0x46f2a0,0x433130,0x48de40,0x48d6e0,0x46f6a0,0x433ad0,0x46fc60,0x46fc90,0x46fbe0,0x46fc20,0x46fa90,0x434050,0x433ed0,0x433f30,0x433f70,0x433fb0,0x434170,0x434180,0x46f5d0,0x433a00,0x46f5b0,0x4339e0,0x4735b0,0x40f540,0x40f450,0x473610])
    weak var scene:ClawNativeScene?
    let globals = UnsafeMutablePointer<ClawBreakableGlobals>.allocate(capacity:1)
    private let context = UnsafeMutablePointer<ClawBreakableContext>.allocate(capacity:1)
    private(set) var originalRecords:[UInt32:ClawInteractionActor] = [:]
    private(set) var initialized:Set<UInt32> = []
    private(set) var bodies:[UInt32:ClawNativeBreakableEnemy] = [:]
    private(set) var fault:UInt32 = 0, unresolved:Set<UInt32> = []
    private(set) var serviceCounts:[UInt32:UInt64] = [:]
    private(set) var childCrates:Set<UInt32> = [],deletedStackParents:Set<UInt32> = []
    init(scene:ClawNativeScene) {
        self.scene = scene;globals.initialize(to:ClawBreakableGlobals());context.initialize(to:ClawBreakableContext())
        context.pointee.globals = globals
        for (token,words) in clawBreakableVTables where scene.heap.lookup(token,words:UInt32(words.count)) == nil {
            let target = scene.heap.store(token:token,words:words.count)
            words.withUnsafeBufferPointer{target.update(from:$0.baseAddress!,count:words.count)}
        }
    }
    deinit { globals.deinitialize(count:1);globals.deallocate();context.deinitialize(count:1);context.deallocate() }
    func attach(_ snapshot:ClawInteractionActor) { originalRecords[snapshot.token] = snapshot }
    func remove(_ actor:UInt32) { bodies.removeValue(forKey:actor) }
    func stackDestructor(receiver:UInt32,flags:UInt32) -> UInt32? {
        guard let scene,let actor = scene.heap.lookup(receiver &+ 12,words:1)?.pointee,
              let record = originalRecords[actor],[UInt32(0x48d560),0x48d620].contains(record.primary.4) else { return nil }
        let value = stackEntry(0x484d90,receiver:receiver,arguments:[flags])
        if flags & 1 != 0 && fault == 0 { deletedStackParents.insert(actor) };return value
    }
    private func stackEntry(_ function:UInt32,receiver:UInt32,arguments:[UInt32]) -> UInt32 {
        var stack = ClawStackedActorLifecycleContext(scene:host,fault:0),result:UInt32 = 0
        let completed = arguments.withUnsafeBufferPointer{claw_stacked_actor_lifecycle_entry(function,receiver,$0.baseAddress,UInt32($0.count),&stack,&result)}
        fault = max(fault,stack.fault);if completed != 1 { unresolved.insert(function) };return result
    }
    var host:ClawSceneActorHost {
        ClawSceneActorHost(context:Unmanaged.passUnretained(self).toOpaque(),lookup:{user,token,count in
            guard let user else { return nil };let owner = Unmanaged<ClawNativeBreakables>.fromOpaque(user).takeUnretainedValue()
            return owner.scene?.heap.lookup(token,words:count) ?? owner.scene?.stateRegistry?.rawMemory(token,words:count) ?? owner.scene?.player.audio?.ambientMetadata(token:token,words:count)
        },allocate:{user,bytes in
            guard let user else { return 0 };return Unmanaged<ClawNativeBreakables>.fromOpaque(user).takeUnretainedValue().scene?.heap.allocate(bytes:bytes) ?? 0
        },free:{user,token in
            guard let user else { return };Unmanaged<ClawNativeBreakables>.fromOpaque(user).takeUnretainedValue().scene?.heap.free(token)
        },call:{user,event in
            guard let user else { return 0 };let owner = Unmanaged<ClawNativeBreakables>.fromOpaque(user).takeUnretainedValue()
            return UInt32(truncatingIfNeeded:owner.service(event.function,receiver:event.receiver,arguments:withUnsafeBytes(of:event.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(event.argumentCount)))}))
        },readClock:{user in
            guard let user else { return 0 };let owner = Unmanaged<ClawNativeBreakables>.fromOpaque(user).takeUnretainedValue(),backing = owner.scene?.actorHost
            return backing?.readClock?(backing?.context) ?? 0
        })
    }
    private func refresh() {
        guard let scene,let loot = scene.loot else { fault = 1;return }
        context.pointee.scene = host;context.pointee.loot = loot.globals
        globals.pointee.animationDelta = scene.animationDelta;globals.pointee.audioEnabled = scene.player.audio?.managerIdentity ?? 0;globals.pointee.audioPosition = scene.player.audio?.routing.masterVolume ?? 0
        let shared = ClawNativeHumanoidGlobals.shared(scene);globals.pointee.damageScale = shared.damageScale;globals.pointee.healthScale = shared.healthScale
        if let words = scene.stateRegistry?.rawTable(0x537ea0) { withUnsafeMutableBytes(of:&globals.pointee.kegStates){raw in words.withUnsafeBytes{raw.copyMemory(from:$0)}} }
        if let words = scene.stateRegistry?.rawTable(0x537308) { withUnsafeMutableBytes(of:&globals.pointee.crateStates){raw in words.withUnsafeBytes{raw.copyMemory(from:$0)}} }
    }
    @discardableResult func callback(_ function:UInt32,actor:UInt32) -> UInt32 {
        let wasNew = scene?.snapshotActor(actor)?.primary.7 == 0
        let result = invoke(function,receiver:0,arguments:[actor])
        if wasNew && fault == 0 { initialized.insert(actor) };return result
    }
    @discardableResult func invoke(_ function:UInt32,receiver:UInt32,arguments:[UInt32]) -> UInt32 {
        guard let scene else { fault = 1;return 0 };refresh();var result:UInt32 = 0
        let status = scene.heap.withStableFreedStorage {
            arguments.withUnsafeBufferPointer{claw_breakable_entry(function,receiver,$0.baseAddress,UInt32($0.count),context,nativeBreakableDependency,Unmanaged.passUnretained(self).toOpaque(),&result)}
        }
        fault = max(fault,context.pointee.fault);if status != 1 { unresolved.insert(function) }
        for body in bodies.values where body.failure != nil || !body.unresolved.isEmpty { fault = 1;unresolved.formUnion(body.unresolved) }
        return result
    }
    private func body(_ actor:UInt32,privateToken:UInt32) -> ClawNativeBreakableEnemy? {
        if let result = bodies[actor] { result.generic.pointee.enemyToken = privateToken;return result }
        guard let scene,let resources = scene.objectResources,let snapshot = scene.snapshotActor(actor) else { fault = 1;return nil }
        do {
            let result = try ClawNativeBreakableEnemy(snapshot:snapshot,scene:scene,resources:resources,owner:self,privateToken:privateToken)
            bodies[actor] = result;return result
        } catch { fault = 1;return nil }
    }
    func service(_ function:UInt32,receiver:UInt32,arguments:[UInt32],name:String? = nil) -> UInt64 {
        guard let scene else { fault = 1;return 0 };serviceCounts[function,default:0] &+= 1
        let a = arguments.first ?? 0,label = name ?? clawOriginalResourceNames[a]
        if Self.owned.contains(function) { return UInt64(invoke(function,receiver:receiver,arguments:arguments)) }
        if function == 0x4332f0 {
            guard let body = body(a,privateToken:receiver) else { return 0 };return UInt64(body.construct())
        }
        if function == 0x4dc870 {
            guard let actor = scene.heap.lookup(a &+ 12,words:1)?.pointee,let body = body(actor,privateToken:a) else { fault = 1;return 0 }
            return UInt64(body.tick())
        }
        if function == 0x406240 || function == 0x406290 || function == 0x40f6c0 || function == 0x4209d0 || function == 0x4061b0 || function == 0x4062e0 {
            var wrapper = ClawActorWrapperContext(scene:host,fault:0),result:UInt32 = 0
            let status = arguments.withUnsafeBufferPointer{claw_actor_wrapper_entry(function,receiver,$0.baseAddress,UInt32($0.count),&wrapper,{context,event,user in
                guard let context,let event,let user else { return 0 };let owner = Unmanaged<ClawNativeBreakables>.fromOpaque(user).takeUnretainedValue()
                let token = UInt32(truncatingIfNeeded:owner.service(0x4f6286,receiver:event.pointee.receiver,arguments:[event.pointee.arguments.0]))
                event.pointee.output?.pointee = token;if owner.fault != 0 { context.pointee.fault = owner.fault };return token == 0 ? 0 : 1
            },Unmanaged.passUnretained(self).toOpaque(),&result)}
            fault = max(fault,wrapper.fault);if status != 1 { unresolved.insert(function) };return UInt64(result)
        }
        do {
            switch function {
            case 0x4f6286:
                guard let label else { fault = 1;return 0 }
                let parent = scene.heap.lookup(scene.sceneIdentity,words:12)!
                if receiver == parent[11] &+ 16 { return UInt64(try scene.objectResources?.sequence(name:label)?.token ?? 0) }
                if receiver == parent[4] &+ 16 { return UInt64(try scene.objectResources?.images(name:label)?.token ?? 0) }
                return UInt64(try scene.loot?.lookup(label) ?? 0)
            case 0x4c7970:
                guard let label else { fault = 1;return 0 };return UInt64(try scene.loot?.bindImage(receiver,name:label) ?? 0)
            case 0x4c7fa0,0x4c8060:
                guard let label else { fault = 1;return 0 }
                return UInt64(function == 0x4c7fa0 ? scene.bindSecondaryLogic(actor:receiver,name:label) : scene.bindContactLogic(actor:receiver,name:label))
            case 0x4c96b0,0x4041b0,0x4041a0,0x456030:
                return UInt64(stackEntry(function,receiver:receiver,arguments:arguments))
            case 0x4c8da0:
                guard arguments.count == 6 else { fault = 1;return 0 }
                if label == "Crate" {
                    var sourceFault:UInt32 = 0
                    let child = claw_scene_actor_create(receiver,ClawSceneActorCreate(id:a,x:arguments[1],y:arguments[2],z:arguments[3],entryToken:scene.entry(named:"Crate"),flags:arguments[5]),scene.actorHost,&sourceFault)
                    fault = max(fault,sourceFault);if child != 0 && sourceFault == 0 { childCrates.insert(child) };return UInt64(child)
                }
                fallthrough
            case 0x40e690:
                var call = ClawWorldLootCall();call.function = function;call.receiver = receiver;call.argumentCount = UInt32(arguments.count)
                withUnsafeMutableBytes(of:&call.arguments){raw in arguments.withUnsafeBytes{UnsafeMutableRawBufferPointer(rebasing:raw.prefix($0.count)).copyMemory(from:$0)}}
                return UInt64(scene.loot?.sourceService(call) ?? 0)
            case 0x4719e0:return scene.loot?.initialize() == true ? 1 : 0
            case 0x42df90:return scene.loot?.lootDrop(receiver:receiver) == true ? 1 : 0
            case 0x4c79e0:
                guard let label,arguments.count == 2 else { fault = 1;return 0 };return UInt64(scene.namedAnimation(function:function,actor:receiver,name:label,eager:arguments[1]))
            case 0x4c8220,0x4c8260,0x4c82a0:
                return UInt64(scene.actorAnimation(function:function,receiver:receiver,argument0:a,argument1:arguments.count>1 ? arguments[1] : 0))
            case 0x4cd800:
                guard var actor = scene.snapshotActor(a) else { fault = 1;return 0 };var collision = ClawCollisionActor(snapshot:actor)
                let result = scene.player.collision.placeOnGround(actor:&collision)
                actor.actor.2 = collision.flags;actor.actor.19 = collision.x;actor.actor.20 = collision.y;actor.actor.51 = collision.mode;actor.actor.32 = collision.supportToken;scene.write(actor);return UInt64(result)
            case 0x4dba00:
                guard let label,let registry = scene.stateRegistry else { fault = 1;return 0 }
                return UInt64(label.withCString{claw_logic_state_find_id(registry.registry,registry.context,$0,nil,nil)})
            case 0x4a3050:return UInt64(scene.nextRandom())
            case 0x4207a0,0x421010,0x420fc0,0x4dbd20,0x4dc6d0:
                guard let carry = scene.carry else { fault = 1;return 0 }
                let result = carry.enemyEntry(function,receiver:receiver,arguments:arguments)
                fault = max(fault,carry.fault);return UInt64(result)
            case 0x486e70:
                var projectileGlobals = ClawPlayerProjectileGlobals(),result:UInt32 = 0
                return withUnsafeMutablePointer(to:&projectileGlobals){g in
                    var pulse = ClawPlayerProjectileContext(scene:host,globals:g,bullet:nil,composeAnimation:0,fault:0)
                    let completed = arguments.withUnsafeBufferPointer{claw_player_projectile_entry(function,receiver,$0.baseAddress,UInt32($0.count),&pulse,nil,nil,&result)}
                    fault = max(fault,pulse.fault);if completed != 1 { unresolved.insert(function) };return UInt64(result)
                }
            case 0x4bb030:return 0
            case 0x4b45f0:
                guard arguments.count == 4 else { fault = 1;return 0 };return UInt64(scene.player.audio?.playVoicePool(receiver,request:ClawAudioRequest(volume:a,pan:arguments[1],pitchPercent:arguments[2],looping:arguments[3])) ?? 0)
            case 0x4208e0:return UInt64(scene.player.audio?.play(resource:receiver,volume:a) ?? 0)
            case 0x4f6428,0x4a49b0:scene.heap.free(a);return 0
            case 0x4dc560:
                var call = ClawSceneActorCall();call.function = function;call.receiver = receiver;call.argumentCount = UInt32(arguments.count)
                withUnsafeMutableBytes(of:&call.arguments){raw in arguments.withUnsafeBytes{UnsafeMutableRawBufferPointer(rebasing:raw.prefix($0.count)).copyMemory(from:$0)}}
                return UInt64(scene.actorHost.call?(scene.actorHost.context,call) ?? 0)
            case 0x47cca0,0x4dbcd0,0x4f6584:
                var result:UInt32 = 0,sourceFault:UInt32 = 0,globals = ClawActorDestructionGlobals(holderActorToken:0,heldActorToken:0,emptyStringToken:0x52e1c4)
                _ = claw_actor_destruction_entry(function,receiver,a,&globals,host,&sourceFault,&result);fault = max(fault,sourceFault);return UInt64(result)
            default:
                if let raw = scene.heap.lookup(receiver &+ 12,words:1),let body = bodies[raw.pointee] {
                    if let result = body.rawEntry(function,argument:a) { return UInt64(result) }
                }
                unresolved.insert(function);fault = 1;return 0
            }
        } catch { fault = 1;return 0 }
    }
}

final class ClawNativeBreakableEnemy:ClawHumanoidActorServices {
    weak var owner:ClawNativeBreakables?
    let human = UnsafeMutablePointer<ClawHumanEnemyContext>.allocate(capacity:1)
    let motion = UnsafeMutablePointer<ClawEnemyMotionAuxContext>.allocate(capacity:1)
    let rat = UnsafeMutablePointer<ClawRatContext>.allocate(capacity:1)
    private let tail = UnsafeMutablePointer<UInt32>.allocate(capacity:20)
    private let tiles:ClawHumanoidTiles
    let privateWords:Int
    init(snapshot:ClawInteractionActor,scene:ClawNativeScene,resources:ClawActorResources,owner:ClawNativeBreakables,privateToken:UInt32) throws {
        self.owner = owner;privateWords = owner.originalRecords[snapshot.token]?.primary.4 == 0x46f1e0 ? 260 : 262
        tiles = try ClawHumanoidTiles.load(resources.root)
        let generic = UnsafeMutablePointer<ClawGenericEnemyContext>.allocate(capacity:1),common = UnsafeMutablePointer<ClawGenericEnemyStatesContext>.allocate(capacity:1)
        generic.initialize(to:ClawGenericEnemyContext());common.initialize(to:ClawGenericEnemyStatesContext());claw_generic_enemy_context_defaults(generic)
        human.initialize(to:ClawHumanEnemyContext());motion.initialize(to:ClawEnemyMotionAuxContext());rat.initialize(to:ClawRatContext());tail.initialize(repeating:0,count:20)
        let states = ClawEnemyStateView(registry:scene.stateRegistry!,inheritance:["CEnemy",privateWords == 260 ? "PowderKeg" : "Crate"])
        super.init(snapshot:snapshot,scene:scene,resources:resources,generic:generic,common:common,states:states)
        generic.pointee.enemyToken = privateToken;generic.pointee.emptyStringToken = 0x52e1c4
        human.pointee.generic = generic;human.pointee.sharedStates = common;human.pointee.privateTail = tail
        human.pointee.sequenceRegistryToken = 0x63000010;motion.pointee.human = human;motion.pointee.world = UnsafePointer(tiles.world)
        bindNativeOwner(.breakable, service: { [weak owner] call in
            let arguments = withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
            return owner?.service(call.function,receiver:call.receiver,arguments:arguments,name:call.name.map{String(cString:$0)})
        })
        reloadPrivate();refreshVTable()
    }
    deinit {
        human.deinitialize(count:1);human.deallocate();motion.deinitialize(count:1);motion.deallocate();rat.deinitialize(count:1);rat.deallocate();tail.deinitialize(count:20);tail.deallocate()
        generic.deinitialize(count:1);generic.deallocate();common.deinitialize(count:1);common.deallocate()
    }
    private func refreshVTable() {
        let vt = state.pointee.enemy.0,words = clawBreakableVTables[vt] ?? clawBreakableVTables[0x50b16c]!
        withUnsafeMutableBytes(of:&generic.pointee.virtualFunctions){raw in raw.initializeMemory(as:UInt8.self,repeating:0);words.withUnsafeBytes{UnsafeMutableRawBufferPointer(rebasing:raw.prefix($0.count)).copyMemory(from:$0)}}
    }
    override func reloadPrivate() {
        guard let raw = scene?.heap.lookup(generic.pointee.enemyToken,words:UInt32(privateWords)) else { return }
        withUnsafeMutableBytes(of:&state.pointee.enemy){UnsafeMutableRawBufferPointer(rebasing:$0.prefix(privateWords*4)).copyMemory(from:UnsafeRawBufferPointer(start:raw,count:privateWords*4))}
        refreshVTable()
    }
    override func refresh() {
        let saved = generic.pointee.enemyToken;super.refresh();if generic.pointee.enemyToken == 0 { generic.pointee.enemyToken = saved };reloadPrivate()
        if let scene {
            let raw = withUnsafeBytes(of:state.pointee.enemy){Array($0.bindMemory(to:UInt32.self))}
            for offset in stride(from:0x38c,through:0x3c0,by:4) { if let sound = scene.player.audio?.sound(resource:raw[offset/4]) { registerAudioResource(sound) } }
            let shared = ClawNativeHumanoidGlobals.shared(scene);human.pointee.damageScale = shared.damageScale;human.pointee.healthScale = shared.healthScale;human.pointee.rangeScale = shared.rangeScale;motion.pointee.strongThrow = shared.strongThrow }
    }
    override func flush() {
        guard ownsActor else { return };super.flush()
        if let raw = scene?.heap.lookup(generic.pointee.enemyToken,words:UInt32(privateWords)) {
            withUnsafeBytes(of:&state.pointee.enemy){UnsafeMutableRawBufferPointer(start:raw,count:privateWords*4).copyMemory(from:UnsafeRawBufferPointer(rebasing:$0.prefix(privateWords*4)))}
        }
        if human.pointee.fault != 0 || motion.pointee.fault != 0 { fail("Breakable common context fault") }
    }
    func construct() -> UInt32 {
        guard ownsActor else { fail("Retired breakable owner");return 0 };refresh();let result = claw_generic_enemy_construct(state,generic,humanoidDependency,Unmanaged.passUnretained(self).toOpaque());flush()
        if result != 1 { fail("Breakable generic construction failed") };return result == 1 ? generic.pointee.enemyToken : 0
    }
    func tick() -> UInt32 {
        guard ownsActor else { fail("Retired breakable owner");return 0 };refresh();let result = claw_generic_enemy_tick(state,generic,humanoidDependency,Unmanaged.passUnretained(self).toOpaque());flush()
        if result != 1 { fail("Breakable FSM failed") };return result
    }
    func rawEntry(_ function:UInt32,argument:UInt32) -> UInt32? { guard ownsActor else { fail("Retired breakable owner");return nil };refresh();let result = entry(function,argument:argument);flush();return result }
    override func entry(_ function:UInt32,argument:UInt32) -> UInt32? {
        let user = Unmanaged.passUnretained(self).toOpaque();var result:UInt32 = 0
        if ClawNativeBreakables.owned.contains(function) {
            flush();let arguments:[UInt32] = [0x46f6a0,0x433ad0,0x46fc90,0x433f70,0x46f5b0,0x4339e0].contains(function) ? [argument] : []
            result = owner?.invoke(function,receiver:generic.pointee.enemyToken,arguments:arguments) ?? 0
            if let snapshot = scene?.snapshotActor(token) { accept(snapshot) };reloadPrivate();return result
        }
        if function == 0x405000 {
            rat.pointee.generic = generic.pointee
            if claw_rat_entry(state,rat,function,argument,humanoidDependency,user,&result) == 1 { generic.pointee = rat.pointee.generic;return result }
        }
        if claw_common_enemy_entry(state,human,function,argument,humanoidDependency,user,&result) == 1 { return result }
        if claw_enemy_motion_aux_entry(state,motion,function,argument,humanoidDependency,user,&result) == 1 { return result }
        if claw_native_generic_enemy_state_entry(state,generic,common,function,argument,humanoidDependency,user) == 1 { return 0 }
        if claw_generic_enemy_entry(state,generic,function,argument,humanoidDependency,user) == 1 { return 0 }
        return nil
    }
}
private let nativeBreakableDependency:ClawBreakableDependency = {_,event,user in
    guard let event,let user else { return 0 };let owner = Unmanaged<ClawNativeBreakables>.fromOpaque(user).takeUnretainedValue(),call = event.pointee
    return owner.service(call.function,receiver:call.receiver,arguments:withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))},name:call.name.map{String(cString:$0)})
}

extension ClawNativeBreakableEnemy {
    struct SavedState: Codable, Equatable {
        let service: ServiceSavedState, privateWords: Int
        let human: [String: Data], motion: [String: Data], rat: [String: Data], ratGeneric: [String: Data]
        let tail: [UInt32]
    }
    func savedState() throws -> SavedState {
        guard nativeOwnerBinding == .breakable, human.pointee.effectActor == nil,
              human.pointee.effectPrimary == nil, human.pointee.effectPrivate == nil,
              rat.pointee.generic.bitWords == nil, rat.pointee.generic.bitWordCount == 0 else { throw ClawSnapshotError.invalidState }
        return .init(service: try savedServiceState(), privateWords: privateWords,
            human: ClawNativeHumanoid.humanFields.capture(human.pointee), motion: ClawNativeHumanoid.motionFields.capture(motion.pointee),
            rat: ClawNativeEnemy.ratFields.capture(rat.pointee), ratGeneric: ClawEnemySnapshotFields.generic.capture(rat.pointee.generic),
            tail: Array(UnsafeBufferPointer(start: tail, count: 20)))
    }
    static func restoring(_ saved: SavedState, owner: ClawNativeBreakables, heap plan: ClawTokenHeap.RestorePlan) throws -> ClawNativeBreakableEnemy {
        guard let scene = owner.scene, let resources = scene.objectResources, saved.tail.count == 20 else { throw ClawSnapshotError.invalidState }
        let actor = savedActor(saved.service)
        let result = try ClawNativeBreakableEnemy(snapshot: actor, scene: scene, resources: resources, owner: owner, privateToken: actor.primary.6)
        guard result.privateWords == saved.privateWords else { throw ClawSnapshotError.invalidState }
        result.human.pointee = try ClawNativeHumanoid.humanFields.restoring(saved.human, into: result.human.pointee)
        result.motion.pointee = try ClawNativeHumanoid.motionFields.restoring(saved.motion, into: result.motion.pointee)
        result.rat.pointee = try ClawNativeEnemy.ratFields.restoring(saved.rat, into: result.rat.pointee)
        // Rat's embedded generic is a borrowed mirror of this body's generic.
        // Rebuild its pointer fields from the candidate before scalar import.
        result.rat.pointee.generic = result.generic.pointee
        result.rat.pointee.generic = try ClawEnemySnapshotFields.generic.restoring(saved.ratGeneric, into: result.rat.pointee.generic)
        saved.tail.withUnsafeBufferPointer { result.tail.update(from: $0.baseAddress!, count: 20) }
        try result.restoreServiceState(saved.service, heap: plan)
        return result
    }
}
extension ClawNativeBreakables {
    struct SavedState: Codable, Equatable {
        let globals: ClawSnapshotValue<ClawBreakableGlobals>, records: [UInt32: ClawSnapshotValue<ClawInteractionActor>]
        let initialized: Set<UInt32>, children: Set<UInt32>, deleted: Set<UInt32>
        let fault: UInt32, contextFault: UInt32, unresolved: Set<UInt32>, calls: [UInt32: UInt64]
        let bodies: [ClawNativeBreakableEnemy.SavedState]
    }
    func savedState() throws -> SavedState {
        .init(globals: ClawSnapshotValue(globals.pointee), records: originalRecords.mapValues(ClawSnapshotValue.init),
            initialized: initialized, children: childCrates, deleted: deletedStackParents, fault: fault, contextFault: context.pointee.fault,
            unresolved: unresolved, calls: serviceCounts, bodies: try bodies.keys.sorted().map { try bodies[$0]!.savedState() })
    }
    func prepareRestore(_ saved: SavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws -> Void {
        guard let scene, Set(saved.bodies.map { $0.service.token }).count == saved.bodies.count else { throw ClawSnapshotError.invalidState }
        try scene.heap.validateRestore(plan)
        // Constructors select Crate/PowderKeg from the saved original record.
        let previous = originalRecords; originalRecords = saved.records.mapValues(\.value)
        defer { originalRecords = previous }
        let bodies = try Dictionary(uniqueKeysWithValues: saved.bodies.map { ($0.service.token, try ClawNativeBreakableEnemy.restoring($0, owner: self, heap: plan)) })
        return { [self] in
            try scene.heap.validateInstalledRestore(plan)
            globals.pointee = saved.globals.value; originalRecords = saved.records.mapValues(\.value)
            initialized = saved.initialized; childCrates = saved.children; deletedStackParents = saved.deleted
            fault = saved.fault; context.pointee.fault = saved.contextFault; unresolved = saved.unresolved; serviceCounts = saved.calls; self.bodies = bodies
            context.pointee.scene = host; context.pointee.loot = scene.loot?.globals
        }
    }
}
