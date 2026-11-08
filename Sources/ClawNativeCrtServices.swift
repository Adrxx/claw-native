import Foundation

// Trusted physical CRT service owner. Source lock/table publication remains in
// admitted bodies; construction only binds storage provided by the launcher.
final class ClawNativeCrtServices: ClawNativeCanonicalHost.SourceFinalPlatformProvider {
    enum Failure: Error { case ownership, unsupported, stopped }
    struct Section: Equatable {
        let address: UInt32
        let identity: ClawTokenHeap.AllocationIdentity
        var owner: UInt32 = 0, depth: UInt32 = 0
        static func == (a: Self, b: Self) -> Bool {
            a.address == b.address && a.identity === b.identity && a.owner == b.owner && a.depth == b.depth
        }
    }
    let host: ClawNativeCanonicalHost
    let memory: ClawNativeCrtMemory
    let logicalThread: UInt32
    private let thread = pthread_self()
    private let spans: [(base: UInt32, count: UInt32, identity: ClawTokenHeap.AllocationIdentity)]
    private let imports: [UInt32: UInt32]
    private let staticSections: [UInt32:UInt32] = [17:0x540e38,13:0x540e68,9:0x540e50,1:0x540e20]
    let sharedSections: ClawNativePhysicalSections?
    private var legacySections: [UInt32:Section] = [:]
    var sections: [UInt32:Section] {
        guard let sharedSections else { return legacySections }
        return sharedSections.records.mapValues { .init(address:$0.address,identity:$0.identity,owner:$0.owner,depth:$0.depth) }
    }
    private(set) var attempts = 0, mallocAttempts = 0, resizeAttempts = 0
    var failMallocAttempt = 0, failResizeAttempt = 0
    var resizeMode: ClawNativeCrtMemory.ResizePolicy = .inPlace
    var mixedResize = false
    var beforeService: ((ClawNativeCrtServices, ClawNativeCanonicalHost.SourceCrtRequest) throws -> Void)?
    var afterService: ((ClawNativeCrtServices, ClawNativeCanonicalHost.SourceCrtRequest) throws -> Void)?

    // Explicit bounded process-local physical domain; no Windows process-wide
    // compatibility or guest source publication is implied.
    struct NamedMessage: Equatable { let name: Data; let identifier: UInt32 }
    struct NamedMessageCall: Equatable {
        let name: Data, result: UInt32, reused: Bool, inserted: Bool, callerReturnPC: UInt32
    }
    private var namedRegistry: [Data:UInt32] = [:]
    private var namedImportTarget: UInt32?
    private var namedMessagesEnabled=false
    private(set) var nextNamedMessage: UInt32 = 0xc000
    private(set) var namedMessageHistory: [NamedMessageCall] = []
    var failNamedMessage=false
    var namedMessages: [NamedMessage] {
        namedRegistry.map { NamedMessage(name:$0.key,identifier:$0.value) }.sorted { $0.identifier<$1.identifier }
    }
    func configureNamedMessages(initial: [NamedMessage] = [], nextIdentifier: UInt32 = 0xc000) throws {
        guard !namedMessagesEnabled,attempts==0,!host.physicalServiceInProgress,validCrtBinding(for:host),
              spans.contains(where: { $0.base<=0x546c2c && UInt64($0.base)+UInt64($0.count)>=0x546c30 }),
              host.heap.lookup(0x546c2c,words:1)?[0]==0x7100fc,
              claw_canonical_lookup(0x7100fc)==nil,!imports.values.contains(0x7100fc),initial.count<=0x4000,
              nextIdentifier==0xc000+UInt32(initial.count),
              Set(initial.map { $0.name }).count==initial.count,
              Set(initial.map { $0.identifier })==Set((0..<initial.count).map { 0xc000+UInt32($0) }),
              initial.allSatisfy({ !$0.name.isEmpty && $0.name.count<256 && !$0.name.contains(0) }) else { throw Failure.ownership }
        namedRegistry=Dictionary(uniqueKeysWithValues:initial.map { ($0.name,$0.identifier) })
        nextNamedMessage=nextIdentifier;namedImportTarget=0x7100fc;namedMessagesEnabled=true
    }

