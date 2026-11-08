"""Original-derived audio triggers, speech markers and scene transitions."""
from clawparity.cases import Case

SOUND = 0x48C1E0
DIALOG = 0x48C8F0
PLAYER_MARK = 0x48C630
ENEMY_MARK = 0x48CC60
TRANSITION = 0x490130
AUDIO = 0x4B45F0


def record(env, tokens, address, call):
    """Keep arguments and publication state in compared surviving memory."""
    log = tokens['log']
    index = env.get(log)
    env.put(log, index + 1)
    slot = log + 4 + index * 0x500
    env.put(slot, address, call.receiver, len(call.arguments), *call.arguments)
    env.write(slot + 0x40, env.read(tokens['actor'], 0x188))
    env.write(slot + 0x1D0, env.read(tokens['state'], 0x138))
    env.write(slot + 0x310, env.read(0x53C988, 0x30))
    return slot


def make_map(env, target, key=None, value=0):
    buckets = env.object(4, 'map-buckets', fill=0)
    env.put(target + 4, buckets, 1)
    if key is not None:
        node = env.object(16, 'map-entry', words=[0, 0, key, value])
        env.put(buckets, node)


def actor_setup(seed, state=5, count=3, present=True, point=(0, 0),
                audio=True, sound=True, changed=True, timer=87, delta=11,
                player_state=47, same_priority=False, target='live',
                game_enabled=True, volume=31, callback=SOUND,
                change_on_audio=None, sprite=True):
    def setup(env):
        actor = env.object(0x200, 'trigger', data=seed[:0x200])
        data = env.object(0x180, 'trigger-state', data=seed[0x200:0x380])
        player = env.object(0x200, 'player', data=seed[0x380:0x580])
        player_data = env.object(0x180, 'player-state', fill=0)
        animation = env.object(0x90, 'player-animation', fill=0)
        audio_ref = env.object(0x20, 'sound-reference', fill=0)
        voice = env.object(0x40, 'voice', data=seed[:0x40])
        game = env.object(0x140, 'game-settings', fill=0)
        marker = env.object(0x200, 'active-marker', fill=0)
        marker_data = env.object(0x180, 'active-marker-state', fill=0)
        scene = env.object(0x40, 'scene', fill=0)
        resources = env.object(0x40, 'resource-manager', fill=0)
        image = env.object(0x80, 'marker-image', fill=0)
        frames = env.object(20, 'marker-frames', words=[0x12345678, 0xCAFEBABE, 0x1468ACE0, 0x76543210, 0xABCDEF12])
        env.put(image + 0x14, frames)
        env.put(image + 0x64, 2, 4)
        make_map(env, resources + 0x10, 0x52C580 if sprite else None, image)
        env.put(scene + 0x10, resources)
        env.put(actor + 0x0C, scene)
        env.put(actor + 0x6C, data)
        env.put(actor + 8, (int.from_bytes(seed[:4], 'little') & ~0xF0003) | 2)
        env.put(actor + 0x40, (int.from_bytes(seed[4:8], 'little') & ~1) | int(state == 15))
        env.put(data + 0x10, callback)
        env.put(data + 0x1C, state)
        env.put(data + 0x64, 0xA8E4C762 if changed else 0xE713915A)
        env.put(data + 0x130, timer)
        env.put(actor + 0x108, count)
        env.put(actor + 0x4C, 300, -170)
        env.put(actor + 0x128, -19, -23, 29, 37)
        env.put(actor + 0x184, audio_ref if sound else 0)
        env.put(audio_ref + 0x10, voice)
        env.put(voice + 0x28, 0x1234ABCD)
        env.put(player + 0x4C, 300 + point[0], -170 + point[1])
        env.put(player + 0x64, 41)
        env.put(player + 0x6C, player_data)
        env.put(player + 0x11C, 17)
        env.put(player + 8, 0x10000 if target == 'dead' else 0x40)
        env.put(player_data + 0x14, animation)
        env.put(player_data + 0x1C, player_state)
        env.put(animation + 0x80, 0xE713915A)
        env.put(actor + 0x64, 42 if same_priority else 0x913)
        env.put(marker + 0x6C, marker_data)
        env.put(game + 0x118, int(game_enabled))
        env.put(game + 0x12C, volume)
        env.put(0x5371FC, game)
        env.put(0x53720C, delta)
        env.put(0x537E88, player if present else 0)
        env.put(0x532C0C, int(audio), 0x3517BC29)
        env.put(0x53C988, 0x75C19E63)
        env.put(0x53C9A0, 0, marker, 0xE19F3147, marker, player if target != 'none' else 0, 0x915E3217)
        tokens = dict(actor=actor, state=data, log=env.object(0x10000, 'callback-observations', fill=0),
                      player=player, marker=marker, marker_data=marker_data)

        def play(env, call):
            record(env, tokens, AUDIO, call)
            if change_on_audio is not None:
                env.put(actor + 0x108, change_on_audio)
                env.put(animation + 0x80, 0xF1A73329)
            return 0xB17E39AD

        env.override(AUDIO, play)
        return tokens
    return setup


