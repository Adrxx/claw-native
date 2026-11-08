"""Original-backed Red Tail jump, block, death and revival cases."""
import itertools
import struct
from clawparity.cases import Case
from clawparity.fixtures import sequence


def setup_case(words, **o):
    def setup(env):
        boss = env.object(0x540, 'red-tail', data=words)
        state = env.object(0x180, 'logic', fill=0)
        publication = env.object(0x40, 'publication', fill=0x39)
        sprite = env.object(0x200, 'sprite', fill=0)
        vt = env.object(0x80, 'vtable', fill=0)
        record = env.object(0x200, 'callback-record', fill=0x71)
        player = env.object(0x190, 'player', fill=0)
        player_state = env.object(0x140, 'player-state', fill=0)
        bits = env.object(0x20, 'dynamic-bits', fill=0x65)
        def put(off, value):
            env.put(boss + off, value)
        env.put(boss, vt)
        put(0xc, state)
        put(0x10, publication)
        put(0x12c, sprite)
        put(0x134, 0x11223344)
        env.put(publication + 0x1c, 0x73517)
        env.put(state + 0xcc, o.get('state', 1))
        env.put(state + 0x10c, 43)
        for off, value in ((0x38, o.get('ax', .125)), (0x40, o.get('ay', .875)),
                           (0x48, o.get('az', -.03125)), (0x50, 12.250000000000004),
                           (0x58, -17.500000000000007), (0x60, 6.125000000000003), (0x68, o.get('x', 37450.25)),
                           (0x70, o.get('y', 1500.25)), (0x78, o.get('z', 3.5))):
            env.write(boss + off, struct.pack('<d', value))
        env.put(0x52b354, o.get('left', -137), 333, o.get('floor', 1000), o.get('bottom', 1800))
        env.put(0x537210, 0x78123456)
        env.put(0x5430c4, o.get('dt', 3))
        if 'health_scale' in o:
            env.write(0x5262b4, struct.pack('<f', o['health_scale']))
        env.put(0x537680, 0)  # Empty real symbol table; dba00 remains original.
        env.put(0x53c9ac, player if o.get('speech_enabled', False) else 0)
        env.put(0x53c9a8, 0)
        env.put(0x53c9b0, state if o.get('speaking', False) else 0)
        env.put(0x537e88, player)
        env.put(player + 0x10c, o.get('health', 100))
        env.put(player + 0x6c, player_state)
        env.put(player_state + 0x1c, 15)
        env.put(sprite + 8, o.get('flags', 0xa5a50105))
        env.put(sprite + 0x40, o.get('flip', 0xa0))
        for off, value in ((0x118, -31), (0x120, 71), (0x128, -43), (0x130, 83), (0x138, -59), (0x140, 97)):
            env.put(sprite + off, value)
        put(0x138, -113)
        put(0x140, 173)
        put(0x18c, o.get('direction', 2))
        frame = env.object(0x30, 'frame', fill=0)
        env.put(frame + 0xc, 9)
        env.put(frame + 0x18, 5, 0x726354)
        if 'alias_delay' in o:
            # Frame duration shares storage with the jump's initial velocity.
            frame = boss + o['alias_delay'] - 0x1c
        frames = env.object(4, 'frames', words=[frame])
        anim = env.object(0x18, 'animation', fill=0)
        env.put(anim + 0xc, frames, 1)
        for off in (0x33c, 0x374, 0x47c):
            put(off, anim if o.get('animation', True) else 0)
        env.put(sprite + 0x18c, sprite)
        env.put(sprite + 0x190, anim if o.get('tick', False) else 0)
        env.put(sprite + 0x194, frame, 0)
        env.put(sprite + 0x1a0, 1)
        env.put(sprite + 0x1a8, 0x12345678, 0x76543210, 0x3f800000)
        env.put(sprite + 0x19c, o.get('timer', 0))
        env.put(sprite + 0x1a4, o.get('complete', 1))
        put(0x460, o.get('saved_argument', 0x98765))
        put(0x464, 6)
        put(0x450, -349)
        put(0x454, 785)
        put(0x45c, 1)  # End-level gem already exists.
        put(0x4e0, o.get('revived', 0))
        put(0x4e8, o.get('spoken', 1))
        put(0x4ec, o.get('finished', 0))
        put(0x2fc, o.get('bit_count', 17))
        put(0x2f8, 32)
        put(0x300, bits if o.get('bit_count', 17) > 32 else 0x25252525)
        for off in (0x49c, 0x4a0, 0x4a4, 0x3a4):
            put(off, o.get('speech_id', 0x83214) + off)
        sound = env.object(0x18, 'sound', fill=0)
        voice = env.object(0x40, 'voice', fill=0)
        audio = env.object(0x80, 'audio', fill=0)
        env.put(sound + 0x10, voice)
        env.put(voice + 0x10, audio)
        env.put(audio + 0x78, 0)
        put(0x40c, sound if o.get('sound', 0) else 0)
        put(0x4a4, sound if o.get('sound', 0) else 0)
        env.put(0x532c0c, o.get('sound_global', 1))
        env.put(0x532c10, 10 if o.get('active_audio', False) else 0x31415926)
        if o.get('active_audio', False):
            node = env.object(0x40, 'live-voice-node', fill=0)
            next_node = env.object(0x40, 'next-voice-node', fill=0)
            detached_backend = env.object(0x80, 'detached-voice-backend', fill=0)
            env.put(audio + 0x78, 1)
            env.put(voice + 0x18, 22050, -100, -300)
            env.put(voice + 0x30, node + 4, next_node + 4)
            env.put(node + 4, 0, next_node + 4)
            env.put(next_node + 4, node + 4, 0)
            env.put(node + 0x10, detached_backend)
            env.put(node + 0x30, 1)
            # The sound's active manager reuses its first detached voice and
            # moves its genuine intrusive-list node behind the second node.
            # Detached voices have a disabled backend; no stack-output COM
            # callback is needed to observe the real sound call's list effect.
        if o.get('publication_alias', False):
            reward_player = env.object(0x180, 'reward-player', fill=0)
            env.put(reward_player + 0x10c, 100)
            # 420590 publishes into the receiver's state pointer; 48cf50 then
            # observes the new matching speech owner in separate speech state.
            env.put(reward_player + 0x6c, boss + 0xc - 0x1c)
            env.put(0x537e88, reward_player)
            env.put(0x53c9ac, player)
            env.put(0x53c9b0, 0x1392)
            env.put(player_state + 0x130, 0x78342561)
        if o.get('gem_guard_alias', False):
            # The real publication sets the gem guard before the real gem helper.
            env.put(player + 0x6c, boss + 0x45c - 0x1c)
            put(0x45c, 0)
        env.override(0x4a3050, sequence(*o.get('rand', (57, 2, 13))))
        def callback(slot):
            def effect(env, call):
                n = env.get(record)
                base = record + 4 + n * 0x70
                env.put(base, slot, call.receiver, len(call.arguments), *call.arguments)
                env.write(base + 0x14, env.read(boss + 0x38, 0x40))
                env.put(base + 0x54, env.get(state + 0xcc), env.get(state + 0x10c), env.get(boss + 0x4ec))
                env.put(record, n + 1)
                if slot == 0x24 and o.get('callback_change', False):
                    env.put(boss + 0x4e4, 0xabcdef01)
                    env.put(boss + 0x4ec, 0xabcdef02)
                    env.put(state + 0x10c, 91)
                return o.get('callback_return', 0x2468ace0)
            return effect
        env.put(record, 0)
        for slot, argc in ((0x24, 0), (0x44, 0), (0x5c, 1)):
            env.put(vt + slot, env.stub('virtual-%x' % slot, 'thiscall', argc, callback(slot)))
        return boss
    return setup


