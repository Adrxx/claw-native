import Foundation

var checks = 0
func check(_ condition: @autoclosure () -> Bool, _ label: String) {
    checks += 1
    if !condition() { FileHandle.standardError.write(Data("FAIL \(label)\n".utf8)); exit(1) }
}
func call(_ slot: UInt32, _ arguments: [UInt32] = []) -> ClawCall {
    var result = ClawCall()
    result.function = slot; result.argumentCount = UInt32(arguments.count)
    result.stackPointer = UInt32(CLAW_STACK_TOP) - 0x100
    withUnsafeMutableBytes(of: &result.arguments) { target in
        arguments.withUnsafeBytes { target.copyMemory(from: $0) }
    }
    return result
}
let imports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map { ($0.element, UInt32(0x710000 + $0.offset * 4)) })
let lockImports = Dictionary(uniqueKeysWithValues: ClawNativeMfcLocks.importSlots.sorted().enumerated().map { ($0.element, UInt32(0x710100 + $0.offset * 4)) })
func memory(_ host: ClawNativeCanonicalHost) throws -> ClawNativeMfcMemory {
    try ClawNativeMfcMemory(host: host, sha256: ClawNativeMfcMemory.imageHash, importTargets: imports)
}
func locks(_ host: ClawNativeCanonicalHost) throws -> ClawNativeMfcLocks {
    try ClawNativeMfcLocks(host: host, sha256: ClawNativeMfcLocks.imageHash,
                         initialBytes: [UInt8](repeating: 0x5a, count: Int(ClawNativeMfcLocks.imageCount)), importTargets: lockImports)
}

// Containment is a borrowed observation, never permission to own an interior
// token or read source-invisible legacy padding. Identities do not pin bytes.
do {
    let heap = ClawTokenHeap(), token: UInt32 = 0x63000000
    let original = heap.storeBytes(token: token, count: 13)
    original[12] = 0x7b
    let identity = heap.allocationIdentity(at: token, count: 13)!
    check(heap.containingAllocationIdentity(at: token + 4, count: 9) === identity, "interior extent")
    check(heap.containingAllocationIdentity(at: token + 13, count: 0) === identity, "empty source end")
    check(heap.containingAllocationIdentity(at: token + 13, count: 1) == nil, "source padding excluded")
    check(heap.containingAllocationIdentity(at: token - 1, count: 1) == nil, "before allocation excluded")
    check(heap.containingAllocationIdentity(at: UInt32.max, count: UInt32.max) == nil, "overflow excluded")
    check(heap.allocationIdentity(at: token + 4, count: 9) == nil, "exact ownership unchanged")
    check(heap.lookup(token, words: 4) != nil && heap.lookupBytes(token, count: 14) == nil, "word padding view unchanged")
    heap.withStableFreedStorage {
        heap.free(token)
        check(heap.containingAllocationIdentity(at: token, count: 1) == nil, "retired storage has no live identity")
        check(original[12] == 0x7b, "retired source bytes remain stable")
        heap.withStableFreedStorage {
            heap.storeBytes(token: token, count: 13)[12] = 0x9c
            check(heap.containingAllocationIdentity(at: token, count: 13) !== identity, "same token new allocation identity")
            check(original[12] == 0x7b, "nested retention remains stable")
        }
        check(original[12] == 0x7b, "outer retention outlives nested scope")
    }
    check(heap.lookupBytes(token, count: 13)![12] == 0x9c, "new allocation survives scope")
    let padded = heap.allocate(bytes: 0x168)
    check(heap.lookup(padded, words: 128) != nil, "legacy large padding remains")
    check(heap.containingAllocationIdentity(at: padded + 0x168, count: 1) == nil, "legacy large padding excluded from identity")
}

// Interior manager and IAT records remain legitimate borrowed storage.
do {
    let heap = ClawTokenHeap()
    let bound = ClawNativeCanonicalHost(heap: heap)
    let slot: UInt32 = 0x5469d8, base: UInt32 = 0x63000000
    heap.storeBytes(token: slot - 4, count: 12).update(repeating: 0x7a, count: 12)
    heap.lookup(slot, words: 1)![0] = imports[slot]!
    heap.storeBytes(token: base, count: 0x39).update(repeating: 0x4b, count: 0x39)
    var owner: ClawNativeMfcMemory? = try memory(bound)
    try owner!.registerManager(base + 4)
    check(owner!.managerBytes[String(base + 4)] == [UInt8](repeating: 0x4b, count: 0x34), "borrowed interior manager snapshot")
    for slot in [UInt32(0x546aa4), 0x546aac, 0x546a9c, 0x546aa0] {
        check(owner!.service(call(slot, [base + 4 + 0x1c])) == 0, "borrowed section normal service")
    }
    check(owner!.service(call(imports[0x5469d8]!, [0])) == 0, "borrowed interior IAT normal service")
    owner = nil
    check(heap.lookupBytes(base, count: 0x39)![0] == 0x4b, "borrowed manager owner lifetime")
    check(heap.lookupBytes(slot - 4, count: 12)![0] == 0x7a, "borrowed IAT owner lifetime")
}
// A word-view import that extends into padding must be rejected atomically.
do {
    let heap = ClawTokenHeap(), slot: UInt32 = 0x5469d8
    heap.storeBytes(token: slot - 4, count: 5)
    heap.lookup(slot, words: 1)![0] = imports[slot]!
    var rejected = false
    do { _ = try memory(ClawNativeCanonicalHost(heap: heap)) } catch { rejected = true }
    check(rejected && heap.lookupBytes(0x546aa8, count: 1) == nil, "padding import rejected before ownership changes")
}

