"""Fresh original lock calls, with physical import services only.

All image reads begin with the hash-checked claw() loader. Exported image data
and observed traces stay under ignored work/. No game entry is intercepted.
"""
import json
import struct
import sys
from pathlib import Path
from Tests.clawparity.kernel import Machine, STACK_TOP
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_ESP

BASE, COUNT, MASTER = 0x5408e0, 0x210, 0x540a90
SLOTS = {0x546abc:'GetVersion', 0x546aa4:'InitializeCriticalSection',
         0x546aac:'EnterCriticalSection', 0x546a9c:'LeaveCriticalSection'}
INIT, ACQUIRE, RELEASE = 0x502e47, 0x502e95, 0x502f05

class PhysicalHalt(Exception): pass

def reference(name, version=10, operations=None, fail_at=None, recheck=None, seed=None):
    program = claw()
    m = Machine(program, 0x3000000, 0x10000)
    for slot, name_ in SLOTS.items():
        assert program.imports[slot].split('!')[-1] == name_
    initial = m.read(BASE, COUNT).hex()
    mapping = {slot:m.import_stub[slot] for slot in SLOTS}
    reverse = {target:slot for slot,target in mapping.items()}
    events, steps, states = [], [], {}
    current = None
    def put(address, value): m.write(address,struct.pack('<I',value))
    def snapshot(): return [dict(states[key]) for key in sorted(states)]
    def adopt(section):
        assert section not in states
        states[section] = dict(section=section,owner=0,depth=0,initialized=1,entered=0,left=0)
    if seed:
        for address,value in seed.items(): put(address,value)
    def external(machine, target):
        slot = reverse[target]
        args = list(m.words(m.register(UC_X86_REG_ESP)+4,0 if slot == 0x546abc else 1))
        frame = current['frame']
        # Independent exact-frame assertions; direct and internally-owned init
        # differ, and release's physical frame must not inherit acquire's frame.
        if current['function'] == INIT: expected = frame-(8 if slot == 0x546abc else 12)
        elif current['function'] == RELEASE: expected = frame-8
        elif slot == 0x546abc: expected = frame-28
        elif slot == 0x546aa4 and args == [MASTER]: expected = frame-32
        else: expected = frame-24
        assert m.register(UC_X86_REG_ESP) == expected
        event = dict(function=slot,target=target if slot == 0x546aac else slot,
                     stackPointer=m.register(UC_X86_REG_ESP),arguments=args,
                     before=snapshot(),beforeBytes=m.read(BASE,COUNT).hex(),completed=False)
        events.append(event)
        if fail_at == len(events):
            event.update(after=snapshot(),afterBytes=m.read(BASE,COUNT).hex())
            raise PhysicalHalt
        if recheck is not None and slot == 0x546aac and args == [MASTER]:
            section = 0x5408f0+24*recheck
            if section not in states:
                adopt(section)
                put(0x540aa8+4*recheck,1)
        if slot != 0x546abc:
            section = args[0]
            if slot == 0x546aa4: adopt(section)
            else:
                state = states[section]
                if slot == 0x546aac:
                    assert state['owner'] in (0,1)
                    state['owner'] = 1; state['depth'] += 1; state['entered'] += 1
                else:
                    assert state['owner'] == 1 and state['depth'] > 0
                    state['depth'] -= 1; state['left'] += 1
                    if state['depth'] == 0: state['owner'] = 0
        event.update(after=snapshot(),afterBytes=m.read(BASE,COUNT).hex(),completed=True)
        m.return_from_external(version if slot == 0x546abc else 0xa1b2c3d4, 4*len(args))
    m.on_external = external
    for index,(function,args) in enumerate(operations or [(ACQUIRE,[16]),(RELEASE,[16])]):
        frame = STACK_TOP-0x100-index*0x40
        current = dict(function=function,arguments=args,frame=frame)
        try:
            result = m.call(function,arguments=args,stack_pointer=frame)
            assert result.completed
            assert result.stack_pointer == frame+4*(1+len(args))
            current.update(completed=True,eax=result.eax if function == INIT else None,
                           returnStackPointer=result.stack_pointer)
        except PhysicalHalt:
            current.update(completed=False,eax=None,returnStackPointer=None)
        current.update(states=snapshot(),imageBytes=m.read(BASE,COUNT).hex(),eventCount=len(events))
        steps.append(current)
        if not current['completed']: break
    assert fail_at is None or not steps[-1]['completed']
    if fail_at is None:
        assert all(state['depth'] == 0 and state['owner'] == 0 for state in states.values())
        assert all(state['entered'] == state['left'] for state in states.values())
    return dict(name=name,sha256=program.sha256,initialBytes=initial,
                imports={str(k):v for k,v in mapping.items()},version=version,
                failAt=fail_at,recheck=recheck,seed={str(k):v for k,v in (seed or {}).items()},
                steps=steps,events=events)

if __name__ == '__main__':
    output = Path(sys.argv[1]).resolve()
    assert Path('work').resolve() in output.parents
    profiles = [reference('cold-recursive',operations=[(ACQUIRE,[16]),(ACQUIRE,[16]),(RELEASE,[16]),(RELEASE,[16]),(INIT,[])]),
                reference('direct-init-warm',operations=[(INIT,[]),(INIT,[]),(ACQUIRE,[0]),(RELEASE,[0]),(ACQUIRE,[0]),(RELEASE,[0])]),
                reference('all-seventeen-slots',operations=[op for i in range(17) for op in [(ACQUIRE,[i]),(RELEASE,[i])]]),
                reference('recheck-publication',recheck=16),
                reference('warm-sentinel',operations=[(INIT,[])],seed={0x5408e8:0x753190ab,0x540a88:7})]
    for value in [3,4,0x80000003,0x80000004,0x80000000,0x7fffff00,0xffffffff]:
        profiles.append(reference('version-'+hex(value),version=value))
    # Seven physical boundaries in the cold acquire/release source graph.
    for index in range(1,8): profiles.append(reference('failure-'+str(index),fail_at=index))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(profiles,indent=2)+'\n')
    print(f'PASS {len(profiles)} fresh original lock profiles; exact callback frames, source data, physical ownership and failure prefixes')
