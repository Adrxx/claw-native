import Foundation

// The scene owns the actor, player and level profile. The callback and impulse
// execute their registered source owners; only resource lookup is physical.
// claw-progress-class-owner: water_rock 0x49de10
@objc(ClawNativeWaterRock)
final class ClawNativeWaterRock: ClawNativeObjectAdapter {
    override class var services: Set<UInt32> { [0x4f6286] }
    override class var stacklessCallerReserve: UInt32? { 0x100 }
    private(set) var tokens: Set<UInt32> = []
    private var memory: ClawNativeMfcMemory?
    private var activeActor: UInt32?
    private var states: [UInt32: (UInt32, ClawTokenHeap.AllocationIdentity)] = [:]
    private var pins: [(UInt32, UInt32, ClawTokenHeap.AllocationIdentity)] = []

    private func pin(_ address: UInt32, _ count: UInt32) -> Bool {
        guard let identity = connections.host.heap.containingAllocationIdentity(at: address, count: count) else { return false }
        pins.append((address, count, identity)); return true
    }
    private func valid(_ actor: UInt32) -> Bool {
        let heap = connections.host.heap
        guard let (state, identity) = states[actor], heap.lookup(actor + 0x6c, words: 1)?[0] == state,
              heap.containingAllocationIdentity(at: state, count: 0x174) === identity,
              heap.lookup(state + 0x10, words: 1)?[0] == 0x49de10 else { return false }
        return pins.allSatisfy { heap.containingAllocationIdentity(at: $0.0, count: $0.1) === $0.2 }
    }

