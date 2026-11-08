import Foundation
import CryptoKit

struct TextRead: Decodable {let pc: UInt32, offset: Int, count: Int}
struct ReferenceEvent: Decodable {
    let function: UInt32, receiver: UInt32, stackPointer: UInt32
    let arguments: [UInt32], result: UInt32?
    let applicationWords: [UInt32], clockWords: [UInt32]
    let beforeBytes: String?, afterBytes: String?
    let reads: [TextRead]?
}
struct ReferenceImport: Decodable {
    let function: UInt32, stackPointer: UInt32, result: UInt32
    let arguments: [UInt32]
    let subkeyHex: String?, nameHex: String?, capacity: UInt32?
    let handle: UInt32?, disposition: UInt32?, outputType: UInt32?, outputSize: UInt32?, outputBytes: String?
}
struct Physical: Decodable {
    let function: UInt32, stackPointer: UInt32, result: UInt32
    let arguments: [UInt32]
    let rootHex: String?, outputBytes: String?
}
struct PregraphicsReference: Decodable {
    let hookFrame: UInt32
    let hookReceiverBefore: String, hookReceiverAfter: String
    let beforeBytes: String, afterBytes: String
    let initialGlobals: [String:UInt32], globals: [String:UInt32]
}
struct Reference: Decodable {
    let pregraphics: PregraphicsReference
    let name: String, sha256: String, fault: String?
    let commandHex: String, storedUserHex: String?
    let commandBytes: String, userCommandBytes: String, initialUserCommandBytes: String
    let textInitialGlobals: [String:UInt32], textGlobals: [String:UInt32]
    let currentDirectory: String, present: Bool
    let stop: ReferenceEvent, nested: [ReferenceEvent], physical: [Physical]
    let app: UInt32, outer: UInt32, window: UInt32, config: UInt32
    let applicationWords: [UInt32], clockWords: [UInt32]
    let configBytes: String?, userBytes: String, userLength: UInt32
    let events: [ReferenceEvent], imports: [ReferenceImport]
    let strings: [String:String], initialGlobals: [String:UInt32], globals: [String:UInt32]
}
func check(_ value: @autoclosure () -> Bool, _ label: String) {precondition(value(),label)}
func decodeHex(_ hex: String) -> [UInt8] {
    check(hex.count % 2 == 0,"hex extent")
    return stride(from:0,to:hex.count,by:2).map {offset in
        let start = hex.index(hex.startIndex,offsetBy:offset)
        return UInt8(hex[start..<hex.index(start,offsetBy:2)],radix:16)!
    }
}
func words(_ heap: ClawTokenHeap, _ token: UInt32, _ count: Int) -> [UInt32] {
    Array(UnsafeBufferPointer(start:heap.lookup(token,words:UInt32(count))!,count:count))
}
func bytes(_ heap: ClawTokenHeap, _ token: UInt32, _ count: Int) -> [UInt8] {
    Array(UnsafeBufferPointer(start:heap.lookupBytes(token,count:UInt32(count))!,count:count))
}
func call(_ f: UInt32, _ receiver: UInt32, _ arguments: [UInt32]) -> ClawCall {
    var value = ClawCall();value.function = f;value.receiver = receiver;value.argumentCount = UInt32(arguments.count)
    withUnsafeMutableBytes(of:&value.arguments) {target in arguments.withUnsafeBytes {target.copyMemory(from:$0)}}
    return value
}
let referenceData = try Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1]))
let references = try JSONDecoder().decode([Reference].self,from:referenceData)
check(references.count == 6,"six original text profiles")
let image = references[0]
let preparedFile = URL(fileURLWithPath:CommandLine.arguments[2])
let metadata = try ClawNativeApplicationMetadata.load(from:preparedFile)
let strings = metadata.strings, initials = metadata.initialGlobals, discStrings = metadata.discStrings
let textStrings = metadata.textStrings, textInitials = metadata.textInitialGlobals
let pregraphicsInitials = metadata.pregraphicsInitialGlobals
check(pregraphicsInitials == Dictionary(uniqueKeysWithValues:image.pregraphics.initialGlobals.map {(UInt32($0.key)!,$0.value)}),"prepared537070 matches original image")
check(textInitials == Dictionary(uniqueKeysWithValues:image.textInitialGlobals.map {(UInt32($0.key)!,$0.value)}),"prepared LCID matches unchanged original image")
check(Set(textStrings.keys) == ClawNativeApplicationStartup.Text.stringTokens,"exact eight original text tokens")
check(Set(discStrings.keys) == [0x525ec4,0x524f08],"explicit prepared disc source strings")
check(metadata.sha256 == image.sha256, "prepared original identity")
check(strings.merging(discStrings) {_,new in new}.merging(textStrings) {_,new in new} == Dictionary(uniqueKeysWithValues:image.strings.map {(UInt32($0.key)!,decodeHex($0.value))}),
      "prepared strings match fresh original execution catalog")
