"""Original-only construction and dispatch inputs for RedTailSpikes."""
from clawparity.cases import Case
from clawparity.world import world, cstring

ENTRY = 0x4842B0
NEW = 0x4F63EC


def cases(random_source):
    samples = [random_source.getrandbits(32) for _ in range(24)]

    def setup_case(state_value, construct=False, hits=False, alias=False):
        def setup(env):
            tokens = world(env, owner_words={0x104: samples[0], 0x138: samples[1],
                            0x13C: samples[2], 0x140: samples[3], 0x144: samples[4]},
                           state_words={0x1C: state_value}, idle_state=samples[5] & 0x7FFFFFFF)
            owner, state = tokens['owner'], tokens['state']
            log = env.object(0x400, 'callback-observations', fill=0)
            table = env.object(0x28, 'callback-table', fill=0)
            obj = env.object(0x48, 'prior-behavior', words=samples[:18])
            env.put(obj, table)
            env.put(obj + 0x10, state)
            env.put(state + 0x18, obj)

            def record(tag, argc):
                def effect(env, call):
                    index = env.get(log)
                    env.put(log, index + 1)
                    at = log + 4 + index * 0x40
                    env.put(at, tag, call.receiver, len(call.arguments), *call.arguments)
                    env.put(at + 0x18, env.get(state + 0x18), env.get(state + 0x1C),
                            env.get(owner + 0x104), env.get(owner + 0x138),
                            env.get(owner + 0x13C), env.get(owner + 0x140), env.get(owner + 0x144))
                    if tag == 16:
                        env.write(log + 0x300, env.read(call.receiver, 0x48))
                        env.put(state + 0x18, obj)
                        env.put(state + 0x1C, samples[12])
                    env.put(call.receiver + 4, samples[tag % len(samples)])
                    return samples[(tag + 1) % len(samples)]
                return env.stub('record-' + str(tag), 'thiscall', argc, effect)

            for offset, argc in ((4, 1), (8, 1), (12, 1), (16, 0), (28, 0), (32, 0)):
                env.put(table + offset, record(offset, argc))
            # Numeric state-to-string records used by the unchanged dispatch helper.
            text = cstring(env, 'distinct-state-text')
            record_data = env.object(12, 'state-string-record', words=[text, samples[6], samples[7]])
            env.put(0x5376A0, state_value, state_value, record_data, record_data, 12, 0, 0)

            if construct:
                if hits:
                    from clawparity.world import resource_manager
                    resources = {}
                    for index, key in enumerate(('LogicHit', 'LogicAttack')):
                        resource = env.object(0x20, key + '-resource', words=samples[:8])
                        env.put(resource + 0x10, samples[10 + index])
                        resources[key] = resource
                        target = env.object(0x180, key + '-receiver', fill=0)
                        methods = env.object(0x28, key + '-methods', fill=0)
                        env.put(target, methods)
                        env.put(methods + 0x1C, record(40 + index, 0))
                        env.put(methods + 0x24, record(44 + index, 2))
                        env.put(owner + (0x70 if index == 0 else 0x78), target)
                    manager = resource_manager(env, resources, bucket_count=1, name='logic-hit-map')
                    env.put(tokens['world'] + 0x14, manager)
                if alias:
                    # The original constructor's bounds writes publish this fresh
                    # callback table through a fully backed allocation alias.
                    allocation = owner + 0x138
                    rect = env.object(0x28, 'constructor-bounds', fill=0)
                    left = (owner + 1 - table) // 2
                    top = (owner + 1 - samples[8]) // 2
                    env.put(rect + 0x18, left, top, left + table, owner + 1 - top)
                    env.put(owner + 0x174, rect)
                else:
                    allocation = env.object(0x48, 'constructed-behavior', words=samples[:18])
                def allocation_effect(env, call):
                    env.put(log + 0x3C0, call.arguments[0], env.get(state + 0x1C), env.get(state + 0x18))
                    return allocation
                env.override(NEW, allocation_effect)
            return tokens
        return setup

    for value in (1, 28, 29, 30, 31, 999, 1000, 1001, 0xFFFFFFFF, 0x80000000,
                  samples[20] | 0x10000, samples[21] | 0x10000):
        yield Case('dispatch-' + hex(value), ENTRY, setup_case(value), arguments=(lambda t: t['owner'],))
    for hits in (False, True):
        for alias in (False, True):
            yield Case(f'construction hits={hits} alias={alias}', ENTRY,
                       setup_case(0, True, hits, alias), arguments=(lambda t: t['owner'],))
