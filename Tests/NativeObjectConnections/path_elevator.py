"""Compare original/native PathElevator retirement through its logic owner."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Tests.NativeObjectConnections.path_elevator_transport import Reference, ACTOR, STATE
from Tests.clawparity.program import claw


def prepare_audit(output):
    profiles = []
    for owner in (False, True):
        ref = Reference('logic-owner' if owner else 'direct-helper-control')
        graph = bytes.fromhex(ref.initial[0]['data'])
        ref.initial = [dict(address=ACTOR+i*0x1000, data=graph[i*0x1000:(i+1)*0x1000].hex())
                       for i in range(8)] + ref.initial[1:]
        virtual = ref.m.read(0x50fee4, 4)
        assert int.from_bytes(virtual, 'little') == 0x49f020
        ref.initial.append(dict(address=0x50fee4, data=virtual.hex()))
        stages = []
        for name in ('initialized', 'tick'):
            ref.call(0x49ee30, args=(ACTOR,))
            spans = [(ACTOR, 0x1b4), (STATE, 0x174)] + ref.allocations
            stages.append(dict(name=name, bytes=[dict(address=a, data=ref.m.read(a,n).hex()) for a,n in spans]))
        before = list(ref.calls); helper = ref.get(STATE+0x18); lifecycle = []; owner_functions = []
        def observe(machine, address):
            lifecycle.append(dict(function=address, callback=ref.get(STATE+0x10)))
        ref.m.observe(0x49f020, observe)
        for address in (0x4c80c0, 0x4c80e0):
            ref.m.observe(address, lambda machine, address: owner_functions.append(address))
        ref.call(0x4c80c0 if owner else 0x49f020, STATE if owner else helper, (1,))
        profiles.append(dict(label=ref.label, initial=ref.initial, actor=ACTOR, state=STATE,
            stages=stages, calls_before=before, calls=ref.calls, allocations=ref.allocations,
            events=ref.events, lifecycle=lifecycle, owner_functions=owner_functions,
            actor_after=ref.m.read(ACTOR, 0x1b4).hex(), state_before_release=ref.m.read(STATE, 0x174).hex(),
            callback_after=ref.get(STATE+0x10), original_completed=True))
    (output/'scene-destruction-reference.json').write_text(json.dumps(dict(
        executable_sha256=claw().sha256, profiles=profiles), indent=2)+'\n')


def compare_audit(output):
    expected = json.loads((output/'scene-destruction-reference.json').read_text())
    actual = json.loads((output/'scene-destruction-native.json').read_text())
    failures = []
    for ref, native in zip(expected['profiles'], actual['profiles'], strict=True):
        for key in ('label', 'stages', 'calls_before', 'calls', 'events', 'lifecycle',
                    'actor_after', 'state_before_release', 'callback_after'):
            if ref[key] != native[key]: failures.append(dict(profile=ref['label'], field=key))
        if not native['initialized_and_ticked']: failures.append(dict(profile=ref['label'], field='initialize/tick'))
        if not native['destroyed'] or native['fault_code'] != 0 or native['owner_fault_code'] != 0:
            failures.append(dict(profile=ref['label'], field='source destruction'))
        if not native['retired'] or native['path_owned'] or native['helper_owned'] or native['path_live'] or native['helper_live']:
            failures.append(dict(profile=ref['label'], field='owned heap and ledger release'))
        expected_frees = [event[1] for event in ref['events'] if event[0] == 'free']
        if native['physical_frees'] != expected_frees:
            failures.append(dict(profile=ref['label'], field='physical free order'))
        if native['state_live'] != (ref['label'] == 'direct-helper-control'):
            failures.append(dict(profile=ref['label'], field='logic owner allocation release'))
    direct, owner = actual['profiles']; original = expected['profiles'][1]
    direct_pass = direct['destroyed'] and direct['retired'] and direct['fault_code'] == 0 and direct['calls'] == expected['profiles'][0]['calls']
    source_order = (original['owner_functions'] == [0x4c80c0, 0x4c80e0]
        and original['lifecycle'] == [dict(function=0x49f020, callback=0)]
        and owner['lifecycle'] == original['lifecycle'] and owner['owner_root'] == 0x4c80c0)
    if not direct_pass: failures.append('Direct-helper control failed')
    if not source_order: failures.append('Original source ordering differs')
    result = dict(command='path-elevator-scene-destruction-audit', family='path_elevator',
        status='pass' if not failures else 'fail', retirement_parity_passed=not failures,
        connection_comparison_passed=False, original_completed=original['original_completed'],
        original_logic_callback_at_helper_entry=original['lifecycle'][0]['callback'],
        direct_helper_control_passed=direct_pass, initialized_and_ticked=all(p['initialized_and_ticked'] for p in actual['profiles']),
        native_fault=owner['fault_address'], native_diagnostic=owner['diagnostic'], failures=failures,
        scene_attachment='Remains wire-object-path-elevator; this audit checks only the shared retirement prerequisite.')
    (output/'scene-destruction-audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result)); return int(bool(failures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-scene-destruction', action='store_true', required=True)
    parser.add_argument('output', type=Path)
    args = parser.parse_args(); output = args.output.resolve()
    assert output.is_relative_to(ROOT/'work')
    output.mkdir(parents=True, exist_ok=True); prepare_audit(output)
    python = str(ROOT/'work/test-env/bin/python')
    objects = subprocess.check_output([python, '-m', 'tools.claw.native_objects', '--dir', 'work/native-player-check', '--jobs', '1'], cwd=ROOT, text=True).splitlines()
    optimized = os.environ.get('CLAW_NATIVE_OPTIMIZE') == '1'
    binary = output/('scene-destruction-audit-release' if optimized else 'scene-destruction-audit')
    command = ['xcrun', 'swiftc', *(['-O'] if optimized else []), '-D', 'PATH_ELEVATOR_SCENE_DESTRUCTION_AUDIT',
        '-import-objc-header', 'Sources/Claw-Bridging-Header.h', 'Sources/ClawTokenHeap.swift',
        'Sources/ClawNativeCanonicalHost.swift', 'Sources/ClawNativeMfcLocks.swift', 'Sources/ClawNativeMfcMemory.swift',
        'Tests/NativeObjectConnections/path_elevator.swift', *objects, '-lc++', '-lz', '-o', str(binary)]
    log_path = output/'scene-destruction-build.log'
    with log_path.open('w') as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        print(log_path.read_text(), file=sys.stderr); return result.returncode
    result = subprocess.run([str(binary), str(output)], cwd=ROOT)
    return result.returncode or compare_audit(output)


# Scene connection comparison uses native-loaded actors as physical input.
from Tests.NativeObjectConnections.rez import entries, verify_assets
from Tests.clawparity.kernel import Machine
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
import struct

CALLBACK = 0x49ee30
OBSERVED = {0x4f63ec: 1, 0x4683a0: 1, 0x468540: 1, 0x468890: 4,
            0x4688f0: 1, 0x4f6286: 2, 0x4f6428: 1}

def prepare(directory):
    root = directory.resolve() / 'resources'
    root.mkdir(exist_ok=True)
    def link(target, source):
        assert target.parent.resolve().is_relative_to(root)
        if source.is_dir():
            if target.is_symlink(): target.unlink()
            target.mkdir(exist_ok=True)
            for child in source.iterdir(): link(target / child.name, child)
        elif not target.exists(): target.symlink_to(source.resolve())
    for child in (ROOT / 'App/GameData').iterdir(): link(root / child.name, child)
    found = []
    for name, payload in entries():
        if name == 'LEVEL9/WORLDS/WORLD.WWD':
            (directory / 'WORLD9.WWD').write_bytes(payload)
        if name.startswith(('LEVEL9/IMAGES/ELEVATOR/', 'LEVEL10/IMAGES/TRAPELEVATOR/')):
            relative = name.split('/', 1)[1]
            target = root / 'LEVEL1' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink(): target.unlink()
            target.write_bytes(payload); found.append(name)
    assert any(n.startswith('LEVEL9/') for n in found) and any(n.startswith('LEVEL10/') for n in found), found
    (directory / 'path-physical-assets.json').write_text(json.dumps(dict(
        asset_sha256=verify_assets(), files=found), indent=2)+'\n')

def _string(machine, token):
    data = bytearray()
    for offset in range(256):
        b = machine.read(token + offset, 1)
        if b == b'\0': return data.decode('ascii')
        data.extend(b)
    raise AssertionError('Unterminated resource name')

def reference_scene(profile):
    program = claw(); machine = Machine(program, 0x10000000, 4096)
    def map_span(address, count):
        for page in range(address & ~4095, (address+count+4095) & ~4095, 4096):
            if not any(start <= page <= end for start, end, _ in machine.uc.mem_regions()):
                machine.uc.mem_map(page, 4096)
    metadata = {a: machine.read(a, n) for a, n in [(0x50fee4, 4), (0x510020, 4), (0x528a4c, len(_string(machine, 0x528a4c))+1)]}
    for segment in profile['segments']:
        address, data = segment['address'], bytes.fromhex(segment['hex'])
        map_span(address, len(data)); machine.write(address, data)
    for address, data in metadata.items():
        assert machine.read(address, len(data)) == data, f'Original metadata mismatch {address:#x}'
    actor, state = profile['actor'], profile['state']
    assert [a['count'] for a in profile['allocations']] == [0x104, 0x18]
    assert len({a['token'] for a in profile['allocations']}) == 2
    allocations = iter(profile['allocations']); calls = []; events = []; lifecycle = []
    bindings = {(b['receiver'], b['name']): b['token'] for b in profile['resourceBindings']}
    def word(address): return machine.words(address, 1)[0]
    def observe(m, address):
        args = list(m.words(m.register(UC_X86_REG_ESP)+4, OBSERVED[address]))
        if address == 0x4f6286: args[1] = 0
        calls.append([address, 0 if address in (0x4f63ec, 0x4f6428) else m.register(UC_X86_REG_ECX), args])
    for address in OBSERVED: machine.observe(address, observe)
    machine.observe(0x49f020, lambda m, address: lifecycle.append(dict(function=address, callback=word(state+0x10))))
    for address in (0x4a48e0, 0x4f6428, 0x4f6286): machine.intercept(address)
    def external(m, address):
        stack = m.register(UC_X86_REG_ESP); args = lambda n: m.words(stack+4, n)
        if address == 0x4a48e0:
            count = args(1)[0]; allocation = next(allocations)
            assert allocation['count'] == count
            token = allocation['token']; map_span(token, count); m.write(token, b'\xcc'*count)
            events.append(['malloc', token, count]); m.return_from_external(token, 0)
        elif address == 0x4f6428:
            events.append(['free', args(1)[0]]); m.return_from_external(0, 0)
        elif address == 0x4f6286:
            name, output = args(2); receiver = m.register(UC_X86_REG_ECX); key = _string(m, name)
            token = bindings[(receiver, key)]
            m.write(output, struct.pack('<I', token)); events.append(['lookup', receiver, key, token])
            m.return_from_external(int(token != 0), 8)
        else: raise AssertionError(hex(address))
    machine.on_external = external; stages = []
    for step in profile['steps']:
        calls.clear(); events.clear()
        machine.write(0x537210, struct.pack('<I', step['clock']))
        before_position = machine.read(actor+0x4c, 8)
        result = machine.call(CALLBACK, arguments=[actor]); assert result.completed, result
        assert word(state+0x1c) == (5 if profile['name'] == 'missing-path' else 1)
        if step['name'] == 'tick' and profile['name'] != 'missing-path':
            assert machine.read(actor+0x4c, 8) != before_position, 'Movement tick must move'
        if step['name'] == 'initialized' and profile['name'].startswith('level-ten'):
            assert len(bindings) == 1 and all(bindings.values())
            lookup = next(iter(bindings.values()))
            assert (word(actor+0x170) == lookup) == (profile['name'] == 'level-ten-match')
            palette = word(0x537960) + (0x98 if profile['name'] == 'level-ten-match' else 0x68)
            colors = list(machine.words(palette, 4)); colors[3] = (colors[3]+0x20) & 0xffffffff
            assert list(machine.words(actor+0x128, 4)) == colors
        stages.append(dict(name=step['name'], calls=list(calls), events=list(events),
            spans=[dict(address=b['address'], hex=machine.read(b['address'], b['count']).hex()) for b in step['spans']]))
    helper = word(state+0x18); path = word(helper+8); calls.clear(); events.clear()
    result = machine.call(0x4c80c0, ecx=state, arguments=[1]); assert result.completed, result
    assert events == [['free', path], ['free', helper], ['free', state]], events
    return dict(name=profile['name'], stages=stages, lifecycle=lifecycle, helper_frees=events[:2],
                executable_sha256=program.sha256)

def compare(directory):
    source = json.loads((directory/'path-native-input.json').read_text())
    actual = json.loads((directory/'path-native-output.json').read_text())
    expected = [reference_scene(p) for p in source['profiles']]
    (directory/'path-original-output.json').write_text(json.dumps(dict(profiles=expected),indent=2)+'\n')
    assert len(expected) == 5 and len(actual['profiles']) == 5
    for native, original in zip(actual['profiles'], expected, strict=True):
        for key in ('name', 'stages', 'lifecycle', 'helper_frees'):
            assert native[key] == original[key], f"{native['name']}: {key} differs"
        assert native['retired'] and native['allocation_identities'], native['name']
    assert actual['controls'] and all(actual['controls'].values()), actual['controls']
    trace = actual['trace']
    order = ['loadGridObject', 'scene.gameplay', 'ClawNativePathElevator', '0x49ee30']
    positions = [trace.index(name) for name in order]
    assert positions == sorted(positions)
    assert 'ClawNativeMfcMemory.owned-path-and-helper' in trace
    assert 'ClawActorResources.0x4f6286' in trace
    assert 'scene.destruction->0x49f020->ClawNativeMfcMemory' in trace
    return dict(original_callback='0x49ee30', native_owner='ClawNativePathElevator',
        comparisons=len(expected)*2, exercised_service_edges=[
            'loadGridObject -> scene.gameplay -> ClawNativePathElevator -> 0x49ee30',
            '0x49ee30 -> 0x4f63ec -> ClawNativeMfcMemory (0x104, 0x18)',
            '0x49ee30 -> canonical 0x4683a0/0x468540/0x468890/0x4688f0',
            '0x49ee30 -> 0x4f6286 -> ClawActorResources -> synchronous stack output',
            'scene destruction -> 0x4c80c0/0x4c80e0 -> 0x49f020/0x49f040 -> 0x4f6428'],
        controls=actual['controls'], faults=actual['faults'],
        unresolved_dependencies=actual['unresolvedDependencies'], trace=trace,
        physical_inputs='Original Level 9 WWD id 9177 elevator and original PID resources; controlled preset, missing-path and level-10 branches; no playable-level claim')


if __name__ == '__main__':
    sys.exit(main())
