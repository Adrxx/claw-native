"""Scene-attached CutThroat against the authenticated original callback.

Only physical allocation and resource dictionaries are intercepted. Constructors,
virtual lifecycle methods, state lookup and animation execute original code.
"""
import json
import struct
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x4379D0
OBSERVE = (0x4F63EC, 0x437A90, 0x44C000, 0x4DCA10, 0x403B40, 0x405000,
           0x4C7FA0, 0x4C8060, 0x4C7970, 0x4062E0, 0x4061B0, 0x4C8220,
           0x4F6439, 0x4DC180, 0x4DB620, 0x4DBE10, 0x4DBD60, 0x4DBCD0,
           0x420FC0, 0x4DBD20, 0x4DC870, 0x44CFD0, 0x4C96B0,
           0x44D000, 0x438100, 0x44D3C0, 0x4C82A0)


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
        if name == 'LEVEL3/WORLDS/WORLD.WWD':
            (directory / 'WORLD3.WWD').write_bytes(payload)
        if name.startswith(('LEVEL3/IMAGES/CUTTHROAT/', 'LEVEL3/ANIS/CUTTHROAT/')):
            target = level / name.removeprefix('LEVEL3/')
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink() or target.parent.is_symlink():
                raise AssertionError('Refuse to overwrite shared resource symlink')
            target.write_bytes(payload)
            found.append(name)
    assert any('/IMAGES/' in name for name in found), 'Missing original CutThroat image set'
    assert any('/ANIS/' in name for name in found), 'Missing original CutThroat animations'
    (directory / 'physical-assets.json').write_text(json.dumps(dict(asset_sha256=verify_assets(), files=found), indent=2)+'\n')


def string(machine, address):
    value = bytearray()
    for offset in range(256):
        byte = machine.read(address + offset, 1)
        if byte == b'\0':
            return value.decode('ascii')
        value.extend(byte)
    raise AssertionError('Unterminated physical dictionary key')


def reference(profile, require_complete=True):
    program = claw()
    machine = Machine(program, 0x10000000, 4096)
    mapped = {0x10000000}
    def map_span(address, size):
        for page in range(address & ~4095, (address + size + 4095) & ~4095, 4096):
            if page in mapped or any(begin <= page <= end for begin, end, _ in machine.uc.mem_regions()):
                continue
            machine.uc.mem_map(page, 4096)
            mapped.add(page)
    # Native projections cannot replace original immutable inputs unnoticed.
    reviewed = [(0x50C934, 76), (0x50C928, 4), (0x5262B0, 12),
                (0x513740, 40), (0x50BA88, 8), (0x50BAC8, 8),
                (0x50B090, 24), (0x50E008, 8), (0x513E10, 16),
                (0x513E40, 4), (0x513E48, 16), (0x50E0C0, 4),
                (0x510020, 4)]
    for address in (0x5246F8, 0x527D50, 0x527D40, 0x527D34,
                    0x5266EC, 0x524870, 0x524864, 0x524858, 0x52484C,
                    0x5266DC, 0x522D48, 0x522D54, 0x523148, 0x5234B4,
                    0x526B24, 0x526B40, 0x526B5C, 0x526B78, 0x526B94,
                    0x526BB0, 0x526BCC, 0x526BE4, 0x526BFC, 0x526C14,
                    0x526C2C, 0x526C44, 0x526C5C, 0x526C74, 0x526C8C,
                    0x526CA4, 0x526CBC, 0x526CD4, 0x526CEC, 0x526D04,
                    0x526D1C, 0x526D34):
        reviewed.append((address, len(string(machine, address)) + 1))
    imports = {slot: machine.read(slot, 4) for slot in machine.import_stub}
    original_metadata = {address: machine.read(address, size) for address, size in reviewed}
    for segment in profile['segments']:
        address, data = segment['address'], bytes.fromhex(segment['hex'])
        map_span(address, len(data))
        machine.write(address, data)
    for slot, data in imports.items():
        machine.write(slot, data)
    for address, data in original_metadata.items():
        assert machine.read(address, len(data)) == data, f'Native metadata differs from original at {address:#x}'
    actor, state = profile['actor'], profile['state']
    allocations = iter(profile['allocations'])
    bindings = {(b['receiver'], b['name']): b['token'] for b in profile['resourceBindings']}
    assert len(bindings) == len(profile['resourceBindings'])
    assert {name for _, name in bindings} >= {'LogicHit', 'LogicAttack', 'LEVEL_CUTTHROAT', 'LEVEL_CUTTHROAT_WALK'}
    required = {'LogicHit', 'LogicAttack', 'LEVEL_CUTTHROAT', 'LEVEL_CUTTHROAT_WALK'}
    assert all(token for (_, name), token in bindings.items() if name in required), 'Required real metadata and resources must be nonzero'
    calls, services, allocated = [], [], []
    current_command = None
    in_base = False
    inline_rectangles = 0
    inline_integrations = 0
    def observe(m, address):
        nonlocal in_base, inline_integrations
        if address == 0x44C000:
            in_base = True
        elif address == 0x4C7970:
            in_base = False
        # LevelOneEnemyActionsRuntime.motion calls its integrate body directly;
        # the constructor's separate 4dca10 owner remains a compared edge.
        if address == 0x4DCA10 and current_command not in (None, 0):
            inline_integrations += 1
            return
        calls.append([address, 0 if address in (0x4F63EC, 0x4DC870) else m.register(UC_X86_REG_ECX)])
    for function in OBSERVE:
        machine.observe(function, observe)
    machine.intercept(0x4A48E0)
    machine.intercept(0x4F6286)
    machine.intercept(0x4A3050)
    random_values = iter(profile['randomValues'])
    def external(m, address):
        nonlocal inline_rectangles
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
        elif address == 0x4A3050:
            value = next(random_values)
            services.append(['rand', value])
            m.return_from_external(value, 0)
        else:
            slot = next((slot for slot, target in machine.import_stub.items() if target == address), address)
            arguments = lambda n: machine.words(stack + 4, n)
            if slot == 0x546D5C:
                output, *values = arguments(5)
                machine.write(output, struct.pack('<4I', *values))
                # The admitted base constructor implements its Win32 rectangle
                # operations as direct writes. Compare those helper bytes below;
                # the derived constructor's actual service calls stay ordered.
                if in_base:
                    inline_rectangles += 1
                else:
                    services.append(['rectangle', output, *values])
                m.return_from_external(1, 20)
            elif slot == 0x546CDC:
                output = arguments(1)[0]
                machine.write(output, bytes(16))
                if in_base:
                    inline_rectangles += 1
                else:
                    services.append(['empty-rectangle', output])
                m.return_from_external(1, 4)
            elif slot == 0x5469E8:
                output = arguments(1)[0]
                value = (machine.words(output, 1)[0] - 1) & 0xFFFFFFFF
                machine.write(output, struct.pack('<I', value))
                m.return_from_external(value, 4)
            elif slot == 0x546CD4:
                pointer, x, y = arguments(3)
                left, top, right, bottom = struct.unpack('<4i', machine.read(pointer, 16))
                x, y = struct.unpack('<2i', struct.pack('<2I', x, y))
                m.return_from_external(int(left <= x < right and top <= y < bottom), 12)
            else:
                raise AssertionError(('Unexpected physical service', hex(address), hex(slot)))
    machine.on_external = external
    machine.reset_x87()
    machine.set_x87_state(0x23f, 0, [])
    outputs = []
    for step in profile['steps']:
        calls.clear(); services.clear()
        current_command = step['command']
        inline_rectangles = inline_integrations = 0
        machine.write(state + 0x1C, struct.pack('<I', step['command']))
        for segment in step['inputGlobals']:
            machine.write(segment['address'], bytes.fromhex(segment['hex']))
        result = machine.call(CALLBACK, arguments=[actor])
        assert result.completed, (profile['name'], step['command'], result)
        assert inline_rectangles == (11 if current_command == 0 else 0)
        assert inline_integrations == (1 if current_command not in (0, 1000, 29, 30) else 0)
        outputs.append(dict(command=step['command'], calls=list(calls), services=list(services),
            spans=[dict(address=span['address'], hex=machine.read(span['address'], span['count']).hex()) for span in step['spans']]))
    assert allocated[0] == 0x480 and allocated.count(0x174) >= 2, allocated
    assert next(allocations, None) is None
    if require_complete:
        assert [step['command'] for step in profile['steps'][:4]] == [0, 1000, 29, 30]
        assert len(profile['steps']) == 5 and profile['steps'][4]['command'] not in (0, 1000, 29, 30)
    assert next(random_values, None) is None
    return dict(name=profile['name'], steps=outputs, executable_sha256=program.sha256)


