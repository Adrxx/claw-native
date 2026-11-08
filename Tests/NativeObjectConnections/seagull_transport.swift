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
private func cpuJSON(_ x:ClawSourceContext)->[String:Any] {
 ["size":x.size,"version":x.version,"input":x.inputMask,"output":x.outputMask,"preserve":x.preserveMask,"eax":x.eax,"ebx":x.ebx,"ecx":x.ecx,"edx":x.edx,"esi":x.esi,"edi":x.edi,"ebp":x.ebp,"esp":x.esp,"eip":x.eip,"eflags":x.eflags,"fsHead":x.fsHead]
}
private final class Fixture {
 let heap=ClawTokenHeap();let host:ClawNativeCanonicalHost;let memory:ClawNativeMfcMemory;let p:[String:Any]
 var animationExact:[[Any]]=[];var sourceReturns:[[String:Any]]=[];var exact:[[String:Any]]=[];var sources:[[String:Any]]=[];var environment=ClawX87State();var allocationWitness=false;var events:[[Any]]=[];var calls:[[Any]]=[];var missing:UInt32?;var inject:((ClawCall)->Void)?
 init(_ p:[String:Any],_ hash:String)throws {
  self.p=p;environment=fp(p["incoming"] as! [Any])
  for b in p["initial"] as! [[String:Any]] {let d=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(d.count)).update(from:d,count:d.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
  let storage=heap;let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().map{k in(k,storage.lookup(k,words:1)![0])})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:0x61000000,sceneObjectAllocations:true)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in self.calls.append([c.function,c.receiver,args(c)]);if c.function==0x4332f0,c.x87ArgumentCount==UInt32(CLAW_X87_EXACT),let p=c.x87State {self.exact.append(["function":c.function,"state":fpJSON(p.pointee),"pop":p.pointee.popCount,"push":p.pointee.pushCount,"returned":p.pointee.returned])};if let p=c.sourceContext,[UInt32(0x4873a0),0x4879a0].contains(c.function) {let x=p.pointee;self.sources.append(["function":c.function,"return_pc":c.sourceReturnPC,"size":x.size,"version":x.version,"input":x.inputMask,"output":x.outputMask,"preserve":x.preserveMask,"cpu":["eax":x.eax,"ebx":x.ebx,"ecx":x.ecx,"edx":x.edx,"esi":x.esi,"edi":x.edi,"ebp":x.ebp,"esp":x.esp,"eip":x.eip,"eflags":x.eflags]])};if c.function==0x4c82a0,c.x87ArgumentCount==UInt32(CLAW_X87_EXACT),let p=c.x87State {self.animationExact.append(fpJSON(p.pointee))};self.inject?(c)}
  memory.beforeObjectAllocation={ [unowned self] r in let offset=Int(r.context.esp-UInt32(CLAW_STACK_BASE)+0x14);self.allocationWitness=r.root==0x486e90 && r.count==0x440 && r.returnPC==0x4f63ff && r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)}==0x486ecd}
  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]])}}
 }
 var actor:UInt32 {u(p["actor"]!)};var state:UInt32 {u(p["state"]!)}
 func get(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)![0]}
 func put(_ a:UInt32,_ v:UInt32){heap.lookup(a,words:1)?[0]=v}
 func string(_ a:UInt32)->String? {var bytes:[UInt8]=[];for i:UInt32 in 0..<256 {guard let p=host.bytes(a+i,count:1) else{return nil};if p[0]==0{return String(bytes:bytes,encoding:.ascii)};bytes.append(p[0])};return nil}
 func service(_ c:ClawCall)->UInt32? {
  let a=args(c);var f=c.function
  for slot:UInt32 in [0x546d5c,0x546cdc,0x5469e8,0x546cd4] {if get(slot)==f {f=slot}}
  if missing==f{return nil}
  switch f {
  case 0x4f6974:
   guard a==[0],let data=heap.lookup(c.receiver,words:1)?[0],data>=12,let header=heap.lookup(data-12,words:3),header[0]==1,header[1]<=header[2],string(data) != nil else{return nil};return data
  case 0x546cd4:
   guard a.count==3,let rectangle=host.bytes(a[0],count:16) else{return nil};let bounds=rectangle.withMemoryRebound(to:UInt32.self,capacity:4){Array(UnsafeBufferPointer(start:$0,count:4)).map{Int32(bitPattern:$0)}};let x=Int32(bitPattern:a[1]),y=Int32(bitPattern:a[2]);let result:UInt32=bounds[0]<=x && x<bounds[2] && bounds[1]<=y && y<bounds[3] ? 1:0;events.append(["contains",a[0],x,y,result]);return result
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
 func call()->ClawCall {var c=ClawCall();c.function=0x486e90;c.argumentCount=1;c.arguments.0=actor;return c}
 func run()->[String:Any] { execute(NSNumber(value:get(state+0x1c)), expected:(p["phases"] as! [[String:Any]])[0]) }
 func execute(_ command:Any,expected:[String:Any])->[String:Any] {
  var completed=false
  if let text=command as? String,text=="retire" {
   if let result=host.withObjectX87Environment(environment,body:{host.retireSeagull(actor:actor,provider:memory)}) {completed=result.0;environment=result.1}
  } else {
   if let value=command as? NSNumber {put(state+0x1c,value.uint32Value)}
   else if let text=command as? String,text=="recreate" {put(state+0x1c,0)}
   _=host.withObjectAllocation(provider:memory){if let result=host.withObjectX87Environment(environment,body:{host.invoke(call())}) {completed=result.0.completed;environment=result.1}}
   sourceReturns += host.seagullSourceObservations.map { x in ["function":x.function,"return_pc":x.returnPC,"input":cpuJSON(x.input),"output":cpuJSON(x.output),"incoming_x87":x.incomingX87.map(fpJSON) as Any,"outgoing_x87":x.outgoingX87.map(fpJSON) as Any] }
  }
  let final=(expected["final"] as! [[String:Any]]).map {b->[String:Any] in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);let text=heap.lookupBytes(a,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing";return["address":a,"data":text]}
  return["command":command,"helper":get(state+0x18),"allocation_witness":allocationWitness,"completed":completed,"fault":host.fault.map{String(describing:$0)} ?? "scope refused","outgoing":fpJSON(environment),"events":events,"calls":calls,"sources":sources,"exact":exact,"source_returns":sourceReturns,"animation_exact":animationExact,"final":final]
 }
 func full()->[String:Any] {
  let phases=(p["phases"] as! [[String:Any]]).map{execute($0["command"]!,expected:$0)}
  return["label":p["label"]!,"allocation_witness":allocationWitness,"phases":phases]
 }

}
@main struct SeagullTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]);let ref=try JSONSerialization.jsonObject(with:Data(contentsOf:dir.appendingPathComponent("reference.json"))) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  var output:[[String:Any]]=[];for p in profiles{let result=try Fixture(p,hash).full();output.append(result);for phase in result["phases"] as! [[String:Any]] {if !(phase["completed"] as! Bool) {print("phase failure \(p["label"]!) \(phase["command"]!) \(phase["fault"]!)")}}}
  var controls:[[String:Any]]=[]
  func record(_ n:String,_ ok:Bool){controls.append(["name":n,"passed":ok])}
  func failed(_ f:Fixture)->Bool {!(f.run()["completed"] as! Bool)}
  do{let f=try Fixture(p,hash);record("provider required",!f.host.invoke(f.call()).completed && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);record("foreign provider rejected",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(f.call())}==nil)}
  do{let f=try Fixture(p,hash);f.put(f.state+0x10,0x486e91);record("wrong callback rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.put(f.actor+0x6c,UInt32.max);record("wrong actor state rejected",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x4f6286;record("missing registry fails",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x546d5c;record("missing rectangle fails",failed(f))}
  do{let f=try Fixture(p,hash);f.memory.failAllocation={$0==0x4a48e0};record("allocation exhaustion preserved",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);let bytes=f.heap.storeBytes(token:0x61000000,count:0x440);bytes.update(repeating:0xa7,count:0x440);record("occupied allocation preserved",failed(f) && UnsafeBufferPointer(start:bytes,count:0x440).allSatisfy{$0==0xa7})}
  do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={_ in f.heap.free(0x10000000);_=f.heap.storeBytes(token:0x10000000,count:0x10000)};record("actor identity replacement rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.memory.afterService={slot,_,token in if slot==0x4a48e0 && token != 0 {f.heap.free(token);_=f.heap.storeBytes(token:token,count:0x440)}};record("allocation identity replacement rejected",failed(f))}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(f.call())};record("physical service reentry rejected",failed(f) && nested?.completed==false)}
  for delta:UInt32 in [0,4,0x14,0x18] {
   let f=try Fixture(p,hash)
   f.memory.beforeObjectAllocation={r in if let bytes=f.host.bytes(r.context.esp+delta,count:4) {bytes.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}}}
   record("source allocation stack word \(delta) tampering rejected before allocation",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  for mode in ["size","receiver","actor","continuation","constructor"] {
   let f=try Fixture(p,hash);var injected=false
   f.inject={c in if !injected && c.function==(mode=="size" ? 0x4f63ec:0x486f50) {injected=true;var wrong=c
    if mode=="size" {wrong.arguments.0=0x43f};if mode=="receiver" {wrong.receiver &+= 4};if mode=="actor" {wrong.arguments.0 &+= 4};if mode=="continuation" {wrong.sourceReturnPC=0x486ee9};if mode=="constructor" {wrong.function=0x437a90}
    _=f.host.callNativeDependency(wrong)
   }};record("reentrant wrong \(mode) request rejected",failed(f) && injected)
  }
  for offset:UInt32 in [8,0x0c,0x10] {
   let f=try Fixture(p,hash);var corrupted=false
   f.inject={c in if !corrupted && c.function==0x4c7970 {corrupted=true;f.put(0x61000000+offset,f.get(0x61000000+offset)+4)}}
   record("post-base helper link \(offset) corruption rejected",failed(f) && corrupted)
  }
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x4c7970 {changed=true;f.put(f.state+0x1c,0)}};record("construction command mutation rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x405000 {changed=true;f.put(0x61000000,0x50f590)}};record("initial vtable replacement rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);let first = !failed(f);f.put(f.state+0x1c,0);record("stale live helper rejected",first && failed(f))}
  for mode in ["size","receiver","actor","continuation","constructor"] {
   let f=try Fixture(p,hash);var c=ClawCall();c.function=mode=="size" ? 0x4f63ec:0x486f50;c.argumentCount=1;c.arguments.0=mode=="size" ? 0x43f:f.actor;c.receiver=mode=="size" ? 0:0x61000004;if mode=="actor" {c.arguments.0 &+= 4};if mode=="continuation" {c.sourceReturnPC=0x486ee9};if mode=="constructor" {c.function=0x437a90}
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
   record("allocation owner retained",success && f.memory.ownsObjectAllocation(token,count:0x440))
   if success {let release=f.host.retireSeagull(actor:f.actor,provider:f.memory);record("owner routed release",release && !f.memory.ownsObjectAllocation(token,count:0x440));f.put(f.state+0x1c,0);record("fresh allocation after release",!failed(f) && f.get(f.state+0x18) != token)}
  }
  do{let f=try Fixture(p,hash);let first = !failed(f);let old=f.get(f.state+0x18);let retired=f.host.retireSeagull(actor:f.actor,provider:f.memory);f.put(f.state+0x1c,0);let recreated = !failed(f);let fresh=f.get(f.state+0x18);f.put(f.state+0x18,old);f.put(f.state+0x1c,5);record("retirement recreation rejects stale helper",first && retired && recreated && fresh != old && failed(f))}
  do{let f=try Fixture(p,hash);let first = !failed(f);let retired=f.host.retireSeagull(actor:f.actor,provider:f.memory);record("double retirement rejected",first && retired && !f.host.retireSeagull(actor:f.actor,provider:f.memory))}
  do{let f=try Fixture(p,hash);let first = !failed(f);let token=f.get(f.state+0x18);let following=f.heap.allocate(bytes:16);record("shared scene cursor advanced by exact extent",first && following==token+0x440)}
  for mode in ["actor","logic","helper","vtable"] {
   let f=try Fixture(p,hash);let first = !failed(f);let helper=f.get(f.state+0x18)
   if mode=="actor" {f.put(f.actor+0x6c,f.state+4)}
   if mode=="logic" {f.put(f.state+0x10,0x486e91)}
   if mode=="helper" {f.heap.free(helper);_=f.heap.storeBytes(token:helper,count:0x440)}
   if mode=="vtable" {f.put(helper,0x50f590)}
   f.put(f.state+0x1c,5);record("lifecycle stale \(mode) rejected",first && failed(f))
  }
  for mode in ["size","version","input","output","preserve","esp","eip","receiver","return","fsHead"] {
   let f=try Fixture(p,hash);let first = !failed(f);var changed=false
   f.inject={c in if !changed && c.function==0x4873a0,let context=c.sourceContext {changed=true
    if mode=="size" {context.pointee.size=0};if mode=="version" {context.pointee.version=2};if mode=="input" {context.pointee.inputMask=0};if mode=="output" {context.pointee.outputMask=0};if mode=="preserve" {context.pointee.preserveMask=0};if mode=="esp" {context.pointee.esp &+= 4};if mode=="eip" {context.pointee.eip &+= 1};if mode=="receiver" {context.pointee.ecx &+= 4};if mode=="fsHead" {context.pointee.fsHead=0};if mode=="return",let bytes=f.host.bytes(c.stackPointer,count:4) {bytes.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}}
   }};f.put(f.state+0x1c,5);record("malformed lifecycle source \(mode) rejected",first && failed(f) && changed)
  }
  for mode in ["size","version","input","output","preserve","esp","eip","receiver","return","fsHead"] {
   let f=try Fixture(p,hash);let first = !failed(f);var changed=false
   f.inject={c in if !changed && c.function==0x4879a0,let context=c.sourceContext {changed=true
    if mode=="size" {context.pointee.size=0};if mode=="version" {context.pointee.version=2};if mode=="input" {context.pointee.inputMask=0};if mode=="output" {context.pointee.outputMask=0};if mode=="preserve" {context.pointee.preserveMask=0};if mode=="esp" {context.pointee.esp &+= 4};if mode=="eip" {context.pointee.eip &+= 1};if mode=="receiver" {context.pointee.ecx &+= 4};if mode=="fsHead" {context.pointee.fsHead=0};if mode=="return",let bytes=f.host.bytes(c.stackPointer,count:4) {bytes.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}}
   }};f.put(f.state+0x1c,5);record("malformed patrol source \(mode) rejected",first && failed(f) && changed)
  }
  for mode in ["control","count","pop","returned"] {
   let f=try Fixture(p,hash);var changed=false
   f.inject={c in if !changed && c.function==0x4332f0,let exact=c.x87State {changed=true;if mode=="control" {exact.pointee.control=0};if mode=="count" {exact.pointee.count=9};if mode=="pop" {exact.pointee.popCount=1};if mode=="returned" {exact.pointee.returned=1}}}
   record("malformed constructor exact x87 \(mode) rejected",failed(f) && changed)
  }
  for mode in ["control","count","pop","push","returned","operation","receiver","delta","stack","rate"] {
   let f=try Fixture(p,hash);let first = !failed(f);var changed=false
   f.inject={c in if !changed && c.function==0x4c82a0,let exact=c.x87State {changed=true
    if mode=="rate" {f.put(c.receiver+0x28,0x3f000000)};if mode=="control" {exact.pointee.control=0};if mode=="count" {exact.pointee.count=9};if mode=="pop" {exact.pointee.popCount=1};if mode=="push" {exact.pointee.pushCount=1};if mode=="returned" {exact.pointee.returned=1}
    if ["operation","receiver","delta","stack"].contains(mode) {var wrong=c
     if mode=="operation" {wrong.x87Operation=1};if mode=="receiver" {wrong.receiver &+= 4};if mode=="delta" {wrong.arguments.0 &+= 1};if mode=="stack" {wrong.stackPointer=UInt32(CLAW_STACK_TOP)}
     _=f.host.callNativeDependency(wrong)
    }
   }};f.put(f.state+0x1c,5);record("malformed animation exact \(mode) rejected",first && failed(f) && changed)
  }
  do{let f=try Fixture(p,hash);let first = !failed(f);let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.map{($0,f.get($0))});let foreign=try ClawNativeMfcMemory(host:f.host,sha256:hash,importTargets:imports,allocationBase:0x62000000,sceneObjectAllocations:true);f.put(f.state+0x1c,5);let result=f.host.withObjectAllocation(provider:foreign){f.host.invoke(f.call())};record("foreign provider on same host rejected",first && result?.completed != true && f.host.fault != nil)}
  do{let f=try Fixture(p,hash);let first = !failed(f);let helper=f.get(f.state+0x18);let foreign=f.heap.allocate(bytes:0x440);if let src=f.heap.lookupBytes(helper,count:0x440),let dst=f.heap.lookupBytes(foreign,count:0x440) {dst.update(from:src,count:0x440)};f.put(f.state+0x18,foreign);f.put(f.state+0x1c,5);record("foreign helper allocation rejected",first && failed(f))}
  let result:[String:Any]=["profiles":output,"controls":controls];try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"));print("native profiles \(output.count), controls \(controls.count)")
 }
}
