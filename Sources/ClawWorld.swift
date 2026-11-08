import Foundation
import zlib

// WWD structure is reference-informed by OpenClaw libwap, not binary recovery.
struct ClawWorld {
    struct Rect {
        let left: Int
        let top: Int
        let right: Int
        let bottom: Int
    }
    struct Object {
        // Preserve all 71 fixed-width words for later recovered object logic.
        let words: [UInt32]
        let encodedRecordOffset: Int
        let encodedRecord: Data
        let name: String
        let logic: String
        let imageSet: String
        let sound: String
        func signed(_ index: Int) -> Int { Int(Int32(bitPattern: words[index])) }
        var id: Int { signed(0) }
        var x: Int { signed(5) }
        var y: Int { signed(6) }
        var z: Int { signed(7) }
        var imageID: Int { signed(8) }
        var addFlags: UInt32 { words[9] }
        var dynamicFlags: UInt32 { words[10] }
        var drawFlags: UInt32 { words[11] }
        var userFlags: UInt32 { words[12] }
        func rect(_ index: Int) -> Rect {
            Rect(left: signed(index), top: signed(index + 1), right: signed(index + 2), bottom: signed(index + 3))
        }
        var moveRect: Rect { rect(19) }
        var hitRect: Rect { rect(23) }
        var attackRect: Rect { rect(27) }
        var clipRect: Rect { rect(31) }
    }
    struct TileDescription {
        let type: UInt32
        let unknown: UInt32
        let width: UInt32
        let height: UInt32
        let insideAttribute: UInt32
        let outsideAttribute: UInt32
        let rect: Rect?
        // Type 3 stores one attribute byte per pixel, row-major.
        let mask: [UInt8]
        func attribute(x: Int, y: Int) -> UInt32 {
            guard x >= 0, y >= 0, x < Int(width), y < Int(height) else { return 0 }
            if type == 3 { return UInt32(mask[y * Int(width) + x]) }
            if let r = rect {
                return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom ? insideAttribute : outsideAttribute
            }
            return insideAttribute
        }
        var native: ClawTileDescription {
            ClawTileDescription(type: type, width: width, height: height,
                insideAttribute: insideAttribute, outsideAttribute: outsideAttribute,
                left: Int32(rect?.left ?? 0), top: Int32(rect?.top ?? 0),
                right: Int32(rect?.right ?? 0), bottom: Int32(rect?.bottom ?? 0))
        }
    }
    struct Plane {
        let encodedHeaderOffset: Int
        let name: String
        let flags: UInt32
        let movementPercentX: Int
        let movementPercentY: Int
        let z: Int
        let width: Int
        let height: Int
        let tileWidth: Int
        let tileHeight: Int
        let tiles: [Int]
        let imageSets: [String]
        let objects: [Object]
        var objectCount: Int { objects.count }
    }
    let name: String
    let startX: Int
    let startY: Int
    let planes: [Plane]
    let tileDescriptions: [TileDescription]
    // Decompression remains a format adapter; retain exact byte offsets for
    // the recovered runtime loader instead of reconstructing its input words.
    let decodedBytes: Data

