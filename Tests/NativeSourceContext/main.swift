import Foundation
import CryptoKit

var checks = 0
func check(_ value: @autoclosure () -> Bool, _ text: String) {
    checks += 1
    if !value() { fatalError("FAIL: \(text)") }
}
struct Reference: Decodable { let sha256: String; let stack_fill: UInt8; let rows: [Row] }
struct Row: Decodable {
    let initial: [String: UInt32]; let continuation: UInt32; let stores: [[UInt32]]
    let final: [String: UInt32]; let stack_sha256: String
}
func context(_ row: Row) -> ClawCompilerContext {
    let r = row.initial
    return ClawCompilerContext(size: 72, version: 1, inputMask: 0x7ff, outputMask: 0x7ff,
        eax:r["eax"]!, ebx:r["ebx"]!, ecx:r["ecx"]!, edx:r["edx"]!, esi:r["esi"]!, edi:r["edi"]!,
        ebp:r["ebp"]!, esp:r["esp"]!, eip:r["eip"]!, eflags:r["eflags"]!, fsHead:r["fsHead"]!,
        continuation:row.continuation, reserved0:0, reserved1:0)
}
func values(_ c: ClawCompilerContext) -> [String:UInt32] {
    ["eax":c.eax,"ebx":c.ebx,"ecx":c.ecx,"edx":c.edx,"esi":c.esi,"edi":c.edi,
     "ebp":c.ebp,"esp":c.esp,"eip":c.eip,"eflags":c.eflags,"fsHead":c.fsHead]
}
func word(_ value: UInt32) -> Data { var v=value.littleEndian; return withUnsafeBytes(of:&v) { Data($0) } }
let reference = try JSONDecoder().decode(Reference.self, from:Data(contentsOf: URL(fileURLWithPath:CommandLine.arguments[1])))
check(reference.sha256 == "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263", "pinned original reference")
check(reference.rows.count == 84, "all independent profiles")
for (index,row) in reference.rows.enumerated() {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap())
    var c=context(row)
    host.withSourceGraph { graph in
        check(graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:Data(repeating:reference.stack_fill,count:Int(CLAW_STACK_END-CLAW_STACK_BASE))),"fill")
        for store in row.stores { check(graph.writeStack(at:store[0],data:word(store[1])),"reference stack store") }
        let result=graph.invokeCompiler(at:.init(rawValue:row.continuation)!, context:&c)
        check(result.completed,"profile \(index) completion \(String(describing: result.fault))")
        check(values(c)==row.final,"profile \(index) CPU")
        let stack=graph.stackSnapshot()!
        check(SHA256.hash(data:stack).map{String(format:"%02x",$0)}.joined()==row.stack_sha256,"profile \(index) complete stack")
        check(c.size==72 && c.version==1 && c.inputMask==0x7ff && c.outputMask==0x7ff && c.continuation==row.continuation && c.reserved0==0 && c.reserved1==0,"immutable header")
    }
    check(host.fault==nil,"clean graph teardown")
}
let row=reference.rows[0]
let mutations: [(String,(inout ClawCompilerContext)->Void)] = [
 ("size",{$0.size=0}), ("version",{$0.version=2}), ("input mask",{$0.inputMask=0x7fe}),
 ("output mask",{$0.outputMask=0x5c1}), ("unknown mask",{$0.inputMask=0xfff}),
 ("reserved0",{$0.reserved0=1}), ("reserved1",{$0.reserved1=1}),
 ("unknown PC",{$0.continuation=0x50342a}), ("STOP PC",{$0.continuation=UInt32(CLAW_STACK_RETURN_SENTINEL)}),
 ("wrong handler",{$0.eax=0x508539}), ("wrong entry",{$0.eip=0x502335}),
 ("flags",{$0.eflags=0x202}), ("missing fixed flag",{$0.eflags=0}),
 ("unaligned FS",{$0.fsHead=UInt32(CLAW_STACK_BASE)+1}), ("straddling FS",{$0.fsHead=UInt32(CLAW_STACK_END)-8}),
 ("foreign FS",{$0.fsHead=0x61000000}), ("unaligned ESP",{$0.esp+=1}),
 ("below stack",{$0.esp=UInt32(CLAW_STACK_BASE)-4}), ("past stack",{$0.esp=UInt32(CLAW_STACK_END)}),
 ("headroom0",{$0.esp=UInt32(CLAW_STACK_BASE)}), ("headroom4",{$0.esp=UInt32(CLAW_STACK_BASE)+4}),
 ("headroom8",{$0.esp=UInt32(CLAW_STACK_BASE)+8}), ("headroom12",{$0.esp=UInt32(CLAW_STACK_BASE)+12})
]
for (name, mutate) in mutations {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap()); var c=context(row)
    host.withSourceGraph { graph in
        check(graph.writeStack(at:c.esp,data:word(c.continuation)),"prepare invalid \(name)")
        mutate(&c)
        let before=values(c)
        check(!graph.invokeCompiler(at:.threadFactory,context:&c).completed,"reject \(name)")
        check(values(c)==before,"reject \(name) before mutation")
        let first=host.fault
        check(!graph.invokeCompiler(at:.threadFactory,context:&c).completed && host.fault==first,"sticky \(name)")
    }
}
// Uppermost successful frame, sibling graphs and graph retirement.
for _ in 0..<2 {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap()); var c=context(row); c.esp=UInt32(CLAW_STACK_END)-4
    host.withSourceGraph { graph in
        check(graph.writeStack(at:c.esp,data:word(c.continuation)),"upper frame")
        check(graph.invokeCompiler(at:.threadFactory,context:&c).completed,"upper end-4 succeeds")
    }
}
do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap()); var saved:ClawNativeCanonicalHost.SourceGraph?
    host.withSourceGraph { saved=$0 }
    host.withSourceGraph { _ in
        var c=context(row)
        check(!saved!.invokeCompiler(at:.threadFactory,context:&c).completed,"retired graph cannot enter new graph")
    }
}
do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap())
    host.withSourceGraph { _ in
        check(host.withSourceGraph { _ in true } == nil,"reentrant graph")
        check(host.fault?.diagnostic == .recursiveCanonicalCall,"reentrancy diagnostic")
    }
}
for compiler in [false,true] {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap()); var c=context(row); var source=ClawSourceContext()
    withUnsafeMutablePointer(to:&c) { cp in withUnsafeMutablePointer(to:&source) { sp in
        var call=ClawCall();call.function=0x4a48c0;call.compilerContext=cp
        if compiler { call.sourceContext=sp;call.sourceReturnPC=0x50233f }
        check(!host.invoke(call).completed,"ordinary API rejects contextual/contradictory channels")
    }}
}
for site in [ClawNativeCanonicalHost.SourceSite.threadFactory,.moduleFactory] {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap(),dependency:{ _,_ in fatalError("must not fabricate contextual dependency") })
    var c=ClawSourceContext(size:72,version:1,inputMask:0x7ff,outputMask:0x7ff,
        eax:1,ebx:2,ecx:3,edx:4,esi:5,edi:6,ebp:0xffffffff,esp:UInt32(CLAW_STACK_TOP),eip:site.function,
        eflags:2,fsHead:0xffffffff,preserveMask:0x472,reserved0:0,reserved1:0)
    host.withSourceGraph { graph in
        let result=graph.invokeSource(at:site,context:&c)
        check(!result.completed,"factory must stop honestly")
        check(result.fault?.address==0x502f84,"factory executes admitted helper then stops at allocator: \(String(describing: result.fault))")
        check(result.fault?.code==UInt32(CLAW_FAULT_ABI),"missing source capability is ABI rejection")
    }
}
do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap(),maximumOperations:1); var c=context(row)
    host.withSourceGraph { graph in
        check(graph.writeStack(at:c.esp,data:word(c.continuation)),"budget frame")
        check(!graph.invokeCompiler(at:.threadFactory,context:&c).completed,"shared budget stops actual helper")
        check(host.fault?.code==UInt32(CLAW_FAULT_BUDGET),"budget diagnostic")
    }
}

