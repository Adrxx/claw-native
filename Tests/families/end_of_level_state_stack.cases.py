"""Cases for end_of_level_state_stack: End-of-level application state stack pop and level advance.

0x429ac0 pops the top of the application's state stack and makes it current.
0x429be0 advances to the next level when the current state reports id 3.

Everything is observed through traced virtual-method stand-ins: each call
appends (tag, receiver, first argument, [application + 0x2c], [application + 0xe4])
to a log object in the heap, so the comparison judges receivers, arguments,
order and the application fields at the moment of every call.

The original level loader 0x46aeb0 (called at 0x429c3d) and the timer 0x42abf0
(called at 0x429b60) end in imports with no stand-in in the specification, so
no case runs them. Cases that would reach the loader stop at the stand-in for
the current state's method at +0x28 (the last call before the loader).
"""
from clawparity.cases import Case
from clawparity.env import Halt

POP = 0x429AC0
ADVANCE = 0x429BE0

ENTRY = 6  # words per log entry
LOG_ENTRIES = 64
LOADER, POST_MESSAGE, TIME_GET_TIME, INTERLOCKED_DEC, INTERLOCKED_INC = 0x46AEB0, 0x546D50, 0x546DF0, 0x5469E8, 0x5469EC

# virtual method offsets
M_DESTROY, M_ID, M_READY, M_ENTER, M_LEAVE = 0x00, 0x10, 0x1C, 0x24, 0x28
APP_ACTIVE = 0x0C


def tracer(log, t, tag, result=0, hook=None, halts=False):
    """A method stand-in: log the call, run an optional hook, return `result` (a number or function of (env, call))."""
    def effect(env, call):
        count = env.get(log)
        app = t["app"]
        env.put(log + 4 + 4 * ENTRY * count, tag, call.receiver,
                call.arguments[0] if call.arguments else 0xA5A5A5A5,
                env.get(app + 0x2C), env.get(app + 0xE4),
                call.arguments[1] if len(call.arguments) > 1 else 0xA5A5A5A5)
        env.put(log, count + 1)
        if hook:
            hook(env, call, t)
        if halts:
            raise Halt()
        return result(env, call) if callable(result) else result
    return effect


def note(env, log, *words):
    """Append raw words (padded to one entry) to the case log."""
    count = env.get(log)
    words = tuple(words) + (0xA5A5A5A5,) * (ENTRY - len(words))
    env.put(log + 4 + 4 * ENTRY * count, *words)
    env.put(log, count + 1)


def scripted(env, t, ticks, loads, loader_hook, post_result, interlocked):
    """Drive the scripted fixtures; every call is recorded in the log."""
    log, app = t["log"], t["app"]

    def tick(env, call):
        note(env, log, TIME_GET_TIME, 0, 0, env.get(app + 0x2C), env.get(app + 0xE4))
        return ticks[min(env.calls_so_far(call.function), len(ticks)) - 1]

    def load(env, call):
        note(env, log, LOADER, call.receiver, call.arguments[0], env.get(app + 0x2C), call.arguments[1],
             env.get(call.receiver + 0x14))
        if loader_hook:
            loader_hook(env, call, t)
        return loads[min(env.calls_so_far(call.function), len(loads)) - 1]

    def post(env, call):
        note(env, log, POST_MESSAGE, *call.arguments)
        return post_result

    def decrement(env, call):
        value = (env.get(call.arguments[0]) - 1) & 0xFFFFFFFF
        env.put(call.arguments[0], value)
        note(env, log, INTERLOCKED_DEC, call.arguments[0], value)
        return value if not interlocked else interlocked

    def increment(env, call):
        value = (env.get(call.arguments[0]) + 1) & 0xFFFFFFFF
        env.put(call.arguments[0], value)
        note(env, log, INTERLOCKED_INC, call.arguments[0], value)
        return value

    env.override(TIME_GET_TIME, tick)
    env.override(LOADER, load)
    env.override(POST_MESSAGE, post)
    env.override(INTERLOCKED_DEC, decrement)
    env.override(INTERLOCKED_INC, increment)


