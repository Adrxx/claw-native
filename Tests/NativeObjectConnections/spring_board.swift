import Foundation

private let observed: Set<UInt32> = [0x4c79e0, 0x4c82a0, 0x4f6286, 0x41e810, 0x41c4e0, 0x4208b0, 0x4170b0, 0x420dd0, 0x4208e0]
private func require(_ value: Bool, _ message: String) { precondition(value, message) }
private func word(_ heap: ClawTokenHeap, _ token: UInt32) -> UInt32 { heap.lookup(token, words: 1)!.pointee }
private func put(_ heap: ClawTokenHeap, _ token: UInt32, _ value: UInt32) { heap.lookup(token, words: 1)!.pointee = value }
private func segment(_ heap: ClawTokenHeap, _ token: UInt32, _ count: UInt32) -> [String: Any] {
    let bytes = heap.lookupBytes(token, count: count)!
    return ["address": token, "hex": Data(bytes: bytes, count: Int(count)).map { String(format: "%02x", $0) }.joined()]
}
private func graph(_ heap: ClawTokenHeap) -> [(UInt32, UInt32)] {
    heap.debugAllocationBases.compactMap { token in
        // PCM samples, image surfaces and spatial grids are not touched by this join.
        if heap.lookupBytes(token, count: 4097) != nil { return nil }
        var low: UInt32 = 1, high: UInt32 = 4096
        while low < high {
            let middle = low + (high - low + 1) / 2
            if heap.lookupBytes(token, count: middle) != nil { low = middle } else { high = middle - 1 }
        }
        return (token, low)
    }
}
private func arguments(_ call: ClawCall) -> [UInt32] {
    withUnsafeBytes(of: call.arguments) {
        Array($0.bindMemory(to: UInt32.self).prefix(Int(call.function == 0x4f6286 ? 1 : call.argumentCount)))
    }
}

