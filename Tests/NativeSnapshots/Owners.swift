import Foundation
import CryptoKit

private struct SnapshotInfrastructureFailure: Error { let message: String }
private let infrastructureOwnerKeys: Set<String> = ["resources", "audio", "input.queue", "input.window"]

private struct CanonicalBindingProbe: Codable, Equatable {
    let completed: Bool, eax: UInt32?
    let fault: ClawNativeCanonicalHost.Fault?
    let digest: String
}

// Only canonical host + allocation providers are reconstructed here. The scene
// supplies real Level 2 actors and resource bytes; no adapter/scene swap claim.
func verifySnapshotCanonicalBindings(root: URL, directory: URL, relaunch: Bool) throws {
    typealias Key = ClawNativeCanonicalHost.SnapshotProviderKey
    let build = try ClawSnapshotSlots.executableBuildIdentifier(URL(fileURLWithPath: CommandLine.arguments[0]))
    let ownerKeys: Set<String> = ["host", "left", "right"]
    let slots = ClawSnapshotSlots(directory: directory, build: build)
    var sourceScene: ClawNativeScene?
    var sourceProviders: [Key: ClawNativeMfcMemory] = [:]
    if !relaunch {
        for level: UInt32 in [1, 2] {
            let world = try ClawLevelScene(root: root, level: level)
            let player = try ClawNativePlayer(world: world.world, assets: ClawPlayerAssets(root: root, level: level), level: level)
            let scene = ClawNativeScene(player: player, clock: { 1000 })
            try scene.loadRecoveredObjects(world: world.world, root: root, level: level)
            guard scene.fault == 0, let connections = scene.objectConnections else { throw SnapshotInfrastructureFailure(message: "binding inventory") }
            // Activate even offscreen cannons, through the existing election.
            for actor in connections.ownedActors.sorted() {
                let family = connections.owner(of: actor)
                if family == "tower_cannon_left" || family == "tower_cannon_right" {
                    connections.callback(family == "tower_cannon_left" ? 0x495d40 : 0x495e00, actor: actor)
                }
            }
            guard scene.fault == 0, connections.host.fault == nil else { throw SnapshotInfrastructureFailure(message: "cannon activation \(String(describing: connections.host.fault))") }
            print("snapshot canonical inventory Level", level, connections.host.snapshotBindingInventory)
            let state = try connections.host.savedBindingsState()
            if level == 1 {
                guard state.towers.isEmpty, state.logic.isEmpty else { throw SnapshotInfrastructureFailure(message: "unexpected Level 1 binding kind") }
                let fresh = ClawNativeCanonicalHost(heap: ClawTokenHeap())
                let plan = try fresh.heap.prepareRestore(scene.heap.checkpoint().image)
                let install = try fresh.prepareBindingsRestore(state, heap: plan)
                try fresh.heap.restore(plan); try install()
                guard try fresh.savedBindingsState() == state else { throw SnapshotInfrastructureFailure(message: "Level 1 empty graph") }
                continue
            }
            guard state.towers.count == 11, state.logic.count == 22,
                  let left = (connections.adapter("tower_cannon_left") as? ClawNativeTowerCannonLeft)?.memory,
                  let right = (connections.adapter("tower_cannon_right") as? ClawNativeTowerCannonRight)?.memory
            else { throw SnapshotInfrastructureFailure(message: "Level 2 populated binding census") }
            sourceScene = scene; sourceProviders = [.towerCannonLeft: left, .towerCannonRight: right]
            // Memory retires its allocation normally; the canonical host keeps
            // its old binding witness while the token gets replacement bytes.
            let stale = state.towers.last!.helper.reference.token
            var release = ClawCall(); release.function = 0x5469d8; release.argumentCount = 1
            release.stackPointer = UInt32(CLAW_STACK_TOP); release.arguments.0 = stale
            guard sourceProviders[state.towers.last!.provider]!.service(release) == 0,
                  scene.heap.lookupBytes(stale, count: 0x7c) == nil
            else { throw SnapshotInfrastructureFailure(message: "source helper retirement") }
            scene.heap.storeBytes(token: stale, count: 0x7c)[0] = 0xa5
            try slots.save(ClawSnapshotImage(build: build, level: level, heap: try scene.heap.checkpoint().image, owners: [
                "host": try ClawSnapshotOwnerDecoder.encode(connections.host.savedBindingsState()),
                "left": try ClawSnapshotOwnerDecoder.encode(left.savedState()),
                "right": try ClawSnapshotOwnerDecoder.encode(right.savedState())
            ]), to: .quick)
        }
    }
    // A new slot reader and new host/providers force disk decoding and fresh
    // native identities in this process as well as in --relaunch's process.
    let image = try ClawSnapshotSlots(directory: directory, build: build).load(.quick)
    var decoder = try ClawSnapshotOwnerDecoder(image.owners, requiring: ownerKeys)
    let state = try decoder.decode(ClawNativeCanonicalHost.BindingsSavedState.self, key: "host")
    let left = try decoder.decode(ClawNativeMfcMemory.SavedState.self, key: "left")
    let right = try decoder.decode(ClawNativeMfcMemory.SavedState.self, key: "right")
    try decoder.finish()
    let fresh = ClawNativeCanonicalHost(heap: ClawTokenHeap())
    var providers: [Key: ClawNativeMfcMemory] = [:]
    for (key, saved) in [(Key.towerCannonLeft, left), (.towerCannonRight, right)] {
        providers[key] = try ClawNativeMfcMemory(host: fresh, sha256: ClawNativeMfcMemory.imageHash,
            importTargets: Dictionary(uniqueKeysWithValues: saved.targets.map { ($0.value, $0.key) }))
    }
    let plan = try fresh.heap.prepareRestore(image.heap)
    do { _ = try fresh.prepareBindingsRestore(state, heap: plan); throw SnapshotInfrastructureFailure(message: "missing providers accepted") }
    catch ClawSnapshotError.incompleteOwners { }
    guard fresh.snapshotBindingInventory.values.allSatisfy({ $0 == 0 }) else { throw SnapshotInfrastructureFailure(message: "failed prepare published bindings") }
    try fresh.registerSnapshotProvider(providers[.towerCannonLeft]!, key: .towerCannonLeft)
    try fresh.registerSnapshotProvider(providers[.towerCannonRight]!, key: .towerCannonRight)
    do {
        try fresh.registerSnapshotProvider(providers[.towerCannonRight]!, key: .towerCannonLeft)
        throw SnapshotInfrastructureFailure(message: "provider key was rebound")
    } catch ClawSnapshotError.invalidState { }
    let unsupported = ClawNativeCanonicalHost.BindingsSavedState(version: state.version, providers: state.providers,
        towers: [.init(kind: 0x48a800, provider: .towerCannonLeft, actor: state.towers[0].actor,
            state: state.towers[0].state, helper: state.towers[0].helper)], logic: state.logic,
        fault: state.fault, maximumOperations: state.maximumOperations)
    do {
        _ = try fresh.prepareBindingsRestore(unsupported, heap: plan)
        throw SnapshotInfrastructureFailure(message: "unsupported populated kind accepted")
    } catch ClawSnapshotError.invalidState { }
    let installHost = try fresh.prepareBindingsRestore(state, heap: plan)
    let installLeft = try providers[.towerCannonLeft]!.prepareRestore(left, heap: plan)
    let installRight = try providers[.towerCannonRight]!.prepareRestore(right, heap: plan)
    // The barrier rejects both capture and restore while a source graph (even
    // with no instructions running yet) or allocator/callback scope is active.
    var rejected = 0
    _ = fresh.withSourceGraph { _ in
        do { _ = try fresh.savedBindingsState() } catch ClawSnapshotError.activeFrame { rejected += 1 } catch { }
        do { _ = try fresh.prepareBindingsRestore(state, heap: plan) } catch ClawSnapshotError.activeFrame { rejected += 1 } catch { }
        do { _ = try providers[.towerCannonLeft]!.savedState() } catch ClawSnapshotError.activeFrame { rejected += 1 } catch { }
    }
    _ = fresh.withObjectAllocation(provider: providers[.towerCannonLeft]!) {
        do { _ = try fresh.savedBindingsState() } catch ClawSnapshotError.activeFrame { rejected += 1 } catch { }
        do { try installHost() } catch ClawSnapshotError.activeFrame { rejected += 1 } catch { }
    }
    guard rejected == 5 else { throw SnapshotInfrastructureFailure(message: "active source/allocator accepted") }
    try fresh.heap.restore(plan); try installLeft(); try installRight(); try installHost()
    guard try fresh.savedBindingsState() == state,
          try providers[.towerCannonLeft]!.savedState() == left,
          try providers[.towerCannonRight]!.savedState() == right
    else { throw SnapshotInfrastructureFailure(message: "canonical/provider roundtrip") }
    for record in state.towers {
        let provider = providers[record.provider]!, token = record.helper.reference.token
        guard provider.ownsObjectAllocation(token, count: 0x7c) == record.helper.live else { throw SnapshotInfrastructureFailure(message: "retired helper rebound") }
        if let source = sourceScene?.objectConnections?.host,
           let original = source.heap.containingAllocationIdentity(at: record.actor.reference.token, count: 0x1b4),
           fresh.heap.containingAllocationIdentity(at: record.actor.reference.token, count: 0x1b4) === original {
            throw SnapshotInfrastructureFailure(message: "host graph retained original allocation identity")
        }
    }
    func replay(_ host: ClawNativeCanonicalHost, _ providers: [Key: ClawNativeMfcMemory]) throws -> [CanonicalBindingProbe] {
        var probes: [CanonicalBindingProbe] = []
        // Both callback elections continue on their actual populated helpers.
        // A final stale invocation must fault without modifying reused storage.
        let ordered = state.towers.filter { $0.helper.live } + state.towers.filter { !$0.helper.live }
        for record in ordered {
            let primary = record.state.reference.token
            host.heap.lookup(primary + 0x1c, words: 1)![0] = 1000
            var call = ClawCall(); call.function = record.kind; call.argumentCount = 1; call.arguments.0 = record.actor.reference.token
            var result: ClawNativeCanonicalHost.Completion?
            host.stacklessCallerReserve = 0x40
            _ = host.withObjectAllocation(provider: providers[record.provider]!) { result = host.invoke(call) }
            host.stacklessCallerReserve = nil
            guard let result, record.helper.live ? result.completed : result.fault != nil
            else { throw SnapshotInfrastructureFailure(message: "continued callback \(String(record.kind, radix: 16)) \(String(describing: host.fault))") }
            var digest = SHA256()
            for allocation in try host.heap.checkpoint().image.allocations {
                var token = allocation.token.littleEndian
                withUnsafeBytes(of: &token) { digest.update(data: $0) }
                digest.update(data: allocation.bytes)
            }
            probes.append(.init(completed: result.completed, eax: result.eax, fault: result.fault,
                digest: digest.finalize().map { String(format: "%02x", $0) }.joined()))
        }
        return probes
    }
    let actual = try replay(fresh, providers), expectedURL = directory.appendingPathComponent("continuation.plist")
    if let source = sourceScene?.objectConnections?.host {
        let expected = try replay(source, sourceProviders)
        guard expected == actual else { throw SnapshotInfrastructureFailure(message: "source/restored callback returns, faults or token writes differ") }
        try ClawSnapshotOwnerDecoder.encode(expected).write(to: expectedURL, options: .atomic)
    } else {
        guard try PropertyListDecoder().decode([CanonicalBindingProbe].self, from: Data(contentsOf: expectedURL)) == actual
        else { throw SnapshotInfrastructureFailure(message: "second-process callback continuation differs") }
    }
    guard let stale = state.towers.first(where: { !$0.helper.live }), fresh.heap.lookupBytes(stale.helper.reference.token, count: 0x7c)?[0] == 0xa5
    else { throw SnapshotInfrastructureFailure(message: "stale callback wrote replacement") }
    print("{\"check\":\"snapshot-canonical-bindings\",\"status\":\"pass\",\"towers\":\(state.towers.count),\"logic\":\(state.logic.count),\"second_process\":\(relaunch),\"retired_and_reused\":true,\"whole_scene\":false}")
}

