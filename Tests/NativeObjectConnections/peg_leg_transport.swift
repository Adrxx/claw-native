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
 var lastRequested:UInt32=0;var memberSource:[[String:Any]]=[];var invalidBacking=false;var contexts:[[Any]]=[];var retiredBytes="";var retiredSecondaryBytes:[[String:Any]]=[];var allocationWitness=false;var secondaryWitnesses:[UInt32]=[];var events:[[Any]]=[];var calls:[[Any]]=[];var missing:UInt32?;var inject:((ClawCall)->Void)?
 init(_ p:[String:Any],_ hash:String,allocationBase:UInt32=0x61000000,sceneObjectAllocations:Bool=true)throws {
  self.p=p
  for b in p["initial"] as! [[String:Any]] {let d=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(d.count)).update(from:d,count:d.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
  let storage=heap;let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().map{k in(k,storage.lookup(k,words:1)![0])})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:allocationBase,sceneObjectAllocations:sceneObjectAllocations)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in self.calls.append([c.function,c.receiver,args(c)]);if c.function==0x4f6428 && self.memory.ownsObjectAllocation(c.arguments.0,count:0x4e8) {self.retiredBytes=self.hex(c.arguments.0,0x4e8)};if c.function==0x4f6428 && self.memory.ownsObjectAllocation(c.arguments.0,count:0x174) {self.retiredSecondaryBytes.append(["address":c.arguments.0,"data":self.hex(c.arguments.0,0x174)])};self.inject?(c)}
  memory.beforeObjectAllocation={ [unowned self] r in self.lastRequested=r.count;let offset=Int(r.context.esp-UInt32(CLAW_STACK_BASE)+0x14);let continuation=r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)};if r.count==0x4e8 {self.allocationWitness=r.root==0x4689b0 && r.returnPC==0x4f63ff && continuation==0x4689ed};if r.count==0x174 && r.returnPC==0x4f63ff && ((r.root==0x4c7fa0 && continuation==0x4c7f4f) || (r.root==0x4c8060 && continuation==0x4c800f)) {self.secondaryWitnesses.append(continuation)}}
  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]])}}
 }
 var actor:UInt32 {u(p["actor"]!)};var state:UInt32 {u(p["state"]!)}
 func get(_ a:UInt32)->UInt32 {guard let p=heap.lookup(a,words:1) else {invalidBacking=true;return 0};return p[0]}
 func put(_ a:UInt32,_ v:UInt32){guard let p=heap.lookup(a,words:1) else {invalidBacking=true;return};p[0]=v}
 func string(_ a:UInt32)->String? {var bytes:[UInt8]=[];for i:UInt32 in 0..<256 {guard let p=host.bytes(a+i,count:1) else{return nil};if p[0]==0{return String(bytes:bytes,encoding:.ascii)};bytes.append(p[0])};return nil}
 func service(_ c:ClawCall)->UInt32? {
  let a=args(c);var f=c.function
  for slot:UInt32 in [0x546d5c,0x546cdc,0x5469e8,0x546cd4] {if get(slot)==f {f=slot}}
  if missing==f{return nil}
  switch f {
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
  case 0x4a3050:events.append(["rand",99]);return 99
  default:return nil
  }
 }
 func call()->ClawCall {var c=ClawCall();c.function=0x4689b0;c.argumentCount=1;c.arguments.0=actor;return c}
 func hex(_ a:UInt32,_ n:UInt32)->String {heap.lookupBytes(a,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing"}
 func execute(_ command:UInt32,_ outgoing:inout ClawX87State)->Bool {
  put(state+0x1c,command)
  if command==6 {put(0x537210,100);put(0x5430c4,0);put(actor+0xcc,7);put(get(state+0x18)+0x4cc,1)}
  var completion:ClawNativeCanonicalHost.Completion?
  _=host.withObjectAllocation(provider:memory){if let r=host.withObjectX87Environment(outgoing,body:{host.invoke(call())}) {completion=r.0;outgoing=r.1}}
  if command==0 && completion?.completed==true && host.fault==nil {
   for observation in host.pegLegMemberSources {
    let input=observation.input,output=observation.output
    let preserved=input.ebx==output.ebx && input.esi==output.esi && input.edi==output.edi && input.ebp==output.ebp && input.fsHead==output.fsHead
    memberSource.append(["function":observation.function,"receiver":input.ecx,"return_pc":observation.returnPC,"eax":output.eax,"stack_delta":Int64(output.esp)-Int64(input.esp),"preserved":preserved])
   }
  }
  return completion?.completed==true && host.fault==nil && !invalidBacking
 }
 func construct()->Bool {var outgoing=fp(p["incoming"] as! [Any]);return execute(0,&outgoing)}
 func run()->[String:Any] {
  var outgoing=fp(p["incoming"] as! [Any]);var completed=true;var snapshots:[[[String:Any]]]=[];var x87Snapshots:[[Any]]=[]
  let shapes=p["snapshots"] as! [[[String:Any]]]
  for (index,command) in (p["commands"] as! [NSNumber]).enumerated() {
   if index==1 {let helper=get(state+0x18);guard host.retirePegLeg(actor:actor,provider:memory) else{completed=false;break};events.append(["free",helper])}
   if !execute(command.uint32Value,&outgoing) {completed=false;break}
   x87Snapshots.append(fpJSON(outgoing))
   snapshots.append(shapes[index].map {b in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);return["address":a,"data":hex(a,n)]})
  }
  let helper=get(state+0x18),hit=get(actor+0x70),attack=get(actor+0x78)
  let retired=completed && host.retirePegLeg(actor:actor,provider:memory,retireSecondary:true)
  if retired {for token in [helper,hit,attack] {events.append(["free",token])}}
  let finalSnapshots=(p["final_snapshots"] as! [[String:Any]]).map {b in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);return["address":a,"data":hex(a,n)] as [String:Any]}
  return["member_source":memberSource,"label":p["label"]!,"allocation_witness":allocationWitness,"secondary_witnesses":secondaryWitnesses,"completed":completed,"fault":host.fault.map{String(describing:$0)} ?? "none","outgoing":fpJSON(outgoing),"events":events,"calls":calls,"contexts":contexts,"snapshots":snapshots,"x87_snapshots":x87Snapshots,"retired":retired,"retired_bytes":retiredBytes,"retired_secondary_bytes":retiredSecondaryBytes,"final_snapshots":finalSnapshots]
 }
}

