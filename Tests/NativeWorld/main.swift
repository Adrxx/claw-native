import Foundation
import Darwin
import zlib
setbuf(stdout,nil)
final class WorldFixture {
    let heap = ClawTokenHeap()
    let world: UInt32 = 0x60003000, parent: UInt32 = 0x10001000
    var currentRecords: [ClawNativeWorld.RawRecord] = [], recordIndex = 0
    var visited: [Data] = [], allocationTokens: [UInt32] = [], frees: [UInt32] = []
    init() {
        _ = heap.store(token:world,words:56)
        let scene = heap.store(token:parent,words:12)
        scene[2] = 0x60000000;scene[4] = 0x63000000;scene[9] = world
        _ = heap.store(token:0x63000000,words:44)
        let actors = heap.store(token:0x60000000,words:11)
        actors[0] = 0x513c20;actors[3] = parent;actors[4] = 0x5107bc;actors[10] = 10
    }
    var host: ClawSceneActorHost {
        ClawSceneActorHost(context:Unmanaged.passUnretained(self).toOpaque(),lookup:{ raw,token,count in
            guard let raw else { return nil };return Unmanaged<WorldFixture>.fromOpaque(raw).takeUnretainedValue().heap.lookup(token,words:count)
        },allocate:{ raw,bytes in
            guard let raw else { return 0 };let f=Unmanaged<WorldFixture>.fromOpaque(raw).takeUnretainedValue()
            let token=f.heap.allocate(bytes:bytes);f.allocationTokens.append(token);return token
        },free:{ raw,token in
            guard let raw else { return };let f=Unmanaged<WorldFixture>.fromOpaque(raw).takeUnretainedValue()
            f.frees.append(token);f.heap.free(token)
        },call:{ raw,call in
            guard let raw else { return 0 };return Unmanaged<WorldFixture>.fromOpaque(raw).takeUnretainedValue().service(call) ?? 0
        },readClock:{_ in 1000})
    }
    func service(_ call: ClawSceneActorCall) -> UInt32? {
        if call.function == 0x4d17e0 {
            precondition(recordIndex < currentRecords.count)
            let record = currentRecords[recordIndex];recordIndex += 1
            precondition(record.token == call.arguments.0)
            let offset=record.token & 3
            let source=heap.lookup(record.token & ~3,words:(record.byteCount+offset+3)/4)!
            let data=Data(bytes:UnsafeRawPointer(source).advanced(by:Int(offset)),count:Int(record.byteCount))
            precondition(data == record.bytes);visited.append(data)
            // Declared inspection-only population policy. Every actual source
            // callback/byte advance runs; no gameplay actor is asserted created.
            return record.byteCount
        }
        return nil
    }
    func grid(_ batch: ClawNativeWorld.GridBatch) -> UInt32? {
        currentRecords=batch.records;recordIndex=0
        var args=ClawSpatialGridArguments(),fault:UInt32=0,result:UInt32=0
        args.count=2;args.words.0=batch.firstRecordToken;args.words.1=batch.count
        precondition(claw_spatial_grid_entry(0x4d1620,batch.planeToken,args,host,&fault,&result)==1 && fault==0)
        precondition(recordIndex == batch.records.count)
        return result
    }
}
func decoded(_ data: Data) -> Data {
    let header=data.withUnsafeBytes { UInt32(littleEndian:$0.loadUnaligned(as:UInt32.self)) }
    let count=data.withUnsafeBytes { UInt32(littleEndian:$0.loadUnaligned(fromByteOffset:744,as:UInt32.self)) }
    var output=Data(count:Int(count)),length=uLongf(count)
    let result=output.withUnsafeMutableBytes { target in
        data.withUnsafeBytes { source in
            uncompress(target.bindMemory(to:UInt8.self).baseAddress!,&length,source.bindMemory(to:UInt8.self).baseAddress!.advanced(by:Int(header)),uLong(data.count-Int(header)))
        }
    }
    precondition(result==Z_OK && length==count)
    return data.prefix(Int(header))+output
}
let root=URL(fileURLWithPath:CommandLine.arguments[1])
let source=try Data(contentsOf:root.appendingPathComponent("LEVEL1/WORLDS/WORLD.WWD"))
let originalLevel1 = try Data(contentsOf:URL(fileURLWithPath:"work/native-world-agent/LEVEL1.WWD"))
precondition(source == originalLevel1)
let format=try ClawWorld(data:source) // Format-only comparison, never gameplay reference.
let f=WorldFixture()
let resources=try ClawActorResources(root:root,heap:f.heap,resolveEvent:{_ in 0})
let world=ClawNativeWorld(heap:f.heap,worldToken:f.world,parentToken:f.parent,host:f.host,
    populationPolicy:"Inspection only:1479 original4d17e0 calls captured; no gameplay actors instantiated",hooks:.init(
        imageRoot:{try resources.tileImages(name:$0)?.token},gridSetup:{f.grid($0)},service:{f.service($0)}))
