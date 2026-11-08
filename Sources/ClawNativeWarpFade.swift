import Foundation

//Raw source type2 fader with native indexed surface/clock transports. This host
//does not elect WM_COMMAND travel or substitute for whole graphics startup.
final class ClawNativeWarpFade {
    let heap:ClawTokenHeap,random:ClawNativeRandom
    let managerToken:UInt32,targetSurface:UInt32,sourceSurface:UInt32
    let targetPixels:UInt32,sourcePixels:UInt32
    static let visibleBytes = 640*480,storageBytes = 640*481
    private let clock:()->UInt32
    private let fade = UnsafeMutablePointer<ClawPlayerFadeContext>.allocate(capacity:1)
    private let blend = UnsafeMutablePointer<ClawPlayerFadeBlendContext>.allocate(capacity:1)
    private var context = ClawWarpFadeContext()
    private var transportTokens:[UInt32] = []
    private let descriptor:UInt32
    private static let unlock:UInt32 = 0x6e200080
    private(set) var fault:UInt32 = 0,unresolved:Set<UInt32> = []
    private(set) var sourceAllocations:Set<UInt32> = [],calls:[UInt32:UInt64] = [:]
    private(set) var clockReads:UInt64 = 0,locks:[UInt32:UInt64] = [:],unlocks:[UInt32:UInt64] = [:]
    private var closed = false
    init(heap:ClawTokenHeap,random:ClawNativeRandom,clock:@escaping ()->UInt32) {
        self.heap = heap;self.random = random;self.clock = clock
        managerToken = heap.allocate(bytes:40);descriptor = heap.allocate(bytes:36)
        targetSurface = heap.allocate(bytes:188);sourceSurface = heap.allocate(bytes:188)
        targetPixels = heap.allocate(bytes:UInt32(Self.storageBytes));sourcePixels = heap.allocate(bytes:UInt32(Self.storageBytes))
        transportTokens = [managerToken,descriptor,targetSurface,sourceSurface,targetPixels,sourcePixels]
        fade.initialize(to:ClawPlayerFadeContext());blend.initialize(to:ClawPlayerFadeBlendContext())
        fade.pointee.scene = host;fade.pointee.temporaryDescriptorToken = descriptor;fade.pointee.maximumClockReads = 1000000
        blend.pointee.fade = fade;blend.pointee.temporaryStringToken = own(4);blend.pointee.emptyStringToken = 0x52e1c4
        context.common = blend;context.maximumOperations = 1000000
        //The immutable table is copied from the verified original image. The
        //188-byte surfaces are explicit native format profiles, not recovered
        //surface constructors. One extra row represents source spill capacity.
        if heap.lookup(0x514228,words:5) == nil {
            let methods:[UInt32] = [0x4ed080,0x4ed1a0,0x4ed5d0,0x4c96b0,0x4c96b0]
            let table = heap.store(token:0x514228,words:5);methods.withUnsafeBufferPointer{table.update(from:$0.baseAddress!,count:5)}
        }
        let vt = own(132);heap.lookup(vt,words:33)![32] = Self.unlock
        for surface in [targetSurface,sourceSurface] {
            let dd = own(4);heap.lookup(dd,words:1)!.pointee = vt
            let p = heap.lookup(surface,words:47)!
            p[2] = dd;p[5] = 480;p[6] = 640;p[7] = 640;p[0xac/4] = 1
        }
        _ = entry(0x4ebf80,receiver:managerToken)
        let manager = heap.lookup(managerToken,words:10)!
        manager[0] = targetSurface;manager[1] = sourceSurface
    }
    deinit {
        shutdown();blend.deinitialize(count:1);blend.deallocate();fade.deinitialize(count:1);fade.deallocate()
    }
    private func own(_ bytes:UInt32)->UInt32 {let token = heap.allocate(bytes:bytes);transportTokens.append(token);return token}
    private var host:ClawSceneActorHost {
        ClawSceneActorHost(context:Unmanaged.passUnretained(heap).toOpaque(),lookup:{user,token,words in
            guard let user else { return nil };return Unmanaged<ClawTokenHeap>.fromOpaque(user).takeUnretainedValue().lookup(token,words:words)
        },allocate:nil,free:nil,call:nil,readClock:nil)
    }
    func setPixels(target:Data,source:Data) {
        precondition(target.count == Self.visibleBytes && source.count == Self.visibleBytes && !closed)
        for (token,data) in [(targetPixels,target),(sourcePixels,source)] {
            let pointer = heap.lookup(token,words:UInt32(Self.storageBytes/4))!
            UnsafeMutableRawPointer(pointer).initializeMemory(as:UInt8.self,repeating:0xa5,count:Self.storageBytes)
            data.withUnsafeBytes{UnsafeMutableRawPointer(pointer).copyMemory(from:$0.baseAddress!,byteCount:$0.count)}
        }
    }
    var targetBytes:Data {Data(bytes:heap.lookup(targetPixels,words:UInt32(Self.visibleBytes/4))!,count:Self.visibleBytes)}
    var sourceBytes:Data {Data(bytes:heap.lookup(sourcePixels,words:UInt32(Self.visibleBytes/4))!,count:Self.visibleBytes)}
    var targetPadding:Data {Data(bytes:heap.lookup(targetPixels+UInt32(Self.visibleBytes),words:160)!,count:640)}
    func create(clear:Bool,percent:UInt32 = 80)->UInt32 {
        let p = heap.lookup(descriptor,words:9)!
        p[0] = 3;p[1] = targetSurface;p[2] = clear ? 0:sourceSurface;p[3] = clear ? 1:0;p[4] = percent
        return entry(0x4ec050,receiver:managerToken,args:[2,descriptor])
    }
    @discardableResult func entry(_ function:UInt32,receiver:UInt32,args:[UInt32] = [])->UInt32 {
        precondition(!closed)
        var result:UInt32 = 0
        let done = heap.withStableFreedStorage {
            args.withUnsafeBufferPointer { a -> UInt32 in
                let completed = claw_warp_fade_entry(function,receiver,a.baseAddress,UInt32(a.count),&context,nativeWarpFadeDependency,Unmanaged.passUnretained(self).toOpaque(),&result)
                if completed == 1 || fade.pointee.fault != 0 {return completed}
                return claw_player_fade_entry(function,receiver,a.baseAddress,UInt32(a.count),fade,nativeWarpFadeDependency,Unmanaged.passUnretained(self).toOpaque(),&result)
            }
        }
        fault = max(fault,fade.pointee.fault);if done != 1 {unresolved.insert(function);fault = max(fault,1)}
        return result
    }
    func remove(_ effect:UInt32) {_ = entry(0x4ec600,receiver:managerToken,args:[effect])}
    func shutdown() {
        guard !closed else {return}
        //Source removal destroys each fader. Recovered CArray SetSize(0)
        //releases its actual source backing store; outer fixture profiles are
        //transport-owned, with no whole4ebfc0 destructor claim.
        if fault == 0 {
            let manager = heap.lookup(managerToken,words:10)!
            while manager[6] != 0 && fault == 0 {remove(heap.lookup(manager[5],words:manager[6])!.pointee)}
            var array = ClawCArrayContext(),result:UInt32 = 0
            array.scene = host;claw_carray_defaults(&array)
            let done = claw_carray_entry(0x4f5915,managerToken+16,0,.max,0,&array,{context,event,user in
                guard let event,let user else {return 0}
                let owner = Unmanaged<ClawNativeWarpFade>.fromOpaque(user).takeUnretainedValue()
                var call = ClawPlayerFadeCall();call.function = event.pointee.function;call.receiver = event.pointee.receiver;call.argumentCount = event.pointee.argumentCount
                call.arguments = (event.pointee.arguments.0,event.pointee.arguments.1,event.pointee.arguments.2,event.pointee.arguments.3,0,0)
                let value = owner.service(call);if owner.fault != 0 {context?.pointee.fault = owner.fault};return value
            },Unmanaged.passUnretained(self).toOpaque(),&result)
            if done != 1 || array.fault != 0 {fault = max(1,array.fault)}
        }
        for token in transportTokens.reversed() {heap.free(token)}
        closed = true
    }
    fileprivate func service(_ call:ClawPlayerFadeCall)->UInt32 {
        calls[call.function,default:0] &+= 1
        let a = call.arguments.0
        switch call.function {
        case 0x4f63ec:
            let token = heap.allocate(bytes:a);if token != 0 {sourceAllocations.insert(token)};return token
        case 0x4f6428:
            guard sourceAllocations.remove(a) != nil else {fault = 1;return 0};heap.free(a);return 0
        case 0x4a3050:
            let result = random.call(call.function);if random.fault != 0 {fault = random.fault};return result
        case 0x546a24,0x546df0:clockReads &+= 1;return clock()
        case 0x4b9730:
            guard call.argumentCount == 1,a == 0,call.receiver == targetSurface || call.receiver == sourceSurface else {fault = 1;return 0}
            locks[call.receiver,default:0] &+= 1;return call.receiver == targetSurface ? targetPixels:sourcePixels
        case Self.unlock:
            guard call.argumentCount == 2,call.arguments.1 == 0,let surface = [targetSurface,sourceSurface].first(where:{heap.lookup($0,words:3)![2] == a}) else {fault = 1;return 0}
            unlocks[surface,default:0] &+= 1;return 0
        case 0x4c96b0:return 0 //Actual original RET leaf at both pre/post slots.
        default:unresolved.insert(call.function);fault = 1;return 0
        }
    }
}
private let nativeWarpFadeDependency:ClawPlayerFadeDependency = {context,event,user in
    guard let context,let event,let user else {return 0}
    let owner = Unmanaged<ClawNativeWarpFade>.fromOpaque(user).takeUnretainedValue()
    let result = owner.service(event.pointee);if owner.fault != 0 {context.pointee.fault = owner.fault};return result
}
