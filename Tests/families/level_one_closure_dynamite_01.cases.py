"""Cases for level_one_closure_dynamite_01: Level 1 player projectile and dynamite helpers.

Every branch has explicit cases; random_source only adds extra variety (object contents, extra coordinates).
"""
import random
import struct

from clawparity.cases import Case

MASK = 0xFFFFFFFF

F_408510, F_408580, F_408860, F_408870 = 0x408510, 0x408580, 0x408860, 0x408870
F_43AD20, F_43B120, F_43B160, F_43B1A0, F_43B1E0, F_43B210 = 0x43AD20, 0x43B120, 0x43B160, 0x43B1A0, 0x43B1E0, 0x43B210

TRIE = 0x537668
FALL_STAMP = 0x537210
IDLE_STATUS = 0x40AF40
DEBUG_FLAG, DEBUG_VALUE = 0x532C0C, 0x532C10
ERROR_MODE = 0x544D18


# ---- helpers --------------------------------------------------------------------------------

def junk(r, n):
    return [r.randrange(1, 1 << 32) for _ in range(n)]


def logger(log, tag, result=0):
    """A stand-in that records (tag, receiver, argument 0, argument 1) into the log object, in call order."""
    def effect(env, call):
        count = env.get(log)
        if count < 30:
            args = list(call.arguments) + [0, 0]
            env.put(log + 8 + count * 16, tag, call.receiver, args[0], args[1])
        env.put(log, count + 1)
        return result(env, call) if callable(result) else result
    return effect


def new_log(env):
    return env.object(8 + 30 * 16, "log", fill=0)


