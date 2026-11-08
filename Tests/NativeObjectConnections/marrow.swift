import Foundation
private let observed:Set<UInt32>=[0x4f63ec,0x458d40,0x40e0d0,0x44c000,0x40e1b0,0x40e5b0,0x4c96b0,0x4dc870,0x459470,0x44d000,0x4587a0,0x44d3c0,0x459440,0x43dfa0,0x403b40,0x4cbb60,0x4c7fa0,0x4c8060,0x4c8160,0x4c7970,0x4062e0,0x4061b0,0x4c8220,0x4f6439,0x4dc180,0x4db620,0x4dbe10,0x4dbd60,0x4dbcd0,0x420fc0,0x4dbd20,0x459c80,0x40e560,0x40abb0,0x40ab80,0x4cd800,0x40abf0]
private func require(_ value:Bool,_ message:String){precondition(value,message)}
private func segment(_ heap:ClawTokenHeap,_ address:UInt32,_ count:UInt32)->[String:Any]{
 guard let bytes=heap.lookupBytes(address,count:count) else{preconditionFailure("Missing span \(String(address,radix:16))/\(count)")}
 let digits=Array("0123456789abcdef".utf8)
 var hex=[UInt8]();hex.reserveCapacity(Int(count)*2)
 for byte in UnsafeBufferPointer(start:bytes,count:Int(count)) {hex.append(digits[Int(byte>>4)]);hex.append(digits[Int(byte & 15)])}
 return ["address":address,"hex":String(decoding:hex,as:UTF8.self)]
}
private func graph(_ heap:ClawTokenHeap,excluding:Set<UInt32>=[])->[[String:Any]]{heap.debugAllocationBases.filter{!excluding.contains($0)}.map{token in
 var low:UInt32=1,high:UInt32=4<<20
 while low<high{let middle=low+(high-low+1)/2;if heap.lookupBytes(token,count:middle) != nil{low=middle}else{high=middle-1}}
 return segment(heap,token,low)
}}
private func body(_ scene:ClawNativeScene)->ClawNativeMarrow{scene.objectConnections!.adapter("marrow") as! ClawNativeMarrow}
private func text(_ host:ClawNativeCanonicalHost,_ token:UInt32)->String?{
 var value:[UInt8]=[]
 for offset:UInt32 in 0..<256{guard let bytes=host.bytes(token+offset,count:1) else{return nil};if bytes[0]==0{return String(bytes:value,encoding:.ascii)};value.append(bytes[0])};return nil
}
private func word(_ scene:ClawNativeScene,_ token:UInt32)->UInt32{scene.heap.lookup(token,words:1)!.pointee}
private func put(_ scene:ClawNativeScene,_ token:UInt32,_ value:UInt32){scene.heap.lookup(token,words:1)!.pointee=value}
func runConnection(_ suppliedDirectory:URL)throws{
 let directory=suppliedDirectory.standardizedFileURL
 let root=directory.appendingPathComponent("resources").standardizedFileURL,level=try ClawLevelScene(root:directory.appendingPathComponent("resources").standardizedFileURL,level:10),assets=try ClawPlayerAssets(root:directory.appendingPathComponent("resources").standardizedFileURL,level:10)
 let world=try ClawWorld(data:Data(contentsOf:directory.appendingPathComponent("WORLD10.WWD")))
 let scenePlane=level.world.planes.first(where:{$0.flags & 1 != 0})!
 guard let record=world.planes.flatMap(\.objects).first(where:{$0.logic=="Marrow" && $0.x>0 && $0.y>0 && $0.x<scenePlane.width*scenePlane.tileWidth && $0.y<scenePlane.height*scenePlane.tileHeight}) else{preconditionFailure("Original WWD Marrow")}
 var sceneNumber=0
 func scene()throws->ClawNativeScene{
  sceneNumber += 1;print("Marrow comparison scene \(sceneNumber) setup")
  let value=ClawNativeScene(player:try ClawNativePlayer(world:level.world,assets:assets,enableAudioOutput:false),clock:{1000})
  try value.loadRecoveredObjects(world:level.world,root:root,level:10);require(value.fault==0,"Scene setup");value.objectConnections!.recordsTrace=true;return value
 }
 func attach(_ runtime:ClawNativeScene)->UInt32{
  let before=body(runtime).tokens
  let actionPlane=level.world.planes.firstIndex(where:{$0.flags & 1 != 0})!
  let plane=runtime.camera!.planeTokens[actionPlane]
  print("Marrow attach WWD id=\(record.id) xy=\(record.x),\(record.y) image=\(record.imageSet) plane=\(String(plane,radix:16)) sceneFaultBefore=\(runtime.fault)")
  let result=runtime.loadGridObject(record,world:world,plane:plane)
  require(result==record.encodedRecord.count && runtime.fault==0,"Marrow attachment result=\(result)/\(record.encodedRecord.count) sceneFault=\(runtime.fault) unresolved=\(runtime.unresolvedDependencies) adapterTokens=\(body(runtime).tokens) bridgeOwners=\(runtime.objectConnections!.ownedActors) WWD=\(record.id) xy=\(record.x),\(record.y) image=\(record.imageSet) hostFault=\(String(describing:runtime.objectConnections!.host.fault)) loadingFailure=\(String(describing:runtime.objectLoadingFailure))")
  let added=body(runtime).tokens.subtracting(before);require(added.count==1,"One scene owner");return added.first!
 }
 func dispatch(_ runtime:ClawNativeScene,_ actor:UInt32,_ command:UInt32){
  put(runtime,word(runtime,actor+0x6c)+0x1c,command)
  var timing=ClawPlayerDeathCommandGlobals();runtime.captureDeathTiming(&timing);timing.animation.deltaMilliseconds=0;runtime.publishDeathTiming(timing)
  var call=ClawSceneActorCall();call.function=0x458680;call.argumentCount=1;call.arguments.0=actor
  let host=runtime.actorHost;_=host.call!(host.context,call)
 }
 func destroy(_ runtime:ClawNativeScene,_ actor:UInt32){
  print("Marrow remove spatial residency for actor \(String(actor,radix:16))")
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
  print("Marrow destroy actor \(String(actor,radix:16))")
  var call=ClawSceneActorCall();call.function=0x4c9be0;call.receiver=actor;call.argumentCount=1;call.arguments.0=1
  let host=runtime.actorHost;_=host.call!(host.context,call)
 }
 let runtime=try scene()
 var inputs:[[String:Any]]=[],outputs:[[String:Any]]=[],controls:[String:Bool]=[:]
 var retiredHelper:UInt32=0,firstActor:UInt32=0,positiveFaults:UInt32=0
 var positiveUnresolved:Set<UInt32>=[]
 for iteration in 0..<2{
  print("Marrow positive profile \(iteration)")
  let actor=attach(runtime),state=word(runtime,actor+0x6c),adapter=body(runtime),bridge=runtime.objectConnections!
  if iteration==0{firstActor=actor};let initial=graph(runtime.heap)
  var allocations:[[String:UInt32]]=[],bindings:[[String:Any]]=[],services:[[Any]]=[]
  let dependency=bridge.host.dependency
  bridge.host.dependency={host,call in
   let key=call.function==0x4f6286 ? (clawOriginalResourceNames[call.arguments.0] ?? text(host,call.arguments.0)):nil,value=dependency?(host,call)
   if call.function==0x4f6286,let key,let pointer=host.bytes(call.arguments.1,count:4){
    let token=UnsafeRawPointer(pointer).loadUnaligned(as:UInt32.self).littleEndian
    services.append(["registry",call.receiver,key,token])
    if !bindings.contains(where:{($0["receiver"] as? UInt32)==call.receiver && ($0["name"] as? String)==key}){bindings.append(["receiver":call.receiver,"name":key,"token":token])}
   }
   if call.function==0x4a3050,let value { services.append(["rand",value]) }
   let slots:[UInt32]=[0x546d5c,0x546cdc,0x546cd4]
   if let slot=slots.first(where:{$0==call.function || runtime.heap.lookup($0,words:1)?[0]==call.function}) {
    let a=withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
    if slot==0x546d5c {services.append(["rectangle"]+a.map{$0 as Any})}
    if slot==0x546cdc {services.append(["empty-rectangle"]+a.map{$0 as Any})}
    if slot==0x546cd4,let value {services.append(["point-in-rectangle"]+a.map{$0 as Any}+[value])}
   }
   return value
  }
  adapter.memory!.afterService={function,args,value in if function==0x4a48e0{allocations.append(["token":value,"count":args[0]]);services.append(["malloc",value,args[0]])}}
  var inputSteps:[[String:Any]]=[],outputSteps:[[String:Any]]=[]
  let table=runtime.heap.lookup(0x537698,words:9)!
  let idle=(table[2]...table[3]).first { index in
   let token=word(runtime,table[4]+(index-table[2])*4)
   return text(bridge.host,token)=="LS_STARTUP"
  }!
  require(idle != 0 && ![UInt32(1000),29,30].contains(idle),"Real LS_STARTUP state index")
  for index in 0..<5{
   let command:UInt32=index==0 ? 0:index==1 ? 1000:index==2 ? 29:index==3 ? 30:idle
   services=[];let before=bridge.calls.count
   var inputs:[(UInt32,UInt32)]=[]
   if index==4 {
    runtime.publishGameTime(100)
    inputs=[(actor+0xcc,7)]
    for (address,value) in inputs {put(runtime,address,value)}
   }
   let clocks:[[String:Any]]=inputs.map{address,value in ["address":address,"hex":withUnsafeBytes(of:value.littleEndian){Data($0).map{String(format:"%02x",$0)}.joined()}]} + [["address":UInt32(0x5430c4),"hex":"00000000"],["address":UInt32(0x537210),"hex":withUnsafeBytes(of:runtime.gameTime.littleEndian){Data($0).map{String(format:"%02x",$0)}.joined()}]]
   print("Marrow profile \(iteration) command \(command)")
   dispatch(runtime,actor,command)
   if runtime.fault != 0 || bridge.host.fault != nil {
    let calls:[[String:Any]]=bridge.calls.dropFirst(before).map{call in
     let arguments=withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
     return ["function":call.function,"receiver":call.receiver,"arguments":arguments]
    }
    let recent=calls.suffix(12)
    print("Marrow failed call tail: \(Array(recent))")
    let failure:[String:Any]=["command":command,"actor":actor,"state":state,"sceneFault":runtime.fault,
      "hostFault":String(describing:bridge.host.fault),"unresolvedDependencies":runtime.unresolvedDependencies.sorted(),
      "initialSegments":initial,"calls":calls,"lastCalls":Array(recent),"services":services]
    try JSONSerialization.data(withJSONObject:failure,options:[.prettyPrinted,.sortedKeys])
      .write(to:directory.appendingPathComponent("marrow-native-failure.json"))
   }
   require(runtime.fault==0 && bridge.host.fault==nil,"Marrow callback \(command): \(String(describing:bridge.host.fault))")
   
   let helper=word(runtime,state+0x18),hit=word(runtime,actor+0x70),attack=word(runtime,actor+0x78)
   require(adapter.memory!.ownsObjectAllocation(helper,count:0x4d8) && [hit,attack].allSatisfy{adapter.memory!.ownsObjectAllocation($0,count:0x174)},"Physical ledger and real bindings")
   let spans:[(UInt32,UInt32)]=[(actor,0x1b4),(state,0x174),(hit,0x174),(attack,0x174),(helper,0x4d8),(0x537668,44),(0x537698,36),(0x537878,36),(0x537af0,40),(0x537210,4),(0x5430c4,4),(0x53c9ac,8)]
   inputSteps.append(["command":command,"random":services.filter{($0.first as? String)=="rand"}.map{$0[1]},"inputGlobals":clocks,"spans":spans.map{["address":$0.0,"count":$0.1]}])
   outputSteps.append(["command":command,"calls":bridge.calls.dropFirst(before).filter{observed.contains($0.function)}.map{[$0.function,$0.receiver]},"services":services,"spans":spans.map{segment(runtime.heap,$0.0,$0.1)}])
  }
  bridge.host.dependency=dependency;adapter.memory!.afterService=nil
  let bases=Set(initial.map{($0["address"] as! UInt32)})
  let supplemental=graph(runtime.heap,excluding:bases.union(allocations.map{$0["token"]!}))
  inputs.append(["name":"WWD-\(record.id)-\(iteration)","actor":actor,"state":state,"segments":initial+supplemental,"allocations":allocations,"resourceBindings":bindings,"steps":inputSteps,"retire":iteration==0]);outputs.append(["name":"WWD-\(record.id)-\(iteration)","steps":outputSteps])
  try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("marrow-partial-input.json"))
  try JSONSerialization.data(withJSONObject:["profiles":outputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("marrow-partial-output.json"))
  positiveFaults |= runtime.fault;positiveUnresolved.formUnion(runtime.unresolvedDependencies)
  require(positiveFaults==0 && positiveUnresolved.isEmpty,"Positive callback completion and dependency closure")
  let helper=word(runtime,state+0x18),hit=word(runtime,actor+0x70),attack=word(runtime,actor+0x78)
  if iteration==0{
   retiredHelper=helper
   let priorObserver=bridge.host.observer
   var retirementBytes:String?
   var secondaryRetirement:[[String:Any]]=[]
   bridge.host.observer={call in
    priorObserver?(call)
    if call.function==0x4f6428 && call.arguments.0==helper {
     retirementBytes=segment(runtime.heap,helper,0x4d8)["hex"] as? String
    }
    if call.function==0x4f6428 && [hit,attack].contains(call.arguments.0) {
     secondaryRetirement.append(segment(runtime.heap,call.arguments.0,0x174))
    }
   }
   destroy(runtime,actor)
   bridge.host.observer=priorObserver
   require(retirementBytes != nil,"Real destructor reaches physical release: scene=\(runtime.fault) host=\(String(describing:bridge.host.fault)) unresolved=\(runtime.unresolvedDependencies) trace=\(bridge.trace.suffix(8)) helperLive=\(adapter.memory!.ownsObjectAllocation(helper,count:0x4d8))")
   outputs[outputs.count-1]["retirement"]=["helper":helper,"hex":retirementBytes!,"secondary":secondaryRetirement]
   positiveFaults |= runtime.fault;positiveUnresolved.formUnion(runtime.unresolvedDependencies)
   controls["scene_destruction_retires_all_allocations"]=runtime.fault==0 && !adapter.tokens.contains(actor) && [actor,state,helper,hit,attack].allSatisfy{runtime.heap.lookupBytes($0,count:1)==nil} && !adapter.memory!.ownsObjectAllocation(helper,count:0x4d8)
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
 let foreign=try scene(),foreignActor=attach(foreign);dispatch(foreign,foreignActor,0);require(foreign.fault==0,"Foreign control initialization")
 let foreignState=word(foreign,foreignActor+0x6c),realHelper=word(foreign,foreignState+0x18),copy=Data(bytes:foreign.heap.lookupBytes(realHelper,count:0x4d8)!,count:0x4d8),fake=foreign.heap.allocate(bytes:0x4d8)
 copy.withUnsafeBytes{foreign.heap.lookupBytes(fake,count:0x4d8)!.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0x4d8)};put(foreign,foreignState+0x18,fake);dispatch(foreign,foreignActor,1000)
 controls["foreign_helper_rejected"]=foreign.objectConnections!.host.fault != nil && foreign.heap.lookupBytes(fake,count:0x4d8) != nil
 // Exercise primary-state teardown at the two scene entry points, before
 // their original bodies clear the callback and helper fields.
 for function:UInt32 in [0x4c80e0,0x4c80c0] {
  let direct=try scene(),actor=attach(direct);dispatch(direct,actor,0)
  require(direct.fault==0,"Direct logic teardown setup")
  let state=word(direct,actor+0x6c),helper=word(direct,state+0x18)
  var call=ClawSceneActorCall();call.function=function;call.receiver=state
  if function==0x4c80c0 {call.argumentCount=1;call.arguments.0=1}
  let host=direct.actorHost;_=host.call!(host.context,call)
  let stateRetired=function==0x4c80c0 ? direct.heap.lookupBytes(state,count:1)==nil :
    word(direct,state+0x18)==0 && word(direct,state+0x10)==0
  controls["primary_logic_\(String(function,radix:16))_retires_helper"]=direct.fault==0 && direct.objectConnections!.host.fault==nil &&
    stateRetired && direct.heap.lookupBytes(helper,count:1)==nil && !body(direct).memory!.ownsObjectAllocation(helper,count:0x4d8) && direct.heap.lookupBytes(actor,count:0x1b4) != nil
 }
 let staleLogic=try scene(),logicActor=attach(staleLogic);dispatch(staleLogic,logicActor,0)
 require(staleLogic.fault==0,"Stale logic teardown setup")
 let logicToken=word(staleLogic,logicActor+0x6c),logicHelper=word(staleLogic,logicToken+0x18)
 let logicBytes=Data(bytes:staleLogic.heap.lookupBytes(logicToken,count:0x174)!,count:0x174)
 staleLogic.heap.free(logicToken)
 logicBytes.withUnsafeBytes{staleLogic.heap.storeBytes(token:logicToken,count:0x174).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0x174)}
 var logicCall=ClawSceneActorCall();logicCall.function=0x4c80e0;logicCall.receiver=logicToken
 let logicHost=staleLogic.actorHost;_=logicHost.call!(logicHost.context,logicCall)
 controls["replacement_logic_teardown_rejected"]=staleLogic.fault != 0 && staleLogic.objectConnections!.host.fault != nil &&
   body(staleLogic).memory!.ownsObjectAllocation(logicHelper,count:0x4d8) && word(staleLogic,logicToken+0x10)==0x458680
 let foreignScene=try scene(),foreignSceneActor=attach(foreignScene)
 put(foreignScene,foreignSceneActor+0xc,foreignScene.worldIdentity)
 dispatch(foreignScene,foreignSceneActor,0)
 controls["foreign_scene_pointer_rejected"]=foreignScene.fault != 0 && foreignScene.objectConnections!.host.fault != nil &&
   foreignScene.objectConnections!.calls.isEmpty && word(foreignScene,word(foreignScene,foreignSceneActor+0x6c)+0x18)==0
 let outside=try scene(),outsideActor=attach(outside)
 var forged=ClawCall();forged.function=0x4f6286;forged.receiver=0x62000010;forged.argumentCount=2;forged.arguments.0=0x522d54;forged.arguments.1=outsideActor
 controls["service_outside_callback_rejected"]=body(outside).service(forged)==nil
 require(controls.values.allSatisfy{$0},"Marrow ownership controls: \(controls)")
 try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("marrow-native-input.json"))
 try JSONSerialization.data(withJSONObject:["profiles":outputs,"controls":controls,"trace":runtime.objectConnections!.trace,"faults":positiveFaults,"unresolvedDependencies":positiveUnresolved.sorted()],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("marrow-native-output.json"))
}