// Actual external heap.free/store sequences, including allocator ABA reuse.
// Retained mode proves the same guards independently of malloc policy; reuse
// mode requires observed pointer reuse in optimized builds, never guesses it.
let requireReuse = CommandLine.arguments.contains("--require-pointer-reuse")
var pointerReuses = 0
func replace(_ heap: ClawTokenHeap, _ token: UInt32, _ size: UInt32, seekReuse: Bool) -> Bool {
    let oldPointer = UInt(bitPattern: heap.lookupBytes(token, count: size)!)
    let oldIdentity = heap.containingAllocationIdentity(at: token, count: size)!
    var reused = false
    for _ in 0..<(seekReuse ? 8192 : 1) {
        heap.free(token)
        let pointer = heap.storeBytes(token: token, count: size)
        pointer.update(repeating: 0xa7, count: Int(size))
        reused = UInt(bitPattern: pointer) == oldPointer
        if reused { break }
    }
    check(heap.containingAllocationIdentity(at: token, count: size) !== oldIdentity, "replacement has distinct allocation identity")
    if reused { pointerReuses += 1 }
    if seekReuse && requireReuse { check(reused, "optimized actual native pointer reuse") }
    return reused
}
for retained in [true, false] {
    for kind in 0..<7 {
        let heap = ClawTokenHeap(), host: ClawNativeCanonicalHost
        host = ClawNativeCanonicalHost(heap: heap)
        let borrowedBase: UInt32 = 0x63000000, borrowedSlot: UInt32 = 0x5469d8
        if kind == 4 {
            heap.storeBytes(token: borrowedBase, count: 0x39).update(repeating: 0x4b, count: 0x39)
        }
        if kind == 6 {
            heap.storeBytes(token: borrowedSlot - 4, count: 12)
            heap.lookup(borrowedSlot, words: 1)![0] = imports[borrowedSlot]!
        }
        var owner: ClawNativeMfcMemory? = try memory(host)
        var token: UInt32 = 0, size: UInt32 = 0, serviceSlot: UInt32 = 0, args: [UInt32] = []
        switch kind {
        case 0:
            token = try owner!.createManager(); size = 0x34
            check(owner!.service(call(0x546aa4, [token + 0x1c])) == 0, "initialize owned manager")
            serviceSlot = 0x546aac; args = [token + 0x1c]
        case 1, 2:
            token = owner!.service(call(0x546aa8, [0x40, 13]))!; size = 13
            serviceSlot = kind == 1 ? 0x5469d8 : 0x546a80
            args = kind == 1 ? [token] : [token, 29, 0x42]
        case 3:
            let handle = owner!.service(call(0x546b1c, [0x2042, 17]))!
            token = owner!.blocks[0].data; size = 17; serviceSlot = 0x5469c4; args = [handle]
        case 4:
            token = borrowedBase; size = 0x39
            try owner!.registerManager(token + 4)
            check(owner!.service(call(0x546aa4, [token + 4 + 0x1c])) == 0, "initialize interior borrowed manager")
            serviceSlot = 0x546aac; args = [token + 4 + 0x1c]
        case 5:
            token = 0x546aa8; size = 4; serviceSlot = token; args = [0x40, 13]
        default:
            token = borrowedSlot - 4; size = 12; serviceSlot = borrowedSlot; args = [0]
        }
        func exercise() {
            _ = replace(heap, token, size, seekReuse: !retained)
            if kind == 5 { heap.lookup(serviceSlot, words: 1)![0] = imports[serviceSlot]! }
            if kind == 6 { heap.lookup(serviceSlot, words: 1)![0] = imports[serviceSlot]! }
            let replacement = heap.containingAllocationIdentity(at: token, count: size)!
            check(owner!.managerBytes.isEmpty && owner!.blockBytes.isEmpty && owner!.localBytes.isEmpty, "stale record snapshots excluded")
            check(host.fault == nil, "snapshot does not fabricate a source fault")
            check(owner!.service(call(imports[serviceSlot]!, args)) == nil, "stale storage service rejected")
            check(host.fault?.code == UInt32(CLAW_FAULT_HALT) && host.fault?.address == serviceSlot, "existing physical boundary failure")
            owner = nil
            check(heap.containingAllocationIdentity(at: token, count: size) === replacement, "destructor preserves replacement allocation")
            check(heap.lookupBytes(token, count: size) != nil, "replacement remains readable")
        }
        if retained { heap.withStableFreedStorage { exercise() } } else { exercise() }
    }
    for image in [true, false] {
        let heap = ClawTokenHeap(), host: ClawNativeCanonicalHost
        host = ClawNativeCanonicalHost(heap: heap)
        var owner: ClawNativeMfcLocks? = try locks(host)
        try owner!.adoptInitializedSection(ClawNativeMfcLocks.master)
        let token = image ? ClawNativeMfcLocks.imageBase : UInt32(0x546aac)
        let size = image ? ClawNativeMfcLocks.imageCount : 4
        func exercise() {
            _ = replace(heap, token, size, seekReuse: !retained)
            if !image { heap.lookup(token, words: 1)![0] = lockImports[token]! }
            let replacement = heap.containingAllocationIdentity(at: token, count: size)!
            check(owner!.imageBytes.isEmpty == image, "lock image snapshot rejects stale mapping")
            check(host.fault == nil, "lock snapshot has no source fault")
            check(owner!.service(call(lockImports[0x546aac]!, [ClawNativeMfcLocks.master])) == nil, "lock stale image or IAT rejects service")
            check(host.fault?.code == UInt32(CLAW_FAULT_HALT), "lock physical failure contract")
            owner = nil
            check(heap.containingAllocationIdentity(at: token, count: size) === replacement, "lock destructor preserves replacement")
        }
        if retained { heap.withStableFreedStorage { exercise() } } else { exercise() }
    }
}

