import Foundation
import CoreGraphics

// Native presentation only. Pixel stores still come from frozen PIDBlitter.
enum ClawFastIndexedDrawing {
    static func draw(_ pid: ClawSprite, command: ClawSpriteDrawCommand, viewport: CGSize, z: Int) -> ClawSceneDraw? {
        guard viewport.width.isFinite, viewport.height.isFinite,
            viewport.width >= 1, viewport.height >= 1,
            viewport.width < 8193, viewport.height < 8193 else { return nil }
        let width = UInt32(viewport.width), height = UInt32(viewport.height)
        func rect(_ r: ClawSpriteRect) -> ClawPIDBlitRect {
            ClawPIDBlitRect(left: Int32(bitPattern: r.left), top: Int32(bitPattern: r.top),
                right: Int32(bitPattern: r.right), bottom: Int32(bitPattern: r.bottom))
        }
        var blit = ClawPIDBlitCommand(destination: rect(command.destination), source: rect(command.source),
            flipX: command.flipX, flipY: command.flipY, originalSourceRectAddress: 0x01003000)
        var output = ClawNativeIndexedImage()
        let accepted = pid.encodedPID.withUnsafeBytes { source in
            pid.paletteRGB.withUnsafeBufferPointer { palette in
                claw_native_indexed_present8(source.bindMemory(to: UInt8.self).baseAddress, pid.encodedPID.count,
                    &blit, palette.baseAddress, palette.count, width, height, &output)
            }
        }
        guard accepted == 1, let pixels = output.rgba else { return nil }
        // Transfer malloc ownership to the image provider's retained CFData.
        let bytes = Data(bytesNoCopy: pixels, count: output.byteCount, deallocator: .free)
        guard let provider = CGDataProvider(data: bytes as CFData),
            let image = CGImage(width: Int(output.width), height: Int(output.height), bitsPerComponent: 8,
                bitsPerPixel: 32, bytesPerRow: Int(output.width) * 4, space: CGColorSpaceCreateDeviceRGB(),
                bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.last.rawValue), provider: provider,
                decode: nil, shouldInterpolate: false, intent: .defaultIntent) else { return nil }
        return ClawSceneDraw(image: image,
            rect: CGRect(x: Int(output.left), y: Int(output.top), width: Int(output.width), height: Int(output.height)),
            mirrored: false, z: z, planeIndex: nil, tileID: nil)
    }
}
