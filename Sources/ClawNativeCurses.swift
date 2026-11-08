import Foundation

// Actual CursePowerup records pass the original mode gate. Original mode3
// singleplayer deletes them before animation, resource or multiplayer effects.
final class ClawNativeCurses {
    static let callbacks:Set<UInt32> = [0x470a20]
    weak var scene:ClawNativeScene?
    private(set) var originalRecords:[UInt32:ClawInteractionActor] = [:]
    private(set) var initialized:Set<UInt32> = []
    private(set) var fault:UInt32 = 0, unresolved:Set<UInt32> = []
    init(scene:ClawNativeScene) { self.scene = scene }
    func attach(_ snapshot:ClawInteractionActor) { originalRecords[snapshot.token] = snapshot }
    func callback(_ actor:UInt32) {
        guard let scene,let loot = scene.loot else { fault = 1;return }
        var context = ClawPowerupObjectContext();context.scene = scene.actorHost
        context.items = loot.itemContext
        var arguments = ClawPowerupObjectArguments();arguments.count = 1;arguments.words.0 = actor
        var result:UInt32 = 0
        let accepted = claw_powerup_object_entry(0x470a20,0,arguments,&context,{context,event,user in
            guard let context,let event,let user else { return 0 }
            let curses = Unmanaged<ClawNativeCurses>.fromOpaque(user).takeUnretainedValue()
            curses.unresolved.insert(event.pointee.function);context.pointee.fault = 1;return 0
        },Unmanaged.passUnretained(self).toOpaque(),&result)
        fault = max(fault,context.fault)
        if accepted == 1 && fault == 0 { initialized.insert(actor) }
        else { unresolved.insert(0x470a20) }
    }
}

extension ClawNativeCurses {
    struct SavedState: Codable, Equatable {
        let originalRecords: [UInt32: ClawSnapshotValue<ClawInteractionActor>]
        let initialized: Set<UInt32>, fault: UInt32, unresolved: Set<UInt32>
    }
    func savedState() -> SavedState {
        .init(originalRecords: originalRecords.mapValues(ClawSnapshotValue.init), initialized: initialized, fault: fault, unresolved: unresolved)
    }
    func restoreState(_ saved: SavedState) {
        originalRecords = saved.originalRecords.mapValues(\.value); initialized = saved.initialized
        fault = saved.fault; unresolved = saved.unresolved
    }
}
