import Foundation
import CryptoKit

struct Folder: Decodable {let path:String;let offset:UInt32;let bytes:UInt32;let stamp:UInt32}
struct Resource: Decodable {let folder:String;let name:String;let offset:UInt32;let bytes:UInt32;let stamp:UInt32;let id:UInt32;let tag:UInt32;let sha256:String}
struct Inventory: Decodable {let folders:[Folder];let resources:[Resource]}
let archiveURL = URL(fileURLWithPath:CommandLine.arguments[1])
let inventory = try JSONDecoder().decode(Inventory.self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2])))
precondition(inventory.folders.count == 1384 && inventory.resources.count == 13077)
let heap = ClawTokenHeap()
let archive = try ClawNativeResourceArchive(heap:heap,url:archiveURL)
precondition(archive.fault == 0 && archive.unresolved.isEmpty)
let root = archive.lookupFolder("")
precondition(root != 0)
let baseline = archive.sourceAllocations.count
var folderTokens: [String:UInt32] = ["":root]
var treeFolders:Set<UInt32> = [],treeResources:Set<UInt32> = []
func ns(_ f:UInt32,_ t:UInt32,_ a:[UInt32] = []) -> UInt32 {
    let v = archive.namespace(f,receiver:t,args:a);precondition(archive.fault == 0);return v
}
func inspect(_ folder:UInt32) {
    precondition(treeFolders.insert(folder).inserted)
    var child = ns(0x4b68e0,folder)
    while child != 0 {inspect(child);child = ns(0x4b6900,folder,[child])}
    var type = ns(0x4b6920,folder)
    while type != 0 {
        var resource = ns(0x4b6960,folder,[type])
        while resource != 0 {
            precondition(treeResources.insert(resource).inserted)
            let w = heap.lookup(resource,words:24)!
            precondition(w[9] == folder && w[2] == type && w[17] == resource && w[23] == resource)
            resource = ns(0x4b6980,type,[resource])
        };type = ns(0x4b6940,folder,[type])
    }
}
inspect(root)
precondition(treeFolders.count == 1384 && treeResources.count == 13077)
for f in inventory.folders {
    let components = f.path.split(separator:"\\")
    let parent = components.dropLast().joined(separator:"\\")
    let token = f.path.isEmpty ? root : archive.lookupChild(folder:folderTokens[parent]!,name:components.last!.description)
    guard token != 0 && archive.fault == 0 && treeFolders.contains(token) else {fatalError("Folder lookup failed: \(f.path) token\(token) fault\(archive.fault)")}
    folderTokens[f.path] = token
    let w = heap.lookup(token,words:19)!
    precondition(w[1] == f.offset && w[2] == f.bytes && w[5] == f.stamp && w[6] == archive.controller && w[14] == token)
    if !f.path.isEmpty {
        precondition(archive.name(w[0]) == components.last! && w[7] == folderTokens[parent])
        // Source4b7f20 treats underscores as separators; preserve that grammar.
        // Direct4b68c0 is the original API for a raw component name.
        if !f.path.contains("_") {
            precondition(archive.lookupFolder(f.path) == token && archive.lookupFolder(f.path.lowercased()) == token && archive.fault == 0)
        }
    }
    let children = inventory.folders.enumerated().filter {i,c in
        guard !c.path.isEmpty else {return false}
        return c.path.split(separator:"\\").dropLast().joined(separator:"\\") == f.path
    }.sorted {a,b in
        let x = a.element.path.split(separator:"\\").last!.utf8.count%5
        let y = b.element.path.split(separator:"\\").last!.utf8.count%5
        return x == y ? a.offset > b.offset : x < y
    }.map {$0.element.path.split(separator:"\\").last!.description}
    var names:[String] = [], child = ns(0x4b68e0,token)
    while child != 0 {names.append(archive.name(heap.lookup(child,words:19)![0]));child = ns(0x4b6900,token,[child])}
    precondition(names == children)
}
print("PASS native source full REZ1384 folder metadata/direct names/compatible source paths/ASCII-case/bucket prepend order and13077 resource tree ownership")
var cached:UInt32 = 0,total:UInt64 = 0
for (index,r) in inventory.resources.enumerated() {
    let folder = folderTokens[r.folder]!
    let token = archive.lookupResource(folder:folder,name:r.name,tag:r.tag)
    precondition(token != 0 && archive.fault == 0 && treeResources.contains(token))
    let w = heap.lookup(token,words:24)!
    precondition(archive.name(w[0]) == r.name && w[1] == r.id && heap.lookup(w[2],words:11)![0] == r.tag)
    precondition(w[3] == 0 && w[4] == r.stamp && w[5] == r.bytes && w[6] == 0 && w[7] == 0 && w[8] == 0 && w[9] == folder && w[10] == r.offset && w[11] == 0)
    let before = archive.sourceAllocations.count
    guard let bytes = archive.payload(token) else {fatalError("Source payload failure \(r.folder) \(r.name) fault\(archive.fault)")}
    let hash = SHA256.hash(data:bytes).map {String(format:"%02x",$0)}.joined()
    precondition(bytes.count == r.bytes && hash == r.sha256 && archive.fault == 0)
    let readCalls = archive.calls[0x4a7260]
    precondition(archive.payload(token) == bytes && archive.calls[0x4a7260] == readCalls && archive.fault == 0)
    precondition(archive.sourceAllocations.count == before+(r.bytes == 0 ? 0 : 1))
    if cached == 0 && r.bytes > 0 {cached = token}
    else {precondition(archive.resource(0x4b6230,token:token) == 1 && archive.fault == 0 && w[6] == 0 && archive.sourceAllocations.count == before)}
    total += UInt64(bytes.count)
    if (index+1)%2000 == 0 {print("Native REZ payloads",index+1,"of13077")}
}
// Verify both ID and name embedded-map iteration orders against record order.
for f in inventory.folders {
    let records = inventory.resources.enumerated().filter {$0.element.folder == f.path}
    let token = folderTokens[f.path]!
    var type = ns(0x4b6920,token)
    while type != 0 {
        let tag = heap.lookup(type,words:11)![0]
        let matching = records.filter {$0.element.tag == tag}
        for (offset,key) in [(UInt32(28),true),(UInt32(36),false)] {
            let expected = matching.sorted {a,b in
                let x = key ? Int(a.element.id%19) : a.element.name.utf8.count%19
                let y = key ? Int(b.element.id%19) : b.element.name.utf8.count%19
                return x == y ? a.offset > b.offset : x < y
            }.map {$0.element.name}
            var names:[String] = [],node = ns(0x4d54c0,type+offset)
            while node != 0 {let resource = heap.lookup(node+20,words:1)!.pointee;names.append(archive.name(heap.lookup(resource,words:24)![0]));node = ns(0x4d5350,node)}
            precondition(names == expected)
        };type = ns(0x4b6940,token,[type])
    }
}
precondition(total == 117018527 && cached != 0 && archive.sourceAllocations.count == baseline+1)
let payloadToken = heap.lookup(cached,words:24)![6]
let sourceTokens = Array(archive.sourceAllocations.keys)
archive.shutdown()
precondition(archive.fault == 0 && archive.sourceAllocations.isEmpty && archive.unresolved.isEmpty)
precondition(sourceTokens.allSatisfy {heap.lookup($0,words:1) == nil} && heap.lookup(payloadToken,words:1) == nil)
precondition(archive.calls[0x4a7ae0] == 2 && archive.calls[0x42a680] == 1)
precondition(archive.lookupFolder("LEVEL1") == 0)
print("PASS native complete actual REZ1384folders/13077resources/117018527payload bytes → source directory parser/embedded bucket prepend order/namespace/cached repeat/all hashes → complete source destructor and retained payload release; ASAN/UBSAN. FILE/allocator/32-bit token transport explicit; no live app menu or original full-boot sensory parity claim")

