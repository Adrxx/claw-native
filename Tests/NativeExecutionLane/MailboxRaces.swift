// Compiled as a same-file extension of the unmodified shipping source, only in
// this executable. Directly controls ordering without production test hooks.
extension ClawNativeExecutionLane.Mailbox {
    func assertExitIdentity(_ expected: ClawNativeExecutionLane<State>.Identity) {
        condition.lock(); defer { condition.unlock() }
        precondition(exitIdentity == expected)
    }
    func queueBoundProbe(_ log: Log) {
        typealias Job = ClawNativeExecutionLane<State>.Job
        let job = Job(run: { _, _ in fatalError("root should never execute") }, reject: {
            log.add($0 == .queueFull ? "full" : "rejected")
        })
        enqueue(job); enqueue(job)
        precondition(log.count("full") == 1 && log.count("rejected") == 0)
        stop(); stop()
        precondition(log.count("full") == 1 && log.count("rejected") == 1)
        precondition(takeJob() == nil)
    }
    func completionBeforeWaitProbe() throws {
        typealias Message = ClawNativeExecutionLane<State>.Message
        typealias ID = ClawNativeExecutionLane<State>.RequestID
        let request = try register(Message(operation: 1))
        // A different application epoch and wrong sequence cannot resolve it.
        complete(ID(session: UUID(), sequence: request.sequence), .success(Message(operation: 2)))
        complete(ID(session: request.session, sequence: request.sequence + 1), .success(Message(operation: 2)))
        condition.lock(); precondition(pending?.result == nil); condition.unlock()
        complete(request, .success(Message(operation: 3, bytes: [11])))
        complete(request, .success(Message(operation: 4, bytes: [22])))
        let response = try waitForReply(request) // Completion is already latched.
        precondition(response == Message(operation: 3, bytes: [11]))
        // A returned callback's identity cannot write into the next operation.
        presentationFinished(request)
        let next = try register(Message(operation: 5))
        complete(request, .success(Message(operation: 99)))
        condition.lock(); precondition(pending?.result == nil); condition.unlock()
        complete(next, .success(Message(operation: 6)))
        let nextResponse = try waitForReply(next)
        precondition(nextResponse.operation == 6)
        presentationFinished(next)
    }
    func stopBeforePresentationProbe() throws {
        typealias Message = ClawNativeExecutionLane<State>.Message
        let id = try register(Message(operation: 1))
        stop()
        precondition(!beginPresentation(id))
        complete(id, .success(Message(operation: 123)))
        do { _ = try waitForReply(id); fatalError("stopped reply revived") }
        catch { precondition(error as? ClawNativeExecutionLane<State>.Failure == .stopped) }
        presentationFinished(id)
        do { _ = try register(Message(operation: 2)); fatalError("registered after stop") }
        catch { precondition(error as? ClawNativeExecutionLane<State>.Failure == .stopped) }
    }
}

@MainActor func mailboxRaceTests() async throws {
    let log = Log()
    let mailbox = Lane.Mailbox(maxQueuedJobs: 1, maxMessageBytes: 256,
        service: { _ in fatalError("no presentation should run") },
        cancelService: { _ in log.add("cancel") })
    try mailbox.completionBeforeWaitProbe()
    try mailbox.stopBeforePresentationProbe()
    mailbox.threadFinished()
    await withCheckedContinuation { mailbox.whenExited($0) }
    precondition(log.count("cancel") == 1)
    let bounded = Lane.Mailbox(maxQueuedJobs: 1, maxMessageBytes: 256,
        service: { _ in fatalError() }, cancelService: { _ in fatalError() })
    bounded.queueBoundProbe(log)
    bounded.threadFinished()
    await withCheckedContinuation { bounded.whenExited($0) }
}

extension ClawNativeExecutionLane {
    func assertExitedOn(_ expected: Identity) { mailbox.assertExitIdentity(expected) }
}
