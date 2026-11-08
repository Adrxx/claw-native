"""Cases for cheat_command_toggles: In-game cheat command helpers: toggle message, power-up grant, layer toggles, fall speed."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

MESSAGE = 0x42AF90
GRANT = 0x41FC00
TOGGLE_NTH = 0x42A750
TOGGLE_FIXED = 0x42A7B0
TOGGLE_FIRST = 0x42A7F0
SET_FIVE = 0x440DE0
SET_ONE = 0x440E00

LSTRLEN, DECREMENT, INCREMENT = 0x5469E4, 0x5469E8, 0x5469EC
BUFFER = 0x5370D8
FALL = (0x5262B0, 0x5262B4, 0x5262B8)
GAME = 0x537E88
CURRENT_SCREEN = 0x5371FC
SUSPEND = 0x53C9C0
STATE_ID = 0x534EAC
STATE_TIME = 0x534EA8


# ---------------------------------------------------------------- fall speed

def fall_setup(values):
    def setup(env):
        for address, value in zip(FALL, values):
            env.put(address, value)
        return {}
    return setup


def fall_cases(random_source):
    starts = [(0, 0, 0), (0x3F800000, 0x40A00000, 0xDEADBEEF), (0x11111111, 0x22222222, 0x33333333)]
    for _ in range(3):
        starts.append(tuple(random_source.getrandbits(32) for _ in range(3)))
    for index, start in enumerate(starts):
        yield Case(f"fall speed five from {index}", SET_FIVE, fall_setup(start))
        yield Case(f"fall speed one from {index}", SET_ONE, fall_setup(start))


# ------------------------------------------------------- layer toggle helpers

def layer_object(env, *, virtual=1, owner=True, inner=True, count=0, items=None, slot_count=None,
                 fixed=None, flags=None, change=None):
    """A game object whose vtable slot 3 returns `virtual`; owner at +0x30, its table at +0x24.

    items: list of flag words (None for a null entry) for the array at inner+0x38.
    fixed: flag word (or None) for the single item at inner+0x5c.
    change: optional function(env, tokens) run inside the virtual call (re-read check).
    """
    tokens = {}
    this = env.object(0x80, "this", fill=0xA5)
    vtable = env.object(0x40, "vtable", fill=0)
    record = env.object(16, "virtual-record", fill=0)
    tokens.update(this=this, record=record, vtable=vtable)
    outer = env.object(0x60, "owner", fill=0x5A) if owner else 0
    table = env.object(0x80, "inner", fill=0x3C) if inner else 0
    tokens.update(outer=outer, table=table)
    item_ptrs = []
    if items is not None and table:
        capacity = max(count, 0) + 3
        array = env.object(4 * capacity, "array", fill=0)
        for index in range(capacity):
            if index < len(items) and items[index] is not None:
                item = env.object(0x20, f"item{index}", fill=0xC3)
                env.put(item + 8, items[index])
                env.put(item, 0x1000 + index, 0x2000 + index)
                env.put(array + 4 * index, item)
                item_ptrs.append(item)
            else:
                env.put(array + 4 * index, 0)
                item_ptrs.append(0)
        tokens["array"] = array
        env.put(table + 0x38, array)
    elif table:
        env.put(table + 0x38, 0xFFFFFFF0)
    tokens["items"] = item_ptrs
    if table:
        env.put(table + 0x3C, count & 0xFFFFFFFF)
        if fixed is not None:
            item = env.object(0x20, "fixed", fill=0x99)
            env.put(item + 8, fixed)
            env.put(table + 0x5C, item)
            tokens["fixed"] = item
        else:
            env.put(table + 0x5C, 0)
    if outer:
        env.put(outer + 0x24, table)
    env.put(this + 0x30, outer)

    def virtual_call(env, call):
        env.put(record, call.receiver, env.calls_so_far(call.function), env.get(this + 0x30))
        if change is not None:
            change(env, tokens)
        return virtual

    env.put(this, vtable)
    env.put(vtable + 0x0C, env.stub("slot3", "thiscall", 0, virtual_call))
    env.put(vtable + 0x08, env.stub("slot2-decoy", "thiscall", 0, returns(0)))
    env.put(vtable + 0x10, env.stub("slot4-decoy", "thiscall", 0, returns(0)))
    return tokens


def toggle(label, function, **options):
    def setup(env):
        return layer_object(env, **options)
    return Case(label, function, setup, receiver=lambda tokens: tokens["this"])


def nth_cases(random_source):
    flag_values = (0, 1, 2, 3, 4, 6, 0x10, 0x80000002, 0xFFFFFFFD, 0xFFFFFFFF)
    for count in (-3, -1, 0, 1, 2, 3, 4, 5, 6, 9):
        entries = [random_source.getrandbits(32) & ~1 for _ in range(max(count, 0))]
        yield toggle(f"nth count {count} even flags", TOGGLE_NTH, count=count, items=entries)
        yield toggle(f"nth count {count} odd flags", TOGGLE_NTH,
                     count=count, items=[(random_source.getrandbits(32) | 1) for _ in range(max(count, 0))])
        yield toggle(f"nth count {count} mixed flags", TOGGLE_NTH,
                     count=count, items=[(0x40 << index) | (index & 1) for index in range(max(count, 0))])
        yield toggle(f"nth count {count} null entries", TOGGLE_NTH,
                     count=count, items=[None] * max(count, 0))
    for flags in flag_values:
        for count in (1, 3, 4, 5):
            slots = [0x100 * (index + 1) | 4 for index in range(count)]
            # the item the function selects is index (count==4 ? 3 : count) - 1
            chosen = (3 if count == 4 else count) - 1
            slots[chosen] = flags
            yield toggle(f"nth chosen flags {flags:#x} count {count}", TOGGLE_NTH, count=count, items=slots)
    # count 4 maps to index 2, not 3
    yield toggle("nth count four skips last", TOGGLE_NTH, count=4, items=[0x10, 0x20, 0x40, 0x80])
    yield toggle("nth count four selected entry null", TOGGLE_NTH, count=4, items=[0x10, 0x20, None, 0x80])
    yield toggle("nth count four last entry only", TOGGLE_NTH, count=4, items=[None, None, None, 0x80])
    yield toggle("nth count three first entry only", TOGGLE_NTH, count=3, items=[0x10, None, None])
    yield toggle("nth count five fourth entry null", TOGGLE_NTH, count=5, items=[1, 2, 4, None, 8])
    for case in chain_cases(TOGGLE_NTH, "nth", dict(count=3, items=[0x10, 0x20, 0x40])):
        yield case
    yield toggle("nth array pointer unreadable when count zero", TOGGLE_NTH, count=0, items=None)
    yield toggle("nth array pointer unreadable when count negative", TOGGLE_NTH, count=-5, items=None)


def chain_cases(function, prefix, base):
    """Null links of the chain and virtual-call result values."""
    base = dict(base)
    cases = []
    for value in (0, 1, 2, 0x80000000, 0xFFFFFFFF, 0x12345678):
        cases.append(toggle(f"{prefix} virtual returns {value:#x}", function, virtual=value, **base))
    cases.append(toggle(f"{prefix} no owner", function, owner=False, **base))
    cases.append(toggle(f"{prefix} no inner table", function, inner=False, **base))
    cases.append(toggle(f"{prefix} virtual zero ignores chain", function, virtual=0, owner=False, inner=False, **base))

    def drop_owner(env, tokens):
        env.put(tokens["this"] + 0x30, 0)

    cases.append(toggle(f"{prefix} owner cleared by virtual call", function, change=drop_owner, **base))

    def adopt_second(env, tokens):
        other_table = env.object(0x80, "late-inner", fill=0x11)
        late = env.object(0x20, "late-item", fill=0x22)
        env.put(late + 8, 0x44)
        array = env.object(16, "late-array", fill=0)
        env.put(array, late, late, late, late)
        env.put(other_table + 0x38, array)
        env.put(other_table + 0x3C, 4)
        env.put(other_table + 0x5C, late)
        other_owner = env.object(0x60, "late-owner", fill=0)
        env.put(other_owner + 0x24, other_table)
        env.put(tokens["this"] + 0x30, other_owner)

    def late_setup(env):
        built = layer_object(env, owner=False, change=adopt_second, **base)
        return built

    cases.append(Case(f"{prefix} owner appears during virtual call", function, late_setup,
                      receiver=lambda tokens: tokens["this"]))
    return cases


def fixed_cases(random_source):
    for flags in (0, 1, 2, 3, 0x10, 0x80000000, 0xFFFFFFFF, 0xFFFFFFFE, 0x7FFFFFFD):
        yield toggle(f"fixed flags {flags:#x}", TOGGLE_FIXED, fixed=flags, count=2, items=[0x10, 0x20])
    for _ in range(4):
        yield toggle("fixed random flags", TOGGLE_FIXED, fixed=random_source.getrandbits(32), count=1, items=[7])
    yield toggle("fixed item absent", TOGGLE_FIXED, fixed=None, count=2, items=[0x10, 0x20])
    yield toggle("fixed uses +0x5c not array", TOGGLE_FIXED, fixed=0x100, count=3, items=[0x1, 0x2, 0x4])
    yield toggle("fixed no array at all", TOGGLE_FIXED, fixed=0x20, count=0, items=None)
    for case in chain_cases(TOGGLE_FIXED, "fixed", dict(fixed=0x24, count=1, items=[0x10])):
        yield case


def first_cases(random_source):
    for count in (-1, 0, 1, 2, 5):
        yield toggle(f"first count {count} even", TOGGLE_FIRST, count=count,
                     items=[0x10 * (index + 1) for index in range(max(count, 0))])
        yield toggle(f"first count {count} first odd", TOGGLE_FIRST, count=count,
                     items=[0x11] + [0x20 * (index + 1) for index in range(1, max(count, 0))])
        yield toggle(f"first count {count} first null", TOGGLE_FIRST, count=count,
                     items=[None] + [0x20 * (index + 1) for index in range(1, max(count, 0))])
    for flags in (0, 1, 2, 3, 0x80000000, 0xFFFFFFFE, 0xFFFFFFFF):
        yield toggle(f"first flags {flags:#x}", TOGGLE_FIRST, count=3, items=[flags, 0x40, 0x80])
    for _ in range(4):
        yield toggle("first random flags", TOGGLE_FIRST, count=2,
                     items=[random_source.getrandbits(32), random_source.getrandbits(32) | 1])
    yield toggle("first array unreadable when count zero", TOGGLE_FIRST, count=0, items=None)
    yield toggle("first array unreadable when count negative", TOGGLE_FIRST, count=-4, items=None)
    for case in chain_cases(TOGGLE_FIRST, "first", dict(count=2, items=[0x10, 0x20])):
        yield case


# ------------------------------------------------------------ message helper

def message_setup(text, hud=True, previous=b"stale buffer contents " * 3):
    def setup(env):
        this = env.object(0x80, "this", fill=0xA5)
        hud_object = env.object(0x80, "hud", fill=0) if hud else 0
        if hud:
            env.put(hud_object + 0x18, 10)
        env.put(this + 0x4C, hud_object)
        name = env.object(len(text) + 1, "name", data=text + b"\0")
        env.write(BUFFER, previous[:80])
        if hud:
            env.override(LSTRLEN, lambda env, call: len(env.cstr(call.arguments[0])))

            def interlocked(delta):
                def effect(env, call):
                    value = (env.get(call.arguments[0]) + delta) & 0xFFFFFFFF
                    env.put(call.arguments[0], value)
                    return value
                return effect

            env.override(DECREMENT, interlocked(-1))
            env.override(INCREMENT, interlocked(1))
        return {"this": this, "name": name, "hud": hud_object}
    return setup


def message(label, text, flag, **options):
    return Case(label, MESSAGE, message_setup(text, **options), receiver=lambda tokens: tokens["this"],
                arguments=(lambda tokens: tokens["name"], flag))


def message_cases(random_source):
    for text in (b"Cheat", b"", b"a", b"God Mode", b"%d%s", b"Layer toggle number 9"):
        for flag in (0, 1):
            yield message(f"message {text!r} flag {flag} no hud", text, flag, hud=False)
    for flag in (2, 0x80000000, 0xFFFFFFFF, 0x100):
        yield message(f"message flag {flag:#x} no hud", b"Invisible", flag, hud=False)
    for flag in (0, 1):
        yield message(f"message flag {flag} with hud", b"Cheat", flag, hud=True)
    for text in (b"Cheat", b"Fall speed five", b"x" * 33):
        yield message(f"message {len(text)} chars with hud", text, 1, hud=True)
    for _ in range(4):
        text = bytes(random_source.randrange(0x41, 0x7B) for _ in range(random_source.randrange(1, 40)))
        yield message("message random no hud", text, random_source.randrange(0, 2), hud=False)


# ------------------------------------------------------------ grant helper

def grant_setup(*, game=True, screen=None, suspended=0, state_id=0, state_time=0, field_a=0x1111, field_b=0x3333,
                this_170=0, this_d4=0x80, third_130=0):
    def setup(env):
        env.put(GAME, 0)
        tokens = {}
        if game:
            inner = env.object(0x40, "inner", fill=0)
            third = env.object(0x180, "third", fill=0x77)
            marked = third_130
            if marked == "item":
                marked = env.object(0x20, "marked-item", fill=0x31)
                env.put(marked + 8, 0x123)
            env.put(third + 0x130, marked)
            env.put(inner + 0x14, third)
            game_object = env.object(0x200, "game", fill=0x66)
            env.put(game_object + 0x6C, inner)
            env.put(game_object + 0xD4, this_d4)
            env.put(game_object + 0x170, this_170)
            env.put(GAME, game_object)
            tokens.update(game=game_object, inner=inner, third=third)
        env.put(CURRENT_SCREEN, env.object(0x80, "screen", fill=0) if screen is None else screen)
        env.put(SUSPEND, suspended)
        env.put(STATE_ID, state_id)
        env.put(STATE_TIME, state_time)
        return tokens
    return setup


def grant(label, first, second, **options):
    return Case(label, GRANT, grant_setup(**options), arguments=(first, second))


def grant_cases(random_source):
    yield grant("grant no game object", 0x26B8, 5, game=False, state_id=0x26B8, state_time=3)
    yield grant("grant no game object zeros", 0, 0, game=False)
    # same state id: accumulate time, clamp at 0xf3e58
    for state_time, add in ((0, 0), (0, 5), (100, 23), (0xF3E50, 7), (0xF3E50, 8), (0xF3E58, 0),
                            (0xF3E58, 1), (0xF3E00, 0x1000), (0xFFFFFFF0, 0x20), (5, 0xFFFFFFFF)):
        yield grant(f"grant same id time {state_time:#x}+{add:#x}", 0x26B8, add,
                    state_id=0x26B8, state_time=state_time)
    yield grant("grant same id zero", 0, 9, state_id=0, state_time=2)
    yield grant("grant same id negative", 0xFFFFFFFF, 4, state_id=0xFFFFFFFF, state_time=40)
    # different id, no sound branch: only global state and the switch
    for ident in (1, 0x26B6, 0x26B7, 0x26B8, 0x26B9, 0x26BA, 0x26BB, 0x26BD, 0x26BE, 0x7FFFFFFF):
        yield grant(f"grant new id {ident:#x} from idle", ident, 0x1234 + ident % 97, state_id=0, state_time=0x55)
    for ident in (0, 0xFFFFFFFF, 0x80000000):
        yield grant(f"grant new id {ident:#x} nonpositive", ident, 7, state_id=3, state_time=11)
    for ident in (0x26B7, 0x26BD):
        yield grant(f"grant leaves state {ident:#x} no helper object", 0x26BB, 2, state_id=ident, state_time=9,
                    this_170=0)
    yield grant("grant leaves state 0x26bc without effect", 0x26BB, 2, state_id=0x26BC, state_time=9, third_130=0)
    for ident in (0x26BB, 0x26B8):
        yield grant(f"grant leaves state 0x26bc with item, new {ident:#x}", ident, 2, state_id=0x26BC,
                    state_time=9, third_130="item")
    yield grant("grant arguments order", 0x26BB, 0x7777, state_id=0x26BB ^ 1, state_time=1)
    for _ in range(6):
        yield grant("grant random", random_source.choice((0x26B0, 0x26B6, 0x26BB, 0x26BE, 0x26C7, 0x1000)), random_source.getrandbits(32),
                    state_id=random_source.choice((0, 0x26B7, 0x26BC, 0x26BD, 0x26C0)),
                    state_time=random_source.getrandbits(20), this_170=0, third_130=0)


def cases(random_source):
    yield from fall_cases(random_source)
    yield from nth_cases(random_source)
    yield from fixed_cases(random_source)
    yield from first_cases(random_source)
    yield from message_cases(random_source)
    yield from grant_cases(random_source)
