import Foundation

// Per-movie physical ownership. AVPlayer completion and the save-file namespace
// are independent. Game flags belong exclusively to MovieStateCleanupRuntime.
final class ClawNativeMovieStateServices {
    enum Failure: Error { case missingOwner, staleOwner, invalidCall, close, reset, runtime }
    private final class Binding {
        let identity: ClawTokenHeap.AllocationIdentity
        var file: FileHandle?
        let handleToken: UInt32
        var data: UInt32
        let bytes: UInt32
        let dataIdentity: ClawTokenHeap.AllocationIdentity?
        init(identity: ClawTokenHeap.AllocationIdentity, file: FileHandle?, handleToken: UInt32, data: UInt32,
             bytes: UInt32, dataIdentity: ClawTokenHeap.AllocationIdentity?) {
            self.identity = identity; self.file = file; self.handleToken = handleToken; self.data = data
            self.bytes = bytes; self.dataIdentity = dataIdentity
        }
    }
    let heap: ClawTokenHeap
    private let closeFile: (FileHandle) throws -> Void
    private var bindings: [UInt32: Binding] = [:]
    func ownsArray(_ receiver:UInt32)->Bool {receiver >= 0x138 && bindings[receiver-0x138] != nil}

    init(heap: ClawTokenHeap, closeFile: @escaping (FileHandle) throws -> Void = { try $0.close() }) {
        self.heap = heap
        self.closeFile = closeFile
    }

    // Called by the native resource owner after construction/open. Ownership of
    // the file and exact array allocation transfers here; no game flag changes.
    func bind(movie: UInt32, file: FileHandle?, array: UInt32, arrayBytes: UInt32) throws {
        guard bindings[movie] == nil,
              let identity = heap.containingAllocationIdentity(at: movie, count: 0x14c),
              let state = heap.lookup(movie, words: 0x14c / 4),
              state[0x124 / 4] == 0x510844,
              state[0x130 / 4] == 0x52e1c4,
              state[0x13c / 4] == array,
              (array == 0 && arrayBytes == 0) ||
                (array != 0 && arrayBytes > 0 && heap.allocationIdentity(at: array, count: arrayBytes) != nil),
              (state[0x128 / 4] == .max) == (file == nil) else { throw Failure.staleOwner }
        // The file and array cannot alias the containing movie allocation.
        let dataIdentity = heap.allocationIdentity(at: array, count: arrayBytes)
        guard dataIdentity !== identity else { throw Failure.staleOwner }
        for existing in bindings.values {
            guard dataIdentity == nil || existing.dataIdentity !== dataIdentity,
                  file == nil || existing.file !== file else { throw Failure.staleOwner }
        }
        bindings[movie] = Binding(identity: identity, file: file, handleToken: state[0x128 / 4], data: array,
                                  bytes: arrayBytes, dataIdentity: dataIdentity)
    }

    // Exact addressed service route shared by canonical and legacy callers.
    // A thrown error must be published as a host fault, never a false game bool.
    func service(_ function: UInt32, receiver: UInt32, arguments: [UInt32]) throws -> UInt32 {
        let offset: UInt32
        switch function {
        case 0x4f766e:
            guard arguments.isEmpty else { throw Failure.invalidCall }
            offset = 0x124
        case 0x4f5915:
            guard arguments == [0, .max] else { throw Failure.invalidCall }
            offset = 0x138
        default: throw Failure.invalidCall
        }
        guard receiver >= offset, let binding = bindings[receiver - offset] else { throw Failure.missingOwner }
        let movie = receiver - offset
        guard heap.containingAllocationIdentity(at: movie, count: 0x14c) === binding.identity,
              let state = heap.lookup(movie, words: 0x14c / 4) else { throw Failure.staleOwner }
        if function == 0x4f766e {
            guard state[0x124 / 4] == 0x510844,
                  state[0x128 / 4] == (binding.file == nil ? .max : binding.handleToken),
                  state[0x130 / 4] == 0x52e1c4 else { throw Failure.staleOwner }
            var failed = false
            if let file = binding.file {
                do { try closeFile(file); binding.file = nil }
                catch { failed = true }
            }
            // Physical close failure still leaves these platform-owned stores,
            // as in the reviewed boundary; subsequent game stores must stop.
            state[0x128 / 4] = .max
            state[0x12c / 4] = 0
            state[0x130 / 4] = 0x52e1c4
            if failed { throw Failure.close }
        } else {
            guard state[0x13c / 4] == binding.data else { throw Failure.staleOwner }
            if binding.data != 0 {
                guard heap.allocationIdentity(at: binding.data, count: binding.bytes) === binding.dataIdentity else {
                    throw Failure.reset
                }
                heap.free(binding.data)
                binding.data = 0
            }
            state[0x13c / 4] = 0
            state[0x144 / 4] = 0
            state[0x140 / 4] = 0
        }
        return 0 // Both physical services are semantic void.
    }

    private final class Invocation {
        let owner: ClawNativeMovieStateServices
        let host = UnsafeMutablePointer<ClawHost>.allocate(capacity: 1)
        var error: Error?
        init(_ owner: ClawNativeMovieStateServices) {
            self.owner = owner
            host.initialize(to: ClawHost())
            host.pointee.user = Unmanaged.passUnretained(self).toOpaque()
            host.pointee.bytes = { user, token, count in
                guard let user else { return nil }
                return Unmanaged<Invocation>.fromOpaque(user).takeUnretainedValue().owner.heap.lookupBytes(token, count: count)
            }
            host.pointee.call = { user, call in
                guard let user, let call else { return 0 }
                let invocation = Unmanaged<Invocation>.fromOpaque(user).takeUnretainedValue()
                let value = call.pointee
                let arguments = withUnsafeBytes(of: value.arguments) {
                    Array($0.bindMemory(to: UInt32.self).prefix(Int(value.argumentCount)))
                }
                do { return try invocation.owner.service(value.function, receiver: value.receiver, arguments: arguments) }
                catch {
                    invocation.error = error
                    invocation.host.pointee.fault = UInt32(CLAW_FAULT_HOST)
                    invocation.host.pointee.faultAddress = value.function
                    return 0
                }
            }
        }
        deinit { host.deinitialize(count: 1); host.deallocate() }
    }

    private func invoke(_ function: UInt32, movie: UInt32) throws -> UInt32 {
        let invocation = Invocation(self)
        var result: UInt32 = 0
        let completed = heap.withStableFreedStorage {
            claw_movie_state_cleanup_entry(function, movie, nil, 0, invocation.host, &result)
        }
        guard completed == 1 && invocation.host.pointee.fault == 0 else {
            throw invocation.error ?? Failure.runtime
        }
        return result
    }

    func stop(movie: UInt32) throws -> Bool { try invoke(0x4efd00, movie: movie) != 0 }
    func cleanup(movie: UInt32) throws { _ = try invoke(0x4efcd0, movie: movie) }

    // Retire only an already-clean native owner; caller controls its lifetime.
    func retire(movie: UInt32) throws {
        guard let binding = bindings[movie], binding.file == nil, binding.data == 0 else {
            throw Failure.staleOwner
        }
        bindings.removeValue(forKey: movie)
    }
}
