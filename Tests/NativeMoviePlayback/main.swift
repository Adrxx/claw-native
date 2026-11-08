import AVFoundation
import CoreVideo
import Foundation

@main struct MoviePlaybackCheck {
    enum CheckFailure: Error { case timedOut(String), missingFrame }
    @MainActor static func wait(_ label: String, seconds: Double = 12, until test: () -> Bool) async throws {
        let deadline = Date().addingTimeInterval(seconds)
        while !test() {
            if Date() >= deadline { throw CheckFailure.timedOut(label) }
            try await Task.sleep(nanoseconds: 10_000_000)
        }
    }
    @MainActor static func begin(_ service: ClawNativeMoviePlayback, id: UInt32, file: URL) async throws
        -> (Task<ClawNativeMoviePlayback.Outcome, Error>, AVPlayerItem, AVPlayerItemVideoOutput) {
        let task = Task { try await service.play(movieID: id, file: file) }
        try await wait("item") { service.player.currentItem != nil }
        let item = service.player.currentItem!
        let output = AVPlayerItemVideoOutput(pixelBufferAttributes: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
        item.add(output)
        try await wait("ready") { service.ready }
        var frame: CVPixelBuffer?
        try await wait("first decoded frame") {
            let time = service.player.currentTime()
            if output.hasNewPixelBuffer(forItemTime: time) {
                frame = output.copyPixelBuffer(forItemTime: time, itemTimeForDisplay: nil)
            }
            return frame != nil && service.player.timeControlStatus == .playing
        }
        precondition(CVPixelBufferGetWidth(frame!) == (id == 1 ? 640 : 320))
        precondition(CVPixelBufferGetHeight(frame!) == 240)
        return (task, item, output)
    }
    @MainActor static func main() async throws {
        precondition(CommandLine.arguments.count == 4)
        let logo = URL(fileURLWithPath: CommandLine.arguments[1])
        let intro = URL(fileURLWithPath: CommandLine.arguments[2])
        let catalog = try ClawNativeMovieCatalog(directory: URL(fileURLWithPath: CommandLine.arguments[3]))
        let catalogLogo = try catalog.file(movieID: 1), catalogIntro = try catalog.file(movieID: 2)
        precondition(catalogLogo.standardizedFileURL == logo.standardizedFileURL)
        precondition(catalogIntro.standardizedFileURL == intro.standardizedFileURL)
        do { _ = try catalog.file(movieID: 3); preconditionFailure("missing originalID selected another movie") }
        catch ClawNativeMovieCatalog.Failure.notPrepared(3) {}
        let service = ClawNativeMoviePlayback()
        do {
            _ = try await service.play(movieID: 1, file: logo.deletingLastPathComponent().appendingPathComponent("missing-movie.mp4"))
            preconditionFailure("missing file succeeded")
        } catch ClawNativeMoviePlayback.Failure.missingFile {}
        precondition(service.movieID == nil && service.player.currentItem == nil)

        let (logoTask, logoItem, logoOutput) = try await begin(service, id: 1, file: logo)
        precondition(service.movieID == 1)
        do {
            _ = try await service.play(movieID: 2, file: intro)
            preconditionFailure("concurrent movie succeeded")
        } catch ClawNativeMoviePlayback.Failure.alreadyPlaying {}
        precondition(service.player.currentItem === logoItem)
        let duration = try await logoItem.asset.load(.duration)
        await withCheckedContinuation { (done: CheckedContinuation<Void, Never>) in
            service.player.seek(to: CMTimeSubtract(duration, CMTime(seconds: 0.15, preferredTimescale: 100000)),
                toleranceBefore: .zero, toleranceAfter: .zero) { _ in done.resume() }
        }
        // Actual AVPlayer end notification after the final native decoded frames.
        try await wait("natural end") { service.movieID == nil }
        let logoResult = try await logoTask.value
        precondition(logoResult == .finished)
        precondition(!service.ready && service.player.currentItem == nil)
        _ = logoOutput

        let (introTask, oldItem, introOutput) = try await begin(service, id: 2, file: intro)
        // Queue an old completion, then explicitly skip and replace the owner.
        NotificationCenter.default.post(name: AVPlayerItem.didPlayToEndTimeNotification, object: oldItem)
        service.skip(); service.skip()
        let introResult = try await introTask.value
        precondition(introResult == .skipped)
        let (cancelTask, newItem, cancelOutput) = try await begin(service, id: 1, file: logo)
        NotificationCenter.default.post(name: AVPlayerItem.failedToPlayToEndTimeNotification, object: oldItem)
        try await Task.sleep(nanoseconds: 50_000_000)
        precondition(service.movieID == 1 && service.player.currentItem === newItem)
        cancelTask.cancel()
        do { _ = try await cancelTask.value; preconditionFailure("cancel advanced movie") }
        catch is CancellationError {}
        precondition(service.movieID == nil && service.player.currentItem == nil && !service.ready)
        _ = introOutput; _ = cancelOutput

        let corrupt = logo.deletingLastPathComponent().appendingPathComponent("playback-check-invalid.mp4")
        try Data("invalid movie".utf8).write(to: corrupt)
        defer { try? FileManager.default.removeItem(at: corrupt) }
        do { _ = try await service.play(movieID: 1, file: corrupt); preconditionFailure("corrupt movie succeeded") }
        catch ClawNativeMoviePlayback.Failure.playback {}
        precondition(service.movieID == nil && service.player.currentItem == nil)
        let final = Task { try await service.play(movieID: 1, file: logo) }
        try await wait("replacement after decode failure") { service.ready }
        service.cancel()
        do { _ = try await final.value; preconditionFailure("owner cancellation succeeded") }
        catch is CancellationError {}
        print("{\"status\":\"pass\",\"scope\":\"Native AVPlayer first frames for logo+intro, actual natural end, busy rejection, skip, stale callbacks, task/owner cancellation, corrupt decode and owner reuse. No onscreen/iPad or original scene-flow claim.\"}")
    }
}