    init(data: Data) throws {
        var header = Bytes(data: Array(data))
        guard try header.u32() == 1524, data.count >= 1524 else { throw AssetError.invalid("Invalid WWD header") }
        _ = try header.u32(); let flags = try header.u32()
        func text(_ bytes: [UInt8]) -> String { String(decoding: bytes.prefix { $0 != 0 }, as: UTF8.self) }
        header.position = 16; name = text(try header.take(64))
        header.position = 720; startX = try header.u32(); startY = try header.u32()
        _ = try header.u32(); let count = try header.u32(); let offset = try header.u32()
        let descriptionsOffset = try header.u32(); let length = try header.u32()
        guard count > 0, count <= 16, offset >= 1524, offset <= data.count,
              length <= 64 * 1024 * 1024 else { throw AssetError.invalid("Invalid WWD bounds") }
        var raw = Array(data)
        if flags & 2 != 0 {
            var decoded = [UInt8](repeating: 0, count: length)
            var decodedLength = uLongf(length)
            let compressed = Array(data.dropFirst(offset))
            let result = decoded.withUnsafeMutableBufferPointer { output in
                compressed.withUnsafeBufferPointer { input in
                    uncompress(output.baseAddress, &decodedLength, input.baseAddress, uLong(compressed.count))
                }
            }
            guard result == Z_OK, decodedLength == length else { throw AssetError.invalid("Invalid WWD compression") }
            raw = Array(data.prefix(offset)) + decoded
        }
        decodedBytes = Data(raw)
        var parsed: [Plane] = []
        for index in 0..<count {
            var reader = Bytes(data: raw, position: offset + index * 160)
            guard try reader.u32() == 160 else { throw AssetError.invalid("Invalid WWD plane header") }
            _ = try reader.u32(); let planeFlags = UInt32(try reader.u32()); _ = try reader.u32()
            let planeName = text(try reader.take(64))
            _ = try reader.take(8)
            let tw = try reader.u32(); let th = try reader.u32()
            let w = try reader.u32(); let h = try reader.u32()
            _ = try reader.take(8)
            let movementX = Int(Int32(bitPattern: UInt32(try reader.u32())))
            let movementY = Int(Int32(bitPattern: UInt32(try reader.u32())))
            _ = try reader.u32(); let imageCount = try reader.u32(); let objectCount = try reader.u32()
            let tilesOffset = try reader.u32(); let imagesOffset = try reader.u32()
            let objectsOffset = try reader.u32(); let z = Int(Int32(bitPattern: UInt32(try reader.u32())))
            guard w > 0, h > 0, w <= 4_000_000, h <= 4_000_000, w * h <= 4_000_000,
                  tw > 0, tw <= 4096, th > 0, th <= 4096,
                  w * tw <= Int(Int32.max), h * th <= Int(Int32.max),
                  imageCount <= 128, objectCount <= 100_000 else { throw AssetError.invalid("Invalid WWD plane dimensions") }
            reader.position = tilesOffset
            var tiles: [Int] = []; tiles.reserveCapacity(w * h)
            for _ in 0..<(w * h) { tiles.append(Int(Int32(bitPattern: UInt32(try reader.u32())))) }
            reader.position = imagesOffset
            var sets: [String] = []
            for _ in 0..<imageCount { sets.append(try reader.cString()) }
            reader.position = objectsOffset
            var objects: [Object] = []; objects.reserveCapacity(objectCount)
            for _ in 0..<objectCount {
                let recordStart = reader.position
                var words: [UInt32] = []; words.reserveCapacity(71)
                for _ in 0..<71 { words.append(UInt32(try reader.u32())) }
                var strings: [String] = []
                for length in words[1...4] {
                    guard length <= 16_384 else { throw AssetError.invalid("Invalid WWD object string") }
                    strings.append(text(try reader.take(Int(length))))
                }
                objects.append(Object(words: words, encodedRecordOffset: recordStart, encodedRecord: Data(reader.data[recordStart..<reader.position]),
                    name: strings[0], logic: strings[1], imageSet: strings[2], sound: strings[3]))
            }
            parsed.append(Plane(encodedHeaderOffset: offset + index * 160, name: planeName, flags: planeFlags, movementPercentX: movementX,
                movementPercentY: movementY, z: z, width: w, height: h, tileWidth: tw, tileHeight: th,
                tiles: tiles, imageSets: sets, objects: objects))
        }
        planes = parsed
        var reader = Bytes(data: raw, position: descriptionsOffset)
        guard try reader.u32() == 32 else { throw AssetError.invalid("Invalid tile-description header") }
        _ = try reader.u32(); let descriptionCount = try reader.u32(); _ = try reader.take(20)
        guard descriptionCount <= 100_000 else { throw AssetError.invalid("Too many tile descriptions") }
        var descriptions: [TileDescription] = []; descriptions.reserveCapacity(descriptionCount)
        for _ in 0..<descriptionCount {
            let type = UInt32(try reader.u32()); let unknown = UInt32(try reader.u32())
            let width = UInt32(try reader.u32()); let height = UInt32(try reader.u32())
            guard (1...3).contains(type), width > 0, width <= 64, height > 0, height <= 64 else {
                throw AssetError.invalid("Invalid tile-description type or dimensions")
            }
            if type == 3 {
                // The original mask loader derives the row shift from height
                // and requires width == 1 << shift (4d5870).
                guard width == 1 << (31 - height.leadingZeroBitCount) else {
                    throw AssetError.invalid("Invalid mask row stride")
                }
                let mask = try reader.take(Int(width * height))
                descriptions.append(TileDescription(type: type, unknown: unknown, width: width,
                    height: height, insideAttribute: 0, outsideAttribute: 0, rect: nil, mask: mask))
                continue
            }
            let outside = type == 2 ? UInt32(try reader.u32()) : 0
            let inside = UInt32(try reader.u32())
            var rect: Rect?
            if type == 2 {
                rect = Rect(left: Int(Int32(bitPattern: UInt32(try reader.u32()))),
                    top: Int(Int32(bitPattern: UInt32(try reader.u32()))),
                    right: Int(Int32(bitPattern: UInt32(try reader.u32()))),
                    bottom: Int(Int32(bitPattern: UInt32(try reader.u32()))))
            }
            descriptions.append(TileDescription(type: type, unknown: unknown, width: width,
                height: height, insideAttribute: inside, outsideAttribute: outside, rect: rect, mask: []))
        }
        tileDescriptions = descriptions
    }
}

