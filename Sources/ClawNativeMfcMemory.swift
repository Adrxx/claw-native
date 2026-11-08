import Foundation

// Physical storage and thread-local services for the source MFC managers. The
// admitted source bodies own slot selection, capacity, clearing and exceptions.
// The token arena is shared with the application; no executable game addresses
// are represented by host fixtures. This is one execution thread, not Win32 SEH
// or a claim about concurrent Windows critical-section scheduling.
final class ClawNativeMfcMemory {
    static let imageHash = ClawNativeMfcLocks.imageHash
    static let importArities: [UInt32: UInt32] = [
        0x546a90: 0, 0x546a7c: 1, 0x546a84: 2,
        0x546aa4: 1, 0x546aac: 1, 0x546a9c: 1, 0x546aa0: 1,
        0x546b1c: 2, 0x546a8c: 1, 0x5469c8: 1, 0x546a88: 3, 0x5469c4: 1, 0x546ac0: 1,
        0x546aa8: 2, 0x546a80: 3, 0x5469d8: 1
    ]
    enum Failure: Error { case invalidImage, invalidImport, invalidStorage, invalidOwnership, exhausted }
    struct Block: Codable, Equatable {
        let handle: UInt32
        var data: UInt32, size: UInt32, flags: UInt32, locks: UInt32
    }
    struct Event {
        let function: UInt32, target: UInt32, stackPointer: UInt32, arguments: [UInt32]
        let result: UInt32?, completed: Bool
        let blocks: [Block], sections: [ClawNativeMfcLocks.State]
        let managerBytes: [String: [UInt8]], blockBytes: [String: [UInt8]], localBytes: [String: [UInt8]]
    }
    private final class Section {
        let lock = NSRecursiveLock()
        let manager: UInt32
        let identity: ClawTokenHeap.AllocationIdentity
        var state: ClawNativeMfcLocks.State
        init(_ token: UInt32, manager: UInt32, identity: ClawTokenHeap.AllocationIdentity) {
            self.manager = manager; self.identity = identity
            state = .init(section: token)
        }
    }
    let host: ClawNativeCanonicalHost
    let sharedStorage: ClawNativeCanonicalHost.SourceSharedStorage?
    let sharedSections: ClawNativePhysicalSections?
    private var sharedAllocations: [UInt32:ClawNativeCanonicalHost.CrtAllocationWitness] = [:]
    private let locks: ClawNativeMfcLocks?
    private let targets: [UInt32: UInt32]
    private let executionThread = Thread.current
    private let logicalThread: UInt32
    private var jointRaiseImport: (target:UInt32,identity:ClawTokenHeap.AllocationIdentity)?
    private var applicationTargets: [UInt32: UInt32] = [:]
    private var applicationInputs: [UInt32: UInt32] = [:]
    private var applicationReceiver: UInt32 = 0
    private var applicationReceiverIdentity: ClawTokenHeap.AllocationIdentity?
    private var cursorSuccess = true
    private var cursorPoint: (Int32,Int32) = (0,0)
    private var currentThreadHandle: UInt32 = UInt32.max
    var beforeSourceApplicationService: ((ClawNativeCanonicalHost.SourceApplicationRequest) -> Void)?
    private var owned: [UInt32: (identity: ClawTokenHeap.AllocationIdentity, count: UInt32)] = [:]
    private var importIdentities: [UInt32: ClawTokenHeap.AllocationIdentity] = [:]
    private var managers: [UInt32: ClawTokenHeap.AllocationIdentity] = [:]
    private var globals: [UInt32: Block] = [:]
    private var locals: [UInt32: UInt32] = [:]
    private var audioAllocations:Set<UInt32> = []
    private var pathElevatorAllocations: Set<UInt32> = []
    // Preserve issued sizes after retirement. A stale helper/path release must
    // never acquire authority over replacement storage at the same token.
    private var issuedPathElevatorAllocations: [UInt32: UInt32] = [:]
    private var sections: [UInt32: Section] = [:]
    private var tls: [UInt32: pthread_key_t] = [:]
    // Observation history records allocations from the same physical ledger.
    // Retired bytes are copied before free; live bytes always come from owned.
    private var allocationHistory: [(token: UInt32, count: UInt32, kind: String)] = []
    private var retiredBytes: [String: [UInt8]] = [:]
    // Diagnostic physical release history, like events, outside gameplay state.
    // Includes direct scene-owner releases as well as source scalar deletion.
    private(set) var sceneObjectRetirements: [(token: UInt32, bytes: [UInt8])] = []
    private var applicationTLSOwners: [UInt32: ClawTokenHeap.AllocationIdentity] = [:]
    private var tlsOwners: [UInt32: ClawTokenHeap.AllocationIdentity] = [:]
    private var publications: [UInt32: ClawTokenHeap.AllocationIdentity] = [:]
    private var borrowed: [ClawNativeCanonicalHost.TLSBorrowed] = []
    var beforeObjectAllocation: ((ClawNativeCanonicalHost.ObjectAllocationRequest) -> Void)?
    let sceneObjectAllocations: Bool
    private var sceneObjects: Set<UInt32> = []
    // Keep issued tokens until this owner retires, so a stale/double scene free
    // cannot fall through to a foreign replacement at the same virtual address.
    private var issuedSceneObjects: Set<UInt32> = []
    var failTLSSet = false
    private var nextTLS: UInt32 = 0
    private var nextData: UInt32 = 0x62000000
    private let allocationAlignment: UInt32
    private var nextHandle: UInt32 = 0x78000000
    private var performingService = false
    private var servicingManager: UInt32?
    private(set) var events: [Event] = []
    // Failure injection remains a physical allocation boundary, never a game
    // return. Returning true produces the API's documented allocation failure.
    var failAllocation: ((UInt32) -> Bool)?
    var beforeService: ((UInt32, [UInt32]) throws -> Void)?
    var afterService: ((UInt32,[UInt32],UInt32) throws -> Void)?
    var incidentalResult: UInt32 = 0

    struct SavedState: Codable, Equatable {
        struct Allocation: Codable, Equatable { let token: UInt32, count: UInt32, kind: String }
        struct Shared: Codable, Equatable {
            let witness: ClawSnapshotWitness
            let requested: UInt32, capacity: UInt32, generation: UInt64
        }
        struct SectionRecord: Codable, Equatable {
            let manager: UInt32, witness: ClawSnapshotWitness
            let state: ClawNativeMfcLocks.State
        }
        let targets: [UInt32: UInt32], logicalThread: UInt32, alignment: UInt32
        let sceneObjectAllocations: Bool, sharedStorage: Bool, sharedSections: Bool
        let owned: [UInt32: ClawSnapshotWitness], imports: [UInt32: ClawSnapshotWitness]
        let managers: [UInt32: ClawSnapshotWitness], tlsOwners: [UInt32: ClawSnapshotWitness]
        let publications: [UInt32: ClawSnapshotWitness], applicationTLSOwners: [UInt32: ClawSnapshotWitness]
        let sharedAllocations: [UInt32: Shared]
        let blocks: [Block], locals: [UInt32: UInt32], sections: [SectionRecord]
        let tlsValues: [UInt32: UInt32], nextTLS: UInt32, nextData: UInt32, nextHandle: UInt32
        let audioAllocations: Set<UInt32>, pathAllocations: Set<UInt32>, issuedPaths: [UInt32: UInt32]
        let sceneObjects: Set<UInt32>, issuedSceneObjects: Set<UInt32>
        let allocationHistory: [Allocation], retiredBytes: [String: [UInt8]]
        let borrowed: [ClawNativeCanonicalHost.TLSBorrowed]
        let applicationTargets: [UInt32: UInt32], applicationInputs: [UInt32: UInt32]
        let applicationReceiver: UInt32, receiverWitness: ClawSnapshotWitness?
        let raiseTarget: UInt32?, raiseWitness: ClawSnapshotWitness?
        let cursorSuccess: Bool, cursorX: Int32, cursorY: Int32, currentThreadHandle: UInt32
        let failTLSSet: Bool, incidentalResult: UInt32
    }
    private func snapshotBoundary() throws {
        guard Thread.current === executionThread, !performingService, servicingManager == nil,
              host.snapshotQuiescent, sections.values.allSatisfy({ $0.state.depth == 0 }),
              sharedSections?.records.values.allSatisfy({ $0.depth == 0 && $0.owner == 0 }) ?? true
        else { throw ClawSnapshotError.activeFrame }
        // Diagnostic callbacks are reconnected by the candidate graph factory;
        // injected allocation failures cannot silently become normal allocation.
        guard failAllocation == nil else { throw ClawSnapshotError.invalidState }
    }
    func savedState() throws -> SavedState {
        try snapshotBoundary()
        func records(_ entries: [UInt32: ClawTokenHeap.AllocationIdentity], count: UInt32) -> [UInt32: ClawSnapshotWitness] {
            Dictionary(uniqueKeysWithValues: entries.map { token, identity in
                (token, ClawSnapshotWitness(heap: host.heap, token: token, count: count, identity: identity, interior: true))
            })
        }
        return SavedState(targets: targets, logicalThread: logicalThread, alignment: allocationAlignment,
            sceneObjectAllocations: sceneObjectAllocations, sharedStorage: sharedStorage != nil, sharedSections: sharedSections != nil,
            owned: Dictionary(uniqueKeysWithValues: owned.map { token, span in
                (token, ClawSnapshotWitness(heap: host.heap, token: token, count: span.count, identity: span.identity, interior: sharedStorage != nil))
            }), imports: records(importIdentities, count: 4), managers: records(managers, count: 0x34),
            tlsOwners: records(tlsOwners, count: 4), publications: records(publications, count: 4),
            applicationTLSOwners: records(applicationTLSOwners, count: 0x1074),
            sharedAllocations: Dictionary(uniqueKeysWithValues: sharedAllocations.map { token, span in
                (token, .init(witness: ClawSnapshotWitness(heap: host.heap, token: token, count: span.capacity, identity: span.identity),
                              requested: span.requested, capacity: span.capacity, generation: span.generation))
            }), blocks: blocks, locals: locals, sections: sections.keys.sorted().map { token in
                let section = sections[token]!
                return .init(manager: section.manager, witness: ClawSnapshotWitness(heap: host.heap, token: token, count: 24, identity: section.identity, interior: true), state: section.state)
            }, tlsValues: logicalTLSValues, nextTLS: nextTLS, nextData: nextData, nextHandle: nextHandle,
            audioAllocations: audioAllocations, pathAllocations: pathElevatorAllocations, issuedPaths: issuedPathElevatorAllocations,
            sceneObjects: sceneObjects, issuedSceneObjects: issuedSceneObjects,
            allocationHistory: allocationHistory.map { .init(token: $0.token, count: $0.count, kind: $0.kind) },
            retiredBytes: retiredBytes, borrowed: borrowed, applicationTargets: applicationTargets, applicationInputs: applicationInputs,
            applicationReceiver: applicationReceiver, receiverWitness: applicationReceiverIdentity.map {
                ClawSnapshotWitness(heap: host.heap, token: applicationReceiver, count: 0xc0, identity: $0, interior: true)
            }, raiseTarget: jointRaiseImport?.target, raiseWitness: jointRaiseImport.map {
                ClawSnapshotWitness(heap: host.heap, token: 0x546958, count: 4, identity: $0.identity, interior: true)
            }, cursorSuccess: cursorSuccess, cursorX: cursorPoint.0, cursorY: cursorPoint.1, currentThreadHandle: currentThreadHandle,
            failTLSSet: failTLSSet, incidentalResult: incidentalResult)
    }

