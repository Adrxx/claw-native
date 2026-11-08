import Foundation
import Darwin

/// A fixed OS thread for one native application lifetime. State need not be
/// Sendable: it is created, used and released only inside the thread entry.
/// Factories/jobs must not capture or publish State through an unchecked wrapper.
/// This is an execution boundary, not a source cancellation/unwind protocol.
final class ClawNativeExecutionLane<State>: Sendable {
    struct Identity: Sendable, Equatable {
        let pthread: UInt64
        let mach: UInt32
        static var current: Identity {
            Identity(pthread: UInt64(UInt(bitPattern: pthread_self())),
                     mach: pthread_mach_thread_np(pthread_self()))
        }
    }
    struct RequestID: Sendable, Hashable {
        let session: UUID
        let sequence: UInt64
    }
    /// Only owned values cross the service boundary; no borrowed span/token is
    /// dereferenced by UI. The operation's adapter defines byte/word semantics.
    struct Message: Sendable, Equatable {
        let operation: UInt32
        let bytes: [UInt8]
        let words: [UInt32]
        init(operation: UInt32, bytes: [UInt8] = [], words: [UInt32] = []) {
            self.operation = operation; self.bytes = bytes; self.words = words
        }
        fileprivate func fits(_ limit: Int) -> Bool {
            bytes.count <= limit && words.count <= (limit - bytes.count) / 4
        }
    }
    struct Request: Sendable {
        let id: RequestID
        let message: Message
    }
    enum Failure: Error, Sendable, Equatable {
        case stopped, queueFull, messageTooLarge
        case construction(String), service(String)
    }
    // Service and cancelService form one identity-scoped owner: cancellation
    // must be remembered even if presentation has not installed its resources
    // yet. A service that ignores cancellation can delay shutdown indefinitely.
    typealias Service = @MainActor @Sendable (Request) async throws -> Message
    typealias CancelService = @MainActor @Sendable (RequestID) async -> Void

    /// UI controllers should retain this handle and call stop from their deinit.
    /// An in-flight async perform can retain the lane, so losing a controller's
    /// reference to the lane alone does not guarantee that lane.deinit runs.
    struct StopHandle: Sendable {
        fileprivate let mailbox: Mailbox
        func stop() { mailbox.stop() }
        func shutdown() async {
            stop()
            await withCheckedContinuation { mailbox.whenExited($0) }
        }
    }
    var stopHandle: StopHandle { StopHandle(mailbox: mailbox) }

    /// Intentionally not Sendable. A synchronous source callback may park here
    /// while its own withUnsafe/C++ frames stay active. Copy replies into those
    /// frames only after request returns successfully and validate their schema.
    final class Context {
        let identity: Identity
        let session: UUID
        private let mailbox: Mailbox
        fileprivate init(_ mailbox: Mailbox) {
            self.mailbox = mailbox; identity = .current; session = mailbox.session
        }
        func assertCurrentThread() {
            precondition(identity == .current, "native state left its owning OS thread")
        }
        func checkRunning() throws {
            assertCurrentThread()
            try mailbox.checkRunning()
        }
        func request(_ message: Message) throws -> Message {
            assertCurrentThread()
            return try mailbox.request(message)
        }
    }

    fileprivate struct Job: Sendable {
        let run: @Sendable (State, Context) -> Void
        let reject: @Sendable (Failure) -> Void
    }
    private struct Pending {
        let id: RequestID
        var result: Result<Message, Failure>?
    }

