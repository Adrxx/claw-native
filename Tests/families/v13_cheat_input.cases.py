"""Original-only inputs for the pinned v1.3 keyboard/cheat entries."""
from clawparity.cases import Case

MATCH = 0x424380
KEYDOWN = 0x46DDC0
LOOKUP = 0x4FC6B4
POST = 0x50C4CC
CLOCK = 0x535920
MASK = 0xFFFFFFFF
CHEATS = (
    "MPTWINTURBO", "MPLONGRANGE", "MPEASYMODE", "MPBOUNCECOUNT",
    "MPGLOOMY", "MPNOISE", "MPMAESTRO", "MPLANGSAM",
    "MPNORMALMUSIC", "MPWILDWACKY",
)


def encoded(text):
    return bytes((ord(c) + 0x11) & 255 for c in text)


def make_case(label, key=ord('A'), count=4, last=100, now=101,
              text=None, expected=None, lookup_result=1, pointer=True,
              command=0x8123, flags=0, cheated=0xA1B2C3D4,
              map_change=False, post_change=None, dispatch=False, paused=0,
              salt=0x39):
    def setup(env):
        # Interior receiver keeps small signed-negative counts valid too.
        backing = env.object(0x1C0, "cheat backing", fill=salt)
        cheat = backing + 0x40
        app = env.object(0x60, "application", fill=0x67)
        app2 = env.object(0x60, "replacement application", fill=0x93)
        window = env.object(0x10, "window", fill=0x4B)
        window2 = env.object(0x10, "replacement window", fill=0x57)
        game = env.object(0x20, "game input", fill=0xD1)
        entry = env.object(12, "command entry", fill=0x6D)
        record = env.object(0x800, "service observations", fill=0)
        hwnd = 0x13572468 ^ (salt << 16)
        env.put(cheat, hwnd)
        env.put(cheat + 0x120, count & MASK, last & MASK, cheated)
        if text is None:
            length = max(0, min(count, 201))
            payload = bytes((0x61 + i % 23) for i in range(length))
        else:
            payload = encoded(text)
        env.write(cheat + 0x20, payload + b'\0')
        env.put(entry, command & MASK, flags & MASK, 0x708192A3)
        env.put(game + 4, app)
        env.put(app + 4, window)
        env.put(app + 0xC, paused & MASK)
        env.put(app + 0x48, cheat)
        env.put(app2 + 4, window2)
        env.put(app2 + 0xC, 0xBADC0DE)
        env.put(app2 + 0x48, cheat)
        env.put(window + 4, 0xCAFE0357)
        env.put(window2 + 4, 0xDEAD2468)
        env.put(CLOCK, now & MASK)

        def observe(env, call, tag):
            index = env.get(record)
            at = record + 4 + index * 0x180
            env.put(record, index + 1)
            env.put(at, tag, call.receiver, len(call.arguments),
                    env.get(cheat), env.get(cheat + 0x120),
                    env.get(cheat + 0x124), env.get(cheat + 0x128),
                    env.get(entry), env.get(entry + 4), env.get(game + 4))
            env.write(at + 0x40, env.read(cheat + 0x20, 0xD0))
            return at

        def lookup(env, call):
            at = observe(env, call, 0x1111)
            actual = env.cstr(call.arguments[0])
            env.put(at + 0x28, env.get(call.arguments[1]))
            # Record dereferenced input, not an assertion inside the fixture.
            env.write(at + 0x30, bytes(actual[:12]).ljust(12, b'\0'))
            match = expected is None or actual == encoded(expected)
            env.put(call.arguments[1], entry if pointer and match else 0)
            if map_change:
                env.put(cheat, 0xF1234567)
                env.put(cheat + 0x120, 19)
                env.put(cheat + 0x124, 0x33445566)
                env.put(cheat + 0x128, 0x87654321)
                env.write(cheat + 0x20, b'CHANGED-BY-MAP\0')
                env.put(game + 4, app2)
            return lookup_result if match else 0

        def post(env, call):
            at = observe(env, call, 0x2222)
            env.put(at + 0x28, *call.arguments)
            if post_change is not None:
                # Flags are read after posting; the saved entry remains live.
                env.put(entry, 0xFFFFFFFF, post_change & MASK)
                env.put(cheat, 0x88776655)
                env.put(cheat + 0x120, 123)
                env.put(cheat + 0x124, 0x10293847)
                env.put(cheat + 0x128, 0x6A5B4C3D)
                env.write(cheat + 0x20, b'POST-CHANGED\0')
                env.put(game + 4, app2)
            return (salt << 24) | 0x123456

        env.override(LOOKUP, lookup)
        env.override(POST, post)
        return {"receiver": game if dispatch else cheat}

    return Case(label, KEYDOWN if dispatch else MATCH, setup,
                receiver=lambda t: t["receiver"],
                arguments=(key & MASK, (0x9ABCDEFF if dispatch else now) & MASK))