    private final class PreparedTLS {
        var keys: [UInt32: pthread_key_t]? = [:]
        deinit { for key in keys?.values ?? Dictionary<UInt32, pthread_key_t>().values { pthread_key_delete(key) } }
    }
    func prepareRestore(_ value: SavedState, heap plan: ClawTokenHeap.RestorePlan) throws -> () throws -> Void {
        try snapshotBoundary(); try host.heap.validateRestore(plan)
        guard value.targets == targets, value.logicalThread == logicalThread, value.alignment == allocationAlignment,
              value.sceneObjectAllocations == sceneObjectAllocations, value.sharedStorage == (sharedStorage != nil),
              value.sharedSections == (sharedSections != nil), value.nextData >= 0x03000000, value.nextData < 0x70000000,
              value.nextData & (allocationAlignment - 1) == 0, value.nextTLS < 65536,
              value.tlsValues.keys.allSatisfy({ $0 < value.nextTLS }),
              Set(value.blocks.map(\.handle)).count == value.blocks.count,
              Set(value.sections.map { $0.state.section }).count == value.sections.count,
              value.sceneObjects.isSubset(of: value.issuedSceneObjects),
              value.pathAllocations.isSubset(of: Set(value.issuedPaths.keys)),
              (value.receiverWitness == nil) == (value.applicationReceiver == 0),
              (value.raiseTarget == nil) == (value.raiseWitness == nil)
        else { throw ClawSnapshotError.invalidState }
        func identities(_ entries: [UInt32: ClawSnapshotWitness], count: UInt32? = nil) throws -> [UInt32: ClawTokenHeap.AllocationIdentity] {
            var result: [UInt32: ClawTokenHeap.AllocationIdentity] = [:]
            for (token, witness) in entries {
                guard witness.reference.token == token, count == nil || witness.reference.count == count else { throw ClawSnapshotError.invalidState }
                result[token] = try witness.resolve(in: plan)
            }
            return result
        }
        let ownedIDs = try identities(value.owned), imports = try identities(value.imports, count: 4)
        let managerIDs = try identities(value.managers, count: 0x34), tlsIDs = try identities(value.tlsOwners, count: 4)
        let publicationIDs = try identities(value.publications, count: 4), applicationIDs = try identities(value.applicationTLSOwners, count: 0x1074)
        var restoredShared: [UInt32: ClawNativeCanonicalHost.CrtAllocationWitness] = [:]
        for (token, span) in value.sharedAllocations {
            guard span.witness.reference.token == token, span.witness.reference.count == span.capacity,
                  span.requested > 0, span.requested <= span.capacity else { throw ClawSnapshotError.invalidState }
            restoredShared[token] = .init(token: token, requested: span.requested, capacity: span.capacity,
                generation: span.generation, identity: try span.witness.resolve(in: plan))
        }
        var restoredSections: [UInt32: Section] = [:]
        for record in value.sections {
            guard record.state.depth == 0, record.state.owner == 0, record.witness.reference.token == record.state.section,
                  record.witness.reference.count == 24 else { throw ClawSnapshotError.invalidState }
            let section = Section(record.state.section, manager: record.manager, identity: try record.witness.resolve(in: plan))
            section.state = record.state; restoredSections[record.state.section] = section
        }
        let receiverIdentity = try value.receiverWitness?.resolve(in: plan)
        let raiseIdentity = try value.raiseWitness?.resolve(in: plan)
        let preparedTLS = PreparedTLS()
        for (index, value) in value.tlsValues {
            var key = pthread_key_t()
            guard pthread_key_create(&key, nil) == 0 else { throw ClawSnapshotError.invalidState }
            preparedTLS.keys![index] = key
            guard pthread_setspecific(key, UnsafeMutableRawPointer(bitPattern: UInt(value))) == 0 else { throw ClawSnapshotError.invalidState }
        }
        return { [self] in
            try snapshotBoundary(); try host.heap.validateInstalledRestore(plan)
            guard let keys = preparedTLS.keys else { throw ClawSnapshotError.invalidState }
            for key in tls.values { pthread_key_delete(key) }
            tls = keys; preparedTLS.keys = nil
            owned = Dictionary(uniqueKeysWithValues: value.owned.map { ($0.key, (ownedIDs[$0.key]!, $0.value.reference.count)) })
            importIdentities = imports; managers = managerIDs; tlsOwners = tlsIDs; publications = publicationIDs
            applicationTLSOwners = applicationIDs; sharedAllocations = restoredShared
            globals = Dictionary(uniqueKeysWithValues: value.blocks.map { ($0.handle, $0) }); locals = value.locals; sections = restoredSections
            nextTLS = value.nextTLS; nextData = value.nextData; nextHandle = value.nextHandle
            audioAllocations = value.audioAllocations; pathElevatorAllocations = value.pathAllocations
            issuedPathElevatorAllocations = value.issuedPaths; sceneObjects = value.sceneObjects; issuedSceneObjects = value.issuedSceneObjects
            allocationHistory = value.allocationHistory.map { ($0.token, $0.count, $0.kind) }; retiredBytes = value.retiredBytes; borrowed = value.borrowed
            applicationTargets = value.applicationTargets; applicationInputs = value.applicationInputs
            applicationReceiver = value.applicationReceiver; applicationReceiverIdentity = receiverIdentity
            jointRaiseImport = value.raiseTarget.map { ($0, raiseIdentity!) }
            cursorSuccess = value.cursorSuccess; cursorPoint = (value.cursorX, value.cursorY); currentThreadHandle = value.currentThreadHandle
            failTLSSet = value.failTLSSet; incidentalResult = value.incidentalResult; events.removeAll()
        }
    }

