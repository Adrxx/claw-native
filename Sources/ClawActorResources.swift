import Foundation
import CryptoKit

// Asset paths/palette selection are explicit native registry adapters. Pixel
// decoding, image geometry, binding stores and animation updates are recovered.
final class ClawActorResources {
    final class Images {
        let name: String, token: UInt32, minimum: Int, maximum: Int
        let frames: [Int: ClawSpriteImage], identities: [Int: UInt32], table: [UInt32]
        private let tablePointer: UnsafePointer<UInt32>
        private let tableToken: UInt32
        private let tableIdentity: ClawTokenHeap.AllocationIdentity
        private let managerIdentity: ClawTokenHeap.AllocationIdentity
        private let headerIdentities: [Int: ClawTokenHeap.AllocationIdentity]
        init(name: String, frames: [Int: ClawSpriteImage], heap: ClawTokenHeap) throws {
            guard let first = frames.keys.min(), let last = frames.keys.max(), first >= 0, last < 100000 else {
                throw AssetError.invalid("Invalid actor images \(name)")
            }
            self.name = name; self.frames = frames; minimum = first; maximum = last
            token = heap.allocate(bytes: 108)
            var identities: [Int: UInt32] = [:], table = [UInt32](repeating: 0, count: last + 1)
            for id in frames.keys.sorted() {
                let image = try ClawActorResources.imageHeader(sprite: frames[id]!.sprite, heap: heap)
                identities[id] = image; table[id] = image
            }
            self.identities = identities; self.table = table
            headerIdentities = identities.mapValues { heap.allocationIdentity(at: $0, count: 64)! }
            let arrayToken = heap.allocate(bytes: UInt32(table.count * 4))
            guard token != 0, arrayToken != 0, let manager = heap.lookup(token, words: 27),
                let array = heap.lookup(arrayToken, words: UInt32(table.count)) else { throw AssetError.invalid("Image table allocation failed") }
            table.withUnsafeBufferPointer { array.update(from: $0.baseAddress!, count: $0.count) }
            tablePointer = UnsafePointer(array)
            tableToken = arrayToken
            tableIdentity = heap.allocationIdentity(at: arrayToken, count: UInt32(table.count * 4))!
            managerIdentity = heap.allocationIdentity(at: token, count: 108)!
            manager[5] = arrayToken; manager[6] = UInt32(table.count); manager[25] = UInt32(first); manager[26] = UInt32(last)
        }
        fileprivate init(record: SavedState.ImagesRecord, frames: [Int: ClawSpriteImage],
                         tablePointer: UnsafePointer<UInt32>, identity: ClawTokenHeap.AllocationIdentity,
                         managerIdentity: ClawTokenHeap.AllocationIdentity, headers: [Int: ClawTokenHeap.AllocationIdentity]) {
            name = record.name; token = record.manager.token
            minimum = frames.keys.min()!; maximum = frames.keys.max()!
            self.frames = frames; identities = record.identities; table = record.table
            self.tablePointer = tablePointer; tableToken = record.array.token; tableIdentity = identity
            self.managerIdentity = managerIdentity
            headerIdentities = headers
        }
        fileprivate func savedRecord(heap: ClawTokenHeap) throws -> SavedState.ImagesRecord {
            guard let manager = heap.snapshotReference(at: token, count: 108, identity: managerIdentity),
                  let array = heap.snapshotReference(at: tableToken, count: UInt32(table.count * 4), identity: tableIdentity)
            else { throw ClawSnapshotError.invalidState }
            var headers: [Int: ClawTokenHeap.AllocationReference] = [:]
            for (id, identity) in headerIdentities {
                guard let reference = heap.snapshotReference(at: identities[id]!, count: 64, identity: identity)
                else { throw ClawSnapshotError.invalidState }
                headers[id] = reference
            }
            return .init(name: name, manager: manager, array: array, identities: identities, headers: headers, table: table,
                         assetHashes: frames.mapValues { Data(SHA256.hash(data: $0.sprite.encodedPID)) })
        }
        func binding() -> ClawActorImageBinding {
            ClawActorImageBinding(token: token, minimum: Int32(minimum), maximum: Int32(maximum),
                firstImageIndex: 0, images: tablePointer, imageCount: table.count)
        }
    }
    struct Sequence {
        let name: String, token: UInt32, animation: ClawAnimation
        let identity: ClawTokenHeap.AllocationIdentity
        let assetHash: Data
    }
    let level: UInt32
    let root: URL, heap: ClawTokenHeap
    private let palette: Data
    private let resolveEvent: (String) -> UInt32
    private var imageDirectories: [String: URL] = [:], sequenceFiles: [String: URL] = [:]
    private var loadedImages: [String: Images] = [:], loadedSequences: [String: Sequence] = [:]
    private var surfaceFrames: [UInt32: ClawSpriteImage] = [:]
    private var surfaceOrigins: [UInt32: SavedState.Surface] = [:]
    private var sequencesByToken: [UInt32: Sequence] = [:], imagesByToken: [UInt32: Images] = [:]

