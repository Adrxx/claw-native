import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

let root = URL(fileURLWithPath: CommandLine.arguments[1])
let scene = try ClawLevelScene(root: root)
let renderer = ClawLevelRenderer(scene: scene)
precondition(scene.layers.map { $0.plane.name } == ["Background", "Action", "Front"])
precondition(scene.layers.map { $0.plane.z } == [-999, 0, 9000])
precondition(scene.layers.map { $0.imageSets.flatMap { $0.keys }.count } == [64, 41, 8])
precondition(scene.layers.map { $0.plane.movementPercentX } == [50, 100, 150])
precondition(scene.layers.map { $0.plane.movementPercentY } == [50, 100, 125])
precondition(scene.layers.allSatisfy { $0.image(for: -1) == nil && $0.image(for: Int(0xeeeeeeee)) == nil })

// Check independently chosen plane-coordinate landmarks, including both wrapping axes.
func background(at camera: CGPoint, viewport: CGSize) -> [ClawSceneDraw] {
    renderer.commands(camera: camera, viewport: viewport).filter { $0.planeIndex == 0 }
}
let wrapped = background(at: CGPoint(x: 3200, y: 4800), viewport: CGSize(width: 64, height: 64))
precondition(wrapped.count == 2)
precondition(wrapped[0].rect == CGRect(x: 0, y: -32, width: 64, height: 64))
precondition(wrapped[0].tileID == scene.world.planes[0].tiles[13 * 24 + 1])
precondition(wrapped[1].rect == CGRect(x: 0, y: 32, width: 64, height: 64))
precondition(wrapped[1].tileID == scene.world.planes[0].tiles[14 * 24 + 1])
let negative = background(at: CGPoint(x: -128, y: -128), viewport: CGSize(width: 64, height: 64))
precondition(negative.count == 1 && negative[0].tileID == scene.world.planes[0].tiles[575])
precondition(negative[0].rect == CGRect(x: 0, y: 0, width: 64, height: 64))
let beyondFront = renderer.commands(camera: CGPoint(x: 2000, y: 7000), viewport: CGSize(width: 640, height: 480))
precondition(!beyondFront.contains { $0.planeIndex == 2 }, "Foreground wraps only x")
precondition(renderer.clampedCamera(CGPoint(x: -100, y: -100), viewport: CGSize(width: 100, height: 100)) == .zero)
precondition(renderer.clampedCamera(CGPoint(x: 1e6, y: 1e6), viewport: CGSize(width: 100, height: 100)) == CGPoint(x: 24476, y: 6044))
precondition(renderer.clampedCamera(CGPoint(x: 100, y: 100), viewport: CGSize(width: 30000, height: 8000)) == .zero)
precondition(renderer.commands(camera: .zero, viewport: .zero).isEmpty)
precondition(renderer.commands(camera: CGPoint(x: CGFloat.nan, y: 0), viewport: CGSize(width: 100, height: 100)).isEmpty)
precondition(renderer.commands(camera: CGPoint(x: 1e100, y: 0), viewport: CGSize(width: 100, height: 100)).isEmpty)
precondition(renderer.commands(camera: .zero, viewport: CGSize(width: 1e100, height: 100)).isEmpty)

// Every emitted tile must agree with the raw WWD plane at its inverse-projected coordinate.
// This catches wrong plane resource maps, rounding, negative wrapping, and incorrect parallax.
var checked = 0
for camera in [CGPoint.zero, CGPoint(x: 689, y: 4723), CGPoint(x: 1599, y: 1535),
    CGPoint(x: 20000, y: 5600), CGPoint(x: -129, y: -65)] {
    let commands = renderer.commands(camera: camera, viewport: CGSize(width: 801, height: 603))
    precondition(zip(commands, commands.dropFirst()).allSatisfy { $0.z <= $1.z })
    for draw in commands {
        let p = scene.world.planes[draw.planeIndex!]
        let worldX = draw.rect.minX + camera.x * CGFloat(p.movementPercentX) / 100
        let worldY = draw.rect.minY + camera.y * CGFloat(p.movementPercentY) / 100
        precondition(worldX.truncatingRemainder(dividingBy: CGFloat(p.tileWidth)) == 0)
        precondition(worldY.truncatingRemainder(dividingBy: CGFloat(p.tileHeight)) == 0)
        let column = Int(worldX / CGFloat(p.tileWidth)), row = Int(worldY / CGFloat(p.tileHeight))
        let x = (column % p.width + p.width) % p.width, y = (row % p.height + p.height) % p.height
        precondition(draw.tileID == p.tiles[y * p.width + x] & 0xffff)
        precondition(draw.rect.intersects(CGRect(origin: .zero, size: CGSize(width: 801, height: 603))))
        checked += 1
    }
}