    init(host: ClawNativeCanonicalHost, sha256: String, importTargets: [UInt32: UInt32],
         locks: ClawNativeMfcLocks? = nil,
         allocationBase: UInt32 = 0x62000000, allocationAlignment: UInt32 = 16, logicalThread: UInt32 = 1,
         sharedStorage: ClawNativeCanonicalHost.SourceSharedStorage? = nil, sharedSections: ClawNativePhysicalSections? = nil,
         sceneObjectAllocations: Bool = false) throws {
        guard sha256 == Self.imageHash, locks == nil || locks!.host === host,
              sharedStorage.map({ $0.sharedHeap === host.heap }) ?? true,
              sharedSections.map({ $0.heap === host.heap && $0.logicalThread==logicalThread && $0.valid() }) ?? true,
              sharedStorage == nil || (sharedSections != nil && locks?.sharedSections === sharedSections && sharedStorage?.sharedSectionOwner === sharedSections) else { throw Failure.invalidImage }
        // The physical policy is explicit so an independently captured source
        // unit may select eight-byte tokens without changing the ordinary
        // application's existing sixteen-byte allocation sequence.
        guard allocationAlignment == 8 || allocationAlignment == 16,
              allocationBase >= 0x03000000, allocationBase < 0x70000000,
              allocationBase & (allocationAlignment - 1) == 0 else { throw Failure.invalidStorage }
        guard !sceneObjectAllocations || (sharedStorage == nil && allocationAlignment == 16) else { throw Failure.invalidStorage }
        self.sceneObjectAllocations = sceneObjectAllocations
        guard Set(importTargets.keys) == Set(Self.importArities.keys),
              Set(importTargets.values).count == importTargets.count else { throw Failure.invalidImport }
        for (slot, target) in importTargets {
            guard target >= 0x710000 && target < 0x711000, claw_canonical_lookup(target) == nil else {
                throw Failure.invalidImport
            }
            if host.heap.overlaps(slot, count: 4) {
                guard host.heap.containingAllocationIdentity(at: slot, count: 4) != nil,
                      let pointer = host.heap.lookup(slot, words: 1), pointer[0] == target else { throw Failure.invalidImport }
            }
        }
        self.sharedStorage=sharedStorage;self.sharedSections=sharedSections
        self.host = host; self.locks = locks; self.logicalThread = logicalThread
        self.nextData = allocationBase; self.allocationAlignment = allocationAlignment
        targets = Dictionary(uniqueKeysWithValues: importTargets.map { ($0.value, $0.key) })
        for (slot, target) in importTargets where !host.heap.overlaps(slot, count: 4) {
            host.heap.store(token: slot, words: 1)[0] = target
            owned[slot] = (host.heap.allocationIdentity(at: slot, count: 4)!, 4)
        }
        for slot in importTargets.keys {
            importIdentities[slot] = host.heap.containingAllocationIdentity(at: slot, count: 4)!
        }
    }
    private func validImport(_ slot: UInt32) -> Bool {
        guard let identity = importIdentities[slot],
              host.heap.containingAllocationIdentity(at: slot, count: 4) === identity,
              let target = host.heap.lookup(slot, words: 1)?[0] else { return false }
        return targets[target] == slot
    }
    var blocks: [Block] { globals.values.sorted { $0.handle < $1.handle } }
    var sectionStates: [ClawNativeMfcLocks.State] {
        if let sharedSections { return sharedSections.records.values.filter { managerForSection($0.address) != nil }.map {
            .init(section:$0.address,owner:$0.owner,depth:$0.depth,entered:$0.entered,left:$0.left)
        }.sorted { $0.section<$1.section } }
        return sections.values.map(\.state).sorted { $0.section<$1.section }
    }
    var managerBytes: [String: [UInt8]] {
        Dictionary(uniqueKeysWithValues: managers.compactMap { token, identity in
            guard host.heap.containingAllocationIdentity(at: token, count: 0x34) === identity,
                  let pointer = host.heap.lookupBytes(token, count: 0x34) else { return nil }
            return (String(token), Array(UnsafeBufferPointer(start: pointer, count: 0x34)))
        })
    }
    var blockBytes: [String: [UInt8]] {
        Dictionary(uniqueKeysWithValues: blocks.compactMap { block in
            guard validStorage(block.data, block.size) else { return nil }
            return (String(block.data), Array(UnsafeBufferPointer(start: host.heap.lookupBytes(block.data, count: block.size)!, count: Int(block.size))))
        })
    }
    var localBytes: [String: [UInt8]] {
        Dictionary(uniqueKeysWithValues: locals.compactMap { token, count in
            guard validStorage(token, count) else { return nil }
            return (String(token), Array(UnsafeBufferPointer(start: host.heap.lookupBytes(token, count: count)!, count: Int(count))))
        })
    }
    var tlsIndices: [UInt32] { tls.keys.sorted() }
    var localPointers: [UInt32] { locals.keys.sorted() }
    var nextGlobalHandle: UInt32 { nextHandle }
    var nextTLSIndex: UInt32 { nextTLS }
    var localRequestedSizes: [UInt32:UInt32] { locals }
    var logicalTLSValues: [UInt32:UInt32] { Dictionary(uniqueKeysWithValues:tls.keys.compactMap { index in tlsValue(index).map { (index,$0) } }) }
    // The bounded joint policy has no service that mutates last-error state.
    var lastErrorValue: UInt32 { 0 }

