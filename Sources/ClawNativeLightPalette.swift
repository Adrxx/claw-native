import Foundation

//Source palette manager/CLT boot over native storage. Filesystem, CMemFile and
//physical palette interfaces remain explicit transports. Mode2 raster composes.
final class ClawNativeLightPalette {
    let heap:ClawTokenHeap,ownerToken:UInt32,applicationToken:UInt32,managerToken:UInt32
    private let root:URL
    private let level:UInt32
    private let context = UnsafeMutablePointer<ClawLightPaletteContext>.allocate(capacity:1)
    private let images:UnsafeMutablePointer<ClawGameImageGlobals>
    private var resources:[String:UInt32] = [:],resourceData:[UInt32:UInt32] = [:]
    private var auxiliary:Set<UInt32> = []
    private var closed = false
    private(set) var fault:UInt32 = 0,unresolved:Set<UInt32> = []
    private(set) var serviceCounts:[UInt32:UInt64] = [:]
    var tables:[UInt32] { guard let o = heap.lookup(ownerToken,words:478) else { return [] };return [o[0x768/4],o[0x76c/4],o[0x770/4]] }
    init(scene:ClawNativeScene,root:URL) throws {
        heap = scene.heap;ownerToken = scene.ownerIdentity;self.root = root;level = scene.objectResources!.level
        applicationToken = heap.lookup(ownerToken,words:2)![1]
        images = scene.rendering!.sourceImageGlobals
        managerToken = heap.allocate(bytes:24)
        context.initialize(to:ClawLightPaletteContext());claw_light_palette_defaults(context)
        context.pointee.temporaryFileToken = heap.allocate(bytes:40);auxiliary.insert(context.pointee.temporaryFileToken)
        context.pointee.scene = host
        let fileVT:[UInt32] = [0x503828, 0x4ff629, 0x4c9e30, 0x4c96b0, 0x4c9e30, 0x4ff71f, 0x4fc035, 0x4fc0b7, 0x4fc139, 0x4a1628, 0x4f7448, 0x4ff8a0, 0x4ff822, 0x4ff77c, 0x4f774d, 0x4ff79f]
        if heap.lookup(0x5142f4,words:16) == nil { let p = heap.store(token:0x5142f4,words:16);fileVT.withUnsafeBufferPointer{p.update(from:$0.baseAddress!,count:16)} }
        if heap.lookup(0x5430b0,words:5) == nil { _ = heap.store(token:0x5430b0,words:5) }
        guard let resources = scene.paletteResources,resources.fault == 0,resources.wrapperToken != 0,
            heap.lookup(ownerToken+0x360,words:256) != nil,let app = heap.lookup(applicationToken,words:77) else { throw AssetError.invalid("Source PAL/GetEntries graph must precede light tables") }
        _ = entry(0x4c61d0,receiver:managerToken);_ = entry(0x4c6260,receiver:managerToken)
        app[0x58/4] = managerToken
        let owner = heap.lookup(ownerToken,words:478)!
        if owner[0x1c/4] == 0 { owner[0x1c/4] = heap.allocate(bytes:4);auxiliary.insert(owner[0x1c/4]) }
        guard entry(0x46e160,receiver:ownerToken) == 1 && fault == 0 else { throw AssetError.invalid("Original light palette startup fault \(fault): \(unresolved)") }
        syncImageGlobals()
    }
    deinit { shutdown();context.deinitialize(count:1);context.deallocate() }
    private var host:ClawSceneActorHost {
        ClawSceneActorHost(context:Unmanaged.passUnretained(self).toOpaque(),lookup:{u,t,n in
            guard let u else { return nil };return Unmanaged<ClawNativeLightPalette>.fromOpaque(u).takeUnretainedValue().heap.lookup(t,words:n)
        },allocate:nil,free:nil,call:nil,readClock:nil)
    }
    @discardableResult func entry(_ f:UInt32,receiver:UInt32,args:[UInt32] = []) -> UInt32 {
        var result:UInt32 = 0
        let recognized = heap.withStableFreedStorage { args.withUnsafeBufferPointer {
            claw_light_palette_entry(f,receiver,$0.baseAddress,UInt32($0.count),context,nativeLightPaletteDependency,Unmanaged.passUnretained(self).toOpaque(),&result)
        } }
        fault = max(fault,context.pointee.fault);if recognized != 1 { fault = max(fault,1);unresolved.insert(f) };return result
    }
    private func syncImageGlobals() {
        guard let globals = heap.lookup(0x5430b0,words:4) else { fault = 1;return }
        withUnsafeMutableBytes(of:&images.pointee.compressedEffect){$0.copyMemory(from:UnsafeRawBufferPointer(start:globals,count:16))}
    }
    //Source46b7b0's palette-removal portion, followed by manager destruction.
    //This does not claim the remaining full scene/audio/settings teardown.
    func shutdown() {
        guard !closed else { return };closed = true
        if let owner = heap.lookup(ownerToken,words:478),heap.lookup(managerToken,words:6) != nil {
            for offset in [0x768,0x76c,0x770,0x150] where owner[offset/4] != 0 {
                _ = entry(0x4c7510,receiver:managerToken,args:[owner[offset/4]]);owner[offset/4] = 0
            }
            _ = entry(0x4c61f0,receiver:managerToken);heap.free(managerToken)
        }
        if let app = heap.lookup(applicationToken,words:77),app[0x58/4] == managerToken { app[0x58/4] = 0 }
        for t in auxiliary { heap.free(t) };auxiliary.removeAll()
    }
    private func bytes(_ t:UInt32,count:UInt32) -> UnsafeMutableRawPointer? {
        let n = (UInt64(count)+UInt64(t&3)+3)/4
        guard count != 0,n <= UInt64(UInt32.max),let p = heap.lookup(t & ~3,words:UInt32(n)) else { return nil }
        return UnsafeMutableRawPointer(p).advanced(by:Int(t&3))
    }
    fileprivate func service(_ e:ClawLightPaletteCall) -> UInt64 {
        let args = withUnsafeBytes(of:e.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(e.argumentCount)))}
        serviceCounts[e.function,default:0] &+= 1
        do {
            switch e.function {
            case 0x4f63ec:guard args.count == 1 else { break };return UInt64(heap.allocate(bytes:args[0]))
            case 0x4f6428:guard args.count == 1 else { break };heap.free(args[0]);return 0
            case 0x4b7dc0:
                guard args.count == 2,args[1] == 0x434c54,let n = e.name.map({String(cString:$0)}),["PALETTES_LIGHT","PALETTES_AVERAGE"].contains(n) else { break }
                if let r = resources[n] { return UInt64(r) }
                let file = root.appendingPathComponent("LEVEL\(level)/PALETTES/"+(n == "PALETTES_LIGHT" ? "LIGHT" : "AVERAGE")+".CLT")
                guard FileManager.default.fileExists(atPath:file.path) else { return 0 }
                let data = try Data(contentsOf:file),r = heap.allocate(bytes:24),buffer = heap.allocate(bytes:UInt32(data.count))
                guard r != 0,buffer != 0,let dst = bytes(buffer,count:UInt32(data.count)),let metadata = heap.lookup(r,words:6) else { break }
                data.withUnsafeBytes{dst.copyMemory(from:$0.baseAddress!,byteCount:$0.count)}
                metadata[4] = buffer;metadata[5] = UInt32(data.count);resources[n] = r;resourceData[r] = buffer;auxiliary.formUnion([r,buffer]);return UInt64(r)
            case 0x4b61c0:guard let data = resourceData[e.receiver] else { break };return UInt64(data)
            case 0x4b6230:return 0 //The cached native file bytes remain owned by this namespace adapter.
            case 0x4ff5f9,0x4ff645,0x4ff79f,0x4ff682:
                guard e.localMask == 1,e.bufferCount == 1,e.bufferBytes.0 == 40,let file = e.buffers.0 else { break }
                switch e.function {
                case 0x4ff5f9:
                    guard args.count == 1 else { break }
                    let seed:[UInt32] = [0x5142f4,.max,0,0,args[0],0,0,0,0,1]
                    seed.withUnsafeBufferPointer{file.update(from:$0.baseAddress!,count:10)};return 0
                case 0x4ff645:
                    guard args.count == 3 else { break };file[4] = args[2];file[5] = 0;file[6] = args[1];file[7] = args[2] == 0 ? args[1] : 0;file[8] = args[0];file[9] = 0;return 0
                case 0x4ff79f:
                    guard args.count == 2 else { break }
                    let actual = min(args[1],file[7] >= file[5] ? file[7]-file[5] : 0)
                    if actual != 0 {
                        guard let src = bytes(file[8]+file[5],count:actual),let dst = bytes(args[0],count:actual) else { break }
                        dst.copyMemory(from:src,byteCount:Int(actual))
                    }
                    file[5] &+= actual;return UInt64(actual)
                default:for i in 4..<10 { file[i] = 0 };return 0
                }
            default:break
            }
        } catch { fault = 1 }
        unresolved.insert(e.function);fault = max(fault,1);return 0
    }
}
private let nativeLightPaletteDependency:ClawLightPaletteDependency = {cx,e,u in
    guard let cx,let e,let u else { return 0 };let p = Unmanaged<ClawNativeLightPalette>.fromOpaque(u).takeUnretainedValue()
    let value = p.service(e.pointee);if p.fault != 0 { cx.pointee.fault = p.fault };return value
}

