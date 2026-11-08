"""Independent v1.3 proposed-position contact cases."""
from clawparity.cases import Case
CONTACT = 0x4D81D0
PROBES = (0x4D7990, 0x4D7BA0, 0x4D7DB0, 0x4D7FC0)


def scene(env, current=(40,40), bounds=(-2,-3,2,3), flags=0x100, movement=1,
          tile=0, mode='zero', step=2, positions=(), callback=1,
          peer_callback=True, mutation=None, category=0x20, peer_category=0x20):
    manager=env.object(0x100,'manager',fill=0x37)
    world=env.object(0x40,'world',fill=0x91)
    objects=env.object(0x40,'objects',fill=0x29)
    plane=env.object(0xa0,'plane',fill=0x63)
    mover=env.object(0x180,'mover',fill=0x57)
    output=env.object(4,'output',words=[0xF1E2D3C4])
    trace=env.object(0x2000,'observations',fill=0)
    env.put(manager+0xc,world);env.put(world+8,objects);env.put(objects+0x14,0)
    env.put(manager+0x5c,plane);env.put(plane+0x30,128,128);env.put(plane+0x8c,4,4)
    cells=env.object(64*4,'tiles',words=[tile]*64)
    rows=env.object(8*4,'rows',words=[i*8 for i in range(8)])
    env.put(plane+0x20,cells,rows)
    classifier=env.object(4,'classifier');methods=env.object(0x1c,'methods',fill=0)
    table=env.object(8,'classifiers',words=[classifier,classifier])
    env.put(manager+0x4c,table);env.put(classifier,methods)
    def classify(e,call):
        n=e.get(trace);e.put(trace,n+1)
        e.put(trace+0x40+n*0x10,call.receiver,*call.arguments,e.get(mover+8))
        if mode=='one':return 1
        if mode=='two':return 2
        if mode=='other':return 3
        if mode=='partial':return int(n<2)
        return 0
    env.put(methods+0x18,env.stub('tile classifier','thiscall',2,classify))
    env.put(mover+8,flags);env.put(mover+0x5c,*current)
    env.put(mover+0x90,0,0x1248ABCD);env.put(mover+0xe4,movement,0x80)
    env.put(mover+0xf4,category,step,step);env.put(mover+0x134,*bounds)
    peers=[]
    for i,position in enumerate(positions):
        if position=='self':peers.append(mover);continue
        peer=env.object(0x180,f'peer {i}',fill=0x6b+i)
        env.put(peer+8,0x100);env.put(peer+0x5c,*position)
        env.put(peer+0x90,0,0x3456CDEF);env.put(peer+0xe8,peer_category)
        env.put(peer+0xf4,0);env.put(peer+0x134,-2,-3,2,3);peers.append(peer)
    head=0
    for peer in reversed(peers):head=env.object(12,'node',words=[head,0xDECAF123,peer])
    env.put(objects+0x14,head)
    def bump(e,call):
        actor=call.arguments[0];n=e.get(trace+4);e.put(trace+4,n+1)
        e.put(trace+0x1000+n*0x20,actor,e.get(actor+0x94),e.get(mover+0x94),
              e.get(mover+0xf4),e.get(mover+0x5c),e.get(mover+0x60))
        if actor==mover:
            if mutation=='mask':e.put(mover+0xf4,0)
            elif mutation=='peer-callback':e.put(e.get(mover+0x94)+0x90,0)
            elif mutation=='move':e.put(mover+0x5c,39,41)
            return int(n>0) if callback=='second' else callback
        return 0xBAADF00D
    address=env.stub('LogicBump','cdecl',1,bump)
    bump_table=env.object(0x14,'callback record',fill=0x45);env.put(bump_table+0x10,address)
    if callback is not None:env.put(mover+0x90,bump_table)
    if peer_callback:
        for peer in peers:
            if peer!=mover:env.put(peer+0x90,bump_table)
    return dict(manager=manager,mover=mover,output=output,peers=peers,trace=trace)


def contact(label,proposed=(60,40),**options):
    return Case(label,CONTACT,lambda e:scene(e,**options),receiver=lambda t:t['manager'],
                arguments=(lambda t:t['mover'],*proposed))


