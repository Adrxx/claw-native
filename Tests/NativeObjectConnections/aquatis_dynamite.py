"""WWD AquatisDynamite scene connection against the authenticated original.

Allocation and resource dictionaries are physical services. Constructors,
state dispatch, virtual methods and scalar teardown execute real game bodies.
"""
import json
import struct
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x406dd0
OBSERVE = (0x4f63ec,0x4071a0,0x4c7fa0,0x4c8060,0x4c7970,0x4c96b0,0x4dc870,0x4c9e30,0x406ef0,0x4c82a0,0x458570,0x4dba00,0x4f6974,0x4041b0,0x484d90,0x4f6428,0x4c8da0,0x465450,0x4f51c5,0x4f572a,0x546d5c)


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
        if name == 'LEVEL12/WORLDS/WORLD.WWD':
            (directory / 'WORLD12.WWD').write_bytes(payload)
            found.append(name)
    assert found == ['LEVEL12/WORLDS/WORLD.WWD']
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
    reviewed = [(0x50B244, 36), (0x513740, 40), (0x510020, 4)]
    reviewed += [(address, len(string(machine, address).encode('ascii')) + 1)
                 for address in (0x522d54,0x522d48,0x523148,0x5235d0,0x522894)]
    metadata = {address: machine.read(address, size) for address, size in reviewed}
    for segment in profile['segments']:
        address, data = segment['address'], bytes.fromhex(segment['hex'])
        map_span(address, len(data)); machine.write(address, data)
    for address, data in metadata.items():
        assert machine.read(address, len(data)) == data, f'Native metadata differs from original at {address:#x}'
    actor, state = profile['actor'], profile['state']
    allocations = iter(profile['allocations'])
    bindings = {(b['receiver'], b['name']): b['token'] for b in profile['resourceBindings']}
    assert len(bindings) == len(profile['resourceBindings'])
    assert {name for _, name in bindings} >= {'LogicHit', 'LogicAttack', 'GAME_DYNAMITE', 'AmmoPowerup'}
    assert all(token for (_, name), token in bindings.items() )
    calls, services, allocated, live = [], [], [], {}
    for function in OBSERVE:
        machine.observe(function, lambda m, a: calls.append([a, 0 if a in (0x4F63EC, 0x4DC870, 0x4F6428) else m.register(UC_X86_REG_ECX)]))
    for function in (0x4A48E0, 0x4F6286, 0x4F6428, 0x4F6974, 0x4f51c5, 0x4f572a, 0x710f00):
        machine.intercept(function)
    def external(m, address):
        stack = m.register(UC_X86_REG_ESP)
        if address == 0x4A48E0:
            count = m.words(stack + 4, 1)[0]
            row = next(allocations)
            assert count == row['count'] and count in (0x54, 0x174, 0x1b4)
            allocated.append(count); live[row['token']] = count
            map_span(row['token'], count); m.write(row['token'], b'\xcc' * count)
            services.append(['malloc', row['token'], count]); m.return_from_external(row['token'], 0)
        elif address == 0x4F6286:
            name_token, output = m.words(stack + 4, 2)
            receiver, name = m.register(UC_X86_REG_ECX), string(m, name_token)
            token = bindings[(receiver, name)]
            m.write(output, struct.pack('<I', token)); services.append(['registry', receiver, name, token])
            m.return_from_external(int(token != 0), 8)
        elif address == 0x4F6974:
            assert m.words(stack + 4, 1)[0] == 0
            m.return_from_external(m.words(m.register(UC_X86_REG_ECX), 1)[0], 4)
        elif address == 0x4F6428:
            token = m.words(stack + 4, 1)[0]
            assert live.pop(token) == 0x54 and m.words(token, 1)[0] == 0x50B014
            services.append(['delete', token, 0x50B014]); m.return_from_external(0, 0)
        elif address in (0x4f51c5, 0x4f572a):
            receiver = m.register(UC_X86_REG_ECX)
            args = m.words(stack + 4, 1 if address == 0x4f51c5 else 2)
            value = args[-1]
            row = next(appends)
            assert row[1:3] == [receiver, value]
            node = row[3]; map_span(node, 12)
            following = 0 if address == 0x4f51c5 else args[0]
            assert following == row[4]
            tail = m.words(following + 4, 1)[0] if following else m.words(receiver + 8, 1)[0]
            m.write(node, struct.pack('<III', following, tail, value))
            if tail: m.write(tail, struct.pack('<I', node))
            else: m.write(receiver + 4, struct.pack('<I', node))
            if following: m.write(following + 4, struct.pack('<I', node))
            else: m.write(receiver + 8, struct.pack('<I', node))
            m.write(receiver + 12, struct.pack('<I', m.words(receiver + 12, 1)[0]+1))
            services.append(row); m.return_from_external(node, len(args)*4)
        elif address == 0x710f00:
            output, *values = m.words(stack + 4, 5)
            m.write(output, struct.pack('<4I', *values))
            calls.append([0x546d5c, 0]); services.append(['SetRect', *values]); m.return_from_external(1, 20)
        else:
            raise AssertionError(hex(address))
    machine.on_external = external
    outputs = []
    for step in profile['steps']:
        calls.clear(); services.clear()
        for segment in step['inputGlobals']:
            machine.write(segment['address'], bytes.fromhex(segment['hex']))
        appends = iter(step['appends'])
        command = step['command']
        if command == -1:
            helper = machine.words(state + 0x18, 1)[0]
            result = machine.call(machine.words(machine.words(helper, 1)[0], 1)[0], ecx=helper, arguments=[1])
            machine.write(state + 0x18, struct.pack('<I', 0))
        else:
            machine.write(state + 0x1C, struct.pack('<I', command))
            result = machine.call(CALLBACK, arguments=[actor])
        assert result.completed, (profile['name'], command, result)
        filtered = list(calls)
        outputs.append(dict(command=command, calls=filtered, services=list(services),
                            spans=[dict(address=s['address'], hex=machine.read(s['address'], s['count']).hex()) for s in step['spans']]))
    assert allocated == [0x54,0x174,0x174,0x1b4,0x174,0x54,0x1b4,0x174], allocated
    assert next(allocations, None) is None
    commands = [step['command'] for step in profile['steps']]
    assert commands[:4] == [0, 1000, 29, 30] and commands[5:7] == [-1, 0]
    assert commands[4] == commands[7] and commands[4] not in (0, 1000, 29, 30)
    return dict(name=profile['name'], steps=outputs, executable_sha256=program.sha256)


