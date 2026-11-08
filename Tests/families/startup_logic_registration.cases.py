"""Independent original-backed startup registration cases."""
from clawparity.cases import Case
from clawparity.fixtures import release

REGISTER = 0x401000
CREATE = 0x4D6340
NEW = 0x4F63EC
DELETE = 0x4F6428
STATE_ARRAYS = (
    0x534820, 0x534850, 0x534888, 0x5348B8, 0x5348E8, 0x534910, 0x534948,
    0x534978, 0x5349B8, 0x5349E0, 0x534A10, 0x534A38, 0x534A88, 0x534AB0,
    0x534AD8, 0x534B00, 0x534B28, 0x534B50, 0x534B78, 0x534BA0, 0x534BC8,
    0x534BF8, 0x534C28, 0x534C58, 0x534ED0, 0x537278, 0x5372A8, 0x5372D8,
    0x537308, 0x537338, 0x537598, 0x5375D8, 0x537608, 0x537638, 0x537698,
    0x5376C8, 0x5376F8, 0x537728, 0x537758, 0x537788, 0x5377B8, 0x5377E8,
    0x537818, 0x537848, 0x537878, 0x537980, 0x5379D0, 0x537A00, 0x537A30,
    0x537A60, 0x537A90, 0x537AC0, 0x537AF0, 0x537B20, 0x537B68, 0x537BA0,
    0x537BD0, 0x537C00, 0x537C30, 0x537C60, 0x537EA0, 0x538428, 0x538458,
    0x53C0E8, 0x53C118, 0x53C148, 0x53C178, 0x53C1A8, 0x53C1D8, 0x53C208,
    0x53C238, 0x53C270, 0x53C2A0, 0x53C2C8, 0x53C2F8, 0x53C328, 0x53C9D0,
    0x53CA08, 0x53CA40, 0x53CA70, 0x53CAA0, 0x53EC00, 0x53EC68,
)


def imports(env):
    env.override(0x5469E4, lambda env, call: len(env.cstr(call.arguments[0])))

    def decrement(env, call):
        at = call.arguments[0]
        value = (env.get(at) - 1) & 0xFFFFFFFF
        env.put(at, value)
        return value

    env.override(0x5469E8, decrement)
    env.override(DELETE, release())


