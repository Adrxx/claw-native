import Foundation
private let base:UInt32=0x10000000,actor:UInt32=0x10001000,logic:UInt32=0x10002000
private let animations:UInt32=0x10006000,images:UInt32=0x10007000,sounds:UInt32=0x10008000,hit:UInt32=0x10009000,attack:UInt32=0x1000a000
private let animation:UInt32=0x1000c000,image:UInt32=0x1000e000
private func u(_ v:Any)->UInt32 {(v as! NSNumber).uint32Value}
private func decode(_ s:String)->[UInt8] {var b:[UInt8]=[];var i=s.startIndex;while i<s.endIndex {let n=s.index(i,offsetBy:2);b.append(UInt8(s[i..<n],radix:16)!);i=n};return b}
private func hex(_ p:UnsafeMutablePointer<UInt8>,_ n:UInt32)->String {UnsafeBufferPointer(start:p,count:Int(n)).map{String(format:"%02x",$0)}.joined()}
private func args(_ c:ClawCall)->[UInt32] {var c=c;return withUnsafeBytes(of:&c.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(c.argumentCount)))}}
private final class Fixture {
 let heap=ClawTokenHeap();let host:ClawNativeCanonicalHost;let memory:ClawNativeMfcMemory;let profile:[String:Any]
 var ambient:ClawX87State?
 var retired:[String:String]=[:]
 var events:[[Any]]=[],calls:[[UInt32]]=[];var removed:UInt32?;var reenter=false
 init(_ p:[String:Any],_ hash:String)throws {
  profile=p
  for b in p["initial"] as! [[String:Any]] {let d=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(d.count)).update(from:d,count:d.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
  let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
  for (slot,target) in imports {heap.lookup(slot,words:1)![0]=target}
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:0x61000000,sceneObjectAllocations:true)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in self.calls.append([c.function,c.receiver]);if c.function==0x4f6428 {self.events.append(["free",args(c)[0]])}}
  memory.beforeService={ [unowned self] f,a in if f==0x4a49b0,let row=self.memory.tlsSnapshot().allocations.first(where:{$0.address==a[0]}),let bytes=self.heap.lookupBytes(a[0],count:row.size) {self.retired[String(a[0])]=hex(bytes,row.size)}}
  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]])} else if f==0x4a49b0 {self.events.append(["free",a[0]])}}
 }
 func put(_ a:UInt32,_ v:UInt32){heap.lookup(a,words:1)![0]=v}
 func get(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)![0]}
 func text(_ token:UInt32)->String? {var b:[UInt8]=[];for i:UInt32 in 0..<128 {guard let p=host.bytes(token+i,count:1) else{return nil};if p[0]==0{return String(bytes:b,encoding:.ascii)};b.append(p[0])};return nil}
 func callback(_ token:UInt32=actor)->ClawCall {var c=ClawCall();c.function=0x421200;c.argumentCount=1;c.arguments.0=token;return c}
 func service(_ c:ClawCall)->UInt32? {
  if removed==c.function{return nil};let a=args(c)
  if reenter {_=host.invoke(callback())}
  switch c.function {
  case 0x4f6286:
   guard a.count==2,let key=text(a[0]),let out=host.bytes(a[1],count:4) else{return nil};let value:UInt32
   if c.receiver==animations+0x10 {let name=key.replacingOccurrences(of:"LEVEL_CHAMELEON_",with:"");guard let i=["IDLE","FASTADVANCE","HIT","JUMP","KILLFALL","STRIKE1","GAME_NULL"].firstIndex(of:name) else{return nil};value=base+0x1c000+UInt32(i)*0x20}
   else if c.receiver==images+0x10 && key=="LEVEL_CHAMELEON" {value=image}
   else if c.receiver==sounds+0x10 {value=base+0x17000+UInt32(key.utf8.reduce(0){$0+Int($1)}%32)*0x20}
   else if c.receiver==hit+0x10 {value=key=="LogicAttack" ? base+0x1d100:base+0x1d000}
   else if c.receiver==attack+0x10 {value=base+0x1d100}
   else{return nil}
   out.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee=value};events.append(["registry",c.receiver,key,value]);return value==0 ? 0:1
  case 0x4f6974:
   guard a==[0] else{return nil};let value=get(c.receiver);events.append(["state-name",c.receiver,value]);return value
  case 0x4a3810:
   guard a.count==2,let left=text(a[0]),let right=text(a[1]) else{return nil};return left==right ? 0:left.lexicographicallyPrecedes(right) ? UInt32.max:1
  case 0x4a5290:
   guard a.count==3,a[2]<=0x100000 else{return nil};if a[2]==0{return a[0]};guard let src=host.bytes(a[1],count:a[2]),let dst=host.bytes(a[0],count:a[2]) else{return nil};let copy=Array(UnsafeBufferPointer(start:src,count:Int(a[2])));dst.update(from:copy,count:copy.count);return a[0]
  case 0x4b0d60:guard a.count==1,a[0]<=255 else{return nil};return a[0]==32 || (9...13).contains(a[0]) ? 8:0
  case 0x4b0d30:guard a.count==1,a[0]<=255 else{return nil};return (48...57).contains(a[0]) ? 4:0
  case 0x4a3050:events.append(["rand",95]);return 95
  case 0x546d5c,0x546cdc,0x68001000,0x68001010:
   guard a.count==((c.function==0x546d5c || c.function==0x68001000) ? 5:1),let p=host.bytes(a[0],count:16) else{return nil};let values=(c.function==0x546d5c || c.function==0x68001000) ? Array(a.dropFirst()):[UInt32](repeating:0,count:4)
   p.withMemoryRebound(to:UInt32.self,capacity:4){q in for i in 0..<4 {q[i]=values[i]}};events.append(["rectangle",a[0]]+values.map{$0 as Any});return 1
  case 0x5469e8,0x68001020:
   guard a.count==1,let p=host.bytes(a[0],count:4) else{return nil};let v=p.withMemoryRebound(to:UInt32.self,capacity:1){q->UInt32 in q[0] &-= 1;return q[0]};events.append(["decrement",a[0],v]);return v
  case 0x546cd4,0x68001030:
   guard a.count==3,let p=host.bytes(a[0],count:16) else{return nil};let q=p.withMemoryRebound(to:Int32.self,capacity:4){Array(UnsafeBufferPointer(start:$0,count:4))};let x=Int32(bitPattern:a[1]),y=Int32(bitPattern:a[2]);let v:UInt32=q[0]<=x && x<q[2] && q[1]<=y && y<q[3] ? 1:0;events.append(["point",a[0],a[1],a[2],v]);return v
  default:return nil
  }
 }
 func perform(_ step:[String:Any])->[String:Any] {
  let command=step["command"]!;events=[];calls=[];let firstMember=host.chameleonMemberSources.count;var completed=false;var result:UInt32?;var x87:[String:Any]=[:]
  var initial=ClawX87State();initial.size=UInt32(MemoryLayout<ClawX87State>.size);initial.version=UInt32(CLAW_X87_VERSION);let incoming=step["incoming_x87"] as! [String:Any];initial.control=u(incoming["control"]!);initial.status=u(incoming["status"]!);initial.count=u(incoming["count"]!)
  withUnsafeMutableBytes(of:&initial.slots){b in let q=b.bindMemory(to:ClawX87Value.self);for (i,row) in (incoming["slots"] as! [[Any]]).enumerated(){q[i].significand=UInt64(row[0] as! String)!;q[i].signExponent=u(row[1])}}
  if let prior=ambient {initial=prior}
  if let value=host.withObjectX87Environment(initial,body:{()->Bool in
   if let s=command as? String,s=="destroy" {let helper=get(logic+0x18);let retired=host.retireChameleon(actor:actor,provider:memory,retireSecondary:true);if retired {result=helper};return retired}
   put(logic+0x1c,u(command));return host.withObjectAllocation(provider:memory){let r=host.invoke(callback());result=r.eax;return r.completed} ?? false
  }) {completed=value.0;ambient=value.1;var state=value.1;let slots:[[Any]]=withUnsafeBytes(of:&state.slots){b in b.bindMemory(to:ClawX87Value.self).prefix(Int(state.count)).map{[String($0.significand),$0.signExponent]}};x87=["control":state.control,"status":state.status,"count":state.count,"slots":slots]}
  let ledger=memory.tlsSnapshot()
  if command as? String == "destroy",ledger.allocations.contains(where:{$0.live}) {completed=false}
  for row in ledger.allocations where !row.live {if let bytes=ledger.allocationBytes[String(row.address)] {retired[String(row.address)]=bytes.map{String(format:"%02x",$0)}.joined()}}
  let snapshots=(step["final"] as! [[String:Any]]).map {b->[String:Any] in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);return ["address":a,"data":heap.lookupBytes(a,count:n).map{hex($0,n)} ?? "missing"]}
  return ["command":command,"result":result.map{$0 as Any} ?? NSNull(),"completed":completed,"fault":host.fault.map{String(describing:$0)} ?? "","events":events,"calls":calls,"final":snapshots,"x87":x87,"retired":retired,"member_sources":host.chameleonMemberSources.dropFirst(firstMember).map{[$0.function,$0.returnPC,$0.input.ecx]}]
 }
}
@main struct ChameleonTransport {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]);let ref=try JSONSerialization.jsonObject(with:Data(contentsOf:dir.appendingPathComponent("reference.json"))) as! [String:Any]
  let profiles=ref["profiles"] as! [[String:Any]],hash=ref["executable_sha256"] as! String
  var output:[[String:Any]]=[]
  for p in profiles {let f=try Fixture(p,hash);var steps:[[String:Any]]=[];for s in p["steps"] as! [[String:Any]] {steps.append(f.perform(s))};output.append(["label":p["label"]!,"steps":steps])}
  var controls:[[String:Any]]=[];let p=profiles[0],first=(p["steps"] as! [[String:Any]])[0]
  func record(_ name:String,_ passed:Bool){controls.append(["name":name,"passed":passed])}
  func success(_ r:[String:Any])->Bool {r["completed"] as! Bool}
  do {let f=try Fixture(p,hash);f.removed=0x4f6286;record("missing service",!success(f.perform(first)) && f.host.fault != nil)}
  do {let f=try Fixture(p,hash),other=try Fixture(p,hash);record("wrong provider",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(f.callback())}==nil)}
  do {let f=try Fixture(p,hash);record("wrong actor",f.host.withObjectAllocation(provider:f.memory){f.host.invoke(f.callback(actor+4)).completed} != true)}
  do {let f=try Fixture(p,hash);f.reenter=true;record("reentrant service",!success(f.perform(first)) && f.host.fault != nil)}
  do {let f=try Fixture(p,hash);let r=f.perform(first);let token=f.get(logic+0x18);f.heap.free(token);_=f.heap.storeBytes(token:token,count:0x488);record("replaced helper",success(r) && f.host.withObjectAllocation(provider:f.memory){f.host.invoke(f.callback()).completed} != true)}
  do {let f=try Fixture(p,hash);let r=f.perform(first);let token=f.get(logic+0x18);let retired=f.host.retireChameleon(actor:actor,provider:f.memory,retireSecondary:true);f.put(logic+0x18,token);f.put(logic+0x1c,29);record("stale helper",success(r) && retired && f.host.withObjectAllocation(provider:f.memory){f.host.invoke(f.callback()).completed} != true)}
  do {let f=try Fixture(p,hash);let r=f.perform(first)
   let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.map{($0,f.get($0))})
   let other=try ClawNativeMfcMemory(host:f.host,sha256:hash,importTargets:imports,allocationBase:0x63000000,sceneObjectAllocations:true)
   f.put(logic+0x1c,1000)
   record("same heap wrong provider",success(r) && f.host.withObjectAllocation(provider:other){f.host.invoke(f.callback()).completed} != true)
  }
  try JSONSerialization.data(withJSONObject:["version":1,"profiles":output,"controls":controls],options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"));print("native profiles \(output.count), controls \(controls.count)")
 }
}
