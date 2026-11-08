import Foundation

// Closed native adapter graph; diagnostic ClawCall history is deliberately absent.
struct ClawAdapterSavedState: Codable, Equatable {
    struct Owner: Codable, Equatable {
        let actor: ClawSnapshotWitness, state: ClawSnapshotWitness
        let helper: UInt32
    }
    let owners: [Owner], children: [Owner], pins: [ClawSnapshotWitness]
    let memory: ClawNativeMfcMemory.SavedState?
    let issued: [UInt32: UInt32]
    func validate() throws {
        for records in [owners, children] {
            guard records.count <= 16384, Set(records.map { $0.actor.reference.token }).count == records.count,
                records.allSatisfy({
                    $0.actor.reference.count == 0x1b4 && $0.state.reference.count == 0x174 && !$0.actor.reference.interior
                        && !$0.state.reference.interior
                })
            else { throw ClawSnapshotError.invalidState }
        }
        guard Set(pins.map { $0.reference.token }).count == pins.count,
            pins.allSatisfy({ $0.reference.count > 0 && $0.reference.interior }),
            issued.values.allSatisfy({ $0 == 0x7c || $0 == 0x174 }),
            issued.allSatisfy({ token, count in
                memory?.allocationHistory.contains(where: { $0.token == token && $0.count == count }) == true
            }),
            owners.allSatisfy({ $0.helper == 0 || issued[$0.helper] == 0x7c })
        else { throw ClawSnapshotError.invalidState }
    }
}

// One scene-owned object adapter. A consumer subclasses this in its own file,
// names the runtime class with @objc(<adapter>) exactly as its election says,
// and declares the finite non-canonical service addresses it answers. The
// bridge owns election, actor ownership, dispatch, teardown and faults.
class ClawNativeObjectAdapter: NSObject {
    unowned let connections: ClawNativeObjectConnections
    let election: ClawNativeObjectConnections.Election
    // Diagnostic result only; no borrowed C call or gameplay ownership.
    var callbackCompletion: ClawNativeCanonicalHost.Completion?
    required init(connections: ClawNativeObjectConnections, election: ClawNativeObjectConnections.Election) {
        self.connections = connections
        self.election = election
    }
    // Native service addresses reachable through ClawNativeCanonicalHost while
    // this adapter's callback is active. A canonical address here is rejected.
    class var services: Set<UInt32> { [] }
    // Set when the recovered callback issues calls without tracking callee
    // ESP (run.call outside a Frame) and one of them reaches a canonical
    // entry: bytes reserved below its entry ESP for its own locals.
    class var stacklessCallerReserve: UInt32? { nil }
    // Return false to reject the scene object; the bridge then faults.
    func attach(_ object: ClawInteractionActor, callback: UInt32) -> Bool { false }
    // Called only for an elected callback on an actor this adapter attached.
    func callback(_ function: UInt32, actor: UInt32) { connections.reject(function) }
    // nil means unsupported; the host reports a missing dependency.
    func service(_ call: ClawCall) -> UInt32? { nil }
    func remove(_ actor: UInt32) {}
    func prepareAdapterProvider(_ value: ClawAdapterSavedState) throws {}
    func savedAdapterState() throws -> ClawAdapterSavedState { throw ClawSnapshotError.incompleteOwners }
    func prepareAdapterRestore(_ value: ClawAdapterSavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws -> Void {
        throw ClawSnapshotError.incompleteOwners
    }
    func snapshotBoundary() throws {
        guard connections.active == nil, connections.host.snapshotQuiescent else { throw ClawSnapshotError.activeFrame }
    }
}

// A closed scene join, not an automatic dispatcher for the canonical registry.
// Elections are explicit and finite; an absent adapter class leaves its objects
// uninstantiated and is reported as missing, never as a fault.
final class ClawNativeObjectConnections {
    struct Election {
        let family: String, adapter: String, callbacks: [UInt32]
    }

    // MARK: - Finite adapter elections

