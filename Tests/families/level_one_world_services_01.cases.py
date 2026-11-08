"""Cases for level_one_world_services_01: Level 1 rect, string-owner and view service entries."""
from clawparity.cases import Case
from clawparity.fixtures import returns

CLEAR_OWNER = 0x422350
RECT = 0x4296F0
SET_ENABLED = 0x42CE20
REFRESH = 0x42D1F0
SET_VIEWPORT = 0x429ED0
SET_RECT = 0x546D5C


def owner(old30, nodes=0, blocks=0, string=False, seed=0x1000):
    """A string owner. `nodes` list nodes hang off +4 (next at +0, string slot at +8), `blocks` plex blocks
    off +0x14 (next at +0), and +0x1c holds either an empty or a non-empty string pointer."""
    def setup(env):
        obj = env.object(0x40, "owner", fill=0)
        text = env.object(16, "string", words=[0x11111111, 0 if not string else 3, 0x22222222, 0x33333333])
        chain = 0
        for index in reversed(range(nodes)):
            chain = env.object(16, f"node-{index}", words=[chain, 0x7000 + index, text + 12, seed + index])
        head = 0
        for index in reversed(range(blocks)):
            head = env.object(16, f"block-{index}", words=[head, 0x8000 + index, seed + 0x10 + index, 0x9999])
        env.put(obj + 0x04, chain, 0xAAAA0002, 0xAAAA0003 + nodes, 0xAAAA0004 + nodes)
        env.put(obj + 0x14, head)
        env.put(obj + 0x18, 0xBBBB0001)
        env.put(obj + 0x1C, text + 12)
        env.put(obj + 0x20, 0xCCCC0001, 0xCCCC0002, 0xCCCC0003)
        env.put(obj + 0x30, old30)
        log = env.object(0x80, "service-log", fill=0)

        def record(env, call):
            count = env.get(log)
            env.put(log, count + 1)
            env.put(log + 4 + 8 * count, call.function, call.receiver)
            return 0

        env.override(0x4F650F, record)
        env.override(0x4F6584, record)
        return {"obj": obj, "text": text, "log": log}
    return setup


def rect(initial):
    def setup(env):
        obj = env.object(16, "rect", words=initial)
        return {"obj": obj}
    return setup


def view(count, flag_values, slot=None, vtable_result=1, has_world=True, has_info=True,
         has_table=True, null_slot=False, marker=0x5A5A0000, field_68=0x68686868, field_128=0x12345678, count_field=None):
    """A view object whose table has `count` entries, each a flag record with distinct contents."""
    def setup(env):
        obj = env.object(0x140, "view", fill=0)
        methods = env.object(0x20, "view-vtable", fill=0)
        seen = env.object(8, "vtable-call-log", fill=0)

        def probe(env, call):
            env.put(seen, call.receiver, env.calls_so_far(call.function))
            return vtable_result

        def record_setter(env, call):
            env.put(obj + 0x130, call.receiver, env.calls_so_far(call.function), *call.arguments)
            return 0

        env.override(SET_VIEWPORT, record_setter)
        env.put(obj, methods)
        env.put(methods + 0x0C, env.stub("view probe", "thiscall", 0, probe))
        records = []
        for index in range(max(count, 0)):
            flags = flag_values[index % len(flag_values)]
            record = env.object(0x10, f"record-{index}", words=[marker + index, marker + 0x100 + index, flags, marker + 0x200 + index])
            records.append(record)
        table = env.object(max(4, 4 * len(records)), "table", words=records or [0])
        info = env.object(0x50, "info", fill=0)
        world = env.object(0x40, "world", fill=0)
        env.put(info + 0x00, marker + 0x300, marker + 0x301)
        env.put(info + 0x38, table if has_table else 0)
        env.put(info + 0x3C, count if count_field is None else count_field)
        env.put(info + 0x40, marker + 0x302)
        env.put(world + 0x00, marker + 0x400)
        env.put(world + 0x24, info if has_info else 0)
        env.put(world + 0x28, marker + 0x401)
        if null_slot and records:
            index = {4: 2}.get(count, count - 1)
            env.put(table + 4 * index, 0)
        env.put(obj + 0x30, world if has_world else 0)
        env.put(obj + 0x68, field_68)
        env.put(obj + 0x128, field_128)
        env.put(obj + 0x12C, marker + 0x500)
        return {"obj": obj, "records": records, "table": table, "seen": seen}
    return setup


