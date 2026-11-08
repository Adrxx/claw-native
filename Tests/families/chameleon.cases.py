"""Original-only Chameleon command dispatch inputs."""
from clawparity.cases import Case
from clawparity.fixtures import returns
from clawparity.world import world, rectangle_services, cstring, sprite, animation

ENTRY = 0x421200


def lifecycle(command, salt, changing):
    def setup(env):
        owner = env.object(0x200, 'dispatch-owner', fill=0x63)
        state = env.object(0x180, 'dispatch-state', fill=0x47)
        child = env.object(0x488, 'lifecycle-child', fill=0xA9)
        methods = env.object(0x24, 'lifecycle-methods', fill=0)
        env.put(owner + 0x6C, state)
        env.put(state + 0x18, child, command)
        env.put(child, methods)
        env.put(child + 0x10, state)
        table = env.object(4, 'state-string-table', fill=0)
        env.put(table, cstring(env, 'command-' + str(salt)))
        env.put(0x5376A0, command, command, table, table, 4, 0, 0)
        replacement = env.object(0x24, 'replacement-methods', fill=0)
        def effect(offset):
            def called(env, call):
                env.put(child + 0x44 + offset, salt ^ offset)
                if changing:
                    env.put(state + 0x18, owner)
                    env.put(state + 0x1C, salt)
                    env.put(child, replacement)
                return salt ^ (offset * 13)
            return called
        for offset, argc in ((4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
            env.put(methods + offset, env.stub('child-method-' + str(offset), 'thiscall', argc, effect(offset)))
            env.put(replacement + offset, env.stub('replacement-method-' + str(offset), 'thiscall', argc, effect(offset)))
        return {'owner': owner}
    return setup


def construct(mode, values):
    def setup(env):
        rectangle_services(env)
        env.override(0x4A3050, returns(values[0]))
        resources = {}
        if mode != 'miss':
            fallback = animation(env, duration=values[1])
            resources['animations'] = {'GAME_NULL': fallback}
        if mode == 'hit':
            resources['sprites'] = {'LEVEL_CHAMELEON': sprite(env, width=values[2], height=values[3], origin=(7, 11))}
            for suffix in ('IDLE', 'FASTADVANCE', 'HIT', 'JUMP', 'KILLFALL', 'STRIKE1'):
                resources['animations']['LEVEL_CHAMELEON_' + suffix] = animation(env, duration=values[1] + len(suffix), name=suffix)
        global_context = env.object(0x30, 'global-context', fill=0)
        env.put(0x5371FC, global_context)
        tokens = world(env, resources=resources, bucket_count=1,
                     owner_words={0x4C: values[4], 0x50: values[5], 0x40: 0, 0x148: 2, 0x14C: 3},
                     state_words={0x64: values[6], 0x68: values[7], 0x168: 33, 0x2C: -71, 0x30: 97, 0x34: -113, 0x38: 151},
                     idle_state=5)
        def allocate_and_change(env, call):
            env.put(tokens['state'] + 0x18, values[7])
            env.put(tokens['state'] + 0x1C, 1000 + values[1])
            return env.object(call.arguments[0], 'constructor-allocation', fill=0x7D)
        env.override(0x4F63EC, allocate_and_change)
        return tokens
    return setup


def cases(random_source):
    commands = (1, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)
    for command in commands:
        for changing in (False, True):
            salt = random_source.randrange(1, 0x10000000)
            yield Case(f'command {command:#x} mutation {changing}', ENTRY, lifecycle(command, salt, changing), arguments=(lambda t: t['owner'],))
    for mode in ('miss', 'fallback', 'hit'):
        for i in range(3):
            values = (random_source.randrange(3, 100), random_source.randrange(1, 800), random_source.randrange(1, 96), random_source.randrange(1, 96), random_source.randrange(-200, 200), random_source.randrange(-200, 200), i - 1, random_source.randrange(1, 2000))
            yield Case(f'construction {mode} {i}', ENTRY, construct(mode, values), arguments=(lambda t: t['owner'],))