func verifySnapshotMenuResourceOwner() throws {
    let archive = URL(fileURLWithPath: "Original/claw-disc/files/DATA/CLAW.REZ")
    func service(_ owner: ClawNativeMenuResources, _ function: UInt32, _ arguments: [UInt32]) throws -> UInt32 {
        var call = ClawCall(); call.function = function; call.argumentCount = UInt32(arguments.count)
        withUnsafeMutableBytes(of: &call.arguments) { raw in
            for (index, value) in arguments.enumerated() { raw.bindMemory(to: UInt32.self)[index] = value }
        }
        let result = owner.service(call)
        guard owner.fault == 0 else { throw SnapshotInfrastructureFailure(message: "menu resource service \(String(function, radix: 16))") }
        return result
    }
    let heap = ClawTokenHeap(), resources = try ClawNativeMenuResources(heap: heap, archiveURL: archive, metadata: [:])
    let name = resources.textToken("CLAW.REZ"), mode = resources.textToken("rb")
    let handle = try service(resources, 0x4f1d90, [name, mode])
    let closed = try service(resources, 0x4f1d90, [name, mode])
    resources.release(name); resources.release(mode)
    _ = try service(resources, 0x4a7840, [handle, 1234, 0])
    _ = try service(resources, 0x4a7ae0, [closed])
    let buffer = resources.allocate(64), stale = resources.allocate(7)
    heap.free(stale); heap.storeBytes(token: stale, count: 7)[0] = 0xa5
    let state = try resources.savedState(), image = try heap.checkpoint().image
    let encoder = PropertyListEncoder()
    let decoded = try PropertyListDecoder().decode(ClawNativeMenuResources.SavedState.self, from: encoder.encode(state))
    let candidateHeap = ClawTokenHeap(), candidate = try ClawNativeMenuResources(heap: candidateHeap, archiveURL: archive, metadata: [:])
    let plan = try candidateHeap.prepareRestore(image)
    let apply = try candidate.prepareRestore(decoded, heap: plan)
    try candidateHeap.restore(plan); try apply()
    guard handle != 0, try candidate.savedState() == state, candidate.openFileCount == 1,
          candidate.owns(buffer), !candidate.owns(stale), candidate.allocationData(stale) == nil
    else { throw SnapshotInfrastructureFailure(message: "menu resource graph differs") }
    _ = try service(resources, 0x4a7260, [buffer, 1, 64, handle])
    _ = try service(candidate, 0x4a7260, [buffer, 1, 64, handle])
    guard resources.allocationData(buffer) == candidate.allocationData(buffer), try resources.savedState() == candidate.savedState(),
          try service(candidate, 0x4a7ae0, [closed]) == UInt32.max
    else { throw SnapshotInfrastructureFailure(message: "restored file cursor/retired handle differs") }
    guard candidate.releaseIfOwned(stale) else { throw SnapshotInfrastructureFailure(message: "retired resource claim fell through to another owner") }
    guard candidate.fault != 0, candidateHeap.lookupBytes(stale, count: 7)?[0] == 0xa5
    else { throw SnapshotInfrastructureFailure(message: "retired resource owner released replacement") }
    candidate.close()
    guard candidateHeap.lookupBytes(stale, count: 7)?[0] == 0xa5 else { throw SnapshotInfrastructureFailure(message: "resource teardown released replacement") }
    print("{\"check\":\"snapshot-menu-resource-owner\",\"status\":\"pass\",\"file_offset\":1234,\"retired_and_reused\":true,\"whole_scene\":false}")
}

