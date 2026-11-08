import Foundation
private func u(_ x:Any)->UInt32 {(x as! NSNumber).uint32Value}
private func decode(_ s:String)->[UInt8] {let b=Array(s.utf8);func n(_ c:UInt8)->UInt8 {c>=97 ? c-87:c-48};return stride(from:0,to:b.count,by:2).map{n(b[$0])*16+n(b[$0+1])}}
private func args(_ c:ClawCall)->[UInt32] {var c=c;return withUnsafeBytes(of:&c.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(c.argumentCount)))}}
private func fp(_ value:[Any])->ClawX87State {
 var s=ClawX87State();s.size=UInt32(MemoryLayout<ClawX87State>.size);s.version=1;s.control=u(value[0]);s.status=u(value[1]);let slots=value[2] as! [[NSNumber]];s.count=UInt32(slots.count)
 withUnsafeMutableBytes(of:&s.slots){b in let q=b.bindMemory(to:ClawX87Value.self);for i in slots.indices{q[i].significand=slots[i][0].uint64Value;q[i].signExponent=slots[i][1].uint32Value}}
 return s
}
private func fpJSON(_ s:ClawX87State)->[Any] {var s=s;let slots=withUnsafeBytes(of:&s.slots){b in Array(b.bindMemory(to:ClawX87Value.self).prefix(Int(s.count))).map{[NSNumber(value:$0.significand),NSNumber(value:$0.signExponent)]}};return[s.control,s.status,slots]}
private final class Fixture {
 let heap=ClawTokenHeap();let host:ClawNativeCanonicalHost;let memory:ClawNativeMfcMemory;let p:[String:Any]
 var source:[[String:Any]]=[];var sourceOutputs:[[String:Any]]=[];var requests:[[UInt32]]=[];var allocationWitness=false;var events:[[Any]]=[];var calls:[[Any]]=[];var missing:UInt32?;var inject:((ClawCall)->Void)?
 init(_ p:[String:Any],_ hash:String)throws {
  self.p=p
  for b in p["initial"] as! [[String:Any]] {let d=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(d.count)).update(from:d,count:d.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
  let storage=heap;let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().map{k in(k,storage.lookup(k,words:1)![0])})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:u(p["allocation_base"]!),sceneObjectAllocations:true)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in
   self.calls.append([c.function,c.receiver,args(c)])
   if c.function==0x438100,let pointer=c.sourceContext {let r=pointer.pointee;let frame=(0..<4).map{self.get(r.esp+UInt32($0*4))};self.source.append(["eax":r.eax,"edx":r.edx,"ebx":r.ebx,"esi":r.esi,"edi":r.edi,"ebp":r.ebp,"ecx":r.ecx,"eflags":r.eflags,"frame":frame])}
   self.inject?(c)
  }
  host.townSourceObserver={ [unowned self] function,r in if function==0x438100 {self.sourceOutputs.append(["eax":r.eax,"ebx":r.ebx,"esi":r.esi,"edi":r.edi,"ebp":r.ebp])}}
  memory.beforeObjectAllocation={ [unowned self] r in let offset=Int(r.context.esp-UInt32(CLAW_STACK_BASE)+0x14);let caller=r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)};self.requests.append([r.root,r.count,r.returnPC,caller])}

  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]])}}
 }
 var actor:UInt32 {u(p["actor"]!)};var state:UInt32 {u(p["state"]!)}
 func get(_ a:UInt32)->UInt32 {UnsafeRawPointer(host.bytes(a,count:4)!).loadUnaligned(as:UInt32.self).littleEndian}
 func put(_ a:UInt32,_ v:UInt32){heap.lookup(a,words:1)![0]=v}
 func string(_ a:UInt32)->String? {var bytes:[UInt8]=[];for i:UInt32 in 0..<256 {guard let p=host.bytes(a+i,count:1) else{return nil};if p[0]==0{return String(bytes:bytes,encoding:.ascii)};bytes.append(p[0])};return nil}
 func service(_ c:ClawCall)->UInt32? {
  let a=args(c);var f=c.function
  for slot:UInt32 in [0x546d5c,0x546cdc,0x5469e8,0x546cd4] {if get(slot)==f {f=slot}}
  if missing==f{return nil}
  switch f {
  case 0x4f6286:
   guard a.count==2,let name=string(a[0]),let out=host.bytes(a[1],count:4) else{return nil}
   let found=(p["bindings"] as! [[Any]]).first{u($0[0])==c.receiver && $0[1] as! String==name}
   guard found != nil || c.receiver==u(p["audio_dictionary"]!) else{return nil}
   let value=found.map{u($0[2])} ?? 0
   out.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee=value};events.append(["lookup",c.receiver,name,value]);return value==0 ? 0:1
  case 0x4f6974:
   guard a.count==1,a[0]==0,let pointer=heap.lookup(c.receiver,words:1)?[0],pointer>=12,let header=heap.lookup(pointer-12,words:3),Int32(bitPattern:header[0])<=1,header[1]<=header[2],heap.lookupBytes(pointer,count:header[1]+1) != nil else{return nil};return pointer
  case 0x546d5c,0x546cdc:
   guard a.count==(f==0x546d5c ? 5:1),let out=host.bytes(a[0],count:16) else{return nil}
   for i in 0..<4 {var value=(f==0x546d5c ? a[i+1]:0).littleEndian;withUnsafeBytes(of:&value){UnsafeMutableRawPointer(out.advanced(by:i*4)).copyMemory(from:$0.baseAddress!,byteCount:4)}};if f==0x546d5c {events.append(["rectangle",a[0],a[1],a[2],a[3],a[4]])}else{events.append(["empty-rectangle",a[0]])};return 1
  case 0x5469e8:
   guard a.count==1,let out=host.bytes(a[0],count:4) else{return nil};return out.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee &-= 1;return $0.pointee}
  case 0x546cd4:
   guard a.count==3,let rect=host.bytes(a[0],count:16) else{return nil};let v=(0..<4).map{UnsafeRawPointer(rect.advanced(by:$0*4)).loadUnaligned(as:Int32.self)};let x=Int32(bitPattern:a[1]),y=Int32(bitPattern:a[2]);return v[0]<=x && x<v[2] && v[1]<=y && y<v[3] ? 1:0
  case 0x4a3810:
   guard c.receiver==0,a.count==2 else{return nil}
   for i:UInt32 in 0..<4096 {guard let lhs=host.bytes(a[0]+i,count:1),let rhs=host.bytes(a[1]+i,count:1) else{return nil};if lhs[0] != rhs[0] {return UInt32(bitPattern:Int32(lhs[0])-Int32(rhs[0]))};if lhs[0]==0{return 0}};return nil
  case 0x4a5290:
   guard c.receiver==0,a.count==3,a[2]<=0x400000,let src=host.bytes(a[1],count:a[2]),let dst=host.bytes(a[0],count:a[2]) else{return nil}
   let copied=Array(UnsafeBufferPointer(start:src,count:Int(a[2])));dst.update(from:copied,count:copied.count);return a[0]
  case 0x4b0d60:
   guard c.receiver==0,a.count==1,a[0]<=255 else{return nil};return a[0]==32 || (9...13).contains(a[0]) ? 8:0
  case 0x4b0d30:
   guard c.receiver==0,a.count==1,a[0]<=255 else{return nil};return (48...57).contains(a[0]) ? 4:0
  case 0x4a3050:events.append(["rand",99]);return 99
  default:return nil
  }
 }
 func call()->ClawCall {var c=ClawCall();c.function=0x4379d0;c.argumentCount=1;c.arguments.0=actor;return c}
 func step(_ e:[String:Any],_ incoming:ClawX87State)->([String:Any],ClawX87State) {
  let retiring=e["command"] as? String=="retire";put(state+0x1c,retiring ? 0:u(e["command"]!));put(0x5430c4,17);put(0x537210,1000);events=[];calls=[];source=[];sourceOutputs=[]
  var completed=false;var outgoing=incoming
  if retiring {if let r=host.withObjectX87Environment(incoming,body:{host.retireCutThroat(actor:actor,provider:memory)}) {completed=r.0;outgoing=r.1}}
  else {_=host.withObjectAllocation(provider:memory){if let r=host.withObjectX87Environment(incoming,body:{host.invoke(call())}) {completed=r.0.completed;outgoing=r.1}}}
  let final=(e["final"] as! [[String:Any]]).map {b->[String:Any] in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);let text=heap.lookupBytes(a,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? (0..<n).map{offset in host.bytes(a+offset,count:1).map{String(format:"%02x",$0[0])} ?? "??"}.joined();return["address":a,"data":text]}
  return(["command":e["command"]!,"completed":completed,"fault":host.fault.map{String(describing:$0)} ?? "scope refused","incoming":fpJSON(incoming),"outgoing":fpJSON(outgoing),"events":events,"calls":calls,"final":final,"source":source,"source_outputs":sourceOutputs,"retirements":memory.sceneObjectRetirements.map{["address":$0.0,"data":$0.1.map{String(format:"%02x",$0)}.joined()]}],outgoing)
 }
}
@main struct CutThroatSceneTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]);let ref=try JSONSerialization.jsonObject(with:Data(contentsOf:dir.appendingPathComponent("reference.json"))) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=ref["fixture"] as! [String:Any]
  var output:[[String:Any]]=[];var controls:[[String:Any]]=[]
  func record(_ n:String,_ ok:Bool){controls.append(["name":n,"passed":ok])}
  for profile in profiles {
   let f=try Fixture(p,hash);var state=fp(profile["incoming"] as! [Any]),steps:[[String:Any]]=[]
   for e in profile["steps"] as! [[String:Any]] {let (row,next)=f.step(e,state);steps.append(row);state=next;if row["completed"] as? Bool != true {print("Failed command",e["command"]!,row["fault"]!);break}}
   output.append(["label":profile["label"]!,"steps":steps,"requests":f.requests])
  }
  try JSONSerialization.data(withJSONObject:["profiles":output],options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native-positive.json"))
  let referenceSteps=profiles[0]["steps"] as! [[String:Any]],constructor=referenceSteps[0]
  func construct(_ f:Fixture)->Bool {f.step(constructor,fp(profiles[0]["incoming"] as! [Any])).0["completed"] as? Bool==true}
  func lifecycle(_ f:Fixture,_ count:Int = 5)->Bool {
   var state=fp(profiles[0]["incoming"] as! [Any])
   for e in referenceSteps.prefix(count) {let(row,next)=f.step(e,state);state=next;if row["completed"] as? Bool != true {return false}}
   return true
  }
  record("v1.0 profile selected",ProcessInfo.processInfo.environment["CLAW_LIVES_BOSS_PROFILE"]=="claw-v1.0")
  do{let f=try Fixture(p,hash);record("provider required",!f.host.invoke(f.call()).completed && f.heap.lookupBytes(u(p["allocation_base"]!),count:1)==nil)}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);record("foreign provider rejected",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(f.call())}==nil)}
  do{let f=try Fixture(p,hash);f.put(f.state+0x10,0x4379d1);record("wrong callback rejected",!construct(f))}
  do{let f=try Fixture(p,hash);f.put(f.actor+0x6c,UInt32.max);record("wrong actor rejected",!construct(f))}
  for offset:UInt32 in [0,4,8,12,16,28,32,36] {
   let f=try Fixture(p,hash);f.put(0x50c934+offset,f.get(0x50c934+offset)^4);record("wrong vtable slot \(offset) rejected",!construct(f))
  }
  for service:UInt32 in [0x4f6286,0x546d5c,0x546cdc] {let f=try Fixture(p,hash);f.missing=service;record("missing service \(service) rejected",!construct(f))}
  do{let f=try Fixture(p,hash);f.memory.failAllocation={$0==0x4a48e0};record("allocation exhaustion preserved",!construct(f) && f.heap.lookupBytes(u(p["allocation_base"]!),count:1)==nil)}
  for attempt in [2,3] {
   let f=try Fixture(p,hash);f.memory.failAllocation={slot in slot==0x4a48e0 && f.requests.count==attempt};let failed = !construct(f),base=u(p["allocation_base"]!),target=base+(attempt==2 ? 0x480:0x600)
   record("secondary allocation exhaustion \(attempt) preserves earlier owners",failed && f.requests.count==attempt && f.memory.ownsObjectAllocation(base,count:0x480) && (attempt==2 || f.memory.ownsObjectAllocation(base+0x480,count:0x174)) && f.heap.lookupBytes(target,count:1)==nil)
  }
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(f.call())};record("physical reentry rejected",!construct(f) && nested?.completed==false)}
  for mode in ["size","receiver","continuation"] {
   let f=try Fixture(p,hash);var injected=false;f.inject={c in if !injected && c.function==(mode=="size" ? 0x4f63ec:0x437a90){injected=true;var wrong=c;if mode=="size"{wrong.arguments.0=0x47f};if mode=="receiver"{wrong.receiver &+= 4};if mode=="continuation"{wrong.sourceReturnPC=0x437a29};_=f.host.callNativeDependency(wrong)}};record("wrong \(mode) request rejected",!construct(f) && injected)
  }
  do{let f=try Fixture(p,hash);let ok=construct(f),helper=f.get(f.state+0x18);f.heap.free(helper);_=f.heap.storeBytes(token:helper,count:0x480);record("replacement helper rejected",ok && !lifecycle(f))}
  do{let f=try Fixture(p,hash);let ok=construct(f);f.put(f.state+0x18,0x69c00000);record("foreign helper rejected",ok && !lifecycle(f))}
  do{let f=try Fixture(p,hash);let ok=construct(f),saved=Array(UnsafeBufferPointer(start:f.heap.lookupBytes(f.actor,count:0x1b4)!,count:0x1b4));f.heap.free(f.actor);f.heap.storeBytes(token:f.actor,count:0x1b4).update(from:saved,count:saved.count);record("replacement actor identity rejected",ok && !lifecycle(f))}
  for offset:UInt32 in [4,8,12,16] {let f=try Fixture(p,hash),metadata=u(((p["resource_proof"] as! [String:Any])["logic"] as! [String:Any])["LogicHit"]!);f.put(metadata+offset,f.get(metadata+offset)^4);record("wrong logic metadata \(offset) rejected",!construct(f))}
  do{let f=try Fixture(p,hash);let ok=construct(f);record("retained live helper rejects second construction",ok && !construct(f))}
  for mode in ["eax","frame","continuation","receiver"] {
   let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x438100,let cpu=c.sourceContext {changed=true;if mode=="eax"{cpu.pointee.eax ^= 4};if mode=="frame",let bytes=f.host.bytes(cpu.pointee.esp+8,count:4){bytes.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}};if mode=="continuation",let bytes=f.host.bytes(cpu.pointee.esp,count:4){bytes.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}};if mode=="receiver"{cpu.pointee.ecx &+= 4}}};record("wrong source \(mode) rejected",!lifecycle(f) && changed)
  }
  for mode in ["cw","count","version","reserved","status","slot"] {
   let f=try Fixture(p,hash);var state=fp(profiles[0]["incoming"] as! [Any]);if mode=="cw"{state.control=0};if mode=="count"{state.count=9};if mode=="version"{state.version=2};if mode=="reserved"{state.reserved0=1};if mode=="status"{state.status=0x10000};if mode=="slot"{state.slots.7.significand=1};record("malformed x87 \(mode) rejected",f.host.withObjectX87Environment(state,body:{f.host.invoke(f.call())})==nil)
  }
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);let ok=lifecycle(f);record("foreign retirement owner rejected",ok && !f.host.retireCutThroat(actor:f.actor,provider:other.memory))}
  do{let f=try Fixture(p,hash);var call=ClawCall();call.function=0x438010;call.receiver=u(p["allocation_base"]!);call.argumentCount=1;call.arguments.0=1;record("unbound destructor rejected",!f.host.invoke(call).completed)}
  for service:UInt32 in [0x4f6974,0x4a3810] {let f=try Fixture(p,hash);f.missing=service;record("missing lifecycle service \(service) rejected",!lifecycle(f,service==0x4a3810 ? 6:5))}
  for function:UInt32 in [0x4384f0,0x4386d0] {let f=try Fixture(p,hash);var call=ClawCall();call.function=function;call.receiver=u(p["allocation_base"]!);record("unbound state handler \(function) rejected",!f.host.invoke(call).completed)}
  do{let f=try Fixture(p,hash);var call=ClawCall();call.function=0x438100;call.receiver=u(p["allocation_base"]!);call.argumentCount=1;call.arguments.0=2000;record("source entry outside lifecycle rejected",!f.host.invoke(call).completed)}
  try JSONSerialization.data(withJSONObject:["profiles":output,"controls":controls],options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"));print("native profiles",output.count)
 }
}
