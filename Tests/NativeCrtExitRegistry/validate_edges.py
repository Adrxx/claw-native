"""Validate finite CRT edge metadata against the hash-pinned original.

This is static metadata validation. It neither executes unknown source callees
nor proves dynamic CPU, frame, physical-owner, or source-election behavior.
"""
import hashlib
import json
import re
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import (X86_OP_IMM, X86_OP_MEM, X86_OP_REG,
                         X86_REG_EBP, X86_REG_ESP, X86_REG_ESI, X86_REG_EAX)
from capstone.x86 import X86_REG_ECX
from Tests.clawparity.program import claw
from tools.claw import gen_project

# Reviewed finite boundary, not permission to admit an additional source body.
# caller, original CALL PC, continuation, source target/import slot, entry-frame
# delta from caller entry ESP, argument count, physical stdcall cleanup.
EXPECTED = [
    (0x4a3610, 0x4a3615, 0x4a361a, 0x4a48e0, 8, 1, False),
    (0x4a3610, 0x4a3628, 0x4a362d, 0x4a4860, 8, 1, False),
    (0x4a35f0, 0x4a35f5, 0x4a35fa, 0x4a3560, 8, 1, False),
    (0x4a3560, 0x4a3561, 0x4a3566, 0x4a5860, 8, 0, False),
    (0x4a3560, 0x4a356c, 0x4a3571, 0x4a6560, 12, 1, False),
    (0x4a3560, 0x4a358c, 0x4a3591, 0x4a6560, 12, 1, False),
    (0x4a3560, 0x4a359f, 0x4a35a4, 0x4a9070, 16, 2, False),
    (0x4a3560, 0x4a35ab, 0x4a35b0, 0x4a5870, 8, 0, False),
    (0x4a3560, 0x4a35e6, 0x4a35eb, 0x4a5870, 8, 0, False),
    (0x4a5860, 0x4a5862, 0x4a5867, 0x4a7bc0, 8, 1, False),
    (0x4a5870, 0x4a5872, 0x4a5877, 0x4a7c40, 8, 1, False),
    (0x4a7b90, 0x4a7b9d, 0x4a7b9f, 0x546aa4, 12, 1, True),
    (0x4a7b90, 0x4a7ba6, 0x4a7ba8, 0x546aa4, 12, 1, True),
    (0x4a7b90, 0x4a7baf, 0x4a7bb1, 0x546aa4, 12, 1, True),
    (0x4a7b90, 0x4a7bb7, 0x4a7bb9, 0x546aa4, 12, 1, True),
    (0x4a7bc0, 0x4a7bd5, 0x4a7bda, 0x4a48e0, 20, 1, False),
    (0x4a7bc0, 0x4a7be5, 0x4a7bea, 0x4a4860, 20, 1, False),
    (0x4a7bc0, 0x4a7bef, 0x4a7bf4, 0x4a7bc0, 20, 1, False),
    (0x4a7bc0, 0x4a7c03, 0x4a7c09, 0x546aa4, 20, 1, True),
    (0x4a7bc0, 0x4a7c12, 0x4a7c17, 0x4a49b0, 20, 1, False),
    (0x4a7bc0, 0x4a7c1c, 0x4a7c21, 0x4a7c40, 20, 1, False),
    (0x4a7bc0, 0x4a7c2d, 0x4a7c33, 0x546aac, 16, 1, True),
    (0x4a7c40, 0x4a7c4e, 0x4a7c54, 0x546a9c, 12, 1, True),
]
FIELDS = ('caller', 'pc', 'continuation', 'target', 'delta', 'count', 'stdcall')
SOURCE = {
    0x4a3610: (0, 'u32', 0x4a3646), 0x4a3560: (1, 'u32', 0x4a35ef),
    0x4a35f0: (1, 'u32', 0x4a3605), 0x4a5860: (0, 'void', 0x4a586b),
    0x4a5870: (0, 'void', 0x4a587b), 0x4a7b90: (0, 'void', 0x4a7bbb),
    0x4a7bc0: (1, 'void', 0x4a7c36), 0x4a7c40: (1, 'void', 0x4a7c56),
}
PHYSICAL = {
    0x4a48e0: ('cdecl', 1, 'u32', None),
    0x4a6560: ('cdecl', 1, 'u32', None),
    0x4a9070: ('cdecl', 2, 'u32', None),
    0x4a49b0: ('cdecl', 1, 'void', None),
    0x546aa4: ('stdcall', 1, 'void', 'InitializeCriticalSection'),
    0x546aac: ('stdcall', 1, 'void', 'EnterCriticalSection'),
    0x546a9c: ('stdcall', 1, 'void', 'LeaveCriticalSection'),
}
MISSING = {0x4a4860: ('cdecl', 1, 'void')}
ROOTS = {
    'initializeLocks': (0x4a7b90, 0x4a7d46),
    'initializeRegistry': (0x4a3610, 0x4a5896),
    'register': (0x4a35f0, 0x42520a), 'append': (0x4a3560, 0x4a35fa),
    'acquireWrapper': (0x4a5860, 0x4a3566),
    'releaseWrapper': (0x4a5870, 0x4a35eb),
    'acquire': (0x4a7bc0, 0x4a5867), 'release': (0x4a7c40, 0x4a5877),
}