def vtable(env, t, name, tagbase=0, results=None, hooks=None, halt=(), size=0x40):
    """A method table. results/hooks map offsets to a value or function and a hook; halt lists offsets that stop the case."""
    results, hooks = results or {}, hooks or {}
    table = env.object(size, name + "-vtable", fill=0)
    argc = {M_DESTROY: 1, M_ENTER: 1, M_LEAVE: 1}
    for offset in (M_DESTROY, M_ID, M_READY, M_ENTER, M_LEAVE):
        env.put(table + offset, env.stub(f"{name} +{offset:#x}", "thiscall", argc.get(offset, 0),
                                         tracer(t["log"], t, tagbase | offset, results.get(offset, 0),
                                                hooks.get(offset), offset in halt)))
    return table


def state(env, t, name, vt, size=0x40, level=None, seed=1):
    obj = env.object(size, name, fill=0)
    env.put(obj, vt)
    for offset in range(4, size, 4):
        env.put(obj + offset, (0x51000000 + (seed << 12) + offset) & 0xFFFFFFFF)
    if level is not None:
        env.put(obj + 0x14, level & 0xFFFFFFFF)
    return obj


def application(env, count, array_values, current=True, ready=1, hooks=None, current_hooks=None,
                new_hooks=None, current_results=None, new_results=None, other=False, alt=False,
                ready_hook=None, seed=1, top_is_current=False, halt=(), halt_others=False,
                stacked_results=None, ticks=(0x1000, 0x1010, 0x1020), loads=(0,), loader_hook=None,
                post_result=1, owner_table=True, interlocked=0):
    """The application with a state stack whose entries are array_values (or fresh states when None)."""
    t = {}
    t["log"] = log = env.object(4 + 4 * ENTRY * LOG_ENTRIES, "log", fill=0)
    app = t["app"] = env.object(0x800, "application", fill=0)
    appvt = env.object(0x20, "application-vtable", fill=0)
    window = env.object(0x20, "window", fill=0)
    owner = t["owner"] = env.object(0x400, "owner", fill=0)
    env.put(app, appvt)
    for offset in range(4, 0x800, 4):
        env.put(app + offset, (0x60000000 + (seed << 12) + offset) & 0xFFFFFFFF)
    env.put(app + 4, window)
    env.put(window + 4, 0x7234)
    env.put(app + 8, owner)
    if owner_table:
        owner_vt = vtable(env, t, "owner", 0x800, size=0x40)
        env.put(owner_vt + 0x1C, env.stub("owner notify", "thiscall", 2, tracer(log, t, 0x81C, 0x4242)))
        env.put(owner, owner_vt)
    scripted(env, t, ticks, loads, loader_hook, post_result, interlocked)
    env.put(app + 0x30, 0)
    env.put(appvt + APP_ACTIVE, env.stub("application active", "thiscall", 0,
                                         tracer(log, t, APP_ACTIVE, ready, ready_hook)))
    others_halt = (M_LEAVE,) if halt_others else ()
    t["alt_vt"] = vtable(env, t, "alt", 0x100, results={M_ID: 0x4400 + seed}, halt=others_halt) if alt else 0
    t["other"] = 0
    if other:
        t["other"] = state(env, t, "other", vtable(env, t, "other", 0x200, results={M_ID: 0x6600 + seed}, halt=others_halt), seed=seed + 9)
    stack = []
    n = max(len(array_values or ()), 1)
    array = env.object(4 * (n + 2), "stack-array", fill=0)
    t["array"] = array
    for i, entry in enumerate(array_values or ()):
        if entry == "state":
            entry = state(env, t, f"stacked{i}",
                          vtable(env, t, f"stacked{i}", 0x300 + 0x10000 * i, results={M_ID: 0x2100 + 3 * i + seed, **(stacked_results or {})}),
                          seed=seed + i)
        stack.append(entry)
        env.put(array + 4 * i, entry)
    t["stack"] = stack
    env.put(app + 0xE0, array)
    env.put(app + 0xE4, count & 0xFFFFFFFF)
    cur = 0
    if current:
        vt = vtable(env, t, "current", 0, results={M_ID: 0x7700 + seed, **(current_results or {})},
                    hooks=current_hooks, halt=halt)
        cur = state(env, t, "current", vt, seed=seed + 5)
    t["current"] = cur
    env.put(app + 0x2C, cur)
    if top_is_current and stack:
        env.put(array + 4 * (len(stack) - 1), cur)
    return t


# ---------------------------------------------------------------- 0x429ac0

