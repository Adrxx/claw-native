import Foundation

// Source crumble/toggle callbacks share live player support, profile, clock and
// scheduler delay words with the ordinary native scene.
final class ClawNativePegs {
    static let callbacks: Set<UInt32> = [0x49d860,0x49d620,0x49e4e0,0x49e7b0,0x49e7d0,0x49e7f0]
    weak var scene: ClawNativeScene?
    let globals = UnsafeMutablePointer<ClawPegGlobals>.allocate(capacity: 1)
    private(set) var tokens: Set<UInt32> = []
    private(set) var fault: UInt32 = 0
    private(set) var unresolved: Set<UInt32> = []
    init(scene: ClawNativeScene) {
        self.scene = scene; globals.initialize(to: ClawPegGlobals())
        globals.pointee.defaultsToken = scene.platforms!.profile.pointee.selectedToken
        globals.pointee.playerToken = 0x10002000
        globals.pointee.audioManagerToken = scene.player.audio?.managerIdentity ?? 0
    }
    deinit { globals.deinitialize(count:1); globals.deallocate() }
    func attach(_ token:UInt32) { tokens.insert(token) }
    func remove(_ token:UInt32) { tokens.remove(token) }
    private var host: ClawSceneActorHost {
        guard let scene else { return ClawSceneActorHost() }
        var value = scene.actorHost
        value.context = Unmanaged.passUnretained(self).toOpaque()
        value.lookup = { user, token, count in
            guard let user else { return nil }
            let pegs = Unmanaged<ClawNativePegs>.fromOpaque(user).takeUnretainedValue()
            return pegs.scene?.heap.lookup(token,words:count) ?? pegs.scene?.player.audio?.speechMetadata(token:token,words:count)
        }
        // Composed ANI only borrows lookup/call. Allocation/free/clock remain
        // unused in these complete source bodies, so do not inherit callbacks
        // with a different context type.
        value.allocate = nil; value.free = nil; value.call = nil; value.readClock = nil
        return value
    }
    func callback(_ function:UInt32, actor:UInt32) {
        guard let scene else { fault = 1; return }
        globals.pointee.tick = scene.gameTime; globals.pointee.animationDelta = scene.animationDelta
        globals.pointee.audioVolume = scene.player.audio?.routing.masterVolume ?? 0
        //53725c remains the explicit startup-zero gate until the source owner
        //that changes it is connected. No host crumble/toggle timer is added.
        globals.pointee.gate = scene.heap.lookup(0x53725c,words:1)?.pointee ?? 0
        var context = ClawPegContext(scene:host, globals:globals, composeAnimation:1, fault:0)
        var argument = actor, result:UInt32 = 0
        let supported = withUnsafePointer(to:&argument) {
            claw_peg_entry(function,0,$0,1,&context,nativePegDependency,Unmanaged.passUnretained(self).toOpaque(),&result)
        }
        fault = max(fault,context.fault); if supported != 1 { unresolved.insert(function) }
    }
    fileprivate func dependency(_ event:ClawPegCall) -> UInt32 {
        guard let scene else { fault = 1; return 0 }
        switch event.function {
        case 0x4f6286:
            guard let name = event.name else { fault = 1; return 0 }
            let label = String(cString:name)
            do {
                if label == "GAME_FORWARD50" || label == "GAME_BACKWARD50" { return try scene.objectResources?.sequence(name:label)?.token ?? 0 }
                return scene.player.audio?.resolve(name:label)?.resourceToken ?? 0
            } catch { fault = 1; return 0 }
        case 0x4b45f0:
            return scene.player.audio?.playVoicePool(event.receiver,request:ClawAudioRequest(volume:event.arguments.0,pan:event.arguments.1,pitchPercent:event.arguments.2,looping:event.arguments.3)) ?? 0
        case 0x4c88e0:
            return scene.player.audio?.playSpatial(resource:event.receiver,sourceX:event.arguments.0,referenceX:event.arguments.1,clampDistance:event.arguments.2,panDistance:event.arguments.3) ?? 0
        default: unresolved.insert(event.function); fault = 1; return 0
        }
    }
}
private let nativePegDependency:ClawPegDependency = { _,event,user in
    guard let event,let user else { return 0 }
    return Unmanaged<ClawNativePegs>.fromOpaque(user).takeUnretainedValue().dependency(event.pointee)
}

extension ClawNativePegs {
    struct SavedState: Codable, Equatable {
        let globals: ClawSnapshotValue<ClawPegGlobals>
        let tokens: Set<UInt32>, fault: UInt32, unresolved: Set<UInt32>
    }
    func savedState() -> SavedState {
        .init(globals: ClawSnapshotValue(globals.pointee), tokens: tokens, fault: fault, unresolved: unresolved)
    }
    func restoreState(_ saved: SavedState) {
        globals.pointee = saved.globals.value; tokens = saved.tokens; fault = saved.fault; unresolved = saved.unresolved
    }
}
extension ClawPegGlobals: ClawSnapshotNativeValue {}
