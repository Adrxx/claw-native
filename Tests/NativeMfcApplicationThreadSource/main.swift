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
    let interiorOwners: [Host.TLSInteriorOwner]
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
    let bridgeIndex: Int?, inputProvenance: String?
}
struct Preparation: Decodable { let label: String, beforeStep: Int, writes: [String: UInt32] }
struct Bridge: Decodable {
    let fromPC: UInt32, toPC: UInt32, inputCPU: [String:UInt32], outputCPU: [String:UInt32]
    let stackBefore: String, stackAfter: String, before: Snapshot, after: Snapshot, rootStep: Int
}
struct Profile: Decodable {
    let name: String, sha256: String, initialBytes: String, imports: [String: UInt32], lockImports: [String: UInt32]
    let manager: UInt32, owner: UInt32, preparations: [Preparation]
    let steps: [Step], events: [Observation], entries: [Observation]
    let allocationFailAt: Int?, physicalFailAt: Int?, tlsFailure: Bool
    let bridges: [Bridge]
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
    check(state.interiorOwners == expected.interiorOwners,label+" live interior owner allocation identity")
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
func word(_ value: UInt32) -> Data { var v=value.littleEndian; return withUnsafeBytes(of:&v) { Data($0) } }
let profiles = try JSONDecoder().decode([Profile].self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
check(profiles.count == 10, "frozen10profiles")
check(claw_canonical_lookup(0x4f50fd) == nil, "genuine missing throw")
func fixture(_ profile: Profile, maximumOperations: UInt32 = 0) throws -> (ClawTokenHeap, Host, ClawNativeMfcLocks, ClawNativeMfcMemory) {
    let heap = ClawTokenHeap(), host: Host; host = Host(heap: heap, maximumOperations: maximumOperations)
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
    return .init(tls:memory.tlsSnapshot(),locks:locks.locksSnapshot(),sourceGlobalBytes:globals,interiorOwners:memory.applicationTLSOwnerSnapshot())
}
var roots = 0, physical = 0, entries = 0, referenceOnly = 0, bridges = 0
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
        var previous: ClawSourceContext?
        for (index,step) in profile.steps.enumerated() {
            let label = "\(profile.name) step \(index)"
            var c: ClawSourceContext
            if step.function == 0x50335e {
                guard let prior = previous, let bridgeIndex = step.bridgeIndex else { fatalError("missing native caller provenance") }
                c = prior
                let bridge = profile.bridges[bridgeIndex]
                check(c.eip == 0x5025bd && bridge.fromPC == 0x5025bd && bridge.toPC == 0x50335e,"exact test caller boundary")
                check(graph.registerApplicationTLSOwner(module:c.eax),"register actual returned module interior owner")
                check(cpu(c) == bridge.inputCPU && graph.stackSnapshot() == unhex(bridge.stackBefore),label+" caller bridge native input")
                compare(snapshot(heap,memory,locks),bridge.before,label+" bridge before")
                // Test caller: execute only the four verified boundary actions.
                // No root registers or stack bytes are copied from the reference.
                c.ebx = c.eax
                c.esp -= 4;check(graph.writeStack(at:c.esp,data:word(0x502301)),"caller PUSH factory")
                c.ecx = c.ebx + 0x1070
                c.esp -= 4;check(graph.writeStack(at:c.esp,data:word(0x5025cf)),"caller CALL return")
                c.eip = 0x50335e
                check(cpu(c) == bridge.outputCPU && graph.stackSnapshot() == unhex(bridge.stackAfter),label+" exact derived bridge output")
                compare(snapshot(heap,memory,locks),bridge.after,label+" bridge after")
                check(fields(c) == step.inputContext && graph.stackSnapshot() == unhex(step.stackBefore),label+" derived application input")
                bridges += 1
            } else {
                check(step.function == 0x50228f && step.bridgeIndex == nil,"external module root only")
                check(graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: unhex(step.stackBefore)),label+" stack input")
                c = context(step.inputContext)
            }
            compare(snapshot(heap,memory,locks),step.before,label+" before")
            let result = graph.invokeSource(at:step.function == 0x50228f ? .moduleGet : .applicationTLSGet, context: &c)
            if result.completed { previous = c }
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
            if [UInt32(0x503167),0x502e47,0x50210b,0x4f5e89,0x4f5133].contains(e.function) {
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
check(roots == 22 && physical == 267 && entries + referenceOnly == 300 && bridges == 11,"frozen application reference totals")
let originalAssertions = checks
func prepareApplication(_ graph: Host.SourceGraph) -> ClawSourceContext {
    let step=profiles[0].steps[0]
    check(graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:unhex(step.stackBefore)),"control module caller stack")
    var c=context(step.inputContext)
    check(graph.invokeSource(at:.moduleGet,context:&c).completed,"control real module construction")
    check(graph.registerApplicationTLSOwner(module:c.eax),"control real interior owner registration")
    c.ebx=c.eax;c.esp-=4;_ = graph.writeStack(at:c.esp,data:word(0x502301))
    c.ecx=c.ebx+0x1070;c.esp-=4;_ = graph.writeStack(at:c.esp,data:word(0x5025cf));c.eip=0x50335e
    return c
}
func replace(_ heap:ClawTokenHeap,_ token:UInt32,_ count:UInt32) {
    let bytes=Array(UnsafeBufferPointer(start:heap.lookupBytes(token,count:count)!,count:Int(count)))
    heap.withStableFreedStorage { heap.free(token);heap.storeBytes(token:token,count:count).update(from:bytes,count:bytes.count) }
}
for variant in 0..<16 {
    let (_,host,locks,memory)=try fixture(profiles[0])
    host.withModuleSourceGraph(provider:memory) { graph in
        var c=prepareApplication(graph);let before=memory.events.count+locks.events.count
        switch variant {
        case 0:c.size=0
        case 1:c.version=2
        case 2:c.inputMask=0
        case 3:c.outputMask=0
        case 4:c.preserveMask=0x472
        case 5:c.reserved0=1
        case 6:c.reserved1=1
        case 7:c.eip=0x502301
        case 8:c.ecx-=4
        case 9:c.esp+=1
        case 10:c.eflags=0
        case 11:c.fsHead=0
        case 12:_ = graph.writeStack(at:c.esp,data:word(0x50229e))
        case 13:_ = graph.writeStack(at:c.esp+4,data:word(0x502335))
        case 14:_ = graph.writeStack(at:c.esp+4,data:word(0x502302))
        default:c.esp=UInt32(CLAW_STACK_END)-4
        }
        check(!graph.invokeSource(at:.applicationTLSGet,context:&c).completed,"invalid application root rejected")
        check(memory.events.count+locks.events.count==before,"invalid app root cannot reach physical owner")
    }
}
// The entire allocation identity, including its interior slot, is checked both
// at entry and after hooks, before real TLS publication or allocation effects.
for variant in 0..<5 {
    let (heap,host,locks,memory)=try fixture(profiles[0])
    host.withModuleSourceGraph(provider:memory) { graph in
        var c=prepareApplication(graph);let module=c.eax;let callerESP=c.esp
        var reached=false, allocationsBefore=0;var sectionsBefore:[ClawNativeMfcLocks.State]=[]
        memory.beforeService = { slot,args in
            let match = variant==0 || variant==4 ? slot==0x546aac : slot==0x546a84
            guard match && !reached else { return }
            reached=true;allocationsBefore=memory.tlsSnapshot().allocations.count;sectionsBefore=memory.sectionStates
            if variant==0 || variant==1 { replace(heap,module,0x1074) }
            else if variant==2 {
                let app=memory.tlsSnapshot().allocations.first { $0.live && $0.size==0x84 }!
                replace(heap,app.address,app.size)
            } else if variant==3 {
                var nested=ClawCall();nested.function=0x546abc;nested.stackPointer=callerESP
                _=locks.service(nested)
            } else {
                check(host.withModuleSourceGraph(provider:memory) { _ in true } == nil,"application nested graph rejected")
            }
        }
        check(!graph.invokeSource(at:.applicationTLSGet,context:&c).completed && reached,"application ownership/reentry attack rejected")
        check(memory.tlsSnapshot().allocations.count==allocationsBefore,"no allocation after application authority loss")
        check(memory.sectionStates==sectionsBefore,"no physical section mutation after application authority loss")
        check(memory.events.last?.completed==false,"attacked application physical service incomplete")
        if variant != 0 && variant != 4 {
            let container=memory.tlsValue(heap.lookup(0x540af8,words:1)![0])!
            let array=heap.lookup(container,words:4)![3]
            check(heap.lookup(array+8,words:1)![0]==0,"no application value publication after rejected TLS service")
        }
    }
}
do {
    let (heap,host,locks,memory)=try fixture(profiles[0])
    host.withModuleSourceGraph(provider:memory) { graph in
        check(!graph.registerApplicationTLSOwner(module:0x62000000),"unconstructed module cannot register owner")
        var c=prepareApplication(graph);let before=memory.events.count+locks.events.count
        replace(heap,c.eax,0x1074)
        check(!graph.invokeSource(at:.applicationTLSGet,context:&c).completed,"interior owner ABA before root rejected")
        check(memory.events.count+locks.events.count==before,"interior owner ABA has no physical effects")
    }
}
do {
    let (_,host,_,memory)=try fixture(profiles[0]);var expired:Host.SourceGraph?;var c=ClawSourceContext()
    host.withModuleSourceGraph(provider:memory) { graph in expired=graph;c=prepareApplication(graph) }
    check(!expired!.registerApplicationTLSOwner(module:c.eax),"expired graph cannot register interior owner")
    check(!expired!.invokeSource(at:.applicationTLSGet,context:&c).completed,"expired application graph rejected")
}
do {
    let (_,host,_,memory)=try fixture(profiles[0])
    host.withModuleSourceGraph(provider:memory) { graph in
        var c=prepareApplication(graph)
        var compiler=ClawCompilerContext();compiler.size=72;compiler.version=1;compiler.inputMask=0x7ff;compiler.outputMask=0x7ff
        compiler.eip=0x4a48c0;compiler.continuation=0x502115;compiler.eax=0x5084ca;compiler.esp=c.esp-28;compiler.eflags=2;compiler.fsHead=UInt32.max
        check(!graph.invokeCompiler(at:.applicationConstructor,context:&compiler).completed,"owned constructor compiler scope cannot be invented as root")
        check(!graph.invokeSource(at:.applicationTLSGet,context:&c).completed,"compiler scope forgery leaves sticky graph fault")
    }
}
// Reallocating the value array must retain the container across both hooks.
for failureHook in [false,true] {
    let (heap,host,_,memory)=try fixture(profiles[0])
    host.withModuleSourceGraph(provider:memory) { graph in
        var c=prepareApplication(graph);var reached=false;var before:[Host.TLSAllocation]=[];var attacked:UInt32=0
        func attack() {
            guard !reached else { return };reached=true
            before=memory.tlsSnapshot().allocations
            let container=memory.tlsValue(heap.lookup(0x540af8,words:1)![0])!
            attacked=container;replace(heap,container,16)
        }
        if failureHook { memory.failAllocation = { slot in if slot==0x546a80 { attack() };return false } }
        else { memory.beforeService = { slot,_ in if slot==0x546a80 { attack() } } }
        check(!graph.invokeSource(at:.applicationTLSGet,context:&c).completed && reached,"TLS realloc container authority rejected")
        let after=memory.tlsSnapshot().allocations
        check(after.count==before.count && after.filter { $0.address != attacked } == before.filter { $0.address != attacked },"rejected realloc neither allocates nor retires old array")
        check(memory.events.last?.result==nil && memory.events.last?.completed==false,"rejected realloc has no physical result")
    }
}
// The preceding module root and application continuation share one lease/thread
// authority. A consumed lock lease cannot be replayed from an application hook.
do {
    let (_,host,locks,memory)=try fixture(profiles[0]);var saved:Host.SourceLocksRequest?
    locks.beforeSourceService = { saved=$0 }
    host.withModuleSourceGraph(provider:memory) { graph in
        var c=prepareApplication(graph);var reached=false
        let sections=memory.sectionStates
        memory.beforeService = { _,_ in
            guard !reached else { return };reached=true
            check(locks.serviceSourceLocks(saved!)==nil,"module lease replay during application rejected")
        }
        check(!graph.invokeSource(at:.applicationTLSGet,context:&c).completed && reached,"lease replay cannot continue application")
        check(memory.sectionStates==sections && memory.events.last?.completed==false,"lease replay has no physical application effect")
    }
    check(!saved!.consume(for:host,provider:locks),"expired composed lease remains unusable")
}
do {
    let (_,host,locks,memory)=try fixture(profiles[0]);let (_,otherHost,otherLocks,_)=try fixture(profiles[0]);var reached=false
    locks.beforeSourceService = { request in
        guard !reached else { return };reached=true
        check(!request.consume(for:host,provider:otherLocks) && !request.consume(for:otherHost,provider:locks),"application graph rejects foreign lease host/provider")
        let done=DispatchSemaphore(value:0)
        Thread.detachNewThread {
            check(!request.consume(for:host,provider:locks) && !request.validReturn(for:host),"foreign thread has no application graph lease")
            check(locks.serviceSourceLocks(request)==nil,"foreign thread cannot drive application graph owner")
            done.signal()
        }
        done.wait()
        check(host.fault==nil,"foreign lease attempt preserves legitimate application issuer")
    }
    host.withModuleSourceGraph(provider:memory) { graph in
        var c=prepareApplication(graph)
        check(graph.invokeSource(at:.applicationTLSGet,context:&c).completed && reached,"same graph application survives rejected foreign lease attempts")
    }
}
// Small source budgets stop actual native instructions. Reusing the same graph
// cannot reset the exhausted budget or erase its sticky fault.
for budget in [UInt32(1),100] {
    let (_,host,locks,memory)=try fixture(profiles[0],maximumOperations:budget)
    host.withModuleSourceGraph(provider:memory) { graph in
        let step=profiles[0].steps[0];_ = graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:unhex(step.stackBefore))
        var c=context(step.inputContext)
        check(!graph.invokeSource(at:.moduleGet,context:&c).completed && host.fault?.code==UInt32(CLAW_FAULT_BUDGET),"finite composed source budget")
        let count=memory.events.count+locks.events.count
        check(!graph.invokeSource(at:.applicationTLSGet,context:&c).completed && memory.events.count+locks.events.count==count,"budget exhaustion cannot escape into next root")
    }
}
let report:[String:Any] = ["status":"pass","profiles":profiles.count,"roots":roots,"physical_events":physical,"reference_entries":entries+referenceOnly,"observed_entries":entries,"reference_only_entries":referenceOnly,"unobserved_sites":unobserved,"bridges":bridges,"assertions":checks,"original_assertions":originalAssertions,"native_controls":checks-originalAssertions,"catch_executed":false,"application_getter_executed":true,"whole_cwinapp_executed":false]
print(String(data:try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]),encoding:.utf8)!)
