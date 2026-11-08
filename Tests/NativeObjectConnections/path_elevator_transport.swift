import Foundation
private func u(_ x:Any)->UInt32 {(x as! NSNumber).uint32Value}
private func decode(_ s:String)->[UInt8] {let b=Array(s.utf8);func n(_ c:UInt8)->UInt8 {c>=97 ? c-87:c-48};return stride(from:0,to:b.count,by:2).map{n(b[$0])*16+n(b[$0+1])}}
private func args(_ c:ClawCall)->[UInt32] {var c=c;return withUnsafeBytes(of:&c.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(c.argumentCount)))}}
private final class Fixture {
 let heap=ClawTokenHeap();let host:ClawNativeCanonicalHost;let memory:ClawNativeMfcMemory;let p:[String:Any]
 var events:[[Any]]=[];var calls:[[Any]]=[];var stages:[[String:Any]]=[];var inject:((ClawCall)->Void)?;var missing=false;var completed=true;var allocationWitnesses:[Bool]=[];var paletteStackOutput=false
 init(_ p:[String:Any],_ hash:String)throws {
  self.p=p
  for b in p["initial"] as! [[String:Any]] {let d=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(d.count)).update(from:d,count:d.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
  let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:0x61000000,sceneObjectAllocations:true)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in
   if [UInt32(0x4f63ec),0x4683a0,0x468540,0x468890,0x4688f0,0x4f6286,0x4f6428].contains(c.function) {
    var a=args(c);if c.function==0x4f6286 && a.count==2 {a[1]=0}
    self.calls.append([c.function,c.receiver,a]);if c.function==0x4f6428 {self.events.append(["free",a[0]])}
   };self.inject?(c)
  }
  memory.beforeObjectAllocation={ [unowned self] r in
   let expected:UInt32=r.count==0x104 ? 0x49ee85:0x49eec1
   let continuation=self.host.bytes(r.context.esp+0x14,count:4).map{UnsafeRawPointer($0).loadUnaligned(as:UInt32.self)}
   self.allocationWitnesses.append(r.root==0x49ee30 && r.function==0x4a48e0 && r.returnPC==0x4f63ff && continuation==expected)
  }
  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]])}}
 }
 var actor:UInt32 {u(p["actor"]!)};var state:UInt32 {u(p["state"]!)}
 func get(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)![0]}
 func put(_ a:UInt32,_ v:UInt32){heap.lookup(a,words:1)![0]=v}
 func string(_ a:UInt32)->String? {var bytes:[UInt8]=[];for i:UInt32 in 0..<64 {guard let p=host.bytes(a+i,count:1) else{return nil};if p[0]==0{return String(bytes:bytes,encoding:.ascii)};bytes.append(p[0])};return nil}
 func service(_ c:ClawCall)->UInt32? {
  guard !missing,c.function==0x4f6286,c.receiver==0x10007010 else{return nil}
  let a=args(c);guard a.count==2,let key=string(a[0]),let output=host.bytes(a[1],count:4) else{return nil}
  paletteStackOutput = a[1]>=UInt32(CLAW_STACK_BASE) && a[1]+4<=UInt32(CLAW_STACK_END)
  let value:UInt32=p["label"] as! String == "level-ten-miss" ? 99:17
  output.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee=value};events.append(["lookup",c.receiver,key,value]);return 1
 }
 func call(_ root:UInt32=0x49ee30,_ receiver:UInt32=0,_ a:[UInt32]?=nil)->ClawCall {
  var c=ClawCall();c.function=root;c.receiver=receiver;let values=a ?? [actor];c.argumentCount=UInt32(values.count)
  withUnsafeMutableBytes(of:&c.arguments){raw in let q=raw.bindMemory(to:UInt32.self);for i in values.indices{q[i]=values[i]}};return c
 }
 @discardableResult func invoke(_ c:ClawCall?=nil)->Bool {let r=host.withObjectAllocation(provider:memory){host.invoke(c ?? call())};let ok=r?.completed==true;completed = completed && ok;return ok}
 func snapshot(_ index:Int) {
  let expected=(p["stages"] as! [[String:Any]])[index]
  let bytes=(expected["bytes"] as! [[String:Any]]).map {b->[String:Any] in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);let value=heap.lookupBytes(a,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing";return["address":a,"data":value]}
  stages.append(["name":expected["name"]!,"bytes":bytes])
 }
 func run()->[String:Any] {
  if invoke() {snapshot(0);if invoke() {snapshot(1);let helper=get(state+0x18);let body=p["label"] as! String == "destructor-body-then-scalar"
   if body && invoke(call(0x49f040,helper,[])) {snapshot(2)}
   if invoke(call(0x49f020,helper,[1])) {snapshot(body ? 3:2)}}}
  let retired=(p["allocations"] as! [[NSNumber]]).allSatisfy{heap.lookupBytes($0[0].uint32Value,count:1)==nil && !memory.ownsObjectAllocation($0[0].uint32Value,count:$0[1].uint32Value)}
  return["label":p["label"]!,"completed":completed,"fault":host.fault.map{String(describing:$0)} ?? "none","retired":retired,"allocation_witnesses":allocationWitnesses,"palette_stack_output":paletteStackOutput,"stages":stages,"events":events,"calls":calls]
 }
}
@main struct PathElevatorTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]);let ref=try JSONSerialization.jsonObject(with:Data(contentsOf:dir.appendingPathComponent("reference.json"))) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  let output=try profiles.map{try Fixture($0,hash).run()};var controls:[[String:Any]]=[]
  func record(_ n:String,_ ok:Bool){controls.append(["name":n,"passed":ok])}
  do{let f=try Fixture(p,hash);record("provider scope required",!f.host.invoke(f.call()).completed && f.events.isEmpty)}
  do{let f=try Fixture(p,hash),foreign=try Fixture(p,hash);let r=f.host.withObjectAllocation(provider:foreign.memory){f.host.invoke(f.call())};record("foreign provider rejected",r==nil && f.events.isEmpty)}
  for root:UInt32 in [0x49ee31,0x4f63ec] {let f=try Fixture(p,hash);record("wrong allocation root \(root)",!f.invoke(f.call(root,0,[0x104])) && f.events.isEmpty)}
  do{let f=try Fixture(p,hash);record("wrong callback receiver",!f.invoke(f.call(0x49ee30,4)) && f.events.isEmpty)}
  do{let f=try Fixture(p,hash);record("wrong callback actor",!f.invoke(f.call(0x49ee30,0,[f.actor+4])) && f.events.isEmpty)}
  do{let f=try Fixture(p,hash);record("overflowing callback actor rejected",!f.invoke(f.call(0x49ee30,0,[UInt32.max])) && f.events.isEmpty)}
  do{let f=try Fixture(p,hash);f.put(f.state+0x10,0x49ee31);record("wrong state callback rejected",!f.invoke() && f.events.isEmpty)}
  do{let f=try Fixture(p,hash);f.put(f.actor+0x6c,UInt32.max);record("wrong actor state rejected",!f.invoke() && f.events.isEmpty)}
  do{let f=try Fixture(profiles.first{$0["label"] as! String == "level-ten-match"}!,hash);f.missing=true;record("missing palette service rejected",!f.invoke())}
  for mode in ["owner-overflow","registry-overflow","observer-owner","observer-registry"] {
   let f=try Fixture(profiles.first{$0["label"] as! String == "level-ten-match"}!,hash);var changed=false
   if mode=="owner-overflow" {f.put(f.actor+0xc,UInt32.max)}
   if mode=="registry-overflow" {f.put(0x10006010,UInt32.max)}
   f.inject={c in if !changed && c.function==0x4f6286 {changed=true;if mode=="observer-owner" {f.put(f.actor+0xc,0x10006004)};if mode=="observer-registry" {f.put(0x10006010,0x10007004)}}}
   record("palette \(mode) rejected",!f.invoke())
  }
  for index in [1,2] {let f=try Fixture(p,hash);var seen=0;f.memory.failAllocation={slot in if slot==0x4a48e0 {seen+=1};return seen==index};record("allocation \(index) exhaustion preserves original handler dependency",!f.invoke() && f.host.fault?.address==0x5022b5 && f.heap.lookupBytes(index==1 ? 0x61000000:0x61000110,count:1)==nil)}
  do{let f=try Fixture(p,hash);let bytes=f.heap.storeBytes(token:0x61000000,count:0x104);bytes.update(repeating:0xa7,count:0x104);record("occupied allocation is preserved exhaustion",!f.invoke() && UnsafeBufferPointer(start:bytes,count:0x104).allSatisfy{$0==0xa7})}
  do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={_ in f.heap.free(0x10000000);_=f.heap.storeBytes(token:0x10000000,count:0x10000)};record("actor allocation replacement rejected",!f.invoke() && f.events.isEmpty)}
  do{let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={_ in f.put(f.actor+0x6c,f.state+4)};record("actor state link mutation rejected",!f.invoke() && f.events.isEmpty)}
  do{let f=try Fixture(p,hash);f.memory.afterService={slot,_,token in if slot==0x4a48e0 && token != 0 {f.heap.free(token);_=f.heap.storeBytes(token:token,count:0x104)}};record("returned allocation replacement rejected",!f.invoke())}
  do{let f=try Fixture(p,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(f.call())};record("physical callback reentry rejected",!f.invoke() && nested?.completed==false)}
  do{let f=try Fixture(p,hash);var rejected=false;let r:Void?=f.host.withObjectAllocation(provider:f.memory){rejected=f.host.withObjectAllocation(provider:f.memory){f.host.invoke(f.call())}==nil};record("nested provider scope rejected",r==nil && rejected && f.events.isEmpty)}
  for delta:UInt32 in [0,4,0x14,0x18] {let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={r in f.host.bytes(r.context.esp+delta,count:4)?.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee ^= 4}};record("allocation source stack \(delta) tampering rejected",!f.invoke() && f.events.isEmpty)}
  for mode in ["size","receiver","actor","continuation"] {
   let f=try Fixture(p,hash);var once=false;f.inject={c in if !once && c.function==0x4f63ec {once=true;var wrong=c
    if mode=="size" {wrong.arguments.0=0x103};if mode=="receiver" {wrong.receiver=4};if mode=="actor" {wrong.function=0x49ee30;wrong.arguments.0=f.actor+4};if mode=="continuation" {wrong.sourceReturnPC=0x49ee86};_=f.host.callNativeDependency(wrong)
   }};record("wrong \(mode) request during callback rejected",!f.invoke() && once)
  }
  do{let f=try Fixture(p,hash);var request:ClawNativeCanonicalHost.ObjectAllocationRequest?;f.memory.beforeObjectAllocation={request=$0};let ok=f.invoke();record("single-use expired lease",ok && request.map{!$0.consume(for:f.host,provider:f.memory) && !$0.validReturn(for:f.host)}==true);record("two allocation identities retained",ok && f.memory.ownsObjectAllocation(0x61000000,count:0x104) && f.memory.ownsObjectAllocation(0x61000110,count:0x18))}
  do{let f=try Fixture(p,hash);let ok=f.invoke();f.put(f.state+0x1c,0);record("stale live helper cannot allocate again",ok && !f.invoke())}
  do{let f=try Fixture(p,hash);let ok=f.invoke();if ok {let helper=f.get(f.state+0x18);f.heap.free(helper);_=f.heap.storeBytes(token:helper,count:0x18)};record("retained helper replacement rejected on tick",ok && !f.invoke())}
  do{let f=try Fixture(p,hash);let ok=f.invoke();if ok {let path=f.get(f.get(f.state+0x18)+8);f.heap.free(path);_=f.heap.storeBytes(token:path,count:0x104)};record("retained path replacement rejected on tick",ok && !f.invoke())}
  do{let f=try Fixture(p,hash);let ok=f.invoke();if ok {f.put(f.get(f.state+0x18)+8,0x61000004)};record("retained path link corruption rejected on tick",ok && !f.invoke())}
  for mode in ["helper-owner","helper-path","state-helper"] {
   let f=try Fixture(p,hash);let ok=f.invoke();var changed=false
   f.inject={c in if !changed && c.function==0x4688f0 {changed=true;let helper=f.get(f.state+0x18)
    if mode=="helper-owner" {f.put(helper+4,f.actor+4)};if mode=="helper-path" {f.put(helper+8,0x61000004)};if mode=="state-helper" {f.put(f.state+0x18,helper+4)}
   }};record("tick observer \(mode) mutation rejected",ok && !f.invoke() && changed)
  }
  do{let f=try Fixture(p,hash);let ok=f.invoke();record("wrong destructor receiver rejected",ok && !f.invoke(f.call(0x49f020,f.get(f.state+0x18)+4,[1])))}
  do{let f=try Fixture(p,hash);let ok=f.invoke();let helper=ok ? f.get(f.state+0x18):0;let released=ok && f.invoke(f.call(0x49f020,helper,[1]));record("double source destructor rejected",ok && released && !f.invoke(f.call(0x49f020,helper,[1])))}
  do{let f=try Fixture(p,hash);let ok=f.invoke();let helper=ok ? f.get(f.state+0x18):0
   let body=ok && f.invoke(f.call(0x49f020,helper,[0]));let kept=body && f.memory.ownsObjectAllocation(helper,count:0x18) && !f.memory.ownsObjectAllocation(0x61000000,count:0x104)
   let deleted=kept && f.invoke(f.call(0x49f020,helper,[1]));record("flags zero retains helper then flags one retires it",deleted && f.heap.lookupBytes(helper,count:1)==nil)
  }
  do{let f=try Fixture(p,hash);let ok=f.invoke();let helper=ok ? f.get(f.state+0x18):0;let r=ok ? f.host.invoke(f.call(0x49f020,helper,[1])):nil;record("destructor requires provider scope",ok && r?.completed==false && f.heap.lookupBytes(helper,count:1) != nil)}
  do{let f=try Fixture(p,hash);let ok=f.invoke();let helper=ok ? f.get(f.state+0x18):0
   let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
   let foreign=try ClawNativeMfcMemory(host:f.host,sha256:hash,importTargets:imports,allocationBase:0x62000000,sceneObjectAllocations:true)
   let r=f.host.withObjectAllocation(provider:foreign){f.host.invoke(f.call(0x49f020,helper,[1]))};record("same-host foreign owner cannot retire helper",ok && r==nil && f.heap.lookupBytes(helper,count:1) != nil)
  }
  // Separate actor/state allocations so replacing one proves its own retained
  // identity check. The actual owner-destructor path is compared in the audit;
  // these controls isolate the election at its already-cleared helper entry.
  var retirementProfile=p
  var initial=p["initial"] as! [[String:Any]]
  let graph=initial.removeFirst()["data"] as! String,graphBytes=decode(graph)
  initial.insert(contentsOf:(0..<8).map{i in ["address":UInt32(0x10000000+i*0x1000),"data":graphBytes[(i*0x1000)..<((i+1)*0x1000)].map{String(format:"%02x",$0)}.joined()]},at:0)
  retirementProfile["initial"]=initial
  func retirement()->Fixture {
   let f=try! Fixture(retirementProfile,hash)
   precondition(f.invoke());f.put(f.state,0x513740);f.put(f.state+0x10,0)
   return f
  }
  func replace(_ f:Fixture,_ token:UInt32,_ count:UInt32) {
   let bytes=Array(UnsafeBufferPointer(start:f.heap.lookupBytes(token,count:count)!,count:Int(count)))
   f.heap.free(token);f.heap.storeBytes(token:token,count:count).update(from:bytes,count:bytes.count)
  }
  for mode in ["actor","state","path","helper","state-link","helper-link","helper-owner","helper-path","helper-vtable","callback","owner-vtable","pending-buffer"] {
   let f=retirement(),helper=f.get(f.state+0x18);let before=f.events.count
   switch mode {
   case "actor":replace(f,f.actor,0x1000)
   case "state":replace(f,f.state,0x1000)
   case "path":replace(f,0x61000000,0x104)
   case "helper":replace(f,helper,0x18)
   case "state-link":f.put(f.actor+0x6c,f.state+4)
   case "helper-link":f.put(f.state+0x18,helper+4)
   case "helper-owner":f.put(helper+4,f.actor+4)
   case "helper-path":f.put(helper+8,0x61000004)
   case "helper-vtable":f.put(helper,0x50b014)
   case "callback":f.put(f.state+0x10,0x49ee31)
   case "owner-vtable":f.put(f.state,0x513770)
   default:f.put(f.state+0x14,0x61000000)
   }
   record("owner retirement \(mode) rejected",!f.invoke(f.call(0x49f020,helper,[1])) && f.events.count==before && f.heap.lookupBytes(helper,count:0x18) != nil && f.heap.lookupBytes(0x61000000,count:0x104) != nil)
  }
  for root:UInt32 in [0x49f040,0x49f020] {
   let f=retirement(),helper=f.get(f.state+0x18),before=f.events.count
   record("cleared callback rejects non-owner destructor \(root)",!f.invoke(f.call(root,helper,root==0x49f040 ? []:[0])) && f.events.count==before)
  }
  do{let f=try Fixture(retirementProfile,hash);let ok=f.invoke();f.put(f.state+0x10,0)
   record("cleared callback without owner state rejected",ok && !f.invoke(f.call(0x49f020,f.get(f.state+0x18),[1])))
  }
  for phase in [1,2] {
   for mode in ["actor","state","path","helper","state-link","helper-link","callback","owner-vtable","pending-buffer","reentry","helper-owner","helper-path"] {
    // The path has already been freed before the second physical free.
    if phase==2 && ["path","helper-owner","helper-path"].contains(mode) {continue}
    let f=retirement(),helper=f.get(f.state+0x18);var seen=0,changed=false
    f.inject={c in guard c.function==0x4f6428 else{return};seen+=1;guard seen==phase else{return};changed=true
     switch mode {
     case "actor":replace(f,f.actor,0x1000)
     case "state":replace(f,f.state,0x1000)
     case "path":replace(f,0x61000000,0x104)
     case "helper":replace(f,helper,0x18)
     case "state-link":f.put(f.actor+0x6c,f.state+4)
     case "helper-link":f.put(f.state+0x18,helper+4)
     case "callback":f.put(f.state+0x10,0x49ee30)
     case "owner-vtable":f.put(f.state,0x513770)
     case "pending-buffer":f.put(f.state+0x14,0x61000000)
     case "helper-owner":f.put(helper+4,f.actor+4)
     case "helper-path":f.put(helper+8,0x61000004)
     default:_=f.host.invoke(f.call(0x49f020,helper,[1]))
     }
    }
    record("owner retirement free \(phase) \(mode) mutation rejected",!f.invoke(f.call(0x49f020,helper,[1])) && changed && f.heap.lookupBytes(helper,count:0x18) != nil && (phase==2 || f.heap.lookupBytes(0x61000000,count:0x104) != nil))
   }
  }
  do{let f=retirement(),helper=f.get(f.state+0x18)
   let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
   let foreign=try ClawNativeMfcMemory(host:f.host,sha256:hash,importTargets:imports,allocationBase:0x62000000,sceneObjectAllocations:true)
   let r=f.host.withObjectAllocation(provider:foreign){f.host.invoke(f.call(0x49f020,helper,[1]))}
   record("cleared owner rejects foreign provider",r==nil && f.memory.ownsObjectAllocation(helper,count:0x18))
  }
  do{let f=retirement(),helper=f.get(f.state+0x18);let released=f.invoke(f.call(0x49f020,helper,[1]))
   record("cleared owner rejects double retirement",released && !f.invoke(f.call(0x49f020,helper,[1])) && f.heap.lookupBytes(helper,count:1)==nil && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  let result:[String:Any]=["profiles":output,"controls":controls];try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"));print("native profiles \(output.count), controls \(controls.count)")
 }
}
