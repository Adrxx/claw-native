import Foundation
import Darwin

// Read-only physical FILE/allocator transport for the recovered REZ graph.
// The source parser, insertion, namespace and cached payload bodies own logic.
final class ClawNativeResourceArchive {
    enum Failure: Error {case source(UInt32, UInt32), transport(String)}
    enum Lifecycle {case uninitialized, constructed, openAttempted, closed}
    let heap: ClawTokenHeap
    let controller: UInt32
    let ownsController: Bool
    private let header: UInt32
    private let borrowedBytes: ((UInt32, UInt32) -> UnsafeMutablePointer<UInt8>?)?
    private var transportTokens: Set<UInt32> = []
    private(set) var sourceAllocations: [UInt32: UInt32] = [:]
    private var spanLengths: [UInt32: UInt32] = [:]
    private var spanBases: [UInt32] = []
    // Custom archives stand in for the original mapped REZ view. Retain a
    // bounded, zero-filled final page without changing any resource length.
    var mappedPayloadPages = false
    private var readingPayload = false
    private var file: UnsafeMutablePointer<FILE>?
    private let fileToken: UInt32 = 0x6e130000
    private(set) var calls: [UInt32: UInt64] = [:]
    private(set) var unresolved: Set<UInt32> = []
    private(set) var fault: UInt32 = 0
    private(set) var fileReadBytes: UInt64 = 0
    private(set) var lifecycle: Lifecycle = .uninitialized
    private(set) var operationCalls: [UInt32: UInt64] = [:]
    private(set) var fileOpenCount: UInt64 = 0
    private(set) var fileCloseCount: UInt64 = 0
    var closed: Bool {lifecycle == .closed}
    var hasOpenFile: Bool {file != nil}
    var transportAllocationTokens: Set<UInt32> {transportTokens}

