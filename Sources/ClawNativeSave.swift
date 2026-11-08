import Foundation
import Darwin

// App-owned metadata only. CLAW.USR remains entirely owned by recovered code.
struct ClawCheckpointPlacement: Codable, Hashable {
    let plane: UInt32, id: UInt32
}

// Whole original save/load routines own format, cipher, records and lists.
// This host maps the original Windows pathname onto a caller-selected native
// directory. Files, ANSI CString assignment and ASCII locale are transports.
final class ClawNativeSave {
    let heap: ClawTokenHeap
    let random: ClawNativeRandom
    let storageDirectory: URL
    let managerToken: UInt32
    private let context = UnsafeMutablePointer<ClawSaveLoadContext>.allocate(capacity: 1)
    private var handles: [UInt32: FileHandle] = [:]
    private var nextHandle: UInt32 = 0x6a00_0000
    private var lastError: UInt32 = 0
    private(set) var fault: UInt32 = 0
    private(set) var unresolved: Set<UInt32> = []
    private(set) var failure: String?
    private(set) var entries: [UInt32: UInt64] = [:]
    private(set) var physicalReads = 0
    private(set) var physicalWrites = 0
    private var ownsManager = false
    var saveURL: URL { storageDirectory.appendingPathComponent("CLAW.USR") }
    var sourceHost: ClawSceneActorHost { context.pointee.save.scene }
    var playerRecord: UInt32 { entry(0x49bee0, arguments: [0x5255e8]) }

    // MARK: - Manager lifecycle

    init(heap: ClawTokenHeap, random: ClawNativeRandom, storageDirectory: URL) throws {
        self.heap = heap
        self.random = random
        self.storageDirectory = storageDirectory
        context.initialize(to: ClawSaveLoadContext())
        managerToken = heap.allocate(bytes: 0x58)
        installMetadata()
        // Callbacks borrow this owner during synchronous recovered calls; they do not retain it.
        context.pointee.save.scene = ClawSceneActorHost(
            context: Unmanaged.passUnretained(self).toOpaque(),
            lookup: { user, token, words in
                guard let user else { return nil }
                return Unmanaged<ClawNativeSave>.fromOpaque(user).takeUnretainedValue().heap.lookup(token, words: words)
            },
            allocate: { user, bytes in
                guard let user else { return 0 }
                return Unmanaged<ClawNativeSave>.fromOpaque(user).takeUnretainedValue().heap.allocate(bytes: bytes)
            },
            free: { user, token in
                guard let user else { return }
                Unmanaged<ClawNativeSave>.fromOpaque(user).takeUnretainedValue().heap.free(token)
            }, call: nil, readClock: nil)
        context.pointee.save.lookupBytes = { user, token, bytes in
            guard let user else { return nil }
            return Unmanaged<ClawNativeSave>.fromOpaque(user).takeUnretainedValue().bytes(token, count: bytes)
        }
        context.pointee.save.emptyStringToken = 0x52e1c4
        context.pointee.save.fileScratchToken = heap.allocate(bytes: 16)
        context.pointee.save.pathScratchToken = heap.allocate(bytes: 260)
        context.pointee.save.securityScratchToken = heap.allocate(bytes: 12)
        context.pointee.save.countScratchToken = heap.allocate(bytes: 4)
        context.pointee.directoryScratchToken = heap.allocate(bytes: 260)
        context.pointee.maximumTraversal = 100000
        guard claw_save_file_initialize_manager(managerToken, &context.pointee.save) == 1 else {
            throw AssetError.invalid("Source save manager constructor")
        }
        ownsManager = true
        try FileManager.default.createDirectory(at: storageDirectory, withIntermediateDirectories: true)
        guard entry(0x49b840, arguments: [0x525618]) == 1 && fault == 0 && playerRecord != 0 else {
            throw AssetError.invalid(failure ?? "Source save startup/default player fault \(fault)")
        }
    }

    deinit {
        if ownsManager && fault == 0 { _ = entry(0x49b950) }
        for handle in handles.values { try? handle.close() }
        context.deinitialize(count: 1)
        context.deallocate()
    }

