import Foundation
import CoreGraphics

/// Decoded pixels and signed PID offsets travel together, even when tiles have zero offsets.
struct ClawSpriteImage {
    let sprite: ClawSprite
    let image: CGImage

    init(sprite: ClawSprite, image: CGImage) { self.sprite = sprite; self.image = image }

    init(sprite: ClawSprite) throws {
        self.sprite = sprite
        guard let provider = CGDataProvider(data: Data(sprite.rgba) as CFData),
              let image = CGImage(width: sprite.width, height: sprite.height,
                bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: sprite.width * 4,
                space: CGColorSpaceCreateDeviceRGB(),
                bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.last.rawValue),
                provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent) else {
            throw AssetError.invalid("Cannot create PID image")
        }
        self.image = image
    }
}

/// WWD plane interpretation and resource resolution are reference-informed, not binary recovered.
struct ClawLevelScene {
    struct Layer {
        let sourceIndex: Int
        let plane: ClawWorld.Plane
        let imageSets: [[Int: ClawSpriteImage]]
        func image(for cell: Int) -> ClawSpriteImage? {
            guard cell != -1, UInt32(truncatingIfNeeded: cell) != 0xeeeeeeee else { return nil }
            let id = Int(UInt32(truncatingIfNeeded: cell) & 0xffff)
            // Preserve the WWD image-set order. Ambiguous duplicate IDs are rejected on load.
            return imageSets.lazy.compactMap { $0[id] }.first
        }
    }
    let world: ClawWorld
    let level: UInt32
    let layers: [Layer]
    let root: URL
    var actionPlane: ClawWorld.Plane { world.planes.first { $0.flags & 1 != 0 }! }

    init(root: URL, level: UInt32 = 1) throws {
        guard (1...14).contains(level) else { throw AssetError.invalid("Level must be in 1...14") }
        self.root = root; self.level = level
        world = try ClawWorld(data: Data(contentsOf: root.appendingPathComponent("LEVEL\(level)/WORLDS/WORLD.WWD")))
        guard world.planes.contains(where: { $0.flags & 1 != 0 }) else {
            throw AssetError.invalid("Missing main plane")
        }
        let palette = try Data(contentsOf: root.appendingPathComponent("LEVEL\(level)/PALETTES/MAIN.PAL"))
        var cache: [String: [Int: ClawSpriteImage]] = [:]
        var loaded: [Layer] = []
        for (index, plane) in world.planes.enumerated() {
            var sets: [[Int: ClawSpriteImage]] = []
            var usedIDs: Set<Int> = []
            for name in plane.imageSets {
                // WWD names are tile directory names, not arbitrary filesystem paths.
                guard !name.isEmpty, !name.contains("/"), !name.contains("\\"), name != ".", name != ".." else {
                    throw AssetError.invalid("Invalid tile image-set name")
                }
                let key = name.uppercased()
                if cache[key] == nil {
                    let directory = root.appendingPathComponent("LEVEL\(level)/TILES/\(key)")
                    let urls = try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
                    var images: [Int: ClawSpriteImage] = [:]
                    for url in urls.sorted(by: { $0.lastPathComponent < $1.lastPathComponent })
                        where url.pathExtension.uppercased() == "PID" {
                        guard let id = Int(url.deletingPathExtension().lastPathComponent) else { continue }
                        guard images[id] == nil else { throw AssetError.invalid("Duplicate tile ID \(id) in \(name)") }
                        images[id] = try ClawSpriteImage(sprite: ClawSprite(pid: Data(contentsOf: url), palette: palette))
                    }
                    cache[key] = images
                }
                let images = cache[key]!
                guard usedIDs.isDisjoint(with: images.keys) else {
                    throw AssetError.invalid("Ambiguous tile IDs across image sets in \(plane.name)")
                }
                usedIDs.formUnion(images.keys)
                sets.append(images)
            }
            let layer = Layer(sourceIndex: index, plane: plane, imageSets: sets)
            if plane.flags & 2 == 0 {
                for cell in Set(plane.tiles) where cell != -1 && UInt32(truncatingIfNeeded: cell) != 0xeeeeeeee {
                    guard layer.image(for: cell) != nil else {
                        throw AssetError.invalid("Missing tile \(cell) in \(plane.name)")
                    }
                }
            }
            loaded.append(layer)
        }
        layers = loaded.sorted { $0.plane.z == $1.plane.z ? $0.sourceIndex < $1.sourceIndex : $0.plane.z < $1.plane.z }
    }

    static func bundled() throws -> ClawLevelScene {
        guard let resources = Bundle.main.resourceURL else { throw AssetError.invalid("Missing GameData") }
        return try ClawLevelScene(root: resources.appendingPathComponent("GameData"))
    }
}
