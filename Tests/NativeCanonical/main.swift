import Foundation

var checks = 0
func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    checks += 1
    guard condition() else { fatalError(message) }
}
func call(_ function: UInt32, receiver: UInt32 = 0, arguments: [UInt32] = [], stackPointer: UInt32 = 0) -> ClawCall {
    precondition(arguments.count <= 16)
    var value = ClawCall()
    value.function = function; value.receiver = receiver; value.argumentCount = UInt32(arguments.count)
    value.stackPointer = stackPointer
    withUnsafeMutableBytes(of: &value.arguments) { target in
        arguments.withUnsafeBytes { source in
            UnsafeMutableRawBufferPointer(rebasing: target.prefix(source.count)).copyMemory(from: source)
        }
    }
    return value
}
func arguments(_ value: ClawCall) -> [UInt32] {
    precondition(value.argumentCount <= 16)
    return withUnsafeBytes(of: value.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(value.argumentCount))) }
}
func put(_ heap: ClawTokenHeap, _ token: UInt32, _ offset: UInt32, _ value: UInt32) {
    heap.lookup(token + offset, words: 1)!.pointee = value
}
func get(_ heap: ClawTokenHeap, _ token: UInt32, _ offset: UInt32) -> UInt32 {
    heap.lookup(token + offset, words: 1)!.pointee
}
func object(_ heap: ClawTokenHeap, phase: UInt32) -> (UInt32, UInt32) {
    let actor = heap.allocate(bytes: 0x1b4), state = heap.allocate(bytes: 0xc0)
    put(heap, actor, 0x6c, state); put(heap, state, 0x1c, phase)
    return (actor, state)
}

// Exact adapter for one recovered native animation dependency. It deliberately
// has no catch-all legacy dispatch. This test exercises the updater's real
// pending-delay branch; it does not assert full animation/resource composition.
final class AnimationDependency {
    var calls: [ClawCall] = []
    var returnedEAX: UInt32?
    func invoke(_ owner: ClawNativeCanonicalHost, _ request: ClawCall) -> UInt32? {
        calls.append(request)
        guard request.function == 0x4c82a0 else { return nil }
        guard request.argumentCount == 1, request.receiver2 == 0,
              request.x87ArgumentCount == 0, request.stackPointer == 0 else {
            owner.fail(UInt32(CLAW_FAULT_ABI), at: request.function, diagnostic: .unsupportedABI)
            return nil
        }
        var host = ClawSceneActorHost()
        host.context = Unmanaged.passUnretained(owner).toOpaque()
        host.lookup = { user, token, words in
            guard let user else { return nil }
            let owner = Unmanaged<ClawNativeCanonicalHost>.fromOpaque(user).takeUnretainedValue()
            guard token & 3 == 0, words <= UInt32.max / 4 else {
                owner.fail(UInt32(CLAW_FAULT_MEMORY), at: token, diagnostic: .invalidMemorySpan)
                return nil
            }
            return owner.bytes(token, count: words * 4).map {
                UnsafeMutableRawPointer($0).assumingMemoryBound(to: UInt32.self)
            }
        }
        host.call = { user, request in
            guard let user else { return 0 }
            let owner = Unmanaged<ClawNativeCanonicalHost>.fromOpaque(user).takeUnretainedValue()
            owner.fail(UInt32(CLAW_FAULT_HALT), at: request.function, diagnostic: .missingDependency)
            return 0
        }
        var globals = ClawActorAnimationGlobals(), nativeFault: UInt32 = 0, eax: UInt32 = 0
        let accepted = claw_actor_animation_entry(request.function, request.receiver, arguments(request)[0],
            0, &globals, host, &nativeFault, &eax)
        guard accepted == 1, nativeFault == 0, owner.fault == nil else {
            owner.fail(UInt32(CLAW_FAULT_HOST), at: request.function)
            return nil
        }
        returnedEAX = eax
        return eax
    }
}