extension ClawNativeLightPalette {
    struct SavedState: Codable, Equatable {
        let level: UInt32, owner: UInt32, application: UInt32, manager: UInt32
        let context: [String: Data], resources: [String: UInt32], data: [UInt32: UInt32], auxiliary: Set<UInt32>
        let fault: UInt32, unresolved: Set<UInt32>, calls: [UInt32: UInt64]
    }
    func savedState() throws -> SavedState {
        guard !closed else { throw ClawSnapshotError.invalidState }
        return .init(level: level, owner: ownerToken, application: applicationToken, manager: managerToken,
            context: Self.snapshotFields.capture(context.pointee), resources: resources, data: resourceData, auxiliary: auxiliary,
            fault: fault, unresolved: unresolved, calls: serviceCounts)
    }
    func restoreState(_ saved: SavedState) throws {
        guard !closed, saved.level == level, saved.owner == ownerToken, saved.application == applicationToken, saved.manager == managerToken else { throw ClawSnapshotError.invalidState }
        context.pointee = try Self.snapshotFields.restoring(saved.context, into: context.pointee)
        resources = saved.resources; resourceData = saved.data; auxiliary = saved.auxiliary
        fault = saved.fault; unresolved = saved.unresolved; serviceCounts = saved.calls
        syncImageGlobals()
    }
    private static let snapshotFields = ClawSnapshotFields<ClawLightPaletteContext>(fields: [
        .init("temporaryFileToken", \.temporaryFileToken),
        .init("composeCore", \.composeCore),
        .init("maximumSteps", \.maximumSteps),
        .init("fault", \.fault)
    ])
}