do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap(),maximumOperations:100)
    host.withSourceGraph { graph in
        var successes=0
        for _ in 0..<100 {
            var c=context(row)
            check(graph.writeStack(at:c.esp,data:word(c.continuation)),"sibling shared frame")
            if graph.invokeCompiler(at:.threadFactory,context:&c).completed { successes+=1 }
            else { break }
        }
        check(successes>0 && successes<100 && host.fault?.code==UInt32(CLAW_FAULT_BUDGET),"budget shared across sibling entries")
    }
}
do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap())
    host.withSourceGraph { graph in
        var outer=context(reference.rows[28]); outer.esp=UInt32(CLAW_STACK_TOP)
        check(graph.writeStack(at:outer.esp,data:word(outer.continuation)),"outer registration frame")
        check(graph.invokeCompiler(at:.threadFactory,context:&outer).completed,"outer native registration")
        var inner=context(row);inner.esp=outer.esp-16;inner.ebp=outer.ebp;inner.fsHead=outer.fsHead
        check(graph.writeStack(at:inner.esp,data:word(inner.continuation)),"nested registration frame")
        check(graph.invokeCompiler(at:.threadFactory,context:&inner).completed,"nested native registration")
        let stack=graph.stackSnapshot()!
        let oldFS=stack.withUnsafeBytes { $0.loadUnaligned(fromByteOffset:Int(inner.fsHead-UInt32(CLAW_STACK_BASE)),as:UInt32.self) }
        check(oldFS==outer.fsHead,"nested registration links existing native record")
    }
}
do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap())
    host.withSourceGraph { graph in
        let done=DispatchSemaphore(value:0)
        Thread.detachNewThread {
            var c=context(row)
            let result=graph.invokeCompiler(at:.threadFactory,context:&c)
            if result.completed { fatalError("cross-thread context accepted") }
            done.signal()
        }
        done.wait()
        check(host.fault?.code==UInt32(CLAW_FAULT_ABI),"cross-thread graph rejected")
    }
}
do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap()); var c=context(row)
    host.withSourceGraph { graph in
        check(!graph.invokeCompiler(at:.threadFactory,context:&c).completed,"wrong return word rejected")
    }
}
do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap()); var call=ClawCall();call.function=0x503420
    check(!host.invoke(call).completed && host.fault?.diagnostic == .unknownEntry,"nonadmitted singleton rejected")
}
do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap())
    host.withSourceGraph { graph in
        check(!graph.writeStack(at:UInt32(CLAW_STACK_BASE)-1,data:Data([1,2])),"graph stack span cannot straddle")
    }
}
do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap())
    host.withSourceGraph { _ in () }
    check(host.bytes(UInt32(CLAW_STACK_BASE),count:4)==nil,"retired stack token")
}

