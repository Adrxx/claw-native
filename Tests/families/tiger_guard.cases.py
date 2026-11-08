"""Original-only inputs for TigerGuard's lifecycle dispatcher."""
from clawparity.cases import Case
from clawparity.world import animation, cstring, rectangle_services, sprite, world

ENTRY = 0x493EB0
NEW = 0x4F63EC
ANIMATIONS = ('HOME', 'FASTADVANCE', 'HITHIGH', 'HITLOW', 'IDLE', 'JUMP',
              'KILLFALL', 'LIFTED1', 'LIFTED2', 'STRIKE1', 'STRIKE3', 'THROWN',
              'FRONTFLIP', 'BACKFLIP', 'BLOCK')


def constructor_setup(mode, white, values, mutate):
    def setup(env):
        rectangle_services(env)
        resources = {}
        if mode != 'empty':
            resources['animations'] = {'GAME_NULL': animation(env, duration=values[0])}
        if mode == 'hit':
            for index, key in enumerate(ANIMATIONS):
                resources['animations']['LEVEL_TIGER_' + key] = animation(
                    env, duration=values[0] + index, name='tiger-' + key)
            resources['sprites'] = {
                'LEVEL_TIGER': sprite(env, width=values[1], height=values[2]),
                'LEVEL_TIGERWHITE': sprite(env, width=values[2], height=values[1])}
        tokens = world(env, resources=resources, bucket_count=1,
                       owner_words={0x4C: values[3], 0x50: values[4], 0x108: white,
                                    0x148: values[5], 0x14C: values[6]},
                       state_words={0x18: 0x12345678, 0x1C: 0, 0x2C: -100,
                                    0x30: 100, 0x34: -200, 0x38: 200,
                                    0x64: values[7], 0x68: values[8], 0x168: values[9]},
                       idle_state=5, collision_step=(values[1], values[2]))
        if mutate:
            alternate = env.object(0x180, 'replacement-constructor-state',
                                   data=env.read(tokens['state'], 0x180))
            def allocator(env, call):
                count = env.calls_so_far(NEW)
                if count == 1:
                    # Dispatcher has already stored 1000, and publishes only after init.
                    env.put(tokens['state'] + 0x18, 0x87654321)
                    env.put(tokens['owner'] + 0x6C, alternate)
                    env.put(tokens['owner'] + 0x4C, values[3] + 19)
                return env.object(call.arguments[0], 'allocation', fill=0xA7)
            env.override(NEW, allocator)
        return tokens
    return setup


def lifecycle_setup(command, values, change):
    def setup(env):
        owner = env.object(0x200, 'owner', fill=0x71)
        state = env.object(0x180, 'state', fill=0x53)
        alternate = env.object(0x180, 'alternate-state', fill=0x37)
        actor = env.object(0x4E0, 'actor', fill=0xA3)
        actor_state = env.object(0x180, 'actor-state', fill=0x25)
        methods = env.object(0x24, 'actor-methods', fill=0)
        replacement = env.object(0x24, 'replacement-methods', fill=0)
        env.put(owner + 0x6C, state)
        env.put(state + 0x18, actor, command)
        env.put(actor, methods)
        env.put(actor + 0x10, actor_state)
        env.put(actor_state + 0x1C, values[0])
        # Original lifecycle string lookup: valid inclusive singleton table.
        text = cstring(env, 'LS_TIGER_' + str(values[0]), 'lifecycle-text')
        table = env.object(4, 'lifecycle-table', words=[text], fill=0)
        env.put(0x5376A0, values[0], values[0], table, table, 4, 0, 0)
        def effect(env, call):
            env.put(actor + 0x480, values[1], values[2])
            if change:
                env.put(owner + 0x6C, alternate)
                env.put(state + 0x18, values[3])
                env.put(actor, replacement)
            return values[4]
        for offset, argc in ((4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
            env.put(methods + offset, env.stub('tiger-callback-' + str(offset), 'thiscall', argc, effect))
            env.put(replacement + offset, env.stub('replacement-' + str(offset), 'thiscall', argc, effect))
        return {'owner': owner}
    return setup


def cases(random_source):
    for mode in ('empty', 'fallback', 'hit'):
        for white in (0, 1, 2):
            for mutate in (False, True):
                values = [random_source.randrange(1, 1000), random_source.randrange(1, 128),
                          random_source.randrange(1, 128), random_source.randrange(-300, 300),
                          random_source.randrange(-300, 300), random_source.randrange(-3, 4),
                          random_source.randrange(-3, 4), random_source.choice((0, 1, 2)),
                          random_source.randrange(1, 100000), random_source.randrange(1, 1000)]
                yield Case(f'construct {mode} white={white} allocator-effect={mutate}', ENTRY,
                           constructor_setup(mode, white, values, mutate),
                           arguments=(lambda t: t['owner'],))
    commands = (1, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)
    for command in commands:
        for change in (False, True):
            values = [random_source.randrange(1, 1000)] + [random_source.randrange(1, 0xFFFFFFFF) for _ in range(4)]
            yield Case(f'command={command:#x} callback-effect={change}', ENTRY,
                       lifecycle_setup(command, values, change), arguments=(lambda t: t['owner'],))
