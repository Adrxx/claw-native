"""Cases for pause_menu_entry: Pause menu key release, refresh and state destruction."""
import json
import pathlib
import random

from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

KEY_RELEASE = 0x44FE40
REFRESH = 0x44FA80
DELETING_DESTRUCTOR = 0x429820
CONSTANT_ELEVEN = 0x429810
DESTRUCTOR = 0x429840

G_REFRESH_FLAG = 0x53789C
G_CURSOR_FLAG = 0x5370CC
G_NIL_STRING = 0x52E1C8
G_PALETTE_OWNER = 0x541374
IAT_SHOWCURSOR = 0x546D54
IAT_TIME = 0x546DF0
# ShowCursor and timeGetTime are Windows imports the original reaches in 0x44fe40. They only have
# stand-ins when the specification declares them; the cases that need them are generated then.
_SPEC = json.loads(pathlib.Path(__file__).with_name("pause_menu_entry.json").read_text())
IMPORTS_DECLARED = all(hex(address) in _SPEC["callees"] for address in (IAT_SHOWCURSOR, IAT_TIME))

MENU_SIZE = 0x300
NODE_ORDER = (0, 8, 4, 1, 7, 3, 5)  # head, tail and interior positions of the slot list
SLOTS = (0x254, 0x258, 0x25C, 0x260, 0x264, 0x268, 0x26C)


def recorder(env, name, convention, argc, result=0, release_receiver=False, side=None):
    """A stub that logs receiver and arguments of its last eight calls into a live object."""
    log = env.object(8 * 4 * 6, name + "-log", fill=0)

    def effect(env, call):
        index = env.calls_so_far(call.function) - 1
        words = [call.receiver, *call.arguments]
        words += [0] * (5 - len(words))
        env.put(log + 24 * (index % 8), index + 1, *words[:5])
        if side:
            side(env, call)
        if release_receiver and call.receiver in env.spans:
            env.release(call.receiver)
        return result

    return env.stub(name, convention, argc, effect), log


def make_list(env, nodes, name):
    """A pointer list header (head, tail, count, free list) over a chain of nodes: next, previous, data."""
    addresses = [env.object(12, f"{name}-node{i}", fill=0) for i in range(nodes)]
    for i, node in enumerate(addresses):
        env.put(node, addresses[i + 1] if i + 1 < nodes else 0,
                addresses[i - 1] if i else 0, 0x7000 + i)
    return addresses


def vtable_object(env, size, slots, name, fill=0):
    """A heap object whose first word is a vtable with the given {index: stub} entries."""
    table = env.object(0x80, name + "-vtable", fill=0)
    for index, stub in slots.items():
        env.put(table + 4 * index, stub)
    obj = env.object(size, name, fill=fill)
    env.put(obj, table)
    return obj


