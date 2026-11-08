import Foundation

// The canonical callback owns path construction, bounds and movement. This
// scene adapter supplies only physical allocation, resource lookup and time.
// claw-progress-class-owner: path_elevator 0x49ee30
@objc(ClawNativePathElevator)
final class ClawNativePathElevator: ClawNativeObjectAdapter {
    private struct Owner {
        let actor: ClawTokenHeap.AllocationIdentity
        let state: UInt32
        let identity: ClawTokenHeap.AllocationIdentity
        var helper: UInt32 = 0
    }
    private var owners: [UInt32: Owner] = [:]
    private var pins: [(UInt32, UInt32, ClawTokenHeap.AllocationIdentity)] = []
    private var activeActor: UInt32?
    private var imageRegistry: UInt32 = 0
    private var profileToken: UInt32 = 0
    private(set) var memory: ClawNativeMfcMemory?
    var tokens: Set<UInt32> { Set(owners.keys) }
    var evidenceSpans: [(UInt32, UInt32)] { pins.map { ($0.0, $0.1) } }
    override class var services: Set<UInt32> { [0x4f6286] }
    override class var stacklessCallerReserve: UInt32? { 0x100 }

    private func pin(_ token: UInt32, _ count: UInt32) -> Bool {
        guard let identity = connections.host.heap.containingAllocationIdentity(at: token, count: count) else { return false }
        if let old = pins.first(where: { $0.0 == token && $0.1 == count }) { return old.2 === identity }
        pins.append((token, count, identity)); return true
    }
    private func word(_ token: UInt32, value: UInt32? = nil) -> Bool {
        let heap = connections.host.heap
        if heap.lookup(token, words: 1) == nil {
            guard !heap.overlaps(token, count: 4) else { return false }
            heap.store(token: token, words: 1)[0] = value ?? 0
        }
        if let value, heap.lookup(token, words: 1)?[0] != value { return false }
        return pin(token, 4)
    }
    private func setup() -> Bool {
        guard let scene = connections.scene, scene.objectResources?.heap === scene.heap else { return false }
        if memory != nil { return true }
        let heap = scene.heap
        guard let profile = heap.lookup(0x537960, words: 1)?[0], pin(0x537960, 4), pin(profile, 192),
              word(0x537210), word(0x510020, value: .max), word(0x50fee4, value: 0x49f020),
              let parent = heap.lookup(scene.sceneIdentity, words: 15) else { return false }
        profileToken = profile
        // Identity of the physical image dictionary. Resource data and image
        // construction stay with the scene's existing ClawActorResources owner.
        if parent[4] == 0 { parent[4] = heap.allocate(bytes: 20) }
        imageRegistry = parent[4]
        guard pin(imageRegistry, 20) else { return false }
        do {
            let imports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map {
                ($0.element, UInt32(0x710000 + $0.offset * 4))
            })
            let provider = try ClawNativeMfcMemory(host: connections.host, sha256: ClawNativeMfcMemory.imageHash,
                importTargets: imports, allocationBase: 0x68e00000, sceneObjectAllocations: true)
            guard scene.registerObjectAllocationOwner(provider) else { return false }
            memory = provider
            return true
        } catch { return false }
    }
    override func attach(_ object: ClawInteractionActor, callback: UInt32) -> Bool {
        let heap = connections.host.heap
        guard callback == 0x49ee30, object.primary.4 == callback, owners[object.token] == nil,
              let actor = heap.allocationIdentity(at: object.token, count: 0x1b4),
              let state = heap.allocationIdentity(at: object.actor.27, count: 0x174), setup() else { return false }
        connections.scene?.write(object)
        owners[object.token] = Owner(actor: actor, state: object.actor.27, identity: state)
        return true
    }
    private func validStorage(_ actor: UInt32) -> Bool {
        let heap = connections.host.heap
        guard let scene = connections.scene, let owner = owners[actor],
              heap.lookup(actor + 0xc, words: 1)?[0] == scene.sceneIdentity,
              heap.lookup(0x537960, words: 1)?[0] == profileToken,
              heap.lookup(scene.sceneIdentity + 0x10, words: 1)?[0] == imageRegistry,
              heap.allocationIdentity(at: actor, count: 0x1b4) === owner.actor,
              heap.allocationIdentity(at: owner.state, count: 0x174) === owner.identity,
              heap.lookup(actor + 0x6c, words: 1)?[0] == owner.state else { return false }
        return pins.allSatisfy { heap.containingAllocationIdentity(at: $0.0, count: $0.1) === $0.2 }
    }
    @discardableResult func syncGlobals() -> Bool {
        guard let scene = connections.scene,
              let application = scene.heap.lookup(scene.ownerIdentity + 4, words: 1)?[0],
              scene.heap.lookup(application + 0x2c, words: 1)?[0] == scene.ownerIdentity,
              word(0x5371fc), pin(application, 0x30), pin(scene.ownerIdentity, 0x18),
              scene.heap.lookup(scene.sceneIdentity + 0x10, words: 1)?[0] == imageRegistry else { return false }
        scene.heap.lookup(0x5371fc, words: 1)![0] = application
        scene.heap.lookup(0x537210, words: 1)![0] = scene.gameTime
        return true
    }
    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x49ee30, activeActor == nil, validStorage(actor), let memory,
              let owner = owners[actor], connections.host.heap.lookup(owner.state + 0x10, words: 1)?[0] == function,
              syncGlobals() else { connections.reject(actor); return }
        activeActor = actor; defer { activeActor = nil }
        connections.record("ClawNativePathElevator"); connections.record("0x49ee30")
        var call = ClawCall(); call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        let result = connections.host.withObjectAllocation(provider: memory) { connections.host.invoke(call) }
        if result?.completed == true {
            guard validStorage(actor), let helper = connections.host.heap.lookup(owner.state + 0x18, words: 1)?[0],
                  memory.ownsObjectAllocation(helper, count: 0x18),
                  let path = connections.host.heap.lookup(helper + 8, words: 1)?[0],
                  memory.ownsObjectAllocation(path, count: 0x104) else { connections.reject(actor); return }
            owners[actor]!.helper = helper
            connections.record("ClawNativeMfcMemory.owned-path-and-helper")
        }
    }
    override func service(_ call: ClawCall) -> UInt32? {
        guard call.function == 0x4f6286, call.argumentCount == 2, call.receiver == imageRegistry + 0x10,
              call.arguments.0 == 0x528a4c, let actor = activeActor, validStorage(actor),
              let scene = connections.scene, let resources = scene.objectResources,
              let output = connections.host.bytes(call.arguments.1, count: 4) else { return nil }
        do {
            let token = try resources.images(name: "LEVEL_TRAPELEVATOR")?.token ?? 0
            var value = token.littleEndian
            withUnsafeBytes(of: &value) { output.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 4) }
            connections.record("ClawActorResources.0x4f6286")
            return token == 0 ? 0 : 1
        } catch { connections.host.fail(UInt32(CLAW_FAULT_HOST), at: call.function); return nil }
    }
    // The logic owner has already cleared its callback before this virtual
    // call. The real helper destructor frees path then helper through Memory.
    func destructHelper(_ helper: UInt32, flags: UInt32) -> UInt32? {
        guard let pair = owners.first(where: { $0.value.helper == helper }) else { return nil }
        guard activeActor == nil, validStorage(pair.key), let memory,
              connections.host.heap.lookup(pair.value.state + 0x18, words: 1)?[0] == helper else {
            connections.reject(helper); return 0
        }
        let host = connections.host, reserve = host.stacklessCallerReserve
        host.stacklessCallerReserve = Self.stacklessCallerReserve
        defer { host.stacklessCallerReserve = reserve }
        connections.record("scene.destruction->0x49f020->ClawNativeMfcMemory")
        var call = ClawCall(); call.function = 0x49f020; call.receiver = helper; call.argumentCount = 1; call.arguments.0 = flags
        return host.withObjectAllocation(provider: memory) { host.invoke(call) }?.eax ?? 0
    }
    override func remove(_ actor: UInt32) { owners.removeValue(forKey: actor) }
}