def contracts(source):
    anchor = 'private static let crtEdges: [CrtEdge] = ['
    if source.count(anchor) != 1:
        raise ValueError('Missing or ambiguous CRT edge table')
    block = source.split(anchor, 1)[1].split('\n    ]', 1)[0]
    pattern = re.compile(
        r'\.init\(caller: (0x[0-9a-f]+), callPC: (0x[0-9a-f]+), '
        r'continuation: (0x[0-9a-f]+), target: (0x[0-9a-f]+), '
        r'delta: (\d+), count: (\d+), stdcall: (true|false)\),')
    rows = []
    for match in pattern.finditer(block):
        a, b, c, d, e, f, g = match.groups()
        rows.append(dict(zip(FIELDS, (int(a, 16), int(b, 16), int(c, 16), int(d, 16),
                                      int(e), int(f), g == 'true'))))
    if not rows or pattern.sub('', block).strip():
        raise ValueError('Unrecognized finite CRT edge syntax')
    return rows


def instructions(program, start, end):
    section = next((s for s in program.sections
                    if s.address <= start < end <= s.address + len(s.data)), None)
    if section is None:
        raise ValueError('Original range is not backed')
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    found = list(md.disasm(section.data[start-section.address:end-section.address], start))
    if not found or found[-1].address + found[-1].size != end:
        raise ValueError('Original range did not decode completely')
    return found


def check_original_call(row, decoded):
    call = decoded.get(row['pc'])
    if call is None or call.mnemonic != 'call' or call.address + call.size != row['continuation']:
        raise ValueError('Not an original CALL/continuation')
    op = call.operands[0]
    target = row['target']
    if row['caller'] == 0x4a7b90:
        if op.type != X86_OP_REG or op.reg != X86_REG_ESI or target != 0x546aa4:
            raise ValueError('Wrong cached InitializeCriticalSection identity')
        # Verify the actual cache assignment and no overwrite before this call.
        load = decoded.get(0x4a7b96)
        if load is None or load.mnemonic != 'mov' or len(load.operands) != 2:
            raise ValueError('Missing original IAT cache load')
        dest, src = load.operands
        if not (dest.type == X86_OP_REG and dest.reg == X86_REG_ESI and
                src.type == X86_OP_MEM and src.mem.base == src.mem.index == 0 and
                src.mem.disp == target):
            raise ValueError('Wrong original IAT cache slot')
        for ins in decoded.values():
            if load.address < ins.address < call.address:
                _, written = ins.regs_access()
                if X86_REG_ESI in written:
                    raise ValueError('Cached IAT identity overwritten')
    elif target in PHYSICAL and PHYSICAL[target][3] is not None:
        if not (op.type == X86_OP_MEM and op.mem.base == op.mem.index == 0 and op.mem.disp == target):
            raise ValueError('Wrong original IAT slot')
    elif op.type != X86_OP_IMM or op.imm != target:
        raise ValueError('Wrong original direct child')


