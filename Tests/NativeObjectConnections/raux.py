"""Scene-attached Raux against the authenticated original callback.

Only physical allocation and resource dictionaries are intercepted. Constructors,
virtual lifecycle methods, state lookup and animation execute original code.
"""
import json
import struct
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x47e210
from Tests.NativeObjectConnections.cut_throat_transport import normalize_calls
# These helpers are inlined in already admitted canonical owners. Descendants
# and bytes are still compared; no game behavior is replaced here.
OBSERVE = {0x40e0d0,0x44c000,0x40e1b0,0x40e5b0,0x4c96b0,0x4dc870,0x47ece0,0x47e8e0,0x47f0c0,0x40e280,0x40e580,0x44d3c0,0x47e7f0,0x4f63ec,0x4f6428}


def audit_callback():
    # Authenticate the exact allocation, constructor and retained-dispatch joins.
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    program = claw()
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    for address, target in ((0x47e248,0x4f63ec),(0x47e263,0x47e2d0),(0x47e29c,0x4dc870)):
        section = next(s for s in program.sections if s.address <= address < s.address+s.size)
        instruction = next(decoder.disasm(section.data[address-section.address:address-section.address+5], address))
        assert instruction.mnemonic == 'call' and instruction.op_str == hex(target) and instruction.size == 5


def prepare(directory):
    audit_callback()
    directory = directory.resolve()
    root = directory / 'resources'
    root.mkdir(exist_ok=True)
    source = (ROOT / 'App/GameData').resolve()
    def link_tree(target, child):
        # Foundation directory enumeration requires real directories here.
        # Remove an overlay link itself before descending; never mutate its target.
        assert target.parent.resolve().is_relative_to(root), target
        if child.is_dir():
            if target.is_symlink():
                target.unlink()
            target.mkdir(exist_ok=True)
            for entry in child.iterdir():
                link_tree(target / entry.name, entry)
        else:
            if target.is_symlink() and not target.exists():
                target.unlink()
            if not target.exists():
                target.symlink_to(child.resolve())
    for child in source.iterdir():
        link_tree(root / child.name, child)
    level = root / 'LEVEL1'
    found = []
    for name, payload in entries():
        if name == 'LEVEL2/WORLDS/WORLD.WWD':
            (directory / 'WORLD2.WWD').write_bytes(payload)
        if name.startswith(('LEVEL2/IMAGES/RAUX/', 'LEVEL2/ANIS/RAUX/', 'LEVEL2/SOUNDS/RAUX/')):
            target = level / name.removeprefix('LEVEL2/')
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink():
                assert target.read_bytes() == payload, name
            else:
                assert not target.parent.is_symlink()
                target.write_bytes(payload)
            found.append(name)
    assert any('/IMAGES/' in name for name in found), 'Missing original Raux image set'
    assert any('/ANIS/' in name for name in found), 'Missing original Raux animations'
    (directory / 'physical-assets.json').write_text(json.dumps(dict(asset_sha256=verify_assets(), files=found, executable_sha256=claw().sha256), indent=2)+'\n')


def string(machine, address):
    value = bytearray()
    for offset in range(256):
        byte = machine.read(address + offset, 1)
        if byte == b'\0':
            return value.decode('ascii')
        value.extend(byte)
    raise AssertionError('Unterminated physical dictionary key')


