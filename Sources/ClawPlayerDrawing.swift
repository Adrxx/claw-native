import Foundation
import CoreGraphics

struct ClawPlayerDrawingCache {
    let key: [UInt32]
    let draw: ClawSceneDraw
}

// Original compressed geometry/blitters write indexed pixels before native RGB
// presentation. Surface drawing still uses CoreGraphics crop/reflection.
extension ClawNativePlayer {
    func drawCommand(camera: CGPoint, viewport: CGSize, projection: ClawSpriteProjection? = nil) -> ClawSceneDraw? {
        guard viewport.width >= 1, viewport.height >= 1,
            let pid = assets.sprites[imageID], let image = assets.images[imageID] else { return nil }
        var geometry = ClawSpriteGeometry()
        claw_sprite_set_geometry(&geometry, UInt32(pid.width), UInt32(pid.height),
            UInt32(bitPattern: Int32(pid.offsetX)), UInt32(bitPattern: imageOffsetY[imageID] ?? Int32(pid.offsetY)))
        geometry.surfaceToken = 1
        if pid.flags & 32 != 0 {
            geometry.compressed = 1; geometry.compressedToken = 1
        }
        var state = runtime
        func word(_ offset: UInt32) -> UInt32 { claw_player_actor_word(&state, offset) }
        var actor = ClawSpriteDrawActor()
        actor.flags = word(8)
        actor.blinkRemaining = word(0x44); actor.blinkInterval = word(0x48)
        actor.x = word(0x4c); actor.y = word(0x50)
        actor.displacementX = word(0x10); actor.displacementY = word(0x14)
        actor.renderFlags = word(0x40)
        var context = ClawSpriteDrawContext()
        context.width = UInt32(viewport.width); context.height = UInt32(viewport.height)
        context.surfaceToken = 1; context.animationDelta = state.animationDelta
        context.worldClip = ClawSpriteRect(left: 0, top: 0, right: context.width - 1, bottom: context.height - 1)
        if let projection { context.projection = projection }
        else {
            context.projection.cameraX = UInt32(bitPattern: Int32(camera.x))
            context.projection.cameraY = UInt32(bitPattern: Int32(camera.y))
        }
        var command = ClawSpriteDrawCommand()
        claw_sprite_prepare_draw(&geometry, &actor, &context, &command)
        recordDrawingState(actor)
        if command.kind == 3 { return compressedDraw(pid, command: command, viewport: viewport) }
        guard command.kind == 1 || command.kind == 2 else { return nil }
        let source = command.source, destination = command.destination
        let sourceRect = CGRect(x: Int(Int32(bitPattern: source.left)), y: Int(Int32(bitPattern: source.top)),
            width: Int(source.right &- source.left), height: Int(source.bottom &- source.top))
        guard let cropped = image.cropping(to: sourceRect) else { return nil }
        // Current player animations use horizontal mirroring; vertical draw
        // flags remain an explicit unsupported host presentation case.
        guard command.flipY == 0 else { return nil }
        return ClawSceneDraw(image: cropped,
            rect: CGRect(x: Int(Int32(bitPattern: destination.left)), y: Int(Int32(bitPattern: destination.top)),
                width: Int(destination.right &- destination.left), height: Int(destination.bottom &- destination.top)),
            mirrored: command.flipX != 0, z: Int(z), planeIndex: nil, tileID: nil)
    }

    private func compressedDraw(_ pid: ClawSprite, command: ClawSpriteDrawCommand,
        viewport: CGSize) -> ClawSceneDraw? {
        let width = Int(viewport.width), height = Int(viewport.height)
        guard width > 0, height > 0, width <= 8192, height <= 8192 else { return nil }
        let key = [UInt32(imageID), UInt32(width), UInt32(height), UInt32(bitPattern: z), command.flipX, command.flipY,
            command.source.left, command.source.top, command.source.right, command.source.bottom,
            command.destination.left, command.destination.top, command.destination.right, command.destination.bottom]
        if let cached = compressedDrawingCache, cached.key == key { return cached.draw }
        guard let draw = ClawIndexedDrawing.draw(pid, command: command, viewport: viewport, z: Int(z)) else { return nil }
        compressedDrawingCache = ClawPlayerDrawingCache(key: key, draw: draw)
        return draw
    }
}
