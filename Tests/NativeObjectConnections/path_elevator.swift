import Foundation

// Real logic-owner retirement comparison; no scene attachment or host-wired claim.
#if PATH_ELEVATOR_SCENE_DESTRUCTION_AUDIT
private func u(_ x:Any)->UInt32 {(x as! NSNumber).uint32Value}
private func decode(_ s:String)->[UInt8] {let b=Array(s.utf8);func n(_ c:UInt8)->UInt8 {c>=97 ? c-87:c-48};return stride(from:0,to:b.count,by:2).map{n(b[$0])*16+n(b[$0+1])}}
private func args(_ c:ClawCall)->[UInt32] {var c=c;return withUnsafeBytes(of:&c.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(c.argumentCount)))}}
private final class Fixture {
 let heap=ClawTokenHeap();let host:ClawNativeCanonicalHost;let memory:ClawNativeMfcMemory;let p:[String:Any]
 var calls:[[Any]]=[];var stages:[[String:Any]]=[];var events:[[Any]]=[]
 init(_ p:[String:Any],_ hash:String)throws {
  self.p=p
  for b in p["initial"] as! [[String:Any]] {let d=decode(b["data"] as! String);heap.storeBytes(token:u(b["address"]!),count:UInt32(d.count)).update(from:d,count:d.count)}
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
  let imports=Dictionary(uniqueKeysWithValues:ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map{(i,k) in(k,UInt32(0x710000+i*4))})
  memory=try ClawNativeMfcMemory(host:host,sha256:hash,importTargets:imports,allocationBase:0x61000000,sceneObjectAllocations:true)
  // Every exercised dependency belongs to canonical code or Memory.
  // No native fallback may supply a missing service.
  host.dependency=nil
  host.observer={ [unowned self] c in
   if [UInt32(0x4f63ec),0x4683a0,0x468540,0x468890,0x4688f0,0x4f6286,0x4f6428].contains(c.function) {
    self.calls.append([c.function,c.receiver,args(c)])
    if c.function==0x4f6428 {self.events.append(["free",c.arguments.0])}
   }
  }
  memory.afterService={ [unowned self] function,arguments,result in
   if function==0x4a48e0 {self.events.append(["malloc",result,arguments[0]])}
  }
 }
 var actor:UInt32 {u(p["actor"]!)};var state:UInt32 {u(p["state"]!)}
 func get(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)![0]}
 func hex(_ a:UInt32,_ count:UInt32)->String {
  heap.lookupBytes(a,count:count).map{UnsafeBufferPointer(start:$0,count:Int(count)).map{String(format:"%02x",$0)}.joined()} ?? "missing"
 }
 func call(_ root:UInt32=0x49ee30,_ receiver:UInt32=0,_ a:[UInt32]?=nil)->ClawCall {
  var c=ClawCall();c.function=root;c.receiver=receiver;let values=a ?? [actor];c.argumentCount=UInt32(values.count)
  withUnsafeMutableBytes(of:&c.arguments){raw in let q=raw.bindMemory(to:UInt32.self);for i in values.indices{q[i]=values[i]}};return c
 }
 @discardableResult func invoke(_ c:ClawCall?=nil)->Bool {let r=host.withObjectAllocation(provider:memory){host.invoke(c ?? call())};return r?.completed==true}
 func snapshot(_ index:Int) {
  let expected=(p["stages"] as! [[String:Any]])[index]
  let bytes=(expected["bytes"] as! [[String:Any]]).map {b->[String:Any] in let a=u(b["address"]!),n=UInt32((b["data"] as! String).count/2);let value=heap.lookupBytes(a,count:n).map{UnsafeBufferPointer(start:$0,count:Int(n)).map{String(format:"%02x",$0)}.joined()} ?? "missing";return["address":a,"data":value]}
  stages.append(["name":expected["name"]!,"bytes":bytes])
 }

}
private final class LogicOwnerDestruction {
 let fixture:Fixture
 let fault=UnsafeMutablePointer<UInt32>.allocate(capacity:1)
 var lifecycle:[[String:UInt32]]=[]
 var stateBeforeRelease:String?
 var physicalFrees:[UInt32]=[]
 init(_ fixture:Fixture){self.fixture=fixture;fault.initialize(to:0)}
 deinit{fault.deinitialize(count:1);fault.deallocate()}
 func destroy()->Bool {
  let context=Unmanaged.passUnretained(self).toOpaque()
  let host=ClawSceneActorHost(context:context,lookup:{context,token,count in
   Unmanaged<LogicOwnerDestruction>.fromOpaque(context!).takeUnretainedValue().fixture.heap.lookup(token,words:count)
  },allocate:nil,free:{context,token in
   let owner=Unmanaged<LogicOwnerDestruction>.fromOpaque(context!).takeUnretainedValue(),f=owner.fixture
   if token==f.state {owner.stateBeforeRelease=f.hex(f.state,0x174)}
   f.calls.append([UInt32(0x4f6428),UInt32(0),[token]])
   f.events.append(["free",token])
   f.heap.free(token);owner.physicalFrees.append(token)
  },call:{context,call in
   let owner=Unmanaged<LogicOwnerDestruction>.fromOpaque(context!).takeUnretainedValue(),f=owner.fixture
   owner.lifecycle.append(["function":call.function,"callback":f.get(f.state+0x10)])
   guard call.function==0x49f020,call.argumentCount==1 else{owner.fault.pointee=1;return 0}
   if !f.invoke(f.call(call.function,call.receiver,[call.arguments.0])){owner.fault.pointee=1}
   return call.receiver
  },readClock:nil)
  var globals=ClawActorDestructionGlobals(),result:UInt32=0
  let recognized=claw_actor_destruction_entry(0x4c80c0,fixture.state,1,&globals,host,fault,&result)
  return recognized==1 && fault.pointee==0 && fixture.host.fault==nil
 }
}
@main struct PathElevatorSceneDestructionAudit {
 static func main()throws {
  let directory=URL(fileURLWithPath:CommandLine.arguments[1])
  let reference=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("scene-destruction-reference.json"))) as! [String:Any]
  let hash=reference["executable_sha256"] as! String
  var profiles:[[String:Any]]=[]
  for profile in reference["profiles"] as! [[String:Any]] {
   let f=try Fixture(profile,hash),owner=LogicOwnerDestruction(f)
   let initialized=f.invoke();if initialized{f.snapshot(0)}
   let ticked=initialized && f.invoke();if ticked{f.snapshot(1)}
   let before=f.calls,helper=f.get(f.state+0x18),path=helper==0 ? 0:f.get(helper+8)
   let usesOwner=profile["label"] as! String=="logic-owner"
   if !usesOwner {owner.lifecycle.append(["function":0x49f020,"callback":f.get(f.state+0x10)])}
   let destroyed=ticked && (usesOwner ? owner.destroy():f.invoke(f.call(0x49f020,helper,[1])))
   let pathOwned=f.memory.ownsObjectAllocation(path,count:0x104),helperOwned=f.memory.ownsObjectAllocation(helper,count:0x18)
   let stateBeforeRelease=owner.stateBeforeRelease ?? f.hex(f.state,0x174)
   let stateBytes=decode(stateBeforeRelease=="missing" ? "":stateBeforeRelease)
   let callback:UInt32=stateBytes.count>=0x14 ? (0..<4).reduce(0){$0 | UInt32(stateBytes[0x10+$1]) << (8*$1)}:0
   let pathLive=f.heap.lookupBytes(path,count:1) != nil,helperLive=f.heap.lookupBytes(helper,count:1) != nil
   let physicalFrees=f.memory.events.filter{$0.function==0x4f6428 && $0.completed}.map{$0.arguments[0]}+owner.physicalFrees
   profiles.append(["label":profile["label"]!,"initialized_and_ticked":initialized && ticked,
    "stages":f.stages,"calls_before":before,"calls":f.calls,"events":f.events,"lifecycle":owner.lifecycle,
    "owner_root":usesOwner ? UInt32(0x4c80c0):UInt32(0),"owner_fault_code":owner.fault.pointee,
    "actor_after":f.hex(f.actor,0x1b4),"state_before_release":stateBeforeRelease,"state_live":f.heap.lookupBytes(f.state,count:1) != nil,
    "destroyed":destroyed,"retired":!pathOwned && !helperOwned && !pathLive && !helperLive,"path_owned":pathOwned,"helper_owned":helperOwned,
    "path_live":pathLive,"helper_live":helperLive,"physical_frees":physicalFrees,"callback_after":callback,
    "fault_code":f.host.fault?.code ?? 0,"fault_address":f.host.fault?.address ?? 0,
    "diagnostic":f.host.fault.map{String(describing:$0.diagnostic)} ?? "none"])
  }
  try JSONSerialization.data(withJSONObject:["profiles":profiles],options:[.prettyPrinted,.sortedKeys])
   .write(to:directory.appendingPathComponent("scene-destruction-native.json"))
 }
}
#endif