    init(root: URL, heap: ClawTokenHeap, level: UInt32 = 1, resolveEvent: @escaping (String) -> UInt32 = { _ in 0 }) throws {
        self.root = root; self.heap = heap; self.level = level
        self.resolveEvent = resolveEvent
        palette = try Data(contentsOf: root.appendingPathComponent("LEVEL\(level)/PALETTES/MAIN.PAL"))
        for file in try FileManager.default.contentsOfDirectory(at: root.appendingPathComponent("ANIS"), includingPropertiesForKeys: nil)
            where file.pathExtension.uppercased() == "ANI" {
            sequenceFiles["CLAW_" + file.deletingPathExtension().lastPathComponent.uppercased()] = file
        }
        for (prefix, directory) in [("LEVEL", "LEVEL\(level)"), ("GAME", "GAME")] {
            let imagesRoot = root.appendingPathComponent("\(directory)/IMAGES")
            if let enumerator = FileManager.default.enumerator(at: imagesRoot, includingPropertiesForKeys: nil) {
                for case let file as URL in enumerator where file.pathExtension.uppercased() == "PID" {
                    let relative = String(file.deletingLastPathComponent().path.dropFirst(imagesRoot.path.count))
                    let name = ([prefix] + relative.split(separator: "/").map(String.init)).joined(separator: "_").uppercased()
                    if let existing = imageDirectories[name], existing != file.deletingLastPathComponent() {
                        throw AssetError.invalid("Ambiguous image namespace \(name)")
                    }
                    imageDirectories[name] = file.deletingLastPathComponent()
                }
            }
            let sequenceRoot = root.appendingPathComponent("\(directory)/ANIS")
            if let enumerator = FileManager.default.enumerator(at: sequenceRoot, includingPropertiesForKeys: nil) {
                for case let file as URL in enumerator where file.pathExtension.uppercased() == "ANI" {
                    let relative = String(file.deletingPathExtension().path.dropFirst(sequenceRoot.path.count))
                    let name = ([prefix] + relative.split(separator: "/").map(String.init)).joined(separator: "_").uppercased()
                    guard sequenceFiles[name] == nil else { throw AssetError.invalid("Ambiguous animation namespace \(name)") }
                    sequenceFiles[name] = file
                }
            }
        }
    }
    // Image geometry/vtable stores are recovered; physical DD surface and
    // compressed object ownership are opaque native graphics services. Header
    // storage reserves64 bytes for the existing16-word view (original52 bytes).
    static func imageHeader(sprite: ClawSprite, heap: ClawTokenHeap, offsetY: Int32? = nil) throws -> UInt32 {
        let token = heap.allocate(bytes: 64)
        guard token != 0, let words = heap.lookup(token, words: 16) else { throw AssetError.invalid("Image header allocation") }
        var geometry = ClawSpriteGeometry()
        claw_sprite_set_geometry(&geometry, UInt32(sprite.width), UInt32(sprite.height),
            UInt32(bitPattern: Int32(sprite.offsetX)), UInt32(bitPattern: offsetY ?? Int32(sprite.offsetY)))
        words[0] = 0x513a70; words[3] = 0x10001000
        words[4] = geometry.width; words[5] = geometry.height; words[6] = geometry.halfWidth; words[7] = geometry.halfHeight
        words[8] = geometry.offsetX; words[9] = geometry.offsetY
        if sprite.flags & 32 != 0 {
            words[10] = 0x11; words[12] = heap.allocate(bytes: 0x28)
            let encoded = heap.allocate(bytes: UInt32(sprite.encodedPID.count))
            defer { heap.free(encoded) }
            guard let payload = heap.lookup(encoded,words:UInt32((sprite.encodedPID.count+3)/4)) else { throw AssetError.invalid("Compressed PID input allocation") }
            sprite.encodedPID.withUnsafeBytes { UnsafeMutableRawPointer(payload).copyMemory(from:$0.baseAddress!,byteCount:$0.count) }
            let host = ClawGameImageHost(heap:ClawSceneActorHost(context:Unmanaged.passUnretained(heap).toOpaque(),lookup:{u,t,n in
                guard let u else { return nil };return Unmanaged<ClawTokenHeap>.fromOpaque(u).takeUnretainedValue().lookup(t,words:n)
            },allocate:{u,n in
                guard let u else { return 0 };return Unmanaged<ClawTokenHeap>.fromOpaque(u).takeUnretainedValue().allocate(bytes:n)
            },free:{u,t in
                guard let u else { return };Unmanaged<ClawTokenHeap>.fromOpaque(u).takeUnretainedValue().free(t)
            },call:nil,readClock:nil),serviceContext:nil,service:nil)
            var globals = ClawGameImageGlobals(),fault:UInt32 = 0,result:UInt32 = 0,arguments = ClawGameImageArguments()
            guard claw_game_image_entry(0x4bfbf0,words[12],arguments,&globals,host,&fault,&result) == 1 else { throw AssetError.invalid("Original compressed image constructor") }
            arguments.count = 3;arguments.words.0 = encoded;arguments.words.1 = UInt32(sprite.encodedPID.count);arguments.words.2 = 8
            guard claw_game_image_entry(0x4bfc50,words[12],arguments,&globals,host,&fault,&result) == 1 && result == 1 else { throw AssetError.invalid("Original compressed PID load") }
            if sprite.flags & 64 != 0 {
                //Source4d2410 elects mode2. Palette ownership is connected by
                //the live source Flare image-set binder after scene palette boot.
                arguments.count = 2;arguments.words.0 = 2;arguments.words.1 = 0
                _ = claw_game_image_entry(0x4c6130,words[12],arguments,&globals,host,&fault,&result)
            }
        } else {
            // Bounded indexed native profile uses key0. The recovered surface
            // factory enables colorkey only for PIDflag1 and a key other than−1.
            // Whole physical DD creation remains an explicit graphics service.
            words[10] = sprite.flags & 1 != 0 ? 0x11 : 0x10; words[11] = heap.allocate(bytes: 8)
        }
        return token
    }
    func images(name: String) throws -> Images? {
        let key = name.uppercased()
        if let existing = loadedImages[key] { return existing }
        guard let directory = imageDirectories[key] else { return nil }
        var frames: [Int: ClawSpriteImage] = [:]
        for file in try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
            where file.pathExtension.uppercased() == "PID" {
            let stem = file.deletingPathExtension().lastPathComponent.uppercased()
            // Whole original4ce5e0 selects the first ASCII numeric substring,
            // or0 for a digit-free name such as SKULL. Filesystem enumeration
            // remains transport; no stored REZ-ID or spelling alias is inferred.
            let numeric = stem.range(of: "[0-9]+", options: .regularExpression)
            guard let id = numeric.map({ Int(stem[$0]) }) ?? 0, frames[id] == nil else {
                throw AssetError.invalid("Invalid/duplicate frame \(file.lastPathComponent)")
            }
            frames[id] = try ClawSpriteImage(sprite: ClawSprite(pid: Data(contentsOf: file), palette: palette))
        }
        let value = try Images(name: key, frames: frames, heap: heap)
        loadedImages[key] = value; imagesByToken[value.token] = value; rememberSurfaces(value); return value
    }
    func tileImages(name: String) throws -> Images? {
        let name = name.uppercased()
        guard !name.isEmpty, !name.contains("/"), !name.contains("\\"), name != ".", name != ".." else {
            throw AssetError.invalid("Invalid plane image-set name")
        }
        let key = "TILES_" + name
        if let existing = loadedImages[key] { return existing }
        let directory = root.appendingPathComponent("LEVEL\(level)/TILES/" + name)
        guard FileManager.default.fileExists(atPath: directory.path) else { return nil }
        var frames: [Int: ClawSpriteImage] = [:]
        for file in try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
            where file.pathExtension.uppercased() == "PID" {
            guard let id = Int(file.deletingPathExtension().lastPathComponent), frames[id] == nil else {
                throw AssetError.invalid("Invalid/duplicate tile frame \(file.lastPathComponent)")
            }
            frames[id] = try ClawSpriteImage(sprite: ClawSprite(pid: Data(contentsOf: file), palette: palette))
        }
        let value = try Images(name: key, frames: frames, heap: heap)
        loadedImages[key] = value; imagesByToken[value.token] = value; rememberSurfaces(value); return value
    }
    func sequence(name: String) throws -> Sequence? {
        let key = name.uppercased()
        if let existing = loadedSequences[key] { return existing }
        guard let file = sequenceFiles[key] else { return nil }
        let source = try Data(contentsOf: file)
        let animation = try ClawAnimation(data: source)
        let token = heap.allocate(bytes: 20)
        let tableToken = heap.allocate(bytes: UInt32(animation.frames.count * 4))
        guard token != 0, tableToken != 0, let sequence = heap.lookup(token, words: 5),
            let table = heap.lookup(tableToken, words: UInt32(animation.frames.count)) else {
            throw AssetError.invalid("Animation allocation failed")
        }
        sequence[3] = tableToken; sequence[4] = UInt32(animation.frames.count)
        for (index, frame) in animation.frames.enumerated() {
            let recordToken = heap.allocate(bytes: 48)
            guard recordToken != 0, let record = heap.lookup(recordToken, words: 12) else {
                throw AssetError.invalid("Animation record allocation failed")
            }
            table[index] = recordToken
            let source = frame.record
            let words: [UInt32] = [0, source.flags, source.imageCommand, source.controlCommand,
                source.movementCommand, source.parameter, source.duration, source.code,
                source.dx, source.dy, 0, frame.event.map(resolveEvent) ?? 0]
            words.withUnsafeBufferPointer { record.update(from: $0.baseAddress!, count: 12) }
        }
        let value = Sequence(name: key, token: token, animation: animation, identity: heap.allocationIdentity(at: token, count: 20)!,
                             assetHash: Data(SHA256.hash(data: source)))
        loadedSequences[key] = value; sequencesByToken[token] = value; return value
    }
    private func rememberSurfaces(_ images: Images) {
        for (id, token) in images.identities {
            if let header = heap.lookup(token, words: 13), header[11] != 0 {
                surfaceFrames[header[11]] = images.frames[id]
                surfaceOrigins[header[11]] = .init(token: header[11], imageSet: images.name, frame: id)
            }
        }
    }
    func graphicsFrame(surfaceToken: UInt32) -> ClawSpriteImage? { surfaceFrames[surfaceToken] }
    func sequence(token: UInt32) -> Sequence? { sequencesByToken[token] }
    func images(token: UInt32) -> Images? { imagesByToken[token] }
    func playback(sequence: UInt32, images: UInt32) throws -> ClawAnimationPlayback? {
        guard let sequence = sequencesByToken[sequence], let images = imagesByToken[images] else { return nil }
        return try ClawAnimationPlayback(animation: sequence.animation, availableImages: Array(images.frames.keys),
            startImmediately: false, imageIdentities: images.identities)
    }

