"""Original-backed Red Tail attack scenarios."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence


def scene(**o):

    def setup(e):
        b = e.object(1344, 'boss', fill=0)
        a = e.object(576, 'actor', fill=0)
        s = e.object(512, 'sprite', fill=0)
        m = e.object(64, 'machine', fill=0)
        p = e.object(512, 'player', fill=0)
        v = e.object(96, 'vtable', fill=0)
        log = e.object(1024, 'callback record', fill=0)
        e.put(b, v)
        e.put(b + 0xc, a, m)
        e.put(b + 0x128, s, s)
        e.put(s + 0x40, 72 | o.get('flip', 0))
        e.put(s + 0x4c, 137, 219)
        e.put(s + 0x64, 17)
        for i, k in enumerate((280, 296, 312)):
            e.put(s + k, 0x80000000 if o.get('sentinel') else 11 + 7 * i, 23 + i, 47 + 3 * i)
        e.put(b + 0x138, 31, 43, 59, 71)
        e.put(b + 0x184, o.get('state', 4))
        e.put(b + 0x18c, o.get('direction', 2))
        e.put(a + 0xcc, o.get('actor_state', 1))
        e.put(m + 0x1c, 79225)
        for k, x in ((56, 0.0), (64, -400.0), (72, 0.0), (80, 7.25), (88, -8.5), (96, 3.75), (104, o.get('x', 37000.25)), (112, 200.0 if o.get('upper', True) else 0.0), (120, 0.0), (128, o.get('left', 36000.0)), (152, o.get('right', 38000.0))):
            e.write(b + k, struct.pack('<d', x))
        e.put(0x52b354, 36000, 38000, 100, 400)
        e.put(0x537e88, p)
        e.put(p + 0x4c, 37123, 200 if o.get('player_upper', True) else 0)
        e.put(0x537210, o.get('tick', 10000))
        e.put(0x5430c4, 1)
        e.put(0x537680, 0)
        e.put(0x53c9ac, 0)
        e.put(0x532c0c, o.get('sound_enabled', 0))
        e.put(b + 0x4b0, o.get('last', 10000), o.get('wait', 0))
        e.put(b + 0x4e4, o.get('wind_used', 0))
        e.put(b + 0x4ec, o.get('shots', 0), o.get('target', 37000))
        e.put(b + 0x4f4, 37, -13, o.get('vx', -500), 23)
        e.put(b + 0x220, 101, 103, 107, 109)
        e.put(b + 0x4c0, 211, 223, 227, 229)
        e.put(b + 0x4d0, 307, 311, 313, 317)
        e.put(b + 0x404, 177)
        for k in (780, 828, 832, 1124, 1128, 1132, 1136, 1140, 1144):
            anim = e.object(32, f'animation {k:x}')
            f = e.object(52, f'frame {k:x}')
            entries = e.object(4, f'entries {k:x}')
            e.put(entries, f)
            e.put(anim + 12, entries, 1)
            e.put(f + 28, k + 3)
            e.put(b + k, anim)
        e.put(s + 0x190, 0)
        e.put(s + 0x16c, o.get('frame', 0))
        e.put(s + 0x19c, o.get('delay', 0))
        e.put(s + 0x1a4, o.get('finished', 0))
        for i in range(8):
            e.put(b + 0x47c + i * 4, 1792 + i * 19)
        e.put(b + 0x480, 0)
        if o.get('sound'):
            snd = e.object(32, 'sound', fill=0)
            voice = e.object(32, 'voice', fill=0)
            provider = e.object(128, 'provider', fill=0)
            e.put(snd + 16, voice)
            e.put(voice + 16, provider)
            for k in (1152, 1192, 1196):
                e.put(b + k, snd)

        def callback(e, c):
            i = e.get(log)
            e.put(log, i + 1)
            e.put(log + 4 + i * 32, c.receiver, len(c.arguments), c.arguments[0] if c.arguments else 0, e.get(b + 0x4ec), e.get(b + 0x4b8), e.get(b + 0x4bc), e.get(b + 0x18c), e.get(s + 0x40))
            if o.get('mutate'):
                e.put(0x537210, 4294967280)
                e.put(b + 0x4bc, 305419896)
            return 2309737967
        e.put(v + 0x44, e.stub('continuation', 'thiscall', 0, callback))
        e.put(v + 0x5c, e.stub('death', 'thiscall', 1, callback))
        # Use the registered game logic callbacks through the original resource lookup.
        if o.get('projectile'):
            world = e.object(64, 'world', fill=0)
            context = e.object(64, 'context', fill=0)
            manager = e.object(64, 'manager', fill=0)
            resources = e.object(64, 'resource map', fill=0)
            e.put(b + 0x130, world)
            e.put(world + 12, context)
            e.put(context + 0x8, manager)
            e.put(context + 0x14, resources)
            e.put(manager + 0xc, context)
            buckets = e.object(4, 'hash buckets', fill=0)
            e.put(resources + 0x14, buckets, 1)
            entry = e.object(16, 'knife entry', fill=0)
            entry2 = e.object(16, 'bullet entry', fill=0)
            e.put(buckets, entry)
            knife_data = e.object(32, 'knife resource', fill=0)
            bullet_data = e.object(32, 'bullet resource', fill=0)
            e.put(entry, entry2, 0, 0x522d70, knife_data)
            e.put(entry2, 0, 0, 0x522d60, bullet_data)
            e.put(knife_data + 16, 0x410640)
            e.put(bullet_data + 16, 0x410700)
            nodes = e.object(48, 'free list nodes', fill=0)
            e.put(nodes, nodes + 16)
            e.put(nodes + 16, nodes + 32)
            e.put(manager + 0x20, nodes)

            def resource_map(items):
                owner = e.object(64, 'resource owner', fill=0)
                buckets = e.object(4, 'resource buckets', fill=0)
                head = 0
                for key, value in items:
                    text = e.object(len(key) + 1, 'resource key', data=key.encode() + b'\x00')
                    node = e.object(16, 'resource node', words=[head, 0, text, value])
                    head = node
                e.put(buckets, head)
                e.put(owner + 20, buckets, 1)
                return owner
            picture = e.object(48, 'projectile picture', fill=0)
            pictures = e.object(4, 'pictures', words=[picture])
            group = e.object(112, 'image group', fill=0)
            e.put(picture + 0x18, 7, 11, 31, 39)
            e.put(group + 0x14, pictures)
            e.put(group + 0x64, 0, 0)
            images = resource_map([] if o.get('sentinel') else [('GAME_BULLETS', group), ('LEVEL_REDTAILKNIFE', group), ('LEVEL_REDTAILBULLET', group)])
            animations = resource_map([])
            collision = e.object(128, 'collision', fill=0)
            e.put(collision + 100, 64, 48)
            e.put(context + 0x10, images)
            e.put(context + 0x24, collision)
            e.put(context + 0x2c, animations)
            e.put(0x53724c, 1)
            e.put(0x540e00, 1)
        e.override(0x4a3050, sequence(*o.get('randoms', (0,) * 16)))
        return {'boss': b}
    return setup


def case(label, f, **o):
    args = o.pop('args', ())
    return Case(label, f, scene(**o), receiver=lambda t: t['boss'], arguments=args)


def cases(random_source):
    # Deterministic branch matrix; randomized inputs change values without removing coverage.
    for f in (0x480aa0, 0x480e50, 0x480fd0, 0x481270, 0x4815b0):
        for pu, u in ((False, False), (False, True), (True, False), (True, True)):
            for st in (0, 4):
                for d, flip in ((2, 0), (2, 2), (3, 0), (3, 2)):
                    yield case(f'{f:x} predicates {pu} {u} {st} {d} {flip}', f, player_upper=pu, upper=u, state=st, direction=d, flip=flip)
    for st in (0, 1, 2, 3, 4, 5, 0xffffffff):
        for roll in (0, 19, 20, 39, 40, 69, 70, 79, 80, 89, 90, 100):
            yield case(f'select {st} roll {roll}', 0x480860, state=st, upper=False, randoms=(roll,) + (0,) * 15)
    for d in (2, 3):
        for flip in (0, 2):
            for sentinel in (False, True):
                yield case(f'select facing {d} {flip} {sentinel}', 0x480860, state=5, direction=d, flip=flip, sentinel=sentinel)
    for f in (0x480aa0, 0x480fd0, 0x481270, 0x4815b0):
        for roll in (0, 24, 25, 100, 0x7fffffff, 0xffffffff):
            yield case(f'{f:x} signed rand {roll}', f, player_upper=True, upper=f != 0x4815b0, randoms=(roll, roll, roll) + (0,) * 13, sound=True, sound_enabled=1)
    for f in (0x480c40, 0x480f20, 0x481400, 0x481720):
        for end, delay in ((0, 0), (1, 0), (1, 2)):
            if f == 0x480c40 and end and (not delay):
                continue
            for flip in (0, 2):
                yield case(f'{f:x} end {end} delay {delay} flip {flip}', f, finished=end, delay=delay, flip=flip, frame=402 if f == 0x480f20 else 0, mutate=True)
    for d in (0, 2, 3):
        for x, t, l, r in ((36999.75, 37000, 36000.0, 38000.0), (37000.0, 37000, 36000.0, 38000.0), (37001.25, 37000, 36000.0, 38000.0), (36000.0, 35000, 36000.0, 38000.0), (38000.0, 39000, 36000.0, 38000.0)):
            for flip in (0, 2):
                yield case(f'slide update {d} {x} {flip}', 0x481180, direction=d, x=x, target=t, left=l, right=r, frame=302, flip=flip)
    for f in (0x481790, 0x4817c0, 0x4817e0):
        for u in (False, True):
            for pu in (False, True):
                yield case(f'{f:x} peer {u} {pu}', f, upper=u, player_upper=pu, x=35000.0, args=(3,) if f == 0x4817e0 else ())
    for arg in (0, 1, 2, 3, 4, 5, 6, 7, 0xffffffff):
        yield case(f'command {arg}', 0x481810, args=(arg,), upper=False)
    for elapsed, wait in ((0, 1), (1, 1), (0xffffffff, 0xffffffff), (0, 0xffffffff)):
        yield case(f'cooldown {elapsed} {wait}', 0x480860, tick=10000 + elapsed & 0xffffffff, wait=wait, state=5)
    for used in (1, 0xffffffff):
        yield case(f'wind used {used}', 0x4815b0, wind_used=used, wait=1)
    for sentinel in (False, True):
        yield case(f'wind sentinel {sentinel}', 0x4815b0, upper=False, sentinel=sentinel)
    for i in range(12):
        yield case(f'random payload {i}', 0x480e50, state=4, tick=random_source.getrandbits(32), randoms=(random_source.getrandbits(32),), upper=True)
    for f in (0x480c40, 0x481400):
        for vx in (-500, 0, 500):
            for flip in (0,):
                for sentinel in (False, True):
                    yield case(f'{f:x} projectile {vx} {flip} {sentinel}', f, projectile=True, finished=1, vx=vx, frame=209 if f == 0x481400 else 0, projectile_flip=flip, sentinel=sentinel, sound=True, sound_enabled=1)
    for f in (0x480c40, 0x481400):
        for enabled in (0, 1):
            yield case(f'{f:x} no sound handle {enabled}', f, projectile=True, finished=1, vx=500, frame=209 if f == 0x481400 else 0, sound=False, sound_enabled=enabled)
    yield case('bullet already published at firing frame', 0x481400, frame=209, shots=1, finished=1)
    yield case('slide update ordinary frame', 0x481180, frame=0, finished=1)
    yield case('kick update ordinary frame', 0x480f20, frame=0, finished=1)
