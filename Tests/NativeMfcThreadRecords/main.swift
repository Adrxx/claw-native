import Foundation
import CryptoKit

var checks = 0
var recycledPointers = 0
func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    checks += 1
    if !condition() { fatalError("FAIL: \(message)") }
}
func sha(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
func word(_ value: UInt32) -> Data { var v = value.littleEndian; return withUnsafeBytes(of: &v) { Data($0) } }
func hex(_ data: Data) -> String { data.map { String(format: "%02x", $0) }.joined() }
func unhex(_ text: String) -> Data {
    let a = Array(text.utf8)
    return Data(stride(from:0,to:a.count,by:2).map { UInt8(String(bytes:a[$0..<$0+2],encoding:.utf8)!,radix:16)! })
}
struct Reference: Decodable {
    let program_sha256: String
    let count: Int
    let profiles: [Profile]
}
struct Profile: Decodable {
    let label: String, function: UInt32, return_pc: UInt32
    let record_address: UInt32, record_size: UInt32
    let allocation_address: UInt32, allocation_size: UInt32, initial_allocation_hex: String
    let stack_seed: UInt32, stack_words: [[UInt32]], input: [String:UInt32]
    let cursor_success: Bool, cursor_point: [Int32], expected: Expected
}
struct Expected: Decodable {
    let cpu: [String:UInt32], stack_sha256: String, allocation_hex: String
    let get_cursor_pos: [Event]
}
struct Event: Decodable {
    let function: UInt32, return_pc: UInt32, arguments: [UInt32], cpu: [String:UInt32]
    let frame_hex: String, stack_sha256: String, allocation_hex: String
    let after_cpu: [String:UInt32]
}
func context(_ p: Profile) -> ClawSourceContext {
    let c = p.input
    return .init(size:72,version:1,inputMask:0x7ff,outputMask:0x7ff,
      eax:c["eax"]!,ebx:c["ebx"]!,ecx:c["ecx"]!,edx:c["edx"]!,esi:c["esi"]!,edi:c["edi"]!,
      ebp:c["ebp"]!,esp:c["esp"]!,eip:c["eip"]!,eflags:c["eflags"]!,fsHead:c["fsHead"]!,preserveMask:0x472,reserved0:0,reserved1:0)
}
func values(_ c: ClawSourceContext) -> [String:UInt32] {
    ["eax":c.eax,"ebx":c.ebx,"ecx":c.ecx,"edx":c.edx,"esi":c.esi,"edi":c.edi,
     "ebp":c.ebp,"esp":c.esp,"eip":c.eip,"eflags":c.eflags,"fsHead":c.fsHead]
}
func prepare(_ graph: ClawNativeCanonicalHost.SourceGraph, _ p: Profile) {
    check(graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:Data((0..<Int(CLAW_STACK_END-CLAW_STACK_BASE)).map { UInt8(($0*37+Int(p.stack_seed))&255) })),"prepare full stack")
    for item in p.stack_words { check(graph.writeStack(at:item[0],data:word(item[1])),"prepare source words") }
}
let target: UInt32 = 0x71002c
func allocation(_ heap:ClawTokenHeap,_ p:Profile) {
    let pointer=heap.storeBytes(token:p.allocation_address,count:p.allocation_size)
    unhex(p.initial_allocation_hex).withUnsafeBytes { UnsafeMutableRawPointer(pointer).copyMemory(from:$0.baseAddress!,byteCount:$0.count) }
}
func service(_ host:ClawNativeCanonicalHost,_ p:Profile) -> ClawNativeCanonicalHost.SourceCursorService? {
    .init(host:host,recordToken:p.record_address,allocationBase:p.allocation_address,allocationCount:p.allocation_size,importTarget:target,success:p.cursor_success,x:p.cursor_point[0],y:p.cursor_point[1])
}
func fixture(_ p:Profile, budget:UInt32=0) -> (ClawTokenHeap,ClawNativeCanonicalHost,ClawNativeCanonicalHost.SourceCursorService) {
    let heap=ClawTokenHeap(); allocation(heap,p)
    let host=ClawNativeCanonicalHost(heap:heap,maximumOperations:budget)
    return (heap,host,service(host,p)!)
}
let data=try Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1]))
check(sha(data)=="40eb786142e740aab4b61a20372e597184a028c5ed2543a6a7c48b71fc8369a5","sealed independent reference")
let reference=try JSONDecoder().decode(Reference.self,from:data)
check(reference.program_sha256=="350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263","pinned original")
check(reference.count==128 && reference.profiles.count==128,"all independent profiles")
for p in reference.profiles {
    let heap=ClawTokenHeap(); allocation(heap,p)
    let host=ClawNativeCanonicalHost(heap:heap)
    var cursor:ClawNativeCanonicalHost.SourceCursorService?=service(host,p)
    check(cursor != nil,"borrow original record")
    var c=context(p), copied:Data?
    host.withSourceGraph(cursorService:cursor) { graph in
        prepare(graph,p)
        let result=graph.invokeSource(at:.threadObject,context:&c)
        check(result.completed && result.eax==p.record_address,"\(p.label) complete \(String(describing:result.fault))")
        check(values(c)==p.expected.cpu,"\(p.label) all CPU")
        check(c.size==72 && c.version==1 && c.inputMask==0x7ff && c.outputMask==0x7ff && c.preserveMask==0x472 && c.reserved0==0 && c.reserved1==0,"immutable envelope")
        copied=graph.stackSnapshot()
        check(sha(copied!)==p.expected.stack_sha256,"\(p.label) full stack")
        check(hex(cursor!.allocationSnapshot()!)==p.expected.allocation_hex,"\(p.label) whole allocation and canaries")
        check(cursor!.events.count==1 && p.expected.get_cursor_pos.count==1,"exact one physical callback")
        let a=cursor!.events[0], b=p.expected.get_cursor_pos[0]
        check(a.function==b.function && a.returnPC==b.return_pc && a.arguments==b.arguments,"physical exact signature")
        check(values(a.context)==b.cpu,"physical all CPU")
        check(values(a.returnedContext)==b.after_cpu,"physical return EAX and all preserved CPU")
        let returned=a.returnedContext
        check(returned.size==72 && returned.version==1 && returned.inputMask==0x7ff && returned.outputMask==0x7ff && returned.preserveMask==0x472 && returned.reserved0==0 && returned.reserved1==0,"physical immutable return header")
        check(hex(a.frame)==b.frame_hex,"physical entire frame")
        check(sha(a.stack)==b.stack_sha256,"physical full stack")
        check(hex(a.allocation)==b.allocation_hex,"physical call-time record and canaries")
    }
    check(host.fault==nil,"clean graph exit")
    let before=cursor!.allocationSnapshot()!
    let event=cursor!.events[0]
    host.withSourceGraph { graph in
        check(graph.stackSnapshot()==Data(repeating:0,count:Int(CLAW_STACK_END-CLAW_STACK_BASE)),"private next graph stack reset")
        check(sha(copied!)==p.expected.stack_sha256,"copied stack stable")
    }
    cursor=nil
    check(Data(bytes:heap.lookupBytes(p.allocation_address,count:p.allocation_size)!,count:Int(p.allocation_size))==before,"borrowed record survives service retirement")
    check(hex(event.allocation)==p.expected.get_cursor_pos[0].allocation_hex,"copied event survives retirement")
    check(heap.lookupBytes(0x546cd0,count:4)==nil,"owned IAT retired")
}
let sample=reference.profiles[2]
let mutations:[(String,(inout ClawSourceContext)->Void)]=[
 ("size",{$0.size=0}),("version",{$0.version=2}),("input",{$0.inputMask=0x7fe}),
 ("output",{$0.outputMask=0x5f3}),("unknown",{$0.inputMask=0xfff}),("preserve",{$0.preserveMask=0}),
 ("reserved0",{$0.reserved0=1}),("reserved1",{$0.reserved1=1}),("entry",{$0.eip=0x50354d}),
 ("flags",{$0.eflags=0x202}),("fixedflag",{$0.eflags=0}),("unalignedFS",{$0.fsHead=UInt32(CLAW_STACK_BASE)+1}),
 ("outsideFS",{$0.fsHead=0}),("FSextent",{$0.fsHead=UInt32(CLAW_STACK_END)-8}),
 ("ESPalign",{$0.esp+=1}),("ESPbelow",{$0.esp=UInt32(CLAW_STACK_BASE)-4}),
 ("ESPend",{$0.esp=UInt32(CLAW_STACK_END)}),("headroom",{$0.esp=UInt32(CLAW_STACK_BASE)+40}),
 ("receiver",{$0.ecx+=1})]
