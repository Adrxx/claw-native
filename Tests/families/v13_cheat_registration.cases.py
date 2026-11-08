"""Original-only cases for v1.3 registration and mode reset."""
from clawparity.cases import Case

REGISTER = 0x423E40
INITIALIZE = 0x423E80
RESET = 0x42A960
NEW = 0x4FCAEA
SUBSCRIPT = 0x4FC6D6
REGISTRATIONS = 67


def registration_setup(payload, failed=(), fail_all=False, rewrite=False, key=None):
    def setup(env):
        receiver = env.object(96, "registry", data=payload[:96])
        slots = env.object(80 * 12, "map cells and witnesses", data=payload * 10)
        state = env.object(16, "fixture state", fill=0)
        allocations = env.object(80 * 20, "allocation observations", fill=0)
        insertions = env.object(80 * 80, "insertion observations", fill=0)
        key_address = env.object(64, "direct encoded key", data=key or payload[:64])

        def allocate(env, call):
            ordinal = env.calls_so_far(NEW)
            last_pointer, last_slot = env.get(state), env.get(state + 4)
            previous_value = env.get(last_slot) if last_slot else 0
            pointer = 0
            if not fail_all and ordinal not in failed:
                base = env.object(call.arguments[0] + 16, "guarded command", data=payload[:24])
                pointer = base + 8
            env.put(allocations + (ordinal - 1) * 20,
                    ordinal, call.arguments[0], pointer, last_pointer, previous_value)
            env.put(state, pointer)
            return pointer

        def subscript(env, call):
            ordinal = env.calls_so_far(SUBSCRIPT)
            allocation = env.get(state)
            previous_slot = env.get(state + 4)
            previous_value = env.get(previous_slot) if previous_slot else 0
            cell = slots + (ordinal - 1) * 12 + 4
            row = insertions + (ordinal - 1) * 80
            env.put(row, ordinal, call.receiver, call.arguments[0], allocation,
                    previous_slot, previous_value, cell, env.get(cell))
            # Preserve exact encoded bytes, allocation contents at callback time,
            # and the prior publication in surviving memory.
            env.write(row + 32, env.read(call.arguments[0], 32))
            env.write(row + 64, env.read(allocation - 4, 16))
            if rewrite:
                env.put(allocation, 0xD13579AB ^ ordinal, 0x8ACE2460 ^ ordinal)
            env.put(state + 4, cell)
            return cell

        env.override(NEW, allocate)
        env.override(SUBSCRIPT, subscript)
        return {"receiver": receiver, "key": key_address}
    return setup


def cases(random_source):
    def payload():
        return bytes(random_source.randrange(1, 256) for _ in range(96))

    yield Case("register all 67 encoded keys in order", INITIALIZE,
               registration_setup(payload()), receiver=lambda t: t["receiver"])
    yield Case("all 67 allocations fail", INITIALIZE,
               registration_setup(payload(), fail_all=True), receiver=lambda t: t["receiver"])
    for position in range(1, REGISTRATIONS + 1):
        yield Case(f"only allocation {position} fails, later entries continue", INITIALIZE,
                   registration_setup(payload(), failed=(position,)), receiver=lambda t: t["receiver"])
    yield Case("map changes command bytes before pointer publication", INITIALIZE,
               registration_setup(payload(), rewrite=True), receiver=lambda t: t["receiver"])
    for trial in range(8):
        failed = tuple(i for i in range(1, REGISTRATIONS + 1) if random_source.randrange(4) == 0)
        yield Case(f"mixed allocation failures {trial}", INITIALIZE,
                   registration_setup(payload(), failed=failed), receiver=lambda t: t["receiver"])

    pairs = [(0, 0), (1, 1), (0xFFFFFFFF, 0x80000000), (0x80000000, 0xFFFFFFFF),
             (0x8044, 0), (0x8086, 1), (0x12345678, 0x9ABCDEF0)]
    pairs += [(random_source.getrandbits(32), random_source.getrandbits(32)) for _ in range(16)]
    for index, (command, flag) in enumerate(pairs):
        for fail in (False, True):
            yield Case(f"helper {index} allocation {'fails' if fail else 'succeeds'}", REGISTER,
                       registration_setup(payload(), fail_all=fail, key=payload()[:64]),
                       receiver=lambda t: t["receiver"],
                       arguments=(lambda t: t["key"], command, flag))
    yield Case("helper preserves map callback changes", REGISTER,
               registration_setup(payload(), rewrite=True), receiver=lambda t: t["receiver"],
               arguments=(lambda t: t["key"], 0x37A5F19C, 0xE2468BD0))

    for trial in range(12):
        words = [random_source.randrange(1, 0x100000000) for _ in range(40)]
        if trial == 0:
            words = [0xFFFFFFFF] * 40
        elif trial == 1:
            words = [0x80000000 | i for i in range(40)]

        def reset_setup(env, words=words):
            # Includes every changed DWORD, every gap, and witnesses on both sides.
            env.put(0x535918, *words)
        yield Case(f"reset fourteen mode DWORDs with witnesses {trial}", RESET, reset_setup)
