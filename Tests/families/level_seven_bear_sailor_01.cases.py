"""Independent original inputs for the Level 7 bear sailor surface."""
import struct
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.kernel import STACK_TOP


def putd(env, address, value):
    env.write(address, struct.pack('<d', value))


def map_at(env, base, entries=()):
    buckets = env.object(4, 'resource bucket')
    link = 0
    for name, value in entries:
        key = env.object(len(name) + 1, 'resource key', data=name.encode() + b'\0')
        link = env.object(16, 'resource node', words=[link, 0, key, value])
    env.put(buckets, link)
    env.put(base + 4, buckets, 1)


def setup_world(seed, **opts):
    def setup(env):
        bear = env.object(0x500, 'bear', fill=0)
        actor = env.object(0x300, 'bear actor', fill=0)
        logic = env.object(0x200, 'bear logic', fill=0)
        player = env.object(0x300, 'player', fill=0)
        plogic = env.object(0x200, 'player logic', fill=0)
        pcontrol = env.object(0x500, 'player control', fill=0)
        scene = env.object(0x80, 'scene', fill=0)
        sound = env.object(0x40, 'sound resources', fill=0)
        ani = env.object(0x40, 'animation resources', fill=0)
        hooks = env.object(0x40, 'logic resources', fill=0)
        collision = env.object(0x80, 'collision', fill=0)
        plane = env.object(0xa0, 'plane', fill=0)
        tiles = env.object(4, 'tile', words=[0xffffffff])
        rows = env.object(4, 'row', words=[0])
        env.put(collision + 0x5c, plane)
        env.put(collision + 0x64, 64, 64)
        env.put(plane + 0x20, tiles, rows)
        env.put(plane + 0x30, 4096, 4096)
        env.put(plane + 0x8c, 12, 12)
        env.put(scene + 0x14, hooks)
        env.put(scene + 0x24, collision, sound, ani)
        map_at(env, sound + 0x10)
        map_at(env, ani + 0x10)
        map_at(env, hooks + 0x10)
        env.put(actor + 0xc, scene)
        env.put(actor + 0x6c, logic)
        env.put(actor + 0x4c, 200, 300)
        env.put(actor + 0xcc, 7)
        env.put(logic + 0x14, pcontrol)
        env.put(logic + 0x1c, 2)
        env.put(player + 0xc, scene)
        env.put(player + 0x6c, plogic)
        env.put(player + 0x4c, 210, 300 + opts.get('dy', 0))
        env.put(player + 0x10c, opts.get('health', 20))
        env.put(plogic + 0x14, pcontrol)
        env.put(plogic + 0x1c, opts.get('player_state', 0x1390))
        inputs = env.object(0x20, 'input', fill=0)
        env.put(inputs + 4, opts.get('input', 0))
        env.put(0x537204, inputs)
        env.put(0x537e88, player)
        env.put(0x537210, opts.get('now', 1000))
        env.put(0x5430c4, opts.get('dt', 1))
        env.put(0x534eac, opts.get('cheat', 0))
        env.put(0x532c0c, opts.get('audio_enabled', 0))
        env.put(0x532c10, 77)
        env.put(0x544d18, 0)
        env.put(0x533470, 32)
        env.put(0x537668 + 0x18, 0)
        other = env.object(6, 'other state name', data=b'OTHER\0')
        names = env.object(16, 'state names', words=[other]*4)
        env.put(0x537698 + 8, 0, 3, names, names, 4, 0, 0)
        events = env.object(0x100, 'callback observations', fill=0)
        methods = env.object(0x100, 'bear vtable', fill=0)
        def callback(env, call):
            index = env.get(events)
            env.put(events, index + 1)
            env.put(events + 4 + index * 40, call.receiver, env.get(bear + 0x458), env.get(bear + 0x45c),
                    env.get(bear + 0x460), env.get(bear + 0x464), env.get(logic + 0x1c),
                    env.get(plogic + 0x1c), env.get(player + 0x10c), env.get(bear + 0x494), env.get(0x537210))
            if opts.get('callback_change'):
                env.put(0x537210, 0x80000001)
            return seed
        cb = env.stub('bear state publication', 'thiscall', 0, callback)
        for off in (0x44, 0x58):
            env.put(methods + off, cb)
        env.put(bear, methods)
        env.put(bear + 0xc, actor, logic)
        env.put(bear + 0x128, actor, actor, logic)
        env.put(bear + 0x178, actor, actor, logic)
        env.put(bear + 0x190, actor, actor)
        env.put(bear + 0x184, opts.get('mode', 7))
        env.put(bear + 0x18c, opts.get('direction', 0))
        env.put(actor + 0x40, opts.get('flipped', 0))
        env.put(actor + 0x38, opts.get('marker', 0))
        env.put(bear + 0x498, opts.get('seen', 0))
        env.put(bear + 0x450, opts.get('start', 100), opts.get('duration', 3000), opts.get('coolstart', 100), opts.get('coolduration', 5000), opts.get('hitstart', 100), opts.get('hitduration', 100))
        env.put(bear + 0x494, opts.get('escapes', 0))
        env.put(bear + 0x138, seed | 1, seed ^ 0xa531, seed ^ 0x8393, seed ^ 0xbcd9)
        for off in (0x118, 0x128, 0x138):
            env.put(actor + off, -19, -37, 29, 47)
        for off in (0x68, 0x70):
            putd(env, bear + off, opts.get('x' if off == 0x68 else 'y', 300.75))
        putd(env, bear + 0x28, 0.5)
        env.put(bear + 0x2fc, 32)
        env.put(bear + 0x300, 0)
        env.put(actor + 0x16c, opts.get('frame', 0))
        env.put(actor + 0x190, 0)
        env.put(bear + 0x134, seed ^ 0x231f)
        env.put(actor + 0x19c, opts.get('remaining', 0))
        env.put(actor + 0x1a4, opts.get('ended', 0))
        sound_actor = env.object(0x300, 'dialogue actor', fill=0)
        slogic = env.object(0x200, 'dialogue logic', fill=0)
        env.put(sound_actor + 0x6c, slogic)
        env.put(0x53c9ac, sound_actor)
        env.put(0x53c9a8, 0)
        env.put(0x53c9b0, actor)
        for i, off in enumerate(range(0x464, 0x494, 4)):
            env.put(bear + off, (seed + i * 89) & 0xffffffff)
        env.put(bear + 0x48c, 0, 0)
        env.put(bear + 0x464, opts.get('hitduration', 100))
        def random_value(env, call):
            vals = opts.get('rand', (seed % 100, 1, 97, 71))
            return vals[(env.calls_so_far(0x4a3050) - 1) % len(vals)]
        env.override(0x4a3050, random_value)
        def copyrect(env, call):
            env.write(call.arguments[0], env.read(call.arguments[1], 16))
            return 1
        env.override(0x546d58, copyrect)
        return dict(bear=bear, actor=actor, logic=logic, player=player, plogic=plogic, control=pcontrol, scene=scene, sound=sound, ani=ani, hooks=hooks, collision=collision, methods=methods, events=events, cb=cb)
    return setup


