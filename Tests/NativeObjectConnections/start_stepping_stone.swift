import Foundation

private func require(_ value: Bool, _ message: String) { precondition(value, message) }
private func word(_ heap: ClawTokenHeap, _ address: UInt32) -> UInt32 { heap.lookup(address, words: 1)!.pointee }
private func put(_ heap: ClawTokenHeap, _ address: UInt32, _ value: UInt32) { heap.lookup(address, words: 1)!.pointee = value }
private func segment(_ heap: ClawTokenHeap, _ address: UInt32, _ count: UInt32) -> [String: Any] {
    let bytes = heap.lookupBytes(address, count: count)!
    return ["address": address, "hex": Data(bytes: bytes, count: Int(count)).map { String(format: "%02x", $0) }.joined()]
}
private func arguments(_ call: ClawCall) -> [UInt32] {
    withUnsafeBytes(of: call.arguments) {
        Array($0.bindMemory(to: UInt32.self).prefix(Int(call.function == 0x4f6286 ? 1 : call.argumentCount)))
    }
}
private func adapter(_ scene: ClawNativeScene) -> ClawNativeStartSteppingStone {
    scene.objectConnections!.adapter("start_stepping_stone") as! ClawNativeStartSteppingStone
}

func runConnection(_ supplied: URL) throws {
    let directory = supplied.standardizedFileURL, root = directory.appendingPathComponent("assets")
    let level = try ClawLevelScene(root: root), assets = try ClawPlayerAssets(root: root)
    let world = try ClawWorld(data: Data(contentsOf: directory.appendingPathComponent("WORLD4.WWD")))
    let record = world.planes[1].objects[988]
    require(record.logic == "StartSteppingStone" && record.id == 1545 && record.imageSet == "LEVEL_STEPPINGSTONE",
        "Original Level 4 StartSteppingStone record")
    func scene() throws -> ClawNativeScene {
        let result = ClawNativeScene(player: try ClawNativePlayer(world: level.world, assets: assets), clock: { 1000 })
        try result.loadRecoveredObjects(world: level.world, root: root, level: 4)
        require(result.fault == 0, "Scene setup")
        for name in ["GAME_FORWARD50", "GAME_BACKWARD50"] {
            let sequence = try result.objectResources!.sequence(name: name)
            require(sequence != nil, "Original sequence \(name)")
        }
        result.objectConnections!.recordsTrace = true
        return result
    }
    func attach(_ runtime: ClawNativeScene) -> UInt32 {
        let before = adapter(runtime).tokens
        let index = level.world.planes.firstIndex(where: { $0.flags & 1 != 0 })!
        let plane = runtime.camera!.planeTokens[index]
        let consumed = runtime.loadGridObject(record, world: world, plane: plane)
        require(consumed == record.encodedRecord.count && runtime.fault == 0,
            "loadGridObject: \(runtime.objectLoadingFailure ?? "") / \(String(describing: runtime.objectConnections!.host.fault))")
        let added = adapter(runtime).tokens.subtracting(before)
        require(added.count == 1, "Exactly one scene-owned stone")
        return added.first!
    }
    func dispatch(_ runtime: ClawNativeScene, _ actor: UInt32, _ delta: UInt32) {
        var timing = ClawPlayerDeathCommandGlobals()
        runtime.captureDeathTiming(&timing); timing.animation.deltaMilliseconds = delta
        runtime.publishDeathTiming(timing)
        var call = ClawSceneActorCall()
        call.function = 0x49eb30; call.argumentCount = 1; call.arguments.0 = actor
        let host = runtime.actorHost
        _ = host.call!(host.context, call)
    }

    var inputs: [[String: Any]] = [], outputs: [[String: Any]] = []
    var controls: [String: Bool] = [:], traces: [String] = []
    for changedSelection in [false, true] {
        let runtime = try scene(), actor = attach(runtime), heap = runtime.heap, bridge = runtime.objectConnections!
        let state = word(heap, actor + 0x6c), player: UInt32 = 0x10002000
        let playerLogic = word(heap, player + 0x6c), playerPrivate = word(heap, playerLogic + 0x14)
        let selection = playerPrivate + 0x80, savedSelection: UInt32 = 0x1234
        let imageToken = word(heap, actor + 0x170)
        require(imageToken != 0, "Real image collection is linked")
        let images = heap.lookup(imageToken, words: 27)!
        require(images[25] == 1 && images[26] == 6, "Original six-frame stepping stone geometry")
        var ranges: [(UInt32, UInt32)] = [(actor, 0x1b4), (state, 0x174), (runtime.sceneIdentity, 60),
            (player, 0x1b4), (playerLogic, 0x174), (playerPrivate, 0x138),
            (imageToken, 108), (images[5], images[6] * 4)]
        for index in Int(images[25])...Int(images[26]) {
            ranges.append((word(heap, images[5] + UInt32(index * 4)), 64))
        }
        var bindings: [[String: Any]] = []
        for name in ["GAME_FORWARD50", "GAME_BACKWARD50"] {
            let sequence = try runtime.objectResources!.sequence(name: name)!
            let seq = heap.lookup(sequence.token, words: 5)!, records = heap.lookup(seq[3], words: seq[4])!
            ranges += [(sequence.token, 20), (seq[3], seq[4] * 4)]
            for index in 0..<Int(seq[4]) { ranges.append((records[index], 48)) }
            bindings.append(["receiver": word(heap, runtime.sceneIdentity + 0x2c) + 16, "name": name, "token": sequence.token])
        }
        let globalRanges: [(UInt32, UInt32)] = [(0x5378a0, 200), (0x537e88, 4), (0x5430c4, 4)]
        require(word(heap, 0x537960) == 0x5378a0 && word(heap, 0x537e88) == player, "Source level and scene player aliases")
        put(heap, selection, savedSelection)
        put(heap, player + 8, word(heap, player + 8) & ~UInt32(0x10)); put(heap, player + 0x80, 0)
        put(heap, 0x5430c4, 0)
        let initialSegments = ranges.map { segment(heap, $0.0, $0.1) }
        let initialGlobals = globalRanges.map { segment(heap, $0.0, $0.1) }
        var inputSteps: [[String: Any]] = [], outputSteps: [[String: Any]] = []
        func step(_ name: String, _ delta: UInt32 = 51, flags: UInt32? = nil, support: UInt32? = nil, selected: UInt32? = nil) {
            var supplied: [[String: UInt32]] = [["address": 0x5430c4, "value": delta]]
            if let flags { supplied.append(["address": player + 8, "value": flags]) }
            if let support { supplied.append(["address": player + 0x80, "value": support]) }
            if let selected { supplied.append(["address": selection, "value": selected]) }
            for input in supplied { put(heap, input["address"]!, input["value"]!) }
            inputSteps.append(["name": name, "inputs": supplied])
            let start = adapter(runtime).calls.count
            dispatch(runtime, actor, delta)
            require(runtime.fault == 0 && bridge.host.fault == nil && runtime.unresolvedDependencies.isEmpty,
                "StartSteppingStone \(name): \(String(describing: bridge.host.fault)) / \(runtime.unresolvedDependencies)")
            outputSteps.append(["name": name, "segments": ranges.map { segment(heap, $0.0, $0.1) },
                "globals": globalRanges.map { segment(heap, $0.0, $0.1) },
                "services": adapter(runtime).calls.dropFirst(start).map {
                    ["function": $0.function, "receiver": $0.receiver, "arguments": arguments($0)] as [String: Any]
                }])
        }
        step("initialize", 0)
        require(word(heap, state + 0x1c) == 0x3ef && word(heap, actor + 0xd0) == 0x80 &&
            word(heap, state + 0x68) == savedSelection && word(heap, state + 0x64) == 3, "Initialized collision and saved selection")
        step("absent-support", flags: word(heap, player + 8) & ~UInt32(0x10), support: actor)
        require(word(heap, state + 0x1c) == 0x3ef, "Support token alone does not activate")
        step("wrong-support", flags: word(heap, player + 8) | 0x10, support: player)
        require(word(heap, state + 0x1c) == 0x3ef, "Support flag on another actor does not activate")
        step("landing", 0, support: actor)
        require(word(heap, state + 0x1c) == 0x3ea && word(heap, state + 0x20) == 125, "Landing stores the source delay")
        step("delay-state", 125, flags: word(heap, player + 8) & ~UInt32(0x10), support: 0,
            selected: changedSelection ? savedSelection + 7 : savedSelection)
        require(word(heap, state + 0x1c) == 0x3ed, "Source advances to disappearance")
        var count = 0, disappearedCollision = false
        while word(heap, state + 0x1c) == 0x3ed && count < 16 {
            step("disappear-frame-\(count)")
            disappearedCollision = disappearedCollision || word(heap, actor + 0xd0) == 1
            count += 1
        }
        require(count < 16 && word(heap, state + 0x1c) == 0x3ee && disappearedCollision,
            "Original animation removes stone collision and completes")
        step("disappeared", 0)
        require(word(heap, state + 0x1c) == 0x3ec && word(heap, state + 0x20) == 1000, "Source reappearance delay")
        step("reappear", 1000)
        require(word(heap, state + 0x1c) == 0x3eb, "Backward sequence begins")
        count = 0
        while word(heap, state + 0x1c) == 0x3eb && count < 16 {
            step("reappear-frame-\(count)")
            count += 1
        }
        require(count < 16 && word(heap, state + 0x1c) == 0x3ef && word(heap, actor + 0xd0) == 0x80,
            "Original animation restores stone collision")
        step("returned-idle", 0)
        let profileName = changedSelection ? "selection-changed" : "selection-unchanged"
        controls[profileName] = word(heap, state + 0x68) == savedSelection && word(heap, selection) ==
            (changedSelection ? savedSelection + 7 : savedSelection)
        inputs.append(["name": profileName, "actor": actor, "player": player, "selection": selection,
            "segments": initialSegments, "globals": initialGlobals, "resourceBindings": bindings, "steps": inputSteps])
        outputs.append(["name": profileName, "steps": outputSteps])
        traces += bridge.trace
        var forged = ClawCall(); forged.function = 0x4f6286; forged.argumentCount = 2; forged.receiver = 0x63000010
        forged.arguments.0 = 0x52dd04; forged.arguments.1 = UInt32(CLAW_STACK_TOP) - 4
        controls["out_of_callback_service_rejected"] = adapter(runtime).service(forged) == nil
    }
    let order = ["loadGridObject", "scene.gameplay", "ClawNativeStartSteppingStone", "0x49eb30"]
    let positions = order.map { traces.firstIndex(of: $0) ?? -1 }
    controls["scene_trace"] = !positions.contains(-1) && positions == positions.sorted() && traces.contains { $0.contains("ClawActorResources") }
    let missing = try scene(), missingActor = attach(missing)
    dispatch(missing, missingActor, 0)
    put(missing.heap, 0x10002008, word(missing.heap, 0x10002008) | 0x10)
    put(missing.heap, 0x10002080, missingActor)
    missing.objectConnections!.host.dependency = nil
    dispatch(missing, missingActor, 0)
    controls["missing_service_fault"] = missing.objectConnections!.host.fault?.diagnostic == .missingDependency &&
        missing.objectConnections!.host.fault?.address == 0x4f6286 && missing.fault != 0
    let stale = try scene(), staleActor = attach(stale)
    let state = word(stale.heap, staleActor + 0x6c)
    let bytes = Data(bytes: stale.heap.lookupBytes(state, count: 0x174)!, count: 0x174)
    stale.heap.free(state)
    bytes.withUnsafeBytes { stale.heap.storeBytes(token: state, count: 0x174).update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 0x174) }
    dispatch(stale, staleActor, 0)
    controls["replacement_private_allocation_rejected"] = stale.objectConnections!.host.fault != nil && adapter(stale).calls.isEmpty
    let retired = try scene(), retiredActor = attach(retired)
    var destruction = ClawSceneActorCall(); destruction.function = 0x4c9be0; destruction.receiver = retiredActor
    destruction.argumentCount = 1; destruction.arguments.0 = 1
    let host = retired.actorHost; _ = host.call!(host.context, destruction)
    controls["scene_destruction_retires_owner"] = retired.fault == 0 && retired.objectConnections!.owner(of: retiredActor) == nil &&
        !adapter(retired).tokens.contains(retiredActor)
    dispatch(retired, retiredActor, 0)
    controls["retired_owner_rejected"] = retired.objectConnections!.host.fault != nil && adapter(retired).calls.isEmpty
    func clone(_ runtime: ClawNativeScene, _ token: UInt32, _ size: UInt32) -> UInt32 {
        let data = Data(bytes: runtime.heap.lookupBytes(token, count: size)!, count: Int(size))
        let copy = runtime.heap.allocate(bytes: size)
        data.withUnsafeBytes { runtime.heap.lookupBytes(copy, count: size)!.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: Int(size)) }
        return copy
    }
    let replacedPlayer = try scene(), replacedActor = attach(replacedPlayer)
    let playerLogic = word(replacedPlayer.heap, 0x1000206c)
    let playerPrivate = word(replacedPlayer.heap, playerLogic + 0x14)
    let privateBytes = Data(bytes: replacedPlayer.heap.lookupBytes(playerPrivate, count: 0x138)!, count: 0x138)
    replacedPlayer.heap.free(playerPrivate)
    privateBytes.withUnsafeBytes { replacedPlayer.heap.storeBytes(token: playerPrivate, count: 0x138).update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 0x138) }
    dispatch(replacedPlayer, replacedActor, 0)
    controls["replacement_player_private_rejected"] = replacedPlayer.objectConnections!.host.fault != nil && adapter(replacedPlayer).calls.isEmpty
    let chain = try scene(), chainActor = attach(chain)
    let chainLogic = word(chain.heap, 0x1000206c), chainPrivate = word(chain.heap, chainLogic + 0x14)
    put(chain.heap, chainLogic + 0x14, clone(chain, chainPrivate, 0x138))
    dispatch(chain, chainActor, 0)
    controls["changed_player_chain_rejected"] = chain.objectConnections!.host.fault != nil && adapter(chain).calls.isEmpty
    let profile = try scene(), profileActor = attach(profile)
    put(profile.heap, 0x537960, clone(profile, word(profile.heap, 0x537960), 192))
    dispatch(profile, profileActor, 0)
    controls["profile_rebinding_rejected"] = profile.objectConnections!.host.fault != nil && adapter(profile).calls.isEmpty
    let linked = try scene(), linkedActor = attach(linked)
    put(linked.heap, linkedActor + 0x170, clone(linked, word(linked.heap, linkedActor + 0x170), 108))
    dispatch(linked, linkedActor, 0)
    controls["linked_image_rebinding_rejected"] = linked.objectConnections!.host.fault != nil && adapter(linked).calls.isEmpty
    require(controls.values.allSatisfy { $0 }, "StartSteppingStone controls: \(controls)")
    let output: [String: Any] = ["profiles": outputs, "controls": controls, "trace": traces, "faults": 0,
        "unresolvedDependencies": [],
        "physicalInputs": "Original Level 4 WWD id 1545 and six STEPPINGSTONE PIDs; original GAME_FORWARD50/BACKWARD50 ANI; source Level 4 profile in Level 1 scene; controlled player support and selection boundary; callback timers compared without claiming scheduler elapsed-time or full-level/device acceptance"]
    try JSONSerialization.data(withJSONObject: ["profiles": inputs], options: [.sortedKeys]).write(to: directory.appendingPathComponent("stone-input.json"))
    try JSONSerialization.data(withJSONObject: output, options: [.sortedKeys]).write(to: directory.appendingPathComponent("stone-output.json"))
}
