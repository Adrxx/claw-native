import Foundation

// The callback, constructor, binders and state methods remain canonical owners.
// This adapter transports the scene's physical resources and registry storage.
@objc(ClawNativeRobberThief) final class ClawNativeRobberThief: ClawNativeObjectAdapter {
    private struct Owner {
        let actor: ClawTokenHeap.AllocationIdentity
        let state: UInt32
        let identity: ClawTokenHeap.AllocationIdentity
        var helper: UInt32 = 0
        var retiredHelper: UInt32 = 0
    }
    private var owners: [UInt32: Owner] = [:]
    private(set) var memory: ClawNativeMfcMemory?
    private var active: UInt32?
    private var retiring = false
    private var projection: [(UInt32, UInt32, ClawTokenHeap.AllocationIdentity)] = []
    var tokens: Set<UInt32> { Set(owners.keys) }
    var evidenceSpans: [(UInt32, UInt32)] { projection.map { ($0.0, $0.1) } }
    override class var services: Set<UInt32> { [0x4f6286,0x4f6974,0x4a3050,0x711100,0x711104,0x711108,0x71110c,0x711110,0x546d24,0x546cdc,0x546d5c,0x4a5290,0x4b0d60,0x4b0d30] }
    override class var stacklessCallerReserve: UInt32? { 0x100 }
    private let tables: [(UInt32, Int)] = [(0x537668, 11), (0x537698, 9), (0x537878, 9), (0x537848, 9), (0x53c238, 9)]
    private static let names: [UInt32: String] = [0x522d54: "LogicHit", 0x522d48: "LogicAttack", 0x523148: "LS_IDLE"]

