"""Independent original-behavior cases for scene rectangles and boss music."""
from clawparity.cases import Case

RECT, MANAGER, MUSIC = 0x42A450, 0x42B000, 0x46CAB0
SETRECT = 0x546D5C


def rectangle(words, live=True, alias=None, switch=None, custom=None):
    def setup(env):
        manager = env.object(0x54, 'manager', fill=0xA7)
        scene = env.object(0x28, 'scene', fill=0xB8)
        description = env.object(0x60, 'description', fill=0xC9)
        output = env.object(24, 'output', fill=0xDA) + 4
        env.put(manager + 0x30, scene if live else 0)
        env.put(scene + 0x24, description)
        env.put(description + 0x10, *words)
        if alias is not None:
            output = description + 0x10 + alias
        def set_rect(env, call):
            env.put(call.arguments[0], *(custom if custom is not None else call.arguments[1:]))
            if switch is not None:
                env.put(manager + 0x30, scene if switch else 0)
            return 0x80000000
        env.override(SETRECT, set_rect)
        return {'receiver': manager, 'output': output}
    return setup


def synthetic(modes, result, replace=False):
    def setup(env):
        manager = env.object(0x54, 'manager')
        log = env.object(0x100, 'observations', fill=0)
        interfaces = [env.object(8, f'interface {i}') for i in range(4)]
        def record(env, tag, call):
            index = env.get(log)
            env.put(log + 4 + index * 16, tag, call.receiver, env.get(manager + 0x2c), index)
            env.put(log, index + 1)
        def select(env, call):
            record(env, 0x60, call)
            return result
        select_address = env.stub('select music', 'thiscall', 0, select)
        def mode(env, call):
            record(env, 0x10, call)
            index = sum(env.calls_so_far(a) for a in mode_addresses) - 1
            if replace:
                env.put(manager + 0x2c, interfaces[min(index + 1, 3)])
            return modes[min(index, len(modes) - 1)]
        mode_addresses = []
        for index, interface in enumerate(interfaces):
            table = env.object(0x64, f'table {index}')
            mode_addresses.append(env.stub(f'mode {index}', 'thiscall', 0, mode))
            env.put(table + 0x10, mode_addresses[-1])
            env.put(table + 0x60, select_address)
            env.put(interface, table)
        env.put(manager + 0x2c, interfaces[0] if modes else 0)
        return {'receiver': manager}
    return setup


def music(controller, found=True, enabled=True, context=True, current=True,
          playback=1, nested=False, mutate=False, null_buckets=False, same_track=False):
    def setup(env):
        manager = env.object(0x54, 'manager', fill=0x93)
        interface = env.object(8, 'single-player interface', words=[0x50C264, manager])
        registry = env.object(0x2c, 'registry')
        alternate = env.object(0x2c, 'alternate registry', fill=0x45)
        log = env.object(0x100, 'audio observations', fill=0)
        track = env.object(12, 'boss track', fill=0x67)
        old = track if same_track else env.object(12, 'previous track', fill=0x89)
        methods = env.object(0x34, 'audio methods')
        context_address = env.object(12, 'audio context', fill=0xAB)
        changed_context = env.object(12, 'replacement context', fill=0xCD)
        def record(env, tag, call):
            index = env.get(log)
            env.put(log + 4 + index * 32, tag, call.receiver,
                    env.get(registry + 0x1c), env.get(manager + 0x50),
                    env.get(registry + 0x20), len(call.arguments),
                    *(list(call.arguments) + [0, 0])[:2])
            env.put(log, index + 1)
        def stop(env, call):
            record(env, 0x30, call)
            if mutate:
                env.put(manager + 0x50, alternate)
                env.put(registry + 0x20, changed_context)
                env.put(registry + 0x1c, track)
            return 0xFFFFFFFF
        def start(env, call):
            record(env, 0x24, call)
            if mutate:
                env.put(manager + 0x50, alternate)
                env.put(registry + 0x1c, old)
            return playback
        env.put(methods + 0x30, env.stub('audio stop', 'thiscall', 0, stop))
        env.put(methods + 0x24, env.stub('audio start', 'thiscall', 2, start))
        env.put(track, methods)
        env.put(old, methods)
        bucket_count = 7
        buckets = env.object(4 * bucket_count, 'map buckets', fill=0)
        key = env.object(8, 'boss key', data=b'BOSS\0')
        other_key = env.object(12, 'other key', data=b'OTHER\0')
        node = env.object(16, 'boss node', words=[0, 0x123, key, track])
        decoy = env.object(16, 'decoy node', words=[node if found else 0, 0x456, other_key, old])
        hash_value = 0
        for byte in b'BOSS':
            hash_value = (hash_value * 33 + byte) & 0xffffffff
        env.put(buckets + 4 * (hash_value % bucket_count), decoy)
        env.put(registry + 4, 0 if null_buckets else buckets, bucket_count)
        env.put(registry + 0x1c, old if current else 0,
                context_address if context else 0, 0xBAADF00D, int(enabled))
        env.put(manager + 0x14, controller)
        env.put(manager + 0x2c, interface)
        env.put(manager + 0x50, registry)
        return {'receiver': manager if nested else interface}
    return setup


