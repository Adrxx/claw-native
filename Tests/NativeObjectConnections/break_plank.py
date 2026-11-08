"""Scene-attached BreakPlank against the authenticated original callback.

Only physical allocation, resource dictionaries and native list handles are
intercepted. Constructors,
virtual lifecycle methods, state lookup and animation execute original code.
"""
import json
import struct
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x40F7B0
OBSERVE = (0x4F63EC, 0x40F870, 0x4C7FA0, 0x4C8060, 0x4C8160,
           0x4C81B0, 0x4C8DA0, 0x4C96B0, 0x4DC870, 0x4C9E30,
           0x40FB30, 0x4890F0, 0x4041B0)



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
        if name.startswith(('LEVEL5/IMAGES/BREAKPLANK/', 'LEVEL5/ANIS/BREAKPLANK/')):
            target = level / name.removeprefix('LEVEL5/')
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink() or target.parent.is_symlink():
                raise AssertionError('Refuse to overwrite shared resource symlink')
            target.write_bytes(payload)
            found.append(name)
    assert any('/IMAGES/' in name for name in found), 'Missing original plank image set'
    assert any('/ANIS/' in name for name in found), 'Missing original plank animations'
    (directory / 'physical-assets.json').write_text(json.dumps(dict(asset_sha256=verify_assets(), files=found), indent=2)+'\n')


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
    reviewed = [(0x50B6EC, 36), (0x50F664, 36), (0x513740, 40), (0x510020, 4)]
    reviewed += [(address, len(string(machine, address).encode('ascii')) + 1)
                 for address in (0x522D54, 0x522D48, 0x522BD4, 0x523148,
                                 0x529A48, 0x52C024, 0x52C010, 0x52BFDC, 0x52BFF4)]
    original_metadata = {address: machine.read(address, size) for address, size in reviewed}
    for segment in profile['segments']:
        address, data = segment['address'], bytes.fromhex(segment['hex'])
        map_span(address, len(data))
        machine.write(address, data)
    for address, data in original_metadata.items():
        assert machine.read(address, len(data)) == data, f'Native metadata differs from original at {address:#x}'
    actor, state = profile['actor'], profile['state']
    allocations = iter(profile['allocations'])
    bindings = {(b['receiver'], b['name']): b['token'] for b in profile['resourceBindings']}
    assert len(bindings) == len(profile['resourceBindings'])
    assert {name for _, name in bindings} >= {'LogicHit', 'LogicAttack', 'SinglePlank', 'LEVEL_BREAKPLANK', 'LEVEL_BREAKPLANK_IDLE', 'LEVEL_BREAKPLANK_CRUMBLE'}
    assert all(value for value in bindings.values()), 'Real metadata and resources must be nonzero'
    calls, services, allocated = [], [], []
    child_constructors = []
    machine.observe(0x488EF0, lambda m, a: child_constructors.append(m.register(UC_X86_REG_ECX)))
    for function in OBSERVE:
        machine.observe(function, lambda m, a: calls.append([a, 0 if a in (0x4F63EC, 0x4DC870) else m.register(UC_X86_REG_ECX)]))
    machine.intercept(0x4A48E0)
    machine.intercept(0x4F6286)
    machine.intercept(0x4F51C5)
    machine.intercept(0x4F572A)
    list_operations = iter(profile['listOperations'])
    def external(m, address):
        stack = m.register(UC_X86_REG_ESP)
        if address == 0x4A48E0:
            count = m.words(stack + 4, 1)[0]
            row = next(allocations)
            assert count == row['count']
            allocated.append(count)
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
        elif address in (0x4F51C5, 0x4F572A):
            receiver = m.register(UC_X86_REG_ECX)
            arguments = list(m.words(stack + 4, 1 if address == 0x4F51C5 else 2))
            row = next(list_operations)
            assert (address, receiver, arguments) == (row['function'], row['receiver'], row['arguments'])
            services.append(['list', address, receiver, arguments, row['result']])
            m.return_from_external(row['result'], len(arguments) * 4)
        else:
            raise AssertionError(hex(address))
    machine.on_external = external
    outputs = []
    for step in profile['steps']:
        calls.clear(); services.clear()
        target, callback = step['actor'], step['callback']
        target_state = machine.words(target + 0x6C, 1)[0]
        machine.write(target_state + 0x1C, struct.pack('<I', step['command']))
        for segment in step['inputGlobals']:
            machine.write(segment['address'], bytes.fromhex(segment['hex']))
        result = machine.call(callback, arguments=[target])
        assert result.completed, (profile['name'], step['command'], result)
        outputs.append(dict(callback=callback, actor=target, command=step['command'], calls=[c for c in calls if not (c[0] == 0x4C8160 and c[1] in profile['childStates'])], services=list(services),
            spans=[dict(address=span['address'], hex=machine.read(span['address'], span['count']).hex()) for span in step['spans']]))
    assert allocated[:3] == [0xA4, 0x174, 0x174], allocated
    assert allocated[3:] and all(allocated[i:i+5] == [0x1B4, 0x174, 0x6C, 0x174, 0x174] for i in range(3, len(allocated), 5)), allocated
    assert len(child_constructors) == allocated.count(0x6C) > 0
    assert next(list_operations, None) is None
    assert next(allocations, None) is None
    assert [step['command'] for step in profile['steps'][:4]] == [0, 1000, 29, 30]
    assert profile['steps'][4]['command'] not in (0, 1000, 29, 30)
    assert all(step['callback'] == 0x488E30 for step in profile['steps'][5:])
    assert len(profile['steps'][5:]) == allocated.count(0x6C)
    return dict(name=profile['name'], steps=outputs, executable_sha256=program.sha256)


