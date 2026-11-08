"""Cases for game_state_resume_helpers: Game state resume helper and in-game menu helper.

0x46ddc0 restores a surface through 0x4b98b0 (callee error paths that reach the message box are avoided).
0x46df20 runs 0x4cb9b0, locks a surface through 0x4b9730, rewrites its 16-bit pixel pairs row by row
(even rows keep the low half and clear the high half, odd rows the reverse as the original does) and unlocks it.
"""
from clawparity.cases import Case

RESUME = 0x46DDC0
FILTER = 0x46DF20
LOST = 0x887601C2


def record(log, result=0, effect=None):
    """A stand-in that stores receiver, arguments and call number into `log`, then returns `result`
    (a number or a function of the 0-based call index)."""
    def run(env, call):
        index = env.calls_so_far(call.function) - 1
        words = [call.receiver] + list(call.arguments)
        env.put(log + 24 * min(index, 3), *words[:5])
        if effect is not None:
            effect(env, call, index)
        return result(index) if callable(result) else result
    return run


def words(random_source, count):
    return [random_source.randrange(0x01010101, 0xFFFFFFFF) for _ in range(count)]


def make_surface(env, random_source, geometry=None, lock_results=0, restore_result=1, pixels=None,
                 lock_publishes=True, set_in_lock=True, unlock_result=0, region_result=0):
    """A surface object (the 0x4b98b0 / 0x4b9730 receiver) with logging DirectDraw stand-ins."""
    height, width, pitch = geometry or (1, 2, 8)
    count = width // 2 if width >= 0 else -((-width) // 2)
    offsets = [row * pitch + k * 4 for row in range(max(height, 0)) for k in range(max(count, 0))] or [0]
    low, high = min(offsets), max(offsets) + 4
    base = env.object(8 + high - low + 16, "pixels", data=bytes(random_source.randrange(1, 256) for _ in range(8 + high - low + 16)))
    pixel_pointer = base + 8 - low
    logs = {name: env.object(96, name, fill=0) for name in ("lock", "unlock", "restore", "region")}
    surface = env.object(0x48, "surface", fill=0)
    interface = env.object(16, "interface", fill=0)
    surface_vtable = env.object(0x40, "surface-vtable", fill=0)
    interface_vtable = env.object(0x90, "interface-vtable", fill=0)

    def lock_effect(env, call, index):
        if set_in_lock:
            env.put(surface + 0x14, height & 0xFFFFFFFF, width & 0xFFFFFFFF, pitch & 0xFFFFFFFF)
        env.put(surface + 0x30, pixel_pointer if lock_publishes else 0)

    results = lock_results if callable(lock_results) else (lambda index: lock_results)
    env.put(surface, surface_vtable)
    env.put(surface + 0x08, interface)
    if not set_in_lock:
        env.put(surface + 0x14, height & 0xFFFFFFFF, width & 0xFFFFFFFF, pitch & 0xFFFFFFFF)
    else:
        env.put(surface + 0x14, 1, 2, 4)
    env.put(surface + 0x30, pixel_pointer)
    env.put(interface, interface_vtable)
    env.put(surface_vtable + 0x1C, env.stub("Restore", "thiscall", 0, record(logs["restore"], restore_result)))
    env.put(interface_vtable + 0x2C, env.stub("Region", "stdcall", 3, record(logs["region"], region_result)))
    env.put(interface_vtable + 0x64, env.stub("Lock", "stdcall", 5, record(logs["lock"], results, lock_effect)))
    env.put(interface_vtable + 0x80, env.stub("Unlock", "stdcall", 2, record(logs["unlock"], unlock_result)))
    return {"surface": surface, "pixels": base, "logs": logs, "interface": interface}


def graph(env, random_source, surface, decoy, slot, listing=None, flags=0):
    """Receiver chain: receiver+0xc -> A; A+4 -> B; B[slot] -> D; D+0x2c -> surface. Decoys sit in the other offsets."""
    other = 0x10 if slot == 0x14 else 0x14
    junk = words(random_source, 20)
    D = env.object(0x40, "target-holder", words=junk[:16])
    C = env.object(0x40, "decoy-holder", words=junk[4:20])
    env.put(D + 0x2C, surface)
    env.put(C + 0x2C, decoy)
    B = env.object(0x30, "B", words=junk[:12])
    env.put(B + slot, D)
    env.put(B + other, C)
    log2 = env.object(96, "param2-log", fill=0)
    p2_vtable = env.object(0x40, "p2-vtable", fill=0)
    p2 = env.object(0x40, "param2", words=junk[:16])
    env.put(p2, p2_vtable)
    env.put(p2_vtable + 0x28, env.stub("p2.28", "thiscall", 1, record(log2, 0)))
    env.put(p2_vtable + 0x2C, env.stub("p2.2c", "thiscall", 1, record(log2, 0)))
    listing_object = env.object(16, "list", fill=0)
    R = env.object(0x70, "R", words=words(random_source, 28))
    env.put(R + 0x08, flags)
    env.put(R + 0x38, listing_object)
    env.put(R + 0x3C, 0)
    env.put(R + 0x60, 0xFFFFFFFF)
    A = env.object(0x30, "A", words=words(random_source, 12))
    env.put(A + 4, B, p2)
    env.put(A + 0x24, R)
    receiver = env.object(0x20, "receiver", words=words(random_source, 8))
    env.put(receiver + 0x0C, A)
    return {"receiver": receiver, "D": D, "B": B, "R": R, "p2": p2, "log2": log2}


