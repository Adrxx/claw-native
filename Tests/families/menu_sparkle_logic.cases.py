"""Menu sparkle inputs derived from the original actor and animation code."""
from clawparity.cases import Case

ENTRY = 0x45F840
RAND = 0x4A3050


def actor_case(label, state=5, countdown=1234, delta=17, stopped=0,
               pending=0, animation=True, random_value=71, found=False,
               mutate=False, noise=0x93):
    def setup(env):
        actor = env.object(0x220, 'sparkle actor', fill=noise)
        logic = env.object(0x150, 'sparkle logic', fill=noise ^ 0x5A)
        owner = env.object(0x40, 'resource owner', fill=0)
        command = env.object(0x30, 'animation command', fill=0)
        commands = env.object(4, 'command array', words=[command])
        clip = env.object(0x20, 'animation clip', fill=0)
        env.put(clip + 0xC, commands, 1)
        env.put(command + 8, 0, 9, 0, 0, 37, 0x76543210)
        env.put(actor + 0xC, owner)
        env.put(actor + 0x6C, logic)
        env.put(logic + 0x1C, state, 0x2468ACE0)
        env.put(logic + 0x130, countdown)
        control = actor + 0x188
        env.put(control + 4, actor, clip if animation else 0, command,
                0, pending, 1, stopped, 0x12345678, 0xABCDEF01, 0x3F800000)
        sprite = env.object(0x70, 'sprite sequence')
        images = env.object(12, 'images', words=[0x19191919, 0x28282828, 0x37373737])
        env.put(sprite + 0x14, images)
        env.put(sprite + 0x64, 1, 2)
        for offset, name, result in ((0x10, b'MENU_SPARKLE\0', sprite),
                                      (0x2C, b'MENU_FORWARD100\0', clip)):
            resource = env.object(0x20, 'resource hash map', fill=0)
            env.put(resource + 0x18, 1)
            if found:
                key = env.object(len(name), 'resource key', data=name)
                node = env.object(16, 'resource hash node', words=[0, 0, key, result])
                buckets = env.object(4, 'resource buckets', words=[node])
                env.put(resource + 0x14, buckets)
            env.put(owner + offset, resource)
        env.put(0x53720C, delta)
        env.put(0x5430C4, 11)
        def rand(env, call):
            if mutate:
                # Publication before rand, and retained logic pointer, are observable.
                receipt = env.get(logic + 0x1C)
                env.put(logic + 0x24, receipt, env.get(logic + 0x130))
                env.put(actor + 0x6C, 0)
            return random_value
        env.override(RAND, rand)
        return actor
    return Case(label, ENTRY, setup, arguments=(lambda actor: actor,))


def cases(random_source):
    yield Case('null actor', ENTRY, arguments=(0,))
    def missing(env):
        return env.object(0x220, 'actor without logic', fill=0)
    yield Case('null logic', ENTRY, missing, arguments=(lambda actor: actor,))
    for state in (1, 4, 6, 0xFFFFFFFF, 0x80000000):
        yield actor_case(f'inactive state {state:#x}', state=state)
    for value in (0, 1, 4000, 4001, 32767, 0xFFFFFFFF, 0x80000000):
        for found in (False, True):
            yield actor_case(f'initialize rand {value:#x} resources {found}',
                             state=0, random_value=value, found=found)
    yield actor_case('initialization rand observes published state and changes actor link',
                     state=0, mutate=True, found=True)
    for countdown, delta in ((0, 0), (0, 1), (1, 0), (1, 1), (1, 2),
                              (101, 100), (100, 101), (0xFFFFFFFF, 1),
                              (1, 0xFFFFFFFF), (0x80000000, 0x7FFFFFFF)):
        for animation in (False, True):
            yield actor_case(f'timer {countdown:#x} delta {delta:#x} clip {animation}',
                             countdown=countdown, delta=delta, animation=animation)
    for stopped, pending in ((0, 0), (1, 1), (1, 0), (0xFFFFFFFF, 0), (7, 0xFFFFFFFF)):
        for animation in (False, True):
            yield actor_case(f'restart stop {stopped:#x} pending {pending:#x} clip {animation}',
                             stopped=stopped, pending=pending, animation=animation)
    yield actor_case('restart rand retains original logic pointer', stopped=1, mutate=True)
    for i in range(24):
        yield actor_case(f'random sparkle {i}', countdown=random_source.getrandbits(32),
                         delta=random_source.getrandbits(32),
                         stopped=random_source.choice((0, 1, 0x80000000)),
                         pending=random_source.choice((0, 1, 23)),
                         random_value=random_source.getrandbits(32),
                         noise=random_source.randrange(1, 256))