def reference(profile):
    program = claw()
    machine = Machine(program, 0x10000000, 4096)
    mapped = {0x10000000}
    def map_span(address, size):
        for page in range(address & ~4095, (address + size + 4095) & ~4095, 4096):
            if page in mapped or any(begin <= page <= end for begin, end, _ in machine.uc.mem_regions()):
                continue
            machine.uc.mem_map(page, 4096)
            mapped.add(page)
    imports = {slot: machine.read(slot, 4) for slot in machine.import_stub}
    reviewed = [(0x50bac8,8),(0x50ba88,8),(0x50f178,8),(0x50f1ac,180),(0x513740,40),(0x5139a0,4),(0x5139e8,4),(0x50b090,24),(0x513e48,16),(0x513e10,16),(0x513e40,4),(0x52e1c8,4)]
    original_metadata = {address: machine.read(address, size) for address, size in reviewed}
    for segment in profile['segments']:
        address, data = segment['address'], bytes.fromhex(segment['hex'])
        map_span(address, len(data))
        machine.write(address, data)
    for address, data in original_metadata.items():
        assert machine.read(address, len(data)) == data, f'Native metadata differs from original at {address:#x}'
    for address, data in imports.items(): machine.write(address, data)
    actor, state = profile['actor'], profile['state']
    allocations = iter(profile['allocations'])
    bindings = {(b['receiver'], b['name']): b['token'] for b in profile['resourceBindings']}
    assert len(bindings) == len(profile['resourceBindings'])
    assert {'LEVEL_RAUX'} <= {name for _, name in bindings}
    random_values = iter(profile['randomValues'])
    calls, services, allocated = [], [], []
    def observed(m, address):
        sp = m.register(UC_X86_REG_ESP)
        receiver = 0 if address in (0x4f63ec, 0x4dc870, 0x4f6428, 0x48cf50, 0x464f20, CALLBACK) else m.register(UC_X86_REG_ECX)
        calls.append([address, receiver])
    for function in OBSERVE:
        machine.observe(function, observed)
    machine.intercept(0x4A48E0)
    machine.intercept(0x4F6286)
    machine.intercept(0x4a3050)
    machine.intercept(0x4a49b0)
    machine.intercept(0x4f51c5)
    machine.intercept(0x4f572a)
    freed = []
    retirements = []
    assert not profile["listNodes"]
    nodes = iter(profile["listNodes"])
    def external(m, address):
        stack = m.register(UC_X86_REG_ESP)
        arg = lambda i: m.words(stack+4+i*4, 1)[0]
        slot = next((k for k,v in m.import_stub.items() if v == address), address)
        if address == 0x4A48E0:
            count = m.words(stack + 4, 1)[0]
            row = next(allocations)
            assert count == row['count']
            allocated.append(row)
            map_span(row['token'], count)
            m.write(row['token'], b'\xcc' * count)
            services.append(['malloc', row['token'], count])
            m.return_from_external(row['token'], 0)
        elif address == 0x4F6286:
            name_token, output = m.words(stack + 4, 2)
            receiver, name = m.register(UC_X86_REG_ECX), string(m, name_token)
            token = bindings[(receiver, name)]
            m.write(output, struct.pack('<I', token))
            services.append(['registry', receiver, name, token])
            m.return_from_external(int(token != 0), 8)
        elif address == 0x4a3050:
            value = next(random_values); services.append(['rand',value]); m.return_from_external(value,0)
        elif address == 0x4a49b0:
            token = arg(0)
            assert token in [row['token'] for row in allocated] and token not in freed
            count = next(row['count'] for row in allocated if row['token']==token)
            retirements.append(dict(token=token, hex=m.read(token,count).hex()))
            freed.append(token); m.return_from_external(0,0)
        elif address in (0x4f51c5,0x4f572a):
            node=next(nodes);receiver=m.register(UC_X86_REG_ECX)
            map_span(node,12)
            following=arg(0) if address==0x4f572a else 0
            child=arg(1) if following else arg(0)
            previous=m.words(following+4 if following else receiver+8,1)[0]
            m.write(node,struct.pack('<3I',following,previous,child))
            m.write(previous if previous else receiver+4,struct.pack('<I',node))
            m.write(following+4 if following else receiver+8,struct.pack('<I',node))
            m.write(receiver+12,struct.pack('<I',m.words(receiver+12,1)[0]+1))
            services.append(['list',address,receiver,arg(0),arg(1) if address==0x4f572a else 0,node])
            m.return_from_external(node,8 if address==0x4f572a else 4)
        elif slot in (0x546d5c,0x546cdc):
            values = [arg(i) for i in range(1,5)] if slot == 0x546d5c else [0]*4
            m.write(arg(0),struct.pack('<4I',*values)); m.return_from_external(1,20 if slot == 0x546d5c else 4)
        elif slot == 0x546cd4:
            left,top,right,bottom = struct.unpack('<4i',m.read(arg(0),16))
            x,y = struct.unpack('<2i',struct.pack('<2I',arg(1),arg(2)))
            m.return_from_external(int(left <= x < right and top <= y < bottom),12)
        elif slot == 0x546d24:
            left,top,right,bottom = struct.unpack('<4I',m.read(arg(0),16))
            m.write(arg(0),struct.pack('<4I',(left-arg(1))&0xffffffff,(top-arg(2))&0xffffffff,(right+arg(1))&0xffffffff,(bottom+arg(2))&0xffffffff))
            m.return_from_external(1,12)
        elif slot == 0x546a40:
            m.read(arg(0),arg(1)); m.return_from_external(0,8)
        elif slot == 0x5469e8:
            value = (m.words(arg(0),1)[0]-1)&0xffffffff
            m.write(arg(0),struct.pack('<I',value)); m.return_from_external(value,4)
        else:
            raise AssertionError(('Unresolved physical service',hex(address),hex(slot)))
    machine.on_external = external
    machine.reset_x87(); machine.set_x87_state(0x23f,0,[])
    outputs = []
    for step in profile['steps']:
        calls.clear(); services.clear()
        machine.write(state + 0x1C, struct.pack('<I', step['command']))
        for segment in step['inputGlobals']:
            machine.write(segment['address'], bytes.fromhex(segment['hex']))
        result = machine.call(CALLBACK, arguments=[actor])
        assert result.completed, (profile['name'], step['command'], result)
        outputs.append(dict(command=step['command'], calls=list(calls), services=list(services),
            spans=[dict(address=span['address'], hex=machine.read(span['address'], span['count']).hex()) for span in step['spans']]))
    assert [row['count'] for row in allocated] == [0x478,0x174,0x174], allocated
    assert next(nodes,None) is None
    assert next(allocations, None) is None and next(random_values, None) is None
    assert [step['command'] for step in profile['steps'][:4]] == [0, 1000, 29, 30]
    assert profile['steps'][4]['command'] not in (0,1000,29,30)
    retired = None
    if profile['retire']:
        def w(a,*v): machine.write(a,struct.pack('<'+'I'*len(v),*v))
        def get(a): return machine.words(a,1)[0]
        helper=profile['helper']
        result=machine.call(0x47e7f0,ecx=helper,arguments=[1]);assert result.completed
        retired=machine.read(helper,0x478).hex()
        for offset in (0x70,0x78):
            secondary=get(actor+offset)
            if secondary:
                result=machine.call(0x4c80c0,ecx=secondary,arguments=[1]);assert result.completed
                w(actor+offset,0)
    return dict(name=profile['name'], steps=outputs, retired=retired, retirements=retirements, executable_sha256=program.sha256)