// Actual admitted AniCycle writes through the same heap seen by the legacy
// word view, then invokes the recovered cycle dependency with its original ABI.
do {
    let heap = ClawTokenHeap(), animation = AnimationDependency()
    let owner = ClawNativeCanonicalHost(heap: heap, dependency: animation.invoke)
    let (actor, state) = object(heap, phase: 0)
    put(heap, actor, 0x190, heap.allocate(bytes: 20)) // Existing animation name/sequence, no name lookup.
    put(heap, actor, 8, 0x80)
    let first = owner.invoke(call(0x4918b0, arguments: [actor]))
    check(first.completed && first.eax == 1 && first.fault == nil, "AniCycle initialization completes")
    check(get(heap, actor, 8) == 0x81 && get(heap, state, 0x1c) == 5, "canonical writes alias scene words")
    check(owner.bytes(actor + 8, count: 1)!.pointee == 0x81, "canonical write visible through byte alias")
    check(animation.calls.isEmpty, "existing sequence bypasses name service")
    heap.store(token: 0x5430c4, words: 1).pointee = 1
    put(heap, actor, 0x188 + 0x14, 3)
    put(heap, actor, 0x188 + 0x18, 1)
    put(heap, actor, 0x188 + 0x24, 0) // Meaningful original dependency EAX is zero.
    let second = owner.invoke(call(0x4918b0, arguments: [actor]))
    check(second.completed && second.eax == 1 && second.fault == nil, "AniCycle cycle callback completes")
    check(get(heap, actor, 0x188 + 0x14) == 2, "native animation updater decrements actual shared delay")
    check(animation.returnedEAX == 0, "dependency zero is valid and not a fault")
    check(animation.calls.count == 1, "one exact dependency dispatch")
    let request = animation.calls[0]
    check(request.function == 0x4c82a0 && request.receiver == actor + 0x188, "original cycle address and ECX")
    check(arguments(request) == [1] && request.receiver2 == 0 && request.x87ArgumentCount == 0 && request.stackPointer == 0,
          "complete cycle dependency ABI")
}

// Admitted application-state factory default branch has no dependency calls,
// writes through the application alias, and returns original EAX zero.
do {
    let heap = ClawTokenHeap(), ownerToken = heap.allocate(bytes: 0xa4), app = heap.allocate(bytes: 0x248)
    put(heap, ownerToken, 8, app); put(heap, app, 0x244, 99)
    let owner = ClawNativeCanonicalHost(heap: heap)
    let result = owner.invoke(call(0x428c40, receiver: ownerToken, arguments: [0, 0, 1, 0]))
    check(result.completed && result.eax == 0 && result.fault == nil, "original zero is successful completion")
    check(get(heap, app, 0x244) == 0, "zero-return factory branch executes native write")
}

// Three source wrappers now track the exact PUSH/CALL child entry. Both the
// wrapper and FloorSpike execute natively; no dependency stand-in runs here.
do {
    let heap = ClawTokenHeap()
    let (actor, _) = object(heap, phase: 1234)
    let owner = ClawNativeCanonicalHost(heap: heap)
    let leaf = owner.invoke(call(0x461d50, arguments: [actor]))
    check(leaf.completed && leaf.eax == 1 && leaf.fault == nil, "actual FloorSpike pure branch")
    heap.store(token: 0x537b8c, words: 1).pointee = 0
    for (function, selector): (UInt32, UInt32) in [(0x461fe0, 2), (0x462000, 3), (0x462020, 4)] {
        let nested = owner.invoke(call(function, arguments: [actor]))
        check(nested.completed && nested.eax == 0 && nested.fault == nil, "native wrapper and native child complete at tracked frames")
        check(get(heap, 0x537b8c, 0) == selector, "real wrapper selector write remains visible after child completion")
    }
}

// Missing service stops AniCycle before its following state write. An original
// zero remains separate from this host-side halt, and the first address sticks.
do {
    let heap = ClawTokenHeap(), owner = ClawNativeCanonicalHost(heap: heap)
    let (actor, state) = object(heap, phase: 0)
    let result = owner.invoke(call(0x4918b0, arguments: [actor]))
    check(!result.completed && result.eax == nil, "missing dependency cannot masquerade as original zero")
    check(result.fault?.code == UInt32(CLAW_FAULT_HALT) && result.fault?.address == 0x4c79e0 &&
          result.fault?.diagnostic == .missingDependency, "missing animation-name dependency halts at exact address")
    check(get(heap, state, 0x1c) == 0 && get(heap, actor, 8) == 1, "native halts after pre-call write")
    check(owner.invoke(call(0xdeadbeef)).fault == result.fault, "missing-dependency fault stays sticky")
}