def actor_case(label, address, seed, **options):
    return Case(label, address, actor_setup(seed, callback=address, **options),
                arguments=(lambda t: t['actor'],))


def transition_setup(seed, missing=None, surface_fail=False, effect_fail=False,
                     skip=False, flag=1, lookup=True, audio=True,
                     clear_surface=False, extra_surface=False, release_clear=False):
    def setup(env):
        actor = env.object(0x200, 'transition-owner', data=seed[:0x200])
        state = env.object(0x180, 'observation-state', data=seed[0x200:0x380])
        log = env.object(0x10000, 'service-observations', fill=0)
        app = env.object(0xA0, 'game-application', fill=0)
        methods = env.object(0x10, 'application-methods', fill=0)
        scene = env.object(0x40, 'transition-scene', fill=0)
        world = env.object(0x20, 'world', fill=0)
        front = env.object(0x40, 'front-view', fill=0)
        back = env.object(0x40, 'back-view', fill=0)
        source = env.object(0xB0, 'source-surface', data=seed[:0xB0])
        destination = env.object(0xB0, 'destination-surface', data=seed[0x100:0x1B0])
        provider = env.object(0x40, 'render-provider', fill=0)
        manager = env.object(0x40, 'fader-manager', fill=0)
        settings = env.object(0x40, 'fader-settings', data=seed[:0x40])
        resources = env.object(0x40, 'sound-resources', fill=0)
        sound_ref = env.object(0x20, 'flagwave-reference', fill=0)
        voice = env.object(0x40, 'flagwave-voice', data=seed[:0x40])
        surface = env.object(0xB0, 'created-surface', data=seed[0x200:0x2B0])
        extra = env.object(0xB0, 'secondary-surface', data=seed[0x300:0x3B0])
        effect = env.object(0x40, 'render-effect', data=seed[:0x40])
        tokens = dict(actor=actor, state=state, log=log)
        env.put(actor + 4, app)
        env.put(actor + 0x0C, scene, manager)
        env.put(actor + 0x2C, settings)
        env.put(scene + 4, world)
        env.put(scene + 0x1C, provider)
        env.put(scene + 0x28, resources)
        env.put(world + 0x10, front, back)
        env.put(front + 0x2C, source)
        env.put(back + 0x2C, destination)
        env.put(source + 0x14, 319, 173)
        env.put(source + 0xA4, 32)
        env.put(settings + 0x10, 0x71BC92D3)
        env.put(resources + 0x30, flag)
        make_map(env, resources + 0x10, 0x5246B4 if lookup else None, sound_ref)
        env.put(sound_ref + 0x10, voice)
        env.put(0x537238, int(skip))
        env.put(0x532C0C, int(audio), 0x12EAB739)
        env.put(0x53C988, 0xC947162B)
        env.put(app, methods)

        def app_check(env, call):
            record(env, tokens, 0x42A4F0, call)
            return 0

        env.put(methods + 0x0C, env.stub('application-ready', 'thiscall', 0, app_check))
        if missing is not None:
            bases = dict(manager=(actor, 0x10), provider=(scene, 0x1C),
                         settings=(actor, 0x2C), source=(front, 0x2C),
                         back=(world, 0x14), destination=(back, 0x2C))
            base, offset = bases[missing]
            env.put(base + offset, 0)

        def service(address):
            def effect_fn(env, call):
                slot = record(env, tokens, address, call)
                if address == 0x4BC670:
                    return 0 if surface_fail else surface
                if address == 0x4EC050:
                    env.write(slot + 0x380, env.read(call.arguments[1], 0x2C))
                    if extra_surface:
                        env.put(actor + 0x40, extra)
                    return 0 if effect_fail else effect
                if address in (0x4EC9C0, 0x4B8960):
                    if clear_surface:
                        env.put(actor + 0x3C, 0)
                    if extra_surface:
                        env.put(actor + 0x40, extra)
                if address == 0x4EC600 and release_clear:
                    env.put(actor + 0x3C, 0)
                return 0xA37E192B
            return effect_fn

        for address in (AUDIO, 0x4B8960, 0x4BC670, 0x4B9C50, 0x4BC4F0,
                        0x4EC050, 0x4EC9C0, 0x4EC600):
            env.override(address, service(address))
        env.override(0x5469E4, lambda e, c: len(e.cstr(c.arguments[0])))

        def decrement(env, call):
            value = (env.get(call.arguments[0]) - 1) & 0xFFFFFFFF
            env.put(call.arguments[0], value)
            return value

        env.override(0x5469E8, decrement)
        return tokens
    return setup


