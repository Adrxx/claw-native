"""Original-driven stalactite state and constructor cases."""
import struct
from clawparity.cases import Case
M=0xffffffff

def obj(e,*args,**kwargs):
    kwargs.setdefault('fill',0)
    return e.object(*args,**kwargs)

def signed(v):
    return v if v < 0x80000000 else v-0x100000000

def text(e,s):
    return obj(e,len(s)+1,s,data=s.encode()+b'\0')

def dictionary(e,at,items):
    head=0
    for s,v in items:
        head=obj(e,16,'map node',words=[head,0,text(e,s),v])
    bucket=obj(e,4,'bucket',words=[head])
    e.put(at+4,bucket,1)

def state(seed,f,mode=0,point=(3,4),np=False,nc=False,elapsed=10,delay=10,sound=0,done=0,countdown=0,restart=False,xy=(-17,29),values=(0,0,0,0),resources=0):
    def setup(e):
        a=obj(e,0x1d0,'stalactite',data=seed)
        g=obj(e,0x240,'world object')
        c=obj(e,0x180,'configuration')
        engine=obj(e,0x100,'world services')
        collision=obj(e,0x100,'collision service')
        p=obj(e,0x100,'player')
        pc=obj(e,0x20,'player chain')
        pd=obj(e,0xa0,'player data')
        e.put(p+0x6c,pc);e.put(pc+0x14,pd);e.put(pd+0x80,0x12345678)
        e.put(p+0x4c,point[0]&M,point[1]&M);e.put(0x537e88,0 if np else p)
        e.put(g+0xc,engine);e.put(g+0x6c,c);e.put(engine+0x24,collision)
        e.put(g+0x4c,xy[0]&M,xy[1]&M);e.put(g+0x148,11,13);e.put(g+0xcc,mode);e.put(g+8,0xa6);e.put(g+0x40,0xb7)
        e.put(c+0x1c,0x73616219)
        for off,v in zip((0x2c,0x34,0x30,0x38),values):e.put(c+off,v&M)
        e.put(c+0xb8,0x87654321,delay&M);e.put(c+0xf0,1,2,8,9)
        e.put(a+0xc,g);e.put(a+0x10,0 if nc else c);e.put(a+0x12c,g)
        e.put(a+0x1a8,0x76543210 if restart else 0x12345678)
        e.put(a+0x1ac,xy[0]&M,xy[1]&M);e.put(a+0x1bc,(100-elapsed)&M,(delay ^ 0x13579135) & M if f in (0x48edd0,0x48ed70) else delay&M)
        e.put(0x537210,100);e.put(0x5430c4,0);e.put(0x532c0c,1 if sound else 0);e.put(0x532c10,0x11224488)
        frame=obj(e,0x30,'sequence frame');e.put(frame+0xc,9);e.put(frame+0x18,4,0x28476183)
        frames=obj(e,4,'frame list',words=[frame]);seq=obj(e,0x20,'sequence');e.put(seq+0xc,frames,1)
        e.put(a+0x19c,seq,seq)
        e.put(g+0x18c,g,seq if f==0x48ef90 else 0,frame,0,countdown,1,done,4,4,0x3f800000)
        snd=obj(e,0x20,'sound resource');sp=obj(e,0x20,'sound player');sb=obj(e,0x100,'sound backend')
        e.put(snd+0x10,sp);e.put(sp+0x10,sb)
        e.put(a+0x1b4,0 if sound==1 else snd);e.put(a+0x1b8,0 if sound==1 else snd)
        names={0x48ed10:'ES_IDLE',0x48ed70:'ES_FALLINGDELAY',0x48edd0:'ES_FALLINGDELAY',0x48ee10:'ES_FALLING',0x48ee30:'ES_FALLING',0x48eee0:'ES_DEAD',0x48ef00:'ES_DEAD',0x48ef90:'ES_RESTART',0x48efd0:'ES_RESTART',0x48f040:'ES_IDLE',0x48e990:'ES_IDLE'}
        leaf=obj(e,20,'state registry entry');e.put(leaf,leaf,leaf,0,text(e,names[f]),0x56781923);e.put(0x537680,leaf)
        def copy(e,call):
            e.write(call.arguments[0],e.read(call.arguments[1],16));return 1
        def inside(e,call):
            l,t,r,b=struct.unpack('<4i',e.read(call.arguments[0],16));x,y=map(signed,call.arguments[1:]);return int(l<=x<r and t<=y<b)
        e.override(0x546d58,copy);e.override(0x546cd4,inside)
        log=obj(e,16,'callback observation')
        def cb(e,call):
            e.put(log,call.receiver,e.get(a+0x68),e.get(a+0x70),e.get(g+0xcc));e.put(c+0x1c,0x8899aa11);return 0xabcdf019
        vt=obj(e,0x30,'actor vtable');e.put(vt+0x24,e.stub('reset callback','thiscall',0,cb));e.put(a,vt)
        if f==0x48e990:
            shapes=obj(e,0x40,'shape resources');images=obj(e,0x40,'image resources');sounds=obj(e,0x40,'sound resources');sequences=obj(e,0x40,'sequence resources')
            e.put(engine+0x10,images,shapes);e.put(engine+0x28,sounds,sequences)
            dictionary(e,shapes+0x10,[])
            image=obj(e,0x80,'image set');pixels=obj(e,0x30,'image frame');e.put(pixels+0x18,3,5,19,31)
            il=obj(e,4,'image frames',words=[pixels]);e.put(image+0x14,il);e.put(image+0x64,0,0)
            dictionary(e,images+0x10,[('LEVEL_PROJECTILES_STALACTITE',image)] if resources&1 else [])
            fallback=obj(e,0x20,'fallback sequence');e.put(fallback+0xc,frames,1)
            crumble=obj(e,0x20,'crumble sequence');e.put(crumble+0xc,frames,1)
            si=[('GAME_NULL',fallback)]
            if resources&2:si += [('LEVEL_STALACTITE_HOME',seq)]
            if resources&4:si += [('LEVEL_STALACTITE_CRUMBLE',crumble)]
            hit=obj(e,0x20,'hit sound');snap=obj(e,0x20,'snap sound')
            dictionary(e,sequences+0x10,si)
            dictionary(e,sounds+0x10,[('LEVEL_STALACTITEHIT2',hit),('LEVEL_STALACTITESNAP2',snap)] if resources&1 else [])
            e.put(g+0x170,0,0)
        return {'actor':a,'game':g}
    return setup

