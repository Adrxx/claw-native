"""Check finite compiled edge metadata against the pinned original and registry.

No reference data is generated. This complements CPU/stack replay: it validates
CALL identities and registry signatures, not dynamic frame/ownership semantics.
"""
import json
import hashlib
import re
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.program import claw
from tools.claw import gen_project
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_REG_EBP, X86_REG_ESP, X86_REG_EAX, X86_REG_EBX, X86_REG_ECX, X86_OP_REG


def contracts(source=None):
    if source is None:
        source = (ROOT / 'Sources/ClawNativeCanonicalHost.swift').read_text()
    block = source.split('private static let sourceEdges: [SourceEdge] = [', 1)[1].split('\n    ]', 1)[0]
    pattern = re.compile(
        r'\.init\(root: (0x[0-9a-f]+), caller: (0x[0-9a-f]+), sourceCaller: (0x[0-9a-f]+), '
        r'callPC: (0x[0-9a-f]+), continuation: (0x[0-9a-f]+),\s*'
        r'target: \.(native|missing|localImport|cursorImport)(?:\((0x[0-9a-f]+)\))?, '
        r'entryFrameDelta: ([0-9]+), parentESPDelta: ([0-9]+), operation: '
        r'\.(checkedAllocation|constructor|localAllocation|missingThrow|cursorReset)'
        r'(?:\((0x[0-9a-f]+)(?:, \[([^\]]*)\])?\))?\),'
    )
    rows = []
    for match in pattern.finditer(block):
        root, caller, source_caller, pc, continuation, target, address, frame, delta, operation, size, arguments = match.groups()
        rows.append(dict(root=int(root,16), caller=int(caller,16), sourceCaller=int(source_caller,16),
                         pc=int(pc,16), continuation=int(continuation,16), target=target,
                         address=int(address,16) if address else None, frame=int(frame), delta=int(delta),
                         operation=operation, size=int(size,16) if size else None,
                         arguments=[] if not arguments else [int(word.strip(),0) for word in arguments.split(',')]))
    if not rows or pattern.sub('', block).strip():
        raise ValueError('Unrecognized finite edge syntax; update checker explicitly')
    return rows


def check(rows, program, registry):
    keys = set()
    disassembler = Cs(CS_ARCH_X86, CS_MODE_32)
    disassembler.detail = True
    for row in rows:
        key = (row['root'], row['caller'], row['continuation'], row['target'], row['address'])
        if key in keys:
            raise ValueError('Ambiguous edge key')
        keys.add(key)
        for field in ('root', 'caller', 'sourceCaller'):
            if row[field] not in registry:
                raise ValueError('Unadmitted caller/root')
        if registry[row['caller']]['family'] != registry[row['sourceCaller']]['family']:
            raise ValueError('Owned body belongs to a different family')
        section = next(s for s in program.sections if s.address <= row['sourceCaller'] < s.address + len(s.data))
        start, end = row['sourceCaller'] - section.address, row['continuation'] - section.address
        if not start <= end <= len(section.data):
            raise ValueError('Invalid CALL range')
        instructions = list(disassembler.disasm(section.data[start:end], row['sourceCaller']))
        call = next((i for i in instructions if i.address == row['pc']), None)
        if call is None or call.mnemonic != 'call' or call.address + call.size != row['continuation']:
            raise ValueError('Not an original CALL/continuation pair')
        operand = call.operands[0]
        if row['target'] in ('native', 'missing'):
            if operand.type != X86_OP_IMM or operand.imm != row['address']:
                raise ValueError('Wrong original direct callee')
        else:
            slot = 0x546aa8 if row['target'] == 'localImport' else 0x546cd0
            if operand.type != X86_OP_MEM or operand.mem.base != 0 or operand.mem.index != 0 or operand.mem.disp != slot:
                raise ValueError('Wrong original import binding')
        if row['target'] == 'native':
            callee = registry.get(row['address'])
            if callee is None:
                raise ValueError('Unadmitted callee')
            expected = {'checkedAllocation': ('stdcall', 1), 'constructor': ('thiscall', len(row['arguments']))}.get(row['operation'])
            if expected is None or (callee['convention'], callee['argc']) != expected:
                raise ValueError('Operation does not match native ABI/cleanup')
            context = callee.get('source_context', {})
            if not context.get('optional') or (context.get('input_mask'), context.get('output_mask'), context.get('preserve_mask')) != (0x7ff, 0x7ff, 0x472):
                raise ValueError('Insufficient source context capability')
        elif row['target'] == 'missing':
            if row['operation'] != 'missingThrow':
                raise ValueError('Missing source edge incorrectly returning')
        elif row['operation'] != {'localImport':'localAllocation','cursorImport':'cursorReset'}[row['target']]:
            raise ValueError('Wrong physical operation')


