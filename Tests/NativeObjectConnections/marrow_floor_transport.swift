import Foundation

private let actor:UInt32=0x30000000, logic:UInt32=0x30000400
private let observed:Set<UInt32>=[0x4f63ec,0x45a7c0,0x4c96b0,0x4dc870,0x4c9e30,0x45a400,0x4041b0,0x484d90,0x4f6428,0x4c7fa0,0x4c8060,0x4c7970,0x406290,0x4dba00,0x4f6286,0x4f6974]
private struct Region:Decodable {let token:UInt32;let bytes:[UInt8]}
private struct Input:Decodable {let sha256:String;let regions:[Region];let commands:[UInt32];let allocator_fill:UInt8}
private enum CheckFailure:Error {case failed(String)}
private func need(_ value:Bool,_ message:String) throws {if !value {throw CheckFailure.failed(message)}}
private final class Fixture {
    let heap:ClawTokenHeap
    let host:ClawNativeCanonicalHost
    let memory:ClawNativeMfcMemory
    var calls:[[String:Any]]=[]
    var missing=false
    init(_ input:Input) throws {
        let h=ClawTokenHeap();heap=h
        for r in input.regions {r.bytes.withUnsafeBytes {bytes in
            UnsafeMutableRawPointer(h.storeBytes(token:r.token,count:UInt32(bytes.count))).copyMemory(from:bytes.baseAddress!,byteCount:bytes.count)
        }}
        let targets=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map {index,slot in (slot,UInt32(0x710000+index*16))})
        for (slot,target) in targets {heap.lookup(slot,words:1)![0]=target}
        // The host binds exact allocator sentinel identity, not an executable guest page.
        heap.store(token:0x3000c000,words:1)[0]=0
        host=ClawNativeCanonicalHost(heap:heap)
        host.stacklessCallerReserve=0x40
        memory=try ClawNativeMfcMemory(host:host,sha256:input.sha256,importTargets:targets,sceneObjectAllocations:true)
        host.observer={ [weak self] call in
            guard observed.contains(call.function) else {return}
            var arguments=withUnsafeBytes(of:call.arguments) {Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
            if call.function==0x4f6286 {arguments[1]=UInt32.max}
            let noReceiver:Set<UInt32>=[0x4f63ec,0x4dc870,0x4c9e30,0x4f6428]
            self?.calls.append(["function":call.function,"receiver":noReceiver.contains(call.function) ? 0:call.receiver,"arguments":arguments])
        }
        host.dependency={ [weak self] host,call in
            guard let self,!self.missing else {return nil}
            if call.function==0x4f6286 {
                guard call.argumentCount==2,let cell=host.bytes(call.arguments.1,count:4) else {return nil}
                let values:[UInt32:UInt32]=[0x522d54:0x30003000,0x522d48:0x30003100,0x528a4c:0x30005000,0x528a3c:0]
                guard let value=values[call.arguments.0] else {return nil}
                UnsafeMutableRawPointer(cell).storeBytes(of:value.littleEndian,as:UInt32.self);self.calls[self.calls.count-1]["output"]=UnsafeRawPointer(cell).loadUnaligned(as:UInt32.self).littleEndian;return 1
            }
            if call.function==0x4f6974 {
                guard call.argumentCount==1,call.arguments.0==0,let cell=self.heap.lookup(call.receiver,words:1) else {return nil}
                if cell[0]==0 {cell[0]=0x3000c000};return cell[0]
            }
            return nil
        }
    }
    func command(_ command:UInt32,callback:UInt32=0x45a2e0,owner:UInt32=actor) -> Bool {
        heap.lookup(logic+0x1c,words:1)![0]=command;calls=[]
        var call=ClawCall();call.function=callback;call.argumentCount=1;call.arguments.0=owner
        return host.withObjectAllocation(provider:memory) {host.invoke(call).completed}==true
    }
    func bytes(_ address:UInt32,_ count:UInt32) -> [UInt8] {Array(UnsafeBufferPointer(start:heap.lookupBytes(address,count:count)!,count:Int(count)))}
    func snapshot() -> [String:Any] {
        let storage=memory.tlsSnapshot()
        let allocations:[Any]=storage.allocations.filter {$0.kind=="object-malloc"}.map {entry in
            [entry.address,entry.size,storage.allocationBytes[String(entry.address)]!] as [Any]
        }
        return ["actor":bytes(actor,0x1b4),"logic":bytes(logic,0x174),"allocations":allocations,
                "globals":[UInt32(0x537684),0x537688,0x53768c,0x537690,0x5376b8,0x537b40].map {[$0,heap.lookup($0,words:1)![0]]},"calls":calls]
    }
}

