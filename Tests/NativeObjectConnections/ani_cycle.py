"""Original-only AniCycle join from a native loadGridObject heap snapshot.

The callback, animation selector/update, and their game dependencies execute
original instructions. Only the native resource registry transport is replaced:
its original stack output pointer is normalized to the native token return ABI.
All original-derived input/output belongs in ignored work/.
"""
import json
import struct
import sys
from pathlib import Path

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP

from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import materialize, verify_assets

CALLBACK = 0x4918B0
RESOURCE = 0x4F6286
ENTRIES = {CALLBACK: (False, 1), 0x4C79E0: (True, 2),
           0x4C82A0: (True, 1), RESOURCE: (True, 2)}
DEPENDENCIES = {0x4C8220, 0x4C87F0, 0x40F680, 0x4C8810, 0x47E1D0, 0x4A30E0}


def _integer(value):
    return int(value, 0) if isinstance(value, str) else int(value)


def _string(machine, token):
    value = bytearray()
    for offset in range(1024):
        byte = machine.read(token + offset, 1)
        if byte == b'\0':
            return value.decode('ascii')
        value.extend(byte)
    raise ValueError('Unterminated resource name')


def reference(profile):
    """Replay profile segments; return per-step complete segment bytes/trace.

    Input: actor, segments [{address,hex}], resourceBindings
    [{receiver,name,token}], steps [{delta}]. Optional globals use the same
    segment format. actorSize/privateSize default to the source allocation
    extents 0x1b4/0x174. Segments must include prewarmed resource graphs.
    """
    program = claw()
    segments = profile['segments']
    if not segments:
        raise ValueError('A scene-produced actor graph is required')
    ranges = sorted((_integer(s['address']), bytes.fromhex(s['hex'])) for s in segments)
    pages = sorted({page for address, data in ranges
                    for page in range(address & ~4095, (address + len(data) + 4095) & ~4095, 4096)})
    if not pages:
        raise ValueError('Empty actor graph')
    machine = Machine(program, pages[0], 4096)
    for page in pages[1:]:
        machine.uc.mem_map(page, 4096)
    for address, data in ranges:
        machine.write(address, data)
    def graph_access(uc, kind, address, size, value, user):
        if not any(start <= address and address + size <= start + len(data)
                   for start, data in ranges):
            raise RuntimeError(f'Original access outside exported scene graph {address:#x}+{size}')

    for page in pages:
        machine.uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, graph_access,
                            begin=page, end=page + 4095)
    global_segments = profile.get('globals', [])
    for segment in global_segments:
        machine.write(_integer(segment['address']), bytes.fromhex(segment['hex']))
    actor = _integer(profile['actor'])
    private = machine.words(actor + 0x6C, 1)[0]
    actor_size = _integer(profile.get('actorSize', 0x1B4))
    private_size = _integer(profile.get('privateSize', 0x174))
    bindings = {(_integer(r['receiver']), r['name']): _integer(r['token'])
                for r in profile['resourceBindings']}
    if len(bindings) != len(profile['resourceBindings']):
        raise ValueError('Ambiguous resource binding')
    services, executed = [], set()

    def entry(uc, address, size, user):
        executed.add(address)
        if address not in ENTRIES or address == CALLBACK:
            return
        receiver_abi, count = ENTRIES[address]
        receiver = machine.register(UC_X86_REG_ECX) if receiver_abi else 0
        args = list(machine.words(machine.register(UC_X86_REG_ESP) + 4, count))
        if address == RESOURCE:
            args = args[:1]  # Native resource transport returns the output token.
        services.append(dict(function=address, receiver=receiver, arguments=args))

    # Observe these real entrypoints, never replace animation bodies.
    for address in set(ENTRIES) | DEPENDENCIES:
        machine.uc.hook_add(UC_HOOK_CODE, entry, begin=address, end=address)
    machine.intercept(RESOURCE)

    def physical(m, address):
        if address != RESOURCE:
            raise RuntimeError(f'Unresolved original physical dependency {address:#x}')
        receiver = m.register(UC_X86_REG_ECX)
        name_pointer, output = m.words(m.register(UC_X86_REG_ESP) + 4, 2)
        name = _string(m, name_pointer)
        key = (receiver, name)
        if key not in bindings:
            raise RuntimeError(f'Unbound resource lookup {receiver:#x}/{name}')
        token = bindings[key]
        m.write(output, struct.pack('<I', token))
        m.return_from_external(int(token != 0), 8)

    machine.on_external = physical
    outputs = []
    for step in profile['steps']:
        services.clear()
        executed.clear()
        delta = _integer(step['delta'])
        machine.write(0x5430C4, struct.pack('<I', delta))
        result = machine.call(CALLBACK, arguments=[actor])
        if not result.completed:
            raise RuntimeError('Original AniCycle callback did not return')
        outputs.append(dict(
            delta=delta,
            actorHex=machine.read(actor, actor_size).hex(),
            privateHex=machine.read(private, private_size).hex(),
            segments=[dict(address=s['address'], hex=machine.read(_integer(s['address']),
                        len(bytes.fromhex(s['hex']))).hex()) for s in segments],
            globals=[dict(address=s['address'], hex=machine.read(_integer(s['address']),
                       len(bytes.fromhex(s['hex']))).hex()) for s in global_segments],
            services=list(services), executedEntries=sorted(executed)))
    return dict(name=profile.get('name', profile.get('className', 'AniCycle')),
                className=profile.get('className', 'AniCycle'), actor=actor,
                executableSHA256=program.sha256, steps=outputs)


