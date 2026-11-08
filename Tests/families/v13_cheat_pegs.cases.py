"""v1.3 peg callbacks: independent profile/cheat flags and fixed branch matrix."""
from clawparity.cases import Case

SLIDING, CRUMBLE, RESPAWN, TOGGLE = 0x4A0F30, 0x4A1230, 0x4A1430, 0x4A2080
MAP, AUDIO, RAND = 0x4FC6B4, 0x4B3DA0, 0x4A595B


def peg_setup(noise, state, profile=0, cheat=0, sprite=True, delay=37,
              ttl=91, category=0x9234, equal=True, ended=1, wait=0,
              standing=2, progress=91, kind=0, secondary=113,
              sound=0, elapsed=29, interval=29, audio_enabled=1,
              map_mutation=False, map_success=False, active_animation=False,
              random_value=0x6A37, audio_result=0x91):
    def setup(env):
        # Distinct data around every field makes offset/width mistakes observable.
        obj = env.object(0x240, 'peg', data=noise)
        logic = env.object(0xC0, 'peg-logic')
        world = env.object(0x40, 'world')
        sounds = env.object(0x40, 'sounds')
        resources = env.object(0x40, 'animations')
        profile_data = env.object(0xA0, 'profile-rectangles')
        player = env.object(0xA0, 'player')
        player_logic = env.object(0x20, 'player-logic')
        progress_data = env.object(0x90, 'player-progress')
        frame_table = env.object(0x40, 'frame-table')
        images = env.object(0x70, 'images')
        sound_resource = env.object(0x20, 'sound-resource')
        audio = env.object(0x20, 'audio')
        observations = env.object(0x50, 'service-observations')
        animation = env.object(0x24, 'animation')
        action_table = env.object(4, 'action-table')
        action = env.object(0x34, 'animation-action', fill=0)
        env.put(animation + 0x0C, action_table, 1)
        env.put(animation + 0x20, 0x3F800000)
        env.put(action_table, action)
        env.put(action + 8, 3, 9, 0, 91)
        env.put(action + 0x1C, 0x73A14629)
        env.put(obj + 0x0C, world)
        env.put(world + 0x28, sounds, resources)
        env.put(sounds + 0x0C, world)
        # Disable positional sound here; dedicated audio cases use crumble's helper.
        env.put(world + 0x24, 0)
        if sound == 3:
            camera = env.object(0x60, 'camera')
            listener = env.object(0x90, 'listener')
            display = env.object(0x14, 'display')
            dimensions = env.object(0x14, 'dimensions')
            env.put(world + 0x24, camera)
            env.put(camera + 0x5C, listener)
            env.put(listener + 0x84, 239)
            env.put(world + 4, display)
            env.put(display + 0x10, dimensions)
            env.put(dimensions + 0x10, 640)
        env.put(sounds + 0x30, 1 if sound == 2 else 0)
        env.put(obj + 0x7C, logic)
        env.put(logic + 0x10, kind)
        env.put(logic + 0x1C, state, 0x91E7A53B)
        env.put(logic + 0x4C, 150)
        env.put(logic + 0x64, 91 if equal else 92)
        env.put(logic + 0xBC, 23)
        env.put(obj + 8, 0xA5000040)
        env.put(obj + 0x40, 0xD0608103)
        env.put(obj + 0x5C, 173)
        env.put(obj + 0x74, ttl)
        env.put(obj + 0xE8, category)
        env.put(obj + 0x124, kind if kind in (0, 1, 2) else 0)
        env.put(obj + 0x12C, secondary)
        env.put(obj + 0x164, delay, 113)
        env.put(obj + 0x174, 0x17001701, 0x18001801)
        env.put(obj + 0x180, 0xA5000040)
        env.put(obj + 0x190, 91, images if sprite else 0, 0x99119911)
        for i in range(16):
            env.put(frame_table + i * 4, 0xA1010000 + i * 0x101)
        env.put(images + 0x14, frame_table)
        env.put(images + 0x64, 3, 8)
        # A null current animation makes the real updater return without changing
        # the pending/finished values the callback must inspect afterwards.
        env.put(obj + 0x1B0, obj, animation if active_animation else 0, action if active_animation else 0)
        env.put(obj + 0x1BC, 0)
        env.put(obj + 0x1C0, wait, 1, ended, 0)
        env.put(obj + 0x1D0, 0xAA55AA55, 0x55AA55AA, 0x3F800000)
        env.put(profile_data + 0x58, 11, 22, 33, 44)
        env.put(profile_data + 0x78, 55, 66, 77, 88)
        env.put(player + 8, 0xD0400000 | (0x10 if standing else 0))
        env.put(player + 0x98, obj if standing == 2 else player)
        env.put(player + 0x7C, player_logic)
        env.put(player_logic + 0x14, progress_data)
        env.put(progress_data + 0x80, progress)
        env.put(sound_resource + 0x0C, world, audio, 100, interval)
        env.put(0x5360A8, profile_data)
        env.put(0x5365D4, player)
        env.put(0x535990, profile)
        env.put(0x535950, cheat)
        env.put(0x535928, elapsed)
        env.put(0x5AAFD8, 7)
        env.put(0x5AAFDC, 100 + elapsed)
        env.put(0x53098C, audio_enabled)
        env.put(0x530990, 100 if sound == 3 else 0xE7)

        def lookup(e, call):
            name = e.read(call.arguments[0], 16)
            found = sound_resource if sound == 1 and name == b'LEVEL_PEGCRUMBLE' else 0
            if sound == 3 and name[:14] == b'LEVEL_PEGSLIDE':
                found = sound_resource
            if map_success and name[:5] == b'GAME_':
                found = animation
            e.put(call.arguments[1], found)
            count = e.calls_so_far(MAP)
            e.put(observations, count, call.receiver, call.arguments[0], found)
            e.put(observations + 0x10, e.get(obj + 0xE8), e.get(logic + 0x1C),
                  e.get(obj + 0x190), e.get(obj + 0x174), e.get(obj + 0x178))
            if map_mutation:
                # Native dictionary activity can change live game data: callbacks
                # must reload fields after returning from their original helper.
                e.put(obj + 0x164, 71)
                e.put(obj + 0x194, 0)
            return 1 if found else 0

        def playback(e, call):
            e.put(observations + 0x30, call.receiver, *call.arguments)
            e.put(observations + 0x44, e.get(sound_resource + 0x14),
                  e.get(logic + 0x1C), e.get(obj + 0xE8))
            return audio_result

        env.override(MAP, lookup)
        env.override(AUDIO, playback)
        env.override(RAND, lambda e, call: random_value)
        env.override(0x50C58C, lambda e, call: 0x12345678)
        return obj
    return setup


