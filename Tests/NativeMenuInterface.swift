import Foundation
import CryptoKit
func verifyNativeMenuInterface(root:URL,literals:[UInt32:Data]) throws {
    let fullInitializer = ProcessInfo.processInfo.environment["CLAW_MENU_FULL_INITIALIZER"] == "1"
    let base = try ClawNativeMenuBase(root:root,literals:literals)
    let display = base.palette!.display!
    try display.installMenuFont(Data(contentsOf:URL(fileURLWithPath:"work/native-menu-resources/menu-font.json")))
    let sharedSurfaces = [display.primaryToken,display.backToken,display.spareToken]
    let sharedAudio = base.audio!.managerIdentity
    let url = URL(fileURLWithPath:"work/native-menu-resources/interface-metadata.json")
    let raw = try JSONDecoder().decode([String:[UInt8]].self,from:Data(contentsOf:url))
    let metadata = Dictionary(uniqueKeysWithValues:raw.map{(UInt32($0.key,radix:16)!,Data($0.value))})
    var resizeClock = false
    var milliseconds:UInt32 = 1000
    let routeDiagnostics = ClawNativeDiagnostics(assetURL:URL(fileURLWithPath:"App/GameData/DiagnosticPolicy.json"),effects:.init(beep:{_ in true},log:{_ in true},dialog:{_,_,_,_ in true}))
    let owner = try ClawNativeMenuInterface(base:base,archiveURL:URL(fileURLWithPath:"Original/claw-disc/files/DATA/CLAW.REZ"),metadata:metadata,captureEvidence:fullInitializer,diagnostics:routeDiagnostics,clock:{if resizeClock {milliseconds += 100};return milliseconds})
    do {
        if fullInitializer {try owner.initialize()}
        else {try owner.load()}
        if ProcessInfo.processInfo.environment["CLAW_MENU_RESIZE"] == "1" {
            resizeClock = true
            try verifySharedMenuResize(owner:owner,root:root,literals:literals,metadata:metadata)
            return
        }
        if ProcessInfo.processInfo.environment["CLAW_MENU_ROUTES"] == "1" {
            try verifySharedMenuRoutes(owner:owner,root:root,literals:literals,metadata:metadata)
            return
        }
        if ProcessInfo.processInfo.environment["CLAW_MENU_FRAMES"] == "1" {
            func block(_ token:UInt32,_ count:UInt32)->[String:Any] {
                let bytes = Data(bytes:base.heap.lookupBytes(token,count:count)!,count:Int(count))
                let pointers = stride(from:0,to:bytes.count-3,by:4).filter{offset in
                    let value = bytes.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)}
                    return value >= 0x61000000 && value < 0x70000000 && base.heap.lookupBytes(value,count:1) != nil
                }
                return ["data":[UInt8](bytes),"pointerOffsets":pointers]
            }
            try owner.enter()
            var frames:[[String:Any]] = []
            for index in 0..<61 {
                milliseconds = 1000+UInt32((index+1)*1000/60)
                let start = owner.physicalEffects.count
                try owner.frame()
                let state = block(base.menuToken,0x2c8)
                let tokens = [UInt32(0x258),0x25c,0x260,0x264,0x268,0x270,0x274,0x278].map{owner.w(base.menuToken+$0)}
                    + (0..<15).map{owner.w(owner.w(base.menuToken+0x26c)+UInt32($0)*4)}
                let actors = tokens.map{block($0,UInt32(owner.resources.allocationData($0)!.count))}
                let world = block(owner.w(base.sceneToken+0x24),0xe0)
                let clocks = [UInt32(0x18),0x1c,0x20,0x24,0x28].map{owner.w(base.applicationToken+$0)}
                    + [UInt32(0x541328),0x54132c,0x541330,0x541334,0x541338].map{owner.w($0)}
                let surfaces = sharedSurfaces.map{SHA256.hash(data:display.surfacePixels(owner.w($0+44))!.bytes).map{String(format:"%02x",$0)}.joined()}
                frames.append(["state":state["data"]!,"pointerOffsets":state["pointerOffsets"]!,"actors":actors,
                               "world":world,"clocks":clocks,
                               "surfaces":surfaces,"palette":[UInt8](base.palette!.currentRGB!),
                               "effects":Array(owner.physicalEffects.dropFirst(start))])
                if index%10 == 0 {print("native menu frame",index)}
            }
            try JSONSerialization.data(withJSONObject:["frames":frames],options:[.sortedKeys]).write(to:URL(fileURLWithPath:"work/native-menu-resources/frames-swift.json"))
            owner.close()
            let cleanup:[String:Any] = ["cleanupFault":owner.cleanupFault,"resourceFault":owner.resources.fault,"cleanupRemaining":owner.resources.cleanupRemaining,"displayFault":display.fault,"details":owner.resources.cleanupDetails]
            try JSONSerialization.data(withJSONObject:cleanup,options:[.sortedKeys]).write(to:URL(fileURLWithPath:"work/native-menu-resources/frames-cleanup.json"))
            precondition(owner.cleanupFault == 0 && owner.resources.cleanupRemaining == 0 && display.fault == 0 && !display.menuSwapChain)
            var controls:[[String:Any]] = []
            for (kind,address):(String,UInt32) in [("owner",0x428b60),("owner",0x4c8fc0),("owner",0x4d32e0),
                ("owner",0x4c00b0),("owner",0x4b9730),("owner",0x4b98b0),
                ("physical",0x6e120044),("physical",0x546d30),("physical",0x6e120064),("physical",0x6e12002c)] {
                let controlBase = try ClawNativeMenuBase(root:root,literals:literals)
                try controlBase.palette!.display!.installMenuFont(Data(contentsOf:URL(fileURLWithPath:"work/native-menu-resources/menu-font.json")))
                var time:UInt32 = 1000
                let control = try ClawNativeMenuInterface(base:controlBase,archiveURL:URL(fileURLWithPath:"Original/claw-disc/files/DATA/CLAW.REZ"),metadata:metadata,clock:{time})
                try control.initialize();try control.enter();time = 1016
                if kind == "owner" {control.resources.missingOwner = address} else {control.resources.missingService = address}
                var rejected = false
                do {try control.frame()} catch {rejected = true}
                precondition(rejected && control.resources.faultAddress == address,"Wrong withheld frame boundary \(String(address,radix:16)): \(String(control.resources.faultAddress,radix:16))")
                control.close();control.close()
                precondition(control.resources.openFileCount == 0 && control.resources.liveAllocationCount == 0)
                controls.append(["kind":kind,"address":String(address,radix:16),"rejected":rejected])
            }
            try JSONSerialization.data(withJSONObject:controls,options:[.sortedKeys]).write(to:URL(fileURLWithPath:"work/native-menu-resources/frames-controls.json"))
            print("PASS 61 native menu frames and recovered cleanup")
            return
        }
    } catch {
        print("FAIL native IFC",error,"calls",owner.calls.suffix(24).map{String($0,radix:16)})
        print("TRACE",owner.resources.failureTrace)
        print("DISPLAY",display.fault,display.textFailureLine,display.unresolved)
        exit(2)
    }
    precondition(sharedSurfaces == [display.primaryToken,display.backToken,display.spareToken])
    precondition(sharedAudio == base.audio!.managerIdentity)
    var nodes:[[String:Any]] = []
    func visit(_ token:UInt32,_ depth:Int) {
        let count = owner.w(token+32)
        precondition(nodes.count < 512 && depth < 16 && count < 512)
        let names = (0..<8).map{owner.resources.text(owner.w(token+84+UInt32($0)*4))!}
        let selected = (0..<8).map{index -> [String:Any] in
            let surface = owner.w(owner.w(token+64)+UInt32(index)*4)
            guard let pixels = base.palette?.display?.surfacePixels(surface) else {preconditionFailure("IFC selection has no live native surface")}
            return ["width":pixels.width,"height":pixels.height,"sha256":SHA256.hash(data:pixels.bytes).map{String(format:"%02x",$0)}.joined()]
        }
        nodes.append(["depth":depth,"id":owner.w(token+80),"name":owner.resources.text(owner.w(token+20))!,"children":count,"images":names,"selected":selected])
        for index in 0..<count {visit(owner.w(owner.w(token+28)+index*4),depth+1)}
    }
    visit(base.menuToken+0x154+72,0)
    let profile = try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:"Tests/state_five_interface_profile.json"))) as! [String:Any]
    let expected = profile["nodes"] as! [[String:Any]]
    precondition(nodes.count == expected.count)
    for (actual,reference) in zip(nodes,expected) {
        let keys = ["depth","id","name","children","images"]
        let observed = actual.filter{keys.contains($0.key)},wanted = reference.filter{keys.contains($0.key)}
        precondition(NSDictionary(dictionary:observed).isEqual(to:wanted),"IFC node mismatch \(observed) vs \(wanted)")
    }
    let calls = owner.calls
    if fullInitializer {
        func bytes(_ token:UInt32,_ count:UInt32)->[UInt8] {
            Array(UnsafeBufferPointer(start:base.heap.lookupBytes(token,count:count)!,count:Int(count)))
        }
        func pointers(_ data:Data)->[Int] {
            stride(from:0,to:data.count-3,by:4).filter {offset in
                let value = data.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)}
                return value >= 0x61000000 && value < 0x70000000 && base.heap.lookupBytes(value,count:1) != nil
            }
        }
        var actors:[[String:Any]] = []
        let tokens = [UInt32(0x258),0x25c,0x260,0x264,0x268,0x270,0x274,0x278].map{owner.w(base.menuToken+$0)}
            + (0..<15).map{owner.w(owner.w(base.menuToken+0x26c)+UInt32($0)*4)}
        for token in tokens {
            let data = owner.resources.allocationData(token)!
            actors.append(["token":token,"data":[UInt8](data),"pointerOffsets":pointers(data)])
        }
        let state = Data(bytes(base.menuToken,0x2c8))
        let world = owner.resources.allocationData(owner.w(base.sceneToken+0x24))!
        let full:[String:Any] = ["menu":base.menuToken,"state":[UInt8](state),"pointerOffsets":pointers(state),"actors":actors,"nodes":nodes,
            "reads":owner.resources.events,"calls":calls,"music":owner.musicEvidence,"physicalEffects":owner.physicalEffects,
            "sounds":base.soundEntries.map{["name":$0.key,"pcm":base.audio!.sceneSoundPCM($0.value)!]},
            "palette":[UInt8](base.palette!.currentRGB ?? Data()),"sharedSurfaces":sharedSurfaces,"audioManager":sharedAudio,
            "world":[UInt8](world),"worldPointerOffsets":pointers(world)]
        try JSONSerialization.data(withJSONObject:full,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:"work/native-menu-resources/initializer-swift.json"))
        print("PASS full initializer returned on shared native heap")
    }
    owner.close();owner.close()
    let report:[String:Any] = ["nodes":nodes,"imageGroups":owner.imageCount,"calls":calls.map{String($0,radix:16)},
        "cleanupFault":owner.cleanupFault,"resourceFault":owner.resources.fault,"cleanupRemaining":owner.resources.cleanupRemaining,"cleanupTokens":owner.resources.cleanupTokens.map{String($0,radix:16)},"cleanupDetails":owner.resources.cleanupDetails,"destroyedWorld":[UInt8](owner.destroyedWorld),
        "displayFault":base.palette!.display!.fault,"invalidRelease":owner.resources.invalidReleaseToken,"invalidReleaseIsDisplay":base.palette!.display!.sourceAllocations.contains(owner.resources.invalidReleaseToken),"failureTrace":owner.resources.failureTrace,"constructorAllocations":base.constructorAllocations.map{$0.token},"cleanupCalls":owner.calls.suffix(32).map{String($0,radix:16)},"resourceAddress":String(owner.resources.faultAddress,radix:16)]
    try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys,.prettyPrinted]).write(to:URL(fileURLWithPath:"work/native-menu-resources/interface-swift.json"))
    if fullInitializer {try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys,.prettyPrinted]).write(to:URL(fileURLWithPath:"work/native-menu-resources/initializer-cleanup.json"))}
    precondition(owner.cleanupFault == 0 && owner.resources.fault == 0 && owner.resources.cleanupRemaining == 0,
        "IFC cleanup \(owner.cleanupFault), resource \(owner.resources.fault) at \(String(owner.resources.faultAddress,radix:16)), remaining \(owner.resources.cleanupRemaining)")
    precondition(base.palette!.display!.fault == 0)
    base.shutdown()
    precondition(base.soundCleanupFault == 0 && base.soundCleanupRemaining == 0 && base.palette!.fault == 0 && base.palette!.display!.fault == 0)
    var controls:[[String:Any]] = []
    let elected:[(String,UInt32)] = fullInitializer ? [("owner",0x4cace0),("owner",0x4ce0d0),("owner",0x4dcdf0),("physical",0x4f1d90),("physical",0x4a7260),("physical",0x546e98),("physical",0x6e120018),("physical",0x6e100014),("resource",0)] : [("owner",0x4dcdf0),("physical",0x4f1d90),("resource",0)]
    for (control,address) in elected {
        let controlBase = try ClawNativeMenuBase(root:root,literals:literals)
        let absent = try ClawNativeMenuInterface(base:controlBase,archiveURL:URL(fileURLWithPath:"Original/claw-disc/files/DATA/CLAW.REZ"),metadata:metadata)
        if control == "owner" {absent.resources.missingOwner = address}
        if control == "physical" {absent.resources.missingService = address}
        if control == "resource" {absent.resources.missingResource = "CLAW"}
        var rejected = false
        do {if fullInitializer {try absent.initialize()} else {try absent.load()}} catch {rejected = true}
        precondition(rejected && !absent.loaded,"Missing \(control) succeeded")
        if control != "resource" {precondition(absent.resources.faultAddress == address)}
        controls.append(["kind":control,"address":String(address,radix:16),"rejected":rejected,"fault":absent.resources.fault,"faultAddress":String(absent.resources.faultAddress,radix:16)])
        absent.close();absent.close()
        precondition(absent.resources.openFileCount == 0 && absent.resources.liveAllocationCount == 0)
        precondition(controlBase.palette!.display!.fault == 0)
    }
    if fullInitializer {
        let controlBase = try ClawNativeMenuBase(root:root,literals:literals)
        let absent = try ClawNativeMenuInterface(base:controlBase,archiveURL:URL(fileURLWithPath:"Original/claw-disc/files/DATA/CLAW.REZ"),metadata:metadata,clock:{1000})
        try absent.initialize()
        absent.resources.missingOwner = 0x429530
        absent.close();absent.close()
        precondition(absent.cleanupFault != 0 && absent.resources.faultAddress == 0x429530)
        precondition(absent.resources.openFileCount == 0 && absent.resources.liveAllocationCount == 0)
        controls.append(["kind":"cleanup-owner","address":"429530","rejected":true,"fault":absent.cleanupFault,"faultAddress":"429530"])
        try JSONSerialization.data(withJSONObject:controls,options:[.sortedKeys,.prettyPrinted]).write(to:URL(fileURLWithPath:"work/native-menu-resources/initializer-controls.json"))
    }
    print("PASS native IFC: \(nodes.count) original nodes, \(owner.imageCount) image groups, native surface selections and recovered cleanup")
}

