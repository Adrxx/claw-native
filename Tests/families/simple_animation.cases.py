"""Independent original-driven cases for SimpleAnimation::logic (cdecl)."""
from clawparity.cases import Case

LOGIC = 0x498F40
DELTA = 0x5430C4


def setup_object(state_value, payload, delta, animation=None, alias=None):
    def setup(env):
        # Random nonzero surrounding words expose narrow or misplaced stores.
        if alias is None:
            obj = env.object(0x1C0, "simple-animation", data=payload[:0x1C0])
            state = env.object(0x180, "logic-state", data=payload[0x1C0:0x340])
        else:
            block = env.object(0x400, "overlapping-object-and-state", data=payload)
            obj = block + 0x100
            state = obj + alias
        env.put(state + 0x168, 0x789ABCDE)
        env.put(obj + 0xC8, 0xFEDC4321)
        env.put(state + 0x1C, state_value)
        env.put(obj + 0x6C, state)
        env.put(DELTA, delta)
        if animation is not None:
            countdown, policy, stopped, present = animation
            inert = env.object(16, "inert-animation-resource", fill=0x73)
            env.put(obj + 0x190, inert if present else 0)
            env.put(obj + 0x19C, countdown, policy, stopped,
                    0xA61742D3, 0x37B89C26)
        return {"object": obj}
    return setup


def cases(random_source):
    def case(label, state, delta=0, animation=None, alias=None):
        payload = bytes(random_source.randrange(1, 256) for _ in range(0x400))
        return Case(label, LOGIC,
                    setup_object(state, payload, delta, animation, alias),
                    arguments=(lambda t: t["object"],))

    yield case("zero state initializes every field", 0)
    yield case("state object is the argument object", 0, alias=0)
    yield case("initialization clears captured state pointer", 0, alias=-0xFC)
    yield case("state transition follows overlapping object clear", 0, alias=0xAC)

    for state in (1, 2, 4, 6, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        yield case(f"nonzero state {state:#x} is preserved", state, 0xF13579BD)
    for index in range(8):
        state = random_source.randrange(6, 0xFFFFFFFF)
        yield case(f"random inactive state {index}", state,
                   random_source.getrandbits(32))

    yield case("active with absent animation returns outer one", 5,
               0xFFFFFFFF, (0x81, 1, 0, False))
    for countdown in (1, 2, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        yield case(f"tick policy decrements {countdown:#x}", 5,
                   0xFEDCBA98, (countdown, 0, 0, True))
    for countdown, delta in ((2, 0), (2, 1), (0x80000001, 0x80000000),
                             (0xFFFFFFFF, 0xFFFFFFFE)):
        yield case(f"elapsed countdown {countdown:#x} delta {delta:#x}",
                   5, delta, (countdown, 1, 0, True))
    for countdown, delta in ((0, 0), (1, 1), (7, 8),
                             (0x80000000, 0xFFFFFFFF)):
        yield case(f"stopped animation publishes value at {countdown:#x}",
                   5, delta, (countdown, 1, 0xFFFFFFFF, True))
    for index in range(12):
        countdown = random_source.randrange(2, 0x100000000)
        delta = random_source.randrange(1, countdown)
        yield case(f"random active elapsed countdown {index}", 5, delta,
                   (countdown, random_source.randrange(1, 0x100000000),
                    0, True))