    struct FinalPlatformPolicy: Equatable, Codable {
        var version: UInt32 = 10
        var processVersion: UInt32 = 0x40000
        var zeroScalars=false, zeroCaps=false, acquireDC=true, releaseDC=true, zeroBorrowed=false
    }
    struct PlatformCall: Equatable, Codable {
        let name: String, returnPC: UInt32, arguments: [UInt32], result: UInt32
    }
    struct VersionCall: Equatable, Codable { let returnPC: UInt32, result: UInt32 }
    struct DesktopAttempt: Equatable, Codable { let result: UInt32; var phase: String; let acquireReturnPC: UInt32 }
    struct DesktopLease: Equatable, Codable { let handle: UInt32; let kind: String; let hwnd: UInt32, acquireReturnPC: UInt32 }
    struct DesktopCall: Equatable, Codable {
        let name: String, returnPC: UInt32, arguments: [UInt32], result: UInt32, live: [UInt32]
    }
    static let finalPlatformPolicyId="6aefbfa66b7bdb8429503d33b28cd13f9195e52ce36ba153e0d94901b5326b41"
    private var finalPolicy: FinalPlatformPolicy?
    private var finalImports: [UInt32:UInt32] = [:]
    private var finalCode: [(UInt32,Data,ClawTokenHeap.AllocationIdentity)] = []
    private var finalSitesExecuted: Set<UInt32> = []
    var finalPlatformReady: Bool { finalPolicy != nil }
    var finalPhysicalIdentities: [UInt32] { [0x79000001,0x7900100f,0x79001006,0x7a007f02,0x7a007f00] }
    var platformPolicyId: String? { finalPlatformReady ? Self.finalPlatformPolicyId : nil }
    private(set) var platformHistory: [PlatformCall] = []
    private(set) var versionHistory: [VersionCall] = []
    private(set) var desktopDCAttempt: DesktopAttempt?
    private(set) var liveDesktopDCs: [DesktopLease] = []
    private(set) var desktopDCHistory: [DesktopCall] = []
    private(set) var borrowedLookupHistory: [PlatformCall] = []
    var borrowedIdentityTable: [String:[String:UInt32]] {
        ["brushes":["15":0x7900100f,"6":0x79001006],"cursors":["32514":0x7a007f02,"32512":0x7a007f00]]
    }
    func configureFinalPlatform(policy: FinalPlatformPolicy = .init()) throws {
        guard !finalPlatformReady,namedMessagesEnabled,attempts==0,!host.physicalServiceInProgress,validCrtBinding(for:host),
              [UInt32(10),0x80000004,3,0x80000104,0x103].contains(policy.version),
              [UInt32(0),0x3ffff,0x40000,UInt32.max].contains(policy.processVersion),
              Set(finalPhysicalIdentities).count==5,finalPhysicalIdentities.allSatisfy({ !host.heap.overlaps($0,count:1) }) else { throw Failure.ownership }
        var bindings:[UInt32:UInt32]=[:],code:[(UInt32,Data,ClawTokenHeap.AllocationIdentity)]=[]
        for site in ClawNativeCanonicalHost.finalPhysicalSites {
            guard spans.contains(where: { $0.base<=site.slot && UInt64($0.base)+UInt64($0.count)>=UInt64(site.slot)+4 }),
                  host.heap.lookup(site.slot,words:1)?[0]==site.target,claw_canonical_lookup(site.target)==nil,
                  let identity=host.heap.containingAllocationIdentity(at:site.callPC,count:UInt32(site.bytes.count)),
                  let bytes=host.heap.lookupBytes(site.callPC,count:UInt32(site.bytes.count)),
                  Data(bytes:bytes,count:site.bytes.count)==Data(site.bytes) else { throw Failure.ownership }
            bindings[site.slot]=site.target;code.append((site.callPC,Data(site.bytes),identity))
        }
        for (base,data):(UInt32,Data) in [(0x511170,Data([0x63,0x6f,0x6d,0x6d,0x63,0x74,0x72,0x6c,0x5f,0x44,0x72,0x61,0x67,0x4c,0x69,0x73,0x74,0x4d,0x73,0x67,0])),(0x5122d0,Data([0x4d,0x53,0x57,0x48,0x45,0x45,0x4c,0x5f,0x52,0x4f,0x4c,0x4c,0x4d,0x53,0x47,0]))] {
            guard let identity=host.heap.containingAllocationIdentity(at:base,count:UInt32(data.count)),let bytes=host.heap.lookupBytes(base,count:UInt32(data.count)),Data(bytes:bytes,count:data.count)==data else { throw Failure.ownership }
            code.append((base,data,identity))
        }
        var all=imports;all[0x546c2c]=namedImportTarget
        for (slot,target) in bindings { guard all[slot].map({$0==target}) ?? true else { throw Failure.ownership };all[slot]=target }
        guard Set(all.values).count==all.count else { throw Failure.ownership }
        finalImports=bindings;finalCode=code;finalPolicy=policy
    }
    private func finalSite(_ request: ClawNativeCanonicalHost.SourceCrtRequest) throws -> ClawNativeCanonicalHost.FinalPhysicalSite {
        guard finalPlatformReady,let site=ClawNativeCanonicalHost.finalPhysicalSites.first(where: { $0.slot==request.function && $0.returnPC==request.returnPC }),
              site.target==request.target,request.context.eip==site.target,site.arguments.count==request.arguments.count else { throw Failure.unsupported }
        // Dynamic HDC arguments are validated by the typed lease below.
        for (expected,actual) in zip(site.arguments,request.arguments) { if let expected,expected != actual { throw Failure.unsupported } }
        guard site.owner==0 || !finalSitesExecuted.contains(site.returnPC) else { throw Failure.ownership }
        return site
    }
    private func performFinalPlatform(_ request: ClawNativeCanonicalHost.SourceCrtRequest) throws -> UInt32 {
        let site=try finalSite(request)
        guard let policy=finalPolicy else { throw Failure.unsupported }
        let args=request.arguments,result:UInt32,name:String
        switch request.function {
        case 0x546abc:
            result=policy.version;versionHistory.append(.init(returnPC:request.returnPC,result:result))
            if site.owner != 0 { finalSitesExecuted.insert(request.returnPC) }
            return result
        case 0x546a94:name="GetProcessVersion";result=policy.processVersion
        case 0x546c44:
            name="GetSystemMetrics"
            let values:[UInt32:UInt32]=[2:UInt32.max,3:37,11:19,12:23]
            guard let value=values[args[0]] else { throw Failure.unsupported }
            result=policy.zeroScalars ? 0 : value
        case 0x546d20:
            name="GetSysColor"
            let values:[UInt32:UInt32]=[15:0x112233,16:0x445566,20:0x778899,18:0x010203,6:0xa1b2c3]
            guard let value=values[args[0]] else { throw Failure.unsupported }
            result=policy.zeroScalars ? 0 : value
        case 0x546c7c:
            name="GetDC"
            guard args==[0],desktopDCAttempt==nil,liveDesktopDCs.isEmpty else { throw Failure.ownership }
            result=policy.acquireDC ? 0x79000001 : 0
            desktopDCAttempt = .init(result:result,phase:"acquired",acquireReturnPC:request.returnPC)
            if result != 0 { liveDesktopDCs=[.init(handle:result,kind:"desktopDC",hwnd:0,acquireReturnPC:request.returnPC)] }
        case 0x546894:
            name="GetDeviceCaps"
            guard var attempt=desktopDCAttempt,args.count==2,args[0]==attempt.result,
                  (args[1]==88 && attempt.phase=="acquired") || (args[1]==90 && attempt.phase=="caps88"),
                  attempt.result==0 ? liveDesktopDCs.isEmpty : liveDesktopDCs.count==1 && liveDesktopDCs[0].handle==attempt.result else { throw Failure.ownership }
            result=attempt.result==0 || policy.zeroScalars || policy.zeroCaps ? 0 : args[1]==88 ? 101 : 137
            attempt.phase=args[1]==88 ? "caps88" : "caps90";desktopDCAttempt=attempt
        case 0x546c80:
            name="ReleaseDC"
            guard var attempt=desktopDCAttempt,attempt.phase=="caps90",args==[0,attempt.result],
                  attempt.result==0 ? liveDesktopDCs.isEmpty : liveDesktopDCs.count==1 && liveDesktopDCs[0].handle==attempt.result else { throw Failure.ownership }
            result=attempt.result != 0 && policy.releaseDC ? 1 : 0
            if result != 0 { liveDesktopDCs.removeAll();attempt.phase="released" } else { attempt.phase="release-failed" }
            desktopDCAttempt=attempt
        case 0x546b64:
            name="GetSysColorBrush"
            guard let value=borrowedIdentityTable["brushes"]?[String(args[0])] else { throw Failure.unsupported }
            result=policy.zeroBorrowed ? 0 : value
        case 0x546b60:
            name="LoadCursorA"
            guard args.count==2,args[0]==0,let value=borrowedIdentityTable["cursors"]?[String(args[1])] else { throw Failure.unsupported }
            result=policy.zeroBorrowed ? 0 : value
        default:throw Failure.unsupported
        }
        let event=PlatformCall(name:name,returnPC:request.returnPC,arguments:args,result:result)
        platformHistory.append(event)
        if [UInt32(0x546c7c),0x546894,0x546c80].contains(request.function) {
            desktopDCHistory.append(.init(name:name,returnPC:request.returnPC,arguments:args,result:result,live:liveDesktopDCs.map{$0.handle}))
        }
        if request.function==0x546b64 || request.function==0x546b60 { borrowedLookupHistory.append(event) }
        finalSitesExecuted.insert(request.returnPC)
        return result
    }

