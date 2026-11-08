import Foundation

var checks = 0
func check(_ condition: @autoclosure () throws -> Bool, _ message: String) rethrows {
    checks += 1
    if try !condition() { fatalError(message) }
}
func rejects(_ message: String, _ body: () throws -> Void) {
    checks += 1
    do { try body(); fatalError(message) } catch {}
}

let heap = ClawTokenHeap()
let memory = ClawNativeCrtMemory(heap: heap)
let zero = try memory.malloc(0)
try check(zero & 15 == 0 && memory.capacity(zero) == 16, "zero malloc is live minimum capacity")
try check(memory.allocation(zero).requested == 0, "zero requested size retained")
try check(memory.bytes(zero).allSatisfy { $0 == 0xcc }, "malloc unspecified-byte policy")
try memory.free(0)
rejects("capacity null rejects") { _ = try memory.capacity(0) }
for size: UInt32 in [1, 15, 16, 17, 31, 32, 33, 127, 128, 129, 479, 480, 481] {
    let base = try memory.malloc(size)
    try check(memory.capacity(base) == (size + 15) & ~15, "rounded capacity")
    try check(memory.allocation(base).requested == size, "requested separate from usable")
    try check(heap.lookupBytes(base, count: memory.capacity(base)) != nil, "all usable bytes physically owned")
    try check(heap.lookupBytes(base, count: memory.capacity(base) + 1) == nil, "capacity bounded")
    rejects("interior capacity rejects") { _ = try memory.capacity(base + 1) }
    rejects("interior free rejects") { try memory.free(base + 1) }
    try memory.free(base)
    rejects("double free rejects") { try memory.free(base) }
}
for (count, size): (UInt32, UInt32) in [(0, .max), (.max, 0), (1, 0), (3, 7), (8, 4)] {
    let base = try memory.calloc(count, size)
    try check(base != 0 && memory.bytes(base).allSatisfy { $0 == 0 }, "calloc zeros rounded capacity")
    try check(memory.allocation(base).requested == count * size, "calloc request product")
}
try check(memory.calloc(.max, .max) == 0, "calloc huge product rejects")
try check(memory.calloc(0x10000, 0x10000) == 0, "historical DWORD overflow outside bounded domain")
try check(memory.malloc(.max) == 0, "malloc excessive request")
try check(memory.malloc(ClawNativeCrtMemory.maximumCapacity + 1) == 0, "bounded maximum")
rejects("new mode unsupported") { _ = try memory.malloc(1, newMode: 1) }
rejects("calloc new mode unsupported") { _ = try memory.calloc(1, 1, newMode: 1) }
let fromNull = try memory.realloc(0, 5)
try check(memory.capacity(fromNull) == 16, "null realloc malloc")
try check(memory.realloc(0, 0) != 0, "null realloc zero follows malloc")

let original = try memory.malloc(17)
let initial = try memory.allocation(original)
let pattern: [UInt8] = (0..<32).map { UInt8($0 * 7 + 1) }
for index in pattern.indices { heap.lookupBytes(original, count: 32)![index] = pattern[index] }
try check(memory.realloc(original, 31) == original, "equal capacity in place")
try check(memory.allocation(original).identity === initial.identity, "equal capacity retains identity")
try check(memory.allocation(original).requested == 31, "equal capacity changes requested")
try check(memory.realloc(original, 65, policy: .inPlace) == original, "in-place growth")
try check(memory.capacity(original) == 80, "in-place capacity grows")
try check(Array(memory.bytes(original).prefix(32)) == pattern, "growth preserves old usable prefix")
try check(memory.bytes(original).suffix(48).allSatisfy { $0 == 0xcc }, "growth explicit tail policy")
try check(memory.allocation(original).identity === initial.identity, "growth identity retained")
try check(memory.realloc(original, 5, policy: .inPlace) == original, "in-place shrink")
try check(memory.bytes(original) == Array(pattern.prefix(16)), "shrink preserves usable prefix")
try check(memory.capacity(original) == 16, "shrink capacity")
let beforeFailure = try memory.allocation(original)
let bytesBeforeFailure = try memory.bytes(original)
let liveRecord = try memory.liveSnapshot().first { $0.allocation.base == original }!
check(liveRecord.bytes == bytesBeforeFailure && liveRecord.allocation.identity === beforeFailure.identity,
      "complete live snapshot carries identity and capacity bytes")
try check(memory.realloc(original, 80, policy: .fail) == 0, "injected failure")
try check(memory.realloc(original, .max) == 0, "overflow failure")
try check(memory.allocation(original).identity === beforeFailure.identity && memory.capacity(original) == beforeFailure.capacity,
          "failure retains identity capacity")
