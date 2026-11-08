"""Original-only AquatisDynamite inputs and persistent callback observations."""
from clawparity.cases import Case
from clawparity.world import world, sprite, cstring

ENTRY = 0x406DD0
NEW = 0x4F63EC


def build_setup(command, values, *, constructor=False, alias=False, resources=False, boss=False, effects=False):
    def setup(env):
        tokens = world(env, owner_words={8: values[0], 0x40: values[1], 0x4c: values[2], 0x50: values[3]},
                       state_words={0x1c: command, 0x2c: values[4], 0x30: values[5], 0x34: values[6], 0x38: values[7]},
                       bucket_count=1 if resources else 17)
        owner, state = tokens['owner'], tokens['state']
        log = env.object(0x600, 'surviving-observations', fill=0)
        table = env.object(0x30, 'callback-table', fill=0)
        second_table = env.object(0x30, 'replacement-callback-table', fill=0)
        target = env.object(0x80, 'existing-dynamite', words=[table], fill=0x97)
        alternate = env.object(0x80, 'alternate-dynamite', words=[second_table], fill=0x53)
        env.put(target + 0x10, state)
        env.put(alternate + 0x10, state)
        env.put(state + 0x18, target)
        decoy_state = env.object(0x180, 'replacement-owner-state', fill=0x51)

        def record(tag, mutate=False):
            def callback(env, call):
                index = env.get(log)
                env.put(log + 4 + index * 0x70, tag, call.receiver, len(call.arguments),
                        *call.arguments, *([0] * (3-len(call.arguments))))
                at = log + 4 + index * 0x70 + 0x18
                env.write(at, env.read(state, 0x40))
                env.put(at + 0x40, env.get(owner + 0x6c), env.get(owner + 0x128), env.get(owner + 0x40))
                env.put(log, index + 1)
                if mutate:
                    env.put(state + 0x18, alternate)
                    env.put(call.receiver, second_table)
                    env.put(owner + 0x6c, decoy_state)
                    env.put(state + 0x1c, values[9])
                return values[8] ^ tag
            return callback

        for offset in (4, 8, 12, 0x10, 0x1c, 0x20, 0x24):
            env.put(table + offset, env.stub(f'primary-{offset:x}', 'thiscall', 1 if offset in (4,8,12) else 0,
                                            record(offset, effects and offset in (4,0x10,0x1c,0x20))))
            env.put(second_table + offset, env.stub(f'secondary-{offset:x}', 'thiscall', 1 if offset in (4,8,12) else 0,
                                                   record(0x100 + offset)))
        if not constructor:
            # Each table entry is an actual CString, consumed by unchanged dispatch.
            entry = env.object(4, 'numeric-state-name', words=[cstring(env, f'STATE_{command:08x}')])
            env.put(0x5376a0, command, command, entry, entry, 4, 0, 0)
        else:
            service = env.object(0x40, 'level-object-service', fill=0)
            env.put(service + 8, owner)
            env.put(state + 0xc, service)
            env.put(0x537e88, owner)
            actor = env.object(0x500, 'optional-global-actor', fill=0x69)
            env.put(0x534874, actor if boss else 0)
            if boss:
                boss_data = env.object(0x80, 'boss-state', fill=0x42)
                env.put(boss_data + 0x78, values[9])
                env.put(state + 0x14, boss_data)
            if resources:
                from clawparity.world import resource_manager
                spr = sprite(env, width=17 + values[9] % 23, height=11 + values[8] % 19,
                             origin=(values[2], values[3]))
                logic_hit = env.object(0x20, 'hit-resource', fill=0x25)
                logic_attack = env.object(0x20, 'attack-resource', fill=0x84)
                env.put(logic_hit + 0x10, values[4])
                env.put(logic_attack + 0x10, values[5])
                manager = resource_manager(env, {'LogicHit': logic_hit, 'LogicAttack': logic_attack}, bucket_count=1)
                sprites = resource_manager(env, {'GAME_DYNAMITE': spr}, bucket_count=1)
                env.put(tokens['world'] + 0x10, sprites, manager)
                # Existing user-supplied logic receivers avoid introducing other constructors.
                for offset, tag in ((0x70, 0x200), (0x78, 0x300)):
                    vt = env.object(0x30, f'logic-table-{offset:x}', fill=0)
                    receiver = env.object(0x180, f'logic-receiver-{offset:x}', words=[vt], fill=0x33)
                    env.put(vt + 0x1c, env.stub(f'logic-clear-{offset:x}', 'thiscall', 0, record(tag)))
                    env.put(vt + 0x24, env.stub(f'logic-select-{offset:x}', 'thiscall', 2, record(tag+1)))
                    env.put(owner + offset, receiver)
            if alias:
                # A fully backed owner subobject; unchanged constructor coordinate
                # stores publish the fresh callback table over its initial vtable.
                env.put(state + 0x2c, table, values[6], owner, owner)
                allocation = owner + 0x128
            else:
                allocation = env.object(0x54, 'constructor-storage', fill=0xb7)
            def allocate(env, call):
                index = env.get(log)
                env.put(log + 4 + index*0x70, 0x400, call.receiver, call.arguments[0],
                        env.get(state + 0x1c), env.get(state + 0x18))
                env.put(log, index + 1)
                return allocation
            env.override(NEW, allocate)
        return tokens
    return setup


def cases(random_source):
    for command in (1, 2, 28, 29, 30, 31, 999, 1000, 1001, 0x7fffffff, 0x80000000, 0xffffffff):
        for effects in (False, True):
            values = [random_source.randrange(1, 0xffffffff) for _ in range(10)]
            yield Case(f'command {command:#x} effects {effects}', ENTRY,
                       build_setup(command, values, effects=effects), arguments=(lambda t:t['owner'],))
    for alias in (False, True):
        for resources in (False, True):
            for boss in (False, True):
                for effects in (False, True):
                    values = [random_source.randrange(1, 0xffffffff) for _ in range(10)]
                    yield Case(f'construct alias {alias} resources {resources} boss {boss} effects {effects}', ENTRY,
                               build_setup(0, values, constructor=True, alias=alias, resources=resources,
                                           boss=boss, effects=effects), arguments=(lambda t:t['owner'],))