for (name,mutate) in mutations {
    let (_,host,cursor)=fixture(sample)
    var c=context(sample);mutate(&c)
    let before=values(c), record=cursor.allocationSnapshot()
    host.withSourceGraph(cursorService:cursor) { graph in
        let r=graph.invokeSource(at:.threadObject,context:&c)
        check(!r.completed && r.fault?.code==UInt32(CLAW_FAULT_ABI),"reject \(name)")
        check(values(c)==before && cursor.events.isEmpty && cursor.allocationSnapshot()==record,"early reject \(name)")
        check(graph.stackSnapshot()==nil,"sticky \(name)")
    }
}
for which in 0..<6 {
    let heap=ClawTokenHeap();allocation(heap,sample)
    let host=ClawNativeCanonicalHost(heap:heap)
    let base=sample.allocation_address, count=sample.allocation_size
    let cursor=ClawNativeCanonicalHost.SourceCursorService(host:host,
       recordToken:which==0 ? base+count-100 : sample.record_address,
       allocationBase:which==1 ? base+4 : base,
       allocationCount:which==2 ? count-1 : count,
       importTarget:which==3 ? 0x503510 : which==4 ? 0x710fff+1 : which==5 ? 0x70ffff : target,
       success:true,x:0,y:0)
    check(cursor==nil,"reject invalid borrow/domain \(which)")
    check(heap.lookupBytes(0x546cd0,count:4)==nil,"invalid owner creates no IAT")
}
do {
    let (_,host,cursor)=fixture(sample)
    let foreign=ClawNativeCanonicalHost(heap:host.heap)
    check(foreign.withSourceGraph(cursorService:cursor,body:{_ in true})==nil,"foreign host rejected")
}
for live in [false,true] {
    for changeRecord in [false,true] {
        let (heap,host,cursor)=fixture(sample)
        var c=context(sample)
        func replace() {
            let token=changeRecord ? sample.allocation_address : 0x546cd0
            let count:UInt32=changeRecord ? sample.allocation_size : 4
            let old=heap.lookupBytes(token,count:count)!
            heap.free(token)
            let p=heap.storeBytes(token:token,count:count)
            if p==old { recycledPointers+=1 }
            if changeRecord { p.update(repeating:0xa5,count:Int(count)) }
            else { word(target).withUnsafeBytes { UnsafeMutableRawPointer(p).copyMemory(from:$0.baseAddress!,byteCount:4) } }
        }
        if !live { replace() }
        let ran=host.withSourceGraph(cursorService:cursor) { graph in
            replace()
            check(!graph.invokeSource(at:.threadObject,context:&c).completed,"live replacement refused")
            return true
        }
        check(live ? ran==true : ran==nil,"identity rejects replaced record/IAT")
        check(cursor.events.isEmpty && cursor.allocationSnapshot()==nil,"replaced owner has no authority")
    }
}
for owned in [false,true] {
    let heap=ClawTokenHeap();allocation(heap,sample)
    if !owned { heap.store(token:0x546cd0,words:1)[0]=target }
    let host=ClawNativeCanonicalHost(heap:heap)
    var cursor=service(host,sample)
    check(cursor != nil,"owned/borrowed IAT")
    let original=heap.lookupBytes(0x546cd0,count:4)!
    heap.free(0x546cd0)
    let replacement=heap.store(token:0x546cd0,words:1);replacement[0]=target
    if UInt(bitPattern:original) == UInt(bitPattern:replacement) { recycledPointers+=1 }
    check(cursor!.allocationSnapshot()==nil,"IAT replacement revokes snapshot")
    cursor=nil
    check(heap.lookup(0x546cd0,words:1)![0]==target,"retirement preserves replacement IAT")
}
do {
    let heap=ClawTokenHeap();allocation(heap,sample)
    heap.store(token:0x546cd0,words:1)[0]=target
    let host=ClawNativeCanonicalHost(heap:heap)
    var cursor=service(host,sample)
    check(cursor != nil,"borrow IAT exact block")
    cursor=nil
    check(heap.lookup(0x546cd0,words:1)![0]==target,"borrowed IAT preserved on retirement")
}
for kind in 0..<3 {
    let heap=ClawTokenHeap();allocation(heap,sample)
    if kind==0 { heap.store(token:0x546cd0-4,words:3)[1]=target }
    else if kind==1 { heap.storeBytes(token:0x546cd0,count:3) }
    else { heap.store(token:0x546cd0,words:1)[0]=target+4 }
    let host=ClawNativeCanonicalHost(heap:heap)
    check(service(host,sample)==nil,"IAT exact extent and target \(kind)")
}
for live in [false,true] {
    let (heap,host,cursor)=fixture(sample)
    if !live { heap.lookup(0x546cd0,words:1)![0]=target+4 }
    var c=context(sample)
    let ran=host.withSourceGraph(cursorService:cursor) { graph in
        heap.lookup(0x546cd0,words:1)![0]=target+4
        check(!graph.invokeSource(at:.threadObject,context:&c).completed,"changed IAT during graph rejected")
        return true
    }
    check(live ? ran==true : ran==nil,"IAT checked before/during graph")
    check(cursor.events.isEmpty,"forged target never dispatched")
}
// A missing service cannot fall through to ordinary dependency hooks.
do {
    let (_,host,cursor)=fixture(sample)
    var hooked=false,c=context(sample)
    host.dependency={_,_ in hooked=true;return 1}
    host.withSourceGraph { graph in
        check(!graph.invokeSource(at:.threadObject,context:&c).completed,"explicit physical service required")
    }
    check(!hooked && cursor.events.isEmpty,"no ordinary callback fallback")
}
for budget in [UInt32(1),8,20] {
    let (_,host,cursor)=fixture(sample,budget:budget)
    var c=context(sample)
    host.withSourceGraph(cursorService:cursor) { graph in
        check(!graph.invokeSource(at:.threadObject,context:&c).completed && host.fault?.code==UInt32(CLAW_FAULT_BUDGET),"shared nested budget \(budget)")
    }
}
do {
    let (_,host,cursor)=fixture(sample)
    var c=context(sample)
    var retired:ClawNativeCanonicalHost.SourceGraph?
    host.withSourceGraph(cursorService:cursor) { graph in
        retired=graph
        check(graph.invokeSource(at:.threadObject,context:&c).completed,"live graph success")
    }
    check(!retired!.invokeSource(at:.threadObject,context:&c).completed,"expired graph rejected")
}
do {
    let (_,host,cursor)=fixture(sample)
    let done=DispatchSemaphore(value:0)
    Thread.detachNewThread {
        if host.withSourceGraph(cursorService:cursor,body:{_ in true}) != nil { fatalError("foreign thread accepted") }
        if cursor.allocationSnapshot() != nil { fatalError("foreign thread snapshot") }
        done.signal()
    }
    done.wait()
    check(host.fault?.code==UInt32(CLAW_FAULT_ABI),"service pinned to creating thread")
}
do {
    let (heap,host,cursor)=fixture(sample)
    heap.storeBytes(token:UInt32(CLAW_STACK_BASE),count:4)
    check(host.withSourceGraph(cursorService:cursor,body:{_ in true})==nil,"source stack cannot overlap heap")
}
do {
    let (_,host,cursor)=fixture(sample)
    host.withSourceGraph(cursorService:cursor) { _ in
        check(host.withSourceGraph(cursorService:cursor,body:{_ in true})==nil,"reentrant graph rejected")
    }
}
do {
    let (_,host,_)=fixture(sample)
    var call=ClawCall();call.function=0x503510;call.receiver=sample.record_address
    check(!host.invoke(call).completed && host.fault?.code==UInt32(CLAW_FAULT_ABI),"ordinary required context remains closed")
}
// Siblings consume the same counter; later graphs receive a fresh counter.
do {
    let (_,host,cursor)=fixture(sample,budget:65)
    host.withSourceGraph(cursorService:cursor) { graph in
        var first=context(sample),second=context(sample)
        check(graph.invokeSource(at:.threadObject,context:&first).completed,"first sibling budget")
        check(!graph.invokeSource(at:.threadObject,context:&second).completed && host.fault?.code==UInt32(CLAW_FAULT_BUDGET),"siblings share budget")
    }
}
do {
    let (_,host,cursor)=fixture(sample)
    for _ in 0..<2 {
        host.withSourceGraph(cursorService:cursor) { graph in
            var a=context(sample),b=context(sample)
            check(graph.invokeSource(at:.threadObject,context:&a).completed,"first sibling same borrowed record")
            check(graph.invokeSource(at:.threadObject,context:&b).completed,"second sibling same borrowed record")
        }
    }
    check(cursor.events.count==4,"borrowed record works across siblings and later graphs")
}
do {
    let heap=ClawTokenHeap();allocation(heap,sample)
    let host=ClawNativeCanonicalHost(heap:heap)
    var cursor=service(host,sample)
    weak var weakCursor=cursor
    var retained:ClawNativeCanonicalHost.SourceGraph?
    host.withSourceGraph(cursorService:cursor) { graph in retained=graph }
    cursor=nil
    check(weakCursor==nil && retained != nil,"retired graph releases cursor capability")
    weakCursor=nil
    check(heap.lookupBytes(0x546cd0,count:4)==nil,"retired graph does not retain owned IAT")
    check(heap.lookupBytes(sample.record_address,count:104) != nil,"borrowed record remains after graph and owner retirement")
}
do {
    let heap=ClawTokenHeap();allocation(heap,sample)
    var host:ClawNativeCanonicalHost?=ClawNativeCanonicalHost(heap:heap)
    var cursor=service(host!,sample)
    host=nil
    check(cursor!.allocationSnapshot()==nil,"service outliving host loses memory authority")
    cursor=nil
    check(heap.lookupBytes(sample.record_address,count:104) != nil,"host retirement preserves caller record")
}
for mode in 0..<3 {
    let (_,host,cursor)=fixture(sample)
    var call=ClawCall();call.function=0x546cd0;call.argumentCount=1
    if mode==0 { call.sourceContext=UnsafeMutablePointer<ClawSourceContext>(bitPattern:1) }
    if mode==1 { call.compilerContext=UnsafeMutablePointer<ClawCompilerContext>(bitPattern:1) }
    if mode==2 { call.sourceReturnPC=0x50356f }
    var hooked=false
    host.dependency={_,_ in hooked=true;return 1}
    check(host.callNativeDependency(call)==nil && host.fault?.code==UInt32(CLAW_FAULT_ABI),"forged public contextual callback \(mode) rejected without pointer access")
    check(!hooked && cursor.events.isEmpty,"forged callback has no physical/ordinary authority")
}
do {
    let (_,host,cursor)=fixture(sample)
    host.withSourceGraph(cursorService:cursor) { _ in
        var call=ClawCall();call.function=0x546cd0
        check(host.callNativeDependency(call)==nil,"public call cannot masquerade as synchronous source callback")
    }
    check(cursor.events.isEmpty,"public callback did not execute cursor")
}
print("native MFC thread records: \(checks) checks PASS; \(reference.count) original profiles; \(recycledPointers) observed pointer reuses")