// The dependency envelope retains every field and all sixteen stack words.
// This probes the transport API directly, not a recovered-family replacement.
do {
    let heap = ClawTokenHeap()
    var observed: ClawCall?
    let owner = ClawNativeCanonicalHost(heap: heap) { _, value in observed = value; return 0 }
    var value = call(0x123456, receiver: 0x11223344, arguments: Array(0..<16).map(UInt32.init))
    value.receiver2 = 0xaabbccdd; value.stackPointer = 0x2007000
    value.x87ArgumentCount = 1; value.x87Argument = -2.75
    check(owner.callNativeDependency(value) == 0 && owner.fault == nil, "full dependency transport accepts original zero")
    check(observed?.function == value.function && observed?.receiver == value.receiver && observed?.receiver2 == value.receiver2,
          "dependency address and both registers preserved")
    check(observed?.stackPointer == value.stackPointer && observed?.x87ArgumentCount == 1 && observed?.x87Argument == -2.75,
          "dependency stack and x87 preserved")
    check(arguments(observed!) == arguments(value), "sixteen dependency words preserved")
}

for invalid in 0..<6 {
    let heap = ClawTokenHeap(), owner = ClawNativeCanonicalHost(heap: heap)
    var value = call(0x4918b0, arguments: [0])
    if invalid == 0 { value.function = 0xdeadbeef }
    if invalid == 1 { value.argumentCount = 0 }
    if invalid == 2 { value.argumentCount = 17 }
    if invalid == 3 { value.receiver2 = 1 }
    if invalid == 4 { value.x87ArgumentCount = 1; value.x87Argument = 2.5 }
    if invalid == 5 { value.stackPointer = 0x02007fff }
    let result = owner.invoke(value)
    check(!result.completed && result.eax == nil, "invalid canonical call has no EAX")
    check(result.fault?.address == value.function, "invalid canonical address diagnostic")
    check(result.fault?.code == UInt32(invalid == 0 ? CLAW_CANONICAL_FAULT_UNKNOWN_ADDRESS : CLAW_FAULT_ABI),
          "unknown address distinct from unsupported canonical ABI")
    check(result.fault?.diagnostic == (invalid == 0 ? .unknownEntry :
          invalid == 5 ? .invalidStackFrame : .unsupportedABI), "Swift ABI diagnostic")
}

do {
    let heap = ClawTokenHeap(), owner = ClawNativeCanonicalHost(heap: heap)
    let token = heap.allocate(bytes: 7), pointer = owner.bytes(token + 1, count: 6)!
    pointer.pointee = 0x7f
    check(heap.lookupBytes(token, count: 7)!.advanced(by: 1).pointee == 0x7f, "unaligned bytes share allocation")
    check(owner.bytes(token, count: 8) == nil, "allocation padding inaccessible")
    check(owner.fault?.code == UInt32(CLAW_FAULT_MEMORY) && owner.fault?.address == token, "exact memory fault")
    let first = owner.fault
    check(owner.invoke(call(0xdeadbeef)).fault == first, "memory fault survives later dispatch")
    check(owner.callNativeDependency(call(0x123456)) == nil && owner.fault == first, "fault prevents dependency work")
}

// A dependency's own fault wins over its nominal return or subsequent nil.
for suppliedReturn in [UInt32(0), nil] {
    let heap = ClawTokenHeap()
    let owner = ClawNativeCanonicalHost(heap: heap) { owner, _ in
        owner.fail(UInt32(CLAW_FAULT_MEMORY), at: 0x12345, diagnostic: .invalidMemorySpan)
        return suppliedReturn
    }
    let (actor, _) = object(heap, phase: 0)
    let result = owner.invoke(call(0x4918b0, arguments: [actor]))
    check(!result.completed && result.eax == nil && result.fault?.code == UInt32(CLAW_FAULT_MEMORY) &&
          result.fault?.address == 0x12345, "dependency fault propagates through real canonical callback")
}