check(initials == Dictionary(uniqueKeysWithValues:image.initialGlobals.map {(UInt32($0.key)!,$0.value)}),
      "prepared globals match original before startup")
let temporary = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString+".json")
defer {try? FileManager.default.removeItem(at:temporary)}
let encoded = try JSONSerialization.jsonObject(with:Data(contentsOf:preparedFile)) as! [String:Any]
for mutation in 0..<4 {
    var changed = encoded
    if mutation == 0 {changed["schema"] = 2}
    if mutation == 1 {changed["sha256"] = String(repeating:"0",count:64)}
    if mutation == 2 {changed["strings"] = ["1":"00"]}
    if mutation == 3 {changed["strings"] = [String(UInt32(0x534938)):"01"]}
    try JSONSerialization.data(withJSONObject:changed).write(to:temporary)
    var rejected = false
    do {_ = try ClawNativeApplicationMetadata.load(from:temporary)} catch {rejected = true}
    check(rejected,"invalid prepared image data cannot be loaded")
}
var comparedEvents = 0, comparedImports = 0
var milestoneProfiles: [[String:Any]] = []
for reference in references {
    var clockIndex = 0
    let clocks: [UInt32] = [100,125,200,225,250]
    var owner: ClawNativeApplication? = try ClawNativeApplication(clock:{
        check(clockIndex < clocks.count,"clock budget");defer {clockIndex += 1};return clocks[clockIndex]
    },tickClock:{400},initialCursorCount:2)
    let heap = owner!.heap, app = owner!.applicationToken
    let outer = heap.allocate(bytes:0x254), window = heap.allocate(bytes:12)
    heap.lookup(outer,words:4)!.update(from:[0x50bbdc,window,app,0x77000001],count:4)
    heap.lookup(window,words:3)!.update(from:[0x50c37c,0x77000002,outer],count:3)
    let input = decodeHex(reference.commandHex)+[0]
    let command = heap.allocate(bytes:UInt32(input.count))
    input.withUnsafeBytes {UnsafeMutableRawPointer(heap.lookupBytes(command,count:UInt32(input.count))!).copyMemory(from:$0.baseAddress!,byteCount:$0.count)}
    typealias Value = ClawNativeApplicationStartup.Configuration.Value
    var values: [UInt32:Value] = [:]
    if let stored = reference.storedUserHex {values[0x525714] = Value(type:1,bytes:decodeHex(stored))}
    owner!.startupConfiguration = try .init(application:owner!,sha256:image.sha256,strings:strings,
        initialGlobals:initials,discStrings:discStrings,values:values)
    owner!.startupDisc = try .init(currentDirectory:reference.currentDirectory,
        opticalRoot:reference.present ? "D:\\" : nil,
        rezURL:reference.present ? URL(fileURLWithPath:CommandLine.arguments[3]) : nil,
        fecURL:reference.present ? URL(fileURLWithPath:CommandLine.arguments[4]) : nil)
    owner!.startupText = try .init(application:owner!,sha256:image.sha256,strings:textStrings,initialGlobals:textInitials,pregraphicsInitialGlobals:pregraphicsInitials)
    weak var pregraphics = owner!.startupText!.pregraphics
    weak var text = owner!.startupText
    weak var disc = owner!.startupDisc
    check(disc!.backingAvailable == reference.present,"verified original asset backing")
    weak var configuration = owner!.startupConfiguration
    let result = owner!.invoke(call(0x425730,app,[window,command]))
    check(!result.completed && result.eax == nil,"bounded missing dependency cannot report source success")
    check(result.canonicalFault?.diagnostic == .missingDependency && result.canonicalFault?.address == reference.stop.function,
          "exact first missing source dependency")
    let config = heap.lookup(app+0x38,words:1)!.pointee
    func normalized(_ original: UInt32) -> UInt32 {
        if original == reference.app {return app}
        if original == reference.outer {return outer}
        if original == reference.window {return window}
        if reference.config != 0 && original >= reference.config && original < reference.config+540 {
            return config+(original-reference.config)
        }
        return original
    }
    check(clockIndex == 5 && owner!.clockReads == 5,"continuous source clocks")
    check(words(heap,app,77) == reference.applicationWords.map(normalized),"all application bytes at first missing call")
    check(words(heap,0x541328,5) == reference.clockWords,"clock aliases")
    check(owner!.sourceAllocations == [config:540],"source allocation ownership")
    if let expected = reference.configBytes {check(bytes(heap,config,540) == decodeHex(expected),"real configuration bytes")}
    for (address, expected) in reference.globals {check(heap.lookup(UInt32(address)!,words:1)!.pointee == expected,"original global initials and read results")}
    check(configuration!.metadataIntact(),"immutable original catalog")
    let nativeEvents = owner!.startup!.events
    check(nativeEvents.count == reference.events.count,"event count")
    for (native,original) in zip(nativeEvents,reference.events) {
        check(native.function == original.function && native.receiver == normalized(original.receiver),"call identity")
        if native.function == 0x4b5e90 {
            check(original.stackPointer == UInt32(CLAW_STACK_TOP)-0x508
                  && original.arguments == [0x525714,UInt32(CLAW_STACK_TOP)-0x4b0,UInt32(CLAW_STACK_TOP)-0x4c4,0],"original rich pointer identities")
            check(native.localMask == 6 && native.bufferBytes == [32,4] && native.bufferPresent == [true,true],"bounded rich mapping")
        } else if native.function == 0x4f21e0 || native.function == 0x4a3990 {
            let upper = native.function == 0x4f21e0
            check(original.stackPointer == UInt32(CLAW_STACK_TOP)-(upper ? 0x4fc : 0x500),"real text entry frame")
            check([UInt32(CLAW_STACK_TOP)-0x42c,UInt32(CLAW_STACK_TOP)-0x138].contains(original.arguments[0]),"real borrowed source alias")
            check(native.localMask == 1 && native.bufferBytes == [300] && native.bufferPresent == [true]
                  && native.arguments[0] == 0,"full rich buffer transport")
            if !upper {check(native.arguments[1] == original.arguments[1],"original immutable search needle")}
        } else if native.function == 0x5028ec {
            check(native.localMask == 4 && native.bufferBytes == [256] && native.bufferPresent == [true],"whole declared rich MFC view retained")
            check(native.arguments == [original.arguments[0],0,0,1] && native.result == nil,"MFC halt has no invented return")
            check(pregraphics!.sourceArguments == original.arguments && pregraphics!.haltFrame == original.stackPointer,"exact genuine MFC source arguments and entry frame")
        } else {check(native.arguments == original.arguments.map(normalized),"full source arguments")}
        if native.function == 0x4a3990 {
            let pointer = original.result!
            let transport = pointer == 0 ? 0 : pointer-original.arguments[0]+1
            check(native.result == transport,"legacy local search offset plus one transport")
        } else {check(native.result == original.result.map(normalized),"source EAX including string pointer")}
        check(native.applicationWords == original.applicationWords.map(normalized),"live application callback snapshot")
        check(native.clockWords == original.clockWords,"live clock callback snapshot")
        comparedEvents += 1
    }
    let nativeImports = configuration!.imports
    check(nativeImports.count == reference.imports.count,"only reached physical imports")
    for (native,original) in zip(nativeImports,reference.imports) {
        check(native.function == original.function && native.stackPointer == original.stackPointer,"exact physical import frame")
        check(native.arguments == original.arguments.map(normalized),"exact original pointer aliases and all physical arguments")
        check(native.name == decodeHex(original.nameHex ?? original.subkeyHex!),"source string bytes")
        check(native.capacity == original.capacity && native.result == original.result,"query capacity and result")
        if let handle = original.handle {
            check(native.outputWords == [handle,original.disposition!],"create writes handle and exact disposition through distinct aliases")
        }
        if original.function == 0x54682c && original.result != 2 {
            check(native.outputWords == [original.outputType!,original.outputSize!],"query type and byte count outputs")
            check(native.outputBytes == decodeHex(original.outputBytes!),"bounded OS query writes before original fallback")
        }
        comparedImports += 1
    }
    if nativeEvents.contains(where:{$0.function == 0x4b5e90}) {
        let initialUser = (reference.storedUserHex.map(decodeHex) ?? [0])
        check(owner!.startup!.configurationUserBytes == initialUser+Array(repeating:0,count:32-initialUser.count),"bounded initial registry User copyback")
        check(owner!.startup!.configurationUserLength == reference.userLength,"source length semantics")
    }
    check(reference.nested[0].function == 0x4b5e90 && reference.nested[0].stackPointer == UInt32(CLAW_STACK_TOP)-0x640
          && reference.nested[0].arguments == [0x525ec4,UInt32(CLAW_STACK_TOP)-0x618,UInt32(CLAW_STACK_TOP)-0x61c,0],
          "real nested getter and exact source local aliases")
    check(disc!.imports.count == reference.physical.count,"physical disc OS call count")
    for (native,original) in zip(disc!.imports,reference.physical) {
        check(native.function == original.function && native.stackPointer == original.stackPointer && native.arguments == original.arguments,
              "disc physical complete ABI frame")
        check(native.result == original.result,"OS result follows logical roots backed by real verified assets")
        if let hex = original.rootHex {check(native.root == decodeHex(hex),"source root after truncation")}
        if let hex = original.outputBytes {check(native.outputBytes == decodeHex(hex),"bounded logical directory write")}
    }
    check(disc!.missingCall == nil,"disc branch has no formatter dependency")
    let sourceText = reference.events.filter {$0.function == 0x4f21e0 || $0.function == 0x4a3990}
    check(text!.calls.count == sourceText.count,"every actual text call captured")
    for (native,original) in zip(text!.calls,sourceText) {
        check(native.function == original.function && native.stackPointer == original.stackPointer
              && native.arguments == original.arguments,"exact source text frame and pointers")
        check(native.sourceEAX == original.result,"full actual source EAX before legacy transport")
        let before = decodeHex(original.beforeBytes!), after = decodeHex(original.afterBytes!)
        let isUser = original.arguments[0] == UInt32(CLAW_STACK_TOP)-0x138
        let initialized = isUser ? input.count : 300
        check(Array(native.beforeBytes.prefix(initialized)) == Array(before.prefix(initialized))
              && Array(native.afterBytes.prefix(initialized)) == Array(after.prefix(initialized)),"every initialized byte; command full300 equality")
        check(native.afterBytes.dropFirst(initialized) == native.beforeBytes.dropFirst(initialized)
              && after.dropFirst(initialized) == before.dropFirst(initialized),"each raw tail independently unchanged")
        let reads = original.reads!
        check(!reads.isEmpty && reads.allSatisfy {$0.offset >= 0 && $0.offset+$0.count <= initialized},"observed original text accesses confined to compared initialized bytes")
        if isUser {
            check(before.dropFirst(initialized) == decodeHex(reference.initialUserCommandBytes).dropFirst(initialized),"original uninitialized tail preserves prior-frame residue")
            check(native.beforeBytes.dropFirst(initialized).allSatisfy {$0 == 0},"native uninitialized tail preserves its own zero scratch canaries")
            print("EVIDENCE USER original search read offsets0...\(reads.map {$0.offset+$0.count-1}.max()!); compared initialized span\(initialized); full raw300 retained; prior-frame residue differs")
        }
    }
    check(text!.commandBytes == decodeHex(reference.commandBytes),"all command local bytes")
    let usedUser = sourceText.contains {$0.arguments[0] == UInt32(CLAW_STACK_TOP)-0x138}
    let userInitialized = usedUser ? input.count : 0
    let sourceUserCommand = Array(decodeHex(reference.pregraphics.beforeBytes).suffix(300))
    let nativeUserBefore = Array(pregraphics!.beforeBytes.suffix(300))
    check(Array(nativeUserBefore.prefix(userInitialized)) == Array(sourceUserCommand.prefix(userInitialized)),"every initialized USER command byte after delimiter edits")
    check(nativeUserBefore.dropFirst(userInitialized).allSatisfy {$0 == 0},"native untouched USER tail canaries")
    check(sourceUserCommand.dropFirst(userInitialized) == decodeHex(reference.initialUserCommandBytes).dropFirst(userInitialized),"original untouched USER tail residue")
    check(text!.userBytes == decodeHex(reference.userBytes),"all final User bytes including source copyback")
    check(pregraphics!.hookFrame == reference.pregraphics.hookFrame && pregraphics!.hookFrame == UInt32(CLAW_STACK_TOP)-0x4f8,"exact hook source frame")
    check(pregraphics!.hookEAX == 0,"raw canonical hook EAX is zero")
    check(pregraphics!.hookReceiverBefore == pregraphics!.hookReceiverAfter
          && reference.pregraphics.hookReceiverBefore == reference.pregraphics.hookReceiverAfter,"each complete receiver unchanged by real hook")
    let originalBefore = decodeHex(reference.pregraphics.beforeBytes), originalAfter = decodeHex(reference.pregraphics.afterBytes)
    check(pregraphics!.beforeBytes.count == 556 && pregraphics!.afterBytes.count == 556,"bounded contiguous source backing includes USER")
    check(pregraphics!.commandToken == command && pregraphics!.commandBytes == input,"original nonnull CLI identity and full bytes retained")
    check(Array(pregraphics!.afterBytes.prefix(input.count)) == input
          && Array(originalAfter.prefix(input.count)) == input,"full original CLI including NUL copied without uppercase or truncation")
    check(pregraphics!.afterBytes.dropFirst(input.count) == pregraphics!.beforeBytes.dropFirst(input.count)
          && originalAfter.dropFirst(input.count) == originalBefore.dropFirst(input.count),"each uninitialized destination tail independently untouched")
    let overlap = max(0,input.count-256)
    check(Array(pregraphics!.afterBytes[256..<256+overlap]) == Array(input.suffix(overlap)),"exact CLI write overlaps adjacent USER local")
    check(text!.userCommandBytes == Array(pregraphics!.afterBytes.suffix(300)),"final USER snapshot shares contiguous CLI backing")
    check(Array(text!.userCommandBytes!.prefix(max(userInitialized,overlap))) == Array(decodeHex(reference.userCommandBytes).prefix(max(userInitialized,overlap))),"every initialized final USER byte including overlap")
    if reference.name == "boundaries" {check(input.count == 300 && overlap == 44,"299-byte CLI overwrites exactly44 USER bytes")}
    check(pregraphics!.initialGlobal == pregraphicsInitials[0x537070]
          && heap.lookup(0x537070,words:1)!.pointee == reference.pregraphics.globals[String(UInt32(0x537070))],"real prepared global initial and subsequent source instance write")

    check(text!.metadataIntact() && heap.lookup(0x540e88,words:1)!.pointee == 0,"original catalog and unchanged default locale")
    check(!owner!.startup!.active && owner!.startup!.fault == 1,"source transport halt retained")
    check(heap.lookup(owner!.startup!.automaticToken,words:1) == nil,"scratch lifetime")
    for offset: UInt32 in [0x2c,0x30,0x34] {check(heap.lookup(app+offset,words:1)!.pointee == 0,"no premature state/scene/archive")}
    let eventsBefore = owner!.startup!.events
    check(owner!.invoke(call(0x425730,app,[window,command])).canonicalFault == result.canonicalFault
          && owner!.startup!.events == eventsBefore,"sticky fault prevents resumed partial startup")
    // Emit observed values only after this profile's original comparisons.
    // These are headless startup-prefix observations, never UI/gameplay events.
    let observedStop = result.canonicalFault!
    milestoneProfiles.append([
        "name":reference.name, "completed":result.completed,
        "stop":["address":observedStop.address,"code":observedStop.code,
                "diagnostic":String(describing:observedStop.diagnostic)],
        "callbacks":nativeEvents.count, "registry_callbacks":nativeImports.count,
        "state_pointers":[UInt32(0x2c),0x30,0x34].map { heap.lookup(app+$0,words:1)!.pointee }
    ])
    owner = nil
    check(configuration == nil && disc == nil && text == nil && pregraphics == nil && heap.lookup(app,words:1) == nil,"configuration lifetime without owner cycle")
    for token in Array(strings.keys)+Array(discStrings.keys)+Array(textStrings.keys)+[0x540e88,0x537070] {check(heap.lookup(token,words:1) == nil,"catalog ownership released")}
    if config != 0 {check(heap.lookup(config,words:1) == nil,"source config ownership released")}
    heap.free(outer);heap.free(window);heap.free(command)
    print("PASS \(reference.name): continuous original constructor/configuration/disc/text; all callbacks, raw pointer EAX, borrowed bytes canonical zero hook; full original CLI copy and genuine5028ec halt")
}
print("PASS \(comparedEvents) source callback snapshots; \(comparedImports) exact registry frames/arguments; bounded User copyback; sticky faults and lifetimes")
// An observed nonzero LCID must fault before the first uppercase write and
// retain the changed raw global. This is an unsupported-state control, not an
// invented alternate successful original locale execution.
do {
    var clockIndex = 0
    let clocks: [UInt32] = [100,125,200,225,250]
    let owner = try ClawNativeApplication(clock:{defer {clockIndex += 1};return clocks[clockIndex]},tickClock:{400},initialCursorCount:2)
    let heap = owner.heap, app = owner.applicationToken
    let outer = heap.allocate(bytes:0x254), window = heap.allocate(bytes:12)
    heap.lookup(outer,words:4)!.update(from:[0x50bbdc,window,app,0x77000001],count:4)
    heap.lookup(window,words:3)!.update(from:[0x50c37c,0x77000002,outer],count:3)
    let command = try owner.makeCString("aZz")
    owner.startupConfiguration = try .init(application:owner,sha256:image.sha256,strings:strings,initialGlobals:initials,discStrings:discStrings)
    owner.startupDisc = try .init(currentDirectory:"D:\\CLAW",opticalRoot:"D:\\",rezURL:URL(fileURLWithPath:CommandLine.arguments[3]),fecURL:URL(fileURLWithPath:CommandLine.arguments[4]))
    owner.startupText = try .init(application:owner,sha256:image.sha256,strings:textStrings,initialGlobals:textInitials)
    heap.lookup(0x540e88,words:1)!.pointee = 0x409
    let result = owner.invoke(call(0x425730,app,[window,command]))
    check(result.canonicalFault?.diagnostic == .unsupportedABI && result.canonicalFault?.address == 0x4f21e0,"unsupported locale first fault")
    check(owner.startupText!.calls.count == 1,"no search after unsupported locale")
    let observed = owner.startupText!.calls[0]
    check(observed.beforeBytes == observed.afterBytes && observed.sourceEAX == nil && observed.transportResult == nil,"locale rejection performs no uppercase or fake return")
    check(heap.lookup(0x540e88,words:1)!.pointee == 0x409,"nonzero LCID never reset")
    check(owner.invoke(call(0x425730,app,[window,command])).canonicalFault == result.canonicalFault && owner.startupText!.calls.count == 1,"unsupported locale sticky")
    heap.free(outer);heap.free(window)
}
print("PASS nonzero raw LCID rejects before text writes or continuation; sticky unsupported fault")
print("LIMIT default C-locale legacy proof only; uppercase is NOT canonically admitted; whole MFC5028ec remains missing; uninitialized USER tail return-PC residue is not modeled; no menu/device acceptance")
let milestoneEvidence: [String:Any] = [
    "schema":1, "command":"native-application-pregraphics", "status":"pass",
    "scope":"startup-prefix", "profiles":milestoneProfiles,
    "source_callbacks":comparedEvents, "registry_callbacks":comparedImports,
    "reference_sha256":SHA256.hash(data:referenceData).map { String(format:"%02x",$0) }.joined(),
    "limits":["Prepared outer/window records; not cold startup or app UI election",
              "Default C-locale legacy comparison; uppercase is not canonically admitted",
              "Uninitialized USER tail return-PC residue is not modeled",
              "No menu, gameplay, results or device acceptance"]
]
print(String(data:try JSONSerialization.data(withJSONObject:milestoneEvidence,options:[.sortedKeys]),encoding:.utf8)!)
