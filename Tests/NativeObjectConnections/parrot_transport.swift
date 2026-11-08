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
 var sourceObservations:[[String:Any]]=[];var freeRequests:[[UInt32]]=[];var frames:[[String:Any]]=[];var allocationRequests:[[UInt32]]=[];var invalidBacking=false;var failBitsetAllocation=false;var retiredBytes="";var allocationWitness=false;var events:[[Any]]=[];var calls:[[Any]]=[];var missing:UInt32?;var inject:((ClawCall)->Void)?
 init(_ p:[String:Any],_ hash:String)throws {
  self.p=p
  for b in p["initial"] as! [[String:Any]] {let d=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(d.count)).update(from:d,count:d.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
  let storage=heap;let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().map{k in(k,storage.lookup(k,words:1)![0])})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:0x61000000,sceneObjectAllocations:true)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in
   self.calls.append([c.function,c.receiver,args(c)])
   if c.function==0x4f6428 && c.arguments.0==self.get(self.state+0x18) {self.retiredBytes=self.hex(c.arguments.0,0x450)}
   if [UInt32(0x4dbe10),0x4dbd60].contains(c.function) {self.frames.append(["function":c.function,"receiver":c.receiver,"caller_frame":c.sourceContext?.pointee.ebp ?? 0,"continuation":c.sourceReturnPC])}
   if c.function==0x4f6428 {let token=c.arguments.0;let count:UInt32=[UInt32(0x450),0x174,16].first{self.memory.ownsObjectAllocation(token,count:$0)} ?? 0;self.freeRequests.append([token,count]);self.events.append(["free",token])}
   self.inject?(c)
  }
  memory.beforeObjectAllocation={ [unowned self] r in let offset=Int(r.context.esp-UInt32(CLAW_STACK_BASE)+0x14);self.allocationRequests.append([r.root,r.count,r.returnPC,r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)}]);if r.count==0x450 {self.allocationWitness=r.root==0x465580 && r.count==0x450 && r.returnPC==0x4f63ff && r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)}==0x4655bd}}
  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]])}}
 }
 var actor:UInt32 {u(p["actor"]!)};var state:UInt32 {u(p["state"]!)}
 func get(_ a:UInt32)->UInt32 {guard let p=heap.lookup(a,words:1) else {invalidBacking=true;return 0};return p[0]}
 func put(_ a:UInt32,_ v:UInt32){guard let p=heap.lookup(a,words:1) else {invalidBacking=true;return};p[0]=v}
 func string(_ a:UInt32)->String? {var bytes:[UInt8]=[];for i:UInt32 in 0..<256 {guard let p=host.bytes(a+i,count:1) else{return nil};if p[0]==0{return String(bytes:bytes,encoding:.ascii)};bytes.append(p[0])};return nil}
 func service(_ c:ClawCall)->UInt32? {
  let a=args(c);var f=c.function
  for slot:UInt32 in [0x546d5c,0x546cdc,0x5469e8,0x546cd4,0x546d24] {if get(slot)==f {f=slot}}
  if missing==f{return nil}
  switch f {
  case 0x4a48e0:
   guard failBitsetAllocation,c.receiver==0,a==[8] else{return nil};return 0
  case 0x4f6974:
   guard a==[0],let value=heap.lookup(c.receiver,words:1)?[0],string(value) != nil else{return nil};return value
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
  case 0x546d24:
   guard a.count==3,let rect=host.bytes(a[0],count:16) else{return nil}
   var values=(0..<4).map{UnsafeRawPointer(rect.advanced(by:$0*4)).loadUnaligned(as:Int32.self)}
   let dx=Int32(bitPattern:a[1]),dy=Int32(bitPattern:a[2]);values[0] &-= dx;values[1] &-= dy;values[2] &+= dx;values[3] &+= dy
   for i in 0..<4 {var v=values[i].littleEndian;withUnsafeBytes(of:&v){UnsafeMutableRawPointer(rect.advanced(by:i*4)).copyMemory(from:$0.baseAddress!,byteCount:4)}}
   events.append(["inflate-rectangle",a[0],dx,dy]);return 1
  case 0x546cd4:
   guard a.count==3,let rect=host.bytes(a[0],count:16) else{return nil}
   let values=(0..<4).map{UnsafeRawPointer(rect.advanced(by:$0*4)).loadUnaligned(as:Int32.self)}
   let x=Int32(bitPattern:a[1]),y=Int32(bitPattern:a[2]);let result:UInt32=values[0]<=x && x<values[2] && values[1]<=y && y<values[3] ? 1:0
   events.append(["point-in-rectangle",a[0],x,y,result]);return result
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
   guard c.receiver==0,a.count==2,let left=string(a[0]),let right=string(a[1]) else{return nil}
   let l=Array(left.utf8),r=Array(right.utf8);var i=0
   while i<l.count && i<r.count && l[i]==r[i] {i+=1}
   return UInt32(bitPattern:Int32(i<l.count ? l[i]:0)-Int32(i<r.count ? r[i]:0))
  case 0x4a3050:events.append(["rand",99]);return 99
  default:return nil
  }
 }
 func call()->ClawCall {var c=ClawCall();c.function=0x465580;c.argumentCount=1;c.arguments.0=actor;return c}
 func hex(_ a:UInt32,_ n:UInt32)->String {heap.lookupBytes(a,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing"}
 func execute(_ command:UInt32,_ outgoing:inout ClawX87State)->Bool {
  put(state+0x1c,command)
  
  var completion:ClawNativeCanonicalHost.Completion?
  _=host.withObjectAllocation(provider:memory){if let r=host.withObjectX87Environment(outgoing,body:{host.invoke(call())}) {completion=r.0;outgoing=r.1}}
  if command==0 {sourceObservations=host.parrotMemberSources.map {o in ["function":o.function,"input_receiver":o.input.ecx,"return_pc":o.returnPC,"output_eax":o.output.eax,"stack_delta":o.output.esp-o.input.esp,"fs_preserved":o.input.fsHead==o.output.fsHead,"nonvolatiles":[o.input.ebx,o.input.esi,o.input.edi,o.input.ebp],"preserved":[o.input.ebx,o.input.esi,o.input.edi,o.input.ebp]==[o.output.ebx,o.output.esi,o.output.edi,o.output.ebp]]}}
  if command==0 {frames=host.parrotCallerFrames.map{["function":$0.function,"receiver":$0.receiver,"caller_frame":$0.callerFrame,"continuation":$0.returnPC]}}
  return completion?.completed==true && host.fault==nil && !invalidBacking
 }
 func construct()->Bool {var outgoing=fp(p["incoming"] as! [Any]);return execute(0,&outgoing)}
 func stringRetirement(_ spec:[String:Any])->[String:Any] {
  let name=spec["name"] as! String,references=u(spec["references"]!),members=spec["members"] as! [NSNumber]
  guard construct() else{return["name":name,"failure":"construction"]}
  var c=ClawCall();c.function=0x546aa8;c.stackPointer=UInt32(CLAW_STACK_TOP);c.argumentCount=2;c.arguments.0=0;c.arguments.1=16
  guard let token=memory.service(c),token != 0 else{return["name":name,"failure":"allocation"]}
  put(token,references);put(token+4,3);put(token+8,3);put(token+12,0x00636261)
  for offset in members {put(0x61000000+offset.uint32Value,token+12)}
  let retired=host.retireParrot(actor:actor,provider:memory,retireSecondary:true)
  let bytes=memory.tlsSnapshot().allocationBytes[String(token)]?.map{String(format:"%02x",$0)}.joined() ?? "missing"
  return["name":name,"references":references,"members":members,"token":token,"bytes":bytes,"freed":!memory.ownsObjectAllocation(token,count:16),"helper_freed":retired && !memory.ownsObjectAllocation(0x61000000,count:0x450),"helper_bytes":retiredBytes]
 }
 func run()->[String:Any] {
  var outgoing=fp(p["incoming"] as! [Any]);var completed=true;var snapshots:[[[String:Any]]]=[];var x87Snapshots:[[Any]]=[]
  let shapes=p["snapshots"] as! [[[String:Any]]]
  for (index,command) in (p["commands"] as! [NSNumber]).enumerated() {
   if !execute(command.uint32Value,&outgoing) {completed=false;break}
   x87Snapshots.append(fpJSON(outgoing))
   snapshots.append(shapes[index].map {b in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);return["address":a,"data":hex(a,n)]})
  }
  var retired=false
  if completed,let result=host.withObjectX87Environment(outgoing,body:{host.retireParrot(actor:actor,provider:memory,retireSecondary:true)}) {retired=result.0;outgoing=result.1}
  let released=retired && freeRequests.count==3 && freeRequests.allSatisfy{$0[1]>0 && !memory.ownsObjectAllocation($0[0],count:$0[1])}
  return["label":p["label"]!,"allocation_witness":allocationWitness,"completed":completed,"fault":host.fault.map{String(describing:$0)} ?? "none","outgoing":fpJSON(outgoing),"events":events,"calls":calls,"snapshots":snapshots,"x87_snapshots":x87Snapshots,"retired":released,"free_requests":freeRequests,"retired_bytes":retiredBytes,"frames":frames,"allocation_requests":allocationRequests,"source_observations":sourceObservations]
 }
}

