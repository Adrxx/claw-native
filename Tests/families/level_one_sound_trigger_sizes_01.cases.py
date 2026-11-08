"""Cases for level_one_sound_trigger_sizes_01: Level 1 sound trigger size variants.

Each wrapper stores its own size code in global 0x53C9B4 and forwards the actor
to the shared body (0x48C1E0 for the first four, 0x48C8F0 for the last four).
Cases give the global a distinct nonzero starting value, give every actor
distinct random contents and drive the shared body through several states so
that the global, the forwarded argument and the choice of body all show up in
the compared memory.
"""
from clawparity.cases import Case

SOUND_BODY = (0x48C450, 0x48C470, 0x48C490, 0x48C4B0)
DIALOG_BODY = (0x48CA80, 0x48CAA0, 0x48CAC0, 0x48CAE0)
CODES = {0x48C450: 3, 0x48C470: 4, 0x48C490: 5, 0x48C4B0: 6,
         0x48CA80: 9, 0x48CAA0: 10, 0x48CAC0: 11, 0x48CAE0: 12}
AUDIO = 0x4B45F0
SIZE_GLOBAL = 0x53C9B4


def record(env, tokens, call):
    """Keep audio-call arguments and surrounding state in compared surviving memory."""
    log = tokens['log']
    index = env.get(log)
    env.put(log, index + 1)
    slot = log + 4 + index * 0x500
    env.put(slot, AUDIO, call.receiver, len(call.arguments), *call.arguments)
    env.write(slot + 0x40, env.read(tokens['actor'], 0x188))
    env.write(slot + 0x1D0, env.read(tokens['state'], 0x138))
    env.put(slot + 0x310, env.get(SIZE_GLOBAL))
    return slot


def actor_setup(seed, initial_global, state=5, count=3, present=True, point=(0, 0),
                audio=True, sound=True, changed=True, callback=0):
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
        env.put(scene + 0x10, resources)
        env.put(actor + 0x0C, scene)
        env.put(actor + 0x6C, data)
        env.put(actor + 8, (int.from_bytes(seed[:4], 'little') & ~0xF0003) | 2)
        env.put(actor + 0x40, int.from_bytes(seed[4:8], 'little') & ~1)
        env.put(data + 0x10, callback)
        env.put(data + 0x1C, state)
        env.put(data + 0x64, 0xA8E4C762 if changed else 0xE713915A)
        env.put(data + 0x130, 87)
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
        env.put(player + 8, 0x40)
        env.put(player_data + 0x14, animation)
        env.put(player_data + 0x1C, 47)
        env.put(animation + 0x80, 0xE713915A)
        env.put(actor + 0x64, 0x913)
        env.put(marker + 0x6C, marker_data)
        env.put(game + 0x118, 1)
        env.put(game + 0x12C, 31)
        env.put(0x5371FC, game)
        env.put(0x53720C, 11)
        env.put(0x537E88, player if present else 0)
        env.put(0x532C0C, int(audio), 0x3517BC29)
        env.put(0x53C988, 0x75C19E63)
        env.put(0x53C9A0, 0, marker, 0xE19F3147, marker, player, 0x915E3217)
        env.put(SIZE_GLOBAL, initial_global)
        tokens = dict(actor=actor, state=data, log=env.object(0x10000, 'audio-observations', fill=0))

        def play(env, call):
            record(env, tokens, call)
            return 0xB17E39AD

        env.override(AUDIO, play)
        return tokens
    return setup


def cases(random_source):
    for address in SOUND_BODY + DIALOG_BODY:
        seed = bytes(random_source.randrange(256) for _ in range(0x600))
        start = 0x1000 + 0x111 * CODES[address]

        def make(label, **options):
            return Case(f'{address:x} {label}', address,
                        actor_setup(seed, start, callback=address, **options),
                        arguments=(lambda t: t['actor'],))

        # Initialization state, counter zero and nonzero.
        yield make('initialize count 0', state=0, count=0)
        yield make('initialize count 7', state=0, count=7)
        # Active state: player inside the box fires the sound and counts down.
        yield make('active in box', state=5, count=3)
        yield make('active last count', state=5, count=1)
        yield make('active no sound reference', state=5, sound=False)
        yield make('active muted', state=5, audio=False)
        yield make('active player outside', state=5, point=(40, 0))
        yield make('active no player', state=5, present=False)
        # Cooldown state: animation changed or not.
        yield make('cooldown changed', state=23, changed=True)
        yield make('cooldown unchanged', state=23, changed=False)
        # Unknown state and the sound-only intermediate state.
        yield make('unknown state', state=24)
        yield make('state 11', state=11)
        yield make('state 11 player outside', state=11, point=(0, 50))
