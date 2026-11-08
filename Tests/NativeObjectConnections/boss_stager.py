"""Original-backed prerequisite audit for the BossStager scene join.

These are boundary diagnostics, not the joined connection comparison. They
never report host-wired or substitute for prepare()/compare(). The mode audit
checks the scene virtual receiver; the audio audit checks the first-voice
allocation reached by the real callback with a genuinely loaded sound pool.
Original-derived evidence is written only under ignored work/.
"""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from Tests.NativeObjectConnections.rez import materialize
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP


def audit_audio_allocation(directory):
    """Trace the real callback into a fresh, genuinely loaded sound pool.

    The Swift diagnostic supplies a ClawNativeAudio-created pool, not a scripted
    constructor or an idle voice. Original execution stops at the unsupported
    allocator boundary. This cannot count as a completed connection comparison.
    """
    materialize({'GAME/SOUNDS/SDPT2.WAV': (ROOT / 'App/GameData/GAME/SOUNDS/SDPT2.WAV', False)})
    native = json.loads((directory / 'audio-allocation-native.json').read_text())
    program = claw()
    profiles = []
    for profile in native['profiles']:
        for callback in (False, True):
            base = 0x10000000
            machine = Machine(program, base, 0x10000)
            pages = set()
            for segment in profile['segments']:
                address, data = segment['address'], bytes.fromhex(segment['hex'])
                for page in range(address & ~4095, (address + len(data) + 4095) & ~4095, 4096):
                    if page not in pages:
                        machine.uc.mem_map(page, 4096)
                        pages.add(page)
                machine.write(address, data)
            def put(address, *values):
                machine.write(address, struct.pack('<' + 'I' * len(values), *values))
            actor, state, context, display, dimensions, sounds, manager = [base + i * 0x200 for i in range(1, 8)]
            put(actor + 0xc, context)
            put(actor + 0x6c, state)
            put(actor + 0x50, 161)
            put(state + 0x1c, 8001, 37)
            put(context + 4, display)
            put(display + 0x10, dimensions)
            put(dimensions + 0x10, 643, 483)
            put(context + 0x28, sounds)
            put(0x5371fc, manager)
            put(0x5430c4, 0)
            put(0x532c0c, 1)
            put(0x532c10, 100)
            put(0x541328, 1234)
            put(0x53c260, 0)
            # Preserve the native sound resource -> genuine source voice pool.
            sound = next(s['address'] for s in profile['segments']
                         if len(bytes.fromhex(s['hex'])) == 64)
            entries, frontier = [], []
            arities = {0x48ded0: (False, 1), 0x42a450: (True, 1),
                       0x486e70: (False, 1), 0x4b45f0: (True, 4),
                       0x4b4430: (True, 0), 0x4b42e0: (True, 1)}
            def observe(m, address):
                thiscall, count = arities[address]
                entries.append(dict(function=address,
                    receiver=m.register(UC_X86_REG_ECX) if thiscall else 0,
                    arguments=list(m.words(m.register(UC_X86_REG_ESP) + 4, count)),
                    returnPC=m.words(m.register(UC_X86_REG_ESP), 1)[0]))
            for address in arities:
                machine.observe(address, observe)
            setrect = machine.words(0x546d5c, 1)[0]
            # Import stubs already enter Machine.on_external; adding a second
            # hook at that token would execute the physical return twice.
            for address in (0x4f63ec, 0x4f6286):
                machine.intercept(address)
            def external(m, address):
                sp = m.register(UC_X86_REG_ESP)
                if address == 0x4f63ec:
                    frontier.append(dict(function=address, count=m.words(sp + 4, 1)[0],
                                         returnPC=m.words(sp, 1)[0]))
                    m.uc.emu_stop()
                elif address == 0x4f6286:
                    key, output = m.words(sp + 4, 2)
                    name = m.read(key, 64).split(b'\0')[0].decode('ascii')
                    value = sound if name == 'GAME_SDPT2' else 0
                    entries.append(dict(function=address, receiver=m.register(UC_X86_REG_ECX),
                                        name=name, result=value))
                    put(output, value)
                    m.return_from_external(int(value != 0), 8)
                elif address == setrect:
                    output, *values = m.words(sp + 4, 5)
                    put(output, *values)
                    m.return_from_external(1, 20)
                else:
                    raise RuntimeError(f'Unexpected physical dependency {address:#x}')
            machine.on_external = external
            result = machine.call(0x48ded0 if callback else profile['root'],
                ecx=0 if callback else profile['receiver'],
                arguments=[actor] if callback else profile['arguments'])
            enabled = profile['enabled']
            if enabled:
                assert not result.completed and frontier == [dict(function=0x4f63ec, count=56, returnPC=0x4b4320)]
            else:
                assert result.completed and not frontier
                if callback:
                    assert machine.words(state + 0x1c, 2) == (8002, 1500)
                else:
                    assert machine.register(UC_X86_REG_EAX) == profile['native']['eax']
            profiles.append(dict(name=profile['name'], originalCallbackExecuted=callback,
                completed=result.completed, entries=entries, frontier=frontier))
    enabled = next(p['native'] for p in native['profiles'] if p['enabled'])
    disabled = next(p['native'] for p in native['profiles'] if not p['enabled'])
    assert not enabled['completed'] and enabled['faultAddress'] == 0x4f63ec
    assert enabled['diagnostic'] == 'unsupportedABI' and not enabled['allocations']
    assert disabled['completed'] and disabled['scopeAccepted'] and not disabled['allocations']
    output = dict(command='boss-stager-audio-allocation-audit', status='blocked',
        executable_sha256=program.sha256, native_join_executed=False,
        original_profiles=profiles, native_profiles=native['profiles'],
        required_boundary='Real 0x4b4430/0x4b42e0 first-voice allocation through 0x4f63ec(0x38) at return PC 0x4b4320')
    (directory / 'audio-allocation-audit.json').write_text(json.dumps(output, indent=2) + '\n')
    return output


