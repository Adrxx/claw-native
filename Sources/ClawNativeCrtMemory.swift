import Foundation

// Physical-service domain v1. No CRT source edges, Windows heap metadata, or
// startup state are synthesized here. The caller supplies the shared heap.
final class ClawNativeCrtMemory {
    enum Failure: Error { case invalidOwnership, reentrantService, unsupportedNewMode }
    enum ResizePolicy { case automatic, move, inPlace, fail }
    enum StoragePolicy { case native, frozenReferenceV1 }
    struct Allocation {
        let base: UInt32
        let requested: UInt32
        let capacity: UInt32
        let identity: ClawTokenHeap.AllocationIdentity
        let generation: UInt64
    }
    struct RetiredAllocation {
        let allocation: Allocation
        let bytes: [UInt8]
    }
    static let domain = "crt-memory-service-v1"
    static let maximumCapacity: UInt32 = 4 << 20
    let heap: ClawTokenHeap
    let storagePolicy: StoragePolicy
    private let executionThread = Thread.current
    private var active = false
    private var serviceFault = false
    private var nextBase: UInt32
    private var generation: UInt64 = 0
    private var owned: [UInt32: Allocation] = [:]
    private(set) var retired: [RetiredAllocation] = []

    // A collision is exhaustion, not permission to overwrite or bypass it.
    init(heap: ClawTokenHeap, firstBase: UInt32 = 0x68000000, storagePolicy: StoragePolicy = .native) {
        precondition(firstBase != 0 && firstBase & 15 == 0)
        self.heap = heap; self.nextBase = firstBase; self.storagePolicy = storagePolicy
    }

    private func service<T>(newMode: UInt32 = 0, _ body: () throws -> T) throws -> T {
        guard Thread.current === executionThread else { throw Failure.invalidOwnership }
        guard !active else { serviceFault = true; throw Failure.reentrantService }
        guard !serviceFault else { throw Failure.reentrantService }
        guard newMode == 0 else { throw Failure.unsupportedNewMode }
        active = true
        defer { active = false }
        return try body()
    }

    private func live(_ base: UInt32) throws -> Allocation {
        guard let allocation = owned[base],
              heap.allocationIdentity(at: base, count: allocation.capacity) === allocation.identity else {
            throw Failure.invalidOwnership
        }
        return allocation
    }

    private func rounded(_ requested: UInt32) -> UInt32? {
        // The bounded domain rejects requests above its physical backing limit.
        // It does not claim the original Windows heap's extreme-size behavior.
        guard requested <= (storagePolicy == .native ? Self.maximumCapacity : 0x10000) else { return nil }
        return (max(requested, 1) + 15) & ~15
    }

    private func allocate(_ requested: UInt32, zero: Bool) -> UInt32 {
        guard let capacity = rounded(requested) else { return 0 }
        let base = nextBase, end = UInt64(base) + UInt64(capacity) + allocationGap
        guard end < UInt64(UInt32.max), generation < UInt64.max,
              !heap.overlaps(base, count: capacity) else { return 0 }
        generation += 1
        let bytes = heap.storeBytes(token: base, count: capacity)
        // Unspecified malloc/growth bytes follow the elected storage policy.
        // Only calloc promises zero across the whole usable capacity.
        for index in 0..<Int(capacity) {
            bytes[index] = zero ? 0 : initialByte(offset: index, generation: generation)
        }
        owned[base] = .init(base: base, requested: requested, capacity: capacity,
                           identity: heap.allocationIdentity(at: base, count: capacity)!, generation: generation)
        nextBase = UInt32(end)
        return base
    }

    private var allocationGap: UInt64 { storagePolicy == .native ? 0 : 16 }
    private func initialByte(offset: Int, generation: UInt64) -> UInt8 {
        storagePolicy == .native ? 0xcc : UInt8(truncatingIfNeeded: UInt64(offset) &* 31 &+ generation &* 19)
    }
    private func growthByte(offset: Int, generation: UInt64) -> UInt8 {
        storagePolicy == .native ? 0xcc : UInt8(truncatingIfNeeded: UInt64(offset) &* 17 &+ generation)
    }

    func malloc(_ requested: UInt32, newMode: UInt32 = 0, fail: Bool = false) throws -> UInt32 {
        try service(newMode: newMode) { fail ? 0 : allocate(requested, zero: false) }
    }

