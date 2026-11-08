import AVFoundation
import Combine
import Foundation

// AVFoundation is a physical playback service. Original state code must select
// the numeric movie ID and consume completion; this owner never chooses a scene.
@MainActor final class ClawNativeMoviePlayback: ObservableObject {
    enum Outcome: Equatable { case finished, skipped }
    enum Failure: Error, Equatable {
        case alreadyPlaying
        case invalidMovie
        case missingFile
        case playback
        case timeout
    }
    // Agent launches (--mute) and every deterministic check never reach the
    // speakers: the same flags that keep ClawNativeAudio's output silent.
    static let silent = ProcessInfo.processInfo.arguments.contains {
        ["--mute", "--menu-check", "--menu-live-check", "--play-script", "--fast-clock", "--new-game-clock",
         "--menu-input-script", "--music-render", "--long-trace", "--movie-check", "--movie-flow-check"].contains($0) }
    let player: AVPlayer = {
        let player = AVPlayer()
        if ClawNativeMoviePlayback.silent { player.isMuted = true; player.volume = 0 }
        return player
    }()
    /// Physical audio evidence: what the player would send to the output.
    var audioState: [String: Any] { ["silent": Self.silent, "isMuted": player.isMuted, "volume": player.volume] }
    @Published private(set) var movieID: UInt32?
    @Published private(set) var ready = false

    private struct Session {
        let id: UUID
        let item: AVPlayerItem
        let completion: (Result<Outcome, Error>) -> Void
    }
    private var session: Session?
    private var notifications: [NSObjectProtocol] = []

    // The game calls this synchronously from its frame. Starting an async Task
    // there can deadlock when the frame itself is draining the main queue:
    // pumping RunLoop does not re-enter that queue. Start immediately and let
    // the host poll while it pumps window events; async consumers use play().
    private var began = 0.0
    private var progressed = 0.0
    private var lastMediaTime = 0.0
    private var monitor: Task<Void, Never>?

    func begin(movieID: UInt32, file: URL, completion: @escaping (Result<Outcome, Error>) -> Void) throws {
        guard session == nil else { throw Failure.alreadyPlaying }
        guard movieID > 0, file.isFileURL else { throw Failure.invalidMovie }
        guard FileManager.default.fileExists(atPath: file.path) else { throw Failure.missingFile }
        let id = UUID(), item = AVPlayerItem(url: file)
        session = Session(id: id, item: item, completion: completion)
        self.movieID = movieID
        ready = false
        began = ProcessInfo.processInfo.systemUptime; progressed = began; lastMediaTime = 0
        let center = NotificationCenter.default
        notifications.append(center.addObserver(forName: AVPlayerItem.didPlayToEndTimeNotification,
            object: item, queue: .main) { [weak self] _ in
            Task { @MainActor [weak self] in self?.finish(id: id, result: .success(.finished)) }
        })
        notifications.append(center.addObserver(forName: AVPlayerItem.failedToPlayToEndTimeNotification,
            object: item, queue: .main) { [weak self] _ in
            Task { @MainActor [weak self] in self?.finish(id: id, result: .failure(Failure.playback)) }
        })
        player.actionAtItemEnd = .pause
        if Self.silent {
            player.isMuted = true; player.volume = 0
            let silence = AVMutableAudioMix()
            silence.inputParameters = item.asset.tracks(withMediaType: .audio).map {
                let parameters = AVMutableAudioMixInputParameters(track: $0); parameters.setVolume(0, at: .zero)
                return parameters
            }
            item.audioMix = silence
        }
        player.replaceCurrentItem(with: item)
        player.play()
        monitor = Task { @MainActor [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 50_000_000)
                guard let self, self.session?.id == id else { return }
                self.poll()
            }
        }
    }

    /// Also observes the item's clock: an end notification queued behind a
    /// synchronous game frame must not leave playback waiting indefinitely.
    func poll() {
        guard let session else { return }
        let item = session.item, now = ProcessInfo.processInfo.systemUptime
        if item.status == .failed { finish(id: session.id, result: .failure(Failure.playback)); return }
        let isReady = item.status == .readyToPlay
        if ready != isReady { ready = isReady }
        let media = item.currentTime().seconds, duration = item.duration.seconds
        if ready && media.isFinite && duration.isFinite && duration > 0 && media >= duration {
            finish(id: session.id, result: .success(.finished)); return
        }
        if media.isFinite && media > lastMediaTime { lastMediaTime = media; progressed = now }
        if now - progressed > 30 || now - began > (duration.isFinite && duration > 0 ? duration + 60 : 300) {
            finish(id: session.id, result: .failure(Failure.timeout))
        }
    }

    func play(movieID: UInt32, file: URL) async throws -> Outcome {
        try await withTaskCancellationHandler(operation: {
            try await withCheckedThrowingContinuation { continuation in
                guard !Task.isCancelled else { continuation.resume(throwing: CancellationError()); return }
                do { try begin(movieID: movieID, file: file) { continuation.resume(with: $0) } }
                catch { continuation.resume(throwing: error) }
            }
        }, onCancel: { [weak self] in Task { @MainActor in self?.cancel() } })
    }

    // The app's input boundary decides when skipping is permitted. Cancellation
    // is separate: abandoning an owner must not report successful movie play.
    func skip() {
        if let session { finish(id: session.id, result: .success(.skipped)) }
    }
    func cancel() {
        if let session { finish(id: session.id, result: .failure(CancellationError())) }
    }
    private func finish(id: UUID, result: Result<Outcome, Error>) {
        guard let current = session, current.id == id else { return }
        session = nil
        for token in notifications { NotificationCenter.default.removeObserver(token) }
        notifications.removeAll()
        player.pause(); player.replaceCurrentItem(with: nil)
        movieID = nil; ready = false
        monitor?.cancel(); monitor = nil
        current.completion(result)
    }
}