def audit_prerequisites():
    """Execute the unchanged original readiness helper and actual mode target."""
    program = claw()
    machine = Machine(program, 0x10000000, 0x1000)
    manager, interface = 0x10000100, 0x10000200
    scene_vtable = 0x50C264
    mode_target = machine.words(scene_vtable + 0x10, 1)[0]
    music_target = machine.words(scene_vtable + 0x60, 1)[0]
    assert mode_target == 0x40AF90 and music_target == 0x46CAB0
    machine.write(manager + 0x2C, struct.pack('<I', interface))
    machine.write(interface, struct.pack('<I', scene_vtable))
    observations = []

    def mode_entry(m, address):
        observations.append(dict(function=hex(address), receiver=m.register(UC_X86_REG_ECX),
                                 return_pc=hex(m.words(m.register(UC_X86_REG_ESP), 1)[0])))

    # Observe the real target without replacing its body or vtable entry.
    machine.observe(mode_target, mode_entry)
    completed = machine.call(0x42A630, ecx=manager)
    readiness = machine.register(UC_X86_REG_EAX)
    assert completed.completed and readiness == 1
    assert len(observations) == 1 and observations[0]['receiver'] == interface
    direct = machine.call(mode_target, ecx=interface)
    mode = machine.register(UC_X86_REG_EAX)
    assert direct.completed and mode == 3
    machine.write(manager + 0x2C, struct.pack('<I', 0))
    missing = machine.call(0x42A630, ecx=manager)
    no_interface = machine.register(UC_X86_REG_EAX)
    assert missing.completed and no_interface == 0

    specification = json.loads((ROOT / 'Tests/families/checkpoint_logic.json').read_text())
    declaration = next(item for item in specification['owned']
                       if int(item['address'], 0) == mode_target)
    header = (ROOT / 'Sources/ClawCanonicalDispatch.h').read_text()
    row = re.search(r'\{0x0040af90u,\s*(CLAW_CANONICAL_\w+),\s*(\d+)u,', header)
    assert row is not None
    source = (ROOT / 'Sources/ClawNativeCanonicalHost.swift').read_text()
    strict_receiver_guard = ('entry.convention == UInt32(CLAW_CANONICAL_THISCALL) || '
                             'value.receiver == 0') in source
    contradiction = (row[1] == 'CLAW_CANONICAL_CDECL' and strict_receiver_guard
                     and observations[0]['receiver'] != 0)
    return dict(
        command='boss-stager-prerequisite-audit',
        status='blocked' if contradiction else 'requires-native-recheck',
        executable_sha256=program.sha256,
        original_scene_vtable=hex(scene_vtable),
        original_mode_slot=dict(offset='0x10', target=hex(mode_target), result=mode),
        original_music_slot=dict(offset='0x60', target=hex(music_target)),
        original_readiness=dict(function='0x42a630', receiver=manager,
                                result=readiness, mode_calls=observations[:1],
                                absent_interface_result=no_interface),
        specification_declaration=declaration,
        generated_registry=dict(convention=row[1], argument_count=int(row[2])),
        host_rejects_nonzero_receiver_for_cdecl=strict_receiver_guard,
        receiver_abi_conflict=contradiction,
        native_join_executed=False,
        required_boundary='Preserve the actual scene virtual receiver at 0x42a630 -> '
                          '0x40af90 while retaining reviewed canonical ownership and '
                          'existing direct callers; verify with the native host.',
    )


