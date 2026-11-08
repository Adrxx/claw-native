import Foundation
import CryptoKit

// Synchronous service boundary for the recovered application startup. It owns
// no window, scene or configuration implementation. Unknown game calls halt.
final class ClawNativeApplicationStartup {
    struct Event: Equatable {
        let function: UInt32
        let receiver: UInt32
        let arguments: [UInt32]
        let localMask: UInt32
        let bufferBytes: [UInt32]
        let bufferPresent: [Bool]
        let applicationWords: [UInt32]
        let clockWords: [UInt32]
        let result: UInt32?
    }
    // Prepared original metadata and isolated OS registry state. No game call
    // is replaced by a lookup here: admitted configuration bodies own all
    // traversal, defaults, type checks and source record writes.
    final class Configuration {
        struct Value {
            let type: UInt32
            let bytes: [UInt8]
        }
        struct ImportEvent {
            let function: UInt32, stackPointer: UInt32
            let arguments: [UInt32]
            let name: [UInt8]
            let capacity: UInt32?
            let outputWords: [UInt32]
            let outputBytes: [UInt8]
            let result: UInt32
        }
        enum PreparationError: Error { case metadata, overlap }
        private let heap: ClawTokenHeap
        private let immutable: [UInt32: [UInt8]]
        private let values: [[UInt8]: Value]
        private let failCreateAt: Int?
        private let existingKeys: Bool
        private var handles: [UInt32: (UInt32, [UInt8])] = [:]
        private var createCount = 0
        private(set) var imports: [ImportEvent] = []
        private let ownedTokens: [UInt32]
        let discPrepared: Bool

        init(application: ClawNativeApplication, sha256: String,
             strings: [UInt32: [UInt8]], initialGlobals: [UInt32: UInt32],
             discStrings: [UInt32: [UInt8]] = [:],
             values: [UInt32: Value] = [:], failCreateAt: Int? = nil, existingKeys: Bool = false) throws {
            let keys: Set<UInt32> = [0x5258b8,0x524eec,0x5258d0,0x532474,0x534938,
                0x5258a8,0x52589c,0x525890,0x525880,0x525874,0x525860,0x525850,
                0x525840,0x52582c,0x525818,0x5257fc,0x5257ec,0x5257dc,0x5257c8,
                0x5257b4,0x525798,0x525784,0x525770,0x525758,0x525744,0x525730,
                0x52571c,0x525714,0x52570c,0x525704,0x5256fc,0x5256f4,0x5256e8,
                0x5256dc,0x5256d0,0x5256c0,0x5256b0]
            let globals: Set<UInt32> = [0x525510,0x525514,0x525518,0x537234,0x537238,
                0x53723c,0x537240,0x537244,0x537248,0x53724c,0x537250,0x537254,
                0x537258,0x52c6e4,0x52c6e8,0x52c6ec,0x527134,0x527130,0x527138]
            guard sha256 == "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263",
                  Set(strings.keys) == keys, Set(initialGlobals.keys) == globals,
                  (discStrings.isEmpty || Set(discStrings.keys) == [0x525ec4,0x524f08]),
                  values.keys.allSatisfy({keys.contains($0) || ($0 == 0x525ec4 && !discStrings.isEmpty)}),
                  failCreateAt == nil || (1...4).contains(failCreateAt!) else {throw PreparationError.metadata}
            discPrepared = !discStrings.isEmpty
            let strings = strings.merging(discStrings) {_,new in new}
            let heap = application.heap
            for (token, bytes) in strings {
                guard token & 3 == 0, !bytes.isEmpty, bytes.count <= 256,
                      bytes.last == 0, !bytes.dropLast().contains(0) else {throw PreparationError.metadata}
                guard !heap.overlaps(token,count:UInt32((bytes.count+3)/4)*4) else {throw PreparationError.overlap}
            }
            for token in initialGlobals.keys {
                guard !heap.overlaps(token,count:4) else {throw PreparationError.overlap}
            }
            // Validate all spans together before publishing any of them.
            let spans = (strings.map {($0.key,UInt32(($0.value.count+3)/4)*4)} + initialGlobals.map {($0.key,UInt32(4))})
                .sorted {$0.0 < $1.0}
            for pair in zip(spans,spans.dropFirst()) {
                guard UInt64(pair.0.0)+UInt64(pair.0.1) <= UInt64(pair.1.0) else {throw PreparationError.overlap}
            }
            for (token, bytes) in strings {
                let pointer = heap.storeBytes(token:token,count:UInt32(bytes.count))
                bytes.withUnsafeBytes {UnsafeMutableRawPointer(pointer).copyMemory(from:$0.baseAddress!,byteCount:$0.count)}
            }
            for (token,value) in initialGlobals {heap.store(token:token,words:1).pointee = value}
            self.heap = heap;immutable = strings
            self.values = Dictionary(uniqueKeysWithValues:values.map {(Array(strings[$0.key]!.dropLast()),$0.value)})
            self.failCreateAt = failCreateAt;self.existingKeys = existingKeys
            ownedTokens = spans.map {$0.0}
        }
        deinit {for token in ownedTokens {heap.free(token)}}

