"""FloorSpike scene join against the authenticated original instructions."""
import json
import struct
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x461D50
OBSERVE = {0x49E470: (False, 2), 0x49E4B0: (False, 3),
           0x4C79E0: (True, 2), 0x4C82A0: (True, 1),
           0x4CA610: (True, 4), 0x4C88E0: (True, 4),
           0x4B4430: (True, 0), 0x4F63EC: (False, 1)}
PHYSICAL = {0x71020014, 0x71010018, 0x7101001C, 0x71010020,
            0x71010024, 0x71010030, 0x7101003C, 0x71010040,
            0x71010044, 0x71010048}


def prepare(directory):
    directory = directory.resolve()
    root = directory / 'resources'
    root.mkdir(exist_ok=True)
    def link_tree(target, source):
        assert target.parent.resolve().is_relative_to(root)
        if source.is_dir():
            if target.is_symlink(): target.unlink()
            target.mkdir(exist_ok=True)
            for child in source.iterdir(): link_tree(target / child.name, child)
        elif not target.exists():
            if target.is_symlink(): target.unlink()
            target.symlink_to(source.resolve())
    for source in (ROOT / 'App/GameData').resolve().iterdir():
        link_tree(root / source.name, source)
    found = []
    for name, payload in entries():
        if name == 'LEVEL3/WORLDS/WORLD.WWD':
            (directory / 'WORLD3.WWD').write_bytes(payload)
        if name.startswith('LEVEL3/IMAGES/FLOORSPIKES2/') or name in (
                'LEVEL3/SOUNDS/FLOORSPIKEUP.WAV', 'LEVEL3/SOUNDS/FLOORSPIKEDOWN.WAV',
                'GAME/ANIS/FORWARD100.ANI', 'GAME/ANIS/BACKWARD100.ANI'):
            target = root / name.replace('LEVEL3/', 'LEVEL1/', 1)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink(): assert target.read_bytes() == payload, name
            else: target.write_bytes(payload)
            found.append(name)
    assert sum('/IMAGES/FLOORSPIKES2/' in name for name in found) == 6
    assert sum('/SOUNDS/' in name for name in found) == 2
    assert sum('/ANIS/' in name for name in found) == 2
    (directory / 'physical-assets.json').write_text(json.dumps(dict(asset_sha256=verify_assets(), files=found), indent=2)+'\n')


def string(machine, address):
    result = bytearray()
    for offset in range(256):
        value = machine.read(address + offset, 1)
        if value == b'\0': return result.decode('ascii')
        result.extend(value)
    raise AssertionError('Unterminated resource key')


