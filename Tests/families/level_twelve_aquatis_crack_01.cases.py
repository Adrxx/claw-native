"""Original-only cases for Aquatis crack logic."""
from clawparity.cases import Case
from clawparity.fixtures import returns


def text(e, s):
    return e.object(len(s)+1, s, data=s.encode()+b'\0')


def table(e, at, values, low=10, stride=4):
    data = e.object(len(values)*stride, 'entries', fill=0x67)
    for i,v in enumerate(values): e.put(data+i*stride,v)
    error=e.object(32,'error'); e.put(error+12,4)
    e.put(at+4,error,low,low+len(values)-1,data,data,stride,0,0)


def resource_map(e, owner, entries):
    bucket=e.object(4,'bucket'); head=0
    for key,value in entries:
        head=e.object(16,'resource',words=[head,0,text(e,key),value])
    e.put(bucket,head); e.put(owner+0x14,bucket,1)


def scene(e,salt,player=True,bits=0,active=(1,0,0,0),now=10000,start=6000,duration=4000,state='LS_IDLE',animate=False,resources=False):
    o=e.object(0x70,'crack',fill=salt&255)
    a=e.object(0x220,'actor',fill=0); s=e.object(0x40,'logic',fill=0x53); b=e.object(0x500,'boss',fill=0x41)
    e.put(o+0x10,s); e.put(o+0x2c,a); e.put(s+0x1c,11); e.put(a+0x190,0)
    for off,v in zip((0x4b8,0x4b4,0x4c4,0x4bc),active): e.put(b+off,v)
    e.put(b+0x4ec,bits); e.put(0x534874,b if player else 0)
    e.put(0x537210,now); e.put(0x5430c4,salt&31); e.put(0x541328,salt); e.put(0x53c260,(salt+3999)&0xffffffff)
    e.put(0x532c0c,0); e.put(0x532c10,salt^0x12345678)
    e.put(o+0x60,start,duration,start,duration)
    left=e.object(20,'delay',words=[0,0,0,text(e,'LS_DELAY'),salt^0x4567])
    right=e.object(20,'idle',words=[0,0,0,text(e,'LS_IDLE'),salt^0x8765])
    root=e.object(20,'state trie',words=[left,right,24,0,0]); e.put(0x537680,root)
    table(e,0x537698,[text(e,'LS_DELAY'),text(e,state),text(e,'LS_IDLE')])
    f=e.object(48,'frame',fill=0); e.put(f+0x1c,salt^0x7373)
    fs=e.object(4,'frames',words=[f]); anim=e.object(32,'animation',fill=0); e.put(anim+0xc,fs,1)
    e.put(o+0x48,anim if animate else 0)
    if animate:
        e.put(a+0x18c,a,anim,f,0,0x10000,1)
        e.put(a+0x1a8,salt ^ 0x6767,salt ^ 0x9898)
    e.override(0x4a3050,returns(salt % 5))
    for off in range(0x4c,0x60,4): e.put(o+off,0)
    if resources:
        manager=e.object(0x40,'manager',fill=0); e.put(a+0xc,manager); e.put(a+0x6c,s)
        for off in (0x10,0x14,0x28,0x2c):
            owner=e.object(0x40,'collection',fill=0); e.put(manager+off,owner)
            entries=[]
            if animate and off==0x2c: entries=[('LEVEL_CRACKGLOW',anim)]
            if animate and off==0x28:
                entries=[(f'LEVEL_EARTHQUAKE{i}',e.object(32,f'earthquake {i}',fill=32+i)) for i in range(1,6)]
            if animate and off==0x10:
                wall=e.object(0x70,'wall sprite',fill=0)
                e.put(wall+0x14,fs); e.put(wall+0x64,0,0)
                e.put(f+0x18,salt ^ 0x1111,salt ^ 0x2222,salt ^ 0x3333,salt ^ 0x4444)
                entries=[('LEVEL_AQUATISWALLCRACK',wall)]
            resource_map(e,owner,entries)
    return dict(obj=o,actor=a,boss=b,state=s)


def ordinary(label,fn,salt,**opts):
    return Case(label,fn,lambda e:scene(e,salt,**opts),receiver=lambda t:t['obj'])


