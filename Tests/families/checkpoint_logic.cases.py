"""Original-backed checkpoint, publication, cache and calendar cases."""
import struct
from clawparity.cases import Case


def calendar(env, mutate=None, date=(2024, 2, 4, 29, 12, 34, 56, 789), malloc_tm=False):
    tls = env.object(0x74, 'CRT thread', fill=0)
    tm = env.object(0x24, 'calendar tm', fill=0)
    env.put(tls + 0x40, 0 if malloc_tm else tm)
    env.put(0x5410b8, 1)
    env.put(0x531430, 0, 0, 0)
    env.put(0x540b68, 0)
    packed = struct.pack('<8H', *date)
    env.write(0x540b70, packed)
    def clock(e, c):
        e.write(c.arguments[0], packed)
        if mutate:
            mutate(e, c)
        return 0
    env.override(0x546a34, clock)
    env.override(0x5469b4, clock)
    def zone(e, c):
        e.write(c.arguments[0], bytes(172))
        return 0
    env.override(0x546a3c, zone)
    env.override(0x546a7c, lambda e, c: tls)
    env.override(0x546df0, lambda e, c: 12345 + e.calls_so_far(0x546df0) * 17)


def cache(env, words=None):
    a = env.object(0x2644, 'checkpoint cache', fill=0xA6)
    if words:
        env.put(a, *words)
    return a


def world(env, state=0, sprite=True, finished=0, countdown=0, callback=0x4232c0,
          type_value=3, string_length=0, cheat=0, flag=0, level=4, inhibit=0,
          live=True, live_state=True, cached=True, mutate=None):
    actor = env.object(0x1c0, 'checkpoint actor', fill=0x53)
    logic = env.object(0x20, 'checkpoint logic', fill=0)
    parent = env.object(0x40, 'resource parent', fill=0)
    maps = env.object(0x60, 'empty lookup maps', fill=0)
    # MFC CMapStringToPtr: null bucket storage, positive bucket count.
    env.put(maps + 0x18, 17)
    env.put(maps + 0x48, 17)
    env.put(parent + 0x14, maps)
    env.put(parent + 0x2c, maps + 0x30)
    env.put(actor + 0xc, parent)
    env.put(actor + 8, 0x82304020)
    env.put(actor + 0x4c, 127, 219)
    env.put(actor + 0x6c, logic)
    env.put(logic + 0x10, callback)
    env.put(logic + 0x1c, state)
    spr = env.object(0x28, 'sprite', fill=0x31)
    env.put(spr + 0x18, 0xfffffff1, 7, 81, 123)
    env.put(actor + 0x174, spr if sprite else 0)
    env.put(actor + 0x190, 0)
    env.put(actor + 0x19c, countdown)
    env.put(actor + 0x1a4, finished)
    app = env.object(0xc4, 'application', fill=0)
    player = env.object(0x300, 'player', fill=0x42)
    env.put(player + 4, app)
    env.put(player + 0x14, level)
    env.put(player + 0x164, 1001, flag)
    env.put(player + 0x258, inhibit)
    vt = env.object(0x14, 'player vtable', fill=0)
    log = env.object(0x20, 'type callback observations', fill=0)
    def type_call(e, c):
        e.put(log, c.receiver, e.get(actor + 8), e.get(logic + 0x1c), e.get(0x53c9f8))
        if mutate:
            mutate(e, dict(actor=actor, logic=logic, app=app, player=player))
        return type_value
    env.put(vt + 0x10, env.stub('player type', 'thiscall', 0, type_call))
    env.put(player, vt)
    cheats = env.object(0x12c, 'cheat configuration', fill=0)
    env.put(cheats + 0x128, cheat)
    text = env.object(16, 'CString backing', fill=0)
    env.put(text, string_length)
    save = env.object(0x44, 'save owner', fill=0)
    env.put(save + 0x1c, text + 8)
    ca = cache(env)
    env.put(app + 0x2c, player)
    env.put(app + 0x48, cheats)
    env.put(app + 0x60, save, ca if cached else 0)
    env.put(app + 0xc0, text + 8)
    live_actor = env.object(0x110, 'live actor', fill=0)
    live_logic = env.object(0x20, 'live actor logic', fill=0)
    stats = env.object(0x124, 'live statistics', fill=0x27)
    env.put(live_actor + 0x4c, 321, 654)
    env.put(live_actor + 0x6c, live_logic)
    env.put(live_actor + 0x10c, 91)
    env.put(live_logic + 0x14, stats if live_state else 0)
    env.put(stats + 0x70, 13, 17, 23, 29)
    env.put(stats + 0x88, *range(1, 11))
    env.put(stats + 0xb0, *range(31, 41))
    env.put(0x5371fc, app)
    env.put(0x537e88, live_actor if live else 0)
    env.put(0x537210, 47)
    env.put(0x53c9f8, 0xfffffff0)
    env.put(0x52c6e8, 0x123)
    env.put(0x5430c4, 9)
    env.put(0x536f00, 0)
    env.put(0x534cc8, 41)
    env.put(0x534cf0, 43, 47, 53, 59)
    env.put(0x534d08, *range(11, 21))
    env.put(0x534d30, *range(61, 71))
    return dict(actor=actor, logic=logic, app=app, player=player, cache=ca, stats=stats)


