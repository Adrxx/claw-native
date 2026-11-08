import Foundation
private let base:UInt32=0x10000000,allocation:UInt32=0x61000000
private let actor=base+0x1000,state=base+0x2000,registry=base+0x4000,animations=base+0x6000,table=base+0x7000,string=base+0x8000,hit=base+0x9000,attack=base+0xa000,player=base+0xb000,controller=base+0xd000
private func u(_ x:Any)->UInt32 {(x as! NSNumber).uint32Value}
private func decode(_ s:String)->[UInt8] {stride(from:0,to:s.count,by:2).map{i in let a=s.index(s.startIndex,offsetBy:i);return UInt8(s[a..<s.index(a,offsetBy:2)],radix:16)!}}
private func args(_ c:ClawCall)->[UInt32] {var c=c;return withUnsafeBytes(of:&c.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(c.argumentCount)))}}
private func call(_ f:UInt32,_ receiver:UInt32=0,_ values:[UInt32]=[])->ClawCall {var c=ClawCall();c.function=f;c.receiver=receiver;c.argumentCount=UInt32(values.count);withUnsafeMutableBytes(of:&c.arguments){b in let p=b.bindMemory(to:UInt32.self);for i in values.indices{p[i]=values[i]}};return c}
private final class Fixture {
 let heap=ClawTokenHeap();let host:ClawNativeCanonicalHost;let memory:ClawNativeMfcMemory;let p:[String:Any]
 var images:[[UInt32]]=[],events:[[Any]]=[],calls:[[UInt32]]=[],allocations:[(UInt32,UInt32)]=[],requests:[[UInt32]]=[]
 var identities:[UInt32:ClawTokenHeap.AllocationIdentity]=[:]
 var pendingCount:UInt32=0
 var removed:UInt32?,hook:((ClawCall)->Void)?,shadowOffered=false
 init(_ p:[String:Any],_ hash:String)throws {
  self.p=p
  for b in p["initial"] as! [[String:Any]] {let bytes=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(bytes.count)).update(from:bytes,count:bytes.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x40
  let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710800+i*4))})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:allocation,sceneObjectAllocations:true)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in if [UInt32(0x431320),0x484d90,0x4f6428,0x431810,0x4f63ec,0x4c7fa0,0x4c8060,0x4c8160,0x4c81b0,0x4c96b0,0x4061b0,0x406290,0x4f65f2,0x4f6584,0x4dba00,0x4c8220,0x4c82a0,0x40f680,0x4dc870,0x4c9e30,0x431440,0x4041b0,0x431a70,0x431b10,0x431b40,0x431b70,0x431bd0,0x431c90].contains(c.function){self.calls.append([c.function,c.receiver])};if [UInt32(0x406290),0x4c8220,0x4c82a0,0x4f6584].contains(c.function){self.images.append([c.function,self.get(actor+0x174)])};self.hook?(c)}
  memory.beforeService={ [unowned self] f,a in if f==0x4a48e0{self.pendingCount=a[0]}}
  memory.failAllocation={ [unowned self] _ in self.pendingCount != 0 && self.pendingCount==u(p["exhausted"]!)}
  memory.beforeObjectAllocation={ [unowned self] r in
   func word(_ address:UInt32)->UInt32 {r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:Int(address-UInt32(CLAW_STACK_BASE)),as:UInt32.self).littleEndian}}
   self.requests.append([r.function,word(r.context.esp),word(r.context.esp+20),word(r.context.esp+4),r.context.ebx])
  }
  memory.afterService={ [unowned self] f,a,t in if f==0x4a48e0{self.events.append(["malloc",t,a[0]]);if t != 0{self.allocations.append((t,a[0]));self.identities[t]=self.heap.allocationIdentity(at:t,count:a[0])}};if f==0x4f6428{self.events.append(["free",a[0]])}}
 }
 func get(_ a:UInt32)->UInt32 {guard let b=host.bytes(a,count:4) else{return 0};return UnsafeRawPointer(b).loadUnaligned(as:UInt32.self).littleEndian}
 func put(_ a:UInt32,_ v:UInt32){if let b=host.bytes(a,count:4){var word=v.littleEndian;withUnsafeBytes(of:&word){b.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:4)}}}
 func name(_ a:UInt32)->String? {var b:[UInt8]=[];for i:UInt32 in 0..<128{guard let p=host.bytes(a+i,count:1) else{return nil};if p[0]==0{return String(bytes:b,encoding:.ascii)};b.append(p[0])};return nil}
 func service(_ c:ClawCall)->UInt32? {
  if removed==c.function{return nil};let a=args(c)
  if claw_canonical_lookup(c.function) != nil {shadowOffered=true;return nil}
  switch c.function {
  case 0x4f6286:
   guard a.count==2,let key=name(a[0]),host.bytes(a[1],count:4) != nil else{return nil}
   let literals:[UInt32]=[0x52417c,0x5240d8,0x5265ec,0x5265dc,0x5265c8,0x5265b0,0x526598,0x526580]
   let values=Dictionary(uniqueKeysWithValues:literals.enumerated().compactMap{i,v in name(v).map{($0,base+UInt32(23+i)*0x1000)}})
   let value:UInt32=c.receiver==registry+16 ? (["LogicHit":hit,"LogicAttack":attack][key] ?? 0):c.receiver==animations+16 ? (values[key] ?? 0):0
   guard value != 0 else{return nil};put(a[1],value);events.append(["registry",c.receiver,key,value]);return 1
  case 0x4f6974:
   guard a==[0],c.receiver>=table,c.receiver<table+256,get(c.receiver)==string+12 else{return nil};events.append(["buffer",c.receiver,string+12]);return string+12
  case 0x5469e4:
   guard a.count==1,let text=name(a[0]) else{return nil};return UInt32(text.utf8.count)
  case 0x4a4a80:
   guard a.count==3,let source=host.bytes(a[1],count:a[2]),let destination=host.bytes(a[0],count:a[2]) else{return nil};destination.update(from:source,count:Int(a[2]));return a[0]
  case 0x5469e8:
   guard a.count==1 else{return nil};let v=get(a[0]) &- 1;put(a[0],v);return v
  case 0x4a3dc0:
   guard a.count==2,let lhs=name(a[0]),let rhs=name(a[1]) else{return nil};return lhs==rhs ? 0:lhs<rhs ? UInt32.max:1
  case 0x546ce0:
   guard a.count==3 else{return nil};let x=(0..<4).map{Int32(bitPattern:get(a[1]+UInt32($0*4)))},y=(0..<4).map{Int32(bitPattern:get(a[2]+UInt32($0*4)))}
   var rect=[max(x[0],y[0]),max(x[1],y[1]),min(x[2],y[2]),min(x[3],y[3])];let ok=rect[0]<rect[2] && rect[1]<rect[3];if !ok{rect=[0,0,0,0]};for i in 0..<4{put(a[0]+UInt32(i*4),UInt32(bitPattern:rect[i]))};events.append(["intersect",x,y,rect]);return ok ? 1:0
  default:return memory.service(c)
  }
 }
 func invoke(_ command:UInt32)->ClawNativeCanonicalHost.Completion? {put(state+0x1c,command);return host.withObjectAllocation(provider:memory){host.invoke(call(0x431320,0,[actor]))}}
 func initialize()->Bool {invoke(0)?.completed==true}
 func snapshot(_ blocks:[[String:Any]])->[[String:Any]] {blocks.map{b in let token=u(b["address"]!),count=(b["data"] as! String).count/2;let bytes=memory.tlsSnapshot().allocationBytes[String(token)] ?? heap.lookupBytes(token,count:UInt32(count)).map{Array(UnsafeBufferPointer(start:$0,count:count))};return ["address":token,"data":bytes?.map{String(format:"%02x",$0)}.joined() ?? "missing"]}}
 func run()->[String:Any] {
  var results:[UInt32]=[],completed:[Bool]=[],snapshots:[[[String:Any]]]=[]
  let expected=p["snapshots"] as! [[[String:Any]]]
  for s in p["steps"] as! [[String:Any]] {put(player+0x4c,u(s["x"]!));put(player+0xcc,u(s["playerMode"]!));let r=invoke(u(s["command"]!));completed.append(r?.completed==true);if r?.completed != true{break};results.append(r!.eax!);snapshots.append(snapshot(expected[snapshots.count]))}
  var roundtrip:[[String:Any]]=[]
  if (u(p["speed"]!)==UInt32(bitPattern:-451) || p["multi_image"] as! Bool) && u(p["exhausted"]!)==0{let helper=get(state+0x18);if host.retireConveyorBelt(actor:actor,provider:memory){events.append(["free",helper]);if initialize(){roundtrip=snapshot(p["roundtrip"] as! [[String:Any]])}}}
  let intact=allocations.allSatisfy{token,count in memory.tlsSnapshot().allocationBytes[String(token)] != nil && (heap.lookupBytes(token,count:1)==nil || (heap.allocationIdentity(at:token,count:count) === identities[token] && memory.ownsObjectAllocation(token,count:count)))}
  return ["images":images,"roundtrip":roundtrip,"label":p["label"]!,"results":results,"completed":completed,"snapshots":snapshots,"events":events,"calls":calls,"requests":requests,"frontier":host.fault.map{$0.address as Any} ?? NSNull(),"physicalIntegrity":intact,"shadowOffered":shadowOffered]
 }
 func replace(_ token:UInt32,_ count:UInt32) {guard let bytes=heap.lookupBytes(token,count:count) else{return};let copy=Array(UnsafeBufferPointer(start:bytes,count:Int(count)));heap.free(token);heap.storeBytes(token:token,count:count).update(from:copy,count:copy.count)}
}
@main struct ConveyorBeltTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]),ref=try JSONSerialization.jsonObject(with:Data(contentsOf:dir.appendingPathComponent("reference.json"))) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  var output:[[String:Any]]=[];for profile in profiles{output.append(try Fixture(profile,hash).run())}
  var exhausted:[[String:Any]]=[];for profile in ref["exhaustions"] as! [[String:Any]]{exhausted.append(try Fixture(profile,hash).run())}
  let multi=profiles.first{$0["multi_image"] as! Bool}!
  var controls:[[String:Any]]=[];func record(_ name:String,_ passed:Bool){controls.append(["name":name,"passed":passed])}
  do{let f=try Fixture(p,hash);record("canonical owner precedence",f.initialize() && !f.shadowOffered)}
  do{let f=try Fixture(p,hash);record("provider required",!f.host.invoke(call(0x431320,0,[actor])).completed)}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);record("foreign provider",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(call(0x431320,0,[actor]))}==nil)}
  for callback:UInt32 in [0,0x40f7b0,0x431321]{let f=try Fixture(p,hash);f.put(state+0x10,callback);record("wrong callback \(callback)",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)}
  for removed:UInt32 in [0x4f6286,0x4f6974,0x546ce0,0x5469e4]{let f=try Fixture(p,hash);let later=removed==0x4f6974 || removed==0x546ce0;let ready=later ? f.initialize():true;f.removed=removed;record("missing physical service \(removed)",ready && f.invoke(later ? 7:0)?.completed != true)}
  for offset:UInt32 in [4,20]{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={r in if r.count==0x58{f.host.bytes(r.context.esp+offset,count:4)!.update(repeating:0,count:4)}};record("size or continuation \(offset)",!f.initialize())}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(call(0x431320,0,[actor]))};record("allocation reentry",!f.initialize() && nested?.completed==false)}
  do{let f=try Fixture(p,hash);f.memory.afterService={fn,a,t in if fn==0x4a48e0 && a[0]==0x58 && t != 0{f.replace(t,0x58)}};record("allocation identity replacement",!f.initialize())}
  for (name,bad) in [("wrong size",call(0x4f63ec,0,[0x54])),("wrong receiver",call(0x4f63ec,actor,[0x58])),("wrong constructor actor",call(0x431810,allocation,[actor+4])),("wrong constructor helper",call(0x431810,allocation+4,[actor]))]{let f=try Fixture(p,hash);f.hook={c in if c.function==(name.contains("constructor") ? 0x431810:0x4f63ec){f.hook=nil;_=f.host.callNativeDependency(bad)}};record(name,!f.initialize())}
  for (name,c) in [("standalone allocation",call(0x4f63ec,0,[0x58])),("standalone lifecycle receiver",call(0x4c9e30,allocation,[0]))]{let f=try Fixture(p,hash);record(name,f.host.withObjectAllocation(provider:f.memory){f.host.invoke(c)}?.completed != true)}
  for (name,token,count) in [("actor",actor,UInt32(0x400)),("logic",state,0x400),("helper",allocation,0x58),("vtable",UInt32(0x50c6bc),0x24),("cycle",base+0x17000,0x400),("image",base+0x12000,0x400)]{let f=try Fixture(p,hash),ready=f.initialize();f.replace(token,count);record("replaced \(name)",ready && f.invoke(7)?.completed != true)}
  for (address,value) in [(allocation,UInt32(0x50b6ec)),(UInt32(0x50c6c0),UInt32(0x4c96b0)),(UInt32(0x50c6c4),UInt32(0x40fb30))]{let f=try Fixture(p,hash),ready=f.initialize();f.put(address,value);record("wrong vtable \(address)",ready && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash),ready=f.initialize();record("repeat constructor cannot leak",ready && !f.initialize())}
  do{let f=try Fixture(p,hash),ready=f.initialize();record("retired helper",ready && f.memory.releaseSceneObject(allocation) && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash),ready=f.initialize();let retired=ready && f.memory.releaseSceneObject(allocation);record("double free",retired && !f.memory.releaseSceneObject(allocation))}
  do{let f=try Fixture(p,hash);_=f.heap.storeBytes(token:allocation,count:0x58);record("foreign free",!f.memory.releaseSceneObject(allocation) && f.heap.lookupBytes(allocation,count:0x58) != nil)}
  do{let f=try Fixture(p,hash),ready=f.initialize();let retired=ready && f.host.retireConveyorBelt(actor:actor,provider:f.memory);let recreated=retired && f.initialize();record("owner teardown recreate",recreated && f.get(state+0x18) != allocation && f.heap.lookupBytes(allocation,count:1)==nil && f.memory.ownsObjectAllocation(f.get(state+0x18),count:0x58));if recreated{f.put(state+0x18,allocation)};record("recreated owner rejects stale helper",recreated && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash);f.memory.afterService={fn,a,t in if fn==0x4a48e0 && a[0]==31 && t != 0{f.replace(t,31)}};record("CString allocation identity replacement",!f.initialize())}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeService={fn,a in if fn==0x4a48e0 && a[0]==31{nested=f.host.invoke(call(0x431320,0,[actor]))}};record("CString allocation reentry",!f.initialize() && nested?.completed==false)}
  do{let f=try Fixture(p,hash),ready=f.initialize();f.hook={c in if c.function==0x431440{f.hook=nil;_=f.host.callNativeDependency(call(0x4c9e30,allocation,[0]))}};record("lifecycle receiver outside elected phase",ready && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash),ready=f.initialize();f.hook={c in if c.function==0x4c9e30{f.hook=nil;_=f.host.callNativeDependency(call(0x4c9e30,allocation+4,[0]))}};record("lifecycle foreign helper receiver",ready && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash),ready=f.initialize();f.hook={c in if c.function==0x4f6974{f.hook=nil;f.replace(player,0x400)}};record("player identity replaced during lifecycle",ready && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash);var replaced:UInt32=0;f.memory.afterService={fn,a,_ in if fn==0x4f6428 && a[0] != allocation{replaced=a[0];f.heap.storeBytes(token:a[0],count:31).update(repeating:0x63,count:31)}};record("CString free rejects foreign replacement",!f.initialize() && replaced != 0 && f.heap.lookupBytes(replaced,count:31) != nil && f.heap.lookup(replaced,words:1)?[0]==0x63636363)}
  let imageSet=base+0x12000,firstImage=base+0x13000,imageTable=base+0x14000,secondImage=base+0x1f000,thirdImage=base+0x20000
  for (name,token) in [("image manager",imageSet),("image table",imageTable),("initial image header",firstImage),("selected image header",secondImage),("other image header",thirdImage)]{
   let f=try Fixture(multi,hash),ready=f.initialize();f.replace(token,0x400);record("multi-image replaced \(name)",ready && f.invoke(7)?.completed != true)
  }
  for (name,address,value) in [("null frame",actor+0x174,UInt32(0)),("stale initial frame",actor+0x174,firstImage),("foreign frame",actor+0x174,player),("foreign image manager",actor+0x170,player),("foreign image table",imageSet+0x14,table),("foreign selected table entry",imageTable+4,player),("manager bounds",imageSet+0x68,UInt32(1))]{
   let f=try Fixture(multi,hash),ready=f.initialize();f.put(address,value);record("multi-image \(name)",ready && f.invoke(7)?.completed != true)
  }
  for (name,token) in [("manager",imageSet),("table",imageTable),("initial frame",firstImage),("selected frame",secondImage),("other frame",thirdImage)]{
   let f=try Fixture(multi,hash);f.hook={c in if c.function==0x4c82a0{f.hook=nil;f.replace(token,0x400)}};record("constructor animation replaces \(name)",!f.initialize())
  }
  for (name,address,value) in [("valid alternative frame",actor+0x174,thirdImage),("foreign frame",actor+0x174,player),("foreign manager",actor+0x170,player),("foreign table",imageSet+0x14,table),("manager bounds",imageSet+0x68,UInt32(1)),("valid table link",imageTable+4,thirdImage)]{
   let f=try Fixture(multi,hash);f.hook={c in if c.function==0x4c82a0{f.hook=nil;f.put(address,value)}};record("constructor animation injects \(name)",!f.initialize())
  }
  for (name,address,value) in [("null frame",actor+0x174,UInt32(0)),("stale initial frame",actor+0x174,firstImage),("foreign frame",actor+0x174,player),("foreign manager",actor+0x170,player),("foreign selected table entry",imageTable+4,player)]{
   let f=try Fixture(multi,hash);f.hook={c in if c.function==0x4f6584{f.hook=nil;f.put(address,value)}};record("constructor teardown \(name)",!f.initialize())
  }
  do{let f=try Fixture(multi,hash),ready=f.initialize();let selected=f.get(actor+0x174);let retired=ready && f.host.retireConveyorBelt(actor:actor,provider:f.memory);let recreated=retired && f.initialize();record("multi-image teardown recreate",recreated && selected==secondImage && f.get(actor+0x174)==thirdImage && f.get(state+0x18) != allocation);if recreated{f.put(state+0x18,allocation)};record("multi-image recreated stale helper",recreated && f.invoke(7)?.completed != true)}
  let result:[String:Any]=["version":1,"profiles":output,"exhaustions":exhausted,"controls":controls];try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"));print("native profiles \(output.count), controls \(controls.count)")
 }
}
