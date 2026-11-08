"""Cases for level_one_state_registry_01: Level one state registry entries, batch 1.

Objects used by the owned code:
  registry object ("owner"): +0 vtable, +4 handler object, +8 bit count, +0xc inline bits or pointer to bits.
  handler object: +0 message callback, +4 scratch index, +8 halfword slot, +0xc kind, +0x14 prefix string.
  global table of callbacks: 0x544b98, 32 slots of 12 bytes (key, value, halfword), count at 0x544d18.
Coverage of every reachable branch does not depend on the random source: the random cases only add variety.
Error-report paths (allocation failure, bad text) go through 0x4dc680, declared as a compiler-context dependency.
"""
import re

from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

REMOVE_OWNER = 0x4DB6C0
ASSIGN = 0x4DBD60
FROM_TEXT = 0x4DBE10
DEFAULT_CTOR = 0x4DC180
REGISTRY = 0x4DC560
RESIZE = 0x4DC7B0

MALLOC = 0x4A48E0
TABLE = 0x544B98
COUNT = 0x544D18
DEFAULT_BITS = 0x533470
MSG_MEMORY = 0x544B4C
MSG_NULL = 0x544B3C
MSG_BAD = 0x544B44
GLOBAL_HANDLER = 0x544B68
VTABLE_A = 0x513E28
VTABLE_B = 0x513E34
OWNER_SIZE = 0x30


def u32(value):
    return value & 0xFFFFFFFF


def filled_malloc(byte):
    """malloc whose new memory is not zero, so that a missing clear is visible."""
    return lambda env, call: env.object(call.arguments[0], name="allocation", fill=byte)


def signed_key(value):
    value = u32(value)
    return value - (1 << 32) if value & 0x80000000 else value


def write_table_signed(env, entries, junk):
    """entries: (key, value, aux) triples; written in signed key order. Unused slots get junk."""
    entries = sorted(entries, key=lambda e: signed_key(e[0]))
    for index in range(32):
        slot = TABLE + 12 * index
        if index < len(entries):
            key, value, aux = entries[index]
            env.put(slot, u32(key), u32(value), 0xA5A50000 | (aux & 0xFFFF))
        else:
            env.put(slot, junk + index, junk + 0x100 + index, junk + 0x200 + index)
    env.put(COUNT, len(entries))


def new_frame(random_source):
    """Four distinct non-zero random words for a caller-frame object; the word at +4 is what 0x4dc680 returns."""
    return random_source.sample(range(1, 0xFFFFFFFF), 4)


def elect_frame(env, words):
    """The caller's EBP at entry points into a live object, so [EBP + 4] is a known backed word."""
    env.entry_frame_pointer(env.object(16, "caller-frame", words=words, fill=0x75))


# ---------------------------------------------------------------- registry (0x4dc560, 0x4db6c0)

def registry_setup(offsets, absolute, stale, junk):
    """A handler h, an owner o whose handler is h, and a table whose keys are o + offset (or absolute)."""
    def setup(env):
        handler = env.object(0x20, "handler", words=[0x1111, stale, 0x3333, 0x4444, 0x5555], fill=0x6B)
        owner = env.object(OWNER_SIZE, "owner", words=[0x7777, handler, 0x20, 0x8888], fill=0x2D)
        entries = []
        for i, offset in enumerate(offsets):
            key = offset if absolute else owner + offset
            entries.append((key, 0x1000 + 0x37 * i + junk, 0x40 + i))
        write_table_signed(env, entries, 0x77000000 + junk)
        return {"handler": handler, "owner": owner}
    return setup


def registry_call(label, offsets, key_offset, value, stale=0, absolute=False, junk=1):
    if absolute:
        key = lambda tokens: u32(key_offset)
    else:
        key = lambda tokens: u32(tokens["owner"] + key_offset)
    return Case(label, REGISTRY, registry_setup(offsets, absolute, stale, junk),
                receiver=lambda tokens: tokens["handler"], arguments=(key, value))