// Nonblocking credits backgrounds use the game's millisecond clock. Decode
// converted disc samples with AVFoundation, then transport indexed pixels to
// the existing eight-bit display (the scrolling text is drawn over this).
final class ClawNativeMovieBackground {
    // More precision in the shadows of the original credits texture. A
    // linear RGB332 cube collapses almost all of movie 12 to black.
    private static let levels = [0,5,21,47,83,130,187,255]
    private static let blues = [0,28,113,255]
    private static func nearest(_ value:Int,_ values:[Int])->UInt8 {
        var best = 0
        for i in 1..<values.count where abs(values[i]-value) < abs(values[best]-value) {best = i}
        return UInt8(best)
    }
    private static let channelIndex:[UInt8] = (0..<256).map {nearest($0,levels)}
    private static let blueIndex:[UInt8] = (0..<256).map {nearest($0,blues)}
    static let entries: Data = {
        var data = Data()
        for i in 0..<256 {
            data.append(UInt8(levels[(i >> 5) & 7]))
            data.append(UInt8(levels[(i >> 2) & 7]))
            data.append(UInt8(blues[i & 3]));data.append(0)
        }
        return data
    }()
    private let reader: AVAssetReader
    private let output: AVAssetReaderTrackOutput
    private var sample: CMSampleBuffer?
    private var next: CMSampleBuffer?
    private let duration: Double
    private var started: UInt32?
    private(set) var frames = 0
    init(file: URL) throws {
        let asset = AVURLAsset(url: file)
        guard let track = asset.tracks(withMediaType: .video).first else { throw ClawNativeMoviePlayback.Failure.playback }
        duration = asset.duration.seconds
        reader = try AVAssetReader(asset: asset)
        output = AVAssetReaderTrackOutput(track: track, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange])
        output.alwaysCopiesSampleData = false
        guard reader.canAdd(output) else { throw ClawNativeMoviePlayback.Failure.playback }
        reader.add(output)
        guard reader.startReading(), let first = output.copyNextSampleBuffer() else { throw ClawNativeMoviePlayback.Failure.playback }
        sample = first; next = output.copyNextSampleBuffer()
    }
    deinit { reader.cancelReading() }
    func frame(clock: UInt32, width: Int, height: Int) throws -> Data? {
        if started == nil { started = clock }
        let elapsed = Double(clock &- started!)/1000
        if elapsed >= duration { return nil }
        while let pending = next, CMSampleBufferGetPresentationTimeStamp(pending).seconds <= elapsed {
            sample = pending; next = output.copyNextSampleBuffer(); frames += 1
        }
        guard reader.status != .failed, let sample, let image = CMSampleBufferGetImageBuffer(sample),
              CVPixelBufferGetPlaneCount(image) == 2 else { throw ClawNativeMoviePlayback.Failure.playback }
        CVPixelBufferLockBaseAddress(image, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(image, .readOnly) }
        guard let yp = CVPixelBufferGetBaseAddressOfPlane(image, 0), let uvp = CVPixelBufferGetBaseAddressOfPlane(image, 1) else { throw ClawNativeMoviePlayback.Failure.playback }
        let w = CVPixelBufferGetWidth(image), h = CVPixelBufferGetHeight(image)
        let ys = CVPixelBufferGetBytesPerRowOfPlane(image, 0), uvs = CVPixelBufferGetBytesPerRowOfPlane(image, 1)
        let y = yp.assumingMemoryBound(to: UInt8.self), uv = uvp.assumingMemoryBound(to: UInt8.self)
        var indexed = [UInt8](repeating: 0, count: w*h)
        for row in 0..<h { for col in 0..<w {
            let c = max(0, Int(y[row*ys+col])-16), at = (row/2)*uvs+(col/2)*2
            let d = Int(uv[at])-128, e = Int(uv[at+1])-128
            let r = min(255,max(0,(298*c+409*e+128)>>8))
            let g = min(255,max(0,(298*c-100*d-208*e+128)>>8))
            let b = min(255,max(0,(298*c+516*d+128)>>8))
            indexed[row*w+col] = (Self.channelIndex[r] << 5) | (Self.channelIndex[g] << 2) | Self.blueIndex[b]
        }}
        var result = Data(count: width*height)
        result.withUnsafeMutableBytes { raw in
            let dest = raw.bindMemory(to: UInt8.self)
            for row in 0..<height { for col in 0..<width { dest[row*width+col] = indexed[(row*h/height)*w+col*w/width] } }
        }
        return result
    }
}
