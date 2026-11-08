import Foundation

// Scene attachment owns the source actor; canonical game code owns staging,
// contact binding, player reset, speech queuing and health-meter construction.
@objc(ClawNativeBossStager) class ClawNativeBossStager: ClawNativeObjectAdapter {
    private struct Owner {
        let actor: ClawTokenHeap.AllocationIdentity
        let state: UInt32
        let identity: ClawTokenHeap.AllocationIdentity
    }
    private var owners: [UInt32: Owner] = [:]
    private var children: [UInt32: Owner] = [:]
    private var active: UInt32?
    private(set) var memory: ClawNativeMfcMemory?
    // Optional synchronous observer/decorator; the real scene audio owner is
    // still required to validate the shared heap and own every sound pool.
    var audioProvider: ClawNativeCanonicalHost.ObjectAudioProvider?
    private(set) var resourceBindings: [[String: UInt32]] = []
    private var pins: [(UInt32, UInt32, ClawTokenHeap.AllocationIdentity)] = []
    private var musicRegistry: (UInt32, ClawTokenHeap.AllocationIdentity)?
    private let musicEntries: [String: UInt32] = [:] // Explicit no-controller profile.
    var tokens: Set<UInt32> { Set(owners.keys) }
    var childTokens: Set<UInt32> { Set(children.keys) }
    var evidenceSpans: [(UInt32, UInt32)] { pins.map { ($0.0, $0.1) } }
    override class var stacklessCallerReserve: UInt32? { 0x100 }
    override class var services: Set<UInt32> { [0x4f6286, 0x4f51c5, 0x4f572a, 0x546d5c, 0x711100] }
    static let names: [UInt32: String] = [0x522290: "BossStagerAttack", 0x522280: "BossHealthMeter",
        0x52c66c: "LEVEL_BOSSNAME", 0x52c660: "GAME_SDPT1", 0x52c62c: "GAME_SDPT2",
        0x52c61c: "LEVEL_DEFEAT", 0x52c64c: "LEVEL_STAGING_CLAW", 0x52c638: "LEVEL_STAGING_ENEMY",
        0x52c8c8: "GAME_BOSSBAR", 0x529fbc: "BOSS", 0x5246d0: "CLAW_STAND"]
    private func storage(_ token: UInt32, _ count: UInt32) -> UnsafeMutablePointer<UInt8>? {
        let heap = connections.host.heap
        let result: UnsafeMutablePointer<UInt8>
        if let p = heap.lookupBytes(token, count: count) { result = p }
        else {
            guard !heap.overlaps(token, count: (count + 3) & ~3) else { return nil }
            result = heap.storeBytes(token: token, count: count)
        }
        guard let identity = heap.containingAllocationIdentity(at: token, count: count) else { return nil }
        if !pins.contains(where: { $0.0 == token }) { pins.append((token, count, identity)) }
        return result
    }
    private func put(_ token: UInt32, _ value: UInt32) -> Bool {
        guard let p = storage(token, 4) else { return false }
        p.withMemoryRebound(to: UInt32.self, capacity: 1) { $0.pointee = value }; return true
    }
    private func setup() -> Bool {
        if memory != nil { return true }
        guard let scene = connections.scene else { return false }
        do {
            let imports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map { ($0.element, UInt32(0x710000 + $0.offset * 4)) })
            let owner = try ClawNativeMfcMemory(host: connections.host, sha256: ClawNativeMfcMemory.imageHash,
                importTargets: imports, allocationBase: 0x67d00000, sceneObjectAllocations: true)
            guard scene.registerObjectAllocationOwner(owner) else { return false }
            memory = owner
            for (address, name) in Self.names {
                let bytes = Array(name.utf8) + [0]
                guard let p = storage(address, UInt32(bytes.count)) else { return false }
                p.update(from: bytes, count: bytes.count)
            }
            for (address, count): (UInt32, UInt32) in [(0x5371fc,4), (0x537e88,4), (0x537204,4),
                (0x5349dc,4), (0x53c9c0,4), (0x53c9a0,4), (0x53c9a4,4), (0x53c9a8,4), (0x53c9ac,4), (0x53c9b0,4), (0x53c9f8,4), (0x52be14,8),
                (0x532c0c,4), (0x532c10,4), (0x52c6f0,8), (0x534e60,24)] {
                guard storage(address,count) != nil else { return false }
            }
            guard storage(0x50f898,8) != nil,
                  scene.heap.lookup(0x50f898,words:2)?[0] == 0,
                  scene.heap.lookup(0x50f898,words:2)?[1] == 0x3ff80000,
                  put(0x546d5c,0x711100), put(0x510020,UInt32.max) else { return false }
            let parent = scene.heap.lookup(scene.sceneIdentity,words:15)!
            if parent[4] == 0 { parent[4] = scene.heap.allocate(bytes:32) }
            guard storage(scene.sceneIdentity,60) != nil, storage(scene.ownerIdentity,0x778) != nil,
                  storage(parent[5],20) != nil, scene.entry(named:"BossStagerAttack") != 0,
                  scene.entry(named:"BossHealthMeter") != 0 else { return false }
            return true
        } catch { return false }
    }
    // Publish existing native owners. Do not clear the live boss or staging state.
    func synchronize() -> Bool {
        guard let scene = connections.scene, let camera = scene.camera,
              let manager = scene.heap.lookup(scene.ownerIdentity+4,words:1)?[0],
              let app = scene.heap.lookup(manager,words:77), let speech = scene.speech else { return false }
        guard put(0x5371fc,manager), put(0x537e88,0x10002000), put(0x537204,camera.inputToken),
              put(0x532c0c,scene.player.audio?.routing.managerAvailable ?? 0),
              put(0x532c10,scene.player.audio?.routing.masterVolume ?? 0),
              put(0x53c9a0,speech.globals.pointee.clawBusy), put(0x53c9a4,speech.globals.pointee.clawActorToken),
              put(0x53c9a8,speech.globals.pointee.enemyBusy), put(0x53c9ac,speech.globals.pointee.enemyActorToken),
              put(0x53c9b0,speech.globals.pointee.speakerToken),
              let hud = scene.hud, put(0x53c9f8,hud.timerRemaining) else { return false }
        // The scene constructor supplies the real single-player interface.
        guard let table = scene.heap.lookup(scene.ownerIdentity,words:1)?[0],
              table == 0x50c264, storage(table,0x64) != nil,
              scene.heap.lookup(table+0x60,words:1)?[0] == 0x46cab0,
              app[0x2c/4] == scene.ownerIdentity, app[0x30/4] == scene.sceneIdentity else { return false }
        guard app[0x14/4] == 0 else { return false }
        if musicRegistry == nil {
            guard app[0x50/4] == 0 else { return false }
            let token = scene.heap.allocate(bytes:44)
            guard token != 0, let identity = scene.heap.allocationIdentity(at:token,count:44) else { return false }
            app[0x50/4] = token; musicRegistry = (token,identity)
            // With no MIDI driver no XMI resource has been loaded. The empty
            // physical map still goes through MusicRuntime's real lookup.
            scene.heap.lookup(token,words:11)![8] = 100
        }
        guard let (registry,identity) = musicRegistry, app[0x50/4] == registry,
              scene.heap.allocationIdentity(at:registry,count:44) === identity else { return false }
        return true
    }
    private func valid(_ actor: UInt32, child: Bool = false) -> Bool {
        let heap = connections.host.heap
        guard let owner = child ? children[actor] : owners[actor],
              heap.allocationIdentity(at:actor,count:0x1b4) === owner.actor,
              heap.allocationIdentity(at:owner.state,count:0x174) === owner.identity,
              heap.lookup(actor+0x6c,words:1)?[0] == owner.state,
              heap.lookup(actor+0x0c,words:1)?[0] == connections.scene?.sceneIdentity,
              heap.lookup(owner.state+0x10,words:1)?[0] == (child ? 0x491fa0 : 0x48ded0) else { return false }
        return pins.allSatisfy { heap.containingAllocationIdentity(at:$0.0,count:$0.1) === $0.2 }
    }
    override func attach(_ object: ClawInteractionActor, callback: UInt32) -> Bool {
        let heap = connections.host.heap
        guard callback == 0x48ded0, object.primary.4 == callback, owners[object.token] == nil,
              let actor = heap.allocationIdentity(at:object.token,count:0x1b4),
              let state = heap.allocationIdentity(at:object.actor.27,count:0x174), setup() else { return false }
        connections.scene?.write(object)
        owners[object.token] = Owner(actor:actor,state:object.actor.27,identity:state)
        return true
    }
    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x48ded0 else { connections.reject(function); return }
        _ = invoke(function,actor:actor)
    }
    @discardableResult func invoke(_ function: UInt32, actor: UInt32) -> UInt32? {
        let child = function == 0x491fa0
        guard [UInt32(0x48ded0),0x48e430,0x491fa0].contains(function), active == nil,
              valid(actor,child:child), let memory, synchronize() else { connections.reject(actor); return nil }
        active = actor
        // Secondary contact and meter callbacks are scene-owned, rather than
        // root elections. Lend only this adapter's declared physical services
        // for their synchronous canonical invocation.
        let previousDependency = connections.host.dependency
        let secondary = connections.active == nil
        if secondary {
            connections.host.dependency = { [weak self] host, call in
                guard let self, host === self.connections.host,
                      type(of:self).services.contains(call.function) else { return nil }
                return self.service(call)
            }
        }
        defer { if secondary { connections.host.dependency = previousDependency } }
        let reserve = connections.host.stacklessCallerReserve
        connections.host.stacklessCallerReserve = Self.stacklessCallerReserve
        defer { active = nil; connections.host.stacklessCallerReserve = reserve }
        connections.record("ClawNativeBossStager"); connections.record(String(format:"0x%x",function))
        var call = ClawCall(); call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        callbackCompletion = connections.host.withObjectAllocation(provider:memory,audio:audioProvider ?? connections.scene?.player.audio) { connections.host.invoke(call) }
        if callbackCompletion?.completed == true, let scene = connections.scene, let g = scene.speech?.globals {
            g.pointee.clawBusy = scene.heap.lookup(0x53c9a0,words:1)![0]
            g.pointee.clawActorToken = scene.heap.lookup(0x53c9a4,words:1)![0]
            g.pointee.enemyBusy = scene.heap.lookup(0x53c9a8,words:1)![0]
            g.pointee.enemyActorToken = scene.heap.lookup(0x53c9ac,words:1)![0]
            g.pointee.speakerToken = scene.heap.lookup(0x53c9b0,words:1)![0]
            scene.hud?.timerRemaining = scene.heap.lookup(0x53c9f8,words:1)![0]
            _ = scene.importPlayerFromHeap()
        }
        if !valid(actor,child:child) { connections.reject(actor) }
        return callbackCompletion?.eax
    }
    override func remove(_ actor: UInt32) { owners.removeValue(forKey:actor); children.removeValue(forKey:actor) }
    override func service(_ call: ClawCall) -> UInt32? {
        guard let actor = active, valid(actor,child:children[actor] != nil),
              let scene = connections.scene, call.receiver2 == 0, call.x87ArgumentCount == 0 else { return nil }
        let heap = scene.heap
        if call.function == 0x4f6286 {
            guard call.argumentCount == 2, let name = Self.names[call.arguments.0],
                  let out = connections.host.bytes(call.arguments.1,count:4) else { return nil }
            let parent = heap.lookup(scene.sceneIdentity,words:15)!, token: UInt32
            do {
                if call.receiver == parent[4]+16, ["LEVEL_BOSSNAME","GAME_BOSSBAR"].contains(name) {
                    token = try scene.objectResources?.images(name:name)?.token ?? 0
                } else if call.receiver == parent[5]+16, ["BossStagerAttack","BossHealthMeter"].contains(name) {
                    token = scene.entry(named:name)
                } else if call.receiver == parent[10]+16, name.hasPrefix("GAME_") || name.hasPrefix("LEVEL_") {
                    token = scene.player.audio?.resolve(name:name)?.resourceToken ?? 0
                } else if call.receiver == parent[11]+16, name == "CLAW_STAND" {
                    token = scene.resolveResource(dictionary:call.receiver,name:call.arguments.0)
                } else if let (registry,identity) = musicRegistry, call.receiver == registry,
                          heap.allocationIdentity(at:registry,count:44) === identity, name == "BOSS" {
                    token = musicEntries[name] ?? 0
                } else { return nil }
            } catch { return nil }
            withUnsafeBytes(of:token.littleEndian) { out.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:4) }
            if connections.recordsTrace { resourceBindings.append(["receiver":call.receiver,"name":call.arguments.0,"token":token]) }
            connections.record("ClawNativeScene.resource.0x4f6286"); return token == 0 ? 0 : 1
        }
        if call.function == 0x4f51c5 || call.function == 0x4f572a {
            let before = call.function == 0x4f572a
            guard call.receiver == scene.containerToken+16, call.argumentCount == (before ? 2:1),let memory else { return nil }
            let actor = before ? call.arguments.1 : call.arguments.0
            guard memory.ownsObjectAllocation(actor,count:0x1b4), let state = heap.lookup(actor+0x6c,words:1)?[0],
                  memory.ownsObjectAllocation(state,count:0x174), heap.lookup(state+0x10,words:1)?[0] == 0x491fa0,
                  heap.lookup(actor+0x68,words:1)?[0] == 0,
                  let ai = heap.allocationIdentity(at:actor,count:0x1b4),let si = heap.allocationIdentity(at:state,count:0x174) else { return nil }
            var fault: UInt32 = 0
            claw_scene_actor_insert(scene.containerToken,actor,scene.actorHost,&fault)
            guard fault == 0,let node = heap.lookup(actor+0x68,words:1)?[0],heap.lookup(node,words:1)?[0] == (before ? call.arguments.0:0) else { return nil }
            children[actor] = Owner(actor:ai,state:state,identity:si)
            connections.record("ClawNativeScene.list"); return node
        }
        if call.function == 0x546d5c || call.function == 0x711100 {
            guard call.argumentCount == 5,let out = connections.host.bytes(call.arguments.0,count:16) else { return nil }
            let values = [call.arguments.1,call.arguments.2,call.arguments.3,call.arguments.4].map(\.littleEndian)
            values.withUnsafeBytes { out.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:16) }
            connections.record("SetRect"); return 1
        }
        return nil
    }
}
