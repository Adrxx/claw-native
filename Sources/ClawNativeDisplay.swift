import Foundation

// Raw pixel transports borrow the caller's stack provider. A menu already owns
// a mapped stack and must not install a second canonical stack over that heap.
protocol ClawNativeRawDisplayHost:AnyObject {
    var heap:ClawTokenHeap {get}
    var fault:ClawNativeCanonicalHost.Fault? {get}
    func bytes(_ token:UInt32,count:UInt32)->UnsafeMutablePointer<UInt8>?
    @discardableResult func rawReject(_ code:UInt32,at:UInt32)->ClawNativeCanonicalHost.Fault
    func callNativeDependency(_ call:ClawCall)->UInt32?
}
extension ClawNativeCanonicalHost:ClawNativeRawDisplayHost {
    @discardableResult func rawReject(_ code:UInt32,at:UInt32)->Fault {fail(code,at:at)}
}

//Source holder/wrapper/surface ownership over the native indexed framebuffer.
//DirectDraw interface creation, descriptors and storage are named transports.
final class ClawNativeDisplay {
    //The owner calls source cleanup from its destructor, when ARC unowned
    //references already reject access. Borrow its callback context, as the C
    //dependencies do, and end forwarding before the owner releases that context.
    private let paletteContext:UnsafeMutableRawPointer
    private var palette:ClawNativePaletteResources {
        Unmanaged<ClawNativePaletteResources>.fromOpaque(paletteContext).takeUnretainedValue()
    }
    let heap:ClawTokenHeap,holderToken:UInt32
    private let context = UnsafeMutablePointer<ClawSceneDisplayContext>.allocate(capacity:1)
    private var interfaces:[UInt32:(pixels:UInt32,descriptor:[UInt32])] = [:]
    private var transportTokens:Set<UInt32> = []
    private var colorKeys:[UInt32:[UInt32:ClosedRange<UInt32>]] = [:]
    private(set) var surfaceDiagnostics:[[UInt32]] = [],lastSurfaceFault:UInt32 = 0
    private(set) var sourceAllocations:Set<UInt32> = [],calls:[UInt32:UInt64] = [:]
    private(set) var fault:UInt32 = 0,unresolved:Set<UInt32> = []
    var failPrimaryCreation = false
    var observePhysical:(([String:Any])->Void)?
    private struct MenuFont:Decodable {
        struct Glyph:Decodable {let advance:Int,measureAdvance:Int,top:Int,pixels:[UInt8];let leftBearing:Int?}
        let height:Int,glyphs:[String:Glyph]
    }
    private var menuFont:MenuFont?
    fileprivate struct TextDC: Codable, Equatable {let surface:UInt32;var background:UInt32 = 2,color:UInt32 = 0,font:UInt32 = 0;var clip:[Int]?}
    private var regions:[UInt32:[Int]] = [:]
    private(set) var creditsEvidence:[[String:Any]] = []
    var recordsCreditsEvidence = false
    private func recordCredits(_ event:[String:Any]) {
        if recordsCreditsEvidence {creditsEvidence.append(event)}
    }
    // Logical fonts made by the native CreateFontA, and the stand-in for the
    // DC's default (stock) font that SelectObject hands back. Both draw with
    // the one physical font atlas (menuFont), as the reference does.
    private var fonts:Set<UInt32> = []
    private var stockFont:UInt32 = 0
    func registerFont(_ handle:UInt32) {fonts.insert(handle)}
    private var textDCs:[UInt32:TextDC] = [:]
    private(set) var textFailureLine:Int = 0
    static let getDC:UInt32 = 0x6e120044,releaseDC:UInt32 = 0x6e120068,selectObject:UInt32 = 0x54691c
    func installMenuFont(_ data:Data) throws {
        let font = try JSONDecoder().decode(MenuFont.self,from:data)
        guard font.height > 0,font.height <= 32,font.glyphs.count == 95,
              (32...126).allSatisfy({code in
                  guard let g = font.glyphs[String(code)] else {return false}
                  return (0...32).contains(g.advance) && (0...32).contains(g.measureAdvance) && (0...32).contains(g.top) && g.pixels.count == 1024 && g.pixels.allSatisfy{$0 < 2}
              }) else {throw AssetError.invalid("Invalid menu physical font")}
        menuFont = font
    }
    private var frontDD:UInt32 = 0,backDD:UInt32 = 0
    var menuSwapChain = false
    private(set) var presentations = 0
    /// The physical screen: called on every primary Flip with the presented
    /// indexed pixels (width, height, stride), as DirectDraw shows a flip at
    /// once even when game code keeps running (the level loading screen).
    var presented:((Data,UInt32,UInt32,UInt32)->Void)?
    /// The physical screen also changes when game code writes the primary
    /// (front) surface itself between Flips, as the level loader's progress
    /// bar does: called after each such write with the whole front surface
    /// and what the write was.
    var primaryWritten:((Data,UInt32,UInt32,UInt32,[String:Any])->Void)?
    private func wrotePrimary(_ dd:UInt32,_ detail:[String:Any]) {
        guard menuSwapChain,dd == frontDD,let primaryWritten,let d = interfaces[dd],
              let pixels = heap.lookupBytes(d.pixels,count:d.descriptor[4]*d.descriptor[2]) else {return}
        primaryWritten(Data(bytes:pixels,count:Int(d.descriptor[4]*d.descriptor[2])),d.descriptor[3],d.descriptor[2],d.descriptor[4],detail)
    }
    private var closed = false,finished = false
    private var pcxInput:(token:UInt32,bytes:UInt32)?
    private var imageFault:UnsafeMutablePointer<UInt32>?
    private(set) var lastPCXFault:UInt32 = 0,pcxLoads:UInt64 = 0
    private let surfaceVT:UInt32
    static let create:UInt32 = 0x6e120018,release:UInt32 = 0x6e120008
    static let attached:UInt32 = 0x6e120030,describe:UInt32 = 0x6e120058
    static let lock:UInt32 = 0x6e120064,unlock:UInt32 = 0x6e120080
    static let blt:UInt32 = 0x6e120014,bltFast:UInt32 = 0x6e12001c,setColorKey:UInt32 = 0x6e120074
    static let flip:UInt32 = 0x6e12002c
    static let isLost:UInt32 = 0x6e120060
    var primaryToken:UInt32 {heap.lookup(holderToken,words:7)?[4] ?? 0}
    var backToken:UInt32 {heap.lookup(holderToken,words:7)?[5] ?? 0}
    var spareToken:UInt32 {heap.lookup(holderToken,words:7)?[6] ?? 0}
    func movieFrame(_ decoder:ClawNativeMovieBackground,surface:UInt32,clock:UInt32) throws -> Bool {
        guard let d = interfaces[surface],d.descriptor[21] == 8,
              let dest = heap.lookupBytes(d.pixels,count:d.descriptor[4]*d.descriptor[2]) else {
            throw AssetError.invalid("Background movie surface")
        }
        let width = Int(d.descriptor[3]),height = Int(d.descriptor[2]),stride = Int(d.descriptor[4])
        guard let frame = try decoder.frame(clock:clock,width:width,height:height) else {return false}
        frame.withUnsafeBytes { raw in
            for y in 0..<height {dest.advanced(by:y*stride).update(from:raw.bindMemory(to:UInt8.self).baseAddress!.advanced(by:y*width),count:width)}
        }
        wrotePrimary(surface,["service":"background-movie-frame"])
        return true
    }

