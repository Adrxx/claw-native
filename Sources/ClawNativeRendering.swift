import Foundation
import CoreGraphics
import ImageIO

// Original tile/world command selection over native token storage. DD surfaces,
// palette presentation and physical blits remain explicit graphics adapters.
final class ClawNativeRendering {
    static let physicalBytes = 640 * 481
    unowned let scene: ClawNativeScene
    private(set) var targetToken: UInt32
    private(set) var indexedToken: UInt32
    private let faultStorage = UnsafeMutablePointer<UInt32>.allocate(capacity: 1)
    private let palette: Data
    private var opaqueImages: [UInt32: CGImage] = [:], fills: [UInt32: CGImage] = [:]
    private let imageGlobals = UnsafeMutablePointer<ClawGameImageGlobals>.allocate(capacity: 1)
    private var drawingImage: ClawSpriteImage?
    private var indexed: UnsafeMutablePointer<UInt8>
    private var indexedIdentity: ClawTokenHeap.AllocationIdentity
    private var snapshotDepth = 0
    private let coverage = UnsafeMutablePointer<UInt8>.allocate(capacity: ClawNativeRendering.physicalBytes)
    private let scratch = UnsafeMutablePointer<UInt8>.allocate(capacity: 129)
    private var surfaceIndices: [Data: Data] = [:]
    private(set) var effectDraws: [UInt32: UInt64] = [:], effectWrites: [UInt32: UInt64] = [:]
    private(set) var commands: [ClawSceneDraw] = []
    private(set) var graphicsCalls: UInt64 = 0, actorDrawCalls: UInt64 = 0, frameCount: UInt64 = 0
    private(set) var unknownServices: Set<UInt32> = []
    private(set) var failure: String?
    private(set) var palettePresentations: UInt64 = 0
    var fault: UInt32 { faultStorage.pointee }
    var indexedSnapshot: Data { Data(bytes: indexed, count: 640 * 480) }
    var sourceImageGlobals: UnsafeMutablePointer<ClawGameImageGlobals> { imageGlobals }

    // MARK: - Indexed storage lifetime

    init(scene: ClawNativeScene, root: URL) throws {
        self.scene = scene
        palette = try Data(
            contentsOf: root.appendingPathComponent("LEVEL\(scene.objectResources!.level)/PALETTES/MAIN.PAL"))
        indexedToken = scene.heap.allocate(bytes: UInt32(Self.physicalBytes))  //Physical indexed storage includes one offscreen row.
        indexed = UnsafeMutableRawPointer(scene.heap.lookup(indexedToken, words: UInt32(Self.physicalBytes / 4))!)
            .assumingMemoryBound(to: UInt8.self)
        indexedIdentity = scene.heap.allocationIdentity(at: indexedToken, count: UInt32(Self.physicalBytes))!
        targetToken = scene.heap.allocate(bytes: 48)
        let target = scene.heap.lookup(targetToken, words: 12)!
        target[4] = 640
        target[5] = 480
        target[11] = scene.heap.allocate(bytes: 12)
        imageGlobals.initialize(to: ClawGameImageGlobals())
        imageGlobals.pointee.directDrawFX.0 = 100
        faultStorage.initialize(to: 0)
        indexed.initialize(repeating: 0, count: Self.physicalBytes)
        coverage.initialize(repeating: 0, count: Self.physicalBytes)
        //Declared native initial caller/global profile. The source scratch tail
        //and destination indices persist thereafter, including across frames.
        scratch.initialize(repeating: 0, count: 129)
    }
    deinit {
        faultStorage.deinitialize(count: 1)
        faultStorage.deallocate()
        imageGlobals.deinitialize(count: 1)
        imageGlobals.deallocate()
        coverage.deinitialize(count: Self.physicalBytes)
        coverage.deallocate()
        scratch.deinitialize(count: 129)
        scratch.deallocate()
    }
    // MARK: - Source display target and draw dispatch