    private func storage(_ count: UInt32, zero: Bool = false, kind: String = "local") throws -> UInt32 {
        guard count > 0, count <= 4 << 20 else { throw Failure.exhausted }
        if sceneObjectAllocations && kind == "object-malloc" && (count == 0x5c || count == 0x1b0 || count == 0x28 || count == 0x38) {
            // Scene voices can follow lazy resource loads after a contact bind.
            // Like wind storage, they follow the shared physical scene cursor.
            let token=host.heap.allocate(bytes:count)
            guard token != 0,UInt64(token)+UInt64(count)+15 < 0x70000000,
                  let bytes=host.heap.lookupBytes(token,count:count),
                  let identity=host.heap.allocationIdentity(at:token,count:count) else {throw Failure.exhausted}
            bytes.update(repeating:zero ? 0:0xcc,count:Int(count))
            nextData=max(nextData,(token+count+15) & ~15)
            owned[token]=(identity,count)
            if count != 0x38 { sceneObjects.insert(token);issuedSceneObjects.insert(token) }
            allocationHistory.append((token,count,kind))
            return token
        }
        if sceneObjectAllocations && kind == "object-malloc" &&
            (count == 0x1b4 || count == 0x1b8 || count == 0x1c8 || count == 0x174 || count == 0xa4 || count == 0xa8 || count == 0xb8 || count == 0x6c || count == 0x70 || count == 0x48 || count == 0x50 || count == 0x54 || count == 0x58 || count == 0x64 || count == 0x410 || (count == 0x7c && host.punkRatTransportActive) || count == 0x498 || count == 0x438 || count == 0x450 || count == 0x440 || count == 0x430 || count == 0x4b8 || count == 0x4d8 || count == 0x4e8 || count == 0x4e0 || count == 0x4a0 || count == 0x460 || count == 0x488 || count == 0x4b0 || count == 0x508 || count == 0x478 || (count == 0x480 && host.cutThroatTransportActive) || (count == 0xd48 && host.omarTransportActive)) {
            // All elected scene extents use the same minimum-aware cursor,
            // including exact RedTail helper storage. The minimum keeps
            // this Memory owner's sequence while following ordinary scene work.
            // The PunkRat child is consumed through canonical spans, so its actor
            // uses the exact source extent rather than legacy snapshot padding.
            let paddedActor = count == 0x1b4 && !host.punkRatTransportActive
            let token = host.heap.allocateSceneObject(bytes: count, minimumToken: nextData, legacyActorPadding: paddedActor)
            guard token != 0 else { throw Failure.exhausted }
            guard token >= nextData, UInt64(token)+UInt64(count)+15 < 0x70000000 else {
                host.heap.free(token); throw Failure.exhausted
            }
            guard let bytes = host.heap.lookupBytes(token, count: count) else { throw Failure.exhausted }
            bytes.update(repeating: zero ? 0 : 0xcc, count: Int(count))
            nextData = (token + (paddedActor ? 512 : count) + 15) & ~15
            owned[token] = (host.heap.allocationIdentity(at: token, count: count)!, count)
            sceneObjects.insert(token); issuedSceneObjects.insert(token)
            allocationHistory.append((token, count, kind))
            return token
        }
        if let sharedStorage {
            let token=try sharedStorage.sharedMalloc(count)
            guard token != 0 else { throw Failure.exhausted }
            let allocation=try sharedStorage.sharedAllocation(token)
            guard allocation.requested==count,let bytes=host.heap.lookupBytes(token,count:count) else { throw Failure.invalidStorage }
            if zero { bytes.update(repeating:0,count:Int(count)) }
            sharedAllocations[token]=allocation;owned[token]=(allocation.identity,count)
            allocationHistory.append((token,count,kind));return token
        }
        // Remaining elected extents retain
        // their exact storage in this heap/ledger without granting a generic
        // scene-actor allocation permission.
        // An occupied token is exhaustion; never resize or overwrite its owner.
        let token = nextData, padding = allocationAlignment - 1
        let end = UInt64(token) + UInt64(count) + UInt64(padding)
        guard end < 0x70000000, !host.heap.overlaps(token, count: (count + 3) & ~3) else { throw Failure.exhausted }
        nextData = UInt32(end) & ~padding
        let bytes = host.heap.storeBytes(token: token, count: count)
        bytes.update(repeating: zero ? 0 : 0xcc, count: Int(count))
        owned[token] = (host.heap.allocationIdentity(at: token, count: count)!, count)
        allocationHistory.append((token, count, kind))
        return token
    }
    private func validStorage(_ token: UInt32, _ count: UInt32) -> Bool {
        guard let span = owned[token], span.count >= count else { return false }
        if let sharedStorage {
            guard let prior=sharedAllocations[token],let live=try? sharedStorage.sharedAllocation(token),
                  prior.requested==span.count,live.requested==prior.requested,live.capacity==prior.capacity,
                  live.generation==prior.generation,live.identity === prior.identity,
                  host.heap.allocationIdentity(at:token,count:prior.capacity) === prior.identity else { return false }
            return true
        }
        return host.heap.allocationIdentity(at: token, count: span.count) === span.identity
    }
    private func retire(_ token: UInt32) {
        if let span=owned[token],validStorage(token,span.count) {
            owned.removeValue(forKey:token)
            sceneObjects.remove(token)
            if let bytes = host.heap.lookupBytes(token, count: span.count) {
                retiredBytes[String(token)] = Array(UnsafeBufferPointer(start: bytes, count: Int(span.count)))
            }
            if let sharedStorage { try? sharedStorage.sharedFree(token);sharedAllocations.removeValue(forKey:token) }
            else { host.heap.free(token) }
        }
    }
    func createManager() throws -> UInt32 {
        guard Thread.current === executionThread, !performingService, !host.physicalServiceInProgress else { throw Failure.invalidOwnership }
        let token = try storage(0x34, kind: "manager")
        try registerManager(token)
        return token
    }
    // Borrowed managers are explicitly registered and stay owned by their caller.
    func registerManager(_ token: UInt32) throws {
        guard Thread.current === executionThread, !performingService, !host.physicalServiceInProgress, managers[token] == nil,
              token & 3 == 0, let identity = host.heap.containingAllocationIdentity(at: token, count: 0x34) else { throw Failure.invalidStorage }
        managers[token] = identity
        if owned[token] == nil { borrowed.append(.init(address: token, size: 0x34, kind: "static-manager")) }
    }
    private func managerForSection(_ token: UInt32) -> UInt32? {
        guard token >= 0x1c else { return nil }
        let manager = token - 0x1c
        guard let identity = managers[manager],
              host.heap.containingAllocationIdentity(at: manager, count: 0x34) === identity else { return nil }
        return manager
    }
    private func global(_ handle: UInt32) throws -> Block {
        guard let block = globals[handle], validStorage(block.data, block.size) else { throw Failure.invalidStorage }
        return block
    }
    private func allocateGlobal(_ flags: UInt32, _ count: UInt32) throws -> UInt32 {
        guard flags == 0x2002 || flags == 0x2042 || flags == 2 || flags == 0x42 else { throw Failure.invalidStorage }
        let data = try storage(count, zero: flags & 0x40 != 0, kind: "global"), handle = nextHandle
        nextHandle += 4
        globals[handle] = Block(handle: handle, data: data, size: count, flags: flags, locks: 0)
        return handle
    }
    private func allocationFails(_ slot: UInt32) throws -> Bool {
        let rejected = failAllocation?(slot) == true
        // Failure hooks are allowed to inspect or invalidate physical state.
        // A callback cannot authorize allocation after reentry or IAT removal.
        guard host.fault == nil, validImport(slot), validRegisteredTLSStorage(), servicingManager.map(ownsSourceManager) ?? true else { throw Failure.invalidImport }
        guard host.validatePhysicalAuthority(at: slot) else { throw Failure.invalidOwnership }
        return rejected
    }
    private func run(_ slot: UInt32, _ a: [UInt32]) throws -> UInt32 {
        switch slot {
        case 0x546a90:
            if try allocationFails(slot) { return UInt32.max }
            guard nextTLS < UInt32.max else { return UInt32.max }
            var key = pthread_key_t()
            guard pthread_key_create(&key, nil) == 0 else { return UInt32.max }
            let index = nextTLS; nextTLS += 1; tls[index] = key; return index
        case 0x546a7c:
            guard let key = tls[a[0]] else { throw Failure.invalidOwnership }
            return UInt32(UInt(bitPattern: pthread_getspecific(key)))
        case 0x546a84:
            guard let key = tls[a[0]] else { throw Failure.invalidOwnership }
            if failTLSSet { return 0 }
            return pthread_setspecific(key, UnsafeMutableRawPointer(bitPattern: UInt(a[1]))) == 0 ? 1 : 0
        case 0x546aa4, 0x546aac, 0x546a9c, 0x546aa0:
            guard let manager = managerForSection(a[0]), let identity = managers[manager] else { throw Failure.invalidOwnership }
            if let sharedSections {
                return try sharedSections.perform(slot:slot,address:a[0])
            }
            if slot == 0x546aa4 {
                guard sections[a[0]] == nil else { throw Failure.invalidOwnership }
                sections[a[0]] = Section(a[0], manager: manager, identity: identity)
            } else {
                guard let section = sections[a[0]], section.identity === identity else { throw Failure.invalidOwnership }
                if slot == 0x546aac {
                    guard section.state.depth < UInt32.max, section.lock.try() else { throw Failure.invalidOwnership }
                    section.state.owner = logicalThread; section.state.depth += 1; section.state.entered &+= 1
                } else if slot == 0x546a9c {
                    guard section.state.depth > 0 else { throw Failure.invalidOwnership }
                    section.state.depth -= 1; section.state.left &+= 1
                    if section.state.depth == 0 { section.state.owner = 0 }
                    section.lock.unlock()
                } else {
                    guard section.state.depth == 0 else { throw Failure.invalidOwnership }
                    sections.removeValue(forKey: a[0])
                }
            }
            return incidentalResult
        case 0x546b1c:
            if try allocationFails(slot) { return 0 }
            do { return try allocateGlobal(a[0], a[1]) } catch Failure.exhausted { return 0 }
        case 0x546a8c:
            if a[0] == 0 { return 0 }
            guard let block = globals.values.first(where: { $0.data == a[0] }) else { throw Failure.invalidOwnership }
            return try global(block.handle).handle
        case 0x5469c4:
            if a[0] == 0 { return 0 }
            var block = try global(a[0]); guard block.locks < UInt32.max else { throw Failure.invalidOwnership }
            block.locks += 1; globals[a[0]] = block; return block.data
        case 0x5469c8:
            var block = try global(a[0]); guard block.locks > 0 else { throw Failure.invalidOwnership }
            block.locks -= 1; globals[a[0]] = block; return block.locks == 0 ? 0 : 1
        case 0x546a88:
            var block = try global(a[0])
            guard block.locks == 0, a[2] == 0x2002 || a[2] == 0x2042 || a[2] == 2 || a[2] == 0x42 else { throw Failure.invalidOwnership }
            if try allocationFails(slot) { return 0 }
            guard validStorage(block.data, block.size) else { throw Failure.invalidStorage }
            let data: UInt32
            do { data = try storage(a[1], zero: a[2] & 0x40 != 0, kind: "global") } catch Failure.exhausted { return 0 }
            host.heap.lookupBytes(data, count: a[1])!.update(from: host.heap.lookupBytes(block.data, count: block.size)!, count: Int(min(a[1], block.size)))
            retire(block.data); block.data = data; block.size = a[1]; block.flags = a[2]
            globals[a[0]] = block; return block.handle
        case 0x546ac0:
            if a[0] == 0 { return 0 }
            let block = try global(a[0]); guard block.locks == 0 else { throw Failure.invalidOwnership }
            retire(block.data); globals.removeValue(forKey: a[0]); return 0
        case 0x546aa8:
            guard a[0] == 0 || a[0] == 0x40 else { throw Failure.invalidStorage }
            if try allocationFails(slot) { return 0 }
            do { let data = try storage(a[1], zero: a[0] & 0x40 != 0); locals[data] = a[1]; return data }
            catch Failure.exhausted { return 0 }
        case 0x546a80:
            // Published scene actor/state tokens have fixed source extents.
            // Ordinary LocalReAlloc must not move one and discard its padding
            // or leave scene links pointing at a retired allocation identity.
            guard host.permitsRobberThiefRawMemoryMutation(a[0]), !sceneObjects.contains(a[0]), let count = locals[a[0]], validStorage(a[0], count),
                  a[2] == 2 || a[2] == 0x42 else { throw Failure.invalidOwnership }
            if try allocationFails(slot) { return 0 }
            guard validStorage(a[0], count) else { throw Failure.invalidOwnership }
            let data: UInt32
            do { data = try storage(a[1], zero: a[2] & 0x40 != 0) } catch Failure.exhausted { return 0 }
            host.heap.lookupBytes(data, count: a[1])!.update(from: host.heap.lookupBytes(a[0], count: count)!, count: Int(min(count, a[1])))
            retire(a[0]); locals.removeValue(forKey: a[0]); locals[data] = a[1]; return data
        case 0x5469d8:
            if a[0] == 0 { return 0 }
            guard host.permitsRobberThiefRawMemoryMutation(a[0]), let count = locals[a[0]], validStorage(a[0], count) else { throw Failure.invalidOwnership }
            retire(a[0]); locals.removeValue(forKey: a[0]); return 0
        default: throw Failure.invalidImport
        }
    }
    func service(_ call: ClawCall) -> UInt32? {
        guard host.fault == nil else { return nil }
        let slot = Self.importArities[call.function] == nil ? targets[call.function] : call.function
        guard let slot, let count = Self.importArities[slot] else { return nil }
        guard !performingService else {
            host.fail(UInt32(CLAW_FAULT_ABI), at: slot, diagnostic: .unsupportedABI)
            return nil
        }
        guard call.sourceTransferVersion == 0, call.sourceTransferKind == 0, call.sourceTransferSite == 0,
              call.sourceCallerFunction == 0, call.sourceDisposition == nil,
              call.compilerContext == nil, call.sourceContext == nil, call.sourceReturnPC == 0, call.argumentCount == count, call.receiver == 0, call.receiver2 == 0, call.x87ArgumentCount == 0,
              call.stackPointer >= CLAW_STACK_BASE, call.stackPointer & 3 == 0,
              UInt64(call.stackPointer) + 4 * (1 + UInt64(count)) <= UInt64(CLAW_STACK_END),
              Thread.current === executionThread else {
            host.fail(UInt32(CLAW_FAULT_ABI), at: call.function, diagnostic: .unsupportedABI); return nil
        }
        let args = withUnsafeBytes(of: call.arguments) { Array($0.bindMemory(to: UInt32.self).prefix(Int(count))) }
        guard validImport(slot) else { host.fail(UInt32(CLAW_FAULT_HALT), at: slot); return nil }
        if [UInt32(0x546aa4), 0x546aac, 0x546a9c].contains(slot), managerForSection(args[0]) == nil,
           args[0] == ClawNativeMfcLocks.master || (args[0] >= 0x5408f0 && args[0] <= 0x540a70 && (args[0] - 0x5408f0) % 24 == 0) {
            return locks?.service(call)
        }
        return performService(slot, target: call.function, stackPointer: call.stackPointer, arguments: args)
    }
    // Both ordinary and source callers reach this operation once. Source frame
    // validation and CPU return transport stay in the canonical host.
    private func performService(_ slot: UInt32, target: UInt32, stackPointer: UInt32,
                                arguments args: [UInt32], manager: UInt32? = nil) -> UInt32? {
        guard host.fault == nil, Thread.current === executionThread, !performingService else {
            host.fail(UInt32(CLAW_FAULT_ABI), at: slot, diagnostic: .unsupportedABI)
            return nil
        }
        guard host.beginPhysicalService(at: slot) else { return nil }
        defer { host.endPhysicalService() }
        performingService = true
        servicingManager = manager
        defer { performingService = false; servicingManager = nil }
        var result: UInt32?
        defer { events.append(Event(function: slot, target: target, stackPointer: stackPointer,
                                    arguments: args, result: result, completed: result != nil, blocks: blocks, sections: sectionStates, managerBytes: managerBytes, blockBytes: blockBytes, localBytes: localBytes)) }
        do {
            try beforeService?(slot, args)
            guard host.fault == nil, validImport(slot), validRegisteredTLSStorage(), servicingManager.map(ownsSourceManager) ?? true else { throw Failure.invalidImport }
            guard host.validatePhysicalAuthority(at: slot) else { return nil }
            let value = try run(slot, args)
            try afterService?(slot,args,value)
            guard host.fault == nil, validImport(slot), validRegisteredTLSStorage(), servicingManager.map(ownsSourceManager) ?? true else { throw Failure.invalidImport }
            guard host.validatePhysicalReturn(at: slot) else { return nil }
            result = value; return result
        }
        catch { host.fail(UInt32(CLAW_FAULT_HALT), at: slot); return nil }
    }
    deinit {
        precondition(Thread.current === executionThread)
        for section in sections.values { for _ in 0..<section.state.depth { section.lock.unlock() } }
        for key in tls.values { pthread_key_delete(key) }
        for (token,span) in owned where validStorage(token,span.count) {
            if let sharedStorage,sharedAllocations[token] != nil { try? sharedStorage.sharedFree(token) }
            else { host.heap.free(token) }
        }
    }
}

