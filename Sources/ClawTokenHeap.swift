import Foundation

// Physical owners opt into scene destruction without coupling the scene to a
// particular allocator implementation. A claimed retired token stays claimed.
protocol ClawSceneObjectAllocationOwner: AnyObject {
    var sceneObjectHeap: ClawTokenHeap { get }
    var canRegisterSceneObjectOwner: Bool { get }
    func claimsSceneObject(_ token: UInt32) -> Bool
    func releaseSceneObject(_ token: UInt32) -> Bool
}

// Stable 32-bit identities and pinned storage for recovered x86 object graphs.
// Tokens are never truncated host pointers. Interior spans are bounds checked.
final class ClawTokenHeap {
    // Retaining this opaque identity does not retain the allocation's storage.
    // A new block always gets a new identity, including after token/pointer reuse.
    final class AllocationIdentity {
        // Persist the identity separately from its bytes. Owner ledgers must
        // rebind these IDs on disk restore; token equality grants no ownership.
        // Transport metadata, excluded from gameplay determinism hashes. Only
        // snapshots need it; normal allocations do not generate random UUIDs.
        private(set) lazy var snapshotID = UUID()
        fileprivate init(snapshotID: UUID? = nil) {
            if let snapshotID { self.snapshotID = snapshotID }
        }
    }
    fileprivate final class Block {
        let identity: AllocationIdentity
        let pointer: UnsafeMutablePointer<UInt32>
        let words: Int
        let byteCount: UInt32
        init(words: Int, byteCount: UInt32, identity: AllocationIdentity = AllocationIdentity()) {
            self.identity = identity
            self.words = words; self.byteCount = byteCount
            pointer = .allocate(capacity: words)
            pointer.initialize(repeating: 0, count: words)
        }
        deinit { pointer.deinitialize(count: words); pointer.deallocate() }
    }
    private var blocks: [UInt32: Block] = [:]
    private var bases: [UInt32] = []
    private var operationDepth = 0
    private var retired: [Block] = []
    private var nextToken: UInt32 = 0x61000000
    private var topologyGeneration: UInt64 = 0
    // Debug-only inspection (CLAW_REAL_SPEED_CONTROL HUD probe); never used by game paths.
    var debugAllocationBases: [UInt32] { bases }

    // Ownership requires the exact allocation base and source byte extent,
    // never a valid interior span or legacy word padding.
    func allocationIdentity(at token: UInt32, count: UInt32) -> AllocationIdentity? {
        guard let block = blocks[token], block.byteCount == count else { return nil }
        return block.identity
    }

    // Borrowed records may be interior spans. This identifies their containing
    // allocation without retaining its bytes or admitting legacy word padding.
    func containingAllocationIdentity(at token: UInt32, count: UInt32) -> AllocationIdentity? {
        let base: UInt32
        if blocks[token] != nil { base = token }
        else {
            let index = insertionIndex(token)
            guard index > 0 else { return nil }
            base = bases[index - 1]
        }
        let block = blocks[base]!
        guard UInt64(token) + UInt64(count) <= UInt64(base) + UInt64(block.byteCount) else { return nil }
        return block.identity
    }

    // Includes physical snapshot padding: a reserved stack must never shadow
    // any live allocation, even bytes hidden from the canonical byte view.
    func overlaps(_ token: UInt32, count: UInt32) -> Bool {
        guard count != 0 else { return false }
        let end = UInt64(token) + UInt64(count)
        let index = insertionIndex(token)
        if index < bases.count && UInt64(bases[index]) < end { return true }
        if index > 0 {
            let base = bases[index - 1]
            if UInt64(base) + UInt64(blocks[base]!.words) * 4 > UInt64(token) { return true }
        }
        return false
    }

    private func insertionIndex(_ token: UInt32) -> Int {
        var low = 0, high = bases.count
        while low < high {
            let middle = low + (high - low) / 2
            if bases[middle] < token { low = middle + 1 } else { high = middle }
        }
        return low
    }

    @discardableResult func store(token: UInt32, words: Int) -> UnsafeMutablePointer<UInt32> {
        precondition(words > 0 && words <= 1 << 20)
        return store(token: token, words: words, byteCount: UInt32(words) * 4)
    }