    private func storage(_ token: UInt32, _ count: UInt32) -> UnsafeMutablePointer<UInt8>? {
        let heap = connections.host.heap
        let bytes: UnsafeMutablePointer<UInt8>
        if let existing = heap.lookupBytes(token, count: count) { bytes = existing }
        else {
            guard !heap.overlaps(token, count: (count + 3) & ~3) else { connections.reject(token); return nil }
            bytes = heap.storeBytes(token: token, count: count)
        }
        guard let identity = heap.containingAllocationIdentity(at: token, count: count) else { return nil }
        if !projection.contains(where: { $0.0 == token }) { projection.append((token, count, identity)) }
        return bytes
    }
    private func words(_ token: UInt32, _ values: [UInt32]) -> Bool {
        if let existing = connections.host.heap.lookup(token,words:UInt32(values.count)),
           Array(UnsafeBufferPointer(start:existing,count:values.count)) != values { connections.reject(token); return false }
        guard let p = storage(token, UInt32(values.count * 4)) else { return false }
        values.withUnsafeBytes { p.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: $0.count) }
        return true
    }
    private func setup() -> Bool {
        guard let scene = connections.scene,let registry = scene.stateRegistry else { return false }
        if memory != nil { return true }
        do {
            let imports = Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map { ($0.element,UInt32(0x710000+$0.offset*4)) })
            let owner = try ClawNativeMfcMemory(host:connections.host,sha256:ClawNativeMfcMemory.imageHash,
                importTargets:imports,allocationBase:0x6a000000,sceneObjectAllocations:true)
            guard scene.registerObjectAllocationOwner(owner) else { return false }
            memory = owner
            guard words(0x50f49c,[0x485870,0x44d000,0x485960,0x44d3c0,0x405000,0x44df60,0x4bb030,0x4c96b0,0x44cfd0,0x43dfa0,0x404dd0,0x44d460,0x44d570,0x44d5a0,0x44d700,0x44d730,0x44d760,0x44d9f0,0x485d60,0x43ed70,0x43eee0,0x43ee10,0x43efe0,0x44e0c0,0x43f640,0x43f740,0x43fa10,0x43fcb0,0x43fd60,0x43fe00,0x44dbb0,0x43ffa0,0x404e00,0x44de30,0x44df10,0x4407d0,0x43f500,0x4409d0,0x440b20,0x440c90,0x440410,0x485ec0,0x404e10]),
                  words(0x50f490,[0x41c80000]),words(0x50e0c0,[0x42480000]),
                  words(0x513980+0x20,[0x4cddc0]),words(0x5139c8+0x20,[0x4cde10]),
                  words(0x513740,[0x4f701d,0x4c80c0,0x4c9e30,0x4c96b0,0x4c9e30,0x4c80a0,0x4bd250,0x4c81b0,0x4c80b0,0x4c8160]),
                  words(0x50b090,[0]),words(0x50b094,[0xbfe00000]),words(0x50b098,[0,0]),
                  words(0x50b0a0,[0,0xc0000000]),
                  words(0x513e48,[0xd2f1a9fc,0x3f50624d,0,0xbfe00000]),
                  storage(0x544b68,4) != nil,storage(0x544b14,60) != nil,
                  words(0x533470,[32]),storage(0x544b98,388) != nil,
                  words(0x510020,[.max]),words(0x52e1c8,[0x52e1b8]),
                  storage(0x534938,1)?[0] == 0,storage(0x541334,4) != nil,words(0x50e008,[0xd2f1a9fc,0x3f50624d]),
                  words(0x513e10,[0xffc00000,0xc1dfffff,0xff800000,0x41dfffff]),words(0x513e40,[24]),
                  words(0x546d5c,[0x711100]),words(0x546cdc,[0x711104]),words(0x5469e8,[0x711108]),words(0x546cd4,[0x71110c]),words(0x546d24,[0x711110]),
                  storage(0x537210,4) != nil,storage(0x534eac,4) != nil,storage(0x53c9ac,8) != nil,
                  storage(0x532c0c,4) != nil,storage(0x532c10,4) != nil,
                  words(0x537e88,[0x10002000]) else { return false }
            for (address,name) in Self.names {
                let bytes = Array(name.utf8)+[0];guard let p = storage(address,UInt32(bytes.count)) else { return false }
                p.update(from:bytes,count:bytes.count)
            }
            guard storage(registry.context.pointee.heapBase,registry.context.pointee.heapCapacity) != nil else { return false }
            // The source dispatcher validates the complete ten-word table object,
            // including its trailing native-owned word; registry payloads are nine words.
            for (token,count) in tables {
                let bytes = UInt32(max(count, 10) * 4)
                guard storage(token,bytes) != nil else { return false }
            }
            let parent = scene.heap.lookup(scene.sceneIdentity,words:15)!
            if parent[4] == 0 { parent[4] = scene.heap.allocate(bytes:32) }
            if parent[10] == 0 { parent[10] = scene.player.audio?.managerIdentity ?? scene.heap.allocate(bytes:32) }
            guard storage(parent[5],20) != nil,scene.entry(named:"LogicHit") != 0,scene.entry(named:"LogicAttack") != 0,
                  try scene.objectResources?.images(name:"LEVEL_ROBBERTHIEF") != nil else { return false }
            // Absent optional sequences remain zero so the original chooses
            // GAME_NULL. Nothing substitutes a successful resource lookup.
            for name in Set(clawOriginalResourceNames.values) where name.hasPrefix("LEVEL_ROBBERTHIEF_") || name == "GAME_NULL" {
                _ = try scene.objectResources?.sequence(name:name)
            }
            return synchronizeRegistry(toHeap:true)
        } catch { return false }
    }
    private func synchronizeRegistry(toHeap: Bool) -> Bool {
        guard let scene = connections.scene, let registry = scene.stateRegistry,
              projection.allSatisfy({ connections.host.heap.containingAllocationIdentity(at: $0.0, count: $0.1) === $0.2 }),
              scene.synchronizeObjectDestructionGlobals(toHeap: toHeap) else { return false }
        guard let errors = connections.host.heap.lookupBytes(0x544b14,count:60) else { return false }
        withUnsafeMutableBytes(of: &registry.registry.pointee.errorGlobals) { raw in
            let data = raw.bindMemory(to:UInt8.self)
            if toHeap { errors.update(from:data.baseAddress!,count:60) }
            else { data.baseAddress!.update(from:errors,count:60) }
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
        guard callback == 0x485270, owners[object.token] == nil, object.primary.4 == callback,
              let actor = heap.allocationIdentity(at: object.token, count: 0x1b4),
              let state = heap.allocationIdentity(at: object.actor.27, count: 0x174), setup() else { return false }
        guard let scene = connections.scene else { return false }
        scene.write(object)
        owners[object.token] = Owner(actor: actor, state: object.actor.27, identity: state)
        return true
    }
    private func valid(_ actor: UInt32) -> Bool {
        let heap = connections.host.heap
        guard let owner = owners[actor],let scene = connections.scene,
              heap.lookup(actor + 0xc,words:1)?[0] == scene.sceneIdentity,
              heap.allocationIdentity(at: actor, count: 0x1b4) === owner.actor,
              heap.allocationIdentity(at: owner.state, count: 0x174) === owner.identity,
              heap.lookup(actor + 0x6c, words: 1)?[0] == owner.state,
              heap.lookup(owner.state + 0x10, words: 1)?[0] == 0x485270 else { return false }
        if owner.helper == 0 {
            let stored = heap.lookup(owner.state+0x18,words:1)?[0]
            return stored == 0 || (owner.retiredHelper != 0 && stored == owner.retiredHelper)
        }
        return heap.lookup(owner.state + 0x18,words:1)?[0] == owner.helper &&
            memory?.ownsObjectAllocation(owner.helper,count:0x478) == true &&
            heap.lookup(owner.helper+8,words:1)?[0] == actor &&
            heap.lookup(owner.helper+0xc,words:1)?[0] == actor &&
            heap.lookup(owner.helper+0x10,words:1)?[0] == owner.state
    }
    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x485270, active == nil, !retiring, owners[actor]?.retiredHelper == 0, valid(actor), let memory, let scene = connections.scene,
              synchronizeRegistry(toHeap: true) else { connections.reject(actor); return }
        if let helper = owners[actor]?.helper, helper != 0,
           scene.heap.lookup(helper,words:1)?[0] != 0x50f49c { connections.reject(helper); return }
        active = actor; defer { active = nil }
        connections.host.heap.lookup(0x537210, words: 1)![0] = scene.gameTime
        connections.record("ClawNativeRobberThief"); connections.record("0x485270")
        var call = ClawCall(); call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        var fp = ClawX87State(); fp.size = UInt32(MemoryLayout<ClawX87State>.size); fp.version = 1; fp.control = 0x23f
        var completed = false
        _ = connections.host.withObjectAllocation(provider:memory) {
            if let result = connections.host.withObjectX87Environment(fp,body:{connections.host.invoke(call)}) { callbackCompletion = result.0; completed = result.0.completed }
        }
        guard completed else { if connections.host.fault == nil { connections.reject(actor) }; return }
        if let state = owners[actor]?.state {
            let helper = scene.heap.lookup(state + 0x18, words: 1)![0]
            guard memory.ownsObjectAllocation(helper, count: 0x478) else { connections.reject(helper); return }
            owners[actor]!.helper = helper
            if !synchronizeRegistry(toHeap: false) || !valid(actor) { connections.reject(actor) }
        }
    }

    // Retire while original actor/logic identities and callback are intact.
    func prepareActorDestruction(_ actor: UInt32) -> Bool {
        guard let owner = owners[actor] else { return true }
        guard active == nil,!retiring,valid(actor),let memory else { connections.reject(actor);return false }
        if owner.helper != 0 {
            guard connections.host.heap.lookup(owner.helper,words:1)?[0] == 0x50f49c else { connections.reject(owner.helper);return false }
            retiring = true; defer { retiring = false }
            // Scene teardown enters outside the callback bridge. Retain its
            // reviewed caller reserve for the real nested member destructors.
            let host = connections.host, previousReserve = connections.host.stacklessCallerReserve
            host.stacklessCallerReserve = Self.stacklessCallerReserve
            defer { host.stacklessCallerReserve = previousReserve }
            guard host.retireRobberThief(actor: actor, provider: memory),
                  host.fault == nil,
                  !memory.ownsObjectAllocation(owner.helper, count: 0x478) else {
                connections.reject(owner.helper); return false
            }
            owners[actor]!.retiredHelper = owner.helper
            owners[actor]!.helper = 0
            connections.record("ClawNativeCanonicalHost.0x485870")
        }
        return true
    }
    func prepareLogicDestruction(_ logic: UInt32) -> Bool {
        guard let actor = owners.first(where: { $0.value.state == logic })?.key else { return true }
        return prepareActorDestruction(actor)
    }
    override func remove(_ actor: UInt32) {
        guard owners[actor]?.helper == 0 else { connections.reject(actor);return }
        owners.removeValue(forKey:actor)
    }
    override func service(_ call: ClawCall) -> UInt32? {
        guard let actor = active, valid(actor), let scene = connections.scene,
              call.receiver2 == 0, call.x87ArgumentCount == 0 else { return nil }
        let heap = scene.heap
        if call.function == 0x4f6286 {
            guard call.argumentCount == 2, let output = connections.host.bytes(call.arguments.1, count: 4),
                  let name = Self.names[call.arguments.0] ?? clawOriginalResourceNames[call.arguments.0],
                  let world = heap.lookup(actor + 0xc, words: 1)?[0],world == scene.sceneIdentity,
                  let managers = heap.lookup(world,words:15) else { return nil }
            let token: UInt32
            do {
                if call.receiver == managers[5] + 16,
                   ["LogicHit", "LogicAttack"].contains(name) { token = scene.entry(named: name) }
                else if call.receiver == managers[4] + 16,
                        name == "LEVEL_ROBBERTHIEF" { token = try scene.objectResources?.images(name: name)?.token ?? 0 }
                else if call.receiver == managers[11] + 16 {
                    token = try scene.objectResources?.sequence(name: name)?.token ?? 0
                } else if call.receiver == managers[10] + 16 {
                    token = scene.player.audio?.resolve(name:name)?.resourceToken ?? 0
                } else { return nil }
            } catch { return nil }
            connections.record("ClawActorResources.0x4f6286")
            withUnsafeBytes(of: token.littleEndian) { output.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 4) }
            return token == 0 ? 0:1
        }
        if call.function == 0x4f6974 {
            guard call.argumentCount == 1, call.arguments.0 == 0,
                  let table = heap.lookup(0x537698, words: 9), table[3] >= table[2], call.receiver >= table[4],
                  UInt64(call.receiver) < UInt64(table[4]) + UInt64(table[3] - table[2] + 1) * 4,
                  (call.receiver - table[4]) % 4 == 0,
                  let pointer = heap.lookup(call.receiver, words: 1)?[0], pointer >= 12,
                  let header = heap.lookup(pointer - 12, words: 3), Int32(bitPattern: header[0]) <= 1,
                  header[1] <= header[2], heap.lookupBytes(pointer, count: header[1] + 1) != nil else { return nil }
            connections.record("ClawNativeStateRegistry.0x4f6974"); return pointer
        }
        let host = connections.host
        switch call.function {
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
        case 0x711110,0x546d24:
            guard call.receiver == 0,call.argumentCount == 3,let p = host.bytes(call.arguments.0,count:16) else { return nil }
            var r = (0..<4).map { UnsafeRawPointer(p.advanced(by:$0*4)).loadUnaligned(as:Int32.self) }
            let dx = Int32(bitPattern:call.arguments.1),dy = Int32(bitPattern:call.arguments.2)
            r[0] &-= dx;r[1] &-= dy;r[2] &+= dx;r[3] &+= dy
            r.withUnsafeBytes { p.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:16) };return 1
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
