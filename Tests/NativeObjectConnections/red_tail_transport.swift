import Foundation
private let actor:UInt32=0x10001000,state:UInt32=0x10002000
private func number(_ v:Any)->UInt32 {(v as! NSNumber).uint32Value}
private func decode(_ s:String)->[UInt8] {let c=Array(s.utf8);func n(_ v:UInt8)->UInt8 {v<=57 ? v-48:v-87};return stride(from:0,to:c.count,by:2).map{n(c[$0])*16+n(c[$0+1])}}
private func arguments(_ c:ClawCall)->[UInt32] {var c=c;return withUnsafeBytes(of:&c.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(c.argumentCount)))}}
private struct ResourceInputs {
 let owner:ClawActorResources
 let images:[String:UInt32],sequences:[String:UInt32]
 let spans:[[String:Any]]
 init(_ input:[String:Any],heap:ClawTokenHeap)throws {
  owner=try ClawActorResources(root:URL(fileURLWithPath:input["root"] as! String),heap:heap,level:13)
  var images:[String:UInt32]=[:],sequences:[String:UInt32]=[:]
  for key in input["images"] as! [String] {images[key]=try owner.images(name:key)?.token ?? 0}
  for key in input["sequences"] as! [String] {sequences[key]=try owner.sequence(name:key)?.token ?? 0}
  self.images=images;self.sequences=sequences
  spans=heap.debugAllocationBases.filter{$0>=0x61000000}.map {address in
   var low:UInt32=1,high:UInt32=4<<20
   while low<high {let mid=low+(high-low+1)/2;if heap.lookupBytes(address,count:mid) != nil {low=mid}else{high=mid-1}}
   let p=heap.lookupBytes(address,count:low)!
   return ["address":address,"data":UnsafeBufferPointer(start:p,count:Int(low)).map{String(format:"%02x",$0)}.joined()]
  }
 }
}