// Test-only synthetic entries use the same generated dispatcher as the real
// registry; the script includes them only in its temporary test header.
let graph: UInt32 = 0x7f001000, bounds: UInt32 = 0x7f001020
let stackBase: UInt32 = 0x01ff0000, stackEnd: UInt32 = 0x02010000, stackTop: UInt32 = 0x02008000
for anchor: UInt32 in [0, stackTop, stackTop - 0x400, stackBase + 0x400] {
    let heap = ClawTokenHeap(), owner = ClawNativeCanonicalHost(heap: heap)
    let output = heap.allocate(bytes: 1024), resolved = anchor == 0 ? stackTop : anchor
    for _ in 0..<2 {
        let result = owner.invoke(call(graph, arguments: [output, 3, 0, 0], stackPointer: anchor))
        check(result.completed && result.eax == 0xabc00005, "nested descendants mutate exact parent local")
        check(get(heap, output, 12) == resolved && get(heap, output, 8) == resolved - 32,
              "Run frame moves with root; child entry ESP is not decremented twice")
        check(get(heap, output, 0) == resolved - 32, "sibling returns to caller before next descending call")
        check(claw_frame_test_scope_state() == 3, "normal unwind restores entry and budget pointers")
    }
}

// Nonzero is necessary but insufficient: reject every malformed nested frame.
for mode: UInt32 in 1...7 {
    let heap = ClawTokenHeap(), output = heap.allocate(bytes: 1024)
    let owner = ClawNativeCanonicalHost(heap: heap)
    let result = owner.invoke(call(graph, arguments: [output, 1, mode, 0]))
    check(!result.completed && result.eax == nil && result.fault?.code == UInt32(CLAW_FAULT_ABI),
          "zero, reused, upward, overlapping, low, overflow and unaligned frames fail")
    check(result.fault?.address == graph && result.fault?.diagnostic ==
          (mode == 1 ? .recursiveCanonicalCall : .invalidStackFrame), "frame diagnostic retains child identity")
    check(claw_frame_test_restored_after_fault() == 1 && claw_frame_test_scope_state() == 3,
          "nested rejection unwinds without replacing the parent's frame")
}

do {
    let heap = ClawTokenHeap(), output = heap.allocate(bytes: 1024)
    let owner = ClawNativeCanonicalHost(heap: heap)
    let result = owner.invoke(call(graph, arguments: [output, 3, 8, 0]))
    check(!result.completed && result.eax == nil && result.fault?.code == UInt32(CLAW_FAULT_MEMORY) &&
          result.fault?.address == 0x0badf00d, "deep native fault retains original code and address")
    check(claw_frame_test_restored_after_fault() == 1 && claw_frame_test_scope_state() == 3,
          "native failure restores all active entry scopes and shared budget pointer")
    check(owner.invoke(call(graph, arguments: [output, 0, 0, 0])).fault == result.fault, "deep fault remains sticky")
}
do {
    let heap = ClawTokenHeap(), output = heap.allocate(bytes: 1024)
    let owner = ClawNativeCanonicalHost(heap: heap, maximumOperations: 20)
    let leaf = owner.invoke(call(graph, arguments: [output, 0, 0, 0]))
    check(leaf.completed, "individual entry fits the operation budget")
    let result = owner.invoke(call(graph, arguments: [output, 1, 0, 0]))
    check(!result.completed && result.eax == nil && result.fault?.code == UInt32(CLAW_FAULT_BUDGET),
          "siblings share one graph budget instead of resetting per entry")
    check(claw_frame_test_restored_after_fault() == 1 && claw_frame_test_scope_state() == 3,
          "exhausted graph restores pointers without clearing the fault")
}
do {
    let heap = ClawTokenHeap(), output = heap.allocate(bytes: 1024)
    let owner = ClawNativeCanonicalHost(heap: heap)
    let result = owner.invoke(call(graph, arguments: [output, 130, 0, 0]))
    check(result.fault?.code == UInt32(CLAW_FAULT_BUDGET) && result.fault?.diagnostic == .canonicalDepthExceeded,
          "native recursion stops independently of remaining operations and bounded original ESP")
    check(claw_frame_test_scope_state() == 3, "depth guard unwinds all frames")
}

// Positive argument slots are materialized before entry, including at both
// legal extreme entry addresses. This probe has no below-entry locals.
for anchor in [stackBase, stackEnd - 20] {
    let owner = ClawNativeCanonicalHost(heap: ClawTokenHeap())
    let result = owner.invoke(call(bounds, arguments: [0, 0, 0, 0], stackPointer: anchor))
    check(result.completed && result.eax == anchor, "entry argument words fit exact stack bounds")
}
for anchor in [stackBase - 4, stackEnd - 16, stackEnd, UInt32.max - 3, stackTop - 1] {
    let owner = ClawNativeCanonicalHost(heap: ClawTokenHeap())
    let result = owner.invoke(call(bounds, arguments: [0, 0, 0, 0], stackPointer: anchor))
    check(result.fault?.diagnostic == .invalidStackFrame && result.eax == nil, "bad root frame rejected before execution")
}

