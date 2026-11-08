import Foundation
import CryptoKit

private struct SnapshotPlayerFailure: Error { let message: String }

// This checks the player owner in isolation, not whole-level determinism. The
// complete scene checkpoint must also restore audio, adapters and shared state.
func verifySnapshotPlayer(root: URL) throws {
    try verifySnapshotWindowOwners()
    try verifySnapshotMfcOwner()
    try verifySnapshotLockOwners()
    try verifySnapshotMenuResourceOwner()
    let world = try ClawLevelScene(root: root)
    let player = try ClawNativePlayer(world: world.world, assets: ClawPlayerAssets(root: root))
    let encoder = JSONEncoder(); encoder.outputFormatting = .sortedKeys
    func digest() throws -> String {
        SHA256.hash(data: try encoder.encode(player.savedState())).map { String(format: "%02x", $0) }.joined()
    }
    func replay() throws -> [String] {
        var hashes: [String] = []
        for frame in 0..<600 {
            player.advance(direction: (frame / 30) % 2 == 0 ? 1 : -1,
                jumpHeld: frame % 120 < 12, jumpPressed: frame % 120 == 0,
                stageDelta: 17, animationDelta: 17)
            if let failure = player.failure { throw SnapshotPlayerFailure(message: "frame \(frame): \(failure)") }
            hashes.append(try digest())
        }
        return hashes
    }
    // Warm animation/resource caches before capturing; resources are immutable
    // dependencies of this owner and their native ledgers are checked elsewhere.
    player.advance(direction: 0, stageDelta: 17, animationDelta: 17)
    let saved = player.savedState(), start = try digest()
    let plist = PropertyListEncoder(); plist.outputFormat = .binary
    let bytes = try plist.encode(saved)
    let decoded = try PropertyListDecoder().decode(ClawNativePlayer.SavedState.self, from: bytes)
    guard decoded == saved else { throw SnapshotPlayerFailure(message: "player archive differs after decoding") }
    let first = try replay()
    try player.restoreState(decoded)
    let restored = try digest()
    guard restored == start else { throw SnapshotPlayerFailure(message: "player owner failed exact restore") }
    let second = try replay()
    guard first == second else {
        throw SnapshotPlayerFailure(message: "player owner diverged at frame \(zip(first, second).enumerated().first(where: { $0.element.0 != $0.element.1 })?.offset ?? -1)")
    }
    player.postCommand(0x803a)
    try player.restoreState(saved)
    guard player.drainPendingCommands() == saved.pendingCommands else { throw SnapshotPlayerFailure(message: "pending command queue not restored") }
    print("{\"check\":\"snapshot-player-owner\",\"status\":\"pass\",\"frames\":600,\"whole_scene\":false}")
    if let audio = player.audio { try verifySnapshotAudioPlayback(audio) }
    try verifySnapshotRemainingServiceValidation(root: root, world: world)
    try verifySnapshotSceneParticipants(root: root, world: world)
}

private func verifySnapshotWindowOwners() throws {
    let queue = ClawNativeWindowInputQueue()
    let input = ClawNativeWindowInput(queue: queue), other = ClawNativeWindowInput(queue: queue)
    input.key(mask: 0x2000000, down: true); input.primary(mask: 0x10, down: true)
    input.menuKey(0x10, down: true); input.menuPointer(message: .mouseMove, x: -5, y: 91)
    _ = input.showCursor(false)
    input.joystickSampler = { .init(x: 42, y: 50000, buttons: 5) }; input.sampleJoystick()
    other.key(mask: 0x20, down: true); try queue.postClose(window: other.window)
    let encoder = PropertyListEncoder()
    let saved = queue.savedState(), inputState = input.savedState(), otherState = other.savedState()
    let decoded = try PropertyListDecoder().decode(ClawNativeWindowInputQueue.SavedState.self, from: encoder.encode(saved))
    let candidate = ClawNativeWindowInputQueue(); try candidate.restoreState(decoded)
    let restored = try ClawNativeWindowInput(restoring: inputState, queue: candidate)
    let restoredOther = try ClawNativeWindowInput(restoring: otherState, queue: candidate)
    guard restored.savedState() == inputState, restoredOther.savedState() == otherState,
          candidate.savedState() == saved, restored.queue === restoredOther.queue,
          restored.frameInput() == input.frameInput(), candidate.pending == queue.pending,
          try candidate.takeCloseRequest(window: restoredOther.window) == queue.takeCloseRequest(window: other.window)
    else { throw SnapshotPlayerFailure(message: "shared window graph differs") }
    let before = candidate.savedState()
    let invalid = ClawNativeWindowInputQueue.SavedState(windows: [], nextWindow: 1, pending: saved.pending, closeRequests: [])
    do { try candidate.restoreState(invalid); throw SnapshotPlayerFailure(message: "input accepted absent window") }
    catch ClawSnapshotError.invalidState { }
    guard candidate.savedState() == before else { throw SnapshotPlayerFailure(message: "invalid input changed queue") }
    print("{\"check\":\"snapshot-window-owners\",\"status\":\"pass\",\"windows\":2,\"whole_scene\":false}")
}