def pop_case(label, count, values, **options):
    return Case(label, POP, lambda env: application(env, count, values, **options), receiver=lambda t: t["app"])


def swap_vtable(target, key):
    def hook(env, call, t):
        env.put(t[target], t[key])
    return hook


def pop_cases(rand):
    S = "state"
    # the application reports it is not active: nothing else happens
    for ready in (0,):
        yield pop_case("not active", 3, [S, S, S], ready=ready)
        yield pop_case("not active, empty stack", 0, [S], ready=ready)
    # any nonzero activity word counts, all 32 bits are tested
    for ready in (1, 2, 0x100, 0x10000, 0x01000000, 0x80000000, 0xFFFFFFFF):
        yield pop_case(f"active {ready:#x}", 3, [S, S, S], ready=ready)
    # stack depth: empty, negative and positive counts
    for count in (0, -1, -7, 0x80000000, 0xFFFFFFFF):
        yield pop_case(f"count {count:#x} has no top", count, [S, S, S])
    for count in (1, 2, 3, 4, 5, 6):
        yield pop_case(f"count {count}", count, [S] * count, seed=count)
        yield pop_case(f"count {count} without current", count, [S] * count, current=False, seed=count)
    # a null entry on top
    for count in (1, 2, 4):
        yield pop_case(f"null top of {count}", count, [S] * (count - 1) + [0])
        yield pop_case(f"null top of {count}, no current", count, [S] * (count - 1) + [0], current=False)
    yield pop_case("null below top", 3, [0, S, S])
    # the top is already the current state
    for count in (1, 2, 4):
        yield pop_case(f"top {count} is current", count, [S] * count, top_is_current=True)
    yield pop_case("current deeper in the stack", 3, [S, S, S], top_is_current=False, current_results={}, seed=4)

    def deep_current(env):
        t = application(env, 3, [S, S, S])
        env.put(t["array"], t["current"])
        env.put(t["array"] + 4, t["current"])
        return t
    yield Case("current equals lower entries only", POP, deep_current, receiver=lambda t: t["app"])
    # activity stand-in changes the stack before it is read
    def grow(env, call, t):
        env.put(t["app"] + 0xE4, 2)
    yield pop_case("stack grows while checking activity", 0, [S, S], ready_hook=grow)

    def shrink(env, call, t):
        env.put(t["app"] + 0xE4, 0)
    yield pop_case("stack empties while checking activity", 3, [S, S, S], ready_hook=shrink)

    def drop_current(env, call, t):
        env.put(t["app"] + 0x2C, 0)
    yield pop_case("current vanishes while checking activity", 3, [S, S, S], ready_hook=drop_current)

    # method tables are read at particular moments
    yield pop_case("current id swaps current table", 3, [S, S, S], alt=True,
                   current_hooks={M_ID: swap_vtable("current", "alt_vt")})

    def swap_current_table(env, call, t):
        env.put(t["current"], t["alt_vt"])
    yield pop_case("current id swaps current table (hook)", 3, [S, S, S], alt=True,
                   current_hooks={M_ID: swap_current_table})

    def swap_new_table(env, call, t):
        env.put(t["stack"][-1], t["alt_vt"])
    yield pop_case("current id swaps new table", 3, [S, S, S], alt=True, current_hooks={M_ID: swap_new_table})

    def make_new_hook_swapping_current(env, call, t):
        env.put(t["current"], t["alt_vt"])
    # new state id call: after the new state's table was used for it, swap current's table
    def new_swap_hooks(env, t):
        return None

    def build_new_id_swap(env, mode):
        t = application(env, 3, [S, S, S], alt=True, other=True)
        top = t["stack"][-1]
        tableid = env.get(top)
        # rebuild the top state's table with a hook on its id
        def hook(env, call, t):
            if mode == "cur_table":
                env.put(t["current"], t["alt_vt"])
            elif mode == "cur_pointer":
                env.put(t["app"] + 0x2C, t["other"])
            elif mode == "cur_null":
                env.put(t["app"] + 0x2C, 0)
        env.put(top, vtable(env, t, "toppy", 0x400, results={M_ID: 0x9100}, hooks={M_ID: hook}))
        return t
    for mode in ("cur_table", "cur_pointer", "cur_null"):
        yield Case(f"new state id: {mode}", POP, lambda env, mode=mode: build_new_id_swap(env, mode),
                   receiver=lambda t: t["app"])

    # leave stand-in changes things
    yield pop_case("leave clears the current pointer", 3, [S, S, S],
                   current_hooks={M_LEAVE: lambda env, call, t: env.put(t["app"] + 0x2C, 0)})
    yield pop_case("leave redirects the current pointer", 3, [S, S, S], other=True,
                   current_hooks={M_LEAVE: lambda env, call, t: env.put(t["app"] + 0x2C, t["other"])})
    yield pop_case("leave empties the stack", 3, [S, S, S],
                   current_hooks={M_LEAVE: lambda env, call, t: env.put(t["app"] + 0xE4, 0)})
    yield pop_case("leave makes the stack negative", 3, [S, S, S],
                   current_hooks={M_LEAVE: lambda env, call, t: env.put(t["app"] + 0xE4, 0xFFFFFFFF)})
    yield pop_case("leave shortens the stack", 4, [S, S, S, S],
                   current_hooks={M_LEAVE: lambda env, call, t: env.put(t["app"] + 0xE4, 2)})

    def release_current(env, call, t):
        env.release(call.receiver)
    yield pop_case("destroy frees the current state", 3, [S, S, S], current_hooks={M_DESTROY: release_current})
    yield pop_case("destroy shrinks the stack", 3, [S, S, S],
                   current_hooks={M_DESTROY: lambda env, call, t: env.put(t["app"] + 0xE4, 1)})
    yield pop_case("destroy empties the stack", 3, [S, S, S],
                   current_hooks={M_DESTROY: lambda env, call, t: env.put(t["app"] + 0xE4, 0)})
    # enter stand-in changes the current pointer before the follow-up method is chosen
    def replace_on_enter(env, call, t):
        env.put(t["app"] + 0x2C, t["other"])

    def build_enter_replace(env):
        t = application(env, 3, [S, S, S], other=True)
        top = t["stack"][-1]
        env.put(top, vtable(env, t, "entering", 0x500, results={M_ID: 0x8123},
                            hooks={M_ENTER: replace_on_enter}))
        return t
    yield Case("enter replaces current before follow-up", POP, build_enter_replace, receiver=lambda t: t["app"])

    def build_enter_clears(env):
        t = application(env, 3, [S, S, S], other=True)
        top = t["stack"][-1]
        env.put(top, vtable(env, t, "entering", 0x500, results={M_ID: 0x8123},
                            hooks={M_ENTER: lambda env, call, t: env.put(t["app"] + 0xE4, 0)}))
        return t
    yield Case("enter empties the stack", POP, build_enter_clears, receiver=lambda t: t["app"])

    # the new state starts (or is ready): the owner flag is set and the timer is reset
    def flagged(label, count=3, tick_pointer=0, chain=0, **options):
        def build(env):
            t = application(env, count, ["state"] * count, **options)
            env.put(t["app"] + 0x30, tick_pointer)
            env.put(0x541328, 0x13572468)
            env.put(0x54132C, 0x2468ACE0)
            env.put(0x5430C4, 0x77777777)
            env.put(0x5430C8, 0x88888888)
            holder = 0
            if chain:
                inner = env.object(0x140, "inner", fill=0x55)
                middle = env.object(0x20, "middle", fill=0x66)
                outer = env.object(0x80, "outer", fill=0x77)
                env.put(outer + 0x6C, middle)
                env.put(middle + 0x14, inner if chain == 2 else 0)
                env.put(inner + 0x120, 0x1111)
                holder = outer
            env.put(0x537E88, holder)
            return t
        return Case(label, POP, build, receiver=lambda t: t["app"])
    for value in (1, 2, 0x100, 0x80000000, 0xFFFFFFFF):
        yield flagged(f"enter returns {value:#x}", stacked_results={M_ENTER: value})
        yield flagged(f"ready returns {value:#x}", stacked_results={M_READY: value})
    yield flagged("both enter and ready nonzero", stacked_results={M_ENTER: 1, M_READY: 1})
    for pointer in (0, 0x1000, 0xFFFFFFFF):
        for chain in (0, 1, 2):
            yield flagged(f"flag path, tick pointer {pointer:#x}, chain {chain}", stacked_results={M_ENTER: 1},
                          tick_pointer=pointer, chain=chain, ticks=(0xCAFE0001, 0xCAFE0002))
    yield flagged("flag path without current", current=False, stacked_results={M_ENTER: 1})
    yield flagged("flag path with one entry", count=1, stacked_results={M_READY: 5})
    yield flagged("flag path with ready hook", stacked_results={M_ENTER: 3},
                  ready_hook=lambda env, call, t: env.put(t["app"] + 0xE4, 3))

    def build_ready_after_enter_replaces(env):
        t = application(env, 3, ["state"] * 3, other=True)
        top = t["stack"][-1]
        env.put(top, vtable(env, t, "entering", 0x500, results={M_ID: 0x8123},
                            hooks={M_ENTER: lambda env, call, t: env.put(t["app"] + 0x2C, t["other"])}))
        env.put(env.get(t["other"]) + M_READY, env.stub("other ready", "thiscall", 0, tracer(t["log"], t, 0x21C, 9)))
        return t
    yield Case("enter replaces current, replacement is ready", POP, build_ready_after_enter_replaces,
               receiver=lambda t: t["app"])

    # random combinations
    for index in range(60):
        count = rand.randrange(1, 7)
        values = [S] * count
        if rand.random() < 0.2:
            values[-1] = 0
        has_current = rand.random() < 0.8
        yield pop_case(f"random pop {index}", count, values, ticks=(rand.randrange(1 << 32),), current=has_current, ready=rand.randrange(1, 1 << 32),
                       seed=rand.randrange(1, 200), top_is_current=rand.random() < 0.1,
                       current_results={M_ID: rand.randrange(1 << 32)})
    for index in range(10):
        yield pop_case(f"random inactive {index}", rand.randrange(0, 5), [S] * 4, ready=0, seed=rand.randrange(1, 200))


