import Foundation

//Whole source PAL resource/backend/list lifetime. File bytes, CString map and
//physical eight-bit DD palette interfaces are explicit native transports.
final class ClawNativePaletteResources {
    let diagnostics:ClawNativeDiagnostics
    let heap:ClawTokenHeap,ownerToken:UInt32,parentToken:UInt32
    let managerToken:UInt32,backendManagerToken:UInt32
    private let context = UnsafeMutablePointer<ClawPaletteResourceContext>.allocate(capacity:1)
    private let globals = UnsafeMutablePointer<ClawPaletteResourceGlobals>.allocate(capacity:1)
    private let graphicsContext = UnsafeMutablePointer<ClawGraphicsManagerLifecycleContext>.allocate(capacity:1)
    private let graphicsGlobals = UnsafeMutablePointer<ClawGraphicsManagerLifecycleGlobals>.allocate(capacity:1)
    private(set) var display:ClawNativeDisplay?
    var sourceGraphicsContext:UnsafeMutablePointer<ClawGraphicsManagerLifecycleContext> { graphicsContext }
    var deviceInterfaceToken:UInt32 { deviceToken }
    private var deviceToken:UInt32 = 0,modeScratch:UInt32 = 0
    private(set) var graphicsCalls:[UInt32:UInt64] = [:],displayProfile:[UInt32] = []
    var graphicsState:ClawGraphicsManagerLifecycleGlobals {graphicsGlobals.pointee}
    private var auxiliary:Set<UInt32> = [],resources:[UInt32:UInt32] = [:],slots:[String:UInt32] = [:]
    private var physical:[UInt32:Data] = [:]
    private var paletteVT:UInt32 = 0
    private var closed = false
    private(set) var sourceAllocations:Set<UInt32> = []
    private(set) var fault:UInt32 = 0,unresolved:Set<UInt32> = []
    var failedPhysicalCall:UInt32?
    var mode:(width:UInt32,height:UInt32,depth:UInt32) = (640,480,8)
    var observePhysical:(([String:Any])->Void)?
    /// The physical screen: the primary's attached palette changed (its
    /// entries or which palette is attached). An eight-bit screen shows such a
    /// change at once, without a Flip (the palette fades around level loading).
    var screenPaletteChanged:(()->Void)?
    private(set) var calls:[UInt32:UInt64] = [:],resourceLocks:[UInt32:Int] = [:]
    private(set) var attachedPalette:UInt32 = 0
    private var fadeClock:(()->UInt32)?,fadeObserver:((UInt32,UInt32,Data)->Void)?
    private(set) var fadeFault:UInt32 = 0,fadeDiagnostics:[[UInt32]] = []
    private(set) var wrapperToken:UInt32 = 0,backendToken:UInt32 = 0
    var currentRGB:Data? {
        guard let entries = physical[attachedPalette] else { return nil }
        var rgb = Data();rgb.reserveCapacity(768)
        for i in 0..<256 { rgb.append(contentsOf:entries[i*4..<i*4+3]) };return rgb
    }
    var isGrayscale:Bool {
        guard let p = physical[attachedPalette],p.count == 1024 else {return false}
        return p[0xdc] == p[0xdd] && p[0xdd] == p[0xde]
    }
    /// Native custom-level palette upload, retaining the physical entry flags.
    func renderRGB(_ rgb:Data) -> Bool {
        guard rgb.count == 768,var entries = physical[attachedPalette],entries.count == 1024 else {return false}
        for i in 0..<256 {for c in 0..<3 {entries[i*4+c] = rgb[i*3+c]}}
        physical[attachedPalette] = entries
        observePhysical?(["service":"IDirectDrawPalette::SetEntries","object":attachedPalette,"start":0,"count":256,"entries":entries])
        screenPaletteChanged?();return true
    }
    func toggleGrayscale() {
        guard var entries = physical[attachedPalette] else {return}
        let backup:UInt32 = 0x58011000,identity:UInt32 = 0x58011400
        if isGrayscale {
            guard heap.lookup(identity,words:1)?.pointee == attachedPalette,
                  let p = heap.lookupBytes(backup,count:1024) else {return}
            entries = Data(bytes:p,count:1024)
        } else {
            let p = heap.lookupBytes(backup,count:1024) ?? heap.storeBytes(token:backup,count:1024)
            entries.withUnsafeBytes{p.update(from:$0.baseAddress!.assumingMemoryBound(to:UInt8.self),count:1024)}
            (heap.lookup(identity,words:1) ?? heap.store(token:identity,words:1)).pointee = attachedPalette
            // Original v1.3 performs each integer division before summing.
            for i in 0..<256 {
                let j = i*4,gray = UInt8(Int(entries[j])*76/255+Int(entries[j+1])*150/255+Int(entries[j+2])*28/255)
                entries[j] = gray;entries[j+1] = gray;entries[j+2] = gray
            }
        }
        physical[attachedPalette] = entries
        observePhysical?(["service":"IDirectDrawPalette::SetEntries","object":attachedPalette,"start":0,"count":256,"entries":entries])
        screenPaletteChanged?()
    }
    private var retiredMoviePalettes:Set<UInt32> = []
    func makeMoviePalette(_ entries:Data)->UInt32 {
        guard entries.count == 1024 else {return 0}
        let token = own(4);heap.lookup(token,words:1)!.pointee = paletteVT
        physical[token] = entries;return token
    }
    func releaseMoviePalette(_ token:UInt32) {
        guard token != 0 else {return}
        if token == attachedPalette {retiredMoviePalettes.insert(token)}
        else {physical.removeValue(forKey:token);auxiliary.remove(token);heap.free(token)}
    }
    var yieldWindowEvents:(()->Void)?
    private static let create:UInt32 = 0x6e100014,get:UInt32 = 0x6e100110,set:UInt32 = 0x6e100118,attach:UInt32 = 0x6e10027c
    private static let ddRelease:UInt32 = 0x6e110008,ddEnumerate:UInt32 = 0x6e110020,ddCaps:UInt32 = 0x6e11002c,ddDisplay:UInt32 = 0x6e110030,ddRestore:UInt32 = 0x6e11004c,ddCooperative:UInt32 = 0x6e110050,ddMode:UInt32 = 0x6e110054,ddWait:UInt32 = 0x6e110058
    convenience init(scene:ClawNativeScene,root:URL) throws {
        try self.init(heap:scene.heap,owner:scene.ownerIdentity,parent:scene.sceneIdentity,
                      image:scene.rendering!.sourceImageGlobals,indexed:scene.rendering!.indexedToken,
                      paletteURL:root.appendingPathComponent("LEVEL\(scene.objectResources!.level)/PALETTES/MAIN.PAL"))
        scene.rendering!.installSourceDisplayTarget(display!.backToken)
    }
    // A nil palette leaves the freshly constructed display ready for the menu's
    // own recovered image/palette election, without loading a level palette.
    init(heap:ClawTokenHeap,owner:UInt32,parent:UInt32,image:UnsafeMutablePointer<ClawGameImageGlobals>,
         indexed:UInt32? = nil,paletteURL:URL? = nil,diagnostics:ClawNativeDiagnostics = .shared) throws {
        self.diagnostics = diagnostics
        self.heap = heap;ownerToken = owner;parentToken = parent
        managerToken = heap.allocate(bytes:104);backendManagerToken = heap.allocate(bytes:2180)
        globals.initialize(to:ClawPaletteResourceGlobals())
        context.initialize(to:ClawPaletteResourceContext());claw_palette_resource_defaults(context)
        context.pointee.globals = globals;context.pointee.scene = host
        graphicsGlobals.initialize(to:ClawGraphicsManagerLifecycleGlobals())
        graphicsContext.initialize(to:ClawGraphicsManagerLifecycleContext(scene:host,globals:graphicsGlobals,palette:context,maximumOperations:1000000,fault:0))
        for (t,n):(UInt32,Int) in [(0x54135c,6),(0x541374,1),(0x541378,5),(0x541398,1)] where heap.lookup(t,words:UInt32(n)) == nil {_ = heap.store(token:t,words:n)}
        guard let parent = heap.lookup(parentToken,words:12),parent[6] == 0,parent[7] == 0 else { throw AssetError.invalid("Palette resource scene slots already owned") }
        //Selected original4cea10 constructor sequence. Complete scene
        //initialization stays separately scoped; no second scene heap is made.
        var g = ClawSinglePlayerSceneGlobals(),c = ClawSinglePlayerSceneContext(),result:UInt32 = 0
        c.host = host
        let built = withUnsafeMutablePointer(to:&g) { p -> Bool in
            c.globals = p
            for (f,t,args):(UInt32,UInt32,[UInt32]) in [(0x45fde0,managerToken,[parentToken,0,0]),(0x4f6118,managerToken+16,[10]),(0x4f6118,managerToken+44,[10]),(0x4f6118,managerToken+72,[10])] {
                if args.withUnsafeBufferPointer({claw_single_player_scene_entry(f,t,$0.baseAddress,UInt32($0.count),&c,nil,nil,&result)}) != 1 || c.fault != 0 { return false }
            }
            return true
        }
        var ctorFault:UInt32 = 0
        guard built,claw_graphics_manager_construct(backendManagerToken,host,&ctorFault,&result) == 1,ctorFault == 0 else { throw AssetError.invalid("Original palette/graphics constructor") }
        let manager = heap.lookup(managerToken,words:26)!
        manager[0] = 0x513b28;manager[25] = 0
        parent[6] = managerToken;parent[7] = backendManagerToken
        for (t,methods):(UInt32,[UInt32]) in [
            (0x513b28,[0x4f701d,0x4cf0a0,0x4c9e30,0x4c96b0,0x4c9e30,0x4cf080,0x4bd250,0x4d4370,0x4cde00,0x4d4420,0x4d44f0,0x4d4570,0x4d45f0,0]),
            (0x513d78,[0x4f701d,0x4d47f0,0x4c9e30,0x4c96b0,0x4c9e30,0x4c80a0,0x4bd250,0x4d6670,0x4d47e0,0x4d65e0,0x4d65a0,0x4d6560,0x4d6620,0x4d6690])]
        where heap.lookup(t,words:14) == nil {
            let v = heap.store(token:t,words:14);methods.withUnsafeBufferPointer{v.update(from:$0.baseAddress!,count:14)}
        }
        let deviceVT = own(92);deviceToken = own(4)
        let dvt = heap.lookup(deviceVT,words:23)!
        for (slot,method):(Int,UInt32) in [(2,Self.ddRelease),(5,Self.create),(8,Self.ddEnumerate),(11,Self.ddCaps),(12,Self.ddDisplay),(19,Self.ddRestore),(20,Self.ddCooperative),(21,Self.ddMode),(22,Self.ddWait)] {dvt[slot] = method}
        heap.lookup(deviceToken,words:1)!.pointee = deviceVT
        paletteVT = own(28);let pvt = heap.lookup(paletteVT,words:7)!
        pvt[4] = Self.get;pvt[6] = Self.set
        modeScratch = own(108)
        displayProfile = [UInt32](repeating:0,count:27)
        displayProfile[0] = 108;displayProfile[2] = 480;displayProfile[3] = 640;displayProfile[4] = 640
        displayProfile[21] = 8 //Physical indexed mode has zero RGB channel masks.
        manager[7] = backendManagerToken
        _ = graphicsEntry(0x4bc0e0,receiver:0)
        //Whole source holder startup elects4d5510/4bc220 and actual primary,
        //attached and blank surfaces. Palette attachment uses that original graph.
        display = try ClawNativeDisplay(palette:self,host:host,image:image,indexed:indexed)
        guard display?.fault == 0 else {throw AssetError.invalid("Original display graph")}
        guard let paletteURL else {return}
        let data = try Data(contentsOf:paletteURL)
        guard data.count == 768 else { throw AssetError.invalid("Normal source PAL route requires actual768-byte triples") }
        let resource = own(24),bytes = own(UInt32(data.count)),name = own(16)
        data.withUnsafeBytes{UnsafeMutableRawPointer(heap.lookup(bytes,words:192)!).copyMemory(from:$0.baseAddress!,byteCount:$0.count)}
        let text = Array("PALETTES_MAIN".utf8)+[0]
        text.withUnsafeBytes{UnsafeMutableRawPointer(heap.lookup(name,words:4)!).copyMemory(from:$0.baseAddress!,byteCount:$0.count)}
        let r = heap.lookup(resource,words:6)!;r[0] = name;r[4] = bytes;r[5] = UInt32(data.count);resources[resource] = bytes
        wrapperToken = entry(0x4d4420,receiver:managerToken,args:[resource,0,0])
        guard wrapperToken != 0,fault == 0 else { throw AssetError.invalid("Original PAL factory failure \(unresolved)") }
        let owner = heap.lookup(ownerToken,words:12)!
        guard owner[0x2c/4] == 0 else { throw AssetError.invalid("Existing owner palette would need source release") }
        owner[0x2c/4] = wrapperToken;backendToken = heap.lookup(wrapperToken,words:5)![4]
        var hr:UInt32 = 0
        guard claw_palette_resource_capture_owner(ownerToken,context,nativePaletteResourceDependency,Unmanaged.passUnretained(self).toOpaque(),&hr) == 1,context.pointee.fault == 0,hr == 0 else { throw AssetError.invalid("Original owner GetEntries prefix") }
        _ = entry(0x4bb870,receiver:backendToken)
        manager[25] = wrapperToken
        guard entry(0x4d6690,receiver:wrapperToken) == 1,fault == 0 else { throw AssetError.invalid("Original palette display attachment") }
    }
    deinit { shutdown();graphicsContext.deinitialize(count:1);graphicsContext.deallocate();graphicsGlobals.deinitialize(count:1);graphicsGlobals.deallocate();context.deinitialize(count:1);context.deallocate();globals.deinitialize(count:1);globals.deallocate() }
    private var host:ClawSceneActorHost {
        ClawSceneActorHost(context:Unmanaged.passUnretained(self).toOpaque(),lookup:{u,t,n in
            guard let u else { return nil };return Unmanaged<ClawNativePaletteResources>.fromOpaque(u).takeUnretainedValue().heap.lookup(t,words:n)
        },allocate:nil,free:nil,call:nil,readClock:nil)
    }
    private func own(_ n:UInt32) -> UInt32 { let t = heap.allocate(bytes:n);auxiliary.insert(t);return t }
    @discardableResult func entry(_ f:UInt32,receiver:UInt32,args:[UInt32] = []) -> UInt32 {
        globals.pointee.cooperativeHolder = heap.lookup(0x541374,words:1)!.pointee
        var result:UInt32 = 0
        let accepted = heap.withStableFreedStorage {args.withUnsafeBufferPointer{
            claw_palette_resource_entry(f,receiver,$0.baseAddress,UInt32($0.count),context,nativePaletteResourceDependency,Unmanaged.passUnretained(self).toOpaque(),&result)
        }}
        heap.lookup(0x541374,words:1)!.pointee = globals.pointee.cooperativeHolder;graphicsGlobals.pointee.cooperativeHolder = globals.pointee.cooperativeHolder
        if accepted != 1 { unresolved.insert(f);fault = 1 };fault = max(fault,context.pointee.fault);return result
    }
    func physicalEntries(_ token:UInt32) -> Data? { physical[token] }
    func menuPhysicalService(_ q:ClawCall)->UInt32? {
        if [Self.ddMode,Self.ddCooperative,Self.ddRestore,Self.ddRelease,Self.ddDisplay,Self.ddCaps,UInt32(0x546850),UInt32(0x4f4486)].contains(q.function),q.receiver == 0,q.argumentCount <= 6 {
            var call = ClawGraphicsManagerLifecycleCall();call.function = q.function;call.argumentCount = q.argumentCount
            withUnsafeMutableBytes(of:&call.arguments){dst in withUnsafeBytes(of:q.arguments){dst.copyBytes(from:$0.prefix(dst.count))}}
            if q.function == Self.ddDisplay,let p = heap.lookup(q.arguments.1,words:27) {
                call.arguments.1 = 0;call.localMask = 2;call.bufferCount = 1;call.buffers.0 = p;call.bufferBytes.0 = 108
            }
            return graphicsService(call)
        }
        guard q.receiver == 0,[Self.create,Self.get,Self.set,Self.attach,Self.ddWait].contains(q.function),q.argumentCount <= 5 else {return nil}
        var call = ClawPaletteResourceCall();call.function = q.function;call.argumentCount = q.argumentCount
        withUnsafeMutableBytes(of:&call.arguments){dst in withUnsafeBytes(of:q.arguments){dst.copyBytes(from:$0.prefix(dst.count))}}
        if q.function == Self.create {
            guard let data = heap.lookup(q.arguments.2,words:256) else {return nil}
            call.localMask = 4;call.bufferCount = 1;call.buffers.0 = data;call.bufferBytes.0 = 1024
        } else if q.function == Self.get || q.function == Self.set {
            guard q.arguments.3 <= 256,let data = heap.lookup(q.arguments.4,words:q.arguments.3*4/4) else {return nil}
            call.localMask = 16;call.bufferCount = 1;call.buffers.0 = data;call.bufferBytes.0 = q.arguments.3*4
        }
        return service(call)
    }
    //The source blocking duration and integer channels remain unchanged. A
    //clock/observer override permits retained headless histories; ordinary
    //calls use monotonic milliseconds and the actual physical palette.
    @discardableResult func fadeEntry(_ f:UInt32,args:[UInt32] = [],clock:(()->UInt32)? = nil,observe:((UInt32,UInt32,Data)->Void)? = nil)->UInt32 {
        guard !closed else {fadeFault = 3;return 0}
        let oldClock = fadeClock,oldObserver = fadeObserver
        fadeClock = clock;fadeObserver = observe
        defer {fadeClock = oldClock;fadeObserver = oldObserver}
        importGraphicsAliases()
        var c = ClawPaletteFadeContext(scene:host,palette:context,maximumOperations:100000000,fault:0),out:UInt32 = 0
        let done = heap.withStableFreedStorage {args.withUnsafeBufferPointer {
            claw_palette_fade_entry(f,backendToken,$0.baseAddress,UInt32($0.count),&c,nativePaletteFadeDependency,Unmanaged.passUnretained(self).toOpaque(),&out)
        }}
        publishGraphicsAliases();fadeFault = c.fault
        if done != 1,fadeFault == 0 {fadeFault = 1};return out
    }
    fileprivate func fadeService(_ call:ClawPaletteFadeCall)->UInt32 {
        if call.function == 0x546df0 {
            calls[call.function,default:0] &+= 1
            guard call.receiver == 0,call.argumentCount == 0 else {fault = 2;return 0}
            return fadeClock?() ?? UInt32(truncatingIfNeeded:UInt64(ProcessInfo.processInfo.systemUptime*1000))
        }
        if call.function == 0x4bd260 {
            guard call.argumentCount == 3 else {fault = 2;return 0}
            return diagnosticReport(withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(3))})
        }
        var q = ClawPaletteResourceCall();q.function = call.function;q.receiver = call.receiver;q.argumentCount = call.argumentCount;q.arguments = call.arguments
        q.localMask = call.localMask;q.bufferCount = call.bufferCount;q.buffers = call.buffers;q.bufferBytes = call.bufferBytes
        return service(q)
    }
    func shutdown() {
        guard !closed else { return };closed = true
        display?.shutdown()
        if wrapperToken != 0,heap.lookup(wrapperToken,words:5) != nil { _ = entry(0x4d47f0,receiver:wrapperToken,args:[1]) }
        if let owner = heap.lookup(ownerToken,words:12),owner[0x2c/4] == wrapperToken { owner[0x2c/4] = 0 }
        if let parent = heap.lookup(parentToken,words:12) {
            if parent[6] == managerToken { parent[6] = 0 };if parent[7] == backendManagerToken { parent[7] = 0 }
            if auxiliary.contains(parent[1]) { parent[1] = 0 }
        }
        //Whole source graphics destruction releases descriptors/lists/device;
        //the outer native owner frees the2180-byte manager after that body.
        if heap.lookup(backendManagerToken,words:545) != nil {
            _ = graphicsEntry(0x4bc1b0,receiver:backendManagerToken)
            _ = graphicsEntry(0x4bc100,receiver:0)
        }
        display?.finishTransport()
        heap.free(managerToken);heap.free(backendManagerToken)
        //Source palette cleanup deliberately performs no palette COM Release. Native physical
        //interface identities end with the device transport's own lifetime.
        for t in auxiliary { heap.free(t) };auxiliary.removeAll();physical.removeAll();slots.removeAll()
    }
    func importGraphicsAliases() {
        graphicsGlobals.pointee.sharedDevice = heap.lookup(0x541398,words:1)!.pointee
        graphicsGlobals.pointee.cooperativeHolder = heap.lookup(0x541374,words:1)!.pointee
        let channels = heap.lookup(0x54135c,words:6)!
        graphicsGlobals.pointee.channelShift = (channels[0],channels[1],channels[2]);graphicsGlobals.pointee.channelReduction = (channels[3],channels[4],channels[5])
        globals.pointee.cooperativeHolder = graphicsGlobals.pointee.cooperativeHolder
    }
    func publishGraphicsAliases() {
        heap.lookup(0x541398,words:1)!.pointee = graphicsGlobals.pointee.sharedDevice
        heap.lookup(0x541374,words:1)!.pointee = graphicsGlobals.pointee.cooperativeHolder
        let channels = heap.lookup(0x54135c,words:6)!,g = graphicsGlobals.pointee
        channels[0] = g.channelShift.0;channels[1] = g.channelShift.1;channels[2] = g.channelShift.2
        channels[3] = g.channelReduction.0;channels[4] = g.channelReduction.1;channels[5] = g.channelReduction.2
        globals.pointee.cooperativeHolder = g.cooperativeHolder
    }
    @discardableResult func graphicsEntry(_ f:UInt32,receiver:UInt32,args:[UInt32] = [])->UInt32 {
        importGraphicsAliases();var result:UInt32 = 0
        let accepted = heap.withStableFreedStorage {args.withUnsafeBufferPointer{
            claw_graphics_manager_lifecycle_entry(f,receiver,$0.baseAddress,UInt32($0.count),graphicsContext,nativeGraphicsLifecycleDependency,Unmanaged.passUnretained(self).toOpaque(),&result)
        }}
        publishGraphicsAliases();fault = max(fault,graphicsContext.pointee.fault)
        if accepted != 1 {unresolved.insert(f);fault = max(fault,1)};return result
    }
    func graphicsService(_ e:ClawGraphicsManagerLifecycleCall)->UInt32 {
        if let value = display?.graphicsService(e) {return value}
        let args = withUnsafeBytes(of:e.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(e.argumentCount)))}
        graphicsCalls[e.function,default:0] &+= 1
        if failedPhysicalCall == e.function {
            failedPhysicalCall = nil
            observePhysical?(["service":"graphics-failure","function":e.function,"result":UInt32(0x8007000e)])
            return 0x8007000e
        }
        switch e.function {
        case 0x546850,0x4f4486:
            guard args.count == 3,args[0] == 0,args[2] == 0,args[1] == backendManagerToken else {break}
            heap.lookup(args[1],words:1)!.pointee = deviceToken
            observePhysical?(["service":"DirectDrawCreate","object":deviceToken,"output":args[1]]);return 0
        case Self.ddCooperative:
            guard args == [deviceToken,parentToken,0x11] else {break};return 0
        case Self.ddCaps:
            guard args.count == 3,args[0] == deviceToken,let deviceCaps = heap.lookup(args[1],words:79),let emulationCaps = heap.lookup(args[2],words:79),deviceCaps[0] == 316,emulationCaps[0] == 316 else {break}
            //The native memory framebuffer has no hardware DirectDraw caps.
            deviceCaps[1] = 0;emulationCaps[1] = 0;return 0
        case Self.ddEnumerate:
            guard args == [deviceToken,0,0,0,0x4bcda0] else {break}
            displayProfile.withUnsafeBufferPointer{heap.lookup(modeScratch,words:27)!.update(from:$0.baseAddress!,count:27)}
            return graphicsEntry(args[4],receiver:0,args:[modeScratch,0]) == 1 ? 0:0x80004005
        case Self.ddMode:
            guard args.count == 4,args[0] == deviceToken,args[1] > 0,args[2] > 0,args[1] <= 2048,args[2] <= 2048,[8,16,24,32].contains(args[3]) else {return 0x80070057}
            mode = (args[1],args[2],args[3])
            displayProfile[3] = args[1];displayProfile[2] = args[2];displayProfile[4] = args[1]*((args[3]+7)/8);displayProfile[21] = args[3]
            observePhysical?(["service":"IDirectDraw::SetDisplayMode","object":deviceToken,"mode":Array(args.dropFirst())]);return 0
        case Self.ddDisplay:
            guard args == [deviceToken,0],e.localMask == 2,e.bufferCount == 1,e.bufferBytes.0 == 108,let p = e.buffers.0 else {break}
            displayProfile.withUnsafeBufferPointer{p.update(from:$0.baseAddress!,count:27)};observePhysical?(["service":"IDirectDraw::GetDisplayMode","object":deviceToken]);return 0
        case Self.ddRestore,Self.ddRelease:
            guard args == [deviceToken] else {break};return 0
        default:
            var paletteCall = ClawPaletteResourceCall();paletteCall.function = e.function;paletteCall.receiver = e.receiver;paletteCall.arguments = e.arguments;paletteCall.argumentCount = e.argumentCount
            paletteCall.localMask = e.localMask;paletteCall.bufferCount = e.bufferCount;paletteCall.buffers = e.buffers;paletteCall.bufferBytes = e.bufferBytes
            return service(paletteCall)
        }
        unresolved.insert(e.function);fault = 1;return 0
    }
    @discardableResult func diagnosticReport(_ args:[UInt32]) -> UInt32 {
        guard args.count == 3 else {fault = 2;return 0}
        fadeDiagnostics.append(args)
        if !diagnostics.report(display:true,filename:args[0],line:args[1],result:args[2],bytes:{[unowned self] token,count in
            self.heap.lookupBytes(token,count:count)
        }) {fault = max(fault,diagnostics.fault)}
        return 0
    }
    func service(_ call:ClawPaletteResourceCall) -> UInt32 {
        let args = withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
        calls[call.function,default:0] &+= 1
        switch call.function {
        case 0x4bd260:
            return diagnosticReport(args)
        case 0x4f63ec:
            guard args.count == 1 else { break };let t = heap.allocate(bytes:args[0]);if t != 0 { sourceAllocations.insert(t) };return t
        case 0x4f6428:
            guard args.count == 1 else {break};if args[0] == 0 {return 0}
            guard sourceAllocations.remove(args[0]) != nil else { break };heap.free(args[0]);return 0
        case 0x4b61c0:
            guard let p = resources[call.receiver] else { break };resourceLocks[call.receiver,default:0] += 1;return p
        case 0x4b6230:
            guard resources[call.receiver] != nil,resourceLocks[call.receiver] == 1 else { break };resourceLocks[call.receiver] = 0;return 0
        case 0x4f62a8:
            guard call.receiver == managerToken+16,args == [0],call.localMask == 1,call.bufferCount == 1,let text = call.buffers.0,call.bufferBytes.0 > 0,call.bufferBytes.0 <= 80 else { break }
            let bytes = UnsafeRawBufferPointer(start:text,count:Int(call.bufferBytes.0))
            guard bytes.last == 0 else { break };let name = String(decoding:bytes.dropLast(),as:UTF8.self)
            if let slot = slots[name] { return slot };let slot = own(4);slots[name] = slot;return slot
        case Self.ddWait:
            guard args == [deviceToken,1,0] else {break}
            yieldWindowEvents?()
            observePhysical?(["service":"IDirectDraw::WaitForVerticalBlank","object":args[0],"flags":args[1]]);return 0
        case Self.create:
            guard args.count == 5,args[1] == 0x44,call.localMask == 4,call.bufferCount == 1,call.bufferBytes.0 == 1024,let entries = call.buffers.0,let output = heap.lookup(args[3],words:1) else { break }
            let token = own(4);heap.lookup(token,words:1)!.pointee = paletteVT
            physical[token] = Data(bytes:entries,count:1024);output.pointee = token
            observePhysical?(["service":"IDirectDraw::CreatePalette","object":args[0],"palette":token,"entries":physical[token]!]);return 0
        case Self.get:
            guard args.count == 5,args[1] == 0,let data = physical[args[0]],UInt64(args[2])+UInt64(args[3]) <= 256,call.bufferBytes.0 == args[3]*4,let destination = call.buffers.0 else { break }
            observePhysical?(["service":"IDirectDrawPalette::GetEntries","object":args[0],"start":args[2],"count":args[3],"entries":data])
            data.withUnsafeBytes{UnsafeMutableRawPointer(destination).copyMemory(from:$0.baseAddress!.advanced(by:Int(args[2])*4),byteCount:Int(args[3])*4)};return 0
        case Self.set:
            guard args.count == 5,var data = physical[args[0]],UInt64(args[2])+UInt64(args[3]) <= 256,call.bufferBytes.0 == args[3]*4 else { break }
            if args[3] == 0 { return 0 };guard let entries = call.buffers.0 else { break }
            let replacement = Data(bytes:entries,count:Int(args[3])*4);data.replaceSubrange(Int(args[2])*4..<Int(args[2]+args[3])*4,with:replacement);physical[args[0]] = data
            observePhysical?(["service":"IDirectDrawPalette::SetEntries","object":args[0],"start":args[2],"count":args[3],"entries":data])
            fadeObserver?(args[2],args[3],data)
            if args[0] == attachedPalette {screenPaletteChanged?()};return 0
        case Self.attach:
            guard args.count == 2,physical[args[1]] != nil else { break };attachedPalette = args[1]
            for token in retiredMoviePalettes where token != attachedPalette {
                physical.removeValue(forKey:token);auxiliary.remove(token);heap.free(token)
                retiredMoviePalettes.remove(token)
            }
            observePhysical?(["service":"IDirectDrawSurface::SetPalette","object":args[0],"palette":args[1]])
            screenPaletteChanged?();return 0
        default:break
        }
        unresolved.insert(call.function);fault = 1;return 0
    }
}
private let nativePaletteResourceDependency:ClawPaletteResourceDependency = {c,e,u in
    guard let c,let e,let u else { return 0 };let host = Unmanaged<ClawNativePaletteResources>.fromOpaque(u).takeUnretainedValue()
    let result = host.service(e.pointee);if host.fault != 0 { c.pointee.fault = host.fault };return result
}