def prepare(directory):
    materialize({'LEVEL2/WORLDS/WORLD.WWD': (directory / 'WORLD2.WWD', True)})


# Calls to owned bodies may be inlined in the admitted translation. These are
# the stable ordered boundary calls shared by the real original and native join.
OBSERVED = {0x42b000:(True,0),0x42a630:(True,0),0x40af90:(True,0),0x4b54a0:(True,1),
    0x4c8060:(True,1),0x4c7900:(True,2),0x42a450:(True,1),0x4208e0:(True,4),
    0x486e70:(False,1),0x420170:(False,0),0x4c8da0:(True,6),0x48c820:(False,2),
    0x48ce40:(False,3),0x4f6286:(True,2),0x491fa0:(False,1)}


def connection_reference(profile, directory):
    program = claw()
    m = Machine(program,0x10000000,4096)
    pages = {page for start,end,_ in m.uc.mem_regions() for page in range(start,end+1,4096)}
    def mapped(address,count):
        for page in range(address & ~4095,(address+count+4095)&~4095,4096):
            if page not in pages: m.uc.mem_map(page,4096);pages.add(page)
    def put(address,*words): m.write(address,struct.pack('<'+'I'*len(words),*words))
    for segment in profile['initial']:
        data=bytes.fromhex(segment['hex']);mapped(segment['address'],len(data));m.write(segment['address'],data)
    bindings={(b['receiver'],b['name']):b['token'] for b in profile['bindings']}
    allocations=list(profile['allocations']);audio=list(profile['audio']);calls=[];executed=set()
    def observe(machine,address):
        executed.add(address)
        thiscall,count=OBSERVED[address]
        args=list(machine.words(machine.register(UC_X86_REG_ESP)+4,count))
        if address == 0x4f6286: args=args[:1]
        if address == 0x42a450: args=[] # borrowed rectangle output pointer
        calls.append(dict(function=address,receiver=machine.register(UC_X86_REG_ECX) if thiscall else 0,arguments=args))
    for address in OBSERVED:m.observe(address,observe)
    m.observe(0x46cab0,lambda machine,address:executed.add(address))
    for address in [0x4a48e0,0x4f6286,0x4f51c5,0x4f572a,0x711100,0x71020014,
        0x71010018,0x7101001c,0x71010020,0x71010024,0x71010030,0x7101003c,0x71010040,0x71010044]:
        if address>=0x70000000 or address==0x711100:mapped(address,4);m.write(address,b'\xc3')
        m.intercept(address)
    def external(machine,address):
        sp=machine.register(UC_X86_REG_ESP)
        arg=lambda i:machine.words(sp+4+4*i,1)[0]
        receiver=machine.register(UC_X86_REG_ECX)
        if address==0x4a48e0:
            allocation=allocations.pop(0);assert allocation['count']==arg(0)
            token=allocation['token'];mapped(token,arg(0));m.write(token,bytes([0xcc])*arg(0))
            machine.return_from_external(token,0);return
        if address==0x4f6286:
            key=(receiver,arg(0));assert key in bindings,('lookup',hex(receiver),hex(arg(0)))
            value=bindings[key];put(arg(1),value);machine.return_from_external(bool(value),8);return
        if address==0x711100:
            put(arg(0),*[arg(i) for i in range(1,5)]);machine.return_from_external(1,20);return
        if address in (0x4f51c5,0x4f572a):
            # Native CPtrList storage transport, using the original list layout.
            before=address==0x4f572a
            at=arg(0) if before else 0;actor=arg(1) if before else arg(0)
            node=machine.words(receiver+16,1)[0]
            assert node,'This bounded scene must have a preallocated list node'
            put(receiver+16,machine.words(node,1)[0])
            tail=machine.words(receiver+8,1)[0]
            previous=machine.words(at+4,1)[0] if before else tail
            put(node,at,previous,actor)
            if previous:put(previous,node)
            else:put(receiver+4,node)
            if before:put(at+4,node)
            else:put(receiver+8,node)
            put(receiver+12,machine.words(receiver+12,1)[0]+1)
            machine.return_from_external(node,8 if before else 4);return
        assert audio,('unexpected physical audio',hex(address))
        event=audio.pop(0);assert address==event['function'],(hex(address),event)
        args=[arg(i) for i in range(len(event['arguments']))]
        getter='output' in event
        if getter:
            assert args[:-1]==event['arguments'][:-1]
            output=event['output']
            if address==0x71020014:mapped(output,16);put(output,machine.words(args[1],1)[0])
            put(args[-1],output)
        else:assert args==event['arguments'],(args,event)
        machine.return_from_external(event['result'],len(args)*4)
    m.on_external=external
    done=m.call(profile['function'],arguments=[profile['actor']])
    if profile['function']==0x48e430: assert m.register(UC_X86_REG_EAX)==profile['eax']
    assert done.completed,('original callback failed',profile['mode'],done)
    assert not allocations and not audio,('unconsumed physical inputs',profile['mode'])
    final=[dict(address=s['address'],hex=m.read(s['address'],len(bytes.fromhex(s['hex']))).hex()) for s in profile['final']]
    return dict(mode=profile['mode'],calls=calls,final=final,executed=sorted(executed),sha256=program.sha256)


