"""Original-backed game image cases; only physical DirectDraw methods are stubs."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt

NEW = 0x4F63EC


def quiet(env):
    env.put(0x54139C, 0, 0, 0, 0)
    env.put(0x54138C, 0)


def physical(env, width=8, height=3, depth=8, create_result=0, desc_result=0,
             locks=(0,), unlock=0, stop_unlock=False, color_result=0, restore=None):
    """Real game vtables dispatch into a bounded physical DirectDraw interface."""
    quiet(env)
    log = env.object(1024, 'physical-call-record', fill=0)
    pixels = env.object(8192, 'distinct-pixel-backing', data=bytes((i * 37 + 19) % 256 for i in range(8192)))
    interface = env.object(4, 'DirectDrawSurface')
    methods = env.object(132, 'DirectDrawSurface-vtable', fill=0)
    device = env.object(4, 'DirectDraw')
    device_methods = env.object(100, 'DirectDraw-vtable', fill=0)
    manager = env.object(0x900, 'image-manager', fill=0)
    target = env.object(188, 'game-surface', fill=0xA7)
    env.put(target, 0x513690)
    env.put(target + 8, interface)
    env.put(target + 0x14, height, width, width * max(1, depth // 8) + 3)
    env.put(target + 0x30, pixels)
    env.put(target + 0x60, depth)
    env.put(target + 0x78, 0)
    env.put(target + 0x90, 0x51079C, 0, 0, 0, 0)
    env.put(target + 0xA4, depth, width * max(1, depth // 8), max(1, depth // 8))
    env.put(target + 0xB0, width + 3, 0, 0)
    env.put(interface, methods)
    env.put(device, device_methods)
    env.put(manager, device)
    env.put(manager + 0x474, depth)
    env.put(manager + 0x878, 1)
    # A prepared free node keeps MFC's genuine AddTail within its ordinary domain.
    node = env.object(36, 'list-free-nodes', fill=0)
    env.put(node, node + 12)
    env.put(node + 12, node + 24)
    env.put(manager + 0x3B8, 0x5107C0, 0, 0, 0, node, 0, 3)

    def record(env, call, tag, pointed=()):
        n = env.get(log)
        base = log + 4 + n * 80
        env.put(base, tag, call.receiver, len(call.arguments), *call.arguments)
        at = base + 32
        for addr, length in pointed:
            env.write(at, env.read(addr, length))
            at += length
        env.put(log, n + 1)

    def create(env, call):
        record(env, call, 1, ((call.arguments[1], 28),))
        if not create_result:
            env.put(call.arguments[2], interface)
        return create_result

    def describe(env, call):
        record(env, call, 2, ((call.arguments[1], 4),))
        descriptor = call.arguments[1]
        env.put(descriptor + 8, height, width, width * max(1, depth // 8) + 3)
        env.put(descriptor + 0x54, depth)
        env.put(descriptor + 0x24, pixels)
        return desc_result

    def lock(env, call):
        record(env, call, 3)
        result = locks[min(env.calls_so_far(call.function) - 1, len(locks) - 1)]
        if result == 0:
            env.put(call.arguments[2] + 0x24, pixels)
        return result

    def unlock_effect(env, call):
        record(env, call, 4)
        if stop_unlock:
            return halt()(env, call)
        return unlock

    def color(env, call):
        record(env, call, 5, ((call.arguments[2], 8),))
        return color_result

    def blit(env, call):
        record(env, call, 6, ((call.arguments[4], 16),))
        return 0

    def blit_rect(env, call):
        record(env, call, 7, ((call.arguments[1], 16), (call.arguments[3], 16)))
        return 0

    if restore is not None:
        def restore_callback(env, call):
            record(env, call, 8)
            return restore
        env.put(target + 0xB4, env.stub('supplied-restore-callback', 'cdecl', 1, restore_callback))
    env.put(device_methods + 0x18, env.stub('DirectDraw.CreateSurface', 'stdcall', 4, create))
    for offset, name, argc, effect in (
        (0x58, 'GetSurfaceDesc', 2, describe), (0x64, 'Lock', 5, lock),
        (0x80, 'Unlock', 2, unlock_effect), (0x74, 'SetColorKey', 3, color),
        (0x1C, 'BltFast', 6, blit), (0x14, 'Blt', 6, blit_rect),
        (8, 'Release', 1, lambda env, call: 0),
    ):
        env.put(methods + offset, env.stub('DirectDrawSurface.' + name, 'stdcall', argc, effect))
    return dict(receiver=target, target=target, manager=manager, log=log, pixels=pixels,
                device=device, interface=interface)


def raw_setup(env, flags=0, width=8, height=3, depth=8, create_result=0,
              locks=(0,), alloc_fail=False, palette=True, **opts):
    t = physical(env, width, height, depth, create_result=create_result, locks=locks, **opts)
    image = env.object(2048, 'encoded-image', data=bytes((i * 17 + 31) % 191 for i in range(2048)))
    env.put(image, 0x12345678, flags, width, height, 13, 29)
    t.update(image=image, size=2048)
    env.put(t['manager'] + 0x878, int(palette))
    if alloc_fail:
        env.override(NEW, allocate(fail=True))
    return t


def component(env, depth=8, **opts):
    t = raw_setup(env, depth=depth, **opts)
    context = env.object(0x30, 'component-context', fill=0)
    config = env.object(0x20, 'display-config', fill=0)
    display = env.object(0x20, 'display', fill=0)
    item = env.object(0x34, 'image-component', fill=0x6B)
    env.put(context + 4, config)
    env.put(config + 0x10, display)
    env.put(display + 0x18, depth)
    env.put(context + 0x1C, t['manager'])
    env.put(item + 0xC, context)
    env.put(item + 0x2C, 0, 0)
    t.update(receiver=item, component=item, context=context)
    return t


def direct(label, address, setup, *arguments, **options):
    return Case(label, address, setup, receiver=lambda t: t['receiver'], arguments=arguments, **options)


def cases(random_source):
    for depth in (0, 8, 16, 24, 32, 15, 33):
        for status in (0, 0x80004005):
            yield direct(f'describe depth {depth} status {status:x}', 0x4B9380,
                         lambda e, d=depth, s=status: physical(e, 13, 7, d, desc_result=s),
                         lambda t: t['manager'])
    for failure in (False, True):
        def setup(env, failure=failure):
            t = physical(env, create_result=0x8007000E if failure else 0)
            if not failure:
                env.put(t['manager'], 0)
            return t
        yield direct(f'create missing device {not failure}', 0x4B9380, setup, lambda t: t['manager'])
    for d in (0, 8, 16):
        yield direct(f'initialize requested depth {d}', 0x4B9180, physical,
                     lambda t: t['manager'], 17, 11, d, 0xCAFE1234)
    for statuses in ((0,), (0x80004005,), (0x887601C2,)):
        yield direct(f'lock {statuses}', 0x4B9730,
                     lambda e, s=statuses: physical(e, locks=s), 0xA51379)
    for restore_result in (0, 1):
        for retry_result in (0, 0x80004005):
            yield direct(f'lost lock restore {restore_result} retry {retry_result:x}', 0x4B9730,
                         lambda e, rr=restore_result, lr=retry_result: physical(e, locks=(0x887601C2, lr), restore=rr),
                         0xA51379)
    for key in (-1, 0, 0xAB34CD):
        for status in (0, 0x80004005):
            yield direct(f'color key {key} status {status:x}', 0x4B9990,
                         lambda e, s=status: physical(e, color_result=s), key)
    for status in (0, 1, 0x80004005):
        yield direct(f'semantic void unlock ignores HRESULT {status:x}', 0x4BB0E0,
                     lambda e, s=status: physical(e, unlock=s))
    yield direct('unlock physical service stops rather than HRESULT failure', 0x4BB0E0,
                 lambda e: physical(e, stop_unlock=True), expect='halt')
    for populated in (False, True):
        def append(env, populated=populated):
            t = physical(env)
            if populated:
                tail = env.object(12, 'existing-tail', fill=0x38)
                env.put(t['manager'] + 0x3BC, tail, tail, 1)
            t['receiver'] = t['manager']
            return t
        yield direct(f'append image to list populated {populated}', 0x4BC490, append, lambda t: t['target'])
    yield direct('initialize raw image preserves untouched bytes', 0x4BFBF0,
                 lambda e: dict(receiver=e.object(40, 'raw-image', fill=0xB9)))
    for mode in (0, 2, 3, 4, 8, 50, 51, 0xFFFFFFFF):
        for value in (0, 0xA13579BD):
            def timing(env):
                env.put(0x5430B0, 101, 203, 307, 409)
                return dict(receiver=env.object(40, 'raw-timing', fill=0x72))
            yield direct(f'timing mode {mode} explicit {value:x}', 0x4C6130, timing, mode, value)
    for depth in (0, 8, 16, 24, 32):
        for old in (False, True):
            def raw(env, d=depth, old=old):
                t = raw_setup(env)
                obj = env.object(40, 'raw-storage', fill=0x73)
                env.put(obj + 0xC, env.object(13, 'old-data') if old else 0)
                env.put(obj + 0x20, env.object(17, 'old-palette') if old else 0)
                t['receiver'] = obj
                return t
            yield direct(f'raw copy depth {depth} old {old}', 0x4BFC50, raw,
                         lambda t: t['image'], 47, depth)
    for flags in (0, 1, 2, 4, 0x80, 0x81, 0x84):
        for depth in (8, 16, 24, 32):
            yield direct(f'RLE flags {flags:x} depth {depth}', 0x4BF310,
                         lambda e, f=flags, d=depth: raw_setup(e, flags=f, depth=d),
                         lambda t: t['manager'], lambda t: t['image'], 2048, 0x4ABC, 0x1739)
    for label, opts, size in (
        ('unaligned width', dict(width=7), 2048), ('short palette', dict(flags=0x80), 768),
        ('no palette', dict(depth=16, palette=False), 2048),
        ('create fails', dict(create_result=0x80004005), 2048),
        ('lock fails', dict(locks=(0x80004005,)), 2048),
        ('scratch allocation fails', dict(depth=16, alloc_fail=True), 2048),
    ):
        yield direct(label, 0x4BF310, lambda e, o=opts: raw_setup(e, **o),
                     lambda t: t['manager'], lambda t: t['image'], size, 0, -1)
    for i in range(24):
        width = 4 * random_source.randrange(1, 10)
        height = random_source.randrange(1, 7)
        flags = random_source.choice((0, 1, 2, 4, 0x80, 0x85))
        yield direct(f'random RLE geometry {i}', 0x4BF310,
                     lambda e, w=width, h=height, f=flags: raw_setup(e, width=w, height=h, flags=f),
                     lambda t: t['manager'], lambda t: t['image'], 2048,
                     random_source.getrandbits(32), random_source.randrange(-1, 256))
    for kind in (0, 1, 2, 3, 4):
        for size in (0, 2048):
            yield direct(f'dispatch kind {kind} size {size}', 0x4BF9C0, raw_setup,
                         lambda t: t['manager'], lambda t: t['image'], kind, size, 0x805, 23)
    for size in (0, 2048):
        for kind in (0, 4):
            def create_image(env):
                t = raw_setup(env)
                t['receiver'] = t['manager']
                return t
            yield direct(f'create managed image kind {kind} size {size}', 0x4BC520, create_image,
                         lambda t: t['image'], kind, size, 0x800, -1)
    for d in (0, 8, 16):
        yield direct(f'raw component depth {d}', 0x4D25E0,
                     lambda e, d=d: component(e, depth=d), lambda t: t['image'], 47)
    yield direct('raw component allocation fails', 0x4D25E0,
                 lambda e: component(e, alloc_fail=True), lambda t: t['image'], 47)
    for kind, flags in ((0, 0), (4, 0x20), (4, 0x60), (1, 0), (2, 0), (3, 0), (4, 0)):
        yield direct(f'component kind {kind} flags {flags:x}', 0x4D2410,
                     lambda e, f=flags: component(e, flags=f), lambda t: t['image'], kind, 47, 1)
    def failed_pid(env):
        return raw_setup(env, width=7)
    yield direct('PID dispatch reports decoder rejection', 0x4BF9C0, failed_pid,
                 lambda t: t['manager'], lambda t: t['image'], 4, 2048, 0, -1)
    for keyed in (False, True):
        def ordinary_component(env, keyed=keyed):
            t = component(env, flags=1 if keyed else 0)
            env.put(0x54316C, 1, 0x5317)
            return t
        yield direct(f'ordinary component key {keyed} global flags', 0x4D2410,
                     ordinary_component, lambda t: t['image'], 4, 2048, 0)
    yield direct('light component load rejected format', 0x4D2410,
                 lambda e: component(e, flags=0x20, depth=0), lambda t: t['image'], 4, 47, 0)
    yield direct('ordinary keyed component publishes transparency mode', 0x4D2410,
                 ordinary_component, lambda t: t['image'], 4, 2048, 1)
    for payload_size in range(10):
        def bounded_copy(env, n=payload_size):
            t = raw_setup(env)
            t['receiver'] = env.object(40, 'bounded-raw-storage', fill=0x42)
            env.put(t['receiver'] + 0xC, 0)
            env.put(t['receiver'] + 0x20, 0)
            return t
        yield direct(f'raw copy exact length {payload_size}', 0x4BFC50, bounded_copy,
                     lambda t: t['image'], 32 + payload_size, 0x108)
    def transparent_palette(env):
        t = raw_setup(env, flags=0x80)
        env.write(t['image'] + 0x20, bytes([0x88, 0x88, 0x88]))
        obj = env.object(40, 'transparent-palette-storage', fill=0)
        t['receiver'] = obj
        return t
    yield direct('palette RLE conversion executes transparent rows', 0x4BFC50, transparent_palette,
                 lambda t: t['image'], 2048, 16)
    def duplicate(env):
        obj = env.object(108, 'component-table', fill=0)
        table = env.object(16, 'component-slots', words=[0, 0x12345678, 0, 0])
        env.put(obj + 0x14, table, 4)
        return dict(receiver=obj)
    yield direct('component table duplicate index', 0x4CE3D0, duplicate, 0, 1, 0)
    for old in (False, True):
        def palette_raw(env, old=old):
            t = raw_setup(env, flags=0x80, height=0)
            obj = env.object(40, 'palette-raw-storage', fill=0x73)
            env.put(obj + 0xC, env.object(13, 'old-data') if old else 0)
            env.put(obj + 0x20, env.object(17, 'old-palette') if old else 0)
            t['receiver'] = obj
            return t
        yield direct(f'palette raw expansion old {old}', 0x4BFC50, palette_raw,
                     lambda t: t['image'], 2048, 16)
    for kind in (1, 2):
        for key in (-1, 29):
            yield direct(f'valid format dispatch {kind} key {key}', 0x4BF9C0,
                         lambda e, k=kind: formatted_setup(e, k),
                         lambda t: t['manager'], lambda t: t['image'], kind, 2048, 0, key)
    for stage in (0, 1, 2, 3):
        for key in (0, 1):
            for flags in (0, 1):
                yield direct(f'resource image stage {stage} key {key} flags {flags}', 0x4D22F0,
                             lambda e, st=stage, k=key, f=flags: resource_setup(e, failure=st, keyed=k, global_flags=f),
                             lambda t: t['name'], key)
    for index, bounds, grow in ((0, (100, -100), False), (3, (0, 9), False),
                                 (7, (3, 5), True), (0, (0, 0), False)):
        for fail in (0, 1):
            yield direct(f'component publication index {index} bounds {bounds} grow {grow} failure {fail}', 0x4CE3D0,
                         lambda e, i=index, b=bounds, g=grow, f=fail: resource_setup(e, index=i, bounds=b, grow=g, failure=f),
                         lambda t: t['name'], index, 1)
    for flags in (1, 8, 0x10000008, 0):
        for timer in (0, 5, 20):
            yield direct(f'visibility flags {flags:x} timer {timer}', 0x4D2890,
                         lambda e, f=flags, tm=timer: render_setup(e, flags=f, timer=tm),
                         lambda t: t['actor'], lambda t: t['destination'])
    for light in (False, True):
        for flip in (0, 2, 4, 6):
            yield direct(f'original draw delegate light {light} flip {flip}', 0x4D2890,
                         lambda e, l=light, f=flip: render_setup(e, flags=f, light=l, position=(200, 200)),
                         lambda t: t['actor'], lambda t: t['destination'])
    for camera in (False, True):
        for clip in (None, (2, 3, 8, 7), (0, 0, 100, 100), (20, 20, 30, 30)):
            for position in ((-3, -2), (3, 4), (29, 19), (80, 1), (1, 80)):
                yield direct(f'clipped image camera {camera} clip {clip} xy {position}', 0x4D2890,
                             lambda e, c=camera, cl=clip, p=position: render_setup(e, camera=c, clip=cl, position=p),
                             lambda t: t['actor'], lambda t: t['destination'])
    for i in range(24):
        w, h = random_source.randrange(1, 30), random_source.randrange(1, 20)
        x, y = random_source.randrange(-10, 40), random_source.randrange(-10, 30)
        yield direct(f'random clipping {i}', 0x4D2890,
                     lambda e, w=w, h=h, x=x, y=y: render_setup(e, geometry=(w, h), position=(x, y)),
                     lambda t: t['actor'], lambda t: t['destination'])

    def descriptor_neighbors(env):
        t = physical(env)
        env.put(t['target'] + 0x78, 0xA13579BD)
        return t
    yield direct('descriptor clears exactly27 words preserving following field', 0x4B9180,
                 descriptor_neighbors, lambda t: t['manager'], 17, 11, 0, 0xCAFE1234)
    # malloc does not promise zeroed storage. Distinct old bytes make each
    # constructor's explicit writes and preserved neighboring bytes observable.
    for poison in (0x39, 0xA6, random_source.randrange(1, 256)):
        def managed_poison(env, p=poison):
            t = raw_setup(env, flags=1)
            poison_allocations(env, p)
            t['receiver'] = t['manager']
            return t
        yield direct(f'nonzero managed allocation {poison:x}', 0x4BC520, managed_poison,
                     lambda t: t['image'], 4, 2048, 0x4008, 37)
        def table_poison(env, p=poison):
            t = resource_setup(env, index=3, keyed=1)
            poison_allocations(env, p)
            return t
        yield direct(f'nonzero component allocation {poison:x}', 0x4CE3D0, table_poison,
                     lambda t: t['name'], 3, 1)
        def light_poison(env, p=poison):
            t = component(env, flags=0x60)
            poison_allocations(env, p)
            return t
        yield direct(f'nonzero light allocation {poison:x}', 0x4D25E0, light_poison,
                     lambda t: t['image'], 47)
    for flags in (0x80, 0x81, 0x84):
        def dirty_palette(env, f=flags):
            t = raw_setup(env, flags=f)
            env.write(0x5427B0, bytes((i * 31 + 93) % 255 + 1 for i in range(1024)))
            return t
        yield direct(f'embedded palette replaces nonzero alpha {flags:x}', 0x4BF310, dirty_palette,
                     lambda t: t['manager'], lambda t: t['image'], 2048, 0x2C19, 43)
    for j in range(20):
        centers = (random_source.randrange(-5, 8), random_source.randrange(-7, 6))
        anchors = (random_source.randrange(-6, 9), random_source.randrange(-8, 7))
        offsets = (random_source.randrange(-7, 10), random_source.randrange(-9, 8))
        def offset_actor(env, c=centers, a=anchors, o=offsets, camera=bool(j % 2)):
            t = render_setup(env, camera=camera)
            env.put(t['component'] + 0x18, *c, *a)
            env.put(t['actor'] + 0x4C, *o)
            # Deliberately distinct neighboring output fields already carry5d.
            return t
        yield direct(f'independent centers anchors actor offsets {j}', 0x4D2890, offset_actor,
                     lambda t: t['actor'], lambda t: t['destination'])
    for width, height, depth in ((0, 0, 8), (1, 1, 16), (0xFFFFFFFF, 0xFFFFFFFD, 24),
                                 (0x80000000, 0x7FFFFFFF, 32), (0x7FFFFFFF, 0x80000000, 8)):
        yield direct(f'descriptor signed geometry {width:x} {height:x} {depth}', 0x4B9380,
                     lambda e, w=width, h=height, d=depth: physical(e, width=w, height=h, depth=d),
                     lambda t: t['manager'])
    for index in (0, 1, 15, 16):
        yield direct(f'array count equality and growth index {index}', 0x4CE3D0,
                     lambda e, i=index: resource_setup(e, index=i, bounds=(i, i)),
                     lambda t: t['name'], index, 0)


def render_setup(env, flags=0, timer=20, light=False, camera=False, clip=None,
                 position=(3, 4), geometry=(11, 9)):
    t = component(env)
    image = t['component']
    width, height = geometry
    env.put(image + 0x10, width, height, 0, 0, 0, 0, 0x10, t['target'],
            env.object(40, 'light-image', fill=0) if light else 0)
    actor = env.object(100, 'actor-render-state', fill=0x5D)
    env.put(actor + 8, 0x40000 if camera else 0)
    env.put(actor + 0x10, *position)
    env.put(actor + 0x40, flags, timer, 17, 0, 0)
    env.put(actor + 0x54, *(clip or (0x80000000, 0, 0, 0)))
    destination = env.object(48, 'destination-component', fill=0x9E)
    env.put(destination + 0x10, 31, 23)
    destination_surface = physical(env, width=31, height=23)
    env.put(destination + 0x2C, destination_surface['target'])
    viewport = env.object(32, 'viewport', fill=0)
    env.put(viewport + 0x10, *(clip or (0, 0, 30, 22)))
    env.put(t['context'] + 0x24, viewport)
    parent = env.object(96, 'camera-owner', fill=0)
    camera_obj = env.object(88, 'camera', fill=0)
    env.put(parent + 0x5C, camera_obj)
    env.put(actor + 0x3C, parent)
    env.put(0x5430C4, 5)
    def copy_rect(env, call):
        env.write(call.arguments[0], env.read(call.arguments[1], 16))
        return 0x12345678
    env.override(0x546D58, copy_rect)
    t.update(actor=actor, destination=destination)
    return t


def formatted_setup(env, kind):
    import struct
    t = raw_setup(env)
    image = t['image']
    if kind == 1:
        env.write(image, bytes(128))
        env.put(image + 10, 0x80)
        env.put(image + 0x12, 8, 3)
        env.write(image + 0x1C, struct.pack('<H', 8))
    else:
        env.write(image, bytes(128))
        env.write(image + 4, struct.pack('<4h', 0, 0, 7, 2))
        env.write(image + 0x41, bytes([1]))
    return t


def resource_setup(env, failure=0, keyed=0, global_flags=0, width=9, height=5, index=None,
                   bounds=(100, -100), grow=False):
    import struct
    t = component(env, width=width, height=height)
    env.put(0x54316C, global_flags, 0x35 if keyed else 0xFFFFFFFF)
    name = env.object(24, 'resource-name', data=b'ORIGINAL_IMAGE_RESOURCE\0')
    bitmap = env.object(2048, 'resource-bitmap', data=bytes((i * 29 + 7) % 256 for i in range(2048)))
    env.put(bitmap, 40, width, height)
    env.write(bitmap + 0xE, struct.pack('<H', 8))
    resource = env.object(4, 'resource-handle', words=[bitmap])
    loaded = env.object(4, 'loaded-resource-handle', words=[bitmap])
    receipt = env.object(100, 'resource-service-record', fill=0)
    def find(env, call):
        env.put(receipt, call.receiver, *call.arguments)
        env.write(receipt + 16, env.read(call.arguments[1], 24))
        return 0 if failure == 1 else resource
    def load(env, call):
        env.put(receipt + 48, call.receiver, *call.arguments)
        return 0 if failure == 2 else loaded
    def lock(env, call):
        env.put(receipt + 64, call.receiver, *call.arguments)
        return 0 if failure == 3 else bitmap
    env.override(0x546AC8, find)
    env.override(0x546ACC, load)
    env.override(0x546AC4, lock)
    t['name'] = name
    if index is not None:
        obj = env.object(108, 'component-array-owner', fill=0x53)
        data = env.object(64, 'component-array-slots', fill=0)
        env.put(obj + 0xC, t['context'])
        env.put(obj + 0x10, 0x51079C, data, 1 if grow else 16, 16, 4)
        env.put(obj + 0x64, *bounds)
        t['receiver'] = obj
    return t


def poison_allocations(env, salt):
    def allocate_pattern(env, call):
        n = call.arguments[0]
        return env.object(n, 'nonzero-allocation',
                          data=bytes(((i * 53 + salt) % 255) + 1 for i in range(n)))
    env.override(NEW, allocate_pattern)
