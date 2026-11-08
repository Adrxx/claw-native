"""Scene-attached TownGuard1 against the authenticated original callback.

Only physical allocation and resource dictionaries are intercepted. Constructors,
virtual lifecycle methods, state lookup and animation execute original code.
"""
import json
import struct
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x496050
from Tests.NativeObjectConnections.town_guard1_transport import OBSERVE as TRANSPORT_OBSERVE, boundary_metadata
# These helpers are inlined in already admitted canonical owners. Descendants
# and bytes are still compared; no game behavior is replaced here.
OBSERVE = (set(TRANSPORT_OBSERVE) | {0x43e9b0,0x48cf50,0x4c81b0,0x4c8160}) - {0x44bc60, 0x4f6286, 0x4dca10, 0x496840}


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
        if name == 'LEVEL5/WORLDS/WORLD.WWD':
            (directory / 'WORLD5.WWD').write_bytes(payload)
        if name.startswith(('LEVEL5/IMAGES/TOWNGUARD1/', 'LEVEL5/ANIS/TOWNGUARD1/')):
            target = level / name.removeprefix('LEVEL5/')
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink() or target.parent.is_symlink():
                raise AssertionError('Refuse to overwrite shared resource symlink')
            target.write_bytes(payload)
            found.append(name)
    assert any('/IMAGES/' in name for name in found), 'Missing original cannon image set'
    assert any('/ANIS/' in name for name in found), 'Missing original cannon animations'
    (directory / 'physical-assets.json').write_text(json.dumps(dict(asset_sha256=verify_assets(), files=found, **boundary_metadata()), indent=2)+'\n')


def string(machine, address):
    value = bytearray()
    for offset in range(256):
        byte = machine.read(address + offset, 1)
        if byte == b'\0':
            return value.decode('ascii')
        value.extend(byte)
    raise AssertionError('Unterminated physical dictionary key')


def reference(profile, *, stop_at_secondary_allocation=False):
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
    reviewed = [(0x50fabc, 40), (0x50fb04, 4), (0x513740, 40), (0x533470, 4),
                (0x5139a0, 4), (0x5139e8, 4), (0x50b090, 24),
                (0x513e10, 16), (0x513e40, 4), (0x513e48, 16),
                (0x50e008, 8), (0x50e0c0, 4), (0x50fab0, 4)]
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
    if not stop_at_secondary_allocation:
        assert {'LEVEL_TOWNGUARD1', 'LEVEL_TOWNGUARD1_STRIKE1'} <= {name for _, name in bindings}
    random_values = iter(profile['randomValues'])
    calls, services, allocated = [], [], []
    secondary_entry = None
    secondary_boundary = None
    secondary_binder = None
    def observed(m, address):
        nonlocal secondary_entry, secondary_boundary, secondary_binder
        sp = m.register(UC_X86_REG_ESP)
        receiver = 0 if address in (0x4f63ec, 0x4dc870, 0x4f6428, 0x48cf50) else m.register(UC_X86_REG_ECX)
        calls.append([address, receiver])
        if address in (0x4c7fa0,0x4c8060):
            secondary_entry = dict(function=address, receiver=receiver,
                argument=m.words(sp+4,1)[0], return_pc=m.words(sp,1)[0])
        if stop_at_secondary_allocation and address in (0x4c7f20,0x4c7fe0):
            assert secondary_entry is not None
            continuation = m.words(sp,1)[0]
            instruction = m.read(continuation-5,5)
            assert instruction[0] == 0xe8
            assert ((continuation+struct.unpack('<i',instruction[1:])[0])&0xffffffff) == address
            expected_root = 0x4c7fa0 if address == 0x4c7f20 else 0x4c8060
            assert secondary_entry['function'] == expected_root
            secondary_binder = dict(function=address, receiver=receiver,
                call_pc=continuation-5, continuation=continuation)
            if address == 0x4c7f20:
                assert secondary_binder['call_pc'] == 0x4c7fcb and continuation == 0x4c7fd0
        if stop_at_secondary_allocation and address == 0x4f63ec and m.words(sp+4,1)[0] == 0x174:
            assert secondary_entry is not None and secondary_binder is not None, 'Original secondary binder must precede allocation'
            continuation = m.words(sp,1)[0]
            call_pc = continuation-5
            instruction = m.read(call_pc,5)
            assert instruction[0] == 0xe8
            target = (continuation+struct.unpack('<i',instruction[1:])[0]) & 0xffffffff
            assert target == 0x4f63ec
            assert (secondary_binder["function"],continuation) in ((0x4c7f20,0x4c7f4f),(0x4c7fe0,0x4c800f))
            secondary_boundary = dict(consumer=secondary_entry, binder=secondary_binder, call_pc=call_pc,
                continuation=continuation, target=target, convention='cdecl', arguments=[0x174],
                stack_pointer=sp, stack_words=list(m.words(sp,8)),
                actor=actor, actor_logic=state,
                actor_hit=m.words(actor+0x70,1)[0], actor_attack=m.words(actor+0x78,1)[0])
            # Stop before the original allocator executes. No made-up allocation
            # or game return is supplied beyond the demonstrated missing join.
            m.uc.emu_stop()
    for function in OBSERVE | ({0x4c7f20,0x4c7fe0} if stop_at_secondary_allocation else set()):
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
        if stop_at_secondary_allocation:
            assert secondary_boundary is not None, ('Secondary allocation was not reached', result)
            assert not result.completed, 'Diagnostic must stop at the boundary, not complete gameplay'
            return dict(status='original-boundary-witness', executable_sha256=program.sha256,
                original_callback=CALLBACK, boundary=secondary_boundary, calls=calls,
                physical_services=services, completed_callback=False, native_comparison=False,
                host_wired=False, source_profile=profile['name'])
        assert result.completed, (profile['name'], step['command'], result)
        outputs.append(dict(command=step['command'], calls=list(calls), services=list(services),
            spans=[dict(address=span['address'], hex=machine.read(span['address'], span['count']).hex()) for span in step['spans']]))
    assert allocated and allocated[0]['count'] == 0x498, allocated
    assert next(allocations, None) is None and next(random_values, None) is None
    assert [step['command'] for step in profile['steps'][:4]] == [0, 1000, 29, 30]
    assert profile['steps'][4]['command'] not in (0,1000,29,30)
    retired = None
    if profile['retire']:
        result = machine.call(0x496840,ecx=profile['helper'],arguments=[1])
        assert result.completed and profile['helper'] in freed
        retired = machine.read(profile['helper'],0x498).hex()
    return dict(name=profile['name'], steps=outputs, retired=retired, executable_sha256=program.sha256)


