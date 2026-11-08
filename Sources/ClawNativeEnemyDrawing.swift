import Foundation
import CoreGraphics

extension ClawNativeEnemy {
    func drawCommand(camera: CGPoint, viewport: CGSize, projection: ClawSpriteProjection? = nil) -> ClawSceneDraw? {
        guard let scene, var snapshot = scene.snapshotActor(token),
            let images = resources.images(token: snapshot.actor.92),
            let frame = images.frames[Int(snapshot.actor.91)], viewport.width >= 1, viewport.height >= 1 else { return nil }
        var geometry = ClawSpriteGeometry()
        claw_sprite_set_geometry(&geometry, UInt32(frame.sprite.width), UInt32(frame.sprite.height),
            UInt32(bitPattern: Int32(frame.sprite.offsetX)), UInt32(bitPattern: Int32(frame.sprite.offsetY)))
        geometry.surfaceToken = 1
        if frame.sprite.flags & 32 != 0 { geometry.compressed = 1; geometry.compressedToken = 1 }
        var actor = ClawSpriteDrawActor()
        withUnsafeBytes(of: &snapshot.actor) { bytes in
            func word(_ offset: Int) -> UInt32 { bytes.load(fromByteOffset: offset, as: UInt32.self) }
            actor.flags = word(8); actor.x = word(0x4c); actor.y = word(0x50)
            actor.displacementX = word(0x10); actor.displacementY = word(0x14); actor.renderFlags = word(0x40)
            actor.blinkRemaining = word(0x44); actor.blinkInterval = word(0x48)
            actor.clip = ClawSpriteRect(left: word(0x54), top: word(0x58), right: word(0x5c), bottom: word(0x60))
        }
        var context = ClawSpriteDrawContext(); context.width = UInt32(viewport.width); context.height = UInt32(viewport.height)
        context.surfaceToken = 1; context.animationDelta = scene.animationDelta
        context.worldClip = ClawSpriteRect(left: 0, top: 0, right: context.width - 1, bottom: context.height - 1)
        if let projection { context.projection = projection }
        else { context.projection.cameraX = UInt32(bitPattern: Int32(camera.x)); context.projection.cameraY = UInt32(bitPattern: Int32(camera.y)) }
        var command = ClawSpriteDrawCommand(); claw_sprite_prepare_draw(&geometry, &actor, &context, &command)
        withUnsafeMutableBytes(of: &snapshot.actor) { bytes in
            for (offset,word) in [(0x40,actor.renderFlags),(0x44,actor.blinkRemaining),(0x18,actor.drawX),(0x1c,actor.drawY),
                (0x20,actor.drawn.left),(0x24,actor.drawn.top),(0x28,actor.drawn.right),(0x2c,actor.drawn.bottom),
                (0x30,actor.drawWidth),(0x34,actor.drawHeight),(0x38,actor.drawStatus)] {
                bytes.storeBytes(of: word, toByteOffset: offset, as: UInt32.self)
            }
        }
        scene.write(snapshot)
        let z = Int(Int32(bitPattern: snapshot.actor.25))
        if command.kind == 3 { return ClawIndexedDrawing.draw(frame.sprite, command: command, viewport: viewport, z: z) }
        guard command.kind == 1 || command.kind == 2, command.flipY == 0 else { return nil }
        let source = command.source, destination = command.destination
        guard let cropped = frame.image.cropping(to: CGRect(x: Int(Int32(bitPattern: source.left)),
            y: Int(Int32(bitPattern: source.top)), width: Int(source.right-source.left), height: Int(source.bottom-source.top))) else { return nil }
        return ClawSceneDraw(image: cropped, rect: CGRect(x: Int(Int32(bitPattern: destination.left)),
            y: Int(Int32(bitPattern: destination.top)), width: Int(destination.right-destination.left), height: Int(destination.bottom-destination.top)),
            mirrored: command.flipX != 0, z: z, planeIndex: nil, tileID: nil)
    }
}
