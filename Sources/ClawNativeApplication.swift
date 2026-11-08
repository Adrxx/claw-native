import Foundation

// One native owner for the application heap and deferred command boundary.
// Startup executes the recovered425730 port until its first unsupported service.
// A stopped prefix does not publish a loaded scene/player or select a menu.
final class ClawNativeApplication {
    enum Failure: Error, Equatable {
        case allocation
        case invalidSpan(UInt32, UInt32)
        case unsupportedFunction(UInt32)
        case invalidCall(UInt32)
        case source(UInt32, UInt32)
        case archiveTransport
        case canonical(ClawNativeCanonicalHost.Fault)
    }
    struct Completion {
        let completed: Bool
        let eax: UInt32?
        let fault: Failure?
        let canonicalFault: ClawNativeCanonicalHost.Fault?
    }
    struct Command: Equatable {
        let handlerWord: UInt32
        let command: UInt32
        let data: UInt32
    }
    struct ArchiveInputs {
        let controller: UInt32
        let path: UInt32
    }
    let heap = ClawTokenHeap()
    private(set) var applicationToken: UInt32 = 0
    private(set) var constructed = false
    private(set) var fault: Failure?
    private(set) var clockReads: UInt64 = 0
    private(set) var operationCalls: [UInt32: UInt64] = [:]
    private(set) var pendingCommands: [Command] = []
    private(set) var archive: ClawNativeResourceArchive?
    private(set) var archiveInputs: ArchiveInputs?
    private(set) var startup: ClawNativeApplicationStartup?
    // Installed before source startup; nil retains the strict missing-service
    // boundary. Preparation supplies image data and isolated platform state.
    var startupConfiguration: ClawNativeApplicationStartup.Configuration?
    var startupDisc: ClawNativeApplicationStartup.Disc?
    var startupText: ClawNativeApplicationStartup.Text?
    private let readClock: () -> UInt32
    private let readTick: () -> UInt32
    private let initialCursorCount: Int32
    private let singlePlayerGlobals = UnsafeMutablePointer<ClawSinglePlayerSceneGlobals>.allocate(capacity:1)
    private var activeResetGlobals: UnsafeMutablePointer<ClawSpecialCommandGlobals>?
    private var allocations: Set<UInt32> = []
    // Source new/delete allocations are separate from application transport
    // storage. A source allocation refusal returns zero without setting fault.
    private(set) var sourceAllocations: [UInt32: UInt32] = [:]
    private var sourceAllocationBytes: UInt64 = 0
    private let sourceAllocationByteLimit: UInt64?
    private var canonicalStorage: ClawNativeCanonicalHost?
    var canonicalHost: ClawNativeCanonicalHost {
        if let canonicalStorage {return canonicalStorage}
        let host = ClawNativeCanonicalHost(heap:heap,dependency:{[weak self] host,call in
            self?.canonicalDependency(host,call)
        })
        canonicalStorage = host;return host
    }

