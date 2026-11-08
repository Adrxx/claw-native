import Foundation

// Bounded platform owner for the admitted MFC lock routines. Source globals and
// cached IAT targets live in the application's actual token heap. This supplies
// physical services only; it does not implement MFC TLS, SEH or application init.
final class ClawNativeMfcLocks {
    static let imageHash = "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263"
    static let imageBase: UInt32 = 0x5408e0
    static let imageCount: UInt32 = 0x210
    static let master: UInt32 = 0x540a90
    static let importSlots: Set<UInt32> = [0x546abc, 0x546aa4, 0x546aac, 0x546a9c]
    enum Failure: Error { case invalidImage, invalidImport, invalidSection, invalidOwnership, contention }
    struct State: Codable, Equatable {
        let section: UInt32
        var owner: UInt32 = 0
        var depth: UInt32 = 0
        var initialized: UInt32 = 1
        var entered: UInt32 = 0
        var left: UInt32 = 0
    }
    struct Event: Equatable {
        let function: UInt32, target: UInt32, stackPointer: UInt32
        let arguments: [UInt32]
        let before: [State], after: [State]
        let beforeBytes: [UInt8], afterBytes: [UInt8]
        let completed: Bool
    }
    private final class Section {
        let lock = NSRecursiveLock()
        var state: State
        var thread: Thread?
        init(_ token: UInt32) { state = State(section: token) }
    }
    let host: ClawNativeCanonicalHost
    private let imports: [UInt32: UInt32]
    private let version: UInt32
    let sharedSections: ClawNativePhysicalSections?
    private var borrowedStorage: Set<UInt32> = []
    private let logicalThread: UInt32
    var logicalThreadIdentifier: UInt32 { logicalThread }
    private var sections: [UInt32: Section] = [:]
    private var ownedStorage: [UInt32: ClawTokenHeap.AllocationIdentity] = [:]
    private let executionThread = Thread.current
    private(set) var events: [Event] = []
    // A nonreturning physical service failure remains a sticky native halt.
    // The optional boundary also allows a controlled synchronization publication
    // before Enter returns. This is a model, not a parallel Windows execution.
    var beforeService: ((ClawNativeMfcLocks, UInt32, [UInt32]) throws -> Void)?
    var incidentalResult: UInt32 = 0
    var beforeSourceService: ((ClawNativeCanonicalHost.SourceLocksRequest) -> Void)?
    struct SavedState: Codable, Equatable {
        let imports: [UInt32: UInt32], version: UInt32, logicalThread: UInt32, shared: Bool
        let borrowed: Set<UInt32>, storage: [UInt32: ClawSnapshotWitness], sections: [State]
        let incidentalResult: UInt32
    }
    func savedState() throws -> SavedState {
        guard Thread.current === executionThread, host.snapshotQuiescent, !performingSource, sourceRequest == nil,
              sections.values.allSatisfy({ $0.state.depth == 0 && $0.thread == nil }),
              sharedSections?.records.values.allSatisfy({ $0.depth == 0 && $0.owner == 0 }) ?? true
        else { throw ClawSnapshotError.activeFrame }
        return .init(imports: imports, version: version, logicalThread: logicalThread, shared: sharedSections != nil,
            borrowed: borrowedStorage, storage: Dictionary(uniqueKeysWithValues: ownedStorage.map { token, identity in
                (token, ClawSnapshotWitness(heap: host.heap, token: token,
                    count: token == Self.imageBase ? Self.imageCount : 4, identity: identity, interior: true))
            }), sections: sections.values.map(\.state).sorted { $0.section < $1.section }, incidentalResult: incidentalResult)
    }
    func prepareRestore(_ value: SavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws -> Void {
        _ = try savedState(); try host.heap.validateRestore(plan)
        guard value.imports == imports, value.version == version, value.logicalThread == logicalThread,
              value.shared == (sharedSections != nil), Set(value.sections.map(\.section)).count == value.sections.count,
              value.sections.allSatisfy({ $0.depth == 0 && $0.owner == 0 }) else { throw ClawSnapshotError.invalidState }
        var restoredStorage: [UInt32: ClawTokenHeap.AllocationIdentity] = [:], restoredSections: [UInt32: Section] = [:]
        for (token, witness) in value.storage {
            guard witness.reference.token == token,
                  witness.reference.count == (token == Self.imageBase ? Self.imageCount : 4) else { throw ClawSnapshotError.invalidState }
            restoredStorage[token] = try witness.resolve(in: plan)
        }
        for state in value.sections {
            let section = Section(state.section); section.state = state; restoredSections[state.section] = section
        }
        return { [self] in
            _ = try savedState(); try host.heap.validateInstalledRestore(plan)
            ownedStorage = restoredStorage; borrowedStorage = value.borrowed; sections = restoredSections
            incidentalResult = value.incidentalResult; events.removeAll()
        }
    }
    private var sourceRequest: ClawNativeCanonicalHost.SourceLocksRequest?
    private var performingSource = false
    fileprivate final class PublicationScope {
        var receiptIssued = false
    }
    final class ObservedInitialization {
        fileprivate weak var owner: ClawNativeMfcLocks?
        fileprivate let scope: PublicationScope
        fileprivate let index: UInt32
        fileprivate var consumed = false
        fileprivate init(owner: ClawNativeMfcLocks, scope: PublicationScope, index: UInt32) {
            self.owner = owner; self.scope = scope; self.index = index
        }
    }
    private var publicationScope: PublicationScope?

    // This receipt models another thread's completed initializer becoming
    // visible while this thread is entering the master section. It grants only
    // the corresponding opaque physical section and source ready flag.
    func observeCompletedInitialization(index: UInt32) throws -> ObservedInitialization {
        guard let scope = publicationScope, !scope.receiptIssued,
              validPublication(index: index) else { throw Failure.invalidOwnership }
        scope.receiptIssued = true
        return ObservedInitialization(owner: self, scope: scope, index: index)
    }
    func publishObservedInitialization(_ receipt: ObservedInitialization) throws {
        guard receipt.owner === self, !receipt.consumed, publicationScope === receipt.scope,
              validPublication(index: receipt.index) else { throw Failure.invalidOwnership }
        receipt.consumed = true
        try initializeSection(0x5408f0 + receipt.index * 24)
        host.heap.lookup(0x540aa8 + receipt.index * 4, words: 1)![0] = 1
    }
    private func validPublication(index: UInt32) -> Bool {
        guard Thread.current === executionThread, host.physicalServiceInProgress, host.fault == nil,
              index < 17, validStorage(Self.imageBase), Self.importSlots.allSatisfy(validStorage),
              states.contains(where: { $0.section==Self.master }), !states.contains(where: { $0.section==0x5408f0+index*24 }),
              host.heap.lookup(0x5408e8, words: 1)?[0] != 0,
              host.heap.lookup(0x540a88, words: 1)?[0] == 0,
              host.heap.lookup(0x540aa8 + index * 4, words: 1)?[0] == 0 else { return false }
        if let request = sourceRequest, !request.validReturn(for: host) { return false }
        return host.validatePhysicalAuthority(at: 0x546aac)
    }

    init(host: ClawNativeCanonicalHost, sha256: String, initialBytes: [UInt8],
         importTargets: [UInt32: UInt32], version: UInt32 = 10, logicalThread: UInt32 = 1,
         sharedSections: ClawNativePhysicalSections? = nil, borrowExistingStorage: Bool = false) throws {
        guard sha256 == Self.imageHash, initialBytes.count == Int(Self.imageCount),
              (borrowExistingStorage ? host.heap.containingAllocationIdentity(at:Self.imageBase,count:Self.imageCount) != nil : !host.heap.overlaps(Self.imageBase, count: Self.imageCount)),
              !borrowExistingStorage || sharedSections != nil,
              sharedSections.map({ $0.heap === host.heap && $0.logicalThread==logicalThread && $0.valid() }) ?? true else { throw Failure.invalidImage }
        guard Set(importTargets.keys) == Self.importSlots,
              Set(importTargets.values).count == Self.importSlots.count,
              importTargets.allSatisfy({ slot, target in
                  (borrowExistingStorage ? host.heap.containingAllocationIdentity(at:slot,count:4) != nil && host.heap.lookup(slot,words:1)?[0]==target : !host.heap.overlaps(slot,count:4)) && target >= 0x710000 && target < 0x711000 &&
                  claw_canonical_lookup(target) == nil
              }) else { throw Failure.invalidImport }
        self.sharedSections=sharedSections
        self.host = host; self.version = version; self.logicalThread = logicalThread
        imports = Dictionary(uniqueKeysWithValues: importTargets.map { ($0.value, $0.key) })
        if borrowExistingStorage {
            ownedStorage[Self.imageBase]=host.heap.containingAllocationIdentity(at:Self.imageBase,count:Self.imageCount)!
            borrowedStorage.insert(Self.imageBase)
            for slot in importTargets.keys {
                ownedStorage[slot]=host.heap.containingAllocationIdentity(at:slot,count:4)!
                borrowedStorage.insert(slot)
            }
        } else {
            let storage=host.heap.storeBytes(token:Self.imageBase,count:Self.imageCount)
            storage.update(from:initialBytes,count:initialBytes.count)
            ownedStorage[Self.imageBase]=host.heap.allocationIdentity(at:Self.imageBase,count:Self.imageCount)!
            for (slot,target) in importTargets {
                host.heap.store(token:slot,words:1)[0]=target
                ownedStorage[slot]=host.heap.allocationIdentity(at:slot,count:4)!
            }
        }
    }

    private func validStorage(_ token: UInt32) -> Bool {
        guard let identity = ownedStorage[token] else { return false }
        return (borrowedStorage.contains(token) ? host.heap.containingAllocationIdentity(at:token,count:token==Self.imageBase ? Self.imageCount : 4) : host.heap.allocationIdentity(at:token,count:token==Self.imageBase ? Self.imageCount : 4)) === identity
    }
    private func validImport(_ slot: UInt32) -> Bool {
        guard validStorage(slot), let target = host.heap.lookup(slot, words: 1)?[0] else { return false }
        return imports[target] == slot
    }
    var states: [State] {
        if let sharedSections { return sharedSections.records.values.filter { validSection($0.address) }.map {
            State(section:$0.address,owner:$0.owner,depth:$0.depth,entered:$0.entered,left:$0.left)
        }.sorted { $0.section<$1.section } }
        return sections.values.map(\.state).sorted { $0.section<$1.section }
    }
    var imageBytes: [UInt8] {
        guard validStorage(Self.imageBase) else { return [] }
        return Array(UnsafeBufferPointer(start: host.heap.lookupBytes(Self.imageBase, count: Self.imageCount)!,
                                  count: Int(Self.imageCount)))
    }
    // The separate MFC TLS section at 0x540b14 is outside this owner.
    private func validSection(_ token: UInt32) -> Bool {
        token == Self.master || (token >= 0x5408f0 && token <= 0x540a70 && (token - 0x5408f0) % 24 == 0)
    }
    // Bind coherent warm state outside physical service execution. Observed
    // completion inside master Enter requires the scoped receipt above.
    func adoptInitializedSection(_ token: UInt32) throws {
        guard !host.physicalServiceInProgress else { throw Failure.invalidOwnership }
        try initializeSection(token)
    }
    private func initializeSection(_ token: UInt32) throws {
        guard Thread.current === executionThread, validStorage(Self.imageBase), validSection(token), sections[token] == nil,
              host.heap.lookupBytes(token, count: 24) != nil else { throw Failure.invalidSection }
        if let sharedSections { _=try sharedSections.perform(slot:0x546aa4,address:token) }
        else { sections[token]=Section(token) }
    }
    // Compose this with the host's previous dependency. Unknown services return
    // nil and can fall through; recognized bad calls set the host's sticky fault.
    func service(_ call: ClawCall) -> UInt32? {
        guard !performingSource else {
            host.fail(UInt32(CLAW_FAULT_ABI), at: call.function, diagnostic: .recursiveCanonicalCall); return nil
        }
        guard host.beginPhysicalService(at: call.function) else { return nil }
        defer { host.endPhysicalService() }
        return performService(call)
    }
    private func performService(_ call: ClawCall) -> UInt32? {
        guard host.fault == nil else { return nil }
        let slot: UInt32
        if Self.importSlots.contains(call.function) { slot = call.function }
        else if let resolved = imports[call.function] { slot = resolved }
        else { return nil }
        let count: UInt32 = slot == 0x546abc ? 0 : 1
        guard call.sourceTransferVersion == 0, call.sourceTransferKind == 0, call.sourceTransferSite == 0,
              call.sourceCallerFunction == 0, call.sourceDisposition == nil,
              call.compilerContext == nil, call.sourceContext == nil, call.sourceReturnPC == 0, call.argumentCount == count, call.receiver == 0, call.receiver2 == 0,
              call.x87ArgumentCount == 0, call.stackPointer >= CLAW_STACK_BASE,
              UInt64(call.stackPointer) + 4 * (1 + UInt64(count)) <= UInt64(CLAW_STACK_END),
              call.stackPointer & 3 == 0, Thread.current === executionThread else {
            host.fail(UInt32(CLAW_FAULT_ABI), at: call.function, diagnostic: .unsupportedABI); return nil
        }
        let arguments = withUnsafeBytes(of: call.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(count))) }
        let before = states, beforeBytes = imageBytes
        var completed = false
        defer {
            events.append(Event(function: slot, target: call.function, stackPointer: call.stackPointer,
                                arguments: arguments, before: before, after: states,
                                beforeBytes: beforeBytes, afterBytes: imageBytes, completed: completed))
        }
        do {
            guard validStorage(Self.imageBase), sourceRequest?.slot == 0x546aac ? validStorage(slot) : validImport(slot) else { throw Failure.invalidOwnership }
            // Scope exists only during this exact hook, never across Enter's
            // actual lock operation or a subsequent callback.
            do {
                if slot == 0x546aac && arguments == [Self.master] { publicationScope = PublicationScope() }
                defer { publicationScope = nil }
                try beforeService?(self, slot, arguments)
            }
            guard validStorage(Self.imageBase), Self.importSlots.allSatisfy(validStorage),
                  sourceRequest?.slot == 0x546aac ? validStorage(slot) : validImport(slot) else { throw Failure.invalidOwnership }
            if let request = sourceRequest, !request.validReturn(for: host) { throw Failure.invalidOwnership }
            guard host.validatePhysicalAuthority(at: slot) else { throw Failure.invalidOwnership }
            if slot == 0x546abc {
                guard host.validatePhysicalReturn(at: slot) else { return nil }
                completed = true; return version
            }
            let token = arguments[0]
            guard validSection(token) else { throw Failure.invalidSection }
            if let sharedSections {
                _=try sharedSections.perform(slot:slot,address:token)
            } else if slot == 0x546aa4 { try initializeSection(token) }
            else {
                guard let section = sections[token] else { throw Failure.invalidSection }
                if slot == 0x546aac {
                    guard section.state.depth < UInt32.max,
                          section.thread == nil || section.thread === Thread.current else { throw Failure.invalidOwnership }
                    guard section.lock.try() else { throw Failure.contention }
                    section.thread = Thread.current
                    section.state.owner = logicalThread
                    section.state.depth += 1; section.state.entered &+= 1
                } else {
                    guard section.thread === Thread.current, section.state.depth > 0 else { throw Failure.invalidOwnership }
                    section.state.depth -= 1; section.state.left &+= 1
                    if section.state.depth == 0 { section.state.owner = 0; section.thread = nil }
                    section.lock.unlock()
                }
            }
            guard host.validatePhysicalReturn(at: slot) else { return nil }
            completed = true; return sharedSections == nil ? incidentalResult : 0
        } catch {
            host.fail(UInt32(CLAW_FAULT_HALT), at: slot); return nil
        }
    }
    deinit {
        // A halted source graph can leave locks held. Reclaim native resources
        // on the owning execution thread without pretending source cleanup ran.
        precondition(Thread.current === executionThread)
        for section in sections.values where section.state.depth > 0 {
            precondition(section.thread === Thread.current)
            for _ in 0..<section.state.depth { section.lock.unlock() }
        }
        // These spans were reserved exclusively by this owner. Do not remove a
        // missing or replaced span if an embedding host ended its lifetime.
        for token in ownedStorage.keys where !borrowedStorage.contains(token) {
            if validStorage(token) {
                host.heap.free(token)
            }
        }
    }
}