extension ClawNativeMfcMemory: ClawNativeCanonicalHost.SourceAllocationProvider {
    var sourceImportTarget: UInt32 { targets.first(where: { $0.value == 0x546aa8 })!.key }

    func validSourceBinding(for host: ClawNativeCanonicalHost) -> Bool {
        self.host === host && host.fault == nil && Thread.current === executionThread && validImport(0x546aa8)
    }

    func allocateSourceLocal(_ request: ClawNativeCanonicalHost.SourceAllocationRequest) -> UInt32? {
        // A foreign thread has no authority even to consume the request or
        // mutate this thread's sticky fault. The valid issuer may still use it.
        guard Thread.current === executionThread else { return nil }
        guard validSourceBinding(for: host), request.slot == 0x546aa8,
              request.target == sourceImportTarget, request.returnPC == 0x502f91,
              request.arguments.count == 2, request.arguments[0] == 0x40,
              ClawNativeCanonicalHost.supportsSourceFactorySize(request.arguments[1]),
              request.consume(for: host, provider: self) else {
            host.fail(UInt32(CLAW_FAULT_ABI), at: 0x546aa8, diagnostic: .unsupportedABI)
            return nil
        }
        return performService(request.slot, target: request.target,
                              stackPointer: request.context.esp, arguments: request.arguments)
    }

    func ownsSourceLocal(_ token: UInt32, count: UInt32) -> Bool {
        Thread.current === executionThread && locals[token] == count && validStorage(token, count)
    }

    func sourceLocalSnapshot(_ token: UInt32) -> Data? {
        guard Thread.current === executionThread, let count = locals[token],
              ownsSourceLocal(token, count: count), let bytes = host.heap.lookupBytes(token, count: count) else { return nil }
        return Data(bytes: bytes, count: Int(count))
    }
}


extension ClawNativeMfcMemory: ClawNativeCanonicalHost.SourceManagerProvider {
    func validManagerBinding(for host: ClawNativeCanonicalHost) -> Bool {
        self.host === host && Thread.current === executionThread && host.fault == nil &&
            Self.importArities.keys.allSatisfy(validImport) && (sharedSections?.valid() ?? true) && sharedAllocations.allSatisfy({ validStorage($0.key,$0.value.requested) })
    }
    func managerImportTarget(_ slot: UInt32) -> UInt32? {
        guard Thread.current === executionThread, validImport(slot) else { return nil }
        return host.heap.lookup(slot, words: 1)?[0]
    }
    func ownsSourceManager(_ token: UInt32) -> Bool {
        guard Thread.current === executionThread, let identity = managers[token] else { return false }
        return host.heap.containingAllocationIdentity(at: token, count: 0x34) === identity
    }
    func ownsSourceBlock(_ data: UInt32, count: UInt32) -> Bool {
        Thread.current === executionThread && globals.values.contains(where: { $0.data == data && $0.size == count }) && validStorage(data, count)
    }
    func managerSnapshot() -> ClawNativeCanonicalHost.SourceManagerSnapshot {
        .init(blocks: blocks.map { .init(handle: $0.handle, data: $0.data, size: $0.size, flags: $0.flags, locks: $0.locks) },
              sections: sectionStates.map { .init(section: $0.section, owner: $0.owner, depth: $0.depth, initialized: $0.initialized, entered: $0.entered, left: $0.left) },
              managerBytes: managerBytes, blockBytes: blockBytes, tlsIndices: tlsIndices)
    }
    func serviceSourceManager(_ request: ClawNativeCanonicalHost.SourceManagerRequest) -> UInt32? {
        guard Thread.current === executionThread else { return nil }
        guard validManagerBinding(for: host), ownsSourceManager(request.manager),
              request.target == managerImportTarget(request.slot),
              request.arguments.count == Int(Self.importArities[request.slot] ?? UInt32.max),
              request.consume(for: host, provider: self) else {
            host.fail(UInt32(CLAW_FAULT_ABI), at: request.slot, diagnostic: .unsupportedABI); return nil
        }
        return performService(request.slot, target: request.slot == 0x5469c4 ? request.target : request.slot,
                              stackPointer: request.context.esp, arguments: request.arguments, manager: request.manager)
    }
}


extension ClawNativeMfcMemory: ClawNativeCanonicalHost.SourceModuleProvider {
    var moduleLocks: ClawNativeCanonicalHost.SourceLocksProvider? { locks }
    func registerModuleSingleton() throws {
        guard Thread.current === executionThread, !performingService, !host.physicalServiceInProgress,
              publications[0x53eca0] == nil,
              let identity = host.heap.containingAllocationIdentity(at: 0x53eca0, count: 4) else { throw Failure.invalidStorage }
        publications[0x53eca0] = identity
        borrowed.append(.init(address: 0x53eca0, size: 4, kind: "static-module-singleton"))
    }
    func ownsModuleSingleton() -> Bool {
        guard Thread.current === executionThread, let identity = publications[0x53eca0] else { return false }
        return host.heap.containingAllocationIdentity(at: 0x53eca0, count: 4) === identity
    }

