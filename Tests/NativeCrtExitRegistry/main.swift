import Foundation
import CryptoKit

typealias Host = ClawNativeCanonicalHost
struct Range: Decodable { let name: String; let address: UInt32; let size: UInt32; let sha256: String }
struct Memory: Decodable { let parent: Int?; let pageChanges: [[Int]]; let ranges: [Range] }
struct Allocation: Codable, Equatable {
    let address: UInt32, requested: UInt32, capacity: UInt32, identity: UInt64
    let live: Bool
}
struct Section: Codable, Equatable {
    let address: UInt32, initialized: Bool, owner: UInt32, depth: UInt32
}
struct State: Decodable {
    let cpu: [String: UInt32], memory: Memory, thread: UInt32, filter: UInt32
    let allocationNext: UInt32, allocationIdentity: UInt64, allocations: [Allocation], sections: [Section]
    let registryBase: UInt32, registryNext: UInt32
}
struct Page: Decodable { let sha256: String, bytes: String }
struct Step: Decodable {
    let function: UInt32, returnPC: UInt32, arguments: [UInt32], frame: UInt32
    let before: Int, after: Int, completed: Bool, eventStart: Int, eventEnd: Int, entryStart: Int, entryEnd: Int
}
struct Event: Decodable {
    let function: UInt32, returnPC: UInt32, arguments: [UInt32], frame: UInt32
    let before: Int, after: Int, completed: Bool
    let result: UInt32?, halt: String?
}
struct Entry: Decodable {
    let function: UInt32, returnPC: UInt32, arguments: [UInt32], frame: UInt32
    let before: Int, after: Int, completed: Bool, rootStep: Int
}
struct Profile: Decodable {
    let schema: String, name: String, programSha256: String, mode: String
    let failMalloc: Bool, failResize: Int, physicalStop: Int, initial: Int
    let pages: [Page], states: [State], steps: [Step], events: [Event], entries: [Entry]
}
var checks = 0
func check(_ value: @autoclosure () -> Bool, _ message: String) {
    checks += 1
    if !value() { FileHandle.standardError.write(Data(("FAIL: " + message + "\n").utf8)); exit(1) }
}
func unhex(_ string: String) -> Data {
    let bytes = Array(string.utf8)
    func digit(_ c: UInt8) -> UInt8 { c <= 57 ? c - 48 : c - 87 }
    return Data(stride(from:0,to:bytes.count,by:2).map { digit(bytes[$0]) * 16 + digit(bytes[$0+1]) })
}
func hash(_ data: Data) -> String { SHA256.hash(data:data).map { String(format:"%02x",$0) }.joined() }
func cpu(_ c: ClawSourceContext) -> [String:UInt32] {
    ["eax":c.eax,"ebx":c.ebx,"ecx":c.ecx,"edx":c.edx,"esi":c.esi,"edi":c.edi,
     "ebp":c.ebp,"esp":c.esp,"eip":c.eip,"eflags":c.eflags,"fsHead":c.fsHead]
}
func context(_ c: [String:UInt32]) -> ClawSourceContext {
    .init(size:72,version:1,inputMask:0x7ff,outputMask:0x7ff,eax:c["eax"]!,ebx:c["ebx"]!,ecx:c["ecx"]!,
          edx:c["edx"]!,esi:c["esi"]!,edi:c["edi"]!,ebp:c["ebp"]!,esp:c["esp"]!,eip:c["eip"]!,
          eflags:c["eflags"]!,fsHead:c["fsHead"]!,preserveMask:0x472,reserved0:0,reserved1:0)
}
let profile = try JSONDecoder().decode(Profile.self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
let whole = CommandLine.arguments.contains("--whole")
check(profile.schema == "claw-original-crt-exit-registry-pages-v1", "frozen schema")
check(profile.programSha256 == "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263", "pinned original")
let pages = profile.pages.map { page -> Data in
    let bytes = unhex(page.bytes); check(hash(bytes) == page.sha256 && bytes.count == 4096,"lossless verified page")
    return bytes
}
var pageMap: [UInt32:Int] = [:], rebuiltThrough = -1
func rebuild(_ state: Int) {
    if state < rebuiltThrough { pageMap.removeAll(); rebuiltThrough = -1 }
    if state > rebuiltThrough {
        for index in (rebuiltThrough+1)...state {
            let m = profile.states[index].memory
            check(m.parent == (index == 0 ? nil : index - 1), "ordered delta parent")
            for change in m.pageChanges {
                check(change.count == 2 && change[1] >= 0 && change[1] < pages.count, "bounded page delta")
                pageMap[UInt32(change[0])] = change[1]
            }
        }
        rebuiltThrough = state
    }
}
func expectedRange(_ range: Range) -> Data {
    var result = Data()
    for address in stride(from:UInt64(range.address),to:UInt64(range.address)+UInt64(range.size),by:4096) {
        result.append(pages[pageMap[UInt32(address)]!])
    }
    check(result.count == range.size && hash(result) == range.sha256,"full reference range hash")
    return result
}
let heap = ClawTokenHeap(), host = Host(heap:heap)
rebuild(profile.initial)
var initialRanges: [String:Data] = [:], pinned: [(UInt32,UInt32)] = []
for range in profile.states[profile.initial].memory.ranges {
    let bytes = expectedRange(range); initialRanges[range.name] = bytes
    if range.name != "stack" && range.name != "heap" {
        let pointer = heap.storeBytes(token:range.address,count:range.size)
        bytes.withUnsafeBytes { UnsafeMutableRawPointer(pointer).copyMemory(from:$0.baseAddress!,byteCount:bytes.count) }
        pinned.append((range.address,range.size))
    }
}
let memory = ClawNativeCrtMemory(heap:heap,firstBase:0x62000000,storagePolicy:.frozenReferenceV1)
let services = try ClawNativeCrtServices(host:host,memory:memory,spans:pinned)
services.failMallocAttempt = profile.failMalloc ? 1 : 0
services.failResizeAttempt = profile.failResize
services.resizeMode = profile.mode == "moving" ? .move : .inPlace
services.mixedResize = profile.mode == "mixed"
services.beforeService = { owner, _ in
    if owner.attempts == profile.physicalStop { throw ClawNativeCrtServices.Failure.stopped }
}
if let flag=CommandLine.arguments.firstIndex(of:"--negative-leaf") {
    let kind=CommandLine.arguments[flag+1]
    var observedChild=false
    let accepted=host.withCrtSourceGraph(provider:services) { graph in
        var c=context(profile.states[profile.initial].cpu)
        let frame=c.esp
        func prepare(_ function: UInt32,_ pc: UInt32) {
            c.eip=function;c.esp=frame
            check(graph.writeStack(at:frame,data:withUnsafeBytes(of:pc.littleEndian) { Data($0) }),"negative prepared return")
        }
        check(graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:initialRanges["stack"]!),"negative initial stack")
        prepare(0x4a7b90,0x4a7d46)
        check(graph.invokeCrtSource(at:.initializeLocks,context:&c).completed,"negative real lock initialization")
        prepare(0x4a3610,0x4a5896)
        check(graph.invokeCrtSource(at:.initializeRegistry,context:&c).completed,"negative real registry initialization")
        let base=heap.lookup(0x545fd4,words:1)![0],next=heap.lookup(0x545fd0,words:1)![0]
        let baseline=try! memory.bytes(base),attempts=services.attempts
        graph.crtObserver = { observation in
            if observation.function==0x4a35f0 && !observation.physical && !observation.returning { observedChild=true }
        }
        prepare(kind=="cleanupFlags" ? 0x403570 : 0x501fc8,0x4a5896)
        let result=graph.invokeCrtRegistrationLeaf(c.eip,context:&c)
        check(!result.completed && result.eax==nil && host.fault != nil,"mutated leaf cannot report completion")
        let afterBody=["bodyEAX","cleanupECX","cleanupFlags"].contains(kind)
        check(observedChild==afterBody,"negative leaf exact child election boundary")
        if !afterBody {
            check(services.attempts==attempts && heap.lookup(0x545fd4,words:1)![0]==base &&
                  heap.lookup(0x545fd0,words:1)![0]==next && (try! memory.bytes(base))==baseline,
                  "invalid leaf call never reaches physical registry effects")
        } else {
            check(heap.lookup(0x545fd0,words:1)![0]==next+4 && services.sections[0x540e68]?.depth==0,
                  "body-result rejection retains prior actual source effects")
        }
        return true
    }
    check(accepted==true,"negative graph binding")
    print("{\"status\":\"pass\",\"negative_leaf\":\"\(kind)\",\"assertions\":\(checks)}")
    exit(0)
}
var comparedStates = Set<Int>()
var nativePages: [[String:Any]] = [], nativePageIDs: [Data:Int] = [:], nativePrevious: [UInt32:Data] = [:]
var nativeStates: [[String:Any]] = []
func compare(_ observation: Host.CrtObservation, state id: Int, label: String) {
    comparedStates.insert(id)
    let state = profile.states[id]; rebuild(id)
    check(cpu(observation.context) == state.cpu,label + " all CPU")
    let live = try! memory.liveSnapshot()
    let all = (memory.retired.map { ($0,false) } + live.map { ($0,true) }).sorted { $0.0.allocation.generation < $1.0.allocation.generation }
    let ledger = all.map { item,isLive in
        Allocation(address:item.allocation.base,requested:item.allocation.requested,capacity:item.allocation.capacity,
                   identity:item.allocation.generation,live:isLive)
    }
    check(ledger == state.allocations,label + " complete allocation owners")
    check(ledger.map(\.identity).max() ?? 0 == state.allocationIdentity,label + " generation")
    check(max(0x62000000,ledger.map { $0.address + $0.capacity + 16 }.max() ?? 0) == state.allocationNext,label + " physical bump")
    let sections = services.sections.values.sorted { $0.address < $1.address }.map {
        Section(address:$0.address,initialized:true,owner:$0.owner,depth:$0.depth)
    }
    check(sections == state.sections && services.logicalThread == state.thread,label + " full sections/thread")
    check(heap.lookup(0x545fd4,words:1)![0] == state.registryBase && heap.lookup(0x545fd0,words:1)![0] == state.registryNext,label + " source registry globals")
    check(state.filter == 0x70001111,label + " untouched filter boundary")
    var changes: [[UInt64]] = [], nativeRanges: [[String:Any]] = []
    for range in state.memory.ranges {
        let expected = expectedRange(range)
        let actual: Data
        if range.name == "stack" { actual = observation.stack }
        else if range.name == "heap" {
            var bytes = initialRanges["heap"]!
            for (item,_) in all {
                let offset = Int(item.allocation.base - range.address)
                check(offset >= 0 && offset + item.bytes.count <= bytes.count,label + " bounded owned capacity")
                bytes.replaceSubrange(offset..<offset+item.bytes.count,with:item.bytes)
            }
            actual = bytes
        } else {
            actual = Data(bytes:heap.lookupBytes(range.address,count:range.size)!,count:Int(range.size))
        }
        check(actual == expected,label + " complete " + range.name + " byte range")
        nativeRanges.append(["name":range.name,"address":range.address,"size":range.size,"sha256":hash(actual)])
        for offset in stride(from:0,to:actual.count,by:4096) {
            let address = range.address + UInt32(offset), page = actual.subdata(in:offset..<offset+4096)
            if nativePrevious[address] != page {
                let pid: Int
                if let existing = nativePageIDs[page] { pid = existing }
                else {
                    pid = nativePages.count; nativePageIDs[page] = pid
                    nativePages.append(["sha256":hash(page),"bytes":page.map { String(format:"%02x",$0) }.joined()])
                }
                changes.append([UInt64(address),UInt64(pid)]); nativePrevious[address] = page
            }
        }
    }
    let ledgerJSON = try! JSONSerialization.jsonObject(with:JSONEncoder().encode(ledger))
    let sectionsJSON = try! JSONSerialization.jsonObject(with:JSONEncoder().encode(sections))
    nativeStates.append(["referenceState":id,"cpu":cpu(observation.context),"allocations":ledgerJSON,
        "sections":sectionsJSON,"function":observation.function,"returnPC":observation.returnPC,
        "physical":observation.physical,"returning":observation.returning,"completed":observation.completed,
        "memory":["parent":nativeStates.isEmpty ? NSNull() : nativeStates.count-1 as Any,
                  "pageChanges":changes,"ranges":nativeRanges]])
}
var roots = 0, leafRoots = 0, physical = 0, sourceEntries = 0, observations = 0, referenceOnly = 0
var rootOutcomes: [[String:Any]] = []
var referenceOnlyInternal = 0, referenceAfterStop = 0
var eventIndex = 0, stepIndex = 0, stoppedState: Int?, seenEntries = Set<Int>()
let accepted = host.withCrtSourceGraph(provider:services) { graph in
    check(graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:initialRanges["stack"]!),"initial full stack")
    var current = context(profile.states[profile.initial].cpu)
    graph.crtObserver = { observation in
        let label = profile.name + " step " + String(stepIndex) + " fn " + String(observation.function,radix:16)
        observations += 1
        if observation.physical {
            let expected = profile.events[eventIndex]
            check(observation.function == expected.function && observation.returnPC == expected.returnPC && observation.arguments == expected.arguments,label + " physical election")
            check(observation.context.esp == profile.states[observation.returning ? expected.after : expected.before].cpu["esp"],label + " physical frame")
            compare(observation,state:observation.returning ? expected.after : expected.before,label:label)
            if observation.returning {
                check(observation.completed == expected.completed,label + " physical outcome")
                if !observation.completed { stoppedState = expected.after }
                physical += 1; eventIndex += 1
            }
        } else {
            let isRoot = observation.function == profile.steps[stepIndex].function
            if isRoot {
                let step = profile.steps[stepIndex]
                compare(observation,state:observation.returning ? stoppedState ?? step.after : step.before,label:label)
                if !observation.returning { sourceEntries += 1 }
            } else {
                let matches = profile.entries.indices.filter {
                    let entry = profile.entries[$0]
                    return entry.rootStep == stepIndex && entry.function == observation.function &&
                        entry.returnPC == observation.returnPC && entry.frame == (observation.returning ? profile.states[entry.before].cpu["esp"] : observation.context.esp)
                }
                check(matches.count == 1,label + " exact child source witness")
                let index = matches[0], entry = profile.entries[index]
                compare(observation,state:observation.returning ? stoppedState ?? entry.after : entry.before,label:label)
                if !observation.returning { sourceEntries += 1; seenEntries.insert(index) }
                if observation.function == 0x4a4860 { stoppedState = entry.before }
            }
        }
    }
    for (index,step) in profile.steps.enumerated() {
        let root = Host.CrtRoot(rawValue:step.function)
        if root == nil && !whole { break }
        if root == nil {
            check(step.returnPC==0x4a5896 && step.arguments.isEmpty,"prepared original leaf invocation")
            let entry=claw_canonical_lookup(step.function)!.pointee
            check(String(cString:entry.family)=="static_exit_registrations" && entry.argumentCount==0,
                  "admitted actual leaf source owner")
        }
        stepIndex = index
        var c = current
        c.esp = step.frame; c.eip = step.function
        check(cpu(c) == profile.states[step.before].cpu,"persistent source CPU before prepared root")
        let cpuBefore = cpu(c)
        check(graph.writeStack(at:step.frame,data:withUnsafeBytes(of:step.returnPC.littleEndian) { Data($0) }),"prepared real return")
        for (i,arg) in step.arguments.enumerated() {
            check(graph.writeStack(at:step.frame+4+UInt32(i)*4,data:withUnsafeBytes(of:arg.littleEndian) { Data($0) }),"prepared argument")
        }
        let completion: Host.Completion
        if let root { completion=graph.invokeCrtSource(at:root,context:&c) }
        else { completion=graph.invokeCrtRegistrationLeaf(step.function,context:&c);leafRoots += 1 }
        current = c
        roots += 1
        var outcome: [String:Any]=["step":index,"function":step.function,"returnPC":step.returnPC,
            "frame":step.frame,"arguments":step.arguments,"leaf":root==nil,"completed":completion.completed,
            "outputCPU":cpu(graph.crtOutput ?? c),"referenceState":stoppedState ?? step.after]
        outcome["eax"]=completion.eax.map { $0 as Any } ?? NSNull()
        if let fault=host.fault {
            outcome["stop"]=["address":fault.address,"code":fault.code,"diagnostic":String(describing:fault.diagnostic)]
        }
        rootOutcomes.append(outcome)
        check(completion.completed == (stoppedState == nil && step.completed),"root completion \(profile.name) \(index) fault=\(String(describing:host.fault))")
        if completion.completed { check(cpu(c) == profile.states[step.after].cpu,"complete output CPU") }
        else { check(host.fault != nil && graph.crtOutput != nil && graph.crtStack != nil,"explicit stopped prefix retained") }
        check(c.size == 72 && c.version == 1 && c.inputMask == 0x7ff && c.outputMask == 0x7ff && c.preserveMask == 0x472,"immutable source header")
        check(cpuBefore["eip"] == step.function,"prepared source input")
        for entryIndex in step.entryStart..<step.entryEnd where profile.entries[entryIndex].function != step.function && !seenEntries.contains(entryIndex) {
            referenceOnly += 1
            if let stop = stoppedState, profile.entries[entryIndex].before > stop { referenceAfterStop += 1 }
            else { referenceOnlyInternal += 1 }
        }
        if !completion.completed { break }
    }
    return true
}
check(accepted == true,"graph bound")
if whole { check(roots==profile.steps.count,"every declared frozen root step executed natively") }
if let flag = CommandLine.arguments.firstIndex(of:"--snapshot-dir") {
    let directory = URL(fileURLWithPath:CommandLine.arguments[flag+1],isDirectory:true)
    try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
    let result: [String:Any] = ["schema":"claw-native-crt-observations-pages-v1","profile":profile.name,
        "pages":nativePages,"states":nativeStates,"scope":whole ? "prepared original leaf roots with whole native CRT registry graph" : "only native-observed direct-root prefix states"]
    try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]).write(to:directory.appendingPathComponent(profile.name+"-native.json"),options:.atomic)
}
var nativeControls = 0
if CommandLine.arguments.contains("--controls") {
    func world() throws -> (Host,ClawNativeCrtServices) {
        let h = Host(heap:ClawTokenHeap())
        for range in profile.states[profile.initial].memory.ranges where range.name != "heap" && range.name != "stack" {
            let data = initialRanges[range.name]!, pointer = h.heap.storeBytes(token:range.address,count:range.size)
            data.withUnsafeBytes { UnsafeMutableRawPointer(pointer).copyMemory(from:$0.baseAddress!,byteCount:data.count) }
        }
        let m = ClawNativeCrtMemory(heap:h.heap,firstBase:0x62000000,storagePolicy:.frozenReferenceV1)
        return (h,try ClawNativeCrtServices(host:h,memory:m,spans:pinned))
    }
    func invoke(_ graph: Host.SourceGraph, _ root: Host.CrtRoot, _ args: [UInt32] = []) -> Host.Completion {
        var c = context(profile.states[profile.initial].cpu)
        c.eip = root.rawValue
        graph.writeStack(at:c.esp,data:withUnsafeBytes(of:root.returnPC.littleEndian) { Data($0) })
        for (index,value) in args.enumerated() {
            graph.writeStack(at:c.esp+4+UInt32(index)*4,data:withUnsafeBytes(of:value.littleEndian) { Data($0) })
        }
        return graph.invokeCrtSource(at:root,context:&c)
    }
    do {
        let (h,s) = try world()
        var saved: Host.SourceCrtRequest?
        let wrong = try ClawNativeCrtServices(host:h,memory:s.memory,spans:pinned)
        s.beforeService = { owner,request in
            saved = request
            check(!request.consume(for:h,provider:owner),"copied request cannot consume twice")
            check(!request.consume(for:h,provider:wrong),"wrong provider denied")
            let foreign = Host(heap:ClawTokenHeap())
            check(!request.consume(for:foreign,provider:owner),"wrong host denied")
            let finished = DispatchSemaphore(value:0)
            DispatchQueue.global().async {
                check(!request.consume(for:h,provider:owner),"foreign-thread lease denied")
                finished.signal()
            }
            finished.wait()
            nativeControls += 4
        }
        var retained: Host.SourceGraph?
        h.withCrtSourceGraph(provider:s) { graph in
            retained = graph
            check(invoke(graph,.initializeLocks).completed,"valid lease executes real lock initializer")
        }
        check(saved != nil && !saved!.consume(for:h,provider:s) && !saved!.validReturn(for:h),"request expires on return")
        nativeControls += 1
        var c = context(profile.states[profile.initial].cpu)
        c.eip = Host.CrtRoot.initializeLocks.rawValue
        check(!retained!.invokeCrtSource(at:.initializeLocks,context:&c).completed,"graph expires on return")
        nativeControls += 1
    }
    do {
        let (h,s) = try world()
        s.beforeService = { _,_ in
            var call = ClawCall(); call.function = 0x4a48e0
            _ = h.callNativeDependency(call)
        }
        h.withCrtSourceGraph(provider:s) { graph in
            check(!invoke(graph,.initializeLocks).completed,"reentry rejected")
            check(s.sections.isEmpty && h.fault?.diagnostic == .recursiveCanonicalCall,"sticky reentry before physical effect")
            let fault = h.fault
            check(!invoke(graph,.initializeRegistry).completed && h.fault == fault,"fault cannot be cleared by later root")
        }
        nativeControls += 3
    }
    do {
        let (h,s) = try world()
        h.withCrtSourceGraph(provider:s) { graph in
            graph.crtObserver = { _ in _ = invoke(graph,.initializeLocks) }
            check(!invoke(graph,.initializeLocks).completed,"observer reentry rejected")
            check(s.sections.isEmpty && h.fault?.diagnostic == .recursiveCanonicalCall,"observer rejection precedes all effects")
        }
        nativeControls += 2
    }
    do {
        let (h,s) = try world()
        let image = profile.states[profile.initial].memory.ranges.first { $0.name == "image" }!
        s.beforeService = { _,_ in
            h.heap.free(image.address)
            h.heap.storeBytes(token:image.address,count:image.size).update(repeating:0x89,count:Int(image.size))
        }
        h.withCrtSourceGraph(provider:s) { graph in
            check(!invoke(graph,.initializeLocks).completed,"exact-base source backing replacement rejected")
            check(s.sections.isEmpty,"replacement fails before initialization")
        }
        nativeControls += 2
    }
    do {
        let (h,s) = try world()
        s.afterService = { owner,request in
            if request.function == 0x4a48e0 {
                let a = try owner.memory.liveSnapshot().last!.allocation
                h.heap.free(a.base)
                h.heap.storeBytes(token:a.base,count:a.capacity).update(repeating:0x9a,count:Int(a.capacity))
            }
        }
        h.withCrtSourceGraph(provider:s) { graph in
            check(!invoke(graph,.initializeRegistry).completed,"post-allocation replacement rejected")
            check(h.heap.lookup(0x545fd4,words:1)![0] == 0 && h.heap.lookup(0x545fd0,words:1)![0] == 0,
                  "invalid allocation never reaches source publication")
        }
        check(h.heap.lookupBytes(0x62000000,count:128)![0] == 0x9a,"foreign replacement preserved")
        nativeControls += 3
    }
    // Each returned boundary invalidates its earlier successful binding check.
    // Prior legitimate effects remain; no source continuation or success result
    // can follow a return hook that replaces storage or attempts reentry.
    for boundary in ["root","child","physical"] {
        for action in ["replace","reenter"] {
            let (h,s) = try world()
            var fired = false
            h.withCrtSourceGraph(provider:s) { graph in
                check(invoke(graph,.initializeLocks).completed,"return-observer control setup locks")
                if boundary == "child" { check(invoke(graph,.initializeRegistry).completed,"return-observer child setup registry") }
                let attempts = s.attempts
                graph.crtObserver = { observation in
                    guard !fired, observation.returning, observation.completed else { return }
                    let matches = boundary == "root" ? (!observation.physical && observation.function == 0x4a3610) :
                        boundary == "child" ? (!observation.physical && observation.function == 0x4a7bc0) :
                        (observation.physical && observation.function == 0x4a48e0)
                    guard matches else { return }
                    fired = true
                    if action == "reenter" {
                        _ = invoke(graph,.initializeLocks)
                    } else if boundary == "physical" {
                        let allocation = try! s.memory.liveSnapshot().last!.allocation
                        h.heap.free(allocation.base)
                        h.heap.storeBytes(token:allocation.base,count:allocation.capacity)
                            .update(repeating:0x93,count:Int(allocation.capacity))
                    } else {
                        let image = profile.states[profile.initial].memory.ranges.first { $0.name == "image" }!
                        let bytes = Data(bytes:h.heap.lookupBytes(image.address,count:image.size)!,count:Int(image.size))
                        h.heap.free(image.address)
                        let replacement = h.heap.storeBytes(token:image.address,count:image.size)
                        bytes.withUnsafeBytes { UnsafeMutableRawPointer(replacement).copyMemory(from:$0.baseAddress!,byteCount:bytes.count) }
                    }
                }
                let result = invoke(graph,boundary == "child" ? .register : .initializeRegistry,
                                    boundary == "child" ? [0x425210] : [])
                check(fired && !result.completed && result.eax == nil && h.fault != nil,
                      boundary + " return " + action + " cannot report success")
                let firstFault = h.fault
                check(!invoke(graph,.initializeRegistry).completed && h.fault == firstFault,
                      boundary + " return " + action + " fault remains sticky")
                if action == "reenter" { check(h.fault?.diagnostic == .recursiveCanonicalCall,"returned observer reentry classification") }
                if boundary == "child" {
                    check(s.attempts == attempts + 1 && s.sections[0x540e68]?.depth == 1,
                          "child return stops before capacity query, append and release")
                    check(h.heap.lookup(0x545fd0,words:1)![0] == h.heap.lookup(0x545fd4,words:1)![0],
                          "child return does not advance registry")
                } else if boundary == "physical" {
                    check(s.attempts == attempts + 1 && h.heap.lookup(0x545fd4,words:1)![0] == 0 &&
                          h.heap.lookup(0x545fd0,words:1)![0] == 0,
                          "physical return stops before source publication")
                    if action == "replace" { check(h.heap.lookupBytes(0x62000000,count:128)![0] == 0x93,"physical observer foreign replacement survives") }
                }
                check(graph.crtOutput != nil && graph.crtStack != nil,"return observer failure retains copied prefix")
            }
            nativeControls += 1
        }
    }
    do {
        let (h,s) = try world()
        h.withCrtSourceGraph(provider:s) { graph in
            graph.crtObserver = { observation in
                if observation.returning && observation.completed && !observation.physical {
                    h.heap.lookup(0x546aa4,words:1)![0] = 0x77777777
                }
            }
            check(!invoke(graph,.initializeLocks).completed && h.fault != nil && !s.validCrtBinding(for:h),
                  "reviewer returning-root import-content repro rejected")
        }
        nativeControls += 1
    }
    do {
        let (h,s) = try world()
        h.withCrtSourceGraph(provider:s) { graph in
            check(invoke(graph,.initializeLocks).completed && invoke(graph,.initializeRegistry).completed,
                  "native consumer initialized through actual source roots")
            for index in 0..<40 {
                if index == 32 {
                    let base = h.heap.lookup(0x545fd4,words:1)![0], next = h.heap.lookup(0x545fd0,words:1)![0]
                    let before = try! s.memory.allocation(base), bytes = try! s.memory.bytes(base)
                    s.failResizeAttempt = 1
                    let failure = invoke(graph,.register,[0x425210])
                    check(failure.completed && failure.eax == UInt32.max,"source reports failed resize through actual failure branch")
                    check(h.heap.lookup(0x545fd4,words:1)![0] == base && h.heap.lookup(0x545fd0,words:1)![0] == next,
                          "failed source append retains publication")
                    check(try! s.memory.bytes(base) == bytes,"failed source append retains full bytes")
                    let after = try! s.memory.allocation(base)
                    check(after.identity === before.identity && after.requested == before.requested && after.capacity == before.capacity,
                          "failed source append retains owner record")
                    check(s.sections[0x540e68]?.depth == 0,"failed append releases actual lock13")
                    nativeControls += 1
                }
                check(invoke(graph,.register,[0x425210]).completed,"prepared repeated direct register")
                let base = h.heap.lookup(0x545fd4,words:1)![0], next = h.heap.lookup(0x545fd0,words:1)![0]
                check(next - base == UInt32(index+1)*4,"source next pointer advances once")
                check(try! s.memory.capacity(base) >= next-base,"source queries/grows actual capacity")
                check(h.heap.lookup(base,words:UInt32(index+1)).map { Array(UnsafeBufferPointer(start:$0,count:index+1)).allSatisfy { $0 == 0x425210 } } == true,
                      "source callback stores retained in order")
            }
            check(s.resizeAttempts >= 2 && s.sections[0x540e68]?.depth == 0,"consumer exercises real growth and lock release")
        }
        nativeControls += 1
    }
    if whole {
        for invalid in ["unknownLeaf","outerReturn"] {
            let (h,s)=try world()
            h.withCrtSourceGraph(provider:s) { graph in
                var c=context(profile.states[profile.initial].cpu)
                c.eip=invalid=="unknownLeaf" ? 0x501fc9 : 0x501fc8
                let pc: UInt32=invalid=="outerReturn" ? 0x4a5897 : 0x4a5896
                graph.writeStack(at:c.esp,data:withUnsafeBytes(of:pc.littleEndian) { Data($0) })
                check(!graph.invokeCrtRegistrationLeaf(c.eip,context:&c).completed && h.fault != nil,
                      "closed leaf identity/outer source frame rejection")
                check(s.attempts==0 && s.sections.isEmpty,"invalid leaf root cannot create source or physical effects")
            }
            nativeControls += 1
        }
        do {
            let (h,s)=try world();s.resizeMode = .move
            h.withCrtSourceGraph(provider:s) { graph in
                check(invoke(graph,.initializeLocks).completed && invoke(graph,.initializeRegistry).completed,"natural-growth source setup")
                let initialBase=h.heap.lookup(0x545fd4,words:1)![0]
                let initialIdentity=try! s.memory.allocation(initialBase).identity
                var rootsReturned=0,fired=false
                graph.crtObserver = { observation in
                    if observation.function==0x501fc8 && !observation.physical && observation.returning && observation.completed {
                        rootsReturned += 1
                        if rootsReturned==33 {
                            let base=h.heap.lookup(0x545fd4,words:1)![0],allocation=try! s.memory.allocation(base)
                            check(base != initialBase && allocation.identity !== initialIdentity,"natural source growth moved exact identity")
                            check(observation.context.esp==profile.states[profile.initial].cpu["esp"]!+4,"leaf caller frame survives natural movement")
                            let bytes=try! s.memory.bytes(base)
                            h.heap.free(base)
                            let replacement=h.heap.storeBytes(token:base,count:allocation.capacity)
                            for (index,byte) in bytes.enumerated() { replacement[index]=byte }
                            fired=true
                        }
                    }
                }
                for index in 0..<33 {
                    var c=context(profile.states[profile.initial].cpu);c.eip=0x501fc8
                    graph.writeStack(at:c.esp,data:withUnsafeBytes(of:UInt32(0x4a5896).littleEndian) { Data($0) })
                    let result=graph.invokeCrtRegistrationLeaf(c.eip,context:&c)
                    check(result.completed==(index<32),"natural-growth exact-base replacement rejects returning leaf success")
                }
                check(fired && h.fault != nil && rootsReturned==33,"natural-growth owner replacement control exercised")
            }
            nativeControls += 1
        }
    }
}
let summary: [String:Any]=["command":"native-crt-exit-registry","status":"pass","profile":profile.name,
    "roots":roots,"leaf_roots":leafRoots,"physical_events":physical,"observed_source_entries":sourceEntries,
    "reference_only_entries":referenceOnly,"reference_only_internal_entries":referenceOnlyInternal,
    "reference_entries_after_native_stop":referenceAfterStop,"compared_reference_states":comparedStates.count,
    "observations":observations,"native_controls":nativeControls,"assertions":checks,"root_outcomes":rootOutcomes,
    "scope":whole ? "prepared-original-leaf-roots" : "prepared-direct-root-prefixes"]
print(String(data:try JSONSerialization.data(withJSONObject:summary,options:[.sortedKeys]),encoding:.utf8)!)
