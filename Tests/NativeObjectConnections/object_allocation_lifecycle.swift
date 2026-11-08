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
 let heap:ClawTokenHeap;let host:ClawNativeCanonicalHost;let memory:ClawNativeMfcMemory;let p:[String:Any]
 var requests:[[UInt32]]=[];var events:[[Any]]=[];var calls:[[UInt32]]=[];var removed:UInt32?;var overrideMetadata:UInt32?;var modeHook:(()->Void)?;var shadowOffered=false;var registryOutput:UInt32?
 init(_ p:[String:Any],_ hash:String, scene:ClawNativeScene? = nil, sceneStorage:Bool = true, registerOwner:Bool = true)throws {
  self.p=p;heap=scene?.heap ?? ClawTokenHeap()
  for b in p["initial"] as! [[String:Any]] {
   let d=decode(b["data"] as! String),address=u(b["address"]!)
   if !heap.overlaps(address,count:UInt32(d.count)) {
    heap.storeBytes(token:address,count:UInt32(d.count)).update(from:d,count:d.count)
   } else {
    // Existing scene lifecycle tables already own their storage. Preserve
    // those identities and populate only source fixture bytes/gaps.
    precondition(d.count%4==0)
    for i in stride(from:0,to:d.count,by:4) {
     let at=address+UInt32(i)
     let target=heap.lookupBytes(at,count:4) ?? heap.storeBytes(token:at,count:4)
     for j in 0..<4 {target[j]=d[i+j]}
    }
   }
  }
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x40
  let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:0x65000000,sceneObjectAllocations:sceneStorage)
  if let scene, registerOwner {precondition(scene.registerObjectAllocationOwner(memory))}
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
 // The constructor fixture owns a physical list distinct from the real scene.
 // Moving its actor to the real scene relinquishes all fixture list links.
 func detachFixtureList() {
  for address in [container+0x14,container+0x18,container+0x1c,node,node+4,node+8] {put(address,0)}
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
@main struct ObjectAllocationLifecycleComparison {
 static func main() throws {
  let directory=URL(fileURLWithPath:CommandLine.arguments[1])
  let reference=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("reference.json"))) as! [String:Any]
  let profiles=reference["profiles"] as! [[String:Any]],hash=reference["executable_sha256"] as! String
  let root=URL(fileURLWithPath:"App/GameData"),level=try ClawLevelScene(root:root),assets=try ClawPlayerAssets(root:root)
  func scene() throws -> ClawNativeScene {
   ClawNativeScene(player:try ClawNativePlayer(world:level.world,assets:assets),windowInput:nil,clock:{1000})
  }
  var output:[[String:Any]]=[],controls:[[String:Any]]=[],diagnostics:[[String:Any]]=[]
  func record(_ name:String,_ passed:Bool){controls.append(["name":name,"passed":passed])}
  func completed(_ result:[String:Any])->Bool {
   (result["completions"] as! [[String:Any]]).allSatisfy{$0["completed"] as! Bool}
  }
  let actor:UInt32=0x65000000,state:UInt32=0x65000200
  for profile in profiles {
   let runtime=try scene(),f=try Fixture(profile,hash,scene:runtime),result=f.run()
   output.append(result)
   let label=profile["label"] as! String
   guard completed(result),let actorIdentity=f.heap.allocationIdentity(at:actor,count:0x1b4),
         let stateIdentity=f.heap.allocationIdentity(at:state,count:0x174),var snapshot=runtime.snapshotActor(actor) else {
    record(label+" source construction joins scene snapshot",false);continue
   }
   record(label+" actor and state source allocation order",f.memory.sceneObjectPointers == [actor,state] && f.get(actor+0x6c)==state)
   record(label+" canonical byte bounds exclude padding",f.host.bytes(actor,count:0x1b4) != nil && f.heap.lookupBytes(actor,count:0x1b5)==nil && f.heap.lookupBytes(actor+0x1b4,count:1)==nil && f.heap.containingAllocationIdentity(at:actor+0x1b4,count:1)==nil && f.heap.allocationIdentity(at:actor,count:512)==nil)
   record(label+" physical padding reserved before state",f.heap.lookup(actor,words:128) != nil && f.heap.lookup(actor,words:129)==nil && f.heap.overlaps(actor+0x1b4,count:76))
   snapshot.actor.19=321;snapshot.actor.127=0xa55aa55a;snapshot.primary.8=10
   runtime.write(snapshot)
   let written=runtime.snapshotActor(actor)
   record(label+" scene write preserves identity and canonical extent",written?.actor.19==321 && written?.actor.127==0xa55aa55a && f.heap.allocationIdentity(at:actor,count:0x1b4) === actorIdentity && f.heap.allocationIdentity(at:state,count:0x174) === stateIdentity && f.heap.lookupBytes(actor+0x1b4,count:1)==nil)
   let physical=runtime.actorHost, scratch=physical.allocate!(physical.context,12)
   record(label+" native allocation cursor follows padded source allocations",scratch>=state+0x180 && f.heap.allocationIdentity(at:scratch,count:12) != nil && f.heap.allocationIdentity(at:actor,count:0x1b4) === actorIdentity && f.heap.allocationIdentity(at:state,count:0x174) === stateIdentity)
   physical.free!(physical.context,scratch)
   runtime.adopt(written!);f.detachFixtureList()
   let listNode=f.get(actor+0x68)
   record(label+" recovered list insertion keeps allocation identity",runtime.actorTokens.contains(actor) && f.get(listNode+8)==actor && f.heap.allocationIdentity(at:actor,count:0x1b4) === actorIdentity && runtime.fault==0)
   // Keep the unrelated player dormant while exercising the same scene scheduler.
   let playerState=f.get(0x10002000+0x6c);f.put(playerState+0x20,100000)
   record(label+" canonical host is clean before scheduling",f.host.fault==nil)
   // Observe delivery from the real scheduler without supplying an adapter's
   // gameplay behavior. The constructor's actual initialization callback was
   // already original-compared above; later callback wiring is consumer work.
   var scheduled:[UInt32]=[]
   runtime.gameplay[0x4701b0]={ token in scheduled.append(token) }
   var globals=ClawSceneActorGlobals(),fault:UInt32=0
   globals.animation.deltaMilliseconds=5
   f.heap.withStableFreedStorage {claw_scene_actor_update(runtime.containerToken,&globals,0,runtime.actorHost,&fault)}
   let delayed=scheduled.isEmpty && f.get(state+0x20)==5
   f.heap.withStableFreedStorage {claw_scene_actor_update(runtime.containerToken,&globals,0,runtime.actorHost,&fault)}
   diagnostics.append(["profile":label,"phase":"scheduled","scheduled":scheduled,"callback":UInt32(0x4701b0),"timer":f.heap.lookup(state+0x20,words:1)?[0] ?? UInt32.max,"fault":fault,"sceneFault":runtime.fault,"hostFault":f.host.fault.map{String(describing:$0)} ?? "","calls":f.calls])
   record(label+" scene scheduling decrements timer and dispatches source callback identity",delayed && scheduled==[actor] && fault==0 && runtime.fault==0)
   if var dying=runtime.snapshotActor(actor) {
    dying.actor.2 |= 0x10000;dying.primary.8=1000;runtime.write(dying)
    f.heap.withStableFreedStorage {claw_scene_actor_update(runtime.containerToken,&globals,0,runtime.actorHost,&fault)}
   }
   diagnostics.append(["profile":label,"phase":"destroyed","fault":fault,"sceneFault":runtime.fault,"hostFault":f.host.fault.map{String(describing:$0)} ?? "","remaining":f.memory.sceneObjectPointers,"unresolved":Array(runtime.unresolvedDependencies)])
   record(label+" scene destruction retires actor and state once",fault==0 && runtime.fault==0 && f.memory.sceneObjectPointers.isEmpty && f.memory.localPointers.isEmpty && f.heap.lookupBytes(actor,count:1)==nil && f.heap.lookupBytes(state,count:1)==nil && !runtime.actorTokens.contains(actor) && f.memory.validObjectAllocationBinding(for:f.host))
   f.detachFixtureList()
   var next:ClawNativeCanonicalHost.Completion?
   let nextScope=f.host.withObjectAllocation(provider:f.memory){next=f.host.invoke(f.call())}
   let nextActor=next?.eax ?? 0
   record(label+" subsequent canonical allocation scope succeeds",nextScope != nil && next?.completed==true && nextActor != actor && f.memory.sceneObjectPointers.count==2)
   if let nextSnapshot=runtime.snapshotActor(nextActor) {
    runtime.adopt(nextSnapshot);f.detachFixtureList()
    var dying=runtime.snapshotActor(nextActor)!;dying.actor.2 |= 0x10000;dying.primary.8=1000;runtime.write(dying)
    f.heap.withStableFreedStorage {claw_scene_actor_update(runtime.containerToken,&globals,0,runtime.actorHost,&fault)}
   }
   record(label+" final teardown leaves zero owned actor and state allocations",f.memory.sceneObjectPointers.isEmpty && f.memory.localPointers.isEmpty && f.memory.validObjectAllocationBinding(for:f.host) && fault==0 && runtime.fault==0)
  }
  let profile=profiles[0]
  do {
   let f=try Fixture(profile,hash);let r=f.run();let foreign:UInt32=0x66000000;_=f.heap.store(token:foreign,words:128)
   record("foreign free rejected",completed(r) && !f.memory.releaseSceneObject(foreign) && f.heap.lookup(foreign,words:128) != nil && f.memory.sceneObjectPointers==[actor,state])
  }
  do {
   let f=try Fixture(profile,hash),r=f.run()
   record("interior free rejected",completed(r) && !f.memory.releaseSceneObject(actor+4) && f.memory.sceneObjectPointers==[actor,state] && f.heap.lookupBytes(actor,count:0x1b4) != nil)
  }
  do {
   let f=try Fixture(profile,hash);_=f.run()
   let identity=f.heap.allocationIdentity(at:actor,count:0x1b4)!
   let once=f.memory.releaseSceneObject(actor),twice=f.memory.releaseSceneObject(actor)
   record("double free rejected with ledger retired once",once && !twice && f.memory.sceneObjectPointers==[state] && f.heap.allocationIdentity(at:actor,count:0x1b4) !== identity)
  }
  do {
   let f=try Fixture(profile,hash);_=f.run();f.heap.free(actor);_=f.heap.storeBytes(token:actor,count:0x1b4)
   let replacement=f.heap.allocationIdentity(at:actor,count:0x1b4)!
   record("stale same-token allocation identity rejected",!f.memory.releaseSceneObject(actor) && f.heap.allocationIdentity(at:actor,count:0x1b4) === replacement && !f.memory.validObjectAllocationBinding(for:f.host))
  }
  do {
   let runtime=try scene(),f=try Fixture(profile,hash,scene:runtime);_=f.run()
   f.heap.free(actor);_=f.heap.storeBytes(token:actor,count:0x1b4)
   let replacement=f.heap.allocationIdentity(at:actor,count:0x1b4)!,h=runtime.actorHost
   h.free!(h.context,actor)
   record("scene free rejects stale identity without deleting replacement",runtime.fault != 0 && f.heap.allocationIdentity(at:actor,count:0x1b4) === replacement)
  }
  do {
   let runtime=try scene(),f=try Fixture(profile,hash,scene:runtime);_=f.run();let h=runtime.actorHost
   h.free!(h.context,actor);let first=runtime.fault==0
   h.free!(h.context,actor)
   record("scene double free rejected",first && runtime.fault != 0 && !f.memory.sceneObjectPointers.contains(actor))
  }
  do {
   let f=try Fixture(profile,hash);_=f.heap.store(token:actor+0x1c0,words:1);f.put(actor+0x1c0,0x11223344)
   let r=f.run()
   record("allocation cannot overlap physical actor padding",!completed(r) && f.get(actor+0x1c0)==0x11223344 && f.heap.allocationIdentity(at:actor,count:0x1b4)==nil)
  }
  do {
   let f=try Fixture(profile,hash);_=f.heap.store(token:state,words:1);f.put(state,0x55667788)
   let r=f.run()
   record("state allocation cannot overlap existing next block",!completed(r) && f.get(state)==0x55667788)
  }
  do {
   let f=try Fixture(profile,hash);var nested:ClawNativeCanonicalHost.Completion?
   f.memory.beforeObjectAllocation={_ in nested=f.host.invoke(f.call())}
   record("canonical allocation reentry rejected",!completed(f.run()) && nested?.completed==false)
  }
  do {
   let f=try Fixture(profile,hash);var rejected=false
   f.memory.beforeObjectAllocation={_ in if f.memory.sceneObjectPointers.contains(actor) {rejected = !f.memory.releaseSceneObject(actor)}}
   let r=f.run()
   record("scene release during physical allocation service rejected",rejected && !completed(r) && f.heap.lookupBytes(actor,count:0x1b4) != nil)
  }
  do {
   let f=try Fixture(profile,hash);var nested=false
   let scope=f.host.withObjectAllocation(provider:f.memory){nested=f.host.withObjectAllocation(provider:f.memory){f.host.invoke(f.call())}==nil}
   record("nested allocation scope rejected",nested && scope==nil)
  }
  do {
   let runtime=try scene(),f=try Fixture(profile,hash)
   record("foreign scene heap registration rejected",!runtime.registerObjectAllocationOwner(f.memory))
  }
  do {
   let f=try Fixture(profile,hash,sceneStorage:false),r=f.run()
   record("standalone allocation profile unchanged",completed(r) && f.get(actor+0x6c)==actor+0x1c0 && f.heap.lookup(actor,words:128)==nil && f.memory.sceneObjectPointers.isEmpty && !f.memory.releaseSceneObject(actor))
  }
  do {
   let runtime=try scene(),f=try Fixture(profile,hash,scene:runtime,sceneStorage:false,registerOwner:false)
   record("default standalone owner cannot register scene lifetime",!runtime.registerObjectAllocationOwner(f.memory))
  }
  do {
   let runtime=try scene(),f=try Fixture(profile,hash,scene:runtime,registerOwner:false)
   var denied=false
   f.memory.beforeObjectAllocation={_ in denied = !runtime.registerObjectAllocationOwner(f.memory)}
   let r=f.run()
   record("owner registration during physical allocation rejected",denied && completed(r) && runtime.registerObjectAllocationOwner(f.memory))
  }
  for (token,count) in [(actor,UInt32(0x1b4)),(state,UInt32(0x174))] {
   let f=try Fixture(profile,hash);_=f.run()
   let identity=f.heap.allocationIdentity(at:token,count:count)!
   var call=ClawCall();call.function=0x546a80;call.argumentCount=3;call.stackPointer=UInt32(CLAW_STACK_BASE)
   call.arguments.0=token;call.arguments.1=count;call.arguments.2=2
   let result=f.memory.service(call)
   record("ordinary resize rejects published scene token \(token)",result==nil && f.host.fault != nil && f.heap.allocationIdentity(at:token,count:count) === identity && f.memory.sceneObjectPointers==[actor,state] && f.memory.localRequestedSizes[token]==count)
  }
  do {
   let f=try Fixture(profile,hash);_=f.run()
   var call=ClawCall();call.function=0x5469d8;call.argumentCount=1;call.stackPointer=UInt32(CLAW_STACK_BASE)
   call.arguments.0=actor;let freedActor=f.memory.service(call)==0
   call.arguments.0=state;let freedState=f.memory.service(call)==0
   let retired=f.memory.sceneObjectPointers.isEmpty && f.memory.localPointers.isEmpty && f.heap.lookupBytes(actor,count:1)==nil && f.heap.lookupBytes(state,count:1)==nil && f.memory.validObjectAllocationBinding(for:f.host)
   f.detachFixtureList()
   let next=f.host.withObjectAllocation(provider:f.memory){f.host.invoke(f.call())}
   diagnostics.append(["phase":"LocalFree then scope","freedActor":freedActor,"freedState":freedState,"retired":retired,"nextCompleted":next?.completed ?? false,"hostFault":f.host.fault.map{String(describing:$0)} ?? "","remaining":f.memory.sceneObjectPointers])
   record("ordinary LocalFree retires scene ledger and permits later scope",freedActor && freedState && retired && next?.completed==true && f.memory.sceneObjectPointers.count==2)
  }
  do {
   let f=try Fixture(profile,hash,sceneStorage:false);_=f.run()
   let prior=Array(UnsafeBufferPointer(start:f.heap.lookupBytes(actor,count:0x1b4)!,count:0x1b4))
   var call=ClawCall();call.function=0x546a80;call.argumentCount=3;call.stackPointer=UInt32(CLAW_STACK_BASE)
   call.arguments.0=actor;call.arguments.1=0x1b8;call.arguments.2=2
   let replacement=f.memory.service(call) ?? 0
   let copied=f.heap.lookupBytes(replacement,count:0x1b4).map{Array(UnsafeBufferPointer(start:$0,count:0x1b4))}==prior
   record("ordinary standalone LocalReAlloc behavior preserved",replacement != 0 && replacement != actor && copied && f.heap.lookupBytes(actor,count:1)==nil && f.memory.localRequestedSizes[replacement]==0x1b8 && f.memory.validObjectAllocationBinding(for:f.host))
  }
  for (address,count) in [(actor,UInt32(0x1b5)),(actor+0x1b4,UInt32(1))] {
   let f=try Fixture(profile,hash);_=f.run()
   let identity=f.heap.allocationIdentity(at:actor,count:0x1b4)!
   record("canonical host rejects padding byte span \(address) count \(count)",f.host.bytes(address,count:count)==nil && f.host.fault != nil && f.heap.allocationIdentity(at:actor,count:0x1b4) === identity)
  }
  let result:[String:Any]=["version":1,"profiles":output,"controls":controls,"diagnostics":diagnostics]
  try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("native.json"))
  print("native lifecycle profiles \(output.count), controls \(controls.count)")
 }
}
