import Foundation
import CryptoKit

struct Resource: Decodable {let folder:String;let name:String;let bytes:UInt32;let tag:UInt32;let sha256:String}
struct Inventory: Decodable {let resources:[Resource]}
func fullCall(_ function: UInt32, receiver: UInt32 = 0, arguments: [UInt32] = []) -> ClawCall {
    precondition(arguments.count <= 16)
    var call = ClawCall();call.function = function;call.receiver = receiver;call.argumentCount = UInt32(arguments.count)
    withUnsafeMutableBytes(of:&call.arguments) {target in
        arguments.withUnsafeBytes {source in
            UnsafeMutableRawBufferPointer(rebasing:target.prefix(source.count)).copyMemory(from:source)
        }
    }
    return call
}
guard CommandLine.arguments.count == 4 else {fatalError("Usage: application-tests CLAW.REZ inventory.json bootstrap-reference.json")}
let archiveURL = URL(fileURLWithPath:CommandLine.arguments[1])
let discHash = SHA256.hash(data:try Data(contentsOf:archiveURL,options:.mappedIfSafe)).map {String(format:"%02x",$0)}.joined()
precondition(discHash == "b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596")
let inventory = try JSONDecoder().decode(Inventory.self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2])))
precondition(inventory.resources.count == 13077)

var readIndex = 0
let samples: [UInt32] = [100,125,150,160,185,200]
var application: ClawNativeApplication? = try ClawNativeApplication(clock:{
    precondition(readIndex < samples.count)
    defer {readIndex += 1};return samples[readIndex]
})
let heap = application!.heap, appToken = application!.applicationToken
let app = heap.lookup(appToken,words:77)!
func word(_ offset: UInt32) -> UInt32 {heap.lookup(appToken+offset,words:1)!.pointee}
precondition(application!.constructed && application!.fault == nil)
precondition(application!.operationCalls == [0x4254a0:1] && application!.clockReads == 2 && readIndex == 2)
// Source4254a0 defaults: application identity, CString cells, history and
// options. A constructor is not a loaded scene, archive or configured window.
precondition(word(0) == 0x50bee4 && word(4) == 0 && word(8) == 0 && word(12) == 0)
precondition(word(0x10) == 1 && word(0x14) == 1 && word(0x18) == .max)
precondition(word(0x1c) == 0 && word(0x20) == 0 && word(0x24) == 100)
precondition(word(0x2c) == 0 && word(0x30) == 0 && word(0x34) == 0 && word(0x38) == 0)
precondition(word(0xc0) == 0x52e1c4 && word(0xf8) == 0x52e1c4 && word(0xfc) == 0x52e1c4 && word(0x100) == 0x52e1c4)
precondition(word(0xdc) == 0x51079c && word(0xe0) == 0 && word(0xe4) == 0)
precondition(word(0x68) == 2 && word(0xc8) == 30 && word(0x78) == 8)
precondition(word(0x118) == 1 && word(0x11c) == 1 && word(0x120) == 0 && word(0x124) == 1 && word(0x128) == 1)
precondition(heap.lookup(0x52e1b8,words:4)![0] == .max && heap.lookup(0x52e1cc,words:1)!.pointee == 0x52e1c4)
precondition(application!.bytes(0x52e1c4,count:1)!.pointee == 0)
precondition(application!.clockSnapshot.nowMilliseconds == 125 && application!.clockSnapshot.deltaMilliseconds == 0)
for token: UInt32 in [0x537208,0x53720c,0x5430c8,0x5430c4,0x537e88] {
    precondition(heap.lookup(token,words:1)!.pointee == 0)
}
let firstTick = try application!.invoke(0x4b82f0,receiver:appToken)
precondition(firstTick == 1 && application!.clockSnapshot.nowMilliseconds == 150 && application!.clockSnapshot.deltaMilliseconds == 25)
let timer = heap.lookup(0x541328,words:5)!
timer[3] = 9;timer[4] = 17
_ = try application!.invoke(0x4b82f0,receiver:appToken)
precondition(timer[0] == 160 && timer[1] == 10 && timer[3] == 0 && word(0x20) == 2)
_ = try application!.invoke(0x4b82f0,receiver:appToken)
precondition(timer[0] == 185 && timer[1] == 25 && timer[3] == 17 && word(0x20) == 3)
precondition(application!.clockReads == 5 && readIndex == 5)
print("PASS original application constructor defaults and two native clock reads; GameTiming updates the same raw manager and global clock aliases")