private func verifySnapshotMfcOwner() throws {
    let imports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map {
        ($0.element, UInt32(0x710200 + $0.offset * 4))
    })
    func make(_ host: ClawNativeCanonicalHost) throws -> ClawNativeMfcMemory {
        try ClawNativeMfcMemory(host: host, sha256: ClawNativeMfcMemory.imageHash, importTargets: imports)
    }
    func service(_ memory: ClawNativeMfcMemory, _ function: UInt32, _ arguments: [UInt32]) throws -> UInt32 {
        var call = ClawCall(); call.function = function; call.argumentCount = UInt32(arguments.count)
        call.stackPointer = UInt32(CLAW_STACK_BASE) + 0x100
        withUnsafeMutableBytes(of: &call.arguments) { raw in
            for (index, value) in arguments.enumerated() { raw.bindMemory(to: UInt32.self)[index] = value }
        }
        guard let result = memory.service(call), memory.host.fault == nil else { throw SnapshotPlayerFailure(message: "MFC fixture service \(String(function, radix:16))") }
        return result
    }
    let heap = ClawTokenHeap(), host = ClawNativeCanonicalHost(heap: ClawTokenHeap())
    // The original and candidate must own separate host heaps.
    let originalHost = ClawNativeCanonicalHost(heap: heap), memory = try make(originalHost)
    let manager = try memory.createManager(), owner = try memory.createTLSOwner(), local = try memory.createTLSLocal(count: 37, zero: true)
    _ = heap.store(token: 0x540af0, words: 1); try memory.registerTLSPublication(0x540af0)
    let index = try service(memory, 0x546a90, [])
    _ = try service(memory, 0x546a84, [index, local]); heap.lookup(owner, words: 1)![0] = index
    _ = try service(memory, 0x546aa4, [manager + 0x1c])
    _ = try service(memory, 0x546aac, [manager + 0x1c])
    do { _ = try memory.savedState(); throw SnapshotPlayerFailure(message: "MFC captured held lock") }
    catch ClawSnapshotError.activeFrame { }
    _ = try service(memory, 0x546a9c, [manager + 0x1c])
    let block = try service(memory, 0x546b1c, [2, 29])
    _ = try service(memory, 0x546ac0, [block])
    let stale = try memory.createManager()
    heap.free(stale); heap.store(token: stale, words: 13)[0] = 0xaabbccdd
    let saved = try memory.savedState(), image = try heap.checkpoint().image
    let encoder = PropertyListEncoder(); encoder.outputFormat = .binary
    let decoded = try PropertyListDecoder().decode(ClawNativeMfcMemory.SavedState.self, from: encoder.encode(saved))
    let candidate = try make(host), plan = try host.heap.prepareRestore(image)
    let apply = try candidate.prepareRestore(decoded, heap: plan)
    try host.heap.restore(plan); try apply()
    guard try candidate.savedState() == saved, candidate.tlsValue(index) == local,
          candidate.ownsTLSOwner(owner), candidate.ownsSourceLocal(local, count: 37),
          !candidate.ownsSourceManager(stale), host.heap.lookup(stale, words: 1)?[0] == 0xaabbccdd
    else { throw SnapshotPlayerFailure(message: "MFC owner/TLS/tombstone roundtrip differs") }
    let originalNext = try memory.createTLSLocal(count: 15, zero: false)
    let restoredNext = try candidate.createTLSLocal(count: 15, zero: false)
    // New allocations deliberately have fresh process-local witness UUIDs.
    // Compare the source ledger's ordinal identities and bytes for continuation.
    guard originalNext == restoredNext,
          candidate.localRequestedSizes == memory.localRequestedSizes,
          candidate.logicalTLSValues == memory.logicalTLSValues,
          candidate.tlsSnapshot() == memory.tlsSnapshot()
    else { throw SnapshotPlayerFailure(message: "MFC allocation cursor continuation differs") }
    print("{\"check\":\"snapshot-mfc-owner\",\"status\":\"pass\",\"retired_and_reused\":true,\"whole_scene\":false}")
}

private func verifySnapshotAudioPlayback(_ audio: ClawNativeAudio) throws {
    guard audio.resolve(name: "GAME_BOINKJR") != nil else { throw SnapshotPlayerFailure(message: "missing audio fixture") }
    _ = audio.play(name: "GAME_BOINKJR", request: ClawAudioRequest(volume: 80, pan: 0, pitchPercent: 100, looping: 1))
    func render(_ count: Int) -> [[Float]] {
        var left = [Float](repeating: 0, count: count), right = left
        left.withUnsafeMutableBufferPointer { l in
            right.withUnsafeMutableBufferPointer { r in audio.render(left: l.baseAddress!, right: r.baseAddress!, frames: count, sampleRate: 44100) }
        }
        return [left, right]
    }
    _ = render(256)
    let saved = try audio.savedPlaybackState()
    guard saved.voices.contains(where: \.playing) else { throw SnapshotPlayerFailure(message: "audio fixture did not play") }
    let encoder = PropertyListEncoder(); encoder.outputFormat = .binary
    let decoded = try PropertyListDecoder().decode(ClawNativeAudio.PlaybackSavedState.self, from: encoder.encode(saved))
    let first = render(4096)
    audio.routing.masterVolume = 17
    try audio.restorePlaybackState(decoded)
    guard try audio.savedPlaybackState() == saved else { throw SnapshotPlayerFailure(message: "audio playback roundtrip differs") }
    let second = render(4096)
    guard first == second, first.flatMap({ $0 }).contains(where: { $0 != 0 })
    else { throw SnapshotPlayerFailure(message: "offline PCM replay differs or is silent") }
    // The native mixer rewinds completed non-looping voices to cursor zero.
    // Preserve that completed state as well as active loop positions.
    audio.stopAll()
    _ = audio.play(name: "GAME_BOINKJR", request: ClawAudioRequest(volume: 80, pan: 0, pitchPercent: 137, looping: 0))
    let started = try audio.savedPlaybackState().voices.filter(\.playing).map(\.token)
    guard !started.isEmpty else { throw SnapshotPlayerFailure(message: "non-looping audio fixture did not play") }
    _ = render(100000)
    let ended = try audio.savedPlaybackState()
    guard started.allSatisfy({ token in
        ended.voices.contains(where: { $0.token == token && !$0.playing && Double(bitPattern: $0.cursorBits) == 0 })
    })
    else { throw SnapshotPlayerFailure(message: "non-looping voice did not finish and rewind") }
    try audio.restorePlaybackState(ended)
    guard try audio.savedPlaybackState() == ended else { throw SnapshotPlayerFailure(message: "completed voice cursor changed") }
    try verifySnapshotAudioOwner(audio)
    print("{\"check\":\"snapshot-audio-playback\",\"status\":\"pass\",\"pcm_frames\":4096,\"speakers\":false}")
}

