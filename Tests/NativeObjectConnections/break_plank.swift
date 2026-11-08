import Foundation
private let observed:Set<UInt32>=[0x4f63ec,0x40f870,0x4c7fa0,0x4c8060,0x4c8160,0x4c81b0,0x4c8da0,0x4c96b0,0x4dc870,0x4c9e30,0x40fb30,0x4890f0,0x4041b0]
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
private func body(_ scene:ClawNativeScene)->ClawNativeBreakPlank{scene.objectConnections!.adapter("break_plank") as! ClawNativeBreakPlank}
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
 guard let record=world.planes.flatMap(\.objects).first(where:{$0.logic=="BreakPlank" && $0.id==7727}) else{preconditionFailure("Original WWD BreakPlank")}
 var sceneNumber=0
 func scene()throws->ClawNativeScene{
  sceneNumber += 1;print("Plank comparison scene \(sceneNumber) setup")
  let value=ClawNativeScene(player:try ClawNativePlayer(world:level.world,assets:assets),clock:{1000})
  try value.loadRecoveredObjects(world:level.world,root:root);require(value.fault==0,"Scene setup");value.objectConnections!.recordsTrace=true;return value
 }
 func attach(_ runtime:ClawNativeScene)->UInt32{
  let before=body(runtime).tokens
  let actionPlane=level.world.planes.firstIndex(where:{$0.flags & 1 != 0})!
  let plane=runtime.camera!.planeTokens[actionPlane]
  print("Plank attach WWD id=\(record.id) xy=\(record.x),\(record.y) image=\(record.imageSet) plane=\(String(plane,radix:16)) sceneFaultBefore=\(runtime.fault)")
  let result=runtime.loadGridObject(record,world:world,plane:plane)
  require(result==record.encodedRecord.count && runtime.fault==0,"Plank attachment result=\(result)/\(record.encodedRecord.count) sceneFault=\(runtime.fault) unresolved=\(runtime.unresolvedDependencies) adapterTokens=\(body(runtime).tokens) bridgeOwners=\(runtime.objectConnections!.ownedActors) WWD=\(record.id) xy=\(record.x),\(record.y) image=\(record.imageSet) hostFault=\(String(describing:runtime.objectConnections!.host.fault)) loadingFailure=\(String(describing:runtime.objectLoadingFailure))")
  let added=body(runtime).tokens.subtracting(before);require(added.count==1,"One scene owner");return added.first!
 }
 func dispatch(_ runtime:ClawNativeScene,_ actor:UInt32,_ command:UInt32,_ callback:UInt32=0x40f7b0){
  put(runtime,word(runtime,actor+0x6c)+0x1c,command)
  var timing=ClawPlayerDeathCommandGlobals();runtime.captureDeathTiming(&timing);timing.animation.deltaMilliseconds=17;runtime.publishDeathTiming(timing)
  var call=ClawSceneActorCall();call.function=callback;call.argumentCount=1;call.arguments.0=actor
  let host=runtime.actorHost;_=host.call!(host.context,call)
 }
 func destroy(_ runtime:ClawNativeScene,_ actor:UInt32){
  print("Plank remove spatial residency for actor \(String(actor,radix:16))")
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
  // Scene update owns list unlinking and invokes each actor's real destructor.
  // Suppress unrelated callbacks for this teardown-only frame with the native
  // one-frame countdown. Parent destruction is not recursive in the original.
  let adapter=body(runtime)
  let ownedActors=adapter.memory!.sceneObjectPointers.filter{adapter.memory!.ownsObjectAllocation($0,count:0x1b4)}
  for current in runtime.actorTokens {put(runtime,word(runtime,current+0x6c)+0x24,1)}
  for current in ownedActors {put(runtime,current+8,word(runtime,current+8)|0x10000)}
  require(runtime.actorFrame(container:runtime.containerToken,refresh:0),"Scene child teardown")
  var destruction=ClawSceneActorCall();destruction.function=0x4c9be0;destruction.receiver=actor
  destruction.argumentCount=1;destruction.arguments.0=1
  let destructionHost=runtime.actorHost;_=destructionHost.call!(destructionHost.context,destruction)
  require(runtime.fault==0,"Scene parent teardown")
 }
 let runtime=try scene()
 var inputs:[[String:Any]]=[],outputs:[[String:Any]]=[],controls:[String:Bool]=[:]
 var retiredHelper:UInt32=0,firstActor:UInt32=0,positiveFaults:UInt32=0
 var positiveUnresolved:Set<UInt32>=[]
 for iteration in 0..<2{
  print("Plank positive profile \(iteration)")
  let actor=attach(runtime),state=word(runtime,actor+0x6c),adapter=body(runtime),bridge=runtime.objectConnections!
  if iteration==0{firstActor=actor};let initial=graph(runtime.heap)
  var allocations:[[String:UInt32]]=[],bindings:[[String:Any]]=[],services:[[Any]]=[],listOperations:[[String:Any]]=[],allCalls:[ClawCall]=[],childStep=false
  let dependency=bridge.host.dependency,observer=bridge.host.observer
  bridge.host.observer={hostCall in
   observer?(hostCall);allCalls.append(hostCall)
   if childStep && hostCall.function==0x4f6286,let key=text(bridge.host,hostCall.arguments.0),
      let binding=bindings.first(where:{($0["receiver"] as? UInt32)==hostCall.receiver && ($0["name"] as? String)==key}),
      let token=binding["token"] as? UInt32 {services.append(["registry",hostCall.receiver,key,token])}
  }
  bridge.host.dependency={host,call in
   let key=call.function==0x4f6286 ? text(host,call.arguments.0):nil,value=dependency?(host,call)
   if call.function==0x4f6286,let key,let pointer=host.bytes(call.arguments.1,count:4){
    let token=UnsafeRawPointer(pointer).loadUnaligned(as:UInt32.self).littleEndian
    services.append(["registry",call.receiver,key,token])
    if !bindings.contains(where:{($0["receiver"] as? UInt32)==call.receiver && ($0["name"] as? String)==key}){bindings.append(["receiver":call.receiver,"name":key,"token":token])}
   }
   if [UInt32(0x4f51c5),0x4f572a].contains(call.function),let value{
    let arguments=call.argumentCount==1 ? [call.arguments.0]:[call.arguments.0,call.arguments.1]
    listOperations.append(["function":call.function,"receiver":call.receiver,"arguments":arguments,"result":value])
    services.append(["list",call.function,call.receiver,arguments,value])
   }
   return value
  }
  adapter.memory!.afterService={function,args,value in if function==0x4a48e0{allocations.append(["token":value,"count":args[0]]);services.append(["malloc",value,args[0]])}}
  var inputSteps:[[String:Any]]=[],outputSteps:[[String:Any]]=[],home:UInt32=0
  func step(_ target:UInt32,_ command:UInt32,_ callback:UInt32){
   childStep=callback==0x488e30
   services=[];let before=allCalls.count
   let clocks:[[String:Any]]=[["address":UInt32(0x5430c4),"hex":"11000000"],["address":UInt32(0x537210),"hex":withUnsafeBytes(of:runtime.gameTime.littleEndian){Data($0).map{String(format:"%02x",$0)}.joined()}]]
   print("Plank profile \(iteration) command \(command)")
   dispatch(runtime,target,command,callback)
   require(runtime.fault==0 && bridge.host.fault==nil,"Plank callback \(command): \(String(describing:bridge.host.fault))")
   let helper=word(runtime,state+0x18),hit=word(runtime,actor+0x70),attack=word(runtime,actor+0x78)
   require(adapter.memory!.ownsObjectAllocation(helper,count:0xa4) && hit != 0 && attack != 0,"Physical ledger and real bindings")
   let spans:[(UInt32,UInt32)]=[(actor,0x1b4),(state,0x174)] + allocations.map{($0["token"]!,$0["count"]!)} + [(0x537668,44),(0x537698,36),(0x534a10,36),(0x53c2c8,36),(0x537210,4),(0x5430c4,4)]
   inputSteps.append(["callback":callback,"actor":target,"command":command,"inputGlobals":clocks,"spans":spans.map{["address":$0.0,"count":$0.1]}])
   outputSteps.append(["callback":callback,"actor":target,"command":command,"calls":allCalls.dropFirst(before).filter{observed.contains($0.function)}.map{[$0.function,$0.receiver]},"services":services,"spans":spans.map{segment(runtime.heap,$0.0,$0.1)}])
  }
  for command:UInt32 in [0,1000,29,30] {
   step(actor,command,0x40f7b0)
   if command==0{home=word(runtime,state+0x1c)}
  }
  require(![UInt32(0),1000,29,30].contains(home),"Original initializer selects a lifecycle state")
  step(actor,home,0x40f7b0)
  let childActors=allocations.filter{$0["count"]==0x1b4}.map{$0["token"]!}
  for child in childActors {step(child,word(runtime,word(runtime,child+0x6c)+0x1c),0x488e30)}
  bridge.host.dependency=dependency;bridge.host.observer=observer;adapter.memory!.afterService=nil
  inputs.append(["name":"WWD-\(record.id)-\(iteration)","actor":actor,"state":state,"segments":initial,"allocations":allocations,"resourceBindings":bindings,"listOperations":listOperations,"childStates":allocations.enumerated().compactMap{index,row in row["count"]==0x1b4 ? allocations[index+1]["token"]:nil},"steps":inputSteps]);outputs.append(["name":"WWD-\(record.id)-\(iteration)","steps":outputSteps])
  try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("plank-partial-input.json"))
  try JSONSerialization.data(withJSONObject:["profiles":outputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("plank-partial-output.json"))
  positiveFaults |= runtime.fault;positiveUnresolved.formUnion(runtime.unresolvedDependencies)
  require(positiveFaults==0 && positiveUnresolved.isEmpty,"Positive callback completion and dependency closure")
  let helper=word(runtime,state+0x18)
  if iteration==0{
   retiredHelper=helper;destroy(runtime,actor)
   positiveFaults |= runtime.fault;positiveUnresolved.formUnion(runtime.unresolvedDependencies)
   controls["scene_destruction_retires_all_allocations"]=runtime.fault==0 && !adapter.tokens.contains(actor) && ([actor,state]+allocations.map{$0["token"]!}).allSatisfy{runtime.heap.lookupBytes($0,count:1)==nil} && !adapter.memory!.ownsObjectAllocation(helper,count:0xa4)
  }else{
   controls["same_scene_recreates_actor_and_helper"]=actor != firstActor && helper != retiredHelper && adapter.tokens.contains(actor)
   put(runtime,state+0x18,retiredHelper);dispatch(runtime,actor,1000)
   controls["retired_helper_rejected"]=bridge.host.fault != nil && runtime.fault != 0
  }
 }
 let missing=try scene(),missingActor=attach(missing);missing.objectConnections!.host.dependency=nil;dispatch(missing,missingActor,0)
 controls["missing_resource_service_rejected"]=missing.objectConnections!.host.fault?.diagnostic == .missingDependency && missing.objectConnections!.host.fault?.address==0x4f6286 && missing.fault != 0
 let stale=try scene(),staleActor=attach(stale),saved=Data(bytes:stale.heap.lookupBytes(staleActor,count:0x1b4)!,count:0x1b4)
 stale.heap.free(staleActor);saved.withUnsafeBytes{stale.heap.storeBytes(token:staleActor,count:0x1b4).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0x1b4)};dispatch(stale,staleActor,0)
 controls["replacement_actor_rejected"]=stale.objectConnections!.host.fault != nil && stale.objectConnections!.calls.isEmpty
 let staleLogic=try scene(),staleLogicActor=attach(staleLogic),logicToken=word(staleLogic,staleLogicActor+0x6c)
 let logicBytes=Data(bytes:staleLogic.heap.lookupBytes(logicToken,count:0x174)!,count:0x174)
 staleLogic.heap.free(logicToken);logicBytes.withUnsafeBytes{staleLogic.heap.storeBytes(token:logicToken,count:0x174).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0x174)};dispatch(staleLogic,staleLogicActor,0)
 controls["replacement_logic_rejected"]=staleLogic.objectConnections!.host.fault != nil && staleLogic.objectConnections!.calls.isEmpty
 let staleHelper=try scene(),staleHelperActor=attach(staleHelper);dispatch(staleHelper,staleHelperActor,0);require(staleHelper.fault==0,"Replacement helper control initialization")
 let helperToken=word(staleHelper,word(staleHelper,staleHelperActor+0x6c)+0x18),helperBytes=Data(bytes:staleHelper.heap.lookupBytes(helperToken,count:0xa4)!,count:0xa4),helperCalls=staleHelper.objectConnections!.calls.count
 staleHelper.heap.free(helperToken);helperBytes.withUnsafeBytes{staleHelper.heap.storeBytes(token:helperToken,count:0xa4).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0xa4)};dispatch(staleHelper,staleHelperActor,1000)
 controls["replacement_helper_rejected"]=staleHelper.objectConnections!.host.fault != nil && staleHelper.objectConnections!.calls.count==helperCalls && !body(staleHelper).memory!.ownsObjectAllocation(helperToken,count:0xa4)
 let foreign=try scene(),foreignActor=attach(foreign);dispatch(foreign,foreignActor,0);require(foreign.fault==0,"Foreign control initialization")
 let foreignState=word(foreign,foreignActor+0x6c),realHelper=word(foreign,foreignState+0x18),copy=Data(bytes:foreign.heap.lookupBytes(realHelper,count:0xa4)!,count:0xa4),fake=foreign.heap.allocate(bytes:0xa4)
 copy.withUnsafeBytes{foreign.heap.lookupBytes(fake,count:0xa4)!.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0xa4)};put(foreign,foreignState+0x18,fake);dispatch(foreign,foreignActor,1000)
 controls["foreign_helper_rejected"]=foreign.objectConnections!.host.fault != nil && foreign.heap.lookupBytes(fake,count:0xa4) != nil
 let outside=try scene(),outsideActor=attach(outside)
 var forged=ClawCall();forged.function=0x4f6286;forged.receiver=0x62000010;forged.argumentCount=2;forged.arguments.0=0x522bd4;forged.arguments.1=outsideActor
 controls["service_outside_callback_rejected"]=body(outside).service(forged)==nil
 require(controls.values.allSatisfy{$0},"Plank ownership controls: \(controls)")
 try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("plank-native-input.json"))
 try JSONSerialization.data(withJSONObject:["profiles":outputs,"controls":controls,"trace":runtime.objectConnections!.trace,"faults":positiveFaults,"unresolvedDependencies":positiveUnresolved.sorted()],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("plank-native-output.json"))
}
