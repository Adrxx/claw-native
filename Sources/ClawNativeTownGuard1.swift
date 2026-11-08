import Foundation

// The callback, constructor, binders and state methods remain canonical owners.
// This adapter transports the scene's physical resources and registry storage.
@objc(ClawNativeTownGuard1) class ClawNativeTownGuard1: ClawNativeObjectAdapter {
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
    override class var services: Set<UInt32> { [0x4f6286, 0x4f6974, 0x4a3050, 0x4a5290, 0x4b0d60, 0x4b0d30, 0x711100, 0x711104, 0x711108, 0x71110c, 0x546cdc, 0x546d5c] }
    override class var stacklessCallerReserve: UInt32? { 0x100 }
    private let tables: [(UInt32, Int)] = [(0x537668, 11), (0x537698, 9), (0x537638, 9), (0x537878, 9), (0x53ca70, 9)]
    private static let names: [UInt32: String] = [
        0x522d54: "LogicHit",
        0x522d48: "LogicAttack",
        0x523148: "LS_IDLE",
        0x5234b4: "GAME_NULL",
        0x52d204: "LEVEL_TOWNGUARD1",
        0x52d47c: "LEVEL_TOWNGUARD1_STRIKE2",
        0x52d1e8: "LEVEL_TOWNGUARD1_ADVANCE",
        0x52d1c8: "LEVEL_TOWNGUARD1_FASTADVANCE",
        0x52d1ac: "LEVEL_TOWNGUARD1_STRIKE1",
        0x52d190: "LEVEL_TOWNGUARD1_KILLFALL",
        0x52d178: "LEVEL_TOWNGUARD1_IDLE1",
        0x52d160: "LEVEL_TOWNGUARD1_IDLE2",
        0x52d148: "LEVEL_TOWNGUARD1_HITLOW",
        0x52d12c: "LEVEL_TOWNGUARD1_HITHIGH",
        0x52d114: "LEVEL_TOWNGUARD1_JUMP",
        0x52d0fc: "LEVEL_TOWNGUARD1_HOME",
        0x52d0e0: "LEVEL_TOWNGUARD1_LIFTED1",
        0x52d0c4: "LEVEL_TOWNGUARD1_LIFTED2",
        0x52d0ac: "LEVEL_TOWNGUARD1_THROWN",
        0x52d090: "LEVEL_TOWNGUARD_00350007",
        0x52d074: "LEVEL_TOWNGUARD_00350008",
        0x52d058: "LEVEL_TOWNGUARD_00390011",
        0x52d040: "LEVEL_TOWNGUARD_LEJUMP2",
        0x52d024: "LEVEL_TOWNGUARD_00390035",
        0x52d008: "LEVEL_TOWNGUARD_00390002",
        0x52cfec: "LEVEL_TOWNGUARD_00390028",
        0x52cfd0: "LEVEL_TOWNGUARD_00390034",
        0x52cfb4: "LEVEL_TOWNGUARD_00390015",
        0x52cf98: "LEVEL_TOWNGUARD_OFCHITHI",
        0x52cf7c: "LEVEL_TOWNGUARD_00350009",
        0x52cf60: "LEVEL_TOWNGUARD_OFCDKSTB",
        0x52cf44: "LEVEL_TOWNGUARD_00390016",
        0x52cf2c: "LEVEL_TOWNGUARD_BLOCK1",
        0x52cf14: "LEVEL_TOWNGUARD_BLOCK2",
        0x5266ec: "GAME_SPLASH",
        0x524870: "GAME_HIT1",
        0x524864: "GAME_HIT2",
        0x524858: "GAME_HIT3",
        0x52484c: "GAME_HIT4",
        0x5266dc: "GAME_PURELEASE1",
        0x5246f8: "LEVEL_DEATHTILE",
        0x527d50: "GAME_SOLHITL2",
        0x527d40: "GAME_SOLHITHI",
        0x527d34: "GAME_LELAND"]

