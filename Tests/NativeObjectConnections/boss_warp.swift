import Foundation
// Internal WorldObject constructor0x4c8160 runs within its canonical owner.
// Its stores are covered by complete allocated actor/state byte comparison;
// these ordered calls describe the externally observable host join.
private let observed:Set<UInt32>=[0x4c79e0,0x4c82a0,0x40af90,0x4750d0,0x4c8da0,0x4f63ec,0x4c81b0,0x4701b0]
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
private func body(_ scene:ClawNativeScene)->ClawNativeBossWarp{scene.objectConnections!.adapter("boss_warp") as! ClawNativeBossWarp}
private func text(_ host:ClawNativeCanonicalHost,_ token:UInt32)->String?{
 var value:[UInt8]=[]
 for offset:UInt32 in 0..<256{guard let bytes=host.bytes(token+offset,count:1) else{return nil};if bytes[0]==0{return String(bytes:value,encoding:.ascii)};value.append(bytes[0])};return nil
}
private func word(_ scene:ClawNativeScene,_ token:UInt32)->UInt32{scene.heap.lookup(token,words:1)!.pointee}
private func put(_ scene:ClawNativeScene,_ token:UInt32,_ value:UInt32){scene.heap.lookup(token,words:1)!.pointee=value}
func runConnection(_ directory:URL)throws{
 let fixtures=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("warp-fixtures.json"))) as! [String:Any]
 let normalRoot=URL(fileURLWithPath:"App/GameData").standardizedFileURL
 let world=try ClawWorld(data:Data(contentsOf:directory.appendingPathComponent("WORLD2.WWD")))
 guard let record=world.planes.flatMap(\.objects).first(where:{$0.logic=="BossWarp"}) else{preconditionFailure("Original Level2 BossWarp")}
 func scene(_ fallback:Bool=false)throws->ClawNativeScene{
  let root=fallback ? directory.appendingPathComponent("fallback-resources").standardizedFileURL:normalRoot
  let level=try ClawLevelScene(root:root),assets=try ClawPlayerAssets(root:root)
  let value=ClawNativeScene(player:try ClawNativePlayer(world:level.world,assets:assets),clock:{1000})
  try value.loadRecoveredObjects(world:level.world,root:root)
  require(value.fault==0,"Scene setup");value.objectConnections!.recordsTrace=true;return value
 }
 func attach(_ runtime:ClawNativeScene)->UInt32{
  let before=body(runtime).tokens
  let plane=runtime.camera!.planeTokens[1]
  let result=runtime.loadGridObject(record,world:world,plane:plane)
  require(result==record.encodedRecord.count && runtime.fault==0,"BossWarp attachment result=\(result) scene=\(runtime.fault) host=\(String(describing:runtime.objectConnections!.host.fault)) loading=\(String(describing:runtime.objectLoadingFailure))")
  let added=body(runtime).tokens.subtracting(before);require(added.count==1,"One scene owner");return added.first!
 }
 func dispatch(_ runtime:ClawNativeScene,_ actor:UInt32,_ delta:UInt32){
  var timing=ClawPlayerDeathCommandGlobals();runtime.captureDeathTiming(&timing);timing.animation.deltaMilliseconds=delta;runtime.publishDeathTiming(timing)
  var call=ClawSceneActorCall();call.function=0x470870;call.argumentCount=1;call.arguments.0=actor
  let host=runtime.actorHost;_=host.call!(host.context,call)
 }
 func dispatchChild(_ runtime:ClawNativeScene,_ actor:UInt32){
  var call=ClawSceneActorCall();call.function=0x4701b0;call.argumentCount=1;call.arguments.0=actor
  let host=runtime.actorHost;_=host.call!(host.context,call)
 }
 func destroy(_ runtime:ClawNativeScene,_ actor:UInt32){
  let member=actor+0x88,cell=word(runtime,member+12)
  if cell != 0{
   let plane=runtime.camera!.planeTokens[1],grid=word(runtime,plane+0xb0),flags=word(runtime,actor+8)
   let layerIndex:UInt32=flags & 0x800000 != 0 ? 1:flags & 0x1000000 != 0 ? 2:0
   let layer=word(runtime,grid+(layerIndex+1)*4)
   _=runtime.spatial(0x4f4680,receiver:layer,arguments:[member]);require(runtime.fault==0,"Spatial unlink")
  }
  var call=ClawSceneActorCall();call.function=0x4c9be0;call.receiver=actor;call.argumentCount=1;call.arguments.0=1
  let host=runtime.actorHost;_=host.call!(host.context,call)
 }
 var inputs:[[String:Any]]=[],outputs:[[String:Any]]=[],controls:[String:Bool]=[:],trace:[String]=[]
 var positiveFaults:UInt32=0,unresolved:Set<UInt32>=[]
 for name in ["mode-three","mode-four","fallback-animation"]{
  print("BossWarp profile \(name)")
  let runtime=try scene(name=="fallback-animation"),actor=attach(runtime),state=word(runtime,actor+0x6c),adapter=body(runtime),bridge=runtime.objectConnections!
  let rect=fixtures["SetRect"] as! [String:Any],slot=(rect["slot"] as! NSNumber).uint32Value,target=(rect["target"] as! NSNumber).uint32Value
  if runtime.heap.lookup(slot,words:1)==nil{runtime.heap.store(token:slot,words:1)[0]=target}else{require(word(runtime,slot)==target,"Declared SetRect import binding")}
  if name=="mode-four"{
   let encoded=Array((fixtures["modeFourTable"] as! String).utf8),bytes=stride(from:0,to:encoded.count,by:2).map{UInt8(String(bytes:encoded[$0..<$0+2],encoding:.ascii)!,radix:16)!}
   runtime.heap.storeBytes(token:0x50ef94,count:20).update(from:bytes,count:20);put(runtime,runtime.ownerIdentity,0x50ef94)
  }
  _=try runtime.objectResources!.sequence(name:"GAME_BOSSWARP");_=try runtime.objectResources!.sequence(name:"GAME_POWERUP")
  for resource in ["LEVEL_GEM","GAME_CHECKEDFLAG","GAME_MAPPIECE"]{_=try runtime.objectResources!.images(name:resource)}
  _=runtime.entry(named:"EndOfLevelPowerup")
  let manager=word(runtime,0x5371fc),modeReceiver=word(runtime,manager+0x2c)
  require(word(runtime,manager+0x124)==0,"Declared native low-detail scene profile")
  let initial=graph(runtime.heap)
  print("BossWarp manager=\(String(manager,radix:16)) detail(+124)=\(word(runtime,manager+0x124)) modeReceiver=\(String(modeReceiver,radix:16)) vtable=\(String(word(runtime,modeReceiver),radix:16))")
  try JSONSerialization.data(withJSONObject:["name":name,"actor":actor,"manager":manager,"detail":word(runtime,manager+0x124),"segments":initial],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("warp-predispatch-"+name+".json"))
  var allocations:[[String:UInt32]]=[],bindings:[[String:Any]]=[],services:[[Any]]=[],listOperations:[[String:Any]]=[],allCalls:[ClawCall]=[]
  let dependency=bridge.host.dependency,observer=bridge.host.observer
  bridge.host.observer={call in observer?(call);allCalls.append(call)}
  bridge.host.dependency={host,call in
   let key=call.function==0x4f6286 ? text(host,call.arguments.0):nil,value=dependency?(host,call)
   if call.function==0x4f6286,let key,let pointer=host.bytes(call.arguments.1,count:4){
    let token=UnsafeRawPointer(pointer).loadUnaligned(as:UInt32.self).littleEndian
    services.append(["registry",call.receiver,key,token])
    if !bindings.contains(where:{($0["receiver"] as? UInt32)==call.receiver && ($0["name"] as? String)==key}){bindings.append(["receiver":call.receiver,"name":key,"token":token])}
   }
   if [UInt32(0x4f51c5),0x4f572a].contains(call.function),let value{let arguments=call.argumentCount==1 ? [call.arguments.0]:[call.arguments.0,call.arguments.1];listOperations.append(["function":call.function,"receiver":call.receiver,"arguments":arguments,"result":value]);services.append(["list",call.function,call.receiver,arguments,value])}
   if call.function==0x546d5c,value != nil{services.append(["rectangle",call.arguments.1,call.arguments.2,call.arguments.3,call.arguments.4])}
   return value
  }
  adapter.memory!.afterService={function,args,value in if function==0x4a48e0{allocations.append(["token":value,"count":args[0]]);services.append(["malloc",value,args[0]])}}
  var inputSteps:[[String:Any]]=[],outputSteps:[[String:Any]]=[]
  for delta:UInt32 in name=="mode-four" ? [0]:[0,17]{
   services=[];let before=allCalls.count
   let clocks:[[String:Any]]=[["address":UInt32(0x5430c4),"hex":withUnsafeBytes(of:delta.littleEndian){Data($0).map{String(format:"%02x",$0)}.joined()}]]
   dispatch(runtime,actor,delta)
   require(runtime.fault==0 && bridge.host.fault==nil,"BossWarp \(name) delta\(delta): scene=\(runtime.fault) host=\(String(describing:bridge.host.fault)) unresolved=\(runtime.unresolvedDependencies) calls=\(allCalls.map{String($0.function,radix:16)})")
   let spans:[(UInt32,UInt32)]=[(actor,0x1b4),(state,0x174),(0x5430c4,4),(runtime.containerToken+0x14,12)] + allocations.map{($0["token"]!,$0["count"]!)}
   inputSteps.append(["delta":delta,"inputGlobals":clocks,"spans":spans.map{["address":$0.0,"count":$0.1]}])
   outputSteps.append(["delta":delta,"calls":allCalls.dropFirst(before).filter{observed.contains($0.function)}.map{[$0.function,[UInt32(0x4f63ec),0x4701b0].contains($0.function) ? 0:$0.receiver]},"services":services,"spans":spans.map{segment(runtime.heap,$0.0,$0.1)}])
  }
  bridge.host.dependency=dependency;bridge.host.observer=observer;adapter.memory!.afterService=nil
  inputs.append(["name":name,"actor":actor,"state":state,"segments":initial,"allocations":allocations,"resourceBindings":bindings,"listOperations":listOperations,"rectTarget":runtime.heap.lookup(0x546d5c,words:1)?[0] ?? 0,"steps":inputSteps])
  outputs.append(["name":name,"steps":outputSteps]);trace += bridge.trace
  if name != "mode-four"{
   require(word(runtime,state+0x1c)==5,"Original mode-three phase5")
   let sequence=try runtime.objectResources!.sequence(name:name=="fallback-animation" ? "GAME_POWERUP":"GAME_BOSSWARP")!
   controls[name+"_real_animation_selected"]=word(runtime,actor+0x190)==sequence.token
  }else{
   let children=allocations.filter{$0["count"]==0x1b4}.map{$0["token"]!}
   controls["spawned_actor_identity"]=children.count==1 && word(runtime,children[0]+0x6c)==allocations.first{$0["count"]==0x174}?["token"] && word(runtime,word(runtime,children[0]+0x6c)+0x10)==0x4701b0 && runtime.actorTokens.contains(children[0])
   // Scene update owns the list unlink and destructor call for inserted actors.
   // Keep unrelated actor logic idle for this teardown-only frame.
   for current in runtime.actorTokens{put(runtime,word(runtime,current+0x6c)+0x24,1)}
   for child in children{put(runtime,child+8,word(runtime,child+8)|0x10000)}
   require(runtime.actorFrame(container:runtime.containerToken,refresh:0),"Scene spawned actor teardown frame")
   controls["scene_teardown_retires_spawned_storage"]=allocations.allSatisfy{runtime.heap.lookupBytes($0["token"]!,count:1)==nil && !adapter.memory!.ownsObjectAllocation($0["token"]!,count:$0["count"]!)}
  }
  if runtime.heap.lookupBytes(actor,count:1) != nil{destroy(runtime,actor)}
  controls[name+"_scene_teardown"]=runtime.fault==0 && !adapter.tokens.contains(actor) && runtime.heap.lookupBytes(actor,count:1)==nil && runtime.heap.lookupBytes(state,count:1)==nil
  positiveFaults |= runtime.fault;unresolved.formUnion(runtime.unresolvedDependencies)
 }
 let missing=try scene(),missingActor=attach(missing);missing.objectConnections!.host.dependency=nil;dispatch(missing,missingActor,0)
 controls["missing_service_rejected"]=missing.objectConnections!.host.fault?.diagnostic == .missingDependency && missing.fault != 0
 for replaceState in [false,true]{
  let stale=try scene(),actor=attach(stale),token=replaceState ? word(stale,actor+0x6c):actor,count:UInt32=replaceState ? 0x174:0x1b4
  let bytes=Data(bytes:stale.heap.lookupBytes(token,count:count)!,count:Int(count));stale.heap.free(token)
  bytes.withUnsafeBytes{stale.heap.storeBytes(token:token,count:count).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:Int(count))};dispatch(stale,actor,0)
  controls[replaceState ? "replacement_state_rejected":"replacement_actor_rejected"]=stale.objectConnections!.host.fault != nil && stale.objectConnections!.calls.isEmpty
 }
 // High detail is a real application option, outside the elected finite
 // glitter-free graph. It must fault rather than changing that option.
 let highDetail=try scene(),highActor=attach(highDetail),highManager=word(highDetail,0x5371fc)
 let encodedTable=Array((fixtures["modeFourTable"] as! String).utf8)
 let tableBytes=stride(from:0,to:encodedTable.count,by:2).map{UInt8(String(bytes:encodedTable[$0..<$0+2],encoding:.ascii)!,radix:16)!}
 highDetail.heap.storeBytes(token:0x50ef94,count:20).update(from:tableBytes,count:20)
 put(highDetail,highDetail.ownerIdentity,0x50ef94);put(highDetail,highManager+0x124,1)
 let rectFixture=fixtures["SetRect"] as! [String:Any],rectSlot=(rectFixture["slot"] as! NSNumber).uint32Value,rectTarget=(rectFixture["target"] as! NSNumber).uint32Value
 if highDetail.heap.lookup(rectSlot,words:1)==nil{highDetail.heap.store(token:rectSlot,words:1)[0]=rectTarget}
 dispatch(highDetail,highActor,0)
 controls["high_detail_requires_glitter_graph"]=highDetail.objectConnections!.host.fault != nil && highDetail.fault != 0 && word(highDetail,highManager+0x124)==1
 let unownedChild=try scene(),unownedParent=attach(unownedChild)
 var unownedSourceCalls=0
 let unownedObserver=unownedChild.objectConnections!.host.observer
 unownedChild.objectConnections!.host.observer={call in unownedObserver?(call);if call.function==0x4701b0{unownedSourceCalls += 1}}
 dispatchChild(unownedChild,unownedParent)
 controls["unowned_child_callback_rejected"]=unownedChild.fault != 0 && unownedChild.objectConnections!.host.fault != nil && unownedSourceCalls==0
 unownedChild.objectConnections!.host.observer=unownedObserver
 for replaceChildState in [false,true]{
  let staleChild=try scene(),parent=attach(staleChild)
  staleChild.heap.storeBytes(token:0x50ef94,count:20).update(from:tableBytes,count:20);put(staleChild,staleChild.ownerIdentity,0x50ef94)
  if staleChild.heap.lookup(rectSlot,words:1)==nil{staleChild.heap.store(token:rectSlot,words:1)[0]=rectTarget}
  dispatch(staleChild,parent,0);require(staleChild.fault==0,"Stale child control construction")
  let childMemory=body(staleChild).memory!,children=childMemory.sceneObjectPointers.filter{childMemory.ownsObjectAllocation($0,count:0x1b4)}
  require(children.count==1,"One genuine source-created child")
  let child=children[0],token=replaceChildState ? word(staleChild,child+0x6c):child,count:UInt32=replaceChildState ? 0x174:0x1b4
  let saved=Data(bytes:staleChild.heap.lookupBytes(token,count:count)!,count:Int(count));staleChild.heap.free(token)
  saved.withUnsafeBytes{staleChild.heap.storeBytes(token:token,count:count).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:Int(count))}
  var childSourceCalls=0
  let childObserver=staleChild.objectConnections!.host.observer
  staleChild.objectConnections!.host.observer={call in childObserver?(call);if call.function==0x4701b0{childSourceCalls += 1}}
  dispatchChild(staleChild,child)
  controls[replaceChildState ? "replacement_child_state_rejected":"replacement_child_actor_rejected"]=staleChild.fault != 0 && staleChild.objectConnections!.host.fault != nil && childSourceCalls==0
  staleChild.objectConnections!.host.observer=childObserver
 }
 let outside=try scene(),outsideActor=attach(outside)
 var forged=ClawCall();forged.function=0x4f6286;forged.argumentCount=2;forged.arguments.0=0x52a204;forged.arguments.1=outsideActor
 controls["service_outside_callback_rejected"]=body(outside).service(forged)==nil
 require(controls.values.allSatisfy{$0},"BossWarp ownership controls: \(controls)")
 try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("warp-native-input.json"))
 try JSONSerialization.data(withJSONObject:["profiles":outputs,"controls":controls,"trace":trace,"faults":positiveFaults,"unresolvedDependencies":unresolved.sorted()],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("warp-native-output.json"))
}