def run(document):
    asset_hash = verify_assets()
    return dict(family='ani_cycle', callback=CALLBACK, assetSHA256=asset_hash,
                profiles=[reference(profile) for profile in document['profiles']])


def prepare(directory):
    """Write the original Level 2 WWD; check the Level 1 physical inputs."""
    materialize({'LEVEL2/WORLDS/WORLD.WWD': (directory / 'WORLD2.WWD', True),
                 'GAME/ANIS/CYCLE100.ANI': (ROOT / 'App/GameData/GAME/ANIS/CYCLE100.ANI', False),
                 'LEVEL1/IMAGES/ARROWSIGN_RIGHT/001.PID': (ROOT / 'App/GameData/LEVEL1/IMAGES/ARROWSIGN_RIGHT/001.PID', False)})


def compare(directory):
    """Compare native output with the original; return the result fields."""
    source = json.loads((directory / 'native-input.json').read_text())
    actual = json.loads((directory / 'native-output.json').read_text())
    expected = run(source)
    (directory / 'original-output.json').write_text(json.dumps(expected, indent=2)+'\n')
    count = 0
    for native, original in zip(actual['profiles'], expected['profiles'], strict=True):
        assert native['className'] == original['className']
        for step, reference_step in zip(native['steps'], original['steps'], strict=True):
            for key in ('delta', 'actorHex', 'privateHex', 'segments', 'globals', 'services'):
                if step[key] != reference_step[key]:
                    raise AssertionError(f"{native['name']} delta {step['delta']}: mismatch in {key}")
            count += 1
    assert len(expected['profiles']) == 2 and count == 6
    return dict(original_callback='0x4918b0', native_owner='ClawNativeAniCycle', comparisons=count,
        exercised_service_edges=['0x4918b0 -> 0x4c79e0 canonical actor_animation -> 0x4f6286 / ClawActorResources', '0x4918b0 -> 0x4c82a0 canonical actor_animation'],
        controls=actual['controls'], faults=actual['faults'],
        unresolved_dependencies=actual['unresolvedDependencies'], physical_inputs=actual['physicalInputs'])


if __name__ == '__main__':
    source, destination = (Path(p).resolve() for p in sys.argv[1:])
    work = (ROOT / 'work').resolve()
    if work not in source.parents or work not in destination.parents:
        raise SystemExit('Original-derived input/output must stay under work/')
    output = run(json.loads(source.read_text()))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(dict(status='reference-generated', family='ani_cycle',
                         profiles=len(output['profiles']))))
