import Foundation

// Finite transport comparison. All constructors and virtual/state methods run
// through their real canonical owners; this fixture supplies physical services.
private let base:UInt32=0x10000000,allocation:UInt32=0x61000000
private let actor=base+0x1000,state=base+0x2000,world=base+0x3000,registry=base+0x4000,table=base+0x5000,string=base+0x6000,hit=base+0x7000,attack=base+0x8000
private let methods=base+0x9000
private func u(_ x:Any)->UInt32 {(x as! NSNumber).uint32Value}
private func decode(_ s:String)->[UInt8] {stride(from:0,to:s.count,by:2).map{i in let a=s.index(s.startIndex,offsetBy:i);return UInt8(s[a..<s.index(a,offsetBy:2)],radix:16)!}}
private func args(_ c:ClawCall)->[UInt32] {var c=c;return withUnsafeBytes(of:&c.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(c.argumentCount)))}}
private func call(_ f:UInt32,_ receiver:UInt32=0,_ values:[UInt32]=[])->ClawCall {
 var c=ClawCall();c.function=f;c.receiver=receiver;c.argumentCount=UInt32(values.count)
 withUnsafeMutableBytes(of:&c.arguments){b in let p=b.bindMemory(to:UInt32.self);for i in values.indices{p[i]=values[i]}}
 return c
}
private final class Fixture {
 let heap=ClawTokenHeap();let host:ClawNativeCanonicalHost;let memory:ClawNativeMfcMemory;let p:[String:Any];let allocationMinimum:UInt32;let root:UInt32
 var requests:[[UInt32]]=[],events:[[Any]]=[],calls:[[UInt32]]=[],allocations:[(UInt32,UInt32)]=[]
 var ordinary:[(UInt32,UInt32,ClawTokenHeap.AllocationIdentity)]=[],foreign:[(UInt32,UInt32,ClawTokenHeap.AllocationIdentity)]=[]
 var removed:UInt32?,hook:((ClawCall)->Void)?,shadowOffered=false,allocating=0
 var registryOverride:((String,UInt32)->UInt32)?
 init(_ p:[String:Any],_ hash:String,allocationBase:UInt32=allocation,root:UInt32=0x4887b0)throws {
  self.p=p;self.allocationMinimum=allocationBase;self.root=root
  for b in p["initial"] as! [[String:Any]] {let bytes=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(bytes.count)).update(from:bytes,count:bytes.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x40
  let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:allocationBase,sceneObjectAllocations:true)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in self.calls.append([c.function,c.receiver]);if c.function==0x4f6428{let token=args(c)[0];self.events.append(["delete",token,self.get(token)])};self.hook?(c)}
  memory.beforeObjectAllocation={ [unowned self] r in
   func word(_ address:UInt32)->UInt32 {r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:Int(address-UInt32(CLAW_STACK_BASE)),as:UInt32.self).littleEndian}}
   self.requests.append([r.function,word(r.context.esp),word(r.context.esp+20),word(r.context.esp+4),r.context.ebx]);self.allocating+=1
   if p["interleave"] as? Bool==true && self.allocating==2 {self.allocateOrdinary()}
   if self.allocating==Int(u(p["occupied"]!)) {
    let candidate=self.nextCandidate
    self.heap.storeBytes(token:candidate,count:r.count).update(repeating:0x6d,count:Int(r.count))
    self.foreign.append((candidate,r.count,self.heap.allocationIdentity(at:candidate,count:r.count)!))
   }
  }
  memory.failAllocation={ [unowned self] _ in self.allocating==Int(u(p["exhausted"]!)) && self.allocating>0}
  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]]);if v != 0{self.allocations.append((v,a[0]))}}}
 }
 func get(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)?[0] ?? 0}
 func put(_ a:UInt32,_ v:UInt32){if let p=heap.lookup(a,words:1){p[0]=v}}
 var nextCandidate:UInt32 {max(allocationMinimum,(allocations + ordinary.map{($0.0,$0.1)}).map{($0.0+($0.1==0x1b4 ? 512:$0.1)+15) & ~15}.max() ?? allocationMinimum)}
 func allocateOrdinary() {
  for count:UInt32 in [0x1b4,0x174,12] {
   let token=heap.allocate(bytes:count)
   guard token != 0,let bytes=heap.lookupBytes(token,count:count),let identity=heap.allocationIdentity(at:token,count:count) else {continue}
   bytes.update(repeating:0x5a,count:Int(count));ordinary.append((token,count,identity));events.append(["ordinary",token,count])
  }
 }
 func exact(_ token:UInt32,_ count:UInt32)->Bool {token & 15==0 && heap.allocationIdentity(at:token,count:count) != nil && heap.lookupBytes(token,count:count+1)==nil}
 var ordinaryIntact:Bool {ordinary.allSatisfy{token,count,identity in heap.allocationIdentity(at:token,count:count) === identity && exact(token,count) && heap.lookupBytes(token,count:count).map{UnsafeBufferPointer(start:$0,count:Int(count)).allSatisfy{$0==0x5a}}==true}}
 func service(_ c:ClawCall)->UInt32? {
  if removed==c.function{return nil};let a=args(c)
  if claw_canonical_lookup(c.function) != nil {shadowOffered=true;return 99}
  switch c.function {
  case 0x4f6286:
   guard a.count==2,c.receiver==registry+16,let out=host.bytes(a[1],count:4) else{return nil}
   var name:[UInt8]=[]
   for i:UInt32 in 0..<64 {guard let b=host.bytes(a[0]+i,count:1) else{return nil};if b[0]==0{break};name.append(b[0])}
   guard let key=String(bytes:name,encoding:.ascii) else{return nil}
   var value:UInt32
   if key.hasPrefix("LEVEL_EARTHQUAKE") {value=base+0xb000}
   else if c.receiver==registry+16 {value=["LogicHit":hit,"LogicAttack":attack][key] ?? 0}
   else {value=0}
   value=registryOverride?(key,value) ?? value
   var word=value.littleEndian;withUnsafeBytes(of:&word){out.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:4)}
   events.append(["registry",c.receiver,key,value]);return value==0 ? 0:1
  case 0x4f6974:
   guard a==[0],c.receiver>=table,c.receiver<table+256,c.receiver & 3==0,get(c.receiver)==string+12,
         get(string)==1,get(string+4)==7,get(string+8)==32 else{return nil}
   events.append(["buffer",c.receiver,string+12]);return string+12
  case 0x4a3050:
   guard c.receiver==0,a.isEmpty else{return nil};let value=u(p["random"]!);events.append(["random",value]);return value
  default:return memory.service(c)
  }
 }
 func invoke(_ command:UInt32,_ target:UInt32=actor)->ClawNativeCanonicalHost.Completion? {
  put(get(target+0x6c)+0x1c,command)
  put(0x537210,1234+u(p["elapsed"]!))
  return host.withObjectAllocation(provider:memory){host.invoke(call(root,0,[target]))}
 }
 func initialize()->Bool {invoke(0)?.completed==true}
 func snapshot(_ blocks:[[String:Any]])->[[String:Any]] {
  blocks.map {b in let address=u(b["address"]!),n=UInt32((b["data"] as! String).count/2)
   let bytes=heap.lookupBytes(address,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing"
   return ["address":address,"data":bytes]
  }
 }
 func run()->[String:Any] {
  var results:[UInt32]=[],completed:[Bool]=[],snapshots:[[[String:Any]]]=[]
  let expected=p["snapshots"] as! [[[String:Any]]]
  for (i,s) in (p["steps"] as! [NSNumber]).enumerated(){
   if s.intValue == -1 {
    let helper=get(state+0x18),done=retire();completed.append(done);if !done{break}
    allocations.removeAll{$0.0==helper};results.append(helper)
   } else {
    if s.uint32Value==7 && u(p["handler"]!)==0x488cd0 {put(get(state+0x18)+0x4c,1234);put(get(state+0x18)+0x50,100);put(actor+8,get(actor+8)|1)}
    let r=invoke(s.uint32Value);completed.append(r?.completed==true);if r?.completed != true{if i<expected.count{snapshots.append(snapshot(expected[i]))};break};if let value=r?.eax{results.append(value)}
   }
   snapshots.append(snapshot(expected[i]))
  }
  return ["label":p["label"]!,"results":results,"completed":completed,"snapshots":snapshots,"events":events,"calls":calls,"requests":requests,"frontier":host.fault.map{$0.address as Any} ?? NSNull(),"foreign":snapshot(p["foreign"] as! [[String:Any]]),
   "physicalIntegrity":ordinaryIntact && allocations.allSatisfy{exact($0.0,$0.1) && memory.ownsObjectAllocation($0.0,count:$0.1)} && foreign.allSatisfy{heap.allocationIdentity(at:$0.0,count:$0.1) === $0.2}]
 }
 func replace(_ token:UInt32,_ count:UInt32) {
  guard let bytes=heap.lookupBytes(token,count:count) else{return};let copy=Array(UnsafeBufferPointer(start:bytes,count:Int(count)))
  heap.free(token);heap.storeBytes(token:token,count:count).update(from:copy,count:copy.count)
 }
 func retire()->Bool {host.retireShake(actor:actor,provider:memory)}
}
@main struct ShakeTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]),data=try Data(contentsOf:dir.appendingPathComponent("reference.json"))
  let ref=try JSONSerialization.jsonObject(with:data) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  var output:[[String:Any]]=[];for profile in profiles{output.append(try Fixture(profile,hash).run())}
  var exhausted:[[String:Any]]=[];for profile in ref["exhaustions"] as! [[String:Any]]{exhausted.append(try Fixture(profile,hash).run())}
  var controls:[[String:Any]]=[]
  func record(_ name:String,_ passed:Bool){controls.append(["name":name,"passed":passed])}
  do{let f=try Fixture(p,hash);record("canonical owners cannot be shadowed",f.initialize() && !f.shadowOffered)}
  do{let f=try Fixture(p,hash,allocationBase:0x62000000);record("provider minimum above shared cursor",f.initialize() && f.get(state+0x18)>=0x62000000)}
  do {
   let f=try Fixture(p,hash,allocationBase:0x62000000),ready=f.initialize(),helper=f.get(state+0x18)
   record("minimum helper exact physical owner extent",ready && helper==0x62000000 && f.exact(helper,0x54) && f.memory.ownsObjectAllocation(helper,count:0x54) && f.heap.allocationIdentity(at:helper+4,count:0x54)==nil && f.heap.lookup(helper,words:22)==nil)
   let identity=f.heap.allocationIdentity(at:helper,count:0x54)
   f.allocateOrdinary()
   record("minimum helper ordinary interleave preserves owner",ready && f.ordinary.count==3 && f.ordinary[0].0>helper && f.ordinaryIntact && identity != nil && f.heap.allocationIdentity(at:helper,count:0x54) === identity)
   let retired=ready && f.retire()
   record("minimum helper owner routed destruction",retired && f.heap.lookupBytes(helper,count:1)==nil && !f.memory.ownsObjectAllocation(helper,count:0x54) && f.memory.claimsSceneObject(helper) && f.ordinaryIntact && f.calls.contains(where:{$0[0]==0x484d90 && $0[1]==helper}))
   record("minimum helper double retirement rejected",retired && !f.retire() && f.heap.lookupBytes(helper,count:1)==nil && f.ordinaryIntact)
  }
  do {
   var occupied=p;occupied["occupied"]=NSNumber(value:1)
   let f=try Fixture(occupied,hash,allocationBase:0x62000000),failed = !f.initialize()
   record("minimum occupied base preserves foreign storage",failed && f.foreign.count==1 && f.foreign[0].0==0x62000000 && f.heap.allocationIdentity(at:0x62000000,count:0x54) === f.foreign[0].2 && f.heap.lookupBytes(0x62000000,count:0x54).map{UnsafeBufferPointer(start:$0,count:0x54).allSatisfy{$0==0x6d}}==true && !f.memory.ownsObjectAllocation(0x62000000,count:0x54))
  }
  do {
   let f=try Fixture(p,hash,allocationBase:0x62000000),ready=f.initialize(),helper=f.get(state+0x18)
   let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
   let foreign=try ClawNativeMfcMemory(host:f.host,sha256:hash,importTargets:imports,allocationBase:0x63000000,sceneObjectAllocations:true)
   let identity=f.heap.allocationIdentity(at:helper,count:0x54)
   record("minimum helper foreign owner release rejected",ready && !foreign.releaseSceneObject(helper) && identity != nil && f.heap.allocationIdentity(at:helper,count:0x54) === identity)
  }
  do {
   let f=try Fixture(p,hash,allocationBase:0x62000000),ready=f.initialize(),helper=f.get(state+0x18)
   let foreign:UInt32=0x63000000
   f.heap.storeBytes(token:foreign,count:0x54).update(repeating:0x6d,count:0x54)
   let identity=f.heap.allocationIdentity(at:foreign,count:0x54),retired=ready && f.retire()
   record("minimum retirement leaves foreign storage intact",retired && f.heap.lookupBytes(helper,count:1)==nil && f.heap.allocationIdentity(at:foreign,count:0x54) === identity && f.heap.lookupBytes(foreign,count:0x54).map{UnsafeBufferPointer(start:$0,count:0x54).allSatisfy{$0==0x6d}}==true)
  }
  do{let f=try Fixture(p,hash);let ready=f.initialize();let result=f.invoke(7);record("real Shake state callback runs",ready && result?.completed==true && f.calls.contains(where:{$0[0]==0x4889e0 && $0[1]==allocation}) && f.calls.contains(where:{$0[0]==0x488c90 && $0[1]==allocation}) && !f.shadowOffered)}
  for command:UInt32 in [0,1000,29,30,7]{let f=try Fixture(p,hash);f.put(state+0x1c,command);record("provider required command \(command)",!f.host.invoke(call(0x4887b0,0,[actor])).completed)}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);record("foreign provider rejected",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(call(0x4887b0,0,[actor]))}==nil)}
  for callback:UInt32 in [0,0x40f7b0,0x4887b1]{let f=try Fixture(p,hash);f.put(state+0x10,callback);record("wrong owner callback \(callback)",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)}
  for removed:UInt32 in [0x4f6286,0x4f6974]{let f=try Fixture(p,hash);if removed==0x4f6974{_=f.initialize()};f.removed=removed;record("missing service \(removed)",f.invoke(removed==0x4f6286 ? 0:7)?.completed != true)}
  for attempt in 1...3 {
   for offset:UInt32 in [4,20]{let f=try Fixture(p,hash);var n=0;f.memory.beforeObjectAllocation={r in n+=1;if n==attempt{f.host.bytes(r.context.esp+offset,count:4)!.update(repeating:0,count:4)}};record("allocation \(attempt) size/continuation \(offset)",!f.initialize())}
   do{let f=try Fixture(p,hash);var n=0,nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in n+=1;if n==attempt{nested=f.host.invoke(call(0x4887b0,0,[actor]))}};record("allocation \(attempt) reentry",!f.initialize() && nested?.completed==false)}
   do{let f=try Fixture(p,hash);var n=0;f.memory.afterService={fn,a,t in if fn==0x4a48e0{n+=1;if n==attempt && t != 0{f.replace(t,a[0])}}};record("allocation \(attempt) identity replacement",!f.initialize())}
  }
  for (metadata,correct) in [(hit,UInt32(0x4dc830)),(attack,UInt32(0x4dc850))]{
   for wrong:UInt32 in [0,0x491fa0,correct+1]{let f=try Fixture(p,hash);f.put(metadata+16,wrong);record("wrong metadata callback \(metadata) \(wrong)",!f.initialize())}
   do{let f=try Fixture(p,hash);f.registryOverride={_,value in value==metadata ? 0:value};record("nonzero metadata required \(metadata)",!f.initialize())}
  }
  for offset:UInt32 in [0x70,0x78]{let f=try Fixture(p,hash);f.put(actor+offset,hit);record("unowned secondary storage \(offset)",!f.initialize())}
  for (name,c) in [("standalone helper allocation",call(0x4f63ec,0,[0x54])),("standalone receiver stdcall",call(0x4c9e30,allocation,[0])),("standalone constructor",call(0x488870,allocation,[actor]))]{let f=try Fixture(p,hash);record(name,f.host.withObjectAllocation(provider:f.memory){f.host.invoke(c)}?.completed != true)}
  for (name,bad) in [("wrong size",call(0x4f63ec,0,[0xa4])),("wrong allocation receiver",call(0x4f63ec,actor,[0x54])),("wrong constructor actor",call(0x488870,allocation,[actor+4])),("wrong constructor helper",call(0x488870,allocation+4,[actor]))]{
   let f=try Fixture(p,hash);f.hook={c in if c.function==(name.contains("constructor") ? 0x488870:0x4f63ec){f.hook=nil;_=f.host.callNativeDependency(bad)}};record(name,!f.initialize())
  }
  for (name,token,count) in [("actor",actor,UInt32(0x400)),("state",state,0x400),("helper",allocation,0x54),("vtable",UInt32(0x50f63c),0x24),("logic manager",registry,0x400),("game clock",UInt32(0x537210),4),("global registry",UInt32(0x537668),0x60),("state callbacks",UInt32(0x53c2a0),0x30)]{
   let f=try Fixture(p,hash);let ready=f.initialize();f.replace(token,count);record("retained \(name) identity",ready && f.invoke(7)?.completed != true)
  }
  for offset:UInt32 in [0x70,0x78]{let f=try Fixture(p,hash);let ready=f.initialize();f.replace(f.get(actor+offset),0x174);record("secondary allocation identity \(offset)",ready && f.invoke(7)?.completed != true)}
  for (address,value) in [(allocation,UInt32(0x50b6ec)),(UInt32(0x50f640),UInt32(0x4c96b0)),(UInt32(0x50f644),UInt32(0x40fb30))]{let f=try Fixture(p,hash);let ready=f.initialize();f.put(address,value);record("cross-owner metadata \(address)",ready && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash);let ready=f.initialize();record("duplicate initialization rejected",ready && !f.initialize())}
  do{let f=try Fixture(p,hash);let ready=f.initialize();let retired=ready && f.retire();let recreated=retired && f.initialize();record("destroy recreate retains canonical secondary binding",recreated && f.heap.lookupBytes(allocation,count:1)==nil && f.get(state+0x18) != allocation && f.calls.contains(where:{$0[0]==0x484d90}) && f.calls.contains(where:{$0[0]==0x4c81b0}) && f.invoke(7)?.completed==true)}
  do{let f=try Fixture(p,hash);let ready=f.initialize();let old=f.get(state+0x18);let retired=ready && f.retire();let recreated=retired && f.initialize();f.put(state+0x18,old);record("recreated owner rejects stale helper",recreated && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash);let ready=f.initialize();let secondary=[f.get(actor+0x70),f.get(actor+0x78)];let retired=ready && f.retire();let cleared=retired && secondary.allSatisfy{f.memory.releaseSceneObject($0)};f.put(actor+0x70,0);f.put(actor+0x78,0);f.allocateOrdinary();let recreated=cleared && f.initialize();record("destroy recreate with fresh secondaries and shared allocations",recreated && f.ordinaryIntact && f.get(state+0x18)>f.ordinary[2].0 && f.invoke(7)?.completed==true)}
  do{let f=try Fixture(p,hash);let ready=f.initialize();var attempted=false,released=false;f.hook={c in if c.function==0x4f6974{f.hook=nil;attempted=true;released=f.retire()}};let result=f.invoke(7);record("active lifecycle cannot retire helper",ready && attempted && !released && result?.completed != true && f.heap.lookupBytes(allocation,count:0x54) != nil)}
  do{let f=try Fixture(p,hash);let ready=f.initialize();let retired=ready && f.retire();record("double retirement rejected",retired && !f.retire())}
  do{let f=try Fixture(p,hash);let ready=f.initialize();let other=try Fixture(p,hash);record("foreign provider retirement rejected",ready && !f.host.retireShake(actor:actor,provider:other.memory) && f.heap.lookupBytes(allocation,count:0x54) != nil)}
  do {
   let f=try Fixture(p,hash),ready=f.initialize()
   let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
   let replacement=try ClawNativeMfcMemory(host:f.host,sha256:hash,importTargets:imports,allocationBase:0x62000000,sceneObjectAllocations:true)
   f.put(state+0x1c,7)
   let result=f.host.withObjectAllocation(provider:replacement){f.host.invoke(call(0x4887b0,0,[actor]))}
   record("same-host replacement provider rejected",ready && result?.completed != true && f.heap.lookupBytes(allocation,count:0x54) != nil)
  }
  do{let f=try Fixture(p,hash);let ready=f.initialize();record("direct deleting destructor has no owner authority",ready && f.host.withObjectAllocation(provider:f.memory){f.host.invoke(call(0x484d90,allocation,[1]))}?.completed != true && f.heap.lookupBytes(allocation,count:0x54) != nil)}
  for (name,bad) in [("lifecycle wrong receiver",call(0x4c9e30,allocation+4,[string+12])),("lifecycle wrong phase",call(0x4041b0,allocation,[string+12]))]{
   let f=try Fixture(p,hash),ready=f.initialize();f.hook={c in if c.function==0x4c9e30{f.hook=nil;_=f.host.callNativeDependency(bad)}}
   record(name,ready && f.invoke(7)?.completed != true)
  }
  do{let f=try Fixture(p,hash);let ready=f.initialize();var attempted=false,nested=false;f.hook={c in if c.function==0x4f6428{f.hook=nil;attempted=true;nested=f.retire()}};let result=f.retire();record("deletion reentry rejected",ready && attempted && !nested && !result && f.heap.lookupBytes(allocation,count:0x54) != nil)}
  do{let f=try Fixture(p,hash);let ready=f.initialize();f.host.dependency={_,c in c.function==0x4f6974 ? 0:f.service(c)};record("zero state registry substitute rejected",ready && f.invoke(7)?.completed != true)}
  for command:UInt32 in [1000,29,30,7]{let f=try Fixture(p,hash);record("unconstructed lifecycle phase \(command)",f.invoke(command)?.completed != true && f.heap.lookupBytes(allocation,count:1)==nil)}
  do{let f=try Fixture(p,hash);var duplicate:UInt32?;f.memory.beforeObjectAllocation={r in duplicate=f.memory.allocateObject(r)};record("duplicate allocation lease rejected",!f.initialize() && duplicate==nil && f.heap.lookupBytes(allocation,count:1)==nil)}
  for (name,address,value) in [("state callback replaced",methods+28,UInt32(0x448b00)),("state table slot changed",UInt32(0x53c2b0),methods+4),("actor link changed",actor+0x6c,state+4),("helper publication changed",state+0x18,allocation+4)] {
   let f=try Fixture(p,hash),ready=f.initialize();f.put(address,value);record(name,ready && f.invoke(7)?.completed != true)
  }
  for missing:UInt32 in [0x4a3050,0x4f6286] {
   let activation=profiles.first{$0["label"] as? String=="activate-random-1"}!,f=try Fixture(activation,hash),ready=f.initialize();f.removed=missing
   record("missing activation physical service \(missing)",ready && f.invoke(7)?.completed != true)
  }
  let activation=profiles.first{$0["label"] as? String=="activate-random-1"}!
  do {
   let f=try Fixture(activation,hash),ready=f.initialize();f.put(0x532c0c,1)
   record("enabled playback requires physical audio owner",ready && f.invoke(7)?.completed != true && f.host.fault != nil && f.get(allocation+0x48)==base+0xb000)
  }
  for target:UInt32 in [0x4889e0,0x488c90,0x488cd0,0x488cf0] {
   for receiver in [allocation,allocation+4] {
    let f=try Fixture(p,hash),ready=f.initialize(),c=call(target,receiver,target==0x4889e0 ? [7]:[])
    record("direct state authority \(target) receiver \(receiver)",ready && f.host.withObjectAllocation(provider:f.memory){f.host.invoke(c)}?.completed != true)
   }
  }
  for offset:UInt32 in [0x10,0x1c,0x20] {
   let f=try Fixture(p,hash),ready=f.initialize();f.put(0x50f63c+offset,0x4c96b1)
   record("wrong no-op vtable slot \(offset)",ready && f.invoke(offset==0x1c ? 30:29)?.completed != true)
  }
  for offset:UInt32 in [0x70,0x78] {
   for replacement in [UInt32(0),hit,allocation] {
    let f=try Fixture(p,hash),ready=f.initialize();f.put(actor+offset,replacement)
    record("stale secondary binding \(offset) value \(replacement)",ready && f.invoke(7)?.completed != true)
   }
  }
  for mutation in ["random","lookup"] {
   let f=try Fixture(activation,hash),ready=f.initialize(),selected=ready && f.invoke(7)?.completed==true
   if mutation=="random" {f.host.dependency={_,c in if c.function==0x4a3050{f.replace(base+0xb000,0x400)};return f.service(c)}}
   else {f.registryOverride={key,value in if key.hasPrefix("LEVEL_EARTHQUAKE"){f.replace(base+0xb000,0x400)};return value}}
   record("retained sound identity replacement during \(mutation)",selected && f.invoke(7)?.completed != true)
  }
  do {
   let f=try Fixture(activation,hash),ready=f.initialize();var attempted=false,nested:ClawNativeCanonicalHost.Completion?
   f.host.dependency={_,c in if c.function==0x4a3050 {attempted=true;nested=f.host.invoke(call(0x4887b0,0,[actor]))};return f.service(c)}
   record("random provider reentry rejected",ready && f.invoke(7)?.completed != true && attempted && nested?.completed==false)
  }
  for stage:UInt32 in [0x4c7fa0,0x4c8060] {
   for offset:UInt32 in [0x18,0x1c] {
    let f=try Fixture(p,hash);f.hook={c in if c.function==stage {f.hook=nil;f.put(state+offset,offset==0x18 ? allocation+4:29)}}
    record("constructor binding preserves publication/command \(stage) \(offset)",!f.initialize())
   }
  }
  for attempt in 1...3 {
   for offset:UInt32 in [0x18,0x1c] {
    let f=try Fixture(p,hash);var n=0;f.memory.beforeObjectAllocation={_ in n+=1;if n==attempt{f.put(state+offset,offset==0x18 ? allocation+4:29)}}
    record("allocator preserves publication/command \(attempt) \(offset)",!f.initialize())
   }
  }
  for mutation in ["identity","selection"] {
   let f=try Fixture(activation,hash),ready=f.initialize(),selected=ready && f.invoke(7)?.completed==true
   if mutation=="identity" {f.replace(base+0xb000,0x400)}
   else {f.put(allocation+0x48,hit)}
   record("retained sound between callbacks \(mutation)",selected && f.invoke(1000)?.completed != true)
  }
  let result:[String:Any]=["version":1,"profiles":output,"exhaustions":exhausted,"controls":controls]
  try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"))
  print("native profiles \(output.count), controls \(controls.count)")
 }
}