def menu(rearm=None, obj270=None, obj3c=None, obj40=None, f2c=None, context=True, flag=None, size=MENU_SIZE,
         refresh_global=0x1357BD, stub_result=0, rearm_again=False):
    """setup() for a menu: sub-object arming flag, three owned list objects and one registered pointer.

    Each of obj270/obj3c/obj40 is None (absent) or the position (0 head, 1 middle, 2 tail) of its node
    in the shared list. f2c is None (zero) or the field compared inside the sub-list owner (True: equal)."""
    def setup(env):
        this = env.object(size, "menu", fill=0)
        env.put(G_REFRESH_FLAG, refresh_global)
        tokens = {"menu": this}
        def arm_again(env, call):
            if rearm_again and env.calls_so_far(call.function) == 1:
                env.put(this + 0x154 + 0x44, 0x7001)  # the callee re-arms the flag behind the caller's back

        sub_stub, tokens["sub-log"] = recorder(env, "armed", "thiscall", 0, stub_result, side=arm_again)
        sub_table = env.object(16, "armed-vtable", fill=0)
        env.put(sub_table + 4, sub_stub)
        nil = env.get(G_NIL_STRING) + 0xC  # an empty string: nothing to release when it is destroyed
        for offset in (0x54, 0x5C, *range(0x9C, 0xBC, 4)):
            env.put(this + 0x154 + offset, nil)
        env.put(this + 0x154 + 0x44, rearm or 0)
        env.put(this + 0x154 + 0x48, sub_table)
        if flag is not None:
            env.put(G_REFRESH_FLAG, flag)
        if context:
            holder = env.object(0x3D0, "list-holder", fill=0)
            nodes = make_list(env, 6, "menu")
            env.put(holder + 0x3B8 + 4, nodes[0], nodes[-1], len(nodes), 0x5000)
            tables = env.object(0x40, "tables", fill=0x5A)
            env.put(tables + 0x1C, 0, 0)  # zero-length lists
            owner = env.object(0x80, "table-owner", fill=0)
            env.put(owner + 0x1C, 0)
            env.put(owner + 0x64, 0x4444)
            ctx = env.object(0x40, "context", fill=0x33)
            env.put(ctx + 0x18, owner)
            env.put(ctx + 0x1C, holder)
            env.put(this + 0xC, ctx)
            tokens.update(holder=holder, nodes=nodes, context=ctx, owner=owner)
            dtor, tokens["dtor-log"] = recorder(env, "deleting-dtor", "thiscall", 1, 0, release_receiver=True)
            for offset, position in ((0x270, obj270), (0x3C, obj3c), (0x40, obj40)):
                if position is None:
                    continue
                victim = vtable_object(env, 0x20, {0: dtor}, f"object-{offset:x}", fill=0x11)
                env.put(victim + 4, nodes[(1, 2, 4)[position] if offset != 0x270 else (0, 3, 5)[position]])
                env.put(this + offset, victim)
                tokens[f"victim-{offset:x}"] = victim
            if f2c:
                env.put(this + 0x2C, 0x4444 if f2c is True else 0x5555)
        return tokens

    return setup


