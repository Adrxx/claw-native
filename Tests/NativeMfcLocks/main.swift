import Foundation

typealias State = ClawNativeMfcLocks.State
struct ReferenceEvent: Decodable {
    let function: UInt32, target: UInt32, stackPointer: UInt32
    let arguments: [UInt32], before: [State], after: [State]
    let beforeBytes: String, afterBytes: String
    let completed: Bool
}
struct ReferenceStep: Decodable {
    let function: UInt32, frame: UInt32, arguments: [UInt32]
    let completed: Bool, eax: UInt32?, returnStackPointer: UInt32?
    let states: [State], imageBytes: String, eventCount: Int
}
struct Reference: Decodable {
    let name: String, sha256: String, initialBytes: String
    let imports: [String: UInt32], version: UInt32, failAt: Int?, recheck: UInt32?
    let seed: [String: UInt32], steps: [ReferenceStep], events: [ReferenceEvent]
}
func check(_ value: @autoclosure () -> Bool, _ label: String) { precondition(value(), label) }
func decodeHex(_ hex: String) -> [UInt8] {
    check(hex.count % 2 == 0,"hex extent")
    return stride(from: 0, to: hex.count, by: 2).map { offset in
        let start = hex.index(hex.startIndex, offsetBy: offset)
        return UInt8(hex[start..<hex.index(start, offsetBy: 2)], radix: 16)!
    }
}
func call(_ function: UInt32, _ arguments: [UInt32], _ frame: UInt32) -> ClawCall {
    var value = ClawCall(); value.function = function; value.argumentCount = UInt32(arguments.count)
    value.stackPointer = frame
    withUnsafeMutableBytes(of: &value.arguments) { target in
        arguments.withUnsafeBytes { target.copyMemory(from: $0) }
    }
    return value
}
let references = try JSONDecoder().decode([Reference].self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
check(references.count == 19,"all original profiles")
var compared = 0, calls = 0
for reference in references {
    let application = try ClawNativeApplication(clock: { 100 })
    let heap = application.heap, host = application.canonicalHost
    check(application.constructed && application.operationCalls[0x4254a0] == 1,"actual application constructor")
    let applicationBytes = Array(UnsafeBufferPointer(start: heap.lookupBytes(application.applicationToken,count: 0x134)!,count: 0x134))
    var platform: ClawNativeMfcLocks? = try ClawNativeMfcLocks(host: host,sha256: reference.sha256,
        initialBytes: decodeHex(reference.initialBytes),
        importTargets: Dictionary(uniqueKeysWithValues: reference.imports.map { (UInt32($0.key)!,$0.value) }),
        version: reference.version)
    weak let weakPlatform = platform
    platform!.incidentalResult = 0xa1b2c3d4
    let previous = host.dependency
    host.dependency = { [weak platform] host, call in
        if let result = platform?.service(call) { return result }
        guard host.fault == nil else { return nil }
        return previous?(host,call)
    }
    for (address,value) in reference.seed { heap.lookup(UInt32(address)!,words:1)![0] = value }
    platform!.beforeService = { owner, function, arguments in
        if reference.failAt == owner.events.count + 1 { throw ClawNativeMfcLocks.Failure.contention }
        if let index = reference.recheck, function == 0x546aac, arguments == [ClawNativeMfcLocks.master],
           !owner.states.contains(where: { $0.section == 0x5408f0 + index*24 }) {
            let receipt = try owner.observeCompletedInitialization(index: index)
            try owner.publishObservedInitialization(receipt)
        }
    }
    for step in reference.steps {
        let result = application.invoke(call(step.function, step.arguments, step.frame))
        check(result.completed == step.completed,reference.name + " completion")
        if step.function == 0x502e47 { check(result.eax == step.eax,reference.name + " initializer EAX") }
        if step.completed {
            check(result.canonicalFault == nil,reference.name + " no fault")
            check(step.returnStackPointer == step.frame + UInt32(4*(1+step.arguments.count)),"original return frame")
        } else {
            check(result.eax == nil && result.canonicalFault?.code == UInt32(CLAW_FAULT_HALT),reference.name + " physical halt")
            check(result.canonicalFault?.address == reference.events.last!.function,"exact halt import")
            let count = platform!.events.count
            check(!application.invoke(call(0x502e47,[],step.frame)).completed,"sticky physical halt")
            check(platform!.events.count == count,"no callbacks after halt")
        }
        check(platform!.states == step.states,reference.name + " source-call ownership/counters")
        check(platform!.imageBytes == decodeHex(step.imageBytes),reference.name + " source-call image bytes")
        check(platform!.events.count == step.eventCount,reference.name + " source-call event count")
        calls += 1
    }
    check(platform!.events.count == reference.events.count,"exact event count")
    for (actual,expected) in zip(platform!.events,reference.events) {
        check(actual.function == expected.function && actual.target == expected.target,"explicit physical import resolution")
        check(actual.stackPointer == expected.stackPointer,reference.name + " exact callback entry ESP")
        check(actual.arguments == expected.arguments,reference.name + " callback arguments")
        check(actual.before == expected.before && actual.after == expected.after,reference.name + " callback ownership/counters")
        check(actual.beforeBytes == decodeHex(expected.beforeBytes) && actual.afterBytes == decodeHex(expected.afterBytes),
              reference.name + " callback globals and untouched canaries")
        check(actual.completed == expected.completed,"physical completion")
        compared += 1
    }
    check(Array(UnsafeBufferPointer(start: heap.lookupBytes(application.applicationToken,count: 0x134)!,count: 0x134)) == applicationBytes,
          "same application storage remains intact")
    check(host.heap === heap,"same actual application heap")
    platform = nil
    check(weakPlatform == nil,"platform owner releases without dependency cycle")
    check(heap.lookupBytes(ClawNativeMfcLocks.imageBase,count:1) == nil,"platform image storage released")
    for slot in ClawNativeMfcLocks.importSlots { check(heap.lookupBytes(slot,count:4) == nil,"platform IAT storage released") }
    check(heap.lookupBytes(application.applicationToken,count:0x134) != nil,"application ownership survives platform teardown")
}

// Loader and service rejection use the same concrete host and heap. They cannot
// silently substitute a game callback, a TLS section, or an unbalanced release.
let image = references[0]
let targets = Dictionary(uniqueKeysWithValues: image.imports.map { (UInt32($0.key)!,$0.value) })
for variant in 0..<5 {
    let heap = ClawTokenHeap()
    let host = ClawNativeCanonicalHost(heap: heap)
    var mapping = targets, bytes = decodeHex(image.initialBytes), hash = image.sha256
    if variant == 0 { hash = "bad" }
    if variant == 1 { bytes.removeLast() }
    if variant == 2 { mapping[0x546aac] = 0x502e47 }
    if variant == 3 { mapping[0x546aac] = mapping[0x546aa4] }
    if variant == 4 { host.heap.store(token:0x546aac,words:1)[0] = 0xdeadbeef }
    var rejected = false
    do { _ = try ClawNativeMfcLocks(host:host,sha256:hash,initialBytes:bytes,importTargets:mapping) }
    catch { rejected = true }
    check(rejected,"invalid image/import refused")
    check(host.heap.lookupBytes(ClawNativeMfcLocks.imageBase,count:1) == nil,"invalid loader is atomic")
    if variant == 4 { check(host.heap.lookup(0x546aac,words:1)![0] == 0xdeadbeef,"existing owner preserved") }

}
// A host may explicitly retire a span while the owner is alive. The old
// storage remains retained during the operation, so a replacement has distinct
// identity and teardown must preserve it.
do {
    let heap = ClawTokenHeap(), host: ClawNativeCanonicalHost
    host = ClawNativeCanonicalHost(heap: heap)
    var owner: ClawNativeMfcLocks? = try ClawNativeMfcLocks(host:host,sha256:image.sha256,
        initialBytes:decodeHex(image.initialBytes),importTargets:targets)
    check(owner != nil,"replacement lifecycle owner")
    heap.withStableFreedStorage {
        heap.free(0x546aac)
        heap.store(token:0x546aac,words:1)[0] = 0xdecafbad
        owner = nil
        check(heap.lookup(0x546aac,words:1)![0] == 0xdecafbad,"replacement span survives teardown")
    }
    check(heap.lookupBytes(ClawNativeMfcLocks.imageBase,count:1) == nil,"other owned spans released")
}
for variant in 0..<4 {
    let application = try ClawNativeApplication(clock:{100}), host: ClawNativeCanonicalHost
    host = application.canonicalHost
    let owner = try ClawNativeMfcLocks(host:host,sha256:image.sha256,initialBytes:decodeHex(image.initialBytes),importTargets:targets)
    var value = call(0x546a9c,[ClawNativeMfcLocks.master],UInt32(CLAW_STACK_TOP)-8)
    if variant == 0 { value.receiver = 1 }
    if variant == 1 { value.stackPointer += 2 }
    if variant == 2 { value = call(0x546aa4,[0x540b14],UInt32(CLAW_STACK_TOP)-8) }
    if variant == 3 { try owner.adoptInitializedSection(ClawNativeMfcLocks.master) }
    check(owner.service(value) == nil && host.fault != nil,"bad ABI/TLS/ownership refused")
}
// Publication authority is narrower than ordinary warm-state adoption. The
// receipt cannot escape its exact master-Enter hook or be reused by any owner.
var publicationControls = 0
func rejects(_ body: () throws -> Void) {
    var rejected = false
    do { try body() } catch { rejected = true }
    check(rejected,"observed publication rejected"); publicationControls += 1
}
for mode in ["outside","wrongIndex","duplicateIssue","repeat","stale","foreign","wrongSlot","wrongSection","adopt","ready","replacement","thread"] {
    let host = ClawNativeCanonicalHost(heap: ClawTokenHeap())
    let owner = try ClawNativeMfcLocks(host:host,sha256:image.sha256,initialBytes:decodeHex(image.initialBytes),importTargets:targets)
    try owner.adoptInitializedSection(ClawNativeMfcLocks.master)
    host.heap.lookup(0x5408e8,words:1)![0] = 1
    host.heap.lookup(0x540a88,words:1)![0] = 0
    host.heap.lookup(0x540aa8,words:1)![0] = 0
    var saved: ClawNativeMfcLocks.ObservedInitialization?
    if mode == "outside" { rejects { _ = try owner.observeCompletedInitialization(index:0) }; continue }
    owner.beforeService = { active, _, _ in
        if mode == "wrongSlot" || mode == "wrongSection" {
            rejects { _ = try active.observeCompletedInitialization(index:0) }; return
        }
        if mode == "adopt" { rejects { try active.adoptInitializedSection(0x5408f0) }; return }
        if mode == "wrongIndex" { rejects { _ = try active.observeCompletedInitialization(index:17) }; return }
        let receipt = try active.observeCompletedInitialization(index:0); saved = receipt
        if mode == "duplicateIssue" { rejects { _ = try active.observeCompletedInitialization(index:1) }; return }
        if mode == "stale" { return }
        if mode == "foreign" {
            let otherHost = ClawNativeCanonicalHost(heap:ClawTokenHeap())
            let other = try ClawNativeMfcLocks(host:otherHost,sha256:image.sha256,initialBytes:decodeHex(image.initialBytes),importTargets:targets)
            rejects { try other.publishObservedInitialization(receipt) }; return
        }
        if mode == "thread" {
            let semaphore = DispatchSemaphore(value:0)
            DispatchQueue.global().async {
                rejects { try active.publishObservedInitialization(receipt) }
                semaphore.signal()
            }
            semaphore.wait(); return
        }
        if mode == "ready" {
            host.heap.lookup(0x540aa8,words:1)![0] = 1
            rejects { try active.publishObservedInitialization(receipt) }; return
        }
        if mode == "replacement" {
            host.heap.free(ClawNativeMfcLocks.imageBase)
            host.heap.storeBytes(token:ClawNativeMfcLocks.imageBase,count:ClawNativeMfcLocks.imageCount).initialize(repeating:0xcc,count:Int(ClawNativeMfcLocks.imageCount))
            rejects { try active.publishObservedInitialization(receipt) }; return
        }
        try active.publishObservedInitialization(receipt)
        rejects { try active.publishObservedInitialization(receipt) }
    }
    let service = mode == "wrongSlot" ? UInt32(0x546abc) : UInt32(0x546aac)
    let arguments: [UInt32] = mode == "wrongSlot" ? [] : [mode == "wrongSection" ? 0x5408f0 : ClawNativeMfcLocks.master]
    host.heap.withStableFreedStorage { _ = owner.service(call(service,arguments,UInt32(CLAW_STACK_TOP)-8)) }
    if mode == "stale" {
        rejects { try owner.publishObservedInitialization(saved!) }
        owner.beforeService = { active, _, _ in rejects { try active.publishObservedInitialization(saved!) } }
        _ = owner.service(call(0x546aac,[ClawNativeMfcLocks.master],UInt32(CLAW_STACK_TOP)-8))
    }
    if mode == "replacement" { check(host.fault != nil,"replacement stops physical completion") }
    if mode != "repeat" { check(!owner.states.contains(where: { $0.section == 0x5408f0 }),"rejected receipt creates no section") }
    else { check(owner.states.first(where: { $0.section == 0x5408f0 })?.initialized == 1,"one finite publication") }
}
print("PASS \(references.count) same-application native MFC lock profiles; \(calls) original calls; \(compared) exact physical callbacks; \(publicationControls) scoped publication controls; all 17 slots, recursion, balanced pairs, recheck, seven failure prefixes, loader/ownership rejection and teardown")
