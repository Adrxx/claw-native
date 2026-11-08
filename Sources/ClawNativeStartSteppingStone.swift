import Foundation

// The callback owns collision mode, timers and selection. Its canonical
// callees own animation and geometry; the scene supplies physical resources.
// claw-progress-class-owner: start_stepping_stone 0x49eb30
@objc(ClawNativeStartSteppingStone)
class ClawNativeStartSteppingStone: ClawNativeObjectAdapter {
    override class var services: Set<UInt32> { [0x4f6286] }
    override class var stacklessCallerReserve: UInt32? { 0x100 }
    private struct Pin {
        let address: UInt32, count: UInt32
        let identity: ClawTokenHeap.AllocationIdentity
    }
    private struct Owner {
        let state: UInt32, images: UInt32, profile: UInt32
        let playerState: UInt32, playerPrivate: UInt32
        let pins: [Pin]
    }
    private var owners: [UInt32: Owner] = [:]
    private var activeActor: UInt32?
    var tokens: Set<UInt32> { Set(owners.keys) }
    var calls: [ClawCall] {
        connections.calls.filter { [0x40f680, 0x4c79e0, 0x4c82a0, 0x4f6286].contains($0.function) }
    }

    override func attach(_ object: ClawInteractionActor, callback: UInt32) -> Bool {
        guard callback == 0x49eb30, object.primary.4 == callback, owners[object.token] == nil,
              let scene = connections.scene, scene.heap === connections.host.heap,
              let resources = scene.objectResources, resources.heap === scene.heap,
              let profile = scene.heap.lookup(0x537960, words: 1)?[0],
              scene.heap.lookup(profile, words: 48) != nil,
              let playerState = scene.heap.lookup(0x1000206c, words: 1)?[0],
              let playerPrivate = scene.heap.lookup(playerState + 0x14, words: 1)?[0],
              scene.heap.lookup(playerPrivate + 0x80, words: 1) != nil else { return false }
        let heap = scene.heap
        if heap.lookup(0x537e88, words: 1) == nil {
            guard !heap.overlaps(0x537e88, count: 4) else { return false }
            heap.store(token: 0x537e88, words: 1)[0] = 0x10002000
        }
        guard let playerGlobal = heap.lookup(0x537e88, words: 1),
              playerGlobal[0] == 0 || playerGlobal[0] == 0x10002000 else { return false }
        playerGlobal[0] = 0x10002000
        var spans: [(UInt32, UInt32)] = [
            (object.token, 0x1b4), (object.actor.27, 0x174),
            (0x537960, 4), (profile, 192), (0x537e88, 4),
            (0x10002000, 0x1b4), (playerState, 0x174), (playerPrivate, 312),
            (scene.sceneIdentity, 60)
        ]
        // +0x170 is the image collection. Its bounds and absolute-index
        // table are consumed by canonical 0x40f680.
        if object.actor.92 != 0 {
            guard resources.images(token: object.actor.92) != nil,
                  let images = heap.lookup(object.actor.92, words: 27), images[6] > 0,
                  images[6] <= UInt32.max / 4 else { return false }
            spans += [(object.actor.92, 108), (images[5], images[6] * 4)]
        }
        var pins: [Pin] = []
        for (address, count) in spans {
            guard let identity = heap.containingAllocationIdentity(at: address, count: count) else { return false }
            pins.append(Pin(address: address, count: count, identity: identity))
        }
        scene.write(object)
        guard scene.fault == 0 else { return false }
        owners[object.token] = Owner(state: object.actor.27, images: object.actor.92, profile: profile,
            playerState: playerState, playerPrivate: playerPrivate, pins: pins)
        return true
    }

    private func valid(_ actor: UInt32) -> Bool {
        let heap = connections.host.heap
        guard let owner = owners[actor], let scene = connections.scene,
              scene.heap === heap, scene.objectResources?.heap === heap,
              heap.lookup(actor + 0x6c, words: 1)?[0] == owner.state,
              heap.lookup(owner.state + 0x10, words: 1)?[0] == 0x49eb30,
              heap.lookup(actor + 0x170, words: 1)?[0] == owner.images,
              heap.lookup(actor + 0x0c, words: 1)?[0] == scene.sceneIdentity,
              heap.lookup(0x537960, words: 1)?[0] == owner.profile,
              heap.lookup(0x537e88, words: 1)?[0] == 0x10002000,
              heap.lookup(0x1000206c, words: 1)?[0] == owner.playerState,
              heap.lookup(owner.playerState + 0x14, words: 1)?[0] == owner.playerPrivate else { return false }
        return owner.pins.allSatisfy {
            heap.containingAllocationIdentity(at: $0.address, count: $0.count) === $0.identity
        }
    }

    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x49eb30, activeActor == nil, valid(actor) else { connections.reject(actor); return }
        activeActor = actor
        defer { activeActor = nil }
        connections.record("ClawNativeStartSteppingStone")
        connections.record("0x49eb30")
        var call = ClawCall()
        call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        let completion = connections.host.invoke(call)
        if completion.completed && !valid(actor) { connections.reject(actor) }
    }

    override func service(_ call: ClawCall) -> UInt32? {
        guard connections.active === self, let actor = activeActor, valid(actor),
              call.function == 0x4f6286, call.receiver2 == 0, call.x87ArgumentCount == 0,
              call.argumentCount == 2, [UInt32(0x52dd04), 0x52dd14].contains(call.arguments.0),
              let scene = connections.scene,
              let parent = scene.heap.lookup(scene.sceneIdentity, words: 12),
              call.receiver == parent[11] + 0x10,
              let output = connections.host.bytes(call.arguments.1, count: 4) else { return nil }
        connections.record("ClawActorResources.0x4f6286")
        let token = scene.resolveResource(dictionary: call.receiver, name: call.arguments.0)
        guard scene.fault == 0, valid(actor) else {
            connections.host.fail(UInt32(CLAW_FAULT_HOST), at: call.function); return nil
        }
        guard token != 0, scene.objectResources?.sequence(token: token) != nil else { return nil }
        withUnsafeBytes(of: token.littleEndian) {
            output.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 4)
        }
        return 1
    }

    override func remove(_ actor: UInt32) { owners.removeValue(forKey: actor) }
}
