"""Original-backed cases for Omar core."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns


def dbl(env, address, value):
    env.write(address, struct.pack("<d", value))


def entry(label, function, setup, *args):
    return Case(label, function, setup, receiver=lambda t: t["obj"], arguments=args)


def ordinary(rng, shield=1, mode=0, health=77, attack=0, visible=-1, audio=0, sound=0, clock=123456, mutate=False):
    entropy = rng.getrandbits(32)
    def setup(env):
        obj = env.object(0xD48, "Omar", fill=0)
        actor = env.object(0x1B0, "Omar actor", fill=0)
        player = env.object(0x1B0, "attacker", fill=0)
        state = env.object(0x30, "logic state", fill=0)
        methods = env.object(0xA0, "Omar methods", fill=0)
        receipts = env.object(0x80, "callback receipts", fill=0)
        player_logic = env.object(0x30, "attacker logic", fill=0)
        player_flags = env.object(0x20, "attacker input", fill=0)
        scene = env.object(0x30, "scene", fill=0)
        env.put(obj, methods)
        env.put(obj + 0xC, actor, state)
        env.put(obj + 0x12C, actor, scene, entropy)
        env.put(obj + 0x18, 0xDEADBEEF, 0xA1B2C3D4)
        env.put(obj + 0x24, entropy ^ 0xA53C91E7)
        env.put(obj + 0x3D0, 0x13579BDF, 0x2468ACE0)
        env.put(obj + 0xD30, 0x31415926, 0x27182818, 0x55AA55AA, 0xAA55AA55)
        for i in range(9):
            dbl(env, obj + 0x4D0 + i * 0xF0, 17.25 + i)
        dbl(env, obj + 0x50, 13.75)
        env.put(obj + 0x18C, 2)
        env.put(obj + 0xD18, mode, shield, 1)
        env.put(actor + 0xC, scene)
        env.put(actor + 8, 0xA5330020)
        env.put(actor + 0x38, visible)
        env.put(actor + 0x40, 0xB3, 0xABCDEF01, 0x10203040)
        env.put(actor + 0x4C, 251, 361)
        env.put(actor + 0x64, 0x876)
        env.put(actor + 0x10C, health)
        env.put(actor + 0x190, 0x137)
        env.put(state + 0x1C, 0x37)
        env.put(player + 0x104, 7)
        env.put(player + 0x138, 0x80000000)
        env.put(player + 0x164, attack)
        env.put(player + 0x6C, player_logic)
        env.put(player_logic + 0x14, player_flags)
        env.put(0x537E88, player)
        env.put(0x537210, clock)
        env.put(0x534EAC, 0x26B7)
        env.put(0x532C0C, audio, 0xA17)
        env.put(0x53C9AC, 0)
        env.put(0x537668 + 0x18, 0)
        env.override(0x4A3050, returns(3))
        def record(index):
            def effect(env, call):
                p = receipts + index * 16
                env.put(p, env.get(p) + 1, call.receiver,
                        call.arguments[0] if call.arguments else 0, env.get(obj + 0xD18))
                if mutate and index == 1:
                    env.put(player + 0x104, 31)
                    env.put(actor + 0x10C, 97)
                    env.put(obj + 0xD20, 0)
                return entropy
            return effect
        env.put(methods + 0x24, env.stub("movement update", "thiscall", 0, record(0)))
        env.put(methods + 0x28, env.stub("hit observer", "thiscall", 1, record(1)))
        env.put(methods + 0x9C, env.stub("unshielded hit", "thiscall", 0, record(2)))
        if sound:
            resource = env.object(0x20, "thunder resource", fill=0)
            voice = env.object(0x20, "thunder voice", fill=0)
            manager = env.object(0x80, "disabled audio manager", fill=0)
            env.put(resource + 0x10, voice)
            env.put(voice + 0x10, manager)
            env.put(obj + 0x47C, resource)
        return dict(obj=obj, actor=actor, player=player, state=state, methods=methods)
    return setup


def destructor(rng, heap=False, strings=False):
    entropy = rng.getrandbits(32)
    def setup(env):
        obj = env.object(0xD48, "Omar being destroyed", fill=0)
        env.put(obj, 0x50EAFC)
        env.put(obj + 0x2F4, 0x513E34, entropy, 0x21 if heap else 0x20)
        if heap:
            bits = env.object(8, "heap bits", words=[entropy, entropy ^ 0xFFFFFFFF])
            env.put(obj + 0x300, bits)
        empty = env.get(0x52E1C8) + 12
        env.put(obj + 0x1A4, empty, empty)
        if strings:
            for off, count in ((0x1A4, 1), (0x1A8, 2)):
                text = env.object(24, "CString storage", words=[count, 5, 5])
                env.write(text + 12, b"Omar!\0")
                env.put(obj + off, text + 12)
        def decrement(env, call):
            ptr = call.arguments[0]
            value = (env.get(ptr) - 1) & 0xFFFFFFFF
            env.put(ptr, value)
            return value
        env.override(0x5469E8, decrement)
        return {"obj": obj}
    return setup


def dispatch(rng, state, minimum, maximum, selected=True):
    entropy = rng.getrandbits(32)
    def setup(env):
        obj = env.object(0xD48, "dispatch receiver", fill=0)
        receipt = env.object(16, "dispatch receipt", fill=0)
        def callback(env, call):
            env.put(receipt, env.get(receipt) + 1, call.receiver, env.get(0x537BF0), entropy)
            return entropy
        code = env.stub("selected Omar state", "thiscall", 0, callback)
        data = env.object((maximum - minimum + 1) * 4, "Omar state table", fill=0)
        for i in range(maximum - minimum + 1):
            env.put(data + i * 4, code if selected else 0)
        env.put(0x537BD0, 0, 0, minimum, maximum, data, data, 4, 0, 0x123)
        lo, hi = min(minimum, state), max(maximum, state)
        base = env.object((hi - lo + 1) * 4, "base enemy state table", fill=0)
        for i in range(hi - lo + 1):
            env.put(base + i * 4, code)
        env.put(0x5349B8, 0, 0, lo, hi, base, base, 4, 0, 0x321)
        return {"obj": obj, "receipt": receipt}
    return setup


def cases(random_source):
    for heap in (False, True):
        for strings in (False, True):
            yield entry(f"destructor {heap} {strings}", 0x463A50,
                        destructor(random_source, heap, strings))
            for flags in (0, 1, 2, 3, 0x80000000):
                yield entry(f"deleting destructor {heap} {strings} {flags:#x}", 0x463A30,
                            destructor(random_source, heap, strings), flags)
    for state in (-4, 0, 4):
        for selected in (False, True):
            yield entry(f"in-range dispatch {state} {selected}", 0x463B40,
                        dispatch(random_source, state, -4, 4, selected), state)
    for state in (-6, 6):
        yield entry(f"growing dispatch {state}", 0x463B40,
                    dispatch(random_source, state, -4, 4), state)
    positions = [(0.0, -0.0), (1.999, -1.999), (-1.0, 2147483647.0),
                 (-2147483648.0, 77.75), (1024.5, -2048.5)]
    positions.extend((random_source.uniform(-1e6, 1e6), random_source.uniform(-1e6, 1e6))
                     for _ in range(12))
    for x, y in positions:
        def position(env, x=x, y=y):
            t = ordinary(random_source)(env)
            dbl(env, t["obj"] + 0x68, x)
            dbl(env, t["obj"] + 0x70, y)
            env.put(t["obj"] + 0x118, 0xAABBCCDD, 0x11223344)
            return t
        yield entry(f"position {x} {y}", 0x463FD0, position)
    for clock in (0, 1, 33, 0x7FFFFFFF, 0xFFFFFFFF):
        def integrate(env, clock=clock):
            t = ordinary(random_source, clock=clock)(env)
            for i in range(9):
                base = t["obj"] + 0x4A8 + 0xF0 * i
                dbl(env, base, i * 0.125 - 2.0)
                env.put(base + 0xA0, 1)
            return t
        yield entry(f"integrate nine clock={clock:#x}", 0x4640B0, integrate, 0x52720C)
    yield entry("body hit shielded", 0x4642B0,
                ordinary(random_source, shield=1), lambda t: t["player"])
    for high in (False, True):
        for mode in (0, 1, 2):
            for health in (-1, 0, 1, 50):
                def body_hit(env, high=high, mode=mode, health=health):
                    t = ordinary(random_source, shield=0, mode=mode, health=health)(env)
                    env.put(t["obj"] + 0xD20, mode)
                    flags = env.get(env.get(t["player"] + 0x6C) + 0x14)
                    env.put(flags + 0x14, 1 if high else 0)
                    return t
                yield entry(f"body hit {high} {mode} {health}", 0x4642B0,
                            body_hit, lambda t: t["player"])
    yield entry("shield hit delegates", 0x464360,
                ordinary(random_source, shield=0), lambda t: t["player"])
    for mode in (0, 1, 2):
        for attack in (0, 0x40000, 0x80000, 0xC0000):
            for health in (74, 75, 76):
                for visible in (-1, 0):
                    yield entry(f"shield hit {mode} {attack:#x} {health} {visible}", 0x464360,
                                ordinary(random_source, mode=mode, health=health,
                                         attack=attack, visible=visible), lambda t: t["player"])
    for audio in (0, 1):
        for sound in (0, 1):
            for a, b in ((0, 0), (0xA16D, 0x42B), (0xFFFFFFFF, 0x80000000)):
                yield entry(f"thunder {audio} {sound} {a:#x} {b:#x}", 0x464500,
                            ordinary(random_source, audio=audio, sound=sound), a, b)
    yield entry("body callback changes damage health and cycle", 0x4642B0,
                ordinary(random_source, shield=0, mutate=True), lambda t: t["player"])
    yield entry("shield callback changes health", 0x464360,
                ordinary(random_source, mode=1, attack=0x40000, mutate=True), lambda t: t["player"])
