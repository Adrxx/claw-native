"""SawBlade scene join against the authenticated original instructions."""
import json
import struct
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x462040
OBSERVE = {0x49E470: (False, 2), 0x49E4B0: (False, 3),
           0x4C79E0: (True, 2), 0x4C82A0: (True, 1),
           0x4CA610: (True, 4)}


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
        if name == 'LEVEL9/WORLDS/WORLD.WWD':
            (directory / 'WORLD9.WWD').write_bytes(payload)
        if name.startswith('LEVEL9/IMAGES/FLOORSAW/') or name.startswith('LEVEL9/ANIS/SAWBLADE/'):
            target = root / name.replace('LEVEL9/', 'LEVEL1/', 1)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink(): assert target.read_bytes() == payload, name
            else: target.write_bytes(payload)
            found.append(name)
    assert sum('/IMAGES/FLOORSAW/' in name for name in found) == 20
    assert sum('/ANIS/' in name for name in found) == 3
    original_names = {name for name, _ in entries()}
    assert not any(name.endswith(('/SAWBLADEUP.WAV', '/SAWBLADEDOWN.WAV')) for name in original_names)
    (directory / 'physical-assets.json').write_text(json.dumps(dict(asset_sha256=verify_assets(), files=found,
        missing_requested_sounds=['LEVEL_SAWBLADEUP', 'LEVEL_SAWBLADEDOWN']), indent=2)+'\n')


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
    literals = {address: string(machine, address) for address in (0x5295D4, 0x5295E8, 0x5295FC, 0x529610, 0x529624)}
    constant = machine.read(0x513768, 4)
    for segment in profile['segments']:
        data = bytes.fromhex(segment['hex'])
        mapped(segment['address'], len(data)); machine.write(segment['address'], data)
    assert {address: string(machine, address) for address in literals} == literals
    assert machine.read(0x513768, 4) == constant
    bindings = {(row['receiver'], row['name']): row['token'] for row in profile['resourceBindings']}
    assert len(bindings) == len(profile['resourceBindings'])
    calls, services = [], []
    assert not profile['allocations']
    for address, (thiscall, count) in OBSERVE.items():
        def observe(m, function, thiscall=thiscall, count=count):
            calls.append(dict(function=function, receiver=m.register(UC_X86_REG_ECX) if thiscall else 0,
                arguments=list(m.words(m.register(UC_X86_REG_ESP) + 4, count))))
        machine.observe(address, observe)
    machine.intercept(0x4F6286)
    def external(m, address):
        sp = m.register(UC_X86_REG_ESP)
        if address == 0x4F6286:
            name_pointer, output = m.words(sp + 4, 2)
            receiver, name = m.register(UC_X86_REG_ECX), string(m, name_pointer)
            token = bindings[(receiver, name)]
            put(output, token); services.append(['registry', receiver, name, token])
            m.return_from_external(int(token != 0), 8)
        else:
            raise AssertionError(f'Unexpected external service {address:#x}')
    machine.on_external = external
    outputs = []
    for step in profile['steps']:
        calls.clear(); services.clear(); assert not step['physical']
        for segment in step['inputGlobals']:
            machine.write(segment['address'], bytes.fromhex(segment['hex']))
        result = machine.call(CALLBACK, arguments=[profile['actor']])
        assert result.completed, (profile['name'], step['name'])
        outputs.append(dict(name=step['name'], calls=list(calls), services=list(services),
            spans=[dict(address=span['address'], hex=machine.read(span['address'], span['count']).hex()) for span in step['spans']]))
    return dict(name=profile['name'], steps=outputs, executable_sha256=program.sha256)


def compare(directory):
    inputs = json.loads((directory / 'saw-blade-native-input.json').read_text())
    actual = json.loads((directory / 'saw-blade-native-output.json').read_text())
    assert len(inputs['profiles']) == len(actual['profiles']) == 2
    expected = [reference(profile) for profile in inputs['profiles']]
    (directory / 'saw-blade-original-output.json').write_text(json.dumps(expected, indent=2)+'\n')
    comparisons = 0
    for native, original in zip(actual['profiles'], expected, strict=True):
        assert native['name'] == original['name']
        for got, want in zip(native['steps'], original['steps'], strict=True):
            for key in ('name', 'calls', 'services', 'spans'):
                assert got[key] == want[key], (native['name'], got['name'], key)
            comparisons += 1
    trace = actual['trace']
    positions = [trace.index(item) for item in ('loadGridObject', 'scene.gameplay', 'ClawNativeSawBlade', '0x462040')]
    assert positions == sorted(positions)
    assert trace.index("ClawActorResources.0x4f6286") > positions[-1]
    assert trace.index("ClawNativeAudio.0x4f6286") > positions[-1]
    executed = {call['function'] for profile in actual['profiles'] for step in profile['steps'] for call in step['calls']}
    assert set(OBSERVE) <= executed
    for profile, source in zip(actual['profiles'], inputs['profiles'], strict=True):
        sounds = [event[2] for step in profile['steps'] for event in step['services']
                  if event[0] == 'registry' and event[2].startswith(('LEVEL_SAWBLADEUP', 'LEVEL_SAWBLADEDOWN'))]
        assert sounds == (['LEVEL_SAWBLADEUP', 'LEVEL_SAWBLADEDOWN']
                          if profile['name'] == 'sound-enabled' else [])
        assert not source['allocations'] and not any(step['physical'] for step in source['steps'])
        assert all(event[3] == 0 for step in profile['steps'] for event in step['services'] if event[0] == 'registry' and event[2] in sounds)
    assert all(actual['controls'].values()), actual['controls']
    assert actual['faults'] == 0 and not actual['unresolvedDependencies']
    return dict(original_callback='0x462040', native_owner='ClawNativeSawBlade', comparisons=comparisons,
        exercised_service_edges=[f'0x{address:x}' for address in sorted(executed | {0x4F6286})],
        controls=actual['controls'], faults=0, unresolved_dependencies=[],
        missing_original_sound_resources=['LEVEL_SAWBLADEUP', 'LEVEL_SAWBLADEDOWN'],
        evidence='Original Level 9 WWD and SawBlade resources through the native scene; original up/down sound resources absent so ordered missing lookups are compared; muted, no live-play claim')
