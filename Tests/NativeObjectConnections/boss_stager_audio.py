"""Finite shared-owner audio join; original-derived witnesses stay under work/."""
import json
import struct
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from Tests.NativeObjectConnections.rez import materialize
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX


def prepare():
    materialize({'GAME/SOUNDS/SDPT2.WAV':(ROOT/'App/GameData/GAME/SOUNDS/SDPT2.WAV',False)})


def compare(directory):
    native=json.loads((directory/'audio-transport-native.json').read_text())
    assert native['outputEnabled'] is False
    program=claw()
    comparisons=[]
    for profile in native['profiles']:
        if profile['name'] not in ('playback-lifecycle','direct-allocation','disabled'):
            continue
        machine=Machine(program,0x10000000,0x10000)
        assert machine.words(0x510020,1)==(0xffffffff,)
        pages={page for start,end,_ in machine.uc.mem_regions() for page in range(start,end+1,4096)}
        def mapped(address,count):
            for page in range(address & ~4095,(address+count+4095)&~4095,4096):
                if page not in pages:
                    machine.uc.mem_map(page,4096);pages.add(page)
        def put(address,*words):
            machine.write(address,struct.pack('<'+'I'*len(words),*words))
        for segment in profile['segments']:
            data=bytes.fromhex(segment['hex']);mapped(segment['address'],len(data));machine.write(segment['address'],data)
        events=[]; allocations=[]; allocation_calls=[]; source_calls=[]; released=[]; retired={}
        for address in (0x4a48e0,0x4f6428,0x71010008,0x71020014,0x71010018,0x7101001c,0x71010020,0x71010024,0x71010030,0x7101003c,0x71010040,0x71010044,0x71010048):
            if address>=0x70000000:
                mapped(address,4);machine.write(address,b"\xc3")
            machine.intercept(address)
        def observe(m,address):
            sp=m.register(UC_X86_REG_ESP)
            if address==0x4f63ec:
                allocation_calls.append(dict(count=m.words(sp+4,1)[0],returnPC=m.words(sp,1)[0]))
            source_calls.append(address)
        for address in (0x4b4430,0x4b42e0,0x4f63ec,0x4b5210,0x4b5270,0x4b5240):machine.observe(address,observe)
        def external(m,address):
            sp=m.register(UC_X86_REG_ESP)
            if address==0x4f6428:
                token=m.words(sp+4,1)[0]
                retired[str(token)]=list(m.read(token,56))
                m.return_from_external(0,0);return
            if address==0x71010008:
                released.append(m.words(sp+4,1)[0]);m.return_from_external(0,4);return
            if address==0x4a48e0:
                assert m.words(sp+4,1)==(56,)
                token=allocations.pop(0);mapped(token,56);m.write(token,bytes([0xcc])*56)
                m.return_from_external(token,0);return
            assert events,f'unexpected physical {address:#x}'
            expected=events.pop(0);assert address==expected['function'],(hex(address),expected)
            a=list(m.words(sp+4,len(expected['arguments'])))
            original_a=expected['arguments']
            getter=address in (0x71010018,0x7101001c,0x71010020,0x71010024)
            if getter or address==0x71020014:
                assert a[:-1]==original_a[:-1]
                value=expected['output']
                if address==0x71020014:
                    mapped(value,16);put(value,m.words(a[1],1)[0])
                put(a[-1],value)
            else:assert a==original_a,(a,original_a)
            m.return_from_external(expected['result'],len(a)*4)
        machine.on_external=external
        previous=[]
        for index,step in enumerate(profile['steps']):
            if step.get('teardown'):
                events=[]
                result=machine.call(0x4c88b0,ecx=profile['sound'])
                assert result.completed and released==step['releases']
                assert all(retired[token]==data for token,data in step['retired'].items())
                for key in ('sound','manager'):
                    segment=step[key];expected=bytes.fromhex(segment['hex'])
                    assert machine.read(segment['address'],len(expected))==expected,key
                comparisons.append(dict(profile=profile['name'],step='source-teardown'));continue
            if index==2:
                # The same controlled stop through the physical owner precedes
                # idle reuse. Stop has no source metadata writes.
                events=[dict(function=0x71010048,arguments=[machine.words(previous[0]+12,1)[0]],result=0)]
                result=machine.call(0x4b3e30,ecx=previous[0]);assert result.completed and not events
            events=list(step['events'])
            allocations=[token for token in step['allocations'] if token not in previous]
            result=machine.call(step['function'],ecx=step['receiver'],arguments=step['arguments'])
            assert result.completed and step['completed'] and not events and not allocations
            assert machine.register(UC_X86_REG_EAX)==step['eax']
            for segment in step['final']:
                expected=bytes.fromhex(segment['hex'])
                actual=machine.read(segment['address'],len(expected))
                if actual!=expected:
                    (directory/'audio-transport-mismatch.json').write_text(json.dumps(dict(profile=profile['name'],step=index,address=segment['address'],original=actual.hex(),native=expected.hex()),indent=2))
                assert actual==expected,(profile['name'],index,hex(segment['address']))
            previous=step['allocations']
            comparisons.append(dict(profile=profile['name'],step=index))
        if profile['name']=='playback-lifecycle':
            assert allocation_calls==[dict(count=56,returnPC=0x4b4320)]*2
            assert all(a in source_calls for a in (0x4b4430,0x4b42e0,0x4b5210,0x4b5270))
    required={'owner-teardown-preserves-replacement','missing-audio-owner','source-teardown-owned-release','missing-physical-service','wrong-pool','wrong-device-target','foreign-audio','foreign-memory','replace-pool','replace-allocation','exhaustion'}
    assert required<=set(native['controls'])
    result=dict(command='boss-stager-audio-transport',status='pass',sha256=program.sha256,
                comparisons=comparisons,controls=native['controls'],host_wired=False,output_enabled=False)
    (directory/'audio-transport-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    else:compare(Path(sys.argv[2]))
