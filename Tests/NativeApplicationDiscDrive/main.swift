import Foundation

struct ReferenceEvent: Decodable {
    let function: UInt32, receiver: UInt32, stackPointer: UInt32
    let arguments: [UInt32], result: UInt32?
    let applicationWords: [UInt32], clockWords: [UInt32]
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
struct Reference: Decodable {
    let name: String, sha256: String, fault: String?
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
let references = try JSONDecoder().decode([Reference].self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
check(references.count == 5,"five original disc profiles")
let image = references[0]
let preparedFile = URL(fileURLWithPath:CommandLine.arguments[2])
let metadata = try ClawNativeApplicationMetadata.load(from:preparedFile)
let strings = metadata.strings, initials = metadata.initialGlobals, discStrings = metadata.discStrings
check(Set(discStrings.keys) == [0x525ec4,0x524f08],"explicit prepared disc source strings")
check(metadata.sha256 == image.sha256, "prepared original identity")
check(strings.merging(discStrings) {_,new in new} == Dictionary(uniqueKeysWithValues:image.strings.map {(UInt32($0.key)!,decodeHex($0.value))}),
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
    let command = try owner!.makeCString("")
    typealias Value = ClawNativeApplicationStartup.Configuration.Value
    var values: [UInt32:Value] = [:]
    if reference.name == "configured-drive" || reference.name == "wrong-disc-type" {
        values[0x525ec4] = Value(type:reference.name == "configured-drive" ? 1 : 4,bytes:[68,58,92,0])
    }
    owner!.startupConfiguration = try .init(application:owner!,sha256:image.sha256,strings:strings,
        initialGlobals:initials,discStrings:discStrings,values:values)
    owner!.startupDisc = try .init(currentDirectory:reference.currentDirectory,
        opticalRoot:reference.present ? "D:\\" : nil,
        rezURL:reference.present ? URL(fileURLWithPath:CommandLine.arguments[3]) : nil,
        fecURL:reference.present ? URL(fileURLWithPath:CommandLine.arguments[4]) : nil)
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
        } else if native.function == 0x4f21e0 {
            check(original.stackPointer == UInt32(CLAW_STACK_TOP)-0x4fc && original.arguments == [UInt32(CLAW_STACK_TOP)-0x42c],
                  "original next source call uses startup command local")
            check(native.localMask == 1 && native.bufferBytes == [300] && native.bufferPresent == [true] && native.arguments == [0],
                  "next unknown rich source call remains bounded and visible")
        } else {check(native.arguments == original.arguments.map(normalized),"full source arguments")}
        check(native.result == original.result.map(normalized),"source EAX including string pointer")
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
        check(owner!.startup!.configurationUserBytes == decodeHex(reference.userBytes),"bounded User bytes including unchanged tail")
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
    if reference.stop.function == 0x4a3920 {
        check(disc!.missingCall?.function == reference.stop.function && disc!.missingCall?.receiver == 0
              && disc!.missingCall?.stackPointer == reference.stop.stackPointer && disc!.missingCall?.arguments == reference.stop.arguments,
              "genuine missing sprintf receives full exact source frame without formatter fixture")
    } else {check(disc!.missingCall == nil,"completed disc branch does not request formatter")}
    check(!owner!.startup!.active && owner!.startup!.fault == 1,"source transport halt retained")
    check(heap.lookup(owner!.startup!.automaticToken,words:1) == nil,"scratch lifetime")
    for offset: UInt32 in [0x2c,0x30,0x34] {check(heap.lookup(app+offset,words:1)!.pointee == 0,"no premature state/scene/archive")}
    let eventsBefore = owner!.startup!.events
    check(owner!.invoke(call(0x425730,app,[window,command])).canonicalFault == result.canonicalFault
          && owner!.startup!.events == eventsBefore,"sticky fault prevents resumed partial startup")
    owner = nil
    check(configuration == nil && disc == nil && heap.lookup(app,words:1) == nil,"configuration lifetime without owner cycle")
    for token in Array(strings.keys)+Array(discStrings.keys) {check(heap.lookup(token,words:1) == nil,"catalog ownership released")}
    if config != 0 {check(heap.lookup(config,words:1) == nil,"source config ownership released")}
    heap.free(outer);heap.free(window)
    print("PASS \(reference.name): continuous constructor/startup/configuration/disc; exact callbacks, aliases, memory and next stop")
}
print("PASS \(comparedEvents) source callback snapshots; \(comparedImports) exact registry frames/arguments; bounded User copyback; sticky faults and lifetimes")
// Preparation is atomic: missing or changed source files cannot create an optical drive.
for variant in 0..<3 {
    var rejected = false
    do {
        _ = try ClawNativeApplicationStartup.Disc(currentDirectory:"D:\\CLAW",opticalRoot:"D:\\",
            rezURL:variant == 0 ? nil : URL(fileURLWithPath:variant == 1 ? "/nonexistent/claw-disc-drive-check" : CommandLine.arguments[4]),
            fecURL:URL(fileURLWithPath:CommandLine.arguments[4]))
    } catch {rejected = true}
    check(rejected,"missing pair, missing file and wrong source bytes reject optical preparation")
}
print("LIMIT isolated logical OS and synthetic window records; next4f21e0 and missing sprintf4a3920 remain halts; no menu/device acceptance")
