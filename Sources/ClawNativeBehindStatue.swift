import Foundation

// The original callback sets the shared statue variant and descriptor before
// entering the canonical crate owner. CrateHit later uses the scene's crate
// and pickup owners, with the same global synchronized by dispatchSingleCrate.
@objc(ClawNativeBehindStatue) class ClawNativeBehindStatue: ClawNativeObjectAdapter {
    private struct Owner {
        let actor: ClawTokenHeap.AllocationIdentity
        let state: UInt32
        let identity: ClawTokenHeap.AllocationIdentity
    }
    private var owners: [UInt32: Owner] = [:]
    private var projection: [(UInt32, UInt32, ClawTokenHeap.AllocationIdentity)] = []
    private var active: UInt32?
    private(set) var memory: ClawNativeMfcMemory?
    var tokens: Set<UInt32> { Set(owners.keys) }
    var evidenceSpans: [(UInt32, UInt32)] { projection.map { ($0.0, $0.1) } }
    override class var services: Set<UInt32> { [0x4f6286] }
    override class var stacklessCallerReserve: UInt32? { 0x40 }

    private func storage(_ token: UInt32, _ count: UInt32) -> UnsafeMutablePointer<UInt8>? {
        let heap = connections.host.heap
        let bytes: UnsafeMutablePointer<UInt8>
        if let existing = heap.lookupBytes(token, count: count) { bytes = existing }
        else {
            guard !heap.overlaps(token, count: (count + 3) & ~3) else { return nil }
            bytes = heap.storeBytes(token: token, count: count)
        }
        guard let identity = heap.containingAllocationIdentity(at: token, count: count) else { return nil }
        if !projection.contains(where: { $0.0 == token }) { projection.append((token, count, identity)) }
        return bytes
    }
    private func immutable(_ token: UInt32, _ bytes: [UInt8]) -> Bool {
        let count = UInt32(bytes.count)
        if let existing = connections.host.heap.lookupBytes(token, count: count),
           Array(UnsafeBufferPointer(start: existing, count: bytes.count)) != bytes { return false }
        guard let target = storage(token, count) else { return false }
        target.update(from: bytes, count: bytes.count); return true
    }
    private func setup() -> Bool {
        guard let scene = connections.scene, let crates = scene.singleCrates else { return false }
        if memory != nil { return true }
        do {
            let imports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map {
                ($0.element, UInt32(0x710000 + $0.offset * 4))
            })
            let memory = try ClawNativeMfcMemory(host: connections.host, sha256: ClawNativeMfcMemory.imageHash,
                importTargets: imports, allocationBase: 0x69000000, sceneObjectAllocations: true)
            let table: [UInt32] = [0x4f701d,0x4c80c0,0x4c9e30,0x4c96b0,0x4c9e30,
                                  0x4c80a0,0x4bd250,0x4c81b0,0x4c80b0,0x4c8160]
            guard immutable(0x513740, table.withUnsafeBytes { Array($0) }),
                  immutable(0x5228dc, Array("CrateHit".utf8) + [0]),
                  immutable(0x510020, [255,255,255,255]),
                  let registry = scene.heap.lookup(scene.sceneIdentity + 0x14, words: 1)?[0],
                  storage(registry, 0x14) != nil, scene.entry(named: "CrateHit") != 0 else { return false }
            if scene.heap.lookup(0x52a194, words: 1) == nil {
                guard storage(0x52a194, 4) != nil else { return false }
                scene.heap.lookup(0x52a194, words: 1)![0] = crates.globals.pointee.crateImageChoice
            } else if storage(0x52a194, 4) == nil { return false }
            guard scene.registerObjectAllocationOwner(memory) else { return false }
            self.memory = memory
            return true
        } catch { return false }
    }
    override func attach(_ object: ClawInteractionActor, callback: UInt32) -> Bool {
        let heap = connections.host.heap
        guard callback == 0x4717b0, object.primary.4 == callback, owners[object.token] == nil,
              let actor = heap.allocationIdentity(at: object.token, count: 0x1b4),
              let state = heap.allocationIdentity(at: object.actor.27, count: 0x174), setup() else { return false }
        connections.scene?.write(object)
        owners[object.token] = Owner(actor: actor, state: object.actor.27, identity: state)
        connections.scene?.singleCrates?.attach(object)
        return true
    }
    private func valid(_ actor: UInt32) -> Bool {
        let heap = connections.host.heap
        guard let owner = owners[actor], heap.allocationIdentity(at: actor, count: 0x1b4) === owner.actor,
              heap.allocationIdentity(at: owner.state, count: 0x174) === owner.identity,
              heap.lookup(actor + 0x6c, words: 1)?[0] == owner.state,
              heap.lookup(owner.state + 0x10, words: 1)?[0] == 0x4717b0,
              projection.allSatisfy({ heap.containingAllocationIdentity(at: $0.0, count: $0.1) === $0.2 }) else { return false }
        return true
    }
    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x4717b0, active == nil, valid(actor), let memory,
              let scene = connections.scene, let crates = scene.singleCrates else { connections.reject(actor); return }
        active = actor; defer { active = nil }
        connections.record("ClawNativeBehindStatue"); connections.record("0x4717b0")
        var call = ClawCall(); call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        let result = connections.host.withObjectAllocation(provider: memory) { connections.host.invoke(call) }
        guard valid(actor), let variant = scene.heap.lookup(0x52a194, words: 1) else { connections.reject(actor); return }
        crates.globals.pointee.crateImageChoice = variant[0]
        if result?.completed != true && connections.host.fault == nil { connections.reject(actor) }
    }
    override func remove(_ actor: UInt32) {
        // The scene retains Memory and routes source destruction through it.
        owners.removeValue(forKey: actor)
    }
    override func service(_ call: ClawCall) -> UInt32? {
        guard let actor = active, valid(actor), let scene = connections.scene,
              call.function == 0x4f6286, call.argumentCount == 2, call.receiver2 == 0,
              call.x87ArgumentCount == 0, call.arguments.0 == 0x5228dc,
              let world = scene.heap.lookup(actor + 0x0c, words: 1)?[0],
              let registry = scene.heap.lookup(world + 0x14, words: 1)?[0], call.receiver == registry + 16,
              let output = connections.host.bytes(call.arguments.1, count: 4) else { return nil }
        let token = scene.entry(named: "CrateHit")
        guard token != 0 else { return nil }
        connections.record("ClawNativeScene.CrateHit.0x4f6286")
        withUnsafeBytes(of: token.littleEndian) { output.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 4) }
        return 1
    }
}
