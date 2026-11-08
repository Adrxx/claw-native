"""Popup forwarding and opaque saved-state words, from original behavior."""
from clawparity.cases import Case

KEY_DOWN = 0x4392D0
KEY_UP = 0x439390
POINTERS = (0x4393C0, 0x439400, 0x439440)
PEEK, PUSH, POP = 0x42BFD0, 0x42BFF0, 0x42C010


def popup_setup(active=True, origin=(37, 91), result=0, escape_swap=False,
                map_key=None, map_mode="empty"):
    def setup(env):
        owner = env.object(0x180, "popup-owner", fill=0xA7)
        popup = env.object(0x2C0, "active-popup", fill=0xB3)
        alternate = env.object(0x2C0, "replacement-popup", fill=0xC5)
        table = env.object(0x200, "popup-methods", fill=0)
        log = env.object(0x200, "callback-observations", fill=0)
        env.put(owner + 0x160, popup if active else 0)
        for p in (popup, alternate):
            env.put(p, table)
            env.put(p + 0x294, *origin)
            env.put(p + 0x27C, 0, 7)

        def recorder(tag):
            def effect(env, call):
                index = env.get(log)
                at = log + 4 + index * 40
                env.put(at, tag, call.receiver, len(call.arguments),
                        *call.arguments)
                env.put(at + 24, env.get(owner + 0x160),
                        env.get(popup + 0x294), env.get(popup + 0x298))
                env.put(log, index + 1)
                return result
            return effect

        for slot, argc in ((0x18C, 2), (0x190, 2), (0x194, 2),
                           (0x198, 2), (0x19C, 2), (0x1B0, 2),
                           (0x1F0, 0), (0x1F8, 0)):
            env.put(table + slot, env.stub(f"popup-slot-{slot:x}", "thiscall", argc,
                                          recorder(slot)))
        provider = env.object(8, "type-provider", fill=0x61)
        provider_table = env.object(0x18, "type-methods", fill=0)
        env.put(provider, provider_table)
        env.put(owner + 0x164, provider)

        def type_query(env, call):
            recorder(0x10)(env, call)
            if escape_swap:
                env.put(owner + 0x160, alternate)
            return 4

        env.put(provider_table + 0x10,
                env.stub("type-query", "thiscall", 0, type_query))
        if map_key is not None:
            buckets = env.object(28, "key-buckets", fill=0)
            item_id = 0x6A31
            tail = env.object(12, "key-tail", words=[0, map_key, item_id])
            head = env.object(12, "key-head", words=[tail, map_key ^ 0x10000, 0x7742])
            env.put(buckets + ((map_key >> 4) % 7) * 4, head)
            env.put(popup + 0x27C, buckets, 7)
            if map_mode == "miss":
                env.put(tail + 4, map_key ^ 0x20000)
            items = env.object(3 * 0x5C, "menu-items", fill=0x93)
            for index, ident in enumerate((0x1B72, item_id if map_mode != "no-item" else 0x6A30, 0x3E82)):
                env.write(items + index * 0x5C + 0x10, ident.to_bytes(2, "little"))
            env.write(popup + 0x14, (3).to_bytes(2, "little"))
            env.put(popup + 0x3C, items)
            env.put(popup + 0x68, 0x8AF17D23)
        return {"owner": owner}
    return setup


def popup_case(label, entry, arguments, **options):
    return Case(label, entry, popup_setup(**options),
                receiver=lambda t: t["owner"], arguments=arguments)


def saved_setup(count, capacity, words):
    def setup(env):
        owner = env.object(0x110, "saved-state-owner", fill=0xB7)
        data = env.object(max(4, capacity * 4), "saved-state-buffer", words=words,
                          fill=0xD9) if capacity else 0
        env.put(owner + 0xE0, data, count & 0xFFFFFFFF, capacity, 3)
        return {"owner": owner}
    return setup