/// Validation at the native file boundary, before the original unbounded WWD
/// reader sees an imported file. The game still loads the unchanged bytes.
struct ClawCustomWorld {
    let data: Data
    let world: ClawWorld
    let level: UInt32
    enum Rejection: LocalizedError {
        case invalid(String), unsupported(String)
        var errorDescription: String? {
            switch self {
            case .invalid(let detail): return "Invalid custom level: \(detail)"
            case .unsupported(let detail): return "Not implemented: \(detail)"
            }
        }
    }
    init(url: URL) throws {
        let size = try url.resourceValues(forKeys:[.fileSizeKey,.isRegularFileKey])
        guard size.isRegularFile == true, let count = size.fileSize, (1524...16*1024*1024).contains(count) else {
            throw Rejection.invalid("The WWD file is missing, empty or too large.")
        }
        let data = try Data(contentsOf:url)
        func word(_ offset:Int)->UInt32 {data.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)}}
        guard data.count >= 1524 else {throw Rejection.invalid("Truncated header.")}
        guard word(0) == 1524, word(8) & ~UInt32(3) == 0 else {
            throw Rejection.unsupported("Extended WWD header.")
        }
        guard data[16..<80].contains(0),word(736) == 1524,word(744) > 0 else {
            throw Rejection.invalid("Invalid world header.")
        }
        // Original 436e60 / 4cd530: scan the description for its first ASCII
        // digit, then atoi. Resource paths and the filename do not choose it.
        let title = Array(data[16..<80].prefix(while:{$0 != 0}))
        let digits = title.drop(while:{$0 < 48 || $0 > 57}).prefix(while:{$0 >= 48 && $0 <= 57})
        guard let base = UInt32(String(decoding:digits,as:UTF8.self)), (1...14).contains(base) else {
            throw Rejection.invalid("The WWD title must identify a base level from 1 to 14.")
        }
        let world:ClawWorld
        do {world = try ClawWorld(data:data)}
        catch {throw Rejection.invalid(String(describing:error))}
        guard world.decodedBytes.count <= Int(ClawTokenHeap.worldBufferByteLimit)-64 else {
            throw Rejection.invalid("World exceeds the measured map buffer budget.")
        }
        guard world.planes.filter({$0.flags & 1 != 0}).count == 1 else {throw Rejection.invalid("Expected one action plane.")}
        for plane in world.planes {
            // Preserve the serialized byte. Original plane load copies it whole;
            // draw uses bit 1, clamp bits 2/3, auto-size bit 4, main bit 0.
            // Sampled 0x20/0x40/0x80 survive unchanged, including retail controls.
            guard plane.flags & ~UInt32(255) == 0 else {throw Rejection.invalid("Invalid plane flags.")}
            guard plane.tileWidth.nonzeroBitCount == 1, plane.tileHeight.nonzeroBitCount == 1,
                  plane.width * plane.height <= Int(ClawNativeMenuResources.gridCellLimit),
                  plane.tiles.allSatisfy({ tile in
                      let word = UInt32(bitPattern:Int32(tile))
                      if word == 0xffffffff || word == 0xeeeeeeee {return true}
                      return word >> 16 < plane.imageSets.count &&
                          (plane.flags & 1 == 0 || Int(word & 0xffff) < world.tileDescriptions.count)
                  }) else {
                throw Rejection.invalid("Invalid tile grid.")
            }
            guard plane.name.utf8.count < 64 else {throw Rejection.invalid("Unterminated plane name.")}
            guard plane.imageSets.allSatisfy({$0.utf8.count < 128 && $0.utf8.allSatisfy{$0 < 128}}) else {
                throw Rejection.unsupported("Extended tile image names.")
            }
            for object in plane.objects {
                // Original 4c9ac0 uses a 1024-byte automatic string buffer.
                guard object.words[1...4].allSatisfy({$0 < 1024}) else {
                    throw Rejection.invalid("Oversized object string record.")
                }
                guard [object.name,object.logic,object.imageSet,object.sound].allSatisfy({$0.utf8.count < 128 && $0.utf8.allSatisfy{$0 < 128}}) else {
                    throw Rejection.unsupported("Extended object strings.")
                }
            }
        }
        guard world.tileDescriptions.allSatisfy({$0.width > 0 && $0.width <= 64 && $0.height > 0 && $0.height <= 64}) else {
            throw Rejection.invalid("Invalid tile descriptions.")
        }
        self.data = data;self.world = world;self.level = base
    }
}