    // Fixed source-image identities retain their exact byte extent, including
    // odd-sized strings. Word snapshot padding remains a separate legacy view.
    @discardableResult func storeBytes(token: UInt32, count: UInt32) -> UnsafeMutablePointer<UInt8> {
        precondition(count > 0 && count <= 4 << 20)
        let pointer = store(token: token, words: Int((count + 3) / 4), byteCount: count)
        return UnsafeMutableRawPointer(pointer).assumingMemoryBound(to: UInt8.self)
    }

    @discardableResult private func store(token: UInt32, words: Int, byteCount: UInt32) -> UnsafeMutablePointer<UInt32> {
        precondition(words > 0 && words <= (Int(Self.worldBufferByteLimit)+3)/4 && token & 3 == 0)
        precondition(byteCount > 0 && UInt64(byteCount) <= UInt64(words) * 4)
        precondition(blocks[token] == nil)
        let end = UInt64(token) + UInt64(words) * 4
        precondition(end <= UInt64(UInt32.max))
        let index = insertionIndex(token)
        if index > 0 {
            let previous = bases[index - 1]
            precondition(UInt64(previous) + UInt64(blocks[previous]!.words) * 4 <= UInt64(token))
        }
        if index < bases.count { precondition(end <= UInt64(bases[index])) }
        let block = Block(words: words, byteCount: byteCount)
        blocks[token] = block; bases.insert(token, at: index)
        topologyGeneration &+= 1
        return block.pointer
    }

    // Elected scene actors, logic and helpers share the scene's cursor
    // so list nodes and later canonical scopes cannot reuse their storage.
    // The source extent and allocation identity remain those of operator new.
    // Canonical actor consumers can omit the legacy 128-word snapshot padding.
    func allocateSceneObject(bytes: UInt32, minimumToken: UInt32, legacyActorPadding: Bool = true) -> UInt32 {
        guard bytes == 0x1b4 || bytes == 0x1b8 || bytes == 0x1c8 || bytes == 0x174 || bytes == 0xa4 || bytes == 0xa8 || bytes == 0xb8 || bytes == 0x6c || bytes == 0x70 || bytes == 0x48 || bytes == 0x50 || bytes == 0x54 || bytes == 0x58 || bytes == 0x64 || bytes == 0x410 || bytes == 0x7c || bytes == 0x498 || bytes == 0x438 || bytes == 0x450 || bytes == 0x440 || bytes == 0x430 || bytes == 0x4b8 || bytes == 0x4d8 || bytes == 0x4e8 || bytes == 0x4e0 || bytes == 0x4a0 || bytes == 0x460 || bytes == 0x488 || bytes == 0x4b0 || bytes == 0x508 || bytes == 0x478 || bytes == 0x480 || bytes == 0xd48,
              minimumToken & 15 == 0 else { return 0 }
        let words = bytes == 0x1b4 && legacyActorPadding ? 128 : Int((bytes + 3) / 4)
        let token = max(nextToken, minimumToken)
        let end = UInt64(token) + UInt64(words * 4) + 15
        guard end < 0x70000000, !overlaps(token, count: UInt32(words * 4)) else { return 0 }
        _ = store(token: token, words: words, byteCount: bytes)
        nextToken = UInt32(end) & ~15
        return token
    }

    // Scene frees require an allocation base, never an interior/padding span.
    @discardableResult func freeSceneStorage(_ token: UInt32) -> Bool {
        guard blocks[token] != nil else { return false }
        free(token)
        return true
    }