def module_contracts(source=None):
    if source is None:
        source = (ROOT / 'Sources/ClawNativeCanonicalHost.swift').read_text()
    block = source.split('private static let moduleEdges: [ModuleEdge] = [', 1)[1].split('\n    ]', 1)[0]
    pattern = re.compile(r'\.init\(caller: (0x[0-9a-f]+), callPC: (0x[0-9a-f]+), continuation: (0x[0-9a-f]+), target: (0x[0-9a-f]+), delta: ([0-9]+), operation: \.(thread|singleton|acquire|factory|release)\),')
    rows = [dict(caller=int(a,16),pc=int(b,16),continuation=int(c,16),target=int(d,16),delta=int(e),operation=f)
            for a,b,c,d,e,f in pattern.findall(block)]
    if not rows or pattern.sub('',block).strip():
        raise ValueError('Unrecognized module edge syntax')
    return rows


def check_module(rows, program, registry):
    # Explicit finite witnesses make each frame and semantic operation reviewable.
    expected = [
        (0x50228f,0x502299,0x50229e,0x50335e,8,'thread'),
        (0x50228f,0x5022af,0x5022b4,0x503420,8,'singleton'),
        (0x503420,0x50343f,0x503444,0x502e95,48,'acquire'),
        (0x503420,0x50344d,0x503450,0x502369,44,'factory'),
        (0x503420,0x503473,0x503478,0x502f05,48,'release')]
    if [tuple(r[k] for k in ('caller','pc','continuation','target','delta','operation')) for r in rows] != expected:
        raise ValueError('Module graph is not the reviewed finite set')
    signatures = {
        0x50228f:('cdecl',0,True,0x400),0x50335e:('thiscall',1,True,0x400),
        0x503420:('thiscall',1,False,0),0x502369:('cdecl',0,False,0x472),
        0x502e95:('stdcall',1,True,0),0x502f05:('stdcall',1,True,0)}
    for address,(convention,argc,optional,preserve) in signatures.items():
        entry=registry.get(address,{})
        context=entry.get('source_context',{})
        if (entry.get('convention'),entry.get('argc'),context.get('optional',False),context.get('input_mask'),context.get('output_mask'),context.get('preserve_mask')) != (convention,argc,optional,0x7ff,0x7ff,preserve):
            raise ValueError('Module source capability mismatch')
    md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
    for row in rows:
        section=next(s for s in program.sections if s.address<=row['caller']<s.address+len(s.data))
        call=next((i for i in md.disasm(section.data[row['caller']-section.address:row['continuation']-section.address],row['caller']) if i.address==row['pc']),None)
        if call is None or call.mnemonic!='call' or call.address+call.size!=row['continuation']:
            raise ValueError('Invalid module original CALL')
        op=call.operands[0]
        if row['operation']=='factory':
            if op.type!=X86_OP_MEM or op.mem.base!=X86_REG_EBP or op.mem.index!=0 or op.mem.disp!=8:
                raise ValueError('Invalid original singleton callback selection')
        elif op.type!=X86_OP_IMM or op.imm!=row['target']:
            raise ValueError('Invalid module original callee')
    # The explicit root and compiler continuation are also source authority.
    for start,pc,cont,target in [(0x50257f,0x5025b8,0x5025bd,0x50228f),(0x503420,0x503425,0x50342a,0x4a48c0)]:
        section=next(s for s in program.sections if s.address<=start<s.address+len(s.data))
        call=next((i for i in md.disasm(section.data[start-section.address:cont-section.address],start) if i.address==pc),None)
        if call is None or call.mnemonic!='call' or call.address+call.size!=cont or call.operands[0].type!=X86_OP_IMM or call.operands[0].imm!=target:
            raise ValueError('Invalid module root/compiler CALL')
    compiler=registry.get(0x4a48c0,{}).get('compiler_context',{})
    if (compiler.get('input_mask'),compiler.get('output_mask'))!=(0x7ff,0x7ff):
        raise ValueError('Invalid module compiler capability')


