"""Scene-attached Siren against the authenticated original callback.

Only physical allocation and resource dictionaries are intercepted. Constructors,
virtual lifecycle methods, state lookup and animation execute original code.
"""
import json
import struct
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x489730
from Tests.NativeObjectConnections.cut_throat_transport import normalize_calls
# These helpers are inlined in already admitted canonical owners. Descendants
# and bytes are still compared; no game behavior is replaced here.
OBSERVE = {0x405000,0x44cfd0,0x43e9b0,0x489c50,0x48a160,0x489850,0x48a2e0,0x44d3c0,0x4c96b0,0x4dc870,0x4f63ec,0x4f6428,0x4f6439,0x4dbe10,0x4dbd60,0x48ce40}


def prepare(directory):
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
        if name == 'LEVEL11/WORLDS/WORLD.WWD':
            (directory / 'WORLD11.WWD').write_bytes(payload)
        if name.startswith(('LEVEL11/IMAGES/SIREN/', 'LEVEL11/ANIS/SIREN/', 'LEVEL11/SOUNDS/SIREN/')):
            target = level / name.removeprefix('LEVEL11/')
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink():
                assert target.read_bytes() == payload, name
            else:
                assert not target.parent.is_symlink()
                target.write_bytes(payload)
            found.append(name)
    assert any('/IMAGES/' in name for name in found), 'Missing original Siren image set'
    assert any('/ANIS/' in name for name in found), 'Missing original Siren animations'
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
    reviewed = [(0x50f694,100),(0x50f688,8),(0x50e0c0,8),
                (0x513740,40),(0x5139a0,4),(0x5139e8,4),
                (0x50b090,24),(0x513e48,16),(0x513e10,16),(0x513e40,4),(0x52e1c8,4),(0x522d54,9),(0x522d48,12),(0x5234ec,8),(0x523148,8)]
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
    assert {'LEVEL_SIREN', 'LEVEL_SIREN_IDLE'} <= {name for _, name in bindings}
    assert all(token for (receiver,name),token in bindings.items() if name.startswith('LEVEL_SIREN'))
    random_values = iter(profile['randomValues'])
    calls, services, allocated = [], [], []
    def observed(m, address):
        sp = m.register(UC_X86_REG_ESP)
        receiver = 0 if address in (0x4f63ec, 0x4dc870, 0x4f6428, 0x48cf50, 0x48ce40) else m.register(UC_X86_REG_ECX)
        calls.append([address, receiver])
    for function in OBSERVE:
        machine.observe(function, observed)
    machine.intercept(0x4A48E0)
    machine.intercept(0x4F6286)
    machine.intercept(0x4a3050)
    machine.intercept(0x4a49b0)
    freed = []
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
            freed.append(token); m.return_from_external(0,0)
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
    assert allocated and allocated[0]['count'] == 0x4b0, allocated
    assert next(allocations, None) is None and next(random_values, None) is None
    assert [step['command'] for step in profile['steps'][:4]] == [0, 1000, 29, 30]
    assert profile['steps'][4]['command'] not in (0,1000,29,30)
    retired = None
    if profile['retire']:
        result = machine.call(0x48a0d0,ecx=profile['helper'],arguments=[1])
        assert result.completed and profile['helper'] in freed
        retired = machine.read(profile['helper'],0x4b0).hex()
    return dict(name=profile['name'], steps=outputs, retired=retired, executable_sha256=program.sha256)


def compare(directory):
    source = json.loads((directory / 'siren-native-input.json').read_text())
    native = json.loads((directory / 'siren-native-output.json').read_text())
    assert len(source['profiles']) == len(native['profiles']) == 2
    original = [reference(profile) for profile in source['profiles']]
    (directory / 'siren-original-output.json').write_text(json.dumps(original, indent=2)+'\n')
    comparisons = 0
    for expected, actual in zip(original, native['profiles'], strict=True):
        assert expected['name'] == actual['name']
        for ref, got in zip(expected['steps'], actual['steps'], strict=True):
            assert normalize_calls([[f,r,[]] for f,r in ref['calls']]) == normalize_calls([[f,r,[]] for f,r in got['calls']]), (actual['name'],got['command'],'ordered calls')
            for key in ('command', 'services', 'spans'):
                assert ref[key] == got[key], (actual['name'], got['command'], key, ref[key] if key != 'spans' else 'see original output', got[key] if key != 'spans' else 'see native output')
            comparisons += 1
        assert expected["retired"] == actual["retired"], "Original destructor bytes"
    expected_owners = OBSERVE - {0x4f6428}
    actual_owners = {a for p in native['profiles'] for s in p['steps'] for a, _ in s['calls']}
    assert expected_owners <= actual_owners
    trace = native['trace']
    positions = [trace.index(value) for value in ['loadGridObject', 'scene.gameplay', 'ClawNativeSiren', '0x489730']]
    assert positions == sorted(positions)
    assert any('ClawActorResources' in event for event in trace)
    assert 'ClawNativeCanonicalHost.0x48a0d0' in trace
    required = {'canonical_release_publishes_real_holder_state','scene_destruction_retires_owner','same_scene_recreates_actor_and_helper','retired_helper_rejected','missing_resource_service_rejected','replacement_actor_rejected','foreign_helper_rejected','service_outside_callback_rejected'}
    assert required <= native['controls'].keys() and all(native['controls'].values()), native['controls']
    assert native['faults'] == 0 and not native['unresolvedDependencies']
    return dict(original_callback='0x489730', native_owner='ClawNativeSiren', comparisons=comparisons,
                exercised_service_edges=[f'0x{function:x}' for function in sorted(actual_owners | {0x4F6286, 0x4A48E0, 0x4F6974, 0x48a0d0})],
                controls=native['controls'], faults=0, unresolved_dependencies=[],
                evidence='Unmodified Level 11 WWD Siren at original coordinates, isolated scene attachment without spatial membership, genuine disc image/animation resources, real constructor/virtual owners and scene destruction; no Level 11 startup or live-play claim')