let textToken = try application!.makeCString("claw")
precondition(application!.bytes(textToken+4,count:1)!.pointee == 0)
precondition(application!.bytes(textToken+5,count:1) == nil && application!.bytes(.max,count:2) == nil)
application!.postCommand(handlerWord:0x12345678,command:0xabcd807f,data:0xfedcba98)
application!.postCommand(command:0x807c,data:1)
let batch = application!.takePendingCommands()
precondition(batch == [ClawNativeApplication.Command(handlerWord:0x12345678,command:0xabcd807f,data:0xfedcba98),
                       ClawNativeApplication.Command(handlerWord:0,command:0x807c,data:1)])
precondition(application!.pendingCommands.isEmpty)
application!.postCommand(command:0x8075)
precondition(batch.count == 2 && application!.takePendingCommands() == [ClawNativeApplication.Command(handlerWord:0,command:0x8075,data:0)])
print("PASS exact CString byte bounds and deferred command batches preserve all original words without LOWORD dispatch")

// A legitimate supplied caller record at application+8 is the only added
// fixture needed by the default factory arm. No state, menu or vtable is faked.
precondition(application!.canonicalHost.heap === heap)
let callerAllocation = application!.invoke(fullCall(0x4f63ec,arguments:[0x248]))
precondition(callerAllocation.completed && callerAllocation.eax != 0 && callerAllocation.canonicalFault == nil)
let caller = callerAllocation.eax!
heap.lookup(appToken+8,words:1)!.pointee = caller
heap.lookup(caller+0x244,words:1)!.pointee = 99
let factory = application!.invoke(fullCall(0x428c40,receiver:appToken,arguments:[0,0,1,0]))
precondition(factory.completed && factory.eax == 0 && factory.fault == nil && factory.canonicalFault == nil)
precondition(word(0x2c) == 0 && heap.lookup(caller+0x244,words:1)!.pointee == 0)
precondition(application!.canonicalHost.bytes(caller+0x244,count:4)!.pointee == 0)
let nativeTiming = application!.invoke(fullCall(0x4b82f0,receiver:appToken))
precondition(nativeTiming.completed && nativeTiming.eax == 1 && nativeTiming.fault == nil)
precondition(timer[0] == 200 && timer[1] == 15 && application!.clockReads == 6)
precondition(application!.sourceAllocations == [caller:0x248] && word(0) == 0x50bee4)
print("PASS constructed application → real canonical state-factory default arm returns EAX0, writes caller alias, and retains original app/current-state identity; full-envelope native timing shares its clock")

let inputs = try application!.prepareArchive(at:archiveURL)
precondition(inputs.controller != appToken && application!.archive!.controller == inputs.controller)
precondition(application!.archive!.heap === heap && !application!.archive!.ownsController)
precondition(application!.archive!.operationCalls.isEmpty && !application!.archive!.hasOpenFile && word(0x34) == 0)
let constructorResult = application!.invoke(fullCall(0x4b7210,receiver:inputs.controller))
let openResult = application!.invoke(fullCall(0x4b72e0,receiver:inputs.controller,arguments:[inputs.path,1,0]))
precondition(constructorResult.completed && constructorResult.eax == inputs.controller && openResult.completed && openResult.eax == 1 && application!.archive!.fault == 0)
let sample = inventory.resources.first {$0.bytes > 0}!
var folder = application!.archive!.lookupFolder("")
for component in sample.folder.split(separator:"\\") {
    folder = application!.archive!.lookupChild(folder:folder,name:String(component));precondition(folder != 0)
}
let resource = application!.archive!.lookupResource(folder:folder,name:sample.name,tag:sample.tag)
let payload = application!.archive!.payload(resource)!
precondition(UInt32(payload.count) == sample.bytes && SHA256.hash(data:payload).map {String(format:"%02x",$0)}.joined() == sample.sha256)
let sourceTokens = Array(application!.archive!.sourceAllocations.keys)
let destroyResult = application!.invoke(fullCall(0x4b7250,receiver:inputs.controller))
precondition(destroyResult.completed && destroyResult.eax == 0 && application!.archive!.sourceAllocations.isEmpty && application!.archive!.fault == 0)
precondition(application!.archive!.operationCalls == [0x4b7210:1,0x4b72e0:1,0x4b7250:1])
precondition(application!.archive!.fileCloseCount == 1 && application!.archive!.calls[0x4a7ae0] == 2)
precondition(heap.lookup(inputs.controller,words:18) != nil && heap.lookup(inputs.path,words:1) != nil)
try application!.releaseArchive()
precondition(application!.archive == nil && application!.archiveInputs == nil)
precondition(sourceTokens.allSatisfy {heap.lookup($0,words:1) == nil})
precondition(heap.lookup(inputs.controller,words:1) == nil && heap.lookup(inputs.path,words:1) == nil)
precondition(heap.lookup(appToken,words:77) == app && word(0) == 0x50bee4 && word(0x34) == 0)
precondition(application!.operationCalls[0x4254a0] == 1 && application!.clockReads == 6)
print("PASS application-owned REZ controller and path, explicit source constructor/open, real payload hash, destructor and caller release; application storage remains live")