@main struct PegLegTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]);let ref=try JSONSerialization.jsonObject(with:Data(contentsOf:dir.appendingPathComponent("reference.json"))) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  var output:[[String:Any]]=[];for p in profiles{output.append(try Fixture(p,hash).run())}
  var controls:[[String:Any]]=[];var allocationFailure:[String:Any]=[:]
  func record(_ n:String,_ ok:Bool){controls.append(["name":n,"passed":ok])}
  func failed(_ f:Fixture)->Bool {!f.construct()}
  do {
   let f=try Fixture(p,hash,allocationBase:0x67800000)
   let ready=f.construct(),helper=f.get(f.state+0x18)
   let ordinary=f.heap.allocate(bytes:0x1b4),identity=f.heap.allocationIdentity(at:ordinary,count:0x1b4)
   let retired=ready && f.host.retirePegLeg(actor:f.actor,provider:f.memory)
   record("scene interleaving retires exact helper",retired && !f.memory.ownsObjectAllocation(helper,count:0x4e8) && f.heap.lookupBytes(helper,count:1)==nil)
   record("scene interleaving advances shared cursor",retired && f.construct() && f.get(f.state+0x18)>=ordinary+0x1b4 && f.heap.allocationIdentity(at:ordinary,count:0x1b4) === identity)
  }
  do{let f=try Fixture(p,hash);record("provider required",!f.host.invoke(f.call()).completed && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);record("foreign provider rejected",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(f.call())}==nil)}
  do{let f=try Fixture(p,hash);f.put(f.state+0x10,0x4968d1);record("wrong callback rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.put(f.actor+0x6c,UInt32.max);record("wrong actor state rejected",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x4f6286;record("missing registry fails",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x546d5c;record("missing rectangle fails",failed(f))}
  do{let f=try Fixture(p,hash);f.memory.failAllocation={$0==0x4a48e0};record("allocation exhaustion preserved",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil);allocationFailure=["requested":f.lastRequested,"target":f.host.fault?.address ?? 0,"event":f.get(f.state+0x1c),"helper":f.get(f.state+0x18)]}
  do{let f=try Fixture(p,hash);let bytes=f.heap.storeBytes(token:0x61000000,count:0x4e8);bytes.update(repeating:0xa7,count:0x4e8);record("occupied allocation preserved",failed(f) && UnsafeBufferPointer(start:bytes,count:0x4e8).allSatisfy{$0==0xa7})}
  do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={_ in f.heap.free(0x10000000);_=f.heap.storeBytes(token:0x10000000,count:0x10000)};record("actor identity replacement rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.memory.afterService={slot,_,token in if slot==0x4a48e0 && token != 0 {f.heap.free(token);_=f.heap.storeBytes(token:token,count:0x4e8)}};record("allocation identity replacement rejected",failed(f))}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(f.call())};record("physical service reentry rejected",failed(f) && nested?.completed==false)}
  do{let f=try Fixture(p,hash);var c=f.call();c.function=0x496050;var completed=false
   _=f.host.withObjectAllocation(provider:f.memory){if let r=f.host.withObjectX87Environment(fp(p["incoming"] as! [Any]),body:{f.host.invoke(c)}) {completed=r.0.completed}}
   record("foreign guard root rejected",!completed && f.host.fault != nil && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  do{let f=try Fixture(p,hash);var changed=false
   f.inject={c in if !changed && c.function==0x468eb0 {changed=true;var wrong=c;wrong.function=0x496110;_=f.host.callNativeDependency(wrong)}}
   record("foreign constructor rejected",failed(f) && changed)
  }
  for offset:UInt32 in [0,4,8,12,16,28,32,36] {
   let f=try Fixture(p,hash);f.put(0x50ed1c+offset,0x405000)
   if offset==16 {f.put(0x50ed1c+offset,0x496110)}
   record("vtable slot \(offset) replacement rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  for delta:UInt32 in [0,4,0x14,0x18] {
   let f=try Fixture(p,hash)
   f.memory.beforeObjectAllocation={r in if let bytes=f.host.bytes(r.context.esp+delta,count:4) {bytes.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}}}
   record("source allocation stack word \(delta) tampering rejected before allocation",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  for mode in ["size","receiver","actor","continuation"] {
   let f=try Fixture(p,hash);var injected=false
   f.inject={c in if !injected && c.function==(mode=="size" ? 0x4f63ec:0x468eb0) {injected=true;var wrong=c
    if mode=="size" {wrong.arguments.0=0x4e7};if mode=="receiver" {wrong.receiver &+= 4};if mode=="actor" {wrong.arguments.0 &+= 4};if mode=="continuation" {wrong.sourceReturnPC=0x468a09}
    _=f.host.callNativeDependency(wrong)
   }};record("reentrant wrong \(mode) request rejected",failed(f) && injected)
  }
  for offset:UInt32 in [8,0x0c,0x10] {
   let f=try Fixture(p,hash);var corrupted=false
   f.inject={c in if !corrupted && c.function==0x4c7970 {corrupted=true;f.put(0x61000000+offset,f.get(0x61000000+offset)+4)}}
   record("post-base helper link \(offset) corruption rejected",failed(f) && corrupted)
  }
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x4c7970 {changed=true;f.put(f.state+0x1c,0)}};record("construction command mutation rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x405000 {changed=true;f.put(0x61000000,0x50ed20)}};record("initial vtable replacement rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);let first = !failed(f);f.put(f.state+0x1c,0);record("stale live helper rejected",first && failed(f))}
  for mode in ["size","receiver","actor","continuation"] {
   let f=try Fixture(p,hash);var c=ClawCall();c.function=mode=="size" ? 0x4f63ec:0x468eb0;c.argumentCount=1;c.arguments.0=mode=="size" ? 0x4e7:f.actor;c.receiver=mode=="size" ? 0:0x61000004;if mode=="actor" {c.arguments.0 &+= 4};if mode=="continuation" {c.sourceReturnPC=0x468a09}
   _=f.host.withObjectAllocation(provider:f.memory){f.host.callNativeDependency(c)}
   record("out-of-context \(mode) request rejected before allocation",f.host.fault != nil && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  for mode in ["size","version","mask","return"] {
   let f=try Fixture(p,hash);var context=ClawSourceContext();context.size=72;context.version=1;context.inputMask=0x7ff;context.outputMask=0x7ff
   if mode=="size" {context.size=0};if mode=="version" {context.version=2};if mode=="mask" {context.inputMask=0}
   var c=ClawCall();c.function=0x4f6439;c.receiver=0x610001a4;c.sourceReturnPC=mode=="return" ? 0x44c04f:0x44c04e
   withUnsafeMutablePointer(to:&context){c.sourceContext=$0;_=f.host.withObjectAllocation(provider:f.memory){f.host.callNativeDependency(c)}}
   record("malformed source \(mode) rejected",f.host.fault != nil && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  do{let f=try Fixture(p,hash);var state=fp(p["incoming"] as! [Any]);state.control=0x27f;_=f.host.withObjectAllocation(provider:f.memory){f.host.withObjectX87Environment(state,body:{f.host.invoke(f.call())})};record("unsupported x87 CW rejected",f.host.fault != nil && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  for mode in ["cw","count","reserved","version","entry","status","pop","push","returned","eax","unused-slot","slot-reserved"] {
   let f=try Fixture(p,hash);var state=fp(p["incoming"] as! [Any]);if mode=="cw" {state.control=0};if mode=="count" {state.count=9};if mode=="reserved" {state.reserved0=1};if mode=="version" {state.version=2};if mode=="status" {state.status=0x10000};if mode=="pop" {state.popCount=1};if mode=="push" {state.pushCount=1};if mode=="returned" {state.returned=1};if mode=="eax" {state.eax=1};if mode=="unused-slot" {state.slots.7.significand=1};if mode=="slot-reserved" {state.slots.0.reserved=1}
   if mode=="entry" {var c=ClawCall();c.function=0x44c000;c.x87ArgumentCount=UInt32(CLAW_X87_ENTRY);withUnsafeMutablePointer(to:&state){c.x87State=$0;_=f.host.callNativeDependency(c)};record("unelected entry rejected",f.host.fault != nil)}
   else {let r=f.host.withObjectX87Environment(state,body:{f.host.invoke(f.call())});record("malformed x87 \(mode) rejected",r==nil && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  }
  do{let f=try Fixture(p,hash);var captured:ClawNativeCanonicalHost.ObjectAllocationRequest?;f.memory.beforeObjectAllocation={captured=$0};let success = !failed(f);let token=f.get(f.state+0x18)
   record("allocation lease expires",success && captured.map{!$0.consume(for:f.host,provider:f.memory)}==true)
   record("allocation owner retained",success && f.memory.ownsObjectAllocation(token,count:0x4e8))
   let retired=success && f.host.retirePegLeg(actor:f.actor,provider:f.memory)
   record("same-owner retirement",retired && !f.memory.ownsObjectAllocation(token,count:0x4e8))
   record("recreation uses fresh helper",retired && f.construct() && f.get(f.state+0x18) != token)
   f.put(f.state+0x18,token);var state=fp(p["incoming"] as! [Any]);record("stale helper after recreation rejected",!f.execute(1000,&state))
  }
  do{let f=try Fixture(p,hash);let ready=f.construct();record("foreign guard retirement rejected",ready && !f.host.retireTownGuard1(actor:f.actor,provider:f.memory))}
  do{let f=try Fixture(p,hash);let ready=f.construct();let bytes=Array(UnsafeBufferPointer(start:f.heap.lookupBytes(0x10000000,count:0x10000)!,count:0x10000));f.heap.free(0x10000000);f.heap.storeBytes(token:0x10000000,count:0x10000).update(from:bytes,count:bytes.count);var state=fp(p["incoming"] as! [Any]);record("retained actor identity replacement rejected",ready && !f.execute(1000,&state))}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);let ready=f.construct();f.put(f.state+0x1c,6);let result=f.host.withObjectAllocation(provider:other.memory){f.host.invoke(f.call())};record("foreign provider at lifecycle rejected",ready && result==nil)}
  do{let f=try Fixture(p,hash);let ready=f.construct() && f.host.retirePegLeg(actor:f.actor,provider:f.memory);record("double retirement rejected",ready && !f.host.retirePegLeg(actor:f.actor,provider:f.memory))}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);let ready=f.construct();record("foreign retirement provider rejected",ready && !f.host.retirePegLeg(actor:f.actor,provider:other.memory))}
  do{let f=try Fixture(p,hash);let ready=f.construct();let token=f.get(f.state+0x18);f.heap.free(token);_=f.heap.storeBytes(token:token,count:0x4e8);var state=fp(p["incoming"] as! [Any]);record("stale helper identity rejected",ready && !f.execute(1000,&state))}
  do{let f=try Fixture(p,hash);let ready=f.construct();f.put(f.actor+0x6c,f.state+0x180);var state=fp(p["incoming"] as! [Any]);record("foreign logic binding rejected",ready && !f.execute(1000,&state))}
  do{let f=try Fixture(p,hash);let ready=f.construct();f.put(f.get(f.state+0x18),0x50fabc);var state=fp(p["incoming"] as! [Any]);record("live vtable replacement rejected",ready && !f.execute(29,&state))}
  do{let f=try Fixture(p,hash);let ready=f.construct();let token=f.get(f.state+0x18);let retired=ready && f.host.retirePegLeg(actor:f.actor,provider:f.memory);record("double physical free rejected",retired && !f.memory.releaseSceneObject(token))}
  do{let f=try Fixture(p,hash);var captured:ClawNativeCanonicalHost.ObjectAllocationRequest?;f.memory.beforeObjectAllocation={captured=$0};let ready=f.construct();let before=f.heap.debugAllocationBases
   let duplicate=captured.flatMap{f.memory.allocateObject($0)}
   record("duplicate allocation request rejected",ready && duplicate==nil && f.heap.debugAllocationBases==before)
  }
  do{let f=try Fixture(p,hash);let ready=f.construct();let table=f.get(0x537c70);f.put(table+4,0x468eb0);var state=fp(p["incoming"] as! [Any]);record("foreign state callback rejected",ready && !f.execute(6,&state))}
  do{let f=try Fixture(p,hash);let ready=f.construct();f.missing=0x4f6974;var state=fp(p["incoming"] as! [Any]);record("missing CString service rejected",ready && !f.execute(6,&state))}
  for function:UInt32 in [0x469480,0x4694a0] {
   let f=try Fixture(p,hash);let ready=f.construct();let helper=f.get(f.state+0x18);let before=f.hex(helper,0x4e8)
   var c=ClawCall();c.function=function;c.receiver=helper;c.argumentCount=function==0x469480 ? 1:0;c.arguments.0=function==0x469480 ? 1:0
   let result=f.host.invoke(c)
   record("direct destructor \(String(function,radix:16)) bypass rejected",ready && !result.completed && f.hex(helper,0x4e8)==before)
  }
  do {
   let f=try Fixture(p,hash);let ready=f.construct(),hit=f.get(f.actor+0x70),attack=f.get(f.actor+0x78)
   let identities=[hit,attack].map{f.heap.allocationIdentity(at:$0,count:0x174)}
   let retired=ready && f.host.retirePegLeg(actor:f.actor,provider:f.memory)
   record("helper-only retirement retains secondaries",retired && f.construct() && [hit,attack].enumerated().allSatisfy{index,token in f.get(f.actor+(index==0 ? 0x70:0x78))==token && f.heap.allocationIdentity(at:token,count:0x174) === identities[index] && f.memory.ownsObjectAllocation(token,count:0x174)})
  }
  do {
   let f=try Fixture(p,hash);let ready=f.construct(),tokens=[f.get(f.state+0x18),f.get(f.actor+0x70),f.get(f.actor+0x78)]
   let retired=ready && f.host.retirePegLeg(actor:f.actor,provider:f.memory,retireSecondary:true)
   record("final retirement frees all owned allocations",retired && f.memory.sceneObjectPointers.isEmpty && f.memory.localPointers.isEmpty && tokens.allSatisfy{f.heap.lookupBytes($0,count:1)==nil} && f.get(f.state+0x18)==0 && f.get(f.actor+0x70)==0 && f.get(f.actor+0x78)==0)
   record("stale secondary after final retirement rejected",retired && {f.put(f.actor+0x70,tokens[1]);return !f.construct()}())
  }
  for offset:UInt32 in [0x70,0x78] {
   let suffix=String(offset,radix:16)
   do{let f=try Fixture(p,hash);let ready=f.construct(),token=f.get(f.actor+offset),data=decode(f.hex(token,0x174));f.heap.free(token);f.heap.storeBytes(token:token,count:0x174).update(from:data,count:data.count)
    record("retained secondary identity replacement rejected \(suffix)",ready && !f.host.retirePegLeg(actor:f.actor,provider:f.memory,retireSecondary:true))}
   do{let f=try Fixture(p,hash);let ready=f.construct();let other=f.heap.allocate(bytes:0x174);f.put(f.actor+offset,other)
    record("foreign secondary slot rejected \(suffix)",ready && !f.host.retirePegLeg(actor:f.actor,provider:f.memory,retireSecondary:true) && f.heap.lookupBytes(other,count:0x174) != nil)}
   do{let f=try Fixture(p,hash);let row=(p["secondary_metadata"] as! [[String:Any]]).first{u($0["offset"]!)==offset}!;f.put(u(row["token"]!)+0x10,0x4689b0)
    record("secondary metadata callback replacement rejected \(suffix)",!f.construct())}
   do{let f=try Fixture(p,hash);let ready=f.construct(),token=f.get(f.actor+offset);let retired=ready && f.host.retirePegLeg(actor:f.actor,provider:f.memory,retireSecondary:true)
    record("secondary duplicate free rejected \(suffix)",retired && !f.memory.releaseSceneObject(token))}
   do{let f=try Fixture(p,hash);let ready=f.construct(),token=f.get(f.actor+offset)
    record("secondary physical free bypass rejected \(suffix)",ready && !f.memory.releaseSceneObject(token) && f.heap.lookupBytes(token,count:0x174) != nil)}
   do{let f=try Fixture(p,hash);let ready=f.construct(),token=f.get(f.actor+offset);let retired=ready && f.host.retirePegLeg(actor:f.actor,provider:f.memory)
    record("secondary physical free after helper retirement rejected \(suffix)",retired && !f.memory.releaseSceneObject(token) && f.heap.lookupBytes(token,count:0x174) != nil)}
   do{let f=try Fixture(p,hash);let ready=f.construct();let row=(p["secondary_metadata"] as! [[String:Any]]).first{u($0["offset"]!)==offset}!;f.put(u(row["token"]!)+0x10,0x4689b0)
    record("retained secondary metadata replacement rejected \(suffix)",ready && !f.host.retirePegLeg(actor:f.actor,provider:f.memory,retireSecondary:true))}
   for mode in ["size","continuation","reentry","duplicate"] {
    let f=try Fixture(p,hash);var seen=false,nested=false;let root:UInt32=offset==0x70 ? 0x4c7fa0:0x4c8060
    f.memory.beforeObjectAllocation={r in if r.root==root {
     seen=true
     if mode=="size" || mode=="continuation" {if let bytes=f.host.bytes(r.context.esp+(mode=="size" ? 4:0x14),count:4) {bytes.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}}}
     if mode=="reentry" {nested = !f.host.invoke(f.call()).completed}
     if mode=="duplicate" {nested=f.memory.allocateObject(r)==nil}
    }}
    let rejected = !f.construct()
    record("secondary allocation \(mode) rejected \(suffix)",seen && rejected && ((mode=="size" || mode=="continuation") || nested))
   }
  }
  let result:[String:Any]=["profiles":output,"controls":controls,"allocation_failure":allocationFailure];try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"));print("native profiles \(output.count), controls \(controls.count)")
 }
}
