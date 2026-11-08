import Foundation
import zlib

// Whole original4cb200 and owned lifecycle over native raw-token storage.
// Resource enumeration and the caller's object-population profile are services.
final class ClawNativeWorld {
    struct RawRecord {
        let token: UInt32, bytes: Data, words: [UInt32]
        var byteCount: UInt32 { UInt32(bytes.count) }
    }
    struct GridBatch {
        let planeToken: UInt32, firstRecordToken: UInt32, count: UInt32
        // Owned copies, taken before the temporary decoded WWD is freed.
        let records: [RawRecord]
    }
    struct Hooks {
        var imageRoot: (String) throws -> UInt32?
        // Must execute real4d1620 and its ordered4d17e0 callbacks. The caller
        // declares unsupported objects through populationPolicy, not a fake grid.
        var gridSetup: (GridBatch) -> UInt32?
        var service: (ClawSceneActorCall) -> UInt32?
    }
    let heap: ClawTokenHeap
    let worldToken: UInt32, parentToken: UInt32, populationPolicy: String
    private let backing: ClawSceneActorHost
    private let hooks: Hooks
    private let context = UnsafeMutablePointer<ClawWorldFileContext>.allocate(capacity: 1)
    private let arrays = UnsafeMutablePointer<ClawCArrayContext>.allocate(capacity: 1)
    private var allocations: [UInt32: UInt32] = [:]
    private var constructed: Bool
    private(set) var fault: UInt32 = 0
    private(set) var failure: String?
    private(set) var unresolvedServices: Set<UInt32> = []
    private(set) var gridBatches: [GridBatch] = []
    private(set) var events: [UInt32] = []
    private(set) var allocationEvents: [(UInt32,UInt32)] = [], freedTokens: [UInt32] = []
    private(set) var codecCalls: UInt64 = 0
    private(set) var codecInputLengths: [(advertised: UInt32, actual: UInt32)] = []
    var planeTokens: [UInt32] { arrayTokens(offset: 0x34) }
    var descriptionTokens: [UInt32] { arrayTokens(offset: 0x48) }
    var mainIndex: UInt32? {
        guard let world = heap.lookup(worldToken,words:56), world[23] != 0 else { return nil }
        return world[24]
    }
    var mainPlaneToken: UInt32? { heap.lookup(worldToken,words:56).flatMap { $0[23] == 0 ? nil : $0[23] } }
    var flags: UInt32? { heap.lookup(worldToken,words:56)?[2] }