precondition(world.construct() && world.flags==0)
precondition(world.load(compressedWWD:source) && world.fault==0 && world.unresolvedServices.isEmpty)
precondition(world.flags==3 && world.planeTokens.count==3 && world.mainIndex==1 && world.descriptionTokens.count==938)
let main=f.heap.lookup(world.mainPlaneToken!,words:86)!
precondition(main[33]==689 && main[34]==4723)
precondition(world.codecInputLengths[0].advertised==647102 && world.codecInputLengths[0].actual==UInt32(source.count-1524))
precondition(world.gridBatches.count==1 && world.gridBatches[0].count==1479 && f.visited.count==1479)
precondition(f.visited==format.planes.flatMap(\.objects).map(\.encodedRecord))
for (i,plane) in format.planes.enumerated() {
    let words=f.heap.lookup(world.planeTokens[i],words:86)!
    precondition(words[0]==0x513d40 && words[1]==UInt32(i) && words[2]==plane.flags)
    precondition(words[10]==plane.width && words[11]==plane.height && words[28]==640 && words[29]==480)
    let tiles=f.heap.lookup(words[8],words:UInt32(plane.tiles.count))!
    precondition(Array(UnsafeBufferPointer(start:tiles,count:plane.tiles.count))==plane.tiles.map{UInt32(bitPattern:Int32($0))})
    let rows=f.heap.lookup(words[9],words:UInt32(plane.height))!
    precondition(Array(UnsafeBufferPointer(start:rows,count:plane.height))==(0..<plane.height).map{UInt32($0*plane.width)})
}
let grid=f.heap.lookup(main[44],words:28)!
precondition((1...3).map{f.heap.lookup(grid[$0],words:17)![7]} == [4608,576,18432])
let descriptions=world.descriptionTokens
for (token,record) in zip(descriptions,format.tileDescriptions) {
    let words=f.heap.lookup(token,words:record.type==1 ? 4:9)!
    precondition(words[0]==(record.type==1 ? 0x513980:0x5139c8))
    precondition(words[1]==record.width && words[2]==record.height)
    if record.type==1 { precondition(words[3]==record.insideAttribute) }
    else {
        let rect=record.rect!
        precondition(Array(UnsafeBufferPointer(start:words.advanced(by:1),count:8)) == [record.width,record.height,record.outsideAttribute,record.insideAttribute,UInt32(bitPattern:Int32(rect.left)),UInt32(bitPattern:Int32(rect.top)),UInt32(bitPattern:Int32(rect.right)),UInt32(bitPattern:Int32(rect.bottom))])
    }
}
let planes=world.planeTokens, firstRecord=world.gridBatches[0].records[0]
precondition(f.heap.lookup(firstRecord.token & ~3,words:1)==nil && firstRecord.bytes==format.planes[1].objects[0].encodedRecord)
let imageTokens=try format.planes.flatMap(\.imageSets).map{try resources.tileImages(name:$0)!.token}
let beforeCleanup=f.allocationTokens.count
precondition(world.cleanup() && world.planeTokens.isEmpty && world.descriptionTokens.isEmpty && world.mainIndex==nil)
precondition(planes.allSatisfy{f.heap.lookup($0,words:1)==nil} && descriptions.allSatisfy{f.heap.lookup($0,words:1)==nil})
precondition(f.allocationTokens.prefix(beforeCleanup).filter{$0 != 0}.allSatisfy{f.heap.lookup($0,words:1)==nil})
precondition(imageTokens.allSatisfy{f.heap.lookup($0,words:1) != nil})
precondition(world.load(compressedWWD:source) && world.descriptionTokens.count==938 && world.planeTokens != planes)
precondition(world.destroy() && f.heap.lookup(f.world,words:56)![0]==0x50becc)
precondition(f.allocationTokens.filter{$0 != 0}.allSatisfy{f.heap.lookup($0,words:1)==nil})
print("PASS realLevel1 whole compressed load: sourceflags3/three planes/938 owned descriptions/1479 ordered raw callbacks; exact tiles/rows, center, retained reload and destruction")
// All14 source streams exercise the same native codec on actual file bounds.
let names=try JSONDecoder().decode([String].self,from:Data(contentsOf:URL(fileURLWithPath:"work/native-world-agent/worlds.json")))
var records=0
for name in names {
    let data=try Data(contentsOf:URL(fileURLWithPath:"work/native-world-agent/\(name).WWD"))
    let fixture=WorldFixture()
    let loader=ClawNativeWorld(heap:fixture.heap,worldToken:fixture.world,parentToken:fixture.parent,host:fixture.host,
        populationPolicy:"Inspection only: preserve all source record callbacks; no gameplay actors",hooks:.init(
            imageRoot:{_ in 0},gridSetup:{fixture.grid($0)},service:{fixture.service($0)}))
    precondition(loader.construct())
    precondition(loader.load(compressedWWD:data),"\(name): \(loader.failure ?? "source failure") fault\(loader.fault)")
    records += fixture.visited.count
    precondition(loader.codecCalls==1 && loader.destroy(deleteWorld:true))
    precondition(fixture.heap.lookup(fixture.world,words:1)==nil)
    precondition(fixture.allocationTokens.filter{$0 != 0}.allSatisfy{fixture.heap.lookup($0,words:1)==nil})
}
precondition(records==34784)
print("PASS14 original compressed worlds and34784 actual source record callbacks; all native world/grid allocations released")
let maskData=try Data(contentsOf:URL(fileURLWithPath:"work/native-world-agent/unaligned-mask.wwd"))
let maskFixture=WorldFixture()
let masked=ClawNativeWorld(heap:maskFixture.heap,worldToken:maskFixture.world,parentToken:maskFixture.parent,host:maskFixture.host,
    populationPolicy:"Synthetic source-description profile without object records",hooks:.init(imageRoot:{_ in nil},gridSetup:{maskFixture.grid($0)},service:{maskFixture.service($0)}))
