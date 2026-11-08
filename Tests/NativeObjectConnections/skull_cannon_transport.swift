import Foundation
private let base:UInt32=0x10000000,allocation:UInt32=0x61000000
private let actor=base+0x1000,state=base+0x2000,world=base+0x3000,registry=base+0x4000,images=base+0x5000,animations=base+0x6000,table=base+0x7000,methods=base+0x8000,string=base+0x9000
private let home:UInt32=base+0xc000,firing:UInt32=base+0xd000,imageSet:UInt32=base+0xe000
private let hitMetadata=base+0xa000,attackMetadata=base+0xb000
private func u(_ x:Any)->UInt32 {(x as! NSNumber).uint32Value}
private func decode(_ s:String)->[UInt8] {
 let input=Array(s.utf8);precondition(input.count%2==0)
 func nibble(_ c:UInt8)->UInt8 {if c>=48 && c<=57{return c-48};if c>=97 && c<=102{return c-87};precondition(c>=65 && c<=70);return c-55}
 return stride(from:0,to:input.count,by:2).map{nibble(input[$0])*16+nibble(input[$0+1])}
}
private func args(_ c:ClawCall)->[UInt32] {var c=c;return withUnsafeBytes(of:&c.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(c.argumentCount)))}}
private func call(_ f:UInt32,_ receiver:UInt32=0,_ values:[UInt32]=[])->ClawCall {
 var c=ClawCall();c.function=f;c.receiver=receiver;c.argumentCount=UInt32(values.count)
 withUnsafeMutableBytes(of:&c.arguments){b in let p=b.bindMemory(to:UInt32.self);for i in values.indices{p[i]=values[i]}}
 return c
}
private func physical(_ f:UInt32,_ receiver:UInt32=0,_ values:[UInt32]=[])->ClawCall {var c=call(f,receiver,values);c.stackPointer=UInt32(CLAW_STACK_TOP);return c}
private final class Fixture {
 let heap=ClawTokenHeap();let host:ClawNativeCanonicalHost;let memory:ClawNativeMfcMemory;let p:[String:Any]
 var requests:[[UInt32]]=[],events:[[Any]]=[],calls:[[UInt32]]=[],contexts:[[UInt32]]=[]
 var bindingCalls:[[UInt32]]=[]
 var retired:[[String:Any]]=[]
 var registryOverride:((String,UInt32)->UInt32)?
 var removed:UInt32?,hook:((ClawCall)->Void)?,shadowOffered=false
 init(_ p:[String:Any],_ hash:String,scene:Bool=true)throws {
  self.p=p
  for b in p["initial"] as! [[String:Any]] {let bytes=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(bytes.count)).update(from:bytes,count:bytes.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x40
  let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:allocation,sceneObjectAllocations:scene)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in
   self.calls.append([c.function,c.receiver])
   if c.function==0x4f6428,let pointer=self.host.bytes(args(c)[0],count:0x7c){self.retired.append(["address":args(c)[0],"data":UnsafeBufferPointer(start:pointer,count:0x7c).map{String(format:"%02x",$0)}.joined()])}
   if [UInt32(0x4c8160),0x4c81b0].contains(c.function){self.bindingCalls.append([c.function,c.receiver]+args(c))}
   if let cpu=c.sourceContext?.pointee,c.function==0x4141f0 || c.function==0x4145f0 || c.function==0x4146b0 {self.contexts.append([c.function,c.receiver,c.sourceReturnPC,cpu.ebx,cpu.ebp,cpu.eax,cpu.esi,cpu.edi,cpu.edx])}
   self.hook?(c)
  }
  memory.beforeObjectAllocation={ [unowned self] r in
   func word(_ address:UInt32)->UInt32 {r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:Int(address-UInt32(CLAW_STACK_BASE)),as:UInt32.self).littleEndian}}
   self.requests.append([r.function,word(r.context.esp),word(r.context.esp+20),word(r.context.esp+4),r.context.ebx])
  }
  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]])}}
 }
 func get(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)![0]}
 func put(_ a:UInt32,_ v:UInt32){heap.lookup(a,words:1)![0]=v}
 func service(_ c:ClawCall)->UInt32? {
  if removed==c.function{return nil};let a=args(c)
  if claw_canonical_lookup(c.function) != nil {shadowOffered=true;return 99}
  switch c.function {
  case 0x4f6428:
   return nil
  case 0x4f6286:
   guard a.count==2,[registry+16,images+16,animations+16].contains(c.receiver),let out=host.bytes(a[1],count:4) else{return nil}
   var name:[UInt8]=[]
   for i:UInt32 in 0..<64 {guard let b=host.bytes(a[0]+i,count:1) else{return nil};if b[0]==0{break};name.append(b[0])}
   guard let key=String(bytes:name,encoding:.ascii) else{return nil}
   var value:UInt32=c.receiver==animations+16 && a[0]==0x52c22c ? home : c.receiver==animations+16 && a[0]==0x52c244 ? firing : c.receiver==images+16 ? imageSet : 0
   if c.receiver==registry+16,p["binding"] as? Bool==true {
    if key=="LogicHit",p["hit"] as? Bool==true {value=hitMetadata}
    if key=="LogicAttack",p["attack"] as? Bool==true {value=attackMetadata}
   }
   value=registryOverride?(key,value) ?? value
   var word=value.littleEndian;withUnsafeBytes(of:&word){out.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:4)}
   events.append(["registry",c.receiver,key,value]);return value==0 ? 0:1
  case 0x4a5290:
   guard a==[allocation+0x94,allocation+0x90,8],let source=host.bytes(a[1],count:a[2]),let destination=host.bytes(a[0],count:a[2]) else{return nil}
   let copied=Array(UnsafeBufferPointer(start:source,count:Int(a[2])));destination.update(from:copied,count:copied.count)
   events.append(["move",a[0],a[1],a[2]]);return a[0]
  case 0x4a9070:
   guard a.count==2,a[0]==allocation+0x80,a[1]==12,(p["growth"] as! Bool),let value=memory.service(physical(0x546a80,0,[a[0],a[1],2])) else{return nil}
   events.append(["realloc",a[0],a[1],value]);return value
  case 0x4f6974:
   guard a==[0],c.receiver>=table,c.receiver<table+256,c.receiver & 3==0,
         let pointer=heap.lookup(c.receiver,words:1)?[0],[string+12,string+0x4c].contains(pointer),
         get(pointer-12)==1 else{return nil}
   events.append(["buffer",c.receiver,pointer]);return pointer
  default:return memory.service(c)
  }
 }
 func invokeCallback(_ callback:UInt32,_ command:UInt32)->ClawNativeCanonicalHost.Completion? {
  put(state+0x1c,command)
  return host.withObjectAllocation(provider:memory){host.invoke(call(callback,0,[actor]))}
 }
 func invoke(_ command:UInt32)->ClawNativeCanonicalHost.Completion? {invokeCallback(0x48a800,command)}
 func initialize()->Bool {invoke(0)?.completed==true}
 func snapshot(_ blocks:[[String:Any]])->[[String:Any]] {
  blocks.map {b in
   let address=u(b["address"]!),n=UInt32((b["data"] as! String).count/2)
   let bytes=heap.lookupBytes(address,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing"
   return ["address":address,"data":bytes]
  }
 }
 func releaseHelper()->Bool {
  let helper=get(state+0x18)
  let ok=memory.sceneObjectAllocations ? host.retireSkullCannon(actor:actor,provider:memory) : memory.service(physical(0x5469d8,0,[helper]))==0
  if ok && !memory.sceneObjectAllocations {put(state+0x18,0)}
  if ok {events.append(["release",helper,0x7c])}
  return ok
 }
 func runBinding()->[String:Any] {
  var results:[UInt32]=[],completed:[Bool]=[],snapshots:[[[String:Any]]]=[]
  let expected=p["snapshots"] as! [[[String:Any]]]
  for iteration in expected.indices {
   if iteration>0 {
    guard releaseHelper() else{break}
    for offset:UInt32 in [0x70,0x78] {let token=get(actor+offset);if token != 0 {put(token+8,77);put(token+0x10,0x4145f0);put(token+0x20,123);put(token+0x24,456);put(token+0x28,789)}}
   }
   let r=invoke(0);completed.append(r?.completed==true)
   if let value=r?.eax {results.append(value)}
   snapshots.append(snapshot(expected[iteration]))
   if r?.completed != true{break}
  }
  return ["label":p["label"]!,"results":results,"completed":completed,"snapshots":snapshots,"events":events,"calls":calls,"requests":requests,"binding_calls":bindingCalls,"retired":retired,"frontier":host.fault.map{$0.address as Any} ?? NSNull()]
 }
 func run()->[String:Any] {
  var results:[UInt32]=[],completions:[[String:Any]]=[],snapshots:[[[String:Any]]]=[]
  let expectedSnapshots=p["snapshots"] as! [[[String:Any]]]
  for command in (p["commands"] as! [NSNumber]).map(\.uint32Value) {
   if command==7,heap.lookupBytes(allocation,count:0x7c) != nil {
    put(allocation+0x74,0);put(allocation+0x78,(p["timeout"] as! Bool) ? 100:500);put(allocation+0x70,(p["vertical"] as! Bool) ? 1:0)
    if p["growth"] as! Bool,host.fault==nil {
     guard let token=memory.service(physical(0x546aa8,0,[0,8])) else{preconditionFailure("owned table setup")}
     precondition(token==allocation+0x80);put(token,u(p["method"]!));put(token+4,u(p["method"]!))
     put(0x534c00,8);put(0x534c04,9);put(0x534c08,token);events.append(["table-owner",token,8])
    }
   }
   let r=invoke(command)
   completions.append(["completed":r?.completed==true,"fault":r?.fault.map{String(describing:$0)} ?? String(describing:host.fault)])
   if let value=r?.eax {results.append(value)}
   if snapshots.count<expectedSnapshots.count {snapshots.append(snapshot(expectedSnapshots[snapshots.count]))}
  }
  let final=(p["final"] as! [[String:Any]]).map{b->[String:Any] in
   let address=u(b["address"]!),n=UInt32((b["data"] as! String).count/2)
   let bytes=heap.lookupBytes(address,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing"
   return ["address":address,"data":bytes]
  }
  return ["frontier":host.fault.map{$0.address as Any} ?? NSNull(),"label":p["label"]!,"results":results,"requests":requests,"events":events,"calls":calls,"contexts":contexts,"final":final,"snapshots":snapshots,"completions":completions]
 }
 func replace(_ token:UInt32,_ count:UInt32) {
  let bytes=Array(UnsafeBufferPointer(start:heap.lookupBytes(token,count:count)!,count:Int(count)))
  heap.free(token);heap.storeBytes(token:token,count:count).update(from:bytes,count:bytes.count)
 }
}
@main struct SkullCannonTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]),data=try Data(contentsOf:dir.appendingPathComponent("reference.json"))
  let ref=try JSONSerialization.jsonObject(with:data) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  var output:[[String:Any]]=[];for profile in profiles{output.append(try Fixture(profile,hash).run())}
  let bindingProfiles=ref["binding_profiles"] as! [[String:Any]],bp=bindingProfiles[0]
  var bindingOutput:[[String:Any]]=[];for profile in bindingProfiles{bindingOutput.append(try Fixture(profile,hash).runBinding())}
  var controls:[[String:Any]]=[];var exhaustion:[String:Any]=[:]
  func record(_ name:String,_ passed:Bool){controls.append(["name":name,"passed":passed])}
  do{let f=try Fixture(p,hash);record("canonical owners cannot be shadowed",f.initialize() && !f.shadowOffered)}
  do{let f=try Fixture(p,hash);record("allocation needs provider",!f.host.invoke(call(0x48a800,0,[actor])).completed)}
  for callback:UInt32 in [0,0x495d40,0x495e01] {let f=try Fixture(p,hash);f.put(state+0x10,callback);record("wrong actor callback \(callback) rejected",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.removed=0x4f6286;record("missing constructor registry fails",!f.initialize())}
  do{let f=try Fixture(p,hash);let initialized=f.initialize();f.removed=0x4f6974;record("missing lifecycle buffer service fails",initialized && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(call(0x48a800,0,[actor]))};record("allocation physical reentry rejected",!f.initialize() && nested?.completed==false)}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.hook={c in if c.function==0x4f6286{f.hook=nil;nested=f.host.invoke(call(0x48a800,0,[actor]))}};record("constructor service reentry rejected",!f.initialize() && nested?.completed==false)}
  do{let f=try Fixture(p,hash),foreign=try Fixture(p,hash);record("foreign allocation provider rejected",f.host.withObjectAllocation(provider:foreign.memory){f.host.invoke(call(0x48a800,0,[actor]))}==nil)}
  do{let f=try Fixture(p,hash);var rejected=false;let r:Void?=f.host.withObjectAllocation(provider:f.memory){rejected=f.host.withObjectAllocation(provider:f.memory){0}==nil};record("nested allocation scope rejected",rejected && r==nil)}
  for (name,token,count) in [("actor",actor,UInt32(0x200)),("state",state,0x200),("helper",allocation,0x7c),("vtable",UInt32(0x50f744),0x24)] {
   let f=try Fixture(p,hash);let initialized=f.initialize();f.hook={c in if c.function==0x4f6974{f.hook=nil;f.replace(token,count)}}
   record(name+" identity replacement during lifecycle rejected",initialized && f.invoke(7)?.completed != true)
  }
  for token in [actor,state] {let f=try Fixture(p,hash);let initialized=f.initialize();f.replace(token,0x200);record("retained actor/state identity \(token) replacement rejected",initialized && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash);let initialized=f.initialize();record("repeated initialization cannot leak live helper",initialized && !f.initialize())}
  for (name,address,value) in [("helper vtable",allocation,UInt32(0x50f748)),("slot four target",UInt32(0x50f748),UInt32(0x4c9e31)),("slot eight target",UInt32(0x50f74c),UInt32(0x4141f1)),("slot twelve target",UInt32(0x50f750),UInt32(0x4041b1)),("state helper",state+0x18,allocation+4)] {
   let f=try Fixture(p,hash);let initialized=f.initialize();f.put(address,value)
   record(name+" mismatch rejected",initialized && f.invoke(7)?.completed != true)
  }
  for (name,change) in [("source masks", { (cpu:UnsafeMutablePointer<ClawSourceContext>) in cpu.pointee.outputMask=0x7ff }), ("source receiver", { (cpu:UnsafeMutablePointer<ClawSourceContext>) in cpu.pointee.ecx=allocation+4 })] {
   let f=try Fixture(p,hash);let initialized=f.initialize();f.hook={c in if c.function==0x4141f0,let cpu=c.sourceContext {f.hook=nil;change(cpu)}}
   record(name+" alteration rejected",initialized && f.invoke(7)?.completed != true)
  }
  do{let f=try Fixture(p,hash);let initialized=f.initialize();f.hook={c in if c.function==0x4141f0,c.sourceContext != nil{f.hook=nil;f.host.bytes(c.stackPointer,count:4)!.update(repeating:0,count:4)}};record("source continuation stack alteration rejected",initialized && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={r in f.host.bytes(r.context.esp+20,count:4)!.update(repeating:0,count:4)};record("wrong allocation continuation rejected",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.memory.afterService={slot,_,token in if slot==0x4a48e0 && token != 0{f.replace(token,0x7c)}};record("returned allocation identity replacement rejected",!f.initialize())}
  for method:UInt32 in [0,0x4c96b0,0x4145f1] {let f=try Fixture(p,hash);let initialized=f.initialize();f.put(methods+28,method);record("unsupported state method \(method) fails",initialized && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash);f.memory.failAllocation={_ in true};record("allocator exhaustion reaches missing handler",!f.initialize() && f.host.fault?.diagnostic == .missingDependency && f.host.fault?.address==0x5022b5 && f.heap.lookupBytes(allocation,count:1)==nil);exhaustion=["requests":f.requests,"events":f.events,"frontier":f.host.fault.map{$0.address as Any} ?? NSNull()]}
  do{let f=try Fixture(p,hash);_=f.heap.storeBytes(token:allocation,count:0x7c);record("occupied shared allocation base is exhaustion",!f.initialize() && f.host.fault?.diagnostic == .missingDependency)}
  for (name,c) in [("standalone stdcall receiver",call(0x4c9e30,allocation,[0])),("standalone source dispatcher",call(0x4141f0,allocation,[7])),("standalone operator new",call(0x4f63ec,0,[0x7c]))] {
   let f=try Fixture(p,hash);record(name+" rejected",f.host.withObjectAllocation(provider:f.memory){f.host.invoke(c)}?.completed != true)
  }
  do{let f=try Fixture(p,hash,scene:false);let initialized=f.initialize();let r=f.memory.service(physical(0x5469d8,0,[allocation]));record("same owner releases helper",initialized && r==0 && !f.memory.ownsObjectAllocation(allocation,count:0x7c) && f.heap.lookupBytes(allocation,count:1)==nil);record("released helper cannot dispatch",f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash,scene:false);let initialized=f.initialize();let released=f.memory.service(physical(0x5469d8,0,[allocation]));f.put(state+0x18,0);let again=f.initialize();let next=f.get(state+0x18);record("owner release and real constructor recreate",initialized && released==0 && again && next != allocation && f.memory.ownsObjectAllocation(next,count:0x7c) && f.get(next)==0x50f744 && f.get(next+8)==actor)}
  for (name,bad) in [("allocation size",call(0x4f63ec,0,[0x80])),("allocation caller",call(0x4f63ec,actor,[0x7c]))] {
   let f=try Fixture(p,hash);f.hook={c in if c.function==0x4f63ec{f.hook=nil;_=f.host.callNativeDependency(bad)}}
   record(name+" forged request rejected",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)
  }
  for (name,change) in [("method receiver", { (c:ClawCall) in c.sourceContext!.pointee.ecx=allocation+4 }), ("method continuation", { (c:ClawCall) in c.sourceContext!.pointee.eip=0x4142ec })] {
   let f=try Fixture(p,hash);let initialized=f.initialize();f.hook={c in if c.function==u(p["method"]!),c.sourceContext != nil{f.hook=nil;change(c)}}
   record(name+" mutation rejected",initialized && f.invoke(7)?.completed != true)
  }
  do{let f=try Fixture(p,hash,scene:false);let initialized=f.initialize();let r=f.memory.service(physical(0x5469d8,0,[allocation]));let again=f.memory.service(physical(0x5469d8,0,[allocation]));record("double free rejected",initialized && r==0 && again==nil && f.host.fault != nil)}
  do{let f=try Fixture(p,hash);_=f.heap.storeBytes(token:allocation,count:0x7c);record("foreign free rejected",f.memory.service(physical(0x5469d8,0,[allocation]))==nil && f.heap.lookupBytes(allocation,count:0x7c) != nil)}
  do{let f=try Fixture(p,hash,scene:false);let initialized=f.initialize();let before=f.heap.lookupBytes(allocation,count:0x7c).map{Array(UnsafeBufferPointer(start:$0,count:0x7c))};let moved=f.memory.service(physical(0x546a80,0,[allocation,0x90,2]));let bytes=moved.flatMap{f.heap.lookupBytes($0,count:0x7c)}.map{Array(UnsafeBufferPointer(start:$0,count:0x7c))};record("owner reallocation preserves helper and retires prior identity",initialized && moved != nil && moved != allocation && before==bytes && !f.memory.ownsObjectAllocation(allocation,count:0x7c));record("old token after resize rejected",f.invoke(7)?.completed != true)}
  do{let f=try Fixture(bp,hash);record("real metadata uses canonical binders without dependency shadow",f.initialize() && !f.shadowOffered && f.bindingCalls.count==2 && !f.calls.contains{$0[0]==0x4dc830 || $0[0]==0x4dc850})}
  for (metadata,callback) in [(hitMetadata,UInt32(0x4dc830)),(attackMetadata,UInt32(0x4dc850))] {
   for wrong:UInt32 in [0,0x48e430,callback+1] {let f=try Fixture(bp,hash);f.put(metadata+0x10,wrong);record("binding callback \(metadata) value \(wrong) rejected",!f.initialize())}
   do{let f=try Fixture(bp,hash);f.heap.free(metadata);record("missing binding metadata \(metadata) rejected",!f.initialize())}
   do{let f=try Fixture(bp,hash);f.registryOverride={key,value in value==metadata ? metadata+0x800:value};record("unmapped registry output \(metadata) rejected",!f.initialize())}
   do{let f=try Fixture(bp,hash);f.memory.beforeObjectAllocation={r in if r.context.ebx==0x174 {f.replace(metadata,0x14)}};record("metadata identity \(metadata) replacement during secondary allocation rejected",!f.initialize())}
   do{let f=try Fixture(bp,hash);let initialized=f.initialize();let released=initialized && f.releaseHelper();f.replace(metadata,0x14);record("retained metadata \(metadata) replacement rejected",released && !f.initialize())}
   do{let f=try Fixture(bp,hash);f.hook={c in if c.function==0x4c7970 {f.hook=nil;f.put(metadata+0x10,callback+1)}};record("metadata \(metadata) mutation later in constructor rejected",!f.initialize())}
  }
  for offset:UInt32 in [0x70,0x78] {
   do{let f=try Fixture(bp,hash);let initialized=f.initialize();let token=f.get(actor+offset);let released=initialized && f.releaseHelper();if initialized{f.replace(token,0x174)};record("retained secondary \(offset) identity replacement rejected",released && !f.initialize())}
   do{let f=try Fixture(bp,hash,scene:false);let initialized=f.initialize();let token=f.get(actor+offset);let released=initialized && f.releaseHelper();let freed=initialized ? f.memory.service(physical(0x5469d8,0,[token])):nil;record("released secondary \(offset) stale actor slot rejected",released && freed==0 && !f.initialize())}
   do{let f=try Fixture(bp,hash,scene:false);let initialized=f.initialize();let token=f.get(actor+offset);let released=initialized && f.releaseHelper();let freed=initialized ? f.memory.service(physical(0x5469d8,0,[token])):nil;if initialized{f.put(actor+offset,0)};let again=released && freed==0 && f.initialize();let next=f.get(actor+offset);record("same owner recreates secondary \(offset)",again && next != token && f.memory.ownsObjectAllocation(next,count:0x174))}
   do{let f=try Fixture(bp,hash,scene:false);let initialized=f.initialize();let token=f.get(actor+offset);let first=initialized ? f.memory.service(physical(0x5469d8,0,[token])):nil;let second=initialized ? f.memory.service(physical(0x5469d8,0,[token])):nil;record("secondary \(offset) double free rejected",initialized && first==0 && second==nil && f.host.fault != nil)}
   do{let f=try Fixture(bp,hash);let token:UInt32=0x62000000;_=f.heap.storeBytes(token:token,count:0x174);f.put(token,0x513740);f.put(actor+offset,token);record("foreign secondary \(offset) cannot rebind",!f.initialize() && f.heap.lookupBytes(token,count:0x174) != nil)}
  }
  for (name,address,value) in [("binding slot",UInt32(0x513764),UInt32(0x4c8161)),("reset slot",UInt32(0x51375c),UInt32(0x4c81b1))] {
   let f=try Fixture(bp,hash);let initialized=f.initialize();let released=initialized && f.releaseHelper();f.put(address,value);record(name+" mismatch rejected",released && !f.initialize())
  }
  do{let f=try Fixture(bp,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={r in if r.context.ebx==0x174 {nested=f.host.invoke(call(0x48a800,0,[actor]))}};record("secondary allocation reentry rejected",!f.initialize() && nested?.completed==false)}
  for (name,offset) in [("size",UInt32(4)),("continuation",UInt32(20))] {let f=try Fixture(bp,hash);f.memory.beforeObjectAllocation={r in if r.context.ebx==0x174 {f.host.bytes(r.context.esp+offset,count:4)!.update(repeating:0,count:4)}};record("secondary allocation \(name) alteration rejected",!f.initialize())}
  do{let f=try Fixture(bp,hash);f.memory.afterService={slot,a,token in if slot==0x4a48e0 && a[0]==0x174 && token != 0 {f.replace(token,0x174)}};record("secondary returned allocation identity replacement rejected",!f.initialize())}
  do{let f=try Fixture(bp,hash);f.memory.beforeObjectAllocation={r in if r.count==0x174 {f.memory.failAllocation={_ in true}}};record("secondary allocation exhaustion reaches original missing handler",!f.initialize() && f.host.fault?.address==0x5022b5)}
  for (entry,name) in [(UInt32(0x4c7fa0),UInt32(0x522d54)),(UInt32(0x4c8060),UInt32(0x522d48))] {
   let f=try Fixture(bp,hash)
   record("binding entry \(entry) outside elected constructor rejected",f.host.withObjectAllocation(provider:f.memory){f.host.invoke(call(entry,actor,[name]))}?.completed != true && f.heap.lookupBytes(allocation,count:1)==nil)
  }
  for token in [world,registry] {
   let f=try Fixture(bp,hash);f.memory.beforeObjectAllocation={r in if r.count==0x174 {f.replace(token,0x200)}}
   record("constructor owner \(token) identity replacement rejected",!f.initialize())
  }
  do{let f=try Fixture(bp,hash);f.removed=0x4f6286;record("real binding missing registry service rejected",!f.initialize())}
  do{let f=try Fixture(bp,hash);record("real binding missing allocation provider rejected",!f.host.invoke(call(0x48a800,0,[actor])).completed)}
  for offset:UInt32 in [0x70,0x78] {
   let f=try Fixture(bp,hash);f.hook={c in if c.function==0x4c7970 {f.hook=nil;let token=f.get(actor+offset);f.put(token+0x10,0x4145f0)}}
   record("bound secondary callback \(offset) mutation later in constructor rejected",!f.initialize())
  }
  for (from,to,table) in [(UInt32(0x48a800),UInt32(0x495d40),UInt32(0x50fa64))] {
   do{let f=try Fixture(p,hash);f.put(state+0x10,from);let initialized=f.invokeCallback(from,0)?.completed==true;f.put(state+0x10,to);if initialized{f.put(allocation,table)};record("cross-cannon helper tuple \(from) to \(to) rejected",initialized && f.invokeCallback(to,7)?.completed != true)}
   do{let f=try Fixture(bp,hash);f.put(state+0x10,from);let initialized=f.invokeCallback(from,0)?.completed==true;let released=initialized && f.releaseHelper();let count=f.requests.count;f.put(state+0x10,to);record("cross-cannon retained logic tuple \(from) to \(to) rejected before allocation",released && f.invokeCallback(to,0)?.completed != true && f.requests.count==count)}
  }
  do{let f=try Fixture(p,hash);f.hook={c in if c.function==0x48a8c0{f.hook=nil;_=f.host.callNativeDependency(call(0x495ec0,c.receiver,[actor]))}};record("left constructor substituted under Skull callback rejected",!f.initialize())}
  for (name,change) in [("left source EBX",{(cpu:UnsafeMutablePointer<ClawSourceContext>) in cpu.pointee.ebx=0x50fa64}),("left source EDX",{(cpu:UnsafeMutablePointer<ClawSourceContext>) in cpu.pointee.edx=0x50fa64})] {
   let f=try Fixture(p,hash);let initialized=f.initialize();f.hook={c in if c.function==0x4141f0,let cpu=c.sourceContext{f.hook=nil;change(cpu)}}
   record(name+" substitution rejected",initialized && f.invoke(7)?.completed != true)
  }
  do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={r in var wrong=UInt32(0x495d7a).littleEndian;withUnsafeBytes(of:&wrong){f.host.bytes(r.context.esp+20,count:4)!.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:4)}};record("left allocation continuation under Skull callback rejected",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)}
  do{let f=try Fixture(p,hash);let initialized=f.initialize();let old=f.get(state+0x18);let retired=f.host.retireSkullCannon(actor:actor,provider:f.memory);let again=retired && f.initialize();let next=f.get(state+0x18);record("scalar owner teardown and real constructor recreate",initialized && retired && again && old != next && f.memory.ownsObjectAllocation(next,count:0x7c) && f.get(next)==0x50f744);record("teardown uses original scalar and free owners",f.calls.contains{$0[0]==0x484d90} && f.calls.contains{$0[0]==0x4f6428})}
  do{let f=try Fixture(p,hash);let initialized=f.initialize();let retired=f.host.retireSkullCannon(actor:actor,provider:f.memory);record("scalar owner double retirement rejected",initialized && retired && !f.host.retireSkullCannon(actor:actor,provider:f.memory))}
  for (name,token) in [("home",home),("firing",firing)] {
   do{let f=try Fixture(p,hash);let initialized=f.initialize();if initialized {f.replace(token,0x200)};record("retained "+name+" resource identity replacement rejected",initialized && f.invoke(7)?.completed != true)}
   do{let f=try Fixture(p,hash);f.hook={c in if c.function==0x4145b0 {f.hook=nil;f.replace(token,0x200)}};record("constructor "+name+" resource identity replacement rejected",!f.initialize())}
  }
  for (name,offset,value) in [("home",UInt32(0x48),firing),("firing",UInt32(0x4c),home)] {
   let f=try Fixture(p,hash);let initialized=f.initialize();if initialized{f.put(allocation+offset,value)};record("retained "+name+" resource pointer mutation rejected",initialized && f.invoke(7)?.completed != true)
  }
  let result:[String:Any]=["version":1,"profiles":output,"binding_profiles":bindingOutput,"controls":controls,"exhaustion":exhaustion]
  try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"))
  print("native profiles \(output.count), controls \(controls.count)")
 }
}
