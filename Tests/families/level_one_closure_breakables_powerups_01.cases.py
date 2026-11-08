"""Cases for level_one_closure_breakables_powerups_01: Level 1 closure: breakables, bouncing goodie, Magic and Super powerups."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, release, returns  # noqa: F401

M32 = 0xFFFFFFFF
OPERATOR_NEW = 0x4F63EC
MALLOC = 0x4A48E0
G_TREE = 0x537668
G_NIL_STRING = 0x52E1C8
G_INTERLOCKED_DECREMENT = 0x5469E8   # import slot of KERNEL32 InterlockedDecrement, read by 0x4f6584
G_STEP = 0x5430C4
G_COUNT = 0x52A190
G_SEEDED = 0x538418
G_GLOBAL_OBJECT = 0x5371FC
G_CLOCK = 0x537210
G_SOUND_FLAG = 0x532C0C
G_LEVEL_POINTER = 0x537960   # read by 0x4719e0: bit 0 and the value 13 select extra lookups
ACTOR_INIT_SLOT = 0x5137F0 + 0x28     # vtable written by the actor factory 0x4c8be0

# the string tables 0x4719e0 fills, by the registry that the lookups go to
KEYS_TABLE = [0x5279b8, 0x52a68c, 0x52a668, 0x52a64c, 0x52a630, 0x52a614, 0x52a5ec, 0x526058, 0x52603c, 0x526020,
              0x526000, 0x5260d0, 0x5260b0, 0x526094, 0x526074, 0x526140, 0x526124, 0x526108, 0x5260ec, 0x52a59c,
              0x52a58c, 0x52a578, 0x52a554, 0x52a540, 0x52a520, 0x52a500, 0x52a4ec, 0x52a4d8, 0x52a4c8, 0x52a4b4,
              0x52418c, 0x52a1e0, 0x524d1c, 0x52a07c, 0x5235d0, 0x52a494, 0x52a474, 0x52a454, 0x52a434, 0x52a410,
              0x52a3f0, 0x525fe4, 0x525fc4, 0x525fa8, 0x525f88, 0x52a3d4, 0x52a3b8, 0x52a39c, 0x52a380, 0x52a360,
              0x52a33c, 0x52a31c, 0x52a2f8, 0x52a2e4, 0x52a2c8, 0x52a1ec, 0x52a2a0, 0x52a280, 0x52a268, 0x52a24c,
              0x52a23c]
KEYS_TREASURE = [0x5228c0, 0x522894, 0x522960, 0x5228b0, 0x52293c, 0x52292c, 0x522864]
KEYS_COIN = [0x52a6b4, 0x52a6a4, 0x52a680, 0x52a604, 0x52a5e0, 0x52a5d0, 0x52a5c0, 0x52a5b0, 0x52a568, 0x52a530,
             0x52a514, 0x52a204, 0x52a4a8, 0x52a488, 0x52a468, 0x52a448, 0x52a428, 0x52a404, 0x52a2b8]

STRING_POWERUP = 0x52A198      # "GAME_POWERUP", looked up by 0x4c79e0
STRING_GLITTER = 0x522950      # "PowerupGlitter", looked up by the actor factory

TREE_MODES = ("match", "empty", "mismatch", "short", "long", "null", "deep", "far")


def words_of(random_source, count):
    return [random_source.randrange(1, 1 << 32) for _ in range(count)]


def observe(env, log, tag, call, with_receiver=False, extra=()):
    """Append one row to a case log: the call a stand-in saw, as surviving case memory."""
    count = env.get(log)
    env.put(log, count + 1)
    row = log + 4 + count * 40
    words = [tag, call.receiver if with_receiver else 0] + list(call.arguments)[:6] + list(extra)
    env.put(row, *words[:10])
    return 0


def new_log(env):
    return env.object(0x2000, "case-log", fill=0)


def key_hash(name):
    value = 0
    for byte in name:
        value = (value * 0x21 + (byte - 256 if byte > 127 else byte)) & M32
    return value


def make_registry(env, random_source, entries, buckets):
    """The string table behind 0x4f6286, embedded at owner+0x10: +4 buckets, +8 count, nodes [next, ?, key, value].
    Every key also gets a decoy node with a near-miss key so a wrong string compare finds the wrong value."""
    owner = env.object(0x40, "registry-owner", words=words_of(random_source, 0x10))
    table = owner + 0x10
    array = env.object(4 * buckets, "registry-buckets", fill=0)
    env.put(table + 4, array, buckets)
    for name, value in entries.items():
        key = env.object(len(name) + 4, "registry-key", data=name + b"\0")
        decoy_key = env.object(len(name) + 8, "decoy-key", data=name + b"X\0")
        index = key_hash(name) % buckets
        node = env.object(16, "registry-node", words=[env.get(array + 4 * index), 0, key, value])
        decoy = env.object(16, "registry-decoy", words=[node, 0, decoy_key, value ^ 0xFFFF])
        env.put(array + 4 * index, decoy if random_source.random() < 0.5 else node)
    return owner


def install_tree(env, random_source, mode, key):
    """The tree behind 0x4dba00(&0x537668, key); the root pointer lives at 0x537680."""
    if mode == "empty":
        env.put(G_TREE + 0x18, 0)
        return 0
    value = random_source.randrange(1, 1 << 32)
    stored = {"mismatch": key[:-1] + b"X\0", "short": key[:3] + b"\0", "long": key + b"2\0"}.get(mode, key + b"\0")
    keyobj = env.object(16, "tree-key", data=stored)
    root = env.object(0x20, "tree-root", words=words_of(random_source, 8))
    node = env.object(0x20, "tree-node", words=words_of(random_source, 8))
    env.put(root, root, root, 0, keyobj, value)
    if mode == "null":
        env.put(root, 0, 0)
    elif mode == "deep":
        env.put(root, node, node)
        env.put(node, node, root, 3, keyobj, value ^ 0x55555555)
    elif mode == "far":
        env.put(root + 8, 100)
    env.put(G_TREE + 0x18, root)
    return value


# ----------------------------------------------------------------------------------------------
# the breakable / powerup logic object behind 0x46f5b0 .. 0x46fc90 and 0x404f30 .. 0x40f390
LOGIC_SIZE = 0x3E8


def logic_world(env, r, *, size_bits=0x20, tree=None, tree_key=None, slot=True, depth=0x20, m_alias=False,
                last_bit_clear=False, sound_flag=None, u3b0=0, u3ac=0, pointer_word=True, strings=None):
    """L: the logic object. +0x0c actor A (+0x74 B with +0xd0 = depth), +0x10 service S, +0x12c M, +0x2f4 a bit set
    (+0x2fc size, +0x300 inline word or pointer), strings at +0x1a4 / +0x1a8 are the empty string."""
    log = new_log(env)
    logic = env.object(LOGIC_SIZE, "logic", words=words_of(r, LOGIC_SIZE // 4))
    actor = env.object(0x1C0, "actor", words=words_of(r, 0x70))
    other = env.object(0x100, "actor-part", words=words_of(r, 0x40))
    service = env.object(0x180, "service", words=words_of(r, 0x60))
    monster = env.object(0x1A0, "monster", words=words_of(r, 0x68))
    vtable = env.object(0x100, "logic-vtable", words=words_of(r, 0x40))
    vtable2 = env.object(0x100, "logic-vtable-2", words=words_of(r, 0x40))
    extra = lambda e: (e.get(logic + 0x304), e.get(logic + 0x300), e.get(logic + 0x2FC), e.get(logic + 0x24))
    env.put(vtable + 0x7C, env.stub("logic-slot-7c", "thiscall", 0,
                                    lambda e, c: observe(e, log, 0x7C, c, True, extra(e)) or 1))
    env.put(vtable2 + 0x7C, env.stub("logic-slot-7c-second", "thiscall", 0,
                                     lambda e, c: observe(e, log, 0x7D, c, True, extra(e)) or 2))
    env.put(logic, vtable)
    env.put(logic + 0x0C, actor)
    env.put(logic + 0x10, service)
    env.put(logic + 0x12C, other if m_alias else monster)
    env.put(actor + 0x74, other)
    env.put(other + 0xD0, depth & M32)
    env.put(other + 0x08, r.randrange(0, M32) & ~0x10000)
    env.put(monster + 0x08, r.randrange(0, M32) & ~4)
    nil = env.get(G_NIL_STRING) + 0xC
    env.put(logic + 0x1A4, nil)
    env.put(logic + 0x1A8, nil)
    if strings is not None:
        # reference-counted strings: the count sits 0xc before the characters; a count of 1 is released
        # by 0x4f6584 through operator delete, so the order of the three teardown calls shows in the delete sequence
        def decrement(e, call):
            value = (e.get(call.arguments[0]) - 1) & M32
            e.put(call.arguments[0], value)
            return value
        env.override(G_INTERLOCKED_DECREMENT, decrement)
        for offset, count in zip((0x1A4, 0x1A8), strings):
            header = env.object(0x20, "string-header", words=words_of(r, 8))
            env.put(header, count & M32)
            env.put(logic + offset, header + 0xC)
    env.put(logic + 0x2FC, size_bits & M32)
    if size_bits > 0x20:
        block = env.object(8 * 4, "bit-block", words=words_of(r, 8))
        env.put(logic + 0x300, block)
    elif last_bit_clear:
        env.put(logic + 0x300, r.randrange(0, M32) & ~0x10)
    if tree is not None:
        install_tree(env, r, tree, tree_key)
    env.put(logic + 0x3B0, u3b0)
    env.put(logic + 0x3AC, u3ac)
    if sound_flag is not None:
        env.put(G_SOUND_FLAG, sound_flag)
    env.put(G_CLOCK, r.randrange(1, 1 << 30))
    return {"L": logic, "log": log, "A": actor, "B": other, "S": service, "M": monster, "V2": vtable2, "bits": logic + 0x2F4}


def logic_setup(r, **options):
    return lambda env: logic_world(env, r, **options)


def destructor_cases(r):
    for function in (0x46F5D0, 0x404F50):
        for bits in (0, 1, 4, 5, 0x1F, 0x20, 0x21, 0x40, 0x7FFFFFFF, M32, 0x80000000):
            yield Case(f"destructor {function:#x} bits {bits:#x}", function, logic_setup(r, size_bits=bits),
                       receiver=lambda t: t["L"])
        # distinct released strings at +0x1a4 / +0x1a8 and a released bit block at +0x2f4: the three
        # teardown calls each free a different block, so their order is part of the recorded sequence
        for bits in (0x21, 0x40, 0x100, 0x7FFFFFFF):
            for counts in ((1, 1), (1, 2), (2, 1), (0, 0), (2, 2)):
                yield Case(f"destructor {function:#x} strings {counts} bits {bits:#x}", function,
                           logic_setup(r, size_bits=bits, strings=counts), receiver=lambda t: t["L"])
        for _ in range(4):
            yield Case(f"destructor {function:#x} random bits", function, logic_setup(r, size_bits=r.choice((3, 9, 0x22, 0x100))),
                       receiver=lambda t: t["L"])


def scalar_cases(r):
    flags = (0, 1, 2, 3, 0x80000000, 0x80000001, 0xFFFFFFFE, M32, 0x100, 0x101)
    for function in (0x46F5B0, 0x404F30):
        for flag in flags:
            for bits in (0x10, 0x21):
                yield Case(f"scalar destructor {function:#x} flags {flag:#x} bits {bits:#x}", function,
                           logic_setup(r, size_bits=bits), receiver=lambda t: t["L"], arguments=(flag,))
        for flag in (1, 3, 0x101):
            yield Case(f"scalar destructor {function:#x} strings flags {flag:#x}", function,
                       logic_setup(r, size_bits=0x40, strings=(1, 1)), receiver=lambda t: t["L"], arguments=(flag,))
        for _ in range(4):
            yield Case(f"scalar destructor {function:#x} random flags", function, logic_setup(r, size_bits=r.choice((2, 0x30))),
                       receiver=lambda t: t["L"], arguments=(r.randrange(0, M32),))


def enter_cases(r):
    # 0x46fbe0 and 0x40f390 look the pacing record up in the tree; the key differs per function
    for function, key_address in ((0x46FBE0, 0x5271B4), (0x40F390, 0x5234F4)):
        for mode in TREE_MODES:
            for _ in range(2):
                def setup(env, mode=mode, key_address=key_address):
                    return logic_world(env, r, tree=mode, tree_key=env.cstr(key_address))
                yield Case(f"enter {function:#x} tree {mode}", function, setup, receiver=lambda t: t["L"])


def monster_cases(r):
    for depth in (0x20, 0x1F, 0x21, 0, 0x120, M32, 0x2000, r.randrange(0x22, 0x1000)):
        for alias in (False, True):
            yield Case(f"monster flags 0x46fc60 depth {depth:#x} alias {alias}", 0x46FC60,
                       logic_setup(r, depth=depth, m_alias=alias), receiver=lambda t: t["L"])


def mode_cases(r):
    # 0x46fc90 with argument 2 depends on the bit set size; the other arguments go to 0x43f120
    for bits in (0, 1, 3, 4, 5, 6, 0x10, 0x1F, 0x20, 0x21, 0x22, 0x40, 0x7FFFFFFF, M32):
        for clear in (False, True):
            if bits in (5, 0x20, 0x21, 0x1F) or not clear:
                yield Case(f"mode two bits {bits:#x} clear {clear}", 0x46FC90,
                           logic_setup(r, size_bits=bits, last_bit_clear=clear),
                           receiver=lambda t: t["L"], arguments=(2,))
    for bits in (0, 2, 4):
        def setup(env, bits=bits):
            tokens = logic_world(env, r, size_bits=bits)
            vtable2 = tokens["V2"]

            def swap(e, call):
                e.put(tokens["L"], vtable2)
                return e.object(call.arguments[0], name="allocation")
            env.override(MALLOC, swap)
            return tokens
        yield Case(f"mode two, vtable replaced during the allocation, bits {bits}", 0x46FC90, setup,
                   receiver=lambda t: t["L"], arguments=(2,))
    for argument in (1, 3, 4, 5, 7, 0x80000000, M32, 0x102):
        for bits in (0, 4, 5, 0x20, 0x40):
            for tree in ("match", "empty"):
                if r.random() < 0.5:
                    continue

                def setup(env, bits=bits, tree=tree):
                    return logic_world(env, r, size_bits=bits, tree=tree, tree_key=env.cstr(0x5234F4),
                                       u3b0=r.choice((0, 0x1234)), u3ac=r.choice((0, 0x1234)), sound_flag=0)
                yield Case(f"mode {argument:#x} bits {bits:#x} tree {tree}", 0x46FC90, setup,
                           receiver=lambda t: t["L"], arguments=(argument,))


# ----------------------------------------------------------------------------------------------
# the powerup actor logic 0x470f00 (Magic) and 0x471330 (Super)
def scene_world(env, r, queue=()):
    """The scene behind 0x4c8da0: +0x0c context (+0x08 scene, +0x14 registry), +0x14 actor list, +0x20 node pool."""
    scene = env.object(0x40, "scene", fill=0)
    context = env.object(0x40, "context", fill=0)
    env.put(scene + 0x0C, context)
    env.put(context + 0x08, scene)
    pool = env.object(64 * 12, "list-node-pool", fill=0)
    for index in range(63):
        env.put(pool + index * 12, pool + (index + 1) * 12)
    env.put(scene + 0x20, pool)
    env.put(scene + 0x28, 64)
    actors, nodes = [], []
    for index, (priority, flags) in enumerate(queue):
        queued = env.object(0x1B4, f"queued-actor-{index}", fill=0x63 + index)
        node = env.object(12, f"queued-node-{index}", fill=0)
        env.put(queued + 8, flags)
        env.put(queued + 0x64, priority & M32, node, 0)
        actors.append(queued)
        nodes.append(node)
    for index, node in enumerate(nodes):
        env.put(node, nodes[index + 1] if index + 1 < len(nodes) else 0, nodes[index - 1] if index else 0, actors[index])
    env.put(scene + 0x14, nodes[0] if nodes else 0, nodes[-1] if nodes else 0, len(nodes))
    return scene, context


def animation_resource(env, r, frames=3):
    """What 0x4c8220 binds: +0x10 frame count, +0x0c frame table; frame 0 has a word at +0x1c."""
    table = env.object(4 * frames, "anim-frames", words=[env.object(0x40, "anim-frame", words=words_of(r, 0x10)) for _ in range(frames)])
    return env.object(0x40, "anim-resource", words=[*words_of(r, 3), table, frames, *words_of(r, 11)])


def pick_level(r):
    return r.choice((0, 1, 0xD, 0xC, 0xF, 2))


def power_world(env, r, *, function, state=0, p64=0, p190=0, found=True, frame=True, seeded=True, count=8, match=None,
                duplicate=False, beyond=False, g124=1, factory="ok", queue=(), anim="none", c8=True, step=3,
                registry_hit=0.6):
    log = new_log(env)
    world = env.object(0x40, "world", words=words_of(r, 0x10))
    scene, context = scene_world(env, r, queue)
    env.put(world + 0x08, scene)
    metadata = env.object(0x18, "powerup-metadata", fill=0)
    glitter = env.cstr(STRING_GLITTER)
    env.put(context + 0x14, make_registry(env, r, {glitter: metadata} if factory != "miss" else {}, r.choice((3, 5, 7))))
    powerup_key = env.cstr(STRING_POWERUP)
    env.put(world + 0x2C, make_registry(env, r, {powerup_key: animation_resource(env, r)} if found else {}, r.choice((3, 5, 7))))
    values = {}
    if seeded:
        env.put(G_SEEDED, r.randrange(1, M32))
        keys = []
        for index in range(0x42):
            keys.append(r.randrange(1, M32))
        env.put(0x537EC8, *keys)
        env.put(0x537FD0, *words_of(r, 0x42))
        env.put(0x538310, *words_of(r, 0x42))
        env.put(0x5380D8, *words_of(r, 0x42))
        env.put(G_COUNT, count)
        if match is not None:
            if beyond:
                match_key = keys[count] if count < 0x42 else r.randrange(1, M32)
            else:
                match_key = keys[match]
                if duplicate:
                    for later in range(match + 1, count):
                        keys[later] = match_key
                    env.put(0x537EC8, *keys)
        else:
            match_key = r.randrange(1, M32)
    else:
        env.put(G_SEEDED, 0)
        env.put(G_LEVEL_POINTER, env.object(8, "level-state", words=[pick_level(r), r.randrange(1, M32)]))
        env.put(G_COUNT, r.randrange(0, 100))
        tables = {}
        for registry_offset, names in ((0x10, KEYS_TABLE), (0x14, KEYS_TREASURE), (0x28, KEYS_COIN)):
            entries = {}
            for address in names:
                if r.random() < registry_hit:
                    value = r.randrange(1, M32)
                    entries[env.cstr(address)] = value
                    tables.setdefault(registry_offset, []).append(value)
            env.put(world + registry_offset, make_registry(env, r, entries, r.choice((5, 7, 11))))
        found_values = tables.get(0x10, [])
        if match is None or not found_values:
            match_key = r.choice((0, r.randrange(1, M32)))
        else:
            match_key = found_values[match % len(found_values)]
    service = env.object(0x180, "service", words=words_of(r, 0x60))
    env.put(service + 0x1C, state)
    actor = env.object(0x1C0, "actor", words=words_of(r, 0x70))
    env.put(actor + 0x0C, world)
    env.put(actor + 0x6C, service)
    env.put(actor + 0x64, p64)
    env.put(actor + 0x190, p190)
    env.put(actor + 0x170, match_key)
    env.put(actor + 0x174, env.object(0x40, "current-frame", words=words_of(r, 0x10)) if frame else 0)
    env.put(actor + 0x08, r.randrange(0, 1 << 32))
    env.put(actor + 0xC8, env.object(0x40, "glitter-actor", words=words_of(r, 0x10)) if c8 else 0)
    env.put(G_STEP, step, r.randrange(1, M32))
    shared = env.object(0x140, "shared-object", words=words_of(r, 0x50))
    env.put(shared + 0x124, g124)
    env.put(G_GLOBAL_OBJECT, shared)
    base = actor + 0x188
    if anim == "none":
        env.put(base + 8, 0)
    elif anim == "hold":
        env.put(base + 8, r.randrange(1, M32))
        env.put(base + 0x14, 9 + step)
        env.put(base + 0x18, 0)
    elif anim == "slow":
        env.put(base + 8, r.randrange(1, M32))
        env.put(base + 0x14, step + 5)
        env.put(base + 0x18, 1)

    def init(e, call):
        receiver = call.receiver
        service_of_new = e.get(receiver + 0x6C)
        x, y, priority, meta = call.arguments
        e.put(receiver + 0x4C, x, y)
        e.put(receiver + 0x64, priority)
        e.put(service_of_new + 0x10, 0x471530)
        observe(e, log, 0xC1, call, True)
        return 0 if factory == "fail" else 1
    env.put(ACTOR_INIT_SLOT, env.stub("actor-initializer", "thiscall", 4, init))
    return {"P": actor, "S": service, "log": log, "W": world}


def power_setup(r, function, **options):
    return lambda env: power_world(env, r, function=function, **options)


def power_cases(r):
    pick = r.choice
    for function in (0x470F00, 0x471330):
        def case(label, **options):
            return Case(f"{label} {function:#x}", function, power_setup(r, function, **options),
                        arguments=(lambda t: t["P"],))

        # the state selects the action
        for state in (5, 0x1D, 0x1C, 0x1E, 1, 4, 6, 0x80000000, M32, 0x15):
            for c8 in (True, False):
                for anim in ("none", "hold", "slow"):
                    if state == 5 or anim == "none":
                        yield case(f"state {state:#x} c8 {c8} anim {anim}", state=state, c8=c8, anim=anim, step=pick((1, 3, 4)))
        # initialisation, seeded tables
        for count in (0, 1, 2, 9, 0x20, 0x42):
            for match in (None, 0, 1, count - 1, count // 2):
                if match is not None and not 0 <= match < count:
                    continue
                for duplicate in (False, True):
                    if duplicate and (match is None or match + 1 >= count):
                        continue
                    yield case(f"init seeded count {count} match {match} dup {duplicate}", seeded=True, count=count,
                               match=match, duplicate=duplicate, factory="ok", p64=pick((0, 5)), g124=pick((1, 0x7777)),
                               p190=pick((0, 0, 3)), frame=pick((True, False)))
        for count in (1, 4, 0x41):
            yield case(f"init seeded no match until beyond the count {count}", seeded=True, count=count, match=0, beyond=True)
        # the pre-initialisation fields
        for p64 in (0, 1, 0x3E7, 0x3E8, M32, 0x80000000):
            for p190 in (0, 0x4444):
                for found in (True, False):
                    if p190 and not found:
                        continue
                    yield case(f"init p64 {p64:#x} p190 {p190:#x} found {found}", p64=p64, p190=p190, found=found,
                               seeded=True, count=pick((2, 5)), match=pick((None, 1)))
        for frame in (True, False):
            for found in (True, False):
                yield case(f"init frame {frame} found {found}", frame=frame, found=found, seeded=True, count=3, match=2)
        # the factory
        for g124 in (0, 1, 0x20000, M32):
            yield case(f"init factory flag {g124:#x}", g124=g124, seeded=True, count=3, match=1, p64=pick((0, 9)))
        for factory in ("ok", "miss", "fail"):
            for queue in ((), ((3, 0), (9, 0)), ((20, 0x20000),), ((0x7FFFFFFF, 0), (-1, 0)), ((1000, 0), (1001, 0x20000), (5, 0))):
                for p64 in (0, 5, 0x3E8, 0x3E7):
                    if r.random() < 0.55:
                        continue
                    yield case(f"init factory {factory} queue {queue} p64 {p64}", factory=factory, queue=queue, p64=p64,
                               seeded=True, count=3, match=pick((None, 0, 2)))
        # table filled by 0x4719e0 itself
        for _ in range(10):
            yield case("init through 0x4719e0", seeded=False, match=pick((None, 0, 1, 7, 20, 40)), p64=pick((0, 5)),
                       registry_hit=pick((0.25, 0.6, 1.0)), p190=pick((0, 9)), frame=pick((True, False)),
                       found=pick((True, False)), factory=pick(("ok", "ok", "miss", "fail")), g124=pick((0, 1)))
        for _ in range(12):
            yield case("init random", seeded=pick((True, False)), count=pick((0, 3, 0x42, 0x20)), match=pick((None, 0, 1, 2)),
                       p64=pick((0, 0, 7)), p190=pick((0, 0, 7)), found=pick((True, False)), frame=pick((True, False)),
                       factory=pick(("ok", "ok", "miss", "fail")), g124=pick((0, 1, 1)), step=pick((1, 2, 5)),
                       queue=pick(((), ((3, 0), (9, 0)), ((20, 0x20000),))), registry_hit=pick((0.3, 0.8)))


def cases(random_source):
    r = random_source
    yield from destructor_cases(r)
    yield from scalar_cases(r)
    yield from enter_cases(r)
    yield from monster_cases(r)
    yield from mode_cases(r)
    yield from power_cases(r)