// Startup requires its two original arguments; constructor success cannot
// excuse a malformed call into the newly supported prefix adapter.
do {
    _ = try application!.invoke(0x425730,receiver:appToken)
    fatalError("Unsupported full bootstrap succeeded")
} catch let failure as ClawNativeApplication.Failure {
    precondition(failure == .invalidCall(0x425730) && application!.fault == failure)
}
application = nil
precondition(heap.lookup(appToken,words:1) == nil && heap.lookup(textToken,words:1) == nil && heap.lookup(caller,words:1) == nil)
let callbackOwner = try ClawNativeApplication(clock:{321})
var unsupported = ClawSceneActorCall();unsupported.function = 0xdeadbeef;unsupported.receiver = callbackOwner.applicationToken
let host = callbackOwner.actorHost
let callbackResult = host.call!(host.context,unsupported)
precondition(callbackResult == 0 && callbackOwner.fault == .unsupportedFunction(0xdeadbeef))
precondition(callbackOwner.operationCalls == [0x4254a0:1])
print("PASS unsupported Swift and C host addresses surface sticky faults; application-owned dynamic storage is released with its owner")

// Source allocation refusal is an original zero return. The explicit budget
// is a native resource constraint for this test, not an app/menu fixture.
do {
    let owner = try ClawNativeApplication(clock:{1},sourceAllocationByteLimit:0)
    let caller = owner.heap.allocate(bytes:0x248)
    owner.heap.lookup(owner.applicationToken+8,words:1)!.pointee = caller
    owner.heap.lookup(caller+0x244,words:1)!.pointee = 77
    let allocation = owner.invoke(fullCall(0x4f63ec,arguments:[344]))
    precondition(allocation.completed && allocation.eax == 0 && allocation.fault == nil && owner.sourceAllocations.isEmpty)
    let transition = owner.invoke(fullCall(0x428c40,receiver:owner.applicationToken,arguments:[2,1,1,0]))
    precondition(transition.completed && transition.eax == 0 && transition.fault == nil && transition.canonicalFault == nil)
    precondition(owner.heap.lookup(caller+0x244,words:1)!.pointee == 0)
    precondition(owner.heap.lookup(owner.applicationToken+0x2c,words:1)!.pointee == 0 && owner.sourceAllocations.isEmpty)
    precondition(owner.invoke(fullCall(0x4f6428,arguments:[0])).eax == 0 && owner.fault == nil)
    owner.heap.free(caller)
}
do {
    let owner = try ClawNativeApplication(clock:{1},sourceAllocationByteLimit:7)
    let allocated = owner.invoke(fullCall(0x4f63ec,arguments:[7]))
    precondition(allocated.completed && allocated.eax != 0 && allocated.fault == nil)
    let token = allocated.eax!
    precondition(owner.sourceAllocations == [token:7] && owner.bytes(token+6,count:1) != nil && owner.bytes(token+7,count:1) == nil)
    let refused = owner.invoke(fullCall(0x4f63ec,arguments:[1]))
    precondition(refused.completed && refused.eax == 0 && refused.fault == nil)
    let deleted = owner.invoke(fullCall(0x4f6428,arguments:[token]))
    precondition(deleted.completed && deleted.eax == 0 && deleted.fault == nil)
    precondition(owner.sourceAllocations.isEmpty && owner.heap.lookup(token,words:1) == nil)
    let replacement = owner.invoke(fullCall(0x4f63ec,arguments:[7]))
    precondition(replacement.completed && replacement.eax != 0 && replacement.fault == nil)
    let invalid = owner.invoke(fullCall(0x4f6428,arguments:[owner.applicationToken]))
    precondition(!invalid.completed && invalid.eax == nil && invalid.canonicalFault?.code == UInt32(CLAW_FAULT_MEMORY))
    precondition(invalid.canonicalFault?.address == owner.applicationToken && owner.heap.lookup(owner.applicationToken,words:77) != nil)
}
print("PASS source new returns legitimate zero on resource refusal; actual type2 factory follows allocation-failure branch; successful source allocations have exact bounds, reusable budget and distinct delete ownership")

