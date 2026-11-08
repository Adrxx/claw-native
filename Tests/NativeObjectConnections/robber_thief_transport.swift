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
 var retirementBytes:String?;var freed:[UInt32]=[];var allocationWitness=false;var events:[[Any]]=[];var calls:[[Any]]=[];var missing:UInt32?;var inject:((ClawCall)->Void)?
 init(_ p:[String:Any],_ hash:String)throws {
  self.p=p
  for b in p["initial"] as! [[String:Any]] {let d=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(d.count)).update(from:d,count:d.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
  let storage=heap;let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().map{k in(k,storage.lookup(k,words:1)![0])})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:0x61000000,sceneObjectAllocations:p["scene"] as? Bool ?? false)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in self.calls.append([c.function,c.receiver,args(c)]);self.inject?(c)
   if c.function==0x4f6428 {let token=c.arguments.0;if token==self.heap.lookup(self.state+0x18,words:1)?[0] {self.retirementBytes=self.hex(token,0x478)};self.freed.append(token);self.events.append(["free",token])}}
  memory.beforeObjectAllocation={ [unowned self] r in if r.root != 0x485270 {return};let offset=Int(r.context.esp-UInt32(CLAW_STACK_BASE)+0x14);self.allocationWitness=r.root==0x485270 && r.count==0x478 && r.returnPC==0x4f63ff && r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)}==0x4852ad}
  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]])}}
 }
 var actor:UInt32 {u(p["actor"]!)};var state:UInt32 {u(p["state"]!)}
 func get(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)![0]}
 func put(_ a:UInt32,_ v:UInt32){heap.lookup(a,words:1)![0]=v}
 func string(_ a:UInt32)->String? {var bytes:[UInt8]=[];for i:UInt32 in 0..<256 {guard let p=host.bytes(a+i,count:1) else{return nil};if p[0]==0{return String(bytes:bytes,encoding:.ascii)};bytes.append(p[0])};return nil}
 func service(_ c:ClawCall)->UInt32? {
  let a=args(c);var f=c.function
  for slot:UInt32 in [0x546d5c,0x546cdc,0x5469e8] {if get(slot)==f {f=slot}}
  if missing==f{return nil}
  switch f {
  case 0x4f6974:
   guard a==[0],let row=heap.lookup(c.receiver,words:1),let value=heap.lookupBytes(row[0],count:8),String(bytes:UnsafeBufferPointer(start:value,count:7),encoding:.ascii)=="LS_IDLE" else{return nil};return row[0]
  case 0x4f6286:
   guard a.count==2,let name=string(a[0]),let out=host.bytes(a[1],count:4),let map=heap.lookup(c.receiver+4,words:2) else{return nil}
   let buckets=map[0],count=map[1];guard count>0,count<4096 else{return nil};var value:UInt32=0
   if buckets != 0 {for i in 0..<count {guard let slot=heap.lookup(buckets+i*4,words:1) else{return nil};var node=slot[0],seen:Set<UInt32>=[]
    while node != 0 {guard seen.insert(node).inserted,let words=heap.lookup(node,words:4),let key=string(words[2]) else{return nil};if key==name {value=words[3];break};node=words[0]}
    if value != 0 {break}
   }}
   out.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee=value};events.append(["lookup",c.receiver,name,value]);return value==0 ? 0:1
  case 0x546d5c,0x546cdc:
   guard a.count==(f==0x546d5c ? 5:1),let out=host.bytes(a[0],count:16) else{return nil}
   for i in 0..<4 {var value=(f==0x546d5c ? a[i+1]:0).littleEndian;withUnsafeBytes(of:&value){UnsafeMutableRawPointer(out.advanced(by:i*4)).copyMemory(from:$0.baseAddress!,byteCount:4)}};if f==0x546d5c {events.append(["rectangle",a[0],a[1],a[2],a[3],a[4]])}else{events.append(["empty-rectangle",a[0]])};return 1
  case 0x5469e8:
   guard a.count==1,let out=host.bytes(a[0],count:4) else{return nil};return out.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee &-= 1;return $0.pointee}
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
 func call()->ClawCall {var c=ClawCall();c.function=0x485270;c.argumentCount=1;c.arguments.0=actor;return c}
 func hex(_ token:UInt32,_ n:UInt32)->String {heap.lookupBytes(token,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing"}
 func snapshot()->[[String:Any]] {(p["final"] as! [[String:Any]]).map{b in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);return["address":a,"data":hex(a,n)]}}
 func step(_ command:UInt32,_ initial:ClawX87State)->(Bool,ClawX87State) {
  put(state+0x1c,command)
  if command==2000 {put(actor+0xcc,7);put(actor+8,get(actor+8)|0x10)}
  var completion:ClawNativeCanonicalHost.Completion?;var outgoing=initial
  _=host.withObjectAllocation(provider:memory){if let r=host.withObjectX87Environment(outgoing,body:{host.invoke(call())}) {completion=r.0;outgoing=r.1}}
  return(completion?.completed==true,outgoing)
 }
 func run()->[String:Any] {
  let lifecycle=p["lifecycle"] as? Bool ?? false
  var completed=true,outgoing=fp(p["incoming"] as! [Any]),steps:[[String:Any]]=[]
  for command:UInt32 in (lifecycle ? [0,1000,29,30,2000]:[0]) {
   let before=(events.count,calls.count),result=step(command,outgoing);outgoing=result.1;completed = completed && result.0
   steps.append(["command":command,"outgoing":fpJSON(outgoing),"events":Array(events.dropFirst(before.0)),"calls":Array(calls.dropFirst(before.1)),"final":snapshot()])
   if !result.0 {break}
  }
  let final=snapshot();var retirement:[String:Any]=[:]
  if lifecycle && completed {
   let helper=get(state+0x18),before=(events.count,calls.count)
   let members=p["members"] as! [[String:Any]]
   for member in members {let bytes=decode(member["data"] as! String),expected=u(member["address"]!);var allocation=ClawCall();allocation.function=0x546aa8;allocation.stackPointer=UInt32(CLAW_STACK_TOP);allocation.argumentCount=2;allocation.arguments.0=0;allocation.arguments.1=UInt32(bytes.count)
    let token=memory.service(allocation);if token != expected {completed=false;break};heap.lookupBytes(expected,count:UInt32(bytes.count))!.update(from:bytes,count:bytes.count)
   }
   if completed {put(helper+0x1a4,u(members[0]["address"]!)+12);put(helper+0x1a8,u(members[1]["address"]!)+12);put(helper+0x2fc,64);put(helper+0x300,u(members[2]["address"]!))}
   let ok=host.retireRobberThief(actor:actor,provider:memory,retireSecondary:true);completed = completed && ok
   retirement=["helper":helper,"bytes":retirementBytes ?? "missing","events":Array(events.dropFirst(before.0)),"calls":Array(calls.dropFirst(before.1)),"freed":memory.sceneObjectRetirements.map{$0.token},"freedBytes":memory.sceneObjectRetirements.map{["address":$0.token,"data":$0.bytes.map{String(format:"%02x",$0)}.joined()] as [String:Any]}]
  }
  return["label":p["label"]!,"allocation_witness":allocationWitness,"completed":completed,"fault":host.fault.map{String(describing:$0)} ?? "scope refused","outgoing":fpJSON(outgoing),"events":events,"calls":calls,"final":final,"steps":steps,"retirement":retirement]
 }

}
@main struct RobberThiefTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]);let ref=try JSONSerialization.jsonObject(with:Data(contentsOf:dir.appendingPathComponent("reference.json"))) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  var output:[[String:Any]]=[];for p in profiles{output.append(try Fixture(p,hash).run())}
  var controls:[[String:Any]]=[]
  func record(_ n:String,_ ok:Bool){controls.append(["name":n,"passed":ok])}
  func failed(_ f:Fixture)->Bool {!f.step(0,fp(f.p["incoming"] as! [Any])).0}
  do{let f=try Fixture(p,hash);record("provider required",!f.host.invoke(f.call()).completed && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);record("foreign provider rejected",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(f.call())}==nil)}
  do{let f=try Fixture(p,hash);f.put(f.state+0x10,0x485271);record("wrong callback rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.put(f.actor+0x6c,UInt32.max);record("wrong actor state rejected",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x4f6286;record("missing registry fails",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x546d5c;record("missing rectangle fails",failed(f))}
  do{let f=try Fixture(p,hash);f.memory.failAllocation={$0==0x4a48e0};record("allocation exhaustion preserved",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);let bytes=f.heap.storeBytes(token:0x61000000,count:0x478);bytes.update(repeating:0xa7,count:0x478);record("occupied allocation preserved",failed(f) && UnsafeBufferPointer(start:bytes,count:0x478).allSatisfy{$0==0xa7})}
  do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={_ in f.heap.free(0x10000000);_=f.heap.storeBytes(token:0x10000000,count:0x10000)};record("actor identity replacement rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.memory.afterService={slot,_,token in if slot==0x4a48e0 && token != 0 {f.heap.free(token);_=f.heap.storeBytes(token:token,count:0x478)}};record("allocation identity replacement rejected",failed(f))}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(f.call())};record("physical service reentry rejected",failed(f) && nested?.completed==false)}
  do{let f=try Fixture(p,hash);f.put(f.state+0x18,f.actor);record("foreign existing helper rejected before allocation",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  for offset:UInt32 in [0,4,8,12,16,28,32,72] {
   let f=try Fixture(p,hash);f.put(0x50f49c+offset,f.get(0x50f49c+offset)^4)
   record("wrong vtable slot \(offset) rejected before allocation",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  for mode in ["cut-size","cut-constructor","cut-vtable","base-x87"] {
   let f=try Fixture(p,hash);var injected=false
   f.inject={c in
    if !injected && c.function==(mode=="cut-size" ? 0x4f63ec:mode=="cut-vtable" ? 0x405000:mode=="base-x87" ? 0x44c000:0x485330) {
     injected=true;var wrong=c
     if mode=="cut-vtable" {f.put(0x61000000,0x50c934)}
     else if mode=="base-x87" {c.x87State?.pointee.reserved0=1}
     else {if mode=="cut-size" {wrong.arguments.0=0x480}else{wrong.function=0x437a90};_=f.host.callNativeDependency(wrong)}
    }
   }
   record("cross-owner or malformed \(mode) rejected",failed(f) && injected)
  }
  for delta:UInt32 in [0,4,0x14,0x18] {
   let f=try Fixture(p,hash)
   f.memory.beforeObjectAllocation={r in if let bytes=f.host.bytes(r.context.esp+delta,count:4) {bytes.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}}}
   record("source allocation stack word \(delta) tampering rejected before allocation",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  for mode in ["size","receiver","actor","continuation"] {
   let f=try Fixture(p,hash);var injected=false
   f.inject={c in if !injected && c.function==(mode=="size" ? 0x4f63ec:0x485330) {injected=true;var wrong=c
    if mode=="size" {wrong.arguments.0=0x47f};if mode=="receiver" {wrong.receiver &+= 4};if mode=="actor" {wrong.arguments.0 &+= 4};if mode=="continuation" {wrong.sourceReturnPC=0x4852c9}
    _=f.host.callNativeDependency(wrong)
   }};record("reentrant wrong \(mode) request rejected",failed(f) && injected)
  }
  for offset:UInt32 in [8,0x0c,0x10] {
   let f=try Fixture(p,hash);var corrupted=false
   f.inject={c in if !corrupted && c.function==0x4c7970 {corrupted=true;f.put(0x61000000+offset,f.get(0x61000000+offset)+4)}}
   record("post-base helper link \(offset) corruption rejected",failed(f) && corrupted)
  }
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x4c7970 {changed=true;f.put(f.state+0x1c,0)}};record("construction command mutation rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x405000 {changed=true;f.put(0x61000000,0x50f4a0)}};record("initial vtable replacement rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);let first = !failed(f);f.put(f.state+0x1c,0);record("stale live helper rejected",first && failed(f))}
  for mode in ["size","receiver","actor","continuation"] {
   let f=try Fixture(p,hash);var c=ClawCall();c.function=mode=="size" ? 0x4f63ec:0x485330;c.argumentCount=1;c.arguments.0=mode=="size" ? 0x47f:f.actor;c.receiver=mode=="size" ? 0:0x61000004;if mode=="actor" {c.arguments.0 &+= 4};if mode=="continuation" {c.sourceReturnPC=0x4852c9}
   _=f.host.withObjectAllocation(provider:f.memory){f.host.callNativeDependency(c)}
   record("out-of-context \(mode) request rejected before allocation",f.host.fault != nil && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  do{let f=try Fixture(p,hash);var state=fp(p["incoming"] as! [Any]);state.control=0x27f;_=f.host.withObjectAllocation(provider:f.memory){f.host.withObjectX87Environment(state,body:{f.host.invoke(f.call())})};record("unsupported x87 CW rejected",f.host.fault != nil && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  for mode in ["cw","count","reserved","version","entry","status","pop","push","returned","eax","unused-slot","slot-reserved"] {
   let f=try Fixture(p,hash);var state=fp(p["incoming"] as! [Any]);if mode=="cw" {state.control=0};if mode=="count" {state.count=9};if mode=="reserved" {state.reserved0=1};if mode=="version" {state.version=2};if mode=="status" {state.status=0x10000};if mode=="pop" {state.popCount=1};if mode=="push" {state.pushCount=1};if mode=="returned" {state.returned=1};if mode=="eax" {state.eax=1};if mode=="unused-slot" {state.slots.7.significand=1};if mode=="slot-reserved" {state.slots.0.reserved=1}
   if mode=="entry" {var c=ClawCall();c.function=0x44c000;c.x87ArgumentCount=UInt32(CLAW_X87_ENTRY);withUnsafeMutablePointer(to:&state){c.x87State=$0;_=f.host.callNativeDependency(c)};record("unelected entry rejected",f.host.fault != nil)}
   else {let r=f.host.withObjectX87Environment(state,body:{f.host.invoke(f.call())});record("malformed x87 \(mode) rejected",r==nil && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  }
  do{var scene=p;scene["scene"]=true;let f=try Fixture(scene,hash);var captured:ClawNativeCanonicalHost.ObjectAllocationRequest?;f.memory.beforeObjectAllocation={captured=$0};let success = !failed(f);let token=f.get(f.state+0x18)
   record("allocation lease expires",success && captured.map{!$0.consume(for:f.host,provider:f.memory)}==true)
   record("allocation owner retained",success && f.memory.ownsObjectAllocation(token,count:0x478))
   if success {let release=f.host.retireRobberThief(actor:f.actor,provider:f.memory,retireSecondary:true);record("owner routed release",release && !f.memory.ownsObjectAllocation(token,count:0x478));f.put(f.state+0x1c,0);record("fresh allocation after release",!failed(f) && f.get(f.state+0x18) != token)}
  }
  do{var scene=p;scene["scene"]=true;let f=try Fixture(scene,hash);let success = !failed(f);let token=f.get(f.state+0x18)
   record("scene heap helper allocation retained",success && f.memory.claimsSceneObject(token) && f.memory.ownsObjectAllocation(token,count:0x478))
   if success {
    let released=f.host.retireRobberThief(actor:f.actor,provider:f.memory,retireSecondary:true);record("scene owner routed release",released && !f.memory.ownsObjectAllocation(token,count:0x478))
    f.put(f.state+0x1c,0);record("scene owner routed reallocation",!failed(f) && f.get(f.state+0x18) != token)
   }
  }
  let lifecycle=profiles.first{($0["lifecycle"] as? Bool)==true}!
  for mode in ["eax","ecx","esi","esp","ebp","frame","continuation"] {
   let f=try Fixture(lifecycle,hash),first=f.step(0,fp(lifecycle["incoming"] as! [Any]));var injected=false
   f.inject={c in if !injected && c.function==0x44c840 {injected=true
    if mode=="frame" || mode=="continuation",let sp=c.sourceContext?.pointee.esp,let bytes=f.host.bytes(sp+(mode=="frame" ? 4:0),count:4) {bytes[0] ^= 1}
    else if let cpu=c.sourceContext {switch mode {
     case "eax":cpu.pointee.eax ^= 4;case "ecx":cpu.pointee.ecx ^= 4;case "esi":cpu.pointee.esi ^= 4;case "esp":cpu.pointee.esp ^= 4;case "ebp":cpu.pointee.ebp ^= 4;default:break}
    }
   }}
   let result=f.step(2000,first.1);record("lifecycle source \(mode) rejected",first.0 && injected && !result.0 && f.host.fault != nil)
  }
  for mode in ["vtable","phase","actor-link","helper-link","state-link","x87","reentry"] {
   let f=try Fixture(lifecycle,hash),first=f.step(0,fp(lifecycle["incoming"] as! [Any]));var injected=false
   if mode=="vtable" {f.put(f.get(f.state+0x18),0x50c934);injected=true}
   if mode=="actor-link" {f.put(f.actor+0x6c,f.state+4);injected=true}
   if mode=="helper-link" {f.put(f.state+0x18,f.get(f.state+0x18)+4);injected=true}
   if mode=="state-link" {f.put(f.state+0x10,0x4379d0);injected=true}
   if mode=="phase" {f.inject={c in if !injected && c.function==0x4dc870 {injected=true;f.put(f.state+0x1c,1000)}}}
   if mode=="x87" {f.inject={c in if !injected && c.function==0x43e420 {injected=true;c.x87State?.pointee.reserved0=1}}}
   if mode=="reentry" {f.inject={c in if !injected && c.function==0x4dc870 {injected=true;_=f.host.invoke(f.call())}}}
   let result=f.step(2000,first.1);record("lifecycle \(mode) rejected",first.0 && injected && !result.0)
  }
  do{var scene=p;scene["scene"]=true;let f=try Fixture(scene,hash),foreign=try Fixture(scene,hash);let first=f.step(0,fp(p["incoming"] as! [Any]));record("retirement rejects foreign provider",first.0 && !f.host.retireRobberThief(actor:f.actor,provider:foreign.memory))}
  for mode in ["cstring-link","bitset-link","provider-reentry"] {
   var scene=p;scene["scene"]=true;let f=try Fixture(scene,hash),first=f.step(0,fp(p["incoming"] as! [Any]));var injected=false
   f.inject={c in if !injected && c.function==0x485870 {injected=true;let helper=f.get(f.state+0x18)
    if mode=="cstring-link" {f.put(helper+0x1a4,f.actor+12)}
    if mode=="bitset-link" {f.put(helper+0x2fc,64);f.put(helper+0x300,f.actor)}
    if mode=="provider-reentry" {_=f.host.retireRobberThief(actor:f.actor,provider:f.memory)}
   }}
   let result=f.host.retireRobberThief(actor:f.actor,provider:f.memory);record("retirement \(mode) substitution rejected",first.0 && injected && !result && f.host.fault != nil)
  }
  for slot:UInt32 in [0x5469d8,0x546a80] {
   let f=try Fixture(p,hash),first=f.step(0,fp(p["incoming"] as! [Any]));let token=f.get(f.state+0x18);var mutation=ClawCall();mutation.function=slot;mutation.stackPointer=UInt32(CLAW_STACK_TOP);mutation.argumentCount=slot==0x5469d8 ? 1:3;mutation.arguments.0=token;mutation.arguments.1=0x500;mutation.arguments.2=2
   let result=f.memory.service(mutation);record("persistent helper raw \(slot==0x5469d8 ? "free":"resize") rejected",first.0 && result==nil && f.host.fault != nil && f.heap.lookupBytes(token,count:0x478) != nil)
  }
  let result:[String:Any]=["profiles":output,"controls":controls];try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"));print("native profiles \(output.count), controls \(controls.count)")
 }
}
