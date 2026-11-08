import Foundation

// Whole original single FrontCrate/BehindCrate callbacks over live scene words.
// Keg and stacked private graphs remain separate integration work.
final class ClawNativeSingleCrates {
    static let callbacks:Set<UInt32> = [0x471720,0x471750,0x471530]
    weak var scene:ClawNativeScene?
    let globals = UnsafeMutablePointer<ClawBreakableGlobals>.allocate(capacity:1)
    private let context = UnsafeMutablePointer<ClawBreakableContext>.allocate(capacity:1)
    private(set) var tokens:Set<UInt32> = []
    private(set) var originalRecords:[UInt32:ClawInteractionActor] = [:]
    private(set) var initialized:Set<UInt32> = []
    private(set) var fault:UInt32 = 0, unresolved:Set<UInt32> = []
    init(scene:ClawNativeScene) {
        self.scene = scene;globals.initialize(to:ClawBreakableGlobals());context.initialize(to:ClawBreakableContext())
        context.pointee.globals = globals
    }
    deinit { context.deinitialize(count:1);context.deallocate();globals.deinitialize(count:1);globals.deallocate() }
    func attach(_ snapshot:ClawInteractionActor) { tokens.insert(snapshot.token); originalRecords[snapshot.token] = snapshot }
    func remove(_ token:UInt32) { tokens.remove(token) }
    @discardableResult func callback(_ function:UInt32,actor:UInt32) -> UInt32 {
        guard let scene,let loot = scene.loot,let speech = scene.speech else { fault = 1;return 0 }
        context.pointee.scene = speech.actorHost;context.pointee.loot = loot.globals
        globals.pointee.animationDelta = scene.animationDelta
        globals.pointee.audioEnabled = scene.player.audio?.managerIdentity ?? 0
        globals.pointee.audioPosition = scene.player.audio?.routing.masterVolume ?? 0
        let wasNew = scene.snapshotActor(actor)?.primary.7 == 0
        let result = invoke(function,receiver:0,arguments:[actor])
        if wasNew && fault == 0 { initialized.insert(actor) };return result
    }
    private func invoke(_ function:UInt32,receiver:UInt32,arguments:[UInt32]) -> UInt32 {
        guard let scene else { fault = 1;return 0 }
        var result:UInt32 = 0
        let accepted = scene.heap.withStableFreedStorage {
            arguments.withUnsafeBufferPointer {
                claw_breakable_entry(function,receiver,$0.baseAddress,UInt32($0.count),context,nativeSingleCrateDependency,
                    Unmanaged.passUnretained(self).toOpaque(),&result)
            }
        }
        fault = max(fault,context.pointee.fault);if accepted != 1 { unresolved.insert(function) };return result
    }
    fileprivate func dependency(_ event:ClawBreakableCall) -> UInt64 {
        guard let scene,let loot = scene.loot else { fault = 1;return 0 }
        let args = withUnsafeBytes(of:event.arguments) { Array($0.bindMemory(to:UInt32.self).prefix(Int(event.argumentCount))) }
        let a = args.first ?? 0
        let label = event.name.map{String(cString:$0)} ?? clawOriginalResourceNames[a]
        do {
            switch event.function {
            case 0x40f680:
                // Bound image-frame identity transport, with the source signed
                // bounds. This is not counted as a new whole helper proof.
                guard let imageRoot = scene.heap.lookup(event.receiver,words:27), Int32(bitPattern:a) >= Int32(bitPattern:imageRoot[25]), Int32(bitPattern:a) <= Int32(bitPattern:imageRoot[26]) else { return 0 }
                return UInt64(scene.heap.lookup(imageRoot[5] &+ a &* 4,words:1)?.pointee ?? 0)
            case 0x4c7fa0:
                guard let label else { fault = 1;return 0 };return UInt64(scene.bindSecondaryLogic(actor:event.receiver,name:label))
            case 0x4c79e0:
                guard let label,args.count == 2 else { fault = 1;return 0 }
                return UInt64(scene.namedAnimation(function:event.function,actor:event.receiver,name:label,eager:args[1]))
            case 0x4c82a0:
                return UInt64(scene.actorAnimation(function:event.function,receiver:event.receiver,argument0:a,argument1:0))
            case 0x4f6286:
                guard let label else { fault = 1;return 0 };return UInt64(try loot.lookup(label))
            case 0x4b45f0:
                guard args.count == 4 else { fault = 1;return 0 }
                return UInt64(scene.player.audio?.playVoicePool(event.receiver,request:ClawAudioRequest(volume:a,pan:args[1],pitchPercent:args[2],looping:args[3])) ?? 0)
            case 0x4a3050:return UInt64(scene.nextRandom())
            case 0x4735b0,0x40f540,0x40f450,0x473610:
                return UInt64(invoke(event.function,receiver:event.receiver,arguments:args))
            case 0x4719e0:return loot.initialize() ? 1 : 0
            case 0x4c8da0,0x40e690:
                guard args.count <= 8 else { fault = 1;return 0 }
                var call = ClawWorldLootCall();call.function = event.function;call.receiver = event.receiver;call.argumentCount = event.argumentCount;call.name = event.name
                withUnsafeMutableBytes(of:&call.arguments) { raw in args.withUnsafeBytes { source in UnsafeMutableRawBufferPointer(rebasing:raw.prefix(source.count)).copyMemory(from:source) } }
                return UInt64(loot.sourceService(call))
            default:unresolved.insert(event.function);fault = 1;return 0
            }
        } catch { fault = 1;return 0 }
    }
}
private let nativeSingleCrateDependency:ClawBreakableDependency = { _,event,user in
    guard let event,let user else { return 0 }
    return Unmanaged<ClawNativeSingleCrates>.fromOpaque(user).takeUnretainedValue().dependency(event.pointee)
}

extension ClawNativeSingleCrates {
    struct SavedState: Codable, Equatable {
        let globals: ClawSnapshotValue<ClawBreakableGlobals>
        let tokens: Set<UInt32>, initialized: Set<UInt32>, fault: UInt32, unresolved: Set<UInt32>, contextFault: UInt32
        let originalRecords: [UInt32: ClawSnapshotValue<ClawInteractionActor>]
    }
    func savedState() -> SavedState {
        .init(globals: ClawSnapshotValue(globals.pointee), tokens: tokens, initialized: initialized,
            fault: fault, unresolved: unresolved, contextFault: context.pointee.fault,
            originalRecords: originalRecords.mapValues(ClawSnapshotValue.init))
    }
    func restoreState(_ saved: SavedState) {
        globals.pointee = saved.globals.value; tokens = saved.tokens; initialized = saved.initialized
        fault = saved.fault; unresolved = saved.unresolved; context.pointee.fault = saved.contextFault
        originalRecords = saved.originalRecords.mapValues(\.value)
        if let scene { context.pointee.scene = scene.speech?.actorHost ?? ClawSceneActorHost(); context.pointee.loot = scene.loot?.globals }
    }
}
extension ClawBreakableGlobals: ClawSnapshotNativeValue {}
extension ClawInteractionActor: ClawSnapshotNativeValue {}
