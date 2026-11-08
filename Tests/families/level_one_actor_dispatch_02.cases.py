"""Independent original-input cases for Level 1 actor dispatch batch 2."""
import struct

from clawparity.cases import Case


def patterned(env, size, name, salt=0x91A205C7):
    return env.object(size, name, words=[(salt + i * 0x0103070B) & 0xFFFFFFFF
                                        for i in range(size // 4)])


def direct(label, function, setup, arguments=()):
    return Case(label, function, setup, receiver=lambda t: t['receiver'], arguments=arguments)


def physics(constants):
    def setup(env):
        target = patterned(env, 0x100, 'physics')
        env.put(0x513E10, *constants)
        return {'receiver': target}
    return setup


def inventory(values, alias=None):
    def setup(env):
        region = patterned(env, 0x400, 'inventory-region')
        actor = patterned(env, 0x180, 'inventory-actor')
        primary = patterned(env, 0x120, 'inventory-primary')
        target = region + 0x100
        if alias == 'actor':
            actor = target
        elif alias == 'primary':
            # Inventory stores overlap primary F0..10C and force original reloads.
            primary = target - 0xC4
        env.put(actor + 0x6C, primary)
        for offset, value in zip((0xF0, 0xF8, 0xF4, 0xFC, 0x100, 0x108, 0x104, 0x10C), values):
            env.put(primary + offset, value)
        env.put(actor + 0x100, values[8])
        return {'receiver': target, 'actor': actor}
    return setup


def wrapper(copy_source=None, alias_wrapper=False):
    def setup(env):
        actor = patterned(env, 0x200, 'wrapped-actor')
        target = (actor + (0x124 if alias_wrapper == 'position' else 0x114)
                  if alias_wrapper else patterned(env, 0x20, 'wrapper'))
        env.put(target + 4, actor)
        source = (actor + copy_source if copy_source is not None
                  else patterned(env, 0x10, 'copy-source', 0x2301759B))
        return {'receiver': target, 'source': source}
    return setup


def deactivate(y, separate=False, sentinel=False, tile=False, callback_status=1):
    def setup(env):
        wrapper = patterned(env, 0x20, 'deactivate-wrapper')
        actor = patterned(env, 0x180, 'deactivate-actor')
        moved = patterned(env, 0x180, 'moved-actor') if separate else actor
        parent = patterned(env, 0x30, 'deactivate-parent')
        scene = patterned(env, 0x60, 'deactivate-scene')
        env.put(wrapper, actor, moved)
        env.put(actor + 0xC, parent)
        env.put(parent + 0x24, scene)
        env.put(moved + 0x50, y)
        env.put(actor + 0x118, 0x80000000 if sentinel else 0)
        env.put(scene + 0x5C, 0)
        if tile:
            world = env.object(0x94, 'tile-world')
            tiles = env.object(4, 'tile-grid', words=[0])
            rows = env.object(16, 'tile-rows', words=[0, 0, 0, 0])
            tile_object = env.object(4, 'tile-object')
            tile_vtable = env.object(0x24, 'tile-vtable')
            tile_list = env.object(4, 'tile-list', words=[tile_object])
            record = env.object(0x20, 'tile-callback-record', fill=0)
            def collide(env, call):
                count = env.get(record)
                env.put(record, count + 1, call.receiver, *call.arguments,
                        env.get(moved + 0x50), env.get(actor + 0xCC))
                return callback_status
            env.put(tile_vtable + 0x20, env.stub('tile-collision', 'thiscall', 2, collide))
            env.put(tile_object, tile_vtable)
            env.put(world + 0x20, tiles, rows)
            env.put(world + 0x30, 4, 4)
            env.put(world + 0x8C, 2, 2)
            env.put(scene + 0x4C, tile_list)
            env.put(scene + 0x5C, world)
            env.put(actor + 0x4C, 1)
            env.put(actor + 0x50, 33)
            env.put(actor + 0x124, 0)
        return {'receiver': wrapper}
    return setup


def lookup(low, high, index, root_present=True, null_entry=False, alias=False):
    def setup(env):
        target = patterned(env, 0x180, 'lookup-actor')
        root = patterned(env, 0x70, 'lookup-root')
        table = patterned(env, 0x100, 'lookup-table')
        base = table + 0x80
        if alias:
            base = target + 0x16C - index * 4
        if -32 <= index < 32:
            env.put((base + index * 4) & 0xFFFFFFFF,
                    0 if null_entry else 0x8ABCD123)
        env.put(root + 0x14, base)
        env.put(root + 0x64, low, high)
        env.put(target + 0x170, root if root_present else 0)
        return {'receiver': target}
    return setup


def constructor(alias=False, divisor=17):
    def setup(env):
        target = patterned(env, 0x24, 'constructor-result')
        actor = patterned(env, 0x180, 'constructor-actor')
        parent = env.object(0x30, 'resource-parent')
        registry = env.object(0x40, 'empty-resource-registry')
        primary = patterned(env, 0x110, 'constructor-primary')
        if alias:
            target = actor + 0x100
        env.put(actor + 0xC, parent)
        env.put(parent + 0x14, registry)
        env.put(registry + 0x14, 0, divisor)
        env.put(actor + 0x6C, primary)
        return {'receiver': target, 'actor': actor}
    return setup


def resource_constructor(redirect=False, reload_animation=False):
    def setup(env):
        target = patterned(env, 0x24, 'constructor-with-resources')
        actors = [env.object(0x180, f'resource-actor-{n}') for n in range(2)]
        parent = env.object(0x30, 'resource-parent')
        registry = env.object(0x40, 'resource-registry')
        buckets = env.object(4, 'resource-buckets')
        nodes = [env.object(0x10, f'resource-node-{n}') for n in range(2)]
        resources = [env.object(0x14, f'resource-{n}') for n in range(2)]
        record = env.object(0x100, 'animation-observations', fill=0)
        animations = [env.object(4, f'animation-{n}') for n in range(5)]
        vtable = env.object(0x28, 'animation-vtable')
        def observe(env, call):
            count = env.get(record)
            # A fixed-size observation per callback preserves receiver, arguments,
            # the constructor publication prefix and both actor animation pointers.
            slot = record + 4 + count * 32
            env.put(slot, call.receiver, len(call.arguments),
                    *(list(call.arguments) + [0] * (2 - len(call.arguments))),
                    env.get(target + 0xC), env.get(target + 0x10),
                    env.get(actors[0] + 0x70), env.get(actors[0] + 0x78))
            env.put(record, count + 1)
        def reset(env, call):
            observe(env, call)
            if redirect and call.receiver == animations[0]:
                env.put(target + 0xC, actors[1])
            if reload_animation and call.receiver == animations[0]:
                env.put(actors[0] + 0x70, animations[4])
            return 0x87654321
        def load(env, call):
            observe(env, call)
            return 0x12345678
        env.put(vtable + 0x1C, env.stub('animation-reset', 'thiscall', 0, reset))
        env.put(vtable + 0x24, env.stub('animation-load', 'thiscall', 2, load))
        for animation in animations:
            env.put(animation, vtable)
        for n, actor in enumerate(actors):
            env.put(actor + 0xC, parent)
            env.put(actor + 0x6C, 0x12345000 + n * 0x1000,
                    animations[n * 2], 0, animations[n * 2 + 1])
        env.put(parent + 0x14, registry)
        env.put(registry + 0x14, buckets, 1)
        env.put(buckets, nodes[0])
        for n, (node, resource, key) in enumerate(zip(nodes, resources, (0x522D54, 0x522D48))):
            env.put(node, nodes[1] if n == 0 else 0, 0, key, resource)
            env.put(resource + 0x10, 0x76543210 + n * 0x10203)
        env.put(0x540E00, 0)
        return {'receiver': target, 'actor': actors[0]}
    return setup


def cases(random_source):
    for constants in ((0x89ABCDEF, 0x3FF00123, 0x76543210, 0xBFE11234),
                      (0, 0x80000000, 0, 0),
                      tuple(random_source.getrandbits(32) for _ in range(4))):
        yield direct(f'physics initialize constants {constants}', 0x4080A0, physics(constants))
    for n in range(8):
        words = tuple(random_source.getrandbits(32) for _ in range(22))
        yield direct(f'physics twenty-two raw words {n}', 0x408220, physics((1, 2, 3, 4)), words)
    for value in (0.0, -0.0, 1.0, -1.0, 1.0000000000000002, -98765.125, 1e200, 1e-200):
        words = struct.unpack('<II', struct.pack('<d', value))
        yield direct(f'physics triple double {value!r}', 0x4082D0, physics((1, 2, 3, 4)), words)
    special_bits = (
        0x7FF0000000000000, 0xFFF0000000000000,  # infinities
        0x7FF8123456789ABC, 0xFFF8FEDCBA987654,  # quiet NaN payloads
        0x7FF0000000000001, 0xFFF0000000000001,  # smallest signaling payloads
        0x7FF123456789ABCD, 0xFFF23456789ABCDE,  # other signaling payloads
        0x0000000000000001, 0x8000000000000001,  # signed smallest subnormals
        0x7FEFFFFFFFFFFFFF, 0xFFEFFFFFFFFFFFFF,  # signed maximum finite
    )
    for bits in special_bits:
        words = (bits & 0xFFFFFFFF, bits >> 32)
        yield direct(f'physics triple special binary64 {bits:016x}',
                     0x4082D0, physics((1, 2, 3, 4)), words)
    for alias in (False, True):
        for divisor in (1, 17, 257):
            yield direct(f'constructor empty registry alias {alias} divisor {divisor}', 0x4082F0,
                         constructor(alias, divisor), (lambda t: t['actor'],))
    for redirect, reload_animation in ((False, False), (True, False), (False, True), (True, True)):
        yield direct(f'constructor resources redirect {redirect} reload {reload_animation}',
                     0x4082F0, resource_constructor(redirect, reload_animation),
                     (lambda t: t['actor'],))
    patterns = [(0,) * 9, tuple(0x12030405 + i * 0x10101 for i in range(9))]
    patterns += [tuple(0x87654321 if i == j else 0 for i in range(9)) for j in range(9)]
    patterns += [tuple(random_source.getrandbits(32) if random_source.randrange(2) else 0
                       for _ in range(9)) for _ in range(12)]
    for n, values in enumerate(patterns):
        for alias in (None, 'actor', 'primary'):
            yield direct(f'inventory {n} alias {alias}', 0x408370, inventory(values, alias),
                         (lambda t: t['actor'],))
    for n in range(8):
        words = tuple(random_source.getrandbits(32) for _ in range(4))
        yield direct(f'wrapper position {n}', 0x40AB80, wrapper(), words)
        yield direct(f'wrapper position caches overwritten actor pointer {n}',
                     0x40AB80, wrapper(alias_wrapper='position'), words)
        yield direct(f'actor bounds {n}', 0x40F6C0, lambda e: {'receiver': patterned(e, 0x180, 'bounds')}, words)
    for offset in (None, 0x108, 0x10C, 0x110, 0x114, 0x118, 0x11C, 0x120, 0x124, 0x128):
        for alias_wrapper in (False, True):
            yield direct(f'copy bounds source {offset} wrapper overlap {alias_wrapper}', 0x40ABB0,
                         wrapper(offset, alias_wrapper), (lambda t: t['source'],))
    for y in (0, 1, 31, 32, 33, 0x80000000, 0xFFFFFFFF):
        for separate in (False, True):
            yield direct(f'deactivate y {y:#x} separate {separate}', 0x40ABF0, deactivate(y, separate))
    yield direct('deactivate original sentinel return', 0x40ABF0, deactivate(65, sentinel=True))
    for result in (0, 1, 2, 3, 4, 0xFFFFFFFF):
        yield direct(f'deactivate original tile collision {result}', 0x40ABF0,
                     deactivate(33, tile=True, callback_status=result))
    for low, high, indices in ((2, 5, (1, 2, 3, 5, 6)), (-3, 2, (-4, -3, -1, 0, 2, 3)),
                               (7, 7, (6, 7, 8)), (4, -4, (-5, 0, 5)),
                               (0x80000000, 0x7FFFFFFF, (-1, 0, 1))):
        for index in indices:
            yield direct(f'lookup bounds {low} {high} index {index}', 0x4209D0,
                         lookup(low, high, index), (index,))
    for index in (0, -1, 0x80000000, 0x7FFFFFFF):
        yield direct(f'lookup missing root index {index}', 0x4209D0,
                     lookup(0, 0, index, root_present=False), (index,))
    yield direct('lookup null table entry', 0x4209D0, lookup(-1, 1, 0, null_entry=True), (0,))
    yield direct('lookup table aliases stored index', 0x4209D0, lookup(-1, 1, 0, alias=True), (0,))
