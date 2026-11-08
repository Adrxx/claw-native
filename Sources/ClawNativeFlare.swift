import Foundation

// Source dynamic Flare/LFX lifetime. Parent projectiles control placement and
// deletion; palette/raster transport remains explicit until level palette boot.
final class ClawNativeFlare {
    unowned let scene:ClawNativeScene
    private let context = UnsafeMutablePointer<ClawFlareContext>.allocate(capacity:1)
    private let animation = UnsafeMutablePointer<ClawActorAnimationGlobals>.allocate(capacity:1)
    private(set) var tokens:Set<UInt32> = [],initialized:Set<UInt32> = []
    private(set) var privateOwners:[UInt32:UInt32] = [:]
    private(set) var fault:UInt32 = 0,unresolved:Set<UInt32> = []
    private(set) var missingSpans:Set<String> = []
    private(set) var failure:String?
    static let callbacks:Set<UInt32> = [0x457f00,0x458010]
    init(scene:ClawNativeScene) {
        self.scene = scene
        animation.initialize(to:ClawActorAnimationGlobals())
        context.initialize(to:ClawFlareContext());claw_flare_defaults(context)
        context.pointee.scene = host;context.pointee.animation = animation
        context.pointee.images = scene.rendering!.sourceImageGlobals
        let methods:[UInt32] = [0x484d90,0x4c9e30,0x458280,0x4041b0,0x4581c0,0x4bb030,0x4bb030,0x4c96b0,0x4c96b0]
        for t:UInt32 in [0x50e6fc,0x50e724] where scene.heap.lookup(t,words:9) == nil {
            let p = scene.heap.store(token:t,words:9);methods.withUnsafeBufferPointer{p.update(from:$0.baseAddress!,count:9)}
        }
        let registry = scene.stateRegistry!
        _ = registry.resolve(Int32(registry.registry.pointee.nextId-1),table:0x537ac0)
        _ = registry.resolve(1000,table:0x537ac0)
        if let words = registry.rawTable(0x537ac0) {
            let p = scene.heap.lookup(0x537ac0,words:10) ?? scene.heap.store(token:0x537ac0,words:10)
            words.withUnsafeBufferPointer{p.update(from:$0.baseAddress!,count:10)}
        } else { fault = 1 }
        let app = scene.heap.lookup(scene.ownerIdentity,words:2)![1]
        let appAlias = scene.heap.lookup(0x5371fc,words:1) ?? scene.heap.store(token:0x5371fc,words:1)
        appAlias.pointee = app
        if scene.heap.lookup(0x5430c4,words:1) == nil { _ = scene.heap.store(token:0x5430c4,words:1) }
    }
    deinit { context.deinitialize(count:1);context.deallocate();animation.deinitialize(count:1);animation.deallocate() }
    private var host:ClawSceneActorHost {
        ClawSceneActorHost(context:Unmanaged.passUnretained(self).toOpaque(),lookup:{u,t,n in
            guard let u else { return nil };let p = Unmanaged<ClawNativeFlare>.fromOpaque(u).takeUnretainedValue()
            let span = p.scene.heap.lookup(t,words:n) ?? p.scene.stateRegistry?.rawMemory(t,words:n)
            if span == nil { p.missingSpans.insert(String(t,radix:16)+"/"+String(n)) };return span
        },allocate:{u,n in
            guard let u else { return 0 };return Unmanaged<ClawNativeFlare>.fromOpaque(u).takeUnretainedValue().scene.heap.allocate(bytes:n)
        },free:{u,t in
            guard let u else { return };let p = Unmanaged<ClawNativeFlare>.fromOpaque(u).takeUnretainedValue();p.privateOwners.removeValue(forKey:t);p.scene.heap.free(t)
        },call:{u,e in
            guard let u else { return 0 };let p = Unmanaged<ClawNativeFlare>.fromOpaque(u).takeUnretainedValue()
            let args = withUnsafeBytes(of:e.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(e.argumentCount)))}
            return UInt32(truncatingIfNeeded:p.dependency(e.function,receiver:e.receiver,args:args,name:args.first.flatMap{[UInt32(0x522e24):"Flare",0x522e14:"WolvingtonLFX"][$0] ?? clawOriginalResourceNames[$0]}))
        },readClock:{u in
            guard let u else { return 0 };let p = Unmanaged<ClawNativeFlare>.fromOpaque(u).takeUnretainedValue(),h = p.scene.actorHost
            return h.readClock?(h.context) ?? 0
        })
    }
    @discardableResult func create(_ name:String,x:UInt32,y:UInt32,z:UInt32,flags:UInt32,id:UInt32) -> UInt32 {
        guard let meta = name.withCString({claw_logic_registry_find($0)}),Self.callbacks.contains(meta.pointee.callback) else { fault = 1;return 0 }
        var error:UInt32 = 0
        let t = claw_scene_actor_create_named(scene.containerToken,ClawSceneActorCreate(id:id,x:x,y:y,z:z,entryToken:0,flags:flags),meta.pointee.originalNameAddress,host,&error)
        fault = max(fault,error);if t != 0 { tokens.insert(t) };return t
    }
    @discardableResult func entry(_ f:UInt32,receiver:UInt32 = 0,args:[UInt32]) -> UInt32 {
        animation.pointee.animationDelta = scene.animationDelta;animation.pointee.audioPosition = scene.player.audio?.routing.masterVolume ?? 0
        scene.heap.lookup(0x5430c4,words:1)!.pointee = scene.animationDelta
        var result:UInt32 = 0
        let recognized = scene.heap.withStableFreedStorage {
            args.withUnsafeBufferPointer { claw_flare_entry(f,receiver,$0.baseAddress,UInt32(args.count),context,nativeFlareDependency,Unmanaged.passUnretained(self).toOpaque(),&result) }
        }
        if context.pointee.fault != 0 { failure = "entry "+String(f,radix:16)+"/"+String(receiver,radix:16)+" fault "+String(context.pointee.fault) };fault = max(fault,context.pointee.fault);if recognized != 1 { fault = 1;unresolved.insert(f) };return result
    }
    func callback(_ f:UInt32,actor:UInt32) {
        let wasNew = scene.snapshotActor(actor)?.primary.7 == 0
        _ = entry(f,args:[actor])
        if let p = scene.snapshotActor(actor)?.primary.6,p != 0 { privateOwners[p] = actor }
        if wasNew && fault == 0 { initialized.insert(actor) }
    }
    func remove(_ t:UInt32) { tokens.remove(t);privateOwners = privateOwners.filter{$0.value != t} }
    func contact(_ f:UInt32,actor:UInt32) {
        guard let source = scene.snapshotActor(actor),let raw = scene.heap.lookup(source.primary.6,words:19),let vt = scene.heap.lookup(raw[0],words:9) else { fault = 1;failure = "contact missing private/VT "+String(actor,radix:16);return }
        var s = ClawGenericEnemy(),g = ClawGenericEnemyContext(),common = ClawGenericEnemyStatesContext()
        s.actor = source.actor;s.primary = source.primary;s.secondary = source.secondary;s.contact = source.contact
        withUnsafeMutableBytes(of:&s.enemy){UnsafeMutableRawBufferPointer(rebasing:$0.prefix(76)).copyMemory(from:UnsafeRawBufferPointer(start:raw,count:76))}
        g.actorToken = actor;g.enemyToken = source.primary.6
        withUnsafeMutableBytes(of:&g.virtualFunctions){UnsafeMutableRawBufferPointer(rebasing:$0.prefix(36)).copyMemory(from:UnsafeRawBufferPointer(start:vt,count:36))}
        let done = claw_native_generic_enemy_state_entry(&s,&g,&common,f,0,{_,_,e,u in
            guard let e,let u else { return 0 };let p = Unmanaged<ClawNativeFlare>.fromOpaque(u).takeUnretainedValue()
            let args = withUnsafeBytes(of:e.pointee.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(e.pointee.argumentCount)))}
            return UInt64(p.entry(e.pointee.function,receiver:e.pointee.receiver,args:args))
        },Unmanaged.passUnretained(self).toOpaque())
        if done != 1 { fault = 1;unresolved.insert(f) }
    }
    fileprivate func dependency(_ f:UInt32,receiver:UInt32,args:[UInt32],name:String?) -> UInt64 {
        let a = args.first ?? 0,label = name ?? clawOriginalResourceNames[a]
        do {
            switch f {
            case 0x4c7970:
                guard let label else { fault = 1;return 0 };return UInt64(try scene.loot?.bindImage(receiver,name:label) ?? 0)
            case 0x4f6286:
                guard let label else { fault = 1;return 0 }
                if label.withCString({claw_logic_registry_find($0)}) != nil { return UInt64(scene.entry(named:label)) }
                return UInt64(try scene.objectResources?.sequence(name:label)?.token ?? 0)
            case 0x4c7fa0,0x4c8060:
                guard let label else { fault = 1;return 0 }
                return UInt64(f == 0x4c7fa0 ? scene.bindSecondaryLogic(actor:receiver,name:label) : scene.bindContactLogic(actor:receiver,name:label))
            case 0x4dba00:
                guard let label,let r = scene.stateRegistry else { fault = 1;return 0 }
                return UInt64(label.withCString{claw_logic_state_find_id(r.registry,r.context,$0,nil,nil)})
            case 0x4f6974:
                // Exact no-copy GetBuffer branch elected by the live bootstrap
                // name CStrings. Shared/undersized buffers diagnose missing
                // transport rather than guessing the allocation branch.
                guard let cell = scene.stateRegistry?.rawMemory(receiver,words:1),let header = scene.stateRegistry?.rawMemory(cell.pointee-12,words:3),
                    Int32(bitPattern:header[0]) <= 1,Int32(bitPattern:header[2]) >= Int32(bitPattern:a) else { fault = 1;unresolved.insert(f);return 0 }
                return UInt64(cell.pointee)
            case 0x4c88e0:return UInt64(scene.player.audio?.playSpatial(resource:receiver,sourceX:a) ?? 0)
            case 0x4208e0:return UInt64(scene.player.audio?.play(resource:receiver,volume:a) ?? 0)
            default:unresolved.insert(f);fault = 1;return 0
            }
        } catch { fault = 1;failure = String(describing:error);return 0 }
    }
}
private let nativeFlareDependency:ClawFlareDependency = {_,e,u in
    guard let e,let u else { return 0 };let p = Unmanaged<ClawNativeFlare>.fromOpaque(u).takeUnretainedValue()
    let args = withUnsafeBytes(of:e.pointee.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(e.pointee.argumentCount)))}
    return p.dependency(e.pointee.function,receiver:e.pointee.receiver,args:args,name:e.pointee.name.map{String(cString:$0)})
}

