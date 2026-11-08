import AVFoundation
import Foundation

@main struct BackgroundControls {
    static func main() throws {
        let directory = URL(fileURLWithPath: CommandLine.arguments[1])
        var records: [[String: Any]] = []
        for id in [11, 12] {
            let file = directory.appendingPathComponent(String(format: "movie-%02d.mp4", id))
            let duration = AVURLAsset(url: file).duration.seconds
            let movie = try ClawNativeMovieBackground(file: file)
            let start: UInt32 = 0xfffffff0
            let first = try movie.frame(clock: start, width: 640, height: 480)
            guard let first, first.count == 640*480,
                  try movie.frame(clock: start, width: 640, height: 480) == first,
                  let later = try movie.frame(clock: start &+ 1000, width: 640, height: 480), later != first,
                  try movie.frame(clock: start &+ UInt32(ceil(duration*1000)), width: 640, height: 480) == nil
            else { throw NSError(domain: "Background timing, wraparound or EOF", code: id) }
            let reopened = try ClawNativeMovieBackground(file: file)
            guard try reopened.frame(clock: 1234, width: 640, height: 480) == first else {
                throw NSError(domain: "Background reopen", code: id)
            }
            let visible = first.filter { $0 != 0 }.count
            if id == 12 && visible <= first.count/2 { throw NSError(domain: "Credits shadows collapsed to black", code: id) }
            records.append(["movie": id, "duration": duration, "timing": true, "clock_wrap": true,
                            "end_of_stream": true, "reopen": true, "pixels": first.count, "visible_pixels": visible])
        }
        guard ClawNativeMovieBackground.entries.count == 1024,
              Array(ClawNativeMovieBackground.entries.prefix(4)) == [0,0,0,0],
              Array(ClawNativeMovieBackground.entries.suffix(4)) == [255,255,255,0] else {
            throw NSError(domain: "Background palette", code: 1)
        }
        print(String(data: try JSONSerialization.data(withJSONObject: ["check": "movie-background", "status": "pass", "controls": records], options: [.sortedKeys]), encoding: .utf8)!)
    }
}
