"""BossWarp scene join against authenticated original game bodies.

Only physical resource lookup, allocation, list nodes and SetRect are replaced.
The callback, animation, mode-three query and spawned actor construction execute
original instructions. All original bytes remain under ignored work/.
"""
import json
import struct
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import materialize, verify_assets

CALLBACK = 0x470870
# Internal WorldObject constructor 0x4c8160 dispatches directly inside its
# canonical owner, outside the host boundary. Complete allocated actor/state
# bytes below compare its stores; ordered calls cover the actual host join.
OBSERVE = {0x4C79E0, 0x4C82A0, 0x40AF90, 0x4750D0, 0x4C8DA0,
           0x4F63EC, 0x4C81B0, 0x4701B0}


def prepare(directory):
    materialize({'LEVEL2/WORLDS/WORLD.WWD': (directory / 'WORLD2.WWD', True),
                 'GAME/ANIS/BOSSWARP.ANI': (ROOT / 'App/GameData/GAME/ANIS/BOSSWARP.ANI', False),
                 'GAME/ANIS/POWERUP.ANI': (ROOT / 'App/GameData/GAME/ANIS/POWERUP.ANI', False),
                 'GAME/SOUNDS/MAGICPOWERUP.WAV': (ROOT / 'App/GameData/GAME/SOUNDS/MAGICPOWERUP.WAV', False)})
    fixture = json.loads((ROOT / 'Tests/NativeObjectConnections/boss_stager_transport.json').read_text())['fixtures']['SetRect']
    machine = Machine(claw(), 0x10000000, 4096)
    (directory / 'warp-fixtures.json').write_text(json.dumps(dict(SetRect=fixture, modeFourTable=machine.read(0x50EF94, 0x14).hex())) + '\n')
    root = (directory / 'fallback-resources').resolve()
    root.mkdir(exist_ok=True)
    source = (ROOT / 'App/GameData').resolve()
    def link_tree(target, child):
        assert target.parent.resolve().is_relative_to(root)
        if child.is_dir():
            if target.is_symlink():
                target.unlink()
            target.mkdir(exist_ok=True)
            for entry in child.iterdir():
                link_tree(target / entry.name, entry)
        elif child.relative_to(source).as_posix() == 'GAME/ANIS/BOSSWARP.ANI':
            if target.is_symlink():
                target.unlink()
            assert not target.exists()
        elif not target.exists():
            target.symlink_to(child.resolve())
    for child in source.iterdir():
        link_tree(root / child.name, child)


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
    metadata = {a: machine.read(a, n) for a, n in
                [(0x50C264, 0x14), (0x50EF94, 0x14), (0x510020, 4)]}
    for segment in profile['segments']:
        address, data = segment['address'], bytes.fromhex(segment['hex'])
        map_span(address, len(data))
        machine.write(address, data)
    for address, data in metadata.items():
        if any(s['address'] <= address < s['address'] + len(bytes.fromhex(s['hex'])) for s in profile['segments']):
            assert machine.read(address, len(data)) == data, f'Mode metadata mismatch {address:#x}'
    bindings = {(b['receiver'], b['name']): b['token'] for b in profile['resourceBindings']}
    assert len(bindings) == len(profile['resourceBindings'])
    allocations = iter(profile['allocations'])
    lists = iter(profile['listOperations'])
    calls, services = [], []
    for function in OBSERVE:
        machine.observe(function, lambda m, a: calls.append([a, 0 if a in (0x4F63EC, 0x4701B0) else m.register(UC_X86_REG_ECX)]))
    machine.intercept(0x4A48E0)
    machine.intercept(0x4F6286)
    machine.intercept(0x4F51C5)
    machine.intercept(0x4F572A)
    if profile['rectTarget']:
        machine.intercept(profile['rectTarget'])
    def external(m, address):
        stack = m.register(UC_X86_REG_ESP)
        if address == 0x4A48E0:
            count = m.words(stack + 4, 1)[0]
            row = next(allocations)
            assert row['count'] == count
            map_span(row['token'], count)
            m.write(row['token'], b'\xcc' * count)
            services.append(['malloc', row['token'], count])
            m.return_from_external(row['token'], 0)
        elif address == 0x4F6286:
            name_pointer, output = m.words(stack + 4, 2)
            receiver = m.register(UC_X86_REG_ECX)
            name = string(m, name_pointer)
            token = bindings[(receiver, name)]
            m.write(output, struct.pack('<I', token))
            services.append(['registry', receiver, name, token])
            m.return_from_external(int(token != 0), 8)
        elif address in (0x4F51C5, 0x4F572A):
            receiver = m.register(UC_X86_REG_ECX)
            arguments = list(m.words(stack + 4, 1 if address == 0x4F51C5 else 2))
            row = next(lists)
            assert (row['function'], row['receiver'], row['arguments']) == (address, receiver, arguments)
            node = row['result']
            map_span(node, 12)
            if address == 0x4F572A:
                at, actor = arguments
                previous = m.words(at + 4, 1)[0]
                m.write(node, struct.pack('<3I', at, previous, actor))
                m.write(previous if previous else receiver + 4, struct.pack('<I', node))
                m.write(at + 4, struct.pack('<I', node))
            else:
                tail = m.words(receiver + 8, 1)[0]
                m.write(node, struct.pack('<3I', 0, tail, arguments[0]))
                m.write(tail if tail else receiver + 4, struct.pack('<I', node))
                m.write(receiver + 8, struct.pack('<I', node))
            m.write(receiver + 12, struct.pack('<I', m.words(receiver + 12, 1)[0] + 1))
            services.append(['list', address, receiver, arguments, row['result']])
            m.return_from_external(row['result'], len(arguments) * 4)
        elif address == profile['rectTarget']:
            output, *values = m.words(stack + 4, 5)
            m.write(output, struct.pack('<4I', *values))
            services.append(['rectangle', *values])
            m.return_from_external(1, 20)
        else:
            raise AssertionError(f'Unexpected physical service {address:#x}')
    machine.on_external = external
    outputs = []
    for step in profile['steps']:
        calls.clear(); services.clear()
        for segment in step['inputGlobals']:
            machine.write(segment['address'], bytes.fromhex(segment['hex']))
        result = machine.call(CALLBACK, arguments=[profile['actor']])
        assert result.completed, (profile['name'], result)
        outputs.append(dict(delta=step['delta'], calls=list(calls), services=list(services),
            spans=[dict(address=span['address'], hex=machine.read(span['address'], span['count']).hex()) for span in step['spans']]))
    assert next(allocations, None) is None
    assert next(lists, None) is None
    return dict(name=profile['name'], steps=outputs, executable_sha256=program.sha256)


