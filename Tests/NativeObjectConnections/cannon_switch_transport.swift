import Foundation

private let actor:UInt32=0x03000000, logic:UInt32=0x03001000, boss:UInt32=0x03009000
private let observed:Set<UInt32>=[0x4f63ec,0x4a48e0,0x415840,0x4c7fa0,0x4c8060,0x4c8160,0x4c81b0,0x4c7970,0x4f6286,0x465450,0x4dba00,0x4dc870,0x4f6974,0x4c9e30,0x415470,0x4159b0,0x415a60,0x4c8220,0x4c82a0,0x4c96b0,0x4041b0,0x484d90,0x4f6428]
private struct Input:Decodable {
    struct Segment:Decodable {let address:UInt32;let bytes:[UInt8]}
    struct Action:Decodable {let command:UInt32,boss:UInt32,delta:UInt32,done:UInt32}
    let segments:[Segment],actions:[Action],imports:[String:UInt32]
}
private final class Probe {
    let heap=ClawTokenHeap()
    let host:ClawNativeCanonicalHost
    let memory:ClawNativeMfcMemory
    var calls:[UInt32]=[]
    var envelopes:[[String:Any]]=[]
    var missing:UInt32?,reentry=false
    var failureBoundary:[String:UInt32]=[:]
    init(_ input:Input) throws {
        host=ClawNativeCanonicalHost(heap:heap)
        for segment in input.segments {
            let pointer=heap.storeBytes(token:segment.address,count:UInt32(segment.bytes.count))
            segment.bytes.withUnsafeBufferPointer {p in pointer.update(from:p.baseAddress!,count:p.count)}
        }
        let imports=Dictionary(uniqueKeysWithValues:input.imports.map {(UInt32($0.key)!, $0.value)})
        memory=try ClawNativeMfcMemory(host:host,sha256:ClawNativeMfcMemory.imageHash,importTargets:imports,sceneObjectAllocations:true)
        memory.beforeService={[weak self] function,arguments in
            if function==0x4a48e0 {self?.record(function,receiver:0,arguments:arguments)}
        }
        host.stacklessCallerReserve=0x100
        host.observer={[weak self] call in
            guard let self,observed.contains(call.function) else {return}
            let arguments=withUnsafeBytes(of:call.arguments) {Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
            self.record(call.function,receiver:call.receiver,arguments:arguments)
        }
        host.dependency={[weak self] host,call in
            guard let self,host === self.host,call.function != self.missing else {return nil}
            if self.reentry {_=self.invoke(0x415350,args:[actor])}
            if call.function==0x4f6286 {
                let resources:[UInt32:UInt32]=[0x522d54:0x03003000,0x522d48:0x03003100,0x524664:0x03004000,0x524648:0x03005000,0x52462c:0x03006000]
                guard call.argumentCount==2,let resource=resources[call.arguments.0],
                      let pointer=host.bytes(call.arguments.1,count:4) else {return nil}
                var word=resource.littleEndian
                withUnsafeBytes(of:&word) {pointer.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:4)}
                return 1
            }
            if call.function==0x4f6974,call.argumentCount==1,call.arguments.0==0 {
                return self.get(call.receiver)
            }
            return nil
        }
    }
    private func record(_ function:UInt32,receiver:UInt32,arguments:[UInt32]) {
        calls.append(function)
        var arguments=arguments
        var envelope:[String:Any]=["function":function,"receiver":receiver,"argumentCount":arguments.count]
        if function==0x4f6286,arguments.count==2 {
            if let output=host.bytes(arguments[1],count:4) {
                envelope["outputCellBefore"]=UnsafeRawPointer(output).loadUnaligned(as:UInt32.self).littleEndian
            }
            arguments[1]=0 // synchronous borrowed output cell, normalized
        }
        envelope["arguments"]=arguments;envelopes.append(envelope)
    }
    func get(_ token:UInt32)->UInt32 {heap.lookup(token,words:1)![0]}
    func put(_ token:UInt32,_ value:UInt32) {heap.lookup(token,words:1)![0]=value}
    @discardableResult func invoke(_ function:UInt32=0x415350,receiver:UInt32=0,args:[UInt32]=[actor])->ClawNativeCanonicalHost.Completion {
        var call=ClawCall();call.function=function;call.receiver=receiver;call.argumentCount=UInt32(args.count)
        withUnsafeMutableBytes(of:&call.arguments) {b in for (i,v) in args.enumerated() {b.bindMemory(to:UInt32.self)[i]=v}}
        var completion:ClawNativeCanonicalHost.Completion?
        _=host.withObjectAllocation(provider:memory) {completion=host.invoke(call)}
        return completion ?? .init(completed:false,eax:nil,fault:host.fault)
    }
    func snapshot()->[String:Any] {
        var spans:[(UInt32,UInt32)]=[(actor,0x1b4),(logic,0x174),(0x537668,0x2c),(0x534c58,0x24),(0x537698,0x24),(boss,0x524),(0x5430c4,4),(0x532c0c,8),(0x53774c,4)]
        for event in memory.events where event.function==0x4a48e0 {
            if let token=event.result,token != 0,let size=event.arguments.first,memory.ownsObjectAllocation(token,count:size) {
                spans.append((token,size))
            }
        }
        var bytes:[String:[UInt8]]=[:]
        for (a,n) in spans {if let p=heap.lookupBytes(a,count:n) {bytes[String(a)]=Array(UnsafeBufferPointer(start:p,count:Int(n)))}}
        return ["bytes":bytes,"helper":get(logic+0x18),"calls":calls,"envelopes":envelopes]
    }
    func initialize()->Bool {invoke().completed && host.fault==nil}
    func run(_ action:Input.Action)->Bool {
        put(logic+0x1c,action.command);put(0x5430c4,action.delta);put(boss+0x518,action.boss)
        if action.done != 0 {put(actor+0x1a4,1);put(actor+0x19c,0)}
        calls=[];envelopes=[]
        return invoke().completed && host.fault==nil
    }
}