for token in [stackBase, stackBase - 4, stackEnd - 4] {
    let heap = ClawTokenHeap()
    heap.store(token: token, words: token == stackBase - 4 ? 2 : 1).pointee = 0x1234
    let owner = ClawNativeCanonicalHost(heap: heap)
    let result = owner.invoke(call(bounds, arguments: [0, 0, 0, 0]))
    check(result.fault?.code == UInt32(CLAW_FAULT_MEMORY) && result.fault?.address == stackBase,
          "reserved stack rejects all overlapping heap blocks")
    check(heap.lookup(token, words: 1)!.pointee == 0x1234, "collision does not mutate the existing owner")
}
do {
    let heap = ClawTokenHeap()
    heap.store(token: stackBase - 4, words: 1).pointee = 7
    heap.store(token: stackEnd, words: 1).pointee = 8
    check(!heap.overlaps(stackBase, count: stackEnd - stackBase), "adjacent allocations do not overlap")
    let owner = ClawNativeCanonicalHost(heap: heap)
    check(owner.invoke(call(bounds, arguments: [0, 0, 0, 0])).completed, "adjacent blocks permit a stack scope")
}
do {
    let heap = ClawTokenHeap(), output = heap.allocate(bytes: 1024)
    heap.store(token: stackBase - 4, words: 1).pointee = 0x1234
    let owner = ClawNativeCanonicalHost(heap: heap)
    let result = owner.invoke(call(graph, arguments: [output, 0, 0, 0], stackPointer: stackBase))
    check(result.fault?.code == UInt32(CLAW_FAULT_MEMORY) && result.fault?.address == stackBase - 4,
          "automatic below the bounded stack cannot alias an adjacent heap block")
    check(heap.lookup(stackBase - 4, words: 1)!.pointee == 0x1234, "invalid local leaves adjacent heap untouched")
    check(claw_frame_test_scope_state() == 3, "automatic bounds failure restores scope")
}

do {
    let heap = ClawTokenHeap(), output = heap.allocate(bytes: 1024)
    var escapedToken: UInt32 = 0
    let owner = ClawNativeCanonicalHost(heap: heap) { owner, request in
        guard request.function == 0x7f002000 else { return nil }
        let frame = arguments(request)[0]
        escapedToken = frame + 5
        check(owner.bytes(escapedToken, count: 3) != nil, "unaligned physical argument aliases are live in a dependency")
        check(owner.bytes(frame - 68, count: 4)!.pointee == 0, "new root clears the previous graph's local bytes")
        check(owner.bytes(stackBase, count: stackEnd - stackBase) != nil, "entire bounded stack belongs to active graph")
        check(owner.bytes(stackEnd, count: 0) != nil, "empty span at active stack end is valid")
        return 0
    }
    check(owner.invoke(call(graph, arguments: [output, 2, 0, 0])).completed, "populate prior graph locals")
    check(owner.invoke(call(bounds, arguments: [0, 0, 0x7f002000, 0])).eax == 0, "dependency original zero is completion")
    check(claw_frame_test_scope_state() == 3, "outer graph cleanup after borrowed alias")
    check(owner.bytes(escapedToken, count: 1) == nil && owner.fault?.code == UInt32(CLAW_FAULT_MEMORY),
          "escaped numeric alias cannot resolve outside its graph")
}
for (token, count): (UInt32, UInt32) in [(stackBase - 1, 2), (stackEnd - 1, 2), (stackEnd, 1), (stackBase, UInt32.max)] {
    let owner = ClawNativeCanonicalHost(heap: ClawTokenHeap()) { owner, _ in
        check(owner.bytes(token, count: count) == nil, "cross-boundary stack span rejected")
        return 0
    }
    let result = owner.invoke(call(bounds, arguments: [0, 0, 0x7f002000, 0]))
    check(result.fault?.code == UInt32(CLAW_FAULT_MEMORY) && result.fault?.address == token,
          "exact invalid span address survives dependency return")
}
do {
    let heap = ClawTokenHeap()
    let owner = ClawNativeCanonicalHost(heap: heap) { owner, _ in
        heap.store(token: stackBase, words: 1).pointee = 9
        check(owner.bytes(stackBase, count: 1) == nil, "a dependency cannot introduce a shadow heap owner")
        return 0
    }
    check(owner.invoke(call(bounds, arguments: [0, 0, 0x7f002000, 0])).fault?.code == UInt32(CLAW_FAULT_MEMORY),
          "late overlap is diagnosed while stack is active")
}

