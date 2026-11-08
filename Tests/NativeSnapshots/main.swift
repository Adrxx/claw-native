import Foundation
import CryptoKit

struct CheckFailure: Error { let message: String }
func require(_ value: @autoclosure () throws -> Bool, _ message: String) throws {
    if try !value() { throw CheckFailure(message: message) }
}
func rejects(_ message: String, _ body: () throws -> Void) throws {
    do { try body() } catch { return }
    throw CheckFailure(message: "accepted " + message)
}
func heapDigest(_ heap: ClawTokenHeap) throws -> String {
    let image = try heap.checkpoint().image
    var digest = SHA256()
    var cursor = image.nextToken.littleEndian
    withUnsafeBytes(of: &cursor) { digest.update(data: $0) }
    for allocation in image.allocations {
        var token = allocation.token.littleEndian, count = allocation.byteCount.littleEndian
        withUnsafeBytes(of: &token) { digest.update(data: $0) }
        withUnsafeBytes(of: &count) { digest.update(data: $0) }
        digest.update(data: allocation.bytes)
    }
    return digest.finalize().map { String(format: "%02x", $0) }.joined()
}
func heapChecks() throws {
    let heap = ClawTokenHeap()
    heap.storeBytes(token: 0x1000, count: 5)[4] = 97
    // Word padding is part of the source transport and must survive too.
    heap.lookup(0x1000, words: 2)![1] = 0xaabbcc61
    let actor = heap.allocate(bytes: 0x1b4)
    heap.lookup(actor, words: 128)![127] = 0xfeedface
    let identity = heap.allocationIdentity(at: actor, count: 0x1b4)!
    let owned = heap.snapshotReference(at: actor, count: 0x1b4, identity: identity)!
    let borrowed = heap.snapshotReference(at: actor + 7, count: 5, identity: identity, interior: true)!
    try require(heap.snapshotReference(at: actor, count: 512, identity: identity) == nil, "padding gained ownership reference")
    try require(heap.snapshotReference(at: actor + 0x1b4, count: 1, identity: identity, interior: true) == nil,
                "padding gained borrowed reference")
    let saved = try heap.checkpoint()
    let digest = try heapDigest(heap)
    let next = heap.allocate(bytes: 4)
    heap.free(actor)
    heap.store(token: actor, words: 4)[0] = 999
    let foreign = heap.allocationIdentity(at: actor, count: 16)!
    try require(heap.snapshotReference(at: actor, count: 16, identity: identity) == nil, "stale identity acquired replacement reference")
    heap.lookup(0x1000, words: 2)![1] = 0
    let plan = try heap.prepareRestore(saved)
    try require(plan.identity(for: identity.snapshotID) === identity, "in-memory owner identity lost")
    try heap.restore(plan)
    try require(heap.allocationIdentity(at: actor, count: 0x1b4) === identity, "actor ownership not resurrected")
    try require(heap.allocationIdentity(at: actor, count: 16) !== foreign, "replacement owner survived")
    try require(heap.lookup(0x1000, words: 2)![1] == 0xaabbcc61, "odd byte allocation padding lost")
    try require(heap.lookup(actor, words: 128)![127] == 0xfeedface, "legacy actor padding lost")
    try require(heap.lookupBytes(actor + 0x1b4, count: 1) == nil, "padding gained source authority")
    try require(try heapDigest(heap) == digest, "heap image differs")
    try require(heap.allocate(bytes: 4) == next, "allocator cursor not restored")
    try rejects("reused plan") { try heap.restore(plan) }
    let encoded = try ClawSnapshotOwnerDecoder.encode(saved.image)
    let decoded = try PropertyListDecoder().decode(ClawTokenHeap.Image.self, from: encoded)
    let relaunched = ClawTokenHeap(), diskPlan = try relaunched.prepareRestore(decoded)
    let diskIdentity = diskPlan.identity(for: identity.snapshotID)
    let retiredID = UUID(), retired = diskPlan.witnessIdentity(for: retiredID)
    try require(diskPlan.witnessIdentity(for: retiredID) === retired && diskPlan.identity(for: retiredID) == nil,
                "retired witness gained a live allocation or lost identity")
    try require(diskPlan.resolve(owned) === diskIdentity && diskPlan.resolve(borrowed) === diskIdentity,
                "owner/borrowed disk references did not rebind")
    try require(diskPlan.bytes(for: owned) != nil && diskPlan.bytes(for: borrowed) != nil,
                "candidate pointers did not bind through allocation witnesses")
    try require(diskPlan.reference(at: actor + 0x1b4, count: 1) == nil,
                "candidate pointer lookup exposed snapshot padding")
    let wrongExtent = ClawTokenHeap.AllocationReference(token: actor, count: 512, identity: identity.snapshotID, interior: true)
    let wrongOwner = ClawTokenHeap.AllocationReference(token: actor, count: 0x1b4, identity: foreign.snapshotID, interior: false)
    try require(diskPlan.resolve(wrongExtent) == nil && diskPlan.resolve(wrongOwner) == nil,
                "invalid owner reference resolved")
    try require(diskIdentity != nil && diskIdentity !== identity, "disk restore reused process identity")
    try relaunched.restore(diskPlan)
    try relaunched.validateInstalledRestore(diskPlan)
    try require(diskPlan.bytes(for: owned) == nil, "consumed plan exposed a borrowed candidate pointer")
    try require(relaunched.allocationIdentity(at: actor, count: 0x1b4) === diskIdentity, "disk identity rebind failed")
    try require(try heapDigest(relaunched) == digest, "disk heap image differs")
    let stale = try heap.prepareRestore(saved)
    heap.free(next)
    try rejects("stale plan") { try heap.restore(stale) }
    try rejects("foreign plan") { try relaunched.restore(stale) }
    try heap.withStableFreedStorage {
        try rejects("capture inside native operation") { _ = try heap.checkpoint() }
        try rejects("prepare inside native operation") { _ = try heap.prepareRestore(saved) }
        let outside = try relaunched.prepareRestore(decoded)
        try rejects("foreign heap commit in operation") { try heap.restore(outside) }
    }
    let first = saved.image.allocations[0]
    let before = try heapDigest(heap)
    let invalidImages: [ClawTokenHeap.Image] = [
        .init(nextToken: 3, allocations: []),
        .init(nextToken: saved.image.nextToken, allocations: [first, first]),
        .init(nextToken: saved.image.nextToken, allocations: Array(saved.image.allocations.reversed())),
        .init(nextToken: saved.image.nextToken, allocations: [.init(token: 0x1001, byteCount: 4, identity: UUID(), bytes: Data(count: 4))]),
        .init(nextToken: saved.image.nextToken, allocations: [.init(token: 0x1000, byteCount: 5, identity: UUID(), bytes: Data(count: 4))]),
        .init(nextToken: saved.image.nextToken, allocations: [.init(token: 0x1000, byteCount: 0, identity: UUID(), bytes: Data(count: 4))]),
        .init(nextToken: saved.image.nextToken, allocations: [.init(token: 0x1000, byteCount: 3, identity: UUID(), bytes: Data(count: 3))]),
        .init(nextToken: saved.image.nextToken, allocations: [.init(token: 0xfffffffc, byteCount: 4, identity: UUID(), bytes: Data(count: 4))]),
        .init(nextToken: saved.image.nextToken, allocations: [first, .init(token: 0x2000, byteCount: 4, identity: first.identity, bytes: Data(count: 4))])
    ]
    for image in invalidImages { try rejects("malformed heap image") { _ = try heap.prepareRestore(image) } }
    try require(try heapDigest(heap) == before, "failed decode changed heap")
    // A source physical resize keeps ownership, so snapshot restore must keep it.
    let resized = heap.allocate(bytes: 5), resizeID = heap.allocationIdentity(at: resized, count: 5)!
    heap.lookupBytes(resized, count: 5)![4] = 17
    let small = try heap.checkpoint()
    try require(heap.resizeInPlace(token: resized, expectedIdentity: resizeID, expectedCount: 5, count: 77), "resize fixture")
    try heap.restore(heap.prepareRestore(small))
    try require(heap.allocationIdentity(at: resized, count: 5) === resizeID && heap.lookupBytes(resized, count: 5)![4] == 17,
                "resize restore lost source extent/identity/data")
}

