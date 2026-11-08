"""Receiver witnesses and indirect operand provenance for the closure audit.

This is a may-analysis. Registration is permission to construct a class, not a
claim that a particular playthrough constructed it. Unknowns never prove absence
and a bounded target set never proves a translated caller's ABI or execution.
Original address/byte and class inventories are written only to ignored work/.
"""
from collections import Counter, defaultdict, deque
import hashlib
import json
import os
import re
import subprocess
import sys
import call_closure_entry_receivers
from call_closure_shapes import SourceShapes
from capstone import CS_GRP_CALL, CS_GRP_JUMP, CS_GRP_RET, CS_AC_WRITE
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG


def witness(ins):
    return dict(site=ins.address,size=ins.size,sha256=hashlib.sha256(ins.bytes).hexdigest())


def instructions(graph, root):
    """Use the graph's exact block boundaries; do not linear-sweep across data."""
    pending=[root]; seen={}
    while pending:
        pc=pending.pop()
        while pc not in seen and graph.program.in_text(pc):
            ins=next(graph.decoder.disasm(graph.bytes(pc,15),pc,count=1),None)
            if ins is None:break
            seen[pc]=ins;after=pc+ins.size
            if ins.group(CS_GRP_RET) or ins.mnemonic in ('int3','hlt','ud2'):break
            if ins.group(CS_GRP_JUMP):
                op=ins.operands[0]
                if op.type==X86_OP_IMM and not (ins.mnemonic=='jmp' and op.imm in graph.roots):
                    pending.append(op.imm & 0xffffffff)
                if ins.mnemonic=='jmp':break
            pc=after
    return seen


def successors(ins, nodes):
    after=ins.address+ins.size
    if ins.group(CS_GRP_RET) or ins.mnemonic in ('int3','hlt','ud2'):return []
    result=[]
    if ins.group(CS_GRP_JUMP):
        op=ins.operands[0]
        if op.type==X86_OP_IMM and op.imm in nodes:result.append(op.imm)
        if ins.mnemonic=='jmp':return result
    if after in nodes:result.append(after)
    return result


# Finite, structural expressions. None is top; equality is identity only within
# one function and survives a join only if every predecessor agrees. Expressions
# identify loads, never assume that a numeric displacement denotes a vtable.
def add(value, offset):
    if value is None:return None
    if not offset:return value
    if value[0]=='constant':return ('constant',(value[1]+offset)&0xffffffff)
    if value[0]=='add':return add(value[1],value[2]+offset)
    return ('add',value,offset)


def load(address, epoch=None):
    if address is None or len(repr(address))>240:return None
    return ('load',address,epoch)


def address(ins, mem, state):
    if mem.segment:return None
    result=state.get(ins.reg_name(mem.base)) if mem.base else ('constant',0)
    if mem.index:
        index=state.get(ins.reg_name(mem.index))
        if index is None:return None
        if result==('constant',0) and mem.scale==1:result=index
        else:return ('indexed',result,index,mem.scale,mem.disp)
    return add(result,mem.disp)


def operand(ins, op, state):
    if op.type==X86_OP_IMM:return ('constant',op.imm&0xffffffff)
    if op.type==X86_OP_REG:return state.get(ins.reg_name(op.reg))
    if op.type==X86_OP_MEM:return load(address(ins,op.mem,state),state.get('memory',('unknown-memory',ins.address))) or ('unknown-load',ins.address)
    return None


