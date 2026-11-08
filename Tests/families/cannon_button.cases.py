"""Returning CannonButton paths with synthetic resources and callback records."""
from clawparity.cases import Case
from clawparity.world import world, animation, sprite, cstring

ENTRY = 0x414CC0
NEW = 0x4F63EC


def cases(random_source):
    for state_value in (1, 2, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        for change in (False, True):
            values = [random_source.getrandbits(32) for _ in range(32)]

            def setup(env, state_value=state_value, change=change, values=values):
                owner = env.object(0x200, 'owner', words=values)
                state = env.object(0x180, 'state', words=values[::-1])
                alternate_state = env.object(0x180, 'alternate-state', words=values)
                runtime = env.object(0x54, 'runtime', words=values[:21])
                alternate_runtime = env.object(0x54, 'alternate-runtime', words=values[1:22])
                table = env.object(0x24, 'callback-table', fill=0)
                record = env.object(0x200, 'observations', fill=0)
                env.put(owner + 0x6C, state)
                env.put(state + 0x18, runtime, state_value)
                env.put(runtime, table)
                env.put(runtime + 0x10, state)
                env.put(alternate_runtime, table)
                env.put(alternate_runtime + 0x10, state)

                def effect(tag, argc):
                    def observe(env, call):
                        index = env.get(record)
                        at = record + 4 + index * 40
                        env.put(at, tag, call.receiver, env.get(state + 0x18), env.get(state + 0x1C),
                                env.get(owner + 0x6C), env.get(call.receiver + 0x10), argc,
                                *(list(call.arguments) + [0] * (3 - argc)))
                        env.put(record, index + 1)
                        if change:
                            env.put(owner + 0x6C, alternate_state)
                            env.put(state + 0x18, alternate_runtime)
                            env.put(state + 0x1C, values[25])
                        env.put(call.receiver + 0x40, values[tag % len(values)])
                        return values[(tag + 1) % len(values)]
                    return observe

                for offset, argc in ((4, 1), (8, 1), (12, 1), (0x10, 0), (0x1C, 0), (0x20, 0)):
                    env.put(table + offset, env.stub('runtime-%x' % offset, 'thiscall', argc, effect(offset, argc)))
                text = cstring(env, 'distinct-state-%08x' % values[24])
                strings = env.object(4, 'state-string-array', words=[text])
                env.put(0x5376A0, state_value, state_value, strings, strings, 4, 0, 0)
                return {'owner': owner}
            yield Case('state %08x callbacks change=%s' % (state_value, change), ENTRY, setup,
                       arguments=(lambda t: t['owner'],))

    for hits in (False, True):
        for variant in range(6):
            values = [random_source.getrandbits(32) for _ in range(64)]

            def setup(env, hits=hits, variant=variant, values=values):
                resources = {}
                if hits:
                    resources = {
                        'sprites': {'LEVEL_CANNONBUTTON': sprite(env, 17 + variant, 35 + variant,
                                                              (variant - 8, 11 - variant))},
                        'animations': {'LEVEL_CANNONBUTTON_IDLE': animation(env, 13 + variant)},
                        'sounds': {'LEVEL_GABRIELCANNON_BUTTON1': env.object(36, 'sound', words=values[:9])},
                    }
                t = world(env, resources=resources, idle_state=variant + 1, bucket_count=1 if variant % 2 else 17)
                owner, state = t['owner'], t['state']
                for offset in (0xD0, 0xD4, 0x128, 0x12C, 0x130, 0x134, 0x138, 0x13C, 0x140, 0x144):
                    env.put(owner + offset, values[offset // 4 % 64])
                sentinel = env.object(0x54, 'prepublication-runtime', words=values[:21])
                env.put(state + 0x18, sentinel, 0)
                record = env.object(0x300, 'construction-observations', fill=0)
                allocated = env.object(0x54, 'constructed-runtime', words=values[21:42])

                def observe(env, call, tag):
                    index = env.get(record)
                    env.put(record + 4 + index * 32, tag, call.receiver, env.get(state + 0x18),
                            env.get(state + 0x1C), env.get(owner + 0x6C),
                            env.get(allocated), *(list(call.arguments) + [0, 0])[:2])
                    env.put(record, index + 1)
                    return values[tag % 64]

                def allocate(env, call):
                    observe(env, call, 1)
                    return allocated
                env.override(NEW, allocate)
                if hits:
                    table = env.object(0x28, 'logic-methods', fill=0)
                    for offset in (0x70, 0x78):
                        logic = env.object(0x174, 'existing-logic-%x' % offset, fill=0)
                        env.put(logic, table)
                        env.put(owner + offset, logic)
                    def reset(env, call):
                        observe(env, call, 2)
                        env.put(call.receiver + 0x10, values[43])
                        return values[44]
                    def select(env, call):
                        observe(env, call, 3)
                        env.put(call.receiver + 0x14, values[45])
                        return values[46]
                    env.put(table + 0x1C, env.stub('logic-reset', 'thiscall', 0, reset))
                    env.put(table + 0x24, env.stub('logic-select', 'thiscall', 2, select))
                    from clawparity.world import resource_manager
                    hit = env.object(0x14, 'hit-logic', words=values[:5])
                    attack = env.object(0x14, 'attack-logic', words=values[5:10])
                    manager = resource_manager(env, {'LogicHit': hit, 'LogicAttack': attack}, bucket_count=1)
                    env.put(t['world'] + 0x14, manager)
                return t
            yield Case('construction resources=%s variant=%d' % (hits, variant), ENTRY, setup,
                       arguments=(lambda t: t['owner'],))

    # The owner and allocation overlap ordinary animation timing storage.
    # The original constructor's duration store consequently supplies the
    # callback table; no game instruction or original vtable is replaced.
    for variant in range(8):
        values = [random_source.getrandbits(32) for _ in range(24)]
        def setup(env, variant=variant, values=values):
            record = env.object(0x180, 'initialization-publication-observations', fill=0)
            table = env.object(0x24, 'supplied-animation-timing-table', fill=0)
            sequence = animation(env, table, 'overlapping-timing-animation')
            t = world(env, resources={'animations': {'LEVEL_CANNONBUTTON_IDLE': sequence}},
                      idle_state=variant + 17, bucket_count=1 if variant % 2 else 17)
            owner, state = t['owner'], t['state']
            allocated = owner + 0x1AC
            previous = env.object(0x54, 'previous-published-runtime', words=values[:21])
            replacement = env.object(0x54, 'callback-published-runtime', words=values[1:22])
            other_state = env.object(0x180, 'callback-owner-state', fill=0)
            env.put(state + 0x18, previous, 0)
            env.put(state + 0x14, values[22])
            env.put(other_state + 0x18, replacement, values[23])

            def allocation(env, call):
                env.put(record, call.arguments[0], env.get(state + 0x18), env.get(state + 0x1C))
                return allocated

            def initialize(env, call):
                env.put(record + 0x20, call.receiver, env.get(state + 0x18), env.get(state + 0x1C),
                        env.get(owner + 0x6C), env.get(call.receiver), env.get(call.receiver + 0x10),
                        env.get(call.receiver + 0x24), env.get(call.receiver + 0x34))
                env.write(record + 0x60, env.read(call.receiver, 0x54))
                env.put(state + 0x18, replacement)
                env.put(state + 0x1C, values[21])
                if variant % 2:
                    env.put(owner + 0x6C, other_state)
                env.put(call.receiver + 0x50, values[20])
                return values[19]

            env.put(table + 0x10, env.stub('initialize-after-original-timing-store', 'thiscall', 0, initialize))
            env.override(NEW, allocation)
            return t
        yield Case('overlapping original timing and allocation variant=%d' % variant, ENTRY, setup,
                   arguments=(lambda t: t['owner'],))
