import Foundation

typealias Block = ClawNativeMfcMemory.Block
typealias SectionState = ClawNativeMfcLocks.State
struct Event: Decodable {
    let function: UInt32, target: UInt32, stackPointer: UInt32, arguments: [UInt32]
    let result: UInt32?, completed: Bool, blocks: [Block], sections: [SectionState]
    let managerBytes: [String: String], blockBytes: [String: String]
}
struct Step: Decodable {
    let function: UInt32, receiver: UInt32, frame: UInt32, writes: [String: UInt32]
    let completed: Bool, eax: UInt32?, halt: String?, blocks: [Block], sections: [SectionState]
    let managerBytes: [String: String], blockBytes: [String: String], tlsIndices: [UInt32]
    let eventCount: Int, entryCount: Int
}
struct Entry: Decodable { let function: UInt32, frame: UInt32, arguments: [UInt32] }
struct Reference: Decodable {
    let name: String, sha256: String, initialBytes: String, imports: [String: UInt32], lockImports: [String: UInt32]
    let managerCount: Int, managers: [UInt32], fail: String?, failAt: Int?
    let steps: [Step], events: [Event], entries: [Entry]
}
func check(_ value: @autoclosure () -> Bool, _ label: String) {
    if !value() { FileHandle.standardError.write(Data(("FAIL " + label + "\n").utf8)); exit(1) }
}
func bytes(_ value: String) -> [UInt8] {
    stride(from: 0,to: value.count,by: 2).map { offset in
        let start=value.index(value.startIndex,offsetBy:offset)
        return UInt8(value[start..<value.index(start,offsetBy:2)],radix:16)!
    }
}
func mapping(_ values: [String: UInt32]) -> [UInt32: UInt32] { Dictionary(uniqueKeysWithValues:values.map { (UInt32($0.key)!,$0.value) }) }
func byteMapping(_ values: [String: String]) -> [String: [UInt8]] { values.mapValues(bytes) }
func call(_ function: UInt32, _ arguments: [UInt32] = [], receiver: UInt32 = 0, frame: UInt32 = UInt32(CLAW_STACK_TOP)-0x100) -> ClawCall {
    var value=ClawCall();value.function=function;value.argumentCount=UInt32(arguments.count);value.receiver=receiver;value.stackPointer=frame
    withUnsafeMutableBytes(of:&value.arguments) { target in arguments.withUnsafeBytes { target.copyMemory(from:$0) } }
    return value
}
let references=try JSONDecoder().decode([Reference].self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
check(references.count==9,"nine original profiles")
check(claw_canonical_lookup(0x502fb6) != nil && claw_canonical_lookup(0x502ff8) != nil && claw_canonical_lookup(0x4a4a20) != nil,"actual admitted manager and byte fill registry")
check(claw_canonical_lookup(0x4f50fd) == nil,"exception remains genuine missing dependency")
var sourceCalls=0,physicalCalls=0,movingBlocks=0
for reference in references {
    let application=try ClawNativeApplication(clock:{100}),host:ClawNativeCanonicalHost
    host=application.canonicalHost
    check(application.constructed && application.operationCalls[0x4254a0]==1,"actual application constructor")
    let originalApplication=Array(UnsafeBufferPointer(start:application.heap.lookupBytes(application.applicationToken,count:0x134)!,count:0x134))
    let locks=try ClawNativeMfcLocks(host:host,sha256:reference.sha256,initialBytes:bytes(reference.initialBytes),importTargets:mapping(reference.lockImports))
    var owner:ClawNativeMfcMemory?=try ClawNativeMfcMemory(host:host,sha256:reference.sha256,importTargets:mapping(reference.imports),locks:locks)
    weak let weakOwner=owner
    owner!.incidentalResult=0xa1b2c3d4
    let managers=try (0..<reference.managerCount).map { _ in try owner!.createManager() }
    check(managers==reference.managers,"deterministic physical manager token allocation")
    owner!.failAllocation={ slot in
        (reference.fail=="tls" && slot==0x546a90) || (reference.fail=="allocate" && slot==0x546b1c) || (reference.fail=="reallocate" && slot==0x546a88)
    }
    owner!.beforeService={ [weak owner] _,_ in
        if reference.failAt == (owner?.events.count ?? 0)+1 { throw ClawNativeMfcMemory.Failure.exhausted }
    }
    var exceptionCalls:[ClawCall]=[]
    let previous=host.dependency
    host.dependency={ [weak owner] host,value in
        if value.function==0x4f50fd { exceptionCalls.append(value) }
        if let result=owner?.service(value) { return result }
        guard host.fault==nil else { return nil }
        return previous?(host,value)
    }
    for step in reference.steps {
        for (address,value) in step.writes { application.heap.lookup(UInt32(address)!,words:1)![0]=value }
        let result=application.invoke(call(step.function,receiver:step.receiver,frame:step.frame))
        check(result.completed==step.completed,reference.name+" completion")
        check(result.eax==step.eax,reference.name+" exact source EAX")
        if step.completed { check(result.canonicalFault==nil,"successful source graph") }
        else {
            let expected=step.halt=="missing-exception" ? 0x4f50fd : UInt32(step.halt!.dropFirst(2),radix:16)!
            check(result.canonicalFault?.address==expected && result.canonicalFault?.code==UInt32(CLAW_FAULT_HALT),"genuine missing/physical stop")
            if expected==0x4f50fd {
                let entry=reference.entries.last!
                check(exceptionCalls.count==1 && exceptionCalls[0].function==entry.function && exceptionCalls[0].stackPointer==entry.frame,"actual throw entry frame")
                check(exceptionCalls[0].receiver==0 && exceptionCalls[0].argumentCount==0,"actual throw entry ABI")
                check(result.canonicalFault?.diagnostic == .missingDependency,"no fabricated exception owner")
            }
            let count=owner!.events.count
            check(!application.invoke(call(0x502ff8,receiver:managers[0])).completed && owner!.events.count==count,"sticky stop")
        }
        check(owner!.blocks==step.blocks && owner!.sectionStates==step.sections,reference.name+" source ownership")
        check(owner!.managerBytes==byteMapping(step.managerBytes),reference.name+" exact manager bytes and canaries")
        check(owner!.blockBytes==byteMapping(step.blockBytes),reference.name+" exact table flags payload and cleared tail")
        check(owner!.tlsIndices==step.tlsIndices && owner!.events.count==step.eventCount,"TLS index and callback count")
        sourceCalls+=1
    }
    check(owner!.events.count==reference.events.count,"exact event count")
    for (actual,expected) in zip(owner!.events,reference.events) {
        check(actual.function==expected.function && actual.target==expected.target,reference.name+" explicit physical loader target")
        check(actual.stackPointer==expected.stackPointer && actual.arguments==expected.arguments,reference.name+" exact physical frame and args")
        check(actual.result==expected.result && actual.completed==expected.completed,"physical return and failure")
        check(actual.blocks==expected.blocks && actual.sections==expected.sections,"physical state snapshot")
        check(actual.managerBytes==byteMapping(expected.managerBytes) && actual.blockBytes==byteMapping(expected.blockBytes),"call-time source bytes")
        physicalCalls+=1
    }
    let retired=Set(owner!.events.flatMap { $0.blocks.map(\.data) }).subtracting(Set(owner!.blocks.map(\.data)))
    for token in retired { check(application.heap.lookupBytes(token,count:1)==nil,"moved old span retired");movingBlocks+=1 }
    let released=owner!.blocks.map(\.data)+managers
    owner=nil
    check(weakOwner==nil,"no dependency retention cycle")
    for token in released { check(application.heap.lookupBytes(token,count:1)==nil,"owned dynamic storage released") }
    for slot in ClawNativeMfcMemory.importArities.keys {
        if ClawNativeMfcLocks.importSlots.contains(slot) { check(application.heap.lookup(slot,words:1)![0]==mapping(reference.imports)[slot],"borrowed IAT survives") }
        else { check(application.heap.lookupBytes(slot,count:4)==nil,"owned IAT retired") }
    }
    check(Array(UnsafeBufferPointer(start:application.heap.lookupBytes(application.applicationToken,count:0x134)!,count:0x134))==originalApplication,"same application ownership intact")
}

// Direct physical contracts supplement, but do not inflate, original source
// comparisons. These services are provision for the forthcoming TLS-value body.
let image=references[0]
func makeOwner(_ host:ClawNativeCanonicalHost) throws -> ClawNativeMfcMemory {
    try ClawNativeMfcMemory(host:host,sha256:image.sha256,importTargets:mapping(image.imports))
}
do {
    let app=try ClawNativeApplication(clock:{100}),host:ClawNativeCanonicalHost;host=app.canonicalHost
    var owner:ClawNativeMfcMemory?=try makeOwner(host)
    func service(_ f:UInt32,_ args:[UInt32]=[]) -> UInt32 { owner!.service(call(f,args))! }
    let i=service(0x546a90),j=service(0x546a90)
    check(i != j && service(0x546a7c,[i])==0,"owned distinct zero-initialized native TLS keys")
    check(service(0x546a84,[i,0xcafebabe])==1 && service(0x546a7c,[i])==0xcafebabe && service(0x546a7c,[j])==0,"native TLS binding isolation")
    let local=service(0x546aa8,[0x40,13]);check(owner!.localPointers==[local],"local owned identity")
    check(Array(UnsafeBufferPointer(start:app.heap.lookupBytes(local,count:13)!,count:13))==[UInt8](repeating:0,count:13),"LocalAlloc zero flag")
    app.heap.lookupBytes(local,count:13)![12]=0xab
    owner!.failAllocation={ $0==0x546a80 }
    check(service(0x546a80,[local,29,0x42])==0 && app.heap.lookupBytes(local,count:13)![12]==0xab,"failed local resize preserves live prefix")
    owner!.failAllocation=nil
    let grown=service(0x546a80,[local,29,0x42]);check(grown != local && app.heap.lookupBytes(local,count:1)==nil,"local resize moves lifetime")
    check(app.heap.lookupBytes(grown,count:29)![12]==0xab && app.heap.lookupBytes(grown,count:29)![28]==0,"local resize prefix and zero tail")
    check(service(0x5469d8,[grown])==0 && app.heap.lookupBytes(grown,count:1)==nil,"local explicit free")
    let global=service(0x546b1c,[0x2042,17]),data=service(0x5469c4,[global])
    check(global != data && app.heap.lookupBytes(global,count:1)==nil && service(0x546a8c,[data])==global,"opaque global handle distinct from actual span")
    check(service(mapping(image.imports)[0x5469c4]!,[global])==data && owner!.blocks[0].locks==2,"cached physical target and recursive global lock count")
    check(service(0x5469c8,[global])==1 && service(0x5469c8,[global])==0,"final successful unlock returns zero")
    app.heap.lookupBytes(data,count:17)![16]=0xde
    owner!.failAllocation={ $0==0x546a88 }
    check(service(0x546a88,[global,33,0x2042])==0 && owner!.blocks[0].data==data && app.heap.lookupBytes(data,count:17)![16]==0xde,"failed global growth retains unlocked handle and bytes")
    owner!.failAllocation=nil
    check(service(0x546a88,[global,33,0x2042])==global,"moving realloc retains opaque handle")
    let moved=owner!.blocks[0].data
    check(moved != data && app.heap.lookupBytes(data,count:1)==nil && app.heap.lookupBytes(moved,count:33)![16]==0xde && app.heap.lookupBytes(moved,count:33)![32]==0,"global prefix and zero tail after move")
    check(service(0x546ac0,[global])==0 && app.heap.lookupBytes(moved,count:1)==nil,"global free ownership")
    let borrowed:UInt32=0x63000000;app.heap.storeBytes(token:borrowed,count:0x34).update(repeating:0x5a,count:0x34)
    try owner!.registerManager(borrowed)
    _=service(0x546aa4,[borrowed+28]);_=service(0x546aac,[borrowed+28]);_=service(0x546aac,[borrowed+28])
    check(owner!.sectionStates[0].depth==2,"dynamic recursive critical section")
    _=service(0x546a9c,[borrowed+28]);_=service(0x546a9c,[borrowed+28]);_=service(0x546aa0,[borrowed+28])
    check(owner!.sectionStates.isEmpty,"source section deletion")
    owner=nil;check(app.heap.lookupBytes(borrowed,count:0x34)![0]==0x5a,"borrowed manager survives teardown")
}
// Explicitly owned versus borrowed/replaced IAT spans and atomic loader checks.
for variant in 0..<4 {
    let heap=ClawTokenHeap(),host:ClawNativeCanonicalHost;host=ClawNativeCanonicalHost(heap:heap)
    var targets=mapping(image.imports),hash=image.sha256
    if variant==0 { hash="invalid" }
    if variant==1 { targets[0x5469c4]=0x502ff8 }
    if variant==2 { targets[0x5469c4]=targets[0x546a90] }
    if variant==3 { heap.store(token:0x5469c4,words:1)[0]=0xdeadbeef }
    var rejected=false
    do { _=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:targets) } catch { rejected=true }
    check(rejected && heap.lookupBytes(0x546b1c,count:1)==nil,"atomic invalid physical loader")
}
do {
    let heap=ClawTokenHeap(),host:ClawNativeCanonicalHost;host=ClawNativeCanonicalHost(heap:heap)
    var owner:ClawNativeMfcMemory?=try makeOwner(host)
    heap.withStableFreedStorage {
        heap.free(0x5469c4);heap.store(token:0x5469c4,words:1)[0]=0xbadcafe
        owner=nil
        check(heap.lookup(0x5469c4,words:1)![0]==0xbadcafe,"replacement IAT lifetime preserved")
    }
    check(owner==nil,"owner released")
}
for variant in 0..<5 {
    let heap=ClawTokenHeap(),host:ClawNativeCanonicalHost;host=ClawNativeCanonicalHost(heap:heap)
    let owner=try makeOwner(host)
    let manager=try owner.createManager()
    var value=call(0x546aa4,[manager+28])
    if variant==0 { value.receiver=1 }
    if variant==1 { value.stackPointer+=1 }
    if variant==2 { value=call(0x546aa4,[manager+32]) }
    if variant==3 { value=call(0x546a9c,[manager+28]) }
    if variant==4 {
        heap.withStableFreedStorage { heap.free(manager);heap.storeBytes(token:manager,count:0x34)[0]=0 }
    }
    check(owner.service(value)==nil && host.fault != nil,"invalid ABI or source owner rejected")
}
// Shared lock namespace composes through the original static-lock body.
do {
    let app=try ClawNativeApplication(clock:{100}),host:ClawNativeCanonicalHost;host=app.canonicalHost
    let locks=try ClawNativeMfcLocks(host:host,sha256:image.sha256,initialBytes:bytes(image.initialBytes),importTargets:mapping(image.lockImports))
    let memory=try ClawNativeMfcMemory(host:host,sha256:image.sha256,importTargets:mapping(image.imports),locks:locks)
    let previous=host.dependency
    host.dependency={ [weak memory,weak locks] host,value in
        if let result=memory?.service(value) { return result }
        guard host.fault==nil else { return nil }
        if let result=locks?.service(value) { return result }
        guard host.fault==nil else { return nil }
        return previous?(host,value)
    }
    check(app.invoke(call(0x502e95,[16])).completed && app.invoke(call(0x502f05,[16])).completed,"actual static-lock namespace composition")
    let manager=try memory.createManager()
    check(app.invoke(call(0x502fb6,receiver:manager)).completed && app.invoke(call(0x502ff8,receiver:manager)).eax==1,"actual dynamic manager composition")
    check(locks.states.allSatisfy { $0.depth==0 } && memory.sectionStates.allSatisfy { $0.depth==0 },"separate owned sections balanced")
}
print("PASS \(references.count) same-application native MFC TLS manager profiles; \(sourceCalls) original calls; \(physicalCalls) exact physical callbacks; \(movingBlocks) retired moving spans; true canonical memset, missing exception frames, TLS/global/local ownership and shared locks")
