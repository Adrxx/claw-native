"""Original-backed state construction, directory lookup, and startup inputs."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns, release, sequence


def directory(env, name, children=()):
    """REZ directory with the original five-bucket name index at +0x3c."""
    target = env.object(0x80, name, fill=0)
    text = env.object(len(name) + 1, name + '-name', data=name.encode() + b'\0')
    env.put(target, text)
    buckets = env.object(5 * 16, name + '-buckets', fill=0)
    env.put(target + 0x40, buckets)
    heads = {}
    for child_name, child in children:
        bucket = len(child_name) % 5
        node = env.object(0x18, child_name + '-index-node', fill=0)
        env.put(node + 4, heads.get(bucket, 0))
        env.put(node + 0x14, child)
        heads[bucket] = node + 4
    for bucket, head in heads.items():
        env.put(buckets + 8 + bucket * 16, head)
    return target


def setup_state(level=1, include_level=False, shared=False, resources=False, custom=b'', seed=b'\x97' * 0x774):
    def setup(env):
        state = env.object(0x774, 'state', data=seed)
        owner = env.object(0x134, 'application', fill=0)
        scene = env.object(0x3c, 'scene', fill=0)
        modes = env.object(0x12c, 'modes', fill=0x67)
        cstring = env.object(len(custom) + 13, 'custom-cstring', fill=0)
        env.put(cstring, 2, len(custom), len(custom))
        env.write(cstring + 12, custom + b'\0')
        children = []
        if include_level:
            children.append((f'LEVEL{level}', directory(env, f'LEVEL{level}')))
        if shared:
            children.append(('CLAW', directory(env, 'CLAW')))
        if resources:
            children.append(('GAME', directory(env, 'GAME')))
        root = directory(env, 'root', children)
        manager = env.object(0x28, 'resource-manager', fill=0)
        env.put(manager + 0x24, root)
        env.put(owner + 0x30, scene, manager)
        env.put(owner + 0x44, 0x6b3d9127, modes)
        env.put(owner + 0x7c, 640, 480)
        env.put(owner + 0xc0, cstring + 12)
        env.put(state + 4, owner, manager, scene)
        env.put(state + 0x2c, 0)
        env.put(0x5371fc, owner)
        def atomic(delta):
            def effect(env, call):
                pointer = call.arguments[0]
                value = (env.get(pointer) + delta) & 0xffffffff
                env.put(pointer, value)
                return value
            return effect
        env.override(0x5469ec, atomic(1))
        env.override(0x5469e8, atomic(-1))
        env.override(0x546d54, returns(0xffffffff))
        env.override(0x4a3040, returns(0))
        env.override(0x4f63ec, allocate())
        env.override(0x4a48e0, allocate())
        env.override(0x4f6428, release())
        return {'state': state, 'owner': owner}
    return setup


def baseline_cases(random_source):
    for index in range(8):
        seed = bytes(random_source.randrange(1, 256) for _ in range(0x774))
        yield Case(f'constructor returned receiver and byte holes {index}', 0x40b5c0,
                   setup_state(seed=seed), receiver=lambda t: t['state'])
    for width, height in ((640, 480), (639, 480), (641, 480), (640, 479), (640, 481), (0, 0), (0xffffffff, 480)):
        def dimensions(env, w=width, h=height):
            owner = env.object(0x88, 'dimensions', fill=0x8d)
            env.put(owner + 0x7c, w, h)
            return owner
        yield Case(f'dimensions {width} by {height}', 0x42af50, dimensions, receiver=lambda t: t)
    def globals_setup(env):
        env.write(0x537200, bytes(random_source.randrange(1, 256) for _ in range(0x80)))
        env.write(0x543104, bytes(random_source.randrange(1, 256) for _ in range(0x70)))
    yield Case('reset clears named globals and preserves gaps', 0x42aa50, globals_setup)
    yield Case('effect table exact 25-word bounds', 0x4cfa60, globals_setup)
    yield Case('scene manager leaf', 0x4cdf20)
    yield Case('single player null application', 0x46a6d0, setup_state(),
               receiver=lambda t: t['state'], arguments=(0, 7, 0xa3b2c1d0))
    for level in (0, 1, 7, 14, -1, 0x7fffffff):
        for present in (False, True):
            setup = setup_state(level=level, include_level=present)
            yield Case(f'initialize level {level} present {present}', 0x48f0d0, setup,
                       receiver=lambda t: t['state'],
                       arguments=(lambda t: t['owner'], level, 0xa3b2c1d0))
            yield Case(f'single player level {level} shared missing {present}', 0x46a6d0, setup,
                       receiver=lambda t: t['state'],
                       arguments=(lambda t: t['owner'], level, 0xa3b2c1d0))
            yield Case(f'load level {level} missing palette {present}', 0x46aeb0, setup,
                       receiver=lambda t: t['state'], arguments=(level, 1))
    for have_game in (False, True):
        base_setup = setup_state(level=3, include_level=True, shared=True, resources=have_game)
        def startup(env, base=base_setup):
            tokens = base(env)
            env.override(0x546d54, sequence(2, 1, 0, 0xffffffff))
            return tokens
        yield Case(f'startup real CLAW directory GAME present {have_game}', 0x46a6d0, startup,
                   receiver=lambda t: t['state'], arguments=(lambda t: t['owner'], 3, 29))
    for level in (-1, 7):
        setup = setup_state(level=level, custom=b'custom.wwd')
        yield Case(f'custom parse missing world level {level}', 0x46a6d0, setup,
                   receiver=lambda t: t['state'], arguments=(lambda t: t['owner'], level, 23))
        yield Case(f'custom load parsed minus one level {level}', 0x46aeb0, setup,
                   receiver=lambda t: t['state'], arguments=(level, 0))
    def scene_setup(env):
        target = env.object(0x3c, 'scene-initializer', fill=0)
        interface = env.object(4, 'physical-directdraw')
        methods = env.object(0x54, 'physical-directdraw-vtable', fill=0)
        env.put(interface, methods)
        env.put(methods + 0x50, env.stub('IDirectDraw::SetCooperativeLevel', 'stdcall', 3, returns(0x80004005)))
        env.put(0x541398, interface)
        env.put(0x54139c, 0, 0, 0, 0)
        env.override(0x4f63ec, allocate())
        env.override(0x4a48e0, allocate())
        env.override(0x4f6428, release())
        env.override(0x546864, returns(0x80004005))
        return target
    yield Case('scene actual original constructors and manager graph', 0x4cea10, scene_setup,
               receiver=lambda t: t, arguments=(0x12345678, 640, 480, 8, 4))


def physical_graph(env, width=640, height=480, depth=8, display_error=0, palette_error=0):
    """Physical COM objects only; every engine constructor/method stays original."""
    observations = env.object(0x4000, 'physical-call-observations', fill=0)
    def observe(tag, effect):
        def callback(env, call):
            count = env.get(observations)
            at = observations + 4 + count * 40
            env.put(at, tag, call.receiver, len(call.arguments), *call.arguments)
            env.put(observations, count + 1)
            return effect(env, call)
        return callback
    def interface(name, entries):
        obj = env.object(4, name, fill=0)
        table = env.object(0x100, name + '-vtable', fill=0)
        env.put(obj, table)
        for offset, argc, effect in entries:
            env.put(table + offset, env.stub(name + ':' + hex(offset), 'stdcall', argc,
                                           observe(offset, effect)))
        return obj
    def description(env, call):
        out = call.arguments[1]
        env.put(out + 8, height, width, width * max(1, depth // 8))
        env.put(out + 0x48, 0x20, 0x40, 0, depth, 0xff0000, 0xff00, 0xff)
        return 0
    surface = interface('IDirectDrawSurface', [
        (8, 1, returns(0)), (0x14, 6, returns(0)), (0x2c, 3, returns(0)),
        (0x30, 3, lambda e, c: (e.put(c.arguments[2], surface), 0)[1]),
        (0x58, 2, description),
        (0x44, 2, lambda e, c: (e.put(c.arguments[1], 0x7612), 0)[1]),
        (0x68, 2, returns(0)), (0x7c, 2, returns(0))])
    palette_bytes = env.object(0x400, 'physical-palette-entries', fill=0)
    def get_entries(env, call):
        _, flags, start, count, out = call.arguments
        env.write(out, env.read(palette_bytes + 4 * start, 4 * count))
        return 0
    def set_entries(env, call):
        _, flags, start, count, source = call.arguments
        env.write(palette_bytes + 4 * start, env.read(source, 4 * count))
        return 0
    palette = interface('IDirectDrawPalette', [(8, 1, returns(0)), (0x10, 5, get_entries),
                                               (0x18, 5, set_entries)])
    def create_palette(env, call):
        if not palette_error:
            env.write(palette_bytes, env.read(call.arguments[2], 0x400))
            env.put(call.arguments[3], palette)
        return palette_error
    draw = interface('IDirectDraw', [
        (0x14, 5, create_palette),
        (0x18, 4, lambda e, c: (e.put(c.arguments[2], surface), 0)[1]),
        (0x20, 5, returns(0)), (0x2c, 3, returns(0)), (0x30, 2, description),
        (0x50, 3, returns(display_error)), (0x54, 4, returns(0))])
    sound = interface('IDirectSound', [(8, 1, returns(0)), (0x18, 3, returns(0))])
    env.put(0x541398, draw)
    env.put(0x54139c, 0, 0, 0, 0)
    env.put(0x541378, 0, 0, 0, 0, 0, 0)
    return {'draw': draw, 'surface': surface, 'sound': sound, 'observations': observations}


def scene_graph(display_error=0, audio_error=0, sticky=0):
    def setup(env):
        target = env.object(0x3c, 'scene-original-manager-graph', fill=0)
        env.put(target + 0x38, sticky)
        physical = physical_graph(env, display_error=display_error)
        env.override(0x4f63ec, allocate())
        env.override(0x4a48e0, allocate())
        env.override(0x4f6428, release())
        def create_audio(env, call):
            if not audio_error:
                env.put(call.arguments[1], physical['sound'])
            return audio_error
        env.override(0x546864, create_audio)
        return target
    return setup


def scene_cases(random_source):
    for flags, audio_error, sticky in ((0, 0, 0), (4, 0, 0), (8, 0, 37),
                                       (0, 0x80004005, 0), (4, 0x80004005, 0),
                                       (8, 0x80004005, 0), (8, 0x80004005, 73)):
        yield Case(f'original scene display audio flags {flags} error {audio_error:#x} sticky {sticky}',
                   0x4cea10, scene_graph(audio_error=audio_error, sticky=sticky),
                   receiver=lambda t: t, arguments=(0x12345678, 640, 480, 8, flags))
    yield Case('original display failure preserves existing scene error', 0x4cea10,
               scene_graph(display_error=0x80004005, sticky=0x631),
               receiver=lambda t: t, arguments=(0x12345678, 640, 480, 8, 0))


def custom_header_setup(level, title, include_level=True, read_size=0x5f4, open_error=False):
    def setup(env):
        tokens = setup_state(level=level, include_level=include_level, custom=b'custom.wwd')(env)
        scene = env.get(tokens['owner'] + 0x30)
        env.put(scene + 0x24, env.object(0xe0, 'world-parser-present', fill=0))
        header = bytearray(0x5f4)
        header[:4] = (0x5f4).to_bytes(4, 'little')
        header[16:16 + len(title) + 1] = title + b'\0'
        env.override(0x5469e4, lambda e, c: len(e.cstr(c.arguments[0])))
        env.override(0x546ad0, returns(0))
        def copy_path(env, call):
            out, source, limit = call.arguments
            text = env.cstr(source)
            if isinstance(text, str):
                text = text.encode()
            env.write(out, text[:limit - 1] + b'\0')
            return out
        env.override(0x5469cc, copy_path)
        env.override(0x546b00, returns(0xffffffff if open_error else 0x7341))
        def read_file(env, call):
            handle, out, count, read, overlapped = call.arguments
            data = bytes(header[:min(count, read_size)])
            env.write(out, data)
            env.put(read, len(data))
            return 1
        env.override(0x546afc, read_file)
        env.override(0x546a04, returns(1))
        return tokens
    return setup


def dimension_reset_setup(width, height):
    def setup(env):
        tokens = setup_state(level=3, include_level=True)(env)
        owner, state = tokens['owner'], tokens['state']
        scene = env.get(owner + 0x30)
        display = env.object(0x1c, 'existing-display', fill=0)
        primary = env.object(0x30, 'existing-primary', fill=0)
        palette_manager = env.object(0x68, 'existing-palette-manager', fill=0)
        world = env.object(0xe0, 'existing-world', fill=0)
        env.put(primary + 0x10, 640, 480)
        env.put(display + 0x10, primary)
        env.put(scene + 4, display)
        env.put(scene + 0x18, palette_manager)
        env.put(scene + 0x24, world)
        env.put(state, 0x50b4ec)
        env.put(owner + 0x2c, state)
        env.put(owner + 0x7c, width, height)
        env.put(0x537e88, 0)
        env.override(0x546df0, lambda e, c: 0x123400 + 251 * e.calls_so_far(0x546df0))
        return tokens
    return setup


def initialization_cases(random_source):
    for level, title in ((3, b'Level 3'), (14, b'Fortress 14'), (0, b'No digits'), (1, b'Level 0')):
        yield Case(f'custom original CString header parse {title!r}', 0x46a6d0,
                   custom_header_setup(level, title), receiver=lambda t: t['state'],
                   arguments=(lambda t: t['owner'], 99, 0x4a6b7c8d))
    for level, title in ((3, b'Level 3'), (3, b'Level 14')):
        yield Case(f'custom load original header compare {title!r}', 0x46aeb0,
                   custom_header_setup(level, title), receiver=lambda t: t['state'], arguments=(level, 0))
    for width, height in ((800, 600), (640, 479)):
        for function in (0x46a6d0, 0x46aeb0):
            yield Case(f'dimension reset original graph {function:#x} {width}x{height}', function,
                       dimension_reset_setup(width, height), receiver=lambda t: t['state'],
                       arguments=((lambda t: t['owner'], 3, 0x75) if function == 0x46a6d0 else (3, 1)))
    def missing_audio(env):
        target = scene_graph(audio_error=0x80004005)(env)
        def heap(env, call):
            return 0 if call.arguments[0] == 0x80 else env.object(call.arguments[0], 'original-allocation')
        env.override(0x4f63ec, heap)
        return target
    yield Case('scene null audio allocation physical create failure is tolerated', 0x4cea10,
               missing_audio, receiver=lambda t: t, arguments=(0x12345678, 640, 480, 8, 0))


def palette_prefix_setup(palette_data, palette_error=0, old_palette=False):
    def setup(env):
        tokens = setup_state(level=3, seed=b'\0' * 0x774)(env)
        state, owner = tokens['state'], tokens['owner']
        scene = env.get(owner + 0x30)
        physical = physical_graph(env, depth=32, palette_error=palette_error)
        env.override(0x5469e4, lambda e, c: len(e.cstr(c.arguments[0])))
        env.override(0x546df0, lambda e, c: 0x123400 + 251 * e.calls_so_far(0x546df0))
        env.put(state, 0x50b4ec)
        env.put(owner + 0x78, 32)
        window = env.object(8, 'window-wrapper', fill=0)
        env.put(window + 4, 0x12345678)
        env.put(owner + 4, window)
        env.put(owner + 0x50, env.object(0x20, 'music-collection', fill=0))
        env.put(owner + 0x5c, env.object(0x24, 'actor-collection', fill=0))
        display = env.object(0x1c, 'display-manager', fill=0)
        primary = env.object(0x30, 'primary-display', fill=0)
        back = env.object(0x34, 'back-display', fill=0)
        surface = env.object(0xbc, 'surface-wrapper', fill=0)
        env.put(surface, 0x513690)
        env.put(surface + 8, physical['surface'])
        env.put(primary + 0x10, 640, 480, 32)
        env.put(primary + 0x2c, surface)
        env.put(back + 0x2c, surface)
        env.put(display + 0x10, primary, back)
        env.put(scene + 4, display)
        for offset, size, vtable in ((8, 0x2c, 0x513c20), (0x10, 0x2c, 0x513b88),
                                    (0x18, 0x68, 0x513b28), (0x24, 0xe0, 0x513938),
                                    (0x28, 0x34, 0x513b00), (0x2c, 0x2c, 0x513ad8)):
            child = env.object(size, 'original-manager-' + hex(offset), fill=0)
            env.put(child, vtable)
            env.put(child + 0xc, scene)
            env.put(child + 0x10, 0x5105c4, 0, 17, 0, 0, 0, 10)
            env.put(scene + offset, child)
        driver = env.object(0x884, 'display-driver', fill=0)
        env.put(driver, physical['draw'])
        env.put(driver + 0x3b8, 0x51000c, 0, 0, 0, 0, 0, 10)
        env.put(driver + 0x3d4, 0x51000c, 0, 0, 0, 0, 0, 10)
        env.put(scene + 0x1c, driver)
        resource = env.object(0x2c, 'MAIN-resource', fill=0)
        name = env.object(5, 'MAIN-name', data=b'MAIN\0')
        payload = env.object(len(palette_data), 'MAIN-RGB-bytes', data=palette_data)
        palette_dir = directory(env, 'PALETTES')
        env.put(resource, name)
        env.put(resource + 0x14, len(palette_data), 0)
        env.put(resource + 0x24, palette_dir, 0)
        env.put(palette_dir + 0x20, payload)
        resource_type = env.object(0x2c, 'PAL-resource-type', fill=0)
        env.put(resource_type, 0x50414c)
        def index(at, buckets_count, bucket, value):
            buckets = env.object(16 * buckets_count, 'resource-index-buckets', fill=0)
            node = env.object(0x18, 'resource-index-node', fill=0)
            env.put(node + 0x14, value)
            env.put(buckets + 8 + 16 * bucket, node + 4)
            env.put(at + 4, buckets)
        index(palette_dir + 0x44, 9, 0x50414c % 9, resource_type)
        index(resource_type + 0x24, 5, 4, resource)
        level_dir = directory(env, 'LEVEL3', [('PALETTES', palette_dir)])
        root = directory(env, 'root', [('LEVEL3', level_dir)])
        env.put(env.get(state + 8) + 0x24, root)
        tokens['palette_dir'] = palette_dir
        # Optional prior palette is a real original palette object, released by its original destructor.
        if old_palette:
            old = env.object(0x14, 'old-palette-object', fill=0)
            env.put(old, 0x513d78)
            env.put(old + 0xc, scene)
            env.put(state + 0x2c, old)
        return tokens
    return setup


def palette_cases(random_source):
    for error, old in ((0, False), (0x80004005, False), (0, True)):
        palette_data = bytes(random_source.randrange(256) for _ in range(768))
        yield Case(f'original MAIN palette creation error {error:#x} prior {old}', 0x46aeb0,
                   palette_prefix_setup(palette_data, error, old), receiver=lambda t: t['state'],
                   arguments=(3, 1))
    def null_sound(env):
        target = scene_graph(display_error=0x80004005)(env)
        count = env.object(4, 'allocation-count', fill=0)
        def heap(env, call):
            number = env.get(count) + 1
            env.put(count, number)
            return 0 if number == 8 else env.object(call.arguments[0], 'original-allocation')
        env.override(0x4f63ec, heap)
        return target
    yield Case('scene null sound allocation before real display failure', 0x4cea10,
               null_sound, receiver=lambda t: t, arguments=(0x12345678, 640, 480, 8, 0))


def retained_cases(random_source):
    yield from baseline_cases(random_source)
    yield from scene_cases(random_source)
    yield from initialization_cases(random_source)
    yield from palette_cases(random_source)
    for read_size, open_error in ((0x5f3, False), (0, False), (0x5f4, True)):
        yield Case(f'custom actual file header read {read_size} open failure {open_error}', 0x46a6d0,
                   custom_header_setup(3, b'Level 3', read_size=read_size, open_error=open_error),
                   receiver=lambda t: t['state'], arguments=(lambda t: t['owner'], 99, 37))
    palette_data = bytes(random_source.randrange(256) for _ in range(768))
    def cursor_loop(env):
        tokens = palette_prefix_setup(palette_data)(env)
        env.override(0x546d54, sequence(2, 1, 0, 0xffffffff))
        return tokens
    yield Case('original MAIN palette prefix repeats cursor until signed negative', 0x46aeb0,
               cursor_loop, receiver=lambda t: t['state'], arguments=(3, 0))
    for width, height, depth, flags in ((320, 200, 16, 1), (800, 600, 32, 2)):
        yield Case(f'original scene forwarded dimensions {width}x{height} depth {depth} flags {flags}',
                   0x4cea10, scene_graph(), receiver=lambda t: t,
                   arguments=(0x28193475, width, height, depth, flags))


RESOURCE_PHASES = (('LEVEL3', 'TILES'), ('LEVEL3', 'SOUNDS'),
                   ('CLAW', 'SOUNDS'), ('GAME', 'SOUNDS'),
                   ('LEVEL3', 'IMAGES'), ('LEVEL3', 'ANIS'),
                   ('CLAW', 'IMAGES'), ('CLAW', 'ANIS'),
                   ('GAME', 'IMAGES'), ('GAME', 'ANIS'))


def level_graph_setup(palette_data, phases=10, world_data=None, captain=False, custom=False, music=None, demo=0, selection=0, restore=False, viewport_top=0, cursor_repeat=False, custom_open_error=False, audio_error=False, animation=None):
    def setup(env):
        tokens = palette_prefix_setup(palette_data)(env)
        state = tokens['state']
        music_owner = env.object(0x30, 'original-music-owner', fill=0)
        env.put(music_owner, 0x5105c4, 0, 17, 0, 0, 0, 10)
        env.put(tokens['owner'] + 0x50, music_owner)
        env.put(tokens['owner'] + 0x9c, demo)
        env.put(state + 0x154, int(restore))
        env.put(0x53c988, selection)
        env.override(0x546cac, returns(0))
        scene = env.get(state + 0xc)
        sprite = env.object(0x2c, 'original-sprite-manager', fill=0)
        env.put(sprite, 0x513be8)
        env.put(sprite + 0xc, scene)
        env.put(sprite + 0x10, 0x5105c4, 0, 0, 0, 0, 0, 10)
        env.put(scene + 0xc, sprite)
        world = env.get(scene + 0x24)
        env.put(world + 0x10, 0, viewport_top, 639, 479)
        logic = env.object(0x2c, 'original-logic-manager', fill=0)
        env.put(logic, 0x513b60)
        env.put(logic + 0xc, scene)
        env.put(logic + 0x10, 0x5105c4, 0, 17, 0, 0, 0, 10)
        env.put(scene + 0x14, logic)
        if captain:
            env.put(tokens['owner'] + 0x2c, state)
            inputs = env.object(0x74, 'game-input-state', fill=0)
            env.put(inputs, env.object(0x218, 'physical-input-owner', fill=0))
            env.put(0x537204, inputs)
            buckets = env.object(17 * 4, 'logic-buckets', fill=0)
            env.put(logic + 0x14, buckets)
            for name, callback, flags in (
                    ('CaptainClaw', 0x415df0, 0),
                    ('CaptainClawScreenPosition', 0x486240, 0),
                    ('MultiStats', 0x491ed0, 0),
                    ('ClawDialogSound', 0x48c630, 0),
                    ('EnemyDialogSound', 0x48cc60, 0),
                    ('CheckpointTimer', 0x491b30, 2),
                    ('CaptainClawHit', 0x41ce80, 0)):
                record = env.object(0x174, name + '-original-logic', fill=0)
                env.put(record, 0x513740, 0, flags, scene, callback)
                key = env.object(len(name) + 1, name + '-key', data=name.encode() + b'\0')
                hash_value = 0
                for byte in name.encode():
                    hash_value = (hash_value * 33 + byte) & 0xffffffff
                bucket = buckets + 4 * (hash_value % 17)
                node = env.object(16, name + '-map-node', words=[env.get(bucket), 0, key, record])
                env.put(bucket, node)
        branches = {'LEVEL3': [('PALETTES', tokens['palette_dir'])], 'CLAW': [], 'GAME': []}
        for parent, child in RESOURCE_PHASES[:phases]:
            if animation is not None and (parent, child) == ('LEVEL3', 'ANIS'):
                child_dir = resource_directory(env, child, 0x414e49, [('TEST', animation)], enumerated=True)
                branches[parent].append((child, child_dir))
                continue
            branches[parent].append((child, directory(env, parent + '-' + child)))
            child_dir = branches[parent][-1][1]
            env.put(child_dir + 0x3c, 5)
            env.put(child_dir + 0x44, 9, env.object(9 * 16, 'empty-resource-types', fill=0))
            # Lookup keys use the actual directory name, distinct from allocation labels.
            env.put(branches[parent][-1][1], env.object(len(child) + 1, child + '-name', data=child.encode() + b'\0'))
        if music is not None:
            for parent, tracks in music.items():
                branches[parent].append(('MUSIC', resource_directory(env, parent + '-music', 0x584d49, tracks)))
                env.put(branches[parent][-1][1], env.object(6, 'MUSIC-name', data=b'MUSIC\0'))
            env.put(0x54131c, 0x1953)
            env.override(0x546e9c, returns(0x2751))
            env.override(0x546e98, returns(0 if audio_error else 1))
            env.override(0x546e94, returns(0))
        if world_data is not None:
            branches['LEVEL3'].append(('WORLDS', resource_directory(env, 'WORLDS', 0x575744, [('WORLD', world_data)])))
        directories = {name: directory(env, name, children) for name, children in branches.items()}
        root = directory(env, 'root', list(directories.items()))
        env.put(env.get(state + 8) + 0x24, root)
        env.put(state + 0x24, directories['CLAW'], directories['GAME'])
        if world_data is not None:
            env.override(0x546d58, lambda e, c: (e.write(c.arguments[0], e.read(c.arguments[1], 16)), 1)[1])
            env.override(0x546d5c, lambda e, c: (e.put(c.arguments[0], *c.arguments[1:]), 1)[1])
        if cursor_repeat:
            env.override(0x546d54, sequence(2, 1, 0xffffffff, 3, 2, 0xffffffff))
        if custom:
            env.override(0x546888, returns(1))
            env.override(0x546880, returns(0x113355))
            env.override(0x546d30, returns(17))
            path = env.object(24, 'custom-world-path', words=[2, 11, 11], data=None, fill=0)
            env.write(path + 12, b'fixture.wwd\0')
            env.put(tokens['owner'] + 0xc0, path + 12)
            cursor = env.object(4, 'physical-file-cursor', fill=0)
            env.override(0x546ad0, returns(0))
            def copy_path(e, c):
                value = e.cstr(c.arguments[1])
                if isinstance(value, str):
                    value = value.encode()
                e.write(c.arguments[0], value[:c.arguments[2] - 1] + b'\0')
                return c.arguments[0]
            env.override(0x5469cc, copy_path)
            env.override(0x546b00, lambda e, c: (e.put(cursor, 0),
                         0xffffffff if custom_open_error and e.calls_so_far(0x546b00) > 1 else 0x7341)[1])
            def read_file(e, c):
                pos = e.get(cursor)
                data = world_data[pos:pos + c.arguments[2]]
                e.write(c.arguments[1], data)
                e.put(c.arguments[3], len(data))
                e.put(cursor, pos + len(data))
                return 1
            def seek_file(e, c):
                base = (0, e.get(cursor), len(world_data))[c.arguments[3]]
                pos = (base + c.arguments[1]) & 0xffffffff
                e.put(cursor, pos)
                return pos
            env.override(0x546afc, read_file)
            env.override(0x546af4, seek_file)
            env.override(0x546a04, returns(1))
        tokens['directories'] = directories
        return tokens
    return setup


def cases(random_source):
    yield from distinction_cases(random_source)
    yield from retained_cases(random_source)
    palette_data = bytes(random_source.randrange(256) for _ in range(768))
    for phases in range(1, 11):
        yield Case(f'original resource directory phase {phases}', 0x46aeb0,
                   level_graph_setup(palette_data, phases), receiver=lambda t: t['state'],
                   arguments=(3, 1))

    for valid, captain in ((False, False), (True, False), (True, True)):
        yield Case(f'original WORLD parser valid {valid} CaptainClaw registered {captain}',
                   0x46aeb0, level_graph_setup(palette_data, world_data=minimal_world(valid), captain=captain),
                   receiver=lambda t: t['state'], arguments=(3, 1))
    for demo in (0, 1):
        yield Case(f'original successful initialize demo {demo} timeout', 0x46a6d0,
                   level_graph_setup(palette_data, world_data=minimal_world(), captain=True, demo=demo),
                   receiver=lambda t: t['state'], arguments=(lambda t: t['owner'], 3, 0x75))
    for custom in (False, True):
        for restore in (False, True):
            yield Case(f'original complete world custom {custom} restore {restore}', 0x46aeb0,
                       level_graph_setup(palette_data, world_data=minimal_world(), captain=True,
                                         custom=custom, restore=restore),
                       receiver=lambda t: t['state'], arguments=(3, 0))
    yield Case('original positive viewport top and repeated second cursor loop', 0x46aeb0,
               level_graph_setup(palette_data, world_data=minimal_world(), captain=True,
                                 viewport_top=13, cursor_repeat=True),
               receiver=lambda t: t['state'], arguments=(3, 1))
    yield Case('original custom world second open fails after valid title parse', 0x46aeb0,
               level_graph_setup(palette_data, world_data=minimal_world(), captain=True,
                                 custom=True, custom_open_error=True),
               receiver=lambda t: t['state'], arguments=(3, 1))
    def missing_color_tables(env):
        tokens = level_graph_setup(palette_data)(env)
        env.put(tokens['owner'] + 0x78, 8)
        return tokens
    yield Case('original eight bit color table owner missing', 0x46aeb0, missing_color_tables,
               receiver=lambda t: t['state'], arguments=(3, 1))
    # Opaque XMI bytes go to the physical Miles service through the real track constructor.
    xmi = b'FORM' + bytes(random_source.randrange(256) for _ in range(28))
    for selection in (0, 1):
        for second in (0, 0x98765432):
            for variant, music in (
                    ('empty', {'LEVEL3': [], 'GAME': []}),
                    ('preferred', {'LEVEL3': [('PLAY0', xmi), ('BOSS0', xmi)],
                                   'GAME': [('POWERUP0', xmi), ('MONOLITH', xmi)]}),
                    ('fallback', {'LEVEL3': [('PLAY', xmi), ('BOSS', xmi)],
                                  'GAME': [('POWERUP', xmi), ('MONOLITH', xmi)]}),
                    ('empty payload', {'LEVEL3': [('PLAY0', b''), ('BOSS0', b''), ('PLAY', b''), ('BOSS', b'')],
                                       'GAME': [('POWERUP0', b''), ('POWERUP', b''), ('MONOLITH', b'')]})):
                yield Case(f'original music {variant} selection {selection} second {second:#x}',
                           0x46aeb0, level_graph_setup(palette_data, world_data=minimal_world(),
                                                     captain=True, music=music, selection=selection),
                           receiver=lambda t: t['state'], arguments=(3, second))

    yield Case('original music Miles initialization failure releases sequence', 0x46aeb0,
               level_graph_setup(palette_data, world_data=minimal_world(), captain=True,
                                 music={'LEVEL3': [('PLAY0', xmi), ('BOSS0', xmi)],
                                        'GAME': [('POWERUP0', xmi), ('MONOLITH', xmi)]}, audio_error=True),
               receiver=lambda t: t['state'], arguments=(3, 1))

    import struct
    animation = struct.pack('<8I', 0, 0, 0, 1, 0, 0, 0, 0)
    animation += struct.pack('<10h', 0, 37, 0, -2, 3, -4, 5, 6, 7, 8)
    yield Case('original nonempty ANI directory parses frame data and registers animation', 0x46aeb0,
               level_graph_setup(palette_data, world_data=minimal_world(), captain=True, animation=animation),
               receiver=lambda t: t['state'], arguments=(3, 1))

    def changed_demo_after_loading(env):
        tokens = level_graph_setup(palette_data, world_data=minimal_world(), captain=True)(env)
        observed = env.object(12, 'mode-change-observation', fill=0)
        def pending_messages(e, call):
            e.put(observed, tokens['owner'], e.get(tokens['owner'] + 0x9c), 1)
            e.put(tokens['owner'] + 0x9c, 1)
            return 0
        env.override(0x546cac, pending_messages)
        return tokens
    yield Case('initialize reloads mode changed during final physical message pump', 0x46a6d0,
               changed_demo_after_loading, receiver=lambda t: t['state'],
               arguments=(lambda t: t['owner'], 3, 0x87))
    def changed_level_directory(env):
        tokens = level_graph_setup(palette_data, world_data=minimal_world(), captain=True)(env)
        replacement = directory(env, 'LEVEL3-replacement-with-no-tiles')
        observed = env.object(12, 'directory-change-observation', fill=0)
        def update_window(e, call):
            e.put(observed, call.arguments[0], e.get(tokens['state'] + 0x1c), replacement)
            e.put(tokens['state'] + 0x1c, replacement)
            return 1
        env.override(0x546ccc, update_window)
        return tokens
    yield Case('loadLevel reloads directory changed during physical UpdateWindow', 0x46aeb0,
               changed_level_directory, receiver=lambda t: t['state'], arguments=(3, 1))


def resource_directory(env, name, kind, resources, enumerated=False):
    target = directory(env, name)
    env.put(target + 0x3c, 5)
    resource_type = env.object(0x2c, name + '-type', fill=0)
    env.put(resource_type, kind)
    env.put(resource_type + 0x10, target + 0x44, kind % 9)
    type_buckets = env.object(9 * 16, name + '-types', fill=0)
    type_node = env.object(0x18, name + '-type-node', fill=0)
    env.put(type_node + 0x14, resource_type)
    env.put(type_buckets + 8 + 16 * (kind % 9), type_node + 4)
    env.put(target + 0x44, 9, type_buckets)
    buckets = env.object(19 * 16, name + '-resource-buckets', fill=0)
    env.put(resource_type + 0x24, 19, buckets)
    heads = {}
    for resource_name, data in resources:
        obj = env.object(0x5c, resource_name + '-resource', fill=0)
        text = env.object(len(resource_name) + 1, resource_name + '-name', data=resource_name.encode() + b'\0')
        payload = env.object(max(1, len(data)), resource_name + '-payload', data=data or b'\0')
        env.put(obj, text)
        env.put(obj + 8, resource_type)
        if enumerated:
            enum_buckets = env.object(16, resource_name + '-id-buckets', fill=0)
            enum_node = env.object(0x18, resource_name + '-id-node', fill=0)
            env.put(enum_node + 0x14, obj)
            env.put(enum_buckets + 8, enum_node + 4)
            env.put(resource_type + 0x1c, 1, enum_buckets)
            env.put(obj + 0x54, resource_type + 0x1c, 0)
        env.put(obj + 0x14, len(data), payload if data else 0)
        env.put(obj + 0x24, target)
        bucket = len(resource_name) % 19
        node = env.object(0x18, resource_name + '-node', fill=0)
        env.put(node + 4, heads.get(bucket, 0))
        env.put(node + 0x14, obj)
        heads[bucket] = node + 4
    for bucket, head in heads.items():
        env.put(buckets + 8 + 16 * bucket, head)
    return target


def minimal_world(valid=True):
    import struct
    data = bytearray(0x698)
    def put(offset, *words):
        struct.pack_into('<' + 'I' * len(words), data, offset, *words)
    put(0, 0x5f4 if valid else 0x5f5)
    data[0x10:0x18] = b'Level 3\0'
    put(0x2dc, 1, 0x5f4)
    plane = 0x5f4
    put(plane, 0xa0)
    put(plane + 8, 1)
    data[plane + 0x10:plane + 0x15] = b'Main\0'
    put(plane + 0x58, 64, 64, 1, 1)
    put(plane + 0x70, 100, 100)
    put(plane + 0x84, 0x694)
    put(0x694, 0xffffffff)
    return bytes(data)


def distinction_cases(random_source):
    """Nonzero prior state, separate surfaces, and live stack distinguish real writes."""
    for index in range(3):
        seed = bytes(random_source.randrange(1, 256) for _ in range(0x774))
        def constructor(env, data=seed):
            # setup_state normally nulls this live pointer for loader cases.
            tokens = setup_state(seed=data)(env)
            env.write(tokens['state'] + 0x2c, data[0x2c:0x30])
            return tokens
        yield Case(f'constructor clears nonzero previous palette {index}', 0x40b5c0,
                   constructor, receiver=lambda t: t['state'])

    palette_data = bytes(random_source.randrange(256) for _ in range(768))
    stack = bytes(random_source.randrange(1, 256) for _ in range(128))
    markers = [random_source.randrange(1, 0x7fffffff) for _ in range(32)]
    def level(env):
        tokens = level_graph_setup(palette_data, world_data=minimal_world(), captain=True)(env)
        state, owner = tokens['state'], tokens['owner']
        # Fields cleared by owned startup, rather than used as live pointers.
        for offset, marker in zip((0x44, 0x48, 0x158, 0x258, 0x764, 0x15c,
                                   0x38, 0x25c, 0x768, 0x76c, 0x770, 0x760), markers):
            env.put(state + offset, marker)
        for address, marker in zip((0x538418, 0x54316c, 0x537210, 0x53c9c0,
                                    0x5349dc, 0x534ca4), markers[12:]):
            env.put(address, marker)
        env.put(owner + 0x130, markers[20])
        # Distinct physical interfaces and engine wrappers make front/back reads visible.
        scene = env.get(state + 0xc)
        display = env.get(scene + 4)
        primary = env.get(display + 0x10)
        back = env.get(display + 0x14)
        old_wrapper = env.get(primary + 0x2c)
        back_wrapper = env.object(0xbc, 'separate-back-wrapper', data=env.read(old_wrapper, 0xbc))
        front_com = env.get(old_wrapper + 8)
        back_com = env.object(4, 'separate-back-COM', words=[env.get(front_com)])
        env.put(back_wrapper + 8, back_com)
        env.put(back + 0x2c, back_wrapper)
        return tokens
    for function in (0x46aeb0, 0x46a6d0):
        yield Case(f'distinct front back and nonzero prior state {function:#x}', function,
                   level, receiver=lambda t: t['state'],
                   arguments=((3, 0x87319524) if function == 0x46aeb0 else
                              (lambda t: t['owner'], 3, 0x92714683)),
                   initial_stack=((-128, stack),))

    for flags in (0, 4, 8):
        def scene(env):
            target = scene_graph()(env)
            # Constructor overwrites all child slots; retain distinct original holes.
            for offset in range(0, 0x38, 4):
                env.put(target + offset, markers[offset // 4])
            return target
        yield Case(f'scene replaces nonzero child slots flags {flags}', 0x4cea10,
                   scene, receiver=lambda t: t, arguments=(0x65319724, 640, 480, 8, flags),
                   initial_stack=((-128, stack),))

    def initialize(env):
        tokens = setup_state(level=7, include_level=True)(env)
        # Unlike loadLevel, State::initialize must clear its old palette itself.
        env.put(tokens['state'] + 0x2c, markers[0])
        env.put(0x53ec44, markers[1])
        return tokens
    yield Case('state initialization nonzero palette and randomized build identifier', 0x48f0d0,
               initialize, receiver=lambda t: t['state'],
               arguments=(lambda t: t['owner'], 7, markers[2]), initial_stack=((-128, stack),))