func verifySnapshotLockOwners() throws {
    let slots = Set(ClawNativeMfcMemory.importArities.keys).union(ClawNativeMfcLocks.importSlots).sorted()
    let imports = Dictionary(uniqueKeysWithValues: slots.enumerated().map { ($0.element, UInt32(0x710300 + $0.offset * 4)) })
    func make(_ heap: ClawTokenHeap) throws -> (ClawNativePhysicalSections, ClawNativeMfcLocks, ClawNativeMfcMemory) {
        let host = ClawNativeCanonicalHost(heap: heap), sections = ClawNativePhysicalSections(heap: heap)
        let locks = try ClawNativeMfcLocks(host: host, sha256: ClawNativeMfcLocks.imageHash,
            initialBytes: [UInt8](repeating: 0, count: Int(ClawNativeMfcLocks.imageCount)),
            importTargets: imports.filter { ClawNativeMfcLocks.importSlots.contains($0.key) }, sharedSections: sections)
        let memory = try ClawNativeMfcMemory(host: host, sha256: ClawNativeMfcMemory.imageHash,
            importTargets: imports.filter { ClawNativeMfcMemory.importArities[$0.key] != nil }, locks: locks, sharedSections: sections)
        return (sections, locks, memory)
    }
    let heap = ClawTokenHeap(), source = try make(heap)
    try source.1.adoptInitializedSection(ClawNativeMfcLocks.master)
    _ = try source.0.perform(slot: 0x546aac, address: ClawNativeMfcLocks.master)
    do { _ = try source.1.savedState(); throw SnapshotInfrastructureFailure(message: "lock owner captured shared held section") }
    catch ClawSnapshotError.activeFrame { }
    do { _ = try source.2.savedState(); throw SnapshotInfrastructureFailure(message: "MFC owner captured shared held section") }
    catch ClawSnapshotError.activeFrame { }
    _ = try source.0.perform(slot: 0x546a9c, address: ClawNativeMfcLocks.master)
    heap.store(token: 0x2100, words: 6)[0] = 0
    _ = try source.0.perform(slot: 0x546aa4, address: 0x2100)
    _ = try source.0.perform(slot: 0x546aa0, address: 0x2100)
    let manager = try source.2.createManager()
    _ = try source.0.perform(slot: 0x546aa4, address: manager + 0x1c)
    _ = try source.2.createTLSLocal(count: 13, zero: true)
    let sectionsState = try source.0.savedState(), locksState = try source.1.savedState(), memoryState = try source.2.savedState()
    let image = try heap.checkpoint().image
    let candidateHeap = ClawTokenHeap(), candidate = try make(candidateHeap)
    let plan = try candidateHeap.prepareRestore(image)
    let applySections = try candidate.0.prepareRestore(sectionsState, heap: plan)
    let applyLocks = try candidate.1.prepareRestore(locksState, heap: plan)
    let applyMemory = try candidate.2.prepareRestore(memoryState, heap: plan)
    try candidateHeap.restore(plan); try applySections(); try applyLocks(); try applyMemory()
    guard candidate.0.valid(), try candidate.0.savedState() == sectionsState,
          try candidate.1.savedState() == locksState, try candidate.2.savedState() == memoryState,
          candidate.2.sharedSections === candidate.0, candidate.1.sharedSections === candidate.0
    else { throw SnapshotInfrastructureFailure(message: "shared lock/MFC graph lost identity or state") }
    for sections in [source.0, candidate.0] {
        _ = try sections.perform(slot: 0x546aac, address: manager + 0x1c)
        _ = try sections.perform(slot: 0x546a9c, address: manager + 0x1c)
    }
    guard try candidate.0.savedState() == source.0.savedState() else { throw SnapshotInfrastructureFailure(message: "shared lock continuation differs") }
    print("{\"check\":\"snapshot-shared-lock-owners\",\"status\":\"pass\",\"whole_scene\":false}")
}

