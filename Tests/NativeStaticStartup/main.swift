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
struct GlobalHandle: Codable, Equatable { let handle: UInt32, data: UInt32, size: UInt32, flags: UInt32, locks: UInt32 }
struct LocalAllocation: Codable, Equatable { let address: UInt32, requested: UInt32 }
struct SectionHistory: Codable, Equatable { let operation: String, address: UInt32, bytesPreserved: Bool }
struct NamedMessage: Codable, Equatable { let nameHex: String, identifier: UInt32 }
struct NamedMessageHistory: Codable, Equatable { let nameHex: String, result: UInt32; let reused: Bool, inserted: Bool; let callerReturnPC: UInt32 }
struct PlatformCall: Codable, Equatable { let name: String, returnPC: UInt32, arguments: [UInt32], result: UInt32 }
struct VersionCall: Codable, Equatable { let returnPC: UInt32, result: UInt32 }
struct DesktopAttempt: Codable, Equatable { let result: UInt32, phase: String, acquireReturnPC: UInt32 }
struct DesktopLease: Codable, Equatable { let handle: UInt32, kind: String, hwnd: UInt32, acquireReturnPC: UInt32 }
struct DesktopCall: Codable, Equatable { let name: String, returnPC: UInt32, arguments: [UInt32], result: UInt32, live: [UInt32] }
struct PlatformInputs: Codable {
    struct Stop: Codable { let selector: String, returnPC: String, occurrence: Int, phase: String }
    let version: UInt32, processVersion: UInt32
    let scalarPolicy: String, dcPolicy: String, releasePolicy: String, borrowedPolicy: String, messagePolicy: String
    let messageInitial: String?, capsPolicy: String?, physicalStop: Stop?
}
struct State: Decodable {
    let platformPolicyId: String?, platformHistory: [PlatformCall]?, versionHistory: [VersionCall]?
    let desktopDCAttempt: DesktopAttempt?, liveDesktopDCs: [DesktopLease]?, desktopDCHistory: [DesktopCall]?
    let borrowedIdentityTable: [String:[String:UInt32]]?, borrowedLookupHistory: [PlatformCall]?