def cases(random_source):
    rnd = random_source

    # 0x422350: clear a string owner.
    for old in (0, 1, 0xDEADBEEF, rnd.randrange(1, 1 << 32), rnd.randrange(1, 1 << 32)):
        yield Case(f"clear owner, +0x30 was {old:#x}", CLEAR_OWNER, owner(old), receiver=lambda t: t["obj"])
    for nodes in range(4):
        for blocks in range(3):
            for string in (False, True):
                yield Case(f"clear owner nodes {nodes} blocks {blocks} string {string}", CLEAR_OWNER,
                           owner(rnd.randrange(1, 1 << 32), nodes, blocks, string, seed=rnd.randrange(0x1000, 1 << 20)),
                           receiver=lambda t: t["obj"])

    # 0x4296f0: SetRect forwarding, with the default stand-in and with a faithful one.
    def faithful(env, call):
        env.put(call.arguments[0], *call.arguments[1:5])
        return 1

    def failing(env, call):
        env.put(call.arguments[0], 0xF0F0F0F0)
        return 0

    values = [(0, 0, 0, 0), (1, 2, 3, 4), (4, 3, 2, 1), (0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 1),
              (10, 20, 640, 480), (0x100, 0, 0, 0x200)]
    values += [tuple(rnd.randrange(0, 1 << 32) for _ in range(4)) for _ in range(6)]
    values += [tuple(rnd.randrange(0, 2000) for _ in range(4)) for _ in range(4)]
    for number, args in enumerate(values):
        initial = [0x01010101 * (number % 200 + 1), 0x02020202, 0x03030303, 0x04040404]

        def silent(env, initial=initial):
            tokens = rect(initial)(env)
            env.override(SET_RECT, returns(1))
            return tokens

        yield Case(f"rect silent {args}", RECT, silent, receiver=lambda t: t["obj"], arguments=args)

        def with_effect(env, effect=faithful, initial=initial):
            tokens = rect(initial)(env)
            env.override(SET_RECT, effect)
            return tokens

        yield Case(f"rect faithful {args}", RECT, with_effect, receiver=lambda t: t["obj"], arguments=args)
    yield Case("rect service fails", RECT, lambda env: (lambda t: (env.override(SET_RECT, failing), t)[1])(rect([5, 6, 7, 8])(env)),
               receiver=lambda t: t["obj"], arguments=(9, 10, 11, 12))

    # 0x42ce20: enable or disable the view's record.
    flag_sets = [(0,), (1,), (2,), (3,), (0xFFFFFFFC,), (0xFFFFFFFF,), (0x80000000,), (0x10, 0x20, 0x30, 0x41, 0x52, 0x63)]
    for count in (1, 2, 3, 4, 5, 6):
        for flags in flag_sets:
            for param in (0, 1, rnd.randrange(2, 1 << 32)):
                yield Case(f"enable count {count} flags {flags[0]:#x} param {param:#x}", SET_ENABLED,
                           view(count, flags, marker=0x10000 * count), receiver=lambda t: t["obj"], arguments=(param,))
    for count in (0, -1, -5, -0x80000000):
        for param in (0, 1):
            yield Case(f"enable count {count} gives no record, param {param}", SET_ENABLED,
                       view(0, (0,), marker=0x70000, count_field=count & 0xFFFFFFFF), receiver=lambda t: t["obj"],
                       arguments=(param,))
    for count in (1, 2, 4, 5):
        for param in (0, 1):
            yield Case(f"enable null record count {count} param {param}", SET_ENABLED,
                       view(count, (0, 2), null_slot=True), receiver=lambda t: t["obj"], arguments=(param,))
    for param in (0, 1, 7):
        yield Case(f"enable vtable returns 0, param {param}", SET_ENABLED, view(3, (0,), vtable_result=0),
                   receiver=lambda t: t["obj"], arguments=(param,))
        yield Case(f"enable vtable returns negative, param {param}", SET_ENABLED, view(3, (0,), vtable_result=0xFFFFFFFF),
                   receiver=lambda t: t["obj"], arguments=(param,))
        yield Case(f"enable no world, param {param}", SET_ENABLED, view(3, (0,), has_world=False),
                   receiver=lambda t: t["obj"], arguments=(param,))
        yield Case(f"enable no info, param {param}", SET_ENABLED, view(3, (0,), has_info=False),
                   receiver=lambda t: t["obj"], arguments=(param,))
    for count in (4, 3):
        # A set high bit pattern in the unrelated flag bits must survive.
        for flags in (0x0, 0xA5A5A5A4, 0xA5A5A5A6, 0xA5A5A5A5, 0xA5A5A5A7):
            yield Case(f"enable preserves other flag bits {flags:#x} count {count}", SET_ENABLED,
                       view(count, (flags,), field_128=0), receiver=lambda t: t["obj"], arguments=(rnd.randrange(0, 2),))

    # 0x42d1f0: refresh, which reapplies the stored state and then calls the viewport setter.
    for count in (1, 2, 4, 5):
        for stored in (0, 1, rnd.randrange(2, 1 << 32)):
            for param in (0, 1, rnd.randrange(2, 1 << 32)):
                yield Case(f"refresh count {count} stored {stored:#x} param {param:#x}", REFRESH,
                           view(count, (0, 1, 2, 3), field_128=stored, field_68=rnd.randrange(1, 1 << 32)),
                           receiver=lambda t: t["obj"], arguments=(param,))
    for param in (0, 5):
        yield Case(f"refresh vtable returns 0, param {param}", REFRESH, view(3, (0,), vtable_result=0, field_128=1),
                   receiver=lambda t: t["obj"], arguments=(param,))
        yield Case(f"refresh no world, param {param}", REFRESH, view(3, (0,), has_world=False),
                   receiver=lambda t: t["obj"], arguments=(param,))

    def setter_writes(env):
        tokens = view(3, (0,), field_128=1)(env)

        def setter(env, call):
            env.put(tokens["obj"] + 0x12C, call.receiver, *call.arguments)
            env.put(tokens["obj"] + 0x128, 0x9999)  # state changes after the first step, not before it
            return 0

        env.override(SET_VIEWPORT, setter)
        return tokens

    yield Case("refresh records the viewport setter's receiver and arguments", REFRESH, setter_writes,
               receiver=lambda t: t["obj"], arguments=(0xABCD1234,))

    def setter_returns(env):
        tokens = view(2, (0, 2), field_128=0, field_68=0x4242)(env)
        env.override(SET_VIEWPORT, returns(0x77))
        return tokens

    yield Case("refresh with overridden viewport setter", REFRESH, setter_returns, receiver=lambda t: t["obj"], arguments=(3,))