// Resource/audio/input graph proof only. This deliberately does not instantiate
// a restored scene or substitute for --snapshot-scenes-only's gameplay proof.
func verifySnapshotInfrastructure(root: URL, directory: URL, relaunch: Bool) throws {
    let build = try ClawSnapshotSlots.executableBuildIdentifier(URL(fileURLWithPath: CommandLine.arguments[0]))
    for level: UInt32 in [1, 2] {
        let location = directory.appendingPathComponent("level-\(level)", isDirectory: true)
        let slots = ClawSnapshotSlots(directory: location, build: build)
        let source: (ClawTokenHeap, ClawNativeAudio, ClawActorResources, ClawNativeWindowInput)?
        if !relaunch {
            let world = try ClawLevelScene(root: root, level: level)
            let player = try ClawNativePlayer(world: world.world, assets: ClawPlayerAssets(root: root, level: level), level: level)
            let scene = ClawNativeScene(player: player, clock: { 1000 })
            try scene.loadRecoveredObjects(world: world.world, root: root, level: level)
            guard scene.fault == 0, let sceneResources = scene.objectResources else { throw SnapshotInfrastructureFailure(message: "Level \(level) resource census failed") }
            let census = try sceneResources.savedState()
            let heap = ClawTokenHeap()
            let audio = try ClawNativeAudio(root: root, outputEnabled: false, sharedHeap: heap, level: level)
            let resources = try ClawActorResources(root: root, heap: heap, level: level, resolveEvent: { audio.resolve(name: $0)?.resourceToken ?? 0 })
            for record in census.images {
                let loaded = record.name.hasPrefix("TILES_")
                    ? try resources.tileImages(name: String(record.name.dropFirst(6)))
                    : try resources.images(name: record.name)
                guard loaded != nil else { throw SnapshotInfrastructureFailure(message: "missing image set \(record.name)") }
            }
            for record in census.sequences {
                guard try resources.sequence(name: record.name) != nil else { throw SnapshotInfrastructureFailure(message: "missing sequence \(record.name)") }
            }
            _ = audio.play(name: "GAME_BOINKJR", request: ClawAudioRequest(volume: 80, pan: 0, pitchPercent: 100, looping: 1))
            _ = audio.play(name: "GAME_BOINKJR", request: ClawAudioRequest(volume: 65, pan: UInt32(bitPattern: -13), pitchPercent: 113, looping: 1))
            let input = ClawNativeWindowInput(); input.key(mask: 0x2000000, down: true)
            input.menuKey(0x10, down: true); _ = input.showCursor(false)
            let image = ClawSnapshotImage(build: build, level: level, heap: try heap.checkpoint().image, owners: [
                "resources": try ClawSnapshotOwnerDecoder.encode(resources.savedState()),
                "audio": try ClawSnapshotOwnerDecoder.encode(audio.savedState()),
                "input.queue": try ClawSnapshotOwnerDecoder.encode(input.queue.savedState()),
                "input.window": try ClawSnapshotOwnerDecoder.encode(input.savedState())
            ])
            try slots.save(image, to: .quick)
            source = (heap, audio, resources, input)
        } else { source = nil }
        // A new slot owner forces disk reads even in the first process.
        let image = try ClawSnapshotSlots(directory: location, build: build).load(.quick)
        guard image.level == level else { throw SnapshotInfrastructureFailure(message: "wrong archived level") }
        var decoder = try ClawSnapshotOwnerDecoder(image.owners, requiring: infrastructureOwnerKeys)
        let resourcesState = try decoder.decode(ClawActorResources.SavedState.self, key: "resources")
        let audioState = try decoder.decode(ClawNativeAudio.SavedState.self, key: "audio")
        let queueState = try decoder.decode(ClawNativeWindowInputQueue.SavedState.self, key: "input.queue")
        let inputState = try decoder.decode(ClawNativeWindowInput.SavedState.self, key: "input.window")
        try decoder.finish()
        let heap = ClawTokenHeap()
        let audio = try ClawNativeAudio(root: root, outputEnabled: false, sharedHeap: heap, preload: false, level: level)
        let resources = try ClawActorResources(root: root, heap: heap, level: level, resolveEvent: { audio.resolve(name: $0)?.resourceToken ?? 0 })
        let queue = ClawNativeWindowInputQueue(); try queue.restoreState(queueState)
        let input = try ClawNativeWindowInput(restoring: inputState, queue: queue)
        let plan = try heap.prepareRestore(image.heap)
        let applyAudio = try audio.prepareRestore(audioState, heap: plan)
        let applyResources = try resources.prepareRestore(resourcesState, heap: plan)
        try heap.restore(plan); try applyAudio(); try applyResources()
        guard try audio.savedState() == audioState, try resources.savedState() == resourcesState,
              queue.savedState() == queueState, input.savedState() == inputState else { throw SnapshotInfrastructureFailure(message: "restored infrastructure differs") }
        let continuation = try infrastructureContinuation(heap: heap, audio: audio, resources: resources, input: input)
        let hashesFile = location.appendingPathComponent("continuation.plist")
        if let source {
            let expected = try infrastructureContinuation(heap: source.0, audio: source.1, resources: source.2, input: source.3)
            guard continuation == expected else { throw SnapshotInfrastructureFailure(message: "Level \(level) resource/audio/input continuation differs") }
            try ClawSnapshotOwnerDecoder.encode(expected).write(to: hashesFile, options: .atomic)
        } else {
            let expected = try PropertyListDecoder().decode([String].self, from: Data(contentsOf: hashesFile))
            guard continuation == expected else { throw SnapshotInfrastructureFailure(message: "Level \(level) second-process continuation differs") }
        }
        print("{\"check\":\"snapshot-infrastructure-graph\",\"status\":\"pass\",\"level\":\(level),\"second_process\":\(relaunch),\"steps\":\(continuation.count),\"image_sets\":\(resourcesState.images.count),\"sequences\":\(resourcesState.sequences.count),\"whole_scene\":false}")
    }
}

