"""Original-backed Tentacle core cases with deterministic branch selection."""
from clawparity.cases import Case
import struct

MASK = 0xffffffff

def word(v):
    return v & MASK


def setup_core(seed=1, flip=0, absent=0, audio=0, state='LS_IDLE', player=0, rand=0, mode=0, atomic=1, heap_bits=0):
    def setup(env):
        obj = env.object(0x480, 'tentacle', fill=0x39)
        actor = env.object(0x220, 'actor', fill=0)
        logic = env.object(0x200, 'logic', fill=0)
        vt = env.object(0x80, 'tentacle-vtable', fill=0)
        log = env.object(0x100, 'callback-observations', fill=0)
        def callback(env, call):
            n = env.get(log)
            if n < 12:
                env.put(log + 4 + n * 16, call.function, call.receiver, env.get(obj + 0x44c), env.get(0x53ca2c))
            env.put(log, n + 1)
            # Alter re-read inputs without supplying game outcomes.
            if mode == 1:
                env.put(obj + 0x45c, 0x40)
            return seed
        cb = env.stub('state-method-observer', 'thiscall', 0, callback)
        env.put(vt + 0x48, cb)
        env.put(vt + 0x58, cb)
        env.put(obj, vt)
        env.put(obj + 0xc, actor, logic)
        env.put(obj + 0x12c, actor)
        env.put(actor + 0x40, flip | 0x100)
        env.put(actor + 0x190, word(seed * 17 + 9))
        for off, value in ((0x118, -23), (0x120, 41), (0x128, -37), (0x130, 59), (0x138, -43), (0x140, 67)):
            env.put(actor + off, 0x80000000 if absent & (1 << ((off-0x118)//16)) else word(value + seed))
        env.put(obj + 0x138, word(-83-seed), 0x456789ab, word(97+seed))
        env.put(obj + 0x210, word(-31-seed), word(-47-seed), word(71+seed), word(89+seed))
        for off in (0x400, 0x404, 0x408, 0x374):
            frame = env.object(0x40, 'animation-frame', fill=0x6b)
            env.put(frame + 0x1c, seed * 13 + off)
            frames = env.object(4, 'animation-frames', words=[frame])
            animation = env.object(0x20, 'animation', fill=0)
            env.put(animation + 0xc, frames, 1)
            env.put(obj + off, animation)
        env.put(obj + 0x45c, 0x20)
        env.put(obj + 0x448, 0)
        env.put(obj + 0x3a4, 0)
        if audio:
            sound = env.object(0x20, 'sound', fill=0)
            backend = env.object(0x20, 'sound-backend', fill=0)
            buffer = env.object(0x80, 'sound-buffer', fill=0)
            env.put(sound + 0x10, backend)
            env.put(backend + 0x10, buffer)
            env.put(obj + 0x448, sound)
            env.put(obj + 0x3a4, sound)
        env.put(0x532c0c, audio & 1)
        env.put(0x532c10, seed * 7)
        env.put(logic + 0x1c, 3)
        env.put(0x537680, 0)  # Empty state-name trie returns zero naturally.
        table = env.object(20, 'state-name-table', fill=0)
        name = env.object(len(state)+1, 'state-name', data=state.encode()+b'\0')
        env.put(table + 12, name)
        env.put(0x5376a0, 0, 4, table, 0, 4, 0, 0)
        player_actor = env.object(0x200, 'player-actor', fill=0)
        player_logic = env.object(0x200, 'player-logic', fill=0)
        player_data = env.object(0x200, 'player-data', fill=0)
        env.put(player_actor + 0x6c, player_logic)
        env.put(player_logic + 0x14, player_data)
        env.put(0x537204, env.object(0x20, 'player-input', fill=0x55))
        env.put(0x537e88, player_actor)
        env.put(actor + 0x38, 0xffffffff)
        target = env.object(0x200, 'hit-target', fill=0)
        env.put(target + 0xd0, 0x20 if mode else 0x21)
        env.put(actor + 0x74, target)
        env.put(0x537210, word(seed * 1009))
        env.put(0x534eac, 0x26b7)
        env.put(0x541334, mode & 1)
        env.put(0x534874, 0)
        if player:
            p = env.object(0x500, 'player-mask', fill=0x53)
            env.put(p + 0x4ec, player)
            env.put(0x534874, p)
        env.put(0x53ca2c, mode & 1)
        env.put(0x53ca30, seed)
        env.put(0x544d18, 0)
        env.put(obj + 0x2fc, 64 if heap_bits else 32)
        if heap_bits:
            env.put(obj + 0x300, env.object(8, 'bitset-data', words=[0x732acd19, 0x9b731231]))
        else:
            env.put(obj + 0x300, 0xa135798b)
        for off in (0x1a4, 0x1a8):
            if atomic:
                header = env.object(32, 'cstring-header', words=[atomic, 7, 16], data=b'')
                env.write(header + 12, b'abcDEF\0')
                env.put(obj + off, header + 12)
            else:
                env.put(obj + off, env.get(0x52e1c8) + 12)
        env.override(0x4a3050, lambda env, call: word(rand))
        def decrement(env, call):
            p = call.arguments[0]
            result = word(env.get(p)-1)
            env.put(p, result)
            return result
        env.override(0x5469e8, decrement)
        return {'obj': obj, 'actor': actor, 'logic': logic, 'log': log}
    return setup


def direct(label, address, setup, arguments=()):
    return Case(label, address, setup, receiver=lambda t: t['obj'], arguments=arguments)


def cases(random_source):
    for seed in (1, 7, random_source.randrange(20, 100)):
        for address in (0x492da0, 0x493110, 0x493450):
            for flip in (0, 2):
                for absent in (0, 1, 2, 3, 4, 7):
                    yield direct(f'enter {address:x} seed {seed} flip {flip} missing {absent}', address,
                                 setup_core(seed, flip=flip, absent=absent, rand=seed * 231 - 1001, audio=(seed & 1)))
    for atomic in (0, 1, 2):
        for heap_bits in (0, 1):
            yield direct(f'destruct atomic {atomic} heap {heap_bits}', 0x492c60, setup_core(atomic+4, atomic=atomic, heap_bits=heap_bits))
            for flag in (0, 1, 2, 3, 0x100):
                yield direct(f'delete flag {flag} atomic {atomic} heap {heap_bits}', 0x492c40,
                             setup_core(atomic+4, atomic=atomic, heap_bits=heap_bits), (flag,))
    for player in (0, 0x20, 0x40, 0x60):
        for mode in (0, 1):
            yield direct(f'reset player {player} mode {mode}', 0x492ce0, setup_core(player=player, mode=mode))
            for rand in (0, 1000, 1001, -1, -1002, 0x7fffffff, -0x80000000):
                yield direct(f'timer player {player} mode {mode} random {rand}', 0x492d30,
                             setup_core(player=player, mode=mode, rand=rand), (0x12345678,))
    for mode in (0, 1):
        for rand in (0, 74, 75, 100, 101, -1, -0x80000000, 0x7fffffff):
            yield direct(f'choose mode {mode} random {rand}', 0x492f70, setup_core(mode=mode, rand=rand))
    for audio in (0, 1, 2):
        yield direct(f'strike audio {audio}', 0x492fb0, setup_core(17, audio=audio))
    for state in ('LS_DEAD', 'LS_SQUEEZE', 'LS_STARTGRAB', 'LS_SUPERFRENZY', 'LS_IDLE'):
        yield direct(f'notice state {state}', 0x4936d0, setup_core(5, state=state))
    for index in (-3, -1, 0, 2, 4):
        for handled in (0, 1):
            def dispatch_setup(env, index=index, handled=handled):
                t = setup_core(seed=29)(env)
                table = env.object(12, 'tentacle-dispatch', fill=0)
                log = t['log']
                def observe(env, call):
                    env.put(log, call.receiver, env.get(0x53ca28), index & MASK)
                    return 0x735491ac
                cb = env.stub('tentacle-handler', 'thiscall', 0, observe)
                for j in range(3):
                    env.put(table + j * 4, cb if handled else 0)
                env.put(0x53ca10, -1 & MASK, 1, table, table, 4, 0x1234)
                env.put(0x53ca28, 0x3579ace1)
                fallback = env.object(64, 'base-dispatch', fill=0)
                for j in range(16):
                    env.put(fallback+j*4, cb)
                env.put(0x537640, -5 & MASK, 10, fallback, fallback, 4, 0x5678)
                return t
            yield direct(f'dispatch {index} handler {handled}', 0x4923e0, dispatch_setup, (word(index),))
    for fallback in (0, 1):
        for default_bits in (0, 64):
            for initial_count in (0, 2, 3):
                for hp in (0, 91):
                    def constructor_setup(env, fallback=fallback, default_bits=default_bits, initial_count=initial_count, hp=hp):
                        t = setup_core(seed=23)(env)
                        actor, logic, obj = t['actor'], t['logic'], t['obj']
                        env.put(actor + 0x6c, logic)
                        env.put(actor + 0x104, hp)
                        manager = env.object(0x40, 'resource-manager', fill=0)
                        env.put(actor + 0xc, manager)
                        collision = env.object(0x80, 'collision-engine', fill=0)
                        env.put(manager + 0x24, collision)
                        def resource_map(name, entries):
                            resource = env.object(0x40, name, fill=0)
                            bucket = env.object(4, name+'-bucket', fill=0)
                            env.put(resource + 0x14, bucket, 1)
                            head = 0
                            for key, value in entries:
                                keyp = env.object(len(key)+1, 'resource-key', data=key.encode()+b'\0')
                                node = env.object(16, 'resource-node', words=[head, 0, keyp, value])
                                head = node
                            env.put(bucket, head)
                            return resource
                        for off in (0x10, 0x14, 0x28):
                            env.put(manager + off, resource_map('empty-resource-map', []))
                        sound_entries = []
                        for sound_name in ('TENTDEATH', 'TENTSWIPE', 'TENTGROW'):
                            if fallback and sound_name == 'TENTGROW':
                                continue
                            sound = env.object(0x20, 'constructor-'+sound_name, fill=0x63)
                            sound_entries.append(('LEVEL_AQUATISTENTACLE_'+sound_name, sound))
                        env.put(manager + 0x28, resource_map('constructor-sounds', sound_entries))
                        image = env.object(0x70, 'tentacle-image', fill=0)
                        image_frame = env.object(0x30, 'tentacle-image-frame', fill=0)
                        env.put(image_frame + 0x18, word(-13), word(-17), 41, 59)
                        image_frames = env.object(4, 'tentacle-image-frames', words=[image_frame])
                        env.put(image + 0x14, image_frames)
                        env.put(manager + 0x10, resource_map('constructor-images', [('LEVEL_AQUATISTENTACLE', image)]))
                        entries = []
                        for name in ('IDLE', 'STRIKE3', 'STRIKE2', 'STRIKE1', 'KILLFALL', 'HIT', 'RESPAWN'):
                            if not fallback:
                                entries.append(('LEVEL_AQUATISTENTACLE_'+name, env.get(obj + 0x400)))
                        entries.append(('GAME_NULL', env.get(obj + 0x404)))
                        env.put(manager + 0x2c, resource_map('animation-resource-map', entries))
                        env.put(0x533470, default_bits)
                        env.write(0x534938, b'\0')
                        env.put(0x53ca30, initial_count)
                        env.put(0x5231dc, 3)
                        return t
                    yield direct(f'constructor fallback {fallback} bits {default_bits} count {initial_count} hp {hp}',
                                 0x4928f0, constructor_setup, (lambda t: t['actor'],))
    yield direct('notice live target type 32 sets flag', 0x4936d0, setup_core(13, state='LS_IDLE', mode=1))
    def unchanged_target(env):
        t = setup_core(19, state='LS_IDLE')(env)
        env.put(t['obj'] + 0x19c, 0)
        return t
    yield direct('notice matching target stays live', 0x4936d0, unchanged_target)