func rejectsTransport(_ body: () throws -> UInt32) {
    do {_ = try body();fatalError("Expected rejected archive lifecycle operation")}
    catch ClawNativeResourceArchive.Failure.transport(_) {}
    catch {fatalError("Unexpected archive error: \(error)")}
}
// The application allocates both controller and path; adoption must not run
// construction, open a FILE, or take ownership of either allocation.
let borrowedHeap = ClawTokenHeap()
let borrowedController = borrowedHeap.allocate(bytes:72)
borrowedHeap.lookup(borrowedController,words:18)!.update(repeating:0xa5a5a5a5,count:18)
let pathBytes = Array(archiveURL.path.utf8)+[UInt8(0)]
let borrowedPath = borrowedHeap.allocate(bytes:UInt32(pathBytes.count))
pathBytes.withUnsafeBytes {
    UnsafeMutableRawPointer(borrowedHeap.lookup(borrowedPath,words:UInt32((pathBytes.count+3)/4))!)
        .copyMemory(from:$0.baseAddress!,byteCount:$0.count)
}
var borrowed: ClawNativeResourceArchive? = try ClawNativeResourceArchive(
    heap:borrowedHeap,borrowingController:borrowedController,borrowedBytes: {token,count in
        guard token >= borrowedPath, UInt64(token)+UInt64(count) <= UInt64(borrowedPath)+UInt64(pathBytes.count),
              let bytes = borrowedHeap.lookupBytes(token,count:count) else {return nil}
        return bytes
    })
