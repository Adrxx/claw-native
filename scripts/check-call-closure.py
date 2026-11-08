#!/usr/bin/env python3
"""Conservative original call-graph/transport audit (no game code executes).

The default acceptance scope is missing game ownership and real refusals.
Unknown indirect targets, missing call-shape evidence, native services and
profile adapter mappings remain explicit warnings. Detailed original-address
metadata stays under work/. A transport probe extracts the app's *actual*
levelTransport method and compiles its C predicates; it does not substitute a
second Python implementation of that policy. Canonical static entrance guards
are compiled separately with explicit lifetime/memory fixtures. Native dialog
replacement cuts retain the hypothetical callback refusals and current source
witnesses. Accepted transport is distinct from a full native provider/ABI path.
"""
import argparse
import fcntl
from collections import Counter, deque
from contextlib import contextmanager
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.program import profile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_GRP_CALL, CS_GRP_JUMP, CS_GRP_RET
from capstone.x86 import X86_OP_IMM, X86_OP_MEM
from call_closure_shapes import SourceShapes, integer as shape_integer
from call_closure_reviews import OriginalReviews, provider_inline
import call_closure_native
import call_closure_providers
import call_closure_receivers
import call_closure_entry_receivers
import call_closure_profiles

OUT = ROOT/'work/call-closure'


@lru_cache(maxsize=4096)
def _digest(path,mtime,size):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(path):
    stamp=path.stat()
    return _digest(path,stamp.st_mtime_ns,stamp.st_size)


def wait_load():
    while float(subprocess.check_output(['sysctl','-n','vm.loadavg'], text=True).split()[1]) >= 16:
        time.sleep(10)