private func infrastructureContinuation(heap: ClawTokenHeap, audio: ClawNativeAudio,
                                       resources: ClawActorResources, input: ClawNativeWindowInput) throws -> [String] {
    var hashes: [String] = []
    for step in 0..<12 {
        // Cache misses exercise restored allocation cursors and audio event
        // resolution. Each new sequence must use the restored audio registry.
        for name in ["CLAW_WALK", "CLAW_JUMP", "CLAW_DUCK", "CLAW_STAND"] {
            _ = try resources.sequence(name: name)
        }
        input.key(mask: 0x2000000, down: step % 2 == 0)
        let event = input.frameInput()
        var left = [Float](repeating: 0, count: 1024), right = left
        left.withUnsafeMutableBufferPointer { l in right.withUnsafeMutableBufferPointer { r in
            audio.render(left: l.baseAddress!, right: r.baseAddress!, frames: 1024, sampleRate: 44100)
        } }
        var digest = SHA256()
        left.withUnsafeBytes { digest.update(data: $0) }; right.withUnsafeBytes { digest.update(data: $0) }
        let image = try heap.checkpoint().image
        var next = image.nextToken.littleEndian
        withUnsafeBytes(of: &next) { digest.update(data: $0) }
        for allocation in image.allocations {
            var token = allocation.token.littleEndian, count = allocation.byteCount.littleEndian
            withUnsafeBytes(of: &token) { digest.update(data: $0) }; withUnsafeBytes(of: &count) { digest.update(data: $0) }
            digest.update(data: allocation.bytes)
        }
        var held = event.held.littleEndian, pressed = event.pressed.littleEndian
        withUnsafeBytes(of: &held) { digest.update(data: $0) }; withUnsafeBytes(of: &pressed) { digest.update(data: $0) }
        hashes.append(digest.finalize().map { String(format: "%02x", $0) }.joined())
    }
    return hashes
}

