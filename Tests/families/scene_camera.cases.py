"""Independent scene cases derived from the hash-verified original packet."""
import struct
from clawparity.cases import Case


def f32(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def plane(env, flags=0, xy=(177.75, 213.25), world=(1009, 811), view=(127, 93), scale=(0.625, 1.375)):
    p = env.object(0x90, 'plane', fill=0xA7)
    env.put(p + 8, flags)
    env.put(p + 0x10, f32(xy[0]), f32(xy[1]), f32(scale[0]), f32(scale[1]))
    env.put(p + 0x30, *world)
    env.put(p + 0x70, *view, int(view[0] / 2), int(view[1] / 2))
    return p


def scene(env, count=3, primary=1, flags=0):
    s = env.object(0x64, 'scene', fill=0x6D)
    ps = [plane(env, flags=flags if i == primary else (1 if i == 0 else 12), scale=(0.375 + i / 2, 1.125 + i / 4)) for i in range(3)]
    array = env.object(12, 'plane array', words=ps)
    env.put(s + 0x38, array, count)
    env.put(s + 0x5C, ps[primary], primary)
    return s


def camera_setup(state=24, player_state=0, suppression=0, movement=0, current=(121, 191), player_xy=(221, 291), override=-1, lock=0, target_kind='valid', mask=0, count=3, flags=0, shake=False, null_state=False, allocation_change=None):
    def setup(env):
        s = scene(env, count=count, flags=flags)
        container = env.object(0x28, 'scene container', fill=0x2B)
        env.put(container + 0x24, s)
        actor = env.object(0x70, 'camera actor', fill=0x3C)
        logic = env.object(0x20, 'camera logic', fill=0x4D)
        st = env.object(0x14, 'camera state', words=[*current, 333, 444, 0 if shake else 53])
        env.put(logic + 0x14, 0 if null_state else st)
        env.put(logic + 0x1C, state)
        env.put(actor + 0xC, container)
        env.put(actor + 0x6C, logic)
        player = env.object(0xD0, 'player', fill=0x5E)
        plogic = env.object(0x20, 'player logic', fill=0x6F)
        private = env.object(0x114, 'player private', fill=0x71)
        env.put(private + 0x110, suppression)
        env.put(plogic + 0x14, private)
        env.put(plogic + 0x1C, player_state)
        env.put(player + 0x4C, *player_xy)
        env.put(player + 0x6C, plogic)
        env.put(player + 0xCC, movement)
        binding = env.object(0x74, 'lock input', fill=0x82)
        env.put(binding + 8, mask)
        target = env.object(0x54, 'target', fill=0x93)
        env.put(target + 0x4C, 341, 467)
        target_pointer = env.object(4, 'target pointer', words=[0 if target_kind == 'null target' else target])
        holder = env.object(0x18, 'lock holder', fill=0xA4)
        env.put(holder + 0x14, 0 if target_kind == 'null holder' else target_pointer)
        env.put(0x537E88, player)
        env.put(0x537204, binding)
        env.put(0x52BE14, override, 387)
        env.put(0x53C25C, lock, 2000 if shake else 0, 0 if target_kind == 'absent' else holder)
        env.put(0x5430C4, 17, 1000)
        env.override(0x4A3050, lambda e, c: (13, 31, 47)[(e.calls_so_far(0x4A3050) - 1) % 3])
        if allocation_change:
            def allocate_changed(e, call):
                out = e.object(call.arguments[0], 'new camera state', fill=0xB5)
                e.put(0x52BE14, *allocation_change)
                return out
            env.override(0x4F63EC, allocate_changed)
        return {'actor': actor, 'scene': s, 'logic': logic, 'state': st}
    return setup


def input_setup(modal=0, timeout=0, elapsed=1, modes=1, held=False, retained=False, suppress_post=0, mouse=(-71, 83), mutate=False):
    def setup(env):
        device = env.object(0x248, 'input source', fill=0)
        binding = env.object(0x74, 'input bindings', fill=0xC6)
        actor = env.object(0x768, 'scene input receiver', fill=0xD7)
        parent = env.object(0x50, 'scene input parent', fill=0xE8)
        dialog = env.object(0x34, 'modal', fill=0xF9)
        window = env.object(8, 'window', words=[0xABCD1234, 0x145289AB])
        receipt = env.object(0x800, 'platform observations', fill=0)
        env.put(actor + 4, parent)
        env.put(actor + 0x764, timeout)
        env.put(parent + 4, window)
        env.put(parent + 0x4C, dialog)
        env.put(dialog + 0x30, modal)
        env.put(binding, device, 0x12345678, 0xABCDEF09, 0xF0003FF if retained else 0x80000010)
        env.put(binding + 0x10, *[1 << i for i in range(10)])
        env.put(binding + 0x38, *range(100, 114))
        env.put(device, 7)
        env.put(device + 0x40, 9)
        env.put(device + 0x1CC, modes, 1, 1, 0)
        env.put(device + 0x1DC, *range(200, 212))
        env.put(device + 0x20C, 0xF00001FF if retained else 0x40000010, 0xBADDCAFE, 0xC001D00D)
        env.put(device + 0x220, 200, 800, 300, 900, *mouse, 17, 23, 513, 385)
        env.put(0x537200, device, binding)
        env.put(0x53720C, elapsed)
        env.put(0x537258, suppress_post)

        def record(e, tag, values):
            n = e.get(receipt)
            e.put(receipt, n + 1)
            at = receipt + 4 + n * 40
            e.put(at, tag, *values, e.get(actor + 0x764), e.get(binding + 4), e.get(binding + 8), e.get(device + 0x210))

        def key(e, call):
            code = call.arguments[0]
            record(e, 1, [call.receiver, code])
            if mutate and e.calls_so_far(0x546CE4) == 1:
                e.put(actor + 0x764, 0x1357)
            return 0xDEAD8001 if held else 0xFFFF0000

        def cursor(e, call):
            record(e, 2, [call.receiver, call.arguments[0]])
            e.put(call.arguments[0], 123456789, -987654321)
            return 0

        def warp(e, call):
            record(e, 3, [call.receiver, *call.arguments])
            return 0

        def metrics(e, call):
            record(e, 4, [call.receiver, *call.arguments])
            return 1027 if call.arguments[0] == 0 else 771

        def joy(e, call):
            record(e, 5, [call.receiver, *call.arguments, e.get(call.arguments[1] + 4)])
            e.put(call.arguments[1] + 8, 51, 1001, 0x1234, 0x2345, 0x3456, 0x4567, 0x1FF)
            return 9

        def post(e, call):
            record(e, 6, [call.receiver, *call.arguments])
            return 0

        for address, effect in ((0x546CE4, key), (0x546CD0, cursor), (0x546D9C, warp), (0x546C44, metrics), (0x546DE8, joy), (0x546D50, post)):
            env.override(address, effect)
        return {'actor': actor}
    return setup


def cases(random_source):
    for flags in (0, 4, 8, 12):
        for xy in ((-2019.5, -1625.75), (-0.25, -0.75), (0, 0), (20.75, 41.5), (504.5, 405.5), (1008.75, 810.75), (1009, 811), (4040.25, 3247.5)):
            def setup(env, flags=flags, xy=xy):
                return plane(env, flags=flags, xy=xy)
            yield Case(f'plane flags {flags} coordinates {xy}', 0x4D0A60, setup, receiver=lambda p: p)
    for _ in range(35):
        flags = random_source.choice((0, 4, 8, 12))
        world = (random_source.randrange(1, 20000), random_source.randrange(1, 20000))
        xy = (random_source.uniform(-2, 3) * world[0], random_source.uniform(-2, 3) * world[1])
        view = (random_source.randrange(1, 1200), random_source.randrange(1, 900))
        yield Case(f'random plane {flags} {world} {xy}', 0x4D0A60, lambda e, f=flags, x=xy, w=world, v=view: plane(e, flags=f, xy=x, world=w, view=v), receiver=lambda p: p)
    for world, xy in (((16777217, 16777219), (33554432., -33554432.)), ((2147483647, 2147483645), (2147483648., 2147483648.))):
        for flags in (0, 12):
            yield Case(f'wide dimension rounding {world} flags {flags}', 0x4D0A60, lambda e, w=world, x=xy, f=flags: plane(e, flags=f, xy=x, world=w), receiver=lambda p: p)
    for rect in ((0x80000000,), (11, 17, 135, 109), (-19, -31, -23, -39), (9, 13, 9, 13), (0x7FFFFFFF, 23, 0x80000000, 25)):
        for result in (0, 1):
            def setup(env, rect=rect, result=result):
                p = plane(env)
                r = env.object(len(rect) * 4, 'rectangle', words=rect)
                receipt = env.object(16, 'rectangle copy receipt', fill=0)
                def copy(e, c):
                    e.put(receipt, c.receiver, *c.arguments)
                    e.write(c.arguments[0], e.read(c.arguments[1], 16))
                    return result
                env.override(0x546D58, copy)
                return (p, r)
            yield Case(f'rectangle {rect} CopyRect return {result}', 0x4D0C50, setup, receiver=lambda t: t[0], arguments=(lambda t: t[1],))
    for count in (-1, 0, 1, 3):
        for flags in (0, 1):
            yield Case(f'scene propagation count {count} flags {flags}', 0x42D5F0, lambda e, c=count, f=flags: scene(e, count=c, flags=f), receiver=lambda s: s, arguments=(-1357, 2011))
    for args in ((0, 90, 9), (1, 0, 1), (0, 9, 1), (0, 9, 9), (0, 9, 10), (0, 0, 0), (0, 0xFFFFFFFF, 1)):
        modal, timeout, elapsed = args
        yield Case(f'input scene modal timeout elapsed {args}', 0x46C860, input_setup(modal=modal, timeout=timeout, elapsed=elapsed, modes=5, held=True), receiver=lambda t: t['actor'])
    for modes in (0, 1, 4, 2, 7):
        for held in (False, True):
            for retained in (False, True):
                for suppressed in (0, 1):
                    yield Case(f'active scene modes {modes} held {held} retained {retained} suppressed {suppressed}', 0x46C860, input_setup(modes=modes, held=held, retained=retained, suppress_post=suppressed), receiver=lambda t: t['actor'])
    yield Case('reset callback mutates scene timeout after modal branch', 0x46C860, input_setup(modal=1, timeout=93, modes=1, mutate=True), receiver=lambda t: t['actor'])
    for mask, kind in ((0, 'valid'), (1, 'valid'), (0x1000000, 'valid'), (0, 'null holder'), (0, 'null target'), (0, 'absent')):
        for count, flags in ((0, 0), (3, 0), (3, 1)):
            yield Case(f'lock target {kind} mask {mask} count {count} flags {flags}', 0x486D70, camera_setup(mask=mask, target_kind=kind, count=count, flags=flags), arguments=(lambda t: t['actor'],))
    def reset(env):
        env.put(0x53C25C, 0xDEADBEEF, 0x11223344, 0xABCDEF01)
    yield Case('release camera lock preserves shake deadline', 0x486D30, reset)
    def absent(env):
        env.put(0x537E88, 0)
        return 0
    yield Case('camera absent player', 0x486240, absent, arguments=(lambda t: t,))
    yield Case('camera dispatches lock routine', 0x486240, camera_setup(lock=1), arguments=(lambda t: t['actor'],))
    for state in (0, 1, 24, 26, 0x138B, 0x22B8, 0xFFFFFFFF):
        for player_state, suppression in ((0, 0), (26, 0), (26, 1), (0x138B, 0), (0x138B, 1), (0x138C, 0)):
            for movement in (0, 3, 4, 8):
                yield Case(f'camera state {state} player {player_state} suppression {suppression} movement {movement}', 0x486240, camera_setup(state=state, player_state=player_state, suppression=suppression, movement=movement), arguments=(lambda t: t['actor'],))
    for current in ((-1000, 291), (221, -1000), (721, 791), (722, 291), (221, 792), (-279, -209), (0x80000000, 291)):
        yield Case(f'camera follow distance {current}', 0x486240, camera_setup(current=current), arguments=(lambda t: t['actor'],))
    for change in ((387, 431), (1001, 431), (221, 1001)):
        yield Case(f'camera allocation callback changes override {change}', 0x486240, camera_setup(state=0, allocation_change=change), arguments=(lambda t: t['actor'],))
    for override in (-1, 0, 513):
        yield Case(f'camera override {override}', 0x486240, camera_setup(state=24, override=override, shake=True), arguments=(lambda t: t['actor'],))
    yield Case('camera unknown state without private state', 0x486240, camera_setup(state=1, null_state=True), arguments=(lambda t: t['actor'],))
    for _ in range(20):
        cur = (random_source.randrange(-700, 700), random_source.randrange(-700, 700))
        xy = (random_source.randrange(-700, 700), random_source.randrange(-700, 700))
        yield Case(f'random camera distances {cur} {xy}', 0x486240, camera_setup(current=cur, player_xy=xy, movement=random_source.choice((0, 3, 4, 8))), arguments=(lambda t: t['actor'],))
    for xy in ((float('nan'), 51.25), (47.5, float('nan')), (float('inf'), float('-inf')), (float('-inf'), float('inf')), (-0.0, -0.0)):
        yield Case(f'nonlooping IEEE coordinates {xy}', 0x4D0A60, lambda e, x=xy: plane(e, xy=x), receiver=lambda p: p)
    for coordinates in ((16777217, 16777219), (-16777217, -16777219), (0x7FFFFFFF, -0x80000000)):
        yield Case(f'scene scales exact signed integers {coordinates}', 0x42D5F0, lambda e: scene(e, count=0, flags=0), receiver=lambda s: s, arguments=coordinates)
    for flags in (0, 1):
        def setup(env, flags=flags):
            tokens = camera_setup(count=0, flags=flags)(env)
            holder = env.get(0x53C264)
            target = env.get(env.get(holder + 0x14))
            env.put(target + 0x4C, 16777217, -16777219)
            return tokens
        yield Case(f'lock scales exact signed target coordinates flags {flags}', 0x486D70, setup, arguments=(lambda t: t['actor'],))
    for view in ((0, 0), (1, 1), (-1, -3), (2000, 1600)):
        yield Case(f'plane signed and oversize view {view}', 0x4D0A60, lambda e, v=view: plane(e, view=v), receiver=lambda p: p)
    # Exact viewport edges distinguish strict signed comparisons after __ftol.
    for flags in (0, 4, 8, 12):
        for xy in ((63., 46.), (63.75, 46.75), (946., 765.), (945., 764.), (947., 766.)):
            yield Case(f'exact viewport edge flags {flags} center {xy}', 0x4D0A60, lambda e, f=flags, x=xy: plane(e, flags=f, xy=x), receiver=lambda p: p)
    for xy in ((-1009., -811.), (-2018., -1622.), (2018., 1622.)):
        yield Case(f'wrap exact multiple {xy}', 0x4D0A60, lambda e, x=xy: plane(e, flags=12, xy=x), receiver=lambda p: p)
    for dx, dy in ((500, 0), (-500, 0), (0, 500), (0, -500), (499, 499), (501, 0), (0, 501)):
        yield Case(f'exact camera distance threshold {dx} {dy}', 0x486240, camera_setup(current=(221 + dx, 291 + dy)), arguments=(lambda t: t['actor'],))
    for timer in (16, 17, 18):
        def setup(env, timer=timer):
            tokens = camera_setup(state=1, shake=True)(env)
            env.put(tokens['state'] + 0x10, timer)
            return tokens
        yield Case(f'exact shake timer threshold {timer}', 0x486240, setup, arguments=(lambda t: t['actor'],))