private func verifySnapshotAudioOwner(_ audio: ClawNativeAudio) throws {
    let request = ClawAudioRequest(volume: 77, pan: 13, pitchPercent: 97, looping: 1)
    _ = audio.play(name: "GAME_BOINKJR", request: request)
    _ = audio.play(name: "GAME_BOINKJR", request: request)
    let saved = try audio.savedState()
    // The player passes its shared heap to audio. Its allocation image is
    // captured by the dedicated resource/owner process check below.
    let root = URL(fileURLWithPath: CommandLine.arguments[1])
    let sourceHeap = ClawTokenHeap()
    let source = try ClawNativeAudio(root: root, outputEnabled: false, sharedHeap: sourceHeap)
    _ = source.play(name: "GAME_BOINKJR", request: request)
    _ = source.play(name: "GAME_BOINKJR", request: request)
    let encoder = PropertyListEncoder(); encoder.outputFormat = .binary
    let state = try source.savedState()
    let decoded = try PropertyListDecoder().decode(ClawNativeAudio.SavedState.self, from: encoder.encode(state))
    let image = try sourceHeap.checkpoint().image
    let heap = ClawTokenHeap()
    let candidate = try ClawNativeAudio(root: root, outputEnabled: false, sharedHeap: heap, preload: false)
    let plan = try heap.prepareRestore(image)
    let apply = try candidate.prepareRestore(decoded, heap: plan)
    // Abandoning a prepared candidate must not free any source or candidate
    // storage. Prepared sample destructors remain disarmed until installation.
    do { let abandoned = try candidate.prepareRestore(decoded, heap: plan); _ = abandoned }
    try heap.restore(plan); try apply()
    guard try candidate.savedState() == state, state.playback.voices.count >= 2, !saved.samples.isEmpty,
          candidate.resolve(name: "GAME_BOINKJR")?.resourceToken == source.resolve(name: "GAME_BOINKJR")?.resourceToken
    else { throw SnapshotPlayerFailure(message: "full audio owner topology differs") }
    func render(_ owner: ClawNativeAudio) -> [[Float]] {
        var left = [Float](repeating: 0, count: 4096), right = left
        left.withUnsafeMutableBufferPointer { l in right.withUnsafeMutableBufferPointer { r in
            owner.render(left: l.baseAddress!, right: r.baseAddress!, frames: 4096, sampleRate: 44100)
        } }
        return [left, right]
    }
    let first = render(source), second = render(candidate)
    guard first == second, first.flatMap({ $0 }).contains(where: { $0 != 0 }),
          try source.savedState() == candidate.savedState() else { throw SnapshotPlayerFailure(message: "relocated audio PCM continuation differs") }
    print("{\"check\":\"snapshot-audio-owner\",\"status\":\"pass\",\"pcm_frames\":4096,\"voices\":\(state.playback.voices.count),\"whole_scene\":false}")
}

private func verifySnapshotSceneParticipants(root: URL, world: ClawLevelScene) throws {
    var now: UInt32 = 1000, probeActiveFrame = false, rejectedActiveFrame = false, rejectedServiceFrame = false
    weak var current: ClawNativeScene?
    let player = try ClawNativePlayer(world: world.world, assets: ClawPlayerAssets(root: root))
    let scene = ClawNativeScene(player: player, clock: {
        if probeActiveFrame, let current {
            do { _ = try current.savedSchedulerState() }
            catch ClawSnapshotError.activeFrame { rejectedActiveFrame = true }
            catch { }
            do { _ = try current.savedRemainingServicesState() }
            catch ClawSnapshotError.activeFrame { rejectedServiceFrame = true }
            catch { }
        }
        return now
    })
    current = scene
    let saves = URL(fileURLWithPath: "work/snapshot-check/scene-saves", isDirectory: true)
    try scene.loadRecoveredObjects(world: world.world, root: root, saveDirectory: saves)
    now += 17; probeActiveFrame = true
    scene.advance(now: now, delta: 17, accumulated: 17, held: 0, pressed: 0)
    probeActiveFrame = false
    guard scene.fault == 0, rejectedActiveFrame, rejectedServiceFrame, let camera = scene.camera, let frame = scene.frameRuntime
    else { throw SnapshotPlayerFailure(message: "scene participant setup/frame-boundary rejection failed: \(scene.fault)") }
    let encoder = PropertyListEncoder(); encoder.outputFormat = .binary
    let decoder = PropertyListDecoder()
    let scheduler = try decoder.decode(ClawNativeScene.SchedulerSavedState.self, from: encoder.encode(scene.savedSchedulerState()))
    let cameraState = try decoder.decode(ClawNativeCamera.SavedState.self, from: encoder.encode(camera.savedState()))
    let frameState = try decoder.decode(ClawNativeFrame.SavedState.self, from: encoder.encode(frame.savedState()))
    now += 17
    scene.advance(now: now, delta: 17, accumulated: 34, held: 0x02000000, pressed: 0x02000000)
    guard scene.fault == 0 else { throw SnapshotPlayerFailure(message: "scene participant mutation frame fault") }
    try scene.restoreSchedulerState(scheduler); try camera.restoreState(cameraState); frame.restoreState(frameState)
    let restoredScheduler = try scene.savedSchedulerState()
    guard restoredScheduler == scheduler, camera.savedState() == cameraState, frame.savedState() == frameState
    else { throw SnapshotPlayerFailure(message: "scheduler/camera/frame participant roundtrip differs") }
    guard let connections = scene.objectConnections else { throw SnapshotPlayerFailure(message: "missing connection participant") }
    try verifySnapshotResourceOwners(root: root, scene: scene)
    let ownership = try connections.savedOwnershipState()
    let decodedOwnership = try decoder.decode(ClawNativeObjectConnections.OwnershipSavedState.self, from: encoder.encode(ownership))
    let heapPlan = try scene.heap.prepareRestore(scene.heap.checkpoint())
    let applyOwnership = try connections.prepareOwnershipRestore(decodedOwnership, heap: heapPlan)
    try applyOwnership()
    guard try connections.savedOwnershipState() == ownership else { throw SnapshotPlayerFailure(message: "dispatch ownership roundtrip differs") }
    // Do not run another frame over this intentionally partial restoration.
    // Adapter and resource-owner restore is the remaining scene integration.
    print("{\"check\":\"snapshot-scene-participants\",\"status\":\"pass\",\"whole_scene\":false}")
}

