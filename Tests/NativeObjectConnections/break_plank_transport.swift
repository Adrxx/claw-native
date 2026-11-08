import Foundation
private let base:UInt32=0x10000000,allocation:UInt32=0x61000000
private let actor=base+0x1000,state=base+0x2000,world=base+0x3000,registry=base+0x4000,images=base+0x5000,animations=base+0x6000,table=base+0x7000,string=base+0x8000,hit=base+0x9000,attack=base+0xa000,childMetadata=base+0xb000,manager=base+0xc000,nodes=base+0xd000
private func u(_ x:Any)->UInt32 {(x as! NSNumber).uint32Value}
private func decode(_ s:String)->[UInt8] {stride(from:0,to:s.count,by:2).map{i in let a=s.index(s.startIndex,offsetBy:i);return UInt8(s[a..<s.index(a,offsetBy:2)],radix:16)!}}
private func args(_ c:ClawCall)->[UInt32] {var c=c;return withUnsafeBytes(of:&c.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(c.argumentCount)))}}
private func call(_ f:UInt32,_ receiver:UInt32=0,_ values:[UInt32]=[])->ClawCall {
 var c=ClawCall();c.function=f;c.receiver=receiver;c.argumentCount=UInt32(values.count)
 withUnsafeMutableBytes(of:&c.arguments){b in let p=b.bindMemory(to:UInt32.self);for i in values.indices{p[i]=values[i]}}
 return c
}
private final class Fixture {
 let heap=ClawTokenHeap();let host:ClawNativeCanonicalHost;let memory:ClawNativeMfcMemory;let p:[String:Any]
 var requests:[[UInt32]]=[],events:[[Any]]=[],calls:[[UInt32]]=[],allocations:[(UInt32,UInt32)]=[]
 var ordinary:[(UInt32,UInt32,ClawTokenHeap.AllocationIdentity)]=[]
 var foreign:[(UInt32,UInt32,ClawTokenHeap.AllocationIdentity)]=[]
 var removed:UInt32?,hook:((ClawCall)->Void)?,shadowOffered=false,allocating=0
 var registryOverride:((String,UInt32)->UInt32)?
 init(_ p:[String:Any],_ hash:String)throws {
  self.p=p
  for b in p["initial"] as! [[String:Any]] {let bytes=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(bytes.count)).update(from:bytes,count:bytes.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x40
  let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:allocation,sceneObjectAllocations:true)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in self.calls.append([c.function,c.receiver]);self.hook?(c)}
  memory.beforeObjectAllocation={ [unowned self] r in
   func word(_ address:UInt32)->UInt32 {r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:Int(address-UInt32(CLAW_STACK_BASE)),as:UInt32.self).littleEndian}}
   self.requests.append([r.function,word(r.context.esp),word(r.context.esp+20),word(r.context.esp+4),r.context.ebx]);self.allocating+=1
   if p["interleave"] as? Bool==true && r.count==0x6c {self.allocateOrdinary()}
   if r.count==u(p["occupied"] ?? 0) {
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
 var nextCandidate:UInt32 {
  (allocations + ordinary.map{($0.0,$0.1)}).map{($0.0+($0.1==0x1b4 ? 512:$0.1)+15) & ~15}.max() ?? allocation
 }
 func allocateOrdinary() {
  for count:UInt32 in [0x1b4,0x174,12] {
   let token=heap.allocate(bytes:count)
   guard token != 0,let bytes=heap.lookupBytes(token,count:count),let identity=heap.allocationIdentity(at:token,count:count) else {continue}
   bytes.update(repeating:0x5a,count:Int(count));ordinary.append((token,count,identity));events.append(["ordinary",token,count])
  }
 }
 func exact(_ token:UInt32,_ count:UInt32)->Bool {
  token & 15==0 && heap.allocationIdentity(at:token,count:count) != nil &&
   heap.lookupBytes(token,count:count+1)==nil && heap.allocationIdentity(at:token,count:count+4)==nil
 }
 var ordinaryIntact:Bool {
  ordinary.allSatisfy{token,count,identity in
   heap.allocationIdentity(at:token,count:count) === identity && exact(token,count) &&
    heap.lookupBytes(token,count:count).map{UnsafeBufferPointer(start:$0,count:Int(count)).allSatisfy{$0==0x5a}}==true
  }
 }
 func service(_ c:ClawCall)->UInt32? {
  if removed==c.function{return nil};let a=args(c)
  if claw_canonical_lookup(c.function) != nil {shadowOffered=true;return 99}
  switch c.function {
  case 0x4f6286:
   guard a.count==2,[registry+16,images+16,animations+16].contains(c.receiver),let out=host.bytes(a[1],count:4) else{return nil}
   var name:[UInt8]=[]
   for i:UInt32 in 0..<64 {guard let b=host.bytes(a[0]+i,count:1) else{return nil};if b[0]==0{break};name.append(b[0])}
   guard let key=String(bytes:name,encoding:.ascii) else{return nil}
   var value:UInt32=c.receiver==registry+16 ? (["LogicHit":hit,"LogicAttack":attack,"SinglePlank":childMetadata][key] ?? 0):0
   if p["resources"] as? Bool==true {
    if c.receiver==images+16 && key=="LEVEL_BREAKPLANK" {value=base+0x18000}
    if c.receiver==animations+16 && key=="LEVEL_BREAKPLANK_IDLE" {value=base+0x1b000}
    if c.receiver==animations+16 && key=="LEVEL_BREAKPLANK_CRUMBLE" {value=base+0x1c000}
   }
   value=registryOverride?(key,value) ?? value
   var word=value.littleEndian;withUnsafeBytes(of:&word){out.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:4)}
   events.append(["registry",c.receiver,key,value]);return value==0 ? 0:1
  case 0x4f51c5:
   // MFC list storage is native platform work; the original executes its
   // append body against the same preallocated node pool for byte comparison.
   guard a.count==1,c.receiver==manager+0x10 else{return nil}
   let node=get(manager+0x20),tail=get(manager+0x18)
   guard node>=nodes,node<nodes+16*12,(node-nodes)%12==0 else{return nil}
   put(manager+0x20,get(node));put(node,0);put(node+4,tail);put(node+8,a[0])
   if tail==0{put(manager+0x14,node)}else{put(tail,node)}
   put(manager+0x18,node);put(manager+0x1c,get(manager+0x1c)+1)
   events.append(["append",c.receiver,a[0]]);return node
  case 0x4f6974:
   guard a==[0],c.receiver>=table,c.receiver<table+256,c.receiver & 3==0,get(c.receiver)==string+12,
         get(string)==1,get(string+4)==0,get(string+8)==0 else{return nil}
   events.append(["buffer",c.receiver,string+12]);return string+12
  default:return memory.service(c)
  }
 }
 func invoke(_ command:UInt32,_ target:UInt32=actor,_ callback:UInt32=0x40f7b0)->ClawNativeCanonicalHost.Completion? {
  put(get(target+0x6c)+0x1c,command)
  return host.withObjectAllocation(provider:memory){host.invoke(call(callback,0,[target]))}
 }
 func initialize()->Bool {invoke(0)?.completed==true}
 func snapshot(_ blocks:[[String:Any]])->[[String:Any]] {
  blocks.map {b in
   let address=u(b["address"]!),n=UInt32((b["data"] as! String).count/2)
   let bytes=heap.lookupBytes(address,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing"
   return ["address":address,"data":bytes]
  }
 }
 func run()->[String:Any] {
  var results:[UInt32]=[],completed:[Bool]=[],snapshots:[[[String:Any]]]=[]
  let expected=p["snapshots"] as! [[[String:Any]]],steps=p["steps"] as! [[NSNumber]]
  for (i,s) in steps.enumerated(){
   let r=invoke(s[2].uint32Value,s[1].uint32Value,s[0].uint32Value);completed.append(r?.completed==true)
   if r?.completed != true{break}
   if let value=r?.eax{results.append(value)}
   if i<5 || i==steps.count-1 {snapshots.append(snapshot(expected[snapshots.count]))}
  }
  return ["label":p["label"]!,"results":results,"completed":completed,"snapshots":snapshots,"events":events,"calls":calls,"requests":requests,"frontier":host.fault.map{$0.address as Any} ?? NSNull(),
   "foreign":snapshot(p["foreign"] as? [[String:Any]] ?? []),
   "physicalIntegrity":ordinaryIntact && allocations.allSatisfy{exact($0.0,$0.1) && memory.ownsObjectAllocation($0.0,count:$0.1)} && foreign.allSatisfy{heap.allocationIdentity(at:$0.0,count:$0.1) === $0.2}]
 }
 func replace(_ token:UInt32,_ count:UInt32) {
  guard let bytes=heap.lookupBytes(token,count:count) else{return}
  let copy=Array(UnsafeBufferPointer(start:bytes,count:Int(count)))
  heap.free(token);heap.storeBytes(token:token,count:count).update(from:copy,count:copy.count)
 }
 func retire()->Bool {
  for (token,_) in allocations.reversed(){if !memory.releaseSceneObject(token){return false}}
  put(state+0x18,0);put(actor+0x70,0);put(actor+0x78,0)
  for b in p["initial"] as! [[String:Any]] where [manager,nodes].contains(u(b["address"]!)) {
   let bytes=decode(b["data"] as! String);heap.lookupBytes(u(b["address"]!),count:UInt32(bytes.count))!.update(from:bytes,count:bytes.count)
  }
  allocations=[];return true
 }
}
@main struct BreakPlankTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]),data=try Data(contentsOf:dir.appendingPathComponent("reference.json"))
  let ref=try JSONSerialization.jsonObject(with:data) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  var output:[[String:Any]]=[];for profile in profiles{output.append(try Fixture(profile,hash).run())}
  var exhausted:[[String:Any]]=[];for profile in ref["exhaustions"] as! [[String:Any]]{exhausted.append(try Fixture(profile,hash).run())}
  var controls:[[String:Any]]=[]
  func record(_ name:String,_ passed:Bool){controls.append(["name":name,"passed":passed])}
  do{let f=try Fixture(p,hash);record("canonical owners are never offered to services",f.initialize() && !f.shadowOffered)}
  do{let f=try Fixture(p,hash);record("provider required",!f.host.invoke(call(0x40f7b0,0,[actor])).completed)}
  for callback:UInt32 in [0,0x488e30,0x40f7b1]{let f=try Fixture(p,hash);f.put(state+0x10,callback);record("wrong root callback \(callback)",!f.initialize() && f.heap.lookupBytes(allocation,count:1)==nil)}
  do{let f=try Fixture(p,hash);let other=try Fixture(p,hash);record("foreign provider rejected",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(call(0x40f7b0,0,[actor]))}==nil)}
  for removed:UInt32 in [0x4f6286,0x4f6974]{let f=try Fixture(p,hash);if removed==0x4f6974{_=f.initialize()};f.removed=removed;record("missing service \(removed)",f.invoke(removed==0x4f6286 ? 0:7)?.completed != true)}
  for count:UInt32 in [0xa4,0x6c,0x1b4,0x174]{
   for offset:UInt32 in [4,20]{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={r in if r.count==count{f.host.bytes(r.context.esp+offset,count:4)!.update(repeating:0,count:4)}};record("allocation \(count) size/continuation \(offset)",!f.initialize())}
   do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={r in if r.count==count{nested=f.host.invoke(call(0x40f7b0,0,[actor]))}};record("allocation \(count) reentry",!f.initialize() && nested?.completed==false)}
   do{let f=try Fixture(p,hash);f.memory.afterService={fn,a,t in if fn==0x4a48e0 && a[0]==count && t != 0{f.replace(t,count)}};record("allocation \(count) identity replacement",!f.initialize())}
  }
  for (metadata,correct) in [(hit,UInt32(0x4dc830)),(attack,UInt32(0x4dc850)),(childMetadata,UInt32(0x488e30))]{
   for wrong:UInt32 in [0,0x491fa0,correct+1]{let f=try Fixture(p,hash);f.put(metadata+16,wrong);record("wrong metadata callback \(metadata) \(wrong)",!f.initialize())}
   do{let f=try Fixture(p,hash);f.registryOverride={_,value in value==metadata ? metadata+0x800:value};record("foreign metadata \(metadata)",!f.initialize())}
  }
  for (name,c) in [("standalone allocation",call(0x4f63ec,0,[0xa4])),("standalone receiver stdcall",call(0x4c9e30,allocation,[0])),("standalone child allocation",call(0x4f63ec,0,[0x6c]))]{let f=try Fixture(p,hash);record(name,f.host.withObjectAllocation(provider:f.memory){f.host.invoke(c)}?.completed != true)}
  for (name,bad) in [("wrong size",call(0x4f63ec,0,[0x80])),("wrong allocation receiver",call(0x4f63ec,actor,[0xa4])),("wrong constructor actor",call(0x40f870,allocation,[actor+4])),("wrong constructor helper",call(0x40f870,allocation+4,[actor]))]{
   let f=try Fixture(p,hash);f.hook={c in if c.function==(name.contains("constructor") ? 0x40f870:0x4f63ec){f.hook=nil;_=f.host.callNativeDependency(bad)}};record(name,!f.initialize())
  }
  for (name,token,count) in [("actor",actor,UInt32(0x400)),("state",state,0x400),("helper",allocation,0xa4),("parent vtable",UInt32(0x50b6ec),0x24),("child vtable",UInt32(0x50f664),0x24)]{
   let f=try Fixture(p,hash);let ready=f.initialize();f.replace(token,count);record("retained \(name) identity",ready && f.invoke(7)?.completed != true)
  }
  for (address,value) in [(allocation,UInt32(0x50f664)),(UInt32(0x50b6f0),UInt32(0x4c96b0)),(UInt32(0x50b6f4),UInt32(0x4890f0)),(UInt32(0x50f66c),UInt32(0x40fb30))]{let f=try Fixture(p,hash);let ready=f.initialize();f.put(address,value);record("cross-owner vtable \(address)",ready && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash);let ready=f.initialize();let child=f.get(allocation+0xa0);f.put(state+0x18,child);record("cross-owner helper substitution",ready && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash);let ready=f.initialize();record("repeated initialization rejects leak",ready && !f.initialize())}
  do{let f=try Fixture(profiles[1],hash);let ready=f.initialize();let issued=f.allocations;let retired=ready && f.retire();let recreated=retired && f.initialize();record("same Memory retires and recreates whole chain",recreated && issued.allSatisfy{f.heap.lookupBytes($0.0,count:1)==nil} && f.get(state+0x18) != allocation && f.allocations.allSatisfy{f.memory.ownsObjectAllocation($0.0,count:$0.1)})}
  do{let f=try Fixture(p,hash);let ready=f.initialize();let child=f.get(allocation+0xa0);let retired=ready && f.memory.releaseSceneObject(child);record("retired child storage rejected",retired && f.invoke(7)?.completed != true)}
  do{let f=try Fixture(p,hash);let ready=f.initialize();let retired=ready && f.memory.releaseSceneObject(allocation);record("retired helper double free rejected",retired && !f.memory.releaseSceneObject(allocation))}
  do{let f=try Fixture(p,hash);_=f.heap.storeBytes(token:allocation,count:0xa4);record("foreign helper retirement rejected",!f.memory.releaseSceneObject(allocation) && f.heap.lookupBytes(allocation,count:0xa4) != nil)}
  do{let f=try Fixture(p,hash);let ready=f.initialize();var attempted=false,released=false;f.hook={c in if c.function==0x4f6974{f.hook=nil;attempted=true;released=f.memory.releaseSceneObject(allocation)}};let completion=f.invoke(7);record("active lifecycle cannot retire its helper",ready && attempted && !released && f.heap.lookupBytes(allocation,count:0xa4) != nil && completion?.completed != true)}
  for parentReplacement in [false,true] {
   let f=try Fixture(profiles[1],hash),ready=f.initialize()
   let label=parentReplacement ? "child rejects retired parent replaced by identical foreign bytes":"child rejects retired sibling replaced by identical foreign bytes"
   if !ready {record(label,false);continue}
   let head=f.get(allocation+0xa0),target=f.get(head+0xc)
   let token=parentReplacement ? allocation:f.get(head+0x50),count:UInt32=parentReplacement ? 0xa4:0x6c
   let bytes=Array(UnsafeBufferPointer(start:f.heap.lookupBytes(token,count:count)!,count:Int(count)))
   let retired=f.memory.releaseSceneObject(token)
   if retired {f.heap.storeBytes(token:token,count:count).update(from:bytes,count:bytes.count)}
   record(label,retired && !f.memory.ownsObjectAllocation(token,count:count) && f.invoke(7,target,0x488e30)?.completed != true)
  }
  do {
   let f=try Fixture(p,hash),ready=f.initialize()
   let first=f.allocations.map{($0.0,$0.1,f.heap.allocationIdentity(at:$0.0,count:$0.1)!)}
   f.allocateOrdinary()
   let secondActor=f.ordinary[0].0,secondState=f.ordinary[1].0
   for (source,target,count) in [(actor,secondActor,UInt32(0x1b4)),(state,secondState,UInt32(0x174))] {
    let original=(p["initial"] as! [[String:Any]]).first{u($0["address"]!)==source}!
    let bytes=Array(decode(original["data"] as! String).prefix(Int(count)))
    f.heap.lookupBytes(target,count:count)!.update(from:bytes,count:bytes.count)
   }
   f.put(secondActor+0x6c,secondState)
   let second=f.invoke(0,secondActor)?.completed==true
   record("second live parent after ordinary actor logic and list allocations",ready && second && f.get(secondState+0x18)>f.ordinary[2].0 && f.get(state+0x18)==allocation && f.invoke(7)?.completed==true && f.invoke(7,secondActor)?.completed==true && first.allSatisfy{f.heap.allocationIdentity(at:$0.0,count:$0.1) === $0.2} && f.ordinary.allSatisfy{f.heap.allocationIdentity(at:$0.0,count:$0.1) === $0.2 && f.exact($0.0,$0.1)} && f.get(f.ordinary[2].0)==0x5a5a5a5a && f.allocations.allSatisfy{f.exact($0.0,$0.1) && f.memory.ownsObjectAllocation($0.0,count:$0.1)})
  }
  do {
   let f=try Fixture(profiles[1],hash),ready=f.initialize(),issued=f.allocations
   let retired=ready && f.retire()
   f.allocateOrdinary()
   let recreated=retired && f.initialize()
   record("destroy recreate after ordinary actor logic and list allocations",recreated && f.ordinary.count==3 && f.ordinaryIntact && f.get(state+0x18)>f.ordinary[2].0 && issued.allSatisfy{f.heap.lookupBytes($0.0,count:1)==nil} && f.allocations.allSatisfy{f.exact($0.0,$0.1) && f.memory.ownsObjectAllocation($0.0,count:$0.1)})
   if recreated {
    f.put(state+0x18,allocation)
    record("recreated parent rejects stale helper",f.invoke(7)?.completed != true)
   } else {record("recreated parent rejects stale helper",false)}
  }
  do {
   let f=try Fixture(p,hash),ready=f.initialize(),retired=ready && f.retire()
   f.allocateOrdinary();let recreated=retired && f.initialize()
   f.heap.storeBytes(token:allocation,count:0xa4).update(repeating:0x37,count:0xa4)
   let replacement=f.heap.allocationIdentity(at:allocation,count:0xa4)
   record("retired helper claim cannot free foreign replacement after recreate",recreated && !f.memory.releaseSceneObject(allocation) && f.heap.allocationIdentity(at:allocation,count:0xa4) === replacement && f.get(allocation)==0x37373737)
  }
  let result:[String:Any]=["version":1,"profiles":output,"exhaustions":exhausted,"controls":controls]
  try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"))
  print("native profiles \(output.count), controls \(controls.count)")
 }
}
