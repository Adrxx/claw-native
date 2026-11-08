"""Cases for level_one_closure_commands_01: Level 1 closure: level end, special command and application command helpers."""
import struct

from clawparity.cases import Case
from clawparity.env import Halt
from clawparity.fixtures import returns, sequence

M32 = 0xFFFFFFFF

# The cases that need imports without stand-ins (GetLocalTime, GetTickCount, lstrlenA, InterlockedIncrement,
# InterlockedDecrement) stay off until the specification declares those imports as scripted fixtures.
EXTENDED = True
# 0x49aa40 -> 0x4f5062 -> _getptd (0x4a7dc0) also calls GetLastError (0x546b0c) and SetLastError (0x546ab8): undeclared.
SYSTEM_TIME_READY = True

TIME_GET = 0x546DF0
GET_LOCAL_TIME = 0x546A34
LSTRLEN = 0x5469E4
INTERLOCKED_DEC = 0x5469E8
INTERLOCKED_INC = 0x5469EC
SEQUENCE_STATUS = 0x546E7C
RAND = 0x4A3050
POST_MESSAGE = 0x546D50
MCI_SEND = 0x546DEC
REG_SET_VALUE = 0x546824
G_LEVEL = 0x537E88      # global pointer read by 0x46bdb0
G_PANEL = 0x5371FC      # global pointer read by 0x415d90
G_HELPER = 0x537200     # global pointer read by 0x42a570
KEY_STRING = 0x522604   # map key used by 0x46bcf0
SCORE_CONSTANTS = 0x52D698
SCORE_SOURCE = 0x534D30


