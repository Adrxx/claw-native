"""Original-backed tentacle state cases with deterministic branch coverage."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns


def setup_case(options, salt):
    def setup(env):
        s = env.object(0x480, 'tentacle', fill=0)
        obj = env.object(0x160, 'placed object', fill=0)
        state = env.object(0x30, 'tentacle state', fill=0)
        sprite = env.object(0x1c0, 'tentacle sprite', fill=0)
        boss = env.object(0x4c0, 'aquatis', fill=0)
        player = env.object(0x1c0, 'player', fill=0)
        ps = env.object(0x30, 'player state', fill=0)
        logic = env.object(0x140, 'player logic', fill=0)
        inp = env.object(0x20, 'input', fill=0)
        table = env.object(0x80, 'player frame table', fill=0)
        frames = env.object(0x730, 'player frames', fill=0)
        resources = []
        for i in range(5):
            frame = env.object(0x34, 'animation frame', fill=0)
            env.put(frame + 0x1c, 13 + i)
            ptr = env.object(4, 'frame pointers', words=[frame])
            resource = env.object(0x18, 'animation resource', fill=0)
            env.put(resource + 0xc, ptr, 1)
            resources.append(resource)
        scene = env.object(0x40, 'player scene', fill=0)
        manager = env.object(0x30, 'player animation manager', fill=0)
        env.put(scene + 0x2c, manager)
        env.put(manager + 0x18, 1)  # empty MFC string map at manager+0x10
        env.put(player + 0xc, scene)
        env.put(player + 0x6c, ps)
        env.put(ps + 0x14, logic)
        env.put(ps + 0x1c, options.get('pstate', 0x1390))
        env.put(logic, options.get('facing', 1))
        env.put(player + 0x4c, options.get('px', 100), 123)
        env.put(player + 0x10c, options.get('health', 100))
        env.put(player + 0x16c, 0x313, table, 0x43434343)
        env.put(table + 0x14, frames)
        env.put(table + 0x64, options.get('lower', 0), options.get('upper', 600))
        env.put(frames + 0x708, 0x23232323 ^ salt, 0x45454545 ^ salt, 0x67676767 ^ salt)
        if options.get('table_null'):
            env.put(player + 0x170, 0)
        for off in (0x118, 0x128, 0x138):
            env.put(player + off, -13, -17, 23, 29)
            env.put(sprite + off, options.get('sentinel', -31), -37, 43, 47)
        env.put(sprite + 8, 0xa18352f7 ^ salt)
        env.put(sprite + 0x40, options.get('flags', 0xa5b6c780))
        env.put(sprite + 0x16c, options.get('frame', 0x12d))
        env.put(sprite + 0x18c, sprite)
        env.put(sprite + 0x190, 0)
        env.put(sprite + 0x19c, options.get('remaining', 0))
        env.put(sprite + 0x1a4, options.get('complete', 0))
        env.put(s + 0xc, obj, state)
        env.put(s + 0x12c, sprite)
        env.put(s + 0x18, 0x98764321, 0x11223344)
        env.put(s + 0x24, 0x76655443 ^ salt)
        env.put(state + 0x1c, 0x55443322 ^ salt)
        env.put(s + 0x134, 0x91827364 ^ salt)
        env.put(s + 0x138, options.get('edge', -67), -71, 79, 83)
        env.put(s + 0x184, options.get('mode', 0))
        env.write(s + 0x68, struct.pack('<dd', options.get('x', 100.25), options.get('y', -200.75)))
        env.put(s + 0x210, options.get('edge', -101), -103, 107, 109)
        env.put(s + 0x220, -113, -127, 131, 137)
        for off, resource in zip((0x374, 0x404, 0x408, 0x40c, 0x410), resources):
            env.put(s + off, resource)
        for off, value in {
            '0x414': 900, '0x418': 101, '0x41c': 900, '0x420': 101,
            '0x42c': 900, '0x430': 101, '0x434': 900, '0x438': 3000,
            '0x43c': 900, '0x440': 100, '0x444': 0, '0x44c': 0, '0x450': 0,
            '0x458': 1,
        }.items():
            env.put(s + int(off, 0), options.get(off, value))
        env.put(obj + 0x4c, 241)
        env.put(obj + 0x64, 9)
        env.put(obj + 0x124, 263)
        env.put(boss + 0xc, 0x13579bdf if options.get('boss') != 'invalid' else 0x13579bde)
        env.put(boss + 0x4b4, options.get('frenzy', 0), options.get('alive', 1))
        env.put(0x5349dc, 0x13579bdf)
        env.put(0x534874, 0 if options.get('boss') == 'null' else boss)
        env.put(0x537e88, 0 if options.get('player_null') else player)
        env.put(0x537204, 0 if options.get('input_null') else inp)
        env.put(inp + 4, options.get('input', 0))
        env.put(inp + 0xc, 0xf1234567)
        env.put(0x537210, options.get('now', 1000))
        env.put(0x5430c4, 17)
        env.put(0x534eac, options.get('powerup', 0))
        env.put(0x53ca2c, options.get('grabbed', 7))
        env.put(0x532c0c, options.get('sound', 0))
        env.put(0x532c10, 0x23456789)
        env.put(0x537668 + 0x18, 0)
        env.put(0x534ea8, 311)
        app = env.object(0x60, 'application', fill=0)
        appstate = env.object(0x800, 'application state', fill=0)
        av = env.object(0x20, 'application state methods', fill=0)
        env.put(av + 0x10, env.stub('state type', 'thiscall', 0, returns(1)))
        env.put(appstate, av)
        env.put(app + 0x2c, appstate)
        env.put(0x5371fc, app)
        sound = env.object(0x20, 'sound wrapper', fill=0)
        snd = env.object(0x40, 'sound', fill=0)
        engine = env.object(0x80, 'sound engine', fill=0)
        env.put(sound + 0x10, snd)
        env.put(snd + 0x10, engine)
        if options.get('sound_pointer'):
            env.put(s + 0x444, sound)
        audit = env.object(0x100, 'callback observations', fill=0)
        vt = env.object(0x60, 'tentacle methods', fill=0)
        def callback(e, call):
            e.put(audit, e.get(audit) + 1, call.receiver, e.get(0x53ca2c), e.get(ps + 0x1c), e.get(player + 0x10c))
            for i, off in enumerate((0x138, 0x140, 0x44c, 0x450, 0x430, 0x42c, 0x458)):
                e.put(audit + 0x20 + i * 4, e.get(s + off))
            e.put(audit + 0x50, e.get(obj + 0x138), e.get(obj + 0x140), e.get(sprite + 0x40))
            if options.get('callback_change'):
                e.put(0x537210, 1029)
                e.put(sprite + 0x16c, 0x12f)
            return 0xdeadbeef
        env.put(vt + 0x48, env.stub('next tentacle state', 'thiscall', 0, callback))
        env.put(vt + 0x58, env.stub('tentacle attack', 'thiscall', 0, callback))
        env.put(s, vt)
        if options.get('active_animation'):
            env.put(sprite + 0x190, resources[0])
            env.put(sprite + 0x194, env.get(env.get(resources[0] + 0xc)))
            env.put(sprite + 0x19c, 100)
            env.put(sprite + 0x1a0, 1)
            env.put(sprite + 0x1a8, 47, 53, 0x3f800000)
        if options.get('active_sound') or options.get('release_sound'):
            env.put(engine + 0x78, 1)
            env.put(0x532c0c, 1)
            env.put(0x532c10, 0)
            voice = env.object(0x38, 'active sound voice', fill=0)
            interface = env.object(4, 'sound interface')
            methods = env.object(0x48, 'sound methods', fill=0)
            env.put(interface, methods)
            env.put(voice + 0xc, interface, engine, 0xabc0, 22050)
            env.put(snd + 0x30, voice + 4, voice + 4)
            env.put(voice + 0x30, 1)
            env.put(s + 0x444, sound)
            def audio(e, call):
                n = e.get(audit + 0x70)
                e.put(audit + 0x70, n + 1)
                e.put(audit + 0x80 + n * 12, e.get(0x53ca2c), e.get(s + 0x134), call.arguments[-1])
                return 0
            def status(e, call):
                e.put(call.arguments[1], 0)
                return 0
            env.put(methods + 0x24, env.stub('sound status', 'stdcall', 2, status))
            for off, argc in ((0x3c, 2),(0x40, 2),(0x44, 2),(0x30, 4)):
                env.put(methods + off, env.stub('sound output', 'stdcall', argc, audio))
            if options.get('release_sound'):
                env.put(player + 0x18c, player)
                assoc = env.object(16, 'stand animation association', words=[0,0,0x5246d0,resources[0]])
                buckets = env.object(4, 'stand animation hash buckets', words=[assoc])
                env.put(manager + 0x14, buckets)
                env.put(env.get(env.get(resources[0] + 0xc)) + 0x2c, sound)
        if options.get('alias_identity'):
            # The animation resource header borrows the receiver's saved-token fields.
            # The original publishes +134 before reset reads this resource's frame list.
            second_frame = env.object(0x34, 'alternate animation frame', fill=0)
            env.put(second_frame + 0x1c, 79)
            other_list = env.object(4, 'alternate frame list', words=[second_frame])
            env.put(s + 0x12c, sprite)
            env.put(s + 0x128, 0, sprite, 0, other_list, 1)
            first_list = env.get(resources[0] + 0xc)
            env.put(sprite + 0x190, first_list)
            env.put(s + 0x40c, s + 0x128)
        env.override(0x4a3050, returns(options.get('rand', 19)))
        return s
    return setup


def cases(random_source):
    def make(label, address, **options):
        return Case(label, address, setup_case(options, random_source.getrandbits(24)), receiver=lambda s: s)
    for address in (0x492ec0, 0x493200, 0x493550):
        for boss in ('null', 'invalid'):
            yield make(f'{address:x} boss {boss}', address, boss=boss)
    for mode in (0, 1, 2, 3, 4, 5, -1):
        for x in (99.5, 100.0, 100.5):
            for elapsed in (100, 101):
                yield make(f'idle mode {mode} x{x} dt{elapsed}', 0x492ec0, mode=mode, x=x, **{'0x420':elapsed})
    for alive, frenzy in ((0,0), (0,1), (1,1)):
        yield make(f'idle transitions {alive}/{frenzy}', 0x492ec0, alive=alive, frenzy=frenzy)
    for rand in (74, 75, 100):
        yield make(f'idle attack selection {rand}', 0x492ec0, mode=3, rand=rand, grabbed=0, **{'0x420':100})
    yield make('idle unordered x', 0x492ec0, mode=3, x=float('nan'))
    for address in (0x493030, 0x493200):
        for frame in (0x12c,0x12d):
            for flags in (0xa5b6c780,0xa5b6c782):
                for complete, remaining in ((0,0),(1,0),(1,5)):
                    for frenzy in ((0,1) if address == 0x493200 else (0,)):
                        yield make(f'{address:x} rect {frame}/{flags:x}/{complete}/{remaining}/{frenzy}', address, frame=frame, flags=flags, complete=complete, remaining=remaining, frenzy=frenzy)
        yield make(f'{address:x} wrapping rect', address, complete=1, flags=2, edge=0x80000000, sentinel=0x80000000)
    for flags in (0,2):
        yield make(f'frenzy sentinel {flags}', 0x493200, complete=1, flags=flags, sentinel=0x80000000)
    yield make('frenzy waits before timer', 0x493200, **{'0x440':101})
    yield make('frenzy unsigned wrap timer', 0x493200, now=3, **{'0x43c':0xfffffff0,'0x440':19})
    for alive in (0,1):
        for frenzy in (0,1):
            for splash in (0,1):
                for delay in (100,101):
                    yield make(f'dead {alive}/{frenzy}/{splash}/{delay}', 0x493550, alive=alive, frenzy=frenzy, **{'0x458':splash,'0x418':delay})
    for pointer, enabled in ((0,0),(1,0),(1,1)):
        yield make(f'respawn sound {pointer}/{enabled}', 0x493600, sound_pointer=pointer, sound=enabled)
    for boss in ('null','valid'):
        for complete, remaining in ((0,0),(1,0),(1,5)):
            yield make(f'respawn update {boss}/{complete}/{remaining}', 0x493680, boss=boss, complete=complete, remaining=remaining)
    for facing in (0,1):
        yield make(f'start grab facing {facing}', 0x493830, facing=facing)
    yield make('start grab without player', 0x493830, player_null=True)
    for complete, remaining in ((0,0),(1,7),(1,0)):
        for x,y in ((100.25,-200.75),(-0.5,0.5),(-2147483600.25,2147483600.75)):
            yield make(f'grab frame {complete}/{remaining}/{x}/{y}', 0x493890, complete=complete, remaining=remaining, x=x, y=y, facing=0)
    yield make('squeeze entry', 0x493920)
    yield make('squeeze no input', 0x4939a0, input_null=True)
    for pstate in (0x1390,0x18):
        for counter in (8,9,10,-1,0x7fffffff):
            for input_word in (0,1,0xf000000,0xf000):
                yield make(f'squeeze release {pstate:x}/{counter}/{input_word:x}',0x4939a0,pstate=pstate,input=input_word,**{'0x450':counter})
    for duration in (99,100,101,0xffffffff):
        yield make(f'squeeze duration {duration}',0x4939a0,**{'0x438':duration})
    for frame in (0x12d,0x12e,0x12f,0x130,0x131):
        for lower,upper,null in ((0,600,False),(451,600,False),(0,449,False),(450,450,False),(0,600,True),(-1,0x7fffffff,False)):
            yield make(f'squeeze frame {frame:x} bounds {lower}/{upper}/{null}',0x4939a0,frame=frame,lower=lower,upper=upper,table_null=null)
    for health in (0,1,2,0x80000000):
        for count in (18,19,20,-1):
            yield make(f'pulse health {health} count {count}',0x4939a0,health=health,**{'0x430':100,'0x44c':count})
    for health in (1,2):
        yield make(f'invulnerable pulse {health}',0x4939a0,health=health,powerup=0x26bd,**{'0x430':100})
    yield make('death callback changes reloaded clock and frame',0x4939a0,health=1,callback_change=True,**{'0x430':100})
    for state in (0x18,0x1390):
        yield make(f'direct release state {state:x}',0x493be0,pstate=state)
    yield make('direct release no player',0x493be0,player_null=True)

    for address in (0x492ec0,0x493030,0x493200,0x493550,0x493680,0x493890,0x4939a0):
        yield make(f'{address:x} active animation tick',address,active_animation=True)
    yield make('respawn actual audio callbacks',0x493600,active_sound=True)
    yield make('respawn resource aliases saved animation identity',0x493600,alias_identity=True)
    yield make('squeeze clears dirty counters',0x493920,**{'0x450':73,'0x44c':91})
    for health,count in ((1,0),(100,19)):
        yield make(f'squeeze release audio observes grab publication {health}/{count}',0x4939a0,release_sound=True,health=health,**{'0x430':100,'0x44c':count})