// The actual base constructor only writes its declared sparse fields. Poison
// the source allocation so untouched padding and the partial byte store cannot
// accidentally pass because the physical allocator initially zeroed memory.
do {
    let owner = try ClawNativeApplication(clock:{1})
    let allocation = owner.invoke(fullCall(0x4f63ec,arguments:[0x158]))
    precondition(allocation.completed && allocation.eax != 0)
    let token = allocation.eax!, raw = owner.bytes(allocation.eax!,count:0x158)!
    raw.update(repeating:0xa5,count:0x158)
    let result = owner.invoke(fullCall(0x40b5c0,receiver:token))
    precondition(result.completed && result.eax == 0 && result.fault == nil && result.canonicalFault == nil)
    var expected = [UInt8](repeating:0xa5,count:0x158)
    func expectedWord(_ offset: Int, _ word: UInt32) {
        for i in 0..<4 {expected[offset+i] = UInt8(truncatingIfNeeded:word >> (i*8))}
    }
    expectedWord(0,0x50b4ec)
    for offset in [4,8,12,0x1c,0x20,0x24,0x2c,0x30,0x3c,0x40,0x34,0x18,0x150] {expectedWord(offset,0)}
    expected[0x4c] = 0
    precondition(Array(UnsafeBufferPointer(start:raw,count:0x158)) == expected)
    precondition(owner.sourceAllocations == [token:0x158] && owner.clockReads == 2 && owner.operationCalls[0x40b5c0] == 1)
    precondition(owner.invoke(fullCall(0x4f6428,arguments:[token])).completed && owner.heap.lookup(token,words:1) == nil)
}
print("PASS native40b5c0 base constructor preserves zero EAX, source-owned allocation, exact sparse words, byte-only clear and untouched padding")

