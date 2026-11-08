import Foundation
import Darwin

typealias Lane = ClawNativeExecutionLane<Runtime>

// Test synchronization owns values only. Never contains runtime/source pointers.
final class Log: @unchecked Sendable {
    private let lock = NSLock()
    private var entries: [String] = []
    func add(_ value: String) { lock.lock(); entries.append(value); lock.unlock() }
    func count(_ value: String) -> Int {
        lock.lock(); defer { lock.unlock() }; return entries.filter { $0 == value }.count
    }
}
final class Runtime {
    let context: Lane.Context
    let log: Log
    let heap: ClawTokenHeap
    var random: ClawNativeRandom?
    let threadToken: UInt32
    var expectedSeed: UInt32 = 123
    init(_ context: Lane.Context, _ log: Log) {
        context.assertCurrentThread(); self.context = context; self.log = log
        heap = ClawTokenHeap()
        random = ClawNativeRandom(heap: heap)
        precondition(random!.initialized)
        threadToken = random!.threadToken
        precondition(heap.lookup(threadToken, words: 1)!.pointee == context.identity.mach)
        random!.call(0x4a3040, arguments: [expectedSeed])
        log.add("constructed")
    }
    func draw() -> UInt32 {
        context.assertCurrentThread()
        precondition(random!.threadToken == threadToken)
        expectedSeed = expectedSeed &* 214013 &+ 2531011
        let value = random!.call(0x4a3050)
        precondition(value == (expectedSeed >> 16) & 0x7fff)
        precondition(random!.seedPointer!.pointee == expectedSeed)
        log.add("draw"); return value
    }
    deinit {
        context.assertCurrentThread()
        precondition(random!.threadToken == threadToken)
        random = nil // CRT cleanup must run on its original TLS thread, before heap.
        precondition(heap.lookup(threadToken, words: 1) == nil)
        log.add("destroyed")
    }
    func borrowed(_ call: UnsafeMutablePointer<LaneBorrowedCall>) -> Int32 {
        context.assertCurrentThread(); log.add("borrow-enter")
        let descriptor = call.pointee
        precondition(descriptor.alias == descriptor.inner! + 3)
        let payload = Lane.Message(operation: 7,
            bytes: Array(UnsafeBufferPointer(start: descriptor.outer, count: 21)) +
                   Array(UnsafeBufferPointer(start: descriptor.inner, count: 13)),
            words: [descriptor.outerBytes, descriptor.innerBytes])
        do {
            let response = try context.request(payload)
            context.assertCurrentThread()
            precondition(response.operation == 7 && response.bytes.count == 34)
            // All raw pointers remain in this active synchronous callback. UI
            // sees owned copies; schema validation precedes borrowed writes.
            for i in 1..<20 { descriptor.outer![i] = response.bytes[i] }
            for i in 1..<12 { descriptor.inner![i] = response.bytes[21 + i] }
            precondition(descriptor.alias![0] == 0x43)
            log.add("borrow-return"); return 1
        } catch {
            precondition(error as? Lane.Failure == .stopped)
            log.add("borrow-cancel"); return -1
        }
    }
}
let borrowedCallback: LaneBorrowCallback = { user, call in
    Unmanaged<Runtime>.fromOpaque(user!).takeUnretainedValue().borrowed(call!)
}

@MainActor
final class ServiceOwner {
    var pending: [Lane.RequestID: CheckedContinuation<Lane.Message, any Error>] = [:]
    var requests: [Lane.Request] = []
    var cancelled: [Lane.RequestID] = []
    var immediate = false
    var fail = false
    var oversized = false
    var cancellationGate: CheckedContinuation<Void, Never>?
    var delayCancellation = false
    func service(_ request: Lane.Request) async throws -> Lane.Message {
        requests.append(request)
        if fail { throw Lane.Failure.service("fixture failure") }
        if oversized { return Lane.Message(operation: 9, bytes: Array(repeating: 1, count: 257)) }
        if immediate { return request.message }
        return try await withCheckedThrowingContinuation { pending[request.id] = $0 }
    }
    func cancel(_ id: Lane.RequestID) async {
        cancelled.append(id)
        pending.removeValue(forKey: id)?.resume(throwing: CancellationError())
        if delayCancellation {
            await withCheckedContinuation { cancellationGate = $0 }
        }
    }
    func finish(_ id: Lane.RequestID) {
        guard let continuation = pending.removeValue(forKey: id) else { return }
        var bytes = Array(repeating: UInt8(0), count: 34)
        for i in 1..<20 { bytes[i] = UInt8(0x20 + i) }
        for i in 1..<12 { bytes[21 + i] = UInt8(0x40 + i) }
        continuation.resume(returning: Lane.Message(operation: 7, bytes: bytes))
    }
}

