import Foundation

// Whole SpecialPowerup callbacks and source-elected CaptainClawHit selector.
// The manager uses shared loot/powerup globals and retained raw warp targets.
final class ClawNativeSpecialPowerups {
    static let callbacks:Set<UInt32> = [0x470430]
    unowned let scene:ClawNativeScene
    private let context = UnsafeMutablePointer<ClawPowerupObjectContext>.allocate(capacity:1)
    private let powerups = UnsafeMutablePointer<ClawPlayerPowerupRuntimeContext>.allocate(capacity:1)
    private let animation = UnsafeMutablePointer<ClawActorAnimationGlobals>.allocate(capacity:1)
    private(set) var originalRecords:[UInt32:ClawInteractionActor] = [:]
    private(set) var initialized:Set<UInt32> = [],awarded:Set<UInt32> = []
    private(set) var fault:UInt32 = 0,unresolved:Set<UInt32> = []
    var waitClock:()->UInt32 = { UInt32(truncatingIfNeeded:DispatchTime.now().uptimeNanoseconds/1_000_000) }
    private(set) var serviceCounts:[UInt32:UInt64] = [:]
    var warpTarget:(UInt32,UInt32) { (context.pointee.warpX,context.pointee.warpY) }
    init(scene:ClawNativeScene) {
        self.scene = scene;context.initialize(to:ClawPowerupObjectContext())
        powerups.initialize(to:ClawPlayerPowerupRuntimeContext());animation.initialize(to:ClawActorAnimationGlobals())
    }
    deinit {
        context.deinitialize(count:1);context.deallocate();powerups.deinitialize(count:1);powerups.deallocate()
        animation.deinitialize(count:1);animation.deallocate()
    }
    func attach(_ record:ClawInteractionActor) { originalRecords[record.token] = record }
    private var host:ClawSceneActorHost {
        var value = scene.speech!.actorHost
        value.context = Unmanaged.passUnretained(self).toOpaque()
        value.lookup = {user,token,words in
            guard let user else { return nil };let owner = Unmanaged<ClawNativeSpecialPowerups>.fromOpaque(user).takeUnretainedValue()
            let span = owner.scene.heap.lookup(token,words:words) ?? owner.scene.player.audio?.speechMetadata(token:token,words:words)
            if span == nil { print("SPECIAL MISSING SPAN",String(token,radix:16),words) };return span
        }
        value.allocate = {user,bytes in guard let user else { return 0 };return Unmanaged<ClawNativeSpecialPowerups>.fromOpaque(user).takeUnretainedValue().scene.heap.allocate(bytes:bytes) }
        value.free = {user,token in guard let user else { return };Unmanaged<ClawNativeSpecialPowerups>.fromOpaque(user).takeUnretainedValue().scene.heap.free(token) }
        value.call = nil;value.readClock = nil;return value
    }
    private func prepare() -> Bool {
        guard let loot = scene.loot,let globals = scene.playerPowerupGlobals,scene.speech != nil,let camera = scene.camera else { fault = 1;return false }
        loot.refreshItemContext();powerups.pointee.scene = host;powerups.pointee.globals = globals;powerups.pointee.fault = 0
        animation.pointee.animationDelta = scene.animationDelta;animation.pointee.audioPosition = scene.player.audio?.routing.masterVolume ?? 0
        context.pointee.scene = host;context.pointee.loot = loot.globals;context.pointee.items = loot.itemContext
        context.pointee.powerups = powerups;context.pointee.animation = animation;context.pointee.inputToken = camera.inputToken
        context.pointee.composeAnimation = 1;context.pointee.composeCreation = 1;context.pointee.fault = 0
        return true
    }
    func callback(_ actor:UInt32) {
        guard prepare() else { return }
        var args = ClawPowerupObjectArguments();args.count = 1;args.words.0 = actor
        var result:UInt32 = 0;let wasNew = scene.snapshotActor(actor)?.primary.7 == 0
        let completed = scene.heap.withStableFreedStorage{claw_powerup_object_entry(0x470430,0,args,context,nativeSpecialPowerupDependency,Unmanaged.passUnretained(self).toOpaque(),&result)}
        fault = max(fault,context.pointee.fault);if completed != 1 { unresolved.insert(0x470430) }
        if wasNew && fault == 0 { initialized.insert(actor) }
    }
    func electedPlayerHit(_ item:UInt32) {
        guard prepare(),let loot = scene.loot else { return }
        loot.player.pointee = scene.player.runtime
        var result:UInt32 = 0
        let completed = withUnsafeMutablePointer(to:&loot.player.pointee.physics){physics in
            context.pointee.physics = physics
            return scene.heap.withStableFreedStorage{claw_powerup_object_award(item,context,nativeSpecialPowerupDependency,Unmanaged.passUnretained(self).toOpaque(),&result)}
        }
        context.pointee.physics = nil;fault = max(fault,context.pointee.fault)
        if completed != 1 { unresolved.insert(0x41ce80) }
        if let snapshot = scene.snapshotActor(0x10002000),let priv = scene.heap.lookup(snapshot.primary.5,words:78) {
            scene.player.acceptSceneSnapshot(snapshot,physics:loot.player.pointee.physics,privateWords:UnsafePointer(priv))
            var updated = scene.player.runtime;updated.powerup = scene.playerPowerupGlobals!.pointee.powerup
            scene.player.acceptRuntimeSnapshot(updated)
        } else { fault = 1 }
        if fault == 0 { awarded.insert(item) }
    }
    fileprivate func service(_ call:ClawPowerupObjectCall) -> UInt32 {
        let args = withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
        let a = args.first ?? 0,label = call.name.map{String(cString:$0)} ?? ClawNativeEffects.names[a] ?? clawOriginalResourceNames[a]
        serviceCounts[call.function,default:0] &+= 1
        if ClawNativeSpeech.services.contains(call.function) { return scene.speech?.service(call.function,receiver:call.receiver,arguments:args) ?? 0 }
        do {
            switch call.function {
            case 0x4f6286:
                guard let label else { fault = 1;return 0 }
                if call.receiver == 0x63000010 { return try scene.objectResources?.sequence(name:label)?.token ?? 0 }
                let parent = scene.heap.lookup(0x10001000,words:12)!
                if call.receiver == parent[10] &+ 16 { return scene.player.audio?.resolve(name:label)?.resourceToken ?? 0 }
                return try scene.loot?.lookup(label) ?? 0
            case 0x4c79e0:
                guard let label,args.count == 2 else { fault = 1;return 0 }
                return scene.namedAnimation(function:call.function,actor:call.receiver,name:label,eager:args[1])
            case 0x4c8220,0x4c82a0:
                return scene.actorAnimation(function:call.function,receiver:call.receiver,argument0:a,argument1:0)
            case 0x4c8da0:
                var event = ClawItemPickupCall();event.function = call.function;event.receiver = call.receiver;event.argumentCount = call.argumentCount;event.name = call.name
                withUnsafeMutableBytes(of:&event.arguments){raw in args.withUnsafeBytes{UnsafeMutableRawBufferPointer(rebasing:raw.prefix($0.count)).copyMemory(from:$0)}}
                guard let result = scene.effects?.itemService(event) else { fault = 1;return 0 };return result
            case 0x4c6130:
                guard args.count == 2,let rendering = scene.rendering else { fault = 1;return 0 }
                return rendering.setCompressedEffect(call.receiver,effect:a,resource:args[1])
            case 0x4b45f0:
                guard args.count == 4 else { fault = 1;return 0 }
                return scene.player.audio?.playVoicePool(call.receiver,request:ClawAudioRequest(volume:a,pan:args[1],pitchPercent:args[2],looping:args[3])) ?? 0
            case 0x4208e0:return scene.player.audio?.play(resource:call.receiver,volume:a) ?? 0
            case 0x4b8960:
                var wait = ClawPlayerFadeContext(scene:host,globals:nil,descriptorWord3:0,temporaryDescriptorToken:0,maximumClockReads:1000000,fault:0),result:UInt32 = 0
                let done = args.withUnsafeBufferPointer{claw_player_fade_entry(call.function,call.receiver,$0.baseAddress,UInt32($0.count),&wait,{context,event,user in
                    guard let context,let event,let user else { return 0 }
                    let owner = Unmanaged<ClawNativeSpecialPowerups>.fromOpaque(user).takeUnretainedValue()
                    guard event.pointee.function == 0x546df0 else { context.pointee.fault = 1;return 0 };return owner.waitClock()
                },Unmanaged.passUnretained(self).toOpaque(),&result)}
                if done != 1 || wait.fault != 0 { fault = max(1,wait.fault) };return result
            case 0x546d50:
                guard args.count == 4 else { fault = 1;return 0 }
                if args[1] == 0x111 { scene.player.postCommand(args[2]) };return 1
            case 0x4a3050:return scene.nextRandom()
            case 0x41c4e0:
                // Carry cleanup is a complete raw source entry, not a model
                // shortcut that would discard the held actor's callback/bitset.
                guard args.count == 3,let carry = scene.carry else { fault = 1;return 0 }
                let result = carry.cleanupRaw(arguments:args)
                if carry.fault != 0 { fault = carry.fault };return result
            default:
                var item = ClawItemPickupCall();item.function = call.function;item.receiver = call.receiver;item.argumentCount = call.argumentCount;item.name = call.name
                withUnsafeMutableBytes(of:&item.arguments){raw in args.withUnsafeBytes{UnsafeMutableRawBufferPointer(rebasing:raw.prefix($0.count)).copyMemory(from:$0)}}
                if let result = scene.effects?.itemService(item) { return result }
                unresolved.insert(call.function);fault = 1;return 0
            }
        } catch { fault = 1;return 0 }
    }
}
private let nativeSpecialPowerupDependency:ClawPowerupObjectDependency = {context,event,user in
    guard let context,let event,let user else { return 0 };let owner = Unmanaged<ClawNativeSpecialPowerups>.fromOpaque(user).takeUnretainedValue()
    let value = owner.service(event.pointee);if owner.fault != 0 { context.pointee.fault = owner.fault };return value
}

