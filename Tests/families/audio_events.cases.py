"""Original-backed audio routing, speech and DirectSound parameter cases."""
import math
from clawparity.cases import Case

DIRECT, NAME, SPEECH, SPEECH_NAME = 0x4208e0, 0x420910, 0x48c820, 0x48c8a0
TABLE, POOL, SPATIAL = 0x4b3b90, 0x4b45f0, 0x4c88e0


def graph(env, *, available=1, errors=(), busy_first=False, skip_first=False,
          drop_after=None, swap_after=None, seed=0):
    """Concrete original pool/voices; only physical COM methods are stand-ins."""
    manager = env.object(0x80, 'manager')
    replacement = env.object(0x80, 'replacement-manager')
    env.put(manager + 0x78, available)
    env.put(replacement + 0x78, 1)
    pool = env.object(0x38, 'pool')
    env.put(pool + 0x10, manager)
    env.put(pool + 0x18, 19531, 371, -2111)
    log = env.object(2048, 'physical-observations')
    env.put(log, 0)
    voices = [env.object(0x38, 'voice-0'), env.object(0x38, 'voice-1')]
    buffers = [env.object(4, 'buffer-0'), env.object(4, 'buffer-1')]
    alternate = env.object(4, 'replacement-buffer')

    def method(kind, which, status=0):
        def effect(env, call):
            n = env.get(log)
            row = log + 4 + n * 40
            env.put(row, kind, call.receiver, len(call.arguments), *call.arguments)
            env.put(row + 28, env.get(voices[which] + 0x14),
                    env.get(voices[which] + 0x24), env.get(manager + 0x78))
            env.put(log, n + 1)
            if kind == 0x24:
                env.put(call.arguments[1], status)
            if drop_after == (kind, n):
                env.put(manager + 0x78, 0)
            if swap_after == (kind, n):
                env.put(voices[which] + 0xc, alternate)
                env.put(voices[which] + 0x10, replacement)
                env.put(voices[which] + 0x14, 0x52)
                env.put(voices[which] + 0x18, 11025)
            return 0x80004005 if (kind, n) in errors or (kind, -1) in errors else 0
        return effect

    for i, buffer in enumerate(buffers + [alternate]):
        vt = env.object(0x48, 'buffer-vtable')
        env.put(buffer, vt)
        for slot, argc in ((0x24, 2), (0x30, 4), (0x3c, 2), (0x40, 2), (0x44, 2)):
            env.put(vt + slot, env.stub(f'buffer-{i}-{slot:x}', 'stdcall', argc,
                    method(slot, min(i, 1), int(i == 0 and busy_first))))
    for i, voice in enumerate(voices):
        env.put(voice + 4, voices[i + 1] + 4 if i == 0 else 0,
                voices[i - 1] + 4 if i else 0, buffers[i], manager,
                0xA4 ^ seed, 22050 + seed % 1000, 167 + i, -2811 - i,
                27000 + i, 0x13572468, pool, 0 if i == 0 and skip_first else 1,
                0x24681357)
    env.put(pool + 0x30, voices[0] + 4, voices[1] + 4)
    env.put(0x532c0c, manager)
    env.put(0x532c10, 73)
    env.put(0x540e00, 0)
    env.put(0x54130c, 0, 0, 0, 0)
    table = [-10000] + [int(-1000 * math.log2(100 / i)) for i in range(1, 100)] + [0]
    env.put(0x541178, *table)
    sound = env.object(0x14, 'sound')
    scene = env.object(0x2c, 'scene')
    world = env.object(0x60, 'world')
    plane = env.object(0x88, 'plane')
    wrapper = env.object(0x14, 'width-wrapper')
    dimensions = env.object(0x14, 'dimensions')
    env.put(sound + 0xc, scene, pool)
    env.put(scene + 4, wrapper)
    env.put(scene + 0x24, world)
    env.put(world + 0x5c, plane)
    env.put(plane + 0x84, 411)
    env.put(wrapper + 0x10, dimensions)
    env.put(dimensions + 0x10, 303)
    return dict(manager=manager, replacement=replacement, pool=pool, sound=sound,
                scene=scene, dimensions=dimensions, plane=plane, voices=voices)


def player(env, value, *, missing=False, null_value=False, disabled=0, key=b'CLAW_\xe1'):
    obj = env.object(0x34, 'name-player')
    name = env.object(len(key) + 1, 'query', data=key + b'\0')
    buckets = env.object(4, 'buckets')
    tail = 0
    for text, result in ((key, 0 if null_value else value), (b'collision-first', 0x13572468)):
        k = env.object(len(text) + 1, 'map-key', data=text + b'\0')
        node = env.object(16, 'map-node', words=[tail, 0xABCD1234, k, result])
        tail = node
    env.put(buckets, 0 if missing else tail)
    env.put(obj + 0x10, 0x456789ab, buckets, 1)
    env.put(obj + 0x30, disabled)
    return obj, name


def speech_setup(*, actor=True, state=True, blocked=0, other=None, named=False,
                 missing=False, null_value=False, key=b'VOICE_7'):
    def setup(env):
        tokens = graph(env)
        a = env.object(0x188, 'speech-actor')
        s = env.object(0x20, 'speech-state')
        env.put(s + 0x1c, 0x98765432)
        env.put(a + 0x6c, s if state else 0)
        env.put(a + 0x184, 0x13572468)
        env.put(a + 0xc, tokens['scene'])
        env.put(0x53c9a4, a if actor else 0)
        env.put(0x53c9a0, blocked)
        env.put(0x537e88, 0)
        if other is not None:
            o = env.object(0x70, 'other-actor')
            os = env.object(0x20, 'other-state')
            env.put(o + 0x6c, os)
            env.put(os + 0x1c, other)
            env.put(0x537e88, o)
        tokens['token'] = tokens['sound']
        if named:
            p, name = player(env, tokens['sound'], missing=missing,
                             null_value=null_value, key=key)
            env.put(tokens['scene'] + 0x28, p)
            tokens['token'] = name
        return tokens
    return setup


