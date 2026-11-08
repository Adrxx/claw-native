import Foundation

// The canonical callback owns every state, timer, rectangle and collision-mode change.
// This scene adapter supplies resource dictionaries and the existing physical
// audio/Memory owners on the scene heap.
// claw-progress-class-owner: stepping_stone 0x49e810
@objc(ClawNativeSteppingStone) class ClawNativeSteppingStone: ClawNativeObjectAdapter {
    private struct Owner {
        let actor: ClawTokenHeap.AllocationIdentity
        let stateToken: UInt32
        let state: ClawTokenHeap.AllocationIdentity
        let images: UInt32, profile: UInt32
        let pins: [(UInt32, UInt32, ClawTokenHeap.AllocationIdentity)]
        let links: [(UInt32, UInt32)]
    }
    private var owners: [UInt32: Owner] = [:]
    private var active: UInt32?
    private var pins: [(UInt32, UInt32, ClawTokenHeap.AllocationIdentity)] = []
    private var links: [(UInt32, UInt32)] = []
    private var soundBank: UInt32?
    private var prepared = false
    private(set) var memory: ClawNativeMfcMemory?
    var tokens: Set<UInt32> { Set(owners.keys) }
    var calls: [ClawCall] {
        connections.calls.filter { [0x40f680, 0x49e470, 0x49e4b0, 0x4ca610, 0x4c79e0, 0x4c82a0, 0x4f6286].contains($0.function) }
    }
    override class var services: Set<UInt32> { [0x4f6286] }
    override class var stacklessCallerReserve: UInt32? { 0x100 }