@main private enum Main {
    static func main() throws {
        let input=try JSONDecoder().decode(Input.self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
        let probe=try Probe(input)
        var snapshots:[[String:Any]]=[]
        for action in input.actions {
            guard probe.run(action) else {return try output(probe,snapshots: snapshots,controls:[:])}
            snapshots.append(probe.snapshot())
        }
        probe.calls=[];probe.envelopes=[]
        guard probe.host.retireCannonSwitch(actor:actor,provider:probe.memory) else {return try output(probe,snapshots:snapshots,controls:[:])}
        snapshots.append(probe.snapshot())
        probe.put(logic+0x1c,0);probe.calls=[];probe.envelopes=[]
        guard probe.initialize() else {return try output(probe,snapshots:snapshots,controls:[:])}
        snapshots.append(probe.snapshot())
        var controls:[String:Bool]=[:]
        func check(_ name:String,_ body:(Probe)->Bool) throws {
            let test=try Probe(input);controls[name]=body(test)
        }
        try check("wrong-callback") {$0.put(logic+0x10,0x414cc0);return !$0.initialize()}
        try check("wrong-vtable") {$0.put(0x50ba64+8,0x414de0);return !$0.initialize()}
        try check("wrong-size-and-context") {!$0.invoke(0x4f63ec,args:[0x58]).completed}
        try check("constructor-without-allocation") {!$0.invoke(0x415840,receiver:0x03003000,args:[actor]).completed}
        try check("lifecycle-receiver-outside-election") {!$0.invoke(0x4c9e30,receiver:actor,args:[0x523148]).completed}
        try check("wrong-continuation") {
            let test=$0
            test.memory.beforeObjectAllocation={ request in
                guard let p=test.host.bytes(request.context.esp,count:4) else {return}
                p[0] ^= 1
            }
            return !test.initialize()
        }
        try check("wrong-provider") {
            let test=$0
            guard test.initialize() else {return false}
            let imports=Dictionary(uniqueKeysWithValues:input.imports.map {(UInt32($0.key)!, $0.value)})
            guard let other=try? ClawNativeMfcMemory(host:test.host,sha256:ClawNativeMfcMemory.imageHash,importTargets:imports,sceneObjectAllocations:true) else {return false}
            test.put(logic+0x1c,29)
            var call=ClawCall();call.function=0x415350;call.argumentCount=1;call.arguments.0=actor
            let result=test.host.withObjectAllocation(provider:other) {test.host.invoke(call)}
            return result==nil || result?.completed==false
        }
        try check("missing-enabled-audio-owner") {
            guard $0.initialize() else {return false}
            $0.put(0x532c0c,1);$0.put(logic+0x1c,1);$0.put(boss+0x518,1)
            return !$0.invoke().completed
        }
        try check("missing-state-registration") {
            guard $0.initialize() else {return false}
            $0.put(0x03007100,0);$0.put(logic+0x1c,1)
            return !$0.invoke().completed
        }
        try check("replaced-logic-allocation") {
            guard $0.initialize() else {return false}
            let bytes=Array(UnsafeBufferPointer(start:$0.heap.lookupBytes(logic,count:0x174)!,count:0x174))
            $0.heap.free(logic);let fresh=$0.heap.storeBytes(token:logic,count:0x174)
            bytes.withUnsafeBufferPointer {fresh.update(from:$0.baseAddress!,count:$0.count)}
            $0.put(logic+0x1c,29);return !$0.invoke().completed
        }
        try check("missing-resource-owner") {$0.missing=0x4f6286;return !$0.initialize()}
        try check("reentry") {$0.reentry=true;return !$0.initialize()}
        try check("foreign-free") {!$0.memory.releaseSceneObject(actor)}
        try check("stale-helper") {
            guard $0.initialize() else {return false};let helper=$0.get(logic+0x18)
            guard $0.host.retireCannonSwitch(actor:actor,provider:$0.memory) else {return false}
            $0.put(logic+0x18,helper);$0.put(logic+0x1c,29);return !$0.invoke().completed
        }
        try check("double-free") {
            guard $0.initialize() else {return false};let helper=$0.get(logic+0x18)
            return $0.host.retireCannonSwitch(actor:actor,provider:$0.memory) && !$0.memory.releaseSceneObject(helper)
        }
        try check("replaced-helper-allocation") {
            guard $0.initialize() else {return false};let helper=$0.get(logic+0x18)
            let bytes=Array(UnsafeBufferPointer(start:$0.heap.lookupBytes(helper,count:0x54)!,count:0x54))
            $0.heap.free(helper);let fresh=$0.heap.storeBytes(token:helper,count:0x54)
            bytes.withUnsafeBufferPointer {fresh.update(from:$0.baseAddress!,count:$0.count)}
            $0.put(logic+0x1c,29);return !$0.invoke().completed
        }
        try check("replaced-actor-allocation") {
            guard $0.initialize() else {return false}
            let bytes=Array(UnsafeBufferPointer(start:$0.heap.lookupBytes(actor,count:0x1b4)!,count:0x1b4))
            $0.heap.free(actor);let fresh=$0.heap.storeBytes(token:actor,count:0x1b4)
            bytes.withUnsafeBufferPointer {fresh.update(from:$0.baseAddress!,count:$0.count)}
            $0.put(logic+0x1c,29);return !$0.invoke().completed
        }
        let allocationFailure=try Probe(input)
        allocationFailure.memory.failAllocation={_ in true}
        let failed = !allocationFailure.initialize()
        probe.failureBoundary=["address":allocationFailure.host.fault?.address ?? 0,"command":allocationFailure.get(logic+0x1c),"helper":allocationFailure.get(logic+0x18)]
        controls["original-allocation-failure"]=failed && allocationFailure.host.fault?.address==0x5022b5 && !allocationFailure.memory.ownsObjectAllocation(0x62000000,count:0x54)

        try check("missing-lifecycle-owner") {
            guard $0.initialize() else {return false};$0.missing=0x4f6974;$0.put(logic+0x1c,1);return !$0.invoke().completed
        }
        try output(probe,snapshots:snapshots,controls:controls)
    }
    private static func output(_ probe:Probe,snapshots:[[String:Any]],controls:[String:Bool]) throws {
        let fault:Any=probe.host.fault.map { ["code":$0.code,"address":$0.address,"diagnostic":String(describing:$0.diagnostic)] as [String:Any] } ?? NSNull()
        let data=try JSONSerialization.data(withJSONObject:["snapshots":snapshots,"controls":controls,"fault":fault,"allocationFailure":probe.failureBoundary],options:[.sortedKeys])
        print(String(decoding:data,as:UTF8.self))
    }
}