@main struct ParrotTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]);let ref=try JSONSerialization.jsonObject(with:Data(contentsOf:dir.appendingPathComponent("reference.json"))) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  var output:[[String:Any]]=[];for p in profiles{output.append(try Fixture(p,hash).run())}
  var controls:[[String:Any]]=[]
  func record(_ n:String,_ ok:Bool){controls.append(["name":n,"passed":ok])}
  func failed(_ f:Fixture)->Bool {!f.construct()}
  do{let f=try Fixture(p,hash);record("provider required",!f.host.invoke(f.call()).completed && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);record("foreign provider rejected",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(f.call())}==nil)}
  do{let f=try Fixture(p,hash);f.put(f.state+0x10,0x465581);record("wrong callback rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.put(f.actor+0x6c,UInt32.max);record("wrong actor state rejected",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x4f6286;record("missing registry fails",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x546d5c;record("missing rectangle fails",failed(f))}
  do{let f=try Fixture(p,hash);f.memory.failAllocation={$0==0x4a48e0};record("allocation exhaustion preserved",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil && f.host.fault?.address==0x5022b5)}
  do{let f=try Fixture(p,hash);let bytes=f.heap.storeBytes(token:0x61000000,count:0x450);bytes.update(repeating:0xa7,count:0x450);record("occupied allocation preserved",failed(f) && UnsafeBufferPointer(start:bytes,count:0x450).allSatisfy{$0==0xa7})}
  do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={_ in f.heap.free(0x10000000);_=f.heap.storeBytes(token:0x10000000,count:0x10000)};record("actor identity replacement rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.memory.afterService={slot,_,token in if slot==0x4a48e0 && token != 0 {f.heap.free(token);_=f.heap.storeBytes(token:token,count:0x450)}};record("allocation identity replacement rejected",failed(f))}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(f.call())};record("physical service reentry rejected",failed(f) && nested?.completed==false)}
  for delta:UInt32 in [0,4,0x14,0x18] {
   let f=try Fixture(p,hash)
   f.memory.beforeObjectAllocation={r in if let bytes=f.host.bytes(r.context.esp+delta,count:4) {bytes.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}}}
   record("source allocation stack word \(delta) tampering rejected before allocation",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  for mode in ["size","receiver","actor","continuation"] {
   let f=try Fixture(p,hash);var injected=false
   f.inject={c in if !injected && c.function==(mode=="size" ? 0x4f63ec:0x465640) {injected=true;var wrong=c
    if mode=="size" {wrong.arguments.0=0x44f};if mode=="receiver" {wrong.receiver &+= 4};if mode=="actor" {wrong.arguments.0 &+= 4};if mode=="continuation" {wrong.sourceReturnPC=0x4655d9}
    _=f.host.callNativeDependency(wrong)
   }};record("reentrant wrong \(mode) request rejected",failed(f) && injected)
  }
  for offset:UInt32 in [8,0x0c,0x10] {
   let f=try Fixture(p,hash);var corrupted=false
   f.inject={c in if !corrupted && c.function==0x4c7970 {corrupted=true;f.put(0x61000000+offset,f.get(0x61000000+offset)+4)}}
   record("post-base helper link \(offset) corruption rejected",failed(f) && corrupted)
  }
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x4c7970 {changed=true;f.put(f.state+0x1c,0)}};record("construction command mutation rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x405000 {changed=true;f.put(0x61000000,0x50ec70)}};record("initial vtable replacement rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);let first = !failed(f);f.put(f.state+0x1c,0);record("stale live helper rejected",first && failed(f))}
  for mode in ["size","receiver","actor","continuation"] {
   let f=try Fixture(p,hash);var c=ClawCall();c.function=mode=="size" ? 0x4f63ec:0x465640;c.argumentCount=1;c.arguments.0=mode=="size" ? 0x44f:f.actor;c.receiver=mode=="size" ? 0:0x61000004;if mode=="actor" {c.arguments.0 &+= 4};if mode=="continuation" {c.sourceReturnPC=0x4655d9}
   _=f.host.withObjectAllocation(provider:f.memory){f.host.callNativeDependency(c)}
   record("out-of-context \(mode) request rejected before allocation",f.host.fault != nil && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  do{let f=try Fixture(p,hash);var state=fp(p["incoming"] as! [Any]);state.control=0x27f;_=f.host.withObjectAllocation(provider:f.memory){f.host.withObjectX87Environment(state,body:{f.host.invoke(f.call())})};record("unsupported x87 CW rejected",f.host.fault != nil && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  for mode in ["cw","count","reserved","version","entry","status","pop","push","returned","eax","unused-slot","slot-reserved"] {
   let f=try Fixture(p,hash);var state=fp(p["incoming"] as! [Any]);if mode=="cw" {state.control=0};if mode=="count" {state.count=9};if mode=="reserved" {state.reserved0=1};if mode=="version" {state.version=2};if mode=="status" {state.status=0x10000};if mode=="pop" {state.popCount=1};if mode=="push" {state.pushCount=1};if mode=="returned" {state.returned=1};if mode=="eax" {state.eax=1};if mode=="unused-slot" {state.slots.7.significand=1};if mode=="slot-reserved" {state.slots.0.reserved=1}
   if mode=="entry" {var c=ClawCall();c.function=0x44bc60;c.x87ArgumentCount=UInt32(CLAW_X87_ENTRY);withUnsafeMutablePointer(to:&state){c.x87State=$0;_=f.host.callNativeDependency(c)};record("unelected entry rejected",f.host.fault != nil)}
   else {let r=f.host.withObjectX87Environment(state,body:{f.host.invoke(f.call())});record("malformed x87 \(mode) rejected",r==nil && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  }
  for offset:UInt32 in [0,4,8,12,16,28,32,36] {
   let f=try Fixture(p,hash);f.put(0x50ec6c+offset,offset==16 ? 0x465640:0x405000)
   record("vtable slot \(offset) replacement rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  do{let f=try Fixture(p,hash);let ready=f.construct();let helper=f.get(f.state+0x18)
   record("allocation owner retained",ready && f.memory.ownsObjectAllocation(helper,count:0x450))
   let retired=ready && f.host.retireParrot(actor:f.actor,provider:f.memory,retireSecondary:true)
   record("same-owner retirement",retired && !f.memory.ownsObjectAllocation(helper,count:0x450) && f.get(f.actor+0x70)==0 && f.get(f.actor+0x78)==0)
   record("recreation uses fresh helper",retired && f.construct() && f.get(f.state+0x18) != helper)
   f.put(f.state+0x18,helper);var x=fp(p["incoming"] as! [Any]);record("stale helper after recreation rejected",!f.execute(1000,&x))
  }
  do{let f=try Fixture(p,hash);let ready=f.construct();let retired=ready && f.host.retireParrot(actor:f.actor,provider:f.memory,retireSecondary:true);record("double retirement rejected",retired && !f.host.retireParrot(actor:f.actor,provider:f.memory,retireSecondary:true));record("double physical free rejected",retired && !f.memory.releaseSceneObject(0x61000000))}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);let ready=f.construct();record("foreign retirement provider rejected",ready && !f.host.retireParrot(actor:f.actor,provider:other.memory,retireSecondary:true))}
  do{let f=try Fixture(p,hash);let ready=f.construct();let helper=f.get(f.state+0x18);f.heap.free(helper);_=f.heap.storeBytes(token:helper,count:0x450);var x=fp(p["incoming"] as! [Any]);record("stale helper identity rejected",ready && !f.execute(1000,&x))}
  do{let f=try Fixture(p,hash);var captured:ClawNativeCanonicalHost.ObjectAllocationRequest?;f.memory.beforeObjectAllocation={captured=$0};let ready=f.construct();let before=f.heap.debugAllocationBases;let duplicate=captured.flatMap{f.memory.allocateObject($0)};record("duplicate allocation request rejected",ready && duplicate==nil && f.heap.debugAllocationBases==before)}
  do{let f=try Fixture(p,hash);let ready=f.construct();f.put(f.get(f.state+0x18),0x50ec70);var x=fp(p["incoming"] as! [Any]);record("live vtable replacement rejected",ready && !f.execute(29,&x))}
  do{let f=try Fixture(p,hash);let ready=f.construct();let bytes=Array(UnsafeBufferPointer(start:f.heap.lookupBytes(0x10000000,count:0x10000)!,count:0x10000));f.heap.free(0x10000000);f.heap.storeBytes(token:0x10000000,count:0x10000).update(from:bytes,count:bytes.count);var x=fp(p["incoming"] as! [Any]);record("retained actor identity replacement rejected",ready && !f.execute(1000,&x))}
  do{let f=try Fixture(p,hash);record("foreign physical free rejected",!f.memory.releaseSceneObject(f.actor))}
  do{let f=try Fixture(p,hash);let ready=f.construct();f.put(f.get(0x537c40),0x465640);var x=fp(p["incoming"] as! [Any]);record("foreign state callback rejected",ready && !f.execute(5,&x))}
  do{let f=try Fixture(p,hash);var seen=false;f.inject={c in if c.function==0x4c7970 && !seen {seen=true;_=f.memory.releaseSceneObject(0x61000000)}};record("physical free during construction rejected",failed(f) && seen)}
  for key in ["LogicHit","LogicAttack"] {
   let f=try Fixture(p,hash);let managers=(p["events"] as! [[Any]]).filter{($0[0] as? String)=="lookup" && ($0[2] as? String)==key};let registry=u(managers[0][1]);var node=f.get(f.get(registry+4))
   while node != 0 {if f.string(f.get(node+8))==key {f.put(node+12,0);break};node=f.get(node)}
   record("missing \(key) metadata rejected",failed(f))
  }
  for target:UInt32 in [0x465cc0,0x465ce0] {
   let f=try Fixture(p,hash);let ready=f.construct();var c=ClawCall();c.function=target;c.receiver=f.get(f.state+0x18);c.argumentCount=target==0x465cc0 ? 1:0;c.arguments.0=1
   record("direct destructor \(String(target,radix:16)) bypass rejected",ready && !f.host.invoke(c).completed)
  }
  do{let f=try Fixture(p,hash);f.failBitsetAllocation=true;f.inject={c in if c.function==0x4dbe10 {f.put(0x533470,64)}}
   let refused = !f.construct();let source=f.host.parrotMemberSources.last
   record("bitset caller frame supplies diagnostic",refused && source?.function==0x4dc680 && source?.returnPC==0x4dbf9f && source?.input.ebp==0x61000128 && source?.output.eax==f.actor)
  }
  do{let f=try Fixture(p,hash);var c=ClawCall();c.function=0x4dc680
   _=f.host.withObjectAllocation(provider:f.memory){f.host.callNativeDependency(c)}
   record("foreign bitset caller frame rejected",f.host.fault != nil)
  }
  do{let f=try Fixture(p,hash);let prior=f.heap.allocateSceneObject(bytes:0x174,minimumToken:0x61000000)
   record("shared scene allocation cursor retained",prior==0x61000000 && f.construct() && f.get(f.state+0x18)==0x61000180 && f.heap.lookupBytes(prior,count:0x174) != nil)
  }
  do{let f=try Fixture(p,hash);let ready=f.construct();f.missing=0x4a3810;var x=fp(p["incoming"] as! [Any]);record("missing lifecycle physical service rejected",ready && !f.execute(5,&x))}
  var stringRetirements:[[String:Any]]=[];for spec in ref["string_retirements"] as! [[String:Any]] {stringRetirements.append(try Fixture(p,hash).stringRetirement(spec))}
  let result:[String:Any]=["profiles":output,"controls":controls,"string_retirements":stringRetirements];try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"));print("native profiles \(output.count), controls \(controls.count)")
 }
}
