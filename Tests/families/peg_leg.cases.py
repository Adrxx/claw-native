"""Original-only PegLeg entry cases."""
from clawparity.cases import Case
from clawparity.fixtures import returns
from clawparity.world import world, rectangle_services, sprite, cstring, animation

ENTRY = 0x4689B0
NEW = 0x4F63EC


def constructor(mode, values, change=False):
    def setup(env):
        rectangle_services(env)
        resources = {}
        if mode != 'miss':
            seq = animation(env, duration=values[0], name='fallback')
            resources['animations'] = {'GAME_NULL': seq}
        if mode in ('hit', 'mixed'):
            names = ('HOME', 'ADVANCE', 'FASTADVANCE', 'HITHIGH', 'HITLOW', 'IDLE',
                     'JUMP', 'KILLFALL', 'LIFTED1', 'LIFTED2', 'STRIKE1', 'STRIKE2',
                     'THROWN', 'FORWARDROLL', 'BACKWARDROLL')
            for i, name in enumerate(names):
                if mode == 'mixed' and i % 2:
                    continue
                resources['animations']['LEVEL_PEGLEG_' + name] = animation(env, duration=values[0] + i + 1, name=name)
            sound_names = ('00410003', '00410004', '00410015', '00410016', '00410017',
                           '00410009', '00410005', '00410006', '00410007', '00410008',
                           '00410001', '00410002', '00410010', '00410011', 'ROLL1', 'SOLGUNFR8_22')
            resources['sounds'] = {
                'LEVEL_PEGLEG_' + name: env.object(0x40, 'sound-' + name, fill=(i + 11))
                for i, name in enumerate(sound_names) if mode == 'hit' or i % 2 == 0}
            resources['sprites'] = {'LEVEL_PEGLEG': sprite(env, width=values[1], height=values[2], origin=(3, 7))}
        tokens = world(env, resources=resources, bucket_count=1,
                       owner_words={0x4C: values[3], 0x50: values[4], 0x148: 2, 0x14C: -3,
                                    0x40: 2 if mode == 'mixed' else 0, 0x108: values[6], 0x114: values[7]},
                       state_words={0x2C: -120, 0x30: 210, 0x34: -140, 0x38: 240, 0x64: values[8] % 3, 0x68: values[9], 0x168: values[10]})
        env.put(tokens['state'] + 0x1C, 0)
        old = env.object(0x30, 'previous-child', fill=0x71)
        env.put(tokens['state'] + 0x18, old)
        env.override(0x4A3050, returns(values[5]))
        if change:
            replacement = env.object(0x180, 'replacement-state', data=env.read(tokens['state'], 0x180), fill=0)
            def allocate(env, call):
                env.put(tokens['state'] + 0x18, replacement)
                env.put(tokens['owner'] + 0x6C, replacement)
                env.put(tokens['state'] + 0x1C, 0xABCD)
                return env.object(call.arguments[0], 'new-child', fill=0x5A)
            env.override(NEW, allocate)
        return tokens
    return setup


def command(state_value, values, change):
    def setup(env):
        owner = env.object(0x200, 'owner', fill=0xA3)
        state = env.object(0x180, 'state', fill=0xB7)
        child = env.object(0x4E8, 'child', fill=0xC9)
        vtable = env.object(0x24, 'methods', fill=0)
        second = env.object(0x24, 'second-methods', fill=0)
        child_state = env.object(0x180, 'child-state', fill=0)
        env.put(owner + 0x6C, state)
        env.put(state + 0x18, child, state_value)
        env.put(child, vtable)
        env.put(child + 0x8, owner, owner, child_state, values[2])
        env.put(child_state + 0x1C, 4)
        key = cstring(env, 'LS_HOME', 'state-key')
        table = env.object(4, 'state-table', words=[key], fill=0)
        env.put(0x5376A0, 4, 4, table, table, 4, 0, 0)
        alternate = env.object(0x180, 'alternate-state', fill=0x6D)
        def callback(env, call):
            env.put(child + 0x14, values[0])
            if change:
                env.put(state + 0x18, alternate)
                env.put(state + 0x1C, values[1])
                env.put(owner + 0x6C, alternate)
                env.put(child, second)
            return values[2]
        for offset, argc in ((4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
            env.put(vtable + offset, env.stub('first-' + str(offset), 'thiscall', argc, callback))
            env.put(second + offset, env.stub('second-' + str(offset), 'thiscall', argc, callback))
        return {'owner': owner}
    return setup


def cases(random_source):
    for mode in ('miss', 'fallback', 'hit', 'mixed'):
        for change in (False, True):
            values = random_source.sample(range(10, 800), 11)
            yield Case('construct ' + mode + (' allocation changes owner state' if change else ''), ENTRY,
                       constructor(mode, values, change), arguments=(lambda t: t['owner'],))
    for value in (1, 2, 27, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        for change in (False, True):
            values = random_source.sample(range(1001, 80000), 3)
            yield Case(f'command {value:#x} mutate {change}', ENTRY, command(value, values, change),
                       arguments=(lambda t: t['owner'],))
