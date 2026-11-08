import Foundation

typealias Host = ClawNativeCanonicalHost
struct Snapshot: Decodable {
    let blocks: [Host.SourceBlockSnapshot], sections: [Host.SourceSectionSnapshot]
    let managerBytes: [String: String], blockBytes: [String: String], tlsIndices: [UInt32]
    let ownerBytes: [String: String], globals: [String: UInt32], locals: [String: UInt32], localBytes: [String: String]
    let allocations: [Host.TLSAllocation], allocationBytes: [String: String], borrowedStorage: [Host.TLSBorrowed], tlsValues: [String: UInt32]
    let ownerValue: UInt32, staticManagerBytes: String, thread: UInt32
}
struct Observation: Decodable {
    let function: UInt32, frame: UInt32, returnPC: UInt32, arguments: [UInt32], rootStep: Int
    let inputCPU: [String: UInt32], outputCPU: [String: UInt32]
    let stackBefore: String, stackAfter: String, before: Snapshot, after: Snapshot, completed: Bool
    let result: UInt32?, importedTarget: UInt32?
}
struct Step: Decodable {
    let function: UInt32, receiver: UInt32, frame: UInt32, returnPC: UInt32, arguments: [UInt32]
    let completed: Bool, eax: UInt32?, halt: String?, failure: String?, tlsSetFalse: Bool
    let inputContext: [String: UInt32], outputContext: [String: UInt32]?, outputCPU: [String: UInt32]
    let stackBefore: String, stackAfter: String, before: Snapshot, after: Snapshot
    let eventCount: Int, entryCount: Int
}
struct Preparation: Decodable { let label: String, beforeStep: Int, writes: [String: UInt32] }
struct Profile: Decodable {
    let name: String, sha256: String, initialBytes: String, imports: [String: UInt32], lockImports: [String: UInt32]
    let manager: UInt32, owner: UInt32, preparations: [Preparation]
    let steps: [Step], events: [Observation], entries: [Observation]
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
func compare(_ actual: Host.TLSSnapshot, _ expected: Snapshot, _ label: String) {
    let m = actual.manager
    check(m.blocks == expected.blocks, label+" blocks")
    check(m.sections == expected.sections, label+" sections")
    check(m.managerBytes == expected.managerBytes.mapValues { Array(unhex($0)) }, label+" manager bytes")
    check(m.blockBytes == expected.blockBytes.mapValues { Array(unhex($0)) }, label+" block bytes")
    check(m.tlsIndices == expected.tlsIndices, label+" TLS indices")
    check(actual.ownerBytes == expected.ownerBytes.mapValues { Array(unhex($0)) }, label+" owner bytes")
    check(actual.globals == expected.globals, label+" publication")
    check(actual.locals == expected.locals, label+" locals")
    check(actual.localBytes == expected.localBytes.mapValues { Array(unhex($0)) }, label+" local bytes")
    check(actual.allocations == expected.allocations, label+" allocation identity/lifetime")
    check(actual.allocationBytes == expected.allocationBytes.mapValues { Array(unhex($0)) }, label+" all live/retired bytes")
    check(actual.borrowedStorage == expected.borrowedStorage, label+" borrowed identity registration")
    check(actual.tlsValues == expected.tlsValues, label+" actual thread TLS values")
    check(expected.thread == 1 && actual.manager.managerBytes["5507832"] == Array(unhex(expected.staticManagerBytes)), label+" static manager/thread")
    let owner = actual.ownerBytes["5500060"]!
    check(expected.ownerValue == owner.enumerated().reduce(UInt32(0)) { $0 | UInt32($1.element) << ($1.offset*8) }, label+" static owner")
}
func compareObservation(_ actual: Host.TLSObservation, _ expected: Observation, _ label: String) {
    check(actual.function == expected.function && actual.returnPC == expected.returnPC && actual.arguments == expected.arguments && actual.input.esp == expected.frame, label+" metadata/frame/args")
    check(cpu(actual.input) == expected.inputCPU, label+" input CPU actual \(cpu(actual.input)) expected \(expected.inputCPU)")
    check(actual.output.map(cpu) == expected.outputCPU, label+" output CPU actual \(String(describing: actual.output.map(cpu))) expected \(expected.outputCPU)")
    check(actual.completed == expected.completed, label+" completion")
    check(actual.stackBefore == unhex(expected.stackBefore) && actual.stackAfter == unhex(expected.stackAfter), label+" full128KiB stack")
    compare(actual.before, expected.before, label+" before"); compare(actual.after!, expected.after, label+" after")
}
let profiles = try JSONDecoder().decode([Profile].self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
check(profiles.count == 11, "eleven original profiles")
check(claw_canonical_lookup(0x4f50fd) == nil, "genuine missing throw")
var roots = 0, physical = 0, entries = 0, referenceOnly = 0
var unobserved: [[String: Any]] = []
for profile in profiles {
    let heap = ClawTokenHeap(), host: Host; host = Host(heap: heap)
    let locks = try ClawNativeMfcLocks(host: host, sha256: profile.sha256, initialBytes: Array(unhex(profile.initialBytes)), importTargets: mapping(profile.lockImports))
    let memory = try ClawNativeMfcMemory(host: host, sha256: profile.sha256, importTargets: mapping(profile.imports), locks: locks)
    for token in [profile.manager, profile.owner, UInt32(0x540af0)] {
        let bytes = token == profile.manager ? unhex(profile.steps[0].before.staticManagerBytes) : Data(repeating: 0, count: 4)
        bytes.withUnsafeBytes { heap.storeBytes(token: token, count: UInt32(bytes.count)).update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: bytes.count) }
    }
    try memory.registerManager(profile.manager); try memory.registerTLSOwner(profile.owner); try memory.registerTLSPublication(0x540af0)
    memory.incidentalResult = 0xa1b2c3d4
    let executed = host.withTLSSourceGraph(provider: memory) { graph in
        for (index, step) in profile.steps.enumerated() {
            let label = "\(profile.name) step \(index)"
            let allocationCount = memory.tlsSnapshot().allocations.count
            // Only explicit original fixture allocations occur between roots:
            // zero owner, independent manager, or the labeled wider backing.
            for allocation in step.before.allocations.dropFirst(allocationCount) {
                let token: UInt32
                switch allocation.kind {
                case "slot-owner": token = try! memory.createTLSOwner()
                case "manager": token = try! memory.createManager()
                case "local":
                    check(profile.preparations.contains(where: { $0.beforeStep == index }), "wider backing is explicit preparation")
                    let container = memory.tlsValue(heap.lookup(profile.manager, words: 1)![0])!
                    let old = heap.lookup(container, words: 4)![3], oldBytes = memory.localBytes[String(old)]!
                    token = try! memory.createTLSLocal(count: 16, zero: true)
                    oldBytes.withUnsafeBufferPointer { heap.lookupBytes(token, count: UInt32(oldBytes.count))!.update(from: $0.baseAddress!, count: oldBytes.count) }
                default: fatalError("unrecognized input preparation")
                }
                check(token == allocation.address, "input allocation sequence")
            }
            for prep in profile.preparations where prep.beforeStep == index {
                for (address, word) in prep.writes { heap.lookup(UInt32(address)!, words: 1)![0] = word }
            }
            memory.failTLSSet = step.tlsSetFalse
            memory.failAllocation = { slot in
                (step.failure == "tls" && slot == 0x546a90) || (step.failure == "global" && slot == 0x546b1c) ||
                (step.failure == "local-realloc" && slot == 0x546a80)
            }
            memory.beforeService = { [weak memory] slot, args in
                if (step.failure == "container" && slot == 0x546aa8 && args == [0x40,16]) ||
                   (step.failure == "array" && slot == 0x546aa8 && args[0] == 0) {
                    memory?.failAllocation = { $0 == 0x546aa8 }
                }
            }
            compare(memory.tlsSnapshot(), step.before, label+" before")
            check(graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(step.stackBefore)), label+" stack seed")
            var c = context(step.inputContext)
            let result = graph.invokeSource(at: Host.SourceSite(rawValue: step.returnPC)!, context: &c)
            check(result.completed == step.completed && result.eax == step.eax, label+" completion/EAX fault=\(String(describing: host.fault))")
            check(graph.tlsOutput.map(cpu) == step.outputCPU, label+" actual live output CPU")
            if let output = step.outputContext { check(fields(c) == output, label+" output full context") }
            check(graph.tlsStack == unhex(step.stackAfter), label+" root full128KiB stack")
            compare(memory.tlsSnapshot(), step.after, label+" after")
            check(graph.tlsEvents.count == step.eventCount, label+" cumulative physical count")
            if !step.completed { check(result.fault?.address == 0x4f50fd && result.fault?.diagnostic == .missingDependency, label+" true missing dependency") }
            roots += 1
        }
        check(graph.tlsEvents.count == profile.events.count && memory.events.count == profile.events.count, "physical owner operation exactly once")
        for (i, pair) in zip(graph.tlsEvents, profile.events).enumerated() {
            compareObservation(pair.0, pair.1, "\(profile.name) physical \(i) pc \(String(pair.1.returnPC,radix:16))")
            check(pair.0.output?.eax == pair.1.result, "physical result"); physical += 1
        }
        let observed = profile.entries.filter { e in
            if e.function == 0x503167 && profile.steps[e.rootStep].function == 0x50335e {
                referenceOnly += 1
                unobserved.append(["profile":profile.name,"root_step":e.rootStep,"function":e.function,"return_pc":e.returnPC,"frame":e.frame])
                return false
            }
            return true
        }
        check(graph.tlsEntries.count == observed.count, "available dispatched entry count actual \(graph.tlsEntries.count) expected \(observed.count)")
        for (i, pair) in zip(graph.tlsEntries, observed).enumerated() {
            compareObservation(pair.0, pair.1, "\(profile.name) child \(i) function \(String(pair.1.function,radix:16))"); entries += 1
        }
        return true
    }
    check(executed == true, "executed TLS graph")
    FileHandle.standardError.write(Data(("PASS profile " + profile.name + "\n").utf8))
}
check(roots == 55 && physical == 399 && entries + referenceOnly == 410, "frozen observation totals; owned setter is reference only")
// These native controls exercise authority and ownership; they are deliberately
// separate from original observations and do not assert foreign callback flow.
let originalAssertions = checks
func fixture() throws -> (ClawTokenHeap, Host, ClawNativeMfcMemory) {
    let p = profiles[0], heap = ClawTokenHeap(), host: Host; host = Host(heap: heap)
    let memory = try ClawNativeMfcMemory(host: host, sha256: p.sha256, importTargets: mapping(p.imports))
    unhex(p.steps[0].before.staticManagerBytes).withUnsafeBytes { bytes in
        heap.storeBytes(token: p.manager, count: 0x34).update(from: bytes.bindMemory(to: UInt8.self).baseAddress!, count: 0x34)
    }
    heap.store(token: p.owner, words: 1)[0] = 0; heap.store(token: 0x540af0, words: 1)[0] = 0
    try memory.registerManager(p.manager); try memory.registerTLSOwner(p.owner); try memory.registerTLSPublication(0x540af0)
    memory.incidentalResult = 0xa1b2c3d4
    return (heap, host, memory)
}
func stackWordData(_ value: UInt32) -> Data { var v = value.littleEndian; return withUnsafeBytes(of: &v) { Data($0) } }
func call(_ graph: Host.SourceGraph, _ step: Step) -> Host.Completion {
    _ = graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(step.stackBefore))
    var c = context(step.inputContext)
    return graph.invokeSource(at: Host.SourceSite(rawValue: step.returnPC)!, context: &c)
}
func replace(_ heap: ClawTokenHeap, _ token: UInt32, _ size: UInt32) -> [UInt8] {
    let bytes = Array(UnsafeBufferPointer(start: heap.lookupBytes(token, count: size)!, count: Int(size)))
    heap.withStableFreedStorage { heap.free(token); heap.storeBytes(token: token, count: size).update(from: bytes, count: bytes.count) }
    return bytes
}
let first = profiles[0].steps[0]
for variant in 0..<17 {
    let (_,host,memory) = try fixture()
    host.withTLSSourceGraph(provider: memory) { graph in
        _ = graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(first.stackBefore))
        var c = context(first.inputContext)
        switch variant {
        case 0:c.size = 0
        case 1:c.version = 2
        case 2:c.inputMask = 0
        case 3:c.outputMask = 0
        case 4:c.preserveMask = 0x442
        case 5:c.reserved0 = 1
        case 6:c.reserved1 = 1
        case 7:c.eip = 0x503167
        case 8:c.ecx += 4
        case 9:c.esp += 1
        case 10:c.esp = UInt32(CLAW_STACK_BASE) + 4
        case 11:c.esp = UInt32(CLAW_STACK_END)-4
        case 12:c.eflags = 0
        case 13:c.fsHead = 0
        case 14:_ = graph.writeStack(at: c.esp, data: stackWordData(0x5033ce))
        case 15:_ = graph.writeStack(at: c.esp+4, data: stackWordData(0x503510))
        default:_ = graph.writeStack(at: c.esp+4, data: stackWordData(0))
        }
        check(!graph.invokeSource(at: .tlsGet, context: &c).completed && memory.events.isEmpty, "invalid getter context/frame/factory cannot reach physical owner")
    }
}
do {
    let (_,host,memory) = try fixture()
    host.withSourceGraph(managerProvider: memory) { graph in
        check(!call(graph, first).completed && memory.events.isEmpty, "manager-only graph has no TLS authority")
    }
}
// Borrowed owner/publication/manager and IAT ABA at rest and inside callbacks.
for during in [false,true] {
    for token in [UInt32(0x53ec9c),0x540af0,0x540af8,0x546a90] {
        let (heap,host,memory) = try fixture()
        let size: UInt32 = token == 0x540af8 ? 0x34 : 4
        if during { memory.beforeService = { _, _ in _ = replace(heap, token, size) } }
        else { _ = replace(heap,token,size) }
        _ = host.withTLSSourceGraph(provider: memory) { graph in check(!call(graph,first).completed, "callback ABA stops source") }
        check(host.fault != nil && memory.tlsIndices.isEmpty && memory.localPointers.isEmpty, "ABA cannot create physical TLS or local allocation")
    }
}
// Same-address replacements of live containers/arrays are caught on the warm
// read and on setter's otherwise allocation-free final store.
for setter in [false,true] {
    for during in [false,true] {
        for containerTarget in [false,true] {
            let (heap,host,memory) = try fixture()
            host.withTLSSourceGraph(provider: memory) { graph in
                check(call(graph,first).completed, "ABA control cold preparation")
                let container = memory.tlsValue(0)!, array = heap.lookup(container, words: 4)![3]
                let token = containerTarget ? container : array, size: UInt32 = containerTarget ? 16 : 8
                var replacement: [UInt8] = []
                if during { memory.beforeService = { slot,_ in if slot == 0x546a7c { replacement = replace(heap,token,size) } } }
                else { replacement = replace(heap,token,size) }
                let step = setter ? profiles[3].steps[1] : profiles[0].steps[1]
                check(!call(graph,step).completed, "same-address container/array ABA rejected")
                check(Array(UnsafeBufferPointer(start: heap.lookupBytes(token,count:size)!,count:Int(size))) == replacement, "no source store to replacement storage")
            }
        }
    }
}
for ordinal in [UInt32.max, UInt32(2), UInt32(0x40000000)] {
    let (heap,host,memory) = try fixture()
    host.withTLSSourceGraph(provider: memory) { graph in
        check(call(graph,first).completed, "invalid zero setter preparation")
        let step = profiles[3].steps[2], before = memory.localBytes
        _ = graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(step.stackBefore))
        _ = graph.writeStack(at: step.frame+4, data: stackWordData(ordinal))
        var c = context(step.inputContext)
        check(!graph.invokeSource(at: .tlsSet, context: &c).completed && memory.localBytes == before, "zero setter requires actual wider backing and nonnegative bounded ordinal")
        check(heap.lookup(0x540af8, words: 13)![3] == 2, "rejected setter preserves logical manager highwater")
    }
}
// The scoped setter must still own the actual factory result when a physical
// callback is entered, and its live container after that callback returns.
for mode in 0..<3 {
    let (heap,host,memory) = try fixture()
    var fired = false, replacement: [UInt8] = [], token: UInt32 = 0, count: UInt32 = 0
    memory.beforeService = { [weak memory] slot,_ in
        guard let memory, !fired else { return }
        if mode == 0 && slot == 0x546a7c && memory.localPointers.count == 1 {
            token = memory.localPointers[0]; count = 0x118
        } else if mode == 1 && slot == 0x546aac && memory.localPointers.count == 2 {
            token = memory.localPointers.last!; count = 16
        } else if mode == 2 && slot == 0x546a84 {
            token = memory.localPointers.last!; count = 8
        } else { return }
        fired = true; replacement = replace(heap,token,count)
    }
    host.withTLSSourceGraph(provider: memory) { graph in
        check(!call(graph,first).completed && fired, "owned setter allocation identity checked at callback return")
        check(Array(UnsafeBufferPointer(start: heap.lookupBytes(token,count:count)!,count:Int(count))) == replacement, "owned setter never writes ABA replacement")
    }
}
final class TLSCapture: Host.SourceTLSProvider {
    let memory: ClawNativeMfcMemory
    var requests: [Host.SourceManagerRequest] = []
    var omitConsumption = false
    init(_ m: ClawNativeMfcMemory) { memory = m }
    var sourceImportTarget: UInt32 { memory.sourceImportTarget }
    func validSourceBinding(for h: Host) -> Bool { memory.validSourceBinding(for:h) }
    func ownsSourceLocal(_ t: UInt32,count: UInt32) -> Bool { memory.ownsSourceLocal(t,count:count) }
    func sourceLocalSnapshot(_ t: UInt32) -> Data? { memory.sourceLocalSnapshot(t) }
    func validManagerBinding(for h: Host) -> Bool { memory.validManagerBinding(for:h) }
    func managerImportTarget(_ s: UInt32) -> UInt32? { memory.managerImportTarget(s) }
    func ownsSourceManager(_ t: UInt32) -> Bool { memory.ownsSourceManager(t) }
    func ownsSourceBlock(_ t: UInt32,count: UInt32) -> Bool { memory.ownsSourceBlock(t,count:count) }
    func managerSnapshot() -> Host.SourceManagerSnapshot { memory.managerSnapshot() }
    func validTLSBinding(for h: Host) -> Bool { memory.validTLSBinding(for:h) }
    func ownsTLSOwner(_ t: UInt32) -> Bool { memory.ownsTLSOwner(t) }
    func ownsTLSLocal(_ t: UInt32,count: UInt32) -> Bool { memory.ownsTLSLocal(t,count:count) }
    func tlsValue(_ i: UInt32) -> UInt32? { memory.tlsValue(i) }
    func tlsSnapshot() -> Host.TLSSnapshot { memory.tlsSnapshot() }
    func ordinary(_ slot: UInt32,_ args: [UInt32],_ frame: UInt32) -> UInt32? {
        var call = ClawCall(); call.function = slot; call.argumentCount = UInt32(args.count); call.stackPointer = frame
        withUnsafeMutableBytes(of:&call.arguments) { out in args.withUnsafeBytes { out.copyMemory(from:$0) } }
        return memory.service(call)
    }
    func allocateSourceLocal(_ r: Host.SourceAllocationRequest) -> UInt32? {
        guard r.consume(for:memory.host,provider:self) else { return nil }
        return ordinary(r.slot,r.arguments,r.context.esp)
    }
    func serviceSourceManager(_ r: Host.SourceManagerRequest) -> UInt32? {
        requests.append(r)
        if omitConsumption { return 0 }
        let foreign = Host(heap:ClawTokenHeap())
        check(!r.consume(for:foreign,provider:self) && !r.consume(for:memory.host,provider:memory), "exact host/provider lease")
        let group = DispatchGroup(); group.enter()
        var foreignConsume = true, foreignResult: UInt32? = 1
        DispatchQueue.global().async { foreignConsume = r.consume(for:self.memory.host,provider:self); foreignResult = self.memory.serviceSourceManager(r); group.leave() }
        group.wait()
        check(!foreignConsume && foreignResult == nil && memory.host.fault == nil, "foreign thread cannot consume or mutate owner fault")
        check(r.consume(for:memory.host,provider:self) && !r.consume(for:memory.host,provider:self), "one physical lease consumption")
        var copied = r.stack; copied[0] ^= 0xff
        check(copied != r.stack, "source stack observation is copied")
        return ordinary(r.slot,r.arguments,r.context.esp)
    }
}
for omit in [false,true] {
    let (_,host,memory) = try fixture(), provider: TLSCapture
    provider = TLSCapture(memory); provider.omitConsumption = omit
    var retired: Host.SourceGraph?
    host.withTLSSourceGraph(provider:provider) { graph in
        retired = graph
        check(call(graph,first).completed == !omit, "TLS provider must consume physical lease")
        check(!provider.requests.last!.consume(for:host,provider:provider), "lease expired within graph")
    }
    check(!provider.requests.last!.consume(for:host,provider:provider), "lease expired after graph")
    let count = memory.events.count
    check(!call(retired!,first).completed && memory.events.count == count, "retired TLS graph cannot execute")
}
do {
    let (_,host,memory) = try fixture()
    host.withTLSSourceGraph(provider: memory) { graph in
        memory.beforeService = { _,_ in var c = context(first.inputContext); _ = graph.invokeSource(at:.tlsGet,context:&c) }
        check(!call(graph,first).completed && memory.tlsIndices.isEmpty, "reentry cannot perform physical TLS allocation")
        memory.beforeService = nil
    }
}
do {
    let (heap,_,memory) = try fixture()
    let tokens: [UInt32] = [0x53ec9c,0x540af0,0x540af8]
    check(tokens.allSatisfy { heap.containingAllocationIdentity(at:$0,count:4) != nil }, "borrowed static storage stays caller owned")
    check(memory.tlsSnapshot().borrowedStorage.count == 3, "three explicit borrowed extents")
}
// Invalid logical growth must not reach an out-of-range final store even
// though the original setter sizes growth from the manager's highwater.
do {
    let (_,host,memory) = try fixture()
    host.withTLSSourceGraph(provider: memory) { graph in
        check(call(graph,first).completed, "bounded growth control preparation")
        let step = profiles[3].steps[1]
        _ = graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(step.stackBefore))
        _ = graph.writeStack(at: step.frame+4, data: stackWordData(2))
        var c = context(step.inputContext)
        check(!graph.invokeSource(at:.tlsSet,context:&c).completed, "growth final store must fit newly owned array")
    }
}
func retiredOwnerFixture() throws -> (ClawTokenHeap,[UInt32],[ClawTokenHeap.AllocationIdentity]) {
    let (heap,host,memory) = try fixture()
    let borrowed: [UInt32] = [0x53ec9c,0x540af0,0x540af8]
    let identities = borrowed.map { heap.containingAllocationIdentity(at:$0,count:4)! }
    host.withTLSSourceGraph(provider:memory) { graph in check(call(graph,first).completed, "teardown cold preparation") }
    return (heap,memory.localPointers + memory.blocks.map(\.data),identities)
}
do {
    let (heap,owned,identities) = try retiredOwnerFixture()
    for (token,identity) in zip([UInt32(0x53ec9c),0x540af0,0x540af8],identities) {
        check(heap.containingAllocationIdentity(at:token,count:4) === identity, "borrowed storage identity survives actual Memory teardown")
    }
    check(owned.allSatisfy { heap.lookupBytes($0,count:1) == nil }, "same owner retires all owned local/global storage")
}
// Regression: the owned setter can store immediately after TLSGetValue when
// a warm container has an empty slot. No later allocation callback may be
// relied upon to detect ABA of the new factory record.
do {
    let (heap,host,memory) = try fixture()
    host.withTLSSourceGraph(provider:memory) { graph in
        check(call(graph,first).completed, "warm factory ABA preparation")
        let container = memory.tlsValue(0)!, array = heap.lookup(container,words:4)![3]
        heap.lookup(array,words:2)![1] = 0
        var fired = false, target: UInt32 = 0, replacement: [UInt8] = []
        memory.beforeService = { [weak memory] slot,_ in
            guard let memory, !fired, slot == 0x546a7c,
                  memory.localPointers.count == 4 else { return }
            target = memory.localPointers.last!; replacement = replace(heap,target,0x118); fired = true
        }
        check(!call(graph,profiles[0].steps[1]).completed && fired, "warm owned setter rejects factory ABA after final physical callback")
        check(heap.lookup(array,words:2)![1] == 0, "warm owned setter cannot publish replaced factory token")
        check(Array(UnsafeBufferPointer(start:heap.lookupBytes(target,count:0x118)!,count:0x118)) == replacement, "factory replacement remains unchanged")
    }
}
let nativeControls = checks - originalAssertions

let report: [String: Any] = ["status":"pass","profiles":profiles.count,"roots":roots,"physical_events":physical,"observed_entries":entries,"reference_only_entries":referenceOnly,"reference_entries":410,"unobserved_sites":unobserved,"assertions":checks,"native_controls":nativeControls]
print(String(data: try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]), encoding: .utf8)!)
