import Foundation

typealias Host = ClawNativeCanonicalHost
struct Snapshot: Decodable {
    let blocks: [Host.SourceBlockSnapshot], sections: [Host.SourceSectionSnapshot]
    let managerBytes: [String: String], blockBytes: [String: String], tlsIndices: [UInt32]
}
struct Event: Decodable {
    let function: UInt32, target: UInt32, importedTarget: UInt32, stackPointer: UInt32, returnPC: UInt32
    let arguments: [UInt32], result: UInt32?, completed: Bool
    let inputCPU: [String: UInt32], outputCPU: [String: UInt32]
    let stackBefore: String, stackAfter: String, before: Snapshot, after: Snapshot
}
struct Entry: Decodable {
    let function: UInt32, frame: UInt32, returnPC: UInt32, arguments: [UInt32]
    let inputCPU: [String: UInt32], stack: String, state: Snapshot
}
struct Step: Decodable {
    let function: UInt32, receiver: UInt32, frame: UInt32, returnPC: UInt32, writes: [String: UInt32]
    let completed: Bool, eax: UInt32?, halt: String?
    let inputContext: [String: UInt32], outputContext: [String: UInt32]?, outputCPU: [String: UInt32]
    let stackBefore: String, stackAfter: String, before: Snapshot, after: Snapshot
    let eventCount: Int, entryCount: Int
}
struct Profile: Decodable {
    let name: String, sha256: String, initialBytes: String, imports: [String: UInt32], lockImports: [String: UInt32]
    let managerCount: Int, managers: [UInt32], fail: String?, failAt: Int?
    let steps: [Step], events: [Event], entries: [Entry]
}
var checks = 0
func check(_ ok: @autoclosure () -> Bool, _ label: String) {
    checks += 1
    if !ok() { FileHandle.standardError.write(Data(("FAIL: " + label + "\n").utf8)); exit(1) }
}
func unhex(_ text: String) -> Data {
    let a = Array(text.utf8)
    func digit(_ c: UInt8) -> UInt8 { c <= 57 ? c-48 : c-87 }
    return Data(stride(from: 0, to: a.count, by: 2).map { digit(a[$0])*16 + digit(a[$0+1]) })
}
func mapping(_ values: [String: UInt32]) -> [UInt32: UInt32] { Dictionary(uniqueKeysWithValues: values.map { (UInt32($0.key)!, $0.value) }) }
func cpu(_ c: ClawSourceContext) -> [String: UInt32] {
    ["eax":c.eax,"ebx":c.ebx,"ecx":c.ecx,"edx":c.edx,"esi":c.esi,"edi":c.edi,
     "ebp":c.ebp,"esp":c.esp,"eip":c.eip,"eflags":c.eflags,"fsHead":c.fsHead]
}
func fields(_ c: ClawSourceContext) -> [String: UInt32] {
    cpu(c).merging(["size":c.size,"version":c.version,"inputMask":c.inputMask,"outputMask":c.outputMask,
                   "preserveMask":c.preserveMask,"reserved0":c.reserved0,"reserved1":c.reserved1]) { _, b in b }
}
func context(_ c: [String: UInt32]) -> ClawSourceContext {
    .init(size:c["size"]!,version:c["version"]!,inputMask:c["inputMask"]!,outputMask:c["outputMask"]!,
          eax:c["eax"]!,ebx:c["ebx"]!,ecx:c["ecx"]!,edx:c["edx"]!,esi:c["esi"]!,edi:c["edi"]!,
          ebp:c["ebp"]!,esp:c["esp"]!,eip:c["eip"]!,eflags:c["eflags"]!,fsHead:c["fsHead"]!,
          preserveMask:c["preserveMask"]!,reserved0:c["reserved0"]!,reserved1:c["reserved1"]!)
}
func compare(_ actual: Host.SourceManagerSnapshot, _ expected: Snapshot, _ label: String) {
    check(actual.blocks == expected.blocks, label+" blocks")
    check(actual.sections == expected.sections, label+" sections")
    check(actual.managerBytes == expected.managerBytes.mapValues { Array(unhex($0)) }, label+" manager bytes")
    check(actual.blockBytes == expected.blockBytes.mapValues { Array(unhex($0)) }, label+" block bytes")
    check(actual.tlsIndices == expected.tlsIndices, label+" TLS indices")
}
let profiles = try JSONDecoder().decode([Profile].self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
check(profiles.count == 9, "nine original profiles")
for (function, mask) in [(UInt32(0x502fb6),UInt32(0x462)),(0x502ff8,0x400),(0x4a4a20,0x452)] {
    let entry = claw_canonical_lookup(function)!.pointee
    check(entry.sourceCapability == 2 && entry.sourceInputMask == 0x7ff && entry.sourceOutputMask == 0x7ff && entry.sourcePreserveMask == mask, "admitted whole source registry")
}
check(claw_canonical_lookup(0x4f50fd) == nil, "genuine missing throw dependency")
var roots = 0, physical = 0, children = 0
for profile in profiles {
    let heap = ClawTokenHeap(), host: Host
    host = Host(heap: heap)
    let locks = try ClawNativeMfcLocks(host: host, sha256: profile.sha256, initialBytes: Array(unhex(profile.initialBytes)), importTargets: mapping(profile.lockImports))
    var memory: ClawNativeMfcMemory? = try ClawNativeMfcMemory(host: host, sha256: profile.sha256, importTargets: mapping(profile.imports), locks: locks)
    weak let weakMemory = memory
    memory!.incidentalResult = 0xa1b2c3d4
    let managers = try (0..<profile.managerCount).map { _ in try memory!.createManager() }
    check(managers == profile.managers, "same physical manager allocation sequence")
    memory!.failAllocation = { slot in
        (profile.fail == "tls" && slot == 0x546a90) || (profile.fail == "allocate" && slot == 0x546b1c) || (profile.fail == "reallocate" && slot == 0x546a88)
    }
    memory!.beforeService = { [weak memory] _, _ in
        if profile.failAt == (memory?.events.count ?? 0)+1 { throw ClawNativeMfcMemory.Failure.exhausted }
    }
    host.withSourceGraph(managerProvider: memory!) { graph in
        for (index, step) in profile.steps.enumerated() {
            let label = "\(profile.name) step \(index)"
            for (address, word) in step.writes { heap.lookup(UInt32(address)!, words: 1)![0] = word }
            compare(memory!.managerSnapshot(), step.before, label+" before")
            check(graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(step.stackBefore)), label+" seed full stack")
            var c = context(step.inputContext)
            let site = Host.SourceSite(rawValue: step.returnPC)!
            let result = graph.invokeSource(at: site, context: &c)
            check(result.completed == step.completed && result.eax == step.eax, label+" completion/EAX \(String(describing: host.fault))")
            check(graph.managerOutput.map(cpu) == step.outputCPU, label+" all live output CPU")
            if let expected = step.outputContext { check(fields(c) == expected, label+" complete output context") }
            check(graph.managerStack == unhex(step.stackAfter), label+" full 128 KiB output stack")
            compare(memory!.managerSnapshot(), step.after, label+" after")
            check(graph.managerEvents.count == step.eventCount && graph.managerEntries.count == step.entryCount, label+" cumulative event/entry counts")
            if !step.completed {
                let address = step.halt == "missing-exception" ? 0x4f50fd : UInt32(step.halt!.dropFirst(2), radix:16)!
                check(result.fault?.address == address && result.fault?.code == UInt32(CLAW_FAULT_HALT), label+" exact halt")
                if address == 0x4f50fd { check(result.fault?.diagnostic == .missingDependency, "no fabricated throw") }
                let count = memory!.events.count
                check(!graph.invokeSource(at: site, context: &c).completed && memory!.events.count == count, "sticky halt")
            }
            roots += 1
        }
        check(graph.managerEvents.count == profile.events.count && memory!.events.count == profile.events.count, "physical operation once")
        for (actual, expected) in zip(graph.managerEvents, profile.events) {
            check(actual.function == expected.function && actual.target == expected.target && actual.importedTarget == expected.importedTarget && actual.returnPC == expected.returnPC, "exact physical identities/PC")
            check(actual.input.esp == expected.stackPointer && actual.arguments == expected.arguments, "physical frame and args")
            check(actual.result == expected.result && (actual.result != nil) == expected.completed, "physical result")
            check(cpu(actual.input) == expected.inputCPU && cpu(actual.output) == expected.outputCPU, "physical all live CPU")
            check(actual.stackBefore == unhex(expected.stackBefore) && actual.stackAfter == unhex(expected.stackAfter), "physical full stack before/after")
            compare(actual.before, expected.before, "physical before")
            compare(actual.after, expected.after, "physical after")
            physical += 1
        }
        for (actual, expected) in zip(graph.managerEntries, profile.entries) {
            check(actual.function == expected.function && actual.returnPC == expected.returnPC && actual.context.esp == expected.frame && actual.arguments == expected.arguments, "real child entry")
            check(cpu(actual.context) == expected.inputCPU && actual.stack == unhex(expected.stack), "real child CPU and full stack")
            compare(actual.state, expected.state, "real child state")
            children += 1
        }
    }
    let released = memory!.blocks.map(\.data) + managers
    memory = nil
    check(weakMemory == nil, "graph retires provider")
    for token in released { check(heap.lookupBytes(token, count: 1) == nil, "owned manager/block teardown") }
}
check(roots == 119 && physical == 271 && children == 13, "frozen original observation counts")
// Independent native authority and ownership controls supplement the original
// replay. They are not additional original game paths or foreign callbacks.
let profile = profiles[0], first = profiles[0].steps[0]
func owner(_ host: Host) throws -> ClawNativeMfcMemory {
    try ClawNativeMfcMemory(host: host, sha256: profile.sha256, importTargets: mapping(profile.imports))
}
func ordinary(_ slot: UInt32, _ args: [UInt32] = []) -> ClawCall {
    var c = ClawCall(); c.function = slot; c.argumentCount = UInt32(args.count); c.stackPointer = first.frame
    withUnsafeMutableBytes(of: &c.arguments) { a in args.withUnsafeBytes { a.copyMemory(from: $0) } }
    return c
}
for variant in 0..<13 {
    let heap = ClawTokenHeap(), host: Host; host = Host(heap: heap)
    let memory = try owner(host), manager = try memory.createManager()
    host.withSourceGraph(managerProvider: memory) { graph in
        check(graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(first.stackBefore)), "invalid root stack setup")
        var c = context(first.inputContext)
        if variant == 0 { c.size = 0 }
        if variant == 1 { c.version = 2 }
        if variant == 2 { c.inputMask = 0 }
        if variant == 3 { c.outputMask = 0 }
        if variant == 4 { c.preserveMask = 0x472 }
        if variant == 5 { c.ecx = manager + 4 }
        if variant == 6 { c.esp += 1 }
        if variant == 7 { c.esp = UInt32(CLAW_STACK_BASE) + 4 }
        if variant == 8 { c.eip = 0x502ff8 }
        if variant == 9 { c.reserved0 = 1 }
        if variant == 10 { c.eflags = 0 }
        if variant == 11 { c.fsHead = 0 }
        if variant == 12 { _ = graph.writeStack(at: c.esp, data: Data(repeating: 0, count: 4)) }
        check(!graph.invokeSource(at: .managerInitialize, context: &c).completed && memory.events.isEmpty, "invalid root/mask/frame/receiver rejected before physical action")
    }
}
for variant in 0..<5 {
    let heap = ClawTokenHeap(), host: Host; host = Host(heap: heap)
    let memory = try owner(host), manager = try memory.createManager()
    if variant == 0 {
        heap.withStableFreedStorage { heap.free(manager); heap.storeBytes(token: manager, count: 0x34).update(repeating: 0xcc, count: 0x34) }
    }
    if variant == 1 {
        let target = heap.lookup(0x546a90, words: 1)![0]
        heap.withStableFreedStorage { heap.free(0x546a90); heap.store(token: 0x546a90, words: 1)[0] = target }
    }
    if variant == 2 { heap.lookup(0x546a90, words: 1)![0] = heap.lookup(0x5469c4, words: 1)![0] }
    if variant == 3 {
        memory.beforeService = { [weak memory] _, _ in _ = memory?.service(ordinary(0x546a90)) }
    }
    if variant == 4 {
        memory.failAllocation = { _ in
            heap.withStableFreedStorage { heap.free(manager); heap.storeBytes(token: manager, count: 0x34).update(repeating: 0xab, count: 0x34) }
            return false
        }
    }
    host.withSourceGraph(managerProvider: memory) { graph in
        _ = graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(first.stackBefore))
        var c = context(first.inputContext)
        check(!graph.invokeSource(at: .managerInitialize, context: &c).completed, "identity/reentry source stop")
    }
    check(host.fault != nil && memory.tlsIndices.isEmpty, "replaced identity or reentry cannot allocate TLS")
}
// A deliberately bounded trusted test provider captures copied requests. Its
// one physical call still uses Memory's existing ordinary operation ledger.
final class CaptureProvider: Host.SourceManagerProvider {
    let memory: ClawNativeMfcMemory
    var request: Host.SourceManagerRequest?
    var consumedTwice = false, foreignConsumed = false
    var mode = 0
    var foreignThreadConsumed = false, foreignThreadService: UInt32?
    init(_ memory: ClawNativeMfcMemory) { self.memory = memory }
    func validManagerBinding(for host: Host) -> Bool { memory.validManagerBinding(for: host) }
    func managerImportTarget(_ slot: UInt32) -> UInt32? { memory.managerImportTarget(slot) }
    func ownsSourceManager(_ token: UInt32) -> Bool { memory.ownsSourceManager(token) }
    func ownsSourceBlock(_ data: UInt32, count: UInt32) -> Bool { memory.ownsSourceBlock(data, count: count) }
    func managerSnapshot() -> Host.SourceManagerSnapshot { memory.managerSnapshot() }
    func serviceSourceManager(_ request: Host.SourceManagerRequest) -> UInt32? {
        self.request = request
        let group = DispatchGroup(); group.enter()
        DispatchQueue.global().async {
            self.foreignThreadConsumed = request.consume(for: self.memory.host, provider: self)
            self.foreignThreadService = self.memory.serviceSourceManager(request)
            group.leave()
        }
        group.wait()
        check(!foreignThreadConsumed && foreignThreadService == nil && memory.host.fault == nil, "foreign thread cannot consume or mutate owner")
        let foreign = Host(heap: ClawTokenHeap())
        foreignConsumed = request.consume(for: foreign, provider: self)
        if mode == 1 { return 0 } // Returning without consuming cannot authorize return.
        check(!request.consume(for: memory.host, provider: memory), "exact provider identity")
        check(request.consume(for: memory.host, provider: self), "valid single-use source lease")
        consumedTwice = request.consume(for: memory.host, provider: self)
        var copiedStack = request.stack
        copiedStack[0] ^= 0xff
        check(copiedStack != request.stack, "source request uses value stack copy")
        let value = memory.service(ordinary(request.slot, request.arguments))
        return value
    }
}
for mode in 0..<2 {
    let heap = ClawTokenHeap(), host: Host; host = Host(heap: heap)
    let memory = try owner(host); _ = try memory.createManager()
    let provider = CaptureProvider(memory); provider.mode = mode
    var retired: Host.SourceGraph?
    host.withSourceGraph(managerProvider: provider) { graph in
        retired = graph
        _ = graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(first.stackBefore))
        var c = context(first.inputContext)
        let result = graph.invokeSource(at: .managerInitialize, context: &c)
        check(result.completed == (mode == 0), "provider must consume before source return")
        check(!provider.foreignConsumed && !provider.consumedTwice, "foreign host and reused lease denied")
        check(!provider.request!.consume(for: host, provider: provider), "expired source request denied inside live graph")
    }
    check(!provider.request!.consume(for: host, provider: provider), "retired request has no authority")
    var c = context(first.inputContext)
    let eventCount = memory.events.count
    check(!retired!.invokeSource(at: .managerInitialize, context: &c).completed && memory.events.count == eventCount, "retired graph cannot call physical owner")
}
for duringEnter in [false, true] {
    let heap = ClawTokenHeap(), host: Host; host = Host(heap: heap)
    let memory = try owner(host); let manager = try memory.createManager()
    host.withSourceGraph(managerProvider: memory) { graph in
        for step in profile.steps.prefix(2) {
            _ = graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(step.stackBefore))
            var c = context(step.inputContext)
            check(graph.invokeSource(at: Host.SourceSite(rawValue: step.returnPC)!, context: &c).completed, "table ABA preparation")
        }
        let block = memory.blocks[0]
        let bytes = Array(UnsafeBufferPointer(start: heap.lookupBytes(block.data, count: block.size)!, count: Int(block.size)))
        func replace() {
            heap.withStableFreedStorage {
                heap.free(block.data)
                heap.storeBytes(token: block.data, count: block.size).update(from: bytes, count: bytes.count)
            }
        }
        if duringEnter { memory.beforeService = { slot, _ in if slot == 0x546aac { replace() } } }
        else { replace() }
        let step = profile.steps[2]
        _ = graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(step.stackBefore))
        var c = context(step.inputContext)
        check(!graph.invokeSource(at: .managerAllocate, context: &c).completed, "same-address table ABA is rejected")
        check(Array(UnsafeBufferPointer(start: heap.lookupBytes(block.data, count: block.size)!, count: Int(block.size))) == bytes, "fast path never writes replacement table")
        check(heap.lookup(manager, words: 13)![2] == 2, "rejected ABA leaves next slot unchanged")
    }
}
do {
    let heap = ClawTokenHeap(), host: Host; host = Host(heap: heap)
    var memory: ClawNativeMfcMemory? = try owner(host)
    let borrowed: UInt32 = 0x63000000
    heap.storeBytes(token: borrowed, count: 0x34).update(repeating: 0xcc, count: 0x34)
    try memory!.registerManager(borrowed)
    host.withSourceGraph(managerProvider: memory!) { graph in
        _ = graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(first.stackBefore))
        var c = context(first.inputContext); c.ecx = borrowed
        check(graph.invokeSource(at: .managerInitialize, context: &c).completed, "explicit borrowed manager accepted")
    }
    memory = nil
    check(heap.lookupBytes(borrowed, count: 0x34) != nil, "borrowed manager survives owner teardown")
}
print("PASS \(checks) checks; \(profiles.count) original source manager profiles; \(roots) root calls; \(physical) physical events; \(children) real child entries; full CPU/stack/owner snapshots")

let report: [String: Any] = ["status":"pass", "profiles":profiles.count, "roots":roots,
    "physical_events":physical, "child_entries":children, "assertions":checks,
    "native_controls":checks-6117]
print(String(data: try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]), encoding: .utf8)!)