    func installSourceDisplayTarget(_ token: UInt32) {
        guard let target = scene.heap.lookup(token, words: 12), target[4] == 640, target[5] == 480,
            scene.heap.lookup(target[11], words: 47) != nil
        else { preconditionFailure("Original source display target") }
        let old = targetToken
        if old != token, let words = scene.heap.lookup(old, words: 12) {
            scene.heap.free(words[11])
            scene.heap.free(old)
        }
        targetToken = token
    }
    // The recovered renderer calls back synchronously while this owner and
    // its heap-backed indexed storage remain alive. No retain is transferred.
    private var host: ClawPlaneRendererHost {
        ClawPlaneRendererHost(
            scene: scene.actorHost, graphicsContext: Unmanaged.passUnretained(self).toOpaque(),
            graphics: { context, call in
                guard let context else { return 0 }
                return Unmanaged<ClawNativeRendering>.fromOpaque(context).takeUnretainedValue().graphics(call)
            })
    }
    func render(world: UInt32, actors: UInt32) {
        snapshotDepth += 1
        defer { snapshotDepth -= 1 }
        commands.removeAll(keepingCapacity: true)
        scene.heap.withStableFreedStorage {
            if claw_plane_renderer_world(world, targetToken, actors, host, faultStorage) == 0 {
                faultStorage.pointee = max(fault, 1)
            }
        }
        //A physical DD palette update recolors existing eight-bit pixels.
        //Retain the ordinary source command history, then present its complete
        //indexed frame through the attached palette when that palette changes.
        if let colors = scene.paletteResources?.currentRGB, colors != palette {
            var output = ClawNativeIndexedImage()
            let done = colors.withUnsafeBytes {
                claw_native_indexed_frame_present8(
                    indexed, 640 * 480, 640, $0.bindMemory(to: UInt8.self).baseAddress, $0.count, 640, 480, &output)
            }
            if done == 1, let pixels = output.rgba {
                let bytes = Data(bytesNoCopy: pixels, count: output.byteCount, deallocator: .free)
                if let image = Self.image(rgba: bytes, width: Int(output.width), height: Int(output.height)) {
                    commands.append(
                        ClawSceneDraw(
                            image: image, rect: CGRect(x: 0, y: 0, width: 640, height: 480), mirrored: false, z: 0,
                            planeIndex: nil, tileID: nil))
                    palettePresentations &+= 1
                } else {
                    faultStorage.pointee = 1
                }
            } else {
                faultStorage.pointee = 1
            }
        }
        frameCount &+= 1
    }
    func drawActor(_ token: UInt32, image: UInt32, target: UInt32) -> UInt32 {
        snapshotDepth += 1
        defer { snapshotDepth -= 1 }
        guard target == targetToken, let snapshot = scene.snapshotActor(token), snapshot.actor.93 == image else {
            faultStorage.pointee = 1
            return 0
        }
        if token == 0x10002000 {
            guard let sprite = scene.player.assets.sprites[Int(snapshot.actor.91)],
                let image = scene.player.assets.images[Int(snapshot.actor.91)]
            else {
                faultStorage.pointee = 1
                return 0
            }
            drawingImage = ClawSpriteImage(sprite: sprite, image: image)
        } else {
            drawingImage = scene.objectResources?.images(token: snapshot.actor.92)?.frames[Int(snapshot.actor.91)]
        }
        guard drawingImage != nil else {
            faultStorage.pointee = 1
            return 0
        }
        defer { drawingImage = nil }
        imageGlobals.pointee.animationDelta = scene.animationDelta
        let host = ClawGameImageHost(
            heap: scene.actorHost, serviceContext: Unmanaged.passUnretained(self).toOpaque(),
            service: { context, call in
                guard let context else { return 0 }
                return Unmanaged<ClawNativeRendering>.fromOpaque(context).takeUnretainedValue().imageService(call)
            })
        var arguments = ClawGameImageArguments(), result: UInt32 = 0
        arguments.count = 2
        arguments.words.0 = token
        arguments.words.1 = target
        if claw_game_image_entry(0x4d2890, image, arguments, imageGlobals, host, faultStorage, &result) == 0 {
            faultStorage.pointee = max(fault, 1)
        }
        if token == 0x10002000, let updated = scene.snapshotActor(token) { scene.player.acceptSceneSnapshot(updated) }
        actorDrawCalls &+= 1
        return 0
    }
    func setCompressedEffect(_ token: UInt32, effect: UInt32, resource: UInt32) -> UInt32 {
        var arguments = ClawGameImageArguments(), result: UInt32 = 0
        arguments.count = 2
        arguments.words.0 = effect
        arguments.words.1 = resource
        let imageHost = ClawGameImageHost(heap: scene.actorHost, serviceContext: nil, service: nil)
        _ = claw_game_image_entry(0x4c6130, token, arguments, imageGlobals, imageHost, faultStorage, &result)
        return result
    }
    // MARK: - Physical image and graphics services