def cases(random_source):
    for value in range(101):
        yield Case(f'finite volume {value}', TABLE, arguments=(value,))
    for available in (0, 1):
        yield Case(f'pool availability {available}', POOL,
                   lambda e, a=available: graph(e, available=a),
                   receiver=lambda t: t['pool'], arguments=(37, -83, 17, 1))
    for fn, field in ((DIRECT, 'sound'), (SPATIAL, 'sound')):
        def absent(env):
            env.put(0x532c0c, 0)
        yield Case(f'{fn:x} absent manager without receiver access', fn, absent,
                   receiver=0, arguments=(0x12345678, 0x87654321, 0xffffffff, 7))
    for mode in ('success', 'busy-first', 'skip-first', 'status-error', 'volume-error',
                 'pan-error', 'frequency-error', 'play-error', 'all-errors',
                 'drop-selection', 'drop-volume', 'drop-pan', 'drop-frequency',
                 'swap-volume', 'swap-pan'):
        errors = {'status-error': ((0x24, -1),), 'volume-error': ((0x3c, 4),),
                  'pan-error': ((0x40, 5),), 'frequency-error': ((0x44, 6),),
                  'play-error': ((0x30, -1),),
                  'all-errors': ((0x3c, -1), (0x40, -1), (0x44, -1), (0x30, -1))}.get(mode, ())
        drop = {'drop-selection': (0x3c, 1), 'drop-volume': (0x3c, 4),
                'drop-pan': (0x40, 5), 'drop-frequency': (0x44, 6)}.get(mode)
        swap = {'swap-volume': (0x3c, 4), 'swap-pan': (0x40, 5)}.get(mode)
        yield Case('pool ' + mode, POOL,
                   lambda e, m=mode, er=errors, d=drop, sw=swap: graph(e, errors=er,
                       busy_first=m == 'busy-first', skip_first=m == 'skip-first',
                       drop_after=d, swap_after=sw),
                   receiver=lambda t: t['pool'], arguments=(91, -67, -99, 0x87654321))
    for i in range(24):
        args = (random_source.randrange(101), random_source.randrange(-100, 101),
                random_source.getrandbits(32), random_source.getrandbits(32))
        seed = random_source.getrandbits(16)
        yield Case(f'direct randomized forwarding {i}', DIRECT,
                   lambda e, s=seed: graph(e, seed=s), receiver=lambda t: t['sound'],
                   arguments=args)
    for disabled, missing, null_value, present in ((1, False, False, 1),
            (0, True, False, 1), (0, False, True, 1), (0, False, False, 0),
            (0, False, False, 1)):
        def named(env, d=disabled, m=missing, n=null_value, present=present):
            t = graph(env)
            p, name = player(env, t['sound'], missing=m, null_value=n, disabled=d)
            t.update(player=p, name=name)
            env.put(0x532c0c, t['manager'] if present else 0)
            return t
        yield Case(f'name {disabled}/{missing}/{null_value}/{present}', NAME, named,
                   receiver=lambda t: t['player'], arguments=(lambda t: t['name'],))
    speech_options = [dict(actor=False), dict(state=False), dict(blocked=1),
                      dict(other=0x1c), dict(other=0x138d), dict(other=0x138c),
                      dict(other=0x138b), dict(other=0), {}]
    for named in (False, True):
        fn = SPEECH_NAME if named else SPEECH
        for index, options in enumerate(speech_options):
            for force in (0, 1, 0x80000000):
                yield Case(f'speech named={named} branch={index} force={force}', fn,
                           speech_setup(named=named, **options),
                           arguments=(lambda t: t['token'], force))
        yield Case(f'speech named={named} null input', fn,
                   speech_setup(named=named), arguments=(0, 1))
    for missing, null_value in ((True, False), (False, True)):
        yield Case(f'speech name missing={missing} null-value={null_value}', SPEECH_NAME,
                   speech_setup(named=True, missing=missing, null_value=null_value),
                   arguments=(lambda t: t['token'], 0))
    geometries = [(411 + d, 411, clamp, pan) for clamp, pan in
                  ((60, 90), (90, 60), (60, 60))
                  for d in (-100, -90, -60, -59, -1, 0, 1, 59, 60, 90, 100)]
    geometries += [(17, 0, 0, 0), (17, -1, -1, -1),
                   (0x80000000, 0x7fffffff, 999, 1000),
                   (0, 0x80000000, 999, 1000),
                   (0x7fffffff, 1, 0x7fffffff, 0x7fffffff)]
    for i in range(24):
        geometries.append((random_source.randrange(-2000, 2001),
                           random_source.randrange(1, 1000),
                           random_source.randrange(1, 1000),
                           random_source.randrange(1, 1000)))
    for i, args in enumerate(geometries):
        master = (0, 1, 37, 99, 100)[i % 5]
        def spatial(env, master=master):
            t = graph(env)
            env.put(0x532c10, master)
            return t
        yield Case(f'spatial clamp and rounding {i}', SPATIAL, spatial,
                   receiver=lambda t: t['sound'], arguments=args)