private final class Fixture {
 let heap=ClawTokenHeap(),host:ClawNativeCanonicalHost,memory:ClawNativeMfcMemory,profile:[String:Any]
 var events:[[Any]]=[],entries:[[UInt32]]=[],allocations:[[UInt32]]=[]
 var fp=ClawX87State()
 var lastX87:[Any]=[]
 var sourceObservations:[[String:Any]]=[]
 var rawSources:[[String:Any]]=[]
 var temporaryFrames:[[String:UInt32]]=[]
 var removed:UInt32?
 let resources:ResourceInputs
 init(_ profile:[String:Any],hash:String)throws {
  self.profile=profile
  fp.size=UInt32(MemoryLayout<ClawX87State>.size);fp.version=1;fp.control=0x023f
  for b in profile["initial"] as! [[String:Any]] {let d=decode(b["data"] as! String);heap.storeBytes(token:number(b["address"]!),count:UInt32(d.count)).update(from:d,count:d.count)}
  resources=try ResourceInputs(profile["resource_inputs"] as! [String:Any],heap:heap)
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
  let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
  for (a,t) in imports {heap.lookup(a,words:1)![0]=t}
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:0x62000000,sceneObjectAllocations:true)
  host.dependency={ [unowned self] _,c in self.service(c)}
  let observed:Set<UInt32>=[0x47ff90,0x40e0d0,0x44c000,0x40e1b0,0x482430,0x4c96b0,0x4dc870,0x4827a0,0x47f800,0x4441b0,0x44d3c0,0x4805a0,0x4dbcd0,0x4f6584,0x4f6439,0x4db620,0x4dbd60,0x4dbe10]
  host.observer={ [unowned self] c in
   if observed.contains(c.function) {self.entries.append([c.function,c.receiver])}
   if c.function==0x4f6428,c.argumentCount==1,let count=self.memory.localRequestedSizes[c.arguments.0],let bytes=self.heap.lookupBytes(c.arguments.0,count:count) {
    let hex=UnsafeBufferPointer(start:bytes,count:Int(count)).map{String(format:"%02x",$0)}.joined()
    self.events.append(["free",c.arguments.0,hex])
   }
  }
  memory.afterService={ [unowned self] f,a,t in if f==0x4a48e0 {self.allocations.append([t,a[0]]);self.events.append(["malloc",t,a[0]])}}
 }
 func get(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)![0]}
 func put(_ a:UInt32,_ v:UInt32) {heap.lookup(a,words:1)![0]=v}
 func service(_ c:ClawCall)->UInt32? {
  if removed==c.function {return nil};let a=arguments(c)
  switch c.function {
  case 0x4f6286:
   guard a.count==2,let output=host.bytes(a[1],count:4) else{return nil}
   var name:[UInt8]=[];for i:UInt32 in 0..<128 {guard let b=host.bytes(a[0]+i,count:1) else{return nil};if b[0]==0 {break};name.append(b[0])}
   guard let key=String(bytes:name,encoding:.ascii) else{return nil}
   let value=resources.images[key] ?? resources.sequences[key] ?? 0
   output.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee=value};events.append(["registry",c.receiver,key,value]);return value==0 ? 0:1
  case 0x546d5c,0x546cdc,0x710c00,0x710c10:
   guard a.count==((c.function==0x546d5c || c.function==0x710c00) ? 5:1),let output=host.bytes(a[0],count:16) else{return nil}
   let v:[UInt32]=(c.function==0x546d5c || c.function==0x710c00) ? Array(a.dropFirst()):[0,0,0,0]
   for i in 0..<4 {var w=v[i].littleEndian;withUnsafeBytes(of:&w){UnsafeMutableRawPointer(output.advanced(by:i*4)).copyMemory(from:$0.baseAddress!,byteCount:4)}}
   events.append(["rectangle",v[0],v[1],v[2],v[3]]);return 1
  case 0x4a3050:return 17
  case 0x4f6974:return get(c.receiver)
  case 0x546cd4,0x710c30:
   guard a.count==3,let rect=host.bytes(a[0],count:16) else{return nil}
   let v=(0..<4).map {UnsafeRawPointer(rect.advanced(by:$0*4)).loadUnaligned(as:UInt32.self)}
   return Int32(bitPattern:v[0])<=Int32(bitPattern:a[1]) && Int32(bitPattern:a[1])<Int32(bitPattern:v[2]) && Int32(bitPattern:v[1])<=Int32(bitPattern:a[2]) && Int32(bitPattern:a[2])<Int32(bitPattern:v[3]) ? 1:0
  case 0x546a40:return 0
  default:return nil
  }
 }
 func call(_ command:UInt32)->ClawNativeCanonicalHost.Completion? {put(state+0x1c,command);var c=ClawCall();c.function=0x47f6e0;c.argumentCount=1;c.arguments.0=actor;entries.append([c.function,0]);var result:ClawNativeCanonicalHost.Completion?
  if let (_,output)=host.withObjectX87Environment(fp,body:{result=host.withObjectAllocation(provider:memory){host.invoke(c)}}) {fp=output}
  var slots=fp.slots;let values=withUnsafeBytes(of:&slots){raw in Array(raw.bindMemory(to:ClawX87Value.self).prefix(Int(fp.count))).map{[$0.significand,UInt64($0.signExponent)]}}
  lastX87=[fp.control,fp.status,values]
  for v in host.redTailBossMemberSources {
   if v.function==0x4db620,v.returnPC==0x4dbe3c {
    precondition(host.redTailBossTemporaryCallerFrame.map{$0>=28 && v.input.ecx==$0-28}==true)
    temporaryFrames.append(["receiver":v.input.ecx,"callerFrame":host.redTailBossTemporaryCallerFrame!])
   }
   let raw:[String:Any]=["function":v.function,"receiver":v.input.ecx,"returnPC":v.returnPC,"eax":v.output.eax,"stackDelta":v.output.esp-v.input.esp,"preserved":v.input.ebx==v.output.ebx && v.input.esi==v.output.esi && v.input.edi==v.output.edi && v.input.ebp==v.output.ebp && v.input.fsHead==v.output.fsHead]
   rawSources.append(raw)
   sourceObservations.append(raw)
  };return result
 }
 func run()->[String:Any] {
  var snapshots:[[String:Any]]=[],completions:[[String:Any]]=[]
  for original in profile["snapshots"] as! [[String:Any]] {
   let command=original["command"]!
   let completed:Bool
   if command as? String == "retire" {completed=host.retireRedTail(actor:actor,provider:memory)}
   else {completed=call(number(command))?.completed==true}
   completions.append(["command":command,"completed":completed,"fault":String(describing:host.fault)])
   let final=(original["final"] as! [[String:Any]]).map {b->[String:Any] in
    let a=number(b["address"]!),n=UInt32((b["data"] as! String).count/2)
    let value=heap.lookupBytes(a,count:n).map {UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing"
    return ["address":a,"data":value]
   }
   snapshots.append(["command":command,"entries":entries,"temporary_frames":temporaryFrames,"raw_entries":entries,"raw_sources":rawSources,"events":events,"allocations":allocations,"final":final,"x87":lastX87,"sources":sourceObservations])
   if !completed {break}
  }
  return ["label":profile["label"]!,"snapshots":snapshots,"completions":completions]
 }
}
@main struct RedTailTransportComparison {
 static func main()throws {
  if CommandLine.arguments[1]=="--resources" {
   let dir=URL(fileURLWithPath:CommandLine.arguments[2]),input=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2]).appendingPathComponent("resource-inputs.json"))) as! [String:Any]
   let r=try ResourceInputs(input,heap:ClawTokenHeap())
   try JSONSerialization.data(withJSONObject:["images":r.images,"sequences":r.sequences,"spans":r.spans],options:[.sortedKeys]).write(to:dir.appendingPathComponent("resources.json"));return
  }
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]),ref=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1]).appendingPathComponent("reference.json"))) as! [String:Any]
  let p=(ref["profiles"] as! [[String:Any]])[0],hash=ref["executable_sha256"] as! String
  let fixture=try Fixture(p,hash:hash),result=fixture.run()
  var controls:[[String:Any]]=[]
  var allocationFailure:[String:Any]=[:]
  func record(_ name:String,_ pass:Bool){controls.append(["name":name,"passed":pass])}
  func fresh()throws->Fixture {try Fixture(p,hash:hash)}
  func raw(_ f:Fixture,_ c:ClawCall)->ClawNativeCanonicalHost.Completion? {f.host.withObjectAllocation(provider:f.memory){f.host.invoke(c)}}
  func root(_ token:UInt32=actor)->ClawCall {var c=ClawCall();c.function=0x47f6e0;c.argumentCount=1;c.arguments.0=token;return c}
  do{let f=try fresh();f.put(state+0x10,0x482820);record("wrong callback rejected",f.call(0)?.completed != true && f.allocations.isEmpty)}
  do{let f=try fresh();record("wrong actor rejected",raw(f,root(actor+4))?.completed != true && f.allocations.isEmpty)}
  do{let f=try fresh(),other=try fresh();record("foreign provider rejected",f.host.withObjectAllocation(provider:other.memory){f.host.invoke(root())}==nil && f.allocations.isEmpty)}
  do{let f=try fresh();var c=ClawCall();c.function=0x4f63ec;c.argumentCount=1;c.arguments.0=0x509;record("wrong size rejected",raw(f,c)?.completed != true && f.allocations.isEmpty)}
  do{let f=try fresh();f.put(0x50f268,0x44d000);record("wrong vtable rejected",f.call(0)?.completed != true && f.allocations.isEmpty)}
  do{let f=try fresh();var c=root();c.sourceReturnPC=0x47f71e;record("wrong continuation rejected",raw(f,c)?.completed != true && f.allocations.isEmpty)}
  do{let f=try fresh();f.removed=0x4f6286;record("missing service rejected",f.call(0)?.completed != true)}
  do{let f=try fresh();f.host.stacklessCallerReserve=4;record("insufficient caller frame rejected",f.call(0)?.completed != true)}
  do{let f=try fresh();var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(root())};record("reentry rejected",f.call(0)?.completed != true && nested?.completed==false)}
  do{let f=try fresh();f.memory.failAllocation={$0==0x4a48e0};let r=f.call(0)
   allocationFailure=["boundary":f.host.fault?.address ?? 0,"command":f.get(state+0x1c),"helper":f.get(state+0x18),"events":f.events]
   record("allocation failure reaches original throw dependency",r?.completed != true && f.get(state+0x18)==0 && f.host.fault?.address==0x5022b5)
  }
  do{let f=try fresh();f.memory.beforeObjectAllocation={_ in f.heap.free(0x10000000);_=f.heap.storeBytes(token:0x10000000,count:0x10000)};record("replaced actor storage rejected",f.call(0)?.completed != true && f.allocations.isEmpty)}
  do{let f=try fresh();let created=f.call(0)?.completed==true;let helper=f.get(state+0x18);if created {f.heap.free(helper);_=f.heap.storeBytes(token:helper,count:0x508)};record("replaced helper rejected",created && f.call(1000)?.completed != true)}
  do{let f=try fresh();let created=f.call(0)?.completed==true;let helper=f.get(state+0x18);if created {f.heap.free(helper)};record("stale helper rejected",created && f.call(1000)?.completed != true)}
  do{let f=try fresh(),other=try fresh();let created=f.call(0)?.completed==true;record("foreign free rejected",created && !other.memory.releaseSceneObject(f.get(state+0x18)) && f.memory.ownsObjectAllocation(f.get(state+0x18),count:0x508))}
  do{let f=try fresh();let created=f.call(0)?.completed==true,helper=f.get(state+0x18);let retired=created && f.host.retireRedTail(actor:actor,provider:f.memory);record("double free rejected",retired && !f.memory.releaseSceneObject(helper))}
  do{let f=try fresh();var captured:ClawNativeCanonicalHost.ObjectAllocationRequest?;var denied=false;f.memory.beforeObjectAllocation={r in captured=r;denied = !r.consume(for:f.host,provider:f.memory)};let created=f.call(0)?.completed==true;record("single use allocation lease",created && denied && captured.map{!$0.validReturn(for:f.host) && !$0.consume(for:f.host,provider:f.memory)}==true)}

  let output:[String:Any]=["profiles":[result],"controls":controls,"allocation_failure":allocationFailure]
  try JSONSerialization.data(withJSONObject:output,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"))
  print(result["completions"]!)
 }
}
