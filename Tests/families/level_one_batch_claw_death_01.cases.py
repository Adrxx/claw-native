"""Cases for level_one_batch_claw_death_01: Level 1 Claw death, respawn and life services."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, release, returns, sequence  # noqa: F401

DEATH_MESSAGE = 0x41EBD0
COPY_NAME = 0x41EE40
SEND_MESSAGE = 0x479F10
FIND_ITEM = 0x47A220
RETURN_ARG = 0x4B7AA0
LOOKUP = 0x4E0C60
SEND_CHECKED = 0x4E0D70
ERROR_TEXT = 0x4E10D0

RAND = 0x4A3050
LSTRLEN = 0x5469E4
DECREMENT = 0x5469E8
INCREMENT = 0x5469EC
MESSAGE_BEEP = 0x546CA4
MESSAGE_BOX = 0x546D48
OPERATOR_NEW = 0x4F63EC
GAME_GLOBAL = 0x5371FC
FILE_NAME = 0x533500

# Every error code the text chain of 0x4e10d0 names, in the original's order.
ERROR_CODES = (
    0x80004005, 0x80004001, 0x80070057, 0x8007000E, 0x8877000A, 0x88770005,
    0x8877001E, 0x88770014, 0x88770032, 0x88770028, 0x88770046, 0x8877003C,
    0x8877005A, 0x88770050, 0x88770082, 0x88770078, 0x887700A0, 0x88770096,
    0x887700BE, 0x887700AA, 0x887700D2, 0x887700C8, 0x887700E6, 0x887700DC,
    0x887700FA, 0x887700F0, 0x88770118, 0x8877010E, 0x88770136, 0x8877012C,
    0x887703F2, 0x887703E8, 0x88770406, 0x887703FC, 0x8877041A, 0x8877042E,
    0,
)
# Values that fall in a range of the chain but match none of its codes, and the extremes.
UNKNOWN_CODES = (
    1, 0x7FFFFFFF, 0x80000000, 0x80004000, 0x80004002, 0x80070000, 0x80070058,
    0x88770001, 0x88770100, 0x887700FB, 0x88770430, 0x88770500, 0xFFFFFFFF,
)
FLAG_SETS = ((0, 0, 0, 0), (1, 0, 0, 0), (0, 1, 0, 0), (1, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1),
             (1, 1, 1, 0), (1, 0, 1, 1), (0, 1, 1, 1), (1, 1, 1, 1))

NAMES = (b"Captain Claw", b"Le Rauxe", b"Pegleg", b"Mercat", b"Wolvington", b"Gabriel")


def pattern(size, seed):
    return bytes(((seed + i * 37) % 251) + 1 for i in range(size))


def stack_fill(draw, size):
    """Distinct non-zero garbage over the whole automatic frame below the entry stack pointer."""
    base = draw.randrange(1, 200)
    return ((-size, bytes(((base + i * 29) % 251) + 1 for i in range(size - 4))),
            (-4, bytes((((base + 7) * (k + 3)) % 251) + 1 for k in range(4))))


def cstring(env, text, refs=1, spare=0):
    """A CString buffer: refcount, length, capacity, then the text. Returns the text pointer."""
    storage = env.object(12 + len(text) + 1 + spare, "CString", data=pattern(12 + len(text) + 1 + spare, len(text)))
    env.put(storage, refs & 0xFFFFFFFF, len(text), len(text) + spare)
    env.write(storage + 12, text + b"\0")
    return storage + 12


def strings(env, decrement=None):
    """Stand-ins for the Windows string and atomic services used by the original CString helpers."""
    env.override(LSTRLEN, lambda e, c: len(e.cstr(c.arguments[0])))

    def increment(e, c):
        value = (e.get(c.arguments[0]) + 1) & 0xFFFFFFFF
        e.put(c.arguments[0], value)
        return value

    def decrease(e, c):
        value = (e.get(c.arguments[0]) - 1) & 0xFFFFFFFF
        if decrement is None:
            e.put(c.arguments[0], value)
            return value
        e.put(c.arguments[0], value)
        return decrement

    env.override(INCREMENT, increment)
    env.override(DECREMENT, decrease)


def dp_globals(env, flags=(0, 0, 0, 0)):
    env.put(0x544D20, flags[0])
    env.put(0x544D24, flags[1])
    env.put(0x544D28, flags[2])
    env.put(0x544D2C, flags[3])
    env.override(MESSAGE_BEEP, returns(1))
    env.override(MESSAGE_BOX, returns(1))


def recorder(env, observations, result):
    """Stand-in for the DirectPlay send method: records its arguments and the message bytes."""

    def send(e, call):
        index = e.calls_so_far(0) if False else 0
        e.put(observations, *call.arguments[:6])
        size = min(call.arguments[5], 0x100) if len(call.arguments) > 5 else 0
        if size and call.arguments[4]:
            e.write(observations + 0x20, e.read(call.arguments[4], size))
        return result

    return send


def world(env, seed=7, state=4, send_result=0, keys=(11, 22, 33), key_index=1, key=None, name=b"Captain Claw",
          name_refs=1, c_mode="item", preset_buffer=False, list_count=0, no_list=False, flags=(0, 0, 0, 0),
          rand=None, locked_name=False):
    """The Claw game object graph used by the death message, send and lookup functions."""
    strings(env)
    dp_globals(env, flags)
    if rand is not None:
        env.override(RAND, returns(rand & 0xFFFFFFFF))
    observations = env.object(0x400, "send observations", fill=0)
    items = []
    for index, item_key in enumerate(keys):
        item = env.object(0x40, f"item {index}", data=pattern(0x40, seed + index))
        env.put(item + 4, item_key & 0xFFFFFFFF)
        text = name + bytes([0x41 + index])
        env.put(item + 8, cstring(env, text, name_refs if not locked_name else 0xFFFFFFFF))
        if preset_buffer:
            buffer = env.object(0x400, f"preset buffer {index}", fill=0x5A)
            env.put(item + 0x18, buffer, 0x400 + index)
        else:
            env.put(item + 0x18, 0, 0)
        items.append(item)
    nodes = []
    for index, item in enumerate(items):
        node = env.object(12, f"node {index}", fill=0)
        env.put(node + 8, item)
        nodes.append(node)
    for index, node in enumerate(nodes):
        env.put(node, nodes[index + 1] if index + 1 < len(nodes) else 0)
        env.put(node + 4, nodes[index - 1] if index else 0)
    methods = env.object(0x80, "dplay methods", data=pattern(0x80, seed + 3))
    dplay = env.object(8, "dplay", data=pattern(8, seed + 4))
    env.put(dplay, methods)
    env.put(methods + 0x68, env.stub("IDirectPlay::Send", "stdcall", 6, recorder(env, observations, send_result)))
    manager = env.object(0x80, "net manager", data=pattern(0x80, seed + 5))
    env.put(manager + 0x18, dplay)
    env.put(manager + 0x58, nodes[0] if nodes else 0)
    # The list that receives displayed messages.
    queue = env.object(0x1C, "message list", fill=0)
    env.put(queue + 0x18, 3)
    if list_count:
        block = env.object(4 + 12 * list_count, "existing list block", fill=0)
        env.put(queue + 0x14, block)
        texts = []
        for index in range(list_count):
            texts.append(cstring(env, b"old-line-%d" % index))
        for index in range(list_count):
            node = block + 4 + index * 12
            env.put(node, block + 4 + (index + 1) * 12 if index + 1 < list_count else 0,
                    block + 4 + (index - 1) * 12 if index else 0, texts[index])
        env.put(queue + 4, block + 4, block + 4 + (list_count - 1) * 12, list_count)
    panel = env.object(0x60, "panel", data=pattern(0x60, seed + 6))
    env.put(panel + 0x4C, queue)
    vtable = env.object(0x20, "claw methods", data=pattern(0x20, seed + 7))
    env.put(vtable + 0x10, env.stub("Claw::state", "thiscall", 0, returns(state & 0xFFFFFFFF)))
    claw = env.object(0xC00, "claw", data=pattern(0xC00, seed + 8))
    chosen = keys[key_index] if (key_index is not None and keys) else 0x7777
    env.put(claw, vtable)
    env.put(claw + 4, panel)
    env.put(claw + 0x780, manager)
    other = env.object(0x40, "other item", data=pattern(0x40, seed + 9))
    env.put(other + 8, cstring(env, b"Stranger"))
    initial = {"item": items[key_index] if (key_index is not None and items) else 0,
               "other": other, "null": 0}[c_mode]
    env.put(claw + 0x784, initial)
    env.put(claw + 0x788, (chosen if key is None else key) & 0xFFFFFFFF)
    message = env.object(0x200, "message buffer", data=pattern(0x200, seed + 10))
    env.put(claw + 0xBC8, message)
    game = env.object(0x40, "game", data=pattern(0x40, seed + 11))
    env.put(game + 0x2C, claw)
    env.put(GAME_GLOBAL, game)
    if no_list:
        env.put(manager + 0x58, 0)
    text = env.object(0x200, "text", data=pattern(0x200, seed + 12))
    return {"claw": claw, "manager": manager, "items": items, "queue": queue, "message": message,
            "text": text, "game": game, "observations": observations}


def with_text(raw, **options):
    """world() plus a caller text buffer holding `raw` followed by a terminator."""

    def setup(env):
        tokens = world(env, **options)
        env.write(tokens["text"], raw + b"\0")
        return tokens

    return setup


def cases(random_source):
    draw = random_source
    # ---- 0x4b7aa0: ret 4
    for value in (0, 1, draw.getrandbits(32)):
        yield Case(f"return arg {value:#x}", RETURN_ARG, None, arguments=(value,))

    # ---- 0x4e0c60: list lookup by key
    def lookup_setup(keys, key_index=None, probe=None, empty=False):
        def setup(env):
            tokens = world(env, keys=keys, key_index=0, no_list=empty)
            tokens["probe"] = probe if probe is not None else keys[key_index]
            return tokens

        return setup

    for keys, index, label in (((5,), 0, "single"), ((5, 6, 7), 0, "first"), ((5, 6, 7), 1, "middle"),
                               ((5, 6, 7), 2, "last"), ((9, 9, 9), 1, "duplicate keys")):
        yield Case(f"lookup {label}", LOOKUP, lookup_setup(keys, index), receiver=lambda t: t["manager"],
                   arguments=(lambda t: t["probe"],))
    yield Case("lookup missing", LOOKUP, lookup_setup((5, 6, 7), probe=8), receiver=lambda t: t["manager"],
               arguments=(lambda t: t["probe"],))
    yield Case("lookup zero key", LOOKUP, lookup_setup((0, 6), probe=0), receiver=lambda t: t["manager"],
               arguments=(lambda t: t["probe"],))
    yield Case("lookup empty", LOOKUP, lookup_setup((5, 6), probe=5, empty=True), receiver=lambda t: t["manager"],
               arguments=(lambda t: t["probe"],))
    for _ in range(4):
        keys = tuple(draw.sample(range(1, 0xFFFFFF00), 4))
        at = draw.randrange(4)
        yield Case(f"lookup random {at}", LOOKUP, lookup_setup(keys, at), receiver=lambda t: t["manager"],
                   arguments=(lambda t: t["probe"],))

    # ---- 0x41ee40: copy a CString
    def copy_setup(refs, text):
        def setup(env):
            strings(env)
            source = env.object(0x20, "source", data=pattern(0x20, 3))
            env.put(source + 8, cstring(env, text, refs))
            destination = env.object(8, "destination", fill=0x33)
            return {"source": source, "destination": destination}

        return setup

    for refs, text in ((1, b"Captain Claw"), (2, b"Le Rauxe"), (0, b"zero refs"), (0x7FFFFFFE, b"many"),
                       (0xFFFFFFFF, b"locked name"), (0xFFFFFFFF, b""), (1, b"")):
        yield Case(f"copy name refs {refs:#x} {text!r}", COPY_NAME, copy_setup(refs, text),
                   receiver=lambda t: t["source"], arguments=(lambda t: t["destination"],))

    # ---- 0x47a220: find the item and give it a buffer
    def find_setup(**options):
        def setup(env):
            return world(env, **options)

        return setup

    for label, options in (("match middle", {}), ("match first", {"key_index": 0}),
                           ("match last", {"key_index": 2}),
                           ("preset buffer", {"preset_buffer": True}),
                           ("missing key", {"key": 99}),
                           ("empty list", {"no_list": True}),
                           ("zero key", {"keys": (0, 4), "key_index": 0}),
                           ("single item", {"keys": (3,), "key_index": 0})):
        yield Case(f"find {label}", FIND_ITEM, find_setup(**options), receiver=lambda t: t["claw"])
    yield Case("find alloc fails", FIND_ITEM,
               lambda env: (lambda t: (env.override(OPERATOR_NEW, allocate(fail=True)), t)[1])(world(env)),
               receiver=lambda t: t["claw"])

    # ---- 0x4e0d70: checked send
    def send_setup(result, item_null=False):
        def setup(env):
            tokens = world(env, send_result=result, flags=FLAG_SETS[result % len(FLAG_SETS)])
            tokens["item"] = 0 if item_null else tokens["items"][1]
            tokens["payload"] = env.object(0x40, "payload", data=pattern(0x40, 21))
            return tokens

        return setup

    for result in (0, 0x80004005, 0x88770118, 0x8877042E, 0x12345678, 0xFFFFFFFF):
        for item_null in (False, True):
            yield Case(f"checked send result {result:#x} item_null {item_null}", SEND_CHECKED,
                       send_setup(result, item_null), receiver=lambda t: t["manager"],
                       arguments=(lambda t: t["item"], draw.getrandbits(32), lambda t: t["payload"],
                                  draw.randrange(1, 0x40)))

    # ---- 0x4e10d0: DirectPlay error text
    def error_setup(flags, name=True):
        def setup(env):
            dp_globals(env, flags)
            env.override(MESSAGE_BEEP, returns(1))
            env.override(MESSAGE_BOX, returns(1))
            return {"file": env.object(0x40, "file name", data=b"net\\directplay.cpp\0" + pattern(0x20, 9))}

        return setup

    def error_case(label, code, flags, file_arg=True, line=0x49A):
        return Case(label, ERROR_TEXT, error_setup(flags),
                    arguments=((lambda t: t["file"]) if file_arg else 0, line, code,
                               draw.getrandbits(32)))

    for index, code in enumerate(ERROR_CODES):
        flags = FLAG_SETS[index % len(FLAG_SETS)]
        yield error_case(f"error {code:#x}", code, flags, file_arg=index % 5 != 4, line=1 + index * 11)
    for index, code in enumerate(UNKNOWN_CODES):
        yield error_case(f"unknown error {code:#x}", code, FLAG_SETS[(index + 3) % len(FLAG_SETS)],
                         file_arg=index % 4 != 3, line=(0x49A if index % 3 else 0))
    for flags in [(a, b, c, d) for a in (0, 1) for b in (0, 1) for c in (0, 1) for d in (0, 1)]:
        for file_arg, line in ((True, 5), (False, 5), (True, 0), (True, -1)):
            if not any(flags) and (not file_arg or line < 5):
                continue
            yield error_case(f"flags {flags} file {file_arg} line {line}", 0x80004005, flags, file_arg, line)
    for flags in FLAG_SETS[:6]:
        code = draw.choice(ERROR_CODES + UNKNOWN_CODES)
        yield error_case(f"random code {code:#x} flags {flags}", code, flags, line=draw.randrange(-2, 3000))
    yield Case("error at the real source name", ERROR_TEXT, error_setup((1, 1, 1, 1)),
               arguments=(FILE_NAME, 0x49A, 0x88770118, 0))

    # ---- 0x479f10: send a typed message
    def tail(count):
        return b"".join(bytes([0x20 + draw.randrange(0x5F)]) for _ in range(count))

    texts = {
        "plain": b"Sails ahead",
        "one char": b"x",
        "exactly 0x80": bytes(0x41 + i % 26 for i in range(0x80)),
        "0x7f": bytes(0x41 + i % 26 for i in range(0x7F)),
        "0x81 truncates": bytes(0x41 + i % 26 for i in range(0x81)),
        "very long": bytes(0x61 + i % 26 for i in range(0xC0)),
        "trailing newline": b"Ahoy\n",
        "trailing cr lf": b"Ahoy\r\n",
        "three trailing controls": b"Ahoy\x01\x02\x03",
        "only control": b"\n",
        "two controls": b"\x01\x02",
        "high byte tail": b"Ahoy\xe9",
        "space tail kept": b"Ahoy ",
        "inner control kept": b"A\x01hoy",
        "newline then letter": b"Ah\noy",
        "long with newline": bytes(0x41 + i % 26 for i in range(0x80)) + b"\n",
        "long newline at limit": bytes(0x41 + i % 26 for i in range(0x7F)) + b"\n",
    }
    for label, raw in texts.items():
        for third, fourth in ((0, 0), (1, 1)):
            yield Case(f"send {label} name {third} queue {fourth}", SEND_MESSAGE,
                       with_text(raw, list_count=(len(raw) % 3), seed=5 + len(raw)),
                       receiver=lambda t: t["claw"],
                       arguments=(lambda t: t["text"], draw.randrange(1, 0x1000), third, fourth),
                       initial_stack=stack_fill(draw, 0x114))
    for third, fourth in ((0, 1), (1, 0)):
        yield Case(f"send plain name {third} queue {fourth}", SEND_MESSAGE, with_text(texts["plain"]),
                   receiver=lambda t: t["claw"], arguments=(lambda t: t["text"], 0x55AA, third, fourth),
                   initial_stack=stack_fill(draw, 0x114))
    for third, fourth in ((7, 0x100), (0x100, 0x80000000), (0xFFFFFFFF, 3), (0x10000, 0x7FFF0000)):
        yield Case(f"send plain flags {third:#x} {fourth:#x}", SEND_MESSAGE, with_text(b"Distinct flags", list_count=1),
                   receiver=lambda t: t["claw"], arguments=(lambda t: t["text"], 0x1357BDF, third, fourth),
                   initial_stack=stack_fill(draw, 0x114))
    yield Case("send null text", SEND_MESSAGE, with_text(b"x"), receiver=lambda t: t["claw"],
               arguments=(0, 3, 1, 1), initial_stack=stack_fill(draw, 0x114))
    yield Case("send empty text", SEND_MESSAGE, with_text(b""), receiver=lambda t: t["claw"],
               arguments=(lambda t: t["text"], 3, 1, 1), initial_stack=stack_fill(draw, 0x114))
    for label, options in (("item missing", {"key": 99}), ("preset buffer", {"preset_buffer": True}),
                           ("empty list", {"no_list": True}), ("send error", {"send_result": 0x80004005,
                                                                               "flags": (1, 1, 1, 0)}),
                           ("shared name", {"name_refs": 3}), ("locked name", {"locked_name": True}),
                           ("locked name only", {"locked_name": True, "name": b""}),
                           ("existing queue", {"list_count": 2}), ("last item", {"key_index": 2}),
                           ("first item", {"key_index": 0})):
        for third in (0, 1):
            yield Case(f"send {label} name {third}", SEND_MESSAGE,
                       with_text(b"Walk the plank\n", **options), receiver=lambda t: t["claw"],
                       arguments=(lambda t: t["text"], 0x77 + third * 0x1111, third, 1),
                       initial_stack=stack_fill(draw, 0x114))
    for _ in range(14):
        length = draw.randrange(1, 150)
        raw = bytes(draw.randrange(0x21, 0x7F) for _ in range(length))
        if draw.random() < 0.5:
            raw += bytes(draw.randrange(1, 0x20) for _ in range(draw.randrange(1, 4)))
        name = bytes(draw.randrange(0x41, 0x5B) for _ in range(draw.randrange(1, 60)))
        third, fourth = draw.randrange(2), draw.randrange(2)
        yield Case(f"send random {length} name {third} queue {fourth}", SEND_MESSAGE,
                   with_text(raw, name=name, seed=draw.randrange(1, 200), key_index=draw.randrange(3)),
                   receiver=lambda t: t["claw"],
                   arguments=(lambda t: t["text"], draw.getrandbits(31) + 1, third, fourth),
                   initial_stack=stack_fill(draw, 0x114))

    # ---- 0x41ebd0: announce the death
    def death(label, rand=0, **options):
        return Case(label, DEATH_MESSAGE, lambda env: world(env, rand=rand, **options),
                    initial_stack=stack_fill(draw, 0x214))

    for state in (0, 1, 3, 5, 0x80000004, 0xFFFFFFFF):
        yield death(f"single player state {state:#x}", state=state)
    for value in range(26):
        options = {"name": NAMES[value % len(NAMES)], "seed": 3 + value, "key_index": value % 3}
        if value % 6 == 1:
            options.update(send_result=0x88770118, flags=FLAG_SETS[value % len(FLAG_SETS)])
        if value % 4 == 2:
            options["list_count"] = 2
        yield death(f"phrase {value}", rand=value, **options)
    for value in (25, 51, 77, 103, 0x7FFF - 0x7FFF % 26 + 25 - 26, 0x7FFFFFFF, 0xFFFFFFE7, 0xFFFFFFE6, 0xFFFFFFE5,
                  0xFFFFFFCD, 0xFFFFFFFE, 0xFFFFFFB3, 0x80000019, 0x8000001A):
        yield death(f"boundary rand {value:#x}", rand=value, name=draw.choice(NAMES), seed=draw.randrange(1, 200),
                    key_index=value % 3)
    for value in (26, 27, 51, 52, 0x7FFF, 0x7FFE, 0x8000, 0xFFFFFFFF, 0xFFFFFFE6, 0x80000000, 0x40000000):
        yield death(f"rand {value:#x}", rand=value, name=draw.choice(NAMES), seed=draw.randrange(1, 200))
    for _ in range(6):
        yield death("random phrase", rand=draw.randrange(0, 0x8000), name=draw.choice(NAMES),
                    seed=draw.randrange(1, 200), key_index=draw.randrange(3),
                    name_refs=draw.randrange(1, 4))
    yield death("no player item", rand=5, c_mode="null")
    yield death("other player item", rand=6, c_mode="other")
    yield death("key missing", rand=7, key=99)
    yield death("preset buffer", rand=8, preset_buffer=True)
    yield death("locked name", rand=9, locked_name=True)
    yield death("locked empty name", rand=10, locked_name=True, name=b"")
    yield death("shared name", rand=11, name_refs=4)
    yield death("send error", rand=12, send_result=0x887700F0, flags=(0, 1, 0, 0))
    yield death("no items", rand=13, keys=(), key_index=None)

    # ---- release order: the name CString is freed after the formatter read it.
    # A zero-reference name is copied (count 1) and released (count 0), so the real
    # operator delete runs. The delete stand-in overwrites the freed text with a
    # poison pattern: a formatter that runs after the release prints the poison.
    def poisoned_world(poison_seed, **options):
        def setup(env):
            tokens = world(env, name_refs=0, **options)

            def poison_delete(e, call):
                block = call.arguments[0]
                if block:
                    size = e.get(block + 4)
                    if 0 < size <= 0x100:
                        e.write(block + 12, bytes(((poison_seed + i * 53) % 100) + 0x90 for i in range(size)))
                    e.release(block)
                return 0

            env.override(0x4F6428, poison_delete)
            return tokens

        return setup

    def poisoned_text(raw, poison_seed, **options):
        inner = poisoned_world(poison_seed, **options)

        def setup(env):
            tokens = inner(env)
            env.write(tokens["text"], raw + b"\0")
            return tokens

        return setup

    for value in range(26):
        seed = draw.randrange(1, 90)
        name = NAMES[value % len(NAMES)] + (b"" if value % 3 else b" the Bold")
        yield Case(f"poisoned death phrase {value}", DEATH_MESSAGE,
                   poisoned_world(seed, rand=value, name=name, seed=2 + value, key_index=value % 3,
                                  list_count=value % 3),
                   initial_stack=stack_fill(draw, 0x214))
    for value in (25, 0x7FFFFFFF, 0xFFFFFFFF, 51):
        yield Case(f"poisoned death boundary rand {value:#x}", DEATH_MESSAGE,
                   poisoned_world(draw.randrange(1, 90), rand=value, name=draw.choice(NAMES), send_result=0x88770118,
                                  flags=FLAG_SETS[value % len(FLAG_SETS)]),
                   initial_stack=stack_fill(draw, 0x214))
    for index, raw in enumerate((b"Sails ahead", b"x", b"Ahoy\n", bytes(0x41 + i % 26 for i in range(0x80)),
                                 b"Walk the plank", b"Ah\x01oy")):
        for third, fourth in ((1, 0), (1, 1)):
            for name in (b"Pegleg", b"Captain Claw the Great"):
                yield Case(f"poisoned send {index} name {name!r} queue {fourth}", SEND_MESSAGE,
                           poisoned_text(raw, draw.randrange(1, 90), name=name, list_count=index % 3,
                                         seed=5 + index, key_index=index % 3),
                           receiver=lambda t: t["claw"],
                           arguments=(lambda t: t["text"], draw.randrange(1, 0x1000), third, fourth),
                           initial_stack=stack_fill(draw, 0x114))
    for _ in range(6):
        raw = bytes(draw.randrange(0x21, 0x7F) for _ in range(draw.randrange(1, 100)))
        name = bytes(draw.randrange(0x41, 0x5B) for _ in range(draw.randrange(1, 40)))
        yield Case("poisoned send random", SEND_MESSAGE,
                   poisoned_text(raw, draw.randrange(1, 90), name=name, seed=draw.randrange(1, 200),
                                 key_index=draw.randrange(3), send_result=draw.choice((0, 0x80004005)),
                                 flags=(1, 0, 1, 0)),
                   receiver=lambda t: t["claw"],
                   arguments=(lambda t: t["text"], draw.getrandbits(31) + 1, 1, draw.randrange(2)),
                   initial_stack=stack_fill(draw, 0x114))

    # Named-layout review: buffer existence and byte capacity are separate words.
    # 0x47a23f tests +0x18 only; +0x1c need not agree with that pointer.
    def distinct_buffer_setup(buffer_present):
        def setup(env):
            tokens = world(env)
            buffer = env.object(0x400, "buffer with zero capacity", fill=0x5A) if buffer_present else 0
            env.put(tokens["items"][1] + 0x18, buffer, 0 if buffer_present else 0x2222)
            return tokens

        return setup

    for buffer_present in (False, True):
        yield Case(f"find buffer and capacity disagree {buffer_present}", FIND_ITEM,
                   distinct_buffer_setup(buffer_present), receiver=lambda t: t["claw"])

    # 0x479f65 resets ECX to 128 before trimming at most two signed control bytes.
    # A wrong 129 reset spends its first trim on the terminator just written at
    # byte 128 and therefore leaves the control byte at 126 in the message.
    for prefix, display in ((0, 0), (1, 1)):
        yield Case(f"send truncated two-control tail prefix {prefix} display {display}", SEND_MESSAGE,
                   with_text(b"A" * 126 + b"\r\nB"), receiver=lambda t: t["claw"],
                   arguments=(lambda t: t["text"], 0x13579, prefix, display))

    # The ordinary comparison entry stack is documented as 0x02008000. File is
    # an unrestricted guest token, so it may point inside the automatic text
    # buffer. Placing it above the destination keeps the forward string copy
    # bounded, while a diagnostic pass changes what the later dialog reads.
    def aliased_error_file_setup(flags):
        def setup(env):
            dp_globals(env, flags)
            return {"file": 0x02008000 - 0x200 + 8}

        return setup

    for flags in ((0, 1, 0, 0), (1, 1, 0, 0)):
        yield Case(f"error filename aliases automatic text flags {flags}", ERROR_TEXT,
                   aliased_error_file_setup(flags),
                   arguments=(lambda t: t["file"], 7, 0x80004005, 0),
                   initial_stack=((-0x1F8, b"witness.cpp\0"),))
