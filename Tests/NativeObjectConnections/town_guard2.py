"""Original TownGuard2 callback over a scene-attached WWD actor and real assets.

Native inputs supply only physical allocation, resource dictionaries and RNG.
The original constructor, vtable targets and lifecycle state code execute intact.
"""
import json
import struct
import zlib
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x4968D0
OBSERVE = (0x4F63EC, 0x496990, 0x44C000, 0x405000, 0x4C7FA0,
           0x4C8060, 0x4C7970, 0x4062E0, 0x4061B0, 0x4C8220,
           0x4F6439, 0x4DC180, 0x4DB620, 0x4DBE10, 0x4DBD60,
           0x4DBCD0, 0x420FC0, 0x4DBD20, 0x497970, 0x44F1B0,
           0x44CFD0, 0x4C96B0, 0x4DC870, 0x497510, 0x497130,
           0x44D000, 0x44D3C0, 0x43DFA0, 0x497A50, 0x403B40,
           0x4CBB60, 0x43E9B0, 0x48CF50)


def prepare(directory):
    directory = directory.resolve()
    root = directory / 'resources'
    root.mkdir(exist_ok=True)
    source = (ROOT / 'App/GameData').resolve()

    def link_tree(target, child):
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
    found = []
    for name, payload in entries():
        if name == 'LEVEL5/WORLDS/WORLD.WWD':
            (directory / 'WORLD5.WWD').write_bytes(payload)
        if name.startswith(('LEVEL5/IMAGES/TOWNGUARD2/', 'LEVEL5/ANIS/TOWNGUARD1/',
                            'LEVEL5/ANIS/TOWNGUARD2/', 'LEVEL5/SOUNDS/')):
            target = root / 'LEVEL1' / name.removeprefix('LEVEL5/')
            target.parent.mkdir(parents=True, exist_ok=True)
            # Own overlay leaves only; never write through App/GameData links.
            if target.is_symlink():
                target.unlink()
            assert target.parent.resolve().is_relative_to(root)
            target.write_bytes(payload)
            found.append(name)
    assert (directory / 'WORLD5.WWD').exists()
    assert any('/IMAGES/' in name for name in found)
    assert any('/ANIS/TOWNGUARD2/' in name for name in found)
    assert any('/SOUNDS/' in name for name in found)
    (directory / 'physical-assets.json').write_text(json.dumps(
        dict(asset_sha256=verify_assets(), files=found), indent=2) + '\n')


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

    # Check static vtable/constant/string values against the authenticated image.
    # Registry arrays and globals are live scene inputs, not immutable metadata.
    reviewed = [(0x50FB6C, 40), (0x50FB6C + 0x48, 4), (0x50FAB0, 4), (0x510020, 4)]
    addresses = (0x522D54, 0x522D48, 0x52D450, 0x52D434, 0x52D414,
                 0x52D3F8, 0x52D3DC, 0x52D3C4, 0x52D3AC, 0x52D394,
                 0x52D378, 0x52D360, 0x52D348, 0x52D32C, 0x52D310,
                 0x52D2F8, 0x52D1AC, 0x52D464)
    reviewed += [(address, len(string(machine, address).encode('ascii')) + 1)
                 for address in addresses]
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
    assert {name for _, name in bindings} >= {
        'LogicHit', 'LogicAttack', 'LEVEL_TOWNGUARD2',
        'LEVEL_TOWNGUARD2_ADVANCE', 'LEVEL_TOWNGUARD2_STRIKE1', 'LEVEL_TOWNGUARD_00370027'}
    required = {'LogicHit', 'LogicAttack', 'LEVEL_TOWNGUARD2',
                'LEVEL_TOWNGUARD2_ADVANCE', 'LEVEL_TOWNGUARD2_STRIKE1', 'LEVEL_TOWNGUARD_00370027'}
    assert all(value for (_, name), value in bindings.items() if name in required), 'Required real resources must be nonzero'
    calls, services, allocated, rng = [], [], [], []
    freed = []
    # The extra entry is an inlined C++ body; independently require it and its
    # descendants rather than treating a native observer omission as execution.
    inlined = []
    machine.observe(0x4DCA10, lambda *_: inlined.append(0x4DCA10))
    for function in OBSERVE:
        machine.observe(function, lambda m, a: calls.append(
            [a, 0 if a in (0x4F63EC, 0x4DC870, 0x48CF50) else m.register(UC_X86_REG_ECX)]))
    for function in (0x4A48E0, 0x4A49B0, 0x4F6286, 0x4A3050):
        machine.intercept(function)
    # The scene has its own physical import entry identities. Intercept those
    # exact target tokens without rewriting import slots or game instructions.
    imports = {}
    for slot in (0x546D5C, 0x546CDC, 0x546CD4, 0x5469E8):
        target = machine.words(slot, 1)[0]
        imports[target] = slot
        map_span(target, 1)
        machine.intercept(target)

    def external(m, address):
        stack = m.register(UC_X86_REG_ESP)
        word = lambda offset: m.words(stack + offset, 1)[0]
        slot = imports.get(address, address)
        if address == 0x4A48E0:
            count = word(4)
            row = next(allocations)
            assert count == row['count']
            allocated.append(count)
            map_span(row['token'], count)
            m.write(row['token'], b'\xcc' * count)
            services.append(['malloc', row['token'], count])
            m.return_from_external(row['token'], 0)
        elif address == 0x4A49B0:
            token = word(4)
            assert token in [row['token'] for row in profile['allocations']] and token not in freed
            freed.append(token)
            m.return_from_external(0, 0)
        elif address == 0x4F6286:
            name_token, output = m.words(stack + 4, 2)
            receiver, name = m.register(UC_X86_REG_ECX), string(m, name_token)
            token = bindings[(receiver, name)]
            m.write(output, struct.pack('<I', token))
            services.append(['registry', receiver, name, token])
            m.return_from_external(int(token != 0), 8)
        elif address == 0x4A3050:
            value = rng.pop(0)
            services.append(['rand', value])
            m.return_from_external(value, 0)
        elif slot in (0x546D5C, 0x546CDC):
            destination = word(4)
            values = list(m.words(stack + 8, 4)) if slot == 0x546D5C else [0] * 4
            m.write(destination, struct.pack('<4I', *values))
            services.append(['rectangle', destination, *values] if slot == 0x546D5C
                            else ['empty-rectangle', destination])
            m.return_from_external(1, 20 if slot == 0x546D5C else 4)
        elif slot == 0x546CD4:
            rectangle, raw_x, raw_y = m.words(stack + 4, 3)
            x, y = struct.unpack('<ii', struct.pack('<II', raw_x, raw_y))
            left, top, right, bottom = struct.unpack('<iiii', m.read(rectangle, 16))
            result = int(left <= x < right and top <= y < bottom)
            services.append(['point-in-rectangle', rectangle, raw_x, raw_y, result])
            m.return_from_external(result, 12)
        elif slot == 0x5469E8:
            pointer = word(4)
            value = (m.words(pointer, 1)[0] - 1) & 0xffffffff
            m.write(pointer, struct.pack('<I', value))
            m.return_from_external(value, 4)
        else:
            raise AssertionError(f'Unresolved physical boundary {address:#x}')

    machine.on_external = external
    outputs = []
    machine.reset_x87()
    machine.set_x87_state(0x23F, 0, [])
    for step in profile['steps']:
        calls.clear(); services.clear()
        rng[:] = step['random']
        machine.write(state + 0x1C, struct.pack('<I', step['command']))
        for segment in step['inputGlobals']:
            machine.write(segment['address'], bytes.fromhex(segment['hex']))
        result = machine.call(CALLBACK, arguments=[actor])
        assert result.completed, (profile['name'], step['command'], result)
        assert not rng, 'Original did not consume the same RNG calls'
        outputs.append(dict(command=step['command'], calls=list(calls), services=list(services),
            spans=[dict(address=span['address'], hex=machine.read(span['address'], span['count']).hex())
                   for span in step['spans']]))
    assert allocated == [0x498], allocated
    assert next(allocations, None) is None
    assert [step['command'] for step in profile['steps'][:4]] == [0, 1000, 29, 30]
    assert profile['steps'][4]['command'] not in (0, 1000, 29, 30)
    assert inlined and {0x43DFA0, 0x403B40, 0x4CBB60} <= {a for s in outputs for a, _ in s['calls']}
    result = dict(name=profile['name'], steps=outputs, executable_sha256=program.sha256)
    if profile['retire']:
        helper = machine.words(state + 0x18, 1)[0]
        retired = machine.call(0x497040, ecx=helper, arguments=[1])
        assert retired.completed and freed == [helper], retired
        result['retirement'] = dict(helper=helper, hex=machine.read(helper, 0x498).hex())
    return result


