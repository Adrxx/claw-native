"""Inputs derived from the original conveyor instructions."""
import struct
from clawparity.cases import Case


def world(speed, noise, mode=0, overlap=True, active=True, cycle=True, ctor=False, right=True, enabled=0, mutation=None, geometry=0, rectangle=None, elapsed=1, missing_cycles=False, callback_change=0):
    def setup(env):
        def obj(n, name):
            return env.object(n, name, data=bytes(noise[i % len(noise)] ^ ((i * 37 + i // 32) & 255) for i in range(n)))
        owner, actor, state = obj(128,'controller'), obj(512,'actor'), obj(208,'logic')
        player, link, motion = obj(320,'player'), obj(32,'player-link'), obj(144,'movement')
        env.put(owner+8, actor, actor, state)
        env.put(owner+40, actor, actor, state)
        env.put(state+188,speed)
        env.put(actor+108,state)
        env.put(player+108,link)
        env.put(link+20,motion if active else 0)
        env.put(0x537e88,player)
        env.put(0x5430c4,elapsed)
        env.put(player+204,mode)
        px=int.from_bytes(noise[:4],'little')%201-100
        env.put(player+76,px,17)
        env.put(player+280,-9,113,13,29)
        env.put(actor+76,px+(2 if overlap else 100),19)
        env.put(actor+280,-6,-3,17,23)
        if geometry:
            env.put(actor+76,px+geometry,19)
        if rectangle is not None:
            env.put(actor+280,*rectangle)
        root=env.object(20,'state-root',fill=0)
        idle=env.object(20,'idle-leaf',fill=0)
        move=env.object(20,'move-leaf',fill=0)
        ni=env.object(8,'idle-name',data=b'ES_IDLE\0')
        nm=env.object(8,'move-name',data=b'ES_MOVE\0')
        env.put(root,idle,move,26,0,0)
        env.put(idle,0,0,26,ni,0x13579)
        env.put(move,0,0,26,nm,0x2468a)
        env.put(0x537680,root)
        cycles=[]
        for n in range(4):
            anim=obj(24,f'animation-{n}')
            table=env.object(4,f'frames-{n}',fill=0)
            frame=env.object(48,f'frame-{n}',fill=0)
            env.put(frame+12,9)
            env.put(frame+24,7+n,0x113+n)
            env.put(anim+12,table,1)
            env.put(table,frame)
            cycles.append(anim if cycle else 0)
        env.put(owner+72,*cycles)
        env.put(actor+396,actor)
        env.put(actor+400,cycles[1])
        env.put(actor+412,5,0,0,0x113,0x224,0x3f800000)
        record=env.object(64,'intersection-observations',fill=0)
        def intersect(env,call):
            a,b=[struct.unpack('<4i',env.read(p,16)) for p in call.arguments[1:]]
            env.write(record,env.read(call.arguments[1],16)+env.read(call.arguments[2],16))
            env.put(record+32,call.receiver,*call.arguments,env.get(state+28),env.get(owner+36))
            r=(max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3]))
            yes=r[0]<r[2] and r[1]<r[3]
            env.write(call.arguments[0],struct.pack('<4i',*(r if yes else (0,0,0,0))))
            if mutation is not None:
                env.put(state+188,mutation)
            return int(yes)
        env.override(0x546ce0,intersect)
        env.override(0x5469e4,lambda e,c:len(e.cstr(c.arguments[0])))
        def decrement(e,c):
            v=(e.get(c.arguments[0])-1)&0xffffffff
            e.put(c.arguments[0],v)
            return v
        env.override(0x5469e8,decrement)
        env.put(0x540e00,0)
        if ctor:
            context=env.object(48,'context',fill=0)
            lm=env.object(48,'logic-map',fill=0)
            cm=env.object(48,'cycle-map',fill=0)
            env.put(lm+24,1)
            logic_bucket=env.object(4,'logic-bucket',fill=0)
            env.put(lm+20,logic_bucket)
            callbacks=env.object(256,'constructor-callback-state',fill=0)
            def observe(tag):
                def effect(e,c):
                    count=e.get(callbacks)
                    at=callbacks+4+count*56
                    e.put(at,tag,c.receiver,len(c.arguments),*(list(c.arguments)+[0,0])[:2])
                    e.write(at+20,e.read(owner,36))
                    e.put(callbacks,count+1)
                    if callback_change == 1 and tag == 1:
                        e.put(actor+108,alternate_state)
                    if callback_change == 2 and tag == 1:
                        e.put(owner+12,alternate)
                    return 0
                return effect
            prior=0
            for n,name in enumerate(('LogicHit','LogicAttack')):
                methods=env.object(40,f'logic-methods-{n}',fill=0)
                handler=env.object(32,f'existing-logic-handler-{n}',fill=0)
                env.put(handler,methods)
                env.put(methods+28,env.stub(f'logic-reset-{n}','thiscall',0,observe(n*2)))
                env.put(methods+36,env.stub(f'logic-bind-{n}','thiscall',2,observe(n*2+1)))
                env.put(actor+(112 if n==0 else 120),handler)
                key=env.object(len(name)+1,f'logic-key-{n}',data=name.encode()+b'\0')
                value=env.object(20,f'logic-map-value-{n}',fill=0)
                env.put(value+16,0x123400+n*57)
                entry=env.object(16,f'logic-entry-{n}',words=[prior,0,key,value])
                prior=entry
            env.put(logic_bucket,prior)
            env.put(cm+24,1)
            buckets=env.object(4,'cycle-map-bucket',fill=0)
            env.put(cm+20,buckets)
            previous=0
            names=('GAME_CYCLE50','GAME_CYCLE100','GAME_CYCLE200','GAME_CYCLE500','GAME_REVERSECYCLE50','GAME_REVERSECYCLE100','GAME_REVERSECYCLE200','GAME_REVERSECYCLE500')
            for n,name in enumerate(names):
                if missing_cycles and n==missing_cycles-1:
                    continue
                anim=obj(24,f'constructor-animation-{n}')
                frames=env.object(4,f'constructor-frames-{n}',fill=0)
                frame=env.object(48,f'constructor-frame-{n}',fill=0)
                env.put(frame+12,9)
                env.put(frame+24,n+11,n+137)
                env.put(anim+12,frames,1)
                env.put(frames,frame)
                key=env.object(len(name)+1,f'cycle-key-{n}',data=name.encode()+b'\0')
                node=env.object(16,f'cycle-entry-{n}',words=[previous,0,key,anim])
                previous=node
            env.put(buckets,previous)
            fallback_frame=env.object(48,'argument-as-animation-frame',fill=0)
            env.put(fallback_frame+12,9)
            env.put(fallback_frame+28,0x3344)
            env.put(context,fallback_frame)
            env.put(actor+16,1,0)
            env.put(context+20,lm)
            env.put(context+44,cm)
            env.put(actor+12,context)
            resource=env.object(128,'resource',fill=0)
            env.write(resource+36,b'LEVEL_CONVEYRIGHT\0' if right else b'LEVEL_CONVEYLEFT\0')
            env.put(actor+368,resource,0)
            env.put(actor+100,enabled)
            env.put(actor+8,0x50 if enabled==0 else 0x20051)
            alternate=obj(512,'pre-construction-actor')
            alternate_state=obj(208,'pre-construction-settings')
            env.write(alternate,env.read(actor,512))
            env.write(alternate_state,env.read(state,208))
            env.put(alternate_state+188,74)
            env.put(alternate+108,alternate_state)
            env.put(owner+12,alternate,alternate_state)
            env.put(owner+40,alternate,alternate,alternate_state)
        return dict(owner=owner,actor=actor)
    return setup


def dispatch(index,noise,stride=4,missing=False,fail=False):
    def setup(env):
        owner=env.object(128,'receiver',data=noise*4)
        vtable=env.object(8,'vtable-and-prefix',fill=0)
        descriptor=env.object(16,'rtti-descriptor',fill=0)
        typeinfo=env.object(8,'type-information',fill=0)
        env.put(vtable,descriptor)
        env.put(descriptor+12,typeinfo)
        env.put(owner,vtable+4)
        table=env.object(stride*3,'handlers',data=(noise*((stride*3+31)//32))[:stride*3])
        fallback=env.object(stride,'fallback',fill=0)
        diagnostic=env.object(24,'error-policy',fill=0)
        observation=env.object(128,'callback-observations',fill=0)
        env.put(diagnostic+12,4)
        env.put(0x53727c,diagnostic,10,12,table,fallback,stride,0x76543210,0xabcdef01)
        env.put(0x544d18,0)
        def callback(slot):
            def effect(e,c):
                e.put(observation,c.receiver,e.get(0x537298),e.get(0x537280),e.get(0x537284),e.get(0x537288),e.get(0x544b14),e.get(diagnostic+8),slot)
                e.write(observation+32,e.read(owner,32))
                return 0x91a72b35+slot
            return effect
        for i in range(3):
            stub=env.stub(f'conveyor-handler-{i}','thiscall',0,callback(i))
            env.put(table+i*stride,0 if missing else stub)
        env.put(fallback,env.stub('fallback-handler','thiscall',0,callback(3)))
        if fail:
            env.override(0x4a9070,lambda e,c:0)
        return dict(owner=owner)
    return setup


def cases(random_source):
    noise=random_source.randbytes(32)
    speeds=sorted(set([0,-1,1,-0x80000000,0x7fffffff]+[s*(t+d) for s in (-1,1) for t in (75,150,225,300) for d in (-1,0,1)]))
    for speed in speeds:
        for live in (False,True):
            yield Case(f'idle speed {speed} cycle {live}',0x431a70,world(speed,noise,cycle=live),receiver=lambda t:t['owner'])
    for mode in (0,1,3,4,0xffffffff):
        for overlap in (False,True):
            for active in (False,True):
                for fn in (0x431b10,0x431b70,0x431bd0):
                    yield Case(f'update {fn:x} mode {mode} overlap {overlap} active {active}',fn,world(-149,noise,mode,overlap,active),receiver=lambda t:t['owner'])
    for speed in (-0x80000000,-301,-1,0,1,301,0x7fffffff):
        for active in (False,True):
            for reset in (0,1,2,0xffffffff):
                yield Case(f'publish {speed} active {active} reset {reset}',0x431c90,world(speed,noise,active=active),receiver=lambda t:t['owner'],arguments=(reset,))
    for i in range(12):
        yield Case(f'move random {i}',0x431b40,world(random_source.getrandbits(32),random_source.randbytes(32)),receiver=lambda t:t['owner'])
    for stride in (4,8,12):
        for index in (10,11,12):
            yield Case(f'dispatch slot {index} stride {stride}',0x431440,dispatch(index,noise,stride),receiver=lambda t:t['owner'],arguments=(index,))
    for speed in (-301,-300,-1,0,1,300,301):
        for right in (False,True):
            for enabled in (0,1,2):
                yield Case(f'construct {speed} right {right} enabled {enabled}',0x431810,world(speed,noise,ctor=True,right=right,enabled=enabled),receiver=lambda t:t['owner'],arguments=(lambda t:t['actor'],))

    for stride in (4,8,12):
        for index in (10,11,12):
            yield Case(f'empty dispatch {index} stride {stride}',0x431440,dispatch(index,noise,stride,missing=True),receiver=lambda t:t['owner'],arguments=(index,))
        for index in (7,9,13,16):
            yield Case(f'grow dispatch {index} stride {stride}',0x431440,dispatch(index,noise,stride),receiver=lambda t:t['owner'],arguments=(index,))
    for fn in (0x431b10,0x431b70,0x431bd0):
        for geometry in (-22,-21,-20,18,19,20,0x7fffffff,-0x80000000):
            yield Case(f'geometry {geometry} entry {fn:x}',fn,world(-301,noise,geometry=geometry),receiver=lambda t:t['owner'])
    for fn in (0x431b10,0x431b70):
        for mutation in (-300,-75,0,1,300):
            for overlap in (False,True):
                yield Case(f'service changes speed {mutation} entry {fn:x} overlap {overlap}',fn,world(-149,noise,overlap=overlap,mutation=mutation),receiver=lambda t:t['owner'])
    for rectangle in ((9,3,-8,29),(-1,5,0,31),(5,-3,-6,13),(0,0,0,0)):
        yield Case(f'constructor signed width {rectangle}',0x431810,world(150,noise,ctor=True,rectangle=rectangle),receiver=lambda t:t['owner'],arguments=(lambda t:t['actor'],))
    for i in range(24):
        fn=(0x431a70,0x431b10,0x431b70)[i%3]
        yield Case(f'random timing and speed {i}',fn,world(random_source.getrandbits(32),random_source.randbytes(32),elapsed=random_source.getrandbits(32),overlap=bool(i%2)),receiver=lambda t:t['owner'])

    for speed in (-301,-300,-1):
        for missing in (1,2,3):
            yield Case(f'constructor missing cycle output {missing} speed {speed}',0x431810,world(speed,noise,ctor=True,missing_cycles=missing),receiver=lambda t:t['owner'],arguments=(lambda t:t['actor'],))

    # A callback can alter pointers before the constructor reloads them.
    for change in (1,2):
        for speed in (-301,-150,-75,0,75,150,301):
            yield Case(f'constructor callback changes pointer {change} speed {speed}',0x431810,world(speed,noise,ctor=True,callback_change=change),receiver=lambda t:t['owner'],arguments=(lambda t:t['actor'],))
    # Exercise both sides of each animation threshold through construction,
    # including independent missing reverse lookups and the last forward one.
    for speed in speeds:
        yield Case(f'constructor threshold {speed}',0x431810,world(speed,noise,ctor=True),receiver=lambda t:t['owner'],arguments=(lambda t:t['actor'],))
    for speed in (-1,0,301):
        for missing in range(1,9):
            yield Case(f'constructor absent resource {missing} speed {speed}',0x431810,world(speed,noise,ctor=True,missing_cycles=missing),receiver=lambda t:t['owner'],arguments=(lambda t:t['actor'],))