    let namedMessages: [NamedMessage]?, nextNamedMessage: UInt32?, namedMessageHistory: [NamedMessageHistory]?
    let globalHandles: [GlobalHandle]?, localAllocations: [LocalAllocation]?, tlsIndices: [UInt32]?, tlsValues: [String:UInt32]?
    let nextGlobalHandle: UInt32?, nextTlsIndex: UInt32?, lastError: UInt32?, sectionHistory: [SectionHistory]?
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
    let nameBytesWithNul: String?, nameReadSha256: String?, physicalResult: UInt32?
}
struct Entry: Decodable {
    let returnPopBytes: UInt32?
    let function: UInt32, returnPC: UInt32, arguments: [UInt32], frame: UInt32
    let before: Int, after: Int, completed: Bool, rootStep: Int
}
struct CompilerEntry: Decodable {
    let function: UInt32, returnPC: UInt32, frame: UInt32
    let before: Int, after: Int, completed: Bool
}
struct InlineFsTransition: Codable {
    let address: UInt32, instruction: UInt32, state: Int, order: Int, effect: String
}
struct Profile: Decodable {
    struct AnalysisCut: Decodable {
        let address: UInt32, frame: UInt32, returnPC: UInt32, state: Int
        let first_instruction_executed: Bool, original_stop: Bool, native_missing_dependency_observed: Bool
    }
    let analysisCut: AnalysisCut?
    let compilerEntries: [CompilerEntry]?
    let physicalAfterEffectStop: Bool?
    let rangeAllocationPolicy: String?
    let strlenPolicy: String?, growthPolicy: String?
    let inlineFsTransitions: [InlineFsTransition]?
    let cursorSuccess: Bool?, stopSelector: String?, failSelector: String?
    let extendedStop: String?, extendedFail: String?
    let messageFailure: Bool?, messageStop: String?, messageInitial: String?, listRegistry: String?
    let declaredCallerInputs: [String:Bool]?
    let platformProfileInputs: PlatformInputs?, physicalPolicySha256: String?
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
check(["claw-original-static-startup-prefix-pages-v1","claw-original-static-startup-three-wrapper-pages-v2","claw-original-static-startup-seven-wrapper-pages-v3","claw-original-static-startup-fifteen-wrapper-pages-v4","claw-original-static-startup-thirtyfour-wrapper-pages-v5","claw-original-static-startup-application-shared-pages-v6","claw-original-static-startup-extended-records-pages-v7","claw-original-static-startup-list-records-pages-v8","claw-original-static-startup-final-records-pages-v9"].contains(profile.schema), "frozen schema")
check(profile.programSha256 == "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263", "pinned original")
let isFinal = profile.schema == "claw-original-static-startup-final-records-pages-v9"
let isList = isFinal || profile.schema == "claw-original-static-startup-list-records-pages-v8"
let isExtended = isList || profile.schema == "claw-original-static-startup-extended-records-pages-v7"
let isJoint = isExtended || profile.schema == "claw-original-static-startup-application-shared-pages-v6"
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
let sharedSections = isJoint ? ClawNativePhysicalSections(heap:heap,logicalThread:1) : nil
let services = try ClawNativeCrtServices(host:host,memory:memory,spans:pinned,sharedSections:sharedSections)
if isList {
    let initial=profile.states[profile.initial]
    try services.configureNamedMessages(initial:initial.namedMessages!.map { .init(name:unhex($0.nameHex),identifier:$0.identifier) },nextIdentifier:initial.nextNamedMessage!)
    services.failNamedMessage=isFinal ? profile.platformProfileInputs!.messagePolicy=="zero" : profile.messageFailure!
    if isFinal {
        let inputs=profile.platformProfileInputs!
        var policy=ClawNativeCrtServices.FinalPlatformPolicy()
        policy.version=inputs.version;policy.processVersion=inputs.processVersion
        policy.zeroScalars=inputs.scalarPolicy=="zero";policy.zeroCaps=inputs.capsPolicy=="zero"
        policy.acquireDC=inputs.dcPolicy != "zero";policy.releaseDC=inputs.releasePolicy != "zero"
        policy.zeroBorrowed=inputs.borrowedPolicy=="zero"
        try services.configureFinalPlatform(policy:policy)
        check(services.platformPolicyId==profile.physicalPolicySha256,"declared final physical policy identity")
    }
}
#if STATIC_APPLICATION
var mfcLocks: ClawNativeMfcLocks?, mfcMemory: ClawNativeMfcMemory?
if isJoint {
    func imports(_ slots: Set<UInt32>) -> [UInt32:UInt32] {
        Dictionary(uniqueKeysWithValues:slots.map { ($0,heap.lookup($0,words:1)![0]) })
    }
    let locks = try ClawNativeMfcLocks(host:host,sha256:profile.programSha256,
        initialBytes:Array(UnsafeBufferPointer(start:heap.lookupBytes(ClawNativeMfcLocks.imageBase,count:ClawNativeMfcLocks.imageCount)!,count:Int(ClawNativeMfcLocks.imageCount))),
        importTargets:imports(ClawNativeMfcLocks.importSlots),sharedSections:sharedSections,borrowExistingStorage:true)
    let mfc = try ClawNativeMfcMemory(host:host,sha256:profile.programSha256,
        importTargets:imports(Set(ClawNativeMfcMemory.importArities.keys)),locks:locks,sharedStorage:services,sharedSections:sharedSections)
    try mfc.registerManager(0x540af8); try mfc.registerTLSOwner(0x53ec9c)
    try mfc.registerTLSPublication(0x540af0); try mfc.registerModuleSingleton()
    try mfc.configureApplicationServices(importTargets:imports([0x546cd0,0x5469bc,0x5469c0]),
        cursorSuccess:profile.cursorSuccess!,x:-31,y:57,threadHandle:UInt32.max)
    let image=profile.states[profile.initial].memory.ranges.first { $0.name=="image" }!
    try mfc.registerApplicationReceiver(0x537008,inputRanges:[0x524eec:5],imageBase:image.address,imageCount:image.size)
    mfcLocks=locks;mfcMemory=mfc
}
#endif
services.failMallocAttempt = profile.failMalloc ? 1 : 0
services.failResizeAttempt = profile.failResize
services.resizeMode = profile.mode == "moving" ? .move : .inPlace
services.mixedResize = profile.mode == "mixed"
func isRangeMalloc(_ request: Host.SourceCrtRequest) -> Bool {
    request.function==0x4a48e0 && request.returnPC==0x4dbc0f && request.arguments==[44]
}
func isStringLength(_ request: Host.SourceCrtRequest) -> Bool {
    request.function==0x5469e4 && request.returnPC==0x4f662e && request.arguments==[0x534938]
}
func isRegistryGrowth(_ request: Host.SourceCrtRequest) -> Bool {
    request.function==0x4a9070 && request.returnPC==0x4a35a4 && request.arguments.count==2 && request.arguments[1]==144
}
var activeExtendedStringRange=false, extendedFactoryReturned=false, extendedRequestSelected=false
func extendedSelector(_ request: Host.SourceCrtRequest) -> String? {
    guard isExtended else { return nil }
    if activeExtendedStringRange && isRangeMalloc(request) { return "string-range" }
    if extendedFactoryReturned && request.function==0x4a9070 && request.returnPC==0x4a35a4 { return "registry" }
    return nil
}
var listFirstClassReturned=false, listRegistrySelected=false
func isListRegistryGrowth(_ request: Host.SourceCrtRequest) -> Bool {
    isList && listFirstClassReturned && request.function==0x4a9070 && request.returnPC==0x4a35a4
}
var finalStopSeen=0
func finalStopMatches(_ request: Host.SourceCrtRequest) -> Bool {
    guard isFinal,let stop=profile.platformProfileInputs?.physicalStop else { return false }
    return request.returnPC==UInt32(stop.returnPC.dropFirst(2),radix:16)
}
services.beforeService = { owner, request in
    if finalStopMatches(request) {
        finalStopSeen += 1
        if let stop=profile.platformProfileInputs?.physicalStop,finalStopSeen==stop.occurrence && stop.phase=="before" { throw ClawNativeCrtServices.Failure.stopped }
    }
    if isList && !isFinal && request.function==0x546c2c && profile.messageStop=="before" { throw ClawNativeCrtServices.Failure.stopped }
    if isListRegistryGrowth(request) && !listRegistrySelected && profile.listRegistry != nil {
        listRegistrySelected=true
        if profile.listRegistry=="zero" { owner.failResizeAttempt=owner.resizeAttempts+1 }
    }
    if let selector=extendedSelector(request),!extendedRequestSelected,
       (profile.extendedStop ?? profile.extendedFail)?.hasPrefix(selector)==true {
        extendedRequestSelected=true
        if profile.extendedStop==selector+"-before" { throw ClawNativeCrtServices.Failure.stopped }
        if profile.extendedFail==selector+"-zero" {
            if selector=="string-range" { owner.failMallocAttempt=owner.mallocAttempts+1 }
            else { owner.failResizeAttempt=owner.resizeAttempts+1 }
        }
    }
    if isJoint && request.function==0x4a48e0 && request.returnPC==0x4a56fc && profile.failSelector=="strdup-malloc" {
        owner.failMallocAttempt=owner.mallocAttempts+1
    }
    if isStringLength(request) && profile.strlenPolicy=="before-effect" { throw ClawNativeCrtServices.Failure.stopped }
    if isRegistryGrowth(request) {
        if profile.growthPolicy=="before-effect" { throw ClawNativeCrtServices.Failure.stopped }
        if profile.growthPolicy=="first-failure" && owner.resizeAttempts==0 { owner.failResizeAttempt=1 }
    }
    if isRangeMalloc(request) {
        if profile.rangeAllocationPolicy=="before-effect" { throw ClawNativeCrtServices.Failure.stopped }
        if profile.rangeAllocationPolicy=="fail-zero" { owner.failMallocAttempt=owner.mallocAttempts+1 }
    }
    if owner.attempts == profile.physicalStop && profile.physicalAfterEffectStop != true { throw ClawNativeCrtServices.Failure.stopped }
}
services.afterService = { _, request in
    if finalStopMatches(request),let stop=profile.platformProfileInputs?.physicalStop,finalStopSeen==stop.occurrence && stop.phase=="after" { throw ClawNativeCrtServices.Failure.stopped }
    if isList && !isFinal && request.function==0x546c2c && profile.messageStop=="after" { throw ClawNativeCrtServices.Failure.stopped }
    if isListRegistryGrowth(request) && listRegistrySelected && profile.listRegistry=="after" { throw ClawNativeCrtServices.Failure.stopped }
    if let selector=extendedSelector(request),extendedRequestSelected,profile.extendedStop==selector+"-after" {
        throw ClawNativeCrtServices.Failure.stopped
    }
    if isJoint && request.function==0x4a9070 && request.returnPC==0x4a35a4 && profile.stopSelector=="post-app-growth-after",
       let next=heap.lookup(0x545fd0,words:1)?[0],let base=heap.lookup(0x545fd4,words:1)?[0],next>=base,(next-base)/4>=34 {
        throw ClawNativeCrtServices.Failure.stopped
    }
    if (isStringLength(request) && profile.strlenPolicy=="after-effect") ||
       (isRegistryGrowth(request) && profile.growthPolicy=="after-effect") { throw ClawNativeCrtServices.Failure.stopped }
    if isRangeMalloc(request) && profile.rangeAllocationPolicy=="after-effect" { throw ClawNativeCrtServices.Failure.stopped }
    if profile.physicalAfterEffectStop == true && request.function==0x546aa4 &&
       request.returnPC==0x4a2d32 && request.arguments==[0x54072c] { throw ClawNativeCrtServices.Failure.stopped }
}
#if STATIC_APPLICATION
var seenPhysicalAPIs: [UInt32:Int] = [:]
if let mfc=mfcMemory {
    var sourceStrdupMalloc=false
    mfc.beforeSourceApplicationService = { request in
        sourceStrdupMalloc=request.function==0x4a48e0 && request.returnPC==0x4a56fc
    }
    mfc.beforeService = { slot, args in
        let seen=seenPhysicalAPIs[slot,default:0];seenPhysicalAPIs[slot]=seen+1
        let selector = slot==0x546cd0 ? "cursor" : slot==0x546aa8 && seen==0 ? "first-local" : slot==0x546b1c && seen==0 ? "first-global" : ""
        if !selector.isEmpty && profile.stopSelector==selector+"-before" { throw ClawNativeCrtServices.Failure.stopped }
    }
    mfc.afterService = { slot, args, result in
        let selector = slot==0x546cd0 ? "cursor" : slot==0x546aa8 && seenPhysicalAPIs[slot]==1 ? "first-local" : slot==0x546b1c && seenPhysicalAPIs[slot]==1 ? "first-global" : ""
        if !selector.isEmpty && profile.stopSelector==selector+"-after" { throw ClawNativeCrtServices.Failure.stopped }
    }
    mfc.failTLSSet=profile.failSelector=="tls-set"
    mfc.failAllocation = { slot in
        (slot==0x4a48e0 && sourceStrdupMalloc && profile.failSelector=="strdup-malloc") ||
        (slot==0x546a90 && profile.failSelector=="tls-alloc") ||
        (slot==0x546aa8 && seenPhysicalAPIs[slot]==1 && profile.failSelector=="first-local") ||
        (slot==0x546b1c && seenPhysicalAPIs[slot]==1 && profile.failSelector=="first-global")
    }
}
#endif
var comparedStates = Set<Int>()
var enteredSourceEntries = Set<Int>(), sourceFrames: [String:[Int]] = [:]
func sourceWitness(_ function: UInt32, _ pc: UInt32, _ frame: UInt32, returning: Bool, completed: Bool) -> Entry {
    let key="\(function):\(pc)"
    if returning {
        guard let index=sourceFrames[key]?.popLast() else { check(false,"source return has real entry \(key)");fatalError() }
        let entry=profile.entries[index]
        check(!completed || entry.completed && frame==entry.frame+4+(entry.returnPopBytes ?? 0),"real source return frame")
        return entry
    }
    let matches=profile.entries.indices.filter { !enteredSourceEntries.contains($0) && profile.entries[$0].function==function && profile.entries[$0].returnPC==pc && profile.entries[$0].frame==frame }
    check(!matches.isEmpty,"real source witness \(String(function,radix:16)) pc \(String(pc,radix:16)) frame \(String(frame,radix:16))")
    let index=matches.first!;enteredSourceEntries.insert(index);sourceFrames[key,default:[]].append(index)
    return profile.entries[index]
}
func listCompilerCandidates(_ entries: [CompilerEntry], returnPC: UInt32, frame: UInt32, returning: Bool, owner: Entry?) -> [CompilerEntry] {
    guard let owner else { return [] }
    return entries.filter {
        $0.returnPC==returnPC && (returning ? $0.frame-12==frame : $0.frame==frame) &&
        owner.before < $0.before && $0.after < owner.after
    }
}
var nativePages: [[String:Any]] = [], nativePageIDs: [Data:Int] = [:], nativePrevious: [UInt32:Data] = [:]
var nativeStates: [[String:Any]] = []
func compare(_ observation: Host.CrtObservation, state id: Int, label: String, tableMutation: Bool = false) {
    if ["claw-original-static-startup-fifteen-wrapper-pages-v4","claw-original-static-startup-thirtyfour-wrapper-pages-v5","claw-original-static-startup-application-shared-pages-v6","claw-original-static-startup-extended-records-pages-v7","claw-original-static-startup-list-records-pages-v8","claw-original-static-startup-final-records-pages-v9"].contains(profile.schema) {
        check(heap.lookup(0,words:1)?[0]==observation.context.fsHead,"executed CPU FS agrees with actual guest thread word")
    }
    comparedStates.insert(id)
    let state = profile.states[id]; rebuild(id)
    check(cpu(observation.context) == state.cpu,label + " all CPU profile \(profile.name) state \(id) actual \(cpu(observation.context)) expected \(state.cpu)")
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
    var jointState: [String:Any] = [:]
    if isList {
        let messages=services.namedMessages.map { NamedMessage(nameHex:$0.name.map { String(format:"%02x",$0) }.joined(),identifier:$0.identifier) }
        let history=services.namedMessageHistory.map { NamedMessageHistory(nameHex:$0.name.map { String(format:"%02x",$0) }.joined(),result:$0.result,reused:$0.reused,inserted:$0.inserted,callerReturnPC:$0.callerReturnPC) }
        check(messages==state.namedMessages && services.nextNamedMessage==state.nextNamedMessage,label+" actual named-message ownership")
        check(history==state.namedMessageHistory,label+" actual named-message history")
        jointState=["namedMessages":try! JSONSerialization.jsonObject(with:JSONEncoder().encode(messages)),
            "nextNamedMessage":services.nextNamedMessage,"namedMessageHistory":try! JSONSerialization.jsonObject(with:JSONEncoder().encode(history))]
    }
    if isFinal {
        func platform(_ calls: [ClawNativeCrtServices.PlatformCall]) -> [PlatformCall] {
            calls.map { PlatformCall(name:$0.name,returnPC:$0.returnPC,arguments:$0.arguments,result:$0.result) }
        }
        func encoded<T:Encodable>(_ value:T) -> Any { try! JSONSerialization.jsonObject(with:JSONEncoder().encode(value)) }
        let history=platform(services.platformHistory),borrowed=platform(services.borrowedLookupHistory)
        let versions=services.versionHistory.map { VersionCall(returnPC:$0.returnPC,result:$0.result) }
        let attempt=services.desktopDCAttempt.map { DesktopAttempt(result:$0.result,phase:$0.phase,acquireReturnPC:$0.acquireReturnPC) }
        let leases=services.liveDesktopDCs.map { DesktopLease(handle:$0.handle,kind:$0.kind,hwnd:$0.hwnd,acquireReturnPC:$0.acquireReturnPC) }
        let dcHistory=services.desktopDCHistory.map { DesktopCall(name:$0.name,returnPC:$0.returnPC,arguments:$0.arguments,result:$0.result,live:$0.live) }
        check(services.platformPolicyId==state.platformPolicyId && history==state.platformHistory && versions==state.versionHistory,label+" actual platform/version history")
        check(attempt==state.desktopDCAttempt && leases==state.liveDesktopDCs && dcHistory==state.desktopDCHistory,label+" actual desktop DC ownership/history")
        check(services.borrowedIdentityTable==state.borrowedIdentityTable && borrowed==state.borrowedLookupHistory,label+" actual borrowed identity/history")
        jointState.merge(["platformPolicyId":services.platformPolicyId!,"platformHistory":encoded(history),"versionHistory":encoded(versions),
            "desktopDCAttempt":attempt.map { encoded($0) } ?? NSNull(),"liveDesktopDCs":encoded(leases),"desktopDCHistory":encoded(dcHistory),
            "borrowedIdentityTable":services.borrowedIdentityTable,"borrowedLookupHistory":encoded(borrowed)]) { _,new in new }
    }
    #if STATIC_APPLICATION
    if let mfc=mfcMemory,let sharedSections {
        let handles=mfc.blocks.map { GlobalHandle(handle:$0.handle,data:$0.data,size:$0.size,flags:$0.flags,locks:$0.locks) }
        let locals=mfc.localRequestedSizes.sorted { $0.key<$1.key }.map { LocalAllocation(address:$0.key,requested:$0.value) }
        let values=Dictionary(uniqueKeysWithValues:mfc.logicalTLSValues.map { (String($0.key),$0.value) })
        let history=sharedSections.deleted.map { SectionHistory(operation:"delete",address:$0,bytesPreserved:true) }
        check(handles==state.globalHandles && locals==state.localAllocations,label+" actual global/local ownership")
        check(mfc.tlsIndices==state.tlsIndices && values==state.tlsValues,label+" actual TLS indices/values")
        check(mfc.nextGlobalHandle==state.nextGlobalHandle && mfc.nextTLSIndex==state.nextTlsIndex && mfc.lastErrorValue==state.lastError,label+" actual physical counters")
        check(history==state.sectionHistory,label+" actual section deletion history")
        jointState.merge(["globalHandles":try! JSONSerialization.jsonObject(with:JSONEncoder().encode(handles)),
            "localAllocations":try! JSONSerialization.jsonObject(with:JSONEncoder().encode(locals)),
            "tlsIndices":mfc.tlsIndices,"tlsValues":values,"nextGlobalHandle":mfc.nextGlobalHandle,
            "nextTlsIndex":mfc.nextTLSIndex,"lastError":mfc.lastErrorValue,
            "sectionHistory":try! JSONSerialization.jsonObject(with:JSONEncoder().encode(history))]) { _,new in new }
    }
    #endif
    var changes: [[UInt64]] = [], nativeRanges: [[String:Any]] = []
    for range in state.memory.ranges {
        var expected = expectedRange(range)
        if tableMutation && range.name == "image" {
            let offset = Int(0x522018-range.address)
            check(expected.subdata(in:offset..<offset+4)==Data([0x22,0x37,0x50,0]),"original consumed slot before controlled mutation")
            expected.replaceSubrange(offset..<offset+4,with:Data([0x48,0x37,0x50,0]))
        }
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
    var nativeState: [String:Any] = ["referenceState":id,"cpu":cpu(observation.context),"allocations":ledgerJSON,
        "sections":sectionsJSON,"function":observation.function,"returnPC":observation.returnPC,
        "physical":observation.physical,"returning":observation.returning,"completed":observation.completed,
        "memory":["parent":nativeStates.isEmpty ? NSNull() : nativeStates.count-1 as Any,
                  "pageChanges":changes,"ranges":nativeRanges]]
    if tableMutation { nativeState["authorityMutation"] = ["address":UInt32(0x522018),"before":UInt32(0x503722),"after":UInt32(0x503748)] }
    nativeState.merge(jointState) { _,new in new }
    nativeStates.append(nativeState)
}
// Prepared real outer caller inputs. Inside the bounded table, the admitted
// source walker executes actual null skips, indirect CALLs, constructors and tails.
var eventIndex=0,staticBoundaries=0,wrappers=0,stops=0
let authorityControl=ProcessInfo.processInfo.environment["CLAW_NATIVE_STATIC_AUTHORITY"] ?? ""
let tableAuthority = authorityControl.hasSuffix("-table")
let allowedAuthority = ["","entry-reentry","return-reentry","entry-owner","return-owner"] +
    (["claw-original-static-startup-seven-wrapper-pages-v3","claw-original-static-startup-fifteen-wrapper-pages-v4","claw-original-static-startup-thirtyfour-wrapper-pages-v5","claw-original-static-startup-application-shared-pages-v6","claw-original-static-startup-extended-records-pages-v7","claw-original-static-startup-list-records-pages-v8","claw-original-static-startup-final-records-pages-v9"].contains(profile.schema) ? ["entry-table","return-table"] : [])
check(allowedAuthority.contains(authorityControl),"known authority control")
let tableOwnerIdentity = heap.containingAllocationIdentity(at:0x522018,count:4)
var authorityTriggered=false
let threadHeadStorage=profile.states[profile.initial].memory.ranges.first { $0.name=="thread" }!.address
let execute: (Host.SourceGraph) -> Void = { graph in
    graph.crtObserver = { observation in
        guard observation.physical else {
            guard isJoint && observation.moduleBoundary else { return }
            if observation.function==0x4a48c0 {
                if observation.returning && !observation.completed { return }
                let activeOwner=sourceFrames.values.compactMap { $0.last }.map { profile.entries[$0] }.max { $0.before < $1.before }
                let matches=isList ? listCompilerCandidates(profile.compilerEntries ?? [],returnPC:observation.returnPC,frame:observation.context.esp,returning:observation.returning,owner:activeOwner) : (profile.compilerEntries ?? []).filter { $0.returnPC==observation.returnPC && (observation.returning ? $0.frame-12==observation.context.esp : $0.frame==observation.context.esp) }
                check(matches.count==1,"unique original module compiler receipt PC \(String(observation.returnPC,radix:16)) frame \(String(observation.context.esp,radix:16)) physical \(eventIndex) candidates \(matches.count)")
                compare(observation,state:observation.returning ? matches[0].after : matches[0].before,label:"module compiler")
            } else {
                let entry=sourceWitness(observation.function,observation.returnPC,observation.context.esp,returning:observation.returning,completed:observation.completed)
                if !observation.returning || observation.completed { compare(observation,state:observation.returning ? entry.after : entry.before,label:"module source") }
            }
            staticBoundaries += 1
            return
        }
        check(eventIndex<profile.events.count,"physical event inventory")
        let event=profile.events[eventIndex]
        check(observation.function==event.function && observation.returnPC==event.returnPC &&
              observation.arguments==event.arguments,"real physical request order")
        if isList && event.function==0x546c2c {
            let name=unhex(event.nameBytesWithNul!)
            check(name.count<=256 && name.last==0 && hash(name)==event.nameReadSha256,"original bounded raw ANSI request")
            check(Data(bytes:heap.lookupBytes(event.arguments[0],count:UInt32(name.count))!,count:name.count)==name,"actual named-message argument bytes")
            if observation.returning,let result=event.result ?? event.physicalResult {
                check(services.namedMessageHistory.last?.result==result,"actual named-message physical result")
            }
        }
        if isJoint && observation.returning { check(observation.completed==event.completed,"physical completion \(eventIndex) fn \(String(event.function,radix:16)) actual \(observation.completed) expected \(event.completed) fault \(String(describing:host.fault))") }
        compare(observation,state:observation.returning ? event.after : event.before,label:"physical")
        if observation.returning { eventIndex += 1 }
    }
    graph.staticObserver = { observation in
        if isList && observation.target==0x50240a && observation.returning && observation.completed { listFirstClassReturned=true }
        if isExtended {
            if observation.target==0x440f30 { activeExtendedStringRange = !observation.returning }
            if observation.target==0x440ee0 && observation.returning && observation.completed { extendedFactoryReturned=true }
        }
        if observation.target==0x4a48c0 {
            let entries=(profile.compilerEntries ?? []).filter {
                $0.returnPC==observation.returnPC && (observation.returning ?
                    $0.frame-12==observation.context.esp : $0.frame==observation.context.esp)
            }
            check(entries.count==1,"unique genuine compiler scope")
            let entry=entries[0]
            check(observation.returnPC==entry.returnPC && (observation.returning ?
                observation.context.esp==entry.frame-12 : observation.context.esp==entry.frame),"compiler physical frame transfer")
            let observed=Host.CrtObservation(function:observation.target,target:observation.target,returnPC:observation.returnPC,
                arguments:[],context:observation.context,stack:observation.stack,physical:false,
                returning:observation.returning,completed:observation.completed)
            compare(observed,state:observation.returning ? entry.after : entry.before,label:"compiler scope")
            staticBoundaries += 1
            return
        }
        if let cut=profile.analysisCut,observation.target==cut.address {
            let expectedCut: (UInt32, UInt32)
            switch profile.schema {
            case "claw-original-static-startup-list-records-pages-v8": expectedCut=(0x502dac,0x502d35)
            case "claw-original-static-startup-extended-records-pages-v7": expectedCut=(0x4f709b,0x502419)
            case "claw-original-static-startup-application-shared-pages-v6": expectedCut=(0x440ee0,0x43d34c)
            case "claw-original-static-startup-thirtyfour-wrapper-pages-v5":
                expectedCut = profile.rangeAllocationPolicy=="fail-zero" ? (0x4dc680,0x4dbc4c) : (0x50257f,0x4251ff)
            case "claw-original-static-startup-fifteen-wrapper-pages-v4":
                expectedCut = profile.rangeAllocationPolicy=="fail-zero" ? (0x4dc680,0x4dbc4c) : (0x4f65f2,0x40b83f)
            case "claw-original-static-startup-seven-wrapper-pages-v3": expectedCut=(0x403ad0,0x403564)
            default: expectedCut=(0x4a2cf1,0x502c95)
            }
            guard cut.address==expectedCut.0 && cut.returnPC==expectedCut.1 &&
                  !cut.first_instruction_executed && !cut.original_stop && !cut.native_missing_dependency_observed &&
                  !observation.returning && observation.returnPC==cut.returnPC && observation.context.esp==cut.frame else {
                check(false,"declared finite original pre-instruction observation cut"); return
            }
            let observed=Host.CrtObservation(function:observation.target,target:observation.target,
                returnPC:observation.returnPC,arguments:[],context:observation.context,stack:observation.stack,
                physical:false,returning:false,completed:false)
            compare(observed,state:cut.state,label:"actual original pre-instruction cut")
            staticBoundaries += 1
            // The reference intentionally ends before the next instruction.
            // This fixture requests a HALT, not an original or native missing-body failure.
            host.fail(UInt32(CLAW_FAULT_HALT),at:observation.target,diagnostic:.nativeFault)
            return
        }
        let entry: Entry
        if isJoint { entry=sourceWitness(observation.target,observation.returnPC,observation.context.esp,returning:observation.returning,completed:observation.completed) }
        else {
            let matches=profile.entries.filter {
                $0.function==observation.target && $0.returnPC==observation.returnPC &&
                (observation.returning ? !observation.completed || $0.frame+4+($0.returnPopBytes ?? 0)==observation.context.esp : $0.frame==observation.context.esp)
            }
            check(matches.count==1,"unique real source edge witness");entry=matches[0]
        }
        let observed=Host.CrtObservation(function:observation.target,target:observation.target,
            returnPC:observation.returnPC,arguments:[],context:observation.context,stack:observation.stack,
            physical:false,returning:observation.returning,completed:observation.completed)
        if !observation.returning || observation.completed {
            compare(observed,state:observation.returning ? entry.after : entry.before,label:"static edge")
        }
        if observation.caller==0x4a5880 && observation.returning && observation.completed { wrappers += 1 }
        staticBoundaries += 1
        if !authorityControl.isEmpty,!authorityTriggered,observation.target==(tableAuthority ? 0x50372c : 0x501fc7),
           observation.returning==authorityControl.hasPrefix("return-") {
            authorityTriggered=true
            if tableAuthority {
                check(heap.lookup(0x522018,words:1)?[0]==0x503722 && tableOwnerIdentity != nil,"consumed table slot has original bytes and owner")
                heap.lookup(0x522018,words:1)![0]=0x503748
                check(heap.containingAllocationIdentity(at:0x522018,count:4) === tableOwnerIdentity,"table mutation retains allocation owner")
                compare(observed,state:observation.returning ? entry.after : entry.before,label:"actual controlled table mutation",tableMutation:true)
            } else if authorityControl.hasSuffix("reentry") {
                var nested=observation.context
                check(!graph.invokeStaticTablePrefix(context:&nested).completed,"observer reentry denied")
            } else {
                let image=profile.states[profile.initial].memory.ranges.first { $0.name=="image" }!
                let bytes=Data(bytes:heap.lookupBytes(image.address,count:image.size)!,count:Int(image.size))
                heap.free(image.address)
                let replacement=heap.storeBytes(token:image.address,count:image.size)
                bytes.withUnsafeBytes { UnsafeMutableRawPointer(replacement).copyMemory(from:$0.baseAddress!,byteCount:bytes.count) }
                check(!services.validCrtBinding(for:host),"same-byte owner replacement expires binding")
            }
        }
    }
    func prepare(_ state:Int) {
        rebuild(state)
        let range=profile.states[state].memory.ranges.first { $0.name=="stack" }!
        check(graph.writeStack(at:range.address,data:expectedRange(range)),"explicit prepared caller stack")
    }
    for step in profile.steps {
        guard let root=Host.CrtRoot(rawValue:step.function) else { continue }
        prepare(step.before)
        var c=context(profile.states[step.before].cpu)
        let completion=graph.invokeCrtSource(at:root,context:&c)
        if completion.completed {
            let observed=Host.CrtObservation(function:step.function,target:step.function,returnPC:step.returnPC,
                arguments:step.arguments,context:c,stack:graph.stackSnapshot()!,physical:false,returning:true,completed:true)
            compare(observed,state:step.after,label:"CRT prerequisite")
        } else {
            // The native host stops at the real missing quick-exit source
            // body; it does not claim the later original ExitProcess path.
            check(host.fault?.address==0x4a4860,"honest missing fatal descendant")
            let entry=profile.entries.first { $0.function==0x4a4860 }!
            let observed=Host.CrtObservation(function:0x4a4860,target:0x4a4860,returnPC:entry.returnPC,
                arguments:entry.arguments,context:graph.crtOutput!,stack:graph.crtStack!,
                physical:false,returning:false,completed:false)
            compare(observed,state:entry.before,label:"genuine missing fatal source CPU and stack prefix")
            stops += 1
            return
        }
    }
    if let step=profile.steps.first(where: { $0.function==0x4a5880 }) {
        prepare(step.before)
        var c=context(profile.states[step.before].cpu);c.preserveMask=0
        let completion=graph.invokeStaticTablePrefix(context:&c)
        if completion.completed {
            let observed=Host.CrtObservation(function:step.function,target:step.function,returnPC:step.returnPC,
                arguments:step.arguments,context:c,stack:graph.stackSnapshot()!,physical:false,returning:true,completed:true)
            compare(observed,state:step.after,label:"whole original source table walker")
        } else {
            check(host.fault != nil,"explicit failed table outcome")
            if !authorityControl.isEmpty {
                check(authorityTriggered && host.fault?.code==UInt32(CLAW_FAULT_ABI),"authority refusal is explicit")
                if tableAuthority {
                    check(wrappers==5 && eventIndex==21 && services.attempts==21,"late table refusal before sixth registration or later effect")
                    check(heap.lookup(0x522018,words:1)?[0]==0x503748 && heap.containingAllocationIdentity(at:0x522018,count:4) === tableOwnerIdentity,"table refusal preserves actual mutation and original owner")
                    check(heap.lookup(0x545fd0,words:1)![0]-heap.lookup(0x545fd4,words:1)![0]==20,"exactly five callback registrations remain")
                } else {
                    check(wrappers==0 && eventIndex==5 && services.attempts==5,"no registration or later physical effect after refusal")
                }
                stops += 1
                return
            }
            check(isJoint && (profile.stopSelector != nil || profile.failSelector != nil || profile.extendedStop != nil || profile.extendedFail != nil || profile.messageStop != nil || profile.listRegistry != nil || profile.platformProfileInputs?.physicalStop != nil) || profile.physicalStop != 0 || profile.physicalAfterEffectStop == true || profile.analysisCut != nil || [profile.rangeAllocationPolicy,profile.strlenPolicy,profile.growthPolicy].contains(where: { ["before-effect","after-effect"].contains($0 ?? "") }),
                  "success profiles finish table walker: \(String(describing:host.fault)) CPU \(cpu(c)) boundaries \(staticBoundaries) physical \(eventIndex)")
            let state:Int
            if isJoint {
                check(eventIndex==profile.events.count,"joint failure reaches every original physical event: fault \(String(describing:host.fault)), physical \(eventIndex)/\(profile.events.count)")
                if ["module-local-allocation-zero","manager-global-allocation-zero","mfc-tls-index-exhausted","extended119-first-local-allocation-zero","list133-first-local-allocation-zero","final144-first-local-allocation-zero"].contains(profile.name) {
                    check(profile.events.last!.function==0x546958 && host.fault?.code==UInt32(CLAW_FAULT_HALT) && host.fault?.address==0x546958,
                          "allocation failure reaches actual nonreturning physical RaiseException: \(String(describing:host.fault))")
                }
            }
            if let cut=profile.analysisCut {
                check(host.fault?.code==UInt32(CLAW_FAULT_HALT) && host.fault?.address==cut.address && c.eip==cut.address,"explicit original pre-instruction observer cut")
                state=cut.state
            } else {
                check(!profile.events.last!.completed,"original physical stop outcome")
                state=profile.events.last!.after
            }
            let observed=Host.CrtObservation(function:c.eip,target:c.eip,returnPC:step.returnPC,
                arguments:[],context:c,stack:graph.crtStack!,physical:false,returning:false,completed:false)
            compare(observed,state:state,label:"actual deepest table child prefix (fault \(String(describing:host.fault)), physical \(eventIndex)/\(profile.events.count))")
            stops += 1
        }
    }
}
let accepted: Void?
#if STATIC_APPLICATION
if let mfc=mfcMemory { accepted=host.withStaticApplicationSourceGraph(crt:services,application:mfc,threadHeadStorage:threadHeadStorage,scope:isFinal ? .final144 : isList ? .list133 : isExtended ? .extended119 : .application58,body:execute) }
else { accepted=host.withCrtSourceGraph(provider:services,threadHeadStorage:threadHeadStorage,body:execute) }
#else
accepted=host.withCrtSourceGraph(provider:services,threadHeadStorage:threadHeadStorage,body:execute)
#endif
check(accepted != nil,"bound shared owner graph")
if authorityControl.isEmpty && profile.name.hasPrefix("two-wrappers") {
    check(wrappers==2 && stops==0 && eventIndex==profile.events.count && staticBoundaries==12,
          "both complete wrappers and all physical/static boundaries required")
}
if authorityControl.isEmpty && profile.name.hasPrefix("three-wrappers") {
    check(wrappers==3 && stops==0 && eventIndex==profile.events.count && staticBoundaries==26,
          "all three complete wrappers and all source/compiler/physical boundaries required")
}
if authorityControl.isEmpty && profile.name.hasPrefix("seven-wrappers") {
    check(wrappers==7 && stops==0 && eventIndex==profile.events.count && eventIndex==27 && staticBoundaries==50,
          "all seven complete wrappers and all source/compiler/physical boundaries required")
}
if authorityControl.isEmpty && profile.name.hasPrefix("fifteen-wrappers") {
    check(wrappers==15 && stops==0 && eventIndex==59 && eventIndex==profile.events.count && staticBoundaries==114,
          "fifteen completed exported constructor chains and actual source/physical boundaries required")
}
if authorityControl.isEmpty && profile.name.hasPrefix("thirtyfour-wrappers") {
    check(wrappers==34 && stops==0 && eventIndex==136 && eventIndex==profile.events.count,
          "thirty-four complete wrappers and actual physical inventory required")
}
if isJoint && authorityControl.isEmpty && stops==0 {
    check(wrappers==(isFinal ? 144 : isList ? 133 : isExtended ? 119 : 58) && eventIndex==profile.events.count,"complete bounded source returns and full physical inventory")
}
var result:[String:Any]=["command":"native-static-startup","status":"pass","profile":profile.name,
    "checks":checks,"wrappers":wrappers,"static_boundaries":staticBoundaries,"physical_events":eventIndex,
    "honest_stops":stops,"native_table_walker":true,"gameplay":false,"authority_control":authorityControl]
if profile.schema=="claw-original-static-startup-thirtyfour-wrapper-pages-v5" || isJoint {
    let base=heap.lookup(0x545fd4,words:1)![0], next=heap.lookup(0x545fd0,words:1)![0]
    check(next>=base && (next-base)%4==0,"actual registry callback count remains bounded")
    let registrations=(next-base)/4
    result["registrations"]=registrations
    if isJoint && authorityControl.isEmpty && stops==0 { check(registrations==(isFinal ? (profile.listRegistry=="zero" ? 125 : 126) : isList ? (profile.listRegistry=="zero" ? 122 : 123) : isExtended ? (profile.extendedFail=="registry-zero" ? 114 : 115) : 57),"actual callbacks exclude direct JMP entries and failed registry append") }
    if authorityControl.isEmpty && profile.growthPolicy=="first-failure" {
        check(wrappers==34 && registrations==33 && stops==0 && eventIndex==138,
              "failed first registry growth loses registration without suppressing wrapper return")
    }
}
if ["claw-original-static-startup-fifteen-wrapper-pages-v4","claw-original-static-startup-thirtyfour-wrapper-pages-v5","claw-original-static-startup-application-shared-pages-v6","claw-original-static-startup-extended-records-pages-v7","claw-original-static-startup-list-records-pages-v8","claw-original-static-startup-final-records-pages-v9"].contains(profile.schema) {
    var boundaries: [[String:Any]] = [], observedEntries=Set<Int>()
    for (index, entry) in profile.entries.enumerated() {
        for returning in [false,true] {
            let state=returning ? entry.after : entry.before
            if nativeStates.contains(where: { ($0["function"] as? UInt32)==entry.function &&
                ($0["returnPC"] as? UInt32)==entry.returnPC && ($0["referenceState"] as? Int)==state &&
                ($0["returning"] as? Bool)==returning }) {
                boundaries.append(["entry":index,"state":state,"returning":returning]);observedEntries.insert(index)
            }
        }
    }
    // These are immutable-original observations with no exported native callback.
    // Internal owned C++ children and inline FS instructions remain reference-only.
    result["observed_reference_boundaries"]=boundaries
    result["reference_only_entry_indices"]=profile.entries.indices.filter { !observedEntries.contains($0) }
    result["reference_only_state_indices"]=profile.states.indices.filter { !comparedStates.contains($0) }
    result["reference_only_inline_fs_transitions"]=try! JSONSerialization.jsonObject(with:JSONEncoder().encode(profile.inlineFsTransitions ?? []))
}
let artifact=URL(fileURLWithPath:CommandLine.arguments[1]).deletingPathExtension().appendingPathExtension("native.json")
if isJoint {
    result["checks"]=checks
    result["reference_only_physical_event_indices"]=profile.events.indices.filter { $0>=eventIndex }
    result["missing_native_dependency"]=NSNull()
    if isFinal { var inputs=try! JSONSerialization.jsonObject(with:JSONEncoder().encode(profile.platformProfileInputs!)) as! [String:Any];for key in ["messageInitial","capsPolicy","physicalStop"] where inputs[key]==nil { inputs[key]=NSNull() };result["declared_platform_inputs"]=inputs;result["physical_policy_sha256"]=profile.physicalPolicySha256! }
    if isExtended { result["declared_caller_inputs"]=profile.declaredCallerInputs! }
}
let capture:[String:Any]=["schema":"claw-native-static-startup-pages-v1","profile":profile.name,
    "pages":nativePages,"states":nativeStates,"result":result]
let captureBytes=try JSONSerialization.data(withJSONObject:capture,options:.sortedKeys)
try captureBytes.write(to:artifact)
print(String(data:try JSONSerialization.data(withJSONObject:result,options:.sortedKeys),encoding:.utf8)!)