    // Largest sampled WWD (The Poisonous Caves: 18,872,009 decoded
    // bytes) plus the original loader's two 32-byte margins. This is elected
    // only for exact buffer sizes derived from a validated world by its owner.
    static let worldBufferByteLimit:UInt32 = 18_872_073
    func allocateWorldBuffer(bytes:UInt32) -> UInt32 {
        allocate(bytes:bytes,limit:Self.worldBufferByteLimit)
    }
    func allocate(bytes: UInt32) -> UInt32 { allocate(bytes:bytes,limit:4 << 20) }
    private func allocate(bytes:UInt32,limit:UInt32) -> UInt32 {
        guard bytes > 0, bytes <= limit else { return 0 }
        // The scene C API carries a 128-word animation-actor snapshot. Actual
        // generic/plain allocations are 0x1b4/0x168. The generic enemy API
        // carries 264 words; keg/crate source objects use 260/262. Reserve only
        // portable snapshot padding; source bridges copy actual allocation words.
        let words = bytes == 0x1b4 || bytes == 0x168 ? 128 : bytes == 0x410 || bytes == 0x418 ? 264 : Int((bytes + 3) / 4)
        let token = nextToken
        let end = UInt64(token) + UInt64(words) * 4 + 15
        guard end < UInt64(UInt32.max), !overlaps(token, count: UInt32(words) * 4) else { return 0 }
        nextToken = UInt32(end) & ~15
        _ = store(token: token, words: words, byteCount: bytes); return token
    }

    func lookup(_ token: UInt32, words: UInt32) -> UnsafeMutablePointer<UInt32>? {
        guard token & 3 == 0 else { return nil }
        let end = UInt64(token) + UInt64(words) * 4
        if let exact = blocks[token] { return words <= exact.words ? exact.pointer : nil }
        let index = insertionIndex(token)
        guard index > 0 else { return nil }
        let base = bases[index - 1], block = blocks[base]!
        guard end <= UInt64(base) + UInt64(block.words) * 4 else { return nil }
        return block.pointer.advanced(by: Int((token - base) / 4))
    }

    // Canonical modules see exactly the requested allocation, including byte
    // interiors, without the padding reserved for legacy word snapshots.
    // Empty spans at a live allocation's end are valid; they cannot be read.
    func lookupBytes(_ token: UInt32, count: UInt32) -> UnsafeMutablePointer<UInt8>? {
        let base: UInt32
        let block: Block
        if let exact = blocks[token] {
            base = token; block = exact
        } else {
            let index = insertionIndex(token)
            guard index > 0 else { return nil }
            base = bases[index - 1]; block = blocks[base]!
        }
        let end = UInt64(token) + UInt64(count)
        guard end <= UInt64(base) + UInt64(block.byteCount) else { return nil }
        return UnsafeMutableRawPointer(block.pointer)
            .advanced(by: Int(token - base)).assumingMemoryBound(to: UInt8.self)
    }

    // An explicit physical-service resize preserves the virtual base and live
    // allocation identity. Native backing may move; synchronous borrowers of
    // its old backing remain safe inside withStableFreedStorage. Callers must
    // revalidate the exact extent after any effect-capable service.
    @discardableResult
    func resizeInPlace(token: UInt32, expectedIdentity: AllocationIdentity,
                       expectedCount: UInt32, count: UInt32) -> Bool {
        guard count > 0, count <= 4 << 20,
              let old = blocks[token], old.identity === expectedIdentity,
              old.byteCount == expectedCount else { return false }
        let words = Int((count + 3) / 4)
        let end = UInt64(token) + UInt64(words) * 4
        let index = insertionIndex(token)
        guard end <= UInt64(UInt32.max),
              index + 1 >= bases.count || end <= UInt64(bases[index + 1]) else { return false }
        let advancesCursor = token <= nextToken && end > UInt64(nextToken)
        guard !advancesCursor || end + 15 < UInt64(UInt32.max) else { return false }
        if old.byteCount == count { return true }
        let replacement = Block(words: words, byteCount: count, identity: old.identity)
        UnsafeMutableRawPointer(replacement.pointer).copyMemory(
            from: UnsafeRawPointer(old.pointer), byteCount: Int(min(old.byteCount, count)))
        blocks[token] = replacement
        topologyGeneration &+= 1
        if advancesCursor { nextToken = UInt32(end + 15) & ~15 }
        if operationDepth != 0 { retired.append(old) }
        return true
    }
    // Original bodies can reread a just-freed object's cleared fields through
    // a cached pointer before returning. Keep bytes alive for that native call
    // graph while ending token ownership immediately; physical CRT reuse remains
    // a host boundary. Nested operations share the outermost retention scope.
    func withStableFreedStorage<T>(_ body: () throws -> T) rethrows -> T {
        operationDepth += 1
        defer {
            operationDepth -= 1
            if operationDepth == 0 { retired.removeAll() }
        }
        return try body()
    }
    func free(_ token: UInt32) {
        if let block = blocks.removeValue(forKey: token) {
            topologyGeneration &+= 1
            bases.remove(at: insertionIndex(token))
            if operationDepth != 0 { retired.append(block) }
        }
    }

