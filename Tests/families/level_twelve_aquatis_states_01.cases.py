"""Original-derived Aquatis state cases with deterministic branch coverage."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns


def setup_case(words, c):
    def setup(env):
        r=env.object(0x500,'Aquatis',data=words)
        s=env.object(0x1c0,'sprite',fill=0)
        d=env.object(0x180,'descriptor',data=words[:0x180])
        t=env.object(0x30,'logic state',fill=0)
        vt=env.object(0x80,'vtable',fill=0)
        log=env.object(0x60,'callback observations',fill=0)
        def callback(env,call):
            env.put(log,env.get(log)+1,call.receiver,env.get(r+0x4a0),env.get(r+0x4b4),env.get(r+0x4ec))
            env.put(log+24,env.get(d+0x10c),env.get(r+0x4b0),env.get(t+0x1c))
            return 0x8734ff21
        env.put(vt+0x48,env.stub('state advance','thiscall',0,callback))
        env.put(r,vt)
        env.put(r+0xc,d,t)
        env.put(r+0x12c,s)
        env.put(t+0x1c,0x12347abc)
        env.put(s+8,0x23450412)
        env.put(s+0x40,c.get('facing',0))
        env.put(s+0x16c,c.get('frame',17))
        env.put(s+0x190,0)
        env.put(s+0x19c,c.get('delay',0))
        env.put(s+0x1a4,c.get('finished',1))
        env.put(d+0x50,c.get('y',731))
        env.put(r+0x184,c.get('phase',0))
        env.put(r+0x18c,0)
        env.put(r+0x374,0)
        env.put(r+0x45c,1)
        for off in (0x460,0x468,0x46c): env.put(r+off,0)
        for off in range(0x488,0x4a0,4): env.put(r+off,0)
        for off in range(0x4a0,0x4cc,4): env.put(r+off,c.get(off,0x6d935b21 if off in (0x4a8,0x4bc,0x4c8) else 0))
        env.put(r+0x4b8,c.get('live',1))
        env.put(r+0x4ec,c.get('idle_delay',0))
        for base in (0x4cc,0x4d4,0x4dc): env.put(r+base,c.get('base',1000),c.get('duration',30))
        env.put(0x537210,c.get('clock',1030))
        env.put(0x5430c4,19)
        env.put(0x534878,c.get('alternate',0))
        env.put(0x532c0c,c.get('sound_enabled',1))
        env.put(0x532c10,77)
        env.put(0x534874,r)
        env.put(0x544d18,0)
        env.put(r+0x1a4,env.get(0x52e1c8)+12,env.get(0x52e1c8)+12)
        bits=c.get('bits',17)
        env.put(r+0x2f4,0x513e34,0,bits)
        if bits>32:
            bp=env.object(16,'bit words',words=[0x87125483,0x81234567,0x12345678,0x7834abcd])
            env.put(r+0x300,bp)
        else: env.put(r+0x300,0x87125483)
        p=env.object(0x190,'player descriptor',fill=0)
        ps=env.object(0x140,'player state',fill=0)
        env.put(p+0x6c,ps)
        env.put(p+0x10c,c.get('player_health',71))
        env.put(0x537e88,p)
        speaker=env.object(0x190,'speaker',fill=0)
        ss=env.object(0x140,'speaker state',fill=0)
        env.put(speaker+0x6c,ss)
        env.put(ss+0x1c,0xf)
        env.put(ss+0x130,0x8734aabb)
        env.put(0x53c9ac,speaker)
        env.put(0x53c9a8,0)
        env.put(0x53c9b0,d)
        if c.get('sound',True):
            for off in range(0x488,0x4a0,4):
                h=env.object(0x20,'sound handle',fill=0)
                b=env.object(0x30,'sound backend',fill=0)
                root=env.object(0x80,'disabled sound root',fill=0)
                env.put(h+0x10,b)
                env.put(b+0x10,root)
                env.put(r+off,h)
        env.write(0x5262b4,struct.pack('<f',c.get('scale',0.375)))
        key=c.get('key',b'LS_HIGHPUNCH')
        kp=env.object(len(key)+1,'registry key',data=key+b'\0')
        node=env.object(0x18,'registry node',fill=0)
        env.put(node,node,node,0,kp,0x5678bace)
        env.put(0x537668+0x18,node)
        env.override(0x4a3050,returns(c.get('rand',0)))
        return r
    return setup


def cases(random_source):
    words=bytes(random_source.randrange(256) for _ in range(0x500))
    index=0
    def emit(fn,c=None,**kw):
        nonlocal index
        index+=1
        c=dict(c or {},**kw)
        return Case(f'{index} {fn:x} {c}',fn,setup_case(words,c),receiver=lambda r:r)
    for c in ({'live':0},{'idle_delay':1},{'phase':0},{'phase':1},{'phase':0xffffffff},{'phase':5},{'phase':2,'clock':1029},{'phase':2},{'phase':4,'base':0xfffffff0,'clock':14},{0x4c0:1,'key':b'LS_SCARED'},{'finished':0},{'delay':1}):
        yield emit(0x4051a0,c)
    for first in (0,1):
        for clock,c0,c4 in ((1029,0,0),(1030,0,0),(1031,1,0),(1031,0,1),(0,0,0)):
            yield emit(0x405440,{0x4a0:first,0x4c0:c0,0x4c4:c4,'clock':clock})
    for alternate in (0,1,0xffffffff):
        for first in (0,1):
            for clock in (1029,1030,1031):
                yield emit(0x405540,{0x4a0:first,0x4b4:37,'alternate':alternate,'clock':clock,'key':b'LS_LOWPUNCH' if alternate else b'LS_HIGHPUNCH'})
    for fn,frame in ((0x405640,0xcc),(0x4057a0,0xcf)):
        for first,sound,enabled in ((0,False,1),(0,True,0),(0,True,1),(1,True,1)):
            for facing in (0,2,0x83):
                for finished,delay,frenzy in ((0,0,0),(1,1,0),(1,0,0),(1,0,1)):
                    yield emit(fn,{0x4a0:first,0x4b4:frenzy,'sound':sound,'sound_enabled':enabled,'facing':facing,'finished':finished,'delay':delay,'frame':frame,'key':b'LS_SUPERFRENZY'})
        yield emit(fn,frame=frame-1)
        yield emit(fn,frame=frame+1)
    for fn in (0x4059e0,0x405df0):
        for first in (0,1):
            for finished,delay,secondary in ((0,0,0),(1,1,0),(1,0,1),(1,0,0)):
                c={0x4a0:first,0x4a4:secondary,'finished':finished,'delay':delay,'key':b'LS_SUPERFRENZY'}
                if fn==0x405df0:
                    for health in (0,0xffffffff,1):
                        for bits in (0,4,5,32,33):
                            yield emit(fn,c,player_health=health,bits=bits)
                else: yield emit(fn,c)
    yield emit(0x405a60,finished=0)
    yield emit(0x405a60,delay=1)
    for count in (0,1,2,3,0xffffffff,0x7fffffff):
        for rand in (0,84,85,100,101,186,0xffffffff,0x80000000):
            yield emit(0x405a60,{0x4ac:count,'rand':rand,'key':b'LS_SCARED' if count==2 else b'LS_HIGHPUNCH'})
    yield emit(0x405d50,{0x4a0:0xabc32145,0x4a4:0x7654abcd},key=b'LS_DEADACT1')
    yield emit(0x405ed0,live=0)
    for scale in (0.,1.,0.375,-0.125,0.009,4.25):
        for y in (0,50,0x80000000,0xffffffff): yield emit(0x405ed0,{off:0x1234a000+off for off in range(0x4a0,0x4cc,4)},scale=scale,y=y)
    for bits in (0,1,32,33,64): yield emit(0x405fa0,bits=bits)

    for fn in (0x405640,0x4057a0,0x4059e0,0x405df0):
        yield emit(fn,{0x4a0:0,0x4a4:0x4312abcd},finished=0)
        yield emit(fn,{0x4a0:0x12349876,0x4a4:0},finished=0)
