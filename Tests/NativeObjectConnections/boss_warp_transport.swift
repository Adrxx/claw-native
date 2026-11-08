import Foundation
private let base:UInt32=0x10000000
private let registry=base+0x300,logics=base+0x500,metadata=base+0x600,container=base+0x700,node=base+0x900,track=base+0xa00
private func u(_ x:Any)->UInt32 {(x as! NSNumber).uint32Value}
private func decode(_ s:String)->[UInt8] {
 let input=Array(s.utf8);precondition(input.count%2==0)
 func nibble(_ c:UInt8)->UInt8 {if c>=48 && c<=57{return c-48};if c>=97 && c<=102{return c-87};precondition(c>=65 && c<=70);return c-55}
 var output=[UInt8]();output.reserveCapacity(input.count/2)
 for i in stride(from:0,to:input.count,by:2){output.append(nibble(input[i])*16+nibble(input[i+1]))}
 return output
}
private func args(_ c:ClawCall)->[UInt32] {var c=c;return withUnsafeBytes(of:&c.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(c.argumentCount)))}}
private final class Fixture {
 let heap=ClawTokenHeap();let host:ClawNativeCanonicalHost;let memory:ClawNativeMfcMemory;let p:[String:Any]
 var requests:[[UInt32]]=[];var events:[[Any]]=[];var calls:[[UInt32]]=[];var removed:UInt32?;var overrideMetadata:UInt32?;var modeHook:(()->Void)?;var shadowOffered=false;var registryOutput:UInt32?
 init(_ p:[String:Any],_ hash:String)throws {
  self.p=p
  for b in p["initial"] as! [[String:Any]] {let d=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(d.count)).update(from:d,count:d.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x40
  let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:0x61000000)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in self.calls.append([c.function,c.receiver]);if c.function==0x4701b0 {let a=args(c)[0];self.events.append(["callback",a,self.get(a+0x68),self.get(container+0x1c),self.get(node+8)])}}
  memory.beforeObjectAllocation={ [unowned self] r in
   func word(_ address:UInt32)->UInt32 {let offset=Int(address-UInt32(CLAW_STACK_BASE));return r.stack.withUnsafeBytes{raw in raw.loadUnaligned(fromByteOffset:offset,as:UInt32.self).littleEndian}}
   self.requests.append([r.function,word(r.context.esp),word(r.context.esp+20),word(r.context.esp+4),r.context.ebx])
  }
  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]])}}
 }
 func get(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)![0]}
 func put(_ a:UInt32,_ v:UInt32){heap.lookup(a,words:1)![0]=v}
 func service(_ c:ClawCall)->UInt32? {
  if removed==c.function{return nil};let a=args(c)
  if c.function==0x40af90 || c.function==0x4f63ec {shadowOffered=true;return 99}
  if p["kind"] as! String == "mode" {guard c.function==0x4f6286,c.receiver==base+0x4010,a.count==2,a[0]==0x52a204,let out=host.bytes(a[1],count:4) else{return nil};modeHook?();out.update(repeating:0,count:4);events.append(["registry",c.receiver,a[0],0]);return 0}
  switch c.function {
  case 0x4750d0:
   guard c.argumentCount==0,c.receiver==base+0x200 else{return nil}
   var context=ClawGameFrameServiceContext(),globals=ClawGameFrameServiceGlobals(),result:UInt32=0
   let handled=withUnsafeMutablePointer(to:&globals){pointer -> UInt32 in context.globals=pointer;return claw_game_frame_service_entry(c.function,c.receiver,0,&context,nil,nil,&result)}
   guard handled==1,context.fault==0 else{return nil};return result
  case 0x4f6286:
   guard a.count==2,let out=host.bytes(a[1],count:4) else{return nil}
   var name:[UInt8]=[];for i:UInt32 in 0..<64 {guard let byte=host.bytes(a[0]+i,count:1) else{return nil};if byte[0]==0 {break};name.append(byte[0])}
   guard let key=String(bytes:name,encoding:.ascii) else{return nil};let found=p["found"] as! Bool
   let value:UInt32
   if p["kind"] as! String == "music" {value=found && key=="BOSS" ? track:0}
   else if c.receiver==logics+0x10 {registryOutput=a[1];value=overrideMetadata ?? (found ? metadata:0)}
   else if c.receiver==registry+0x10 {value=0}
   else{return nil}
   out.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee=value};events.append(["registry",c.receiver,key,value]);return value==0 ? 0:1
  case 0x4f51c5:
   guard c.receiver==container+0x10,a.count==1,get(container+0x1c)==0 else{return nil}
   put(node,0);put(node+4,0);put(node+8,a[0]);put(container+0x14,node);put(container+0x18,node);put(container+0x1c,1)
   events.append(["append",c.receiver,a[0],node]);return node
  case 0x546d5c:
   guard get(0x546d5c)==0x68001000,c.receiver==0,a.count==5,let output=host.bytes(a[0],count:16) else{return nil};for i in 0..<4 {var value=a[i+1].littleEndian;withUnsafeBytes(of:&value){UnsafeMutableRawPointer(output.advanced(by:i*4)).copyMemory(from:$0.baseAddress!,byteCount:4)}};events.append(["rectangle",a[1],a[2],a[3],a[4]]);return 1
  default:return nil
  }
 }
 func call()->ClawCall {var c=ClawCall();c.function=u(p["root"]!);c.receiver=u(p["receiver"]!);let a=(p["args"] as! [NSNumber]).map(\.uint32Value);c.argumentCount=UInt32(a.count);withUnsafeMutableBytes(of:&c.arguments){b in let q=b.bindMemory(to:UInt32.self);for i in a.indices{q[i]=a[i]}};return c}
 func run()->[String:Any] {
  var results:[UInt32]=[],completions:[[String:Any]]=[]
  for _ in 0..<((p["rebind"] as! Bool) ? 2:1) {var result:ClawNativeCanonicalHost.Completion?;_=host.withObjectAllocation(provider:memory){result=host.invoke(call())};if let r=result {completions.append(["completed":r.completed,"fault":r.fault.map{String(describing:$0)} ?? ""]);if let v=r.eax{results.append(v)}}else{completions.append(["completed":false,"fault":"scope rejected"])}}
  let final=(p["final"] as! [[String:Any]]).map {b->[String:Any] in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);let text=heap.lookupBytes(a,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing";return["address":a,"data":text]}
  if p["kind"] as! String == "contact" {results=[]}
  return["label":p["label"]!,"results":results,"requests":requests,"events":events,"calls":calls,"final":final,"completions":completions]
 }
}
@main struct BossWarpTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]),data=try Data(contentsOf:dir.appendingPathComponent("reference.json"))
  let ref=try JSONSerialization.jsonObject(with:data) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]]
  var output:[[String:Any]]=[];for p in profiles{output.append(try Fixture(p,hash).run())}
  var controls:[[String:Any]]=[]
  let mode=profiles.first{$0["kind"] as! String == "mode"}!,gem=profiles.first{$0["label"] as! String == "gem-deferred"}!
  func record(_ n:String,_ ok:Bool){controls.append(["name":n,"passed":ok])}
  func failed(_ r:[String:Any])->Bool {(r["completions"] as! [[String:Any]]).allSatisfy{!($0["completed"] as! Bool)}}
  for (name,address,value) in [("manager global",UInt32(0x5371fc),base+0x5004),("manager owner link",base+0x502c,base+0x6004),("owner table link",base+0x6000,UInt32(0x50c268)),("table mode target",UInt32(0x50c274),UInt32(0x40af91)),("actor state link",base+0x106c,base+0x2004)] {
   let f=try Fixture(mode,hash);f.modeHook={f.put(address,value)}
   record(name+" mutation rejected",failed(f.run()))
  }
  for (name,token,count) in [("actor",base+0x1000,UInt32(0x200)),("state",base+0x2000,0x200),("scene",base+0x3000,0x200),("sound",base+0x4000,0x200),("manager",base+0x5000,0x200),("owner",base+0x6000,0x200),("vtable",UInt32(0x50c264),0x14)] {
   let f=try Fixture(mode,hash);f.modeHook={let bytes=Array(UnsafeBufferPointer(start:f.heap.lookupBytes(token,count:count)!,count:Int(count)));f.heap.free(token);f.heap.storeBytes(token:token,count:count).update(from:bytes,count:bytes.count)}
   record(name+" identity replacement rejected",failed(f.run()))
  }
  do{let f=try Fixture(mode,hash);var c=ClawCall();c.function=0x40af90;c.receiver=base+0x6000;record("unowned nonzero receiver rejected",!f.host.invoke(c).completed)}
  do{let f=try Fixture(mode,hash);f.removed=0x4f6286;record("missing sound registry rejected",failed(f.run()))}
  do{let f=try Fixture(mode,hash);let r=f.run();record("mode canonical precedence",!failed(r) && !f.shadowOffered)}
  do{let f=try Fixture(gem,hash);let r=f.run();record("allocation canonical precedence",!failed(r) && !f.shadowOffered)}
  do{let f=try Fixture(gem,hash);record("allocation requires provider",!f.host.invoke(f.call()).completed)}
  do{let f=try Fixture(gem,hash);f.removed=0x4f6286;record("missing logic registry rejected",failed(f.run()))}
  for callback:UInt32 in [0x491fa0,0x4701b1,0x470870,0] {
   let f=try Fixture(gem,hash);f.put(metadata+0x10,callback);record("wrong metadata callback \(callback) rejected",failed(f.run()) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  do{let f=try Fixture(gem,hash);var count=0;f.memory.beforeObjectAllocation={_ in count+=1;if count==1 {f.put(metadata+0x10,0x491fa0)}};record("metadata callback changed during allocation rejected",failed(f.run()))}
  do{let f=try Fixture(gem,hash);f.memory.beforeObjectAllocation={_ in let bytes=Array(UnsafeBufferPointer(start:f.heap.lookupBytes(metadata,count:0x100)!,count:0x100));f.heap.free(metadata);f.heap.storeBytes(token:metadata,count:0x100).update(from:bytes,count:bytes.count)};record("metadata identity replaced rejected",failed(f.run()))}
  do{let f=try Fixture(gem,hash);f.memory.afterService={slot,_,token in if slot==0x4a48e0 && token != 0 {let count:UInt32=token==0x61000000 ? 0x1b4:0x174;f.heap.free(token);_=f.heap.storeBytes(token:token,count:count)}};record("returned allocation replaced rejected",failed(f.run()))}
  do{let f=try Fixture(gem,hash);var nested:ClawNativeCanonicalHost.Completion?;f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(f.call())};record("allocation reentry rejected",failed(f.run()) && nested?.completed==false)}
  do{let f=try Fixture(gem,hash);var rejected=false;let r=f.host.withObjectAllocation(provider:f.memory){rejected=f.host.withObjectAllocation(provider:f.memory){f.host.invoke(f.call())}==nil};record("nested scope rejected",rejected && r==nil)}
  do{let f=try Fixture(gem,hash);var n=0;f.memory.beforeObjectAllocation={_ in n+=1;if n==2 {f.heap.free(0x61000000);_=f.heap.storeBytes(token:0x61000000,count:0x1b4)}};record("first actor allocation replaced before state allocation rejected",failed(f.run()))}
  do{let f=try Fixture(gem,hash),foreign=try Fixture(gem,hash);record("foreign provider rejected",f.host.withObjectAllocation(provider:foreign.memory){f.host.invoke(f.call())}==nil)}
  do{let p=profiles.first{$0["label"] as! String == "gem-initialized"}!,f=try Fixture(p,hash);f.removed=0x4750d0;record("missing mode-four owner rejected",failed(f.run()))}
  do{let f=try Fixture(gem,hash);var c=f.call();c.arguments.4=base+0xb00;let r=f.host.withObjectAllocation(provider:f.memory){f.host.invoke(c)};record("wrong metadata name token rejected",r==nil && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(mode,hash);var nested:ClawNativeCanonicalHost.Completion?;f.modeHook={f.modeHook=nil;nested=f.host.invoke(f.call())};record("BossWarp sound service reentry rejected",failed(f.run()) && nested?.completed==false)}
  do{let f=try Fixture(gem,hash);_=f.heap.store(token:base+0xc00,words:5);f.put(base+0xc10,0x4701b0);var n=0;f.memory.afterService={slot,_,_ in if slot==0x4a48e0 {n+=1;if n==1,let local=f.registryOutput {f.host.bytes(local,count:4)!.withMemoryRebound(to:UInt32.self,capacity:1){$0.pointee=base+0xc00}}}};record("metadata pointer replaced between allocations rejected",failed(f.run()))}
  do{let f=try Fixture(gem,hash);f.memory.beforeObjectAllocation={r in f.host.bytes(r.context.esp+20,count:4)!.update(repeating:0,count:4)};record("source allocation stack continuation mutation rejected",failed(f.run()) && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(gem,hash);let r=f.run();record("shared Memory retains actor and state after scope",!failed(r) && f.memory.ownsObjectAllocation(0x61000000,count:0x1b4) && f.memory.ownsObjectAllocation(0x610001c0,count:0x174))}
  let result:[String:Any]=["version":1,"profiles":output,"controls":controls];try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"));print("native profiles \(output.count), controls \(controls.count)")
 }
}
