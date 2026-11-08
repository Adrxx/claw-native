import Foundation

// Physical heap controls complement source transport ownership checks.
@main struct SharedHelperAllocations {
 static func main() throws {
  let minimum:UInt32=0x62000000
  var controls:[[String:Any]]=[]
  func record(_ name:String,_ passed:Bool){controls.append(["name":name,"passed":passed])}
  func exact(_ h:ClawTokenHeap,_ t:UInt32,_ n:UInt32)->Bool {
   t != 0 && t & 15==0 && h.allocationIdentity(at:t,count:n) != nil &&
    h.allocationIdentity(at:t,count:n+1)==nil && h.allocationIdentity(at:t+4,count:n-4)==nil &&
    h.lookupBytes(t,count:n) != nil && h.lookupBytes(t,count:n+1)==nil && h.lookup(t,words:n/4+1)==nil
  }
  for size:UInt32 in [0x48,0x58] {
   let prefix=String(format:"0x%x ",size),stride=(size+15) & ~15
   do {
    let h=ClawTokenHeap(),t=h.allocateSceneObject(bytes:size,minimumToken:minimum)
    record(prefix+"minimum and exact aligned extent",t==minimum && exact(h,t,size))
    let identity=h.allocationIdentity(at:t,count:size),ordinary=h.allocate(bytes:13)
    h.lookupBytes(ordinary,count:13)?.update(repeating:0x5a,count:13)
    let next=h.allocateSceneObject(bytes:size,minimumToken:minimum)
    record(prefix+"ordinary interleave advances shared cursor",ordinary==minimum+stride && next==ordinary+16 && exact(h,next,size))
    record(prefix+"interleave preserves identity and bytes",identity != nil && h.allocationIdentity(at:t,count:size) === identity && h.lookupBytes(ordinary,count:13).map{UnsafeBufferPointer(start:$0,count:13).allSatisfy{$0==0x5a}}==true)
    record(prefix+"interior free rejected",!h.freeSceneStorage(t+4) && h.allocationIdentity(at:t,count:size) === identity)
    record(prefix+"base free and double free",h.freeSceneStorage(t) && !h.freeSceneStorage(t) && h.lookupBytes(t,count:1)==nil && h.allocationIdentity(at:next,count:size) != nil && h.lookupBytes(ordinary,count:13) != nil)
    let recreated=h.allocateSceneObject(bytes:size,minimumToken:minimum)
    record(prefix+"free does not rewind cursor",recreated==next+stride && exact(h,recreated,size))
   }
   do {
    let h=ClawTokenHeap(),first=h.allocateSceneObject(bytes:size,minimumToken:minimum+0x1000),ordinary=h.allocate(bytes:0x1b4)
    let second=h.allocateSceneObject(bytes:size,minimumToken:minimum)
    record(prefix+"cursor above minimum",first==minimum+0x1000 && ordinary==first+stride && second==ordinary+512 && exact(h,second,size))
   }
   for offset:Int32 in [0,4,-16] {
    let h=ClawTokenHeap(),occupied=UInt32(Int64(minimum)+Int64(offset))
    h.storeBytes(token:occupied,count:32).update(repeating:0x6d,count:32)
    let identity=h.allocationIdentity(at:occupied,count:32),failed=h.allocateSceneObject(bytes:size,minimumToken:minimum)
    record(prefix+"occupied span \(offset) preserves bytes and cursor",failed==0 && h.allocationIdentity(at:occupied,count:32) === identity && h.lookupBytes(occupied,count:32).map{UnsafeBufferPointer(start:$0,count:32).allSatisfy{$0==0x6d}}==true && h.allocate(bytes:4)==0x61000000)
   }
   do {
    let h=ClawTokenHeap(),failed=h.allocateSceneObject(bytes:size,minimumToken:0x6ffffff0)
    record(prefix+"exhaustion preserves cursor",failed==0 && h.debugAllocationBases.isEmpty && h.allocate(bytes:4)==0x61000000)
    let high=h.allocateSceneObject(bytes:size,minimumToken:0x6fffff00)
    record(prefix+"bounded high allocation",high==0x6fffff00 && exact(h,high,size))
   }
   do {
    let h=ClawTokenHeap()
    record(prefix+"unaligned minimum rejected",h.allocateSceneObject(bytes:size,minimumToken:minimum+4)==0 && h.debugAllocationBases.isEmpty && h.allocate(bytes:4)==0x61000000)
   }
   do {
    let h=ClawTokenHeap(),token=h.allocateSceneObject(bytes:size,minimumToken:minimum)
    let old=h.allocationIdentity(at:token,count:size),freed=h.freeSceneStorage(token)
    h.storeBytes(token:token,count:size)
    let replacement=h.allocationIdentity(at:token,count:size)
    record(prefix+"replacement has fresh identity",freed && old != nil && replacement != nil && old !== replacement && !h.resizeInPlace(token:token,expectedIdentity:old!,expectedCount:size,count:size))
   }
  }
  for size:UInt32 in [0,0x44,0x4c,0x54,0x5c,UInt32.max] {
   let h=ClawTokenHeap()
   record(String(format:"unelected extent 0x%x rejected",size),h.allocateSceneObject(bytes:size,minimumToken:minimum)==0 && h.debugAllocationBases.isEmpty && h.allocate(bytes:4)==0x61000000)
  }
  let failed=controls.filter{$0["passed"] as? Bool != true}
  let result:[String:Any]=["status":failed.isEmpty ? "pass":"fail","controls":controls.count,"failures":failed]
  print(String(decoding:try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]),as:UTF8.self))
  if !failed.isEmpty{exit(1)}
 }
}