    private func pin(_ token: UInt32, _ count: UInt32) -> Bool {
        guard let identity = connections.host.heap.containingAllocationIdentity(at: token, count: count) else { return false }
        pins.append((token, count, identity)); return true
    }
    private func word(_ token: UInt32, initial: UInt32 = 0) -> Bool {
        let heap = connections.host.heap
        if heap.lookup(token, words: 1) == nil {
            guard !heap.overlaps(token, count: 4) else { return false }
            heap.store(token: token, words: 1)[0] = initial
        }
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
        for name in ["LEVEL_STONERISE", "LEVEL_STONESINK"] {
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
                    importTargets: imports, allocationBase: 0x68800000)
            } catch { return false }
        }
        return true
    }
    // Objects can attach during grid construction, before configureRespawn
    // publishes the scene's sound registry. Bind it once it exists, before
    // the first callback, and reject replacement thereafter.
    private func bindSoundBank(required: Bool) -> Bool {
        guard let scene = connections.scene,
              let parent = scene.heap.lookup(scene.sceneIdentity, words: 15) else { return false }
        if let soundBank { return parent[10] == soundBank }
        guard parent[10] != 0 else { return !required }
        let bank = parent[10]
        guard scene.heap.lookup(bank + 12, words: 1)?[0] == scene.sceneIdentity,
              pin(bank, 52) else { return false }
        soundBank = bank
        links += [(scene.sceneIdentity + 0x28, bank), (bank + 12, scene.sceneIdentity)]
        return true
    }
    override func attach(_ object: ClawInteractionActor, callback: UInt32) -> Bool {
        let heap = connections.host.heap
        guard callback == 0x49e810, object.primary.4 == callback, owners[object.token] == nil,
              let actor = heap.allocationIdentity(at: object.token, count: 0x1b4),
              let state = heap.allocationIdentity(at: object.actor.27, count: 0x174),
              let scene = connections.scene, let resources = scene.objectResources,
              resources.heap === heap, object.actor.3 == scene.sceneIdentity,
              let profile = heap.lookup(0x537960, words: 1)?[0],
              heap.lookup(profile, words: 48) != nil else { return false }
        var spans: [(UInt32, UInt32)] = [(0x537960, 4), (profile, 192), (scene.sceneIdentity, 60)]
        var actorLinks: [(UInt32, UInt32)] = [(scene.sceneIdentity + 0x2c, 0x63000000)]
        if object.actor.92 != 0 {
            guard let resource = resources.images(token: object.actor.92),
                  let images = heap.lookup(object.actor.92, words: 27),
                  images[6] == UInt32(resource.table.count), images[6] > 0,
                  images[6] <= UInt32.max / 4 else { return false }
            spans += [(object.actor.92, 108), (images[5], images[6] * 4)]
            actorLinks += [(object.actor.92 + 20, images[5]), (object.actor.92 + 24, images[6])]
            for (index, frame) in resource.table.enumerated() {
                actorLinks.append((images[5] + UInt32(index * 4), frame))
                if frame != 0 { spans.append((frame, 64)) }
            }
        }
        var actorPins: [(UInt32, UInt32, ClawTokenHeap.AllocationIdentity)] = []
        for (token, count) in spans {
            guard let identity = heap.containingAllocationIdentity(at: token, count: count) else { return false }
            actorPins.append((token, count, identity))
        }
        if !prepared {
            guard prepareAudio() else { return false }
            prepared = true
        }
        guard bindSoundBank(required: false),
              actorLinks.allSatisfy({ heap.lookup($0.0, words: 1)?[0] == $0.1 }) else { return false }
        scene.write(object)
        owners[object.token] = Owner(actor: actor, stateToken: object.actor.27, state: state,
            images: object.actor.92, profile: profile, pins: actorPins, links: actorLinks)
        return true
    }
    override func remove(_ actor: UInt32) { owners.removeValue(forKey: actor) }
    private func valid(_ actor: UInt32) -> Bool {
        let heap = connections.host.heap
        guard let owner = owners[actor], connections.scene?.heap === heap,
              heap.allocationIdentity(at: actor, count: 0x1b4) === owner.actor,
              heap.allocationIdentity(at: owner.stateToken, count: 0x174) === owner.state,
              heap.lookup(actor + 0x6c, words: 1)?[0] == owner.stateToken,
              heap.lookup(owner.stateToken + 0x10, words: 1)?[0] == 0x49e810,
              heap.lookup(actor + 0x0c, words: 1)?[0] == connections.scene?.sceneIdentity,
              heap.lookup(actor + 0x170, words: 1)?[0] == owner.images,
              heap.lookup(0x537960, words: 1)?[0] == owner.profile,
              connections.scene?.objectResources?.heap === heap else { return false }
        guard owner.pins.allSatisfy({ heap.containingAllocationIdentity(at: $0.0, count: $0.1) === $0.2 }),
              owner.links.allSatisfy({ heap.lookup($0.0, words: 1)?[0] == $0.1 }) else { return false }
        return pins.allSatisfy { heap.containingAllocationIdentity(at: $0.0, count: $0.1) === $0.2 } &&
            links.allSatisfy { heap.lookup($0.0, words: 1)?[0] == $0.1 }
    }
    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x49e810, active == nil, valid(actor),
              bindSoundBank(required: true), let scene = connections.scene else {
            connections.reject(actor); return
        }
        active = actor
        defer { active = nil }
        let host = connections.host
        host.heap.lookup(0x537210, words: 1)![0] = scene.gameTime
        host.heap.lookup(0x532c0c, words: 1)![0] = scene.player.audio?.routing.managerAvailable ?? 0
        host.heap.lookup(0x532c10, words: 1)![0] = scene.player.audio?.routing.masterVolume ?? 0
        connections.record("ClawNativeSteppingStone"); connections.record("0x49e810")
        var call = ClawCall(); call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        if let audio = scene.player.audio, let memory {
            _ = host.withObjectAllocation(provider: memory, audio: audio) { host.invoke(call) }
        } else { _ = host.invoke(call) }
        if !valid(actor) { connections.reject(actor) }
    }
    override func service(_ call: ClawCall) -> UInt32? {
        guard connections.active === self, let actor = active, valid(actor), let scene = connections.scene,
              call.function == 0x4f6286, call.argumentCount == 2, call.receiver2 == 0,
              call.x87ArgumentCount == 0, let output = connections.host.bytes(call.arguments.1, count: 4) else { return nil }
        let token: UInt32
        switch call.arguments.0 {
        case 0x52dd04, 0x52dd14:
            guard call.receiver == 0x63000010 else { return nil }
            connections.record("ClawActorResources.0x4f6286")
            token = scene.resolveResource(dictionary: call.receiver, name: call.arguments.0)
        case 0x52dd7c, 0x52dd8c:
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
