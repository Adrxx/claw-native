import Foundation

typealias Host = ClawNativeCanonicalHost
struct InputRange: Decodable { let address:UInt32,size:UInt32,bytes:String }
struct Snapshot: Decodable {
    let receiver:UInt32, receiverBytes:String,inputRanges:[InputRange],currentThreadHandle:UInt32,currentThreadId:UInt32,lastError:UInt32
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
    let eventCount: Int, entryCount: Int,order:Int,returnOrder:Int?
    let bridgeIndex: Int?, inputProvenance: String?
}
struct Preparation: Decodable { let label: String, beforeStep: Int, writes: [String: UInt32] }
struct Bridge: Decodable {
    let fromPC: UInt32, toPC: UInt32, inputCPU: [String:UInt32], outputCPU: [String:UInt32]
    let stackBefore: String, stackAfter: String, before: Snapshot, after: Snapshot, rootStep: Int
}
struct MissingPrefix:Decodable {let entryIndex:Int,function:UInt32,order:Int}
struct Profile: Decodable {
    let name: String, sha256: String, initialBytes: String, imports: [String: UInt32], lockImports: [String: UInt32]
    let manager: UInt32, owner: UInt32, preparations: [Preparation]
    let steps: [Step], events: [Observation], entries: [Observation]
    let allocationFailAt: Int?, physicalFailAt: Int?, tlsFailure: Bool
    let bridges: [Bridge]
    let initialImageData:String,imageDataStart:UInt32,profileIndex:Int
    let cursorSuccess:Bool,cursorPoint:[Int32],threadHandle:UInt32,threadId:UInt32,mallocNull:Bool,mallocRescan:String?,tlsSetFalse:Bool
    let missingNativePrefixes:[MissingPrefix]
    let referenceOnlyEntries:[UInt32]
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
func compare(_ state: Host.ModuleSnapshot, _ expected: Snapshot, _ label: String, order:Int = Int.max) {
    check(state.applicationBytes[String(expected.receiver)]==Array(unhex(expected.receiverBytes)),label+" receiver bytes")
    for range in expected.inputRanges {check(state.applicationBytes[String(range.address)]==Array(unhex(range.bytes)),label+" caller input bytes")}
    var image=initialImageBytes
    for (address,bytes) in expected.writtenImageBytes {image[Int(UInt32(address)!-profile.imageDataStart)]=unhex(bytes).first!}
    // Emulator service writes do not enter the instruction-store ledger.
    // Replay their frozen event-time cursor bytes when reconstructing image data.
    for event in profile.events where profile.cursorSuccess && event.function==0x546cd0 && event.completed && (event.returnOrder ?? Int.max)<=order {
        let destination=event.arguments[0]
        if destination>=profile.imageDataStart && UInt64(destination)+8<=UInt64(profile.imageDataStart)+UInt64(image.count) {
            check((0..<8).allSatisfy {expected.writtenImageBytes[String(destination+UInt32($0))]==nil},label+" cursor physical bytes disjoint from instruction-store ledger")
            let bytes=Array(unhex(event.after.receiverBytes))[0x5c..<0x64]
            image.replaceSubrange(Int(destination-profile.imageDataStart)..<Int(destination-profile.imageDataStart)+8,with:bytes)
        }
    }
    let actualImage=state.applicationBytes[String(profile.imageDataStart)]!
    check(actualImage==image,label+" complete image data baseline and writes mismatches \(zip(actualImage,image).enumerated().filter { $0.element.0 != $0.element.1 }.prefix(12).map { (String(profile.imageDataStart+UInt32($0.offset),radix:16),$0.element.0,$0.element.1) })")
    check(expected.currentThreadHandle==profile.threadHandle && expected.currentThreadId==profile.threadId && expected.lastError==0,label+" physical logical thread policy")
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
    check(expected.thread == profile.threadId && actual.manager.managerBytes["5507832"] == Array(unhex(expected.staticManagerBytes)), label+" static manager/thread")
    check(state.locks.imageBytes == Array(unhex(expected.imageBytes)), label+" lock global bytes")
    check(state.sourceGlobalBytes == expected.sourceGlobalBytes.mapValues { Array(unhex($0)) }, label+" all source globals")
    for (address, byte) in expected.writtenImageBytes {
        let token = UInt32(address)!
        let spans = state.applicationBytes.merging(state.sourceGlobalBytes) { a,_ in a }.merging(m.managerBytes) { a,_ in a }
        let span = spans.first { UInt32($0.key)! <= token && token - UInt32($0.key)! < UInt32($0.value.count) }
        check(span.map { $0.value[Int(token - UInt32($0.key)!)] } == unhex(byte).first, label+" written image byte "+address)
    }
    check(expected.staticOwnerIdentities.map(\.address) == [0x53ec9c,0x53eca0,0x540af0] && expected.staticOwnerIdentities.allSatisfy { $0.size == 4 }, label+" explicit pinned original owner identities")
}
func compareObservation(_ actual: Host.ModuleObservation, _ expected: Observation, _ label: String) {
    if let target = expected.importedTarget { check(actual.physical && actual.input.eip == target, label+" exact physical import identity") }
    check(actual.function == expected.function && actual.returnPC == expected.returnPC && actual.arguments == expected.arguments && actual.input.esp == expected.frame, label+" metadata/frame/args")
    check(cpu(actual.input) == expected.inputCPU, label+" input CPU actual \(cpu(actual.input)) expected \(expected.inputCPU)")
    check(actual.stackBefore == unhex(expected.stackBefore), label+" full128KiB input stack")
    compare(actual.before,expected.before,label+" before",order:expected.order)
    if let prefix=missingPrefix,expected.order<=prefix.order,(expected.returnOrder ?? Int.max)>prefix.order {
        check(!actual.completed,label+" missing dependency ancestor incomplete")
        check(actual.output.map(cpu)==prefix.inputCPU,label+" exact deepest missing dependency CPU")
        check(actual.stackAfter==unhex(prefix.stackBefore),label+" missing dependency full stack")
        compare(actual.after!,prefix.before,label+" missing dependency state",order:prefix.order)
    } else {
        check(actual.output.map(cpu)==expected.outputCPU,label+" output CPU actual \(String(describing:actual.output.map(cpu))) expected \(expected.outputCPU)")
        check(actual.completed==expected.completed,label+" completion")
        check(actual.stackAfter==unhex(expected.stackAfter),label+" full128KiB output stack")
        compare(actual.after!,expected.after,label+" after",order:expected.returnOrder ?? Int.max)
    }
}
func word(_ value: UInt32) -> Data { var v=value.littleEndian; return withUnsafeBytes(of:&v) { Data($0) } }
// The original profileIndex is a variation seed, reused for failure scenarios.
// The builder supplies the distinct ordinal from the hash-pinned shard index.
precondition(CommandLine.arguments.count == 3)
let shardIndex = Int(CommandLine.arguments[2])!
precondition((0..<61).contains(shardIndex))
let profile = try JSONDecoder().decode(Profile.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
let initialImageBytes=Array(unhex(profile.initialImageData))
let missingPrefix=profile.missingNativePrefixes.first.map {profile.entries[$0.entryIndex]}
let comparedEvents=profile.events.filter {$0.order<(missingPrefix?.order ?? Int.max)}
let comparedEntries=profile.entries.filter {$0.order<=(missingPrefix?.order ?? Int.max)}
check(claw_canonical_lookup(0x4f50fd) == nil, "genuine missing throw")
func fixture(_ profile: Profile, maximumOperations: UInt32 = 0) throws -> (ClawTokenHeap, Host, ClawNativeMfcLocks, ClawNativeMfcMemory) {
    let heap = ClawTokenHeap(), host: Host; host = Host(heap: heap, maximumOperations: maximumOperations)
    let locks = try ClawNativeMfcLocks(host: host, sha256: profile.sha256, initialBytes: Array(unhex(profile.initialBytes)), importTargets: mapping(profile.lockImports),logicalThread:profile.threadId)
    let memory = try ClawNativeMfcMemory(host: host, sha256: profile.sha256, importTargets: mapping(profile.imports).filter { ClawNativeMfcMemory.importArities[$0.key] != nil }, locks: locks,logicalThread:profile.threadId)
    let cold = profile.steps[0].before
    for (token, bytes) in [(profile.manager,unhex(cold.staticManagerBytes)),(UInt32(0x53ec9c),unhex(cold.sourceGlobalBytes[String(0x53ec9c)]!)),(UInt32(0x540af0),unhex(cold.sourceGlobalBytes[String(0x5408e0)]!).subdata(in: 0x210..<0x218))] {
        bytes.withUnsafeBytes { heap.storeBytes(token: token, count: UInt32(bytes.count)).update(from: $0.bindMemory(to: UInt8.self).baseAddress!, count: bytes.count) }
    }
    try memory.registerManager(profile.manager); try memory.registerTLSOwner(profile.owner); try memory.registerTLSPublication(0x540af0); try memory.registerModuleSingleton()
    try memory.configureApplicationServices(importTargets:mapping(profile.imports).filter {[UInt32(0x546cd0),0x5469bc,0x5469c0].contains($0.key)},cursorSuccess:profile.cursorSuccess,x:profile.cursorPoint[0],y:profile.cursorPoint[1],threadHandle:profile.threadHandle)
    let image=initialImageBytes;var offset=0
    while offset<image.count {
        if heap.lookupBytes(profile.imageDataStart+UInt32(offset),count:1) != nil { offset+=1;continue }
        let start=offset
        while offset<image.count && heap.lookupBytes(profile.imageDataStart+UInt32(offset),count:1)==nil {offset+=1}
        let bytes=Array(image[start..<offset]);heap.storeBytes(token:profile.imageDataStart+UInt32(start),count:UInt32(bytes.count)).update(from:bytes,count:bytes.count)
    }
    memory.incidentalResult = 0xa1b2c3d4; locks.incidentalResult = 0xa1b2c3d4
    return (heap,host,locks,memory)
}
func snapshot(_ heap: ClawTokenHeap, _ memory: ClawNativeMfcMemory, _ locks: ClawNativeMfcLocks) -> Host.ModuleSnapshot {
    var globals: [String:[UInt8]] = [:]
    for (base,count) in [(UInt32(0x53ec9c),8),(UInt32(0x5408e0),0x244)] {
        globals[String(base)] = (0..<count).map { heap.lookupBytes(base + UInt32($0), count: 1)![0] }
    }
    return .init(tls:memory.tlsSnapshot(),locks:locks.locksSnapshot(),sourceGlobalBytes:globals,interiorOwners:memory.applicationTLSOwnerSnapshot(),applicationBytes:memory.applicationBytes())
}
let (heap,host,locks,memory)=try fixture(profile)
var physicalAttempt=0,allocationAttempt=0
func beforePhysical(_ slot:UInt32) throws {
    physicalAttempt+=1
    if profile.physicalFailAt==physicalAttempt {throw ClawNativeMfcMemory.Failure.invalidOwnership}
    if slot==0x4a48e0,let replacement=profile.mallocRescan {
        let name=profile.steps[0].arguments[0],bytes=Array(unhex(replacement))
        heap.lookupBytes(name,count:UInt32(bytes.count))!.update(from:bytes,count:bytes.count)
    }
}
memory.beforeService={slot,_ in try beforePhysical(slot)}
locks.beforeService={_,slot,_ in try beforePhysical(slot)}
memory.failTLSSet=profile.tlsSetFalse
memory.failAllocation={slot in
    if slot==0x546a90 {return profile.tlsFailure}
    if [UInt32(0x4a48e0),0x546b1c,0x546aa8,0x546a88,0x546a80].contains(slot) {allocationAttempt+=1}
    return profile.allocationFailAt==allocationAttempt || (slot==0x4a48e0 && profile.mallocNull)
}
var roots=0,physical=0,entries=0,referenceOnly=0,nativeUnobserved=0
var unobserved:[[String:Any]]=[]
let executed=host.withApplicationSourceGraph(provider:memory) { graph in
    for (index,step) in profile.steps.enumerated() {
        let label="\(profile.name) root \(index)"
        for range in step.before.inputRanges {
            check(!heap.overlaps(range.address,count:range.size),label+" new caller storage disjoint")
            let bytes=Array(unhex(range.bytes)),base=range.address & ~3,offset=range.address & 3
            let p=heap.storeBytes(token:base,count:range.size+offset);p.update(repeating:0xcc,count:Int(range.size+offset));p.advanced(by:Int(offset)).update(from:bytes,count:bytes.count)
        }
        try! memory.registerApplicationReceiver(step.receiver,inputRanges:Dictionary(uniqueKeysWithValues:step.before.inputRanges.map {($0.address,$0.size)}),imageBase:profile.imageDataStart,imageCount:UInt32(profile.initialImageData.count/2))
        check(graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:unhex(step.stackBefore)),label+" caller stack")
        compare(snapshot(heap,memory,locks),step.before,label+" before",order:step.order)
        var c=context(step.inputContext)
        let result=graph.invokeSource(at:.applicationObject,context:&c)
        check(result.completed==step.completed,label+" completed actual \(result) expected \(step.completed)")
        if step.completed { check(fields(c)==step.outputContext,label+" full output header/CPU actual \(fields(c)) expected \(String(describing:step.outputContext))") }
        else {check(graph.tlsOutput.map(cpu)==(missingPrefix?.inputCPU ?? step.outputCPU),label+" stopped CPU actual \(String(describing:graph.tlsOutput.map(cpu))) expected \(missingPrefix?.inputCPU ?? step.outputCPU)")}
        if let prefix=missingPrefix {
            check(host.fault?.address==0x4f50fd && host.fault?.diagnostic == .missingDependency,label+" honest missing native throw boundary")
            check(graph.tlsStack==unhex(prefix.stackBefore),label+" full missing-prefix stack")
            compare(snapshot(heap,memory,locks),prefix.before,label+" missing prefix state",order:prefix.order)
        } else {
            check(graph.tlsStack==unhex(step.stackAfter),label+" full final stack")
            compare(snapshot(heap,memory,locks),step.after,label+" after",order:step.returnOrder ?? Int.max)
        }
        roots+=1
    }
    let actual=graph.moduleObservations.filter {$0.function != 0x50257f}
    let physicalActual=actual.filter(\.physical)
    check(physicalActual.count==comparedEvents.count,"physical boundary count actual \(physicalActual.count) expected \(comparedEvents.count)")
    for (i,pair) in zip(physicalActual,comparedEvents).enumerated() {compareObservation(pair.0,pair.1,"physical \(i) \(String(pair.1.function,radix:16))");physical+=1}
    let excluded:Set<UInt32>=[0x503167,0x502e47,0x50210b,0x4f5e89,0x4f5133,0x4f6a9a,0x50354d]
    let observed=comparedEntries.filter {!excluded.contains($0.function)}
    for e in comparedEntries where excluded.contains(e.function) {
        let originalOnly=profile.referenceOnlyEntries.contains(e.function)
        if originalOnly {referenceOnly+=1}else{nativeUnobserved+=1}
        unobserved.append(["profile":profile.name,"function":e.function,"return_pc":e.returnPC,"frame":e.frame,"root_step":e.rootStep,"original_defined":originalOnly,"reason":originalOnly ? "original-only internal owner body" : "constructor executes inside admitted factory; no dispatched boundary"])
    }
    let sourceActual=actual.filter {!$0.physical}
    check(sourceActual.count==observed.count,"source entry count actual \(sourceActual.count) expected \(observed.count)")
    for (i,pair) in zip(sourceActual,observed).enumerated() {compareObservation(pair.0,pair.1,"entry \(i) \(String(pair.1.function,radix:16))");entries+=1}
    func key(_ physical:Bool,_ e:UInt32,_ pc:UInt32,_ esp:UInt32,_ returned:Bool)->String {"\(physical):\(e):\(pc):\(esp):\(returned)"}
    var a:[(Int,String)]=[],b:[(Int,String)]=[]
    for e in actual {
        a.append((e.order,key(e.physical,e.function,e.returnPC,e.input.esp,false)))
        if e.completed,let order=e.returnOrder {a.append((order,key(e.physical,e.function,e.returnPC,e.input.esp,true)))}
    }
    for e in observed+comparedEvents {
        let isPhysical=e.importedTarget != nil
        b.append((e.order,key(isPhysical,e.function,e.returnPC,e.frame,false)))
        if e.completed,let order=e.returnOrder,order<(missingPrefix?.order ?? Int.max) {b.append((order,key(isPhysical,e.function,e.returnPC,e.frame,true)))}
    }
    check(a.sorted {$0.0<$1.0}.map(\.1)==b.sorted {$0.0<$1.0}.map(\.1),"joint source/physical ordering")
    return true
}
check(executed==true,"whole application graph executed")
let originalAssertions=checks
// Native controls run once, in the actual static profile's physical policy.
if shardIndex==0 {
    func prepared(_ maximumOperations:UInt32=0) throws -> (ClawTokenHeap,Host,ClawNativeMfcLocks,ClawNativeMfcMemory,ClawSourceContext) {
        let (heap,host,locks,memory)=try fixture(profile,maximumOperations:maximumOperations)
        let receiverBase:UInt32=0x62100000,nameBase:UInt32=0x62110000
        heap.storeBytes(token:receiverBase,count:0xc4).update(repeating:0x91,count:0xc4)
        let name:[UInt8]=[0xcc,67,108,97,119,0,0xcc,0xcc]
        heap.storeBytes(token:nameBase,count:8).update(from:name,count:8)
        try memory.registerApplicationReceiver(receiverBase+3,inputRanges:[receiverBase+3:0xc0,nameBase+1:5],imageBase:profile.imageDataStart,imageCount:UInt32(initialImageBytes.count))
        var c=context(profile.steps[0].inputContext);c.ecx=receiverBase+3
        return (heap,host,locks,memory,c)
    }
    func seed(_ graph:Host.SourceGraph,_ c:ClawSourceContext) {
        check(graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:unhex(profile.steps[0].stackBefore)),"control stack seeded")
        check(graph.writeStack(at:c.esp+4,data:word(0x62110001)),"control name caller argument")
    }
    func replace(_ heap:ClawTokenHeap,_ base:UInt32,_ count:UInt32) {
        let bytes=Array(UnsafeBufferPointer(start:heap.lookupBytes(base,count:count)!,count:Int(count)))
        heap.withStableFreedStorage {heap.free(base);heap.storeBytes(token:base,count:count).update(from:bytes,count:bytes.count)}
    }
    for variant in 0..<17 {
        let (_,host,locks,memory,initial)=try prepared()
        host.withApplicationSourceGraph(provider:memory) {graph in
            var c=initial;seed(graph,c)
            switch variant {
            case 0:c.size=0
            case 1:c.version=2
            case 2:c.inputMask=0
            case 3:c.outputMask=0
            case 4:c.preserveMask=0x400
            case 5:c.reserved0=1
            case 6:c.reserved1=1
            case 7:c.eip=0x503510
            case 8:c.ecx+=1
            case 9:c.esp+=1
            case 10:c.eflags=0
            case 11:c.fsHead=0
            case 12:c.esp=UInt32(CLAW_STACK_END)-4
            case 13:c.eflags|=0x400
            case 14:_=graph.writeStack(at:c.esp,data:word(0x5025cf))
            case 15:_=graph.writeStack(at:c.esp+4,data:word(0xfffffff0))
            default:c.esp=UInt32(CLAW_STACK_BASE)+64
            }
            check(!graph.invokeSource(at:.applicationObject,context:&c).completed,"malformed whole constructor rejected")
            check(memory.events.isEmpty && locks.events.isEmpty,"malformed root cannot reach physical service")
        }
    }
    // Invalidation of the first request hook must suppress the later effect hook.
    for variant in 0..<6 {
        let (heap,host,locks,memory,initial)=try prepared();var reached=false,secondHook=false
        memory.beforeSourceApplicationService={request in
            guard !reached else {return};reached=true
            switch variant {
            case 0:replace(heap,0x62100000,0xc4)
            case 1:replace(heap,0x62110000,8)
            case 2:replace(heap,0x546cd0,4)
            case 3:check(memory.serviceSourceApplication(request)==nil,"consumed physical lease replay rejected")
            case 4:check(host.withApplicationSourceGraph(provider:memory) {_ in true}==nil,"nested whole application graph rejected")
            default:var call=ClawCall();call.function=0x546abc;call.stackPointer=request.context.esp;_=locks.service(call)
            }
        }
        memory.beforeService={_,_ in secondHook=true}
        host.withApplicationSourceGraph(provider:memory) {graph in
            var c=initial;seed(graph,c)
            check(!graph.invokeSource(at:.applicationObject,context:&c).completed && reached,"invalidated whole owner aborts")
            check(!secondHook,"invalidated first hook suppresses later effect hook")
            check(memory.tlsSnapshot().allocations.isEmpty && locks.events.isEmpty,"invalidated cursor boundary cannot allocate or lock")
            check(Array(UnsafeBufferPointer(start:heap.lookupBytes(0x62100003+0x5c,count:8)!,count:8))==Array(repeating:UInt8(0x91),count:8),"invalidated cursor cannot write POINT")
        }
    }
    // Both effect-capable malloc hooks must retain input and receiver identity.
    for allocationHook in [false,true] {
        let (heap,host,_,memory,initial)=try prepared();var reached=false
        func attack(_ slot:UInt32) {if slot==0x4a48e0 && !reached {reached=true;replace(heap,0x62110000,8)}}
        if allocationHook {memory.failAllocation={slot in attack(slot);return false}}
        else {memory.beforeService={slot,_ in attack(slot)}}
        host.withApplicationSourceGraph(provider:memory) {graph in
            var c=initial;seed(graph,c)
            check(!graph.invokeSource(at:.applicationObject,context:&c).completed && reached,"malloc hook name ABA rejected")
            check(memory.tlsSnapshot().allocations.isEmpty,"malloc hook cannot allocate after input owner loss")
            check(memory.events.last?.function==0x4a48e0 && memory.events.last?.completed==false,"malloc hook stops at genuine physical boundary")
        }
    }
    for size in [UInt32(0x1074),0x84,5] {
        let (heap,host,_,memory,initial)=try prepared();var reached=false;var fieldsBefore:[UInt8]=[];var countBefore=0
        memory.beforeService={slot,_ in
            guard slot==0x5469bc && !reached else {return};reached=true
            fieldsBefore=Array(UnsafeBufferPointer(start:heap.lookupBytes(initial.ecx+0x28,count:8)!,count:8))
            countBefore=memory.tlsSnapshot().allocations.count
            let allocation=memory.tlsSnapshot().allocations.first {$0.live && $0.size==size}!
            replace(heap,allocation.address,allocation.size)
        }
        host.withApplicationSourceGraph(provider:memory) {graph in
            var c=initial;seed(graph,c)
            check(!graph.invokeSource(at:.applicationObject,context:&c).completed && reached,"retained module/application/duplicate ABA rejects thread service")
            check(memory.tlsSnapshot().allocations.count==countBefore,"thread service owner loss cannot allocate")
            check(Array(UnsafeBufferPointer(start:heap.lookupBytes(initial.ecx+0x28,count:8)!,count:8))==fieldsBefore,"thread service owner loss cannot publish handle/ID")
            check(memory.events.last?.function==0x5469bc && memory.events.last?.completed==false,"retained owner loss has no physical thread result")
        }
    }
    // Valid issuer authority survives foreign-thread and foreign-provider probes.
    do {
        let (_,host,_,memory,initial)=try prepared();let (_,otherHost,_,otherMemory,_)=try prepared()
        var saved:Host.SourceApplicationRequest?,reached=false
        memory.beforeSourceApplicationService={request in
            saved=request
            guard !reached else {return};reached=true
            check(!request.consume(for:host,provider:otherMemory) && !request.consume(for:otherHost,provider:memory),"foreign provider/host cannot consume application lease")
            let done=DispatchSemaphore(value:0)
            Thread.detachNewThread {
                check(!request.consume(for:host,provider:memory) && !request.validReturn(for:host),"foreign thread has no application lease")
                check(memory.serviceSourceApplication(request)==nil,"foreign thread cannot mutate application owner")
                done.signal()
            }
            done.wait();check(host.fault==nil,"foreign request cannot fault real issuer")
        }
        host.withApplicationSourceGraph(provider:memory) {graph in
            var c=initial;seed(graph,c)
            check(graph.invokeSource(at:.applicationObject,context:&c).completed && reached,"valid whole root survives foreign probes")
        }
        check(saved != nil && !saved!.consume(for:host,provider:memory),"expired application request cannot consume")
        check(memory.serviceSourceApplication(saved!)==nil,"expired request cannot drive physical owner")
    }
    do {
        let (_,host,locks,memory,initial)=try prepared();var expired:Host.SourceGraph?
        host.withApplicationSourceGraph(provider:memory) {graph in expired=graph}
        var c=initial
        check(!expired!.invokeSource(at:.applicationObject,context:&c).completed,"expired application root rejected")
        check(memory.events.isEmpty && locks.events.isEmpty,"expired root has no effects")
    }
    do {
        let (_,host,locks,memory,initial)=try prepared()
        host.withApplicationSourceGraph(provider:memory) {graph in
            var c=initial;seed(graph,c)
            check(!graph.invokeSource(at:.moduleGet,context:&c).completed,"whole graph cannot elect unit root")
            check(memory.events.isEmpty && locks.events.isEmpty,"wrong root election has no effects")
        }
    }
    for budget in [UInt32(1),100] {
        let (_,host,locks,memory,initial)=try prepared(budget)
        host.withApplicationSourceGraph(provider:memory) {graph in
            var c=initial;seed(graph,c)
            check(!graph.invokeSource(at:.applicationObject,context:&c).completed && host.fault?.code==UInt32(CLAW_FAULT_BUDGET),"whole application bounded source budget")
            let count=memory.events.count+locks.events.count
            check(!graph.invokeSource(at:.applicationObject,context:&c).completed && memory.events.count+locks.events.count==count,"second root cannot reset source budget")
        }
    }
    do {
        let (_,host,_,memory,initial)=try prepared()
        host.withApplicationSourceGraph(provider:memory) {graph in
            var c=initial;seed(graph,c)
            check(graph.invokeSource(at:.applicationObject,context:&c).completed,"receiver ownership setup executes real root")
            let module=memory.tlsSnapshot().allocations.first {$0.live && $0.size==0x1074}!.address
            for candidate in [module,UInt32(0x5408e0)] {
                var rejected=false
                do {try memory.registerApplicationReceiver(candidate,inputRanges:[:],imageBase:profile.imageDataStart,imageCount:UInt32(initialImageBytes.count))}catch{rejected=true}
                check(rejected,"physical module/lock owner cannot be relabeled caller receiver")
            }
            check(memory.ownsApplicationReceiver(initial.ecx),"rejected receiver setup preserves legitimate owner")
        }
    }
    // Configuration validates every import before allocating the first slot.
    do {
        let host=Host(heap:ClawTokenHeap())
        let memory=try ClawNativeMfcMemory(host:host,sha256:profile.sha256,importTargets:mapping(profile.imports).filter {ClawNativeMfcMemory.importArities[$0.key] != nil})
        let imports=mapping(profile.imports).filter {[UInt32(0x546cd0),0x5469bc,0x5469c0].contains($0.key)}
        var invalid=imports;invalid[0x5469c0]=0x50257f
        var rejected=false
        do {try memory.configureApplicationServices(importTargets:invalid,cursorSuccess:true,x:0,y:0,threadHandle:UInt32.max)}catch{rejected=true}
        check(rejected && imports.keys.allSatisfy {!host.heap.overlaps($0,count:4)},"invalid setup has no partial IAT allocations")
        try memory.configureApplicationServices(importTargets:imports,cursorSuccess:true,x:0,y:0,threadHandle:UInt32.max)
        check(imports.allSatisfy {host.heap.lookup($0.key,words:1)?[0]==$0.value},"corrected setup succeeds after rejected configuration")
    }
}
let report:[String:Any]=["status":"pass","profile_index":shardIndex,"original_variation_index":profile.profileIndex,"profile_name":profile.name,"profiles":1,"roots":roots,"physical_events":physical,"observed_entries":entries,"reference_only_entries":referenceOnly,"native_unobserved_entries":nativeUnobserved,"unobserved_sites":unobserved,"assertions":checks,"original_assertions":originalAssertions,"native_controls":checks-originalAssertions,"missing_native_sites":missingPrefix.map {[["profile":profile.name,"function":$0.function,"return_pc":$0.returnPC,"frame":$0.frame,"root_step":$0.rootStep] as [String:Any]]} ?? [],"missing_native_prefixes":missingPrefix == nil ? 0 : 1,"later_original_physical_events":profile.events.count-comparedEvents.count,"later_original_entries":profile.entries.count-comparedEntries.count,"reference_entries":profile.entries.count,"reference_physical_events":profile.events.count,"returned_roots":profile.steps.filter(\.completed).count,"stopped_roots":profile.steps.filter {!$0.completed}.count,"catch_executed":false,"whole_cwinapp_executed":profile.steps.contains {$0.completed}]
print(String(data:try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]),encoding:.utf8)!)