def compare(directory):
    native=json.loads((directory/'native-connection.json').read_text())
    expected=[]
    for profile in native['profiles']:
        assert profile['completed'] and profile['fault']==0
        reference=connection_reference(profile,directory);expected.append(reference)
        for actual,wanted in zip(profile['final'],reference['final'],strict=True):
            if actual!=wanted:
                (directory/'connection-mismatch.json').write_text(json.dumps(dict(mode=profile['mode'],native=actual,original=wanted),indent=2)+'\n')
                raise AssertionError(('source memory mismatch',profile['mode'],hex(actual['address'])))
        actual=[]
        for call in profile['calls']:
            if call['function'] not in OBSERVED:continue
            call=dict(call)
            if call['function']==0x42a450:call['arguments']=[]
            actual.append(call)
        if actual!=reference['calls']:
            (directory/'connection-call-mismatch.json').write_text(json.dumps(dict(mode=profile['mode'],native=actual,original=reference['calls']),indent=2)+'\n')
            raise AssertionError(('ordered call mismatch',profile['mode']))
    (directory/'original-connection.json').write_text(json.dumps(expected,indent=2)+'\n')
    assert [p['mode'] for p in expected]==[0,8000,8001,8001,8002,8002,8003,8003,8004,8005,8006,8007,8007,8008,8008,1,2,3]
    required={'contact_timer_wraps','meter_teardown_releases_scene_ledger','missing_service_fault',
        'out_of_callback_service_rejected','parent_retirement_preserves_children','real_boss_published',
        'real_contact_binding','real_meter_children','recreation_has_fresh_owner','shared_scene_heap',
        'replacement_private_identity_rejected','shared_hud_timer'}
    assert set(native['controls'])==required and all(native['controls'].values()),native['controls']
    assert native['faults']==0 and not native['unresolvedDependencies']
    assert {0x46cab0,0x40af90,0x42a630,0x4b54a0} <= set(expected[0]['executed'])
    trace=native['trace'];order=['loadGridObject','scene.gameplay','ClawNativeBossStager','0x48ded0','ClawNativeScene.resource.0x4f6286']
    cursor=0
    for event in trace:
        if cursor<len(order) and event==order[cursor]:cursor+=1
    assert cursor==len(order)
    return dict(original_callback='0x48ded0',native_owner='ClawNativeBossStager',comparisons=len(expected),
        exercised_service_edges=['loadGridObject -> scene.gameplay -> ClawNativeBossStager -> 0x48ded0',
            '0x42b000 -> 0x42a630 -> actual 0x40af90 and 0x46cab0 -> MusicRuntime 0x4b54a0',
            '0x4c8060 -> BossStagerAttack binding','0x4c7900 -> physical image dictionary',
            '0x42a450 -> native SetRect','0x4a30e0 -> shared audio x87 primitive',
            '0x4b45f0 -> real PCM voice owner and shared allocator','0x420170 -> player reset',
            '0x4c8da0 -> scene list -> actual BossHealthMeter 0x491fa0',
            '0x48c820 / 0x48ce40 -> shared speech owners'],
        controls=native['controls'],faults=native['faults'],unresolved_dependencies=native['unresolvedDependencies'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument('--audit-prerequisites', action='store_true')
    operation.add_argument('--audit-audio-allocation', type=Path, metavar='DIRECTORY')
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'work/native-object-connections/boss_stager/mode-abi-audit.json')
    args = parser.parse_args()
    if args.audit_audio_allocation:
        directory = args.audit_audio_allocation.resolve()
        if (ROOT / 'work').resolve() not in directory.parents:
            parser.error('Original-derived evidence must stay under work/')
        result = audit_audio_allocation(directory)
        print(json.dumps(dict(command=result['command'], status=result['status'],
            profiles=len(result['original_profiles']), evidence=str(directory / 'audio-allocation-audit.json'))))
        return 2
    destination = args.output.resolve()
    if (ROOT / 'work').resolve() not in destination.parents:
        parser.error('Original-derived evidence must stay under work/')
    result = audit_prerequisites()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 2 if result['receiver_abi_conflict'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
