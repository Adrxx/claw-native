import Foundation

// Actual deferred source creation and raw Pistol/Magic/Dynamite controllers.
// Source launch fields are committed after41c5a0, before the scheduler can
// initialize the new actor. Physical/resource transport stays in the scene.
final class ClawNativeProjectiles {
    unowned let scene:ClawNativeScene
    private let generic = UnsafeMutablePointer<ClawGenericEnemyContext>.allocate(capacity:1)
    private let bullet = UnsafeMutablePointer<ClawBulletContext>.allocate(capacity:1)
    private let globals = UnsafeMutablePointer<ClawPlayerProjectileGlobals>.allocate(capacity:1)
    private let context = UnsafeMutablePointer<ClawPlayerProjectileContext>.allocate(capacity:1)
    private let states:ClawEnemyStateView
    private(set) var tokens:Set<UInt32> = [],initialized:Set<UInt32> = []
    private(set) var privateOwners:[UInt32:UInt32] = [:]
    private(set) var fault:UInt32 = 0,unresolved:Set<UInt32> = []
    private(set) var callbackCounts:[UInt32:UInt64] = [:]
    private(set) var creationArguments:[UInt32:[UInt32]] = [:]
    private(set) var emitCounts:[UInt32:UInt64] = [:]
    private var launchBorrow:UInt32 = 0
    static let elementalCallbacks:Set<UInt32> = [0x410100,0x4101c0,0x410280]
    static let elementalFunctions:Set<UInt32> = [0x410100,0x4101c0,0x410280,0x410ec0,0x411370,0x411820,0x411030,0x4114e0,0x411990,0x411310,0x4117c0,0x411c70,0x411cd0]
    static let callbacks:Set<UInt32> = elementalCallbacks.union([0x40ff80,0x410040,0x43a850])
    static let names:[UInt32:String] = [0x522dc8:"PistolBullet",0x522e00:"MagicBullet",0x522bec:"Dynamite",0x522df4:"FireBullet",0x522de4:"LightningBullet",0x522dd8:"IceBullet",0x522e24:"Flare",0x522594:"GlitterBaby"]
    init(scene:ClawNativeScene) {
        self.scene = scene
        let registry = scene.stateRegistry!
        states = ClawEnemyStateView(registry:registry,inheritance:["Projectile"])
        generic.initialize(to:ClawGenericEnemyContext());claw_generic_enemy_context_defaults(generic)
        generic.pointee.states = UnsafePointer(states.entries);generic.pointee.stateCount = states.count
        generic.pointee.emptyStringToken = states.entries[0].nameToken
        bullet.initialize(to:ClawBulletContext());bullet.pointee.generic = generic
        bullet.pointee.projectileStates = UnsafePointer(states.entries);bullet.pointee.projectileStateCount = states.count
        claw_bullet_context_defaults(bullet)
        globals.initialize(to:ClawPlayerProjectileGlobals())
        globals.pointee.ownerToken = scene.heap.lookup(scene.ownerIdentity,words:2)![1]
        context.initialize(to:ClawPlayerProjectileContext(scene:host,globals:globals,bullet:bullet,composeAnimation:1,fault:0))
        for (t,words) in clawPlayerProjectileVTables where scene.heap.lookup(t,words:UInt32(words.count)) == nil {
            let p = scene.heap.store(token:t,words:words.count);words.withUnsafeBufferPointer{p.update(from:$0.baseAddress!,count:words.count)}
        }
        for vt:UInt32 in [0x50b7bc,0x50b80c,0x50b844] where scene.heap.lookup(vt,words:12) == nil {
            let p = scene.heap.store(token:vt,words:12)
            for i:UInt32 in 0..<12 { p[Int(i)] = claw_elemental_projectile_function(vt,i*4) }
        }
        for (t,value):(UInt32,Double) in [(0x50b7f0,0),(0x50b7f8,-20),(0x50b800,20)] where scene.heap.lookup(t,words:2) == nil {
            let p = scene.heap.store(token:t,words:2),bits = value.bitPattern;p[0] = UInt32(truncatingIfNeeded:bits);p[1] = UInt32(truncatingIfNeeded:bits>>32)
        }
        let top = Int32(registry.registry.pointee.nextId-1)
        for table:UInt32 in [0x538428,0x534ab0,0x534910,0x5375d8,0x534ba0,0x534a38,0x534b00] { _ = registry.resolve(top,table:table);_ = registry.resolve(1000,table:table) }
        for table:UInt32 in [0x537698,0x538428,0x534ab0,0x534910,0x5375d8,0x534ba0,0x534a38,0x534b00] {
            guard let words = registry.rawTable(table) else { fault = 1;continue }
            // The shared CString state-name table has nine source words;
            // cannon adapters may already own its exact span.
            let count = table == 0x537698 ? 9 : 10
            let p = scene.heap.lookup(table,words:UInt32(count)) ?? scene.heap.store(token:table,words:count)
            words.withUnsafeBufferPointer{p.update(from:$0.baseAddress!,count:count)}
        }
    }
    deinit {
        context.deinitialize(count:1);context.deallocate();globals.deinitialize(count:1);globals.deallocate()
        bullet.deinitialize(count:1);bullet.deallocate();generic.deinitialize(count:1);generic.deallocate()
    }
    private var host:ClawSceneActorHost {
        ClawSceneActorHost(context:Unmanaged.passUnretained(self).toOpaque(),lookup:{u,t,n in
            guard let u else { return nil };let p = Unmanaged<ClawNativeProjectiles>.fromOpaque(u).takeUnretainedValue()
            return p.scene.heap.lookup(t,words:n) ?? p.scene.stateRegistry?.rawMemory(t,words:n) ?? p.scene.player.audio?.ambientMetadata(token:t,words:n)
        },allocate:{u,n in
            guard let u else { return 0 };return Unmanaged<ClawNativeProjectiles>.fromOpaque(u).takeUnretainedValue().scene.heap.allocate(bytes:n)
        },free:{u,t in
            guard let u else { return };let p = Unmanaged<ClawNativeProjectiles>.fromOpaque(u).takeUnretainedValue();p.privateOwners.removeValue(forKey:t);p.scene.heap.free(t)
        },call:{u,e in
            guard let u else { return 0 };let p = Unmanaged<ClawNativeProjectiles>.fromOpaque(u).takeUnretainedValue()
            let args = withUnsafeBytes(of:e.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(e.argumentCount)))}
            return UInt32(truncatingIfNeeded:p.dependency(e.function,receiver:e.receiver,args:args,name:args.first.flatMap{ClawNativeProjectiles.names[$0] ?? clawOriginalResourceNames[$0]}))
        },readClock:{u in
            guard let u else { return 0 };let p = Unmanaged<ClawNativeProjectiles>.fromOpaque(u).takeUnretainedValue(),h = p.scene.actorHost
            return h.readClock?(h.context) ?? 0
        })
    }
    @discardableResult func entry(_ f:UInt32,receiver:UInt32 = 0,args:[UInt32]) -> UInt32 {
        globals.pointee.tick = scene.gameTime;globals.pointee.animationDelta = scene.animationDelta
        globals.pointee.audioEnabled = scene.player.audio?.managerIdentity ?? 0;globals.pointee.masterVolume = scene.player.audio?.routing.masterVolume ?? 0
        var result:UInt32 = 0
        let ownerActor = privateOwners[receiver] ?? (f == 0x4dc870 ? args.first.flatMap{privateOwners[$0]} : nil)
        let elemental = Self.elementalFunctions.contains(f) || ownerActor.flatMap{scene.snapshotActor($0)?.primary.4}.map{Self.elementalCallbacks.contains($0)} == true
        let accepted = scene.heap.withStableFreedStorage {
            if elemental {
                let arguments = f == 0x4dc870 && receiver != 0 && args.isEmpty ? [receiver] : args
                let target:UInt32 = f == 0x4dc870 ? 0 : receiver
                return arguments.withUnsafeBufferPointer { claw_elemental_projectile_entry(f,target,$0.baseAddress,UInt32(arguments.count),context,nativeProjectileDependency,Unmanaged.passUnretained(self).toOpaque(),&result) }
            }
            return args.withUnsafeBufferPointer { claw_player_projectile_entry(f,receiver,$0.baseAddress,UInt32(args.count),context,nativeProjectileDependency,Unmanaged.passUnretained(self).toOpaque(),&result) }
        }
        fault = max(fault,context.pointee.fault);if accepted != 1 { unresolved.insert(f);fault = max(fault,1) }
        return result
    }
    func callback(_ f:UInt32,actor:UInt32) {
        let wasNew = scene.snapshotActor(actor)?.primary.7 == 0
        _ = entry(f,args:[actor]);callbackCounts[actor,default:0] &+= 1
        if let p = scene.snapshotActor(actor)?.primary.6,p != 0 { privateOwners[p] = actor }
        if wasNew && fault == 0 { initialized.insert(actor) }
    }
    func remove(_ t:UInt32) { tokens.remove(t);privateOwners = privateOwners.filter{$0.value != t} }
    //Borrow the suspended portable player, publish its current raw spans and
    //import source writes before returning to the original duck/attack caller.
    //Resource callbacks never reenter the player's Swift runtime cache.
    func emit(_ f:UInt32,state:UnsafeMutablePointer<ClawPlayerLocomotion>) -> UInt32 {
        guard let actor = scene.heap.lookup(0x10002000,words:128),
            let primary = scene.heap.lookup(state.pointee.actor.27,words:93),
            let priv = scene.heap.lookup(primary[5],words:78),let liveGlobals = scene.playerPowerupGlobals else { fault = 1;return 0 }
        withUnsafeBytes(of:&state.pointee.actor){UnsafeMutableRawPointer(actor).copyMemory(from:$0.baseAddress!,byteCount:512)}
        withUnsafeBytes(of:&state.pointee.privateWords){UnsafeMutableRawPointer(priv).copyMemory(from:$0.baseAddress!,byteCount:312)}
        primary[7] = state.pointee.logicState;liveGlobals.pointee.powerup = state.pointee.powerup
        var g = ClawPlayerRangedHelpersGlobals(powerup:liveGlobals.pointee.powerup,masterVolume:scene.player.audio?.routing.masterVolume ?? 0)
        var result:UInt32 = 0
        let args:[UInt32] = [0x10002000,state.pointee.actor.27,primary[5]]
        let done = withUnsafeMutablePointer(to:&g){ globals in
            var c = ClawPlayerRangedHelpersContext(scene:host,globals:globals,composeCreation:0,composeImages:1,fault:0)
            let complete = scene.heap.withStableFreedStorage { args.withUnsafeBufferPointer {
                claw_player_ranged_helpers_entry(f,$0.baseAddress,UInt32($0.count),&c,{cx,event,u in
                    guard let cx,let event,let u else { return 0 };let p = Unmanaged<ClawNativeProjectiles>.fromOpaque(u).takeUnretainedValue()
                    let args = withUnsafeBytes(of:event.pointee.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(event.pointee.argumentCount)))}
                    let value = p.dependency(event.pointee.function,receiver:event.pointee.receiver,args:args,name:event.pointee.name.map{String(cString:$0)})
                    cx.pointee.globals.pointee.powerup = p.scene.playerPowerupGlobals!.pointee.powerup
                    cx.pointee.globals.pointee.masterVolume = p.scene.player.audio?.routing.masterVolume ?? 0
                    if p.fault != 0 { cx.pointee.fault = p.fault };return value
                },Unmanaged.passUnretained(self).toOpaque(),&result)
            } }
            fault = max(fault,c.fault);return complete
        }
        withUnsafeMutableBytes(of:&state.pointee.actor){$0.copyMemory(from:UnsafeRawBufferPointer(start:actor,count:512))}
        withUnsafeMutableBytes(of:&state.pointee.privateWords){$0.copyMemory(from:UnsafeRawBufferPointer(start:priv,count:312))}
        state.pointee.logicState = primary[7];state.pointee.powerup = g.powerup
        emitCounts[f,default:0] &+= 1
        if done != 1 { fault = max(fault,1);unresolved.insert(f) };return result
    }
    @discardableResult func create(_ name:String,x:UInt32,y:UInt32,z:UInt32,flags:UInt32,id:UInt32 = 0) -> UInt32 {
        guard let meta = name.withCString({claw_logic_registry_find($0)}),Self.callbacks.contains(meta.pointee.callback) else { fault = 1;return 0 }
        var error:UInt32 = 0
        let t = claw_scene_actor_create_named(scene.containerToken,ClawSceneActorCreate(id:id,x:x,y:y,z:z,entryToken:0,flags:flags),meta.pointee.originalNameAddress,host,&error)
        fault = max(fault,error)
        if t != 0 { tokens.insert(t);creationArguments[t] = [id,x,y,z,meta.pointee.originalNameAddress,flags] }
        return t
    }
    func beginPlayerLaunch(_ state:UnsafeMutablePointer<ClawPlayerLocomotion>,name:UInt32,x:UInt32,y:UInt32) -> UInt32 {
        let a = scene.player.attack
        guard let label = Self.names[name] else { fault = 1;return 0 }
        let t = create(label,x:x,y:y,z:a.pointee.spawnZ,flags:a.pointee.spawnFlags)
        guard t != 0,let actor = scene.heap.lookup(t,words:128) else { fault = max(fault,1);return 0 }
        a.pointee.projectileToken = t
        withUnsafeMutableBytes(of:&a.pointee.projectileActor){$0.copyMemory(from:UnsafeRawBufferPointer(start:actor,count:512))}
        a.pointee.projectileLogicRepeat = scene.heap.lookup(actor[27],words:93)![0xb8/4]
        launchBorrow = t;return t
    }
    func commitPlayerLaunch(clear:Bool = true) {
        guard launchBorrow != 0,let actor = scene.heap.lookup(launchBorrow,words:128) else { return }
        let a = scene.player.attack
        withUnsafeBytes(of:&a.pointee.projectileActor){UnsafeMutableRawPointer(actor).copyMemory(from:$0.baseAddress!,byteCount:512)}
        scene.heap.lookup(actor[27],words:93)![0xb8/4] = a.pointee.projectileLogicRepeat
        if clear { launchBorrow = 0 }
    }
    func bindLaunchImage(actor:UInt32,literal:UInt32) -> UInt32 {
        guard actor == launchBorrow,let name = clawOriginalResourceNames[literal] else { fault = 1;return 0 }
        commitPlayerLaunch(clear:false)
        do {
            let result = try scene.loot?.bindImage(actor,name:name) ?? 0
            guard let p = scene.heap.lookup(actor,words:128) else { fault = 1;return 0 }
            withUnsafeMutableBytes(of:&scene.player.attack.pointee.projectileActor){$0.copyMemory(from:UnsafeRawBufferPointer(start:p,count:512))}
            return result
        } catch { fault = 1;return 0 }
    }
    func contact(_ f:UInt32,actor:UInt32) {
        guard let source = scene.snapshotActor(actor),let raw = scene.heap.lookup(source.primary.6,words:1) else { fault = 1;return }
        var s = ClawGenericEnemy();s.actor = source.actor;s.primary = source.primary;s.secondary = source.secondary;s.contact = source.contact
        let ordinary = claw_player_projectile_private_bytes(source.primary.4)
        let bytes = ordinary != 0 ? ordinary : claw_elemental_projectile_private_bytes(source.primary.4),n = bytes/4
        guard let p = scene.heap.lookup(source.primary.6,words:n),let vt = scene.heap.lookup(raw.pointee,words:12) else { fault = 1;return }
        withUnsafeMutableBytes(of:&s.enemy){UnsafeMutableRawBufferPointer(rebasing:$0.prefix(Int(bytes))).copyMemory(from:UnsafeRawBufferPointer(start:p,count:Int(bytes)))}
        generic.pointee.actorToken = actor;generic.pointee.primaryToken = source.actor.27;generic.pointee.enemyToken = source.primary.6
        withUnsafeMutableBytes(of:&generic.pointee.virtualFunctions){UnsafeMutableRawBufferPointer(rebasing:$0.prefix(48)).copyMemory(from:UnsafeRawBufferPointer(start:vt,count:48))}
        var common = ClawGenericEnemyStatesContext()
        let done = claw_native_generic_enemy_state_entry(&s,generic,&common,f,0,{_,_,e,u in
            guard let e,let u else { return 0 };let p = Unmanaged<ClawNativeProjectiles>.fromOpaque(u).takeUnretainedValue()
            let args = withUnsafeBytes(of:e.pointee.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(e.pointee.argumentCount)))}
            return UInt64(p.entry(e.pointee.function,receiver:e.pointee.receiver,args:args))
        },Unmanaged.passUnretained(self).toOpaque())
        if done != 1 { fault = 1;unresolved.insert(f) }
    }
    fileprivate func dependency(_ f:UInt32,receiver:UInt32,args:[UInt32],name:String?) -> UInt64 {
        let a = args.first ?? 0,label = name ?? Self.names[a] ?? clawOriginalResourceNames[a]
        do {
            switch f {
            case 0x4f63ec:return UInt64(scene.heap.allocate(bytes:a))
            case 0x4f6428:scene.heap.free(a);return 0
            case 0x4f6286:
                guard let label else { fault = 1;return 0 }
                if label.withCString({claw_logic_registry_find($0)}) != nil { return UInt64(scene.entry(named:label)) }
                let parent = scene.heap.lookup(scene.sceneIdentity,words:12)!
                if receiver == parent[11]+16 { return UInt64(try scene.objectResources?.sequence(name:label)?.token ?? 0) }
                if receiver == parent[4]+16 { return UInt64(try scene.objectResources?.images(name:label)?.token ?? 0) }
                return UInt64(scene.player.audio?.resolve(name:label)?.resourceToken ?? 0)
            case 0x4c7fa0,0x4c8060:
                guard let label else { fault = 1;return 0 }
                return UInt64(f == 0x4c7fa0 ? scene.bindSecondaryLogic(actor:receiver,name:label) : scene.bindContactLogic(actor:receiver,name:label))
            case 0x4dba00:
                guard let label,let registry = scene.stateRegistry else { fault = 1;return 0 }
                return UInt64(label.withCString{claw_logic_state_find_id(registry.registry,registry.context,$0,nil,nil)})
            case 0x4cbb60:
                guard args.count == 4,var actor = scene.snapshotActor(a) else { fault = 1;return 0 }
                var collision = ClawCollisionActor(snapshot:actor)
                let value = scene.player.collision.move(actor:&collision,x:args[1],y:args[2],options:args[3],otherActors:scene.collisionActors(excluding:a))
                actor.actor.2 = collision.flags;actor.actor.19 = collision.x;actor.actor.20 = collision.y;actor.actor.51 = collision.mode
                actor.actor.32 = collision.supportToken;actor.actor.86 = collision.deltaX;actor.actor.87 = collision.deltaY
                scene.write(actor);return UInt64(value)
            case 0x4c8da0:
                guard args.count == 6,let label else { fault = 1;return 0 }
                if ["PistolBullet","MagicBullet","Dynamite","FireBullet","LightningBullet","IceBullet"].contains(label) {
                    return UInt64(create(label,x:args[1],y:args[2],z:args[3],flags:args[5],id:a))
                }
                if label == "GlitterBaby",let effects = scene.effects {
                    var call = ClawPlayerPowerupCall();call.function = f;call.receiver = receiver;call.argumentCount = 6
                    withUnsafeMutableBytes(of:&call.arguments){raw in args.withUnsafeBytes{raw.copyMemory(from:$0)}}
                    let value = effects.service(call) ?? 0;if effects.fault != 0 { fault = effects.fault };return UInt64(value)
                }
                if label == "Flare",let flare = scene.flares {
                    let value = flare.create(label,x:args[1],y:args[2],z:args[3],flags:args[5],id:a)
                    if flare.fault != 0 { fault = flare.fault;unresolved.formUnion(flare.unresolved) };return UInt64(value)
                }
                unresolved.insert(f);fault = 1;return 0
            case 0x4485a0:
                let value = scene.effects?.callback(a,function:f) ?? 0;if let effects = scene.effects,effects.fault != 0 { fault = effects.fault };return UInt64(value)
            case 0x4061b0:
                guard let label else { fault = 1;return 0 };return UInt64(scene.player.audio?.resolve(name:label)?.resourceToken ?? 0)
            case 0x4a3050:return UInt64(scene.nextRandom())
            case 0x4208e0:return UInt64(scene.player.audio?.play(resource:receiver,volume:a) ?? 0)
            case 0x4c8220,0x4c82a0,0x420970:
                return UInt64(scene.actorAnimation(function:f,receiver:receiver,argument0:a,argument1:0))
            case 0x4b45f0:
                return UInt64(scene.player.audio?.playVoicePool(receiver,request:ClawAudioRequest(volume:a,pan:args[1],pitchPercent:args[2],looping:args[3])) ?? 0)
            case 0x4bb030,0x4c9e30:return 0
            default:unresolved.insert(f);fault = 1;return 0
            }
        } catch { fault = 1;return 0 }
    }
}
private let nativeProjectileDependency:ClawPlayerProjectileDependency = {_,e,u in
    guard let e,let u else { return 0 };let p = Unmanaged<ClawNativeProjectiles>.fromOpaque(u).takeUnretainedValue()
    let args = withUnsafeBytes(of:e.pointee.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(e.pointee.argumentCount)))}
    return p.dependency(e.pointee.function,receiver:e.pointee.receiver,args:args,name:e.pointee.name.map{String(cString:$0)})
}

