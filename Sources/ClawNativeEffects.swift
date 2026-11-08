import Foundation

// Original Points/Glitter callbacks operate directly on the live scene heap.
// Root owns callback installation and invokes remove after its scene destructor.
final class ClawNativeEffects {
    struct Event: Codable, Equatable { let function:UInt32,receiver:UInt32,arguments:[UInt32],name:String? }
    static let callbacks:Set<UInt32> = [0x473a70,0x448440,0x4485a0,0x470110,0x461a90,0x461bc0]
    weak var scene:ClawNativeScene?
    let resources:ClawActorResources
    private(set) var actors:[UInt32:ClawNativeEffect] = [:]
    private(set) var failure:String?
    private(set) var fault:UInt32 = 0
    private(set) var unresolved:Set<UInt32> = []
    private(set) var events:[Event] = []
    private(set) var allocations:[(token:UInt32,bytes:UInt32)] = []
    private(set) var freed:[UInt32] = []
    var onCreated:((ClawNativeEffect)->Void)?,onRemoved:((UInt32)->Void)?
    var externalService:((Event)->UInt32?)?
    var allocationAllowed:((UInt32)->Bool)? // Explicit failure injection/host boundary.
    var frameClock:(()->(animationDelta:UInt32,audioPosition:UInt32))?
    var managerToken:UInt32
    private var pending:Set<UInt32> = []
    private let points = UnsafeMutablePointer<ClawPickupPointsContext>.allocate(capacity:1)
    private let glitter = UnsafeMutablePointer<ClawGlitterContext>.allocate(capacity:1)
    private let destruction = UnsafeMutablePointer<ClawActorDestructionGlobals>.allocate(capacity:1)
    private let impact = UnsafeMutablePointer<ClawImpactParticleContext>.allocate(capacity:1)

