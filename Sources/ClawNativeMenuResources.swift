import Foundation
import CryptoKit
import zlib // links the system zlib used by ClawNativeLevelServices.cpp

// The recovered archive, directory and resource owners use the scene's heap.
// Only allocation and read-only file I/O are supplied here. No native directory
// tree or preselected game resource substitutes for the admitted graph.
final class ClawNativeMenuResources {
    enum Failure: Error { case invalid(String) }
    // Original disc, or the deterministic local archive assembled by
    // setup-game-data.py from the pinned Claw Recluse 1.4.5.4 ZIP.
    // Never trust a caller-supplied manifest as an archive hash allowlist.
    private static let supportedArchiveHashes: Set<String> = [
        "b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596",
        "24da719bb0c18a306ecac7059c748ea8acdcde5f4f830723df449f234635249f"
    ]
    let heap: ClawTokenHeap
    let archiveURL: URL
    private var installedArchiveHash: String?
    private let host = UnsafeMutablePointer<ClawHost>.allocate(capacity:1)
    private var allocations: Set<UInt32> = []
    private var allocationSizes:[UInt32:UInt32] = [:]
    private var allocationIdentities: [UInt32: ClawTokenHeap.AllocationIdentity] = [:]
    private var allocationOrigins:[UInt32:[String]] = [:]
    var traceAllocations = false
    private(set) var cleanupDetails:[[String:Any]] = []
    private var files: [UInt32:FileHandle] = [:]
    private var retiredFiles: Set<UInt32> = []
    private var packageURL: URL?
    private(set) var packageArchive: UInt32 = 0
    private var packageOwner: ClawNativeResourceArchive?
    private var frames: [UInt32] = []
    var currentFrame:UInt32 {frames.last ?? stack}
    private var diagnosticFrames:[UInt32] = []
    var diagnosticFrame:UInt32? {diagnosticFrames.last}
    private var closed = false
    private(set) var archive: UInt32 = 0
    var faultAddress: UInt32 { host.pointee.faultAddress }
    private(set) var events: [[String:Any]] = []
    var observePhysical:(([String:Any])->Void)?
    private func record(_ event:[String:Any]) {events.append(event);observePhysical?(event)}
    private(set) var cleanupRemaining = 0
    private(set) var cleanupTokens:[UInt32] = []
    private(set) var destroyedArchive = Data()
    private(set) var invalidReleaseToken:UInt32 = 0
    // Largest spatial grid (eight-byte cells, 0x4f45f0 / 0x4a4590) the native CRT vector iterators accept;
    // Level 5 allocates 0x12000 cells. One owned allocation still bounds every grid.
    // Measured largest plane in the compatibility sample: Midnight Espionage.
    static let gridCellLimit:UInt32 = 1_105_000
    private var worldBufferSizes = Set<UInt32>()
    func configureWorldBuffers(_ world:ClawWorld?) {
        worldBufferSizes.removeAll()
        guard let world else {return}
        let decoded = UInt32(world.decodedBytes.count)
        worldBufferSizes.formUnion([decoded,decoded+32,decoded+64])
        for plane in world.planes {
            let cells = UInt32(plane.width*plane.height)
            worldBufferSizes.formUnion([cells*4,cells*8,cells*8+4])
        }
        worldBufferSizes = worldBufferSizes.filter{$0 <= ClawTokenHeap.worldBufferByteLimit}
    }
    // Failure trace depth; --long-trace keeps more for diagnosis.
    static let traceDepth = ProcessInfo.processInfo.environment["CLAW_TRACE_DEPTH"].flatMap {Int($0)} ?? (ProcessInfo.processInfo.arguments.contains("--long-trace") ? 3000:16)
    private var recent = ClawTraceRing(capacity:ClawNativeMenuResources.traceDepth)
    private(set) var failureTrace:[String] = []
    private var drawingWorld:UInt32 = 0
    // Read-only diagnostics at the failed tile/image boundary, before teardown.
    func missingTileFrames(world:UInt32)->[[String:Any]] {
        guard world != 0,let count = word(world+0x3c),count <= 16,
              let planes = word(world+0x38) else {return []}
        var result:[[String:Any]] = []
        for index in 0..<count {
            guard let plane = word(planes+index*4),let width = word(plane+0x28),let height = word(plane+0x2c),
                  UInt64(width)*UInt64(height) <= 4_000_000,let tiles = word(plane+0x20),let sets = word(plane+0xa0),
                  (word(plane+8) ?? 0) & 2 == 0 else {continue}
            var seen = Set<UInt32>()
            for cell in 0..<(width*height) {
                guard let tile = word(tiles+cell*4),tile != 0xffffffff,tile != 0xeeeeeeee,seen.insert(tile).inserted else {continue}
                let set = word(sets+(tile>>16)*4) ?? 0,frame = tile & 0xffff
                let table = word(set+0x14) ?? 0
                let image = word(table+frame*4) ?? 0
                if table == 0 || frame < (word(set+0x64) ?? 0) || frame > (word(set+0x68) ?? 0) ||
                   image == 0 || word(image+0x2c) == nil || word(image+0x2c) == 0 {
                    result.append(["plane":index,"tile":tile,"set":set,"frame":frame,
                        "image":image,"surface":word(image+0x2c) ?? 0,"compressed_image":word(image+0x30) ?? 0,
                        "first":word(set+0x64) ?? 0,"last":word(set+0x68) ?? 0])
                    if result.count >= 32 {return result}
                }
            }
        }
        return result
    }
    private(set) var mathServiceCounts:[UInt32:UInt64] = [:]
    // Diagnostic only: per-entry invoke counts while CLAW_REAL_SPEED_LOG is set.
    static let countInvokes = ProcessInfo.processInfo.environment["CLAW_REAL_SPEED_LOG"] != nil
    private(set) var invokeCounts:[UInt32:UInt64] = [:]
    var missingOwner: UInt32?
    var clockCaller:UInt32 {functions.last ?? 0}
    var missingService: UInt32?
    var missingResource: String?
    // Session resource overlays must be installed after retail registration,
    // immediately before a music lookup or selection consumes the registry.
    var beforeMusicLookup: (() -> Void)?
    // Mac developer fixture at the existing physical decompression boundary.
    private var localTestPayload: Data?
    private var localTestSourceSHA: String?
    private var testObjectRecords: [[String:Any]] = []
    private(set) var localTestWorldEvidence: [String:Any] = [:]
    var testLevelEvidence: [String:Any] {
        guard !localTestWorldEvidence.isEmpty else {return [:]}
        var result = localTestWorldEvidence
        result["objects"] = testObjectRecords.map {record -> [String:Any] in
            var value = record
            let candidates = heap.debugAllocationBases.filter {token in
                heap.lookupBytes(token,count:0x174) != nil && word(token+0x4c) == record["source_x"] as? UInt32 &&
                abs(Int64(word(token+0x50) ?? 0)-Int64(record["source_y"] as? UInt32 ?? 0)) <= 96 &&
                word(token+0xa0) == token && (word(token+0x170) ?? 0) > 0x10000
            }.sorted {left,right in
                abs(Int64(word(left+0x50) ?? 0)-Int64(record["source_y"] as? UInt32 ?? 0)) <
                abs(Int64(word(right+0x50) ?? 0)-Int64(record["source_y"] as? UInt32 ?? 0))
            }
            // Pickup callbacks can replace the WWD actor with a generated-id
            // actor. Prefer its original id, then inspect the same placement.
            if let actor = candidates.first(where:{word($0+4) == record["id"] as? UInt32}) ?? candidates.first {
                value["actor"] = actor
                value["runtime_id"] = word(actor+4) ?? 0
                value["x"] = word(actor+0x4c) ?? 0;value["y"] = word(actor+0x50) ?? 0
                value["image_set"] = word(actor+0x170) ?? 0;value["image_index"] = word(actor+0x16c) ?? UInt32.max
            }
            return value
        }
        return result
    }
    func installLocalTestWorld(_ url: URL) throws -> UInt32 {
        #if targetEnvironment(macCatalyst)
        guard ProcessInfo.processInfo.environment["CLAW_LOCAL_TEST_LEVELS"] == "1",
              ProcessInfo.processInfo.arguments.contains("--mute"),
              url.resolvingSymlinksInPath().path.contains("/work/test-levels/"),
              localTestWorldEvidence.isEmpty else {
            throw Failure.invalid("Local test levels require CLAW_LOCAL_TEST_LEVELS=1, --mute and work/test-levels/")
        }
        let data = try Data(contentsOf:url)
        let manifest = try JSONSerialization.jsonObject(with:Data(contentsOf:url.deletingPathExtension().appendingPathExtension("json"))) as? [String:Any]
        let digest = SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined()
        guard data.count >= 1524,data.count <= 16<<20,
              data.prefix(4) == Data([0xf4,5,0,0]),let level = manifest?["source_level"] as? Int,
              (1...14).contains(level),manifest?["output_sha256"] as? String == digest else {
            throw Failure.invalid("Invalid local WWD or generator manifest")
        }
        guard let sourceSHA = manifest?["source_compressed_sha256"] as? String,
              let objects = manifest?["objects"] as? [[String:Any]] else {throw Failure.invalid("Missing test-level provenance")}
        func wordAt(_ offset:Int)->UInt32 {data.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)}}
        let offset = Int(wordAt(736)),length = Int(wordAt(744))
        guard offset == 1524,length > 0,length <= 16<<20,offset <= data.count else {throw Failure.invalid("Invalid test payload")}
        var payload = Data(repeating:0,count:length)
        if wordAt(8) & 2 != 0 {
            var written:UInt32 = 0
            let result = payload.withUnsafeMutableBytes {out in data.withUnsafeBytes {input in
                claw_level_uncompress(out.baseAddress!.assumingMemoryBound(to:UInt8.self),UInt32(length),
                    input.baseAddress!.assumingMemoryBound(to:UInt8.self).advanced(by:offset),UInt32(data.count-offset),&written)
            }}
            guard result == 0,written == length else {throw Failure.invalid("Invalid test compression")}
        } else {
            guard data.count-offset == length else {throw Failure.invalid("Invalid test payload length")}
            payload = data.subdata(in:offset..<data.count)
        }
        localTestPayload = payload;localTestSourceSHA = sourceSHA
        testObjectRecords = try objects.map {row in
            guard let id = row["id"] as? UInt32,let logic = row["logic"] as? String else {throw Failure.invalid("Invalid test object")}
            return ["id":id,"logic":logic,"source_x":row["x"] ?? 0,"source_y":row["y"] ?? 0]
        }
        localTestWorldEvidence = ["path":url.path,"sha256":digest,
            "runtime_level":level,"substitutions":0,"fixture":"WWD payload at physical 0x4d5fe0 decompression boundary"]
        return UInt32(level)
        #else
        throw Failure.invalid("Local test levels are available only in the Mac developer runner")
        #endif
    }
    var gameEntry: ClawEntry?
    var gameService: ((UInt32,UInt32,[UInt32])->UInt32?)?
    var dependency: ((ClawCall)->UInt32?)?
    var releaseExternalAllocation: ((UInt32)->Bool)?
    var openFileCount: Int { files.count }
    var liveAllocationCount: Int { allocations.count }
    var fault: UInt32 { host.pointee.fault }
    private let stack: UInt32
    private var scratch: [UInt32] = []
    private var scratchIdentities: [UInt32: (count: UInt32, identity: ClawTokenHeap.AllocationIdentity)] = [:]

    struct SavedState: Codable, Equatable {
        struct File: Codable, Equatable { let token: UInt32, offset: UInt64 }
        let allocations: [ClawSnapshotWitness], scratch: [ClawSnapshotWitness]
        let archive: UInt32, stack: UInt32, files: [File], retiredFiles: Set<UInt32>
        let tailThunks: [UInt32: UInt32], tailOnly: Set<UInt32>, frameExtents: [UInt32: UInt32], threadHead: UInt32
        let hasGameEntry: Bool, hasGameService: Bool, hasDependency: Bool, hasExternalRelease: Bool
        let mathCounts: [UInt32: UInt64], invokeCounts: [UInt32: UInt64], transportCounts: [String: UInt64]
        var archiveSHA256: String? = nil
    }
    private func snapshotBoundary() throws {
        guard frames.isEmpty, functions.isEmpty, diagnosticFrames.isEmpty,
              host.pointee.sourceContext == nil else { throw ClawSnapshotError.activeFrame }
        guard !closed, fault == 0, localTestPayload == nil, missingOwner == nil,
              missingService == nil, missingResource == nil else { throw ClawSnapshotError.invalidState }
    }
    func savedState() throws -> SavedState {
        try snapshotBoundary()
        let leases = try allocations.sorted().map { token -> ClawSnapshotWitness in
            guard let count = allocationSizes[token], let identity = allocationIdentities[token] else { throw ClawSnapshotError.invalidState }
            return ClawSnapshotWitness(heap: heap, token: token, count: count, identity: identity)
        }
        let scratchLeases = try scratch.map { token -> ClawSnapshotWitness in
            guard let span = scratchIdentities[token] else { throw ClawSnapshotError.invalidState }
            return ClawSnapshotWitness(heap: heap, token: token, count: span.count, identity: span.identity)
        }
        return SavedState(allocations: leases, scratch: scratchLeases, archive: archive, stack: stack,
            files: try files.keys.sorted().map { .init(token: $0, offset: try files[$0]!.offset()) }, retiredFiles: retiredFiles,
            tailThunks: tailThunks, tailOnly: tailOnly, frameExtents: frameExtents, threadHead: threadHead,
            hasGameEntry: gameEntry != nil, hasGameService: gameService != nil, hasDependency: dependency != nil,
            hasExternalRelease: releaseExternalAllocation != nil, mathCounts: mathServiceCounts, invokeCounts: invokeCounts, transportCounts: transportCounts,
            archiveSHA256: installedArchiveHash)
    }
    private final class PreparedFiles {
        var files: [UInt32: FileHandle]? = [:]
        deinit { for file in files?.values ?? Dictionary<UInt32, FileHandle>().values { try? file.close() } }
    }
    func prepareRestore(_ value: SavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws -> Void {
        try snapshotBoundary(); try heap.validateRestore(plan)
        guard value.stack == stack, value.tailThunks == tailThunks, value.tailOnly == tailOnly, value.frameExtents == frameExtents,
              value.hasGameEntry == (gameEntry != nil), value.hasGameService == (gameService != nil),
              value.hasDependency == (dependency != nil), value.hasExternalRelease == (releaseExternalAllocation != nil),
              Set(value.allocations.map { $0.reference.token }).count == value.allocations.count,
              Set(value.scratch.map { $0.reference.token }).count == value.scratch.count,
              Set(value.files.map(\.token)).count == value.files.count,
              value.files.allSatisfy({ !value.retiredFiles.contains($0.token) })
        else { throw ClawSnapshotError.incompleteOwners }
        var restored: [UInt32: ClawTokenHeap.AllocationIdentity] = [:], sizes: [UInt32: UInt32] = [:]
        var restoredScratch: [UInt32: (count: UInt32, identity: ClawTokenHeap.AllocationIdentity)] = [:]
        for witness in value.allocations {
            guard !witness.reference.interior else { throw ClawSnapshotError.invalidState }
            restored[witness.reference.token] = try witness.resolve(in: plan); sizes[witness.reference.token] = witness.reference.count
        }
        for witness in value.scratch {
            guard !witness.reference.interior, restored[witness.reference.token] == nil else { throw ClawSnapshotError.invalidState }
            restoredScratch[witness.reference.token] = (witness.reference.count, try witness.resolve(in: plan))
        }
        guard value.archive == 0 || sizes[value.archive] == 72,
              value.files.allSatisfy({ sizes[$0.token] == 32 && $0.offset <= Int64.max }) else { throw ClawSnapshotError.invalidState }
        let prepared = PreparedFiles()
        if !value.files.isEmpty || value.archive != 0 {
            // Reopen only the installed supported archive, never an archived path or
            // OS file descriptor. The token-to-file map and cursors are state.
            let file = try FileHandle(forReadingFrom: archiveURL); defer { try? file.close() }
            var digest = SHA256()
            while let bytes = try file.read(upToCount: 1 << 20), !bytes.isEmpty { digest.update(data: bytes) }
            let actual = digest.finalize().map({ String(format: "%02x", $0) }).joined()
            // Legacy snapshots used only the disc. File cursors and resource
            // offsets cannot be restored against the other supported archive.
            let expected = value.archiveSHA256 ?? "b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596"
            guard Self.supportedArchiveHashes.contains(actual), actual == expected
            else { throw ClawSnapshotError.invalidState }
        }
        for record in value.files {
            let file = try FileHandle(forReadingFrom: archiveURL)
            prepared.files![record.token] = file
            try file.seek(toOffset: record.offset)
        }
        return { [self] in
            try snapshotBoundary(); try heap.validateInstalledRestore(plan)
            guard let opened = prepared.files else { throw ClawSnapshotError.invalidState }
            for file in files.values { try? file.close() }
            files = opened; prepared.files = nil
            allocations = Set(restored.keys); allocationIdentities = restored; allocationSizes = sizes
            scratch = value.scratch.map { $0.reference.token }; scratchIdentities = restoredScratch
            archive = value.archive; retiredFiles = value.retiredFiles; threadHead = value.threadHead
            mathServiceCounts = value.mathCounts; invokeCounts = value.invokeCounts; transportCounts = value.transportCounts
            allocationOrigins.removeAll(); events.removeAll(); failureTrace.removeAll()
        }
    }

    init(heap:ClawTokenHeap,archiveURL:URL,metadata:[UInt32:Data],stack:UInt32 = 0x02008000) throws {
        self.heap = heap; self.archiveURL = archiveURL; self.stack = stack
        host.initialize(to:ClawHost())
        host.pointee.user = Unmanaged.passUnretained(self).toOpaque()
        host.pointee.maximumOperations = 200000000
        host.pointee.bytes = {u,t,n in
            guard let u else {return nil}
            return Unmanaged<ClawNativeMenuResources>.fromOpaque(u).takeUnretainedValue().heap.lookupBytes(t,count:n)
        }
        host.pointee.call = {u,q in
            guard let u,let q else {return 0}
            return Unmanaged<ClawNativeMenuResources>.fromOpaque(u).takeUnretainedValue().service(q.pointee,request:q)
        }
        if heap.lookupBytes(0x01ff0000,count:0x20000) == nil {
            guard !heap.overlaps(0x01ff0000,count:0x20000) else {throw Failure.invalid("Resource stack already owned")}
            heap.storeBytes(token:0x01ff0000,count:0x20000);scratch.append(0x01ff0000)
            scratchIdentities[0x01ff0000] = (0x20000, heap.allocationIdentity(at: 0x01ff0000, count: 0x20000)!)
        }
        try installMetadata(metadata)
    }
    /// Maps original image spans. With `onlyUnmapped`, bytes the heap already
    /// owns keep their live values (a later election fills only the gaps).
    func installMetadata(_ metadata:[UInt32:Data],onlyUnmapped:Bool = false) throws {
        for (token,data) in metadata.sorted(by:{$0.key<$1.key}) {
            guard !data.isEmpty,UInt64(token)+UInt64(data.count) <= UInt32.max else {
                throw Failure.invalid("Invalid resource metadata span")
            }
            var offset = 0
            while offset < data.count {
                let at = token+UInt32(offset)
                let existing = heap.lookupBytes(at,count:1) ?? heap.lookup(at & ~3,words:1).map {
                    UnsafeRawPointer($0).assumingMemoryBound(to:UInt8.self).advanced(by:Int(at & 3))
                }.map {UnsafeMutablePointer(mutating:$0)}
                if let existing {
                    guard onlyUnmapped || existing.pointee == data[offset] else {
                        throw Failure.invalid("Resource metadata mismatch at \(String(token+UInt32(offset),radix:16))")
                    }
                    offset += 1
                } else {
                    let start = offset
                    while offset < data.count && !heap.overlaps(token+UInt32(offset),count:1) {offset += 1}
                    guard offset > start else {throw Failure.invalid("Partial resource metadata overlap")}
                    let at = token+UInt32(start),chunk = data.subdata(in:start..<offset)
                    chunk.copyBytes(to:heap.storeBytes(token:at,count:UInt32(chunk.count)),count:chunk.count)
                    scratch.append(at)
                    scratchIdentities[at] = (UInt32(chunk.count), heap.allocationIdentity(at: at, count: UInt32(chunk.count))!)
                }
            }
        }
    }
    deinit {
        close()
        host.deinitialize(count:1);host.deallocate()
    }
    @discardableResult func fail(_ address:UInt32)->UInt32 {
        if failureTrace.isEmpty {
            failureTrace = recent.lines()
            if let path = ProcessInfo.processInfo.environment["CLAW_REAL_SPEED_LOG"] {
                let evidence:[String:Any] = ["address":String(host.pointee.faultAddress == 0 ? address:host.pointee.faultAddress,radix:16),"trace":failureTrace,"missing_tile_frames":missingTileFrames(world:drawingWorld)]
                try? JSONSerialization.data(withJSONObject:evidence,options:[.sortedKeys]).write(to:URL(fileURLWithPath:path).appendingPathComponent("native-fault.json"),options:.atomic)
            }
        }
        if host.pointee.faultAddress == 0 { host.pointee.faultAddress = address }
        if host.pointee.fault == 0 {
            host.pointee.fault = UInt32(CLAW_FAULT_HOST);host.pointee.faultAddress = address
        }
        return 0
    }
    // Capture WWD identity before gameplay repurposes actor+4 (loot does so).
    // Witnesses distinguish deletion from token reuse. Containing witnesses
    // accept the complete actor span when its owner retains a larger block.
    private struct PlacementActor {
        let token: UInt32, plane: UInt32
        let identity: ClawTokenHeap.AllocationIdentity
    }
    private var placementActors: [ClawCheckpointPlacement: PlacementActor] = [:]
    private var placementChildren: [ClawCheckpointPlacement: [PlacementActor]] = [:]
    private var placementOwners: [UInt32: (key: ClawCheckpointPlacement, actor: PlacementActor)] = [:]
    private var loadingPlacement: (key: ClawCheckpointPlacement, plane: UInt32)?
    private var checkpointPickupAwards: [[String:Any]] = []
    private var checkpointFactories: [[String:Any]] = []
    private var placementLogics: [ClawCheckpointPlacement: String] = [:]
    var checkpointLogicEntries: (() -> [String:UInt32])?
    var checkpointSequenceName: ((UInt32) -> String?)?
    private func checkpointAnimation(_ actor: UInt32) -> ClawCheckpointAnimation? {
        let animator = actor+0x188
        guard let sequence = word(animator+8),sequence != 0,
              let name = checkpointSequenceName?(sequence) else {return nil}
        return ClawCheckpointAnimation(name:name,index:word(animator+0x10) ?? 0,
            scalars:ClawCheckpointAnimation.offsets.map {word(animator+$0) ?? 0})
    }
    private func restoreCheckpointAnimation(_ saved: ClawCheckpointAnimation, actor: UInt32) throws {
        guard saved.valid else {throw ClawCustomCheckpoint.Failure.loadFailed}
        let name = textToken(saved.name);defer {release(name)}
        _ = invoke(0x4c79e0,actor,[name,0])
        _ = invoke(0x420970,actor+0x188,[saved.index])
        guard fault == 0,word(actor+0x198) == saved.index else {throw ClawCustomCheckpoint.Failure.loadFailed}
        for (offset,scalar) in zip(ClawCheckpointAnimation.offsets,saved.scalars) {
            guard putWord(actor+0x188+offset,scalar) else {throw ClawCustomCheckpoint.Failure.loadFailed}
        }
    }
    private struct RuntimeLoot {
        let actor: PlacementActor
        let owner: ClawCheckpointPlacement?
        let logic: String
        let identifier: UInt32, z: UInt32, flags: UInt32
    }
    private var runtimeLoot: [UInt32:RuntimeLoot] = [:]
    private func checkpointBounce(_ actor: UInt32) -> ClawCheckpointBounce? {
        guard word((word(actor+0x6c) ?? 0)+0x10) == 0x40e690,
              let body = word((word(actor+0x6c) ?? 0)+0x18),body != 0,
              let item = word(body+0x184) else {return nil}
        func number(_ offset: UInt32) -> Double {
            guard let p = heap.lookupBytes(body+offset,count:8) else {return .nan}
            return UnsafeRawPointer(p).loadUnaligned(as:Double.self)
        }
        let phase = [word((word(actor+0x6c) ?? 0)+0x1c) ?? 0] + ClawCheckpointBounce.phaseOffsets.map {word(body+$0) ?? 0}
        return ClawCheckpointBounce(item:item,gravity:number(0x40),velocityX:number(0x50),velocityY:number(0x58),
            physics:ClawCheckpointBounce.physicsOffsets.map(number),stopped:word(body+0xc8),phase:phase,
            dynamics:ClawCheckpointBounce.dynamicsOffsets.map {word(actor+$0) ?? 0},animation:checkpointAnimation(actor))
    }
    var checkpointLoot: [ClawCheckpointLoot] {
        runtimeLoot.values.compactMap { value in
            guard heap.containingAllocationIdentity(at:value.actor.token,count:0x1b4) === value.actor.identity,
                  (word(value.actor.token+8) ?? 0) & 0x10000 == 0 else {return nil}
            return ClawCheckpointLoot(owner:value.owner,logic:value.logic,identifier:value.identifier,z:value.z,flags:value.flags,
                actor:ClawCheckpointLoot.actorOffsets.map {word(value.actor.token+$0) ?? 0},bounce:checkpointBounce(value.actor.token))
        }.sorted {
            let a = ($0.owner?.plane ?? 0,$0.owner?.id ?? 0,$0.identifier)
            let b = ($1.owner?.plane ?? 0,$1.owner?.id ?? 0,$1.identifier)
            return a == b ? $0.actor[1] > $1.actor[1] : a < b
        }
    }
    func restoreCheckpointLoot(_ values: [ClawCheckpointLoot], state: UInt32) throws {
        let entries = checkpointLogicEntries?() ?? [:]
        let scene = word(state+0xc) ?? 0,map = word(scene+0x24) ?? 0,array = word(map+0x38) ?? 0
        for saved in values {
            guard saved.valid,entries[saved.logic] != nil else {throw ClawCustomCheckpoint.Failure.loadFailed}
            let plane = saved.owner.flatMap {word(array+$0.plane*4)} ?? word(map+0x5c) ?? 0
            guard plane != 0 else {throw ClawCustomCheckpoint.Failure.loadFailed}
            let previous = loadingPlacement
            loadingPlacement = saved.owner.map {($0,plane)}
            // Settled drops are ordinary pickups. Do not run a new bouncing
            // controller: it can land/rebind during its first tick and create
            // a companion before the explicit rebind, leaving that one orphaned.
            let logic = saved.logic == "BouncingGoodie" && saved.bounce == nil ? "TreasurePowerup" : saved.logic
            let name = textToken(logic)
            let actor = invoke(0x4c8da0,word(scene+8) ?? 0,[saved.identifier,saved.actor[1],saved.actor[2],saved.z,name,saved.flags])
            release(name)
            loadingPlacement = previous
            guard actor != 0,fault == 0 else {throw ClawCustomCheckpoint.Failure.loadFailed}
            // The runtime factory never selects the item's image. A settled
            // BouncingGoodie has already retired its bounce controller; its
            // item now lives at actor+4. Both phases need the original image
            // before initialization builds collision bounds and award data.
            let item = saved.bounce?.item ?? saved.actor[0]
            let image = invoke(0x473630,0,[item])
            _ = invoke(0x4c7970,actor,[image])
            // Only an airborne drop needs the bounce constructor. Settled
            // pickups initialize exactly once through the item rebind below.
            if saved.bounce != nil {
                _ = invoke(word((word(actor+0x6c) ?? 0)+0x10) ?? 0,0,[actor])
                guard fault == 0 else {throw ClawCustomCheckpoint.Failure.loadFailed}
            }
            // The loot owner binds the saved item kind to fresh images,
            // collision callbacks and award data. Constructor IDs alone do
            // not select a treasure kind.
            if let bounce = saved.bounce {
                let body = word((word(actor+0x6c) ?? 0)+0x18) ?? 0
                guard body != 0,putWord(body+0x184,bounce.item) else {throw ClawCustomCheckpoint.Failure.loadFailed}
                for (offset,number): (UInt32,Double) in [(0x40,bounce.gravity),(0x50,bounce.velocityX),(0x58,bounce.velocityY)] {
                    guard let p = heap.lookupBytes(body+offset,count:8) else {throw ClawCustomCheckpoint.Failure.loadFailed}
                    p.withMemoryRebound(to:Double.self,capacity:1) {$0.pointee = number}
                }
                if let physics = bounce.physics {
                    for (offset,number) in zip(ClawCheckpointBounce.physicsOffsets,physics) {
                        guard let p = heap.lookupBytes(body+offset,count:8) else {throw ClawCustomCheckpoint.Failure.loadFailed}
                        p.withMemoryRebound(to:Double.self,capacity:1) {$0.pointee = number}
                    }
                }
                if let stopped = bounce.stopped {_ = putWord(body+0xc8,stopped)}
                if let phase = bounce.phase {
                    _ = putWord((word(actor+0x6c) ?? 0)+0x1c,phase[0])
                    for (offset,scalar) in zip(ClawCheckpointBounce.phaseOffsets,phase.dropFirst()) {_ = putWord(body+offset,scalar)}
                    if phase[1] != 0 {_ = invoke(0x4736b0,0,[actor])}
                }
                if let dynamics = bounce.dynamics {
                    for (offset,scalar) in zip(ClawCheckpointBounce.dynamicsOffsets,dynamics) {_ = putWord(actor+offset,scalar)}
                }
                if let animation = bounce.animation {try restoreCheckpointAnimation(animation,actor:actor)}
            } else {
                // A settled drop has already passed the bounce enable edge.
                // Reapply it to clear the constructor's non-collidable bit and
                // rebuild kind data/bounds before rebinding its pickup logic.
                _ = invoke(0x4736b0,0,[actor])
                _ = invoke(0x473660,0,[actor,saved.actor[0]])
            }
            guard fault == 0 else {throw ClawCustomCheckpoint.Failure.loadFailed}
            for (offset,value) in zip(ClawCheckpointLoot.actorOffsets,saved.actor) {
                guard putWord(actor+offset,value) else {throw ClawCustomCheckpoint.Failure.loadFailed}
            }
        }
    }
    func spawnCheckpointLootFixture(state: UInt32, item: UInt32 = 33) throws {
        guard ProcessInfo.processInfo.arguments.contains("--custom-checkpoint-check"),
              checkpointLogicEntries?()["BouncingGoodie"] != nil,
              let owner = placementActors.sorted(by:{$0.key.id < $1.key.id}).first else {throw ClawCustomCheckpoint.Failure.unavailable}
        let player = word(0x537e88) ?? 0,x = word(player+0x4c) ?? 0
        let inventory = allocate(0x70)
        guard inventory != 0,let words = heap.lookup(inventory,words:28) else {throw ClawCustomCheckpoint.Failure.loadFailed}
        words.update(repeating:0,count:28)
        let previous = loadingPlacement;loadingPlacement = (owner.key,owner.value.plane)
        defer {loadingPlacement = previous;_ = putWord(player+0x4c,x);release(inventory)}
        // Labelled inventory fixture, through the exact enemy-drop owner.
        // The temporary live source coordinate only positions the drop; no
        // score, collection flag or actor-private bytes are manufactured.
        _ = putWord(inventory+8,player);_ = putWord(inventory+0x6c,player)
        _ = putWord(inventory+0x24,1);_ = putWord(inventory+0x28,1);_ = putWord(inventory+0x2c,item)
        _ = putWord(player+0x4c,x+120)
        _ = invoke(0x42df90,inventory)
        guard fault == 0 else {throw ClawCustomCheckpoint.Failure.loadFailed}
    }
    var checkpointPickupEvidence: [String:Any] {
        let player = word(0x537e88) ?? 0, scene = word(player+0xc) ?? 0
        let x = Int64(word(player+0x4c) ?? 0), y = Int64(word(player+0x50) ?? 0)
        let nearby: [[String:Any]] = heap.debugAllocationBases.compactMap { actor in
            guard heap.containingAllocationIdentity(at:actor,count:0x1b4) != nil,
                  [UInt32(0x513770),0x5137f0].contains(word(actor) ?? 0),word(actor+0xc) == scene,
                  abs(Int64(word(actor+0x4c) ?? 0)-x) < 200,
                  abs(Int64(word(actor+0x50) ?? 0)-y) < 200 else {return nil}
            let logic = word(actor+0x6c) ?? 0
            return ["actor":actor,"item":word(actor+4) ?? 0,"flags":word(actor+8) ?? 0,
                "callback":word(logic+0x10) ?? 0,"state":word(logic+0x1c) ?? 0,
                "contact":word(actor+0x164) ?? 0,"x":word(actor+0x4c) ?? 0,"y":word(actor+0x50) ?? 0,
                "collision_kind":word(actor+0xd0) ?? 0,"image":word(actor+0x170) ?? 0,
                "bounds":(0..<4).map {word(actor+0x138+UInt32($0*4)) ?? 0},
                "placement":placementOwners[actor]?.key.id as Any? ?? NSNull()]
        }
        return ["awards":checkpointPickupAwards,"nearby":nearby,"factories":checkpointFactories,
            "remaining":checkpointLoot.map {["owner":$0.owner?.id as Any? ?? NSNull(),"logic":$0.logic,"id":$0.identifier,"x":$0.actor[1],"y":$0.actor[2],"item":$0.bounce?.item ?? $0.actor[0],"bouncing":$0.bounce != nil] as [String:Any]}]
    }
    // Some initializer services compose the loader internally. Complete the
    // placement census from the scene's live actors before its first frame.
    // Primary+4 retains the WWD id when pickup initialization repurposes actor+4.
    func capturePlacements(world: ClawWorld, state: UInt32) {
        let scene = word(state+0xc) ?? 0, map = word(scene+0x24) ?? 0
        let array = word(map+0x38) ?? 0
        var records: [UInt32: [(key:ClawCheckpointPlacement,x:UInt32,y:UInt32)]] = [:]
        placementLogics.removeAll()
        for (plane, value) in world.planes.enumerated() {
            let counts = Dictionary(grouping:value.objects,by:{$0.id}).mapValues(\.count)
            for object in value.objects {
                let id = UInt32(bitPattern:Int32(object.id))
                // Retail maps contain duplicate object IDs. Their authored
                // record offsets distinguish them without persisting pointers.
                let key = ClawCheckpointPlacement(plane:UInt32(plane),id:counts[object.id] == 1 ? id : 0x80000000 | UInt32(object.encodedRecordOffset))
                placementLogics[key] = object.logic
                records[id,default:[]].append((key,UInt32(bitPattern:Int32(object.x)),UInt32(bitPattern:Int32(object.y))))
            }
        }
        placementActors.removeAll();placementChildren.removeAll();placementOwners.removeAll()
        for actor in heap.debugAllocationBases {
            guard let identity = heap.containingAllocationIdentity(at: actor, count: 0x1b4),
                  word(actor) == 0x5137f0, word(actor+0xc) == scene, (word(actor+8) ?? 0) & 0x40000 != 0,
                  let logic = word(actor+0x6c), logic != 0, let id = word(logic+4),
                  let choices = records[id],
                  let match = choices.count == 1 ? choices.first : choices.first(where:{placementActors[$0.key] == nil && $0.x == word(actor+0x4c) && $0.y == word(actor+0x50)}),
                  let plane = word(array+match.key.plane*4), plane != 0 else { continue }
            let key = match.key
            if placementActors[key] == nil { placementActors[key] = .init(token: actor, plane: plane, identity: identity) }
            placementOwners[actor] = (key,.init(token:actor,plane:plane,identity:identity))
        }
    }
    var removedPlacements: [ClawCheckpointPlacement] {
        placementActors.compactMap { key, value in
            let live = heap.containingAllocationIdentity(at: value.token, count: 0x1b4) === value.identity
            let flags = word(value.token+8) ?? 0
            // Broken statues retain their decorative actor with bit 4 set.
            // Its inventory is spent even though the actor was not deleted.
            let spentStatue = placementLogics[key] == "BehindStatue" && flags & 4 != 0
            return !live || flags & 0x10000 != 0 || spentStatue ? key : nil
        }.sorted { $0.plane == $1.plane ? $0.id < $1.id : $0.plane < $1.plane }
    }
    var checkpointMechanisms: [ClawCheckpointMechanism] {
        placementActors.compactMap { key, value in
            guard let name = placementLogics[key],ClawCheckpointMechanism.supported.contains(name),
                  heap.containingAllocationIdentity(at:value.token,count:0x1b4) === value.identity,
                  (word(value.token+8) ?? 0) & 0x10000 == 0,
                  let logic = word(value.token+0x6c),(word(logic+0x1c) ?? 0) != 0 else {return nil}
            let motion: [UInt32]? = ClawCheckpointMechanism.movingLogics.contains(name)
                ? ClawCheckpointMechanism.motionActorOffsets.map {word(value.token+$0) ?? 0} + ClawCheckpointMechanism.motionPrimaryOffsets.map {word(logic+$0) ?? 0} : nil
            let helper = word(logic+0x18) ?? 0
            // Pending callback addresses are never recipes. The ordinary
            // switch profile has no pending callbacks after construction.
            if name == "JumpSwitch",word(helper+0x14) != 0 || word(helper+0x18) != 0 {return nil}
            let path: [UInt32]? = name == "PathElevator" ? [0xc,0x10,0x14].map {word(helper+$0) ?? 0} : nil
            let switchPhase: [UInt32]? = name == "JumpSwitch" ? [0x1c,0x20].map {word(helper+$0) ?? 0} : nil
            let stone: [UInt32]? = name == "StartSteppingStone" ? [word(logic+0x64) ?? 0,word(logic+0x68) ?? 0,word(value.token+0xd0) ?? 0] : nil
            return ClawCheckpointMechanism(placement:key,logic:name,
                actor:ClawCheckpointMechanism.actorOffsets.map {word(value.token+$0) ?? 0},
                primary:ClawCheckpointMechanism.primaryOffsets.map {word(logic+$0) ?? 0},
                motion:motion,path:path,switchPhase:switchPhase,stone:stone,
                superFlags:ClawCheckpointMechanism.superLogics.contains(name) ? (word(value.token+8) ?? 0) & 5 : nil,
                animation:checkpointAnimation(value.token))
        }.sorted {$0.placement.plane == $1.placement.plane ? $0.placement.id < $1.placement.id : $0.placement.plane < $1.placement.plane}
    }
    var checkpointProgressLimits: [String] {
        var limits: [String] = []
        if placementLogics.values.contains("BossStager"),checkpointBossStage == nil {limits.append("In-progress boss staging restarts")}
        let switches = placementActors.filter {placementLogics[$0.key] == "JumpSwitch"}
        if switches.contains(where: {_,value in
            guard heap.containingAllocationIdentity(at:value.token,count:0x1b4) === value.identity else {return false}
            let helper = word((word(value.token+0x6c) ?? 0)+0x18) ?? 0
            return helper != 0 && (word(helper+0x14) != 0 || word(helper+0x18) != 0)
        }) {limits.append("Pending switch callbacks restart")}
        return limits
    }
    var checkpointBossStage: ClawCheckpointBossStage? {
        guard word(0x53c9c0) == 2 else {return nil}
        let boss = word(0x5349dc) ?? 0
        let target = placementActors.first {_,value in
            value.token == boss && heap.containingAllocationIdentity(at:boss,count:0x1b4) === value.identity
        }?.key
        guard boss == 0 || target != nil else {return nil}
        let meter = heap.debugAllocationBases.contains {actor in
            guard heap.containingAllocationIdentity(at:actor,count:0x1b4) != nil,
                  [UInt32(0x513770),0x5137f0].contains(word(actor) ?? 0),
                  let logic = word(actor+0x6c),logic <= UInt32.max-0x10 else {return false}
            return word(logic+0x10) == 0x491fa0 && (word(actor+8) ?? 0) & 0x10000 == 0
        }
        return ClawCheckpointBossStage(phase:2,boss:target,healthMeter:meter && target != nil)
    }
    func restoreCheckpointBossStage(_ saved: ClawCheckpointBossStage, state: UInt32) throws {
        guard saved.valid else {throw ClawCustomCheckpoint.Failure.loadFailed}
        if let target = saved.boss {
            guard let value = placementActors[target],
                  heap.containingAllocationIdentity(at:value.token,count:0x1b4) === value.identity,
                  let logic = word(value.token+0x6c) else {throw ClawCustomCheckpoint.Failure.loadFailed}
            if word(logic+0x1c) == 0 {_ = invoke(word(logic+0x10) ?? 0,0,[value.token])}
            guard fault == 0,putWord(0x5349dc,value.token) else {throw ClawCustomCheckpoint.Failure.loadFailed}
        } else {
            guard putWord(0x5349dc,0) else {throw ClawCustomCheckpoint.Failure.loadFailed}
        }
        guard putWord(0x53c9c0,saved.phase),putWord(0x52be14,.max),putWord(0x52be18,.max) else {throw ClawCustomCheckpoint.Failure.loadFailed}
        if saved.healthMeter {
            let name = textToken("BossHealthMeter");defer {release(name)}
            let scene = word(state+0xc) ?? 0
            let meter = invoke(0x4c8da0,word(scene+8) ?? 0,[0,0,0,0,name,0x200000])
            guard meter != 0,fault == 0 else {throw ClawCustomCheckpoint.Failure.loadFailed}
            _ = invoke(0x491fa0,0,[meter])
            guard fault == 0 else {throw ClawCustomCheckpoint.Failure.loadFailed}
        }
    }
    func restoreCheckpointMechanisms(_ values: [ClawCheckpointMechanism]) throws {
        for saved in values {
            guard saved.valid,let value = placementActors[saved.placement],
                  placementLogics[saved.placement] == saved.logic,
                  heap.containingAllocationIdentity(at:value.token,count:0x1b4) === value.identity,
                  let logic = word(value.token+0x6c) else {throw ClawCustomCheckpoint.Failure.loadFailed}
            // The original initializer owns private data and resource binding.
            // It must run on this map's fresh actor before scalar progress.
            if (word(logic+0x1c) ?? 0) == 0,saved.primary[0] != 0 {
                _ = invoke(word(logic+0x10) ?? 0,0,[value.token])
            }
            guard fault == 0 else {throw ClawCustomCheckpoint.Failure.loadFailed}
            let scene = word(value.token+0xc) ?? 0
            _ = invoke(0x4cbb60,word(scene+0x24) ?? 0,[value.token,saved.actor[0],saved.actor[1],8])
            guard fault == 0 else {throw ClawCustomCheckpoint.Failure.loadFailed}
            for (offset,scalar) in zip(ClawCheckpointMechanism.actorOffsets,saved.actor) where offset != 0x16c {
                guard putWord(value.token+offset,scalar) else {throw ClawCustomCheckpoint.Failure.loadFailed}
            }
            for (offset,scalar) in zip(ClawCheckpointMechanism.primaryOffsets,saved.primary) {
                guard putWord(logic+offset,scalar) else {throw ClawCustomCheckpoint.Failure.loadFailed}
            }
            if let motion = saved.motion {
                let count = ClawCheckpointMechanism.motionActorOffsets.count
                for (offset,scalar) in zip(ClawCheckpointMechanism.motionActorOffsets,motion.prefix(count)) {
                    guard putWord(value.token+offset,scalar) else {throw ClawCustomCheckpoint.Failure.loadFailed}
                }
                for (offset,scalar) in zip(ClawCheckpointMechanism.motionPrimaryOffsets,motion.dropFirst(count)) {
                    guard putWord(logic+offset,scalar) else {throw ClawCustomCheckpoint.Failure.loadFailed}
                }
            }
            let helper = word(logic+0x18) ?? 0
            if let path = saved.path {
                guard helper != 0,word(helper+4) == value.token,(word(helper+8) ?? 0) != 0 else {throw ClawCustomCheckpoint.Failure.loadFailed}
                for (offset,scalar) in zip([UInt32(0xc),0x10,0x14],path) {
                    guard putWord(helper+offset,scalar) else {throw ClawCustomCheckpoint.Failure.loadFailed}
                }
            }
            if let phase = saved.switchPhase {
                guard helper != 0,word(helper+8) == value.token,word(helper+0x10) == logic else {throw ClawCustomCheckpoint.Failure.loadFailed}
                for (offset,scalar) in zip([UInt32(0x1c),0x20],phase) {_ = putWord(helper+offset,scalar)}
            }
            if let stone = saved.stone {
                _ = putWord(logic+0x64,stone[0]);_ = putWord(logic+0x68,stone[1]);_ = putWord(value.token+0xd0,stone[2])
            }
            if let flags = saved.superFlags {
                // Preserve the original contact latch and draw bit. Resource
                // ownership and every other flag belong to the fresh actor.
                _ = putWord(value.token+8,((word(value.token+8) ?? 0) & ~UInt32(5)) | flags)
            }
            if let animation = saved.animation {try restoreCheckpointAnimation(animation,actor:value.token)}
            // Rebind the frame through the new image group's owner.
            let group = word(value.token+0x170) ?? 0,frame = saved.actor.last!
            if group != 0 {
                let image = invoke(0x40f680,group,[frame])
                guard fault == 0,putWord(value.token+0x16c,frame),putWord(value.token+0x174,image) else {throw ClawCustomCheckpoint.Failure.loadFailed}
            }
        }
    }
    // Read-only evidence for the focused real-input world-state check.
    var checkpointRecipeEvidence: [[String:Any]] {
        guard let data = try? JSONEncoder().encode(checkpointMechanisms),
              let rows = try? JSONSerialization.jsonObject(with:data) as? [[String:Any]] else {return []}
        return rows
    }
    var checkpointPlacementEvidence: [[String: Any]] {
        placementActors.map { key, value in
            let live = heap.containingAllocationIdentity(at: value.token, count: 0x1b4) === value.identity
            return ["plane":key.plane,"id":key.id,"actor":value.token,"live":live,
                "logic":placementLogics[key] ?? "",
                "state":live ? word((word(value.token+0x6c) ?? 0)+0x1c) ?? 0 : 0,
                "x":live ? word(value.token+0x4c) ?? 0 : 0,"y":live ? word(value.token+0x50) ?? 0 : 0,
                "health":live ? word(value.token+0x10c) ?? 0 : 0,
                "flags":live ? word(value.token+8) ?? 0 : 0,
                "children_live":(placementChildren[key] ?? []).filter {heap.containingAllocationIdentity(at:$0.token,count:0x1b4) === $0.identity}.count,
                "callback":live ? word((word(value.token+0x6c) ?? 0)+0x10) ?? 0 : 0] as [String: Any]
        }.sorted { ($0["id"] as! UInt32) < ($1["id"] as! UInt32) }
    }
    // Both active and dormant actors are unlinked by their existing owners.
    func removePlacements(_ placements: [ClawCheckpointPlacement]) {
        for key in Set(placements).sorted(by: { $0.plane == $1.plane ? $0.id < $1.id : $0.plane < $1.plane }) {
            // A placed pickup may replace itself with a live child before
            // load finishes. Retire its descendants as well as the WWD actor.
            let values = (placementChildren[key] ?? []) + (placementActors[key].map{[$0]} ?? [])
            for value in values.reversed() {
            guard heap.containingAllocationIdentity(at:value.token,count:0x1b4) === value.identity else {continue}
            let actor = value.token, flags = word(actor+8) ?? 0
            let position = word(actor+0x68) ?? 0
            if flags & 0x80000 != 0, let logic = word(actor+0x6c), logic != 0 {
                _ = putWord(logic+0x1c, 29)
                _ = invoke(word(logic+0x10) ?? 0, 0, [actor])
            }
            // A dormant actor can retain an old active-list position. The
            // embedded grid member is the current membership witness.
            if word(actor+0x94) != 0 {
                let manager = word(value.plane+0xb0) ?? 0
                let offset: UInt32 = flags & 0x800000 != 0 ? 8 : flags & 0x1000000 != 0 ? 12 : 4
                _ = invoke(0x4f4680, word(manager+offset) ?? 0, [actor+0x88])
            } else if position != 0 {
                let container = word((word(actor+0xc) ?? 0)+8) ?? 0
                var call = ClawCall();call.function = 0x4f5212;call.receiver = container+0x10
                call.argumentCount = 1;call.arguments.0 = position
                _ = service(call)
            }
            _ = invoke(word((word(actor) ?? 0)+4) ?? 0, actor, [1])
            if fault != 0 { return }
            }
        }
    }
    // Optional allocation observer for the muted object-load census.
    var observeAllocation: ((UInt32, UInt32) -> Void)?
    func allocate(_ n:UInt32)->UInt32 {
        let token = worldBufferSizes.contains(n) ? heap.allocateWorldBuffer(bytes:max(n,1)):heap.allocate(bytes:max(n,1))
        if token != 0 {
            allocations.insert(token);allocationSizes[token] = max(n,1)
            allocationIdentities[token] = heap.allocationIdentity(at: token, count: max(n,1))!
            observeAllocation?(token, n)
            if traceAllocations {allocationOrigins[token] = recent.lines(last:4)}
        }
        return token
    }
    func allocationData(_ token:UInt32)->Data? {
        guard let count = allocationSizes[token],owns(token),let bytes = heap.lookupBytes(token,count:count) else {return nil}
        return Data(bytes:bytes,count:Int(count))
    }
    func release(_ token:UInt32) {
        guard token != 0 else { return }
        guard owns(token) else {
            // A retired local lease must not fall through to another owner.
            if allocations.contains(token) { invalidReleaseToken = token; _ = fail(0x4f6428); return }
            if releaseExternalAllocation?(token) == true {return}
            invalidReleaseToken = token;_ = fail(0x4f6428);return
        }
        allocations.remove(token); allocationIdentities.removeValue(forKey: token)
        heap.free(token)
        allocationSizes.removeValue(forKey:token)
        allocationOrigins.removeValue(forKey:token)
    }
    func transferAllocation(_ token:UInt32,to display:ClawNativeDisplay)->Bool {
        guard let count = allocationSizes[token],owns(token),display.adoptMenuAllocation(token,bytes:count) else {return false}
        allocations.remove(token);allocationSizes.removeValue(forKey:token);allocationOrigins.removeValue(forKey:token)
        allocationIdentities.removeValue(forKey: token)
        return true
    }
    func owns(_ token:UInt32)->Bool {
        guard allocations.contains(token), let count = allocationSizes[token], let identity = allocationIdentities[token] else { return false }
        return heap.allocationIdentity(at: token, count: count) === identity
    }
    // Ends ledger ownership without freeing: the native owner that adopted
    // the block keeps its storage when the game never deleted it.
    func relinquish(_ token:UInt32)->Bool {
        guard !closed,allocations.remove(token) != nil else {return false}
        allocationSizes.removeValue(forKey:token);allocationOrigins.removeValue(forKey:token)
        allocationIdentities.removeValue(forKey: token)
        return true
    }
    func releaseIfOwned(_ token:UInt32)->Bool {
        // A remembered lease handles the request even when release rejects its
        // retired witness; callers must not grant another owner that token.
        guard allocations.contains(token) else {return false}
        release(token);return true
    }
    func adoptConstructorAllocations(_ blocks:[(token:UInt32,bytes:UInt32)]) throws {
        guard !closed,fault == 0,Set(blocks.map{$0.token}).count == blocks.count,
              blocks.allSatisfy({!allocations.contains($0.token) && heap.allocationIdentity(at:$0.token,count:$0.bytes) != nil}) else {
            throw Failure.invalid("Menu constructor allocation ownership")
        }
        allocations.formUnion(blocks.map{$0.token})
        for block in blocks {
            allocationSizes[block.token] = block.bytes
            allocationIdentities[block.token] = heap.allocationIdentity(at: block.token, count: block.bytes)!
        }
    }
    func text(_ token:UInt32,maximumBytes:UInt32 = 4096)->String? {
        var data = Data()
        for i:UInt32 in 0..<maximumBytes {
            guard let p = heap.lookupBytes(token+i,count:1) else {return nil}
            if p.pointee == 0 {return String(data:data,encoding:.ascii)}
            data.append(p.pointee)
        }
        return nil
    }
    func textToken(_ text:String)->UInt32 {
        let data = Data(text.utf8)+Data([0]),token = allocate(UInt32(data.count))
        if let p = heap.lookupBytes(token,count:UInt32(data.count)) {data.copyBytes(to:p,count:data.count)}
        return token
    }
    /// App-only responsiveness instrumentation; never changes recovered execution.
    var observeBlockingInvocation:((UInt32,Bool)->Void)?
    var completedInvocation:((UInt32,UInt32)->Void)?
    // Native checkpoint state is applied after the original level load succeeds.
    var levelLoaded:((UInt32)->Void)?
    var observeInvocation:((UInt32,UInt32,[UInt32])->Void)?
    // Level 1 join election (App/GameData/MENU/level-one-transports.json):
    // vtable tail thunks and their slots, tail-only owners, and original
    // prologue extents of callers whose child frame needs more than 0x400.
    var tailThunks:[UInt32:UInt32] = [:]
    var tailOnly:Set<UInt32> = []
    private var originalDirectCalls:[UInt32:Set<UInt32>] = [:]
    var frameExtents:[UInt32:UInt32] = [:]
    private var functions:[UInt32] = []
    // Native startup owns an empty structured-exception chain (the join's
    // word 0); root source frames start from it.
    private var threadHead:UInt32 = 0xffffffff
    private(set) var transportCounts:[String:UInt64] = [:]
    private func count(_ kind:String) {transportCounts[kind,default:0] += 1}
    private func word(_ token:UInt32)->UInt32? {heap.lookup(token,words:1)?.pointee}
    private func putWord(_ token:UInt32,_ value:UInt32)->Bool {
        guard let p = heap.lookup(token,words:1) else {return false}
        p.pointee = value;return true
    }
    /// Installs the join's election from level-one-transports.json.
    func installLevelTransports(_ data:Data) throws {
        guard let raw = try JSONSerialization.jsonObject(with:data) as? [String:Any],
              let thunks = raw["tail_thunks"] as? [String:String],let only = raw["tail_only"] as? [String],
              let extents = raw["frame_extents"] as? [String:Int] else {throw Failure.invalid("Level 1 transport election")}
        func address(_ text:String) throws -> UInt32 {
            guard text.hasPrefix("0x"),let value = UInt32(text.dropFirst(2),radix:16) else {throw Failure.invalid("Level 1 transport address")}
            return value
        }
        tailThunks = [:];for (k,v) in thunks {tailThunks[try address(k)] = try address(v)}
        tailOnly = Set(try only.map(address))
        originalDirectCalls = [:]
        for (caller, targets) in raw["original_direct_calls"] as? [String:[String]] ?? [:] {
            originalDirectCalls[try address(caller)] = Set(try targets.map(address))
        }
        frameExtents = [:];for (k,v) in extents {frameExtents[try address(k)] = UInt32(v)}
    }
    /// Disjoint automatic frame below the innermost entry's original extent.
    private var childFrame:UInt32? {
        guard let last = frames.last else {return nil}
        let caller = functions.last ?? 0
        return last-claw_level_child_gap(frameExtents[caller] ?? 0)
    }
    @discardableResult func invoke(_ function:UInt32,_ receiver:UInt32,_ arguments:[UInt32] = [],frame:UInt32 = 0,
                                   source:UnsafeMutablePointer<ClawSourceContext>? = nil,returnPC:UInt32 = 0,
                                   x87:UnsafeMutablePointer<ClawX87State>? = nil)->UInt32 {
        recent.append(.invoke(function,receiver,arguments))
        if function == 0x4cb9b0,Self.countInvokes {drawingWorld = receiver}
        if Self.countInvokes {invokeCounts[function,default:0] += 1}
        guard !closed,fault == 0,frames.count < 64,missingOwner != function else {return fail(function)}
        if function == 0x4b54f0 || function == 0x4b54a0 {beforeMusicLookup?()}
        if function == 0x4b67f0,arguments.count == 2,let missingResource,text(arguments[0]) == missingResource {return 0}
        if let owner = packageOwner,owner.sourceAllocations[receiver] != nil,
           [UInt32(0x4b61b0),0x4b61c0,0x4b6230].contains(function) {
            let result = owner.resource(function,token:receiver)
            guard owner.fault == 0 else {return fail(function)}
            // Preserve distinct BMP/PID resource keys and source enumeration
            // precedence while the physical BMP adapter supplies indexed PID.
            return function == 0x4b61b0 && result == 0x424d50 ? 0x504944:result
        }
        let blocking = observeBlockingInvocation != nil && [UInt32(0x45dc90),0x48f500,0x48f740,0x4ec9c0,0x4b8960].contains(function)
        if blocking {observeBlockingInvocation?(function,true)}
        defer {if blocking {observeBlockingInvocation?(function,false)}}
        let entry = frame == 0 ? (childFrame ?? stack):frame
        guard entry >= 0x01ff0000+0x100,UInt64(entry)+UInt64(4*(arguments.count+1)) <= 0x02010000,arguments.count <= 32 else {return fail(function)}
        var owner = ClawLevelOwner()
        if x87 == nil, claw_level_x87_environment(function) != 0 {
            // An ordinary root has no live caller stack. Exact nested calls below
            // carry the caller's full environment and publish the callee's flags.
            var empty = ClawX87State(); claw_level_x87_empty_request(&empty)
            empty.pushCount = 0
            return invoke(function,receiver,arguments,frame:frame,source:source,returnPC:returnPC,x87:&empty)
        }
        let contract = claw_level_owner(function,&owner) == 1 && owner.sourceCapability != 0 && x87 == nil
        if let source,contract {
            // A caller's ordinary source edge may claim less than the admitted
            // callee guarantees; narrow it explicitly, as the join does.
            var adapted = ClawSourceContext()
            let narrowing = claw_level_narrow_source(source,&owner,&adapted)
            if narrowing != UInt32(CLAW_LEVEL_SOURCE_SAME) {
                if narrowing == UInt32(CLAW_LEVEL_SOURCE_INCOMPATIBLE) {
                    guard claw_level_checked_source_adapt(source,&owner,&adapted) == 1 else {return fail(function)}
                    count("source-checked-adaptation")
                } else {count("source-narrowed")}
                let value = invoke(function,receiver,arguments,frame:entry,source:&adapted,returnPC:returnPC)
                if fault != 0 {
                    claw_level_restore_source(source,&adapted)
                    return value
                }
                guard claw_level_source_return_ok(source,&adapted) == 1 else {return fail(function)}
                claw_level_restore_source(source,&adapted)
                return value
            }
        }
        if source == nil,contract {
            // Root source frame: the harness continuation and the argument
            // words a real CALL would have pushed.
            var root = ClawSourceContext()
            claw_level_root_source(&root,&owner,entry,function,receiver,threadHead)
            guard putWord(entry,UInt32(CLAW_LEVEL_STOP)) else {return fail(function)}
            for (index,value) in arguments.enumerated() {guard putWord(entry+4+UInt32(index*4),value) else {return fail(function)}}
            count("source-root")
            let value = invoke(function,receiver,arguments,frame:entry,source:&root,returnPC:UInt32(CLAW_LEVEL_STOP))
            if fault == 0 {threadHead = root.fsHead}
            return value
        }
        let previous = host.pointee.entryStackPointer
        let priorSource = host.pointee.sourceContext,priorReturn = host.pointee.sourceReturnPC
        host.pointee.entryStackPointer = entry;frames.append(entry);functions.append(function)
        host.pointee.sourceContext = source;host.pointee.sourceReturnPC = source == nil ? 0:returnPC
        let diagnostic = function == 0x4bd260 || function == 0x4b4ed0
        if diagnostic {diagnosticFrames.append(entry)}
        defer {
            if diagnostic {diagnosticFrames.removeLast()}
            frames.removeLast();functions.removeLast();host.pointee.entryStackPointer = previous
            host.pointee.sourceContext = priorSource;host.pointee.sourceReturnPC = priorReturn
        }
        if source == nil,frames.count == 1,frame == 0,!diagnostic,!putWord(entry,UInt32(CLAW_LEVEL_STOP)) {return fail(function)}
        if diagnostic {
            // This policy reloads the caller's three argument words through
            // Run::automatic, including after physical callbacks. Materialize
            // them on the existing menu frame, never on a second host stack.
            guard arguments.count == 3,receiver == 0,let bytes = heap.lookupBytes(entry+4,count:12) else {return fail(function)}
            arguments.withUnsafeBytes{bytes.update(from:$0.baseAddress!.assumingMemoryBound(to:UInt8.self),count:12)}
        } else if source == nil,!arguments.isEmpty {
            // Ordinary entries may reread their stack arguments through the
            // original frame (0x426e30 reads LPARAM at ESP+0xc). Publish the
            // words a real CALL would have pushed, as the Level 1 join does.
            guard let bytes = heap.lookupBytes(entry+4,count:UInt32(arguments.count*4)) else {return fail(function)}
            arguments.withUnsafeBytes{bytes.update(from:$0.baseAddress!.assumingMemoryBound(to:UInt8.self),count:arguments.count*4)}
        }
        if function == 0x46aeb0 || function == 0x46a6d0 {
            placementActors.removeAll();placementChildren.removeAll();placementOwners.removeAll()
            checkpointPickupAwards.removeAll()
            runtimeLoot.removeAll();checkpointFactories.removeAll()
        }
        let previousPlacement = loadingPlacement
        if function == 0x4d17e0, let record = arguments.first {
            loadingPlacement = (.init(plane: word(receiver+4) ?? 0, id: word(record) ?? 0), receiver)
        } else if arguments.count == 1,let actor = arguments.first,
                  let owner = placementOwners[actor],
                  heap.containingAllocationIdentity(at:actor,count:0x1b4) === owner.actor.identity,
                  word((word(actor+0x6c) ?? 0)+0x10) == function {
            // Spawned pickups inherit the placement that produced them. Keep
            // provenance through actual callbacks, never by coordinate guesses.
            loadingPlacement = (owner.key,owner.actor.plane)
        }
        defer {loadingPlacement = previousPlacement}
        // Original loader publishes its final actor here. Some logic constructors
        // replace the first allocation, so allocation order is not identity.
        if function == 0x4d51a0, let value = loadingPlacement, let actor = arguments.first,
           let identity = heap.containingAllocationIdentity(at: actor, count: 0x1b4) {
            let record = PlacementActor(token:actor,plane:value.plane,identity:identity)
            if functions.contains(0x4d17e0), (word(actor+8) ?? 0) & 0x40000 != 0,
               let logic = word(actor+0x6c), let id = word(logic+4) {
                // A composed loader can reuse its input buffer before the
                // host edge returns. The initialized actor owns the final id.
                let key = ClawCheckpointPlacement(plane:word(value.plane+4) ?? value.key.plane,id:id)
                placementActors[key] = record
                placementOwners[actor] = (key,record)
            } else {
                placementOwners[actor] = (value.key,record)
                if !(placementChildren[value.key] ?? []).contains(where:{$0.token == actor && $0.identity === identity}) {
                    placementChildren[value.key,default:[]].append(record)
                }
            }
        }
        if function == 0x4737c0, let actor = arguments.first,
           ProcessInfo.processInfo.arguments.contains("--custom-checkpoint-check") {
            let owner = placementOwners[actor]
            checkpointPickupAwards.append(["actor":actor,"item":word(actor+4) ?? 0,
                "x":word(actor+0x4c) ?? 0,"y":word(actor+0x50) ?? 0,
                "placement":owner?.key.id as Any? ?? NSNull()])
        }
        observeInvocation?(function,receiver,arguments)
        if let result = gameService?(function,receiver,arguments) {return result}
        var result:UInt32 = 0
        let done = heap.withStableFreedStorage {arguments.withUnsafeBufferPointer {args -> UInt32 in
            if let x87 {
                if claw_level_x87_environment(function) != 0 {
                    return claw_level_x87_environment_invoke(claw_level_x87_entry(function),function,receiver,
                        args.baseAddress,UInt32(args.count),host,x87,&result)
                }
                // Owned x87 result: ENTRY/RESULT through the registry owner.
                return claw_level_x87_owned_invoke(claw_level_x87_entry(function),function,receiver,
                                                   args.baseAddress,UInt32(args.count),host,x87,&result)
            }
            let accepted = claw_native_menu_resource_entry(function,receiver,args.baseAddress,UInt32(args.count),host,&result)
            if accepted == 1 || fault != 0 {return accepted}
            return gameEntry?(function,receiver,args.baseAddress,UInt32(args.count),host,&result) ?? 0
        }}
        guard done == 1,fault == 0 else {return fail(host.pointee.faultAddress == 0 ? function:host.pointee.faultAddress)}
        // Runtime factories insert into the scene's active list directly,
        // bypassing the WWD publication edge above (notably treasure spawns).
        if [UInt32(0x4c8da0),0x4c8be0].contains(function), result != 0,
           let identity = heap.containingAllocationIdentity(at:result,count:0x1b4) {
            let scene = word(result+0xc) ?? 0
            let record = PlacementActor(token:result,plane:loadingPlacement?.plane ?? word((word(scene+0x24) ?? 0)+0x5c) ?? 0,identity:identity)
            if function == 0x4c8da0,arguments.count == 6,let name = text(arguments[4]),
               ClawCheckpointLoot.supported.contains(name) {
                runtimeLoot[result] = RuntimeLoot(actor:record,owner:loadingPlacement?.key,logic:name,identifier:arguments[0],z:arguments[3],flags:arguments[5])
            }
            if ProcessInfo.processInfo.arguments.contains("--custom-checkpoint-check"),checkpointFactories.count < 128 {
                checkpointFactories.append(["factory":String(function,radix:16),"arguments":arguments,
                    "owner":loadingPlacement?.key.id as Any? ?? NSNull(),"actor":result,"callback":word((word(result+0x6c) ?? 0)+0x10) ?? 0])
            }
            if let value = loadingPlacement {
            placementOwners[result] = (value.key,record)
            if !(placementChildren[value.key] ?? []).contains(where:{$0.token == result && $0.identity === identity}) {
                placementChildren[value.key,default:[]].append(record)
            }
            }
        }
        if Self.traceDepth > 16 {recent.append(.ret(function,result))}
        completedInvocation?(function,result)
        // Initial startup calls its owned loadLevel body directly; later map
        // loads enter 46aeb0. Both are complete before gameplay can run.
        if result != 0, function == 0x46aeb0 || function == 0x46a6d0 { levelLoaded?(receiver) }
        return result
    }
    func open() throws {
        guard !closed,archive == 0 else {throw Failure.invalid("Archive lifetime")}
        // Stream the hash; do not map or copy the supported archive.
        if FileManager.default.fileExists(atPath:archiveURL.path) {
            let file = try FileHandle(forReadingFrom:archiveURL)
            defer {try? file.close()}
            var hash = SHA256()
            while let data = try file.read(upToCount:1<<20),!data.isEmpty {hash.update(data:data)}
            let actual = hash.finalize().map({String(format:"%02x",$0)}).joined()
            guard Self.supportedArchiveHashes.contains(actual) else {
                throw Failure.invalid("Unsupported archive hash")
            }
            installedArchiveHash = actual
        }
        archive = allocate(0x48)
        _ = invoke(0x4b7210,archive)
        let path = textToken("CLAW.REZ")
        let result = invoke(0x4b72e0,archive,[path,1,0])
        release(path)
        guard result == 1,fault == 0 else {throw Failure.invalid("Original archive open failed at \(String(faultAddress,radix:16))")}
    }
    func mountPackage(_ data:Data) throws {
        unmountPackage()
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("Claw-assets-"+SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined()+".rez")
        try data.write(to:url,options:.atomic);packageURL = url
        let owner = try ClawNativeResourceArchive(heap:heap,url:url)
        owner.mappedPayloadPages = true
        packageOwner = owner;packageArchive = owner.controller
    }
    func packageDirectory(_ path:String)->UInt32 {
        packageOwner?.lookupFolder(path) ?? 0
    }
    func unmountPackage() {
        packageOwner?.shutdown();packageOwner = nil;packageArchive = 0
        if let packageURL {try? FileManager.default.removeItem(at:packageURL)}
        packageURL = nil
    }
    func directory(_ path:String)->UInt32 {
        let token = textToken(path);defer {release(token)}
        return invoke(0x4b7f20,archive,[token])
    }
    func resource(directory:UInt32,name:String,type:UInt32)->UInt32 {
        if missingResource == name {return 0}
        let token = textToken(name);defer {release(token)}
        return invoke(0x4b67f0,directory,[token,type])
    }
    func load(_ resource:UInt32)->Data? {
        guard resource != 0,let words = heap.lookup(resource,words:6) else {return nil}
        let count = words[5],bytes = invoke(0x4b61c0,resource)
        guard bytes != 0,fault == 0,let pointer = heap.lookupBytes(bytes,count:count) else {return nil}
        let data = Data(bytes:pointer,count:Int(count));_ = invoke(0x4b6230,resource)
        return fault == 0 ? data:nil
    }
    /// Compiler-frame diagnostic accessors used by indexed-table errors. Their
    /// only memory input is the caller's saved continuation or frame word.
    private func compilerDiagnostic(_ q:ClawCall)->UInt32? {
        guard let p = q.compilerContext else {return nil}
        let f = q.function,c = p.pointee
        guard (f == 0x4db5f0 || f == 0x4dc680),q.receiver == 0,q.receiver2 == 0,q.argumentCount == 0,q.stackPointer == 0,
              q.sourceContext == nil,q.sourceReturnPC == 0,q.x87ArgumentCount == 0,q.x87State == nil,
              q.x87Operation == 0,q.callbackCPU == nil,q.callbackActivation == 0,
              q.sourceTransferVersion == 0,q.sourceTransferKind == 0,q.sourceTransferSite == 0,
              q.sourceCallerFunction == 0,q.sourceDisposition == nil,
              c.size == UInt32(MemoryLayout<ClawCompilerContext>.size),c.version == UInt32(CLAW_CONTEXT_VERSION),
              c.reserved0 == 0,c.reserved1 == 0,c.inputMask == 0x5c1,c.outputMask == 0x5c1,
              c.eip == f,c.esp >= 0x01ff0000,c.esp <= 0x02010000-4,c.esp & 3 == 0,
              c.continuation != 0,c.continuation != UInt32(CLAW_STACK_RETURN_SENTINEL),
              !(0x01ff0000..<0x02010000).contains(c.continuation),
              c.fsHead == UInt32.max || (c.fsHead >= 0x01ff0000 && c.fsHead <= 0x02010000-12 && c.fsHead & 3 == 0),
              word(c.esp) == c.continuation,
              let value = word(f == 0x4db5f0 ? c.esp:c.ebp &+ 4) else {return fail(f)}
        p.pointee.eax = value;p.pointee.eip = c.continuation;p.pointee.esp = c.esp+4
        count("compiler-diagnostic")
        return value
    }
    /// Contextual transports of the Level 1 join (LevelOneNativeJoin.service),
    /// in its order. Returns nil for an ordinary request (served below).
    private func levelTransport(_ request:ClawCall,request pointer:UnsafePointer<ClawCall>?)->UInt32? {
        if request.compilerContext != nil {return compilerDiagnostic(request)}
        var q = request
        let f = q.function,caller = functions.last ?? 0
        var owner = ClawLevelOwner()
        let owned = claw_level_owner(f,&owner) == 1
        let a = withUnsafeBytes(of:q.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(min(q.argumentCount,32))))}
        let plainTransfer = q.sourceTransferVersion == 0 && q.sourceTransferKind == 0 && q.sourceTransferSite == 0 &&
            q.sourceCallerFunction == 0 && q.sourceDisposition == nil
        if tailOnly.contains(f), let table = word(q.receiver),
           claw_level_pirate_base_call_ok(&q, caller, table, word(table &+ (f == 0x44e0c0 ? 0x5c : 0x58)) ?? 0) == 1 {
            count("pirate-base-direct")
            if f == 0x44e0c0 { count("pirate-death-base-direct") }
            return nil
        }
        if tailOnly.contains(f), let table = word(q.receiver),
           claw_level_boss_base_call_ok(&q, caller, table, word(table &+ 0x5c) ?? 0) == 1 {
            count("boss-base-direct")
            return nil
        }
        if tailOnly.contains(f),owned,let table = word(q.receiver),
           claw_level_state_base_call_ok(&q,caller,word(table &+ 8) ?? 0) == 1 {
            count("state-base-direct")
            count("state-base-direct-"+String(caller,radix:16))
            return nil
        }
        if tailOnly.contains(f),owned,let table = word(q.receiver),
           claw_level_enemy_lift_base_ok(&q,caller,word(table &+ 0x88) ?? 0) == 1 {
            count("enemy-lift-base-direct")
            count("enemy-lift-base-direct-"+String(caller,radix:16))
            return nil
        }
        var directConvention:UInt32 = 0,directCount:UInt32 = 0
        if tailOnly.contains(f),owned,word(q.receiver) != nil,
           claw_level_owner_abi(f,&directConvention,&directCount) == 1,directConvention == 2,
           claw_level_original_direct_ok(&q,caller,originalDirectCalls[caller]?.contains(f) == true ? 1:0,directCount) == 1 {
            // An immediate CALL names the base implementation itself. Derived
            // classes may override its slot; vtable membership is not required.
            // The relation comes from authenticated original instruction edges.
            count("original-base-direct")
            if q.sourceContext == nil {return nil}
        } else if tailOnly.contains(f),tailThunks[caller] == nil,caller != 0,claw_level_game_range(caller) == 1 {
            // The election calls these owners tail-only because the join reached
            // them only through a thunk. Game code also calls them directly as
            // ordinary virtuals, including Level 6 source-context enemy states.
            // Prove the same receiver-vtable membership on both paths. A source
            // CALL must continue through the normal source transport below so
            // its continuation, stack pop and register contract are preserved.
            guard owned,let table = word(q.receiver),
                  claw_level_tail_direct_ok(&q,caller,
                    (0..<64).contains(where:{word(table &+ UInt32($0*4)) == f}) ? 1:0) == 1 else {return fail(f)}
            count("tail-only-direct")
            if q.sourceContext == nil {return nil}
            count("tail-only-direct-source")
            count("tail-only-direct-source-"+String(f,radix:16))
        } else if tailOnly.contains(f) {
            // Reached only as the vtable target of the innermost elected thunk.
            let slot = tailThunks[caller] ?? 0
            let vtable = word(q.receiver).flatMap{word($0 &+ slot)} ?? 0
            guard claw_level_tail_only_ok(&q,slot,vtable) == 1 else {return fail(f)}
            count("tail-only")
            return nil
        }
        if q.x87ArgumentCount == UInt32(CLAW_X87_EXACT),owned,claw_level_is_game(f) == 1 {
            guard let state = q.x87State,q.compilerContext == nil,q.callbackCPU == nil,plainTransfer else {return fail(f)}
            if claw_level_x87_environment(f) != 0 {
                guard q.sourceContext == nil,q.sourceReturnPC == 0,q.receiver2 == 0,
                      q.callbackActivation == 0,q.x87Operation == 0 else {return fail(f)}
                let value = invoke(f,q.receiver,a,frame:q.stackPointer,x87:state)
                guard fault == 0 else {return 0}
                count("x87-environment");return value
            }
            switch claw_level_x87_exact_kind(state,owner.returnsX87) {
            case UInt32(CLAW_LEVEL_X87_OWNED):
                guard q.sourceContext == nil else {return fail(f)}
                let value = invoke(f,q.receiver,a,frame:q.stackPointer,x87:state)
                guard fault == 0 else {return 0}
                count("x87-owned");return value
            case UInt32(CLAW_LEVEL_X87_BALANCED):
                // An ordinary owner neither reads nor changes the caller's x87 stack.
                let before = state.pointee
                let value = invoke(f,q.receiver,a,frame:q.stackPointer,source:q.sourceContext,returnPC:q.sourceReturnPC)
                guard fault == 0 else {return 0}
                let same = withUnsafeBytes(of:before){b in withUnsafeBytes(of:state.pointee){$0.elementsEqual(b)}}
                guard same else {return fail(f)}
                state.pointee.returned = 1;state.pointee.eax = value;state.pointee.edx = 0
                count("x87-balanced");return value
            default: return fail(f)
            }
        }
        if q.x87ArgumentCount == 0,owned,owner.returnsX87 != 0 {
            // Ordinary call into an x87-result owner: only the reviewed
            // discard sites, entered on an empty stack.
            guard claw_level_x87_discard_elected(caller,f) == 1,q.compilerContext == nil,q.callbackCPU == nil,
                  q.x87State == nil,q.sourceContext == nil,plainTransfer else {return fail(f)}
            var empty = ClawX87State();claw_level_x87_empty_request(&empty)
            let value = invoke(f,q.receiver,a,frame:q.stackPointer,x87:&empty)
            guard fault == 0 else {return 0}
            if caller == 0x4181c0 && f == 0x420dd0 { count("rope-jump-x87") }
            count("x87-discarded");return value
        }
        if owned,claw_level_is_game(f) == 1,claw_level_game_range(f) == 0 {
            // Reviewed game-owned spatial-grid bodies inside the CRT/MFC range.
            guard q.x87ArgumentCount == 0,q.compilerContext == nil,q.callbackCPU == nil,plainTransfer else {return fail(f)}
            count("game-in-library-range")
            return invoke(f,q.receiver,a,frame:q.stackPointer,source:q.sourceContext,returnPC:q.sourceReturnPC)
        }
        if plainTransfer {
            guard let cpu = q.sourceContext else {return nil}
            guard q.compilerContext == nil,q.callbackCPU == nil,q.x87ArgumentCount == 0,q.x87State == nil else {return fail(f)}
            if claw_level_game_range(f) == 1 {
                guard owned,q.stackPointer == cpu.pointee.esp else {return fail(f)}
                if owner.sourceCapability == 0 {
                    // Ordinary owner reached by a source CALL (0x4141f0 -> a cannon logic state):
                    // run it without the context, then return to the caller's continuation.
                    var pop:UInt32 = 0,convention:UInt32 = 0,argc:UInt32 = 0
                    guard claw_level_owner_abi(f,&convention,&argc) == 1,
                          claw_level_ordinary_source_ok(&q,word(cpu.pointee.esp) ?? 0,&owner,convention,argc,&pop) == 1 else {return fail(f)}
                    let value = invoke(f,q.receiver,a,frame:q.stackPointer)
                    guard fault == 0 else {return 0}
                    claw_level_physical_source_return(cpu,q.sourceReturnPC,pop,value)
                    count("source-ordinary");return value
                }
                count("source-call")
                return invoke(f,q.receiver,a,frame:q.stackPointer,source:cpu,returnPC:q.sourceReturnPC)
            }
            return physicalSource(q,cpu)
        }
        // Explicit zero-argument source tail JMP: the target runs on the
        // caller's frame and returns to the caller's own continuation.
        guard let cpu = q.sourceContext,let pointer,claw_level_tail_request_ok(&q,word(cpu.pointee.esp) ?? 0) == 1 else {return fail(f)}
        let entry = cpu.pointee.esp
        let value:UInt32
        if claw_level_is_game(f) == 1 {
            guard owned else {return fail(f)}
            value = invoke(f,q.receiver,[],frame:entry,source:cpu,returnPC:q.sourceReturnPC)
        } else {
            var plain = ClawCall()
            plain.function = f;plain.receiver = q.receiver;plain.receiver2 = q.receiver2
            plain.stackPointer = entry;plain.sourceContext = cpu;plain.sourceReturnPC = q.sourceReturnPC
            value = physicalSource(plain,cpu)
        }
        guard fault == 0,claw_level_tail_receipt(pointer,entry) == 1 else {return fail(f)}
        count("source-tail");return value
    }
    /// Physical stand-in served from a source context: the provider's EAX,
    /// and the callee's return to the caller continuation.
    private func physicalSource(_ request:ClawCall,_ cpu:UnsafeMutablePointer<ClawSourceContext>)->UInt32 {
        var q = request,pop:UInt32 = 0
        guard claw_level_physical_source_frame_ok(&q,word(cpu.pointee.esp) ?? 0) == 1,
              claw_level_physical_source_pop(q.function,q.argumentCount,&pop) == 1 else {return fail(q.function)}
        var plain = q
        plain.sourceContext = nil;plain.sourceReturnPC = 0
        let value = service(plain)
        guard fault == 0 else {return 0}
        claw_level_physical_source_return(cpu,q.sourceReturnPC,pop,value)
        if q.function == 0x4a3050 {count("source-crt-rand")}
        count("source-physical");return value
    }
    func service(_ q:ClawCall,request:UnsafePointer<ClawCall>? = nil)->UInt32 {
        guard !closed,fault == 0 else {return fail(q.function)}
        if Self.traceDepth > 16, q.x87ArgumentCount == UInt32(CLAW_X87_EXACT) {
            let s = q.x87State?.pointee
            recent.append(text:"exact x87 \(String(q.function,radix:16)) source=\(q.sourceContext != nil) return=\(q.sourceReturnPC) op=\(q.x87Operation) cw=\(s?.control ?? 0) sw=\(s?.status ?? 0) count=\(s?.count ?? 0) returned=\(s?.returned ?? 0)")
        }
        if q.function == 0x4d5fe0 {return uncompress(q)}
        if let value = levelTransport(q,request:request) {return value}
        if q.x87ArgumentCount != 0 {
            guard !closed,fault == 0,missingService != q.function,q.argumentCount <= 2,
                  q.sourceTransferVersion == 0 else {return fail(q.function)}
            var call = q,result:UInt32 = 0
            guard claw_native_menu_math_service(&call,&result) == 1 else {
                let state = q.x87State?.pointee
                recent.append(text:"refused x87 \(String(q.function,radix:16)) kind=\(q.x87ArgumentCount) op=\(q.x87Operation) args=\(q.argumentCount) depth=\(state?.count ?? 0) pop=\(state?.popCount ?? 0) push=\(state?.pushCount ?? 0)")
                return fail(q.function)
            }
            if q.function != 0 {mathServiceCounts[q.function,default:0] += 1}
            return result
        }
        guard !closed,fault == 0,q.argumentCount <= 32,q.compilerContext == nil,q.sourceContext == nil,
              q.x87ArgumentCount == 0,q.sourceTransferVersion == 0,missingService != q.function else {return fail(q.function)}
        let a = withUnsafeBytes(of:q.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(q.argumentCount)))}
        recent.append(.service(q.function,q.receiver,a))
        // Script callbacks are native host entries, outside the retail address
        // range. Keep the actor call's frame when reentering the Lua owner;
        // it validates the live actor before dispatching any script or built-in.
        if (ClawCustomLua.callback...ClawCustomLua.callback+2).contains(q.function) {
            guard q.receiver == 0,a.count == 1 else {return fail(q.function)}
            return invoke(q.function,0,a,frame:q.stackPointer)
        }
        // Explicit native elections for the single-player F2-F8 guard and
        // DirectDraw BMP transport. Both addresses lie in the game's broad
        // address range, ahead of its default canonical-owner dispatch.
        if q.function == 0x42aa90 || q.function == 0x4b9e10 {
            return dependency?(q) ?? fail(q.function)
        }
        // Native CRect construction used by the recovered text drawing path.
        if q.function == 0x4dfec0 {
            guard a.count == 4,q.receiver != 0,
                  let bytes = heap.lookupBytes(q.receiver,count:16) else {return fail(q.function)}
            for (index,value) in a.enumerated() {
                for byte in 0..<4 {bytes[index*4+byte] = UInt8(truncatingIfNeeded:value >> (byte*8))}
            }
            count("native-rect-constructor")
            return q.receiver
        }
        // Retail command formatting followed by CreateProcessA. Neither native
        // platform can execute the original Win32 auxiliary programs. Preserve
        // the selected command and working directory, and expose launch failure.
        if q.function == 0x42beb0 {
            guard a.count == 2 else {return fail(q.function)}
            func text(_ token:UInt32)->[UInt8]? {
                guard token != 0 else {return nil}
                var bytes:[UInt8] = []
                for offset:UInt32 in 0..<256 {
                    guard token <= UInt32.max-offset,
                          let byte = heap.lookupBytes(token+offset,count:1) else {return nil}
                    if byte.pointee == 0 {return bytes}
                    bytes.append(byte.pointee)
                }
                return nil
            }
            guard let executable = text(a[0]),let directory = a[1] == 0 ? []:text(a[1]) else {return fail(q.function)}
            let separator:[UInt8] = directory.isEmpty || directory.last == 92 ? []:[92]
            let command = directory+separator+executable
            guard command.count < 256 else {return fail(q.function)}
            record(["service":"Windows process unavailable","command_bytes":command,
                    "directory":directory.isEmpty ? 0:a[1],"result":0])
            return 0
        }
        if claw_level_game_range(q.function) == 1 {
            return invoke(q.function,q.receiver,a,frame:q.stackPointer)
        }
        do {
            switch q.function {
            case 0x4a4450:
                // Beyond 4096 elements only the large grid profile the vector
                // constructor iterator (0x4a4590 below) elects: eight-byte cells
                // with the 0x4c96b0 destructor inside one owned allocation.
                let grid = a.count == 4 && a[2] > 4096 && a[2] <= Self.gridCellLimit && a[1] == 8 && a[3] == 0x4c96b0 &&
                    owningAllocation(a[0]).map{a[0]+a[1]*a[2] <= $0.token+$0.bytes} == true
                guard a.count == 4,a[1] > 0,a[2] <= 4096 || grid,
                      heap.lookupBytes(a[0],count:a[1]*a[2]) != nil else {break}
                if grid {record(["service":"CRT vector destructor iterator","base":a[0],"stride":a[1],"count":a[2]])}
                for index in (0..<a[2]).reversed() {
                    _ = invoke(a[3],a[0]+index*a[1],frame:q.stackPointer == 0 ? 0:q.stackPointer-4)
                    if fault != 0 {return 0}
                }
                return 0
            case 0x4a4590:
                // Beyond 4096 elements only the elected large grid profile:
                // eight-byte cells inside one owned allocation.
                let grid = a.count == 5 && a[2] > 4096 && a[2] <= Self.gridCellLimit && a[1] == 8 && a[3] == 0x4f4a90 &&
                    a[4] == 0x4c96b0 && owningAllocation(a[0]).map{a[0]+a[1]*a[2] <= $0.token+$0.bytes} == true
                guard a.count == 5,a[1] > 0,a[2] <= 4096 || grid,
                      heap.lookupBytes(a[0],count:a[1]*a[2]) != nil else {break}
                if grid {record(["service":"CRT vector constructor iterator","base":a[0],"stride":a[1],"count":a[2]])}
                for index in 0..<a[2] {
                    _ = invoke(a[3],a[0]+index*a[1],frame:q.stackPointer == 0 ? 0:q.stackPointer-4)
                    if fault != 0 {return 0}
                }
                return 0
            case 0x4a9070: // CRT realloc on the shared ledger.
                guard a.count == 2,a[1] <= 0x800000,a[0] == 0 || allocations.contains(a[0]) else {break}
                let result = a[1] == 0 ? 0:allocate(a[1])
                if result != 0,a[0] != 0,let size = allocationSizes[a[0]] {
                    let count = min(a[1],size)
                    guard let from = heap.lookupBytes(a[0],count:count),let to = heap.lookupBytes(result,count:count) else {break}
                    to.update(from:from,count:Int(count))
                }
                if a[0] != 0 {release(a[0])}
                record(["service":"CRT realloc","previous":a[0],"result":result,"size":a[1]])
                return result
            case 0x4f1e20: // CRT qsort: the elected 256-byte palette sort.
                guard a.count == 4,a[1] == 256,a[2] == 1,a[3] == 0x4c70b0,
                      let bytes = heap.lookupBytes(a[0],count:256) else {break}
                let comparator = a[3],base = a[0],frame = q.stackPointer == 0 ? 0:q.stackPointer-64
                var context = (owner:self,base:base,comparator:comparator,frame:frame)
                var comparisons:UInt32 = 0,swaps:UInt32 = 0
                let done = withUnsafeMutablePointer(to:&context) {pointer in
                    claw_level_adjacent_sort(bytes,256,{u,left,right,value in
                        let c = u!.assumingMemoryBound(to:(owner:ClawNativeMenuResources,base:UInt32,comparator:UInt32,frame:UInt32).self).pointee
                        let result = c.owner.invoke(c.comparator,0,[c.base+left,c.base+right],frame:c.frame)
                        guard c.owner.fault == 0 else {return 0}
                        value!.pointee = result;return 1
                    },pointer,&comparisons,&swaps)
                }
                guard done == 1,fault == 0 else {return fail(q.function)}
                record(["service":"CRT qsort","base":base,"comparisons":comparisons,"swaps":swaps])
                return 0
            case 0x4a36f0:
                // Native MSVC RTTI: vtable[-1] names the complete-object
                // locator, whose type descriptor must have eight readable bytes.
                var result:UInt32 = 0
                guard q.receiver == 0,q.receiver2 == 0,a.count == 1,
                      claw_level_native_type_info(host,a[0],&result) == 1 else {break}
                return result
            case 0x4f2060:
                var result:UInt32 = 0
                guard q.receiver == 0,q.receiver2 == 0,a.count == 3,
                      claw_level_native_strncat(host,a[0],a[1],a[2],&result) == 1 else {break}
                return result
            case 0x4f63ec,0x4a48e0:
                guard a.count == 1 else {break}
                // The app retains the old engine layout while its v1.3 sound
                // manager adds the zero-default repeat interval at +0x34.
                let soundManager = q.function == 0x4f63ec && functions.last == 0x4cea10 && a[0] == 0x34
                let token = allocate(soundManager ? 0x38 : a[0])
                if soundManager {heap.lookup(token+0x34,words:1)?.pointee = 0}
                // Guest new/malloc are uninitialized storage, not calloc.
                // Use the original trace's deterministic heap fill. In particular,
                // Cutthroat's constructor leaves its +0x468 speech latch untouched;
                // zero-filling it invents a first-sighting voice request.
                if let bytes = heap.lookupBytes(token,count:max(a[0],1)) {
                    bytes.update(repeating:0xa5,count:Int(max(a[0],1)))
                }
                return token
            case 0x4f6428,0x4a49b0:
                guard a.count == 1 else {break}
                release(a[0])
                return 0
            case 0x4a3a20,0x4ad460:
                var result:UInt32 = 0
                guard a.count == 2,q.receiver == 0,q.receiver2 == 0,
                      claw_native_menu_byte_search(host,a[0],a[1],q.function == 0x4ad460 ? 1:0,&result) == 1 else {break}
                return result
            case 0x4a7920:
                // FILE storage here uses unbuffered, read-only FileHandles.
                // fflush has no pending output to write; NULL flushes all.
                guard a.count == 1,a[0] == 0 || files[a[0]] != nil else {break}
                return 0
            case 0x4a3990:
                var result:UInt32 = 0
                guard a.count == 2,q.receiver == 0,q.receiver2 == 0,
                      claw_native_menu_substring(host,a[0],a[1],&result) == 1 else {break}
                return result
            case 0x5469e4:
                guard a.count == 1,q.receiver == 0,q.receiver2 == 0 else {break}
                if a[0] == 0 {return 0}
                var end:UInt32 = 0
                guard claw_native_menu_byte_search(host,a[0],0,0,&end) == 1 else {break}
                return end-a[0]
            case 0x4f1d90:
                guard a.count == 2,text(a[0]) == "CLAW.REZ",text(a[1]) == "rb" else {break}
                let handle:UInt32
                if FileManager.default.fileExists(atPath:archiveURL.path) {
                    let file = try FileHandle(forReadingFrom:archiveURL);handle = allocate(32);files[handle] = file
                } else {handle = 0}
                record(["service":"open","path":"CLAW.REZ","success":handle != 0]);return handle
            case 0x4a7840:
                guard a.count == 3,let file = files[a[0]],a[2] <= 2 else {break}
                let offset = Int64(Int32(bitPattern:a[1]))
                let base = a[2] == 0 ? 0:try (a[2] == 1 ? file.offset():file.seekToEnd())
                guard Int64(base)+offset >= 0 else {break}
                try file.seek(toOffset:UInt64(Int64(base)+offset));return 0
            case 0x4a7260:
                guard a.count == 4,let file = files[a[3]],UInt64(a[1])*UInt64(a[2]) <= 4<<20,
                      let pointer = heap.lookupBytes(a[0],count:a[1]*a[2]) else {break}
                let offset = try file.offset(),data = try file.read(upToCount:Int(a[1]*a[2])) ?? Data()
                data.copyBytes(to:pointer,count:data.count)
                record(["service":"read","offset":offset,"requested":a[1]*a[2],"bytes":data.count,
                               "sha256":SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined()])
                return a[1] == 0 ? 0:UInt32(data.count)/a[1]
            case 0x4a7ae0:
                guard a.count == 1 else {break}
                if retiredFiles.contains(a[0]) {
                    record(["service":"close","result":UInt32.max]);return .max
                }
                guard let file = files.removeValue(forKey:a[0]) else {break}
                try file.close();record(["service":"close"])
                retiredFiles.insert(a[0])
                return 0
            case 0x4a3dc0:
                // Native C-locale _mbsicmp for the conveyor's ASCII image name.
                // The checked original boundary returns signed unit order.
                guard a.count == 2,let left = text(a[0]),let right = text(a[1]),
                      left.utf8.allSatisfy({$0 < 128}),right.utf8.allSatisfy({$0 < 128}) else {break}
                let foldedLeft = left.lowercased(),foldedRight = right.lowercased()
                transportCounts["ascii-case-compare",default:0] += 1
                return foldedLeft == foldedRight ? 0:foldedLeft < foldedRight ? .max:1
            case 0x4a3cf0:
                guard a.count == 2,let left = text(a[0])?.lowercased(),let right = text(a[1])?.lowercased() else {break}
                return left == right ? 0:left < right ? .max:1
            default:
                if let result = dependency?(q) {return result}
            }
        } catch {return fail(q.function)}
        return fail(q.function)
    }
    /// The owned allocation containing `token`, if any.
    func owningAllocation(_ token:UInt32)->(token:UInt32,bytes:UInt32)? {
        if owns(token), let size = allocationSizes[token] {return (token,size)}
        return allocationSizes.first{owns($0.key) && $0.key < token && UInt64(token) < UInt64($0.key)+UInt64($0.value)}.map{($0.key,$0.value)}
    }
    /// Native zlib for the original's statically linked uncompress 0x4d5fe0,
    /// bounded by the owned source buffer (Tests/NativeLevelOne/native_join.py).
    private func uncompress(_ q:ClawCall)->UInt32 {
        let a = withUnsafeBytes(of:q.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(min(q.argumentCount,32))))}
        guard q.argumentCount == 4,q.receiver == 0,q.sourceContext == nil,q.compilerContext == nil,
              q.sourceTransferVersion == 0,q.x87ArgumentCount == 0,let capacity = word(a[1]),capacity > 0,
              capacity <= 0x2000000,let block = owningAllocation(a[2]) else {return fail(q.function)}
        let available = min(a[3],block.token+block.bytes-a[2])
        guard let source = heap.lookupBytes(a[2],count:max(available,1)),
              let destination = heap.lookupBytes(a[0],count:capacity) else {return fail(q.function)}
        if let payload = localTestPayload,let expected = localTestSourceSHA,
           SHA256.hash(data:Data(bytes:source,count:Int(available))).map({String(format:"%02x",$0)}).joined() == expected {
            guard payload.count <= capacity else {return fail(q.function)}
            payload.copyBytes(to:destination,count:payload.count)
            _ = putWord(a[1],UInt32(payload.count))
            localTestPayload = nil;localTestSourceSHA = nil
            localTestWorldEvidence["substitutions"] = 1
            return 0
        }
        var written:UInt32 = 0
        let result = claw_level_uncompress(destination,capacity,source,available,&written)
        if result != 0xfffffffd {_ = putWord(a[1],written)}
        record(["service":"native zlib uncompress","capacity":capacity,"advertised":a[3],"available":available,"result":result])
        return result
    }
    func close() {
        guard !closed else {return}
        unmountPackage()
        if archive != 0,fault == 0,owns(archive) {_ = invoke(0x4b7250,archive)}
        if archive != 0,let pointer = heap.lookupBytes(archive,count:72) {
            destroyedArchive = Data(bytes:pointer,count:72)
        }
        cleanupTokens = allocations.subtracting(retiredFiles).subtracting(files.keys).subtracting([archive]).sorted()
        cleanupRemaining = cleanupTokens.count
        cleanupDetails = cleanupTokens.map { ["token":String($0,radix:16),"bytes":allocationSizes[$0] ?? 0,"origin":allocationOrigins[$0] ?? []] }
        for file in files.values {try? file.close()};files.removeAll()
        for token in allocations where owns(token) {heap.free(token)};allocations.removeAll()
        allocationSizes.removeAll()
        allocationIdentities.removeAll()
        allocationOrigins.removeAll()
        for (token, span) in scratchIdentities where heap.allocationIdentity(at: token, count: span.count) === span.identity {heap.free(token)}
        scratch.removeAll();scratchIdentities.removeAll()
        archive = 0;closed = true
    }
}