extension ClawNativeProjectiles {
    struct SavedState: Codable, Equatable {
        let tokens: Set<UInt32>, initialized: Set<UInt32>, privateOwners: [UInt32: UInt32]
        let globals: ClawSnapshotValue<ClawPlayerProjectileGlobals>
        let generic: [String: Data], bullet: [String: Data], context: [String: Data], states: ClawEnemyStateView.SavedState
        let fault: UInt32, unresolved: Set<UInt32>, callbacks: [UInt32: UInt64], arguments: [UInt32: [UInt32]], emits: [UInt32: UInt64]
    }
    func savedState() throws -> SavedState {
        guard launchBorrow == 0, bullet.pointee.imageFrames == nil, bullet.pointee.imageFrameCount == 0,
              generic.pointee.bitWords == nil, generic.pointee.bitWordCount == 0 else { throw ClawSnapshotError.activeFrame }
        return .init(tokens: tokens, initialized: initialized, privateOwners: privateOwners, globals: ClawSnapshotValue(globals.pointee),
            generic: ClawEnemySnapshotFields.generic.capture(generic.pointee), bullet: Self.bulletFields.capture(bullet.pointee),
            context: Self.contextFields.capture(context.pointee), states: states.savedState(), fault: fault, unresolved: unresolved,
            callbacks: callbackCounts, arguments: creationArguments, emits: emitCounts)
    }
    func restoreState(_ saved: SavedState) throws {
        guard launchBorrow == 0 else { throw ClawSnapshotError.activeFrame }
        let cx = try Self.contextFields.restoring(saved.context, into: context.pointee)
        let bx = try Self.bulletFields.restoring(saved.bullet, into: bullet.pointee)
        let gx = try ClawEnemySnapshotFields.generic.restoring(saved.generic, into: generic.pointee)
        try states.restoreState(saved.states)
        tokens = saved.tokens; initialized = saved.initialized; privateOwners = saved.privateOwners; globals.pointee = saved.globals.value
        context.pointee = cx; bullet.pointee = bx; generic.pointee = gx
        fault = saved.fault; unresolved = saved.unresolved; callbackCounts = saved.callbacks; creationArguments = saved.arguments; emitCounts = saved.emits
    }
    private static let contextFields = ClawSnapshotFields<ClawPlayerProjectileContext>(fields: [
        .init("composeAnimation", \.composeAnimation),
        .init("fault", \.fault)
    ])
    private static let bulletFields = ClawSnapshotFields<ClawBulletContext>(fields: [
        .init("imageRegistryToken", \.imageRegistryToken),
        .init("imageRootToken", \.imageRootToken),
        .init("imageRootHeader", \.imageRootHeader),
        .init("imageFrameOrigin", \.imageFrameOrigin),
        .init("imageLeafToken", \.imageLeafToken),
        .init("imageLeafHeader", \.imageLeafHeader),
        .init("fault", \.fault)
    ])
}
extension ClawPlayerProjectileGlobals: ClawSnapshotNativeValue {}