try check(memory.allocation(original).requested == beforeFailure.requested && memory.bytes(original) == bytesBeforeFailure,
          "failure retains requested bytes")
let moved = try memory.realloc(original, 33, policy: .move)
check(moved != original && moved != 0, "forced movement")
try check(memory.allocation(moved).identity !== initial.identity, "move fresh identity")
try check(Array(memory.bytes(moved).prefix(16)) == bytesBeforeFailure, "move copies usable prefix")
try check(memory.bytes(moved).suffix(32).allSatisfy { $0 == 0xcc }, "move tail policy")
rejects("moved base invalid") { _ = try memory.capacity(original) }
check(memory.retired.last!.bytes == bytesBeforeFailure, "retired complete old capacity")
try check(memory.realloc(moved, 0) == 0, "nonnull zero realloc frees")
rejects("zero realloc retires") { _ = try memory.capacity(moved) }

let occupiedHeap = ClawTokenHeap()
occupiedHeap.storeBytes(token: 0x68000000, count: 16).update(repeating: 0x37, count: 16)
let occupied = ClawNativeCrtMemory(heap: occupiedHeap)
try check(occupied.malloc(1) == 0, "collision exhaustion")
check(occupiedHeap.lookupBytes(0x68000000, count: 16)![0] == 0x37, "collision preserves foreign bytes")
rejects("foreign allocation capacity") { _ = try occupied.capacity(0x68000000) }

let blockedHeap = ClawTokenHeap()
let blocked = ClawNativeCrtMemory(heap: blockedHeap)
let blockedBase = try blocked.malloc(1)
blockedHeap.lookupBytes(blockedBase, count: 16)!.update(repeating: 0x39, count: 16)
blockedHeap.storeBytes(token: blockedBase + 16, count: 16).update(repeating: 0x58, count: 16)
let blockedIdentity = try blocked.allocation(blockedBase).identity
try check(blocked.realloc(blockedBase, 17, policy: .inPlace) == 0, "in-place collision fails")
try check(blocked.capacity(blockedBase) == 16 && blocked.allocation(blockedBase).identity === blockedIdentity,
          "collision retains old identity capacity")
try check(blocked.bytes(blockedBase).allSatisfy { $0 == 0x39 }, "collision old bytes preserved")
try check(blocked.realloc(blockedBase, 17) == 0, "move candidate collision failure preserves old")

let automaticHeap = ClawTokenHeap()
let automatic = ClawNativeCrtMemory(heap: automaticHeap)
let automaticBase = try automatic.malloc(17)
automaticHeap.lookupBytes(automaticBase, count: 32)!.update(repeating: 0x91, count: 32)
let neighbor = try automatic.malloc(1)
let automaticMoved = try automatic.realloc(automaticBase, 33)
check(automaticMoved != 0 && automaticMoved != automaticBase, "automatic moves when neighbor blocks growth")
try check(automatic.bytes(automaticMoved).prefix(32).allSatisfy { $0 == 0x91 }, "automatic move preserves old capacity bytes")
try check(automatic.capacity(neighbor) == 16, "automatic move leaves neighbor owned")
let movedShrink = try automatic.realloc(automaticMoved, 1, policy: .move)
try check(automatic.bytes(movedShrink).count == 16 && automatic.bytes(movedShrink).allSatisfy { $0 == 0x91 },
          "forced moving shrink preserves new usable prefix")
let failedIdentity = try automatic.allocation(movedShrink).identity
rejects("unsupported realloc mode") { _ = try automatic.realloc(movedShrink, 2, newMode: 1) }
try check(automatic.allocation(movedShrink).identity === failedIdentity, "unsupported mode leaves owner untouched")
rejects("invalid realloc even on failure") { _ = try automatic.realloc(0x12345678, 1, policy: .fail) }

let high = ClawNativeCrtMemory(heap: ClawTokenHeap(), firstBase: 0xfffffff0)
try check(high.malloc(1) == 0, "allocation token range cannot wrap")
let maximum = try automatic.malloc(ClawNativeCrtMemory.maximumCapacity)
try check(automatic.capacity(maximum) == ClawNativeCrtMemory.maximumCapacity, "maximum bounded allocation supported")
try automatic.free(maximum)

