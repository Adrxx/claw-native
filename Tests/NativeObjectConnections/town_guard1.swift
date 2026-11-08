import Foundation
private let observed:Set<UInt32>=[0x43e9b0,0x48cf50,0x4c81b0,0x4c8160,0x403b40,0x405000,0x4061b0,0x4062e0,0x420fc0,0x43dfa0,0x43e420,0x44c000,0x44cfd0,0x44d000,0x44d3c0,0x44f1b0,0x496110,0x497130,0x497510,0x497970,0x4979b0,0x497a50,0x4c7970,0x4c7fa0,0x4c8060,0x4c8220,0x4c96b0,0x4cbb60,0x4db620,0x4dbcd0,0x4dbd20,0x4dbd60,0x4dbe10,0x4dc180,0x4dc870,0x4f63ec,0x4f6428,0x4f6439,0x4f6584]
private func require(_ value:Bool,_ message:String){precondition(value,message)}
private func segment(_ heap:ClawTokenHeap,_ address:UInt32,_ count:UInt32)->[String:Any]{
 guard let bytes=heap.lookupBytes(address,count:count) else{preconditionFailure("Missing span \(String(address,radix:16))/\(count)")}
 return ["address":address,"hex":Data(bytes:bytes,count:Int(count)).map{String(format:"%02x",$0)}.joined()]
}
private func graph(_ heap:ClawTokenHeap)->[[String:Any]]{heap.debugAllocationBases.map{token in
 var low:UInt32=1,high:UInt32=4<<20
 while low<high{let middle=low+(high-low+1)/2;if heap.lookupBytes(token,count:middle) != nil{low=middle}else{high=middle-1}}
 return segment(heap,token,low)
}}
private func body(_ scene:ClawNativeScene)->ClawNativeTownGuard1{scene.objectConnections!.adapter("town_guard1") as! ClawNativeTownGuard1}
private func text(_ host:ClawNativeCanonicalHost,_ token:UInt32)->String?{
 var value:[UInt8]=[]
 for offset:UInt32 in 0..<256{guard let bytes=host.bytes(token+offset,count:1) else{return nil};if bytes[0]==0{return String(bytes:value,encoding:.ascii)};value.append(bytes[0])};return nil
}
private func word(_ scene:ClawNativeScene,_ token:UInt32)->UInt32{scene.heap.lookup(token,words:1)!.pointee}
private func put(_ scene:ClawNativeScene,_ token:UInt32,_ value:UInt32){scene.heap.lookup(token,words:1)!.pointee=value}
func runConnection(_ suppliedDirectory:URL)throws{
 let directory=suppliedDirectory.standardizedFileURL
 let root=directory.appendingPathComponent("resources").standardizedFileURL,level=try ClawLevelScene(root:directory.appendingPathComponent("resources").standardizedFileURL),assets=try ClawPlayerAssets(root:directory.appendingPathComponent("resources").standardizedFileURL)
 let world=try ClawWorld(data:Data(contentsOf:directory.appendingPathComponent("WORLD5.WWD")))
 guard let record=world.planes.flatMap(\.objects).first(where:{$0.logic=="TownGuard1"}) else{preconditionFailure("Original WWD TownGuard1")}
 var sceneNumber=0
 func scene()throws->ClawNativeScene{
  sceneNumber += 1;print("TownGuard1 comparison scene \(sceneNumber) setup")
  let value=ClawNativeScene(player:try ClawNativePlayer(world:level.world,assets:assets),clock:{1000})
  // Use the Level 1 scene whose compressed world and resource overlay
  // prepare() supplies; attach the untouched Level 5 WWD actor below.
  try value.loadRecoveredObjects(world:level.world,root:root);require(value.fault==0,"Scene setup");value.objectConnections!.recordsTrace=true;return value
 }
 func attach(_ runtime:ClawNativeScene)->UInt32{
  let before=body(runtime).tokens
  let actionPlane=level.world.planes.firstIndex(where:{$0.flags & 1 != 0})!
  let plane=runtime.camera!.planeTokens[actionPlane]
  print("TownGuard1 attach WWD id=\(record.id) xy=\(record.x),\(record.y) image=\(record.imageSet) plane=\(String(plane,radix:16)) sceneFaultBefore=\(runtime.fault)")
  let result=runtime.loadGridObject(record,world:world,plane:plane)
  require(result==record.encodedRecord.count && runtime.fault==0,"TownGuard1 attachment result=\(result)/\(record.encodedRecord.count) sceneFault=\(runtime.fault) unresolved=\(runtime.unresolvedDependencies) adapterTokens=\(body(runtime).tokens) bridgeOwners=\(runtime.objectConnections!.ownedActors) WWD=\(record.id) xy=\(record.x),\(record.y) image=\(record.imageSet) hostFault=\(String(describing:runtime.objectConnections!.host.fault)) loadingFailure=\(String(describing:runtime.objectLoadingFailure))")
  let added=body(runtime).tokens.subtracting(before);require(added.count==1,"One scene owner");return added.first!
 }
 func dispatch(_ runtime:ClawNativeScene,_ actor:UInt32,_ command:UInt32){
  put(runtime,word(runtime,actor+0x6c)+0x1c,command)
  var timing=ClawPlayerDeathCommandGlobals();runtime.captureDeathTiming(&timing);timing.animation.deltaMilliseconds=17;runtime.publishDeathTiming(timing)
  var call=ClawSceneActorCall();call.function=0x496050;call.argumentCount=1;call.arguments.0=actor
  let host=runtime.actorHost;_=host.call!(host.context,call)
 }
 func destroy(_ runtime:ClawNativeScene,_ actor:UInt32){
  print("TownGuard1 remove spatial residency for actor \(String(actor,radix:16))")
  let actionPlane=level.world.planes.firstIndex(where:{$0.flags & 1 != 0})!
  let plane=runtime.camera!.planeTokens[actionPlane],grid=word(runtime,plane+0xb0)
  let flags=word(runtime,actor+8),layerIndex:UInt32=flags & 0x800000 != 0 ? 1:flags & 0x1000000 != 0 ? 2:0
  let layer=word(runtime,grid+(layerIndex+1)*4),member=actor+0x88,cell=word(runtime,member+12)
  let next=word(runtime,member),previous=word(runtime,member+4),count=word(runtime,layer+8)
  require(cell != 0 && count>0,"Original spatial residency before destruction")
  _=runtime.spatial(0x4f4680,receiver:layer,arguments:[member])
  require(runtime.fault==0 && word(runtime,member+12)==0 && word(runtime,layer+8)==count-1 &&
      word(runtime,previous==0 ? cell:previous)==next && word(runtime,next==0 ? cell+4:next+4)==previous,
      "Original spatial unlink removes the cell membership")
  print("TownGuard1 destroy actor \(String(actor,radix:16))")
  var call=ClawSceneActorCall();call.function=0x4c9be0;call.receiver=actor;call.argumentCount=1;call.arguments.0=1
  let host=runtime.actorHost;_=host.call!(host.context,call)
 }
 let runtime=try scene()
  let registry=runtime.stateRegistry!
  let idle=UInt32((0..<registry.registry.pointee.nextId).first {
   let view=registry.resolve(Int32($0))
   guard let name=view.name else{return false}
   return String(cString:name)=="LS_IDLE2"
  }!)

 var inputs:[[String:Any]]=[],outputs:[[String:Any]]=[],controls:[String:Bool]=[:]
 var retiredHelper:UInt32=0,firstActor:UInt32=0,positiveFaults:UInt32=0
 var positiveUnresolved:Set<UInt32>=[]
 for iteration in 0..<2{
  print("TownGuard1 positive profile \(iteration)")
  let actor=attach(runtime),state=word(runtime,actor+0x6c),adapter=body(runtime),bridge=runtime.objectConnections!
  if iteration==0{firstActor=actor};let initial=graph(runtime.heap)
  var allocations:[[String:UInt32]]=[],bindings:[[String:Any]]=[],services:[[Any]]=[],randomValues:[UInt32]=[]
  let dependency=bridge.host.dependency
  bridge.host.dependency={host,call in
   let key=call.function==0x4f6286 ? text(host,call.arguments.0):nil,value=dependency?(host,call)
   if call.function==0x4f6286,let key,let pointer=host.bytes(call.arguments.1,count:4){
    let token=UnsafeRawPointer(pointer).loadUnaligned(as:UInt32.self).littleEndian
    services.append(["registry",call.receiver,key,token])
    if !bindings.contains(where:{($0["receiver"] as? UInt32)==call.receiver && ($0["name"] as? String)==key}){bindings.append(["receiver":call.receiver,"name":key,"token":token])}
   }
   if call.function==0x4a3050,let value { randomValues.append(value);services.append(["rand",value]) }
   return value
  }
  adapter.memory!.afterService={function,args,value in if function==0x4a48e0{allocations.append(["token":value,"count":args[0]]);services.append(["malloc",value,args[0]])}}
  var inputSteps:[[String:Any]]=[],outputSteps:[[String:Any]]=[]
  for index in 0..<5{
   let command:UInt32=index==0 ? 0:index==1 ? 1000:index==2 ? 29:index==3 ? 30:idle
   services=[];let before=bridge.calls.count
   var clocks:[[String:Any]]=[["address":UInt32(0x5430c4),"hex":"11000000"],["address":UInt32(0x537210),"hex":withUnsafeBytes(of:runtime.gameTime.littleEndian){Data($0).map{String(format:"%02x",$0)}.joined()}]]
   if index==4 {
    let helper=word(runtime,state+0x18)
    put(runtime,helper+0x488,runtime.gameTime);put(runtime,helper+0x48c,20);put(runtime,actor+0xcc,7)
    clocks += [segment(runtime.heap,helper+0x488,8),segment(runtime.heap,actor+0xcc,4)]
   }
   print("TownGuard1 profile \(iteration) command \(command)")
   let activeInput:[String:Any]=["name":"WWD-\(record.id)-\(iteration)","actor":actor,"state":state,"segments":initial,"command":command,"inputGlobals":clocks,"completedSteps":inputSteps]
   try JSONSerialization.data(withJSONObject:activeInput,options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("town-active-input.json"))
   dispatch(runtime,actor,command)
   if runtime.fault != 0 || bridge.host.fault != nil {
    let failed:[String:Any]=["command":command,"fault":String(describing:bridge.host.fault),"sceneFault":runtime.fault,"trace":bridge.trace,"calls":bridge.calls.map{[$0.function,$0.receiver]},"services":services,"allocations":allocations,"resourceBindings":bindings,"randomValues":randomValues,"unresolvedDependencies":runtime.unresolvedDependencies.sorted()]
    try JSONSerialization.data(withJSONObject:failed,options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("town-failed-callback.json"))
   }
   require(runtime.fault==0 && bridge.host.fault==nil,"TownGuard1 callback \(command): \(String(describing:bridge.host.fault))")
   let helper=word(runtime,state+0x18)
   require(adapter.memory!.ownsObjectAllocation(helper,count:0x498),"Physical ledger and real bindings")
   let spans:[(UInt32,UInt32)]=[(actor,0x1b4),(state,0x174),(helper,0x498),(word(runtime,actor+0x70),0x174),(word(runtime,actor+0x78),0x174),(0x53c9ac,8),(0x544b14,60),(0x537668,44),(0x537698,36),(0x53ca70,36),(0x537210,4),(0x5430c4,4)]
   inputSteps.append(["command":command,"inputGlobals":clocks,"spans":spans.map{["address":$0.0,"count":$0.1]}])
   outputSteps.append(["command":command,"calls":bridge.calls.dropFirst(before).filter{observed.contains($0.function)}.map{[$0.function,$0.receiver]},"services":services,"spans":spans.map{segment(runtime.heap,$0.0,$0.1)}])
  }
  bridge.host.dependency=dependency;adapter.memory!.afterService=nil
  let helper=word(runtime,state+0x18)
  inputs.append(["helper":helper,"retire":iteration==0,"randomValues":randomValues,"name":"WWD-\(record.id)-\(iteration)","actor":actor,"state":state,"segments":initial,"allocations":allocations,"resourceBindings":bindings,"steps":inputSteps]);outputs.append(["name":"WWD-\(record.id)-\(iteration)","steps":outputSteps,"retired":NSNull()])
  try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("town-partial-input.json"))
  try JSONSerialization.data(withJSONObject:["profiles":outputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("town-partial-output.json"))
  positiveFaults |= runtime.fault;positiveUnresolved.formUnion(runtime.unresolvedDependencies)
  require(positiveFaults==0 && positiveUnresolved.isEmpty,"Positive callback completion and dependency closure")
  if iteration==0{
   var retiredBytes:String?;let observer=bridge.host.observer
   bridge.host.observer={call in
    observer?(call)
    if call.function==0x4f6428 && call.arguments.0==helper { retiredBytes=segment(runtime.heap,helper,0x498)["hex"] as? String }
   }
   retiredHelper=helper;destroy(runtime,actor);bridge.host.observer=observer
   require(runtime.fault==0 && bridge.host.fault==nil,"Scene destruction: \(String(describing:bridge.host.fault))")
   outputs[iteration]["retired"]=retiredBytes ?? "missing"

   positiveFaults |= runtime.fault;positiveUnresolved.formUnion(runtime.unresolvedDependencies)
   controls["scene_destruction_retires_owner"]=runtime.fault==0 && !adapter.tokens.contains(actor) && [actor,state,helper].allSatisfy{runtime.heap.lookupBytes($0,count:1)==nil} && !adapter.memory!.ownsObjectAllocation(helper,count:0x498)
  }else{
   controls["same_scene_recreates_actor_and_helper"]=actor != firstActor && helper != retiredHelper && adapter.tokens.contains(actor)
   put(runtime,state+0x18,retiredHelper);dispatch(runtime,actor,1000)
   controls["retired_helper_rejected"]=bridge.host.fault != nil && runtime.fault != 0
  }
 }
 let missing=try scene(),missingActor=attach(missing);missing.objectConnections!.host.dependency=nil;dispatch(missing,missingActor,0)
 controls["missing_resource_service_rejected"]=missing.objectConnections!.host.fault?.diagnostic == .missingDependency && missing.fault != 0
 let stale=try scene(),staleActor=attach(stale),saved=Data(bytes:stale.heap.lookupBytes(staleActor,count:0x1b4)!,count:0x1b4)
 stale.heap.free(staleActor);saved.withUnsafeBytes{stale.heap.storeBytes(token:staleActor,count:0x1b4).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0x1b4)};dispatch(stale,staleActor,0)
 controls["replacement_actor_rejected"]=stale.objectConnections!.host.fault != nil && stale.objectConnections!.calls.isEmpty
 let foreign=try scene(),foreignActor=attach(foreign);dispatch(foreign,foreignActor,0);require(foreign.fault==0,"Foreign control initialization")
 let foreignState=word(foreign,foreignActor+0x6c),realHelper=word(foreign,foreignState+0x18),copy=Data(bytes:foreign.heap.lookupBytes(realHelper,count:0x498)!,count:0x498),fake=foreign.heap.allocate(bytes:0x498)
 copy.withUnsafeBytes{foreign.heap.lookupBytes(fake,count:0x498)!.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0x498)};put(foreign,foreignState+0x18,fake);dispatch(foreign,foreignActor,1000)
 controls["foreign_helper_rejected"]=foreign.objectConnections!.host.fault != nil && foreign.heap.lookupBytes(fake,count:0x498) != nil
 let outside=try scene(),outsideActor=attach(outside)
 var forged=ClawCall();forged.function=0x4f6286;forged.receiver=0x62000010;forged.argumentCount=2;forged.arguments.0=0x522d54;forged.arguments.1=outsideActor
 controls["service_outside_callback_rejected"]=body(outside).service(forged)==nil
 require(controls.values.allSatisfy{$0},"TownGuard1 ownership controls: \(controls)")
 try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("town-native-input.json"))
 try JSONSerialization.data(withJSONObject:["profiles":outputs,"controls":controls,"trace":runtime.objectConnections!.trace,"faults":positiveFaults,"unresolvedDependencies":positiveUnresolved.sorted()],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("town-native-output.json"))
}