def dispatch(seed,index,nonzero=True):
    def setup(e):
        a=obj(e,0x40,'dispatch receiver',data=seed[:0x40]);log=obj(e,16,'dispatch observation')
        def cb(e,call):
            e.put(log,call.receiver,e.get(0x53c9f0),e.get(0x53c9d8),e.get(0x53c9dc));return 0x98765432
        stub=e.stub('state callback','thiscall',0,cb);table=obj(e,12,'dispatch table',words=[stub if nonzero else 0]*3)
        e.put(0x53c9d8,0,2,table,table,4,table,0x87654321)
        vt=obj(e,12,'RTTI vtable');loc=obj(e,20,'RTTI locator');info=obj(e,8,'RTTI info')
        e.put(vt,loc);e.put(loc+0xc,info);e.put(a,vt+4)
        return {'actor':a,'index':index}
    return setup

def cases(random_source):
    seed=random_source.randbytes(0x1d0)
    for idx in (0,1,2,-1,3):
        for nz in (True,False):yield Case(f'dispatch {idx} {nz}',0x48e5c0,dispatch(seed,idx,nz),receiver=lambda t:t['actor'],arguments=(lambda t:t['index']&M,))
    for f in (0x48ed10,0x48edd0,0x48ee30,0x48ef00,0x48efd0):
        for sound in (0,1,2):yield Case(f'state {f:x} sound {sound}',f,state(seed,f,sound=sound),receiver=lambda t:t['actor'])
    for pt in ((1,2),(7,8),(8,8),(7,9),(0,4),(3,1),(3,4),(-1,-1)):
        yield Case(f'point {pt}',0x48ed70,state(seed,0x48ed70,point=pt),receiver=lambda t:t['actor'])
    for np,nc in ((True,False),(False,True),(True,True)):
        yield Case(f'missing point {np} {nc}',0x48ed70,state(seed,0x48ed70,np=np,nc=nc),receiver=lambda t:t['actor'])
    for elapsed,delay in ((0,0),(0,1),(9,10),(10,10),(11,10),(M,1),(1,M)):
        yield Case(f'delay {elapsed} {delay}',0x48ee10,state(seed,0x48ee10,elapsed=elapsed,delay=delay),receiver=lambda t:t['actor'])
    for mode in (0,1,2,7,M):yield Case(f'fall mode {mode}',0x48eee0,state(seed,0x48eee0,mode=mode),receiver=lambda t:t['actor'])
    for done in (0,1,7):
        for countdown in (0,1,9):yield Case(f'animation {done} {countdown}',0x48ef90,state(seed,0x48ef90,done=done,countdown=countdown),receiver=lambda t:t['actor'])
    for restart in (False,True):
        for xy in ((0,0),(-1,1),(-2147483648,2147483647),(781,-213)):
            yield Case(f'restart {restart} {xy}',0x48f040,state(seed,0x48f040,restart=restart,xy=xy),receiver=lambda t:t['actor'])
    for values in ((0,0,0,0),(11,-12,13,-14),(0,22,0,44),(-31,0,-33,0)):
        for res in range(8):yield Case(f'constructor {values} {res}',0x48e990,state(seed,0x48e990,values=values,resources=res),receiver=lambda t:t['actor'],arguments=(lambda t:t['game'],))