    func registerApplicationTLSOwner(_ module: UInt32) -> Bool {
        guard Thread.current === executionThread, !performingService, !host.physicalServiceInProgress,
              ownsSourceLocal(module, count: 0x1074),
              let identity = (sharedStorage == nil ? host.heap.allocationIdentity(at:module,count:0x1074) : host.heap.containingAllocationIdentity(at:module,count:0x1074)) else { return false }
        if let prior = applicationTLSOwners[module] { return prior === identity && ownsApplicationTLSOwner(module) }
        let slot = module + 0x1070
        guard tlsOwners[slot] == nil else { return false }
        applicationTLSOwners[module] = identity; tlsOwners[slot] = identity
        return true
    }
    func ownsApplicationTLSOwner(_ module: UInt32) -> Bool {
        guard Thread.current === executionThread, let identity = applicationTLSOwners[module] else { return false }
        return ownsSourceLocal(module, count: 0x1074) &&
            (sharedStorage == nil ? host.heap.allocationIdentity(at:module,count:0x1074) : host.heap.containingAllocationIdentity(at:module,count:0x1074)) === identity && tlsOwners[module + 0x1070] === identity
    }
    func applicationTLSOwnerSnapshot() -> [ClawNativeCanonicalHost.TLSInteriorOwner] {
        applicationTLSOwners.keys.sorted().compactMap { module in
            guard ownsApplicationTLSOwner(module), let index = allocationHistory.firstIndex(where: { $0.token == module && $0.count == 0x1074 }) else { return nil }
            return .init(address: module + 0x1070, size: 4, allocation: module, allocationSize: 0x1074, identity: UInt32(index + 1), offset: 0x1070)
        }
    }
    func registerTLSOwner(_ token: UInt32) throws {
        guard Thread.current === executionThread, !performingService, !host.physicalServiceInProgress, tlsOwners[token] == nil,
              token & 3 == 0, let identity = host.heap.containingAllocationIdentity(at: token, count: 4) else { throw Failure.invalidStorage }
        tlsOwners[token] = identity
        if owned[token] == nil { borrowed.append(.init(address: token, size: 4, kind: "slot-owner")) }
    }
    func registerTLSPublication(_ token: UInt32) throws {
        guard Thread.current === executionThread, !performingService, !host.physicalServiceInProgress, token == 0x540af0,
              publications[token] == nil, let identity = host.heap.containingAllocationIdentity(at: token, count: 4) else { throw Failure.invalidStorage }
        publications[token] = identity
        borrowed.append(.init(address: token, size: 4, kind: "publication"))
    }
    func createTLSOwner() throws -> UInt32 {
        guard Thread.current === executionThread, !performingService, !host.physicalServiceInProgress else { throw Failure.invalidOwnership }
        let token = try storage(4, zero: true, kind: "slot-owner")
        try registerTLSOwner(token); return token
    }
    func createTLSLocal(count: UInt32, zero: Bool) throws -> UInt32 {
        guard Thread.current === executionThread, !performingService, !host.physicalServiceInProgress else { throw Failure.invalidOwnership }
        let token = try storage(count, zero: zero); locals[token] = count; return token
    }
    private func validRegisteredTLSStorage() -> Bool {
        publications.allSatisfy { host.heap.containingAllocationIdentity(at: $0.key, count: 4) === $0.value } &&
            tlsOwners.allSatisfy { host.heap.containingAllocationIdentity(at: $0.key, count: 4) === $0.value }
    }
    func validTLSBinding(for host: ClawNativeCanonicalHost) -> Bool {
        validManagerBinding(for: host) && publications[0x540af0] != nil && validRegisteredTLSStorage()
    }
    func ownsTLSOwner(_ token: UInt32) -> Bool {
        guard Thread.current === executionThread, let identity = tlsOwners[token] else { return false }
        return host.heap.containingAllocationIdentity(at: token, count: 4) === identity
    }
    func ownsTLSLocal(_ token: UInt32, count: UInt32) -> Bool {
        guard Thread.current === executionThread else { return false }
        return locals.contains { base, size in
            UInt64(token) >= UInt64(base) && UInt64(token) + UInt64(count) <= UInt64(base) + UInt64(size) && validStorage(base, size)
        }
    }
    func tlsValue(_ index: UInt32) -> UInt32? {
        guard Thread.current === executionThread, let key = tls[index] else { return nil }
        return UInt32(UInt(bitPattern: pthread_getspecific(key)))
    }
    func tlsSnapshot() -> ClawNativeCanonicalHost.TLSSnapshot {
        var bytes = retiredBytes
        for item in allocationHistory where validStorage(item.token, item.count) {
            bytes[String(item.token)] = Array(UnsafeBufferPointer(start: host.heap.lookupBytes(item.token, count: item.count)!, count: Int(item.count)))
        }
        return .init(manager: managerSnapshot(),
            ownerBytes: Dictionary(uniqueKeysWithValues: tlsOwners.keys.filter(ownsTLSOwner).map { token in
                (String(token), Array(UnsafeBufferPointer(start: host.heap.lookupBytes(token, count: 4)!, count: 4)))
            }), globals: Dictionary(uniqueKeysWithValues: publications.compactMap { token, identity in
                guard host.heap.containingAllocationIdentity(at: token, count: 4) === identity else { return nil }
                return (String(token), host.heap.lookup(token, words: 1)![0])
            }), locals: Dictionary(uniqueKeysWithValues: locals.map { (String($0.key), $0.value) }), localBytes: localBytes,
            allocations: allocationHistory.enumerated().map { index, item in
                .init(identity: UInt32(index + 1), address: item.token, size: item.count, kind: item.kind, live: validStorage(item.token, item.count))
            }, allocationBytes: bytes, borrowedStorage: borrowed,
            tlsValues: Dictionary(uniqueKeysWithValues: tls.keys.map { (String($0), tlsValue($0)!) }))
    }
}


