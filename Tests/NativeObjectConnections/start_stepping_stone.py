"""Original StartSteppingStone replay of scene-owned physical input graphs."""
import json
import struct

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x49EB30
RESOURCE = 0x4F6286
ENTRIES = {0x40F680: 1, 0x4C79E0: 2, 0x4C82A0: 1, RESOURCE: 2}


def prepare(directory):
    """Keep the app assets unchanged; mount only this object's original PIDs."""
    target = directory / 'assets'
    target.mkdir(exist_ok=True)

    def link_tree(destination, source):
        if source.is_dir():
            if destination.is_symlink():
                destination.unlink()
            destination.mkdir(exist_ok=True)
            for child in source.iterdir():
                link_tree(destination / child.name, child)
        elif not destination.exists():
            if destination.is_symlink():
                destination.unlink()
            destination.symlink_to(source.resolve())

    for source in (ROOT / 'App/GameData').iterdir():
        link_tree(target / source.name, source)
    found = set()
    for name, payload in entries():
        if name == 'LEVEL4/WORLDS/WORLD.WWD':
            (directory / 'WORLD4.WWD').write_bytes(payload)
            found.add(name)
        if name.startswith('LEVEL4/IMAGES/STEPPINGSTONE/'):
            path = target / 'LEVEL1' / name.removeprefix('LEVEL4/')
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_symlink():
                assert path.read_bytes() == payload, name
            else:
                path.write_bytes(payload)
            found.add(name)
        if name in ('GAME/ANIS/FORWARD50.ANI', 'GAME/ANIS/BACKWARD50.ANI'):
            assert (target / name).read_bytes() == payload, name
            found.add(name)
    assert len(found) == 9, found


def reference(profile):
    program = claw()
    machine = Machine(program, 0x10000000, 4096)
    mapped = {page for begin, end, _ in machine.uc.mem_regions()
              for page in range(begin, end + 1, 4096)}
    all_rows = profile['segments'] + profile['globals']
    spans = [(row['address'], bytes.fromhex(row['hex'])) for row in all_rows]
    for address, data in spans:
        for page in range(address & ~4095, (address + len(data) + 4095) & ~4095, 4096):
            if page not in mapped:
                machine.uc.mem_map(page, 4096)
                mapped.add(page)
        machine.write(address, data)

    def bounded_access(uc, kind, address, size, value, user):
        if not any(start <= address and address + size <= start + len(data) for start, data in spans):
            raise AssertionError(f'Original access outside exported scene graph {address:#x}+{size}')

    graph_pages = {page for start, data in spans if start >= 0x10000000
                   for page in range(start & ~4095, (start + len(data) + 4095) & ~4095, 4096)}
    for page in graph_pages:
        machine.uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, bounded_access, begin=page, end=page+4095)
    bindings = {(row['receiver'], row['name']): row['token'] for row in profile['resourceBindings']}
    assert len(bindings) == len(profile['resourceBindings'])
    services, executed = [], set()

    def string(token):
        result = bytearray()
        for index in range(256):
            byte = machine.read(token + index, 1)
            if byte == b'\0':
                return result.decode('ascii')
            result.extend(byte)
        raise AssertionError('Unterminated resource name')

    def observe(uc, address, size, user):
        executed.add(address)
        if address in ENTRIES:
            args = list(machine.words(machine.register(UC_X86_REG_ESP) + 4, ENTRIES[address]))
            services.append(dict(function=address, receiver=machine.register(UC_X86_REG_ECX),
                                 arguments=args[:1] if address == RESOURCE else args))

    for address in set(ENTRIES) | {CALLBACK}:
        machine.uc.hook_add(UC_HOOK_CODE, observe, begin=address, end=address)
    machine.intercept(RESOURCE)

    def physical(m, address):
        assert address == RESOURCE, hex(address)
        name, output = m.words(m.register(UC_X86_REG_ESP) + 4, 2)
        key = (m.register(UC_X86_REG_ECX), string(name))
        assert key in bindings, key
        token = bindings[key]
        m.write(output, struct.pack('<I', token))
        m.return_from_external(int(token != 0), 8)

    machine.on_external = physical

    def capture(rows):
        return [dict(address=s['address'], hex=machine.read(s['address'], len(bytes.fromhex(s['hex']))).hex()) for s in rows]

    outputs = []
    for step in profile['steps']:
        services.clear()
        executed.clear()
        # Only clock, real player support flags/token and selection are inputs.
        allowed = {0x5430C4, profile['player'] + 8, profile['player'] + 0x80, profile['selection']}
        assert all(row['address'] in allowed for row in step['inputs'])
        for row in step['inputs']:
            machine.write(row['address'], struct.pack('<I', row['value']))
        result = machine.call(CALLBACK, arguments=[profile['actor']])
        assert result.completed, step['name']
        outputs.append(dict(name=step['name'], segments=capture(profile['segments']),
                            globals=capture(profile['globals']), services=list(services), executed=sorted(executed)))
    return dict(name=profile['name'], steps=outputs)


def compare(directory):
    source = json.loads((directory / 'stone-input.json').read_text())
    actual = json.loads((directory / 'stone-output.json').read_text())
    expected = [reference(profile) for profile in source['profiles']]
    (directory / 'stone-original.json').write_text(json.dumps(expected, indent=2) + '\n')
    count = 0
    for native, original in zip(actual['profiles'], expected, strict=True):
        assert native['name'] == original['name']
        for native_step, original_step in zip(native['steps'], original['steps'], strict=True):
            for key in ('name', 'segments', 'globals', 'services'):
                if native_step[key] != original_step[key]:
                    raise AssertionError(f"{native['name']}/{native_step['name']}: mismatch in {key}")
            count += 1
        names = {step['name'] for step in original['steps']}
        assert {'initialize', 'absent-support', 'wrong-support', 'landing', 'delay-state',
                'disappeared', 'reappear', 'returned-idle'} <= names
    assert len(expected) == 2
    reached = {call['function'] for profile in expected for step in profile['steps'] for call in step['services']}
    assert reached == set(ENTRIES), reached
    assert all(actual['controls'].values())
    return dict(original_callback='0x49eb30', native_owner='ClawNativeStartSteppingStone', comparisons=count,
        exercised_service_edges=['loadGridObject -> scene.gameplay -> ClawNativeStartSteppingStone -> 0x49eb30',
            '0x49eb30 -> 0x40f680 canonical pickup_points over ClawActorResources image geometry',
            '0x49eb30 -> 0x4c79e0 canonical actor_animation -> 0x4f6286 / ClawActorResources',
            '0x49eb30 -> 0x4c82a0 canonical actor_animation -> 0x40f680',
            '0x49eb30 -> scene player support/selection chain and source level profile 0x537960'],
        controls=actual['controls'], faults=actual['faults'], unresolved_dependencies=actual['unresolvedDependencies'],
        executableSHA256=claw().sha256, assetSHA256=verify_assets(), physical_inputs=actual['physicalInputs'])