def pause(slots=None, two_a8=True, chain=None, cursor=0, cursor_values=(0xFFFFFFFF,), palette_owner=False,
          times=None, blt=("ok",), flip=("ok",), blt_restore=1, flip_restore=1, held_flags=0, seed=1,
          dtor_side=None, release_slots=True, cursor_side=None, **menu_options):
    """setup() for the key release handler: registered pointers, the optional fade chain and the services.

    slots lists the registered pointer offsets (their list nodes differ by slot and by seed). chain is None (nothing at 0x274), "bare" (an object
    without a palette holder) or "full" (the whole fade chain). times is the list of millisecond offsets
    timeGetTime returns after its start value. blt and flip are cycled lists of "ok" or "lost" results."""
    slots = tuple(slots or ())

    def setup(env):
        rng = random.Random(seed)
        shift = seed % len(NODE_ORDER)
        tokens = menu(**menu_options)(env)
        this = tokens["menu"]
        ctx = tokens["context"]
        env.put(this + 0x2A8, rng.choice((1, 0x100, 0x80000000, rng.randrange(1, 1 << 32))) if two_a8 else 0)
        env.put(G_CURSOR_FLAG, cursor)
        # Registered pointers: each has flags, an owner list and a node to unlink.
        holder = env.object(0x40, "slot-holder", fill=0)
        owner = env.object(0x20, "slot-owner", fill=0x21)
        env.put(owner + 8, holder)
        nodes = make_list(env, 9, "slot")
        env.put(holder + 0x10, 0, nodes[0], nodes[-1], len(nodes), 0x6000)
        side = (lambda env, call: dtor_side(env, call, tokens)) if dtor_side else None
        dtor, tokens["slot-log"] = recorder(env, "slot-dtor", "thiscall", 1, rng.randrange(1 << 32),
                                            release_receiver=release_slots, side=side)
        tokens["slots"] = {}
        tokens["spare"] = env.object(0x80, "spare", fill=0x12)
        for index, offset in enumerate(SLOTS):
            if offset not in slots:
                continue
            victim = vtable_object(env, 0x80, {1: dtor}, f"slot-{offset:x}", fill=0)
            env.write(victim + 0x10, bytes(rng.randrange(256) for _ in range(0x30)))
            env.put(victim + 8, rng.randrange(1 << 32))
            env.put(victim + 0xC, owner)
            env.put(victim + 0x40, rng.randrange(1 << 32))
            env.put(victim + 0x4C, 0x1111, 0x2222)
            env.put(victim + 0x68, nodes[NODE_ORDER[(index + shift) % len(NODE_ORDER)]])
            env.put(this + offset, victim)
            tokens["slots"][offset] = victim
        if chain:
            glue = env.object(0x20, "pair", fill=0x44)
            env.put(ctx + 4, glue)
            flags_holder = env.object(0x40, "flag-holder", fill=0)
            env.put(flags_holder + 0x34, held_flags)
            env.put(glue + 0xC, flags_holder)

            def cycling(results):
                def effect(env, call):
                    n = env.calls_so_far(call.function) - 1
                    return {"ok": 0, "lost": 0x887601C2}[results[n % len(results)]]
                return effect

            for name, field, kind, results, restore_result in (
                    ("blt", 0x14, (5, "stdcall", 6), blt, blt_restore),
                    ("flip", 0x10, (11, "stdcall", 3), flip, flip_restore)):
                restore, tokens[name + "-restore-log"] = recorder(env, name + "-restore", "thiscall", 0, restore_result)
                service = env.stub(name.capitalize(), kind[1], kind[2], cycling(results))
                direct = vtable_object(env, 0x10, {kind[0]: service}, name + "-interface", fill=0)
                surface = vtable_object(env, 0x40, {7: restore}, name + "-surface", fill=0x55)
                env.put(surface + 8, direct)
                wrapper = env.object(0x40, name + "-wrapper", fill=0x66)
                env.put(wrapper + 0x2C, surface)
                env.put(glue + field, wrapper)
                tokens[name + "-surface"] = surface
            top = env.object(0x40, "fade-top", fill=0xAA)
            env.put(this + 0x274, top)
            if chain == "full":
                get, tokens["get-log"] = recorder(env, "GetEntries", "stdcall", 5, 0, side=_fill_palette(rng))
                put, tokens["set-log"] = recorder(env, "SetEntries", "stdcall", 5, 0)
                palette = vtable_object(env, 0x10, {4: get, 6: put}, "palette", fill=0)
                fader = env.object(0x40, "fader", fill=0x77)
                buffer = env.object(0x400, "fade-buffer", fill=0x88)
                source = env.object(0x400, "fade-source", fill=0)
                env.write(source, bytes(rng.randrange(256) for _ in range(0x400)))
                env.put(fader + 4, palette)
                env.put(fader + 0xC, buffer, source)
                middle = env.object(0x40, "fade-holder", fill=0x99)
                env.put(middle + 0x10, fader)
                env.put(top + 0x2C, middle)
                tokens.update(buffer=buffer, source=source)
            else:
                env.put(top + 0x2C, 0)
        if palette_owner:
            query, _ = recorder(env, "palette-owner-service", "stdcall", 3, 0)
            service = vtable_object(env, 0x80, {22: query}, "palette-service", fill=0)
            cell = env.object(8, "palette-cell", fill=0)
            env.put(cell, service)
            env.put(G_PALETTE_OWNER, cell)
        else:
            env.put(G_PALETTE_OWNER, 0)
        start = rng.choice((0, 1000, 123456, 0xFFFFFF00, 0xFFFFFFFF, rng.randrange(1 << 32)))
        offsets = times if times is not None else (0, 100, 100, 260, 499, 500, 900)
        if IMPORTS_DECLARED:
            def time_get_time(env, call):
                n = env.calls_so_far(call.function) - 1
                return (start + offsets[min(n, len(offsets) - 1)]) & 0xFFFFFFFF

            def show_cursor(env, call):
                n = env.calls_so_far(call.function) - 1
                if cursor_side:
                    cursor_side(env, tokens, n)
                return cursor_values[min(n, len(cursor_values) - 1)] & 0xFFFFFFFF

            env.override(IAT_TIME, time_get_time)
            env.override(IAT_SHOWCURSOR, show_cursor)
        return tokens

    return setup


