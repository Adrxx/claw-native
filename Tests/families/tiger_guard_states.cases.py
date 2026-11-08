"""Original-derived inputs for tiger guard state methods."""
import itertools
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence


def setup_case(rng, **o):
    salt = rng.getrandbits(32)
    def setup(env):
        def obj(size, name):
            return env.object(size, name, words=[(salt + i * 0x1020305) & 0xffffffff for i in range(size // 4)])
        t, s, e, l = obj(0x500, 'tiger'), obj(0x200, 'sprite'), obj(0x180, 'entity'), obj(0x40, 'logic')
        vt, log, projectile = env.object(0xb0, 'vtable'), env.object(0x100, 'observations'), obj(0x20, 'projectile')
        env.put(t, vt)
        env.put(t + 0xc, e, l)
        env.put(t + 0x12c, s)
        env.put(t + 0x18c, o.get('direction', 2))
        env.put(t + 0x184, o.get('mode', 4))
        env.put(t + 0x138, 17, 23, 37, 43)
        env.put(s + 0x40, 0xa5a50000 | o.get('flip', 0))
        env.put(s + 8, 0xf1234567)
        env.put(s + 0x16c, o.get('frame', 17))
        env.put(s + 0x170, 0)
        env.put(s + 0x190, 0, 0, 0, o.get('anim_timer', 0), 0, o.get('done', 0))
        p = o.get('position', 0.25)
        for off, val in ((0x68, p), (0x70, 130.75), (0x50, 19.5), (0x58, 7.0), (0x40, 0.0)):
            env.write(t + off, struct.pack('<d', val))
        eq = o.get('equal', 'neither')
        env.write(t + 0x80, struct.pack('<d', p if eq in ('low', 'both') else 330.5))
        env.write(t + 0x98, struct.pack('<d', p if eq in ('high', 'both') else -440.5))
        env.put(t + 0x220, 11, 19, 31, 47)
        env.put(t + 0x260, 61, 71, 83, 97)
        env.put(t + 0x270, 101, 103, 107, 109)
        for off, key, default in ((0x4c0, 'limit', 0), (0x4c4, 'count', 1), (0x4cc, 'speed', -333),
                                  (0x4d0, 'once', 0), (0x4d8, 'attack', 0), (0x4dc, 'invulnerable', 0),
                                  (0x424, 'hit_stage', 2), (0x404, 'advance_speed', 77)):
            env.put(t + off, o.get(key, default))
        now = o.get('now', 0x1234)
        env.put(0x537210, now)
        env.put(0x5430c4, 13)
        for off in (0x4b0, 0x4b8):
            env.put(t + off, o.get('start', now - 10), o.get('duration', 10))
        env.put(e + 0x10c, 8)
        for off, vals in ((0x118, (3, 5, 11, 17)), (0x128, (19, 23, 29, 31)), (0x138, (41, 43, 47, 53))):
            env.put(e + off, *vals)
            env.put(s + off, *(v + 100 for v in vals))
        for i, off in enumerate((0x30c, 0x310, 0x36c, 0x344, 0x450, 0x458, 0x454)):
            cmd = env.object(0x30, f'command {i}')
            table = env.object(4, f'command table {i}', words=[cmd])
            anim = env.object(0x20, f'animation {i}')
            env.put(anim + 0xc, table, 1)
            env.put(cmd + 0x1c, 100 + i)
            env.put(t + off, anim)
        # A real single-node trie makes state-name operands observable.
        node = env.object(0x14, 'state trie')
        env.put(node, node, node, 0, o.get('state_name', 0x526a38), 0x71)
        env.put(0x537680, node)
        env.put(l + 0x1c, 0x17)
        state_slot = env.object(4, 'current state name', words=[0x523204])
        env.put(0x5376a0, 0x17, 0x17, state_slot)
        env.put(0x5376b0, 4)
        env.put(0x5376b8, 0)
        manager = env.object(0x190, 'message manager')
        message_logic = env.object(0x30, 'message state')
        env.put(manager + 0x6c, message_logic)
        env.put(0x53c9ac, manager)
        env.put(0x53c9a8, 0)
        env.put(0x53c9b0, 0)
        env.put(t + 0x468, 0x2101, 0x2102, 0x2103, 0x2104, 0x2105, 0x2106)
        wrapper, player, buffer = env.object(0x20, 'sound wrapper'), env.object(0x20, 'sound player'), env.object(0x80, 'sound buffer')
        env.put(wrapper + 0x10, player)
        env.put(player + 0x10, buffer)
        env.put(buffer + 0x78, 0)
        sound = o.get('sound', 'present')
        env.put(t + 0x408, wrapper)
        env.put(t + 0x45c, wrapper)
        env.put(t + 0x460, wrapper if sound != 'missing' else 0, wrapper if sound != 'missing' else 0)
        env.put(t + 0x494, wrapper if sound != 'missing' else 0)
        env.put(0x532c0c, 0 if sound == 'disabled' else 1)
        env.put(0x532c10, 0x4a3b2c1d)
        env.override(0x4a3050, sequence(*o.get('rand', (77, 3))))
        def copy_rect(env, call):
            env.write(call.arguments[0], env.read(call.arguments[1], 16))
            return 1
        env.override(0x546d58, copy_rect)
        def callback(env, call):
            index = env.get(log)
            slot = log + 4 + (index % 5) * 44
            env.put(slot, call.receiver, len(call.arguments), *(list(call.arguments) + [0])[:1],
                    env.get(t + 0x4d8), env.get(t + 0x4b0), env.get(t + 0x4b4), env.get(t + 0x4c4),
                    env.get(s + 8), env.get(e + 0x138), env.get(e + 0x140), env.get(0x537210))
            env.put(log, index + 1)
            if o.get('callback_change'):
                env.put(t + 0x4d8, 1)
                env.put(t + 0x4b0, now)
                env.put(t + 0x4b4, 0x7fffffff)
            return 0x11223344
        for off, argc in ((0x44, 0), (0x90, 1), (0xa8, 0), (0x5c, 1), (0x28, 1)):
            env.put(vt + off, env.stub(f'virtual {off:x}', 'thiscall', argc, callback))
        return {'tiger': t, 'projectile': projectile}
    return setup


def one(rng, label, fn, argument=None, projectile=False, **options):
    args = () if argument is None and not projectile else ((lambda t: t['projectile']) if projectile else argument,)
    return Case(label, fn, setup_case(rng, **options), receiver=lambda t: t['tiger'], arguments=args)


def cases(rng):
    for fn in (0x495280, 0x495710, 0x495940):
        for i, (direction, p, limit, eq) in enumerate(itertools.product((0, 2, 3), (-1.25, 0.0, 1.25), (-1, 1), ('neither', 'low', 'high'))):
            yield one(rng, f'{fn:x} movement {i}', fn, direction=direction, position=p, limit=limit, equal=eq,
                      frame=(800, 402, 17)[i % 3], flip=i % 2 * 2, done=i // 2 % 2, anim_timer=i // 4 % 2,
                      attack=i // 3 % 2, duration=(0, 10, 11)[i % 3], callback_change=i % 7 == 0)
    for frame, flip, (done, timer), count in itertools.product((202, 17), (0, 2), ((0, 0), (1, 1), (1, 0)), (0, 1, 2)):
        yield one(rng, f'knife tick {frame}/{flip}/{done}/{timer}/{count}', 0x4954f0,
                  frame=frame, flip=flip, done=done, anim_timer=timer, count=count, state_name=0x52b3a4)
    for direction, flip, mode, rand in itertools.product((0, 2, 3), (0, 2), (3, 4), ((39, 0), (40, 1), (0, 3), (0xffffffff, 0xfffffffd))):
        yield one(rng, f'knife init {direction}/{flip}/{mode}/{rand}', 0x4953b0, argument=0x98765432,
                  direction=direction, flip=flip, mode=mode, rand=rand, state_name=0x52b3a4)
    for direction, flip, sound, rand in itertools.product((0, 2, 3), (0, 2), ('missing', 'disabled', 'present'), ((0,), (1,), (0xffffffff,))):
        yield one(rng, f'front init {direction}/{flip}/{sound}/{rand}', 0x4955c0, argument=0xfedcba98,
                  direction=direction, flip=flip, sound=sound, rand=rand, position=-123.75, state_name=0x52ca78)
    for i, (direction, flip, equal, sound) in enumerate(itertools.product(
            (0, 2, 3), (0, 2), ('neither', 'low', 'high'), ('missing', 'disabled', 'present'))):
        yield one(rng, f'back init {direction}/{flip}/{equal}/{sound}', 0x4957f0,
                  direction=direction, flip=flip, equal=equal, sound=sound,
                  rand=((0,), (1,), (0xffffffff,), (0x80000000,))[i % 4],
                  position=(-123.75, 0.0, 123.75)[i % 3], state_name=0x52ca98)
    for direction, position, equal in itertools.product((2, 3), (float('nan'), -0.0), ('neither', 'both')):
        yield one(rng, f'back unordered {direction}/{position}/{equal}', 0x4957f0,
                  direction=direction, flip=2, position=position, equal=equal,
                  rand=(1,), state_name=0x52ca78)
    for fn in (0x495ae0, 0x495a30):
        for direction, flip in itertools.product((0, 2, 3), (0, 2)):
            yield one(rng, f'{fn:x} block {direction}/{flip}', fn,
                      argument=0xcafebabe if fn == 0x495a30 else None, direction=direction, flip=flip)
    for projectile, sound, direction, flip in itertools.product((False, True), ('missing', 'disabled', 'present'), (2, 3), (0, 2)):
        yield one(rng, f'projectile {projectile}/{sound}/{direction}/{flip}', 0x4959e0,
                  argument=0, projectile=projectile, sound=sound, direction=direction, flip=flip)
    for invulnerable, argument in itertools.product((0, 1, 0xffffffff), (0, 0x89abcdef)):
        yield one(rng, f'hit wrapper {invulnerable}/{argument}', 0x495a40, argument=argument, invulnerable=invulnerable)
    for rand in (0, 9, 10, 100, 101, 0xffffffff):
        yield one(rng, f'lifted random {rand}', 0x495a60, rand=(rand,), state_name=0x5271d8)
    for once, stage in itertools.product((0, 1, 0x80000000), (0, 2)):
        yield one(rng, f'hit stage {once}/{stage}', 0x495ac0, once=once, hit_stage=stage)
    for now, start, duration in ((0, 0, 0), (10, 0, 9), (10, 0, 10), (10, 0, 11), (1, 0xfffffffe, 3), (1, 0xfffffffe, 4), (0, 1, 0x80000000), (0xffffffff, 0, 0xffffffff)):
        yield one(rng, f'block timer {now}/{start}/{duration}', 0x495ba0, now=now, start=start, duration=duration)