def check_application(source, program, registry):
    app_rows=[r for r in contracts(source) if r['root']==0x502301]
    if len(app_rows)!=3: raise ValueError('Application must have exactly three physical allocation edges')
    check(app_rows,program,registry)
    pattern=(r'private static let applicationOwnedScope = OwnedCompilerScope\(\s*'
      r'owner: (0x[0-9a-f]+), body: (0x[0-9a-f]+), callPC: (0x[0-9a-f]+), continuation: (0x[0-9a-f]+),\s*'
      r'helperCallPC: (0x[0-9a-f]+), helperContinuation: (0x[0-9a-f]+), handler: (0x[0-9a-f]+),\s*'
      r'constructorFrameDelta: (\d+), helperFrameDelta: (\d+), allocationSize: (0x[0-9a-f]+)\)')
    match=re.search(pattern,source)
    if match is None: raise ValueError('Missing typed owned compiler scope')
    values=[int(v,16 if v.startswith('0x') else 10) for v in match.groups()]
    if values != [0x502301,0x50210b,0x502324,0x502329,0x502110,0x502115,0x5084ca,24,28,0x84]:
        raise ValueError('Invalid owned compiler scope/frame')
    for address,convention in [(0x502301,'cdecl'),(0x50210b,'thiscall')]:
        entry=registry.get(address,{})
        context=entry.get('source_context',{})
        if (entry.get('argc'),entry.get('convention'),context.get('optional',False),context.get('input_mask'),context.get('output_mask'),context.get('preserve_mask')) != (0,convention,False,0x7ff,0x7ff,0x472):
            raise ValueError('Application requires exact required source capability')
    md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
    for start,pc,cont,target in [(0x50257f,0x5025ca,0x5025cf,0x50335e),(0x502301,0x502306,0x50230b,0x4a48c0),(0x502301,0x502324,0x502329,0x50210b),(0x50210b,0x502110,0x502115,0x4a48c0),(0x50335e,0x5033ba,0x5033be,None)]:
        section=next(s for s in program.sections if s.address<=start<s.address+len(s.data))
        call=next((i for i in md.disasm(section.data[start-section.address:cont-section.address],start) if i.address==pc),None)
        if call is None or call.mnemonic!='call' or call.address+call.size!=cont:
            raise ValueError('Invalid application original CALL')
        op=call.operands[0]
        if target is None:
            if op.type!=X86_OP_MEM or op.mem.base!=X86_REG_ESP or op.mem.index!=0 or op.mem.disp!=12:
                raise ValueError('Invalid TLS callback selection')
        elif op.type!=X86_OP_IMM or op.imm!=target: raise ValueError('Invalid application callee')
    section=next(s for s in program.sections if s.address<=0x5025bd<s.address+len(s.data))
    bridge=list(md.disasm(section.data[0x5025bd-section.address:0x5025cf-section.address],0x5025bd))
    if len(bridge)!=4: raise ValueError('Invalid caller bridge length')
    mov,push,lea,call=bridge
    if not (mov.mnemonic=='mov' and mov.operands[0].type==X86_OP_REG and mov.operands[0].reg==X86_REG_EBX and mov.operands[1].type==X86_OP_REG and mov.operands[1].reg==X86_REG_EAX and
        push.mnemonic=='push' and push.operands[0].type==X86_OP_IMM and push.operands[0].imm==0x502301 and
        lea.mnemonic=='lea' and lea.operands[0].reg==X86_REG_ECX and lea.operands[1].type==X86_OP_MEM and lea.operands[1].mem.base==X86_REG_EBX and lea.operands[1].mem.index==0 and lea.operands[1].mem.disp==0x1070 and
        call.address==0x5025ca and call.mnemonic=='call' and call.operands[0].type==X86_OP_IMM and call.operands[0].imm==0x50335e):
        raise ValueError('Caller bridge does not match actual boundary actions')
    return dict(source_edges=app_rows,owned_scope=values,bridge=[i.address for i in bridge])