extension ClawNativeMfcMemory: ClawNativeCanonicalHost.SourceApplicationProvider {
    func configureApplicationServices(importTargets: [UInt32: UInt32], cursorSuccess: Bool, x: Int32, y: Int32, threadHandle: UInt32) throws {
        guard Thread.current === executionThread,!performingService,!host.physicalServiceInProgress,
              applicationTargets.isEmpty,Set(importTargets.keys)==[0x546cd0,0x5469bc,0x5469c0],
              Set(importTargets.values).count==3 else { throw Failure.invalidImport }
        guard importTargets.allSatisfy({slot,target in target>=0x710000 && target<0x711000 && claw_canonical_lookup(target)==nil && (!host.heap.overlaps(slot,count:4) || (sharedStorage != nil && host.heap.containingAllocationIdentity(at:slot,count:4) != nil && host.heap.lookup(slot,words:1)?[0]==target))}) else {throw Failure.invalidImport}
        for (slot,target) in importTargets {
            if !host.heap.overlaps(slot,count:4) {
                host.heap.store(token:slot,words:1)[0]=target
                owned[slot]=(host.heap.allocationIdentity(at:slot,count:4)!,4)
            }
            importIdentities[slot]=host.heap.containingAllocationIdentity(at:slot,count:4)!
        }
        if sharedStorage != nil {
            guard let target=host.heap.lookup(0x546958,words:1)?[0],target>=0x710000,target<0x711000,
                  !importTargets.values.contains(target),!targets.keys.contains(target),claw_canonical_lookup(target)==nil,
                  let identity=host.heap.containingAllocationIdentity(at:0x546958,count:4) else { throw Failure.invalidImport }
            jointRaiseImport=(target,identity)
        }
        applicationTargets=importTargets;self.cursorSuccess=cursorSuccess;cursorPoint=(x,y);currentThreadHandle=threadHandle
    }
    // Test-caller input storage remains borrowed and is never an allocation result.
    func registerApplicationReceiver(_ token: UInt32, inputRanges: [UInt32: UInt32], imageBase: UInt32, imageCount: UInt32) throws {
        guard Thread.current === executionThread,!performingService,!host.physicalServiceInProgress,
              let identity=host.heap.containingAllocationIdentity(at:token,count:0xc0),
              UInt64(token)+0xc0<=UInt64(CLAW_STACK_BASE) || token>=CLAW_STACK_END,
              inputRanges.allSatisfy({host.heap.containingAllocationIdentity(at:$0.key,count:$0.value) != nil}) else { throw Failure.invalidStorage }
        func overlaps(_ base: UInt32, _ count: UInt32) -> Bool {
            UInt64(token)<UInt64(base)+UInt64(count) && UInt64(base)<UInt64(token)+0xc0
        }
        // The caller owns this object; a live physical allocation or static
        // manager/lock/publication cannot be relabeled as a CWinApp receiver.
        guard !owned.contains(where:{overlaps($0.key,$0.value.count)}),
              !borrowed.filter({$0.kind != "caller-owned-application-object"}).contains(where:{overlaps($0.address,$0.size)}),
              !overlaps(0x5408e0,0x244) else {throw Failure.invalidOwnership}
        applicationReceiver=token;applicationReceiverIdentity=identity
        applicationInputs=inputRanges;applicationInputs[token]=0xc0
        // The image may consist of adjacent allocations owned by different services.
        applicationInputs[imageBase]=imageCount
        borrowed.removeAll {$0.kind=="caller-owned-application-object"}
        borrowed.append(.init(address:token,size:0xc0,kind:"caller-owned-application-object"))
    }
    func validApplicationBinding(for host: ClawNativeCanonicalHost) -> Bool {
        self.host === host && Thread.current === executionThread && locks?.logicalThreadIdentifier==logicalThread && applicationTargets.count==3 &&
            (jointRaiseImport.map { host.heap.containingAllocationIdentity(at:0x546958,count:4) === $0.identity && host.heap.lookup(0x546958,words:1)?[0]==$0.target } ?? true) &&
            applicationTargets.allSatisfy {slot,target in host.heap.containingAllocationIdentity(at:slot,count:4) === importIdentities[slot] && host.heap.lookup(slot,words:1)?[0]==target}
    }
    func ownsApplicationReceiver(_ token: UInt32) -> Bool {
        Thread.current === executionThread && token==applicationReceiver && applicationReceiverIdentity != nil &&
            host.heap.containingAllocationIdentity(at:token,count:0xc0) === applicationReceiverIdentity
    }
    func ownsApplicationAllocation(_ token: UInt32, count: UInt32) -> Bool {
        Thread.current === executionThread && allocationHistory.contains {$0.token==token && $0.count==count && $0.kind=="malloc"} && validStorage(token,count)
    }
    func applicationImportTarget(_ slot: UInt32) -> UInt32? {
        guard validApplicationBinding(for:host) else { return nil }
        if slot==0x546958 { return jointRaiseImport?.target }
        return applicationTargets[slot]
    }
    func applicationBytes() -> [String:[UInt8]] {
        guard Thread.current === executionThread else {return [:]}
        return Dictionary(uniqueKeysWithValues:applicationInputs.map {token,count in
            var bytes:[UInt8]=[];var offset:UInt32=0
            while offset<count {
                var low:UInt32=1,high=count-offset
                while low<high {let mid=low+(high-low+1)/2;if host.heap.lookupBytes(token+offset,count:mid) != nil {low=mid}else{high=mid-1}}
                guard let p=host.heap.lookupBytes(token+offset,count:low) else {return (String(token),[])}
                bytes.append(contentsOf:UnsafeBufferPointer(start:p,count:Int(low)));offset+=low
            }
            return (String(token),bytes)
        })
    }
    func serviceSourceApplication(_ request: ClawNativeCanonicalHost.SourceApplicationRequest) -> UInt32? {
        guard Thread.current === executionThread else {return nil}
        let slot=request.function
        guard validApplicationBinding(for:host),ownsApplicationReceiver(request.receiver),
              request.target==(slot==0x4a48e0 ? slot : applicationImportTarget(slot)),
              request.consume(for:host,provider:self),!performingService,host.beginPhysicalService(at:slot) else {
            host.fail(UInt32(CLAW_FAULT_ABI),at:slot,diagnostic:.unsupportedABI);return nil
        }
        performingService=true
        var result:UInt32?
        defer {
            performingService=false;host.endPhysicalService()
            events.append(.init(function:slot,target:request.target,stackPointer:request.context.esp,arguments:request.arguments,
                result:result,completed:result != nil && host.fault==nil,blocks:blocks,sections:sectionStates,
                managerBytes:managerBytes,blockBytes:blockBytes,localBytes:localBytes))
        }
        do {
            beforeSourceApplicationService?(request)
            guard request.validReturn(for:host),host.validatePhysicalAuthority(at:slot),ownsApplicationReceiver(request.receiver) else {return nil}
            try beforeService?(slot,request.arguments)
            guard request.validReturn(for:host),host.validatePhysicalAuthority(at:slot),ownsApplicationReceiver(request.receiver) else {return nil}
            switch slot {
            case 0x546958:
                guard jointRaiseImport != nil,request.returnPC==0x4a56cf,request.arguments.count==4,
                      request.arguments[0]==0xe06d7363,request.arguments[1]==1,request.arguments[2]==3 else { throw Failure.invalidStorage }
                host.fail(UInt32(CLAW_FAULT_HALT),at:slot,diagnostic:.nativeFault)
                return nil
            case 0x4a48e0:
                guard request.arguments.count==1,request.arguments[0]>0,request.arguments[0]<=1<<20 else {throw Failure.invalidStorage}
                let failed=failAllocation?(slot)==true
                guard request.validReturn(for:host),host.validatePhysicalAuthority(at:slot) else {return nil}
                result=failed ? 0 : try storage(request.arguments[0],kind:"malloc")
            case 0x546cd0:
                guard request.arguments==[request.receiver+0x5c],let p=host.heap.lookupBytes(request.arguments[0],count:8) else {throw Failure.invalidStorage}
                if cursorSuccess {
                    var values=[UInt32(bitPattern:cursorPoint.0).littleEndian,UInt32(bitPattern:cursorPoint.1).littleEndian]
                    values.withUnsafeMutableBytes {UnsafeMutableRawPointer(p).copyMemory(from:$0.baseAddress!,byteCount:8)}
                }
                result=cursorSuccess ? 1 : 0
            case 0x5469bc:guard request.arguments.isEmpty else {throw Failure.invalidStorage};result=currentThreadHandle
            case 0x5469c0:guard request.arguments.isEmpty else {throw Failure.invalidStorage};result=logicalThread
            default:throw Failure.invalidImport
            }
            if let value=result { try afterService?(slot,request.arguments,value) }
            guard request.validReturn(for:host),host.validatePhysicalReturn(at:slot) else {result=nil;return nil}
            return result
        } catch {host.fail(UInt32(CLAW_FAULT_HALT),at:slot);return nil}
    }
}

extension ClawNativeMfcMemory: ClawNativeCanonicalHost.SourceJointApplicationProvider {
    func sharesStaticPhysicalOwner(_ provider: ClawNativeCanonicalHost.SourceCrtProvider) -> Bool {
        sharedStorage.map { ($0 as AnyObject) === (provider as AnyObject) } == true &&
        sharedSections != nil && sharedStorage?.sharedSectionOwner === sharedSections && locks?.sharedSections === sharedSections
    }
}

// Version 1 physical CRT malloc cut for the finite object allocation election.
// The admitted operator-new body executes its own saves, retry and return path.
extension ClawNativeMfcMemory: ClawNativeCanonicalHost.AudioAllocationProvider, ClawNativeCanonicalHost.PathElevatorAllocationProvider, ClawNativeCanonicalHost.JumpSwitchAllocationProvider, ClawSceneObjectAllocationOwner {
    var sceneObjectHeap: ClawTokenHeap { host.heap }
    var canRegisterSceneObjectOwner: Bool {
        sceneObjectAllocations && !performingService && !host.physicalServiceInProgress && validObjectAllocationBinding(for: host)
    }
    var sceneObjectPointers: [UInt32] { sceneObjects.sorted() }
    func claimsSceneObject(_ token: UInt32) -> Bool { issuedSceneObjects.contains(token) }

    // Install this owner with scene.registerObjectAllocationOwner before using
    // host.withObjectAllocation(provider:). ActorDestruction then retires both
    // physical storage and the canonical ledger through the same owner.
    @discardableResult func releaseSceneObject(_ token: UInt32) -> Bool {
        guard Thread.current === executionThread else { return false }
        guard sceneObjectAllocations, !performingService, !host.physicalServiceInProgress, host.permitsSceneObjectRelease(token),
              validObjectAllocationBinding(for: host), sceneObjects.contains(token),
              let count = locals[token], ownsObjectAllocation(token, count: count),
              let bytes = host.heap.lookupBytes(token, count: count) else {
            host.fail(UInt32(CLAW_FAULT_ABI), at: token, diagnostic: .unsupportedABI)
            return false
        }
        if host.robberThiefTransportActive || host.cutThroatTransportActive || host.rauxTransportActive || host.omarTransportActive || host.punkRatTransportActive {
            sceneObjectRetirements.append((token, Array(UnsafeBufferPointer(start: bytes, count: Int(count)))))
        }
        retire(token)
        locals.removeValue(forKey: token)
        return true
    }

