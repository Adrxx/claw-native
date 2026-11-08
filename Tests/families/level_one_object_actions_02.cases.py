"""Original-only cases for level_one_object_actions_02: the Officer enemy's dispatch, construction and helpers."""
import struct

from clawparity.cases import Case
from clawparity.fixtures import returns, sequence
from clawparity.program import claw
from clawparity.world import cstring, resource_manager, set_rect, set_rect_empty, sprite, world

M32 = 0xFFFFFFFF
RAND = 0x4A3050
NEW = 0x4F63EC
SET_RECT_SLOT, SET_RECT_EMPTY_SLOT = 0x546D5C, 0x546CDC
G_TICKS, G_PLAYER, G_MODE, G_STEP, G_SWITCH = 0x537210, 0x537E88, 0x534EAC, 0x5430C4, 0x541334
G_FLOATS = (0x5262B0, 0x5262B4, 0x5262B8)
G_VARIANT = 0x537964
G_STRUCT = 0x5378A0

F_44F840, F_44F850, F_452B00, F_452C50 = 0x44F840, 0x44F850, 0x452B00, 0x452C50
F_462350, F_462410, F_462AF0, F_462EF0 = 0x462350, 0x462410, 0x462AF0, 0x462EF0
F_463120, F_4631E0 = 0x463120, 0x4631E0
F_46A8D0, F_46C2C0 = 0x46A8D0, 0x46C2C0

ANIM_KEYS = (0x52983C, 0x529820, 0x529808, 0x5297F0, 0x5297D8, 0x5297C0, 0x5297A8, 0x529790, 0x52977C,
             0x529764, 0x52974C, 0x529738, 0x529724, 0x52970C, 0x5296F4, 0x5296DC, 0x529870)
SOUND_KEYS = (0x5296C4, 0x5296AC, 0x529694, 0x529678, 0x529664, 0x529650)
SPRITE_KEY, NULL_KEY, IDLE_KEY, PACING_KEY = 0x529854, 0x5234B4, 0x523148, 0x527D78


