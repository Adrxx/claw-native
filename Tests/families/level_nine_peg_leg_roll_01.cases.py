"""PegLeg roll cases derived from original instructions and original callees."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence, reallocate


def setup_actor(seed_word=23, **opts):
    def setup(env):
        actor = env.object(0x500, 'peg-leg', fill=0)
        visual = env.object(0x200, 'visual', fill=0)
        entity = env.object(0x180, 'entity', fill=0)
        state = env.object(0x40, 'state', fill=0)
        attacker = env.object(0x180, 'attacker', fill=0)
        methods = env.object(0xb0, 'methods', fill=0)
        record = env.object(0x100, 'callback record', fill=0)
        env.put(actor, methods)
        env.put(actor + 0xc, entity, state)
        env.put(actor + 0x12c, visual)
        env.put(entity + 0x74, attacker)
        env.put(entity + 0x38, 0xffffffff)
        env.put(entity + 0x10c, opts.get('health', 83))
        env.put(attacker + 0xd0, opts.get('attack_type', 3))
        env.put(attacker + 0x104, opts.get('damage', 17))
        env.put(attacker + 0x138, 0x80000000)
        env.put(visual + 0x40, opts.get('flags', 0))
        for offset in (0x118, 0x128, 0x138):
            env.put(visual + offset, seed_word + offset, 19, seed_word + offset + 41, 67)
        env.put(visual + 0x190, 0)
        env.put(actor + 0x138, seed_word + 5, 37, seed_word + 19)
        env.put(actor + 0x18c, opts.get('direction', 2))
        env.put(actor + 0x260, seed_word, 17, 31, 43, 61, 73, 89, 101)
        env.put(entity + 0x118, 107, 127, 149, 173)
        env.put(actor + 0x4d8, opts.get('saved', 0))
        env.put(actor + 0x424, 2)
        env.put(actor + 0x49c, opts.get('last', 100))
        env.put(actor + 0x4a0, opts.get('cooldown', 50))
        env.put(actor + 0x4b4, opts.get('roll_last', 100))
        env.put(actor + 0x4b8, opts.get('roll_time', 50))
        env.put(actor + 0x4bc, opts.get('target', 100))
        for offset, name, argc in ((0x28,'hit',1),(0x44,'resume',0),(0x58,'done',0),(0x90,'death',1)):
            def effect(e, call, name=name):
                n=e.get(record)
                e.put(record, n+1)
                e.put(record+4+n*56, call.receiver, len(call.arguments), *(list(call.arguments)+[0])[:1],
                      e.get(actor+0x49c), e.get(actor+0x4a0), e.get(actor+0x134), e.get(state+0x1c),
                      {'hit':1,'resume':2,'done':3,'death':4}[name], e.get(actor+0x4b4),
                      e.get(actor+0x4b8), e.get(actor+0x4bc), e.get(visual+0x40),
                      e.get(entity+0x10c), e.get(actor+0x4d8))
                if opts.get('callback_change'):
                    e.put(0x537210, opts.get('now', 200)+1000)
                    e.put(actor+0x4b4, 0)
                return seed_word ^ 0x1789
            env.put(methods+offset, env.stub(name,'thiscall',argc,effect))
        env.put(0x537210,opts.get('now',200)&0xffffffff)
        env.put(0x5430c4,13)
        env.put(0x537680,0)
        env.put(0x53c9ac,0)
        env.put(0x537964,0)
        env.put(0x532c0c,opts.get('audio_enabled',0))
        env.put(0x532c10,seed_word)
        audio=env.object(0x20, 'audio wrapper', fill=0)
        sound=env.object(0x20, 'sound', fill=0)
        driver=env.object(0x80, 'sound driver', fill=0)
        env.put(audio+0x10,sound)
        env.put(sound+0x10,driver)
        env.put(actor+0x490,audio if opts.get('audio') else 0)
        world=env.object(0x80, 'world', fill=0)
        worldstate=env.object(0x40, 'world state', fill=0)
        player=env.object(0x100, 'player', fill=0)
        env.put(0x537e88,world)
        env.put(world+0x6c,worldstate)
        env.put(worldstate+0x14,player)
        env.put(player+0x3c,opts.get('weapon',1))
        current=opts.get('state',b'OTHER')
        text=env.object(len(current)+1,'state name',data=current+b'\0')
        low=opts.get('table_low',0)
        stride=opts.get('table_stride',4)
        names=opts.get('table_names',(current,current,current))
        table=env.object(stride*len(names),'state names',fill=0xa7)
        for slot,name in enumerate(names):
            entry=env.object(len(name)+1,'table state name',data=name+b'\0')
            env.put(table+slot*stride,entry)
        env.put(state+0x1c,opts.get('index',1))
        env.put(0x5376a0,low,low+len(names)-1,table,0,stride,0,0)
        if opts.get('grow'):
            env.put(state+0x1c,-1 if opts['grow']=='down' else 3)
        for offset,value in ((0x50,23.25),(0x68,opts.get('x',100.75)),(0x70,71.5),
                             (0x80,opts.get('left',-500.0)),(0x98,opts.get('right',500.0))):
            env.write(actor+offset,struct.pack('<d',value))
        def copy_rect(e,c):
            e.write(c.arguments[0],e.read(c.arguments[1],16))
            return 1
        env.override(0x546d58,copy_rect)
        env.override(0x4a3050,sequence(*opts.get('randoms',(0,1,2,3,4,5))))
        for offset in range(0x454,0x470,4):
            env.put(actor+offset,seed_word+offset)
        env.put(actor+0x454,0)
        if 'rectangle_words' in opts:
            values=opts['rectangle_words']
            env.put(actor+0x260,*values[:8])
            env.put(actor+0x138,*values[8:11])
            for i,offset in enumerate((0x118,0x128,0x138)):
                env.put(visual+offset,*values[11+i*4:15+i*4])
        if opts.get('animation'):
            old=env.object(0x20,'old animation',fill=0)
            animation=env.object(0x20,'new animation',fill=0)
            frame=env.object(0x30,'animation frame',fill=0)
            frames=env.object(4,'frames',words=[frame])
            env.put(animation+0xc,frames,1)
            env.put(frame+0x1c,seed_word+191)
            env.put(visual+0x190,old)
            env.put(visual+0x19c,17)
            env.put(actor+0x454,animation)
            env.put(actor+0x334,animation,animation)
        if opts.get('mutate_index'):
            def grow_and_change(e,c):
                moved=reallocate()(e,c)
                if e.calls_so_far(c.function)==1:
                    e.put(state+0x1c,4)
                return moved
            env.override(0x4a9070,grow_and_change)
        return {'actor':actor,'entity':entity,'attacker':attacker,'record':record}
    return setup


def case(label, fn, word, **opts):
    return Case(label,fn,setup_actor(word,**opts),receiver=lambda t:t['actor'],
                arguments=(lambda t:t['attacker'],) if fn in (0x46a420,0x46a430,0x46a690) else ())


def cases(random_source):
    word=random_source.randrange(21,10000)
    yield case('set roll collision rectangle',0x46a000,word)
    for direction in (2,3,0):
        for flags in (0,2):
            for x in (-500.0,100.75,500.0):
                yield case(f'rollback begin d{direction} flags{flags} x{x}',0x46a040,word,
                           direction=direction,flags=flags,x=x)
    for direction in (2,3):
        yield case(f'rollback animation switch d{direction}',0x46a040,word,direction=direction,
                   flags=0xabcdeff0,animation=True)
        yield case(f'low hit animation switch d{direction}',0x46a5b0,word,direction=direction,
                   animation=True)
    for rand in (0xffffffff,0x80000000,0x7fffffff,150):
        yield case(f'signed random high hit {rand:x}',0x46a430,word,weapon=1,animation=True,
                   randoms=(rand,1,2,3))
    for elapsed in (0,49,50,51,0xffffffff):
        yield case(f'rollback cooldown elapsed {elapsed}',0x46a040,word,now=100+elapsed)
    for enabled in (0,1):
        yield case(f'rollback sound enabled {enabled}',0x46a040,word,audio=True,audio_enabled=enabled)
    for direction in (2,3,0):
        for x in (-500.0,99.0,100.0,101.0,500.0):
            for elapsed in (49,50):
                yield case(f'rollback update d{direction} x{x} elapsed{elapsed}',0x46a1c0,word,
                           direction=direction,x=x,now=100+elapsed)
    yield case('callback changes expiry before second transition',0x46a1c0,word,
               direction=0,x=-500.0,now=149,callback_change=True)
    for name in (b'LS_ROLLFORWARD',b'LS_ROLLBACKWARD',b'OTHER',b'ls_rollforward'):
        yield case(f'roll hit-state {name!r}',0x46a280,word,state=name)
    for grow in ('down','up'):
        yield case(f'roll state table grow {grow}',0x46a280,word,grow=grow)
    for fn in (0x46a280,0x46a430):
        yield case(f'two state-table grows {fn:x}',fn,word,grow='down',mutate_index=True)
    yield case('forward wrapper delegates cooldown',0x46a420,word,now=120)
    for state in (b'LS_HITLOW',b'LS_HITHIGH',b'OTHER'):
        for weapon in (0,1,2,3,4,5,6,7,8,9,10,11,12,13,14):
            for rand in (49,50):
                yield case(f'hit {state!r} weapon{weapon} rand{rand}',0x46a430,word,
                           state=state,weapon=weapon,randoms=(rand,1,2,3,4,5))
    yield case('hit random high while cooldown still running',0x46a430,word,weapon=1,now=149,randoms=(50,0,1,2))
    for direction in (2,3):
        for elapsed in (0,49,50,51,0xffffffff):
            yield case(f'low hit d{direction} elapsed{elapsed}',0x46a5b0,word,
                       direction=direction,now=(100+elapsed)&0xffffffff)
    for rand in (0,1,2,3,4,0xffffffff,0xfffffffe,0xfffffffd,0x80000000):
        yield case(f'lift voice choice {rand:x}',0x46a610,word,randoms=(rand,))
    for saved in (0,1,0xffffffff):
        yield case(f'death restores saved rect flag {saved}',0x46a650,word,saved=saved)
    for attack_type in (0,0x20,0x21):
        for health in (-1,0,1,83):
            for damage in (0,17,-13):
                yield case(f'health type{attack_type} hp{health} damage{damage}',0x46a690,word,
                           attack_type=attack_type,health=health,damage=damage)
    yield Case('health null attacker',0x46a690,setup_actor(word),receiver=lambda t:t['actor'],arguments=(0,))

    # Distinct names and padding distinguish index subtraction, bounds and stride.
    for low in (-7,0,19):
        for stride in (4,12):
            for slot in range(3):
                for fn in (0x46a280,0x46a430):
                    names=(b'LS_ROLLFORWARD',b'OTHER',b'LS_HITLOW')
                    yield case(f'distinct state slots {fn:x} low{low} stride{stride} slot{slot}',
                               fn,word,table_low=low,table_stride=stride,
                               table_names=names,index=low+slot)
    # The original uses unsigned subtraction for both cooldown clocks.
    for fn in (0x46a040,0x46a1c0,0x46a5b0,0x46a430):
        for last,now,limit in ((0xfffffff0,0x21,49),(0xfffffff0,0x22,50),
                               (0xfffffff0,0x23,51),(0x80000000,0,0x80000000),
                               (100,99,0xffffffff),(100,100,0),(100,99,1)):
            yield case(f'wrapped clock {fn:x} {last:x} {now:x} {limit:x}',fn,word,
                       last=last,roll_last=last,now=now,cooldown=limit,roll_time=limit,
                       randoms=(50,1,2,3),direction=0)
    # Integer conversion truncates signed coordinates; comparisons use x87 flags.
    for x in (-1.75,-0.75,-0.0,0.75,1.75,-2147483648.0,2147483647.0,
              float('nan'),float('inf'),-float('inf')):
        for direction in (2,3):
            yield case(f'signed coordinate d{direction} x{x}',0x46a040,word,
                       x=x,direction=direction)
            yield case(f'update coordinate d{direction} x{x}',0x46a1c0,word,
                       x=x,direction=direction,target=-1)
    for health,damage in ((1,2),(1,0x80000000),(0x7fffffff,-1),
                          (0x7fffffff,0x7fffffff),(0x80000000,1)):
        yield case(f'health arithmetic {health:x} damage{damage:x}',0x46a690,word,
                   health=health,damage=damage)
    # Vary every copied word and the flip operands independently on unseen seeds.
    for i in range(24):
        values=tuple(random_source.getrandbits(32) for _ in range(23))
        for fn in (0x46a000,0x46a040,0x46a650):
            yield case(f'random distinct rectangle {fn:x} {i}',fn,word,
                       rectangle_words=values,direction=2 if i%2 else 3,
                       flags=2 if i%3 else 0,saved=i%2)

    for fn in (0x46a040,0x46a1c0):
        for direction in (0,2,3):
            for endpoint in ('left','right'):
                yield case(f'unordered endpoint {fn:x} d{direction} {endpoint}',fn,word,
                           direction=direction,x=100.75,**{endpoint:float('nan')})
