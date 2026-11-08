import Foundation
private func u(_ x:Any)->UInt32 {(x as! NSNumber).uint32Value}
private func decode(_ s:String)->[UInt8] {let b=Array(s.utf8);func n(_ c:UInt8)->UInt8 {c>=97 ? c-87:c-48};return stride(from:0,to:b.count,by:2).map{n(b[$0])*16+n(b[$0+1])}}
private func args(_ c:ClawCall)->[UInt32] {var c=c;return withUnsafeBytes(of:&c.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(c.argumentCount)))}}
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
  host.observer={ [unowned self] c in self.calls.append([c.function,c.receiver,args(c)]);self.inject?(c)}
  memory.beforeObjectAllocation={ [unowned self] r in guard r.root==0x4553d0 else {return};let offset=Int(r.context.esp-UInt32(CLAW_STACK_BASE)+0x14);self.allocationWitness=r.root==0x4553d0 && r.count==0x58 && r.returnPC==0x4f63ff && r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)}==0x45540a}
  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]])}}
 }
 var actor:UInt32 {u(p["actor"]!)};var state:UInt32 {u(p["state"]!)}
 func get(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)![0]}
 func put(_ a:UInt32,_ v:UInt32){heap.lookup(a,words:1)?[0]=v}
 func string(_ a:UInt32)->String? {var bytes:[UInt8]=[];for i:UInt32 in 0..<256 {guard let p=host.bytes(a+i,count:1) else{return nil};if p[0]==0{return String(bytes:bytes,encoding:.ascii)};bytes.append(p[0])};return nil}
 func service(_ c:ClawCall)->UInt32? {
  let a=args(c);let f=c.function
  if missing==f{return nil}
  switch f {
  case 0x4f6974:
   guard a==[0],let data=heap.lookup(c.receiver,words:1)?[0],data>=12,let header=heap.lookup(data-12,words:3),header[0]==1,header[1]<=header[2],string(data) != nil else{return nil};return data
  case 0x4f6286:
   guard a.count==2,let name=string(a[0]),let out=host.bytes(a[1],count:4),let map=heap.lookup(c.receiver+4,words:2) else{return nil}
   let buckets=map[0],count=map[1];guard count>0,count<4096 else{return nil};var value:UInt32=0
   if buckets != 0 {for i in 0..<count {guard let slot=heap.lookup(buckets+i*4,words:1) else{return nil};var node=slot[0],seen:Set<UInt32>=[]
    while node != 0 {guard seen.insert(node).inserted,let words=heap.lookup(node,words:4),let key=string(words[2]) else{return nil};if key==name {value=words[3];break};node=words[0]}
    if value != 0 {break}
   }}
   out.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee=value};events.append(["lookup",c.receiver,name,value]);return value==0 ? 0:1
  default:return nil
  }
 }
 func call()->ClawCall {var c=ClawCall();c.function=0x4553d0;c.argumentCount=1;c.arguments.0=actor;return c}
 func run()->[String:Any] { execute(NSNumber(value:get(state+0x1c)), expected:(p["phases"] as! [[String:Any]])[0]) }
 func execute(_ command:Any,expected:[String:Any])->[String:Any] {
  var completed=false
  if let text=command as? String,text=="retire" {
   completed=host.retireLaser(actor:actor,provider:memory)
  } else {
   if let value=command as? NSNumber {put(state+0x1c,value.uint32Value);if value.uint32Value==5 {put(0x537210,0xfffffff0 &+ u(p["elapsed"]!))}}
   else if let text=command as? String,text=="recreate" {put(state+0x1c,0)}
   _=host.withObjectAllocation(provider:memory){completed=host.invoke(call()).completed}

  }
  let final=(expected["final"] as! [[String:Any]]).map {b->[String:Any] in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);let text=heap.lookupBytes(a,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing";return["address":a,"data":text]}
  return["command":command,"helper":get(state+0x18),"allocation_witness":allocationWitness,"completed":completed,"fault":host.fault.map{String(describing:$0)} ?? "scope refused","events":events,"calls":calls,"retired":memory.tlsSnapshot().allocationBytes.filter{memory.localBytes[$0.key]==nil}.mapValues{$0.map{String(format:"%02x",$0)}.joined()},"final":final]
 }
 func full()->[String:Any] {
  let phases=(p["phases"] as! [[String:Any]]).map{execute($0["command"]!,expected:$0)}
  return["label":p["label"]!,"allocation_witness":allocationWitness,"phases":phases]
 }

}
@main struct LaserTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]);let ref=try JSONSerialization.jsonObject(with:Data(contentsOf:dir.appendingPathComponent("reference.json"))) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  var output:[[String:Any]]=[];for p in profiles{let result=try Fixture(p,hash).full();output.append(result);for phase in result["phases"] as! [[String:Any]] {if !(phase["completed"] as! Bool) {print("phase failure \(p["label"]!) \(phase["command"]!) \(phase["fault"]!)")}}}
  var controls:[[String:Any]]=[]
  func record(_ n:String,_ ok:Bool){controls.append(["name":n,"passed":ok])}
  func failed(_ f:Fixture)->Bool {!(f.run()["completed"] as! Bool)}
  do{let f=try Fixture(p,hash);record("provider required",!f.host.invoke(f.call()).completed && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);record("foreign provider rejected",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(f.call())}==nil)}
  do{let f=try Fixture(p,hash);f.put(f.state+0x10,0x4553d1);record("wrong callback rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.put(f.actor+0x6c,UInt32.max);record("wrong actor state rejected",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x4f6286;record("missing registry fails",failed(f))}
  do{let f=try Fixture(p,hash);f.memory.failAllocation={$0==0x4a48e0};record("allocation exhaustion preserved",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);let bytes=f.heap.storeBytes(token:0x61000000,count:0x58);bytes.update(repeating:0xa7,count:0x58);record("occupied allocation preserved",failed(f) && UnsafeBufferPointer(start:bytes,count:0x58).allSatisfy{$0==0xa7})}
  do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={_ in f.heap.free(0x10000000);_=f.heap.storeBytes(token:0x10000000,count:0x10000)};record("actor identity replacement rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.memory.afterService={slot,_,token in if slot==0x4a48e0 && token != 0 {f.heap.free(token);_=f.heap.storeBytes(token:token,count:0x58)}};record("allocation identity replacement rejected",failed(f))}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(f.call())};record("physical service reentry rejected",failed(f) && nested?.completed==false)}
  for delta:UInt32 in [0,4,0x14,0x18] {
   let f=try Fixture(p,hash)
   f.memory.beforeObjectAllocation={r in if let bytes=f.host.bytes(r.context.esp+delta,count:4) {bytes.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}}}
   record("source allocation stack word \(delta) tampering rejected before allocation",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  for mode in ["size","receiver","actor","continuation","constructor"] {
   let f=try Fixture(p,hash);var injected=false
   f.inject={c in if !injected && c.function==(mode=="size" ? 0x4f63ec:0x455490) {injected=true;var wrong=c
    if mode=="size" {wrong.arguments.0=0x57};if mode=="receiver" {wrong.receiver &+= 4};if mode=="actor" {wrong.arguments.0 &+= 4};if mode=="continuation" {wrong.sourceReturnPC=0x455429};if mode=="constructor" {wrong.function=0x437a90}
    _=f.host.callNativeDependency(wrong)
   }};record("reentrant wrong \(mode) request rejected",failed(f) && injected)
  }
  for offset:UInt32 in [8,0x0c,0x10] {
   let f=try Fixture(p,hash);var corrupted=false
   f.inject={c in if !corrupted && c.function==0x4c7970 {corrupted=true;f.put(0x61000000+offset,f.get(0x61000000+offset)+4)}}
   record("post-base helper link \(offset) corruption rejected",failed(f) && corrupted)
  }
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x4c7970 {changed=true;f.put(f.state+0x1c,0)}};record("construction command mutation rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x4c96b0 {changed=true;f.put(0x61000000,0x50f590)}};record("initial vtable replacement rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);let first = !failed(f);f.put(f.state+0x1c,0);record("stale live helper rejected",first && failed(f))}
  for mode in ["size","receiver","actor","continuation","constructor"] {
   let f=try Fixture(p,hash);var c=ClawCall();c.function=mode=="size" ? 0x4f63ec:0x455490;c.argumentCount=1;c.arguments.0=mode=="size" ? 0x57:f.actor;c.receiver=mode=="size" ? 0:0x61000004;if mode=="actor" {c.arguments.0 &+= 4};if mode=="continuation" {c.sourceReturnPC=0x455429};if mode=="constructor" {c.function=0x437a90}
   _=f.host.withObjectAllocation(provider:f.memory){f.host.callNativeDependency(c)}
   record("out-of-context \(mode) request rejected before allocation",f.host.fault != nil && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  do{let f=try Fixture(p,hash);var captured:ClawNativeCanonicalHost.ObjectAllocationRequest?;f.memory.beforeObjectAllocation={captured=$0};let success = !failed(f);let token=f.get(f.state+0x18)
   record("allocation lease expires",success && captured.map{!$0.consume(for:f.host,provider:f.memory)}==true)
   record("allocation owner retained",success && f.memory.ownsObjectAllocation(token,count:0x58))
   if success {let release=f.host.retireLaser(actor:f.actor,provider:f.memory);record("owner routed release",release && !f.memory.ownsObjectAllocation(token,count:0x58));f.put(f.state+0x1c,0);record("fresh allocation after release",!failed(f) && f.get(f.state+0x18) != token)}
  }
  do{let f=try Fixture(p,hash);let first = !failed(f);let old=f.get(f.state+0x18);let retired=f.host.retireLaser(actor:f.actor,provider:f.memory);f.put(f.state+0x1c,0);let recreated = !failed(f);let fresh=f.get(f.state+0x18);f.put(f.state+0x18,old);f.put(f.state+0x1c,5);record("retirement recreation rejects stale helper",first && retired && recreated && fresh != old && failed(f))}
  do{let f=try Fixture(p,hash);let first = !failed(f);let retired=f.host.retireLaser(actor:f.actor,provider:f.memory);record("double retirement rejected",first && retired && !f.host.retireLaser(actor:f.actor,provider:f.memory))}
  do{let f=try Fixture(p,hash);let first = !failed(f);let token=f.get(f.state+0x18);let following=f.heap.allocate(bytes:16);record("shared scene cursor advanced by exact extent",first && following==token+0x360)}
  for mode in ["actor","logic","helper","vtable"] {
   let f=try Fixture(p,hash);let first = !failed(f);let helper=f.get(f.state+0x18)
   if mode=="actor" {f.put(f.actor+0x6c,f.state+4)}
   if mode=="logic" {f.put(f.state+0x10,0x4553d1)}
   if mode=="helper" {f.heap.free(helper);_=f.heap.storeBytes(token:helper,count:0x58)}
   if mode=="vtable" {f.put(helper,0x50f590)}
   f.put(f.state+0x1c,5);record("lifecycle stale \(mode) rejected",first && failed(f))
  }
  do{let f=try Fixture(p,hash);let first = !failed(f);let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.map{($0,f.get($0))});let foreign=try ClawNativeMfcMemory(host:f.host,sha256:hash,importTargets:imports,allocationBase:0x62000000,sceneObjectAllocations:true);f.put(f.state+0x1c,5);let result=f.host.withObjectAllocation(provider:foreign){f.host.invoke(f.call())};record("foreign provider on same host rejected",first && result?.completed != true && f.host.fault != nil)}
  do{let f=try Fixture(p,hash);let first = !failed(f);let helper=f.get(f.state+0x18);let foreign=f.heap.allocate(bytes:0x58);if let src=f.heap.lookupBytes(helper,count:0x58),let dst=f.heap.lookupBytes(foreign,count:0x58) {dst.update(from:src,count:0x58)};f.put(f.state+0x18,foreign);f.put(f.state+0x1c,5);record("foreign helper allocation rejected",first && failed(f))}
  for mode in ["wrong actor","foreign provider","replaced helper","foreign helper"] {
   let f=try Fixture(p,hash);let first = !failed(f);let helper=f.get(f.state+0x18);var actor=f.actor;var provider=f.memory
   if mode=="wrong actor" {actor &+= 4}
   if mode=="foreign provider" {let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.map{($0,f.get($0))});provider=try ClawNativeMfcMemory(host:f.host,sha256:hash,importTargets:imports,allocationBase:0x62000000,sceneObjectAllocations:true)}
   if mode=="replaced helper" {f.heap.free(helper);_=f.heap.storeBytes(token:helper,count:0x58)}
   if mode=="foreign helper" {let other=f.heap.allocate(bytes:0x58);if let src=f.heap.lookupBytes(helper,count:0x58),let dst=f.heap.lookupBytes(other,count:0x58) {dst.update(from:src,count:0x58)};f.put(f.state+0x18,other)}
   let retired=f.host.retireLaser(actor:actor,provider:provider)
   record("direct retirement \(mode) rejected",first && !retired && f.host.fault != nil)
  }
  do{let f=try Fixture(p,hash);let first = !failed(f);f.missing=0x4f6974;f.put(f.state+0x1c,5);record("missing lifecycle string service rejected",first && failed(f))}
  do{let f=try Fixture(p,hash);let first = !failed(f);let table=f.get(0x5379e0);f.put(table,0x4041a0);f.put(f.state+0x1c,5);record("unelected state table target rejected",first && failed(f))}
  for target:UInt32 in [0x455490,0x455600,0x4558b0,0x455960] {
   let f=try Fixture(p,hash);let first = !failed(f);var c=ClawCall();c.function=target;c.receiver=f.get(f.state+0x18)
   if target==0x455490 || target==0x455600 {c.argumentCount=1;c.arguments.0=target==0x455490 ? f.actor:5}
   record("direct Laser entry \(target) rejected",first && !f.host.invoke(c).completed)
  }
  let result:[String:Any]=["profiles":output,"controls":controls];try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"));print("native profiles \(output.count), controls \(controls.count)")
 }
}