        func metadataIntact() -> Bool {
            immutable.allSatisfy {token, bytes in
                guard let pointer = heap.lookupBytes(token,count:UInt32(bytes.count)) else {return false}
                return Array(UnsafeBufferPointer(start:pointer,count:bytes.count)) == bytes
            }
        }
        func leaf(_ host: ClawNativeCanonicalHost, _ call: ClawCall) -> UInt32? {
            guard call.function == 0x546834 || call.function == 0x54682c else {return nil}
            let create = call.function == 0x546834
            guard call.argumentCount == (create ? 9 : 6), call.receiver == 0, call.receiver2 == 0,
                  call.x87ArgumentCount == 0,
                  (create ? [UInt32(CLAW_STACK_TOP)-0x564] : [UInt32(CLAW_STACK_TOP)-0x524,UInt32(CLAW_STACK_TOP)-0x534] + (discPrepared ? [UInt32(CLAW_STACK_TOP)-0x66c] : [])).contains(call.stackPointer),
                  metadataIntact() else {
                host.fail(UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return nil
            }
            let args = withUnsafeBytes(of:call.arguments) {Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
            func string(_ token: UInt32) -> [UInt8]? {
                var bytes: [UInt8] = []
                for offset: UInt32 in 0..<256 {
                    guard let p = host.bytes(token+offset,count:1) else {return nil}
                    if p.pointee == 0 {return bytes};bytes.append(p.pointee)
                }
                host.fail(UInt32(CLAW_FAULT_MEMORY),at:token,diagnostic:.invalidMemorySpan);return nil
            }
            func put(_ pointer: UnsafeMutablePointer<UInt8>, _ word: UInt32) {
                var value = word.littleEndian
                withUnsafeBytes(of:&value) {UnsafeMutableRawPointer(pointer).copyMemory(from:$0.baseAddress!,byteCount:4)}
            }
            if call.stackPointer == UInt32(CLAW_STACK_TOP)-0x66c {
                // Disc entry S=E-4f8; getter G=S-148. Its incoming third
                // argument G+c becomes type-out, not detached heap scratch.
                let s = UInt32(CLAW_STACK_TOP)-0x4f8
                guard !create, discPrepared, args[1] == 0x525ec4, args[3] == s-0x13c,
                      args[4] == s-0x120, args[5] == s-0x124 else {
                    host.fail(UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return nil
                }
            }
            guard let name = string(args[1]) else {return nil}
            let result: UInt32
            var capacity: UInt32?
            var outputWords: [UInt32] = [], outputBytes: [UInt8] = []
            if create {
                guard args[2] == 0, args[3] == 0x534938, args[4] == 0, args[5] == 0xf003f, args[6] == 0,
                      args[0] == 0x80000002 || handles[args[0]] != nil,
                      args[7] != args[8],
                      let output = host.bytes(args[7],count:4), let disposition = host.bytes(args[8],count:4) else {
                    host.fail(UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return nil
                }
                createCount += 1
                if failCreateAt == createCount {result = 5}
                else {
                    let existing = handles.first {$0.value.0 == args[0] && $0.value.1 == name}?.key
                    let handle = existing ?? (0x78000000 + UInt32(handles.count)*4)
                    handles[handle] = (args[0],name)
                    let dispositionValue: UInt32 = existing != nil || existingKeys ? 2 : 1
                    put(output,handle);put(disposition,dispositionValue);result = 0
                    outputWords = [handle,dispositionValue]
                }
            } else {
                guard handles[args[0]] != nil, args[2] == 0,
                      let type = host.bytes(args[3],count:4), let length = host.bytes(args[5],count:4) else {
                    host.fail(UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return nil
                }
                let count = UnsafeRawPointer(length).loadUnaligned(as:UInt32.self).littleEndian
                capacity = count
                guard let output = host.bytes(args[4],count:count) else {return nil}
                if let value = values[name] {
                    put(type,value.type);put(length,UInt32(value.bytes.count))
                    outputWords = [value.type,UInt32(value.bytes.count)]
                    if value.bytes.count > Int(count) {result = 234}
                    else {
                        value.bytes.withUnsafeBytes {bytes in
                            if !bytes.isEmpty {UnsafeMutableRawPointer(output).copyMemory(from:bytes.baseAddress!,byteCount:bytes.count)}
                        }
                        result = 0
                    }
                } else {result = 2}
                outputBytes = Array(UnsafeBufferPointer(start:output,count:Int(count)))
            }
            imports.append(ImportEvent(function:call.function,stackPointer:call.stackPointer,
                arguments:args,name:name,capacity:capacity,outputWords:outputWords,outputBytes:outputBytes,result:result))
            return result
        }
    }
    // Isolated DOS-like OS view backed by the owner's verified original disc.
    // Holding the open files keeps this preparation's backing lifetime explicit.
    // It neither selects a drive in application memory nor implements sprintf.
    final class Disc {
        enum PreparationError: Error { case path, assetPair, source }
        struct ImportEvent {
            let function: UInt32, stackPointer: UInt32
            let arguments: [UInt32], result: UInt32
            let root: [UInt8], outputBytes: [UInt8]
        }
        struct MissingCall {
            let function: UInt32, stackPointer: UInt32, receiver: UInt32
            let arguments: [UInt32]
        }
        let currentDirectory: [UInt8]
        let opticalRoot: [UInt8]?
        private let handles: [FileHandle]
        private static let sizes: [UInt64] = [118033115,365449951]
        private(set) var imports: [ImportEvent] = []
        private(set) var missingCall: MissingCall?

        init(currentDirectory: String, opticalRoot: String?, rezURL: URL?, fecURL: URL?) throws {
            func path(_ value: String, root: Bool) throws -> [UInt8] {
                let bytes = Array(value.utf8)
                guard bytes.count >= 3, bytes.count <= 254, bytes.allSatisfy({$0 >= 32 && $0 < 127}),
                      (65...90).contains(bytes[0]), bytes[1] == 58, bytes[2] == 92,
                      !root || bytes.count == 3 else {throw PreparationError.path}
                return bytes
            }
            self.currentDirectory = try path(currentDirectory,root:false)
            self.opticalRoot = try opticalRoot.map {try path($0,root:true)}
            guard (opticalRoot == nil && rezURL == nil && fecURL == nil) ||
                    (opticalRoot != nil && rezURL != nil && fecURL != nil) else {throw PreparationError.assetPair}
            var opened: [FileHandle] = []
            do {
                if let rezURL, let fecURL {
                    let digests = ["b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596",
                                   "9c87c82aaec3c73aa6c9eb268da9db8601aa10f75af35060bff4f1edcfbb80d8"]
                    for (index,url) in [rezURL,fecURL].enumerated() {
                        let file = try FileHandle(forReadingFrom:url);opened.append(file)
                        var digest = SHA256(), count: UInt64 = 0
                        while let data = try file.read(upToCount:1024*1024), !data.isEmpty {
                            count += UInt64(data.count);digest.update(data:data)
                        }
                        guard count == Self.sizes[index], digest.finalize().map({String(format:"%02x",$0)}).joined() == digests[index] else {
                            throw PreparationError.source
                        }
                        try file.seek(toOffset:0)
                    }
                }
            } catch {for file in opened {try? file.close()};throw error}
            handles = opened
        }
        deinit {for file in handles {try? file.close()}}
        var backingAvailable: Bool {
            guard handles.count == 2 else {return false}
            return zip(handles,Self.sizes).allSatisfy {file,size in (try? file.seekToEnd()) == size}
        }
        func observeMissing(_ call: ClawCall) {
            guard call.function == 0x4a3920 else {return}
            let args = withUnsafeBytes(of:call.arguments) {Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
            missingCall = MissingCall(function:call.function,stackPointer:call.stackPointer,receiver:call.receiver,arguments:args)
        }
        func leaf(_ host: ClawNativeCanonicalHost, _ call: ClawCall) -> UInt32? {
            guard call.function == 0x546a28 || call.function == 0x546a2c else {return nil}
            let directoryCall = call.function == 0x546a28
            let s = UInt32(CLAW_STACK_TOP)-0x4f8, directory = s-0x100
            guard call.receiver == 0, call.receiver2 == 0, call.x87ArgumentCount == 0,
                  call.argumentCount == (directoryCall ? 2 : 1),
                  call.stackPointer == s-(directoryCall ? 0x140 : 0x13c) else {
                host.fail(UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return nil
            }
            let args = withUnsafeBytes(of:call.arguments) {Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
            var output: [UInt8] = [], root: [UInt8] = []
            let result: UInt32
            if directoryCall {
                guard args == [255,directory], let pointer = host.bytes(directory,count:255) else {
                    host.fail(UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return nil
                }
                // Preparation bounds the current directory to this exact source capacity.
                output = currentDirectory+[0]
                output.withUnsafeBytes {UnsafeMutableRawPointer(pointer).copyMemory(from:$0.baseAddress!,byteCount:$0.count)}
                result = UInt32(currentDirectory.count)
            } else {
                guard args == [directory], let pointer = host.bytes(directory,count:4), pointer[3] == 0 else {
                    host.fail(UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return nil
                }
                root = Array(UnsafeBufferPointer(start:pointer,count:3))
                if root == opticalRoot && backingAvailable {result = 5}
                else if root == [67,58,92] {result = 3}
                else {result = 1}
            }
            imports.append(ImportEvent(function:call.function,stackPointer:call.stackPointer,arguments:args,
                result:result,root:root,outputBytes:output))
            return result
        }
    }
    // Opt-in state retained by the same text/application owner. Snapshots copy
    // values while the outer source stack is live; no borrowed pointer escapes.
    final class Pregraphics {
        fileprivate weak var application: ClawNativeApplication?
        private let heap: ClawTokenHeap
        fileprivate(set) var hookFrame: UInt32?
        fileprivate(set) var hookEAX: UInt32?
        fileprivate(set) var hookReceiverBefore: [UInt8] = []
        fileprivate(set) var hookReceiverAfter: [UInt8] = []
        fileprivate(set) var beforeBytes: [UInt8] = []
        fileprivate(set) var afterBytes: [UInt8] = []
        fileprivate(set) var sourceArguments: [UInt32] = []
        fileprivate(set) var haltFrame: UInt32?
        fileprivate(set) var commandToken: UInt32 = 0
        fileprivate(set) var commandBytes: [UInt8] = []
        fileprivate(set) var initialGlobal: UInt32
        fileprivate var projected = false
        fileprivate init(application: ClawNativeApplication, initialGlobals: [UInt32:UInt32]) throws {
            guard Set(initialGlobals.keys) == [0x537070] else {throw Text.PreparationError.metadata}
            guard !application.heap.overlaps(0x537070,count:4) else {throw Text.PreparationError.overlap}
            self.application = application;heap = application.heap;initialGlobal = initialGlobals[0x537070]!
            heap.store(token:0x537070,words:1).pointee = initialGlobal
        }
        deinit {heap.free(0x537070)}
    }

    // Bounded legacy C-locale support, explicitly separate from canonical
    // admission of the complete locale-dependent uppercase routine.
    final class Text {
        enum PreparationError: Error { case metadata, overlap }
        struct CallEvent {
            let function: UInt32, stackPointer: UInt32
            let arguments: [UInt32]
            let beforeBytes: [UInt8], afterBytes: [UInt8]
            let sourceEAX: UInt32?, transportResult: UInt32?
        }
        private let heap: ClawTokenHeap
        private let strings: [UInt32:[UInt8]]
        private let ownedTokens: [UInt32]
        let pregraphics: Pregraphics?
        private(set) var calls: [CallEvent] = []
        private(set) var commandBytes: [UInt8]?
        private(set) var userCommandBytes: [UInt8]?
        private(set) var userBytes: [UInt8]?
        static let stringTokens: Set<UInt32> = [0x5256a8,0x5256a0,0x525698,0x525690,
                                               0x52568c,0x525684,0x52567c,0x525674]

        init(application: ClawNativeApplication, sha256: String,
             strings: [UInt32:[UInt8]], initialGlobals: [UInt32:UInt32],
             pregraphicsInitialGlobals: [UInt32:UInt32]? = nil) throws {
            guard sha256 == "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263",
                  Set(strings.keys) == Self.stringTokens,
                  Set(initialGlobals.keys) == [0x540e88] else {throw PreparationError.metadata}
            let sizes: [UInt32:Int] = [0x5256a8:5,0x5256a0:7,0x525698:5,0x525690:8,
                                      0x52568c:4,0x525684:5,0x52567c:6,0x525674:6]
            let heap = application.heap
            for (token, bytes) in strings {
                guard bytes.count == sizes[token], bytes.last == 0,
                      !bytes.dropLast().contains(0) else {throw PreparationError.metadata}
                guard !heap.overlaps(token,count:UInt32((bytes.count+3)/4)*4) else {throw PreparationError.overlap}
            }
            guard !heap.overlaps(0x540e88,count:4) else {throw PreparationError.overlap}
            pregraphics = try pregraphicsInitialGlobals.map {try Pregraphics(application:application,initialGlobals:$0)}
            // The preparation exporter reads these bytes from the hash-checked
            // original image. No original payload is embedded here.
            for (token,bytes) in strings {
                let target = heap.storeBytes(token:token,count:UInt32(bytes.count))
                bytes.withUnsafeBytes {UnsafeMutableRawPointer(target).copyMemory(from:$0.baseAddress!,byteCount:$0.count)}
            }
            heap.store(token:0x540e88,words:1).pointee = initialGlobals[0x540e88]!
            self.heap = heap;self.strings = strings;ownedTokens = Array(strings.keys)+[0x540e88]
        }
        deinit {for token in ownedTokens {heap.free(token)}}
        func metadataIntact() -> Bool {
            strings.allSatisfy {token,bytes in
                guard let pointer = heap.lookupBytes(token,count:UInt32(bytes.count)) else {return false}
                return Array(UnsafeBufferPointer(start:pointer,count:bytes.count)) == bytes
            }
        }
        fileprivate func captureLocals(_ runtime: ClawNativeApplicationStartup) {
            func copy(_ offset: UInt32,_ count: Int) -> [UInt8]? {
                guard let pointer = runtime.application.heap.lookupBytes(runtime.automaticToken+offset,count:UInt32(count)) else {return nil}
                return Array(UnsafeBufferPointer(start:pointer,count:count))
            }
            commandBytes = copy(32,300);userCommandBytes = copy(332,300);userBytes = copy(0,32)
            if let pregraphics, pregraphics.afterBytes.count == 556 {
                userCommandBytes = Array(pregraphics.afterBytes.suffix(300))
            }
        }
        fileprivate func record(function: UInt32, frame: UInt32, arguments: [UInt32],
                                before: [UInt8], after: [UInt8], source: UInt32?, transport: UInt32?) {
            calls.append(CallEvent(function:function,stackPointer:frame,arguments:arguments,
                                   beforeBytes:before,afterBytes:after,sourceEAX:source,transportResult:transport))
        }
    }

    unowned let application: ClawNativeApplication
    private let readTick: () -> UInt32
    private(set) var cursorCount: Int32
    private(set) var fault: UInt32 = 0
    private(set) var events: [Event] = []
    private(set) var random: ClawNativeRandom?
    private(set) var automaticToken: UInt32 = 0
    private(set) var active = false
    private(set) var configurationUserBytes: [UInt8]?
    private(set) var configurationUserLength: UInt32?

    init(application: ClawNativeApplication, tickClock: @escaping () -> UInt32, initialCursorCount: Int32) {
        self.application = application;readTick = tickClock;cursorCount = initialCursorCount
    }

    private func fail(_ context: UnsafeMutablePointer<ClawApplicationStartupContext>,
                      _ code: UInt32, at address: UInt32,
                      diagnostic: ClawNativeCanonicalHost.Diagnostic) {
        application.canonicalHost.fail(code,at:address,diagnostic:diagnostic)
        if context.pointee.fault == 0 {context.pointee.fault = code == UInt32(CLAW_FAULT_ABI) ? 2 : 1}
        if fault == 0 {fault = context.pointee.fault}
    }

    func run(arguments: [UInt32]) -> UInt32? {
        guard !active, automaticToken == 0, arguments.count == 2 else {return nil}
        let heap = application.heap
        automaticToken = heap.allocate(bytes:UInt32(CLAW_APPLICATION_STARTUP_AUTOMATIC_BYTES))
        guard automaticToken != 0 else {
            application.canonicalHost.fail(UInt32(CLAW_FAULT_MEMORY),at:0,diagnostic:.invalidMemorySpan)
            fault = 1;return nil
        }
        active = true
        defer {application.startupText?.captureLocals(self);active = false;heap.free(automaticToken)}
        var context = ClawApplicationStartupContext(), result: UInt32 = 0
        // CRT/TLS readiness is a platform-runtime prerequisite, established
        // before entering425730. Source srand itself remains a separate call.
        random = ClawNativeRandom(heap:heap)
        guard let random, random.initialized, random.fault == 0 else {
            fail(&context,UInt32(CLAW_FAULT_HOST),at:0x4a7d40,diagnostic:.nativeFault);return nil
        }
        if let raw = heap.lookup(0x52edd8,words:1) {
            guard raw.pointee == random.globals.pointee.tlsIndex else {
                fail(&context,UInt32(CLAW_FAULT_MEMORY),at:0x52edd8,diagnostic:.invalidMemorySpan);return nil
            }
        } else {heap.store(token:0x52edd8,words:1).pointee = random.globals.pointee.tlsIndex}
        context.automaticToken = automaticToken
        context.maximumOperations = 100000
        context.pregraphicsSourceFrame = application.startupText?.pregraphics == nil ? 0 : 1
        // Exact word spans do not expose ClawTokenHeap's snapshot padding.
        let user = Unmanaged.passUnretained(self).toOpaque()
        context.scene = ClawSceneActorHost(context:user,lookup:{u,t,n in
            guard let u else {return nil}
            let runtime = Unmanaged<ClawNativeApplicationStartup>.fromOpaque(u).takeUnretainedValue()
            guard n <= UInt32.max / 4, t & 3 == 0,
                  runtime.application.bytes(t,count:n*4) != nil else {
                runtime.application.canonicalHost.fail(UInt32(CLAW_FAULT_MEMORY),at:t,diagnostic:.invalidMemorySpan)
                return nil
            }
            return runtime.application.heap.lookup(t,words:n)
        },allocate:nil,free:nil,call:nil,readClock:nil)
        context.byteContext = user
        context.bytes = {u,t,n in
            guard let u else {return nil}
            let runtime = Unmanaged<ClawNativeApplicationStartup>.fromOpaque(u).takeUnretainedValue()
            if let pregraphics = runtime.application.startupText?.pregraphics, pregraphics.projected,
               t >= runtime.automaticToken+632, t < runtime.automaticToken+932 {
                let offset = t-(runtime.automaticToken+632)
                guard UInt64(offset)+UInt64(n) <= 300 else {return nil}
                return runtime.application.canonicalHost.bytes(UInt32(CLAW_STACK_TOP)-0x238+offset,count:n)
            }
            guard let bytes = runtime.application.bytes(t,count:n) else {
                runtime.application.canonicalHost.fail(UInt32(CLAW_FAULT_MEMORY),at:t,diagnostic:.invalidMemorySpan)
                return nil
            }
            return bytes
        }
        let configuration = application.startupConfiguration
        let disc = application.startupDisc
        let host = application.canonicalHost
        let previousDependency = host.dependency
        if let configuration {
            host.dependency = {host,call in
                if call.function == 0x546834 || call.function == 0x54682c {return configuration.leaf(host,call)}
                if let disc {
                    if call.function == 0x546a28 || call.function == 0x546a2c {return disc.leaf(host,call)}
                    disc.observeMissing(call)
                }
                return previousDependency?(host,call)
            }
        }
        defer {host.dependency = previousDependency}
        if let pregraphics = application.startupText?.pregraphics {
            guard pregraphics.application === application, configuration != nil, application.startupDisc != nil,
                  arguments[1] != 0 else {
                fail(&context,UInt32(CLAW_FAULT_ABI),at:0x425730,diagnostic:.unsupportedABI);return nil
            }
            pregraphics.commandToken = arguments[1]
            for index: UInt32 in 0..<300 {
                guard let byte = application.bytes(arguments[1]+index,count:1) else {
                    fail(&context,UInt32(CLAW_FAULT_MEMORY),at:arguments[1],diagnostic:.invalidMemorySpan);return nil
                }
                pregraphics.commandBytes.append(byte.pointee)
                if byte.pointee == 0 {break}
            }
            guard pregraphics.commandBytes.last == 0 else {
                fail(&context,UInt32(CLAW_FAULT_ABI),at:0x425730,diagnostic:.unsupportedABI);return nil
            }
        }
        let execute = { arguments.withUnsafeBufferPointer {args in
            claw_application_startup_entry(0x425730,self.application.applicationToken,args.baseAddress,UInt32(args.count),
                &context,{context,call,user in
                    guard let context,let call,let user else {return 0}
                    return Unmanaged<ClawNativeApplicationStartup>.fromOpaque(user).takeUnretainedValue()
                        .service(call.pointee,context:context)
                },user,&result)
        }
        }
        let done: UInt32
        if configuration != nil {
            done = host.withSourceStackFrame(entryStackPointer:UInt32(CLAW_STACK_TOP),arguments:arguments,
                                             at:0x425730,body:execute) ?? 0
        } else {done = execute()}
        if fault == 0 {fault = context.fault}
        return done == 1 && fault == 0 && application.canonicalHost.fault == nil ? result : nil
    }

    private func textService(_ call: ClawApplicationStartupCall, arguments: [UInt32],
                             sizes: [UInt32], buffers: [UnsafeMutableRawPointer?],
                             context: UnsafeMutablePointer<ClawApplicationStartupContext>,
                             text: Text) -> UInt32? {
        let upper = call.function == 0x4f21e0
        let host = application.canonicalHost
        guard active, application.startupConfiguration != nil, text.metadataIntact(),
              call.receiver == 0, call.name == nil, call.localMask == 1,
              call.bufferCount == 1, sizes == [300], arguments.count == (upper ? 1 : 2),
              arguments[0] == 0, let borrowed = buffers[0] else {
            fail(context,UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return nil
        }
        let command = application.heap.lookupBytes(automaticToken+32,count:300)
        let userCommand = application.heap.lookupBytes(automaticToken+332,count:300)
        let isUser = borrowed == userCommand.map {UnsafeMutableRawPointer($0)}
        guard borrowed == command.map({UnsafeMutableRawPointer($0)}) || (!upper && isUser),
              upper || Text.stringTokens.contains(arguments[1]),
              !isUser || arguments[1] == 0x525674 else {
            fail(context,UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return nil
        }
        let token = UInt32(CLAW_STACK_TOP)-(isUser ? 0x138 : 0x42c)
        let frame = UInt32(CLAW_STACK_TOP)-(upper ? 0x4fc : 0x500)
        let sourceArguments = upper ? [token] : [token,arguments[1]]
        let before = Array(UnsafeBufferPointer(start:borrowed.assumingMemoryBound(to:UInt8.self),count:300))
        guard before.contains(0), let source = host.bytes(token,count:300) else {
            fail(context,UInt32(CLAW_FAULT_MEMORY),at:token,diagnostic:.invalidMemorySpan);return nil
        }
        UnsafeMutableRawPointer(source).copyMemory(from:borrowed,byteCount:300)
        var raw: UInt32?, transport: UInt32?
        defer {
            borrowed.copyMemory(from:source,byteCount:300)
            text.record(function:call.function,frame:frame,arguments:sourceArguments,before:before,
                        after:Array(UnsafeBufferPointer(start:source,count:300)),source:raw,transport:transport)
        }
        if upper {
            // Never select or reset the locale here. This legacy service is
            // valid only while the actual prepared CRT LCID remains zero.
            guard let locale = host.bytes(0x540e88,count:4) else {return nil}
            guard UnsafeRawPointer(locale).loadUnaligned(as:UInt32.self).littleEndian == 0 else {
                fail(context,UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return nil
            }
            for offset in 0..<300 {
                let byte = source[offset]
                if byte == 0 {break}
                // Signed source byte comparisons leave every high-bit byte
                // unchanged; only ASCII lowercase bytes are written.
                if byte >= 0x61 && byte <= 0x7a {source[offset] = byte-0x20}
            }
            raw = token;transport = token
        } else {
            // Whole strstr/strchr family admission owns the actual search.
            // Preserve its raw source pointer before adapting the legacy port's
            // explicit local-buffer offset-plus-one return representation.
            var canonical = ClawCall()
            canonical.function = call.function;canonical.stackPointer = frame
            canonical.argumentCount = 2;canonical.arguments.0 = token;canonical.arguments.1 = arguments[1]
            raw = host.invoke(canonical).eax
            if let result = raw {
                guard result == 0 || (result >= token && result <= token+UInt32(before.firstIndex(of:0)!)) else {
                    fail(context,UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return nil
                }
                transport = result == 0 ? 0 : result-token+1
            }
        }
        return transport
    }

    // Borrowed rich pointers are consumed only in this synchronous callback.
    // Diagnostics retain values/shape, never pointers or truncated four-word calls.
    func service(_ call: ClawApplicationStartupCall,
                 context: UnsafeMutablePointer<ClawApplicationStartupContext>) -> UInt32 {
        guard context.pointee.fault == 0, fault == 0, application.canonicalHost.fault == nil else {return 0}
        guard call.argumentCount <= 40, call.bufferCount <= 3 else {
            fail(context,UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return 0
        }
        let arguments = withUnsafeBytes(of:call.arguments) {Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
        let sizes = withUnsafeBytes(of:call.bufferBytes) {Array($0.bindMemory(to:UInt32.self).prefix(Int(call.bufferCount)))}
        let buffers = withUnsafeBytes(of:call.buffers) {Array($0.bindMemory(to:UnsafeMutableRawPointer?.self).prefix(Int(call.bufferCount)))}
        let argumentMask: UInt32 = call.argumentCount >= 32 ? .max : (UInt32(1) << call.argumentCount)-1
        guard call.localMask & ~(argumentMask | 0x100) == 0,
              call.localMask.nonzeroBitCount <= Int(call.bufferCount),
              zip(sizes,buffers).allSatisfy({$0.0 == 0 || $0.1 != nil}) else {
            fail(context,UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return 0
        }
        let appWords = Array(UnsafeBufferPointer(start:application.heap.lookup(application.applicationToken,words:77)!,count:77))
        let clockWords = Array(UnsafeBufferPointer(start:application.heap.lookup(0x541328,words:5)!,count:5))
        // Each declared prefix service takes raw scalar/token arguments only.
        // A richer unknown call is recorded whole and halted, never converted.
        let arities: [UInt32:UInt32] = [0x546df0:0,0x546a24:0,0x546d54:1,0x4a3040:1,0x4f63ec:1]
        var value: UInt32?
        if let arity = arities[call.function] {
            guard call.receiver == 0, call.argumentCount == arity, call.localMask == 0,
                  call.bufferCount == 0, call.name == nil else {
                fail(context,UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return 0
            }
            switch call.function {
            case 0x546df0:value = application.startupClock()
            case 0x546a24:value = readTick()
            case 0x546d54:
                // No undocumented signed-boundary wrap behavior is assumed.
                let next = Int64(cursorCount) + (arguments[0] == 0 ? -1 : 1)
                guard next >= Int64(Int32.min), next <= Int64(Int32.max) else {
                    fail(context,UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return 0
                }
                cursorCount = Int32(next);value = UInt32(bitPattern:cursorCount)
            case 0x4f63ec:
                var allocation = ClawCall();allocation.function = call.function;allocation.argumentCount = 1
                allocation.arguments.0 = arguments[0]
                value = application.invoke(allocation).eax
            case 0x4a3040:
                guard let random,random.initialized,random.fault == 0,
                      let tls = application.heap.lookup(0x52edd8,words:1),tls.pointee == random.globals.pointee.tlsIndex else {
                    fail(context,UInt32(CLAW_FAULT_HOST),at:call.function,diagnostic:.nativeFault);return 0
                }
                // Source srand writes the real shared thread+14 seed. It is void.
                _ = random.call(call.function,arguments:arguments)
                tls.pointee = random.globals.pointee.tlsIndex
                guard random.fault == 0 else {
                    fail(context,UInt32(CLAW_FAULT_HOST),at:call.function,diagnostic:.nativeFault);return 0
                }
                value = 0
            default:preconditionFailure("Declared startup service has no implementation")
            }
        } else if call.function == 0x42a680, let pregraphics = application.startupText?.pregraphics {
            let host = application.canonicalHost
            guard active, pregraphics.application === application, !pregraphics.projected,
                  call.receiver == application.applicationToken, arguments.isEmpty,
                  call.localMask == 0, call.bufferCount == 0, call.name == nil,
                  let receiver = application.bytes(call.receiver,count:0x134),
                  let user = application.bytes(automaticToken+332,count:300),
                  let backing = host.bytes(UInt32(CLAW_STACK_TOP)-0x238,count:556) else {
                fail(context,UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return 0
            }
            // The normalized USER scratch has received all text delimiter edits.
            // Project it once; subsequent CLI writes share this same backing.
            UnsafeMutableRawPointer(backing+256).copyMemory(from:user,byteCount:300)
            pregraphics.beforeBytes = Array(UnsafeBufferPointer(start:backing,count:556))
            pregraphics.hookReceiverBefore = Array(UnsafeBufferPointer(start:receiver,count:0x134))
            var canonical = ClawCall()
            canonical.function = call.function;canonical.receiver = call.receiver
            canonical.stackPointer = UInt32(CLAW_STACK_TOP)-0x4f8
            pregraphics.hookFrame = canonical.stackPointer
            value = host.invoke(canonical).eax
            pregraphics.hookEAX = value
            pregraphics.hookReceiverAfter = Array(UnsafeBufferPointer(start:receiver,count:0x134))
            guard value == 0, pregraphics.hookReceiverBefore == pregraphics.hookReceiverAfter else {
                fail(context,UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return 0
            }
            pregraphics.projected = true
        } else if call.function == 0x5028ec, let pregraphics = application.startupText?.pregraphics {
            let token = UInt32(CLAW_STACK_TOP)-0x238
            guard active, pregraphics.projected, call.receiver == 0, call.name == nil,
                  call.localMask == 4, sizes == [256], arguments.count == 4,
                  arguments[1] == 0, arguments[2] == 0, arguments[3] == 1,
                  let backing = application.canonicalHost.bytes(token,count:556),
                  buffers[0] == UnsafeMutableRawPointer(backing) else {
                fail(context,UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return 0
            }
            // Read the owned source-frame backing, never beyond the borrowed
            // callback's declared256-byte view. The full rich event remains below.
            pregraphics.afterBytes = Array(UnsafeBufferPointer(start:backing,count:556))
            pregraphics.sourceArguments = [arguments[0],0,token,1]
            pregraphics.haltFrame = UInt32(CLAW_STACK_TOP)-0x508
            fail(context,UInt32(CLAW_FAULT_HALT),at:call.function,diagnostic:.missingDependency)
        } else if (call.function == 0x4f21e0 || call.function == 0x4a3990), let text = application.startupText {
            value = textService(call,arguments:arguments,sizes:sizes,buffers:buffers,context:context,text:text)
        } else if call.function == 0x42b020, application.startupDisc != nil,
                  let configuration = application.startupConfiguration, configuration.discPrepared {
            guard active, configuration.metadataIntact(), call.receiver == application.applicationToken,
                  arguments.isEmpty, call.localMask == 0, call.bufferCount == 0, call.name == nil else {
                fail(context,UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return 0
            }
            var canonical = ClawCall()
            canonical.function = call.function;canonical.receiver = call.receiver
            canonical.stackPointer = UInt32(CLAW_STACK_TOP)-0x4f8
            value = application.canonicalHost.invoke(canonical).eax
            if !configuration.metadataIntact() {
                fail(context,UInt32(CLAW_FAULT_MEMORY),at:call.function,diagnostic:.invalidMemorySpan);value = nil
            }
        } else if let configuration = application.startupConfiguration,
                  [UInt32(0x4b5c50),0x4b5f30,0x4b5e90].contains(call.function) {
            let count: UInt32 = call.function == 0x4b5c50 ? 6 : call.function == 0x4b5f30 ? 2 : 4
            let local = call.function == 0x4b5e90
            guard active, configuration.metadataIntact(), call.argumentCount == count, call.name == nil,
                  call.localMask == (local ? 6 : 0), call.bufferCount == (local ? 2 : 0),
                  !local || (sizes == [32,4] && arguments == [0x525714,0,0,0]) else {
                fail(context,UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI);return 0
            }
            var canonical = ClawCall()
            canonical.function = call.function;canonical.receiver = call.receiver;canonical.argumentCount = count
            canonical.stackPointer = UInt32(CLAW_STACK_TOP) - (call.function == 0x4b5c50 ? 0x510 : local ? 0x508 : 0x500)
            var adapted = arguments
            var projections: [(UnsafeMutableRawPointer,UnsafeMutablePointer<UInt8>,Int)] = []
            if local {
                // Original425730 User locals: E-4b0 data32, E-4c4 length4.
                // Only borrow during this callback; copy back while stack scope
                // is live. The source port's normalized scratch owns its bytes.
                for (index, token) in [(1,UInt32(CLAW_STACK_TOP)-0x4b0),(2,UInt32(CLAW_STACK_TOP)-0x4c4)] {
                    let bufferIndex = index-1, size = sizes[bufferIndex]
                    guard let borrowed = buffers[bufferIndex],
                          let target = application.canonicalHost.bytes(token,count:size),
                          let expected = application.bytes(automaticToken+(index == 1 ? 0 : 892),count:size),
                          borrowed == UnsafeMutableRawPointer(expected) else {
                        fail(context,UInt32(CLAW_FAULT_MEMORY),at:token,diagnostic:.invalidMemorySpan);return 0
                    }
                    UnsafeMutableRawPointer(target).copyMemory(from:borrowed,byteCount:Int(size))
                    projections.append((borrowed,target,Int(size)));adapted[index] = token
                }
            }
            withUnsafeMutableBytes(of:&canonical.arguments) {dst in
                adapted.withUnsafeBytes {dst.copyMemory(from:$0)}
            }
            value = application.canonicalHost.invoke(canonical).eax
            // A failed call can have valid preceding writes; retain those bytes.
            for (borrowed,source,size) in projections {borrowed.copyMemory(from:source,byteCount:size)}
            if local {
                configurationUserBytes = Array(UnsafeBufferPointer(start:projections[0].1,count:32))
                configurationUserLength = UnsafeRawPointer(projections[1].1).loadUnaligned(as:UInt32.self).littleEndian
            }
            if !configuration.metadataIntact() {
                fail(context,UInt32(CLAW_FAULT_MEMORY),at:call.function,diagnostic:.invalidMemorySpan);value = nil
            }
        } else {
            fail(context,UInt32(CLAW_FAULT_HALT),at:call.function,diagnostic:.missingDependency)
        }
        events.append(Event(function:call.function,receiver:call.receiver,arguments:arguments,localMask:call.localMask,
                            bufferBytes:sizes,bufferPresent:buffers.map {$0 != nil},
                            applicationWords:appWords,clockWords:clockWords,result:value))
        if value == nil, context.pointee.fault == 0 {
            fail(context,UInt32(CLAW_FAULT_HOST),at:call.function,diagnostic:.nativeFault)
        }
        return value ?? 0
    }
}
