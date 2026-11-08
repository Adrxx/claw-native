"""Cases for the surface flip example."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

FLIP = 0x4B99D0
OPERATOR_NEW = 0x4F63EC
SURFACE_VTABLE = 0x513690


def surface(width, height, pitch=None, lock_result=0, unlock_result=0, depth=None):
    """setup() for one surface of the given geometry with stand-in DirectDraw Lock and Unlock methods."""
    pitch = width if pitch is None else pitch

    def setup(env):
        capacity = max(1, (max(0, height) - 1) * max(0, pitch) + max(0, width))
        pixels = env.object(capacity, "pixels")
        target = env.object(188, "surface", fill=0)
        interface = env.object(4, "directdraw-surface")
        methods = env.object(132, "directdraw-vtable")

        def lock(env, call):
            if not lock_result:
                env.put(target + 0x30, pixels)
            return lock_result

        env.put(target, SURFACE_VTABLE)
        env.put(target + 0x08, interface)
        env.put(target + 0x14, height, width, pitch)
        env.put(target + 0x30, pixels)
        if depth is not None:
            env.put(target + 0xA4, depth)
        env.put(interface, methods)
        env.put(methods + 0x64, env.stub("IDirectDrawSurface::Lock", "stdcall", 5, lock))
        env.put(methods + 0x80, env.stub("IDirectDrawSurface::Unlock", "stdcall", 2, returns(unlock_result)))
        return {"surface": target, "pixels": pixels}

    return setup


def flip(label, setup, **options):
    return Case(label, FLIP, setup, receiver=lambda tokens: tokens["surface"], **options)


def cases(random_source):
    for width in (0, 1, 2, 3, 4, 7, 16, 31):
        for height in (-1, 0, 1, 2, 3, 4, 7):
            for extra in (0, 1, 5):
                yield flip(f"rows {width}x{height} pitch+{extra}", surface(width, height, width + extra))
    for _ in range(40):
        width, height = random_source.randrange(1, 200), random_source.randrange(2, 120)
        yield flip(f"random {width}x{height}", surface(width, height, width + random_source.randrange(0, 9)))
    for pitch in (0, 1, 3):
        yield flip(f"overlapping rows pitch {pitch}", surface(7, 5, pitch))
    for depth in (8, 16, 24, 32):
        yield flip(f"depth {depth} still copies width bytes", surface(5, 7, 5 * (depth // 8) + 3, depth=depth))
    yield flip("unlock failure is ignored", surface(7, 5, 11, unlock_result=0x80004005))

    def no_memory(env):
        tokens = surface(7, 5, 11)(env)
        env.override(OPERATOR_NEW, allocate(fail=True))
        return tokens

    yield flip("scratch allocation fails: unlock, no copy", no_memory)

    def geometry_changes_during_allocation(env):
        tokens = surface(7, 5, 11)(env)

        def allocate_and_shrink(env, call):
            env.put(tokens["surface"] + 0x14, 3, 2)  # height and width change after the scratch row is sized
            return env.object(call.arguments[0], name="allocation")

        env.override(OPERATOR_NEW, allocate_and_shrink)
        return tokens

    yield flip("height and width are re-read after the allocation", geometry_changes_during_allocation)
    for status in (0x80004005, 0x887601C2):
        yield flip(f"lock fails with {status:#x}", surface(7, 5, 11, lock_result=status))