private func verifySnapshotResourceOwners(root: URL, scene: ClawNativeScene) throws {
    guard let resources = scene.objectResources else { throw SnapshotPlayerFailure(message: "missing resource owner") }
    let encoder = PropertyListEncoder(); encoder.outputFormat = .binary
    let saved = try resources.savedState()
    let decoded = try PropertyListDecoder().decode(ClawActorResources.SavedState.self, from: encoder.encode(saved))
    let heapImage = try scene.heap.checkpoint().image
    let heap = ClawTokenHeap()
    let candidate = try ClawActorResources(root: root, heap: heap, level: saved.level)
    let plan = try heap.prepareRestore(heapImage)
    let apply = try candidate.prepareRestore(decoded, heap: plan)
    // Apply must reject until the corresponding candidate heap is installed.
    do { try apply(); throw SnapshotPlayerFailure(message: "resource owner accepted uninstalled heap") }
    catch ClawTokenHeap.SnapshotError.stalePlan { }
    try heap.restore(plan); try apply()
    guard try candidate.savedState() == saved else { throw SnapshotPlayerFailure(message: "resource manifest differs") }
    for record in saved.images {
        guard let original = resources.images(token: record.manager.token),
              let restored = candidate.images(token: record.manager.token),
              original.binding().images != restored.binding().images,
              restored.binding().images == UnsafePointer(heap.lookup(record.array.token, words: record.array.count / 4)),
              Array(UnsafeBufferPointer(start: restored.binding().images, count: record.table.count)) == record.table
        else { throw SnapshotPlayerFailure(message: "image binding did not relocate") }
        for token in record.identities.values {
            if let header = heap.lookup(token, words: 13), header[11] != 0 {
                guard candidate.graphicsFrame(surfaceToken: header[11]) != nil else { throw SnapshotPlayerFailure(message: "missing relocated surface") }
            }
        }
    }
    guard !saved.images.isEmpty, !saved.sequences.isEmpty else { throw SnapshotPlayerFailure(message: "empty resource fixture") }
    let bad = ClawActorResources.SavedState(level: saved.level == 1 ? 2 : 1, paletteHash: saved.paletteHash,
                                           images: saved.images, sequences: saved.sequences, surfaces: saved.surfaces)
    let rejectedPlan = try heap.prepareRestore(heapImage)
    do { _ = try candidate.prepareRestore(bad, heap: rejectedPlan); throw SnapshotPlayerFailure(message: "resource owner accepted wrong level") }
    catch ClawSnapshotError.invalidState { }
    guard try candidate.savedState() == saved else { throw SnapshotPlayerFailure(message: "rejected resource restore mutated owner") }
    let header = saved.images[0].headers.values.first!
    heap.free(header.token); heap.store(token: header.token, words: 16)[0] = 0xfeedface
    do { _ = try candidate.savedState(); throw SnapshotPlayerFailure(message: "resource cache accepted replaced image allocation") }
    catch ClawSnapshotError.invalidState { }
    print("{\"check\":\"snapshot-resource-owners\",\"status\":\"pass\",\"image_sets\":\(saved.images.count),\"sequences\":\(saved.sequences.count),\"whole_scene\":false}")
}