    // These are heap images, not complete game snapshots. Every native owner
    // must be restored in the same between-frame transaction. In particular,
    // raw host pointers and Swift ownership ledgers do not live in this image.
    struct Image: Codable, Equatable {
        struct Allocation: Codable, Equatable {
            let token: UInt32
            let byteCount: UInt32
            let identity: UUID
            let bytes: Data // Includes legacy word padding, not just byteCount.
        }
        let nextToken: UInt32
        let allocations: [Allocation]

        func validate() throws {
            // Validate the entire image before allocating or touching live storage.
            // A cursor may precede or overlap fixed-address blocks (allocate then
            // rejects that overlap); preserve that state rather than normalizing it.
            guard nextToken >= 0x61000000, nextToken & 15 == 0,
                  allocations.count <= 131072 else { throw SnapshotError.invalidImage }
            var end: UInt64 = 0, total = 0, ids: Set<UUID> = []
            for allocation in allocations {
                let count = allocation.bytes.count
                guard allocation.token & 3 == 0, UInt64(allocation.token) >= end,
                      count > 0, count <= Int((ClawTokenHeap.worldBufferByteLimit+3) & ~3), count & 3 == 0,
                      allocation.byteCount > 0, allocation.byteCount <= count,
                      ids.insert(allocation.identity).inserted else { throw SnapshotError.invalidImage }
                end = UInt64(allocation.token) + UInt64(count)
                total += count
                guard end <= UInt64(UInt32.max), total <= 512 << 20
                else { throw SnapshotError.invalidImage }
            }
        }
    }
    struct Checkpoint {
        let image: Image
        fileprivate let identities: [UUID: AllocationIdentity]
    }
    struct AllocationReference: Codable, Equatable {
        let token: UInt32, count: UInt32
        let identity: UUID
        let interior: Bool
    }
    func snapshotReference(at token: UInt32, count: UInt32, identity: AllocationIdentity,
                           interior: Bool = false) -> AllocationReference? {
        let actual = interior ? containingAllocationIdentity(at: token, count: count) : allocationIdentity(at: token, count: count)
        guard actual === identity else { return nil }
        return AllocationReference(token: token, count: count, identity: identity.snapshotID, interior: interior)
    }
    enum SnapshotError: Error { case activeOperation, invalidImage, stalePlan }

    struct AllocationTopology {
        let token: UInt32, byteCount: UInt32, identity: UUID
    }
    // Component replay can inspect allocation order/identity without copying
    // immutable sprite/surface bytes on every step. This is not a heap image.
    func snapshotTopology() throws -> (nextToken: UInt32, allocations: [AllocationTopology]) {
        guard operationDepth == 0, retired.isEmpty else { throw SnapshotError.activeOperation }
        return (nextToken, bases.map { token in
            let block = blocks[token]!
            return AllocationTopology(token: token, byteCount: block.byteCount, identity: block.identity.snapshotID)
        })
    }

    func checkpoint() throws -> Checkpoint {
        guard operationDepth == 0, retired.isEmpty else { throw SnapshotError.activeOperation }
        let allocations = bases.map { token -> Image.Allocation in
            let block = blocks[token]!
            return Image.Allocation(token: token, byteCount: block.byteCount,
                identity: block.identity.snapshotID,
                bytes: Data(bytes: block.pointer, count: block.words * 4))
        }
        return Checkpoint(image: Image(nextToken: nextToken, allocations: allocations),
            identities: Dictionary(uniqueKeysWithValues: blocks.values.map { ($0.identity.snapshotID, $0.identity) }))
    }