// Missing spans are safe to observe. The hook is an explicit mutation boundary,
// so bindings must be revalidated after it, before physical service effects.
for which in 0..<4 {
    let heap = ClawTokenHeap(), host: ClawNativeCanonicalHost
    host = ClawNativeCanonicalHost(heap: heap)
    if which < 2 {
        let owner = try memory(host), manager = try owner.createManager()
        if which == 0 {
            heap.free(manager)
            check(owner.managerBytes.isEmpty && host.fault == nil, "freed manager snapshot safe")
        } else {
            owner.beforeService = { _, _ in heap.free(0x546aa8); heap.store(token: 0x546aa8, words: 1)[0] = imports[0x546aa8]! }
            check(owner.service(call(0x546aa8, [0x40, 13])) == nil && owner.localPointers.isEmpty, "post-hook IAT identity checked")
        }
    } else {
        let owner = try locks(host)
        if which == 2 {
            heap.free(ClawNativeMfcLocks.imageBase)
            check(owner.imageBytes.isEmpty && host.fault == nil, "freed lock image snapshot safe")
        } else {
            owner.beforeService = { _, _, _ in heap.free(ClawNativeMfcLocks.imageBase); heap.storeBytes(token: ClawNativeMfcLocks.imageBase, count: ClawNativeMfcLocks.imageCount) }
            check(owner.service(call(0x546abc)) == nil, "post-hook image identity checked")
        }
    }
}
// Allocation-failure injection is also a callback: it cannot invalidate a
// resize source and make the subsequent copy read replacement storage.
for global in [true, false] {
    let heap = ClawTokenHeap(), host: ClawNativeCanonicalHost
    host = ClawNativeCanonicalHost(heap: heap)
    let owner = try memory(host)
    let handle = owner.service(call(global ? 0x546b1c : 0x546aa8, [global ? 0x2042 : 0x40, 13]))!
    let token = global ? owner.blocks[0].data : handle
    owner.failAllocation = { _ in
        heap.free(token)
        heap.storeBytes(token: token, count: 13).update(repeating: 0xa7, count: 13)
        return false
    }
    check(owner.service(call(global ? 0x546a88 : 0x546a80, [handle, 29, global ? 0x2042 : 0x42])) == nil, "resize revalidates after allocation callback")
    check(heap.lookupBytes(token, count: 13)![12] == 0xa7, "invalidated resize preserves replacement bytes")
    check(owner.blockBytes.isEmpty && owner.localBytes.isEmpty, "invalidated resize snapshot safe")
}
print("PASS native MFC ownership identity: \(checks) checks, \(pointerReuses) actual pointer reuses, 18 replacement scenarios")
