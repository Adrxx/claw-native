import Foundation

struct ReferenceEvent: Decodable, Sendable {
    let function: UInt32, receiver: UInt32, stackPointer: UInt32
    let arguments: [UInt32], result: UInt32?
    let applicationWords: [UInt32], clockWords: [UInt32]
}
struct ReferenceImport: Decodable, Sendable {
    let function: UInt32, stackPointer: UInt32, result: UInt32
    let arguments: [UInt32]
    let subkeyHex: String?, nameHex: String?, capacity: UInt32?
    let handle: UInt32?, disposition: UInt32?, outputType: UInt32?, outputSize: UInt32?, outputBytes: String?
}
struct Reference: Decodable, Sendable {
    let name: String, sha256: String, fault: String?
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

// Only these owned immutable values leave the fixed native OS thread.
struct Snapshot: Sendable, Equatable {
    let profile: String
    let identity: Lane.Identity
    let applicationWords: [UInt32], clockWords: [UInt32], configurationBytes: [UInt8]
    let globals: [UInt32: UInt32]
    let events: Int, imports: Int
    let completed: Bool, eax: UInt32?, halt: UInt32
    let tlsToken: UInt32, seed: UInt32
}
struct Teardown: Sendable {
    let identity: Lane.Identity
    let applicationReleased: Bool, randomReleased: Bool, configurationReleased: Bool, tlsReleased: Bool
}
typealias Lane = ClawNativeExecutionLane<ThreadState>
final class ClockFixture {
    var index = 0
    let context: Lane.Context
    init(_ context: Lane.Context) { self.context = context }
    func read() -> UInt32 {
        context.assertCurrentThread()
        let values: [UInt32] = [100,125,200,225,250]
        check(index < values.count,"clock budget")
        defer { index += 1 }; return values[index]
    }
}
// This wrapper and its application, heap, RNG and Context are not Sendable.
final class ThreadState {
    let context: Lane.Context
    let ui: ServiceOwner
    let clock: ClockFixture
    let reference: Reference
    let metadata: ClawNativeApplicationMetadata
    var owner: ClawNativeApplication?
    var outer: UInt32 = 0, window: UInt32 = 0
    var tlsToken: UInt32 = 0
    var expectedSeed: UInt32 = 0
    var comparedEvents = 0, comparedImports = 0
    init(_ context: Lane.Context, _ ui: ServiceOwner, _ reference: Reference,
         _ metadata: ClawNativeApplicationMetadata) throws {
        context.assertCurrentThread()
        self.context = context; self.ui = ui; self.reference = reference; self.metadata = metadata
        let clock = ClockFixture(context); self.clock = clock
        owner = try ClawNativeApplication(clock: { clock.read() },
            sourceAllocationByteLimit: reference.name == "allocation-refused" ? 0 : nil,
            tickClock: { context.assertCurrentThread(); return 400 }, initialCursorCount: 2)
        check(owner!.constructed && owner!.operationCalls[0x4254a0] == 1,"one real constructor")
    }
    func executeAndCompare() throws -> Snapshot {
        context.assertCurrentThread()
        check(owner!.startup == nil,"startup executes once")
    let heap = owner!.heap, app = owner!.applicationToken
    outer = heap.allocate(bytes:0x254); window = heap.allocate(bytes:12)
    heap.lookup(outer,words:4)!.update(from:[0x50bbdc,window,app,0x77000001],count:4)
    heap.lookup(window,words:3)!.update(from:[0x50c37c,0x77000002,outer],count:3)
    let command = try owner!.makeCString("")
    typealias Value = ClawNativeApplicationStartup.Configuration.Value
    func dword(_ value: UInt32) -> Value {
        var word = value.littleEndian
        return Value(type:4,bytes:withUnsafeBytes(of:&word) {Array($0)})
    }
    var values: [UInt32:Value] = [:]
    if reference.name == "stored" {
        values = [0x5258a8:dword(27),0x52589c:dword(8),0x5257fc:dword(1),0x525784:dword(91),
                  0x525714:Value(type:1,bytes:Array("Ada".utf8)+[0])]
    }
    if reference.name == "wrong-type" {values = [0x5258a8:Value(type:1,bytes:Array("bad".utf8)+[0]),0x525714:dword(88)]}
    if reference.name == "short-user" {values = [0x525714:Value(type:1,bytes:[UInt8](repeating:90,count:31))]}
    owner!.startupConfiguration = try .init(application:owner!,sha256:metadata.sha256,strings:metadata.strings,
        initialGlobals:metadata.initialGlobals,values:values,failCreateAt:reference.name == "create-refused" ? 1 : nil,
        existingKeys:reference.name == "stored")
    weak let configuration = owner!.startupConfiguration
    let result = owner!.invoke(call(0x425730,app,[window,command]))
    check(!result.completed && result.eax == nil,"bounded missing dependency cannot report source success")
    let refused = reference.name == "allocation-refused"
    if refused {
        check(reference.fault != nil && result.canonicalFault?.diagnostic == .invalidMemorySpan
              && result.canonicalFault?.address == 0x1c,"original null receiver prefix remains memory fault")
    } else {
        let next: UInt32 = reference.name == "create-refused" ? 0x429e10 : 0x42b020
        check(result.canonicalFault?.diagnostic == .missingDependency && result.canonicalFault?.address == next,"exact next source dependency")
    }
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
    check(clock.index == 5 && owner!.clockReads == 5,"continuous source clocks")
    check(words(heap,app,77) == reference.applicationWords.map(normalized),"all application bytes at first missing call")
    check(words(heap,0x541328,5) == reference.clockWords,"clock aliases")
    check(owner!.sourceAllocations == (refused ? [:] : [config:540]),"source allocation ownership")
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
    check(!owner!.startup!.active && owner!.startup!.fault == 1,"source transport halt retained")
    check(heap.lookup(owner!.startup!.automaticToken,words:1) == nil,"scratch lifetime")
    for offset: UInt32 in [0x2c,0x30,0x34] {check(heap.lookup(app+offset,words:1)!.pointee == 0,"no premature state/scene/archive")}
    let eventsBefore = owner!.startup!.events
    check(owner!.invoke(call(0x425730,app,[window,command])).canonicalFault == result.canonicalFault
          && owner!.startup!.events == eventsBefore,"sticky fault prevents resumed partial startup")

        check(owner!.operationCalls[0x4254a0] == 1 && owner!.operationCalls[0x425730] == 1,
              "constructor and startup are once only even after sticky retry")
        let random = owner!.startup!.random!
        tlsToken = random.threadToken
        check(random.initialized && random.fault == 0 && random.unresolved.isEmpty,"real native CRT")
        check(heap.lookup(tlsToken,words:1)!.pointee == context.identity.mach,"TLS owner identity")
        expectedSeed = reference.events.first { $0.function == 0x4a3040 }!.arguments[0]
        check(random.seedPointer!.pointee == expectedSeed && random.calls[0x4a3040] == 1,"actual original source srand seed")
        return Snapshot(profile:reference.name,identity:context.identity,
            applicationWords:words(heap,app,77),clockWords:words(heap,0x541328,5),
            configurationBytes:config == 0 ? [] : bytes(heap,config,540),
            globals:Dictionary(uniqueKeysWithValues:reference.globals.keys.map {
                let token = UInt32($0)!; return (token,heap.lookup(token,words:1)!.pointee)
            }),events:comparedEvents,imports:comparedImports,
            completed:result.completed,eax:result.eax,halt:result.canonicalFault!.address,
            tlsToken:tlsToken,seed:random.seedPointer!.pointee)
    }
    func draw() -> UInt32 {
        context.assertCurrentThread()
        let random = owner!.startup!.random!
        check(random.threadToken == tlsToken,"same TLS allocation across jobs and wait")
        expectedSeed = expectedSeed &* 214013 &+ 2531011
        let value = random.call(0x4a3050)
        check(value == (expectedSeed >> 16) & 0x7fff && random.seedPointer!.pointee == expectedSeed,"source RNG continuity")
        return value
    }
    func verifyRetained(_ snapshot: Snapshot) {
        context.assertCurrentThread()
        check(words(owner!.heap,owner!.applicationToken,77) == snapshot.applicationWords,"snapshot remains independently owned")
        check(owner!.canonicalHost.fault!.address == snapshot.halt && owner!.fault != nil,"UI wait cannot clear source halt")
        check(owner!.operationCalls[0x4254a0] == 1 && owner!.operationCalls[0x425730] == 1,"UI wait cannot reenter source")
    }
    deinit {
        context.assertCurrentThread()
        let heap = owner!.heap, app = owner!.applicationToken
        let config = heap.lookup(app+0x38,words:1)!.pointee
        weak let application = owner
        weak let random = owner!.startup?.random
        weak let configuration = owner!.startupConfiguration
        check(random?.threadToken == tlsToken,"teardown runs on original TLS thread")
        owner = nil // Releases startup's real CRT before the retained heap goes away.
        let record = Teardown(identity:Lane.Identity.current,applicationReleased:application == nil,
            randomReleased:random == nil,configurationReleased:configuration == nil,
            tlsReleased:heap.lookup(tlsToken,words:1) == nil)
        check(record.applicationReleased && record.randomReleased && record.configurationReleased && record.tlsReleased,"same-thread application and CRT release")
        check(heap.lookup(app,words:1) == nil,"application allocation released")
        for token in metadata.strings.keys { check(heap.lookupBytes(token,count:1) == nil,"metadata released") }
        if config != 0 { check(heap.lookup(config,words:1) == nil,"source allocation released") }
        heap.free(outer); heap.free(window)
        let ui = ui
        Task { @MainActor in ui.teardowns.append(record) }
    }
}

@MainActor final class ServiceOwner {
    var pending: [Lane.RequestID: CheckedContinuation<Lane.Message, any Error>] = [:]
    var requests: [Lane.Request] = []
    var cancellations: [Lane.RequestID] = []
    var teardowns: [Teardown] = []
    var queuedCompleted = false
    func service(_ request: Lane.Request) async throws -> Lane.Message {
        requests.append(request)
        return try await withCheckedThrowingContinuation { pending[request.id] = $0 }
    }
    func cancel(_ id: Lane.RequestID) async {
        cancellations.append(id)
        pending.removeValue(forKey:id)?.resume(throwing:CancellationError())
    }
    func reply() {
        let request = requests.last!
        pending.removeValue(forKey:request.id)!.resume(returning:request.message)
    }
}
@MainActor final class Controller {
    let execution: Lane
    nonisolated let stopHandle: Lane.StopHandle
    init(_ execution: Lane) { self.execution = execution; stopHandle = execution.stopHandle }
    deinit { stopHandle.stop() }
}
@main struct Tests {
    @MainActor static func until(_ predicate: () -> Bool) async throws {
        for _ in 0..<5000 {
            if predicate() { return }
            try await Task.sleep(nanoseconds:1_000_000)
        }
        fatalError("timed out")
    }
    @MainActor static func run(_ reference: Reference, _ metadata: ClawNativeApplicationMetadata,
                               cancel: Bool) async throws -> Snapshot {
        let ui = ServiceOwner()
        let lane = Lane(service: { try await ui.service($0) }, cancelService: { await ui.cancel($0) },
                        makeState: { try ThreadState($0,ui,reference,metadata) })
        var controller: Controller? = Controller(lane)
        let handle = controller!.stopHandle
        let identity = try await lane.ready()
        check(identity != Lane.Identity.current,"application is off MainActor OS thread")
        let snapshot = try await lane.perform { state, context in
            check(context.identity == identity,"constructor and startup same OS thread")
            return try state.executeAndCompare()
        }
        // Explicitly synthetic UI RPC AFTER the genuine source halt. This does
        // not implement a source window, dialog, movie or bootstrap callback.
        let parked = Task {
            try await lane.perform { state, context in
                _ = state.draw()
                state.verifyRetained(snapshot)
                let message = Lane.Message(operation:0xf001,bytes:snapshot.configurationBytes,
                                           words:snapshot.applicationWords)
                do {
                    let reply = try context.request(message)
                    check(!cancel && reply == message,"copied synthetic UI reply")
                    _ = state.draw()
                    state.verifyRetained(snapshot)
                    return true
                } catch {
                    check(cancel && error as? Lane.Failure == .stopped,"stop wakes parked wrapper")
                    state.verifyRetained(snapshot)
                    return false
                }
            }
        }
        try await until { ui.pending.count == 1 }
        let queued = Task {
            let result = try await lane.perform { state, _ in state.verifyRetained(snapshot); return state.draw() }
            ui.queuedCompleted = true
            return result
        }
        for _ in 0..<8 {
            try await Task.sleep(nanoseconds:1_000_000)
            check(!ui.queuedCompleted && ui.teardowns.isEmpty && ui.pending.count == 1,
                  "MainActor responsive while root remains parked and queued root cannot run")
        }
        check(ui.requests[0].message.words == snapshot.applicationWords,"UI receives owned source snapshot")
        if cancel {
            controller = nil // in-flight tasks retain lane; independent handle must stop it.
            let completed = try await parked.value; check(!completed,"park canceled")
            do { _ = try await queued.value; fatalError("queued root ran after stop") }
            catch { check(error as? Lane.Failure == .stopped,"queued root rejected") }
            await handle.shutdown()
            check(ui.cancellations.count == 1 && !ui.queuedCompleted,"controller cancellation")
        } else {
            ui.reply()
            let completed = try await parked.value; check(completed,"park resumed")
            _ = try await queued.value
            check(ui.queuedCompleted,"queued root runs after callback return")
            controller = nil
            await handle.shutdown()
            check(ui.cancellations.isEmpty,"normal UI completion")
        }
        try await until { ui.teardowns.count == 1 }
        check(ui.teardowns[0].identity == identity && ui.pending.isEmpty,"observed exact teardown thread")
        check(snapshot.applicationWords.count == 77 && snapshot.eax == nil && !snapshot.completed,
              "copied snapshot survives complete source destruction and never reports fake EAX")
        return snapshot
    }
    @MainActor static func main() async throws {
        let references = try JSONDecoder().decode([Reference].self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
        let metadata = try ClawNativeApplicationMetadata.load(from:URL(fileURLWithPath:CommandLine.arguments[2]))
        check(references.count == 6,"six fresh original profiles")
        let image = references[0]
        check(metadata.sha256 == image.sha256,"pinned metadata identity")
        check(metadata.strings == Dictionary(uniqueKeysWithValues:image.strings.map {(UInt32($0.key)!,decodeHex($0.value))}),"fresh original strings")
        check(metadata.initialGlobals == Dictionary(uniqueKeysWithValues:image.initialGlobals.map {(UInt32($0.key)!,$0.value)}),"fresh original global initials")
        var events = 0, imports = 0
        for reference in references {
            let value = try await run(reference,metadata,cancel:false)
            events += value.events; imports += value.imports
            print("PASS \(reference.name): full application fixed-thread join, original comparison, copied UI wait, RNG and teardown")
        }
        _ = try await run(references[0],metadata,cancel:true)
        print("PASS \(events) original callback snapshots; \(imports) exact registry frames; controller-drop cancellation")
        print("LIMIT synthetic platform records, isolated registry, synthetic UI RPC; real 42b020/error/null halts; no playable/on-screen/AVPlayer/device/platform-window acceptance")
    }
}
