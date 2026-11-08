import Foundation

func check(_ value: @autoclosure () -> Bool, _ message: String) { precondition(value(), message) }
func bytes(_ hex: String) -> [UInt8] { stride(from:0,to:hex.count,by:2).map { i in
    let start=hex.index(hex.startIndex,offsetBy:i);return UInt8(hex[start..<hex.index(start,offsetBy:2)],radix:16)!
} }
func mapping(_ value:[String:UInt32]) -> [UInt32:UInt32] { Dictionary(uniqueKeysWithValues:value.map { (UInt32($0.key)!,$0.value) }) }
func call(_ f:UInt32,_ receiver:UInt32,_ args:[UInt32],_ frame:UInt32) -> ClawCall {
    var c=ClawCall();c.function=f;c.receiver=receiver;c.argumentCount=UInt32(args.count);c.stackPointer=frame
    withUnsafeMutableBytes(of:&c.arguments) { target in args.withUnsafeBytes { source in
        if !source.isEmpty { target.baseAddress!.copyMemory(from:source.baseAddress!,byteCount:source.count) }
    } };return c
}
struct Snapshot:Decodable {
    let managerBytes:String,ownerValue:UInt32,locals:[String:String],blocks:[ClawNativeMfcMemory.Block],blockBytes:[String:String],sections:[ClawNativeMfcLocks.State]
}
struct Step:Decodable {
    let function:UInt32,receiver:UInt32,arguments:[UInt32],frame:UInt32,writes:[String:UInt32],completed:Bool,eax:UInt32?,halt:UInt32?,eventCount:Int
    let managerBytes:String,ownerValue:UInt32,locals:[String:String],blocks:[ClawNativeMfcMemory.Block],blockBytes:[String:String],sections:[ClawNativeMfcLocks.State]
}
struct Event:Decodable {
    let function:UInt32,target:UInt32,frame:UInt32,arguments:[UInt32],result:UInt32
    let managerBytes:String,ownerValue:UInt32,locals:[String:String],blocks:[ClawNativeMfcMemory.Block],blockBytes:[String:String],sections:[ClawNativeMfcLocks.State]
}
struct Profile:Decodable {
    let name:String,sha256:String,initialBytes:String,imports:[String:UInt32],lockImports:[String:UInt32],manager:UInt32,owner:UInt32,failure:String?,events:[Event],steps:[Step]
}
let profiles=try JSONDecoder().decode([Profile].self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
var sourceCalls=0,physicalCalls=0
for p in profiles {
    let app=try ClawNativeApplication(clock:{100}),host=app.canonicalHost
    let locks=try ClawNativeMfcLocks(host:host,sha256:p.sha256,initialBytes:bytes(p.initialBytes),importTargets:mapping(p.lockImports))
    let memory=try ClawNativeMfcMemory(host:host,sha256:p.sha256,importTargets:mapping(p.imports),locks:locks)
    memory.incidentalResult=0xa1b2c3d4
    let manager=try memory.createManager();check(manager==p.manager,"physical manager identity")
    app.heap.store(token:p.owner,words:1)[0]=0
    app.heap.store(token:0x540af0,words:1)[0]=0
    memory.failAllocation={ slot in (p.failure=="container" && slot==0x546aa8) || (p.failure=="reallocate" && slot==0x546a80) }
    let previous=host.dependency
    host.dependency={ [weak memory] host,c in
        if let r=memory?.service(c) { return r }
        guard host.fault==nil else { return nil };return previous?(host,c)
    }
    func compare(_ managerHex:String,_ owner:UInt32,_ locals:[String:String],_ blocks:[ClawNativeMfcMemory.Block],_ blockBytes:[String:String],_ sections:[ClawNativeMfcLocks.State]) {
        check(memory.managerBytes[String(manager)]==bytes(managerHex),p.name+" manager bytes")
        check(app.heap.lookup(p.owner,words:1)![0]==owner,p.name+" getter slot")
        check(memory.blocks==blocks && memory.sectionStates==sections,p.name+" ownership")
        check(memory.localPointers==locals.keys.map { UInt32($0)! }.sorted(),p.name+" local lifetimes")
        for (t,h) in locals { let b=bytes(h);check(Array(UnsafeBufferPointer(start:app.heap.lookupBytes(UInt32(t)!,count:UInt32(b.count))!,count:b.count))==b,p.name+" container/value bytes") }
        check(memory.blockBytes==Dictionary(uniqueKeysWithValues:blockBytes.map { ($0.key,bytes($0.value)) }),p.name+" slot table bytes")
    }
    for step in p.steps {
        for (t,v) in step.writes { app.heap.lookup(UInt32(t)!,words:1)![0]=v }
        let result=app.invoke(call(step.function,step.receiver,step.arguments,step.frame))
        check(result.completed==step.completed && result.eax==step.eax,p.name+" source result")
        if !step.completed {
            if let halt = step.halt, halt == 0x502335 {
                // The factory is now admitted with required source state.
                // This older getter has no ambient context capability yet.
                check(claw_canonical_lookup(halt)?.pointee.sourceCapability == 1,
                      p.name+" admitted factory requires source capability")
                check(result.canonicalFault?.address == step.halt &&
                      result.canonicalFault?.code == UInt32(CLAW_FAULT_ABI) &&
                      result.canonicalFault?.diagnostic == .unsupportedABI,
                      p.name+" missing factory source capability refuses before execution")
            } else {
                check(result.canonicalFault?.address==step.halt && result.canonicalFault?.diagnostic == .missingDependency,
                      p.name+" genuine unresolved source entry")
            }
        }
        compare(step.managerBytes,step.ownerValue,step.locals,step.blocks,step.blockBytes,step.sections)
        check(memory.events.count==step.eventCount,p.name+" exact physical event count")
        sourceCalls+=1
    }
    check(memory.events.count==p.events.count,"event lengths")
    for (actual,expected) in zip(memory.events,p.events) {
        check(actual.function==expected.function && actual.target==expected.target && actual.stackPointer==expected.frame && actual.arguments==expected.arguments && actual.result==expected.result && actual.completed,"exact physical call frames and returns")
        check(actual.managerBytes[String(manager)]==bytes(expected.managerBytes) && actual.blocks==expected.blocks && actual.sections==expected.sections,"exact call-time source manager and physical state")
        check(actual.localBytes==Dictionary(uniqueKeysWithValues:expected.locals.map { ($0.key,bytes($0.value)) }),"exact call-time source container and value bytes")
        check(actual.blockBytes==Dictionary(uniqueKeysWithValues:expected.blockBytes.map { ($0.key,bytes($0.value)) }),"exact call-time original slot-table bytes")
        physicalCalls+=1
    }
}
// A physical API cannot silently reinterpret a compiler-context envelope.
for lockAPI in [false,true] {
    let p=profiles[0],app=try ClawNativeApplication(clock:{100}),host=app.canonicalHost
    let locks=try ClawNativeMfcLocks(host:host,sha256:p.sha256,initialBytes:bytes(p.initialBytes),importTargets:mapping(p.lockImports))
    let memory=try ClawNativeMfcMemory(host:host,sha256:p.sha256,importTargets:mapping(p.imports),locks:locks)
    var context=ClawCompilerContext()
    withUnsafeMutablePointer(to:&context) { pointer in
        var request=call(lockAPI ? 0x546abc : 0x546a90,0,[],UInt32(CLAW_STACK_TOP));request.compilerContext=pointer
        let result=lockAPI ? locks.service(request) : memory.service(request)
        check(result==nil && host.fault?.diagnostic == .unsupportedABI,"physical service rejects compiler-context envelope")
        check(memory.tlsIndices.isEmpty && memory.events.isEmpty && locks.events.isEmpty,"rejection precedes physical side effects")
    }
}
print("{\"status\":\"pass\",\"profiles\":\(profiles.count),\"original_source_calls\":\(sourceCalls),\"exact_physical_callbacks\":\(physicalCalls),\"scope\":\"TLS unit composition; actual factory and exception dependencies remain unresolved\"}")