def probe(label,index,current=(40,40),proposed=None,**options):
    proposed=((48,40),(32,40),(40,48),(40,32))[index] if proposed is None else proposed
    return Case(label,PROBES[index],lambda e:scene(e,current=current,**options),
                receiver=lambda t:t['manager'],arguments=(lambda t:t['mover'],*proposed,
                lambda t:t['output'],0xA178C34D))


def cases(random_source):
    yield contact('mover disabled',flags=0,positions=((60,40),))
    yield contact('empty list')
    for cb in (None,0,1,0x80000000):
        for pcb in (False,True):
            yield contact(f'callbacks {cb} {pcb}',callback=cb,peer_callback=pcb,positions=((60,40),))
    for mutation in ('mask','peer-callback','move'):
        yield contact(f'callback changes {mutation}',mutation=mutation,positions=((60,40),))
    yield contact('reject then accept',callback='second',positions=((60,40),(61,40)))
    yield contact('skip self',positions=('self',(60,40)))
    for which in ('flag','mask','mover-sentinel','peer-sentinel'):
        def setup(e,which=which):
            t=scene(e,positions=((60,40),))
            if which=='flag':e.put(t['peers'][0]+8,0)
            if which=='mask':e.put(t['peers'][0]+0xe8,0x40)
            if which=='mover-sentinel':e.put(t['mover']+0x134,0x80000000)
            if which=='peer-sentinel':e.put(t['peers'][0]+0x134,0x80000000)
            return t
        yield Case(which,CONTACT,setup,receiver=lambda t:t['manager'],arguments=(lambda t:t['mover'],60,40))
    for dx,dy in ((0,0),(-4,0),(4,0),(0,-6),(0,6),(-5,0),(5,0),(0,-7),(0,7)):
        yield contact(f'current relative {dx},{dy}',positions=((40+dx,40+dy),),proposed=(40+dx,40+dy))
        yield contact(f'proposed relative {dx},{dy}',positions=((60,40),),proposed=(60+dx,40+dy))
    for c in (-2147483648,-2147483647,2147483646,2147483647):
        yield contact(f'wrapped {c}',positions=((c,40),),proposed=(c,40))
    for i in range(4):
        for mode in ('zero','one','two','other','partial'):
            for flags in (0x100,0x500):yield probe(f'probe {i} {mode} {flags:x}',i,mode=mode,flags=flags)
        for tile in (0xEEEEEEEE,0xFFFFFFFF,0xCAFE0001):yield probe(f'probe {i} tile {tile:x}',i,tile=tile)
        for cur,prop in (((-20,-20),(-12,-12)),((140,140),(148,148)),((40,40),(40,40)),((40,40),(41,41))):
            yield probe(f'probe {i} clamp {cur} {prop}',i,current=cur,proposed=prop)
        for step in (1,3,17):yield probe(f'probe {i} step {step}',i,step=step)
        for cb in (None,0,1):
            prop=((48,40),(32,40),(40,48),(40,32))[i]
            yield probe(f'probe {i} bump {cb}',i,callback=cb,positions=(prop,))
        yield probe(f'probe {i} empty span',i,bounds=(2,3,-2,-3))
    for function in (0x4D7860,0x4D78F0):
        for movement in (-1,0,1,2,3,7,8):
            for delta in ((0,0),(8,0),(0,8),(-8,-8),(8,8)):
                mode='one' if delta==(8,8) else 'zero'
                flags=(0x100,0x400100,0x110,0x400110)[(movement+sum(delta))%4]
                yield Case(f'dispatch {function:x} {movement} {delta}',function,
                    lambda e,m=movement,o=mode,f=flags:scene(e,movement=m,flags=f,mode=o),
                    receiver=lambda t:t['manager'],arguments=(lambda t:t['mover'],40+delta[0],40+delta[1],0xA0234B5C))
    for n in range(20):
        x=random_source.randrange(20,80);y=random_source.randrange(20,80)
        dx=random_source.choice((-9,-1,0,1,9));dy=random_source.choice((-9,-1,0,1,9))
        yield contact(f'random {n}',current=(x,y),proposed=(x+dx,y+dy),positions=((x+dx,y+dy),),bounds=(-1,-2,3,4))
