"""Original-only cases for pickup point actors and image selection."""
from clawparity.cases import Case

FRAME = 0x40F680
SPAWN = 0x4737C0
UPDATE = 0x473A70
SELECT = 0x4C7900
FIRST = 0x4C7970


def string_map(env, owner, name, value):
    """The actual original one-bucket string map, including a nonmatching node."""
    bucket = env.object(4, 'bucket', fill=0)
    env.put(owner + 0x14, bucket, 1)
    env.put(bucket, 0)
    if value is not None:
        node = env.object(16, 'matching-node', fill=0)
        key = env.object(len(name) + 1, 'map-key', data=name + b'\0', fill=0)
        env.put(node, 0)
        env.put(node + 8, key, value)
        decoy = env.object(16, 'decoy-node', fill=0)
        other = env.object(6, 'decoy-key', data=b'OTHER\0', fill=0)
        env.put(decoy, node)
        env.put(decoy + 8, other, 0x76543210)
        env.put(bucket, decoy)
    env.put(0x540E00, 0)


def collection(env, low, high, words, address=None):
    image = address if address is not None else env.object(0x6C, 'collection', fill=0)
    table = env.object(128 * 4, 'absolute-frame-table', words=words, fill=0)
    env.put(image + 0x14, table + 64 * 4)
    env.put(image + 0x64, low & 0xFFFFFFFF, high & 0xFFFFFFFF)
    return image


def selector_setup(low, high, words, missing=False, alias=False, name=b'GAME_POINTS'):
    def setup(env):
        actor = env.object(0x1B4, 'actor', fill=0)
        world = env.object(0x40, 'world', fill=0)
        manager = env.object(0x50, 'image-manager', fill=0)
        env.put(actor + 0x0C, world)
        env.put(actor + 0x16C, 0x24681357, 0x13572468, 0xABCDEF19)
        env.put(world + 0x10, manager)
        image = collection(env, low, high, words, actor + 0x107 if alias else None)
        string_map(env, manager, name, None if missing else image)
        key = env.object(len(name) + 1, 'requested-name', data=name + b'\0', fill=0)
        return {'actor': actor, 'name': key}
    return setup


def spawn_setup(points, low, high, words, missing=False, no_logic=False, xy=(37, 59), change=None):
    def setup(env):
        source = env.object(0x100, 'pickup-source', fill=0)
        world = env.object(0x80, 'world', fill=0)
        manager = env.object(0x80, 'actor-manager', fill=0)
        logic = env.object(0x50, 'logic-manager', fill=0)
        images = env.object(0x50, 'image-manager', fill=0)
        descriptor = env.object(0x20, 'PointsIcon-descriptor', fill=0)
        free_node = env.object(12, 'free-list-node', fill=0)
        env.put(source + 0x0C, world)
        env.put(source + 0x4C, xy[0] & 0xFFFFFFFF, xy[1] & 0xFFFFFFFF)
        env.put(source + 0xFC, points & 0xFFFFFFFF)
        env.put(world + 8, manager, 0, images, logic)
        env.put(manager + 0x0C, world)
        env.put(manager + 0x14, 0, 0, 0)
        env.put(manager + 0x20, free_node)
        env.put(free_node, 0, 0, 0)
        env.put(manager + 0x28, 1)
        env.put(descriptor + 8, 0x1280)
        env.put(descriptor + 0x10, 1)
        string_map(env, logic, b'PointsIcon', None if no_logic else descriptor)
        image = collection(env, low, high, words)
        string_map(env, images, b'GAME_POINTS', None if missing else image)
        if change is not None:
            def allocation(env, call):
                env.put(source + 0xFC, change)
                return env.object(call.arguments[0], 'factory-allocation', fill=0)
            env.override(0x4F63EC, allocation)
        return source
    return setup


def update_setup(status, flags, finished, duration, delta, live=False, timed=False):
    def setup(env):
        actor = env.object(0x1B4, 'actor', fill=0)
        state = env.object(0x174, 'state', fill=0)
        world = env.object(0x50, 'world', fill=0)
        manager = env.object(0x50, 'animation-manager', fill=0)
        env.put(actor + 8, flags, world)
        env.put(actor + 0x6C, state)
        env.put(state + 0x1C, status & 0xFFFFFFFF)
        env.put(actor + 0x19C, duration & 0xFFFFFFFF, int(timed), finished)
        env.put(world + 0x2C, manager)
        string_map(env, manager, b'GAME_POINTS', None)
        env.put(0x5430C4, delta)
        if live:
            sequence = env.object(0x20, 'sequence', fill=0)
            env.put(actor + 0x190, sequence)
            record = env.object(0x30, 'animation-record', fill=0)
            env.put(actor + 0x194, record)
            env.put(actor + 0x18C, actor)
            env.put(actor + 0x1B0, 0x3F800000)
            env.put(record + 0x0C, 9)
            env.put(record + 0x18, 7)
        return actor
    return setup


