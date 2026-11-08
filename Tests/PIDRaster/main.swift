import Foundation

let root = URL(fileURLWithPath: CommandLine.arguments[1])
let palette = try Data(contentsOf: root.appendingPathComponent("MAIN.PAL"))
let colors = Array(palette)
let files = FileManager.default.enumerator(at: root, includingPropertiesForKeys: nil)!
var checked = 0, pixelCount = 0
for case let url as URL in files where url.pathExtension.uppercased() == "PID" {
    let pid = try Data(contentsOf: url)
    let bytes = Array(pid)
    guard bytes.count > 32, bytes[4] & 32 != 0 else { continue }
    let sprite = try ClawSprite(pid: pid, palette: palette)
    var indices = [UInt8](repeating: 0x99, count: sprite.width * sprite.height)
    var coverage = [UInt8](repeating: 0x77, count: indices.count)
    var info = ClawPIDRasterInfo()
    let accepted = indices.withUnsafeMutableBufferPointer { output in
        coverage.withUnsafeMutableBufferPointer { mask in
            bytes.withUnsafeBufferPointer { source in
                claw_pid_decode_raster8(source.baseAddress, bytes.count,
                    output.baseAddress, mask.baseAddress, output.count, sprite.width, &info)
            }
        }
    }
    precondition(accepted == 1 && info.width == sprite.width && info.height == sprite.height)
    precondition(info.offsetX == sprite.offsetX && info.offsetY == sprite.offsetY)
    let effectiveColors = bytes[4] & 128 != 0 ? Array(bytes.suffix(768)) : colors
    for pixel in indices.indices {
        let rgba: [UInt8]
        if coverage[pixel] == 0 { rgba = [0, 0, 0, 0] }
        else {
            let offset = Int(indices[pixel]) * 3
            rgba = [effectiveColors[offset], effectiveColors[offset+1], effectiveColors[offset+2], 255]
        }
        precondition(Array(sprite.rgba[(pixel*4)..<(pixel*4+4)]) == rgba, "Swift/native compressed raster mismatch in \(url.path)")
    }
    checked += 1; pixelCount += indices.count
}
precondition(checked == 261)
// This deliberate synthetic edge distinguishes a literal zero from a skipped pixel.
var fixture = Data()
for word: UInt32 in [10, 32, 2, 1, 0, 0, 0, 0] {
    fixture.append(contentsOf: (0..<4).map { UInt8(truncatingIfNeeded: word >> ($0 * 8)) })
}
fixture.append(contentsOf: [1, 0, 129])
let sourceReference = try ClawSprite(pid: fixture, palette: palette)
var literalIndices = [UInt8](repeating: 99, count: 2)
var literalCoverage = [UInt8](repeating: 99, count: 2)
var literalInfo = ClawPIDRasterInfo()
let fixtureBytes = Array(fixture)
let acceptedFixture = literalIndices.withUnsafeMutableBufferPointer { output in
    literalCoverage.withUnsafeMutableBufferPointer { mask in
        fixtureBytes.withUnsafeBufferPointer { source in
            claw_pid_decode_raster8(source.baseAddress, fixtureBytes.count,
                output.baseAddress, mask.baseAddress, 2, 2, &literalInfo)
        }
    }
}
precondition(acceptedFixture == 1 && literalIndices == [0, 0] && literalCoverage == [1, 0])
precondition(sourceReference.rgba[3] == 255 && sourceReference.rgba[7] == 0,
    "Integrated decoder must distinguish literal index zero from transparent skips")
print("PASS integrated Swift decoder uses original indices/coverage for \(checked) compressed PIDs / \(pixelCount) pixels, with opaque literal zero and transparent skips")