def transfer(ins, state):
    out=dict(state);ops=ins.operands
    # Calls preserve the nonvolatile registers. Their result and volatile
    # registers have fresh, site-specific identities; prior loads cannot leak.
    if ins.group(CS_GRP_CALL):
        for reg in ('eax','ecx','edx'):out[reg]=('call-result',ins.address,reg)
        out['esp']=('after-call-stack',ins.address)
        out['memory']=('after-call',ins.address)
        return out
    try:written=ins.regs_access()[1]
    except Exception:written=[]
    for reg in written:
        name=ins.reg_name(reg)
        if name not in ('eflags','eip'):
            aliases={'al':'eax','ah':'eax','ax':'eax','bl':'ebx','bh':'ebx','bx':'ebx','cl':'ecx','ch':'ecx','cx':'ecx','dl':'edx','dh':'edx','dx':'edx','si':'esi','di':'edi','bp':'ebp','sp':'esp'}
            out[aliases.get(name,name)]=('written',ins.address,name)
    if ops and ops[0].type==X86_OP_REG:
        dest=ins.reg_name(ops[0].reg)
        if ins.mnemonic=='mov' and len(ops)==2 and ops[0].size==4:
            out[dest]=operand(ins,ops[1],state)
        elif ins.mnemonic=='lea' and ops[1].type==X86_OP_MEM:
            out[dest]=address(ins,ops[1].mem,state)
        elif ins.mnemonic in ('add','sub') and ops[1].type==X86_OP_IMM:
            out[dest]=add(state.get(dest),ops[1].imm*(1 if ins.mnemonic=='add' else -1))
        elif ins.mnemonic=='xor' and ops[1].type==X86_OP_REG and ops[0].reg==ops[1].reg:
            out[dest]=('constant',0)
    memory_write=any(op.type==X86_OP_MEM and op.access & CS_AC_WRITE for op in ops)
    memory_write|=ins.mnemonic.startswith(('push','rep ','stos','movs','ins'))
    if memory_write:
        out['memory']=('after-write',ins.address)
    # Stack loads have structural identities only while the stack offset is
    # known. Pop reads the pre-increment location, push decrements it.
    if ins.mnemonic=='push':out['esp']=add(state.get('esp'),-4)
    if ins.mnemonic=='pop':
        if ops[0].type==X86_OP_REG:out[ins.reg_name(ops[0].reg)]=load(state.get('esp'),state.get('memory',('unknown-memory',ins.address)))
        out['esp']=add(state.get('esp'),4)
    return out


def states(nodes, root):
    entry={r:('entry',r) for r in ('eax','ebx','ecx','edx','esi','edi','ebp','esp')}
    entry['memory']=('entry-memory',root)
    incoming={root:entry};todo=deque([root]);outputs={}
    parents=defaultdict(set)
    for pc,ins in nodes.items():
        for nxt in successors(ins,nodes):parents[nxt].add(pc)
    steps=0
    while todo:
        steps+=1
        if steps>max(1000,len(nodes)*50):raise ValueError(f'Receiver dataflow did not converge at {root:#x}')
        pc=todo.popleft();out=transfer(nodes[pc],incoming[pc]);outputs[pc]=out
        for nxt in successors(nodes[pc],nodes):
            paths=[outputs[p] for p in parents[nxt] if p in outputs]
            if nxt==root:paths.append(entry)
            keys=set().union(*(p.keys() for p in paths))
            new={}
            for key in keys:
                values=[p.get(key) for p in paths]
                phi=('phi',nxt,key)
                previous=incoming.get(nxt,{}).get(key)
                new[key]=phi if previous==phi or not all(v==values[0] for v in values) else values[0]
            if nxt not in incoming or new!=incoming[nxt]:
                incoming[nxt]=new;todo.append(nxt)
    return incoming


def split_offset(expr):
    return (expr[1],expr[2]) if expr and expr[0]=='add' else (expr,0)


def classify(ins, state, imports):
    expr=operand(ins,ins.operands[0],state)
    proof=dict(witness(ins),expression=expr)
    if expr and expr[0]=='load':
        base,slot=split_offset(expr[1])
        if base and base[0]=='constant' and base[1]+slot in imports:
            return dict(proof,indirect_kind='import-pointer',target=base[1]+slot,status='target-set-proved')
        # call [[receiver]+slot], with that exact receiver in ECX. A mere
        # call [reg+offset] is insufficient: it can be a callback record.
        if base and base[0]=='load' and base[1]==state.get('ecx') and slot>=0 and slot%4==0:
            return dict(proof,indirect_kind='vtable-slot',slot=slot,receiver_expression=base[1],status='receiver-domain-unresolved')
        if base and base[0]=='indexed':
            return dict(proof,indirect_kind='function-pointer-table',status='target-domain-unresolved')
        if base and base[0]=='constant':
            return dict(proof,indirect_kind='global-function-pointer',pointer=base[1]+slot,status='target-domain-unresolved')
    if expr and expr[0]=='constant':
        return dict(proof,indirect_kind='constant-function-pointer',target=expr[1],status='target-set-proved')
    return dict(proof,indirect_kind='callback-or-unproved-table',status='operand-provenance-unresolved')


