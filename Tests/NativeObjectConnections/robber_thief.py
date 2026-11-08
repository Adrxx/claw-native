"""Original RobberThief callback over a scene-attached WWD actor and real assets.

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

CALLBACK = 0x485270
OBSERVE = (0x4f63ec,0x485330,0x44c000,0x403b40,0x405000,0x4c7fa0,0x4c8060,0x4c7970,0x4062e0,0x4061b0,0x4c8220,0x4f6439,0x4dc180,0x4db620,0x4dbe10,0x4dbd60,0x4dbcd0,0x420fc0,0x4dbd20,0x44f1b0,0x40f6c0,0x40ab80,0x40abf0,0x4c81b0,0x4c8160,0x4c96b0,0x44cfd0,0x43e9b0,0x4dc870,0x44d000,0x485960,0x44d3c0,0x43e420,0x44ef70,0x44f850,0x43dfa0)


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
        if name == 'LEVEL3/WORLDS/WORLD.WWD':
            (directory / 'WORLD3.WWD').write_bytes(payload)
        if name.startswith(('LEVEL3/IMAGES/ROBBERTHIEF/', 'LEVEL3/ANIS/ROBBERTHIEF/', 'LEVEL3/SOUNDS/')):
            target = root / 'LEVEL1' / name.removeprefix('LEVEL3/')
            target.parent.mkdir(parents=True, exist_ok=True)
            # Own overlay leaves only; never write through App/GameData links.
            if target.is_symlink():
                target.unlink()
            assert target.parent.resolve().is_relative_to(root)
            target.write_bytes(payload)
            found.append(name)
    assert (directory / 'WORLD3.WWD').exists()
    assert any('/IMAGES/' in name for name in found)
    assert any('/ANIS/ROBBERTHIEF/' in name for name in found)
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
    reviewed = [
        (0x50f49c, 43 * 4),  # Complete RobberThief vtable through +0xa8.
        (0x50f490, 4), (0x50e008, 8), (0x50e0c0, 4),
        (0x50b090, 24),      # Original binary64 constants at +0/+4/+8/+0x10.
        (0x513e10, 16), (0x513e40, 4), (0x513e48, 16),
        (0x513740, 40),      # Real secondary LogicHit/LogicAttack vtable.
        (0x513980 + 0x20, 4), (0x5139c8 + 0x20, 4),
    ]
    addresses = (0x523148,0x522d54,0x522d48,0x52bdac,0x52bd8c,0x52bd70,0x52bd58,0x52bd3c,0x52bd20,0x52bd08,0x52bcf0,0x52bcd4,0x52bcb8,0x52bca0,0x52bc84,0x52bc68,0x52bc4c,0x52bc30,0x52bc14,0x52bbf8,0x52bbdc,0x52bbc0,0x52bba4)
    reviewed += [(address, len(string(machine,address).encode('ascii'))+1) for address in addresses]
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
    required = {'LogicHit','LogicAttack','LEVEL_ROBBERTHIEF','LEVEL_ROBBERTHIEF_FASTADVANCE'}
    assert {name for _,name in bindings} >= required
    assert all(value for (_,name),value in bindings.items() if name in required)
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
    for slot in (0x546D5C, 0x546CDC, 0x546CD4, 0x5469E8, 0x546D24):
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
        elif slot == 0x546D24:
            rectangle, raw_x, raw_y = m.words(stack+4,3)
            x,y=struct.unpack('<ii',struct.pack('<II',raw_x,raw_y))
            left,top,right,bottom=struct.unpack('<iiii',m.read(rectangle,16))
            m.write(rectangle,struct.pack('<iiii',left-x,top-y,right+x,bottom+y))
            services.append(['inflate-rectangle',rectangle,raw_x,raw_y])
            m.return_from_external(1,12)
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
    assert allocated == [0x478,0x174,0x174], allocated
    assert next(allocations, None) is None
    assert [step['command'] for step in profile['steps'][:4]] == [0, 1000, 29, 30]
    assert profile['steps'][4]['command'] not in (0, 1000, 29, 30)
    assert inlined and {0x403B40} <= {a for s in outputs for a, _ in s['calls']}
    result = dict(name=profile['name'], steps=outputs, executable_sha256=program.sha256)
    if profile['retire']:
        helper = machine.words(state + 0x18, 1)[0]
        retired = machine.call(0x485870, ecx=helper, arguments=[1])
        assert retired.completed and freed == [helper], retired
        result['retirement'] = dict(helper=helper, hex=machine.read(helper, 0x478).hex())
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
    source = json.loads((directory / 'robber-native-input.json').read_text())
    native = json.loads((directory / 'robber-native-output.json').read_text())
    assert len(source['profiles']) == len(native['profiles']) == 2
    for profile in source['profiles']:
        verify_world_projection(profile, (directory / 'resources/LEVEL1/WORLDS/WORLD.WWD').read_bytes())
    original = [reference(profile) for profile in source['profiles']]
    (directory / 'robber-original-output.json').write_text(json.dumps(original, indent=2) + '\n')
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
    assert {0x4f63ec,0x485330,0x44c000,0x405000,0x44cfd0,0x4c96b0,0x4dc870,0x44d000,0x485960,0x44d3c0,0x43dfa0} <= owners
    trace = native['trace']
    positions = [trace.index(value) for value in
                 ('loadGridObject', 'scene.gameplay', 'ClawNativeRobberThief', '0x485270')]
    assert positions == sorted(positions)
    assert any('ClawActorResources' in event for event in trace)
    assert 'ClawNativeCanonicalHost.0x485870' in trace
    expected_controls = {'scene_destruction_retires_all_allocations', 'same_scene_recreates_actor_and_helper',
        'retired_helper_rejected', 'missing_resource_service_rejected', 'replacement_actor_rejected',
        'foreign_helper_rejected', 'service_outside_callback_rejected',
        'primary_logic_4c80e0_retires_helper', 'primary_logic_4c80c0_retires_helper',
        'replacement_logic_teardown_rejected', 'foreign_scene_pointer_rejected',
        'canonical_release_updates_scene_holder_globals'}
    assert expected_controls <= native['controls'].keys() and all(native['controls'].values()), native['controls']
    assert native['faults'] == 0 and not native['unresolvedDependencies']
    return dict(original_callback='0x485270', native_owner='ClawNativeRobberThief', comparisons=comparisons,
                exercised_service_edges=[f'0x{function:x}' for function in
                    sorted(owners | {0x4F6286, 0x4A48E0, 0x4F6974, 0x485870})],
                controls=native['controls'], faults=0, unresolved_dependencies=[],
                evidence='Original Level 3 WWD actor and assets attached without spatial residency to the established Level 1 scene fixture at original coordinates, five commands and same-scene recreation; no live-play claim')


def probe_failed_dispatch(snapshot_path):
    """Diagnostic original-only replay of a retained pre-dispatch scene graph.

    This is never connection evidence or a pass substitute. It preserves the
    failed native input so a coordinator can identify the next real source
    boundaries without scripting game callbacks. RNG is an explicit physical
    input, fixed at 99 for this diagnostic only.
    """
    from pathlib import Path
    snapshot_path = Path(snapshot_path).resolve()
    assert snapshot_path.is_relative_to(ROOT / 'work')
    profile = json.loads(snapshot_path.read_text())
    machine = Machine(claw(), 0x10000000, 4096)

    def map_span(address, size):
        for page in range(address & ~4095, (address + size + 4095) & ~4095, 4096):
            if not any(begin <= page <= end for begin, end, _ in machine.uc.mem_regions()):
                machine.uc.mem_map(page, 4096)

    original_vtable = machine.read(0x50f49c, 0xac)
    for block in profile['segments']:
        address, data = block['address'], bytes.fromhex(block['hex'])
        map_span(address, len(data)); machine.write(address, data)
    assert machine.read(0x50f49c, 0xac) == original_vtable
    for block in profile['inputGlobals']:
        machine.write(block['address'], bytes.fromhex(block['hex']))
    machine.write(profile['state'] + 0x1c, struct.pack('<I', profile['command']))
    bindings = {(b['receiver'], b['name']): b['token'] for b in profile['resourceBindings']}
    calls, services = [], []
    for target in (*OBSERVE, 0x44c840, 0x485d60, 0x485d90, 0x485ec0, 0x485f00):
        machine.observe(target, lambda m, a: calls.append(hex(a)))
    imports = {}
    for slot in (0x546d5c, 0x546cdc, 0x5469e8, 0x546cd4, 0x546d24):
        target = machine.words(slot, 1)[0]
        imports[target] = slot; map_span(target, 1); machine.intercept(target)
    for target in (0x4f6286, 0x4a3050):
        machine.intercept(target)

    def external(m, address):
        stack = m.register(UC_X86_REG_ESP)
        args = lambda count: list(m.words(stack + 4, count))
        slot = imports.get(address, address)
        if slot == 0x4a3050:
            services.append(['rand', 99]); m.return_from_external(99, 0)
        elif slot == 0x4f6286:
            key, output = args(2)
            name, receiver = string(m, key), m.register(UC_X86_REG_ECX)
            token = bindings[(receiver, name)]
            m.write(output, struct.pack('<I', token))
            services.append(['registry', receiver, name, token])
            m.return_from_external(int(token != 0), 8)
        elif slot in (0x546d5c, 0x546cdc):
            values = args(5 if slot == 0x546d5c else 1)
            m.write(values[0], struct.pack('<4I', *(values[1:] if slot == 0x546d5c else [0]*4)))
            m.return_from_external(1, len(values)*4)
        elif slot == 0x5469e8:
            pointer = args(1)[0]; value = (m.words(pointer, 1)[0]-1) & 0xffffffff
            m.write(pointer, struct.pack('<I', value)); m.return_from_external(value, 4)
        elif slot in (0x546cd4, 0x546d24):
            pointer, x, y = args(3)
            x, y = struct.unpack('<ii', struct.pack('<II', x, y))
            left, top, right, bottom = struct.unpack('<iiii', m.read(pointer, 16))
            if slot == 0x546cd4:
                m.return_from_external(int(left <= x < right and top <= y < bottom), 12)
            else:
                m.write(pointer, struct.pack('<iiii', left-x, top-y, right+x, bottom+y))
                m.return_from_external(1, 12)
        else:
            raise AssertionError(f'Unresolved diagnostic physical boundary {address:#x}')

    machine.on_external = external
    machine.reset_x87(); machine.set_x87_state(0x23f, 0, [])
    error = None
    try:
        result = machine.call(CALLBACK, arguments=[profile['actor']])
        completed = result.completed
        if not completed: error = str(result)
    except Exception as exc:
        completed = False; error = repr(exc)
    output = dict(diagnostic_only=True, command=profile['command'], completed=completed,
                  error=error, calls=calls, services=services, executable_sha256=claw().sha256)
    snapshot_path.with_name(snapshot_path.stem+'-original-probe.json').write_text(json.dumps(output, indent=2)+'\n')
    return output


if __name__ == '__main__':
    import sys
    assert len(sys.argv) == 3 and sys.argv[1] == 'probe-failure'
    print(json.dumps(probe_failed_dispatch(sys.argv[2])))