def case(label, function, seed, **opts):
    return Case(label, function, setup_world(seed, **opts), receiver=lambda t: t['bear'])


def cases(random_source):
    seeds = [random_source.randrange(1, 0x7fffffff) for _ in range(8)]
    for i, seed in enumerate(seeds):
        for direction in (0, 2, 3):
            for flipped in (0, 2):
                yield case(f'home geometry {i} {direction} {flipped}', 0x40a490, seed, direction=direction, flipped=flipped, seen=1)
        for dy in (-51, -50, -49, 0, 49, 50, 51):
            yield case(f'home sight {i} {dy}', 0x40a490, seed, dy=dy, rand=(69, i % 2, 97))
        for cheat in (0x26b7, 0):
            yield case(f'home marker {i} {cheat}', 0x40a490, seed, cheat=cheat, marker=-1)
        yield case(f'attack begin {i}', 0x40a610, seed)
        yield case(f'hug enter {i}', 0x40a740, seed)
        yield case(f'hug cleanup {i}', 0x40aa40, seed)
        yield case(f'lower audio choice {i}', 0x40ab20, seed, rand=(34,))
        yield case(f'upper audio choice {i}', 0x40ab20, seed, rand=(35,))
        yield case(f'idle callback {i}', 0x435130, seed, mode=i % 8)
    for i, (ended, remaining) in enumerate(((0,0),(1,1),(1,0))):
        for direction in (2,3):
            yield case(f'start hug {i} {direction}', 0x40a690, seeds[i], ended=ended, remaining=remaining, direction=direction)
    for frame in (0,0x12d,0x12e,0x12f,0x130,0x131):
        for hitduration in (899,900,901):
            yield case(f'hug frame {frame} timer {hitduration}', 0x40a7f0, seeds[0], frame=frame, hitduration=hitduration)
    for now, start, duration in ((0,0,0),(1000,100,900),(1000,100,901),(0x10,0xfffffff0,32),(0x10,0xfffffff0,33)):
        for escapes in (9,10,0x80000000):
            yield case(f'hug timeout {now} {start} {duration} {escapes}', 0x40a7f0, seeds[1], now=now,start=start,duration=duration,escapes=escapes,input=1)
    for state in (0x1390,0x18):
        for ended, remaining in ((0,0),(1,0),(1,1)):
            yield case(f'release {state} {ended} {remaining}', 0x40aa70, seeds[2], player_state=state, ended=ended, remaining=remaining)