// Dynamic actor graph proof only. No restored scene is advanced/rendered here:
// services/adapters/canonical bindings remain separate scene participants.
func verifySnapshotDynamicActors(root: URL, directory: URL, relaunch: Bool) throws {
    let build = try ClawSnapshotSlots.executableBuildIdentifier(URL(fileURLWithPath: CommandLine.arguments[0]))
    let ownerKeys: Set<String> = ["actors", "resources", "audio", "player", "random", "scheduler", "rendering", "player.services", "respawn", "object.services", "remaining.services"]
    for level: UInt32 in [1, 2] {
        let world = try ClawLevelScene(root: root, level: level)
        func make() throws -> ClawNativeScene {
            let player = try ClawNativePlayer(world: world.world, assets: ClawPlayerAssets(root: root, level: level), level: level)
            let scene = ClawNativeScene(player: player, clock: { 1000 })
            try scene.loadRecoveredObjects(world: world.world, root: root, level: level)
            return scene
        }
        let location = directory.appendingPathComponent("level-\(level)")
        let slots = ClawSnapshotSlots(directory: location, build: build)
        let original: ClawNativeScene?
        if !relaunch {
            let scene = try make()
            scene.advance(now: 1017, delta: 17, accumulated: 17, held: 0, pressed: 0)
            print("snapshot actor initial frame Level", level, "fault", scene.fault, "enemies", scene.enemies.count, "humanoids", scene.humanoids.count)
            guard scene.fault == 0, let resources = scene.objectResources, let audio = scene.player.audio,
                  !scene.humanoids.isEmpty else { throw SnapshotPlayerFailure(message: "actor graph initial frame Level \(level)") }
            // A real source-created RatBomb and Bullet did not exist in the seed
            // graph. Their owners must be constructed, not matched by census.
            guard let bomb = try scene.createBomb(x: 1000, y: 500, z: 10, flags: 0) else { throw SnapshotPlayerFailure(message: "dynamic bomb creation") }
            bomb.tick()
            guard let soldier = scene.humanoids.values.sorted(by: { $0.token < $1.token }).first(where: { $0.kind == .soldier })
            else { throw SnapshotPlayerFailure(message: "missing source Soldier") }
            var create = ClawGenericEnemyCall(); create.function = 0x4c8da0; create.argumentCount = 6
            create.arguments.1 = 1100; create.arguments.2 = 500; create.arguments.3 = 10; create.arguments.4 = 0x522e0c
            let token = UInt32(truncatingIfNeeded: soldier.dependency(create))
            guard let bullet = scene.bullets[token] else { throw SnapshotPlayerFailure(message: "dynamic bullet creation") }
            bullet.tick()
            // Populate the remaining service graph through the actual creators.
            // This stays a component proof until adapters and scene replacement
            // join the transaction; do not call scene.advance after partial restore.
            try populateSnapshotServiceActors(scene)
            print("snapshot elected owners Level", level, Dictionary(grouping: try scene.objectConnections!.savedOwnershipState().owners, by: \.family).mapValues(\.count))
            // Keep tombstones in the native dictionaries while replacing their
            // token storage. They must remain stale after disk reconstruction.
            let retiredBomb = try scene.createBomb(x: 2000, y: 500, z: 10, flags: 0)!
            scene.heap.free(retiredBomb.token); scene.heap.store(token: retiredBomb.token, words: 128)[0] = 0xf00dcafe
            ClawNativeHumanoidGlobals.shared(scene).clockCountdown = 31
            scene.playerPowerupGlobals!.pointee.powerup = 3
            scene.playerPowerupGlobals!.pointee.remaining = 12345
            print("snapshot actor capture Level", level, "enemies", scene.enemies.count, "humanoids", scene.humanoids.count, "bullets", scene.bullets.count)
            for token in scene.enemies.keys.sorted() {
                do { _ = try scene.enemies[token]!.savedState() }
                catch { throw SnapshotPlayerFailure(message: "capture enemy \(String(token, radix: 16)): \(error)") }
            }
            for token in scene.humanoids.keys.sorted() {
                do { _ = try scene.humanoids[token]!.savedState() }
                catch { throw SnapshotPlayerFailure(message: "capture humanoid \(String(token, radix: 16)): \(error)") }
            }
            for token in scene.bullets.keys.sorted() {
                do { _ = try scene.bullets[token]!.savedState() }
                catch { throw SnapshotPlayerFailure(message: "capture bullet \(String(token, radix: 16)): \(error)") }
            }
            let image = ClawSnapshotImage(build: build, level: level, heap: try scene.heap.checkpoint().image, owners: [
                "actors": try ClawSnapshotOwnerDecoder.encode(scene.savedDynamicActorsState()),
                "resources": try ClawSnapshotOwnerDecoder.encode(resources.savedState()),
                "audio": try ClawSnapshotOwnerDecoder.encode(audio.savedState()),
                "player": try ClawSnapshotOwnerDecoder.encode(scene.player.savedState()),
                "random": try ClawSnapshotOwnerDecoder.encode(scene.random.savedState()),
                "scheduler": try ClawSnapshotOwnerDecoder.encode(scene.savedSchedulerState()),
                "rendering": try ClawSnapshotOwnerDecoder.encode(scene.rendering!.savedState()),
                "player.services": try ClawSnapshotOwnerDecoder.encode(scene.savedPlayerServicesState()),
                "respawn": try ClawSnapshotOwnerDecoder.encode(scene.respawn!.savedState()),
                "object.services": try ClawSnapshotOwnerDecoder.encode(scene.savedObjectServicesState()),
                "remaining.services": try ClawSnapshotOwnerDecoder.encode(scene.savedRemainingServicesState())
            ])
            try slots.save(image, to: .quick); original = scene
        } else { original = nil }
        let image = try ClawSnapshotSlots(directory: location, build: build).load(.quick)
        var decoder = try ClawSnapshotOwnerDecoder(image.owners, requiring: ownerKeys)
        let actors = try decoder.decode(ClawNativeScene.DynamicActorsSavedState.self, key: "actors")
        let resources = try decoder.decode(ClawActorResources.SavedState.self, key: "resources")
        let audio = try decoder.decode(ClawNativeAudio.SavedState.self, key: "audio")
        let player = try decoder.decode(ClawNativePlayer.SavedState.self, key: "player")
        let random = try decoder.decode(ClawNativeRandom.SavedState.self, key: "random")
        let scheduler = try decoder.decode(ClawNativeScene.SchedulerSavedState.self, key: "scheduler")
        let rendering = try decoder.decode(ClawNativeRendering.SavedState.self, key: "rendering")
        let playerServices = try decoder.decode(ClawNativePlayerServices.SavedState.self, key: "player.services")
        let respawn = try decoder.decode(ClawNativeRespawn.SavedState.self, key: "respawn")
        let objectServices = try decoder.decode(ClawNativeScene.ObjectServicesSavedState.self, key: "object.services")
        let remainingServices = try decoder.decode(ClawNativeScene.RemainingServicesSavedState.self, key: "remaining.services")
        try decoder.finish()
        let candidate = try make(), plan = try candidate.heap.prepareRestore(image.heap)
        print("snapshot actor prepare Level", level)
        let installAudio = try candidate.player.audio!.prepareRestore(audio, heap: plan)
        let installResources = try candidate.objectResources!.prepareRestore(resources, heap: plan)
        let installRendering = try candidate.rendering!.prepareRestore(rendering, heap: plan)
        let installActors = try candidate.reconstructDynamicActors(actors, heap: plan)
        let installRemaining = try candidate.prepareRemainingServicesRestore(remainingServices, heap: plan)
        do { try installRemaining(); throw SnapshotPlayerFailure(message: "service graph accepted uninstalled heap") }
        catch ClawTokenHeap.SnapshotError.stalePlan { }
        print("snapshot actor prepared Level", level)
        // These candidate owners must not capture source-scene closures or its
        // generic/state/resource buffers, even when tokens happen to be equal.
        if let original, let first = actors.humanoids.first {
            guard original.humanoids[first.service.token]!.generic != candidate.humanoids[first.service.token]!.generic
            else { throw SnapshotPlayerFailure(message: "actor context did not relocate") }
        }
        try candidate.heap.restore(plan); try installAudio(); try installResources(); try installActors(); try installRendering()
        try candidate.player.restoreState(player); try candidate.random.restoreState(random); try candidate.restoreSchedulerState(scheduler)
        try candidate.restorePlayerServicesState(playerServices); try candidate.respawn!.restoreState(respawn)
        try candidate.restoreObjectServicesState(objectServices); try installRemaining()
        let restoredServices = try candidate.savedRemainingServicesState()
        guard restoredServices == remainingServices else {
            let differences = ["loot": restoredServices.loot == remainingServices.loot, "effects": restoredServices.effects == remainingServices.effects,
                "breakables": restoredServices.breakables == remainingServices.breakables, "projectiles": restoredServices.projectiles == remainingServices.projectiles,
                "flares": restoredServices.flares == remainingServices.flares, "special": restoredServices.special == remainingServices.special,
                "save": restoredServices.save == remainingServices.save, "status": restoredServices.status == remainingServices.status,
                "palette": restoredServices.palettes == remainingServices.palettes, "light": restoredServices.light == remainingServices.light]
            throw SnapshotPlayerFailure(message: "remaining native service graph differs: \(differences.filter { !$0.value }.keys.sorted())")
        }
        guard try candidate.savedObjectServicesState() == objectServices,
              try candidate.savedPlayerServicesState() == playerServices, try candidate.respawn!.savedState() == respawn,
              candidate.playerPowerupGlobals!.pointee.remaining == 12345,
              candidate.rendering!.commands.count == rendering.commands.count,
              candidate.rendering!.indexedSnapshot == Data(image.heap.allocations.first(where: { $0.token == rendering.indexed.token })!.bytes.prefix(640 * 480))
        else { throw SnapshotPlayerFailure(message: "renderer/player-service/respawn candidate differs") }
        guard try candidate.savedDynamicActorsState() == actors else { throw SnapshotPlayerFailure(message: "actor graph roundtrip Level \(level)") }
        for body in actors.humanoids {
            for token in body.bullets {
                guard candidate.humanoids[body.service.token]!.bullets[token.token] === candidate.bullets[token.token]
                else { throw SnapshotPlayerFailure(message: "humanoid and scene copied their shared bullet") }
            }
        }
        let retired = actors.enemies.first(where: { !$0.actor.live })!
        candidate.enemies[retired.token]!.tick()
        guard candidate.enemies[retired.token]!.failure == "Retired enemy owner", candidate.heap.lookup(retired.token, words: 1)![0] == 0xf00dcafe
        else { throw SnapshotPlayerFailure(message: "retired enemy wrote replacement token") }
        original?.enemies[retired.token]!.tick()
        let continuation = try snapshotActorContinuation(candidate)
        let expectedFile = location.appendingPathComponent("actor-continuation.plist")
        if let original {
            let expected = try snapshotActorContinuation(original)
            guard expected == continuation else {
                let first = zip(expected, continuation).enumerated().first(where: { $0.element.0 != $0.element.1 })?.offset ?? -1
                throw SnapshotPlayerFailure(message: "actor continuation Level \(level) step \(first)")
            }
            try ClawSnapshotOwnerDecoder.encode(expected).write(to: expectedFile, options: .atomic)
        } else {
            let expected = try PropertyListDecoder().decode([String].self, from: Data(contentsOf: expectedFile))
            guard expected == continuation else { throw SnapshotPlayerFailure(message: "second-process actor continuation Level \(level)") }
        }
        print("{\"check\":\"snapshot-dynamic-actors\",\"status\":\"pass\",\"level\":\(level),\"second_process\":\(relaunch),\"steps\":\(continuation.count),\"enemies\":\(actors.enemies.count),\"humanoids\":\(actors.humanoids.count),\"bullets\":\(actors.bullets.count),\"retired_and_reused\":true,\"whole_scene\":false}")
    }
}