    // MARK: - Original metadata and token-backed byte/string transport

    private func installMetadata() {
        func words(_ token: UInt32, _ values: [UInt32]) {
            if heap.lookup(token, words: UInt32(values.count)) != nil { return }
            let span = heap.store(token: token, words: values.count)
            values.withUnsafeBufferPointer { span.update(from: $0.baseAddress!, count: $0.count) }
        }
        // Exact immutable source bytes from the hash-pinned original PE.
        words(0x52e1b8, [.max, 0, 0, 0])
        words(0x50feac, [0x4f701d, 0x4d5330])
        words(
            0x510844,
            [
                0x502ac2, 0x4f7309, 0x4c9e30, 0x4c96b0, 0x4c9e30, 0x4f7624, 0x4fc035, 0x4fc0b7, 0x4fc139, 0x4a1628,
                0x4f7448, 0x4f73b7, 0x4f75f5, 0x4f7721,
            ])
        for (token, text) in [
            (UInt32(0x525618), "CLAW.USR"), (0x5255e8, "Player"), (0x525f78, "%s\\%s"), (0x534938, ""),
        ] {
            let data = Array(text.utf8) + [UInt8(0)]
            if heap.lookup(token, words: UInt32((data.count + 3) / 4)) == nil {
                _ = heap.store(token: token, words: (data.count + 3) / 4)
            }
            data.withUnsafeBufferPointer {
                bytes(token, count: UInt32(data.count))!.update(from: $0.baseAddress!, count: $0.count)
            }
        }
    }

    // The returned span borrows heap storage and is consumed synchronously by the caller.
    fileprivate func bytes(_ token: UInt32, count: UInt32) -> UnsafeMutablePointer<UInt8>? {
        let offset = token & 3
        let total = UInt64(offset) + UInt64(count)
        guard total <= UInt64(UInt32.max) - 3, let span = heap.lookup(token & ~3, words: UInt32((total + 3) / 4)) else {
            return nil
        }
        return UnsafeMutableRawPointer(span).assumingMemoryBound(to: UInt8.self).advanced(by: Int(offset))
    }

    private func readCStringBytes(_ token: UInt32) -> [UInt8]? {
        var value: [UInt8] = []
        for offset: UInt32 in 0..<65536 {
            guard let byte = bytes(token &+ offset, count: 1)?.pointee else {
                fault = 1
                return nil
            }
            if byte == 0 { return value }
            value.append(byte)
        }
        fault = 4
        return nil
    }

    private func writeBytes(_ value: [UInt8], at token: UInt32) -> Bool {
        guard let span = bytes(token, count: UInt32(value.count)) else {
            fault = 1
            return false
        }
        value.withUnsafeBufferPointer { span.update(from: $0.baseAddress!, count: $0.count) }
        return true
    }

    private func releaseString(field: UInt32) {
        var globals = ClawActorDestructionGlobals(holderActorToken: 0, heldActorToken: 0, emptyStringToken: 0x52e1c4)
        var sourceFault: UInt32 = 0
        var result: UInt32 = 0
        let done = claw_actor_destruction_entry(
            0x4f6584, field, 0, &globals, context.pointee.save.scene, &sourceFault, &result)
        fault = max(fault, sourceFault)
        if done != 1 { fault = 1 }
    }

    private func assignCString(_ value: [UInt8], field: UInt32) -> UInt32 {
        releaseString(field: field)
        guard fault == 0 else { return 0 }
        // CString storage holds reference count, length and capacity before its terminated bytes.
        let header = heap.allocate(bytes: UInt32(13 + value.count))
        let span = heap.lookup(header, words: 3)!
        span[0] = 1
        span[1] = UInt32(value.count)
        span[2] = UInt32(value.count)
        guard writeBytes(value + [0], at: header + 12), let target = heap.lookup(field, words: 1) else {
            fault = 1
            return 0
        }
        target.pointee = header + 12
        return field
    }

    // MARK: - Recovered entry dispatch

