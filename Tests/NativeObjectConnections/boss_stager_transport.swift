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
 var events:[[Any]]=[];var calls:[[UInt32]]=[];var removed:UInt32?;var overrideMetadata:UInt32?
 init(_ p:[String:Any],_ hash:String)throws {
  self.p=p
  for b in p["initial"] as! [[String:Any]] {let d=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(d.count)).update(from:d,count:d.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x40
  let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:0x61000000)
  host.dependency={ [unowned self] _,c in self.service(c)}
  host.observer={ [unowned self] c in self.calls.append([c.function,c.receiver]);if c.function==0x491fa0 {let a=args(c)[0];self.events.append(["callback",a,self.get(a+0x68),self.get(container+0x1c),self.get(node+8)])}}
  memory.afterService={ [unowned self] f,a,v in if f==0x4a48e0 {self.events.append(["malloc",v,a[0]])}}
 }
 func get(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)![0]}
 func put(_ a:UInt32,_ v:UInt32){heap.lookup(a,words:1)![0]=v}
 func service(_ c:ClawCall)->UInt32? {
  if removed==c.function{return nil};let a=args(c)
  switch c.function {
  case 0x4f6286:
   guard a.count==2,let out=host.bytes(a[1],count:4) else{return nil}
   var name:[UInt8]=[];for i:UInt32 in 0..<64 {guard let byte=host.bytes(a[0]+i,count:1) else{return nil};if byte[0]==0 {break};name.append(byte[0])}
   guard let key=String(bytes:name,encoding:.ascii) else{return nil};let found=p["found"] as! Bool
   let value:UInt32
   if p["kind"] as! String == "music" {value=found && key=="BOSS" ? track:0}
   else if c.receiver==logics+0x10 {value=overrideMetadata ?? (found ? metadata:0)}
   else if c.receiver==registry+0x10 && key=="GAME_BOSSBAR" {value=0}
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
  return["label":p["label"]!,"results":results,"events":events,"calls":calls,"final":final,"completions":completions]
 }
}
@main struct BossStagerTransportComparison {
 static func main()throws {
  let dir=URL(fileURLWithPath:CommandLine.arguments[1]),data=try Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1]).appendingPathComponent("reference.json"))
  let ref=try JSONSerialization.jsonObject(with:data) as! [String:Any],hash=ref["executable_sha256"] as! String,profiles=ref["profiles"] as! [[String:Any]]
  var output:[[String:Any]]=[];for p in profiles{output.append(try Fixture(p,hash).run())}
  var controls:[[String:Any]]=[];let contact=profiles.first{$0["label"] as! String == "contact-create"}!,music=profiles.first{$0["label"] as! String == "music-selected"}!
  func record(_ n:String,_ ok:Bool){controls.append(["name":n,"passed":ok])}
  func failed(_ r:[String:Any])->Bool {(r["completions"] as! [[String:Any]]).allSatisfy{!($0["completed"] as! Bool)}}
  do{let f=try Fixture(contact,hash),r=f.host.invoke(f.call());record("allocation requires provider scope",!r.completed && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(contact,hash);f.removed=0x4f6286;record("missing registry fails",failed(f.run()))}
  do{let f=try Fixture(contact,hash),other=try Fixture(contact,hash);let r=f.host.withObjectAllocation(provider:other.memory){f.host.invoke(f.call())};record("foreign provider rejected",r==nil && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(contact,hash);var c=f.call();c.receiver2=1;let r=f.host.withObjectAllocation(provider:f.memory){f.host.invoke(c)};record("incorrect receiver2 rejected",r==nil && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(contact,hash);var c=ClawCall();c.function=0x4f63ec;c.argumentCount=1;c.arguments.0=0x174;let r=f.host.withObjectAllocation(provider:f.memory){f.host.invoke(c)};record("direct new rejected",r==nil && f.heap.lookupBytes(0x61000000,count:1)==nil)}
  do{let f=try Fixture(music,hash);var c=ClawCall();c.function=0x40af90;let r=f.host.invoke(c);record("direct zero receiver mode preserved",r.completed && r.eax==3)}
  do{let f=try Fixture(music,hash);var c=ClawCall();c.function=0x40af90;c.receiver=base+0x200;record("direct nonzero receiver mode rejected",!f.host.invoke(c).completed)}
  do{let f=try Fixture(music,hash);f.put(0x50c264+0x10,0x40af91);record("incorrect virtual target rejected",failed(f.run()))}
  do{let f=try Fixture(contact,hash);f.memory.failAllocation={$0==0x4a48e0};record("exhaustion is not successful null construction",failed(f.run()))}
  do{let f=try Fixture(contact,hash);var captured:ClawNativeCanonicalHost.ObjectAllocationRequest?;var replay=false
   f.memory.beforeObjectAllocation={r in captured=r;replay = !r.consume(for:f.host,provider:f.memory)}
   let r=f.run();let after=captured.map{!$0.consume(for:f.host,provider:f.memory) && !$0.validReturn(for:f.host)} ?? false
   record("allocation lease single use and expires after scope",!failed(r) && replay && after)
   record("allocation remains owned after scope",f.memory.ownsObjectAllocation(0x61000000,count:0x174))
  }
  do{let f=try Fixture(contact,hash),other=try Fixture(contact,hash);var foreign=false
   f.memory.beforeObjectAllocation={r in foreign = !r.consume(for:other.host,provider:other.memory)}
   record("foreign host cannot consume lease",!failed(f.run()) && foreign)
  }
  do{let f=try Fixture(contact,hash);let p=f.heap.storeBytes(token:0x61000000,count:0x174);p.update(repeating:0xa7,count:0x174)
   let r=f.run();record("occupied allocation preserved on exhaustion",failed(r) && UnsafeBufferPointer(start:p,count:0x174).allSatisfy{$0==0xa7})
  }
  do{let f=try Fixture(contact,hash);f.memory.beforeObjectAllocation={_ in f.heap.free(base);_=f.heap.storeBytes(token:base,count:0x10000)}
   record("root allocation replacement rejected",failed(f.run()) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  do{let f=try Fixture(contact,hash);f.memory.afterService={slot,_,token in if slot==0x4a48e0 && token != 0 {f.heap.free(token);_=f.heap.storeBytes(token:token,count:0x174)}}
   record("replacement of returned allocation rejected",failed(f.run()))
  }
  do{let f=try Fixture(contact,hash);var nested:ClawNativeCanonicalHost.Completion?
   f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(f.call())}
   record("reentrant allocation callback rejected",failed(f.run()) && nested?.completed==false)
  }
  do{let f=try Fixture(contact,hash);var innerRejected=false
   let outer=f.host.withObjectAllocation(provider:f.memory){innerRejected=f.host.withObjectAllocation(provider:f.memory){f.host.invoke(f.call())}==nil}
   record("nested allocation scope rejected",innerRejected && outer==nil && f.host.fault != nil && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  do{let f=try Fixture(contact,hash);f.memory.beforeObjectAllocation={_ in f.put(0x510020,0)}
   record("new-handler sentinel mutation rejected before allocation",failed(f.run()) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  do{let f=try Fixture(contact,hash);var refused=false
   f.memory.beforeObjectAllocation={request in
    let done=DispatchSemaphore(value:0)
    Thread.detachNewThread {refused = f.memory.allocateObject(request)==nil && !request.consume(for:f.host,provider:f.memory);done.signal()}
    _=done.wait(timeout:.now()+2)
   }
   record("foreign thread rejects request without poisoning issuer",!failed(f.run()) && refused)
  }
  do{let f=try Fixture(music,hash);let prior=f.host.observer
   f.host.observer={call in prior?(call);if call.function==0x40af90 {f.put(base+0x100+0x2c,base+0x204)}}
   record("scene receiver link mutation rejected",failed(f.run()))
  }
  do{let f=try Fixture(contact,hash);f.overrideMetadata=UInt32.max
   record("malformed registry metadata rejected before allocation",failed(f.run()) && f.heap.lookupBytes(0x61000000,count:1)==nil)
  }
  let result:[String:Any]=["version":1,"profiles":output,"controls":controls];try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dir.appendingPathComponent("native.json"));print("native profiles \(output.count), controls \(controls.count)")
 }
}