@main private enum MarrowFloorTransport {
    static func main() throws {
        let input=try JSONDecoder().decode(Input.self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
        try need(input.allocator_fill==0xcc,"physical allocator fill configuration")
        let f=try Fixture(input);var steps:[[String:Any]]=[]
        for command in input.commands {
            try need(f.command(command),"command \(command) failed: \(String(describing:f.host.fault))")
            steps.append(f.snapshot())
        }
        let helper=f.heap.lookup(logic+0x18,words:1)![0];f.calls=[]
        try need(f.host.retireMarrowFloor(actor:actor,provider:f.memory),"retirement failed: \(String(describing:f.host.fault))")
        let retired=f.snapshot()
        var controls:[String:Bool]=[:]
        controls["same-owner-retirement"] = !f.memory.ownsObjectAllocation(helper,count:0x6c) && f.heap.lookup(logic+0x18,words:1)![0]==0
        controls["reallocation"] = f.command(0) && f.heap.lookup(logic+0x18,words:1)![0] != helper
        let reallocated=f.snapshot()
        do {let t=try Fixture(input);try need(t.command(0),"unauthorized release setup");let h=t.heap.lookup(logic+0x18,words:1)![0]
            controls["unauthorized-release"] = !t.memory.releaseSceneObject(h) && t.host.fault != nil && t.memory.ownsObjectAllocation(h,count:0x6c)
        }
        for target:UInt32 in [0x484d90,0x456030] {
            let t=try Fixture(input);try need(t.command(0),"direct destructor setup");let h=t.heap.lookup(logic+0x18,words:1)![0]
            var c=ClawCall();c.function=target;c.receiver=h;c.argumentCount=target==0x484d90 ? 1:0;c.arguments.0=1
            let r=t.host.withObjectAllocation(provider:t.memory){t.host.invoke(c)}
            controls["direct-destructor-\(target)"] = r?.completed != true && t.host.fault != nil && t.memory.ownsObjectAllocation(h,count:0x6c)
        }
        do {let t=try Fixture(input);t.missing=true;controls["missing-services"] = !t.command(0) && t.host.fault != nil}
        do {let t=try Fixture(input);t.heap.lookup(logic+0x10,words:1)![0]=0x453b10;controls["wrong-callback"] = !t.command(0) && t.host.fault != nil}
        do {let t=try Fixture(input);controls["wrong-actor"] = !t.command(0,owner:actor+4) && t.host.fault != nil}
        do {let t=try Fixture(input);var c=ClawCall();c.function=0x4f63ec;c.argumentCount=1;c.arguments.0=0x70;let r=t.host.withObjectAllocation(provider:t.memory){t.host.callNativeDependency(c)};controls["wrong-size"] = r == nil || t.host.fault != nil}
        do {let t=try Fixture(input);var c=ClawCall();c.function=0x45a7c0;c.receiver=0x62000000;c.argumentCount=1;c.arguments.0=actor;let r=t.host.withObjectAllocation(provider:t.memory){t.host.invoke(c)};controls["wrong-receiver"] = r?.completed != true && t.host.fault != nil}
        do {let t=try Fixture(input);try need(t.command(0),"stale setup");let h=t.heap.lookup(logic+0x18,words:1)![0];let old=t.bytes(h,0x6c);t.heap.free(h);old.withUnsafeBytes {UnsafeMutableRawPointer(t.heap.storeBytes(token:h,count:0x6c)).copyMemory(from:$0.baseAddress!,byteCount:0x6c)};controls["stale-allocation"] = !t.command(29) && t.host.fault != nil}
        for (label,token,count) in [("actor-identity",actor,UInt32(0x1b4)),("state-identity",logic,UInt32(0x174))] {
            let t=try Fixture(input);try need(t.command(0),"identity setup");let old=t.bytes(token,count);t.heap.free(token)
            old.withUnsafeBytes {UnsafeMutableRawPointer(t.heap.storeBytes(token:token,count:count)).copyMemory(from:$0.baseAddress!,byteCount:Int(count))}
            controls[label] = !t.command(29) && t.host.fault != nil
        }
        do {let t=try Fixture(input);t.memory.beforeObjectAllocation={_ in var c=ClawCall();c.function=0x45a2e0;c.argumentCount=1;c.arguments.0=actor;_ = t.host.invoke(c)};controls["reentry"] = !t.command(0) && t.host.fault != nil}
        do {let t=try Fixture(input);var replayDenied=true;var saved:ClawNativeCanonicalHost.ObjectAllocationRequest?
            t.memory.beforeObjectAllocation={request in replayDenied = replayDenied && !request.consume(for:t.host,provider:t.memory);saved=request}
            let completed=t.command(0);let expired=saved.map {t.memory.allocateObject($0)==nil} ?? false
            controls["single-use-request"] = completed && replayDenied && expired && t.host.fault != nil
        }
        do {let t=try Fixture(input);t.memory.beforeObjectAllocation={request in
            if let cell=t.host.bytes(request.context.esp,count:4) {UnsafeMutableRawPointer(cell).storeBytes(of:UInt32(0x4f6400),as:UInt32.self)}
        };controls["continuation-stack-mismatch"] = !t.command(0) && t.host.fault != nil && t.memory.tlsSnapshot().allocations.isEmpty}
        do {let t=try Fixture(input);t.memory.failAllocation={_ in true};controls["exhaustion"] = !t.command(0) && t.host.fault != nil && t.memory.tlsSnapshot().allocations.isEmpty}
        do {let t=try Fixture(input);let p=t.heap.storeBytes(token:0x62000000,count:0x6c);p.update(repeating:0xa5,count:0x6c);controls["occupied-allocation-exhaustion"] = !t.command(0) && t.host.fault != nil && t.bytes(0x62000000,0x6c)==Array(repeating:0xa5,count:0x6c)}
        do {let t=try Fixture(input);var cpu=ClawSourceContext();cpu.size=72;cpu.version=1;cpu.eip=0x4f63ec;cpu.esp=UInt32(CLAW_STACK_TOP);var c=ClawCall();c.function=0x4f63ec;c.argumentCount=1;c.arguments.0=0x6c;c.sourceReturnPC=0x45a31b;withUnsafeMutablePointer(to:&cpu){c.sourceContext=$0;_=t.host.withObjectAllocation(provider:t.memory){t.host.callNativeDependency(c)}};controls["context-continuation"] = t.host.fault != nil}
        controls["allocator-padding"] = input.allocator_fill==0xcc && f.bytes(f.heap.lookup(logic+0x18,words:1)![0]+0x38,4)==Array(repeating:0xcc,count:4)
        let output:[String:Any]=["steps":steps,"retired":retired,"reallocated":reallocated,"controls":controls]
        let data=try JSONSerialization.data(withJSONObject:output,options:[.sortedKeys]);print(String(decoding:data,as:UTF8.self))
    }
}