extension ClawNativeMfcLocks: ClawNativeCanonicalHost.SourceLocksProvider {
    func validLocksBinding(for host: ClawNativeCanonicalHost) -> Bool {
        self.host === host && Thread.current === executionThread && host.fault == nil &&
            validStorage(Self.imageBase) && Self.importSlots.allSatisfy(validStorage) && (sharedSections?.valid() ?? true)
    }
    func locksImportTarget(_ slot: UInt32) -> UInt32? {
        guard Thread.current === executionThread, validStorage(slot) else { return nil }
        // Enter is cached by the original source before either physical call.
        // The lease retains that import identity across later IAT content writes.
        if slot == 0x546aac { return imports.first(where: { $0.value == slot })?.key }
        guard validImport(slot) else { return nil }
        return host.heap.lookup(slot, words: 1)?[0]
    }
    func locksSnapshot() -> ClawNativeCanonicalHost.LocksSnapshot {
        .init(imageBytes: imageBytes, states: states.map { .init(section: $0.section, owner: $0.owner, depth: $0.depth, initialized: $0.initialized, entered: $0.entered, left: $0.left) })
    }
    func serviceSourceLocks(_ request: ClawNativeCanonicalHost.SourceLocksRequest) -> UInt32? {
        guard Thread.current === executionThread else { return nil }
        guard !performingSource, validLocksBinding(for: host), request.target == locksImportTarget(request.slot),
              request.arguments.count == (request.slot == 0x546abc ? 0 : 1),
              request.consume(for: host, provider: self) else {
            host.fail(UInt32(CLAW_FAULT_ABI), at: request.slot, diagnostic: .unsupportedABI); return nil
        }
        guard host.beginPhysicalService(at: request.slot) else { return nil }
        defer { host.endPhysicalService() }
        performingSource = true; sourceRequest = request
        defer { sourceRequest = nil; performingSource = false }
        beforeSourceService?(request)
        guard request.validReturn(for: host) else { return nil }
        var call = ClawCall()
        call.function = request.slot == 0x546aac ? request.target : request.slot
        call.argumentCount = UInt32(request.arguments.count); call.stackPointer = request.context.esp
        withUnsafeMutableBytes(of: &call.arguments) { bytes in
            for (i, value) in request.arguments.enumerated() { bytes.storeBytes(of: value, toByteOffset: i*4, as: UInt32.self) }
        }
        return performService(call)
    }
}
