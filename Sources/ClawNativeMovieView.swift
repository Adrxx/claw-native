import AVFoundation
import SwiftUI
import UIKit

// The native video layer fills the viewport the caller sizes (the original's
// 4:3 screen) without changing stored resolution or frame cadence.
@MainActor struct ClawNativeMovieView: View {
    @ObservedObject var playback: ClawNativeMoviePlayback
    var allowsSkipping: Bool

    var body: some View {
        MovieSurface(player: playback.player)
            .background(.black)
            .overlay(alignment: .bottomTrailing) {
                if allowsSkipping && playback.movieID != nil {
                    Button("Skip") { playback.skip() }
                        .buttonStyle(.borderedProminent)
                        .accessibilityIdentifier("claw-movie-skip")
                        .padding()
                }
            }
            .onDisappear { playback.cancel() }
    }
}

private struct MovieSurface: UIViewRepresentable {
    let player: AVPlayer
    func makeUIView(context: Context) -> Surface {
        let view = Surface()
        view.backgroundColor = .black
        view.video.videoGravity = .resize
        view.video.player = player
        return view
    }
    func updateUIView(_ view: Surface, context: Context) { view.video.player = player }
    static func dismantleUIView(_ view: Surface, coordinator: ()) { view.video.player = nil }

    final class Surface: UIView {
        override class var layerClass: AnyClass { AVPlayerLayer.self }
        var video: AVPlayerLayer { layer as! AVPlayerLayer }
    }
}