@contextmanager
def heavy_lock():
    if os.environ.get('CLAW_BUILD_LOCK_HELD'):
        yield
    else:
        with (ROOT/'work/.claw-app-build.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            yield


def body(text, signature):
    start = text.index(signature)
    at = text.index('{', start)
    depth = 1
    end = at+1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def registry():
    text = (ROOT/'Sources/ClawCanonicalDispatch.h').read_text()
    rows = {}
    # Only the primary address inventory; original variants retain these ABIs.
    primary = text.split('clawCanonicalEntries[] = {',1)[1].split('\n};',1)[0]
    for line in primary.splitlines():
        m = re.search(r'\{(0x[0-9a-f]+)u, CLAW_CANONICAL_(\w+), (\d+)u, CLAW_CANONICAL_RETURN_(\w+), (\w+), "([^"]+)"',line)
        if m:
            address, convention, argc, returns, entry, family = m.groups()
            rows[int(address,16)] = dict(convention=convention,argc=int(argc),returns=returns,entry=entry,family=family)
    if not rows:
        raise ValueError('empty generated registry')
    return rows


def manifests():
    result = {}
    for path in sorted((ROOT/'Tests/families').glob('*.json')):
        m = json.loads(path.read_text())
        if m.get('abi') != 'canonical' or m.get('evidence',{}).get('level') != 'admitted':
            continue
        name = m.get('program','claw-v1.0')
        for owned in m.get('owned',[]):
            result[(name,int(owned['address'],16))] = (m,owned)
    return result


def probe_build():
    """Compile the production routing policy with nonexecuting destinations."""
    inputs = [ROOT/p for p in ('Sources/ClawNativeMenuResources.swift','Sources/ClawNativeMenuInterface.cpp',
              'Sources/ClawNativeLevelTransport.cpp','Sources/ClawNativeLevelTransport.h',
              'Sources/ClawNativeMenuResources.cpp','Sources/ClawNativeMenuResources.h',
              'Sources/ClawRuntime.h','Sources/ClawNativeCanonicalHost.swift','Sources/ClawCanonicalDispatch.h')]
    key = hashlib.sha256((''.join(digest(p) for p in inputs)+Path(__file__).read_text()).encode()).hexdigest()[:24]
    folder = ROOT/'work/build/call-closure'/key
    folder.mkdir(parents=True,exist_ok=True)
    binary = folder/'probe'
    if binary.exists():
        return binary
    # Entry pointers are deliberately null: dispatch metadata is real; executing
    # any recovered body would be a bug in this dry-run executable.
    header = inputs[-1].read_text()
    header = re.sub(r', claw_\w+, "', ', nullptr, "', header)
    (folder/'ClawCanonicalDispatch.h').write_text(header)
    owner_text = inputs[1].read_text()
    bridge = '#include "ClawCanonicalDispatch.h"\n#include "ClawNativeLevelTransport.h"\n#include "ClawNativeMenuResources.h"\n#include <cstdlib>\n'
    for name in ('claw_level_owner','claw_level_owner_abi','claw_level_x87_environment'):
        bridge += body(owner_text,'uint32_t '+name+'(')+'\n'
    # Use the same reviewed unused-argument adapter as the app. The original
    # caller shape still goes through levelTransport before this normalization.
    start=owner_text.index('struct ClawCdeclUnreadArguments')
    stop=owner_text.index('uint32_t claw_native_menu_argument_count(',start)
    bridge += 'namespace {\n'+owner_text[start:stop]+body(owner_text,'uint32_t claw_native_menu_argument_count(')+'\n'
    resource_text=(ROOT/'Sources/ClawNativeMenuResources.cpp').read_text()
    resource_body=body(resource_text,'uint32_t claw_native_menu_resource_entry(')
    names=set(re.findall(r'claw_\w+_entry',resource_body)) - {'claw_native_menu_resource_entry'}
    for name in sorted(names):
        effect=('if(f==0x4c96b0u) {if(n) {h->fault=CLAW_FAULT_ABI;return 0;} *out=0;return 1;}'
                if name=='claw_menu_paper_transition_entry' else '')
        bridge += f'extern "C" uint32_t {name}(uint32_t f,uint32_t,const uint32_t*,uint32_t n,ClawHost *h,uint32_t *out) {{{effect} return 0;}}\n'
    bridge += resource_body+'\n'
    bridge += 'extern "C" const ClawCanonicalEntry *claw_closure_lookup(uint32_t f) {return claw_canonical_lookup(f);}\n'
    bridge += '''extern "C" uint32_t claw_closure_resource_probe(uint32_t f,uint32_t n) {
        ClawHost h{};uint32_t words[CLAW_CALL_ARGUMENT_CAPACITY]{},out=0;
        return claw_native_menu_resource_entry(f,0,words,n,&h,&out)==1 && !h.fault;
    }\n'''
    (folder/'owners.cpp').write_text(bridge)
    entry_struct=header[header.index('typedef struct ClawCanonicalEntry {'):header.index('} ClawCanonicalEntry;')+len('} ClawCanonicalEntry;')]
    (folder/'probe.h').write_text('#include "ClawNativeLevelTransport.h"\n#include "ClawNativeMenuResources.h"\n'+entry_struct+
        '\nenum { CLAW_CANONICAL_THISCALL = 2 };\nconst ClawCanonicalEntry *claw_closure_lookup(uint32_t);\nuint32_t claw_closure_resource_probe(uint32_t,uint32_t);\n')
    method = body(inputs[0].read_text(),'    private func levelTransport(').replace('private func levelTransport','func levelTransport')
    physical = body(inputs[0].read_text(),'    private func physicalSource(')
    compiler = body(inputs[0].read_text(),'    private func compilerDiagnostic(')
    canonical = (ROOT/'Sources/ClawNativeCanonicalHost.swift').read_text()
    routing=body(canonical,'if let graph = activeGraph, graph.staticWrapper == 0x4251e0, contextEntries.last == 0x4251f0')
    if 'return callStaticApplicationFrontier(call, graph: graph)' not in routing:
        raise ValueError('Canonical static application routing changed')
    frontier = body(canonical,'    private func callStaticApplicationFrontier(')
    # Compile the actual entrance guards, stopping before observer/provider
    # execution. Graph lifetime, pinned memory and thread binding are fixtures,
    # exactly as destinations/return receipts are fixtures for levelTransport.
    guards = frontier[frontier.index('        guard validateGraph'):frontier.index('        let edge=StaticEdge')]
    guards = guards.replace('native.pointee','staticNative').replace('contextReject(', 'fail(').replace('claw_canonical_lookup(', 'claw_closure_lookup(')
    static_policy = r'''
    struct SourceGraph {
        var staticWrapper:UInt32? = 0x4251e0, staticFrame:UInt32? = 0x200000c
        var staticDriverFrame:UInt32? = nil
        var stringFrontierSpans:[UInt32:(count:UInt32, identity:UInt32)] = [0x537008:(0xc0,1)]
    }
    var staticNative = ClawHost(), contextEntries:[UInt32] = [], frames:[UInt32] = []
    var physicalServiceActive = false, crtObservationActive = false
    func validateGraph(_ g:SourceGraph,at:UInt32)->Bool {true}
    func matchingThreadHead(_ g:SourceGraph,fsHead:UInt32)->Bool {fsHead == UInt32.max}
    func validCPU(esp:UInt32,flags:UInt32,fs:UInt32)->Bool {
        esp >= 0x1ff0000 && esp < 0x2010000 && esp & 3 == 0 && flags == 2 && fs == UInt32.max
    }
    func stackWord(_ at:UInt32)->UInt32? {word(at)}
'''+body(canonical,'    private func staticHeader(')+'''
    func staticFrontier(_ call:ClawCall,graph:SourceGraph)->UInt32? {
'''+guards+'''
        count("canonical-static-application")
        return 0
    }
'''
    swift = r'''
import Foundation
final class Probe {
    var functions:[UInt32] = [], tailOnly:Set<UInt32> = [], tailThunks:[UInt32:UInt32] = [:]
    var originalDirectCalls:[UInt32:Set<UInt32>] = [:]
    var words:[UInt32:UInt32] = [:], fault:UInt32 = 0
    var route = "ordinary", outcome = "transport-only"
    var clobber:UInt32 = 0
    func word(_ p:UInt32)->UInt32? {words[p]}
    func count(_ s:String) {route = s}
    func fail(_ f:UInt32)->UInt32 {fault = f;outcome = "refused";return 0}
    func invoke(_ f:UInt32,_ r:UInt32,_ a:[UInt32],frame:UInt32,
                source:UnsafeMutablePointer<ClawSourceContext>? = nil,returnPC:UInt32 = 0,
                x87:UnsafeMutablePointer<ClawX87State>? = nil)->UInt32 {
        var o = ClawLevelOwner(), convention:UInt32 = 0, argc:UInt32 = 0
        guard claw_level_owner(f,&o) == 1,claw_level_owner_abi(f,&convention,&argc) == 1 else {return fail(f)}
        guard argc == claw_native_menu_argument_count(f,UInt32(a.count)) else {return fail(f)}
        if let source, o.sourceCapability != 0 {
            var adapted = source.pointee
            if claw_level_narrow_source(source,&o,&adapted) == UInt32(CLAW_LEVEL_SOURCE_INCOMPATIBLE) {
                guard claw_level_checked_source_adapt(source,&o,&adapted) == 1 else {return fail(f)}
            }
            adapted.eip = returnPC;adapted.esp = frame+4+(convention == 0 ? 0:argc*4)
            adapted.ebp ^= clobber
            guard claw_level_source_return_ok(source,&adapted) == 1 else {return fail(f)}
        }
        // Receipt fields are synthesized only after the input policy accepted.
        // This proves entrance compatibility, not the callee's execution/return.
        if let source {source.pointee.eip = returnPC;source.pointee.esp = frame+4+(convention == 0 ? 0:argc*4)}
        if let x87 {x87.pointee.returned = 1}
        return 0
    }
    func service(_ q:ClawCall)->UInt32 {outcome = "provider-unresolved";return 0}
'''+method+'\n'+physical+'\n'+compiler+'\n'+static_policy+r'''
    func run(_ row:[String:Any])->[String:Any] {
        func number(_ key:String)->UInt32 {(row[key] as? NSNumber)?.uint32Value ?? 0}
        if number("resource_probe") != 0 {
            return ["accepted":claw_closure_resource_probe(number("target"),number("argc"))]
        }
        var q = ClawCall(), cpu = ClawSourceContext(), cc = ClawCompilerContext(), disposition = ClawSourceDisposition(), fp = ClawX87State(), callback = ClawCallbackCPU()
        clobber = number("clobber_ebp")
        q.function = number("target");q.receiver = number("receiver");q.receiver2 = number("receiver2");q.argumentCount = number("argc")
        q.stackPointer = 0x2000000
        functions = [number("caller")]
        for (key,value) in row["original_direct_calls"] as? [String:[UInt32]] ?? [:] {originalDirectCalls[UInt32(key)!] = Set(value)}
        words = [q.receiver:number("table")]
        for (key,value) in row["words"] as? [String:UInt32] ?? [:] {words[UInt32(key)!] = value}
        tailOnly = Set((row["tail_only"] as? [UInt32]) ?? [])
        for (key,value) in row["tail_thunks"] as? [String:UInt32] ?? [:] {tailThunks[UInt32(key)!] = value}
        cpu.size = UInt32(MemoryLayout<ClawSourceContext>.size);cpu.version = 1
        cpu.inputMask = number("input_mask");cpu.outputMask = number("output_mask");cpu.preserveMask = number("preserve_mask")
        cpu.esp = q.stackPointer;cpu.ecx = q.receiver;cpu.eflags = 2
        if number("static_frontier") != 0 {
            q.sourceReturnPC = number("return_pc");cpu.eip = q.function;cpu.fsHead = UInt32.max
            q.arguments.0 = number("argument0")
            var parent = cpu
            parent.eip = number("site");parent.esp = cpu.esp+4
            staticNative.entryStackPointer = cpu.esp+8;staticNative.sourceReturnPC = 0x4251e5
            contextEntries = [0x4251e0,number("caller")];frames = [cpu.esp+12,cpu.esp+8]
            words[cpu.esp] = q.sourceReturnPC;words[cpu.esp+4] = q.arguments.0
            words[cpu.esp+8] = 0x4251e5;words[cpu.esp+12] = 0x4a5896
            if number("bad_stack") != 0 {words[cpu.esp+8] = 0}
            var graph = SourceGraph()
            if number("bad_wrapper") != 0 {graph.staticWrapper = 0}
            withUnsafeMutablePointer(to:&parent) {p in
                staticNative.sourceContext = p
                withUnsafeMutablePointer(to:&cpu) {c in
                    if number("source") != 0 {q.sourceContext = c}
                    if staticFrontier(q,graph:graph) == nil && fault == 0 {_ = fail(q.function)}
                }
            }
            return ["outcome":outcome,"route":route,"fault":fault,
                    "source_eip":q.sourceReturnPC,"source_esp":q.stackPointer+8]
        }
        if number("source") != 0 {
            q.sourceReturnPC = number("return_pc") == 0 ? 0x70000080:number("return_pc")
            words[q.stackPointer] = q.sourceReturnPC
        }
        fp.size = UInt32(MemoryLayout<ClawX87State>.size);fp.version = 1;fp.control = 0x023f
        fp.count = number("x87_count");fp.popCount = number("x87_pop");fp.pushCount = number("x87_push")
        if number("x87_scalar") != 0 {q.x87ArgumentCount = 1;q.x87Argument = 0}
        cc.size = UInt32(MemoryLayout<ClawCompilerContext>.size);cc.version = UInt32(CLAW_CONTEXT_VERSION)
        cc.inputMask = number("input_mask");cc.outputMask = number("output_mask")
        cc.eip = q.function;cc.esp = q.stackPointer;cc.ebp = number("compiler_ebp");cc.fsHead = UInt32.max
        cc.continuation = number("compiler_return_pc")
        if number("compiler") != 0 {
            words[cc.esp] = cc.continuation
            if number("compiler_unreadable") == 0 {words[cc.ebp &+ 4] = 0x70000090}
            q.stackPointer = 0
        }
        withUnsafeMutablePointer(to:&cc) {context in
        withUnsafeMutablePointer(to:&callback) {activation in
        if number("callback") != 0 {
            activation.pointee.size = UInt32(MemoryLayout<ClawCallbackCPU>.size);activation.pointee.version = 1
            activation.pointee.activation = 1;activation.pointee.target = number("caller")
            activation.pointee.entryStackPointer = q.stackPointer+0x100
            activation.pointee.cpu = cpu
            q.callbackCPU = activation;q.callbackActivation = 1
        }
        if number("compiler") != 0 {q.compilerContext = context}
        withUnsafeMutablePointer(to:&cpu) {ptr in
            if number("source") != 0 {q.sourceContext = ptr}
            withUnsafeMutablePointer(to:&fp) {state in
            if number("x87") != 0 {q.x87ArgumentCount = UInt32(CLAW_X87_EXACT);q.x87State = state}
            withUnsafeMutablePointer(to:&disposition) {receipt in
                if number("tail") != 0 {
                    q.sourceTransferVersion = 1;q.sourceTransferKind = UInt32(CLAW_SOURCE_TAIL_JMP)
                    q.sourceCallerFunction = number("caller");q.sourceTransferSite = number("site");q.sourceDisposition = receipt
                }
                let copy = q
                withUnsafePointer(to:copy) {request in
                    if levelTransport(q,request:request) == nil {
                        if claw_level_is_game(q.function) != 0 {
                            _ = invoke(q.function,q.receiver,Array(repeating:0,count:Int(q.argumentCount)),frame:q.stackPointer)
                        } else {outcome = "provider-unresolved"}
                    }
                }
            }
        }
        }
        }
        }
        return ["outcome":outcome,"route":route,"fault":fault,
                "source_eip":cpu.eip,"source_esp":cpu.esp,"disposition":disposition.disposition,
                "x87_returned":fp.returned,"compiler_eip":cc.eip,"compiler_esp":cc.esp,"compiler_eax":cc.eax]
    }
}
let input = FileHandle.standardInput.readDataToEndOfFile()
let rows = try JSONSerialization.jsonObject(with:input) as! [[String:Any]]
let answers = rows.map { Probe().run($0) }
FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject:answers,options:[.sortedKeys]))
'''
    (folder/'main.swift').write_text(swift)
    with heavy_lock():
        if binary.exists():return binary
        wait_load()
        for source in (folder/'owners.cpp',ROOT/'Sources/ClawNativeLevelTransport.cpp'):
            subprocess.run(['xcrun','clang++','-std=c++17','-O1','-I'+str(folder),'-I'+str(ROOT/'Sources'),'-c',str(source),'-o',str(folder/(source.stem+'.o'))],check=True)
        subprocess.run(['xcrun','swiftc','-O','-I'+str(ROOT/'Sources'),'-import-objc-header',str(folder/'probe.h'),
                        str(folder/'main.swift'),str(folder/'owners.o'),str(folder/'ClawNativeLevelTransport.o'),
                        '-Xlinker','-lc++','-o',str(binary)],check=True)
    return binary


class Graph:
    def __init__(self, program, roots):
        self.program = program
        self.roots = set(roots)
        self.decoder = Cs(CS_ARCH_X86,CS_MODE_32)
        self.decoder.detail = True
        self.edges, self.unresolved, self.tables = [], [], {}
        self.visited = set()

    def bytes(self,address,size):
        for section in self.program.sections:
            if section.address <= address < section.address+len(section.data):
                return section.data[address-section.address:address-section.address+size]
        return b''

    def word(self,address):
        raw = self.bytes(address,4)
        return int.from_bytes(raw,'little') if len(raw)==4 else None

    def census_tables(self):
        # An overapproximation, not a claim that each data array is registered.
        # Every contiguous code-pointer run is retained; nonconstant indirect
        # calls are still unresolved until receiver provenance is established.
        for section in self.program.sections:
            if section.name != '.rdata':
                continue
            run = []
            for offset in range(0,len(section.data)-3,4):
                at = section.address+offset
                target = self.word(at)
                if self.program.in_text(target):
                    run.append((at,target))
                else:
                    if len(run)>=2:
                        self.tables[run[0][0]] = [target for _,target in run]
                    run=[]
            if len(run)>=2:
                self.tables[run[0][0]] = [target for _,target in run]

    def scan(self):
        pending = deque(sorted(self.roots))
        while pending:
            root = pending.popleft()
            if root in self.visited or not self.program.in_text(root):
                continue
            self.visited.add(root)
            # Native platform replacements terminate the original graph here.
            if self.program.name == 'claw-v1.0' and not game(root):
                continue
            blocks, seen = [root],set()
            while blocks:
                pc=blocks.pop()
                while pc not in seen:
                    if not self.program.in_text(pc):
                        self.unresolved.append(dict(caller=root,site=pc,reason='branch-outside-code'));break
                    seen.add(pc)
                    ins=next(self.decoder.disasm(self.bytes(pc,15),pc,count=1),None)
                    if ins is None:
                        self.unresolved.append(dict(caller=root,site=pc,reason='undecodable'));break
                    after=pc+ins.size
                    if ins.group(CS_GRP_RET) or ins.mnemonic in ('int3','hlt','ud2'):
                        break
                    call,jump=ins.group(CS_GRP_CALL),ins.group(CS_GRP_JUMP)
                    if call or jump:
                        operand=ins.operands[0] if ins.operands else None
                        target=None;kind='call' if call else 'tail'
                        if operand and operand.type == X86_OP_IMM:
                            target=operand.imm & 0xffffffff
                            if jump and (ins.mnemonic!='jmp' or target not in self.roots):
                                blocks.append(target)
                                if ins.mnemonic=='jmp':break
                                pc=after;continue
                        elif operand and operand.type == X86_OP_MEM and not operand.mem.base and not operand.mem.index:
                            slot=operand.mem.disp & 0xffffffff
                            target=slot if slot in self.program.imports else self.word(slot)
                        if target is None:
                            self.unresolved.append(dict(caller=root,site=pc,reason='indirect-target',kind=kind))
                        else:
                            self.edges.append(dict(caller=root,site=pc,target=target,kind=kind,immediate=operand.type == X86_OP_IMM))
                            if self.program.in_text(target):
                                self.roots.add(target);pending.append(target)
                        if ins.mnemonic=='jmp':break
                    pc=after
        return self


def game(address):
    return 0x401000<=address<0x4a1300 or 0x4b3400<=address<0x4f0000 or 0x4f4490<=address<0x4f4aa0


def inline_shape(original, manifest):
    # Reviewed local metadata is intentionally kept out of the source tree.
    # A review goes stale on any original or translated-source change.
    path=OUT/'inline-shapes.json'
    if not path.exists():return None
    for row in json.loads(path.read_text()):
        if row['original_site']!=original or row['family']!=manifest['id']:continue
        source=ROOT/row['source']
        if row['source'] not in manifest['sources'] or digest(source)!=row['source_sha256']:continue
        actual=row.get('actual_source')
        if actual:
            if actual['path']!=row['source'] or actual['line']!=row['source_lines'][0]:continue
            symbol=actual.get('operation') if actual['api']=='memory' else actual.get('callee')
            lines=source.read_text().splitlines()
            if not symbol or not 1<=actual['line']<=len(lines) or symbol+'(' not in lines[actual['line']-1]:continue
        p=profile(original['profile']);g=Graph(p,set())
        if hashlib.sha256(g.bytes(row['callee_start'],row['callee_size'])).hexdigest()!=row['callee_sha256']:continue
        return dict(inlined=True,emitted_host_calls=0),row
    return None


def dialog_replacement(native_sources=None):
    """A native-context cut, never an original-impossibility exemption.

    The original may enter this procedure through DialogBoxParamA. The native
    app intercepts EDITPLAYERS before the application dispatcher, and has no
    native DialogBoxParamA provider or callback registration for this address.
    Keep testing hypothetical callback requests: they must still be refused.
    """
    paths = [*sorted((ROOT/'Sources').glob('*.swift')), *sorted((ROOT/'App').rglob('*.swift')),
             *sorted((ROOT/'Sources').glob('ClawNative*.cpp'))]
    sources = native_sources if native_sources is not None else {str(p.relative_to(ROOT)):p.read_text() for p in paths}
    for path,text in sources.items():
        # Transport metadata declares the import's shape, not a provider.
        if path == 'Sources/ClawNativeLevelTransport.cpp':continue
        if re.search(r'\b(?:0x0*49b730|0x0*546d2c|DialogBoxParam\w*)\b',text,re.I):
            raise ValueError(f'Native dialog callback/provider reference requires review: {path}')
    menu=sources['Sources/ClawNativeMenuInterface.swift']
    command=body(menu,'if command.wParam == 0x8090,command.lParam == 4,let showPlayers')
    compact=lambda s:re.sub(r'\s+','',re.sub(r'//[^\n]*','',s))
    expected='''if command.wParam == 0x8090,command.lParam == 4,let showPlayers {
        input.releaseMenuKeys()
        while try input.queue.next(window:input.window) != nil {}
        playersActive = true;showPlayers();return
    }'''
    if compact(command)!=compact(expected):raise ValueError('Native player command interception changed')
    if menu.index(command)>menu.index('_ = resources.invoke(0x426e30,base.applicationToken,[0,command.wParam,command.lParam])'):
        raise ValueError('Player command reaches original dispatcher before native sheet')
    required={
        'Sources/ClawNativeMenuInterface.swift':[
            'command.lParam == 4 && showPlayers == nil',
            '![UInt32(0),2,4].contains(command.lParam)) {continue}',
            'if showPlayers == nil {unavailable += [13001]}',
            '_ = resources.invoke(0x42bf90,base.applicationToken,[record])'],
        'App/ClawApp.swift':['self?.players = PlayersState(choices:menu.playerChoices,selected:menu.selectedPlayer)',
                            'case "select":try owner.selectPlayer(draft.selected)',
                            'owner.finishPlayerDialog(cancelled:action == "close")']}
    for path,fragments in required.items():
        if any(fragment not in sources[path] for fragment in fragments):
            raise ValueError(f'Native player sheet boundary changed: {path}')
    return dict(kind='native-replaced-callback-activation',original_impossible=False,
                original_callback=0x49b730,original_dialog_import=0x546d2c,
                source_inputs={p:hashlib.sha256(t.encode()).hexdigest() for p,t in sources.items()},
                contract='Native EDITPLAYERS returns through the Swift sheet before original dispatch; unavailable services are disabled. No native callback registration or DialogBoxParamA provider references the original procedure. Original and hypothetical non-callback provider obligations remain open.')


def static_frontier_fixture(shape):
    """Bind emitted operands from the admitted thunk, rather than a fake receiver."""
    source=(ROOT/'Sources/StaticConstructorThunksRuntime.cpp').read_text()
    thunk=body(source,'uint32_t function_4251f0(')
    receivers=re.findall(r'context\.ecx = (0x[0-9a-f]+);',thunk)
    if len(receivers)!=1 or shape.get('receiver_expression')!='context.ecx':
        raise ValueError('Static application thunk receiver needs review')
    arguments=shape.get('argument_expressions',[])
    if len(arguments)!=1 or shape_integer(arguments[0]) is None:
        raise ValueError('Static application thunk operands need review')
    return dict(static_frontier=1,receiver=int(receivers[0],16),argument0=shape_integer(arguments[0]))


def unowned_routes(binary, rows):
    return call_closure_native.audit(ROOT,rows,binary,body,digest,heavy_lock,wait_load)


def closure_acceptance(rows, unresolved):
    """Keep unproved classes visible without expanding missing-game scope."""
    failures = [r for r in rows if r['outcome'] in ('owner-unresolved','transport-refused')]
    warnings = Counter(r['outcome'] for r in rows
        if not r['outcome'].startswith('served-') and
        r['outcome'] not in ('owner-unresolved','transport-refused','unreachable-single-player'))
    if unresolved:warnings['indirect-target-unresolved'] = len(unresolved)
    return dict(scope='Missing game ownership and real transport refusals only',
        complete=not failures, failure_counts=dict(Counter(r['outcome'] for r in failures)),
        warnings=dict(warnings))


def audit(name, inventory, owners, binary):
    program=profile(name)
    roots={address for (p,address) in owners if p==name and (name!='claw-v1.0' or address in inventory and game(address))}
    graph=Graph(program,roots)
    graph.census_tables()
    # Include every candidate virtual target, even when no direct caller reaches
    # it. Receiver provenance remains a separate unresolved obligation.
    graph.roots.update(target for words in graph.tables.values() for target in words if name!='claw-v1.0' or game(target))
    graph.scan()
    if name=='claw-v1.3':
        rows,adapter_proof=call_closure_profiles.audit(
            ROOT,graph,inventory,owners,binary,digest,heavy_lock,wait_load)
        counts=Counter(row['outcome'] for row in rows)
        counts.setdefault('transport-refused',0)
        return dict(profile=name,sha256=program.sha256,roots=len(roots),functions=len(graph.visited),
            candidate_tables=len(graph.tables),edges=rows,unresolved=graph.unresolved,
            profile_adapter_proof=adapter_proof,counts=dict(counts),
            complete=not graph.unresolved and all(r['outcome'].startswith('served-') for r in rows),
            limitations=[adapter_proof['contract'],adapter_proof['prerequisite']])
    native_dialog=dialog_replacement() if name=='claw-v1.0' else None
    if native_dialog and any(e['target']==native_dialog['original_callback'] for e in graph.edges):
        raise ValueError('Original dialog procedure acquired a direct caller; native cut needs review')
    reviews=None
    if name=='claw-v1.0':
        with heavy_lock():
            wait_load()
            reviews=OriginalReviews(graph,OUT/'ordinary-reviews.json')
    election=json.loads((ROOT/'App/GameData/MENU/level-one-transports.json').read_text())
    receiver_proof=call_closure_receivers.audit(ROOT,graph,inventory,owners,binary,election,digest) if name=='claw-v1.0' else None
    if receiver_proof:
        (OUT/'receivers.json').write_text(json.dumps(receiver_proof,indent=2)+'\n')
    tail_only=[int(x,16) for x in election['tail_only']]
    thunks={str(int(k,16)):int(v,16) for k,v in election['tail_thunks'].items()}
    provider_review_path=OUT/'provider-inline-shapes.json'
    provider_reviews=json.loads(provider_review_path.read_text()) if provider_review_path.exists() else []
    requests=[]; rows=[]; shape_readers={};selected=[];ordinary=[];providers=[]
    for edge in graph.edges:
        row=dict(edge)
        caller,target=edge['caller'],edge['target']
        declared=owners.get((name,caller))
        target_owner=inventory.get(target) if name=='claw-v1.0' else None
        if name!='claw-v1.0':
            row['outcome']='profile-adapter-unresolved';rows.append(row);continue
        required=declared and target_owner and (edge['kind']=='tail' or target_owner['returns']=='X87' or
                   'source_context' in declared[1] or 'compiler_context' in declared[1])
        preliminary=None
        if declared and target_owner and declared[1].get('x87_environment'):
            family=declared[0]['id']
            if family not in shape_readers:shape_readers[family]=SourceShapes(ROOT,declared[0],import_slots=program.imports)
            ins=next(graph.decoder.disasm(graph.bytes(edge['site'],15),edge['site'],count=1))
            preliminary=shape_readers[family].edge(edge,declared[1],ins.size)
            exact_calls=shape_readers[family].entry_calls(caller,bool(declared[1].get('source_context')))
            if any(l['api']=='call_x87_exact' and l['args'] and shape_integer(l['args'][0])==target for l in exact_calls):required=True
        if declared and (target_owner or not game(target)):
            family=declared[0]['id']
            if family not in shape_readers:shape_readers[family]=SourceShapes(ROOT,declared[0],import_slots=program.imports)
            ins=next(graph.decoder.disasm(graph.bytes(edge['site'],15),edge['site'],count=1))
            proof=preliminary or shape_readers[family].edge(edge,declared[1],ins.size)
            original=dict(profile=program.name,sha256=program.sha256,caller=caller,site=edge['site'],
                          target=target,size=ins.size,bytes_sha256=hashlib.sha256(ins.bytes).hexdigest(),kind=edge['kind'])
            row['original_site']=original
            (providers if not target_owner else selected if required else ordinary).append(row)
            proof=reviews.edge(original) or proof
            if proof is None:
                proof=inline_shape(original,declared[0])
            if proof is None and not target_owner:
                proof=provider_inline(graph,original,declared[0],shape_readers[family],provider_reviews)
            if proof is None:
                row['shape_status']='unresolved'
                row['outcome']='provider-shape-unresolved' if not target_owner else 'x87-shape-unresolved' if target_owner['returns']=='X87' else 'call-shape-unresolved'
                rows.append(row);continue
            shape,evidence=proof
            row['caller_shape']=shape;row['shape_evidence']=evidence;row['shape_status']='proved'
            if 'path' in evidence:evidence['source_sha256']=digest(ROOT/evidence['path'])
            evidence['runtime_sha256']=digest(ROOT/'Sources/ClawRuntime.hpp')
            evidence['manifest_sha256']=digest(ROOT/'Tests/families'/f'{family}.json')
            def source_inputs(value):
                paths=set()
                if isinstance(value,dict):
                    if 'path' in value:paths.add(value['path'])
                    for child in value.values():paths.update(source_inputs(child))
                elif isinstance(value,list):
                    for child in value:paths.update(source_inputs(child))
                return paths
            evidence['source_inputs']={p:digest(ROOT/p) for p in source_inputs(evidence)}
            row['callee_contract']=dict(target_owner or {},declared=owners.get((name,target),(None,None))[1])
            if shape.get('direct_entry') and not target_owner:
                row['outcome']='provider-entry-unresolved';row['shape_status']='unresolved'
                rows.append(row);continue
            if shape.get('direct_entry') and (shape['direct_entry']!=target_owner['entry'] or shape['argc']!=target_owner['argc']):
                raise ValueError(f'Local canonical ABI mismatch at {edge}')
            if shape.get('local') or shape.get('inlined') or shape.get('impossible'):
                row['outcome']='served-reviewed-impossible' if shape.get('impossible') else 'served-inline' if shape.get('inlined') else 'served-local'
                rows.append(row);continue
            candidates=[(table,words) for table,words in graph.tables.items() if caller in words]
            if receiver_proof:
                candidates=call_closure_receivers.receiver_tables(receiver_proof,graph,caller)
            if target in tail_only and not candidates:
                row['outcome']='receiver-provenance-unresolved';rows.append(row);continue
            indexes=[]
            # Every legal live depth for this emitted pop/push shape. Caller
            # Run validation supplies the domain; the target ABI supplies none.
            for shape in shape.get('variants',[shape]):
                depths=range(shape.get('x87_pop',0),9-shape.get('x87_push',0)) if shape.get('x87') else [0]
                for table,words in candidates if target in tail_only else [(0,[])]:
                    for count in depths:
                        query=dict(shape,caller=caller,target=target,site=edge['site'],table=table,x87_count=count,
                                   words=(call_closure_receivers.receiver_words(graph,table) if receiver_proof else {str(table+4*i):word for i,word in enumerate(words)}),tail_only=tail_only,tail_thunks=thunks,
                                   original_direct_calls={str(int(k,16)):[int(v,16) for v in values] for k,values in election.get('original_direct_calls',{}).items()})
                        if caller==0x4251f0:
                            query.update(static_frontier_fixture(shape))
                            row['provider_preconditions']='Canonical static entrance guards are compiled from production. Graph lifetime, pinned application/name storage and thread binding are explicit fixtures; provider execution and return are not proved.'
                        if shape.get('compiler'):
                            value=shape_integer(shape['compiler_ebp_expression'])
                            query['compiler_ebp']=value if value is not None else 0x2000100
                            row['provider_preconditions']='Diagnostic memory reads use an explicit dry-run fixture. Real caller-frame readability, including a possible null-page fault, remains unproved; no edge is exempted by this fixture.'
                        requests.append(query);indexes.append(len(requests)-1)
            row['shape_probe_indexes']=indexes;rows.append(row);continue
        if not target_owner:
            # owner-unresolved is the owner-crash class: an admitted caller's
            # host call into an original game body no family owns. An edge out
            # of an unowned caller is only taken once that caller is entered,
            # which is itself one of these obligations or a receiver/indirect one.
            row['outcome']=('owner-unresolved' if declared else 'caller-owner-unresolved') if game(target) else 'provider-unresolved'
            if declared and game(target):
                ins=next(graph.decoder.disasm(graph.bytes(edge['site'],15),edge['site'],count=1))
                row['original_site']=dict(profile=program.name,sha256=program.sha256,caller=caller,site=edge['site'],
                    target=target,size=ins.size,bytes_sha256=hashlib.sha256(ins.bytes).hexdigest(),kind=edge['kind'],
                    family=declared[0]['id'])
                family=declared[0]['id']
                if family not in shape_readers:
                    shape_readers[family]=SourceShapes(ROOT,declared[0],import_slots=program.imports)
                proof=shape_readers[family].edge(edge,declared[1],ins.size)
                if proof:
                    row['caller_shape'],row['shape_evidence']=proof
                    row['shape_status']='proved'
            rows.append(row);continue
        if edge['kind']=='tail' or (declared and ('source_context' in declared[1] or 'compiler_context' in declared[1])):
            row['outcome']='caller-owner-unresolved' if not declared else 'call-shape-unresolved';rows.append(row);continue
        # No admitted caller means there is no emitted shape to inspect. Never
        # manufacture one from the callee's declaration.
        row['outcome']='caller-owner-unresolved';rows.append(row)
    answers=[]
    if requests:
        process=subprocess.run([str(binary)],input=json.dumps(requests),text=True,capture_output=True,
                               env={**os.environ,'CLAW_GAME_VERSION':'1.0'},check=True)
        answers=json.loads(process.stdout)
    for row in rows:
        if 'shape_probe_indexes' in row:
            probes=[dict(request=requests[i],answer=answers[i]) for i in row.pop('shape_probe_indexes')]
            if native_dialog and row['caller']==native_dialog['original_callback']:
                excluded=[p for p in probes if p['request'].get('callback')]
                if excluded:
                    row['native_context_proof']=native_dialog
                    row['excluded_native_activation_probes']=excluded
                    probes=[p for p in probes if not p['request'].get('callback')]
            row['shape_probes']=probes
            failures=[p for p in probes if p['answer']['outcome']=='refused']
            provider=not game(row['target'])
            for p in probes:
                q,a=p['request'],p['answer']
                if a['outcome']=='refused':continue
                if provider and a['route']!='source-physical':continue
                # The destination is nonexecuting; these receipts check that
                # routing publishes the continuation the emitted API expects.
                if q.get('source'):
                    pc=q.get('return_pc',0x70000080)
                    pop=q.get('return_pop',0)
                    if a['source_eip']!=pc or a['source_esp']!=0x2000000+4+pop:failures.append(p)
                    if q.get('tail') and a['disposition']!=1:failures.append(p)
                if q.get('x87') and a['x87_returned']!=1:failures.append(p)
                if q.get('compiler'):
                    expected=q['compiler_return_pc'] if row['target']==0x4db5f0 else 0x70000090
                    if a['compiler_eip']!=q['compiler_return_pc'] or a['compiler_esp']!=0x2000004 or a['compiler_eax']!=expected:failures.append(p)
            row['outcome']='transport-refused' if failures else 'provider-unresolved' if provider else 'transport-only'
            if failures:row['shape_status']='refused'
            if not probes:row['shape_status']='unresolved'
        if 'probe_index' in row:
            row.update(answers[row.pop('probe_index')])
    unresolved=graph.unresolved
    if receiver_proof:
        rows.extend(receiver_proof['slots'])
        unresolved=[r for r in receiver_proof['indirect_sites'] if r['status']!='target-set-proved']
        for indirect in receiver_proof['indirect_sites']:
            if indirect['status']!='target-set-proved':continue
            targets=indirect.get('targets',[indirect.get('target')])
            for target in targets:
                # Closing the target set does not establish an emitted caller
                # shape, provider execution or even callee ownership.
                rows.append(dict(caller=indirect['caller'],site=indirect['site'],target=target,
                    kind=indirect['kind'],indirect_kind=indirect['indirect_kind'],
                    outcome='indirect-call-shape-unresolved',target_proof=indirect))
    else:
        for table,words in graph.tables.items():
            for slot,target in enumerate(words):
                if name!='claw-v1.0' or game(target):
                    rows.append(dict(caller=0,site=table+slot*4,target=target,kind='vtable-candidate',table=table,outcome='receiver-provenance-unresolved'))
    unowned_proof=unowned_routes(binary,rows) if name=='claw-v1.0' else None
    counts=Counter(row['outcome'] for row in rows)
    counts.setdefault('transport-refused',0)
    shape_summary=dict(selection='All original direct edges with admitted app caller and target owners involving a source/compiler caller, an original tail, an x87-result target, or an emitted exact x87 call from an admitted x87-environment caller.',
        selected_callers=sorted({r['caller'] for r in selected}),selected_edges=len(selected),
        probe_contract='Compiled level routing, canonical static entrance guards and C predicates with nonexecuting destinations; lifetime/memory are fixtures and return receipts are synthesized, not game-execution evidence.',
        statuses=dict(Counter(r['shape_status'] for r in selected)),
        unresolved=[dict(caller=r['caller'],site=r['site'],target=r['target'],status=r['shape_status']) for r in selected if r['shape_status']!='proved'])
    shape_summary['complete']=not shape_summary['unresolved']
    ordinary_summary=dict(selected_edges=len(ordinary),statuses=dict(Counter(r['shape_status'] for r in ordinary)),
        unresolved=[dict(caller=r['caller'],site=r['site'],target=r['target'],status=r['shape_status'])
                    for r in ordinary if r['shape_status']!='proved'])
    ordinary_summary['complete']=not ordinary_summary['unresolved']
    provider_summary=dict(selected_edges=len(providers),statuses=dict(Counter(r['shape_status'] for r in providers)),
        extracted_edges=sum(bool(r.get('caller_shape')) for r in providers),
        unresolved=[dict(caller=r['caller'],site=r['site'],target=r['target'],status=r['shape_status'])
                    for r in providers if r['shape_status']!='proved'],
        contract='Actual emitted native-provider call shapes and production transport gates only; provider destination, memory and value preconditions remain open.')
    provider_summary['complete']=not provider_summary['unresolved']
    # Plain dry-runs do not infer operand counts from the callee's signature or
    # prove all dynamic receiver classes. Transport-only is intentionally open.
    return dict(profile=name,sha256=program.sha256,roots=len(roots),functions=len(graph.visited),
                candidate_tables=len(graph.tables),source_context_proof=shape_summary,ordinary_call_proof=ordinary_summary,
                provider_call_proof=provider_summary,edges=rows,unresolved=unresolved,
                receiver_proof=({k:v for k,v in receiver_proof.items() if k not in ('slots','tables','indirect_sites','registered_classes')} if receiver_proof else None),
                indirect_sites=receiver_proof['indirect_sites'] if receiver_proof else [],
                unowned_call_proof=unowned_proof,
                unowned_target_edges=[r['original_site'] for r in rows if r['outcome']=='owner-unresolved'],
                counts=dict(counts),complete=closure_acceptance(rows,unresolved)['complete'],
                acceptance=closure_acceptance(rows,unresolved),
                full_closure_complete=not unresolved and all(row["outcome"].startswith("served-") for row in rows),
                limitations=['Source/tail/x87 and ordinary caller shapes have bounded proofs; dynamic receiver provenance and native-provider memory preconditions remain open.',
                             'Native provider preconditions and v1.3 adapter mappings need dry-run coverage.',
                             'Indirect edges, jump tables and registered class closure must be resolved.'])


def transport_tests(binary, report=None):
    """Regression for a real inherited-base edge, plus malformed-call refusal."""
    program=profile('claw-v1.0')
    election=json.loads((ROOT/'App/GameData/MENU/level-one-transports.json').read_text())
    inventory=registry()
    graph=Graph(program,set(inventory)).scan()
    caller,target,table=0x40ab20,0x440420,0x50b38c
    sites=[edge['site'] for edge in graph.edges if edge['caller']==caller and edge['target']==target and edge.get('immediate')]
    if sites != [0x40ab58,0x40ab76]:
        raise ValueError(f'Original BearSailor CALL evidence changed: {sites}')
    words={str(table+4*i):graph.word(table+4*i) for i in range(43)}
    if target in words.values():raise ValueError('Expected overridden base absent from receiver table')
    query=dict(caller=caller,target=target,site=sites[0],argc=0,receiver=0x61000000,table=table,words=words,
               tail_only=[int(x,16) for x in election['tail_only']],
               tail_thunks={str(int(k,16)):int(v,16) for k,v in election['tail_thunks'].items()},
               original_direct_calls={str(int(k,16)):[int(v,16) for v in values] for k,values in election.get('original_direct_calls',{}).items()})
    requests=[query,dict(query,original_direct_calls={}),dict(query,argc=1),dict(query,receiver=0),dict(query,caller=0),
              dict(query,source=1,input_mask=0x7ff,output_mask=0x7ff,preserve_mask=0x472),
              dict(query,source=1,input_mask=0x7ff,output_mask=0x7ff,preserve_mask=1)]
    process=subprocess.run([str(binary)],input=json.dumps(requests),text=True,capture_output=True,
                           env={**os.environ,'CLAW_GAME_VERSION':'1.0'},check=True)
    answers=json.loads(process.stdout)
    if answers[0]['outcome']!='transport-only' or answers[0]['route']!='original-base-direct':
        raise ValueError(f'Authenticated base CALL refused: {answers[0]}')
    if answers[5]['outcome']!='transport-only' or answers[5]['route']!='source-ordinary':
        raise ValueError(f'Ordinary source continuation refused: {answers[5]}')
    if any(answers[i]['outcome']!='refused' for i in (1,2,3,4,6)):
        raise ValueError(f'Malformed or unauthenticated base CALL accepted: {answers[1:]}')
    # Original bird-state calls push otherwise unused words into a shared bare
    # RET. Check the byte witness and each caller's actual emitted operands;
    # this is an adapter regression, not an impossible-edge exemption.
    noop=0x4c96b0
    if graph.bytes(noop,1)!=b'\xc3':raise ValueError('Unused-argument no-op is no longer a bare RET')
    resource_queries=[dict(resource_probe=1,target=noop,argc=n) for n in (0,3)]
    resource_queries.append(dict(resource_probe=1,target=0xdeadbeef,argc=3))
    resource_answers=json.loads(subprocess.run([str(binary)],input=json.dumps(resource_queries),
        text=True,capture_output=True,check=True).stdout)
    if [a['accepted'] for a in resource_answers]!=[1,1,0]:
        raise ValueError(f'Resource-first unused-argument adapter failed: {resource_answers}')
    owned_manifests=manifests()
    manifest,owned=owned_manifests[('claw-v1.0',0x403540)]
    reader=SourceShapes(ROOT,manifest)
    edge=next(e for e in graph.edges if e['caller']==0x403540 and e['kind']=='call')
    extracted=reader.edge(edge,owned,5)
    if not extracted or not extracted[0].get('source'):raise ValueError('Lost actual source-call extraction')
    leaf=next(l for l in reader.entry_calls(edge['caller'],True) if l['api']=='source_call')
    unbound=dict(leaf,args=leaf['args'][:4]+['unknown_operands'])
    if reader.shape(unbound,owned) is not None:raise ValueError('Inferred unknown caller operands')
    report=report or audit('claw-v1.0',inventory,owned_manifests,binary)
    noop_edges=[e for e in report['edges'] if e['target']==noop and e.get('caller_shape',{}).get('argc')==3]
    if not noop_edges or any(e['outcome']!='transport-only' for e in noop_edges):
        raise ValueError(f'Original bird-state unused-argument calls refused: {[(e["caller"],e["outcome"]) for e in noop_edges]}')
    summary=report['source_context_proof']
    if not summary['complete']:raise ValueError(f"Source/tail/x87 obligations remain: {summary['unresolved']}")
    original_probes=[p for e in report['edges'] for p in e.get('shape_probes',[]) if game(e['target'])]
    by_route={p['answer']['route']:p['request'] for p in original_probes}
    required_routes={'source-call','source-tail','x87-balanced','x87-owned','x87-discarded','original-base-direct'}
    if not required_routes.issubset(by_route):raise ValueError(f'Missing production routes: {required_routes-set(by_route)}')
    source=next(p['request'] for e in report['edges'] if e['target']==0x4db5f0
                for p in e.get('shape_probes',[]) if p['request'].get('source'))
    negative=[dict(source,clobber_ebp=1),dict(source,input_mask=0),
              dict(source,preserve_mask=0,output_mask=0x7bf,clobber_ebp=1),
              dict(by_route['source-tail'],source=0),
              dict(by_route['x87-owned'],x87_count=8),dict(by_route['x87-owned'],x87_push=2),
              dict(by_route['x87-balanced'],x87_count=9),dict(by_route['x87-balanced'],x87_pop=1),
              dict(by_route['original-base-direct'],receiver2=1),
              dict(by_route['original-base-direct'],x87_scalar=1),
              dict(by_route['original-base-direct'],original_direct_calls={})]
    refused=json.loads(subprocess.run([str(binary)],input=json.dumps(negative),text=True,capture_output=True,
                      env={**os.environ,'CLAW_GAME_VERSION':'1.0'},check=True).stdout)
    if any(a['outcome']!='refused' for a in refused):raise ValueError(f'Malformed source/tail/x87 request accepted: {refused}')
    # Native destinations remain unresolved, but rejection by the production
    # source gate is already a definite refusal. Do not hide it as unresolved.
    native=dict(source,caller=0x497960,target=0x4a3050,argc=0,receiver=0,return_pop=0)
    native_requests=[native,dict(native,argc=1),dict(native,target=0x4f6428,argc=1)]
    native_answers=json.loads(subprocess.run([str(binary)],input=json.dumps(native_requests),text=True,capture_output=True,
                              env={**os.environ,'CLAW_GAME_VERSION':'1.0'},check=True).stdout)
    if native_answers[0]['outcome']!='provider-unresolved' or any(a['outcome']!='refused' for a in native_answers[1:]):
        raise ValueError(f'Native-provider source transport classification changed: {native_answers}')
    if native_answers[0]['source_eip']!=native['return_pc'] or native_answers[0]['source_esp']!=0x2000004:
        raise ValueError('Native-provider source continuation changed')
    # Keep every original-site/translation/probe record in the v1.0 report.
    (OUT/'source-context.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(status='pass',original_call_sites=[hex(site) for site in sites],probes=answers,
                source_context_proof=summary,original_shape_probes=len(original_probes),
                unused_argument_edges=[dict(caller=e['caller'],site=e['site'],target=e['target'],shape=e['caller_shape']) for e in noop_edges],
                resource_adapter_probes=resource_answers,
                native_source_probes=[dict(request=q,answer=a) for q,a in zip(native_requests,native_answers)],
                production_routes=sorted(by_route),malformed_shape_probes=refused)


def ordinary_tests(binary):
    cohort=json.loads((OUT/'ordinary-remaining.json').read_text())
    report=audit('claw-v1.0',registry(),manifests(),binary)
    keys=lambda e:(e['caller'],e['site'],e['target'],e['kind'])
    wanted={keys(e):e for e in cohort['edges']}
    if len(wanted)!=370 or cohort['original_sha256']!=report['sha256']:
        raise ValueError('The selected ordinary cohort must remain exactly 370 original sites')
    selected=[e for e in report['edges'] if keys(e) in wanted]
    if len(selected)!=370:raise ValueError('Lost an original ordinary cohort edge')
    if not report['ordinary_call_proof']['complete']:
        raise ValueError(f"Ordinary shapes regressed outside the cohort: {report['ordinary_call_proof']['unresolved']}")
    for edge in selected:
        if edge.get('original_site')!=wanted[keys(edge)]['original_site']:
            raise ValueError(f'Original site changed: {keys(edge)}')
        if edge.get('shape_status')!='proved' or not edge.get('shape_evidence'):
            raise ValueError(f'Ordinary shape remains unresolved or refused: {keys(edge)}')
        if edge['outcome']=='transport-refused':raise ValueError(f'Ordinary transport refused: {keys(edge)}')
        evidence=edge['shape_evidence']
        if not (evidence.get('source_inputs') or evidence.get('source_sha256') or evidence.get('reviewed_original_impossibility')):
            raise ValueError(f'Missing actual source or original impossibility witness: {keys(edge)}')
        for p in edge.get('shape_probes',[]):
            if p['answer']['outcome']=='refused':raise ValueError(f'Actual ordinary shape refused: {keys(edge)}')
    regression=transport_tests(binary,report)
    compiler=[p['request'] for e in selected for p in e.get('shape_probes',[]) if p['request'].get('compiler')]
    if not compiler:raise ValueError('Compiler-context cohort has no production probe')
    accessor_queries=[dict(compiler[0],target=0x4db5f0),dict(compiler[0],target=0x4dc680)]
    accessor_answers=json.loads(subprocess.run([str(binary)],input=json.dumps(accessor_queries),text=True,capture_output=True,check=True).stdout)
    for q,a,expected in zip(accessor_queries,accessor_answers,[compiler[0]['compiler_return_pc'],0x70000090]):
        if a['outcome']=='refused' or a['compiler_eax']!=expected or a['compiler_eip']!=q['compiler_return_pc'] or a['compiler_esp']!=0x2000004:
            raise ValueError('Compiler accessor value or continuation changed')
    negative=[dict(compiler[0],input_mask=0),dict(compiler[0],output_mask=0),
              dict(compiler[0],argc=1),dict(compiler[0],receiver=1),
              dict(compiler[0],compiler_return_pc=0),dict(compiler[0],target=0xdeadbeef)]
    frame=next(q for q in compiler if q['target']!=compiler[0]['target'] or q['compiler_ebp_expression']=='arguments[0]')
    negative.append(dict(frame,compiler_unreadable=1))
    refused=json.loads(subprocess.run([str(binary)],input=json.dumps(negative),text=True,capture_output=True,check=True).stdout)
    if any(a['outcome']!='refused' for a in refused):raise ValueError('Malformed compiler diagnostic accepted')
    if report['complete']:raise ValueError('Unexpected claim of full call closure')
    (OUT/'ordinary-proof.json').write_text(json.dumps(dict(profile=report['profile'],sha256=report['sha256'],edges=selected),indent=2)+'\n')
    return dict(status='pass',selected_edges=len(selected),selected_callers=len({e['caller'] for e in selected}),
                outcomes=dict(Counter(e['outcome'] for e in selected)),
                actual_shape_probes=sum(len(e.get('shape_probes',[])) for e in selected),
                compiler_diagnostic_probes=len(compiler),malformed_compiler_probes=refused,
                compiler_accessor_regression=dict(kind='Synthetic API regression only; original-site proofs are recorded separately.',answers=accessor_answers),
                transport_regressions=regression,full_closure_complete=False,
                unrelated_obligations=report['counts'],evidence=str(OUT/'ordinary-proof.json'))


def provider_tests(binary):
    """Prove caller shapes, keeping native execution and full closure open."""
    cohort=json.loads((OUT/'provider-remaining.json').read_text())
    inventory=registry();owners=manifests()
    report=audit('claw-v1.0',inventory,owners,binary)
    key=lambda e:(e['caller'],e['site'],e['target'],e['kind'])
    wanted={key(e):e for e in cohort}
    if len(wanted)!=81:raise ValueError('The retained provider cohort must have exactly 81 sites')
    selected=[e for e in report['edges'] if 'original_site' in e and e['target'] not in inventory and not game(e['target'])]
    if len(selected)!=2924 or report['provider_call_proof']['extracted_edges']!=2924:
        raise ValueError(f"Provider shape cohort is incomplete: {report['provider_call_proof']}")
    remaining=[e for e in selected if key(e) in wanted]
    if len(remaining)!=81:raise ValueError('Lost a retained original provider site')
    for e in remaining:
        if e['original_site']!=wanted[key(e)]['original_site']:raise ValueError('Retained original site changed')
    callback_sites={0x49b765,0x49b780,0x49b7b8,0x49b7d7,0x49b7ee,0x49b807}
    replaced_callbacks=[]
    for e in selected:
        proof=e.get('shape_evidence',{})
        if e.get('shape_status')!='proved' or e['outcome']=='transport-refused':
            raise ValueError(f'Provider shape refused or unresolved: {key(e)}')
        excluded=e.get('excluded_native_activation_probes',[])
        if excluded:
            if (e['caller']!=0x49b730 or not e.get('native_context_proof')
                    or e['native_context_proof']['original_impossible']
                    or any(not p['request'].get('callback') or p['answer']['outcome']!='refused' for p in excluded)):
                raise ValueError('Native replacement hid a live transport refusal')
            replaced_callbacks.append(e)
        if not (proof.get('source_inputs') or proof.get('reviewed_original_impossibility')):
            raise ValueError(f'Missing current actual-source witness: {key(e)}')
        if any(digest(ROOT/p)!=h for p,h in proof.get('source_inputs',{}).items()):
            raise ValueError(f'Stale source witness: {key(e)}')
    if {e['site'] for e in replaced_callbacks}!=callback_sites:
        raise ValueError('Native dialog activation proof lost an original site')
    stdcall=[]
    for caller,site,target,pop in ((0x42bb00,0x42bb7b,0x546d2c,20),(0x42bbf0,0x42bc2b,0x546d50,16)):
        edge=next(e for e in selected if (e['caller'],e['site'],e['target'])==(caller,site,target))
        if not edge.get('shape_probes') or any(p['answer']['route']!='source-physical'
                or p['answer']['source_esp']!=0x2000004+pop or p['answer']['source_eip']!=site+6
                for p in edge['shape_probes']):raise ValueError('Imported stdcall source continuation regressed')
        stdcall.append(edge['original_site'])
    repaired=[];queries=[dict(p['request'],argc=p['request']['argc']+1)
        for e in selected if e['original_site'] in stdcall for p in e.get('shape_probes',[])]
    for caller,site,target in ((0x4141f0,0x4142f3,0x4a36f0),(0x49f1c0,0x49f2c3,0x4a36f0),
                               (0x423450,0x42346b,0x4f63ec),(0x4db4d0,0x4db556,0x4f2060)):
        e=next(e for e in report['edges'] if (e['caller'],e['site'],e['target'])==(caller,site,target))
        probes=e.get('shape_probes',[])
        if not probes or any(p['answer']['route']!='source-physical' or p['answer']['outcome']!='provider-unresolved'
                             or p['answer']['source_eip']!=p['request']['return_pc']
                             or p['answer']['source_esp']!=0x2000004 for p in probes):
            raise ValueError(f'Repaired native source edge regressed: {key(e)}')
        repaired.append(e);queries += [dict(p['request'],argc=p['request']['argc']+1) for p in probes]
    answers=json.loads(subprocess.run([str(binary)],input=json.dumps(queries),text=True,capture_output=True,
                       env={**os.environ,'CLAW_GAME_VERSION':'1.0'},check=True).stdout)
    if any(a['outcome']!='refused' for a in answers):raise ValueError('Malformed provider source shape accepted')
    graph=Graph(profile('claw-v1.0'),set());stale=Counter()
    reviews=json.loads((OUT/'provider-inline-shapes.json').read_text())
    for row in reviews:
        original=row['original_site'];m,_=owners[('claw-v1.0',original['caller'])]
        reader=SourceShapes(ROOT,m,import_slots=graph.program.imports)
        if not provider_inline(graph,original,m,reader,[row]):raise ValueError('Inline review no longer validates')
        for kind in ('source','original','path','parents'):
            bad=json.loads(json.dumps(row))
            if kind=='source':bad['source_inputs'][next(iter(bad['source_inputs']))]='0'*64
            elif kind=='original':bad['original_ranges'][0]['sha256']='0'*64
            elif kind=='path':bad['actual_source']['line']+=1
            else:bad['parent_calls'].append({})
            if provider_inline(graph,original,m,reader,[bad]):raise ValueError(f'Stale {kind} review accepted')
            stale[kind]+=1
    frontier=next(e for e in report['edges'] if (e['caller'],e['target'])==(0x4251f0,0x50257f))
    if (report['complete'] or report['counts'].get('transport-refused',0)
            or frontier['outcome']!='provider-unresolved' or frontier['shape_status']!='proved'
            or any(p['answer']['route']!='canonical-static-application' for p in frontier['shape_probes'])):
        raise ValueError('Context closure regressed or full closure was incorrectly claimed')
    static_query=frontier['shape_probes'][0]['request']
    negative=[dict(static_query,**change) for change in (
        {'argc':0},{'receiver':0},{'argument0':0},{'source':0},{'return_pc':1},
        {'input_mask':0},{'output_mask':0},{'preserve_mask':0x472},{'bad_stack':1},
        {'bad_wrapper':1},{'caller':0},{'site':0})]
    static_answers=json.loads(subprocess.run([str(binary)],input=json.dumps(negative),text=True,
        capture_output=True,env={**os.environ,'CLAW_GAME_VERSION':'1.0'},check=True).stdout)
    if any(a['outcome']!='refused' for a in static_answers):raise ValueError('Malformed static frontier accepted')
    # Ensure source changes reopen the native cut instead of silently allowing
    # a new dialog provider, direct callback registration or removed interception.
    paths=replaced_callbacks[0]['native_context_proof']['source_inputs']
    native_sources={p:(ROOT/p).read_text() for p in paths}
    for fragment in ('0x49b730','0x546d2c','DialogBoxParamA'):
        bad=dict(native_sources)
        bad['App/ClawApp.swift']+='\nlet unexpectedRegistration = '+fragment+'\n'
        try:dialog_replacement(bad)
        except ValueError:pass
        else:raise ValueError('New native dialog registration did not invalidate proof')
    bad=dict(native_sources)
    bad['Sources/ClawNativeMenuInterface.swift']=bad['Sources/ClawNativeMenuInterface.swift'].replace(
        'playersActive = true;showPlayers();return','playersActive = true;showPlayers()')
    try:dialog_replacement(bad)
    except ValueError:pass
    else:raise ValueError('Missing native dialog return did not invalidate proof')
    evidence=dict(profile=report['profile'],sha256=report['sha256'],edges=selected,
                  retained_sites=[e['original_site'] for e in remaining],repaired_source_edges=repaired,
                  native_replaced_callbacks=replaced_callbacks,
                  static_frontier=frontier,malformed_static_probes=static_answers,
                  full_closure_complete=False,unrelated_obligations=report['counts'])
    (OUT/'provider-proof.json').write_text(json.dumps(evidence,indent=2)+'\n')
    return dict(status='pass',selected_edges=len(selected),retained_edges=len(remaining),
                retained_outcomes=dict(Counter(e['outcome'] for e in remaining)),
                actual_shape_probes=sum(len(e.get('shape_probes',[])) for e in selected),
                repaired_source_edges=len(repaired),stdcall_source_edges=stdcall,malformed_source_shapes=answers,stale_reviews_rejected=dict(stale),
                full_closure_complete=False,static_frontier=frontier['original_site'],
                malformed_static_probes=static_answers,native_cut_invalidation_tests=4,
                native_replaced_callbacks=[e['original_site'] for e in replaced_callbacks],
                unrelated_obligations=report['counts'],evidence=str(OUT/'provider-proof.json'),
                contract='Caller shape and nonexecuting production transport only; native service execution, memory validity and value domains are separate.')


def receiver_tests(binary):
    """Analysis regressions plus the fixed entry packet's closure obligation."""
    inventory,owners=registry(),manifests()
    graph=Graph(profile('claw-v1.0'),{a for p,a in owners if p=='claw-v1.0' and a in inventory and game(a)})
    graph.census_tables()
    graph.roots.update(t for words in graph.tables.values() for t in words if game(t))
    graph.scan()
    election=json.loads((ROOT/'App/GameData/MENU/level-one-transports.json').read_text())
    proof=call_closure_receivers.audit(ROOT,graph,inventory,owners,binary,election,digest)
    (OUT/'receivers.json').write_text(json.dumps(proof,indent=2)+'\n')
    regressions=call_closure_receivers.self_test(graph.decoder)
    regressions+=call_closure_entry_receivers.self_test(graph.decoder,call_closure_receivers)
    regressions+=call_closure_entry_receivers.operand_tests(ROOT,digest,call_closure_receivers)
    regressions+=call_closure_entry_receivers.legacy_operand_tests()
    invalidations=call_closure_receivers.invalidation_tests(ROOT,graph,digest)
    invalidations['entry_packet']=call_closure_entry_receivers.invalidation_tests(
        ROOT,graph,proof['indirect_sites'],digest)
    pairing=json.loads((OUT/'entry-legacy-pairings.json').read_text())
    call_closure_entry_receivers.legacy_adapter_tests(ROOT,pairing,body,digest,heavy_lock,wait_load)
    invalidations['legacy_entry_pairings']=pairing['source_adapter_invalidations']
    expected={(table+i*4,target) for table,words in graph.tables.items() for i,target in enumerate(words) if game(target)}
    if {(r['site'],r['target']) for r in proof['slots']}!=expected or len(proof['slots'])!=len(expected):
        raise ValueError('Receiver analysis lost or duplicated original candidate slots')
    if {(r['caller'],r['site']) for r in proof['indirect_sites']}!={(r['caller'],r['site']) for r in graph.unresolved}:
        raise ValueError('Receiver analysis lost an original indirect site')
    queries=[];expected_routes=[]
    pairs=[(0x409920,0x40a440,'original-base-direct'),(0x414be0,0x474290,'original-base-direct'),
        (0x431df0,0x408580,'state-base-direct-431df0'),(0x463310,0x44df10,'enemy-lift-base-direct-463310'),
        (0x40e660,0x44e0c0,'boss-base-direct'),(0x484260,0x43efe0,'pirate-base-direct'),
        (0x483e10,0x44e0c0,'pirate-death-base-direct')]
    for caller,target,route in pairs:
        manifest,owned=owners[('claw-v1.0',caller)]
        edge=next(e for e in graph.edges if e['caller']==caller and e['target']==target)
        ins=next(graph.decoder.disasm(graph.bytes(edge['site'],15),edge['site'],count=1))
        extracted=SourceShapes(ROOT,manifest,import_slots=graph.program.imports).edge(edge,owned,ins.size)
        if not extracted:raise ValueError('Constructor caller shape requires review')
        shape,_=extracted
        tables=call_closure_receivers.receiver_tables(proof,graph,caller)
        if not tables:raise ValueError('Lost constructor receiver witness')
        for table,words in tables:
            query=dict(shape,caller=caller,target=target,table=table,
                words=call_closure_receivers.receiver_words(graph,table),
                tail_only=[int(x,16) for x in election['tail_only']],
                tail_thunks={str(int(k,16)):int(v,16) for k,v in election['tail_thunks'].items()},
                original_direct_calls={str(int(k,16)):[int(v,16) for v in values] for k,values in election['original_direct_calls'].items()})
            queries.extend([query,dict(query,receiver=0),dict(query,argc=shape['argc']+1)])
            expected_routes.extend([route,None,None])
    answers=json.loads(subprocess.run([str(binary)],input=json.dumps(queries),text=True,capture_output=True,
        env={**os.environ,'CLAW_GAME_VERSION':'1.0'},check=True).stdout)
    for i,answer in enumerate(answers):
        if i%3==0:
            if answer['outcome']!='transport-only' or answer['route'] not in (expected_routes[i],'original-base-direct'):
                raise ValueError(f'Receiver base transport refused: {answer}; expected {expected_routes[i]}')
        elif answer['outcome']!='refused':raise ValueError('Malformed constructor base request accepted')
    required={route for _,_,route in pairs}
    observed={a['route'] for i,a in enumerate(answers) if i%3==0}
    if not required.issubset(observed):raise ValueError(f'Missing production base routes: {required-observed}')
    evidence=OUT/'receivers.json'
    evidence.write_text(json.dumps(proof,indent=2)+'\n')
    return dict(status='pass' if proof['entry_receivers']['completion_obligation_met'] else 'fail',
        analysis_status='pass',entry_receivers=proof['entry_receivers'],
        analysis_regressions=regressions,invalidation_tests=invalidations,
        base_probes=[dict(request=q,answer=a) for q,a in zip(queries,answers)],
        base_routes=dict(Counter(a['route'] for i,a in enumerate(answers) if i%3==0)),
        original_candidate_tables=len(graph.tables),candidate_slots=len(expected),indirect_sites=len(graph.unresolved),
        table_statuses=proof['table_statuses'],slot_statuses=proof['slot_statuses'],
        transport_statuses=proof['transport_statuses'],indirect_kinds=proof['indirect_kinds'],
        completion_obligation_met=proof['completion_obligation_met'],evidence=str(evidence),contract=proof['contract'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['1.0','1.3','both'],default='both')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--transport-tests',action='store_true',help='focused inherited-base and source/tail/x87 proofs, not full closure')
    parser.add_argument('--receiver-tests',action='store_true',help='receiver regressions and complete source-bound domains for the fixed 685 entry sites')
    parser.add_argument('--entry-pairing-tests',action='store_true',help='captured legacy entry/ingress bindings and production adapter controls; incomplete pairings fail')
    parser.add_argument('--ordinary-tests',action='store_true',help='the exact 370 remaining ordinary sites plus transport regressions')
    parser.add_argument('--provider-tests',action='store_true',help='all 2924 provider caller shapes, the retained 81 sites and four source repairs')
    parser.add_argument('--provider-destination-tests',action='store_true',help='native service destination elections, grouped by admitted and unowned caller')
    parser.add_argument('--unowned-tests',action='store_true',help='require admitted callers to have no unowned targets after compiled production native routes')
    parser.add_argument('--profile-adapter-tests',action='store_true',help='v1.3 mapping obligation; unknown execution remains a failure')
    args=parser.parse_args()
    if args.output is None:args.output=OUT/('entry-pairing-tests.json' if args.entry_pairing_tests else 'receiver-tests.json' if args.receiver_tests else 'provider-destinations-tests.json' if args.provider_destination_tests else 'unowned-tests.json' if args.unowned_tests else 'provider-tests.json' if args.provider_tests else 'ordinary-tests.json' if args.ordinary_tests else 'transport-tests.json' if args.transport_tests else 'result.json')
    result=dict(check='call-closure',status='fail')
    result['inputs']={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__).resolve(),
        ROOT/'Sources/ClawCanonicalDispatch.h',ROOT/'Sources/ClawNativeMenuResources.swift',
        ROOT/'Sources/ClawNativeMenuInterface.cpp',ROOT/'Sources/ClawNativeMenuResources.cpp',
        ROOT/'Sources/ClawNativeMenuResources.h',ROOT/'Sources/ClawNativeLevelTransport.cpp',
        ROOT/'Sources/ClawNativeLevelTransport.h',ROOT/'Sources/ClawRuntime.h',
        ROOT/'Sources/ClawRuntime.hpp',ROOT/'scripts/call_closure_shapes.py',ROOT/'scripts/call_closure_reviews.py',
        ROOT/'scripts/call_closure_native.py',ROOT/'Sources/ClawNativeScene.swift',ROOT/'Sources/WorldFileRuntime.cpp']}
    result['inputs']['scripts/call_closure_receivers.py']=digest(ROOT/'scripts/call_closure_receivers.py')
    result['inputs']['scripts/call_closure_entry_receivers.py']=digest(ROOT/'scripts/call_closure_entry_receivers.py')
    result['inputs']['work/call-closure/receiver-entry-sites.json']=digest(OUT/'receiver-entry-sites.json')
    result['inputs']['App/GameData/MENU/level-one-transports.json']=digest(ROOT/'App/GameData/MENU/level-one-transports.json')
    result['inputs']['App/GameData/MENU/level-one-data.json']=digest(ROOT/'App/GameData/MENU/level-one-data.json')
    for path in ('Sources/ClawNativeCanonicalHost.swift','Sources/StaticConstructorThunksRuntime.cpp',
                 'Sources/ClawNativeMenuInterface.swift','App/ClawApp.swift'):
        result['inputs'][path]=digest(ROOT/path)
    try:
        if args.entry_pairing_tests:
            graph=Graph(profile('claw-v1.0'),set())
            pairing=call_closure_entry_receivers.legacy_pairings(ROOT,graph,manifests(),digest)
            pairing['operand_regressions']=call_closure_entry_receivers.legacy_operand_tests()
            call_closure_entry_receivers.legacy_adapter_tests(ROOT,pairing,body,digest,heavy_lock,wait_load)
            summary=dict(check='call-closure-entry-legacy-pairings',
                status='pass' if pairing['completion_obligation_met'] else 'fail',
                bound_functions=pairing['bound_functions'],bound_ingress=pairing['bound_ingress'],
                adapter_status=pairing['adapter_probe']['status'],
                analysis_status='pass',adapter_controls=pairing['adapter_probe']['checks'],
                source_adapter_invalidations=pairing['source_adapter_invalidations'],
                operand_regressions=pairing['operand_regressions'],
                evidence=str(OUT/'entry-legacy-pairings.json'))
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(summary,indent=2)+'\n')
            print(json.dumps(summary))
            return int(not pairing['completion_obligation_met'])
        binary=probe_build()
        if args.receiver_tests:
            result['check']='call-closure-entry-receivers'
            result['receiver_tests']=receiver_tests(binary)
            result['status']=result['receiver_tests']['status']
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(result,indent=2)+'\n')
            entry=result['receiver_tests']['entry_receivers']
            print(json.dumps(dict(check=result['check'],status=result['status'],output=str(args.output),
                analysis_status=result['receiver_tests']['analysis_status'],
                entry_sites=entry['sites'],entry_sites_proved=entry['proved_sites'],
                entry_completion_obligation_met=entry['completion_obligation_met'],
                completion_obligation_met=result['receiver_tests']['completion_obligation_met'])))
            return int(result['status']!='pass')
        if args.transport_tests or args.ordinary_tests or args.provider_tests:
            key='provider_tests' if args.provider_tests else 'ordinary_tests' if args.ordinary_tests else 'transport_tests'
            result[key]=provider_tests(binary) if args.provider_tests else ordinary_tests(binary) if args.ordinary_tests else transport_tests(binary)
            result['status']='pass'
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps(dict(check='call-closure-provider-regression' if args.provider_tests else 'call-closure-ordinary-regression' if args.ordinary_tests else 'call-closure-transport-regression',status='pass',output=str(args.output))))
            return 0
        inventory,owners=registry(),manifests()
        result['profiles']=[audit('claw-v'+name,inventory,owners,binary) for name in (['1.0','1.3'] if args.profile=='both' else [args.profile])]
        for report in result['profiles']:
            if report['profile']=='claw-v1.0':
                report['provider_destination_proof']=call_closure_providers.audit(
                    ROOT,report['edges'],owners,body,digest,heavy_lock,wait_load)
                destination=report['provider_destination_proof']
                (OUT/'provider-destinations.json').write_text(json.dumps(
                    dict(destination,original_sha256=report['sha256']),indent=2)+'\n')
                report['counts']=dict(Counter(e['outcome'] for e in report['edges']))
            report['acceptance']=closure_acceptance(report['edges'],report['unresolved'])
            report['counts'].setdefault('owner-unresolved',0)
            report['counts'].setdefault('transport-refused',0)
            report.setdefault('full_closure_complete',report['complete'])
            report['complete']=report['acceptance']['complete']
        result['reviewed_impossible_edges']=[e['original_site'] for p in result['profiles'] for e in p['edges'] if e.get('caller_shape',{}).get('impossible')]
        result['status']='pass' if all(row['complete'] for row in result['profiles']) else 'fail'
        if args.profile_adapter_tests:
            if args.profile!='1.3':raise ValueError('--profile-adapter-tests requires --profile 1.3')
            result['check']='call-closure-profile-adapters'
            result['status']='pass' if result['profiles'][0]['profile_adapter_proof']['completion_obligation_met'] else 'fail'
        if args.unowned_tests:
            if args.profile=='1.3':raise ValueError('--unowned-tests requires the 1.0 profile')
            result['check']='call-closure-unowned-regression'
            result['status']='pass' if (result['profiles'][0]['unowned_call_proof']['completion_obligation_met']
                and not result['profiles'][0]['counts'].get('transport-refused',0)) else 'fail'
        if args.provider_destination_tests:
            if args.profile=='1.3':raise ValueError('--provider-destination-tests requires the 1.0 profile')
            result['check']='call-closure-provider-destinations'
            result['status']='pass' if result['profiles'][0]['provider_destination_proof']['completion_obligation_met'] else 'fail'
    except Exception as error:
        result['error']=f'{type(error).__name__}: {error}'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(check=result['check'],status=result['status'],output=str(args.output),error=result.get('error'),
                         profiles=[dict({k:r[k] for k in ('profile','functions','candidate_tables','counts','complete')},
                            warnings=r['acceptance']['warnings'],
                            provider_destinations_missing=len((r.get('provider_destination_proof') or {}).get('missing_admitted_destinations',[])),
                            unowned_obligation_met=(r.get('unowned_call_proof') or {}).get('completion_obligation_met')) for r in result.get('profiles',[])])))
    return int(result['status']!='pass')


if __name__=='__main__':
    raise SystemExit(main())
