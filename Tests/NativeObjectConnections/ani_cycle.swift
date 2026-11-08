import Foundation

func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    precondition(condition(), message)
}
func hex(_ data: Data) -> String { data.map { String(format: "%02x", $0) }.joined() }
func segment(_ heap: ClawTokenHeap, _ address: UInt32, _ count: UInt32) -> [String: Any] {
    guard let bytes = heap.lookupBytes(address, count: count) else { fatalError("Missing export span \(address) / \(count)") }
    return ["address": address, "hex": hex(Data(bytes: bytes, count: Int(count)))]
}
func alias(_ record: ClawWorld.Object) -> ClawWorld.Object {
    let name = "AniCycleNormal"
    var words = record.words
    let prefix = 284 + Int(words[1]), end = prefix + Int(words[2])
    let replacement = Array(name.utf8) + [UInt8(0)]
    words[2] = UInt32(replacement.count)
    var bytes = record.encodedRecord
    bytes.replaceSubrange(prefix..<end, with: replacement)
    var length = words[2].littleEndian
    withUnsafeBytes(of: &length) { bytes.replaceSubrange(8..<12, with: $0) }
    return ClawWorld.Object(words: words, encodedRecordOffset: record.encodedRecordOffset,
        encodedRecord: bytes, name: record.name, logic: name, imageSet: record.imageSet, sound: record.sound)
}

func aniCycleAdapter(_ scene: ClawNativeScene) -> ClawNativeAniCycle {
    scene.objectConnections!.adapter("ani_cycle") as! ClawNativeAniCycle
}

