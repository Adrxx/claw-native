import Foundation
import Darwin

// Whole original CRT initialization/srand/rand over the actual 29-word thread
// object. Windows TLS and LastError slots are native thread-local transports;
// game, fade and save callers share the source seed word at thread+14.
final class ClawNativeRandom {
    let heap:ClawTokenHeap
    let globals = UnsafeMutablePointer<ClawCRTRandomGlobals>.allocate(capacity:1)
    private let context = UnsafeMutablePointer<ClawCRTRandomContext>.allocate(capacity:1)
    private var values:[UInt32:UInt32] = [:],errors:[UInt32:UInt32] = [:]
    private(set) var fault:UInt32 = 0,unresolved:Set<UInt32> = []
    private(set) var calls:[UInt32:UInt64] = [:]
    private(set) var initialized = false
    init(heap:ClawTokenHeap) {
        self.heap = heap;globals.initialize(to:ClawCRTRandomGlobals());claw_crt_random_defaults(globals)
        context.initialize(to:ClawCRTRandomContext());context.pointee.globals = globals
        context.pointee.host = ClawSceneActorHost(context:Unmanaged.passUnretained(self).toOpaque(),lookup:{user,token,words in
            guard let user else { return nil };return Unmanaged<ClawNativeRandom>.fromOpaque(user).takeUnretainedValue().heap.lookup(token,words:words)
        },allocate:nil,free:nil,call:nil,readClock:nil)
        initialized = call(0x4a7d40) == 1 && fault == 0
    }
    deinit {
        // All source-owned thread allocations are released while the heap and
        // native transport still live; no access to a dying Swift scene cache.
        if initialized && fault == 0 { _ = call(0x4a7e40,arguments:[0]) }
        context.deinitialize(count:1);context.deallocate();globals.deinitialize(count:1);globals.deallocate()
    }
    @discardableResult func call(_ function:UInt32,arguments:[UInt32] = []) -> UInt32 {
        var result:UInt32 = 0;calls[function,default:0] &+= 1
        let completed = arguments.withUnsafeBufferPointer{claw_crt_random_entry(function,$0.baseAddress,UInt32($0.count),context,nativeRandomDependency,Unmanaged.passUnretained(self).toOpaque(),&result)}
        fault = max(fault,context.pointee.fault);if completed != 1 { unresolved.insert(function) };return result
    }
    var threadToken:UInt32 { call(0x4a7dc0) }
    var seedPointer:UnsafeMutablePointer<UInt32>? { heap.lookup(threadToken &+ 0x14,words:1) }
    struct SavedState: Codable, Equatable {
        let tlsIndex: UInt32
        let thread: UInt32?
        let lastError: UInt32?
        let fault: UInt32, contextFault: UInt32
        let calls: [UInt32: UInt64]
        let unresolved: Set<UInt32>
        let initialized: Bool
    }
    func savedState() throws -> SavedState {
        // This adapter represents one execution thread. Do not silently lose
        // another thread's TLS if a future caller changes that contract.
        let id = threadID
        guard values.keys.allSatisfy({ $0 == id }), errors.keys.allSatisfy({ $0 == id })
        else { throw ClawSnapshotError.invalidState }
        return SavedState(tlsIndex: globals.pointee.tlsIndex, thread: values[id], lastError: errors[id],
            fault: fault, contextFault: context.pointee.fault, calls: calls,
            unresolved: unresolved, initialized: initialized)
    }
    func restoreState(_ state: SavedState) throws {
        // The heap must already have been restored off screen. Keep original
        // thread record bytes (including its recorded ID), but bind native TLS
        // to this process's executing thread rather than the old Mach ID.
        guard state.thread.map({ heap.allocationIdentity(at: $0, count: 0x74) != nil }) ?? true,
              state.thread == nil || state.initialized,
              !state.initialized || state.tlsIndex != .max else { throw ClawSnapshotError.invalidState }
        globals.pointee.tlsIndex = state.tlsIndex
        values = state.thread.map { [threadID: $0] } ?? [:]
        errors = state.lastError.map { [threadID: $0] } ?? [:]
        fault = state.fault; context.pointee.fault = state.contextFault
        calls = state.calls; unresolved = state.unresolved; initialized = state.initialized
    }
    private var threadID:UInt32 { pthread_mach_thread_np(pthread_self()) }
    fileprivate func transport(_ call:ClawCRTRandomCall) -> UInt32 {
        let a=call.arguments.0,b=call.arguments.1,id=threadID
        switch call.function {
        case 0x4a7b90:return 1 // Native main-thread runtime lock initialization.
        case 0x546a90:return 0 // One TLS index owned by this application scope.
        case 0x546b0c:return errors[id] ?? 0
        case 0x546ab8:errors[id] = a;return 0
        case 0x5469c0:return id
        case 0x546a7c:
            guard a == globals.pointee.tlsIndex && a != .max else { errors[id] = 87;return 0 }
            errors[id] = 0;return values[id] ?? 0
        case 0x546a84:
            guard a == globals.pointee.tlsIndex && a != .max else { errors[id] = 87;return 0 }
            values[id] = b;return 1
        case 0x4adf50:
            let bytes = UInt64(a)*UInt64(b);guard bytes > 0 && bytes <= 4<<20 else { return 0 }
            return heap.allocate(bytes:UInt32(bytes))
        case 0x4a49b0:heap.free(a);return 0
        case 0x4a4860:context.pointee.fault = 1;return 0
        default:unresolved.insert(call.function);context.pointee.fault = 1;return 0
        }
    }
}
private let nativeRandomDependency:ClawCRTRandomDependency = {_,event,user in
    guard let event,let user else { return 0 };return Unmanaged<ClawNativeRandom>.fromOpaque(user).takeUnretainedValue().transport(event.pointee)
}
