import Foundation

// Synthetic indexed Blob fixtures. Expected byte addresses follow the v1.3
// traversal reference; no downloaded image or level data enters this check.
@main
struct CheckCrazyHookBlob {
    static func main() throws {
        var passed: [String] = []
        func check(_ name: String, _ expected: Set<Int>?, payload: [UInt8],
                   width: Int = 2, height: Int = 1,
                   source: [Int] = [0, 0, 1, 0],
                   destination: [Int] = [4, 0, 5, 0],
                   pitch: Int = 16, capacity: Int = 64,
                   flipX: Bool = false, flipY: Bool = false, paired: Bool = false) {
            let actual = ClawCustomBlob.ranges(payload: payload, width: width, height: height,
                source: source, destination: destination, pitch: pitch, capacity: capacity,
                flipX: flipX, flipY: flipY, paired: paired)
            let bytes = actual.map { Set($0.flatMap { Array($0) }) }
            precondition(bytes == expected,
                "\(name): expected \(String(describing: expected)), got \(String(describing: bytes))")
            passed.append(name)
        }
        // A literal consumes two source bytes, but its body reads two WORDs.
        // Trailing padding therefore matters even though it is not a run.
        let row: [UInt8] = [2, 7, 8, 0, 0]
        check("normal-two-word-writes", Set(4..<8), payload: row)
        check("flip-x-word-spacing", Set(4..<8), payload: row, flipX: true)
        check("flip-y-row-base", Set(20..<24), payload: row,
              destination: [4, 1, 5, 1], flipY: true)
        // The second row starts after exactly one token plus two BYTEs. Its
        // first token is also part of the preceding body's second WORD read.
        let twoRows: [UInt8] = [2, 7, 8, 2, 9, 10, 0, 0]
        check("parser-consumes-byte-count", Set(Array(4..<8) + Array(20..<24)),
              payload: twoRows, height: 2, source: [0, 0, 1, 1],
              destination: [4, 0, 5, 1])
        check("flip-y-two-rows", Set(Array(4..<8) + Array(20..<24)),
              payload: twoRows, height: 2, source: [0, 0, 1, 1],
              destination: [4, 0, 5, 1], flipY: true)
        check("paired-even-row-skipped", [], payload: row, paired: true)
        check("paired-skip-does-not-read-words", [], payload: [2, 7, 8], paired: true)
        check("paired-odd-row-and-neighbor", Set(Array(20..<24) + Array(36..<40)),
              payload: row, destination: [4, 1, 5, 1], paired: true)
        check("paired-neighbor-rounds-pitch-down-even", Set(Array(21..<25) + Array(37..<41)),
              payload: row, destination: [4, 1, 5, 1], pitch: 17, paired: true)
        check("paired-flip-y-neighbor-still-forward", Set(Array(20..<24) + Array(36..<40)),
              payload: row, destination: [4, 1, 5, 1], flipY: true, paired: true)
        check("transparent-run-has-no-writes", [], payload: [130])
        // A transparent first BYTE advances x by one; the following literal
        // still produces a WORD, rather than ordinary indexed byte output.
        check("transparent-then-literal", Set(5..<7), payload: [129, 1, 7, 0])
        check("literal-then-transparent", Set(4..<6), payload: [1, 7, 129])

        check("reject-zero-run", nil, payload: [0])
        check("reject-row-overrun", nil, payload: [3, 7, 8, 9, 0, 0, 0])
        check("reject-missing-literal-byte", nil, payload: [2, 7])
        check("reject-body-word-read-overrun", nil, payload: [2, 7, 8])
        check("reject-body-second-word-overrun", nil, payload: [2, 7, 8, 0])
        check("reject-destination-word-overrun", nil, payload: row, capacity: 7)
        check("reject-flip-scratch-underflow", nil, payload: row,
              destination: [0, 0, 1, 0], flipX: true)
        check("reject-paired-neighbor-overrun", nil, payload: row,
              destination: [4, 1, 5, 1], capacity: 39, paired: true)
        check("reject-negative-source", nil, payload: row, source: [-1, 0, 1, 0])
        check("reject-source-past-width", nil, payload: row, source: [0, 0, 2, 0])
        check("reject-zero-width", nil, payload: row, width: 0)
        check("reject-zero-pitch", nil, payload: row, pitch: 0)

        let result: [String: Any] = ["status": "pass", "cases": passed.count, "checks": passed]
        let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
        print(String(decoding: data, as: UTF8.self))
    }
}
