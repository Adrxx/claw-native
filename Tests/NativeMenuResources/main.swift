import Foundation
import CryptoKit

let root = URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
let metadataFile = root.appendingPathComponent("work/native-menu-resources/metadata.json")
let raw = try JSONSerialization.jsonObject(with:Data(contentsOf:metadataFile)) as! [String:[UInt8]]
let metadata = Dictionary(uniqueKeysWithValues:raw.map{(UInt32($0.key,radix:16)!,Data($0.value))})
let heap = ClawTokenHeap()
let shared = heap.allocate(bytes:16)
heap.lookup(shared,words:4)![0] = 0xc1a0
let owner = try ClawNativeMenuResources(heap:heap,archiveURL:root.appendingPathComponent("Original/claw-disc/files/DATA/CLAW.REZ"),metadata:metadata)
do {try owner.open()} catch {print("FAIL open",error,"at",String(owner.faultAddress,radix:16),owner.events);exit(2)}
let directory = owner.directory("STATES_MENU")
precondition(directory != 0 && owner.fault == 0)
var resources:[[String:Any]] = []
for (path,name,type):(String,String,UInt32) in [("STATES_MENU","CLAW",0x494643),("STATES_MENU_SCREENS","MENU",0x504358),("STATES_MENU_ANIS","CURSOR",0x414e49)] {
    let dir = owner.directory(path)
    let token = dir == 0 ? 0:owner.resource(directory:dir,name:name,type:type)
    let data = owner.load(token)
    resources.append(["path":path,"name":name,"type":type,"found":data != nil,"bytes":data?.count ?? 0,
                      "sha256":data.map{SHA256.hash(data:$0).map{String(format:"%02x",$0)}.joined()} ?? ""])
}
precondition(resources[0]["found"] as! Bool)
precondition(owner.directory("MISSING_MENU_DIRECTORY") == 0 && owner.fault == 0)
precondition(owner.resource(directory:directory,name:"MISSING",type:0x494643) == 0 && owner.fault == 0)
let beforeClose = owner.events
owner.close();owner.close()
precondition(owner.openFileCount == 0 && owner.liveAllocationCount == 0)
precondition(heap.lookup(shared,words:4)![0] == 0xc1a0)
let report:[String:Any] = ["resources":resources,"services":beforeClose,"cleanupFault":owner.fault,"cleanupAddress":owner.faultAddress,"cleanupRemaining":owner.cleanupRemaining,"destroyedArchive":Array(owner.destroyedArchive),"cleanupServices":Array(owner.events.dropFirst(beforeClose.count))]
try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys,.prettyPrinted]).write(to:root.appendingPathComponent("work/native-menu-resources/swift.json"))
precondition(owner.fault == 0 && owner.cleanupRemaining == 0,"Cleanup did not complete: \(owner.fault) \(String(owner.faultAddress,radix:16)) remaining \(owner.cleanupRemaining)")
print("PASS native resource archive, three actual menu assets and recovered cleanup")