    convenience init(palette:ClawNativePaletteResources,scene:ClawNativeScene) throws {
        try self.init(palette:palette,host:scene.actorHost,image:scene.rendering!.sourceImageGlobals,
                      indexed:scene.rendering!.indexedToken)
        scene.rendering!.installSourceDisplayTarget(backToken)
    }
    // Native menu startup supplies its own heap/scene and image globals; no world
    // or player is needed to own the display. Image storage outlives this owner.
    init(palette:ClawNativePaletteResources,host:ClawSceneActorHost,
         image:UnsafeMutablePointer<ClawGameImageGlobals>,indexed:UInt32? = nil) throws {
        paletteContext = Unmanaged.passUnretained(palette).toOpaque();heap = palette.heap
        holderToken = heap.allocate(bytes:28);sourceAllocations.insert(holderToken)
        surfaceVT = heap.allocate(bytes:132);transportTokens.insert(surfaceVT)
        // Shared original scratch persists across raw draws on this heap.
        if heap.lookupBytes(0x542bb0,count:129) == nil {
            guard !heap.overlaps(0x542bb0,count:132) else {throw AssetError.invalid("Raw PID scratch span")}
            heap.store(token:0x542bb0,words:33).initialize(repeating:0,count:33)
        }
        context.initialize(to:ClawSceneDisplayContext())
        context.pointee.scene = host
        context.pointee.graphics = palette.sourceGraphicsContext
        context.pointee.image = image
        context.pointee.maximumOperations = 1000000
        for (t,values) in clawOriginalDisplayVTables {
            if let old = heap.lookup(t,words:UInt32(values.count)) {
                guard Array(UnsafeBufferPointer(start:old,count:values.count)) == values else {throw AssetError.invalid("Source display vtable mismatch")}
            } else {
                guard heap.lookup(t,words:1) == nil else {throw AssetError.invalid("Source display metadata span")}
                values.withUnsafeBufferPointer{heap.store(token:t,words:values.count).update(from:$0.baseAddress!,count:values.count)}
            }
        }
        let vt = heap.lookup(surfaceVT,words:33)!
        for (slot,f):(Int,UInt32) in [(2,Self.release),(5,Self.blt),(7,Self.bltFast),(11,Self.flip),(17,Self.getDC),(26,Self.releaseDC),(29,Self.setColorKey),(12,Self.attached),(22,Self.describe),(24,Self.isLost),(25,Self.lock),(31,0x6e10027c),(32,Self.unlock)] {vt[slot] = f}
        heap.lookup(heap.lookup(palette.deviceInterfaceToken,words:1)!.pointee,words:23)![6] = Self.create
        var g = ClawSinglePlayerSceneGlobals(),c = ClawSinglePlayerSceneContext(),out:UInt32 = 0
        c.host = host
        let args:[UInt32] = [palette.parentToken,0,0]
        let built = withUnsafeMutablePointer(to:&g){p -> Bool in
            c.globals = p
            return args.withUnsafeBufferPointer{claw_single_player_scene_entry(0x45fde0,holderToken,$0.baseAddress,3,&c,nil,nil,&out)} == 1 && c.fault == 0
        }
        guard built else {throw AssetError.invalid("Source display holder constructor")}
        let holder = heap.lookup(holderToken,words:7)!
        holder[0] = 0x513c68;holder[4] = 0;holder[5] = 0;holder[6] = 0
        let parent = heap.lookup(palette.parentToken,words:15)!
        parent[1] = holderToken;parent[12] = palette.parentToken
        //4ca6f0 owns primary startup and both auxiliary factory elections.
        //The back DD storage is the same live native indexed pixel allocation.
        backDD = makeInterface(pixels:indexed)
        guard entry(0x4ca6f0,receiver:holderToken,args:[640,480,8,0]) == 1,
              entry(0x4cf730,receiver:holderToken) == 1,fault == 0 else {
            throw AssetError.invalid("Original native display startup fault \(unresolved)")
        }
    }
    deinit {shutdown();finishTransport();context.deinitialize(count:1);context.deallocate()}
    private func own(_ n:UInt32)->UInt32 {let t = heap.allocate(bytes:n);transportTokens.insert(t);return t}
    private func makeInterface(pixels:UInt32? = nil,width:UInt32 = 640,height:UInt32 = 480,depth:UInt32 = 8)->UInt32 {
        let stride = width*((depth+7)/8)
        let dd = own(4),p = pixels ?? own(stride*(height+1))
        heap.lookup(dd,words:1)!.pointee = surfaceVT
        var d = [UInt32](repeating:0,count:27)
        d[0] = 108;d[1] = 7;d[2] = height;d[3] = width;d[4] = stride;d[9] = p;d[21] = depth
        interfaces[dd] = (p,d);return dd
    }
    //Whole original surface factory/list ownership, using the requested physical
    //memory descriptor. Menus/Story still have to elect this through their loader.
    func createSurface(width:UInt32,height:UInt32,depth:UInt32 = 0)->UInt32 {
        guard !closed,!finished else {return 0}
        return entry(0x4bc670,receiver:palette.backendManagerToken,args:[width,height,depth,0,0xffffffff])
    }
    private var sourceHost:ClawSceneActorHost {
        ClawSceneActorHost(context:Unmanaged.passUnretained(self).toOpaque(),lookup:{u,t,n in
            guard let u else {return nil};return Unmanaged<ClawNativeDisplay>.fromOpaque(u).takeUnretainedValue().heap.lookup(t,words:n)
        },allocate:{u,n in
            guard let u else {return 0};let h = Unmanaged<ClawNativeDisplay>.fromOpaque(u).takeUnretainedValue()
            guard !h.finished else {return 0};let t = h.heap.allocate(bytes:n);if t != 0 {h.sourceAllocations.insert(t)};return t
        },free:nil,call:nil,readClock:nil)
    }
    //Whole4bc520 →4bf9c0(type2) →4be810. Dimensions come from the source
    //PCX wrapper; initialization and list insertion are elected by that graph.
    func createPCX(data:UInt32,byteCount:UInt32,flags:UInt32 = 0,colorKey:UInt32 = .max)->UInt32 {
        guard !closed,!finished else {lastPCXFault = 3;return 0}
        guard byteCount <= 4<<20 else {lastPCXFault = 2;return 0}
        let oldInput = pcxInput;pcxInput = (data,byteCount);defer {pcxInput = oldInput}
        var args = ClawGameImageArguments(),out:UInt32 = 0,localFault:UInt32 = 0
        args.count = 5;args.words = (data,2,byteCount,flags,colorKey,0,0,0)
        let h = ClawGameImageHost(heap:sourceHost,serviceContext:Unmanaged.passUnretained(self).toOpaque(),service:nativeDisplayImageDependency)
        let done = withUnsafeMutablePointer(to:&localFault){p -> UInt32 in
            let old = imageFault;imageFault = p;defer {imageFault = old}
            return heap.withStableFreedStorage {claw_game_image_entry(0x4bc520,palette.backendManagerToken,args,context.pointee.image,h,p,&out)}
        }
        lastPCXFault = localFault;if done == 1,localFault == 0 {if out != 0 {pcxLoads &+= 1};return out};return 0
    }
    //Whole source type4 indexed PID surface factory; compressed PID ownership
    //remains its existing GameImage owner and has no DD surface copy here.
    func createPID(data:UInt32,byteCount:UInt32,flags:UInt32 = 0,colorKey:UInt32 = 0)->UInt32 {
        guard !closed,!finished,byteCount >= 32,byteCount <= 4<<20 else {lastPCXFault = 2;return 0}
        var args = ClawGameImageArguments(),out:UInt32 = 0,localFault:UInt32 = 0
        args.count = 5;args.words = (data,4,byteCount,flags,colorKey,0,0,0)
        let h = ClawGameImageHost(heap:sourceHost,serviceContext:Unmanaged.passUnretained(self).toOpaque(),service:nativeDisplayImageDependency)
        let done = withUnsafeMutablePointer(to:&localFault){p -> UInt32 in
            let old = imageFault;imageFault = p;defer {imageFault = old}
            return heap.withStableFreedStorage {claw_game_image_entry(0x4bc520,palette.backendManagerToken,args,context.pointee.image,h,p,&out)}
        };lastPCXFault = localFault;return done == 1 && localFault == 0 ? out:0
    }
    // Resource-registry image wrapper -> the existing whole GameImage owner.
    // Its surface factory and PCX/PID decoder share this display and scene heap.
    func loadMenuResourceImage(_ receiver:UInt32,args:[UInt32])->UInt32? {
        guard !closed,!finished,args.count == 4,[UInt32(2),4].contains(args[1]),args[2] <= 4<<20 else {return nil}
        let old = pcxInput;pcxInput = (args[0],args[2]);defer {pcxInput = old}
        var a = ClawGameImageArguments(),out:UInt32 = 0,localFault:UInt32 = 0
        a.count = 4
        withUnsafeMutableBytes(of:&a.words){dst in args.withUnsafeBytes{dst.copyBytes(from:$0)}}
        let h = ClawGameImageHost(heap:sourceHost,serviceContext:Unmanaged.passUnretained(self).toOpaque(),service:nativeDisplayImageDependency)
        let done = withUnsafeMutablePointer(to:&localFault){p -> UInt32 in
            let previous = imageFault;imageFault = p;defer {imageFault = previous}
            return heap.withStableFreedStorage {claw_game_image_entry(0x4d2410,receiver,a,context.pointee.image,h,p,&out)}
        }
        lastPCXFault = localFault
        return done == 1 && localFault == 0 ? out:nil
    }
    // Canonical resource destruction frees the buffers created by GameImage.
    // The display ledger remains authoritative; foreign or repeated frees fail.
    func adoptMenuAllocation(_ token:UInt32,bytes:UInt32)->Bool {
        guard !closed,!finished,!sourceAllocations.contains(token),heap.allocationIdentity(at:token,count:bytes) != nil else {return false}
        sourceAllocations.insert(token);return true
    }
    func releaseMenuImageAllocation(_ token:UInt32)->Bool {
        guard !closed,!finished,sourceAllocations.remove(token) != nil else {return false}
        heap.free(token);return true
    }
    @discardableResult func surfaceOperation(_ f:UInt32,surface:UInt32,args:[UInt32],destination:[UInt32]? = nil,source:[UInt32]? = nil)->UInt32 {
        guard !closed,!finished,args.count <= 5,destination == nil || destination!.count == 4,
              source == nil || source!.count == (f == 0x4b9950 ? 2:4) else {lastSurfaceFault = 2;return 0}
        lastSurfaceFault = 0
        var a = ClawSurfaceBlitArguments(),c = ClawSurfaceBlitContext(),out:UInt32 = 0
        a.count = UInt32(args.count)
        withUnsafeMutableBytes(of:&a.words){dst in args.withUnsafeBytes {src in dst.copyBytes(from:src)}}
        c.scene = sourceHost;c.image = context.pointee.image;c.maximumOperations = 1000000
        var dest = destination ?? [],src = source ?? []
        let done = dest.withUnsafeMutableBufferPointer {d in src.withUnsafeMutableBufferPointer {s in
            a.destination = destination == nil ? nil:d.baseAddress;a.source = source == nil ? nil:s.baseAddress
            return heap.withStableFreedStorage {claw_surface_blit_entry(f,surface,a,&c,nativeDisplaySurfaceDependency,Unmanaged.passUnretained(self).toOpaque(),&out)}
        }};lastSurfaceFault = c.fault;if done != 1,lastSurfaceFault == 0 {lastSurfaceFault = 1};return out
    }
    func removeSurface(_ token:UInt32) {
        guard !closed,!finished else {return}
        _ = entry(0x4bc4f0,receiver:palette.backendManagerToken,args:[token])
    }
    // Finite display boundary for StateFive. In particular its frame method
    // calls IDirectDrawSurface::IsLost through slot +96. Native indexed
    // storage stays resident until the display transport is retired.
    // nil means this owner does not serve the call; the menu host must route
    // it to its actual owner or fault, never treat it as successful.
    func menuDisplayService(_ q:ClawStateFiveCall)->UInt32? {
        guard [Self.isLost,0x4b9d80,0x4b98b0].contains(q.function) else {return nil}
        guard !closed,!finished else {lastSurfaceFault = 3;return 0x80070057}
        guard q.localMask == 0,q.bufferCount == 0,q.argumentCount <= 5 else {
            lastSurfaceFault = 2;return 0x80070057
        }
        let a = withUnsafeBytes(of:q.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(q.argumentCount)))}
        switch q.function {
        case Self.isLost:
            calls[q.function,default:0] &+= 1
            guard a.count == 1,q.receiver == 0,interfaces[a[0]] != nil else {return 0x80070057}
            observePhysical?(["service":"IDirectDrawSurface::IsLost","object":a[0]])
            return 0
        case 0x4b98b0:
            guard a.count == 1 else {lastSurfaceFault = 2;return 0x80070057}
            return flipSurface(q.receiver,source:a[0])
        default:
            guard a.count == 5 else {lastSurfaceFault = 2;return 0x80070057}
            return surfaceOperation(q.function,surface:q.receiver,args:a)
        }
    }
    // Canonical callers already keep automatic buffers in the shared heap.
    // Adapt their physical packet without copying or replacing game state.
    private func menuTextService(_ q:ClawCall)->UInt32? {
        guard [Self.getDC,Self.releaseDC,0x546888,0x546880,0x546884,0x546d30,0x546890,Self.selectObject].contains(q.function) else {return nil}
        let a = withUnsafeBytes(of:q.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(q.argumentCount)))}
        func reject(_ line:Int = #line)->UInt32 {textFailureLine = line;fault = 1;unresolved.insert(q.function);return 0x80070057}
        guard !finished,q.receiver == 0 else {return reject()}
        if q.function == Self.getDC {
            guard a.count == 2,menuFont != nil,interfaces[a[0]] != nil,
                  !textDCs.values.contains(where:{$0.surface == a[0]}),
                  let output = heap.lookup(a[1],words:1),palette.currentRGB != nil else {return reject()}
            let dc = own(4);textDCs[dc] = TextDC(surface:a[0]);output.pointee = dc
            observePhysical?(["service":"IDirectDrawSurface::GetDC","object":a[0],"dc":dc]);return 0
        }
        if q.function == Self.releaseDC {
            guard a.count == 2,let dc = textDCs[a[1]],dc.surface == a[0],let surface = interfaces[a[0]],
                  let pixels = heap.lookupBytes(surface.pixels,count:surface.descriptor[4]*surface.descriptor[2]) else {return reject()}
            textDCs.removeValue(forKey:a[1]);heap.free(a[1]);transportTokens.remove(a[1])
            observePhysical?(["service":"IDirectDrawSurface::ReleaseDC","object":a[0],"dc":a[1],
                              "pixels":Data(bytes:pixels,count:Int(surface.descriptor[4]*surface.descriptor[2]))])
            wrotePrimary(a[0],["service":"IDirectDrawSurface::ReleaseDC"]);return 0
        }
        guard a.count == (q.function == 0x546d30 || q.function == 0x546890 ? 5:2),var dc = textDCs[a[0]] else {return reject()}
        if q.function == 0x546884 {
            guard a[1] == 0 || regions[a[1]] != nil else {return reject()}
            dc.clip = regions[a[1]];textDCs[a[0]] = dc
            recordCredits(["service":"SelectClipRgn","selected":a[1] != 0])
            observePhysical?(["service":"SelectClipRgn","dc":a[0],"region":a[1]])
            return dc.clip.map {$0[2] <= $0[0] || $0[3] <= $0[1] ? 1:2} ?? 2
        }
        if q.function == 0x546888 {
            guard a[1] == 1 || a[1] == 2 else {return reject()}
            let old = dc.background;dc.background = a[1];textDCs[a[0]] = dc
            observePhysical?(["service":"SetBkMode","dc":a[0],"previous":old,"value":a[1]]);return old
        }
        if q.function == 0x546880 {
            guard a[1] <= 0xffffff else {return reject()}
            let old = dc.color;dc.color = a[1];textDCs[a[0]] = dc
            observePhysical?(["service":"SetTextColor","dc":a[0],"previous":old,"value":a[1]]);return old
        }
        if q.function == Self.selectObject {
            // SelectObject(hdc, font): the in-game message overlay (0x422640,
            // 0x4226b0, 0x422810) selects its CreateFontA font around DrawTextA
            // and restores the previous object. Only fonts are served here.
            if stockFont == 0 {stockFont = own(4)}
            guard a[1] == stockFont || fonts.contains(a[1]) else {return reject()}
            let old = dc.font == 0 ? stockFont:dc.font
            dc.font = a[1] == stockFont ? 0:a[1];textDCs[a[0]] = dc
            observePhysical?(["service":"SelectObject","dc":a[0],"previous":old,"value":a[1]]);return old
        }
        // DrawTextA flags served: DT_CENTER 1, DT_RIGHT 2, DT_WORDBREAK 0x10,
        // DT_SINGLELINE 0x20, DT_VCENTER 4, DT_EXPANDTABS 0x40 and
        // DT_CALCRECT 0x400. Region clipping belongs to the DC, not the text.
        // TextOutA(hdc, x, y, text, count) (the 0x46c2c0 debug line of MPFPS, MPPOS
        // and MPOBJECTS) draws one unclipped line from (x, y) in the default top-left
        // alignment: served as a single line clipped only by the surface, '&' literal.
        let textOut = q.function == 0x546890
        let flags = textOut ? 0x20:a[4],single = flags&0x20 != 0
        let textPointer = textOut ? a[3]:a[1],length = textOut ? a[4]:a[2]
        let calculating = flags&0x400 != 0
        guard let font = menuFont,(dc.background == 1 || calculating),flags & ~UInt32(0x477) == 0,flags&3 != 3,
              length == .max && !textOut || length <= 65536,
              let surface = interfaces[dc.surface],let rgb = palette.currentRGB else {return reject()}
        var codes:[UInt8] = []
        for offset in 0..<(length == .max ? 65537:Int(length)) {
            guard let byte = heap.lookupBytes(textPointer+UInt32(offset),count:1) else {return reject()}
            if length == .max,byte.pointee == 0 {break}
            guard offset < 65536,(32...126).contains(byte.pointee) || (!single && (byte.pointee == 10 || byte.pointee == 13)) || (flags&0x40 != 0 && byte.pointee == 9),
                  textOut || byte.pointee != 38 else {return reject()}
            codes.append(byte.pointee)
        }
        let r:[Int]
        if textOut {
            let x = Int(Int32(bitPattern:a[1])),y = Int(Int32(bitPattern:a[2]))
            r = [x,y,max(x,Int(surface.descriptor[3])),max(y,Int(surface.descriptor[2]))]
        } else {
            guard let rect = heap.lookup(a[3],words:4) else {return reject()}
            r = (0..<4).map{Int(Int32(bitPattern:rect[$0]))}
        }
        guard r[0] >= -65536,r[0] <= r[2],r[2] <= 65536,r[1] >= -65536,r[1] <= r[3],r[3] <= 65536 else {return reject()}
        if flags&0x40 != 0 {
            var expanded:[UInt8] = [],column = 0
            for code in codes {
                if code == 9 {let count = 8-column%8;expanded += Array(repeating:32,count:count);column += count}
                else {expanded.append(code);column = code == 10 || code == 13 ? 0:column+1}
            }
            codes = expanded
        }
        func measure(_ line:ArraySlice<UInt8>)->Int {line.reduce(0){$0+font.glyphs[String($1)]!.measureAdvance}}
        // Lines: CR LF / LF break unless single-line; DT_WORDBREAK wraps at
        // spaces when a word would cross the rectangle's right edge.
        var lines:[ArraySlice<UInt8>] = []
        for raw in (single ? [codes[...]]:codes.split(separator:10,omittingEmptySubsequences:false)) {
            let text = raw.last == 13 ? raw.dropLast():raw
            guard flags&0x10 != 0,measure(text) > r[2]-r[0] else {lines.append(text);continue}
            var start = text.startIndex,lastBreak:Int? = nil,index = text.startIndex
            while index < text.endIndex {
                if text[index] == 32 {lastBreak = index}
                if measure(text[start...index]) > r[2]-r[0],let cut = lastBreak,cut > start {
                    lines.append(text[start..<cut]);start = cut+1;lastBreak = nil;index = start;continue
                }
                index += 1
            }
            lines.append(text[start..<text.endIndex])
        }
        if calculating {
            guard let rect = heap.lookup(a[3],words:4) else {return reject()}
            rect[2] = UInt32(bitPattern:Int32(r[0]+(lines.map{measure($0)}.max() ?? 0)))
            rect[3] = UInt32(bitPattern:Int32(r[1]+font.height*lines.count))
            recordCredits(["service":"DrawTextA","flags":flags,"lines":lines.count,"height":font.height*lines.count,
                                    "rectangle":[r[0],r[1],Int(Int32(bitPattern:rect[2])),Int(Int32(bitPattern:rect[3]))]])
            observePhysical?(["service":"DrawTextA","dc":a[0],"flags":flags,"lines":lines.count,"height":font.height*lines.count,"calculated":true])
            return codes.isEmpty ? 0:UInt32(font.height*lines.count)
        }
        let height = Int(surface.descriptor[2]),stride = Int(surface.descriptor[4]),surfaceWidth = Int(surface.descriptor[3])
        guard let pixels = heap.lookupBytes(surface.pixels,count:UInt32(stride*height)) else {return reject()}
        let color = (0..<3).map{Int((dc.color >> ($0*8))&255)}
        let index = (0..<256).min {lhs,rhs in
            func distance(_ i:Int)->Int {(0..<3).reduce(0){sum,c in let d = Int(rgb[i*3+c])-color[c];return sum+d*d}}
            return distance(lhs) < distance(rhs)
        }!
        for (number,line) in lines.enumerated() {
            let glyphs = line.map{font.glyphs[String($0)]!}
            let width = measure(line),top = glyphs.map(\.top).min() ?? 0
            let lineTop = r[1]+number*font.height+(single && flags&4 != 0 ? (r[3]-r[1]-font.height)/2:0)
            var x = flags&2 != 0 ? r[2]-width:flags&1 != 0 ? r[0]+(r[2]-r[0]-width)/2:r[0]
            for (position,glyph) in glyphs.enumerated() {
                let bearing = min(0,glyph.leftBearing ?? 0)
                for row in 0..<32 {
                    let y = lineTop+row-top
                    guard y >= max(0,r[1],dc.clip?[1] ?? 0),y < min(height,r[3],dc.clip?[3] ?? height) else {continue}
                    for column in 0..<32 where glyph.pixels[row*32+column] != 0 {
                        let at = x+column-8-(position == 0 ? 0:bearing)
                        if at >= max(0,r[0],dc.clip?[0] ?? 0),at < min(surfaceWidth,r[2],dc.clip?[2] ?? surfaceWidth) {pixels[y*stride+at] = UInt8(index)}
                    }
                }
                x += glyph.advance+(position == 0 ? bearing:0)
            }
        }
        observePhysical?(["service":textOut ? "TextOutA":"DrawTextA","dc":a[0],"text":String(decoding:codes,as:UTF8.self),
                          "rectangle":r,"flags":a[4],"palette_index":index,"font":dc.font,"lines":lines.count,
                          "pixels":Data(bytes:pixels,count:stride*height)])
        if flags == 0x50 {
            recordCredits(["service":"DrawTextA","flags":flags,"lines":lines.count,"height":font.height*lines.count,"rectangle":r])
        }
        if textOut {return 1}
        return codes.isEmpty ? 0:UInt32(font.height*lines.count)
    }
    // MARK: - Menu physical services

    // Keep the preceding text service at its existing line positions: its
    // #line default argument is part of the recorded failure diagnostics.
    func menuPhysicalService(_ q: ClawCall) -> UInt32? {
        let a = withUnsafeBytes(of: q.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(q.argumentCount))) }
        if q.function == 0x54688c, q.receiver == 0, a.count == 4 {
            let handle = own(4)
            regions[handle] = a.map { Int(Int32(bitPattern: $0)) }
            recordCredits(["service": "CreateRectRgn", "rectangle": regions[handle]!])
            observePhysical?(["service": "CreateRectRgn", "region": handle, "rectangle": regions[handle]!])
            return handle
        }
        if q.function == 0x4fd6db, a.count == 1, regions[a[0]] != nil,
            let object = heap.lookup(q.receiver, words: 2), object[1] == 0
        {
            recordCredits(["service": "CGdiObject::Attach"])
            object[1] = a[0]
            return 1
        }
        if q.function == 0x4fd732, a.isEmpty, let object = heap.lookup(q.receiver, words: 2) {
            let handle = object[1]
            guard handle == 0 || regions[handle] != nil else { return nil }
            if handle == 0 { return 0 }
            recordCredits(["service": "CGdiObject::DeleteObject"])
            regions.removeValue(forKey: handle)
            heap.free(handle)
            transportTokens.remove(handle)
            object[1] = 0
            return 1
        }
        if let result = menuTextService(q) { return result }
        guard q.receiver == 0, q.argumentCount <= 8 else { return nil }
        if q.function == Self.isLost {
            var call = ClawStateFiveCall()
            call.function = q.function
            call.argumentCount = q.argumentCount
            call.arguments.0 = q.arguments.0
            return menuDisplayService(call)
        }
        if [Self.flip, Self.setColorKey, Self.blt, Self.bltFast].contains(q.function) {
            var call = ClawSurfaceBlitCall()
            call.function = q.function
            call.argumentCount = q.argumentCount
            withUnsafeMutableBytes(of: &call.arguments) { dst in
                withUnsafeBytes(of: q.arguments) { dst.copyBytes(from: $0.prefix(dst.count)) }
            }
            return surfaceService(call)
        }
        if [Self.create, Self.attached, Self.describe, Self.lock, Self.unlock, Self.release].contains(q.function) {
            var call = ClawSceneDisplayCall()
            call.function = q.function
            call.argumentCount = q.argumentCount
            withUnsafeMutableBytes(of: &call.arguments) { dst in
                withUnsafeBytes(of: q.arguments) { dst.copyBytes(from: $0.prefix(dst.count)) }
            }
            return service(call)
        }
        return nil
    }
    func menuListService(_ q: ClawCall) -> UInt32? {
        guard q.receiver >= palette.backendManagerToken, q.receiver + 28 <= palette.backendManagerToken + 2180,
            [UInt32(0x4f51c5), 0x4f5212, 0x4f5172].contains(q.function), q.argumentCount <= 1
        else { return nil }
        var c = ClawAmbientAudioBackendContext(scene: sourceHost, maximumTraversal: 1000000, fault: 0), out: UInt32 = 0
        var argument = q.arguments.0
        let done = claw_ambient_audio_backend_entry(
            q.function, q.receiver, &argument, q.argumentCount, &c, nativeDisplayListDependency,
            Unmanaged.passUnretained(self).toOpaque(), &out)
        if done != 1 || c.fault != 0 { fault = c.fault == 0 ? 2 : c.fault }
        return out
    }
    @discardableResult func flipSurface(_ surface: UInt32, source: UInt32 = 0) -> UInt32 {
        guard !closed, !finished else {
            lastSurfaceFault = 3
            return 0
        }
        lastSurfaceFault = 0
        var blit = ClawSurfaceBlitContext(
            scene: sourceHost, pcx: nil, image: context.pointee.image, maximumOperations: 1000000, fault: 0)
        var c = ClawSurfaceFlipContext(), out: UInt32 = 0
        c.scene = sourceHost
        c.maximumOperations = 1000000
        let a = [source]
        let done = withUnsafeMutablePointer(to: &blit) { p -> UInt32 in
            c.blit = p
            return heap.withStableFreedStorage {
                a.withUnsafeBufferPointer {
                    claw_surface_flip_entry(
                        0x4b98b0, surface, $0.baseAddress, 1, &c, nativeDisplayFlipDependency,
                        Unmanaged.passUnretained(self).toOpaque(), &out)
                }
            }
        }
        lastSurfaceFault = c.fault
        if done != 1, lastSurfaceFault == 0 { lastSurfaceFault = 1 }
        return out
    }
    func surfacePixels(_ token: UInt32) -> (bytes: Data, width: UInt32, height: UInt32, stride: UInt32)? {
        guard !finished, let s = heap.lookup(token, words: 47), let d = interfaces[s[2]],
            let pixels = heap.lookup(d.pixels, words: (d.descriptor[4] * d.descriptor[2] + 3) / 4)
        else { return nil }
        //Primary presentation need not Lock first: its source cached pitch is
        //not initialized until Lock, while the physical descriptor is complete.
        return (
            Data(bytes: pixels, count: Int(d.descriptor[4] * d.descriptor[2])), d.descriptor[3], d.descriptor[2],
            d.descriptor[4]
        )
    }
    // MARK: - Raw actor and PID transport

    // Finite native service election for the admitted raw eight-bit PID entry.
    // The canonical host owns RECT/stream tokens; this display owns the actual
    // surface and indexed storage. In particular, no sprite cache is consulted.
    func rawPIDService(_ host: any ClawNativeRawDisplayHost, _ q: ClawCall) -> UInt32? {
        guard [UInt32(0x4b9730), Self.lock, Self.unlock].contains(q.function) else { return nil }
        func reject(_ code: UInt32 = UInt32(CLAW_FAULT_HOST)) -> UInt32? {
            host.rawReject(code, at: q.function)
            return nil
        }
        guard host.heap === heap, host.fault == nil, !closed, !finished, fault == 0,
            q.receiver2 == 0, q.x87ArgumentCount == 0, q.argumentCount <= 5
        else { return reject() }
        let a = withUnsafeBytes(of: q.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(q.argumentCount))) }
        if q.function == 0x4b9730 {
            guard a == [0], let s = heap.lookup(q.receiver, words: 47),
                let physical = interfaces[s[2]], physical.descriptor[21] == 8,
                let dd = heap.lookup(s[2], words: 1), let vt = heap.lookup(dd.pointee, words: 33),
                vt[25] == Self.lock, vt[32] == Self.unlock
            else { return reject() }
            var args = ClawGameImageArguments(), out: UInt32 = 0, localFault: UInt32 = 0
            args.count = 1
            let bridge = NativeDisplayRawPIDLock(host: host)
            let imageHost = ClawGameImageHost(
                heap: sourceHost,
                serviceContext: Unmanaged.passUnretained(bridge).toOpaque(),
                service: { u, call in
                    guard let u else { return 0 }
                    let bridge = Unmanaged<NativeDisplayRawPIDLock>.fromOpaque(u).takeUnretainedValue()
                    var request = ClawCall()
                    request.function = call.function
                    request.receiver = call.receiver
                    request.argumentCount = call.argumentCount
                    guard call.argumentCount <= 8, call.source == nil, call.destination == nil else {
                        bridge.host.rawReject(UInt32(CLAW_FAULT_ABI), at: call.function)
                        bridge.fault?.pointee = UInt32(CLAW_FAULT_ABI)
                        return 0
                    }
                    withUnsafeMutableBytes(of: &request.arguments) { dst in
                        withUnsafeBytes(of: call.arguments) {
                            dst.copyBytes(from: $0.prefix(Int(call.argumentCount) * 4))
                        }
                    }
                    let result = bridge.host.callNativeDependency(request)
                    if let failure = bridge.host.fault { bridge.fault?.pointee = failure.code }
                    return result ?? 0
                })
            let done = withUnsafeMutablePointer(to: &localFault) { p in
                bridge.fault = p
                defer { bridge.fault = nil }
                return claw_game_image_entry(q.function, q.receiver, args, context.pointee.image, imageHost, p, &out)
            }
            guard done == 1, localFault == 0, host.fault == nil else {
                return reject(localFault == 0 ? UInt32(CLAW_FAULT_HOST) : localFault)
            }
            return out
        }
        guard q.receiver == 0 else { return reject(UInt32(CLAW_FAULT_ABI)) }
        if q.function == Self.lock {
            guard a.count == 5, a[1] == 0, a[3] == 1, a[4] == 0,
                let physical = interfaces[a[0]], physical.descriptor[21] == 8,
                heap.lookupBytes(a[2], count: 108) != nil
            else { return reject() }
        } else {
            guard a.count == 2, a[1] == 0, let physical = interfaces[a[0]],
                physical.descriptor[21] == 8
            else { return reject() }
        }
        var call = ClawSceneDisplayCall()
        call.function = q.function
        call.receiver = q.receiver
        call.argumentCount = q.argumentCount
        withUnsafeMutableBytes(of: &call.arguments) { dst in
            withUnsafeBytes(of: q.arguments) { dst.copyBytes(from: $0.prefix(a.count * 4)) }
        }
        let result = service(call)
        guard fault == 0 else { return reject(fault) }
        return result
    }
    func drawRawPID(_ receiver: UInt32, destination: UInt32, surface: UInt32, source: UInt32)
        -> ClawNativeCanonicalHost.Completion
    {
        let host = ClawNativeCanonicalHost(
            heap: heap, dependency: { [unowned self] host, call in self.rawPIDService(host, call) })
        var call = ClawCall()
        call.function = 0x4c00b0
        call.receiver = receiver
        call.argumentCount = 3
        call.arguments.0 = destination
        call.arguments.1 = surface
        call.arguments.2 = source
        return host.invoke(call)
    }
    // Selected raw transports use the existing pixel cores. Only the bounded
    // payload-to-file envelope is synthesized; game-visible objects stay live.
    private func rawSelectedPID(_ host: any ClawNativeRawDisplayHost, _ q: ClawCall) -> UInt32? {
        func reject(_ at: UInt32) -> UInt32? {
            host.rawReject(UInt32(CLAW_FAULT_MEMORY), at: at)
            return nil
        }
        func words(_ at: UInt32, _ n: UInt32) -> UnsafeMutablePointer<UInt32>? {
            guard at & 3 == 0, UInt64(at) + UInt64(n) * 4 <= 0x100000000,
                let p = host.bytes(at, count: n * 4)
            else { return nil }
            return UnsafeMutableRawPointer(p).assumingMemoryBound(to: UInt32.self)
        }
        guard host.heap === heap, host.fault == nil, !closed, !finished, fault == 0,
            q.argumentCount == 3, q.receiver2 == 0, q.x87ArgumentCount == 0,
            q.stackPointer >= UInt32(CLAW_STACK_BASE) + 64,
            let raw = words(q.receiver, 10)
        else { return reject(q.function) }
        let normal = [UInt32(0x4c0450), 0x4c0920, 0x4c0cc0].contains(q.function)
        let flipX = [UInt32(0x4c0450), 0x4c0cc0, 0x4c25b0, 0x4c4c20].contains(q.function)
        let flipY = [UInt32(0x4c0920), 0x4c0cc0, 0x4c3800, 0x4c4c20].contains(q.function)
        // Effect bodies test table presence before even reading the surface.
        if !normal && raw[7] == 0 { return 0 }
        let destination = q.arguments.0, surface = q.arguments.1, source = q.arguments.2
        guard let sw = words(surface, 47), let physical = interfaces[sw[2]], physical.descriptor[21] == 8 else {
            return reject(surface)
        }
        let pitch = Int(Int32(bitPattern: sw[7]))
        var lock = ClawCall()
        lock.function = 0x4b9730
        lock.receiver = surface
        lock.argumentCount = 1
        guard let pixels = host.callNativeDependency(lock), host.fault == nil else { return nil }
        // Reload every field after Lock, including mode/table/RECT/payload.
        guard let r = words(q.receiver, 10), let d = words(destination, 4), let src = words(source, 4),
            let backing = interfaces.values.first(where: { $0.pixels == pixels }), backing.descriptor[21] == 8
        else { return reject(q.receiver) }
        let width = Int(Int32(bitPattern: r[1])), height = Int(Int32(bitPattern: r[2])), length = Int(r[4])
        guard width > 0, height > 0, width <= 4096, height <= 4096, pitch > 0,
            length > 0, length <= 0x2000000, normal ? r[9] & 255 == 1 : true,
            Int32(bitPattern: src[0]) >= 0, Int(src[0]) < width,
            Int32(bitPattern: src[1]) >= 0, Int(src[1]) < height,
            Int32(bitPattern: src[2]) < width, Int32(bitPattern: src[3]) < height,
            let payload = host.bytes(r[3], count: r[4])
        else { return reject(q.receiver) }
        let capacity = Int(backing.descriptor[4]) * (Int(backing.descriptor[2]) + 1)
        guard capacity > 0, capacity <= 0x2000000, let output = host.bytes(pixels, count: UInt32(capacity)) else {
            return reject(pixels)
        }
        func overlaps(_ a: UInt32, _ n: Int, _ b: UInt32, _ m: Int) -> Bool {
            UInt64(a) < UInt64(b) + UInt64(m) && UInt64(b) < UInt64(a) + UInt64(n)
        }
        var protected: [(UInt32, Int)] = [
            (r[3], length), (q.receiver, 40), (destination, 16), (source, 16), (surface, 188)
        ]
        guard let currentDD = words(sw[2], 1), let _ = words(currentDD.pointee, 33) else { return reject(surface) }
        protected += [(sw[2], 4), (currentDD.pointee, 132)]
        var command = ClawPIDBlitCommand(
            destination: ClawPIDBlitRect(
                left: Int32(bitPattern: d[0]), top: Int32(bitPattern: d[1]), right: Int32(bitPattern: d[2]),
                bottom: Int32(bitPattern: d[3])),
            source: ClawPIDBlitRect(
                left: Int32(bitPattern: src[0]), top: Int32(bitPattern: src[1]), right: Int32(bitPattern: src[2]),
                bottom: Int32(bitPattern: src[3])),
            flipX: flipX ? 1 : 0, flipY: flipY ? 1 : 0, originalSourceRectAddress: source)
        var state = ClawLightPIDBlitState(
            renderWord: r[0], effectMode: normal ? 1 : r[5], effectValue: r[6], formatByte: 1, bothTopSkipSeed: 0)
        if q.function == 0x4c4c20 && src[1] != 0 {
            guard let seed = words(q.stackPointer - 36, 1) else { return reject(q.stackPointer - 36) }
            state.bothTopSkipSeed = seed.pointee
        }
        var table = ClawLightPIDBlitTable()
        var scratch: UnsafeMutablePointer<UInt8>?
        if !normal {
            guard let t = words(r[7], 3), let storage = host.bytes(0x542bb0, count: 129) else { return reject(r[7]) }
            scratch = storage
            table.words = (t[0], t[1], t[2])
            protected.append((r[7], 12))
            if [UInt32(2), 4, 8, 50].contains(state.effectMode) {
                // Table length/active words are ignored by the original. Bound
                // reads by the actual mapped span, not either metadata word.
                var lo = 0, hi = 0x100000
                while lo < hi {
                    let mid = (lo + hi + 1) / 2
                    if heap.lookupBytes(t[2], count: UInt32(mid)) != nil { lo = mid } else { hi = mid - 1 }
                }
                guard lo > 0, let data = host.bytes(t[2], count: UInt32(lo)) else { return reject(t[2]) }
                table.data = UnsafePointer(data)
                table.capacity = lo
                protected.append((t[2], lo))
            }
        }
        guard !protected.contains(where: { overlaps(pixels, capacity, $0.0, $0.1) }),
            (normal || !overlaps(pixels, capacity, 0x542bb0, 129)),
            !protected.contains(where: { !normal && overlaps(0x542bb0, 129, $0.0, $0.1) })
        else { return reject(pixels) }
        var file = [UInt8](repeating: 0, count: 32 + length)
        let header: [UInt32] = [10, 32, UInt32(width), UInt32(height), 0, 0, 0, 0]
        header.withUnsafeBytes { bytes in file.withUnsafeMutableBytes { $0.copyBytes(from: bytes) } }
        file.withUnsafeMutableBufferPointer { $0.baseAddress!.advanced(by: 32).update(from: payload, count: length) }
        var info = ClawLightPIDBlitInfo()
        // Unknown effects (including a post-lock change to mode 1) consume runs
        // but perform no literal writes in the selected effect body. Validate
        // the same stream/bounds with a private mode-22 destination, then discard.
        let noWrite = !normal && ![UInt32(2), 4, 8, 22, 50].contains(state.effectMode)
        var dry = noWrite ? Array(UnsafeBufferPointer(start: output, count: capacity)) : []
        if noWrite { state.effectMode = 22 }
        let done = file.withUnsafeBufferPointer { input in
            withUnsafePointer(to: &table) { t in
                if noWrite {
                    return dry.withUnsafeMutableBufferPointer { out in
                        claw_effect_pid_blit8(
                            input.baseAddress, input.count, &command, &state, t, out.baseAddress, nil, capacity, pitch,
                            scratch, 129, &info)
                    }
                }
                return claw_effect_pid_blit8(
                    input.baseAddress, input.count, &command, &state, normal ? nil : t, output, nil, capacity, pitch,
                    scratch, 129, &info)
            }
        }
        guard done == 1 else { return reject(q.receiver) }
        // The selected target, not a cached interface, owns the final COM call.
        guard let finalSurface = words(surface, 3), let dd = words(finalSurface[2], 1), let vt = words(dd.pointee, 33)
        else { return reject(surface) }
        var unlock = ClawCall()
        unlock.function = vt[32]
        unlock.argumentCount = 2
        unlock.arguments.0 = finalSurface[2]
        _ = host.callNativeDependency(unlock)
        return host.fault == nil ? 0 : nil
    }
    // Exact raw actor connection. The unconditional helper does not inherit
    // visibility, blink or flip selection from the composed actor dispatcher.
    func rawActorService(_ host: any ClawNativeRawDisplayHost, _ q: ClawCall) -> UInt32? {
        if [UInt32(0x4c0450), 0x4c0920, 0x4c0cc0, 0x4c1190, 0x4c25b0, 0x4c3800, 0x4c4c20].contains(q.function) {
            return rawSelectedPID(host, q)
        }
        guard [UInt32(0x4c96d0), 0x546d58, 0x4bffa0].contains(q.function) else {
            return rawPIDService(host, q)
        }
        guard host.heap === heap, host.fault == nil, !closed, !finished, fault == 0,
            q.receiver2 == 0, q.x87ArgumentCount == 0
        else {
            host.rawReject(UInt32(CLAW_FAULT_HOST), at: q.function)
            return nil
        }
        func words(_ token: UInt32, _ count: UInt32) -> UnsafeMutablePointer<UInt32>? {
            guard token & 3 == 0, let p = host.bytes(token, count: count * 4) else {
                host.rawReject(UInt32(CLAW_FAULT_MEMORY), at: token)
                return nil
            }
            return UnsafeMutableRawPointer(p).assumingMemoryBound(to: UInt32.self)
        }
        guard q.argumentCount <= UInt32(CLAW_CALL_ARGUMENT_CAPACITY) else {
            host.rawReject(UInt32(CLAW_FAULT_ABI), at: q.function)
            return nil
        }
        let a = withUnsafeBytes(of: q.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(q.argumentCount))) }
        switch q.function {
        case 0x4c96d0:
            guard a.count == 2, let p = words(q.receiver, 22), let x = words(a[0], 1), let y = words(a[1], 1) else {
                host.rawReject(UInt32(CLAW_FAULT_ABI), at: q.function)
                return nil
            }
            var projection = ClawSpriteProjection(
                flags: p[2], extentX: p[12], extentY: p[13], cameraX: p[16], cameraY: p[17],
                visibleEndX: p[18], visibleEndY: p[19], screenOffsetX: p[20], screenOffsetY: p[21])
            claw_sprite_project(&projection, x, y)
            return 0
        case 0x546d58:
            guard q.receiver == 0, a.count == 2, let src = words(a[1], 4), let dst = words(a[0], 4) else {
                host.rawReject(UInt32(CLAW_FAULT_ABI), at: q.function)
                return nil
            }
            let copy = Array(UnsafeBufferPointer(start: src, count: 4))
            copy.withUnsafeBufferPointer { dst.update(from: $0.baseAddress!, count: 4) }
            return 1
        default:
            guard a.count == 5, q.stackPointer >= UInt32(CLAW_STACK_BASE) + 20,
                let src = words(a[2], 4), let image = words(q.receiver, 10)
            else {
                host.rawReject(UInt32(CLAW_FAULT_ABI), at: q.function)
                return nil
            }
            // Original dispatcher rejection precedes effect/format selection.
            if Int32(bitPattern: src[0]) < 0 || Int32(bitPattern: src[2]) > Int32(bitPattern: image[1] &- 1)
                || Int32(bitPattern: src[1]) < 0 || Int32(bitPattern: src[1]) > Int32(bitPattern: image[2] &- 1)
            {
                return 0
            }
            // CrazyHook's two-table flag 7 requires a 16-bit destination;
            // this native indexed renderer matches its pre-lock rejection.
            if image[5] == 7 {return 0}
            if image[5] == 0x43480008 {return customIndexedBlob(host,q)}
            let normal = image[5] == 1
            if !normal && image[9] & 255 != 1 { return 0 }
            let target: UInt32 =
                normal
                ? (a[3] != 0 ? (a[4] != 0 ? 0x4c0cc0 : 0x4c0450) : (a[4] != 0 ? 0x4c0920 : 0x4c00b0))
                : (a[3] != 0 ? (a[4] != 0 ? 0x4c4c20 : 0x4c25b0) : (a[4] != 0 ? 0x4c3800 : 0x4c1190))
            // PUSH ESI, three arguments, CALL: preserve the original child ESP.
            var child = ClawCall()
            child.function = target
            child.receiver = q.receiver
            child.argumentCount = 3
            child.arguments.0 = a[0]
            child.arguments.1 = a[1]
            child.arguments.2 = a[2]
            child.stackPointer = q.stackPointer - 20
            _ = host.callNativeDependency(child)
            return host.fault == nil ? 1 : nil
        }
    }
    // The release's Blob effect always blends packed words, including on an
    // indexed target. Zero RGB masks make its component tables all zero. Keep
    // the word footprints and stream traversal, bounded by the native buffers.
    private func customIndexedBlob(_ host:any ClawNativeRawDisplayHost,_ q:ClawCall)->UInt32? {
        func reject()->UInt32? {host.rawReject(UInt32(CLAW_FAULT_MEMORY),at:q.receiver);return nil}
        guard let r = heap.lookup(q.receiver,words:10),let s = heap.lookup(q.arguments.1,words:47),
              let physical = interfaces[s[2]],physical.descriptor[21] == 8,
              physical.descriptor[22...24].allSatisfy({$0 == 0}),
              let source = heap.lookup(q.arguments.2,words:4),let destination = heap.lookup(q.arguments.0,words:4),
              r[9]&255 == 1,r[1] > 0,r[1] <= 4096,r[2] > 0,r[2] <= 4096,r[4] > 0,r[4] <= 0x2000000,
              let input = host.bytes(r[3],count:r[4]) else {return reject()}
        let length = Int(r[4]),width = Int(r[1]),height = Int(r[2])
        // Validate the declared stream before allowing padded WORD reads.
        var cursor = 0
        for _ in 0..<height {
            var x = 0
            while x < width {
                guard cursor < length else {return reject()}
                let command = Int(input[cursor]);cursor += 1
                let count = command&127
                guard count > 0,count <= width-x else {return reject()}
                if command < 128 {guard count <= length-cursor else {return reject()};cursor += count}
                x += count
            }
        }
        var readable = length
        while readable < length+128 && heap.lookupBytes(r[3],count:UInt32(readable+1)) != nil {readable += 1}
        let payload = Array(UnsafeBufferPointer(start:input,count:readable))
        let src = (0..<4).map {Int(Int32(bitPattern:source[$0]))},dst = (0..<4).map {Int(Int32(bitPattern:destination[$0]))}
        let capacity = Int(physical.descriptor[4])*(Int(physical.descriptor[2])+1)
        var lock = ClawCall();lock.function = 0x4b9730;lock.receiver = q.arguments.1;lock.argumentCount = 1
        guard let pixels = host.callNativeDependency(lock),host.fault == nil,pixels == physical.pixels else {return reject()}
        guard capacity > 0,capacity <= 0x2000000,
              let ranges = ClawCustomBlob.ranges(payload:payload,width:width,height:height,source:src,destination:dst,
                  pitch:Int(Int32(bitPattern:s[7])),capacity:capacity,flipX:q.arguments.3 != 0,flipY:q.arguments.4 != 0,paired:r[0] != 0),
              let output = host.bytes(pixels,count:UInt32(capacity)) else {return reject()}
        for range in ranges {output.advanced(by:range.lowerBound).initialize(repeating:0,count:range.count)}
        guard let dd = heap.lookup(s[2],words:1),let vt = heap.lookup(dd.pointee,words:33) else {return reject()}
        var unlock = ClawCall();unlock.function = vt[32];unlock.argumentCount = 2;unlock.arguments.0 = s[2]
        _ = host.callNativeDependency(unlock)
        return host.fault == nil ? 1:nil
    }
    func drawRawActor(_ image: UInt32, actor: UInt32, target: UInt32) -> ClawNativeCanonicalHost.Completion {
        let host = ClawNativeCanonicalHost(
            heap: heap, dependency: { [unowned self] host, call in self.rawActorService(host, call) })
        var call = ClawCall()
        call.function = 0x4d32e0
        call.receiver = image
        call.argumentCount = 2
        call.arguments.0 = actor
        call.arguments.1 = target
        return host.invoke(call)
    }
    // MARK: - Image decoding and source dispatch

    func decodePCX(surface: UInt32, data: UInt32, byteCount: UInt32) -> UInt32 {
        guard !closed, !finished else {
            lastPCXFault = 3
            return 0
        }
        guard byteCount <= 4 << 20 else {
            lastPCXFault = 2
            return 0
        }
        let oldInput = pcxInput
        pcxInput = (data, byteCount)
        defer { pcxInput = oldInput }
        var c = ClawPCXImageContext(), out: UInt32 = 0
        c.scene = context.pointee.scene
        c.byteContext = Unmanaged.passUnretained(self).toOpaque()
        c.bytes = { u, t, n in
            guard let u else { return nil }
            return Unmanaged<ClawNativeDisplay>.fromOpaque(u).takeUnretainedValue().pcxBytes(t, count: n)
        }
        c.image = context.pointee.image
        c.composeImage = 1
        c.maximumOperations = 100000000
        let a: [UInt32] = [palette.backendManagerToken, data, byteCount]
        let done = heap.withStableFreedStorage {
            a.withUnsafeBufferPointer {
                claw_pcx_image_entry(
                    0x4bebc0, surface, $0.baseAddress, 3, &c, nativeDisplayPCXDependency,
                    Unmanaged.passUnretained(self).toOpaque(), &out)
            }
        }
        lastPCXFault = c.fault
        if done == 1, c.fault == 0 {
            pcxLoads &+= 1
            return out
        }
        return 0
    }
    private func pcxBytes(_ token: UInt32, count: UInt32) -> UnsafeMutablePointer<UInt8>? {
        guard !finished else { return nil }
        if let input = pcxInput, token >= input.token,
            UInt64(token) <= UInt64(input.token) + UInt64((input.bytes + 3) & ~3),
            UInt64(token) + UInt64(count) > UInt64(input.token) + UInt64(input.bytes)
        {
            return nil
        }
        let offset = token & 3
        guard UInt64(offset) + UInt64(count) + 3 <= UInt64(UInt32.max),
            let p = heap.lookup(token & ~3, words: (offset + count + 3) / 4)
        else { return nil }
        return UnsafeMutableRawPointer(p).assumingMemoryBound(to: UInt8.self).advanced(by: Int(offset))
    }
    fileprivate func pcxService(_ q: ClawPCXImageCall) -> UInt32 {
        guard q.source == nil, q.destination == nil else {
            fault = 2
            return 0
        }
        var e = ClawSceneDisplayCall()
        e.function = q.function
        e.receiver = q.receiver
        e.argumentCount = q.argumentCount
        e.arguments = q.arguments
        return service(e)
    }
    fileprivate func imageService(_ q: ClawGameImageCall) -> UInt32 {
        if q.function == 0x4be810 {
            var c = ClawPCXImageContext(), out: UInt32 = 0
            c.scene = sourceHost
            c.byteContext = Unmanaged.passUnretained(self).toOpaque()
            c.bytes = { u, t, n in
                guard let u else { return nil }
                return Unmanaged<ClawNativeDisplay>.fromOpaque(u).takeUnretainedValue().pcxBytes(t, count: n)
            }
            c.image = context.pointee.image
            c.composeImage = 1
            c.maximumOperations = 100000000
            let a = withUnsafeBytes(of: q.arguments) {
                Array($0.bindMemory(to: UInt32.self).prefix(Int(q.argumentCount)))
            }
            let done = a.withUnsafeBufferPointer {
                claw_pcx_creation_entry(
                    q.receiver, $0.baseAddress, UInt32($0.count), &c, nativeDisplayPCXDependency,
                    Unmanaged.passUnretained(self).toOpaque(), &out)
            }
            if done != 1 || c.fault != 0 {
                imageFault?.pointee = c.fault == 0 ? 2 : c.fault
                return 0
            }
            return out
        }
        let a = withUnsafeBytes(of: q.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(q.argumentCount))) }
        if q.function == 0x4f51c5 {
            var c = ClawAmbientAudioBackendContext(scene: sourceHost, maximumTraversal: 1000000, fault: 0),
                out: UInt32 = 0
            let done = a.withUnsafeBufferPointer {
                claw_ambient_audio_backend_entry(
                    q.function, q.receiver, $0.baseAddress, UInt32($0.count), &c, nativeDisplayListDependency,
                    Unmanaged.passUnretained(self).toOpaque(), &out)
            }
            if done != 1 || c.fault != 0 {
                imageFault?.pointee = c.fault == 0 ? 2 : c.fault
                return 0
            }
            return out
        }
        if [0x4b9ce0, 0x4b9d80, 0x4b9950].contains(q.function) {
            let d = q.destination.map { Array(UnsafeBufferPointer(start: $0, count: 4)) }
            let s = q.source.map { Array(UnsafeBufferPointer(start: $0, count: q.function == 0x4b9950 ? 2 : 4)) }
            let out = surfaceOperation(q.function, surface: q.receiver, args: a, destination: d, source: s)
            if lastSurfaceFault != 0 { imageFault?.pointee = lastSurfaceFault }
            return out
        }
        if q.function == Self.setColorKey {
            lastSurfaceFault = 0
            var c = ClawSurfaceBlitCall()
            c.function = q.function
            c.receiver = q.receiver
            c.argumentCount = q.argumentCount
            c.arguments = q.arguments
            if let pair = q.source {
                c.localMask = 4
                c.bufferCount = 1
                c.buffers.0 = pair
                c.bufferBytes.0 = 8
            }
            let out = surfaceService(c)
            if lastSurfaceFault != 0 { imageFault?.pointee = lastSurfaceFault }
            return out
        }
        if q.function == 0x4bc5f0 { return palette.graphicsEntry(q.function, receiver: q.receiver, args: a) }
        guard q.source == nil, q.destination == nil else {
            imageFault?.pointee = 2
            return 0
        }
        var e = ClawSceneDisplayCall()
        e.function = q.function
        e.receiver = q.receiver
        e.argumentCount = q.argumentCount
        e.arguments = q.arguments
        let out = service(e)
        if fault != 0 { imageFault?.pointee = fault }
        return out
    }
    fileprivate func listService(_ q: ClawAmbientAudioBackendCall) -> UInt32 {
        guard q.outputWord == nil, q.argumentCount <= 6 else {
            fault = 2
            return 0
        }
        var e = ClawSceneDisplayCall()
        e.function = q.function
        e.receiver = q.receiver
        e.argumentCount = q.argumentCount
        withUnsafeMutableBytes(of: &e.arguments) { dest in
            withUnsafeBytes(of: q.arguments) { src in dest.copyBytes(from: src.prefix(Int(q.argumentCount) * 4)) }
        }
        return service(e)
    }
    @discardableResult func entry(_ f: UInt32, receiver: UInt32, args: [UInt32] = []) -> UInt32 {
        guard !finished else {
            fault = 3
            return 0
        }
        palette.importGraphicsAliases()
        var out: UInt32 = 0
        let accepted = heap.withStableFreedStorage {
            args.withUnsafeBufferPointer {
                claw_scene_display_entry(
                    f, receiver, $0.baseAddress, UInt32($0.count), context, nativeDisplayDependency,
                    Unmanaged.passUnretained(self).toOpaque(), &out)
            }
        }
        palette.publishGraphicsAliases()
        fault = max(fault, context.pointee.fault)
        if accepted != 1 {
            unresolved.insert(f)
            fault = max(fault, 1)
        }
        return out
    }
    // MARK: - Source shutdown and transport retirement

    func shutdown() {
        guard !closed else { return }
        closed = true
        if fault == 0, heap.lookup(holderToken, words: 7) != nil {
            _ = entry(0x4cf760, receiver: holderToken, args: [1])
        }
        if let parent = heap.lookup(palette.parentToken, words: 15), parent[1] == holderToken { parent[1] = 0 }
        //The graphics manager owns remaining source surfaces and source list
        //blocks. Its later teardown dispatches through this same live adapter.
    }
    func finishTransport() {
        guard !finished else { return }
        finished = true
        for t in transportTokens { heap.free(t) }
        transportTokens.removeAll()
        interfaces.removeAll()
        colorKeys.removeAll()
    }
    func graphicsService(_ e: ClawGraphicsManagerLifecycleCall) -> UInt32? {
        guard !finished else { return nil }
        let args = withUnsafeBytes(of: e.arguments) {
            Array($0.bindMemory(to: UInt32.self).prefix(Int(e.argumentCount)))
        }
        if e.function == 0x4bc810 || e.function == 0x4bb060 {
            return entry(e.function, receiver: e.receiver, args: args)
        }
        if e.function == Self.release
            || (e.function == 0x4f6428 && args.count == 1 && sourceAllocations.contains(args[0]))
        {
            var q = ClawSceneDisplayCall()
            q.function = e.function
            q.receiver = e.receiver
            q.argumentCount = e.argumentCount
            q.arguments = e.arguments
            return service(q)
        }
        return nil
    }
    // MARK: - Physical surface services

    func surfaceService(_ q: ClawSurfaceBlitCall) -> UInt32 {
        guard !finished else {
            lastSurfaceFault = 3
            return 0
        }
        calls[q.function, default: 0] &+= 1
        let a = withUnsafeBytes(of: q.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(q.argumentCount))) }
        func local(_ index: Int, words: Int) -> UnsafeMutablePointer<UInt32>? {
            guard index < a.count else { return nil }
            if q.localMask & (1 << index) != 0 {
                let number = (0..<index).filter { q.localMask & (1 << $0) != 0 }.count
                guard number < Int(q.bufferCount), number < 2 else { return nil }
                let p = number == 0 ? q.buffers.0 : q.buffers.1
                let bytes = number == 0 ? q.bufferBytes.0 : q.bufferBytes.1
                return bytes >= words * 4 ? p : nil
            }
            return a[index] == 0 ? nil : heap.lookup(a[index], words: UInt32(words))
        }
        switch q.function {
        case Self.flip:
            guard a.count == 3, a[2] == 1, let dst = interfaces[a[0]] else { return 0x80070057 }
            let sourceDD = a[1] == 0 ? (a[0] == frontDD ? backDD : 0) : a[1]
            guard let src = interfaces[sourceDD], src.descriptor[21] == 8, dst.descriptor[21] == 8,
                src.descriptor[3] == dst.descriptor[3], src.descriptor[2] == dst.descriptor[2]
            else { return 0x80004001 }
            let width = Int(dst.descriptor[3]), height = Int(dst.descriptor[2])
            if menuSwapChain {
                guard a[0] == frontDD, sourceDD == backDD, a[1] == 0, textDCs.isEmpty else { return 0x80070057 }
                interfaces[a[0]]!.pixels = src.pixels
                interfaces[a[0]]!.descriptor[9] = src.pixels
                interfaces[sourceDD]!.pixels = dst.pixels
                interfaces[sourceDD]!.descriptor[9] = dst.pixels
                guard let pixels = heap.lookupBytes(src.pixels, count: src.descriptor[4] * src.descriptor[2]) else {
                    lastSurfaceFault = 1
                    return 0
                }
                presentations += 1
                presented?(
                    Data(bytes: pixels, count: Int(src.descriptor[4] * src.descriptor[2])), src.descriptor[3],
                    src.descriptor[2], src.descriptor[4])
                observePhysical?([
                    "service": "IDirectDrawSurface::Flip", "object": a[0], "flags": a[2],
                    "pixels": Data(bytes: pixels, count: Int(src.descriptor[4] * src.descriptor[2]))
                ])
                return 0
            }
            guard let sp = heap.lookup(src.pixels, words: (src.descriptor[4] * src.descriptor[2] + 3) / 4),
                let dp = heap.lookup(dst.pixels, words: (dst.descriptor[4] * dst.descriptor[2] + 3) / 4)
            else {
                lastSurfaceFault = 1
                return 0
            }
            //Memory presentation is an explicit copy, preserving the retained
            //indexed renderer allocation; this is not a hardware VRAM swap.
            let bytes = Data(bytes: sp, count: Int(src.descriptor[4]) * height)
            bytes.withUnsafeBytes { s in
                for y in 0..<height {
                    UnsafeMutableRawPointer(dp).advanced(by: y * Int(dst.descriptor[4])).copyMemory(
                        from: s.baseAddress!.advanced(by: y * Int(src.descriptor[4])), byteCount: width)
                }
            }
            return 0
        case Self.setColorKey:
            guard a.count == 3, interfaces[a[0]] != nil, [2, 3, 8, 9].contains(a[1]) else { return 0x80070057 }
            let kind = a[1] & ~1
            guard let p = local(2, words: 2) else {
                if a[2] == 0 && q.localMask & 4 == 0 {
                    colorKeys[a[0]]?[kind] = nil
                    return 0
                }
                return 0x80070057
            }
            guard p[0] <= p[1] else { return 0x80070057 }
            colorKeys[a[0], default: [:]][kind] = p[0]...p[1]
            observePhysical?([
                "service": "IDirectDrawSurface::SetColorKey", "object": a[0], "flags": a[1], "range": [p[0], p[1]]
            ])
            return 0
        case Self.blt, Self.bltFast:
            guard a.count == 6, let dst = interfaces[a[0]] else { return 0x88760082 }
            // The recovered resize path clears both buffers through 4b97c0.
            // Its DDBLTFX is a 100-byte record with an indexed fill color at +80.
            if q.function == Self.blt, a[4] == 0x01000400, a[1] != 0 {
                // Level 1 rectangular indexed fill: in-bounds rectangle, no
                // source, the same DDBLTFX checks as the full-surface fill.
                guard a[2] == 0, a[3] == 0, dst.descriptor[21] == 8, let r = local(1, words: 4),
                    let fx = local(5, words: 25), fx[0] == 100, fx[20] <= 255,
                    (1..<25).allSatisfy({ $0 == 20 || fx[$0] == 0 })
                else { return 0x80070057 }
                let left = Int(Int32(bitPattern: r[0])), top = Int(Int32(bitPattern: r[1]))
                let right = Int(Int32(bitPattern: r[2])), bottom = Int(Int32(bitPattern: r[3]))
                let width = Int(dst.descriptor[3]), height = Int(dst.descriptor[2]), stride = Int(dst.descriptor[4])
                guard 0 <= left, left < right, right <= width, 0 <= top, top < bottom, bottom <= height else {
                    return 0x80070057
                }
                guard let pixels = heap.lookupBytes(dst.pixels, count: UInt32(stride * height)) else {
                    lastSurfaceFault = 1
                    return 0x80070057
                }
                for row in top..<bottom {
                    pixels.advanced(by: row * stride + left).update(repeating: UInt8(fx[20]), count: right - left)
                }
                observePhysical?([
                    "service": "IDirectDrawSurface::Blt", "object": a[0], "flags": a[4],
                    "rectangle": [left, top, right, bottom], "fill_color": fx[20]
                ])
                wrotePrimary(
                    a[0],
                    [
                        "service": "IDirectDrawSurface::Blt", "rectangle": [left, top, right, bottom],
                        "fill_color": fx[20]
                    ])
                return 0
            }
            if q.function == Self.blt, a[4] == 0x01000400 {
                guard a[1] == 0, a[2] == 0, a[3] == 0, dst.descriptor[21] == 8,
                    let fx = local(5, words: 25), fx[0] == 100, fx[20] <= 255,
                    (1..<25).allSatisfy({ $0 == 20 || fx[$0] == 0 })
                else { return 0x80070057 }
                let width = Int(dst.descriptor[3]), height = Int(dst.descriptor[2]), stride = Int(dst.descriptor[4])
                guard let pixels = heap.lookupBytes(dst.pixels, count: UInt32(stride * height)) else {
                    lastSurfaceFault = 1
                    return 0x80070057
                }
                for row in 0..<height {
                    pixels.advanced(by: row * stride).update(repeating: UInt8(fx[20]), count: width)
                }
                observePhysical?([
                    "service": "IDirectDrawSurface::BltFill", "object": a[0], "flags": a[4], "fill_color": fx[20]
                ])
                wrotePrimary(a[0], ["service": "IDirectDrawSurface::Blt", "fill_color": fx[20]])
                return 0
            }
            let fast = q.function == Self.bltFast, sourceDD = fast ? a[3] : a[2]
            guard let src = interfaces[sourceDD], dst.descriptor[21] == 8, src.descriptor[21] == 8 else {
                return 0x80004001
            }
            func rect(_ p: UnsafeMutablePointer<UInt32>?, _ width: UInt32, _ height: UInt32) -> [Int] {
                guard let p else { return [0, 0, Int(width), Int(height)] }
                return (0..<4).map { Int(Int32(bitPattern: p[$0])) }
            }
            let sr = rect(local(fast ? 4 : 3, words: 4), src.descriptor[3], src.descriptor[2])
            let sw = sr[2] - sr[0], sh = sr[3] - sr[1]
            let dr =
                fast
                ? [
                    Int(Int32(bitPattern: a[1])), Int(Int32(bitPattern: a[2])), Int(Int32(bitPattern: a[1])) + sw,
                    Int(Int32(bitPattern: a[2])) + sh
                ] : rect(local(1, words: 4), dst.descriptor[3], dst.descriptor[2])
            let flags = fast ? a[5] : a[4], allowed: UInt32 = fast ? 0x33 : 0x0300aa00
            guard flags & ~allowed == 0 else { return 0x80004001 }
            let keyedSource = flags & (fast ? 1 : 0x8000) != 0, keyedDest = flags & (fast ? 2 : 0x2000) != 0
            guard !keyedSource || colorKeys[sourceDD]?[8] != nil, !keyedDest || colorKeys[a[0]]?[2] != nil else {
                return 0x887600d7
            }
            guard sw > 0, sh > 0, sr[0] >= 0, sr[1] >= 0, sr[2] <= Int(src.descriptor[3]),
                sr[3] <= Int(src.descriptor[2]),
                dr[0] >= 0, dr[1] >= 0, dr[2] <= Int(dst.descriptor[3]), dr[3] <= Int(dst.descriptor[2]), dr[2] > dr[0],
                dr[3] > dr[1]
            else { return 0x88760096 }
            //Stretching/filtering is not silently substituted for the original
            //DD operation. Current indexed menu copies are equal-sized spans.
            guard dr[2] - dr[0] == sw, dr[3] - dr[1] == sh else { return 0x80004001 }
            var fx: UInt32 = 0
            if !fast, flags & 0x800 != 0 {
                //The game's own DDBLTFX at 0x543108 (game_image_flips writes its
                //dwDDFX, 0x54310c) is authoritative once it is in guest memory;
                //the native image view is the fallback before the scene owns it.
                if let p = heap.lookup(a[5], words: 25), p[0] == 100 {
                    fx = p[1]
                } else if a[5] == 0x543108 {
                    fx = context.pointee.image.pointee.directDrawFX.1
                } else {
                    return 0x80070057
                }
                guard fx & ~6 == 0 else { return 0x80004001 }
            }
            guard let dp = heap.lookup(dst.pixels, words: (dst.descriptor[4] * dst.descriptor[2] + 3) / 4),
                let sp = heap.lookup(src.pixels, words: (src.descriptor[4] * src.descriptor[2] + 3) / 4)
            else {
                lastSurfaceFault = 1
                return 0
            }
            let d = UnsafeMutableRawPointer(dp).assumingMemoryBound(to: UInt8.self),
                s = UnsafeRawPointer(sp).assumingMemoryBound(to: UInt8.self)
            //Snapshot permits overlapping source/destination memory without
            //host pointer-order dependence. Pixel/coverage transport is explicit.
            var pixels = [UInt8](repeating: 0, count: sw * sh)
            // Color-key ranges are fixed for the whole call (checked above);
            // read them once instead of two dictionary lookups per pixel.
            let sourceKey = keyedSource ? colorKeys[sourceDD]![8]! : 0...0,
                destKey = keyedDest ? colorKeys[a[0]]![2]! : 0...0
            let srcStride = Int(src.descriptor[4]), dstStride = Int(dst.descriptor[4])
            pixels.withUnsafeMutableBufferPointer { pixels in
                for y in 0..<sh { for x in 0..<sw { pixels[y * sw + x] = s[(sr[1] + y) * srcStride + sr[0] + x] } }
                for y in 0..<sh {
                    for x in 0..<sw {
                        let pixel = pixels[(fx & 4 == 0 ? y : sh - y - 1) * sw + (fx & 2 == 0 ? x : sw - x - 1)]
                        let at = (dr[1] + y) * dstStride + dr[0] + x
                        if keyedSource, sourceKey.contains(UInt32(pixel)) { continue }
                        if keyedDest, !destKey.contains(UInt32(d[at])) { continue }
                        d[at] = pixel
                    }
                }
            }
            if fast {
                observePhysical?([
                    "service": "IDirectDrawSurface::BltFast", "object": a[0], "source": sourceDD, "rectangle": sr,
                    "destination": [dr[0], dr[1]], "flags": flags,
                    "pixels": Data(bytes: d, count: Int(dst.descriptor[4] * dst.descriptor[2]))
                ])
            } else {
                observePhysical?([
                    "service": "IDirectDrawSurface::Blt", "object": a[0], "source": sourceDD, "source_rectangle": sr,
                    "destination_rectangle": dr, "flags": flags
                ])
            }
            wrotePrimary(
                a[0],
                [
                    "service": fast ? "IDirectDrawSurface::BltFast" : "IDirectDrawSurface::Blt", "source_rectangle": sr,
                    "destination_rectangle": dr, "flags": flags
                ])
            return 0
        case 0x4bd260:
            guard a.count == 3 else { break }
            surfaceDiagnostics.append(a)
            let result = palette.diagnosticReport(a)
            lastSurfaceFault = max(lastSurfaceFault, palette.fault)
            return result
        default:
            guard q.localMask == 0, q.argumentCount <= 8 else { break }
            var e = ClawSceneDisplayCall()
            e.function = q.function
            e.receiver = q.receiver
            e.argumentCount = q.argumentCount
            e.arguments = q.arguments
            let out = service(e)
            if fault != 0 { lastSurfaceFault = fault }
            return out
        }
        unresolved.insert(q.function)
        lastSurfaceFault = 1
        return 0
    }
    fileprivate func service(_ q: ClawSceneDisplayCall) -> UInt32 {
        guard !finished else {
            fault = 3
            return 0
        }
        let a = withUnsafeBytes(of: q.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(q.argumentCount))) }
        calls[q.function, default: 0] &+= 1
        switch q.function {
        case 0x4f63ec:
            guard a.count == 1 else { break }
            let t = heap.allocate(bytes: a[0])
            if t != 0 { sourceAllocations.insert(t) }
            return t
        case 0x4f6428:
            guard a.count == 1 else { break }
            if a[0] == 0 { return 0 }
            //Enum callbacks borrow the palette host, so its source CArray
            //backing can be released by this same original startup call graph.
            if sourceAllocations.remove(a[0]) != nil {
                heap.free(a[0])
                return 0
            }
            return forward(q)
        case Self.create:
            guard a.count == 4, a[3] == 0, let descriptor = heap.lookup(a[1], words: 27), descriptor[0] == 108,
                let output = heap.lookup(a[2], words: 1)
            else { break }
            //Primary mode-only descriptors inherit the native display mode.
            //Blank image descriptors carry their actual width/height/depth.
            let sized = descriptor[1] & 6 == 6
            let width: UInt32 = sized ? descriptor[3] : palette.mode.width,
                height: UInt32 = sized ? descriptor[2] : palette.mode.height
            let depth: UInt32 = descriptor[1] & 0x1000 != 0 ? descriptor[21] : palette.mode.depth
            guard width > 0, height > 0, width <= 2048, height <= 2048, [8, 16, 24, 32].contains(depth),
                UInt64(width) * UInt64((depth + 7) / 8) * UInt64(height + 1) <= 4 << 20
            else { break }
            if descriptor[26] & 0x200 != 0, failPrimaryCreation {
                failPrimaryCreation = false
                output.pointee = 0
                observePhysical?(["service": "graphics-failure", "function": Self.create, "result": UInt32(0x8007000e)])
                return 0x8007000e
            }
            let dd = makeInterface(width: width, height: height, depth: depth)
            output.pointee = dd
            if descriptor[26] & 0x200 != 0 {
                frontDD = dd
                if menuSwapChain { backDD = makeInterface(width: width, height: height, depth: depth) }
            }
            observePhysical?([
                "service": "IDirectDraw::CreateSurface", "object": a[0], "surface": dd,
                "descriptor": Data(bytes: descriptor, count: 108)
            ])
            if frontDD == 0 { frontDD = dd }
            return 0
        case Self.attached:
            guard a.count == 3, a[0] == frontDD else { break }
            let caps = q.localMask == 6 ? q.buffers.0 : heap.lookup(a[1], words: 1)
            let output = q.localMask == 6 ? q.buffers.1 : heap.lookup(a[2], words: 1)
            guard caps?.pointee == 4, let output else { break }
            output.pointee = backDD
            observePhysical?(["service": "IDirectDrawSurface::GetAttachedSurface", "object": a[0]])
            return 0
        case Self.describe:
            guard a.count == 2, let d = interfaces[a[0]], let output = heap.lookup(a[1], words: 27) else { break }
            observePhysical?(["service": "IDirectDrawSurface::GetSurfaceDesc", "object": a[0]])
            d.descriptor.withUnsafeBufferPointer { output.update(from: $0.baseAddress!, count: 27) }
            return 0
        case Self.lock:
            guard a.count == 5, a[1] == 0, a[3] == 1, a[4] == 0, let d = interfaces[a[0]],
                let output = heap.lookup(a[2], words: 27)
            else { break }
            observePhysical?(["service": "IDirectDrawSurface::Lock", "object": a[0], "flags": a[3]])
            d.descriptor.withUnsafeBufferPointer { output.update(from: $0.baseAddress!, count: 27) }
            return 0
        case Self.unlock:
            guard a.count == 2, a[1] == 0, let d = interfaces[a[0]],
                let pixels = heap.lookupBytes(d.pixels, count: d.descriptor[4] * d.descriptor[2])
            else { break }
            observePhysical?([
                "service": "IDirectDrawSurface::Unlock", "object": a[0],
                "pixels": Data(bytes: pixels, count: Int(d.descriptor[4] * d.descriptor[2]))
            ])
            wrotePrimary(a[0], ["service": "IDirectDrawSurface::Unlock"])
            return 0
        case Self.release:
            guard a.count == 1, interfaces[a[0]] != nil else { break }
            observePhysical?(["service": "IDirectDrawSurface::Release", "object": a[0]])
            return 0  //Physical identities end with the device transport.
        default:
            return forward(q)
        }
        unresolved.insert(q.function)
        fault = 1
        return 0
    }
    private func forward(_ q: ClawSceneDisplayCall) -> UInt32 {
        var e = ClawGraphicsManagerLifecycleCall()
        e.function = q.function
        e.receiver = q.receiver
        e.argumentCount = q.argumentCount
        e.arguments = q.arguments
        e.localMask = q.localMask
        e.bufferCount = q.bufferCount
        e.buffers = q.buffers
        e.bufferBytes = q.bufferBytes
        let result = palette.graphicsService(e)
        fault = max(fault, palette.fault)
        return result
    }
}
private final class NativeDisplayRawPIDLock {
    let host: any ClawNativeRawDisplayHost
    var fault: UnsafeMutablePointer<UInt32>?
    init(host: any ClawNativeRawDisplayHost) { self.host = host }
}
private let nativeDisplayDependency: ClawSceneDisplayDependency = { c, e, u in
    guard let c, let e, let u else { return 0 }
    let host = Unmanaged<ClawNativeDisplay>.fromOpaque(u).takeUnretainedValue()
    let result = host.service(e.pointee)
    if host.fault != 0 { c.pointee.fault = host.fault }
    return result
}
private let nativeDisplayPCXDependency: ClawPCXImageDependency = { c, e, u in
    guard let c, let e, let u else { return 0 }
    let host = Unmanaged<ClawNativeDisplay>.fromOpaque(u).takeUnretainedValue()
    let result = host.pcxService(e.pointee)
    if host.fault != 0 { c.pointee.fault = host.fault }
    return result
}
private let nativeDisplayImageDependency: ClawGameImageService = { u, q in
    guard let u else { return 0 }
    return Unmanaged<ClawNativeDisplay>.fromOpaque(u).takeUnretainedValue().imageService(q)
}
private let nativeDisplayListDependency: ClawAmbientAudioBackendDependency = { c, e, u in
    guard let c, let e, let u else { return 0 }
    let h = Unmanaged<ClawNativeDisplay>.fromOpaque(u).takeUnretainedValue()
    let out = h.listService(e.pointee)
    if h.fault != 0 { c.pointee.fault = h.fault }
    return out
}