def compare(directory):
    source = json.loads((directory / 'cut-throat-native-input.json').read_text())
    native = json.loads((directory / 'cut-throat-native-output.json').read_text())
    assert len(source['profiles']) == len(native['profiles']) == 2
    original = [reference(profile) for profile in source['profiles']]
    (directory / 'cut-throat-original-output.json').write_text(json.dumps(original, indent=2)+'\n')
    comparisons = 0
    for expected, actual in zip(original, native['profiles'], strict=True):
        assert expected['name'] == actual['name']
        for ref, got in zip(expected['steps'], actual['steps'], strict=True):
            def calls_at_boundary(rows, temporary):
                # 4dbe10 constructs a synchronous temporary bitset. Native
                # stackless transport reserves its own explicit caller frame;
                # no stack pointer escapes into the compared persistent graph.
                return [[function, 'temporary-bitset' if receiver == temporary and
                         function in (0x4DBE10, 0x4DB620, 0x4DBCD0) else receiver]
                        for function, receiver in rows]
            assert calls_at_boundary(ref['calls'], 0x02007FA0) == calls_at_boundary(got['calls'], 0x02007DE4)
            for key in ('command', 'services', 'spans'):
                assert ref[key] == got[key], (actual['name'], got['command'], key, ref[key] if key != 'spans' else 'see original output', got[key] if key != 'spans' else 'see native output')
            comparisons += 1
    expected_owners = {0x4F63EC, 0x437A90, 0x44C000, 0x405000, 0x4C7FA0,
                       0x4C8060, 0x44CFD0, 0x4C96B0, 0x4DC870, 0x44D000,
                       0x438100, 0x44D3C0}
    actual_owners = {a for p in native['profiles'] for s in p['steps'] for a, _ in s['calls']}
    assert expected_owners <= actual_owners
    trace = native['trace']
    positions = [trace.index(value) for value in ['loadGridObject', 'scene.gameplay', 'ClawNativeCutThroat', '0x4379d0']]
    assert positions == sorted(positions)
    assert any('ClawActorResources' in event for event in trace)
    assert any('0x438010' in event for event in trace)
    assert all(native['controls'].values()), native['controls']
    assert native['faults'] == 0 and not native['unresolvedDependencies']
    return dict(original_callback='0x4379d0', native_owner='ClawNativeCutThroat', comparisons=comparisons,
                exercised_service_edges=[f'0x{function:x}' for function in sorted(actual_owners | {0x4F6286, 0x4A48E0, 0x4F6974, 0x438010, 0x4F4680})],
                controls=native['controls'], faults=0, unresolved_dependencies=[],
                evidence='Actual Level 3 WWD actor with original CutThroat resources in the existing native scene; no live-play claim')