def check_application_object(source, program, registry):
    block=source.split('private static let applicationEdges: [ApplicationEdge] = [',1)[1].split('\n    ]',1)[0]
    pattern=re.compile(r'\.init\(caller:(0x[0-9a-f]+),callPC:(0x[0-9a-f]+),continuation:(0x[0-9a-f]+),target:(0x[0-9a-f]+),delta:(\d+),count:(\d+),preserve:(0x[0-9a-f]+|0)\),')
    rows=[[int(v,0) for v in match.groups()] for match in pattern.finditer(block)]
    expected=[
        [0x50257f,0x502592,0x502597,0x503510,36,0,0x472],
        [0x50257f,0x5025aa,0x5025af,0x4a56e0,40,1,0x472],
        [0x50257f,0x5025b8,0x5025bd,0x50228f,36,0,0x400],
        [0x50257f,0x5025ca,0x5025cf,0x50335e,40,1,0x400],
        [0x50257f,0x5025d2,0x5025d8,0x5469bc,36,0,0],
        [0x50257f,0x5025db,0x5025e1,0x5469c0,36,0,0],
        [0x4a56e0,0x4a56f7,0x4a56fc,0x4a48e0,20,1,0x472],
        [0x503510,0x503569,0x50356f,0x546cd0,44,1,0x472]]
    if pattern.sub('',block).strip() or rows!=expected: raise ValueError('Invalid finite whole application edge/frame contract')
    for address,argc,convention,preserve,optional in [(0x50257f,1,'thiscall',0x472,False),(0x503510,0,'thiscall',0x472,False),(0x4a56e0,1,'cdecl',0x472,False),(0x50228f,0,'cdecl',0x400,True),(0x50335e,1,'thiscall',0x400,True)]:
        entry=registry.get(address,{});context=entry.get('source_context',{})
        if (entry.get('argc'),entry.get('convention'),context.get('input_mask'),context.get('output_mask'),context.get('preserve_mask'),context.get('optional',False))!=(argc,convention,0x7ff,0x7ff,preserve,optional): raise ValueError('Invalid whole application child capability')
    md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
    calls=[row[:4] for row in rows]+[[0x4251f0,0x4251fa,0x4251ff,0x50257f],[0x50257f,0x502584,0x502589,0x4a48c0],[0x503510,0x503515,0x50351a,0x4a48c0]]
    for start,pc,cont,target in calls:
        section=next(s for s in program.sections if s.address<=start<s.address+len(s.data))
        call=next((i for i in md.disasm(section.data[start-section.address:cont-section.address],start) if i.address==pc),None)
        if call is None or call.mnemonic!='call' or call.address+call.size!=cont: raise ValueError('Wrong application original CALL identity')
        op=call.operands[0]
        if target>=0x546000:
            if op.type!=X86_OP_MEM or op.mem.base!=0 or op.mem.index!=0 or op.mem.disp!=target: raise ValueError('Wrong physical import target')
        elif op.type!=X86_OP_IMM or op.imm!=target: raise ValueError('Wrong direct source target')
    compiler=source.split('enum CompilerSite: UInt32 {',1)[1].split('enum SourceSite:',1)[0]
    root=source.split('enum SourceSite: UInt32 {',1)[1].split('struct LocksSnapshot:',1)[0]
    if 'case applicationObject = 0x502589' not in compiler or 'case .applicationObject: return 0x50257f' not in compiler or 'case .applicationObject: return 0x5086f4' not in compiler or 'case applicationObject = 0x4251ff' not in root or 'case .applicationObject: return 0x50257f' not in root: raise ValueError('Wrong whole root/compiler scope election')
    helper=registry.get(0x4a48c0,{});contract=helper.get('compiler_context',{})
    if helper.get('convention')!='compiler-context' or helper.get('argc')!=0 or contract.get('input_mask')!=0x7ff or contract.get('output_mask')!=0x7ff: raise ValueError('Wrong compiler capability')
    return dict(edges=rows,root=[0x4251fa,0x4251ff,0x50257f],compiler=[0x502584,0x502589,0x5086f4],thread_compiler=[0x503515,0x50351a,0x508ca4])