private func snapshotActorContinuation(_ scene: ClawNativeScene) throws -> [String] {
    var hashes: [String] = []
    // This is a component driver, not the recovered camera/culling scheduler.
    // Exercise one placed Rat/Officer/Soldier and every spawned projectile;
    // forcing all dormant WWD enemies to move is neither a game frame nor a
    // useful cost for the actor transport proof. All owner state is hashed.
    let rat = scene.enemies.keys.sorted().first { scene.enemies[$0]!.kind == .rat }
    let humans = [ClawNativeHumanoid.Kind.officer, .soldier].compactMap { kind in
        scene.humanoids.keys.sorted().first { scene.humanoids[$0]!.kind == kind }
    }
    for step in 0..<600 {
        let hash = try autoreleasepool { () throws -> String in
        scene.publishGameTime(34 + UInt32(step) * 17)
        for token in scene.enemies.keys.sorted() {
            let body = scene.enemies[token]!
            if body.failure == "Retired enemy owner" { continue }
            guard token == rat || body.kind == .bomb else { continue }
            body.tick()
            guard body.failure == nil, body.unresolved.isEmpty else { throw SnapshotPlayerFailure(message: "enemy continuation \(body.failure ?? "") \(body.unresolved)") }
        }
        for token in humans {
            let body = scene.humanoids[token]!; body.tick()
            guard body.failure == nil, body.unresolved.isEmpty else { throw SnapshotPlayerFailure(message: "humanoid continuation \(body.failure ?? "") \(body.unresolved)") }
        }
        try advanceSnapshotServiceActors(scene, step: step)
        for token in scene.bullets.keys.sorted() {
            let body = scene.bullets[token]!; body.tick()
            guard body.failure == nil, body.unresolved.isEmpty else { throw SnapshotPlayerFailure(message: "bullet continuation \(body.failure ?? "") \(body.unresolved)") }
        }
        var digest = SHA256()
        let image = try scene.heap.snapshotTopology()
        var semantic = SnapshotSemanticState(heap: image)
        digest.update(data: try semantic.bytes(scene.savedDynamicActorsState()))
        digest.update(data: try semantic.bytes(scene.savedRemainingServicesState()))
        var next = image.nextToken.littleEndian
        withUnsafeBytes(of: &next) { digest.update(data: $0) }
        for allocation in image.allocations {
            var token = allocation.token.littleEndian, count = allocation.byteCount.littleEndian
            withUnsafeBytes(of: &token) { digest.update(data: $0) }; withUnsafeBytes(of: &count) { digest.update(data: $0) }
            guard let bytes = scene.heap.lookupBytes(allocation.token, count: allocation.byteCount) else { throw SnapshotPlayerFailure(message: "continuation allocation disappeared") }
            digest.update(bufferPointer: UnsafeRawBufferPointer(start: bytes, count: Int(allocation.byteCount)))
        }
        return digest.finalize().map { String(format: "%02x", $0) }.joined()
        }
        hashes.append(hash)
    }
    return hashes
}