def cases(random_source):
    # Every name is checked as a complete encoded string, with independently
    # chosen command and flags. Prefixes cover lengths before lookup begins.
    for i, name in enumerate(CHEATS):
        for length in range(1, len(name) + 1):
            yield make_case(f"{name} prefix {length}", key=ord(name[length - 1]),
                            count=length - 1, text=name[:length - 1], expected=name,
                            command=0x8201 + i * 17, flags=i & 1,
                            dispatch=bool(length & 1), cheated=i * 0x1234567)
        for flag in (0, 1, 2, 0x100, 0x80000001):
            yield make_case(f"{name} flags {flag:#x}", key=ord(name[-1]),
                            count=len(name) - 1, text=name[:-1], expected=name,
                            command=0x8345 + i, flags=flag)

    for key in (0, 0x1B, 0x2F, 0x30, 0x31, 0x39, 0x3A, 0x40, 0x41,
                0x59, 0x5A, 0x5B, 0x61, 0x7F, 0x100, 0x80000000, 0xFFFFFFFF):
        for dispatch in (False, True):
            yield make_case(f"key {key:#x} dispatch {dispatch}", key=key,
                            count=7, dispatch=dispatch)

    for count in (-33, -32, -31, -2, -1, 0, 1, 3, 4, 5, 199, 200, 201,
                  202, 0x7FFFFFFF):
        yield make_case(f"signed count {count}", count=count, lookup_result=0)
    for last, now in ((100, 1599), (100, 1600), (100, 1601), (0, 1499),
                      (0, 1500), (0, 1501), (0xFFFFFF00, 0),
                      (0xFFFFFF00, 1243), (0xFFFFFF00, 1244),
                      (0xFFFFFF00, 1245), (0xFFFFFF00, 0xFFFFFFFE),
                      (0xFFFFFA23, 0xFFFFFFFF), (0xFFFFFA24, 0),
                      (0xFFFFFA24, 1), (0xFFFFFFFF, 1499),
                      (0xFFFFFFFF, 1500), (1000, 0), (0, 0)):
        for count in (4, 200, 201):
            yield make_case(f"time {last:#x} to {now:#x} count {count}",
                            last=last, now=now, count=count, lookup_result=0)

    for result in (0, 1, 2, 0x100, 0x80000000, 0xFFFFFFFF):
        for pointer in (False, True):
            for command in (-1, 0, 1, 0x7FFFFFFF, 0x80000000):
                yield make_case(f"lookup {result:#x} ptr {pointer} command {command}",
                                lookup_result=result, pointer=pointer, command=command,
                                map_change=True)
    for before in (0, 1, 2, 0x100, 0x80000001):
        for after in (0, 1, 2, 0x100, 0x80000001):
            for dispatch in (False, True):
                yield make_case(f"mutable flags {before:#x} to {after:#x} dispatch {dispatch}",
                                flags=before, post_change=after, map_change=True,
                                dispatch=dispatch)
    for paused in (0, 1, 2, 0xFFFFFFFF, 0x80000000):
        for key in (0x1B, 0x41, 0x30, 0x5B):
            yield make_case(f"paused {paused:#x} key {key:#x}", dispatch=True,
                            paused=paused, key=key, post_change=1)
    for i in range(24):
        name = random_source.choice(CHEATS)
        last = random_source.randrange(0xFFFF0000)
        yield make_case(f"random complete name {i}", text=name[:-1],
                        count=len(name) - 1, key=ord(name[-1]), expected=name,
                        last=last, now=last + random_source.randrange(1501), flags=random_source.getrandbits(32),
                        cheated=random_source.getrandbits(32),
                        command=random_source.randrange(1, 0x80000000),
                        salt=random_source.randrange(1, 255),
                        post_change=random_source.getrandbits(32))