def cases(random_source):
    words = [random_source.getrandbits(32) | 1 for _ in range(128)]
    for low, high in ((0, 9), (-5, 3), (2, 2), (3, 2)):
        for index in (low - 1, low, high, high + 1, -0x80000000, 0x7FFFFFFF):
            def setup(env, low=low, high=high):
                return collection(env, low, high, words)
            yield Case(f'frame bounds {low}..{high} index {index}', FRAME, setup,
                       receiver=lambda t: t, arguments=(index & 0xFFFFFFFF,))
    for entry in (SELECT, FIRST):
        for low, high, index in ((0, 9, 0), (-5, 3, -5), (-5, 3, 3), (2, 2, 2),
                                 (3, 2, 1), (3, 2, 3), (-5, 3, -6), (-5, 3, 4),
                                 (0, 9, -0x80000000), (0, 9, 0x7FFFFFFF)):
            for missing in (False, True):
                yield Case(f'select {entry:x} {low}..{high} at {index} missing {missing}', entry,
                           selector_setup(low, high, words, missing), receiver=lambda t: t['actor'],
                           arguments=(lambda t: t['name'],) + ((index & 0xFFFFFFFF,) if entry == SELECT else ()))
    yield Case('first index store increases overlapping minimum', FIRST,
               selector_setup(1, 9, words, alias=True), receiver=lambda t: t['actor'],
               arguments=(lambda t: t['name'],))
    for entry in (SELECT, FIRST):
        def aliased_table(env):
            tokens = selector_setup(2, 9, words)(env)
            actor = tokens['actor']
            world = env.get(actor + 0x0C)
            manager = env.get(world + 0x10)
            bucket = env.get(manager + 0x14)
            decoy = env.get(bucket)
            matching = env.get(decoy)
            image = env.get(matching + 0x0C)
            # The selected frame aliases the index publication slot. Explicit
            # selection reads it before publishing; first selection reads after.
            env.put(image + 0x14, actor + 0x16C - 2 * 4)
            return tokens
        yield Case(f'selection publication table alias {entry:x}', entry, aliased_table,
                   receiver=lambda t: t['actor'],
                   arguments=(lambda t: t['name'],) + ((2,) if entry == SELECT else ()))
    for index, points in enumerate((100, 500, 1500, 2500, 5000, 7500, 10000, 15000, 25000), 1):
        for low, high, missing in ((0, 10, False), (index, index, False),
                                   (index + 1, 10, False), (0, index - 1, False), (0, 10, True)):
            yield Case(f'spawn {points} range {low}..{high} missing {missing}', SPAWN,
                       spawn_setup(points, low, high, words, missing), arguments=(lambda t: t,))
    for points in (-0x80000000, -1, 0, 1, 99, 101, 499, 501, 1499, 1501, 2499, 2501,
                   4999, 5001, 7499, 7501, 9999, 10001, 14999, 15001, 24999, 25001, 0x7FFFFFFF):
        yield Case(f'fallback points {points}', SPAWN, spawn_setup(points, 0, 9, words), arguments=(lambda t: t,))
    yield Case('missing PointsIcon returns null factory', SPAWN,
               spawn_setup(100, 0, 9, words, no_logic=True), arguments=(lambda t: t,))
    yield Case('points reread after actual factory allocations', SPAWN,
               spawn_setup(100, 0, 9, words, change=25000, xy=(-17, 891)), arguments=(lambda t: t,))
    for status in (0, 1, 4, 5, 6, -1, -0x80000000):
        for finished, duration in ((0, 0), (1, 0), (1, 7), (0x80000000, -1)):
            flags = random_source.getrandbits(32) & ~0x10021
            yield Case(f'update status {status} finished {finished} duration {duration}', UPDATE,
                       update_setup(status, flags, finished, duration, 3), arguments=(lambda t: t,))
    for timed in (False, True):
        for delta in (0, 1, 3, 0xFFFFFFFF):
            yield Case(f'live animator decrement timed {timed} delta {delta}', UPDATE,
                       update_setup(5, 0x81248042, 0, 11, delta, live=True, timed=timed),
                       arguments=(lambda t: t,))
    for status, flags in ((0, 0xFFFFFFFF), (5, 0xFFFFFFFF), (5, 0), (0, 0)):
        yield Case(f'update existing flags status {status} flags {flags:x}', UPDATE,
                   update_setup(status, flags, 1, 0, 17), arguments=(lambda t: t,))
