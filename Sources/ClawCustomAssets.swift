import Foundation
import CryptoKit

/// Read-only, bounded Windows-path view of one WWD's companion directory.
/// No downloaded code is evaluated and symbolic links never enter the package.
struct ClawCustomAssets {
    struct File { let path: String; let url: URL; let size: Int }
    let worldURL: URL
    let root: URL?
    let files: [String: File]
    private let imageDirectories:Set<String>
    static let maximumBytes = 256 * 1024 * 1024
    static func key(_ path: String) throws -> String {
        let parts = path.replacingOccurrences(of:"\\",with:"/").split(separator:"/",omittingEmptySubsequences:false)
        guard !parts.isEmpty, parts.count <= 32, parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." && !$0.contains(":") && !$0.contains("\0") }) else {
            throw AssetError.invalid("Invalid package path: \(path)")
        }
        return parts.joined(separator:"/").uppercased()
    }
    init(worldURL: URL) throws {
        self.worldURL = worldURL
        let parent = worldURL.deletingLastPathComponent(), stem = worldURL.deletingPathExtension().lastPathComponent.uppercased()
        let siblings = try FileManager.default.contentsOfDirectory(at:parent,includingPropertiesForKeys:[.isDirectoryKey,.isSymbolicLinkKey])
        let matches = try siblings.filter { url in
            let values = try url.resourceValues(forKeys:[.isDirectoryKey])
            return url.lastPathComponent.uppercased() == stem && values.isDirectory == true
        }
        guard matches.count <= 1 else {throw AssetError.invalid("Ambiguous companion directory: \(stem)")}
        root = matches.first
        var found:[String:File] = [:], total = 0
        if let root {
            guard try root.resourceValues(forKeys:[.isSymbolicLinkKey]).isSymbolicLink != true else {throw AssetError.invalid("Linked companion directory")}
            guard let iterator = FileManager.default.enumerator(at:root,includingPropertiesForKeys:[.isRegularFileKey,.isDirectoryKey,.isSymbolicLinkKey,.fileSizeKey]) else {throw AssetError.invalid("Unreadable companion directory")}
            for case let url as URL in iterator {
                let values = try url.resourceValues(forKeys:[.isRegularFileKey,.isSymbolicLinkKey,.fileSizeKey])
                guard values.isSymbolicLink != true else {throw AssetError.invalid("Linked package asset: \(url.lastPathComponent)")}
                let path = String(url.path.dropFirst(root.path.count+1)), folded = try Self.key(path)
                guard path.utf8.count <= 240 else {throw AssetError.invalid("Package path too long")}
                if values.isRegularFile == true {
                    let size = values.fileSize ?? 0
                    guard found[folded] == nil, size <= 16*1024*1024, found.count < 30000 else {throw AssetError.invalid("Duplicate or oversized package asset: \(path)")}
                    total += size
                    guard total <= Self.maximumBytes else {throw AssetError.invalid("Package exceeds 256 MiB")}
                    found[folded] = File(path:folded,url:url,size:size)
                }
            }
        }
        files = found
        imageDirectories = Set(found.keys.compactMap { path in
            guard ["PID","BMP","PCX"].contains(String(path.split(separator:".").last ?? "")) else {return nil}
            return path.split(separator:"/").dropLast().joined(separator:"_")
        })
    }
    func data(_ path:String) throws -> Data? {
        guard let file = files[try Self.key(path)] else {return nil}
        let data = try Data(contentsOf:file.url)
        guard data.count == file.size else {throw AssetError.invalid("Package changed while loading: \(file.path)")}
        return data
    }
    func containsImages(_ name:String) -> Bool {
        let target = name.uppercased().replacingOccurrences(of:"/",with:"_")
        return imageDirectories.contains(target)
    }
    /// Files/open-in can grant a document alone, but cannot grant its siblings.
    /// Selecting the containing folder grants both on iPad as well as Mac.
    static func importPackage(_ selection:URL, into destination:URL) throws -> [URL] {
        let fm = FileManager.default
        let isFolder = try selection.resourceValues(forKeys:[.isDirectoryKey]).isDirectory == true
        let candidates = isFolder ? try fm.contentsOfDirectory(at:selection,includingPropertiesForKeys:nil).filter{$0.pathExtension.lowercased() == "wwd"} : [selection]
        guard !candidates.isEmpty else {throw AssetError.invalid("Choose the folder containing a WWD and its same-name companion folder.")}
        try fm.createDirectory(at:destination,withIntermediateDirectories:true)
        var imported:[URL] = []
        for source in candidates.sorted(by:{$0.lastPathComponent < $1.lastPathComponent}) {
            guard source.pathExtension.lowercased() == "wwd" else {throw AssetError.invalid("Choose a WWD or its containing folder.")}
            // Parsing and package bounds precede any destination mutation.
            _ = try ClawCustomCapabilities.preflight(source)
            let package = try ClawCustomAssets(worldURL:source)
            if source.standardizedFileURL.deletingLastPathComponent() == destination.standardizedFileURL {imported.append(source);continue}
            var target = destination.appendingPathComponent(source.lastPathComponent), suffix = 1
            while fm.fileExists(atPath:target.path) || fm.fileExists(atPath:target.deletingPathExtension().path) {
                target = destination.appendingPathComponent(source.deletingPathExtension().lastPathComponent+" (\(suffix)).wwd");suffix += 1
            }
            let staging = destination.appendingPathComponent(".import-"+UUID().uuidString,isDirectory:true)
            try fm.createDirectory(at:staging,withIntermediateDirectories:false)
            defer {try? fm.removeItem(at:staging)}
            let stagedWorld = staging.appendingPathComponent(target.lastPathComponent)
            try fm.copyItem(at:source,to:stagedWorld)
            let stagedAssets = stagedWorld.deletingPathExtension()
            if package.root != nil {
                try fm.createDirectory(at:stagedAssets,withIntermediateDirectories:false)
                for file in package.files.values {
                    let to = stagedAssets.appendingPathComponent(file.path)
                    try fm.createDirectory(at:to.deletingLastPathComponent(),withIntermediateDirectories:true)
                    try fm.copyItem(at:file.url,to:to)
                }
                try fm.moveItem(at:stagedAssets,to:target.deletingPathExtension())
            }
            do {try fm.moveItem(at:stagedWorld,to:target)}
            catch {if package.root != nil {try? fm.removeItem(at:target.deletingPathExtension())};throw error}
            imported.append(target)
        }
        return imported
    }

    /// The retail registry recognizes PID, BMP, PCX and ANI, not PNG. Preserve
    /// PNGs in the import, but do not invent a runtime mapping for editor files.
    /// BMPs use a native format adapter into the existing indexed PID renderer.
    func archive() throws -> Data {
        final class Folder { var folders:[String:Folder] = [:]; var files:[String:Data] = [:] }
        let root = Folder()
        func insert(_ path:String,_ raw:Data) throws {
            let parts = path.split(separator:"/").map(String.init)
            let ext = URL(fileURLWithPath:path).pathExtension
            var folder = root
            for name in parts.dropLast() {
                if folder.folders[name] == nil {folder.folders[name] = Folder()}
                folder = folder.folders[name]!
            }
            folder.files[parts.last!] = ext == "BMP" ? try Self.bitmapPID(raw,compressed:parts[0] != "TILES"):ext == "PID" ? try Self.surfacePID(raw):ext == "ANI" ? Self.surfaceANI(raw):ext == "WAV" ? try Self.surfaceWAV(raw):raw
        }
        // Local, prepared helper assets share the package archive's lifetime.
        // Reserved roots cannot be supplied by a level and never alter the disc.
        if let helpers = Bundle.main.resourceURL?.appendingPathComponent("GameData/CRAZYHOOK"),
           let manifest = try? Data(contentsOf:helpers.appendingPathComponent("manifest.json")),
           let value = try JSONSerialization.jsonObject(with:manifest) as? [String:Any],
           let entries = value["files"] as? [String:String] {
            for path in entries.keys.sorted() {
                let key = try Self.key(path)
                guard ["HELPERIMAGES","HELPERANIS","HELPERSOUNDS"].contains(key.split(separator:"/").first.map(String.init) ?? "") else {throw AssetError.invalid("Helper resource root")}
                try insert(key,Data(contentsOf:helpers.appendingPathComponent(path)))
            }
        }
        for path in files.keys.sorted() {
            let ext = URL(fileURLWithPath:path).pathExtension
            guard ["PID","BMP","PCX","ANI","WAV","XMI"].contains(ext) else {continue}
            let parts = path.split(separator:"/").map(String.init)
            guard parts.count >= 2,["IMAGES","TILES","LEVEL","ANIS","SOUNDS","MUSIC","SCREENS"].contains(parts[0]) else {continue}
            let raw = try data(path)!
            // Keep the original extension/type ordering. The physical resource
            // adapter below changes only the BMP's encoded bytes/type to PID.
            try insert(path,raw)
        }
        var result = Data(repeating:0,count:168)
        func word(_ n:Int)->Data { var v = UInt32(n).littleEndian;return withUnsafeBytes(of:&v){Data($0)} }
        func emit(_ folder:Folder) -> (Int,Int) {
            var records = Data()
            for name in folder.folders.keys.sorted() {
                let (offset,length) = emit(folder.folders[name]!)
                for n in [1,offset,length,0] {records.append(word(n))}
                records.append(contentsOf:name.utf8);records.append(0)
            }
            for (index,name) in folder.files.keys.sorted().enumerated() {
                let raw = folder.files[name]!, offset = result.count
                result.append(raw)
                let url = URL(fileURLWithPath:name), ext = url.pathExtension
                let type = ext
                let tag = type.utf8.reduce(0){($0<<8)|Int($1)}
                for n in [0,offset,raw.count,0,index,tag,0] {records.append(word(n))}
                records.append(contentsOf:url.deletingPathExtension().lastPathComponent.utf8);records.append(contentsOf:[0,0])
            }
            let offset = result.count; result.append(records);return (offset,records.count)
        }
        let (offset,length) = emit(root)
        for (at,value) in [(127,1),(131,offset),(135,length),(143,result.count),(147,1),(151,1),(155,1),(159,1),(163,1)] {result.replaceSubrange(at..<at+4,with:word(value))}
        result[167] = 1
        return result
    }
    /// Adapt Microsoft IMA ADPCM to the PCM stream understood by the retail
    /// resource loader. Conversion is in memory; imported WAVs stay unchanged.
    static func surfaceWAV(_ data:Data) throws -> Data {
        func invalid() -> AssetError { .invalid("Malformed IMA ADPCM WAV") }
        func u16(_ i:Int)->Int {Int(data[i]) | Int(data[i+1]) << 8}
        func u32(_ i:Int)->Int {u16(i) | u16(i+2) << 16}
        guard data.count >= 12,Array(data[0..<4]) == Array("RIFF".utf8),
              Array(data[8..<12]) == Array("WAVE".utf8) else {return data}
        var fmt:Range<Int>?,payload:Range<Int>?,fact:Int?,at = 12
        let end = min(data.count,u32(4)+8)
        while at+8 <= end {
            let size = u32(at+4),start = at+8
            guard size <= end-start else {throw invalid()}
            let tag = String(bytes:data[at..<at+4],encoding:.ascii)
            if tag == "fmt " {fmt = start..<start+size}
            if tag == "data" {payload = start..<start+size}
            if tag == "fact",size >= 4 {fact = u32(start)}
            at = start+size+(size & 1)
        }
        guard let fmt,fmt.count >= 2,u16(fmt.lowerBound) == 17 else {return data}
        let f = fmt.lowerBound
        guard fmt.count >= 20,let payload else {throw invalid()}
        let channels = u16(f+2),rate = u32(f+4),block = u16(f+12),frames = u16(f+18)
        guard (1...2).contains(channels),rate > 0,rate <= 192000,u16(f+14) == 4,
              u16(f+16) >= 2,block >= channels*4,block <= 65536,
              frames == 1+(block-channels*4)*2/channels,
              payload.count > 0 else {throw invalid()}
        let steps = [7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,494,544,598,658,724,796,876,963,1060,1166,1282,1411,1552,1707,1878,2066,2272,2499,2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,7132,7845,8630,9493,10442,11487,12635,13899,15289,16818,18500,20350,22385,24623,27086,29794,32767]
        let changes = [-1,-1,-1,-1,2,4,6,8]
        var pcm = Data(),total = 0,offset = payload.lowerBound
        while offset < payload.upperBound {
            let count = min(block,payload.upperBound-offset)
            guard count >= channels*4,(count-channels*4) % (channels*4) == 0 else {throw invalid()}
            var predictors = [Int](),indices = [Int](),samples = [[Int]]()
            for channel in 0..<channels {
                let h = offset+channel*4,index = Int(data[h+2])
                guard index <= 88,data[h+3] == 0 else {throw invalid()}
                let predictor = Int(Int16(bitPattern:UInt16(u16(h))))
                predictors.append(predictor);indices.append(index);samples.append([predictor])
            }
            var cursor = offset+channels*4
            while cursor < offset+count {
                for channel in 0..<channels {
                    for byte in data[cursor..<cursor+4] {
                        for nibble in [Int(byte & 15),Int(byte >> 4)] {
                            let step = steps[indices[channel]]
                            var delta = step >> 3
                            if nibble & 1 != 0 {delta += step >> 2}
                            if nibble & 2 != 0 {delta += step >> 1}
                            if nibble & 4 != 0 {delta += step}
                            predictors[channel] = max(-32768,min(32767,predictors[channel]+(nibble & 8 == 0 ? delta:-delta)))
                            indices[channel] = max(0,min(88,indices[channel]+changes[nibble & 7]))
                            samples[channel].append(predictors[channel])
                        }
                    }
                    cursor += 4
                }
            }
            for frame in 0..<samples[0].count {
                for channel in 0..<channels {
                    var sample = Int16(samples[channel][frame]).littleEndian
                    withUnsafeBytes(of:&sample) {pcm.append(contentsOf:$0)}
                }
            }
            total += samples[0].count;offset += count
            guard pcm.count <= maximumBytes else {throw invalid()}
        }
        if let fact {
            guard fact > 0,fact <= total else {throw invalid()}
            pcm = Data(pcm.prefix(fact*channels*2))
        }
        var result = Data()
        func word(_ n:Int,_ bytes:Int) {for i in 0..<bytes {result.append(UInt8(truncatingIfNeeded:n >> (i*8)))}}
        result.append(contentsOf:"RIFF".utf8);word(36+pcm.count,4);result.append(contentsOf:"WAVEfmt ".utf8)
        word(16,4);word(1,2);word(channels,2);word(rate,4);word(rate*channels*2,4)
        word(channels*2,2);word(16,2);result.append(contentsOf:"data".utf8);word(pcm.count,4);result.append(pcm)
        return result
    }
    /// Some custom exporters encode surface PID runs continuously across
    /// scanlines. Repack those runs for the native row decoder without changing
    /// a pixel, flags, anchor or palette. Package files remain read-only.
    static func surfacePID(_ data:Data) throws -> Data {
        guard data.count >= 32 else {throw AssetError.invalid("Truncated PID")}
        func word(_ at:Int)->UInt32 {data.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:at,as:UInt32.self)}}
        let flags = word(4)
        if flags & 0x20 != 0 {return data}
        let width = Int(word(8)),height = Int(word(12))
        guard width > 0,width <= 4096,height > 0,height <= 4096 else {throw AssetError.invalid("Invalid surface PID geometry")}
        let end = data.count-(flags & 0x80 != 0 ? 768:0)
        guard end >= 32 else {throw AssetError.invalid("Truncated surface PID palette")}
        var pixels = Data(),at = 32,crossesRow = false
        pixels.reserveCapacity(width*height)
        while pixels.count < width*height {
            guard at < end else {throw AssetError.invalid("Truncated surface PID pixels")}
            let tag = data[at];at += 1
            let count:Int,index:UInt8
            if tag & 0xc0 == 0xc0 {
                guard at < end else {throw AssetError.invalid("Truncated surface PID run")}
                count = Int(tag & 0x3f);index = data[at];at += 1
            } else {count = 1;index = tag}
            // Exporters may finish the final run in surface padding. Keep
            // exactly the declared visible pixels; no out-of-image store.
            let visible = min(count,width*height-pixels.count)
            if pixels.count%width+count > width {crossesRow = true}
            pixels.append(contentsOf:repeatElement(index,count:visible))
        }
        if !crossesRow {return data}
        var result = Data(data.prefix(32))
        for y in 0..<height {
            var x = 0
            while x < width {
                let start = x,index = pixels[y*width+x]
                repeat {x += 1} while x < width && x-start < 63 && pixels[y*width+x] == index
                if x-start > 1 || index >= 0xc0 {result.append(0xc0|UInt8(x-start))}
                result.append(index)
            }
        }
        result.append(data.suffix(from:at))
        return result
    }
    /// The sampled Cultist ANI declares more fixed frames than it contains.
    /// Bound only the unambiguous fixed-record form: no sound/string commands,
    /// no partial record, and at most two zero padding bytes. Preserve every
    /// supplied frame and leave all other streams to the ordinary loader.
    static func surfaceANI(_ data:Data) -> Data {
        // These two byte-identical exports ship in Cat and Cultist Island.
        // Six frame records are present, but three omit their final padding
        // word. The nine-pixel offsets are ordinary frame coordinates.
        // Repair only the pinned files; preserve their actual frames, timing
        // and offsets rather than consuming the next frame as padding.
        if data.count == 146,["7f5e546af4ab2ba8eafddc873eb030aab5f6b0f8478e8007f425c5c6bf7b8ab4",
                              "94367ba78ebcfe83884eeb385a996acb779b0e9b3b37615584ecb134f4ef8d1b"].contains(SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined()) {
            var result = Data(data.prefix(32))
            let starts = [32,52,72,90,108,126,146]
            for i in 0..<6 {
                var frame = Data(data[starts[i]..<starts[i+1]])
                frame.append(Data(repeating:0,count:20-frame.count))
                result.append(frame)
            }
            return result
        }
        // The release's final plasma explosion frame ends after its X field.
        // Zero-extend only this pinned export; retain its stop timing and all
        // supplied fields. Unknown truncated animations remain rejected.
        if data.count == 391,SHA256.hash(data:data).map({String(format:"%02x",$0)}).joined() == "6439129a4082ba596883d8a706f6dd40ce189d6cdf2c4abd116735b568c3adf1" {
            return data+Data(repeating:0,count:6)
        }
        guard data.count >= 52 else {return data}
        func word(_ at:Int)->UInt32 {data.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:at,as:UInt32.self)}}
        let nameBytes = Int(word(16))
        guard nameBytes <= 256,32+nameBytes <= data.count else {return data}
        if nameBytes > 0 {
            let name = data[32..<32+nameBytes]
            guard (name.last == 0 ? name.dropLast():name[...]).allSatisfy({$0 >= 32 && $0 < 127}) else {return data}
        }
        let start = 32+nameBytes,frames = (data.count-start)/20,tail = (data.count-start)%20
        guard word(0) == 32,frames > 0,word(12) > UInt32(frames),tail <= 2,
              data.suffix(tail).allSatisfy({$0 == 0}) else {return data}
        for i in 0..<frames {
            let at = start+i*20
            guard word(at) == 0x30000,word(at+4) == 0 else {return data}
        }
        var result = data,count = UInt32(frames).littleEndian
        withUnsafeBytes(of:&count) {result.replaceSubrange(12..<16,with:$0)}
        return result
    }

    static func bitmapPID(_ data:Data,compressed:Bool = true) throws -> Data {
        guard data.count >= 54, data[0] == 66,data[1] == 77 else {throw AssetError.invalid("Invalid BMP")}
        func u32(_ at:Int)->UInt32 {data.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:at,as:UInt32.self)}}
        let width = Int(Int32(bitPattern:u32(18))), signedHeight = Int(Int32(bitPattern:u32(22)))
        let bits = Int(data[28])|Int(data[29])<<8, compression = u32(30), pixelStart = Int(u32(10)), dib = Int(u32(14))
        guard width > 0, width <= 4096,signedHeight != 0,abs(signedHeight) <= 4096, pixelStart <= data.count else {throw AssetError.invalid("Invalid BMP geometry")}
        let height = abs(signedHeight), stride = ((width*bits+31)/32)*4
        var palette = Data(repeating:0,count:768), pixels = Data(repeating:0,count:width*height)
        if [4,8].contains(bits), compression == 0 || compression == 3 {
            let colors = u32(46) == 0 ? 1<<bits:Int(u32(46)), start = 14+dib
            guard colors <= 256,start >= 54,start+colors*4 <= pixelStart, stride*height <= data.count-pixelStart else {throw AssetError.invalid("Truncated BMP")}
            for i in 0..<colors {for c in 0..<3 {palette[i*3+c] = data[start+i*4+2-c]}}
            for y in 0..<height {for x in 0..<width {
                let at = pixelStart+(signedHeight > 0 ? height-1-y:y)*stride+(bits == 8 ? x:x/2)
                pixels[y*width+x] = bits == 8 ? data[at]:(x%2 == 0 ? data[at]>>4:data[at]&15)
            }}
        } else if bits == 24,compression == 0 {
            guard stride*height <= data.count-pixelStart else {throw AssetError.invalid("Truncated BMP")}
            // Indexed host surfaces use an explicit RGB cube for true-colour
            // BMPs. The sampled 24-bit file is an unused LOADING.bmp; the
            // published loading-screen path specifically asks for LOADING.PCX.
            for i in 0..<256 {
                palette[i*3] = UInt8((i>>5)*255/7)
                palette[i*3+1] = UInt8(((i>>2)&7)*255/7)
                palette[i*3+2] = UInt8((i&3)*255/3)
            }
            for y in 0..<height {for x in 0..<width {
                let at = pixelStart+(signedHeight > 0 ? height-1-y:y)*stride+x*3
                pixels[y*width+x] = (data[at+2]&0xe0)|((data[at+1]>>3)&0x1c)|(data[at]>>6)
            }}
        } else {
            throw AssetError.invalid("Unsupported BMP encoding: \(bits) bits, compression \(compression)")
        }
        var output = Data()
        // Plane drawing consumes a surface, whereas sprites also support the
        // compressed-image field. Tile BMPs therefore use the surface PID form.
        for value in [10,compressed ? 160:129,width,height,0,0,0,0] {var word = UInt32(value).littleEndian;withUnsafeBytes(of:&word){output.append(contentsOf:$0)}}
        if !compressed {
            // Surface rows use 0xc0|count followed by an index for repeats;
            // high literal indices must also be escaped as a one-pixel run.
            for y in 0..<height {
                var x = 0
                while x < width {
                    let start = x,index = pixels[y*width+x]
                    while x < width,x-start < 63,pixels[y*width+x] == index {x += 1}
                    if x-start > 1 || index >= 0xc0 {output.append(0xc0|UInt8(x-start))}
                    output.append(index)
                }
            }
            output.append(palette);return output
        }
        // Canonical PID row grammar: high-bit runs skip transparent pixels;
        // low-bit runs contain literal palette indices, at most 127 per run.
        for y in 0..<height {
            var x = 0
            while x < width {
                let start = x, transparent = pixels[y*width+x] == 0
                while x < width,x-start < 127,(pixels[y*width+x] == 0) == transparent {x += 1}
                output.append(UInt8(x-start)+(transparent ? 128:0))
                if !transparent {output.append(pixels.subdata(in:y*width+start..<y*width+x))}
            }
        }
        output.append(palette);return output
    }
}