def verify_world_projection(profile, data):
    """Independent raw WWD check of the existing scene-owned collision world."""
    def word(raw, offset):
        return struct.unpack_from('<I', raw, offset)[0]
    assert word(data, 0) == 1524
    offset, count, description_offset = word(data, 736), word(data, 732), word(data, 740)
    raw = data[:offset] + zlib.decompress(data[offset:]) if word(data, 8) & 2 else data
    if word(data, 8) & 2:
        assert len(raw) - offset == word(data, 744)
    planes = [offset + i * 160 for i in range(count)]
    plane = next(at for at in planes if word(raw, at + 8) & 1)
    tw, th, width, height = struct.unpack_from('<4I', raw, plane + 88)
    cells_at = word(raw, plane + 132)
    segments = [(row['address'], bytes.fromhex(row['hex'])) for row in profile['segments']]
    def read(address, size):
        for start, block in segments:
            if start <= address and address + size <= start + len(block):
                return block[address - start:address - start + size]
        raise AssertionError(f'Projection span missing {address:#x}+{size}')
    def get(address):
        return struct.unpack('<I', read(address, 4))[0]
    world = get(get(profile['actor'] + 12) + 0x24)
    handlers, tilemap = get(world + 0x4c), get(world + 0x5c)
    assert get(tilemap + 0x30) == width * tw and get(tilemap + 0x34) == height * th
    assert get(tilemap + 0x8c) == tw.bit_length() - 1
    assert get(tilemap + 0x90) == th.bit_length() - 1
    assert read(get(tilemap + 0x20), width * height * 4) == raw[cells_at:cells_at + width * height * 4]
    assert list(struct.unpack('<' + 'I' * height, read(get(tilemap + 0x24), height * 4))) == [i * width for i in range(height)]
    assert word(raw, description_offset) == 32
    n = word(raw, description_offset + 8)
    at = description_offset + 32
    for index in range(n):
        kind = word(raw, at)
        assert kind in (1, 2)
        # The original 4cb700 allocator chooses these vtables, then +14
        # invokes 4d5840/4d5c30: 3/8 WWD words at +8 copied to object +4.
        vtable, words = (0x513980, 3) if kind == 1 else (0x5139c8, 8)
        token = get(handlers + index * 4)
        assert get(token) == vtable
        assert read(token + 4, words * 4) == raw[at + 8:at + 8 + words * 4], index
        at += 20 if kind == 1 else 40
    program = claw()
    def original(address, size):
        section = next(s for s in program.sections if s.address <= address and address + size <= s.address + len(s.data))
        return section.data[address - section.address:address - section.address + size]
    for vtable, initializer, point in ((0x513980, 0x4d5840, 0x4cddc0), (0x5139c8, 0x4d5c30, 0x4cde10)):
        assert struct.unpack('<I', original(vtable + 0x14, 4))[0] == initializer
        assert struct.unpack('<I', original(vtable + 0x20, 4))[0] == point
        assert get(vtable + 0x20) == point