precondition(masked.construct() && masked.load(compressedWWD:maskData))
let ownedMask=maskFixture.heap.lookup(masked.descriptionTokens[2],words:6)!
precondition(ownedMask[0]==0x513a10 && ownedMask[1]==4 && ownedMask[2]==4 && ownedMask[3]==2 && ownedMask[4]==16)
let maskToken=ownedMask[5]
precondition(Data(bytes:maskFixture.heap.lookup(maskToken,words:4)!,count:16)==Data(0..<16))
precondition(masked.cleanup(resetViewport:true) && maskFixture.heap.lookup(maskToken,words:1)==nil && maskFixture.heap.lookup(maskFixture.world,words:56)![4]==0x80000000)
precondition(masked.load(compressedWWD:maskData))
var invalid=maskData;invalid.withUnsafeMutableBytes{$0.storeBytes(of:UInt32(0x5f5),as:UInt32.self)}
precondition(!masked.load(compressedWWD:invalid) && masked.fault==0 && masked.planeTokens.isEmpty && masked.descriptionTokens.isEmpty)
precondition(masked.load(compressedWWD:maskData))
var zeroDecoded=maskData
zeroDecoded.withUnsafeMutableBytes{$0.storeBytes(of:UInt32(0),toByteOffset:744,as:UInt32.self)}
let codecCalls=masked.codecCalls
precondition(!masked.load(compressedWWD:zeroDecoded) && masked.fault==0 && masked.codecCalls==codecCalls && masked.planeTokens.isEmpty)
var uncompressed=decoded(maskData)
uncompressed.withUnsafeMutableBytes{$0.storeBytes(of:UInt32(1),toByteOffset:8,as:UInt32.self)}
precondition(masked.load(compressedWWD:uncompressed) && masked.flags==1 && masked.codecCalls==codecCalls)
precondition(masked.destroy())
print("PASS unaligned source type3→owned mask lifecycle, reset viewport and original invalid-header cleanup-before-validation/zero-decoded failure/uncompressed ownership paths")