def registry_cases(random_source):
    for n in (0, 1, 2, 3, 4, 5, 8, 9, 16, 31, 32):
        offsets = [0x20 * (i + 1) for i in range(n)]
        probes = {}
        for i in sorted({0, n // 2, n - 1}) if n else []:
            probes[f"hit {i}"] = offsets[i]
        probes["below all"] = 0x10
        probes["above all"] = 0x20 * n + 0x30
        if n >= 2:
            probes["between 0 and 1"] = offsets[0] + 0x10
            probes[f"between {n // 2} and next"] = offsets[n // 2 - 1] + 0x10 if n // 2 else offsets[0] + 0x10
        if n >= 3:
            probes[f"between {n - 2} and {n - 1}"] = offsets[n - 2] + 0x10
        for name, key in probes.items():
            for value in (0, 0x9000 + random_source.randrange(1, 0xFFF) * 0x10 + n):
                action = "remove" if value == 0 else "store"
                stale = 7 if n == 0 else random_source.randrange(0, 31)
                yield registry_call(f"registry n={n} {name} {action}", offsets, key, value, stale=stale,
                                    junk=random_source.randrange(1, 0xFFFF))
    for stale in (0, 1, 7, 31):
        for value in (0, 0x5151):
            yield registry_call(f"registry empty table, stale index {stale}, value {value}", [], 0x40, value, stale=stale)
    # keys on either side of the sign boundary exercise the signed comparison
    keys = [-0x7FFFFF00, -500, -3, 0, 5, 77, 0x7FFFFF00]
    for probe in (-0x7FFFFF00, -500, -3, 0, 5, 77, 0x7FFFFF00, -4, -1, 1, 6, 0x70000000, -0x7FFFFFFF, 0x7FFFFFFF):
        for value in (0, 0xBEEF):
            yield registry_call(f"registry signed keys probe {probe} value {value}", keys, probe, value, absolute=True,
                                stale=3)
    for _ in range(40):
        n = random_source.randrange(0, 33)
        keys = sorted(random_source.sample(range(-3000, 3000), n))
        probe = random_source.choice(keys) if keys and random_source.random() < 0.5 else random_source.randrange(-3100, 3100)
        value = random_source.choice((0, random_source.randrange(1, 0xFFFFFFF)))
        yield registry_call(f"registry random n={n} probe {probe} value {value:#x}", keys, probe, value, absolute=True,
                            stale=random_source.randrange(0, 32), junk=random_source.randrange(1, 0xFFFF))


def remove_owner_cases(random_source):
    for n in (1, 2, 5, 9, 32):
        for position in sorted({0, n // 2, n - 1}):
            offsets = [0x20 * (i - position) for i in range(n)]
            yield Case(f"owner destructor: entry {position} of {n} is removed",
                       REMOVE_OWNER, registry_setup(offsets, False, 5, random_source.randrange(1, 999)),
                       receiver=lambda tokens: tokens["owner"])
    for name, offsets in (("below every key", [0x20 * (i + 1) for i in range(6)]),
                          ("above every key", [-0x20 * (i + 1) for i in range(6)]),
                          ("between keys", [-0x40, -0x20, 0x20, 0x40]),
                          ("empty table", []),
                          ("full table without it", [0x20 * (i + 1) for i in range(32)])):
        yield Case(f"owner destructor: owner not registered, {name}", REMOVE_OWNER,
                   registry_setup(offsets, False, 9, random_source.randrange(1, 999)),
                   receiver=lambda tokens: tokens["owner"])


# ---------------------------------------------------------------- bit sets

def make_set(env, handler, bits, seed, name="set"):
    """A registry object holding `bits` bits, with distinct non-zero contents."""
    words = [u32(0x9E3779B1 * (seed + i + 1)) | 1 for i in range(max(1, (bits + 31) // 32))]
    if bits > 0x20:
        buffer = env.object(len(words) * 4, name + "-bits", words=words, fill=0x66)
        return env.object(OWNER_SIZE, name, words=[VTABLE_B, handler, bits, buffer], fill=0x2D), buffer
    return env.object(OWNER_SIZE, name, words=[VTABLE_B, handler, bits, words[0]], fill=0x2D), None


def install_handler(env, handler, kind, owner, found):
    """Fill a handler object for 0x4db4d0: the message callback, a halfword slot, the kind and a prefix."""
    callback = env.stub("handler-message", "cdecl", 2, returns(0x61))
    prefix = env.object(8, "prefix", data=b"Err: \x00", fill=0x71)
    env.put(handler, callback)
    env.put(handler + 8, 0x11112222)
    env.put(handler + 0xC, kind)
    env.put(handler + 0x14, prefix)
    around = [(owner - 0x40, 0x4001, 0x11), (owner + 0x40, 0x4003, 0x33)]
    if found:
        around.append((owner, env.stub("table-message", "cdecl", 2, returns(0x62)), 0x22))
    write_table_signed(env, around, 0x66000000)


def put_messages(env):
    for address, text in ((MSG_MEMORY, b"Memory failed\x00"), (MSG_NULL, b"Null given\x00"), (MSG_BAD, b"Bad value given\x00")):
        env.put(address, env.object(len(text) + 8, "message", data=text + b"\x00" * 8, fill=0x72))


ERROR_KINDS = ((0, False), (3, True), (4, False), (4, True), (1, False), (1, True), (2, False), (2, True))


def sizes_cases(random_source):
    sizes = (0x20, 0x40, 0x60, 0x80, 0x100, 0x120, 0x1E0)
    for this_bits in sizes:
        for source_bits in sizes:
            seed = random_source.randrange(0, 1000)

            def setup(env, this_bits=this_bits, source_bits=source_bits, seed=seed):
                handler = env.object(0x20, "handler", fill=0x5C)
                target, target_buffer = make_set(env, handler, this_bits, seed, "target")
                source, source_buffer = make_set(env, handler, source_bits, seed + 50, "source")
                env.put(MSG_MEMORY, env.object(8, "message", data=b"Memory\x00", fill=0x72))
                return {"target": target, "source": source}

            yield Case(f"assign {this_bits:#x} bits from {source_bits:#x} bits", ASSIGN, setup,
                       receiver=lambda tokens: tokens["target"], arguments=(lambda tokens: tokens["source"],))
    for bits in (0x20, 0x60, 0x100):
        def setup(env, bits=bits):
            handler = env.object(0x20, "handler", fill=0x5C)
            target, _ = make_set(env, handler, bits, 17, "target")
            return {"target": target}

        yield Case(f"assign {bits:#x} bits to itself", ASSIGN, setup, receiver=lambda tokens: tokens["target"],
                   arguments=(lambda tokens: tokens["target"],))
    for _ in range(24):
        this_bits = 32 * random_source.randrange(1, 40)
        source_bits = 32 * random_source.randrange(1, 40)
        seed = random_source.randrange(0, 100000)

        def setup(env, this_bits=this_bits, source_bits=source_bits, seed=seed):
            handler = env.object(0x20, "handler", fill=0x5C)
            target, _ = make_set(env, handler, this_bits, seed, "target")
            source, _ = make_set(env, handler, source_bits, seed + 7, "source")
            return {"target": target, "source": source}

        yield Case(f"assign random {this_bits:#x} from {source_bits:#x}", ASSIGN, setup,
                   receiver=lambda tokens: tokens["target"], arguments=(lambda tokens: tokens["source"],))


def resize_cases(random_source):
    counts = [0, 1, 2, 31, 0x1F, 0x20, 0x21, 0x22, 0x3F, 0x40, 0x41, 0x5F, 0x60, 0x61, 0x7F, 0x80, 0x81, 0xA0, 0xE1,
              0x100, 0x3E7, 0x400, 0x401, 0x1000, 0x1021]
    counts += [random_source.randrange(0x21, 6000) for _ in range(20)]
    for bits in counts:
        fill = random_source.randrange(1, 255)

        def setup(env, fill=fill):
            owner = env.object(OWNER_SIZE, "owner", words=[VTABLE_B, 0x1234, 0x5678, 0x9ABC], fill=0x2D)
            env.override(MALLOC, filled_malloc(fill))
            return {"owner": owner}

        yield Case(f"resize to {bits:#x} bits", RESIZE, setup, receiver=lambda tokens: tokens["owner"], arguments=(bits,))
    for bits in (0x21, 0x40, 0x100, 0x3E7):
        def setup(env):
            owner = env.object(OWNER_SIZE, "owner", words=[VTABLE_B, 0x1234, 0x5678, 0x9ABC], fill=0x2D)
            env.override(MALLOC, allocate(fail=True))
            return {"owner": owner}

        yield Case(f"resize to {bits:#x} bits, malloc fails", RESIZE, setup, receiver=lambda tokens: tokens["owner"],
                   arguments=(bits,))


# ---------------------------------------------------------------- default constructor (0x4dc180)

def default_ctor_cases(random_source):
    defaults = [0, 1, 0x1F, 0x20, 0x21, 0x40, 0x41, 100, 0x3E7, 0x1000] + [random_source.randrange(0x21, 5000) for _ in range(6)]
    for bits in defaults:
        for custom_messages in (False, True):
            def setup(env, bits=bits, custom=custom_messages):
                owner = env.object(OWNER_SIZE, "owner", words=[0x1357, 0x2468, 0x3579, 0x468A, 0x579B], fill=0x2D)
                env.put(DEFAULT_BITS, bits)
                if custom:
                    put_messages(env)
                env.override(MALLOC, filled_malloc(0x3B))
                return {"owner": owner}

            yield Case(f"default constructor, default size {bits:#x}{', own messages' if custom_messages else ''}",
                       DEFAULT_CTOR, setup, receiver=lambda tokens: tokens["owner"])


# ---------------------------------------------------------------- constructor from text (0x4dbe10)

VALID_TEXTS = [
    "", " ", "   ", "\t \t", "0", "5", "31", "32", "33", "63", "64", "65", "127", "128", "200", "1000",
    "1,2,3", "1,2", "3,1,2", "1-5", "0-3", "5-1", "3-3", "2-2,9", "1 , 3 - 7", "1 ,3", "1, 3", "1 -3", "1- 3",
    " 4 5 6", "1 2", "1 2 3 4 5", "10-20,30", "1-3-6", "3-", "3 -", "1,2,", "1,2 ,", "7  ,  9", "0-31", "0-32",
    "0-33", "28-34", "100 - 105, 3", "  12  -  14  ", "5,5,5", "9-3,1", "9-3 ,1", "4,3-1,8",
    "\t5", "2,", "12", "7-12,40-45", "60-70", "30,31", "31-2", "17,2-9,40", "10-9", "10-10", "6 -2", "0,1,2,3-4,5",
    "1 - 3 5", "1-3 5,7", "2-4 7-9", "5,", "8 - 9 - 11", "3,6-", "9 14 ", "9 14 20 ",
]
INVALID_TEXTS = ["@;4", "@,,4", "@--4", "@, ,4", "@ ,, 4", "@- -4", "@	4", "@x", "4 @ x", "@.5", "4,@;"]
NUMBER = re.compile(r"\d+")


def text_footprint(text, bits, default):
    if "@" in text:
        return True
    """True when every number in the text addresses a bit that exists in the final set."""
    numbers = [int(n) for n in NUMBER.findall(text)]
    biggest = max(numbers) if numbers else 0
    size = max(bits or default, biggest)
    if size <= 0x20:
        return biggest < 128  # the inline word sits at the end of a padded owner
    return biggest < ((size + 31) // 32) * 32


def text_setup(text, bits, default, own_messages=True, fill=0x3B, kind=None, found=False, fail=False, null=False,
               entry_frame=None):
    def setup(env):
        if entry_frame is not None:
            elect_frame(env, entry_frame)
        owner = env.object(OWNER_SIZE, "owner", words=[0x1357, 0x2468, 0x3579, 0x468A, 0x579B, 0x68AC, 0x79BD], fill=0x2D)
        env.put(DEFAULT_BITS, default)
        if own_messages:
            put_messages(env)
        if kind is not None:
            install_handler(env, GLOBAL_HANDLER, kind, owner, found)
        env.override(MALLOC, allocate(fail=True) if fail else filled_malloc(fill))
        # the original can read a few bytes past the terminator of a text with an odd tail; keep them zero
        if "@" in text:
            # 0x4dc680 reads [ebp+4]; in 0x4dbe10 EBP holds the last number parsed, so the text names a backed word
            frame = env.object(16, "frame", words=[0x71717171, 0x72727272, 0x73737373, 0x74747474], fill=0x75)
            shown = text.replace("@", str(frame - 4))
        else:
            shown = text
        raw = shown.encode("latin-1") + b"\x00" * 8
        string = 0 if null else env.object(len(raw), "text", data=raw, fill=0)
        return {"owner": owner, "string": string}
    return setup


def text_case(label, text, bits, default, **options):
    return Case(label, FROM_TEXT, text_setup(text, bits, default, **options),
                receiver=lambda tokens: tokens["owner"], arguments=(lambda tokens: tokens["string"], bits))


def text_cases(random_source):
    combos = ((0, 0x20), (0, 0x45), (8, 0x20), (200, 0x30), (0x40, 0x20))
    for index, text in enumerate(VALID_TEXTS):
        for bits, default in (combos[index % 5], combos[(index + 2) % 5]):
            if not text_footprint(text, bits, default):
                bits, default = 200, 0x30
            if text_footprint(text, bits, default):
                yield text_case(f"text {text!r} bits {bits} default {default:#x}", text, bits, default,
                                own_messages=(index % 2 == 0), fill=random_source.randrange(1, 255))
    # Error reports. Every one reaches 0x4dc680, which reads [ebp+4]; EBP is the last number parsed ("@" is an
    # address-4 number). Reports whose EBP is still the caller's (null text, non-digit start, allocation failure
    # for an empty text) are in caller_frame_cases, which elects the entry frame.
    for text in INVALID_TEXTS:
        for bits, default in ((0, 0x20), (200, 0x30)):
            yield text_case(f"invalid text {text!r} bits {bits}", text, bits, default)
    reasons = (("bad separator", dict(text="@;4"), 0), ("separator twice", dict(text="@,,4"), 0),
               ("allocation fails (single number)", dict(text="@", fail=True), 0),
               ("allocation fails (inline size)", dict(text="3,@", fail=True), 8),
               ("allocation fails (range)", dict(text="2-@", fail=True), 100))
    for name, options, bits in reasons:
        rest = {key: value for key, value in options.items() if key != "text"}
        for kind, found in ERROR_KINDS:
            yield text_case(f"error {name}: handler kind {kind} found={found}", options["text"], bits, 0x20,
                            kind=kind, found=found, **rest)
        yield text_case(f"error {name}: initialised default messages", options["text"], bits, 0x20,
                        own_messages=False, **rest)
    # random valid texts
    for _ in range(40):
        limit = random_source.choice((10, 40, 100, 400))
        text = " " * random_source.randrange(0, 3) + str(random_source.randrange(0, limit))
        for _ in range(random_source.randrange(0, 6)):
            separator = random_source.choice((",", "-", " ", " , ", " - ", ", ", " ,", "  ", ",", "-", "-"))
            text += separator + str(random_source.randrange(0, limit))
        if random_source.random() < 0.3:
            text += random_source.choice((",", " ", "-", " , "))
        bits = random_source.choice((0, 0, 8, 100, 250))
        default = random_source.choice((0x20, 0x21, 0x50, 300))
        if text_footprint(text, bits, default):
            yield text_case(f"random text {text!r} bits {bits} default {default:#x}", text, bits, default,
                            own_messages=random_source.random() < 0.5, fill=random_source.randrange(1, 255))


# ---------------------------------------------------------------- error reports with the caller's EBP

def assign_failure_cases(random_source):
    """0x4dbd60: the source needs a buffer and malloc fails; every handler kind, found or not."""
    for this_bits, source_bits in ((0x20, 0x21), (0x80, 0x140), (0x60, 0x40)):
        for kind, found in ERROR_KINDS:
            seed = random_source.randrange(0, 1000)
            words = new_frame(random_source)

            def setup(env, this_bits=this_bits, source_bits=source_bits, kind=kind, found=found, seed=seed, words=words):
                handler = env.object(0x20, "handler", fill=0x5C)
                target, _ = make_set(env, handler, this_bits, seed, "target")
                source, _ = make_set(env, handler, source_bits, seed + 50, "source")
                put_messages(env)
                install_handler(env, handler, kind, target, found)
                env.override(MALLOC, allocate(fail=True))
                elect_frame(env, words)
                return {"target": target, "source": source}

            yield Case(f"assign {this_bits:#x} from {source_bits:#x}, malloc fails, handler kind {kind} found={found}",
                       ASSIGN, setup, receiver=lambda tokens: tokens["target"], arguments=(lambda tokens: tokens["source"],))
    for _ in range(6):
        this_bits = 32 * random_source.randrange(1, 40)
        source_bits = 32 * random_source.choice([n for n in range(2, 40) if n * 32 != this_bits])
        kind, found = random_source.choice(ERROR_KINDS)
        seed = random_source.randrange(0, 100000)
        words = new_frame(random_source)

        def setup(env, this_bits=this_bits, source_bits=source_bits, kind=kind, found=found, seed=seed, words=words):
            handler = env.object(0x20, "handler", fill=0x5C)
            target, _ = make_set(env, handler, this_bits, seed, "target")
            source, _ = make_set(env, handler, source_bits, seed + 7, "source")
            put_messages(env)
            install_handler(env, handler, kind, target, found)
            env.override(MALLOC, allocate(fail=True))
            elect_frame(env, words)
            return {"target": target, "source": source}

        yield Case(f"assign random {this_bits:#x} from {source_bits:#x}, malloc fails, kind {kind} found={found}",
                   ASSIGN, setup, receiver=lambda tokens: tokens["target"], arguments=(lambda tokens: tokens["source"],))


def default_failure_cases(random_source):
    """0x4dc180: the default size needs a buffer and malloc fails."""
    for bits in (0x21, 0x100, random_source.randrange(0x22, 5000)):
        for kind, found in ERROR_KINDS:
            words = new_frame(random_source)

            def setup(env, bits=bits, kind=kind, found=found, words=words):
                owner = env.object(OWNER_SIZE, "owner", words=[0x1357, 0x2468, 0x3579, 0x468A, 0x579B], fill=0x2D)
                env.put(DEFAULT_BITS, bits)
                put_messages(env)
                install_handler(env, GLOBAL_HANDLER, kind, owner, found)
                env.override(MALLOC, allocate(fail=True))
                elect_frame(env, words)
                return {"owner": owner}

            yield Case(f"default constructor, size {bits:#x}, malloc fails, handler kind {kind} found={found}",
                       DEFAULT_CTOR, setup, receiver=lambda tokens: tokens["owner"])
    for bits in (0x21, 0x3E7):
        words = new_frame(random_source)

        def setup(env, bits=bits, words=words):
            owner = env.object(OWNER_SIZE, "owner", words=[0x1357, 0x2468, 0x3579, 0x468A, 0x579B], fill=0x2D)
            env.put(DEFAULT_BITS, bits)
            env.override(MALLOC, allocate(fail=True))
            elect_frame(env, words)
            return {"owner": owner}

        yield Case(f"default constructor, size {bits:#x}, malloc fails, initialised default messages",
                   DEFAULT_CTOR, setup, receiver=lambda tokens: tokens["owner"])


NON_DIGIT_STARTS = ["x", "abc", "-3", ",4", ";", "+5", "  x1", "\t,5", " -", ".", "-", "#"]
EMPTY_TEXTS = ["", "   ", "\t", " \t "]


def caller_frame_cases(random_source):
    """0x4dbe10 error reports reached while EBP is still the caller's: null text, non-digit start, empty text
    whose resize fails. Each site is reached by construction, not by chance."""
    # null text
    for kind, found in ERROR_KINDS:
        yield text_case(f"null text: handler kind {kind} found={found}", "", 0, 0x20, null=True, kind=kind,
                        found=found, entry_frame=new_frame(random_source))
    for bits, default in ((0, 0x45), (200, 0x30), (8, 0x21)):
        yield text_case(f"null text: bits {bits} default {default:#x}", "", bits, default, null=True,
                        entry_frame=new_frame(random_source), fill=random_source.randrange(1, 255))
    yield text_case("null text: initialised default messages", "", 0, 0x20, null=True, own_messages=False,
                    entry_frame=new_frame(random_source))
    # non-digit start
    for kind, found in ERROR_KINDS:
        yield text_case(f"non-digit start 'x': handler kind {kind} found={found}", "x", 0, 0x20, kind=kind,
                        found=found, entry_frame=new_frame(random_source))
    for text in NON_DIGIT_STARTS:
        for bits, default in ((0, 0x20), (200, 0x30), (8, 0x45)):
            yield text_case(f"non-digit start {text!r} bits {bits} default {default:#x}", text, bits, default,
                            own_messages=random_source.random() < 0.5, fill=random_source.randrange(1, 255),
                            entry_frame=new_frame(random_source))
    yield text_case("non-digit start 'x': initialised default messages", "x", 0, 0x20, own_messages=False,
                    entry_frame=new_frame(random_source))
    # empty or blank text: the resize to the default or given size fails
    for kind, found in ERROR_KINDS:
        yield text_case(f"empty text, resize fails: handler kind {kind} found={found}", "", 0, 0x21, fail=True,
                        kind=kind, found=found, entry_frame=new_frame(random_source))
    for text in EMPTY_TEXTS:
        for bits, default in ((0, 0x21), (0, 0x100), (0x40, 0x20), (200, 0x30)):
            yield text_case(f"blank text {text!r}, resize fails, bits {bits} default {default:#x}", text, bits,
                            default, fail=True, own_messages=random_source.random() < 0.5,
                            entry_frame=new_frame(random_source))
    yield text_case("empty text, resize fails: initialised default messages", "", 0, 0x21, fail=True,
                    own_messages=False, entry_frame=new_frame(random_source))


def cases(random_source):
    yield from registry_cases(random_source)
    yield from remove_owner_cases(random_source)
    yield from sizes_cases(random_source)
    yield from resize_cases(random_source)
    yield from default_ctor_cases(random_source)
    yield from text_cases(random_source)
    yield from assign_failure_cases(random_source)
    yield from default_failure_cases(random_source)
    yield from caller_frame_cases(random_source)
