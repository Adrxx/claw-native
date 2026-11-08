import Foundation

// The wrappers select their shared global and call the admitted base callback.
// Keep the WWD callback in the private record: the base reads it to select its
// phase. Only resource lookup and physical audio/allocation live here.
// claw-progress-class-owner: object_variants 0x461fe0 0x462000 0x462020 0x4622f0 0x462310 0x49ead0 0x49eaf0 0x49eb10
@objc(ClawNativeObjectVariants) class ClawNativeObjectVariants: ClawNativeObjectAdapter {
    private struct Owner {
        let callback: UInt32, state: UInt32, images: UInt32, profile: UInt32
        let pins: [(UInt32, UInt32, ClawTokenHeap.AllocationIdentity)]
        let links: [(UInt32, UInt32)]
    }
    private var owners: [UInt32: Owner] = [:]
    private var pins: [(UInt32, UInt32, ClawTokenHeap.AllocationIdentity)] = []
    private var links: [(UInt32, UInt32)] = []
    private var soundBank: UInt32?
    private var active: UInt32?
    private(set) var memory: ClawNativeMfcMemory?
    var tokens: Set<UInt32> { Set(owners.keys) }
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
    private func prepare() -> Bool {
        guard let scene = connections.scene else { return false }
        let heap = scene.heap
        guard word(0x537210), word(0x532c0c), word(0x532c10),
              word(0x537b8c), word(0x537b90), word(0x53ebf0),
              word(0x513768, initial: Float(0.01).bitPattern), word(0x510020, initial: .max),
              heap.lookup(0x513768, words: 1)?[0] == Float(0.01).bitPattern,
              heap.lookup(0x510020, words: 1)?[0] == .max else { return false }
        if memory == nil {
            let imports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map {
                ($0.element, UInt32(0x710000 + $0.offset * 4))
            })
            do {
                memory = try ClawNativeMfcMemory(host: connections.host, sha256: ClawNativeMfcMemory.imageHash,
                    importTargets: imports, allocationBase: 0x69000000)
            } catch { return false }
        }
        return true
    }
    private func bindAudio(required: Bool) -> Bool {
        guard let scene = connections.scene, let parent = scene.heap.lookup(scene.sceneIdentity, words: 15) else { return false }
        if let soundBank { return parent[10] == soundBank }
        guard parent[10] != 0 else { return !required }
        let heap = scene.heap, bank = parent[10]
        guard let audio = scene.player.audio, audio.validAudioBinding(for: connections.host),
              heap.lookup(bank + 12, words: 1)?[0] == scene.sceneIdentity, pin(bank, 52) else { return false }
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
        parent[8] = audio.managerIdentity
        links += [(scene.sceneIdentity + 4, parent[1]), (parent[1] + 16, wrapper[4]),
                  (scene.sceneIdentity + 0x20, audio.managerIdentity),
                  (scene.sceneIdentity + 0x28, bank), (bank + 12, scene.sceneIdentity)]
        for name in ["LEVEL_FLOORSPIKEUP", "LEVEL_FLOORSPIKEDOWN", "LEVEL_SAWBLADEUP", "LEVEL_SAWBLADEDOWN", "LEVEL_STONERISE", "LEVEL_STONESINK"] {
            if let sound = audio.resolve(name: name) {
                guard audio.ownsAudioPool(sound.voicePoolToken), pin(sound.resourceToken, 64),
                      let resource = heap.lookup(sound.resourceToken, words: 5) else { return false }
                resource[3] = scene.sceneIdentity
                links += [(sound.resourceToken + 12, scene.sceneIdentity), (sound.resourceToken + 16, sound.voicePoolToken)]
            }
        }
        soundBank = bank
        return true
    }
    override func attach(_ object: ClawInteractionActor, callback: UInt32) -> Bool {
        let heap = connections.host.heap
        guard election.callbacks.contains(callback), object.primary.4 == callback, owners[object.token] == nil,
              let scene = connections.scene, object.actor.3 == scene.sceneIdentity,
              let resources = scene.objectResources, resources.heap === heap,
              let profile = heap.lookup(0x537960, words: 1)?[0],
              heap.lookup(profile, words: 48) != nil else { return false }
        var spans: [(UInt32, UInt32)] = [(object.token, 0x1b4), (object.actor.27, 0x174),
            (scene.sceneIdentity, 60), (0x537960, 4), (profile, 192)]
        var actorLinks: [(UInt32, UInt32)] = [(scene.sceneIdentity + 0x2c, 0x63000000)]
        if object.actor.92 != 0 {
            guard let resource = resources.images(token: object.actor.92),
                  let images = heap.lookup(object.actor.92, words: 27),
                  images[6] == UInt32(resource.table.count), images[6] > 0, images[6] <= UInt32.max / 4 else { return false }
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
        guard (memory != nil || prepare()), bindAudio(required: false),
              actorLinks.allSatisfy({ heap.lookup($0.0, words: 1)?[0] == $0.1 }) else { return false }
        scene.write(object)
        owners[object.token] = Owner(callback: callback, state: object.actor.27, images: object.actor.92,
            profile: profile, pins: actorPins, links: actorLinks)
        return true
    }
    private func valid(_ actor: UInt32) -> Bool {
        let heap = connections.host.heap
        guard let owner = owners[actor], let scene = connections.scene, scene.heap === heap,
              scene.objectResources?.heap === heap,
              heap.lookup(actor + 0x6c, words: 1)?[0] == owner.state,
              heap.lookup(owner.state + 0x10, words: 1)?[0] == owner.callback,
              heap.lookup(actor + 12, words: 1)?[0] == scene.sceneIdentity,
              heap.lookup(actor + 0x170, words: 1)?[0] == owner.images,
              heap.lookup(0x537960, words: 1)?[0] == owner.profile else { return false }
        return (owner.pins + pins).allSatisfy { heap.containingAllocationIdentity(at: $0.0, count: $0.1) === $0.2 } &&
            (owner.links + links).allSatisfy { heap.lookup($0.0, words: 1)?[0] == $0.1 }
    }
    override func remove(_ actor: UInt32) { owners.removeValue(forKey: actor) }
    override func callback(_ function: UInt32, actor: UInt32) {
        guard connections.active === self, active == nil, owners[actor]?.callback == function,
              valid(actor), bindAudio(required: true), let scene = connections.scene else { connections.reject(actor); return }
        active = actor
        defer { active = nil }
        let host = connections.host
        host.heap.lookup(0x537210, words: 1)![0] = scene.gameTime
        host.heap.lookup(0x532c0c, words: 1)![0] = scene.player.audio?.routing.managerAvailable ?? 0
        host.heap.lookup(0x532c10, words: 1)![0] = scene.player.audio?.routing.masterVolume ?? 0
        connections.record("ClawNativeObjectVariants"); connections.record(String(format: "0x%x", function))
        var call = ClawCall(); call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        guard let memory, let audio = scene.player.audio else { connections.reject(actor); return }
        _ = host.withObjectAllocation(provider: memory, audio: audio) { host.invoke(call) }
        if !valid(actor) { connections.reject(actor) }
    }
    override func service(_ call: ClawCall) -> UInt32? {
        guard connections.active === self, let actor = active, valid(actor), let scene = connections.scene,
              call.function == 0x4f6286, call.argumentCount == 2, call.receiver2 == 0,
              call.x87ArgumentCount == 0, let output = connections.host.bytes(call.arguments.1, count: 4) else { return nil }
        let animationKeys: Set<UInt32>, soundKeys: Set<UInt32>
        switch owners[actor]!.callback {
        case 0x461fe0, 0x462000, 0x462020:
            animationKeys = [0x52959c, 0x5295b0]; soundKeys = [0x529584, 0x5295c0]
        case 0x4622f0, 0x462310:
            animationKeys = [0x5295d4, 0x5295fc, 0x529610]; soundKeys = [0x5295e8, 0x529624]
        default:
            animationKeys = [0x52dd04, 0x52dd14]; soundKeys = [0x52dd7c, 0x52dd8c]
        }
        let token: UInt32
        if animationKeys.contains(call.arguments.0) {
            guard call.receiver == 0x63000010 else { return nil }
            connections.record("ClawActorResources.0x4f6286")
            token = scene.resolveResource(dictionary: call.receiver, name: call.arguments.0)
        } else if soundKeys.contains(call.arguments.0) {
            guard let bank = soundBank, call.receiver == bank + 0x10,
                  let name = clawOriginalResourceNames[call.arguments.0],
                  let audio = scene.player.audio, audio.validAudioBinding(for: connections.host) else { return nil }
            connections.record("ClawNativeAudio.0x4f6286")
            token = audio.resolve(name: name)?.resourceToken ?? 0
        } else { return nil }
        guard scene.fault == 0, valid(actor) else { connections.host.fail(UInt32(CLAW_FAULT_HOST), at: call.function); return nil }
        withUnsafeBytes(of: token.littleEndian) { output.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 4) }
        return token == 0 ? 0 : 1
    }
}