let replacementHeap = ClawTokenHeap()
let replacementOwner = ClawNativeCrtMemory(heap: replacementHeap)
try replacementOwner.validateLiveOwnership()
check(true, "ownership validation accepts an empty ledger")
let replaced = try replacementOwner.malloc(1)
let unrelated = try replacementOwner.malloc(3)
let unrelatedBytes = try replacementOwner.bytes(unrelated)
try replacementOwner.validateLiveOwnership()
try check(replacementOwner.bytes(unrelated) == unrelatedBytes, "ownership validation leaves live bytes unchanged")
replacementHeap.free(replaced)
replacementHeap.storeBytes(token: replaced, count: 16).update(repeating: 0x73, count: 16)
rejects("same-base same-size replacement capacity") { _ = try replacementOwner.capacity(replaced) }
rejects("same-base replacement realloc") { _ = try replacementOwner.realloc(replaced, 32) }
rejects("same-base replacement free") { try replacementOwner.free(replaced) }
rejects("teardown replacement") { try replacementOwner.teardown() }
rejects("snapshot rejects foreign replacement") { _ = try replacementOwner.liveSnapshot() }
rejects("ownership validation rejects replacement with another live allocation") { try replacementOwner.validateLiveOwnership() }
check(replacementHeap.lookupBytes(replaced, count: 16)![0] == 0x73, "foreign replacement survives teardown")
check(replacementOwner.retired.isEmpty, "replacement not captured as owned retired bytes")

let semaphore = DispatchSemaphore(value: 0)
DispatchQueue.global().async {
    do { _ = try memory.capacity(zero); fatalError("foreign thread accepted") }
    catch {}
    do { try memory.validateLiveOwnership(); fatalError("foreign thread validation accepted") }
    catch {}
    semaphore.signal()
}
semaphore.wait()
check(true, "foreign thread rejects")
check(true, "foreign thread ownership validation rejects")
try check(memory.capacity(zero) == 16, "foreign thread leaves valid owner usable")
try memory.teardown()
try check(memory.liveSnapshot().isEmpty, "teardown empties live snapshot")
try memory.validateLiveOwnership()
check(true, "ownership validation accepts a torn-down empty ledger")
rejects("teardown ends live ownership") { _ = try memory.capacity(zero) }
try memory.teardown()
let referenceHeap = ClawTokenHeap()
let reference = ClawNativeCrtMemory(heap: referenceHeap, firstBase: 0x69000000,
                                  storagePolicy: .frozenReferenceV1)
try check(reference.malloc(3, fail: true) == 0, "policy injected failure")
let referenceBase = try reference.malloc(3)
try check(reference.allocation(referenceBase).generation == 1, "failed allocation does not advance generation")
try check(reference.bytes(referenceBase) == (0..<16).map { UInt8(truncatingIfNeeded: $0 * 31 + 19) },
          "frozen policy initial complete capacity bytes")
let referencePrefix = try reference.bytes(referenceBase)
try check(reference.realloc(referenceBase, 17, policy: .inPlace) == referenceBase, "frozen policy in-place growth")
try check(reference.allocation(referenceBase).generation == 1, "in-place generation stable")
try check(reference.bytes(referenceBase).prefix(16).elementsEqual(referencePrefix), "policy in-place prefix")
try check(reference.bytes(referenceBase).suffix(16).elementsEqual((0..<16).map { UInt8(truncatingIfNeeded: $0 * 17 + 1) }),
          "frozen policy growth uses tail-relative offset")
let referenceSecond = try reference.malloc(1)
check(referenceSecond == referenceBase + 32 + 16, "growth advances bump with sixteen-byte gap")
try check(reference.allocation(referenceSecond).generation == 2 && reference.bytes(referenceSecond)[0] == 38,
          "fresh allocation advances generation and initializer")
let referenceThird = try reference.malloc(1)
check(referenceThird == referenceSecond + 16 + 16, "allocation bump includes sixteen-byte gap")
let referenceBeforeMove = try reference.bytes(referenceBase)
let referenceMoved = try reference.realloc(referenceBase, 33, policy: .move)
try check(reference.allocation(referenceMoved).generation == 4, "move receives fresh generation")
try check(reference.bytes(referenceMoved).prefix(32).elementsEqual(referenceBeforeMove), "policy move copies full usable prefix")
try check(reference.bytes(referenceMoved).suffix(16).elementsEqual((32..<48).map { UInt8(truncatingIfNeeded: $0 * 31 + 4 * 19) }),
          "move tail uses full-allocation offset and new generation")
let referenceZero = try reference.calloc(1, 1)
try check(reference.bytes(referenceZero).allSatisfy { $0 == 0 }, "calloc zeros reference policy bytes")
try check(reference.allocation(referenceZero).generation == 5, "calloc retains generation")
try check(reference.malloc(0x10001) == 0, "frozen policy bounded request matches producer")
check(reference.retired.last!.bytes == referenceBeforeMove, "policy retired snapshot complete")
print("{\"command\":\"native-crt-memory\",\"domain\":\"crt-memory-service-v1\",\"status\":\"pass\",\"checks\":\(checks)}")