    @discardableResult func entry(_ function: UInt32, receiver: UInt32? = nil, arguments: [UInt32] = []) -> UInt32 {
        var result: UInt32 = 0
        entries[function, default: 0] &+= 1
        let done = heap.withStableFreedStorage {
            arguments.withUnsafeBufferPointer { args in
                if [
                    UInt32(0x49bbc0), 0x49bf70, 0x49bfb0, 0x49c000, 0x49c030, 0x49c070, 0x4f72c9, 0x4f7369, 0x4f7448,
                    0x4f75aa, 0x4f766e, 0x4f650f,
                ].contains(function) {
                    return claw_save_file_entry(
                        function, receiver ?? managerToken, args.baseAddress, UInt32(args.count), &context.pointee.save,
                        nativeSaveFileDependency, Unmanaged.passUnretained(self).toOpaque(), &result)
                }
                return claw_save_load_entry(
                    function, receiver ?? managerToken, args.baseAddress, UInt32(args.count), context,
                    nativeSaveLoadDependency, Unmanaged.passUnretained(self).toOpaque(), &result)
            }
        }
        fault = max(fault, max(context.pointee.fault, context.pointee.save.fault))
        if done != 1 {
            unresolved.insert(function)
            fault = max(1, fault)
        }
        return result
    }

    // MARK: - Synchronous native platform services

    // Address cases are stable dependency identities, not native pointers. Unknown services fault.
    fileprivate func transport(_ call: ClawSaveFileCall) -> UInt32 {
        let arguments = withUnsafeBytes(of: call.arguments) {
            Array($0.bindMemory(to: UInt32.self).prefix(Int(call.argumentCount)))
        }
        do {
            switch call.function {
            case 0x4a3040, 0x4a3050:
                let result = random.call(call.function, arguments: arguments)
                fault = max(fault, random.fault)
                return result
            case 0x4f6584:
                releaseString(field: call.receiver)
                return 0
            case 0x4f64ba:
                releaseString(field: call.receiver)
                heap.lookup(call.receiver, words: 1)?.pointee = 0x52e1c4
                return 0
            case 0x4f66cc:
                guard let value = readCStringBytes(arguments[0]) else { return 0 }
                return assignCString(value, field: call.receiver)
            case 0x4f777f:
                guard let value = readCStringBytes(arguments[1]), value.count < 260 else {
                    fault = 1
                    return 0
                }
                return writeBytes(value + [0], at: arguments[0]) ? 1 : 0
            case 0x4f4f58:
                guard let format = readCStringBytes(arguments[1]), format == Array("%s\\%s".utf8),
                    let directory = readCStringBytes(arguments[2]),
                    let file = readCStringBytes(arguments[3])
                else {
                    fault = 1
                    return 0
                }
                return assignCString(directory + [92] + file, field: arguments[0])
            case 0x4a3cf0:
                guard let leftBytes = readCStringBytes(arguments[0]), let rightBytes = readCStringBytes(arguments[1])
                else { return 0 }
                func lowercaseASCII(_ bytes: [UInt8]) -> [UInt8] { bytes.map { $0 >= 65 && $0 <= 90 ? $0 + 32 : $0 } }
                let left = lowercaseASCII(leftBytes)
                let right = lowercaseASCII(rightBytes)
                return left == right ? 0 : left.lexicographicallyPrecedes(right) ? .max : 1
            case 0x546a28: return writeBytes(Array("C:\\CLAW".utf8) + [0], at: arguments[1]) ? 7 : 0
            case 0x546a10: return writeBytes(Array("C:\\WINDOWS".utf8) + [0], at: arguments[0]) ? 10 : 0
            case 0x546a2c: return 3  // Explicit native fixed-disk path profile.
            case 0x546b0c: return lastError
            // File open/create, close, write, read and seek retain source service order.
            case 0x546b00:
                guard let raw = readCStringBytes(arguments[0]),
                    String(decoding: raw, as: UTF8.self).uppercased() == "C:\\CLAW\\CLAW.USR"
                else {
                    lastError = 3
                    return .max
                }
                if arguments[4] == 2 { try Data().write(to: saveURL) }
                guard FileManager.default.fileExists(atPath: saveURL.path) else {
                    lastError = 2
                    return .max
                }
                let handle =
                    arguments[1] == 0x4000_0000
                    ? try FileHandle(forWritingTo: saveURL) : try FileHandle(forReadingFrom: saveURL)
                nextHandle &+= 1
                handles[nextHandle] = handle
                return nextHandle
            case 0x546a04:
                guard let handle = handles.removeValue(forKey: arguments[0]) else {
                    lastError = 6
                    return 0
                }
                try handle.close()
                return 1
            case 0x546af8:
                guard let handle = handles[arguments[0]], let span = bytes(arguments[1], count: arguments[2]),
                    let transferredByteCount = heap.lookup(arguments[3], words: 1)
                else {
                    fault = 1
                    return 0
                }
                try handle.write(contentsOf: Data(bytes: span, count: Int(arguments[2])))
                transferredByteCount.pointee = arguments[2]
                physicalWrites += 1
                return 1
            case 0x546afc:
                guard let handle = handles[arguments[0]], let span = bytes(arguments[1], count: arguments[2]),
                    let transferredByteCount = heap.lookup(arguments[3], words: 1)
                else {
                    fault = 1
                    return 0
                }
                let data = try handle.read(upToCount: Int(arguments[2])) ?? Data()
                data.withUnsafeBytes {
                    if let base = $0.baseAddress {
                        UnsafeMutableRawPointer(span).copyMemory(from: base, byteCount: $0.count)
                    }
                }
                transferredByteCount.pointee = UInt32(data.count)
                physicalReads += 1
                return 1
            case 0x546af4:
                guard let handle = handles[arguments[0]] else {
                    lastError = 6
                    return .max
                }
                let originalOffset = try handle.offset()
                let base: UInt64
                if arguments[3] == 1 {
                    base = originalOffset
                } else if arguments[3] == 2 {
                    base = try handle.seekToEnd()
                } else {
                    base = 0
                }
                let position = Int64(base) + Int64(Int32(bitPattern: arguments[1]))
                guard position >= 0 && position < Int64(UInt32.max) else {
                    lastError = 87
                    return .max
                }
                try handle.seek(toOffset: UInt64(position))
                return UInt32(position)
            case 0x4fc242, 0x4fc303:
                failure = "Source file exception at \(String(call.function,radix:16)), native error \(lastError)"
                fault = 3
                return 0
            case 0x4fc384: return lastError  // Native OS error mapping is explicit transport.
            default:
                unresolved.insert(call.function)
                fault = 1
                return 0
            }
        } catch {
            lastError = UInt32(truncatingIfNeeded: (error as NSError).code)
            failure = String(describing: error)
            // Original platform APIs report failure; their reached source
            // exception election sets the enclosing fault on the next call.
            if call.function == 0x546b00 || call.function == 0x546af4 { return .max }
            return 0
        }
    }

