import Foundation

// The canonical callback owns every state, timer, rectangle and damage change.
// This scene adapter supplies resource dictionaries and the existing physical
// audio/Memory owners on the scene heap.
@objc(ClawNativeFloorSpike) class ClawNativeFloorSpike: ClawNativeObjectAdapter {
    private struct Owner {
        let actor: ClawTokenHeap.AllocationIdentity
        let stateToken: UInt32
        let state: ClawTokenHeap.AllocationIdentity
    }
    private var owners: [UInt32: Owner] = [:]
    private var active: UInt32?
    private var pins: [(UInt32, UInt32, ClawTokenHeap.AllocationIdentity)] = []
    private var links: [(UInt32, UInt32)] = []
    private(set) var memory: ClawNativeMfcMemory?
    var tokens: Set<UInt32> { Set(owners.keys) }
    var calls: [ClawCall] {
        connections.calls.filter { [0x49e470, 0x49e4b0, 0x4ca610, 0x4c79e0, 0x4c82a0, 0x4f6286].contains($0.function) }
    }
    override class var services: Set<UInt32> { [0x4f6286] }
    override class var stacklessCallerReserve: UInt32? { 0x40 }

    private func pin(_ token: UInt32, _ count: UInt32) -> Bool {
        guard let identity = connections.host.heap.containingAllocationIdentity(at: token, count: count) else { return false }
        pins.append((token, count, identity)); return true
    }
    private func word(_ token: UInt32, initial: UInt32 = 0) -> Bool {
        let heap = connections.host.heap
        if heap.lookup(token, words: 1) == nil { heap.store(token: token, words: 1)[0] = initial }
        return pin(token, 4)
    }
    private func prepareAudio() -> Bool {
        guard let scene = connections.scene else { return false }
        let heap = scene.heap
        guard word(0x537210), word(0x532c0c), word(0x532c10),
              word(0x513768, initial: Float(0.01).bitPattern), word(0x510020, initial: .max),
              heap.lookup(0x513768, words: 1)?[0] == Float(0.01).bitPattern,
              heap.lookup(0x510020, words: 1)?[0] == .max else { return false }
        guard let audio = scene.player.audio else { return true }
        guard audio.validAudioBinding(for: connections.host),
              let parent = heap.lookup(scene.sceneIdentity, words: 15) else { return false }
        // Physical viewport storage consumed by the real spatial sound owner.
        // The camera and renderer use this same native 640 by 480 viewport.
        if parent[1] == 0 {
            let wrapper = heap.allocate(bytes: 20), dimensions = heap.allocate(bytes: 24)
            guard let w = heap.lookup(wrapper, words: 5), let d = heap.lookup(dimensions, words: 6) else { return false }
            w[4] = dimensions
            d[4] = UInt32(ClawNativeCamera.viewport.width); d[5] = UInt32(ClawNativeCamera.viewport.height)
            parent[1] = wrapper
        }
        guard let wrapper = heap.lookup(parent[1], words: 5),
              let dimensions = heap.lookup(wrapper[4], words: 6), dimensions[4] > 0,
              pin(parent[1], 20), pin(wrapper[4], 24) else { return false }
        links.append((scene.sceneIdentity + 4, parent[1])); links.append((parent[1] + 16, wrapper[4]))
        parent[8] = audio.managerIdentity
        links.append((scene.sceneIdentity + 0x20, audio.managerIdentity))
        for name in ["LEVEL_FLOORSPIKEUP", "LEVEL_FLOORSPIKEDOWN"] {
            if let sound = audio.resolve(name: name) {
                guard audio.ownsAudioPool(sound.voicePoolToken), pin(sound.resourceToken, 20),
                      let resource = heap.lookup(sound.resourceToken, words: 5) else { return false }
                // Attach the preloaded PCM resource to its actual scene; the
                // source sound owner reads camera position and viewport here.
                resource[3] = scene.sceneIdentity
                links.append((sound.resourceToken + 12, scene.sceneIdentity))
                links.append((sound.resourceToken + 16, sound.voicePoolToken))
            }
        }
        if memory == nil {
            let imports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map {
                ($0.element, UInt32(0x710000 + $0.offset * 4))
            })
            do {
                memory = try ClawNativeMfcMemory(host: connections.host, sha256: ClawNativeMfcMemory.imageHash,
                    importTargets: imports, allocationBase: 0x68000000)
            } catch { return false }
        }
        return true
    }
    override func attach(_ object: ClawInteractionActor, callback: UInt32) -> Bool {
        let heap = connections.host.heap
        guard callback == 0x461d50, object.primary.4 == callback, owners[object.token] == nil,
              let actor = heap.allocationIdentity(at: object.token, count: 0x1b4),
              let state = heap.allocationIdentity(at: object.actor.27, count: 0x174), prepareAudio() else { return false }
        connections.scene?.write(object)
        owners[object.token] = Owner(actor: actor, stateToken: object.actor.27, state: state)
        return true
    }
    override func remove(_ actor: UInt32) { owners.removeValue(forKey: actor) }
    private func valid(_ actor: UInt32) -> Bool {
        let heap = connections.host.heap
        guard let owner = owners[actor], connections.scene?.heap === heap,
              heap.allocationIdentity(at: actor, count: 0x1b4) === owner.actor,
              heap.allocationIdentity(at: owner.stateToken, count: 0x174) === owner.state,
              heap.lookup(actor + 0x6c, words: 1)?[0] == owner.stateToken,
              heap.lookup(owner.stateToken + 0x10, words: 1)?[0] == 0x461d50 else { return false }
        return pins.allSatisfy { heap.containingAllocationIdentity(at: $0.0, count: $0.1) === $0.2 } &&
            links.allSatisfy { heap.lookup($0.0, words: 1)?[0] == $0.1 }
    }
    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x461d50, active == nil, valid(actor), let scene = connections.scene else {
            connections.reject(actor); return
        }
        active = actor
        defer { active = nil }
        let host = connections.host
        host.heap.lookup(0x537210, words: 1)![0] = scene.gameTime
        host.heap.lookup(0x532c0c, words: 1)![0] = scene.player.audio?.routing.managerAvailable ?? 0
        host.heap.lookup(0x532c10, words: 1)![0] = scene.player.audio?.routing.masterVolume ?? 0
        connections.record("ClawNativeFloorSpike"); connections.record("0x461d50")
        var call = ClawCall(); call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        if let audio = scene.player.audio, let memory {
            _ = host.withObjectAllocation(provider: memory, audio: audio) { host.invoke(call) }
        } else { _ = host.invoke(call) }
        if !valid(actor) { connections.reject(actor) }
    }
    override func service(_ call: ClawCall) -> UInt32? {
        guard let actor = active, valid(actor), let scene = connections.scene,
              call.function == 0x4f6286, call.argumentCount == 2, call.receiver2 == 0,
              call.x87ArgumentCount == 0, let output = connections.host.bytes(call.arguments.1, count: 4) else { return nil }
        let token: UInt32
        switch call.arguments.0 {
        case 0x52959c, 0x5295b0:
            guard call.receiver == 0x63000010 else { return nil }
            connections.record("ClawActorResources.0x4f6286")
            token = scene.resolveResource(dictionary: call.receiver, name: call.arguments.0)
        case 0x529584, 0x5295c0:
            guard let bank = scene.heap.lookup(scene.sceneIdentity + 0x28, words: 1), bank[0] != 0,
                  call.receiver == bank[0] + 0x10, let name = clawOriginalResourceNames[call.arguments.0] else { return nil }
            connections.record("ClawNativeAudio.0x4f6286")
            token = scene.player.audio?.resolve(name: name)?.resourceToken ?? 0
        default: return nil
        }
        guard scene.fault == 0, valid(actor) else { connections.host.fail(UInt32(CLAW_FAULT_HOST), at: call.function); return nil }
        withUnsafeBytes(of: token.littleEndian) { output.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 4) }
        return token == 0 ? 0 : 1
    }
}
