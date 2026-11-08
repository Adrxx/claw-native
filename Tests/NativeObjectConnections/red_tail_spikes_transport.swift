import Foundation

@main struct RedTailSpikesTransport {
    static let actor:UInt32=0x61000000, logic:UInt32=0x61000200
    static let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map {( $0.element,UInt32(0x710000+$0.offset*4))})
    static let edges:Set<UInt32>=[0x4f63ec,0x484680,0x4c7fa0,0x4c8060,0x432c20,0x4dba00,0x4c96b0,0x4dc870,0x4c9e30,0x4843d0,0x42a680,0x4041b0,0x484d90,0x4f6286,0x4f6974,0x4a30e0]
    static func decode(_ hex:String)->[UInt8] {
        let chars=Array(hex.utf8)
        func nibble(_ b:UInt8)->UInt8 {b<=57 ? b-48:b-87}
        return stride(from:0,to:chars.count,by:2).map {nibble(chars[$0])*16+nibble(chars[$0+1])}
    }
    static func hex(_ heap:ClawTokenHeap,_ a:UInt32,_ n:UInt32)->String {Array(UnsafeBufferPointer(start:heap.lookupBytes(a,count:n)!,count:Int(n))).map {String(format:"%02x",$0)}.joined()}
    static func main() throws {
        let directory=URL(fileURLWithPath:CommandLine.arguments[1])
        let profiles=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inputs.json"))) as! [[String:Any]]
        func setup(_ profile:[String:Any]) throws -> (ClawTokenHeap,ClawNativeCanonicalHost,ClawNativeMfcMemory) {
            let heap=ClawTokenHeap()
            for span in profile["spans"] as! [[String:Any]] {
                let a=(span["address"] as! NSNumber).uint32Value,b=decode(span["hex"] as! String)
                if a==actor || a==logic {
                    let token=heap.allocateSceneObject(bytes:UInt32(b.count),minimumToken:a)
                    precondition(token==a,"scene token expected \(String(a,radix:16)) got \(String(token,radix:16))")
                }
                b.withUnsafeBufferPointer {
                    let destination=heap.lookupBytes(a,count:UInt32(b.count)) ?? heap.storeBytes(token:a,count:UInt32(b.count))
                    destination.update(from:$0.baseAddress!,count:b.count)
                }
            }
            let host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
            let memory=try ClawNativeMfcMemory(host:host,sha256:ClawNativeMfcMemory.imageHash,importTargets:imports,sceneObjectAllocations:true)
            host.dependency={h,c in
                if c.function==0x4f6286 {
                    guard c.receiver==0x61000510,c.argumentCount==2,[UInt32(0x522d54),0x522d48].contains(c.arguments.0),let out=h.bytes(c.arguments.1,count:4) else {return nil}
                    out.withMemoryRebound(to:UInt32.self,capacity:1) {$0.pointee=c.arguments.0==0x522d54 ? 0x61000600:0x61000640};return 1
                }
                if c.function==0x4f6974 {
                    guard c.receiver==0x61000700,c.argumentCount==1,c.arguments.0==0 else {return nil}
                    return heap.lookup(c.receiver,words:1)?[0]
                }
                return nil
            }
            return (heap,host,memory)
        }
        func callback(_ host:ClawNativeCanonicalHost,_ memory:ClawNativeMfcMemory,_ command:UInt32,_ actor:UInt32=actor)->Bool {
            host.heap.lookup(host.heap.lookup(actor+0x6c,words:1)![0]+0x1c,words:1)![0]=command
            var call=ClawCall();call.function=0x4842b0;call.argumentCount=1;call.arguments.0=actor
            return host.withObjectAllocation(provider:memory) {host.invoke(call).completed} ?? false
        }
        for (i,profile) in profiles.enumerated() {
            let (heap,host,memory)=try setup(profile);var trace:[[UInt32]]=[],snapshots:[[String:Any]]=[]
            host.observer={c in if edges.contains(c.function) {
                var args=withUnsafeBytes(of:c.arguments) {Array($0.bindMemory(to:UInt32.self).prefix(Int(c.argumentCount)))}
                if c.function==0x4f6286 {args[1]=0}
                trace.append([c.function,c.receiver]+args)
            }}
            func snapshot(_ label:String) {
                var allocations:[String:String]=[:]
                for a in memory.sceneObjectPointers {let n:UInt32=memory.ownsObjectAllocation(a,count:0x48) ? 0x48:0x174;allocations[String(a)]=hex(heap,a,n)}
                var globals:[String:String]=[:]
                for (a,n):(UInt32,UInt32) in [(0x537668,0x2c),(0x53c1d8,0x24),(0x537698,0x24)] {globals[String(a)]=hex(heap,a,n)}
                snapshots.append(["label":label,"actor":hex(heap,actor,0x1b4),"logic":hex(heap,logic,0x174),"allocations":allocations,"globals":globals,"trace":trace])
            }
            for cycle in 0..<2 {
                for command:UInt32 in [0,1000,29,30,7] {
                    guard callback(host,memory,command) else {fatalError("profile \(i), cycle \(cycle), command \(command): \(String(describing:host.fault)) trace \(trace.map{String($0[0],radix:16)})")}
                    snapshot("\(cycle):\(command)")
                }
                let hit=heap.lookup(actor+0x70,words:1)![0],attack=heap.lookup(actor+0x78,words:1)![0]
                precondition(host.retireRedTailSpikes(actor:actor,provider:memory),"retire \(String(describing:host.fault))")
                precondition(memory.ownsObjectAllocation(hit,count:0x174) && memory.ownsObjectAllocation(attack,count:0x174))
                snapshot("\(cycle):retire")
            }
            try JSONSerialization.data(withJSONObject:snapshots,options:[.sortedKeys]).write(to:directory.appendingPathComponent("native-\(i).json"))
        }
        // Each negative control uses a fresh host because faults are sticky.
        for control in ["missing-service","wrong-provider","wrong-actor","stale-helper","replaced-helper","reentrant-service","replaced-vtable","secondary-replacement","direct-free","canonical-shadow"] {
            let (heap,host,memory)=try setup(profiles[0]);let service=host.dependency
            if control=="missing-service" {host.dependency=nil}
            if control=="reentrant-service" {
                host.dependency={h,c in var call=ClawCall();call.function=0x4842b0;call.argumentCount=1;call.arguments.0=actor;_ = h.invoke(call);return service?(h,c)}
            }
            if ["missing-service","reentrant-service"].contains(control) {precondition(!callback(host,memory,0),control);continue}
            precondition(callback(host,memory,0),"setup \(control) \(String(describing:host.fault))")
            let helper=heap.lookup(logic+0x18,words:1)![0]
            if control=="wrong-provider" {
                let foreign=try ClawNativeMfcMemory(host:host,sha256:ClawNativeMfcMemory.imageHash,importTargets:imports,allocationBase:0x63000000,sceneObjectAllocations:true)
                precondition(!callback(host,foreign,29),control);continue
            }
            if control=="canonical-shadow" {
                host.dependency={h,c in
                    precondition(!edges.contains(c.function) || [UInt32(0x4f6286),0x4f6974].contains(c.function),"canonical shadow")
                    return service?(h,c)
                }
                precondition(callback(host,memory,7),control);continue
            }
            if control=="direct-free" {precondition(!memory.releaseSceneObject(helper),control);continue}
            if control=="wrong-actor" {
                let copy=heap.store(token:0x61002000,words:0x1b4/4)
                copy.update(from:heap.lookup(actor,words:0x1b4/4)!,count:0x1b4/4)
                precondition(!callback(host,memory,29,0x61002000),control);continue
            }
            if control=="stale-helper" {precondition(host.retireRedTailSpikes(actor:actor,provider:memory));heap.lookup(logic+0x18,words:1)![0]=helper}
            if control=="replaced-helper" || control=="secondary-replacement" {
                let a=control=="replaced-helper" ? helper:heap.lookup(actor+0x70,words:1)![0],n:UInt32=control=="replaced-helper" ? 0x48:0x174
                let data=Array(UnsafeBufferPointer(start:heap.lookupBytes(a,count:n)!,count:Int(n)))
                heap.free(a);data.withUnsafeBufferPointer {heap.storeBytes(token:a,count:n).update(from:$0.baseAddress!,count:Int(n))}
            }
            if control=="replaced-vtable" {heap.lookup(0x50f44c,words:1)![0]=0x42a680}
            precondition(!callback(host,memory,29),control)
        }
        print("{\"native_controls\":10,\"status\":\"pass\"}")
    }
}