    static let elections: [Election] = [
        Election(family: "ani_cycle", adapter: "ClawNativeAniCycle", callbacks: [0x4918b0]),
        Election(family: "boss_stager", adapter: "ClawNativeBossStager", callbacks: [0x48ded0]),
        Election(family: "boss_warp", adapter: "ClawNativeBossWarp", callbacks: [0x470870]),
        Election(family: "tower_cannon_left", adapter: "ClawNativeTowerCannonLeft", callbacks: [0x495d40]),
        Election(family: "tower_cannon_right", adapter: "ClawNativeTowerCannonRight", callbacks: [0x495e00]),
        Election(family: "cut_throat", adapter: "ClawNativeCutThroat", callbacks: [0x4379d0]),
        Election(family: "floor_spike", adapter: "ClawNativeFloorSpike", callbacks: [0x461d50]),
        Election(family: "path_elevator", adapter: "ClawNativePathElevator", callbacks: [0x49ee30]),
        Election(family: "robber_thief", adapter: "ClawNativeRobberThief", callbacks: [0x485270]),
        Election(family: "spring_board", adapter: "ClawNativeSpringBoard", callbacks: [0x49db90]),
        Election(family: "start_stepping_stone", adapter: "ClawNativeStartSteppingStone", callbacks: [0x49eb30]),
        Election(family: "stepping_stone", adapter: "ClawNativeSteppingStone", callbacks: [0x49e810]),
        Election(family: "front_statue", adapter: "ClawNativeFrontStatue", callbacks: [0x471780]),
        Election(family: "behind_statue", adapter: "ClawNativeBehindStatue", callbacks: [0x4717b0]),
        Election(family: "break_plank", adapter: "ClawNativeBreakPlank", callbacks: [0x40f7b0]),
        Election(family: "jump_switch", adapter: "ClawNativeJumpSwitch", callbacks: [0x453b10]),
        Election(family: "seagull", adapter: "ClawNativeSeagull", callbacks: [0x486e90]),
        Election(family: "town_guard1", adapter: "ClawNativeTownGuard1", callbacks: [0x496050]),
        Election(family: "town_guard2", adapter: "ClawNativeTownGuard2", callbacks: [0x4968d0]),
        Election(family: "goo_vent", adapter: "ClawNativeGooVent", callbacks: [0x448620]),
        Election(family: "ground_blower", adapter: "ClawNativeGroundBlower", callbacks: [0x448d10]),
        Election(family: "bear_sailor", adapter: "ClawNativeBearSailor", callbacks: [0x409860]),
        Election(family: "crab_nest", adapter: "ClawNativeCrabNest", callbacks: [0x432570]),
        Election(family: "hermit_crab", adapter: "ClawNativeHermitCrab", callbacks: [0x449c40]),
        Election(family: "red_tail_pirate", adapter: "ClawNativeRedTailPirate", callbacks: [0x482820]),
        Election(family: "cannon_button", adapter: "ClawNativeCannonButton", callbacks: [0x414cc0]),
        Election(family: "cannon_switch", adapter: "ClawNativeCannonSwitch", callbacks: [0x415350]),
        Election(family: "conveyor_belt", adapter: "ClawNativeConveyorBelt", callbacks: [0x431320]),
        Election(family: "crazy_hook", adapter: "ClawNativeCrazyHook", callbacks: [0x434190]),
        Election(family: "peg_leg", adapter: "ClawNativePegLeg", callbacks: [0x4689b0]),
        Election(family: "saw_blade", adapter: "ClawNativeSawBlade", callbacks: [0x462040]),
        Election(
            family: "object_variants", adapter: "ClawNativeObjectVariants",
            callbacks: [0x461fe0, 0x462000, 0x462020, 0x4622f0, 0x462310, 0x49ead0, 0x49eaf0, 0x49eb10]),
        Election(family: "skull_cannon", adapter: "ClawNativeSkullCannon", callbacks: [0x48a800]),
        Election(family: "t_projectile", adapter: "ClawNativeTProjectile", callbacks: [0x497eb0]),
        Election(family: "marrow", adapter: "ClawNativeMarrow", callbacks: [0x458680]),
        Election(family: "marrow_floor", adapter: "ClawNativeMarrowFloor", callbacks: [0x45a2e0]),
        Election(family: "parrot", adapter: "ClawNativeParrot", callbacks: [0x465580]),
        Election(family: "fish", adapter: "ClawNativeFish", callbacks: [0x441be0]),
        Election(family: "laser", adapter: "ClawNativeLaser", callbacks: [0x4553d0]),
        Election(family: "mercat", adapter: "ClawNativeMercat", callbacks: [0x45ff00]),
        Election(family: "siren", adapter: "ClawNativeSiren", callbacks: [0x489730]),
        Election(family: "aquatis_crack", adapter: "ClawNativeAquatisCrack", callbacks: [0x406400]),
        Election(family: "aquatis_dynamite", adapter: "ClawNativeAquatisDynamite", callbacks: [0x406dd0]),
        Election(family: "aquatis_stalactite", adapter: "ClawNativeAquatisStalactite", callbacks: [0x4073e0]),
        Election(family: "shake", adapter: "ClawNativeShake", callbacks: [0x4887b0]),
        Election(family: "stalactite", adapter: "ClawNativeStalactite", callbacks: [0x48e4a0]),
        Election(family: "tentacle", adapter: "ClawNativeTentacle", callbacks: [0x4922c0]),
        Election(family: "chameleon", adapter: "ClawNativeChameleon", callbacks: [0x421200]),
        Election(family: "red_tail", adapter: "ClawNativeRedTail", callbacks: [0x47f6e0]),
        Election(family: "red_tail_spikes", adapter: "ClawNativeRedTailSpikes", callbacks: [0x4842b0]),
        Election(family: "red_tail_wind", adapter: "ClawNativeRedTailWind", callbacks: [0x4847b0]),
        Election(family: "water_rock", adapter: "ClawNativeWaterRock", callbacks: [0x49de10]),
        Election(family: "lava_geyser", adapter: "ClawNativeLavaGeyser", callbacks: [0x4559e0]),
        Election(family: "lava_hand", adapter: "ClawNativeLavaHand", callbacks: [0x4561c0]),
        Election(family: "lava_mouth", adapter: "ClawNativeLavaMouth", callbacks: [0x457620]),
        Election(family: "raux", adapter: "ClawNativeRaux", callbacks: [0x47e210]),
        Election(family: "omar", adapter: "ClawNativeOmar", callbacks: [0x4633a0]),
        Election(family: "punk_rat", adapter: "ClawNativePunkRat", callbacks: [0x474330]),
        Election(family: "tiger_guard", adapter: "ClawNativeTigerGuard", callbacks: [0x493eb0])
    ]
    static func resolve(_ election: Election) -> ClawNativeObjectAdapter.Type? {
        NSClassFromString(election.adapter) as? ClawNativeObjectAdapter.Type
    }