def tokens_of(env, random_source, **options):
    flags = options.pop("flags", 0)
    slot = options.pop("slot")
    main = make_surface(env, random_source, **options)
    decoy = make_surface(env, random_source, geometry=(2, 6, 16))
    result = graph(env, random_source, main["surface"], decoy["surface"], slot, flags=flags)
    result.update(main)
    return result


def resume_case(label, random_source, **options):
    return Case(f"46ddc0 {label}", RESUME, lambda env: tokens_of(env, random_source, slot=0x10, **options),
                receiver=lambda tokens: tokens["receiver"])


def filter_case(label, random_source, **options):
    return Case(f"46df20 {label}", FILTER, lambda env: tokens_of(env, random_source, slot=0x14, **options),
                receiver=lambda tokens: tokens["receiver"])


def cases(random_source):
    # 0x46ddc0: restore the surface; success, lost then restored, lost and not restorable.
    yield resume_case("region ok", random_source)
    lost_once = lambda index: LOST if index == 0 else 0  # the retry succeeds, so the error dialog is never reached
    yield resume_case("surface lost, restore ok, retry ok", random_source, region_result=lost_once)
    yield resume_case("surface lost, restore returns 0", random_source, region_result=LOST, restore_result=0)
    for restore in (5, 0x80004005, 0x7FFFFFFF):
        yield resume_case(f"surface lost, restore {restore:#x}, retry ok", random_source,
                          region_result=lost_once, restore_result=restore)

    # 0x46df20, 0x4cb9b0 flag variants (count 0, so the list paths that need 0x4d0d50 are not entered).
    for flags in (0, 1, 2, 3, 0x100, 0x101, 0xFFFFFFFF, 0xFFFFFFFE):
        yield filter_case(f"cb9b0 flags {flags:#x}", random_source, flags=flags, geometry=(3, 8, 20))

    # Row/column grid, deterministic.
    for width in (-3, -2, 0, 1, 2, 3, 4, 5, 8, 9, 16, 33):
        for height in (0, 1, 2, 3, 4, 5):
            count = max(width // 2 if width >= 0 else 0, 0)
            tight = max(count * 4, 4)
            for name, pitch in (("tight", tight), ("pad", tight + 4 * random_source.randrange(1, 6)),
                                ("odd", tight + 1 + 2 * random_source.randrange(0, 3))):
                yield filter_case(f"{width}x{height} {name} pitch {pitch}", random_source,
                                  geometry=(height, width, pitch), set_in_lock=bool(random_source.randrange(2)))

    # Overlapping, zero and negative pitch.
    for pitch in (0, 1, 2, 3, 4, 6, -4, -8, -20):
        for width, height in ((6, 4), (7, 3), (2, 5)):
            yield filter_case(f"{width}x{height} pitch {pitch}", random_source, geometry=(height, width, pitch))

    # Random geometries, geometry published by Lock or preset.
    for _ in range(100):
        width = random_source.randrange(1, 80)
        height = random_source.randrange(1, 12)
        pitch = (width // 2) * 4 + random_source.randrange(0, 40)
        yield filter_case(f"random {width}x{height} pitch {pitch}", random_source, geometry=(height, width, pitch),
                          set_in_lock=bool(random_source.randrange(2)), flags=random_source.choice((0, 0, 1, 2, 3)))

    # Lock outcomes.
    geometry = (4, 10, 24)
    yield filter_case("lock publishes null pixels", random_source, geometry=geometry, lock_publishes=False)
    yield filter_case("lock lost, restore ok, second lock ok", random_source, geometry=geometry,
                      lock_results=lambda index: LOST if index == 0 else 0)
    yield filter_case("lock lost, second lock ok, null pixels", random_source, geometry=geometry,
                      lock_results=lambda index: LOST if index == 0 else 0, lock_publishes=False)
    yield filter_case("lock lost, restore returns 0", random_source, geometry=geometry,
                      lock_results=LOST, restore_result=0)
    for count in range(1, 11):
        yield filter_case(f"pixel values seed {count}", random_source,
                          geometry=(random_source.randrange(2, 7), random_source.randrange(2, 20),
                                    40 + 4 * random_source.randrange(0, 6)))
