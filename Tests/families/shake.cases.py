"""Blind original-program cases for the Shake command dispatcher."""
from clawparity.cases import Case
from clawparity.world import world, resource_manager, cstring

ENTRY = 0x4887B0
NEW = 0x4F63EC


def setup_case(command, values, resource_mode="miss", effect_mode=False, reload=False):
    def setup(env):
        tokens = world(env, owner_words={
            8: values[0], 0x4C: values[1], 0x50: values[2],
            0x138: values[3], 0x13C: values[4], 0x140: values[5],
            0x144: values[6], 0x70: 0, 0x78: 0,
        }, state_words={0x1C: command})
        owner, state = tokens["owner"], tokens["state"]
        target = env.object(0x54, "existing-shake", words=values + values[:6], fill=0)
        env.put(target, 0x50F63C, 0, owner, owner, state, 0, 0, 1001)
        env.put(target + 0x20, 2, values[7], owner, owner, state)
        env.put(target + 0x48, 0, values[8], values[9])
        env.put(state + 0x18, target)
        # A singleton CString state table and handler table have honest bounds.
        string = cstring(env, "shake-state-" + str(command))
        names = env.object(4, "numeric-state-name", words=[string])
        env.put(0x5376A0, command, command, names, names, 4, 0, 0)
        handlers = env.object(4, "numeric-state-handler", words=[0x488CD0])
        env.put(0x53C2A8, command, command, handlers, handlers, 4, 0, 0)
        env.put(0x537210, values[10])
        if resource_mode != "miss":
            descriptor = env.object(0x14, "logic-descriptor", fill=0)
            payload = env.object(8, "logic-payload", words=values[:2])
            env.put(descriptor + 0x10, payload if resource_mode in ("hit", "reuse-hit", "logic-allocation-fails") else 0)
            resources = resource_manager(env, {"LogicHit": descriptor, "LogicAttack": descriptor})
            env.put(tokens["world"] + 0x14, resources)
        if resource_mode == "reuse-hit":
            for offset in (0x70, 0x78):
                logic = env.object(0x174, "existing-logic-" + str(offset), fill=0)
                scratch = env.object(16, "logic-scratch-" + str(offset), fill=0x6A)
                env.put(logic, 0x513740)
                env.put(logic + 0x10, values[0], scratch, 0)
                env.put(owner + offset, logic)
        if resource_mode == "logic-allocation-fails":
            def allocate_optional(env, call):
                if call.arguments[0] == 0x174:
                    return 0
                return env.object(call.arguments[0], "allocation", fill=0xA5)
            env.override(NEW, allocate_optional)
        if reload:
            replacement = env.object(0x180, "replacement-state", fill=0)
            env.put(replacement + 0x1C, values[11])
            def allocate_and_change(env, call):
                if call.arguments[0] == 0x54:
                    env.put(owner + 0x6C, replacement)
                    env.put(state + 0x1C, values[12])
                    env.put(owner + 0x4C, values[13])
                return env.object(call.arguments[0], "allocation", fill=0xA5)
            env.override(NEW, allocate_and_change)
        if effect_mode:
            methods = env.object(0x24, "callback-methods", fill=0)
            next_methods = env.object(0x24, "replacement-methods", fill=0)
            def first(env, call):
                env.put(target, next_methods)
                env.put(state + 0x18, 0)
                env.put(state + 0x1C, values[11])
                env.put(target + 0x24, call.arguments[0])
                return values[12]
            def later(env, call):
                env.put(target + 0x40 + 4 * (len(call.arguments) == 0), values[13])
                return values[14]
            for offset in (4, 8, 12, 0x1C, 0x20):
                argc = 1 if offset in (4, 8, 12) else 0
                env.put(methods + offset, env.stub("shake-method-" + str(offset), "thiscall", argc,
                                                first if offset == 4 else later))
                env.put(next_methods + offset, env.stub("reloaded-method-" + str(offset), "thiscall", argc, later))
            env.put(target, methods)
        return tokens
    return setup


def cases(random_source):
    values = random_source.sample(range(1, 100000), 15)
    commands = (0, 1, 2, 28, 29, 30, 31, 999, 1000, 1001, -1, -2, 0x7FFFFFFF)
    for command in commands:
        yield Case("command " + str(command), ENTRY, setup_case(command, values),
                   arguments=(lambda t: t["owner"],))
    for mode in ("hit", "empty-payload", "reuse-hit", "logic-allocation-fails"):
        yield Case("constructor resource " + mode, ENTRY, setup_case(0, values, mode),
                   arguments=(lambda t: t["owner"],))
    yield Case("constructor allocator changes owner state before original reload", ENTRY,
               setup_case(0, values, reload=True), arguments=(lambda t: t["owner"],))
    for command in (1, 28, 29, 30, 31, -1):
        yield Case("callback effects command " + str(command), ENTRY,
                   setup_case(command, values, effect_mode=True), arguments=(lambda t: t["owner"],))
