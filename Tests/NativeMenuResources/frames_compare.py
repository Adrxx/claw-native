"""Original/Swift menu frame comparison on the shared native heap and display."""
import hashlib
import json
from .compare import WORK
from .initializer_compare import original_initializer,normalized,physical_effects


def main():
    witness=json.loads((WORK/'frames-swift.json').read_text())
    original,menu,_=original_initializer()
    try:
        application=original.word(menu+4)
        original.put(application+0x2c,menu)
        original.run(0x45b3f0,menu,(0,),phase='menu-entry')
        def is_pointer(offset,value):
            return any(base<=value<base+size for base,size in original.allocations.items())
        def state(row):
            native_pointers,original_pointers={},{}
            actual=normalized(row['state'],native_pointers,lambda off,v:off in row['pointerOffsets'])
            expected=normalized(original.machine.mem_read(menu,0x2c8),original_pointers,is_pointer)
            assert actual==expected,('menu',[(hex(i*4),a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b][:12])
            tokens=[original.word(menu+off) for off in (0x258,0x25c,0x260,0x264,0x268,0x270,0x274,0x278)]
            tokens += [original.word(original.word(menu+0x26c)+4*i) for i in range(15)]
            for i,(token,actor) in enumerate(zip(tokens,row['actors'])):
                a=normalized(actor['data'],native_pointers,lambda off,v:off in actor['pointerOffsets'])
                b=normalized(original.machine.mem_read(token,len(actor['data'])),original_pointers,is_pointer)
                assert a==b,('actor',i,[(hex(j*4),x,y) for j,(x,y) in enumerate(zip(a,b)) if x!=y][:12])
            world=row['world']
            a=normalized(world['data'],native_pointers,lambda off,v:off in world['pointerOffsets'])
            b=normalized(original.machine.mem_read(original.word(original.word(menu+12)+0x24),0xe0),original_pointers,is_pointer)
            assert a==b,('world',[(hex(j*4),x,y) for j,(x,y) in enumerate(zip(a,b)) if x!=y][:12])
            clocks=[original.word(application+off) for off in (0x18,0x1c,0x20,0x24,0x28)]
            clocks += [original.word(p) for p in (0x541328,0x54132c,0x541330,0x541334,0x541338)]
            assert row['clocks']==clocks,('clocks',row['clocks'],clocks)
        assert len(witness['frames'])==61
        for index,row in enumerate(witness['frames']):
            original.advance_time(1000+(index+1)*1000//60)
            start=len(original.physical_events)
            assert original.run(0x428b60,application,phase=f'swift-compare-{index}')==1
            state(row)
            scene=original.word(menu+12);holder=original.word(scene+4)
            surfaces=[original.word(original.word(holder+offset)+44) for offset in (16,20,24)]
            hashes=[]
            for surface in surfaces:
                physical=original.com_objects[original.word(surface+8)]
                hashes.append(hashlib.sha256(original.machine.mem_read(physical['pixels'],physical['pitch']*physical['height'])).hexdigest())
            assert row['surfaces']==hashes,('pixels',index,row['surfaces'],hashes)
            palette=original.com_objects[original.com_objects[original.word(surfaces[0]+8)]['palette']]
            entries=bytes.fromhex(palette['entries'])
            assert row['palette']==list(b''.join(entries[i:i+3] for i in range(0,1024,4)))
            expected=physical_effects(original.physical_events[start:])
            actual=physical_effects(row['effects'],native=True)
            (WORK/'frames-last-effects.json').write_text(json.dumps(dict(index=index,original=expected,native=actual),indent=2)+'\n')
            assert actual==expected,('effects',index,len(actual),len(expected),[(i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b][:4])
        cleanup=json.loads((WORK/'frames-cleanup.json').read_text())
        assert all(cleanup[k]==0 for k in ('cleanupFault','resourceFault','cleanupRemaining','displayFault'))
        controls=json.loads((WORK/'frames-controls.json').read_text())
        assert {(c['kind'],c['address']) for c in controls}=={
            ('owner','428b60'),('owner','4c8fc0'),('owner','4d32e0'),('owner','4c00b0'),('owner','4b9730'),('owner','4b98b0'),
            ('physical','6e120044'),('physical','546d30'),('physical','6e120064'),('physical','6e12002c')}
        assert all(c['rejected'] for c in controls)
        result=dict(status='compared',frames=61,idle_frames=60,state=True,actors=23,world=True,clocks=True,pixels=True,palette=True,ordered_services=True,cleanup=True)
        (WORK/'frames-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    finally:
        for stream in original.files.values():stream.close()


if __name__=='__main__':main()
