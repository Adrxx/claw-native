import Foundation

// The callback, constructor, binders and state methods remain canonical owners.
// This adapter transports the scene's physical resources and registry storage.
// claw-progress-class-owner: aquatis_dynamite 0x406dd0
@objc(ClawNativeAquatisDynamite) class ClawNativeAquatisDynamite: ClawNativeObjectAdapter {
    private struct Owner {
        let actor: ClawTokenHeap.AllocationIdentity
        let state: UInt32
        let identity: ClawTokenHeap.AllocationIdentity
        var helper: UInt32 = 0
    }
    private var owners: [UInt32: Owner] = [:]
    private(set) var memory: ClawNativeMfcMemory?
    private var active: UInt32?
    private var projection: [(UInt32, UInt32, ClawTokenHeap.AllocationIdentity)] = []
    var tokens: Set<UInt32> { Set(owners.keys) }
    var evidenceSpans: [(UInt32, UInt32)] { projection.map { ($0.0, $0.1) } }
    override class var services: Set<UInt32> { [0x4f6286, 0x4f6974, 0x4f51c5, 0x4f572a, 0x546d5c] }
    override class var stacklessCallerReserve: UInt32? { 0x100 }
    private let tables: [(UInt32, Int)] = [(0x537668, 11), (0x537698, 9), (0x5348b8, 9)]
    private static let names: [UInt32: String] = [0x522d54: "LogicHit", 0x522d48: "LogicAttack",
        0x523148: "LS_IDLE", 0x5235d0: "GAME_DYNAMITE", 0x522894: "AmmoPowerup"]

