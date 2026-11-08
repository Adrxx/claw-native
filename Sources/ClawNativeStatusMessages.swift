import Foundation
import CoreGraphics

// Source config/CStringList helpers retain message ownership and timers.
// Font and native text rendering are explicit physical GDI transports.
final class ClawNativeStatusMessages {
    static let getDC:UInt32 = 0x70011044,releaseDC:UInt32 = 0x70011068
    struct TextDraw: Codable, Equatable { let text:String,rect:CGRect,flags:UInt32,color:UInt32,fontHeight:Int,fontWidth:Int }
    let heap:ClawTokenHeap,saves:ClawNativeSave,application:UInt32,config:UInt32
    private let temporary:UInt32,output:UInt32
    private(set) var fault:UInt32 = 0,unresolved:Set<UInt32> = []
    private(set) var sourceCalls:[UInt32:UInt64] = [:]
    private(set) var fontArguments:[UInt32] = []
    private(set) var textDraws:[TextDraw] = [],getDCCount = 0,releaseDCCount = 0
    private var selectedFont:UInt32 = 0x73000000,textColor:UInt32 = 0xffffff,backgroundMode:UInt32 = 1
    var count:UInt32 { heap.lookup(config,words:14)![3] }
    var timer:UInt32 { heap.lookup(config,words:14)![8] }
    init(heap:ClawTokenHeap,saves:ClawNativeSave,application:UInt32) {
        self.heap = heap;self.saves = saves;self.application = application
        config = heap.lookup(application,words:77)![0x4c/4]
        // Caller-owned views of dead automatic CString objects; they are not
        // original heap allocator events and are kept distinct from each other.
        temporary = heap.allocate(bytes:4);output = heap.allocate(bytes:4)
        for (token,value) in [(UInt32(0x5253a8),"Your game has been saved"),(0x5253c4,"Your game was not saved because you cheated!"),(0x5250b0,"ARIAL")] {
            let bytes = Array(value.utf8)+[UInt8(0)]
            if heap.lookup(token,words:UInt32((bytes.count+3)/4)) == nil { _ = heap.store(token:token,words:(bytes.count+3)/4) }
            bytes.withUnsafeBytes{UnsafeMutableRawPointer(heap.lookup(token,words:UInt32((bytes.count+3)/4))!).copyMemory(from:$0.baseAddress!,byteCount:$0.count)}
        }
        // Exact42614c..42616b source constructor interval; the other words are
        // initialized only by whole4222a0 below, not blanket zeroed here.
        _ = entry(0x4f5249,receiver:config,arguments:[10])
        let c = heap.lookup(config,words:14)!
        c[7] = heap.lookup(0x52e1cc,words:1)!.pointee;c[12] = 0;c[13] = 0
        _ = entry(0x4222a0,receiver:config,arguments:[5000,2000])
    }
    deinit { if fault == 0 { _ = entry(0x4f5288,receiver:config) } }
    @discardableResult func entry(_ function:UInt32,receiver:UInt32? = nil,arguments:[UInt32] = []) -> UInt32 {
        var context = ClawPlayerStartupContext(),result:UInt32 = 0
        context.scene = saves.sourceHost;claw_player_startup_defaults(&context)
        sourceCalls[function,default:0] &+= 1
        let done = heap.withStableFreedStorage{arguments.withUnsafeBufferPointer{claw_player_startup_entry(function,receiver ?? application,$0.baseAddress,UInt32($0.count),&context,nativeStatusStartupDependency,Unmanaged.passUnretained(self).toOpaque(),&result)}}
        fault = max(fault,context.fault);if done != 1 { unresolved.insert(function);fault = max(1,fault) };return result
    }
    fileprivate func startupService(_ call:ClawPlayerStartupCall) -> UInt32 {
        if call.function == 0x546918 {
            guard call.bufferCount == 1,call.bufferBytes.0 == 56,let raw = call.buffers.0 else { fault = 1;return 0 }
            fontArguments = Array(UnsafeBufferPointer(start:raw.assumingMemoryBound(to:UInt32.self),count:14))
            return 0x73000001 // A native font descriptor handle, not a Win32 HFONT.
        }
        guard [UInt32(0x4f6449),0x4f66cc,0x4f6584].contains(call.function) else { unresolved.insert(call.function);fault = 1;return 0 }
        var receiver = call.receiver,argument = call.arguments.0
        if call.localMask != 0 {
            guard call.bufferCount == 1,call.bufferBytes.0 == 4,let raw = call.buffers.0 else { fault = 1;return 0 }
            let local = raw.assumingMemoryBound(to:UInt32.self)
            heap.lookup(temporary,words:1)!.pointee = local.pointee
            if call.localMask&0x100 != 0 { receiver = temporary }
            if call.localMask&1 != 0 { argument = temporary }
            let result = saves.stringService(call.function,receiver:receiver,argument:argument)
            local.pointee = heap.lookup(temporary,words:1)!.pointee;fault = max(fault,saves.fault);return result
        }
        let result = saves.stringService(call.function,receiver:receiver,argument:argument)
        fault = max(fault,saves.fault);return result
    }
    func frameService(_ call:ClawGameFrameServiceCall) -> UInt32? {
        if call.function == Self.getDC {
            guard call.localMask == 2,call.bufferCount == 1,call.bufferBytes.0 == 4,let raw = call.buffers.0 else { fault = 1;return 0 }
            raw.assumingMemoryBound(to:UInt32.self).pointee = 0x74000001;getDCCount += 1;return 0
        }
        if call.function == Self.releaseDC { releaseDCCount += 1;return 0 }
        if call.function == 0x546888 { let old = backgroundMode;backgroundMode = call.arguments.1;return old }
        if call.function == 0x546880 { let old = textColor;textColor = call.arguments.1;return old }
        if call.function == 0x4226b0 {
            let a:[UInt32] = [call.arguments.0,call.arguments.1,call.arguments.2,call.arguments.3]
            var rect:UnsafeMutablePointer<UInt32>?
            if call.localMask&4 != 0 {
                guard call.bufferCount > 0,call.bufferBytes.0 == 16,let raw = call.buffers.0 else { fault = 1;return 0 };rect = raw.assumingMemoryBound(to:UInt32.self)
            }
            var context = ClawMessageDrawingContext(),result:UInt32 = 0
            context.scene = saves.sourceHost;context.emptyStringToken = 0x52e1c4;claw_message_drawing_defaults(&context)
            context.textLimit = 1024 // Declared native buffer guard, not a source capacity claim.
            let done = heap.withStableFreedStorage{a.withUnsafeBufferPointer{claw_message_drawing_entry(call.function,call.receiver,$0.baseAddress,4,rect,&context,nativeStatusDrawingDependency,Unmanaged.passUnretained(self).toOpaque(),&result)}}
            fault = max(fault,context.fault);if done != 1 { unresolved.insert(call.function);fault = max(1,fault) };return result
        }
        if call.function == 0x4f53eb {
            guard call.localMask == 1,call.bufferCount == 1,call.bufferBytes.0 == 4,let raw = call.buffers.0 else { fault = 1;return 0 }
            let result = entry(call.function,receiver:call.receiver,arguments:[output])
            raw.assumingMemoryBound(to:UInt32.self).pointee = heap.lookup(output,words:1)!.pointee
            return result
        }
        if call.function == 0x4f6584 && call.localMask == 0x100 {
            guard call.bufferCount == 1,call.bufferBytes.0 == 4,let raw = call.buffers.0 else { fault = 1;return 0 }
            heap.lookup(output,words:1)!.pointee = raw.assumingMemoryBound(to:UInt32.self).pointee
            let result = saves.stringService(call.function,receiver:output)
            raw.assumingMemoryBound(to:UInt32.self).pointee = heap.lookup(output,words:1)!.pointee
            fault = max(fault,saves.fault);return result
        }
        if call.function == 0x4f650f {
            let result = saves.stringService(call.function,receiver:call.receiver);fault = max(fault,saves.fault);return result
        }
        return nil
    }
    func beginFrame() { textDraws.removeAll(keepingCapacity:true) }
    func installDrawingBridge(target:UInt32) {
        // Native surface/DC views satisfy the exact offsets consumed by the
        // original overlay. Slot identities below are physical host methods.
        let t = heap.lookup(target,words:12)!,backend = heap.lookup(t[11],words:3)!
        //The source display already owns this DD identity. Install physical
        //text/DC methods in its existing table so copies/Flip/Release continue
        //using the same surface, rather than replacing the DD object.
        let iface = backend[2],table = heap.lookup(iface,words:1)!.pointee
        let slots = heap.lookup(table,words:27)!;slots[0x44/4] = Self.getDC;slots[0x68/4] = Self.releaseDC
        if heap.lookup(0x534ef8,words:256) == nil { _ = heap.store(token:0x534ef8,words:256) }
        if heap.lookup(0x5250d8,words:1) == nil { heap.store(token:0x5250d8,words:1).pointee = 10 }
    }
    fileprivate func drawingService(_ call:ClawMessageDrawingCall) -> UInt32 {
        if call.function == 0x54691c { let previous = selectedFont;selectedFont = call.arguments.1;return previous }
        if call.function == 0x4f6428 { heap.free(call.arguments.0);return 0 }
        if call.function == 0x4f66cc {
            guard call.localMask == 0x100,call.bufferCount == 1,call.bufferBytes.0 == 4,let raw = call.buffers.0 else { fault = 1;return 0 }
            let local = raw.assumingMemoryBound(to:UInt32.self);heap.lookup(temporary,words:1)!.pointee = local.pointee
            let result = saves.stringService(call.function,receiver:temporary,argument:call.arguments.0)
            local.pointee = heap.lookup(temporary,words:1)!.pointee;fault = max(fault,saves.fault);return result
        }
        if call.function == 0x546d30 {
            let normalized = call.localMask&8 != 0,index = normalized ? 1 : 0
            var rect:UnsafeMutablePointer<UInt32>?
            if normalized { rect = call.buffers.0?.assumingMemoryBound(to:UInt32.self) }
            else if call.arguments.3 != 0 { rect = heap.lookup(call.arguments.3,words:4) }
            let data = index == 1 ? call.buffers.1 : call.buffers.0
            guard let rect,let data else { fault = 1;return 0 }
            let count = Int(call.arguments.2),text = String(decoding:UnsafeRawBufferPointer(start:data,count:count),as:UTF8.self)
            let left = Int32(bitPattern:rect[0]),top = Int32(bitPattern:rect[1]),right = Int32(bitPattern:rect[2]),bottom = Int32(bitPattern:rect[3])
            let height = fontArguments.isEmpty ? 12 : abs(Int(Int32(bitPattern:fontArguments[0])))
            let width = fontArguments.count>1 ? abs(Int(Int32(bitPattern:fontArguments[1]))) : 8
            textDraws.append(TextDraw(text:text,rect:CGRect(x:Int(left),y:Int(top),width:Int(right)-Int(left),height:Int(bottom)-Int(top)),flags:call.arguments.4,color:textColor,fontHeight:height,fontWidth:width))
            return UInt32(height) // Native text raster/layout remains physical transport.
        }
        unresolved.insert(call.function);fault = 1;return 0
    }
}
private let nativeStatusStartupDependency:ClawPlayerStartupDependency = {context,event,user in
    guard let context,let event,let user else { return 0 };let owner = Unmanaged<ClawNativeStatusMessages>.fromOpaque(user).takeUnretainedValue()
    let result = owner.startupService(event.pointee);if owner.fault != 0 { context.pointee.fault = owner.fault };return result
}
private let nativeStatusDrawingDependency:ClawMessageDrawingDependency = {context,event,user in
    guard let context,let user else { return 0 };let owner = Unmanaged<ClawNativeStatusMessages>.fromOpaque(user).takeUnretainedValue()
    let result = owner.drawingService(event);if owner.fault != 0 { context.pointee.fault = owner.fault };return result
}

