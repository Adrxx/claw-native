import Foundation

// The callback, constructor, binders and state methods remain canonical owners.
// This adapter transports the scene's physical resources and registry storage.
@objc(ClawNativeSkullCannon) class ClawNativeSkullCannon: ClawNativeObjectAdapter {
    private struct Owner {
        let actor: ClawTokenHeap.AllocationIdentity
        let state: UInt32
        let identity: ClawTokenHeap.AllocationIdentity
        var helper: UInt32 = 0
    }
    // Scene teardown keeps this ledger alive even after an election is replaced.
    private final class Allocations: ClawSceneObjectAllocationOwner {
        let memory: ClawNativeMfcMemory
        var issued: [UInt32: UInt32] = [:]
        init(_ memory: ClawNativeMfcMemory) { self.memory = memory }
        var sceneObjectHeap: ClawTokenHeap { memory.host.heap }
        var canRegisterSceneObjectOwner: Bool { memory.validObjectAllocationBinding(for: memory.host) }
        func claimsSceneObject(_ token: UInt32) -> Bool { issued[token] != nil }
        func releaseSceneObject(_ token: UInt32) -> Bool {
            guard let count = issued[token], memory.ownsObjectAllocation(token, count: count) else { return false }
            var call = ClawCall(); call.function = 0x5469d8; call.stackPointer = UInt32(CLAW_STACK_TOP)
            call.argumentCount = 1; call.arguments.0 = token
            return memory.service(call) == 0
        }
    }
    private var owners: [UInt32: Owner] = [:]
    private var allocationOwner: Allocations?
    private var active: UInt32?
    private var projection: [(UInt32, UInt32, ClawTokenHeap.AllocationIdentity)] = []
    var tokens: Set<UInt32> { Set(owners.keys) }
    var memory: ClawNativeMfcMemory? { allocationOwner?.memory }
    var evidenceSpans: [(UInt32, UInt32)] { projection.map { ($0.0, $0.1) } }
    override class var services: Set<UInt32> { [0x4f6286, 0x4f6974] }
    override class var stacklessCallerReserve: UInt32? { 0x40 }
    private let tables: [(UInt32, Int)] = [(0x537668, 11), (0x537698, 9), (0x534bf8, 9)]
    private static let names: [UInt32: String] = [0x522d54: "LogicHit", 0x522d48: "LogicAttack",
        0x5234ec: "LS_HOME", 0x524538: "LS_VERTFIRING", 0x524548: "LS_FIRING"]

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
    private func words(_ token: UInt32, _ values: [UInt32]) -> Bool {
        guard let p = storage(token, UInt32(values.count * 4)) else { return false }
        values.withUnsafeBytes { p.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: $0.count) }
        return true
    }
    private func setup() -> Bool {
        guard let scene = connections.scene, let registry = scene.stateRegistry else { return false }
        if allocationOwner != nil { return true }
        do {
            let imports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map { ($0.element, UInt32(0x710000 + $0.offset * 4)) })
            let memory = try ClawNativeMfcMemory(host: connections.host, sha256: ClawNativeMfcMemory.imageHash,
                importTargets: imports, allocationBase: 0x66d00000)
            let owner = Allocations(memory)
            guard scene.registerObjectAllocationOwner(owner) else { return false }
            allocationOwner = owner
            // Reviewed vtable metadata; all callable slots retain their real owners.
            guard words(0x50f744, [0x484d90,0x4c9e30,0x4141f0,0x4041b0,0x4c96b0,0x4bb030,0x4bb030,0x4c96b0,0x4c96b0]),
                  words(0x513740, [0x4f701d,0x4c80c0,0x4c9e30,0x4c96b0,0x4c9e30,0x4c80a0,0x4bd250,0x4c81b0,0x4c80b0,0x4c8160]),
                  words(0x50b9c4, [50]), words(0x510020, [.max]), storage(0x537210, 4) != nil else { return false }
            for (address, name) in Self.names.merging([0x52c260: clawOriginalResourceNames[0x52c260]!,
                0x52c22c: clawOriginalResourceNames[0x52c22c]!, 0x52c244: clawOriginalResourceNames[0x52c244]!], uniquingKeysWith: { a, _ in a }) {
                let bytes = Array(name.utf8) + [0]
                guard let p = storage(address, UInt32(bytes.count)) else { return false }
                p.update(from: bytes, count: bytes.count)
            }
            // Materialize the existing registry's storage, never a manufactured
            // state/function table. Copy back synchronous mutable lookup fields.
            guard storage(registry.context.pointee.heapBase, registry.context.pointee.heapCapacity) != nil else { return false }
            for (token, count) in tables { guard storage(token, UInt32(count * 4)) != nil else { return false } }
            let logic = scene.heap.lookup(scene.sceneIdentity + 0x14, words: 1)![0]
            let animations = scene.heap.lookup(scene.sceneIdentity + 0x2c, words: 1)![0]
            guard animations != 0, storage(animations, 0x14) != nil,
                  storage(logic, 0x14) != nil, scene.entry(named: "LogicHit") != 0,
                  scene.entry(named: "LogicAttack") != 0,
                  try scene.objectResources?.images(name: "LEVEL_SKULLCANNON") != nil,
                  try scene.objectResources?.sequence(name: "LEVEL_SKULLCANNON_HOME") != nil,
                  try scene.objectResources?.sequence(name: "LEVEL_SKULLCANNON_FIRING") != nil else { return false }
            return synchronizeRegistry(toHeap: true)
        } catch { return false }
    }
    private func synchronizeRegistry(toHeap: Bool) -> Bool {
        guard let registry = connections.scene?.stateRegistry,
              projection.allSatisfy({ connections.host.heap.containingAllocationIdentity(at: $0.0, count: $0.1) === $0.2 }) else { return false }
        for (token, count) in tables {
            guard let destination = connections.host.heap.lookup(token, words: UInt32(count)) else { return false }
            var found = false
            for index in 0..<claw_logic_state_table_count(registry.registry) {
                guard let table = claw_logic_state_table_at(registry.registry, index), table.pointee.token == token else { continue }
                let writable = UnsafeMutablePointer(mutating: table)
                withUnsafeMutableBytes(of: &writable.pointee.words) { raw in
                    let data = raw.bindMemory(to: UInt32.self)
                    if toHeap { destination.update(from: data.baseAddress!, count: count) }
                    else { data.baseAddress!.update(from: destination, count: count) }
                }
                found = true; break
            }
            guard found else { return false }
        }
        let context = registry.context.pointee
        guard let p = connections.host.heap.lookupBytes(context.heapBase, count: context.heapCapacity), let arena = context.heap else { return false }
        if toHeap { p.update(from: arena, count: Int(context.heapUsed)) }
        else { arena.update(from: p, count: Int(context.heapUsed)) }
        return true
    }
    override func attach(_ object: ClawInteractionActor, callback: UInt32) -> Bool {
        let heap = connections.host.heap
        guard callback == 0x48a800, owners[object.token] == nil, object.primary.4 == callback,
              let actor = heap.allocationIdentity(at: object.token, count: 0x1b4),
              let state = heap.allocationIdentity(at: object.actor.27, count: 0x174),
              setup(), synchronizeRegistry(toHeap: true) else { return false }
        connections.scene?.write(object)
        owners[object.token] = Owner(actor: actor, state: object.actor.27, identity: state)
        return true
    }
    private func valid(_ actor: UInt32) -> Bool {
        let heap = connections.host.heap
        guard let owner = owners[actor], heap.allocationIdentity(at: actor, count: 0x1b4) === owner.actor,
              heap.allocationIdentity(at: owner.state, count: 0x174) === owner.identity,
              heap.lookup(actor + 0x6c, words: 1)?[0] == owner.state,
              heap.lookup(owner.state + 0x10, words: 1)?[0] == 0x48a800 else { return false }
        return owner.helper == 0 || (heap.lookup(owner.state + 0x18, words: 1)?[0] == owner.helper && memory?.ownsObjectAllocation(owner.helper, count: 0x7c) == true)
    }
    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x48a800, active == nil, valid(actor), let memory, let scene = connections.scene,
              synchronizeRegistry(toHeap: true) else { connections.reject(actor); return }
        active = actor; defer { active = nil }
        connections.host.heap.lookup(0x537210, words: 1)![0] = scene.gameTime
        connections.record("ClawNativeSkullCannon"); connections.record("0x48a800")
        var call = ClawCall(); call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        let result = connections.host.withObjectAllocation(provider: memory) { connections.host.invoke(call) }
        if result?.completed == true, let state = owners[actor]?.state {
            let helper = scene.heap.lookup(state + 0x18, words: 1)![0]
            guard memory.ownsObjectAllocation(helper, count: 0x7c) else { connections.reject(helper); return }
            owners[actor]!.helper = helper; allocationOwner!.issued[helper] = 0x7c
            for offset: UInt32 in [0x70, 0x78] {
                let token = scene.heap.lookup(actor + offset, words: 1)![0]
                guard memory.ownsObjectAllocation(token, count: 0x174) else { connections.reject(token); return }
                allocationOwner!.issued[token] = 0x174
            }
            if !synchronizeRegistry(toHeap: false) || !valid(actor) { connections.reject(actor) }
        }
    }
    // ActorDestruction reaches the helper through the real primary-state vtable.
    // Its callback field is already cleared at this point in the source order.
    func destructHelper(_ helper: UInt32, flags: UInt32) -> UInt32? {
        guard let pair = owners.first(where: { $0.value.helper == helper }), let scene = connections.scene else { return nil }
        let owner = pair.value, heap = scene.heap
        guard active == nil, heap.allocationIdentity(at: pair.key, count: 0x1b4) === owner.actor,
              heap.allocationIdentity(at: owner.state, count: 0x174) === owner.identity,
              heap.lookup(owner.state + 0x18, words: 1)?[0] == helper,
              memory?.ownsObjectAllocation(helper, count: 0x7c) == true else { connections.reject(helper); return 0 }
        var context = ClawStackedActorLifecycleContext(scene: scene.actorHost, fault: 0)
        var argument = flags, result: UInt32 = 0
        guard claw_stacked_actor_lifecycle_entry(0x484d90, helper, &argument, 1, &context, &result) == 1,
              context.fault == 0, scene.fault == 0 else { connections.reject(helper); return 0 }
        if flags & 1 != 0 { owners[pair.key]!.helper = 0 }
        connections.record("ClawStackedActorLifecycle.0x484d90")
        return result
    }
    override func remove(_ actor: UInt32) {
        guard let owner = owners.removeValue(forKey: actor), owner.helper != 0 else { return }
        if allocationOwner?.releaseSceneObject(owner.helper) != true { connections.reject(owner.helper) }
    }
    override func service(_ call: ClawCall) -> UInt32? {
        guard let actor = active, valid(actor), let scene = connections.scene,
              call.receiver2 == 0, call.x87ArgumentCount == 0 else { return nil }
        let heap = scene.heap
        if call.function == 0x4f6286 {
            guard call.argumentCount == 2, let output = connections.host.bytes(call.arguments.1, count: 4),
                  let name = Self.names[call.arguments.0] ?? clawOriginalResourceNames[call.arguments.0],
                  let world = heap.lookup(actor + 0xc, words: 1)?[0] else { return nil }
            let token: UInt32
            do {
                if call.receiver == heap.lookup(world + 0x14, words: 1)![0] + 16,
                   ["LogicHit", "LogicAttack"].contains(name) { token = scene.entry(named: name) }
                else if call.receiver == heap.lookup(world + 0x10, words: 1)![0] + 16,
                        name == "LEVEL_SKULLCANNON" { token = try scene.objectResources?.images(name: name)?.token ?? 0 }
                else if call.receiver == heap.lookup(world + 0x2c, words: 1)![0] + 16,
                        ["LEVEL_SKULLCANNON_HOME", "LEVEL_SKULLCANNON_FIRING"].contains(name) {
                    token = try scene.objectResources?.sequence(name: name)?.token ?? 0
                } else { return nil }
            } catch { return nil }
            guard token != 0 else { return nil }
            connections.record("ClawActorResources.0x4f6286")
            withUnsafeBytes(of: token.littleEndian) { output.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 4) }
            return 1
        }
        if call.function == 0x4f6974 {
            guard call.argumentCount == 1, call.arguments.0 == 0,
                  let table = heap.lookup(0x537698, words: 9), call.receiver >= table[4],
                  UInt64(call.receiver) < UInt64(table[4]) + UInt64(table[3] - table[2] + 1) * 4,
                  (call.receiver - table[4]) % 4 == 0,
                  let pointer = heap.lookup(call.receiver, words: 1)?[0], pointer >= 12,
                  let header = heap.lookup(pointer - 12, words: 3), Int32(bitPattern: header[0]) <= 1,
                  header[1] <= header[2], heap.lookupBytes(pointer, count: header[1] + 1) != nil else { return nil }
            connections.record("ClawNativeStateRegistry.0x4f6974"); return pointer
        }
        return nil
    }
}