    init(clock: @escaping () -> UInt32 = {
        UInt32(truncatingIfNeeded:UInt64(ProcessInfo.processInfo.systemUptime * 1000))
    }, sourceAllocationByteLimit: UInt64? = nil,
       tickClock: @escaping () -> UInt32 = {
           UInt32(truncatingIfNeeded:UInt64(ProcessInfo.processInfo.systemUptime * 1000))
       }, initialCursorCount: Int32 = 0) throws {
        readClock = clock
        readTick = tickClock
        self.initialCursorCount = initialCursorCount
        self.sourceAllocationByteLimit = sourceAllocationByteLimit
        singlePlayerGlobals.initialize(to:ClawSinglePlayerSceneGlobals())
        // Same immutable empty CString metadata as the existing native scene.
        // Mutable timer words are shared raw aliases, not a second Swift cache.
        heap.store(token:0x52e1b8,words:4)[0] = .max
        heap.store(token:0x52e1cc,words:1)[0] = 0x52e1c4
        _ = heap.store(token:0x541328,words:5)
        _ = heap.store(token:0x53c260,words:1)
        // Pinned EXE .data initials, independently verified before this join.
        // Only reset42abf0's stage, animation and player aliases are bound here.
        _ = heap.store(token:0x537208,words:2)
        _ = heap.store(token:0x5430c4,words:2)
        _ = heap.store(token:0x537e88,words:1)
        applicationToken = allocate(UInt32(CLAW_ORIGINAL_APPLICATION_BYTES))
        guard applicationToken != 0 else {throw record(.allocation)}
        let result = try invoke(0x4254a0,receiver:applicationToken)
        guard result == applicationToken else {throw record(.source(0x4254a0,0))}
    }
    deinit {
        // Release archive subobjects before the application's borrowed storage.
        // Full initialized-application destruction is outside this constructor slice.
        archive?.shutdown();archive = nil
        startup = nil
        startupText = nil
        startupDisc = nil
        for token in sourceAllocations.keys {heap.free(token)}
        for token in allocations {heap.free(token)}
        singlePlayerGlobals.deinitialize(count:1);singlePlayerGlobals.deallocate()
    }
    private func record(_ value: Failure) -> Failure {
        if fault == nil {fault = value};return fault!
    }
    private func allocate(_ count: UInt32) -> UInt32 {
        let token = heap.allocate(bytes:count)
        if token != 0 {allocations.insert(token)} else {_ = record(.allocation)}
        return token
    }
    private func release(_ token: UInt32) {
        guard token != 0 else {return}
        guard allocations.remove(token) != nil else {_ = record(.invalidSpan(token,0));return}
        heap.free(token)
    }
    // Exact byte extents, including odd-sized and unaligned CString interiors.
    func bytes(_ token: UInt32, count: UInt32) -> UnsafeMutablePointer<UInt8>? {
        heap.lookupBytes(token,count:count)
    }
    func makeCString(_ text: String) throws -> UInt32 {
        if let fault {throw fault}
        let value = Array(text.utf8)+[UInt8(0)]
        guard value.count <= Int(UInt32.max) else {throw record(.allocation)}
        let token = allocate(UInt32(value.count))
        guard token != 0, let pointer = bytes(token,count:UInt32(value.count)) else {throw record(.allocation)}
        value.withUnsafeBufferPointer {pointer.update(from:$0.baseAddress!,count:$0.count)}
        return token
    }
    var actorHost: ClawSceneActorHost {
        ClawSceneActorHost(context:Unmanaged.passUnretained(self).toOpaque(),lookup:{u,t,n in
            guard let u else {return nil}
            let owner = Unmanaged<ClawNativeApplication>.fromOpaque(u).takeUnretainedValue()
            if owner.activeResetGlobals != nil {
                guard n <= UInt32.max / 4, t & 3 == 0, owner.bytes(t,count:n*4) != nil else {
                    _ = owner.record(.invalidSpan(t,n <= UInt32.max / 4 ? n*4 : .max));return nil
                }
            }
            return owner.heap.lookup(t,words:n)
        },allocate:{u,n in
            guard let u else {return 0}
            return Unmanaged<ClawNativeApplication>.fromOpaque(u).takeUnretainedValue().allocate(n)
        },free:{u,t in
            guard let u else {return}
            Unmanaged<ClawNativeApplication>.fromOpaque(u).takeUnretainedValue().release(t)
        },call:{u,q in
            guard let u else {return 0}
            let owner = Unmanaged<ClawNativeApplication>.fromOpaque(u).takeUnretainedValue()
            guard q.argumentCount <= 4 else {_ = owner.record(.invalidCall(q.function));return 0}
            let args = withUnsafeBytes(of:q.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(q.argumentCount)))}
            // C callbacks cannot throw. The sticky fault distinguishes unsupported
            // service failure from an ordinary original zero return.
            return (try? owner.invoke(q.function,receiver:q.receiver,arguments:args)) ?? 0
        },readClock:{u in
            guard let u else {return 0}
            let owner = Unmanaged<ClawNativeApplication>.fromOpaque(u).takeUnretainedValue()
            return owner.sampleClock()
        })
    }
    // SpecialCommandRuntime uses a portable snapshot. Commit before each host
    // callback and reload after it, matching original live global aliasing.
    // No long-lived cached globals can overwrite writes by another runtime.
    private func resetAliases(_ globals: UnsafeMutablePointer<ClawSpecialCommandGlobals>, publish: Bool) throws {
        func span(_ token: UInt32, _ count: UInt32) throws -> UnsafeMutablePointer<UInt32> {
            guard bytes(token,count:count*4) != nil, let value = heap.lookup(token,words:count) else {
                throw record(.invalidSpan(token,count*4))
            }
            return value
        }
        let clock = try span(0x541328,5), stage = try span(0x537208,2)
        let animation = try span(0x5430c4,2), player = try span(0x537e88,1)
        if publish {
            let value = globals.pointee
            clock[0] = value.clock.nowMilliseconds;clock[1] = value.clock.deltaMilliseconds
            clock[2] = value.clock.pacedFrameStart;clock[3] = value.clock.countdown;clock[4] = value.clock.countdownReload
            stage[0] = value.stage.nowMilliseconds;stage[1] = value.stage.deltaMilliseconds
            animation[0] = value.animation.deltaMilliseconds;animation[1] = value.animation.nowMilliseconds
            player[0] = value.playerToken
        } else {
            globals.pointee.clock = ClawClockState(nowMilliseconds:clock[0],deltaMilliseconds:clock[1],pacedFrameStart:clock[2],countdown:clock[3],countdownReload:clock[4])
            globals.pointee.stage = ClawFrameClock(nowMilliseconds:stage[0],deltaMilliseconds:stage[1])
            globals.pointee.animation = ClawFrameClock(nowMilliseconds:animation[1],deltaMilliseconds:animation[0])
            globals.pointee.playerToken = player[0]
        }
    }
    private func sampleClock() -> UInt32 {
        do {
            if let activeResetGlobals {try resetAliases(activeResetGlobals,publish:true)}
            clockReads &+= 1
            let value = readClock()
            if let activeResetGlobals {try resetAliases(activeResetGlobals,publish:false)}
            return value
        } catch {return 0} // The exact span fault remains sticky across the C ABI.
    }
    // The startup adapter samples the same clock as the application constructor.
    func startupClock() -> UInt32 { sampleClock() }
    var clockSnapshot: ClawClockState {
        UnsafeRawPointer(heap.lookup(0x541328,words:5)!).load(as:ClawClockState.self)
    }
    // Registry ownership always wins. Full call envelopes are validated before
    // any conversion to the smaller legacy ABI; canonical recursion continues
    // to be rejected by ClawNativeCanonicalHost's scoped-stack boundary.
    func invoke(_ call: ClawCall) -> Completion {
        let host = canonicalHost
        if let canonicalFault = host.fault {_ = record(.canonical(canonicalFault))}
        guard fault == nil else {return Completion(completed:false,eax:nil,fault:fault,canonicalFault:host.fault)}
        let eax: UInt32?
        if claw_canonical_lookup(call.function) != nil {
            eax = host.invoke(call).eax
        } else if Self.legacyArity(call.function) != nil {
            eax = host.callNativeDependency(call)
        } else {
            // Top-level unknown entries have the registry's unknown-entry fault;
            // a missing callee reached inside canonical code is a service halt.
            eax = host.invoke(call).eax
        }
        if let canonicalFault = host.fault {_ = record(.canonical(canonicalFault))}
        let completed = eax != nil && fault == nil && host.fault == nil
        return Completion(completed:completed,eax:completed ? eax : nil,fault:fault,canonicalFault:host.fault)
    }
    private static func legacyArity(_ function: UInt32) -> UInt32? {
        switch function {
        case 0x4254a0,0x40b5c0,0x42abf0,0x4b82f0,0x4b7210,0x4b7250: return 0
        case 0x4b72e0: return 3
        case 0x425730: return 2
        case 0x4f63ec,0x4f6428: return 1
        default: return nil
        }
    }
    private func canonicalDependency(_ host: ClawNativeCanonicalHost, _ call: ClawCall) -> UInt32? {
        guard fault == nil else {
            host.fail(UInt32(CLAW_FAULT_HOST),at:call.function);return nil
        }
        guard let count = Self.legacyArity(call.function) else {return nil}
        let allocator = call.function == 0x4f63ec || call.function == 0x4f6428
        guard call.argumentCount == count, call.receiver2 == 0, call.x87ArgumentCount == 0,
              call.stackPointer == 0, !allocator || call.receiver == 0 else {
            _ = record(.canonical(host.fail(UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI)))
            return nil
        }
        let args = withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(count)))}
        if call.function == 0x4f63ec {
            if let limit = sourceAllocationByteLimit,
               sourceAllocationBytes > limit || UInt64(args[0]) > limit-sourceAllocationBytes {return 0}
            let token = heap.allocate(bytes:args[0])
            if token != 0 {sourceAllocations[token] = args[0];sourceAllocationBytes += UInt64(args[0])}
            return token
        }
        if call.function == 0x4f6428 {
            guard args[0] != 0 else {return 0}
            guard let count = sourceAllocations.removeValue(forKey:args[0]) else {
                _ = record(.canonical(host.fail(UInt32(CLAW_FAULT_MEMORY),at:args[0],diagnostic:.invalidMemorySpan)))
                return nil
            }
            sourceAllocationBytes -= UInt64(count);heap.free(args[0]);return 0
        }
        // Thiscall identity is validated before legacy conversion, including
        // rejection of arbitrary source pointers as the persistent app owner.
        if call.function == 0x40b5c0 {
            guard call.receiver & 3 == 0, let size = sourceAllocations[call.receiver], size >= 0x154,
                  heap.lookupBytes(call.receiver,count:0x154) != nil else {
                _ = record(.canonical(host.fail(UInt32(CLAW_FAULT_MEMORY),at:call.receiver,diagnostic:.invalidMemorySpan)))
                return nil
            }
        } else {
            let expectedReceiver = call.function == 0x4254a0 || call.function == 0x425730 || call.function == 0x4b82f0 || call.function == 0x42abf0
                ? applicationToken : archive?.controller
            guard let expectedReceiver, call.receiver == expectedReceiver else {
                _ = record(.canonical(host.fail(UInt32(CLAW_FAULT_ABI),at:call.function,diagnostic:.unsupportedABI)))
                return nil
            }
        }
        do {return try invoke(call.function,receiver:call.receiver,arguments:args)}
        catch {
            let abi = fault == .invalidCall(call.function)
            host.fail(UInt32(abi ? CLAW_FAULT_ABI : CLAW_FAULT_HOST),at:call.function,
                      diagnostic:abi ? .unsupportedABI : .nativeFault)
            return nil
        }
    }
    @discardableResult func invoke(_ function: UInt32, receiver: UInt32, arguments: [UInt32] = []) throws -> UInt32 {
        if let canonicalFault = canonicalStorage?.fault {_ = record(.canonical(canonicalFault))}
        if let fault {throw fault}
        switch function {
        case 0x425730:
            guard constructed, receiver == applicationToken, arguments.count == 2, startup == nil else {
                throw record(.invalidCall(function))
            }
            let runtime = ClawNativeApplicationStartup(application:self,tickClock:readTick,initialCursorCount:initialCursorCount)
            startup = runtime
            operationCalls[function,default:0] &+= 1
            let result = runtime.run(arguments:arguments)
            if let canonicalFault = canonicalHost.fault {throw record(.canonical(canonicalFault))}
            guard let result, runtime.fault == 0, fault == nil else {throw record(.source(function,runtime.fault))}
            return result
        case 0x4254a0:
            guard receiver == applicationToken, arguments.isEmpty, !constructed else {throw record(.invalidCall(function))}
            var context = ClawSinglePlayerSceneContext(), result: UInt32 = 0
            context.host = actorHost;context.globals = singlePlayerGlobals
            operationCalls[function,default:0] &+= 1
            let done = claw_single_player_scene_entry(function,receiver,nil,0,&context,nil,nil,&result)
            guard done == 1, context.fault == 0, fault == nil else {throw record(.source(function,context.fault))}
            constructed = true;return result
        case 0x40b5c0:
            guard arguments.isEmpty else {throw record(.invalidCall(function))}
            guard receiver & 3 == 0, let size = sourceAllocations[receiver], size >= 0x154,
                  heap.lookupBytes(receiver,count:0x154) != nil else {throw record(.invalidSpan(receiver,0x154))}
            // The recovered constructor performs its sparse stores itself.
            // Preserve its EAX normalization and all untouched object bytes.
            var context = ClawSinglePlayerSceneContext(), result: UInt32 = 0
            context.host = actorHost;context.globals = singlePlayerGlobals
            operationCalls[function,default:0] &+= 1
            let done = claw_single_player_scene_entry(function,receiver,nil,0,&context,nil,nil,&result)
            guard done == 1, context.fault == 0, fault == nil else {throw record(.source(function,context.fault))}
            return result
        case 0x42abf0:
            guard constructed, receiver == applicationToken, arguments.isEmpty, activeResetGlobals == nil else {
                throw record(.invalidCall(function))
            }
            var globals = ClawSpecialCommandGlobals()
            return try withUnsafeMutablePointer(to:&globals) {pointer in
                try resetAliases(pointer,publish:false)
                activeResetGlobals = pointer
                defer {activeResetGlobals = nil}
                var context = ClawSpecialCommandContext(), result: UInt32 = 0
                context.scene = actorHost;context.globals = pointer
                operationCalls[function,default:0] &+= 1
                let done = claw_special_command_entry(function,receiver,nil,0,&context,nil,nil,&result)
                // Source reset writes clocks before following the player graph.
                // Preserve that reached prefix even when a later lookup fails.
                try resetAliases(pointer,publish:true)
                guard done == 1, context.fault == 0, fault == nil else {throw record(.source(function,context.fault))}
                return result
            }
        case 0x4b82f0:
            guard constructed, receiver == applicationToken, arguments.isEmpty,
                  let rawManager = heap.lookup(applicationToken+0x18,words:5), let rawClock = heap.lookup(0x541328,words:5) else {
                throw record(.invalidCall(function))
            }
            let host = actorHost
            let timingHost = ClawTimingHost(context:host.context,read:host.readClock,observeWait:nil)
            operationCalls[function,default:0] &+= 1
            return claw_timing_update(UnsafeMutableRawPointer(rawManager).assumingMemoryBound(to:ClawTimingManager.self),
                                     UnsafeMutableRawPointer(rawClock).assumingMemoryBound(to:ClawClockState.self),timingHost)
        case 0x4b7210,0x4b72e0,0x4b7250:
            guard let archive, receiver == archive.controller else {throw record(.invalidCall(function))}
            do {
                let result = try archive.operation(function,args:arguments)
                operationCalls[function,default:0] &+= 1;return result
            } catch ClawNativeResourceArchive.Failure.source(let address, let code) {
                throw record(.source(address,code))
            } catch {throw record(.archiveTransport)}
        default: throw record(.unsupportedFunction(function))
        }
    }
    // Preparation supplies storage only. Source startup will eventually own
    // app+34 publication and its constructor/open ordering; neither occurs here.
    func prepareArchive(at url: URL) throws -> ArchiveInputs {
        if let fault {throw fault}
        guard archive == nil else {throw record(.invalidCall(0x4b7210))}
        let controller = allocate(UInt32(CLAW_RESOURCE_ARCHIVE_CONTROLLER_BYTES))
        guard controller != 0 else {throw record(.allocation)}
        let path = try makeCString(url.path)
        do {
            archive = try ClawNativeResourceArchive(heap:heap,borrowingController:controller,
                borrowedBytes:{[heap] token,count in heap.lookupBytes(token,count:count)})
        } catch {release(controller);release(path);throw record(.archiveTransport)}
        let inputs = ArchiveInputs(controller:controller,path:path)
        archiveInputs = inputs;return inputs
    }
    // Cleanup remains available after a fault. Successful shutdown does not
    // clear diagnostics from a preceding unsupported application operation.
    func releaseArchive() throws {
        guard let archive, let inputs = archiveInputs else {return}
        archive.shutdown()
        guard archive.fault == 0 else {throw record(.source(0x4b7250,archive.fault))}
        self.archive = nil;archiveInputs = nil
        release(inputs.controller);release(inputs.path)
    }
    func postCommand(handlerWord: UInt32 = 0, command: UInt32, data: UInt32 = 0) {
        pendingCommands.append(Command(handlerWord:handlerWord,command:command,data:data))
    }
    // Dequeue only outside source callbacks. Commands posted during processing
    // remain in the next batch, retaining all three original argument words.
    func takePendingCommands() -> [Command] {
        let batch = pendingCommands;pendingCommands.removeAll(keepingCapacity:true);return batch
    }
}