def cases(random_source):
    yield Case('type constant', 0x40af90)
    for fn in (0x422ef0, 0x423060):
        for st, sp, fin, count in ((0,False,0,0),(0,True,0,0),(1,True,0,0),(5,True,0,0),
                                  (6,True,0,0),(6,True,1,2),(6,True,1,0),(0xffffffff,True,0,0)):
            def setup(e, st=st, sp=sp, fin=fin, count=count):
                return world(e,state=st,sprite=sp,finished=fin,countdown=count)
            yield Case(f'tick {fn:x} state {st} sprite {sp} finished {fin} countdown {count}', fn, setup,
                       arguments=(lambda t:t['actor'],))
    for fn in (0x423060,0x4232c0,0x4232e0):
        def resumed(e):
            t=world(e); e.put(0x536f00, 7); return t
        yield Case(f'resumed {fn:x}',fn,resumed,arguments=(lambda t:t['actor'],))
    yield Case('ordinary activation',0x422ff0,world,arguments=(lambda t:t['actor'],))
    for opts in ({'type_value':2},{'string_length':5},{'callback':0x422ef0},{'cheat':1},
                 {'inhibit':1},{'callback':0x4232c0},{'callback':0x4232e0}):
        def activate(e, opts=opts):
            t=world(e,**opts); calendar(e); return t
        yield Case(f'super activation {opts}',0x4231a0,activate,arguments=(lambda t:t['actor'],))
    def replace_logic(e,t):
        l=e.object(0x20,'replacement logic', fill=0); e.put(l+0x10,0x4232e0); e.put(t['actor']+0x6c,l)
    def replacement(e):
        t=world(e,callback=0x422ef0,mutate=replace_logic);calendar(e);return t
    yield Case('type callback replaces logic before callback identity reload',0x4231a0,replacement,arguments=(lambda t:t['actor'],))
    publish_options=[((1,2,1),{}),((0,2,2),{}),((0,0,9),{}),((-1,-2,1),{'flag':1}),
        ((1,2,1),{'inhibit':1}),((1,2,1),{'live':False}),((1,2,3),{}),
        ((1,2,1),{'flag':1}),((1,2,2),{'cheat':1}),((1,2,1),{'cached':False}),
        ((1,2,1),{'live_state':False}),((0,0,0),{'cached':False}),
        ((0,0,0),{'flag':1,'level':15})]
    for args,opts in publish_options:
        def setup(e,opts=opts):
            t=world(e,**opts);calendar(e);return t
        yield Case(f'publication {args} {opts}',0x46d620,setup,receiver=lambda t:t['player'],arguments=args)
    for active_timer in (0,1):
        def timer_setup(e,active_timer=active_timer):
            t=world(e);calendar(e);e.put(t['app']+0x30,active_timer);return t
        yield Case(f'super activation real timer mode {active_timer}',0x4231a0,timer_setup,arguments=(lambda t:t['actor'],))
    for flag in (0,1):
        def setup(e,flag=flag):
            t=world(e)
            def change(e,c): e.put(t['player']+0x168,flag);e.put(t['player']+0x14,7)
            calendar(e,change);return t
        yield Case(f'publication clock changes flags and level {flag}',0x46d620,setup,receiver=lambda t:t['player'],arguments=(1,2,1))
    for lev in (-2147483648,-1,0,1,14,15,2147483647):
        for kind in (0,1,2,3,4,0xffffffff):
            yield Case(f'lookup level {lev} kind {kind}',0x49ae60,lambda e:cache(e),receiver=lambda t:t,arguments=(lev,kind))
    def reset(e):
        a=cache(e)
        for kind,base in enumerate((0x2d4,0xd24,0x1774)):
            for lev in range(15): e.put(a+base+lev*0xb0,0xfffffff0|((lev+kind)&1))
        return a
    yield Case('reset mixed retained bits and nonzero records',0x49a720,reset,receiver=lambda t:t)
    for lev,kind,null,alias in [(-1,1,False,0),(15,1,False,0),(0,1,True,0),(0,0,False,0),
                               (0,4,False,0),(0,1,False,0),(7,2,False,0),(14,3,False,0),
                               (1,1,False,-4),(1,2,False,4),(1,3,False,1)]:
        words=[random_source.getrandbits(32) for _ in range(44)]
        def setup(e,lev=lev,kind=kind,null=null,alias=alias,words=words):
            a=cache(e); p=e.object(0xb0,'checkpoint input',words=words)
            if alias:
                p=a+(0x2d4,0xd24,0x1774)[kind-1]+lev*0xb0+(0 if alias==1 else alias)
                e.put(p,*words)
            return a,0 if null else p
        yield Case(f'copy checkpoint {lev} {kind} null {null} alias {alias}',0x49a860,setup,
                   receiver=lambda t:t[0],arguments=(lev,lambda t:t[1],kind))
    for lev,null,old,new,ot,nt,alias in [(-1,False,0,1,0,0,0),(15,False,0,1,0,0,0),(0,True,0,1,0,0,0),
         (0,False,0xffffffff,1,2,1,0),(14,False,1,0xffffffff,2,3,0),(7,False,9,9,10,11,0),
         (7,False,9,9,11,10,0),(7,False,9,9,10,10,0),(1,False,0,1,5,2,-4),(1,False,0,1,5,2,4)]:
        words=[random_source.getrandbits(32) for _ in range(17)]
        def setup(e,lev=lev,null=null,old=old,new=new,ot=ot,nt=nt,alias=alias,words=words):
            a=cache(e); dst=a+0x21c4+max(0,min(14,lev))*0x44
            p=dst+alias if alias else e.object(0x44,'score input', fill=0)
            e.put(p,*words);e.put(dst+4,old,ot);e.put(p+4,new,nt)
            return a,0 if null else p
        yield Case(f'best score {lev} null {null} score {old}/{new} time {ot}/{nt} alias {alias}',0x49a800,setup,
                   receiver=lambda t:t[0],arguments=(lev,lambda t:t[1]))
    def allocated_tm(e):
        calendar(e,malloc_tm=True)
        return e.object(0x44,'malloc-backed dated score',fill=0x67)
    yield Case('date initializes calendar tm through malloc',0x49aa40,allocated_tm,arguments=(lambda t:t,))
    def changing_timezone(e):
        calendar(e,date=(2024,3,5,1,0,30,0,0))
        tls=e.object(0x74,'changing timezone CRT thread',fill=0)
        tm=e.object(0x24,'changing timezone tm',fill=0)
        e.put(tls+0x40,tm)
        observed=e.object(0x20,'TLS date observations',fill=0)
        def lookup(e,c):
            n=e.calls_so_far(0x546a7c)
            e.put(observed+4*((n-1)%8),e.get(0x531430))
            e.put(0x531430,(n%3)*3600)
            return tls
        e.override(0x546a7c,lookup)
        return e.object(0x44,'varying-date score',fill=0x73)
    yield Case('date rereads three original localtime results',0x49aa40,changing_timezone,arguments=(lambda t:t,))
    yield Case('date null',0x49aa40,arguments=(0,))
    for date in ((2024,2,4,29,12,34,56,789),(2037,12,4,31,23,59,58,999)):
        def setup(e,date=date):
            calendar(e,date=date);return e.object(0x44,'dated score',fill=0x61)
        yield Case(f'date {date}',0x49aa40,setup,arguments=(lambda t:t,))
    for null_dest,null_counts,alias in ((True,False,0),(False,True,0),(False,False,0),(False,False,-4),(False,False,4)):
        words=[random_source.getrandbits(32) for _ in range(10)]
        weights=[random_source.getrandbits(32) for _ in range(10)]
        elapsed=random_source.getrandbits(32)
        def setup(e,nd=null_dest,nc=null_counts,alias=alias,words=words,weights=weights):
            calendar(e); d=e.object(0x80,'score backing',fill=0x39)
            p=d+0x1c+alias if alias else e.object(0x28,'counts', fill=0)
            e.put(p,*words);e.put(0x52d698,*weights)
            return (0 if nd else d,0 if nc else p)
        yield Case(f'score build null {null_dest}/{null_counts} alias {alias}',0x49a9d0,setup,
                   arguments=(lambda t:t[0],lambda t:t[1],elapsed))