    final class RestorePlan {
        fileprivate let heap: ObjectIdentifier
        fileprivate let generation: UInt64
        fileprivate let image: Image
        fileprivate var blocks: [UInt32: Block]
        fileprivate let identities: [UUID: AllocationIdentity]
        private var retiredIdentities: [UUID: AllocationIdentity] = [:]
        fileprivate var consumed = false
        fileprivate init(heap: ClawTokenHeap, image: Image, blocks: [UInt32: Block],
                         identities: [UUID: AllocationIdentity]) {
            self.heap = ObjectIdentifier(heap); generation = heap.topologyGeneration
            self.image = image; self.blocks = blocks; self.identities = identities
        }
        func identity(for id: UUID) -> AllocationIdentity? { identities[id] }
        func reference(at token: UInt32, count: UInt32) -> AllocationReference? {
            var low = 0, high = image.allocations.count
            while low < high {
                let middle = low + (high - low) / 2
                if image.allocations[middle].token <= token { low = middle + 1 } else { high = middle }
            }
            guard low > 0 else { return nil }
            let allocation = image.allocations[low - 1]
            guard UInt64(token) + UInt64(count) <= UInt64(allocation.token) + UInt64(allocation.byteCount) else { return nil }
            return .init(token: token, count: count, identity: allocation.identity, interior: true)
        }
        // Candidate owners bind pinned pointers only through the same plan that
        // supplies their allocation witnesses. No live heap is consulted here.
        func bytes(for reference: AllocationReference) -> UnsafeMutablePointer<UInt8>? {
            guard !consumed, resolve(reference) != nil else { return nil }
            var low = 0, high = image.allocations.count
            while low < high {
                let middle = low + (high - low) / 2
                if image.allocations[middle].token <= reference.token { low = middle + 1 } else { high = middle }
            }
            let index = low
            guard index > 0, let block = blocks[image.allocations[index - 1].token] else { return nil }
            return UnsafeMutableRawPointer(block.pointer).advanced(by: Int(reference.token - image.allocations[index - 1].token))
                .assumingMemoryBound(to: UInt8.self)
        }
        func witnessIdentity(for id: UUID) -> AllocationIdentity {
            // Retired/stale ledger entries must remain stale after relaunch.
            // Recreating their shared witness grants no storage authority;
            // ownership still requires a matching live token and source extent.
            if let live = identities[id] { return live }
            if let retired = retiredIdentities[id] { return retired }
            let retired = AllocationIdentity(snapshotID: id)
            retiredIdentities[id] = retired
            return retired
        }
        func identity(at token: UInt32, count: UInt32, matching id: UUID) -> AllocationIdentity? {
            guard let block = blocks[token], block.byteCount == count, block.identity.snapshotID == id else { return nil }
            return block.identity
        }
        func resolve(_ reference: AllocationReference) -> AllocationIdentity? {
            // Resolve against the source extent, never legacy word padding.
            let allocations = image.allocations
            var low = 0, high = allocations.count
            while low < high {
                let middle = low + (high - low) / 2
                if allocations[middle].token <= reference.token { low = middle + 1 } else { high = middle }
            }
            guard low > 0 else { return nil }
            let allocation = allocations[low - 1]
            guard allocation.identity == reference.identity,
                  UInt64(reference.token) + UInt64(reference.count) <= UInt64(allocation.token) + UInt64(allocation.byteCount),
                  reference.interior || (reference.token == allocation.token && reference.count == allocation.byteCount)
            else { return nil }
            return identities[reference.identity]
        }
    }