/// Shared by the picker, document import and guarded runtime callbacks. Static
/// inspection describes requirements; it never executes or rejects dormant code.
struct ClawCustomCapabilities {
    enum Kind:String {case missing = "Missing companion file", malformed = "Malformed custom level", pending = "Not implemented", execution = "Unsupported execution", script = "Script error"}
    struct Requirement:Codable {
        let feature:String
        let provenance:String
        let status:String
    }
    struct Report:Codable {
        let file:String
        let requirements:[Requirement]
        let dynamicRequirements:String
    }
    struct Failure:LocalizedError {
        let kind:Kind
        let detail:String
        var errorDescription:String? {"\(kind.rawValue): \(detail)"}
    }
    static let groups:[String:[String]] = [
        "assets":["animation-files","animations","asset-mapping-api","bmp-files","custom-splash","images","level-overrides","loading-screen","pcx-files","pid-files","png-files","tiles"],
        "lua":["builtin-dispatch","bundled-core-script","ffi-struct-values","lifecycle-hooks","lua-scripts","module-loading","wwd-customlogic"],
        "audio":["audio-api","music","sound-files","sounds","xmi-files"],
        "planes":["fill-tiles","mask-tile-attributes","more-than-10000-objects","more-than-three-planes","non-64-tiles","plane-api","unknown-wwd-header-plane-flags"],
        "gameplay":["game-control-api","object-api","player-physics"],
        "checkpoints":["super-checkpoint"],"bindings":["code-patching","ffi-address-access","ffi-or-memory"],
        "presentation":["camera-api","input-api","presentation-api"],"persistence":["script-persistence"],
        "palettes":["palette-api","palette-files","palettes"],
        "diagnostics":["native-binary-files","native-library-load","plugin-request"]]
    static func preflight(_ url:URL) throws -> Report {
        let world:ClawCustomWorld
        do {world = try ClawCustomWorld(url:url)}
        catch let error as ClawCustomWorld.Rejection {throw error}
        catch {throw Failure(kind:.missing,detail:"WWD \(url.path): \(error.localizedDescription)")}
        let package = try ClawCustomAssets(worldURL:url)
        if package.root == nil,let object = world.world.planes.flatMap(\.objects).first(where:{$0.imageSet.hasPrefix("CUSTOM_") || $0.sound.hasPrefix("CUSTOM_")}) {
            throw Failure(kind:.missing,detail:"companion \(url.deletingPathExtension().path)/ for object \(object.id) '\(object.name)', image \(object.imageSet), sound/animation \(object.sound); import the containing folder.")
        }
        var rows:[Requirement] = []
        for plane in world.world.planes {
            rows.append(Requirement(feature:"plane",provenance:"WWD plane \(plane.name), \(plane.width)x\(plane.height), flags \(plane.flags)",status:"native"))
            for object in plane.objects where object.logic == "CustomLogic" {
                let path = "LOGICS/"+object.name.replacingOccurrences(of:":",with:"/").uppercased()+".LUA"
                guard package.files[path] != nil else {
                    throw Failure(kind:.missing,detail:"\(path) for object \(object.id) '\(object.name)' in \(plane.name); import \(url.deletingPathExtension().lastPathComponent)/ with the WWD.")
                }
                rows.append(Requirement(feature:"wwd-customlogic",provenance:"object \(object.id) '\(object.name)' -> \(path)",status:"bounded Lua callback"))
            }
        }
        for path in package.files.keys.sorted() {
            if path.hasSuffix(".LUA"),let bytes = try package.data(path) {
                let lines = String(decoding:bytes,as:UTF8.self).components(separatedBy:"\n")
                for (index,line) in lines.enumerated() where !line.trimmingCharacters(in:.whitespaces).hasPrefix("--") && !line.trimmingCharacters(in:.whitespaces).isEmpty {
                    // Lexical provenance is intentionally not a dependency proof.
                    rows.append(Requirement(feature:"lua-scripts",provenance:"\(path):\(index+1): \(line.prefix(240))",status:"requires guarded runtime evaluation"))
                }
            } else {
                rows.append(Requirement(feature:"package-file",provenance:path,status:["DLL","SO","DYLIB","EXE"].contains(URL(fileURLWithPath:path).pathExtension) ? "presence only; not a dependency":"native resource candidate"))
            }
        }
        return Report(file:url.lastPathComponent,requirements:rows,dynamicRequirements:"Guarded callbacks resolve portable operations; required external execution is refused. Lua dialect guards do not certify whole-release compatibility.")
    }
    static func runtime(_ detail:String,context:String) -> Failure {
        let kind:Kind = detail.contains("UnsupportedExecution:") ? .execution :
            detail.contains("NotImplemented:") ? .pending :
            (detail.contains("ModuleNotFound:") || detail.contains("LogicNotFound:") || detail.contains("Missing companion file:")) ? .missing : .script
        return Failure(kind:kind,detail:"\(context): \(detail)")
    }
}
