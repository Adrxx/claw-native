"""Blind original-code cases for Omar's dispatch and construction."""
from clawparity.cases import Case
from clawparity.world import world, rectangle_services, cstring, animation, sprite

ENTRY = 0x4633A0
NEW = 0x4F63EC


def registry(env, idle, startup):
    # Two leaf Patricia nodes, split at the first differing bit of I and S.
    a = env.object(20, "idle-node", fill=0)
    b = env.object(20, "startup-node", fill=0)
    root = env.object(20, "registry-root", fill=0)
    env.put(a, a, a, 0, cstring(env, "LS_IDLE"), idle)
    env.put(b, b, b, 0, cstring(env, "LS_STARTUP"), startup)
    env.put(root, a, b, 25, cstring(env, "LS_IDLE"), idle)
    env.put(0x537680, root)


def setup_case(state_code, values, mode="dispatch", mutate=False):
    def setup(env):
        rectangle_services(env)
        record = env.object(0x200, "callback-observations", fill=0)
        token = world(env, owner_words={0x4C: values[0], 0x50: values[1], 0x64: values[2]},
                      state_words={0x1C: state_code, 0x2C: values[3], 0x34: values[4]})
        owner, state = token["owner"], token["state"]
        env.put(state + 0xC, token["world"])
        target = env.object(0xD48, "dispatch-target", fill=values[5] & 255)
        table = env.object(0x50, "dispatch-table", fill=0)
        env.put(target, table)
        env.put(target + 0x10, state)
        env.put(state + 0x18, target)
        def observe(slot, argc):
            def effect(env, call):
                count = env.get(record)
                at = record + 4 + count * 32
                env.put(at, slot, call.receiver, env.get(state + 0x1C),
                        env.get(state + 0x18), *call.arguments)
                env.put(record, count + 1)
                if mutate:
                    env.put(state + 0x18, alternate)
                    env.put(state + 0x1C, values[6])
                return values[7]
            return env.stub("observed-slot-%x" % slot, "thiscall", argc, effect)
        alternate = env.object(0xD48, "alternate-publication", fill=0xA3)
        for slot, argc in ((4, 1), (8, 1), (12, 1), (16, 0), (28, 0), (32, 0)):
            env.put(table + slot, observe(slot, argc))
        # Numeric state strings consumed by unchanged default dispatch.
        text = cstring(env, "STATE_%08x" % state_code)
        string_slot = env.object(4, "numeric-state-string", words=[text])
        env.put(0x5376A0, state_code, state_code, string_slot, string_slot, 4, 0, 0)
        if mode != "dispatch":
            # Shield spawning runs normal original constructors against a backed manager.
            spawn = env.object(0x40, "shield-object-manager", fill=0)
            env.put(spawn + 0xC, token["world"])
            env.put(spawn + 0x28, 16)
            env.put(token["world"] + 8, spawn)
            logic = env.object(0x14, "shield-definition", fill=0)
            def shield_callback(env, call):
                index = env.get(record + 0x100)
                env.put(record + 0x104 + index * 8, call.arguments[0],
                        env.get(call.arguments[0] + 8))
                env.put(record + 0x1A0, env.get(state + 0x1C), env.get(state + 0x18))
                env.put(record + 0x100, index + 1)
                return values[7]
            descriptor = env.stub("shield-logic", "cdecl", 1, shield_callback)
            env.put(logic + 0x10, descriptor)
            from clawparity.world import resource_manager
            env.put(token["world"] + 0x14,
                    resource_manager(env, {"OmarShield": logic}, name="shield-logic"))
            registry(env, 1, 2)
            if mode.endswith("hits"):
                animations = {key: animation(env, 1 + index * 19)
                              for index, key in enumerate(("LEVEL_OMAR_HITHIGH", "LEVEL_OMAR_HITLOW",
                                  "LEVEL_OMAR_IDLE", "LEVEL_OMAR_KILLFALL", "LEVEL_OMAR_KILLFALL3",
                                  "LEVEL_OMAR_STRIKE1", "LEVEL_OMAR_BLOCK", "GAME_NULL"))}
                env.put(token["world"] + 0x2C,
                        resource_manager(env, animations, bucket_count=1, name="hit-animations"))
                env.put(token["world"] + 0x10, resource_manager(env,
                        {"LEVEL_OMAR": sprite(env, 47, 63, (3, -9))}, name="hit-sprites"))
            def allocate(env, call):
                result = env.object(call.arguments[0], "constructor-allocation", fill=values[5] & 255)
                if call.arguments[0] == 0xD48:
                    env.put(record + 0x180, env.get(state + 0x1C), env.get(state + 0x18), result)
                return result
            env.override(NEW, allocate)
        return {"owner": owner}
    return setup


def cases(random_source):
    values = [random_source.randrange(1, 2000) for _ in range(8)]
    for code in (1, 28, 29, 30, 31, 999, 1000, 1001, 0xFFFFFFFF, 0x80000000):
        for mutate in (False, True):
            values = [random_source.randrange(1, 2000) for _ in range(8)]
            yield Case("dispatch %08x mutate %s" % (code, mutate), ENTRY,
                       setup_case(code, values, mutate=mutate), arguments=(lambda x: x["owner"],))
    for mode in ("misses", "hits"):
        values = [random_source.randrange(1, 2000) for _ in range(8)]
        yield Case("complete construction " + mode, ENTRY, setup_case(0, values, mode),
                   arguments=(lambda x: x["owner"],))