    private func storage(_ token: UInt32, _ count: UInt32) -> UnsafeMutablePointer<UInt8>? {
        let heap = connections.host.heap
        let bytes: UnsafeMutablePointer<UInt8>
        if let existing = heap.lookupBytes(token, count: count) { bytes = existing }
        else {
            guard token != 0, !heap.overlaps(token, count: (count + 3) & ~3) else { connections.reject(token); return nil }
            bytes = heap.storeBytes(token: token, count: count)
        }
        guard let identity = heap.containingAllocationIdentity(at: token, count: count) else { return nil }
        if !projection.contains(where: { $0.0 == token }) { projection.append((token, count, identity)) }
        return bytes
    }
    private func words(_ token: UInt32, _ values: [UInt32]) -> Bool {
        if let existing = connections.host.heap.lookup(token, words: UInt32(values.count)),
           Array(UnsafeBufferPointer(start: existing, count: values.count)) != values { connections.reject(token); return false }
        guard let p = storage(token, UInt32(values.count * 4)) else { return false }
        values.withUnsafeBytes { p.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: $0.count) }
        return true
    }
    private func setup() -> Bool {
        guard let scene = connections.scene, let registry = scene.stateRegistry else { return false }
        if memory != nil { return true }
        do {
            let imports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map { ($0.element, UInt32(0x710000 + $0.offset * 4)) })
            let memory = try ClawNativeMfcMemory(host: connections.host, sha256: ClawNativeMfcMemory.imageHash,
                importTargets: imports, allocationBase: 0x6a700000, sceneObjectAllocations: true)
            guard scene.registerObjectAllocationOwner(memory) else { return false }
            self.memory = memory
            // Reviewed vtable metadata; all callable slots retain their real owners.
            guard words(0x50b244, [0x484d90,0x4c9e30,0x406ef0,0x4041b0,0x4c96b0,0x407310,0x4bb030,0x4c96b0,0x4c96b0]),
                  words(0x513740, [0x4f701d,0x4c80c0,0x4c9e30,0x4c96b0,0x4c9e30,0x4c80a0,0x4bd250,0x4c81b0,0x4c80b0,0x4c8160]),
                  words(0x510020, [.max]), storage(0x537210, 4) != nil, storage(0x534874, 4) != nil, words(0x537e88, [scene.player.sceneSnapshot().token]) else { return false }
            for (address, name) in Self.names {
                let bytes = Array(name.utf8) + [0]
                guard let p = storage(address, UInt32(bytes.count)) else { return false }
                p.update(from: bytes, count: bytes.count)
            }
            // Materialize the existing registry's storage, never a manufactured
            // state/function table. Copy back synchronous mutable lookup fields.
            guard storage(registry.context.pointee.heapBase, registry.context.pointee.heapCapacity) != nil else { return false }
            for (token, count) in tables { guard storage(token, UInt32(count * 4)) != nil else { return false } }
            // Reuse the scene dictionaries for synchronous resource lookups.
            guard let world = scene.heap.lookup(scene.sceneIdentity, words: 15) else { return false }
            // The native loader binds decoded image sets directly. Give the
            // canonical image binder a physical dictionary identity in that
            // same scene; its lookup still resolves ClawActorResources.
            if world[4] == 0 { world[4] = scene.heap.allocate(bytes: 0x14) }
            if world[10] == 0 { world[10] = scene.heap.allocate(bytes: 0x14) }
            guard storage(world[10], 0x14) != nil, storage(world[11], 0x14) != nil, storage(world[5], 0x14) != nil, storage(world[4], 0x14) != nil,
                  scene.entry(named: "LogicHit") != 0, scene.entry(named: "LogicAttack") != 0,
                  scene.entry(named: "AmmoPowerup") != 0,
                  try scene.objectResources?.images(name: "GAME_DYNAMITE") != nil else { return false }
            // SetRect's import slot is data; the synchronous physical service
            // writes through host.bytes, including source stack output cells.
            guard words(0x546d5c, [0x710f00]) else { return false }
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
        guard callback == 0x406dd0, owners[object.token] == nil, object.primary.4 == callback,
              let actor = heap.allocationIdentity(at: object.token, count: 0x1b4),
              let state = heap.allocationIdentity(at: object.actor.27, count: 0x174), setup() else { return false }
        connections.scene?.write(object)
        owners[object.token] = Owner(actor: actor, state: object.actor.27, identity: state)
        return true
    }
    private func valid(_ actor: UInt32) -> Bool {
        let heap = connections.host.heap
        guard let owner = owners[actor], heap.allocationIdentity(at: actor, count: 0x1b4) === owner.actor,
              heap.allocationIdentity(at: owner.state, count: 0x174) === owner.identity,
              heap.lookup(actor + 0x6c, words: 1)?[0] == owner.state,
              heap.lookup(owner.state + 0x10, words: 1)?[0] == 0x406dd0 else { return false }
        return owner.helper == 0 || (heap.lookup(owner.state + 0x18, words: 1)?[0] == owner.helper && memory?.ownsObjectAllocation(owner.helper, count: 0x54) == true)
    }
    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x406dd0, active == nil, valid(actor), let memory, let scene = connections.scene,
              synchronizeRegistry(toHeap: true) else { connections.reject(actor); return }
        active = actor; defer { active = nil }
        scene.heap.lookup(0x537210, words: 1)!.pointee = scene.gameTime
        connections.record("ClawNativeAquatisDynamite"); connections.record("0x406dd0")
        var call = ClawCall(); call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        let result = connections.host.withObjectAllocation(provider: memory) { connections.host.invoke(call) }
        if result?.completed == true, let state = owners[actor]?.state {
            let helper = scene.heap.lookup(state + 0x18, words: 1)![0]
            guard memory.ownsObjectAllocation(helper, count: 0x54) else { connections.reject(helper); return }
            owners[actor]!.helper = helper
            connections.record("ClawNativeMfcMemory")
            for offset: UInt32 in [0x70, 0x78] {
                let token = scene.heap.lookup(actor + offset, words: 1)![0]
                guard memory.ownsObjectAllocation(token, count: 0x174) else { connections.reject(token); return }
            }
            if !synchronizeRegistry(toHeap: false) || !valid(actor) { connections.reject(actor) }
        }
    }
    // Retire while actor and primary logic still have their pinned identities.
    @discardableResult func retire(_ actor: UInt32) -> Bool {
        guard active == nil, valid(actor), let memory, owners[actor]?.helper != 0 else {
            connections.reject(actor); return false
        }
        guard connections.host.retireAquatisDynamite(actor: actor, provider: memory) else { return false }
        owners[actor]!.helper = 0
        connections.record("ClawNativeAquatisDynamite.0x484d90")
        return true
    }
    // The actor destructor inlines primary cleanup, which clears the callback
    // before reaching the helper. Retire at the scene teardown boundary while
    // the host can still prove the complete actor/logic/helper chain.
    func prepareActorDestruction(_ actor: UInt32) -> Bool? {
        guard owners[actor] != nil else { return nil }
        guard valid(actor), active == nil else { connections.reject(actor); return false }
        return owners[actor]!.helper == 0 || retire(actor)
    }
    func prepareLogicDestruction(_ logic: UInt32) -> Bool? {
        guard let actor = owners.first(where: { $0.value.state == logic })?.key else { return nil }
        return prepareActorDestruction(actor)
    }
    func destructHelper(_ helper: UInt32, flags: UInt32) -> UInt32? {
        guard let actor = owners.first(where: { $0.value.helper == helper && helper != 0 })?.key else { return nil }
        guard flags == 1, retire(actor) else { connections.reject(helper); return 0 }
        return helper
    }
    override func remove(_ actor: UInt32) {
        guard let owner = owners[actor] else { return }
        guard owner.helper == 0 else { connections.reject(owner.helper); return }
        owners.removeValue(forKey: actor)
    }
    override func service(_ call: ClawCall) -> UInt32? {
        guard let actor = active, valid(actor), let scene = connections.scene,
              call.receiver2 == 0, call.x87ArgumentCount == 0 else { return nil }
        let heap = scene.heap
        if call.function == 0x546d5c {
            guard call.argumentCount == 5, let output = connections.host.bytes(call.arguments.0, count: 16) else { return nil }
            for (index, value) in [call.arguments.1,call.arguments.2,call.arguments.3,call.arguments.4].enumerated() {
                UnsafeMutableRawPointer(output.advanced(by: index * 4)).storeBytes(of: value.littleEndian, as: UInt32.self)
            }
            connections.record("SetRect.0x546d5c"); return 1
        }
        if call.function == 0x4f51c5 || call.function == 0x4f572a {
            // MFC CPtrList insert/append is physical list storage. The real
            // factory selects position from scene actor depths before this call.
            let insert = call.function == 0x4f572a
            let actor = insert ? call.arguments.1 : call.arguments.0
            guard call.argumentCount == (insert ? 2 : 1), call.receiver == scene.containerToken + 0x10,
                  memory?.ownsObjectAllocation(actor, count: 0x1b4) == true,
                  let list = heap.lookup(call.receiver, words: 7) else { return nil }
            let next = insert ? call.arguments.0 : 0
            var previous = list[2]
            if insert {
                var cursor = list[1], seen: Set<UInt32> = []
                while cursor != 0 && cursor != next {
                    guard seen.insert(cursor).inserted, let node = heap.lookup(cursor, words: 3) else { return nil }
                    cursor = node[0]
                }
                guard cursor == next, next != 0, let node = heap.lookup(next, words: 3) else { return nil }
                previous = node[1]
            }
            guard previous == 0 || heap.lookup(previous, words: 3) != nil else { return nil }
            let node = heap.allocate(bytes: 12)
            guard node != 0, let words = heap.lookup(node, words: 3) else { return nil }
            words[0] = next; words[1] = previous; words[2] = actor
            if previous != 0 { heap.lookup(previous, words: 1)![0] = node } else { list[1] = node }
            if next != 0 { heap.lookup(next + 4, words: 1)![0] = node } else { list[2] = node }
            list[3] += 1
            connections.record("ClawNativeScene.CPtrList.0x" + String(call.function, radix: 16)); return node
        }
        if call.function == 0x4f6286 {
            guard call.argumentCount == 2, let output = connections.host.bytes(call.arguments.1, count: 4),
                  let name = Self.names[call.arguments.0],
                  let world = heap.lookup(actor + 0xc, words: 1)?[0] else { return nil }
            let token: UInt32
            do {
                if call.receiver == heap.lookup(world + 0x14, words: 1)![0] + 16,
                   ["LogicHit", "LogicAttack", "AmmoPowerup"].contains(name) { token = scene.entry(named: name) }
                else if call.receiver == heap.lookup(world + 0x10, words: 1)![0] + 16, name == "GAME_DYNAMITE" {
                    token = try scene.objectResources?.images(name: name)?.token ?? 0
                } else { return nil }
            } catch { return nil }
            guard token != 0 else { return nil }
            connections.record("ClawActorResources.0x4f6286")
            withUnsafeBytes(of: token.littleEndian) { output.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 4) }
            return token == 0 ? 0 : 1
        }
        if call.function == 0x4f6974 {
            guard call.argumentCount == 1, call.arguments.0 == 0,
                  let table = heap.lookup(0x537698, words: 9), call.receiver >= table[4], table[3] >= table[2],
                  UInt64(call.receiver) < UInt64(table[4]) + (UInt64(table[3]) - UInt64(table[2]) + 1) * 4,
                  (call.receiver - table[4]) % 4 == 0,
                  let pointer = heap.lookup(call.receiver, words: 1)?[0], pointer >= 12,
                  let header = heap.lookup(pointer - 12, words: 3), Int32(bitPattern: header[0]) <= 1,
                  header[1] <= header[2], header[1] < UInt32.max, heap.lookupBytes(pointer, count: header[1] + 1) != nil else { return nil }
            connections.record("ClawNativeStateRegistry.0x4f6974"); return pointer
        }
        return nil
    }
}
