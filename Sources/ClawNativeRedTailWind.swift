import Foundation

// The callback, constructor, binders and state methods remain canonical owners.
// This adapter transports the scene's physical resources and registry storage.
@objc(ClawNativeRedTailWind) class ClawNativeRedTailWind: ClawNativeObjectAdapter {
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
    override class var services: Set<UInt32> { [0x4f6286, 0x4f6974, 0x4a3050, 0x4f51c5, 0x711100, 0x711104, 0x711108, 0x71110c, 0x546cdc, 0x546d5c, 0x4a5290, 0x4b0d60, 0x4b0d30] }
    override class var stacklessCallerReserve: UInt32? { 0x100 }
    private let tables: [(UInt32, Int)] = [(0x537668, 11), (0x537698, 9), (0x53c208, 9)]
    private static let names: [UInt32: String] = [0x522d54: "LogicHit", 0x522d48: "LogicAttack", 0x523604: "ES_IDLE", 0x52bb28: "ES_BLOW",
        0x52bb4c: "LEVEL_REDTAIL_WINDWHISTLING", 0x522a1c: "WindDebris",
        0x52dde4: "LEVEL_WINDGRASS", 0x52ddf4: "LEVEL_WINDLEAF", 0x52de04: "LEVEL_WINDSAND",
        0x52417c: "GAME_CYCLE50", 0x52ddbc: "ES_MOVING"]

    required init(connections: ClawNativeObjectConnections, election: ClawNativeObjectConnections.Election) {
        super.init(connections: connections, election: election)
        // Reserve each complete original table before another adapter borrows
        // its nine active words. No state entries are manufactured here.
        for (token, _) in tables {
            if storage(token, 44) == nil { connections.reject(token) }
        }
    }