precondition(borrowed!.lifecycle == .uninitialized && !borrowed!.ownsController && !borrowed!.hasOpenFile)
precondition(borrowed!.operationCalls.isEmpty && borrowed!.sourceAllocations.isEmpty)
precondition(borrowedHeap.lookup(borrowedController,words:18)![0] == 0xa5a5a5a5)
let borrowedTransport = borrowed!.transportAllocationTokens
precondition(borrowedTransport.count == 1 && !borrowedTransport.contains(borrowedController))
rejectsTransport {try borrowed!.operation(0x4b72e0,args:[borrowedPath,1,0])}
let constructed = try borrowed!.operation(0x4b7210)
precondition(constructed == borrowedController && borrowed!.lifecycle == .constructed)
rejectsTransport {try borrowed!.operation(0x4b7210)}
let opened = try borrowed!.operation(0x4b72e0,args:[borrowedPath,1,0])
precondition(opened == 1 && borrowed!.fault == 0 && borrowed!.hasOpenFile && borrowed!.fileOpenCount == 1)
rejectsTransport {try borrowed!.operation(0x4b72e0,args:[borrowedPath,1,0])}
let sample = inventory.resources.first {$0.bytes > 0}!
var sampleFolder = borrowed!.lookupFolder("")
for component in sample.folder.split(separator:"\\") {
    sampleFolder = borrowed!.lookupChild(folder:sampleFolder,name:String(component))
    precondition(sampleFolder != 0)
}
let sampleToken = borrowed!.lookupResource(folder:sampleFolder,name:sample.name,tag:sample.tag)
let samplePayload = borrowed!.payload(sampleToken)!
precondition(SHA256.hash(data:samplePayload).map {String(format:"%02x",$0)}.joined() == sample.sha256)
let borrowedSourceTokens = Array(borrowed!.sourceAllocations.keys)
let destroyed = try borrowed!.operation(0x4b7250)
precondition(destroyed == 0 && borrowed!.fault == 0 && borrowed!.closed && !borrowed!.hasOpenFile)
precondition(borrowed!.sourceAllocations.isEmpty && borrowed!.unresolved.isEmpty)
precondition(borrowed!.operationCalls == [0x4b7210:1,0x4b72e0:1,0x4b7250:1])
precondition(borrowed!.calls[0x4a7ae0] == 2 && borrowed!.fileCloseCount == 1)
borrowed!.shutdown()
precondition(borrowed!.operationCalls[0x4b7250] == 1 && borrowed!.fileCloseCount == 1)
rejectsTransport {try borrowed!.operation(0x4b7250)}
borrowed = nil
precondition(borrowedSourceTokens.allSatisfy {borrowedHeap.lookup($0,words:1) == nil})
precondition(borrowedTransport.allSatisfy {borrowedHeap.lookup($0,words:1) == nil})
precondition(borrowedHeap.lookup(borrowedController,words:18) != nil && borrowedHeap.lookup(borrowedPath,words:1) != nil)
borrowedHeap.free(borrowedController);borrowedHeap.free(borrowedPath)
print("PASS borrowed application controller and CString → one source constructor/open → real REZ lookup and payload hash → one destructor, two original close elections, one physical fclose; caller allocations survive host release")