// These are adapter callbacks on a reconstructed component graph. No scene is
// published, and no whole-scene gameplay continuation is claimed here.
func verifySnapshotAdapters(root: URL, directory: URL, relaunch: Bool) throws {
    let build = try ClawSnapshotSlots.executableBuildIdentifier(URL(fileURLWithPath: CommandLine.arguments[0]))
    let world = try ClawLevelScene(root: root, level: 2)
    let elections = ClawNativeObjectConnections.elections.filter { ["ani_cycle", "boss_warp", "tower_cannon_left", "tower_cannon_right"].contains($0.family) }
    func make(populated: Bool = true) throws -> ClawNativeScene {
        let player = try ClawNativePlayer(world: world.world, assets: ClawPlayerAssets(root: root, level: 2), level: 2)
        let scene = ClawNativeScene(player: player, clock: { 1000 })
        try scene.loadRecoveredObjects(world: world.world, root: root, level: 2,
            objectElections: elections)
        if !populated { scene.installObjectConnections(elections) }
        return scene
    }
    let source: ClawNativeScene?
    if !relaunch {
        let scene = try make(), connections = scene.objectConnections!
        let ordered = connections.ownedActors.sorted().sorted {
            let a = connections.owner(of: $0)!.hasPrefix("tower_cannon")
            let b = connections.owner(of: $1)!.hasPrefix("tower_cannon")
            return a == b ? $0 < $1 : a
        }
        for token in ordered {
            let actor = scene.snapshotActor(token)!
            connections.callback(actor.primary.4, actor: token)
            guard connections.host.fault == nil else { throw SnapshotInfrastructureFailure(message: "adapter activation \(connections.owner(of: token) ?? "") \(String(describing: connections.host.fault))") }
        }
        let warp = connections.adapter("boss_warp") as! ClawNativeBossWarp
        let warpActor = warp.tokens.first!
        let primary = scene.heap.lookup(warpActor + 0x6c, words: 1)![0]
        // The component fixture elects the derived scene's reviewed mode getter.
        // The unadvanced WWD loader retains the generic base vtable (mode zero).
        // Use the real GameFrameServices mode-four method through the adapter;
        // the canonical BossWarp body alone constructs/initializes its child.
        scene.heap.store(token: 0x50ef94, words: 5)[4] = 0x4750d0
        scene.heap.lookup(scene.ownerIdentity, words: 1)![0] = 0x50ef94
        scene.heap.lookup(primary + 0x1c, words: 1)![0] = 0
        connections.callback(0x470870, actor: warpActor)
        guard connections.host.fault == nil, try !warp.savedAdapterState().children.isEmpty else {
            throw SnapshotInfrastructureFailure(message: "source BossWarp child creation \(String(describing: connections.host.fault))")
        }
        let state = try connections.savedAdaptersState()
        guard state.bindings.towers.count == 11 else { throw SnapshotInfrastructureFailure(message: "cannon activation census") }
        // Keep both an actor and a primary-state tombstone while their token
        // storage is reused. Canonical bindings also retain a retired helper.
        let ani = state.adapters["ani_cycle"]!.owners
        for token in [ani[0].actor.reference.token, ani[1].state.reference.token] {
            let count: UInt32 = token == ani[0].actor.reference.token ? 0x1b4 : 0x174
            scene.heap.free(token); scene.heap.storeBytes(token: token, count: count)[0] = 0xa5
        }
        let tower = state.bindings.towers.last!
        let memory = tower.provider == .towerCannonLeft
            ? (connections.adapter("tower_cannon_left") as! ClawNativeTowerCannonLeft).memory!
            : (connections.adapter("tower_cannon_right") as! ClawNativeTowerCannonRight).memory!
        var free = ClawCall(); free.function = 0x5469d8; free.argumentCount = 1
        free.stackPointer = UInt32(CLAW_STACK_TOP); free.arguments.0 = tower.helper.reference.token
        guard memory.service(free) == 0 else { throw SnapshotInfrastructureFailure(message: "helper retirement") }
        scene.heap.storeBytes(token: free.arguments.0, count: 0x7c)[0] = 0xa5
        let owners: [String: Data] = [
            "adapters": try ClawSnapshotOwnerDecoder.encode(connections.savedAdaptersState()),
            "resources": try ClawSnapshotOwnerDecoder.encode(scene.objectResources!.savedState()),
            "audio": try ClawSnapshotOwnerDecoder.encode(scene.player.audio!.savedState()),
            "actors": try ClawSnapshotOwnerDecoder.encode(scene.savedDynamicActorsState()),
            "scheduler": try ClawSnapshotOwnerDecoder.encode(scene.savedSchedulerState())
        ]
        try ClawSnapshotSlots(directory: directory, build: build).save(
            ClawSnapshotImage(build: build, level: 2, heap: try scene.heap.checkpoint().image, owners: owners), to: .quick)
        source = scene
    } else { source = nil }
    let image = try ClawSnapshotSlots(directory: directory, build: build).load(.quick)
    var decoder = try ClawSnapshotOwnerDecoder(image.owners, requiring: ["adapters", "resources", "audio", "actors", "scheduler"])
    let state = try decoder.decode(ClawNativeObjectConnections.AdaptersSavedState.self, key: "adapters")
    let resources = try decoder.decode(ClawActorResources.SavedState.self, key: "resources")
    let audio = try decoder.decode(ClawNativeAudio.SavedState.self, key: "audio")
    let actors = try decoder.decode(ClawNativeScene.DynamicActorsSavedState.self, key: "actors")
    let scheduler = try decoder.decode(ClawNativeScene.SchedulerSavedState.self, key: "scheduler")
    try decoder.finish()
    let candidate = try make(populated: false), connections = candidate.objectConnections!
    try connections.prepareAdapterProviders(state)
    let plan = try candidate.heap.prepareRestore(image.heap)
    var missing = state.adapters; missing.removeValue(forKey: "ani_cycle")
    for entries in [missing, state.adapters.merging(["unknown": state.adapters["ani_cycle"]!], uniquingKeysWith: { a, _ in a })] {
        do {
            _ = try connections.prepareAdaptersRestore(.init(ownership: state.ownership, adapters: entries, bindings: state.bindings), heap: plan)
            throw SnapshotInfrastructureFailure(message: "adapter coverage accepted")
        } catch ClawSnapshotError.incompleteOwners { }
    }
    let installActors = try candidate.reconstructDynamicActors(actors, heap: plan)
    let installAudio = try candidate.player.audio!.prepareRestore(audio, heap: plan)
    let installResources = try candidate.objectResources!.prepareRestore(resources, heap: plan)
    let install = try connections.prepareAdaptersRestore(state, heap: plan)
    do { try install(); throw SnapshotInfrastructureFailure(message: "adapter accepted uninstalled heap") }
    catch ClawTokenHeap.SnapshotError.stalePlan { }
    var rejected = 0
    _ = connections.host.withSourceGraph { _ in
        do { _ = try connections.savedAdaptersState() } catch ClawSnapshotError.activeFrame { rejected += 1 } catch { }
        do { _ = try connections.prepareAdaptersRestore(state, heap: plan) } catch ClawSnapshotError.activeFrame { rejected += 1 } catch { }
        do { try install() } catch ClawSnapshotError.activeFrame { rejected += 1 } catch { }
    }
    guard rejected == 3 else { throw SnapshotInfrastructureFailure(message: "adapter active-call barrier") }
    try candidate.heap.restore(plan); try installAudio(); try installResources(); try installActors()
    try candidate.restoreSchedulerState(scheduler); try install()
    guard try connections.savedAdaptersState() == state else { throw SnapshotInfrastructureFailure(message: "adapter/provider/binding graph roundtrip") }
    if let source {
        let old = (source.objectConnections!.adapter("tower_cannon_left") as! ClawNativeTowerCannonLeft).memory!
        guard old !== (connections.adapter("tower_cannon_left") as! ClawNativeTowerCannonLeft).memory!
        else { throw SnapshotInfrastructureFailure(message: "source provider leaked") }
    }
    func digest(_ scene: ClawNativeScene) throws -> String {
        var hash = SHA256()
        var semantic = SnapshotSemanticState(heap: try scene.heap.snapshotTopology())
        hash.update(data: try semantic.bytes(scene.objectConnections!.savedAdaptersState()))
        for allocation in try scene.heap.checkpoint().image.allocations {
            var token = allocation.token.littleEndian
            withUnsafeBytes(of: &token) { hash.update(data: $0) }; hash.update(data: allocation.bytes)
        }
        return hash.finalize().map { String(format: "%02x", $0) }.joined()
    }
    func continuation(_ scene: ClawNativeScene) throws -> [String] {
        let bridge = scene.objectConnections!
        var probes: [String] = []
        let saved = try bridge.savedAdaptersState()
        for family in saved.adapters.keys.sorted() {
            for owner in saved.adapters[family]!.owners where owner.actor.live && owner.state.live && (owner.helper == 0 || saved.bindings.towers.first(where: { $0.helper.reference.token == owner.helper })?.helper.live == true) {
                let actor = owner.actor.reference.token
                if family.hasPrefix("tower_cannon") { scene.heap.lookup(owner.state.reference.token + 0x1c, words: 1)![0] = 1000 }
                bridge.callback(scene.snapshotActor(actor)!.primary.4, actor: actor)
                guard bridge.host.fault == nil else { throw SnapshotInfrastructureFailure(message: "continued \(family) \(String(describing: bridge.host.fault))") }
                let result = bridge.adapter(family)!.callbackCompletion
                guard result?.completed == true else { throw SnapshotInfrastructureFailure(message: "missing callback completion") }
                probes.append(String(describing: result) + (try digest(scene)))
            }
        }
        let warp = bridge.adapter("boss_warp") as! ClawNativeBossWarp
        for child in saved.adapters["boss_warp"]!.children {
            for _ in 0..<3 {
                warp.childCallback(child.actor.reference.token)
                guard bridge.host.fault == nil, warp.callbackCompletion?.completed == true else {
                    throw SnapshotInfrastructureFailure(message: "BossWarp child continuation \(String(describing: bridge.host.fault))")
                }
                probes.append(String(describing: warp.callbackCompletion) + (try digest(scene)))
            }
        }
        // Real issued teardown, then an actor with retired storage is rejected.
        let tower = saved.adapters["tower_cannon_left"]!.owners.first!
        bridge.remove(tower.actor.reference.token)
        let left = bridge.adapter("tower_cannon_left") as! ClawNativeTowerCannonLeft
        guard bridge.host.fault == nil, left.memory?.ownsObjectAllocation(tower.helper, count: 0x7c) == false,
              try left.savedAdapterState().issued[tower.helper] == 0x7c else {
            throw SnapshotInfrastructureFailure(message: "helper release lost issued teardown ledger")
        }
        probes.append(try digest(scene))
        let stale = saved.adapters["ani_cycle"]!.owners.first(where: { !$0.actor.live })!
        bridge.callback(0x4918b0, actor: stale.actor.reference.token)
        guard bridge.host.fault != nil, scene.heap.lookupBytes(stale.actor.reference.token, count: 0x1b4)?[0] == 0xa5 else { throw SnapshotInfrastructureFailure(message: "retired adapter rebound") }
        probes.append(String(describing: bridge.host.fault) + (try digest(scene)))
        return probes
    }
    let actual = try continuation(candidate), file = directory.appendingPathComponent("continuation.plist")
    if let source {
        let expected = try continuation(source)
        guard actual == expected else { throw SnapshotInfrastructureFailure(message: "adapter continuation differs at \(zip(actual, expected).enumerated().first(where: { $0.element.0 != $0.element.1 })?.offset ?? -1)") }
        try ClawSnapshotOwnerDecoder.encode(expected).write(to: file, options: .atomic)
    } else {
        guard try PropertyListDecoder().decode([String].self, from: Data(contentsOf: file)) == actual else { throw SnapshotInfrastructureFailure(message: "second-process adapter continuation") }
    }
    // Persist a previously-used unsupported election after its final actor is
    // removed. An empty dispatch map must never license dropping native state.
    let unsupported = ClawNativeObjectConnections(scene: candidate)
    let own = try unsupported.savedOwnershipState()
    let witness = candidate.heap.containingAllocationIdentity(at: 0x10002000, count: 4)!
    let unsupportedFamily = own.families.subtracting(Set(elections.map(\.family))).sorted().first!
    let record = ClawNativeObjectConnections.OwnershipSavedState.Record(actor: 0x10002000, family: unsupportedFamily, identity: witness.snapshotID,
        live: candidate.heap.snapshotReference(at: 0x10002000, count: 4, identity: witness, interior: true))
    let history = ClawNativeObjectConnections.OwnershipSavedState(callbacks: own.callbacks, families: own.families, owners: [record], usedFamilies: [unsupportedFamily])
    let historyPlan = try candidate.heap.prepareRestore(candidate.heap.checkpoint())
    try unsupported.prepareOwnershipRestore(history, heap: historyPlan)()
    unsupported.remove(0x10002000)
    guard unsupported.ownedActors.isEmpty else { throw SnapshotInfrastructureFailure(message: "unsupported removal") }
    do { _ = try unsupported.savedAdaptersState(); throw SnapshotInfrastructureFailure(message: "empty unsupported adapter history omitted") }
    catch ClawSnapshotError.incompleteOwners { }
    print("{\"check\":\"snapshot-adapters\",\"status\":\"pass\",\"second_process\":\(relaunch),\"callbacks\":\(actual.count),\"boss_children\":\(state.adapters["boss_warp"]!.children.count),\"whole_scene\":false}")
}