def reference(profile):
    program = claw()
    machine = Machine(program, 0x10000000, 4096)
    pages = {page for start, end, _ in machine.uc.mem_regions()
             for page in range(start, end + 1, 4096)}
    def mapped(address, count):
        for page in range(address & ~4095, (address + count + 4095) & ~4095, 4096):
            if page not in pages:
                machine.uc.mem_map(page, 4096); pages.add(page)
    def put(address, *words):
        machine.write(address, struct.pack('<' + 'I' * len(words), *words))
    literals = {address: string(machine, address) for address in (0x529584, 0x52959C, 0x5295B0, 0x5295C0)}
    constant = machine.read(0x513768, 4)
    for segment in profile['segments']:
        data = bytes.fromhex(segment['hex'])
        mapped(segment['address'], len(data)); machine.write(segment['address'], data)
    assert {address: string(machine, address) for address in literals} == literals
    assert machine.read(0x513768, 4) == constant
    bindings = {(row['receiver'], row['name']): row['token'] for row in profile['resourceBindings']}
    assert len(bindings) == len(profile['resourceBindings'])
    calls, services, physical = [], [], []
    allocations = iter(profile['allocations'])
    for address, (thiscall, count) in OBSERVE.items():
        def observe(m, function, thiscall=thiscall, count=count):
            calls.append(dict(function=function, receiver=m.register(UC_X86_REG_ECX) if thiscall else 0,
                arguments=list(m.words(m.register(UC_X86_REG_ESP) + 4, count))))
        machine.observe(address, observe)
    for address in PHYSICAL | {0x4F6286, 0x4A48E0}:
        if address in PHYSICAL:
            mapped(address, 4); machine.write(address, b'\xc3')
        machine.intercept(address)
    def external(m, address):
        sp = m.register(UC_X86_REG_ESP)
        if address == 0x4F6286:
            name_pointer, output = m.words(sp + 4, 2)
            receiver, name = m.register(UC_X86_REG_ECX), string(m, name_pointer)
            token = bindings[(receiver, name)]
            put(output, token); services.append(['registry', receiver, name, token])
            m.return_from_external(int(token != 0), 8)
        elif address == 0x4A48E0:
            count = m.words(sp + 4, 1)[0]
            row = next(allocations); assert row['count'] == count == 56
            mapped(row['token'], count); machine.write(row['token'], b'\xcc' * count)
            services.append(['malloc', row['token'], count]); m.return_from_external(row['token'], 0)
        else:
            assert physical, f'Unexpected physical service {address:#x}'
            event = physical.pop(0); assert event['function'] == address
            args = list(m.words(sp + 4, len(event['arguments'])))
            if 'output' in event:
                assert args[:-1] == event['arguments'][:-1]
                value = event['output']
                if address == 0x71020014:
                    mapped(value, 16); put(value, m.words(args[1], 1)[0])
                put(args[-1], value)
            else: assert args == event['arguments'], (args, event)
            m.return_from_external(event['result'], len(args) * 4)
    machine.on_external = external
    outputs = []
    for step in profile['steps']:
        calls.clear(); services.clear(); physical[:] = step['physical']
        for segment in step['inputGlobals']:
            machine.write(segment['address'], bytes.fromhex(segment['hex']))
        result = machine.call(CALLBACK, arguments=[profile['actor']])
        assert result.completed and not physical, (profile['name'], step['name'])
        outputs.append(dict(name=step['name'], calls=list(calls), services=list(services),
            spans=[dict(address=span['address'], hex=machine.read(span['address'], span['count']).hex()) for span in step['spans']]))
    assert next(allocations, None) is None
    return dict(name=profile['name'], steps=outputs, executable_sha256=program.sha256)


def compare(directory):
    inputs = json.loads((directory / 'floor-spike-native-input.json').read_text())
    actual = json.loads((directory / 'floor-spike-native-output.json').read_text())
    assert len(inputs['profiles']) == len(actual['profiles']) == 2
    expected = [reference(profile) for profile in inputs['profiles']]
    (directory / 'floor-spike-original-output.json').write_text(json.dumps(expected, indent=2)+'\n')
    comparisons = 0
    for native, original in zip(actual['profiles'], expected, strict=True):
        assert native['name'] == original['name']
        for got, want in zip(native['steps'], original['steps'], strict=True):
            for key in ('name', 'calls', 'services', 'spans'):
                assert got[key] == want[key], (native['name'], got['name'], key)
            comparisons += 1
    trace = actual['trace']
    positions = [trace.index(item) for item in ('loadGridObject', 'scene.gameplay', 'ClawNativeFloorSpike', '0x461d50')]
    assert positions == sorted(positions)
    executed = {call['function'] for profile in actual['profiles'] for step in profile['steps'] for call in step['calls']}
    assert set(OBSERVE) <= executed
    for profile, source in zip(actual['profiles'], inputs['profiles'], strict=True):
        sounds = [event[2] for step in profile['steps'] for event in step['services']
                  if event[0] == 'registry' and event[2].startswith('LEVEL_FLOORSPIKE')]
        assert sounds == (['LEVEL_FLOORSPIKEUP', 'LEVEL_FLOORSPIKEDOWN']
                          if profile['name'] == 'sound-enabled' else [])
        assert len(source['allocations']) == (2 if sounds else 0)
        assert any(step['physical'] for step in source['steps']) == bool(sounds)
    assert all(actual['controls'].values()), actual['controls']
    assert actual['faults'] == 0 and not actual['unresolvedDependencies']
    return dict(original_callback='0x461d50', native_owner='ClawNativeFloorSpike', comparisons=comparisons,
        exercised_service_edges=[f'0x{address:x}' for address in sorted(executed | {0x4F6286, 0x4A48E0})],
        controls=actual['controls'], faults=0, unresolved_dependencies=[],
        evidence='Original Level 3 WWD and FloorSpike resources through the native scene; muted physical audio, no live-play claim')