// Branch witnesses remain on the initialized menu's heap, stack and display.
// The original runner recreates each input and compares fresh effects/state.
func verifySharedMenuRoutes(owner:ClawNativeMenuInterface,root:URL,literals:[UInt32:Data],metadata:[UInt32:Data]) throws {
    let base = owner.base,resources = owner.resources,heap = owner.heap,display = base.palette!.display!
    try owner.enter()
    print("shared routes: input")
    var effects:[[String:Any]] = [],rows:[[String:Any]] = []
    display.observePhysical = {event in
        var value = event
        for (key,field) in event {if let data = field as? Data {
            value.removeValue(forKey:key)
            value[key+"_sha256"] = SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined()
        }}
        effects.append(value)
    }
    base.windowInput!.queue.observePhysical = {effects.append($0)}
    func invoke(_ f:UInt32,_ r:UInt32,_ a:[UInt32] = [])->UInt32 {
        let result = resources.invoke(f,r,a)
        precondition(resources.fault == 0,"Shared route \(String(f,radix:16)) failed at \(String(resources.faultAddress,radix:16)): \(resources.failureTrace)")
        return result
    }
    func words(_ p:UInt32,_ values:[UInt32]) {for (i,v) in values.enumerated(){owner.put(p+UInt32(i*4),v)}}
    func state(_ p:UInt32,_ offsets:[UInt32])->[UInt32] {offsets.map{owner.w(p+$0)}}
    func events(_ input:ClawNativeWindowInput)->[[UInt32]] {input.queue.pending.map{[$0.window,$0.message.rawValue,$0.mask,$0.pressed ? 1:0]}}
    let input = base.windowInput!,other = ClawNativeWindowInput(queue:input.queue)
    input.key(mask:1,down:true);input.primary(mask:2,down:true);input.key(mask:4,down:false);other.key(mask:8,down:true)
    for (selector,limit):(UInt32,UInt32) in [(0x100,1),(0x100,64),(0x201,64),(0,64),(0,0),(0,.max)] {
        effects.removeAll();_ = invoke(0x4b8910,base.windowReceiver,[selector,limit])
        rows.append(["kind":"input","selector":selector,"limit":limit,"pending":events(input),"held":input.held,"effects":effects])
    }
    precondition(input.frameInput().pressed == 0 && other.frameInput().pressed == 8)
    var diagnosticEffects:[ClawNativeDiagnostics.Effect] = []
    var diagnosticFrame:UInt32 = 0
    print("shared routes: diagnostics")
    owner.diagnostics.observe = {diagnosticEffects.append($0);diagnosticFrame = resources.diagnosticFrame!}
    for flags:[UInt32] in [[1,1,1,0],[0,0,0,0],[0,0,1,0],[0,0,0,1],[1,0,0,0],[0,1,0,0]] {
        for error:UInt32 in [0x88760064,0x88760230,0x80004005,0x12345678] {
            diagnosticEffects.removeAll();owner.diagnostics.setFlags(display:true,flags)
            _ = invoke(0x4bd260,0,[0x532500,75,error])
            let data = try JSONEncoder().encode(diagnosticEffects)
            rows.append(["kind":"diagnostic","flags":flags,"error":error,"frame":diagnosticFrame,"effects":try JSONSerialization.jsonObject(with:data)])
        }
    }
    // A bound native file and array are cleaned by the real recovered movie
    // owner. File storage is task-local and contains no original asset bytes.
    print("shared routes: movie")
    let oldDependency = resources.dependency
    for profile in 0..<2 {
    let movie = resources.allocate(0x14c),array = heap.allocate(bytes:16)
    words(movie,[1,profile == 0 ? 1:0,1]);words(movie+0x124,[0x510844,77,1,0x52e1c4,9,0x5108fc,array,4,4,0])
    let movieURL = URL(fileURLWithPath:"work/native-menu-resources/route-movie.tmp")
    try Data([1,2,3,4]).write(to:movieURL)
    let file = try FileHandle(forReadingFrom:movieURL)
    try owner.movieServices.bind(movie:movie,file:file,array:array,arrayBytes:16)
    resources.dependency = {q in
        if q.function == 0x4f766e || q.function == 0x4f5915 && q.receiver == movie+0x138 {
            effects.append(["service":String(q.function,radix:16),"offset":q.receiver-movie,
                            "arguments":withUnsafeBytes(of:q.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(q.argumentCount)))}])
        }
        return oldDependency?(q)
    }
    let entries:[UInt32] = profile == 0 ? [0x4efd00,0x4efd00,0x4efcd0,0x4efcd0]:[0x4efcd0,0x4efcd0]
    for f in entries {
        effects.removeAll();let result = invoke(f,movie)
        rows.append(["kind":"movie","profile":profile,"entry":f,"result":result,"state":state(movie,[0,4,8,0x128,0x12c,0x134,0x13c,0x140,0x144]),"effects":effects])
    }
    try owner.movieServices.retire(movie:movie);resources.release(movie)
    precondition(heap.lookupBytes(array,count:1) == nil)
    try FileManager.default.removeItem(at:movieURL)
    resources.dependency = oldDependency
    }
    // Every raw effect and both axes use the live menu back surface, shared
    // callback stack, and original selector; frames cover the real actor root.
    let pid = resources.allocate(40),stream = resources.allocate(128),rects = resources.allocate(32)
    print("shared routes: raw")
    let table = resources.allocate(12),tableData = resources.allocate(65536)
    var payload:[UInt8] = []
    for y in 0..<5 {payload += [2,UInt8(10+y),UInt8(20+y),130,4,UInt8(30+y),UInt8(40+y),UInt8(50+y),UInt8(60+y)]}
    payload.withUnsafeBufferPointer{heap.lookupBytes(stream,count:UInt32(payload.count))!.update(from:$0.baseAddress!,count:$0.count)}
    words(table,[0,3,tableData])
    let surface = owner.w(display.backToken+44)
    for mode:UInt32 in [1,2,4,8,22,50,0,3,.max] {
        for fx:UInt32 in [0,1] {for fy:UInt32 in [0,1] {for render:UInt32 in [0,1] {
            for i in 0..<65536 {heap.lookupBytes(tableData,count:65536)![i] = UInt8(truncatingIfNeeded:mode == 50 ? i:(i>>8)^i)}
            words(pid,[render,8,5,stream,UInt32(payload.count),mode,52,table,0,1])
            words(rects,[1,1,6,4,3,2,10,6])
            owner.put(0x02008000-56,0x01003000)
            effects.removeAll();let start = owner.calls.count
            let result = invoke(0x4bffa0,pid,[rects+16,surface,rects,fx,fy])
            rows.append(["kind":"raw","mode":mode,"fx":fx,"fy":fy,"render":render,"result":result,
                         "pixels":SHA256.hash(data:display.surfacePixels(surface)!.bytes).map{String(format:"%02x",$0)}.joined(),
                         "scratch":[UInt8](Data(bytes:heap.lookupBytes(0x542bb0,count:129)!,count:129)),
                         "rects":state(rects,[0,4,8,12,16,20,24,28]),
                         "effects":effects,"calls":Array(owner.calls.dropFirst(start))])
        }}}
    }
    for token in [pid,stream,rects,table,tableData] {resources.release(token)}
    diagnosticEffects.removeAll();owner.diagnostics.setFlags(display:true,[1,1,1,0])
    var failedFlip:[UInt32] = []
    resources.dependency = {q in
        if q.function == ClawNativeDisplay.flip {
            failedFlip = [q.receiver,q.argumentCount,q.arguments.1,q.arguments.2]
            return 0x88760064
        }
        return oldDependency?(q)
    }
    let flipStart = owner.calls.count
    let flipResult = invoke(0x4b98b0,owner.w(display.primaryToken+44),[0])
    precondition(owner.calls.dropFirst(flipStart).contains(0x4bd260) && !diagnosticEffects.isEmpty)
    rows.append(["kind":"flip-diagnostic","request":failedFlip,"result":flipResult,"frame":diagnosticFrame,
                 "effects":try JSONSerialization.jsonObject(with:JSONEncoder().encode(diagnosticEffects))])
    resources.dependency = oldDependency
    // Presentation after branch exercises proves the shared display is usable.
    try owner.frame()
    var cleanupPointers:Set<UInt32> = []
    func cleanupSnapshot(_ kind:String) {
        let data = Data(bytes:heap.lookupBytes(base.menuToken,count:0x2c8)!,count:0x2c8)
        let offsets = stride(from:0,to:data.count,by:4).filter {off in
            let value = data.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:off,as:UInt32.self)}
            if value >= 0x61000000 && value < 0x70000000 && heap.lookupBytes(value,count:1) != nil {cleanupPointers.insert(value)}
            return cleanupPointers.contains(value)
        }
        rows.append(["kind":kind,"state":[UInt8](data),"pointerOffsets":offsets,"active":owner.w(0x537b58) != 0])
    }
    cleanupSnapshot("cleanup-before")
    _ = invoke(0x45b050,base.menuToken);cleanupSnapshot("cleanup-state")
    _ = invoke(0x45b050,base.menuToken);cleanupSnapshot("cleanup-repeat")
    owner.close();owner.close()
    precondition(owner.cleanupFault == 0 && resources.cleanupRemaining == 0 && resources.openFileCount == 0 && display.fault == 0)
    var controls:[[String:Any]] = []
    let denied:[(String,UInt32)] = [("owner",0x4bd260),("owner",0x4b8910),("owner",0x4efd00),("owner",0x4efcd0),
        ("owner",0x4bc110),
        ("physical",0x546ca4),("physical",0x546d48),("physical",0x4a3920),("physical",0x4f766e),("physical",0x4f5915),
        ("movie-binding",0x4f766e),("diagnostic-resource",0x4bd260),("input-window",0x4b8910),
        ("raw-owner",0x4c00b0),("raw-owner",0x4c0450),("raw-owner",0x4c0920),("raw-owner",0x4c0cc0),
        ("raw-owner",0x4c1190),("raw-owner",0x4c25b0),("raw-owner",0x4c3800),("raw-owner",0x4c4c20),
        ("raw-owner",0x4b9730),("raw-physical",0x6e120064),("raw-physical",0x6e120080),("raw-resource",0x4c1190)]
    for (kind,address) in denied {
        let b = try ClawNativeMenuBase(root:root,literals:literals)
        let d = ClawNativeDiagnostics(assetURL:URL(fileURLWithPath:kind == "diagnostic-resource" ? "work/native-menu-resources/absent-policy.json":"App/GameData/DiagnosticPolicy.json"),effects:.init(beep:{_ in true},log:{_ in true},dialog:{_,_,_,_ in true}))
        d.setFlags(display:true,[1,1,1,0])
        let c = try ClawNativeMenuInterface(base:b,archiveURL:URL(fileURLWithPath:"Original/claw-disc/files/DATA/CLAW.REZ"),metadata:metadata,diagnostics:d,clock:{1000})
        try c.initialize();try c.enter()
        if kind == "owner" || kind == "raw-owner" {c.resources.missingOwner = address}
        if kind == "physical" || kind == "raw-physical" {c.resources.missingService = address}
        if kind.hasPrefix("raw-") {
            let p = c.resources.allocate(40),s = c.resources.allocate(128),rect = c.resources.allocate(32)
            let light = c.resources.allocate(12),data = c.resources.allocate(65536)
            payload.withUnsafeBufferPointer{b.heap.lookupBytes(s,count:UInt32(payload.count))!.update(from:$0.baseAddress!,count:$0.count)}
            let mode:UInt32 = [UInt32(0x4c1190),0x4c25b0,0x4c3800,0x4c4c20].contains(address) ? 2:1
            let fx:UInt32 = [UInt32(0x4c0450),0x4c0cc0,0x4c25b0,0x4c4c20].contains(address) ? 1:0
            let fy:UInt32 = [UInt32(0x4c0920),0x4c0cc0,0x4c3800,0x4c4c20].contains(address) ? 1:0
            for (i,v) in [UInt32(0),8,5,s,UInt32(payload.count),mode,52,kind == "raw-resource" ? 0xfffffff0:light,0,1].enumerated(){c.put(p+UInt32(i*4),v)}
            c.put(light+8,data)
            for (i,v) in [UInt32(1),1,6,4,3,2,10,6].enumerated(){c.put(rect+UInt32(i*4),v)}
            let target = c.w(b.palette!.display!.backToken+44)
            let before = b.palette!.display!.surfacePixels(target)!.bytes
            _ = c.resources.invoke(0x4bffa0,p,[rect+16,target,rect,fx,fy])
            if address != ClawNativeDisplay.unlock {precondition(b.palette!.display!.surfacePixels(target)!.bytes == before)}
        } else if [UInt32(0x4efd00),0x4efcd0,0x4f766e,0x4f5915].contains(address) {
            let m = c.resources.allocate(0x14c)
            for (off,value):(UInt32,UInt32) in [(0,1),(4,1),(0x124,0x510844),(0x128,.max),(0x130,0x52e1c4)] {c.put(m+off,value)}
            if kind != "movie-binding" {try c.movieServices.bind(movie:m,file:nil,array:0,arrayBytes:0)}
            _ = c.resources.invoke(address == 0x4efd00 ? address:0x4efcd0,m)
            precondition(c.w(m) == 1 && c.w(m+4) == (address == 0x4f5915 ? 0:1),"Movie failure crossed the withheld boundary")
        } else if address == 0x4b8910 {
            b.windowInput!.key(mask:1,down:true)
            if kind == "input-window" {c.put(b.windowReceiver+4,0)}
            _ = c.resources.invoke(address,b.windowReceiver,[0x100,64])
            precondition(b.windowInput!.queue.pending.count == 1)
        } else {_ = c.resources.invoke(0x4bd260,0,[0x532500,75,0x88760064])}
        precondition(c.resources.fault != 0 && c.resources.faultAddress == (kind == "raw-resource" ? 0xfffffff0:address),"Wrong control \(kind) \(String(address,radix:16)) at \(String(c.resources.faultAddress,radix:16))")
        c.close();c.close()
        precondition(c.resources.openFileCount == 0 && c.resources.liveAllocationCount == 0)
        controls.append(["kind":kind,"address":address,"rejected":true])
    }
    let report:[String:Any] = ["rows":rows,"controls":controls,"cleanup":true,"sharedHeap":resources.heap === base.heap]
    try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]).write(to:URL(fileURLWithPath:"work/native-menu-resources/routes-swift.json"))
    print("PASS shared native routes: \(rows.count) witnesses, \(controls.count) controls; original comparison follows")
}

