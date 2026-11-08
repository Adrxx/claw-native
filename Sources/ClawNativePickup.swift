import Foundation

// Ordinary rebound pickup callbacks operate on the live scene heap.
final class ClawNativePickup {
    // Reviewed Level 1 class roots delegated to claw_item_pickup_entry below.
    // claw-progress-class-owner: item_pickup 0x46fd10 0x470100 0x470d00 0x471100
    static let supported:Set<UInt32> = [0x46fd10,0x470100,0x470d00,0x470f00,0x471100]
    let token:UInt32
    weak var loot:ClawNativeLoot?
    private(set) var failure:String?
    private(set) var unresolved:Set<UInt32> = []
    private var actorIdentity: ClawTokenHeap.AllocationIdentity?
    init(token:UInt32,loot:ClawNativeLoot) { self.token = token;self.loot = loot;actorIdentity = loot.scene?.heap.containingAllocationIdentity(at: token, count: 4) }
    var ownsActor: Bool { guard let heap = loot?.scene?.heap, let actorIdentity else { return false };return heap.containingAllocationIdentity(at: token, count: 4) === actorIdentity }
    struct SavedState: Codable, Equatable { let token: UInt32, actor: ClawSnapshotWitness , failure: String?, unresolved: Set<UInt32> }
    func savedState() throws -> SavedState {
        guard let heap = loot?.scene?.heap, let actorIdentity else { throw ClawSnapshotError.invalidState }
        return .init(token: token, actor: ClawSnapshotWitness(heap: heap, token: token, count: 4, identity: actorIdentity, interior: true), failure: failure, unresolved: unresolved)
    }
    static func restoring(_ saved: SavedState, owner: ClawNativeLoot, heap plan: ClawTokenHeap.RestorePlan) throws -> ClawNativePickup {
        guard saved.actor.reference.token == saved.token, saved.actor.reference.count == 4, saved.actor.reference.interior else { throw ClawSnapshotError.invalidState }
        let result = ClawNativePickup(token: saved.token, loot: owner)
        result.actorIdentity = try saved.actor.resolve(in: plan)
        result.failure = saved.failure;result.unresolved = saved.unresolved
        return result
    }
    func snapshot() -> ClawInteractionActor? { ownsActor ? loot?.scene?.snapshotActor(token) : nil }
    func refresh() { loot?.refreshItemContext() }
    func flush() {} // Original item bodies already write the live raw heap.
    func tick() { guard let snapshot = snapshot() else { return };_ = callback(snapshot.primary.4) }
    @discardableResult func callback(_ function:UInt32) -> UInt32 {
        guard ownsActor else { failure = "Retired pickup owner";return 0 };guard let loot else { return 0 };refresh();var result:UInt32 = 0,argument = token
        let supported = claw_item_pickup_entry(function,0,&argument,1,loot.itemContext,nativePickupDependency,Unmanaged.passUnretained(self).toOpaque(),&result)
        if supported != 1 { unresolved.insert(function) }
        if loot.itemContext.pointee.fault != 0 { failure = "Pickup context fault \(loot.itemContext.pointee.fault)" };return supported == 1 ? result : 0
    }
    // Only ordinary categories are supported; catnip and other powerups remain
    // address services. Caller supplies the actual scene interaction election.
    @discardableResult func electedPlayerHit() -> Bool {
        guard ownsActor,let loot,let scene = loot.scene,let snapshot = snapshot() else { return false }
        let type = snapshot.actor.52,value = snapshot.actor.63
        if (type == 0x10000 && Int32(bitPattern:value) > 100) || ![UInt32(0x40000),0x10000,0x800000,0x100000,0x200000,0x100].contains(type) {
            unresolved.insert(type == 0x10000 ? 0x41f990 : 0x41ce80);return false
        }
        guard let write = loot.writePlayer else { failure = "Full native player runtime write-back hook required";return false }
        refresh();loot.player.pointee = loot.readPlayer?() ?? scene.player.runtime
        claw_player_set_actor_word(loot.player,0x74,token)
        var playerSnapshot = scene.player.sceneSnapshot();playerSnapshot.actor = loot.player.pointee.actor;scene.write(playerSnapshot)
        if let raw = scene.heap.lookup(loot.itemContext.pointee.playerPrivateToken,words:78) {
            withUnsafeBytes(of:&loot.player.pointee.privateWords) { UnsafeMutableRawBufferPointer(start:raw,count:312).copyMemory(from:$0) }
        }
        let result = claw_item_pickup_award(token,loot.itemContext,nativePickupDependency,Unmanaged.passUnretained(self).toOpaque())
        if loot.itemContext.pointee.fault != 0 { failure = "Pickup award fault \(loot.itemContext.pointee.fault)" }
        write(loot.player.pointee);return result == 1 && loot.itemContext.pointee.fault == 0
    }
    fileprivate func dependency(_ event:ClawItemPickupCall) -> UInt32 {
        guard let loot,let scene = loot.scene else { return 0 };let a = event.arguments.0
        do {
            switch event.function {
            case 0x4719e0: return loot.initialize() ? 1 : 0
            case 0x4f6286:
                guard let key = event.name.map({String(cString:$0)}) ?? ClawNativeLoot.literalNames[a] else { unresolved.insert(event.function);return 0 }
                return try loot.lookup(key)
            case 0x4c79e0:
                guard let key = event.name.map({String(cString:$0)}) ?? ClawNativeLoot.literalNames[a] else { unresolved.insert(event.function);return 0 }
                let sequence = try loot.resources.sequence(name:key)?.token ?? 0
                return scene.actorAnimation(function:0x4c8220,receiver:event.receiver+0x188,argument0:sequence,argument1:0)
            case 0x4c82a0: return scene.actorAnimation(function:event.function,receiver:event.receiver,argument0:a,argument1:0)
            case 0x4b45f0: return scene.player.audio?.playVoicePool(event.receiver,request:ClawAudioRequest(volume:a,pan:event.arguments.1,pitchPercent:event.arguments.2,looping:event.arguments.3)) ?? 0
            default:
                if let value = loot.externalService?(event) { return value };unresolved.insert(event.function);return 0
            }
        } catch { failure = String(describing:error);return 0 }
    }
}
private let nativePickupDependency:ClawItemPickupDependency = {_,event,user in
    guard let event,let user else { return 0 };return Unmanaged<ClawNativePickup>.fromOpaque(user).takeUnretainedValue().dependency(event.pointee)
}
