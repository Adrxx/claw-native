import Foundation

// Source lift/carry/throw bodies share the live scene heap. The suspended
// player's model is borrowed only for exchange; rich calls never re-enter its
// Swift runtime property. Physics and the attack selector retain C storage.
final class ClawNativeCarry {
    unowned let scene:ClawNativeScene
    let globals = UnsafeMutablePointer<ClawLiftThrowGlobals>.allocate(capacity:1)
    private let lift = UnsafeMutablePointer<ClawLiftThrowContext>.allocate(capacity:1)
    private let scratch = UnsafeMutablePointer<ClawPlayerLocomotion>.allocate(capacity:1)
    private(set) var fault:UInt32 = 0,unresolved:Set<UInt32> = []
    private(set) var entries:[UInt32:UInt64] = [:]
    private var active = false
    init(scene:ClawNativeScene) {
        self.scene = scene;globals.initialize(to:ClawLiftThrowGlobals());claw_lift_throw_defaults(globals)
        lift.initialize(to:ClawLiftThrowContext());scratch.initialize(to:ClawPlayerLocomotion())
    }
    deinit {
        globals.deinitialize(count:1);globals.deallocate();lift.deinitialize(count:1);lift.deallocate()
        scratch.deinitialize(count:1);scratch.deallocate()
    }
    private func prepare(_ state:UnsafeMutablePointer<ClawPlayerLocomotion>) {
        guard let input = scene.camera?.inputToken,let component = scene.breakables else { fault = 1;return }
        globals.pointee.playerToken = 0x10002000;globals.pointee.inputToken = input
        globals.pointee.stageDelta = state.pointee.stageDelta;globals.pointee.animationDelta = state.pointee.animationDelta
        globals.pointee.tick = scene.gameTime;globals.pointee.powerup = state.pointee.powerup;globals.pointee.pixelScratch = state.pointee.pixelScratch
        globals.pointee.audioEnabled = scene.player.audio?.managerIdentity ?? 0;globals.pointee.masterVolume = scene.player.audio?.routing.masterVolume ?? 0
        globals.pointee.strongThrow = ClawNativeHumanoidGlobals.shared(scene).strongThrow
        lift.pointee.scene = component.host;lift.pointee.globals = globals;lift.pointee.attack = scene.player.attack
        lift.pointee.enemyWordCount = 260;lift.pointee.composeAnimation = 1;lift.pointee.core = scene.coreGlobals;lift.pointee.fault = 0
        let raw = scene.heap.lookup(input,words:4)!
        raw[2] = state.pointee.inputHeld;raw[3] = state.pointee.inputLatched
    }
    private func exchange(_ state:UnsafeMutablePointer<ClawPlayerLocomotion>,output:Bool) {
        let actor = scene.heap.lookup(0x10002000,words:128)!,primary = scene.heap.lookup(state.pointee.actor.27,words:93)!,priv = scene.heap.lookup(primary[5],words:78)!
        if output {
            withUnsafeBytes(of:&state.pointee.actor){UnsafeMutableRawPointer(actor).copyMemory(from:$0.baseAddress!,byteCount:512)}
            withUnsafeBytes(of:&state.pointee.privateWords){UnsafeMutableRawPointer(priv).copyMemory(from:$0.baseAddress!,byteCount:312)}
            primary[7] = state.pointee.logicState
            if let physics = lift.pointee.playerPhysics { physics.pointee = state.pointee.physics }
            globals.pointee.powerup = state.pointee.powerup;globals.pointee.pixelScratch = state.pointee.pixelScratch
            scene.heap.lookup(globals.pointee.inputToken,words:4)![3] = state.pointee.inputLatched
        } else {
            withUnsafeMutableBytes(of:&state.pointee.actor){$0.copyMemory(from:UnsafeRawBufferPointer(start:actor,count:512))}
            withUnsafeMutableBytes(of:&state.pointee.privateWords){$0.copyMemory(from:UnsafeRawBufferPointer(start:priv,count:312))}
            state.pointee.logicState = primary[7]
            state.pointee.physics = lift.pointee.playerPhysics!.pointee
            state.pointee.stageDelta = globals.pointee.stageDelta;state.pointee.animationDelta = globals.pointee.animationDelta
            state.pointee.powerup = globals.pointee.powerup;state.pointee.pixelScratch = globals.pointee.pixelScratch
            let input = scene.heap.lookup(globals.pointee.inputToken,words:4)!
            state.pointee.inputHeld = input[2];state.pointee.inputLatched = input[3]
            if priv[75] != 0,let held = scene.snapshotActor(priv[75]),let e = scene.heap.lookup(held.primary.6,words:193) {
                state.pointee.weaponLogicStatus = Int32(bitPattern:e[8]);state.pointee.weaponLogicCallback = e[5]
                state.pointee.weaponDeleteCount = e[0x2fc/4]
                let flags = state.pointee.weaponDeleteCount < 33 ? e.advanced(by:0x300/4) : scene.heap.lookup(e[0x300/4],words:1)
                state.pointee.weaponDeleteFlags = flags?.pointee ?? 0
            }
        }
    }
    func call(_ state:UnsafeMutablePointer<ClawPlayerLocomotion>,entry:UInt32,a:UInt32,b:UInt32,c:UInt32) -> UInt32? {
        guard [UInt32(0x41dc50),0x41c4e0,0x421010,0x420fc0,0x4dbd20].contains(entry) else { return nil }
        if active {
            // Damage/powerup cleanup can call back while the original carry
            // dispatcher owns physics. Reuse that borrow and raw source graph.
            guard lift.pointee.playerPhysics != nil else { fault = 1;return 0 }
            exchange(state,output:true)
            let primary = state.pointee.actor.27,priv = scene.heap.lookup(primary,words:6)![5]
            var receiver:UInt32 = 0,args:[UInt32] = [0x10002000,primary,priv],result:UInt32 = 0
            if entry == 0x41dc50 { args.append(a) }
            else if entry != 0x41c4e0 {
                guard let target = scene.snapshotActor(a) else { fault = 1;return 0 }
                receiver = target.primary.6 &+ (entry == 0x421010 ? 0 : 0x2f4)
                args = entry == 0x421010 ? [b,c] : [b]
            }
            let completed = args.withUnsafeBufferPointer{claw_lift_throw_entry(entry,receiver,$0.baseAddress,UInt32($0.count),lift,nativeCarryLiftDependency,Unmanaged.passUnretained(self).toOpaque(),&result)}
            fault = max(fault,lift.pointee.fault);if completed != 1 { unresolved.insert(entry) }
            exchange(state,output:false);return result
        }
        prepare(state);guard fault == 0 else { return 0 };active = true;defer{active = false}
        var physics = state.pointee.physics,result:UInt32 = 0
        withUnsafeMutablePointer(to:&physics){ borrowed in
            lift.pointee.playerPhysics = borrowed;exchange(state,output:true)
            let primary = state.pointee.actor.27,priv = scene.heap.lookup(primary,words:6)![5]
            var receiver:UInt32 = 0,args:[UInt32] = [0x10002000,primary,priv]
            if entry == 0x41dc50 { args.append(a) }
            else if entry == 0x421010 || entry == 0x420fc0 || entry == 0x4dbd20 {
                guard let target = scene.snapshotActor(a) else { fault = 1;return }
                receiver = target.primary.6 &+ (entry == 0x421010 ? 0 : 0x2f4)
                args = entry == 0x421010 ? [b,c] : [b]
            }
            entries[entry,default:0] &+= 1
            let completed = scene.heap.withStableFreedStorage{args.withUnsafeBufferPointer{claw_lift_throw_entry(entry,receiver,$0.baseAddress,UInt32($0.count),lift,nativeCarryLiftDependency,Unmanaged.passUnretained(self).toOpaque(),&result)}}
            fault = max(fault,lift.pointee.fault);if completed != 1 { unresolved.insert(entry) }
            exchange(state,output:false);lift.pointee.playerPhysics = nil
        }
        return result
    }
    func dispatch(_ state:UnsafeMutablePointer<ClawPlayerLocomotion>,input:UnsafeMutablePointer<ClawPlayerInputContext>) -> UInt32 {
        prepare(state);guard fault == 0 else { return 1 };active = true;defer{active = false}
        var physics = state.pointee.physics,result:UInt32 = 0
        withUnsafeMutablePointer(to:&physics){ borrowed in
            lift.pointee.playerPhysics = borrowed
            let primary = state.pointee.actor.27,priv = scene.heap.lookup(primary,words:6)![5]
            var context = ClawPlayerCarryDispatchContext(lift:lift,actorToken:0x10002000,primaryToken:primary,privateToken:priv,ignoreHazards:input.pointee.ignoreHazards,cheat:input.pointee.cheat,fault:0)
            entries[state.pointee.logicState,default:0] &+= 1
            result = scene.heap.withStableFreedStorage{claw_player_dispatch_carry(state,input,&context,nativeCarryLiftDependency,nativeCarryTailDependency,Unmanaged.passUnretained(self).toOpaque())}
            fault = max(fault,context.fault);lift.pointee.playerPhysics = nil
        }
        return result
    }
    func enemyEntry(_ entry:UInt32,receiver:UInt32,arguments:[UInt32]) -> UInt32 {
        var rawGlobals = ClawLiftThrowGlobals(),result:UInt32 = 0
        claw_lift_throw_defaults(&rawGlobals);rawGlobals.animationDelta = scene.animationDelta
        rawGlobals.stageDelta = scene.stageDelta;rawGlobals.tick = scene.gameTime
        rawGlobals.audioEnabled = scene.player.audio?.managerIdentity ?? 0
        rawGlobals.masterVolume = scene.player.audio?.routing.masterVolume ?? 0
        let completed = withUnsafeMutablePointer(to:&rawGlobals){g in
            var context = ClawLiftThrowContext(scene:scene.breakables!.host,globals:g,playerPhysics:nil,attack:nil,enemyWordCount:260,composeAnimation:1,fault:0,core:scene.coreGlobals)
            let done = arguments.withUnsafeBufferPointer{claw_lift_throw_entry(entry,receiver,$0.baseAddress,UInt32($0.count),&context,nativeCarryLiftDependency,Unmanaged.passUnretained(self).toOpaque(),&result)}
            fault = max(fault,context.fault);return done
        }
        if completed != 1 { unresolved.insert(entry) };return result
    }
    // The source powerup selector may have already changed raw player words.
    // Cleanup consumes those live tokens without exporting a stale Swift model.
    func cleanupRaw(arguments:[UInt32]) -> UInt32 {
        guard arguments.count == 3,let input = scene.camera?.inputToken,let component = scene.breakables else { fault = 1;return 0 }
        var rawGlobals = ClawLiftThrowGlobals(),result:UInt32 = 0
        claw_lift_throw_defaults(&rawGlobals);rawGlobals.playerToken = arguments[0];rawGlobals.inputToken = input
        let completed = withUnsafeMutablePointer(to:&rawGlobals){g in
            var context = ClawLiftThrowContext(scene:component.host,globals:g,playerPhysics:nil,attack:nil,enemyWordCount:260,composeAnimation:1,fault:0,core:scene.coreGlobals)
            let done = scene.heap.withStableFreedStorage{arguments.withUnsafeBufferPointer{claw_lift_throw_entry(0x41c4e0,0,$0.baseAddress,UInt32($0.count),&context,nativeCarryLiftDependency,Unmanaged.passUnretained(self).toOpaque(),&result)}}
            fault = max(fault,context.fault);return done
        }
        entries[0x41c4e0,default:0] &+= 1
        if completed != 1 { unresolved.insert(0x41c4e0) };return result
    }
    fileprivate func service(_ entry:UInt32,receiver:UInt32,arguments:[UInt32],name:String? = nil) -> UInt32 {
        let a = arguments.first ?? 0
        if entry == 0x4cbb60 || entry == 0x41d750 || entry == 0x417c50 || entry == 0x41fc30 || entry == 0x4cd740 {
            // The common epilogue publishes raw words before every call. Reuse
            // existing complete player services on a separate model buffer.
            scratch.pointee.actor.27 = scene.heap.lookup(0x10002000,words:28)![27]
            exchange(scratch,output:false)
            let x:UInt32,y:UInt32,z:UInt32
            if entry == 0x4cbb60 { guard arguments.count == 4 else { fault = 1;return 0 };x=arguments[1];y=arguments[2];z=arguments[3] }
            else if entry == 0x41fc30 { guard arguments.count == 4 else { fault = 1;return 0 };x=arguments[3];y=0;z=0 }
            else if entry == 0x4cd740 { x=arguments.count > 1 ? arguments[1] : 0;y=0;z=0 }
            else { x=0;y=0;z=0 }
            let result = scene.player.dependency(scratch,entry:entry,a:x,b:y,c:z)
            exchange(scratch,output:true);return result
        }
        if entry == 0x4a48e0 { return scene.heap.allocate(bytes:a) }
        if entry == 0x420910 {
            guard let label = clawOriginalResourceNames[a] else { fault = 1;return 0 }
            return scene.player.audio?.play(name:label) ?? 0
        }
        return UInt32(truncatingIfNeeded:scene.breakables?.service(entry,receiver:receiver,arguments:arguments,name:name) ?? 0)
    }
}
private let nativeCarryLiftDependency:ClawLiftThrowDependency = {context,event,user in
    guard let context,let event,let user else { return 0 };let owner = Unmanaged<ClawNativeCarry>.fromOpaque(user).takeUnretainedValue(),call = event.pointee
    let result = owner.service(call.function,receiver:call.receiver,arguments:withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))},name:call.name.map{String(cString:$0)})
    if owner.fault != 0 || owner.scene.breakables?.fault != 0 { context.pointee.fault = 1 };return UInt64(result)
}
private let nativeCarryTailDependency:ClawPlayerCarryDispatchDependency = {context,event,user in
    guard let context,let event,let user else { return 0 };let owner = Unmanaged<ClawNativeCarry>.fromOpaque(user).takeUnretainedValue(),call = event.pointee
    let result = owner.service(call.function,receiver:call.receiver,arguments:withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))})
    if owner.fault != 0 || owner.scene.breakables?.fault != 0 { context.pointee.fault = 1 };return result
}