def with_audio(seed, *, playing=0, enabled=0, status_change=False, **opts):
    def setup(env):
        t = setup_world(seed, audio_enabled=enabled, **opts)(env)
        record = env.object(0x20, 'sound record', fill=0)
        audio = env.object(0x40, 'sound body', fill=0)
        device = env.object(0x80, 'sound device', fill=0)
        interface = env.object(4, 'sound interface', fill=0)
        vtable = env.object(0x80, 'sound methods', fill=0)
        env.put(record + 0x10, audio)
        env.put(audio + 0xc, interface, device)
        env.put(interface, vtable)
        env.put(device + 0x78, 1)
        env.put(audio + 0x18, 22050)
        replacement = env.object(0x20, 'replacement sound record', fill=0)
        replacement_audio = env.object(0x40, 'replacement sound body', fill=0)
        env.write(replacement_audio, env.read(audio, 0x40))
        env.put(replacement + 0x10, replacement_audio)
        def status(env, call):
            if status_change:
                env.put(t['bear'] + 0x48c, replacement)
                env.put(0x537210, 0x80000001)
            env.put(call.arguments[1], playing)
            return 0
        env.put(vtable + 0x24, env.stub('GetStatus', 'stdcall', 2, status))
        def physical(env, call):
            n = env.get(t['events'] + 0xe0)
            env.put(t['events'] + 0xe0, n + 1)
            return 0
        for off, argc in ((0x30,4),(0x3c,2),(0x40,2),(0x44,2),(0x48,1)):
            env.put(vtable + off, env.stub(f'sound method {off}', 'stdcall', argc, physical))
        env.put(t['bear'] + 0x48c, record)
        # The one-shot path can safely observe an unavailable duplicate device.
        disabled = env.object(0x40, 'one shot unavailable', fill=0)
        unavailable = env.object(0x80, 'unavailable device', fill=0)
        oneshot = env.object(0x20, 'one shot record', fill=0)
        env.put(disabled + 0x10, unavailable)
        env.put(oneshot + 0x10, disabled)
        env.put(t['bear'] + 0x490, oneshot)
        return t
    return setup