def cases(random_source):
    seed = bytes(random_source.randrange(256) for _ in range(0x600))
    for value in (0, 1, 0xFFFFFFFF, random_source.getrandbits(32)):
        def getter(env, value=value):
            env.put(0x53C988, value)
        yield Case(f'current audio {value:#x}', 0x48BFD0, getter)

    for address in (SOUND, DIALOG, 0x48C410, 0x48C430, 0x48CA40, 0x48CA60):
        for count in (0, 7):
            yield actor_case(f'{address:x} initialize count {count}', address, seed, state=0, count=count)
        yield actor_case(f'{address:x} forwarded active call', address, seed, count=1)
    for address in (SOUND, DIALOG):
        for state in (1, 24, 0xFFFFFFFF):
            yield actor_case(f'{address:x} unknown state {state}', address, seed, state=state)
        for state in ((5, 11, 23) if address == SOUND else (5, 23)):
            yield actor_case(f'{address:x} state {state} no player', address, seed, state=state, present=False)
        for point in ((-20, 0), (-19, 0), (29, 0), (30, 0), (0, -24), (0, -23), (0, 37), (0, 38)):
            yield actor_case(f'{address:x} box face {point}', address, seed, point=point)
            if address == SOUND:
                yield actor_case(f'sound repeated box face {point}', address, seed, state=11, point=point)
        for count in (0, 1, 2, -1, -2, 0x80000000):
            yield actor_case(f'{address:x} active counter {count}', address, seed, count=count)
        for audio, sound in ((False, True), (True, False)):
            yield actor_case(f'{address:x} audio {audio} reference {sound}', address, seed, audio=audio, sound=sound)
        for changed in (False, True):
            yield actor_case(f'{address:x} animation changed {changed}', address, seed, state=23, changed=changed)
    for count in (1, 4, -1):
        yield actor_case(f'sound callback changes counter to {count}', SOUND, seed, count=9, change_on_audio=count)

    for address in (PLAYER_MARK, ENEMY_MARK):
        for state in (0, 1, 5, 29, 34, 0xFFFFFFFF):
            yield actor_case(f'{address:x} state {state}', address, seed, state=state)
        yield actor_case(f'{address:x} initialization resource missing', address, seed, state=0, sprite=False)
        for sound, enabled in ((False, True), (True, False), (True, True)):
            yield actor_case(f'{address:x} activate sound {sound} enabled {enabled}', address, seed,
                             state=1001, sound=sound, game_enabled=enabled)
        for volume in (-41, 79, 80, 89, 90, 100, 0x7FFFFFFF):
            yield actor_case(f'{address:x} volume {volume}', address, seed, state=1001, volume=volume)
        yield actor_case(f'{address:x} activate muted', address, seed, state=1001, audio=False)
        for timer, delta in ((0, 0), (1, 0), (11, 11), (10, 11), (12, 11), (0xFFFFFFFF, 0x80000000)):
            yield actor_case(f'{address:x} countdown {timer}/{delta}', address, seed, state=15, timer=timer, delta=delta)
        yield actor_case(f'{address:x} unchanged priority', address, seed, state=15, same_priority=True)
        for index, point in enumerate(((13, -9),
                                       (random_source.randrange(1, 80), -random_source.randrange(1, 80)))):
            for same_priority in (False, True):
                yield actor_case(f'{address:x} distinct follow coordinates {index} priority {same_priority}',
                                 address, seed, state=15, point=point, same_priority=same_priority)
    yield actor_case('player marker no player', PLAYER_MARK, seed, state=15, present=False)
    for player_state in (0x138C, 0x138D, 0x138B):
        yield actor_case(f'player marker player state {player_state}', PLAYER_MARK, seed, state=15, player_state=player_state)
    for target in ('none', 'dead', 'live'):
        yield actor_case(f'enemy marker target {target}', ENEMY_MARK, seed, state=15, target=target)

    for missing in ('manager', 'provider', 'settings', 'source', 'back', 'destination'):
        yield Case(f'transition missing {missing}', TRANSITION, transition_setup(seed, missing=missing),
                   receiver=lambda t: t['actor'], arguments=(0x51A2, 0x712BE349, 0x9371AC25))
    configurations = [dict(surface_fail=True), dict(effect_fail=True), dict(),
                      dict(skip=True), dict(flag=0), dict(flag=0, lookup=False),
                      dict(flag=0, audio=False), dict(clear_surface=True),
                      dict(skip=True, clear_surface=True), dict(extra_surface=True),
                      dict(skip=True, extra_surface=True), dict(release_clear=True)]
    for index, options in enumerate(configurations):
        yield Case(f'transition service path {index} {options}', TRANSITION, transition_setup(seed, **options),
                   receiver=lambda t: t['actor'], arguments=(0x31B7, 0x712BE349, 0x9371AC25),
                   initial_stack=((-56, seed[:44]),))