// Failed source fopen returns zero without a native fault; its retained path
// allocation still belongs to the source destructor, never to the caller.
let missingHeap = ClawTokenHeap(), missingController = missingHeap.allocate(bytes:72)
var missing: ClawNativeResourceArchive? = try ClawNativeResourceArchive(heap:missingHeap,borrowingController:missingController)
let missingTransport = missing!.transportAllocationTokens
let missingPath = missing!.string(FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString+"/CLAW.REZ").path)
_ = try missing!.operation(0x4b7210)
let failedOpen = try missing!.operation(0x4b72e0,args:[missingPath,1,0])
precondition(failedOpen == 0 && missing!.fault == 0 && missing!.unresolved.isEmpty && !missing!.hasOpenFile)
precondition(missing!.fileOpenCount == 0 && !missing!.sourceAllocations.isEmpty)
let failedSourceTokens = Array(missing!.sourceAllocations.keys)
missing!.shutdown()
precondition(missing!.fault == 0 && missing!.sourceAllocations.isEmpty && missing!.fileCloseCount == 0)
precondition(missing!.calls[0x4a7ae0,default:0] == 0)
precondition(missing!.operationCalls == [0x4b7210:1,0x4b72e0:1,0x4b7250:1])
missing!.shutdown();missing = nil
precondition(failedSourceTokens.allSatisfy {missingHeap.lookup($0,words:1) == nil})
precondition(missingTransport.allSatisfy {missingHeap.lookup($0,words:1) == nil})
precondition(missingHeap.lookup(missingController,words:18) != nil && missingHeap.lookup(missingPath,words:1) != nil)
missingHeap.free(missingController);missingHeap.free(missingPath)
print("PASS borrowed missing-file open preserves original zero return, releases source path on shutdown, performs no fclose, and retains caller controller")

// Dropping an adopted host before bootstrap must not destruct an object whose
// original constructor never ran, including when its initial words are poison.
let unusedHeap = ClawTokenHeap(), unusedController = unusedHeap.allocate(bytes:72)
unusedHeap.lookup(unusedController,words:18)!.update(repeating:0xdeadbeef,count:18)
var unused: ClawNativeResourceArchive? = try ClawNativeResourceArchive(heap:unusedHeap,borrowingController:unusedController)
let unusedTransport = unused!.transportAllocationTokens
unused!.shutdown()
precondition(unused!.lifecycle == .uninitialized && unused!.operationCalls.isEmpty)
unused = nil
precondition(unusedTransport.allSatisfy {unusedHeap.lookup($0,words:1) == nil})
precondition(Array(UnsafeBufferPointer(start:unusedHeap.lookup(unusedController,words:18)!,count:18)) == Array(repeating:UInt32(0xdeadbeef),count:18))
unusedHeap.free(unusedController)
print("PASS unconstructed borrowed controller remains untouched during shutdown and host release")

let shortHeap = ClawTokenHeap(), shortController = shortHeap.allocate(bytes:71)
do {
    _ = try ClawNativeResourceArchive(heap:shortHeap,borrowingController:shortController)
    fatalError("Accepted controller word padding as live bytes")
} catch ClawNativeResourceArchive.Failure.transport(_) {}
precondition(shortHeap.lookupBytes(shortController,count:71) != nil)
shortHeap.free(shortController)
print("PASS borrowed controller rejects containing-word padding beyond its exact allocation")