private let nativeGraphicsLifecycleDependency:ClawGraphicsManagerLifecycleDependency = {c,e,u in
    guard let c,let e,let u else {return 0};let host = Unmanaged<ClawNativePaletteResources>.fromOpaque(u).takeUnretainedValue()
    host.publishGraphicsAliases();let result = host.graphicsService(e.pointee)
    if host.fault != 0 {c.pointee.fault = host.fault};return result
}
private let nativePaletteFadeDependency:ClawPaletteFadeDependency = {c,e,u in
    guard let c,let e,let u else {return 0};let h = Unmanaged<ClawNativePaletteResources>.fromOpaque(u).takeUnretainedValue()
    let out = h.fadeService(e.pointee);if h.fault != 0 {c.pointee.fault = h.fault};return out
}

extension ClawNativePaletteResources {
    struct SavedState: Codable, Equatable {
        let owner: UInt32, parent: UInt32, manager: UInt32, backend: UInt32
        let context: [String: Data], graphicsContext: [String: Data]
        let globals: ClawSnapshotValue<ClawPaletteResourceGlobals>, graphics: ClawSnapshotValue<ClawGraphicsManagerLifecycleGlobals>
        let device: UInt32, scratch: UInt32, paletteVT: UInt32, wrapper: UInt32, backendToken: UInt32
        let auxiliary: Set<UInt32>, resources: [UInt32: UInt32], slots: [String: UInt32], physical: [UInt32: Data], source: Set<UInt32>
        let graphicsCalls: [UInt32: UInt64], profile: [UInt32], calls: [UInt32: UInt64], locks: [UInt32: Int]
        let fault: UInt32, unresolved: Set<UInt32>, mode: [UInt32], attached: UInt32, retired: Set<UInt32>, fadeFault: UInt32, fades: [[UInt32]]
        let display: ClawNativeDisplay.SavedState?
    }
    func savedState() throws -> SavedState {
        guard !closed, fadeClock == nil, fadeObserver == nil, failedPhysicalCall == nil else { throw ClawSnapshotError.activeFrame }
        return .init(owner: ownerToken, parent: parentToken, manager: managerToken, backend: backendManagerToken,
            context: Self.contextFields.capture(context.pointee), graphicsContext: Self.graphicsFields.capture(graphicsContext.pointee),
            globals: ClawSnapshotValue(globals.pointee), graphics: ClawSnapshotValue(graphicsGlobals.pointee), device: deviceToken, scratch: modeScratch,
            paletteVT: paletteVT, wrapper: wrapperToken, backendToken: backendToken, auxiliary: auxiliary, resources: resources, slots: slots, physical: physical,
            source: sourceAllocations, graphicsCalls: graphicsCalls, profile: displayProfile, calls: calls, locks: resourceLocks, fault: fault, unresolved: unresolved,
            mode: [mode.width, mode.height, mode.depth], attached: attachedPalette, retired: retiredMoviePalettes, fadeFault: fadeFault, fades: fadeDiagnostics,
            display: try display?.savedState())
    }
    func restoreState(_ saved: SavedState) throws {
        guard !closed, fadeClock == nil, fadeObserver == nil, saved.owner == ownerToken, saved.parent == parentToken, saved.manager == managerToken,
              saved.backend == backendManagerToken, saved.mode.count == 3, (saved.display == nil) == (display == nil),
              saved.physical.values.allSatisfy({ $0.count == 1024 }) else { throw ClawSnapshotError.invalidState }
        let cx = try Self.contextFields.restoring(saved.context, into: context.pointee)
        let gx = try Self.graphicsFields.restoring(saved.graphicsContext, into: graphicsContext.pointee)
        if let state = saved.display { try display!.restoreState(state) }
        context.pointee = cx; graphicsContext.pointee = gx; globals.pointee = saved.globals.value; graphicsGlobals.pointee = saved.graphics.value
        deviceToken = saved.device; modeScratch = saved.scratch; paletteVT = saved.paletteVT; wrapperToken = saved.wrapper; backendToken = saved.backendToken
        auxiliary = saved.auxiliary; resources = saved.resources; slots = saved.slots; physical = saved.physical; sourceAllocations = saved.source
        graphicsCalls = saved.graphicsCalls; displayProfile = saved.profile; calls = saved.calls; resourceLocks = saved.locks; fault = saved.fault; unresolved = saved.unresolved
        mode = (saved.mode[0], saved.mode[1], saved.mode[2]); attachedPalette = saved.attached; retiredMoviePalettes = saved.retired
        fadeFault = saved.fadeFault; fadeDiagnostics = saved.fades
    }
    private static let contextFields = ClawSnapshotFields<ClawPaletteResourceContext>(fields: [
        .init("systemPaletteScratchToken", \.systemPaletteScratchToken),
        .init("composeLists", \.composeLists),
        .init("maximumSteps", \.maximumSteps),
        .init("fault", \.fault)
    ])
    private static let graphicsFields = ClawSnapshotFields<ClawGraphicsManagerLifecycleContext>(fields: [
        .init("maximumOperations", \.maximumOperations),
        .init("fault", \.fault)
    ])
}
extension ClawPaletteResourceGlobals: ClawSnapshotNativeValue {}
extension ClawGraphicsManagerLifecycleGlobals: ClawSnapshotNativeValue {}