    private func imageService(_ call: ClawGameImageCall) -> UInt32 {
        if call.function == 0x546d58 {
            guard let source = call.source, let destination = call.destination else {
                faultStorage.pointee = 1
                return 0
            }
            destination.update(from: source, count: 4)
            return 1
        }
        guard let frame = drawingImage, let source = call.source else {
            faultStorage.pointee = 1
            return 0
        }
        var command = ClawSpriteDrawCommand()
        command.source = ClawSpriteRect(left: source[0], top: source[1], right: source[2], bottom: source[3])
        switch call.function {
        case 0x4bffa0:
            guard let destination = call.destination else {
                faultStorage.pointee = 1
                return 0
            }
            command.kind = 3
            command.flipX = call.arguments.3
            command.flipY = call.arguments.4
            command.destination = ClawSpriteRect(
                left: destination[0], top: destination[1], right: destination[2], bottom: destination[3])
            appendCompressed(frame.sprite, command: command, receiver: call.receiver)
        case 0x4b9d80:
            let width = source[2] &- source[0], height = source[3] &- source[1]
            command.destination = ClawSpriteRect(
                left: call.arguments.0, top: call.arguments.1,
                right: call.arguments.0 &+ width, bottom: call.arguments.1 &+ height)
            appendSurface(frame, command: command, keyEnabled: call.arguments.4 & 1 != 0)
        case 0x4b9ce0:
            guard let destination = call.destination else {
                faultStorage.pointee = 1
                return 0
            }
            command.destination = ClawSpriteRect(
                left: destination[0], top: destination[1], right: destination[2], bottom: destination[3])
            command.flipX = imageGlobals.pointee.directDrawFX.1 & 2 != 0 ? 1 : 0
            command.flipY = imageGlobals.pointee.directDrawFX.1 & 4 != 0 ? 1 : 0
            appendSurface(frame, command: command, keyEnabled: true)
        default:
            unknownServices.insert(call.function)
            faultStorage.pointee = 1
        }
        return 1
    }
    private func appendSurface(_ frame: ClawSpriteImage, command: ClawSpriteDrawCommand, keyEnabled: Bool) {
        updateIndexedSurface(frame.sprite, command: command, keyEnabled: keyEnabled)
        let source = command.source, destination = command.destination
        let left = Int(Int32(bitPattern: source.left)), top = Int(Int32(bitPattern: source.top))
        let width = Int(Int32(bitPattern: source.right &- source.left)),
            height = Int(Int32(bitPattern: source.bottom &- source.top))
        guard left >= 0, top >= 0, width > 0, height > 0, left + width <= frame.sprite.width,
            top + height <= frame.sprite.height
        else { return }
        var rgba = [UInt8](repeating: 0, count: width * height * 4)
        for y in 0..<height {
            for x in 0..<width {
                let sx = left + (command.flipX == 0 ? x : width - x - 1)
                let sy = top + (command.flipY == 0 ? y : height - y - 1)
                let pixel = (sy * frame.sprite.width + sx) * 4, out = (y * width + x) * 4
                rgba[out] = frame.sprite.rgba[pixel]
                rgba[out + 1] = frame.sprite.rgba[pixel + 1]
                rgba[out + 2] = frame.sprite.rgba[pixel + 2]
                rgba[out + 3] = keyEnabled ? frame.sprite.rgba[pixel + 3] : 255
            }
        }
        guard let image = Self.image(rgba: Data(rgba), width: width, height: height) else {
            faultStorage.pointee = 1
            return
        }
        commands.append(
            ClawSceneDraw(
                image: image,
                rect: CGRect(
                    x: Int(Int32(bitPattern: destination.left)), y: Int(Int32(bitPattern: destination.top)),
                    width: width, height: height),
                mirrored: false, z: 0, planeIndex: nil, tileID: nil))
    }
    private func graphics(_ call: ClawPlaneGraphicsCall) -> UInt32 {
        graphicsCalls &+= 1
        guard let rectangle = call.rectangle else {
            faultStorage.pointee = 1
            return 0
        }
        let left = Int(Int32(bitPattern: rectangle[0])), top = Int(Int32(bitPattern: rectangle[1]))
        let width = Int(Int32(bitPattern: rectangle[2] &- rectangle[0])),
            height = Int(Int32(bitPattern: rectangle[3] &- rectangle[1]))
        guard width > 0, height > 0 else { return 0 }
        switch call.function {
        case 0x4b9d80:
            let surface = call.arguments.2
            guard let frame = scene.objectResources?.graphicsFrame(surfaceToken: surface) else {
                faultStorage.pointee = 1
                return 0
            }
            var command = ClawSpriteDrawCommand()
            command.source = ClawSpriteRect(
                left: rectangle[0], top: rectangle[1], right: rectangle[2], bottom: rectangle[3])
            command.destination = ClawSpriteRect(
                left: call.arguments.0, top: call.arguments.1, right: call.arguments.0 &+ UInt32(width),
                bottom: call.arguments.1 &+ UInt32(height))
            updateIndexedSurface(frame.sprite, command: command, keyEnabled: call.arguments.3 & 1 != 0)
            let image: CGImage
            if call.arguments.3 & 1 == 0 {
                if let cached = opaqueImages[surface] {
                    image = cached
                } else {
                    var rgba = frame.sprite.rgba
                    for index in stride(from: 3, to: rgba.count, by: 4) { rgba[index] = 255 }
                    guard
                        let made = Self.image(rgba: Data(rgba), width: frame.sprite.width, height: frame.sprite.height)
                    else {
                        faultStorage.pointee = 1
                        return 0
                    }
                    opaqueImages[surface] = made
                    image = made
                }
            } else {
                image = frame.image
            }
            guard let cropped = image.cropping(to: CGRect(x: left, y: top, width: width, height: height)) else {
                return 0
            }
            commands.append(
                ClawSceneDraw(
                    image: cropped,
                    rect: CGRect(
                        x: Int(Int32(bitPattern: call.arguments.0)), y: Int(Int32(bitPattern: call.arguments.1)),
                        width: width, height: height),
                    mirrored: false, z: 0, planeIndex: nil, tileID: nil))
        case 0x4b9ce0:
            guard let colorWord = scene.heap.lookup(call.arguments.3 &+ 0x50, words: 1) else {
                faultStorage.pointee = 1
                return 0
            }
            let color = colorWord[0]
            var rect = ClawPIDBlitRect(
                left: Int32(bitPattern: rectangle[0]), top: Int32(bitPattern: rectangle[1]),
                right: Int32(bitPattern: rectangle[2]), bottom: Int32(bitPattern: rectangle[3]))
            if claw_native_indexed_fill8(&rect, color, indexed, Self.physicalBytes, 640, 640, 480) != 1 {
                faultStorage.pointee = 1
                return 0
            }
            let image: CGImage
            if let existing = fills[color] {
                image = existing
            } else {
                // Native indexed framebuffer profile. Actual DirectDraw format
                // and display-mode conversion remain a presentation boundary.
                let index = Int(color & 255) * 3
                guard index + 2 < palette.count,
                    let made = Self.image(
                        rgba: Data([palette[index], palette[index + 1], palette[index + 2], 255]), width: 1, height: 1)
                else {
                    faultStorage.pointee = 1
                    return 0
                }
                fills[color] = made
                image = made
            }
            commands.append(
                ClawSceneDraw(
                    image: image, rect: CGRect(x: left, y: top, width: width, height: height), mirrored: false, z: 0,
                    planeIndex: nil, tileID: nil))
        default:
            unknownServices.insert(call.function)
            faultStorage.pointee = 1
        }
        return 1
    }
    private static func image(rgba: Data, width: Int, height: Int) -> CGImage? {
        guard let provider = CGDataProvider(data: rgba as CFData) else { return nil }
        return CGImage(
            width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: width * 4,
            space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.last.rawValue),
            provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent)
    }
    // MARK: - Indexed raster adapters

    private func blitCommand(_ command: ClawSpriteDrawCommand) -> ClawPIDBlitCommand {
        func rect(_ r: ClawSpriteRect) -> ClawPIDBlitRect {
            ClawPIDBlitRect(
                left: Int32(bitPattern: r.left), top: Int32(bitPattern: r.top), right: Int32(bitPattern: r.right),
                bottom: Int32(bitPattern: r.bottom))
        }
        return ClawPIDBlitCommand(
            destination: rect(command.destination), source: rect(command.source), flipX: command.flipX,
            flipY: command.flipY, originalSourceRectAddress: 0x01003000)
    }
    private func updateIndexedSurface(_ sprite: ClawSprite, command: ClawSpriteDrawCommand, keyEnabled: Bool) {
        let decoded: Data
        if let cached = surfaceIndices[sprite.encodedPID] {
            decoded = cached
        } else {
            var bytes = Data(count: sprite.width * sprite.height), mask = Data(count: bytes.count)
            var surfaceInfo = ClawPIDSurfaceRasterInfo(), rasterInfo = ClawPIDRasterInfo()
            let n = bytes.count, w = sprite.width
            let done = sprite.encodedPID.withUnsafeBytes { source in
                bytes.withUnsafeMutableBytes { out in
                    mask.withUnsafeMutableBytes { cover in
                        sprite.flags & 32 == 0
                            ? claw_pid_decode_surface_raster8(
                                source.bindMemory(to: UInt8.self).baseAddress, source.count, 0,
                                out.bindMemory(to: UInt8.self).baseAddress,
                                cover.bindMemory(to: UInt8.self).baseAddress, n, w, &surfaceInfo)
                            : claw_pid_decode_raster8(
                                source.bindMemory(to: UInt8.self).baseAddress, source.count,
                                out.bindMemory(to: UInt8.self).baseAddress,
                                cover.bindMemory(to: UInt8.self).baseAddress, n, w, &rasterInfo)
                    }
                }
            }
            guard done == 1 else {
                faultStorage.pointee = 1
                failure = "Indexed surface decode flags \(sprite.flags), \(sprite.width)x\(sprite.height)"
                return
            }
            decoded = bytes
            surfaceIndices[sprite.encodedPID] = bytes
        }
        var c = blitCommand(command)
        let done = decoded.withUnsafeBytes { source in
            claw_native_indexed_surface8(
                source.bindMemory(to: UInt8.self).baseAddress, source.count, UInt32(sprite.width),
                UInt32(sprite.height), &c, keyEnabled ? 1 : 0, indexed, Self.physicalBytes, 640, 640, 480)
        }
        //The original DD caller ignores rejected/clipped physical blits.
        _ = done
    }
    private func appendCompressed(_ sprite: ClawSprite, command: ClawSpriteDrawCommand, receiver: UInt32) {
        guard let raw = scene.heap.lookup(receiver, words: 10) else {
            faultStorage.pointee = 1
            return
        }
        var state = ClawLightPIDBlitState(
            renderWord: raw[0], effectMode: raw[5], effectValue: raw[6], formatByte: raw[9] & 255, bothTopSkipSeed: 0)
        var table = ClawLightPIDBlitTable(), tablePointer: UnsafePointer<ClawLightPIDBlitTable>?
        if raw[7] != 0 {
            guard let t = scene.heap.lookup(raw[7], words: 3) else {
                faultStorage.pointee = 1
                return
            }
            table.words = (t[0], t[1], t[2])
            table.capacity = Int(t[1])
            if t[2] != 0 {
                guard let payload = scene.heap.lookup(t[2], words: (t[1] + 3) / 4) else {
                    faultStorage.pointee = 1
                    return
                }
                table.data = UnsafeRawPointer(payload).assumingMemoryBound(to: UInt8.self)
            }
        }
        var c = blitCommand(command), output = ClawNativeIndexedImage(), info = ClawLightPIDBlitInfo()
        let done = withUnsafePointer(to: &table) { t -> UInt32 in
            tablePointer = raw[7] == 0 ? nil : t
            return sprite.encodedPID.withUnsafeBytes { source in
                sprite.paletteRGB.withUnsafeBufferPointer { palette in
                    claw_native_indexed_composite8(
                        source.bindMemory(to: UInt8.self).baseAddress, source.count, &c, &state, tablePointer, indexed,
                        coverage, Self.physicalBytes, 640, scratch, 129, palette.baseAddress, palette.count, 640, 480,
                        &info, &output)
                }
            }
        }
        effectDraws[state.effectMode, default: 0] &+= 1
        effectWrites[state.effectMode, default: 0] &+= UInt64(info.writes)
        //Original source callers ignore a rejected/no-write physical draw.
        guard done == 1, let pixels = output.rgba else { return }
        let bytes = Data(bytesNoCopy: pixels, count: output.byteCount, deallocator: .free)
        guard let image = Self.image(rgba: bytes, width: Int(output.width), height: Int(output.height)) else {
            faultStorage.pointee = 1
            return
        }
        commands.append(
            ClawSceneDraw(
                image: image,
                rect: CGRect(
                    x: Int(output.left), y: Int(output.top), width: Int(output.width), height: Int(output.height)),
                mirrored: false, z: 0, planeIndex: nil, tileID: nil))
    }
}

