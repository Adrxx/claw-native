"""Original SpringBoard/impulse comparison over scene-owned memory exports."""
import json
import struct

from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets

CALLBACK = 0x49DB90
RESOURCE = 0x4F6286
ENTRIES = {0x4C79E0: (True, 2), 0x4C82A0: (True, 1), RESOURCE: (True, 2),
           0x41E810: (False, 2), 0x41C4E0: (False, 3), 0x4208B0: (True, 4),
           0x4170B0: (False, 2), 0x420DD0: (True, 6), 0x4208E0: (True, 4)}


def prepare(directory):
    """Mount original fern resources beside existing Level 1 physical inputs.

    This is a focused cross-level object join, not a whole Level 4 scene claim.
    Existing app assets are never changed.
    """
    target = directory / 'assets'
    target.mkdir(exist_ok=True)
    def link_tree(destination, source):
        # Foundation's directory enumeration needs actual directory nodes.
        # Only leaves point back to the unchanged app inputs.
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
    level = target / 'LEVEL1'
    found = []
    for name, payload in entries():
        if name == 'LEVEL4/WORLDS/WORLD.WWD':
            (directory / 'WORLD4.WWD').write_bytes(payload)
        if name.startswith(('LEVEL4/ANIS/SPRINGYFERN/', 'LEVEL4/IMAGES/SPRINGYFERN/', 'LEVEL4/SOUNDS/SPRINGYFERN/')):
            path = level / name.removeprefix('LEVEL4/')
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_symlink():
                assert path.read_bytes() == payload, name
            else:
                path.write_bytes(payload)
            found.append(name)
    assert len(found) == 15, found


def reference(profile):
    program = claw()
    machine = Machine(program, 0x10000000, 4096)
    mapped = {page for begin, end, _ in machine.uc.mem_regions() for page in range(begin, end + 1, 4096)}
    constants = {a: machine.read(a, 8) for a in (0x50BA88, 0x50BAA8, 0x50BAC0, 0x50BAC8, 0x50BAD0, 0x50BAD8, 0x513E20)}
    for segment in profile['segments'] + profile['globals']:
        address = segment['address']
        data = bytes.fromhex(segment['hex'])
        for page in range(address & ~4095, (address + len(data) + 4095) & ~4095, 4096):
            if page not in mapped:
                machine.uc.mem_map(page, 4096)
                mapped.add(page)
        machine.write(address, data)
    assert all(machine.read(address, 8) == data for address, data in constants.items()), 'Native constants differ from original'
    bindings = {(row['receiver'], row['name']): row['token'] for row in profile['resourceBindings']}
    services = []
    executed = set()

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
        if address not in ENTRIES:
            return
        thiscall, count = ENTRIES[address]
        args = list(machine.words(machine.register(UC_X86_REG_ESP) + 4, count))
        services.append(dict(function=address,
            receiver=machine.register(UC_X86_REG_ECX) if thiscall else 0,
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
    result = machine.call(CALLBACK, arguments=[profile['actor']])
    assert result.completed, profile['name']
    def capture(rows):
        return [dict(address=s['address'], hex=machine.read(s['address'], len(bytes.fromhex(s['hex']))).hex()) for s in rows]
    return dict(name=profile['name'], segments=capture(profile['segments']),
                globals=capture(profile['globals']), services=services, executed=sorted(executed))


def compare(directory):
    source = json.loads((directory / 'spring-input.json').read_text())
    actual = json.loads((directory / 'spring-output.json').read_text())
    expected = [reference(profile) for profile in source['profiles']]
    (directory / 'spring-original.json').write_text(json.dumps(expected, indent=2) + '\n')
    for native, original in zip(actual['profiles'], expected, strict=True):
        for key in ('name', 'segments', 'globals', 'services'):
            if native[key] != original[key]:
                raise AssertionError(f"{native['name']}: mismatch in {key}")
    names = {row['name'] for row in expected}
    assert {'initialize', 'absent-contact', 'landing', 'first-impulse', 'repeated-frame', 'animation-completion'} <= names
    impulse = [row for row in expected if row['name'] == 'first-impulse'][0]
    assert 0x41E810 in impulse['executed'] and 0x420DD0 in impulse['executed']
    sound = [row for row in expected if row['name'] == 'spring-sound-frame'][0]
    assert 0x4208E0 in sound['executed'], 'Original animation sound event must reach its real owner'
    assert sum(call['function'] == 0x41E810 for row in expected for call in row['services']) == 1
    assert all(actual['controls'].values())
    return dict(original_callback='0x49db90', native_owner='ClawNativeSpringBoard', comparisons=len(expected),
        exercised_service_edges=['loadGridObject -> scene.gameplay -> ClawNativeSpringBoard -> 0x49db90',
            '0x49db90 -> 0x4c79e0/0x4c82a0 -> 0x4f6286 / ClawActorResources',
            '0x4c82a0 -> 0x4208e0 canonical audio_events with physical manager unavailable',
            '0x49db90 -> 0x41e810 -> 0x41c4e0/0x4c79e0/0x4208b0/0x4170b0/0x420dd0'],
        controls=actual['controls'], faults=actual['faults'], unresolved_dependencies=actual['unresolvedDependencies'],
        executableSHA256=claw().sha256, assetSHA256=verify_assets(), physical_inputs=actual['physicalInputs'])