def stack_frames(caller, decoded, edges):
    """Finite static CFG proof of original stack height, without callee execution.

    Calls use the reviewed explicit ABI; missing fatal calls have no successor.
    Both branch successors are checked. Unknown calls/ESP writes fail closed.
    """
    pending = [(caller, 0, None)]
    visited = set()
    observed = {}
    returned = False
    while pending:
        pc, delta, ebp = pending.pop()
        key = (pc, delta, ebp)
        if key in visited:
            continue
        visited.add(key)
        if len(visited) > 512 or not -64 <= delta <= 0:
            raise ValueError('Unbounded original stack proof')
        ins = decoded.get(pc)
        if ins is None:
            raise ValueError('Original branch outside owned body')
        next_pc = pc + ins.size
        ops = ins.operands
        if ins.mnemonic == 'call':
            row = edges.get(pc)
            if row is None:
                raise ValueError('Unreviewed original source call')
            observed.setdefault(pc, set()).add(4 - delta)
            if row['target'] in MISSING:
                continue
            if row['stdcall']:
                delta += row['count'] * 4
        elif ins.mnemonic == 'push':
            delta -= 4
        elif ins.mnemonic == 'pop':
            if ops[0].type == X86_OP_REG and ops[0].reg == X86_REG_ESP:
                raise ValueError('Unsupported pop ESP')
            delta += 4
        elif ins.mnemonic == 'mov' and ops[0].type == X86_OP_REG and ops[0].reg == X86_REG_EBP:
            if ops[1].type != X86_OP_REG or ops[1].reg != X86_REG_ESP:
                raise ValueError('Unsupported EBP replacement')
            ebp = delta
        elif ins.mnemonic in ('add', 'sub') and ops[0].type == X86_OP_REG and ops[0].reg == X86_REG_ESP:
            if ops[1].type != X86_OP_IMM:
                raise ValueError('Unknown ESP arithmetic')
            delta += ops[1].imm if ins.mnemonic == 'add' else -ops[1].imm
        elif ins.mnemonic == 'ret':
            if delta != 0 or (ops and ops[0].imm != 0):
                raise ValueError('Original cdecl return/stack cleanup mismatch')
            returned = True
            continue
        elif ins.mnemonic.startswith('j'):
            if ops[0].type != X86_OP_IMM:
                raise ValueError('Unknown original jump')
            pending.append((ops[0].imm, delta, ebp))
            if ins.mnemonic == 'jmp':
                continue
        else:
            _, written = ins.regs_access()
            if X86_REG_ESP in written:
                raise ValueError('Unsupported original ESP write')
        pending.append((next_pc, delta, ebp))
    if not returned or set(observed) != set(edges):
        raise ValueError('Incomplete original finite CALL coverage')
    for pc, heights in observed.items():
        if heights != {edges[pc]['delta']}:
            raise ValueError('Wrong original bounded entry frame')