    convenience init(heap: ClawTokenHeap, url: URL) throws {
        let controller = heap.allocate(bytes: 72)
        guard controller != 0 else {throw Failure.transport("Archive controller allocation")}
        try self.init(heap:heap,controller:controller,ownsController:true,borrowedBytes:nil)
        guard try operation(0x4b7210) == controller else {throw Failure.source(0x4b7210,fault)}
        let path = string(url.path); defer {heap.free(path)}
        guard try operation(0x4b72e0,args:[path,1,0]) == 1, file != nil else {
            shutdown();throw Failure.source(0x4b72e0,fault)
        }
    }
    // The caller retains this unconstructed 72-byte allocation until shutdown
    // and host release. Adoption performs no source construction or FILE open.
    // Optional bytes must enforce exact extents of caller-owned CString spans.
    convenience init(heap: ClawTokenHeap, borrowingController controller: UInt32,
                     borrowedBytes: ((UInt32, UInt32) -> UnsafeMutablePointer<UInt8>?)? = nil) throws {
        try self.init(heap:heap,controller:controller,ownsController:false,borrowedBytes:borrowedBytes)
    }
    private init(heap: ClawTokenHeap, controller: UInt32, ownsController: Bool,
                 borrowedBytes: ((UInt32, UInt32) -> UnsafeMutablePointer<UInt8>?)?) throws {
        self.heap = heap
        self.controller = controller;self.ownsController = ownsController;self.borrowedBytes = borrowedBytes
        header = heap.allocate(bytes: 168)
        if ownsController {transportTokens.insert(controller)}
        if header != 0 {transportTokens.insert(header)}
        guard controller != 0, heap.lookupBytes(controller,count:72) != nil, header != 0 else {
            throw Failure.transport("Archive transport allocation")
        }
        trackSpan(controller,bytes:72);trackSpan(header,bytes:168)
        // Exact original immutable method metadata and C locale flag. No tree,
        // success return, archive resource or enumeration is supplied here.
        for (t,v): (UInt32,[UInt32]) in [
            (0x513568,[0x4b8050]), (0x51356c,[0x4b7f40]),
            (0x513570,[0x4b80c0]), (0x513574,[0x4b8130]),
            (0x513578,[0x4b7a90,0x4b7aa0,0x42a680,0]),
            (0x534938,[0]), (0x540e88,[0])
        ] {
            if let p = heap.lookup(t, words: UInt32(v.count)) {
                guard Array(UnsafeBufferPointer(start:p,count:v.count)) == v else {throw Failure.transport("Archive metadata conflict")}
            } else {v.withUnsafeBufferPointer {heap.store(token:t,words:v.count).update(from:$0.baseAddress!,count:v.count)}}
        }
    }
    deinit {
        shutdown()
        if let file {fclose(file);self.file = nil;fileCloseCount &+= 1}
        for t in transportTokens {heap.free(t)}
    }
    private var opaque: UnsafeMutableRawPointer {Unmanaged.passUnretained(self).toOpaque()}
    private var host: ClawSceneActorHost {
        ClawSceneActorHost(context:opaque,lookup:{u,t,n in
            guard let u else {return nil};return Unmanaged<ClawNativeResourceArchive>.fromOpaque(u).takeUnretainedValue().heap.lookup(t,words:n)
        },allocate:nil,free:nil,call:nil,readClock:nil)
    }
    private var table: ClawResourceTableConstructionContext {
        var c = ClawResourceTableConstructionContext();c.scene = host
        c.maximumOperations = 10000000;c.byteContext = opaque
        c.bytes = {u,t,n in
            guard let u else {return nil};return Unmanaged<ClawNativeResourceArchive>.fromOpaque(u).takeUnretainedValue().bytes(t,count:n)
        };return c
    }
    private func bytes(_ t: UInt32, count n: UInt32) -> UnsafeMutablePointer<UInt8>? {
        // Byte transport checks exact malloc extent; aligned legacy word views
        // retain only their declared final containing-word padding.
        let end = UInt64(t)+UInt64(n)
        var low = 0, high = spanBases.count
        while low < high {let mid = low+(high-low)/2;if spanBases[mid] <= t {low = mid+1}else {high = mid}}
        let base = low > 0 ? spanBases[low-1] : 0
        let own = low > 0 && end <= UInt64(base)+UInt64(spanLengths[base] ?? 0)
        let scratch = t >= header && end <= UInt64(header)+168
        let literal = t >= 0x534938 && end <= 0x53493c
        guard own || scratch || literal else {return borrowedBytes?(t,n)}
        let words = (UInt64(n)+UInt64(t&3)+3)/4
        guard let p = heap.lookup(t & ~3,words:UInt32(words)) else {return nil}
        return UnsafeMutableRawPointer(p).assumingMemoryBound(to:UInt8.self).advanced(by:Int(t&3))
    }
    private func trackSpan(_ token: UInt32, bytes: UInt32) {
        guard token != 0 else {return}
        if spanLengths[token] == nil {
            var low = 0, high = spanBases.count
            while low < high {let mid = low+(high-low)/2;if spanBases[mid] < token {low = mid+1}else {high = mid}}
            spanBases.insert(token,at:low)
        }
        spanLengths[token] = bytes
    }
    func string(_ s: String) -> UInt32 {
        let data = Array(s.utf8)+[0];let t = heap.allocate(bytes:UInt32(data.count));trackSpan(t,bytes:UInt32(data.count))
        if let p = heap.lookup(t,words:UInt32((data.count+3)/4)) {
            data.withUnsafeBytes {UnsafeMutableRawPointer(p).copyMemory(from:$0.baseAddress!,byteCount:$0.count)}
        };return t
    }
    func name(_ t: UInt32) -> String {
        var data: [UInt8] = [], at = t
        while data.count < 4096, let p = heap.lookup(at & ~3,words:1) {
            let b = UnsafeRawPointer(p).assumingMemoryBound(to:UInt8.self)[Int(at&3)]
            if b == 0 {return String(decoding:data,as:UTF8.self)}
            data.append(b);at &+= 1
        };return ""
    }
    private static let dependency: ClawResourceTableConstructionDependency = {c,q,u in
        guard let c, let q, let u else {return 0}
        return Unmanaged<ClawNativeResourceArchive>.fromOpaque(u).takeUnretainedValue().service(c,q.pointee)
    }
    private func service(_ c: UnsafeMutablePointer<ClawResourceTableConstructionContext>, _ q: ClawResourceTableConstructionCall) -> UInt32 {
        calls[q.function,default:0] &+= 1
        let a = withUnsafeBytes(of:q.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(q.argumentCount)))}
        switch q.function {
        case 0x4f63ec:
            guard a.count == 1 else {break}
            let size = mappedPayloadPages && readingPayload ? (UInt64(a[0])+4095) & ~UInt64(4095):UInt64(a[0])
            guard size <= UInt32.max else {break}
            let t = heap.allocate(bytes:UInt32(size))
            if t != 0 {
                sourceAllocations[t] = UInt32(size);trackSpan(t,bytes:UInt32(size))
                if mappedPayloadPages && readingPayload,let p = heap.lookupBytes(t,count:UInt32(size)) {
                    p.update(repeating:0,count:Int(size))
                }
            }
            return t
        case 0x4f6428:
            guard a.count == 1, a[0] == 0 || sourceAllocations.removeValue(forKey:a[0]) != nil else {break}
            heap.free(a[0]);return 0
        case 0x4f1d90:
            guard a.count == 2, a[1] == 0x532298, file == nil else {break}
            file = fopen(name(a[0]),"rb");if file != nil {fileOpenCount &+= 1};return file == nil ? 0 : fileToken
        case 0x4a7840:
            guard a.count == 3, a[0] == fileToken, let file else {return .max}
            return UInt32(bitPattern:Int32(fseek(file,Int(a[1]),Int32(a[2]))))
        case 0x4a7260:
            guard a.count == 4, a[3] == fileToken, let file else {return 0}
            let count = UInt64(a[1])*UInt64(a[2]);guard count <= UInt64(UInt32.max) else {break}
            let destination: UnsafeMutableRawPointer?
            if q.localMask == 1, q.bufferCount == 1, q.bufferBytes.0 >= count {destination = q.buffers.0}
            else {destination = bytes(a[0],count:UInt32(count)).map(UnsafeMutableRawPointer.init)}
            guard let destination else {break}
            let n = fread(destination,Int(a[1]),Int(a[2]),file)
            fileReadBytes &+= UInt64(n)*UInt64(a[1]);return UInt32(n)
        case 0x4a7ae0:
            guard a.count == 1, a[0] == fileToken else {break}
            // Source leaves a stale FILE identity and elects close twice. Record
            // both calls; avoid a host libc use-after-free on the second call.
            guard let file else {return .max};self.file = nil;fileCloseCount &+= 1
            return UInt32(bitPattern:Int32(fclose(file)))
        case 0x42a680: return 0 //Frozen common XOR EAX,EAX / RET retry leaf.
        default: break
        }
        unresolved.insert(q.function);c.pointee.fault = 1;return 0
    }
    private func archive(_ f: UInt32, args: [UInt32] = []) -> UInt32 {
        operationCalls[f,default:0] &+= 1
        var c = table, out: UInt32 = 0
        let done = withUnsafeMutablePointer(to:&c) {p -> UInt32 in
            var a = ClawResourceArchiveLoadingContext();a.table = p;a.headerToken = header;a.maximumOperations = 20000000
            return args.withUnsafeBufferPointer {buffer in
                heap.withStableFreedStorage {claw_resource_archive_loading_entry(f,controller,buffer.baseAddress,UInt32(args.count),&a,Self.dependency,opaque,&out)}
            }
        };fault = c.fault;if done != 1, fault == 0 {fault = 1};return out
    }
    // Narrow original-address bootstrap boundary. Returns the source EAX;
    // unsupported calls, lifecycle misuse and native faults throw separately.
    // An open return of 1 does not establish successful recursive parsing.
    @discardableResult func operation(_ function: UInt32, args: [UInt32] = []) throws -> UInt32 {
        switch function {
        case 0x4b7210:
            guard lifecycle == .uninitialized, args.isEmpty else {throw Failure.transport("Archive constructor lifecycle")}
        case 0x4b72e0:
            guard lifecycle == .constructed, args.count == 3, args[1] == 1, args[2] == 0 else {
                throw Failure.transport("Archive read-only open lifecycle")
            }
            lifecycle = .openAttempted
        case 0x4b7250:
            guard lifecycle == .constructed || lifecycle == .openAttempted, args.isEmpty else {
                throw Failure.transport("Archive destructor lifecycle")
            }
            // Do not replay a partially executed destructor after a host fault.
            lifecycle = .closed
        default: throw Failure.transport("Unsupported archive bootstrap operation")
        }
        let result = archive(function,args:args)
        guard fault == 0 else {throw Failure.source(function,fault)}
        if function == 0x4b7210 {lifecycle = .constructed}
        return result
    }
    func namespace(_ f: UInt32, receiver: UInt32, args: [UInt32] = []) -> UInt32 {
        guard lifecycle == .openAttempted else {return 0}
        var c = ClawResourceNamespaceContext();c.scene = host;c.maximumOperations = 1000000
        var out: UInt32 = 0
        let done = args.withUnsafeBufferPointer {claw_resource_namespace_entry(f,receiver,$0.baseAddress,UInt32(args.count),&c,nil,nil,&out)}
        fault = c.fault;if done != 1, fault == 0 {fault = 1};return out
    }
    func lookupFolder(_ path: String) -> UInt32 {
        if path.isEmpty {return namespace(0x4b7540,receiver:controller)}
        let t = string(path);defer {heap.free(t)}
        return namespace(0x4b7f20,receiver:controller,args:[t])
    }
    func lookupChild(folder: UInt32, name: String) -> UInt32 {
        let t = string(name);defer {heap.free(t)}
        return namespace(0x4b68c0,receiver:folder,args:[t])
    }
    func lookupResource(folder: UInt32, name: String, tag: UInt32) -> UInt32 {
        let t = string(name);defer {heap.free(t)}
        return namespace(0x4b67f0,receiver:folder,args:[t,tag])
    }
    @discardableResult func resource(_ f: UInt32, token: UInt32) -> UInt32 {
        guard lifecycle == .openAttempted else {return 0}
        let priorRead = readingPayload;readingPayload = f == 0x4b61c0
        defer {readingPayload = priorRead}
        var c = ClawResourceDataContext();c.scene = host;c.maximumOperations = 1000000
        var out: UInt32 = 0
        let done = heap.withStableFreedStorage {
            claw_resource_data_entry(f,token,nil,0,&c,{c,q,u in
                guard let c, let q, let u else {return 0}
                let h = Unmanaged<ClawNativeResourceArchive>.fromOpaque(u).takeUnretainedValue()
                var t = h.table;var call = ClawResourceTableConstructionCall()
                call.function = q.pointee.function;call.receiver = q.pointee.receiver
                call.argumentCount = q.pointee.argumentCount;call.arguments = q.pointee.arguments
                let v = h.service(&t,call);if t.fault != 0 {c.pointee.fault = t.fault};return v
            },opaque,&out)
        };fault = c.fault;if done != 1, fault == 0 {fault = 1};return out
    }
    func payload(_ token: UInt32) -> Data? {
        let p = resource(0x4b61c0,token:token)
        guard fault == 0, let r = heap.lookup(token,words:24) else {return nil}
        if r[5] == 0 {return Data()}
        guard p != 0, let bytes = bytes(p,count:r[5]) else {return nil}
        return Data(bytes:bytes,count:Int(r[5]))
    }
    func shutdown() {
        guard lifecycle == .constructed || lifecycle == .openAttempted else {return}
        // Preserve source fault diagnostics; deinit cannot report thrown errors.
        _ = try? operation(0x4b7250)
    }
}
