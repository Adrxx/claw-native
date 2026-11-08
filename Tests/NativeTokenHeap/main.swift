import Foundation

var checks = 0
func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    checks += 1
    guard condition() else { fatalError(message) }
}

let heap = ClawTokenHeap()
let token = heap.allocate(bytes: 7)
check(token != 0, "small allocation")
let words = heap.lookup(token, words: 2)!
check(words[0] == 0 && words[1] == 0, "legacy storage starts zeroed")
words[0] = 0x12345678
let bytes = heap.lookupBytes(token, count: 7)!
withUnsafeBytes(of: words[0]) { expected in
    check(Array(UnsafeBufferPointer(start: bytes, count: 4)) == Array(expected), "word writes reach byte view")
}
let interior = heap.lookupBytes(token + 1, count: 6)!
check(interior == bytes.advanced(by: 1), "unaligned interior aliases allocation")
interior[0] = 0xab
withUnsafeBytes(of: words[0]) { check($0[1] == 0xab, "byte writes reach word view") }
check(heap.lookup(token + 1, words: 1) == nil, "word lookup still rejects unaligned tokens")
check(heap.lookup(token + 4, words: 1) == words.advanced(by: 1), "word interior remains valid")
check(heap.lookup(token, words: 3) == nil, "word view still bounds storage")
check(heap.lookupBytes(token, count: 8) == nil, "rounding padding hidden")
check(heap.lookupBytes(token + 6, count: 1) != nil, "last logical byte valid")
check(heap.lookupBytes(token + 7, count: 1) == nil, "first padding byte rejected")
check(heap.lookupBytes(token + 7, count: 0) != nil, "empty span at logical end")
check(heap.lookupBytes(token + 8, count: 0) == nil, "empty span beyond logical end rejected")
check(heap.lookupBytes(token - 1, count: 1) == nil, "unknown byte before allocation")
check(heap.lookupBytes(0, count: 0) == nil, "unknown empty span rejected")
check(heap.lookupBytes(token, count: .max) == nil, "huge byte count does not wrap")
check(heap.lookup(token, words: .max) == nil, "huge word count does not wrap")

for (requested, reservedWords) in [(UInt32(0x168), 128), (0x1b4, 128), (0x410, 264), (0x418, 264)] {
    let padded = heap.allocate(bytes: requested)
    check(heap.lookup(padded, words: UInt32(reservedWords)) != nil, "legacy snapshot padding retained")
    check(heap.lookupBytes(padded, count: requested) != nil, "exact requested snapshot extent")
    check(heap.lookupBytes(padded, count: requested + 1) == nil, "snapshot padding excluded from byte view")
    check(heap.lookupBytes(padded + requested, count: 1) == nil, "interior snapshot padding excluded")
    check(heap.lookup(padded + requested, words: 1) != nil, "legacy interior padding retained")
}

let explicit = heap.store(token: 0x1000, words: 2)
check(heap.lookupBytes(0x1001, count: 7) != nil, "explicit block full word extent")
check(heap.lookupBytes(0x1001, count: 8) == nil, "explicit block bounds")
heap.store(token: 0x1008, words: 1)[0] = 99
check(heap.lookupBytes(0x1007, count: 2) == nil, "span cannot cross adjacent blocks")
check(heap.lookup(0x1008, words: 1)![0] == 99, "exact adjacent block wins")
check(heap.lookupBytes(0x1008, count: 4) != nil, "adjacent byte block resolves")
explicit[0] = 123

let image = heap.storeBytes(token: 0x2000, count: 5)
image[4] = 0x7f
check(heap.lookupBytes(0x2000, count: 5) == image, "fixed image span retains exact bytes")
check(heap.lookupBytes(0x2004, count: 1)?.pointee == 0x7f, "fixed image last byte aliases storage")
check(heap.lookupBytes(0x2005, count: 0) != nil, "fixed image logical end permits empty span")
check(heap.lookupBytes(0x2005, count: 1) == nil, "fixed image cannot expose word padding")
check(heap.lookupBytes(0x2008, count: 0) == nil, "fixed image padded end is outside logical span")
check(heap.lookup(0x2000, words: 2) != nil, "fixed image legacy word view retains backing")
check(heap.overlaps(0x2005, count: 1), "fixed image padding still participates in ownership conflicts")
heap.free(0x2000)
check(heap.lookupBytes(0x2000, count: 1) == nil, "fixed image free ends logical ownership")

heap.store(token: 0xfffffff8, words: 1)[0] = 42
check(heap.lookupBytes(0xfffffffb, count: 1) != nil, "high unaligned address")
check(heap.lookupBytes(0xfffffffb, count: 2) == nil, "high address exceeds block")
check(heap.lookupBytes(0xfffffffb, count: 8) == nil, "32-bit end overflow rejected")
check(heap.lookupBytes(.max, count: .max) == nil, "maximum address and count rejected")
check(heap.lookup(0xfffffffc, words: 1) == nil, "high word address bounded")
check(heap.lookup(0xfffffff8, words: .max) == nil, "high word count bounded")

