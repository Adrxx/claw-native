import Foundation

// Canonical BossWarp, animation and actor creation share the scene's physical owners.
@objc(ClawNativeBossWarp) class ClawNativeBossWarp: ClawNativeObjectAdapter {
    private struct Owner {
        let actor: ClawTokenHeap.AllocationIdentity
        let state: UInt32
        let identity: ClawTokenHeap.AllocationIdentity
    }
    private var owners: [UInt32: Owner] = [:]
    private var active: UInt32?
    private var children: [UInt32: Owner] = [:]
    private(set) var memory: ClawNativeMfcMemory?
    var tokens: Set<UInt32> { Set(owners.keys) }
    var calls: [ClawCall] { connections.calls }
    override class var stacklessCallerReserve: UInt32? { 0x40 }
    override class var services: Set<UInt32> { [0x4f6286, 0x4750d0, 0x4f51c5, 0x4f572a, 0x546d5c] }
    private static let names: [UInt32: String] = [0x52293c: "EndOfLevelPowerup",
        0x52a218: "GAME_BOSSWARP", 0x52a198: "GAME_POWERUP", 0x52a204: "GAME_MAGICPOWERUP",
        0x52a1e0: "LEVEL_GEM", 0x52a1cc: "GAME_CHECKEDFLAG", 0x524d1c: "GAME_MAPPIECE"]
    private var pins: [(UInt32, UInt32, ClawTokenHeap.AllocationIdentity)] = []
    var evidenceSpans: [(UInt32, UInt32)] { pins.map { ($0.0, $0.1) } }
    private func storage(_ token: UInt32, _ count: UInt32) -> UnsafeMutablePointer<UInt8>? {
        let heap = connections.host.heap
        let bytes: UnsafeMutablePointer<UInt8>
        if let p = heap.lookupBytes(token, count: count) { bytes = p }
        else {
            guard !heap.overlaps(token, count: (count + 3) & ~3) else { return nil }
            bytes = heap.storeBytes(token: token, count: count)
        }
        guard let identity = heap.containingAllocationIdentity(at: token, count: count) else { return nil }
        if !pins.contains(where: { $0.0 == token }) { pins.append((token, count, identity)) }
        return bytes
    }
    private func setup() -> Bool {
        guard let scene = connections.scene else { return false }
        if memory != nil { return true }
        do {
            let imports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map { ($0.element, UInt32(0x710000 + $0.offset * 4)) })
            let memory = try ClawNativeMfcMemory(host: connections.host, sha256: ClawNativeMfcMemory.imageHash,
                importTargets: imports, allocationBase: 0x69d00000, sceneObjectAllocations: true)
            guard scene.registerObjectAllocationOwner(memory) else { return false }
            self.memory = memory
            for (address, name) in Self.names {
                let bytes = Array(name.utf8) + [0]
                guard let p = storage(address, UInt32(bytes.count)) else { return false }
                p.update(from: bytes, count: bytes.count)
            }
            // The native registry already owns the entry records. Its opaque
            // dictionary receiver also needs a stable span for source pinning.
            guard let registry = scene.heap.lookup(scene.sceneIdentity + 0x14, words: 1)?[0],
                  registry != 0, storage(registry, 0x14) != nil else { return false }
            guard storage(0x5371fc, 4) != nil, storage(0x537ec8, 341 * 4) != nil,
                  storage(0x52a190, 4) != nil, let sentinel = storage(0x510020, 4) else { return false }
            sentinel.withMemoryRebound(to: UInt32.self, capacity: 1) { $0.pointee = .max }
            return true
        } catch { return false }
    }
    // Project existing native owners; no independent loot or application defaults.
    func synchronize() -> Bool {
        guard let scene = connections.scene, let loot = scene.loot,
              let manager = scene.heap.lookup(scene.ownerIdentity + 4, words: 1)?[0] else { return false }
        scene.heap.lookup(0x5371fc, words: 1)![0] = manager
        withUnsafeBytes(of: &loot.globals.pointee.words) { bytes in
            scene.heap.lookupBytes(0x537ec8, count: 341 * 4)!.update(from: bytes.bindMemory(to: UInt8.self).baseAddress!, count: bytes.count)
        }
        scene.heap.lookup(0x52a190, words: 1)![0] = loot.globals.pointee.itemCount
        return true
    }
    override func attach(_ object: ClawInteractionActor, callback: UInt32) -> Bool {
        let heap = connections.host.heap
        guard callback == 0x470870, object.primary.4 == callback, owners[object.token] == nil,
              let actor = heap.allocationIdentity(at: object.token, count: 0x1b4),
              let state = heap.allocationIdentity(at: object.actor.27, count: 0x174), setup() else { return false }
        connections.scene?.write(object)
        owners[object.token] = Owner(actor: actor, state: object.actor.27, identity: state)
        // WWD population precedes loot initialization; the first gameplay call
        // publishes it after all native scene owners have completed startup.
        _ = synchronize()
        return true
    }
    private func valid(_ actor: UInt32) -> Bool {
        let heap = connections.host.heap
        guard let owner = owners[actor], heap.allocationIdentity(at: actor, count: 0x1b4) === owner.actor,
              heap.allocationIdentity(at: owner.state, count: 0x174) === owner.identity,
              heap.lookup(actor + 0x6c, words: 1)?[0] == owner.state,
              heap.lookup(owner.state + 0x10, words: 1)?[0] == 0x470870 else { return false }
        return pins.allSatisfy { heap.containingAllocationIdentity(at: $0.0, count: $0.1) === $0.2 }
    }
    override func callback(_ function: UInt32, actor: UInt32) {
        guard function == 0x470870, active == nil, valid(actor), let memory, synchronize() else { connections.reject(actor); return }
        active = actor; defer { active = nil }
        connections.record("ClawNativeBossWarp"); connections.record("0x470870")
        var call = ClawCall(); call.function = function; call.argumentCount = 1; call.arguments.0 = actor
        callbackCompletion = connections.host.withObjectAllocation(provider: memory) { connections.host.invoke(call) }
        if !valid(actor) { connections.reject(actor) }
    }
    // Named construction initializes this child synchronously. Its later scene
    // ticks retain the same actor/state allocation identities and canonical body.
    func childCallback(_ actor: UInt32) {
        callbackCompletion = nil
        let heap = connections.host.heap
        guard active == nil, let scene = connections.scene, let memory, let child = children[actor],
              memory.ownsObjectAllocation(actor, count: 0x1b4),
              memory.ownsObjectAllocation(child.state, count: 0x174),
              heap.allocationIdentity(at: actor, count: 0x1b4) === child.actor,
              heap.allocationIdentity(at: child.state, count: 0x174) === child.identity,
              heap.lookup(actor + 0x6c, words: 1)?[0] == child.state,
              heap.lookup(child.state + 0x10, words: 1)?[0] == 0x4701b0,
              heap.lookup(child.state + 0x1c, words: 1)?[0] != 0 else { connections.reject(actor); return }
        let reserve = connections.host.stacklessCallerReserve
        connections.host.stacklessCallerReserve = Self.stacklessCallerReserve
        active = actor
        defer { active = nil; connections.host.stacklessCallerReserve = reserve }
        heap.lookup(0x5430c4, words: 1)![0] = scene.animationDelta
        connections.record("ClawNativeBossWarp.EndOfLevelPowerup.0x4701b0")
        var call = ClawCall(); call.function = 0x4701b0; call.argumentCount = 1; call.arguments.0 = actor
        callbackCompletion = connections.host.withObjectAllocation(provider: memory) { connections.host.invoke(call) }
    }
    override func remove(_ actor: UInt32) {
        owners.removeValue(forKey: actor); children.removeValue(forKey: actor)
    }
    override func service(_ call: ClawCall) -> UInt32? {
        guard let actor = active, valid(actor), let scene = connections.scene,
              call.receiver2 == 0, call.x87ArgumentCount == 0 else { return nil }
        let heap = scene.heap
        if call.function == 0x4f6286 {
            guard call.argumentCount == 2, let output = connections.host.bytes(call.arguments.1, count: 4),
                  let name = Self.names[call.arguments.0], let world = heap.lookup(actor + 0xc, words: 1)?[0] else { return nil }
            func dictionary(_ offset: UInt32) -> UInt32? { heap.lookup(world + offset, words: 1).map { $0[0] + 16 } }
            let token: UInt32
            do {
                if call.receiver == dictionary(0x2c), ["GAME_BOSSWARP", "GAME_POWERUP"].contains(name) {
                    token = try scene.objectResources?.sequence(name: name)?.token ?? 0
                } else if call.receiver == dictionary(0x28), name == "GAME_MAGICPOWERUP" {
                    token = scene.player.audio?.resolve(name: name)?.resourceToken ?? 0
                } else if call.receiver == dictionary(0x14), name == "EndOfLevelPowerup" {
                    token = scene.entry(named: name)
                } else if call.receiver == dictionary(0x10), ["LEVEL_GEM", "GAME_CHECKEDFLAG", "GAME_MAPPIECE"].contains(name) {
                    token = try scene.objectResources?.images(name: name)?.token ?? 0
                } else { return nil }
            } catch { return nil }
            guard valid(actor) else { return nil }
            withUnsafeBytes(of: token.littleEndian) { output.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 4) }
            connections.record("ClawActorResources.0x4f6286")
            return token == 0 ? 0 : 1
        }
        if call.function == 0x4750d0 {
            guard call.argumentCount == 0, call.receiver == scene.ownerIdentity,
                  heap.lookup(call.receiver, words: 1)?[0] == 0x50ef94,
                  heap.lookup(0x50efa4, words: 1)?[0] == call.function else { return nil }
            var globals = ClawGameFrameServiceGlobals(), context = ClawGameFrameServiceContext(), result: UInt32 = 0
            context.host = scene.actorHost
            let completed = withUnsafeMutablePointer(to: &globals) { p -> UInt32 in
                context.globals = p
                return claw_game_frame_service_entry(call.function, call.receiver, 0, &context, nil, nil, &result)
            }
            guard completed == 1, context.fault == 0 else { return nil }
            connections.record("GameFrameServices.0x4750d0"); return result
        }
        if call.function == 0x4f51c5 || call.function == 0x4f572a {
            let before = call.function == 0x4f572a
            guard call.receiver == scene.containerToken + 0x10, call.argumentCount == (before ? 2 : 1), let memory else { return nil }
            let child = before ? call.arguments.1 : call.arguments.0
            guard memory.ownsObjectAllocation(child, count: 0x1b4), heap.lookup(child + 0x68, words: 1)?[0] == 0 else { return nil }
            var fault: UInt32 = 0
            claw_scene_actor_insert(scene.containerToken, child, scene.actorHost, &fault)
            guard fault == 0, let node = heap.lookup(child + 0x68, words: 1)?[0],
                  heap.lookup(node, words: 1)?[0] == (before ? call.arguments.0 : 0) else { return nil }
            guard let state = heap.lookup(child + 0x6c, words: 1)?[0],
                  memory.ownsObjectAllocation(state, count: 0x174),
                  heap.lookup(state + 0x10, words: 1)?[0] == 0x4701b0,
                  let actorIdentity = heap.allocationIdentity(at: child, count: 0x1b4),
                  let stateIdentity = heap.allocationIdentity(at: state, count: 0x174) else { return nil }
            children[child] = Owner(actor: actorIdentity, state: state, identity: stateIdentity)
            connections.record("ClawNativeScene.list"); return node
        }
        if call.function == 0x546d5c {
            guard call.argumentCount == 5, let output = connections.host.bytes(call.arguments.0, count: 16) else { return nil }
            let values = [call.arguments.1, call.arguments.2, call.arguments.3, call.arguments.4].map(\.littleEndian)
            values.withUnsafeBytes { output.update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: 16) }
            connections.record("SetRect.0x546d5c"); return 1
        }
        return nil
    }

    override func savedAdapterState() throws -> ClawAdapterSavedState {
        try snapshotBoundary()
        guard active == nil else { throw ClawSnapshotError.activeFrame }
        let heap = connections.host.heap
        func record(_ token: UInt32, _ owner: Owner) -> ClawAdapterSavedState.Owner {
            .init(actor: ClawSnapshotWitness(heap: heap, token: token, count: 0x1b4, identity: owner.actor),
                  state: ClawSnapshotWitness(heap: heap, token: owner.state, count: 0x174, identity: owner.identity), helper: 0)
        }
        return .init(owners: owners.keys.sorted().map { record($0, owners[$0]!) }, children: children.keys.sorted().map { record($0, children[$0]!) },
            pins: pins.map { ClawSnapshotWitness(heap: heap, token: $0.0, count: $0.1, identity: $0.2, interior: true) }, memory: try memory?.savedState(), issued: [:])
    }
    override func prepareAdapterProvider(_ value: ClawAdapterSavedState) throws {
        try snapshotBoundary(); try value.validate()
        guard let saved = value.memory else { return }
        if memory == nil {
            let fresh = try ClawNativeMfcMemory(host: connections.host, sha256: ClawNativeMfcMemory.imageHash,
                importTargets: Dictionary(uniqueKeysWithValues: saved.targets.map { ($0.value, $0.key) }), allocationBase: 0x69d00000, sceneObjectAllocations: true)

            guard connections.scene?.registerObjectAllocationOwner(fresh) == true else { throw ClawSnapshotError.invalidState }
            memory = fresh
        }

    }
    override func prepareAdapterRestore(_ value: ClawAdapterSavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws -> Void {
        try snapshotBoundary(); try connections.host.heap.validateRestore(plan); try value.validate()
        guard active == nil else { throw ClawSnapshotError.activeFrame }
        guard value.issued.isEmpty, (value.owners + value.children).allSatisfy({ $0.helper == 0 }) else { throw ClawSnapshotError.invalidState }
        func records(_ values: [ClawAdapterSavedState.Owner]) throws -> [UInt32: Owner] {
            var result: [UInt32: Owner] = [:]
            for record in values {
                result[record.actor.reference.token] = Owner(actor: try record.actor.resolve(in: plan), state: record.state.reference.token,
                    identity: try record.state.resolve(in: plan))
            }
            return result
        }
        let restored = try records(value.owners)
        let restoredPins = try value.pins.map { ($0.reference.token, $0.reference.count, try $0.resolve(in: plan)) }
        var installMemory: (() throws -> Void)?
        if let saved = value.memory {
            try prepareAdapterProvider(value)
            installMemory = try memory!.prepareRestore(saved, heap: plan)
        } else {
            guard memory == nil, value.owners.isEmpty, value.children.isEmpty, value.pins.isEmpty, value.issued.isEmpty else { throw ClawSnapshotError.invalidState }
        }
        let restoredChildren = try records(value.children)
        return { [self] in
            try snapshotBoundary(); try connections.host.heap.validateInstalledRestore(plan)
            guard active == nil else { throw ClawSnapshotError.activeFrame }
            try installMemory?()
            pins = restoredPins
            children = restoredChildren
            owners = restored
        }
    }
}
