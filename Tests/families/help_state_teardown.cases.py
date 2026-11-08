"""Cases for help_state_teardown: Help screen state destructor."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401

DELETING_DESTRUCTOR = 0x429670
DESTRUCTOR = 0x429690


def state(random_source, game=True, size=0x60):
    """setup() for a Help state object with distinct non-zero contents.

    [S+0x2c] stays zero so the original base cleanup returns at once; [S+0xc] is a live
    object or zero and [S+0x34] holds a non-zero value the base cleanup clears.
    """
    words = [random_source.randrange(1, 1 << 32) for _ in range(size // 4)]

    def setup(env):
        s = env.object(size, "help state", words=words)
        g = env.object(0x40, "game", fill=0x5A) if game else 0
        env.put(s, 0x50C11C ^ random_source.randrange(1, 1 << 16))  # a vtable the destructor must overwrite
        env.put(s + 0x0C, g)
        env.put(s + 0x2C, 0)
        env.put(s + 0x34, random_source.randrange(1, 1 << 32))
        env.put(s + 0x3C, 0)
        env.put(s + 0x40, 0)
        return {"state": s}

    return setup


def cases(random_source):
    receiver = lambda tokens: tokens["state"]
    for game in (True, False):
        for size in (0x44, 0x60, 0x154):
            yield Case(f"destructor game={game} size={size:#x}", DESTRUCTOR,
                       state(random_source, game, size), receiver=receiver)
    for _ in range(6):
        yield Case("destructor random", DESTRUCTOR, state(random_source, random_source.random() < 0.5,
                   4 * random_source.randrange(0x11, 0x50)), receiver=receiver)
    flags = (0, 1, 2, 3, 0x80000000, 0x80000001, 0xFFFFFFFE, 0xFFFFFFFF, 0x100, 0x101)
    for flag in flags:
        for game in (True, False):
            yield Case(f"deleting destructor flag={flag:#x} game={game}", DELETING_DESTRUCTOR,
                       state(random_source, game), receiver=receiver, arguments=(flag,))
    for _ in range(8):
        flag = random_source.randrange(0, 1 << 32)
        yield Case(f"deleting destructor random flag={flag:#x}", DELETING_DESTRUCTOR,
                   state(random_source, random_source.random() < 0.5), receiver=receiver, arguments=(flag,))


def cleanup_state(random_source, chain=True, use_handle=True, game_present=True):
    """Real base cleanup with backed manager containers and observed resource callbacks."""
    words = [random_source.getrandbits(32) for _ in range(0x60 // 4)]
    marker = random_source.randrange(1, 1 << 32)
    callback_results = [random_source.getrandbits(32) for _ in range(3)]

    def setup(env):
        s = env.object(0x60, "help state with resources", words=words)
        receipt = env.object(4 + 3 * 32, "surviving callback receipt", fill=0)
        game = env.object(0x40, "game", fill=0) if game_present else 0
        handles = env.object(0x68, "handle manager", fill=0)
        surfaces = env.object(0x400, "surface manager", fill=0)
        handle = env.object(12, "unregistered handle", fill=0xA6)
        resources = [env.object(16, f"surface {i}", fill=0x31 + i) for i in range(3)]
        nodes = [env.object(12, f"surface list node {i}", fill=0) for i in range(3)]
        table = env.object(4, "surface destructor vtable", fill=0)
        env.put(s, 0x12345678)
        env.put(s + 0x0C, game)
        env.put(s + 0x2C, handle if use_handle else 0)
        env.put(s + 0x34, marker)
        env.put(s + 0x3C, resources[0])
        env.put(s + 0x40, 0 if chain else resources[1])
        if game:
            env.put(game + 0x18, handles, surfaces)
        # Empty registry still clears its selected handle without CString refcount imports.
        env.put(handles + 0x1C, 0)
        env.put(handles + 0x64, handle)
        # Keep a positive container count after these removals: no final container teardown.
        env.put(surfaces + 0x3BC, nodes[0], nodes[-1], 8, 0)
        for i, (resource, node) in enumerate(zip(resources, nodes)):
            env.put(resource, table, node)
            env.put(node, nodes[i + 1] if i + 1 < len(nodes) else 0,
                    nodes[i - 1] if i else 0, resource)

        def destroy_resource(env, call):
            i = resources.index(call.receiver)
            count = env.get(receipt)
            # Capture the receiver, argument, publication order, vtable and cleanup state.
            env.put(receipt + 4 + count * 32, call.receiver, call.arguments[0],
                    env.get(s), env.get(s + 0x2C), env.get(s + 0x34),
                    env.get(s + 0x3C), env.get(s + 0x40), env.get(handles + 0x64))
            env.put(receipt, count + 1)
            if chain and i == 0:
                env.put(s + 0x40, resources[1])
            if chain and i == 1:
                env.put(s + 0x3C, resources[2])
                env.put(s + 0x2C, handle if use_handle else 0)
                env.put(handles + 0x64, handle)
            env.release(call.receiver)
            return callback_results[i]

        env.put(table, env.stub("surface deleting destructor", "thiscall", 1, destroy_resource))
        return {"state": s}

    return setup


_basic_cases = cases


def cases(random_source):
    yield from _basic_cases(random_source)
    for chain in (False, True):
        for handle in (False, True):
            for game in (False, True):
                for function, flags in ((DESTRUCTOR, (None,)),
                                        (DELETING_DESTRUCTOR, (0, 1, 2, 3, 0x100, 0x101))):
                    for flag in flags:
                        yield Case(f"manager cleanup chain={chain} handle={handle} game={game} flag={flag}",
                                   function, cleanup_state(random_source, chain, handle, game),
                                   receiver=lambda tokens: tokens["state"],
                                   arguments=() if flag is None else (flag,))