    private func prepareAudio(_ scene: ClawNativeScene) -> Bool {
        let heap = scene.heap
        for (address, value): (UInt32, UInt32) in [
            (0x532c0c, 0), (0x532c10, 0), (0x513768, Float(0.01).bitPattern), (0x510020, .max)
        ] {
            if heap.lookup(address, words: 1) == nil { heap.store(token: address, words: 1)[0] = value }
            guard pin(address, 4) else { return false }
        }
        guard let audio = scene.player.audio else { return true }
        guard audio.validAudioBinding(for: connections.host),
              let parent = heap.lookup(scene.sceneIdentity, words: 15) else { return false }
        if parent[1] == 0 {
            let wrapper = heap.allocate(bytes: 20), dimensions = heap.allocate(bytes: 24)
            guard let w = heap.lookup(wrapper, words: 5), let d = heap.lookup(dimensions, words: 6) else { return false }
            w[4] = dimensions
            d[4] = UInt32(ClawNativeCamera.viewport.width); d[5] = UInt32(ClawNativeCamera.viewport.height)
            parent[1] = wrapper
        }
        parent[8] = audio.managerIdentity
        if memory == nil {
            let imports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map {
                ($0.element, UInt32(0x710000 + $0.offset * 4))
            })
            do {
                memory = try ClawNativeMfcMemory(host: connections.host, sha256: ClawNativeMfcMemory.imageHash,
                    importTargets: imports, allocationBase: 0x68e00000)
            } catch { return false }
        }
        return true
    }

    override func attach(_ object: ClawInteractionActor, callback: UInt32) -> Bool {
        guard callback == 0x49de10, !tokens.contains(object.token), let scene = connections.scene,
              scene.objectResources?.heap === scene.heap,
              let profile = scene.heap.lookup(0x537960, words: 1),
              let table = scene.heap.lookup(profile[0], words: 48),
              table[0] == 13, object.primary.4 == callback,
              let state = scene.heap.containingAllocationIdentity(at: object.actor.27, count: 0x174),
              prepareAudio(scene), pin(profile[0], 192), pin(0x537960, 4) else { return false }
        scene.write(object)
        guard scene.fault == 0 else { return false }
        for (address, words): (UInt32, UInt32) in [
            (0x537e88, 1), (0x537204, 1), (0x534eac, 1),
            (0x534db8, UInt32(MemoryLayout<ClawPlayerPhysics>.size / 4))
        ] {
            if scene.heap.lookup(address, words: words) == nil {
                guard !scene.heap.overlaps(address, count: words * 4) else { return false }
                scene.heap.store(token: address, words: Int(words))
            }
            guard pin(address, words * 4) else { return false }
        }
        // Immutable binary64 constants used by the original impulse owner.
        for (address, value): (UInt32, Double) in [
            (0x50ba88, 0), (0x50baa8, 2250), (0x50bac0, 4),
            (0x50bac8, -2), (0x50bad0, 0.5), (0x50bad8, 0.25), (0x513e20, 0.1)
        ] {
            if scene.heap.lookup(address, words: 2) == nil {
                guard !scene.heap.overlaps(address, count: 8) else { return false }
                let words = scene.heap.store(token: address, words: 2)
                words[0] = UInt32(truncatingIfNeeded: value.bitPattern)
                words[1] = UInt32(value.bitPattern >> 32)
            }
            let words = scene.heap.lookup(address, words: 2)!
            guard words[0] == UInt32(truncatingIfNeeded: value.bitPattern),
                  words[1] == UInt32(value.bitPattern >> 32), pin(address, 8) else { return false }
        }
        tokens.insert(object.token)
        states[object.token] = (object.actor.27, state)
        return true
    }

    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x49de10, activeActor == nil, tokens.contains(actor), valid(actor), let scene = connections.scene,
              let camera = scene.camera,
              let identity = scene.heap.lookup(0x537e88, words: 1),
              let keyboard = scene.heap.lookup(0x537204, words: 1),
              let input = scene.heap.lookup(camera.inputToken, words: 4),
              let powerup = scene.heap.lookup(0x534eac, words: 1),
              let physicsBytes = scene.heap.lookupBytes(0x534db8, count: UInt32(MemoryLayout<ClawPlayerPhysics>.size)) else {
            connections.reject(function); return
        }
        activeActor = actor
        defer { activeActor = nil }
        identity[0] = 0x10002000
        keyboard[0] = camera.inputToken
        powerup[0] = scene.player.runtime.powerup
        scene.heap.lookup(0x532c0c, words: 1)![0] = scene.player.audio?.routing.managerAvailable ?? 0
        scene.heap.lookup(0x532c10, words: 1)![0] = scene.player.audio?.routing.masterVolume ?? 0
        input[3] = scene.player.runtime.inputLatched
        var physics = scene.player.runtime.physics
        withUnsafeBytes(of: &physics) { physicsBytes.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: $0.count) }
        connections.record("ClawNativeWaterRock")
        connections.record("0x49de10")
        var call = ClawCall()
        call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        let completed: Bool
        if let audio = scene.player.audio, let memory {
            completed = connections.host.withObjectAllocation(provider: memory, audio: audio) {
                connections.host.invoke(call).completed
            } ?? false
        } else { completed = connections.host.invoke(call).completed }
        guard completed else { return }
        guard valid(actor),
              let player = scene.snapshotActor(0x10002000),
              let privateWords = scene.heap.lookup(player.primary.5, words: 78) else {
            connections.reject(actor); return
        }
        withUnsafeMutableBytes(of: &physics) {
            $0.copyMemory(from: UnsafeRawBufferPointer(start: physicsBytes, count: $0.count))
        }
        scene.player.acceptSceneSnapshot(player, physics: physics, privateWords: UnsafePointer(privateWords))
        var runtime = scene.player.runtime
        runtime.inputLatched = input[3]
        scene.player.acceptRuntimeSnapshot(runtime)
    }

    override func service(_ call: ClawCall) -> UInt32? {
        guard connections.active === self, let activeActor, valid(activeActor), call.function == 0x4f6286,
              call.argumentCount == 2, call.receiver2 == 0, call.x87ArgumentCount == 0,
              let scene = connections.scene, let resources = scene.objectResources,
              let parent = scene.heap.lookup(scene.sceneIdentity, words: 12),
              call.receiver == parent[11] + 16,
              let output = connections.host.bytes(call.arguments.1, count: 4) else { return nil }
        let name: String
        switch call.arguments.0 {
        case 0x52dd50: name = "LEVEL_WATERROCK_IDLE"
        case 0x52dd38: name = "LEVEL_WATERROCK_SPRING"
        case 0x5246a8: name = "CLAW_JUMP"
        default: return nil
        }
        do {
            guard let sequence = try resources.sequence(name: name) else { return nil }
            // Resource events keep their real PCM pool and scene geometry.
            let sequenceWords = scene.heap.lookup(sequence.token, words: 5)!
            let records = scene.heap.lookup(sequenceWords[3], words: sequenceWords[4])!
            for index in 0..<Int(sequenceWords[4]) {
                guard let record = scene.heap.lookup(records[index], words: 12) else { return nil }
                if record[11] != 0 {
                    guard let sound = scene.heap.lookup(record[11], words: 5),
                          scene.player.audio?.ownsAudioPool(sound[4]) == true else { return nil }
                    sound[3] = scene.sceneIdentity
                }
            }
            var token = sequence.token.littleEndian
            withUnsafeBytes(of: &token) { output.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 4) }
            connections.record("ClawActorResources.sequence:\(name)")
            return 1
        } catch { return nil }
    }

    override func remove(_ actor: UInt32) { tokens.remove(actor); states.removeValue(forKey: actor) }
}