private func populateSnapshotServiceActors(_ scene: ClawNativeScene) throws {
    guard let loot = scene.loot, let effects = scene.effects, let projectiles = scene.projectiles,
          let breakables = scene.breakables else { throw SnapshotPlayerFailure(message: "missing remaining services") }
    var create = ClawWorldLootCall(); create.function = 0x4c8da0; create.receiver = scene.containerToken; create.argumentCount = 6
    create.arguments.1 = 1000; create.arguments.2 = 500; create.arguments.3 = 10; create.arguments.4 = 0x522cc0
    let goodie = loot.sourceService(create)
    guard let body = loot.goodies[goodie] else { throw SnapshotPlayerFailure(message: "snapshot Goodie creation") }
    guard try loot.bindImage(goodie, name: "GAME_TREASURE_COINS") != 0 else { throw SnapshotPlayerFailure(message: "snapshot Goodie image binding") }
    body.tick()
    guard body.failure == nil else { throw SnapshotPlayerFailure(message: "snapshot Goodie initialization \(body.failure ?? "")") }
    guard effects.impactEntry(0x461a00, arguments: [scene.sceneIdentity, 1000, 500, 9000, 0, 0x10002000]) == 1,
          let effect = effects.actors.values.sorted(by: { $0.token < $1.token }).first else { throw SnapshotPlayerFailure(message: "snapshot effect creation") }
    effect.tick()
    let projectile = projectiles.create("PistolBullet", x: 1000, y: 500, z: 10, flags: 0)
    projectiles.callback(0x40ff80, actor: projectile)
    guard projectile != 0, projectiles.fault == 0 else { throw SnapshotPlayerFailure(message: "snapshot player projectile initialization") }
    if let record = breakables.originalRecords.values.sorted(by: { $0.token < $1.token }).first(where: { $0.primary.4 == 0x46f1e0 }) {
        _ = breakables.callback(record.primary.4, actor: record.token)
    }
    guard breakables.fault == 0, !breakables.bodies.isEmpty else { throw SnapshotPlayerFailure(message: "snapshot breakable initialization") }
    // A raw wrapper must keep the retired allocation witness even though the
    // token now names a new allocation. These wrappers remain in the archive.
    for token in [effect.token, goodie] { scene.heap.free(token); scene.heap.store(token: token, words: 128)[0] = 0xf00dcafe }
    guard effect.callback(0x461a90) == 0 else { throw SnapshotPlayerFailure(message: "stale effect remained callable") }
    body.tick()
    guard body.failure == "Retired goodie owner" else { throw SnapshotPlayerFailure(message: "stale Goodie remained callable") }
    if let pickup = loot.pickups.keys.sorted().first {
        scene.heap.free(pickup); scene.heap.store(token: pickup, words: 128)[0] = 0xf00dcafe
        guard loot.pickups[pickup]!.callback(0x46fd10) == 0, loot.pickups[pickup]!.failure == "Retired pickup owner" else { throw SnapshotPlayerFailure(message: "stale pickup remained callable") }
    }
}

