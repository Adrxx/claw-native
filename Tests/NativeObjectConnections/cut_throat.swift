import Foundation
private let observed:Set<UInt32>=[0x4f63ec,0x437a90,0x44c000,0x4dca10,0x403b40,0x405000,0x4c7fa0,0x4c8060,0x4c7970,0x4062e0,0x4061b0,0x4c8220,0x4f6439,0x4dc180,0x4db620,0x4dbe10,0x4dbd60,0x4dbcd0,0x420fc0,0x4dbd20,0x4dc870,0x44cfd0,0x4c96b0,0x44d000,0x438100,0x44d3c0,0x4c82a0]
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
private func body(_ scene:ClawNativeScene)->ClawNativeCutThroat{scene.objectConnections!.adapter("cut_throat") as! ClawNativeCutThroat}
private func text(_ host:ClawNativeCanonicalHost,_ token:UInt32)->String?{
 var value:[UInt8]=[]
 for offset:UInt32 in 0..<256{guard let bytes=host.bytes(token+offset,count:1) else{return nil};if bytes[0]==0{return String(bytes:value,encoding:.ascii)};value.append(bytes[0])};return nil
}
private func word(_ scene:ClawNativeScene,_ token:UInt32)->UInt32{scene.heap.lookup(token,words:1)!.pointee}
private func put(_ scene:ClawNativeScene,_ token:UInt32,_ value:UInt32){scene.heap.lookup(token,words:1)!.pointee=value}
func runConnection(_ suppliedDirectory:URL)throws{
 // This join compares the authenticated v1.0 callback, not the v1.3 overlay.
 setenv("CLAW_LIVES_BOSS_PROFILE","claw-v1.0",1)
 let directory=suppliedDirectory.standardizedFileURL
 let root=directory.appendingPathComponent("resources").standardizedFileURL,level=try ClawLevelScene(root:directory.appendingPathComponent("resources").standardizedFileURL),assets=try ClawPlayerAssets(root:directory.appendingPathComponent("resources").standardizedFileURL)
 let world=try ClawWorld(data:Data(contentsOf:directory.appendingPathComponent("WORLD3.WWD")))
 let actionPlane=level.world.planes.first(where:{$0.flags & 1 != 0})!
 guard let record=world.planes.flatMap(\.objects).first(where:{$0.logic=="CutThroat" && $0.x >= 0 && $0.y >= 0 && Int($0.x) < Int(actionPlane.width * actionPlane.tileWidth) && Int($0.y) < Int(actionPlane.height * actionPlane.tileHeight)}) else{preconditionFailure("Original WWD CutThroat within the scene plane bounds")}
 var sceneNumber=0
 func scene()throws->ClawNativeScene{
  sceneNumber += 1;print("CutThroat comparison scene \(sceneNumber) setup")
  let value=ClawNativeScene(player:try ClawNativePlayer(world:level.world,assets:assets),clock:{1000})
  try value.loadRecoveredObjects(world:level.world,root:root);require(value.fault==0,"Scene setup");value.objectConnections!.recordsTrace=true;return value
 }
 func attach(_ runtime:ClawNativeScene)->UInt32{
  let before=body(runtime).tokens
  let actionPlane=level.world.planes.firstIndex(where:{$0.flags & 1 != 0})!
  let plane=runtime.camera!.planeTokens[actionPlane]
  print("CutThroat attach WWD id=\(record.id) xy=\(record.x),\(record.y) image=\(record.imageSet) plane=\(String(plane,radix:16)) sceneFaultBefore=\(runtime.fault)")
  let result=runtime.loadGridObject(record,world:world,plane:plane)
  require(result==record.encodedRecord.count && runtime.fault==0,"CutThroat attachment result=\(result)/\(record.encodedRecord.count) sceneFault=\(runtime.fault) unresolved=\(runtime.unresolvedDependencies) adapterTokens=\(body(runtime).tokens) bridgeOwners=\(runtime.objectConnections!.ownedActors) WWD=\(record.id) xy=\(record.x),\(record.y) image=\(record.imageSet) hostFault=\(String(describing:runtime.objectConnections!.host.fault)) loadingFailure=\(String(describing:runtime.objectLoadingFailure))")
  let added=body(runtime).tokens.subtracting(before);require(added.count==1,"One scene owner");return added.first!
 }
 func dispatch(_ runtime:ClawNativeScene,_ actor:UInt32,_ command:UInt32){
  put(runtime,word(runtime,actor+0x6c)+0x1c,command)
  var timing=ClawPlayerDeathCommandGlobals();runtime.captureDeathTiming(&timing);timing.animation.deltaMilliseconds=17;runtime.publishDeathTiming(timing)
  var call=ClawSceneActorCall();call.function=0x4379d0;call.argumentCount=1;call.arguments.0=actor
  let host=runtime.actorHost;_=host.call!(host.context,call)
 }
 func destroy(_ runtime:ClawNativeScene,_ actor:UInt32){
  print("CutThroat remove spatial residency for actor \(String(actor,radix:16))")
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
  print("CutThroat destroy actor \(String(actor,radix:16))")
  var call=ClawSceneActorCall();call.function=0x4c9be0;call.receiver=actor;call.argumentCount=1;call.arguments.0=1
  let host=runtime.actorHost;_=host.call!(host.context,call)
 }
 let runtime=try scene()
 var inputs:[[String:Any]]=[],outputs:[[String:Any]]=[],controls:[String:Bool]=[:]
 var retiredHelper:UInt32=0,firstActor:UInt32=0,positiveFaults:UInt32=0
 var positiveUnresolved:Set<UInt32>=[]
 for iteration in 0..<2{
  print("CutThroat positive profile \(iteration)")
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
   } else if call.function==0x4a3050,let value { services.append(["rand",value]);randomValues.append(value) }
   else if call.function==0x711100 { services.append(["rectangle",call.arguments.0,call.arguments.1,call.arguments.2,call.arguments.3,call.arguments.4]) }
   else if call.function==0x711104 { services.append(["empty-rectangle",call.arguments.0]) }
   return value
  }
  adapter.memory!.afterService={function,args,value in if function==0x4a48e0{allocations.append(["token":value,"count":args[0]]);services.append(["malloc",value,args[0]])}}
  var inputSteps:[[String:Any]]=[],outputSteps:[[String:Any]]=[],home:UInt32=0
  for index in 0..<5{
   let command:UInt32=index==0 ? 0:index==1 ? 1000:index==2 ? 29:index==3 ? 30:home
   services=[];let before=bridge.calls.count
   var clocks:[[String:Any]]=[]
   let clockInputs:[(UInt32,UInt32)]=[(0x5430c4,17),(0x537210,runtime.gameTime)]
   for (address,value) in clockInputs where runtime.heap.lookup(address,words:1) != nil {
    clocks.append(["address":address,"hex":withUnsafeBytes(of:value.littleEndian){Data($0).map{String(format:"%02x",$0)}.joined()}])
   }
   print("CutThroat profile \(iteration) command \(command)")
   dispatch(runtime,actor,command)
   if runtime.fault != 0 || bridge.host.fault != nil {
    try JSONSerialization.data(withJSONObject:["iteration":iteration,"command":command,"sceneFault":runtime.fault,"hostFault":String(describing:bridge.host.fault),"calls":bridge.calls.map{[$0.function,$0.receiver]},"trace":bridge.trace,"segments":initial,"allocations":allocations,"services":services],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("cut-throat-fault.json"))
   }
   require(runtime.fault==0 && bridge.host.fault==nil,"CutThroat callback \(command): \(String(describing:bridge.host.fault))")
   if index==0{home=word(runtime,state+0x1c);require(home != 0 && home != 1000 && home != 29 && home != 30,"Constructor elects real default lifecycle command")}
   let helper=word(runtime,state+0x18),hit=word(runtime,actor+0x70),attack=word(runtime,actor+0x78)
   require(adapter.memory!.ownsObjectAllocation(helper,count:0x480) && hit != 0 && attack != 0,"Physical ledger and real bindings")
   var spans:[(UInt32,UInt32)]=[(actor,0x1b4),(state,0x174)]
   spans += allocations.map{($0["token"]!,$0["count"]!)}
   spans += adapter.evidenceSpans.filter{(address,count) in !Set<UInt32>([0x546d5c,0x546cdc,0x5469e8,0x546cd4]).contains(address) && runtime.heap.lookupBytes(address,count:count) != nil}
   var seen:Set<UInt32>=[];spans=spans.filter{seen.insert($0.0).inserted}
   inputSteps.append(["command":command,"inputGlobals":clocks,"spans":spans.map{["address":$0.0,"count":$0.1]}])
   outputSteps.append(["command":command,"calls":bridge.calls.dropFirst(before).filter{observed.contains($0.function)}.map{[$0.function,$0.receiver]},"services":services,"spans":spans.map{segment(runtime.heap,$0.0,$0.1)}])
   try JSONSerialization.data(withJSONObject:["name":"WWD-\(record.id)-\(iteration)","actor":actor,"state":state,"segments":initial,"allocations":allocations,"resourceBindings":bindings,"randomValues":randomValues,"steps":inputSteps],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("cut-throat-active-input.json"))
   try JSONSerialization.data(withJSONObject:["name":"WWD-\(record.id)-\(iteration)","steps":outputSteps],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("cut-throat-active-output.json"))
  }
  bridge.host.dependency=dependency;adapter.memory!.afterService=nil
  inputs.append(["name":"WWD-\(record.id)-\(iteration)","actor":actor,"state":state,"segments":initial,"allocations":allocations,"resourceBindings":bindings,"randomValues":randomValues,"steps":inputSteps]);outputs.append(["name":"WWD-\(record.id)-\(iteration)","steps":outputSteps])
  try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("cut-throat-partial-input.json"))
  try JSONSerialization.data(withJSONObject:["profiles":outputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("cut-throat-partial-output.json"))
  positiveFaults |= runtime.fault;positiveUnresolved.formUnion(runtime.unresolvedDependencies)
  require(positiveFaults==0 && positiveUnresolved.isEmpty,"Positive callback completion and dependency closure")
  let helper=word(runtime,state+0x18),hit=word(runtime,actor+0x70),attack=word(runtime,actor+0x78)
  if iteration==0{
   retiredHelper=helper;destroy(runtime,actor)
   positiveFaults |= runtime.fault;positiveUnresolved.formUnion(runtime.unresolvedDependencies)
   controls["scene_destruction_retires_all_allocations"]=runtime.fault==0 && !adapter.tokens.contains(actor) && [actor,state,helper,hit,attack].allSatisfy{runtime.heap.lookupBytes($0,count:1)==nil} && !adapter.memory!.ownsObjectAllocation(helper,count:0x480)
  }else{
   controls["same_scene_recreates_actor_and_helper"]=actor != firstActor && helper != retiredHelper && adapter.tokens.contains(actor)
   put(runtime,state+0x18,retiredHelper);dispatch(runtime,actor,1000)
   controls["retired_helper_rejected"]=bridge.host.fault != nil && runtime.fault != 0
  }
 }
 let missing=try scene(),missingActor=attach(missing),missingDependency=missing.objectConnections!.host.dependency
 missing.objectConnections!.host.dependency={host,call in call.function==0x4f6286 ? nil:missingDependency?(host,call)};dispatch(missing,missingActor,0)
 controls["missing_resource_service_rejected"]=missing.objectConnections!.host.fault?.diagnostic == .missingDependency && missing.objectConnections!.host.fault?.address==0x4f6286 && missing.fault != 0
 let stale=try scene(),staleActor=attach(stale),saved=Data(bytes:stale.heap.lookupBytes(staleActor,count:0x1b4)!,count:0x1b4)
 stale.heap.free(staleActor);saved.withUnsafeBytes{stale.heap.storeBytes(token:staleActor,count:0x1b4).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0x1b4)};dispatch(stale,staleActor,0)
 controls["replacement_actor_rejected"]=stale.objectConnections!.host.fault != nil && stale.objectConnections!.calls.isEmpty
 let foreign=try scene(),foreignActor=attach(foreign);dispatch(foreign,foreignActor,0);require(foreign.fault==0,"Foreign control initialization")
 let foreignState=word(foreign,foreignActor+0x6c),realHelper=word(foreign,foreignState+0x18),copy=Data(bytes:foreign.heap.lookupBytes(realHelper,count:0x480)!,count:0x480),fake=foreign.heap.allocate(bytes:0x480)
 copy.withUnsafeBytes{foreign.heap.lookupBytes(fake,count:0x480)!.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0x480)};put(foreign,foreignState+0x18,fake);dispatch(foreign,foreignActor,1000)
 controls["foreign_helper_rejected"]=foreign.objectConnections!.host.fault != nil && foreign.heap.lookupBytes(fake,count:0x480) != nil
 let outside=try scene(),outsideActor=attach(outside)
 var forged=ClawCall();forged.function=0x4f6286;forged.receiver=0x62000010;forged.argumentCount=2;forged.arguments.0=0x522d54;forged.arguments.1=outsideActor
 controls["service_outside_callback_rejected"]=body(outside).service(forged)==nil
 require(controls.values.allSatisfy{$0},"CutThroat ownership controls: \(controls)")
 try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("cut-throat-native-input.json"))
 try JSONSerialization.data(withJSONObject:["profiles":outputs,"controls":controls,"trace":runtime.objectConnections!.trace,"faults":positiveFaults,"unresolvedDependencies":positiveUnresolved.sorted()],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("cut-throat-native-output.json"))
}