    // Tokens and file identities only. Sprites/animations are re-decoded from
    // installed assets; the pinned binding table comes from the candidate heap.
    struct SavedState: Codable, Equatable {
        struct ImagesRecord: Codable, Equatable {
            let name: String
            let manager: ClawTokenHeap.AllocationReference
            let array: ClawTokenHeap.AllocationReference
            let identities: [Int: UInt32], headers: [Int: ClawTokenHeap.AllocationReference], table: [UInt32]
            let assetHashes: [Int: Data]
        }
        struct SequenceRecord: Codable, Equatable {
            let name: String
            let manager: ClawTokenHeap.AllocationReference
            let assetHash: Data
        }
        struct Surface: Codable, Equatable { let token: UInt32, imageSet: String, frame: Int }
        let level: UInt32, paletteHash: Data
        let images: [ImagesRecord], sequences: [SequenceRecord], surfaces: [Surface]
    }
    func savedState() throws -> SavedState {
        let images = try loadedImages.keys.sorted().map { try loadedImages[$0]!.savedRecord(heap: heap) }
        let sequences = try loadedSequences.keys.sorted().map { key -> SavedState.SequenceRecord in
            let value = loadedSequences[key]!
            guard let file = sequenceFiles[key],
                  let reference = heap.snapshotReference(at: value.token, count: 20, identity: value.identity)
            else { throw ClawSnapshotError.invalidState }
            guard value.assetHash == Data(SHA256.hash(data: try Data(contentsOf: file))) else { throw ClawSnapshotError.invalidState }
            return .init(name: key, manager: reference, assetHash: value.assetHash)
        }
        return .init(level: level, paletteHash: Data(SHA256.hash(data: palette)), images: images, sequences: sequences,
                     surfaces: surfaceOrigins.keys.sorted().map { surfaceOrigins[$0]! })
    }
    func prepareRestore(_ value: SavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws -> Void {
        try heap.validateRestore(plan)
        guard value.level == level, value.paletteHash == Data(SHA256.hash(data: palette)),
              value.images.count <= 4096, value.sequences.count <= 16384,
              Set(value.images.map(\.name)).count == value.images.count,
              Set(value.sequences.map(\.name)).count == value.sequences.count,
              Set(value.images.map { $0.manager.token }).count == value.images.count,
              Set(value.sequences.map { $0.manager.token }).count == value.sequences.count
        else { throw ClawSnapshotError.invalidState }
        var restoredImages: [String: Images] = [:], restoredSequences: [String: Sequence] = [:]
        var surfaces: [UInt32: ClawSpriteImage] = [:]
        for record in value.images {
            guard !record.manager.interior, record.manager.count == 108,
                  !record.array.interior, record.array.count == UInt32(record.table.count * 4),
                  !record.table.isEmpty, record.table.count <= 100000,
                  let managerBytes = plan.bytes(for: record.manager), let arrayBytes = plan.bytes(for: record.array),
                  let identity = plan.resolve(record.array) else { throw ClawSnapshotError.invalidState }
            let manager = UnsafeRawPointer(managerBytes).assumingMemoryBound(to: UInt32.self)
            let table = UnsafeRawPointer(arrayBytes).assumingMemoryBound(to: UInt32.self)
            guard manager[5] == record.array.token, manager[6] == UInt32(record.table.count),
                  Array(UnsafeBufferPointer(start: table, count: record.table.count)) == record.table
            else { throw ClawSnapshotError.invalidState }
            let directory: URL, tiles: Bool
            if let mapped = imageDirectories[record.name] { directory = mapped; tiles = false }
            else {
                guard record.name.hasPrefix("TILES_") else { throw ClawSnapshotError.invalidState }
                let name = String(record.name.dropFirst(6))
                guard !name.isEmpty, !name.contains("/"), !name.contains("\\"), name != ".", name != ".."
                else { throw ClawSnapshotError.invalidState }
                directory = root.appendingPathComponent("LEVEL\(level)/TILES/" + name); tiles = true
            }
            var frames: [Int: ClawSpriteImage] = [:]
            for file in try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
                where file.pathExtension.uppercased() == "PID" {
                let stem = file.deletingPathExtension().lastPathComponent.uppercased()
                let numeric = stem.range(of: "[0-9]+", options: .regularExpression)
                guard let id = tiles ? Int(stem) : (numeric.map { Int(stem[$0]) } ?? 0), frames[id] == nil,
                      record.assetHashes[id] == Data(SHA256.hash(data: try Data(contentsOf: file)))
                else { throw ClawSnapshotError.invalidState }
                frames[id] = try ClawSpriteImage(sprite: ClawSprite(pid: Data(contentsOf: file), palette: palette))
            }
            guard let first = frames.keys.min(), let last = frames.keys.max(), first >= 0,
                  last + 1 == record.table.count, manager[25] == UInt32(first), manager[26] == UInt32(last),
                  Set(frames.keys) == Set(record.identities.keys), Set(frames.keys) == Set(record.assetHashes.keys),
                  Set(record.identities.values).count == frames.count
            else { throw ClawSnapshotError.invalidState }
            for index in record.table.indices {
                guard record.table[index] == (record.identities[index] ?? 0) else { throw ClawSnapshotError.invalidState }
            }
            guard Set(record.headers.keys) == Set(record.identities.keys) else { throw ClawSnapshotError.invalidState }
            var headerIDs: [Int: ClawTokenHeap.AllocationIdentity] = [:]
            for (id, token) in record.identities {
                // Image/surface bytes are owned by the heap, not Swift. Validate
                // the full header against the same candidate allocation image.
                guard let reference = record.headers[id], reference.token == token, reference.count == 64, !reference.interior,
                      let identity = plan.resolve(reference) else { throw ClawSnapshotError.invalidState }
                headerIDs[id] = identity
            }
            restoredImages[record.name] = Images(record: record, frames: frames, tablePointer: table, identity: identity,
                                                  managerIdentity: plan.resolve(record.manager)!, headers: headerIDs)
        }
        for record in value.sequences {
            guard !record.manager.interior, record.manager.count == 20,
                  let bytes = plan.bytes(for: record.manager), let file = sequenceFiles[record.name],
                  record.assetHash == Data(SHA256.hash(data: try Data(contentsOf: file)))
            else { throw ClawSnapshotError.invalidState }
            let animation = try ClawAnimation(data: Data(contentsOf: file))
            let manager = UnsafeRawPointer(bytes).assumingMemoryBound(to: UInt32.self)
            guard manager[4] == UInt32(animation.frames.count),
                  let reference = plan.reference(at: manager[3], count: manager[4] * 4),
                  let array = plan.bytes(for: reference) else { throw ClawSnapshotError.invalidState }
            let records = UnsafeRawPointer(array).assumingMemoryBound(to: UInt32.self)
            for index in animation.frames.indices {
                guard plan.reference(at: records[index], count: 48) != nil else { throw ClawSnapshotError.invalidState }
            }
            restoredSequences[record.name] = Sequence(name: record.name, token: record.manager.token, animation: animation,
                                                       identity: plan.resolve(record.manager)!, assetHash: record.assetHash)
        }
        guard Set(value.surfaces.map(\.token)).count == value.surfaces.count else { throw ClawSnapshotError.invalidState }
        var origins: [UInt32: SavedState.Surface] = [:]
        for record in value.surfaces {
            guard let frame = restoredImages[record.imageSet]?.frames[record.frame] else { throw ClawSnapshotError.invalidState }
            surfaces[record.token] = frame; origins[record.token] = record
        }
        return { [self] in
            try heap.validateInstalledRestore(plan)
            loadedImages = restoredImages; loadedSequences = restoredSequences; surfaceFrames = surfaces; surfaceOrigins = origins
            imagesByToken = Dictionary(uniqueKeysWithValues: restoredImages.values.map { ($0.token, $0) })
            sequencesByToken = Dictionary(uniqueKeysWithValues: restoredSequences.values.map { ($0.token, $0) })
        }
    }
}
