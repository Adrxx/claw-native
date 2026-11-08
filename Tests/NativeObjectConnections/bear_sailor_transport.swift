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
 var allocationWitness=false;var events:[[Any]]=[];var calls:[[Any]]=[];var missing:UInt32?;var inject:((ClawCall)->Void)?
 init(_ p:[String:Any],_ hash:String)throws {
  self.p=p
  for b in p["initial"] as! [[String:Any]] {let d=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(d.count)).update(from:d,count:d.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
  let storage=heap;let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().map{k in(k,storage.lookup(k,words:1)![0])})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:0x61000000,sceneObjectAllocations:true)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in self.calls.append([c.function,c.receiver,args(c)]);if c.function==0x4f6428 {self.events.append(["free",c.arguments.0])};self.inject?(c)}
  memory.beforeObjectAllocation={ [unowned self] r in if r.root != 0x409860 {return};let offset=Int(r.context.esp-UInt32(CLAW_STACK_BASE)+0x14);self.allocationWitness=r.root==0x409860 && r.count==0x4a0 && r.returnPC==0x4f63ff && r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)}==0x40989d}
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
   guard a==[0],let cell=heap.lookup(c.receiver,words:1),string(cell[0]) != nil else{return nil};return cell[0]
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
  case 0x4a3810:
   guard c.receiver==0,a.count==2 else{return nil}
   for offset:UInt32 in 0..<4096 {
    guard let left=host.bytes(a[0]+offset,count:1),let right=host.bytes(a[1]+offset,count:1) else{return nil}
    let difference=Int32(left[0])-Int32(right[0])
    if difference != 0 {return UInt32(bitPattern:difference)}
    if left[0]==0 {return 0}
   }
   return nil
  case 0x4a3050:events.append(["rand",99]);return 99
  default:return nil
  }
 }
 func call()->ClawCall {var c=ClawCall();c.function=0x409860;c.argumentCount=1;c.arguments.0=actor;return c}
 func callback(_ command:UInt32)->Bool {
  put(state+0x1c,command)
  var complete=false
  _=host.withObjectAllocation(provider:memory) {
   if let result=host.withObjectX87Environment(fp(p["incoming"] as! [Any]),body:{host.invoke(call())}) {complete=result.0.completed}
  }
  return complete && host.fault==nil
 }
 func snapshot(_ spans:[[String:Any]])->[[String:Any]] {
  spans.map {b->[String:Any] in
   let address=u(b["address"]!),expected=b["data"] as! String
   if expected=="released" {return ["address":address,"data":heap.lookupBytes(address,count:1)==nil ? "released":"still allocated"]}
   let count=UInt32(expected.count/2)
   let value=heap.lookupBytes(address,count:count).map{UnsafeBufferPointer(start:$0,count:Int(count)).map{String(format:"%02x",$0)}.joined()} ?? "missing"
   return ["address":address,"data":value]
  }
 }
 func run()->[String:Any] {
  var stages:[[String:Any]]=[],outgoing=fp(p["incoming"] as! [Any]),allComplete=true
  for stage in p["stages"] as! [[String:Any]] {
   for write in stage["writes"] as? [[Any]] ?? [] {put(u(write[0]),u(write[1]))}
   var complete=false
   if stage["retire"] as? Bool == true {
    complete=host.retireBearSailor(actor:actor,provider:memory)
   } else {
    put(state+0x1c,u(stage["command"]!))
    _=host.withObjectAllocation(provider:memory){
     if let r=host.withObjectX87Environment(fp(fpJSON(outgoing)),body:{host.invoke(call())}) {complete=r.0.completed;outgoing=r.1}
    }
   }
   allComplete = allComplete && complete && host.fault==nil
   stages.append(["label":stage["label"]!,"completed":complete,"fault":host.fault.map{String(describing:$0)} ?? "none","outgoing":fpJSON(outgoing),"events":events,"calls":calls,"final":snapshot(stage["final"] as! [[String:Any]])])
   if !complete {break}
  }
  return ["label":p["label"]!,"completed":allComplete,"allocation_witness":allocationWitness,"stages":stages,"fault":host.fault.map{String(describing:$0)} ?? "none"]
 }
 func runInitial()->[String:Any] {
  var completion:ClawNativeCanonicalHost.Completion?;var outgoing=fp(p["incoming"] as! [Any])
  _=host.withObjectAllocation(provider:memory){if let r=host.withObjectX87Environment(outgoing,body:{host.invoke(call())}) {completion=r.0;outgoing=r.1}}
  let spans=(p["stages"] as! [[String:Any]])[0]["final"] as! [[String:Any]]
  let final=spans.map {b->[String:Any] in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);let text=heap.lookupBytes(a,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing";return["address":a,"data":text]}
  return["label":p["label"]!,"allocation_witness":allocationWitness,"completed":completion?.completed==true,"fault":host.fault.map{String(describing:$0)} ?? "scope refused","outgoing":fpJSON(outgoing),"events":events,"calls":calls,"final":final]
 }
}
@main struct BearSailorTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]);let ref=try JSONSerialization.jsonObject(with:Data(contentsOf:dir.appendingPathComponent("reference.json"))) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  var output:[[String:Any]]=[];for p in profiles{output.append(try Fixture(p,hash).run())}
  var controls:[[String:Any]]=[]
  func record(_ n:String,_ ok:Bool){controls.append(["name":n,"passed":ok])}
  func failed(_ f:Fixture)->Bool {!(f.runInitial()["completed"] as! Bool)}
  do{let f=try Fixture(p,hash);record("provider required",!f.host.invoke(f.call()).completed && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);record("foreign provider rejected",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(f.call())}==nil)}
  do{let f=try Fixture(p,hash);f.put(f.state+0x10,0x409861);record("wrong callback rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.put(f.actor+0x6c,UInt32.max);record("wrong actor state rejected",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x4f6286;record("missing registry fails",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x546d5c;record("missing rectangle fails",failed(f))}
  do{let f=try Fixture(p,hash);f.memory.failAllocation={$0==0x4a48e0};record("allocation exhaustion preserved",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);let bytes=f.heap.storeBytes(token:0x61000000,count:0x4a0);bytes.update(repeating:0xa7,count:0x4a0);record("occupied allocation preserved",failed(f) && UnsafeBufferPointer(start:bytes,count:0x4a0).allSatisfy{$0==0xa7})}
  do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={_ in f.heap.free(0x10000000);_=f.heap.storeBytes(token:0x10000000,count:0x10000)};record("actor identity replacement rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.memory.afterService={slot,_,token in if slot==0x4a48e0 && token != 0 {f.heap.free(token);_=f.heap.storeBytes(token:token,count:0x4a0)}};record("allocation identity replacement rejected",failed(f))}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(f.call())};record("physical service reentry rejected",failed(f) && nested?.completed==false)}
  for delta:UInt32 in [0,4,0x14,0x18] {
   let f=try Fixture(p,hash)
   f.memory.beforeObjectAllocation={r in if let bytes=f.host.bytes(r.context.esp+delta,count:4) {bytes.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}}}
   record("source allocation stack word \(delta) tampering rejected before allocation",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  for mode in ["size","receiver","actor","continuation"] {
   let f=try Fixture(p,hash);var injected=false
   f.inject={c in if !injected && c.function==(mode=="size" ? 0x4f63ec:0x409920) {injected=true;var wrong=c
    if mode=="size" {wrong.arguments.0=0x49f};if mode=="receiver" {wrong.receiver &+= 4};if mode=="actor" {wrong.arguments.0 &+= 4};if mode=="continuation" {wrong.sourceReturnPC=0x4098b9}
    _=f.host.callNativeDependency(wrong)
   }};record("reentrant wrong \(mode) request rejected",failed(f) && injected)
  }
  for offset:UInt32 in [8,0x0c,0x10] {
   let f=try Fixture(p,hash);var corrupted=false
   f.inject={c in if !corrupted && c.function==0x4062e0 && f.get(0x61000000)==0x50b38c {corrupted=true;f.put(0x61000000+offset,f.get(0x61000000+offset)+4)}}
   record("post-base helper link \(offset) corruption rejected",failed(f) && corrupted)
  }
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x4062e0 && f.get(0x61000000)==0x50b38c {changed=true;f.put(f.state+0x1c,0)}};record("construction command mutation rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x405000 {changed=true;f.put(0x61000000,0x50b390)}};record("initial vtable replacement rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);let first = !failed(f);f.put(f.state+0x1c,0);record("stale live helper rejected",first && failed(f))}
  do{let f=try Fixture(p,hash);let first = !failed(f)
   let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.map{($0,f.get($0))})
   let replacement=try ClawNativeMfcMemory(host:f.host,sha256:hash,importTargets:imports,allocationBase:0x62000000,sceneObjectAllocations:true)
   f.put(f.state+0x1c,1000)
   let result=f.host.withObjectAllocation(provider:replacement){f.host.invoke(f.call())}
   record("live binding rejects replacement provider",first && result?.completed != true && f.host.fault != nil)
  }
  do{let f=try Fixture(p,hash);record("unbound nonconstruction phase rejected",!f.callback(1000))}
  do{let f=try Fixture(p,hash);let first = !failed(f);f.put(f.state+0x18,f.get(f.state+0x18)+4);record("wrong helper rejected",first && !f.callback(1000))}
  do{let f=try Fixture(p,hash);let first = !failed(f);let token=f.get(f.state+0x18)
   if first,let ptr=f.heap.lookupBytes(token,count:0x4a0) {let saved=Array(UnsafeBufferPointer(start:ptr,count:0x4a0));f.heap.free(token);f.heap.storeBytes(token:token,count:0x4a0).update(from:saved,count:saved.count)}
   record("live helper identity replacement rejected",first && !f.callback(1000))
  }
  do{let f=try Fixture(p,hash);let first = !failed(f);let token=f.get(f.state+0x18);let retired=first && f.host.retireBearSailor(actor:f.actor,provider:f.memory);f.put(f.state+0x18,token);record("retired helper rejected",retired && !f.callback(1000))}
  do{let f=try Fixture(p,hash);let first = !failed(f);let token=f.get(f.state+0x18);let retired=first && f.host.retireBearSailor(actor:f.actor,provider:f.memory);f.put(f.state+0x1c,0);let fresh=retired && !failed(f);record("stale release cannot retire recreated helper",fresh && token != f.get(f.state+0x18) && !f.memory.releaseSceneObject(token) && f.heap.lookupBytes(f.get(f.state+0x18),count:0x4a0) != nil)}
  do{let f=try Fixture(p,hash);f.missing=0x4f6974;record("missing lifecycle CString fails",!(f.run()["completed"] as! Bool) && f.calls.contains{u($0[0])==0x4f6974})}
  do{let f=try Fixture(p,hash);var changed=false
   f.inject={c in if !changed && c.function==0x40a040 {changed=true;let low=f.get(0x534980),stride=f.get(0x534990),base=f.get(0x534988),index=f.get(f.state+0x1c);f.put(base &+ (index &- low) &* stride,0x405000)}}
   record("registered handler replacement rejected",!(f.run()["completed"] as! Bool) && changed)
  }
  for mode in ["continuation","stack","receiver"] {
   let f=try Fixture(p,hash);var injected=false
   f.inject={c in if !injected && c.function==0x40a040 && c.sourceContext != nil {injected=true;var wrong=c
    if mode=="continuation" {wrong.sourceReturnPC &+= 1};if mode=="stack" {wrong.stackPointer &+= 4};if mode=="receiver" {wrong.receiver &+= 4}
    _=f.host.callNativeDependency(wrong)
   }}
   record("source dispatcher wrong \(mode) rejected",!(f.run()["completed"] as! Bool) && injected)
  }
  do{let f=try Fixture(p,hash);var attempted=false,nested:ClawNativeCanonicalHost.Completion?
   f.inject={c in if !attempted && c.function==0x40a490 {attempted=true;nested=f.host.invoke(f.call())}}
   record("state handler reentry rejected",!(f.run()["completed"] as! Bool) && attempted && nested?.completed==false)
  }
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);let first = !failed(f)
   record("foreign provider retirement rejected",first && !f.host.retireBearSailor(actor:f.actor,provider:other.memory) && f.heap.lookupBytes(f.get(f.state+0x18),count:0x4a0) != nil)
  }
  for mode in ["size","receiver","actor","continuation"] {
   let f=try Fixture(p,hash);var c=ClawCall();c.function=mode=="size" ? 0x4f63ec:0x409920;c.argumentCount=1;c.arguments.0=mode=="size" ? 0x49f:f.actor;c.receiver=mode=="size" ? 0:0x61000004;if mode=="actor" {c.arguments.0 &+= 4};if mode=="continuation" {c.sourceReturnPC=0x4098b9}
   _=f.host.withObjectAllocation(provider:f.memory){f.host.callNativeDependency(c)}
   record("out-of-context \(mode) request rejected before allocation",f.host.fault != nil && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  do{let f=try Fixture(p,hash);var state=fp(p["incoming"] as! [Any]);state.control=0x27f;_=f.host.withObjectAllocation(provider:f.memory){f.host.withObjectX87Environment(state,body:{f.host.invoke(f.call())})};record("unsupported x87 CW rejected",f.host.fault != nil && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  for mode in ["cw","count","reserved","version","entry","status","pop","push","returned","eax","unused-slot","slot-reserved"] {
   let f=try Fixture(p,hash);var state=fp(p["incoming"] as! [Any]);if mode=="cw" {state.control=0};if mode=="count" {state.count=9};if mode=="reserved" {state.reserved0=1};if mode=="version" {state.version=2};if mode=="status" {state.status=0x10000};if mode=="pop" {state.popCount=1};if mode=="push" {state.pushCount=1};if mode=="returned" {state.returned=1};if mode=="eax" {state.eax=1};if mode=="unused-slot" {state.slots.7.significand=1};if mode=="slot-reserved" {state.slots.0.reserved=1}
   if mode=="entry" {var c=ClawCall();c.function=0x44c000;c.x87ArgumentCount=UInt32(CLAW_X87_ENTRY);withUnsafeMutablePointer(to:&state){c.x87State=$0;_=f.host.callNativeDependency(c)};record("unelected entry rejected",f.host.fault != nil)}
   else {let r=f.host.withObjectX87Environment(state,body:{f.host.invoke(f.call())});record("malformed x87 \(mode) rejected",r==nil && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  }
  do{let f=try Fixture(p,hash);var captured:ClawNativeCanonicalHost.ObjectAllocationRequest?;f.memory.beforeObjectAllocation={captured=$0};let success = !failed(f);let token=f.get(f.state+0x18)
   record("allocation lease expires",success && captured.map{!$0.consume(for:f.host,provider:f.memory)}==true)
   record("allocation owner retained",success && f.memory.ownsObjectAllocation(token,count:0x4a0))
   if success {let release=f.host.retireBearSailor(actor:f.actor,provider:f.memory);record("owner routed release",release && !f.memory.ownsObjectAllocation(token,count:0x4a0));f.put(f.state+0x1c,0);record("fresh allocation after release",!failed(f) && f.get(f.state+0x18) != token)}
  }
  let result:[String:Any]=["profiles":output,"controls":controls];try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"));print("native profiles \(output.count), controls \(controls.count)")
 }
}
