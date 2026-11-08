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
private let observed:Set<UInt32>=[0x42a680,0x4f63ec,0x484ca0,0x4c96b0,0x4dc870,0x4c9e30,0x4848d0,0x4041b0,0x4dca10,0x4f6428,0x484d90,0x4c7fa0,0x4c8060,0x4c7970,0x4062e0,0x4061b0,0x4c8220,0x4c82a0,0x4f6286,0x4f6974,0x4dba00,0x406290,0x406240,0x408050,0x4c8da0,0x49f0a0,0x4c79e0,0x4082f0,0x4080a0,0x408220,0x408370]
private final class AudioWitness:ClawNativeCanonicalHost.ObjectAudioProvider {
 let audio:ClawNativeAudio
 var physical:[[String:Any]]=[]
 var missing:UInt32?
 init(_ audio:ClawNativeAudio){self.audio=audio}
 func validAudioBinding(for host:ClawNativeCanonicalHost)->Bool {audio.validAudioBinding(for:host)}
 func ownsAudioPool(_ token:UInt32)->Bool {audio.ownsAudioPool(token)}
 func retainAudioAllocation(_ token:UInt32,provider:ClawNativeCanonicalHost.ObjectAllocationProvider)->Bool {audio.retainAudioAllocation(token,provider:provider)}
 func audioPhysical(_ c:ClawCall,host:ClawNativeCanonicalHost)->UInt32? {
  if missing==c.function{return nil}
  let a=args(c),result=audio.audioPhysical(c,host:host)
  var event:[String:Any]=["function":c.function,"arguments":a,"result":result as Any? ?? NSNull()]
  if c.function==0x71020014 || [UInt32(0x71010018),0x7101001c,0x71010020,0x71010024].contains(c.function),let out=host.bytes(a.last!,count:4) {event["output"]=UnsafeRawPointer(out).loadUnaligned(as:UInt32.self)}
  physical.append(event);return result
 }
}
private final class Fixture {
 let heap=ClawTokenHeap();let host:ClawNativeCanonicalHost;let memory:ClawNativeMfcMemory;let p:[String:Any]
 var audio:AudioWitness?
 var invalidBacking=false;var events:[[Any]]=[];var calls:[[Any]]=[];var missing:UInt32?;var inject:((ClawCall)->Void)?
 var retired:[String:String]=[:];var allocationWitness=true;var allocationCount=0
 init(_ p:[String:Any],_ hash:String)throws {
  self.p=p
  for b in p["initial"] as! [[String:Any]] {let d=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(d.count)).update(from:d,count:d.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
  let storage=heap;let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().map{k in(k,storage.lookup(k,words:1)![0])})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:0x61000000,sceneObjectAllocations:true)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in
   if observed.contains(c.function) {self.calls.append([c.function,([UInt32(0x4f63ec),0x4dc870,0x4f6428,0x49f0a0].contains(c.function) ? 0:c.receiver),args(c)])}
   if c.function==0x4f6428 {let token=c.arguments.0;self.retired[String(token)]=self.hex(token,0x5c);self.events.append(["free",token])}
   self.inject?(c)
  }
  memory.beforeObjectAllocation={ [unowned self] r in
   guard r.count==0x5c else{return};self.allocationCount+=1;let offset=Int(r.context.esp-UInt32(CLAW_STACK_BASE)+0x14)
   self.allocationWitness=self.allocationWitness && r.root==0x4847b0 && r.count==0x5c && r.returnPC==0x4f63ff && r.stack.withUnsafeBytes{$0.loadUnaligned(fromByteOffset:offset,as:UInt32.self)}==0x4847ea
  }
  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]])}}
 }
 var actor:UInt32 {u(p["actor"]!)};var state:UInt32 {u(p["state"]!)};var player:UInt32 {u(p["player"]!)};var boss:UInt32 {u(p["boss"]!)}
 func get(_ a:UInt32)->UInt32 {guard let p=heap.lookup(a,words:1) else {invalidBacking=true;return 0};return p[0]}
 func put(_ a:UInt32,_ v:UInt32){guard let p=heap.lookup(a,words:1) else {invalidBacking=true;return};p[0]=v}
 func hex(_ a:UInt32,_ n:UInt32)->String {
  if let p=heap.lookupBytes(a,count:n) {return UnsafeBufferPointer(start:p,count:Int(n)).map{String(format:"%02x",$0)}.joined()}
  var result="";for i:UInt32 in 0..<n {guard let p=heap.lookupBytes(a+i,count:1) else{return "missing"};result+=String(format:"%02x",p[0])};return result
 }

 func string(_ a:UInt32)->String? {var bytes:[UInt8]=[];for i:UInt32 in 0..<256 {guard let p=host.bytes(a+i,count:1) else{return nil};if p[0]==0{return String(bytes:bytes,encoding:.ascii)};bytes.append(p[0])};return nil}
 func service(_ c:ClawCall)->UInt32? {
  let a=args(c);var f=c.function
  for slot:UInt32 in [0x546d5c,0x546cdc,0x5469e8,0x546cd4,0x546d24,0x546a40,0x546df0] {if get(slot)==f {f=slot}}
  if missing==f{return nil}
  switch f {
  case 0x546df0:
   guard a.isEmpty else{return nil};let tick=get(0x537210);events.append(["tick",tick]);return tick
  case 0x4f51c5:
   guard a.count==1,let tail=heap.lookup(c.receiver+8,words:1)?[0],let count=heap.lookup(c.receiver+12,words:1)?[0] else{return nil}
   let token=heap.allocate(bytes:12);guard token != 0 else{return nil}
   put(token,0);put(token+4,tail);put(token+8,a[0])
   if tail != 0 {put(tail,token)}else{put(c.receiver+4,token)}
   put(c.receiver+8,token);put(c.receiver+12,count+1);events.append(["list-append",c.receiver,a[0],token]);return token
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
  case 0x546a40:
   guard a.count==2 else{return nil};return host.bytes(a[0],count:a[1]) == nil ? 1:0
  case 0x4a3050:events.append(["rand",99]);return 99
  default:return nil
  }
 }
 func call()->ClawCall {var c=ClawCall();c.function=0x4847b0;c.argumentCount=1;c.arguments.0=actor;return c}
 func execute(_ command:UInt32,_ outgoing:inout ClawX87State)->Bool {
  put(state+0x1c,command);var completion:ClawNativeCanonicalHost.Completion?
  _=host.withObjectAllocation(provider:memory,audio:audio){if let r=host.withObjectX87Environment(outgoing,body:{host.invoke(call())}) {completion=r.0;outgoing=r.1}}
  return completion?.completed==true && host.fault==nil && !invalidBacking
 }
 func construct()->Bool {var outgoing=fp(p["incoming"] as! [Any]);return execute(0,&outgoing)}
 func snapshot(_ label:Any,_ shape:[String:Any],_ outgoing:ClawX87State)->[String:Any] {
  let final=(shape["final"] as! [[String:Any]]).map {b->[String:Any] in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);return["address":a,"data":hex(a,n)]}
  return["label":label,"outgoing":fpJSON(outgoing),"events":events,"entries":calls,"retired":retired,"final":final]
 }
 func installAudio()throws {
  heap.free(0x541178)
  let owner=try ClawNativeAudio(root:URL(fileURLWithPath:"App/GameData"),outputEnabled:false,sharedHeap:heap,preload:false)
  try owner.load(name:"LEVEL_REDTAIL_WINDWHISTLING",data:Data(contentsOf:URL(fileURLWithPath:"App/GameData/LEVEL13/SOUNDS/REDTAIL/WINDWHISTLING.WAV")))
  audio=AudioWitness(owner)
  let sound=owner.resolve(name:"LEVEL_REDTAIL_WINDWHISTLING")!,world=get(actor+0xc),map=get(world+0x28)+0x10
  var buckets=get(map+4)
  if buckets==0 {buckets=heap.allocate(bytes:4);put(map+4,buckets)}
  if get(map+8)==0 {put(map+8,1)}
  let node=heap.allocate(bytes:16)
  put(node,get(buckets));put(node+8,0x52bb4c);put(node+12,sound.resourceToken);put(buckets,node);put(map+12,get(map+12)+1)
  put(0x532c0c,1)
 }
 func segments()->[[String:Any]] {
  heap.debugAllocationBases.map {base in
   var low:UInt32=1,high:UInt32=4<<20
   while low<high {let mid=low+(high-low+1)/2;if heap.lookupBytes(base,count:mid) != nil {low=mid}else{high=mid-1}}
   return ["address":base,"data":hex(base,low)]
  }
 }
 func runAudio()throws->[String:Any] {
  try installAudio()
  let initial=segments();var out=fp(p["incoming"] as! [Any]),steps:[[String:Any]]=[]
  for (i,command) in [UInt32(0),1001,1002,1002].enumerated() {
   if i==1 {put(boss+0x4e4,1)}
   if i==2 {put(get(state+0x18)+0x54,1234);put(get(state+0x18)+0x58,100)}
   if i==3 {put(0x537210,2234)}
   events=[];calls=[];audio!.physical=[]
   let ok=execute(command,&out)
   steps.append(["command":command,"completed":ok,"fault":host.fault.map{String(describing:$0)} ?? "none","events":events,"calls":calls,"physical":audio!.physical,"final":segments(),"outgoing":fpJSON(out)])
   if !ok {break}
  }
  return ["actor":actor,"state":state,"boss":boss,"initial":initial,"incoming":p["incoming"]!,"steps":steps,"output_enabled":false]
 }
 func run()->[String:Any] {
  var outgoing=fp(p["incoming"] as! [Any]),completed=true;var phases:[[String:Any]]=[]
  let expected=p["phases"] as! [[String:Any]]
  for (i,command) in [UInt32(0),1000,29,30,1001,1001,1002,1002].enumerated() {
   if i==5 {put(boss+0x4e4,1)}
   if i==6 {let helper=get(state+0x18);put(helper+0x54,1234);put(helper+0x58,100)}
   if i==7 {put(0x537210,2234)}
   if !execute(command,&outgoing) {completed=false;break}
   phases.append(snapshot(command,expected[i],outgoing))
  }
  if completed {
   completed=host.retireRedTailWind(actor:actor,provider:memory)
   if completed {phases.append(snapshot("retire",expected[8],outgoing));completed=execute(0,&outgoing);if completed {phases.append(snapshot("recreate",expected[9],outgoing))}}
  }
  return["completed":completed,"allocation_witness":allocationWitness && allocationCount==2,"fault":host.fault.map{String(describing:$0)} ?? "none","phases":phases,"calls":calls]
 }
}
@main struct RedTailWindTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]);let ref=try JSONSerialization.jsonObject(with:Data(contentsOf:dir.appendingPathComponent("reference.json"))) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]],p=profiles[0]
  var output:[[String:Any]]=[];for profile in profiles{output.append(try Fixture(profile,hash).run())}
  var controls:[[String:Any]]=[]
  func record(_ name:String,_ passed:Bool){controls.append(["name":name,"passed":passed])}
  for (i,row) in output.enumerated() {if row["completed"] as? Bool==true {record("allocation continuation witness \(i)",row["allocation_witness"] as? Bool==true)}}
  do {let f=try Fixture(p,hash);record("provider required",!f.host.invoke(f.call()).completed)}
  do {let f=try Fixture(p,hash),other=try Fixture(p,hash);record("foreign provider",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(f.call())}==nil)}
  do {let f=try Fixture(p,hash);f.put(f.state+0x10,0x4847b1);record("wrong root",!f.construct() && f.host.fault != nil)}
  do {let f=try Fixture(p,hash);f.put(f.actor+0x6c,f.state+4);record("wrong actor",!f.construct() && f.host.fault != nil)}
  do {let f=try Fixture(p,hash);f.missing=0x4f6286;record("missing service",!f.construct() && f.host.fault != nil)}
  do {let f=try Fixture(p,hash);f.memory.failAllocation={$0==0x4a48e0};record("allocation exhaustion",!f.construct() && f.host.fault?.address==0x5022b5 && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do {let f=try Fixture(p,hash);let b=f.heap.storeBytes(token:0x61000000,count:0x5c);b.update(repeating:0xa7,count:0x5c);record("occupied allocation",!f.construct() && UnsafeBufferPointer(start:b,count:0x5c).allSatisfy{$0==0xa7})}
  do {let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={_ in _=f.host.invoke(f.call())};record("reentry",!f.construct() && f.host.fault != nil)}
  do {let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={r in if let b=f.host.bytes(r.context.esp+0x14,count:4) {UnsafeMutableRawPointer(b).storeBytes(of:UInt32(0x4847eb),as:UInt32.self)}};record("wrong continuation",!f.construct() && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do {let f=try Fixture(p,hash);f.memory.beforeObjectAllocation={r in if let b=f.host.bytes(r.context.esp+0x18,count:4) {UnsafeMutableRawPointer(b).storeBytes(of:UInt32(0x58),as:UInt32.self)}};record("wrong allocation size",!f.construct() && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do {let f=try Fixture(p,hash);let setup=f.construct();f.missing=0x4f6974;var out=fp(p["incoming"] as! [Any]);record("missing lifecycle service",setup && !f.execute(1001,&out) && f.host.fault != nil)}
  do {let f=try Fixture(p,hash);let setup=f.construct();var c=ClawCall();c.function=0x4c9e30;c.receiver=f.get(f.state+0x18)+4;c.argumentCount=1;c.arguments.0=0
   let result=f.host.withObjectAllocation(provider:f.memory){f.host.invoke(c)};record("unbound stdcall receiver",setup && result?.completed != true && f.host.fault != nil)
  }
  for mode in ["size","receiver","continuation"] {
   let f=try Fixture(p,hash);var injected=false
   f.inject={c in if !injected && c.function==(mode=="size" ? 0x4f63ec:0x484ca0) {injected=true;var bad=c;if mode=="size"{bad.arguments.0=0x1b4};if mode=="receiver"{bad.receiver &+= 4};if mode=="continuation"{bad.sourceReturnPC=0x484806};_=f.host.callNativeDependency(bad)}}
   record("reentrant wrong \(mode)",!f.construct() && f.host.fault != nil && injected)
  }
  for mode in ["actor","helper","logic"] {
   let f=try Fixture(p,hash);let setup=f.construct();let token:UInt32=mode=="helper" ? f.get(f.state+0x18):(mode=="actor" ? f.actor:f.state);let size:UInt32=mode=="helper" ? 0x5c:(mode=="actor" ? 0x200:0x180)
   if setup {let bytes=decode(f.hex(token,size));f.heap.free(token);f.heap.storeBytes(token:token,count:size).update(from:bytes,count:bytes.count)}
   var out=fp(p["incoming"] as! [Any]);record("stale \(mode) identity",setup && !f.execute(29,&out) && f.host.fault != nil)
  }
  for mode in ["vtable","slot"] {
   let f=try Fixture(p,hash);let setup=f.construct();if setup {if mode=="vtable"{f.put(f.get(f.state+0x18),0x50b014)}else{f.put(0x50f46c+0x20,0x4bb030)}}
   var out=fp(p["incoming"] as! [Any]);record("wrong \(mode)",setup && !f.execute(29,&out) && f.host.fault != nil)
  }
  do {let f=try Fixture(p,hash);let setup=f.construct(),helper=f.get(f.state+0x18);record("unauthorized free",setup && !f.memory.releaseSceneObject(helper) && f.memory.ownsObjectAllocation(helper,count:0x5c))}
  do {let f=try Fixture(p,hash);let setup=f.construct();record("foreign free",setup && !f.memory.releaseSceneObject(f.actor) && f.heap.lookupBytes(f.actor,count:0x1b4) != nil)}
  do {let f=try Fixture(p,hash);let setup=f.construct(),helper=f.get(f.state+0x18),retired=f.host.retireRedTailWind(actor:f.actor,provider:f.memory);record("same owner retirement",setup && retired && !f.memory.ownsObjectAllocation(helper,count:0x5c) && f.get(f.state+0x18)==0);record("double free",retired && !f.memory.releaseSceneObject(helper))}
  do {let f=try Fixture(p,hash);let setup=f.construct(),retired=f.host.retireRedTailWind(actor:f.actor,provider:f.memory);record("double retirement",setup && retired && !f.host.retireRedTailWind(actor:f.actor,provider:f.memory))}
  do {let f=try Fixture(p,hash);let setup=f.construct(),first=f.get(f.state+0x18)
   let freed=setup && f.host.retireRedTailWind(actor:f.actor,provider:f.memory)
   let sentinel=f.heap.allocate(bytes:0x40)
   if let b=f.heap.lookupBytes(sentinel,count:0x40) {b.update(repeating:0x5a,count:0x40)}
   let recreated=freed && f.construct(),helper=f.get(f.state+0x18)
   let intact:Bool=f.heap.lookupBytes(sentinel,count:0x40).map{UnsafeBufferPointer(start:$0,count:0x40).allSatisfy{$0==0x5a}} ?? false
   record("shared scene cursor cooperation",setup && freed && sentinel != 0 && recreated && helper != first && UInt64(helper)>=UInt64(sentinel)+0x40 && intact && f.memory.ownsObjectAllocation(helper,count:0x5c))
   controls[controls.count-1]["diagnostic"]=["setup":setup,"freed":freed,"sentinel":sentinel,"recreated":recreated,"helper":helper,"first":first,"intact":intact,"fault":f.host.fault.map{String(describing:$0)} ?? "none"]
  }
  for target:UInt32 in [0x4f63ec,0x484ca0] {
   let f=try Fixture(p,hash);var c=ClawCall();c.function=target;c.argumentCount=1;c.receiver=target==0x484ca0 ? 0x61000000:0;c.arguments.0=target==0x484ca0 ? f.actor:0x5c
   let result=f.host.withObjectAllocation(provider:f.memory){f.host.invoke(c)}
   record("unbound entry \(target)",result?.completed != true && f.host.fault != nil)
  }
  do {let f=try Fixture(p,hash);try f.installAudio();f.audio!.missing=0x71010024;record("missing audio physical service",!f.construct() && f.host.fault != nil)}
  do {let f=try Fixture(p,hash);try f.installAudio();let sound=f.audio!.audio.resolve(name:"LEVEL_REDTAIL_WINDWHISTLING")!;var injected=false
   f.inject={c in if c.function==0x4dba00 && !injected {injected=true;f.put(sound.resourceToken+0x10,sound.voicePoolToken+4)}}
   record("replaced sound pool before registry",!f.construct() && injected && f.host.fault != nil)
  }
  do {let f=try Fixture(profiles[2],hash);let setup=f.construct();var out=fp(p["incoming"] as! [Any]);f.put(f.boss+0x4e4,1);let active=setup && f.execute(1001,&out);var replaced=false
   f.inject={c in if c.function==0x4a3050 && !replaced {let world=f.get(f.state+0xc),factory=f.get(world+8),node=f.get(factory+0x14)
    if node != 0 {let actor=f.get(node+8),state=f.get(actor+0x6c),helper=f.get(state+0x18)
     if helper != 0 {let bytes=decode(f.hex(helper,0x1b0));f.heap.free(helper);f.heap.storeBytes(token:helper,count:0x1b0).update(from:bytes,count:bytes.count);replaced=true}
    }
   }}
   record("replaced debris helper during resumed random",active && !f.execute(1002,&out) && replaced && f.host.fault != nil)
  }
  let enabled=try Fixture(p,hash).runAudio()
  let data=try JSONSerialization.data(withJSONObject:["profiles":output,"controls":controls,"enabled_audio":enabled],options:[.sortedKeys]);print(String(decoding:data,as:UTF8.self))
 }
}