def check(rows, program, registry, manifests):
    keys = set()
    for row in rows:
        if set(row) != set(FIELDS) or any(type(row[k]) is not int for k in FIELDS[:-1]) or type(row['stdcall']) is not bool:
            raise ValueError('Malformed parsed CRT row')
        key = (row['caller'], row['continuation'])
        if key in keys:
            raise ValueError('Ambiguous CRT edge key')
        keys.add(key)
    if sorted(tuple(r[k] for k in FIELDS) for r in rows) != sorted(EXPECTED):
        raise ValueError('CRT graph is not the reviewed finite set')
    for address, (argc, returns, _) in SOURCE.items():
        entry = registry.get(address, {})
        context = entry.get('source_context', {})
        if (entry.get('convention'), entry.get('argc'), entry.get('returns'),
            context.get('input_mask'), context.get('output_mask'), context.get('preserve_mask'),
            context.get('optional', False)) != ('cdecl', argc, returns, 0x7ff, 0x7ff, 0x472, False):
            raise ValueError('Unadmitted or stale CRT source capability')
    # Physical boundaries are explicitly declared fixtures; an admitted address
    # elsewhere does not change this domain into execution of CRT heap internals.
    for address, signature in PHYSICAL.items():
        convention, argc, returns, import_name = signature
        declarations = [m.get('callees', {}).get(hex(address)) for m in manifests
                        if m.get('id') in ('crt_exit_registry', 'crt_lock_records')]
        declarations = [d for d in declarations if d is not None]
        if not declarations or any((d.get('kind'), d.get('convention'), d.get('argc'), d.get('returns')) !=
                                   ('fixture', convention, argc, returns) for d in declarations):
            raise ValueError('Stale physical CRT service declaration')
        if import_name and program.imports.get(address, '').split('!')[-1] != import_name:
            raise ValueError('Wrong pinned original physical import identity')
    for address, signature in MISSING.items():
        if address in registry:
            raise ValueError('Fatal child is no longer missing; boundary needs explicit review')
        for manifest in manifests:
            if manifest.get('id') not in ('crt_exit_registry', 'crt_lock_records'):
                continue
            child = manifest.get('callees', {}).get(hex(address), {})
            if (child.get('kind'), child.get('convention'), child.get('argc'), child.get('returns')) != ('whole', *signature):
                raise ValueError('Fatal source stop incorrectly classified')
            context = child.get('source_context', {})
            if tuple(context.get(k) for k in ('input_mask', 'output_mask', 'preserve_mask')) != (0x7ff, 0x7ff, 0x472):
                raise ValueError('Stale fatal source capability')
    for caller, (_, _, end) in SOURCE.items():
        decoded = {i.address: i for i in instructions(program, caller, end)}
        edges = {row['pc']: row for row in rows if row['caller'] == caller}
        for row in edges.values():
            check_original_call(row, decoded)
            target = row['target']
            signature = (('cdecl', SOURCE[target][0], SOURCE[target][1]) if target in SOURCE else
                         PHYSICAL[target][:3] if target in PHYSICAL else MISSING[target])
            if (row['count'], row['stdcall']) != (signature[1], signature[0] == 'stdcall'):
                raise ValueError('Edge ABI/stack pop mismatch')
        stack_frames(caller, decoded, edges)


