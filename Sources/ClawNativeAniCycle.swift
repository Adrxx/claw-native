import Foundation

// 0x4918b0 is shared by both registered names. Animation game code is the
// canonical actor_animation family (host precedence); this adapter supplies
// only the physical resource lookup through ClawActorResources.
@objc(ClawNativeAniCycle) class ClawNativeAniCycle: ClawNativeObjectAdapter {
    private struct Owner {
        let actor: ClawTokenHeap.AllocationIdentity
        let stateToken: UInt32
        let state: ClawTokenHeap.AllocationIdentity
    }
    private var owners: [UInt32: Owner] = [:]
    private var active: UInt32?
    // The callback's ordered boundary calls, as the original comparison records them.
    var calls: [ClawCall] { connections.calls.filter { [0x4c79e0, 0x4c82a0, 0x4f6286].contains($0.function) } }
    var tokens: Set<UInt32> { Set(owners.keys) }
    override class var services: Set<UInt32> { [0x4f6286] }
    // 0x4918b0 keeps no locals; its run.call to canonical 0x4c79e0/0x4c82a0 is stackless.
    override class var stacklessCallerReserve: UInt32? { 0x40 }
    override func attach(_ object: ClawInteractionActor, callback: UInt32) -> Bool {
        let heap = connections.host.heap
        guard callback == 0x4918b0, owners[object.token] == nil,
              let actor = heap.allocationIdentity(at: object.token, count: 0x1b4),
              let state = heap.allocationIdentity(at: object.actor.27, count: 0x174),
              object.primary.4 == 0x4918b0 else { return false }
        // Spatial residency owns activation and scene-list insertion.
        connections.scene?.write(object)
        owners[object.token] = Owner(actor: actor, stateToken: object.actor.27, state: state)
        return true
    }
    override func remove(_ token: UInt32) { owners.removeValue(forKey: token) }
    private func valid(_ actor: UInt32) -> Bool {
        let heap = connections.host.heap
        guard let owner = owners[actor],
              heap.allocationIdentity(at: actor, count: 0x1b4) === owner.actor,
              heap.allocationIdentity(at: owner.stateToken, count: 0x174) === owner.state,
              heap.lookup(actor + 0x6c, words: 1)?.pointee == owner.stateToken,
              heap.lookup(owner.stateToken + 0x10, words: 1)?.pointee == 0x4918b0 else { return false }
        return true
    }
    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x4918b0, active == nil, valid(actor) else { connections.reject(actor); return }
        active = actor
        defer { active = nil }
        connections.record("ClawNativeAniCycle")
        connections.record("0x4918b0")
        var call = ClawCall()
        call.function = 0x4918b0; call.argumentCount = 1; call.arguments.0 = actor
        callbackCompletion = connections.host.invoke(call)
        if !valid(actor) { connections.reject(actor) }
    }
    override func service(_ call: ClawCall) -> UInt32? {
        // Canonical actor_animation (0x4c79e0) asks the physical dictionary
        // for GAME_CYCLE100 and reads the token from its stack output.
        guard let actor = active, valid(actor), let scene = connections.scene,
              scene.heap === connections.host.heap, call.function == 0x4f6286,
              call.receiver2 == 0, call.x87ArgumentCount == 0, call.argumentCount == 2,
              call.arguments.0 == 0x5240d8,
              let output = connections.host.bytes(call.arguments.1, count: 4) else { return nil }
        connections.record("ClawActorResources.0x4f6286")
        let token = scene.resolveResource(dictionary: call.receiver, name: call.arguments.0)
        guard scene.fault == 0, valid(actor) else {
            connections.host.fail(UInt32(CLAW_FAULT_HOST), at: call.function)
            return nil
        }
        withUnsafeBytes(of: token.littleEndian) { output.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 4) }
        return token == 0 ? 0 : 1
    }

    override func savedAdapterState() throws -> ClawAdapterSavedState {
        try snapshotBoundary()
        guard active == nil else { throw ClawSnapshotError.activeFrame }
        let heap = connections.host.heap
        func record(_ token: UInt32, _ owner: Owner) -> ClawAdapterSavedState.Owner {
            .init(actor: ClawSnapshotWitness(heap: heap, token: token, count: 0x1b4, identity: owner.actor),
                  state: ClawSnapshotWitness(heap: heap, token: owner.stateToken, count: 0x174, identity: owner.state), helper: 0)
        }
        return .init(owners: owners.keys.sorted().map { record($0, owners[$0]!) }, children: [],
            pins: [], memory: nil, issued: [:])
    }
    override func prepareAdapterRestore(_ value: ClawAdapterSavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws -> Void {
        try snapshotBoundary(); try connections.host.heap.validateRestore(plan); try value.validate()
        guard active == nil else { throw ClawSnapshotError.activeFrame }
        guard value.children.isEmpty, value.pins.isEmpty, value.memory == nil, value.issued.isEmpty, value.owners.allSatisfy({ $0.helper == 0 }) else { throw ClawSnapshotError.invalidState }
        func records(_ values: [ClawAdapterSavedState.Owner]) throws -> [UInt32: Owner] {
            var result: [UInt32: Owner] = [:]
            for record in values {
                result[record.actor.reference.token] = Owner(actor: try record.actor.resolve(in: plan), stateToken: record.state.reference.token,
                    state: try record.state.resolve(in: plan))
            }
            return result
        }
        let restored = try records(value.owners)
        return { [self] in
            try snapshotBoundary(); try connections.host.heap.validateInstalledRestore(plan)
            guard active == nil else { throw ClawSnapshotError.activeFrame }
            owners = restored
        }
    }
}
