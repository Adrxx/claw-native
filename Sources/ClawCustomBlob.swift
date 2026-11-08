/// Plans the release Blob effect for an indexed target whose RGB masks are zero.
/// Its component tables contain zero, but its stores remain packed 16-bit
/// stores. Build the complete plan before touching the target surface.
enum ClawCustomBlob {
    private struct Invalid: Error {}
    private struct Run {
        let count: Int
        let literal: Bool
        let start: Int
    }

    static func ranges(payload: [UInt8], width: Int, height: Int,
                       source: [Int], destination: [Int], pitch: Int,
                       capacity: Int, flipX: Bool, flipY: Bool,
                       paired: Bool) -> [Range<Int>]? {
        guard (1...4096).contains(width), (1...4096).contains(height),
              !payload.isEmpty, payload.count <= 0x2000000,
              (1...0x2000000).contains(pitch), (1...0x2000000).contains(capacity),
              source.count == 4, destination.count == 4,
              (source + destination).allSatisfy({ Int(Int32.min)...Int(Int32.max) ~= $0 }),
              source[0] >= 0, source[0] < width,
              source[1] >= 0, source[1] < height,
              source[2] < width, source[3] < height else { return nil }

        var cursor = 0
        var steps = 0
        var result: [Range<Int>] = []
        func nextRun() throws -> Run {
            steps += 1
            guard steps <= 20_000_000, cursor < payload.count else { throw Invalid() }
            let byte = Int(payload[cursor])
            cursor += 1
            let literal = byte < 128
            let count = literal ? byte : byte - 128
            guard count > 0, !literal || count <= payload.count - cursor else { throw Invalid() }
            let run = Run(count: count, literal: literal, start: cursor)
            if literal { cursor += count }
            return run
        }
        func bounded(_ at: Int, _ count: Int) throws -> Range<Int> {
            guard at >= 0, at <= capacity, count >= 0, count <= capacity - at else { throw Invalid() }
            return at..<(at + count)
        }
        func append(_ range: Range<Int>) {
            if let last = result.last,
               last.lowerBound <= range.upperBound, range.lowerBound <= last.upperBound {
                result[result.count - 1] = min(last.lowerBound, range.lowerBound)..<max(last.upperBound, range.upperBound)
            } else {
                result.append(range)
            }
        }
        func pixels(_ start: Int, _ anchor: Int, _ count: Int, _ row: Int) throws {
            guard count > 0 else { return }
            guard count <= 127, start >= 0, start <= payload.count,
                  count <= payload.count - start else { throw Invalid() }
            if paired && ((row + destination[1]) & 1) == 0 { return }
            // The stream consumes count bytes, while this effect reads count
            // words. The extra source reads must still stay in the payload.
            guard count * 2 <= payload.count - start else { throw Invalid() }
            let scratch = flipX ? anchor - count * 2 - 2 : anchor
            _ = try bounded(scratch, count * 2)
            let low = flipX ? anchor - (count - 1) * 2 : anchor
            append(try bounded(low, count * 2))
            if paired {
                append(try bounded(low + (pitch / 2) * 2, count * 2))
            }
        }
        do {
            // Reject malformed runs throughout the declared image, including
            // rows outside the clipping rectangle. Trailing payload is legal.
            for _ in 0..<height {
                var x = 0
                while x < width {
                    let run = try nextRun()
                    guard run.count <= width - x else { throw Invalid() }
                    x += run.count
                }
            }
            cursor = 0
            var row = 0
            var x = 0
            while row < source[1] {
                let run = try nextRun()
                x += run.count
                if x >= width { row += 1; x = 0 }
            }
            var base = (flipY ? destination[3] : destination[1]) * pitch + destination[0]
            let delta = flipY ? -pitch : pitch
            x = flipX ? width : 0
            if !flipX {
                if source[0] == 0 {
                    while row <= source[3] {
                        let run = try nextRun()
                        if run.literal {
                            let count = source[2] == width - 1 ? run.count : max(0, min(run.count, source[2] - x))
                            try pixels(run.start, base + x, count, row)
                        }
                        x += run.count
                        if x >= width { row += 1; base += delta; x = 0 }
                    }
                } else {
                    while row < source[3] {
                        if x < source[0] {
                            var run: Run
                            repeat { run = try nextRun(); x += run.count } while x < source[0]
                            if x > source[0] && run.literal {
                                let count = x - source[0]
                                try pixels(cursor - count, base, count, row)
                            }
                        }
                        if x < width {
                            let run = try nextRun()
                            if run.literal { try pixels(run.start, base + x - source[0], run.count, row) }
                            x += run.count
                        } else { row += 1; base += delta; x = 0 }
                    }
                }
            } else if source[0] != 0 {
                while row <= source[3] {
                    let run = try nextRun()
                    if run.literal {
                        try pixels(run.start, base + x - source[0], max(0, min(run.count, x - source[0])), row)
                    }
                    x -= run.count
                    if x < 1 { row += 1; base += delta; x = width }
                }
            } else if source[2] == width - 1 {
                while row <= source[3] {
                    let run = try nextRun()
                    if run.literal { try pixels(run.start, base + x, run.count, row) }
                    x -= run.count
                    if x < 1 { row += 1; base += delta; x = width }
                }
            } else {
                while (flipY ? row <= source[3] : row < source[3]) {
                    var advance = false
                    if source[2] < x {
                        var run: Run
                        repeat { run = try nextRun(); x -= run.count } while source[2] < x
                        if x >= 0 {
                            if run.literal {
                                let count = source[2] - x
                                try pixels(cursor - count, base + source[2], count, row)
                            }
                        } else { advance = true }
                    }
                    if x < 1 { advance = true }
                    if advance { row += 1; base += delta; x = width }
                    else {
                        let run = try nextRun()
                        if run.literal { try pixels(run.start, base + x, run.count, row) }
                        x -= run.count
                    }
                }
            }
            return result
        } catch { return nil }
    }
}