// A noncanonical source caller owns the same stack through multiple admitted
// descendants. Its borrowed locals and incoming arguments retain their bytes.
do {
    let heap = ClawTokenHeap(), owner = ClawNativeCanonicalHost(heap: heap)
    let output = heap.allocate(bytes: 1024)
    let value = owner.withSourceStackFrame(entryStackPointer: stackTop,
        arguments: [0x11223344, 0x55667788], at: 0x425730) {
        let local = owner.bytes(stackTop - 128, count: 7)!
        for index in 0..<7 { local[index] = UInt8(0xa0 + index) }
        for _ in 0..<2 {
            let child = owner.invoke(call(graph, arguments: [output, 1, 0, 0], stackPointer: stackTop - 256))
            check(child.completed && child.eax == 0xabc00003, "source scope permits descending canonical descendants")
            check(Array(UnsafeBufferPointer(start: local, count: 7)) == Array(0xa0...0xa6).map(UInt8.init),
                  "sibling canonical roots cannot clear borrowed source locals")
            check(owner.bytes(stackTop + 4, count: 4)!.withMemoryRebound(to: UInt32.self, capacity: 1) { $0.pointee } == 0x11223344,
                  "source incoming arguments remain materialized")
        }
        return UInt32(123)
    }
    check(value == 123 && owner.fault == nil, "source frame returns its caller value")
    check(claw_frame_test_scope_state() == 3, "source scope restores native frame and budget pointers")
    check(owner.bytes(stackTop - 128, count: 1) == nil, "source-local token invalidates at scope return")
}
for anchor in [UInt32(0), stackBase - 4, stackTop - 1, stackEnd - 4, UInt32.max - 3] {
    let owner = ClawNativeCanonicalHost(heap: ClawTokenHeap())
    var entered = false
    let result = owner.withSourceStackFrame(entryStackPointer: anchor, arguments: [1], at: 0x425730) {
        entered = true
        return 1
    }
    check(result == nil && !entered && owner.fault?.diagnostic == .invalidStackFrame,
          "invalid source frame rejects before entering caller body")
}
do {
    let owner = ClawNativeCanonicalHost(heap: ClawTokenHeap())
    let result = owner.withSourceStackFrame(entryStackPointer: stackTop, arguments: Array(repeating: 0, count: 17),
        at: 0x425730) { 1 }
    check(result == nil && owner.fault?.diagnostic == .invalidStackFrame, "source argument extent is bounded")
}
do {
    let heap = ClawTokenHeap(), output = heap.allocate(bytes: 1024)
    let owner = ClawNativeCanonicalHost(heap: heap, maximumOperations: 10)
    _ = owner.withSourceStackFrame(entryStackPointer: stackTop, arguments: [], at: 0x425730) {
        let first = owner.invoke(call(graph, arguments: [output, 0, 0, 0], stackPointer: stackTop - 256))
        check(first.completed, "first source descendant fits shared budget")
        let second = owner.invoke(call(graph, arguments: [output, 0, 0, 0], stackPointer: stackTop - 256))
        check(!second.completed && second.fault?.code == UInt32(CLAW_FAULT_BUDGET),
              "source siblings share one operation budget")
    }
    check(claw_frame_test_scope_state() == 3, "source budget failure restores native scope")
}
do {
    let heap = ClawTokenHeap()
    heap.store(token: stackBase, words: 1).pointee = 7
    let owner = ClawNativeCanonicalHost(heap: heap)
    var entered = false
    let result = owner.withSourceStackFrame(entryStackPointer: stackTop, arguments: [], at: 0x425730) {
        entered = true
        return 1
    }
    check(result == nil && !entered && owner.fault?.diagnostic == .invalidMemorySpan,
          "source scope cannot shadow a reserved-stack heap allocation")
}
do {
    let owner = ClawNativeCanonicalHost(heap: ClawTokenHeap())
    _ = owner.withSourceStackFrame(entryStackPointer: stackTop, arguments: [], at: 0x425730) {
        var entered = false
        let nested = owner.withSourceStackFrame(entryStackPointer: stackTop - 64, arguments: [], at: 0x425730) {
            entered = true
            return 1
        }
        check(nested == nil && !entered && owner.fault?.diagnostic == .invalidStackFrame,
              "external source scopes cannot reset an active graph")
    }
}