    /// The only unchecked conformance: every mutable field below is protected
    /// by condition. It contains owned messages/continuations/Sendable closures,
    /// never State, an application, heap, Context, or a borrowed native pointer.
    fileprivate final class Mailbox: @unchecked Sendable {
        let session = UUID()
        private let condition = NSCondition()
        private let maxQueuedJobs: Int
        private let maxMessageBytes: Int
        private let service: Service
        private let cancelService: CancelService
        private var jobs: [Job] = []
        private var stopping: Failure?
        private var identity: Identity?
        private var readyWaiters: [CheckedContinuation<Identity, any Error>] = []
        private var exitWaiters: [CheckedContinuation<Void, Never>] = []
        private var exitIdentity: Identity?
        private var nextRequest: UInt64 = 0
        private var pending: Pending?
        private var presentations: Set<RequestID> = []
        private var tasks: [RequestID: Task<Void, Never>] = [:]
        private var cancellations = 0

        init(maxQueuedJobs: Int, maxMessageBytes: Int,
             service: @escaping Service, cancelService: @escaping CancelService) {
            self.maxQueuedJobs = maxQueuedJobs; self.maxMessageBytes = maxMessageBytes
            self.service = service; self.cancelService = cancelService
        }
        func checkRunning() throws {
            condition.lock(); let failure = stopping; condition.unlock()
            if let failure { throw failure }
        }
        fileprivate func enqueue(_ job: Job) {
            condition.lock()
            let failure: Failure?
            if let stopping { failure = stopping }
            else if jobs.count >= maxQueuedJobs { failure = .queueFull }
            else { jobs.append(job); failure = nil; condition.signal() }
            condition.unlock()
            if let failure { job.reject(failure) }
        }
        fileprivate func takeJob() -> Job? {
            condition.lock(); defer { condition.unlock() }
            while jobs.isEmpty && stopping == nil { condition.wait() }
            guard stopping == nil else { return nil }
            return jobs.removeFirst()
        }
        func whenReady(_ continuation: CheckedContinuation<Identity, any Error>) {
            condition.lock()
            let failure = stopping, readyIdentity = identity
            if failure == nil && readyIdentity == nil { readyWaiters.append(continuation) }
            condition.unlock()
            if let failure { continuation.resume(throwing: failure) }
            else if let readyIdentity { continuation.resume(returning: readyIdentity) }
        }
        func publishReady(_ value: Identity) {
            condition.lock()
            guard stopping == nil else { condition.unlock(); return }
            identity = value
            let waiters = readyWaiters; readyWaiters.removeAll()
            condition.unlock()
            for waiter in waiters { waiter.resume(returning: value) }
        }
        private func register(_ message: Message) throws -> RequestID {
            condition.lock()
            if let stopping { condition.unlock(); throw stopping }
            guard message.fits(maxMessageBytes) else {
                condition.unlock(); throw Failure.messageTooLarge
            }
            precondition(pending == nil, "only one synchronous service may be outstanding")
            precondition(nextRequest < UInt64.max, "request identity exhausted")
            nextRequest += 1
            let id = RequestID(session: session, sequence: nextRequest)
            pending = Pending(id: id)
            presentations.insert(id)
            condition.unlock()
            return id
        }
        func request(_ message: Message) throws -> Message {
            let id = try register(message)
            let task = Task { @MainActor [self] in
                defer { presentationFinished(id) }
                // Admission is the presentation start linearization point.
                guard beginPresentation(id), !Task.isCancelled else { return }
                do { complete(id, .success(try await service(Request(id: id, message: message)))) }
                catch { complete(id, .failure(.service(String(describing: error)))) }
            }
            condition.lock()
            if presentations.contains(id) { tasks[id] = task }
            let cancel = stopping != nil
            condition.unlock()
            if cancel { task.cancel() }
            return try waitForReply(id)
        }
        private func waitForReply(_ id: RequestID) throws -> Message {
            condition.lock()
            precondition(pending?.id == id)
            // Result is a predicate, not a notification: completion before wait
            // and spurious wakeups cannot lose a reply. Stop wins at this boundary.
            while pending?.result == nil && stopping == nil { condition.wait() }
            let result: Result<Message, Failure>
            if let stopping { result = .failure(stopping) }
            else { result = pending!.result! }
            pending = nil
            condition.unlock()
            return try result.get()
        }
        private func beginPresentation(_ id: RequestID) -> Bool {
            condition.lock(); defer { condition.unlock() }
            return stopping == nil && pending?.id == id && presentations.contains(id)
        }
        /// Identity and terminal-state checks also reject late/duplicate replies.
        fileprivate func complete(_ id: RequestID, _ result: Result<Message, Failure>) {
            condition.lock(); defer { condition.unlock() }
            guard stopping == nil, pending?.id == id, pending?.result == nil else { return }
            if case .success(let message) = result, !message.fits(maxMessageBytes) {
                pending?.result = .failure(.messageTooLarge)
            } else { pending?.result = result }
            condition.broadcast()
        }
        func stop(_ reason: Failure = .stopped) {
            condition.lock()
            guard stopping == nil else { condition.unlock(); return }
            stopping = reason
            let rejected = jobs; jobs.removeAll()
            let ready = readyWaiters; readyWaiters.removeAll()
            let ids = Array(presentations), activeTasks = Array(tasks.values)
            cancellations += ids.count
            condition.broadcast()
            condition.unlock()
            for job in rejected { job.reject(reason) }
            for waiter in ready { waiter.resume(throwing: reason) }
            for task in activeTasks { task.cancel() }
            for id in ids {
                Task { @MainActor [self] in
                    await cancelService(id)
                    cancellationFinished()
                }
            }
        }
        private func presentationFinished(_ id: RequestID) {
            condition.lock()
            presentations.remove(id); tasks.removeValue(forKey: id)
            let waiters = drainWaiters()
            condition.unlock()
            for waiter in waiters { waiter.resume() }
        }
        private func cancellationFinished() {
            condition.lock(); cancellations -= 1
            let waiters = drainWaiters()
            condition.unlock()
            for waiter in waiters { waiter.resume() }
        }
        func threadFinished() {
            let value = Identity.current
            condition.lock()
            precondition(identity == nil || identity == value)
            exitIdentity = value
            let waiters = drainWaiters()
            condition.unlock()
            for waiter in waiters { waiter.resume() }
        }
        private func drainWaiters() -> [CheckedContinuation<Void, Never>] {
            guard exitIdentity != nil && presentations.isEmpty && cancellations == 0 else { return [] }
            let waiters = exitWaiters; exitWaiters.removeAll(); return waiters
        }
        func whenExited(_ continuation: CheckedContinuation<Void, Never>) {
            condition.lock()
            exitWaiters.append(continuation)
            let waiters = drainWaiters()
            condition.unlock()
            for waiter in waiters { waiter.resume() }
        }
    }