def check_roots(source, program):
    anchor = 'enum CrtRoot: UInt32 {'
    if source.count(anchor) != 1:
        raise ValueError('Missing or ambiguous prepared CRT root enum')
    block = source.split(anchor, 1)[1].split('\n    }', 1)[0] + '\n    }'
    definitions, properties = block.split('var count:', 1)
    pattern = re.compile(r'case (\w+) = (0x[0-9a-f]+)(?:, (\w+) = (0x[0-9a-f]+))?')
    roots = {}
    for match in pattern.finditer(definitions):
        a, b, c, d = match.groups()
        for name, address in ((a, b), (c, d)):
            if name is not None:
                if name in roots:
                    raise ValueError('Duplicate CRT root')
                roots[name] = int(address, 16)
    if pattern.sub('', definitions).strip() or roots != {k: v[0] for k, v in ROOTS.items()}:
        raise ValueError('Prepared root functions differ from reviewed set')
    count, returns = properties.split('var returnPC:', 1)
    if re.sub(r'\s+', '', count) != 'UInt32{[.register,.append,.acquire,.release].contains(self)?1:0}':
        raise ValueError('Prepared root argument ABI mismatch')
    pattern = re.compile(r'case \.(\w+): return (0x[0-9a-f]+)')
    matches = pattern.findall(returns)
    mapping = {name: int(address, 16) for name, address in matches}
    if len(matches) != len(mapping) or mapping != {k: v[1] for k, v in ROOTS.items()}:
        raise ValueError('Prepared root continuation mismatch')
    if re.sub(r'\s+', '', pattern.sub('', returns)) != 'UInt32{switchself{}}}':
        raise ValueError('Unknown prepared CRT root syntax')
    # These are original CALL witnesses for prepared unit invocations. Checking
    # them does not admit or authorize executing their surrounding caller.
    for caller, pc, continuation, target in [
        (0x4a7d40, 0x4a7d41, 0x4a7d46, 0x4a7b90),
        (0x425200, 0x425205, 0x42520a, 0x4a35f0),
    ]:
        decoded = {i.address: i for i in instructions(program, caller, continuation)}
        check_original_call(dict(caller=caller, pc=pc, continuation=continuation, target=target), decoded)
    indirect = {i.address: i for i in instructions(program, 0x4a5880, 0x4a5896)}[0x4a5894]
    if indirect.mnemonic != 'call' or indirect.size != 2 or indirect.operands[0].type != X86_OP_REG or indirect.operands[0].reg != X86_REG_EAX:
        raise ValueError('Wrong prepared initializer callback witness')
    section = next(s for s in program.sections if s.address <= 0x52224c < s.address + len(s.data))
    offset = 0x52224c - section.address
    if int.from_bytes(section.data[offset:offset+4], 'little') != 0x4a3610:
        raise ValueError('Wrong pinned initializer table entry')
    return len(roots)


LEAF_FIELDS = ('function', 'callback', 'pc', 'continuation', 'popECX')


def leaf_contracts(source):
    anchor = 'private static let crtRegistrationLeaves: [CrtRegistrationLeaf] = ['
    if source.count(anchor) != 1:
        raise ValueError('Missing or ambiguous closed registration leaf table')
    block = source.split(anchor, 1)[1].split('\n    ]', 1)[0]
    pattern = re.compile(r'\.init\(function: (0x[0-9a-f]+), callback: (0x[0-9a-f]+), '
                         r'callPC: (0x[0-9a-f]+), continuation: (0x[0-9a-f]+), popECX: (true|false)\),')
    rows = [dict(zip(LEAF_FIELDS, (*[int(v,16) for v in match.groups()[:4]],match[5]=='true')))
            for match in pattern.finditer(block)]
    if not rows or pattern.sub('',block).strip():
        raise ValueError('Unrecognized finite registration leaf syntax')
    return rows


def original_bytes(program, address, count):
    section = next((s for s in program.sections if s.address <= address and
                    address + count <= s.address + len(s.data)),None)
    if section is None:
        raise ValueError('Original metadata is not file-backed')
    return section.data[address-section.address:address-section.address+count]