struct FixtureState: Codable {
    let random: ClawNativeRandom.SavedState
    let clock: ClawFrameClockAdapter.SavedState
    let now: UInt32
    let actor: UInt32
}
final class PhysicalClock { var now: UInt32 = 1000 }
func run600(heap: ClawTokenHeap, rng: ClawNativeRandom, clock: ClawFrameClockAdapter,
            physical: PhysicalClock, actor: UInt32) throws -> [String] {
    var hashes: [String] = []
    for frame in 0..<600 {
        physical.now &+= UInt32(frame % 3 == 0 ? 16 : 17)
        let step = clock.sampleScene()
        let random = rng.call(0x4a3050)
        let words = heap.lookup(actor, words: 128)!
        // Scripted changes exercise clock, original rand, allocating/freeing,
        // exact byte extents and the future allocator cursor on replay.
        let held: UInt32 = frame % 120 < 60 ? 1 : 2
        words[0] &+= random &* held; words[1] = step.accumulated
        if frame % 17 == 0 {
            let temporary = heap.allocate(bytes: UInt32(frame % 31 + 1))
            heap.lookupBytes(temporary, count: 1)![0] = UInt8(truncatingIfNeeded: random)
            heap.free(temporary)
        }
        struct FrameState: Encodable {
            let heap: String
            struct Call: Encodable { let function: UInt32; let count: UInt64 }
            let random: Data
            let calls: [Call]
            let clock: ClawFrameClockAdapter.SavedState
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = .sortedKeys
        let saved = try rng.savedState()
        // UInt32-key dictionaries encode as alternating arrays. Canonicalize
        // their order explicitly; JSON's sortedKeys only sorts keyed objects.
        let scalars = [saved.tlsIndex, saved.thread ?? 0, saved.lastError ?? 0, saved.fault,
                       saved.contextFault, saved.initialized ? 1 : 0] + saved.unresolved.sorted()
        let state = try FrameState(heap: heapDigest(heap), random: encoder.encode(scalars),
            calls: saved.calls.keys.sorted().map { .init(function: $0, count: saved.calls[$0]!) }, clock: clock.savedState())
        hashes.append(SHA256.hash(data: try encoder.encode(state)).map { String(format: "%02x", $0) }.joined())
    }
    try require(rng.fault == 0 && rng.unresolved.isEmpty, "original RNG fault")
    return hashes
}
func storageChecks(_ directory: URL, relaunch: Bool) throws {
    let root = directory.appendingPathComponent("slots", isDirectory: true)
    let store = ClawSnapshotSlots(directory: root, build: "snapshot-fixture-build")
    let physical = PhysicalClock(), heap = ClawTokenHeap()
    let rng = ClawNativeRandom(heap: heap)
    let clock = ClawFrameClockAdapter(clock: { physical.now })
    if relaunch {
        let image = try store.load(.quick)
        var decoder = try ClawSnapshotOwnerDecoder(image.owners, requiring: ["fixture"])
        let state = try decoder.decode(FixtureState.self, key: "fixture")
        try decoder.finish()
        try heap.restore(heap.prepareRestore(image.heap))
        try rng.restoreState(state.random); try clock.restoreState(state.clock); physical.now = state.now
        let hashes = try run600(heap: heap, rng: rng, clock: clock, physical: physical, actor: state.actor)
        let expected = try PropertyListDecoder().decode([String].self,
            from: Data(contentsOf: directory.appendingPathComponent("hashes.plist")))
        try require(hashes == expected, "600-frame disk relaunch replay differs")
        print("{\"check\":\"snapshot-storage-relaunch\",\"status\":\"pass\",\"frames\":600,\"gameplay\":false}")
        return
    }
    try? FileManager.default.removeItem(at: root)
    try require(rng.initialized && rng.fault == 0, "RNG initialize")
    _ = rng.call(0x4a3040, arguments: [0x1b3cf])
    let actor = heap.allocate(bytes: 0x1b4)
    physical.now += 35; _ = clock.sample()
    let state = try FixtureState(random: rng.savedState(), clock: clock.savedState(), now: physical.now, actor: actor)
    let saved = try heap.checkpoint()
    let image = ClawSnapshotImage(build: store.build, level: 1, heap: saved.image,
        owners: ["fixture": try ClawSnapshotOwnerDecoder.encode(state)])
    try store.save(image, to: .quick)
    try require(store.occupied() == [.quick], "slot enumeration")
    for slot in [ClawSnapshotSlots.Slot.one, .two, .three] { try store.save(image, to: slot) }
    try require(store.occupied().count == 4, "four slots")
    let first = try run600(heap: heap, rng: rng, clock: clock, physical: physical, actor: actor)
    try heap.restore(heap.prepareRestore(saved))
    try rng.restoreState(state.random); try clock.restoreState(state.clock); physical.now = state.now
    let second = try run600(heap: heap, rng: rng, clock: clock, physical: physical, actor: actor)
    try require(first == second, "600-frame in-memory replay differs")
    try require(try store.load(.quick) == image, "cached slot changed")
    try ClawSnapshotOwnerDecoder.encode(first).write(to: directory.appendingPathComponent("hashes.plist"), options: .atomic)
    let old = try Data(contentsOf: store.file(.quick))
    let wrongBuild = ClawSnapshotSlots(directory: root, build: "different-build")
    try rejects("wrong build on relaunch") { _ = try wrongBuild.load(.quick) }
    try rejects("wrong build save") { try wrongBuild.save(image, to: .quick) }
    try require(try Data(contentsOf: store.file(.quick)) == old, "invalid save replaced prior slot")
    // Mutate a syntactically valid envelope: its checksum must catch corruption.
    var envelope = try PropertyListSerialization.propertyList(from: old, format: nil) as! [String: Any]
    var payload = envelope["payload"] as! Data; payload[payload.count / 2] ^= 1; envelope["payload"] = payload
    try PropertyListSerialization.data(fromPropertyList: envelope, format: .binary, options: 0).write(to: store.file(.one))
    let fresh = ClawSnapshotSlots(directory: root, build: store.build)
    try rejects("corrupt slot") { _ = try fresh.load(.one) }
    try require(try fresh.load(.quick) == image, "bad slot damaged quick slot")
    try rejects("omitted required owner") { _ = try ClawSnapshotOwnerDecoder(image.owners, requiring: ["fixture", "player"]) }
    try rejects("unknown archived owner") { _ = try ClawSnapshotOwnerDecoder(image.owners, requiring: ["player"]) }
    var missing = try ClawSnapshotOwnerDecoder(image.owners, requiring: ["fixture"])
    try rejects("unconsumed owner") { try missing.finish() }
    try rejects("missing owner") { let _: FixtureState = try missing.decode(FixtureState.self, key: "absent") }
    try rejects("wrong owner schema") { let _: [String] = try missing.decode([String].self, key: "fixture") }
    try rejects("failed owner decode consumed state") { try missing.finish() }
    let _: FixtureState = try missing.decode(FixtureState.self, key: "fixture"); try missing.finish()
    // Failed clock decode is all-or-nothing.
    let beforeClock = clock.savedState()
    let badClock = ClawFrameClockAdapter.SavedState(manager: state.clock.manager, clock: state.clock.clock,
        stage: state.clock.stage, animation: Data(), accumulated: 999)
    try rejects("invalid clock layout") { try clock.restoreState(badClock) }
    try require(clock.savedState() == beforeClock, "invalid clock mutated state")
    let beforeRng = try rng.savedState()
    let badRng = ClawNativeRandom.SavedState(tlsIndex: 0, thread: 0x1234, lastError: 0, fault: 0,
        contextFault: 0, calls: [:], unresolved: [], initialized: true)
    try rejects("invalid RNG thread") { try rng.restoreState(badRng) }
    try require(try rng.savedState() == beforeRng, "invalid RNG mutated state")
    // A disk write failure does not report a save or cache the new state.
    let blockedPath = directory.appendingPathComponent("not-a-directory")
    try Data([1]).write(to: blockedPath)
    let blocked = ClawSnapshotSlots(directory: blockedPath, build: store.build)
    try rejects("failed disk write") { try blocked.save(image, to: .quick) }
    try require(blocked.occupied().isEmpty, "failed save populated memory slot")
    // Also preserve a previously populated in-memory slot on write failure.
    let atomicPath = directory.appendingPathComponent("atomic-store", isDirectory: true)
    let backup = directory.appendingPathComponent("atomic-store-backup", isDirectory: true)
    try? FileManager.default.removeItem(at: atomicPath)
    try? FileManager.default.removeItem(at: backup)
    let atomic = ClawSnapshotSlots(directory: atomicPath, build: store.build)
    try atomic.save(image, to: .quick)
    try FileManager.default.moveItem(at: atomicPath, to: backup)
    try Data([1]).write(to: atomicPath)
    let changed = ClawSnapshotImage(build: store.build, level: 2, heap: image.heap, owners: image.owners)
    try rejects("overwrite after disk failure") { try atomic.save(changed, to: .quick) }
    try require(try atomic.load(.quick) == image, "failed overwrite changed in-memory slot")
    try FileManager.default.removeItem(at: atomicPath)
    try FileManager.default.moveItem(at: backup, to: atomicPath)
    try require(try ClawSnapshotSlots(directory: atomicPath, build: store.build).load(.quick) == image,
                "failed overwrite changed disk slot")
    print("{\"check\":\"snapshot-storage\",\"status\":\"pass\",\"frames\":600,\"gameplay\":false}")
}

do {
    let directory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
    let relaunch = CommandLine.arguments.contains("--relaunch")
    if !relaunch { try heapChecks() }
    try storageChecks(directory, relaunch: relaunch)
} catch {
    fputs("snapshot check failed: \(error)\n", stderr)
    exit(1)
}
