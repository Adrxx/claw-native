import Foundation
import CryptoKit

// Read-only normalization of the two sealed original schemas. There are no
// synthesized source outputs: execution stays in the current SourceGraph.
typealias Host = ClawNativeCanonicalHost
var checks = 0
func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    checks += 1
    if !condition() { fatalError("FAIL: \(message)") }
}
func sha(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
func word(_ value: UInt32) -> Data { var v = value.littleEndian; return withUnsafeBytes(of: &v) { Data($0) } }
func physicalMemoryCall(_ slot: UInt32, _ arguments: [UInt32]) -> ClawCall {
    var call = ClawCall()
    call.function = slot; call.argumentCount = UInt32(arguments.count)
    call.stackPointer = UInt32(CLAW_STACK_TOP) - 0x100
    withUnsafeMutableBytes(of: &call.arguments) { out in arguments.withUnsafeBytes { out.copyMemory(from: $0) } }
    return call
}
func unhex(_ text: String) -> Data {
    let a = Array(text.utf8)
    precondition(a.count % 2 == 0)
    return Data(stride(from: 0, to: a.count, by: 2).map { UInt8(String(bytes: a[$0..<$0+2], encoding: .utf8)!, radix: 16)! })
}
struct Reference: Decodable {
    let schema: Int, program_sha256: String, count: Int
    let stack_base: UInt32, stack_size: Int, input_mask: UInt32, output_mask: UInt32, preserve_mask: UInt32
    let cpu_fields: [String], profiles: [Profile]
}
struct Profile: Decodable {
    let label: String, function: UInt32, return_pc: UInt32
    let allocation_address: UInt32, allocation_size: UInt32, stack_seed: UInt32
    let stack_words: [[UInt32]], input: [String: UInt32], expected: Expected
    let initial_allocation_hex: String?, record_address: UInt32?, record_size: UInt32?
    let cursor_success: Bool?, cursor_point: [Int32]?
}
struct Expected: Decodable {
    let cpu: [String: UInt32], stack_sha256: String, allocation_hex: String
    let allocation_sha256: String?, record_hex: String?, record_sha256: String?, record_with_canaries_hex: String?
    let local_alloc: [Event]?, get_cursor_pos: [Event]?
}
struct Event: Decodable {
    let function: UInt32, return_pc: UInt32, arguments: [UInt32], cpu: [String: UInt32]
    let frame_hex: String, stack_sha256: String
    let allocation_hex: String?, record_hex: String?, record_sha256: String?, record_with_canaries_hex: String?
    let after_cpu: [String: UInt32]?
}
struct Observation {
    let function: UInt32, returnPC: UInt32, arguments: [UInt32], context: ClawSourceContext
    let frame: Data, stack: Data, allocation: Data?, returnedContext: ClawSourceContext?
}
enum Kind: String { case factories, threadRecords, sharedFactories }
func values(_ c: ClawSourceContext) -> [String: UInt32] {
    ["eax":c.eax,"ebx":c.ebx,"ecx":c.ecx,"edx":c.edx,"esi":c.esi,"edi":c.edi,
     "ebp":c.ebp,"esp":c.esp,"eip":c.eip,"eflags":c.eflags,"fsHead":c.fsHead]
}
func context(_ p: Profile) -> ClawSourceContext {
    let c = p.input
    return .init(size:72,version:1,inputMask:0x7ff,outputMask:0x7ff,
      eax:c["eax"]!,ebx:c["ebx"]!,ecx:c["ecx"]!,edx:c["edx"]!,esi:c["esi"]!,edi:c["edi"]!,
      ebp:c["ebp"]!,esp:c["esp"]!,eip:c["eip"]!,eflags:c["eflags"]!,fsHead:c["fsHead"]!,preserveMask:0x472,reserved0:0,reserved1:0)
}
func compareCPU(_ actual: ClawSourceContext, _ expected: [String:UInt32], _ label: String) {
    check(expected.count == 11 && values(actual) == expected, "\(label) all 11 CPU fields")
    check(actual.size == 72 && actual.version == 1 && actual.inputMask == 0x7ff && actual.outputMask == 0x7ff && actual.preserveMask == 0x472 && actual.reserved0 == 0 && actual.reserved1 == 0, "\(label) immutable context header")
}
func compareBytes(_ actual: Data, hex: String? = nil, digest: String? = nil, label: String) {
    if let hex { check(actual == unhex(hex), "\(label) complete bytes") }
    if let digest { check(sha(actual) == digest, "\(label) complete SHA256") }
}
func slice(_ bytes: Data, base: UInt32, at address: UInt32, count: UInt32) -> Data {
    precondition(address >= base && UInt64(address) + UInt64(count) <= UInt64(base) + UInt64(bytes.count))
    return bytes.subdata(in: Int(address-base)..<Int(address-base+count))
}
func compareAllocation(_ bytes: Data, p: Profile, allocationHex: String, allocationHash: String? = nil,
                       recordHex: String? = nil, recordHash: String? = nil, canaryHex: String? = nil, label: String) {
    check(bytes.count == Int(p.allocation_size), "\(label) exact allocation extent")
    compareBytes(bytes, hex: allocationHex, digest: allocationHash, label: label)
    if let address = p.record_address, let size = p.record_size {
        compareBytes(slice(bytes, base:p.allocation_address, at:address, count:size), hex:recordHex, digest:recordHash, label:"\(label) record slice")
        if let canaryHex {
            compareBytes(slice(bytes, base:p.allocation_address, at:address-32, count:size+64), hex:canaryHex, label:"\(label) record and canary slice")
        }
    }
}
func compareEvent(_ a: Observation, _ b: Event, p: Profile) {
    check(a.function == b.function && a.returnPC == b.return_pc && a.arguments == b.arguments, "physical exact signature")
    compareCPU(a.context, b.cpu, "physical entry")
    compareBytes(a.frame, hex:b.frame_hex, label:"physical full frame")
    check(a.stack.count == Int(CLAW_STACK_END-CLAW_STACK_BASE), "physical 128 KiB stack extent")
    compareBytes(a.stack, digest:b.stack_sha256, label:"physical full stack")
    check((a.returnedContext != nil) == (b.after_cpu != nil), "physical return observation presence")
    if let c = a.returnedContext, let expected = b.after_cpu { compareCPU(c, expected, "physical return including EAX BOOL") }
    check((a.allocation != nil) == (b.allocation_hex != nil), "physical allocation observation presence")
    if let allocation = a.allocation, let expected = b.allocation_hex {
        compareAllocation(allocation, p:p, allocationHex:expected, recordHex:b.record_hex, recordHash:b.record_sha256, canaryHex:b.record_with_canaries_hex, label:"physical record and canaries")
    }
}

// Only this adapter knows the two concrete physical capability types.
// Adding a new OS edge still requires an admitted Host capability and adapter.
final class Services {
    var allocator: Host.SourceLocalAllocator?
    var cursor: Host.SourceCursorService?
    var memory: ClawNativeMfcMemory?
    let kind: Kind
    init(_ kind: Kind, host: Host, p: Profile) {
        self.kind = kind
        switch kind {
        case .factories:
            check(p.initial_allocation_hex == nil && p.expected.local_alloc != nil && p.expected.get_cursor_pos == nil, "factory schema")
            allocator = .init(host:host, importTarget:0x710028, allocationBase:p.allocation_address)
            check(allocator != nil, "physical allocator capability")
        case .sharedFactories:
            check(p.initial_allocation_hex == nil && p.expected.local_alloc != nil && p.expected.get_cursor_pos == nil, "shared factory schema")
            var imports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map { ($0.element, UInt32(0x710100 + $0.offset * 4)) })
            imports[0x546aa8] = 0x710028
            memory = try! .init(host:host,sha256:ClawNativeMfcMemory.imageHash,importTargets:imports,allocationBase:p.allocation_address,allocationAlignment:8)
            allocator = .init(host:host,provider:memory!)
            check(allocator != nil, "shared physical allocator capability")
        case .threadRecords:
            let data = unhex(p.initial_allocation_hex!)
            check(data.count == Int(p.allocation_size), "initial allocation extent")
            let pointer = host.heap.storeBytes(token:p.allocation_address,count:p.allocation_size)
            data.withUnsafeBytes { UnsafeMutableRawPointer(pointer).copyMemory(from:$0.baseAddress!,byteCount:$0.count) }
            cursor = .init(host:host,recordToken:p.record_address!,allocationBase:p.allocation_address,allocationCount:p.allocation_size,importTarget:0x71002c,success:p.cursor_success!,x:p.cursor_point![0],y:p.cursor_point![1])
            check(cursor != nil && p.expected.get_cursor_pos != nil && p.expected.local_alloc == nil, "physical cursor capability")
        }
    }
    func allocation(_ p: Profile) -> Data { allocator?.allocationSnapshot(p.allocation_address) ?? cursor!.allocationSnapshot()! }
    func observations() -> [Observation] {
        if let allocator {
            return allocator.events.map { .init(function:$0.function,returnPC:$0.returnPC,arguments:$0.arguments,context:$0.context,frame:$0.frame,stack:$0.stack,allocation:nil,returnedContext:nil) }
        }
        return cursor!.events.map { .init(function:$0.function,returnPC:$0.returnPC,arguments:$0.arguments,context:$0.context,frame:$0.frame,stack:$0.stack,allocation:$0.allocation,returnedContext:$0.returnedContext) }
    }
    func retire() { allocator = nil; cursor = nil }
    var iat: UInt32 { kind == .threadRecords ? 0x546cd0 : 0x546aa8 }
}
func replay(_ p: Profile, kind: Kind) {
    let host = Host(heap:ClawTokenHeap())
    let service = Services(kind, host:host, p:p)
    var c = context(p), copied: Data?
    var observations: [Observation] = []
    let expectedEvents = p.expected.local_alloc ?? p.expected.get_cursor_pos!
    guard let site = Host.SourceSite(rawValue:p.return_pc) else { fatalError("unadmitted callsite") }
    check(site.function == p.function, "exact explicit source capability")
    host.withSourceGraph(localAllocator:service.allocator,cursorService:service.cursor) { graph in
        let initial = Data((0..<Int(CLAW_STACK_END-CLAW_STACK_BASE)).map { UInt8(($0*37+Int(p.stack_seed))&255) })
        check(graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:initial), "prepare full stack")
        for item in p.stack_words { check(graph.writeStack(at:item[0],data:word(item[1])), "prepare source word") }
        let result = graph.invokeSource(at:site,context:&c)
        check(result.completed && result.eax == (p.record_address ?? p.allocation_address), "\(p.label) completed: \(String(describing:result.fault))")
        compareCPU(c, p.expected.cpu, p.label)
        copied = graph.stackSnapshot()
        check(copied?.count == Int(CLAW_STACK_END-CLAW_STACK_BASE), "final 128 KiB stack extent")
        compareBytes(copied!,digest:p.expected.stack_sha256,label:"final stack")
        compareAllocation(service.allocation(p),p:p,allocationHex:p.expected.allocation_hex,allocationHash:p.expected.allocation_sha256,recordHex:p.expected.record_hex,recordHash:p.expected.record_sha256,canaryHex:p.expected.record_with_canaries_hex,label:"final allocation")
        observations = service.observations()
        check(observations.count == 1 && expectedEvents.count == 1, "exact one physical call")
        for (actual,expected) in zip(observations,expectedEvents) { compareEvent(actual,expected,p:p) }
    }
    check(host.fault == nil, "clean graph teardown")
    let before = service.allocation(p)
    check(host.heap.lookupBytes(p.allocation_address,count:p.allocation_size) != nil, "record survives graph")
    check(host.heap.lookupBytes(p.allocation_address+p.allocation_size,count:1) == nil, "exact record bounds")
    host.withSourceGraph { graph in
        check(graph.stackSnapshot() == Data(repeating:0,count:Int(CLAW_STACK_END-CLAW_STACK_BASE)), "next graph private stack reset")
        compareBytes(copied!,digest:p.expected.stack_sha256,label:"copied stack survives graph")
    }
    service.retire()
    if kind == .sharedFactories {
        check(service.memory!.localPointers == [p.allocation_address], "one shared ownership ledger")
        check(service.memory!.localBytes[String(p.allocation_address)] == Array(before), "shared owner sees source-written record")
        check(service.memory!.events.count == 1 && service.memory!.events[0].result == p.allocation_address, "one physical allocation operation")
        check(host.heap.lookupBytes(p.allocation_address,count:1) != nil, "adapter retirement preserves provider allocation")
        check(host.heap.lookupBytes(service.iat,count:4) != nil, "adapter retirement preserves provider IAT")
        // The constructor bytes were compared to the sealed original above.
        // These subsequent calls exercise the physical owner's lifecycle, not
        // additional original factory instructions or source graph edges.
        let moved = service.memory!.service(physicalMemoryCall(0x546a80,[p.allocation_address,p.allocation_size+17,0x42]))!
        check(moved != 0 && moved != p.allocation_address, "same owner resizes source allocation")
        check(service.memory!.sourceLocalSnapshot(moved) == unhex(p.expected.allocation_hex) + Data(repeating:0,count:17), "resize preserves independently sealed constructor bytes and zeroes growth")
        check(service.memory!.service(physicalMemoryCall(0x5469d8,[moved])) == 0, "same owner frees resized source allocation")
        check(service.memory!.localPointers.isEmpty && service.memory!.events.count == 3, "exactly one operation for allocation resize and free")
        service.memory = nil
        check(host.heap.lookupBytes(p.allocation_address,count:1) == nil, "provider retirement releases owned record")
    } else if kind == .factories {
        check(host.heap.lookupBytes(p.allocation_address,count:1) == nil, "owned record retires")
    } else {
        let pointer = host.heap.lookupBytes(p.allocation_address,count:p.allocation_size)!
        check(Data(bytes:pointer,count:Int(p.allocation_size)) == before, "borrowed record survives retirement")
        compareEvent(observations[0],expectedEvents[0],p:p)
    }
    check(host.heap.lookupBytes(service.iat,count:4) == nil, "owned IAT retires")
}
let start = DispatchTime.now().uptimeNanoseconds
let sets: [(Kind,String,Int,Int)] = [
    (.factories,"d9b916231ae75c9d46a232f970684a03357c5ec909c5496f3919b327b913f41d",160,1),
    (.threadRecords,"40eb786142e740aab4b61a20372e597184a028c5ed2543a6a7c48b71fc8369a5",128,2),
    (.sharedFactories,"d9b916231ae75c9d46a232f970684a03357c5ec909c5496f3919b327b913f41d",160,1)]
