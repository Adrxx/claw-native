"""Original TowerCannonRight dispatch, construction and callback observations."""
from clawparity.cases import Case
from clawparity.world import world, sprite, animation, cstring

ENTRY = 0x495E00
NEW = 0x4F63EC


def cases(random_source):
    for state_value in (0, 1, 2, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        for resources_present in (range(5) if state_value == 0 else (0,)):
            words = [random_source.getrandbits(32) for _ in range(31)]
            duration = random_source.randrange(1, 10000)
            marker = random_source.getrandbits(32)

            def setup(env, value=state_value, hits=resources_present, initial=words,
                      duration=duration, marker=marker):
                resources = {}
                if hits:
                    resources = {
                        'sprites': {'LEVEL_TOWERCANNONRIGHT': sprite(env, 31, 47, (-7, 11))},
                        'animations': {
                            'LEVEL_TOWERCANNONRIGHT_HOME': animation(env, duration, 'home'),
                            'LEVEL_TOWERCANNONRIGHT_FIRING': animation(env, duration + 19, 'firing'),
                        },
                    }
                if not (hits & 1):
                    resources.pop('sprites', None)
                if not (hits & 2):
                    resources.pop('animations', None)
                tokens = world(env, resources=resources, bucket_count=1,
                               owner_words={8: marker & ~0x20000, 0x148: marker if hits else 0,
                                            0x104: duration if hits else 0,
                                            0x64: duration if hits else 0,
                                            0x14C: marker ^ 0x89132 if hits else 0,
                                            0x190: marker ^ 0x91372},
                               state_words={0x1C: value})
                owner, state = tokens['owner'], tokens['state']
                old = env.object(0x7C, 'previous-controller', words=initial)
                vt = env.object(0x24, 'controller-methods', fill=0)
                env.put(old, vt)
                env.put(old + 0x10, state)
                env.put(state + 0x18, old)
                record = env.object(0x100, 'callback-observations', fill=0)
                other_state = env.object(0x180, 'replacement-owner-state', fill=0)
                count = env.object(4, 'callback-count', fill=0)

                def callback(slot, argc):
                    def effect(env, call):
                        index = env.get(count)
                        at = record + index * 0x20
                        env.put(at, slot, call.receiver, env.get(state + 0x1C),
                                env.get(state + 0x18), env.get(owner + 0x6C),
                                *call.arguments)
                        env.put(count, index + 1)
                        env.put(state + 0x20, marker ^ slot)
                        env.put(owner + 0x6C, other_state)
                        return marker ^ 0xDEADBEEF
                    return env.stub('controller-slot-' + str(slot), 'thiscall', argc, effect)

                for slot, argc in ((0x10, 0), (4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
                    env.put(vt + slot, callback(slot, argc))
                if value == 0 and hits == 4:
                    # Allocate inside the backed state record. Constructor's final
                    # state-ID write overlaps its own vtable word at state+0x1c.
                    # The singleton registry returns our fresh callback table; no
                    # instruction or original vtable entry is changed.
                    env.put(tokens['idle_registry'] + 12,
                            cstring(env, 'LS_HOME', 'alias-home-state'), vt)
                # The unchanged generic dispatch reads an indexed CString pair.
                key = cstring(env, 'LS_SYNTHETIC_' + str(duration), 'dispatch-state-name')
                table = env.object(12, 'dispatch-state-table', words=[key, marker, marker ^ 1])
                env.put(0x5376A0, value, value, table)
                env.put(0x5376B0, 12)

                def allocation(env, call):
                    env.put(record + 0xE0, call.arguments[0], env.get(state + 0x1C),
                            env.get(state + 0x18), env.get(owner + 0x6C))
                    if value == 0 and hits == 4:
                        return state + 0x1C
                    return env.object(call.arguments[0], 'new-controller', words=initial)

                env.override(NEW, allocation)
                return tokens

            yield Case(f'state {state_value:#x} resource-mask {resources_present}', ENTRY,
                       setup, arguments=(lambda t: t['owner'],))
