"""Cases for level_one_scene_timers_03: Level 1 scene timer and Actor storage helpers."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

F_16 = 0x4C9E20
F_E40 = 0x4C9E40
F_E50 = 0x4C9E50
F_HAS = 0x4C9FA0
F_1B = 0x4C9FB0
F_RESET = 0x4CA1B0
F_A = 0x4D3F50
F_B = 0x4D3F80
F_C = 0x4D3FC0

SLOT_FUNCTIONS = {F_A: (0x30, 2), F_B: (0x34, 3), F_C: (0x38, 3)}


def logger(env, log, tag, argc):
    """A stub that appends (tag, receiver, args...) to the log object; word 0 is the entry count."""
    def effect(env, call):
        n = env.get(log)
        base = log + 4 + n * 24
        words = [tag, call.receiver] + [call.arguments[i] for i in range(argc)]
        words += [0] * (6 - len(words))
        env.put(base, *words)
        env.put(log, n + 1)
        return 0
    return effect


def make_vtable(env, log, tag_base):
    """A vtable with distinct logging stubs in every slot, so a wrong slot shows up in the log."""
    vt = env.object(0x80, "vtable")
    for slot in range(0, 0x40, 4):
        argc = 1 if slot == 4 else (2 if slot == 0x30 else 3)
        env.put(vt + slot, env.stub(f"slot{slot:#x}-{tag_base}", "thiscall", argc, logger(env, log, tag_base + slot, argc)))
    return vt


def make_list(env, log, count, rnd, null_objects=()):
    """Linked list at head; returns (head, objects). Nodes: next@0, junk@4, obj@8."""
    nodes = [env.object(16, f"node{i}") for i in range(count)]
    objs = []
    for i, node in enumerate(nodes):
        nxt = nodes[i + 1] if i + 1 < count else 0
        if i in null_objects:
            obj = 0
        else:
            obj = env.object(16, f"obj{i}")
            env.put(obj, make_vtable(env, log, 0x1000 * (i + 1)))
            env.put(obj + 4, rnd.getrandbits(32))
        env.put(node, nxt, rnd.getrandbits(32), obj)
        objs.append(obj)
    return (nodes[0] if nodes else 0), objs


def container(count, rnd, args, null_objects=()):
    def setup(env):
        log = env.object(4 + 24 * 40, "log")
        this = env.object(0x200, "scene", fill=0)
        for off in range(0, 0x1B0, 4):
            env.put(this + off, rnd.getrandbits(32))
        head, objs = make_list(env, log, count, rnd, null_objects)
        env.put(this + 0x1B8, head)
        env.put(this + 0x1BC, rnd.getrandbits(32))
        env.put(log, 0)
        return {"this": this, "log": log, "args": args}
    return setup


def reset_object(mask, rnd, count=0, null_objects=()):
    def setup(env):
        log = env.object(4 + 24 * 40, "log")
        this = env.object(0x200, "actor", fill=0)
        for off in range(0, 0x1B0, 4):
            env.put(this + off, rnd.getrandbits(32))
        head, objs = make_list(env, log, count, rnd, null_objects)
        env.put(this + 0x1B8, head)
        env.put(this + 0x1BC, rnd.getrandbits(32))
        held = {}
        for bit, off in enumerate((0x6C, 0x70, 0x78)):
            if mask & (1 << bit):
                obj = env.object(16, f"held{off:#x}")
                env.put(obj, make_vtable(env, log, 0x100000 * (bit + 1)))
                env.put(obj + 4, rnd.getrandbits(32))
                env.put(this + off, obj)
                held[off] = obj
            else:
                env.put(this + off, 0)
        env.put(log, 0)
        return {"this": this, "log": log, "held": held}
    return setup


def cases(random_source):
    rnd = random_source

    for _ in range(3):
        yield Case("constant 0x16", F_16)
        yield Case("constant 0x1b", F_1B)

    for _ in range(6):
        a, b, c = rnd.getrandbits(32), rnd.getrandbits(32), rnd.getrandbits(32)
        yield Case("empty stdcall 2", F_E40, arguments=(a, b))
        yield Case("empty stdcall 3", F_E50, arguments=(a, b, c))

    # 0x4c9fa0: nonzero field detection, including values that a width or sign error would misjudge.
    for value in (0, 1, 0x80000000, 0xFFFFFFFF, 0x100, 0x10000, 0x01000000, 0x7FFFFFFF):
        def has_setup(env, value=value):
            this = env.object(0x80, "obj", fill=0)
            for off in range(0, 0x80, 4):
                env.put(this + off, rnd.getrandbits(32) if off != 0x6C else value)
            return {"this": this}
        yield Case(f"has object field {value:#x}", F_HAS, has_setup, receiver=lambda t: t["this"])
    for _ in range(4):
        def has_other(env):
            this = env.object(0x80, "obj", fill=0)
            env.put(this + 0x68, rnd.getrandbits(32) | 1)
            env.put(this + 0x70, rnd.getrandbits(32) | 1)
            return {"this": this}
        yield Case("has object only neighbours set", F_HAS, has_other, receiver=lambda t: t["this"])

    # 0x4ca1b0: every combination of held objects, with and without a list for the callee.
    for mask in range(8):
        for count in (0, 1, 2, 3, 5):
            nulls = ()
            yield Case(f"reset mask {mask} list {count}", F_RESET, reset_object(mask, rnd, count, nulls),
                       receiver=lambda t: t["this"])
    for mask in (0, 7, 5, 2):
        yield Case(f"reset mask {mask} list with null object", F_RESET, reset_object(mask, rnd, 3, (1,)),
                   receiver=lambda t: t["this"])
        yield Case(f"reset mask {mask} list first and last null", F_RESET, reset_object(mask, rnd, 4, (0, 3)),
                   receiver=lambda t: t["this"])
    for _ in range(20):
        mask = rnd.randrange(8)
        count = rnd.randrange(0, 7)
        nulls = tuple(i for i in range(count) if rnd.random() < 0.25)
        yield Case(f"reset random mask {mask} list {count}", F_RESET, reset_object(mask, rnd, count, nulls),
                   receiver=lambda t: t["this"])

    # Broadcast helpers: argument order, call order, empty and null-object lists.
    for function in (F_A, F_B, F_C):
        _, argc = SLOT_FUNCTIONS[function]
        for count in (0, 1, 2, 3, 6):
            for _ in range(2):
                args = tuple(rnd.getrandbits(32) | 0x01010101 for _ in range(argc))
                yield Case(f"{function:#x} list {count}", function, container(count, rnd, args),
                           receiver=lambda t: t["this"], arguments=tuple((lambda t, i=i: t["args"][i]) for i in range(argc)))
        for args in ((0,) * argc, (0xFFFFFFFF,) * argc, tuple(range(1, argc + 1))):
            yield Case(f"{function:#x} edge args {args[0]:#x}", function, container(3, rnd, args),
                       receiver=lambda t: t["this"], arguments=tuple((lambda t, i=i: t["args"][i]) for i in range(argc)))