#if !PATH_ELEVATOR_SCENE_DESTRUCTION_AUDIT
private let pathObserved: Set<UInt32> = [0x4f63ec,0x4683a0,0x468540,0x468890,0x4688f0,0x4f6286,0x4f6428]
private func pathRequire(_ value: Bool, _ message: String) { precondition(value, message) }
private func pathSegment(_ heap: ClawTokenHeap, _ address: UInt32, _ count: UInt32) -> [String: Any] {
    guard let bytes = heap.lookupBytes(address, count: count) else { preconditionFailure("Missing span \(String(address, radix: 16))/\(count)") }
    return ["address": address, "hex": Data(bytes: bytes, count: Int(count)).map { String(format: "%02x", $0) }.joined()]
}
private func pathGraph(_ heap: ClawTokenHeap) -> [[String: Any]] {
    heap.debugAllocationBases.map { address in
        var low: UInt32 = 1, high: UInt32 = 4 << 20
        while low < high { let middle = low + (high-low+1)/2; if heap.lookupBytes(address,count:middle) != nil { low=middle } else { high=middle-1 } }
        return pathSegment(heap,address,low)
    }
}
private func pathBody(_ scene: ClawNativeScene) -> ClawNativePathElevator { scene.objectConnections!.adapter("path_elevator") as! ClawNativePathElevator }
private func pathWord(_ scene: ClawNativeScene,_ address:UInt32)->UInt32 { scene.heap.lookup(address,words:1)!.pointee }
private func pathPut(_ scene:ClawNativeScene,_ address:UInt32,_ value:UInt32) { scene.heap.lookup(address,words:1)!.pointee=value }
private func pathArguments(_ call:ClawCall)->[UInt32] { withUnsafeBytes(of:call.arguments){Array($0.bindMemory(to:UInt32.self).prefix(Int(call.argumentCount)))} }
func runConnection(_ directory:URL)throws {
    let root=directory.appendingPathComponent("resources").standardizedFileURL
    let level=try ClawLevelScene(root:root),assets=try ClawPlayerAssets(root:root)
    let world=try ClawWorld(data:Data(contentsOf:directory.appendingPathComponent("WORLD9.WWD")))
    let records=world.planes.flatMap(\.objects).filter{$0.logic=="PathElevator" && $0.id==9177}
    pathRequire(records.count==1,"Original Level 9 PathElevator id 9177")
    func scene(_ number:UInt32=9)throws->ClawNativeScene {
        let result=ClawNativeScene(player:try ClawNativePlayer(world:level.world,assets:assets),clock:{1000})
        try result.loadRecoveredObjects(world:level.world,root:root,level:number)
        pathRequire(result.fault==0,"Scene setup")
        result.objectConnections!.recordsTrace=true
        result.publishGameTime(375)
        return result
    }
    func attach(_ scene:ClawNativeScene)->UInt32 {
        let before=pathBody(scene).tokens
        let index=level.world.planes.firstIndex(where:{$0.flags & 1 != 0})!
        let plane=scene.camera!.planeTokens[index]
        for record in records {
            let skipped=scene.uninstantiatedObjectCount
            let result=scene.loadGridObject(record,world:world,plane:plane)
            let added=pathBody(scene).tokens.subtracting(before)
            if added.count != 1 || scene.fault != 0 {
                let callback=record.logic.withCString{claw_logic_registry_find($0)?.pointee.callback ?? 0}
                let dimensions=scene.heap.lookup(plane,words:14)!
                let diagnostic="Path WWD id=\(record.id) xy=\(record.x),\(record.y) grid=\(dimensions[12])x\(dimensions[13]) image=\(record.imageSet) result=\(result)/\(record.encodedRecord.count) added=\(added.count) fault=\(scene.fault) callback=\(String(callback,radix:16)) elected=\(scene.objectConnections!.callbacks.contains(callback)) missing=\(scene.objectConnections!.missing) uninstantiatedDelta=\(scene.uninstantiatedObjectCount-skipped)\n"
                FileHandle.standardError.write(Data(diagnostic.utf8))
            }
            pathRequire(result==record.encodedRecord.count && scene.fault==0,"Path attachment: \(String(describing:scene.objectConnections!.host.fault)) \(String(describing:scene.objectLoadingFailure))")
            if added.count==1 {return added.first!}
            pathRequire(added.isEmpty,"One scene-owned PathElevator per WWD record")
        }
        preconditionFailure("No Level 9 PathElevator record was created by the original WWD loader in this scene")
    }
    func dispatch(_ scene:ClawNativeScene,_ actor:UInt32) {
        var call=ClawSceneActorCall();call.function=0x49ee30;call.argumentCount=1;call.arguments.0=actor
        let host=scene.actorHost;_=host.call!(host.context,call)
    }
    func destroy(_ scene:ClawNativeScene,_ actor:UInt32) {
        // The scene's original grid unlink precedes its actor destructor.
        let index=level.world.planes.firstIndex(where:{$0.flags & 1 != 0})!
        let plane=scene.camera!.planeTokens[index],grid=pathWord(scene,plane+0xb0)
        let flags=pathWord(scene,actor+8),layerIndex:UInt32=flags & 0x800000 != 0 ? 1:flags & 0x1000000 != 0 ? 2:0
        let layer=pathWord(scene,grid+(layerIndex+1)*4),member=actor+0x88
        if pathWord(scene,member+12) != 0 { _=scene.spatial(0x4f4680,receiver:layer,arguments:[member]) }
        var call=ClawSceneActorCall();call.function=0x4c9be0;call.receiver=actor;call.argumentCount=1;call.arguments.0=1
        let host=scene.actorHost;_=host.call!(host.context,call)
    }
    var inputs:[[String:Any]]=[],outputs:[[String:Any]]=[],controls:[String:Bool]=[:],trace:[String]=[]
    var positiveFaults:UInt32=0,positiveUnresolved:Set<UInt32>=[]
    for name in ["preset-one","object-pairs","missing-path","level-ten-match","level-ten-miss"] {
        let runtime=try scene(name.hasPrefix("level-ten") ? 10:9),actor=attach(runtime)
        let state=pathWord(runtime,actor+0x6c),adapter=pathBody(runtime),bridge=runtime.objectConnections!,heap=runtime.heap
        pathPut(runtime,actor+0x100,name=="object-pairs" || name=="missing-path" ? 0:1)
        pathPut(runtime,state+0xbc,125);pathPut(runtime,actor+0x110,75)
        if name=="object-pairs" {
            let pairs:[(UInt32,UInt32)]=[(0x118,6),(0x11c,150),(0x120,2),(0x124,80),(0x128,0),(0x12c,0)]
            for (offset,value) in pairs {pathPut(runtime,actor+offset,value)}
        }
        if name=="missing-path" {pathPut(runtime,actor+0x118,0x80000000)}
        if name=="level-ten-match" {pathPut(runtime,actor+0x170,try runtime.objectResources!.images(name:"LEVEL_TRAPELEVATOR")!.token)}
        pathRequire(adapter.syncGlobals(),"Synchronized scene globals")
        let initial=pathGraph(heap)
        var allocations:[[String:UInt32]]=[],bindings:[[String:Any]]=[],calls:[[Any]]=[],events:[[Any]]=[],lifecycle:[[String:UInt32]]=[]
        let observer=bridge.host.observer,dependency=bridge.host.dependency
        bridge.host.observer={call in
            observer?(call)
            if pathObserved.contains(call.function) {
                var arguments=pathArguments(call);if call.function==0x4f6286 {arguments[1]=0}
                calls.append([call.function,call.receiver,arguments])
                if call.function==0x4f6428 {
                    events.append(["free",call.arguments.0])
                    if lifecycle.isEmpty { lifecycle.append(["function":UInt32(0x49f020),"callback":pathWord(runtime,state+0x10)]) }
                }
            }
        }
        bridge.host.dependency={host,call in
            let result=dependency?(host,call)
            if call.function==0x4f6286,let output=host.bytes(call.arguments.1,count:4) {
                let token=UnsafeRawPointer(output).loadUnaligned(as:UInt32.self).littleEndian,key="LEVEL_TRAPELEVATOR"
                bindings.append(["receiver":call.receiver,"name":key,"token":token]);events.append(["lookup",call.receiver,key,token])
            }
            return result
        }
        adapter.memory!.afterService={function,arguments,result in
            if function==0x4a48e0 {allocations.append(["token":result,"count":arguments[0]]);events.append(["malloc",result,arguments[0]])}
        }
        var steps:[[String:Any]]=[],stages:[[String:Any]]=[]
        var identities=true
        for stage in ["initialized","tick"] {
            calls=[];events=[];dispatch(runtime,actor)
            pathRequire(runtime.fault==0 && bridge.host.fault==nil,"Path \(name)/\(stage): \(String(describing:bridge.host.fault))")
            let helper=pathWord(runtime,state+0x18),path=pathWord(runtime,helper+8)
            identities = identities && adapter.memory!.ownsObjectAllocation(path,count:0x104) && adapter.memory!.ownsObjectAllocation(helper,count:0x18)
            let spans:[(UInt32,UInt32)]=[(actor,0x1b4),(state,0x174),(path,0x104),(helper,0x18),(0x537210,4),(0x537960,4),(0x5378a0,200)]
            steps.append(["name":stage,"clock":runtime.gameTime,"spans":spans.map{["address":$0.0,"count":$0.1]}])
            stages.append(["name":stage,"calls":calls,"events":events,"spans":spans.map{pathSegment(heap,$0.0,$0.1)}])
        }
        if name=="missing-path" {controls["missing_path_state_five_inert"]=pathWord(runtime,state+0x1c)==5 && calls.isEmpty}
        let helper=pathWord(runtime,state+0x18),path=pathWord(runtime,helper+8)
        events=[];destroy(runtime,actor)
        let retired=runtime.fault==0 && bridge.host.fault==nil && [actor,state,path,helper].allSatisfy{heap.lookupBytes($0,count:1)==nil} && !adapter.tokens.contains(actor) && bridge.owner(of:actor)==nil && !adapter.memory!.ownsObjectAllocation(path,count:0x104) && !adapter.memory!.ownsObjectAllocation(helper,count:0x18)
        pathRequire(retired,"Source scene retirement \(name): \(String(describing:bridge.host.fault)); scene \(runtime.fault) unresolved \(runtime.unresolvedDependencies)")
        inputs.append(["name":name,"actor":actor,"state":state,"segments":initial,"allocations":allocations,"resourceBindings":bindings,"steps":steps])
        outputs.append(["name":name,"stages":stages,"lifecycle":lifecycle,"helper_frees":events,"retired":retired,"allocation_identities":identities])
        positiveFaults |= runtime.fault;positiveUnresolved.formUnion(runtime.unresolvedDependencies);trace.append(contentsOf:bridge.trace)
        bridge.host.observer=observer;bridge.host.dependency=dependency;adapter.memory!.afterService=nil
        dispatch(runtime,actor)
        controls["retired_owner_rejected_"+name]=bridge.host.fault != nil
    }
    let missing=try scene(10),missingActor=attach(missing)
    pathPut(missing,missingActor+0x100,1);missing.objectConnections!.host.dependency=nil;dispatch(missing,missingActor)
    controls["missing_palette_service_rejected"]=missing.objectConnections!.host.fault?.diagnostic == .missingDependency && missing.objectConnections!.host.fault?.address==0x4f6286 && missing.fault != 0
    for kind in ["actor","state","helper","path"] {
        let runtime=try scene(),actor=attach(runtime),state=pathWord(runtime,actor+0x6c)
        pathPut(runtime,actor+0x100,1)
        if kind=="helper" || kind=="path" {dispatch(runtime,actor);pathRequire(runtime.fault==0,"Replacement control initialization")}
        let helper=pathWord(runtime,state+0x18)
        let address=kind=="actor" ? actor:kind=="state" ? state:kind=="helper" ? helper:pathWord(runtime,helper+8)
        let count:UInt32=kind=="actor" ? 0x1b4:kind=="state" ? 0x174:kind=="helper" ? 0x18:0x104
        let saved=Data(bytes:runtime.heap.lookupBytes(address,count:count)!,count:Int(count)),before=runtime.objectConnections!.calls.count
        runtime.heap.free(address)
        saved.withUnsafeBytes{runtime.heap.storeBytes(token:address,count:count).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:Int(count))}
        dispatch(runtime,actor)
        controls["replacement_"+kind+"_rejected"]=runtime.objectConnections!.host.fault != nil && (kind=="helper" || kind=="path" || runtime.objectConnections!.calls.count==before)
    }
    for kind in ["actor_scene","profile_pointer","image_dictionary","profile_storage"] {
        let runtime=try scene(),actor=attach(runtime),bridge=runtime.objectConnections!
        pathPut(runtime,actor+0x100,1)
        pathRequire(pathBody(runtime).syncGlobals(),"Ownership projection setup")
        if kind=="profile_storage" {
            let address:UInt32=0x5378a0,count:UInt32=200
            let saved=Data(bytes:runtime.heap.lookupBytes(address,count:count)!,count:Int(count))
            runtime.heap.free(address)
            saved.withUnsafeBytes{runtime.heap.storeBytes(token:address,count:count).update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:Int(count))}
        } else {
            let address:UInt32=kind=="actor_scene" ? actor+0xc:kind=="profile_pointer" ? 0x537960:runtime.sceneIdentity+0x10
            pathPut(runtime,address,pathWord(runtime,address)+4)
        }
        let before=bridge.calls.count;dispatch(runtime,actor)
        controls["changed_"+kind+"_rejected"]=bridge.host.fault != nil && bridge.calls.count==before
    }
    let outside=try scene(),outsideActor=attach(outside)
    var forged=ClawCall();forged.function=0x4f6286;forged.receiver=0x62000010;forged.argumentCount=2;forged.arguments.0=0x528a4c;forged.arguments.1=outsideActor
    controls["service_outside_callback_rejected"]=pathBody(outside).service(forged)==nil
    pathRequire(controls.values.allSatisfy{$0},"Path controls: \(controls)")
    try JSONSerialization.data(withJSONObject:["profiles":inputs],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("path-native-input.json"))
    try JSONSerialization.data(withJSONObject:["profiles":outputs,"controls":controls,"trace":trace,"faults":positiveFaults,"unresolvedDependencies":positiveUnresolved.sorted()],options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("path-native-output.json"))
}
#endif
