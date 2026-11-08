import Foundation

enum AssetError: Error { case invalid(String) }

struct Bytes {
    let data: [UInt8]
    var position = 0
    mutating func take(_ count: Int) throws -> [UInt8] {
        guard count >= 0, position <= data.count, count <= data.count - position else {
            throw AssetError.invalid("Truncated asset at byte \(position)")
        }
        defer { position += count }
        return Array(data[position ..< position + count])
    }
    mutating func u16() throws -> Int {
        let b = try take(2); return Int(b[0]) | Int(b[1]) << 8
    }
    mutating func u32() throws -> Int {
        let b = try take(4)
        return Int(b[0]) | Int(b[1]) << 8 | Int(b[2]) << 16 | Int(b[3]) << 24
    }
    mutating func cString() throws -> String {
        var result: [UInt8] = []
        while true {
            let byte = try take(1)[0]
            if byte == 0 { return String(decoding: result, as: UTF8.self) }
            result.append(byte)
        }
    }
}

struct ClawSprite {
    let encodedPID: Data
    let flags: UInt32
    let paletteRGB: [UInt8]
    let width: Int
    let height: Int
    let offsetX: Int
    let offsetY: Int
    let rgba: [UInt8]

    init(pid: Data, palette: Data, useColorKey: UInt32 = 1) throws {
        encodedPID = pid
        var reader = Bytes(data: Array(pid))
        // The first header word varies in original light-effect assets. The
        // original image/raster paths consume geometry and flags, not a magic10.
        _ = try reader.u32()
        let flags = try reader.u32()
        self.flags = UInt32(flags)
        width = try reader.u32(); height = try reader.u32()
        offsetX = Int(Int32(bitPattern: UInt32(try reader.u32())))
        offsetY = Int(Int32(bitPattern: UInt32(try reader.u32())))
        _ = try reader.take(8)
        guard width > 0, height > 0, width <= 4096, height <= 4096 else {
            throw AssetError.invalid("Invalid sprite dimensions")
        }
        let embedded = flags & 128 != 0
        guard !embedded || pid.count >= 800 else { throw AssetError.invalid("Missing embedded palette") }
        let colors = embedded ? Array(pid.suffix(768)) : Array(palette)
        guard colors.count == 768 else { throw AssetError.invalid("Palette must contain 256 RGB entries") }
        paletteRGB = colors
        let pixelCount = width * height
        var indices = [UInt8](repeating: 0, count: pixelCount)
        var coverage = [UInt8](repeating: 0, count: pixelCount)
        var compressedInfo = ClawPIDRasterInfo()
        var surfaceInfo = ClawPIDSurfaceRasterInfo()
        let rasterWidth = width
        let accepted = pid.withUnsafeBytes { bytes in
            indices.withUnsafeMutableBufferPointer { indices in
                coverage.withUnsafeMutableBufferPointer { coverage in
                    if flags & 32 != 0 {
                        return claw_pid_decode_raster8(bytes.bindMemory(to: UInt8.self).baseAddress, pid.count,
                            indices.baseAddress, coverage.baseAddress, pixelCount, rasterWidth, &compressedInfo)
                    } else {
                        return claw_pid_decode_surface_raster8(bytes.bindMemory(to: UInt8.self).baseAddress, pid.count,
                            useColorKey, indices.baseAddress, coverage.baseAddress, pixelCount, rasterWidth, &surfaceInfo)
                    }
                }
            }
        }
        guard accepted == 1 else { throw AssetError.invalid("Malformed or unsupported PID raster") }
        var decoded: [UInt8] = []; decoded.reserveCapacity(pixelCount * 4)
        for pixel in 0..<pixelCount {
            if coverage[pixel] == 0 { decoded.append(contentsOf: [0, 0, 0, 0]); continue }
            let start = Int(indices[pixel]) * 3
            decoded.append(contentsOf: [colors[start], colors[start + 1], colors[start + 2], 255])
        }
        rgba = decoded
    }
}

struct ClawAnimation {
    struct Frame {
        let record: ClawAnimationRecord
        let event: String?
        var imageID: Int { Int(Int32(bitPattern: record.parameter)) }
        var milliseconds: Int { Int(record.duration) }
    }
    let imageSet: String
    let frames: [Frame]
    var duration: Double { Double(frames.reduce(0) { $0 + $1.milliseconds }) / 1000 }

    init(data: Data) throws {
        var reader = Bytes(data: Array(data))
        guard try reader.u32() == 32 else { throw AssetError.invalid("Unknown ANI signature") }
        _ = try reader.take(8)
        let count = try reader.u32(); let pathLength = try reader.u32()
        _ = try reader.take(12)
        guard count > 0, count <= 10000, pathLength < 4096 else { throw AssetError.invalid("Invalid ANI header") }
        imageSet = String(decoding: try reader.take(pathLength), as: UTF8.self)
        var parsed: [Frame] = []
        for _ in 0 ..< count {
            var record = ClawAnimationRecord()
            var nameLength: UInt32 = 0
            let remaining = reader.data.count - reader.position
            let consumed = reader.data.withUnsafeBufferPointer { buffer in
                claw_animation_decode_record(buffer.baseAddress!.advanced(by: reader.position),
                    UInt32(remaining), 0, &record, &nameLength)
            }
            guard consumed > 0 else { throw AssetError.invalid("Truncated ANI record") }
            let event = record.flags & 2 != 0
                ? String(decoding: reader.data[(reader.position + 20)..<(reader.position + 20 + Int(nameLength))], as: UTF8.self)
                : nil
            _ = try reader.take(Int(consumed))
            parsed.append(Frame(record: record, event: event))
        }
        // Original control/stop-only sequences (e.g. RatBomb BOUNCE and
        // GAME_NULL) are valid. Timing is interpreted by AnimationEngine.
        frames = parsed
    }

    func frame(at seconds: Double) -> Frame {
        guard duration > 0, seconds.isFinite else { return frames[0] }
        var time = max(0, seconds).truncatingRemainder(dividingBy: duration) * 1000
        for frame in frames {
            if time < Double(frame.milliseconds) { return frame }
            time -= Double(frame.milliseconds)
        }
        return frames[frames.count - 1]
    }
}