    init(scene:ClawNativeScene,resources:ClawActorResources,managerToken:UInt32? = nil) {
        self.scene = scene;self.resources = resources
        self.managerToken = managerToken ?? scene.heap.lookup(scene.ownerIdentity,words:2)?[1] ?? 0
        points.initialize(to:ClawPickupPointsContext());glitter.initialize(to:ClawGlitterContext())
        impact.initialize(to:ClawImpactParticleContext())
        destruction.initialize(to:ClawActorDestructionGlobals(holderActorToken:0,heldActorToken:0,emptyStringToken:0x52e1c4))
        refresh()
    }
    deinit {
        points.deinitialize(count:1);points.deallocate();glitter.deinitialize(count:1);glitter.deallocate()
        destruction.deinitialize(count:1);destruction.deallocate()
        impact.deinitialize(count:1);impact.deallocate()
    }
    func resetDiagnostic() { failure = nil;fault = 0;points.pointee.fault = 0;glitter.pointee.fault = 0;impact.pointee.fault = 0 }
    private func fail(_ message:String,_ code:UInt32 = 1) { if failure == nil { failure = message };fault = code }
    func refresh() {
        let clock = frameClock?() ?? (animationDelta:scene?.animationDelta ?? 0,audioPosition:scene?.player.audio?.routing.masterVolume ?? 0)
        points.pointee.scene = host;points.pointee.animationDelta = clock.animationDelta;points.pointee.audioPosition = clock.audioPosition
        points.pointee.composeCreation = 1;points.pointee.composeAnimation = 1;points.pointee.pointsEntryToken = 0
        glitter.pointee.scene = host;glitter.pointee.managerToken = managerToken;glitter.pointee.animationDelta = clock.animationDelta;glitter.pointee.audioPosition = clock.audioPosition
        glitter.pointee.composeCreation = 1;glitter.pointee.composeAnimation = 1
        impact.pointee.scene = host;impact.pointee.animation = ClawActorAnimationGlobals(animationDelta:clock.animationDelta,audioPosition:clock.audioPosition)
        impact.pointee.composeCreation = 1;impact.pointee.composeAnimation = 1
    }
    func flush() {} // C bodies commit the original stores directly; no stale cache.
    @discardableResult func attach(token:UInt32) -> ClawNativeEffect? {
        if let existing = actors[token] { return existing }
        guard let snapshot = scene?.snapshotActor(token),Self.callbacks.contains(snapshot.primary.4) else { return nil }
        let actor = ClawNativeEffect(token:token,effects:self);actors[token] = actor;pending.remove(token)
        onCreated?(actor);return actor
    }
    func remove(_ token:UInt32) {
        pending.remove(token)
        if actors.removeValue(forKey:token) != nil { onRemoved?(token) }
    }
    // Creator sets actor+68 only after list insertion. Discover on the next
    // heap access: immediate Baby initialization's first body read sees a
    // registered child. The snapshot is read through the backing heap directly.
    private func discover() {
        guard let scene else { return }
        for token in Array(pending) {
            guard let raw = scene.heap.lookup(token,words:128),raw[26] != 0,
                  let node = scene.heap.lookup(raw[26],words:3),node[2] == token else { continue }
            _ = attach(token:token)
        }
    }
    @discardableResult func points(item:UInt32) -> Bool {
        guard let scene else { fail("Effects scene lifetime ended");return false };refresh();points.pointee.fault = 0
        var argument = item,result:UInt32 = 0
        let covered = scene.heap.withStableFreedStorage {
            claw_pickup_points_entry(0x4737c0,0,&argument,1,points,nativePointsHostDependency,Unmanaged.passUnretained(self).toOpaque(),&result)
        }
        discover();if points.pointee.fault != 0 { fail("Points source fault \(points.pointee.fault)",points.pointee.fault) }
        return covered == 1 && fault == 0
    }
    func itemService(_ call:ClawItemPickupCall) -> UInt32? {
        if call.function == 0x4737c0 && call.argumentCount == 1 { return points(item:call.arguments.0) ? 1 : 0 }
        if call.function == 0x4c8da0 && call.argumentCount == 6 { return create(receiver:call.receiver,arguments:words(call.arguments,count:call.argumentCount)) }
        return nil
    }
    func service(_ call:ClawPlayerPowerupCall) -> UInt32? {
        guard call.function == 0x4c8da0 && call.argumentCount == 6 else { return nil }
        return create(receiver:call.receiver,arguments:words(call.arguments,count:call.argumentCount))
    }
    @discardableResult func impactEntry(_ function:UInt32,arguments:[UInt32]) -> UInt32 {
        guard let scene else { fail("Impact scene lifetime ended");return 0 }
        refresh();impact.pointee.fault = 0;var result:UInt32 = 0
        let covered = scene.heap.withStableFreedStorage {
            arguments.withUnsafeBufferPointer {
                claw_impact_particle_entry(function,0,$0.baseAddress,UInt32($0.count),impact,nativeImpactHostDependency,Unmanaged.passUnretained(self).toOpaque(),&result)
            }
        }
        discover()
        if covered != 1 || impact.pointee.fault != 0 { fail("Impact source fault \(impact.pointee.fault)",impact.pointee.fault == 0 ? 1 : impact.pointee.fault) }
        return result
    }
    // Direct448400 wrapper for callers that have not entered its frozen body.
    // Setter's rich4c8da0 service must call service above, avoiding recursion.
    @discardableResult func mother(owner:UInt32) -> UInt32 {
        guard scene != nil else { fail("Effects scene lifetime ended");return 0 };refresh()
        var globals = ClawPlayerPowerupGlobals();globals.managerToken = managerToken
        var result:UInt32 = 0,argument = owner
        let supported = withUnsafeMutablePointer(to:&globals) { g in
            var context = ClawPlayerPowerupRuntimeContext(scene:host,globals:g,fault:0)
            let supported = claw_player_powerup_entry(0x448400,0,&argument,1,&context,{context,event,user in
                guard let event,let user else { return 0 }
                let effects = Unmanaged<ClawNativeEffects>.fromOpaque(user).takeUnretainedValue()
                guard let result = effects.service(event.pointee) else { context?.pointee.fault = 1;return 0 };return result
            },Unmanaged.passUnretained(self).toOpaque(),&result)
            if context.fault != 0 { fail("Mother wrapper fault \(context.fault)",context.fault) };return supported
        }
        return supported == 1 && fault == 0 ? result : 0
    }
    @discardableResult func callback(_ token:UInt32,function:UInt32) -> UInt32 {
        guard actors[token]?.ownsActor != false else { return 0 };guard let scene,Self.callbacks.contains(function) else { unresolved.insert(function);return 0 }
        if function == 0x461a90 || function == 0x461bc0 { _ = attach(token:token);return impactEntry(function,arguments:[token]) }
        _ = attach(token:token);refresh();var argument = token,result:UInt32 = 0
        let status = scene.heap.withStableFreedStorage {
            if function == 0x473a70 {
                points.pointee.fault = 0
                return claw_pickup_points_entry(function,0,&argument,1,points,nativePointsHostDependency,Unmanaged.passUnretained(self).toOpaque(),&result)
            }
            glitter.pointee.fault = 0
            return claw_glitter_entry(function,0,&argument,1,glitter,nativeGlitterHostDependency,Unmanaged.passUnretained(self).toOpaque(),&result)
        }
        let sourceFault = function == 0x473a70 ? points.pointee.fault : glitter.pointee.fault
        if status == 0 || sourceFault != 0 { fail("Effect callback \(String(function,radix:16)) fault \(sourceFault)",sourceFault == 0 ? 1 : sourceFault) }
        discover();return status == 1 && sourceFault == 0 ? result : 0
    }
    func receiverLifecycle(_ call:ClawSceneActorCall) -> UInt32? {
        guard call.function == 0x4c9be0,actors[call.receiver]?.ownsActor == true,let scene else { return nil }
        var result:UInt32 = 0,sourceFault:UInt32 = 0
        _ = scene.heap.withStableFreedStorage {
            claw_actor_destruction_entry(call.function,call.receiver,call.arguments.0,destruction,host,&sourceFault,&result)
        }
        if sourceFault != 0 { fail("Effect destructor fault \(sourceFault)",sourceFault) }
        return result
    }
    private func create(receiver:UInt32,arguments:[UInt32]) -> UInt32? {
        guard arguments.count == 6,Self.names[arguments[4]].map({["PointsIcon","GlitterMother","GlitterBaby","PowerupGlitter"].contains($0)}) == true else { return nil }
        guard let scene else { fail("Effects scene lifetime ended");return 0 }
        events.append(Event(function:0x4c8da0,receiver:receiver,arguments:arguments,name:Self.names[arguments[4]]))
        var sourceFault:UInt32 = 0
        let token = scene.heap.withStableFreedStorage {
            claw_scene_actor_create_named(receiver,ClawSceneActorCreate(id:arguments[0],x:arguments[1],y:arguments[2],z:arguments[3],entryToken:0,flags:arguments[5]),arguments[4],host,&sourceFault)
        }
        discover();if sourceFault != 0 { fail("Effect scene creation fault \(sourceFault)",sourceFault) };return token
    }
    private func words<T>(_ tuple:T,count:UInt32) -> [UInt32] {
        withUnsafeBytes(of:tuple) { Array($0.bindMemory(to:UInt32.self).prefix(Int(count))) }
    }
    var actorHost:ClawSceneActorHost { host }
    private var host:ClawSceneActorHost {
        ClawSceneActorHost(context:Unmanaged.passUnretained(self).toOpaque(),lookup:{user,token,count in
            guard let user else { return nil };let effects = Unmanaged<ClawNativeEffects>.fromOpaque(user).takeUnretainedValue();effects.discover();return effects.scene?.heap.lookup(token,words:count)
        },allocate:{user,bytes in
            guard let user else { return 0 };return Unmanaged<ClawNativeEffects>.fromOpaque(user).takeUnretainedValue().allocate(bytes)
        },free:{user,token in
            guard let user else { return };let effects = Unmanaged<ClawNativeEffects>.fromOpaque(user).takeUnretainedValue();effects.freed.append(token);effects.remove(token);effects.scene?.heap.free(token)
        },call:{user,call in
            guard let user else { return 0 };let effects = Unmanaged<ClawNativeEffects>.fromOpaque(user).takeUnretainedValue()
            let args = effects.words(call.arguments,count:call.argumentCount)
            return effects.dependency(Event(function:call.function,receiver:call.receiver,arguments:args,name:args.first.flatMap{ClawNativeEffects.names[$0]}))
        },readClock:{user in
            guard let user else { return 0 };let effects = Unmanaged<ClawNativeEffects>.fromOpaque(user).takeUnretainedValue();let backing = effects.scene?.actorHost;return backing?.readClock?(backing?.context) ?? 0
        })
    }
    private func allocate(_ bytes:UInt32) -> UInt32 {
        let token = allocationAllowed?(bytes) == false ? 0 : scene?.heap.allocate(bytes:bytes) ?? 0
        allocations.append((token,bytes));if bytes == 0x1b4 && token != 0 { pending.insert(token) };return token
    }
    fileprivate func dependency(_ event:Event) -> UInt32 {
        events.append(event);discover();guard let scene else { fail("Effects scene lifetime ended");return 0 }
        do {
            switch event.function {
            case 0x4f6286:
                guard let literal = event.arguments.first,let name = event.name ?? Self.names[literal] else { fail("Unresolved effects literal");return 0 }
                if ["PointsIcon","GlitterMother","GlitterBaby","PowerupGlitter","HitBurst","Splash"].contains(name) { return scene.entry(named:name) }
                if ["GAME_SMLHITBURST","GAME_MEDHITBURST","GAME_BIGHITBURST","GAME_SPLASH"].contains(name) { return try resources.sequence(name:name)?.token ?? 0 }
                if name == "GAME_POINTS" {
                    let parent = scene.heap.lookup(scene.sceneIdentity,words:12)
                    let registry = (parent?[4] ?? 0) &+ 16
                    return event.receiver == registry ? try resources.images(name:name)?.token ?? 0 : try resources.sequence(name:name)?.token ?? 0
                }
                if name == "GAME_GLITTER1" || name == "GAME_CYCLE100" { return try resources.sequence(name:name)?.token ?? 0 }
                return try resources.images(name:name)?.token ?? 0
            case 0x4c9be0:
                var call = ClawSceneActorCall();call.function = event.function;call.receiver = event.receiver;call.argumentCount = UInt32(event.arguments.count);call.arguments.0 = event.arguments.first ?? 0
                return receiverLifecycle(call) ?? 0
            case 0x4c7970:
                guard let name = event.name ?? event.arguments.first.flatMap({Self.names[$0]}) else { fail("Unresolved impact image literal");return 0 }
                return try scene.loot?.bindImage(event.receiver,name:name) ?? 0
            case 0x4a3050:return scene.nextRandom()
            case 0x4c88e0:return scene.player.audio?.playSpatial(resource:event.receiver,sourceX:event.arguments[0]) ?? 0
            case 0x4208e0:return scene.player.audio?.play(resource:event.receiver,volume:event.arguments[0]) ?? 0
            case 0x473a70,0x448440,0x4485a0,0x470110:return callback(event.arguments[0],function:event.function)
            default:
                if let result = externalService?(event) { return result }
                unresolved.insert(event.function);fail("Unimplemented effects service \(String(event.function,radix:16))");return 0
            }
        } catch { fail(String(describing:error));return 0 }
    }
    static let names:[UInt32:String] = [0x522874:"PointsIcon",0x52a6c0:"GAME_POINTS",0x5225a0:"GlitterMother",0x522594:"GlitterBaby",0x522950:"PowerupGlitter",0x527a50:"GAME_SPARKLE",0x527a40:"GAME_GLITTER1",0x52a1a8:"GAME_GLITTER",0x5240d8:"GAME_CYCLE100",0x522570:"HitBurst",0x522568:"Splash",0x5294dc:"GAME_ENEMYHIT",0x5294ec:"GAME_CLAWHIT",0x5294fc:"GAME_SMLHITBURST",0x529510:"GAME_BIGHITBURST",0x529524:"GAME_MEDHITBURST",0x5266ec:"GAME_SPLASH",0x529538:"LEVEL_SPLASH"]
}
final class ClawNativeEffect {
    let token:UInt32
    weak var effects:ClawNativeEffects?
    private var actorIdentity: ClawTokenHeap.AllocationIdentity?
    init(token:UInt32,effects:ClawNativeEffects) { self.token = token;self.effects = effects;actorIdentity = effects.scene?.heap.containingAllocationIdentity(at: token, count: 4) }
    var ownsActor: Bool { guard let heap = effects?.scene?.heap, let actorIdentity else { return false };return heap.containingAllocationIdentity(at: token, count: 4) === actorIdentity }
    struct SavedState: Codable, Equatable { let token: UInt32, actor: ClawSnapshotWitness }
    func savedState() throws -> SavedState {
        guard let heap = effects?.scene?.heap, let actorIdentity else { throw ClawSnapshotError.invalidState }
        return .init(token: token, actor: ClawSnapshotWitness(heap: heap, token: token, count: 4, identity: actorIdentity, interior: true))
    }
    static func restoring(_ saved: SavedState, owner: ClawNativeEffects, heap plan: ClawTokenHeap.RestorePlan) throws -> ClawNativeEffect {
        guard saved.actor.reference.token == saved.token, saved.actor.reference.count == 4, saved.actor.reference.interior else { throw ClawSnapshotError.invalidState }
        let result = ClawNativeEffect(token: saved.token, effects: owner)
        result.actorIdentity = try saved.actor.resolve(in: plan)
        return result
    }
    func snapshot() -> ClawInteractionActor? { ownsActor ? effects?.scene?.snapshotActor(token) : nil }
    func refresh() { effects?.refresh() }
    func flush() {} // Live raw stores already committed.
    func tick() { guard let snapshot = snapshot() else { return };_ = callback(snapshot.primary.4) }
    @discardableResult func callback(_ function:UInt32) -> UInt32 { ownsActor ? (effects?.callback(token,function:function) ?? 0) : 0 }
}
private let nativePointsHostDependency:ClawPickupPointsDependency = {_,event,user in
    guard let event,let user else { return 0 };let effects = Unmanaged<ClawNativeEffects>.fromOpaque(user).takeUnretainedValue()
    let call = event.pointee;let arguments = withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
    return effects.dependency(ClawNativeEffects.Event(function:call.function,receiver:call.receiver,arguments:arguments,name:call.name.map{String(cString:$0)}))
}
private let nativeGlitterHostDependency:ClawGlitterDependency = {_,event,user in
    guard let event,let user else { return 0 };let effects = Unmanaged<ClawNativeEffects>.fromOpaque(user).takeUnretainedValue()
    let call = event.pointee;let arguments = withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
    return effects.dependency(ClawNativeEffects.Event(function:call.function,receiver:call.receiver,arguments:arguments,name:call.name.map{String(cString:$0)}))
}
private let nativeImpactHostDependency:ClawImpactParticleDependency = {_,event,user in
    guard let event,let user else { return 0 };let effects = Unmanaged<ClawNativeEffects>.fromOpaque(user).takeUnretainedValue()
    let call = event.pointee;let arguments = withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
    return effects.dependency(ClawNativeEffects.Event(function:call.function,receiver:call.receiver,arguments:arguments,name:call.name.map{String(cString:$0)}))
}