def saved_case(label, entry, count, capacity, words, arguments=()):
    return Case(label, entry, saved_setup(count, capacity, words),
                receiver=lambda t: t["owner"], arguments=arguments)


def cases(random_source):
    for entry, args in ((KEY_DOWN, (0x1B, 0x81923764)),
                        (KEY_UP, (0xFFFFFFFF, 0x718492A3)),
                        *((p, (0xA3D57291, 0x80000000, 0xFFFFFFFF)) for p in POINTERS)):
        yield popup_case(f"null popup {entry:x}", entry, args, active=False)
    for key in (0x0D, 0x20, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2E):
        for result in (0, 0x87654321):
            yield popup_case(f"direct key {key:x} callback {result:x}", KEY_DOWN,
                             (key, random_source.getrandbits(32)), result=result)
    for key in (0, 0x0C, 0x0E, 0x1A, 0x1C, 0x21, 0x22, 0x29,
                0x2D, 0x2F, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        yield popup_case(f"default key {key:x} empty map", KEY_DOWN,
                         (key, random_source.getrandbits(32)))
        yield popup_case(f"default key {key:x} mapped item", KEY_DOWN,
                         (key, random_source.getrandbits(32)), map_key=key, map_mode="hit",
                         result=0xF12345AB)
    for mode in ("miss", "no-item"):
        yield popup_case(f"default populated {mode}", KEY_DOWN, (0x41, 0x82A1F37D),
                         map_key=0x41, map_mode=mode)
    for swap in (False, True):
        yield popup_case(f"escape reload {swap}", KEY_DOWN, (0x1B, 0xA13B7D29),
                         escape_swap=swap, result=0xFFFFFFFF)
    for first, second in ((0, 1), (0xFFFFFFFF, 0x80000000),
                          (random_source.getrandbits(32), random_source.getrandbits(32))):
        yield popup_case(f"key up {first:x} {second:x}", KEY_UP, (first, second),
                         result=0xD764193A)
    geometries = ((37, 91, 119, 233), (100, 200, 99, 202),
                  (0x80000000, 0xFFFFFFFF, 0x7FFFFFFF, 1),
                  (0xFFFFFFFF, 0x7FFFFFFF, 0, 0x80000000),
                  (31, 79, 31, 79))
    for entry in POINTERS:
        for ox, oy, x, y in (*geometries,
                              tuple(random_source.getrandbits(32) for _ in range(4))):
            yield popup_case(f"coordinates {entry:x} {ox:x},{oy:x} to {x:x},{y:x}",
                             entry, (random_source.getrandbits(32), x, y),
                             origin=(ox, oy), result=0x83D5A719)
    words = [0x17A3B941, 0x82F14567, 0xD1B5729F, 0x381D7A63,
             random_source.getrandbits(32) | 1, 0x91A3C7E5]
    for count in (0, -1, -0x80000000):
        yield saved_case(f"peek nonpositive {count}", PEEK, count, 0, [])
        yield saved_case(f"pop nonpositive {count}", POP, count, 0, [], (0xA315D749,))
    for count in (1, 2, 5):
        yield saved_case(f"peek count {count}", PEEK, count, 6, words)
        for value in (0, words[count - 1], words[count - 1] ^ 0x80000000):
            yield saved_case(f"pop count {count} value {value:x}", POP, count, 6, words, (value,))
    yield saved_case("peek top zero", PEEK, 3, 6, [*words[:2], 0, *words[3:]])
    yield saved_case("pop zero top versus nonzero", POP, 3, 6,
                     [*words[:2], 0, *words[3:]], (0x80000000,))
    for count, capacity in ((0, 0), (0, 6), (1, 6), (5, 6), (1, 1), (6, 6)):
        for value in (0, 0x80000000, random_source.getrandbits(32) | 1):
            yield saved_case(f"push count {count} capacity {capacity} value {value:x}",
                             PUSH, count, capacity, words[:capacity], (value,))
    yield saved_case("zero push negative count", PUSH, -1, 0, [], (0,))
