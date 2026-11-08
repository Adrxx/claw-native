import Foundation

// The callback, constructor, binders and state methods remain canonical owners.
// This adapter transports the scene's physical resources and registry storage.
@objc(ClawNativeOmar) final class ClawNativeOmar: ClawNativeObjectAdapter {
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
    override class var services: Set<UInt32> { [0x4f572a,0x4f51c5,0x4a3810,0x4f6286,0x4f6974,0x4a3050,0x711100,0x711104,0x711108,0x71110c,0x711114,0x546cdc,0x546d5c,0x4a5290,0x4b0d60,0x4b0d30] }
    override class var stacklessCallerReserve: UInt32? { 0x100 }
    private let tables: [(UInt32, Int)] = [(0x537668, 11), (0x537698, 9), (0x537bd0, 10)]
    private static let names: [UInt32: String] = [0x5266ec: "GAME_SPLASH", 0x524870: "GAME_HIT1", 0x524864: "GAME_HIT2", 0x524858: "GAME_HIT3", 0x52484c: "GAME_HIT4", 0x5266dc: "GAME_PURELEASE1", 0x5246f8: "LEVEL_DEATHTILE", 0x527d50: "GAME_SOLHITL2", 0x527d40: "GAME_SOLHITHI", 0x527d34: "GAME_LELAND", 0x524098: "GAME_AMULETRISE", 0x522594: "GlitterBaby", 0x522c40: "OmarShield", 0x522d48: "LogicAttack", 0x522d54: "LogicHit", 0x523148: "LS_IDLE", 0x523268: "LS_STARTUP", 0x5234b4: "GAME_NULL", 0x5234ec: "LS_HOME", 0x52417c: "GAME_CYCLE50", 0x52433c: "LEVEL_OMARPROJECTILE", 0x5298cc: "LEVEL_OMAR_00520004", 0x5298e0: "LEVEL_OMAR_SKYTHUNDER", 0x5298f8: "LEVEL_OMAR_ENERGYLOOP", 0x529910: "LEVEL_OMAR_THENFALL", 0x529924: "LEVEL_OMAR_ENERGYBALL", 0x52993c: "LEVEL_OMAR_00520010", 0x529950: "LEVEL_OMAR_00520008", 0x529964: "LEVEL_OMAR_00520015", 0x529978: "LEVEL_OMAR_00520014", 0x52998c: "LEVEL_OMAR_BLOCK", 0x5299a0: "LEVEL_OMAR_STRIKE1", 0x5299b4: "LEVEL_OMAR_KILLFALL3", 0x5299cc: "LEVEL_OMAR_KILLFALL", 0x5299e0: "LEVEL_OMAR_IDLE", 0x5299f0: "LEVEL_OMAR_HITLOW", 0x529a04: "LEVEL_OMAR_HITHIGH", 0x529a18: "LEVEL_OMAR", 0x529a8c: "LEVEL_FIRESHIELD", 0x529aa0: "LEVEL_ICESHIELD"]

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
                importTargets:imports,allocationBase:0x67000000,sceneObjectAllocations:true)
            guard scene.registerObjectAllocationOwner(owner) else { return false }
            memory = owner
            guard words(0x50eafc,[0x463a30,0x464010,0x463b40,0x4640b0,0x40e1b0,0x44df60,0x4bb030,0x4c96b0,0x40e5b0,0x463fd0,0x4c9e30,0x4642b0,0x4a07e0,0x464360,0x4646e0,0x4b7aa0,0x44d760,0x4648e0,0x4646f0]),
                  words(0x50ebb4,[0x484d90,0x4c9e30,0x4651a0,0x4041b0,0x4c96b0,0x465550,0x4bb030,0x4c96b0,0x4c96b0]),
                  words(0x50eab8,[0x4d12d84a,0x400921fb,0x42480000,0x0,0x16c16c17,0x3f76c16c,0x0,0xc0540000,0xd2f1a9fc,0x3f50624d]),
                  words(0x50e0c0,[0x42480000,0x0]),words(0x513980+0x20,[0x4cddc0]),words(0x5139c8+0x20,[0x4cde10]),
                  words(0x513740,[0x4f701d,0x4c80c0,0x4c9e30,0x4c96b0,0x4c9e30,0x4c80a0,0x4bd250,0x4c81b0,0x4c80b0,0x4c8160]),
                  words(0x50b090,[0]),words(0x50b094,[0xbfe00000]),words(0x50b098,[0,0]),
                  words(0x50b0a0,[0,0xc0000000]),
                  words(0x513e48,[0xd2f1a9fc,0x3f50624d,0,0xbfe00000]),
                  storage(0x544b68,4) != nil,storage(0x544b14,60) != nil,
                  words(0x533470,[32]),storage(0x544b98,388) != nil,
                  words(0x510020,[.max]),words(0x52e1c8,[0x52e1b8]),
                  storage(0x534938,1)?[0] == 0,words(0x50e008,[0xd2f1a9fc,0x3f50624d]),
                  words(0x513e10,[0xffc00000,0xc1dfffff,0xff800000,0x41dfffff]),words(0x513e40,[24]),
                  scene.heap.lookupBytes(0x5262b0,count:12) != nil,
                  storage(0x541334,4) != nil,storage(0x53c9ac,8) != nil,
                  words(0x546d5c,[0x711100]),words(0x546cdc,[0x711104]),words(0x5469e8,[0x711108]),words(0x546cd4,[0x71110c]),words(0x546d24,[0x711114]),
                  storage(0x5349dc,4) != nil,storage(0x53c19c,4) != nil,storage(0x537210,4) != nil,storage(0x534eac,4) != nil,
                  storage(0x532c0c,4) != nil,storage(0x532c10,4) != nil,
                  words(0x537e88,[0x10002000]) else { return false }
            for (address,name) in Self.names {
                let bytes = Array(name.utf8)+[0];guard let p = storage(address,UInt32(bytes.count)) else { return false }
                p.update(from:bytes,count:bytes.count)
            }
            guard storage(registry.context.pointee.heapBase,registry.context.pointee.heapCapacity) != nil else { return false }
            for (token,count) in tables { guard storage(token,UInt32(count*4)) != nil else { return false } }
            let parent = scene.heap.lookup(scene.sceneIdentity,words:15)!
            if parent[4] == 0 { parent[4] = scene.heap.allocate(bytes:32) }
            if parent[10] == 0 { parent[10] = scene.player.audio?.managerIdentity ?? scene.heap.allocate(bytes:32) }
            guard storage(parent[5],20) != nil,scene.entry(named:"OmarShield") != 0,scene.entry(named:"LogicHit") != 0,scene.entry(named:"LogicAttack") != 0,
                  try scene.objectResources?.images(name:"LEVEL_OMAR") != nil,
                  try scene.objectResources?.images(name:"LEVEL_FIRESHIELD") != nil,
                  try scene.objectResources?.images(name:"LEVEL_ICESHIELD") != nil else { return false }
            // Absent optional sequences remain zero so the original chooses
            // GAME_NULL. Nothing substitutes a successful resource lookup.
            for name in Set(Self.names.values).union(clawOriginalResourceNames.values) where name.hasPrefix("LEVEL_OMAR") || ["LEVEL_FIRESHIELD", "LEVEL_ICESHIELD", "GAME_NULL"].contains(name) {
                _ = try scene.objectResources?.sequence(name:name)
            }
            return synchronizeRegistry(toHeap:true)
        } catch { return false }
    }
    private func synchronizeRegistry(toHeap: Bool) -> Bool {
        guard let registry = connections.scene?.stateRegistry,
              projection.allSatisfy({ connections.host.heap.containingAllocationIdentity(at: $0.0, count: $0.1) === $0.2 }) else { return false }
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
        guard callback == 0x4633a0, owners[object.token] == nil, object.primary.4 == callback,
              let actor = heap.allocationIdentity(at: object.token, count: 0x1b4),
              let state = heap.allocationIdentity(at: object.actor.27, count: 0x174), setup() else { return false }
        connections.scene!.write(object)
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
              heap.lookup(owner.state + 0x10, words: 1)?[0] == 0x4633a0 else { return false }
        return owner.helper == 0 || (heap.lookup(owner.state + 0x18, words: 1)?[0] == owner.helper && memory?.ownsObjectAllocation(owner.helper, count: 0xd48) == true)
    }
    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x4633a0, active == nil, valid(actor), let memory, let scene = connections.scene,
              synchronizeRegistry(toHeap: true) else { connections.reject(actor); return }
        active = actor; defer { active = nil }
        connections.host.heap.lookup(0x537210, words: 1)![0] = scene.gameTime
        connections.record("ClawNativeOmar"); connections.record("0x4633a0")
        // The canonical 48cf50 body shares the scene's actual holder globals.
        let destruction = scene.objectDestructionGlobals
        scene.heap.lookup(0x53c9ac,words:2)![0] = destruction.holderActorToken
        scene.heap.lookup(0x53c9ac,words:2)![1] = destruction.heldActorToken
        var call = ClawCall(); call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        var fp = ClawX87State(); fp.size = UInt32(MemoryLayout<ClawX87State>.size); fp.version = 1; fp.control = 0x23f
        var completed = false
        _ = connections.host.withObjectAllocation(provider:memory) {
            if let result = connections.host.withObjectX87Environment(fp,body:{connections.host.invoke(call)}) { completed = result.0.completed }
        }
        if completed {
            var destruction = scene.objectDestructionGlobals
            destruction.holderActorToken = scene.heap.lookup(0x53c9ac,words:2)![0]
            destruction.heldActorToken = scene.heap.lookup(0x53c9ac,words:2)![1]
            scene.objectDestructionGlobals = destruction
        }
        if completed, let state = owners[actor]?.state {
            let helper = scene.heap.lookup(state + 0x18, words: 1)![0]
            guard memory.ownsObjectAllocation(helper, count: 0xd48) else { connections.reject(helper); return }
            owners[actor]!.helper = helper
            if !synchronizeRegistry(toHeap: false) || !valid(actor) { connections.reject(actor) }
        }
    }

    // Retire while original actor/logic identities and callback are intact.
    func prepareActorDestruction(_ actor: UInt32) -> Bool {
        guard let owner = owners[actor] else { return true }
        guard active == nil,valid(actor),let memory else { connections.reject(actor);return false }
        if owner.helper != 0 {
            let reserve = connections.host.stacklessCallerReserve
            connections.host.stacklessCallerReserve = Self.stacklessCallerReserve
            defer { connections.host.stacklessCallerReserve = reserve }
            var fp = ClawX87State();fp.size = UInt32(MemoryLayout<ClawX87State>.size);fp.version = 1;fp.control = 0x23f
            guard connections.host.withObjectX87Environment(fp,body:{ connections.host.retireOmar(actor:actor,provider:memory) })?.0 == true else { return false }
            owners[actor]!.helper = 0
            connections.record("ClawNativeCanonicalHost.0x463a30")
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
        if call.function == 0x4f51c5 || call.function == 0x4f572a {
            let before = call.function == 0x4f572a
            guard call.receiver == scene.containerToken + 0x10,
                  call.argumentCount == (before ? 2:1), let memory else { return nil }
            let child = before ? call.arguments.1:call.arguments.0
            guard memory.ownsObjectAllocation(child, count: 0x1b4),
                  let state = heap.lookup(child + 0x6c, words: 1)?[0],
                  memory.ownsObjectAllocation(state, count: 0x174),
                  heap.lookup(state + 0x10, words: 1)?[0] == 0x464f20,
                  heap.lookup(child + 0x68, words: 1)?[0] == 0 else { return nil }
            // The scene's pooled CList owns nodes and preserves priority order.
            var fault: UInt32 = 0
            claw_scene_actor_insert(scene.containerToken, child, scene.actorHost, &fault)
            guard fault == 0, let node = heap.lookup(child + 0x68, words: 1)?[0],
                  heap.lookup(node, words: 1)?[0] == (before ? call.arguments.0:0) else { return nil }
            connections.record("ClawNativeScene.list")
            return node
        }
        if call.function == 0x4f6286 {
            guard call.argumentCount == 2, let output = connections.host.bytes(call.arguments.1, count: 4),
                  let name = Self.names[call.arguments.0] ?? clawOriginalResourceNames[call.arguments.0],
                  let world = heap.lookup(actor + 0xc, words: 1)?[0],world == scene.sceneIdentity,
                  let managers = heap.lookup(world,words:15) else { return nil }
            let token: UInt32
            do {
                if call.receiver == managers[5] + 16,
                   ["LogicHit", "LogicAttack", "OmarShield"].contains(name) { token = scene.entry(named: name) }
                else if call.receiver == managers[4] + 16,
                        ["LEVEL_OMAR", "LEVEL_FIRESHIELD", "LEVEL_ICESHIELD"].contains(name) { token = try scene.objectResources?.images(name: name)?.token ?? 0 }
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
        case 0x4a3810:
            guard call.receiver == 0,call.argumentCount == 2 else { return nil }
            func string(_ token: UInt32) -> [UInt8]? {
                var result: [UInt8] = []
                for offset: UInt32 in 0..<256 {
                    guard let p = host.bytes(token+offset,count:1) else { return nil }
                    if p[0] == 0 { return result };result.append(p[0])
                }
                return nil
            }
            guard let left = string(call.arguments.0),let right = string(call.arguments.1) else { return nil }
            var i = 0;while i < left.count && i < right.count && left[i] == right[i] { i += 1 }
            return UInt32(bitPattern:Int32(i < left.count ? left[i]:0)-Int32(i < right.count ? right[i]:0))
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
        case 0x711114:
            guard call.receiver == 0,call.argumentCount == 3,let p = host.bytes(call.arguments.0,count:16) else { return nil }
            let dx = call.arguments.1,dy = call.arguments.2
            p.withMemoryRebound(to:UInt32.self,capacity:4) { r in r[0] &-= dx;r[1] &-= dy;r[2] &+= dx;r[3] &+= dy }
            return 1
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