def compare(directory):
    audit_callback()
    source = json.loads((directory / 'raux-native-input.json').read_text())
    native = json.loads((directory / 'raux-native-output.json').read_text())
    assert len(source['profiles']) == len(native['profiles']) == 2
    original = [reference(profile) for profile in source['profiles']]
    (directory / 'raux-original-output.json').write_text(json.dumps(original, indent=2)+'\n')
    comparisons = 0
    for expected, actual in zip(original, native['profiles'], strict=True):
        assert expected['name'] == actual['name']
        for ref, got in zip(expected['steps'], actual['steps'], strict=True):
            assert normalize_calls([[f,r,[]] for f,r in ref['calls']]) == normalize_calls([[f,r,[]] for f,r in got['calls']]), (actual['name'],got['command'],'ordered calls')
            for key in ('command', 'services', 'spans'):
                assert ref[key] == got[key], (actual['name'], got['command'], key, ref[key] if key != 'spans' else 'see original output', got[key] if key != 'spans' else 'see native output')
            comparisons += 1
        assert expected["retired"] == actual["retired"], "Original destructor bytes"
        if "retirements" in actual: assert expected["retirements"] == actual["retirements"], "Original child/helper retirement bytes"
    expected_owners = OBSERVE - {0x4f6428, 0x47e7f0}
    actual_owners = {a for p in native['profiles'] for s in p['steps'] for a, _ in s['calls']}
    assert expected_owners <= actual_owners
    trace = native['trace']
    positions = [trace.index(value) for value in ['loadGridObject', 'scene.gameplay', 'ClawNativeRaux', '0x47e210']]
    assert positions == sorted(positions)
    assert any('ClawActorResources' in event for event in trace)
    assert 'ClawNativeCanonicalHost.0x47e7f0' in trace
    required = {'replacement_state_rejected','replacement_helper_identity_rejected','scene_destruction_retires_owner','same_scene_recreates_actor_and_helper','retired_helper_rejected','missing_resource_service_rejected','replacement_actor_rejected','foreign_helper_rejected','service_outside_callback_rejected'}
    assert required <= native['controls'].keys() and all(native['controls'].values()), native['controls']
    assert native['faults'] == 0 and not native['unresolvedDependencies']
    physical_edges = {0x4f6286,0x4a48e0,0x47e7f0,0x4f6974}
    assert 'ClawNativeStateRegistry.0x4f6974' in trace
    physical_edges.update(row[1] for profile in native['profiles'] for step in profile['steps'] for row in step['services'] if row[0]=='list')
    return dict(original_callback='0x47e210', native_owner='ClawNativeRaux', comparisons=comparisons,
                exercised_service_edges=[f'0x{function:x}' for function in sorted(actual_owners | physical_edges)],
                controls=native['controls'], faults=0, unresolved_dependencies=[],
                evidence='Unmodified Level 2 WWD Raux at original coordinates, isolated scene attachment without spatial membership, genuine disc image/animation resources, real constructor/virtual owners and scene destruction; no Level 2 startup or live-play claim')

