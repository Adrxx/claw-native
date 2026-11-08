"""Original v1.3 palette and tempo service observations."""
from clawparity.cases import Case
GRAY, TOGGLE, TEMPO = 0x463BC0, 0x463C90, 0x4B55E0
SET, SAVE, RESTORE, BACKEND = 0x4BC4F0, 0x4BC560, 0x4BC5B0, 0x50C61C


def palette_setup(palette, marker, result, redirect=False):
    def setup(env):
        owner = env.object(0x40, "palette owner", fill=0xB7)
        providers = [env.object(0x40, "provider " + str(i), fill=0x31 + i) for i in range(2)]
        palettes = [env.object(0x400, "palette " + str(i), data=palette) for i in range(2)]
        interfaces = [env.object(8, "interface " + str(i), fill=0x51 + i) for i in range(2)]
        tables = [env.object(0x20, "methods " + str(i), fill=0) for i in range(2)]
        record = env.object(0x2000, "service order and palette bytes", fill=0xD3)
        env.put(record, 0)
        env.put(owner + 0x10, providers[0])
        for i in range(2):
            env.put(providers[i] + 4, interfaces[i])
            env.put(providers[i] + 0xC, palettes[i])
            env.put(palettes[i] + 0xDC, marker)
            env.put(interfaces[i], tables[i])

        def observe(env, kind, call, data=b""):
            n = env.get(record)
            at = record + 4 + n * 0x480
            env.put(at, kind, call.receiver, len(call.arguments), *call.arguments)
            env.put(at + 0x30, env.get(owner + 0x10), env.get(providers[0] + 0xC), env.get(providers[1] + 0xC))
            if data:
                env.write(at + 0x40, data)
            env.put(record, n + 1)

        def entries(env, call):
            observe(env, 1, call)
            env.write(call.arguments[4], palette)
            if redirect:
                env.put(owner + 0x10, providers[1])
            return result
        for table in tables:
            env.put(table + 0x10, env.stub("palette GetEntries", "stdcall", 5, entries))

        def save(env, call):
            observe(env, 2, call)
            if redirect:
                env.put(owner + 0x10, providers[1])
            return result

        def restore(env, call):
            observe(env, 3, call)
            env.put(call.receiver + 0x20, 0xAB123456)
            return result

        def set_entries(env, call):
            observe(env, 4, call, env.read(call.arguments[2], 0x400))
            env.put(call.receiver + 0x24, 0xBA654321)
            return result
        env.override(SAVE, save)
        env.override(RESTORE, restore)
        env.override(SET, set_entries)
        return {"owner": owner}
    return setup


def tempo_setup(ready, result, old_tempo, handle, changed_handle=None):
    def setup(env):
        target = env.object(0x80, "music receiver", fill=0xC5)
        table = env.object(0x20, "music methods", fill=0)
        record = env.object(0x100, "music observations", fill=0xD7)
        env.put(record, 0)
        env.put(target, table)
        env.put(target + 0x54, old_tempo, handle)

        def observe(env, kind, call):
            n = env.get(record)
            env.put(record + 4 + n * 0x40, kind, call.receiver, len(call.arguments), *call.arguments)
            env.put(record + 0x24 + n * 0x40, env.get(target + 0x54), env.get(target + 0x58))
            env.put(record, n + 1)

        def readiness(env, call):
            observe(env, 1, call)
            if changed_handle is not None:
                env.put(target + 0x54, 0x13579BDF, changed_handle)
            return ready

        def backend(env, call):
            observe(env, 2, call)
            env.put(target + 0x54, 0x2468ACE0)
            return result
        env.put(table + 0x18, env.stub("music ready", "thiscall", 0, readiness))
        env.override(BACKEND, backend)
        return {"target": target}
    return setup


def cases(random_source):
    for function in (GRAY, TOGGLE):
        yield Case("null palette owner " + hex(function), function, arguments=(0,))
    patterns = [
        bytes(x for i in range(256) for x in (i, (i * 73 + 19) & 255, 255 - i, (i * 29 + 7) & 255)),
        bytes(x for i in range(256) for x in (0, i, 0, (i + 1) & 255)),
        bytes(x for i in range(256) for x in (0, 0, i, (i + 73) & 255)),
        bytes(x for i in range(256) for x in (i, 0, 0, (i + 129) & 255)),
        bytes(x for i in range(256) for x in (i, i, i, 255 - i)),
    ]
    patterns += [bytes(random_source.randrange(256) for _ in range(1024)) for _ in range(10)]
    for i, palette in enumerate(patterns):
        for result in (0, 0x80004005):
            yield Case(f"grayscale all entries pattern {i} service {result:#x}", GRAY,
                       palette_setup(palette, 0xA1010203, result, bool(i % 2)),
                       arguments=(lambda t: t["owner"],))
    markers = (0x00000000, 0xFF000000, 0xABFFFFFF, 0x887F7F7F,
               0x00010100, 0x00000101, 0x00010001, 0xFF030201,
               0xABFFFFFE, 0xABFEFFFF)
    for i, marker in enumerate(markers):
        for result in (0, 0xFFFFFFFF):
            yield Case(f"palette toggle marker {marker:#x} service {result:#x}", TOGGLE,
                       palette_setup(patterns[i % len(patterns)], marker, result, bool(i % 2)),
                       arguments=(lambda t: t["owner"],))
    inputs = [(0, 0), (1, 1), (100, 0), (0xFFFFFFFF, 0x80000000),
              (0x7FFFFFFF, 0xFFFFFFFF), (0x80000000, 0x12345678)]
    inputs += [(random_source.getrandbits(32), random_source.getrandbits(32)) for _ in range(12)]
    for i, (tempo, duration) in enumerate(inputs):
        for ready in (0, 1, 0x80000000):
            changed = None if i % 2 else random_source.getrandbits(32)
            yield Case(f"tempo {i} readiness {ready:#x}", TEMPO,
                       tempo_setup(ready, (0, 0xFFFFFFFF)[i % 2], random_source.getrandbits(32),
                                   random_source.getrandbits(32), changed),
                       receiver=lambda t: t["target"], arguments=(tempo, duration))