# ---------------------------------------------------------------- 0x429be0

def id_by_call(first, later):
    """EAX of the state's id method: `first` on the first call, `later` afterwards."""
    return lambda env, call: first if env.calls_so_far(call.function) == 1 else later


def advance(env, ident, level, later=0x1234, hooks=None, results=None, string=None, other=False, alt=False,
            seed=1, size=0x800, owner_null=False, **app_options):
    t = application(env, 0, [], current=False, other=other, alt=alt, seed=seed, **app_options)
    results = {M_ID: id_by_call(ident, later), **(results or {})}
    vt = vtable(env, t, "level", 0, results=results, hooks=hooks, size=0x40)
    cur = t["current"] = state(env, t, "level", vt, size=size, level=level, seed=seed + 3)
    env.put(t["app"] + 0x2C, cur)
    string = string if string is not None else [0, 0x11223344, 0x55667788]
    text = env.object(32, "cstring", fill=0)
    env.put(text, string[1], string[0], string[2])  # p[-12], p[-8], p[-4]
    env.put(t["app"] + 0xC0, text + 12)
    t["text"] = text
    if owner_null:
        env.put(t["app"] + 8, 0)
    return t


def adv_case(label, ident, level, **options):
    return Case(label, ADVANCE, lambda env: advance(env, ident, level, **options), receiver=lambda t: t["app"])