def cases(random_source):
    # Only payloads vary with the seed; branch choices and case count never do.
    serial = 0

    def case(function, state, **options):
        nonlocal serial
        serial += 1
        noise = bytes(random_source.randrange(256) for _ in range(0x240))
        options.setdefault('random_value', random_source.randrange(0x8000))
        return Case(f'peg {serial:03d} {function:x} state {state:x} {options}',
                    function, peg_setup(noise, state, **options),
                    arguments=(lambda obj: obj,))

    flags = ((0, 0), (1, 0), (0, 1), (3, 0x80000000))
    for function in (SLIDING, CRUMBLE, RESPAWN, TOGGLE):
        for profile, cheat in flags:
            for sprite in (False, True):
                for delay in (0, -1, -2, 37):
                    yield case(function, 0, profile=profile, cheat=cheat,
                               sprite=sprite, delay=delay,
                               ttl=0 if sprite else 91,
                               secondary=0 if delay == 0 else 113,
                               kind=1 if delay == -1 else 2)

    for function in (SLIDING, TOGGLE):
        for state in (1003, 1005):
            for profile, cheat in flags:
                for equal in (False, True):
                    for ended, wait in ((0, 0), (1, 13), (1, 0)):
                        for delay in (-1, -2, 37):
                            yield case(function, state, profile=profile, cheat=cheat,
                                       equal=equal, ended=ended, wait=wait, delay=delay)

    for function in (CRUMBLE, RESPAWN):
        for profile, cheat in flags:
            for equal in (False, True):
                for ended, wait in ((0, 0), (1, 13), (1, 0)):
                    yield case(function, 1005, profile=profile, cheat=cheat,
                               equal=equal, ended=ended, wait=wait)
        for profile, cheat in flags:
            for standing in (0, 1, 2):
                yield case(function, 5, profile=profile, cheat=cheat, standing=standing,
                           delay=-7 if standing == 1 else 57)
            yield case(function, 1111, profile=profile, cheat=cheat, delay=57)
        for sound, enabled, elapsed, interval in (
                (0, 1, 29, 29), (2, 1, 29, 29), (1, 0, 29, 29),
                (1, 1, 28, 29), (1, 1, 29, 29), (1, 1, 30, 29),
                (1, 1, 0, 0)):
            yield case(function, 1002, sound=sound, audio_enabled=enabled,
                       elapsed=elapsed, interval=interval)

    for function in (SLIDING, TOGGLE):
        for state in (1002, 1004):
            yield case(function, state)
    for kind in (0, 0x4A2350, 0x4A2370, 0x4A2390):
        yield case(TOGGLE, 0, kind=kind, delay=0)
    for state in (1006, 1007):
        for elapsed in (23, 59, 60, 61, 172, 173, 174, 0xFFFFFFFF):
            yield case(TOGGLE, state, elapsed=elapsed, delay=37)
    for progress in (90, 91, 92, -1, 0x7FFFFFFF, 0x80000000):
        yield case(RESPAWN, 23, progress=progress)
    for function in (SLIDING, CRUMBLE, RESPAWN, TOGGLE):
        for state in (1, 1001, 1008, 0xFFFFFFFF):
            yield case(function, state)
        yield case(function, 0, map_mutation=True)

    for function in (SLIDING, CRUMBLE, RESPAWN, TOGGLE):
        for sprite in (False, True):
            for mutation in (False, True):
                yield case(function, 0, sprite=sprite, map_success=True,
                           map_mutation=mutation, delay=-1, ttl=0)
        for equal in (False, True):
            yield case(function, 1005, equal=equal, active_animation=True,
                       ended=0, wait=0)

    for function in (SLIDING, TOGGLE):
        for state in (1002, 1004):
            for enabled in (0, 1):
                for result in (0, 0x91):
                    yield case(function, state, sound=3, audio_enabled=enabled,
                               audio_result=result)