def startup_setup(start, lower, marker, changing, result):
    def setup(env):
        imports(env)
        env.override(NEW, lambda env, call: env.object(call.arguments[0], "original helper allocation", fill=marker))
        # Bounds and backing only: original initializers publish all handler values.
        empty = env.get(0x52E1CC)
        for base in STATE_ARRAYS:
            words = [empty if base == 0x537698 else marker * 0x01010101] * 256
            backing = env.object(1024, f"state storage {base:x}", words=words)
            env.put(base + 8, lower, lower + 255, backing, 0, 4, 0, 0)
        env.put(0x52712C, start)
        env.put(0x537668 + 0x14, 0, 0, 0, 0, 0, 0)
        world = env.object(0x40, "world", fill=marker)
        registrars = [env.object(0x30, f"registrar {i}", fill=marker ^ (i + 1)) for i in range(2)]
        tables = [env.object(0x28, f"registration vtable {i}") for i in range(2)]
        log = env.object(4 + 256 * 32, "registration observations", fill=0)

        def observe(env, call):
            index = env.get(log)
            callback, name, flags = call.arguments
            env.put(log + 4 + index * 32, call.receiver, callback, name, flags,
                    env.get(0x52712C), env.get(world + 0x14), env.get(call.receiver), len(env.cstr(name)))
            env.put(log, index + 1)
            if changing:
                following = registrars[(index + 1) % 2]
                env.put(world + 0x14, following)
                env.put(following, tables[(index // 2 + 1) % 2])
            return result ^ index

        for i, table in enumerate(tables):
            env.put(table + 0x24, env.stub(f"register logic method {i}", "thiscall", 3, observe))
        for i, registrar in enumerate(registrars):
            env.put(registrar, tables[i])
        env.put(world + 0x14, registrars[0])
        return world

    return setup


def factory_setup(name, callback, flags, marker, mode, mutate):
    def setup(env):
        imports(env)
        registrar = env.object(0x40, "factory registrar", fill=marker)
        context = env.object(0x30, "factory context", fill=marker ^ 0x55)
        changed_context = env.object(0x30, "changed factory context", fill=marker ^ 0xAA)
        key = env.object(len(name) + 1, "requested name", data=name + b"\0")
        bucket_count = 7
        env.put(registrar + 0xC, context)
        # Embedded map begins at +0x10. Its item count at +0x1c also
        # supplies the construction context word consumed by the owned entry.
        env.put(registrar + 0x14, 0, bucket_count, 3, 0, 0, 4)
        buckets = env.object(bucket_count * 4, "map buckets", fill=0)
        if mode != "allocate buckets":
            env.put(registrar + 0x14, buckets)
        h = 0
        for byte in name:
            h = (h * 33 + (byte if byte < 128 else byte - 256)) & 0xFFFFFFFF
        bucket = h % bucket_count
        if mode == "existing":
            prior = env.object(0x174, "previous mapped value", fill=marker ^ 0x33)
            node = env.object(16, "existing matching entry", words=[0, bucket, key, prior])
            # Start with a colliding non-matching key, ensuring original lookup walks the chain.
            different = env.object(12, "collision key", data=b"not-the-key\0")
            collision = env.object(16, "collision entry", words=[node, bucket, different, context])
            env.put(buckets + bucket * 4, collision)
        receipt = env.object(16, "allocation and deletion observations", fill=0)

        def allocation(env, call):
            if env.get(receipt) == 0:
                env.put(receipt, 1, env.get(registrar + 0xC), env.get(registrar + 0x1C))
                if mutate:
                    env.put(registrar + 0xC, changed_context)
                    env.put(registrar + 0x1C, 9)
            return env.object(call.arguments[0], "allocated object", fill=marker)

        def deletion(env, call):
            address = call.arguments[0]
            # Preserve destructor writes before the heap object ceases to be live.
            env.put(receipt + 12, env.get(address + 4))
            env.release(address)
            return 0

        env.override(NEW, allocation)
        env.override(DELETE, deletion)
        return {"registrar": registrar, "key": key, "callback": callback, "flags": flags}

    return setup


def cases(random_source):
    for index, changing in enumerate((False, True, True)):
        start = random_source.randrange(1, 25)
        lower = -random_source.randrange(1, 9)
        marker = random_source.randrange(1, 255)
        yield Case(f"all registrations original state helpers variant {index}", REGISTER,
                   startup_setup(start, lower, marker, changing, (0, 1, 0xFFFFFFFF)[index]),
                   arguments=(lambda token: token,))
    for index, (name, callback, flags, mode, mutate) in enumerate((
        (b"CaptainClaw", 0x418400, 0, "existing", False),
        (b"", 1, 1, "existing", True),
        (b"High\xffByte", 0xFFFFFFFF, 0x80000000, "existing", True),
        (b"new-logic", 0x418400, 2, "new entry", False),
        (b"new-map-logic", 0x418400, 0xFFFFFFFF, "allocate buckets", True),
        (b"failure", 0, 0, "existing", False),
        (b"failure flags", 0, 0xFFFFFFFF, "new entry", True),
    )):
        marker = random_source.randrange(1, 255)
        yield Case(f"factory {index} {mode} callback {callback:x}", CREATE,
                   factory_setup(name, callback, flags, marker, mode, mutate),
                   receiver=lambda token: token["registrar"],
                   arguments=(lambda token: token["callback"], lambda token: token["key"], lambda token: token["flags"]))
    for index in range(4):
        name = bytes(random_source.randrange(65, 91) for _ in range(random_source.randrange(1, 48)))
        callback = random_source.randrange(1, 0xFFFFFFFF)
        flags = random_source.getrandbits(32)
        marker = random_source.randrange(1, 255)
        yield Case(f"random existing map {index}", CREATE,
                   factory_setup(name, callback, flags, marker, "existing", index % 2 == 0),
                   receiver=lambda token: token["registrar"],
                   arguments=(lambda token: token["callback"], lambda token: token["key"], lambda token: token["flags"]))
