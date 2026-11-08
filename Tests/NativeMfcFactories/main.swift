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
struct Reference: Decodable {
    let program_sha256: String
    let count: Int
    let profiles: [Profile]
}
struct Profile: Decodable {
    let label: String, function: UInt32, return_pc: UInt32
    let allocation_address: UInt32, allocation_size: UInt32, stack_seed: UInt32
    let stack_words: [[UInt32]], input: [String: UInt32], expected: Expected
}
struct Expected: Decodable {
    let cpu: [String: UInt32], stack_sha256: String, allocation_hex: String, allocation_sha256: String
    let local_alloc: [Event]
}
struct Event: Decodable {
    let function: UInt32, return_pc: UInt32, arguments: [UInt32], cpu: [String: UInt32]
    let frame_hex: String, stack_sha256: String
}
func context(_ p: Profile) -> ClawSourceContext {
    let c = p.input
    return .init(size: 72, version: 1, inputMask: 0x7ff, outputMask: 0x7ff,
                 eax:c["eax"]!, ebx:c["ebx"]!, ecx:c["ecx"]!, edx:c["edx"]!, esi:c["esi"]!, edi:c["edi"]!,
                 ebp:c["ebp"]!, esp:c["esp"]!, eip:c["eip"]!, eflags:c["eflags"]!, fsHead:c["fsHead"]!,
                 preserveMask:0x472, reserved0:0, reserved1:0)
}
func values(_ c: ClawSourceContext) -> [String: UInt32] {
    ["eax":c.eax,"ebx":c.ebx,"ecx":c.ecx,"edx":c.edx,"esi":c.esi,"edi":c.edi,
     "ebp":c.ebp,"esp":c.esp,"eip":c.eip,"eflags":c.eflags,"fsHead":c.fsHead]
}
func prepare(_ graph: ClawNativeCanonicalHost.SourceGraph, _ p: Profile) {
    let data = Data((0..<Int(CLAW_STACK_END-CLAW_STACK_BASE)).map { UInt8(($0 * 37 + Int(p.stack_seed)) & 255) })
    check(graph.writeStack(at: UInt32(CLAW_STACK_BASE), data: data), "prepare full stack")
    for item in p.stack_words { check(graph.writeStack(at: item[0], data: word(item[1])), "prepare source words") }
}
let bytes = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
check(sha(bytes) == "d9b916231ae75c9d46a232f970684a03357c5ec909c5496f3919b327b913f41d", "sealed independent reference")
let reference = try JSONDecoder().decode(Reference.self, from: bytes)
check(reference.program_sha256 == "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263", "pinned original")
check(reference.count == 160 && reference.profiles.count == 160, "all independent profiles")
for p in reference.profiles {
    let heap = ClawTokenHeap(), target: UInt32 = 0x710028
    let host = ClawNativeCanonicalHost(heap: heap)
    var allocator: ClawNativeCanonicalHost.SourceLocalAllocator? = .init(host: host, importTarget: target, allocationBase: p.allocation_address)
    check(allocator != nil, "create physical service")
    var c = context(p)
    var copied: Data?
    host.withSourceGraph(localAllocator: allocator) { graph in
        prepare(graph, p)
        let result = graph.invokeSource(at: .init(rawValue: p.return_pc)!, context: &c)
        check(result.completed && result.eax == p.allocation_address, "\(p.label) completed: \(String(describing: result.fault))")
        check(values(c) == p.expected.cpu, "\(p.label) all CPU")
        check(c.size == 72 && c.version == 1 && c.inputMask == 0x7ff && c.outputMask == 0x7ff && c.preserveMask == 0x472 && c.reserved0 == 0 && c.reserved1 == 0, "immutable envelope")
        copied = graph.stackSnapshot()
        check(sha(copied!) == p.expected.stack_sha256, "\(p.label) full stack")
        let allocation = allocator!.allocationSnapshot(p.allocation_address)!
        check(hex(allocation) == p.expected.allocation_hex && sha(allocation) == p.expected.allocation_sha256, "\(p.label) whole record")
        check(allocator!.events.count == 1 && p.expected.local_alloc.count == 1, "exact one physical call")
        let event = allocator!.events[0], expected = p.expected.local_alloc[0]
        check(event.function == expected.function && event.returnPC == expected.return_pc && event.arguments == expected.arguments, "exact physical signature")
        check(values(event.context) == expected.cpu, "physical all CPU")
        check(hex(event.frame) == expected.frame_hex, "physical complete frame")
        check(sha(event.stack) == expected.stack_sha256, "physical full stack")
    }
    check(host.fault == nil, "clean graph teardown")
    check(heap.lookupBytes(p.allocation_address, count:p.allocation_size) != nil, "record survives graph")
    check(heap.lookupBytes(p.allocation_address + p.allocation_size, count:1) == nil, "actual size bounds")
    host.withSourceGraph { graph in
        check(graph.stackSnapshot() == Data(repeating:0,count:Int(CLAW_STACK_END-CLAW_STACK_BASE)), "next graph private storage cleared")
        check(sha(copied!) == p.expected.stack_sha256, "copied stack stable")
    }
    allocator = nil
    check(heap.lookupBytes(p.allocation_address, count:1) == nil, "service retirement ends ownership")
    check(heap.lookupBytes(0x546aa8, count:4) == nil, "owned IAT retirement")
}
// Guard checks are native safety contracts, separate from original parity.
let sample = reference.profiles[2]
let target: UInt32 = 0x710028
let mutations: [(String,(inout ClawSourceContext)->Void)] = [
    ("size",{$0.size=0}), ("version",{$0.version=2}), ("input mask",{$0.inputMask=0x7fe}),
    ("output mask",{$0.outputMask=0x5f3}), ("unknown mask",{$0.inputMask=0xfff}),
    ("preserve mask",{$0.preserveMask=0}), ("reserved0",{$0.reserved0=1}), ("reserved1",{$0.reserved1=1}),
    ("entry",{$0.eip=0x501f01}), ("flags",{$0.eflags=0x202}), ("fixed flag",{$0.eflags=0}),
    ("unaligned FS",{$0.fsHead=UInt32(CLAW_STACK_BASE)+1}), ("outside FS",{$0.fsHead=0}),
    ("FS end",{$0.fsHead=UInt32(CLAW_STACK_END)-8}), ("ESP alignment",{$0.esp+=1}),
    ("ESP below",{$0.esp=UInt32(CLAW_STACK_BASE)-4}), ("ESP end",{$0.esp=UInt32(CLAW_STACK_END)}),
    ("headroom",{$0.esp=UInt32(CLAW_STACK_BASE)+40})
]
for (name, mutate) in mutations {
    let host = ClawNativeCanonicalHost(heap:ClawTokenHeap())
    let allocator = ClawNativeCanonicalHost.SourceLocalAllocator(host:host,importTarget:target)!
    var c = context(sample); mutate(&c)
    let before = values(c)
    host.withSourceGraph(localAllocator:allocator) { graph in
        let result = graph.invokeSource(at:.threadFactory,context:&c)
        check(!result.completed && result.fault?.code == UInt32(CLAW_FAULT_ABI), "reject \(name)")
        check(values(c) == before && allocator.events.isEmpty, "reject before mutation \(name)")
        check(graph.stackSnapshot() == nil, "sticky \(name)")
    }
}
for p in [reference.profiles[2],reference.profiles[82]] {
    let host = ClawNativeCanonicalHost(heap:ClawTokenHeap())
    let allocator = ClawNativeCanonicalHost.SourceLocalAllocator(host:host,importTarget:target)!
    allocator.failAllocation = true
    var c = context(p)
    var hooked = false
    host.dependency = { _,_ in hooked=true; return 0xdeadbeef }
    host.withSourceGraph(localAllocator:allocator) { graph in
        prepare(graph,p)
        let result = graph.invokeSource(at:.init(rawValue:p.return_pc)!,context:&c)
        check(!result.completed && result.eax == nil && result.fault?.address == 0x4f50fd && result.fault?.diagnostic == .missingDependency,"real allocation failure stops at missing original throw")
        check(allocator.events.count == 1 && !hooked,"no fake source exception or physical fallback")
        let first=host.fault
        check(!graph.invokeSource(at:.init(rawValue:p.return_pc)!,context:&c).completed && host.fault==first,"failure remains sticky")
    }
}
do {
    let heap=ClawTokenHeap(),host=ClawNativeCanonicalHost(heap:ClawTokenHeap())
    let allocator=ClawNativeCanonicalHost.SourceLocalAllocator(host:host,importTarget:target)!
    let other=ClawNativeCanonicalHost(heap:heap)
    check(other.withSourceGraph(localAllocator:allocator,body:{_ in true}) == nil && other.fault?.code == UInt32(CLAW_FAULT_ABI),"foreign host service rejected")
}
for overlap in [UInt32(0x62000000),0x62000010] {
    let heap=ClawTokenHeap(),base:UInt32=0x62000000
    heap.storeBytes(token:overlap,count:3).update(repeating:0x55,count:3)
    let host=ClawNativeCanonicalHost(heap:heap)
    let allocator=ClawNativeCanonicalHost.SourceLocalAllocator(host:host,importTarget:target,allocationBase:base)!
    var c=context(sample)
    host.withSourceGraph(localAllocator:allocator) { graph in
        let result=graph.invokeSource(at:.threadFactory,context:&c)
        check(!result.completed && result.fault?.diagnostic == .invalidMemorySpan,"existing heap allocation collision rejected")
    }
    check(heap.lookupBytes(overlap,count:3)?.pointee == 0x55,"collision preserves unrelated heap")
}
do {
    let heap=ClawTokenHeap()
    heap.store(token:0x61ffffff-3,words:1)[0]=0x11223344
    let host=ClawNativeCanonicalHost(heap:heap)
    let allocator=ClawNativeCanonicalHost.SourceLocalAllocator(host:host,importTarget:target,allocationBase:0x62000000)!
    var c=context(sample)
    host.withSourceGraph(localAllocator:allocator) { graph in
        check(graph.invokeSource(at:.threadFactory,context:&c).completed,"adjacent allocation allowed")
    }
    check(heap.lookup(0x61fffffc,words:1)![0] == 0x11223344,"adjacent allocation preserved")
}
do {
    let heap=ClawTokenHeap()
    heap.store(token:0x546aa8,words:1)[0]=target
    let host=ClawNativeCanonicalHost(heap:heap)
    var allocator:ClawNativeCanonicalHost.SourceLocalAllocator? = .init(host:host,importTarget:target)
    check(allocator != nil,"borrow matching IAT")
    allocator=nil
    check(heap.lookup(0x546aa8,words:1)![0] == target,"borrowed IAT survives service release")
    check(ClawNativeCanonicalHost.SourceLocalAllocator(host:host,importTarget:target+4)==nil,"IAT identity mismatch rejected")
}
for mutateDuringGraph in [false,true] {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap())
    let allocator=ClawNativeCanonicalHost.SourceLocalAllocator(host:host,importTarget:target)!
    var c=context(sample)
    if !mutateDuringGraph { host.heap.lookup(0x546aa8,words:1)![0]=target+4 }
    let ran=host.withSourceGraph(localAllocator:allocator) { graph in
        host.heap.lookup(0x546aa8,words:1)![0]=target+4
        check(!graph.invokeSource(at:.threadFactory,context:&c).completed,"changed live IAT target rejected")
        return true
    }
    check(mutateDuringGraph ? ran == true : ran == nil,"IAT guard before and during graph")
    check(allocator.events.isEmpty,"no service for forged cached target")
}
for limit in [UInt32(1),10,20] {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap(),maximumOperations:limit)
    let allocator=ClawNativeCanonicalHost.SourceLocalAllocator(host:host,importTarget:target)!
    var c=context(sample)
    host.withSourceGraph(localAllocator:allocator) { graph in
        check(!graph.invokeSource(at:.threadFactory,context:&c).completed && host.fault?.code == UInt32(CLAW_FAULT_BUDGET),"shared nested budget \(limit)")
    }
}
do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap(),maximumOperations:45)
    let allocator=ClawNativeCanonicalHost.SourceLocalAllocator(host:host,importTarget:target)!
    host.withSourceGraph(localAllocator:allocator) { graph in
        var a=context(sample)
        check(graph.invokeSource(at:.threadFactory,context:&a).completed,"first sibling budget")
        var b=context(sample)
        check(!graph.invokeSource(at:.threadFactory,context:&b).completed && host.fault?.code == UInt32(CLAW_FAULT_BUDGET),"siblings share operation budget")
    }
}
do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap())
    let allocator=ClawNativeCanonicalHost.SourceLocalAllocator(host:host,importTarget:target)!
    let done=DispatchSemaphore(value:0)
    Thread.detachNewThread {
        if host.withSourceGraph(localAllocator:allocator,body:{_ in true}) != nil { fatalError("foreign service thread accepted") }
        done.signal()
    }
    done.wait()
    check(host.fault?.code == UInt32(CLAW_FAULT_ABI),"service thread pinned")
}
do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap())
    var allocator:ClawNativeCanonicalHost.SourceLocalAllocator? = .init(host:host,importTarget:target)
    var retained:ClawNativeCanonicalHost.SourceGraph?
    var c=context(sample)
    host.withSourceGraph(localAllocator:allocator) { graph in
        retained=graph
        check(graph.invokeSource(at:.threadFactory,context:&c).completed,"retained graph first call")
    }
    allocator=nil
    check(host.heap.lookupBytes(0x62000000,count:1)==nil,"retired graph does not retain allocator ownership")
    check(!retained!.invokeSource(at:.threadFactory,context:&c).completed,"retired graph rejected")
}
do {
    let heap=ClawTokenHeap()
    heap.storeBytes(token:UInt32(CLAW_STACK_BASE),count:4)
    let host=ClawNativeCanonicalHost(heap:heap)
    let allocator=ClawNativeCanonicalHost.SourceLocalAllocator(host:host,importTarget:target)!
    check(host.withSourceGraph(localAllocator:allocator,body:{_ in true}) == nil,"heap source-stack overlap rejected")
}
for address in [UInt32(0x502335),0x502369] {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap())
    var call=ClawCall();call.function=address
    check(!host.invoke(call).completed && host.fault?.code == UInt32(CLAW_FAULT_ABI),"required factory closed to ordinary dispatch")
}
do {
    let heap=ClawTokenHeap(),base:UInt32=0x62000000
    let host=ClawNativeCanonicalHost(heap:heap)
    var allocator:ClawNativeCanonicalHost.SourceLocalAllocator? = .init(host:host,importTarget:target)
    var first:Data?
    host.withSourceGraph(localAllocator:allocator) { graph in
        var a=context(sample),b=context(reference.profiles[82])
        check(graph.invokeSource(at:.threadFactory,context:&a).eax == base,"first successful sibling owns block")
        first=allocator!.allocationSnapshot(base)
        check(graph.invokeSource(at:.moduleFactory,context:&b).eax == base+0x118,"second successful sibling distinct block")
        check(allocator!.allocationSnapshot(base)==first,"second sibling preserves first full record")
    }
    host.withSourceGraph(localAllocator:allocator) { graph in
        var c=context(sample)
        check(graph.invokeSource(at:.threadFactory,context:&c).eax == base+0x1190,"later graph retains service allocation sequence")
        check(allocator!.allocationSnapshot(base)==first,"earlier record survives later graph")
    }
    let identity=heap.allocationIdentity(at:base,count:0x118)!
    let oldAddress=UInt(bitPattern:heap.lookupBytes(base,count:0x118)!)
    heap.free(base)
    let replacement=heap.storeBytes(token:base,count:0x118)
    replacement.update(repeating:0x7d,count:0x118)
    if oldAddress == UInt(bitPattern:replacement) { recycledPointers += 1 }
    check(heap.allocationIdentity(at:base,count:0x118) !== identity,"new allocation identity survives address reuse")
    check(heap.allocationIdentity(at:base+4,count:0x114)==nil && heap.allocationIdentity(at:base,count:0x114)==nil,"identity requires exact base and extent")
    check(allocator!.allocationSnapshot(base)==nil,"replaced allocation cannot pass ownership")
    allocator=nil
    check(heap.lookupBytes(base,count:0x118)?.pointee==0x7d,"owner retirement preserves replacement storage")
    check(heap.lookupBytes(base+0x118,count:1)==nil && heap.lookupBytes(base+0x1190,count:1)==nil,"retirement frees remaining owned records")
}
for borrowed in [false,true] {
    let heap=ClawTokenHeap()
    if borrowed { heap.store(token:0x546aa8,words:1)[0]=target }
    let host=ClawNativeCanonicalHost(heap:heap)
    var allocator:ClawNativeCanonicalHost.SourceLocalAllocator? = .init(host:host,importTarget:target)
    let identity=heap.allocationIdentity(at:0x546aa8,count:4)!
    let oldAddress=UInt(bitPattern:heap.lookupBytes(0x546aa8,count:4)!)
    heap.free(0x546aa8)
    let replacement=heap.store(token:0x546aa8,words:1)
    replacement[0]=target
    if oldAddress == UInt(bitPattern:replacement) { recycledPointers += 1 }
    check(heap.allocationIdentity(at:0x546aa8,count:4) !== identity,"IAT replacement unique identity")
    check(host.withSourceGraph(localAllocator:allocator,body:{_ in true})==nil,"matching-value IAT replacement rejected")
    allocator=nil
    check(heap.lookup(0x546aa8,words:1)![0]==target,"owned or borrowed replacement IAT survives obsolete owner release")
}
do {
    let heap=ClawTokenHeap()
    heap.store(token:0x546aa4,words:3)[1]=target
    let host=ClawNativeCanonicalHost(heap:heap)
    check(ClawNativeCanonicalHost.SourceLocalAllocator(host:host,importTarget:target)==nil,"interior IAT of larger image allocation rejected")
    check(heap.lookup(0x546aa8,words:1)![0]==target,"larger borrowed image unchanged")
}
print("PASS \(checks) native MFC factory checks; 160 independent original full CPU/stack/record/physical-frame profiles and native ownership guards; actual recycled pointers \(recycledPointers)")