extension ClawNativeEffects {
    struct SavedState: Codable, Equatable {
        struct Allocation: Codable, Equatable { let token: UInt32, bytes: UInt32 }
        let actors: [ClawNativeEffect.SavedState], pending: Set<UInt32>, manager: UInt32
        let points: [String: Data], glitter: [String: Data], impact: [String: Data]
        let destruction: ClawSnapshotValue<ClawActorDestructionGlobals>
        let failure: String?, fault: UInt32, unresolved: Set<UInt32>, events: [Event]
        let allocations: [Allocation], freed: [UInt32]
    }
    func savedState() throws -> SavedState {
        guard allocationAllowed == nil, frameClock == nil, onCreated == nil, onRemoved == nil else { throw ClawSnapshotError.invalidState }
        return .init(actors: try actors.keys.sorted().map { try actors[$0]!.savedState() }, pending: pending, manager: managerToken,
            points: Self.pointsFields.capture(points.pointee), glitter: Self.glitterFields.capture(glitter.pointee), impact: Self.impactFields.capture(impact.pointee),
            destruction: ClawSnapshotValue(destruction.pointee), failure: failure, fault: fault, unresolved: unresolved, events: events,
            allocations: allocations.map { .init(token: $0.token, bytes: $0.bytes) }, freed: freed)
    }
    func prepareRestore(_ saved: SavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws -> Void {
        guard let scene, Set(saved.actors.map(\.token)).count == saved.actors.count else { throw ClawSnapshotError.invalidState }
        try scene.heap.validateRestore(plan)
        let points = try Self.pointsFields.restoring(saved.points, into: self.points.pointee)
        let glitter = try Self.glitterFields.restoring(saved.glitter, into: self.glitter.pointee)
        let impact = try Self.impactFields.restoring(saved.impact, into: self.impact.pointee)
        let actors = try Dictionary(uniqueKeysWithValues: saved.actors.map { ($0.token, try ClawNativeEffect.restoring($0, owner: self, heap: plan)) })
        return { [self] in
            try scene.heap.validateInstalledRestore(plan)
            self.actors = actors; pending = saved.pending; managerToken = saved.manager
            self.points.pointee = points; self.glitter.pointee = glitter; self.impact.pointee = impact; destruction.pointee = saved.destruction.value
            failure = saved.failure; fault = saved.fault; unresolved = saved.unresolved; events = saved.events
            allocations = saved.allocations.map { ($0.token, $0.bytes) }; freed = saved.freed
        }
    }
    private static let pointsFields = ClawSnapshotFields<ClawPickupPointsContext>(fields: [
        .init("animationDelta", \.animationDelta),
        .init("audioPosition", \.audioPosition),
        .init("composeCreation", \.composeCreation),
        .init("composeAnimation", \.composeAnimation),
        .init("pointsEntryToken", \.pointsEntryToken),
        .init("fault", \.fault)
    ])
    private static let glitterFields = ClawSnapshotFields<ClawGlitterContext>(fields: [
        .init("managerToken", \.managerToken),
        .init("animationDelta", \.animationDelta),
        .init("audioPosition", \.audioPosition),
        .init("composeCreation", \.composeCreation),
        .init("composeAnimation", \.composeAnimation),
        .init("fault", \.fault)
    ])
    private static let impactFields = ClawSnapshotFields<ClawImpactParticleContext>(fields: [
        .init("animation", \.animation),
        .init("composeCreation", \.composeCreation),
        .init("composeAnimation", \.composeAnimation),
        .init("fault", \.fault)
    ])
}
