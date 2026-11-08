"""Original-driven Wolvington projectile and light cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import reallocate

NEW = 0x4F63EC
RAND = 0x4A3050
REALLOC = 0x4A9070


def obj(env, size, name, **options):
    options.setdefault("fill", 0)
    return env.object(size, name, **options)


def map_table(env, address, entries):
    buckets = obj(env, 4, "map buckets")
    head = 0
    for name, value in entries:
        key = obj(env, len(name) + 1, "map key", data=name.encode() + b"\0")
        node = obj(env, 16, "map association", words=[head, 0, key, value])
        head = node
    env.put(buckets, head)
    env.put(address + 4, buckets, 1)


def recorder(env, log, tag, convention="thiscall", argc=0, change=None):
    def effect(env, call):
        i = env.get(log)
        env.put(log, i + 1)
        env.put(log + 4 + i * 32, tag, call.receiver, *call.arguments)
        if change:
            change(env, call)
        return tag ^ 0x51432
    return env.stub("observed callback " + str(tag), convention, argc, effect)


def world_graph(env, random_word=0xA6512, spawn=False, cycle=False):
    world = obj(env, 0x220, "world")
    logic = obj(env, 0x60, "logic")
    context = obj(env, 0x50, "resource context")
    images = obj(env, 0x30, "image dictionary")
    classes = obj(env, 0x30, "class dictionary")
    cycles = obj(env, 0x30, "cycle dictionary")
    collider = obj(env, 0x80, "collision service")
    manager = obj(env, 0x40, "object manager")
    log = obj(env, 4096, "callback record")
    env.put(world + 8, random_word & ~0x10)
    env.put(world + 0xC, context)
    env.put(world + 0x4C, 31, 47)
    env.put(world + 0x64, 9)
    env.put(world + 0x6C, logic)
    env.put(world + 0x148, 0, 0)
    env.put(world + 0x164, random_word)
    env.put(logic + 0xC, context)
    env.put(context + 8, manager)
    env.put(context + 0x10, images, classes)
    env.put(context + 0x24, collider)
    env.put(context + 0x2C, cycles)
    env.put(manager + 0xC, context)
    env.put(manager + 0x28, 4)
    map_table(env, images + 0x10, [])
    entries = []
    if spawn:
        callback = recorder(env, log, 0x661, "cdecl", 1)
        prototype = obj(env, 0x20, "spawn prototype")
        env.put(prototype + 8, random_word)
        env.put(prototype + 0x10, callback)
        entries = [("GlitterBaby", prototype), ("WolvingtonLFX", prototype)]
    map_table(env, classes + 0x10, entries)
    entries = []
    if cycle:
        frame = obj(env, 0x30, "cycle frame")
        env.put(frame + 0x1C, 17)
        frame_list = obj(env, 4, "cycle frame list", words=[frame])
        animation = obj(env, 0x20, "animation cycle")
        env.put(animation + 0xC, frame_list, 1)
        entries = [("GAME_CYCLE50", animation), ("GAME_LIGHTFX_WOLVINGTONLFX", animation)]
    map_table(env, cycles + 0x10, entries)
    env.put(0x537668 + 0x18, 0)
    config = obj(env, 0x800, "configuration")
    env.put(0x5371FC, config)
    env.put(config + 0x124, 0)
    env.put(0x53724C, 0)
    env.put(0x537210, 0)
    return dict(world=world, logic=logic, context=context, manager=manager, log=log, config=config)


def lifecycle_setup(command, word, create=False, mode=0, configured=False, cycle=False):
    def setup(env):
        t = world_graph(env, word, spawn=configured, cycle=cycle)
        env.put(t["logic"] + 0x1C, command)
        if create:
            env.put(0x53724C, mode)
            env.put(t["config"] + 0x124, int(configured))
        else:
            impl = obj(env, 0x158, "existing implementation")
            methods = obj(env, 0x30, "implementation methods")
            env.put(impl, methods)
            env.put(impl + 0x10, t["logic"])
            env.put(t["logic"] + 0x18, impl)
            for offset in (4, 8, 12):
                env.put(methods + offset, recorder(env, t["log"], offset, "thiscall", 1))
            for offset in (0x10, 0x1C, 0x20):
                env.put(methods + offset, recorder(env, t["log"], offset))
            chars = obj(env, 32, "CString backing", words=[1, 3, 19], data=None)
            env.write(chars + 12, b"abc\0")
            cell = obj(env, 4, "CString cell", words=[chars + 12])
            env.put(0x537698 + 8, command, command, cell, cell, 4, 0, 0)
        return t
    return setup


def dispatch_setup(value, lower, upper, handler, word, second=False):
    def setup(env):
        log = obj(env, 4096, "dispatch observations")
        receiver = obj(env, 0x158, "dispatch receiver", fill=0x5A)
        callback = recorder(env, log, word)
        data = obj(env, (upper - lower + 1) * 4, "dispatch table")
        for i in range(upper-lower+1):
            env.put(data + 4*i, callback if handler else 0)
        env.put(0x534AD8 + 8, lower, upper, data, data, 4, 0, word)
        base = obj(env, 4, "base dispatch", words=[callback])
        env.put(0x538428 + 8, value, value, base, base, 4, 0, 0)
        if second:
            calls = obj(env, 4, "allocator count")
            def realloc_effect(env, call):
                old, size = call.arguments
                new = obj(env, max(4, size), "grown dispatch")
                env.put(new, callback)
                env.put(calls, env.get(calls)+1)
                # A physical allocator can change globals. Zero stride keeps the
                # real MFC grow's copy and clearing operations bounded while an
                # inverted range requires the owned dispatch to look up again.
                env.put(0x534AF0, 0)
                if env.get(calls) == 1:
                    if value < lower:
                        env.put(0x534AE4, value-1)
                    else:
                        env.put(0x534AE0, value+1)
                return new
            env.override(REALLOC, realloc_effect)
        return dict(receiver=receiver, log=log)
    return setup


def falling_setup(n, bounds, random_values, velocity, light_flags, sentinel, word, mutate=False):
    def setup(env):
        t = world_graph(env, word, spawn=True)
        receiver = obj(env, 0x158, "falling receiver")
        descriptor = t["world"]
        env.put(receiver + 0xC, descriptor)
        env.put(receiver + 0x12C, descriptor, t["logic"])
        env.put(receiver + 0x148, 0)
        env.put(receiver + 0x150, n)
        env.put(receiver + 0x120, word & 0x10000)
        env.write(receiver + 0x68, struct.pack("<dd", 102.75, -39.5))
        env.write(receiver + 0x50, struct.pack("<d", velocity))
        env.put(descriptor + 0x118, bounds[0], bounds[2], bounds[1], bounds[3])
        if light_flags is not None:
            light = obj(env, 0x80, "light world")
            logic = obj(env, 0x30, "light logic")
            animator = obj(env, 0x50, "light animator")
            light_desc = obj(env, 0x148, "light descriptor", fill=0x37)
            env.put(receiver + 0x154, light)
            env.put(light + 0x6C, logic)
            env.put(logic + 0x18, animator)
            env.put(animator + 0x2C, light_desc)
            env.put(animator + 0x38, 7)
            env.put(animator + 0x40, 19)
            env.put(light_desc + 0x40, light_flags)
            env.put(light_desc + 0x118, 0x80000000 if sentinel else 11)
            env.put(light_desc + 0x120, 23)
            env.put(light_desc + 0x128, 13)
            env.put(light_desc + 0x130, 29)
            env.put(light_desc + 0x138, 17)
            env.put(light_desc + 0x140, 31)
        count = obj(env, 4, "random count")
        def random_effect(env, call):
            i = env.get(count)
            env.put(count, i+1)
            if mutate and i == 1:
                env.put(receiver + 0x150, 1)
            return random_values[i % len(random_values)]
        env.override(RAND, random_effect)
        t["receiver"] = receiver
        return t
    return setup


def cases(random_source):
    for address in (0x410340, 0x458010):
        for command in (1, 28, 29, 30, 31, 999, 1000, 1001, 0xFFFFFFFF):
            yield Case(f"lifecycle {address:x} command {command:x}", address,
                       lifecycle_setup(command, random_source.getrandbits(24)),
                       arguments=(lambda t:t["world"],))
        for cycle in (False, True):
            yield Case(f"create {address:x} cycle {cycle}", address,
                       lifecycle_setup(0, random_source.getrandbits(24), True, cycle=cycle),
                       arguments=(lambda t:t["world"],))
    for mode, configured in ((0, False), (1, True), (0, True)):
        def setup(env, mode=mode, configured=configured):
            t = lifecycle_setup(0, random_source.getrandbits(24), True, mode, configured)(env)
            t["receiver"] = obj(env, 0x158, "direct constructor", fill=0x69)
            return t
        yield Case(f"constructor mode{mode} configured{configured}", 0x411CF0, setup,
                   receiver=lambda t:t["receiver"], arguments=(lambda t:t["world"],))
    for value, low, high in ((3, 1, 5), (1, 1, 5), (5, 1, 5), (-2, 1, 5), (8, 1, 5)):
        for handler in (False, True):
            yield Case(f"dispatch {value} handler{handler}", 0x411E70,
                       dispatch_setup(value, low, high, handler, random_source.randrange(1,1000)),
                       receiver=lambda t:t["receiver"], arguments=(value,))
    for value in (-2, 8):
        yield Case(f"dispatch repeats grown range {value}", 0x411E70,
                   dispatch_setup(value, 1, 5, True, random_source.randrange(1,1000), True),
                   receiver=lambda t:t["receiver"], arguments=(value,))
    for n in (-1, 0, 1, 2):
        for bounds, rands in (((-2, 3, -4, 5), (0, 32767)), ((3, 2, 5, 4), (0, 0)),
                              ((3, 2, 5, 4), (1, 1)), ((-3, 2, -6, 1), (0xFFFFFFFD, 7))):
            yield Case(f"falling emit {n} {bounds} {rands}", 0x412150,
                       falling_setup(n, bounds, rands, 1.0, None, False, random_source.getrandbits(24)),
                       receiver=lambda t:t["receiver"])
    yield Case("emission count changes during random callback", 0x412150,
               falling_setup(3, (-2,3,-4,5), (4,9), 1.0, None, False,
                             random_source.getrandbits(24), mutate=True),
               receiver=lambda t:t["receiver"])
    for velocity in (-2.0, 0.0, 2.0, float("nan")):
        for flags in (0x40, 0x42):
            for sentinel in (False, True):
                yield Case(f"light update {velocity} flags{flags} sentinel{sentinel}", 0x412150,
                           falling_setup(0, (-2,3,-4,5), (2,3), velocity, flags, sentinel,
                                         random_source.getrandbits(24)), receiver=lambda t:t["receiver"])