def construct(seed, full=False, scale=1.0):
    def setup(env):
        t = setup_world(seed)(env)
        bear, actor = t['bear'], t['actor']
        for off in range(0x200,0x500,4):
            env.put(bear+off,(seed+off*17)&0xffffffff)
        env.put(actor + 0x108, 17)
        putd(env, 0x50e008, .001)
        for addr in (0x5262b0,0x5262b4,0x5262b8):
            env.write(addr, struct.pack('<f', scale))
        frame = env.object(0x30, 'animation step', fill=0)
        env.put(frame + 0x1c, seed)
        frame_list = env.object(4, 'animation steps', words=[frame])
        animation = env.object(0x20, 'animation', fill=0)
        env.put(animation + 0xc, frame_list, 1)
        keys = ['GAME_NULL']
        if full:
            keys += ['LEVEL_BEARSAILOR_' + name for name in ('ADVANCE','FASTADVANCE','HITHIGH','HITLOW','IDLE','JUMP','KILLFALL','LIFTED1','LIFTED2','STRIKE1','THROWN','HOME')]
        entries = []
        for i,name in enumerate(keys):
            step = env.object(0x30, 'distinct step',fill=0)
            env.put(step+0x1c,seed+i*13)
            steps = env.object(4,'distinct step list',words=[step])
            item = env.object(0x20,'distinct animation',fill=0)
            env.put(item+0xc,steps,1)
            entries.append((name,item))
        map_at(env,t['ani']+0x10,entries)
        if full:
            sound_entries = []
            for suffix in ('00380000','00380007','00380015','00380018','00380019',
                           '00380002','00380020','00380023','BEARGRAB','BEARHUG','00380024','00380006'):
                resource = env.object(0x20, 'distinct constructor sound', fill=0)
                env.put(resource + 4, seed ^ len(sound_entries))
                sound_entries.append(('LEVEL_BEARSAILOR_' + suffix, resource))
            map_at(env,t['sound']+0x10,sound_entries)
        env.put(0x52f01c, 0)
        table = env.object(512, 'ctype', fill=0)
        env.put(0x52ee10, table)
        return t
    return setup


def destructor(seed, flags, allocated=False):
    def setup(env):
        t = setup_world(seed)(env)
        env.put(t['bear'] + 0x2fc, 64 if allocated else 32)
        if allocated:
            storage = env.object(8, 'owned bitset')
            env.put(t['bear'] + 0x300, storage)
        for off in (0x1a4,0x1a8):
            string = env.object(16, 'reference counted string', words=[2,3,3,0])
            env.put(t['bear'] + off, string + 12)
        def decrement(env, call):
            p = call.arguments[0]
            n = env.get(p) - 1
            env.put(p, n)
            return n
        env.override(0x5469e8, decrement)
        return t
    return setup


_basic_cases = cases

def cases(random_source):
    yield from _basic_cases(random_source)
    for i in range(4):
        seed = random_source.randrange(1,0x7fffffff)
        for full in (False, True):
            yield Case(f'construct resources {i} {full}', 0x409920, construct(seed, full, (0.125,1.0,7.75,100.0)[i]), receiver=lambda t:t['bear'], arguments=(lambda t:t['actor'],))
        for flags in (0,1,2,3,0x80):
            yield Case(f'delete flags {i} {flags}', 0x409ee0, destructor(seed,flags,bool(i%2)), receiver=lambda t:t['bear'], arguments=(flags,))
        yield Case(f'destruct direct {i}', 0x409f70, destructor(seed,0,bool(i%2)), receiver=lambda t:t['bear'])
        for playing in (0,1):
            for enabled in (0,1):
                for f in (0x40a610,0x40a740,0x40aa40):
                    yield Case(f'audio path {f:x} {i} {playing} {enabled}', f, with_audio(seed,playing=playing,enabled=enabled), receiver=lambda t:t['bear'])
        for duration, health in ((899,20),(900,0),(900,1),(900,2),(901,1)):
            yield case(f'home attack gate {i} {duration} {health}',0x40a490, seed,mode=4,coolduration=duration,health=health)
        for player_state in (0x18,0x1390):
            for playing in (0,1):
                yield Case(f'hug stop sound {i} {player_state} {playing}',0x40a7f0,with_audio(seed,playing=playing,player_state=player_state,start=100,duration=900),receiver=lambda t:t['bear'])
        for frame in (0x12e,0x12f,0x130):
            for bounds in ((0,500),(451,500),(0,449),(450,450)):
                def mapped(env, seed=seed, frame=frame, bounds=bounds):
                    t = setup_world(seed,frame=frame,hitduration=901)(env)
                    images = env.object(0x80, 'player image set',fill=0)
                    entries = env.object(0x720,'image entries',fill=0)
                    env.put(entries + 0x708, seed, seed^0x12345, seed^0x67891)
                    env.put(images + 0x14,entries)
                    env.put(images + 0x64,*bounds)
                    env.put(t['player'] + 0x170,images)
                    return t
                yield Case(f'hug frame image {i} {frame} {bounds}',0x40a7f0,mapped,receiver=lambda t:t['bear'])

_previous_cases = cases

