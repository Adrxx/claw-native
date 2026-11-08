import Foundation
private let observed:Set<UInt32>=[0x4f63ec,0x453bd0,0x4c7fa0,0x4c8060,0x4c8160,0x4c81b0,0x4c96b0,0x4dc870,0x4c9e30,0x4041a0,0x4a36f0,0x4f6974,0x4041b0,0x484d90,0x4f6428]
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
private func body(_ scene:ClawNativeScene)->ClawNativeJumpSwitch{scene.objectConnections!.adapter("jump_switch") as! ClawNativeJumpSwitch}
private func text(_ host:ClawNativeCanonicalHost,_ token:UInt32)->String?{
 var value:[UInt8]=[]
 for offset:UInt32 in 0..<256{guard let bytes=host.bytes(token+offset,count:1) else{return nil};if bytes[0]==0{return String(bytes:value,encoding:.ascii)};value.append(bytes[0])};return nil
}
private func word(_ scene:ClawNativeScene,_ token:UInt32)->UInt32{scene.heap.lookup(token,words:1)!.pointee}
private func put(_ scene:ClawNativeScene,_ token:UInt32,_ value:UInt32){scene.heap.lookup(token,words:1)!.pointee=value}
func runConnection(_ suppliedDirectory:URL)throws{
 let directory=suppliedDirectory.standardizedFileURL,root=suppliedDirectory.appendingPathComponent("resources").standardizedFileURL
 let level=try ClawLevelScene(root:root),assets=try ClawPlayerAssets(root:root)
 let world=try ClawWorld(data:Data(contentsOf:directory.appendingPathComponent("WORLD5.WWD")))
 guard let record=world.planes.flatMap(\.objects).first(where:{$0.logic=="JumpSwitch"}) else{preconditionFailure("Original WWD JumpSwitch")}
 let sourcePlane=world.planes.first(where:{$0.flags & 1 != 0})!
 let width=UInt32(sourcePlane.width*sourcePlane.tileWidth),height=UInt32(sourcePlane.height*sourcePlane.tileHeight)
 var planes:[ObjectIdentifier:UInt32]=[:]
 func scene()throws->ClawNativeScene{
  let value=ClawNativeScene(player:try ClawNativePlayer(world:level.world,assets:assets),clock:{1000})
  try value.loadRecoveredObjects(world:level.world,root:root);require(value.fault==0,"Scene setup")
  // Keep the original Level 5 record and coordinates. Its physical grid uses
  // the original Level 5 bounds, constructed by the recovered layer owner.
  let plane=value.heap.allocate(bytes:180),grid=value.heap.allocate(bytes:112)
  require(plane != 0 && grid != 0,"Comparison plane storage")
  put(value,plane+0x30,width);put(value,plane+0x34,height);put(value,plane+0xb0,grid)
  put(value,grid,value.containerToken)
  for index:UInt32 in 1...3{
   let layer=value.heap.allocate(bytes:0x44);require(layer != 0,"Comparison layer storage")
   put(value,layer,0x513db0)
   require(value.spatial(0x4f4490,receiver:layer,arguments:[0,0,width-1,height-1,256,256])==1 && value.fault==0,"Recovered Level 5 layer construction")
   put(value,grid+index*4,layer)
  }
  planes[ObjectIdentifier(value)]=plane
  value.objectConnections!.recordsTrace=true;return value
 }
 func attach(_ runtime:ClawNativeScene)->UInt32{
  let before=body(runtime).tokens,plane=planes[ObjectIdentifier(runtime)]!
  let result=runtime.loadGridObject(record,world:world,plane:plane)
  require(result==record.encodedRecord.count && runtime.fault==0,"JumpSwitch attach \(record.id): \(result)/\(record.encodedRecord.count) scene=\(runtime.fault) host=\(String(describing:runtime.objectConnections!.host.fault)) loading=\(String(describing:runtime.objectLoadingFailure))")
  let added=body(runtime).tokens.subtracting(before);require(added.count==1,"Exactly one scene owner")
  return added.first!
 }
 func dispatch(_ runtime:ClawNativeScene,_ actor:UInt32,_ command:UInt32,_ callback:UInt32=0x453b10){
  put(runtime,word(runtime,actor+0x6c)+0x1c,command)
  var timing=ClawPlayerDeathCommandGlobals();runtime.captureDeathTiming(&timing);timing.animation.deltaMilliseconds=0;runtime.publishDeathTiming(timing)
  var call=ClawSceneActorCall();call.function=callback;call.argumentCount=1;call.arguments.0=actor
  let host=runtime.actorHost;_=host.call!(host.context,call)
 }
 func destroy(_ runtime:ClawNativeScene,_ actor:UInt32){
  let plane=planes[ObjectIdentifier(runtime)]!,grid=word(runtime,plane+0xb0)
  let flags=word(runtime,actor+8),index:UInt32=flags & 0x800000 != 0 ? 1:flags & 0x1000000 != 0 ? 2:0
  let layer=word(runtime,grid+(index+1)*4),member=actor+0x88
  _=runtime.spatial(0x4f4680,receiver:layer,arguments:[member])
  require(runtime.fault==0 && word(runtime,member+12)==0,"Real scene spatial unlink")
  var call=ClawSceneActorCall();call.function=0x4c9be0;call.receiver=actor;call.argumentCount=1;call.arguments.0=1
  let host=runtime.actorHost;_=host.call!(host.context,call)
  require(runtime.fault==0,"Scene JumpSwitch destruction: \(String(describing:runtime.objectConnections!.host.fault))")
 }
 let runtime=try scene()
 var inputs:[[String:Any]]=[],outputs:[[String:Any]]=[],controls:[String:Bool]=[:]
 var retiredHelper:UInt32=0,firstActor:UInt32=0,positiveFaults:UInt32=0
 var positiveUnresolved:Set<UInt32>=[]
 for iteration in 0..<2{
  print("JumpSwitch positive profile \(iteration)")
  let actor=attach(runtime),state=word(runtime,actor+0x6c),adapter=body(runtime),bridge=runtime.objectConnections!
  if iteration==0{firstActor=actor};let initial=graph(runtime.heap)
  var allocations:[[String:UInt32]]=[],bindings:[[String:Any]]=[],services:[[Any]]=[],allCalls:[ClawCall]=[]
  let dependency=bridge.host.dependency,observer=bridge.host.observer
  bridge.host.observer={call in
   observer?(call);allCalls.append(call)
   if call.function==0x4f6428{let token=call.arguments.0;services.append(["delete",token,word(runtime,token)])}
  }
  bridge.host.dependency={host,call in
   let key=call.function==0x4f6286 ? text(host,call.arguments.0):nil,value=dependency?(host,call)
   if call.function==0x4f6286,let key,let pointer=host.bytes(call.arguments.1,count:4){
    let token=UnsafeRawPointer(pointer).loadUnaligned(as:UInt32.self).littleEndian
    services.append(["registry",call.receiver,key,token])
    if !bindings.contains(where:{($0["receiver"] as? UInt32)==call.receiver && ($0["name"] as? String)==key}){bindings.append(["receiver":call.receiver,"name":key,"token":token])}
   }
   if call.function==0x4f6974,let value {services.append(["buffer",call.receiver,value])}
   return value
  }
  adapter.memory!.afterService={function,args,value in if function==0x4a48e0{allocations.append(["token":value,"count":args[0]]);services.append(["malloc",value,args[0]])}}
  var inputSteps:[[String:Any]]=[],outputSteps:[[String:Any]]=[]
  func step(_ command:Int){
   print("JumpSwitch profile \(iteration) command \(command)")
   services=[];let before=allCalls.count
   let globals:[[String:Any]]=[["address":UInt32(0x5430c4),"hex":"00000000"]]
   if command == -1{require(adapter.retire(actor),"Owned helper scalar teardown")}
   else{dispatch(runtime,actor,UInt32(command))}
   require(runtime.fault==0 && bridge.host.fault==nil,"JumpSwitch command \(command): \(String(describing:bridge.host.fault))")
   let helper=word(runtime,state+0x18),hit=word(runtime,actor+0x70),attack=word(runtime,actor+0x78)
   require(hit != 0 && attack != 0 && adapter.memory!.ownsObjectAllocation(hit,count:0x174) && adapter.memory!.ownsObjectAllocation(attack,count:0x174),"Real nonzero secondary bindings")
   require(command == -1 ? helper==0:adapter.memory!.ownsObjectAllocation(helper,count:0x48),"Exact owned helper lifecycle")
   let spans:[(UInt32,UInt32)]=[(actor,0x1b4),(state,0x174)] + allocations.filter{runtime.heap.lookupBytes($0["token"]!,count:$0["count"]!) != nil}.map{($0["token"]!,$0["count"]!)} + [(0x537668,44),(0x537698,36),(0x5377e8,36)]
   inputSteps.append(["command":command,"inputGlobals":globals,"spans":spans.map{["address":$0.0,"count":$0.1]}])
   outputSteps.append(["command":command,"calls":allCalls.dropFirst(before).filter{observed.contains($0.function)}.map{[$0.function,$0.receiver]},"services":services,"spans":spans.map{segment(runtime.heap,$0.0,$0.1)}])

  }
  var defaultCommand=word(runtime,0x5376a0)
  while [UInt32(0),1000,29,30].contains(defaultCommand) {defaultCommand+=1}
  require(defaultCommand<=word(runtime,0x5376a4),"Real registry lifecycle command")
  for command in [0,1000,29,30,Int(defaultCommand)]{step(command)}
  let previous=word(runtime,state+0x18),secondary=[word(runtime,actor+0x70),word(runtime,actor+0x78)]
  step(-1);step(0);step(Int(defaultCommand))
  controls["same_actor_recreates_helper_and_reuses_secondaries"]=(controls["same_actor_recreates_helper_and_reuses_secondaries"] ?? true) && word(runtime,state+0x18) != previous && runtime.heap.lookupBytes(previous,count:1)==nil && secondary==[word(runtime,actor+0x70),word(runtime,actor+0x78)] && allocations.map{$0["count"]!}==[0x48,0x174,0x174,0x48]
  bridge.host.dependency=dependency;bridge.host.observer=observer;adapter.memory!.afterService=nil
  inputs.append(["name":"WWD-\(record.id)-\(iteration)","actor":actor,"state":state,"segments":initial,"allocations":allocations,"resourceBindings":bindings,"steps":inputSteps]);outputs.append(["name":"WWD-\(record.id)-\(iteration)","steps":outputSteps])
  try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("switch-partial-input.json"))
  try JSONSerialization.data(withJSONObject:["profiles":outputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("switch-partial-output.json"))
  positiveFaults |= runtime.fault;positiveUnresolved.formUnion(runtime.unresolvedDependencies)
  let helper=word(runtime,state+0x18)
  if iteration==0{
   retiredHelper=helper;destroy(runtime,actor)
   positiveFaults |= runtime.fault;positiveUnresolved.formUnion(runtime.unresolvedDependencies)
   controls["scene_destruction_retires_all_allocations"]=runtime.fault==0 && !adapter.tokens.contains(actor) && ([actor,state]+allocations.map{$0["token"]!}).allSatisfy{runtime.heap.lookupBytes($0,count:1)==nil} && !adapter.memory!.ownsObjectAllocation(helper,count:0x48)
  }else{
   controls["same_scene_recreates_actor_and_helper"]=actor != firstActor && helper != retiredHelper && adapter.tokens.contains(actor)
   put(runtime,state+0x18,retiredHelper);dispatch(runtime,actor,1000)
   controls["retired_helper_rejected"]=bridge.host.fault != nil && runtime.fault != 0
  }
 }
 print("JumpSwitch ownership controls")
 let missing=try scene(),missingActor=attach(missing);missing.objectConnections!.host.dependency=nil;dispatch(missing,missingActor,0)
 controls["missing_resource_service_rejected"]=missing.objectConnections!.host.fault?.diagnostic == .missingDependency && missing.objectConnections!.host.fault?.address==0x4f6286 && missing.fault != 0
 let missingBuffer=try scene(),bufferActor=attach(missingBuffer);dispatch(missingBuffer,bufferActor,0)
 require(missingBuffer.fault==0,"Buffer control initialization")
 var idle=word(missingBuffer,0x5376a0)
 while [UInt32(0),1000,29,30].contains(idle) {idle+=1}
 let bufferDependency=missingBuffer.objectConnections!.host.dependency
 missingBuffer.objectConnections!.host.dependency={host,call in call.function==0x4f6974 ? nil:bufferDependency?(host,call)}
 dispatch(missingBuffer,bufferActor,idle)
 controls["missing_state_buffer_service_rejected"]=missingBuffer.objectConnections!.host.fault?.diagnostic == .missingDependency && missingBuffer.objectConnections!.host.fault?.address==0x4f6974 && missingBuffer.fault != 0
 for offset:UInt32 in [0,0x6c]{
  let stale=try scene(),actor=attach(stale),token=offset==0 ? actor:word(stale,actor+offset),count:UInt32=offset==0 ? 0x1b4:0x174
  let saved=Data(bytes:stale.heap.lookupBytes(token,count:count)!,count:Int(count));stale.heap.free(token)
  saved.withUnsafeBytes{stale.heap.storeBytes(token:token,count:count).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:Int(count))}
  dispatch(stale,actor,0)
  controls[offset==0 ? "replacement_actor_rejected":"replacement_logic_rejected"]=stale.objectConnections!.host.fault != nil && stale.objectConnections!.calls.isEmpty
 }
 let staleHelper=try scene(),staleHelperActor=attach(staleHelper);dispatch(staleHelper,staleHelperActor,0);require(staleHelper.fault==0,"Replacement helper initialization")
 let helperToken=word(staleHelper,word(staleHelper,staleHelperActor+0x6c)+0x18),helperBytes=Data(bytes:staleHelper.heap.lookupBytes(helperToken,count:0x48)!,count:0x48),helperCalls=staleHelper.objectConnections!.calls.count
 staleHelper.heap.free(helperToken);helperBytes.withUnsafeBytes{staleHelper.heap.storeBytes(token:helperToken,count:0x48).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:0x48)};dispatch(staleHelper,staleHelperActor,1000)
 controls["replacement_helper_rejected"]=staleHelper.objectConnections!.host.fault != nil && staleHelper.objectConnections!.calls.count==helperCalls && !body(staleHelper).memory!.ownsObjectAllocation(helperToken,count:0x48)
 let foreign=try scene(),foreignActor=attach(foreign);dispatch(foreign,foreignActor,0);require(foreign.fault==0,"Foreign helper initialization")
 let foreignState=word(foreign,foreignActor+0x6c),realHelper=word(foreign,foreignState+0x18),fake=foreign.heap.allocate(bytes:0x48)
 foreign.heap.lookupBytes(fake,count:0x48)!.update(from:foreign.heap.lookupBytes(realHelper,count:0x48)!,count:0x48);put(foreign,foreignState+0x18,fake);dispatch(foreign,foreignActor,1000)
 controls["foreign_helper_rejected"]=foreign.objectConnections!.host.fault != nil && foreign.heap.lookupBytes(fake,count:0x48) != nil
 let wrong=try scene(),wrongActor=attach(wrong);put(wrong,word(wrong,wrongActor+0x6c)+0x10,0x448d10);dispatch(wrong,wrongActor,0)
 controls["foreign_callback_rejected"]=wrong.objectConnections!.host.fault != nil && word(wrong,word(wrong,wrongActor+0x6c)+0x18)==0
 let outside=try scene(),outsideActor=attach(outside)
 var forged=ClawCall();forged.function=0x4f6286;forged.receiver=0x62000010;forged.argumentCount=2;forged.arguments.0=0x522d54;forged.arguments.1=outsideActor
 controls["service_outside_callback_rejected"]=body(outside).service(forged)==nil
 require(controls.values.allSatisfy{$0},"JumpSwitch ownership controls: \(controls)")
 try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("switch-native-input.json"))
 try JSONSerialization.data(withJSONObject:["profiles":outputs,"controls":controls,"trace":runtime.objectConnections!.trace,"faults":positiveFaults,"unresolvedDependencies":positiveUnresolved.sorted()],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("switch-native-output.json"))
}
