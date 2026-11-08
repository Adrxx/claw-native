#!/usr/bin/env python3
"""Complete raw actor/effect/flip join; baseline runs original actor, projection,
dispatcher, PID and lock wrapper. Only physical CopyRect/Lock/Unlock are replaced.
Controlled callback mutations are identical inputs, not game implementations.
"""
import base64
import json
from pathlib import Path
import struct
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'Tests')]
from Tests.clawparity.program import claw
from original_v10 import OriginalV10
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP

PROJECT, COPY, BLIT, LOCK, UNLOCK = 0x4c96d0, 0x546d58, 0x4bffa0, 0x6e120064, 0x6e120080
SELECTED = (0x4c0450,0x4c0920,0x4c0cc0,0x4c1190,0x4c25b0,0x4c3800,0x4c4c20)
COPY_STUB = 0x6e120100

def main(path):
    claw()
    witness = json.loads(path.read_text())
    assert len(witness['cases']) == 623 and witness['controls'] == 78, 'Incomplete native witness'
    assert len([c for c in witness['cases'][:83] if c['entry'] == 0x4d32e0]) == 83
    original = OriginalV10(ROOT/'Original/claw10/CLAW.EXE')
    u = original.u
    mapped = {p for start,end,_ in u.mem_regions() for p in range(start&~4095,end+1,4096)}
    def map_bytes(address,count):
        for p in range(address&~4095,(address+count+4095)&~4095,4096):
            if p not in mapped:
                u.mem_map(p,4096);mapped.add(p)
    map_bytes(LOCK,256)
    def put(address,values):
        u.mem_write(address,struct.pack('<'+'I'*len(values),*values))
    put(COPY,[COPY_STUB])
    events,objects,tokens,policy = [],[],{},''
    frame = dst = src = 0
    direct = False
    executed = {name:set() for name in ('actor','projection','dispatcher','pid')}
    ranges = {'actor':(0x4d32e0,0x4d3544),'projection':(PROJECT,0x4c977c),'dispatcher':(BLIT,0x4c00aa),'pid':(0x4c00b0,0x4c0446)}
    for start,end in zip(SELECTED,SELECTED[1:]+(0x4c5d50,)):
        name = f'transport-{start:x}';ranges[name] = (start,end);executed[name] = set()
    def snapshot():
        return [dict(name=o['name'],token=o['token'],bytes=base64.b64encode(bytes(u.mem_read(o['token'],len(base64.b64decode(o['bytes']))))).decode()) for o in objects]
    def spans(pairs):
        return [dict(token=t,bytes=base64.b64encode(bytes(u.mem_read(t,n))).decode()) for t,n in pairs]
    def project_mutation():
        if policy == 'project-dimensions': put(tokens['image']+16,[6,4])
        if policy == 'project-target':
            put(tokens['actor']+8,[0]);put(tokens['target']+16,[7])
        if policy == 'project-world': put(tokens['parent']+36,[tokens['world2']])
    def hook(_,address,size,user):
        nonlocal dst,src
        for name,(start,end) in ranges.items():
            if start<=address<end: executed[name].update(range(address,address+size))
        if address == 0x4d333d:
            project_mutation();return
        # The actor ignores the dispatcher's result even when a callback returns
        # a nonzero failure-like word. Override only after real dispatcher return.
        if address == 0x4d34f8 and policy == 'blit-result':
            u.reg_write(UC_X86_REG_EAX,0x88760001)
        if address not in (PROJECT,COPY_STUB,BLIT,0x4b9730,LOCK,UNLOCK)+SELECTED: return
        fn = COPY if address == COPY_STUB else address
        sp = u.reg_read(UC_X86_REG_ESP)
        count = {PROJECT:2,COPY:2,BLIT:5,0x4b9730:1,LOCK:5,UNLOCK:2,**{t:3 for t in SELECTED}}[fn]
        args = original.read_words(sp+4,count)
        if fn == BLIT: dst,src = args[0],args[2]
        event = dict(function=fn,receiver=u.reg_read(UC_X86_REG_ECX) if fn in (PROJECT,BLIT,0x4b9730)+SELECTED else 0,
                     arguments=args,memory=snapshot())
        if fn in (PROJECT,COPY,BLIT): event['stack'] = sp
        if fn == PROJECT: event['spans'] = spans([(args[0],4),(args[1],4)])
        elif fn == COPY: event['spans'] = spans([(args[1],16)])
        elif dst: event['spans'] = spans([(dst,16),(src,16)])
        events.append(event)
        if fn in (PROJECT,BLIT,0x4b9730)+SELECTED: return  # All three execute original game code.
        if fn == COPY:
            u.mem_write(args[0],bytes(u.mem_read(args[1],16)))
            if policy == 'copy-reload':
                put(frame-0x44,[tokens['image2']]);put(frame+8,[tokens['target2']])
                put(tokens['image']+48,[0]);put(tokens['target']+44,[0]);put(tokens['image']+16,[1,1]);put(tokens['actor']+76,[900,901])
                put(args[0],[5,2,9,5]);put(tokens['world']+16,[99,99,100,100])
            result = 1
        elif fn == LOCK:
            index = '2' if args[0] == tokens['dd2'] else ''
            assert args == [tokens['dd'+index],0,tokens['surface'+index]+12,1,0]
            desc = [0]*27;desc[:5] = [108,7,16,32,32];desc[9] = tokens['pixels'+index];desc[21] = 8
            put(args[2],desc)
            if policy == 'lock-reload':
                put(tokens['pid']+4,[8,5,tokens['replacement'],45]);put(src,[1,1,6,4]);put(dst,[3,2,99,6 if direct else 100])
                put(tokens['surface']+28,[39]);put(tokens['surface']+8,[tokens['dd2']])
            if policy == 'effect-reload':
                put(tokens['pid'],[1,8,5,tokens['replacement'],45,22,0x12ab,tokens['table2'],0,7])
                put(src,[1,1,6,4]);put(dst,[3,2,10,6]);put(tokens['surface']+28,[39]);put(tokens['surface']+8,[tokens['dd2']])
            if policy == 'mode-reload': put(tokens['pid']+20,[1])
            if policy == 'ordinary-reload': put(tokens['pid']+20,[22])
            result = 0
        else:
            assert args[0] in (tokens['dd'],tokens['dd2']) and args[1] == 0
            if policy == 'unlock-stores':
                put(tokens['actor']+24,[0xdeadbeef]*9);put(dst,[4,5,17,23]);put(src,[0,1,2,3])
            result = 0x88760001
        ret = original.read_words(sp,1)[0]
        u.reg_write(UC_X86_REG_EAX,result);u.reg_write(UC_X86_REG_ESP,sp+4*(count+1));u.reg_write(UC_X86_REG_EIP,ret)
    u.hook_add(UC_HOOK_CODE,hook)
    event_count = 0
    for case in witness['cases']:
        objects,events = case['before'],[]
        tokens = {o['name']:o['token'] for o in objects}
        policy,frame,dst,src = case['policy'],case['frame'],0,0
        direct = case['entry'] == BLIT
        for o in objects:
            data = base64.b64decode(o['bytes']);map_bytes(o['token'],len(data));u.mem_write(o['token'],data)
        original.stack = frame
        put(frame-56,[case.get('seed',0)])
        original.call(case['entry'],case['receiver'],struct.pack('<'+'I'*len(case['arguments']),*case['arguments']))
        assert len(events) == len(case['events']), (case['label'],'event count',len(events),len(case['events']))
        for i,(expected,actual) in enumerate(zip(events,case['events'])):
            assert expected == actual,(case['label'],'event',i,[k for k in expected if expected[k]!=actual.get(k)],
                {k:(expected[k],actual.get(k)) for k in expected if k!='memory' and expected[k]!=actual.get(k)},
                [a['name'] for a,b in zip(expected['memory'],actual['memory']) if a!=b])
        after = snapshot()
        assert after == case['after'],(case['label'],'final memory',[a['name'] for a,b in zip(after,case['after']) if a!=b])
        event_count += len(events)
    assert all(executed[f'transport-{t:x}'] for t in SELECTED), 'Missing selected transport'
    assert set(SELECTED) <= {e['function'] for c in witness['cases'] for e in c['events']}
    result = dict(status='pass',rawActorNativeComparisons=len(witness['cases']),orderedMemoryEvents=event_count,
                  nativeControls=witness['controls'],executedBytes={k:len(v) for k,v in executed.items()},
                  scope='raw actor and all eight compressed effect/flip selections -> native display',appAcceptance=False)
    path.with_name('raw-actor-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__ == '__main__': main(Path(sys.argv[1]))