    func stringService(_ function: UInt32, receiver: UInt32, argument: UInt32 = 0) -> UInt32 {
        if function == 0x4f650f { return entry(function, receiver: receiver) }
        if function == 0x4f6449 {
            var globals = ClawPlayerDeathServiceGlobals(managerToken: 0, emptyStringToken: 0x52e1c4)
            var result: UInt32 = 0
            let done = withUnsafeMutablePointer(to: &globals) { globalsPointer -> UInt32 in
                var serviceContext = ClawPlayerDeathServiceContext(
                    scene: context.pointee.save.scene, globals: globalsPointer, temporaryStringToken: 0, fault: 0)
                var argumentWord = argument
                let completed = withUnsafePointer(to: &argumentWord) {
                    claw_player_death_service_entry(
                        function, receiver, $0, 1, &serviceContext,
                        { serviceContext, event, user in
                            guard let serviceContext, let event, let user else { return 0 }
                            let owner = Unmanaged<ClawNativeSave>.fromOpaque(user).takeUnretainedValue()
                            var call = ClawSaveFileCall()
                            call.function = event.pointee.function
                            call.receiver = event.pointee.receiver
                            call.argumentCount = event.pointee.argumentCount
                            call.arguments.0 = event.pointee.arguments.0
                            let value = owner.transport(call)
                            if owner.fault != 0 { serviceContext.pointee.fault = owner.fault }
                            return value
                        }, Unmanaged.passUnretained(self).toOpaque(), &result)
                }
                fault = max(fault, serviceContext.fault)
                return completed
            }
            if done != 1 { fault = max(1, fault) }
            return result
        }
        guard [UInt32(0x4f66cc), 0x4f6584, 0x4f64ba].contains(function) else {
            fault = 1
            return 0
        }
        var event = ClawSaveFileCall()
        event.function = function
        event.receiver = receiver
        event.argumentCount = function == 0x4f66cc ? 1 : 0
        event.arguments.0 = argument
        return transport(event)
    }
}
// These bridges propagate the owner fault into the active recovered contexts.
private let nativeSaveFileDependency: ClawSaveFileDependency = { context, event, user in
    guard let context, let event, let user else { return 0 }
    let owner = Unmanaged<ClawNativeSave>.fromOpaque(user).takeUnretainedValue()
    let result = owner.transport(event.pointee)
    if owner.fault != 0 { context.pointee.fault = owner.fault }
    return result
}
private let nativeSaveLoadDependency: ClawSaveLoadDependency = { context, event, user in
    guard let context, let event, let user else { return 0 }
    let owner = Unmanaged<ClawNativeSave>.fromOpaque(user).takeUnretainedValue()
    let result = owner.transport(event.pointee)
    if owner.fault != 0 {
        context.pointee.fault = owner.fault
        context.pointee.save.fault = owner.fault
    }
    return result
}