func runConnection(_ directory: URL) throws {
    let root = URL(fileURLWithPath: "App/GameData")
    let level = try ClawLevelScene(root: root), assets = try ClawPlayerAssets(root: root)
    let originalWorld = try ClawWorld(data: Data(contentsOf: directory.appendingPathComponent("WORLD2.WWD")))
    let record = originalWorld.planes[1].objects[405]
    check(record.logic == "AniCycle" && record.id == 4481 && record.sound.isEmpty, "Original WWD pilot")
    func scene() throws -> ClawNativeScene {
        let value = ClawNativeScene(player: try ClawNativePlayer(world: level.world, assets: assets), clock: { 1000 })
        try value.loadRecoveredObjects(world: level.world, root: root)
        check(value.fault == 0, "Scene setup")
        value.objectConnections!.recordsTrace = true
        return value
    }
    func attach(_ runtime: ClawNativeScene, _ object: ClawWorld.Object) -> UInt32 {
        let before = aniCycleAdapter(runtime).tokens
        let plane = runtime.heap.lookup(runtime.worldIdentity, words: 24)![23]
        check(runtime.loadGridObject(object, world: originalWorld, plane: plane) == object.encodedRecord.count, "loadGridObject")
        check(runtime.fault == 0, "Object load service fault")
        let added = aniCycleAdapter(runtime).tokens.subtracting(before)
        check(added.count == 1, "Exactly one native owner")
        return added.first!
    }
    func dispatch(_ runtime: ClawNativeScene, _ actor: UInt32, delta: UInt32) {
        var timing = ClawPlayerDeathCommandGlobals()
        runtime.captureDeathTiming(&timing); timing.animation.deltaMilliseconds = delta
        runtime.publishDeathTiming(timing)
        var call = ClawSceneActorCall()
        call.function = 0x4918b0; call.argumentCount = 1; call.arguments.0 = actor
        let host = runtime.actorHost
        _ = host.call!(host.context, call)
    }
    let runtime = try scene()
    var inputs: [[String: Any]] = [], outputs: [[String: Any]] = []
    for object in [record, alias(record)] {
        let actor = attach(runtime, object), heap = runtime.heap
        let owner = runtime.objectConnections!, body = aniCycleAdapter(runtime)
        let privateToken = heap.lookup(actor + 0x6c, words: 1)!.pointee
        check(heap.lookup(actor + 0x190, words: 1)!.pointee == 0, "Phase 0 starts without sequence")
        check(heap.lookup(privateToken + 0x1c, words: 1)!.pointee == 0, "Phase 0")
        let sequence = try runtime.objectResources!.sequence(name: "GAME_CYCLE100")!
        let seq = heap.lookup(sequence.token, words: 5)!, table = heap.lookup(seq[3], words: seq[4])!
        var ranges: [(UInt32, UInt32)] = [(actor, 0x1b4), (privateToken, 0x174), (runtime.sceneIdentity, 60),
            (sequence.token, 20), (seq[3], seq[4] * 4)]
        for index in 0..<Int(seq[4]) { ranges.append((table[index], 48)) }
        let imageToken = heap.lookup(actor + 0x170, words: 1)!.pointee
        check(imageToken != 0, "Real Level 1 physical image binding")
        let images = heap.lookup(imageToken, words: 27)!
        ranges.append((imageToken, 108)); ranges.append((images[5], images[6] * 4))
        let globals: [[String: Any]] = [["address": UInt32(0x5430c4), "hex": "00000000"], ["address": UInt32(0x532c10), "hex": "00000000"]]
        let profile: [String: Any] = ["name": object.logic, "className": object.logic, "actor": actor,
            "segments": ranges.map { segment(heap, $0.0, $0.1) }, "globals": globals,
            "resourceBindings": [["receiver": UInt32(0x63000010), "name": "GAME_CYCLE100", "token": sequence.token]],
            "steps": [["delta": 0], ["delta": 17], ["delta": 113]]]
        inputs.append(profile)
        var steps: [[String: Any]] = []
        for delta: UInt32 in [0, 17, 113] {
            let start = body.calls.count
            dispatch(runtime, actor, delta: delta)
            check(runtime.fault == 0 && owner.host.fault == nil, "Joined callback completed")
            check(runtime.unresolvedDependencies.isEmpty, "No unresolved dependencies")
            let services = body.calls.dropFirst(start).map { call -> [String: Any] in
                var args: [UInt32] = []
                withUnsafeBytes(of: call.arguments) { bytes in
                    // The output pointer is a stack alias; the token it receives is compared in memory.
                    for index in 0..<Int(call.function == 0x4f6286 ? 1 : call.argumentCount) { args.append(bytes.load(fromByteOffset: index * 4, as: UInt32.self)) }
                }
                return ["function": call.function, "receiver": call.receiver, "arguments": args]
            }
            steps.append(["delta": delta, "actorHex": segment(heap, actor, 0x1b4)["hex"]!,
                "privateHex": segment(heap, privateToken, 0x174)["hex"]!,
                "segments": ranges.map { segment(heap, $0.0, $0.1) },
                "globals": [segment(heap, 0x5430c4, 4), ["address": UInt32(0x532c10), "hex": "00000000"]],
                "services": services])
        }
        outputs.append(["name": object.logic, "className": object.logic, "actor": actor, "steps": steps])
    }
    check(runtime.objectConnections!.trace.contains("ClawActorResources.0x4f6286"), "Real physical owner reached")
    var controls: [String: Bool] = [:]
    // A valid service envelope outside its active owner must not gain authority.
    var forged = ClawCall(); forged.function = 0x4f6286; forged.argumentCount = 2
    forged.receiver = 0x63000010; forged.arguments.0 = 0x5240d8; forged.arguments.1 = UInt32(CLAW_STACK_TOP) - 4
    controls["out_of_callback_service_rejected"] = aniCycleAdapter(runtime).service(forged) == nil
    let missingActor = attach(runtime, record)
    runtime.objectConnections!.host.dependency = nil
    dispatch(runtime, missingActor, delta: 0)
    controls["missing_service_fault"] = runtime.objectConnections!.host.fault?.diagnostic == .missingDependency && runtime.objectConnections!.host.fault?.address == 0x4f6286 && runtime.fault != 0
    let stale = try scene(), staleActor = attach(stale, record)
    let bytes = Data(bytes: stale.heap.lookupBytes(staleActor, count: 0x1b4)!, count: 0x1b4)
    stale.heap.free(staleActor)
    bytes.withUnsafeBytes { stale.heap.storeBytes(token: staleActor, count: 0x1b4).update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 0x1b4) }
    dispatch(stale, staleActor, delta: 0)
    controls["replacement_allocation_rejected"] = stale.objectConnections!.host.fault != nil && aniCycleAdapter(stale).calls.isEmpty
    let removed = try scene(), removedActor = attach(removed, record)
    var destruction = ClawSceneActorCall()
    destruction.function = 0x4c9be0; destruction.receiver = removedActor
    destruction.argumentCount = 1; destruction.arguments.0 = 1
    let destructionHost = removed.actorHost
    _ = destructionHost.call!(destructionHost.context, destruction)
    controls["scene_destruction_retires_owner"] = removed.fault == 0 &&
        removed.heap.lookup(removedActor, words: 1) == nil && !aniCycleAdapter(removed).tokens.contains(removedActor)
    let callsBeforeRetired = aniCycleAdapter(removed).calls.count
    dispatch(removed, removedActor, delta: 0)
    controls["retired_owner_rejected"] = removed.objectConnections!.host.fault != nil && aniCycleAdapter(removed).calls.count == callsBeforeRetired
    let other = try scene()
    other.objectConnections!.callback(0x491930, actor: 0)
    controls["unelected_callback_rejected"] = other.objectConnections!.host.fault != nil && aniCycleAdapter(other).calls.isEmpty
    check(controls.values.allSatisfy { $0 }, "Ownership controls")
    let input: [String: Any] = ["profiles": inputs]
    let output: [String: Any] = ["profiles": outputs, "controls": controls,
        "trace": runtime.objectConnections!.trace, "faults": 0, "unresolvedDependencies": [],
        "physicalInputs": "Original Level 2 WWD id 4481 in existing Level 1 scene resources; alias changes only logic spelling; no Level 2 rendering claim"]
    try JSONSerialization.data(withJSONObject: input, options: [.prettyPrinted, .sortedKeys]).write(to: directory.appendingPathComponent("native-input.json"))
    try JSONSerialization.data(withJSONObject: output, options: [.prettyPrinted, .sortedKeys]).write(to: directory.appendingPathComponent("native-output.json"))
}
