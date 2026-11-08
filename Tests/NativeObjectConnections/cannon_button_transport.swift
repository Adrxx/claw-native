import Foundation

private func require(_ value: Bool, _ message: String) throws {
    if !value { throw NSError(domain: "CannonButtonTransport", code: 1, userInfo: [NSLocalizedDescriptionKey: message]) }
}
private struct Span: Codable { let token: UInt32; let bytes: [UInt8] }
private struct Trace: Codable { let function: UInt32; let receiver: UInt32; let args: [UInt32] }
private struct Step: Codable { let name: String; let command: UInt32; let spans: [Span]; let calls: [Trace] }
private struct Input: Codable { let image: [Span] }
private final class Fixture {
    let heap = ClawTokenHeap()
    lazy var host = ClawNativeCanonicalHost(heap: heap)
    var memory: ClawNativeMfcMemory!
    let registry = UnsafeMutablePointer<ClawLogicStateRegistry>.allocate(capacity: 1)
    let context = UnsafeMutablePointer<ClawLogicStateContext>.allocate(capacity: 1)
    let arena = UnsafeMutablePointer<UInt8>.allocate(capacity: 1 << 20)
    var spans: [UInt32: UInt32] = [:]
    var calls: [Trace] = []
    var missing: UInt32 = 0
    static let actor: UInt32 = 0x10002000, logic: UInt32 = 0x10003000, boss: UInt32 = 0x10004000
    static let world: UInt32 = 0x10005000, registryMap: UInt32 = 0x10006000
    static let imageMap: UInt32 = 0x10006100, aniMap: UInt32 = 0x10006200, soundMap: UInt32 = 0x10006300
    static let image: UInt32 = 0x10007000, imageTable: UInt32 = 0x10007100, frame: UInt32 = 0x10007200
    static let ani: UInt32 = 0x10008000, aniTable: UInt32 = 0x10008100, record: UInt32 = 0x10008200
    static let sound: UInt32 = 0x10009000, hit: UInt32 = 0x10009100, attack: UInt32 = 0x10009200
    var idle: UInt32 = 0
    init(_ input: Input) throws {
        for span in input.image { store(span.token, span.bytes) }
        host.stacklessCallerReserve = 0x100
        for (token,count) in [(Self.actor,UInt32(0x200)),(Self.logic,0x174),(Self.boss,0x524),(Self.world,0x40),
            (Self.registryMap,0x20),(Self.imageMap,0x20),(Self.aniMap,0x20),(Self.soundMap,0x20),
            (Self.image,0x6c),(Self.imageTable,12),(Self.frame,0x34),(Self.ani,20),(Self.aniTable,4),(Self.record,48),
            (Self.sound,0x14),(Self.hit,0x14),(Self.attack,0x14)] { store(token,[UInt8](repeating:0,count:Int(count))) }
        put(Self.actor+0xc,Self.world);put(Self.actor+0x6c,Self.logic);put(Self.actor+0x18c,Self.actor)
        put(Self.logic+0xc,Self.world);put(Self.logic+0x10,0x414cc0)
        put(Self.world+0x10,Self.imageMap);put(Self.world+0x14,Self.registryMap)
        put(Self.world+0x28,Self.soundMap);put(Self.world+0x2c,Self.aniMap)
        put(Self.hit+0x10,0x4dc830);put(Self.attack+0x10,0x4dc850)
        put(Self.image+0x14,Self.imageTable);put(Self.image+0x64,0);put(Self.image+0x68,2)
        for offset: UInt32 in [0,4,8] {put(Self.imageTable+offset,Self.frame)}
        put(Self.frame+0x18,3);put(Self.frame+0x1c,5);put(Self.frame+0x20,29);put(Self.frame+0x24,31)
        put(Self.ani+0xc,Self.aniTable);put(Self.ani+0x10,1);put(Self.aniTable,Self.record)
        put(Self.record+0x18,100);put(Self.record+0x1c,17)
        put(Self.sound+0x10,0x10009300)
        put(0x53774c,Self.boss);put(0x5430c4,16);put(0x532c0c,0)
        registry.initialize(to:ClawLogicStateRegistry());context.initialize(to:ClawLogicStateContext())
        arena.initialize(repeating:0,count:1<<20);context.pointee.heap=arena;context.pointee.heapBase=0x65000000;context.pointee.heapCapacity=1<<20
        claw_logic_state_context_defaults(registry,context)
        try require(claw_logic_state_initialize(registry,context,nil,nil)==1 && claw_logic_state_bootstrap(registry,context,nil,nil)==1,"state bootstrap")
        idle="LS_IDLE".withCString {claw_logic_state_find_id(registry,context,$0,nil,nil)}
        var view=ClawLogicStateView()
        for value in [UInt32(1000),idle] {try require(claw_logic_state_resolve(registry,context,0,Int32(bitPattern:value),&view,nil,nil)==1,"state name")}
        for value in [UInt32(1000),idle] {try require(claw_logic_state_resolve(registry,context,0x534c28,Int32(bitPattern:value),&view,nil,nil)==1,"button table")}
        syncRegistry(initial:true)
        let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map {($0.element,UInt32(0x710000+$0.offset*4))})
        memory=try ClawNativeMfcMemory(host:host,sha256:ClawNativeMfcMemory.imageHash,importTargets:imports,allocationBase:0x62000000,sceneObjectAllocations:true)
        memory.beforeObjectAllocation = { [unowned self] request in calls.append(Trace(function:request.function,receiver:0,args:[request.count])) }
        host.observer = { [unowned self] q in
            let args=withUnsafeBytes(of:q.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(q.argumentCount)))}
            calls.append(Trace(function:q.function,receiver:q.receiver,args:args))
        }
        host.dependency = { [unowned self] _,q in service(q) }
    }
    deinit {registry.deinitialize(count:1);registry.deallocate();context.deinitialize(count:1);context.deallocate();arena.deinitialize(count:1<<20);arena.deallocate()}
    func store(_ token:UInt32,_ data:[UInt8]) {let p=heap.storeBytes(token:token,count:UInt32(data.count));p.update(from:data,count:data.count);spans[token]=UInt32(data.count)}
    func word(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)![0]}
    func put(_ a:UInt32,_ value:UInt32) {heap.lookup(a,words:1)![0]=value}
    func syncRegistry(initial:Bool=false) {
        for i in 0..<claw_logic_state_table_count(registry) {
            let table=claw_logic_state_table_at(registry,i)!.pointee
            let count=table.kind==1 ? 44:36
            let data=withUnsafeBytes(of:table.words){Array($0.prefix(count))}
            if heap.lookupBytes(table.token,count:UInt32(count))==nil {store(table.token,data)}
            else {heap.lookupBytes(table.token,count:UInt32(count))!.update(from:data,count:count)}
        }
        let used=context.pointee.heapUsed
        if initial {store(context.pointee.heapBase,Array(UnsafeBufferPointer(start:arena,count:Int(used))))}
        else {precondition(spans[context.pointee.heapBase]==used);heap.lookupBytes(context.pointee.heapBase,count:used)!.update(from:arena,count:Int(used))}
    }
    func service(_ q:ClawCall)->UInt32? {
        if q.function==missing {return nil}
        precondition(claw_canonical_lookup(q.function)==nil,"dependency cannot shadow canonical owner")
        switch q.function {
        case 0x4f6286:
            let resolved:UInt32
            switch (q.receiver,q.arguments.0) {
            case (Self.registryMap+0x10,0x522d54):resolved=Self.hit
            case (Self.registryMap+0x10,0x522d48):resolved=Self.attack
            case (Self.imageMap+0x10,0x5245f0):resolved=Self.image
            case (Self.aniMap+0x10,0x5245d8):resolved=Self.ani
            case (Self.soundMap+0x10,0x5245bc):resolved=Self.sound
            default:return nil
            }
            guard q.argumentCount==2,let output=host.bytes(q.arguments.1,count:4) else {return nil}
            output.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee=resolved};return 1
        case 0x4f6974:
            guard q.argumentCount==1,q.arguments.0==0 else {return nil};return word(q.receiver)
        default:return nil
        }
    }
    func snapshot()->[Span] {
        var ranges=spans
        for (token,data) in memory.localBytes {ranges[UInt32(token)!]=UInt32(data.count)}
        return ranges.keys.sorted().compactMap {a in
            guard let p=heap.lookupBytes(a,count:ranges[a]!) else {return nil}
            return Span(token:a,bytes:Array(UnsafeBufferPointer(start:p,count:Int(ranges[a]!))))
        }
    }
    @discardableResult func callback(_ command:UInt32)->Bool {
        put(Self.logic+0x1c,command)
        var q=ClawCall();q.function=0x414cc0;q.argumentCount=1;q.arguments.0=Self.actor
        return host.withObjectAllocation(provider:memory){host.invoke(q).completed} ?? false
    }
    func contact()->Bool {var q=ClawCall();q.function=0x4152e0;q.receiver=word(Self.logic+0x18);return host.withObjectAllocation(provider:memory){host.invoke(q).completed} ?? false}
    func faultText()->String {String(describing:host.fault)}
}

