import Foundation
import CoreGraphics

// Local reference assets for the native player milestone. Registry/asset-version
// equivalence is separate from the recovered gameplay routines.
struct ClawPlayerAssets {
    let root: URL
    let sprites: [Int: ClawSprite]
    let images: [Int: CGImage]
    let animations: [String: ClawAnimation]
    let sequenceNames: [UInt32: String]

    init(root: URL, level: UInt32 = 1) throws {
        self.root = root
        let palette = try Data(contentsOf: root.appendingPathComponent("LEVEL\(level)/PALETTES/MAIN.PAL"))
        let files = try FileManager.default.contentsOfDirectory(
            at: root.appendingPathComponent("IMAGES"), includingPropertiesForKeys: nil)
        var sprites: [Int: ClawSprite] = [:], images: [Int: CGImage] = [:]
        for file in files where file.pathExtension.uppercased() == "PID" {
            let name = file.deletingPathExtension().lastPathComponent
            guard name.hasPrefix("FRAME"), let id = Int(name.dropFirst(5)) else { continue }
            let sprite = try ClawSprite(pid: Data(contentsOf: file), palette: palette)
            guard let provider = CGDataProvider(data: Data(sprite.rgba) as CFData),
                  let image = CGImage(width: sprite.width, height: sprite.height,
                    bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: sprite.width * 4,
                    space: CGColorSpaceCreateDeviceRGB(),
                    bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.last.rawValue),
                    provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent) else {
                throw AssetError.invalid("Cannot create player sprite \(id)")
            }
            sprites[id] = sprite; images[id] = image
        }
        guard !sprites.isEmpty else { throw AssetError.invalid("Missing player sprites") }
        self.sprites = sprites; self.images = images
        let animationFiles = try FileManager.default.contentsOfDirectory(
            at: root.appendingPathComponent("ANIS"), includingPropertiesForKeys: nil)
        var animations: [String: ClawAnimation] = [:]
        for file in animationFiles where file.pathExtension.uppercased() == "ANI" {
            let name = file.deletingPathExtension().lastPathComponent.uppercased()
            animations[name] = try ClawAnimation(data: Data(contentsOf: file))
        }
        for name in ["STAND", "WALK", "JUMP", "FALL"] where animations[name] == nil {
            throw AssetError.invalid("Missing player animation \(name)")
        }
        self.animations = animations
        sequenceNames = [0x524690: "TEETER", 0x52469c: "WALK", 0x5246a8: "JUMP", 0x5246c4: "CLIMB",
            0x5246d0: "STAND", 0x5246dc: "FALL", 0x524718: "LAND", 0x524734: "IDLE",
            0x524740: "DUCK", 0x52474c: "LIFT2", 0x524758: "LIFTWALK", 0x524768: "LOOKUP",
            0x524790: "CLIMBIDLE", 0x5247a0: "CLIMBDOWN",
            0x5246e8: "FALLDEATH", 0x524708: "SPIKEDEATH",
            0x5247e0: "DAMAGE2", 0x5247f0: "DAMAGE1",
            0x524898: "KICK", 0x5248a4: "PUNCH", 0x5248b0: "UPPERCUT",
            0x5248c0: "EMPTYJUMPDYNAMITE", 0x5248d8: "JUMPDYNAMITE", 0x5248ec: "POSTDYNAMITE",
            0x524900: "EMPTYDYNAMITE", 0x524914: "PREDYNAMITE", 0x524928: "DUCKPOSTDYNAMITE",
            0x524940: "DUCKEMPTYDYNAMITE", 0x524958: "DUCKPREDYNAMITE",
            0x52497c: "EMPTYJUMPMAGIC", 0x524990: "JUMPMAGIC", 0x5249a0: "EMPTYMAGIC",
            0x5249b0: "MAGIC", 0x5249bc: "DUCKEMPTYMAGIC", 0x5249d0: "DUCKMAGIC",
            0x5249e0: "EMPTYJUMPPISTOL", 0x5249f8: "JUMPPISTOL", 0x524a08: "DUCKEMPTYPISTOL",
            0x524a20: "DUCKPISTOL", 0x524a30: "EMPTYPISTOL", 0x524a44: "PISTOL",
            0x524a5c: "JUMPPOWERUPSWIPE", 0x524a74: "JUMPSWIPE", 0x524a84: "POWERUPSWIPE",
            0x524a98: "SWIPE", 0x524aa4: "DUCKPOWERUPSWIPE", 0x524abc: "DUCKSWIPE"]
    }

    func playback(name: String, startImmediately: Bool = true) throws -> ClawAnimationPlayback {
        guard let animation = animations[name] else { throw AssetError.invalid("Unknown player sequence \(name)") }
        return try ClawAnimationPlayback(animation: animation, availableImages: Array(images.keys), startImmediately: startImmediately)
    }
}
