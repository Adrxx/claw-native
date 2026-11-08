"""Recheck bounded local reviews against original bytes and caller source hashes.

Original addresses, byte hashes, reviewed function ranges and site selections
live under work/call-closure. No diagnostic label by itself exempts an edge.
"""
from functools import lru_cache
import hashlib
import json
import re
from capstone import CS_GRP_JUMP, CS_GRP_RET
from capstone.x86 import X86_OP_IMM


def provider_inline(graph, original, manifest, reader, rows):
    """Validate a reviewed local replacement, never an impossible-edge waiver.

    Reviews retain the original operand context and current reachable source
    path. Arithmetic domains and native memory operations remain separate.
    """
    for row in rows:
        if row['original_site']!=original or row['family']!=manifest['id']:continue
        if any(hashlib.sha256((reader.root/p).read_bytes()).hexdigest()!=h
               for p,h in row['source_inputs'].items()):continue
        if not set(manifest['sources']).issubset(row['source_inputs']):continue
        if hashlib.sha256((reader.root/'Tests/families'/f"{manifest['id']}.json").read_bytes()).hexdigest()!=row['manifest_sha256']:continue
        if any(hashlib.sha256(graph.bytes(b['address'],b['size'])).hexdigest()!=b['sha256']
               for b in row['original_ranges']):continue
        owned=next(o for o in manifest['owned'] if int(o['address'],16)==original['caller'])
        leaves=reader.entry_calls(original['caller'],bool(owned.get('source_context') or owned.get('compiler_context')))
        witness=row['actual_source']
        matches=[l for l in leaves if l['api']=='enter' and all(l.get(k)==witness[k]
                 for k in ('path','line','callee','args','chain'))]
        matches=[l for l in matches if [{k:p[k] for k in ('path','line','api','args','chain')}
                  for p in l.get('parents',[])]==row['parent_calls']]
        if len(matches)!=1:continue
        leaf=matches[0];definition=reader.resolve(leaf['callee'],leaf['path'])
        if definition is None:continue
        operation=row['operation']
        path=reader.root/operation['path'];lines=path.read_text().splitlines()
        if not 1<=operation['line']<=len(lines) or lines[operation['line']-1].strip()!=operation['text']:continue
        if operation['path']!=definition['path']:continue
        start=reader.files[definition['path']][:definition['offset']].count('\n')+1
        if not start<=operation['line']<=start+definition['text'].count('\n'):continue
        # No host dispatch may be silently swallowed by the replacement's
        # helper subtree. Memory loads/stores and tick remain value obligations.
        chain=leaf['chain']+[leaf['callee']]
        if row['replacement_kind']=='helper':
            if any(l['api'] not in ('enter','local','memory') and l['chain'][:len(chain)]==chain for l in leaves):continue
        elif row['replacement_kind']=='expression':
            if re.search(r'\b(?:call|icall|source_call|source_tail|context_call|call_x87|call_x87_exact|fastcall|vcall|dispatch)\s*\(',operation['text']):continue
        else:continue
        return dict(inlined=True,emitted_host_calls=0),dict(
            reviewed_provider_inline=row,actual_source=witness,operation=operation,
            source_inputs=row['source_inputs'],
            contract='Original-site to emitted local-operation shape only; arithmetic, memory and accepted value domains remain separate.')
    return None


def cfg(graph, root):
    nodes={};pending=[root]
    while pending:
        address=pending.pop()
        if address in nodes:continue
        if not root <= address < root+0x10000 or len(nodes)>10000:
            raise ValueError('Review escapes its bounded caller')
        ins=next(graph.decoder.disasm(graph.bytes(address,15),address,count=1))
        after=address+ins.size;edges=[]
        if ins.group(CS_GRP_RET):pass
        elif ins.group(CS_GRP_JUMP):
            if ins.operands[0].type!=X86_OP_IMM:
                raise ValueError('Indirect caller control flow needs a separate review')
            edges.append(ins.operands[0].imm)
            if ins.mnemonic!='jmp':edges.append(after)
        else:edges.append(after)
        nodes[address]=(ins,edges);pending+=edges
    return nodes


