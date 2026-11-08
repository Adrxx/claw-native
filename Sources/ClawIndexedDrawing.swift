import Foundation
import CoreGraphics

// Original indexed blitters followed by native palette/RGB presentation.
enum ClawIndexedDrawing {
    static func draw(_ pid: ClawSprite, command: ClawSpriteDrawCommand, viewport: CGSize, z: Int) -> ClawSceneDraw? {
        let width = Int(viewport.width), height = Int(viewport.height)
        guard width > 0, height > 0, width <= 8192, height <= 8192 else { return nil }
        let stride = (width + 3) & ~3, capacity = stride * height
        var indices = [UInt8](repeating: 0, count: capacity)
        var coverage = [UInt8](repeating: 0, count: capacity)
        func rect(_ r: ClawSpriteRect) -> ClawPIDBlitRect {
            ClawPIDBlitRect(left: Int32(bitPattern: r.left), top: Int32(bitPattern: r.top),
                right: Int32(bitPattern: r.right), bottom: Int32(bitPattern: r.bottom))
        }
        // The native buffer has no original x86 address. This positive token
        // preserves the ordinary original pointer branch in the both-flip bug.
        var blit = ClawPIDBlitCommand(destination: rect(command.destination), source: rect(command.source),
            flipX: command.flipX, flipY: command.flipY, originalSourceRectAddress: 0x01003000)
        let accepted = pid.encodedPID.withUnsafeBytes { source in
            indices.withUnsafeMutableBufferPointer { output in
                coverage.withUnsafeMutableBufferPointer { mask in
                    claw_pid_blit8(source.bindMemory(to: UInt8.self).baseAddress, pid.encodedPID.count,
                        &blit, output.baseAddress, mask.baseAddress, capacity, stride, nil)
                }
            }
        }
        guard accepted == 1 else { return nil }
        // Preserve every actual store, including clipping spills into visible
        // neighboring rows; padded columns are not presented as screen pixels.
        var left = width, right = -1, top = height, bottom = -1
        for y in 0..<height {
            for x in 0..<width where coverage[y * stride + x] != 0 {
                left = min(left, x); right = max(right, x); top = min(top, y); bottom = max(bottom, y)
            }
        }
        guard right >= left, bottom >= top else { return nil }
        let drawWidth = right - left + 1, drawHeight = bottom - top + 1
        var rgba = [UInt8](repeating: 0, count: drawWidth * drawHeight * 4)
        for y in top...bottom {
            for x in left...right where coverage[y * stride + x] != 0 {
                let color = Int(indices[y * stride + x]) * 3
                let pixel = ((y - top) * drawWidth + x - left) * 4
                rgba[pixel] = pid.paletteRGB[color]; rgba[pixel + 1] = pid.paletteRGB[color + 1]
                rgba[pixel + 2] = pid.paletteRGB[color + 2]; rgba[pixel + 3] = 255
            }
        }
        guard let provider = CGDataProvider(data: Data(rgba) as CFData),
            let image = CGImage(width: drawWidth, height: drawHeight, bitsPerComponent: 8, bitsPerPixel: 32,
                bytesPerRow: drawWidth * 4, space: CGColorSpaceCreateDeviceRGB(),
                bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.last.rawValue), provider: provider,
                decode: nil, shouldInterpolate: false, intent: .defaultIntent) else { return nil }
        let draw = ClawSceneDraw(image: image, rect: CGRect(x: left, y: top, width: drawWidth, height: drawHeight),
            mirrored: false, z: Int(z), planeIndex: nil, tileID: nil)
        return draw
    }
}