def cases(random_source):
    for fn in (0x406af0,0x406b10,0x406c40):
        for present in (False,True):
            for bits in (0,1,2,3,0xfffffffd,0xffffffff):
                for animate in (False,True):
                    yield ordinary(f'{fn:x} boss={present} bits={bits:x} glow={animate}',fn,random_source.getrandbits(32),player=present,bits=bits,animate=animate)
    for active in ((0,0,0,0),(1,1,0,0),(1,0,1,0),(1,0,0,1),(0xffffffff,0,0,0),(1,0,0,0)):
        for present in (False,True):
            for rand in (0,1,2,3,4,5,32767,0x7fffffff,0xffffffff):
                salt=random_source.getrandbits(32)
                def setup(e,active=active,present=present,rand=rand,salt=salt):
                    t=scene(e,salt,player=present,active=active); e.override(0x4a3050,returns(rand))
                    for off in range(0x3c,0x60,4): e.put(t['obj']+off,0)
                    return t
                yield Case(f'trigger boss={present} active={active} rand={rand:x}',0x406b50,setup,receiver=lambda t:t['obj'])
    for elapsed,limit in ((0,0),(0,1),(3999,4000),(4000,4000),(4001,4000),(0xffffffff,4000),(0x80000000,0x7fffffff),(1,0xffffffff)):
        for fn in (0x406c40,0x406cb0):
            for state in ('LS_DELAY','LS_IDLE','ls_delay','OTHER'):
                start=random_source.getrandbits(32)
                yield ordinary(f'{fn:x} elapsed={elapsed:x} limit={limit:x} state={state}',fn,random_source.getrandbits(32),start=start,now=(start+elapsed)&0xffffffff,duration=limit,state=state)
    for animate in (False,True):
        for present in (False,True):
            for salt in (0,0xffffffff,random_source.getrandbits(32)):
                yield Case(f'constructor glow={animate} boss={present} salt={salt:x}',0x4068f0,lambda e,salt=salt,present=present,animate=animate:scene(e,salt,player=present,animate=animate,resources=True),receiver=lambda t:t['obj'],arguments=(lambda t:t['actor'],))
    for low,index in ((-2,-2),(-2,0),(10,11),(10,12),(10,9),(10,13)):
        for stride in (4,12):
            for callback in (False,True):
                salt=random_source.getrandbits(32)
                def setup(e,low=low,stride=stride,callback=callback,salt=salt):
                    o=e.object(32,'dispatch',fill=0x49); record=e.object(48,'observations')
                    def effect(e,c):
                        e.put(record,c.receiver,e.get(0x534890),e.get(0x534894),e.get(0x5348a8),e.get(c.receiver+4),e.get(0x534898)); return salt
                    cb=e.stub('state callback','thiscall',0,effect)
                    table(e,0x534888,[cb if callback else 0]*3,low,stride)
                    locator=e.object(24,'RTTI locator'); info=e.object(16,'type descriptor',fill=0x71); vt=e.object(12,'vtable')
                    e.put(locator+12,info); e.put(vt,locator); e.put(o,vt+4,salt)
                    return dict(obj=o)
                yield Case(f'dispatch low={low} key={index} stride={stride} callback={callback}',0x406520,setup,receiver=lambda t:t['obj'],arguments=(index,))

    # Reach signed-index sound selection, disabled sound, and the play boundary.
    for rand in (0,1,2,3,4,9,0xffffffff,0xfffffffc):
        for enabled in (0,1):
            salt=random_source.getrandbits(32)
            def sound(e,rand=rand,enabled=enabled,salt=salt):
                t=scene(e,salt)
                for off in range(0x3c,0x60,4):
                    clip=e.object(32,'sound resource',fill=0)
                    interface=e.object(32,'sound interface',fill=0)
                    backend=e.object(0x80,'sound backend',fill=0)
                    e.put(clip+0x10,interface); e.put(interface+0x10,backend)
                    e.put(t['obj']+off,clip)
                e.put(0x532c0c,enabled)
                def rng(e,c):
                    e.put(0x537210,(salt+17)&0xffffffff)
                    return rand
                e.override(0x4a3050,rng)
                return t
            yield Case(f'sound rand={rand:x} enabled={enabled}',0x406b50,sound,receiver=lambda t:t['obj'])
    # CString table growth initializes each fresh entry before comparison.
    for index in (8,9,13,15):
        for low in (10,-4):
            salt=random_source.getrandbits(32)
            def grown(e,index=index,low=low,salt=salt):
                t=scene(e,salt,active=(0,0,0,0))
                table(e,0x537698,[text(e,'FIRST'),text(e,'SECOND'),text(e,'THIRD')],low)
                e.put(t['state']+0x1c,index)
                return t
            yield Case(f'state table grow {low} key={index}',0x406cb0,grown,receiver=lambda t:t['obj'])
    # Construction must publish all fields before resource callbacks inspect it.
    for salt in (1,0x87654321,random_source.getrandbits(32)):
        def constructor(e,salt=salt):
            t=scene(e,salt,animate=True,resources=True)
            o,a=t['obj'],t['actor']
            e.put(o+0x10,e.object(64,'old state',fill=0x72))
            e.put(o+0x2c,e.object(0x220,'old actor',fill=0x63))
            e.put(o+0x48,e.object(32,'old glow',fill=0x54))
            e.put(a+0x138,0xaabbccdd,0x11223344,0x55667788,0x99aabbcc,0xddeeff11)
            manager=e.get(a+0xc)
            collection=e.get(manager+0x14)
            hit=e.object(32,'hit resource',fill=0x48)
            attack=e.object(32,'attack resource',fill=0x56)
            resource_map(e,collection,[('LogicHit',hit),('LogicAttack',attack)])
            log=e.object(256,'logic callback log',fill=0)
            methods=e.object(0x28,'logic methods',fill=0)
            def record(e,c):
                at=log+4+e.get(log)*32
                e.put(at,c.receiver,e.get(o+0x10),e.get(o+0x2c),e.get(a+0x138))
                for i,v in enumerate(c.arguments): e.put(at+16+i*4,v)
                e.put(log,e.get(log)+1)
                return 0
            e.put(methods+0x1c,e.stub('clear logic','thiscall',0,record))
            e.put(methods+0x24,e.stub('install logic','thiscall',2,record))
            for off in (0x70,0x78):
                component=e.object(32,'logic component',words=[methods],fill=0x39)
                e.put(a+off,component)
            return t
        yield Case(f'constructor publication {salt:x}',0x4068f0,constructor,receiver=lambda t:t['obj'],arguments=(lambda t:t['actor'],))
    # A real enabled sound interface records every argument and sees state order.
    for rand in range(5):
        salt=random_source.getrandbits(32)
        def playing(e,rand=rand,salt=salt):
            t=scene(e,salt)
            log=e.object(512,'sound observations',fill=0)
            methods=e.object(0x48,'sound methods',fill=0)
            def observe(e,c):
                at=log+4+e.get(log)*48
                e.put(at,c.receiver,e.get(t['obj']+0x24),e.get(t['state']+0x1c),e.get(t['obj']+0x64))
                for i,v in enumerate(c.arguments): e.put(at+16+i*4,v)
                e.put(log,e.get(log)+1)
                return 0
            def status(e,c):
                observe(e,c); e.put(c.arguments[1],0); return 0
            e.put(methods+0x24,e.stub('GetStatus','stdcall',2,status))
            for off in (0x3c,0x40,0x44):
                e.put(methods+off,e.stub(f'sound setter {off:x}','stdcall',2,observe))
            e.put(methods+0x30,e.stub('Play','stdcall',4,observe))
            com=e.object(4,'sound COM',words=[methods])
            backend=e.object(0x80,'enabled audio backend',fill=0); e.put(backend+0x78,1)
            for off in range(0x4c,0x60,4):
                clip=e.object(32,'earthquake resource',fill=0)
                interface=e.object(0x38,'earthquake interface',fill=0)
                node=e.object(0x38,'idle sound buffer',fill=0)
                e.put(clip+0x10,interface); e.put(interface+0x10,backend)
                e.put(interface+0x18,22050,123,456)
                e.put(interface+0x30,node+4,node+4)
                e.put(node+0xc,com,backend,0xffffffff,22050)
                e.put(node+0x30,1)
                e.put(t['obj']+off,clip)
            e.put(0x532c0c,1); e.put(0x532c10,rand)
            e.override(0x4a3050,returns(rand))
            return t
        yield Case(f'play enabled sound index {rand}',0x406b50,playing,receiver=lambda t:t['obj'])