// Raw values here are explicit test inputs, not application/menu defaults.
// With no scene, reset reads only once and leaves animation/countdowns intact.
do {
    let owner = try ClawNativeApplication(clock:{99}), heap = owner.heap
    let clock = heap.lookup(0x541328,words:5)!, stage = heap.lookup(0x537208,words:2)!
    let animation = heap.lookup(0x5430c4,words:2)!
    clock[0] = 7;clock[1] = 8;clock[2] = 9;clock[3] = 10;clock[4] = 11
    stage[0] = 12;stage[1] = 13;animation[0] = 14;animation[1] = 15
    let result = owner.invoke(fullCall(0x42abf0,receiver:owner.applicationToken))
    precondition(result.completed && result.eax == 0 && result.fault == nil && owner.clockReads == 3)
    precondition(Array(UnsafeBufferPointer(start:clock,count:5)) == [99,0,0,10,11])
    precondition(stage[0] == 99 && stage[1] == 0 && animation[0] == 14 && animation[1] == 15)
    // A later runtime's writes must replace the old snapshot before each call.
    clock[3] = 31;clock[4] = 32;animation[0] = 33;animation[1] = 34
    precondition(owner.invoke(fullCall(0x42abf0,receiver:owner.applicationToken)).completed)
    precondition(clock[3] == 31 && clock[4] == 32 && animation[0] == 33 && animation[1] == 34 && owner.clockReads == 4)
    let player = owner.invoke(fullCall(0x4f63ec,arguments:[0x70])).eax!
    let primary = owner.invoke(fullCall(0x4f63ec,arguments:[0x18])).eax!
    heap.lookup(player+0x6c,words:1)!.pointee = primary
    heap.lookup(0x537e88,words:1)!.pointee = player
    precondition(heap.lookup(primary+0x14,words:1)!.pointee == 0)
    let nullPrivate = owner.invoke(fullCall(0x42abf0,receiver:owner.applicationToken))
    precondition(nullPrivate.completed && nullPrivate.eax == 0 && owner.clockReads == 5)
}
// Clock callbacks observe source-prefix stores and can mutate live aliases.
// The second clock read is controlled by app+30 after the first callback.
do {
    var sharedHeap: ClawTokenHeap?, app: UInt32 = 0, player: UInt32 = 0, reads = 0
    let owner = try ClawNativeApplication(clock:{
        reads += 1
        guard let heap = sharedHeap else {return 1}
        let clock = heap.lookup(0x541328,words:5)!, stage = heap.lookup(0x537208,words:2)!
        let animation = heap.lookup(0x5430c4,words:2)!
        if reads == 3 {
            precondition(Array(UnsafeBufferPointer(start:clock,count:5)) == [10,11,12,13,14])
            precondition(stage[0] == 30 && stage[1] == 31 && animation[0] == 40 && animation[1] == 41)
            clock[3] = 700;clock[4] = 701;stage[0] = 50;stage[1] = 51
            animation[0] = 60;animation[1] = 61
            heap.lookup(app+0x30,words:1)!.pointee = 1
            return 300
        }
        precondition(reads == 4)
        precondition(Array(UnsafeBufferPointer(start:clock,count:5)) == [300,0,0,700,701])
        precondition(stage[0] == 50 && stage[1] == 51 && animation[0] == 60 && animation[1] == 61)
        clock[0] = 900;clock[1] = 9;clock[2] = 8;clock[3] = 702;clock[4] = 703
        heap.lookup(0x537e88,words:1)!.pointee = player
        return 400
    })
    sharedHeap = owner.heap;app = owner.applicationToken
    let heap = owner.heap, clock = heap.lookup(0x541328,words:5)!
    for (i,value) in [UInt32(10),11,12,13,14].enumerated() {clock[i] = value}
    heap.lookup(0x537208,words:2)![0] = 30;heap.lookup(0x537208,words:2)![1] = 31
    heap.lookup(0x5430c4,words:2)![0] = 40;heap.lookup(0x5430c4,words:2)![1] = 41
    func allocateSource(_ bytes: UInt32) -> UInt32 {owner.invoke(fullCall(0x4f63ec,arguments:[bytes])).eax!}
    player = allocateSource(0x70)
    let primary = allocateSource(0x18), privateState = allocateSource(0x124)
    heap.lookup(player+0x6c,words:1)!.pointee = primary
    heap.lookup(primary+0x14,words:1)!.pointee = privateState
    heap.lookup(privateState+0x120,words:1)!.pointee = 123
    let result = owner.invoke(fullCall(0x42abf0,receiver:app))
    precondition(result.completed && result.eax == 0 && owner.clockReads == 4 && reads == 4)
    precondition(Array(UnsafeBufferPointer(start:clock,count:5)) == [900,9,8,702,703])
    precondition(heap.lookup(0x537208,words:2)![0] == 900 && heap.lookup(0x537208,words:2)![1] == 9)
    precondition(heap.lookup(0x5430c4,words:2)![0] == 0 && heap.lookup(0x5430c4,words:2)![1] == 400)
    precondition(heap.lookup(0x537e88,words:1)!.pointee == player && heap.lookup(privateState+0x120,words:1)!.pointee == 20000)
    precondition(owner.sourceAllocations == [player:0x70,primary:0x18,privateState:0x124])
}
// Each player-graph failure occurs after both clocks and stage publication.
// In particular a short private allocation must not pass via word padding.
for missing in 0..<3 {
    let owner = try ClawNativeApplication(clock:{123}), heap = owner.heap
    func allocateSource(_ bytes: UInt32) -> UInt32 {owner.invoke(fullCall(0x4f63ec,arguments:[bytes])).eax!}
    let player = allocateSource(missing == 0 ? 0x6f : 0x70)
    let primary = allocateSource(missing == 1 ? 0x17 : 0x18)
    let privateState = allocateSource(0x123)
    if missing != 0 {heap.lookup(player+0x6c,words:1)!.pointee = primary}
    if missing != 1 {heap.lookup(primary+0x14,words:1)!.pointee = privateState}
    heap.lookup(0x537e88,words:1)!.pointee = player
    heap.lookup(owner.applicationToken+0x30,words:1)!.pointee = 1
    heap.lookup(0x541328,words:5)![3] = 7;heap.lookup(0x541328,words:5)![4] = 8
    let address = missing == 0 ? player+0x6c : missing == 1 ? primary+0x14 : privateState+0x120
    let result = owner.invoke(fullCall(0x42abf0,receiver:owner.applicationToken))
    precondition(!result.completed && result.eax == nil && result.fault == .invalidSpan(address,4))
    precondition(result.canonicalFault?.code == UInt32(CLAW_FAULT_HOST) && result.canonicalFault?.address == 0x42abf0)
    precondition(owner.clockReads == 4 && owner.operationCalls[0x42abf0] == 1)
    precondition(owner.clockSnapshot.nowMilliseconds == 123 && owner.clockSnapshot.countdown == 7 && owner.clockSnapshot.countdownReload == 8)
    precondition(heap.lookup(0x537208,words:2)![0] == 123 && heap.lookup(0x537208,words:2)![1] == 0)
    precondition(heap.lookup(0x5430c4,words:2)![0] == 0 && heap.lookup(0x5430c4,words:2)![1] == 123)
    precondition(owner.invoke(fullCall(0xdeadbeef)).fault == result.fault)
}
print("PASS native42abf0 preserves live raw aliases, no-scene animation/countdowns, source clock order and callback writes, valid player cooldown, and the timer prefix on each exact player-span fault")
do {
    let owner = try ClawNativeApplication(clock:{1})
    owner.heap.free(0x537208)
    let result = owner.invoke(fullCall(0x42abf0,receiver:owner.applicationToken))
    precondition(!result.completed && result.eax == nil && result.fault == .invalidSpan(0x537208,8))
    precondition(owner.clockReads == 2 && owner.operationCalls[0x42abf0] == nil)
}

