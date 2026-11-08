// This must fail: a borrowed pointer cannot be the async job's result.
func escapePointer(_ lane: ClawNativeExecutionLane<Int>) async throws {
    _ = try await lane.perform { _, _ in UnsafeMutablePointer<UInt8>.allocate(capacity: 1) }
}