def new_object(env, r, size, name, **fields):
    """A heap object of random non-zero words, with the named byte offsets overwritten (keys like o_1c)."""
    obj = env.object(size, name, words=junk(r, size // 4))
    for key, value in fields.items():
        env.put(obj + int(key[2:], 16), value)
    return obj


def animation(env, r, name):
    """The object 0x4c8220 reads: [+0x10] > 0, [+0xc] -> array whose first element has a word at +0x1c."""
    frame = new_object(env, r, 0x40, name + "-frame")
    frames = env.object(16, name + "-frames", words=[frame] + junk(r, 3))
    return new_object(env, r, 0x30, name, o_0c=frames, o_10=r.randrange(1, 40))


def set_trie(env, r, key, node_key, value):
    """The string table at 0x537668 with one node. node_key is what the node holds; key says nothing here."""
    node = env.object(0x20, "trie-node")
    text = env.object(len(node_key) + 1, "trie-key", data=node_key.encode() + b"\0")
    env.put(node, node, node, 0, text, value)
    env.put(TRIE + 4, new_object(env, r, 0x20, "trie-error", o_0c=4))
    env.put(TRIE + 0x18, node)
    env.put(TRIE + 0x1C, *junk(r, 4))
    return node


def clear_trie(env, r):
    env.put(TRIE + 4, new_object(env, r, 0x20, "trie-error", o_0c=4))
    env.put(TRIE + 0x18, 0)
    env.put(TRIE + 0x1C, *junk(r, 4))


# ---- 0x408510, 0x408860 ----------------------------------------------------------------------

def flag_setup(seed, flags):
    def setup(env):
        r = random.Random(seed)
        a = new_object(env, r, 0x40, "flag-owner", o_08=flags)
        obj = new_object(env, r, 0x140, "object", o_12c=a)
        return {"obj": obj, "a": a}
    return setup


def vcall_setup(seed, slot_value_kind):
    def setup(env):
        r = random.Random(seed)
        log = new_log(env)
        vtable = new_object(env, r, 0x80, "vtable")
        for slot in range(0, 0x80, 4):
            if slot != 0x28:
                env.put(vtable + slot, env.stub(f"decoy-{slot:x}", "thiscall", 0, logger(log, 0xD000 + slot)))
        env.put(vtable + 0x28, env.stub("slot-28", "thiscall", 0, logger(log, 0x28, slot_value_kind)))
        obj = new_object(env, r, 0x40, "object", o_00=vtable)
        return {"obj": obj, "log": log}
    return setup


# ---- 0x408580 and 0x43ad20: the three dispatch tables ------------------------------------------

# (base address of the table struct, lowest index, highest index, entry stride)
TABLES = ((0x5375D8, 10, 17, 8), (0x534910, 14, 22, 12), (0x538428, -70, 130, 16))
CYCLE = 7


def make_table(env, r, log, number, nonzero, default_nonzero, error_type, default_field=None):
    base, lo, hi, stride = TABLES[number]
    stubs = [env.stub(f"table{number}-entry{k}", "thiscall", 0, logger(log, number * 0x100 + k)) for k in range(CYCLE)]
    words = []
    for value in range(lo, hi + 1):
        words.append(stubs[value % CYCLE] if nonzero(value) else 0)
        words.extend(junk(r, stride // 4 - 1))
    buf = env.object((hi - lo + 1) * stride, f"table{number}", words=words)
    default = env.object(stride, f"table{number}-default",
                         words=[env.stub(f"table{number}-default", "thiscall", 0, logger(log, number * 0x100 + 0xFF))
                                if default_nonzero else 0] + junk(r, stride // 4 - 1))
    error = new_object(env, r, 0x20, f"table{number}-error", o_0c=error_type)
    env.put(base + 4, error, lo, hi, buf, default, stride, *junk(r, 2))
    if default_field is not None:
        # The default entry is only used when growing fails, which no case can reach, so the field may hold any
        # word. A word below every index makes a read of +0x14 in place of the upper bound at +0x0c visible.
        env.put(base + 0x14, default_field(lo, hi) & MASK)
    return buf


PATTERNS = (
    (lambda v: True, lambda v: True),
    (lambda v: False, lambda v: False),
    (lambda v: v % 2 == 1, lambda v: v % 3 != 1),
)


DEFAULT_FIELDS = (None, lambda lo, hi: 0, lambda lo, hi: -1000, lambda lo, hi: lo - 3, lambda lo, hi: lo, lambda lo, hi: 0x7FFFFFFF)


def chain_setup(seed, pattern, kind=0):
    def setup(env):
        r = random.Random(seed)
        env.put(ERROR_MODE, 0)
        log = new_log(env)
        t1, t2 = PATTERNS[pattern]
        field = DEFAULT_FIELDS[kind % len(DEFAULT_FIELDS)]
        make_table(env, r, log, 0, t1, True, 4, field)
        make_table(env, r, log, 1, t2, True, 4, field)
        make_table(env, r, log, 2, lambda v: True, True, 4)
        obj = new_object(env, r, 0x40, "receiver")
        return {"obj": obj, "log": log}
    return setup


# Every p is inside the third table, whose entries are all live. Tables one and two grow when p lies outside them;
# the new entry is then zero and the lookup falls through to the next table. A failing realloc cannot be exercised:
# the original's failure path reads [0 + 4] and crashes.
P_LIST = (-30, -1, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 40, 100)


def chain_cases(function, name, r):
    kind = 0
    for p in P_LIST:
        for pattern in range(3):
            kind += 1
            yield Case(f"{name} p={p} pattern={pattern}", function, chain_setup(r.getrandbits(64), pattern, kind),
                       receiver=lambda t: t["obj"], arguments=(p & MASK,))


# ---- 0x408870 -----------------------------------------------------------------------------------

def fall_setup(seed, x, y, yoff, sx=4, sy=3, width=100, height=80, anim=True, trie="match",
               cells=((2, 3, 0xEEEEEEEE), (5, 6, 0xFFFFFFFF), (1, 1, 0xFFFF0002), (4, 2, 0xEEEE0005)), pad_tile=None):
    def setup(env):
        r = random.Random(seed)
        log = new_log(env)
        snaps = env.object(0x100, "snapshots", fill=0)
        ref = {}

        def snapshot(effect):
            def run(env, call):
                n = env.get(snaps)
                if n < 7:
                    obj, holder = ref["obj"], ref["holder"]
                    env.put(snaps + 4 + n * 0x24, env.get(obj + 0x134), env.get(obj + 0x24), env.get(obj + 0x130),
                            env.get(obj + 0x138), env.get(obj + 0x160), env.get(obj + 0x164), env.get(holder + 8),
                            env.get(holder + 0x190), env.get(ref["shape"] + 0x1C))
                env.put(snaps, n + 1)
                return effect(env, call)
            return run
        cols, rows = max(((width - 1) >> sx) + 1, 1), max(((height - 1) >> sy) + 1, 1)
        row_stride = cols + 2
        row_table = [ty * row_stride + (ty & 1) for ty in range(rows)]
        tiles = [(r.randrange(0x10000) << 16) | (k % 16) for k in range(max(rows * row_stride + cols + 4, 64))]
        for tx, ty, value in cells:
            tiles[row_table[ty] + tx] = value
        # four spare words before each array, so that an index of -1 (a pixel clamped to width - 1 or height - 1 of an
        # empty extent) still reads a backed word
        tile_pad = [(r.randrange(0x10000) << 16) | (3 + k) for k in range(4)]
        if pad_tile is not None:
            tile_pad[3] = pad_tile
        tile_array = env.object((len(tiles) + 4) * 4, "tiles", words=tile_pad + tiles)
        row_array = env.object((len(row_table) + 4) * 4, "rows", words=[20, 21, 22, 23] + row_table)
        tile_vtable = new_object(env, r, 0x40, "tile-vtable")
        env.put(tile_vtable + 0x20, env.stub("tile-hit", "thiscall", 2,
                                              snapshot(logger(log, 0x7E, lambda env, call: env.get(call.receiver + 4)))))
        results = (1, 0, 2, 1, 5, 0, 1, 3, MASK, 1, 0, 2, 1, 0, 7, 1)
        tile_objects = [env.object(16, f"tile-object-{i}", words=[tile_vtable, results[i]] + junk(r, 2))
                        for i in range(16)]
        object_array = env.object(64, "tile-objects", words=tile_objects)
        grid = new_object(env, r, 0x98, "grid", o_20=tile_array + 16, o_24=row_array + 16, o_30=width & MASK, o_34=height & MASK,
                          o_8c=sx, o_90=sy)
        level = new_object(env, r, 0x80, "level", o_4c=object_array, o_5c=grid)
        level_owner = new_object(env, r, 0x40, "level-owner", o_24=level)
        world = new_object(env, r, 0x130, "world", o_0c=level_owner, o_124=yoff & MASK)
        owner = new_object(env, r, 0xE0, "owner")
        shape = new_object(env, r, 0x20, "shape", o_1c=r.randrange(1, 1 << 32))
        vtable = new_object(env, r, 0x80, "vtable")
        env.put(vtable + 0x3C, env.stub("object-slot-3c", "thiscall", 0, snapshot(logger(log, 0x3C))))
        holder = new_object(env, r, 0x1C0, "holder")
        anim_object = animation(env, r, "animation") if anim else 0
        obj = new_object(env, r, 0x180, "object", o_00=vtable, o_08=world, o_0c=owner, o_10=shape,
                         o_12c=holder, o_150=anim_object)
        ref.update(obj=obj, holder=holder, shape=shape)
        env.write(obj + 0x68, struct.pack("<d", x))
        env.write(obj + 0x70, struct.pack("<d", y))
        env.put(FALL_STAMP, r.randrange(1, 1 << 32))
        if trie == "match":
            set_trie(env, r, "LS_FALLING", "LS_FALLING", r.randrange(1, 1 << 32))
        elif trie == "mismatch":
            set_trie(env, r, "LS_FALLING", "LS_FALLINX", r.randrange(1, 1 << 32))
        else:
            clear_trie(env, r)
        return {"obj": obj, "log": log}
    return setup


XS = (-7.5, -0.5, 0.0, 15.99, 16.0, 40.5, 85.2, 99.99, 100.0, 133.7, 3.0e9)
YS = (-12.25, -0.9, 0.0, 7.99, 8.0, 26.0, 50.1, 79.0, 90.5, 200.0, -3.0e9)
OFFSETS = (0, 5, -3, 12, -40, 30, 1, -1, 0, 80)


def fall_cases(r):
    def make(label, x, y, yoff, **options):
        return Case(f"fall {label} x={x} y={y} off={yoff}", F_408870,
                    fall_setup(r.getrandbits(64), x, y, yoff, **options), receiver=lambda t: t["obj"])
    for i, x in enumerate(XS):
        for j, y in enumerate(YS):
            yield make("grid", x, y, OFFSETS[(i + 3 * j) % len(OFFSETS)])
    yield make("empty tile eeeeeeee", 40.5, 26.0, 0)
    yield make("empty tile ffffffff", 85.2, 50.1, 0)
    yield make("tile ffff0002 is live", 16.0, 8.0, 0)
    yield make("tile eeee0005 is live", 64.5, 16.5, 0)
    yield make("empty tile eeeeeeee, y from offset", 40.5, 10.0, 16)
    yield make("empty tile ffffffff, y from offset", 85.2, 70.1, -20)
    yield make("no animation", 40.5, 26.0, 0, anim=False)
    yield make("no animation, other tile", 70.0, 61.0, 3, anim=False)
    yield make("trie mismatch", 33.3, 44.4, 2, trie="mismatch")
    yield make("trie empty", 33.3, 44.4, 2, trie="empty")
    yield make("trie empty, empty tile", 40.5, 26.0, 0, trie="empty")
    for x in (-1.5, 0.0, 7.99, 8.0, 31.5, 59.99, 60.5):
        for y in (-2.0, 15.99, 16.0, 70.5, 129.9, 131.0):
            yield make("geometry 3/4", x, y, 4 * int(x) % 7 - 3, sx=3, sy=4, width=60, height=130,
                       cells=((2, 3, 0xEEEEEEEE), (5, 6, 0xFFFFFFFF), (1, 1, 0xFFFF0002), (7, 8, 0xEEEE0005)))
    for _ in range(24):
        yield make("random", round(r.uniform(-20, 135), 3), round(r.uniform(-30, 125), 3), r.randrange(-25, 26))


DIMS = ((100, 80, 4, 3), (0, 80, 4, 3), (100, 0, 4, 3), (0, 0, 4, 3), (-3, 50, 4, 3), (60, -4, 4, 3),
        (1, 1, 0, 0), (16, 8, 4, 3))


def truncating(target, k):
    """A float that __ftol truncates to `target`, with a fractional part that varies with k."""
    fraction = (0.0, 0.75, 0.5, 0.25)[k % 4]
    sign = -1 if target < 0 else 1 if target > 0 else (1 if k % 2 else -1)
    return target + sign * fraction


def edge_cases(r):
    """The pixel position is clamped against 0 and against the extent of the tile grid. Put it exactly on, one below
    and one above both edges, with the extent positive, zero and negative, and with different row offsets."""
    n = 0
    for width, height, sx, sy in DIMS:
        def make(label, x, y, yoff, **options):
            return Case(f"fall edge {label} {width}x{height}/{sx},{sy} x={x} y={y} off={yoff}", F_408870,
                        fall_setup(r.getrandbits(64), x, y, yoff, sx=sx, sy=sy, width=width, height=height,
                                   cells=((0, 0, 0xEEEEEEEE),) if width > 0 and height > 0 else (), **options),
                        receiver=lambda t: t["obj"])
        x_mid = float(max(0, min(width - 1, 5)))
        y_mid = float(max(0, min(height - 1, 3)))
        for t in sorted({-2, -1, 0, 1, width - 1, width, width + 1}):
            n += 1
            yield make("x", truncating(t, n), y_mid, (0, 3, -2)[n % 3], pad_tile=(None, 0xEEEEEEEE, 0xFFFFFFFF)[n % 3])
        for t in sorted({-2, -1, 0, 1, height - 1, height, height + 1}):
            n += 1
            off = (0, 3, -2, 7)[n % 4]
            yield make("y", x_mid, truncating(t - off, n), off, pad_tile=(None, 0xEEEEEEEE, 0xFFFFFFFF)[n % 3])
        yield make("corner", 0.0, 0.0, 0)
        yield make("corner low", -0.5, -0.5, 0, pad_tile=0xEEEEEEEE)
        yield make("corner high", float(width), float(height), 0)


# ---- 0x43b120, 0x43b160, 0x43b1a0, 0x43b1e0, 0x43b210 --------------------------------------------

def sync_setup(seed, equal, with_pending, anim=True, xor=None):
    def setup(env):
        r = random.Random(seed)
        value = r.randrange(1, 1 << 32)
        holder = new_object(env, r, 0x1C0, "holder", o_190=value)
        pending = animation(env, r, "pending") if with_pending else 0
        current = animation(env, r, "current") if anim else 0
        obj = new_object(env, r, 0x180, "object", o_12c=holder, o_174=value if equal else value ^ (xor or r.randrange(1, 1 << 32)),
                         o_178=pending, o_c8=r.randrange(2, 1 << 32), o_134=r.randrange(1, 1 << 32), o_150=current)
        return {"obj": obj}
    return setup


def voice_pool(env, r, player_sound, probe):
    """What 0x4b45f0 needs to find an idle voice and set its pitch, volume and pan: the player's voice list holds one
    voice whose buffer is idle. The buffer methods record their arguments."""
    log = env.object(0x80, "voice-log", fill=0)

    def recorder(slot, result=0, out_arg=None):
        def effect(env, call):
            n = env.calls_so_far(call.function)
            env.put(log + slot * 0x10, n, call.receiver & MASK, *[a & MASK for a in call.arguments[:2]])
            if out_arg is not None:
                env.put(call.arguments[out_arg], 0)
            return result
        return effect

    vtable = new_object(env, r, 0x60, "voice-vtable")
    # The status method is a function of the original image that only returns zero (xor eax, eax; ret 8). A stand-in
    # would see the address of a local of 0x4b3e70 as its second argument, which is a stack address that differs
    # between the native and the original run.
    env.put(vtable + 0x24, IDLE_STATUS)
    env.put(vtable + 0x30, env.stub("voice-play", "stdcall", 4, recorder(1)))
    env.put(vtable + 0x3C, env.stub("voice-frequency", "stdcall", 2, recorder(2)))
    env.put(vtable + 0x40, env.stub("voice-volume", "stdcall", 2, recorder(3)))
    env.put(vtable + 0x44, env.stub("voice-pan", "stdcall", 2, recorder(4)))
    buf = env.object(0x10, "voice-buffer", fill=0)
    env.put(buf, vtable)
    voice = new_object(env, r, 0x60, "voice", o_0c=buf, o_10=probe, o_30=r.randrange(1, 1 << 32))
    env.put(voice + 0x04, 0, 0)
    env.put(player_sound + 0x30, voice + 4, voice + 4)
    env.put(player_sound + 0x18, r.randrange(1, 1000), r.randrange(1, 1000), r.randrange(1, 1000), r.randrange(1, 1000))
    return voice


def debug_setup(seed, queue, flag, voice=False, probe78=0, sound_index=None):
    def setup(env):
        r = random.Random(seed)
        log = new_log(env)
        env.put(DEBUG_FLAG, flag)
        env.put(DEBUG_VALUE, r.randrange(1, 1 << 32) if sound_index is None else sound_index)
        vtable = new_object(env, r, 0x80, "vtable")
        env.put(vtable + 0x2C, env.stub("object-slot-2c", "thiscall", 0, logger(log, 0x2C)))
        obj_q = 0
        if queue:
            inner = new_object(env, r, 0x80, "debug-inner")
            probe = new_object(env, r, 0x100, "debug-state", o_78=probe78)
            env.put(inner + 0x10, probe)
            if voice:
                voice_pool(env, r, inner, probe)
            obj_q = new_object(env, r, 0x40, "queue", o_10=inner)
        obj = new_object(env, r, 0x180, "object", o_00=vtable, o_17c=obj_q, o_c8=r.randrange(2, 1 << 32))
        return {"obj": obj, "log": log}
    return setup


def flags_setup(seed, current, flags):
    def setup(env):
        r = random.Random(seed)
        owner = new_object(env, r, 0x80, "owner", o_64=current, o_08=flags)
        obj = new_object(env, r, 0xE0, "object", o_0c=owner, o_c8=r.randrange(2, 1 << 32))
        return {"obj": obj}
    return setup


EXPLOSION_NAME = b"GAME_DYNAMITEEXPLO"


def string_hash(text):
    value = 0
    for byte in text:
        value = (value * 33 + byte) & MASK
    return value


def explode_setup(seed, anim, trie, lookup="found", index=None):
    def setup(env):
        r = random.Random(seed)
        buckets = 17
        map_owner = env.object(0x40, "map-owner", fill=0)
        env.put(map_owner + 0x18, buckets)
        slot = string_hash(EXPLOSION_NAME) % buckets
        if lookup != "no-table":
            table = [0] * buckets
            # four spare words before the array, so that a negative index still reads a backed word
            entry_array = env.object(64, "entries", words=junk(r, 16))
            entry = new_object(env, r, 0x70, "entry", o_14=entry_array + 16, o_64=r.randrange(0, 5), o_68=0)
            env.put(entry + 0x68, 4 if lookup == "found" else 0)
            if lookup == "found-out-of-range":
                env.put(entry + 0x64, 5)
                env.put(entry + 0x68, 4)
            if index is not None:
                env.put(entry + 0x64, index[0] & MASK, index[1] & MASK)
            key = env.object(len(EXPLOSION_NAME) + 1, "key", data=EXPLOSION_NAME + b"\0")
            decoy_key = env.object(len(EXPLOSION_NAME) + 1, "decoy-key", data=EXPLOSION_NAME[:-1] + b"P\0")
            node = env.object(16, "node", words=[0, 0, key, entry])
            decoy = env.object(16, "decoy", words=[node, 0, decoy_key, r.randrange(1, 1 << 32)])
            if lookup == "missing":
                node = decoy = env.object(16, "other", words=[0, 0, decoy_key, r.randrange(1, 1 << 32)])
                decoy = env.object(16, "other2", words=[node, 0, decoy_key, r.randrange(1, 1 << 32)])
            table[slot] = decoy
            for k in range(buckets):
                if k != slot and k % 5 == 2:
                    table[k] = env.object(16, "unrelated", words=[0, 0, decoy_key, r.randrange(1, 1 << 32)])
            env.put(map_owner + 0x14, env.object(buckets * 4, "buckets", words=table))
        middle = new_object(env, r, 0x20, "map-holder", o_10=map_owner)
        holder = new_object(env, r, 0x1C0, "holder", o_0c=middle, o_190=r.randrange(1, 1 << 32))
        shape = new_object(env, r, 0x20, "shape", o_1c=r.randrange(1, 1 << 32))
        obj = new_object(env, r, 0x1A0, "object", o_10=shape, o_12c=holder,
                         o_174=animation(env, r, "animation") if anim else 0,
                         o_180=r.randrange(1, 1 << 32), o_134=r.randrange(1, 1 << 32), o_24=r.randrange(1, 1 << 32))
        if trie == "match":
            set_trie(env, r, "LS_EXPLODING", "LS_EXPLODING", r.randrange(1, 1 << 32))
        elif trie == "mismatch":
            set_trie(env, r, "LS_EXPLODING", "LS_FALLING", r.randrange(1, 1 << 32))
        else:
            clear_trie(env, r)
        return {"obj": obj}
    return setup


def regrown_case(function, number, low, count, tail, skip, seed):
    """A table of one-byte entries that grows by one entry below `low`. The new entry is a four-byte read that straddles
    the new zero byte and the first three old bytes, so it is not zero and names a stand-in at a page boundary: the
    original takes its second pass (which zeroes the scratch word at +0x20 that the grow routine just set) and calls
    through the regrown entry. The stand-in records the table fields as it finds them."""
    base, _, _, _ = TABLES[number]

    def setup(env):
        r = random.Random(seed)
        log = new_log(env)
        env.put(log, 0)

        def effect(env, call):
            env.put(log + 8, 0xCA11, call.receiver, env.get(base + 8), env.get(base + 0xC), env.get(base + 0x10),
                    env.get(base + 0x1C), env.get(base + 0x20), env.get(base + 0x24))
            return 0x7001
        target = 0
        pages = 0
        while pages <= skip:
            target = env.stub("regrown entry", "thiscall", 0, effect)
            if target & 0xFF == 0:
                pages += 1
        old = bytes([(target >> 8) & 0xFF, (target >> 16) & 0xFF, 0]) + bytes(tail)
        old = old + bytes((0x31 + 7 * i) & 0xFF or 1 for i in range(count - len(old)))
        entries = env.object(count, "byte entries", data=old[:count])
        error = new_object(env, r, 0x20, "table-error", o_0c=4)
        default = new_object(env, r, 0x10, "table-default")
        env.put(base + 4, error, low & MASK, (low + count - 1) & MASK, entries, (0, -1000, low - 3)[skip % 3] & MASK, 1, *junk(r, 4))
        obj = new_object(env, r, 0x40, "receiver")
        return {"obj": obj, "log": log}
    return setup, low - 1


def regrown_cases(r):
    layouts = ((4, 6, (0xE1, 0x5C, 0x93)), (-9, 12, (0x44, 0x88, 0xCC, 0x21, 0x09)), (40, 4, (0x77,)), (0, 5, (1, 2)),
               (-1, 3, ()), (100, 7, (0x90, 0x91, 0x92, 0x93)))
    for function, name, number in ((F_408580, "408580", 1), (F_43AD20, "43ad20", 0)):
        for index, (low, count, tail) in enumerate(layouts):
            setup, p = regrown_case(function, number, low, count, tail, index % 3, r.getrandbits(64))
            yield Case(f"{name} regrown entry second pass {index}", function, setup, receiver=lambda t: t["obj"],
                       arguments=(p & MASK,))


def cases(random_source):
    r = random_source
    seed = r.getrandbits

    for flags in (0, 0xFFFFFFFF, 0x10000, 0xFFFEFFFF, 1, 0x20002):
        yield Case(f"408510 flags {flags:#x}", F_408510, flag_setup(seed(64), flags), receiver=lambda t: t["obj"])
    for _ in range(3):
        yield Case("408510 random flags", F_408510, flag_setup(seed(64), r.randrange(1 << 32)),
                   receiver=lambda t: t["obj"])
    for result in (0, 1, 0x1234ABCD):
        yield Case(f"408860 jumps through vtable slot 0x28 ({result:#x})", F_408860, vcall_setup(seed(64), result),
                   receiver=lambda t: t["obj"])

    yield from chain_cases(F_408580, "408580", r)
    yield from chain_cases(F_43AD20, "43ad20", r)
    yield from regrown_cases(r)
    yield from fall_cases(r)
    yield from edge_cases(r)

    for equal in (True, False):
        for pending in (True, False):
            for anim in (True, False):
                yield Case(f"43b120 equal={equal} pending={pending} anim={anim}", F_43B120,
                           sync_setup(seed(64), equal, pending, anim), receiver=lambda t: t["obj"])
                yield Case(f"43b160 equal={equal} pending={pending} anim={anim}", F_43B160,
                           sync_setup(seed(64), equal, pending, anim), receiver=lambda t: t["obj"])

    for xor in (1, 0x80000000, 0x10000, 0x100):
        for pending in (True, False):
            for anim in (True, False):
                yield Case(f"43b120 differs by {xor:#x} pending={pending} anim={anim}", F_43B120,
                           sync_setup(seed(64), False, pending, anim, xor), receiver=lambda t: t["obj"])
                yield Case(f"43b160 differs by {xor:#x} pending={pending} anim={anim}", F_43B160,
                           sync_setup(seed(64), False, pending, anim, xor), receiver=lambda t: t["obj"])

    for queue in (False, True):
        for flag in (0, 1, 0x8000, MASK):
            yield Case(f"43b1a0 queue={queue} flag={flag:#x}", F_43B1A0, debug_setup(seed(64), queue, flag),
                       receiver=lambda t: t["obj"])
    for number, (flag, probe78) in enumerate(((1, 1), (2, 1), (0x100, 0x20), (0x8000, MASK), (0x10000, 2), (MASK, 0x100),
                                              (0x80000000, 1), (0x10000000, 7), (0, 1), (0, 0), (2, 0))):
        yield Case(f"43b1a0 voice flag={flag:#x} probe={probe78:#x}", F_43B1A0,
                   debug_setup(seed(64), True, flag, voice=True, probe78=probe78, sound_index=3 + 4 * number),
                   receiver=lambda t: t["obj"])
    yield Case("43b1a0 voice, no queue", F_43B1A0, debug_setup(seed(64), False, 2, voice=True, sound_index=5),
               receiver=lambda t: t["obj"])
    for queue in (False, True):
        yield Case(f"43b1a0 random flag queue={queue}", F_43B1A0,
                   debug_setup(seed(64), queue, r.randrange(1, 1 << 32)), receiver=lambda t: t["obj"])

    for current, flags in ((0x2134, 0), (0x2134, 0x20000), (0x2134, MASK), (0, 0), (0x2133, 0x20000),
                           (0x2135, 0x5), (MASK, 0x10), (0x12134, 0x100), (0x2134 << 4, 0xFFFDFFFF)):
        yield Case(f"43b1e0 current {current:#x} flags {flags:#x}", F_43B1E0, flags_setup(seed(64), current, flags),
                   receiver=lambda t: t["obj"])
    for current, flags in ((0x2135, 0), (0x2134 ^ 0x80000000, 0), (0x2134 ^ 0x100, 0x20000), (0x2134 ^ 0x10000, 0xFFFDFFFF),
                           (0x2134, 0x20000 ^ MASK), (0x2134, 0x10000), (0x2134, 0x40000), (0x2134 ^ 4, 0x20000)):
        yield Case(f"43b1e0 current {current:#x} flags {flags:#x}", F_43B1E0, flags_setup(seed(64), current, flags),
                   receiver=lambda t: t["obj"])
    for _ in range(3):
        yield Case("43b1e0 random", F_43B1E0, flags_setup(seed(64), r.randrange(1 << 32), r.randrange(1 << 32)),
                   receiver=lambda t: t["obj"])

    for anim in (True, False):
        for trie in ("match", "mismatch", "empty"):
            for lookup in ("found", "found-out-of-range", "missing", "no-table"):
                yield Case(f"43b210 anim={anim} trie={trie} lookup={lookup}", F_43B210,
                           explode_setup(seed(64), anim, trie, lookup), receiver=lambda t: t["obj"])
    for index in ((3, 3), (0, 0), (-1, -1), (-2, 0), (-1, -3), (2, 1), (11, 11), (-4, -4), (7, 8), (0, -1), (1, 0),
                  (MASK, 0), (0, MASK)):
        for anim in (True, False):
            yield Case(f"43b210 anim={anim} range check {index}", F_43B210,
                       explode_setup(seed(64), anim, "match", "found", index), receiver=lambda t: t["obj"])
    for lookup in ("found", "found-out-of-range", "missing", "no-table", "found"):
        yield Case(f"43b210 random lookup={lookup}", F_43B210,
                   explode_setup(seed(64), r.random() < 0.5, "match", lookup), receiver=lambda t: t["obj"])