extension ClawNativeSpecialPowerups {
    struct SavedState: Codable, Equatable {
        let records: [UInt32: ClawSnapshotValue<ClawInteractionActor>], initialized: Set<UInt32>, awarded: Set<UInt32>
        let context: [String: Data], animation: ClawSnapshotValue<ClawActorAnimationGlobals>, powerupFault: UInt32
        let fault: UInt32, unresolved: Set<UInt32>, calls: [UInt32: UInt64]
    }
    func savedState() throws -> SavedState {
        guard context.pointee.physics == nil else { throw ClawSnapshotError.activeFrame }
        return .init(records: originalRecords.mapValues(ClawSnapshotValue.init), initialized: initialized, awarded: awarded,
            context: Self.snapshotFields.capture(context.pointee), animation: ClawSnapshotValue(animation.pointee), powerupFault: powerups.pointee.fault,
            fault: fault, unresolved: unresolved, calls: serviceCounts)
    }
    func restoreState(_ saved: SavedState) throws {
        guard context.pointee.physics == nil else { throw ClawSnapshotError.activeFrame }
        let cx = try Self.snapshotFields.restoring(saved.context, into: context.pointee)
        originalRecords = saved.records.mapValues(\.value); initialized = saved.initialized; awarded = saved.awarded
        context.pointee = cx; animation.pointee = saved.animation.value; powerups.pointee.fault = saved.powerupFault
        fault = saved.fault; unresolved = saved.unresolved; serviceCounts = saved.calls
    }
    private static let snapshotFields = ClawSnapshotFields<ClawPowerupObjectContext>(fields: [
        .init("inputToken", \.inputToken),
        .init("curseEnabled", \.curseEnabled),
        .init("warpX", \.warpX),
        .init("warpY", \.warpY),
        .init("composeAnimation", \.composeAnimation),
        .init("composeCreation", \.composeCreation),
        .init("fault", \.fault)
    ])
}