extension ClawNativeStatusMessages {
    struct SavedState: Codable, Equatable {
        let application: UInt32, config: UInt32, temporary: UInt32, output: UInt32
        let fault: UInt32, unresolved: Set<UInt32>, calls: [UInt32: UInt64], font: [UInt32], draws: [TextDraw]
        let getDC: Int, releaseDC: Int, selectedFont: UInt32, color: UInt32, background: UInt32
    }
    func savedState() -> SavedState {
        .init(application: application, config: config, temporary: temporary, output: output, fault: fault, unresolved: unresolved,
            calls: sourceCalls, font: fontArguments, draws: textDraws, getDC: getDCCount, releaseDC: releaseDCCount,
            selectedFont: selectedFont, color: textColor, background: backgroundMode)
    }
    func restoreState(_ saved: SavedState) throws {
        guard saved.application == application, saved.config == config, saved.temporary == temporary, saved.output == output else { throw ClawSnapshotError.invalidState }
        fault = saved.fault; unresolved = saved.unresolved; sourceCalls = saved.calls; fontArguments = saved.font; textDraws = saved.draws
        getDCCount = saved.getDC; releaseDCCount = saved.releaseDC; selectedFont = saved.selectedFont; textColor = saved.color; backgroundMode = saved.background
    }
}