    // MARK: - Scene graph ownership and callback tracing

    weak var scene: ClawNativeScene?
    let host: ClawNativeCanonicalHost
    private(set) var adapters: [String: ClawNativeObjectAdapter] = [:]
    private(set) var missing: [String] = []
    private var byCallback: [UInt32: ClawNativeObjectAdapter] = [:]
    private struct Owner {
        let adapter: ClawNativeObjectAdapter
        let identity: ClawTokenHeap.AllocationIdentity
    }
    private var owners: [UInt32: Owner] = [:]
    private var usedFamilies: Set<String> = []
    private(set) var active: ClawNativeObjectAdapter?
    var recordsTrace = false
    private(set) var trace: [String] = []
    // Ordered native-level calls (canonical or service) inside adapter callbacks.
    private(set) var calls: [ClawCall] = []
    var callbacks: Set<UInt32> { Set(byCallback.keys) }

    // Dispatch ownership only. Each adapter and the canonical host are separate
    // graph participants. Call history contains borrowed C pointers and is not
    // gameplay state; never serialize those host addresses as an owner image.

    // MARK: - Snapshot ownership and adapter restore

    struct OwnershipSavedState: Codable, Equatable {
        struct Record: Codable, Equatable {
            let actor: UInt32
            let family: String
            let identity: UUID
            let live: ClawTokenHeap.AllocationReference?
        }
        let callbacks: Set<UInt32>, families: Set<String>
        let owners: [Record]
        let usedFamilies: Set<String>
    }
    func savedOwnershipState() throws -> OwnershipSavedState {
        guard active == nil, host.snapshotQuiescent else { throw ClawSnapshotError.activeFrame }
        return OwnershipSavedState(
            callbacks: callbacks, families: Set(adapters.keys),
            owners: owners.keys.sorted().map { actor in
                let owner = owners[actor]!
                return .init(
                    actor: actor, family: owner.adapter.election.family, identity: owner.identity.snapshotID,
                    live: host.heap.snapshotReference(at: actor, count: 4, identity: owner.identity, interior: true))
            }, usedFamilies: usedFamilies)
    }
    func prepareOwnershipRestore(_ value: OwnershipSavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws -> Void {
        guard active == nil, host.snapshotQuiescent else { throw ClawSnapshotError.activeFrame }
        try host.heap.validateRestore(plan)
        guard value.callbacks == callbacks, value.families == Set(adapters.keys),
            Set(value.owners.map(\.actor)).count == value.owners.count,
            value.usedFamilies.isSubset(of: value.families),
            Set(value.owners.map(\.family)).isSubset(of: value.usedFamilies)
        else { throw ClawSnapshotError.invalidState }
        var restored: [UInt32: Owner] = [:]
        for record in value.owners {
            guard let adapter = adapters[record.family] else { throw ClawSnapshotError.invalidState }
            let identity: ClawTokenHeap.AllocationIdentity
            if let reference = record.live {
                guard reference.token == record.actor, reference.count == 4, reference.interior,
                    reference.identity == record.identity, let live = plan.resolve(reference)
                else { throw ClawSnapshotError.invalidState }
                identity = live
            } else {
                guard plan.resolve(.init(token: record.actor, count: 4, identity: record.identity, interior: true)) == nil else {
                    throw ClawSnapshotError.invalidState
                }
                identity = plan.witnessIdentity(for: record.identity)
            }
            restored[record.actor] = Owner(adapter: adapter, identity: identity)
        }
        // Apply only to an off-screen candidate, with the rest of its graph,
        // before the final scene swap. No callback is invoked during apply.
        return { [self] in
            guard active == nil, host.snapshotQuiescent else { throw ClawSnapshotError.activeFrame }
            owners = restored
            usedFamilies = value.usedFamilies
        }
    }

    struct AdaptersSavedState: Codable, Equatable {
        let ownership: OwnershipSavedState
        let adapters: [String: ClawAdapterSavedState]
        let bindings: ClawNativeCanonicalHost.BindingsSavedState
    }
    private static let snapshotFamilies: Set<String> = ["ani_cycle", "boss_warp", "tower_cannon_left", "tower_cannon_right"]
    func savedAdaptersState() throws -> AdaptersSavedState {
        let ownership = try savedOwnershipState()
        guard usedFamilies.isSubset(of: Self.snapshotFamilies) else { throw ClawSnapshotError.incompleteOwners }
        var states: [String: ClawAdapterSavedState] = [:]
        for family in usedFamilies.sorted() { states[family] = try adapters[family]!.savedAdapterState() }
        return .init(ownership: ownership, adapters: states, bindings: try host.savedBindingsState())
    }
    // The candidate factory calls this before making its ONE heap plan. MFC
    // construction may install import slots; decoding never changes that plan.
    func prepareAdapterProviders(_ value: AdaptersSavedState) throws {
        guard active == nil, host.snapshotQuiescent else { throw ClawSnapshotError.activeFrame }
        guard value.ownership.usedFamilies.isSubset(of: Self.snapshotFamilies),
            usedFamilies.isSubset(of: value.ownership.usedFamilies),
            Set(value.adapters.keys) == value.ownership.usedFamilies
        else { throw ClawSnapshotError.incompleteOwners }
        for family in value.adapters.keys.sorted() {
            guard let adapter = adapters[family] else { throw ClawSnapshotError.incompleteOwners }
            try adapter.prepareAdapterProvider(value.adapters[family]!)
        }
    }
    func prepareAdaptersRestore(_ value: AdaptersSavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws -> Void {
        guard active == nil, host.snapshotQuiescent else { throw ClawSnapshotError.activeFrame }
        guard value.ownership.usedFamilies.isSubset(of: Self.snapshotFamilies),
            usedFamilies.isSubset(of: value.ownership.usedFamilies),
            Set(value.adapters.keys) == value.ownership.usedFamilies
        else { throw ClawSnapshotError.incompleteOwners }
        let ownership = try prepareOwnershipRestore(value.ownership, heap: plan)
        var installs: [() throws -> Void] = []
        for family in value.adapters.keys.sorted() {
            guard let adapter = adapters[family] else { throw ClawSnapshotError.incompleteOwners }
            let state = value.adapters[family]!
            let records = value.ownership.owners.filter { $0.family == family }
            guard Set(records.map(\.actor)) == Set(state.owners.map { $0.actor.reference.token }),
                records.allSatisfy({ record in
                    state.owners.contains { $0.actor.reference.token == record.actor && $0.actor.reference.identity == record.identity }
                })
            else { throw ClawSnapshotError.invalidState }
            installs.append(try adapter.prepareAdapterRestore(state, heap: plan))
        }
        // Adapter preparation registers candidate tower providers before binding decode.
        let bindings = try host.prepareBindingsRestore(value.bindings, heap: plan)
        return { [self] in
            guard active == nil, host.snapshotQuiescent else { throw ClawSnapshotError.activeFrame }
            try host.heap.validateInstalledRestore(plan)
            for install in installs { try install() }
            try ownership()
            try bindings()
        }
    }

    // MARK: - Election validation and service routing

    init(scene: ClawNativeScene, elections: [Election] = ClawNativeObjectConnections.elections) {
        self.scene = scene
        host = ClawNativeCanonicalHost(heap: scene.heap)
        var claimed: [UInt32: Int] = [:]
        for election in elections { for callback in election.callbacks { claimed[callback, default: 0] += 1 } }
        for election in elections {
            guard let type = Self.resolve(election) else {
                missing.append(election.family)
                continue
            }
            // Duplicate elections, a callback owned by another canonical family
            // and a service that would shadow a canonical entry all reject.
            let valid =
                !election.callbacks.isEmpty && adapters[election.family] == nil
                && election.callbacks.allSatisfy { callback in
                    guard claimed[callback] == 1, let entry = claw_canonical_lookup(callback)?.pointee else { return false }
                    // These admitted owners retain the original machine U32
                    // completion; scene callback dispatch ignores EAX.
                    let punkRat = election.family == "punk_rat" && callback == 0x474330
                    let raux = election.family == "raux" && callback == 0x47e210
                    return String(cString: entry.family) == (raux ? "level_two_raux_core" : punkRat ? "punk_rat_states" : election.family)
                        && entry.convention == UInt32(CLAW_CANONICAL_CDECL) && entry.argumentCount == 1
                        && entry.returnKind == UInt32((punkRat || raux) ? CLAW_CANONICAL_RETURN_U32 : CLAW_CANONICAL_RETURN_VOID)
                } && type.services.allSatisfy { claw_canonical_lookup($0) == nil }
            guard valid else {
                reject(election.callbacks.first ?? 0)
                continue
            }
            let adapter = type.init(connections: self, election: election)
            adapters[election.family] = adapter
            for callback in election.callbacks { byCallback[callback] = adapter }
        }
        if scene.heap.lookup(0x5430c4, words: 1) == nil { scene.heap.store(token: 0x5430c4, words: 1) }
        host.observer = { [weak self] call in
            guard let self, self.recordsTrace, self.active != nil else { return }
            self.calls.append(call)
        }
        host.dependency = { [weak self] host, call in
            guard let self, self.host === host, let adapter = self.active,
                type(of: adapter).services.contains(call.function)
            else { return nil }
            return adapter.service(call)
        }
    }
    func adapter(_ family: String) -> ClawNativeObjectAdapter? { adapters[family] }
    func owner(of actor: UInt32) -> String? { owners[actor]?.adapter.election.family }
    var ownedActors: Set<UInt32> { Set(owners.keys) }
    func record(_ event: String) { if recordsTrace { trace.append(event) } }

    // MARK: - Actor attachment and synchronous callback lifetime

    func attach(_ object: ClawInteractionActor, callback: UInt32) {
        guard let adapter = byCallback[callback], owners[object.token] == nil,
            let identity = host.heap.containingAllocationIdentity(at: object.token, count: 4)
        else {
            reject(object.token)
            return
        }
        record("loadGridObject")
        usedFamilies.insert(adapter.election.family)
        guard adapter.attach(object, callback: callback) else {
            reject(object.token)
            return
        }
        owners[object.token] = Owner(adapter: adapter, identity: identity)
    }
    func remove(_ actor: UInt32) {
        guard let owner = owners.removeValue(forKey: actor) else { return }
        owner.adapter.remove(actor)
    }
    func callback(_ function: UInt32, actor: UInt32) {
        guard let scene, scene.heap === host.heap, let adapter = byCallback[function] else {
            reject(function)
            return
        }
        guard host.fault == nil else { return }
        guard active == nil, let owner = owners[actor], owner.adapter === adapter,
            host.heap.containingAllocationIdentity(at: actor, count: 4) === owner.identity
        else {
            reject(actor)
            return
        }
        adapter.callbackCompletion = nil
        record("scene.gameplay")
        guard let clock = host.heap.lookup(0x5430c4, words: 1) else {
            host.fail(UInt32(CLAW_FAULT_MEMORY), at: 0x5430c4)
            return
        }
        clock.pointee = scene.animationDelta
        // Only this synchronous callback may use the adapter service set.
        // Restore both pieces of authority even when the callback faults.
        active = adapter
        host.stacklessCallerReserve = type(of: adapter).stacklessCallerReserve
        defer {
            active = nil
            host.stacklessCallerReserve = nil
        }
        adapter.callback(function, actor: actor)
    }
    func reject(_ address: UInt32) { host.fail(UInt32(CLAW_FAULT_ABI), at: address, diagnostic: .unsupportedABI) }
}