def cases(random_source):
    R = random_source

    def r32():
        return R.randrange(1, 1 << 32)

    def rb(n):
        return bytes(R.randrange(256) for _ in range(n))

    def mk(env, size, name):
        return env.object(size, name, data=rb(size))

    def cstring(env, text, refs=1, extra=3, name="cstring"):
        header = env.object(12 + len(text) + extra + 1, name, data=rb(12 + len(text) + extra + 1))
        env.put(header, refs, len(text), len(text) + extra)
        env.write(header + 12, text + b"\0")
        return header + 12

    def physical_imports(env, clock=None, sequence_status=0):
        """Stand-ins for the Windows services the unchanged CString and clock helpers call."""
        stamp = struct.pack("<8H", 2000 + R.randrange(30), 1 + R.randrange(12), R.randrange(7), 1 + R.randrange(28),
                            R.randrange(24), R.randrange(60), R.randrange(60), R.randrange(1000))

        def local_time(e, c):
            e.write(c.arguments[0], stamp)
            return 0

        def step(delta):
            def effect(e, c):
                value = (e.get(c.arguments[0]) + delta) & M32
                e.put(c.arguments[0], value)
                return value
            return effect
        env.override(GET_LOCAL_TIME, local_time)
        env.write(0x540B70, stamp)
        env.put(0x540B68, 0)
        env.override(0x5469B4, local_time)

        def zone(e, c):
            e.write(c.arguments[0], bytes(172))
            return 0
        env.override(0x546A3C, zone)
        thread = env.object(0x74, "CRT thread", fill=0)
        calendar = env.object(0x24, "calendar tm", fill=0)
        env.put(thread + 0x40, calendar)
        env.put(0x5410B8, 1)
        env.put(0x531430, 0, 0, 0)
        env.override(0x546A7C, returns(thread))
        env.override(LSTRLEN, lambda e, c: len(e.cstr(c.arguments[0])))
        env.override(INTERLOCKED_INC, step(1))
        env.override(INTERLOCKED_DEC, step(-1))
        env.override(TIME_GET, clock or (lambda e, c: 5000 + 1000 * e.calls_so_far(TIME_GET)))
        env.override(SEQUENCE_STATUS, returns(sequence_status))

    def recorder(log, results=(0,), deref=(), stride=16):
        """A scripted effect that records the receiver, the arguments and some dereferenced words of each call."""
        def effect(env, call):
            n = env.calls_so_far(call.function) - 1
            words = [call.receiver] + list(call.arguments) + [env.get(call.arguments[i]) for i in deref]
            env.put(log + 4 * stride * (n % 8), *words)
            return results[min(n, len(results) - 1)]
        return effect

    def stopper(log, stride=16):
        def effect(env, call):
            n = env.calls_so_far(call.function) - 1
            env.put(log + 4 * stride * (n % 8), call.receiver, *call.arguments)
            raise Halt()
        return effect

    def stub(env, log, name, convention, argc, results=(0,), stop=False):
        effect = stopper(log) if stop else recorder(log, results)
        return env.stub(name, convention, argc, effect)

    def vtable(env, size, name, slots):
        table = mk(env, size, name)
        for offset, address in slots.items():
            env.put(table + offset, address)
        return table

    def instance(env, size, name, table):
        obj = mk(env, size, name)
        env.put(obj, table)
        return obj

    # ------------------------------------------------------------------ 0x4b5c00
    for left, right in ((0, 0), (1, 2), (r32(), r32()), (M32, 0x80000000)):
        yield Case(f"4b5c00 stdcall pair {left:#x},{right:#x}", 0x4B5C00, None, arguments=(left, right))

    # ------------------------------------------------------------------ 0x4b5c10
    def mci_case(label, flag, results):
        device, flagword = r32(), flag if flag in (0, 1) else r32()

        def setup(env):
            obj = mk(env, 0x60, "mci player")
            env.put(obj + 0x40, flagword)
            env.put(obj + 0x18, device)
            log = env.object(512, "mci log", fill=0)
            env.override(MCI_SEND, recorder(log, results))
            return {"obj": obj, "log": log}
        return Case(label, 0x4B5C10, setup, receiver=lambda t: t["obj"])

    yield mci_case("4b5c10 no device flag", 0, (0x77,))
    yield mci_case("4b5c10 device and mci success", 1, (0,))
    yield mci_case("4b5c10 device flag is any nonzero word", 7, (0,))
    for code in (1, 0x10D, 0x80000000, M32, r32()):
        yield mci_case(f"4b5c10 mci error {code:#x}", 1, (code,))

    # ------------------------------------------------------------------ 0x4b5e50
    def reg_case(label, handle_flag, name_arg, value, result):
        handle = r32()

        def setup(env):
            obj = mk(env, 0x30, "registry key")
            env.put(obj, handle_flag)
            env.put(obj + 0x18, handle)
            log = env.object(512, "registry log", fill=0)
            env.override(REG_SET_VALUE, recorder(log, (result,), deref=(4,)))
            return {"obj": obj, "log": log}
        return Case(label, 0x4B5E50, setup, receiver=lambda t: t["obj"], arguments=(name_arg, value))

    yield reg_case("4b5e50 key not open", 0, 0x1234, r32(), 9)
    yield reg_case("4b5e50 key not open, null name", 0, 0, r32(), 9)
    yield reg_case("4b5e50 null name", r32(), 0, r32(), 9)
    for result in (0, 1, 2, 0x80000000, M32):
        yield reg_case(f"4b5e50 registry result {result:#x}", r32(), 0x520000 + R.randrange(0x1000), r32(), result)

    # ------------------------------------------------------------------ 0x42d520
    def destroy_case(label, has_block, flag):
        def setup(env):
            obj = mk(env, 0x30, "owner")
            block = 0
            if has_block:
                block = mk(env, 0x18, "owned block")
            env.put(obj, r32())
            env.put(obj + 4, block)
            return {"obj": obj, "block": block}
        return Case(label, 0x42D520, setup, receiver=lambda t: t["obj"], arguments=(flag,))

    for has_block in (False, True):
        for flag in (0, 1, 2, 3, 0x80000001, 0xFFFFFFFE, 0xFFFFFFFF):
            yield destroy_case(f"42d520 block={has_block} flag={flag:#x}", has_block, flag)

    # ------------------------------------------------------------------ 0x42abb0
    def request_close_case(label, done, has_a, has_b):
        hwnd = r32()

        def setup(env):
            q = mk(env, 0xB0, "application")
            env.put(q + 0xA0, done)
            a = mk(env, 0x250, "session") if has_a else 0
            b = mk(env, 0x10, "window record") if has_b else 0
            if b:
                env.put(b + 4, hwnd)
            env.put(q + 8, a)
            env.put(q + 4, b)
            log = env.object(512, "post log", fill=0)
            env.override(POST_MESSAGE, recorder(log, (r32(),)))
            return {"q": q, "a": a, "log": log}
        return Case(label, 0x42ABB0, setup, receiver=lambda t: t["q"])

    for done in (0, 1, 0x40000000, M32):
        for has_a in (False, True):
            for has_b in (False, True):
                yield request_close_case(f"42abb0 done={done:#x} session={has_a} window={has_b}", done, has_a, has_b)

    # ------------------------------------------------------------------ 0x42b910
    def forward_case(label, flag, path):
        def setup(env):
            obj = mk(env, 0x110, "dialog")
            env.put(obj + 0x9C, flag)
            p = 0
            if path == "empty":
                p = env.object(8, "empty path", fill=0)
            elif path == "wild":
                p = 0x00DEAD00 + R.randrange(0x1000) * 0x10000
            env.put(obj + 0x100, p)
            return {"obj": obj}
        return Case(label, 0x42B910, setup, receiver=lambda t: t["obj"])

    yield forward_case("42b910 no flag", 0, "null")
    yield forward_case("42b910 no flag, empty path", 0, "empty")
    yield forward_case("42b910 no flag, unbacked path pointer", 0, "wild")
    yield forward_case("42b910 no flag, another unbacked path pointer", 0, "wild")
    yield forward_case("42b910 flag, null path", 1, "null")
    yield forward_case("42b910 flag, empty path", 0x70000000, "empty")

    # ------------------------------------------------------------------ shared world
    class World:
        pass

    def build(env, **o):
        """Object graph for 0x46bc90, 0x46bcf0 and 0x46bdb0."""
        w = World()
        physical_imports(env, clock=o.get("clock"), sequence_status=o.get("seq", 0))
        w.log = env.object(0x800, "stub log", fill=0)
        w.t0 = mk(env, 0x260, "level command")
        w.q = mk(env, 0xE0, "application")
        env.put(w.t0 + 4, w.q)
        w.num = o.get("num", r32())
        env.put(w.t0 + 0x164, w.num)
        env.put(w.t0 + 0x168, o.get("flags", 0))
        env.put(w.t0 + 0x258, o.get("w258", 0))
        env.put(w.q + 0x9C, o.get("q9c", 0))
        env.put(w.q + 0xA0, o.get("qa0", 0))
        # string at [q + 0xc0]: empty so that 0x4f650f returns at once
        env.put(w.q + 0xC0, cstring(env, b"", refs=1, extra=5, name="empty text"))
        # 0x42abb0 state
        w.a8 = mk(env, 0x250, "session")
        w.b4 = mk(env, 0x10, "window record")
        env.put(w.q + 8, w.a8)
        env.put(w.q + 4, w.b4)
        env.put(w.b4 + 4, r32())
        env.override(POST_MESSAGE, recorder(w.log + 0x600, (r32(),)))
        # 0x46bdb0 state
        w.scores = mk(env, 0x2230, "score table") if o.get("scores", True) else 0
        env.put(w.q + 0x64, w.scores)
        w.rec = mk(env, 0x30, "score record")
        text = o.get("rec_text", b"")
        env.put(w.rec + 0x1C, cstring(env, text, refs=1, extra=2, name="record text"))
        env.put(w.rec + 0xC, o.get("rec_count", 0))
        env.put(w.q + 0x60, w.rec)
        w.s = mk(env, 0x140, "level record")
        w.A = mk(env, 0x20, "level host")
        env.put(w.A + 0x14, w.s if o.get("s", True) else 0)
        w.g = mk(env, 0x120, "level object")
        env.put(w.g + 0x6C, w.A if o.get("a", True) else 0)
        env.put(w.g + 0xF8, r32())
        env.put(w.g + 0x10C, r32())
        env.put(G_LEVEL, w.g if o.get("g", True) else 0)
        # panel for 0x415d90 / 0x42a630
        w.panel = mk(env, 0x40, "panel")
        w.m = mk(env, 0x40, "panel state")
        env.put(w.m + 0x14, 0)
        state = stub(env, w.log + 0x400, "state", "thiscall", 0, o.get("state", (0,)))
        env.put(w.m, vtable(env, 0x40, "panel vtable", {0x10: state}))
        env.put(w.panel + 0x2C, w.m if o.get("m", True) else 0)
        env.put(G_PANEL, w.panel)
        if o.get("source_words") is not None:
            env.write(SCORE_SOURCE, struct.pack("<10I", *o["source_words"]))
        constants = struct.unpack("<10I", env.read(SCORE_CONSTANTS, 40))
        words = struct.unpack("<10I", env.read(SCORE_SOURCE, 40))
        w.checksum = sum(a * b for a, b in zip(words, constants)) & M32
        slot = w.scores + 0x21C4 if w.scores else 0
        w.slot = slot
        if slot:
            env.put(slot + 4, o.get("stored4", w.checksum + 1 if w.checksum < M32 else w.checksum))
            env.put(slot + 8, o.get("stored8", r32()))
        env.override(RAND, recorder(w.log + 0x700, (r32(), r32(), r32())))
        # 0x46bcf0 state
        w.x = mk(env, 0x30, "closure frame")
        env.put(w.t0 + 0xC, w.x)
        w.w = mk(env, 0x30, "closure window")
        w.y = mk(env, 0x40, "closure host")
        w.u = mk(env, 0x10, "closure sink")
        w.v = mk(env, 0x70, "closure list")
        w.z = mk(env, 0x40, "closure surface owner")
        w.t = mk(env, 0x40, "closure surface")
        w.d = mk(env, 0x10, "closure device")
        w.wp = mk(env, 0x40, "closure callback")
        env.put(w.x + 4, w.w)
        env.put(w.x + 8, w.y)
        env.put(w.x + 0xC, w.u)
        env.put(w.x + 0x24, w.v)
        env.put(w.w + 0x10, w.z)
        env.put(w.w + 0x14, w.wp)
        env.put(w.w + 0x18, r32())
        env.put(w.z + 0x2C, w.t)
        env.put(w.t + 8, w.d)
        w.log2 = env.object(0x400, "extra stub log", fill=0)
        env.put(w.t, vtable(env, 0x40, "surface vtable", {0x1C: stub(env, w.log2, "restore", "thiscall", 0, o.get("restore", (0,)))}))
        # V: 0x4cb9b0 takes the second path
        env.put(w.v + 8, 0)
        env.put(w.v + 0x60, M32)
        env.put(w.v + 0x3C, 0)
        # Y -> host -> map used by 0x4c8da0
        yc = mk(env, 0x30, "map owner")
        mp = mk(env, 0x40, "map holder")
        env.put(w.y + 0xC, yc)
        env.put(yc + 0x14, mp)
        w.map = mp + 0x10
        size = o.get("hash_size", 17)
        env.put(w.map + 8, size)
        table = 0
        if o.get("table", True):
            table = mk(env, size * 4, "hash table")
            env.write(table, bytes(4 * size))
            key = env.cstr(KEY_STRING)
            h = 0
            for c in key:
                c = c - 256 if c > 127 else c
                h = (h * 0x21 + c) & M32
            bucket = h % size
            chain = 0
            if o.get("match", False):
                node = mk(env, 0x10, "match node")
                keycopy = env.object(len(key) + 1, "key copy", data=key + b"\0")
                value = o.get("value")
                if value is None:
                    value = mk(env, 0x100, "map value")
                    created = vtable(env, 0x40, "created vtable", {
                        0x2C: stub(env, w.log2 + 0x100, "created call", "thiscall", 1, (0,))})
                    hook_result = r32()

                    def hook(e, c, created=created, hook_result=hook_result, log=w.log + 0x580):
                        e.put(log, c.arguments[0], e.get(c.arguments[0]))
                        e.put(c.arguments[0], created)
                        return hook_result
                    env.put(value + 0x10, env.stub("create hook", "cdecl", 1, hook))
                env.put(node, 0, h, keycopy, value)
                chain = node
            if o.get("other", False):
                node = mk(env, 0x10, "other node")
                other = env.object(8, "other key", data=b"nokey\0\0\0")
                env.put(node, chain, h, other, r32())
                chain = node
            env.put(table + 4 * bucket, chain)
        env.put(w.map + 4, table)
        # callbacks
        u_vt = vtable(env, 0x40, "sink vtable", {0x34: stub(env, w.log + 0x100, "sink call", "thiscall", 2, (0,), stop=o.get("stop") == "sink")})
        env.put(w.u, u_vt)
        d_vt = vtable(env, 0x40, "device vtable", {0x2C: stub(env, w.log + 0x200, "device call", "stdcall", 3, o.get("dev", (0,)), stop=o.get("stop") == "device")})
        env.put(w.d, d_vt)
        wp_vt = vtable(env, 0x40, "callback vtable", {0x28: stub(env, w.log + 0x300, "closure callback", "thiscall", 1, (0,))})
        env.put(w.wp, wp_vt)
        surf = o.get("surf")
        if surf:
            height, width, pitch = surf
            w.s_surf = mk(env, 0x40, "pixel surface")
            d2 = mk(env, 0x10, "pixel device")
            lock = stub(env, w.log2 + 0x200, "pixel lock", "stdcall", 5, o.get("lock", (0,)))
            unlock = stub(env, w.log2 + 0x300, "pixel unlock", "stdcall", 2, (0,))
            env.put(d2, vtable(env, 0x90, "pixel device vtable", {0x64: lock, 0x80: unlock}))
            restore2 = stub(env, w.log2 + 0x380, "pixel restore", "thiscall", 0, o.get("restore2", (1,)))
            env.put(w.s_surf, vtable(env, 0x40, "pixel surface vtable", {0x1C: restore2}))
            w.pixels = mk(env, pitch * height + 16, "pixels")
            env.put(w.s_surf + 8, d2)
            env.put(w.s_surf + 0x14, height, width, pitch)
            env.put(w.s_surf + 0x30, w.pixels)
            env.put(w.wp + 0x2C, w.s_surf)
        y_vt = vtable(env, 0x40, "host vtable", {0x28: stub(env, w.log + 0x500, "host call", "thiscall", 1, (0,))})
        env.put(w.y, y_vt)
        env.put(w.q + 0x78, o.get("q78", 0))
        if o.get("match"):
            env.write(w.y + 0x10, bytes(0x20))
            env.put(w.y + 0x28, 10)
        return w

    def world_case(label, function, expect="return", **o):
        def setup(env):
            w = build(env, **o)
            return {"t0": w.t0, "w": w}
        return Case(label, function, setup, receiver=lambda t: t["t0"], expect=expect)

    # ------------------------------------------------------------------ 0x46bdb0
    # 0x49a9d0 reaches GetLocalTime, which has no stand-in, so only the paths that skip it can pass:
    # no level object, no score table, or the locked flag word.
    yield world_case("46bdb0 no level object", 0x46BDB0, g=False)
    yield world_case("46bdb0 no score table, level object without host", 0x46BDB0, a=False, scores=False)
    yield world_case("46bdb0 no score table, host without record", 0x46BDB0, s=False, scores=False)
    yield world_case("46bdb0 no score table, panel empty", 0x46BDB0, m=False, scores=False)
    for st in ((3,), (4,), (6,), (0, 4), (0, 0, 6), (5, 7, 9)):
        yield world_case(f"46bdb0 no score table, panel state {st}", 0x46BDB0, state=st, scores=False)
    yield world_case("46bdb0 no score table", 0x46BDB0, scores=False)
    yield world_case("46bdb0 locked flag word", 0x46BDB0, w258=r32())
    yield world_case("46bdb0 locked flag word 1", 0x46BDB0, w258=1)
    yield world_case("46bdb0 locked flag word, no host", 0x46BDB0, w258=0x80000000, a=False)
    if SYSTEM_TIME_READY:
        yield world_case("46bdb0 level object without host", 0x46BDB0, a=False)
        yield world_case("46bdb0 host without record", 0x46BDB0, s=False)
        yield world_case("46bdb0 full level object, panel empty", 0x46BDB0, m=False, stored4=0, flags=1)
        for st in ((3,), (4,), (6,), (0, 4), (0, 0, 6), (5, 7, 9)):
            yield world_case(f"46bdb0 panel state {st}", 0x46BDB0, state=st, flags=1)
        yield world_case("46bdb0 cheat flag set", 0x46BDB0, flags=1)
        yield world_case("46bdb0 cheat flag other bits", 0x46BDB0, flags=0xFE, stored4=0)
        yield world_case("46bdb0 cheat flag and others", 0x46BDB0, flags=r32() | 1)

    def score_case(label, kind, **extra):
        def setup(env):
            probe = World()
            # compute the checksum for the data this case installs
            words = extra.get("source_words")
            if words is None:
                words = struct.unpack("<10I", env.read(SCORE_SOURCE, 40))
            constants = struct.unpack("<10I", env.read(SCORE_CONSTANTS, 40))
            cs = sum(a * b for a, b in zip(words, constants)) & M32
            num = extra.get("num", r32())
            if kind == "stored-above":
                opts = dict(stored4=(cs + 1) & M32 if cs < M32 else cs, stored8=num - 1 if num else 1)
                if cs == M32:
                    opts["stored4"] = cs
                    opts["stored8"] = (num - 1) & M32 if num else 1
            elif kind == "stored-below":
                opts = dict(stored4=(cs - 1) & M32 if cs else cs, stored8=(num + 5) & M32)
            elif kind == "equal-older":
                opts = dict(stored4=cs, stored8=(num - 1) & M32 if num else 1)
            elif kind == "equal-same":
                opts = dict(stored4=cs, stored8=num)
            elif kind == "equal-newer":
                opts = dict(stored4=cs, stored8=(num + 1 + R.randrange(100)) & M32)
            elif kind == "equal-newer-wrap":
                opts = dict(stored4=cs, stored8=0xFFFFFFF0)
            elif kind == "equal-older-wrap":
                opts = dict(stored4=cs, stored8=0x7FFFFFF0)
            opts.update(extra)
            opts["num"] = num
            w = build(env, **opts)
            return {"t0": w.t0, "w": w}
        return Case(label, 0x46BDB0, setup, receiver=lambda t: t["t0"])

    if SYSTEM_TIME_READY:
        for kind in ("stored-above", "stored-below", "equal-older", "equal-same", "equal-newer", "equal-newer-wrap",
                     "equal-older-wrap"):
            yield score_case(f"46bdb0 score {kind}", kind)
            yield score_case(f"46bdb0 score {kind} random data", kind, source_words=tuple(r32() for _ in range(10)))
        yield score_case("46bdb0 score equal-older, high num", "equal-older", num=0x90000000 | R.randrange(1000))
        yield score_case("46bdb0 score equal-newer, high num", "equal-older-wrap", num=0xFFFFFFF8)
        # a positive count with text reaches file I/O (GetFullPathNameA, undeclared), so it is left out
        yield score_case("46bdb0 score win with text count=0", "stored-below", rec_text=b"Level", rec_count=0)
        yield score_case("46bdb0 score win with text count<0", "stored-below", rec_text=b"Level", rec_count=M32)


    # ------------------------------------------------------------------ 0x46bc90
    yield world_case("46bc90 closing: no level object", 0x46BC90, g=False)
    yield world_case("46bc90 closing: halts in the sink", 0x46BC90, expect="halt", stop="sink", scores=False)
    yield world_case("46bc90 closing: halts in the device", 0x46BC90, expect="halt", stop="device", w258=r32())
    yield world_case("46bc90 closing, cheat flag: halts in the device", 0x46BC90, expect="halt", stop="device", flags=1,
                     scores=False)
    for qa0 in (0, 1, r32()):
        for q9c in (1, r32(), 0x80000000):
            yield world_case(f"46bc90 already closing {q9c:#x} done={qa0:#x}", 0x46BC90, q9c=q9c, qa0=qa0)

    # ------------------------------------------------------------------ 0x46bcf0
    yield world_case("46bcf0 halts in the sink", 0x46BCF0, expect="halt", stop="sink")
    yield world_case("46bcf0 cheat flag, halts in the sink", 0x46BCF0, expect="halt", stop="sink", flags=1)
    yield world_case("46bcf0 flag 0x100, halts in the sink", 0x46BCF0, expect="halt", stop="sink", flags=0xFFFFFFFE)
    yield world_case("46bcf0 halts in the device", 0x46BCF0, expect="halt", stop="device")
    yield world_case("46bcf0 cheat flag, halts in the device", 0x46BCF0, expect="halt", stop="device", flags=1)
    yield world_case("46bcf0 empty table, halts in the device", 0x46BCF0, expect="halt", stop="device", table=False)
    yield world_case("46bcf0 other node, halts in the device", 0x46BCF0, expect="halt", stop="device", other=True)
    yield world_case("46bcf0 other node, size 1", 0x46BCF0, expect="halt", stop="device", other=True, hash_size=1)
    yield world_case("46bcf0 found key", 0x46BCF0, expect="halt", stop="device", match=True)
    yield world_case("46bcf0 found key after another node", 0x46BCF0, expect="halt", stop="device", match=True,
                     other=True, hash_size=1)
    yield world_case("46bcf0 found key, cheat flag", 0x46BCF0, expect="halt", stop="device", match=True, flags=1)
    yield world_case("46bc90 closing: found key, halts in the device", 0x46BC90, expect="halt", stop="device",
                     match=True, scores=False)

    def ticks(*values, step=50):
        """timeGetTime: the listed values for the first calls, then a steady clock."""
        def clock(e, c):
            n = e.calls_so_far(TIME_GET)
            return values[n - 1] if n <= len(values) else (values[-1] + step * (n - len(values))) & M32
        return clock

    if EXTENDED:
        for flags in (0, 1):
            yield world_case(f"46bcf0 completes, waits, flags={flags}", 0x46BCF0, flags=flags, clock=ticks(100))
        yield world_case("46bcf0 completes, default clock", 0x46BCF0)
        yield world_case("46bcf0 no wait: just past the delay", 0x46BCF0, clock=ticks(1000, 1000 + 0xFA0 + 7))
        yield world_case("46bcf0 no wait: exactly the delay", 0x46BCF0, clock=ticks(2000, 2000 + 0xFA0))
        yield world_case("46bcf0 wait one tick", 0x46BCF0, clock=ticks(3000, 3000 + 0xFA0 - 1, 3000 + 0xFA0 - 1))
        yield world_case("46bcf0 clock wraps", 0x46BCF0, clock=ticks(0xFFFFFF00, 0xFFFFFF01))
        yield world_case("46bcf0 completes after a found key", 0x46BCF0, match=True, clock=ticks(100))
        yield world_case("46bcf0 surface lost and restored", 0x46BCF0, dev=(0x887601C2, 0), restore=(1,), clock=ticks(100))
        yield world_case("46bcf0 surface lost, restore fails", 0x46BCF0, dev=(0x887601C2,), restore=(0,), clock=ticks(100))
        yield world_case("46bcf0 empty table completes", 0x46BCF0, table=False, clock=ticks(1000, 9000))
        yield world_case("46bc90 closing completes", 0x46BC90, scores=False, clock=ticks(100))
        yield world_case("46bc90 closing completes, locked word", 0x46BC90, w258=r32(), flags=1, clock=ticks(1000, 9000))
        yield world_case("46bc90 closing completes after found key", 0x46BC90, scores=False, match=True, clock=ticks(100))

    # ------------------------------------------------------------------ 0x42a570
    def command_world(env, **o):
        w = World()
        physical_imports(env, clock=o.get("clock"), sequence_status=o.get("seq", 0))
        w.log = env.object(0x800, "command log", fill=0)
        w.o = mk(env, 0x100, "command")
        w.e = mk(env, 0x250, "command host")
        env.put(w.o + 8, w.e)
        env.put(w.e + 0x244, r32())
        env.put(w.o + 0x10, o.get("o10", 0))
        env.put(w.o + 0x14, o.get("o14", 0))
        # [o+0x2c]: object with state (+0x10) and update (+0x4c) methods
        state = stub(env, w.log, "mode", "thiscall", 0, o.get("state", (0,)))
        update = stub(env, w.log + 0x100, "update", "thiscall", 0, (r32(),))
        c_vt = vtable(env, 0x60, "mode vtable", {0x10: state, 0x4C: update})
        w.c = instance(env, 0x40, "mode object", c_vt)
        env.put(w.o + 0x2C, w.c)
        # [o+0x30] chain for 0x4b4b40
        level = o.get("chain", 3)
        f = 0
        if level >= 0:
            f = mk(env, 0x40, "chain 0")
            f1 = 0
            if level >= 1:
                f1 = mk(env, 0x40, "chain 1")
                f2 = 0
                if level >= 2:
                    f2 = mk(env, 0x90, "chain 2")
                    env.put(f2 + 0x78, o.get("f78", 0))
                    first = 0
                    for i in range(o.get("f_nodes", 0)):
                        probe = stub(env, w.log + 0x700 + 0x40 * i, f"chain entry {i}", "stdcall", 1, (0,))
                        k = instance(env, 0x20, f"chain owner {i}", vtable(env, 0x60, f"chain vtable {i}", {0x48: probe}))
                        part = mk(env, 0x80, f"chain part {i}")
                        env.put(part + 0x78, r32())
                        node = mk(env, 0x40, f"chain node {i}")
                        env.put(node + 4, first + 4 if first else 0)
                        env.put(node + 0xC, k)
                        env.put(node + 0x10, part)
                        env.put(node + 0x30, 0)
                        first = node
                    env.put(f2 + 4, first + 4 if first else 0)
                env.put(f1 + 0x2C, f2)
            env.put(f + 0x28, f1)
        env.put(w.o + 0x30, f if level >= 0 else 0)
        # [o+0x50]
        w.h = mk(env, 0x40, "toolbar")
        env.put(w.o + 0x50, w.h)
        h1_mode = o.get("h1", "none")
        h1 = 0
        if h1_mode != "none":
            h_vt = vtable(env, 0x60, "toolbar vtable", {
                0x20: stub(env, w.log + 0x200, "toolbar probe", "thiscall", 0, o.get("probe", (0,))),
                0x28: stub(env, w.log + 0x280, "toolbar a", "thiscall", 0, (r32(),)),
                0x2C: stub(env, w.log + 0x300, "toolbar b", "thiscall", 1, (r32(),), stop=h1_mode == "stop")})
            h1 = instance(env, 0x60, "toolbar part", h_vt)
        env.put(w.h + 0x1C, h1)
        # [o+0x5c]
        w.l = 0
        if o.get("l", True):
            w.l = mk(env, 0x40, "entry list")
            l0 = mk(env, 0x40, "entry list head")
            env.put(l0 + 0x2C, 0)
            env.put(w.l, l0)
            node_count = o.get("nodes", 0)
            head = 0
            for i in range(node_count):
                entry_vt = vtable(env, 0x20, "entry vtable", {
                    4: stub(env, w.log + 0x400 + 0x80 * i, f"entry {i}", "thiscall", 3, (0,), stop=o.get("stop_entry") == i)})
                entry = instance(env, 0x40, f"entry {i}", entry_vt)
                env.put(entry + 4, 0)
                node = mk(env, 0x10, f"node {i}")
                env.put(node, head)
                env.put(node + 8, entry)
                head = node
            env.put(w.l + 0xC, head)
            env.put(w.l + 0x28, r32())
            env.put(w.l + 0x2C, r32())
        env.put(w.o + 0x5C, w.l)
        # globals for 0x4b3ab0
        helper = mk(env, 0x230, "helper")
        env.write(helper + 0x1CC, bytes([R.randrange(256) & 0xFA]))
        env.put(G_HELPER, helper)
        if h1:
            env.put(h1 + 0x58, r32())
        level = o.get("level", "none")
        g = 0
        if level != "none":
            g = mk(env, 0x120, "level object")
            host = mk(env, 0x20, "level host")
            rec = mk(env, 0x140, "level record")
            env.put(g + 0x6C, host)
            env.put(host + 0x14, rec if level == "full" else 0)
            w.rec = rec
        env.put(G_LEVEL, g)
        return w

    def command_case(label, argument, expect="return", **o):
        def setup(env):
            w = command_world(env, **o)
            return {"o": w.o, "w": w}
        return Case(label, 0x42A570, setup, receiver=lambda t: t["o"], arguments=(argument,), expect=expect)

    for arg in (1, 0x80000000, M32):
        yield command_case(f"42a570 arg={arg:#x} full", arg)
    yield command_case("42a570 arg, no list", 1, l=False)
    yield command_case("42a570 arg, list of one", 5, nodes=1)
    yield command_case("42a570 arg, list of three", 5, nodes=3)
    for level in (-1, 0, 1, 2):
        yield command_case(f"42a570 arg, chain level {level}", 2, chain=level)
    yield command_case("42a570 arg, chain with count", 2, chain=2, f78=r32())
    yield command_case("42a570 arg, toolbar part", 3, h1="go")
    yield command_case("42a570 arg, toolbar part, list", 3, h1="go", nodes=2, chain=1)

    # argument zero: every path ends in a call that reaches GetTickCount, so the cases stop at a stand-in.
    yield command_case("42a570 zero, stop in list entry", 0, expect="halt", o10=1, nodes=1, stop_entry=0)
    yield command_case("42a570 zero, stop in second list entry", 0, expect="halt", o10=r32(), nodes=3, stop_entry=1)
    yield command_case("42a570 zero, update flag, mode 3", 0, expect="halt", o10=1, o14=1, nodes=1, stop_entry=0,
                       state=(3,), h1="go")
    yield command_case("42a570 zero, mode 4 stop in toolbar", 0, expect="halt", o14=r32(), state=(0, 4), h1="stop")
    yield command_case("42a570 zero, mode 6 stop in toolbar", 0, expect="halt", o14=r32(), state=(0, 0, 6), h1="stop")
    yield command_case("42a570 zero, mode 5 no toolbar part, stop in entry", 0, expect="halt", o14=1, o10=1,
                       state=(5, 5, 5), nodes=1, stop_entry=0)
    yield command_case("42a570 zero, mode 3, no toolbar part, stop in entry", 0, expect="halt", o14=1, o10=1,
                       state=(3,), nodes=1, stop_entry=0)


    if EXTENDED:
        for level in ("none", "nohost", "full"):
            yield command_case(f"42a570 zero completes, level {level}", 0, o10=1, nodes=1, level=level)
        yield command_case("42a570 zero completes, plain", 0)
        yield command_case("42a570 zero completes, entries", 0, o10=r32(), nodes=3, level="full")
        yield command_case("42a570 zero completes, mode 3", 0, o14=1, state=(3,), h1="go", level="full")
        yield command_case("42a570 zero completes, mode 4, o10", 0, o14=1, o10=1, state=(0, 4), h1="go", nodes=2)
        yield command_case("42a570 zero completes, mode 6", 0, o14=1, state=(0, 0, 6), h1="go")
        yield command_case("42a570 zero completes, mode 5", 0, o14=r32(), state=(5, 5, 5), h1="go", nodes=1)
        yield command_case("42a570 zero completes, mode 3 without toolbar part", 0, o14=1, state=(3,))
        yield command_case("42a570 zero completes, no list", 0, l=False)
        yield command_case("42a570 zero completes, no chain", 0, chain=-1, level="full")
        yield command_case("42a570 zero completes, clock", 0, clock=ticks(0xFFFFFF00))
        for status in (4, 0x10, 0, 3, 5, 0x11):
            yield command_case(f"42a570 arg, toolbar active, status {status:#x}", 7, h1="go", probe=(1,), seq=status)
        yield command_case("42a570 arg, toolbar active, status 4, list", 0x80000000, h1="go", probe=(r32(),), seq=4, nodes=2)

    # ------------------------------------------------------------------ 0x4373d0
    def name_case(label, text, refs=1, header=None):
        def setup(env):
            physical_imports(env)
            out = env.object(16, "result slot", fill=0)
            data = cstring(env, text, refs=refs, extra=R.randrange(4), name="argument string")
            if header is not None:
                env.put(data - 8, header)
            return {"out": out, "data": data}
        return Case(label, 0x4373D0, setup, arguments=(lambda t: t["out"], lambda t: t["data"]))

    if EXTENDED:
        for text in (b"", b"a", b"abcd", b"a.wa", b"a.wav", b"ab.wav", b"x\\.wav", b"\\.wav", b"dir\\.wav",
                     b"file.wav", b"C:\\GAME\\CLAW\\LEVEL1.PCX", b"\\\\a\\b\\c\\d\\e\\f.tga", b"no extension at all",
                     bytes(R.randrange(97, 123) for _ in range(5 + R.randrange(40)))):
            yield name_case(f"4373d0 name {text!r}", text)
        for text, header in ((b"abc", 0), (b"abc", 4), (b"abc", 5), (b"ab.wav", 4), (b"ab.wav", 0), (b"C:\\x\\y.wav", 3),
                             (b"C:\\x\\y.wav", 5), (b"ab", 9), (b"abcd", 5), (b"abcde", 5)):
            yield name_case(f"4373d0 header {header} data {text!r}", text, header=header)
        for refs in (2, 5, 0, M32):
            yield name_case(f"4373d0 refs {refs:#x} short", b"ab", refs=refs)
            yield name_case(f"4373d0 refs {refs:#x} path", b"C:\\a\\b.wav", refs=refs)

    # ------------------------------------------------------------------ 0x49c860
    def clock_text_case(label, seconds):
        def setup(env):
            physical_imports(env)
            return {"out": env.object(16, "result slot", fill=0)}
        return Case(label, 0x49C860, setup, arguments=(lambda t: t["out"], seconds))

    if EXTENDED:
        for seconds in (0, 1, 9, 10, 59, 60, 61, 599, 3599, 3600, 3601, 3661, 36000, 86399, 86400, 359999, 360000,
                        0x7FFFFFFF, 0x80000000, M32, R.randrange(100000), R.randrange(1 << 20), r32()):
            yield clock_text_case(f"49c860 seconds {seconds}", seconds)

    # ------------------------------------------------------------------ targeted cases
    if EXTENDED:
        for count in (1, 2, 3):
            yield command_case(f"42a570 arg, chain entries {count}", 9, chain=2, f78=1 + R.randrange(100), f_nodes=count)
        yield command_case("42a570 arg, chain entries with list and toolbar", 0x40, chain=2, f78=r32(), f_nodes=2, nodes=2,
                           h1="go")

        def surface_case(label, mode, geometry, **extra):
            return world_case(label, 0x46BCF0, q78=mode, match=True, surf=geometry, clock=ticks(100), **extra)

        for mode in (8, 0x10):
            for geometry in ((1, 4, 24), (2, 8, 40), (3, 6, 40), (4, 16, 40), (5, 12, 36), (6, 10, 32), (3, 1, 40), (2, 0, 24)):
                yield surface_case(f"46bcf0 pixel mode {mode:#x} geometry {geometry}", mode, geometry)
            yield surface_case(f"46bcf0 pixel mode {mode:#x} lost then restored", mode, (3, 8, 40), lock=(0x887601C2, 0),
                               restore2=(1,))
            yield surface_case(f"46bcf0 pixel mode {mode:#x} lost, restore fails", mode, (3, 8, 40), lock=(0x887601C2,),
                               restore2=(0,))
            yield surface_case(f"46bcf0 pixel mode {mode:#x} cheat flag", mode, (3, 8, 40), flags=1)
        for mode in (0, 1, 7, 0x11, M32):
            yield surface_case(f"46bcf0 pixel mode {mode:#x} is ignored", mode, (3, 8, 40))
        yield world_case("46bcf0 no key, pixel mode 8 untouched", 0x46BCF0, q78=8, surf=(3, 8, 40), clock=ticks(100))
        yield world_case("46bc90 closing: pixel mode 0x10", 0x46BC90, scores=False, q78=0x10, match=True, surf=(3, 8, 40),
                         clock=ticks(100))