// Comparison compiler-context transport is not yet an elected app service.
// Reject it before entering canonical source or a physical dependency adapter.
for canonical in [true, false] {
    let heap = ClawTokenHeap()
    var dependencyEntered = false
    let owner = ClawNativeCanonicalHost(heap: heap, dependency: { _, _ in
        dependencyEntered = true
        return 123
    })
    var context = ClawCompilerContext()
    withUnsafeMutablePointer(to: &context) { pointer in
        var request = call(canonical ? 0x7f001000 : 0x7f002000, arguments: canonical ? [0, 0, 0, 0] : [])
        request.compilerContext = pointer
        if canonical {
            check(!owner.invoke(request).completed, "unsupported compiler context cannot enter ordinary canonical source")
        } else {
            check(owner.callNativeDependency(request) == nil, "unsupported compiler context cannot enter ordinary dependency")
        }
        check(owner.fault?.diagnostic == .unsupportedABI && !dependencyEntered,
              "compiler context rejects before borrowed pointer interpretation or service entry")
    }
}

// The source-context ABI is opt-in; current app entries must reject both
// the new borrowed pointer and real-PC channel before interpreting either.
for canonical in [true, false] {
    for pointerChannel in [true, false] {
        let heap = ClawTokenHeap()
        var dependencyEntered = false
        let owner = ClawNativeCanonicalHost(heap: heap, dependency: { _, _ in
            dependencyEntered = true
            return 123
        })
        var context = ClawSourceContext()
        withUnsafeMutablePointer(to: &context) { pointer in
            var request = call(canonical ? 0x7f001000 : 0x7f002000, arguments: canonical ? [0, 0, 0, 0] : [])
            if pointerChannel { request.sourceContext = pointer }
            else { request.sourceReturnPC = 0x50233f }
            if canonical { check(!owner.invoke(request).completed, "unsupported source ABI cannot enter canonical source") }
            else { check(owner.callNativeDependency(request) == nil, "unsupported source ABI cannot enter dependency") }
            check(owner.fault?.diagnostic == .unsupportedABI && !dependencyEntered, "source ABI rejects before service entry")
        }
    }
}

// Tail transport is a host-owned source graph capability. Every ordinary API
// rejects even one tail field before touching a source or physical provider.
for canonical in [true, false] {
    for field in 0..<5 {
        let heap = ClawTokenHeap()
        var effect = false
        let owner = ClawNativeCanonicalHost(heap: heap, dependency: { _, _ in effect = true; return 1 })
        var receipt = ClawSourceDisposition()
        withUnsafeMutablePointer(to: &receipt) { pointer in
            var request = call(canonical ? 0x7f001000 : 0x7f002000, arguments: canonical ? [0,0,0,0] : [])
            switch field {
            case 0: request.sourceTransferVersion = 1
            case 1: request.sourceTransferKind = 1
            case 2: request.sourceTransferSite = 0x401000
            case 3: request.sourceCallerFunction = 0x401000
            default: request.sourceDisposition = pointer
            }
            if canonical { check(!owner.invoke(request).completed, "ordinary canonical rejects tail metadata") }
            else { check(owner.callNativeDependency(request) == nil, "ordinary dependency rejects tail metadata") }
            check(owner.fault?.diagnostic == .unsupportedABI && !effect, "tail rejection precedes effects")
            check(pointer.pointee.disposition == 0, "rejected tail never publishes returned disposition")
        }
    }
}

print("{\"command\":\"native-canonical-host\",\"status\":\"pass\",\"checks\":\(checks),\"nested_canonical\":\"explicit_descending_frames_only\",\"animation_branch\":\"native_pending_delay\"}")