check(CommandLine.arguments.count == 3, "two original reference paths required")
var counts: [String:Int] = [:], referenceHashes: [String:String] = [:]
for set in sets {
    let (kind,pin,count,pathIndex) = set
    let bytes = try Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[pathIndex]))
    check(sha(bytes) == pin, "sealed \(kind.rawValue) reference")
    let reference = try JSONDecoder().decode(Reference.self,from:bytes)
    check(reference.program_sha256 == "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263", "pinned original")
    check(reference.schema == 1 && reference.count == count && reference.profiles.count == count, "complete existing corpus")
    check(reference.stack_base == CLAW_STACK_BASE && reference.stack_size == 131072 && reference.input_mask == 0x7ff && reference.output_mask == 0x7ff && reference.preserve_mask == 0x472 && Set(reference.cpu_fields) == Set(values(context(reference.profiles[0])).keys), "sealed common observation contract")
    for p in reference.profiles { replay(p,kind:kind) }
    counts[kind.rawValue] = count; referenceHashes[kind.rawValue] = pin
}
let replayChecks = checks
checkSharedMemoryContracts()
let result: [String:Any] = ["status":"pass","profiles":448,"unique_reference_profiles":288,"profiles_by_kind":counts,"assertions":checks,"replay_assertions":replayChecks,"physical_contract_assertions":checks-replayChecks,"reference_sha256":referenceHashes,"replay_seconds":Double(DispatchTime.now().uptimeNanoseconds-start)/1e9,"adversarial_suites":"unchanged; run existing guards separately"]
print(String(data:try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]),encoding:.utf8)!)