def cases(random_source):
    yield from _previous_cases(random_source)
    for health in (-1,0,1):
        for playing in (0,1):
            def lethal(env, health=health, playing=playing):
                t = with_audio(0x13379,playing=playing,health=health,hitduration=900)(env)
                app = env.object(0x60, 'application',fill=0)
                engine = env.object(0x800, 'application interface',fill=0)
                methods = env.object(0x20, 'application methods',fill=0)
                env.put(methods + 0x10, env.stub('single player mode','thiscall',0,lambda env,call:0))
                env.put(engine,methods)
                env.put(app + 0x2c,engine)
                env.put(0x5371fc,app)
                return t
            yield Case(f'lethal damage {health} {playing}',0x40a7f0,lethal,receiver=lambda t:t['bear'])


def dispatch_setup(seed, ident, lo=-2, hi=2, fallback=False, failure=False):
    def setup(env):
        t = setup_world(seed)(env)
        data = env.object((hi-lo+1)*4,'bear state table',words=[0 if fallback else t['cb']]*(hi-lo+1))
        handler = env.object(0x20,'error policy',fill=0)
        env.put(handler+0xc,4)
        zero = env.object(4,'default state',words=[t['cb']])
        env.put(0x534978+4,handler,lo,hi,data,zero,4,0,0)
        inherited = env.object(84,'base state table',words=[t['cb']]*21)
        env.put(0x537878+4,handler,-10,10,inherited,zero,4,0,0)
        sp = STACK_TOP-0x2000
        for off in range(-512,64,4):
            env.put(sp+off,(seed^off)&0xffffffff)
        env.put(sp,0x4dc946,ident)
        source = NativeSourceContext(72,1,0x7ff,0x5f3,
            seed,seed^0x1234,t['bear'],t['methods'],ident,seed^0x9876,t['bear'],sp,0x40a040,2,0xffffffff,0x472,0,0)
        if failure:
            env.override(0x4a9070,lambda env,call:0)
        t['source']=source
        return t
    return setup

_previous2_cases=cases

def cases(random_source):
    yield from _previous2_cases(random_source)
    for i in range(3):
        seed=random_source.randrange(1,0x7fffffff)
        for ident in (-2,0,2):
            for fallback in (False,True):
                yield Case(f'dispatch existing {i} {ident} {fallback}',0x40a040,dispatch_setup(seed,ident,fallback=fallback),receiver=lambda t:t['bear'],arguments=(ident,),source_context=lambda t:t['source'],source_return_pc=0x4dc946)
        for ident in (-5,5):
            yield Case(f'dispatch grow {i} {ident}',0x40a040,dispatch_setup(seed,ident),receiver=lambda t:t['bear'],arguments=(ident,),source_context=lambda t:t['source'],source_return_pc=0x4dc946)

_previous3_cases = cases

def cases(random_source):
    yield from _previous3_cases(random_source)
    for value in (0,1,69,70,99,100,0xffffffff,0x80000000):
        yield case(f'home greeting random threshold {value}',0x40a490,0x112233,rand=(value,1,97))
    for change in (False,True):
        yield case(f'release callback time reread {change}',0x40aa70,0x224466,callback_change=change,ended=1)


_existing_cases = cases

