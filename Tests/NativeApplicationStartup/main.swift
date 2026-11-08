import Foundation

struct ReferenceEvent: Decodable {
    let function: UInt32, receiver: UInt32
    let arguments: [UInt32]
    let result: UInt32?
    let applicationWords: [UInt32], clockWords: [UInt32]
}
struct Reference: Decodable {
    let name: String, sha256: String
    let clocks: [UInt32], tick: UInt32, cursor: Int32, cursorFinal: Int32
    let refused: Bool
    let app: UInt32, outer: UInt32, window: UInt32, config: UInt32
    let constructorWords: [UInt32], constructorClock: [UInt32]
    let applicationWords: [UInt32], clockWords: [UInt32], threadWords: [UInt32], tlsIndex: UInt32
    let configBytes: String?
    let events: [ReferenceEvent]
}
func fullCall(_ function: UInt32, receiver: UInt32 = 0, arguments: [UInt32] = []) -> ClawCall {
    precondition(arguments.count <= 16)
    var call = ClawCall();call.function = function;call.receiver = receiver;call.argumentCount = UInt32(arguments.count)
    withUnsafeMutableBytes(of:&call.arguments) {target in
        arguments.withUnsafeBytes {source in target.copyMemory(from:source)}
    }
    return call
}
func words(_ heap: ClawTokenHeap, _ token: UInt32, _ count: Int) -> [UInt32] {
    Array(UnsafeBufferPointer(start:heap.lookup(token,words:UInt32(count))!,count:count))
}
func check(_ condition: @autoclosure () -> Bool, _ label: String) {
    precondition(condition(),label)
}