    func prepareRestore(_ checkpoint: Checkpoint) throws -> RestorePlan {
        try prepareRestore(checkpoint.image, retaining: checkpoint.identities)
    }
    func prepareRestore(_ image: Image) throws -> RestorePlan {
        try prepareRestore(image, retaining: [:])
    }
    private func prepareRestore(_ image: Image, retaining: [UUID: AllocationIdentity]) throws -> RestorePlan {
        guard operationDepth == 0, retired.isEmpty else { throw SnapshotError.activeOperation }
        try image.validate()
        var replacement: [UInt32: Block] = [:], identities: [UUID: AllocationIdentity] = [:]
        for allocation in image.allocations {
            let identity = retaining[allocation.identity] ?? AllocationIdentity(snapshotID: allocation.identity)
            let block = Block(words: allocation.bytes.count / 4, byteCount: allocation.byteCount, identity: identity)
            allocation.bytes.withUnsafeBytes { bytes in
                UnsafeMutableRawPointer(block.pointer).copyMemory(from: bytes.baseAddress!, byteCount: bytes.count)
            }
            replacement[allocation.token] = block; identities[allocation.identity] = identity
        }
        return RestorePlan(heap: self, image: image, blocks: replacement, identities: identities)
    }
    func validateRestore(_ plan: RestorePlan) throws {
        guard operationDepth == 0, retired.isEmpty else { throw SnapshotError.activeOperation }
        guard plan.heap == ObjectIdentifier(self), plan.generation == topologyGeneration, !plan.consumed
        else { throw SnapshotError.stalePlan }
    }
    func restore(_ plan: RestorePlan) throws {
        try validateRestore(plan)
        // No recovered callback can be active here. All host pointers into the
        // previous heap become invalid; participants rebind through token/ID.
        blocks = plan.blocks; bases = plan.image.allocations.map(\.token)
        nextToken = plan.image.nextToken; topologyGeneration &+= 1; plan.consumed = true
        plan.blocks.removeAll()
    }
    func validateInstalledRestore(_ plan: RestorePlan) throws {
        guard operationDepth == 0, plan.heap == ObjectIdentifier(self), plan.consumed,
              topologyGeneration == plan.generation &+ 1 else { throw SnapshotError.stalePlan }
    }
}

// Only pointer-free, reference-free imported C values may opt in. A native
// context containing callbacks, host pointers or allocation identities needs an
// explicit transport that rebinds them; never copy it into a disk snapshot.
protocol ClawSnapshotNativeValue {
    init()
}
extension ClawSnapshotNativeValue {
    func snapshotBytes() -> Data {
        var value = self
        return withUnsafeBytes(of: &value) { Data($0) }
    }
    static func fromSnapshotBytes(_ data: Data) throws -> Self {
        guard data.count == MemoryLayout<Self>.size else { throw ClawSnapshotError.invalidState }
        var value = Self()
        _ = withUnsafeMutableBytes(of: &value) { destination in data.copyBytes(to: destination) }
        return value
    }
}

enum ClawSnapshotError: Error {
    case invalidState, incompatibleBuild, incompleteOwners, activeFrame
}

// An owner may deliberately remember a retired allocation. Preserve its witness
// even when the token has been reused, without granting the replacement bytes.
struct ClawSnapshotWitness: Codable, Equatable {
    let reference: ClawTokenHeap.AllocationReference
    let live: Bool
    init(heap: ClawTokenHeap, token: UInt32, count: UInt32,
         identity: ClawTokenHeap.AllocationIdentity, interior: Bool = false) {
        reference = .init(token: token, count: count, identity: identity.snapshotID, interior: interior)
        live = heap.snapshotReference(at: token, count: count, identity: identity, interior: interior) != nil
    }
    func resolve(in plan: ClawTokenHeap.RestorePlan) throws -> ClawTokenHeap.AllocationIdentity {
        if live {
            guard let identity = plan.resolve(reference) else { throw ClawSnapshotError.invalidState }
            return identity
        }
        guard plan.resolve(reference) == nil else { throw ClawSnapshotError.invalidState }
        return plan.witnessIdentity(for: reference.identity)
    }
}

// Decode performs the native layout check before a SavedState can be applied.
// The outer file's executable fingerprint prevents cross-build layout reuse.
struct ClawSnapshotValue<Value: ClawSnapshotNativeValue>: Codable, Equatable {
    let value: Value
    init(_ value: Value) { self.value = value }
    init(from decoder: Decoder) throws {
        value = try Value.fromSnapshotBytes(decoder.singleValueContainer().decode(Data.self))
    }
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(value.snapshotBytes())
    }
    static func == (lhs: Self, rhs: Self) -> Bool { lhs.value.snapshotBytes() == rhs.value.snapshotBytes() }
}

