import Foundation

func verifyNativeWindowInputRoutes(root: URL, literals: [UInt32: Data]) throws {
    let queue = ClawNativeWindowInputQueue()
    let input = ClawNativeWindowInput(queue: queue), other = ClawNativeWindowInput(queue: queue)
    let menu = try ClawNativeMenuBase(root: root, literals: literals, audioAvailable: false, windowInput: input)
    precondition(menu.heap.lookup(menu.applicationToken, words: 2)![1] == menu.windowReceiver)
    let world = try ClawLevelScene(root: root)
    let player = try ClawNativePlayer(world: world.world, assets: ClawPlayerAssets(root: root))
    let scene = ClawNativeScene(player: player, windowInput: input)
    precondition(menu.windowInput === scene.windowInput)
    input.key(mask: 1, down: true)
    input.primary(mask: 2, down: true)
    input.key(mask: 4, down: false)
    other.key(mask: 8, down: true)
    var menuCall = ClawStateFiveCall()
    menuCall.function = 0x4b8910; menuCall.receiver = menu.windowReceiver
    menuCall.argumentCount = 2; menuCall.arguments.0 = 0x100; menuCall.arguments.1 = 64
    precondition(menu.initializerService(menuCall) == 0 && menu.fault == 0)
    precondition(queue.pending.map { $0.message.rawValue } == [0x201, 0x101, 0x100])
    var sceneCall = ClawSceneActorCall()
    sceneCall.function = 0x4b8910; sceneCall.receiver = scene.windowReceiver
    sceneCall.argumentCount = 2; sceneCall.arguments.0 = 0x201; sceneCall.arguments.1 = 64
    precondition(scene.performService(sceneCall) == 0 && scene.fault == 0)
    precondition(queue.pending.map { $0.message.rawValue } == [0x101, 0x100])
    precondition(input.held == 3 && input.frameInput().pressed == 0)
    precondition(other.frameInput().pressed == 8)
    // Scene/SpecialCommand's portable host callback consumes the same queue.
    input.key(mask: 16, down: true)
    var hostCall = sceneCall
    hostCall.receiver = menu.windowReceiver; hostCall.arguments.0 = 0x100
    let host = menu.actorHost
    precondition(host.call!(host.context, hostCall) == 0 && menu.fault == 0)
    precondition(queue.pending.isEmpty && input.held == 19)
    // Receiver identity is read from the physical heap on each invocation.
    other.primary(mask: 32, down: true)
    menu.heap.lookup(menu.windowReceiver, words: 2)![1] = other.window
    menuCall.arguments.0 = 0x201
    precondition(menu.initializerService(menuCall) == 0 && menu.fault == 0 && queue.pending.isEmpty)
    menu.heap.lookup(menu.windowReceiver, words: 2)![1] = input.window
    input.key(mask: 64, down: true)
    let before = queue.pending
    // Invalid ABI, receiver, selector, window, and owner cannot masquerade as empty.
    for kind in 0..<6 {
        let bad = try ClawNativeMenuBase(root: root, literals: literals,
            missingOwner: kind == 4 ? 0x4b8910 : nil, audioAvailable: false,
            windowInput: kind == 5 ? nil : input)
        var call = menuCall; call.receiver = bad.windowReceiver
        if kind == 0 { call.argumentCount = 1 }
        if kind == 1 { call.receiver &+= 4 }
        if kind == 2 { call.arguments.0 = 0x999 }
        if kind == 3 { bad.heap.lookup(bad.windowReceiver, words: 2)![1] = 0 }
        _ = bad.initializerService(call)
        precondition(bad.fault != 0 && bad.boundary == 0x4b8910 && queue.pending == before)
    }
    for kind in 0..<5 {
        let bad = ClawNativeScene(player: player, windowInput: kind == 4 ? nil : input)
        var call = sceneCall; call.receiver = bad.windowReceiver
        if kind == 0 { call.argumentCount = 1 }
        if kind == 1 { call.receiver &+= 4 }
        if kind == 2 { call.arguments.0 = 0x999 }
        if kind == 3 { bad.heap.lookup(bad.windowReceiver, words: 2)![1] = .max }
        _ = bad.performService(call)
        precondition(bad.fault != 0 && bad.unresolvedDependencies.contains(0x4b8910) && queue.pending == before)
    }
    print("PASS shared native ingestion -> menu initializer / scene / scene-host drains; held state, survivors, missing owner and invalid mappings")
}
