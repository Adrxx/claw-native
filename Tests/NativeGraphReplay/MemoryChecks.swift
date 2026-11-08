import Foundation

// Native owner contracts. These inputs are independent of the sealed original
// profiles, and their count must never be reported as additional source paths.
private let memoryImports = Dictionary(uniqueKeysWithValues: ClawNativeMfcMemory.importArities.keys.sorted().enumerated().map { ($0.element, UInt32(0x710100 + $0.offset * 4)) })
private func ownerCall(_ slot: UInt32, _ args: [UInt32]) -> ClawCall {
    var c = ClawCall(); c.function = slot; c.argumentCount = UInt32(args.count)
    c.stackPointer = UInt32(CLAW_STACK_TOP) - 0x100
    withUnsafeMutableBytes(of:&c.arguments) { out in args.withUnsafeBytes { out.copyMemory(from:$0) } }
    return c
}
private func ownerContext(_ site: Host.SourceSite) -> ClawSourceContext {
    .init(size:72,version:1,inputMask:0x7ff,outputMask:0x7ff,eax:0,ebx:1,ecx:2,edx:3,esi:4,edi:5,ebp:6,esp:UInt32(CLAW_STACK_TOP),eip:site.function,eflags:2,fsHead:UInt32.max,preserveMask:0x472,reserved0:0,reserved1:0)
}
private func newOwner(_ host: Host, base: UInt32 = 0x62000000, alignment: UInt32 = 16) -> ClawNativeMfcMemory {
    try! .init(host:host,sha256:ClawNativeMfcMemory.imageHash,importTargets:memoryImports,allocationBase:base,allocationAlignment:alignment)
}
private func ownerFactory(_ host: Host, _ allocator: Host.SourceLocalAllocator, _ site: Host.SourceSite, expectSuccess: Bool = true) -> UInt32 {
    var c = ownerContext(site); var token: UInt32 = 0
    host.withSourceGraph(localAllocator:allocator) { graph in
        check(graph.writeStack(at:c.esp,data:word(site.rawValue)), "owner root continuation")
        let result = graph.invokeSource(at:site,context:&c)
        check(result.completed == expectSuccess, "owner root completion contract")
        if expectSuccess { check(result.eax != nil, "successful owner result present") }
        token = result.eax ?? 0
    }
    return token
}
private final class RequestSpy: Host.SourceAllocationProvider {
    let owner: ClawNativeMfcMemory
    let host: Host
    let consumes: Bool
    var retained: Host.SourceAllocationRequest?
    var foreignResult = true
    var attempts = 0
    init(_ owner: ClawNativeMfcMemory, _ host: Host, consumes: Bool) { self.owner = owner; self.host = host; self.consumes = consumes }
    var sourceImportTarget: UInt32 { owner.sourceImportTarget }
    func validSourceBinding(for host: Host) -> Bool { owner.validSourceBinding(for:host) }
    func allocateSourceLocal(_ request: Host.SourceAllocationRequest) -> UInt32? {
        attempts += 1; retained = request
        let group = DispatchGroup(); group.enter()
        DispatchQueue.global().async { self.foreignResult = request.consume(for:self.host,provider:self); group.leave() }
        group.wait()
        check(!foreignResult, "foreign thread cannot consume elected request")
        check(!request.consume(for:Host(heap:ClawTokenHeap()),provider:self), "foreign host cannot consume elected request")
        check(!request.consume(for:host,provider:owner), "foreign provider cannot consume elected request")
        if consumes {
            check(request.consume(for:host,provider:self), "exact elected provider consumes once")
            check(!request.consume(for:host,provider:self), "immediate second consumption rejected")
        }
        return 0
    }
    func ownsSourceLocal(_ token: UInt32, count: UInt32) -> Bool { false }
    func sourceLocalSnapshot(_ token: UInt32) -> Data? { nil }
}
func checkSharedMemoryContracts() {
    for (site,size) in [(Host.SourceSite.threadFactory,UInt32(0x118)),(.moduleFactory,UInt32(0x1074))] {
        // Both root sizes enter the same ordinary ownership and resize ledger.
        let host = Host(heap:ClawTokenHeap())
        let bound = newOwner(host)
        var adapter: Host.SourceLocalAllocator? = .init(host:host,provider:bound)
        check(adapter != nil, "owner adapter binding")
        let token = ownerFactory(host,adapter!,site)
        check(bound.localPointers == [token] && bound.ownsSourceLocal(token,count:size), "source publishes exact owner witness")
        check(!bound.ownsSourceLocal(token+1,count:size-1) && !bound.ownsSourceLocal(token,count:size+1), "interior and wrong extent cannot own")
        check(bound.events.count == 1, "one source owner event")
        adapter = nil
        check(bound.sourceLocalSnapshot(token)?.count == Int(size), "adapter teardown retains local")
        let pattern = Data((0..<Int(size)).map { UInt8(($0 * 19 + 11) & 255) })
        pattern.withUnsafeBytes { host.heap.lookupBytes(token,count:size)!.update(from:$0.bindMemory(to:UInt8.self).baseAddress!,count:Int(size)) }
        bound.failAllocation = { _ in true }
        check(bound.service(ownerCall(0x546a80,[token,size+31,0x42])) == 0, "resize zero contract")
        check(bound.sourceLocalSnapshot(token) == pattern && bound.ownsSourceLocal(token,count:size), "failed resize preserves bytes and ownership")
        bound.failAllocation = nil
        let moved = bound.service(ownerCall(0x546a80,[token,size+31,0x42]))!
        check(moved != 0 && moved != token, "ordinary moving resize of source local")
        check(bound.sourceLocalSnapshot(moved)?.prefix(Int(size)) == pattern, "explicit independent resize prefix")
        check(!bound.ownsSourceLocal(token,count:size) && bound.ownsSourceLocal(moved,count:size+31), "resize transfers exact ownership")
        check(bound.service(ownerCall(0x5469d8,[moved])) == 0 && bound.localPointers.isEmpty, "ordinary free source local")
    }
    for alignment in [UInt32(8),16] {
        let host = Host(heap:ClawTokenHeap()), base: UInt32 = alignment == 8 ? 0x62000008 : 0x62000000
        let owner = newOwner(host,base:base,alignment:alignment)
        let ordinary = owner.service(ownerCall(0x546aa8,[0x40,13]))!
        let a = Host.SourceLocalAllocator(host:host,provider:owner)!
        let first = ownerFactory(host,a,.threadFactory)
        let second = ownerFactory(host,Host.SourceLocalAllocator(host:host,provider:owner)!, .moduleFactory)
        check(ordinary == base && first % alignment == 0 && second % alignment == 0, "explicit alignment and shared cursor")
        check(Set(owner.localPointers) == Set([ordinary,first,second]) && owner.events.count == 3, "sequential ordinary and source owner ledger")
        check(owner.sourceLocalSnapshot(ordinary) == Data(repeating:0,count:13), "sibling ordinary bytes preserved")
        check(owner.service(ownerCall(0x5469d8,[first])) == 0 && owner.ownsSourceLocal(second,count:0x1074), "free preserves sibling")
    }
    do {
        let host = Host(heap:ClawTokenHeap()), owner = newOwner(Host(heap:ClawTokenHeap()))
        check(Host.SourceLocalAllocator(host:host,provider:owner) == nil, "foreign host cannot bind provider")
        let bound = newOwner(host)
        check(bound.service(ownerCall(0x546aa8,[0x40,13])) == 0x62000000, "ordinary default allocation base")
        check(bound.service(ownerCall(0x546aa8,[0x40,13])) == 0x62000010, "ordinary default sixteen-byte stride")
    }
    do {
        let host = Host(heap:ClawTokenHeap()), base: UInt32 = 0x62000000
        host.heap.storeBytes(token:base,count:0x118).update(repeating:0xa6,count:0x118)
        let identity = host.heap.allocationIdentity(at:base,count:0x118)!
        let owner = newOwner(host,base:base)
        _ = ownerFactory(host,Host.SourceLocalAllocator(host:host,provider:owner)!, .threadFactory,expectSuccess:false)
        check(host.fault?.address == 0x4f50fd, "occupied shared allocation policy reaches genuine missing throw")
        check(owner.localPointers.isEmpty && owner.events.count == 1 && owner.events[0].result == 0, "occupied span causes one zero allocation")
        check(host.heap.allocationIdentity(at:base,count:0x118) === identity, "occupied allocation identity preserved")
        check(Data(bytes:host.heap.lookupBytes(base,count:0x118)!,count:0x118) == Data(repeating:0xa6,count:0x118), "occupied source span bytes preserved")
    }
    for site in [Host.SourceSite.threadFactory,.moduleFactory] {
        let host = Host(heap:ClawTokenHeap()), owner = newOwner(host)
        owner.failAllocation = { _ in true }
        _ = ownerFactory(host,Host.SourceLocalAllocator(host:host,provider:owner)!,site,expectSuccess:false)
        check(owner.localPointers.isEmpty && owner.events.count == 1 && owner.events[0].result == 0, "genuine zero has one physical event")
        check(host.fault?.address == 0x4f50fd, "zero reaches genuine missing throw")
    }
    for borrowed in [false,true] {
        let host = Host(heap:ClawTokenHeap()), slot: UInt32 = 0x546aa8
        if borrowed {
            host.heap.storeBytes(token:slot-8,count:20).update(repeating:0x6b,count:20)
            for (iat,target) in memoryImports where iat >= slot-8 && iat+4 <= slot+12 {
                host.heap.lookup(iat,words:1)![0] = target
            }
        }
        var owner: ClawNativeMfcMemory? = newOwner(host)
        var adapter: Host.SourceLocalAllocator? = .init(host:host,provider:owner!)
        let token = ownerFactory(host,adapter!,.threadFactory)
        adapter = nil
        check(host.heap.lookupBytes(token,count:0x118) != nil && host.heap.lookupBytes(slot,count:4) != nil, "adapter lifetime distinct from owner")
        owner = nil
        check(host.heap.lookupBytes(token,count:1) == nil, "final owner retires source local")
        check((host.heap.lookupBytes(slot,count:4) != nil) == borrowed, "borrowed IAT destruction rights")
        if borrowed { check(Data(bytes:host.heap.lookupBytes(slot+8,count:4)!,count:4) == Data(repeating:0x6b,count:4), "borrowed IAT surrounding bytes survive") }
    }
    for replaceIAT in [false,true] {
        let host = Host(heap:ClawTokenHeap()); var owner: ClawNativeMfcMemory? = newOwner(host)
        var adapter: Host.SourceLocalAllocator? = .init(host:host,provider:owner!)
        let local = ownerFactory(host,adapter!,.threadFactory)
        let token: UInt32 = replaceIAT ? 0x546aa8 : local, size: UInt32 = replaceIAT ? 4 : 0x118
        host.heap.withStableFreedStorage {
            host.heap.free(token); host.heap.storeBytes(token:token,count:size).update(repeating:0xa7,count:Int(size))
            if replaceIAT { host.heap.lookup(token,words:1)![0] = memoryImports[token]! }
            let replacement = host.heap.allocationIdentity(at:token,count:size)!
            if replaceIAT {
                check(!owner!.validSourceBinding(for:host), "equal IAT word cannot restore identity")
                check(Host.SourceLocalAllocator(host:host,provider:owner!) == nil, "stale IAT rejects fresh adapter")
            } else {
                check(owner!.sourceLocalSnapshot(token) == nil && !owner!.ownsSourceLocal(token,count:size), "replacement local is not owner storage")
                check(owner!.service(ownerCall(0x5469d8,[token])) == nil, "stale free rejects replacement")
            }
            adapter = nil; owner = nil
            check(host.heap.allocationIdentity(at:token,count:size) === replacement, "owner teardown preserves replacement identity")
            if !replaceIAT { check(host.heap.lookupBytes(token,count:size)![Int(size)-1] == 0xa7, "owner preserves replacement bytes") }
        }
    }
    for consumes in [true,false] {
        let host = Host(heap:ClawTokenHeap()), owner = newOwner(host)
        let spy = RequestSpy(owner,host,consumes:consumes)
        _ = ownerFactory(host,Host.SourceLocalAllocator(host:host,provider:spy)!, .threadFactory,expectSuccess:false)
        check(spy.attempts == 1 && owner.events.isEmpty && owner.localPointers.isEmpty, "synthetic lease provider has no Memory effect")
        if consumes { check(host.fault?.address == 0x4f50fd, "consumed zero reaches real missing throw") }
        else { check(host.fault?.address != 0x4f50fd, "unconsumed zero rejected before guest throw") }
        check(!spy.retained!.consume(for:host,provider:spy), "synchronous return expires consumed or unused lease")
    }
    do {
        let host = Host(heap:ClawTokenHeap()), owner = newOwner(host)
        owner.beforeService = { _, _ in
            host.heap.free(0x546aa8); host.heap.storeBytes(token:0x546aa8,count:4)
            host.heap.lookup(0x546aa8,words:1)![0] = memoryImports[0x546aa8]!
        }
        _ = ownerFactory(host,Host.SourceLocalAllocator(host:host,provider:owner)!, .threadFactory,expectSuccess:false)
        check(owner.localPointers.isEmpty && !owner.events.contains(where: { $0.completed }), "hook IAT replacement rejects before completed allocation event")
    }
    do {
        let host = Host(heap:ClawTokenHeap()), owner = newOwner(host)
        var nested: UInt32? = 1
        owner.beforeService = { _, _ in nested = owner.service(ownerCall(0x546aa8,[0x40,13])) }
        _ = ownerFactory(host,Host.SourceLocalAllocator(host:host,provider:owner)!, .threadFactory,expectSuccess:false)
        check(nested == nil && !owner.events.contains(where: { $0.completed }) && owner.localPointers.isEmpty, "sticky reentrant rejection aborts outer physical effects")
    }
    for replaceIAT in [false,true] {
        let host = Host(heap:ClawTokenHeap()), owner = newOwner(host)
        var nested: UInt32? = 1
        owner.failAllocation = { _ in
            if replaceIAT {
                host.heap.free(0x546aa8); host.heap.storeBytes(token:0x546aa8,count:4)
                host.heap.lookup(0x546aa8,words:1)![0] = memoryImports[0x546aa8]!
            } else { nested = owner.service(ownerCall(0x546aa8,[0x40,13])) }
            return false
        }
        _ = ownerFactory(host,Host.SourceLocalAllocator(host:host,provider:owner)!, .threadFactory,expectSuccess:false)
        check(owner.localPointers.isEmpty && !owner.events.contains(where: { $0.completed }), "allocation callback invalidation prevents successful effect")
        if !replaceIAT { check(nested == nil, "allocation callback nested operation rejected") }
    }
    do {
        let host = Host(heap:ClawTokenHeap())
        let lockImports = Dictionary(uniqueKeysWithValues: ClawNativeMfcLocks.importSlots.sorted().enumerated().map { ($0.element, memoryImports[$0.element] ?? UInt32(0x710800 + $0.offset * 4)) })
        let locks = try! ClawNativeMfcLocks(host:host,sha256:ClawNativeMfcLocks.imageHash,initialBytes:[UInt8](repeating:0x5a,count:Int(ClawNativeMfcLocks.imageCount)),importTargets:lockImports)
        try! locks.adoptInitializedSection(ClawNativeMfcLocks.master)
        let owner = try! ClawNativeMfcMemory(host:host,sha256:ClawNativeMfcMemory.imageHash,importTargets:memoryImports,locks:locks)
        let states = locks.states, bytes = locks.imageBytes, eventCount = locks.events.count
        var nested: UInt32? = 1
        var setupRejected = false
        owner.beforeService = { _, _ in
            nested = owner.service(ownerCall(0x546aac,[ClawNativeMfcLocks.master]))
            do { _ = try owner.createManager() } catch { setupRejected = true }
        }
        _ = ownerFactory(host,Host.SourceLocalAllocator(host:host,provider:owner)!, .threadFactory,expectSuccess:false)
        check(nested == nil && setupRejected, "busy owner rejects delegated lock and manager setup")
        check(locks.states == states && locks.imageBytes == bytes && locks.events.count == eventCount, "reentry cannot reach delegated lock effects")
        check(owner.localPointers.isEmpty && !owner.events.contains(where: { $0.completed }), "delegated reentry aborts source allocation")
    }
    for alignment in [UInt32(0),1,4,12,32] {
        let host = Host(heap:ClawTokenHeap()); var rejected = false
        do { _ = try ClawNativeMfcMemory(host:host,sha256:ClawNativeMfcMemory.imageHash,importTargets:memoryImports,allocationBase:0x62000000,allocationAlignment:alignment) } catch { rejected = true }
        check(rejected && host.heap.lookupBytes(0x546aa8,count:1) == nil, "unsupported policy rejects before IAT ownership")
    }
}