def cases(random_source):
    for live in (False, True):
        for alias in (None, -4, 0, 4, 8, 12):
            words = [random_source.getrandbits(32) for _ in range(4)]
            yield Case(f'rectangle live={live} alias={alias}', RECT,
                       rectangle(words, live, alias), receiver=lambda t: t['receiver'],
                       arguments=(lambda t: t['output'],))
    for initially_live in (False, True):
        yield Case(f'SetRect replaces link {initially_live}', RECT,
                   rectangle([0x11223344, 0x55667788, 0x99AABBCC, 0xDDEEFF00],
                             initially_live, switch=not initially_live,
                             custom=[0xFEDCBA98, 0x76543210, 0x80000000, 0xFFFFFFFF]),
                   receiver=lambda t: t['receiver'], arguments=(lambda t: t['output'],))
    # SetRect receives the actual local address, so it can publish a scene
    # description whose rectangle overlaps that local. The original snapshots
    # into the local in order, then rereads the source for the heap output.
    for displacement in (-4, 0, 4):
        values = [random_source.getrandbits(32) for _ in range(4)]
        def stack_source(env, displacement=displacement, values=values):
            manager = env.object(0x54, 'stack-alias manager', fill=0xA1)
            scene = env.object(0x28, 'stack-alias scene', fill=0xB2)
            output = env.object(24, 'stack-alias output', fill=0xC3) + 4
            env.put(manager + 0x30, scene)
            def set_rect(env, call):
                temporary = call.arguments[0]
                env.put(temporary, *values)
                if displacement < 0:
                    # This is the backed saved-register slot. Its eventual
                    # restored ESI value is not consumed by the root's caller.
                    env.put(temporary - 4, 0xD4E5F607)
                env.put(scene + 0x24, temporary + displacement - 0x10)
                return 1
            env.override(SETRECT, set_rect)
            return {'receiver': manager, 'output': output}
        yield Case(f'SetRect publishes overlapping stack source {displacement}',
                   RECT, stack_source, receiver=lambda t: t['receiver'],
                   arguments=(lambda t: t['output'],))
    for modes in ((), (3,), (0, 4), (0, 0, 6), (0, 0, 0), (0x100, 0x80000000, 0xFFFFFFFF)):
        for result in (0, 1, 0x100, 0x80000000, 0xFFFFFFFF):
            for replace in (False, True):
                yield Case(f'manager modes={modes} result={result:#x} replace={replace}',
                           MANAGER, synthetic(modes, result, replace), receiver=lambda t: t['receiver'])
    for nested in (False, True):
        for controller in (0, 1, 0x80000000):
            for options in ({}, {'found': False}, {'enabled': False}, {'context': False},
                            {'current': False}, {'playback': 0}, {'playback': 0x80000000},
                            {'playback': 0x100}, {'mutate': True},
                            {'mutate': True, 'playback': 0}, {'null_buckets': True},
                            {'same_track': True}):
                yield Case(f'music nested={nested} controller={controller:#x} {options}',
                           MANAGER if nested else MUSIC,
                           music(controller, nested=nested, **options), receiver=lambda t: t['receiver'])