func runConnection(_ supplied: URL) throws {
    let directory = supplied.standardizedFileURL, root = directory.appendingPathComponent("assets")
    let level = try ClawLevelScene(root: root), assets = try ClawPlayerAssets(root: root)
    let world = try ClawWorld(data: Data(contentsOf: directory.appendingPathComponent("WORLD4.WWD")))
    guard let record = world.planes.flatMap(\.objects).first(where: { $0.logic == "SpringBoard" && $0.imageSet == "LEVEL_SPRINGYFERN" }) else {
        preconditionFailure("Original Level 4 SpringBoard record")
    }
    func scene() throws -> ClawNativeScene {
        let value = ClawNativeScene(player: try ClawNativePlayer(world: level.world, assets: assets), clock: { 1000 })
        try value.loadRecoveredObjects(world: level.world, root: root, level: 4)
        require(value.fault == 0, "Scene setup")
        let audio = value.player.audio!
        audio.routing.masterVolume = 0
        audio.routing.managerAvailable = 0
        require(!audio.outputEnabled, "Offline muted sound output")
        for name in ["RUSTLE", "SPRING"] {
            if audio.resolve(name: "LEVEL_SPRINGYFERN_" + name) == nil {
                try audio.load(name: "LEVEL_SPRINGYFERN_" + name,
                    data: Data(contentsOf: root.appendingPathComponent("LEVEL1/SOUNDS/SPRINGYFERN/\(name).WAV")))
            }
            let sound = audio.resolve(name: "LEVEL_SPRINGYFERN_" + name)!
            put(value.heap, sound.resourceToken + 12, value.sceneIdentity)
        }
        for name in ["LEVEL_SPRINGYFERN_IDLE", "LEVEL_SPRINGYFERN_SPRING", "CLAW_JUMP"] {
            let loaded = try value.objectResources!.sequence(name: name)
            require(loaded != nil, "Real ANI: \(name)")
        }
        value.objectConnections!.recordsTrace = true
        return value
    }
    func attach(_ runtime: ClawNativeScene) -> UInt32 {
        let bridge = runtime.objectConnections!, before = bridge.ownedActors
        let index = level.world.planes.firstIndex(where: { $0.flags & 1 != 0 })!
        let plane = runtime.camera!.planeTokens[index]
        let count = runtime.loadGridObject(record, world: world, plane: plane)
        require(count == record.encodedRecord.count && runtime.fault == 0,
            "loadGridObject SpringBoard: \(runtime.objectLoadingFailure ?? "") / \(String(describing: bridge.host.fault))")
        let added = bridge.ownedActors.subtracting(before)
        require(added.count == 1, "One attached SpringBoard")
        return added.first!
    }
    func dispatch(_ runtime: ClawNativeScene, _ actor: UInt32, delta: UInt32) {
        var timing = ClawPlayerDeathCommandGlobals()
        runtime.captureDeathTiming(&timing); timing.animation.deltaMilliseconds = delta
        runtime.publishDeathTiming(timing)
        var call = ClawSceneActorCall()
        call.function = 0x49db90; call.argumentCount = 1; call.arguments.0 = actor
        let host = runtime.actorHost
        _ = host.call!(host.context, call)
    }
    let runtime = try scene(), actor = attach(runtime), heap = runtime.heap, bridge = runtime.objectConnections!
    let state = word(heap, actor + 0x6c), player: UInt32 = 0x10002000
    var inputs: [[String: Any]] = [], outputs: [[String: Any]] = []
    var bindings: [[String: Any]] = []
    for name in ["LEVEL_SPRINGYFERN_IDLE", "LEVEL_SPRINGYFERN_SPRING", "CLAW_JUMP"] {
        let sequence = try runtime.objectResources!.sequence(name: name)!
        bindings.append(["receiver": word(heap, runtime.sceneIdentity + 0x2c) + 16, "name": name, "token": sequence.token])
    }
    func contact(_ supported: Bool) {
        var snapshot = runtime.player.sceneSnapshot()
        snapshot.actor.2 = supported ? snapshot.actor.2 | 0x10 : snapshot.actor.2 & ~UInt32(0x10)
        snapshot.actor.32 = supported ? actor : 0
        runtime.player.acceptSceneSnapshot(snapshot)
        runtime.write(snapshot)
    }
    func step(_ name: String, _ delta: UInt32) {
        // Supply the same physical scene boundary to the original callback.
        // These are input/global transport values, never SpringBoard decisions.
        put(heap, 0x5430c4, delta)
        put(heap, 0x537e88, player)
        put(heap, 0x537204, runtime.camera!.inputToken)
        put(heap, runtime.camera!.inputToken + 12, runtime.player.runtime.inputLatched)
        put(heap, 0x534eac, runtime.player.runtime.powerup)
        put(heap, 0x532c0c, runtime.player.audio!.routing.managerAvailable)
        put(heap, 0x532c10, runtime.player.audio!.routing.masterVolume)
        withUnsafeBytes(of: runtime.player.runtime.physics) {
            heap.lookupBytes(0x534db8, count: UInt32($0.count))!.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: $0.count)
        }
        let spans = graph(heap)
        let ordinary = spans.filter { $0.0 >= 0x10000000 }, globals = spans.filter { $0.0 < 0x10000000 }
        inputs.append(["name": name, "actor": actor,
            "segments": ordinary.map { segment(heap, $0.0, $0.1) },
            "globals": globals.map { segment(heap, $0.0, $0.1) }, "resourceBindings": bindings])
        let start = bridge.calls.count
        dispatch(runtime, actor, delta: delta)
        require(runtime.fault == 0 && bridge.host.fault == nil && runtime.unresolvedDependencies.isEmpty,
            "SpringBoard \(name): \(String(describing: bridge.host.fault)) / \(runtime.unresolvedDependencies)")
        require(graph(heap).map { $0.0 } == spans.map { $0.0 }, "Prewarmed physical resources do not allocate inside the callback")
        outputs.append(["name": name,
            "segments": ordinary.map { segment(heap, $0.0, $0.1) },
            "globals": globals.map { segment(heap, $0.0, $0.1) },
            "services": bridge.calls.dropFirst(start).filter { observed.contains($0.function) }.map {
                ["function": $0.function, "receiver": $0.receiver, "arguments": arguments($0)] as [String: Any]
            }])
    }
    contact(false)
    step("initialize", 0)
    require(word(heap, state + 0x1c) == 5, "Initialized idle state")
    step("absent-contact", 17)
    require(word(heap, state + 0x1c) == 5, "Absent contact stays idle")
    contact(true)
    step("landing", 0)
    require(word(heap, state + 0x1c) == 6 && word(heap, state + 0x64) == 1, "Landing arms one impulse")
    step("spring-first-frame", 0)
    step("spring-sound-frame", 51)
    require(bridge.calls.contains { $0.function == 0x4208e0 }, "Real fern sound event reaches canonical audio owner")
    step("first-impulse", 51)
    require(word(heap, state + 0x64) == 0 && word(heap, player + 8) & 0x10 == 0,
        "Impulse consumes latch and releases support")
    require(word(heap, word(heap, player + 0x6c) + 0x1c) == 4, "Real player jump state")
    step("repeated-frame", 0)
    for index in 0..<8 { step("completion-progress-\(index)", 76) }
    step("animation-completion", 0)
    require(word(heap, state + 0x1c) == 5, "Completed spring returns to idle")
    let order = ["loadGridObject", "scene.gameplay", "ClawNativeSpringBoard", "0x49db90"]
    let positions = order.map { bridge.trace.firstIndex(of: $0) ?? -1 }
    let physics = withUnsafeBytes(of: runtime.player.runtime.physics) { Data($0) }
    let heapPhysics = Data(bytes: heap.lookupBytes(0x534db8, count: UInt32(physics.count))!, count: physics.count)
    var controls: [String: Bool] = ["scene_trace": !positions.contains(-1) && positions == positions.sorted(),
        "single_impulse": bridge.calls.filter { $0.function == 0x41e810 }.count == 1,
        "player_physics_imported": runtime.player.runtime.logicState == 4 && physics == heapPhysics]
    var forged = ClawCall(); forged.function = 0x4f6286; forged.receiver = 0x63000010; forged.argumentCount = 2
    forged.arguments.0 = word(heap, 0x537960) + 4; forged.arguments.1 = UInt32(CLAW_STACK_TOP) - 4
    controls["out_of_callback_service_rejected"] = bridge.adapter("spring_board")!.service(forged) == nil
    let missing = try scene(), missingActor = attach(missing)
    missing.objectConnections!.host.dependency = nil
    dispatch(missing, missingActor, delta: 0)
    controls["missing_service_fault"] = missing.objectConnections!.host.fault?.diagnostic == .missingDependency &&
        missing.objectConnections!.host.fault?.address == 0x4f6286 && missing.fault != 0
    let stale = try scene(), staleActor = attach(stale)
    let old = Data(bytes: stale.heap.lookupBytes(staleActor, count: 0x1b4)!, count: 0x1b4)
    stale.heap.free(staleActor)
    old.withUnsafeBytes { stale.heap.storeBytes(token: staleActor, count: 0x1b4).update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 0x1b4) }
    dispatch(stale, staleActor, delta: 0)
    controls["replacement_allocation_rejected"] = stale.objectConnections!.host.fault != nil && stale.objectConnections!.calls.isEmpty
    let retired = try scene(), retiredActor = attach(retired)
    var destruction = ClawSceneActorCall(); destruction.function = 0x4c9be0; destruction.receiver = retiredActor
    destruction.argumentCount = 1; destruction.arguments.0 = 1
    let host = retired.actorHost; _ = host.call!(host.context, destruction)
    controls["scene_destruction_retires_owner"] = retired.fault == 0 && retired.objectConnections!.owner(of: retiredActor) == nil
    dispatch(retired, retiredActor, delta: 0)
    controls["retired_owner_rejected"] = retired.objectConnections!.host.fault != nil
    require(controls.values.allSatisfy { $0 }, "SpringBoard ownership controls: \(controls)")
    let input: [String: Any] = ["profiles": inputs]
    let output: [String: Any] = ["profiles": outputs, "controls": controls, "trace": bridge.trace,
        "faults": runtime.fault, "unresolvedDependencies": runtime.unresolvedDependencies.sorted(),
        "physicalInputs": "Original Level 4 SpringBoard WWD and SpringyFern ANI/PID/WAV; Level 4 source profile in existing Level 1 scene; real audio event tokens with physical audio manager unavailable; controlled player support boundary, no full-level, enabled-audio or physical-device claim"]
    try JSONSerialization.data(withJSONObject: input, options: [.sortedKeys]).write(to: directory.appendingPathComponent("spring-input.json"))
    try JSONSerialization.data(withJSONObject: output, options: [.sortedKeys]).write(to: directory.appendingPathComponent("spring-output.json"))
}