// Actual type2 factory now completes allocation/base construction, publishes
// the concrete source state, resets clocks, and stops at missing vtable metadata.
// Host teardown frees the reached prefix; no game destructor is fabricated.
do {
    var owner: ClawNativeApplication? = try ClawNativeApplication(clock:{1})
    let heap = owner!.heap, applicationToken = owner!.applicationToken
    let result = owner!.invoke(fullCall(0x428c40,receiver:applicationToken,arguments:[2,1,1,0]))
    precondition(!result.completed && result.eax == nil && result.canonicalFault?.code == UInt32(CLAW_FAULT_MEMORY))
    precondition(result.canonicalFault?.address == 0x50c2d8 && result.canonicalFault?.diagnostic == .invalidMemorySpan)
    precondition(owner!.sourceAllocations.count == 1 && owner!.sourceAllocations.values.first == 0x158)
    let state = owner!.sourceAllocations.keys.first!
    precondition(heap.lookup(applicationToken+0x2c,words:1)!.pointee == state && heap.lookup(state,words:1)!.pointee == 0x50c2d4)
    for offset: UInt32 in [4,8,12,0x1c,0x20,0x24,0x2c,0x30,0x3c,0x40,0x34,0x18,0x150] {
        precondition(heap.lookup(state+offset,words:1)!.pointee == 0)
    }
    precondition(owner!.bytes(state+0x4c,count:1)!.pointee == 0 && owner!.bytes(state+0x158,count:1) == nil)
    precondition(owner!.operationCalls[0x40b5c0] == 1 && owner!.operationCalls[0x42abf0] == 1 && owner!.clockReads == 3)
    precondition(heap.lookup(0x537208,words:2)![0] == 1 && heap.lookup(0x537208,words:2)![1] == 0)
    let following = owner!.invoke(fullCall(0xdeadbeef))
    precondition(following.fault == result.fault && following.canonicalFault == result.canonicalFault)
    precondition(heap.lookup(applicationToken+0x2c,words:1)!.pointee == state)
    owner = nil
    precondition(heap.lookup(state,words:1) == nil && heap.lookup(applicationToken,words:1) == nil)
}
print("PASS canonical type2 allocation → native base ctor → source concrete vtable/current-state publication → native reset → missing50c2d8 metadata; prefix retained until owner cleanup")