extension ClawNativeFlare {
    struct SavedState: Codable, Equatable {
        let tokens: Set<UInt32>, initialized: Set<UInt32>, privateOwners: [UInt32: UInt32]
        let context: [String: Data], animation: ClawSnapshotValue<ClawActorAnimationGlobals>
        let fault: UInt32, unresolved: Set<UInt32>, missing: Set<String>, failure: String?
    }
    func savedState() -> SavedState {
        .init(tokens: tokens, initialized: initialized, privateOwners: privateOwners, context: Self.snapshotFields.capture(context.pointee),
            animation: ClawSnapshotValue(animation.pointee), fault: fault, unresolved: unresolved, missing: missingSpans, failure: failure)
    }
    func restoreState(_ saved: SavedState) throws {
        let cx = try Self.snapshotFields.restoring(saved.context, into: context.pointee)
        tokens = saved.tokens; initialized = saved.initialized; privateOwners = saved.privateOwners
        context.pointee = cx; animation.pointee = saved.animation.value
        fault = saved.fault; unresolved = saved.unresolved; missingSpans = saved.missing; failure = saved.failure
    }
    private static let snapshotFields = ClawSnapshotFields<ClawFlareContext>(fields: [
        .init("composeAnimation", \.composeAnimation),
        .init("composeFSM", \.composeFSM),
        .init("composeEffects", \.composeEffects),
        .init("maximumSteps", \.maximumSteps),
        .init("fault", \.fault)
    ])
}

extension ClawActorAnimationGlobals: ClawSnapshotNativeValue {}