def advance_cases(rand):
    # any other id: nothing else is touched
    for ident in (0, 1, 2, 4, 5, 0x103, 0x10003, 0x80000003, 0xFFFFFFFD, 0xFFFFFFFF, 0x3000000):
        yield adv_case(f"id {ident:#x} is not the level state", ident, 5)
    # every real level where each load fails: 13 attempts, then the window message
    for level in range(1, 15):
        yield adv_case(f"level {level}: all loads fail", 3, level, seed=level)
    # levels outside 1..14: 14 attempts, then the owner notification
    for level in (0, 15, 16, 100, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xFFFFFFF0):
        yield adv_case(f"level {level:#x}: all loads fail", 3, level, seed=level & 0xFF)
        yield adv_case(f"level {level:#x}: all loads fail, no owner", 3, level, seed=level & 0xFF, owner_null=True)
    # success on the k-th attempt
    for level in range(1, 15):
        for attempt in (1, 2, 13):
            yield adv_case(f"level {level}: load {attempt} succeeds", 3, level, seed=level + attempt,
                           loads=(0,) * (attempt - 1) + (1,))
    for level in (0, 15, 0xFFFFFFFF, 0x80000000):
        for attempt in (1, 13, 14):
            yield adv_case(f"level {level:#x}: load {attempt} succeeds", 3, level, loads=(0,) * (attempt - 1) + (1,))
    # nonzero results of any width count as success; 14th attempt is the last for out-of-range levels
    for value in (2, 0x100, 0x10000, 0x80000000, 0xFFFFFFFF):
        yield adv_case(f"load returns {value:#x}", 3, 6, loads=(0, 0, value))
    # the second id call differs from the first; it is passed to the leave method and the loader hook
    for later in (0, 3, 7, 0xFFFFFFFF):
        yield adv_case(f"second id call returns {later:#x}", 3, 6, later=later, loads=(0, 1))
    # the window message goes to the handle two levels of pointers deep
    for hwnd in (0, 1, 0x80000000, 0xFFFFFFFF):
        def build(env, hwnd=hwnd):
            t = advance(env, 3, 9)
            env.put(env.get(t["app"] + 4) + 4, hwnd)
            return t
        yield Case(f"window handle {hwnd:#x}", ADVANCE, build, receiver=lambda t: t["app"])
    for result in (0, 7, 0xFFFFFFFF):
        yield adv_case(f"PostMessageA returns {result:#x}", 3, 3, post_result=result)
    # loader and method tables change between attempts
    def load_swaps(env, call, t):
        if env.calls_so_far(call.function) == 2:
            env.put(t["current"], t["alt_vt"])
    yield adv_case("table swapped by the second load", 3, 4, alt=True, loader_hook=load_swaps, loads=(0, 0, 0, 1))

    def load_changes_level(env, call, t):
        env.put(t["current"] + 0x14, 14)
    yield adv_case("level changed by the first load", 3, 4, loader_hook=load_changes_level, loads=(0, 0, 0, 0))

    def load_clears_app_state(env, call, t):
        env.put(t["app"] + 0x2C, t["other"])
    yield adv_case("application state replaced by the first load", 3, 4, other=True, loader_hook=load_clears_app_state,
                   loads=(0, 0, 1))

    def load_swaps_success(env, call, t):
        env.put(t["current"], t["alt_vt"])
    yield adv_case("table swapped by the successful load", 3, 4, alt=True, loader_hook=load_swaps_success, loads=(1,))

    def swap_state(env, call, t):
        if env.calls_so_far(call.function) == 1:
            env.put(t["app"] + 0x2C, t["other"])
    yield adv_case("state replaced during the first id call", 3, 4, other=True, hooks={M_ID: swap_state})

    def swap_table(env, call, t):
        if env.calls_so_far(call.function) == 2:
            env.put(t["current"], t["alt_vt"])
    yield adv_case("table swapped during the second id call", 3, 4, alt=True, hooks={M_ID: swap_table},
                   loads=(0, 1))

    def swap_table_first(env, call, t):
        if env.calls_so_far(call.function) == 1:
            env.put(t["current"], t["alt_vt"])
    yield adv_case("table swapped during the first id call", 3, 4, alt=True, hooks={M_ID: swap_table_first})

    def change_level(env, call, t):
        env.put(t["current"] + 0x14, 14)
    yield adv_case("level changed by the first id call", 3, 4, hooks={M_ID: change_level})
    # text header words
    for pattern in ([0, 0, 0], [0, 0xFFFFFFFF, 0xFFFFFFFF], [0, 1, 2], [0, 0x80000000, 0x7FFFFFFF]):
        yield adv_case(f"empty text header {pattern}", 3, 4, string=pattern)
    for index in range(30):
        level = rand.randrange(1, 15) if index % 2 else rand.randrange(1 << 32)
        attempts = rand.randrange(1, 16)
        yield adv_case(f"random advance {index}", 3, level, seed=rand.randrange(1, 100),
                       later=rand.randrange(1 << 32), loads=(0,) * (attempts - 1) + (rand.randrange(1, 1 << 32),),
                       ticks=(rand.randrange(1 << 32),),
                       string=[0, rand.randrange(1 << 32), rand.randrange(1 << 32)])
    for index in range(10):
        ident = rand.randrange(1 << 32)
        if ident == 3:
            ident = 4
        yield adv_case(f"random other id {index}", ident, rand.randrange(1 << 32), seed=rand.randrange(1, 100))


def cases(random_source):
    yield from pop_cases(random_source)
    yield from advance_cases(random_source)