// Invalid full envelopes must not be silently narrowed into valid legacy calls.
for invalid in 0..<12 {
    let owner = try ClawNativeApplication(clock:{1})
    var request = fullCall(0x4b82f0,receiver:owner.applicationToken)
    if invalid == 0 {request.argumentCount = 1}
    if invalid == 1 {request.receiver2 = 7}
    if invalid == 2 {request.x87ArgumentCount = 1;request.x87Argument = 3.5}
    if invalid == 3 {request.stackPointer = 0x02008000}
    if invalid == 4 {request.receiver = owner.applicationToken+4}
    if invalid == 5 {request = fullCall(0x4f63ec,receiver:owner.applicationToken,arguments:[16])}
    if invalid == 6 {request = fullCall(0x40b5c0,receiver:owner.applicationToken,arguments:[1])}
    if invalid >= 7 {
        request = fullCall(0x42abf0,receiver:owner.applicationToken)
        if invalid == 7 {request.argumentCount = 1}
        if invalid == 8 {request.receiver2 = 1}
        if invalid == 9 {request.x87ArgumentCount = 1;request.x87Argument = 2.5}
        if invalid == 10 {request.stackPointer = 0x02008000}
        if invalid == 11 {request.receiver += 4}
    }
    let result = owner.invoke(request)
    precondition(!result.completed && result.eax == nil && result.canonicalFault?.code == UInt32(CLAW_FAULT_ABI))
    precondition(result.canonicalFault?.address == request.function && result.canonicalFault?.diagnostic == .unsupportedABI)
    precondition(owner.clockReads == 2 && owner.sourceAllocations.isEmpty)
    let following = owner.invoke(fullCall(0x4f63ec,arguments:[16]))
    precondition(following.fault == result.fault && following.canonicalFault == result.canonicalFault && following.eax == nil)
}
do {
    let owner = try ClawNativeApplication(clock:{1})
    var bad = fullCall(0x428c40,receiver:owner.applicationToken,arguments:[0,0,1,0]);bad.stackPointer = 0x02010000
    let result = owner.invoke(bad)
    precondition(!result.completed && result.eax == nil && result.canonicalFault?.code == UInt32(CLAW_FAULT_ABI))
    precondition(result.canonicalFault?.address == 0x428c40 && result.canonicalFault?.diagnostic == .invalidStackFrame)
    precondition(owner.invoke(fullCall(0xdeadbeef)).canonicalFault == result.canonicalFault)
}
do {
    let owner = try ClawNativeApplication(clock:{1})
    let result = owner.invoke(fullCall(0xdeadbeef))
    precondition(!result.completed && result.eax == nil && result.canonicalFault?.code == UInt32(CLAW_CANONICAL_FAULT_UNKNOWN_ADDRESS))
    precondition(result.canonicalFault?.address == 0xdeadbeef && result.canonicalFault?.diagnostic == .unknownEntry)
    precondition(owner.invoke(fullCall(0x4f63ec,arguments:[16])).canonicalFault == result.canonicalFault && owner.sourceAllocations.isEmpty)
}
// An original wrapper with a verified child frame composes on the same heap.
do {
    let owner = try ClawNativeApplication(clock:{1}), heap = owner.heap
    let actor = heap.allocate(bytes:0x1b4), state = heap.allocate(bytes:0xc0)
    heap.lookup(actor+0x6c,words:1)!.pointee = state
    heap.lookup(state+0x1c,words:1)!.pointee = 1234
    heap.store(token:0x537b8c,words:1).pointee = 0
    let result = owner.invoke(fullCall(0x461fe0,arguments:[actor]))
    precondition(result.completed && result.eax == 0 && result.canonicalFault == nil)
    precondition(heap.lookup(0x537b8c,words:1)!.pointee == 2)
}
print("PASS exact missing-vtable fault, canonical and legacy ABI rejection, unknown-entry diagnostics, sticky faults and tracked native ObjectVariants → FloorSpike composition")

// Independent outputs are freshly produced by the hash-checked original, with
// only its CRT allocator supplied. These joins do not publish startup owners.
struct BootstrapOutput: Decodable {
    let eax: UInt32
    let arguments: [UInt32]
    let receiver_bytes: String
    let lookup_bytes: String?
    let receiver_prefix: String?
}
struct BootstrapReference: Decodable {
    let character: BootstrapOutput
    let character_refused: BootstrapOutput
    let resource: BootstrapOutput
    let variants: [VariantOutput]
}
struct VariantOutput: Decodable {
    let function: UInt32
    let raw_eax: UInt32
    let normalized_void_eax: UInt32
    let selector: UInt32
    let state_bytes: String
}
func unhex(_ value: String) -> Data {
    let bytes = Array(value.utf8)
    precondition(bytes.count % 2 == 0)
    return Data(stride(from: 0, to: bytes.count, by: 2).map {
        UInt8(String(decoding: bytes[$0..<$0+2], as: UTF8.self), radix: 16)!
    })
}
let bootstrapReference = try JSONDecoder().decode(BootstrapReference.self,
    from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[3])))
