func escapeHeap(_ lane: ClawNativeExecutionLane<ClawNativeApplication>) async throws {
    _ = try await lane.perform { application, _ in application.heap }
}