def f32(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def text_at(program, address):
    for section in program.sections:
        if section.address <= address < section.address + len(section.data):
            return section.data[address - section.address:].split(b"\0", 1)[0]
    raise ValueError("original string is not backed")


def words_of(random_source, count):
    return [random_source.randrange(1, 1 << 32) for _ in range(count)]


def animation(env, duration=100, name="animation"):
    """An animation sequence whose single frame is large enough for the original's frame stepper."""
    sequence_record = env.object(0x20, name, fill=0)
    frames = env.object(4, name + "-frames", fill=0)
    frame = env.object(0x40, name + "-frame", fill=0)
    env.put(sequence_record + 0xC, frames, 1)
    env.put(frames, frame)
    env.put(frame + 0x1C, duration)
    return sequence_record


def install_imports(env):
    """The two rectangle imports are called through import-table slots: put a stand-in in each slot."""
    env.put(SET_RECT_SLOT, env.stub("SetRect", "stdcall", 5, set_rect))
    env.put(SET_RECT_EMPTY_SLOT, env.stub("SetRectEmpty", "stdcall", 1, set_rect_empty))


def script_rand(env, values):
    env.override(RAND, sequence(*values))


def recorder(log, tag, result=0):
    """A callback that publishes its receiver and arguments into the shared log object."""
    def effect(env, call):
        count = env.get(log)
        row = log + 4 + (count % 24) * 0x20
        # Only the first argument is published: later ones may point into a caller's stack frame.
        words = [tag, call.receiver, len(call.arguments)] + list(call.arguments)[:1]
        env.put(row, *(words + [0] * (8 - len(words))))
        env.put(log, count + 1)
        return result
    return effect


def set_bits(env, officer, size, word):
    env.put(officer + 0x2FC, size)
    if size > 0x20:
        count = (size + 31) // 32
        bits = env.object(4 * count, "bits", words=[word] + [0x5A5A5A5A] * (count - 1))
        env.put(officer + 0x300, bits)
    else:
        env.put(officer + 0x300, word)


# ------------------------------------------------------------------------------------------------
# 0x44f840: tail call through virtual slot 0x48
def vslot_cases(random_source):
    for _ in range(6):
        salt = random_source.getrandbits(32)

        def setup(env, salt=salt):
            log = env.object(0x200, "slot-log", fill=0)
            vtable = env.object(0x80, "vtable", fill=0)
            obj = env.object(0x40, "object", words=words_of(random_source, 16))
            env.put(obj, vtable)
            for offset in (0x40, 0x44, 0x4C, 0x50):
                env.put(vtable + offset, env.stub(f"decoy-{offset:x}", "thiscall", 0, recorder(log, 0xDEAD0000 + offset)))
            env.put(vtable + 0x48, env.stub("slot-48", "thiscall", 0, recorder(log, 0x48, salt)))
            return {"obj": obj}

        yield Case(f"virtual slot 0x48 salt {salt:#x}", F_44F840, setup, receiver=lambda t: t["obj"])


# ------------------------------------------------------------------------------------------------
# 0x44f850: bounded random number
def rand_cases(random_source):
    plain = [0, 1, 2, 3, 4, 5, 99, 0x7FFF, 0x7FFFFFFF, 0x80000001, 0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFFF0, 0x80000005]
    plain += [random_source.randrange(0, 1 << 32) for _ in range(6)]
    for value in plain + [0x80000000]:
        def setup(env, value=value):
            script_rand(env, [value])
            return {}
        yield Case(f"rand parity {value:#x}", F_44F850, setup, arguments=(M32,))
    bounds = [0, 1, 2, 3, 9, 99, 999, 0x7FFF, 0x10000, 0x7FFFFFFE, 0x7FFFFFFF, 0xFFFFFFFE, 0xFFFFFFFD, 0x80000000]
    for bound in bounds:
        for value in plain + [0x80000000]:
            if bound == 0xFFFFFFFE and value == 0x80000000:
                continue  # INT_MIN / -1 traps in the original as well
            if random_source.random() < 0.55:
                continue

            def setup(env, value=value):
                script_rand(env, [value])
                return {}
            yield Case(f"rand {value:#x} below {bound:#x}", F_44F850, setup, arguments=(bound,))


# ------------------------------------------------------------------------------------------------
# 0x452b00 and 0x452c50: per-variant rectangle tables
def globals_setup(random_source):
    def setup(env):
        install_imports(env)
        env.put(G_STRUCT, *words_of(random_source, 0xD0 // 4))
        env.put(G_STRUCT + 0xD0, *words_of(random_source, 4))
        env.put(G_FLOATS[0], f32(0.5), f32(2.5), f32(7.0))
        return {}
    return setup


def variant_cases(random_source):
    for value in (0, -1, 0x80000000, 0x7FFFFFFF, 15, 16, 100) + tuple(range(1, 15)):
        yield Case(f"variant {value & M32:#x}", F_452B00, globals_setup(random_source), arguments=(value & M32,))
    for value in (3, 11):
        yield Case(f"variant {value} again, other prior data", F_452B00, globals_setup(random_source), arguments=(value,))


def first_variant_cases(random_source):
    yield Case("rectangle table with null record", F_452C50, globals_setup(random_source), arguments=(0,))
    for _ in range(4):
        def setup(env):
            install_imports(env)
            record = env.object(0x90, "record", words=words_of(random_source, 0x24))
            env.put(G_FLOATS[0], *words_of(random_source, 3))
            return {"record": record}
        yield Case("rectangle table on a record", F_452C50, setup, arguments=(lambda t: t["record"],))


# ------------------------------------------------------------------------------------------------
# 0x462af0: dispatch through a growable handler table
TABLE = dict(lo=0x537BA8, hi=0x537BAC, base=0x537BB0, stride=0x537BB8, fallback=0x537BB4, flag=0x537BC0)
MAIN = dict(lo=0x537880, hi=0x537884, base=0x537888, stride=0x537890, fallback=0x53788C, flag=0x537898)
SECOND = dict(lo=0x537640, hi=0x537644, base=0x537648, stride=0x537650, fallback=0x53764C, flag=0x537658)


def table_setup(random_source, low, high, stride, present, mirror="main", ident=None, empty_base=False):
    """Install a handler table (function pointers, `present[i]` says whether entry i has one) in the globals."""
    sub_low = low if ident is None else min(low, ident)
    sub_high = high if ident is None else max(high, ident)

    def setup(env):
        log = env.object(0x300, "handler-log", fill=0)
        count = high - low + 1
        area = env.object(stride * count + 16, "handler-table", words=words_of(random_source, (stride * count + 16) // 4))
        for index in range(count):
            if present[index % len(present)]:
                env.put(area + index * stride, env.stub(f"handler-{index}", "thiscall", 0, recorder(log, 0x100 + index, 7 + index)))
            else:
                env.put(area + index * stride, 0)
        env.put(TABLE["lo"], low)
        env.put(TABLE["hi"], high)
        env.put(TABLE["base"], 0 if empty_base else area)
        env.put(TABLE["stride"], stride)
        env.put(TABLE["fallback"], env.object(0x20, "fallback-entry", words=words_of(random_source, 8)))
        env.put(TABLE["flag"], random_source.randrange(1, 1 << 30))
        env.put(0x537BA4, random_source.randrange(1, 1 << 30))
        # The secondary dispatchers that empty entries fall back to.
        wide = sub_high - sub_low + 1
        for name, slots in (("main", MAIN), ("second", SECOND)):
            sub = env.object(stride * wide + 16, f"{name}-dispatch", words=words_of(random_source, (stride * wide + 16) // 4))
            for index in range(wide):
                use = (index % 2 == 0) if name == "main" else (index % 2 == 1)
                if use or mirror == "both":
                    env.put(sub + index * stride, env.stub(f"{name}-handler-{index}", "thiscall", 0,
                                                           recorder(log, 0x200 + 0x10 * (name == "second") + index, 3)))
                else:
                    env.put(sub + index * stride, 0)
            env.put(slots["lo"], sub_low)
            env.put(slots["hi"], sub_high)
            env.put(slots["base"], sub)
            env.put(slots["stride"], stride)
            env.put(slots["fallback"], env.object(0x20, f"{name}-fallback", words=words_of(random_source, 8)))
            env.put(slots["flag"], random_source.randrange(1, 1 << 30))
        target = env.object(0x40, "receiver", words=words_of(random_source, 16))
        return {"target": target, "low": low}
    return setup


def handler_table_cases(random_source):
    for low in (0, 5, -3):
        for stride in (4, 8, 12, 16):
            high = low + 5
            present = [True, False, True, True, False, True]
            for index in (0, 1, 2, 4, 5):
                yield Case(f"table[{low}..{high}] stride {stride} id {low + index}", F_462AF0,
                           table_setup(random_source, low, high, stride, present),
                           receiver=lambda t: t["target"], arguments=((low + index) & M32,))
    yield Case("table all entries empty everywhere", F_462AF0,
               table_setup(random_source, 2, 7, 8, [False] * 6, mirror="both"),
               receiver=lambda t: t["target"], arguments=(4,))
    for ident in (8, 1, 40, 0, -9 & M32):
        for stride in (4, 12):
            signed = ident - (1 << 32) if ident >= 1 << 31 else ident
            yield Case(f"table grows to reach id {signed} stride {stride}", F_462AF0,
                       table_setup(random_source, 2, 7, stride, [True] * 6, mirror="both", ident=signed, empty_base=True),
                       receiver=lambda t: t["target"], arguments=(ident,))


def wrapped_table_setup(random_source, low, stride):
    """A one-entry table asked for an id so far above it that the entry offset wraps back to entry 0.

    The table starts without a block, so the grow call allocates one through the allocator stand-in, which here
    leaves a handler in the first entry.  The grow call succeeds and leaves its added-entry count in the flag
    word, the wrapped offset lands on that handler (so the lookup does not fall back), and only the second flag
    clear can remove the count.
    """
    def setup(env):
        log = env.object(0x300, "handler-log", fill=0)
        handler = env.stub("handler-0", "thiscall", 0, recorder(log, 0x100, 7))
        filler = words_of(random_source, 4)

        def allocator(env, call):
            block = env.object(call.arguments[0], "allocation", fill=0)
            env.put(block, handler, *filler)
            return block

        env.override(0x4A48E0, allocator)
        env.put(TABLE["lo"], low)
        env.put(TABLE["hi"], low)
        env.put(TABLE["base"], 0)
        env.put(TABLE["stride"], stride)
        env.put(TABLE["fallback"], env.object(0x20, "fallback-entry", words=words_of(random_source, 8)))
        env.put(TABLE["flag"], random_source.randrange(1, 1 << 30))
        env.put(0x537BA4, random_source.randrange(1, 1 << 30))
        target = env.object(0x40, "receiver", words=words_of(random_source, 16))
        return {"target": target}
    return setup


def wrapped_table_cases(random_source):
    for low, stride, count in ((2, 0x10000, 0x10000), (-3, 0x8000, 0x20000), (7, 0x4000, 0x40000)):
        ident = (low + count) & M32
        yield Case(f"table id {low + count:#x} wraps to entry 0, stride {stride:#x}", F_462AF0,
                   wrapped_table_setup(random_source, low, stride),
                   receiver=lambda t: t["target"], arguments=(ident,))


# ------------------------------------------------------------------------------------------------
# The Officer record
def officer_world(env, random_source, *, anim_hits=None, sound_hits=None, sprite_hit=True, null_hit=True,
                  owner_words=None, state_words=None, idle=1, keys=None, **options):
    animations = {}
    for index, address in enumerate(ANIM_KEYS):
        if anim_hits is None or address in anim_hits:
            animations[keys[address]] = animation(env, duration=20 + 9 * index, name=f"animation-{index}")
    if null_hit:
        animations[keys[NULL_KEY]] = animation(env, duration=777, name="animation-null")
    sounds = {}
    for index, address in enumerate(SOUND_KEYS):
        if sound_hits is None or address in sound_hits:
            sounds[keys[address]] = env.object(0x40, f"sound-{index}", fill=0x31 + index)
    sprites = {keys[SPRITE_KEY]: sprite(env, width=30 + random_source.randrange(40), height=50 + random_source.randrange(60),
                                         origin=(random_source.randrange(9), random_source.randrange(9)))} if sprite_hit else {}
    w = world(env, resources={"animations": animations, "sounds": sounds, "sprites": sprites},
              owner_words=owner_words, state_words=state_words, idle_state=idle, **options)
    owner = w["owner"]
    env.put(owner + 0x18C, owner)  # animator back pointer
    install_imports(env)
    return w


def make_officer(env, random_source, w, vtable=None, size=0x470, words=None, fields=None):
    officer = env.object(size, "officer", words=words_of(random_source, size // 4))
    env.put(officer + 0x128, w["owner"], w["owner"], w["state"])
    env.put(officer + 0xC, w["owner"], w["state"])
    env.put(officer + 0x10, w["state"])
    if vtable is not None:
        env.put(officer, vtable)
    for offset, value in (fields or {}).items():
        env.put(officer + offset, value)
    return officer


def ctor_setup(random_source, program_keys, *, anim_hits=None, sound_hits=None, sprite_hit=True, null_hit=True,
               rands=(7, 11, 13), flip=False, variant=1, floats=(1.0, 1.0, 1.0), state_count=0, ticks=None):
    def setup(env):
        w = officer_world(env, random_source, anim_hits=anim_hits, sound_hits=sound_hits, sprite_hit=sprite_hit,
                          null_hit=null_hit, keys=program_keys,
                          owner_words={8: random_source.randrange(1, 1 << 16), 0x40: 2 if flip else 0,
                                       0x4C: random_source.randrange(50, 900), 0x50: random_source.randrange(50, 900),
                                       0x118: 5, 0x11C: 6, 0x120: 7, 0x124: 8, 0x128: 9, 0x12C: 10, 0x130: 11, 0x134: 12,
                                       0x164: random_source.randrange(1, 1 << 16), 0x188: 0, 0x190: random_source.randrange(1, 1 << 16)},
                          state_words={0x64: state_count, 0x68: random_source.randrange(1, 1 << 16)})
        script_rand(env, rands)
        env.put(G_VARIANT, variant)
        env.put(G_FLOATS[0], *[f32(v) for v in floats])
        env.put(G_TICKS, ticks if ticks is not None else random_source.randrange(1000, 1 << 30))
        env.put(G_SWITCH, 0)
        officer = env.object(0x470, "officer", words=words_of(random_source, 0x470 // 4))
        return {"officer": officer, "owner": w["owner"], "world": w}
    return setup


def ctor_cases(random_source, keys):
    everything = set(ANIM_KEYS)
    for rands in ((7, 5, 8), (-1, 4, 99), (49, 50, 0xFFFFFFFE), (50, 40, 1), (0x80000003, 0x7FFFFFFF, 6)):
        yield Case(f"construct all resources, rand {rands[0]:#x}", F_462410,
                   ctor_setup(random_source, keys, rands=rands), receiver=lambda t: t["officer"],
                   arguments=(lambda t: t["owner"],))
    yield Case("construct, nothing found, no fallback", F_462410,
               ctor_setup(random_source, keys, anim_hits=set(), sound_hits=set(), sprite_hit=False, null_hit=False),
               receiver=lambda t: t["officer"], arguments=(lambda t: t["owner"],))
    yield Case("construct, only fallback animation", F_462410,
               ctor_setup(random_source, keys, anim_hits=set(), sound_hits=set()),
               receiver=lambda t: t["officer"], arguments=(lambda t: t["owner"],))
    ordered = list(ANIM_KEYS)
    for _ in range(5):
        hits = {a for a in ordered if random_source.random() < 0.5}
        sounds = {a for a in SOUND_KEYS if random_source.random() < 0.6}
        yield Case(f"construct random hits {len(hits)}/{len(sounds)}", F_462410,
                   ctor_setup(random_source, keys, anim_hits=hits, sound_hits=sounds,
                              null_hit=random_source.random() < 0.5, rands=(random_source.randrange(1 << 32), 9, 40)),
                   receiver=lambda t: t["officer"], arguments=(lambda t: t["owner"],))
    for floats in ((1.0, 1.0, 1.0), (0.25, 3.0, 0.01), (4.5, 0.1, 9.0), (100.0, 100.0, 100.0)):
        for variant in (1, 2):
            yield Case(f"construct scale {floats} variant {variant}", F_462410,
                       ctor_setup(random_source, keys, floats=floats, variant=variant),
                       receiver=lambda t: t["officer"], arguments=(lambda t: t["owner"],))
    yield Case("construct on a mirrored owner", F_462410, ctor_setup(random_source, keys, flip=True),
               receiver=lambda t: t["officer"], arguments=(lambda t: t["owner"],))
    yield Case("construct with a state frame count", F_462410, ctor_setup(random_source, keys, state_count=3),
               receiver=lambda t: t["officer"], arguments=(lambda t: t["owner"],))


# ------------------------------------------------------------------------------------------------
# 0x462350: dispatch on the state's event
def dispatch_setup(random_source, keys, event, *, change=False, reg=None):
    def setup(env):
        w = officer_world(env, random_source, keys=keys,
                          owner_words={8: 3, 0x40: 0, 0x4C: 300, 0x50: 400, 0x164: 0x1234, 0x190: 77},
                          state_words={0x64: 0, 0x68: 9})
        owner, state = w["owner"], w["state"]
        log = env.object(0x300, "dispatch-log", fill=0)
        vtable = env.object(0x80, "vtable", fill=0)
        existing = env.object(0x470, "existing-officer", words=words_of(random_source, 0x470 // 4))
        env.put(existing, vtable)
        env.put(existing + 0x10, state)
        salt = random_source.getrandbits(32)
        replacement = env.object(0x470, "replacement", words=words_of(random_source, 0x470 // 4))
        env.put(replacement, vtable)
        env.put(replacement + 0x10, state)

        def effect(offset):
            def run(e, call):
                recorder(log, 0x4000 + offset, salt ^ offset)(e, call)
                if change:
                    e.put(state + 0x18, replacement)
                return salt ^ offset
            return run

        for offset in (4, 8, 0xC, 0x10, 0x1C, 0x20):
            env.put(vtable + offset, env.stub(f"officer-{offset:x}", "thiscall", 1 if offset in (4, 8, 0xC) else 0, effect(offset)))
        env.put(state + 0x18, existing, event)
        script_rand(env, [9, 6, 3])
        env.put(G_VARIANT, 1)
        env.put(G_FLOATS[0], f32(1.0), f32(1.0), f32(1.0))
        env.put(G_TICKS, 5000)
        # Numeric-state lookup used by the generic handler is real game code over a CString table.
        text = cstring(env, "distinct-event-%x" % salt)
        record = env.object(12, "numeric-state-record", words=[text, salt ^ 0x9876, salt])
        env.put(0x5376A0, event, event, record, record, 12)
        return {"owner": owner, "state": state}
    return setup


# The specification declares 0x462350 with no stack arguments, but the function reads one (the owning record) at
# [esp+4]: the harness then refuses a case that passes it, and without it the original dereferences null.  These cases
# are written and were checked with the argument declared; flip the switch once the specification says argc 1.
DISPATCH_ARGUMENT_DECLARED = True


def dispatch_cases(random_source, keys):
    if not DISPATCH_ARGUMENT_DECLARED:
        return
    for event in (0x1D, 0x1E, 0x3E8, 0x3E9, 5, 0x1F, 0xFFFFFFFF):
        for change in (False, True):
            yield Case(f"event {event:#x} effects {change}", F_462350,
                       dispatch_setup(random_source, keys, event, change=change), arguments=(lambda t: t["owner"],))
    yield Case("event 0 constructs an officer", F_462350, dispatch_setup(random_source, keys, 0),
               arguments=(lambda t: t["owner"],))
    yield Case("event 0 constructs, nothing found", F_462350, dispatch_setup(random_source, keys, 0, change=True),
               arguments=(lambda t: t["owner"],))


# ------------------------------------------------------------------------------------------------
# 0x463120 and 0x4631e0: animations
def anim_officer_setup(random_source, keys, *, rands, sound_gate=None, global_object=None, owner_extra=None,
                       fields=None, idle=1, vtable_log=False, registry_key=None, ticks=None, player=True,
                       sequences=(True, True, True, True, True)):
    def setup(env):
        extra = {0x38: 0xFFFFFFFF if sound_gate is None else sound_gate, 0x190: random_source.randrange(1, 1 << 30),
                 0x164: 0x77, 0x40: 0}
        extra.update(owner_extra or {})
        w = officer_world(env, random_source, keys=keys, owner_words=extra, idle=idle, state_words={0x1C: 3})
        owner, state = w["owner"], w["state"]
        log = env.object(0x300, "officer-log", fill=0)
        vtable = env.object(0x80, "vtable", fill=0)
        for offset in (0x44, 0x48, 0x10, 0x4C):
            env.put(vtable + offset, env.stub(f"slot-{offset:x}", "thiscall", 0, recorder(log, offset, 5)))
        merged = {0x2FC: 0x20, 0x300: 0, 0x34C: animation(env, duration=31, name="pacing-animation"),
                  0x68: 0x11, 0x6C: 0x22, 0x98: 0x33, 0x9C: 0x44}
        merged.update(fields or {})
        officer = make_officer(env, random_source, w, vtable=vtable, fields=merged)
        for index, offset in enumerate((0x318, 0x31C, 0x320, 0x324, 0x328)):
            env.put(officer + offset, animation(env, duration=40 + 17 * index, name=f"idle-{index}") if sequences[index] else 0)
        env.put(officer + 0x44C, 0x1111)
        env.put(officer + 0x450, 0x2222, 0x3333)
        env.put(officer + 0x458, 100, 50)
        env.put(officer + 0x468, 100, 50)
        if global_object is not None:
            target = env.object(0x200, "sound-target", words=words_of(random_source, 0x80))
            env.put(target + 0x6C, env.object(0x80, "target-state", words=words_of(random_source, 0x20)) if global_object != "nostate" else 0)
            env.put(0x53C9AC, target)
            env.put(0x53C9A8, 1 if global_object == "busy" else 0)
        else:
            env.put(0x53C9AC, 0)
        env.put(G_TICKS, ticks if ticks is not None else 5000)
        env.put(G_STEP, random_source.randrange(1, 5))
        script_rand(env, rands)
        return {"officer": officer, "owner": owner, "state": state}
    return setup


def idle_cases(random_source, keys):
    gates = [(None, None), (0x123, None), (0x123, "nostate"), (0x123, "ok"), (0x123, "busy"), (0, "ok")]
    for rands in ((10, 4, 0), (10, 5, 1), (20, 0xFFFFFFFF, 3), (-3 & M32, 0x80000001, 2), (-3 & M32, 0xFFFFFFFE, 2),
                  (32, 7, 1), (33, 7, 1), (50, 7, 1), (99, 3, 0), (0x80000000, 0x80000000, 0)):
        gate, kind = random_source.choice(gates)
        yield Case(f"idle start rand {rands[0]:#x}/{rands[1]:#x} gate {gate} {kind}", F_463120,
                   anim_officer_setup(random_source, keys, rands=rands, sound_gate=gate, global_object=kind),
                   receiver=lambda t: t["officer"])
    for gate, kind in gates:
        yield Case(f"idle start sound gate {gate} {kind}", F_463120,
                   anim_officer_setup(random_source, keys, rands=(3, 5, 1), sound_gate=gate if gate is not None else 0x55,
                                      global_object=kind), receiver=lambda t: t["officer"])
    yield Case("idle start without the idle state registered", F_463120,
               anim_officer_setup(random_source, keys, rands=(60, 5, 1), idle=None), receiver=lambda t: t["officer"])
    yield Case("idle start without animations", F_463120,
               anim_officer_setup(random_source, keys, rands=(60, 5, 1), fields={0x318: 0},
                                  sequences=(False,) * 5), receiver=lambda t: t["officer"])


def update_cases(random_source, keys):
    for elapsed in (0, 99, 100, 101, 5000):
        for remainder in (0, 1, 2, 3, 4):
            if elapsed in (0, 99) and remainder:
                continue
            yield Case(f"update interval {elapsed} pick {remainder}", F_4631E0,
                       anim_officer_setup(random_source, keys, rands=(remainder + 5 * random_source.randrange(0, 1000), 90, 90),
                                          fields={0x184: 9, 0x458: 5000 - elapsed, 0x45C: 100}),
                       receiver=lambda t: t["officer"])
    for value in (0xFFFFFFFF, 0x80000001, 5 * 7 - 1 | 0x80000000, -2 & M32):
        yield Case(f"update with negative remainder source {value:#x}", F_4631E0,
                   anim_officer_setup(random_source, keys, rands=(value, 90, 90), fields={0x184: 9, 0x458: 1, 0x45C: 100}),
                   receiver=lambda t: t["officer"])
    yield Case("update picks a missing animation", F_4631E0,
               anim_officer_setup(random_source, keys, rands=(2, 90, 90), sequences=(True, True, False, True, True),
                                  fields={0x184: 9, 0x458: 1, 0x45C: 100}), receiver=lambda t: t["officer"])
    for state in (0, 1, 2, 3, 4, 5, 6, 7, 0x40, 0xFFFFFFFF):
        yield Case(f"update mode {state:#x} waiting", F_4631E0,
                   anim_officer_setup(random_source, keys, rands=(10, 5, 5), fields={0x184: state, 0x458: 4999, 0x45C: 100}),
                   receiver=lambda t: t["officer"])
    for state in (5, 6):
        for roll in (0, 19, 20, 21, 0xFFFFFFFB, 77):
            for slack in (-1, 0, 1):
                equal = random_source.choice((False, True))
                bits = random_source.choice((0, 4, 0xFFFFFFFF, 0xB))
                threshold = random_source.randrange(50, 400)
                same = {0x98: 0x70, 0x9C: 0x71, 0x68: 0x70, 0x6C: 0x71} if equal else {}
                yield Case(f"update mode {state} roll {roll:#x} slack {slack} bits {bits:#x} equal {equal}", F_4631E0,
                           anim_officer_setup(random_source, keys, rands=(roll, roll, roll),
                                              fields={0x184: state, 0x458: 4999, 0x45C: 100,
                                                      0x468: (5000 - threshold - slack) & M32, 0x46C: threshold,
                                                      0x2FC: 0x20, 0x300: bits, **same},
                                              owner_extra={0x40: random_source.choice((0, 2)), 0x118: 3, 0x120: 4, 0x128: 5, 0x130: 6}),
                           receiver=lambda t: t["officer"])
    for equal in (False, True):
        for flipped in (0, 2):
            same = {0x98: 0x70, 0x9C: 0x71, 0x68: 0x70, 0x6C: 0x71} if equal else {}
            yield Case(f"update mode 5 pacing flip equal {equal} owner flags {flipped}", F_4631E0,
                       anim_officer_setup(random_source, keys, rands=(3, 3, 3),
                                          fields={0x184: 5, 0x458: 4999, 0x45C: 100, 0x468: 1, 0x46C: 5, 0x2FC: 0x20, 0x300: 0, **same},
                                          owner_extra={0x40: flipped, 0x118: 3, 0x120: 4, 0x128: 5, 0x130: 6}),
                       receiver=lambda t: t["officer"])


# ------------------------------------------------------------------------------------------------
# 0x462ef0: state change then sound lookup
def reaction_setup(random_source, keys, *, player_state, hits, owner_flags=0x10, extra=None, bitword=0x200, bitsize=0x20,
                   limited=False):
    def setup(env):
        owner_words = {8: owner_flags, 0x40: 0, 0x164: 0x1357, 0x80: 0, 0x38: 0xFFFFFFFF}
        w = officer_world(env, random_source, keys=keys, owner_words=owner_words, state_words={0x1C: 3},
                          anim_hits={address for address in ANIM_KEYS if hits.get(address, False)}, null_hit=hits.get("null", False))
        owner, state = w["owner"], w["state"]
        log = env.object(0x300, "officer-log", fill=0)
        vtable = env.object(0x80, "vtable", fill=0)
        for offset in (0x44, 0x48, 0x10, 0x4C):
            env.put(vtable + offset, env.stub(f"slot-{offset:x}", "thiscall", 0, recorder(log, offset, 5)))
        fields = {0x20: 5, 0x184: 9, 0x440: 10, 0x444: 99999, 0x448: 0, 0x68: 0, 0x69: 0}
        fields.update(extra or {})
        officer = make_officer(env, random_source, w, vtable=vtable, fields=fields)
        set_bits(env, officer, bitsize, bitword)
        for index, offset in enumerate(range(0x210, 0x250, 4)):
            env.put(officer + offset, 0x1000 * (index + 1) + random_source.randrange(0x100))
        player = env.object(0x200, "player", words=words_of(random_source, 0x80))
        env.put(player + 0xCC, player_state)
        env.put(player + 0x4C, random_source.randrange(100, 400))
        env.put(G_PLAYER, player)
        env.put(G_MODE, 0x26B7)
        env.put(G_TICKS, 5000)
        env.put(G_SWITCH, random_source.choice((0, 1)))
        script_rand(env, [random_source.randrange(1 << 32) for _ in range(3)])
        name = env.object(8, "state-name", fill=0)
        return {"officer": officer, "owner": owner, "name": name}
    return setup


def reaction_cases(random_source, keys):
    for player_state in (5, 4, 6, 0):
        for hit_mode in ("none", "strike1", "strike", "both", "null"):
            hits = {"none": {}, "strike1": {0x529870: True}, "strike": {0x529808: True},
                    "both": {0x529870: True, 0x529808: True}, "null": {"null": True}}[hit_mode]
            yield Case(f"reaction player {player_state} lookups {hit_mode}", F_462EF0,
                       reaction_setup(random_source, keys, player_state=player_state, hits=hits),
                       receiver=lambda t: t["officer"], arguments=(lambda t: t["name"],))


# ------------------------------------------------------------------------------------------------
# 0x46a8d0: leave the game screen with a given transition
SHOW_CURSOR_SLOT, TIME_SLOT = 0x546D54, 0x546DF0


def transition_setup(random_source, *, cursor=(-1,), edge_checks=True, display_matches=True, palette=True,
                     shadow=False, player=None, tile_list=0, hud_bar=False, flip_flags=0, input_flag=0, overlay=False, mode=3, mode_fail=False):
    def setup(env):
        log = env.object(0x400, "transition-log", fill=0)
        env.put(SHOW_CURSOR_SLOT, env.stub("ShowCursor", "stdcall", 1, sequence(*cursor)))
        env.put(TIME_SLOT, env.stub("timeGetTime", "stdcall", 0,
                                     lambda e, call: 1000 + 70 * e.calls_so_far(call.function)))
        install_imports(env)

        def iface(name, slots):
            vt = env.object(0x80, name + "-vtable", fill=0)
            for offset, (convention, argc, result) in slots.items():
                env.put(vt + offset, env.stub(f"{name}-{offset:x}", convention, argc, recorder(log, (hash(name) & 0xF00) + offset, result)))
            holder = env.object(0x20, name, words=words_of(random_source, 8))
            env.put(holder, vt)
            return holder

        # Surfaces: Q is the primary, K the secondary; both are wrappers around a DirectDraw-like interface.
        surface_iface = iface("surface", {0x14: ("stdcall", 6, 0), 0x2C: ("stdcall", 3, 0)})
        primary = env.object(0x40, "primary", words=words_of(random_source, 16))
        env.put(primary + 8, surface_iface)
        secondary = env.object(0x40, "secondary", words=words_of(random_source, 16))
        env.put(secondary + 8, surface_iface)
        z1 = env.object(0x40, "buffer-a", words=words_of(random_source, 16))
        env.put(z1 + 0x10, 640, 480)
        env.put(z1 + 0x2C, primary)
        z2 = env.object(0x40, "buffer-b", words=words_of(random_source, 16))
        env.put(z2 + 0x10, 640, 480)
        env.put(z2 + 0x2C, secondary)
        graphics = env.object(0x40, "graphics", words=words_of(random_source, 16))
        env.put(graphics + 0x10, z1, z2)
        flags = env.object(0x40, "graphics-flags", words=words_of(random_source, 16))
        env.put(flags + 0x34, flip_flags)
        env.put(graphics + 0xC, flags)

        # The display.
        display_table = env.object(0x80, "display-vtable", fill=0)
        env.put(display_table + 0xC, env.stub("display-ready", "thiscall", 0, recorder(log, 0xD0C, 0)))
        manager = env.object(0x100, "tile-manager", words=words_of(random_source, 0x40))
        env.put(manager + 8, tile_list)
        env.put(manager + 0x3C, 0)
        env.put(manager + 0x60, M32)
        if overlay:
            env.put(manager + 0x5C, env.object(0x100, "overlay", fill=0))
        else:
            env.put(manager + 0x5C, 0)
        frame = env.object(0x40, "frame", words=words_of(random_source, 16))
        env.put(frame + 4, graphics)
        env.put(frame + 0x24, manager)
        env.put(frame + 0x18, env.object(0x80, "frame-context", fill=0))
        display = env.object(0x140, "display", words=words_of(random_source, 0x50))
        env.put(display, display_table)
        env.put(display + 0x30, frame)
        env.put(display + 0x68, 4)
        env.put(display + 0x7C, 640, 480 if display_matches else 400)
        mode_table = env.object(0x40, "mode-vtable", fill=0)
        env.put(mode_table + 0x10, env.stub("display-mode", "thiscall", 0, recorder(log, 0xD10, mode)))
        mode_holder = env.object(0x20, "mode-holder", words=words_of(random_source, 8))
        env.put(mode_holder, mode_table)
        env.put(display + 0x2C, mode_holder)
        notify = iface("notify", {0x1C: ("thiscall", 2, 0)})
        env.put(display + 8, notify)
        if mode_fail:
            fail_table = env.object(0x80, "surface-vtable", fill=0)
            env.put(fail_table + 0x28, env.stub("set-mode", "thiscall", 3, recorder(log, 0x528, 0)))
            env.put(z1, fail_table)
            env.put(z1 + 0x10, 800, 600)
        env.put(0x537268, 0)
        hud = env.object(0x80, "hud", words=words_of(random_source, 0x20)) if hud_bar else 0
        if hud_bar:
            env.put(hud + 0x28, 0)  # no resource table: the lookup returns at once
        env.put(display + 0x14, 1 if hud_bar else 0)
        env.put(display + 0x50, hud)

        # The game record.
        game = env.object(0x80, "game", words=words_of(random_source, 0x20))
        scene_iface = iface("scene", {0x24: ("thiscall", 1, 0), 0x28: ("thiscall", 1, 0)})
        cursor_iface = iface("pointer", {0x34: ("thiscall", 2, 0)})
        env.put(game + 4, graphics)
        env.put(game + 8, scene_iface)
        env.put(game + 0xC, cursor_iface)
        env.put(game + 0x24, manager)
        grandparent = env.object(0x40, "tile-owner", words=words_of(random_source, 16))
        env.put(game + 0x18, grandparent)

        # The palette holder.
        palette_iface = iface("palette", {0x10: ("stdcall", 5, 0), 0x18: ("stdcall", 5, 0)})
        pal = env.object(0x40, "palette", words=words_of(random_source, 16))
        env.put(pal + 4, palette_iface)
        env.put(pal + 0xC, env.object(0x400, "palette-entries", words=words_of(random_source, 0x100)))
        env.put(pal + 0x10, env.object(0x400, "palette-copy", words=words_of(random_source, 0x100)) if shadow else 0)
        env.put(pal + 0x34, 0)
        holder_table = env.object(0x80, "holder-vtable", fill=0)
        env.put(holder_table + 0x34, env.stub("holder-34", "thiscall", 0, recorder(log, 0xE34, 0)))
        env.put(holder_table + 0x10, env.stub("holder-10", "thiscall", 0, recorder(log, 0xE10, 3)))
        holder = env.object(0x40, "holder", words=words_of(random_source, 16))
        env.put(holder, holder_table)
        env.put(holder + 0x10, pal)

        record = env.object(0x780, "screen", words=words_of(random_source, 0x1E0))
        env.put(record + 4, display)
        env.put(record + 0xC, game)
        env.put(record + 0x10, 0)
        env.put(record + 0x2C, holder if palette else 0)
        env.put(record + 0x760, random_source.randrange(1, 1 << 30))

        # Input records reset by the leave transitions.
        pad = env.object(0x240, "pad-device", words=words_of(random_source, 0x90))
        env.put(pad + 0x1CC, input_flag)
        pad_owner = env.object(0x80, "pad-owner", words=words_of(random_source, 0x20))
        env.put(pad_owner, pad)
        env.put(0x537204, pad_owner)
        keys = env.object(0x240, "key-device", words=words_of(random_source, 0x90))
        env.put(keys + 0x1CC, input_flag)
        env.put(0x537200, keys)
        if player is None:
            env.put(G_PLAYER, 0)
        else:
            target = env.object(0x80, "player-attachment", words=words_of(random_source, 0x20))
            state = env.object(0x80, "player-state", words=words_of(random_source, 0x20))
            env.put(state + 0x14, target if player else 0)
            holder_p = env.object(0x100, "player", words=words_of(random_source, 0x40))
            env.put(holder_p + 0x6C, state)
            env.put(G_PLAYER, holder_p)
        env.put(G_TICKS, random_source.randrange(1, 1 << 30))
        return {"record": record}
    return setup


def transition_cases(random_source):
    for kind in (0xA, 0xB, 0xC, 9, 0, 1, 8, 0xD, 0x40, 0xFFFFFFFF):
        yield Case(f"transition {kind:#x}", F_46A8D0, transition_setup(random_source, shadow=kind == 9),
                   receiver=lambda t: t["record"], arguments=(kind,))
    for kind in (0xB, 0xC, 9, 1):
        shadow = kind == 9
        for cursor in ((3, 2, -1), (0, 5, 6, -4), (-2,), (-1, 3, 2, -1), (-3, 0, 0, 0, -1)):
            yield Case(f"transition {kind:#x} cursor script {cursor}", F_46A8D0,
                       transition_setup(random_source, cursor=cursor, shadow=shadow), receiver=lambda t: t["record"],
                       arguments=(kind,))
        if kind in (0xB, 0xC, 9):
            yield Case(f"transition {kind:#x} without palette", F_46A8D0,
                       transition_setup(random_source, palette=False), receiver=lambda t: t["record"], arguments=(kind,))
        yield Case(f"transition {kind:#x} flipped graphics and listed tiles", F_46A8D0,
                   transition_setup(random_source, flip_flags=2, tile_list=1, shadow=shadow),
                   receiver=lambda t: t["record"], arguments=(kind,))
        yield Case(f"transition {kind:#x} with palette copy and player", F_46A8D0,
                   transition_setup(random_source, shadow=True, player=True), receiver=lambda t: t["record"], arguments=(kind,))
        yield Case(f"transition {kind:#x} player without attachment", F_46A8D0,
                   transition_setup(random_source, player=False, shadow=shadow), receiver=lambda t: t["record"], arguments=(kind,))
        yield Case(f"transition {kind:#x} with a hud", F_46A8D0, transition_setup(random_source, hud_bar=True, shadow=shadow),
                   receiver=lambda t: t["record"], arguments=(kind,))
        yield Case(f"transition {kind:#x} with an overlay", F_46A8D0,
                   transition_setup(random_source, overlay=True, shadow=shadow, player=True),
                   receiver=lambda t: t["record"], arguments=(kind,))
        if kind != 0xB and kind != 0xC:
            yield Case(f"transition {kind:#x} display mode cannot change", F_46A8D0,
                       transition_setup(random_source, display_matches=False, mode_fail=True, shadow=shadow),
                       receiver=lambda t: t["record"], arguments=(kind,))
            for mode in (3, 4, 0):
                yield Case(f"transition {kind:#x} display needs a mode change ({mode})", F_46A8D0,
                           transition_setup(random_source, display_matches=False, mode=mode, shadow=shadow),
                           receiver=lambda t: t["record"], arguments=(kind,))


# ------------------------------------------------------------------------------------------------
# 0x46c2c0: the diagnostic overlay text (drawing needs GDI imports with no stand-in, so the device context stays empty)
G_OVERLAY, G_SPARE_TICKS = 0x537264, 0x53720C
LSTRLEN_SLOT, INTERLOCK_DEC_SLOT, INTERLOCK_INC_SLOT = 0x5469E4, 0x5469E8, 0x5469EC


def lstrlen_effect(env, call):
    return len(env.cstr(call.arguments[0], 4096))


def decrement_effect(env, call):
    value = (env.get(call.arguments[0]) - 1) & M32
    env.put(call.arguments[0], value)
    return value


def increment_effect(env, call):
    value = (env.get(call.arguments[0]) + 1) & M32
    env.put(call.arguments[0], value)
    return value


ORIGINAL_WORD_34 = 0x40AF20  # original function: returns the word at [ECX+0x34] and leaves its stack arguments in place


def receiver_kind(log, kind, holder):
    """Slot +0x10 (thiscall, no arguments): answers `kind` only for the overlay itself; any other receiver gets a
    different kind (kind ^ 7 swaps 3 and 4) and the recorded state shows the receiver."""
    def effect(env, call):
        recorder(log, 0x10, 0)(env, call)
        env.put(log + 0x3F0, call.receiver ^ 0x10)
        return kind if call.receiver == holder[0] else kind ^ 7
    return effect


def receiver_draw(log, holder):
    """Slot +0x64 (thiscall, one argument): publishes a word mixing the receiver and the argument, plus whether the
    receiver is the overlay."""
    def effect(env, call):
        recorder(log, 0x64, 0)(env, call)
        env.put(log + 0x3F4, (call.receiver ^ call.arguments[0]) & 0xFFFFFFFF)
        env.put(log + 0x3F8, 1 if call.receiver == holder[0] else 0)
        return call.receiver
    return effect


def overlay_setup(random_source, flags, *, kind=3, count=None, player=True, text_imports=False, timer_busy=False,
                  timer_count=0, timer_mode=0, gdi=None, rect=(0, 0, 0)):
    def setup(env):
        log = env.object(0x400, "overlay-log", fill=0)
        holder = [0]
        if text_imports:
            env.put(LSTRLEN_SLOT, env.stub("lstrlenA", "stdcall", 1, lstrlen_effect))
            env.put(INTERLOCK_DEC_SLOT, env.stub("InterlockedDecrement", "stdcall", 1, decrement_effect))
            env.put(INTERLOCK_INC_SLOT, env.stub("InterlockedIncrement", "stdcall", 1, increment_effect))
        surface_table = env.object(0x80, "surface-vtable", fill=0)
        def get_dc(e, call):
            recorder(log, 0x44, 0)(e, call)
            if gdi is not None:
                e.put(call.arguments[1], gdi)  # the handle goes out through the pointer argument
            return 0
        env.put(surface_table + 0x44, env.stub("get-dc", "stdcall", 2, get_dc))
        if gdi is not None:
            # Drawing goes through GDI import-table slots: stand-ins publish the handle and the scalar arguments.
            def scalars(tag, picks):
                def effect(e, call):
                    count = e.get(log)
                    row = log + 4 + (count % 24) * 0x20
                    e.put(row, tag, *[call.arguments[i] for i in picks])  # scalar arguments only
                    e.put(log, count + 1)
                    return 1
                return effect
            env.put(0x546888, env.stub("SetBkMode", "stdcall", 2, scalars(0xB0, (0, 1))))
            env.put(0x546880, env.stub("SetTextColor", "stdcall", 2, scalars(0xC0, (0, 1))))
            env.put(0x546D30, env.stub("DrawTextA", "stdcall", 5, scalars(0xD0, (0, 2, 4))))
            env.put(0x546890, env.stub("TextOutA", "stdcall", 5, scalars(0xE0, (0, 1, 2, 4))))
            env.put(0x5370C8, rect[0])
            env.put(0x5370D0, rect[1])
            env.put(0x5370D4, rect[2])
        env.put(surface_table + 0x68, env.stub("release-dc", "stdcall", 2, recorder(log, 0x68, 0)))
        surface = env.object(0x20, "surface", words=words_of(random_source, 8))
        env.put(surface, surface_table)
        wrapper = env.object(0x40, "surface-wrapper", words=words_of(random_source, 16))
        env.put(wrapper + 8, surface)
        wrapper_owner = env.object(0x40, "wrapper-owner", words=words_of(random_source, 16))
        env.put(wrapper_owner + 0x2C, wrapper)
        graphics = env.object(0x40, "graphics", words=words_of(random_source, 16))
        env.put(graphics + 0x14, wrapper_owner)
        scene = env.object(0x40, "scene", words=words_of(random_source, 16))
        env.put(scene + 0x1C, random_source.randrange(1, 100000))
        game = env.object(0x40, "game", words=words_of(random_source, 16))
        env.put(game + 4, graphics)
        env.put(game + 8, scene)
        timer = env.object(0x40, "timer", words=words_of(random_source, 16))
        env.put(timer + 0xC, timer_mode)
        env.put(timer + 0x20, 3)
        env.put(timer + 0x24, 1 << 20)
        env.put(timer + 0x28, 1 << 20)
        env.put(timer + 0x2C, 4)
        env.put(timer + 0x30, 1 if timer_busy else 0)
        clock = env.object(0x60, "clock", words=words_of(random_source, 24))
        env.put(clock + 0x18, random_source.randrange(1, 1000))
        env.put(clock + 0x30, env.object(0x40, "clock-detail", words=words_of(random_source, 16)))
        env.put(env.get(clock + 0x30) + 8, scene)
        env.put(clock + 0x4C, timer)
        vtable = env.object(0x80, "overlay-vtable", fill=0)
        env.put(vtable + 0x10, env.stub("kind", "thiscall", 0, receiver_kind(log, kind, holder)))
        env.put(vtable + 0x50, ORIGINAL_WORD_34)
        env.put(vtable + 0x64, env.stub("draw", "thiscall", 1, receiver_draw(log, holder)))
        overlay = env.object(0x180, "overlay", words=words_of(random_source, 0x60))
        holder[0] = overlay
        env.put(overlay + 0x34, count if count is not None else random_source.randrange(1, 1 << 20))
        env.put(overlay, vtable)
        env.put(overlay + 4, clock)
        env.put(overlay + 0xC, game)
        env.put(overlay + 0x14C, random_source.randrange(1, 1 << 30))
        env.put(G_OVERLAY, flags)
        env.put(G_SPARE_TICKS, random_source.randrange(1, 5000))
        env.put(G_TICKS, random_source.randrange(1, 1 << 30))
        if player:
            env.put(G_PLAYER, env.object(0x100, "player", words=words_of(random_source, 0x40)))
        else:
            env.put(G_PLAYER, 0)
        return {"overlay": overlay}
    return setup


def overlay_cases(random_source):
    for flags in (0x20, 0xFF, 0xE0, 0x30, 0x2F):
        yield Case(f"overlay suppressed {flags:#x}", F_46C2C0, overlay_setup(random_source, flags),
                   receiver=lambda t: t["overlay"])
    for count in (1, 7, 12345, 0x7FFFFFFF):
        yield Case(f"overlay racers text count {count:#x}", F_46C2C0, overlay_setup(random_source, 2, count=count),
                   receiver=lambda t: t["overlay"])
    for flags in (0, 1, 2, 4, 0x10, 0x40, 0x13, 0x45, 0x57, 0x0F):
        for kind in (4, 3):
            yield Case(f"overlay text {flags:#x} kind {kind}", F_46C2C0, overlay_setup(random_source, flags, kind=kind),
                       receiver=lambda t: t["overlay"])
    for flags in (0x01, 0x10, 0x41):
        yield Case(f"overlay text {flags:#x} without a player", F_46C2C0, overlay_setup(random_source, flags, player=False),
                   receiver=lambda t: t["overlay"])
    for busy, mode in ((False, 0), (True, 0), (True, 2), (False, 5)):
        yield Case(f"overlay idle clock busy {busy} mode {mode}", F_46C2C0,
                   overlay_setup(random_source, 0, kind=2, timer_busy=busy, timer_mode=mode), receiver=lambda t: t["overlay"])
    for flags in (0, 1, 2, 0x10, 0x45, 0x0F):
        for rect in ((0, 100, 80), (7, 120, 200), (-5, 30, 15), (0x7FFFFFFF, 1, 2)):
            yield Case(f"overlay drawn {flags:#x} rect {rect}", F_46C2C0,
                       overlay_setup(random_source, flags, kind=4, gdi=random_source.randrange(1, 1 << 30), rect=rect),
                       receiver=lambda t: t["overlay"])
    for kind in (4, 3):
        yield Case(f"overlay drawn nothing to say kind {kind}", F_46C2C0,
                   overlay_setup(random_source, 0, kind=kind, gdi=0x4D2, rect=(3, 4, 5), timer_mode=1), receiver=lambda t: t["overlay"])
    for flags in (0x80, 0x81, 0xC0 & ~0x20, 0x9F & ~0x20):
        yield Case(f"overlay clock text {flags:#x}", F_46C2C0, overlay_setup(random_source, flags, text_imports=True),
                   receiver=lambda t: t["overlay"])


# ------------------------------------------------------------------------------------------------
# Store-order cases: prior contents that a dropped, shifted or reordered store would leave behind
def distinct_word(random_source, avoid=()):
    while True:
        value = random_source.randrange(0x100, 1 << 32)
        if value not in avoid and value < 0xFFFFFF00:
            return value


def primed_ctor_setup(random_source, program_keys, *, scramble_rect=False, **options):
    """A construction whose rectangle service plants fresh non-zero priors right before the stores that follow it.

    The base constructor clears the record, so priors set up front never survive to the stores under test.  The
    rectangle stand-in runs between the base constructor and each store, so it writes them there.
    """
    inner = ctor_setup(random_source, program_keys, **options)
    constants = (0xFFFFFFF6, 0xFFFFFFF1, 0xA, 0xFFFFFFD3, 0xFFFFFFEC, 0x14, 0x64, 0x28, 0x32)
    copy_priors = [distinct_word(random_source) for _ in range(4)]
    block_priors = [distinct_word(random_source, constants) for _ in range(0x2EC // 4 - 0x28C // 4 + 1)]
    late_priors = [distinct_word(random_source, constants) for _ in range(len(block_priors))]
    rect_words = [distinct_word(random_source) for _ in range(4)]

    def setup(env):
        tokens = inner(env)
        officer = tokens["officer"]

        def effect(env, call):
            rect, words = call.arguments[0], list(call.arguments[1:])
            if rect == officer + 0x230 and scramble_rect:
                words = rect_words
            env.put(rect, *words)
            if rect == officer + 0x240:
                env.put(officer + 0x220, *copy_priors)
            if rect == officer + 0x250:
                env.put(officer + 0x28C, *late_priors)
            if rect == officer + 0x260:
                env.put(officer + 0x28C, *block_priors)
            return 1

        env.put(SET_RECT_SLOT, env.stub("SetRect", "stdcall", 5, effect))
        return tokens
    return setup


def primed_ctor_cases(random_source, keys):
    for scramble in (False, True, True):
        for rands in ((7, 5, 8), (0x80000003, 0x7FFFFFFF, 6)):
            yield Case(f"construct with prior record words, scrambled rectangle {scramble}", F_462410,
                       primed_ctor_setup(random_source, keys, scramble_rect=scramble, rands=rands),
                       receiver=lambda t: t["officer"], arguments=(lambda t: t["owner"],))
    yield Case("construct with prior record words, mirrored owner, nothing found", F_462410,
               primed_ctor_setup(random_source, keys, flip=True, anim_hits=set(), sound_hits=set(), sprite_hit=False,
                                 null_hit=False, scramble_rect=True),
               receiver=lambda t: t["officer"], arguments=(lambda t: t["owner"],))
    for variant in (1, 2):
        yield Case(f"construct with prior record words, variant {variant}", F_462410,
                   primed_ctor_setup(random_source, keys, variant=variant, floats=(2.0, 0.5, 3.0)),
                   receiver=lambda t: t["officer"], arguments=(lambda t: t["owner"],))


def sound_lookup_cases(random_source, keys):
    """The three sound lookups share one scratch slot (the incoming argument), so each must clear it before the call."""
    for first_roll in (10, 60):
        first = SOUND_KEYS[0] if first_roll < 50 else SOUND_KEYS[1]
        for mask in range(8):
            hits = {key for bit, key in zip((1, 2, 4), (first, SOUND_KEYS[2], SOUND_KEYS[3])) if mask & bit}
            yield Case(f"construct sound lookups {mask:03b} first roll {first_roll}", F_462410,
                       ctor_setup(random_source, keys, sound_hits=hits, rands=(first_roll, 9, 40)),
                       receiver=lambda t: t["officer"], arguments=(lambda t: t["owner"],))


OVERLAP_SHIFT = 0x5C  # the record starts this far into the owner: owner + 0x188 + 8 is then record + 0x134


def overlapped_animation_setup(random_source, keys, *, rands, fields=None, sequences=(True, True, True, True, True),
                               idle=1, prior=None, tail=None):
    """The record sits inside its owner's memory so that the animator's own fields alias the record's +0x134.

    The animator is at owner + 0x188 and 0x4c8220 stores the sequence at animator + 8 = owner + 0x190, which is also
    record + 0x134.  The original reads that word, stores it back into record + 0x134, then lets 0x4c8220 overwrite
    it, so the order of the store and the call decides the final word.
    """
    inner = anim_officer_setup(random_source, keys, rands=rands, fields=fields, sequences=sequences, idle=idle)
    old_frame = prior if prior is not None else distinct_word(random_source)

    def setup(env):
        tokens = inner(env)
        owner, officer = tokens["owner"], tokens["officer"]
        block = env.object(0x800, "owner-with-record", fill=0)
        env.write(block, env.read(owner, 0x200))
        record = block + OVERLAP_SHIFT
        env.write(record, env.read(officer, 0x470))
        env.put(record + 0xC, block)
        env.put(record + 0x128, block, block, block)
        env.put(block + 0x164, 0x77)
        env.put(block + 0x190, old_frame)
        for offset, value in (tail or {}).items():
            env.put(record + offset, value)
        return {"officer": record, "owner": block, "state": tokens["state"]}
    return setup


def overlapped_animation_cases(random_source, keys):
    for rands in ((10, 4, 0), (60, 5, 1), (20, 0xFFFFFFFF, 3)):
        yield Case(f"idle start inside the owner, rand {rands[0]:#x}", F_463120,
                   overlapped_animation_setup(random_source, keys, rands=rands), receiver=lambda t: t["officer"])
    yield Case("idle start inside the owner, no animations", F_463120,
               overlapped_animation_setup(random_source, keys, rands=(60, 5, 1), sequences=(False,) * 5),
               receiver=lambda t: t["officer"])
    for remainder in (0, 1, 2, 3, 4):
        yield Case(f"update inside the owner, pick {remainder}", F_4631E0,
                   overlapped_animation_setup(random_source, keys, rands=(remainder + 5 * random_source.randrange(0, 1000), 90, 90),
                                              fields={0x184: 9, 0x458: 1, 0x45C: 100}),
                   receiver=lambda t: t["officer"])
    yield Case("update inside the owner, missing animation", F_4631E0,
               overlapped_animation_setup(random_source, keys, rands=(2, 90, 90), sequences=(True, True, False, True, True),
                                          fields={0x184: 9, 0x458: 1, 0x45C: 100}),
               receiver=lambda t: t["officer"])


# ------------------------------------------------------------------------------------------------
def cases(random_source):
    program = claw()  # the loader verifies the reference hash before any read
    keys = {}
    for address in ANIM_KEYS + SOUND_KEYS + (SPRITE_KEY, NULL_KEY, IDLE_KEY, PACING_KEY):
        keys[address] = text_at(program, address)
    yield from vslot_cases(random_source)
    yield from rand_cases(random_source)
    yield from variant_cases(random_source)
    yield from first_variant_cases(random_source)
    yield from handler_table_cases(random_source)
    yield from wrapped_table_cases(random_source)
    yield from idle_cases(random_source, keys)
    yield from update_cases(random_source, keys)
    yield from reaction_cases(random_source, keys)
    yield from ctor_cases(random_source, keys)
    yield from dispatch_cases(random_source, keys)
    yield from transition_cases(random_source)
    yield from overlay_cases(random_source)
    yield from primed_ctor_cases(random_source, keys)
    yield from sound_lookup_cases(random_source, keys)
    yield from overlapped_animation_cases(random_source, keys)