@main private enum Main {
    static func main() throws {
        let dir=URL(fileURLWithPath:CommandLine.arguments[1])
        let input=try JSONDecoder().decode(Input.self,from:Data(contentsOf:dir.appendingPathComponent("input.json")))
        let f=try Fixture(input)
        let initial=f.snapshot();var steps:[Step]=[]
        func step(_ name:String,_ command:UInt32,_ run:()->Bool) throws {
            f.calls=[];try require(run(),"\(name): \(f.faultText()) calls \(f.calls.map {String($0.function,radix:16)})")
            steps.append(Step(name:name,command:command,spans:f.snapshot(),calls:f.calls))
        }
        try step("construct",0){f.callback(0)}
        let old=f.word(Fixture.logic+0x18),identity=f.heap.allocationIdentity(at:old,count:0x54)
        try require(old==0x62000000 && identity != nil && f.memory.ownsObjectAllocation(old,count:0x54),"helper ownership")
        for command:UInt32 in [1000,29,30,f.idle] {try step("callback-\(command)",command){f.callback(command)}}
        try step("contact",0){f.contact()}
        try step("active",f.idle){f.callback(f.idle)}
        try step("retire",0){f.host.retireCannonButton(actor:Fixture.actor,provider:f.memory)}
        try require(!f.memory.ownsObjectAllocation(old,count:0x54) && f.heap.lookupBytes(old,count:1)==nil,"retired helper")
        try step("recreate",0){f.callback(0)}
        try require(f.word(Fixture.logic+0x18) != old && f.heap.allocationIdentity(at:f.word(Fixture.logic+0x18),count:0x54) !== identity,"fresh helper identity")
        var controls:[String]=[]
        func negative(_ name:String,_ mutate:(Fixture)throws->Void,_ action:(Fixture)->Bool) throws {
            let x=try Fixture(input);try require(x.callback(0),"negative setup \(name): \(x.faultText())");try mutate(x)
            try require(!action(x),"accepted \(name)");controls.append(name)
        }
        try negative("wrong-callback",{ $0.put(Fixture.logic+0x10,0x415350) },{$0.callback(1000)})
        try negative("wrong-actor",{ $0.put(Fixture.actor+0x6c,Fixture.hit) },{$0.callback(1000)})
        try negative("wrong-vtable",{ $0.put($0.word(Fixture.logic+0x18),0x50ba64) },{$0.callback(1000)})
        try negative("stale-helper",{ $0.heap.free($0.word(Fixture.logic+0x18)) },{$0.callback(1000)})
        try negative("replaced-helper",{x in let a=x.word(Fixture.logic+0x18);let b=Array(UnsafeBufferPointer(start:x.heap.lookupBytes(a,count:0x54)!,count:0x54));x.heap.free(a);x.heap.storeBytes(token:a,count:0x54).update(from:b,count:b.count)},{$0.callback(1000)})
        try negative("foreign-free",{_ in},{$0.memory.releaseSceneObject(Fixture.actor)})
        try negative("double-free",{_ in},{x in let retired=x.word(Fixture.logic+0x18);guard x.host.retireCannonButton(actor:Fixture.actor,provider:x.memory) else{return true};return x.memory.releaseSceneObject(retired)})
        try negative("missing-state-service",{$0.missing=0x4f6974},{$0.callback($0.idle)})
        try negative("receiver-exception-outside-lifecycle",{_ in},{x in var q=ClawCall();q.function=0x4c9e30;q.receiver=x.word(Fixture.logic+0x18);q.argumentCount=1;q.arguments.0=1;return x.host.withObjectAllocation(provider:x.memory){x.host.invoke(q).completed} ?? false})
        try negative("wrong-provider",{_ in},{x in
            let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map {($0.element,UInt32(0x710000+$0.offset*4))})
            let foreign=try! ClawNativeMfcMemory(host:x.host,sha256:ClawNativeMfcMemory.imageHash,importTargets:imports,allocationBase:0x63000000,sceneObjectAllocations:true)
            var q=ClawCall();q.function=0x414cc0;q.argumentCount=1;q.arguments.0=Fixture.actor;x.put(Fixture.logic+0x1c,1000)
            return x.host.withObjectAllocation(provider:foreign){x.host.invoke(q).completed} ?? false
        })
        try negative("wrong-size",{_ in},{x in var q=ClawCall();q.function=0x4f63ec;q.argumentCount=1;q.arguments.0=0x58;return x.host.withObjectAllocation(provider:x.memory){x.host.invoke(q).completed} ?? false})
        try negative("wrong-continuation",{_ in},{x in var q=ClawCall();q.function=0x414cc0;q.argumentCount=1;q.arguments.0=Fixture.actor;q.sourceReturnPC=0x414cfb;return x.host.withObjectAllocation(provider:x.memory){x.host.invoke(q).completed} ?? false})
        let missing=try Fixture(input);missing.missing=0x4f6286
        try require(!missing.callback(0),"missing resource lookup");controls.append("missing-resource-service")
        let failure=try Fixture(input);failure.memory.failAllocation={_ in true}
        try require(!failure.callback(0) && failure.word(Fixture.logic+0x1c)==1000 && failure.word(Fixture.logic+0x18)==0 && failure.host.fault?.address==0x5022b5 && failure.host.fault?.diagnostic == .missingDependency,"allocation failure");controls.append("allocation-failure")
        let occupied=try Fixture(input);occupied.heap.storeBytes(token:0x62000000,count:0x54).update(repeating:0xa7,count:0x54)
        try require(!occupied.callback(0) && Array(UnsafeBufferPointer(start:occupied.heap.lookupBytes(0x62000000,count:0x54)!,count:0x54)) == [UInt8](repeating:0xa7,count:0x54),"occupied token preservation");controls.append("occupied-token-preserved")
        let reentry=try Fixture(input);reentry.memory.beforeObjectAllocation={_ in _=reentry.callback(0)}
        try require(!reentry.callback(0),"reentry");controls.append("reentry")
        let result:[String:Any]=["initial":try JSONSerialization.jsonObject(with:JSONEncoder().encode(initial)),"steps":try JSONSerialization.jsonObject(with:JSONEncoder().encode(steps)),"controls":controls,"idle":f.idle]
        try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]).write(to:dir.appendingPathComponent("native.json"))
        print("CannonButton native transport: \(steps.count) steps, \(controls.count) controls")
    }
}
