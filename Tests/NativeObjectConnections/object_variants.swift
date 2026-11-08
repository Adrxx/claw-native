import Foundation
private let observed:Set<UInt32> = [0x461d50,0x462040,0x49e810,0x40f680,0x49e470,0x49e4b0,0x4c79e0,0x4c82a0,0x4ca610]
private func require(_ value:Bool,_ message:String){precondition(value,message)}
private func word(_ heap:ClawTokenHeap,_ token:UInt32)->UInt32 {heap.lookup(token,words:1)!.pointee}
private func put(_ heap:ClawTokenHeap,_ token:UInt32,_ value:UInt32){heap.lookup(token,words:1)!.pointee=value}
private func segment(_ heap:ClawTokenHeap,_ address:UInt32,_ count:UInt32)->[String:Any]{
 guard let bytes=heap.lookupBytes(address,count:count) else{preconditionFailure("Missing span \(String(address,radix:16))")}
 return ["address":address,"hex":Data(bytes:bytes,count:Int(count)).map{String(format:"%02x",$0)}.joined()]
}
private func graph(_ heap:ClawTokenHeap)->[[String:Any]]{
 heap.debugAllocationBases.compactMap{token in
  if heap.lookupBytes(token,count:4097) != nil{return nil}
  var low:UInt32=1,high:UInt32=4096
  while low<high{let middle=low+(high-low+1)/2;if heap.lookupBytes(token,count:middle) != nil{low=middle}else{high=middle-1}}
  return segment(heap,token,low)
 }
}
private func arguments(_ call:ClawCall)->[UInt32]{withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))}}
private func adapter(_ scene:ClawNativeScene)->ClawNativeObjectVariants{scene.objectConnections!.adapter("object_variants") as! ClawNativeObjectVariants}
func runConnection(_ supplied:URL)throws{
 let directory=supplied.standardizedFileURL,root=directory.appendingPathComponent("resources")
 let level=try ClawLevelScene(root:root),assets=try ClawPlayerAssets(root:root)
 let worlds=try [3,4,9,12,14].map{try ClawWorld(data:Data(contentsOf:directory.appendingPathComponent("WORLD\($0).WWD")))}
 let groups:[(String,UInt32,UInt32,[(String,UInt32,UInt32)])] = [
  ("FloorSpike",3,0x537b8c,[("FloorSpike",0x461d50,1),("FloorSpike2",0x461fe0,2),("FloorSpike3",0x462000,3),("FloorSpike4",0x462020,4)]),
  ("SawBlade",9,0x537b90,[("SawBlade",0x462040,1),("SawBlade2",0x4622f0,2),("SawBlade3",0x462310,3)]),
  ("SteppingStone",4,0x53ebf0,[("SteppingStone",0x49e810,1),("SteppingStone2",0x49ead0,2),("SteppingStone3",0x49eaf0,3),("SteppingStone4",0x49eb10,4)])]
 var provenance:[[String:Any]]=[]
 func scene(_ sourceLevel:UInt32)throws->ClawNativeScene{
  let result=ClawNativeScene(player:try ClawNativePlayer(world:level.world,assets:assets),clock:{1000})
  try result.loadRecoveredObjects(world:level.world,root:root,level:sourceLevel)
  require(result.fault==0,"Scene setup");result.objectConnections!.recordsTrace=true
  for name in ["GAME_FORWARD100","GAME_BACKWARD100","GAME_FORWARD50","GAME_BACKWARD50","LEVEL_SAWBLADE_UP","LEVEL_SAWBLADE_DOWN","LEVEL_SAWBLADE_SPIN"]{_=try result.objectResources!.sequence(name:name)}
  require(!result.player.audio!.outputEnabled,"Silent physical audio");return result
 }
 func record(_ logic:String,_ runtime:ClawNativeScene)->(ClawWorld.Object,ClawWorld){
  for world in worlds{
   if let original=world.planes.flatMap(\.objects).first(where:{$0.logic==logic}){
    // Position is a controlled spatial input. Keep every other original WWD
    // field, callback and resource name, and retain the source bytes locally.
    var words=original.words,encoded=original.encodedRecord
    words[5]=1024;words[6]=1024
    for index in [5,6]{var value=words[index].littleEndian;withUnsafeBytes(of:&value){encoded.replaceSubrange(index*4..<index*4+4,with:$0)}}
    provenance.append(["logic":logic,"id":original.id,"sourceX":original.x,"sourceY":original.y,"controlledX":1024,"controlledY":1024,"sourceRecordOffset":original.encodedRecordOffset,"sourceEncoded":original.encodedRecord.map{String(format:"%02x",$0)}.joined()])
    return(ClawWorld.Object(words:words,encodedRecordOffset:original.encodedRecordOffset,encodedRecord:encoded,name:original.name,logic:original.logic,imageSet:original.imageSet,sound:original.sound),world)
   }
  }
  preconditionFailure("No authentic WWD record for \(logic)")
 }
 func attach(_ runtime:ClawNativeScene,_ logic:String,_ callback:UInt32)->UInt32{
  let (source,world)=record(logic,runtime),before=runtime.objectConnections!.ownedActors
  let index=level.world.planes.firstIndex(where:{$0.flags&1 != 0})!,plane=runtime.camera!.planeTokens[index]
  require(source.logic.withCString{claw_logic_registry_find($0)?.pointee.callback}==callback,"Original callback identity")
  let consumed=runtime.loadGridObject(source,world:world,plane:plane)
  require(consumed==source.encodedRecord.count && runtime.fault==0,"\(logic) load: \(runtime.objectLoadingFailure ?? "") / \(String(describing:runtime.objectConnections!.host.fault))")
  let added=runtime.objectConnections!.ownedActors.subtracting(before)
  require(added.count==1,"One attached actor for \(logic)");return added.first!
 }
 func dispatch(_ runtime:ClawNativeScene,_ actor:UInt32,_ callback:UInt32,_ clock:UInt32){
  runtime.publishGameTime(clock)
  var timing=ClawPlayerDeathCommandGlobals();runtime.captureDeathTiming(&timing);timing.animation.deltaMilliseconds=0;runtime.publishDeathTiming(timing)
  var call=ClawSceneActorCall();call.function=callback;call.argumentCount=1;call.arguments.0=actor
  let host=runtime.actorHost;_=host.call!(host.context,call)
 }
 var inputs:[[String:Any]]=[],outputs:[[String:Any]]=[],traces:[String]=[],controls:[String:Bool]=[:]
 controls["callback_identity_preserved"]=true;controls["variant_globals_shared_with_bases"]=true
 for (family,sourceLevel,global,classes) in groups{
  let runtime=try scene(sourceLevel),heap=runtime.heap,bridge=runtime.objectConnections!
  let actors=classes.map{attach(runtime,$0.0,$0.1)}
  for actor in actors{put(heap,actor+0x38,UInt32.max)}
  let initial=graph(heap)
  var expectedGlobal=word(heap,global)
  var services:[[Any]]=[],bindings:[[String:Any]]=[],inputSteps:[[String:Any]]=[],outputSteps:[[String:Any]]=[]
  let dependency=bridge.host.dependency
  bridge.host.dependency={host,call in
   let name=call.function==0x4f6286 ? clawOriginalResourceNames[call.arguments.0]:nil,result=dependency?(host,call)
   if call.function==0x4f6286,let name,let pointer=host.bytes(call.arguments.1,count:4){
    let token=UnsafeRawPointer(pointer).loadUnaligned(as:UInt32.self)
    services.append(["registry",call.receiver,name,token])
    if !bindings.contains(where:{($0["receiver"] as? UInt32)==call.receiver && ($0["name"] as? String)==name}){bindings.append(["receiver":call.receiver,"name":name,"token":token])}
   };return result
  }
  func step(_ index:Int,_ phase:String,_ clock:UInt32){
   let actor=actors[index],callback=classes[index].1,state=word(heap,actor+0x6c)
   services=[];let start=bridge.calls.count
   if index>0{expectedGlobal=classes[index].2}
   dispatch(runtime,actor,callback,clock)
   require(runtime.fault==0 && bridge.host.fault==nil && runtime.unresolvedDependencies.isEmpty,"\(classes[index].0) \(phase): \(String(describing:bridge.host.fault)) / \(runtime.unresolvedDependencies)")
   controls["callback_identity_preserved"] = controls["callback_identity_preserved"]! && word(heap,state+0x10)==callback
   controls["variant_globals_shared_with_bases"] = controls["variant_globals_shared_with_bases"]! && word(heap,global)==expectedGlobal
   let spans:[(UInt32,UInt32)]=actors.flatMap{actor -> [(UInt32,UInt32)] in [(actor,0x1b4),(word(heap,actor+0x6c),0x174)]}+[(0x537b8c,4),(0x537b90,4),(0x53ebf0,4),(0x5378a0,200),(runtime.sceneIdentity,60),(0x537210,4),(0x5430c4,4),(0x532c0c,4),(0x532c10,4)]
   let globals:[(UInt32,UInt32)]=[(0x537210,4),(0x5430c4,4),(0x532c0c,4),(0x532c10,4)]
   let name=classes[index].0+":"+phase
   inputSteps.append(["name":name,"callback":callback,"actor":actor,"inputGlobals":globals.map{segment(heap,$0.0,$0.1)},"physical":[],"spans":spans.map{["address":$0.0,"count":$0.1]}])
   outputSteps.append(["name":name,"callback":callback,"actor":actor,"calls":bridge.calls.dropFirst(start).filter{observed.contains($0.function)}.map{["function":$0.function,"receiver":$0.receiver,"arguments":arguments($0)] as [String:Any]},"services":services,"spans":spans.map{segment(heap,$0.0,$0.1)}])
  }
  for index in actors.indices{step(index,"initialize",0);if index>0{step(0,"interleaved-base",0)}}
  for index in actors.indices.reversed(){
   let actor=actors[index],state=word(heap,actor+0x6c),phase=word(heap,state+0xbc),period=word(heap,state+0x4c),limit=word(heap,actor+0x148)
   let clock=family=="SteppingStone" ? phase+limit+1:phase+period
   step(index,"active-transition",clock);step(index,"physical-animation",clock)
   if index>0{step(0,"interleaved-base",0)}
  }
  inputs.append(["name":family,"segments":initial,"recordProvenance":provenance,"allocations":[],"resourceBindings":bindings,"steps":inputSteps])
  outputs.append(["name":family,"steps":outputSteps]);traces+=bridge.trace
  bridge.host.dependency=dependency
 }
 let missing=try scene(3),missingActor=attach(missing,"FloorSpike2",0x461fe0)
 dispatch(missing,missingActor,0x461fe0,0)
 let state=word(missing.heap,missingActor+0x6c),on=word(missing.heap,state+0xbc)+word(missing.heap,state+0x4c)
 dispatch(missing,missingActor,0x461fe0,on)
 missing.objectConnections!.host.dependency=nil;dispatch(missing,missingActor,0x461fe0,on)
 controls["missing_service_rejected"]=missing.fault != 0 && missing.objectConnections!.host.fault?.diagnostic == .missingDependency
 for (isActor,name) in [(true,"replacement_actor_rejected"),(false,"replacement_private_state_rejected")]{
  let runtime=try scene(3),actor=attach(runtime,"FloorSpike2",0x461fe0),token=isActor ? actor:word(runtime.heap,actor+0x6c),count:UInt32=isActor ? 0x1b4:0x174
  let bytes=Data(bytes:runtime.heap.lookupBytes(token,count:count)!,count:Int(count));runtime.heap.free(token)
  bytes.withUnsafeBytes{runtime.heap.storeBytes(token:token,count:count).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:Int(count))}
  dispatch(runtime,actor,0x461fe0,0)
  controls[name]=runtime.objectConnections!.host.fault != nil && runtime.objectConnections!.calls.isEmpty
 }
 let spoof=try scene(3),spoofActor=attach(spoof,"FloorSpike2",0x461fe0)
 put(spoof.heap,word(spoof.heap,spoofActor+0x6c)+0x10,0x462000)
 dispatch(spoof,spoofActor,0x461fe0,0)
 controls["callback_rebinding_rejected"]=spoof.objectConnections!.host.fault != nil && spoof.objectConnections!.calls.isEmpty
 let outside=try scene(3),outsideActor=attach(outside,"FloorSpike2",0x461fe0)
 var forged=ClawCall();forged.function=0x4f6286;forged.receiver=0x63000010;forged.argumentCount=2;forged.arguments.0=0x52959c;forged.arguments.1=outsideActor
 controls["service_outside_callback_rejected"]=adapter(outside).service(forged)==nil
 let index=level.world.planes.firstIndex(where:{$0.flags&1 != 0})!,plane=outside.camera!.planeTokens[index],grid=word(outside.heap,plane+0xb0),flags=word(outside.heap,outsideActor+8)
 let layerIndex:UInt32=flags&0x800000 != 0 ? 1:flags&0x1000000 != 0 ? 2:0
 let layer=word(outside.heap,grid+(layerIndex+1)*4),member=outsideActor+0x88
 _=outside.spatial(0x4f4680,receiver:layer,arguments:[member])
 let retiredState=word(outside.heap,outsideActor+0x6c)
 var destroy=ClawSceneActorCall();destroy.function=0x4c9be0;destroy.receiver=outsideActor;destroy.argumentCount=1;destroy.arguments.0=1
 let destructionHost=outside.actorHost;_=destructionHost.call!(destructionHost.context,destroy)
 controls["scene_destruction_retires_actor_and_private_state"]=outside.fault==0 && !adapter(outside).tokens.contains(outsideActor) && outside.heap.lookupBytes(outsideActor,count:1)==nil && outside.heap.lookupBytes(retiredState,count:1)==nil
 dispatch(outside,outsideActor,0x461fe0,0)
 controls["retired_owner_rejected"]=outside.objectConnections!.host.fault != nil
 require(controls.values.allSatisfy{$0},"Variant controls: \(controls)")
 try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("object-variants-native-input.json"))
 try JSONSerialization.data(withJSONObject:["profiles":outputs,"controls":controls,"trace":traces,"faults":0,"unresolvedDependencies":[]],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("object-variants-native-output.json"))
}