def original_leaves(program):
    import struct
    md = Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
    table = struct.unpack('<144I',original_bytes(program,0x522004,144*4))
    if len(set(table)) != 144 or not all(program.in_text(a) for a in table):
        raise ValueError('Wrong pinned static constructor table')
    leaves = []
    for wrapper in table:
        prefix = list(md.disasm(original_bytes(program,wrapper,12),wrapper))
        first = prefix[0]
        if first.mnemonic == 'jmp':
            if first.operands[0].type != X86_OP_IMM or not program.in_text(first.operands[0].imm):
                raise ValueError('Unknown original non-registration wrapper')
            continue
        if (len(prefix) < 2 or first.mnemonic != 'call' or first.operands[0].type != X86_OP_IMM or
                not program.in_text(first.operands[0].imm) or prefix[1].mnemonic != 'jmp' or
                prefix[1].operands[0].type != X86_OP_IMM):
            raise ValueError('Unknown original constructor-to-registration wrapper')
        function = prefix[1].operands[0].imm
        decoded = list(md.disasm(original_bytes(program,function,14),function))
        if len(decoded) < 4:
            raise ValueError('Incomplete original registration body')
        push,call,cleanup,ret = decoded[:4]
        pop = (cleanup.mnemonic == 'pop' and cleanup.operands[0].type == X86_OP_REG and
               cleanup.operands[0].reg == X86_REG_ECX and cleanup.size == 1)
        add = (cleanup.mnemonic == 'add' and len(cleanup.operands) == 2 and
               cleanup.operands[0].type == X86_OP_REG and cleanup.operands[0].reg == X86_REG_ESP and
               cleanup.operands[1].type == X86_OP_IMM and cleanup.operands[1].imm == 4 and cleanup.size == 3)
        if not (push.mnemonic == 'push' and push.size == 5 and push.operands[0].type == X86_OP_IMM and
                call.mnemonic == 'call' and call.address == function+5 and call.size == 5 and
                call.operands[0].type == X86_OP_IMM and call.operands[0].imm == 0x4a35f0 and
                cleanup.address == function+10 and (pop or add) and ret.mnemonic == 'ret' and
                not ret.operands and ret.size == 1 and ret.address == function+(11 if pop else 13)):
            raise ValueError('Not a complete original registration leaf')
        callback = push.operands[0].imm & 0xffffffff
        if not program.in_text(callback):
            raise ValueError('Original leaf callback is not code')
        leaves.append(dict(zip(LEAF_FIELDS,(function,callback,function+5,function+10,pop))))
    if len(leaves) != 126 or len({row['function'] for row in leaves}) != 126:
        raise ValueError('Wrong original reachable registration leaf set')
    return leaves


def check_leaves(rows, program, registry):
    expected = original_leaves(program)  # Independent original table order.
    keys = set()
    for row in rows:
        if set(row) != set(LEAF_FIELDS) or any(type(row[k]) is not int for k in LEAF_FIELDS[:-1]) or type(row['popECX']) is not bool:
            raise ValueError('Malformed registration leaf row')
        if row['function'] in keys:
            raise ValueError('Ambiguous registration leaf identity')
        keys.add(row['function'])
    # The host does lookup by function, not iteration; replay order is a separate
    # dynamic obligation. Compare the exact independently derived finite set.
    if sorted(tuple(r[k] for k in LEAF_FIELDS) for r in rows) != sorted(tuple(r[k] for k in LEAF_FIELDS) for r in expected):
        raise ValueError('Host registration leaves differ from original reachable set')
    for row in expected:
        entry = registry.get(row['function'],{});context=entry.get('source_context',{})
        if (entry.get('family'),entry.get('convention'),entry.get('argc'),entry.get('returns'),
            context.get('input_mask'),context.get('output_mask'),context.get('preserve_mask'),context.get('optional',False)) != (
                'static_exit_registrations','cdecl',0,'void',0x7ff,0x7ff,0x472,False):
            raise ValueError('Missing or stale admitted registration leaf capability')
        edge = dict(caller=row['function'],pc=row['pc'],continuation=row['continuation'],
                    target=0x4a35f0,delta=8,count=1,stdcall=False)
        end = row['function'] + (12 if row['popECX'] else 14)
        decoded={i.address:i for i in instructions(program,row['function'],end)}
        check_original_call(edge,decoded)
        stack_frames(row['function'],decoded,{row['pc']:edge})
    return expected


def check_leaf_witness(source):
    anchor = 'private func invokeCrtRegistrationLeaf('
    if source.count(anchor) != 1:
        raise ValueError('Missing or ambiguous prepared leaf invocation')
    block = source.split(anchor,1)[1].split('\n    }',1)[0]
    compact = re.sub(r'\s+','',block)
    if 'returninvokeCrtPreparedRoot(graph,function:function,count:0,returnPC:0x4a5896,context:&context)' not in compact:
        raise ValueError('Wrong prepared registration outer return witness')