    private func storage(_ token: UInt32, _ count: UInt32) -> UnsafeMutablePointer<UInt8>? {
        let heap = connections.host.heap
        let bytes: UnsafeMutablePointer<UInt8>
        if let existing = heap.lookupBytes(token, count: count) { bytes = existing }
        else {
            guard token != 0, !heap.overlaps(token, count: (count + 3) & ~3) else { return nil }
            bytes = heap.storeBytes(token: token, count: count)
        }
        guard let identity = heap.containingAllocationIdentity(at: token, count: count) else { return nil }
        if !projection.contains(where: { $0.0 == token }) { projection.append((token, count, identity)) }
        return bytes
    }
    private func words(_ token: UInt32, _ values: [UInt32]) -> Bool {
        if let existing = connections.host.heap.lookup(token, words: UInt32(values.count)),
           Array(UnsafeBufferPointer(start: existing, count: values.count)) != values { return false }
        guard let p = storage(token, UInt32(values.count * 4)) else { return false }
        values.withUnsafeBytes { p.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: $0.count) }
        return true
    }
    private func setup() -> Bool {
        guard let scene = connections.scene, let registry = scene.stateRegistry else { return false }
        if memory != nil { return synchronizeRegistry(toHeap: true) }
        do {
            let imports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map { ($0.element, UInt32(0x710000 + $0.offset * 4)) })
            let memory = try ClawNativeMfcMemory(host: connections.host, sha256: ClawNativeMfcMemory.imageHash,
                importTargets: imports, allocationBase: 0x6ab00000, sceneObjectAllocations: true)
            guard scene.registerObjectAllocationOwner(memory) else { return false }
            self.memory = memory
            // Reviewed vtable metadata; all callable slots retain their real owners.
            guard words(0x50f46c, [0x484d90,0x4c9e30,0x4848d0,0x4041b0,0x4c96b0,0x4bb030,0x4bb030,0x4c96b0,0x4c96b0]),
                  words(0x513740, [0x4f701d,0x4c80c0,0x4c9e30,0x4c96b0,0x4c9e30,0x4c80a0,0x4bd250,0x4c81b0,0x4c80b0,0x4c8160]),
                  words(0x50feec, [0x484d90,0x4c9e30,0x49f1c0,0x4063b0,0x4c96b0,0x4bb030,0x4bb030,0x4c96b0,0x4c96b0]),
                  words(0x50ff18, [0xd2f1a9fc,0x3f50624d]),
                  words(0x513e10, [0xffc00000,0xc1dfffff,0xff800000,0x41dfffff]), words(0x513e40, [24]),
                  words(0x546d5c, [0x711100]), words(0x546cdc, [0x711104]),
                  words(0x5469e8, [0x711108]), words(0x546cd4, [0x71110c]),
                  words(0x510020, [.max]), storage(0x537210, 4) != nil, storage(0x532c0c, 8) != nil,
                  storage(0x537e88, 4) != nil, storage(0x53c19c, 4) != nil,
                  words(0x52b34c, [UInt32(bitPattern: -300), 5000, 37100, 37900, 1920, 2150]) else { return false }
            for (address, name) in Self.names {
                let bytes = Array(name.utf8) + [0]
                guard let p = storage(address, UInt32(bytes.count)) else { return false }
                p.update(from: bytes, count: bytes.count)
            }
            // Materialize the existing registry's storage, never a manufactured
            // state/function table. Copy back synchronous mutable lookup fields.
            guard storage(registry.context.pointee.heapBase, registry.context.pointee.heapCapacity) != nil else { return false }
            for (token, _) in tables { guard storage(token, 44) != nil else { return false } }
            // Reuse the scene dictionaries for synchronous resource lookups.
            guard let world = scene.heap.lookup(scene.sceneIdentity, words: 15) else { return false }
            if world[4] == 0 { world[4] = scene.heap.allocate(bytes: 32) }
            if world[10] == 0 { world[10] = scene.heap.allocate(bytes: 52) }
            guard storage(world[5], 0x14) != nil, storage(world[10], 0x14) != nil,
                  scene.entry(named: "LogicHit") != 0, scene.entry(named: "LogicAttack") != 0 else { return false }
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
        guard callback == 0x4847b0, owners[object.token] == nil, object.primary.4 == callback,
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
              heap.lookup(owner.state + 0x10, words: 1)?[0] == 0x4847b0 else { return false }
        return owner.helper == 0 || (heap.lookup(owner.state + 0x18, words: 1)?[0] == owner.helper && memory?.ownsObjectAllocation(owner.helper, count: 0x5c) == true)
    }
    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x4847b0, active == nil, valid(actor), let memory, let scene = connections.scene,
              synchronizeRegistry(toHeap: true) else { connections.reject(actor); return }
        active = actor; defer { active = nil }
        scene.heap.lookup(0x537210, words: 1)!.pointee = scene.gameTime
        scene.heap.lookup(0x537e88, words: 1)!.pointee = 0x10002000
        scene.heap.lookup(0x532c0c, words: 2)![0] = scene.player.audio?.routing.managerAvailable ?? 0
        scene.heap.lookup(0x532c0c, words: 2)![1] = scene.player.audio?.routing.masterVolume ?? 0
        connections.record("ClawNativeRedTailWind"); connections.record("0x4847b0")
        var call = ClawCall(); call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        let result = connections.host.withObjectAllocation(provider: memory, audio: scene.player.audio) { connections.host.invoke(call) }
        if result?.completed == true, let state = owners[actor]?.state {
            let helper = scene.heap.lookup(state + 0x18, words: 1)![0]
            guard memory.ownsObjectAllocation(helper, count: 0x5c) else { connections.reject(helper); return }
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
    @discardableResult func retire(_ actor: UInt32, retireSecondary: Bool = false) -> Bool {
        guard active == nil, valid(actor), let memory, owners[actor]?.helper != 0 else {
            connections.reject(actor); return false
        }
        guard connections.host.retireRedTailWind(actor: actor, provider: memory, retireSecondary: retireSecondary) else { return false }
        owners[actor]!.helper = 0
        connections.record("ClawNativeRedTailWind.0x484d90")
        return true
    }
    // The actor destructor inlines primary cleanup, which clears the callback
    // before reaching the helper. Retire at the scene teardown boundary while
    // the host can still prove the complete actor/logic/helper chain.
    func prepareActorDestruction(_ actor: UInt32) -> Bool? {
        guard owners[actor] != nil else { return nil }
        guard valid(actor), active == nil else { connections.reject(actor); return false }
        return owners[actor]!.helper == 0 || retire(actor, retireSecondary: true)
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
        if call.function == 0x4f6286 {
            guard call.argumentCount == 2, let output = connections.host.bytes(call.arguments.1, count: 4),
                  let name = Self.names[call.arguments.0],
                  let world = heap.lookup(actor + 0xc, words: 1)?[0] else { return nil }
            let token: UInt32
            if call.receiver == (heap.lookup(world + 0x14, words: 1)?[0]).map({ $0 + 16 }),
               ["LogicHit", "LogicAttack", "WindDebris"].contains(name) { token = scene.entry(named: name) }
            else if call.receiver == (heap.lookup(world + 0x28, words: 1)?[0]).map({ $0 + 16 }),
                    name == "LEVEL_REDTAIL_WINDWHISTLING" {
                token = scene.player.audio?.resolve(name: name)?.resourceToken ?? 0
            } else if call.receiver == (heap.lookup(world + 0x10, words: 1)?[0]).map({ $0 + 16 }),
                      ["LEVEL_WINDGRASS", "LEVEL_WINDLEAF", "LEVEL_WINDSAND"].contains(name) {
                do { token = try scene.objectResources?.images(name: name)?.token ?? 0 } catch { return nil }
            } else if call.receiver == (heap.lookup(world + 0x2c, words: 1)?[0]).map({ $0 + 16 }), name == "GAME_CYCLE50" {
                do { token = try scene.objectResources?.sequence(name: name)?.token ?? 0 } catch { return nil }
            } else { return nil }
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
        let host = connections.host
        switch call.function {
        case 0x4f51c5:
            guard call.argumentCount == 1, let world = heap.lookup(actor + 0xc, words: 1)?[0],
                  let factory = heap.lookup(world + 8, words: 1)?[0], call.receiver == factory + 0x10,
                  memory?.ownsObjectAllocation(call.arguments.0, count: 0x1b4) == true,
                  let list = heap.lookup(call.receiver, words: 4) else { return nil }
            let node = heap.allocate(bytes: 12)
            guard node != 0, let record = heap.lookup(node, words: 3) else { return nil }
            record[0] = 0; record[1] = list[2]; record[2] = call.arguments.0
            if list[2] != 0 {
                guard let tail = heap.lookup(list[2], words: 3) else { heap.free(node); return nil }
                tail[0] = node
            } else { list[1] = node }
            list[2] = node; list[3] &+= 1
            return node
        case 0x4a3050:
            guard call.receiver == 0,call.argumentCount == 0 else { return nil }
            connections.record("ClawNativeRandom.0x4a3050")
            let result = scene.nextRandom();return scene.fault == 0 ? result:nil
        case 0x711100,0x711104,0x546cdc,0x546d5c:
            let set = call.function == 0x711100 || call.function == 0x546d5c
            guard call.receiver == 0,call.argumentCount == (set ? 5:1),let p = host.bytes(call.arguments.0,count:16) else { return nil }
            let values: [UInt32] = set ? [call.arguments.1,call.arguments.2,call.arguments.3,call.arguments.4]:[0,0,0,0]
            values.withUnsafeBytes { p.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:16) };return 1
        case 0x711108:
            guard call.receiver == 0,call.argumentCount == 1,let p = host.bytes(call.arguments.0,count:4) else { return nil }
            return p.withMemoryRebound(to:UInt32.self,capacity:1) { $0.pointee &-= 1;return $0.pointee }
        case 0x71110c:
            guard call.receiver == 0,call.argumentCount == 3,let p = host.bytes(call.arguments.0,count:16) else { return nil }
            let r = (0..<4).map { UnsafeRawPointer(p.advanced(by:$0*4)).loadUnaligned(as:Int32.self) }
            let x = Int32(bitPattern:call.arguments.1),y = Int32(bitPattern:call.arguments.2)
            return r[0] <= x && x < r[2] && r[1] <= y && y < r[3] ? 1:0
        case 0x4a5290:
            guard call.receiver == 0,call.argumentCount == 3,call.arguments.2 <= 0x400000,
                  let src = host.bytes(call.arguments.1,count:call.arguments.2),let dst = host.bytes(call.arguments.0,count:call.arguments.2) else { return nil }
            let bytes = Array(UnsafeBufferPointer(start:src,count:Int(call.arguments.2)));dst.update(from:bytes,count:bytes.count);return call.arguments.0
        case 0x4b0d60,0x4b0d30:
            guard call.receiver == 0,call.argumentCount == 1,call.arguments.0 <= 255 else { return nil }
            let c = call.arguments.0
            return call.function == 0x4b0d60 ? (c == 32 || (9...13).contains(c) ? 8:0):((48...57).contains(c) ? 4:0)
        default:return nil
        }
    }
}
