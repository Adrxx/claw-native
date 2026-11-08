import Foundation
private let observed:Set<UInt32> = [0x40f680,0x49e470,0x49e4b0,0x4c79e0,0x4c82a0,0x4ca610,0x4c88e0,0x4b4430,0x4f63ec]
private let physicalTargets:Set<UInt32> = [0x71020014,0x71010018,0x7101001c,0x71010020,0x71010024,0x71010030,0x7101003c,0x71010040,0x71010044,0x71010048]
private func require(_ value:Bool,_ message:String) { precondition(value,message) }
private func segment(_ heap:ClawTokenHeap,_ address:UInt32,_ count:UInt32)->[String:Any] {
 guard let bytes=heap.lookupBytes(address,count:count) else {preconditionFailure("Missing span \(String(address,radix:16)) / \(count)")}
 return ["address":address,"hex":Data(bytes:bytes,count:Int(count)).map{String(format:"%02x",$0)}.joined()]
}
private func graph(_ heap:ClawTokenHeap)->[[String:Any]] {
 heap.debugAllocationBases.compactMap { token in
  // Large PCM bytes and spatial grids are physical owner data.
  if heap.lookupBytes(token,count:4097) != nil {return nil}
  var low:UInt32=1,high:UInt32=4096
  while low<high {let middle=low+(high-low+1)/2;if heap.lookupBytes(token,count:middle) != nil {low=middle}else{high=middle-1}}
  return segment(heap,token,low)
 }
}
private func adapter(_ scene:ClawNativeScene)->ClawNativeSteppingStone {scene.objectConnections!.adapter("stepping_stone") as! ClawNativeSteppingStone}
private func word(_ heap:ClawTokenHeap,_ token:UInt32)->UInt32 {heap.lookup(token,words:1)!.pointee}
private func put(_ heap:ClawTokenHeap,_ token:UInt32,_ value:UInt32) {heap.lookup(token,words:1)!.pointee=value}
private func arguments(_ call:ClawCall)->[UInt32] {
 withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
}
func runConnection(_ supplied:URL)throws {
 let directory=supplied.standardizedFileURL,root=supplied.appendingPathComponent("resources").standardizedFileURL
 let level=try ClawLevelScene(root:root),assets=try ClawPlayerAssets(root:root)
 let world=try ClawWorld(data:Data(contentsOf:directory.appendingPathComponent("WORLD4.WWD")))
 guard let record=world.planes.flatMap(\.objects).first(where:{$0.logic=="SteppingStone" && $0.imageSet=="LEVEL_STEPPINGSTONE"}) else{preconditionFailure("Original Level 4 SteppingStone record")}
 require(record.imageSet=="LEVEL_STEPPINGSTONE","Original SteppingStone WWD identity")
 func scene(linked:Bool = true,controlledSound:Bool = true)throws->ClawNativeScene {
  let root = linked ? root:directory.appendingPathComponent("resources-unlinked")
  let result=ClawNativeScene(player:try ClawNativePlayer(world:level.world,assets:assets),clock:{1000})
  try result.loadRecoveredObjects(world:level.world,root:root,level:4)
  require(result.fault==0,"Scene setup");result.objectConnections!.recordsTrace=true
  for name in ["GAME_FORWARD50","GAME_BACKWARD50"] {require(try result.objectResources!.sequence(name:name) != nil,"Original animation \(name)")}
  // The disc has STONERISE3, but neither literal requested by this callback.
  // Only controlled-bank profiles bind that PCM under the requested keys.
  if controlledSound {
   for name in ["STONERISE","STONESINK"] where result.player.audio!.resolve(name:"LEVEL_"+name)==nil {
    try result.player.audio!.load(name:"LEVEL_"+name,data:Data(contentsOf:root.appendingPathComponent("LEVEL1/SOUNDS/STONERISE3.WAV")))
   }
  } else {
   require(result.player.audio!.resolve(name:"LEVEL_STONERISE")==nil && result.player.audio!.resolve(name:"LEVEL_STONESINK")==nil,"Exact disc bank has no requested literal keys")
  }
  result.player.audio!.routing.masterVolume=80
  require(!result.player.audio!.outputEnabled,"Silent test audio");return result
 }
 func attach(_ runtime:ClawNativeScene)->UInt32 {
  let before=adapter(runtime).tokens,index=level.world.planes.firstIndex(where:{$0.flags & 1 != 0})!
  let plane=runtime.camera!.planeTokens[index],callback=record.logic.withCString{claw_logic_registry_find($0)?.pointee.callback ?? 0}
  print("SteppingStone WWD id=\(record.id) logic=\(record.logic) xy=\(record.x),\(record.y) flags=\(record.words[9...12]) callback=\(String(callback,radix:16)) before=\(before.sorted()) world=\(word(runtime.heap,plane+48))x\(word(runtime.heap,plane+52))")
  let count=runtime.loadGridObject(record,world:world,plane:plane)
  require(count==record.encodedRecord.count && runtime.fault==0,"SteppingStone load: \(runtime.objectLoadingFailure ?? "") / \(String(describing:runtime.objectConnections!.host.fault))")
  let added=adapter(runtime).tokens.subtracting(before);require(added.count==1,"One scene-owned SteppingStone: before=\(before.sorted()) after=\(adapter(runtime).tokens.sorted()) bridge=\(runtime.objectConnections!.ownedActors.sorted()) callback=\(String(callback,radix:16)) consumed=\(count)");return added.first!
 }
 func dispatch(_ runtime:ClawNativeScene,_ actor:UInt32,_ clock:UInt32,_ delta:UInt32) {
  runtime.publishGameTime(clock)
  var timing=ClawPlayerDeathCommandGlobals();runtime.captureDeathTiming(&timing);timing.animation.deltaMilliseconds=delta;runtime.publishDeathTiming(timing)
  var call=ClawSceneActorCall();call.function=0x49e810;call.argumentCount=1;call.arguments.0=actor
  let host=runtime.actorHost;_=host.call!(host.context,call)
 }
 var inputs:[[String:Any]]=[],outputs:[[String:Any]]=[],traces:[String]=[],controls:[String:Bool]=[:]
 for (linked,enabled,controlledSound) in [(true,false,true),(true,true,true),(true,true,false),(false,false,true)] {
  let runtime=try scene(linked:linked,controlledSound:controlledSound),actor=attach(runtime),heap=runtime.heap,bridge=runtime.objectConnections!,body=adapter(runtime),audio=runtime.player.audio!
  let state=word(heap,actor+0x6c)
  require((word(heap,actor+0x170) != 0)==linked,"Physical image-bank presence")
  require(word(heap,0x537960)==0x5378a0,"Source level profile")
  put(heap,actor+0x38,enabled ? 0:UInt32.max)
  let initial=graph(heap)
  var allocations:[[String:UInt32]]=[],bindings:[[String:Any]]=[],services:[[Any]]=[],physical:[[String:Any]]=[]
  let dependency=bridge.host.dependency,observer=bridge.host.observer
  var pending:ClawCall?
  func flushPhysical() {
   guard let call=pending else{return};pending=nil
   let args=arguments(call)
   var event:[String:Any]=["function":call.function,"arguments":args,"result":UInt32(0)]
   if call.function==0x71020014 || [UInt32(0x71010018),0x7101001c,0x71010020,0x71010024].contains(call.function) {
    guard let pointer=bridge.host.bytes(args.last!,count:4) else{preconditionFailure("Physical output cell")}
    event["output"]=UnsafeRawPointer(pointer).loadUnaligned(as:UInt32.self)
   };physical.append(event)
  }
  bridge.host.observer={call in flushPhysical();observer?(call);if physicalTargets.contains(call.function){pending=call}}
  audio.observePhysical={_ in flushPhysical()}
  bridge.host.dependency={host,call in
   let name=call.function==0x4f6286 ? clawOriginalResourceNames[call.arguments.0]:nil,result=dependency?(host,call)
   if call.function==0x4f6286,let name,let pointer=host.bytes(call.arguments.1,count:4) {
    let token=UnsafeRawPointer(pointer).loadUnaligned(as:UInt32.self)
    services.append(["registry",call.receiver,name,token])
    if !bindings.contains(where:{($0["receiver"] as? UInt32)==call.receiver && ($0["name"] as? String)==name}){bindings.append(["receiver":call.receiver,"name":name,"token":token])}
   };return result
  }
  body.memory!.afterService={function,args,value in if function==0x4a48e0 {allocations.append(["token":value,"count":args[0]]);services.append(["malloc",value,args[0]])}}
  let soundRanges=["LEVEL_STONERISE","LEVEL_STONESINK"].flatMap{ name -> [(UInt32,UInt32)] in guard let sound=audio.resolve(name:name) else{return []};return [(sound.resourceToken,64),(sound.voicePoolToken,56)] }
  var imageRanges:[(UInt32,UInt32)]=[]
  if linked {
   let imageToken=word(heap,actor+0x170),images=heap.lookup(imageToken,words:27)!
   imageRanges=[(imageToken,108),(images[5],images[6]*4)]
   for index in Int(images[25])...Int(images[26]) {imageRanges.append((word(heap,images[5]+UInt32(index*4)),64))}
  }
  var inputSteps:[[String:Any]]=[],outputSteps:[[String:Any]]=[]
  func step(_ name:String,_ clock:UInt32,_ delta:UInt32,expectedFault:Bool = false) {
   services=[];physical=[];let start=bridge.calls.count
   dispatch(runtime,actor,clock,delta);flushPhysical()
   if expectedFault {
    require(bridge.host.fault?.code==UInt32(CLAW_FAULT_MEMORY) && [UInt32(0x64),0x68].contains(bridge.host.fault!.address),"Original no-image control boundary")
    controls["unlinked_original_fault_boundary"]=true
   } else {require(runtime.fault==0 && bridge.host.fault==nil && runtime.unresolvedDependencies.isEmpty,"SteppingStone \(name): \(String(describing:bridge.host.fault)) / \(runtime.unresolvedDependencies)")}
   let spans:[(UInt32,UInt32)]=[(actor,0x1b4),(state,0x174),(0x5378a0,200),(runtime.sceneIdentity,60),(0x537210,4),(0x5430c4,4),(0x532c0c,4),(0x532c10,4)]+imageRanges+soundRanges+body.memory!.localPointers.map{($0,56)}
   let globals:[(UInt32,UInt32)]=[(0x537210,4),(0x5430c4,4),(0x532c0c,4),(0x532c10,4)]
   inputSteps.append(["name":name,"expectedFault":expectedFault ? bridge.host.fault!.address as Any:NSNull(),"inputGlobals":globals.map{segment(heap,$0.0,$0.1)},"physical":physical,"spans":spans.map{["address":$0.0,"count":$0.1]}])
   outputSteps.append(["name":name,"expectedFault":expectedFault ? bridge.host.fault!.address as Any:NSNull(),"calls":bridge.calls.dropFirst(start).filter{observed.contains($0.function)}.map{["function":$0.function,"receiver":$0.receiver,"arguments":arguments($0)] as [String:Any]},"services":services,"spans":spans.map{segment(heap,$0.0,$0.1)}])
  }
  step("initialize",0,0)
  require(word(heap,state+0x1c)==1006 && word(heap,actor+0xd0)==0x80,"Initial visible state")
  require(word(heap,actor+0x134)==word(heap,word(heap,0x537960)+0x94)+32,"Source linked rectangle")
  let phase=word(heap,state+0xbc),period=word(heap,state+0x4c),limit=word(heap,actor+0x148)
  require(period>limit+1,"Nonempty timer true and false intervals")
  let on=phase+period,equal=phase+limit,off=phase+limit+1
  step("visible-timer-true",on,0);require(word(heap,state+0x1c)==1006,"True timer retains visible state")
  step("visible-timer-equal",equal,0);require(word(heap,state+0x1c)==1006,"Equality is inclusive")
  step("visible-timer-false",off,0);require(word(heap,state+0x1c)==1004,"False timer requests disappearance")
  if linked {
   step("disappear",off,0);require(word(heap,state+0x1c)==1003 && word(heap,actor+0xd0)==1,"Disappearance starts")
   for index in 0..<32 where word(heap,state+0x1c)==1003 {step("forward-\(index)",off,51)}
   require(word(heap,state+0x1c)==1007 && word(heap,actor+0xd0)==1,"Forward completion removes collision")
   step("hidden-timer-false",off,0);require(word(heap,state+0x1c)==1007,"False timer retains hidden state")
   step("hidden-timer-equal",equal,0);require(word(heap,state+0x1c)==1002,"Equality requests reappearance")
   step("reappear",equal,0);require(word(heap,state+0x1c)==1005,"Reappearance starts")
   for index in 0..<32 where word(heap,state+0x1c)==1005 {step("backward-\(index)",equal,51)}
   require(word(heap,state+0x1c)==1006 && word(heap,actor+0xd0)==0x80,"Backward completion restores collision")
   step("returned-visible",on,0);require(word(heap,state+0x1c)==1006,"Returned visible state")
  } else {
   step("unlinked-disappear",off,0)
   step("unlinked-animation-original-fault",off,51,expectedFault:true)
   require(word(heap,actor+0x170)==0 && word(heap,actor+0x174)==0,"Missing image bank stays unlinked")
  }
  require(enabled && controlledSound ? audio.activeVoiceCount>=2:allocations.isEmpty,"Sound enabled and disabled paths")
  let name=linked ? (enabled ? (controlledSound ? "linked-controlled-sound-enabled":"linked-exact-disc-sound-enabled"):"linked-sound-disabled"):"unlinked-sound-disabled"
  inputs.append(["name":name,"actor":actor,"segments":initial,"allocations":allocations,"resourceBindings":bindings,"steps":inputSteps])
  outputs.append(["name":name,"steps":outputSteps]);traces+=bridge.trace
  bridge.host.dependency=dependency;bridge.host.observer=observer;audio.observePhysical=nil;body.memory!.afterService=nil
  let voices=body.memory!.localPointers
  var audioFault:UInt32=0
  for soundName in ["LEVEL_STONERISE","LEVEL_STONESINK"] {
   if let sound=audio.resolve(name:soundName) {audio.unloadSceneSound(sound.resourceToken,fault:&audioFault)}
  }
  controls[name+"-source-audio-teardown"]=audioFault==0 && body.memory!.localPointers.isEmpty &&
   voices.allSatisfy{heap.lookupBytes($0,count:56)==nil && !body.memory!.ownsObjectAllocation($0,count:56)}
 }
 let missing=try scene(),missingActor=attach(missing)
 dispatch(missing,missingActor,0,0)
 let missingState=word(missing.heap,missingActor+0x6c)
 let missingOff=word(missing.heap,missingState+0xbc)+word(missing.heap,missingActor+0x148)+1
 dispatch(missing,missingActor,missingOff,0)
 missing.objectConnections!.host.dependency=nil;dispatch(missing,missingActor,missingOff,0)
 controls["missing_service_rejected"]=missing.fault != 0 && missing.objectConnections!.host.fault?.diagnostic == .missingDependency && missing.objectConnections!.host.fault?.address==0x4f6286
 let stale=try scene(),staleActor=attach(stale),saved=Data(bytes:stale.heap.lookupBytes(staleActor,count:0x1b4)!,count:0x1b4)
 stale.heap.free(staleActor);saved.withUnsafeBytes{stale.heap.storeBytes(token:staleActor,count:0x1b4).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0x1b4)}
 dispatch(stale,staleActor,0,0);controls["replacement_actor_rejected"]=stale.objectConnections!.host.fault != nil && stale.objectConnections!.calls.isEmpty
 let staleStateScene=try scene(),stateActor=attach(staleStateScene),stateToken=word(staleStateScene.heap,stateActor+0x6c)
 let stateBytes=Data(bytes:staleStateScene.heap.lookupBytes(stateToken,count:0x174)!,count:0x174)
 staleStateScene.heap.free(stateToken);stateBytes.withUnsafeBytes{staleStateScene.heap.storeBytes(token:stateToken,count:0x174).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0x174)}
 dispatch(staleStateScene,stateActor,0,0);controls["replacement_private_state_rejected"]=staleStateScene.objectConnections!.host.fault != nil && staleStateScene.objectConnections!.calls.isEmpty
 let outside=try scene(),outsideActor=attach(outside)
 var forged=ClawCall();forged.function=0x4f6286;forged.receiver=0x63000010;forged.argumentCount=2;forged.arguments.0=0x52dd04;forged.arguments.1=outsideActor
 controls["service_outside_callback_rejected"]=adapter(outside).service(forged)==nil
 let index=level.world.planes.firstIndex(where:{$0.flags & 1 != 0})!
 let plane=outside.camera!.planeTokens[index],grid=word(outside.heap,plane+0xb0),flags=word(outside.heap,outsideActor+8)
 let layerIndex:UInt32=flags&0x800000 != 0 ? 1:flags&0x1000000 != 0 ? 2:0
 let layer=word(outside.heap,grid+(layerIndex+1)*4),member=outsideActor+0x88
 let cell=word(outside.heap,member+12),beforeCount=word(outside.heap,layer+8)
 require(cell != 0 && beforeCount>0,"SteppingStone spatial membership")
 _=outside.spatial(0x4f4680,receiver:layer,arguments:[member])
 require(outside.fault==0 && word(outside.heap,member+12)==0 && word(outside.heap,layer+8)==beforeCount-1,"Source spatial unlink")
 let retiredState=word(outside.heap,outsideActor+0x6c)
 var destroy=ClawSceneActorCall();destroy.function=0x4c9be0;destroy.receiver=outsideActor;destroy.argumentCount=1;destroy.arguments.0=1
 let destructionHost=outside.actorHost;_=destructionHost.call!(destructionHost.context,destroy)
 controls["scene_destruction_retires_actor_and_private_state"]=outside.fault==0 && !adapter(outside).tokens.contains(outsideActor) &&
  outside.heap.lookupBytes(outsideActor,count:1)==nil && outside.heap.lookupBytes(retiredState,count:1)==nil
 dispatch(outside,outsideActor,0,0)
 controls["retired_owner_rejected"]=outside.objectConnections!.host.fault != nil && !adapter(outside).tokens.contains(outsideActor)
 func clone(_ runtime:ClawNativeScene,_ token:UInt32,_ count:UInt32)->UInt32 {
  let data=Data(bytes:runtime.heap.lookupBytes(token,count:count)!,count:Int(count)),copy=runtime.heap.allocate(bytes:count)
  data.withUnsafeBytes{runtime.heap.lookupBytes(copy,count:count)!.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:Int(count))};return copy
 }
 let rebound=try scene(),reboundActor=attach(rebound)
 put(rebound.heap,reboundActor+0x170,clone(rebound,word(rebound.heap,reboundActor+0x170),108))
 dispatch(rebound,reboundActor,0,0)
 controls["linked_image_rebinding_rejected"]=rebound.objectConnections!.host.fault != nil && rebound.objectConnections!.calls.isEmpty
 let tableScene=try scene(),tableActor=attach(tableScene)
 let collection=word(tableScene.heap,tableActor+0x170),table=word(tableScene.heap,collection+0x14),tableCount=word(tableScene.heap,collection+0x18)*4
 put(tableScene.heap,collection+0x14,clone(tableScene,table,tableCount))
 dispatch(tableScene,tableActor,0,0)
 controls["image_table_rebinding_rejected"]=tableScene.objectConnections!.host.fault != nil && tableScene.objectConnections!.calls.isEmpty
 let frameScene=try scene(),frameActor=attach(frameScene)
 let image=word(frameScene.heap,frameActor+0x174),imageBytes=Data(bytes:frameScene.heap.lookupBytes(image,count:64)!,count:64)
 frameScene.heap.free(image)
 imageBytes.withUnsafeBytes{frameScene.heap.storeBytes(token:image,count:64).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:64)}
 dispatch(frameScene,frameActor,0,0)
 controls["image_header_replacement_rejected"]=frameScene.objectConnections!.host.fault != nil && frameScene.objectConnections!.calls.isEmpty
 for (offset,name) in [(UInt32(0x28),"audio"),(UInt32(0x2c),"animation")] {
  let managerScene=try scene(),managerActor=attach(managerScene)
  put(managerScene.heap,managerScene.sceneIdentity+offset,managerScene.heap.allocate(bytes:64))
  dispatch(managerScene,managerActor,0,0)
  controls[name+"_manager_rebinding_rejected"]=managerScene.objectConnections!.host.fault != nil && managerScene.objectConnections!.calls.isEmpty
 }
 let profile=try scene(),profileActor=attach(profile)
 put(profile.heap,0x537960,clone(profile,word(profile.heap,0x537960),192))
 dispatch(profile,profileActor,0,0)
 controls["profile_rebinding_rejected"]=profile.objectConnections!.host.fault != nil && profile.objectConnections!.calls.isEmpty
 let replacedResource=try scene(),resourceActor=attach(replacedResource)
 let resource=replacedResource.player.audio!.resolve(name:"LEVEL_STONERISE")!.resourceToken
 let resourceBytes=Data(bytes:replacedResource.heap.lookupBytes(resource,count:64)!,count:64)
 replacedResource.heap.free(resource)
 resourceBytes.withUnsafeBytes{replacedResource.heap.storeBytes(token:resource,count:64).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:64)}
 dispatch(replacedResource,resourceActor,0,0)
 controls["replacement_audio_resource_rejected"]=replacedResource.objectConnections!.host.fault != nil && replacedResource.objectConnections!.calls.isEmpty
 require(controls.values.allSatisfy{$0},"SteppingStone controls: \(controls)")
 try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("stepping-stone-native-input.json"))
 try JSONSerialization.data(withJSONObject:["profiles":outputs,"controls":controls,"trace":traces,"faults":0,"unresolvedDependencies":[]],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("stepping-stone-native-output.json"))
}
