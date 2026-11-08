"""Scene-attached TowerCannonRight against the authenticated original callback.

Only physical allocation and resource dictionaries are intercepted. Constructors,
virtual lifecycle methods, state lookup and animation execute original code.
"""
import json
import struct
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x495E00
OBSERVE = (0x4F63EC, 0x495F90, 0x4C7FA0, 0x4C8060, 0x4C8160, 0x4C7970,
           0x4145B0, 0x4DBA00, 0x4C8220, 0x4C96B0, 0x4DC870, 0x4C9E30,
           0x4141F0, 0x4145F0, 0x4041B0, 0x4C82A0)


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
        if name == 'LEVEL2/WORLDS/WORLD.WWD':
            (directory / 'WORLD2.WWD').write_bytes(payload)
        if name.startswith(('LEVEL2/IMAGES/TOWERCANNONRIGHT/', 'LEVEL2/ANIS/TOWERCANNONRIGHT/')):
            target = level / name.removeprefix('LEVEL2/')
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink() or target.parent.is_symlink():
                raise AssertionError('Refuse to overwrite shared resource symlink')
            target.write_bytes(payload)
            found.append(name)
    assert any('/IMAGES/' in name for name in found), 'Missing original cannon image set'
    assert any('/ANIS/' in name for name in found), 'Missing original cannon animations'
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
    reviewed = [(0x50FA8C, 36), (0x513740, 40), (0x50B9C4, 4), (0x510020, 4)]
    reviewed += [(address, len(string(machine, address).encode('ascii')) + 1) for address in (0x522D54, 0x522D48, 0x5234EC, 0x524538, 0x524548, 0x52CE80, 0x52CE9C, 0x52CEBC)]
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
    assert {name for _, name in bindings} >= {'LogicHit', 'LogicAttack', 'LEVEL_TOWERCANNONRIGHT', 'LEVEL_TOWERCANNONRIGHT_HOME', 'LEVEL_TOWERCANNONRIGHT_FIRING'}
    assert all(value for value in bindings.values()), 'Real metadata and resources must be nonzero'
    calls, services, allocated = [], [], []
    for function in OBSERVE:
        machine.observe(function, lambda m, a: calls.append([a, 0 if a in (0x4F63EC, 0x4DC870) else m.register(UC_X86_REG_ECX)]))
    machine.intercept(0x4A48E0)
    machine.intercept(0x4F6286)
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
            m.return_from_external(1, 8)
        else:
            raise AssertionError(hex(address))
    machine.on_external = external
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
    assert allocated == [0x7C, 0x174, 0x174], allocated
    assert next(allocations, None) is None
    assert [step['command'] for step in profile['steps'][:4]] == [0, 1000, 29, 30]
    assert profile['steps'][4]['command'] >= 2000
    return dict(name=profile['name'], steps=outputs, executable_sha256=program.sha256)


def compare(directory):
    source = json.loads((directory / 'tower-native-input.json').read_text())
    native = json.loads((directory / 'tower-native-output.json').read_text())
    assert len(source['profiles']) == len(native['profiles']) == 2
    original = [reference(profile) for profile in source['profiles']]
    (directory / 'tower-original-output.json').write_text(json.dumps(original, indent=2)+'\n')
    comparisons = 0
    for expected, actual in zip(original, native['profiles'], strict=True):
        assert expected['name'] == actual['name']
        for ref, got in zip(expected['steps'], actual['steps'], strict=True):
            for key in ('command', 'calls', 'services', 'spans'):
                assert ref[key] == got[key], (actual['name'], got['command'], key, ref[key] if key != 'spans' else 'see original output', got[key] if key != 'spans' else 'see native output')
            comparisons += 1
    expected_owners = {0x4F63EC, 0x495F90, 0x4C7FA0, 0x4C8060, 0x4C8160, 0x4C96B0, 0x4DC870, 0x4C9E30, 0x4141F0, 0x4145F0, 0x4041B0}
    actual_owners = {a for p in native['profiles'] for s in p['steps'] for a, _ in s['calls']}
    assert expected_owners <= actual_owners
    trace = native['trace']
    positions = [trace.index(value) for value in ['loadGridObject', 'scene.gameplay', 'ClawNativeTowerCannonRight', '0x495e00']]
    assert positions == sorted(positions)
    assert any('ClawActorResources' in event for event in trace)
    assert 'ClawStackedActorLifecycle.0x484d90' in trace
    assert all(native['controls'].values()), native['controls']
    assert native['faults'] == 0 and not native['unresolvedDependencies']
    return dict(original_callback='0x495e00', native_owner='ClawNativeTowerCannonRight', comparisons=comparisons,
                exercised_service_edges=[f'0x{function:x}' for function in sorted(actual_owners | {0x4F6286, 0x4A48E0, 0x4F6974, 0x484D90, 0x4F4680})],
                controls=native['controls'], faults=0, unresolved_dependencies=[],
                evidence='Actual Level 2 WWD actor with original cannon resources in the existing native scene; no live-play claim')