check(heap.allocate(bytes: 0) == 0, "zero allocation rejected")
check(heap.allocate(bytes: (4 << 20) + 1) == 0, "over-limit allocation rejected")
check(heap.allocate(bytes: .max) == 0, "maximum allocation rejected")
let maximum = heap.allocate(bytes: 4 << 20)
check(maximum != 0, "maximum supported allocation")
check(heap.lookupBytes(maximum, count: 4 << 20) != nil, "maximum byte extent")
check(heap.lookupBytes(maximum, count: (4 << 20) + 1) == nil, "maximum byte extent bounded")
heap.free(maximum)
check(heap.lookupBytes(maximum, count: 1) == nil, "freed maximum allocation unavailable")

heap.withStableFreedStorage {
    heap.withStableFreedStorage {
        heap.free(token)
        check(heap.lookupBytes(token, count: 1) == nil, "freed byte identity unavailable immediately")
        check(heap.lookup(token, words: 1) == nil, "freed word identity unavailable immediately")
        check(bytes[1] == 0xab, "cached byte storage remains live")
    }
    words[0] = 0x10203040
    withUnsafeBytes(of: words[0]) { expected in
        check(Array(UnsafeBufferPointer(start: bytes, count: 4)) == Array(expected), "outer scope retains freed byte and word storage")
    }
}
heap.free(token)
heap.free(0x12345678)
heap.free(0x1001)
check(heap.lookup(0x1000, words: 1)![0] == 123, "unknown/interior free preserves owner")
heap.free(0x1000)
check(heap.lookupBytes(0x1000, count: 0) == nil, "freed explicit empty span rejected")
check(heap.lookupBytes(0x1001, count: 1) == nil, "freed explicit interior rejected")
check(heap.lookup(0x1008, words: 1)![0] == 99, "neighbor survives freeing")

let resizing = ClawTokenHeap()
let resizeToken = resizing.allocate(bytes: 7)
let resizeIdentity = resizing.allocationIdentity(at: resizeToken, count: 7)!
let resizeBytes = resizing.lookupBytes(resizeToken, count: 7)!
for index in 0..<7 { resizeBytes[index] = UInt8(index + 1) }
resizing.withStableFreedStorage {
    check(resizing.resizeInPlace(token: resizeToken, expectedIdentity: resizeIdentity, expectedCount: 7, count: 33), "in-place growth")
    check(resizing.allocationIdentity(at: resizeToken, count: 33) === resizeIdentity, "growth preserves identity")
    check(resizing.allocationIdentity(at: resizeToken, count: 7) == nil, "old extent loses authority")
    let grown = resizing.lookupBytes(resizeToken, count: 33)!
    check(Array(UnsafeBufferPointer(start: grown, count: 7)) == Array(1...7), "growth preserves prefix")
    check(Array(UnsafeBufferPointer(start: grown + 7, count: 26)).allSatisfy { $0 == 0 }, "growth zeroes new bytes")
    check(resizeBytes[6] == 7, "old backing retained during graph")
    check(resizing.resizeInPlace(token: resizeToken, expectedIdentity: resizeIdentity, expectedCount: 33, count: 5), "in-place shrink")
    check(resizing.lookupBytes(resizeToken, count: 6) == nil, "shrink bounds exact bytes")
    check(grown[6] == 7, "intermediate backing retained")
}
let nextResizeToken = resizing.allocate(bytes: 4)
check(nextResizeToken >= resizeToken + 36, "growth advances ordinary allocation cursor")
let beforeRejected = Array(UnsafeBufferPointer(start: resizing.lookupBytes(resizeToken, count: 5)!, count: 5))
check(!resizing.resizeInPlace(token: resizeToken, expectedIdentity: resizeIdentity, expectedCount: 5, count: 64), "neighbor overlap rejected")
check(!resizing.resizeInPlace(token: resizeToken, expectedIdentity: resizeIdentity, expectedCount: 33, count: 8), "stale extent rejected")
check(!resizing.resizeInPlace(token: resizeToken + 4, expectedIdentity: resizeIdentity, expectedCount: 1, count: 8), "interior base rejected")
check(!resizing.resizeInPlace(token: resizeToken, expectedIdentity: resizeIdentity, expectedCount: 5, count: 0), "zero resize rejected")
check(!resizing.resizeInPlace(token: resizeToken, expectedIdentity: resizeIdentity, expectedCount: 5, count: .max), "oversized resize rejected")
check(Array(UnsafeBufferPointer(start: resizing.lookupBytes(resizeToken, count: 5)!, count: 5)) == beforeRejected, "failed resize leaves bytes intact")
resizing.free(resizeToken)
resizing.storeBytes(token: resizeToken, count: 5)
check(!resizing.resizeInPlace(token: resizeToken, expectedIdentity: resizeIdentity, expectedCount: 5, count: 8), "reused base rejects retired identity")

let roundingCollision = ClawTokenHeap()
let roundingBase = roundingCollision.allocate(bytes: 4)
let roundingIdentity = roundingCollision.allocationIdentity(at: roundingBase, count: 4)!
roundingCollision.storeBytes(token: roundingBase + 0x18, count: 32)[0] = 0xab
check(roundingCollision.resizeInPlace(token: roundingBase, expectedIdentity: roundingIdentity, expectedCount: 4, count: 17), "growth before unaligned neighbor succeeds")
check(roundingCollision.allocate(bytes: 4) == 0, "rounded cursor collision is exhaustion without trap")
check(roundingCollision.lookupBytes(roundingBase + 0x18, count: 32)?[0] == 0xab, "collision preserves neighboring bytes")

print("{\"command\":\"native-token-heap\",\"status\":\"pass\",\"checks\":\(checks)}")