def _fill_palette(rng):
    data = bytes(rng.randrange(256) for _ in range(0x400))

    def side(env, call):
        env.write(call.arguments[4], data)

    return side


def on_menu(label, function, setup, **options):
    return Case(label, function, setup, receiver=lambda tokens: tokens["menu"], **options)


def cases(random_source):
    yield Case("eleven", CONSTANT_ELEVEN)
    # Refresh: nothing set, each owned object alone, all together.
    yield on_menu("refresh: empty", REFRESH, menu(context=False))
    yield on_menu("refresh: empty with context", REFRESH, menu())
    yield on_menu("refresh: armed sub-object", REFRESH, menu(rearm=1))
    yield on_menu("refresh: armed random", REFRESH, menu(rearm=random_source.randrange(2, 1 << 32), stub_result=7))
    for position in (0, 1, 2):
        yield on_menu(f"refresh: 0x270 node {position}", REFRESH, menu(obj270=position))
        yield on_menu(f"refresh: 0x3c node {position}", REFRESH, menu(obj3c=position))
        yield on_menu(f"refresh: 0x40 node {position}", REFRESH, menu(obj40=position))
    for same in (True, False):
        yield on_menu(f"refresh: field 0x2c {'equal' if same else 'different'}", REFRESH, menu(f2c=same))
    yield on_menu("refresh: callee re-arms the flag", REFRESH, menu(rearm=1, rearm_again=True))
    yield on_menu("refresh: all", REFRESH, menu(rearm=1, obj270=0, obj3c=1, obj40=2, f2c=True))
    yield on_menu("refresh: all other nodes", REFRESH, menu(rearm=3, obj270=2, obj3c=0, obj40=1, f2c=False))
    # Destructors.
    yield on_menu("destructor: empty", DESTRUCTOR, menu())
    yield on_menu("destructor: armed callee re-arms", DESTRUCTOR, menu(rearm=5, rearm_again=True))
    yield on_menu("destructor: everything", DESTRUCTOR, menu(rearm=1, obj270=1, obj3c=2, obj40=0, f2c=True))
    for flags in (0, 1, 2, 3, 0xFFFFFFFE, 0xFFFFFFFF):
        yield on_menu(f"deleting destructor flags {flags:#x}", DELETING_DESTRUCTOR, menu(obj270=1, rearm=1),
                      arguments=(flags,))

    # Key release.
    def release_case(label, key, **options):
        seed = random_source.randrange(1 << 62)
        return on_menu(label, KEY_RELEASE, pause(seed=seed, **options), arguments=(key,))

    all_slots = SLOTS
    full = dict(chain="full", cursor=1, palette_owner=True, slots=all_slots)
    # Enter returns at once and touches nothing, even with everything registered.
    yield release_case("release: enter, nothing registered", 13)
    yield release_case("release: enter, everything registered", 13, **full)
    yield release_case("release: enter, 0x2a8 clear", 13, two_a8=False, **full)
    if not IMPORTS_DECLARED:
        return
    keys = (0, 1, 5, 8, 10, 12, 14, 27, 0x109, 0x80000009, 0x8000000D, 0xFFFFFFFF, 0x100)
    for key in keys:
        yield release_case(f"release: key {key:#x}, nothing registered", key)
    for key in (9, 8):
        yield release_case(f"release: key {key}, all slots, fade chain", key, **full)
        yield release_case(f"release: key {key}, all slots, 0x2a8 clear", key, two_a8=False, **full)
    # Registered pointers, singly and in groups.
    for index, offset in enumerate(SLOTS):
        for two_a8 in (True, False):
            yield release_case(f"release: only slot {offset:#x}, 0x2a8 {'set' if two_a8 else 'clear'}", 7 + index,
                               slots=(offset,), two_a8=two_a8)
    for two_a8 in (True, False):
        yield release_case(f"release: all slots, 0x2a8 {'set' if two_a8 else 'clear'}", 3, slots=all_slots, two_a8=two_a8)
        yield release_case(f"release: all slots kept, 0x2a8 {'set' if two_a8 else 'clear'}", 3, slots=all_slots,
                           two_a8=two_a8, release_slots=False)
    for number in range(24):
        subset = tuple(offset for offset in SLOTS if random_source.randrange(2))
        yield release_case(f"release: random slots {sorted(hex(o) for o in subset)} #{number}",
                           random_source.randrange(256), slots=subset, two_a8=bool(random_source.randrange(4)),
                           release_slots=bool(random_source.randrange(2)))
    # Fade chain: object present, tail missing, palette holder present or absent.
    yield release_case("release: key 9, no fade object", 9)
    yield release_case("release: key 9, fade object without holder", 9, chain="bare")
    yield release_case("release: key 8, fade object without holder", 8, chain="bare")
    for key in (9, 10, 0x109, 0x80000009, 0x7FFFFFF9):
        yield release_case(f"release: key {key:#x} fade chain", key, chain="full")
    for owner in (False, True):
        for held in (0, 1, 2, 3, 0xFFFFFFFD):
            yield release_case(f"release: fade, palette owner {owner}, flags {held:#x}", 9, chain="full", cursor=1,
                               palette_owner=owner, held_flags=held)
    for times in ((0, 500), (0, 499, 500), (0, 0, 0, 10, 11, 600), (0, 9, 10, 11, 12, 13, 14, 300, 700),
                  (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 500)):
        yield release_case(f"release: fade clock {times[:6]}", 9, chain="full", times=times)
    for blt, flip, blt_restore, flip_restore in (
            (("ok",), ("ok",), 1, 1), (("ok",), ("lost", "ok"), 1, 1), (("ok",), ("lost",), 1, 0),
            (("ok",), ("lost", "ok"), 1, 7), (("ok",), ("lost", "lost", "ok"), 1, 5)):
        yield release_case(f"release: surfaces {blt} {flip} {blt_restore} {flip_restore}", 9, chain="full",
                           blt=blt, flip=flip, blt_restore=blt_restore, flip_restore=flip_restore, cursor=2)
    # The cursor flag is compared signed against zero.
    for cursor in (0, 1, 2, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, random_source.randrange(1, 1 << 31),
                   random_source.randrange(1 << 31, 1 << 32)):
        for chain in ("full", "bare"):
            yield release_case(f"release: cursor flag {cursor:#x} {chain}", random_source.randrange(256), chain=chain,
                               cursor=cursor, flip=("lost",), flip_restore=0)
    # The cursor counter loop.
    for values in ((0xFFFFFFFF,), (0, 0xFFFFFFFF), (3, 2, 1, 0, 0xFFFFFFFF), (0x7FFFFFFF, 0xFFFFFFFE),
                   (1, 0x80000000), (0x80000000,), (5,) * 3 + (0xFFFFFFF0,)):
        yield release_case(f"release: cursor counts {[hex(v) for v in values]}", 4, cursor_values=values, slots=(0x254,))
    # Values that callees change behind the function's back.
    def clear_next_slots(env, call, tokens):
        for offset in SLOTS:
            env.put(tokens["menu"] + offset, 0)
        env.put(tokens["menu"] + 0x274, 0)

    def swap_fade_object(env, call, tokens):
        env.put(tokens["menu"] + 0x274, 0)

    yield release_case("release: first destructor clears later slots", 9, slots=all_slots, chain="full",
                       dtor_side=clear_next_slots)
    yield release_case("release: destructor clears the fade object", 9, slots=all_slots, chain="full",
                       dtor_side=swap_fade_object)

    def register_slot(env, tokens, n):
        env.put(tokens["menu"] + 0x254, tokens["spare"])

    yield release_case("release: cursor service registers slot 0x254", 4, two_a8=False, cursor_side=register_slot)
    yield release_case("release: cursor service registers slot 0x254, 0x2a8 set", 4, cursor_side=register_slot)
