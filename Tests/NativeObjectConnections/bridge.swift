import Foundation

// Shared bridge controls. They run the real AniCycle adapter and canonical
// callback; control adapters only change elections or declared services and
// never script a game result.
@objc(ClawBridgeProbe) final class ClawBridgeProbe: ClawNativeObjectAdapter {}
@objc(ClawBridgeAniCycleWithoutResource) final class ClawBridgeAniCycleWithoutResource: ClawNativeAniCycle {
    override class var services: Set<UInt32> { [] }
}
@objc(ClawBridgeCanonicalShadow) final class ClawBridgeCanonicalShadow: ClawNativeAniCycle {
    override class var services: Set<UInt32> { [0x4f6286, 0x4c79e0] }
}

private func bridgeRequire(_ condition: @autoclosure () -> Bool, _ message: String) {
    precondition(condition(), message)
}

func runBridgeControls(_ directory: URL) throws {
    typealias Election = ClawNativeObjectConnections.Election
    let root = URL(fileURLWithPath: "App/GameData")
    let level = try ClawLevelScene(root: root), assets = try ClawPlayerAssets(root: root)
    let world = try ClawWorld(data: Data(contentsOf: directory.appendingPathComponent("WORLD2.WWD")))
    let record = world.planes[1].objects[405]
    bridgeRequire(record.logic == "AniCycle" && record.id == 4481, "Original WWD AniCycle record")
    let aniCycle = Election(family: "ani_cycle", adapter: "ClawNativeAniCycle", callbacks: [0x4918b0])
    func scene(_ elections: [Election]? = nil) throws -> ClawNativeScene {
        let value = ClawNativeScene(player: try ClawNativePlayer(world: level.world, assets: assets), clock: { 1000 })
        try value.loadRecoveredObjects(world: level.world, root: root)
        bridgeRequire(value.fault == 0, "Scene setup")
        if let elections { value.installObjectConnections(elections) }
        value.objectConnections!.recordsTrace = true
        return value
    }
    func attach(_ runtime: ClawNativeScene) -> UInt32? {
        let before = runtime.objectConnections!.ownedActors
        let plane = runtime.heap.lookup(runtime.worldIdentity, words: 24)![23]
        guard runtime.loadGridObject(record, world: world, plane: plane) == record.encodedRecord.count,
              runtime.fault == 0 else { return nil }
        let added = runtime.objectConnections!.ownedActors.subtracting(before)
        return added.count == 1 ? added.first : nil
    }
    func dispatch(_ runtime: ClawNativeScene, _ actor: UInt32) {
        var call = ClawSceneActorCall()
        call.function = 0x4918b0; call.argumentCount = 1; call.arguments.0 = actor
        let host = runtime.actorHost
        _ = host.call!(host.context, call)
    }
    var controls: [String: Bool] = [:]

    // Explicit dispatch through the adapter, then scene destruction teardown.
    let joined = try scene()
    let bridge = joined.objectConnections!
    if let actor = attach(joined) {
        dispatch(joined, actor)
        let order = ["loadGridObject", "scene.gameplay", "ClawNativeAniCycle", "0x4918b0"]
        let positions = order.map { bridge.trace.firstIndex(of: $0) ?? -1 }
        let dispatched = joined.fault == 0 && bridge.host.fault == nil && bridge.owner(of: actor) == "ani_cycle" &&
            !positions.contains(-1) && positions == positions.sorted()
        var destruction = ClawSceneActorCall()
        destruction.function = 0x4c9be0; destruction.receiver = actor
        destruction.argumentCount = 1; destruction.arguments.0 = 1
        let host = joined.actorHost
        _ = host.call!(host.context, destruction)
        let retired = joined.fault == 0 && bridge.ownedActors.isEmpty && bridge.owner(of: actor) == nil &&
            (bridge.adapter("ani_cycle") as! ClawNativeAniCycle).tokens.isEmpty
        dispatch(joined, actor)
        controls["adapter_dispatch_and_teardown"] = dispatched && retired && bridge.host.fault != nil
    } else { controls["adapter_dispatch_and_teardown"] = false }

    // Canonical entries win: the dependency hook is only offered native services.
    let precedence = try scene()
    var offered: [UInt32] = []
    if let actor = attach(precedence) {
        let host = precedence.objectConnections!.host, inner = host.dependency
        host.dependency = { value, call in offered.append(call.function); return inner?(value, call) }
        dispatch(precedence, actor)
    }
    let shadow = try scene([Election(family: "ani_cycle", adapter: "ClawBridgeCanonicalShadow", callbacks: [0x4918b0])])
    let observed = precedence.objectConnections!.calls.map(\.function)
    controls["canonical_precedence"] = precedence.fault == 0 && !offered.isEmpty &&
        offered.allSatisfy { claw_canonical_lookup($0) == nil && ClawNativeAniCycle.services.contains($0) } &&
        observed.contains { claw_canonical_lookup($0) != nil } && !offered.contains { claw_canonical_lookup($0) != nil } &&
        shadow.objectConnections!.host.fault != nil && shadow.objectConnections!.callbacks.isEmpty && shadow.fault != 0

    // Two elections for one callback, or one family elected twice, reject both.
    let duplicate = try scene([aniCycle, Election(family: "ani_cycle", adapter: "ClawBridgeProbe", callbacks: [0x4918b0])])
    controls["duplicate_callback_rejected"] = duplicate.objectConnections!.host.fault != nil &&
        !duplicate.objectConnections!.callbacks.contains(0x4918b0) && duplicate.fault != 0

    // A callback another native scene owner already dispatches is never displaced.
    let owned = try scene()
    owned.installObjectConnections([aniCycle], registerGameplay: false)
    let installed = owned.objectConnections!.adapter("ani_cycle") != nil && owned.fault == 0
    var otherOwnerCalls = 0
    owned.gameplay[0x4918b0] = { _ in otherOwnerCalls += 1 }
    owned.registerObjectConnectionGameplay()
    owned.gameplay[0x4918b0]?(0)
    controls["scene_owner_callback_not_displaced"] = installed && owned.objectConnections!.host.fault != nil && owned.fault != 0 &&
        otherOwnerCalls == 1

    // Unknown callbacks and a family that is not the callback's canonical owner reject.
    let unknown = try scene()
    unknown.objectConnections!.callback(0x491930, actor: 0)
    let mismatch = try scene([Election(family: "boss_warp", adapter: "ClawNativeAniCycle", callbacks: [0x4918b0])])
    controls["unknown_callback_rejected"] = unknown.objectConnections!.host.fault?.address == 0x491930 &&
        mismatch.objectConnections!.host.fault != nil && mismatch.objectConnections!.callbacks.isEmpty

    // An actor dispatched to an adapter that never attached it rejects.
    let stray = try scene()
    dispatch(stray, stray.sceneIdentity)
    controls["unowned_actor_rejected"] = stray.objectConnections!.host.fault != nil && stray.fault != 0

    // An absent adapter class is a missing implementation, not a fault.
    let absent = try scene([aniCycle, Election(family: "boss_warp", adapter: "ClawBridgeAbsentAdapter", callbacks: [0x470870])])
    controls["missing_implementation_reported"] = absent.fault == 0 && absent.objectConnections!.host.fault == nil &&
        absent.objectConnections!.missing == ["boss_warp"] && absent.objectConnections!.callbacks == [0x4918b0]

    // A service the adapter did not declare is a missing dependency fault.
    let narrow = try scene([Election(family: "ani_cycle", adapter: "ClawBridgeAniCycleWithoutResource", callbacks: [0x4918b0])])
    if let actor = attach(narrow) {
        dispatch(narrow, actor)
        controls["missing_service_fault"] = narrow.objectConnections!.host.fault?.diagnostic == .missingDependency &&
            narrow.objectConnections!.host.fault?.address == 0x4f6286 && narrow.fault != 0
    } else { controls["missing_service_fault"] = false }

    try JSONSerialization.data(withJSONObject: ["controls": controls], options: [.prettyPrinted, .sortedKeys])
        .write(to: directory.appendingPathComponent("bridge-controls.json"))
    bridgeRequire(controls.values.allSatisfy { $0 }, "Bridge controls: \(controls)")
}