def cases(random_source):
    def case(label, fn, **options):
        words = bytes(random_source.randrange(1, 256) for _ in range(0x540))
        args = (0x98765,) if fn in (0x481880, 0x481c90, 0x4821c0) else ()
        return Case(label, fn, setup_case(words, **options), receiver=lambda p: p, arguments=args)
    for fn in (0x481880, 0x481c90):
        for state, y in itertools.product((1, 7, 8), (999.0, 1000.0, 1001.0)):
            yield case('dispatch %x %s %s' % (fn, state, y), fn, state=state, y=y)
        for acceleration in ((0, 0, 0), (1e-8, 0, 0), (.125, 0, 0), (.125, .875, -.03125), (-.5, 1.25, .75)):
            for direction, x, flip in itertools.product((1, 2, 3), (37000.0, 37450.0, 38000.0), (0xa0, 0xa2)):
                yield case('trajectory %x %s %s %s %s' % (fn, acceleration, direction, x, flip), fn,
                           y=1001.0 if fn == 0x481880 else 999.0,
                           ax=acceleration[0], ay=acceleration[1], az=acceleration[2],
                           direction=direction, x=x, flip=flip)
        for sound, enabled in ((0, 1), (1, 0), (1, 1)):
            yield case('jump audio %x %s %s' % (fn, sound, enabled), fn,
                       y=1001.0 if fn == 0x481880 else 999.0, sound=sound, sound_global=enabled)
    for fn in (0x481c10, 0x481f70, 0x481fe0):
        for state, y in itertools.product((1, 7, 8), (924.0, 925.0, 926.0, 1744.0, 1745.0, 1746.0, 2000.0, 2001.0)):
            yield case('landing %x %s %s' % (fn, state, y), fn, state=state, y=y)
    for direction, flip, rand in itertools.product((1, 2, 3), (0xa0, 0xa2), ((32, 0), (33, 1), (100, 2), (101, 2), (-1, 1))):
        yield case('block %s %s %s' % (direction, flip, rand), 0x482090, direction=direction, flip=flip, rand=rand, speech_enabled=True)
    for sound, enabled in ((0, 1), (1, 0), (1, 1)):
        yield case('block audio %s %s' % (sound, enabled), 0x482090, sound=sound, sound_global=enabled)
    for complete, timer in itertools.product((0, 1), (0, 1, 99)):
        yield case('block update %s %s' % (complete, timer), 0x482180, complete=complete, timer=timer)
    for y, state, animation in itertools.product((999.0, 1001.0), (1, 7), (False, True)):
        yield case('death %s %s %s' % (y, state, animation), 0x4821c0, y=y, state=state, animation=animation)
    for spoken, speaking, complete, timer, finished in itertools.product((0, 1), repeat=5):
        yield case('death wait %s' % ((spoken, speaking, complete, timer, finished),), 0x482260,
                   spoken=spoken, speaking=speaking, complete=complete, timer=timer, finished=finished)
    for count, health in itertools.product((0, 4, 5, 32, 33, 64), (-1, 0, 1, 100)):
        yield case('death reward %s %s' % (count, health), 0x482260, bit_count=count, health=health)
    for revived, change, result in itertools.product((0, 1), (False, True), (0, 0xdeadbeef)):
        yield case('revive %s %s %s' % (revived, change, result), 0x482380, revived=revived, callback_change=change, callback_return=result)

    for fn in (0x481880, 0x481c90):
        for direction, flip in itertools.product((2, 3), (0xa0, 0xa2)):
            yield case('exact jump target %x %s %s' % (fn, direction, flip), fn,
                       y=1001.0 if fn == 0x481880 else 999.0,
                       x=37500.0, direction=direction, flip=flip)
        for index in range(12):
            yield case('random trajectory %x %s' % (fn, index), fn,
                       y=1000.0 + random_source.uniform(.125, 120) if fn == 0x481880 else random_source.uniform(-300, 999),
                       x=random_source.uniform(36500, 39000), z=random_source.uniform(-30, 80),
                       ax=random_source.uniform(-2, 2), ay=random_source.uniform(.1, 2), az=random_source.uniform(-1, 1),
                       flags=random_source.getrandbits(32), flip=random_source.getrandbits(32),
                       rand=(random_source.randrange(-32768, 32768),))
    for scale in (0.0, -0.5, 0.125, 1.75):
        yield case('revival health scale %s' % scale, 0x482380, health_scale=scale, callback_change=True)

    for fn in (0x481880, 0x481c90, 0x482090):
        for sound in (0, 1):
            yield case('active sound %x %s' % (fn, sound), fn,
                       y=1001.0 if fn == 0x481880 else 999.0,
                       sound=sound, active_audio=True)
    for fn in (0x481880, 0x481c90):
        for offset in (0x50, 0x54, 0x58, 0x5c, 0x60, 0x64):
            yield case('frame delay aliases velocity %x %x' % (fn, offset), fn,
                       y=1001.0 if fn == 0x481880 else 999.0, alias_delay=offset)
    for fn in (0x481c10, 0x481f70, 0x482180, 0x482260):
        for timer, complete, dt in itertools.product((0, 1, 7), (0, 1), (0, 3)):
            yield case('live animation %x %s %s %s' % (fn, timer, complete, dt), fn,
                       tick=True, timer=timer, complete=complete, dt=dt, state=1)
    for fn in (0x481c10, 0x481f70):
        yield case('saved death dispatch %x' % fn, fn, saved_argument=6)
    yield case('death speech release through publication alias', 0x482260, publication_alias=True)
    yield case('death guard published before gem creation', 0x482260, gem_guard_alias=True)