func verifySharedMenuResize(owner:ClawNativeMenuInterface,root:URL,literals:[UInt32:Data],metadata:[UInt32:Data]) throws {
    let base = owner.base,r = owner.resources,d = base.palette!.display!,p = base.palette!
    var rows:[[String:Any]] = [],edges:[[String:Any]] = [],effects:[[String:Any]] = []
    let offsets:[UInt32] = [0x68,0x6c,0x78,0x7c,0x80,0x84,0x88]
    func snapshot()->[String:Any] {
        let wrappers = [d.primaryToken,d.backToken,d.spareToken]
        return ["application":offsets.map{owner.w(base.applicationToken+$0)},
                "wrappers":wrappers.map{token in [UInt32(16),20,24,28,32,36,40].map{owner.w(token+$0)}},
                "sceneError":owner.w(base.sceneToken+0x38),"managerError":owner.w(p.backendManagerToken+0x880),
                "error":[UInt32(0x244),0x248,0x24c,0x250].map{owner.w(base.applicationErrors!.receiver+$0)}]
    }
    r.observeInvocation = {f,receiver,args in
        if [UInt32(0x4cf020),0x4c9bd0,0x42abf0,0x4b90b0].contains(f) {
            let role = receiver == base.applicationToken ? "application":receiver == base.sceneToken ? "scene":receiver == base.menuToken ? "menu":receiver == base.applicationErrors!.receiver ? "error":"unexpected"
            edges.append(["function":f,"receiver":role,"arguments":args,"state":snapshot(),"serviceCount":effects.count])
        }
    }
    func event(_ value:[String:Any]) {
        var e = value
        for (key,field) in value {if let data = field as? Data {e.removeValue(forKey:key);e[key+"_sha256"] = SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined()}}
        effects.append(e)
    }
    owner.observeEvidence = event
    func record(_ name:String,_ f:UInt32,_ receiver:UInt32,_ args:[UInt32],expected:UInt32) throws {
        edges.removeAll();effects.removeAll()
        let result = owner.invokeBranch(f,receiver,args)
        guard r.fault == 0,base.fault == 0,d.fault == 0 else {throw ClawNativeMenuResources.Failure.invalid("Resize \(name) at \(String(r.faultAddress,radix:16)): \(r.failureTrace), display \(d.unresolved)")}
        precondition(result == expected,"Unexpected result \(name): \(result)")
        let bytes = Data(bytes:base.heap.lookupBytes(base.menuToken,count:0x2c8)!,count:0x2c8)
        let pointers = stride(from:0,to:bytes.count,by:4).filter{off in let v = bytes.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:off,as:UInt32.self)};return v >= 0x61000000 && v < 0x70000000 && base.heap.lookupBytes(v,count:1) != nil}
        rows.append(["name":name,"result":result,"state":snapshot(),"edges":edges,"effects":effects,
                     "menu":[UInt8](bytes),"pointerOffsets":pointers])
        try JSONSerialization.data(withJSONObject:rows,options:[.sortedKeys]).write(to:URL(fileURLWithPath:"work/native-menu-resources/resize-swift.json"))
        print("resize profile",name)
    }
    // Entry establishes the actual application state and physical swap chain.
    try owner.enter()
    for previous:UInt32 in 2...13 {
        try record("prior-\(previous)",0x45b3f0,base.menuToken,[previous],expected:1)
    }
    try record("unforced",0x42a000,base.applicationToken,[0],expected:1)
    try record("forced-same",0x42a000,base.applicationToken,[1],expected:1)
    try record("changed",0x42a060,base.applicationToken,[800,600],expected:1)
    try record("restored",0x42a000,base.applicationToken,[1],expected:1)
    try record("changed-again",0x42a060,base.applicationToken,[800,600],expected:1)
    d.failPrimaryCreation = true
    try record("failed-resize",0x42a000,base.applicationToken,[1],expected:0)
    try record("latched-error",0x429e10,base.applicationToken,[0x1234,0x5678],expected:0)
    // Existing manager errors are first-error latches. A genuine physical
    // cooperative failure must map every retained 1001...1005 code at 4d5587.
    for code:UInt32 in [0,1001,1002,1003,1004,1005] {
        owner.put(p.backendManagerToken+0x880,code);owner.put(base.sceneToken+0x38,0)
        for offset:UInt32 in [0x244,0x248,0x24c,0x250] {owner.put(base.applicationErrors!.receiver+offset,0)}
        p.failedPhysicalCall = 0x6e110050
        try record("graphics-\(code)",0x4d5510,d.primaryToken,[640,480,8],expected:0)
        try record("graphics-error-\(code)",0x429e10,base.applicationToken,[0x8008,0x403],expected:0)
    }
    try JSONSerialization.data(withJSONObject:rows,options:[.sortedKeys]).write(to:URL(fileURLWithPath:"work/native-menu-resources/resize-swift.json"))
    r.observeInvocation = nil;owner.observeEvidence = nil
    owner.close();owner.close()
    let cleanup:[String:Any] = ["fault":owner.cleanupFault,"remaining":r.cleanupRemaining,"display":d.fault,"trace":r.failureTrace,"details":r.cleanupDetails]
    try JSONSerialization.data(withJSONObject:cleanup,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:"work/native-menu-resources/resize-cleanup.json"))
    precondition(owner.cleanupFault == 0 && r.cleanupRemaining == 0 && d.fault == 0)
    var controls:[[String:Any]] = []
    for (kind,address):(String,UInt32) in [
        ("owner",0x4cf020),("owner",0x4c9bd0),("owner",0x4d5720),("owner",0x4d5510),
        ("error-owner",0x4b90b0),("error-physical",0x546d50),("prior-owner",0x45b3f0),("prior-owner",0x4bbd90),
        ("physical",0x6e110054),("physical",0x6e120018),("physical",0x6e110030),
        ("resource",0),("cleanup-owner",0x429530)] {
        let b = try ClawNativeMenuBase(root:root,literals:literals)
        try b.palette!.display!.installMenuFont(Data(contentsOf:URL(fileURLWithPath:"work/native-menu-resources/menu-font.json")))
        let policy = ClawNativeDiagnostics(assetURL:URL(fileURLWithPath:"App/GameData/DiagnosticPolicy.json"),effects:.init(beep:{_ in true},log:{_ in true},dialog:{_,_,_,_ in true}))
        var time:UInt32 = 1000
        let c = try ClawNativeMenuInterface(base:b,archiveURL:URL(fileURLWithPath:"Original/claw-disc/files/DATA/CLAW.REZ"),metadata:metadata,diagnostics:policy,clock:{time += 100;return time})
        var rejected = false
        if kind == "resource" {
            c.resources.missingResource = "CLAW"
            do {try c.initialize()} catch {rejected = true}
        } else {
            try c.initialize();try c.enter()
            if kind == "physical" || kind == "error-physical" {c.resources.missingService = address} else {c.resources.missingOwner = address}
            if kind == "cleanup-owner" {c.close();rejected = c.cleanupFault != 0}
            else {
                if kind == "error-owner" || kind == "error-physical" {
                    b.palette!.display!.failPrimaryCreation = true
                    _ = c.resources.invoke(0x42a060,b.applicationToken,[800,600])
                    // The application guard is the owner that reports failure.
                    if c.resources.fault == 0 {_ = c.resources.invoke(0x429e10,b.applicationToken,[0x8008,0x403])}
                } else if kind == "prior-owner" {_ = c.resources.invoke(0x45b3f0,b.menuToken,[8])}
                else if address == 0x4d5510 {_ = c.resources.invoke(address,b.palette!.display!.primaryToken,[640,480,8])}
                else {_ = c.resources.invoke(0x42a060,b.applicationToken,[800,600])}
                rejected = c.resources.fault != 0
            }
            precondition(c.resources.faultAddress == address,"Wrong resize negative boundary \(kind) \(String(address,radix:16)): \(String(c.resources.faultAddress,radix:16))")
        }
        precondition(rejected,"Resize control unexpectedly succeeded \(kind)")
        c.close();c.close()
        precondition(c.resources.openFileCount == 0 && c.resources.liveAllocationCount == 0)
        controls.append(["kind":kind,"address":address,"rejected":rejected,"files":c.resources.openFileCount,"allocations":c.resources.liveAllocationCount])
    }
    try JSONSerialization.data(withJSONObject:controls,options:[.sortedKeys]).write(to:URL(fileURLWithPath:"work/native-menu-resources/resize-controls.json"))
    print("PASS resize profiles and cleanup")
}
