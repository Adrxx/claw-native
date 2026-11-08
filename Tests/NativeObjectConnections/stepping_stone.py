"""SteppingStone scene join against the authenticated original instructions."""
import json
import re
import struct
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP
from Tests.clawparity.kernel import EmulationFault, Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x49E810
OBSERVE = {0x40F680: (True, 1), 0x49E470: (False, 2), 0x49E4B0: (False, 3),
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
        if name == 'LEVEL4/WORLDS/WORLD.WWD':
            (directory / 'WORLD4.WWD').write_bytes(payload)
        if name.startswith('LEVEL4/IMAGES/STEPPINGSTONE/') or name in (
                'LEVEL4/SOUNDS/STONERISE3.WAV',
                'GAME/ANIS/FORWARD50.ANI', 'GAME/ANIS/BACKWARD50.ANI'):
            target = root / name.replace('LEVEL4/', 'LEVEL1/', 1)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink(): assert target.read_bytes() == payload, name
            else: target.write_bytes(payload)
            found.append(name)
    assert sum('/IMAGES/STEPPINGSTONE/' in name for name in found) == 6
    assert sum('/SOUNDS/' in name for name in found) == 1
    assert sum('/ANIS/' in name for name in found) == 2
    unlinked = directory / 'resources-unlinked'
    unlinked.mkdir(exist_ok=True)
    def link_without_images(target, source):
        if source.relative_to(root).as_posix() == 'LEVEL1/IMAGES/STEPPINGSTONE':
            return
        if source.is_dir():
            target.mkdir(exist_ok=True)
            for child in source.iterdir(): link_without_images(target / child.name, child)
        elif not target.exists(): target.symlink_to(source.resolve())
    for source in root.iterdir(): link_without_images(unlinked / source.name, source)
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
    literals = {address: string(machine, address) for address in (0x52DD7C, 0x52DD04, 0x52DD14, 0x52DD8C)}
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
        assert {row['address'] for row in step['inputGlobals']} == {0x537210, 0x5430c4, 0x532c0c, 0x532c10}
        assert all(len(bytes.fromhex(row['hex'])) == 4 for row in step['inputGlobals'])
        for segment in step['inputGlobals']:
            machine.write(segment['address'], bytes.fromhex(segment['hex']))
        expected_fault = step.get('expectedFault')
        try:
            result = machine.call(CALLBACK, arguments=[profile['actor']])
        except EmulationFault as error:
            # Machine maps page zero for FS. Its authenticated null-access
            # guard stops before Unicorn can raise an unmapped-memory event.
            fault = re.fullmatch(r'null pointer access at (0x[0-9a-f]+) from instruction (0x[0-9a-f]+)', str(error))
            assert fault is not None, str(error)
            address, instruction = (int(value, 16) for value in fault.groups())
            assert address == expected_fault == 0x68, (step['name'], str(error), expected_fault)
            assert instruction == machine.register(UC_X86_REG_EIP) == 0x4c86ad
        else:
            assert expected_fault is None and result.completed, (profile['name'], step['name'])
        assert not physical
        outputs.append(dict(name=step['name'], expectedFault=expected_fault, calls=list(calls), services=list(services),
            spans=[dict(address=span['address'], hex=machine.read(span['address'], span['count']).hex()) for span in step['spans']]))
    assert next(allocations, None) is None
    return dict(name=profile['name'], steps=outputs, executable_sha256=program.sha256)


def compare(directory):
    inputs = json.loads((directory / 'stepping-stone-native-input.json').read_text())
    actual = json.loads((directory / 'stepping-stone-native-output.json').read_text())
    assert len(inputs['profiles']) == len(actual['profiles']) == 4
    expected = [reference(profile) for profile in inputs['profiles']]
    (directory / 'stepping-stone-original-output.json').write_text(json.dumps(expected, indent=2)+'\n')
    comparisons = 0
    fault_comparisons = []
    for native, original in zip(actual['profiles'], expected, strict=True):
        assert native['name'] == original['name']
        for got, want in zip(native['steps'], original['steps'], strict=True):
            for key in ('name', 'expectedFault', 'calls', 'services', 'spans'):
                assert got[key] == want[key], (native['name'], got['name'], key)
            if got['expectedFault'] is None:
                comparisons += 1
            else:
                fault_comparisons.append(dict(profile=native['name'], step=got['name'], original_and_native_address=hex(got['expectedFault'])))
    for profile in actual['profiles']:
        names = {step['name'] for step in profile['steps']}
        assert {'initialize', 'visible-timer-true', 'visible-timer-equal', 'visible-timer-false'} <= names
        if profile['name'].startswith('linked-'):
            assert {'disappear', 'hidden-timer-false', 'hidden-timer-equal', 'reappear', 'returned-visible'} <= names
    trace = actual['trace']
    positions = [trace.index(item) for item in ('loadGridObject', 'scene.gameplay', 'ClawNativeSteppingStone', '0x49e810')]
    assert positions == sorted(positions)
    executed = {call['function'] for profile in actual['profiles'] for step in profile['steps'] for call in step['calls']}
    assert set(OBSERVE) <= executed
    for profile, source in zip(actual['profiles'], inputs['profiles'], strict=True):
        sounds = [event[2] for step in profile['steps'] for event in step['services']
                  if event[0] == 'registry' and event[2] in ('LEVEL_STONERISE', 'LEVEL_STONESINK')]
        assert sounds == (['LEVEL_STONERISE', 'LEVEL_STONESINK']
                          if profile['name'] in ('linked-controlled-sound-enabled', 'linked-exact-disc-sound-enabled') else [])
        playback = profile['name'] == 'linked-controlled-sound-enabled'
        assert len(source['allocations']) == (2 if playback else 0)
        assert any(step['physical'] for step in source['steps']) == playback
        if profile['name'] == 'linked-exact-disc-sound-enabled':
            assert all(event[3] == 0 for step in profile['steps'] for event in step['services'] if event[0] == 'registry' and event[2] in sounds)
        if profile['name'] == 'unlinked-sound-disabled':
            assert profile['steps'][-1]['expectedFault'] in (0x64, 0x68)
    required_controls = {'missing_service_rejected', 'replacement_actor_rejected',
        'replacement_private_state_rejected', 'service_outside_callback_rejected',
        'scene_destruction_retires_actor_and_private_state', 'retired_owner_rejected',
        'linked_image_rebinding_rejected', 'profile_rebinding_rejected', 'replacement_audio_resource_rejected', 'unlinked_original_fault_boundary', 'image_table_rebinding_rejected', 'image_header_replacement_rejected',
        'audio_manager_rebinding_rejected', 'animation_manager_rebinding_rejected'}
    assert required_controls <= actual['controls'].keys()
    assert all(actual['controls'].values()), actual['controls']
    assert actual['faults'] == 0 and not actual['unresolvedDependencies']
    return dict(original_callback='0x49e810', native_owner='ClawNativeSteppingStone', comparisons=comparisons,
        exercised_service_edges=[f'0x{address:x}' for address in sorted(executed | {0x4F6286, 0x4A48E0})],
        controls=actual['controls'], faults=0, unresolved_dependencies=[], expected_fault_comparisons=fault_comparisons,
        evidence='Original Level 4 WWD, source level profile, linked and missing physical image banks, timer boundary cycle, exact-name sound misses and separately controlled sound-bank PCM playback through real muted audio through the native scene; no live-play claim', executable_sha256=claw().sha256, asset_sha256=verify_assets())