do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap())
    host.withSourceGraph { _ in () }
    let done=DispatchSemaphore(value:0)
    Thread.detachNewThread {
        if host.withSourceGraph(body:{ _ in true }) != nil { fatalError("source host migrated thread") }
        done.signal()
    }
    done.wait()
    check(host.fault?.code==UInt32(CLAW_FAULT_ABI),"same source host keeps thread identity across graphs")
}

for token in [UInt32(CLAW_STACK_BASE),UInt32(0x61000000)] {
    let heap=ClawTokenHeap();heap.storeBytes(token:0x61000000,count:4)
    let host=ClawNativeCanonicalHost(heap:heap)
    host.withSourceGraph { _ in
        let done=DispatchSemaphore(value:0)
        Thread.detachNewThread {
            if host.bytes(token,count:4) != nil { fatalError("direct byte access escaped source thread") }
            done.signal()
        }
        done.wait()
        check(host.fault?.code==UInt32(CLAW_FAULT_ABI),"direct foreign-thread span rejected")
    }
}

// A source graph never lends raw storage to public host clients, on any thread.
for token in [UInt32(CLAW_STACK_BASE),UInt32(0x61000000)] {
    let heap=ClawTokenHeap();heap.storeBytes(token:0x61000000,count:4)
    let host=ClawNativeCanonicalHost(heap:heap)
    host.withSourceGraph { _ in
        check(host.bytes(token,count:4)==nil,"public bytes refuses active source graph")
        check(host.fault?.code==UInt32(CLAW_FAULT_ABI),"public source span refusal is sticky ABI fault")
    }
}
do {
    let host=ClawNativeCanonicalHost(heap:ClawTokenHeap())
    var oldAlias:UnsafeMutablePointer<UInt8>?
    host.withSourceStackFrame(entryStackPointer:UInt32(CLAW_STACK_TOP),arguments:[],at:0x401000) {
        oldAlias=host.bytes(UInt32(CLAW_STACK_BASE),count:UInt32(CLAW_STACK_END-CLAW_STACK_BASE))
        check(oldAlias != nil,"ordinary compatibility stack alias")
        oldAlias!.update(repeating:0x55,count:Int(CLAW_STACK_END-CLAW_STACK_BASE))
    }
    var retainedSnapshot:Data?
    host.withSourceGraph { graph in
        check(oldAlias!.pointee==0x55,"source graph clearing cannot mutate ordinary backing")
        check(graph.writeStack(at:UInt32(CLAW_STACK_BASE),data:Data(repeating:reference.stack_fill,count:Int(CLAW_STACK_END-CLAW_STACK_BASE))),"isolated source fill")
        var c=context(row)
        for store in row.stores { check(graph.writeStack(at:store[0],data:word(store[1])),"isolated reference stores") }
        oldAlias!.update(repeating:0xcd,count:Int(CLAW_STACK_END-CLAW_STACK_BASE))
        check(graph.invokeCompiler(at:.threadFactory,context:&c).completed,"old ordinary alias cannot corrupt source helper")
        retainedSnapshot=graph.stackSnapshot()!
        check(SHA256.hash(data:retainedSnapshot!).map{String(format:"%02x",$0)}.joined()==row.stack_sha256,"old ordinary alias isolation preserves full original stack")
        check(values(c)==row.final,"old ordinary alias isolation preserves CPU")
    }
    host.withSourceGraph { graph in
        oldAlias!.update(repeating:0xee,count:Int(CLAW_STACK_END-CLAW_STACK_BASE))
        check(graph.stackSnapshot()==Data(repeating:0,count:Int(CLAW_STACK_END-CLAW_STACK_BASE)),"later source graph isolated from retained ordinary aliases")
        check(SHA256.hash(data:retainedSnapshot!).map{String(format:"%02x",$0)}.joined()==row.stack_sha256,"copied snapshot survives private source backing reuse")
    }
    check(host.fault==nil,"isolated source graph teardown clean")
}
// Factory prefix headroom ends at its genuine unsupported allocator call.
// Lesser headroom is rejected before source mutation, not compared to an
// original partially executed fault or described as whole-factory completion.
for site in [ClawNativeCanonicalHost.SourceSite.threadFactory,.moduleFactory] {
    for headroom in [UInt32(site.prefixHeadroom)-4,UInt32(site.prefixHeadroom)] {
        let host=ClawNativeCanonicalHost(heap:ClawTokenHeap())
        var c=ClawSourceContext(size:72,version:1,inputMask:0x7ff,outputMask:0x7ff,
            eax:1,ebx:2,ecx:3,edx:4,esi:5,edi:6,ebp:0xffffffff,esp:UInt32(CLAW_STACK_BASE)+headroom,eip:site.function,
            eflags:2,fsHead:0xffffffff,preserveMask:0x472,reserved0:0,reserved1:0)
        let initialESP=c.esp
        host.withSourceGraph { graph in
            let result=graph.invokeSource(at:site,context:&c)
            check(!result.completed && result.fault?.code==UInt32(CLAW_FAULT_ABI),"factory bounded prefix result")
            if UInt64(headroom)<site.prefixHeadroom {
                check(result.fault?.address==site.function && c.esp==initialESP && c.fsHead==0xffffffff,"insufficient factory prefix headroom rejected before source mutation")
            } else {
                check(result.fault?.address==0x502f84,"minimum factory prefix reaches actual allocator dependency")
            }
        }
    }
}
print("PASS \(checks) native source graph checks; 84 original CPU and full 128KiB stack profiles; factory unsupported dependency prefixes only")