    init(host: ClawNativeCanonicalHost, memory: ClawNativeCrtMemory,
         spans: [(UInt32, UInt32)], logicalThread: UInt32 = 1, sharedSections: ClawNativePhysicalSections? = nil) throws {
        guard host.heap === memory.heap, host.fault == nil, !host.physicalServiceInProgress,
              logicalThread != 0,sharedSections.map({ $0.heap === host.heap && $0.logicalThread==logicalThread && $0.valid() }) ?? true else { throw Failure.ownership }
        self.sharedSections=sharedSections
        self.host = host; self.memory = memory; self.logicalThread = logicalThread
        let pinned = try spans.map { base, count in
            guard count > 0, let identity = host.heap.containingAllocationIdentity(at: base,count: count) else {
                throw Failure.ownership
            }
            return (base,count,identity)
        }
        self.spans = pinned
        let required: [(UInt32,UInt32)] = [(0x52ed18,80),(0x545fd0,8),(0x546aa4,4),(0x546aac,4),(0x546a9c,4)]
        guard required.allSatisfy({ address,count in
            pinned.contains { $0.0 <= address && UInt64(address)+UInt64(count) <= UInt64($0.0)+UInt64($0.1) }
        }) else { throw Failure.ownership }
        var resolved: [UInt32:UInt32] = [:]
        for slot: UInt32 in [0x546aa4,0x546aac,0x546a9c] {
            guard let p = host.heap.lookup(slot,words:1), p[0] != 0,
                  claw_canonical_lookup(p[0]) == nil,
                  !(p[0] >= CLAW_STACK_BASE && p[0] < CLAW_STACK_END) else { throw Failure.ownership }
            resolved[slot] = p[0]
        }
        // Optional finite string import leaves legacy CRT-only owners unchanged.
        if pinned.contains(where: { $0.0<=0x5469e4 && UInt64($0.0)+UInt64($0.1)>=0x5469e8 }) {
            guard let p=host.heap.lookup(0x5469e4,words:1),p[0] != 0,
                  claw_canonical_lookup(p[0])==nil,!(p[0]>=CLAW_STACK_BASE && p[0]<CLAW_STACK_END),
                  !resolved.values.contains(p[0]) else { throw Failure.ownership }
            resolved[0x5469e4]=p[0]
        }
        guard Set(resolved.values).count == resolved.count else { throw Failure.ownership }
        imports = resolved
    }