func u32(_ value: UInt32) -> [UInt8] { (0..<4).map { UInt8(truncatingIfNeeded: value >> ($0 * 8)) } }
var palette = [UInt8](repeating: 0, count: 768)
palette[3] = 255; palette[7] = 255; palette[11] = 255
let fixture = try ClawSpriteImage(sprite: ClawSprite(pid: Data(
    [10, 32, 2, 2, UInt32(bitPattern: -7), 9, 0, 0].flatMap(u32) + [2, 1, 2, 129, 1, 3]), palette: Data(palette)))
precondition(fixture.sprite.offsetX == -7 && fixture.sprite.offsetY == 9)
let sprites = [ClawSceneSprite(decoded: fixture, position: CGPoint(x: 20, y: 30), origin: CGPoint(x: 1, y: 2), z: -1000),
    ClawSceneSprite(decoded: fixture, position: CGPoint(x: 20, y: 30), origin: CGPoint(x: -3, y: 2), mirrored: true, z: 10000)]
let actorCommands = renderer.commands(camera: CGPoint(x: 10, y: 20), viewport: CGSize(width: 64, height: 64), sprites: sprites)
let actors = actorCommands.filter { $0.planeIndex == nil }
precondition(actors.count == 2 && actorCommands.first?.planeIndex == nil && actorCommands.last?.planeIndex == nil)
precondition(actors[0].rect == CGRect(x: 9, y: 8, width: 2, height: 2))
precondition(actors[1].rect == CGRect(x: 5, y: 8, width: 2, height: 2))

func bitmap(width: Int, height: Int) -> CGContext {
    let context = CGContext(data: nil, width: width, height: height, bitsPerComponent: 8,
        bytesPerRow: width * 4, space: CGColorSpaceCreateDeviceRGB(),
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    context.translateBy(x: 0, y: CGFloat(height)); context.scaleBy(x: 1, y: -1)
    return context
}
let pixelContext = bitmap(width: 8, height: 8)
pixelContext.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
pixelContext.fill(CGRect(x: 0, y: 0, width: 8, height: 8))
ClawLevelRenderer.draw(ClawSceneDraw(image: fixture.image, rect: CGRect(x: 1, y: 1, width: 2, height: 2), mirrored: false, z: 0, planeIndex: nil, tileID: nil), in: pixelContext)
ClawLevelRenderer.draw(ClawSceneDraw(image: fixture.image, rect: CGRect(x: 4, y: 1, width: 2, height: 2), mirrored: true, z: 0, planeIndex: nil, tileID: nil), in: pixelContext)
let pixels = pixelContext.data!.assumingMemoryBound(to: UInt8.self)
func pixel(_ x: Int, _ y: Int) -> [UInt8] { Array(UnsafeBufferPointer(start: pixels.advanced(by: (y * 8 + x) * 4), count: 4)) }
precondition(pixel(1, 1) == [255, 0, 0, 255] && pixel(2, 1) == [0, 255, 0, 255])
precondition(pixel(1, 2) == [255, 255, 255, 255] && pixel(2, 2) == [0, 0, 255, 255])
precondition(pixel(4, 1) == [0, 255, 0, 255] && pixel(5, 1) == [255, 0, 0, 255])
precondition(pixel(4, 2) == [0, 0, 255, 255] && pixel(5, 2) == [255, 255, 255, 255])

if CommandLine.arguments.count > 2 {
    let viewport = CGSize(width: 960, height: 600)
    let context = bitmap(width: 960, height: 600)
    let camera = renderer.cameraCentered(at: CGPoint(x: scene.world.startX, y: scene.world.startY), viewport: viewport)
    for draw in renderer.commands(camera: camera, viewport: viewport) { ClawLevelRenderer.draw(draw, in: context) }
    let target = URL(fileURLWithPath: CommandLine.arguments[2])
    let output = CGImageDestinationCreateWithURL(target as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(output, context.makeImage()!, nil)
    precondition(CGImageDestinationFinalize(output))
}
print("PASS: 113 Level 1 PID tiles, 3 plane resource maps, \(checked) projected draws, wrapping/parallax/z/camera, signed PID metadata and pixel alpha/orientation/mirroring")