    private let mailbox: Mailbox
    init(maxQueuedJobs: Int = 64, maxMessageBytes: Int = 1_048_576,
         service: @escaping Service,
         cancelService: @escaping CancelService,
         makeState: @escaping @Sendable (Context) throws -> State) {
        precondition(maxQueuedJobs > 0 && maxMessageBytes >= 0)
        let mailbox = Mailbox(maxQueuedJobs: maxQueuedJobs, maxMessageBytes: maxMessageBytes,
                              service: service, cancelService: cancelService)
        self.mailbox = mailbox
        let thread = Thread {
            // No State is retained by the controller or a Task. The function
            // scope ends (including State deinit) before threadFinished is sent.
            autoreleasepool {
                do { try Self.runState(mailbox, makeState) }
                catch { mailbox.stop(.construction(String(describing: error))) }
            }
            mailbox.threadFinished()
        }
        thread.stackSize = 2 * 1024 * 1024
        thread.name = "Claw native application"
        thread.start()
    }
    private static func runState(_ mailbox: Mailbox,
                                 _ makeState: @Sendable (Context) throws -> State) throws {
        let context = Context(mailbox)
        try context.checkRunning()
        let state = try makeState(context)
        context.assertCurrentThread()
        mailbox.publishReady(context.identity)
        while let job = mailbox.takeJob() {
            autoreleasepool { context.assertCurrentThread(); job.run(state, context) }
        }
        context.assertCurrentThread()
        // Runtime State owns its own explicit dependency release order. This
        // release is host teardown; no original graceful destructor is implied.
    }
    func ready() async throws -> Identity {
        try await withCheckedThrowingContinuation { mailbox.whenReady($0) }
    }
    func perform<Output: Sendable>(
        _ body: @escaping @Sendable (State, Context) throws -> Output
    ) async throws -> Output {
        try await withCheckedThrowingContinuation { continuation in
            mailbox.enqueue(Job(run: { state, context in
                do { continuation.resume(returning: try body(state, context)) }
                catch { continuation.resume(throwing: error) }
            }, reject: { continuation.resume(throwing: $0) }))
        }
    }
    /// Stops admission and wakes service/idle waits immediately. Running source
    /// code must reach an audited safe point; it is never forcibly terminated.
    func stop() { mailbox.stop() }
    /// Async only: waits for State release AND UI task/cancellation acknowledgement.
    /// The service's cancel callback must terminate its identity-scoped operation.
    func shutdown() async {
        await stopHandle.shutdown()
    }
    deinit { mailbox.stop() }
}