extension ClawNativeCarry {
    struct SavedState: Codable, Equatable {
        let globals: ClawSnapshotValue<ClawLiftThrowGlobals>, scratch: ClawSnapshotValue<ClawPlayerLocomotion>
        let fault: UInt32, unresolved: Set<UInt32>, entries: [UInt32: UInt64]
        let bound: Bool, enemyWordCount: UInt32, composeAnimation: UInt32, contextFault: UInt32
    }
    func savedState() throws -> SavedState {
        guard !active, lift.pointee.playerPhysics == nil else { throw ClawSnapshotError.activeFrame }
        return .init(globals: ClawSnapshotValue(globals.pointee), scratch: ClawSnapshotValue(scratch.pointee), fault: fault,
            unresolved: unresolved, entries: entries, bound: lift.pointee.globals != nil, enemyWordCount: lift.pointee.enemyWordCount,
            composeAnimation: lift.pointee.composeAnimation, contextFault: lift.pointee.fault)
    }
    func restoreState(_ saved: SavedState) throws {
        guard !active, lift.pointee.playerPhysics == nil else { throw ClawSnapshotError.activeFrame }
        guard !saved.bound || scene.breakables != nil else { throw ClawSnapshotError.incompleteOwners }
        globals.pointee = saved.globals.value; scratch.pointee = saved.scratch.value
        fault = saved.fault; unresolved = saved.unresolved; entries = saved.entries
        lift.pointee.scene = saved.bound ? scene.breakables!.host : ClawSceneActorHost()
        lift.pointee.globals = saved.bound ? globals : nil; lift.pointee.attack = saved.bound ? scene.player.attack : nil
        lift.pointee.core = saved.bound ? scene.coreGlobals : nil; lift.pointee.enemyWordCount = saved.enemyWordCount
        lift.pointee.composeAnimation = saved.composeAnimation; lift.pointee.fault = saved.contextFault
    }
}
extension ClawLiftThrowGlobals: ClawSnapshotNativeValue {}
