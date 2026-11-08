import Foundation
private let base:UInt32=0x10000000,allocation:UInt32=0x61000000
private let actor=base+0x1000,state=base+0x2000,world=base+0x3000,registry=base+0x4000,metadata=base+0xa000
private func u(_ x:Any)->UInt32 {(x as! NSNumber).uint32Value}
private func decode(_ s:String)->[UInt8] {stride(from:0,to:s.count,by:2).map {i in let start=s.index(s.startIndex,offsetBy:i);return UInt8(s[start..<s.index(start,offsetBy:2)],radix:16)!}}
private func args(_ c:ClawCall)->[UInt32] {var c=c;return withUnsafeBytes(of:&c.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(c.argumentCount)))}}
private func call(_ f:UInt32,_ receiver:UInt32=0,_ values:[UInt32]=[])->ClawCall {
 var c=ClawCall();c.function=f;c.receiver=receiver;c.argumentCount=UInt32(values.count)
 withUnsafeMutableBytes(of:&c.arguments){b in let p=b.bindMemory(to:UInt32.self);for i in values.indices{p[i]=values[i]}}
 return c
}
private func physical(_ f:UInt32,_ values:[UInt32])->ClawCall {var c=call(f,0,values);c.stackPointer=UInt32(CLAW_STACK_TOP);return c}
private final class Fixture {
 let heap=ClawTokenHeap();let host:ClawNativeCanonicalHost;let memory:ClawNativeMfcMemory;let p:[String:Any]
 var requests:[[UInt32]]=[],events:[[Any]]=[],calls:[[UInt32]]=[],bindingCalls:[[UInt32]]=[]
 var registryOverride:((String,UInt32)->UInt32)?
 var removed:UInt32?,hook:((ClawCall)->Void)?,shadowOffered=false
 init(_ p:[String:Any],_ hash:String)throws {
  self.p=p
  for b in p["initial"] as! [[String:Any]] {let bytes=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(bytes.count)).update(from:bytes,count:bytes.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x40
  let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:allocation)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in
   self.calls.append([c.function,c.receiver])
   if [UInt32(0x4c8160),0x4c81b0].contains(c.function){self.bindingCalls.append([c.function,c.receiver]+args(c))}
   self.hook?(c)
  }
  memory.beforeObjectAllocation={ [unowned self] r in
   func word(_ a:UInt32)->UInt32 {r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:Int(a-UInt32(CLAW_STACK_BASE)),as:UInt32.self).littleEndian}}
   self.requests.append([r.function,word(r.context.esp),word(r.context.esp+20),word(r.context.esp+4),r.context.ebx])
  }
  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]])}}
  if p["exhausted"] as! Bool {memory.failAllocation={_ in true}}
 }
 func get(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)![0]}
 func put(_ a:UInt32,_ v:UInt32){heap.lookup(a,words:1)![0]=v}
 func service(_ c:ClawCall)->UInt32? {
  if removed==c.function{return nil}
  if claw_canonical_lookup(c.function) != nil {shadowOffered=true;return 99}
  if c.function==0x4f6286 {
   let a=args(c)
   guard a.count==2,c.receiver==registry+16,let out=host.bytes(a[1],count:4) else{return nil}
   var name:[UInt8]=[]
   for i:UInt32 in 0..<32 {guard let b=host.bytes(a[0]+i,count:1) else{return nil};if b[0]==0{break};name.append(b[0])}
   guard let key=String(bytes:name,encoding:.ascii) else{return nil}
   var value:UInt32=key=="CrateHit" && p["enabled"] as! Bool ? metadata:0
   value=registryOverride?(key,value) ?? value
   var word=value.littleEndian;withUnsafeBytes(of:&word){out.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:4)}
   events.append(["registry",c.receiver,key,value]);return value==0 ? 0:1
  }
  return memory.service(c)
 }
 func invoke()->ClawNativeCanonicalHost.Completion? {host.withObjectAllocation(provider:memory){host.invoke(call(0x471780,0,[actor]))}}
 func initialize()->Bool {put(state+0x1c,0);return invoke()?.completed==true}
 func snapshot(_ blocks:[[String:Any]])->[[String:Any]] {
  blocks.map {b in let address=u(b["address"]!),n=UInt32((b["data"] as! String).count/2)
   let bytes=heap.lookupBytes(address,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing"
   return ["address":address,"data":bytes]
  }
 }
 func release()->Bool {
  let token=get(actor+0x70)
  guard memory.service(physical(0x5469d8,[token]))==0 else{return false}
  events.append(["release",token,0x174]);put(actor+0x70,0);return true
 }
 func run()->[String:Any] {
  var results:[UInt32]=[],completed:[Bool]=[],snapshots:[[[String:Any]]]=[]
  let expected=p["snapshots"] as! [[[String:Any]]]
  for iteration in expected.indices {
   if iteration>0 {
    if p["mode"] as! String == "retire" {guard release() else{break}}
    else {let token=get(actor+0x70);put(token+8,77);put(token+0x10,0x4717e0);put(token+0x20,123);put(token+0x24,456);put(token+0x28,789);put(token+0x168,345);put(token+0x16c,678)}
    put(state+0x1c,0)
   }
   let r=invoke();completed.append(r?.completed==true)
   if r?.completed==true,let value=r?.eax {results.append(value)}
   snapshots.append(snapshot(expected[iteration]))
   if r?.completed != true{break}
  }
  return ["label":p["label"]!,"results":results,"completed":completed,"snapshots":snapshots,"events":events,"calls":calls,"requests":requests,"binding_calls":bindingCalls,"frontier":host.fault.map{$0.address as Any} ?? NSNull()]
 }
 func replace(_ token:UInt32,_ count:UInt32) {
  let bytes=Array(UnsafeBufferPointer(start:heap.lookupBytes(token,count:count)!,count:Int(count)))
  heap.free(token);heap.storeBytes(token:token,count:count).update(from:bytes,count:bytes.count)
 }
}
@main struct FrontStatueTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]),data=try Data(contentsOf:dir.appendingPathComponent("reference.json"))
  let ref=try JSONSerialization.jsonObject(with:data) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  var output:[[String:Any]]=[];for profile in profiles{output.append(try Fixture(profile,hash).run())}
  var controls:[[String:Any]]=[]
  func record(_ name:String,_ passed:Bool){controls.append(["name":name,"passed":passed])}
  do{let f=try Fixture(p,hash);record("canonical binders cannot be shadowed",f.initialize() && !f.shadowOffered && f.bindingCalls.count==1)}
  do{let f=try Fixture(p,hash);record("allocation needs provider",!f.host.invoke(call(0x471780,0,[actor])).completed)}
  do{let f=try Fixture(p,hash);f.removed=0x4f6286;record("missing registry service fails",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)}
  for callback:UInt32 in [0,0x471720,0x471781] {let f=try Fixture(p,hash);f.put(state+0x10,callback);record("wrong primary callback \(callback) rejected",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)}
  for callback:UInt32 in [0,0x4dc830,0x4717e1] {let f=try Fixture(p,hash);f.put(metadata+0x10,callback);record("wrong CrateHit callback \(callback) rejected",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.put(0x5228dc,0x676e6f57);record("wrong CrateHit name bytes rejected",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.heap.free(metadata);record("missing CrateHit metadata rejected",!f.initialize())}
  do{let f=try Fixture(p,hash);f.registryOverride={_,_ in metadata+0x800};record("unmapped CrateHit lookup output rejected",!f.initialize())}
  do{let f=try Fixture(p,hash),foreign=try Fixture(p,hash);record("foreign heap provider rejected",f.host.withObjectAllocation(provider:foreign.memory){f.host.invoke(call(0x471780,0,[actor]))}==nil)}
  do{let f=try Fixture(p,hash);var rejected=false;let r:Void?=f.host.withObjectAllocation(provider:f.memory){rejected=f.host.withObjectAllocation(provider:f.memory){0}==nil};record("nested allocation scope rejected",rejected && r==nil)}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(call(0x471780,0,[actor]))};record("physical allocation reentry rejected",!f.initialize() && nested?.completed==false)}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.hook={c in if c.function==0x4f6286 {f.hook=nil;nested=f.host.invoke(call(0x471780,0,[actor]))}};record("registry observer reentry rejected",!f.initialize() && nested?.completed==false)}
  for (name,token,count) in [("actor",actor,UInt32(0x200)),("primary state",state,0x200),("world",world,0x200),("registry",registry,0x200),("metadata",metadata,0x14),("vtable",UInt32(0x513740),0x28)] {
   do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={_ in f.replace(token,count)};record(name+" identity replacement during allocation rejected",!f.initialize())}
   do{let f=try Fixture(p,hash);let initialized=f.initialize();f.replace(token,count);record(name+" identity replacement between bindings rejected",initialized && !f.initialize())}
  }
  do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={_ in f.put(metadata+0x10,0x4717e1)};record("callback alteration during allocation rejected",!f.initialize())}
  for (name,offset) in [("size",UInt32(4)),("continuation",UInt32(20))] {let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={r in f.host.bytes(r.context.esp+offset,count:4)!.update(repeating:0,count:4)};record("allocation \(name) alteration rejected",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)}
  for (name,bad) in [("wrong size",call(0x4f63ec,0,[0x170])),("wrong receiver",call(0x4f63ec,actor,[0x174]))] {
   let f=try Fixture(p,hash);f.hook={c in if c.function==0x4f63ec {f.hook=nil;_=f.host.callNativeDependency(bad)}}
   record(name+" forged allocation rejected",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)
  }
  for (name,bad) in [("wrong name pointer",call(0x4c7fa0,actor,[0x5228e0])),("wrong actor receiver",call(0x4c7fa0,actor+4,[0x5228dc]))] {
   let f=try Fixture(p,hash);f.hook={c in if c.function==0x4c7fa0 {f.hook=nil;_=f.host.callNativeDependency(bad)}}
   record(name+" forged binding rejected",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)
  }
  do{let f=try Fixture(p,hash);f.memory.afterService={slot,_,token in if slot==0x4a48e0 && token != 0 {f.replace(token,0x174)}};record("returned allocation identity replacement rejected",!f.initialize())}
  do{let f=try Fixture(p,hash);let initialized=f.initialize();let token=f.get(actor+0x70);if initialized{f.replace(token,0x174)};record("retained secondary identity replacement rejected",initialized && !f.initialize())}
  do{let f=try Fixture(p,hash);let initialized=f.initialize();let token=f.get(actor+0x70);let freed=initialized ? f.memory.service(physical(0x5469d8,[token])):nil;record("released secondary stale actor slot rejected",initialized && freed==0 && !f.initialize())}
  do{let f=try Fixture(p,hash);let initialized=f.initialize();let token=f.get(actor+0x70);let released=initialized && f.release();let again=released && f.initialize();let next=f.get(actor+0x70);record("same owner retirement and real recreation",again && next != token && !f.memory.ownsObjectAllocation(token,count:0x174) && f.memory.ownsObjectAllocation(next,count:0x174) && f.get(next)==0x513740 && f.get(next+0x10)==0x4717e0)}
  do{let f=try Fixture(p,hash);let initialized=f.initialize();let token=f.get(actor+0x70);let first=initialized ? f.memory.service(physical(0x5469d8,[token])):nil;let second=initialized ? f.memory.service(physical(0x5469d8,[token])):nil;record("secondary double free rejected",initialized && first==0 && second==nil && f.host.fault != nil)}
  do{let f=try Fixture(p,hash);let token:UInt32=0x62000000;_=f.heap.storeBytes(token:token,count:0x174);f.put(token,0x513740);f.put(actor+0x70,token);record("foreign secondary cannot rebind",!f.initialize() && f.heap.lookupBytes(token,count:0x174) != nil)}
  for (name,address,value) in [("bind slot",UInt32(0x513764),UInt32(0x4c8161)),("reset slot",UInt32(0x51375c),UInt32(0x4c81b1)),("secondary vtable",allocation,UInt32(0x513744)),("actor slot",actor+0x70,allocation+4)] {
   let f=try Fixture(p,hash);let initialized=f.initialize();if initialized{f.put(address,value)};record(name+" mismatch rejected",initialized && !f.initialize())
  }
  do{let f=try Fixture(p,hash);f.memory.failAllocation={_ in true};record("allocation exhaustion reaches original missing handler",!f.initialize() && f.host.fault?.diagnostic == .missingDependency && f.host.fault?.address==0x5022b5 && f.heap.lookupBytes(allocation,count:1)==nil)}
  do{let f=try Fixture(p,hash);_=f.heap.storeBytes(token:allocation,count:0x174);record("occupied shared allocation base is exhaustion",!f.initialize() && f.host.fault?.diagnostic == .missingDependency)}
  for (name,c) in [("standalone binding",call(0x4c7fa0,actor,[0x5228dc])),("standalone helper",call(0x471530,0,[actor])),("standalone operator new",call(0x4f63ec,0,[0x174]))] {let f=try Fixture(p,hash);record(name+" outside elected callback rejected",f.host.withObjectAllocation(provider:f.memory){f.host.invoke(c)}?.completed != true && f.heap.lookupBytes(allocation,count:1)==nil)}
  do{let f=try Fixture(p,hash);let initialized=f.initialize();f.put(actor+0x70,0);record("cleared slot cannot orphan owned secondary",initialized && !f.initialize() && f.memory.ownsObjectAllocation(allocation,count:0x174))}
  do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={_ in f.put(actor+0x70,metadata)};record("empty secondary slot mutation during allocation rejected",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)}
  for (name,token,count) in [("actor",actor,UInt32(0x200)),("primary state",state,0x200),("world",world,0x200),("registry",registry,0x200)] {
   let f=try Fixture(p,hash);f.registryOverride={_,value in f.replace(token,count);return value};record(name+" identity replacement during registry service rejected",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)
  }
  let result:[String:Any]=["profiles":output,"controls":controls]
  try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"))
  print("native profiles \(output.count), controls \(controls.count)")
 }
}
