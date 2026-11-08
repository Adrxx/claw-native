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
 var invalidBacking=false;var contexts:[[Any]]=[];var retiredBytes="";var secondaryRetired:[[String:Any]]=[];var allocationWitness=false;var secondaryWitnesses:[[UInt32]]=[];var events:[[Any]]=[];var calls:[[Any]]=[];var missing:UInt32?;var inject:((ClawCall)->Void)?
 init(_ p:[String:Any],_ hash:String,isolateMetadata:Bool=false)throws {
  self.p=p
  let metadata=(p["events"] as? [[Any]] ?? []).filter{($0[0] as? String)=="lookup" && ["LogicHit","LogicAttack"].contains($0[2] as? String ?? "")}.flatMap{[u($0[3]),u($0[1])-16]}
  for b in p["initial"] as! [[String:Any]] {
   let d=decode(b["data"] as! String),base=u(b["address"]!),end=base+UInt32(d.count)
   let cuts=Set([base,end]+(isolateMetadata ? metadata.filter{$0>=base && $0+20<=end}.flatMap{[$0,$0+20]}:[])).sorted()
   for i in 0..<(cuts.count-1) {let start=cuts[i],count=cuts[i+1]-start;let bytes=Array(d[Int(start-base)..<Int(start-base+count)]);heap.storeBytes(token:start,count:count).update(from:bytes,count:bytes.count)}
  }
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
  let storage=heap;let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().map{k in(k,storage.lookup(k,words:1)![0])})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:p["allocation_base"].map{u($0)} ?? 0x61000000,sceneObjectAllocations:true)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in self.calls.append([c.function,c.receiver,args(c)]);if c.function==0x497130,let cpu=c.sourceContext?.pointee {self.contexts.append([c.function,c.receiver,c.sourceReturnPC,cpu.ebx,cpu.ebp,cpu.eax,cpu.esi,cpu.edi,c.arguments.0])};if c.function==0x4f6428 && self.memory.ownsObjectAllocation(c.arguments.0,count:0x498) {self.retiredBytes=self.hex(c.arguments.0,0x498)};if c.function==0x4f6428 && self.memory.ownsObjectAllocation(c.arguments.0,count:0x174) && !self.memory.ownsObjectAllocation(c.arguments.0,count:0x498) {self.secondaryRetired.append(["address":c.arguments.0,"data":self.hex(c.arguments.0,0x174)])};self.inject?(c)}
  memory.beforeObjectAllocation={ [unowned self] r in if r.count==0x174 {let offset=Int(r.context.esp-UInt32(CLAW_STACK_BASE)+0x14);self.secondaryWitnesses.append([r.root,r.count,r.returnPC,r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)}])};if r.count==0x498 {let offset=Int(r.context.esp-UInt32(CLAW_STACK_BASE)+0x14);self.allocationWitness=r.root==0x496050 && r.returnPC==0x4f63ff && r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)}==0x49608d}}
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
   guard a.count==2,let name=string(a[0]),let out=host.bytes(a[1],count:4) else{return nil}
   if let bindings=p["bindings"] as? [String:NSNumber] {
    guard c.receiver==0x62000010,let token=bindings[name] else{return nil}
    let value=token.uint32Value;out.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee=value};events.append(["lookup",c.receiver,name,value]);return 1
   }
   guard let map=heap.lookup(c.receiver+4,words:2) else{return nil}
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
 func call()->ClawCall {var c=ClawCall();c.function=0x496050;c.argumentCount=1;c.arguments.0=actor;return c}
 func hex(_ a:UInt32,_ n:UInt32)->String {heap.lookupBytes(a,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing"}
 func execute(_ command:UInt32,_ outgoing:inout ClawX87State)->Bool {
  put(state+0x1c,command)
  if command==6 {put(0x537210,100);put(0x61000000+0x488,90);put(0x61000000+0x48c,20);put(actor+0xcc,7)}
  var completion:ClawNativeCanonicalHost.Completion?
  _=host.withObjectAllocation(provider:memory){if let r=host.withObjectX87Environment(outgoing,body:{host.invoke(call())}) {completion=r.0;outgoing=r.1}}
  return completion?.completed==true && host.fault==nil && !invalidBacking
 }
 func construct()->Bool {var outgoing=fp(p["incoming"] as! [Any]);return execute(0,&outgoing)}
 func wwdPrefix()->[String:Any] {
  let selected:Set<UInt32>=[0x4c7fa0,0x4c8060,0x4c8160]
  var binds=0,prefix:[String:Any]?
  // The hash-verified original stops on return from the second 4c8160.
  // Capture before the next observed call can perform any later service.
  // Continue execution separately; this prefix is not a completed callback.
  inject={ [unowned self] c in
   if binds==2 && prefix==nil {
    let secondaries=[self.get(self.actor+0x70),self.get(self.actor+0x78)]
    prefix=["events":self.events,"calls":self.calls.dropLast().filter{selected.contains(u($0[0]))},"secondary_bytes":secondaries.map{["address":$0,"data":self.hex($0,0x174)]},"owned":secondaries.allSatisfy{$0 != 0 && self.memory.ownsObjectAllocation($0,count:0x174)}]
   }
   if c.function==0x4c8160 {binds+=1}
  }
  let completed=construct()
  inject=nil
  var result=prefix ?? ["events":[],"calls":[],"secondary_bytes":[],"owned":false]
  result["completed"]=completed
  result["fault"]=host.fault.map{String(describing:$0)} ?? "none"
  return result
 }
 func stringRetirement(_ spec:[String:Any])->[String:Any] {
  let name=spec["name"] as! String,references=u(spec["references"]!),members=spec["members"] as! [NSNumber]
  guard construct() else{return["name":name,"failure":"construction"]}
  var c=ClawCall();c.function=0x546aa8;c.stackPointer=UInt32(CLAW_STACK_TOP);c.argumentCount=2;c.arguments.0=0;c.arguments.1=16
  guard let token=memory.service(c),token != 0 else{return["name":name,"failure":"allocation"]}
  put(token,references);put(token+4,3);put(token+8,3);put(token+12,0x00636261)
  for offset in members {put(0x61000000+offset.uint32Value,token+12)}
  let retired=host.retireTownGuard1(actor:actor,provider:memory)
  let bytes=memory.tlsSnapshot().allocationBytes[String(token)]?.map{String(format:"%02x",$0)}.joined() ?? "missing"
  return["name":name,"references":references,"members":members,"token":token,"bytes":bytes,"freed":!memory.ownsObjectAllocation(token,count:16),"helper_freed":retired && !memory.ownsObjectAllocation(0x61000000,count:0x498),"helper_bytes":retiredBytes]
 }
 func run()->[String:Any] {
  var outgoing=fp(p["incoming"] as! [Any]);var completed=true;var snapshots:[[[String:Any]]]=[];var x87Snapshots:[[Any]]=[]
  let shapes=p["snapshots"] as! [[[String:Any]]]
  for (index,command) in (p["commands"] as! [NSNumber]).enumerated() {
   if p["secondary"] as? Bool==true && index>0 {
    let old=get(state+0x18)
    guard host.retireTownGuard1(actor:actor,provider:memory) else{completed=false;break}
    events.append(["free",old])
   }
   if !execute(command.uint32Value,&outgoing) {completed=false;break}
   x87Snapshots.append(fpJSON(outgoing))
   snapshots.append(shapes[index].map {b in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);return["address":a,"data":hex(a,n)]})
  }
  let helper=get(state+0x18),secondaries=[get(actor+0x70),get(actor+0x78)]
  let secondary=p["secondary"] as? Bool==true
  let retired=completed && host.retireTownGuard1(actor:actor,provider:memory,retireSecondary:secondary)
  if retired {events.append(["free",helper]);if secondary {for token in secondaries {events.append(["free",token])}}}
  let secondaryRetirementComplete = !secondary || (get(actor+0x70)==0 && get(actor+0x78)==0 && secondaries.allSatisfy{!memory.ownsObjectAllocation($0,count:0x174)})
  return["label":p["label"]!,"allocation_witness":allocationWitness,"secondary_witnesses":secondaryWitnesses,"completed":completed,"fault":host.fault.map{String(describing:$0)} ?? "none","outgoing":fpJSON(outgoing),"events":events,"calls":calls,"contexts":contexts,"snapshots":snapshots,"x87_snapshots":x87Snapshots,"retired":retired && secondaryRetirementComplete,"retired_bytes":retiredBytes,"secondary_retired":secondaryRetired]
 }
}