def main():
    program = claw()  # Hash verification precedes every original byte read.
    host = ROOT / 'Sources/ClawNativeCanonicalHost.swift'
    host_data = host.read_bytes()
    manifest_data = {p: p.read_bytes() for p in sorted(gen_project.FAMILIES.glob('*.json'))}
    manifests = [json.loads(data) for data in manifest_data.values()]
    exclusions = gen_project.EXCLUDE_FILE.read_bytes()
    registry = {r['address']: r for r in gen_project.canonical_inventory(manifests, json.loads(exclusions))[2]}
    rows = contracts(host_data.decode())
    check(rows, program, registry, manifests)
    root_count = check_roots(host_data.decode(), program)
    leaves = leaf_contracts(host_data.decode()) if '--leaves' in sys.argv[1:] else []
    original_leaf_rows = check_leaves(leaves,program,registry) if leaves else []
    if leaves:
        check_leaf_witness(host_data.decode())
    rejected = 0

    def reject(body):
        nonlocal rejected
        try:
            body()
        except ValueError:
            rejected += 1
        else:
            raise AssertionError('Tampered CRT metadata accepted')

    for field, value in [('caller', 0), ('pc', rows[0]['pc']+1), ('continuation', rows[0]['continuation']+1),
                         ('target', 0x4a49b0), ('delta', rows[0]['delta']+4), ('count', 2), ('stdcall', True)]:
        changed = deepcopy(rows); changed[0][field] = value
        reject(lambda: check(changed, program, registry, manifests))
    reject(lambda: check(rows + [deepcopy(rows[0])], program, registry, manifests))
    anchor = 'private static let crtEdges: [CrtEdge] = ['
    prefix, edge_source = host_data.decode().split(anchor, 1)
    for before, after in [('stdcall: false', 'stdcall: maybe'), ('count: 1', 'count: -1'),
                          ('target: 0x4a48e0', 'target: bogus'),
                          ('.init(caller:', '.unknown(caller:')]:
        reject(lambda before=before, after=after: contracts(prefix + anchor + edge_source.replace(before, after, 1)))
    reject(lambda: contracts(host_data.decode().replace(anchor, anchor.replace('crtEdges', 'typo'), 1)))
    for before, after in [('case register = 0x4a35f0', 'case register = 0x425200'),
                          ('case .register: return 0x42520a', 'case .register: return 0x42520b'),
                          ('[.register,.append,.acquire,.release]', '[.register,.append]')]:
        reject(lambda before=before, after=after: check_roots(host_data.decode().replace(before, after, 1), program))
    for field, value in [('convention', 'stdcall'), ('argc', 2), ('returns', 'void')]:
        changed = deepcopy(registry); changed[0x4a3610][field] = value
        reject(lambda: check(rows, program, changed, manifests))
    for field in ('input_mask', 'output_mask', 'preserve_mask', 'optional'):
        changed = deepcopy(registry); changed[0x4a7bc0]['source_context'][field] = True if field == 'optional' else 0
        reject(lambda: check(rows, program, changed, manifests))
    changed = deepcopy(registry); del changed[0x4a3560]
    reject(lambda: check(rows, program, changed, manifests))
    changed = deepcopy(registry); changed[0x4a4860] = dict(changed[0x4a7bc0])
    reject(lambda: check(rows, program, changed, manifests))
    for address, field, value in [(0x4a48e0, 'kind', 'whole'), (0x546aa4, 'convention', 'cdecl'),
                                  (0x4a4860, 'kind', 'fixture')]:
        changed = deepcopy(manifests)
        manifest = next(m for m in changed if m.get('id') == 'crt_exit_registry')
        manifest['callees'][hex(address)][field] = value
        reject(lambda: check(rows, program, registry, changed))
    cached = next(r for r in rows if r['caller'] == 0x4a7b90)
    wrong = dict(cached, target=0x546aac)
    decoded = {i.address: i for i in instructions(program, 0x4a7b90, 0x4a7bbb)}
    reject(lambda: check_original_call(wrong, decoded))
    wrong = dict(next(r for r in rows if r['pc'] == 0x4a7c2d), target=0x546a9c)
    decoded = {i.address: i for i in instructions(program, 0x4a7bc0, 0x4a7c36)}
    reject(lambda: check_original_call(wrong, decoded))
    changed = deepcopy(program); changed.imports[0x546aa4] = 'KERNEL32.dll!EnterCriticalSection'
    reject(lambda: check(rows, changed, registry, manifests))
    if leaves:
        for field,value in [('function',0x501fbd),('callback',leaves[0]['callback']+1),
                            ('pc',leaves[0]['pc']+1),('continuation',leaves[0]['continuation']+1),
                            ('popECX',not leaves[0]['popECX'])]:
            changed=deepcopy(leaves);changed[0][field]=value
            reject(lambda:check_leaves(changed,program,registry))
        reject(lambda:check_leaves(leaves[:-1],program,registry))
        reject(lambda:check_leaves(leaves+[deepcopy(leaves[0])],program,registry))
        for field,value in [('family','crt_exit_registry'),('argc',1),('convention','stdcall'),('returns','u32')]:
            changed=deepcopy(registry);changed[leaves[0]['function']][field]=value
            reject(lambda:check_leaves(leaves,program,changed))
        for field in ('input_mask','output_mask','preserve_mask','optional'):
            changed=deepcopy(registry);changed[leaves[0]['function']]['source_context'][field]=True if field=='optional' else 0
            reject(lambda:check_leaves(leaves,program,changed))
        changed=deepcopy(registry);del changed[leaves[0]['function']]
        reject(lambda:check_leaves(leaves,program,changed))
        reject(lambda:leaf_contracts(host_data.decode().replace('popECX: true','popECX: invalid',1)))
        reject(lambda:check_leaf_witness(host_data.decode().replace('returnPC:0x4a5896','returnPC:0x4a5897',1)))
    used = {registry[a]['family'] for a in SOURCE}
    if leaves:used.add('static_exit_registrations')
    inputs = {str(host.relative_to(ROOT)): hashlib.sha256(host_data).hexdigest(),
              str(Path(__file__).relative_to(ROOT)): hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              str(gen_project.EXCLUDE_FILE.relative_to(ROOT)): hashlib.sha256(exclusions).hexdigest()}
    inputs.update({str(p.relative_to(ROOT)): hashlib.sha256(data).hexdigest()
                   for p, data in manifest_data.items() if json.loads(data).get('id') in used})
    # The full inventory also establishes the absence of an admitted fatal
    # child; retain provenance for every manifest, not only positive owners.
    inventory_inputs = {str(p.relative_to(ROOT)): hashlib.sha256(data).hexdigest()
                        for p, data in manifest_data.items()}
    inventory_digest = hashlib.sha256(json.dumps(inventory_inputs, sort_keys=True).encode()).hexdigest()
    print(json.dumps(dict(status='pass', edges=len(rows), source_entries=len(SOURCE), prepared_roots=root_count,
                         physical_services=len(PHYSICAL), missing_source_stops=len(MISSING),
                         registration_leaves=len(leaves),
                         original_registration_order_sha256=hashlib.sha256(json.dumps(original_leaf_rows,sort_keys=True).encode()).hexdigest() if leaves else None,
                         rejected_metadata_mutations=rejected, input_sha256=inputs,
                         manifest_inventory_sha256=inventory_digest,
                         program_sha256=program.sha256,
                         scope='original CALL/ABI/static bounded frame metadata; dynamic CPU/frame/ownership remain replay checks')))


if __name__ == '__main__':
    main()