    func validObjectAllocationBinding(for host: ClawNativeCanonicalHost) -> Bool {
        self.host === host && Thread.current === executionThread && host.fault==nil &&
            owned.allSatisfy {validStorage($0.key,$0.value.count)}
    }
    func ownsObjectAllocation(_ token: UInt32, count: UInt32) -> Bool {
        Thread.current === executionThread && locals[token]==count && validStorage(token,count)
    }
    @discardableResult func releaseAudioAllocation(_ token:UInt32) -> Bool {
        guard !performingService,!host.physicalServiceInProgress,audioAllocations.contains(token),
              ownsObjectAllocation(token,count:0x38) else {return false}
        retire(token);locals.removeValue(forKey:token);audioAllocations.remove(token);return true
    }
    @discardableResult func releasePathElevatorAllocation(_ token: UInt32, count: UInt32) -> Bool {
        guard Thread.current === executionThread else { return false }
        guard !performingService, !host.physicalServiceInProgress,
              validObjectAllocationBinding(for: host), count == 0x104 || count == 0x18,
              issuedPathElevatorAllocations[token] == count, pathElevatorAllocations.contains(token),
              ownsObjectAllocation(token, count: count) else {
            host.fail(UInt32(CLAW_FAULT_ABI), at: 0x4f6428, diagnostic: .unsupportedABI)
            return false
        }
        retire(token)
        locals.removeValue(forKey: token)
        pathElevatorAllocations.remove(token)
        events.append(.init(function: 0x4f6428, target: 0x4f6428, stackPointer: 0, arguments: [token],
            result: 0, completed: true, blocks: blocks, sections: sectionStates,
            managerBytes: managerBytes, blockBytes: blockBytes, localBytes: localBytes))
        return true
    }
    func releaseTownGuardMember(_ token: UInt32) -> Bool {
        guard Thread.current === executionThread,!performingService,!host.physicalServiceInProgress,
              host.permitsTownGuardMemberRelease(token),validObjectAllocationBinding(for:host),
              let count=locals[token],ownsObjectAllocation(token,count:count) else {
            host.fail(UInt32(CLAW_FAULT_ABI),at:token,diagnostic:.unsupportedABI);return false
        }
        if host.robberThiefTransportActive,let bytes=host.heap.lookupBytes(token,count:count) {
            sceneObjectRetirements.append((token,Array(UnsafeBufferPointer(start:bytes,count:Int(count)))))
        }
        retire(token);locals.removeValue(forKey:token);return true
    }
    // The Conveyor constructor's temporary CString shares this ledger. Only
    // an active single-use constructor-local lease authorizes its exact extent.
    func serviceConveyorString(_ request:ClawNativeCanonicalHost.ConveyorStringRequest) -> UInt32? {
        guard Thread.current === executionThread,validObjectAllocationBinding(for:host),
              request.token != 0,request.count>13,request.count<=1<<20,!performingService,
              request.consume(for:host,provider:self),host.beginPhysicalService(at:0x4f6428) else {
            host.fail(UInt32(CLAW_FAULT_ABI),at:0x4f6480,diagnostic:.unsupportedABI);return nil
        }
        performingService=true
        let function:UInt32=0x4f6428
        let argument=request.token
        var result:UInt32?
        defer {
            performingService=false;host.endPhysicalService()
            events.append(.init(function:function,target:function,stackPointer:0,arguments:[argument],result:result,
                completed:result != nil && host.fault==nil,blocks:blocks,sections:sectionStates,
                managerBytes:managerBytes,blockBytes:blockBytes,localBytes:localBytes))
        }
        do {
            try beforeService?(function,[argument])
            guard request.validReturn(for:host),host.validatePhysicalAuthority(at:function) else {throw Failure.invalidOwnership}
            guard ownsObjectAllocation(request.token,count:request.count),
                  let header=host.heap.lookup(request.token,words:3),header[0]==1,
                  header[1]==request.count-13,header[2]==request.count-13,
                  host.heap.lookupBytes(request.token+request.count-1,count:1)?[0]==0 else {throw Failure.invalidOwnership}
            header[0]=0
            retire(request.token);locals.removeValue(forKey:request.token);result=0
            if let value=result {try afterService?(function,[argument],value)}
            guard request.validReturn(for:host),host.validatePhysicalReturn(at:function),
                  !host.heap.overlaps(request.token,count:request.count) else {throw Failure.invalidOwnership}
            return result
        } catch {host.fail(UInt32(CLAW_FAULT_HALT),at:function);return nil}
    }
    func allocateObject(_ request: ClawNativeCanonicalHost.ObjectAllocationRequest) -> UInt32? {
        guard Thread.current === executionThread else {return nil}
        guard validObjectAllocationBinding(for:host),request.function==0x4a48e0,request.returnPC==0x4f63ff,
              (request.root==0x4f65f2 && host.permitsConveyorStringNew(request.count)) ||
              ([UInt32(0x4c7fa0),0x4c8060,0x4c8da0].contains(request.root) &&
               (request.count==0x174 || (request.root==0x4c8da0 && request.count==0x1b4))) ||
                ([UInt32(0x4b4430),0x4b42e0].contains(request.root) && request.count==0x38) ||
                ([UInt32(0x495d40),0x495e00,0x48a800].contains(request.root) && request.count==0x7c) ||
                (request.root==0x4559e0 && request.count==0xa8) ||
                ([UInt32(0x457620),0x4561c0].contains(request.root) && request.count==0xb8) ||
                (request.root==0x49ee30 && (request.count==0x104 || request.count==0x18)) ||
                (request.root==0x4379d0 && request.count==0x480) ||
                (request.root==0x485270 && request.count==0x478) ||
                (request.root==0x409860 && request.count==0x4a0) ||
                (request.root==0x489730 && request.count==0x4b0) ||
                (request.root==0x421200 && request.count==0x488) ||
                (request.root==0x4922c0 && request.count==0x460) ||
                (request.root==0x486e90 && request.count==0x440) ||
                (request.root==0x441be0 && request.count==0x430) ||
                (request.root==0x474330 && request.count==0x410 && host.punkRatTransportActive) ||
                (request.root==0x4493c0 && request.count==0x7c && host.punkRatTransportActive) ||
                (request.root==0x449c40 && request.count==0x438) ||
                (request.root==0x482820 && request.count==0x4b8) ||
                (request.root==0x47e210 && request.count==0x478 && host.rauxTransportActive) ||
                (request.root==0x47f6e0 && request.count==0x508) ||
                (request.root==0x4633a0 && request.count==0xd48 && host.omarTransportActive) ||
                (request.root==0x464f20 && request.count==0x48 && host.omarTransportActive) ||
                (request.root==0x4689b0 && request.count==0x4e8) ||
                (request.root==0x458680 && request.count==0x4d8) ||
                (request.root==0x493eb0 && request.count==0x4e0) ||
                (request.root==0x45ff00 && request.count==0x4e0) ||
                (request.root==0x465580 && request.count==0x450) ||
                ([UInt32(0x496050),0x4968d0,0x434190].contains(request.root) && request.count==0x498) ||
                (request.root==0x40f7b0 && request.count==0xa4) ||
                ([UInt32(0x453b10),0x4842b0].contains(request.root) && request.count==0x48) ||
                (request.root==0x406400 && request.count==0x70) ||
                (request.root==0x4073e0 && request.count==0x1b8) ||
                (request.root==0x48e4a0 && request.count==0x1c8) ||
                (request.root==0x4847b0 && request.count==0x5c) ||
                (request.root==0x4b3fe0 && request.count==0x28) ||
                (request.root==0x49f0a0 && request.count==0x1b0) ||
                (request.root==0x448d10 && request.count==0x50) ||
                (request.root==0x497eb0 && request.count==0x64) ||
                ([UInt32(0x4887b0),0x406dd0,0x414cc0,0x415350].contains(request.root) && request.count==0x54) ||
                ([UInt32(0x432570),0x448620,0x431320,0x4553d0].contains(request.root) && request.count==0x58) ||
                ([UInt32(0x40f870),0x488e30,0x45a2e0].contains(request.root) && request.count==0x6c),
              request.consume(for:host,provider:self),!performingService,host.beginPhysicalService(at:request.function) else {
            host.fail(UInt32(CLAW_FAULT_ABI),at:request.function,diagnostic:.unsupportedABI);return nil
        }
        performingService=true
        var result:UInt32?
        defer {
            performingService=false;host.endPhysicalService()
            events.append(.init(function:request.function,target:request.function,stackPointer:request.context.esp,arguments:[request.count],
                result:result,completed:result != nil && host.fault==nil,blocks:blocks,sections:sectionStates,
                managerBytes:managerBytes,blockBytes:blockBytes,localBytes:localBytes))
        }
        do {
            beforeObjectAllocation?(request)
            guard request.validReturn(for:host),host.validatePhysicalAuthority(at:request.function) else {throw Failure.invalidOwnership}
            try beforeService?(request.function,[request.count])
            guard request.validReturn(for:host),host.validatePhysicalAuthority(at:request.function) else {throw Failure.invalidOwnership}
            let failed=failAllocation?(request.function)==true
            guard request.validReturn(for:host),host.validatePhysicalAuthority(at:request.function) else {throw Failure.invalidOwnership}
            if failed {result=0}
            else {
                do {result=try storage(request.count,kind:"object-malloc")}
                catch Failure.exhausted {result=0}
            }
            if let token=result,token != 0 {
                locals[token]=request.count
                if sceneObjectAllocations && ([UInt32(0x4379d0),0x485270,0x457620,0x4561c0,0x4559e0,0x4887b0,0x40f7b0,0x40f870,0x488e30,0x432570,0x448620,0x448d10,0x414cc0,0x415350,0x431320,0x497eb0,0x482820,0x47f6e0,0x47e210,0x449c40,0x434190,0x48a800,0x493eb0,0x45ff00,0x4689b0,0x458680,0x465580,0x45a2e0,0x441be0,0x409860,0x489730,0x4922c0,0x421200,0x4553d0,0x406400,0x406dd0,0x4073e0,0x48e4a0,0x4847b0,0x4b3fe0,0x49f0a0].contains(request.root) ||
                    ([UInt32(0x4633a0),0x464f20].contains(request.root) && host.omarTransportActive) ||
                    ([UInt32(0x474330),0x4493c0].contains(request.root) && host.punkRatTransportActive) ||
                    (request.root==0x4c8da0 && (host.aquatisDynamiteTransportActive || host.omarTransportActive || host.punkRatTransportActive))) {
                    sceneObjects.insert(token);issuedSceneObjects.insert(token)
                }
                if request.count==0x38 {audioAllocations.insert(token)}
                if request.root==0x49ee30 {
                    pathElevatorAllocations.insert(token)
                    issuedPathElevatorAllocations[token]=request.count
                }
            }
            if let value=result {try afterService?(request.function,[request.count],value)}
            guard request.validReturn(for:host),host.validatePhysicalReturn(at:request.function),
                  result==0 || result.map({ownsObjectAllocation($0,count:request.count)})==true else {throw Failure.invalidOwnership}
            return result
        } catch {host.fail(UInt32(CLAW_FAULT_HALT),at:request.function);return nil}
    }
}

extension ClawNativeMfcMemory: ClawNativeCanonicalHost.TownGuardAllocationProvider {}