do {
    let owner = try ClawNativeApplication(clock: { 1 }), heap = owner.heap
    let actor = heap.allocate(bytes: 0x1b4), state = heap.allocate(bytes: 0xc0)
    heap.lookup(actor+0x6c, words: 1)!.pointee = state
    heap.lookup(state+0x1c, words: 1)!.pointee = 1234
    heap.store(token: 0x537b8c, words: 1).pointee = 0
    for reference in bootstrapReference.variants {
        let result = owner.invoke(fullCall(reference.function, arguments: [actor]))
        precondition(result.completed && result.eax == reference.normalized_void_eax && result.canonicalFault == nil)
        precondition(reference.raw_eax == 1)
        precondition(heap.lookup(0x537b8c, words: 1)!.pointee == reference.selector)
        precondition(Data(bytes: owner.bytes(state, count: 0xc0)!, count: 0xc0) == unhex(reference.state_bytes))
    }
}
print("PASS three real ObjectVariants → FloorSpike native calls with exact child frames, original selectors, state bytes and void-result normalization")
do {
    let owner = try ClawNativeApplication(clock: { 1 })
    let allocation = owner.invoke(fullCall(0x4f63ec, arguments: [8]))
    precondition(allocation.completed && allocation.eax != 0)
    let manager = allocation.eax!
    owner.bytes(manager, count: 8)!.initialize(repeating: 0xa5, count: 8)
    let result = owner.invoke(fullCall(0x493c20, receiver: manager))
    precondition(result.completed && result.eax == bootstrapReference.character.eax)
    precondition(Data(bytes: owner.bytes(manager, count: 4)!, count: 4) == unhex(bootstrapReference.character.receiver_prefix!))
    let table = owner.heap.lookup(manager+4, words: 1)!.pointee
    precondition(owner.sourceAllocations == [manager: 8, table: 128])
    precondition(Data(bytes: owner.bytes(table, count: 128)!, count: 128) == unhex(bootstrapReference.character.lookup_bytes!))
    precondition(owner.bytes(table+128, count: 1) == nil)
    precondition(owner.heap.lookup(owner.applicationToken+0x40, words: 1)!.pointee == 0)
}
do {
    let owner = try ClawNativeApplication(clock: { 1 }, sourceAllocationByteLimit: 8)
    let manager = owner.invoke(fullCall(0x4f63ec, arguments: [8])).eax!
    owner.bytes(manager, count: 8)!.initialize(repeating: 0xa5, count: 8)
    let result = owner.invoke(fullCall(0x493c20, receiver: manager))
    precondition(result.completed && result.eax == bootstrapReference.character_refused.eax && result.eax == 0)
    precondition(owner.fault == nil && owner.sourceAllocations == [manager: 8])
    precondition(Data(bytes: owner.bytes(manager, count: 8)!, count: 8) == unhex(bootstrapReference.character_refused.receiver_bytes))
}
do {
    let owner = try ClawNativeApplication(clock: { 1 })
    let manager = owner.invoke(fullCall(0x4f63ec, arguments: [40])).eax!
    owner.bytes(manager, count: 40)!.initialize(repeating: 0xa5, count: 40)
    let result = owner.invoke(fullCall(0x4ec010, receiver: manager, arguments: bootstrapReference.resource.arguments))
    precondition(result.completed && result.eax == bootstrapReference.resource.eax)
    precondition(Data(bytes: owner.bytes(manager, count: 40)!, count: 40) == unhex(bootstrapReference.resource.receiver_bytes))
    precondition(owner.heap.lookup(owner.applicationToken+0x44, words: 1)!.pointee == 0)
}
do {
    let owner = try ClawNativeApplication(clock: { 1 })
    let manager = owner.invoke(fullCall(0x4f63ec, arguments: [39])).eax!
    owner.bytes(manager, count: 39)!.initialize(repeating: 0xa5, count: 39)
    let result = owner.invoke(fullCall(0x4ec010, receiver: manager, arguments: bootstrapReference.resource.arguments))
    precondition(!result.completed && result.eax == nil && result.canonicalFault?.code == UInt32(CLAW_FAULT_MEMORY))
    precondition(result.canonicalFault?.address == manager+0x24)
    precondition(owner.heap.lookup(manager, words: 1)!.pointee == bootstrapReference.resource.arguments[0])
    precondition(owner.heap.lookup(manager+4, words: 1)!.pointee == 0xa5a5a5a5)
}
print("PASS original493c20 character-table bytes and genuine allocation refusal; original4ec010 sparse opaque fields, padding and reached prefix on exact39-byte fault, all in the shared application heap")
print("PASS native application owner foundation only; no full startup, scene transition, menu, gameplay or device claim")