private func advanceSnapshotServiceActors(_ scene: ClawNativeScene, step: Int) throws {
    guard let loot = scene.loot, let effects = scene.effects, let projectiles = scene.projectiles, let flares = scene.flares else { throw SnapshotPlayerFailure(message: "missing continuation services") }
    if step == 60 {
        guard effects.impactEntry(0x461a00, arguments: [scene.sceneIdentity, 1000, 500, 9000, 0, 0x10002000]) == 1 else { throw SnapshotPlayerFailure(message: "continued effect creation") }
    }
    for token in loot.goodies.keys.sorted() {
        let body = loot.goodies[token]!
        if !body.ownsActor { body.tick(); guard body.failure == "Retired goodie owner", scene.heap.lookup(token, words: 1)![0] == 0xf00dcafe else { throw SnapshotPlayerFailure(message: "restored stale Goodie rebound") }; continue }
        body.tick(); guard body.failure == nil else { throw SnapshotPlayerFailure(message: "Goodie continuation") }
    }
    for token in loot.pickups.keys.sorted() where !loot.pickups[token]!.ownsActor {
        guard loot.pickups[token]!.callback(0x46fd10) == 0, scene.heap.lookup(token, words: 1)![0] == 0xf00dcafe else { throw SnapshotPlayerFailure(message: "restored stale pickup rebound") }
    }
    for token in effects.actors.keys.sorted() { effects.actors[token]?.tick() }
    for token in projectiles.tokens.sorted() {
        guard let actor = scene.snapshotActor(token) else { continue };projectiles.callback(actor.primary.4, actor: token)
    }
    for token in flares.tokens.sorted() {
        guard let actor = scene.snapshotActor(token) else { continue };flares.callback(actor.primary.4, actor: token)
    }
    guard effects.fault == 0, projectiles.fault == 0, flares.fault == 0 else { throw SnapshotPlayerFailure(message: "native service continuation fault \(effects.fault)/\(projectiles.fault)/\(flares.fault)") }
}

// The archive's Set/Dictionary encoding order is not semantic state. Sort those
// containers while keeping array/list order, and map allocation UUIDs to stable
// live token order plus deterministic retired-witness discovery order.
struct SnapshotSemanticState {
    private var witnesses: [UUID: String]
    init(heap: (nextToken: UInt32, allocations: [ClawTokenHeap.AllocationTopology])) {
        witnesses = Dictionary(uniqueKeysWithValues: heap.allocations.enumerated().map { ($0.element.identity, "live-\($0.offset)") })
    }
    mutating func bytes(_ value: Any) throws -> Data { Data(try encode(value).utf8) }
    private mutating func encode(_ value: Any) throws -> String {
        if let uuid = value as? UUID {
            if witnesses[uuid] == nil { witnesses[uuid] = "retired-\(witnesses.count)" }
            return witnesses[uuid]!
        }
        if let data = value as? Data { return "data:" + data.base64EncodedString() }
        if let text = value as? String { return "s\(text.utf8.count):" + text }
        let mirror = Mirror(reflecting: value)
        if mirror.displayStyle == .dictionary {
            let entries = mirror.children.map { child -> (String, Any) in
                let pair = Array(Mirror(reflecting: child.value).children)
                return (String(describing: pair[0].value), pair[1].value)
            }.sorted { $0.0 < $1.0 }
            var result = "map["
            for (key, item) in entries { result += try encode(key) + encode(item) + ";" }
            return result + "]"
        }
        if mirror.displayStyle == .set {
            // Witnesses are never set elements in these schemas. Preexisting
            // stable owner keys use deterministic token + allocation ordering.
            let ordered = mirror.children.map(\.value).sorted { String(describing: $0) < String(describing: $1) }
            var parts: [String] = [];for item in ordered { parts.append(try encode(item)) }
            return "set[" + parts.sorted().joined(separator: ";") + "]"
        }
        if mirror.children.isEmpty { return String(reflecting: value) }
        var result = String(describing: mirror.displayStyle) + "["
        for child in mirror.children { result += (child.label ?? "_") + ":" + (try encode(child.value)) + ";" }
        return result + "]"
    }
}

private func verifySnapshotRemainingServiceValidation(root: URL, world: ClawLevelScene) throws {
    func make() throws -> ClawNativeScene {
        let player = try ClawNativePlayer(world: world.world, assets: ClawPlayerAssets(root: root))
        let scene = ClawNativeScene(player: player, clock: { 1000 })
        try scene.loadRecoveredObjects(world: world.world, root: root)
        return scene
    }
    let source = try make(), saved = try source.savedRemainingServicesState()
    let image = try source.heap.checkpoint().image, candidate = try make()
    let plan = try candidate.heap.prepareRestore(image)
    let install = try candidate.prepareRemainingServicesRestore(saved, heap: plan)
    do { try install(); throw SnapshotPlayerFailure(message: "services accepted uninstalled heap") }
    catch ClawTokenHeap.SnapshotError.stalePlan { }
    try candidate.heap.restore(plan); try install()
    guard try candidate.savedRemainingServicesState() == saved,
          try candidate.heap.checkpoint().image == image else { throw SnapshotPlayerFailure(message: "service validation roundtrip changed heap/owners") }
    let light = saved.light
    let wrongLevel = ClawNativeLightPalette.SavedState(level: 2, owner: light.owner, application: light.application,
        manager: light.manager, context: light.context, resources: light.resources, data: light.data, auxiliary: light.auxiliary,
        fault: light.fault, unresolved: light.unresolved, calls: light.calls)
    do { try candidate.palettes!.restoreState(wrongLevel); throw SnapshotPlayerFailure(message: "light palette accepted wrong world") }
    catch ClawSnapshotError.invalidState { }
    guard try candidate.savedRemainingServicesState() == saved else { throw SnapshotPlayerFailure(message: "rejected service restore mutated candidate") }
    // No frame is run over this partial transaction. The adapter/world/host
    // participants are required before a scene can be published and advanced.
    print("{\"check\":\"snapshot-native-services-validation\",\"status\":\"pass\",\"owners\":10,\"whole_scene\":false}")
}