extension ClawNativeRendering {
    // MARK: - Snapshot persistence

    struct SavedState: Codable, Equatable {
        struct Command: Codable, Equatable {
            let png: Data
            let x: Double, y: Double, width: Double, height: Double
            let mirrored: Bool, z: Int, planeIndex: Int?, tileID: Int?
        }
        let target: ClawTokenHeap.AllocationReference, indexed: ClawTokenHeap.AllocationReference
        let palette: Data, coverage: Data, scratch: Data
        let image: ClawSnapshotValue<ClawGameImageGlobals>
        let commands: [Command]
        let effectDraws: [UInt32: UInt64], effectWrites: [UInt32: UInt64]
        let graphicsCalls: UInt64, actorDrawCalls: UInt64, frameCount: UInt64, palettePresentations: UInt64
        let unknownServices: Set<UInt32>, failure: String?, fault: UInt32
    }
    func savedState() throws -> SavedState {
        guard snapshotDepth == 0, drawingImage == nil else { throw ClawSnapshotError.activeFrame }
        guard let targetIdentity = scene.heap.containingAllocationIdentity(at: targetToken, count: 48),
            let target = scene.heap.snapshotReference(
                at: targetToken, count: 48, identity: targetIdentity, interior: true),
            let buffer = scene.heap.snapshotReference(
                at: indexedToken, count: UInt32(Self.physicalBytes), identity: indexedIdentity),
            scene.heap.lookupBytes(indexedToken, count: UInt32(Self.physicalBytes)) == indexed
        else { throw ClawSnapshotError.invalidState }
        let savedCommands: [SavedState.Command] = try commands.map { command in
            let data = NSMutableData()
            guard let destination = CGImageDestinationCreateWithData(data, "public.png" as CFString, 1, nil) else {
                throw ClawSnapshotError.invalidState
            }
            CGImageDestinationAddImage(destination, command.image, nil)
            guard CGImageDestinationFinalize(destination) else { throw ClawSnapshotError.invalidState }
            return .init(
                png: data as Data, x: command.rect.origin.x, y: command.rect.origin.y,
                width: command.rect.width, height: command.rect.height, mirrored: command.mirrored, z: command.z,
                planeIndex: command.planeIndex, tileID: command.tileID)
        }
        return .init(
            target: target, indexed: buffer, palette: palette,
            coverage: Data(bytes: coverage, count: Self.physicalBytes), scratch: Data(bytes: scratch, count: 129),
            image: ClawSnapshotValue(imageGlobals.pointee), commands: savedCommands, effectDraws: effectDraws,
            effectWrites: effectWrites,
            graphicsCalls: graphicsCalls, actorDrawCalls: actorDrawCalls, frameCount: frameCount,
            palettePresentations: palettePresentations,
            unknownServices: unknownServices, failure: failure, fault: fault)
    }
    func prepareRestore(_ saved: SavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws -> Void {
        guard snapshotDepth == 0, drawingImage == nil else { throw ClawSnapshotError.activeFrame }
        try scene.heap.validateRestore(plan)
        guard saved.palette == palette, saved.coverage.count == Self.physicalBytes, saved.scratch.count == 129,
            saved.target.count == 48, saved.target.interior, plan.resolve(saved.target) != nil,
            saved.indexed.count == UInt32(Self.physicalBytes), !saved.indexed.interior,
            let identity = plan.resolve(saved.indexed), let pointer = plan.bytes(for: saved.indexed),
            saved.commands.count <= 16384, saved.commands.reduce(0, { $0 + $1.png.count }) <= 128 << 20
        else { throw ClawSnapshotError.invalidState }
        let restoredCommands: [ClawSceneDraw] = try saved.commands.map { command in
            guard command.x.isFinite, command.y.isFinite, command.width.isFinite, command.height.isFinite,
                command.width > 0, command.height > 0, command.png.count <= 32 << 20,
                let source = CGImageSourceCreateWithData(command.png as CFData, nil),
                let image = CGImageSourceCreateImageAtIndex(source, 0, nil), image.width <= 16384, image.height <= 16384
            else { throw ClawSnapshotError.invalidState }
            return ClawSceneDraw(
                image: image, rect: CGRect(x: command.x, y: command.y, width: command.width, height: command.height),
                mirrored: command.mirrored, z: command.z, planeIndex: command.planeIndex, tileID: command.tileID)
        }
        return { [self] in
            try scene.heap.validateInstalledRestore(plan)
            guard snapshotDepth == 0, drawingImage == nil else { throw ClawSnapshotError.activeFrame }
            indexedToken = saved.indexed.token
            indexed = pointer
            indexedIdentity = identity
            targetToken = saved.target.token
            saved.coverage.withUnsafeBytes {
                UnsafeMutableRawPointer(coverage).copyMemory(from: $0.baseAddress!, byteCount: $0.count)
            }
            saved.scratch.withUnsafeBytes {
                UnsafeMutableRawPointer(scratch).copyMemory(from: $0.baseAddress!, byteCount: $0.count)
            }
            imageGlobals.pointee = saved.image.value
            commands = restoredCommands
            effectDraws = saved.effectDraws
            effectWrites = saved.effectWrites
            graphicsCalls = saved.graphicsCalls
            actorDrawCalls = saved.actorDrawCalls
            frameCount = saved.frameCount
            palettePresentations = saved.palettePresentations
            unknownServices = saved.unknownServices
            failure = saved.failure
            faultStorage.pointee = saved.fault
            // Pure immutable-image caches are derived from installed assets;
            // rebuilding them cannot consume tokens or change gameplay state.
            opaqueImages.removeAll()
            fills.removeAll()
            surfaceIndices.removeAll()
        }
    }
}
extension ClawGameImageGlobals: ClawSnapshotNativeValue {}
