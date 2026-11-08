import Foundation
private let observed:Set<UInt32> = [0x49e470,0x49e4b0,0x4c79e0,0x4c82a0,0x4ca610]
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
private func adapter(_ scene:ClawNativeScene)->ClawNativeSawBlade {scene.objectConnections!.adapter("saw_blade") as! ClawNativeSawBlade}
private func word(_ heap:ClawTokenHeap,_ token:UInt32)->UInt32 {heap.lookup(token,words:1)!.pointee}
private func put(_ heap:ClawTokenHeap,_ token:UInt32,_ value:UInt32) {heap.lookup(token,words:1)!.pointee=value}
private func arguments(_ call:ClawCall)->[UInt32] {
 withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}
}
func runConnection(_ supplied:URL)throws {
 let directory=supplied.standardizedFileURL,root=supplied.appendingPathComponent("resources").standardizedFileURL
 let level=try ClawLevelScene(root:root),assets=try ClawPlayerAssets(root:root)
 let world=try ClawWorld(data:Data(contentsOf:directory.appendingPathComponent("WORLD9.WWD")))
 // This authentic Level 9 record lies inside the shared Level 1 service grid.
 // Keep its WWD bytes unchanged; the first SawBlade is outside that grid.
 guard let record=world.planes.flatMap(\.objects).first(where:{$0.id==631 && $0.logic=="SawBlade"}) else{preconditionFailure("Original Level 9 SawBlade record")}
 require(record.id==631 && record.x==15133 && record.y==6012 && record.imageSet=="LEVEL_FLOORSAW","Original SawBlade WWD identity")
 func scene()throws->ClawNativeScene {
  let result=ClawNativeScene(player:try ClawNativePlayer(world:level.world,assets:assets),clock:{1000})
  try result.loadRecoveredObjects(world:level.world,root:root)
  require(result.fault==0,"Scene setup");result.objectConnections!.recordsTrace=true
  for name in ["LEVEL_SAWBLADE_UP","LEVEL_SAWBLADE_DOWN","LEVEL_SAWBLADE_SPIN"] {require(try result.objectResources!.sequence(name:name) != nil,"Original animation \(name)")}
  require(result.player.audio!.resolve(name:"LEVEL_SAWBLADEUP")==nil && result.player.audio!.resolve(name:"LEVEL_SAWBLADEDOWN")==nil,"Original disc has no SawBlade up/down WAV resources")
  result.player.audio!.routing.masterVolume=80
  require(!result.player.audio!.outputEnabled,"Silent test audio");return result
 }
 func attach(_ runtime:ClawNativeScene)->UInt32 {
  let before=adapter(runtime).tokens,index=level.world.planes.firstIndex(where:{$0.flags & 1 != 0})!
  let plane=runtime.camera!.planeTokens[index],callback=record.logic.withCString{claw_logic_registry_find($0)?.pointee.callback ?? 0}
  print("SawBlade WWD id=\(record.id) logic=\(record.logic) xy=\(record.x),\(record.y) flags=\(record.words[9...12]) callback=\(String(callback,radix:16)) before=\(before.sorted()) world=\(word(runtime.heap,plane+48))x\(word(runtime.heap,plane+52))")
  let count=runtime.loadGridObject(record,world:world,plane:plane)
  require(count==record.encodedRecord.count && runtime.fault==0,"SawBlade load: \(runtime.objectLoadingFailure ?? "") / \(String(describing:runtime.objectConnections!.host.fault))")
  let added=adapter(runtime).tokens.subtracting(before);require(added.count==1,"One scene-owned SawBlade: before=\(before.sorted()) after=\(adapter(runtime).tokens.sorted()) bridge=\(runtime.objectConnections!.ownedActors.sorted()) callback=\(String(callback,radix:16)) consumed=\(count)");return added.first!
 }
 func dispatch(_ runtime:ClawNativeScene,_ actor:UInt32,_ clock:UInt32,_ delta:UInt32) {
  runtime.publishGameTime(clock)
  var timing=ClawPlayerDeathCommandGlobals();runtime.captureDeathTiming(&timing);timing.animation.deltaMilliseconds=delta;runtime.publishDeathTiming(timing)
  var call=ClawSceneActorCall();call.function=0x462040;call.argumentCount=1;call.arguments.0=actor
  let host=runtime.actorHost;_=host.call!(host.context,call)
 }
 var inputs:[[String:Any]]=[],outputs:[[String:Any]]=[],traces:[String]=[],controls:[String:Bool]=[:]
 for enabled in [false,true] {
  let runtime=try scene(),actor=attach(runtime),heap=runtime.heap,bridge=runtime.objectConnections!,audio=runtime.player.audio!
  let state=word(heap,actor+0x6c)
  put(heap,actor+0x38,enabled ? 0:UInt32.max)
  let initial=graph(heap)
  let allocations:[[String:UInt32]]=[]
  var bindings:[[String:Any]]=[],services:[[Any]]=[],physical:[[String:Any]]=[]
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
  var inputSteps:[[String:Any]]=[],outputSteps:[[String:Any]]=[]
  func step(_ name:String,_ clock:UInt32,_ delta:UInt32) {
   services=[];physical=[];let start=bridge.calls.count
   dispatch(runtime,actor,clock,delta);flushPhysical()
   require(runtime.fault==0 && bridge.host.fault==nil && runtime.unresolvedDependencies.isEmpty,"SawBlade \(name): \(String(describing:bridge.host.fault)) / \(runtime.unresolvedDependencies)")
   let spans:[(UInt32,UInt32)]=[(actor,0x1b4),(state,0x174),(0x537210,4),(0x5430c4,4),(0x532c0c,4),(0x532c10,4)]
   let globals:[(UInt32,UInt32)]=[(0x537210,4),(0x5430c4,4),(0x532c0c,4),(0x532c10,4)]
   inputSteps.append(["name":name,"inputGlobals":globals.map{segment(heap,$0.0,$0.1)},"physical":physical,"spans":spans.map{["address":$0.0,"count":$0.1]}])
   outputSteps.append(["name":name,"calls":bridge.calls.dropFirst(start).filter{observed.contains($0.function)}.map{["function":$0.function,"receiver":$0.receiver,"arguments":arguments($0)] as [String:Any]},"services":services,"spans":spans.map{segment(heap,$0.0,$0.1)}])
  }
  let image=word(heap,actor+0x174)
  require(image != 0,"Original SawBlade image geometry")
  let expectedBounds=[word(heap,image+0x20) &- word(heap,image+0x18) &+ 20,
    word(heap,image+0x24) &- word(heap,image+0x1c) &- 20,
    word(heap,image+0x20) &+ word(heap,image+0x18) &- 21,
    word(heap,image+0x24) &+ word(heap,image+0x1c) &- 1]
  step("initialize",0,0);require(word(heap,state+0x1c)==1007,"Initial lower state")
  require((0..<4).map{word(heap,actor+0x138+UInt32($0)*4)}==expectedBounds,"SawBlade hit box follows original image and inset")
  require(word(heap,actor+0xd0)==0x1000000 && word(heap,actor+0x104) != 0 && word(heap,actor+0x64) != 0,"SawBlade initialization damage and timing")
  let phase=word(heap,state+0xbc),period=word(heap,state+0x4c),limit=word(heap,actor+0x148)
  require(period>limit+1,"Nonempty timer true and false intervals")
  let on=phase+period,off=phase+limit+1
  step("lower-timer-false",off,0);require(word(heap,state+0x1c)==1007,"False timer retains lower state")
  step("lower-timer-true",on,0);require(word(heap,state+0x1c)==1002,"True timer requests rise")
  step("rise",on,0);require(word(heap,state+0x1c)==1005,"Forward animation starts")
  for index in 0..<32 where word(heap,state+0x1c)==1005 {step("forward-\(index)",on,101)}
  require(word(heap,state+0x1c)==1006 && word(heap,actor+8)&0x80==0,"Forward completion enables damage")
  step("upper-timer-true",on,0);require(word(heap,state+0x1c)==1006,"True timer retains upper state")
  step("upper-timer-false",off,0);require(word(heap,state+0x1c)==1004,"False timer requests lower")
  step("lower",off,0);require(word(heap,state+0x1c)==1003 && word(heap,actor+8)&0x80 != 0,"Lower disables damage")
  for index in 0..<32 where word(heap,state+0x1c)==1003 {step("backward-\(index)",off,101)}
  require(word(heap,state+0x1c)==1007,"Backward animation completes")
  require(audio.activeVoiceCount==0 && physical.isEmpty && allocations.isEmpty,"Missing original sounds never allocate or play invented PCM")
  let name=enabled ? "sound-enabled":"sound-disabled"
  inputs.append(["name":name,"actor":actor,"segments":initial,"allocations":allocations,"resourceBindings":bindings,"steps":inputSteps])
  outputs.append(["name":name,"steps":outputSteps]);traces+=bridge.trace
  bridge.host.dependency=dependency;bridge.host.observer=observer;audio.observePhysical=nil
  controls[name+"-missing-original-audio-no-voices"]=audio.activeVoiceCount==0
 }
 let missing=try scene(),missingActor=attach(missing)
 dispatch(missing,missingActor,0,0)
 let missingState=word(missing.heap,missingActor+0x6c),missingOn=word(missing.heap,missingState+0xbc)+word(missing.heap,missingState+0x4c)
 dispatch(missing,missingActor,missingOn,0)
 missing.objectConnections!.host.dependency=nil;dispatch(missing,missingActor,missingOn,0)
 controls["missing_service_rejected"]=missing.fault != 0 && missing.objectConnections!.host.fault?.diagnostic == .missingDependency
 let stale=try scene(),staleActor=attach(stale),saved=Data(bytes:stale.heap.lookupBytes(staleActor,count:0x1b4)!,count:0x1b4)
 stale.heap.free(staleActor);saved.withUnsafeBytes{stale.heap.storeBytes(token:staleActor,count:0x1b4).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0x1b4)}
 dispatch(stale,staleActor,0,0);controls["replacement_actor_rejected"]=stale.objectConnections!.host.fault != nil && stale.objectConnections!.calls.isEmpty
 let staleStateScene=try scene(),stateActor=attach(staleStateScene),stateToken=word(staleStateScene.heap,stateActor+0x6c)
 let stateBytes=Data(bytes:staleStateScene.heap.lookupBytes(stateToken,count:0x174)!,count:0x174)
 staleStateScene.heap.free(stateToken);stateBytes.withUnsafeBytes{staleStateScene.heap.storeBytes(token:stateToken,count:0x174).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0x174)}
 dispatch(staleStateScene,stateActor,0,0);controls["replacement_private_state_rejected"]=staleStateScene.objectConnections!.host.fault != nil && staleStateScene.objectConnections!.calls.isEmpty
 let outside=try scene(),outsideActor=attach(outside)
 var forged=ClawCall();forged.function=0x4f6286;forged.receiver=0x63000010;forged.argumentCount=2;forged.arguments.0=0x529610;forged.arguments.1=outsideActor
 controls["service_outside_callback_rejected"]=adapter(outside).service(forged)==nil
 let index=level.world.planes.firstIndex(where:{$0.flags & 1 != 0})!
 let plane=outside.camera!.planeTokens[index],grid=word(outside.heap,plane+0xb0),flags=word(outside.heap,outsideActor+8)
 let layerIndex:UInt32=flags&0x800000 != 0 ? 1:flags&0x1000000 != 0 ? 2:0
 let layer=word(outside.heap,grid+(layerIndex+1)*4),member=outsideActor+0x88
 let cell=word(outside.heap,member+12),beforeCount=word(outside.heap,layer+8)
 require(cell != 0 && beforeCount>0,"SawBlade spatial membership")
 _=outside.spatial(0x4f4680,receiver:layer,arguments:[member])
 require(outside.fault==0 && word(outside.heap,member+12)==0 && word(outside.heap,layer+8)==beforeCount-1,"Source spatial unlink")
 let retiredState=word(outside.heap,outsideActor+0x6c)
 var destroy=ClawSceneActorCall();destroy.function=0x4c9be0;destroy.receiver=outsideActor;destroy.argumentCount=1;destroy.arguments.0=1
 let destructionHost=outside.actorHost;_=destructionHost.call!(destructionHost.context,destroy)
 controls["scene_destruction_retires_actor_and_private_state"]=outside.fault==0 && !adapter(outside).tokens.contains(outsideActor) &&
  outside.heap.lookupBytes(outsideActor,count:1)==nil && outside.heap.lookupBytes(retiredState,count:1)==nil
 dispatch(outside,outsideActor,0,0)
 controls["retired_owner_rejected"]=outside.objectConnections!.host.fault != nil && !adapter(outside).tokens.contains(outsideActor)
 require(controls.values.allSatisfy{$0},"SawBlade controls: \(controls)")
 try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("saw-blade-native-input.json"))
 try JSONSerialization.data(withJSONObject:["profiles":outputs,"controls":controls,"trace":traces,"faults":0,"unresolvedDependencies":[]],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("saw-blade-native-output.json"))
}
