import Foundation

typealias Host = ClawNativeCanonicalHost
typealias State = Host.SourceSectionSnapshot
struct Snapshot: Decodable {
    let imageBytes: String, states: [State], thread: UInt32
}
struct Event: Decodable {
    let function: UInt32, target: UInt32, importedTarget: UInt32, stackPointer: UInt32, returnPC: UInt32
    let arguments: [UInt32], result: UInt32?, completed: Bool
    let inputCPU: [String: UInt32], outputCPU: [String: UInt32]
    let stackBefore: String, stackAfter: String, before: Snapshot, after: Snapshot
}
struct Entry: Decodable {
    let function: UInt32, frame: UInt32, returnPC: UInt32, arguments: [UInt32], rootStep: Int, kind: String
    let inputCPU: [String: UInt32], outputCPU: [String: UInt32], completed: Bool
    let stackBefore: String, stackAfter: String, before: Snapshot, after: Snapshot
}
struct Step: Decodable {
    let function: UInt32, frame: UInt32, returnPC: UInt32, arguments: [UInt32]
    let completed: Bool, eax: UInt32?
    let inputContext: [String: UInt32], outputContext: [String: UInt32]?, outputCPU: [String: UInt32]
    let stackBefore: String, stackAfter: String, before: Snapshot, after: Snapshot
    let eventCount: Int, entryCount: Int
}
struct Profile: Decodable {
    let name: String, sha256: String, initialBytes: String, imports: [String: UInt32]
    let version: UInt32, failAt: Int?, recheck: UInt32?, serviceEAX: UInt32, seed: [String: UInt32]
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

func compare(_ actual: Host.LocksSnapshot, _ expected: Snapshot, _ label: String) {
    check(actual.imageBytes == Array(unhex(expected.imageBytes)), label + " image")
    check(actual.states == expected.states && expected.thread == 1, label + " same thread ledger")
}
let profiles = try JSONDecoder().decode([Profile].self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
check(profiles.count == 22, "frozen profiles")
for f: UInt32 in [0x502e47,0x502e95,0x502f05] {
    let e = claw_canonical_lookup(f)!.pointee
    check(e.sourceCapability == 2 && e.sourceInputMask == 0x7ff && e.sourceOutputMask == 0x7ff && e.sourcePreserveMask == 0, "admitted source contract")
}
var roots = 0, physical = 0, completedRoots = 0, completedPhysical = 0, observedEntries = 0
var unobserved: [[String: Any]] = []
func makeOwner(_ host: Host, _ p: Profile) throws -> ClawNativeMfcLocks {
    try ClawNativeMfcLocks(host: host, sha256: p.sha256, initialBytes: Array(unhex(p.initialBytes)), importTargets: mapping(p.imports), version: p.version)
}
for profile in profiles {
    let heap = ClawTokenHeap(), host: Host; host = Host(heap: heap)
    var locks: ClawNativeMfcLocks? = try makeOwner(host, profile)
    weak let weakLocks = locks
    locks!.incidentalResult = profile.serviceEAX
    for (address, value) in profile.seed { heap.lookup(UInt32(address)!,words:1)![0] = value }
    locks!.beforeService = { owner, slot, args in
        if profile.failAt == owner.events.count + 1 { throw ClawNativeMfcLocks.Failure.contention }
        if let i = profile.recheck, slot == 0x546aac, args == [ClawNativeMfcLocks.master],
           !owner.states.contains(where: { $0.section == 0x5408f0 + i*24 }) {
            let receipt = try owner.observeCompletedInitialization(index: i)
            try owner.publishObservedInitialization(receipt)
        }
    }
    host.withLocksSourceGraph(provider: locks!) { graph in
        for (index, step) in profile.steps.enumerated() {
            let label = "\(profile.name) step \(index)"
            compare(locks!.locksSnapshot(), step.before, label + " before")
            check(graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(step.stackBefore)), label + " full stack seed")
            var c = context(step.inputContext)
            let result = graph.invokeSource(at: Host.SourceSite(rawValue: step.returnPC)!, context: &c)
            check(result.completed == step.completed && result.eax == step.eax, label + " completion/EAX \(String(describing: host.fault))")
            check(graph.locksOutput.map(cpu) == step.outputCPU, label + " full actual root CPU")
            if let expected = step.outputContext { check(fields(c) == expected, label + " immutable header and all CPU") }
            check(graph.locksStack == unhex(step.stackAfter), label + " full stack output")
            compare(locks!.locksSnapshot(), step.after, label + " after")
            check(graph.locksEvents.count == step.eventCount && locks!.events.count == step.eventCount, label + " exact physical count")
            check(graph.locksEntries.count == index+1, label + " root observation count")
            if !step.completed {
                check(result.fault?.code == UInt32(CLAW_FAULT_HALT) && result.fault?.address == profile.events.last!.function, label + " genuine physical halt")
                check(!graph.invokeSource(at: Host.SourceSite(rawValue: step.returnPC)!, context: &c).completed && locks!.events.count == step.eventCount, "sticky halt")
            }
            roots += 1; if step.completed { completedRoots += 1 }
        }
        check(graph.locksEvents.count == profile.events.count, "all events")
        for (actual, expected) in zip(graph.locksEvents, profile.events) {
            check(actual.function == expected.function && actual.target == expected.target && actual.importedTarget == expected.importedTarget && actual.returnPC == expected.returnPC, "physical identity")
            check(actual.arguments == expected.arguments && actual.input.esp == expected.stackPointer, "physical frame args")
            check(actual.result == expected.result && actual.completed == expected.completed, "physical result")
            check(cpu(actual.input) == expected.inputCPU && actual.output.map(cpu) == expected.outputCPU, "physical all CPU")
            check(actual.stackBefore == unhex(expected.stackBefore) && actual.stackAfter == unhex(expected.stackAfter), "physical full stack")
            compare(actual.before, expected.before, "physical before")
            compare(actual.after!, expected.after, "physical after")
            physical += 1; if actual.completed { completedPhysical += 1 }
        }
        let referenceRoots = profile.entries.filter { $0.kind == "root" }
        check(referenceRoots.count == graph.locksEntries.count, "all root entries")
        for (actual, expected) in zip(graph.locksEntries, referenceRoots) {
            check(actual.function == expected.function && actual.returnPC == expected.returnPC && actual.input.esp == expected.frame && actual.arguments == expected.arguments, "root identities")
            check(cpu(actual.input) == expected.inputCPU && actual.output.map(cpu) == expected.outputCPU, "root observed CPU")
            check(actual.stackBefore == unhex(expected.stackBefore) && actual.stackAfter == unhex(expected.stackAfter), "root full stack")
            check(actual.completed == expected.completed, "root observation completion")
            compare(actual.before, expected.before, "root before"); compare(actual.after!, expected.after, "root after")
            observedEntries += 1
        }
        for e in profile.entries where e.kind != "root" {
            check(e.kind == "nested-owned-initializer" && e.function == 0x502e47 && e.returnPC == 0x502ea8, "reference-only scope")
            unobserved.append(["profile":profile.name,"root_step":e.rootStep,"function":e.function,"return_pc":e.returnPC,"frame":e.frame])
        }
    }
    locks = nil
    check(weakLocks == nil && heap.lookupBytes(ClawNativeMfcLocks.imageBase,count:1) == nil, "owner teardown")
}
check(roots == 76 && completedRoots == 69 && physical == 195 && completedPhysical == 188 && observedEntries == 76 && unobserved.count == 20, "frozen reference counts")

let profile = profiles[0], first = profiles[0].steps[0]
var controls = 0
// Reject malformed source roots before a physical effect.
for variant in 0..<10 {
    let heap = ClawTokenHeap(), host: Host; host = Host(heap:heap)
    let locks = try makeOwner(host,profile)
    host.withLocksSourceGraph(provider:locks) { graph in
        check(graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:unhex(first.stackBefore)),"control stack")
        var c = context(first.inputContext)
        switch variant {
        case 0: c.size = 0
        case 1: c.version = 2
        case 2: c.inputMask = 0
        case 3: c.outputMask = 0
        case 4: c.preserveMask = 1
        case 5: c.reserved1 = 1
        case 6: c.esp += 2
        case 7: c.fsHead = 0
        case 8: c.eip = 0x502f05
        default:
            check(graph.writeStack(at:c.esp,data:Data([0,0,0,0])),"invalid return PC")
        }
        check(!graph.invokeSource(at:.locksAcquire,context:&c).completed && locks.events.isEmpty,"invalid root rejected without effects")
    }
    controls += 1
}
// Saved requests grant no authority to other threads/providers/hosts or a
// second consumption. Checks are made while the physical request is live.
do {
    let heap = ClawTokenHeap(), host: Host; host = Host(heap:heap)
    let locks = try makeOwner(host,profile)
    let otherHost = Host(heap:ClawTokenHeap()), otherOwner: ClawNativeMfcLocks
    otherOwner = try makeOwner(otherHost,profile)
    var saved: Host.SourceLocksRequest?, staleGraph: Host.SourceGraph?
    locks.beforeSourceService = { request in
        saved = request
        check(!request.consume(for:host,provider:locks),"request single use")
        check(!request.consume(for:otherHost,provider:locks),"foreign host")
        check(!request.consume(for:host,provider:otherOwner),"foreign provider")
        let done = DispatchSemaphore(value:0)
        Thread.detachNewThread {
            check(!request.consume(for:host,provider:locks) && !request.validReturn(for:host),"foreign thread")
            done.signal()
        }
        done.wait()
    }
    host.withLocksSourceGraph(provider:locks) { graph in
        staleGraph = graph
        check(graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:unhex(first.stackBefore)),"request stack")
        var c = context(first.inputContext)
        check(graph.invokeSource(at:.locksAcquire,context:&c).completed,"valid request completes")
    }
    check(saved != nil && !saved!.validReturn(for:host) && !saved!.consume(for:host,provider:locks),"expired request")
    var c = context(first.inputContext)
    check(!staleGraph!.invokeSource(at:.locksAcquire,context:&c).completed,"expired graph")
    controls += 6
}
// Storage identity loss or recursive source entry in either callback must halt
// before the callback's physical operation commits.
for variant in 0..<6 {
    let heap = ClawTokenHeap(), host: Host; host = Host(heap:heap)
    let locks = try makeOwner(host,profile)
    host.withLocksSourceGraph(provider:locks) { graph in
        check(graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:unhex(first.stackBefore)),"mutation stack")
        let mutate = {
            if variant < 2 {
                let token: UInt32 = variant == 0 ? ClawNativeMfcLocks.imageBase : 0x546aac
                let count = variant == 0 ? ClawNativeMfcLocks.imageCount : 4
                heap.free(token); _ = heap.storeBytes(token:token,count:count)
            } else if variant < 4 {
                var c = context(first.inputContext)
                check(!graph.invokeSource(at:.locksAcquire,context:&c).completed,"recursive root rejected")
            } else {
                var call = ClawCall(); call.function = 0x546abc; call.stackPointer = first.frame
                check(locks.service(call) == nil,"ordinary callback reentry rejected")
            }
        }
        if variant % 2 == 0 { locks.beforeSourceService = { _ in mutate() } }
        else { locks.beforeService = { _,_,_ in mutate() } }
        var c = context(first.inputContext)
        check(!graph.invokeSource(at:.locksAcquire,context:&c).completed && locks.states.isEmpty,"no effect after authority mutation")
    }
    controls += 1
}
// The source cached Enter target survives a later IAT content mutation, while
// loss of the backing allocation is rejected above.
do {
    let heap = ClawTokenHeap(), host: Host; host = Host(heap:heap)
    let locks = try makeOwner(host,profile)
    locks.incidentalResult = profile.serviceEAX
    locks.beforeService = { _, slot, args in
        if slot == 0x546aac && args == [ClawNativeMfcLocks.master] { heap.lookup(slot,words:1)![0] = 0xdeadbeef }
    }
    host.withLocksSourceGraph(provider:locks) { graph in
        check(graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:unhex(first.stackBefore)),"cached target stack")
        var c = context(first.inputContext)
        check(graph.invokeSource(at:.locksAcquire,context:&c).completed,"cached target accepted")
        check(locks.states.first(where:{$0.section == 0x540a70})?.depth == 1,"cached numbered enter executes")
        check(graph.locksEvents.filter({$0.function == 0x546aac}).allSatisfy({$0.importedTarget == mapping(profile.imports)[0x546aac]}),"cached identity remains original")
    }
    controls += 1
}
let report: [String:Any] = ["status":"pass","profiles":profiles.count,"roots":roots,"completed_roots":completedRoots,
    "physical_events":physical,"completed_physical_events":completedPhysical,"reference_entries":96,
    "observed_entries":observedEntries,"reference_only_entries":unobserved.count,"unobserved_sites":unobserved,
    "native_controls":controls,"assertions":checks,"catch_executed":false]
print(String(data:try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]),encoding:.utf8)!)