// Synchronous adapter: all raw callbacks retain the menu resource host's
// stack, missing-service checks and sticky fault instead of opening a new host.
final class ClawNativeMenuRawDisplayHost:ClawNativeRawDisplayHost {
    unowned let resources:ClawNativeMenuResources
    init(_ resources:ClawNativeMenuResources) {self.resources = resources}
    var heap:ClawTokenHeap {resources.heap}
    var fault:ClawNativeCanonicalHost.Fault? {
        resources.fault == 0 ? nil:.init(code:resources.fault,address:resources.faultAddress,diagnostic:.nativeFault)
    }
    func bytes(_ token:UInt32,count:UInt32)->UnsafeMutablePointer<UInt8>? {
        guard resources.fault == 0,let pointer = heap.lookupBytes(token,count:count) else {resources.fail(token);return nil}
        return pointer
    }
    @discardableResult func rawReject(_ code:UInt32,at:UInt32)->ClawNativeCanonicalHost.Fault {resources.fail(at);return fault!}
    func callNativeDependency(_ call:ClawCall)->UInt32? {
        let result = resources.service(call)
        return resources.fault == 0 ? result:nil
    }
}

/// Failure-trace ring for ClawNativeMenuResources. Entries keep raw words and
/// are formatted only when a failure trace is read, so the per-call cost is a
/// slot store instead of string formatting and an O(n) removeFirst.
struct ClawTraceRing {
    enum Entry {
        case invoke(UInt32,UInt32,[UInt32])
        case service(UInt32,UInt32,[UInt32])
        case ret(UInt32,UInt32)
        case text(String)
        var line:String {
            switch self {
            case let .invoke(f,r,a): return "\(String(f,radix:16)) self=\(String(r,radix:16)) args=\(a.map{String($0,radix:16)})"
            case let .service(f,r,a): return "service \(String(f,radix:16)) self=\(String(r,radix:16)) args=\(a.map{String($0,radix:16)})"
            case let .ret(f,v): return "ret \(String(f,radix:16)) = \(String(v,radix:16))"
            case let .text(t): return t
            }
        }
    }
    private var slots:[Entry] = []
    private var next = 0
    let capacity:Int
    init(capacity:Int) {self.capacity = max(capacity,1);slots.reserveCapacity(self.capacity)}
    mutating func append(_ entry:Entry) {
        if slots.count < capacity {slots.append(entry)} else {slots[next] = entry;next = (next+1) % capacity}
    }
    mutating func append(text:String) {append(.text(text))}
    /// Oldest first, the same lines the eager trace kept.
    func lines(last:Int? = nil)->[String] {
        let ordered = slots.count < capacity ? slots:Array(slots[next...]+slots[..<next])
        return ordered.suffix(last ?? ordered.count).map{$0.line}
    }
}
