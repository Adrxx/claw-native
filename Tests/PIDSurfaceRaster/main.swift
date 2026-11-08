import Foundation

let root = URL(fileURLWithPath: CommandLine.arguments[1])
let palette = try Data(contentsOf: root.appendingPathComponent("MAIN.PAL"))
let colors = Array(palette)
func decodeSurface(_ pid: Data, useColorKey: UInt32 = 1) -> (ClawPIDSurfaceRasterInfo, [UInt8], [UInt8]) {
    let bytes = Array(pid)
    func word(_ start: Int) -> Int {
        (0..<4).reduce(0) { $0 | Int(bytes[start+$1]) << ($1*8) }
    }
    let width = word(8), height = word(12)
    var indices = [UInt8](repeating: 0x99, count: width*height)
    var coverage = [UInt8](repeating: 0x77, count: indices.count)
    var info = ClawPIDSurfaceRasterInfo()
    let accepted = indices.withUnsafeMutableBufferPointer { output in
        coverage.withUnsafeMutableBufferPointer { mask in
            bytes.withUnsafeBufferPointer { source in
                claw_pid_decode_surface_raster8(source.baseAddress, bytes.count, useColorKey,
                    output.baseAddress, mask.baseAddress, output.count, width, &info)
            }
        }
    }
    precondition(accepted == 1)
    return (info,indices,coverage)
}
let files = FileManager.default.enumerator(at: root, includingPropertiesForKeys: nil)!
var checked = 0, pixelCount = 0
for case let url as URL in files where url.pathExtension.uppercased() == "PID" {
    let pid = try Data(contentsOf: url), bytes = Array(pid)
    guard bytes.count > 32, bytes[4] & 32 == 0 else { continue }
    let sprite = try ClawSprite(pid: pid, palette: palette)
    let (info,indices,coverage) = decodeSurface(pid)
    precondition(info.width == sprite.width && info.height == sprite.height)
    precondition(info.offsetX == sprite.offsetX && info.offsetY == sprite.offsetY)
    let effectiveColors = bytes[4] & 128 != 0 ? Array(bytes.suffix(768)) : colors
    for pixel in indices.indices {
        let offset = Int(indices[pixel])*3
        let rgba: [UInt8] = [effectiveColors[offset],effectiveColors[offset+1],effectiveColors[offset+2],coverage[pixel] == 0 ? 0 : 255]
        // Transparent RGB is immaterial to the surface/color-key convention.
        precondition(sprite.rgba[pixel*4+3] == rgba[3], "Swift/native surface alpha mismatch in \(url.path)")
        if coverage[pixel] != 0 {
            precondition(Array(sprite.rgba[(pixel*4)..<(pixel*4+4)]) == rgba, "Swift/native surface pixel mismatch in \(url.path)")
        }
    }
    checked += 1; pixelCount += indices.count
}
precondition(checked == 221)
func fixture(flags: UInt32) -> Data {
    var result = Data()
    for word: UInt32 in [10, flags, 4, 1, 0, 0, 0, 0] {
        result.append(contentsOf: (0..<4).map { UInt8(truncatingIfNeeded: word >> ($0*8)) })
    }
    result.append(contentsOf: [0xc0,0xee,0,0x80,0xbf,0xc1,0xff])
    return result
}
let (_,opaque,opaqueCoverage) = decodeSurface(fixture(flags: 2))
let (keyedInfo,_,keyedCoverage) = decodeSurface(fixture(flags: 3))
let (disabledInfo,_,disabledCoverage) = decodeSurface(fixture(flags: 3),useColorKey: 0)
precondition(opaque == [0,128,191,255] && opaqueCoverage == [1,1,1,1])
precondition(keyedInfo.colorKeyEnabled == 1 && keyedCoverage == [0,1,1,1])
precondition(disabledInfo.colorKeyEnabled == 0 && disabledCoverage == [1,1,1,1])
let opaqueSprite = try ClawSprite(pid: fixture(flags: 2), palette: palette)
let keyedSprite = try ClawSprite(pid: fixture(flags: 3), palette: palette)
let disabledSprite = try ClawSprite(pid: fixture(flags: 3), palette: palette, useColorKey: 0)
precondition(opaqueSprite.rgba[3] == 255 && keyedSprite.rgba[3] == 0 && disabledSprite.rgba[3] == 255)
for pixel in 1..<4 {
    precondition(Array(opaqueSprite.rgba[(pixel*4)..<(pixel*4+4)]) == Array(keyedSprite.rgba[(pixel*4)..<(pixel*4+4)]))
}
print("PASS Swift/native surface raster interoperability: \(checked) PIDs / \(pixelCount) pixels; zero-run, opaque/keyed index zero, explicit color-key disabling")