def compare(directory):
    source = json.loads((directory / 'aquatis_dynamite-native-input.json').read_text())
    native = json.loads((directory / 'aquatis_dynamite-native-output.json').read_text())
    assert len(source['profiles']) == len(native['profiles']) == 2
    original = [reference(profile) for profile in source['profiles']]
    (directory / 'aquatis_dynamite-original-output.json').write_text(json.dumps(original, indent=2)+'\n')
    comparisons = 0
    for expected, actual in zip(original, native['profiles'], strict=True):
        assert expected['name'] == actual['name']
        for ref, got in zip(expected['steps'], actual['steps'], strict=True):
            for key in ('command', 'calls', 'services', 'spans'):
                assert ref[key] == got[key], (actual['name'], got['command'], key, ref[key] if key != 'spans' else 'see original output', got[key] if key != 'spans' else 'see native output')
            comparisons += 1
    actual_owners = {address for profile in native['profiles'] for step in profile['steps'] for address, _ in step['calls']}
    assert set(OBSERVE) - {0x4f51c5, 0x546d5c} <= actual_owners
    trace = native['trace']
    positions = [trace.index(value) for value in ['loadGridObject', 'scene.gameplay', 'ClawNativeAquatisDynamite', '0x406dd0']]
    assert positions == sorted(positions)
    assert any('ClawActorResources' in event for event in trace)
    assert any('ClawNativeMfcMemory' in event for event in trace)
    expected_controls = {'scene_destruction_retires_owned_helper_and_secondaries', 'same_scene_recreates_actor_and_helper',
                         'retired_helper_rejected', 'same_actor_recreates_helper_and_reuses_secondaries',
                         'missing_resource_service_rejected', 'replacement_actor_rejected',
                         'replacement_logic_rejected', 'replacement_helper_rejected',
                         'foreign_helper_rejected', 'service_outside_callback_rejected',
                         'missing_state_buffer_service_rejected', 'foreign_callback_rejected'}
    assert set(native['controls']) == expected_controls, native['controls']
    assert all(value is True for value in native['controls'].values()), native['controls']
    assert native['faults'] == 0 and not native['unresolvedDependencies']
    return dict(original_callback='0x406dd0', native_owner='ClawNativeAquatisDynamite', comparisons=comparisons,
                exercised_service_edges=[f'0x{function:x}' for function in sorted(actual_owners | {CALLBACK, 0x4F6286, 0x4A48E0, 0x4F6974})],
                controls=native['controls'], faults=0, unresolved_dependencies=[],
                evidence='Original Level 12 WWD AquatisDynamite in the native scene, real constructor, real idle animation and lifecycle dispatcher, scalar teardown/reuse and scene actor recreation; no live-play claim')