def compare(directory):
    source = json.loads((directory / 'town-native-input.json').read_text())
    native = json.loads((directory / 'town-native-output.json').read_text())
    assert len(source['profiles']) == len(native['profiles']) == 2
    for profile in source['profiles']:
        verify_world_projection(profile, (directory / 'resources/LEVEL1/WORLDS/WORLD.WWD').read_bytes())
    original = [reference(profile) for profile in source['profiles']]
    (directory / 'town-original-output.json').write_text(json.dumps(original, indent=2) + '\n')
    comparisons = 0
    for expected, actual in zip(original, native['profiles'], strict=True):
        assert expected['name'] == actual['name']
        assert expected.get('retirement') == actual.get('retirement'), 'Original scalar destructor bytes'
        for ref, got in zip(expected['steps'], actual['steps'], strict=True):
            # The native caller reserves its own physical scratch frame. Keep
            # the one temporary bitset's alias identity and ordered lifetime;
            # the prerequisite transport checks the source CPU/frame contract.
            def local_receivers(rows):
                locals = {}
                result = []
                for function, receiver in rows:
                    if 0x01ff0000 <= receiver < 0x02010000:
                        assert function in (0x4DBE10, 0x4DB620, 0x4DBCD0)
                        receiver = locals.setdefault(receiver, f'bitset-local-{len(locals)}')
                    result.append([function, receiver])
                return result
            ref['calls'] = local_receivers(ref['calls'])
            got['calls'] = local_receivers(got['calls'])
            for key in ('command', 'calls', 'services', 'spans'):
                assert ref[key] == got[key], (actual['name'], got['command'], key,
                    ref[key] if key != 'spans' else 'see original output',
                    got[key] if key != 'spans' else 'see native output')
            comparisons += 1
    owners = {a for p in native['profiles'] for s in p['steps'] for a, _ in s['calls']}
    assert {0x4F63EC, 0x496990, 0x44C000, 0x405000, 0x44CFD0,
            0x4C96B0, 0x4DC870, 0x497510, 0x497130, 0x497A50} <= owners
    trace = native['trace']
    positions = [trace.index(value) for value in
                 ('loadGridObject', 'scene.gameplay', 'ClawNativeTownGuard2', '0x4968d0')]
    assert positions == sorted(positions)
    assert any('ClawActorResources' in event for event in trace)
    assert 'ClawNativeCanonicalHost.0x497040' in trace
    expected_controls = {'scene_destruction_retires_all_allocations', 'same_scene_recreates_actor_and_helper',
        'retired_helper_rejected', 'missing_resource_service_rejected', 'replacement_actor_rejected',
        'foreign_helper_rejected', 'service_outside_callback_rejected',
        'primary_logic_4c80e0_retires_helper', 'primary_logic_4c80c0_retires_helper',
        'replacement_logic_teardown_rejected', 'foreign_scene_pointer_rejected',
        'canonical_release_updates_scene_holder_globals'}
    assert expected_controls <= native['controls'].keys() and all(native['controls'].values()), native['controls']
    assert native['faults'] == 0 and not native['unresolvedDependencies']
    return dict(original_callback='0x4968d0', native_owner='ClawNativeTownGuard2', comparisons=comparisons,
                exercised_service_edges=[f'0x{function:x}' for function in
                    sorted(owners | {0x4F6286, 0x4A48E0, 0x4F6974, 0x497040, 0x4F4680})],
                controls=native['controls'], faults=0, unresolved_dependencies=[],
                evidence='Original Level 5 WWD actor and assets attached to the existing Level 1 native scene world, five commands and same-scene recreation; no live-play claim')