def compare(directory):
    source = json.loads((directory / 'town-native-input.json').read_text())
    native = json.loads((directory / 'town-native-output.json').read_text())
    assert len(source['profiles']) == len(native['profiles']) == 2
    for profile in source['profiles']:
        actor = bytes.fromhex(next(s['hex'] for s in profile['segments'] if s['address'] == profile['actor']))
        assert struct.unpack_from('<I', actor, 0x70)[0] == 0
        assert struct.unpack_from('<I', actor, 0x78)[0] == 0
        assert [a['count'] for a in profile['allocations'][:3]] == [0x498, 0x174, 0x174]
    original = [reference(profile) for profile in source['profiles']]
    (directory / 'town-original-output.json').write_text(json.dumps(original, indent=2)+'\n')
    comparisons = 0
    for expected, actual in zip(original, native['profiles'], strict=True):
        assert expected['name'] == actual['name']
        for ref, got in zip(expected['steps'], actual['steps'], strict=True):
            # Native caller frames own different physical stack addresses.
            # Preserve the order and aliasing of the single synchronous bitset
            # temporary, as the prerequisite transport comparison does.
            from Tests.NativeObjectConnections.town_guard1_transport import cut
            ref['calls'] = [row[:2] for row in cut.normalize_calls([[f, r, []] for f, r in ref['calls']])]
            got['calls'] = [row[:2] for row in cut.normalize_calls([[f, r, []] for f, r in got['calls']])]
            for key in ('command', 'calls', 'services', 'spans'):
                assert ref[key] == got[key], (actual['name'], got['command'], key, ref[key] if key != 'spans' else 'see original output', got[key] if key != 'spans' else 'see native output')
            comparisons += 1
        assert expected["retired"] == actual["retired"], "Original destructor bytes"
    expected_owners = {0x4f63ec,0x496110,0x405000,0x44cfd0,0x4c96b0,0x4dc870,0x497130,0x497a50,0x43dfa0}
    actual_owners = {a for p in native['profiles'] for s in p['steps'] for a, _ in s['calls']}
    assert expected_owners <= actual_owners
    trace = native['trace']
    positions = [trace.index(value) for value in ['loadGridObject', 'scene.gameplay', 'ClawNativeTownGuard1', '0x496050']]
    assert positions == sorted(positions)
    assert any('ClawActorResources' in event for event in trace)
    assert 'ClawNativeTownGuard1.retire.0x496840' in trace
    required = {'scene_destruction_retires_owner','same_scene_recreates_actor_and_helper','retired_helper_rejected','missing_resource_service_rejected','replacement_actor_rejected','foreign_helper_rejected','service_outside_callback_rejected'}
    assert required <= native['controls'].keys() and all(native['controls'].values()), native['controls']
    assert native['faults'] == 0 and not native['unresolvedDependencies']
    return dict(original_callback='0x496050', native_owner='ClawNativeTownGuard1', comparisons=comparisons,
                exercised_service_edges=[f'0x{function:x}' for function in sorted(actual_owners | {0x4F6286, 0x4A48E0, 0x4F6974, 0x496840, 0x4F4680})],
                controls=native['controls'], faults=0, unresolved_dependencies=[],
                evidence='Actual Level 5 WWD actor with original TownGuard1 resources in the existing native scene; no live-play claim')


def allocation_boundary_witness(directory):
    """Run only when the coordinator elects this original-only diagnostic.

    Native scene inputs and services lead up to the unsupported join. The
    original stops on entry to operator new before that missing join executes.
    """
    source = json.loads((directory / 'town-active-input.json').read_text())
    failure = json.loads((directory / 'town-failed-callback.json').read_text())
    assert source['command'] == failure['command'] == 0
    assert any(row[0] == 0x4c7fa0 for row in failure['calls'])
    profile = dict(source, allocations=failure['allocations'], resourceBindings=failure['resourceBindings'],
        randomValues=failure['randomValues'], steps=[dict(command=0,inputGlobals=source['inputGlobals'],spans=[])])
    witness = reference(profile, stop_at_secondary_allocation=True)
    witness['native_failure'] = {key: failure[key] for key in ('fault','sceneFault','unresolvedDependencies')}
    (directory / 'town-secondary-allocation-witness.json').write_text(json.dumps(witness,indent=2)+'\n')
    return witness