def compare(directory):
    source = json.loads((directory / 'plank-native-input.json').read_text())
    native = json.loads((directory / 'plank-native-output.json').read_text())
    assert len(source['profiles']) == len(native['profiles']) == 2
    original = [reference(profile) for profile in source['profiles']]
    (directory / 'plank-original-output.json').write_text(json.dumps(original, indent=2)+'\n')
    comparisons = 0
    for expected, actual in zip(original, native['profiles'], strict=True):
        assert expected['name'] == actual['name']
        for ref, got in zip(expected['steps'], actual['steps'], strict=True):
            for key in ('callback', 'actor', 'command', 'calls', 'services', 'spans'):
                assert ref[key] == got[key], (actual['name'], got['command'], key, ref[key] if key != 'spans' else 'see original output', got[key] if key != 'spans' else 'see native output')
            comparisons += 1
    expected_owners = {0x4F63EC, 0x40F870, 0x4C7FA0, 0x4C8060, 0x4C8160, 0x4C8DA0,
                       0x4C96B0, 0x4DC870, 0x4C9E30, 0x40FB30, 0x4890F0, 0x4041B0}
    actual_owners = {a for p in native['profiles'] for s in p['steps'] for a, _ in s['calls']}
    assert expected_owners <= actual_owners
    trace = native['trace']
    positions = [trace.index(value) for value in ['loadGridObject', 'scene.gameplay', 'ClawNativeBreakPlank', '0x40f7b0']]
    assert positions == sorted(positions)
    assert any('ClawActorResources' in event for event in trace)
    assert any('ClawNativeMfcMemory' in event for event in trace)
    expected_controls = {'scene_destruction_retires_all_allocations',
                         'same_scene_recreates_actor_and_helper', 'retired_helper_rejected',
                         'missing_resource_service_rejected', 'replacement_actor_rejected',
                         'replacement_logic_rejected', 'replacement_helper_rejected',
                         'foreign_helper_rejected', 'service_outside_callback_rejected'}
    assert set(native['controls']) == expected_controls, native['controls']
    assert all(value is True for value in native['controls'].values()), native['controls']
    assert native['faults'] == 0 and not native['unresolvedDependencies']
    physical_lists = {event[1] for p in native['profiles'] for step in p['steps']
                      for event in step['services'] if event[0] == 'list'}
    return dict(original_callback='0x40f7b0', native_owner='ClawNativeBreakPlank', comparisons=comparisons,
                exercised_service_edges=[f'0x{function:x}' for function in sorted(actual_owners | physical_lists | {0x4F6286, 0x4A48E0, 0x4F6974, 0x4F4680, 0x488E30})],
                controls=native['controls'], faults=0, unresolved_dependencies=[],
                evidence='Actual Level 5 WWD actor with original plank resources in the existing native scene; no live-play claim')