// MARK: - Snapshot persistence

extension ClawNativeSave {
    // Property names and explicit field-table keys are part of the existing snapshot schema.
    struct SavedState: Codable, Equatable {
        let manager: UInt32, context: [String: Data], file: [String: Data]
        let nextHandle: UInt32, lastError: UInt32, fault: UInt32, unresolved: Set<UInt32>, failure: String?
        let entries: [UInt32: UInt64], reads: Int, writes: Int, ownsManager: Bool
    }

    func savedState() throws -> SavedState {
        // Source file I/O is synchronous. No file or pathname is archived or
        // opened during restore; the user's original CLAW.USR stays untouched.
        guard handles.isEmpty else { throw ClawSnapshotError.activeFrame }
        return .init(
            manager: managerToken, context: Self.contextFields.capture(context.pointee),
            file: Self.fileFields.capture(context.pointee.save),
            nextHandle: nextHandle, lastError: lastError, fault: fault, unresolved: unresolved, failure: failure,
            entries: entries, reads: physicalReads, writes: physicalWrites, ownsManager: ownsManager)
    }

    func restoreState(_ saved: SavedState) throws {
        guard handles.isEmpty else { throw ClawSnapshotError.activeFrame }
        guard saved.manager == managerToken else { throw ClawSnapshotError.invalidState }
        var restoredContext = try Self.contextFields.restoring(saved.context, into: context.pointee)
        restoredContext.save = try Self.fileFields.restoring(saved.file, into: restoredContext.save)
        context.pointee = restoredContext
        nextHandle = saved.nextHandle
        lastError = saved.lastError
        fault = saved.fault
        unresolved = saved.unresolved
        failure = saved.failure
        entries = saved.entries
        physicalReads = saved.reads
        physicalWrites = saved.writes
        ownsManager = saved.ownsManager
    }
    private static let contextFields = ClawSnapshotFields<ClawSaveLoadContext>(fields: [
        .init("directoryScratchToken", \.directoryScratchToken),
        .init("maximumTraversal", \.maximumTraversal),
        .init("fault", \.fault),
    ])
    private static let fileFields = ClawSnapshotFields<ClawSaveFileContext>(fields: [
        .init("emptyStringToken", \.emptyStringToken),
        .init("fileScratchToken", \.fileScratchToken),
        .init("pathScratchToken", \.pathScratchToken),
        .init("securityScratchToken", \.securityScratchToken),
        .init("countScratchToken", \.countScratchToken),
        .init("maximumTraversal", \.maximumTraversal),
        .init("maximumSteps", \.maximumSteps),
        .init("fault", \.fault),
    ])
}