def compare(directory):
    source = json.loads((directory / 'warp-native-input.json').read_text())
    actual = json.loads((directory / 'warp-native-output.json').read_text())
    original = [reference(profile) for profile in source['profiles']]
    (directory / 'warp-original-output.json').write_text(json.dumps(original, indent=2) + '\n')
    comparisons = 0
    for ref, got in zip(original, actual['profiles'], strict=True):
        assert ref['name'] == got['name']
        for expected, native in zip(ref['steps'], got['steps'], strict=True):
            for field in ('delta', 'calls', 'services', 'spans'):
                assert expected[field] == native[field], (ref['name'], native['delta'], field,
                    expected[field] if field != 'spans' else 'see warp-original-output.json',
                    native[field] if field != 'spans' else 'see warp-native-output.json')
            comparisons += 1
    assert len(original) == 3
    profiles = dict(zip([p['name'] for p in source['profiles']], source['profiles']))
    assert set(profiles) == {'mode-three', 'mode-four', 'fallback-animation'}
    assert [a['count'] for a in profiles['mode-four']['allocations']] == [0x1B4, 0x174]
    assert not profiles['mode-three']['allocations'] and not profiles['fallback-animation']['allocations']
    fallback = {(b['name'], b['token'] != 0) for b in profiles['fallback-animation']['resourceBindings']}
    assert ('GAME_BOSSWARP', False) in fallback and ('GAME_POWERUP', True) in fallback
    calls = {a for p in actual['profiles'] for step in p['steps'] for a, _ in step['calls']}
    assert {0x40AF90, 0x4750D0, 0x4C79E0, 0x4C82A0, 0x4C8DA0, 0x4701B0} <= calls
    trace = actual['trace']
    positions = [trace.index(value) for value in ['loadGridObject', 'scene.gameplay', 'ClawNativeBossWarp', '0x470870']]
    assert positions == sorted(positions)
    assert actual['controls'] and all(actual['controls'].values())
    return dict(original_callback='0x470870', native_owner='ClawNativeBossWarp', comparisons=comparisons,
                exercised_service_edges=[f'0x{function:x}' for function in sorted(calls | {0x4F6286, 0x4A48E0, 0x4F51C5, 0x546D5C})],
                controls=actual['controls'], faults=actual['faults'], unresolved_dependencies=actual['unresolvedDependencies'],
                physical_inputs='Original Level 2 BossWarp record in native scene with disc resources and actual application detail=0 (native low-detail profile); fallback omits only BOSSWARP.ANI; high-detail negative requires the unelected glitter graph; no live-play acceptance',
                asset_sha256=verify_assets())