def cases(random_source):
    yield from _existing_cases(random_source)
    # Fixed geometry and thresholds guarantee branch coverage for every seed.
    for direction in (0, 2, 3):
        for coordinate in (-301.875, -0.5, 0.5, 300.875):
            yield case(f'completed alignment {direction} {coordinate}', 0x40a690,
                       random_source.randrange(1, 0x7fffffff), ended=1,
                       direction=direction, x=coordinate, y=-coordinate)
    for mask in (0, 1, 0x800, 0x1000, 0x100000, 0x1000000, 0x8000000, 0x10000000, 0x80000000):
        for escape in (8, 9, 0x7fffffff, 0xffffffff):
            yield case(f'escape mask {mask:x} count {escape:x}', 0x40a7f0,
                       random_source.randrange(1, 0x7fffffff), input=mask,
                       escapes=escape, hitduration=901)
    for now, start, interval in ((0x10, 0xfffffff0, 31), (0x10, 0xfffffff0, 32),
                                 (0x10, 0xfffffff0, 33), (0x80000000, 0, 0x80000001)):
        for cheat in (0, 0x26bd):
            yield case(f'damage wrapping {now:x} {interval:x} {cheat:x}', 0x40a7f0,
                       random_source.randrange(1, 0x7fffffff), now=now, start=now,
                       hitstart=start, hitduration=interval, cheat=cheat)
    for frame in (0x12e, 0x12f, 0x130):
        target = frame + 0x94
        for lo, hi in ((target, target), (target + 1, 500), (-1, target - 1)):
            def exact_bounds(env, frame=frame, lo=lo, hi=hi):
                t = setup_world(0x674523, frame=frame, hitduration=901)(env)
                images = env.object(0x80, 'exact image range', fill=0)
                entries = env.object(0x720, 'exact image entries', fill=0)
                env.put(entries + 0x708, 0x91a351, 0x82b462, 0x73c573)
                env.put(images + 0x14, entries)
                env.put(images + 0x64, lo, hi)
                env.put(t['player'] + 0x170, images)
                env.put(t['player'] + 0x16c, 0xabcdef01)
                env.put(t['player'] + 0x174, 0x12345678)
                return t
            yield Case(f'exact image bounds {frame:x} {lo} {hi}', 0x40a7f0,
                       exact_bounds, receiver=lambda t: t['bear'])
    for function in (0x40a740, 0x40aa40, 0x40a7f0):
        for playing in (0, 1):
            yield Case(f'status mutates resource {function:x} {playing}', function,
                       with_audio(0x31894, playing=playing, enabled=1, status_change=True,
                                  player_state=0x18), receiver=lambda t: t['bear'])
    for state in (0x18, 0x1390):
        yield case(f'hug exit callback publication {state:x}', 0x40a7f0,
                   0x13791, player_state=state, duration=900, callback_change=True)
    for value in (0, 34, 35, 99, 100, 134, 135, 0xffffffff, 0x80000000):
        yield case(f'lifted signed random {value:x}', 0x40ab20, 0x31791, rand=(value,))
    for value in (0, 1, 0xffffffff):
        yield case(f'greeting signed parity {value:x}', 0x40a490, 0x31891,
                   rand=(0, value, 97))


def animated_world(seed, function, ticks, remaining):
    def setup(env):
        t = setup_world(seed, dt=ticks, hitduration=901)(env)
        actor, bear = t['actor'], t['bear']
        steps = []
        for i in range(2):
            step = env.object(0x30, 'active animation step', fill=0)
            # No movement or audio. Advancing still publishes timer/frame state.
            env.put(step + 0xc, 9)
            env.put(step + 0x18, 17 + i, seed ^ (i + 0x135))
            steps.append(step)
        table = env.object(8, 'active animation steps', words=steps)
        animation = env.object(0x20, 'active animation', fill=0)
        env.put(animation + 0xc, table, 2)
        selected = env.object(0x20, 'selected hug animation', fill=0)
        env.put(selected + 0xc, table, 2)
        map_at(env, t['ani'] + 0x10,
               [('LEVEL_BEARSAILOR_STRIKE2', selected), ('LEVEL_BEARSAILOR_STRIKE3', selected)])
        env.put(actor + 0x18c, actor, animation, steps[0], 0, remaining, 1, 0,
                seed ^ 0x145, seed ^ 0x256, 0x3f800000)
        env.put(bear + 0x1c, seed ^ 0x367, seed ^ 0x478, seed ^ 0x589)
        # A single-node crit-bit state registry uses a self edge to its leaf.
        name = 'LS_STARTHUG' if function == 0x40a610 else 'LS_HUG'
        key = env.object(len(name) + 1, 'registered hug state name', data=name.encode() + b'\0')
        node = env.object(0x14, 'registered hug state', fill=0)
        env.put(node, node, node, 0, key, 0x1357)
        env.put(0x537668 + 0x18, node)
        return t
    return setup


_before_active_animation = cases

def cases(random_source):
    yield from _before_active_animation(random_source)
    for function in (0x40a610, 0x40a740, 0x40a690, 0x40a7f0, 0x40aa70):
        for ticks in (0, 1, 9, 31):
            for remaining in (5, 40):
                seed = random_source.randrange(1, 0x7fffffff)
                yield Case(f'active animation {function:x} ticks {ticks} remaining {remaining}',
                           function, animated_world(seed, function, ticks, remaining),
                           receiver=lambda t: t['bear'])
