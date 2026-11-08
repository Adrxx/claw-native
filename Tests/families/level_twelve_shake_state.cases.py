"""Original-derived shake constructor, dispatch, timer and resource cases."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns


def words(env, size, name, salt):
    return env.object(size, name, words=[(salt + i * 0x1030507) & 0xffffffff for i in range((size + 3) // 4)])


def resource_map(env, target, entries):
    buckets = env.object(4, "map bucket")
    head = 0
    for name, value in entries:
        key = env.object(len(name) + 1, "resource key", data=name.encode() + b"\0")
        head = env.object(16, "map node", words=[head, 0x12345678, key, value])
    env.put(buckets, head)
    env.put(target + 4, buckets, 1)


def registry(env, found, value):
    env.put(0x537668 + 0x18, 0)
    if found:
        key = env.object(8, "wait key", data=b"LS_WAIT\0")
        node = env.object(20, "wait node")
        env.put(node, node, node, 0, key, value)
        env.put(0x537680, node)


def constructor_setup(salt, populated=False, allocation_fail=False, mutate=False):
    def setup(env):
        receiver = words(env, 0x54, "shake", salt)
        obj = words(env, 0x148, "placed object", salt ^ 0x81234567)
        owner = words(env, 0x80, "level owner", salt ^ 0x19283746)
        resources = env.object(0x20, "logic resources")
        state = words(env, 0x24, "logic owner state", salt ^ 0xa1234567)
        env.put(obj + 0xc, owner)
        env.put(obj + 0x6c, state)
        env.put(owner + 0x14, resources)
        entries = []
        log = env.object(0x100, "binding observations")
        if populated:
            for index, (name, offset) in enumerate((("LogicHit", 0x70), ("LogicAttack", 0x78))):
                resource = words(env, 0x14, name, salt + index)
                entries.append((name, resource))
                if allocation_fail:
                    env.put(obj + offset, 0)
                else:
                    vt = env.object(0x28, "binding methods")
                    binding = env.object(0x20, "binding", words=[vt])
                    env.put(obj + offset, binding)
                    def clear(e, call, n=index):
                        e.put(log + n * 0x40, call.receiver, e.get(receiver), e.get(receiver + 0x10), e.get(obj + 8))
                        return 0x98765432
                    def bind(e, call, n=index):
                        e.put(log + n * 0x40 + 16, call.receiver, *call.arguments, e.get(receiver), e.get(receiver + 0x1c))
                        if mutate:
                            e.put(obj + 0x6c, state + 4)
                            e.put(obj + 0x4c, salt ^ 0xfedcba98)
                        return 0x12349876
                    env.put(vt + 0x1c, env.stub("clear binding", "thiscall", 0, clear))
                    env.put(vt + 0x24, env.stub("set binding", "thiscall", 2, bind))
        resource_map(env, resources + 0x10, entries)
        if allocation_fail:
            env.override(0x4f63ec, allocate(fail=True))
        return {"r": receiver, "arg": obj}
    return setup


def wait_setup(clock, start, duration, flags, found=False, salt=0):
    def setup(env):
        r = words(env, 0x54, "shake", salt)
        obj = words(env, 0x20, "object", salt ^ 0x13579bdf)
        owner = words(env, 0x24, "logic state", salt ^ 0x2468ace0)
        env.put(r + 0x10, owner)
        env.put(r + 0x2c, obj)
        env.put(r + 0x4c, start, duration)
        env.put(obj + 8, flags)
        env.put(0x537210, clock)
        registry(env, found, salt ^ 0xeac07125)
        return {"r": r}
    return setup


def shake_setup(rand, found, enabled, old_resource, salt, deadline, alias_clock=False):
    def setup(env):
        tokens = wait_setup(salt, salt ^ 0x12345678, 3, salt, found, salt)(env)
        r = tokens["r"]
        obj = env.get(r + 0x2c)
        if alias_clock:
            obj = 0x541320
            env.put(r + 0x2c, obj)
        level = env.object(0x30, "level")
        resources = env.object(0x20, "sound resources")
        sound_owner = env.object(0x80, "audio owner")
        audio = env.object(0x14, "audio object")
        resource = words(env, 0x14, "quake resource", salt)
        env.put(audio + 0x10, sound_owner)
        env.put(sound_owner + 0x78, 0)
        env.put(resource + 0x10, audio)
        env.put(obj + 0xc, level)
        env.put(level + 0x28, resources)
        entries = []
        for i in range(1, 6):
            selected = words(env, 0x14, "quake resource " + str(i), salt + i * 0x112233)
            selected_audio = env.object(0x14, "quake audio " + str(i))
            env.put(selected_audio + 0x10, sound_owner)
            env.put(selected + 0x10, selected_audio)
            entries.append(("LEVEL_EARTHQUAKE" + str(i), selected))
        resource_map(env, resources + 0x10, entries if found else [])
        env.put(r + 0x48, resource if old_resource else 0)
        env.put(0x532c0c, enabled)
        env.put(0x532c10, salt ^ 0x99887766)
        env.put(0x541328, salt)
        env.put(0x53c260, deadline)
        env.override(0x4a3050, returns(rand))
        return tokens
    return setup


def dispatch_setup(lower, upper, index, stride, zero, salt):
    def setup(env):
        r = words(env, 0x54, "dispatcher receiver", salt)
        log = env.object(0x40, "callback observations")
        def callback(e, call, identity=0xabcdef12):
            e.put(log + 0x20, identity)
            e.put(log, call.receiver, e.get(0x53c2c0), e.get(0x53c2a8), e.get(0x53c2ac), e.get(0x53c2b8), e.get(r + 0x24))
            e.put(r + 0x24, salt ^ 0x13572468)
            return salt ^ 0x87654321
        target = env.stub("state callback", "thiscall", 0, callback)
        table = env.object((upper - lower + 1) * stride, "state table")
        for i in range(upper - lower + 1):
            def selected_callback(e, call, identity=i):
                return callback(e, call, identity)
            selected = env.stub("state slot " + str(i), "thiscall", 0, selected_callback)
            env.put(table + i * stride, 0 if zero else selected)
        fallback = env.object(stride, "fallback slot", words=[target])
        env.put(0x53c2a0, 0, 0, lower, upper, table, fallback, stride, 0, 0xaabbccdd)
        descriptor = env.object(16, "RTTI descriptor")
        data = env.object(8, "RTTI data", words=[salt, salt ^ 0xffffffff])
        vtable = env.object(8, "RTTI vtable", words=[descriptor, target])
        env.put(descriptor + 0xc, data)
        env.put(r, vtable + 4)
        return {"r": r}
    return setup


def cases(random_source):
    for i in range(16):
        salt = random_source.getrandbits(32)
        yield Case(f"constructor distinct words {i}", 0x488870, constructor_setup(salt, i % 3 != 0, i % 4 == 0, i % 5 == 0), receiver=lambda t: t["r"], arguments=(lambda t: t["arg"],))
    for clock, start in ((0, 0), (10, 0xfffffff8), (0x80000000, 0), (0xffffffff, 1), (123456, 123455)):
        elapsed = (clock - start) & 0xffffffff
        for duration in (0, elapsed, (elapsed + 1) & 0xffffffff, 0x80000000, 0xffffffff):
            for flags in (0xabcdef01, 0x12345678):
                yield Case(f"wait {clock:x}-{start:x} duration {duration:x} flags {flags:x}", 0x488cd0, wait_setup(clock, start, duration, flags, salt=random_source.getrandbits(32)), receiver=lambda t: t["r"])
    for found in (False, True):
        for i in range(8):
            yield Case(f"begin wait found={found} {i}", 0x488c90, wait_setup(random_source.getrandbits(32), 0, 0, 0, found, random_source.getrandbits(32)), receiver=lambda t: t["r"])
    for rand in (0, 1, 2, 3, 4, 5, 6, 7, 0xffffffff, 0xfffffffb, 0x80000000, 0x7fffffff):
        for found in (False, True):
            for enabled, old in ((0, False), (0, True), (1, True), (0xffffffff, False)):
                salt = random_source.getrandbits(32)
                yield Case(f"shake rand={rand:x} found={found} enabled={enabled:x} old={old}", 0x488cf0, shake_setup(rand, found, enabled, old, salt, (salt + (4000 if old else 6000)) & 0xffffffff), receiver=lambda t: t["r"], initial_stack=((-4, random_source.getrandbits(32).to_bytes(4, "little")),))
    for clock in (0, 2, 0x100, 0x7ffffffe, 0xfffffff0):
        yield Case(f"shake object flags alias clock {clock:x}", 0x488cf0,
                   shake_setup(0, False, 0, False, clock, 0, alias_clock=True), receiver=lambda t: t["r"])
    for lower, upper in ((-3, 2), (0, 4), (0x7ffffffc, 0x7ffffffe), (-2147483646, -2147483644)):
        for index in (lower - 1, lower, upper, upper + 1):
            for stride in (4, 12):
                yield Case(f"dispatch {lower}..{upper} index {index} stride {stride}", 0x4889e0, dispatch_setup(lower, upper, index, stride, False, random_source.getrandbits(32)), receiver=lambda t: t["r"], arguments=(index & 0xffffffff,))
    for index in (-1, 0, 1):
        yield Case(f"dispatch zero slot {index}", 0x4889e0, dispatch_setup(-1, 1, index, 8, True, random_source.getrandbits(32)), receiver=lambda t: t["r"], arguments=(index & 0xffffffff,))


def original_dispatch_probe():
    """Coordinator diagnostic: original fault and stable-bounds evidence only."""
    import json
    import random
    from pathlib import Path
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_EBP
    from clawparity.runner import load_program, load_symbols
    from clawparity.env import Env
    from clawparity.fixtures import CATALOGUE, reallocate
    spec = json.loads(Path("Tests/families/level_twelve_shake_state.json").read_text())
    results = []
    for index, failure in ((-4, True), (3, True), (-4, False), (3, False), (-3, False), (2, False)):
        e = Env(load_program(spec), symbols=load_symbols())
        for addr, c in spec["callees"].items():
            if c["kind"] == "fixture":
                e.fixture(int(addr, 16), c["convention"], c["argc"], CATALOGUE[c["fixture"]], c.get("name", ""), c.get("arguments", ()))
        e._begin_case(random.Random(55))
        tokens = dispatch_setup(-3, 2, index, 4, False, 123)(e)
        if failure:
            e.override(0x4a9070, reallocate(fail=True))
        observed = []
        def observe(uc, address, size, _):
            if address in (0x488a63, 0x488a68, 0x488a7e):
                item = {"pc": hex(address), "lower": e.get(0x53c2a8), "upper": e.get(0x53c2ac)}
                if address == 0x488a63:
                    item["slot"] = e.get(e.machine.register(UC_X86_REG_EAX))
                observed.append(item)
        e.machine.uc.hook_add(UC_HOOK_CODE, observe)
        e._freeze()
        side = e.run_original(0x4889e0, tokens["r"], (index & 0xffffffff,), trace=True, check_objects=True)
        results.append({"index": index, "realloc_fail": failure, "completed": side.completed,
                        "errors": [str(x) for x in side.errors], "eip": hex(e.machine.register(UC_X86_REG_EIP)),
                        "ebp": hex(e.machine.register(UC_X86_REG_EBP)), "observed": observed})
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(original_dispatch_probe(), sort_keys=True))