    init(heap: ClawTokenHeap, worldToken: UInt32, parentToken: UInt32,
         host: ClawSceneActorHost, populationPolicy: String, alreadyConstructed: Bool = false, hooks: Hooks) {
        precondition(!populationPolicy.isEmpty)
        precondition(host.lookup != nil && host.allocate != nil && host.free != nil, "World host requires physical lookup/allocation/free services")
        self.heap = heap; self.worldToken = worldToken; self.parentToken = parentToken
        backing = host; self.populationPolicy = populationPolicy; self.hooks = hooks
        constructed = alreadyConstructed
        context.initialize(to: ClawWorldFileContext()); arrays.initialize(to: ClawCArrayContext())
        claw_carray_defaults(arrays); arrays.pointee.composeAllocator = 0
        context.pointee.arrays = arrays; context.pointee.composeSpatial = 0; context.pointee.scene = runtimeHost
    }
    deinit {
        // The caller explicitly orders cleanup before releasing scene/resource
        // services. Swift deinit must not invoke callbacks on a dying graph.
        context.deinitialize(count:1); context.deallocate()
        arrays.deinitialize(count:1); arrays.deallocate()
    }
    @discardableResult func construct(id: UInt32 = 0, flags: UInt32 = 0) -> Bool {
        guard !constructed, heap.lookup(worldToken,words:56) != nil else { diagnose("World constructor requires fresh56-word storage"); return false }
        let result = entry(0x4cace0, arguments:[parentToken,id,flags])
        constructed = fault == 0 && result == worldToken
        return constructed
    }
    @discardableResult func load(compressedWWD data: Data, viewportWidth: UInt32 = 640, viewportHeight: UInt32 = 480) -> Bool {
        guard constructed else { diagnose("World constructor has not run"); return false }
        fault = 0; failure = nil; context.pointee.fault = 0; arrays.pointee.fault = 0
        gridBatches.removeAll(keepingCapacity:true); events.removeAll(keepingCapacity:true)
        // The original requires188 header words even on its size-validation
        // path. Extending a truncated file with invented bytes would be false.
        guard data.count >= 752, data.count <= Int(UInt32.max)-3 else { diagnose("WWD source does not contain the original header span"); return false }
        var viewport = ClawSpatialGridArguments(); viewport.count = 2
        viewport.words.0 = viewportWidth; viewport.words.1 = viewportHeight
        var viewportFault: UInt32 = 0, ignored: UInt32 = 0
        _ = claw_spatial_grid_entry(0x4cb040,worldToken,viewport,runtimeHost,&viewportFault,&ignored)
        if viewportFault != 0 { fault = viewportFault; return false }
        let input = allocate(bytes:UInt32(data.count))
        guard input != 0 else { diagnose("WWD source allocation failed"); return false }
        defer { release(input) }
        guard let raw = heap.lookup(input,words:UInt32((data.count+3)/4)) else { diagnose("WWD allocation has no readable source span"); return false }
        data.withUnsafeBytes { UnsafeMutableRawPointer(raw).copyMemory(from:$0.baseAddress!,byteCount:$0.count) }
        let result = entry(0x4cb200,arguments:[input])
        return fault == 0 && result == 1
    }
    @discardableResult func cleanup(resetViewport: Bool = false) -> Bool {
        guard constructed else { return true }
        _ = entry(resetViewport ? 0x4cb180 : 0x4cb5f0)
        return fault == 0
    }
    @discardableResult func destroy(deleteWorld: Bool = false) -> Bool {
        guard constructed else { return true }
        _ = entry(deleteWorld ? 0x4cdd10 : 0x4cdd30,arguments:deleteWorld ? [1] : [])
        if fault == 0 { constructed = false }
        return fault == 0
    }
    private func arrayTokens(offset: UInt32) -> [UInt32] {
        guard let a = heap.lookup(worldToken &+ offset,words:5), a[2] != 0,
              a[2] < 1000000, let values = heap.lookup(a[1],words:a[2]) else { return [] }
        return Array(UnsafeBufferPointer(start:values,count:Int(a[2])))
    }
    private func diagnose(_ message: String, _ code: UInt32 = 1) {
        fault = code; context.pointee.fault = code; failure = message
    }
    private func entry(_ function: UInt32,arguments: [UInt32] = []) -> UInt32 {
        var args = ClawWorldFileArguments(), result: UInt32 = 0
        args.count = UInt32(arguments.count)
        withUnsafeMutableBytes(of:&args.words) { raw in
            for (index,value) in arguments.enumerated() { raw.storeBytes(of:value,toByteOffset:index*4,as:UInt32.self) }
        }
        context.pointee.fault = 0; arrays.pointee.fault = 0; fault = 0
        let completed = heap.withStableFreedStorage {
            claw_world_file_entry(function,worldToken,args,context,{ context,call,raw in
                guard let context,let call,let raw else { return 0 }
                return Unmanaged<ClawNativeWorld>.fromOpaque(raw).takeUnretainedValue().dependency(context,call.pointee)
            },Unmanaged.passUnretained(self).toOpaque(),&result)
        }
        fault = max(fault,context.pointee.fault)
        if completed == 0 && fault == 0 { diagnose("Unsupported world entry",2) }
        return result
    }
    private func byteSpan(_ token: UInt32,count: UInt32) -> UnsafeMutablePointer<UInt8>? {
        let offset = token & 3
        guard UInt64(count)+UInt64(offset)+3 <= UInt64(UInt32.max),
              let words = heap.lookup(token & ~3,words:(count+offset+3)/4) else { return nil }
        return UnsafeMutableRawPointer(words).assumingMemoryBound(to:UInt8.self).advanced(by:Int(offset))
    }
    private func containing(_ token: UInt32) -> (base: UInt32,remaining: UInt32)? {
        for (base,size) in allocations where token >= base && UInt64(token) < UInt64(base)+UInt64(size) {
            return (base,size-(token-base))
        }
        return nil
    }
    private func copyRecords(_ start: UInt32,count: UInt32) -> [RawRecord]? {
        if Int32(bitPattern:count) < 1 { return [] }
        guard count < 1000000 else { diagnose("Unbounded record count",2); return nil }
        var records: [RawRecord] = [], cursor = start
        for _ in 0..<count {
            guard let source = byteSpan(cursor,count:284), let block = containing(cursor) else { diagnose("Record header outside live WWD allocation"); return nil }
            let header = Data(bytes:source,count:284)
            let words = (0..<71).map { index in header.withUnsafeBytes { UInt32(littleEndian:$0.loadUnaligned(fromByteOffset:index*4,as:UInt32.self)) } }
            let length = UInt64(284)+words[1...4].reduce(UInt64(0)) { $0+UInt64($1) }
            guard length <= UInt64(block.remaining), length <= UInt64(UInt32.max),
                  let bytes = byteSpan(cursor,count:UInt32(length)) else { diagnose("Record strings outside live WWD allocation"); return nil }
            records.append(RawRecord(token:cursor,bytes:Data(bytes:bytes,count:Int(length)),words:words))
            cursor &+= UInt32(length)
        }
        return records
    }
    private func dependency(_ ctx: UnsafeMutablePointer<ClawWorldFileContext>, _ call: ClawWorldFileCall) -> UInt32 {
        events.append(call.function)
        switch call.function {
        case 0x4d5fe0:
            guard let size = call.size, let sourceBlock = containing(call.arguments.2),
                  let source = byteSpan(call.arguments.2,count:sourceBlock.remaining),
                  let target = byteSpan(call.arguments.0,count:size.pointee) else { diagnose("Codec span outside owned buffers"); return UInt32(bitPattern:Int32(Z_BUF_ERROR)) }
            codecInputLengths.append((call.arguments.3,sourceBlock.remaining))
            var length = uLongf(size.pointee)
            let result = uncompress(target,&length,source,uLong(sourceBlock.remaining))
            size.pointee = UInt32(length); codecCalls &+= 1
            return UInt32(bitPattern:Int32(result))
        case 0x4f6286:
            guard let name = call.name else { diagnose("Missing source plane resource name"); return 0 }
            do { return try hooks.imageRoot(String(cString:name)) ?? 0 }
            catch { diagnose(String(describing:error)); return 0 }
        case 0x4d1620:
            guard let records = copyRecords(call.arguments.0,count:call.arguments.1) else { return 0 }
            let batch = GridBatch(planeToken:call.receiver,firstRecordToken:call.arguments.0,count:call.arguments.1,records:records)
            gridBatches.append(batch)
            guard let result = hooks.gridSetup(batch) else { unresolvedServices.insert(call.function); diagnose("Grid setup service unavailable"); return 0 }
            return result
        default:
            var event = ClawSceneActorCall(); event.function = call.function; event.receiver = call.receiver
            event.arguments = call.arguments; event.argumentCount = call.argumentCount
            if let result = hooks.service(event) { return result }
            unresolvedServices.insert(call.function); diagnose("World service \(String(call.function,radix:16)) unavailable"); return 0
        }
    }
    private func allocate(bytes: UInt32) -> UInt32 {
        let token = backing.allocate?(backing.context,bytes) ?? 0
        if token != 0 { allocations[token] = bytes }
        allocationEvents.append((token,bytes)); return token
    }
    private func release(_ token: UInt32) {
        allocations.removeValue(forKey:token); freedTokens.append(token)
        backing.free?(backing.context,token)
    }
    private var runtimeHost: ClawSceneActorHost {
        ClawSceneActorHost(context:Unmanaged.passUnretained(self).toOpaque(),lookup:{ raw,token,words in
            guard let raw else { return nil }; let owner = Unmanaged<ClawNativeWorld>.fromOpaque(raw).takeUnretainedValue()
            return owner.backing.lookup?(owner.backing.context,token,words)
        },allocate:{ raw,bytes in
            guard let raw else { return 0 }; return Unmanaged<ClawNativeWorld>.fromOpaque(raw).takeUnretainedValue().allocate(bytes:bytes)
        },free:{ raw,token in
            guard let raw else { return }; Unmanaged<ClawNativeWorld>.fromOpaque(raw).takeUnretainedValue().release(token)
        },call:{ raw,call in
            guard let raw else { return 0 }; let owner = Unmanaged<ClawNativeWorld>.fromOpaque(raw).takeUnretainedValue()
            if let result = owner.hooks.service(call) { return result }
            owner.unresolvedServices.insert(call.function); owner.diagnose("Spatial/lifecycle service unavailable"); return 0
        },readClock:{ raw in
            guard let raw else { return 0 }; let owner = Unmanaged<ClawNativeWorld>.fromOpaque(raw).takeUnretainedValue()
            return owner.backing.readClock?(owner.backing.context) ?? 0
        })
    }
}
