import Foundation

typealias Host = ClawNativeCanonicalHost
struct Snapshot: Decodable {
    let blocks: [Host.SourceBlockSnapshot], sections: [Host.SourceSectionSnapshot]
    let managerBytes: [String: String], blockBytes: [String: String], tlsIndices: [UInt32]
    let ownerBytes: [String: String], globals: [String: UInt32], locals: [String: UInt32], localBytes: [String: String]
    let allocations: [Host.TLSAllocation], allocationBytes: [String: String], borrowedStorage: [Host.TLSBorrowed], tlsValues: [String: UInt32]
    let ownerValue: UInt32, staticManagerBytes: String, thread: UInt32
    let imageBytes: String, moduleOwnerValue: UInt32, sourceGlobalBytes: [String:String], writtenImageBytes: [String:String]
    let staticOwnerIdentities: [StaticIdentity]
}
struct StaticIdentity: Decodable { let address: UInt32, size: UInt32, identity: String }
struct Observation: Decodable {
    let function: UInt32, frame: UInt32, returnPC: UInt32, arguments: [UInt32], rootStep: Int
    let inputCPU: [String: UInt32], outputCPU: [String: UInt32]
    let stackBefore: String, stackAfter: String, before: Snapshot, after: Snapshot, completed: Bool
    let result: UInt32?, importedTarget: UInt32?, order: Int, returnOrder: Int?, observation: String?
}
struct Step: Decodable {
    let function: UInt32, receiver: UInt32, frame: UInt32, returnPC: UInt32, arguments: [UInt32]
    let completed: Bool, eax: UInt32?, halt: String?, outcome: String
    let inputContext: [String: UInt32], outputContext: [String: UInt32]?, outputCPU: [String: UInt32]
    let stackBefore: String, stackAfter: String, before: Snapshot, after: Snapshot
    let eventCount: Int, entryCount: Int
}
struct Preparation: Decodable { let label: String, beforeStep: Int, writes: [String: UInt32] }
struct Profile: Decodable {
    let name: String, sha256: String, initialBytes: String, imports: [String: UInt32], lockImports: [String: UInt32]
    let manager: UInt32, owner: UInt32, preparations: [Preparation]
    let steps: [Step], events: [Observation], entries: [Observation]
    let allocationFailAt: Int?, physicalFailAt: Int?, tlsFailure: Bool
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
func compare(_ state: Host.ModuleSnapshot, _ expected: Snapshot, _ label: String) {
    let actual = state.tls, m = actual.manager
    check(m.blocks == expected.blocks, label+" blocks")
    check((m.sections + state.locks.states).sorted { $0.section < $1.section } == expected.sections, label+" combined sections")
    check(m.managerBytes == expected.managerBytes.mapValues { Array(unhex($0)) }, label+" manager bytes")
    check(m.blockBytes == expected.blockBytes.mapValues { Array(unhex($0)) }, label+" block bytes")
    check(m.tlsIndices == expected.tlsIndices, label+" TLS indices")
    let singleton = actual.globals[String(0x53eca0)]!
    var ownerBytes = actual.ownerBytes
    ownerBytes[String(0x53eca0)] = (0..<4).map { UInt8(truncatingIfNeeded: singleton >> ($0*8)) }
    check(ownerBytes == expected.ownerBytes.mapValues { Array(unhex($0)) }, label+" owner bytes")
    check(actual.globals.filter { $0.key != String(0x53eca0) } == expected.globals && singleton == expected.moduleOwnerValue, label+" publications")
    check(actual.locals == expected.locals, label+" locals")
    check(actual.localBytes == expected.localBytes.mapValues { Array(unhex($0)) }, label+" local bytes")
    check(actual.allocations == expected.allocations, label+" allocation identity/lifetime")
    check(actual.allocationBytes == expected.allocationBytes.mapValues { Array(unhex($0)) }, label+" all live/retired bytes")
    check(actual.borrowedStorage == expected.borrowedStorage, label+" borrowed identity registration")
    check(actual.tlsValues == expected.tlsValues, label+" actual thread TLS values")
    check(expected.thread == 1 && actual.manager.managerBytes["5507832"] == Array(unhex(expected.staticManagerBytes)), label+" static manager/thread")
    check(state.locks.imageBytes == Array(unhex(expected.imageBytes)), label+" lock global bytes")
    check(state.sourceGlobalBytes == expected.sourceGlobalBytes.mapValues { Array(unhex($0)) }, label+" all source globals")
    for (address, byte) in expected.writtenImageBytes {
        let token = UInt32(address)!
        let spans = state.sourceGlobalBytes.merging(m.managerBytes) { a,_ in a }
        let span = spans.first { UInt32($0.key)! <= token && token - UInt32($0.key)! < UInt32($0.value.count) }
        check(span.map { $0.value[Int(token - UInt32($0.key)!)] } == unhex(byte).first, label+" written image byte "+address)
    }
    check(expected.staticOwnerIdentities.map(\.address) == [0x53ec9c,0x53eca0,0x540af0] && expected.staticOwnerIdentities.allSatisfy { $0.size == 4 }, label+" explicit pinned original owner identities")
}
func compareObservation(_ actual: Host.ModuleObservation, _ expected: Observation, _ label: String) {
    if let target = expected.importedTarget { check(actual.physical && actual.input.eip == target, label+" exact physical import identity") }
    check(actual.function == expected.function && actual.returnPC == expected.returnPC && actual.arguments == expected.arguments && actual.input.esp == expected.frame, label+" metadata/frame/args")
    check(cpu(actual.input) == expected.inputCPU, label+" input CPU actual \(cpu(actual.input)) expected \(expected.inputCPU)")
    check(actual.output.map(cpu) == expected.outputCPU, label+" output CPU actual \(String(describing: actual.output.map(cpu))) expected \(expected.outputCPU)")
    check(actual.completed == expected.completed, label+" completion actual \(actual.completed) expected \(expected.completed)")
    check(actual.stackBefore == unhex(expected.stackBefore), label+" full128KiB input stack")
    check(actual.stackAfter == unhex(expected.stackAfter), label+" full128KiB output stack")
    compare(actual.before, expected.before, label+" before"); compare(actual.after!, expected.after, label+" after")
}
let profiles = try JSONDecoder().decode([Profile].self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
check(profiles.count == 29, "frozen29profiles")
check(claw_canonical_lookup(0x4f50fd) == nil, "genuine missing throw")
func fixture(_ profile: Profile) throws -> (ClawTokenHeap, Host, ClawNativeMfcLocks, ClawNativeMfcMemory) {
    let heap = ClawTokenHeap(), host: Host; host = Host(heap: heap)
    let locks = try ClawNativeMfcLocks(host: host, sha256: profile.sha256, initialBytes: Array(unhex(profile.initialBytes)), importTargets: mapping(profile.lockImports))
    let memory = try ClawNativeMfcMemory(host: host, sha256: profile.sha256, importTargets: mapping(profile.imports).filter { $0.key != 0x546abc }, locks: locks)
    let cold = profile.steps[0].before
    for (token, bytes) in [(profile.manager,unhex(cold.staticManagerBytes)),(UInt32(0x53ec9c),unhex(cold.sourceGlobalBytes[String(0x53ec9c)]!)),(UInt32(0x540af0),unhex(cold.sourceGlobalBytes[String(0x5408e0)]!).subdata(in: 0x210..<0x218))] {
        bytes.withUnsafeBytes { heap.storeBytes(token: token, count: UInt32(bytes.count)).update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: bytes.count) }
    }
    try memory.registerManager(profile.manager); try memory.registerTLSOwner(profile.owner); try memory.registerTLSPublication(0x540af0); try memory.registerModuleSingleton()
    memory.incidentalResult = 0xa1b2c3d4; locks.incidentalResult = 0xa1b2c3d4
    return (heap,host,locks,memory)
}
func snapshot(_ heap: ClawTokenHeap, _ memory: ClawNativeMfcMemory, _ locks: ClawNativeMfcLocks) -> Host.ModuleSnapshot {
    var globals: [String:[UInt8]] = [:]
    for (base,count) in [(UInt32(0x53ec9c),8),(UInt32(0x5408e0),0x244)] {
        globals[String(base)] = (0..<count).map { heap.lookupBytes(base + UInt32($0), count: 1)![0] }
    }
    return .init(tls:memory.tlsSnapshot(),locks:locks.locksSnapshot(),sourceGlobalBytes:globals)
}
var roots = 0, physical = 0, entries = 0, referenceOnly = 0
var unobserved: [[String:Any]] = []
for profile in profiles {
    let (heap,host,locks,memory) = try fixture(profile)
    check(profile.preparations.isEmpty, "no prepared original caches")
    var physicalAttempt = 0, allocationAttempt = 0
    func beforePhysical(_ slot: UInt32) throws {
        physicalAttempt += 1
        if profile.physicalFailAt == physicalAttempt { throw ClawNativeMfcMemory.Failure.invalidOwnership }
    }
    memory.beforeService = { slot,_ in try beforePhysical(slot) }
    locks.beforeService = { _,slot,_ in try beforePhysical(slot) }
    memory.failAllocation = { slot in
        if slot == 0x546a90 { return profile.tlsFailure }
        if [UInt32(0x546b1c),0x546aa8,0x546a88,0x546a80].contains(slot) { allocationAttempt += 1 }
        return profile.allocationFailAt == allocationAttempt
    }
    let executed = host.withModuleSourceGraph(provider: memory) { graph in
        for (index,step) in profile.steps.enumerated() {
            let label = "\(profile.name) step \(index)"
            compare(snapshot(heap,memory,locks),step.before,label+" before")
            check(graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(step.stackBefore)),label+" stack input")
            var c = context(step.inputContext)
            let result = graph.invokeSource(at: .moduleGet, context: &c)
            check(result.completed == step.completed && result.eax == step.eax,label+" completion/EAX fault=\(String(describing:host.fault))")
            check(graph.tlsOutput.map(cpu) == step.outputCPU,label+" deepest output CPU actual \(String(describing:graph.tlsOutput.map(cpu))) expected \(step.outputCPU)")
            if let output = step.outputContext { check(fields(c) == output,label+" full output context") }
            check(graph.tlsStack == unhex(step.stackAfter),label+" full128KiB root stack")
            compare(snapshot(heap,memory,locks),step.after,label+" after")
            check(graph.moduleObservations.filter(\.physical).count == step.eventCount,label+" physical count")
            if step.outcome == "missing-native-dependency-prefix" {
                check(result.fault?.address == 0x4f50fd && result.fault?.diagnostic == .missingDependency,label+" exact unsupported boundary")
            } else if step.outcome == "physical-host-stop" {
                check(result.fault?.address == profile.events[step.eventCount-1].function,label+" exact physical safety stop")
            } else { check(result.fault == nil && step.outcome == "returned",label+" normal return") }
            roots += 1
        }
        let actualPhysical = graph.moduleObservations.filter(\.physical)
        check(actualPhysical.count == profile.events.count && memory.events.count + locks.events.count == profile.events.count,"both physical owners execute each service once")
        for (i,pair) in zip(actualPhysical,profile.events).enumerated() {
            compareObservation(pair.0,pair.1,"\(profile.name) physical \(i) pc \(String(pair.1.returnPC,radix:16))")
            if pair.1.completed { check(pair.0.output?.eax == pair.1.result,"physical result") }
            physical += 1
        }
        // Constructors are separately dispatched and can be compared; only the
        // getter-owned setter and lock-owned initializer lack native entry hooks.
        let observed = profile.entries.filter { e in
            if e.function == 0x503167 || e.function == 0x502e47 {
                referenceOnly += 1
                unobserved.append(["profile":profile.name,"root_step":e.rootStep,"function":e.function,"return_pc":e.returnPC,"frame":e.frame]); return false
            }
            return true
        }
        let actualEntries = graph.moduleObservations.filter { !$0.physical }
        check(actualEntries.count == observed.count,"dispatched entry count actual \(actualEntries.count) expected \(observed.count)")
        for (i,pair) in zip(actualEntries,observed).enumerated() {
            compareObservation(pair.0,pair.1,"\(profile.name) entry \(i) function \(String(pair.1.function,radix:16))"); entries += 1
        }
        // Compare the joint partial order, dropping only original-only hooks and
        // their returns. Same-PC original hooks need no fabricated native scope.
        func key(_ kind: String,_ function: UInt32,_ pc: UInt32,_ frame: UInt32) -> String { "\(kind):\(function):\(pc):\(frame)" }
        var nativeOrder: [(Int,String)] = [], originalOrder: [(Int,String)] = []
        for e in graph.moduleObservations {
            let tag = e.physical ? "physical" : "entry"
            nativeOrder.append((e.order,key(tag,e.function,e.returnPC,e.input.esp)))
            if e.completed, let returned = e.returnOrder { nativeOrder.append((returned,key(tag+"-return",e.function,e.returnPC,e.input.esp))) }
        }
        for e in profile.events + observed {
            let tag = e.importedTarget == nil ? "entry" : "physical"
            originalOrder.append((e.order,key(tag,e.function,e.returnPC,e.frame)))
            if e.completed, let returned = e.returnOrder { originalOrder.append((returned,key(tag+"-return",e.function,e.returnPC,e.frame))) }
        }
        check(nativeOrder.sorted { $0.0 < $1.0 }.map(\.1) == originalOrder.sorted { $0.0 < $1.0 }.map(\.1),profile.name+" complete mixed-provider boundary order")
        return true
    }
    check(executed == true,"executed module graph")
    FileHandle.standardError.write(Data(("PASS profile "+profile.name+"\n").utf8))
}
check(roots == 30 && physical == 336 && entries + referenceOnly == 339,"frozen reference totals")
let originalAssertions = checks
func word(_ value: UInt32) -> Data { var v=value.littleEndian; return withUnsafeBytes(of:&v) { Data($0) } }
let first = profiles[0].steps[0]
func call(_ graph: Host.SourceGraph) -> Host.Completion {
    _ = graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(first.stackBefore))
    var c=context(first.inputContext);return graph.invokeSource(at:.moduleGet,context:&c)
}
func replace(_ heap: ClawTokenHeap,_ token: UInt32,_ size: UInt32) {
    let bytes=Array(UnsafeBufferPointer(start:heap.lookupBytes(token,count:size)!,count:Int(size)))
    heap.withStableFreedStorage { heap.free(token);heap.storeBytes(token:token,count:size).update(from:bytes,count:bytes.count) }
}
for variant in 0..<13 {
    let (_,host,locks,memory)=try fixture(profiles[0])
    host.withModuleSourceGraph(provider:memory) { graph in
        _=graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:unhex(first.stackBefore))
        var c=context(first.inputContext)
        switch variant {
        case 0:c.size=0
        case 1:c.version=2
        case 2:c.inputMask=0
        case 3:c.outputMask=0
        case 4:c.preserveMask=0
        case 5:c.reserved0=1
        case 6:c.reserved1=1
        case 7:c.eip=0x503420
        case 8:c.esp+=1
        case 9:c.esp=UInt32(CLAW_STACK_BASE)+4
        case 10:c.eflags=0
        case 11:c.fsHead=0
        default:_=graph.writeStack(at:c.esp,data:word(0x50229e))
        }
        check(!graph.invokeSource(at:.moduleGet,context:&c).completed,"invalid root rejected")
        check(memory.events.isEmpty && locks.events.isEmpty,"invalid root cannot reach owner")
    }
}
for variant in 0..<4 {
    let (heap,host,locks,memory)=try fixture(profiles[0]);var triggered=false
    var beforeAttack:[ClawNativeMfcLocks.State] = []
    locks.beforeService = { _,slot,args in
        if slot == 0x546a9c && args == [0x540a70] && !triggered {
            triggered=true;beforeAttack=locks.states
            check(beforeAttack.first { $0.section == 0x540a70 }?.depth == 1,"attack starts while numbered lock held")
            switch variant {
            case 0:replace(heap,0x53ec9c,8)
            case 1:let token=heap.lookup(0x53eca0,words:1)![0];replace(heap,token,0x1074)
            case 2:
                var nested=ClawCall();nested.function=0x546a90;nested.stackPointer=first.frame
                _=memory.service(nested)
            default:
                check(host.withModuleSourceGraph(provider:memory) { _ in true } == nil,"nested module graph rejected")
            }
        }
    }
    host.withModuleSourceGraph(provider:memory) { graph in
        check(!call(graph).completed,"final unlock identity/reentry fault")
        check(triggered && host.fault != nil,"final unlock attack reached and stopped")
        check(locks.states == beforeAttack,"invalid owner cannot decrement lock depth or change counters")
        check(locks.states.first { $0.section == 0x540a70 }?.depth == 1,"invalid owner leaves numbered lock held")
        check(locks.events.last?.completed == false,"invalid final unlock has no completed physical service")
    }
}
for token in [UInt32(0x53ec9c),0x540af0] {
    let (heap,host,locks,memory)=try fixture(profiles[0]);replace(heap,token,8)
    check(host.withModuleSourceGraph(provider:memory) { _ in true } == nil,"replaced static owner rejected")
    check(memory.events.isEmpty && locks.events.isEmpty,"owner replacement has no physical effects")
}
do {
    let (_,host,_,memory)=try fixture(profiles[0]);var escaped:Host.SourceGraph?
    host.withModuleSourceGraph(provider:memory) { graph in escaped=graph }
    check(!call(escaped!).completed,"expired graph rejected")
}
do {
    let (_,host,_,_)=try fixture(profiles[0]);let (_,_,_,other)=try fixture(profiles[0])
    check(host.withModuleSourceGraph(provider:other) { _ in true } == nil,"foreign host providers rejected")
}
// The composed lock path carries the same one-use lease through both owners.
do {
    let (_,host,locks,memory)=try fixture(profiles[0]);var reached=false
    locks.beforeSourceService = { request in
        reached=true
        check(locks.serviceSourceLocks(request) == nil,"consumed composed request replay rejected")
    }
    host.withModuleSourceGraph(provider:memory) { graph in
        check(!call(graph).completed && reached && host.fault != nil,"replayed lock lease aborts composed graph")
    }
}
do {
    let (_,host,locks,memory)=try fixture(profiles[0]);var saved:Host.SourceLocksRequest?
    locks.beforeSourceService = { saved=$0 }
    host.withModuleSourceGraph(provider:memory) { graph in check(call(graph).completed,"lease-expiry setup executes complete source") }
    check(saved != nil,"real composed request captured")
    check(locks.serviceSourceLocks(saved!) == nil && host.fault != nil,"expired composed request rejected")
}
do {
    let (_,host,locks,memory)=try fixture(profiles[0]);var saved:Host.SourceLocksRequest?
    locks.beforeSourceService = { saved=$0 }
    host.withModuleSourceGraph(provider:memory) { graph in check(call(graph).completed,"foreign-lease setup executes complete source") }
    let (_,otherHost,otherLocks,otherMemory)=try fixture(profiles[0])
    check(otherLocks.serviceSourceLocks(saved!) == nil && otherHost.fault != nil,"foreign-host composed request rejected")
    check(otherLocks.events.isEmpty && otherMemory.events.isEmpty,"foreign request has no effects")
}
do {
    let (_,host,locks,memory)=try fixture(profiles[0]);var reached=false
    locks.beforeService = { _,_,_ in reached=true;_ = try memory.createTLSOwner() }
    host.withModuleSourceGraph(provider:memory) { graph in
        check(!call(graph).completed && reached,"cross-owner setup during physical service rejected")
    }
}
do {
    let (_,host,locks,memory)=try fixture(profiles[0]);let (_,otherHost,otherLocks,_)=try fixture(profiles[0])
    var reached=false
    locks.beforeSourceService = { request in
        if reached { return };reached=true
        check(!request.consume(for:host,provider:otherLocks) && !request.consume(for:otherHost,provider:locks),"wrong provider and host request identity")
        let done=DispatchSemaphore(value:0)
        Thread.detachNewThread {
            check(!request.consume(for:host,provider:locks) && !request.validReturn(for:host),"foreign thread has no composed lease authority")
            check(locks.serviceSourceLocks(request) == nil,"foreign thread cannot drive physical owner")
            done.signal()
        }
        done.wait()
        check(host.fault == nil,"foreign thread cannot fault legitimate issuer")
    }
    host.withModuleSourceGraph(provider:memory) { graph in check(call(graph).completed && reached,"valid composed request survives rejected foreign attempts") }
}
do {
    let (_,host,locks,memory)=try fixture(profiles[0])
    host.withModuleSourceGraph(provider:memory) { graph in
        _=graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:unhex(first.stackBefore))
        var c=context(first.inputContext);c.eip=0x502369;c.preserveMask=0x472
        check(!graph.invokeSource(at:.moduleFactory,context:&c).completed,"module graph cannot elect unrelated root")
        check(memory.events.isEmpty && locks.events.isEmpty,"unrelated root has no physical effects")
    }
}
// Both effect-capable Memory hooks must reject an ABA of the retained thread
// allocation before executing the next container allocation.
for allocationHook in [false,true] {
    let (heap,host,locks,memory)=try fixture(profiles[0]);var triggered=false
    var allocationCount=0
    func invalidateRetainedThread() {
        guard !triggered, let allocation=memory.tlsSnapshot().allocations.first(where: { $0.size == 0x118 && $0.live }) else { return }
        triggered=true;allocationCount=memory.tlsSnapshot().allocations.count
        replace(heap,allocation.address,allocation.size)
    }
    if allocationHook {
        memory.failAllocation = { slot in if slot == 0x546aa8 { invalidateRetainedThread() };return false }
    } else {
        memory.beforeService = { slot,args in if slot == 0x546aa8 && args == [0x40,16] { invalidateRetainedThread() } }
    }
    host.withModuleSourceGraph(provider:memory) { graph in
        check(!call(graph).completed && triggered,"Memory callback owner ABA is rejected")
        check(memory.tlsSnapshot().allocations.count == allocationCount,"Memory callback cannot allocate after authority loss")
        check(memory.events.last?.result == nil && memory.events.last?.completed == false,"Memory callback invalidation stops before physical allocation")
        check(locks.events.isEmpty,"allocation attack cannot reach singleton lock or publication")
        check(heap.lookup(0x53eca0,words:1)![0] == 0,"allocation attack cannot publish singleton")
    }
}
let report:[String:Any] = ["status":"pass","profiles":profiles.count,"roots":roots,"physical_events":physical,"reference_entries":entries+referenceOnly,"observed_entries":entries,"reference_only_entries":referenceOnly,"unobserved_sites":unobserved,"assertions":checks,"original_assertions":originalAssertions,"native_controls":checks-originalAssertions,"catch_executed":false,"application_getter_executed":false]
print(String(data:try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]),encoding:.utf8)!)
