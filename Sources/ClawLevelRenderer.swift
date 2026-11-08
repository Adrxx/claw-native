import Foundation
import CoreGraphics

/// Actor origin is supplied explicitly; the original PID-to-actor origin convention is not recovered.
struct ClawSceneSprite {
    let image: CGImage
    let position: CGPoint
    let origin: CGPoint
    let mirrored: Bool
    let z: Int

    init(image: CGImage, position: CGPoint, origin: CGPoint, mirrored: Bool = false, z: Int = 0) {
        self.image = image; self.position = position; self.origin = origin
        self.mirrored = mirrored; self.z = z
    }

    init(decoded: ClawSpriteImage, position: CGPoint, origin: CGPoint, mirrored: Bool = false, z: Int = 0) {
        self.init(image: decoded.image, position: position, origin: origin, mirrored: mirrored, z: z)
    }
}

struct ClawSceneDraw {
    let image: CGImage
    let rect: CGRect
    let mirrored: Bool
    let z: Int
    let planeIndex: Int?
    let tileID: Int?
}

/// Preview transforms: WWD percentage parallax, plane z ordering and wrapping flags.
/// These have format-reference support but have not been compared to the original renderer.
struct ClawLevelRenderer {
    let scene: ClawLevelScene

    func clampedCamera(_ camera: CGPoint, viewport: CGSize) -> CGPoint {
        let plane = scene.actionPlane
        return CGPoint(x: max(0, min(CGFloat(plane.width * plane.tileWidth) - viewport.width, camera.x)),
            y: max(0, min(CGFloat(plane.height * plane.tileHeight) - viewport.height, camera.y)))
    }

    func cameraCentered(at position: CGPoint, viewport: CGSize) -> CGPoint {
        clampedCamera(CGPoint(x: position.x - viewport.width / 2, y: position.y - viewport.height / 2), viewport: viewport)
    }

    func commands(camera: CGPoint, viewport: CGSize, sprites: [ClawSceneSprite] = [],
        projections: [Int: ClawSpriteProjection]? = nil) -> [ClawSceneDraw] {
        guard viewport.width > 0, viewport.height > 0,
              viewport.width.isFinite, viewport.height.isFinite, camera.x.isFinite, camera.y.isFinite,
              viewport.width <= 16_384, viewport.height <= 16_384,
              abs(camera.x) <= 1e12, abs(camera.y) <= 1e12 else { return [] }
        var result: [ClawSceneDraw] = []
        for layer in scene.layers where layer.plane.flags & 2 == 0 {
            let p = layer.plane
            let offset: CGPoint
            if let projection = projections?[layer.sourceIndex] {
                offset = CGPoint(x: CGFloat(Int32(bitPattern: projection.cameraX &- projection.screenOffsetX)),
                    y: CGFloat(Int32(bitPattern: projection.cameraY &- projection.screenOffsetY)))
            } else {
                offset = CGPoint(x: camera.x * CGFloat(p.movementPercentX) / 100,
                    y: camera.y * CGFloat(p.movementPercentY) / 100)
            }
            let tileSize = CGSize(width: p.tileWidth, height: p.tileHeight)
            let minX = Int(floor(offset.x / tileSize.width))
            let minY = Int(floor(offset.y / tileSize.height))
            let maxX = Int(ceil((offset.x + viewport.width) / tileSize.width))
            let maxY = Int(ceil((offset.y + viewport.height) / tileSize.height))
            let wrappingX = p.flags & 4 != 0, wrappingY = p.flags & 8 != 0
            let left = wrappingX ? minX : max(0, minX), right = wrappingX ? maxX : min(p.width, maxX)
            let top = wrappingY ? minY : max(0, minY), bottom = wrappingY ? maxY : min(p.height, maxY)
            guard left < right, top < bottom else { continue }
            for row in top..<bottom {
                for column in left..<right {
                    let x = ((column % p.width) + p.width) % p.width
                    let y = ((row % p.height) + p.height) % p.height
                    let cell = p.tiles[y * p.width + x]
                    guard let decoded = layer.image(for: cell) else { continue }
                    result.append(ClawSceneDraw(image: decoded.image,
                        rect: CGRect(x: CGFloat(column * p.tileWidth) - offset.x,
                            y: CGFloat(row * p.tileHeight) - offset.y,
                            width: CGFloat(decoded.sprite.width), height: CGFloat(decoded.sprite.height)),
                        mirrored: false, z: p.z, planeIndex: layer.sourceIndex,
                        tileID: Int(UInt32(truncatingIfNeeded: cell) & 0xffff)))
                }
            }
        }
        for sprite in sprites {
            // A mirrored origin reflects around the actor position, not around a fixed left edge.
            let originX = sprite.mirrored ? CGFloat(sprite.image.width) - sprite.origin.x : sprite.origin.x
            let rect = CGRect(x: sprite.position.x - originX - camera.x,
                y: sprite.position.y - sprite.origin.y - camera.y,
                width: CGFloat(sprite.image.width), height: CGFloat(sprite.image.height))
            if rect.intersects(CGRect(origin: .zero, size: viewport)) {
                result.append(ClawSceneDraw(image: sprite.image, rect: rect, mirrored: sprite.mirrored,
                    z: sprite.z, planeIndex: nil, tileID: nil))
            }
        }
        // Stable equal-z order: plane tiles first, supplied sprites afterwards in supplied order.
        return result.enumerated().sorted { $0.element.z == $1.element.z ? $0.offset < $1.offset : $0.element.z < $1.element.z }
            .map(\.element)
    }

    /// Draw in a top-left, y-down context. Canvas callers can consume the same commands directly.
    static func draw(_ command: ClawSceneDraw, in context: CGContext) {
        context.saveGState()
        context.interpolationQuality = .none
        context.translateBy(x: command.mirrored ? command.rect.maxX : command.rect.minX, y: command.rect.maxY)
        context.scaleBy(x: command.mirrored ? -1 : 1, y: -1)
        context.draw(command.image, in: CGRect(origin: .zero, size: command.rect.size))
        context.restoreGState()
    }
}
