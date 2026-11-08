import Foundation
private let observed:Set<UInt32>=[0x471530,0x4c7fa0,0x4f63ec,0x4c8160,0x4c81b0,0x40f680,0x4c82a0]
private func require(_ condition:Bool,_ message:String){precondition(condition,message)}
private func hex(_ data:Data)->String{data.map{String(format:"%02x",$0)}.joined()}
private func segment(_ heap:ClawTokenHeap,_ address:UInt32,_ count:UInt32)->[String:Any]{
 guard let bytes=heap.lookupBytes(address,count:count) else{preconditionFailure("Missing span \(String(address,radix:16))/\(count)")}
 return ["address":address,"hex":hex(Data(bytes:bytes,count:Int(count)))]
}
private func graph(_ heap:ClawTokenHeap)->[[String:Any]]{heap.debugAllocationBases.map{token in
 var low:UInt32=1,high:UInt32=4<<20
 while low<high{let middle=low+(high-low+1)/2;if heap.lookupBytes(token,count:middle) != nil{low=middle}else{high=middle-1}}
 return segment(heap,token,low)
}}
private func word(_ scene:ClawNativeScene,_ token:UInt32)->UInt32{scene.heap.lookup(token,words:1)!.pointee}
private func put(_ scene:ClawNativeScene,_ token:UInt32,_ value:UInt32){scene.heap.lookup(token,words:1)!.pointee=value}
private func body(_ scene:ClawNativeScene)->ClawNativeBehindStatue{scene.objectConnections!.adapter("behind_statue") as! ClawNativeBehindStatue}
private func front(_ scene:ClawNativeScene)->ClawNativeFrontStatue{scene.objectConnections!.adapter("front_statue") as! ClawNativeFrontStatue}
private func text(_ host:ClawNativeCanonicalHost,_ token:UInt32)->String?{
 var data:[UInt8]=[]
 for index:UInt32 in 0..<256{guard let p=host.bytes(token+index,count:1) else{return nil};if p[0]==0{return String(bytes:data,encoding:.ascii)};data.append(p[0])};return nil
}
private func global(_ address:UInt32,_ values:[UInt32])->[String:Any]{["address":address,"hex":values.withUnsafeBytes{hex(Data($0))}]}
func runConnection(_ directory:URL)throws{
 let root=directory.appendingPathComponent("resources").standardizedFileURL,level=try ClawLevelScene(root:root),assets=try ClawPlayerAssets(root:root)
 let world=try ClawWorld(data:Data(contentsOf:directory.appendingPathComponent("WORLD5.WWD")))
 guard let record=world.planes.flatMap(\.objects).first(where:{$0.logic=="BehindStatue"}),let baseRecord=world.planes.flatMap(\.objects).first(where:{$0.logic=="FrontStatue"}) else{preconditionFailure("Original BehindStatue and FrontStatue records")}
 func scene()throws->ClawNativeScene{
  let s=ClawNativeScene(player:try ClawNativePlayer(world:level.world,assets:assets),clock:{1000})
  try s.loadRecoveredObjects(world:level.world,root:root);require(s.fault==0,"Scene setup");s.objectConnections!.recordsTrace=true;return s
 }
 func attach(_ s:ClawNativeScene,_ object:ClawWorld.Object)->UInt32{
  let before=object.logic=="BehindStatue" ? body(s).tokens:front(s).tokens,index=level.world.planes.firstIndex(where:{$0.flags & 1 != 0})!,plane=s.camera!.planeTokens[index]
  let result=s.loadGridObject(object,world:world,plane:plane)
  require(result==object.encodedRecord.count && s.fault==0,"loadGridObject \(object.logic): \(String(describing:s.objectLoadingFailure)) / \(String(describing:s.objectConnections!.host.fault))")
  let after=object.logic=="BehindStatue" ? body(s).tokens:front(s).tokens
  let added=after.subtracting(before);require(added.count==1,"Exactly one scene-owned actor");return added.first!
 }
 func dispatch(_ s:ClawNativeScene,_ actor:UInt32,_ callback:UInt32,_ delta:UInt32=17){
  var timing=ClawPlayerDeathCommandGlobals();s.captureDeathTiming(&timing);timing.animation.deltaMilliseconds=delta;s.publishDeathTiming(timing)
  var call=ClawSceneActorCall();call.function=callback;call.argumentCount=1;call.arguments.0=actor
  let host=s.actorHost;_=host.call!(host.context,call)
 }
 let s=try scene(),actor=attach(s,record),baseActor=attach(s,baseRecord),bridge=s.objectConnections!,adapter=body(s)
 let state=word(s,actor+0x6c),baseState=word(s,baseActor+0x6c)
 require(word(s,actor+0x70)==0 && word(s,baseActor+0x70)==0,"Both roots begin without secondary storage")
 let initial=graph(s.heap)
 var allocations:[[String:UInt32]]=[],bindings:[[String:Any]]=[],services:[[Any]]=[]
 let dependency=bridge.host.dependency
 bridge.host.dependency={host,call in
  let key=call.function==0x4f6286 ? text(host,call.arguments.0):nil,result=dependency?(host,call)
  if call.function==0x4f6286,let key,let out=host.bytes(call.arguments.1,count:4){
   let token=UnsafeRawPointer(out).loadUnaligned(as:UInt32.self).littleEndian;services.append(["registry",call.receiver,key,token])
   if !bindings.contains(where:{($0["receiver"] as? UInt32)==call.receiver && ($0["name"] as? String)==key}){bindings.append(["receiver":call.receiver,"name":key,"token":token])}
  };return result
 }
 for memory in [adapter.memory!,front(s).memory!]{memory.afterService={function,args,value in if function==0x4a48e0{allocations.append(["token":value,"count":args[0]]);services.append(["malloc",value,args[0]])}}}
 var inputSteps:[[String:Any]]=[],outputSteps:[[String:Any]]=[]
 let scenarios:[(String,UInt32,UInt32,[[UInt32]])]=[
  ("statue initialize",actor,0x4717b0,[[state+0x54,123],[state+0x64,91]]),
  ("statue cooldown",actor,0x4717b0,[[state+0x130,42]]),
  ("statue reset and rebind",actor,0x4717b0,[[state+0x1c,0]]),
  ("following FrontStatue",baseActor,0x471780,[[baseState+0x54,123],[baseState+0x64,91]]),
  ("BehindStatue after FrontStatue",actor,0x4717b0,[]),
  ("FrontStatue after BehindStatue",baseActor,0x471780,[]) ]
 for (label,target,callback,writes) in scenarios{
  print("BehindStatue comparison: \(label)")
  for row in writes{put(s,row[0],row[1])};services=[];let start=bridge.calls.count
  dispatch(s,target,callback)
  require(s.fault==0 && bridge.host.fault==nil,"\(label): scene=\(s.fault) host=\(String(describing:bridge.host.fault))")
  let secondary=word(s,target+0x70)
  let spans:[(UInt32,UInt32)]=[(actor,0x1b4),(state,0x174),(baseActor,0x1b4),(baseState,0x174),(0x52a194,4)] + [(secondary,UInt32(0x174))]
  inputSteps.append(["label":label,"actor":target,"callback":callback,"writes":writes+[[UInt32(0x5430c4),UInt32(17)]],"spans":spans.map{["address":$0.0,"count":$0.1]}])
  outputSteps.append(["label":label,"calls":bridge.calls.dropFirst(start).filter{observed.contains($0.function)}.map{[$0.function,$0.receiver]},"services":services,"spans":spans.map{segment(s.heap,$0.0,$0.1)}])
  require(word(s,0x52a194)==s.singleCrates!.globals.pointee.crateImageChoice,"Shared crate global is synchronized")
  require(word(s,0x52a194)==(callback==0x4717b0 ? 2:3),"Root-specific variant")
  let descriptor=word(s,target+0x6c)
  require(word(s,descriptor+0x54)==(callback==0x4717b0 ? 1:UInt32.max) && word(s,descriptor+0x64)==0,"Root-specific descriptor")
 }
 bridge.host.dependency=dependency;adapter.memory!.afterService=nil;front(s).memory!.afterService=nil
 var controls:[String:Bool]=["shared_variant_follows_front_callback":word(s,0x52a194)==3,
  "distinct_secondary_owners":word(s,actor+0x70) != word(s,baseActor+0x70) && adapter.memory!.ownsObjectAllocation(word(s,actor+0x70),count:0x174) && front(s).memory!.ownsObjectAllocation(word(s,baseActor+0x70),count:0x174)]
 var hitInputs:[[String:Any]]=[],hitOutputs:[[String:Any]]=[],phaseProfiles:[[String:Any]]=[],phaseOutputs:[[String:Any]]=[]
 for target in [actor,baseActor]{
  print("BehindStatue downstream hit: \(target==actor ? "statue":"FrontStatue")")
  let logic=word(s,target+0x6c)
  // Controlled physical hit and loot slots; all crate/pickup decisions remain source code.
  put(s,target+0x74,s.player.sceneSnapshot().token);put(s,target+0x10c,1);put(s,logic+0x130,0)
  put(s,target+0x100,1);for offset:UInt32 in stride(from:0xf0,through:0x10c,by:4){put(s,logic+offset,0)}
  put(s,logic+0xf0,2)
  if target==actor{dispatch(s,target,0x4717b0)}else{dispatch(s,target,0x471780)}
  let sequence=try s.objectResources!.sequence(name:"LEVEL_CRATEBREAK")!
  let lookupReceiver=word(s,s.sceneIdentity+0x2c)+0x10
  let resourceBindings:[[String:Any]]=[["receiver":lookupReceiver,"name":"LEVEL_CRATEBREAK","token":sequence.token]]
  let seed:UInt32=12345;s.random.seedPointer!.pointee=seed
  let loot=s.loot!,table=withUnsafeBytes(of:&loot.globals.pointee.words){Array($0.bindMemory(to:UInt32.self))}
  let globals=[global(0x537ec8,table),global(0x52a190,[loot.globals.pointee.itemCount]),global(0x53721c,[loot.globals.pointee.highLaunch]),global(0x532c0c,[0]),global(0x532c10,[0])]
  var creation:[[UInt32]]=[];let previous=loot.onCreated
  loot.onCreated={goodie in
   creation.append([goodie.token,word(s,goodie.token+0x6c),s.containerToken,word(s,goodie.token+0x4c),word(s,goodie.token+0x50),word(s,goodie.token+0x64)])
   previous?(goodie)
  }
  let before=graph(s.heap),spans:[(UInt32,UInt32)]=[(target,0x1b4),(logic,0x174),(0x52a194,4)]
  dispatch(s,target,0x4717e0);loot.onCreated=previous
  require(s.fault==0 && s.singleCrates!.fault==0 && loot.failure==nil && !creation.isEmpty,"Real crate pickup: \(s.fault) / \(String(describing:loot.failure))")
  let created=creation.map{["actor":$0[0],"state":$0[1],"private":word(s,$0[1]+0x18)]}
  let effects=created.map{row->[String:Any] in
   let a=row["actor"]!,p=row["private"]!
   require(loot.goodies[a]?.failure==nil,"Goodie source owner completed")
   return ["actor":a,"position":[word(s,a+0x4c),word(s,a+0x50),word(s,a+0x64)],"physics":(segment(s.heap,p+0x40,8)["hex"] as! String)+(segment(s.heap,p+0x50,24)["hex"] as! String),"item":word(s,p+0x184),"image":word(s,a+0x170),"frame":word(s,a+0x174)]
  }
  hitInputs.append(["actor":target,"segments":before+globals,"seed":seed,"created":created,"resourceBindings":resourceBindings,"spans":spans.map{["address":$0.0,"count":$0.1]}])
  hitOutputs.append(["calls":creation.map{[$0[2],UInt32(1),$0[3],$0[4],$0[5],UInt32(0x522cc0),UInt32(0x40000)]},"effects":effects,"seed":s.random.seedPointer!.pointee,"spans":spans.map{segment(s.heap,$0.0,$0.1)}])
  controls[target==actor ? "statue_scatter_real_pickups":"front_statue_scatter_real_pickups"]=creation.count==2
  let phaseInitial=graph(s.heap)+[global(0x532c0c,[0]),global(0x532c10,[0])]
  var phaseInput:[[String:Any]]=[],phaseOutput:[[String:Any]]=[]
  for delta:UInt32 in [17,1000,17]{
   print("BehindStatue post-hit animation delta \(delta)")
   let start=bridge.calls.count,callback:UInt32=target==actor ? 0x4717b0:0x471780,label="post-hit \(target) delta \(delta)"
   dispatch(s,target,callback,delta)
   require(s.fault==0 && bridge.host.fault==nil,"Post-hit animation: \(String(describing:bridge.host.fault))")
   phaseInput.append(["label":label,"actor":target,"callback":callback,"writes":[[UInt32(0x5430c4),delta]],"spans":spans.map{["address":$0.0,"count":$0.1]}])
   phaseOutput.append(["label":label,"calls":bridge.calls.dropFirst(start).filter{observed.contains($0.function)}.map{[$0.function,$0.receiver]},"services":[],"spans":spans.map{segment(s.heap,$0.0,$0.1)}])
  }
  phaseProfiles.append(["segments":phaseInitial,"allocations":[],"resourceBindings":[],"steps":phaseInput]);phaseOutputs.append(["steps":phaseOutput])
 }
 let positiveFaults=s.fault | s.singleCrates!.fault,positiveUnresolved=s.unresolvedDependencies.union(s.singleCrates!.unresolved).union(s.loot!.unresolved)
 try JSONSerialization.data(withJSONObject:["profiles":[["segments":initial,"allocations":allocations,"resourceBindings":bindings,"steps":inputSteps]]+phaseProfiles,"hits":hitInputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("behind-native-input.json"))
 try JSONSerialization.data(withJSONObject:["profiles":[["steps":outputSteps]]+phaseOutputs,"hits":hitOutputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("behind-partial-output.json"))
 print("BehindStatue ownership controls")
 let missing=try scene(),missingActor=attach(missing,record);missing.objectConnections!.host.dependency=nil;dispatch(missing,missingActor,0x4717b0)
 controls["missing_registry_service_rejected"]=missing.objectConnections!.host.fault?.diagnostic == .missingDependency && missing.objectConnections!.host.fault?.address==0x4f6286 && missing.fault != 0
 for offset:UInt32 in [0,0x6c]{
  let stale=try scene(),a=attach(stale,record),token=offset==0 ? a:word(stale,a+offset),count:UInt32=offset==0 ? 0x1b4:0x174
  let bytes=Data(bytes:stale.heap.lookupBytes(token,count:count)!,count:Int(count));stale.heap.free(token)
  bytes.withUnsafeBytes{stale.heap.storeBytes(token:token,count:count).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:Int(count))}
  dispatch(stale,a,0x4717b0);controls[offset==0 ? "replacement_actor_rejected":"replacement_primary_rejected"]=stale.objectConnections!.host.fault != nil
 }
 let foreign=try scene(),foreignActor=attach(foreign,record);dispatch(foreign,foreignActor,0x4717b0)
 let actual=word(foreign,foreignActor+0x70),fake=foreign.heap.allocate(bytes:0x174)
 foreign.heap.lookupBytes(fake,count:0x174)!.update(from:foreign.heap.lookupBytes(actual,count:0x174)!,count:0x174);put(foreign,foreignActor+0x70,fake);dispatch(foreign,foreignActor,0x4717b0)
 controls["foreign_secondary_rejected"]=foreign.objectConnections!.host.fault != nil && foreign.heap.lookupBytes(fake,count:1) != nil
 let wrongRoot=try scene(),wrongActor=attach(wrongRoot,record)
 dispatch(wrongRoot,wrongActor,0x471780)
 controls["foreign_root_dispatch_rejected"]=wrongRoot.objectConnections!.host.fault != nil && word(wrongRoot,wrongActor+0x70)==0
 let wrongDescriptor=try scene(),wrongDescriptorActor=attach(wrongDescriptor,record)
 put(wrongDescriptor,word(wrongDescriptor,wrongDescriptorActor+0x6c)+0x10,0x471780);dispatch(wrongDescriptor,wrongDescriptorActor,0x4717b0)
 controls["foreign_descriptor_callback_rejected"]=wrongDescriptor.objectConnections!.host.fault != nil && word(wrongDescriptor,wrongDescriptorActor+0x70)==0
 let crossed=try scene(),crossedBehind=attach(crossed,record),crossedFront=attach(crossed,baseRecord)
 dispatch(crossed,crossedBehind,0x4717b0);dispatch(crossed,crossedFront,0x471780)
 let frontSecondary=word(crossed,crossedFront+0x70)
 put(crossed,crossedBehind+0x70,frontSecondary);dispatch(crossed,crossedBehind,0x4717b0)
 controls["cross_root_secondary_rejected"]=crossed.objectConnections!.host.fault != nil && front(crossed).memory!.ownsObjectAllocation(frontSecondary,count:0x174)
 let retired=try scene(),retiredActor=attach(retired,record);dispatch(retired,retiredActor,0x4717b0)
 let retiredState=word(retired,retiredActor+0x6c),retiredSecondary=word(retired,retiredActor+0x70)
 let actionPlane=level.world.planes.firstIndex(where:{$0.flags & 1 != 0})!,plane=retired.camera!.planeTokens[actionPlane],grid=word(retired,plane+0xb0)
 let flags=word(retired,retiredActor+8),layerIndex:UInt32=flags & 0x800000 != 0 ? 1:flags & 0x1000000 != 0 ? 2:0
 let layer=word(retired,grid+(layerIndex+1)*4),member=retiredActor+0x88
 _=retired.spatial(0x4f4680,receiver:layer,arguments:[member])
 var destruction=ClawSceneActorCall();destruction.function=0x4c9be0;destruction.receiver=retiredActor;destruction.argumentCount=1;destruction.arguments.0=1
 let destructionHost=retired.actorHost;_=destructionHost.call!(destructionHost.context,destruction)
 controls["scene_destruction_retires_shared_secondary"]=retired.fault==0 && !body(retired).tokens.contains(retiredActor) && [retiredActor,retiredState,retiredSecondary].allSatisfy{retired.heap.lookupBytes($0,count:1)==nil} && !body(retired).memory!.ownsObjectAllocation(retiredSecondary,count:0x174)
 let beforeRetired=retired.objectConnections!.calls.count;dispatch(retired,retiredActor,0x4717b0)
 controls["retired_actor_dispatch_rejected"]=retired.objectConnections!.host.fault != nil && retired.objectConnections!.calls.count==beforeRetired
 var forged=ClawCall();forged.function=0x4f6286;forged.receiver=0x62000010;forged.argumentCount=2;forged.arguments.0=0x5228dc;forged.arguments.1=actor
 controls["service_outside_active_callback_rejected"]=adapter.service(forged)==nil
 require(controls.values.allSatisfy{$0},"BehindStatue controls: \(controls)")
 try JSONSerialization.data(withJSONObject:["profiles":[["segments":initial,"allocations":allocations,"resourceBindings":bindings,"steps":inputSteps]]+phaseProfiles,"hits":hitInputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("behind-native-input.json"))
 try JSONSerialization.data(withJSONObject:["profiles":[["steps":outputSteps]]+phaseOutputs,"hits":hitOutputs,"controls":controls,"trace":bridge.trace,"faults":positiveFaults,"unresolvedDependencies":positiveUnresolved.sorted()],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("behind-native-output.json"))
}
