"""Original v1.3 contact dispatcher inputs; real helpers traverse real tile worlds."""
from clawparity.cases import Case

DISPATCH = 0x4CC920


def world(env, movement=1, current=(40, 53), flags=0, manager_flags=0,
          terrain='empty', bounds=(-2, -3, 3, 4), step=2, mutation=None):
    manager = env.object(0x100, 'manager', fill=0x37)
    plane = env.object(0xa0, 'plane', fill=0x63)
    actor = env.object(0x180, 'actor', fill=0x57)
    scene = env.object(0x40, 'scene', fill=0x91)
    objects = env.object(0x40, 'scene objects', fill=0x29)
    trace = env.object(0x2020, 'classification observations', fill=0)
    env.put(manager + 8, manager_flags, scene)
    env.put(scene + 8, objects)
    env.put(objects + 0x14, 0)
    env.put(manager + 0x5c, plane)
    env.put(manager + 0x64, 8, 11)
    env.put(plane + 0x30, 128, 128)
    env.put(plane + 0x8c, 3, 3)
    cells = []
    for row in range(16):
        for col in range(16):
            value = 0
            if terrain == 'floor': value = int(row >= 8)
            elif terrain == 'roof': value = int(row == 4)
            elif terrain == 'walls': value = int(col in (3, 7))
            elif terrain == 'ladder': value = 3 if col in (4, 5, 6) else 0
            elif terrain == 'hazard': value = 4
            elif terrain == 'solid': value = 1
            elif terrain == 'oneway': value = 2 if row >= 8 else 0
            elif terrain == 'pattern': value = (row * 3 + col) % 5
            elif terrain == 'sentinel': value = 0xEEEEEEEE if (row + col) % 2 else 0xFFFFFFFF
            cells.append(value if value > 4 else value | ((row * 17 + col + 1) << 16))
    data = env.object(16 * 16 * 4, 'tile data', words=cells)
    rows = env.object(16 * 4, 'tile rows', words=[row * 16 for row in range(16)])
    env.put(plane + 0x20, data, rows)
    table = env.object(5 * 4, 'tile objects', fill=0)
    env.put(manager + 0x4c, table)
    for kind in range(5):
        tile = env.object(16, f'tile {kind}', fill=0x40 + kind)
        methods = env.object(0x20, f'tile methods {kind}', fill=0)
        env.put(tile, methods, 8 + kind)
        env.put(table + kind * 4, tile)
        def classify(e, call, kind=kind):
            count = e.get(trace)
            e.put(trace, count + 1)
            slot = trace + 0x20 + (count % 256) * 32
            e.put(slot, call.receiver, *call.arguments, e.get(actor + 8),
                  e.get(actor + 0xe4), e.get(actor + 0x5c), e.get(actor + 0x60), kind)
            if count == 0 and mutation is not None:
                field, value = mutation
                e.put(actor + field, value)
            return kind
        env.put(methods + 0x18, env.stub(f'classify tile {kind}', 'thiscall', 2, classify))
    env.put(actor + 8, flags)
    env.put(actor + 0x5c, *current)
    env.put(actor + 0x90, 0, 0x18374A6B, 0)
    env.put(actor + 0xe4, movement, 0x80)
    env.put(actor + 0xf4, 0, step, step + 1)
    env.put(actor + 0x134, *bounds)
    return dict(manager=manager, actor=actor)


def dispatch(label, proposed=(43, 51), **settings):
    options = settings.pop('options', 0)
    return Case(label, DISPATCH, lambda env: world(env, **settings),
                receiver=lambda t: t['manager'],
                arguments=(lambda t: t['actor'], *proposed, options))


def cases(random_source):
    # Every switch arm, each independent postprocessing flag, and both axes of
    # the unchanged-position test. Unknown types must leave coordinates alone.
    for movement in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, -1, 0x80000000):
        for delta in ((0, 0), (3, 0), (0, 5), (-3, -5)):
            for flags in (0, 0x400000, 0x10, 0x400010):
                yield dispatch(f'mode {movement} delta {delta} flags {flags:x}',
                               movement=movement, flags=flags,
                               proposed=(40 + delta[0], 53 + delta[1]))
    # Exact alternate-bit selection, including other low/high manager bits.
    for manager_flags in (1, 2, 8, 0x80000000, 4, 5, 0x80000004, 0xFFFFFFFF):
        for movement in (0, 1, 2, 3, 7, 8):
            yield dispatch(f'manager {manager_flags:x} mode {movement}',
                           manager_flags=manager_flags, movement=movement,
                           flags=0x400010, proposed=(46, 49), options=0xA0234B5C)
    # Natural ceiling/floor transitions distinguish modes 3, 4 and 8 and test
    # the returned collision mask together with flags produced by helpers.
    for terrain, current, proposed in (
            ('roof', (43, 53), (43, 36)),
            ('floor', (43, 53), (43, 69)),
            ('oneway', (43, 53), (43, 69)),
            ('walls', (40, 53), (62, 53)),
            ('walls', (40, 53), (22, 53)),
            ('hazard', (43, 53), (43, 59)),
            ('ladder', (43, 53), (44, 49)),
            ('sentinel', (43, 53), (44, 49))):
        for movement in (1, 2, 3, 4, 5, 6, 8):
            for options in (0, 1, 2, 0x11):
                yield dispatch(f'{terrain} mode {movement} options {options:x}',
                               terrain=terrain, current=current, proposed=proposed,
                               movement=movement, options=options)
    # Fixture changes survive in memory, never hidden inside assertions.
    # These expose cached pre-helper flags/state and premature publication.
    for movement in (1, 2, 3, 4, 5, 6, 8):
        for field, value in ((8, 0x400010), (8, 0), (0xe4, 1), (0xe4, 4), (0xe4, 7)):
            yield dispatch(f'callback changes {field:x} to {value:x} mode {movement}',
                           movement=movement, flags=0x400010 if value == 0 else 0,
                           mutation=(field, value), proposed=(40, 50))
    # A signed Y comparison has different behavior either side of zero. Empty
    # spans bound the original helper loops even for extreme coordinates.
    for current_y, target_y in ((0, -1), (-1, 0), (0x7FFFFFFF, 0x80000000),
                                (0x80000000, 0x7FFFFFFF), (0x80000000, 0x80000000)):
        yield dispatch(f'signed mode 8 {current_y:x} to {target_y:x}', movement=8,
                       current=(41, current_y), proposed=(41, target_y), bounds=(3, 0, -2, 0))
    for n in range(24):
        x = random_source.randrange(20, 100)
        y = random_source.randrange(20, 100)
        yield dispatch(f'random world {n}', movement=random_source.randrange(1, 9),
                       current=(x, y), proposed=(x + random_source.randrange(-8, 9),
                                               y + random_source.randrange(-8, 9)),
                       terrain=random_source.choice(('empty', 'floor', 'roof', 'walls', 'pattern')),
                       flags=random_source.choice((0, 0x10, 0x400000, 0x400010)),
                       options=random_source.choice((0, 1, 2, 8, 0x11, 0x12)),
                       step=random_source.randrange(1, 5))
