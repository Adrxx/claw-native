// This must fail strict-concurrency typechecking: raw runtime cannot return to UI.
final class NonSendableRuntime { var value = 0 }
func escapeState(_ lane: ClawNativeExecutionLane<NonSendableRuntime>) async throws {
    _ = try await lane.perform { state, _ in state }
}
