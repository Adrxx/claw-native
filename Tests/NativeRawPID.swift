import Foundation

// Original/native comparison witnesses use the real display owner, without a
// player, cached sprite or synthetic replacement for the physical surface.
func verifyNativeRawPID() throws {
    let heap = ClawTokenHeap(),owner = heap.allocate(bytes:512),parent = heap.allocate(bytes:60)
    let globals = UnsafeMutablePointer<ClawGameImageGlobals>.allocate(capacity:1)
    globals.initialize(to:ClawGameImageGlobals())
    defer {globals.deinitialize(count:1);globals.deallocate()}
    let palette = try ClawNativePaletteResources(heap:heap,owner:owner,parent:parent,image:globals)
    let display = palette.display!
    let surface = display.createSurface(width:32,height:16,depth:8)
    let second = display.createSurface(width:32,height:16,depth:8)
    precondition(surface != 0 && second != 0)
    let sw = heap.lookup(surface,words:47)!,secondWords = heap.lookup(second,words:47)!
    let dd = sw[2],dd2 = secondWords[2],vt = heap.lookup(dd,words:1)!.pointee
    // Creation fills the source descriptor, including its actual native pixels.
    let pixels = sw[12]
    precondition(pixels != 0 && sw[7] == 32)
    let image = heap.allocate(bytes:40),src = heap.allocate(bytes:16),dst = heap.allocate(bytes:16)
    let stream = heap.allocate(bytes:128),replacement = heap.allocate(bytes:128)
    let objects:[(String,UInt32,UInt32)] = [
        ("image",image,40),("source",src,16),("destination",dst,16),("stream",stream,128),
        ("replacement",replacement,128),("surface",surface,188),("dd",dd,4),("dd2",dd2,4),
        ("vtable",vt,132),("pixels",pixels,32*17)]
    func put(_ token:UInt32,_ words:[UInt32]) {
        words.withUnsafeBufferPointer{heap.lookup(token,words:UInt32(words.count))!.update(from:$0.baseAddress!,count:words.count)}
    }
    func snapshots()->[[String:Any]] {
        objects.map {name,token,count in
            ["name":name,"token":token,"bytes":Data(bytes:heap.lookupBytes(token,count:count)!,count:Int(count)).base64EncodedString()]
        }
    }
    let initialSurface = Data(bytes:sw,count:188)
    var witnesses:[[String:Any]] = [],controls = 0
    func run(_ label:String,left:UInt32,right:UInt32,pitch:UInt32,policy:String = "",missing:UInt32 = 0,invalid:String = "") {
        initialSurface.withUnsafeBytes{UnsafeMutableRawPointer(sw).copyMemory(from:$0.baseAddress!,byteCount:188)}
        heap.lookupBytes(pixels,count:32*17)!.update(repeating:0xa7,count:32*17)
        heap.lookupBytes(image,count:40)!.update(repeating:0,count:40)
        var payload:[UInt8] = []
        for y in 0..<5 {payload += [2,UInt8(10+y),UInt8(20+y),130,4,UInt8(30+y),UInt8(40+y),UInt8(50+y),UInt8(60+y)]}
        for token in [stream,replacement] {
            heap.lookupBytes(token,count:128)!.update(repeating:0,count:128)
            payload.withUnsafeBufferPointer{heap.lookupBytes(token,count:UInt32(payload.count))!.update(from:$0.baseAddress!,count:payload.count)}
        }
        put(image+4,[8,5,stream,UInt32(payload.count),1]);put(image+36,[1])
        put(src,[left,1,right,4]);put(dst,[3,2,123,456]);sw[7] = pitch
        if policy == "lock-reload" {
            put(image+4,[9,6,0,0]);put(image+36,[2]);put(src,[0,0,8,5]);put(dst,[0,0,0,0])
        }
        if invalid == "depth" {put(image+36,[2])}
        if invalid == "malformed" {heap.lookupBytes(stream,count:1)!.pointee = 0}
        if invalid == "unsafe" {put(dst,[3,10000,123,456])}
        if invalid == "alias" {put(image+12,[pixels])}
        let before = snapshots()
        var events:[[String:Any]] = []
        let host = ClawNativeCanonicalHost(heap:heap)
        host.dependency = {h,q in
            let a = withUnsafeBytes(of:q.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(q.argumentCount)))}
            events.append(["function":q.function,"receiver":q.receiver,"arguments":a,"memory":snapshots()])
            if q.function == missing {return nil}
            guard let result = display.rawPIDService(h,q) else {return nil}
            if q.function == ClawNativeDisplay.lock,policy == "lock-reload" {
                put(image+4,[8,5,replacement,UInt32(payload.count)]);put(image+36,[1])
                put(src,[left,1,right,4]);put(dst,[3,2,123,456]);sw[7] = 39;sw[2] = dd2
            }
            if q.function == ClawNativeDisplay.unlock {return 0x88760001}
            return result
        }
        var call = ClawCall();call.function = 0x4c00b0;call.receiver = image;call.argumentCount = 3
        call.arguments.0 = dst;call.arguments.1 = surface;call.arguments.2 = src
        let result = host.invoke(call)
        if missing != 0 || !invalid.isEmpty {
            precondition(!result.completed && result.fault != nil,"Control accepted: \(label)")
            if missing != ClawNativeDisplay.unlock {
                precondition(Data(bytes:heap.lookupBytes(pixels,count:32*17)!,count:32*17) == Data(repeating:0xa7,count:32*17))
            }
            controls += 1;return
        }
        precondition(result.completed && result.fault == nil,"Raw PID failed: \(label) \(String(describing:result.fault))")
        precondition(Data(bytes:heap.lookupBytes(pixels,count:32*17)!,count:32*17) != Data(repeating:0xa7,count:32*17))
        precondition(events.map{$0["function"] as! UInt32} == [0x4b9730,ClawNativeDisplay.lock,ClawNativeDisplay.unlock])
        precondition(display.surfacePixels(surface) != nil)
        witnesses.append(["label":label,"entry":call.function,"receiver":image,"arguments":[dst,surface,src],
                          "policy":policy,"left":left,"right":right,"before":before,"after":snapshots(),"events":events])
    }
    for pitch:UInt32 in [29,32] {
        for (left,right):(UInt32,UInt32) in [(0,7),(0,3),(1,6),(4,7)] {
            run("clip-\(left)-\(right)-pitch-\(pitch)",left:left,right:right,pitch:pitch)
            run("reload-\(left)-\(right)-pitch-\(pitch)",left:left,right:right,pitch:pitch,policy:"lock-reload")
        }
    }
    for missing:UInt32 in [0x4b9730,ClawNativeDisplay.lock,ClawNativeDisplay.unlock] {
        run("missing-\(missing)",left:0,right:7,pitch:32,missing:missing)
    }
    for invalid in ["depth","malformed","unsafe","alias"] {
        run(invalid,left:0,right:7,pitch:32,invalid:invalid)
    }
    // Exercise the public entry and its receiver/owner lifetime controls too.
    run("public-setup",left:0,right:7,pitch:32)
    precondition(display.drawRawPID(image,destination:dst,surface:surface,source:src).completed)
    precondition(!display.drawRawPID(image,destination:dst,surface:0,source:src).completed)
    let otherDepth = display.createSurface(width:32,height:16,depth:16)
    precondition(otherDepth != 0 && !display.drawRawPID(image,destination:dst,surface:otherDepth,source:src).completed)
    sw[2] = 0
    precondition(!display.drawRawPID(image,destination:dst,surface:surface,source:src).completed)
    sw[2] = dd
    let foreign = ClawNativeCanonicalHost(heap:ClawTokenHeap())
    var physical = ClawCall();physical.function = ClawNativeDisplay.unlock;physical.argumentCount = 2;physical.arguments.0 = dd
    precondition(display.rawPIDService(foreign,physical) == nil && foreign.fault != nil)
    palette.shutdown()
    precondition(!display.drawRawPID(image,destination:dst,surface:surface,source:src).completed)
    controls += 6
    let path = ProcessInfo.processInfo.environment["CLAW_NATIVE_RAW_PID_WITNESS"]!
    try JSONSerialization.data(withJSONObject:["cases":witnesses,"controls":controls],options:[.sortedKeys])
        .write(to:URL(fileURLWithPath:path))
    print("PASS native raw PID display: \(witnesses.count) witnesses, \(controls) controls; original comparison follows")
}
