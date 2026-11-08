import Foundation

// Prepared media retain the original container's numeric movie identities.
// Availability does not decide whether an original state should play a movie.
struct ClawNativeMovieCatalog {
    enum Failure: Error, Equatable { case invalidManifest, missingFile, notPrepared(UInt32) }
    private struct Entry: Decodable {
        let movieID: UInt32
        let file: String
        let width: Int
        let height: Int
    }
    private struct Manifest: Decodable {
        let schema: Int
        let originalMovieCount: UInt32
        let entries: [Entry]
    }
    private let movies: [UInt32: URL]

    init(directory: URL) throws {
        let manifest = try JSONDecoder().decode(Manifest.self,
            from: Data(contentsOf: directory.appendingPathComponent("movies.json")))
        guard directory.isFileURL, manifest.schema == 1, manifest.originalMovieCount == 12 else {
            throw Failure.invalidManifest
        }
        var urls: [UInt32: URL] = [:]
        for entry in manifest.entries {
            guard entry.movieID > 0, entry.movieID <= manifest.originalMovieCount,
                  urls[entry.movieID] == nil, entry.width > 0, entry.height > 0,
                  !entry.file.isEmpty, !entry.file.contains("/"), !entry.file.contains("\\"),
                  entry.file != ".", entry.file != "..", entry.file.hasSuffix(".mp4") else {
                throw Failure.invalidManifest
            }
            let url = directory.appendingPathComponent(entry.file)
            var isDirectory: ObjCBool = false
            guard FileManager.default.fileExists(atPath: url.path, isDirectory: &isDirectory), !isDirectory.boolValue else {
                throw Failure.missingFile
            }
            urls[entry.movieID] = url
        }
        movies = urls
    }
    func file(movieID: UInt32) throws -> URL {
        guard let url = movies[movieID] else { throw Failure.notPrepared(movieID) }
        return url
    }
}
