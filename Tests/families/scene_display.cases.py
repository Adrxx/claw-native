"""Original-backed scene/display cases; only physical COM and supplied callbacks are scripted."""
from clawparity.cases import Case

NEW = 0x4F63EC
DELETE = 0x4F6428


def zero(env, *args, **kwargs):
    return env.object(*args, fill=0, **kwargs)


def record(env, log, tag, call, extra=()):
    index = env.get(log)
    env.put(log, index + 1)
    values = (tag, call.receiver, len(call.arguments), *call.arguments, *extra)
    env.put(log + 4 + index * 64, *values)


def quiet(env):
    env.put(0x54139C, 0, 0, 0, 0)
    env.put(0x541378, 0x51079C, 0, 0, 0, 0)
    env.override(0x546850, lambda e, c: 0x80004005)


def obj(env, size=0xBC, name="receiver"):
    # Distinct live fields detect accidental clearing/copying beyond the owned extent.
    return zero(env, size, name, words=[(0xA3100000 + i * 0x10203) & 0xFFFFFFFF for i in range(size // 4)])


def plain(fields=(), size=0xBC):
    def setup(env):
        quiet(env)
        receiver = obj(env, size)
        for offset, value in fields:
            env.put(receiver + offset, value)
        return {"receiver": receiver}
    return setup


def case(label, function, setup=None, arguments=()):
    return Case(label, function, setup, receiver=lambda t: t["receiver"], arguments=arguments)


def free_nodes(env, header, count=10):
    nodes = zero(env, count * 12, "free-list-nodes")
    for i in range(count):
        env.put(nodes + 12 * i, nodes + 12 * (i + 1) if i + 1 < count else 0, 0, 0)
    env.put(header, 0x51000C, 0, 0, 0, nodes, 0, count)


def physical_scene(options=None):
    options = {} if options is None else options
    def setup(env):
        quiet(env)
        log = zero(env, 0x10000, "observations")
        receiver = obj(env, 0xBC)
        parent = zero(env, 0x40, "scene")
        alternate = zero(env, 0x40, "alternate-scene")
        manager = zero(env, 0x884, "directdraw-manager")
        com = zero(env, 4, "directdraw-interface")
        methods = zero(env, 0x90, "directdraw-methods")
        surface_com = zero(env, 4, "surface-interface")
        surface_methods = zero(env, 0x90, "surface-methods")
        source = zero(env, 0xBC, "source-surface")
        outer = zero(env, 0x14, "owner")
        inner = zero(env, 0x30, "owner-display")
        env.put(outer + 0x10, inner)
        env.put(inner + 0x2C, source)
        env.put(parent + 4, outer)
        env.put(parent + 0x1C, manager)
        env.put(parent + 0x30, 0x13572468, options.get("flags", 0), options.get("sticky", 0))
        env.put(alternate + 0x38, options.get("alternate_sticky", 0))
        env.put(receiver + 4, options.get("type", 2), 0xF1234500, parent)
        env.put(receiver + 0x10, 0, 0, 0)
        env.put(receiver + 0x2C, 0, 1)
        env.put(manager, com)
        env.put(manager + 0x474, 16)
        env.put(manager + 0x880, options.get("manager_error", 0))
        free_nodes(env, manager + 0x3B8)
        env.put(manager + 0x3F0, 0x51079C, 0, 0, 0, 0)
        env.put(com, methods)
        env.put(surface_com, surface_methods)
        env.put(source + 8, surface_com)
        env.put(0x541398, 0 if options.get("ddraw_fail") else com)

        def switch_parent(e):
            if options.get("switch_parent"):
                e.put(receiver + 0xC, alternate)

        def desc(e, c):
            record(e, log, 0x58, c)
            p = c.arguments[1]
            e.put(p + 8, options.get("height", 13), options.get("width", 19), options.get("pitch", 89))
            e.put(p + 0x54, options.get("depth", 24))
            return options.get("desc_result", 0)

        def create(e, c):
            record(e, log, 0x18, c)
            n = e.calls_so_far(c.function)
            fail = options.get("create_fail", 0)
            if fail == n or fail == -1:
                switch_parent(e)
                return 0x80004005
            e.put(c.arguments[2], surface_com)
            if options.get("change_type"):
                e.put(receiver + 4, 2)
            if options.get("create_mutate_width"):
                e.put(receiver + 0x10, 0x556677)
            return 0

        def attached(e, c):
            record(e, log, 0x30, c, (e.get(c.arguments[1]),))
            if options.get("attached_fail"):
                switch_parent(e)
                return 0x887601C2
            e.put(c.arguments[2], surface_com)
            if options.get("change_type"):
                e.put(receiver + 4, 2)
            return 0

        def cooperative(e, c):
            record(e, log, 0x50, c)
            if options.get("coop_fail"):
                if "callback_error" in options:
                    e.put(manager + 0x880, options["callback_error"])
                switch_parent(e)
                return 0x80004005
            return 0

        def display_mode(e, c):
            record(e, log, 0x54, c)
            return options.get("mode_result", 0)

        def get_mode(e, c):
            record(e, log, 0x130, c)
            e.put(c.arguments[1] + 0x54, 24)
            e.put(c.arguments[1] + 0x58, 0xFF0000, 0xFF00, 0xFF)
            return options.get("mode_desc_result", 0)

        def callback(tag, result=0):
            def effect(e, c):
                record(e, log, tag, c)
                return result
            return effect

        for offset, argc, effect in [(0x18, 4, create), (0x20, 5, callback(0x20)), (0x2C, 3, callback(0x2C)), (0x30, 2, get_mode), (0x50, 3, cooperative), (0x54, 4, display_mode)]:
            env.put(methods + offset, env.stub(f"physical DD +{offset:x}", "stdcall", argc, effect))
        for offset, argc, effect in [(8, 1, callback(8)), (0x30, 3, attached), (0x58, 2, desc), (0x74, 3, callback(0x74))]:
            env.put(surface_methods + offset, env.stub(f"physical surface +{offset:x}", "stdcall", argc, effect))

        def alloc(e, c):
            record(e, log, 0xA110C, c)
            if e.calls_so_far(c.function) == options.get("fail_allocation"):
                return 0
            return e.object(c.arguments[0], "allocation")
        env.override(NEW, alloc)
        return dict(receiver=receiver, parent=parent, alternate=alternate, manager=manager, com=surface_com, source=source, log=log)
    return setup


def manager_setup(options=None):
    def setup(env):
        tokens = physical_scene(options)(env)
        tokens["receiver"] = tokens["manager"]
        return tokens
    return setup


def descriptor_setup(result, descriptor=True):
    def setup(env):
        tokens = physical_scene()(env)
        receiver = obj(env)
        methods = zero(env, 0x30, "supplied-surface-methods")
        def forward(e, c):
            record(e, tokens["log"], 0x220, c)
            return result
        env.put(receiver, methods)
        env.put(receiver + 8, tokens["com"])
        env.put(methods + 0x20, env.stub("supplied initialize", "thiscall", 1, forward))
        descriptor_pointer = obj(env, 0x6C, "input-description") if descriptor else 0
        tokens.update(receiver=receiver, descriptor=descriptor_pointer)
        return tokens
    return setup


def destructor_setup(kind, surface=True, own=True):
    def setup(env):
        t = physical_scene()(env)
        r = obj(env)
        env.put(r + 8, t["com"] if surface else 0)
        env.put(r + 0x78, 0)
        env.put(r + 0x90, 0x51079C, 0, 0, 0, 0)
        env.put(r + 0xC, t["parent"])
        env.put(r + 0x2C, 0, int(own))
        if kind == "child" and surface:
            item = zero(env, 0xBC, "owned-surface")
            vt = zero(env, 8, "owned-surface-methods")
            node = zero(env, 12, "list-node")
            sentinel = zero(env, 12, "remaining-node")
            env.put(node, sentinel, 0, item)
            env.put(sentinel, 0, node, 0)
            env.put(t["manager"] + 0x3BC, node, sentinel, 2)
            env.put(item, vt, node)
            def destroy(e, c):
                record(e, t["log"], 0xD00, c, (e.get(r + 0x2C), e.get(r + 0x10)))
                e.release(c.receiver)
                return 0
            env.put(vt, env.stub("supplied owned surface destructor", "thiscall", 1, destroy))
            env.put(r + 0x2C, item)
        t["receiver"] = r
        return t
    return setup


def holder_setup(mask=7, mutate=False):
    def setup(env):
        quiet(env)
        r = obj(env, 0x1C)
        log = zero(env, 4096, "holder-observations")
        children = [zero(env, 4, f"child-{i}") for i in range(4)]
        for i, child in enumerate(children):
            vt = zero(env, 8, f"child-methods-{i}")
            def destroy(e, c, index=i):
                record(e, log, index, c, tuple(e.get(r + k) for k in (0x10, 0x14, 0x18)))
                if mutate and index == 0:
                    e.put(r + 0x14, children[3])
                e.release(c.receiver)
                return 0
            env.put(child, vt)
            env.put(vt + 4, env.stub(f"supplied child destructor {i}", "thiscall", 1, destroy))
        env.put(r + 0x10, *(children[i] if mask & (1 << i) else 0 for i in range(3)))
        return dict(receiver=r)
    return setup


def resize_setup(change=0, fail=0, third=1, mutate=0):
    def setup(env):
        quiet(env)
        r = obj(env, 0x1C)
        log = zero(env, 4096, "resize-observations")
        children = [obj(env, 0x2C, f"resize-child-{i}") for i in range(6)]
        for i, child in enumerate(children):
            vt = zero(env, 0x2C, f"resize-methods-{i}")
            def resize(e, c, index=i):
                record(e, log, index + 10, c)
                if mutate == 1 and index == 0:
                    e.put(r + 0x14, children[3])
                if mutate == 2 and index == 1:
                    e.put(r + 0x18, children[4])
                return 0 if fail == index + 1 else 0x89ABCDEF
            def ready(e, c, index=i):
                record(e, log, index + 20, c)
                if mutate == 3:
                    e.put(r + 0x18, children[5])
                return third == 1
            env.put(child, vt)
            env.put(child + 0x10, 71, 53, 24)
            env.put(vt + 0x28, env.stub(f"supplied resize {i}", "thiscall", 3, resize))
            env.put(vt + 0x14, env.stub(f"supplied readiness {i}", "thiscall", 0, ready))
        if change < 3:
            env.put(children[0] + 0x10 + change * 4, (72, 54, 32)[change])
        if change == 3:
            env.put(children[0] + 0x10, 71, 53, 24)
        env.put(r + 0x10, children[0], children[1], children[2] if third else 0)
        return dict(receiver=r)
    return setup


def queue_setup(counters=(), ready=0, mutate=0):
    def setup(env):
        quiet(env)
        r = obj(env, 0x2C)
        log = zero(env, 4096, "queue-observations")
        target = zero(env, 4, "render-target")
        tvt = zero(env, 0x18, "render-target-methods")
        env.put(target, tvt)
        items = [obj(env, 0x68, f"render-item-{i}") for i in range(len(counters))]
        nodes = [zero(env, 12, f"queue-node-{i}") for i in range(len(counters))]
        env.put(r + 0x10, 0x51000C, nodes[0] if nodes else 0, nodes[-1] if nodes else 0, len(nodes), 0, 0, 10)
        for i, (item, node, counter) in enumerate(zip(items, nodes, counters)):
            vt = zero(env, 0x2C, f"render-methods-{i}")
            env.put(item, vt)
            env.put(item + 0x64, counter)
            env.put(node, nodes[i + 1] if i + 1 < len(nodes) else 0, nodes[i - 1] if i else 0, item)
            def draw(e, c, index=i):
                record(e, log, index + 30, c, (e.get(c.receiver + 0x64),))
                if mutate == 1:
                    e.put(c.receiver + 0x64, 1)
                if mutate == 3 and index == 0:
                    e.put(nodes[0], 0)
                return 0
            def destroy(e, c, index=i):
                record(e, log, index + 40, c, (e.get(c.receiver + 0x64),))
                e.release(c.receiver)
                return 0
            env.put(vt + 0x28, env.stub(f"supplied draw {i}", "thiscall", 2, draw))
            env.put(vt + 4, env.stub(f"supplied item destructor {i}", "thiscall", 1, destroy))
        def target_ready(e, c):
            record(e, log, 50, c)
            if mutate == 2:
                index = e.calls_so_far(c.function) - 1
                e.put(items[index] + 0x64, 0)
            return ready
        env.put(tvt + 0x14, env.stub("supplied target readiness", "thiscall", 0, target_ready))
        return dict(receiver=r, target=target)
    return setup


def cases(random_source):
    for function in (0x45FEC0, 0x4CACA0):
        yield case("reset distinct words", function, plain())
    for _ in range(5):
        values = tuple(random_source.getrandbits(32) for _ in range(3))
        yield case("constructor randomized fields", 0x4CAB90, plain(), values)
    for function in (0x45FE40, 0x4CABE0):
        for flag in (0, 1, 2, 0x100, 0xFFFFFFFF):
            yield case(f"child delete flag {flag:x}", function, destructor_setup("child"), (flag,))
    yield case("child destructor direct", 0x45FE60, destructor_setup("child"))
    for function in (0x4D4160,):
        for surf, own in ((False, False), (False, True), (True, False), (True, True)):
            yield case(f"owned removal {surf} {own}", function, destructor_setup("child", surf, own))
    for function in (0x4BB060, 0x4BC810):
        for flag in (0, 1, 2, 0x101):
            yield case(f"surface destructor flag {flag}", function, destructor_setup("surface"), (flag,))
    for function in (0x4BB080, 0x4BC830):
        for surf in (False, True):
            yield case(f"surface destructor COM {surf}", function, destructor_setup("surface", surf))
    for function in (0x4CA8B0, 0x4CF780, 0x4CF760):
        for mask in (0, 1, 2, 4, 7):
            args = (mask & 1,) if function == 0x4CF760 else ()
            yield case(f"holder clear mask {mask}", function, holder_setup(mask), args)
        yield case("holder reloads next child", function, holder_setup(7, True), (0,) if function == 0x4CF760 else ())
    for function in (0x4CABC0, 0x4CACB0):
        for width, parent, kind, surf in ((0, 1, 0, 1), (-1, 1, 0, 1), (1, 0, 0, 1), (1, 1, -1, 1), (1, 1, 2, 0), (1, 1, -2, 1)):
            yield case(f"validity {width} {parent} {kind} {surf}", function, plain(((0x10, width), (0xC, parent), (4, kind), (0x2C, surf))))
    for surf, width, height in ((0, 1, 1), (1, 0, 1), (1, -1, 1), (1, 1, 0), (1, 1, -1), (1, 7, 11)):
        yield case(f"surface readiness {surf} {width} {height}", 0x4BB000, plain(((8, surf), (0x84, width), (0x88, height))))
    for mask in (0, 1, 3, 6, 7):
        yield case(f"holder readiness {mask}", 0x4CF730, plain(tuple((0x10 + i * 4, (i + 1) if mask & (1 << i) else 0) for i in range(3))))
    yield Case("constant capability", 0x4CF750)
    for width, height in ((0, 3), (-1, 3), (3, 0), (3, -1), (1, 1), (0x7FFFFFFF, 0x7FFFFFFF), (73, 59)):
        yield case(f"rectangle {width} {height}", 0x4CAC00, plain(), (width, height))
        for depth in (0, 8, 16, 24, 32, 33, 0xFFFFFFFF):
            yield case(f"geometry {width} {height} {depth}", 0x4CAC40, plain(), (width, height, depth))
    for result in (0, 1, 0x100, 0xFFFFFFFF):
        for descriptor in (False, True):
            yield case(f"descriptor forwarding {result:x} {descriptor}", 0x4B9150, descriptor_setup(result, descriptor), (0x24681357, lambda t: t["descriptor"]))
            yield case(f"descriptor normalized {result:x} {descriptor}", 0x4BFBD0, descriptor_setup(result, descriptor), (0x56781234, lambda t: t["descriptor"]))
        yield case(f"primary descriptor normalization {result:x}", 0x4BFB80, descriptor_setup(result), (0x24681357, 0xABCD1234, 0x47893211, 0xFEDCBA98))
    for depth in (0, 7, 8, 9, 16, 24, 32, 33, 0xFFFFFFFF):
        for error in (0, 0x80004005):
            options = dict(depth=depth, desc_result=error, pitch=random_source.getrandbits(32), width=random_source.randrange(1, 200), height=random_source.randrange(1, 80))
            yield case(f"COM description {depth} {error:x}", 0x4B91F0, physical_scene(options), (lambda t: t["com"],))
    for result in (0, 1, 0x100):
        for key in (-1, 0x6A5B4C3D):
            yield case(f"surface initialize {result:x} key {key}", 0x4BF970, descriptor_setup(result), (lambda t: t["manager"], 71, 53, 32, 0x80120304, key))
    for change in (0, 1, 2, 3):
        for fail in (0, 1, 2, 3):
            yield case(f"resize mismatch {change} failure {fail}", 0x4CA960, resize_setup(change, fail), (71, 53, 24))
    for third in (0, 2):
        yield case(f"resize optional third {third}", 0x4CA960, resize_setup(third=third), (71, 53, 24))
    for mutate in (1, 2, 3):
        yield case(f"resize reload mutation {mutate}", 0x4CA960, resize_setup(mutate=mutate), (71, 53, 24))
    for counters, ready, mutate in (((), 0, 0), ((4,), 0, 0), ((1,), 0, 0), ((0,), 0, 0), ((-1,), 0, 0), ((4, 3, 2), 1, 0), ((5, 1, 3), 0, 0), ((7, 9), 0, 1), ((7, 9), 0, 2), ((7, 9), 0, 3), ((-2147483648,), 0, 0)):
        yield case(f"renderer queue {counters} {ready} mutation {mutate}", 0x4D63C0, queue_setup(counters, ready, mutate), (0xCAFEBABE, lambda t: t["target"]))
    def overlap(env):
        t = descriptor_setup(0x80010001)(env)
        t["descriptor"] = t["receiver"] + 8
        return t
    yield case("description overlapping forward copy", 0x4B9150, overlap, (0x12345678, lambda t: t["descriptor"]))
    for geometry in ((0, 0, 0), (0x80000001, 0x80000003, 0xFFFFFFFD), (0x7FFFFFFF, 0x7FFFFFFD, 0)):
        width, height, pitch = geometry
        yield case(f"descriptor arithmetic wrap {geometry}", 0x4B91F0, physical_scene(dict(width=width, height=height, pitch=pitch, depth=32)), (lambda t: t["com"],))
    # Factory callbacks remain original game targets installed by their constructors.
    for fail in (0, 1):
        yield case(f"surface factory create failure {fail}", 0x4BC670, manager_setup(dict(create_fail=fail)), (19, 13, 24, 0x81230000, -1))
        yield case(f"primary factory create failure {fail}", 0x4BC890, manager_setup(dict(create_fail=fail)), (0x81230001,))
        yield case(f"attached factory failure {fail}", 0x4BCF80, manager_setup(dict(attached_fail=fail)), (lambda t: t["source"], 0x10203040))
    for typ in (1, 2):
        for sticky in (0, 0x76543210):
            for width, height in ((0, 13), (19, 0), (19, 13)):
                for fail in (0, 1):
                    yield case(f"child creation type {typ} sticky {sticky:x} size {width}x{height} fail {fail}", 0x4D4000, physical_scene(dict(type=typ, sticky=sticky, create_fail=fail, attached_fail=fail)), (width, height))
    yield case("child reloads type after attachment", 0x4D4000, physical_scene(dict(type=1, change_type=True)), (19, 13))
    for error in (0, 0x3E9, 0x3EA, 0x3EB, 0x3EC, 0x3ED, 0xFFFFFFFF):
        for sticky in (0, 0xABCDEF):
            yield case(f"primary manager error map {error:x} sticky {sticky:x}", 0x4D5510, physical_scene(dict(coop_fail=True, callback_error=error, sticky=sticky)), (319, 29, 24))
    for flags in (0, 2, 0x10, 0x12):
        for width in (320, 321):
            for fail in (0, 1):
                yield case(f"primary init flags {flags:x} width {width} fail {fail}", 0x4D5510, physical_scene(dict(flags=flags, create_fail=fail)), (width, 29, 24))
    for sticky in (0, 0xAABBCC):
        yield case(f"primary unready sticky {sticky:x}", 0x4D5510, physical_scene(dict(width=0, sticky=sticky)), (321, 29, 24))
    for options in ({}, dict(ddraw_fail=True), dict(mode_result=0x80004005), dict(mode_desc_result=0x80004005)):
        yield case(f"primary physical path {options}", 0x4D5510, physical_scene(options), (321, 29, 24))
    for flags in (0, 1):
        for stage in (0, 1, 2, 3):
            for sticky in (0, 0x55667788):
                options = dict(sticky=sticky, switch_parent=bool(stage), alternate_sticky=sticky)
                if stage == 1:
                    options.update(coop_fail=True)
                elif stage == 2:
                    options.update(attached_fail=True)
                elif stage == 3:
                    options.update(create_fail=2)
                yield case(f"holder initialize flags {flags} failure stage {stage} sticky {sticky:x}", 0x4CA6F0, physical_scene(options), (321, 29, 24, flags))
    for fail_at in (2, 3):
        yield case(f"holder later allocation {fail_at} primary fails", 0x4CA6F0, physical_scene(dict(fail_allocation=fail_at, coop_fail=True)), (321, 29, 24, 1))
    yield case("holder third allocation fails but skip flag permits return", 0x4CA6F0, physical_scene(dict(fail_allocation=3)), (321, 29, 24, 1))
    # Direct removal exercises the MFC node join and callback publication.
    def removal(env):
        t = destructor_setup("child")(env)
        t["item"] = env.get(t["receiver"] + 0x2C)
        t["receiver"] = t["manager"]
        return t
    yield case("surface manager removes node before destructor", 0x4BC4F0, removal, (lambda t: t["item"],))