def reachable(nodes,root,cuts):
    seen=set();pending=[root]
    while pending:
        address=pending.pop()
        if address in seen:continue
        seen.add(address)
        pending.extend(target for target in nodes[address][1] if (address,target) not in cuts)
    return seen


@lru_cache(maxsize=8)
def fault_witness(program_hash, review_json):
    """Execute unmodified post-realloc paths, with EAX zero, to the null read."""
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_MEM_INVALID, UcError
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP
    review=json.loads(review_json)
    receipts=[]
    # Bytes were read through the hash-checking Program by the caller.
    for path in review['null_return_paths']:
        uc=Uc(UC_ARCH_X86,UC_MODE_32)
        for block in review['code_blocks']:
            uc.mem_map(block['address'],block['size'])
            uc.mem_write(block['address'],bytes.fromhex(block['bytes']))
        uc.mem_map(0x1ff0000,0x20000)
        uc.reg_write(UC_X86_REG_ESP,0x2000000);uc.reg_write(UC_X86_REG_EAX,0)
        faults=[]
        def invalid(machine,access,address,size,value,user):
            faults.append(dict(pc=machine.reg_read(UC_X86_REG_EIP),address=address,size=size))
            return False
        uc.hook_add(UC_HOOK_MEM_INVALID,invalid)
        try:uc.emu_start(path,0,count=64)
        except UcError:pass
        if faults!=[review['expected_fault']]:raise ValueError(f'Original fault witness changed: {faults}')
        receipts.append(dict(start=path,fault=faults[0]))
    return dict(original_sha256=program_hash,paths=receipts,review=review['review'])


class OriginalReviews:
    def __init__(self,graph,path):
        self.graph=graph;self.nodes={};self.rows={};self.witness=None
        if not path.exists():return
        data=json.loads(path.read_text())
        if data['original_sha256']!=graph.program.sha256:raise ValueError('Stale original review')
        grow=data['grow']
        for block in grow['code_blocks']:
            raw=graph.bytes(block['address'],block['size'])
            if hashlib.sha256(raw).hexdigest()!=block['sha256']:raise ValueError('Stale reviewed grow bytes')
            block['bytes']=raw.hex()
        self.witness=fault_witness(graph.program.sha256,json.dumps(grow,sort_keys=True))
        self.grow=grow
        for row in data['edges']:
            original=row['original_site'];root=original['caller']
            raw=graph.bytes(root,row['caller_size'])
            if hashlib.sha256(raw).hexdigest()!=row['caller_sha256']:raise ValueError('Stale reviewed caller bytes')
            if root not in self.nodes:self.nodes[root]=cfg(graph,root)
            nodes=self.nodes[root];cuts=set()
            for guard in row['guards']:
                call=nodes[guard['grow_site']][0]
                test=nodes[guard['test']][0];branch=nodes[guard['branch']][0]
                if not (call.mnemonic=='call' and call.operands[0].type==X86_OP_IMM and call.operands[0].imm==grow['address'] and
                        call.address+call.size==test.address and test.mnemonic=='test' and test.op_str=='eax, eax' and
                        test.address+test.size==branch.address and branch.mnemonic in ('je','jne')):
                    raise ValueError('Reviewed failure guard changed')
                zero=branch.operands[0].imm if branch.mnemonic=='je' else branch.address+branch.size
                if zero!=guard['zero']:raise ValueError('Reviewed zero-return branch changed')
                cuts.add((branch.address,zero))
            if not cuts or original['site'] in reachable(nodes,root,cuts):raise ValueError('Reviewed edge remains reachable')
            self.rows[(root,original['site'])]=row

    def edge(self,original):
        row=self.rows.get((original['caller'],original['site']))
        if not row or row['original_site']!=original:return None
        return dict(impossible=True),dict(reviewed_original_impossibility=row,original_fault=self.witness)