def registrations(graph, nodes):
    """Only accept the original registrar's constant, three-push records."""
    rows=[];pushes=[]
    for pc,ins in sorted(nodes.items()):
        if ins.mnemonic=='push':
            pushes.append(ins.operands[0].imm&0xffffffff if ins.operands[0].type==X86_OP_IMM else None)
        if ins.group(CS_GRP_CALL):
            if ins.operands[0].type==X86_OP_MEM and ins.operands[0].mem.disp==0x24 and len(pushes)>=3:
                flags,name,callback=pushes[-3:]
                if flags is not None and name is not None and callback is not None and graph.program.in_text(callback):
                    raw=graph.bytes(name,256).split(b'\0',1)[0]
                    if raw and all(32<=c<127 for c in raw):
                        rows.append(dict(name=raw.decode('ascii'),callback=callback,flags=flags,name_address=name,call=witness(ins)))
            pushes=[]
    return rows


def constructor_closure(graph, node_map, registrations):
    # This is a conservative reachable-function closure. Indirect calls are
    # explicitly not treated as an absence proof for any remaining table.
    children=defaultdict(set)
    for edge in graph.edges:
        if graph.program.in_text(edge['target']):children[edge['caller']].add(edge['target'])
    # A constructed class can dispatch any of its original virtual slots. This
    # adds possible destructor/state reachability, rather than mistaking the
    # lack of an immediate caller for proof that a base table is never live.
    for caller,nodes in node_map.items():
        for ins in nodes.values():
            ops=ins.operands
            if ins.mnemonic!='mov' or len(ops)!=2 or ops[0].type!=X86_OP_MEM or ops[1].type!=X86_OP_IMM:continue
            value=ops[1].imm&0xffffffff
            for table,words in graph.tables.items():
                if table<=value<table+4*len(words) and (value-table)%4==0:
                    children[caller].update(words[(value-table)//4:])
    result=defaultdict(list)
    for row in registrations:
        todo=[row['callback']];seen=set()
        while todo:
            root=todo.pop()
            if root in seen:continue
            seen.add(root);todo.extend(children[root]-seen)
        for root in seen:result[root].append(row['name'])
    return result


def receiver_contexts(graph, tables, node_map, flow):
    """Candidate entry contexts, not a complete per-site receiver domain."""
    contexts=defaultdict(set);same_receiver=[]
    for table in tables:
        if not table['installations']:continue
        at=table['table']
        for i in range(table['slots']):contexts[graph.word(at+i*4)].add(at)
        for w in table['installations']:
            if w['destination_expression']==('entry','ecx'):contexts[w['caller']].add(at)
    for edge in graph.edges:
        caller=edge['caller'];nodes=node_map.get(caller)
        if not nodes or edge['site'] not in nodes or not edge.get('immediate'):continue
        ins=nodes[edge['site']]
        if not ins.group(CS_GRP_CALL):continue
        if caller not in flow:flow[caller]=states(nodes,caller)
        if flow[caller].get(edge['site'],{}).get('ecx')==('entry','ecx'):
            same_receiver.append(dict(witness(ins),caller=caller,target=edge['target']))
    changed=True
    while changed:
        changed=False
        for edge in same_receiver:
            before=len(contexts[edge['target']])
            contexts[edge['target']].update(contexts[edge['caller']])
            changed|=len(contexts[edge['target']])!=before
    return {f:sorted(v) for f,v in contexts.items() if v},same_receiver


def origin(expr):
    expr=semantic(expr)
    if expr is None:return 'unknown'
    if expr[0]=='entry':return 'entry-'+expr[1]
    if expr[0]=='constant':return 'constant'
    if expr[0]=='call-result':return 'call-result'
    if expr[0]=='phi':return 'control-flow-join'
    if expr[0]=='add':return origin(expr[1])
    if expr[0]=='load':return 'field-of-'+origin(expr[1])
    return 'computed'


def receiver_tables(proof, graph, caller):
    result=[]
    for table in proof['tables']:
        at=table['table'];words=[graph.word(at+i*4) for i in range(table['slots'])]
        primary_constructor=any(w['caller']==caller and w['destination_expression']==('entry','ecx')
            for w in table['installations'])
        if caller in words or primary_constructor:result.append((at,words))
    return result


def semantic(expr):
    if not isinstance(expr,tuple):return expr
    if expr and expr[0]=='load':return ('load',semantic(expr[1]))
    return tuple(semantic(x) for x in expr)


def receiver_words(graph, table):
    # Match the production heap: its mapped read-only image includes adjoining
    # RTTI and other tables. Slicing at a declared table boundary would hide
    # over-reads by the router's 64-word membership search.
    result={}
    for i in range(64):
        address=table+i*4
        for at,raw in graph.receiver_metadata_spans.items():
            if at<=address and address+4<=at+len(raw):
                result[str(address)]=int.from_bytes(raw[address-at:address-at+4],'little');break
    return result


def metadata_tables(root, graph, digest, spans=None):
    path=root/'App/GameData/MENU/level-one-data.json'
    if spans is None:spans={int(k,16):bytes(v) for k,v in json.loads(path.read_text()).items()}
    mapped={}
    for section in graph.program.sections:
        if section.name!='.rdata':continue
        for at,raw in spans.items():
            lo=max(at,section.address);hi=min(at+len(raw),section.address+len(section.data))
            if lo<hi and raw[lo-at:hi-at]!=graph.bytes(lo,hi-lo):
                raise ValueError('Native read-only metadata differs from original')
    for at,raw in spans.items():
        for table,words in graph.tables.items():
            size=len(words)*4
            if at<=table and table+size<=at+len(raw):
                original=graph.bytes(table,size);actual=raw[table-at:table-at+size]
                if original!=actual:raise ValueError(f'Native vtable metadata differs from original at {table:#x}')
                mapped[table]=dict(span=at,bytes=size,sha256=hashlib.sha256(actual).hexdigest())
    graph.receiver_metadata_spans=spans
    return dict(path=str(path.relative_to(root)),sha256=digest(path),tables=mapped)


def native_registration(root, digest, source=None):
    path=root/'Sources/ClawNativeMenuInterface.swift'
    if source is None:source=path.read_text()
    invocation='_ = resources.invoke(0x401000,0,[base.sceneToken])'
    if source.count(invocation)!=1:
        raise ValueError('Native complete class registration requires review')
    fragments=['(20,0x513b60,0x4cf940,false)', 'put(token,table);put(base.sceneToken+offset,token)']
    if any(source.count(fragment)!=1 for fragment in fragments):
        raise ValueError('Native registrar receiver installation requires review')
    if any(source.index(fragment)>source.index(invocation) for fragment in fragments):
        raise ValueError('Native registrar receiver is installed after registration')
    return dict(path=str(path.relative_to(root)),sha256=digest(path),registrar_table=0x513b60,
        line=source[:source.index(invocation)].count('\n')+1,
        contract='Native startup invokes the complete original registrar. This proves registration availability, not runtime construction of every class.')


def native_table_writes(root, graph, digest):
    # Native CRT/MFC constructors replace original bodies, so their explicit
    # table stores are separate source witnesses. A store alone does not prove
    # activation/reachability; that obligation remains in the table status.
    path=root/'Sources/ClawNativeMenuInterface.swift';source=path.read_text();result=defaultdict(list)
    for match in re.finditer(r'\bput\(([^,;\n]+),([^;\n]+?)\)',source):
        destination,value=match.groups()
        choices=re.findall(r'(?:^|[?:])\s*(0x[0-9a-f]+)\s*(?=[:]|$)',value)
        for choice in choices:
            table=int(choice,16)
            if not any(at<=table<at+4*len(words) and (table-at)%4==0 for at,words in graph.tables.items()):continue
            result[table].append(dict(caller=0,origin='native-source-store',activation='unproved',
                source_path=str(path.relative_to(root)),source_sha256=digest(path),
                source_line=source[:match.start()].count('\n')+1,
                destination=destination,destination_expression=None,registered_classes=[]))
    return result


def table_type(graph, table):
    locator=graph.word(table-4)
    if locator is None or graph.word(locator)!=0:return None
    descriptor=graph.word(locator+12)
    if descriptor is None:return None
    raw=graph.bytes(descriptor+8,256).split(b'\0',1)[0]
    if not raw.startswith((b'.?AV',b'.?AU')) or not raw.endswith(b'@@'):return None
    return dict(locator=locator,descriptor=descriptor,decorated_name=raw.decode('ascii'),
        subobject_offset=graph.word(locator+4))


def tail_probes(graph, tables, binary, election, inventory):
    queries=[];witnesses=[]
    only={int(x,16) for x in election['tail_only']}
    thunks={str(int(k,16)):int(v,16) for k,v in election['tail_thunks'].items()}
    for caller_text,slot in thunks.items():
        caller=int(caller_text);nodes=instructions(graph,caller);flow=states(nodes,caller)
        sites=[i for i in nodes.values() if i.mnemonic=='jmp' and i.operands[0].type!=X86_OP_IMM]
        if len(sites)!=1:raise ValueError('Tail thunk branch requires review')
        ins=sites[0];shape=classify(ins,flow[ins.address],graph.program.imports)
        if shape.get('slot')!=slot or shape['indirect_kind']!='vtable-slot':
            raise ValueError('Tail thunk receiver provenance changed')
        for table in tables:
            if table['slots']*4<=slot:continue
            at=table['table'];target=graph.word(at+slot)
            if target not in only or target not in inventory:continue
            words=receiver_words(graph,at)
            query=dict(caller=caller,site=ins.address,target=target,argc=0,receiver=0x61000000,table=at,
                words=words,tail_only=sorted(only),tail_thunks=thunks)
            bad=dict(query,words=dict(words,**{str(at+slot):0}))
            missing_receiver=dict(query,receiver=0)
            wrong_receiver_table=dict(query,words=dict(words,**{str(query['receiver']):0}))
            second_receiver=dict(query,receiver2=0x62000000)
            queries.extend([query,bad,missing_receiver,wrong_receiver_table,second_receiver])
            witnesses.extend([witness(ins)]*5)
    if binary is None:return []
    answers=json.loads(subprocess.run([str(binary)],input=json.dumps(queries),text=True,capture_output=True,
        env={**os.environ,'CLAW_GAME_VERSION':'1.0'},check=True).stdout)
    for i,answer in enumerate(answers):
        if i%5==0:
            if answer['outcome']!='transport-only' or answer['route']!='tail-only':
                raise ValueError(f'Original tail thunk contract refused: {answer}')
        elif answer['outcome']!='refused':
            raise ValueError(f'Wrong thunk slot or receiver accepted (variant {i%5}, caller {queries[i]["caller"]:#x}): {answer}')
    covered={q['caller'] for q in queries}
    if covered!={int(k) for k in thunks}:raise ValueError('An elected tail thunk has no receiver probe')
    return [dict(request=q,answer=a,original=w) for q,a,w in zip(queries,answers,witnesses)]


def audit(root, graph, inventory, owners, binary, election, digest):
    node_map={f:instructions(graph,f) for f in graph.visited if 0x401000<=f<0x4f0000}
    if 0x401000 not in node_map:node_map[0x401000]=instructions(graph,0x401000)
    registration_witness=native_registration(root,digest)
    metadata=metadata_tables(root,graph,digest)
    registered=registrations(graph,node_map[0x401000])
    construction=constructor_closure(graph,node_map,registered)
    # Table writes must be reachable instructions in the current graph, not
    # accidental immediates decoded by a linear sweep through text data.
    installations=defaultdict(list);flow={}
    for caller,nodes in node_map.items():
        for ins in nodes.values():
            ops=ins.operands
            if ins.mnemonic!='mov' or len(ops)!=2 or ops[0].type!=X86_OP_MEM or ops[1].type!=X86_OP_IMM:continue
            value=ops[1].imm&0xffffffff
            for table,words in graph.tables.items():
                if table<=value<table+4*len(words) and (value-table)%4==0:
                    if caller not in flow:flow[caller]=states(nodes,caller)
                    destination=address(ins,ops[0].mem,flow[caller].get(ins.address,{}))
                    installations[value].append(dict(witness(ins),caller=caller,registered_classes=construction.get(caller,[]),destination_expression=destination,
                        destination_offset=ops[0].mem.disp,source_family=(owners.get((graph.program.name,caller)) or ({},))[0].get('id')))
    for table,writes in native_table_writes(root,graph,digest).items():installations[table].extend(writes)
    tables=[];slot_rows=[];queries=[]
    tail_only=[int(x,16) for x in election['tail_only']]
    thunks={str(int(k,16)):int(v,16) for k,v in election['tail_thunks'].items()}
    for candidate,words in graph.tables.items():
        starts=sorted({candidate}|{t for t in installations if candidate<=t<candidate+4*len(words)})
        for at,end in zip(starts,starts[1:]+[candidate+4*len(words)]):
            values=words[(at-candidate)//4:(end-candidate)//4]
            writes=installations.get(at,[])
            classes=sorted({c for w in writes for c in w['registered_classes']})
            status=('registered-construction-witness' if classes else
                'native-construction-activation-unresolved' if writes and all(w.get('origin')=='native-source-store' for w in writes) else
                'construction-witness' if writes else 'construction-unresolved')
            tables.append(dict(candidate=candidate,table=at,slots=len(values),status=status,registered_classes=classes,installations=writes,rtti=table_type(graph,at)))
            for i,target in enumerate(values):
                if not (0x401000<=target<0x4a1300 or 0x4b3400<=target<0x4f0000 or 0x4f4490<=target<0x4f4aa0):continue
                row=dict(caller=0,site=at+i*4,target=target,kind='vtable-candidate',table=at,candidate_table=candidate,slot=i*4,
                         receiver_status=status,registered_classes=classes,outcome='receiver-provenance-unresolved')
                row['construction_witness']=bool(writes)
                if classes:row['outcome']='receiver-registered-construction-witness'
                target_owner=inventory.get(target)
                # Every candidate gets a conditional probe, even without a
                # constructor or callee owner. An unknown ABI uses an explicit
                # zero-argument fixture and can never count as ABI acceptance.
                query=dict(caller=0x401000,target=target,argc=target_owner['argc'] if target_owner else 0,
                    receiver=0x61000000,table=at,
                    words=receiver_words(graph,at),tail_only=tail_only,tail_thunks=thunks)
                row['probe_input_kind']='callee-contract-fixture' if target_owner else 'unknown-abi-zero-argument-fixture'
                row['callee_owned']=bool(target_owner)
                row['contract_probe_index']=len(queries);queries.append(query)
                slot_rows.append(row)
    answers=[]
    if queries and binary is not None:
        answers=json.loads(subprocess.run([str(binary)],input=json.dumps(queries),text=True,capture_output=True,
            env={**os.environ,'CLAW_GAME_VERSION':'1.0'},check=True).stdout)
    for row in slot_rows:
        if 'contract_probe_index' in row and binary is not None:
            i=row.pop('contract_probe_index');answer=answers[i]
            row['contract_probe']=dict(request=queries[i],answer=answer)
            row['transport_status']=('owner-unresolved' if not row['callee_owned'] else
                'refused' if answer['outcome']=='refused' else 'conditional-contract-accepted')
    tails=tail_probes(graph,tables,binary,election,inventory)
    contexts,same_receiver_edges=receiver_contexts(graph,tables,node_map,flow)
    indirect=[];registrar_sites={r['call']['site'] for r in registered};registrar_queries=[];registrar_rows=[]
    for edge in graph.unresolved:
        row=dict(edge);nodes=node_map.get(edge['caller'])
        if nodes is None:
            nodes=instructions(graph,edge['caller']);node_map[edge['caller']]=nodes
        if edge['reason']!='indirect-target' or edge['site'] not in nodes:
            row.update(indirect_kind='unclassified',status='operand-provenance-unresolved')
        else:
            caller=edge['caller']
            # Cache one fixed-point analysis per function, including all branch
            # joins. The site must be reachable from this function's entry.
            if caller not in flow:flow[caller]=states(nodes,caller)
            row.update(classify(nodes[edge['site']],flow[caller].get(edge['site'],{}),graph.program.imports))
            if row['indirect_kind']=='vtable-slot':
                row['receiver_origin']=origin(row['receiver_expression'])
                row['caller_receiver_contexts']=contexts.get(caller,[])
                # Retain a may-target inventory for diagnosis. It cannot close
                # a site until this particular receiver's class domain is bound.
                row['candidate_targets']=sorted({graph.word(t['table']+row['slot']) for t in tables if t['slots']*4>row['slot'] and t['installations']})
                if row['caller']==0x401000 and row['site'] in registrar_sites and row['slot']==0x24:
                    expected_receiver=('load',('add',('load',('add',('entry','esp'),4)),20))
                    if semantic(row['receiver_expression'])!=expected_receiver:
                        raise ValueError('Original registrar receiver expression changed')
                    table=registration_witness['registrar_table'];target=graph.word(table+row['slot'])
                    row.update(status='target-set-proved',receiver_domain=[table],targets=[target],
                        receiver_domain_proof=registration_witness)
                    query=dict(caller=row['caller'],site=row['site'],target=target,argc=3,receiver=0x61000000,table=table,
                        words=receiver_words(graph,table),tail_only=tail_only,tail_thunks=thunks)
                    registrar_queries.append(query);registrar_rows.append(row)
        indirect.append(row)
    if binary is not None and registrar_queries:
        registrar_answers=json.loads(subprocess.run([str(binary)],input=json.dumps(registrar_queries),text=True,capture_output=True,
            env={**os.environ,'CLAW_GAME_VERSION':'1.0'},check=True).stdout)
        for row,query,answer in zip(registrar_rows,registrar_queries,registrar_answers):
            row['original_contract_probe']=dict(request=query,answer=answer)
    construction_inputs={}
    for table in tables:
        for installation in table['installations']:
            declared=owners.get((graph.program.name,installation['caller']))
            if declared:
                manifest,_=declared
                paths=[root/'Tests/families'/f"{manifest['id']}.json",*(root/p for p in manifest['sources'])]
                construction_inputs.update({str(p.relative_to(root)):digest(p) for p in paths})
    entry_receivers=call_closure_entry_receivers.audit(root,graph,inventory,owners,indirect,
        node_map,flow,sys.modules[__name__],SourceShapes,digest,binary,election)
    summary=dict(profile=graph.program.name,original_sha256=graph.program.sha256,
        entry_receivers=entry_receivers,
        construction_inputs=construction_inputs,native_registration=registration_witness,metadata=metadata,registered_classes=registered,tables=tables,slots=slot_rows,indirect_sites=indirect,
        original_candidate_tables=len(graph.tables),original_game_slots=len(slot_rows),
        never_constructed_tables=[],
        table_statuses=dict(Counter(t['status'] for t in tables)),
        slot_statuses=dict(Counter(r['outcome'] for r in slot_rows)),
        transport_statuses=dict(Counter(r.get('transport_status','not-probed') for r in slot_rows)),
        indirect_kinds=dict(Counter(r['indirect_kind'] for r in indirect)),
        indirect_statuses=dict(Counter(r['status'] for r in indirect)),
        completion_obligation_met=(all(t['status']=='registered-construction-witness' for t in tables if any(r['table']==t['table'] for r in slot_rows))
            and all(r['status']=='target-set-proved' for r in indirect if r['indirect_kind']=='vtable-slot')
            and not any(r['status']=='operand-provenance-unresolved' for r in indirect)),
        tail_thunk_probes=tails,receiver_contexts=contexts,same_receiver_edges=same_receiver_edges,
        unresolved_vtable_origins=dict(Counter(r['receiver_origin'] for r in indirect if r['indirect_kind']=='vtable-slot' and r['status']!='target-set-proved')),
        unresolved_vtable_sites=[dict(caller=r['caller'],site=r['site'],slot=r['slot'],receiver_origin=r['receiver_origin']) for r in indirect if r['indirect_kind']=='vtable-slot' and r['status']!='target-set-proved'],
        contract='Original reachable constructor writes and registrar callback reachability prove possible construction, never nonconstruction. Slot probes use explicit callee-ABI fixtures through the production router; they do not prove emitted caller shapes or receiver class domains. Unknown table construction and indirect receiver domains remain open.')
    return summary


def self_test(decoder):
    """Small synthetic x86 programs exercise analysis, never the game harness."""
    examples=[
        ('thiscall-slot','8b01ff5004c3','vtable-slot'),
        ('callback-record','ff5104c3','callback-or-unproved-table'),
        ('different-receiver','8b02ff5004c3','callback-or-unproved-table'),
        ('changed-memory-receiver','8b4e048b018956048b4e04ff5004c3','callback-or-unproved-table'),
        ('push-aliases-receiver-slot','8b4c24fc8b01528b0c24ff5004c3','callback-or-unproved-table'),
        ('changed-receiver','8b0189d1ff5004c3','callback-or-unproved-table'),
        ('partial-register-write','8b0130c0ff5004c3','callback-or-unproved-table'),
        ('conflicting-tables-join','85d275048b01eb028b02ff5004c3','callback-or-unproved-table'),
        ('receiver-phi-then-slot','85d2750489d1eb0289d98b01ff5004c3','vtable-slot'),
        ('indexed-table','ff148500341200c3','function-pointer-table'),
        ('loop-receiver','8bf18bce8b01ff5004ebf7','vtable-slot'),
        ('cached-import','8b3500341200ffd6c3','import-pointer'),
        ('nonvolatile-import','8b3500341200e800000000ffd6c3','import-pointer'),
        ('volatile-import-killed','a100341200e800000000ffd0c3','callback-or-unproved-table'),
    ]
    results=[]
    for name,raw,expected in examples:
        nodes={i.address:i for i in decoder.disasm(bytes.fromhex(raw),0x1000)}
        incoming=states(nodes,0x1000)
        ins=next(i for i in reversed(list(nodes.values())) if i.group(CS_GRP_CALL))
        proof=classify(ins,incoming[ins.address],{0x123400:'fixture'})
        if proof['indirect_kind']!=expected:
            raise ValueError(f'Receiver flow regression {name}: {proof}')
        results.append(dict(name=name,kind=expected,status='pass'))
    return results


def invalidation_tests(root, graph, digest):
    source=(root/'Sources/ClawNativeMenuInterface.swift').read_text()
    mutations=[
        source.replace('_ = resources.invoke(0x401000,0,[base.sceneToken])',''),
        source.replace('(20,0x513b60,0x4cf940,false)','(20,0,0x4cf940,false)'),
    ]
    rejected=0
    for changed in mutations:
        try:native_registration(root,digest,source=changed)
        except ValueError:rejected+=1
        else:raise ValueError('Stale native registrar binding accepted')
    path=root/'App/GameData/MENU/level-one-data.json'
    spans={int(k,16):bytes(v) for k,v in json.loads(path.read_text()).items()}
    table=next(t for t in graph.tables if any(at<=t<t+4<=at+len(raw) for at,raw in spans.items()))
    at=next(at for at,raw in spans.items() if at<=table<table+4<=at+len(raw))
    raw=bytearray(spans[at]);raw[table-at]^=1;spans[at]=bytes(raw)
    try:metadata_tables(root,graph,digest,spans=spans)
    except ValueError:rejected+=1
    else:raise ValueError('Changed native table metadata accepted')
    return dict(status='pass',stale_native_bindings_rejected=rejected-1,changed_metadata_rejected=1)
