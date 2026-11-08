"""Entry-ECX receiver obligations for the fixed call-closure work packet.

This module never promotes the may-context inventory to a complete domain.
It records original ingress and vptr lifetime facts independently of translated
caller shapes. A local original vptr write is not native activation evidence.
All address/byte witnesses are emitted only to ignored work/.
"""
from collections import Counter, defaultdict, deque
import hashlib
import json
import os
import re
import subprocess

from capstone import CS_AC_WRITE, CS_GRP_CALL
from capstone.x86 import X86_OP_IMM, X86_OP_MEM


def expression(value):
    return tuple(expression(x) for x in value) if isinstance(value,(tuple,list)) else value


def packet(root, graph, indirect, digest, data=None):
    path = root/'work/call-closure/receiver-entry-sites.json'
    data = json.loads(path.read_text()) if data is None else data
    if data.get('profile') != graph.program.name or data.get('original_sha256') != graph.program.sha256:
        raise ValueError('Entry receiver packet belongs to a different original')
    expected = data.get('sites', [])
    keys = [(r['caller'], r['site']) for r in expected]
    if len(keys) != 685 or len(set(keys)) != len(keys):
        raise ValueError('Entry receiver packet must retain 685 distinct original sites')
    actual = {(r['caller'], r['site']): r for r in indirect}
    for row in expected:
        key = row['caller'], row['site']
        found = actual.get(key)
        if found is None:
            raise ValueError(f'Lost entry receiver site {key}')
        original_receiver=expression(row.get('receiver_expression'))
        base=original_receiver[1] if original_receiver and original_receiver[0]=='add' else original_receiver
        if (found.get('indirect_kind') != 'vtable-slot' or base!=('entry','ecx') or
                expression(found.get('receiver_expression')) != original_receiver):
            raise ValueError(f'Entry receiver operand changed at {key}')
        for name in ('size', 'sha256', 'slot', 'kind'):
            if row[name] != found[name]:
                raise ValueError(f'Entry receiver original {name} changed at {key}')
        raw = graph.bytes(row['site'], row['size'])
        if len(raw) != row['size'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError(f'Entry receiver original bytes changed at {key}')
    return dict(path=str(path.relative_to(root)), sha256=digest(path), sites=len(keys)), expected


def _write_effect(ins, state, receiver, object_expression):
    """Classify effects on the first word of the *same* entry receiver.

    Distinct symbolic bases are not assumed disjoint. Partial/unknown stores,
    implicit string stores and calls are barriers. Push/pop stack writes are
    also barriers: heap/stack separation must not be invented here.
    """
    if ins.group(CS_GRP_CALL):
        target = ins.operands[0].imm & 0xffffffff if ins.operands[0].type == X86_OP_IMM else None
        return ('call', ins.address, target)
    writes = [op for op in ins.operands if op.type == X86_OP_MEM and op.access & CS_AC_WRITE]
    if ins.mnemonic.startswith(('push', 'rep ', 'stos', 'movs', 'ins', 'enter')):
        return ('implicit-write', ins.address)
    for op in writes:
        dest = receiver.address(ins, op.mem, state)
        base, offset = receiver.split_offset(dest)
        object_base,object_offset=receiver.split_offset(object_expression)
        offset=(offset-object_offset)&0xffffffff
        if offset>=0x80000000:offset-=0x100000000
        # Writes wholly outside the vptr on this exact receiver preserve it.
        if base == object_base and (offset >= 4 or offset + op.size <= 0):
            continue
        if (ins.mnemonic == 'mov' and len(ins.operands) == 2 and
                dest == object_expression and op.size == 4 and
                ins.operands[1].type == X86_OP_IMM):
            return ('table-write', ins.address, ins.operands[1].imm & 0xffffffff)
        return ('aliasing-write', ins.address)
    return None


def lifetimes(nodes, root, flow, receiver, object_expression=('entry','ecx')):
    """Reaching definitions of entry ECX's vptr, retaining every barrier.

    This is deliberately independent of receiver_contexts. A direct base call
    is an effect barrier even when its ECX is the original receiver: a base
    constructor/destructor can install another table during its lifetime.
    """
    entry = frozenset({('entry-domain', root)})
    incoming = {root: entry}
    pending = deque([root])
    while pending:
        pc = pending.popleft()
        effect = _write_effect(nodes[pc], flow.get(pc, {}), receiver,object_expression)
        out = frozenset({effect}) if effect else incoming[pc]
        for nxt in receiver.successors(nodes[pc], nodes):
            new = incoming.get(nxt, frozenset()) | out
            if nxt == root:
                new |= entry
            if incoming.get(nxt) != new:
                incoming[nxt] = new
                pending.append(nxt)
    return incoming


def original_lifetime(row, nodes, flow, reaching, receiver):
    ins = nodes[row['site']]
    expr = receiver.operand(ins, ins.operands[0], flow[row['site']])
    table_load, _ = receiver.split_offset(expr[1])
    loads = []
    for pc, candidate in nodes.items():
        ops = candidate.operands
        if candidate.mnemonic != 'mov' or len(ops) != 2 or ops[1].type != X86_OP_MEM or ops[1].size != 4:
            continue
        if receiver.operand(candidate, ops[1], flow.get(pc, {})) == table_load:
            loads.append(pc)
    events = set().union(*(reaching.get(pc, frozenset()) for pc in loads)) if loads else set()
    current = reaching.get(row['site'], frozenset())
    known = sorted({e[2] for e in events if e[0] == 'table-write'})
    complete = bool(events) and all(e[0] == 'table-write' for e in events)
    current_tables = {e[2] for e in current if e[0] == 'table-write'}
    current_complete = bool(current) and all(e[0] == 'table-write' for e in current)
    # Equality of two may-sets is not path correlation. Require that no vptr
    # effect can intervene between the actual load and the call as well.
    stable=bool(loads)
    for start in loads:
        pending=list(receiver.successors(nodes[start],nodes));seen=set()
        while pending:
            pc=pending.pop()
            if pc in seen or pc==row['site']:continue
            seen.add(pc)
            if _write_effect(nodes[pc],flow.get(pc,{}),receiver,expression(row.get('receiver_expression',('entry','ecx')))):
                stable=False;break
            pending.extend(receiver.successors(nodes[pc],nodes))
    return dict(table_loads=[receiver.witness(nodes[pc]) for pc in sorted(loads)],
        reaching_effects=[dict(kind=e[0],site=e[1],**({'value':e[2]} if len(e)==3 else {})) for e in sorted(events,key=repr)],
        possible_local_tables=known, original_local_domain_complete=complete,
        current_receiver_tables=sorted(current_tables),
        operand_matches_current_receiver=(stable and complete and current_complete and set(known)==current_tables),
        contract='Original reaching vptr definitions only. Calls and potentially aliasing writes invalidate the table. Source stores, native activation and emitted call operands remain independent obligations.')


def source_binding(root, owners, graph, edge, shape_readers, shape_type, digest):
    declared = owners.get((graph.program.name, edge['caller']))
    if not declared:
        return dict(status='caller-owner-unresolved')
    manifest, owned = declared
    family = manifest['id']
    if family not in shape_readers:
        shape_readers[family] = shape_type(root, manifest, import_slots=graph.program.imports)
    proof = shape_readers[family].edge(edge, owned, edge['size'])
    reader=shape_readers[family]
    result = dict(family=family, source_inputs={
        str((root/'Tests/families'/f'{family}.json').relative_to(root)):digest(root/'Tests/families'/f'{family}.json'),
        **{p:hashlib.sha256(text.encode()).hexdigest() for p,text in reader.files.items()}})
    if proof:
        result.update(status='shape-extracted', caller_shape=proof[0], shape_evidence=proof[1])
    else:
        result['status'] = 'call-shape-unresolved'
    return result


def native_invocations(root, digest, callers):
    """A source census, never a claim that the listed files are all ingress.

    Numeric target references retain the emitted receiver expression verbatim.
    Computed targets remain visible; their receiver pairing is not deduced from
    target membership in a table. No regex match is used to prove activation.
    """
    paths = ('Sources/ClawNativeMenuResources.swift', 'Sources/ClawNativeMenuInterface.swift',
             'Sources/ClawNativeCanonicalHost.swift')
    from call_closure_shapes import close,split,integer,clean
    rows = []
    for name in paths:
        path = root/name
        text = path.read_text()
        code=clean(text)
        for match in re.finditer(r'\b(?:invoke|transport)\s*\(',code):
            if re.search(r'\bfunc\s*$',code[max(0,match.start()-12):match.start()]):continue
            start=code.index('(',match.start())
            try:end=close(code,start)
            except (ValueError,IndexError):continue
            arguments=split(code[start+1:end]);target=integer(arguments[0]) if arguments else None
            if target in callers or target is None:
                rows.append(dict(path=name,sha256=hashlib.sha256(text.encode()).hexdigest(),
                    line=code[:match.start()].count('\n')+1,source=code[match.start():end+1],
                    arguments=arguments,receiver_expression=arguments[1] if len(arguments)>1 else None,
                    selected_targets=[target] if target in callers else [],computed_target=target is None,
                    status='native-function-receiver-pairing-unresolved'))
    return rows


def legacy_pairings(root, graph, owners, digest):
    """Keep the captured prerequisite intact, including functions with no body.

    A routed entry and a matched emitted call are different facts. In particular
    a source target reference, a v1.3 owner at a v1.0 address, or a rejecting
    startup skeleton is never an entry/receiver witness.
    """
    from call_closure_shapes import SourceShapes, close
    path=root/'work/call-closure/receiver-entry-legacy-ingress.json'
    captured=json.loads(path.read_text())
    if (captured['profile']!=graph.program.name or
            captured['original_sha256']!=graph.program.sha256 or
            captured['entry_packet']['sha256']!=digest(root/captured['entry_packet']['path'])):
        raise ValueError('Stale legacy entry prerequisite')
    functions=captured['source_pairing_functions']
    selected=captured['selected_sites'];ingress=captured['legacy_original_ingress']
    if (len(functions)!=180 or len(set(functions))!=180 or len(selected)!=315 or len(ingress)!=239 or
            set(functions)!=(set(captured['selected_legacy_callers'])|{r['caller'] for r in ingress})):
        raise ValueError('Legacy prerequisite lost a captured function or site')
    references=[r for group in captured['original_pointer_references'].values() for r in group]
    for row in selected+ingress+references:
        raw=graph.bytes(row['site'],row['size'])
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError(f'Legacy original instruction/reference changed: {row["site"]:#x}')
        row['original_bytes']=raw.hex()
        if row in selected or row in ingress:
            ins=next(graph.decoder.disasm(raw,row['site'],count=1),None)
            if ins is None or ins.size!=row['size']:raise ValueError('Legacy site is not one instruction')
            row['original_instruction']=dict(mnemonic=ins.mnemonic,operands=ins.op_str)
    inputs={str(path.relative_to(root)):digest(path)}
    def read(name):
        inputs[name]=digest(root/name)
        return (root/name).read_text()
    for name in ('scripts/call_closure_entry_receivers.py','scripts/call_closure_shapes.py',
                 'scripts/check-call-closure.py'):
        read(name)
    swift=read('Sources/ClawNativeMenuResources.swift')
    installation=read('Sources/ClawNativeMenuInterface.swift')
    interface=read('Sources/ClawNativeMenuInterface.cpp')
    read('Sources/ClawNativeMenuResources.cpp')
    read('Sources/ClawNativeCanonicalHost.swift')
    legacy=read('Sources/ApplicationLevelProgressionRuntime.cpp')
    read('Sources/ApplicationLevelProgressionRuntime.h')
    read('Sources/ClawRuntime.h')
    read('tools/claw/app_sources.json')
    registry=read('Sources/ClawCanonicalDispatch.h')
    primary_registry=registry.split('clawCanonicalEntries[] = {',1)[1].split('\n};',1)[0]
    startup=read('Sources/StartupStateTwoRuntime.cpp')
    # These are source-bound path conditions, not a whole-program absence test.
    required={
        'resource-invoke':(swift,'gameEntry?(function,receiver,args.baseAddress,UInt32(args.count),host,&result)'),
        'resource-first':(swift,'claw_native_menu_resource_entry(function,receiver,args.baseAddress,UInt32(args.count),host,&result)'),
        'installed-interface':(installation,'resources.gameEntry = claw_native_menu_interface_entry'),
        'interface-credits':(interface,'if(creditsEntry(f,self,a,n,h,out)) return 1;'),
        'credits-entry':(interface,'claw_application_level_progression_entry(f,self,a,n,&c,creditsDependency,h,out)'),
        'credits-receiver':(interface,'q.receiver=e->receiver;'),
        'credits-local-receiver':(interface,'if(bit==8) q.receiver=token;else q.arguments[bit]=token;'),
        'credits-host-call':(interface,'auto result=h->call(h->user,&q);'),
        'legacy-body':(legacy,'body(r, f, p, args)'),
        'legacy-receiver':(legacy,'q.receiver = p;'),
    }
    for label,(text,needle) in required.items():
        if needle not in text:raise ValueError(f'Legacy adapter requires review: {label}')
    title_signature='    private func titleService(_ function:UInt32,_ state:UInt32,_ args:[UInt32])->UInt32?'
    title_at=installation.index(title_signature);title_start=installation.index('{',title_at)
    title_source=installation[title_at:close(installation,title_start,'{','}')+1]
    title_branch='if let result = self.titleService(f,r,a) {return result}'
    if title_branch not in installation:raise ValueError('Native title entry installation changed')
    reader=SourceShapes(root,dict(sources=['Sources/ApplicationLevelProgressionRuntime.cpp'],owned=[]))
    # creditsEntry is in the native interface, not the legacy translation unit.
    at=interface.index('uint32_t creditsEntry(');start=interface.index('{',at)
    credits=interface[start+1:close(interface,start,'{','}')]
    switch=credits[:credits.index('default:return 0;')]
    routed={int(m,16) for m in re.findall(r'case\s+0x([0-9a-f]+)\s*:',switch)}
    source_body=reader.resolve('body')
    if source_body is None:raise ValueError('Legacy body dispatcher disappeared')
    bindings=[];readers={}
    for address in functions:
        row=dict(function=address,status='entry-adapter-unresolved',complete=False,
                 original_pointer_references=captured['original_pointer_references'].get(str(address),[]))
        if address in (0x408d30,0x408e20,0x408fa0):
            signature='uint32_t function_'+f'{address:x}'+'('
            start=startup.index('{',startup.index(signature))
            stub=startup[start+1:close(startup,start,'{','}')]
            row['available_source']=dict(path='Sources/StartupStateTwoRuntime.cpp',source=stub,
                implemented='run.fail(CLAW_FAULT_UNIMPLEMENTED' not in stub,
                contract='An available source body is not proof of app composition or nonactivation.')
        declared=owners.get((graph.program.name,address))
        if declared:
            manifest,owned=declared
            # Require an actual primary registry row, not just a manifest.
            if re.search(r'\{0x'+f'{address:x}'+r'u,.*"'+re.escape(manifest['id'])+r'"',primary_registry):
                for name in manifest['sources']:read(name)
                row.update(status='canonical-entry-bound',family=manifest['id'],complete=True,
                           receiver_expression='receiver',obligations=['emitted-site-correspondence','receiver-domain','activation'])
        elif address in (0x408d30,0x408e20,0x408fa0):
            row.update(status='native-title-entry-bound',complete=True,
                adapter='resources.gameService -> titleService(f,r,a)',receiver_expression='state',
                source_adapter=dict(path='Sources/ClawNativeMenuInterface.swift',
                    branch=title_branch,source=title_source),
                obligations=['original-source-site-correspondence','receiver-domain','field-and-callback-domains','activation'])
        elif address in routed:
            region=reader.region(source_body['text'],{'f':str(address)})
            if not region or not re.search(r'case\s+0x'+f'{address:x}'+r'\s*:',source_body['text']):
                # An unpaired legacy adapter is an unproved class, not a
                # demonstrated refusal or missing canonical game owner.
                row['reason']='Native credits route has no paired legacy body'
                bindings.append(row)
                continue
            operands=reader.legacy_credits_calls(address)
            row.update(status='legacy-credits-entry-bound',complete=True,
                receiver_expression='p',body_receiver_expression='p',
                adapter='creditsEntry -> claw_application_level_progression_entry -> body',
                source_body_sha256=hashlib.sha256(region.encode()).hexdigest(),
                source_body_witness=dict(path=source_body['path'],source=region),
                emitted_operand_candidates=operands,
                dependency_receiver='e->receiver; localMask bit 8 substitutes an owned temporary token',
                obligations=['emitted-site-correspondence','receiver-domain','callback-and-local-buffer-domain','activation'])
        bindings.append(row)
    by_function={r['function']:r for r in bindings}
    ingress_rows=[]
    for edge in ingress:
        binding=source_binding(root,owners,graph,edge,readers,SourceShapes,digest)
        from call_closure_shapes import integer
        candidates=[r for r in by_function[edge['caller']].get('emitted_operand_candidates',[])
                    if r['api']=='legacy-invoke' and integer(r['args'][0])==edge['target']]
        # A legacy entry route alone says nothing about a particular original
        # CALL's emitted operands. Keep it open until a site witness exists.
        ingress_rows.append(dict(original=edge,caller_entry_status=by_function[edge['caller']]['status'],
            source_binding=binding,legacy_operand_candidates=candidates,
            complete=binding['status']=='shape-extracted',
            status='source-bound' if binding['status']=='shape-extracted' else 'emitted-site-pairing-unresolved'))
    result=dict(profile=graph.program.name,original_sha256=graph.program.sha256,
        source_inputs=inputs,functions=bindings,original_ingress=ingress_rows,
        selected_sites=selected,native_invocations=native_invocations(root,digest,set(functions)),
        original_pointer_references=captured['original_pointer_references'],
        function_statuses=dict(Counter(r['status'] for r in bindings)),
        bound_functions=sum(r['complete'] for r in bindings),
        bound_ingress=sum(r['complete'] for r in ingress_rows),
        completion_obligation_met=all(r['complete'] for r in bindings+ingress_rows),
        contract='Entry routing only. Every captured original site and activation reference remains present; unresolved emitted operands and receiver/field/callback domains are not discharged by entry routing.')
    (root/'work/call-closure/entry-legacy-pairings.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def pairing_inputs_current(root, result, digest):
    return all((root/name).exists() and digest(root/name)==expected
               for name,expected in result['source_inputs'].items())


def title_adapter_tests(root, result, heavy_lock, wait_load):
    rows=[r for r in result['functions'] if r['status']=='native-title-entry-bound']
    if not rows:return dict(status='pass',requests=0)
    witness=rows[0]['source_adapter']
    source='''import Foundation
final class Heap {
 var enabled=true
 func lookupBytes(_ token:UInt32,count:UInt32)->Int? {enabled && token==0x61000000 ? 1:nil}
}
final class Resources {
 var fault:UInt32=0
 var calls:[[UInt32]]=[]
 func fail(_ f:UInt32)->UInt32 {fault=f;return 0}
 func invoke(_ f:UInt32,_ r:UInt32,_ a:[UInt32])->UInt32 {calls.append([f,r]+a);return 0}
 func allocate(_ n:UInt32)->UInt32 {0x62000000}
 func release(_ token:UInt32) {}
}
struct Input {var window:UInt32=0}
final class Base {var windowInput:Input?}
final class Probe {
 let heap=Heap(),resources=Resources(),base=Base()
 var words:[UInt32:UInt32]=[0x61000000:0x50c2d4,0x6100000c:0x61001000,
  0x61000004:0x61002000,0x61000034:1,0x6100002c:1,0x61000154:10,
  0x61001004:0x61003000,0x61001028:0x61007000,0x61003010:0x61004000,
  0x6100402c:0x61005000,0x537200:0x61006000,0x53720c:1]
 var transports:[[UInt32]]=[]
 func w(_ token:UInt32)->UInt32 {words[token] ?? 0}
 func put(_ token:UInt32,_ value:UInt32) {words[token]=value}
 func transport(_ f:UInt32,_ r:UInt32,_ a:[UInt32])->UInt32 {transports.append([f,r]+a);return 0}
 func installed(_ f:UInt32,_ r:UInt32,_ a:[UInt32],enabled:Bool=true)->UInt32? {
  if enabled {
'''+witness['branch']+'''
  }
  return nil
 }
'''+witness['source']+'''
}
let functions:[UInt32]=['''+','.join(str(r['function']) for r in rows)+''']
for f in functions {
 let p=Probe(),args:[UInt32]=f==0x408d30 ? [7]:[]
 precondition(p.installed(f,0x61000000,args)==1 && p.resources.fault==0)
 if f==0x408fa0 {precondition(p.resources.calls.contains([0x4b98b0,0x61005000,0]))}
 if f==0x408e20 {precondition(p.w(0x61000154)==9 && p.resources.calls.contains([0x4b3490,0x61006000]))}
 if f==0x408d30 {precondition(p.transports.contains([0x4f6286,0x61007010,0x52374c,0x62000000]))}
 let wrong=Probe();precondition(wrong.installed(f,0x61000004,args)==0 && wrong.resources.fault==f)
 let missing=Probe();missing.heap.enabled=false
 precondition(missing.installed(f,0x61000000,args)==0 && missing.resources.fault==f)
 let table=Probe();table.words[0x61000000]=0
 precondition(table.installed(f,0x61000000,args)==0 && table.resources.fault==f)
 let disabled=Probe();precondition(disabled.installed(f,0x61000000,args,enabled:false)==nil && disabled.resources.fault==0)
}
print("native-title-entry-receiver-controls-pass")
'''
    key=hashlib.sha256(source.encode()).hexdigest()[:24]
    folder=root/'work/build/call-closure-title-entry'/key;folder.mkdir(parents=True,exist_ok=True)
    binary=folder/'probe';(folder/'main.swift').write_text(source)
    with heavy_lock():
        wait_load()
        subprocess.run(['xcrun','swiftc','-O',str(folder/'main.swift'),'-o',str(binary)],check=True)
    if subprocess.check_output([str(binary)],text=True).strip()!='native-title-entry-receiver-controls-pass':
        raise ValueError('Native title receiver adapter controls failed')
    return dict(status='pass',requests=len(rows)*5,binary=str(binary),
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        contract='Production installed title branch and full titleService with recording invocation endpoints and explicit memory fixture. Gameplay and complete activation/field domains remain open.')


def legacy_adapter_tests(root, result, body, digest, heavy_lock, wait_load):
    """Execute the real entry adapters; body effects are a recording endpoint.

    This deliberately does not execute or certify credits gameplay, nor does
    it identify an original CALL site with a source CALL site.
    """
    if not pairing_inputs_current(root,result,digest):
        raise ValueError('Stale legacy entry pairings before adapter execution')
    interface=(root/'Sources/ClawNativeMenuInterface.cpp').read_text()
    legacy=(root/'Sources/ApplicationLevelProgressionRuntime.cpp').read_text()
    extracts={name:body(text,signature) for name,text,signature in (
        ('credits',interface,'uint32_t creditsEntry('),
        ('dependency',interface,'uint32_t creditsDependency('),
        ('entry',legacy,'extern "C" uint32_t claw_application_level_progression_entry('),
        ('owned',legacy,'bool owned(uint32_t f)'),
        ('arity',legacy,'uint32_t arity(uint32_t f)'))}
    functions=[r['function'] for r in result['functions'] if r['status']=='legacy-credits-entry-bound']
    source='''#include "ClawRuntime.h"
#include "ApplicationLevelProgressionRuntime.h"
#include <algorithm>
#include <cassert>
#include <cstdio>
struct Failure {};
struct Run {
 ClawApplicationLevelProgressionContext &c;
 ClawApplicationLevelProgressionDependency d; void *u;
 uint32_t invoke(uint32_t,uint32_t,std::initializer_list<uint32_t>) {assert(false);return 0;}
};
static uint32_t expectedFunction,expectedReceiver,expectedCount,bodyCalls,hostCalls;
uint32_t body(Run &,uint32_t f,uint32_t p,const uint32_t *a) {
 assert(f==expectedFunction && p==expectedReceiver);
 for(uint32_t i=0;i<expectedCount;++i) assert(a[i]==0x72000000+i);
 ++bodyCalls; return 0x12345678;
}
'''+extracts['owned']+'\n'+extracts['arity']+'\n'+extracts['entry']+'\n'+extracts['dependency']+'\n'+extracts['credits']+'''
uint32_t observe(void *,const ClawCall *q) {
 assert(q->function==expectedFunction && q->receiver==expectedReceiver && q->argumentCount==expectedCount);
 for(uint32_t i=0;i<expectedCount;++i) assert(q->arguments[i]==0x72000000+i);
 ++hostCalls;return 0x12345678;
}
int main() {
 ClawHost host{};host.call=observe;
 uint32_t args[2]={0x72000000,0x72000001},out=0;
 const uint32_t functions[]={'''+','.join(str(f) for f in functions)+'''};
 for(auto f:functions) for(uint32_t receiver:{0u,0x61000000u,0x61000004u}) {
  expectedFunction=f;expectedReceiver=receiver;expectedCount=arity(f);
  auto before=bodyCalls;
  assert(creditsEntry(f,receiver,args,expectedCount,&host,&out)==1);
  assert(bodyCalls==before+1 && out==0x12345678 && host.fault==0);
  assert(creditsEntry(f,receiver,args,expectedCount+1,&host,&out)==0);
  assert(bodyCalls==before+1 && host.fault!=0);host.fault=0;
  ClawApplicationLevelProgressionContext context{};
  ClawApplicationLevelProgressionCall q{};q.function=f;q.receiver=receiver;q.argumentCount=expectedCount;
  std::copy_n(args,expectedCount,q.arguments);
  auto calls=hostCalls;
  assert(creditsDependency(&context,&q,&host)==0x12345678 && hostCalls==calls+1);
 }
 auto before=bodyCalls;
 assert(creditsEntry(0x40b280,0,args,0,&host,&out)==0 && bodyCalls==before);
 std::puts("entry-and-dependency-receiver-controls-pass");
}
'''
    key=hashlib.sha256(source.encode()).hexdigest()[:24]
    folder=root/'work/build/call-closure-legacy-entry'/key
    folder.mkdir(parents=True,exist_ok=True)
    binary=folder/'probe';(folder/'probe.cpp').write_text(source)
    with heavy_lock():
        wait_load()
        subprocess.run(['xcrun','clang++','-std=c++17','-O1','-I'+str(root/'Sources'),
                        str(folder/'probe.cpp'),'-o',str(binary)],check=True)
    output=subprocess.check_output([str(binary)],text=True).strip()
    if output!='entry-and-dependency-receiver-controls-pass':raise ValueError(output)
    if not pairing_inputs_current(root,result,digest):
        raise ValueError('Legacy entry inputs changed during adapter execution; rerun')
    result['adapter_probe']=dict(binary=str(binary),functions=functions,checks=len(functions)*3*3+1,
        status='pass',source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        extracted_source=extracts,
        contract='Production C++ entry and nonlocal dependency adapters with recording body/host endpoints. Null and interior receivers are preserved, not validated. Local-mask remapping and gameplay effects remain obligations.')
    result['native_title_adapter_probe']=title_adapter_tests(root,result,heavy_lock,wait_load)
    if not pairing_inputs_current(root,result,digest):
        raise ValueError('Legacy entry inputs changed during title execution; rerun')
    # Refuse stale output for each independently mutable source/packet input.
    invalidations=[]
    for name in result['source_inputs']:
        if pairing_inputs_current(root,result,lambda p: 'changed' if p==root/name else digest(p)):
            raise ValueError('Stale entry pairing accepted: '+name)
        invalidations.append(name)
    result['source_adapter_invalidations']=dict(status='pass',inputs=invalidations)
    (root/'work/call-closure/entry-legacy-pairings.json').write_text(json.dumps(result,indent=2)+'\n')
    return result['adapter_probe']


def legacy_operand_tests():
    from call_closure_shapes import SourceShapes
    examples=[
        ('explicit-legacy-zero-receiver','r.invoke(7,0,{first,second});',0,'0',2),
        ('legacy-virtual-object','r.virt(p,12,{value});',0,'p',1),
        ('legacy-arguments-remain-unknown','r.invoke(7,p,computed);',0,None,None),
        ('legacy-entry-selector-prunes-other-body','r.invoke(7,p);',1,'p',0),
    ]
    results=[]
    for name,call,selector,expected_receiver,expected_argc in examples:
        text='switch(f) {case 0: '+(call if selector==0 else 'r.invoke(9,other,{x,y,z});')+' break; case 1: '+(call if selector==1 else 'return 0;')+' break; default: return 0;}'
        fn=dict(params=['r','f','p','a'],text=text,path='fixture.cpp',offset=0)
        reader=SourceShapes.__new__(SourceShapes)
        reader.resolve=lambda name:fn if name=='body' else None
        reader.files={'fixture.cpp':text}
        found=reader.legacy_credits_calls(selector)
        if len(found)!=1:raise ValueError(f'Legacy operand selector regression: {name}')
        shape=found[0]['shape']
        if expected_argc is None:
            if shape is not None:raise ValueError('Legacy operands inferred from missing argument list')
        elif shape['argc']!=expected_argc or shape['receiver_expression']!=expected_receiver:
            raise ValueError(f'Legacy emitted operand regression: {name}')
        if found[0]['site_correspondence_complete']:raise ValueError('Legacy candidate promoted to original site proof')
        results.append(dict(name=name,status='pass'))
    return results


def audit(root, graph, inventory, owners, indirect, node_map, flow, receiver,
          shape_type, digest, binary, election):
    binding, selected = packet(root, graph, indirect, digest)
    pairings=legacy_pairings(root,graph,owners,digest)
    if not pairing_inputs_current(root,pairings,digest):
        raise ValueError('Legacy pairing inputs changed during receiver audit')
    paired_functions={r['function']:r for r in pairings['functions']}
    paired_ingress={(r['original']['caller'],r['original']['site']):r for r in pairings['original_ingress']}
    selected_callers = {r['caller'] for r in selected}
    ingress = defaultdict(list)
    readers = {}
    lifetime = {}
    for edge in graph.edges:
        if edge['target'] not in selected_callers:
            continue
        caller = edge['caller']
        if caller not in node_map:
            node_map[caller] = receiver.instructions(graph, caller)
        nodes = node_map[caller]
        if edge['site'] not in nodes:
            raise ValueError('Entry ingress lacks an original instruction')
        if caller not in flow:
            flow[caller] = receiver.states(nodes, caller)
        ins = nodes[edge['site']]
        expr = flow[caller].get(edge['site'], {}).get('ecx')
        witness = dict(edge, **{k:v for k,v in receiver.witness(ins).items() if k not in edge},
                       receiver_expression=expr, receiver_origin=receiver.origin(expr))
        object_base,_=receiver.split_offset(expr)
        if object_base==('entry','ecx'):
            key=caller,expr
            if key not in lifetime:lifetime[key]=lifetimes(nodes,caller,flow[caller],receiver,expr)
            effects=lifetime[key].get(edge['site'],frozenset())
            witness['original_receiver_lifetime']=dict(
                object_expression=expr,
                reaching_effects=[dict(kind=e[0],site=e[1],
                    **({'value':e[2]} if len(e)==3 else {}),
                    original=receiver.witness(nodes[e[1]])) for e in sorted(effects,key=repr)],
                local_table_values=sorted({e[2] for e in effects if e[0]=='table-write'}),
                requires_entry_domain=any(e[0]=='entry-domain' for e in effects),
                has_effect_barrier=any(e[0] not in ('entry-domain','table-write') for e in effects))
        witness['source_binding'] = source_binding(root, owners, graph, witness, readers, shape_type, digest)
        if (caller,edge['site']) in paired_ingress:
            witness['legacy_entry_pairing']=paired_ingress[caller,edge['site']]
        ingress[edge['target']].append(witness)
    rows = {(r['caller'],r['site']):r for r in indirect}
    selected_rows = []
    for expected in selected:
        caller = expected['caller']
        row = rows[caller,expected['site']]
        nodes = node_map[caller]
        if caller not in flow:
            flow[caller] = receiver.states(nodes, caller)
        key=caller,expression(row['receiver_expression'])
        if key not in lifetime:
            lifetime[key] = lifetimes(nodes, caller, flow[caller], receiver,key[1])
        local = original_lifetime(row, nodes, flow[caller], lifetime[key], receiver)
        # These are original lifetime witnesses, not native/source complete
        # domains. Never copy caller_receiver_contexts into receiver_domain.
        row['entry_receiver_obligation'] = dict(packet_sha256=binding['sha256'],
            original_lifetime=local,
            original_ingress_count=len(ingress[caller]),
            caller_owned=caller in inventory,
            native_pairing_complete=False, source_pairing_complete=False,
            complete=False,
            missing=['complete-native-and-original-function-receiver-pairing',
                     'source-bound-constructor-lifetime-effects',
                     'emitted-indirect-call-operands-and-production-transport'])
        if caller in paired_functions:
            row['entry_receiver_obligation']['entry_adapter_binding']=paired_functions[caller]
        selected_rows.append(row)
    operands=emitted_operands(root,graph,owners,selected_rows,receiver,shape_type,digest)
    for row in selected_rows:
        row['entry_receiver_obligation']['emitted_operands']=operands[row['caller'],row['site']]
    probes=conditional_probes(graph,selected_rows,receiver,binary,election,inventory)
    native = native_invocations(root, digest, selected_callers)
    references=pointer_ingress(graph,node_map,flow,selected_callers,receiver)
    for row in selected_rows:
        row['entry_receiver_obligation']['original_pointer_reference_count']=len(references.get(str(row['caller']),[]))
    all_ingress = [r for group in ingress.values() for r in group]
    return dict(packet=binding, sites=len(selected_rows), callers=len(selected_callers),
        legacy_entry_pairings=dict(path='work/call-closure/entry-legacy-pairings.json',
            bound_functions=pairings['bound_functions'],bound_ingress=pairings['bound_ingress'],
            completion_obligation_met=pairings['completion_obligation_met']),
        proved_sites=sum(r['status']=='target-set-proved' for r in selected_rows),
        completion_obligation_met=all(r['status']=='target-set-proved' and
            r['entry_receiver_obligation']['complete'] for r in selected_rows),
        original_ingress={str(k):v for k,v in sorted(ingress.items())},
        original_pointer_references=references,
        ingress_origins=dict(Counter(r['receiver_origin'] for r in all_ingress)),
        ingress_source_statuses=dict(Counter(r['source_binding']['status'] for r in all_ingress)),
        callers_without_admitted_owner=sorted(selected_callers-inventory.keys()),
        native_invocations=native,
        emitted_operand_statuses=dict(Counter(v['status'] for v in operands.values())),
        conditional_site_transport=probes,
        original_local_domains=sum(r['entry_receiver_obligation']['original_lifetime']['original_local_domain_complete'] for r in selected_rows),
        original_operand_current_matches=sum(r['entry_receiver_obligation']['original_lifetime']['operand_matches_current_receiver'] for r in selected_rows),
        contract='The fixed entry packet is preserved exactly. Original ingress and vptr lifetimes are witnesses, not complete native receiver domains; candidate contexts and callee-ABI fixtures cannot discharge these obligations.')


def self_test(decoder, receiver):
    examples = [
        ('entry-domain-stays-open', '8b01ff5004c3', [], False, False),
        ('local-install', 'c701002000008b01ff5004c3', [0x2000], True, True),
        ('field-store-preserves-vptr', 'c70100200000c74104070000008b01ff5004c3', [0x2000], True, True),
        ('base-call-invalidates-lifetime', '89cec70100200000e80000000089f18b01ff5004c3', [], False, False),
        ('post-base-install-restores-lifetime', '89cee80000000089f1c701002000008b01ff5004c3', [0x2000], True, True),
        ('aliased-store-invalidates-lifetime', 'c70100200000c702030000008b01ff5004c3', [], False, False),
        ('partial-vptr-write-invalidates', 'c70100200000c64103008b01ff5004c3', [], False, False),
        ('wrapped-store-overlaps-vptr', 'c7010020000089ca81c2ffffffffc702030000008b01ff5004c3', [], False, False),
        ('stack-alias-not-assumed-disjoint', 'c70100200000528b01ff5004c3', [], False, False),
        ('stale-table-load-receiver-mismatch', 'c701002000008b01c70100300000ff5004c3', [0x2000], True, False),
        ('rewritten-vptr-requires-path-witness', 'c701002000008b01c70100200000ff5004c3', [0x2000], True, False),
        ('changed-table-reloaded', 'c701002000008b01c701003000008b01ff5004c3', [0x3000], True, True),
        ('branch-table-union', '85d27408c70100200000eb06c701003000008b01ff5004c3', [0x2000,0x3000], True, True),
        ('branch-with-unbound-entry', '85d27406c701002000008b01ff5004c3', [0x2000], False, False),
        ('loop-reinstalls-table', 'c701002000008b01ff5004ebf4', [0x2000], True, True),
        ('interior-subobject-own-install', 'c741100020000083c1108b01ff5004c3', [0x2000], True, True),
        ('root-install-does-not-type-subobject', 'c7010020000083c1108b01ff5004c3', [], False, False),
    ]
    results = []
    for name, raw, tables, complete, current in examples:
        nodes = {i.address:i for i in decoder.disasm(bytes.fromhex(raw),0x1000)}
        flow = receiver.states(nodes,0x1000)
        calls = [i for i in nodes.values() if i.group(CS_GRP_CALL) and i.operands[0].type != X86_OP_IMM]
        if len(calls)!=1:
            raise ValueError(f'Bad entry lifetime fixture {name}')
        ins=calls[0]
        shape=receiver.classify(ins,flow[ins.address],{})
        object_expression=shape.get('receiver_expression')
        if receiver.origin(object_expression)!='entry-ecx':
            raise ValueError(f'Entry lifetime fixture lost receiver: {name}')
        row=dict(caller=0x1000,site=ins.address,receiver_expression=object_expression)
        result=original_lifetime(row,nodes,flow,lifetimes(nodes,0x1000,flow,receiver,object_expression),receiver)
        if (result['possible_local_tables']!=tables or result['original_local_domain_complete']!=complete or
                result['operand_matches_current_receiver']!=current):
            raise ValueError(f'Entry lifetime regression {name}: {result}')
        results.append(dict(name=name,status='pass'))
    return results


def invalidation_tests(root, graph, indirect, digest):
    path=root/'work/call-closure/receiver-entry-sites.json'
    original=json.loads(path.read_text())
    mutations=[]
    for name in ('profile','original_sha256'):
        data=json.loads(json.dumps(original));data[name]='changed';mutations.append((name,data,indirect))
    for name in ('drop','duplicate','slot','sha256','receiver_expression'):
        data=json.loads(json.dumps(original))
        if name=='drop':data['sites'].pop()
        elif name=='duplicate':data['sites'][-1]=data['sites'][0]
        elif name=='slot':data['sites'][0]['slot']+=4
        elif name=='sha256':data['sites'][0]['sha256']='changed'
        else:data['sites'][0]['receiver_expression']=['entry','edx']
        mutations.append((name,data,indirect))
    key=original['sites'][0]['caller'],original['sites'][0]['site']
    mutations.append(('missing-indirect-site',original,
        [r for r in indirect if (r['caller'],r['site'])!=key]))
    results=[]
    for name,data,rows in mutations:
        try:packet(root,graph,rows,digest,data)
        except ValueError:results.append(dict(name=name,status='rejected'))
        else:raise ValueError(f'Invalid entry packet accepted: {name}')
    return results


def source_expression(text, prefix, receiver, seen=()):
    """Restricted structural operand reader; aliases remain source witnesses.

    This does not establish dominance or the memory epoch of a cached load.
    It is used to find candidate emitted calls, never to close a domain.
    """
    from call_closure_shapes import close, integer
    text=text.strip()
    while text.startswith('(') and close(text,0)==len(text)-1:
        text=text[1:-1].strip()
    if text=='receiver':
        if re.search(r'(?<![\w.])receiver\s*(?:=(?!=)|[+*/%&|^-]=|\+\+|--)',prefix):return None
        return ('entry','ecx')
    value=integer(text)
    if value is not None:return ('constant',value)
    if re.fullmatch(r'\w+',text):
        if text in seen:return None
        matches=list(re.finditer(r'(?<![\w.>])\b'+re.escape(text)+r'\s*=(?!=)\s*([^;]+);',prefix))
        if len(matches)!=1 or re.search(r'\b'+re.escape(text)+r'\s*(?:[+*/%&|^-]=|\+\+|--)|(?:\+\+|--)\s*\b'+re.escape(text)+r'\b',prefix):return None
        match=matches[0]
        return source_expression(match[1],prefix[:match.start()],receiver,seen+(text,))
    op=re.match(r'(?:run\.)?get\s*\(',text)
    if op and close(text,op.end()-1)==len(text)-1:
        inner=source_expression(text[op.end():-1],prefix,receiver,seen)
        return ('load',inner) if inner is not None else None
    depth=0
    for index,char in enumerate(text):
        depth+=(char in '([{')-(char in ')]}')
        if char in '+-' and index and depth==0:
            left=source_expression(text[:index],prefix,receiver,seen)
            right=integer(text[index+1:])
            if left is not None and right is not None:
                return receiver.add(left,right if char=='+' else -right)
    return None


def emitted_operands(root, graph, owners, selected, receiver, shape_type, digest):
    """Retain structural source candidates without guessing a target's ABI."""
    readers={};by_caller=defaultdict(list);virtual_helper=runtime_virtual_helper(root,digest)
    for row in selected:by_caller[row['caller']].append(row)
    result={}
    for caller,sites in by_caller.items():
        declared=owners.get((graph.program.name,caller))
        if not declared:
            for row in sites:result[caller,row['site']]=dict(status='caller-owner-unresolved',candidates=[])
            continue
        manifest,owned=declared;family=manifest['id']
        if family not in readers:readers[family]=shape_type(root,manifest,import_slots=graph.program.imports,include_virtual=True)
        reader=readers[family]
        candidates=[]
        for leaf in reader.entry_calls(caller,bool(owned.get('source_context') or owned.get('compiler_context'))):
            if leaf['api'] not in ('call','source_call','source_tail','vcall'):continue
            args=leaf['args']
            if len(args)<2:continue
            if leaf['api']=='vcall':
                receiver_expr=source_expression(args[0],leaf['prefix'],receiver)
                from call_closure_shapes import integer
                slot=integer(args[1])
                if receiver_expr is None or slot is None or slot<0 or slot%4:continue
                target_expr=('load',receiver.add(('load',receiver_expr),slot))
                adapted=dict(leaf,api='call',args=['<virtual-slot>',args[0],args[2] if len(args)>2 else '{}'])
                shape=reader.shape(adapted,owned) if virtual_helper else None
            else:
                target_expr=source_expression(args[0],leaf['prefix'],receiver)
                receiver_expr=source_expression(args[1],leaf['prefix'],receiver)
                shape=reader.shape(leaf,owned)
            if target_expr is None or receiver_expr is None:continue
            witness={k:leaf[k] for k in ('path','line','helper','chain','api','args')}
            witness.update(source_sha256=hashlib.sha256(reader.files[leaf['path']].encode()).hexdigest(),prefix_sha256=hashlib.sha256(leaf['prefix'].encode()).hexdigest(),
                           target_expression=target_expr,receiver_expression=receiver_expr,shape=shape)
            if leaf['api']=='vcall':witness['virtual_helper']=virtual_helper
            candidates.append(witness)
        for row in sites:
            matched=[]
            for candidate in candidates:
                original_target=receiver.semantic(row['expression'])
                if candidate['target_expression']!=original_target or candidate['receiver_expression']!=expression(row['receiver_expression']):continue
                if candidate['api']=='source_call' and (not candidate['shape'] or candidate['shape'].get('return_pc')!=row['site']+row['size']):continue
                if candidate['api']=='source_tail' and (not candidate['shape'] or candidate['shape'].get('transfer_site')!=row['site']):continue
                matched.append(candidate)
            result[caller,row['site']]=dict(status='structural-operand-candidates' if matched else 'call-shape-unresolved',
                candidates=matched,complete=False,
                contract='Matching receiver and target expressions only. Source control flow, cached-load lifetime and site correspondence remain unproved; vcall helpers require their own source binding.')
    return result


def runtime_virtual_helper(root, digest, source=None):
    from call_closure_shapes import close
    path=root/'Sources/ClawRuntime.hpp';text=path.read_text() if source is None else source
    signature='uint32_t vcall(uint32_t object, uint32_t slotOffset, std::initializer_list<uint32_t> arguments = {})'
    if text.count(signature)!=1:return None
    at=text.index(signature);start=text.index('{',at+len(signature));end=close(text,start,'{','}')
    body=text[start+1:end]
    if re.sub(r'\s+','',body)!='returndispatch(get(get(object)+slotOffset),object,0,arguments);':return None
    return dict(path=str(path.relative_to(root)),sha256=hashlib.sha256(text.encode()).hexdigest(),line=text[:at].count('\n')+1,
        body_sha256=hashlib.sha256(body.encode()).hexdigest(),
        contract='Actual Run::vcall emits dispatch of the loaded slot with the same object, zero second receiver, and its explicit initializer list.')


def conditional_probes(graph, rows, receiver, binary, election, inventory):
    """Probe source operand candidates, never fill operands from a target ABI."""
    queries=[];destinations=[]
    tail_only=[int(x,16) for x in election['tail_only']]
    thunks={str(int(k,16)):int(v,16) for k,v in election['tail_thunks'].items()}
    for row in rows:
        obligation=row['entry_receiver_obligation']
        obligation['conditional_shape_probes']=[]
        # A primary class table is not the table of an interior subobject.
        # Do not borrow root contexts for the eighteen adjusted receivers.
        if expression(row['receiver_expression'])!=('entry','ecx'):continue
        for candidate in obligation['emitted_operands']['candidates']:
            shape=candidate['shape']
            if shape is None:continue
            for table in row['caller_receiver_contexts']:
                target=graph.word(table+row['slot'])
                words=receiver.receiver_words(graph,table)
                if str(table+row['slot']) not in words or target is None or not graph.program.in_text(target):continue
                query=dict(shape,caller=row['caller'],site=row['site'],target=target,table=table,
                    words=words,tail_only=tail_only,tail_thunks=thunks,
                    original_direct_calls={str(int(k,16)):[int(v,16) for v in values]
                        for k,values in election['original_direct_calls'].items()})
                queries.append(query);destinations.append((obligation,candidate))
    if binary is None:return dict(status='not-run',queries=len(queries),complete=False)
    answers=json.loads(subprocess.run([str(binary)],input=json.dumps(queries),text=True,capture_output=True,
        env={**os.environ,'CLAW_GAME_VERSION':'1.0'},check=True).stdout) if queries else []
    if len(answers)!=len(queries):raise ValueError('Entry receiver production probe lost a request')
    for query,answer,(obligation,candidate) in zip(queries,answers,destinations):
        obligation['conditional_shape_probes'].append(dict(request=query,answer=answer,
            target_owned=query['target'] in inventory,
            transport_status=('owner-unresolved' if query['target'] not in inventory else
                'refused' if answer['outcome']=='refused' else 'conditional-shape-accepted'),
            source={k:candidate[k] for k in ('path','line','source_sha256','api','args')},
            receiver_domain_proved=False,site_correspondence_proved=False,
            contract='Actual emitted operand candidate through extracted production levelTransport with a candidate-context receiver fixture. The nonexecuting ordinary destination models canonical ownership only; an unowned target still needs its real gameEntry/provider route. Acceptance does not prove the receiver domain or original/source site correspondence.'))
    return dict(status='measured',queries=len(queries),sites=sum(bool(r['entry_receiver_obligation']['conditional_shape_probes']) for r in rows),
        outcomes=dict(Counter(a['outcome'] for a in answers)),complete=False)


def operand_tests(root, digest, receiver):
    tests=[
        ('literal-entry-slot','run.get(run.get(receiver) + 0x28)','',('load',('add',('load',('entry','ecx')),40))),
        ('cached-slot-alias','method','uint32_t method = run.get(run.get(receiver) + 0x28);',('load',('add',('load',('entry','ecx')),40))),
        ('subobject-slot','run.get(run.get(container) + 4)','uint32_t container = receiver + 0x154;',('load',('add',('load',('add',('entry','ecx'),340)),4))),
        ('foreign-receiver','run.get(run.get(other) + 4)','',None),
        ('changed-target-alias','method','uint32_t method = run.get(run.get(receiver) + 4); method = 7;',None),
        ('incremented-target-alias','method','uint32_t method = run.get(run.get(receiver) + 4); ++method;',None),
        ('changed-entry-parameter','run.get(run.get(receiver)+4)','receiver = other;',None),
        ('callback-field-is-not-vptr','run.get(receiver + 0x18)','',('load',('add',('entry','ecx'),24))),
    ]
    out=[]
    for name,text,prefix,expected in tests:
        found=source_expression(text,prefix,receiver)
        if found!=expected:raise ValueError(f'Entry emitted operand regression {name}: {found}')
        out.append(dict(name=name,status='pass'))
    source=(root/'Sources/ClawRuntime.hpp').read_text()
    if runtime_virtual_helper(root,digest) is None:raise ValueError('Production virtual helper requires review')
    old='return dispatch(get(get(object) + slotOffset), object, 0, arguments);'
    mutations={
        'different-dispatch-receiver':source.replace(old,'return dispatch(get(get(object) + slotOffset), 0, 0, arguments);'),
        'different-vtable-slot':source.replace(old,'return dispatch(get(get(object) + 4), object, 0, arguments);'),
        'lost-emitted-arguments':source.replace(old,'return dispatch(get(get(object) + slotOffset), object, 0, {});'),
        'missing-virtual-helper':source.replace('uint32_t vcall(', 'uint32_t removedVirtual('),
    }
    for name,changed in mutations.items():
        if changed==source or runtime_virtual_helper(root,digest,changed) is not None:
            raise ValueError(f'Changed production virtual helper accepted: {name}')
        out.append(dict(name=name,status='rejected'))
    return out


def pointer_ingress(graph, node_map, flow, selected_callers, receiver):
    """Address escapes into selected entries are ingress obligations too.

    A state callback installed in an object field can enter an ordinary member
    that occurs in no vtable at all. These references are retained as witnesses;
    unrelated callback/field sites remain open on the parent audit.
    """
    references=defaultdict(list)
    for caller,nodes in node_map.items():
        for ins in nodes.values():
            if ins.group(CS_GRP_CALL) or ins.mnemonic.startswith('j'):continue
            targets={op.imm & 0xffffffff for op in ins.operands if op.type==X86_OP_IMM}
            for target in targets & selected_callers:
                row=dict(receiver.witness(ins),caller=caller,target=target,
                    kind='original-code-pointer-reference',status='function-receiver-pairing-unresolved')
                if ins.operands and ins.operands[0].type==X86_OP_MEM and ins.operands[0].access & CS_AC_WRITE:
                    if caller not in flow:flow[caller]=receiver.states(nodes,caller)
                    row['destination_expression']=receiver.address(ins,ins.operands[0].mem,flow[caller].get(ins.address,{}))
                references[target].append(row)
    for section in graph.program.sections:
        if section.name not in ('.data','.rdata'):continue
        for offset in range(0,len(section.data)-3,4):
            target=int.from_bytes(section.data[offset:offset+4],'little')
            if target not in selected_callers:continue
            at=section.address+offset
            references[target].append(dict(site=at,target=target,section=section.name,size=4,
                sha256=hashlib.sha256(section.data[offset:offset+4]).hexdigest(),
                kind='original-data-pointer-reference',status='function-receiver-pairing-unresolved'))
    return {str(k):v for k,v in sorted(references.items())}