// This is the required owner pattern: async operations may retain Lane, while
// controller teardown sends stop through a handle independent of that lifetime.
@MainActor final class Controller {
    let execution: Lane
    nonisolated let stopHandle: Lane.StopHandle
    init(_ execution: Lane) { self.execution = execution; stopHandle = execution.stopHandle }
    deinit { stopHandle.stop() }
}

@main struct Tests {
    @MainActor static func until(_ label: String, _ predicate: () -> Bool) async {
        for _ in 0..<5000 {
            if predicate() { return }
            try! await Task.sleep(nanoseconds: 1_000_000)
        }
        fatalError("timeout: \(label)")
    }
    @MainActor static func lane(_ log: Log, _ ui: ServiceOwner,
                               limit: Int = 64,
                               factory: (@Sendable (Lane.Context) throws -> Runtime)? = nil) -> Lane {
        Lane(maxQueuedJobs: limit, maxMessageBytes: 256,
             service: { try await ui.service($0) },
             cancelService: { await ui.cancel($0) },
             makeState: factory ?? { Runtime($0, log) })
    }
    @MainActor static func expectStopped<T>(_ task: Task<T, any Error>) async {
        do { _ = try await task.value; fatalError("expected stopped") }
        catch { precondition(error as? Lane.Failure == .stopped) }
    }
    @MainActor static func parkedBorrow(cancel: Bool) async throws {
        let log = Log(), ui = ServiceOwner(), worker = lane(log, ServiceOwner())
        // Separate worker above checks idle shutdown with no presentation.
        _ = try await worker.ready(); await worker.shutdown()
        precondition(log.count("destroyed") == 1)
        let runLog = Log(), execution = lane(runLog, ui)
        let identity = try await execution.ready()
        precondition(identity != Lane.Identity.current)
        _ = try await execution.perform { state, context in
            precondition(context.identity == identity); return state.draw()
        }
        let job = Task {
            try await execution.perform { state, context in
                precondition(context.identity == identity)
                let token = state.heap.allocate(bytes: 21)
                let borrowed = state.heap.lookupBytes(token, count: 21)!
                borrowed[3] = 0x7a
                let result = state.heap.withStableFreedStorage {
                    state.heap.free(token)
                    precondition(state.heap.lookupBytes(token, count: 1) == nil)
                    let value = lane_borrow_probe(Unmanaged.passUnretained(state).toOpaque(), borrowedCallback, cancel ? -1 : 1)
                    precondition(borrowed[3] == 0x7a)
                    return value
                }
                if !cancel { _ = state.draw() }
                return result
            }
        }
        await until("UI presentation") { ui.pending.count == 1 }
        precondition(runLog.count("borrow-return") == 0 && runLog.count("destroyed") == 0)
        let id = ui.requests[0].id
        // Actual MainActor suspension/resumption while the C++ stack is parked.
        var heartbeats = 0
        for _ in 0..<8 {
            try await Task.sleep(nanoseconds: 1_000_000); heartbeats += 1
            precondition(runLog.count("borrow-return") == 0)
        }
        precondition(heartbeats == 8)
        let queued = Task { try await execution.perform { state, _ in state.log.add("queued"); return 1 } }
        await Task.yield()
        precondition(runLog.count("queued") == 0)
        if cancel {
            ui.delayCancellation = true
            execution.stop(); execution.stop()
            let shutdown = Task { await execution.shutdown(); runLog.add("shutdown") }
            await until("cancel acknowledgement gate") { ui.cancellationGate != nil }
            let result = try await job.value; precondition(result == 2)
            await expectStopped(queued)
            await until("source deinit") { runLog.count("destroyed") == 1 }
            precondition(runLog.count("shutdown") == 0)
            ui.finish(id); ui.finish(id) // stale/double service completion does nothing.
            ui.cancellationGate!.resume(); ui.cancellationGate = nil
            await shutdown.value
            precondition(ui.cancelled == [id] && runLog.count("borrow-cancel") == 1)
        } else {
            ui.finish(id); ui.finish(id)
            let result = try await job.value; precondition(result == 2)
            let queuedResult = try await queued.value; precondition(queuedResult == 1)
            _ = try await execution.perform { state, context in
                precondition(context.identity == identity); return state.draw()
            }
            await execution.shutdown()
            precondition(runLog.count("draw") == 3 && runLog.count("borrow-return") == 1)
        }
        precondition(runLog.count("constructed") == 1 && runLog.count("destroyed") == 1)
        execution.assertExitedOn(identity)
    }
    @MainActor static func stopBeforeRegister() async throws {
        let log = Log(), ui = ServiceOwner()
        let gate = DispatchSemaphore(value: 0)
        let execution = lane(log, ui, factory: { context in
            let state = Runtime(context, log)
            log.add("factory-wait")
            precondition(gate.wait(timeout: .now() + 5) == .success)
            do { _ = try context.request(Lane.Message(operation: 1)); fatalError("registered after stop") }
            catch { precondition(error as? Lane.Failure == .stopped) }
            return state
        })
        await until("factory wait") { log.count("factory-wait") == 1 }
        execution.stop(); gate.signal(); await execution.shutdown()
        precondition(ui.requests.isEmpty && ui.cancelled.isEmpty && log.count("destroyed") == 1)
        await expectStopped(Task { try await execution.ready() })
        await expectStopped(Task { try await execution.perform { _, _ in 1 } })
    }
    @MainActor static func immediateAndFailure() async throws {
        let log = Log(), ui = ServiceOwner(); ui.immediate = true
        let execution = lane(log, ui)
        _ = try await execution.ready()
        for i in 0..<100 {
            let response = try await execution.perform { state, context in
                _ = state.draw()
                return try context.request(Lane.Message(operation: UInt32(i), bytes: [1, 2, 3]))
            }
            precondition(response.operation == UInt32(i) && response.bytes == [1, 2, 3])
        }
        precondition(Set(ui.requests.map(\.id)).count == 100)
        ui.fail = true
        do { _ = try await execution.perform { _, context in try context.request(Lane.Message(operation: 9)) }; fatalError() }
        catch { guard case Lane.Failure.service = error else { fatalError("wrong service failure") } }
        ui.fail = false; ui.oversized = true
        do { _ = try await execution.perform { _, context in try context.request(Lane.Message(operation: 9)) }; fatalError() }
        catch { precondition(error as? Lane.Failure == .messageTooLarge) }
        let requestCount = ui.requests.count
        do { _ = try await execution.perform { _, context in try context.request(Lane.Message(operation: 9, words: Array(repeating: 0, count: 65))) }; fatalError() }
        catch { precondition(error as? Lane.Failure == .messageTooLarge) }
        precondition(ui.requests.count == requestCount)
        async let first: Void = execution.shutdown()
        async let second: Void = execution.shutdown()
        _ = await (first, second)
        precondition(log.count("destroyed") == 1)
    }
    @MainActor static func parkedControllerRelease() async throws {
        let log = Log(), ui = ServiceOwner()
        var owner: Controller? = Controller(lane(log, ui))
        let stopHandle = owner!.stopHandle
        _ = try await owner!.execution.ready()
        let operation = Task { [execution = owner!.execution] in
            try await execution.perform { state, _ in
                lane_borrow_probe(Unmanaged.passUnretained(state).toOpaque(), borrowedCallback, -1)
            }
        }
        await until("controller-owned presentation") { ui.pending.count == 1 }
        owner = nil // Task still retains Lane; Controller deinit sends stop.
        let result = try await operation.value
        precondition(result == 2)
        await stopHandle.shutdown()
        precondition(log.count("destroyed") == 1 && log.count("borrow-cancel") == 1)
        precondition(ui.pending.isEmpty && ui.cancelled.count == 1)
    }
    @MainActor static func creationFailureAndOwnerRelease() async throws {
        let log = Log(), ui = ServiceOwner()
        let failed = lane(log, ui, factory: { _ in throw Lane.Failure.service("factory fixture") })
        do { _ = try await failed.ready(); fatalError("factory failure became ready") }
        catch { guard case Lane.Failure.construction = error else { fatalError("wrong construction failure") } }
        await failed.shutdown()
        precondition(log.count("constructed") == 0)
        var idle: Lane? = lane(log, ui)
        _ = try await idle!.ready()
        idle = nil
        await until("owner deinit stops idle thread") { log.count("destroyed") == 1 }
    }
    @MainActor static func completionStopRaces() async throws {
        for _ in 0..<40 {
            let log = Log(), ui = ServiceOwner()
            let worker = lane(log, ui)
            _ = try await worker.ready()
            let job = Task { try await worker.perform { _, context in
                try context.request(Lane.Message(operation: 7))
            } }
            await until("race presentation") { ui.pending.count == 1 }
            let id = ui.requests[0].id
            ui.finish(id)
            worker.stop(); worker.stop()
            do { _ = try await job.value }
            catch { precondition(error as? Lane.Failure == .stopped) }
            await worker.shutdown()
            precondition(log.count("destroyed") == 1 && ui.pending.isEmpty)
        }
    }
    @MainActor static func main() async throws {
        try await mailboxRaceTests()
        try await parkedBorrow(cancel: false)
        try await parkedBorrow(cancel: true)
        try await stopBeforeRegister()
        try await immediateAndFailure()
        try await creationFailureAndOwnerRelease()
        try await parkedControllerRelease()
        try await completionStopRaces()
        print("native-execution-lane: borrowed C++ scopes, RNG TLS, MainActor responsiveness, stop, bounds and teardown passed")
    }
}
