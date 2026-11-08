import Foundation
private let actor:UInt32=0x3000000, logic:UInt32=0x3001000
private struct TransportInput:Decodable {
 struct Region:Decodable {let address:UInt32,bytes:Data}
 let allocationBase:UInt32
 let sha256:String,regions:[Region],imports:[String:UInt32]
}
private final class Rig {
 let heap=ClawTokenHeap()
 let host:ClawNativeCanonicalHost
 let memory:ClawNativeMfcMemory
 var services:[[Any]]=[]
 var missing=false
 var fallback=false
 init(_ input:TransportInput) throws {
  for region in input.regions {
   let p=heap.store(token:region.address,words:(region.bytes.count+3)/4)
   region.bytes.withUnsafeBytes {UnsafeMutableRawPointer(p).copyMemory(from:$0.baseAddress!,byteCount:$0.count)}
  }
  host=ClawNativeCanonicalHost(heap:heap);host.stacklessCallerReserve=0x100
  memory=try ClawNativeMfcMemory(host:host,sha256:input.sha256,importTargets:Dictionary(uniqueKeysWithValues:input.imports.map {(UInt32($0.key)!,$0.value)}),allocationBase:input.allocationBase,sceneObjectAllocations:true)
  memory.afterService = { [unowned self] function,args,result in
   if function==0x4a48e0 && result != 0 {services.append(["allocate",args[0],result])}
  }
  host.observer = { [unowned self] call in
   if call.function==0x4f6428 {services.append(["free",call.arguments.0])}
  }
  host.dependency = { [unowned self] h,call in
   guard !missing,h.lavaHandTransportActive else {return nil}
   if call.function==0x4f6974,call.argumentCount==1,call.arguments.0==0,[UInt32(0x3008100),0x3008104].contains(call.receiver) {let value=word(call.receiver);services.append(["table",call.receiver,value]);return value}
   guard call.function==0x4f6286,call.argumentCount==2 else {return nil}
   let key=call.arguments.0;let value:UInt32
   switch key {
   case 0x522d54:value=0x3007700
   case 0x522d48:value=0x3007800
   case 0x5285f8:value=call.receiver==0x3007010 ? 0x3007300:(fallback ? 0:0x3007600)
   case 0x5234b4:value=0x3007600
   case 0x522a48:value=0
   default:return nil
   }
   guard let out=h.bytes(call.arguments.1,count:4) else {return nil}
   out.withMemoryRebound(to:UInt32.self,capacity:1) {$0.pointee=value}
   services.append(["lookup",call.receiver,key,value]);return 1
  }
 }
 func put(_ a:UInt32,_ v:UInt32) {heap.lookup(a,words:1)![0]=v}
 func word(_ a:UInt32)->UInt32 {heap.lookup(a,words:1)![0]}
 @discardableResult func command(_ n:UInt32,clock:UInt32=100,actorToken:UInt32=actor)->Bool {
  put(logic+0x1c,n);put(0x537210,clock)
  var call=ClawCall();call.function=0x4561c0;call.argumentCount=1;call.arguments.0=actorToken
  let completion=host.withObjectAllocation(provider:memory) {host.invoke(call)}
  return completion?.completed==true && host.fault==nil
 }
 func bytes(_ a:UInt32,_ n:UInt32)->[UInt8] {Array(UnsafeBufferPointer(start:heap.lookupBytes(a,count:n)!,count:Int(n)))}
 func snapshot(_ label:String)->[String:Any] {
  let helper=word(logic+0x18)
  let allocations=Dictionary(uniqueKeysWithValues:memory.localRequestedSizes.map {(String($0.key),$0.value)})
  var globals:[String:[UInt8]]=[:]
  for (a,n):(UInt32,UInt32) in [(0x537668,0x2c),(0x537698,0x24),(0x537a30,0x24),(0x537210,4)] {globals[String(a)]=bytes(a,n)}
  return ["label":label,"helper":helper,"actor":bytes(actor,0x1b4),"logic":bytes(logic,0x174),"helperBytes":helper==0 ? []:bytes(helper,0xb8),"globals":globals,"services":services,"allocations":allocations,"secondaries":Dictionary(uniqueKeysWithValues:[word(actor+0x70),word(actor+0x78)].filter {$0 != 0}.map {(String($0),bytes($0,0x174))})]
 }
}
@main struct LavaHandTransportCheck {
 static func main() throws {
  let directory=URL(fileURLWithPath:CommandLine.arguments[1])
  let input=try JSONDecoder().decode(TransportInput.self,from:Data(contentsOf:directory.appendingPathComponent("input.json")))
  let r=try Rig(input);var snapshots:[[String:Any]]=[]
  let stages:[(String,UInt32,UInt32)]=[("construct",0,100),("no-op",1000,100),("command29",29,100),("command30",30,100),("throw-entry",1,100),("throw-update",2,121)]
  for (label,n,clock) in stages {
   guard r.command(n,clock:clock) else {fatalError("\(label): \(String(describing:r.host.fault)); services=\(r.services); allocations=\(r.memory.localRequestedSizes); events=\(r.memory.events.map { (String($0.function,radix:16),$0.arguments,$0.result) })")}
   snapshots.append(r.snapshot(label))
  }
  r.put(actor+0x16c,10);precondition(r.command(2,clock:121));snapshots.append(r.snapshot("projectile-lookup-miss"))
  let secondary=[r.word(actor+0x70),r.word(actor+0x78)]
  precondition(r.host.retireLavaHand(actor:actor,provider:r.memory))
  precondition(secondary.allSatisfy {r.memory.ownsObjectAllocation($0,count:0x174)})
  snapshots.append(r.snapshot("retired"));precondition(r.command(0,clock:121));snapshots.append(r.snapshot("recreated"))
  let fallbackRig=try Rig(input);fallbackRig.fallback=true;precondition(fallbackRig.command(0));snapshots.append(fallbackRig.snapshot("fallback"))
  let mirrored=try Rig(input);mirrored.put(0x300404c,200);precondition(mirrored.command(0));precondition(mirrored.command(1));snapshots.append(mirrored.snapshot("mirrored-throw"))
  var controls:[String:Bool]=[:]
  func control(_ name:String,_ body:(Rig)->Bool) throws {controls[name]=body(try Rig(input))}
  try control("missing-physical-service") {$0.missing=true;return !$0.command(0) && $0.host.fault != nil}
  try control("wrong-actor") {$0.command(0,actorToken:actor+4)==false && $0.host.fault != nil}
  try control("wrong-vtable") {$0.put(0x50e4dc+0x10,0x4041b0);return !$0.command(0)}
  try control("reentry") {q in q.memory.beforeObjectAllocation={_ in _=q.command(0)};return !q.command(0)}
  try control("missing-provider") {q in var call=ClawCall();call.function=0x4561c0;call.argumentCount=1;call.arguments.0=actor;return !q.host.invoke(call).completed && q.host.fault != nil}
  try control("replaced-secondary") {q in guard q.command(0) else {return false};let secondary=q.word(actor+0x70);let saved=q.bytes(secondary,0x174);q.heap.free(secondary);let p=q.heap.store(token:secondary,words:93);saved.withUnsafeBytes {UnsafeMutableRawPointer(p).copyMemory(from:$0.baseAddress!,byteCount:$0.count)};return !q.command(29)}
  try control("wrong-root") {q in q.put(logic+0x10,0x4559e0);return !q.command(0)}
  try control("replaced-actor") {q in guard q.command(0) else {return false};let saved=q.bytes(actor,0x1000);q.heap.free(actor);let p=q.heap.store(token:actor,words:1024);saved.withUnsafeBytes {UnsafeMutableRawPointer(p).copyMemory(from:$0.baseAddress!,byteCount:$0.count)};return !q.command(29)}
  try control("replaced-logic") {q in guard q.command(0) else {return false};let saved=q.bytes(logic,0x1000);q.heap.free(logic);let p=q.heap.store(token:logic,words:1024);saved.withUnsafeBytes {UnsafeMutableRawPointer(p).copyMemory(from:$0.baseAddress!,byteCount:$0.count)};return !q.command(29)}
  try control("replaced-helper") {q in guard q.command(0) else {return false};let h=q.word(logic+0x18);let saved=q.bytes(h,0xb8);q.heap.free(h);let p=q.heap.store(token:h,words:46);saved.withUnsafeBytes {UnsafeMutableRawPointer(p).copyMemory(from:$0.baseAddress!,byteCount:$0.count)};return !q.command(29)}
  try control("stale-helper") {q in guard q.command(0) else {return false};let h=q.word(logic+0x18);guard q.host.retireLavaHand(actor:actor,provider:q.memory) else {return false};q.put(logic+0x18,h);return !q.command(29)}
  try control("double-free") {q in guard q.command(0),q.host.retireLavaHand(actor:actor,provider:q.memory) else {return false};return !q.host.retireLavaHand(actor:actor,provider:q.memory)}
  try control("wrong-provider") {q in guard q.command(0) else {return false};let other=try! ClawNativeMfcMemory(host:q.host,sha256:input.sha256,importTargets:Dictionary(uniqueKeysWithValues:input.imports.map {(UInt32($0.key)!,$0.value)}),allocationBase:0x3200000,sceneObjectAllocations:true);return !q.host.retireLavaHand(actor:actor,provider:other)}
  try control("wrong-size") {q in q.memory.beforeObjectAllocation={request in q.host.bytes(request.context.esp+4,count:4)!.withMemoryRebound(to:UInt32.self,capacity:1) {$0.pointee=0xac}};return !q.command(0)}
  try control("wrong-continuation") {q in q.memory.beforeObjectAllocation={request in q.host.bytes(request.context.esp,count:4)!.withMemoryRebound(to:UInt32.self,capacity:1) {$0.pointee=0x4561fe}};return !q.command(0)}
  try control("foreign-free") {q in guard q.command(0) else {return false};var call=ClawCall();call.function=0x4f6428;call.argumentCount=1;call.arguments.0=q.word(logic+0x18);let rejected = !q.memory.releaseSceneObject(call.arguments.0);return rejected && !q.host.invoke(call).completed}
  try control("allocation-failure") {q in q.memory.failAllocation={_ in true};return !q.command(0) && q.host.fault != nil && q.word(logic+0x18)==0}
  let failure=try Rig(input);failure.memory.failAllocation={_ in true};precondition(!failure.command(0))
  let failureData:[String:Any]=["address":failure.host.fault?.address ?? 0,"command":failure.word(logic+0x1c),"helper":failure.word(logic+0x18)]
  let result:[String:Any]=["snapshots":snapshots,"controls":controls,"allocationFailure":failureData]
  try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]).write(to:directory.appendingPathComponent("native.json"))
  print("LavaHand native transport: \(snapshots.count) snapshots, \(controls.count) controls")
 }
}