def main():
    program = claw()  # Hash verification precedes every original byte read.
    host_path = ROOT / 'Sources/ClawNativeCanonicalHost.swift'
    host_bytes = host_path.read_bytes()
    manifests = {p: p.read_bytes() for p in sorted(gen_project.FAMILIES.glob('*.json'))}
    exclusion_bytes = gen_project.EXCLUDE_FILE.read_bytes()
    inventory = gen_project.canonical_inventory(
        [json.loads(data) for data in manifests.values()], json.loads(exclusion_bytes))[2]
    registry = {row['address']: row for row in inventory}
    rows = contracts(host_bytes.decode())
    if "--application" not in sys.argv[1:]: rows = [r for r in rows if r["root"] != 0x502301]
    check(rows, program, registry)
    modules = module_contracts(host_bytes.decode()) if "--module" in sys.argv[1:] else []
    if modules: check_module(modules, program, registry)
    application = check_application(host_bytes.decode(),program,registry) if "--application" in sys.argv[1:] else None
    whole = check_application_object(host_bytes.decode(),program,registry) if "--application-object" in sys.argv[1:] else None
    rejected = 0
    def must_reject(changed, changed_registry=registry):
        nonlocal rejected
        try:
            check(changed, program, changed_registry)
        except ValueError:
            rejected += 1
            return
        raise AssertionError('Tampered edge metadata accepted')
    for field, value in [('caller',0), ('sourceCaller',0x503510), ('pc',rows[0]['pc']+1),
                         ('continuation',rows[0]['continuation']+1), ('address',0x501f01),
                         ('operation','constructor')]:
        changed=deepcopy(rows); changed[0][field]=value; must_reject(changed)
    must_reject(rows + [deepcopy(rows[0])])
    for field, value in [('argc',0), ('convention','cdecl')]:
        changed=deepcopy(registry); changed[rows[0]['address']][field]=value
        must_reject(rows, changed)
    for field in ('input_mask','output_mask','preserve_mask'):
        changed=deepcopy(registry); changed[rows[0]['address']]['source_context'][field]=0
        must_reject(rows, changed)
    addresses = {row[field] for row in rows for field in ('root','caller','sourceCaller')}
    addresses.update(row['address'] for row in rows if row['target'] == 'native')
    if modules:
        for field, value in [('caller',0),('pc',0),('continuation',0),('target',0),('delta',0),('operation','factory')]:
            changed=deepcopy(modules);changed[0][field]=value
            try: check_module(changed,program,registry)
            except ValueError: rejected+=1
            else: raise AssertionError('Tampered module edge accepted')
        for address in (0x50335e,0x503420,0x502369,0x502e95,0x502f05):
            changed=deepcopy(registry);changed[address]['source_context']['preserve_mask'] ^= 1
            try: check_module(modules,program,changed)
            except ValueError: rejected+=1
            else: raise AssertionError('Tampered module capability accepted')
        addresses.update(r[k] for r in modules for k in ('caller','target'))
        addresses.add(0x4a48c0)
    if application:
        for before,after in [('constructorFrameDelta: 24','constructorFrameDelta: 20'),('helperFrameDelta: 28','helperFrameDelta: 24'),('handler: 0x5084ca','handler: 0x508511'),('body: 0x50210b','body: 0x502301')]:
            changed=host_bytes.decode().replace(before,after)
            try: check_application(changed,program,registry)
            except ValueError: rejected+=1
            else: raise AssertionError('Invalid owned scope accepted')
        for field,value in [('optional',True),('preserve_mask',0),('input_mask',0),('output_mask',0)]:
            changed=deepcopy(registry);changed[0x502301]['source_context'][field]=value
            try: check_application(host_bytes.decode(),program,changed)
            except ValueError: rejected+=1
            else: raise AssertionError('Invalid application capability accepted')
        addresses.update((0x502301,0x50210b,0x4a48c0,0x50335e))
    if whole:
        for before,after in [('callPC:0x502592','callPC:0x502593'),('continuation:0x502597','continuation:0x502598'),('target:0x503510','target:0x502301'),('delta:36','delta:32'),('count:0','count:1'),('preserve:0x400','preserve:0x472'),('case applicationObject = 0x4251ff','case applicationObject = 0x425200'),('case .applicationObject: return 0x5086f4','case .applicationObject: return 0x508ca4')]:
            try: check_application_object(host_bytes.decode().replace(before,after),program,registry)
            except ValueError: rejected+=1
            else: raise AssertionError('Invalid whole application edge accepted')
        for address in (0x50257f,0x503510,0x4a56e0,0x50228f,0x50335e):
            for field,value in [('optional',not registry[address]['source_context'].get('optional',False)),('preserve_mask',0)]:
                changed=deepcopy(registry);changed[address]['source_context'][field]=value
                try: check_application_object(host_bytes.decode(),program,changed)
                except ValueError: rejected+=1
                else: raise AssertionError('Invalid whole application capability accepted')
        addresses.update((0x50257f,0x503510,0x4a56e0,0x50228f,0x50335e,0x4a48c0))
    families = {registry[address]['family'] for address in addresses}
    inputs = {str(p.relative_to(ROOT)): hashlib.sha256(data).hexdigest()
              for p, data in manifests.items() if json.loads(data).get('id') in families}
    inputs[str(host_path.relative_to(ROOT))] = hashlib.sha256(host_bytes).hexdigest()
    inputs[str(gen_project.EXCLUDE_FILE.relative_to(ROOT))] = hashlib.sha256(exclusion_bytes).hexdigest()
    print(json.dumps({'status':'pass','edges':len(rows),'module_edges':len(modules),'application_object_edges':len(whole['edges']) if whole else 0,'rejected_metadata_mutations':rejected,
                      'input_sha256': inputs,
                      'program_sha256':program.sha256,
                      'scope':'original CALL identities and registry signatures; dynamic witnesses remain replay checks'}))


if __name__ == '__main__':
    main()