    private func record(_ section: Section) -> [UInt32] {
        [0,section.depth &- 1,section.depth,section.owner,0,0]
    }
    func validCrtBinding(for host: ClawNativeCanonicalHost) -> Bool {
        guard self.host === host, host.heap === memory.heap, pthread_equal(thread,pthread_self()) != 0,
              sharedSections?.valid() ?? true,
              spans.allSatisfy({ host.heap.containingAllocationIdentity(at:$0.base,count:$0.count) === $0.identity }),
              imports.allSatisfy({ slot,target in host.heap.lookup(slot,words:1)?[0] == target }),
              namedImportTarget.map({ host.heap.lookup(0x546c2c,words:1)?[0]==$0 }) ?? true,
              finalImports.allSatisfy({ host.heap.lookup($0.key,words:1)?[0]==$0.value }),
              finalCode.allSatisfy({ base,data,identity in
                  host.heap.containingAllocationIdentity(at:base,count:UInt32(data.count)) === identity && host.heap.lookupBytes(base,count:UInt32(data.count)).map({ Data(bytes:$0,count:data.count)==data })==true
              }),
              staticSections.allSatisfy({ index,address in host.heap.lookup(0x52ed18+index*4,words:1)?[0] == address }),
              sections.values.allSatisfy({ section in
                  host.heap.containingAllocationIdentity(at:section.address,count:24) === section.identity &&
                  host.heap.lookup(section.address,words:6).map { Array(UnsafeBufferPointer(start:$0,count:6)) == record(section) } == true
              }) else { return false }
        do { try memory.validateLiveOwnership(); return true } catch { return false }
    }
    func crtImportTarget(_ slot: UInt32) -> UInt32? {
        guard validCrtBinding(for:host) else { return nil }
        return finalImports[slot] ?? (slot==0x546c2c ? namedImportTarget : imports[slot])
    }
    func crtAllocationWitness(_ token: UInt32) -> ClawNativeCanonicalHost.CrtAllocationWitness? {
        guard validCrtBinding(for:host),let allocation=try? memory.allocation(token) else { return nil }
        return .init(token:allocation.base,requested:allocation.requested,capacity:allocation.capacity,
                     generation:allocation.generation,identity:allocation.identity)
    }
    private func writeSection(_ section: Section) throws {
        guard host.heap.containingAllocationIdentity(at:section.address,count:24) === section.identity,
              let p = host.heap.lookup(section.address,words:6) else { throw Failure.ownership }
        for (index,value) in record(section).enumerated() { p[index] = value }
    }
    private func ansiSnapshot(_ token: UInt32, maximum: UInt32 = 65_536) throws -> (Data,ClawTokenHeap.AllocationIdentity) {
        // ANSI byte count, bounded by the declared physical policy and one live
        // allocation. No Unicode conversion or source-object publication.
        for count: UInt32 in 1...maximum {
            guard let bytes=host.heap.lookupBytes(token,count:count) else { throw Failure.ownership }
            if bytes[Int(count)-1]==0 {
                guard let identity=host.heap.containingAllocationIdentity(at:token,count:count) else { throw Failure.ownership }
                return (Data(bytes:bytes,count:Int(count)),identity)
            }
        }
        throw Failure.unsupported
    }
    func serviceSourceCrt(_ request: ClawNativeCanonicalHost.SourceCrtRequest) -> UInt32? {
        guard request.consume(for:host,provider:self), validCrtBinding(for:host),
              host.beginPhysicalService(at:request.function) else { return nil }
        defer { host.endPhysicalService() }
        do {
            let readonly: (Data,ClawTokenHeap.AllocationIdentity)?
            if request.function==0x5469e4 {
                guard request.returnPC==0x4f662e,request.arguments==[0x534938],
                      request.target==imports[0x5469e4],request.context.eip==request.target else { throw Failure.unsupported }
                readonly=try ansiSnapshot(request.arguments[0])
            } else if request.function==0x546c2c {
                guard namedMessagesEnabled,((request.returnPC==0x4f822d && request.arguments==[0x511170]) ||
                      (finalPlatformReady && request.returnPC==0x4ffd50 && request.arguments==[0x5122d0])),
                      request.target==namedImportTarget,request.target==0x7100fc,request.context.eip==request.target else { throw Failure.unsupported }
                readonly=try ansiSnapshot(request.arguments[0],maximum:256)
            } else { readonly=nil }
            func validReadonly() -> Bool {
                guard let readonly else { return true }
                let token=request.arguments[0],count=UInt32(readonly.0.count)
                guard host.heap.containingAllocationIdentity(at:token,count:count) === readonly.1,
                      let bytes=host.heap.lookupBytes(token,count:count) else { return false }
                return Data(bytes:bytes,count:Int(count))==readonly.0
            }
            if finalImports[request.function] != nil { _=try finalSite(request) }
            attempts += 1
            try beforeService?(self,request)
            guard host.validatePhysicalAuthority(at:request.function), validCrtBinding(for:host),
                  request.validReturn(for:host),validReadonly() else { throw Failure.ownership }
            let args = request.arguments
            let result: UInt32
            switch request.function {
            case 0x4a48e0:
                let mallocRows: [UInt32:UInt32] = [0x4a361a:0x80,0x4a7bda:0x18,0x4dbc0f:44]
                guard args.count == 1,mallocRows[request.returnPC]==args[0] else { throw Failure.unsupported }
                mallocAttempts += 1
                result = try memory.malloc(args[0],fail:mallocAttempts == failMallocAttempt)
                if request.returnPC==0x4dbc0f,result != 0 {
                    guard let witness=crtAllocationWitness(result),request.publishAllocation(witness,for:host,provider:self) else {
                        throw Failure.ownership
                    }
                }
            case 0x4a6560:
                guard args.count == 1, host.heap.lookup(0x545fd4,words:1)?[0] == args[0] else { throw Failure.ownership }
                result = try memory.capacity(args[0])
            case 0x4a9070:
                guard args.count == 2, host.heap.lookup(0x545fd4,words:1)?[0] == args[0],
                      args[1] == (try memory.capacity(args[0])) + 16 else { throw Failure.ownership }
                resizeAttempts += 1
                let policy: ClawNativeCrtMemory.ResizePolicy = resizeAttempts == failResizeAttempt ? .fail :
                    mixedResize ? (resizeAttempts.isMultiple(of:2) ? .move : .inPlace) : resizeMode
                result = try memory.realloc(args[0],args[1],policy:policy)
            case 0x4a49b0:
                guard args.count == 1 else { throw Failure.unsupported }
                try memory.free(args[0]); result = 0
            case 0x546abc,0x546a94,0x546c44,0x546c7c,0x546894,0x546c80,0x546d20,0x546b64,0x546b60:
                result=try performFinalPlatform(request)
            case 0x546c2c:
                guard let readonly,validReadonly() else { throw Failure.ownership }
                let key=readonly.0.dropLast(),existing=namedRegistry[Data(key)]
                if failNamedMessage || key.isEmpty { result=0 }
                else if let existing { result=existing }
                else if nextNamedMessage<=0xffff {
                    result=nextNamedMessage;nextNamedMessage+=1;namedRegistry[Data(key)]=result
                } else { result=0 }
                namedMessageHistory.append(.init(name:Data(key),result:result,reused:result != 0 && existing != nil,
                    inserted:result != 0 && existing==nil,callerReturnPC:request.returnPC))
                if request.returnPC==0x4ffd50 { finalSitesExecuted.insert(request.returnPC) }
            case 0x5469e4:
                guard let readonly,validReadonly() else { throw Failure.ownership }
                result=UInt32(readonly.0.count-1)
            case 0x546aa4 where sharedSections != nil,0x546aac where sharedSections != nil,0x546a9c where sharedSections != nil:
                guard args.count==1 else { throw Failure.unsupported }
                result=try sharedSections!.perform(slot:request.function,address:args[0])
            case 0x546aa4:
                guard args.count == 1, sections[args[0]] == nil,
                      let identity = host.heap.containingAllocationIdentity(at:args[0],count:24) else { throw Failure.ownership }
                let section = Section(address:args[0],identity:identity)
                try writeSection(section); legacySections[args[0]] = section; result = 0
            case 0x546aac,0x546a9c:
                guard args.count == 1, var section = sections[args[0]] else { throw Failure.ownership }
                if request.function == 0x546aac {
                    guard section.owner == 0 || section.owner == logicalThread, section.depth < UInt32.max else { throw Failure.ownership }
                    section.owner = logicalThread; section.depth += 1
                } else {
                    guard section.owner == logicalThread, section.depth > 0 else { throw Failure.ownership }
                    section.depth -= 1; if section.depth == 0 { section.owner = 0 }
                }
                try writeSection(section); legacySections[args[0]] = section; result = 0
            default: throw Failure.unsupported
            }
            try afterService?(self,request)
            guard host.validatePhysicalReturn(at:request.function),validCrtBinding(for:host),request.validReturn(for:host),validReadonly() else {
                throw Failure.ownership
            }
            return result
        } catch {
            host.fail(UInt32(CLAW_FAULT_HALT),at:request.function); return nil
        }
    }
}

extension ClawNativeCrtServices: ClawNativeCanonicalHost.SourceSharedStorage {
    var sharedHeap: ClawTokenHeap { memory.heap }
    var sharedSectionOwner: ClawNativePhysicalSections? { sharedSections }
    func sharedMalloc(_ count: UInt32) throws -> UInt32 { try memory.malloc(count) }
    func sharedAllocation(_ token: UInt32) throws -> ClawNativeCanonicalHost.CrtAllocationWitness {
        let allocation=try memory.allocation(token)
        return .init(token:allocation.base,requested:allocation.requested,capacity:allocation.capacity,
                     generation:allocation.generation,identity:allocation.identity)
    }
    func sharedFree(_ token: UInt32) throws { try memory.free(token) }
}
