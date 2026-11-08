"""Blind original-only cases for the JumpSwitch callback."""
from clawparity.cases import Case
from clawparity.world import world, cstring, resource_manager

ENTRY = 0x453B10
NEW = 0x4F63EC


def cases(random_source):
    states = (0, 1, 28, 29, 30, 31, 999, 1000, 1001, 0x7fffffff,
              0x80000000, 0xffffffff)
    for iteration in range(4):
        for state_id in states:
            owner_data = {offset: random_source.getrandbits(32)
                          for offset in (4, 0xD0, 0xD4, 0x138, 0x13C, 0x140, 0x144)}
            marker = random_source.getrandbits(32) | 1
            payload = bytes(random_source.randrange(1, 256) for _ in range(0x48))

            def setup(env, state_id=state_id, owner_data=owner_data,
                      marker=marker, payload=payload, iteration=iteration):
                token = world(env, owner_words=owner_data,
                              state_words={0x1C: state_id})
                owner, state = token['owner'], token['state']
                existing = env.object(0x48, 'previous-switch', data=payload)
                methods = env.object(0x24, 'switch-methods', fill=0)
                alternate = env.object(0x24, 'alternate-methods', fill=0)
                env.put(existing, methods)
                env.put(existing + 0x10, state)
                env.put(state + 0x18, existing)
                text = cstring(env, 'switch-state-%08x' % marker, 'state-name')
                table = env.object(4, 'state-name-cell', words=[text])
                env.put(0x5376A0, 0x80000000, 0x7FFFFFFF, table)
                env.put(0x5376B0, 0, 0, 0)

                def callback(offset):
                    def effect(env, call):
                        env.put(call.receiver + 0x34, marker ^ offset)
                        env.put(owner + 0x148, marker + offset)
                        env.put(state + 0x20, marker ^ 0x35)
                        return marker ^ 0xA5A5A5A5
                    return effect

                for offset in (0x1C, 0x20):
                    env.put(methods + offset,
                            env.stub('switch-%x' % offset, 'thiscall', 0, callback(offset)))

                def first(env, call):
                    env.put(call.receiver + 0x34, marker)
                    env.put(call.receiver, alternate)
                    env.put(owner + 0x148, marker ^ 0xF0)
                    # The dispatcher captures the state ID before callbacks.
                    env.put(state + 0x1C, 1000)
                    return marker

                def second(env, call):
                    env.put(call.receiver + 0x38, call.arguments[0])
                    env.put(call.receiver + 0x10, owner)
                    return marker ^ 0xFF

                def third(env, call):
                    env.put(call.receiver + 0x3C, call.arguments[0])
                    env.put(state + 0x18, owner)
                    return marker ^ 0xFFFF

                env.put(methods + 4, env.stub('dispatch-name-first', 'thiscall', 1, first))
                env.put(alternate + 8, env.stub('dispatch-state-reloaded-vtable', 'thiscall', 1, second))
                env.put(alternate + 0xC, env.stub('dispatch-name-last', 'thiscall', 1, third))

                def allocation(env, call):
                    # Check publication order without replacing the constructor.
                    if env.get(state + 0x1C) != 1000 or env.get(state + 0x18) != existing:
                        raise AssertionError('state transition/publication before allocation')
                    address = env.object(call.arguments[0], 'constructed-switch', data=payload)
                    env.put(owner + 0x148, marker ^ 0x1234)
                    return address

                if state_id == 0 and iteration:
                    entries = {}
                    for index, (key, owner_offset) in enumerate((('LogicHit', 0x70), ('LogicAttack', 0x78))):
                        resource = env.object(0x14, key + '-resource', fill=0)
                        env.put(resource + 0x10, marker ^ (index + 1))
                        entries[key] = resource
                        component = env.object(0x174, key + '-component', fill=0)
                        component_methods = env.object(0x28, key + '-methods', fill=0)
                        env.put(component, component_methods)
                        env.put(owner + owner_offset, component)
                        env.put(component_methods + 0x1C,
                                env.stub(key + '-reset', 'thiscall', 0, callback(0x70 + index)))

                        def bind(env, call, index=index):
                            env.put(call.receiver + 0x20, *call.arguments)
                            env.put(owner + 0x150 + 4 * index, marker ^ (index + 7))
                            env.put(state + 0x18, owner)
                            return marker ^ (index + 3)

                        env.put(component_methods + 0x24,
                                env.stub(key + '-bind', 'thiscall', 2, bind))
                    manager = resource_manager(env, entries, bucket_count=iteration)
                    env.put(token['world'] + 0x14, manager)
                env.override(NEW, allocation)
                return token

            yield Case('state %08x variant %d' % (state_id, iteration), ENTRY,
                       setup, arguments=(lambda token: token['owner'],))
