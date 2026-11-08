"""WWD GroundBlower scene connection against the authenticated original.

Allocation and resource dictionaries are physical services. Constructors,
state dispatch, virtual methods and scalar teardown execute real game bodies.
"""
import json
import struct
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x448d10
OBSERVE = (0x4F63EC, 0x4490E0, 0x4C7FA0, 0x4C8060, 0x4C8160,
           0x4C81B0, 0x4C96B0, 0x4DC870, 0x4C9E30, 0x448E30, 0x406290, 0x4C8220, 0x4C82A0,
           0x4492C0, 0x4DBA00, 0x4F6974, 0x4041B0, 0x484D90, 0x4F6428,
           0x41E810, 0x41C4E0, 0x4C79E0, 0x4208B0, 0x4170B0, 0x420DD0)


def prepare(directory):
    directory = directory.resolve()
    root = directory / 'resources'
    root.mkdir(exist_ok=True)
    def link_tree(target, source):
        assert target.parent.resolve().is_relative_to(root), target
        if source.is_dir():
            if target.is_symlink():
                target.unlink()
            target.mkdir(exist_ok=True)
            for child in source.iterdir():
                link_tree(target / child.name, child)
        else:
            if target.is_symlink() and not target.exists():
                target.unlink()
            if not target.exists():
                target.symlink_to(source.resolve())
    for child in (ROOT / 'App/GameData').resolve().iterdir():
        link_tree(root / child.name, child)
    found = []
    for name, payload in entries():
        if name == 'LEVEL6/WORLDS/WORLD.WWD':
            (directory / 'WORLD6.WWD').write_bytes(payload)
        if name.startswith('LEVEL6/IMAGES/BLOWING1/') or name == 'LEVEL6/ANIS/GROUNDBLOWER.ANI':
            target = root / 'LEVEL1' / name.removeprefix('LEVEL6/')
            target.parent.mkdir(parents=True, exist_ok=True)
            assert not target.is_symlink() and not target.parent.is_symlink(), target
            target.write_bytes(payload)
            found.append(name)
    assert any('/IMAGES/' in name for name in found)
    assert 'LEVEL6/ANIS/GROUNDBLOWER.ANI' in found
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
    def map_span(address, size):
        for page in range(address & ~4095, (address + size + 4095) & ~4095, 4096):
            if not any(begin <= page <= end for begin, end, _ in machine.uc.mem_regions()):
                machine.uc.mem_map(page, 4096)
    reviewed = [(0x50DFAC, 36), (0x513740, 40), (0x510020, 4),
                (0x50BA88, 8), (0x50BAA8, 8), (0x50BAC0, 32), (0x513E20, 8)]
    reviewed += [(address, len(string(machine, address).encode('ascii')) + 1)
                 for address in (0x522D54, 0x522D48, 0x527ABC, 0x523604, 0x5246A8)]
    metadata = {address: machine.read(address, size) for address, size in reviewed}
    import_slots = {slot: machine.words(slot, 1)[0] for slot in (0x546D58, 0x546D4C, 0x546CE0)}
    for segment in profile['segments']:
        address, data = segment['address'], bytes.fromhex(segment['hex'])
        map_span(address, len(data)); machine.write(address, data)
    for address, data in metadata.items():
        assert machine.read(address, len(data)) == data, f'Native metadata differs from original at {address:#x}'
    # The native Memory import table uses native service tokens. The original
    # keeps its authenticated import targets and supplies the same rectangle API.
    for slot, target in import_slots.items():
        machine.write(slot, struct.pack('<I', target))
    imports = {value: name for (slot, value), name in zip(import_slots.items(), ('copy', 'empty', 'intersect'), strict=True)}
    actor, state = profile['actor'], profile['state']
    allocations = iter(profile['allocations'])
    bindings = {(b['receiver'], b['name']): b['token'] for b in profile['resourceBindings']}
    assert len(bindings) == len(profile['resourceBindings'])
    assert {name for _, name in bindings} >= {'LogicHit', 'LogicAttack', 'LEVEL_GROUNDBLOWER'}
    assert all(token for (_, name), token in bindings.items() )
    calls, services, allocated, live = [], [], [], {}
    for function in OBSERVE:
        machine.observe(function, lambda m, a: calls.append([a, 0 if a in (0x4F63EC, 0x4DC870, 0x4F6428, 0x41E810, 0x41C4E0, 0x4170B0) else m.register(UC_X86_REG_ECX)]))
    for function in (0x4A48E0, 0x4F6286, 0x4F6428):
        machine.intercept(function)
    def external(m, address):
        stack = m.register(UC_X86_REG_ESP)
        if address in imports:
            name = imports[address]
            args = lambda count: m.words(stack + 4, count)
            signed = lambda x: x if x < 0x80000000 else x - 0x100000000
            if name == 'copy':
                destination, source = args(2)
                m.write(destination, m.read(source, 16)); value, arity = 1, 2
            elif name == 'empty':
                rectangle, = args(1)
                left, top, right, bottom = map(signed, m.words(rectangle, 4))
                value, arity = int(left >= right or top >= bottom), 1
            else:
                destination, first, second = args(3)
                a, b = [list(map(signed, m.words(pointer, 4))) for pointer in (first, second)]
                rectangle = [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]
                value, arity = int(rectangle[0] < rectangle[2] and rectangle[1] < rectangle[3]), 3
                m.write(destination, struct.pack('<iiii', *(rectangle if value else [0] * 4)))
            services.append(['rectangle', name, value]); m.return_from_external(value, arity * 4)
        elif address == 0x4A48E0:
            count = m.words(stack + 4, 1)[0]
            row = next(allocations)
            assert count == row['count'] and count in (0x50, 0x174)
            allocated.append(count); live[row['token']] = count
            map_span(row['token'], count); m.write(row['token'], b'\xcc' * count)
            services.append(['malloc', row['token'], count]); m.return_from_external(row['token'], 0)
        elif address == 0x4F6286:
            name_token, output = m.words(stack + 4, 2)
            receiver, name = m.register(UC_X86_REG_ECX), string(m, name_token)
            token = bindings[(receiver, name)]
            m.write(output, struct.pack('<I', token)); services.append(['registry', receiver, name, token])
            m.return_from_external(int(token != 0), 8)
        elif address == 0x4F6428:
            token = m.words(stack + 4, 1)[0]
            assert live.pop(token) == 0x50 and m.words(token, 1)[0] == 0x50B014
            services.append(['delete', token, 0x50B014]); m.return_from_external(0, 0)
        else:
            raise AssertionError(hex(address))
    machine.on_external = external
    outputs = []
    for step in profile['steps']:
        calls.clear(); services.clear()
        for segment in step['inputGlobals']:
            machine.write(segment['address'], bytes.fromhex(segment['hex']))
        command = step['command']
        if command == -1:
            helper = machine.words(state + 0x18, 1)[0]
            result = machine.call(machine.words(machine.words(helper, 1)[0], 1)[0], ecx=helper, arguments=[1])
            machine.write(state + 0x18, struct.pack('<I', 0))
        else:
            machine.write(state + 0x1C, struct.pack('<I', command))
            result = machine.call(CALLBACK, arguments=[actor])
        assert result.completed, (profile['name'], command, result)
        # constructBlower inlines blowerIdle in the source.
        # A separately dispatched idle remains an observed canonical call.
        filtered = []
        constructing = False
        for call in calls:
            if call[0] == 0x4490E0:
                constructing = True
            if call[0] == 0x449270 and constructing:
                continue
            if call[0] == 0x4C96B0:
                constructing = False
            # ActorAnimationCanonical.named executes select directly. The
            # original 0x4c79e0 calls 0x4c8220 for the same player's embedded
            # animation state. Keep constructor and all other selects observed.
            player = machine.words(0x537E88, 1)[0]
            if (call == [0x4C8220, player + 0x188] and filtered and
                    filtered[-1] == [0x4C79E0, player]):
                continue
            filtered.append(call)
        outputs.append(dict(command=command, calls=filtered, services=list(services),
                            spans=[dict(address=s['address'], hex=machine.read(s['address'], s['count']).hex()) for s in step['spans']]))
    assert allocated == [0x50, 0x174, 0x174, 0x50], allocated
    assert next(allocations, None) is None
    commands = [step['command'] for step in profile['steps']]
    assert commands[:4] == [0, 1000, 29, 30] and commands[5:7] == [-1, 0]
    assert commands[4] == commands[7] and commands[4] not in (0, 1000, 29, 30)
    return dict(name=profile['name'], steps=outputs, executable_sha256=program.sha256)