let references = try JSONDecoder().decode([Reference].self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
check(references.count == 4,"four fresh original profiles")
var comparedEvents = 0
for reference in references {
    check(reference.sha256 == "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263","pinned reference")
    var clockIndex = 0, ticks = 0
    var application: ClawNativeApplication? = try ClawNativeApplication(clock:{
        check(clockIndex < reference.clocks.count,"clock sequence exhausted")
        defer {clockIndex += 1};return reference.clocks[clockIndex]
    },sourceAllocationByteLimit:reference.refused ? 0 : nil,tickClock:{ticks += 1;return reference.tick},initialCursorCount:reference.cursor)
    let heap = application!.heap, app = application!.applicationToken
    check(words(heap,app,77) == reference.constructorWords,"real constructor bytes: \(reference.name)")
    check(words(heap,0x541328,5) == reference.constructorClock,"real constructor clock")
    check(clockIndex == 2 && application!.startup == nil,"constructor does not initialize startup")
    // Synthetic platform owner/window records are boundary inputs only.
    // These are never advertised as completed original window initialization.
    let outer = heap.allocate(bytes:0x254), window = heap.allocate(bytes:12)
    heap.lookup(outer,words:4)!.update(from:[0x50bbdc,window,app,0x77000001],count:4)
    heap.lookup(window,words:3)!.update(from:[0x50c37c,0x77000002,outer],count:3)
    let outerBefore = words(heap,outer,149), windowBefore = words(heap,window,3)
    let command = try application!.makeCString("")
    let completion = application!.invoke(fullCall(0x425730,receiver:app,arguments:[window,command]))
    check(!completion.completed && completion.eax == nil,"missing dependency is not EAX0")
    check(completion.canonicalFault?.address == 0x4b5c50 && completion.canonicalFault?.code == UInt32(CLAW_FAULT_HALT)
          && completion.canonicalFault?.diagnostic == .missingDependency,"exact configuration halt")
    check(completion.fault == .canonical(completion.canonicalFault!),"canonical diagnostic retained")
    check(application!.startup!.fault == 1 && !application!.startup!.active,"startup context failure retained")
    let config = heap.lookup(app+0x38,words:1)!.pointee
    check((config == 0) == reference.refused,"source new refusal remains zero")
    check(application!.sourceAllocations == (reference.refused ? [:] : [config:540]),"source allocation ledger")
    check(heap.lookup(application!.startup!.automaticToken,words:1) == nil,"scoped automatic projection released")
    check(words(heap,outer,149) == outerBefore && words(heap,window,3) == windowBefore,"platform inputs preserved")
    func normalized(_ source: [UInt32]) -> [UInt32] {
        var result = source
        if result[1] == reference.window {result[1] = window}
        if result[2] == reference.outer {result[2] = outer}
        if reference.config != 0 && result[0x38/4] == reference.config {result[0x38/4] = config}
        return result
    }
    check(words(heap,app,77) == normalized(reference.applicationWords),"complete prefix application bytes")
    check(words(heap,0x541328,5) == reference.clockWords,"complete prefix raw clocks")
    check(application!.clockReads == 5 && clockIndex == 5 && ticks == 1,"constructor/startup clock count")
    check(application!.startup!.cursorCount == reference.cursorFinal,"shared ordinary cursor count")
    check(application!.operationCalls[0x4254a0] == 1 && application!.operationCalls[0x425730] == 1,"one source entry each")
    check(application!.archive == nil && application!.pendingCommands.isEmpty,"no archive or commands fabricated")
    for offset: UInt32 in [0x2c,0x30,0x34] {check(heap.lookup(app+offset,words:1)!.pointee == 0,"no early state/scene/archive publication")}
    if let expected = reference.configBytes {
        let actual = Array(UnsafeBufferPointer(start:application!.bytes(config,count:540)!,count:540))
        check(actual.map {String(format:"%02x",$0)}.joined() == expected,"config allocation exactly540")
        check(application!.bytes(config+539,count:1) != nil && application!.bytes(config+540,count:1) == nil,"config exact bounds")
    }
    let nativeEvents = application!.startup!.events
    check(nativeEvents.count == reference.events.count,"ordered event count")
    for (native,original) in zip(nativeEvents,reference.events) {
        check(native.function == original.function && native.arguments == original.arguments,"full ordered call \(String(original.function,radix:16))")
        let receiver = original.receiver == reference.config && reference.config != 0 ? config : original.receiver
        check(native.receiver == receiver && native.localMask == 0 && native.bufferBytes.isEmpty && native.bufferPresent.isEmpty,"raw call envelope")
        let value = original.function == 0x4f63ec && original.result != 0 ? config : original.result
        check(native.result == value,"source/service return")
        check(native.applicationWords == normalized(original.applicationWords),"live application at call \(String(original.function,radix:16))")
        check(native.clockWords == original.clockWords,"live clock aliases at callback")
        comparedEvents += 1
    }
    check(nativeEvents.last!.arguments.count == 6 && nativeEvents.last!.receiver == config,"six config arguments retained")
    let random = application!.startup!.random!
    check(random.heap === heap && random.initialized && random.fault == 0,"same-heap real CRT owner")
    let thread = random.threadToken
    let nativeThread = words(heap,thread,29)
    check(Array(nativeThread.dropFirst()) == Array(reference.threadWords.dropFirst()),"all CRT thread fields except physical thread ID")
    check(heap.lookup(0x52edd8,words:1)!.pointee == reference.tlsIndex,"raw source TLS alias")
    check(random.calls[0x4a3040] == 1 && random.seedPointer!.pointee == reference.threadWords[5],"shared source seed")
    // Confirm a second real CRT client observes the same source seed pointer.
    let seed = random.seedPointer!.pointee
    let expectedSeed = seed &* 214013 &+ 2531011
    check(random.call(0x4a3050) == ((expectedSeed >> 16) & 0x7fff) && random.seedPointer!.pointee == expectedSeed,"shared next source random draw")
    let oldFault = completion.canonicalFault, oldEvents = nativeEvents
    let again = application!.invoke(fullCall(0x425730,receiver:app,arguments:[window,command]))
    check(again.canonicalFault == oldFault && !again.completed && application!.startup!.events == oldEvents,"no retries after partial writes")
    application = nil
    check(heap.lookup(app,words:1) == nil && heap.lookup(command,words:1) == nil,"application transport ownership release")
    if config != 0 {check(heap.lookup(config,words:1) == nil,"source config cleanup after halt")}
    heap.free(outer);heap.free(window)
    print("PASS \(reference.name): original4254a0→425730 prefix, ordered callback snapshots, exact4b5c50 halt")
}

// Malformed entry envelopes cannot start source startup or replace the first fault.
for variant in 0..<5 {
    let owner = try ClawNativeApplication(clock:{1})
    var call = fullCall(0x425730,receiver:owner.applicationToken,arguments:[0,0])
    if variant == 0 {call.argumentCount = 0}
    if variant == 1 {call.receiver = owner.applicationToken+4}
    if variant == 2 {call.receiver2 = 1}
    if variant == 3 {call.x87ArgumentCount = 1}
    if variant == 4 {call.stackPointer = UInt32(CLAW_STACK_TOP)-32}
    let result = owner.invoke(call)
    check(result.canonicalFault?.diagnostic == .unsupportedABI && result.eax == nil,"strict startup ABI")
    check(owner.startup == nil && owner.clockReads == 2 && owner.sourceAllocations.isEmpty,"no work for invalid envelope")
    check(owner.invoke(fullCall(0xdeadbeef)).canonicalFault == result.canonicalFault,"first fault retained")
}
do {
    let owner = try ClawNativeApplication(clock:{1})
    do {_ = try owner.invoke(0x425730,receiver:owner.applicationToken);preconditionFailure("invalid startup returned")}
    catch let error as ClawNativeApplication.Failure {check(error == .invalidCall(0x425730),"throwing API strict arity")}
}
do {
    let owner = try ClawNativeApplication(clock:{1})
    let window = owner.heap.allocate(bytes:8)
    owner.heap.lookup(window+4,words:1)!.pointee = 1
    let command = try owner.makeCString("")
    let result = owner.invoke(fullCall(0x425730,receiver:owner.applicationToken,arguments:[window,command]))
    check(result.canonicalFault?.diagnostic == .invalidMemorySpan && result.canonicalFault?.address == window+8,"exact source window span failure")
    check(owner.startup!.fault == 1 && owner.clockReads == 2 && owner.startup!.events.isEmpty,"no services after incomplete source owner lookup")
    check(owner.heap.lookup(owner.applicationToken+4,words:1)!.pointee == window,"source store preceding memory failure retained")
    check(owner.heap.lookup(owner.startup!.automaticToken,words:1) == nil,"automatic lifetime on memory fault")
    owner.heap.free(window)
}
do {
    var owner: ClawNativeApplication? = try ClawNativeApplication(clock:{1})
    let heap = owner!.heap, app = owner!.applicationToken
    let outer = heap.allocate(bytes:0x254), window = heap.allocate(bytes:12)
    heap.lookup(window+4,words:2)!.update(from:[1,outer],count:2)
    let command = try owner!.makeCString("")
    _ = owner!.invoke(fullCall(0x425730,receiver:app,arguments:[window,command]))
    weak var startup = owner!.startup
    weak var random = owner!.startup!.random
    let thread = random!.threadToken, config = heap.lookup(app+0x38,words:1)!.pointee
    owner = nil
    check(startup == nil && random == nil,"application owns startup and CRT lifetime")
    for token in [app,command,thread,config] {check(heap.lookup(token,words:1) == nil,"halt cleanup releases source and transport objects once")}
    heap.free(outer);heap.free(window)
}

// Rich callback contracts are checked before scalar conversion or side effects.
for variant in 0..<7 {
    let owner = try ClawNativeApplication(clock:{1})
    let runtime = ClawNativeApplicationStartup(application:owner,tickClock:{2},initialCursorCount:0)
    var context = ClawApplicationStartupContext(), call = ClawApplicationStartupCall()
    call.function = 0x546d54;call.argumentCount = 1
    if variant == 0 {call.argumentCount = 41}
    if variant == 1 {call.bufferCount = 4}
    if variant == 2 {call.localMask = 1}
    if variant == 3 {call.receiver = 1}
    if variant == 4 {call.argumentCount = 2}
    if variant == 5 {call.bufferCount = 1;call.bufferBytes.0 = 4}
    if variant == 6 {call.function = 0xdeadbeef;call.argumentCount = 0;call.localMask = 2}
    _ = runtime.service(call,context:&context)
    check(context.fault == 2 && runtime.fault == 2 && runtime.cursorCount == 0 && runtime.events.isEmpty,"malformed rich envelope rejected")
    let originalFault = owner.canonicalHost.fault
    call.function = 0xdeadbeef
    _ = runtime.service(call,context:&context)
    check(owner.canonicalHost.fault == originalFault,"rich callback first fault retained")
}
do {
    let owner = try ClawNativeApplication(clock:{1})
    let runtime = ClawNativeApplicationStartup(application:owner,tickClock:{2},initialCursorCount:0)
    var context = ClawApplicationStartupContext(), call = ClawApplicationStartupCall()
    call.function = 0xdeadbeef;call.receiver = 0xaabbccdd;call.argumentCount = 40
    call.localMask = 0x101;call.bufferCount = 2;call.bufferBytes.0 = 4;call.bufferBytes.1 = 7
    withUnsafeMutableBytes(of:&call.arguments) {raw in
        for i in 0..<40 {raw.storeBytes(of:UInt32(i)+0xf0000000,toByteOffset:i*4,as:UInt32.self)}
    }
    // Unknown services retain only diagnostic shape; no borrowed pointer escapes.
    var borrowed: UInt32 = 0x12345678
    var second = [UInt8](repeating:0xa5,count:7)
    withUnsafeMutablePointer(to:&borrowed) {pointer in
        second.withUnsafeMutableBytes {buffer in
            call.buffers.0 = UnsafeMutableRawPointer(pointer);call.buffers.1 = buffer.baseAddress!
            _ = runtime.service(call,context:&context)
        }
    }
    let event = runtime.events.first!
    check(event.arguments.count == 40 && event.arguments[39] == 0xf0000027 && event.receiver == 0xaabbccdd,"unknown rich arguments not truncated")
    check(event.localMask == 0x101 && event.bufferBytes == [4,7] && event.bufferPresent == [true,true],"borrowed buffer shape retained")
    check(borrowed == 0x12345678 && second == [UInt8](repeating:0xa5,count:7) && event.result == nil && context.fault == 1,"unsupported rich call not serviced")
    check(owner.canonicalHost.fault?.diagnostic == .missingDependency && owner.canonicalHost.fault?.address == 0xdeadbeef,"unknown exact address")
}
do {
    let owner = try ClawNativeApplication(clock:{1},sourceAllocationByteLimit:0)
    let runtime = ClawNativeApplicationStartup(application:owner,tickClock:{0},initialCursorCount:1)
    var context = ClawApplicationStartupContext(), call = ClawApplicationStartupCall()
    call.function = 0x546d54;call.argumentCount = 1
    check(runtime.service(call,context:&context) == 0 && context.fault == 0,"cursor count zero is ordinary success")
    call.function = 0x4f63ec;call.arguments.0 = 540
    check(runtime.service(call,context:&context) == 0 && context.fault == 0 && owner.fault == nil,"source allocation zero is ordinary success")
    check(runtime.events.count == 2 && runtime.events.allSatisfy {$0.result == 0},"zero source/service results retained")
}
do {
    let owner = try ClawNativeApplication(clock:{1})
    let runtime = ClawNativeApplicationStartup(application:owner,tickClock:{0},initialCursorCount:Int32.min)
    var context = ClawApplicationStartupContext(), call = ClawApplicationStartupCall()
    call.function = 0x546d54;call.argumentCount = 1
    _ = runtime.service(call,context:&context)
    check(context.fault == 2 && runtime.cursorCount == Int32.min,"no invented cursor overflow")
}
print("PASS \(comparedEvents) composed original callback/memory comparisons; strict entry/rich ABI, retained first faults, ordinary zero results, scoped ownership")
print("LIMIT synthetic platform records; stops before4b5c50 executes; no configuration/menu/window/media/device acceptance")
