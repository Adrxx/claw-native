import Foundation

// Real native display allocations, with callbacks instrumented at the same
// boundaries as the pinned original. No cached sprite or emulator on this side.
func verifyNativeRawActor() throws {
    let heap = ClawTokenHeap(),owner = heap.allocate(bytes:512),parent = heap.allocate(bytes:60)
    let globals = UnsafeMutablePointer<ClawGameImageGlobals>.allocate(capacity:1)
    globals.initialize(to:ClawGameImageGlobals())
    defer {globals.deinitialize(count:1);globals.deallocate()}
    let palette = try ClawNativePaletteResources(heap:heap,owner:owner,parent:parent,image:globals)
    let display = palette.display!
    let surface = display.createSurface(width:32,height:16,depth:8)
    let surface2 = display.createSurface(width:32,height:16,depth:8)
    let sw = heap.lookup(surface,words:47)!,sw2 = heap.lookup(surface2,words:47)!
    let dd = sw[2],dd2 = sw2[2],pixels = sw[12],pixels2 = sw2[12],vt = heap.lookup(dd,words:1)!.pointee
    let actor = heap.allocate(bytes:512),image = heap.allocate(bytes:52),image2 = heap.allocate(bytes:52)
    let target = heap.allocate(bytes:48),target2 = heap.allocate(bytes:48),imageParent = heap.allocate(bytes:40)
    let world = heap.allocate(bytes:32),world2 = heap.allocate(bytes:32),plane = heap.allocate(bytes:88),holder = heap.allocate(bytes:96)
    let pid = heap.allocate(bytes:40),pid2 = heap.allocate(bytes:40),stream = heap.allocate(bytes:128),replacement = heap.allocate(bytes:128)
    let rawRects = heap.allocate(bytes:32),table = heap.allocate(bytes:12),table2 = heap.allocate(bytes:12),tableData = heap.allocate(bytes:65536)
    let objects:[(String,UInt32,UInt32)] = [
        ("rect",rawRects,32),("table",table,12),("table2",table2,12),("tableData",tableData,65536),("scratch",0x542bb0,129),
        ("actor",actor,512),("image",image,52),("image2",image2,52),("target",target,48),("target2",target2,48),
        ("parent",imageParent,40),("world",world,32),("world2",world2,32),("plane",plane,88),("holder",holder,96),
        ("pid",pid,40),("pid2",pid2,40),("stream",stream,128),("replacement",replacement,128),
        ("surface",surface,188),("surface2",surface2,188),("dd",dd,4),("dd2",dd2,4),("vtable",vt,132),
        ("pixels",pixels,32*17),("pixels2",pixels2,32*17)]
    let initial = objects.map{Data(bytes:heap.lookupBytes($0.1,count:$0.2)!,count:Int($0.2))}
    func put(_ token:UInt32,_ values:[UInt32],host:ClawNativeCanonicalHost? = nil) {
        let p = host == nil ? heap.lookupBytes(token,count:UInt32(values.count*4)):host!.bytes(token,count:UInt32(values.count*4))
        values.withUnsafeBytes{UnsafeMutableRawPointer(p!).copyMemory(from:$0.baseAddress!,byteCount:$0.count)}
    }
    func snapshots()->[[String:Any]] {
        objects.map{["name":$0.0,"token":$0.1,"bytes":Data(bytes:heap.lookupBytes($0.1,count:$0.2)!,count:Int($0.2)).base64EncodedString()]}
    }
    var witnesses:[[String:Any]] = [],controls = 0
    func run(_ label:String,path:String = "world",clip:String = "full",flags:UInt32 = 0,policy:String = "",missing:UInt32 = 0,invalid:String = "",frame:UInt32 = UInt32(CLAW_STACK_TOP),mode:UInt32 = 1,flipX:UInt32 = 0,flipY:UInt32 = 0,render:UInt32 = 0,direct:Bool = false,seed:UInt32 = 0,retain:Bool = false) {
        let retained = [pixels,pixels2,0x542bb0].map{t in Data(bytes:heap.lookupBytes(t,count:t == 0x542bb0 ? 129:32*17)!,count:t == 0x542bb0 ? 129:32*17)}
        for (o,data) in zip(objects,initial) {data.withUnsafeBytes{UnsafeMutableRawPointer(heap.lookupBytes(o.1,count:o.2)!).copyMemory(from:$0.baseAddress!,byteCount:$0.count)}}
        for t in [pixels,pixels2] {heap.lookupBytes(t,count:32*17)!.update(repeating:0xa7,count:32*17)}
        var payload:[UInt8] = []
        for y in 0..<5 {payload += [2,UInt8(10+y),UInt8(20+y),130,4,UInt8(30+y),UInt8(40+y),UInt8(50+y),UInt8(60+y)]}
        for t in [stream,replacement] {payload.withUnsafeBufferPointer{heap.lookupBytes(t,count:UInt32(payload.count))!.update(from:$0.baseAddress!,count:payload.count)}}
        for i in 0..<65536 {heap.lookupBytes(tableData,count:65536)![i] = UInt8(truncatingIfNeeded:(i >> 8) ^ i)}
        if mode == 50 {for i in 0..<512 {heap.lookupBytes(tableData,count:512)![i] = UInt8(truncatingIfNeeded:i)}}
        put(table,[0x99887766,3,tableData]);put(table2,[0,0,tableData])
        for i in 0..<129 {heap.lookupBytes(0x542bb0,count:129)![i] = UInt8(truncatingIfNeeded:i*17+9)}
        for t in [pid,pid2] {put(t,[render,8,5,stream,UInt32(payload.count),mode,52,table,0,1])}
        if policy == "no-table" {put(pid+28,[0])}
        if policy == "fill-null-payload" {put(table+8,[0])}
        for t in [image,image2] {put(t,[0,0,0,imageParent,8,5,0,0,0,0,0,0,t == image ? pid:pid2])}
        for t in [target,target2] {put(t+16,[32,16]);put(t+44,[t == target ? surface:surface2])}
        put(actor+24,[UInt32](repeating:0x55667788,count:9))
        put(actor+8,[path == "world" ? 0x40000:0]);put(actor+16,[0,0]);put(actor+60,[holder,flags,18,50,3,2])
        var rect:[UInt32] = [0,0,31,15]
        if clip == "right" {rect[2] = 6}
        if clip == "left" {rect[0] = 5}
        if clip == "empty" {rect[0] = 30}
        put(actor+84,path == "actor" ? rect:[0x80000000,0,0,0])
        if path == "target" {
            if clip == "right" {put(target+16,[7])}
            if clip == "left" {put(actor+76,[UInt32(bitPattern:-2)])}
            if clip == "empty" {put(actor+76,[100])}
        }
        put(holder+92,[plane]);put(imageParent+36,[world]);put(world+16,rect);put(world2+16,[5,2,9,5])
        put(plane+8,[0]);put(plane+48,[512,256,0,0,0,0,511,255,0,0])
        if policy == "projection-wrap" {put(plane+8,[12]);put(actor+76,[515,258])}
        sw[7] = 29;sw2[7] = 29
        if invalid == "depth" {put(pid+36,[2])}
        if invalid == "malformed" {heap.lookupBytes(stream,count:1)!.pointee = 0}
        if invalid == "alias" {put(pid+12,[pixels])}
        if invalid == "scratch-payload" {
            payload.withUnsafeBufferPointer{heap.lookupBytes(0x542bb0,count:129)!.update(from:$0.baseAddress!,count:payload.count)}
            put(pid+12,[0x542bb0])
        }
        if invalid == "table-output" {put(table+8,[pixels])}
        if invalid == "scratch-table" {put(table+8,[0x542bb0])}
        if invalid == "table" {put(pid+28,[0xfffffff0])}
        // Source rejection is successful original dispatch, distinct from domain faults.
        if policy == "source-reject" {put(pid+4,[2])}
        var sourceRect:[UInt32] = [0,0,7,4]
        if clip == "right" {sourceRect[2] = 4}
        if clip == "left" {sourceRect[0] = 2}
        if clip == "top" {sourceRect[1] = 1}
        put(rawRects,sourceRect+[3,2,10,6])
        if policy == "long-literal" {
            payload = [127]+(0..<127).map{UInt8($0)}
            payload.withUnsafeBufferPointer{heap.lookupBytes(stream,count:128)!.update(from:$0.baseAddress!,count:128)}
            put(pid+4,[127,1,stream,128]);put(rawRects,[0,0,126,0,3,2,129,2])
        }
        if policy == "bounded-table" {
            let size = mode == 50 ? 512:16384,offset = mode == 50 ? 65024:49152
            for i in 0..<size {heap.lookupBytes(tableData,count:65536)![offset+i] = UInt8(truncatingIfNeeded:mode == 50 ? i:(i >> 8) ^ i)}
            put(table+8,[tableData+UInt32(offset)])
            // The 16 KiB source-color lookup accepts colors 0...63.
            if mode == 8 {heap.lookupBytes(stream,count:45)![44] = 63}
            if mode != 50 {heap.lookupBytes(pixels,count:32*17)!.update(repeating:0x27,count:32*17)}
        }
        if retain {
            for (t,data) in zip([pixels,pixels2,0x542bb0],retained) {
                data.withUnsafeBytes{UnsafeMutableRawPointer(heap.lookupBytes(t,count:UInt32(data.count))!).copyMemory(from:$0.baseAddress!,byteCount:$0.count)}
            }
        }
        let before = snapshots()
        var events:[[String:Any]] = [],dst:UInt32 = 0,src:UInt32 = 0
        let host = ClawNativeCanonicalHost(heap:heap)
        func spans(_ pairs:[(UInt32,UInt32)])->[[String:Any]] {
            pairs.map{["token":$0.0,"bytes":Data(bytes:host.bytes($0.0,count:$0.1)!,count:Int($0.1)).base64EncodedString()]}
        }
        host.dependency = {h,q in
            let a = withUnsafeBytes(of:q.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(q.argumentCount)))}
            if q.function == 0x4bffa0 {dst = a[0];src = a[2]}
            var event:[String:Any] = ["function":q.function,"receiver":q.receiver,"arguments":a,"memory":snapshots()]
            if [UInt32(0x4c96d0),0x546d58,0x4bffa0].contains(q.function) {event["stack"] = q.stackPointer}
            if q.function == 0x4c96d0 {event["spans"] = spans([(a[0],4),(a[1],4)])}
            else if q.function == 0x546d58 {event["spans"] = spans([(a[1],16)])}
            else if dst != 0 {event["spans"] = spans([(dst,16),(src,16)])}
            events.append(event)
            if q.function == missing {return nil}
            guard let result = display.rawActorService(h,q) else {return nil}
            if q.function == 0x4c96d0 {
                if policy == "project-dimensions" {put(image+16,[6,4])}
                if policy == "project-target" {put(actor+8,[0]);put(target+16,[7])}
                if policy == "project-world" {put(imageParent+36,[world2])}
            }
            if q.function == 0x546d58 && policy == "copy-reload" {
                put(frame-0x44,[image2],host:h);put(frame+8,[target2],host:h)
                put(image+48,[0]);put(target+44,[0]);put(image+16,[1,1]);put(actor+76,[900,901])
                put(a[0],[5,2,9,5],host:h);put(world+16,[99,99,100,100])
            }
            if q.function == ClawNativeDisplay.lock && policy == "lock-reload" {
                put(pid+4,[8,5,replacement,UInt32(payload.count)]);put(src,[1,1,6,4],host:h);put(dst,[3,2,99,direct ? 6:100],host:h)
                sw[7] = 39;sw[2] = dd2
            }
            if q.function == ClawNativeDisplay.lock && policy == "effect-reload" {
                put(pid,[1,8,5,replacement,UInt32(payload.count),22,0x12ab,table2,0,7])
                put(src,[1,1,6,4],host:h);put(dst,[3,2,10,6],host:h);sw[7] = 39;sw[2] = dd2
            }
            if q.function == ClawNativeDisplay.lock && invalid == "post-lock-depth" {put(pid+36,[2])}
            if q.function == ClawNativeDisplay.lock && policy == "mode-reload" {put(pid+20,[1])}
            if q.function == ClawNativeDisplay.lock && policy == "ordinary-reload" {put(pid+20,[22])}
            if q.function == ClawNativeDisplay.unlock {
                if policy == "unlock-stores" {
                    put(actor+24,[UInt32](repeating:0xdeadbeef,count:9));put(dst,[4,5,17,23],host:h);put(src,[0,1,2,3],host:h)
                }
                return 0x88760001
            }
            if q.function == 0x4bffa0 && policy == "blit-result" {return 0x88760001}
            return result
        }
        var call = ClawCall();call.function = 0x4d32e0;call.receiver = image;call.argumentCount = 2
        call.arguments.0 = actor;call.arguments.1 = target;call.stackPointer = frame
        let result:ClawNativeCanonicalHost.Completion
        if direct {
            call.function = 0x4bffa0;call.receiver = pid;call.argumentCount = 5
            call.arguments.0 = rawRects+16;call.arguments.1 = surface;call.arguments.2 = rawRects;call.arguments.3 = flipX;call.arguments.4 = flipY
            let value = host.withSourceStackFrame(entryStackPointer:frame,arguments:[rawRects+16,surface,rawRects,flipX,flipY],at:call.function) {
                put(frame-56,[seed],host:host)
                return host.callNativeDependency(call)
            }
            result = ClawNativeCanonicalHost.Completion(completed:host.fault == nil && value != nil,eax:nil,fault:host.fault)
        } else {result = host.invoke(call)}
        if missing != 0 || !invalid.isEmpty {
            precondition(!result.completed && result.fault != nil,"Accepted control \(label)")
            // Raw helper must not publish successful actor stores after a fault.
            precondition(heap.lookup(actor+56,words:1)!.pointee == 0x55667788)
            if missing != ClawNativeDisplay.unlock {
                precondition(Data(bytes:heap.lookupBytes(pixels,count:32*17)!,count:32*17) == Data(repeating:0xa7,count:32*17))
            }
            controls += 1;return
        }
        precondition(result.completed && result.fault == nil,"Raw actor failed \(label): \(String(describing:result.fault))")
        witnesses.append(["label":label,"entry":call.function,"receiver":call.receiver,"arguments":direct ? [rawRects+16,surface,rawRects,flipX,flipY]:[actor,target],"frame":frame,"seed":seed,
            "policy":policy,"before":before,"after":snapshots(),"events":events])
    }
    for path in ["world","actor","target"] {
        for clip in ["full","right","left","empty"] {
            for flags:UInt32 in [0,1,8,6,0x1000000e,0xffffffff] {
                run("\(path)-\(clip)-\(flags)",path:path,clip:clip,flags:flags)
            }
        }
    }
    for policy in ["project-dimensions","project-target","project-world","copy-reload","lock-reload","unlock-stores","blit-result","projection-wrap","source-reject"] {
        run(policy,flags:0xffffffff,policy:policy)
    }
    run("relocated-stack",policy:"copy-reload",frame:0x2009000)
    for missing:UInt32 in [0x4c96d0,0x546d58,0x4bffa0,0x4b9730,ClawNativeDisplay.lock,ClawNativeDisplay.unlock] {
        run("missing-\(missing)",missing:missing)
    }
    for invalid in ["depth","malformed","alias","table"] {run(invalid,invalid:invalid,mode:invalid == "table" ? 2:1)}
    run("public-setup")
    precondition(display.drawRawActor(image,actor:actor,target:target).completed)
    // Every selected transport executes through real surface allocations. The
    // original raw actor is intentionally unflipped; flips enter its dispatcher.
    let selected:[UInt32] = [0x4c0450,0x4c0920,0x4c0cc0,0x4c1190,0x4c25b0,0x4c3800,0x4c4c20]
    for mode:UInt32 in [1,2,4,8,22,50,0,3,0xffffffff] {
        for fx:UInt32 in [0,1] {for fy:UInt32 in [0,1] where mode != 1 || fx != 0 || fy != 0 {
            for render:UInt32 in [0,1] {for clip in ["full","left","right","top"] {
                run("transport-\(mode)-\(fx)-\(fy)-\(render)-\(clip)",clip:clip,mode:mode,flipX:fx,flipY:fy,render:render,direct:true,seed:0x1003000)
            }}
            for policy in mode == 1 ? ["lock-reload","ordinary-reload"]:["no-table","effect-reload","mode-reload"] {
                run("transport-\(mode)-\(fx)-\(fy)-\(policy)",policy:policy,mode:mode,flipX:fx,flipY:fy,direct:true)
            }
            run("long-\(mode)-\(fx)-\(fy)",policy:"long-literal",mode:mode,flipX:fx,flipY:fy,direct:true)
            for history in 0..<2 {
                run("retained-\(mode)-\(fx)-\(fy)-\(history)",mode:mode,flipX:fx,flipY:fy,direct:true,retain:true)
            }
            if [UInt32(4),8,50].contains(mode) {
                for render:UInt32 in [0,1] {
                    run("bounded-table-\(mode)-\(fx)-\(fy)-\(render)",policy:"bounded-table",mode:mode,flipX:fx,flipY:fy,render:render,direct:true)
                }
            }
            if mode == 50 {run("table-output-\(fx)-\(fy)",invalid:"table-output",mode:mode,flipX:fx,flipY:fy,direct:true)}
            if mode == 22 {run("fill-null-\(fx)-\(fy)",policy:"fill-null-payload",mode:mode,flipX:fx,flipY:fy,direct:true)}
            if mode == 1 || mode == 2 {
                let target:UInt32 = mode == 1 ? (fx != 0 ? (fy != 0 ? 0x4c0cc0:0x4c0450):0x4c0920)
                    : (fx != 0 ? (fy != 0 ? 0x4c4c20:0x4c25b0):(fy != 0 ? 0x4c3800:0x4c1190))
                precondition(selected.contains(target))
                for missing in [target,0x4b9730,ClawNativeDisplay.lock,ClawNativeDisplay.unlock] {
                    run("transport-missing-\(target)-\(missing)",missing:missing,mode:mode,flipX:fx,flipY:fy,direct:true)
                }
                for invalid in mode == 1 ? ["depth","post-lock-depth","malformed","alias"]:["malformed","alias","table","scratch-payload","scratch-table"] {
                    run("transport-invalid-\(target)-\(invalid)",invalid:invalid,mode:mode,flipX:fx,flipY:fy,direct:true)
                }
            }
        }}
    }
    for mode:UInt32 in [2,4,8,22,50] {
        for policy in ["","copy-reload","lock-reload","unlock-stores","effect-reload"] {
            run("actor-effect-\(mode)-\(policy)",flags:0xffffffff,policy:policy,mode:mode)
        }
    }
    // Non-mode-1 format rejection remains a successful zero with no lock.
    put(pid+20,[2]);put(pid+36,[2])
    let rejected = ClawNativeCanonicalHost(heap:heap)
    var dispatch = ClawCall();dispatch.function = 0x4bffa0;dispatch.receiver = pid;dispatch.argumentCount = 5
    dispatch.stackPointer = UInt32(CLAW_STACK_TOP)-0x78;dispatch.arguments.0 = rawRects+16;dispatch.arguments.1 = surface;dispatch.arguments.2 = rawRects
    precondition(display.rawActorService(rejected,dispatch) == 0 && rejected.fault == nil)
    put(pid+20,[1]);put(pid+36,[1]);controls += 1
    let foreign = ClawNativeCanonicalHost(heap:ClawTokenHeap())
    var q = ClawCall();q.function = 0x4c96d0;q.receiver = plane;q.argumentCount = 2
    precondition(display.rawActorService(foreign,q) == nil && foreign.fault != nil)
    palette.shutdown()
    precondition(!display.drawRawActor(image,actor:actor,target:target).completed)
    controls += 3
    let path = ProcessInfo.processInfo.environment["CLAW_NATIVE_RAW_ACTOR_WITNESS"]!
    try JSONSerialization.data(withJSONObject:["cases":witnesses,"controls":controls],options:[.sortedKeys]).write(to:URL(fileURLWithPath:path))
    print("PASS native raw actor and effect/flip transports: \(witnesses.count) witnesses, \(controls) controls; original comparison follows")
}
