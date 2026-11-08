"""Bounded original controller and relative-mouse input-source reference.

Only physical API outputs are scripted. InputSource and InputBindings execute
unaltered pinned v1.0 code. No admission or physical-device acceptance claim.
"""
import argparse
import json
from pathlib import Path
from Tests.clawparity.program import claw
from Tests.clawparity.env import Env


def profiles():
    for failure in ('no-device', 'position', 'caps'):
        for old in (0, 2, 4):
            yield dict(label=f'initialize-{failure}-old-{old}', function=0x4b3240,
                       arguments=[3, 0], oldMode=old, failure=failure)
    for count in (4, 8, 9):
        for mode in (1, 2, 4, 7):
            yield dict(label=f'initialize-{count}-buttons-mode-{mode}', function=0x4b3240,
                       arguments=[mode, 0], count=count)
    for available in (0, 1):
        for mode in (0, 1, 2, 4, 7):
            yield dict(label=f'mode-{mode}-available-{available}', function=0x4b3430,
                       arguments=[mode], available=available)
    yield dict(label='disabled-source-ignores-controller', mode=0, buttons=0x1ff, x=0, y=65535)
    yield dict(label='keyboard-source-without-controller', mode=1, keys={0x27:0x8000,0x20:1})
    for axis in ('x', 'y'):
        for value in (19999, 20000, 20001, 44999, 45000, 45001):
            yield dict(label=f'axis-{axis}-{value}', **{axis:value})
    for button in range(9):
        for edge in ('new', 'held', 'release'):
            mask = 1 << button
            yield dict(label=f'button-{button+1}-{edge}', buttons=0 if edge == 'release' else mask,
                       latch=mask if edge != 'new' else 0)
    for extended, count, inhibit in ((0, 9, 0), (1, 8, 0), (1, 9, 1)):
        yield dict(label=f'extended-{extended}-count-{count}-inhibit-{inhibit}',
                   buttons=0x1ff, extended=extended, count=count, inhibit=inhibit)
    yield dict(label='poll-failure-stale-buffer', failure='position', staleButtons=0x42,
               staleX=19999, staleY=45001)
    for axis in ('dx', 'dy'):
        for value in (-7, -6, 0, 6, 7):
            yield dict(label=f'mouse-{axis}-{value}', mode=4, **{axis:value})
    for key in (1, 2):
        for state in (1, 0x8000, 0x8001):
            yield dict(label=f'mouse-button-{key}-state-{state}', mode=4, keys={key:state})
    for held in (False, True):
        for mapping in ('defaults', 'remap', 'shared', 'none'):
            yield dict(label=f'binding-{mapping}-held-{held}', function=0x430ec0,
                       binding=mapping, buttons=0x80, bindingLatch=0xffffffff if held else 0,
                       keys={0x27:0x8000})


def probe(program, profile):
    env = Env(program)
    token = env.object(0x300, 'source-and-binding', fill=0xa5)
    binding = token + 0x250
    values = {0:0, 0x40:profile.get('count',9), 0x198:52,
              0x1cc:profile.get('mode',2), 0x1d0:profile.get('available',1),
              0x1d4:profile.get('extended',1), 0x1d8:profile.get('inhibit',0),
              0x1a0:profile.get('staleX',32767), 0x1a4:profile.get('staleY',32767),
              0x1b8:profile.get('staleButtons',0), 0x20c:profile.get('latch',0),
              0x220:20000, 0x224:45000, 0x228:20000, 0x22c:45000,
              0x230:profile.get('dx',0), 0x234:profile.get('dy',0),
              0x238:6, 0x23c:6, 0x240:320, 0x244:240}
    if 'oldMode' in profile: values[0x1cc] = profile['oldMode']
    for offset, value in values.items(): env.put(token+offset,value & 0xffffffff)
    keys = [0x25,0x27,0x26,0x28,0x20,0x11,0x12,0x10,0x5a,0x31,0x32,0x33]
    for i,key in enumerate(keys): env.put(token+0x1dc+4*i,key)
    masks = [1,2,4,8,0,0x10,0x20,0x40,0x80,0]
    if profile.get('binding') == 'remap': masks[1] = 0x80; masks[8] = 2
    if profile.get('binding') == 'shared': masks[0] = masks[1] = 0x80
    if profile.get('binding') == 'none': masks = [0]*10
    env.put(binding,token,0xdeadbeef,0xdeadbeef,profile.get('bindingLatch',0))
    for i,mask in enumerate(masks): env.put(binding+0x10+4*i,mask)
    for i,key in enumerate([0x25,0x27,0x26,0x28,0x20,0x11,0x12,0x10,0,0x5a,0x31,0x32,0x33,0x34]):
        env.put(binding+0x38+4*i,key)
    events=[]
    def service(owner, call):
        events.append(dict(function=call.function,arguments=list(call.arguments),stackPointer=call.stack_pointer))
        a=call.arguments
        if call.function == 0x546df8: return 0 if profile.get('failure') == 'no-device' else 1
        if call.function == 0x546de8:
            if profile.get('failure') == 'position': return 167
            owner.put(a[1]+8,profile.get('x',32767),profile.get('y',32767))
            owner.put(a[1]+32,profile.get('buttons',0))
            return 0
        if call.function == 0x546df4:
            if profile.get('failure') == 'caps': return 165
            owner.write(a[1],bytes(404))
            owner.put(a[1]+0x24,0,65535,0,65535)
            owner.put(a[1]+0x3c,profile.get('count',9))
            return 0
        if call.function == 0x546ce4: return profile.get('keys',{}).get(a[0],0)
        if call.function == 0x546cd0: owner.put(a[0],123,456); return 1
        if call.function == 0x546c44: return (640,480)[a[0]]
        if call.function == 0x546d9c: return 1
        raise AssertionError(hex(call.function))
    for address,argc,arguments in ((0x546df8,0,()),(0x546de8,2,('u32','ptr:52')),
        (0x546df4,3,('u32','out:404','u32')),(0x546ce4,1,()),(0x546cd0,1,('out:8',)),
        (0x546c44,1,()),(0x546d9c,2,())):
        env.fixture(address,'stdcall',argc,service,arguments=arguments)
    function=profile.get('function',0x4b3490)
    before=env.read(token,0x300).hex()
    env._freeze()
    result=env.run_original(function,binding if function==0x430ec0 else token,
                            tuple(profile.get('arguments',())),check_objects=True)
    assert result.completed and not result.errors, (profile,result.errors)
    return dict(profile=profile,token=token,function=function,
                receiver=binding if function==0x430ec0 else token,
                before=before,after=env.machine.read(token,0x300).hex(),events=events,eax=result.eax)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    program=claw()
    rows=[probe(program,p) for p in profiles()]
    assert len(rows) <= 100
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(dict(status='pass',cases=len(rows),binary_sha256=program.sha256)))

if __name__=='__main__': main()