private let nativeDisplaySurfaceDependency: ClawSurfaceBlitDependency = { c, q, u in
    guard let c, let q, let u else { return 0 }
    let h = Unmanaged<ClawNativeDisplay>.fromOpaque(u).takeUnretainedValue()
    let out = h.surfaceService(q.pointee)
    if h.lastSurfaceFault != 0 { c.pointee.fault = h.lastSurfaceFault }
    return out
}
private let nativeDisplayFlipDependency: ClawSurfaceFlipDependency = { c, q, u in
    guard let c, let q, let u else { return 0 }
    let h = Unmanaged<ClawNativeDisplay>.fromOpaque(u).takeUnretainedValue()
    let out = h.surfaceService(q.pointee)
    if h.lastSurfaceFault != 0 { c.pointee.fault = h.lastSurfaceFault }
    return out
}

extension ClawNativeDisplay {
    // MARK: - Snapshot persistence

    struct SavedState: Codable, Equatable {
        struct Interface: Codable, Equatable { let pixels: UInt32, descriptor: [UInt32] }
        let holder: UInt32, surfaceVT: UInt32, context: [String: Data]
        let interfaces: [UInt32: Interface], transport: Set<UInt32>, colorKeys: [UInt32: [UInt32: ClosedRange<UInt32>]]
        let source: Set<UInt32>, calls: [UInt32: UInt64], surfaceDiagnostics: [[UInt32]], surfaceFault: UInt32
        let fault: UInt32, unresolved: Set<UInt32>, regions: [UInt32: [Int]], fonts: Set<UInt32>, stockFont: UInt32
        fileprivate let textDCs: [UInt32: TextDC]
        let textFailure: Int, front: UInt32, back: UInt32, swapChain: Bool, presentations: Int, pcxFault: UInt32,
            pcxLoads: UInt64
    }
    func savedState() throws -> SavedState {
        guard !closed, !finished, pcxInput == nil, imageFault == nil, !failPrimaryCreation, !recordsCreditsEvidence
        else { throw ClawSnapshotError.activeFrame }
        return .init(
            holder: holderToken, surfaceVT: surfaceVT, context: Self.snapshotFields.capture(context.pointee),
            interfaces: interfaces.mapValues { .init(pixels: $0.pixels, descriptor: $0.descriptor) },
            transport: transportTokens, colorKeys: colorKeys,
            source: sourceAllocations, calls: calls, surfaceDiagnostics: surfaceDiagnostics,
            surfaceFault: lastSurfaceFault, fault: fault, unresolved: unresolved,
            regions: regions, fonts: fonts, stockFont: stockFont, textDCs: textDCs, textFailure: textFailureLine,
            front: frontDD, back: backDD,
            swapChain: menuSwapChain, presentations: presentations, pcxFault: lastPCXFault, pcxLoads: pcxLoads)
    }
    func restoreState(_ saved: SavedState) throws {
        guard !closed, !finished, pcxInput == nil, imageFault == nil, saved.holder == holderToken,
            saved.surfaceVT == surfaceVT,
            saved.interfaces.count <= 16384,
            saved.interfaces.values.allSatisfy({ entry in
                let d = entry.descriptor
                return d.count == 27 && d[0] == 108 && d[9] == entry.pixels && d[2] > 0 && d[3] > 0 && d[2] <= 16384
                    && d[3] <= 16384 && [UInt32(8), 16, 24, 32].contains(d[21])
                    && UInt64(d[4]) >= UInt64(d[3]) * UInt64((d[21] + 7) / 8) && UInt64(d[4]) * UInt64(d[2]) <= 4 << 20
            }),
            saved.textDCs.values.allSatisfy({
                saved.interfaces[$0.surface] != nil && ($0.clip == nil || $0.clip!.count == 4)
            })
        else { throw ClawSnapshotError.invalidState }
        context.pointee = try Self.snapshotFields.restoring(saved.context, into: context.pointee)
        interfaces = saved.interfaces.mapValues { ($0.pixels, $0.descriptor) }
        transportTokens = saved.transport
        colorKeys = saved.colorKeys
        sourceAllocations = saved.source
        calls = saved.calls
        surfaceDiagnostics = saved.surfaceDiagnostics
        lastSurfaceFault = saved.surfaceFault
        fault = saved.fault
        unresolved = saved.unresolved
        regions = saved.regions
        fonts = saved.fonts
        stockFont = saved.stockFont
        textDCs = saved.textDCs
        textFailureLine = saved.textFailure
        frontDD = saved.front
        backDD = saved.back
        menuSwapChain = saved.swapChain
        presentations = saved.presentations
        lastPCXFault = saved.pcxFault
        pcxLoads = saved.pcxLoads
    }
    private static let snapshotFields = ClawSnapshotFields<ClawSceneDisplayContext>(fields: [
        .init("maximumOperations", \.maximumOperations),
        .init("fault", \.fault)
    ])
}
