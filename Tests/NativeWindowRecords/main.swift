import Foundation
struct Step:Decodable { let function:UInt32,eax:UInt32,record:String,counter:UInt32 }
struct Profile:Decodable { let sha256:String,count:UInt32,token:UInt32,initial:String,steps:[Step] }
func bytes(_ hex:String)->[UInt8] {stride(from:0,to:hex.count,by:2).map { i in let a=hex.index(hex.startIndex,offsetBy:i);return UInt8(hex[a..<hex.index(a,offsetBy:2)],radix:16)! }}
let profiles=try JSONDecoder().decode([Profile].self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
for p in profiles {
 precondition(p.sha256=="350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263")
 let app=try ClawNativeApplication(clock:{123}),record=bytes(p.initial)
 let application=Array(UnsafeBufferPointer(start:app.heap.lookupBytes(app.applicationToken,count:0x134)!,count:0x134))
 let span=app.heap.storeBytes(token:0x64000000,count:UInt32(record.count));record.withUnsafeBufferPointer { span.update(from:$0.baseAddress!,count:$0.count) }
 let counter=app.heap.store(token:0x541340,words:1);counter[0]=p.count
 for step in p.steps {
  var c=ClawCall();c.function=step.function;c.receiver=p.token;c.stackPointer=UInt32(CLAW_STACK_TOP)-0x100
  let result=app.invoke(c)
  precondition(result.completed && result.eax==step.eax && result.canonicalFault==nil)
  precondition(Array(UnsafeBufferPointer(start:span,count:record.count))==bytes(step.record))
  precondition(counter[0]==step.counter)
  precondition(Array(UnsafeBufferPointer(start:app.heap.lookupBytes(app.applicationToken,count:0x134)!,count:0x134))==application)
 }
}
print("{\"status\":\"pass\",\"profiles\":4,\"original_source_calls\":12,\"scope\":\"same-application window-owner unit records; no original window creation or menu election\"}")
