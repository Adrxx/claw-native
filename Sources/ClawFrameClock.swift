import Foundation

// The UI schedule is native. Clock arithmetic and separate animation sampling
// use the recovered routines; original Windows event-loop pacing is not claimed.
final class ClawFrameClockAdapter {
    private var manager = ClawTimingManager()
    private var clock = ClawClockState()
    private var stage = ClawFrameClock()
    private var animation = ClawFrameClock()
    private var accumulated: UInt32 = 0
    private let readClock: () -> UInt32
    private var host: ClawTimingHost {
        ClawTimingHost(context: Unmanaged.passUnretained(self).toOpaque(), read: { user in
            Unmanaged<ClawFrameClockAdapter>.fromOpaque(user!).takeUnretainedValue().readClock()
        }, observeWait: nil)
    }

    init(clock: @escaping () -> UInt32 = {
        UInt32(truncatingIfNeeded: UInt64(ProcessInfo.processInfo.systemUptime * 1000))
    }) { readClock = clock; reset() }
    var snapshot: ClawClockState { clock }
    func acceptSnapshot(_ value: ClawClockState) { clock = value }
    struct SavedState: Codable, Equatable {
        let manager: Data, clock: Data, stage: Data, animation: Data
        let accumulated: UInt32
    }
    func savedState() -> SavedState {
        SavedState(manager: manager.snapshotBytes(), clock: clock.snapshotBytes(),
            stage: stage.snapshotBytes(), animation: animation.snapshotBytes(), accumulated: accumulated)
    }
    func restoreState(_ state: SavedState) throws {
        // Decode all four values before assigning any of them.
        let manager = try ClawTimingManager.fromSnapshotBytes(state.manager)
        let clock = try ClawClockState.fromSnapshotBytes(state.clock)
        let stage = try ClawFrameClock.fromSnapshotBytes(state.stage)
        let animation = try ClawFrameClock.fromSnapshotBytes(state.animation)
        self.manager = manager; self.clock = clock; self.stage = stage
        self.animation = animation; accumulated = state.accumulated
    }
    func reset() {
        clock.countdownReload = 33
        claw_timing_initialize(&manager, &clock, host)
        claw_timing_update_animation(&animation, 1, host)
        accumulated = 0
    }
    func sample() -> (stage: UInt32, animation: UInt32) {
        _ = claw_timing_update(&manager, &clock, host)
        claw_timing_publish_stage(&clock, &stage, &accumulated)
        claw_timing_update_animation(&animation, 1, host)
        return (stage.deltaMilliseconds, animation.deltaMilliseconds)
    }
    // The recovered scene owns the later animation-clock refresh/subdivision.
    // This publishes the outer stage only, avoiding a second animation update.
    func sampleScene() -> (now: UInt32, delta: UInt32, accumulated: UInt32) {
        _ = claw_timing_update(&manager, &clock, host)
        claw_timing_publish_stage(&clock, &stage, &accumulated)
        return (stage.nowMilliseconds, stage.deltaMilliseconds, accumulated)
    }
}

extension ClawTimingManager: ClawSnapshotNativeValue {}
extension ClawClockState: ClawSnapshotNativeValue {}
extension ClawFrameClock: ClawSnapshotNativeValue {}