    func calloc(_ count: UInt32, _ size: UInt32, newMode: UInt32 = 0, fail: Bool = false) throws -> UInt32 {
        // This domain admits only products representable in DWORD arithmetic.
        // Historical low-DWORD IMUL wraparound is deliberately outside v1.
        try service(newMode: newMode) {
            let product = UInt64(count) * UInt64(size)
            guard product <= UInt64(Self.maximumCapacity), !fail else { return 0 }
            return allocate(UInt32(product), zero: true)
        }
    }

    func allocation(_ base: UInt32) throws -> Allocation { try service { try live(base) } }
    func capacity(_ base: UInt32) throws -> UInt32 { try service { try live(base).capacity } }
    func bytes(_ base: UInt32) throws -> [UInt8] {
        try service {
            let allocation = try live(base)
            return Array(UnsafeBufferPointer(start: heap.lookupBytes(base, count: allocation.capacity)!,
                                             count: Int(allocation.capacity)))
        }
    }

    // Same service and exact ownership validation as liveSnapshot, without
    // constructing capacity-byte snapshots that the binding caller discards.
    func validateLiveOwnership() throws {
        try service {
            for base in owned.keys { _ = try live(base) }
        }
    }

    // Complete capacity bytes for the live ledger; retired records retain their
    // own allocation identities, so address reuse cannot overwrite history.
    func liveSnapshot() throws -> [RetiredAllocation] {
        try service {
            try owned.keys.sorted().map { base in
                let allocation = try live(base)
                return .init(allocation: allocation,
                    bytes: Array(UnsafeBufferPointer(start: heap.lookupBytes(base, count: allocation.capacity)!,
                                                    count: Int(allocation.capacity))))
            }
        }
    }

    private func retire(_ allocation: Allocation) {
        retired.append(.init(allocation: allocation,
            bytes: Array(UnsafeBufferPointer(start: heap.lookupBytes(allocation.base, count: allocation.capacity)!,
                                            count: Int(allocation.capacity)))))
        owned.removeValue(forKey: allocation.base)
        heap.free(allocation.base)
    }

    func free(_ base: UInt32) throws {
        try service { if base != 0 { retire(try live(base)) } }
    }

    func realloc(_ base: UInt32, _ requested: UInt32, newMode: UInt32 = 0,
                 policy: ResizePolicy = .automatic) throws -> UInt32 {
        try service(newMode: newMode) {
            if base == 0 { return policy == .fail ? 0 : allocate(requested, zero: false) }
            let old = try live(base)
            if requested == 0 { retire(old); return 0 }
            guard let capacity = rounded(requested), policy != .fail else { return 0 }
            if capacity == old.capacity && policy != .move {
                owned[base] = .init(base: base, requested: requested, capacity: capacity, identity: old.identity, generation: old.generation)
                return base
            }
            let end = UInt64(base) + UInt64(capacity) + allocationGap
            guard end < UInt64(UInt32.max) else { return 0 }
            if policy != .move && heap.resizeInPlace(token: base, expectedIdentity: old.identity,
                                                    expectedCount: old.capacity, count: capacity) {
                if capacity > old.capacity {
                    let tail = heap.lookupBytes(base + old.capacity, count: capacity - old.capacity)!
                    for index in 0..<Int(capacity - old.capacity) {
                        tail[index] = growthByte(offset: index, generation: old.generation)
                    }
                }
                owned[base] = .init(base: base, requested: requested, capacity: capacity, identity: old.identity, generation: old.generation)
                nextBase = max(nextBase, UInt32(end))
                return base
            }
            if policy == .inPlace { return 0 }
            let replacement = allocate(requested, zero: false)
            guard replacement != 0 else { return 0 }
            let prefix = min(old.capacity, capacity)
            heap.lookupBytes(replacement, count: prefix)!.update(from: heap.lookupBytes(base, count: prefix)!, count: Int(prefix))
            retire(old)
            return replacement
        }
    }

    // Explicit teardown cannot silently free a reused foreign allocation.
    func teardown() throws {
        try service {
            let allocations = try owned.keys.sorted().map { try live($0) }
            for allocation in allocations { retire(allocation) }
        }
    }
}