def compare(directory):
    source = json.loads((directory / 'blower-native-input.json').read_text())
    native = json.loads((directory / 'blower-native-output.json').read_text())
    assert len(source['profiles']) == len(native['profiles']) == 2
    original = [reference(profile) for profile in source['profiles']]
    (directory / 'blower-original-output.json').write_text(json.dumps(original, indent=2)+'\n')
    comparisons = 0
    for expected, actual in zip(original, native['profiles'], strict=True):
        assert expected['name'] == actual['name']
        for ref, got in zip(expected['steps'], actual['steps'], strict=True):
            for key in ('command', 'calls', 'services', 'spans'):
                assert ref[key] == got[key], (actual['name'], got['command'], key, ref[key] if key != 'spans' else 'see original output', got[key] if key != 'spans' else 'see native output')
            comparisons += 1
    actual_owners = {address for profile in native['profiles'] for step in profile['steps'] for address, _ in step['calls']}
    assert set(OBSERVE) <= actual_owners
    rectangle_addresses = {'copy': 0x546D58, 'empty': 0x546D4C, 'intersect': 0x546CE0}
    rectangle_edges = {rectangle_addresses[service[1]]
                       for profile in native['profiles'] for step in profile['steps']
                       for service in step['services'] if service[0] == 'rectangle'}
    trace = native['trace']
    positions = [trace.index(value) for value in ['loadGridObject', 'scene.gameplay', 'ClawNativeGroundBlower', '0x448d10']]
    assert positions == sorted(positions)
    assert any('ClawActorResources' in event for event in trace)
    assert any('ClawNativeMfcMemory' in event for event in trace)
    expected_controls = {'scene_destruction_retires_all_allocations', 'same_scene_recreates_actor_and_helper',
                         'retired_helper_rejected', 'same_actor_recreates_helper_and_reuses_secondaries',
                         'missing_resource_service_rejected', 'replacement_actor_rejected',
                         'replacement_logic_rejected', 'replacement_helper_rejected',
                         'foreign_helper_rejected', 'service_outside_callback_rejected',
                         'missing_state_buffer_service_rejected', 'missing_rectangle_service_rejected', 'foreign_callback_rejected',
                         'player_runtime_imported'}
    assert set(native['controls']) == expected_controls, native['controls']
    assert all(value is True for value in native['controls'].values()), native['controls']
    assert native['faults'] == 0 and not native['unresolvedDependencies']
    return dict(original_callback='0x448d10', native_owner='ClawNativeGroundBlower', comparisons=comparisons,
                exercised_service_edges=[f'0x{function:x}' for function in sorted(actual_owners | rectangle_edges | {CALLBACK, 0x4F6286, 0x4A48E0, 0x4F6974})],
                controls=native['controls'], faults=0, unresolved_dependencies=[],
                evidence='Original Level 6 WWD GroundBlower in the native scene, real constructor, frame-one tick/player force and runtime import, scalar teardown/reuse and scene actor recreation; no live-play claim')