@main struct TownGuard1TransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]);let ref=try JSONSerialization.jsonObject(with:Data(contentsOf:dir.appendingPathComponent("reference.json"))) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  var output:[[String:Any]]=[];for p in profiles{output.append(try Fixture(p,hash).run())}
  var controls:[[String:Any]]=[]
  func record(_ n:String,_ ok:Bool){controls.append(["name":n,"passed":ok])}
  func failed(_ f:Fixture)->Bool {!f.construct()}
  do{let f=try Fixture(p,hash);record("provider required",!f.host.invoke(f.call()).completed && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);record("foreign provider rejected",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(f.call())}==nil)}
  do{let f=try Fixture(p,hash);f.put(f.state+0x10,0x496051);record("wrong callback rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.put(f.actor+0x6c,UInt32.max);record("wrong actor state rejected",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x4f6286;record("missing registry fails",failed(f))}
  do{let f=try Fixture(p,hash);f.missing=0x546d5c;record("missing rectangle fails",failed(f))}
  do{let f=try Fixture(p,hash);f.memory.failAllocation={$0==0x4a48e0};record("allocation exhaustion preserved",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);let bytes=f.heap.storeBytes(token:0x61000000,count:0x498);bytes.update(repeating:0xa7,count:0x498);record("occupied allocation preserved",failed(f) && UnsafeBufferPointer(start:bytes,count:0x498).allSatisfy{$0==0xa7})}
  do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={_ in f.heap.free(0x10000000);_=f.heap.storeBytes(token:0x10000000,count:0x10000)};record("actor identity replacement rejected",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(p,hash);f.memory.afterService={slot,_,token in if slot==0x4a48e0 && token != 0 {f.heap.free(token);_=f.heap.storeBytes(token:token,count:0x498)}};record("allocation identity replacement rejected",failed(f))}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(f.call())};record("physical service reentry rejected",failed(f) && nested?.completed==false)}
  for delta:UInt32 in [0,4,0x14,0x18] {
   let f=try Fixture(p,hash)
   f.memory.beforeObjectAllocation={r in if let bytes=f.host.bytes(r.context.esp+delta,count:4) {bytes.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}}}
   record("source allocation stack word \(delta) tampering rejected before allocation",failed(f) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  for mode in ["size","receiver","actor","continuation"] {
   let f=try Fixture(p,hash);var injected=false
   f.inject={c in if !injected && c.function==(mode=="size" ? 0x4f63ec:0x496110) {injected=true;var wrong=c
    if mode=="size" {wrong.arguments.0=0x497};if mode=="receiver" {wrong.receiver &+= 4};if mode=="actor" {wrong.arguments.0 &+= 4};if mode=="continuation" {wrong.sourceReturnPC=0x4960a9}
    _=f.host.callNativeDependency(wrong)
   }};record("reentrant wrong \(mode) request rejected",failed(f) && injected)
  }
  for offset:UInt32 in [8,0x0c,0x10] {
   let f=try Fixture(p,hash);var corrupted=false
   f.inject={c in if !corrupted && c.function==0x4c7970 {corrupted=true;f.put(0x61000000+offset,f.get(0x61000000+offset)+4)}}
   record("post-base helper link \(offset) corruption rejected",failed(f) && corrupted)
  }
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x4c7970 {changed=true;f.put(f.state+0x1c,0)}};record("construction command mutation rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);var changed=false;f.inject={c in if !changed && c.function==0x405000 {changed=true;f.put(0x61000000,0x50fac0)}};record("initial vtable replacement rejected",failed(f) && changed)}
  do{let f=try Fixture(p,hash);let first = !failed(f);f.put(f.state+0x1c,0);record("stale live helper rejected",first && failed(f))}
  for mode in ["size","receiver","actor","continuation"] {
   let f=try Fixture(p,hash);var c=ClawCall();c.function=mode=="size" ? 0x4f63ec:0x496110;c.argumentCount=1;c.arguments.0=mode=="size" ? 0x497:f.actor;c.receiver=mode=="size" ? 0:0x61000004;if mode=="actor" {c.arguments.0 &+= 4};if mode=="continuation" {c.sourceReturnPC=0x4960a9}
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
   record("allocation owner retained",success && f.memory.ownsObjectAllocation(token,count:0x498))
   let retired=success && f.host.retireTownGuard1(actor:f.actor,provider:f.memory)
   record("same-owner retirement",retired && !f.memory.ownsObjectAllocation(token,count:0x498))
   record("recreation uses fresh helper",retired && f.construct() && f.get(f.state+0x18) != token)
   f.put(f.state+0x18,token);var state=fp(p["incoming"] as! [Any]);record("stale helper after recreation rejected",!f.execute(1000,&state))
  }
  do{let f=try Fixture(p,hash);let ready=f.construct() && f.host.retireTownGuard1(actor:f.actor,provider:f.memory);record("double retirement rejected",ready && !f.host.retireTownGuard1(actor:f.actor,provider:f.memory))}
  do{let f=try Fixture(p,hash),other=try Fixture(p,hash);let ready=f.construct();record("foreign retirement provider rejected",ready && !f.host.retireTownGuard1(actor:f.actor,provider:other.memory))}
  do{let f=try Fixture(p,hash);let ready=f.construct();let token=f.get(f.state+0x18);f.heap.free(token);_=f.heap.storeBytes(token:token,count:0x498);var state=fp(p["incoming"] as! [Any]);record("stale helper identity rejected",ready && !f.execute(1000,&state))}
  do{let f=try Fixture(p,hash);let ready=f.construct();f.put(f.actor+0x6c,f.state+0x180);var state=fp(p["incoming"] as! [Any]);record("foreign logic binding rejected",ready && !f.execute(1000,&state))}
  do{let f=try Fixture(p,hash);let ready=f.construct();f.put(f.get(f.state+0x18),0x50fb6c);var state=fp(p["incoming"] as! [Any]);record("live vtable replacement rejected",ready && !f.execute(29,&state))}
  do{let f=try Fixture(p,hash);let ready=f.construct();let token=f.get(f.state+0x18);let retired=ready && f.host.retireTownGuard1(actor:f.actor,provider:f.memory);record("double physical free rejected",retired && !f.memory.releaseSceneObject(token))}
  do{let f=try Fixture(p,hash);let ready=f.construct();f.missing=0x4f6974;var state=fp(p["incoming"] as! [Any]);record("missing CString service rejected",ready && !f.execute(6,&state))}
  for target:UInt32 in [0x497130,0x497a50] {
   for mode in ["version","input-mask","output-mask","preserve-mask","receiver","stack","function","eax","continuation"] {
    let f=try Fixture(p,hash);let ready=f.construct();var injected=false
    f.inject={c in if !injected && c.function==target,let cpu=c.sourceContext {
     injected=true
     switch mode {
     case "version":cpu.pointee.version=2
     case "input-mask":cpu.pointee.inputMask ^= 1
     case "output-mask":cpu.pointee.outputMask ^= 1
     case "preserve-mask":cpu.pointee.preserveMask ^= 1
     case "receiver":cpu.pointee.ecx &+= 4
     case "stack":cpu.pointee.esp &+= 4
     case "function":cpu.pointee.eip &+= 1
     case "eax":cpu.pointee.eax ^= 1
     default:if let bytes=f.host.bytes(c.stackPointer,count:4) {bytes.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}}
     }
    }}
    var state=fp(p["incoming"] as! [Any]);record("source \(String(target,radix:16)) \(mode) tampering rejected",ready && !f.execute(6,&state) && injected)
   }
  }
  let fresh=profiles[4]
  do{let f=try Fixture(fresh,hash);record("fresh secondaries require scene owner",!f.host.invoke(f.call()).completed && f.get(f.actor+0x70)==0 && f.get(f.actor+0x78)==0)}
  do{let f=try Fixture(fresh,hash);let ready=f.construct();let hit=f.get(f.actor+0x70),attack=f.get(f.actor+0x78)
   record("fresh secondary ledger ownership",ready && hit != 0 && attack != 0 && hit != attack && f.memory.ownsObjectAllocation(hit,count:0x174) && f.memory.ownsObjectAllocation(attack,count:0x174))
   let retired=ready && f.host.retireTownGuard1(actor:f.actor,provider:f.memory,retireSecondary:true)
   record("same owner retires all three allocations",retired && f.get(f.actor+0x70)==0 && f.get(f.actor+0x78)==0 && !f.memory.ownsObjectAllocation(hit,count:0x174) && !f.memory.ownsObjectAllocation(attack,count:0x174) && !f.memory.ownsObjectAllocation(0x61000000,count:0x498))
  }
  for offset:UInt32 in [0x70,0x78] {
   do{let f=try Fixture(fresh,hash);let ready=f.construct();let token=f.get(f.actor+offset);let helperRetired=ready && f.host.retireTownGuard1(actor:f.actor,provider:f.memory)
    f.heap.free(token);_=f.heap.storeBytes(token:token,count:0x174)
    record("stale secondary \(offset) allocation rejected",helperRetired && !f.construct())
   }
   do{let f=try Fixture(fresh,hash);let ready=f.construct();f.put(f.actor+offset,f.actor)
    record("foreign secondary \(offset) slot rejected at retirement",ready && !f.host.retireTownGuard1(actor:f.actor,provider:f.memory,retireSecondary:true))
   }
  }
  for target:UInt32 in [0x4c7fa0,0x4c8060,0x4c81b0,0x4c8160] {
   let f=try Fixture(fresh,hash);var c=ClawCall();c.function=target;c.receiver=f.actor;c.argumentCount=target==0x4c81b0 ? 0:target==0x4c8160 ? 2:1;c.arguments.0=0x522d54
   _=f.host.withObjectAllocation(provider:f.memory){f.host.callNativeDependency(c)}
   record("secondary \(String(target,radix:16)) outside constructor rejected",f.host.fault != nil && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  do{let f=try Fixture(fresh,hash);var changed=false
   f.memory.beforeObjectAllocation={r in if r.count==0x174 && !changed {changed=true;f.put(f.actor+0x70,f.actor)}}
   record("secondary slot mutation during physical allocation rejected",!f.construct() && changed)
  }
  do{let f=try Fixture(fresh,hash);var captured:ClawNativeCanonicalHost.ObjectAllocationRequest?
   f.memory.beforeObjectAllocation={r in if r.count==0x174 {captured=r}}
   let ready=f.construct();record("secondary allocation lease expires",ready && captured.map{!$0.consume(for:f.host,provider:f.memory)}==true)
  }
  for name in ["LogicHit","LogicAttack"] {
   let rows=fresh["events"] as! [[Any]],token=u(rows.first{($0[0] as? String)=="lookup" && ($0[2] as? String)==name}![3])
   do{let f=try Fixture(fresh,hash,isolateMetadata:true);var changed=false
    f.memory.beforeObjectAllocation={r in if r.count==0x174 && !changed && (name=="LogicHit" || f.get(f.actor+0x70) != 0) {
     changed=true;let data=Array(UnsafeBufferPointer(start:f.heap.lookupBytes(token,count:20)!,count:20));f.heap.free(token);f.heap.storeBytes(token:token,count:20).update(from:data,count:data.count)
    }}
    record("stale \(name) metadata allocation rejected",!f.construct() && changed)
   }
   do{let f=try Fixture(fresh,hash);var changed=false
    f.memory.beforeObjectAllocation={r in if r.count==0x174 && !changed && (name=="LogicHit" || f.get(f.actor+0x70) != 0) {changed=true;f.put(token+0x10,0x4dc810)}}
    record("\(name) callback mutation rejected",!f.construct() && changed)
   }
  }
  do{let f=try Fixture(fresh,hash);var reached=false
   f.memory.beforeObjectAllocation={r in if r.count==0x174 {reached=true;if let b=f.host.bytes(r.context.esp+0x14,count:4) {b.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}}}}
   record("secondary allocation source stack tampering rejected",!f.construct() && reached && f.get(f.actor+0x70)==0)
  }
  do{let f=try Fixture(fresh,hash);var count=0;f.memory.failAllocation={slot in if slot==0x4a48e0 {count += 1};return count==2}
   record("secondary allocation exhaustion preserved",!f.construct() && count==2 && f.get(f.actor+0x70)==0)
  }
  do{let f=try Fixture(fresh,hash);let ready=f.construct() && f.host.retireTownGuard1(actor:f.actor,provider:f.memory)
   let world=f.get(f.actor+0x0c),copy:UInt32=0x62010000
   let bytes=Array(UnsafeBufferPointer(start:f.heap.lookupBytes(world,count:0x18)!,count:0x18));f.heap.storeBytes(token:copy,count:0x18).update(from:bytes,count:bytes.count);f.put(f.actor+0x0c,copy)
   record("secondary rebind rejects redirected scene owner",ready && !f.construct())
  }
  do{let f=try Fixture(fresh,hash,isolateMetadata:true);let ready=f.construct() && f.host.retireTownGuard1(actor:f.actor,provider:f.memory)
   let world=f.get(f.actor+0x0c),registry=f.get(world+0x14)
   let bytes=Array(UnsafeBufferPointer(start:f.heap.lookupBytes(registry,count:0x14)!,count:0x14));f.heap.free(registry);f.heap.storeBytes(token:registry,count:0x14).update(from:bytes,count:bytes.count)
   record("secondary rebind rejects replaced registry identity",ready && !f.construct())
  }
  do{let f=try Fixture(fresh,hash);let ready=f.construct();var nested:ClawNativeCanonicalHost.Completion?;var injected=false
   f.inject={c in if c.function==0x4c80c0 && !injected {injected=true;nested=f.host.invoke(f.call())}}
   let retired=f.host.retireTownGuard1(actor:f.actor,provider:f.memory,retireSecondary:true)
   record("secondary teardown observer reentry rejected",ready && injected && !retired && nested?.completed==false)
  }
  var stringRetirements:[[String:Any]]=[]
  for spec in ref["string_retirements"] as! [[String:Any]] {stringRetirements.append(try Fixture(p,hash).stringRetirement(spec))}
  let wwd=try Fixture(ref["wwd"] as! [String:Any],hash).wwdPrefix()
  let result:[String:Any]=["profiles":output,"controls":controls,"string_retirements":stringRetirements,"wwd":wwd];try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"));print("native profiles \(output.count), controls \(controls.count)")
 }
}
