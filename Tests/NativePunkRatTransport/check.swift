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
 var platformNext:UInt32=0;var lastChild:UInt32=0
 var unresolvedCalls=0
 var memberSources:[[String:Any]]=[];var exact:[[String:Any]]=[];var environment=ClawX87State();var allocationWitness=false;var allocationContinuations:[UInt32]=[];var events:[[Any]]=[];var calls:[[Any]]=[];var missing:UInt32?;var missingName:String?;var inject:((ClawCall)->Void)?
 init(_ p:[String:Any],_ hash:String,isolateState:Bool=false)throws {
  self.p=p;platformNext=u(p["platform_next"]!);environment=fp(p["incoming"] as! [Any])
  for b in p["initial"] as! [[String:Any]] {
   let d=decode(b["data"] as! String),base=u(b["address"]!),end=base+UInt32(d.count),state=u(p["state"]!)
   let cuts=Set([base,end]+(isolateState && state>=base && state+0x180<=end ? [state,state+0x180]:[])).sorted()
   for i in 0..<(cuts.count-1) {let start=cuts[i],count=cuts[i+1]-start,bytes=Array(d[Int(start-base)..<Int(start-base+count)]);heap.storeBytes(token:start,count:count).update(from:bytes,count:bytes.count)}
  }
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
  let storage=heap;let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().map{k in(k,storage.lookup(k,words:1)![0])})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:0x61000000,sceneObjectAllocations:true)
  host.dependency={ [unowned self] _,c in let value=self.service(c);if value==nil {self.unresolvedCalls+=1};return value}
  host.observer={ [unowned self] c in self.calls.append([c.function,c.receiver,args(c)]);if [UInt32(0x4332f0),0x404fc0,0x4063b0].contains(c.function),c.x87ArgumentCount==UInt32(CLAW_X87_EXACT),let p=c.x87State {self.exact.append(["function":c.function,"state":fpJSON(p.pointee),"pop":p.pointee.popCount,"push":p.pointee.pushCount,"returned":p.pointee.returned])};if c.function==0x4f6428 {self.events.append(["free",c.arguments.0])};self.inject?(c)}
  memory.beforeObjectAllocation={ [unowned self] r in let offset=Int(r.context.esp-UInt32(CLAW_STACK_BASE)+0x14);self.allocationContinuations.append(r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)});if r.count==0x410 {self.allocationWitness=r.root==0x474330 && r.count==0x410 && r.returnPC==0x4f63ff && r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)}==0x47436d}}
  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]])}}
 }
 var actor:UInt32 {u(p["actor"]!)};var state:UInt32 {u(p["state"]!)}
 func get(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)?[0] ?? 0}
 func put(_ a:UInt32,_ v:UInt32){heap.lookup(a,words:1)?[0]=v}
 func string(_ a:UInt32)->String? {var bytes:[UInt8]=[];for i:UInt32 in 0..<256 {guard let p=host.bytes(a+i,count:1) else{return nil};if p[0]==0{return String(bytes:bytes,encoding:.ascii)};bytes.append(p[0])};return nil}
 func service(_ c:ClawCall)->UInt32? {
  let a=args(c);var f=c.function
  for slot:UInt32 in [0x546d5c,0x546cdc,0x5469e8,0x546cd4,0x546a40,0x546d24] {if get(slot)==f {f=slot}}
  if missing==f{return nil}
  switch f {
  case 0x4f51c5:
   guard a.count==1,c.receiver>=0x10,host.bytes(c.receiver,count:16) != nil else{return nil}
   let node=platformNext;platformNext=(node+12+15) & ~15;guard host.bytes(node,count:12) != nil else{return nil}
   let last=get(c.receiver+8);put(node,0);put(node+4,last);put(node+8,a[0])
   if last != 0 {put(last,node)}else{put(c.receiver+4,node)}
   put(c.receiver+8,node);put(c.receiver+12,get(c.receiver+12)+1)
   events.append(["append",c.receiver,a[0],node]);return node
  case 0x546a40:
   guard a.count==2,host.bytes(a[0],count:a[1]) != nil else{return nil};events.append(["readable",a[0],a[1],0]);return 0
  case 0x4f6974:
   guard a==[0],let data=heap.lookup(c.receiver,words:1)?[0],data>=12,let header=heap.lookup(data-12,words:3),header[0]==1,header[1]<=header[2],string(data) != nil else{return nil};return data
  case 0x546cd4:
   guard a.count==3,let rectangle=host.bytes(a[0],count:16) else{return nil};let bounds=rectangle.withMemoryRebound(to:UInt32.self,capacity:4){Array(UnsafeBufferPointer(start:$0,count:4)).map{Int32(bitPattern:$0)}};let x=Int32(bitPattern:a[1]),y=Int32(bitPattern:a[2]);let result:UInt32=bounds[0]<=x && x<bounds[2] && bounds[1]<=y && y<bounds[3] ? 1:0;events.append(["contains",a[0],x,y,result]);return result
  case 0x4f6286:
   guard a.count==2,let name=string(a[0]),let out=host.bytes(a[1],count:4),let map=heap.lookup(c.receiver+4,words:2) else{return nil}
   if name==missingName{return nil}
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
   guard a.count==2,let left=string(a[0]),let right=string(a[1]) else{return nil}
   let l=Array(left.utf8),r=Array(right.utf8)
   for i in 0...min(l.count,r.count) {let x=i<l.count ? l[i]:0,y=i<r.count ? r[i]:0;if x != y{return UInt32(bitPattern:Int32(x)-Int32(y))}}
   return 0
  case 0x546d24:
   guard a.count==3,let rect=host.bytes(a[0],count:16) else{return nil}
   var values=(0..<4).map{UnsafeRawPointer(rect.advanced(by:$0*4)).loadUnaligned(as:Int32.self)};let dx=Int32(bitPattern:a[1]),dy=Int32(bitPattern:a[2]);values[0] &-= dx;values[1] &-= dy;values[2] &+= dx;values[3] &+= dy
   for i in 0..<4 {var v=values[i].littleEndian;withUnsafeBytes(of:&v){UnsafeMutableRawPointer(rect.advanced(by:i*4)).copyMemory(from:$0.baseAddress!,byteCount:4)}}
   events.append(["inflate-rectangle",a[0],dx,dy]);return 1
  case 0x4a3050:events.append(["rand",99]);return 99
  default:return nil
  }
 }
 func hex(_ token:UInt32,_ count:UInt32)->String {heap.lookupBytes(token,count:count).map{UnsafeBufferPointer(start:$0,count:Int(count)).map{String(format:"%02x",$0)}.joined()} ?? "missing"}
 func call()->ClawCall {var c=ClawCall();c.function=0x474330;c.argumentCount=1;c.arguments.0=actor;return c}
 func run()->[String:Any] { execute(NSNumber(value:get(state+0x1c)), expected:(p["phases"] as! [[String:Any]])[0]) }
 func execute(_ command:Any,expected:[String:Any])->[String:Any] {
  var completed=false
  if let text=command as? String,text=="retire" {
   lastChild=get(get(state+0x18)+0x408)
   if let result=host.withObjectX87Environment(environment,body:{host.retirePunkRat(actor:actor,provider:memory)}) {completed=result.0;environment=result.1}
  } else if let text=command as? String,text=="child-retire" {
   if let result=host.withObjectX87Environment(environment,body:{host.retirePunkRatChild(actor:lastChild,provider:memory)}) {completed=result.0;environment=result.1}
  } else {
   if let value=command as? NSNumber {put(state+0x1c,value.uint32Value)}
   else if let text=command as? String,text=="recreate" {put(state+0x1c,0)}
   _=host.withObjectAllocation(provider:memory){if let result=host.withObjectX87Environment(environment,body:{host.invoke(call())}) {completed=result.0.completed;environment=result.1}}
   memberSources += host.punkRatMemberSources.map{x in ["function":x.function,"receiver":x.input.ecx,"return_pc":x.returnPC,"eax":x.output.eax,"stack_delta":x.output.esp-x.input.esp,"preserved":x.input.ebx==x.output.ebx && x.input.esi==x.output.esi && x.input.edi==x.output.edi && x.input.ebp==x.output.ebp]}

  }
  let final=(expected["final"] as! [[String:Any]]).map {b->[String:Any] in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);let text=heap.lookupBytes(a,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing";return["address":a,"data":text]}
  return["command":command,"helper":get(state+0x18),"allocation_witness":allocationWitness,"completed":completed,"fault":host.fault.map{String(describing:$0)} ?? "none","outgoing":fpJSON(environment),"events":events,"calls":calls,"exact":exact,"retired":memory.tlsSnapshot().allocationBytes.filter{memory.localBytes[$0.key]==nil}.mapValues{$0.map{String(format:"%02x",$0)}.joined()},"member_source":memberSources,"final":final]
 }
 func full()->[String:Any] {
  let phases=(p["phases"] as! [[String:Any]]).map{execute($0["command"]!,expected:$0)}
  return["label":p["label"]!,"allocation_witness":allocationWitness,"allocation_continuations":allocationContinuations,"unresolved_calls":unresolvedCalls,"phases":phases]
 }

}
@main struct PunkRatTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]);let ref=try JSONSerialization.jsonObject(with:Data(contentsOf:dir.appendingPathComponent("reference.json"))) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  var output:[[String:Any]]=[];for p in profiles{let result=try Fixture(p,hash).full();output.append(result);for phase in result["phases"] as! [[String:Any]] {if !(phase["completed"] as! Bool) {print("phase failure \(p["label"]!) \(phase["command"]!) \(phase["fault"]!)")}}}
  var controls:[[String:Any]]=[]
  func record(_ n:String,_ ok:Bool){controls.append(["name":n,"passed":ok])}
  func failed(_ f:Fixture)->Bool {!(f.run()["completed"] as! Bool)}
  do{let f=try Fixture(p,hash);record("provider required",!f.host.invoke(f.call()).completed && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);record("foreign provider rejected",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(f.call())}==nil)}
  do{let f=try Fixture(p,hash);f.put(f.state+0x10,0x474331);record("wrong callback rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.put(f.actor+0x6c,UInt32.max);record("wrong actor state rejected",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x4f6286;record("missing registry fails",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x546cdc;record("missing rectangle fails",failed(f))}
  do{let f=try Fixture(p,hash);f.memory.failAllocation={$0==0x4a48e0};record("allocation exhaustion preserved",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);let bytes=f.heap.storeBytes(token:0x61000000,count:0x410);bytes.update(repeating:0xa7,count:0x410);record("occupied allocation preserved",failed(f) && UnsafeBufferPointer(start:bytes,count:0x410).allSatisfy{$0==0xa7})}
  do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={_ in f.heap.free(0x10000000);_=f.heap.storeBytes(token:0x10000000,count:0x10000)};record("actor identity replacement rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.memory.afterService={slot,_,token in if slot==0x4a48e0 && token != 0 {f.heap.free(token);_=f.heap.storeBytes(token:token,count:0x410)}};record("allocation identity replacement rejected",failed(f))}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(f.call())};record("physical service reentry rejected",failed(f) && nested?.completed==false)}
  for delta:UInt32 in [0,4,0x14,0x18] {
   let f=try Fixture(p,hash)
   f.memory.beforeObjectAllocation={r in if let bytes=f.host.bytes(r.context.esp+delta,count:4) {bytes.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}}}
   record("source allocation stack word \(delta) tampering rejected before allocation",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  for mode in ["size","receiver","actor","continuation","constructor"] {
   let f=try Fixture(p,hash);var injected=false
   f.inject={c in if !injected && c.function==(mode=="size" ? 0x4f63ec:0x4332f0) {injected=true;var wrong=c
    if mode=="size" {wrong.arguments.0=0x40f};if mode=="receiver" {wrong.receiver &+= 4};if mode=="actor" {wrong.arguments.0 &+= 4};if mode=="continuation" {wrong.sourceReturnPC=0x474389};if mode=="constructor" {wrong.function=0x437a90}
    _=f.host.callNativeDependency(wrong)
   }};record("reentrant wrong \(mode) request rejected",failed(f) && injected)
  }
  for offset:UInt32 in [8,0x0c,0x10] {
   let f=try Fixture(p,hash);var corrupted=false
   f.inject={c in if !corrupted && c.function==0x4c7970 {corrupted=true;f.put(0x61000000+offset,f.get(0x61000000+offset)+4)}}
   record("post-base helper link \(offset) corruption rejected",failed(f) && corrupted)
  }
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x4c7970 {changed=true;f.put(f.state+0x1c,0)}};record("construction command mutation rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x4c8da0 {changed=true;f.put(0x61000000,0x50f590)}};record("initial vtable replacement rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);let first = !failed(f);f.put(f.state+0x1c,0);record("stale live helper rejected",first && failed(f))}
  for mode in ["size","receiver","actor","continuation","constructor"] {
   let f=try Fixture(p,hash);var c=ClawCall();c.function=mode=="size" ? 0x4f63ec:0x4332f0;c.argumentCount=1;c.arguments.0=mode=="size" ? 0x40f:f.actor;c.receiver=mode=="size" ? 0:0x61000004;if mode=="actor" {c.arguments.0 &+= 4};if mode=="continuation" {c.sourceReturnPC=0x474389};if mode=="constructor" {c.function=0x437a90}
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
   record("allocation owner retained",success && f.memory.ownsObjectAllocation(token,count:0x410))
   if success {let release=f.host.retirePunkRat(actor:f.actor,provider:f.memory);record("owner routed release",release && !f.memory.ownsObjectAllocation(token,count:0x410));f.put(f.state+0x1c,0);record("fresh allocation after release",!failed(f) && f.get(f.state+0x18) != token)}
  }
  do{let f=try Fixture(p,hash);let first = !failed(f);let old=f.get(f.state+0x18);let retired=f.host.retirePunkRat(actor:f.actor,provider:f.memory);f.put(f.state+0x1c,0);let recreated = !failed(f);let fresh=f.get(f.state+0x18);f.put(f.state+0x18,old);f.put(f.state+0x1c,5);record("retirement recreation rejects stale helper",first && retired && recreated && fresh != old && failed(f))}
  do{let f=try Fixture(p,hash);let first = !failed(f);let retired=f.host.retirePunkRat(actor:f.actor,provider:f.memory);record("double retirement rejected",first && retired && !f.host.retirePunkRat(actor:f.actor,provider:f.memory))}
  do{let f=try Fixture(p,hash);let first = !failed(f);let following=f.heap.allocate(bytes:16);record("shared scene cursor advanced by exact extent",first && following==0x61000dd0)}
  for mode in ["actor","logic","helper","vtable"] {
   let f=try Fixture(p,hash);let first = !failed(f);let helper=f.get(f.state+0x18)
   if mode=="actor" {f.put(f.actor+0x6c,f.state+4)}
   if mode=="logic" {f.put(f.state+0x10,0x474331)}
   if mode=="helper" {f.heap.free(helper);_=f.heap.storeBytes(token:helper,count:0x410)}
   if mode=="vtable" {f.put(helper,0x50f590)}
   f.put(f.state+0x1c,5);record("lifecycle stale \(mode) rejected",first && failed(f))
  }
  for mode in ["control","count","pop","returned"] {
   let f=try Fixture(p,hash);var changed=false
   f.inject={c in if !changed && c.function==0x4332f0,let exact=c.x87State {changed=true;if mode=="control" {exact.pointee.control=0};if mode=="count" {exact.pointee.count=9};if mode=="pop" {exact.pointee.popCount=1};if mode=="returned" {exact.pointee.returned=1}}}
   record("malformed constructor exact x87 \(mode) rejected",failed(f) && changed)
  }
  do{let f=try Fixture(p,hash);let first = !failed(f);let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.map{($0,f.get($0))});let foreign=try ClawNativeMfcMemory(host:f.host,sha256:hash,importTargets:imports,allocationBase:0x62000000,sceneObjectAllocations:true);f.put(f.state+0x1c,5);let result=f.host.withObjectAllocation(provider:foreign){f.host.invoke(f.call())};record("foreign provider on same host rejected",first && result?.completed != true && f.host.fault != nil)}
  do{let f=try Fixture(p,hash);let first = !failed(f);let helper=f.get(f.state+0x18);let foreign=f.heap.allocate(bytes:0x410);if let src=f.heap.lookupBytes(helper,count:0x410),let dst=f.heap.lookupBytes(foreign,count:0x410) {dst.update(from:src,count:0x410)};f.put(f.state+0x18,foreign);f.put(f.state+0x1c,5);record("foreign helper allocation rejected",first && failed(f))}
  for mode in ["wrong actor","foreign provider","replaced helper","foreign helper"] {
   let f=try Fixture(p,hash);let first = !failed(f);let helper=f.get(f.state+0x18);var actor=f.actor;var provider=f.memory
   if mode=="wrong actor" {actor &+= 4}
   if mode=="foreign provider" {let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.map{($0,f.get($0))});provider=try ClawNativeMfcMemory(host:f.host,sha256:hash,importTargets:imports,allocationBase:0x62000000,sceneObjectAllocations:true)}
   if mode=="replaced helper" {f.heap.free(helper);_=f.heap.storeBytes(token:helper,count:0x410)}
   if mode=="foreign helper" {let other=f.heap.allocate(bytes:0x410);if let src=f.heap.lookupBytes(helper,count:0x410),let dst=f.heap.lookupBytes(other,count:0x410) {dst.update(from:src,count:0x410)};f.put(f.state+0x18,other)}
   let retired=f.host.retirePunkRat(actor:actor,provider:provider)
   record("direct retirement \(mode) rejected",first && !retired && f.host.fault != nil)
  }
  do{let f=try Fixture(p,hash);let first = !failed(f);f.missing=0x546a40;f.put(f.state+0x1c,5);record("missing RTTI readability rejected",first && failed(f))}
  do{let f=try Fixture(p,hash);let result=f.host.withObjectX87Environment(f.environment,body:{f.host.invokePunkRat(actor:f.actor,provider:f.memory)});record("consumer callback API",result?.0?.completed==true && f.host.fault==nil)}
  do{let f=try Fixture(p,hash,isolateState:true);let ready = !failed(f);let bytes=Array(UnsafeBufferPointer(start:f.heap.lookupBytes(f.state,count:0x180)!,count:0x180));f.heap.free(f.state);f.heap.storeBytes(token:f.state,count:0x180).update(from:bytes,count:bytes.count);f.put(f.state+0x1c,1000);record("state identity replacement rejected",ready && failed(f))}
  for mode in ["actor","state","private"] {
   let f=try Fixture(p,hash);let ready = !failed(f);let child=f.get(f.get(f.state+0x18)+0x408),state=f.get(child+0x6c),helper=f.get(state+0x18)
   let token=mode=="actor" ? child:mode=="state" ? state:helper,count:UInt32=mode=="actor" ? 0x1b4:mode=="state" ? 0x174:0x7c
   if ready,let ptr=f.heap.lookupBytes(token,count:count) {let bytes=Array(UnsafeBufferPointer(start:ptr,count:Int(count)));f.heap.free(token);f.heap.storeBytes(token:token,count:count).update(from:bytes,count:bytes.count)}
   f.put(f.state+0x1c,1000);record("child \(mode) identity replacement rejected",ready && failed(f))
  }
  do{let f=try Fixture(p,hash);let ready = !failed(f);let helper=f.get(f.state+0x18);f.put(helper+0x408,f.get(helper+0x408)+4);f.put(f.state+0x1c,1000);record("parent child link replacement rejected",ready && failed(f))}
  for mode in ["actor","state","private"] {
   let f=try Fixture(p,hash);let ready = !failed(f);let child=f.get(f.get(f.state+0x18)+0x408),state=f.get(child+0x6c),helper=f.get(state+0x18)
   let token=mode=="actor" ? child:mode=="state" ? state:helper
   record("linked child \(mode) physical retirement rejected",ready && !f.memory.releaseSceneObject(token))
  }
  do{let f=try Fixture(p,hash);let ready = !failed(f);let child=f.get(f.get(f.state+0x18)+0x408),state=f.get(child+0x6c),helper=f.get(state+0x18)
   let retired=ready && f.host.retirePunkRat(actor:f.actor,provider:f.memory)
   record("child survives parent retirement",retired && f.memory.ownsObjectAllocation(child,count:0x1b4) && f.memory.ownsObjectAllocation(state,count:0x174) && f.memory.ownsObjectAllocation(helper,count:0x7c))
   let childRetired=retired && f.host.retirePunkRatChild(actor:child,provider:f.memory)
   record("same-owner independent child retirement",childRetired && !f.memory.ownsObjectAllocation(helper,count:0x7c) && f.get(state+0x18)==0 && f.get(child+0x70)==0 && f.get(child+0x78)==0)
   record("double child retirement rejected",childRetired && !f.host.retirePunkRatChild(actor:child,provider:f.memory))
  }
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);let ready = !failed(f);let child=f.get(f.get(f.state+0x18)+0x408);record("foreign child retirement provider rejected",ready && !f.host.retirePunkRatChild(actor:child,provider:other.memory))}
  for target:UInt32 in [0x4746f0,0x474710,0x484d90,0x456030] {
   let f=try Fixture(p,hash);let ready = !failed(f);let child=f.get(f.get(f.state+0x18)+0x408)
   var call=ClawCall();call.function=target;call.receiver=target==0x4746f0 || target==0x474710 ? f.get(f.state+0x18):f.get(f.get(child+0x6c)+0x18);call.argumentCount=target==0x4746f0 || target==0x484d90 ? 1:0;call.arguments.0=1
   let before=f.hex(call.receiver,call.receiver==f.get(f.state+0x18) ? 0x410:0x7c);let rejected = !f.host.invoke(call).completed
   record("direct destructor \(String(target,radix:16)) bypass rejected",ready && rejected && f.hex(call.receiver,call.receiver==f.get(f.state+0x18) ? 0x410:0x7c)==before)
  }
  for field in ["root","size"] {
   let f=try Fixture(p,hash);var authorityRejected=false,attempted=false
   f.memory.beforeObjectAllocation={r in if !attempted {attempted=true;var wrong=r
    let offset=field=="root" ? MemoryLayout<ClawNativeCanonicalHost.ObjectAllocationRequest>.offset(of:\.root)!:MemoryLayout<ClawNativeCanonicalHost.ObjectAllocationRequest>.offset(of:\.count)!
    withUnsafeMutableBytes(of:&wrong){bytes in bytes.storeBytes(of:field=="root" ? UInt32(0x4493c0):UInt32(0x40f),toByteOffset:offset,as:UInt32.self)}
    authorityRejected = !wrong.validReturn(for:f.host);_=f.memory.allocateObject(wrong)
   }}
   record("wrong request \(field) rejected",failed(f) && attempted && authorityRejected && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  for name in ["LEVEL_CANNON","LEVEL_CANNON_FIRING"] {
   let f=try Fixture(p,hash);f.missingName=name
   record("missing child resource \(name) rejected",failed(f) && f.memory.ownsObjectAllocation(0x61000710,count:0x1b4))
  }
  for nth in 4...8 {
   let f=try Fixture(p,hash);var count=0;f.memory.failAllocation={function in if function==0x4a48e0 {count+=1;return count==nth};return false}
   record("child allocation \(nth) exhaustion rejected",failed(f) && count==nth && f.host.fault != nil)
  }
  for mode in ["actor","state","private"] {
   let f=try Fixture(p,hash);let ready = !failed(f);let token=mode=="actor" ? f.actor:mode=="state" ? f.state:f.get(f.state+0x18)
   record("live parent \(mode) physical retirement rejected",ready && !f.memory.releaseSceneObject(token))
  }
  for offset:UInt32 in [0,4,8,12,16,28,32,36] {
   let f=try Fixture(p,hash);f.put(0x50eee4+offset,f.get(0x50eee4+offset)+4)
   record("parent vtable slot \(offset) replacement rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  for offset:UInt32 in [0,4,8,12,16,28,32] {
   let f=try Fixture(p,hash);f.put(0x50dfd4+offset,f.get(0x50dfd4+offset)+4)
   record("child vtable slot \(offset) replacement rejected",failed(f))
  }
  let result:[String:Any]=["profiles":output,"controls":controls];try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"));print("native profiles \(output.count), controls \(controls.count)")
 }
}