    private func storage(_ token: UInt32, _ count: UInt32) -> UnsafeMutablePointer<UInt8>? {
        let heap = connections.host.heap
        let bytes: UnsafeMutablePointer<UInt8>
        if let existing = heap.lookupBytes(token, count: count) { bytes = existing }
        else {
            guard token != 0, !heap.overlaps(token, count: (count + 3) & ~3) else { print("TownGuard1 storage overlap", String(token, radix: 16), count); return nil }
            bytes = heap.storeBytes(token: token, count: count)
        }
        guard let identity = heap.containingAllocationIdentity(at: token, count: count) else { return nil }
        if !projection.contains(where: { $0.0 == token }) { projection.append((token, count, identity)) }
        return bytes
    }
    private func words(_ token: UInt32, _ values: [UInt32]) -> Bool {
        // Existing scene constants may be separate word allocations. Preserve
        // their identities rather than replacing another scene owner's backing.
        if connections.host.heap.lookup(token, words: UInt32(values.count)) == nil,
           connections.host.heap.overlaps(token, count: UInt32(values.count * 4)), values.count > 1 {
            return values.enumerated().allSatisfy { words(token + UInt32($0.offset * 4), [$0.element]) }
        }
        if let existing = connections.host.heap.lookup(token, words: UInt32(values.count)),
           Array(UnsafeBufferPointer(start: existing, count: values.count)) != values { print("TownGuard1 metadata mismatch", String(token, radix: 16)); return false }
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
                importTargets: imports, allocationBase: 0x69f00000, sceneObjectAllocations: true)
            guard scene.registerObjectAllocationOwner(memory) else { return false }
            self.memory = memory
            // Reviewed vtable metadata; all callable slots retain their real owners.
            guard words(0x50fabc, [0x496840, 0x497510, 0x497130, 0x44d3c0, 0x405000, 0x44df60, 0x4bb030, 0x4c96b0, 0x44cfd0, 0x43dfa0]),
                  words(0x50fb04, [0x497970]),
                  words(0x513740, [0x4f701d, 0x4c80c0, 0x4c9e30, 0x4c96b0, 0x4c9e30, 0x4c80a0, 0x4bd250, 0x4c81b0, 0x4c80b0, 0x4c8160]),
                  words(0x50b090, [0x0, 0xbfe00000]),
                  words(0x50b098, [0x0, 0x0]),
                  words(0x50b0a0, [0x0, 0xc0000000]),
                  words(0x50e008, [0xd2f1a9fc, 0x3f50624d]),
                  words(0x513e10, [0xffc00000, 0xc1dfffff]),
                  words(0x513e18, [0xff800000, 0x41dfffff]),
                  words(0x513e40, [0x18]),
                  words(0x513e48, [0xd2f1a9fc, 0x3f50624d]),
                  words(0x513e50, [0x0, 0xbfe00000]),
                  words(0x50e0c0, [0x42480000]),
                  words(0x50fab0, [0x42480000]),
                  words(0x510020, [0xffffffff]),
                  words(0x52e1c8, [0x52e1b8]),
                  words(0x546d5c, [0x711100]),
                  words(0x546cdc, [0x711104]),
                  words(0x5469e8, [0x711108]),
                  words(0x546cd4, [0x71110c]),
                  words(0x537e88, [scene.player.sceneSnapshot().token]),
                  storage(0x537210, 4) != nil,
                  (0..<4).allSatisfy({ storage(0x534938 + UInt32($0 * 4), 4) != nil }),
                  storage(0x544b14, 60) != nil, storage(0x53c9ac, 8) != nil,
                  words(0x533470, [32]), storage(0x544b98, 388) != nil,
                  words(0x513980 + 0x20, [0x4cddc0]), words(0x5139c8 + 0x20, [0x4cde10]),
                  storage(0x534eac, 4) != nil, storage(0x532c0c, 4) != nil,
                  storage(0x532c10, 4) != nil,
                  storage(0x544b68, 4) != nil else { return false }
            for (address, name) in Self.names {
                let bytes = Array(name.utf8) + [0]
                guard let p = storage(address, UInt32(bytes.count)) else { return false }
                p.update(from: bytes, count: bytes.count)
            }
            // Materialize the existing registry's storage, never a manufactured
            // state/function table. Copy back synchronous mutable lookup fields.
            guard storage(registry.context.pointee.heapBase, registry.context.pointee.heapCapacity) != nil else { return false }
            for (token, count) in tables { guard storage(token, UInt32(count * 4)) != nil else { return false } }
            // Scene-owned physical dictionaries; the audio registry may be
            // empty, in which case its real lookup returns zero.
            guard let world = scene.heap.lookup(scene.sceneIdentity, words: 15) else { return false }
            for index in [4, 10] { if world[index] == 0 { world[index] = scene.heap.allocate(bytes: 0x14) } }
            for index in [4, 5, 10, 11] { guard world[index] != 0, storage(world[index], 0x14) != nil else { return false } }
            guard scene.entry(named: "LogicHit") != 0, scene.entry(named: "LogicAttack") != 0,
                  try scene.objectResources?.images(name: "LEVEL_TOWNGUARD1") != nil else { return false }
            for name in Self.names.values where name.hasPrefix("LEVEL_TOWNGUARD1_") || name == "GAME_NULL" {
                _ = try scene.objectResources?.sequence(name: name)
            }
            for name in Self.names.values where name.hasPrefix("GAME_") || name.hasPrefix("LEVEL_TOWNGUARD_") || name == "LEVEL_DEATHTILE" {
                _ = scene.player.audio?.resolve(name: name)
            }
            return synchronizeRegistry(toHeap: true)
        } catch { print("TownGuard1 setup", error); return false }
    }
    private func synchronizeRegistry(toHeap: Bool) -> Bool {
        guard let scene = connections.scene, let registry = scene.stateRegistry,
              projection.allSatisfy({ connections.host.heap.containingAllocationIdentity(at: $0.0, count: $0.1) === $0.2 }),
              scene.synchronizeObjectDestructionGlobals(toHeap: toHeap) else { return false }
        guard let errors = connections.host.heap.lookupBytes(0x544b14, count: 60) else { return false }
        withUnsafeMutableBytes(of: &registry.registry.pointee.errorGlobals) { raw in
            let data = raw.bindMemory(to: UInt8.self)
            if toHeap { errors.update(from: data.baseAddress!, count: 60) }
            else { data.baseAddress!.update(from: errors, count: 60) }
        }
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
            guard found else { print("TownGuard1 registry absent", String(token, radix: 16)); return false }
        }
        let context = registry.context.pointee
        guard let p = connections.host.heap.lookupBytes(context.heapBase, count: context.heapCapacity), let arena = context.heap else { return false }
        if toHeap { p.update(from: arena, count: Int(context.heapUsed)) }
        else { arena.update(from: p, count: Int(context.heapUsed)) }
        return true
    }
    override func attach(_ object: ClawInteractionActor, callback: UInt32) -> Bool {
        let heap = connections.host.heap
        guard callback == 0x496050, owners[object.token] == nil, object.primary.4 == callback,
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
              heap.lookup(owner.state + 0x10, words: 1)?[0] == 0x496050 else { return false }
        return owner.helper == 0 || (heap.lookup(owner.state + 0x18, words: 1)?[0] == owner.helper && memory?.ownsObjectAllocation(owner.helper, count: 0x498) == true)
    }
    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x496050, active == nil, valid(actor), let memory, let scene = connections.scene,
              synchronizeRegistry(toHeap: true) else { connections.reject(actor); return }
        scene.heap.lookup(0x537210, words: 1)![0] = scene.gameTime
        active = actor; defer { active = nil }
        connections.record("ClawNativeTownGuard1"); connections.record("0x496050")
        var call = ClawCall(); call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        let result = connections.host.withObjectAllocation(provider: memory) { connections.host.invoke(call) }
        if result?.completed == true, let state = owners[actor]?.state {
            let helper = scene.heap.lookup(state + 0x18, words: 1)![0]
            guard memory.ownsObjectAllocation(helper, count: 0x498) else { connections.reject(helper); return }
            owners[actor]!.helper = helper
            connections.record("ClawNativeMfcMemory")
            if !synchronizeRegistry(toHeap: false) || !valid(actor) { connections.reject(actor) }
        }
    }
    // Retire while actor and primary logic still have their pinned identities.
    @discardableResult func retire(_ actor: UInt32) -> Bool {
        guard active == nil, valid(actor), let memory, owners[actor]?.helper != 0 else {
            connections.reject(actor); return false
        }
        // Teardown enters from the scene rather than the callback bridge.
        // Keep the same reviewed reserve for nested canonical member calls.
        let host = connections.host, previousReserve = connections.host.stacklessCallerReserve
        host.stacklessCallerReserve = Self.stacklessCallerReserve
        defer { host.stacklessCallerReserve = previousReserve }
        guard host.retireTownGuard1(actor: actor, provider: memory) else { return false }
        owners[actor]!.helper = 0
        connections.record("ClawNativeTownGuard1.retire.0x496840")
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
        if call.function == 0x4f6286 {
            guard call.argumentCount == 2, let output = connections.host.bytes(call.arguments.1, count: 4),
                  let name = Self.names[call.arguments.0],
                  let world = heap.lookup(scene.sceneIdentity, words: 15) else { return nil }
            let token: UInt32
            do {
                if call.receiver == world[5] + 16, ["LogicHit", "LogicAttack"].contains(name) {
                    token = scene.entry(named: name)
                } else if call.receiver == world[4] + 16, name == "LEVEL_TOWNGUARD1" {
                    token = try scene.objectResources?.images(name: name)?.token ?? 0
                } else if call.receiver == world[11] + 16, name.hasPrefix("LEVEL_TOWNGUARD1_") || name == "GAME_NULL" {
                    token = try scene.objectResources?.sequence(name: name)?.token ?? 0
                } else if call.receiver == world[10] + 16,
                          name.hasPrefix("GAME_") || name.hasPrefix("LEVEL_TOWNGUARD_") || name == "LEVEL_DEATHTILE" {
                    token = scene.player.audio?.resolve(name: name)?.resourceToken ?? 0
                } else { return nil }
            } catch { return nil }
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
        var copied = call
        let args = withUnsafeBytes(of: &copied.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(call.argumentCount))) }
        switch call.function {
        case 0x4a3050:
            guard args.isEmpty, call.receiver == 0 else { return nil }
            connections.record("ClawNativeRandom.0x4a3050"); return scene.nextRandom()
        case 0x711100, 0x711104, 0x546d5c, 0x546cdc:
            let setting = call.function == 0x711100 || call.function == 0x546d5c
            guard args.count == (setting ? 5 : 1), let out = connections.host.bytes(args[0], count: 16) else { return nil }
            for i in 0..<4 {
                var value = (setting ? args[i + 1] : 0).littleEndian
                withUnsafeBytes(of: &value) { out.advanced(by: i * 4).update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 4) }
            }
            return 1
        case 0x711108:
            guard args.count == 1, let out = connections.host.bytes(args[0], count: 4) else { return nil }
            return out.withMemoryRebound(to: UInt32.self, capacity: 1) { $0.pointee &-= 1; return $0.pointee }
        case 0x71110c:
            guard args.count == 3, let rect = connections.host.bytes(args[0], count: 16) else { return nil }
            let v = (0..<4).map { UnsafeRawPointer(rect.advanced(by: $0 * 4)).loadUnaligned(as: Int32.self) }
            let x = Int32(bitPattern: args[1]), y = Int32(bitPattern: args[2])
            return v[0] <= x && x < v[2] && v[1] <= y && y < v[3] ? 1 : 0
        case 0x4a5290:
            guard args.count == 3, args[2] <= 0x400000,
                  let source = connections.host.bytes(args[1], count: args[2]),
                  let target = connections.host.bytes(args[0], count: args[2]) else { return nil }
            let bytes = Array(UnsafeBufferPointer(start: source, count: Int(args[2])))
            target.update(from: bytes, count: bytes.count); return args[0]
        case 0x4b0d60, 0x4b0d30:
            guard args.count == 1, args[0] <= 255 else { return nil }
            return call.function == 0x4b0d60 ? ((args[0] == 32 || (9...13).contains(args[0])) ? 8 : 0) : ((48...57).contains(args[0]) ? 4 : 0)
        default: return nil
        }
    }
}
