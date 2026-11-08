"""Original-only command, lifecycle and constructor inputs."""
from clawparity.cases import Case
from clawparity.fixtures import returns
from clawparity.world import cstring, rectangle_services, sprite, world

ENTRY = 0x4379D0
NEW = 0x4F63EC


def sequence(env, duration, name):
    # Original animation selection/timing uses descriptor +0xc/+0x10;
    # playback reads frame fields through +0x2c (004c82a0).
    descriptor = env.object(0x14, name, fill=0)
    frames = env.object(4, name + '-frames', fill=0)
    frame = env.object(0x30, name + '-frame', fill=0)
    env.put(descriptor + 0xC, frames, 1)
    env.put(frames, frame)
    env.put(frame + 0x18, duration, duration + 7)
    return descriptor


def construct(mode, values, change_owner):
    def setup(env):
        rectangle_services(env)
        env.override(0x4A3050, returns(values[0]))
        resources = {}
        if mode != 'miss':
            fallback = sequence(env, values[1], 'fallback')
            resources['animations'] = {'GAME_NULL': fallback}
        if mode == 'hit':
            direct = sequence(env, values[2], 'direct')
            resources['animations'].update({'LEVEL_CUTTHROAT_WALK': direct,
                                           'LEVEL_CUTTHROAT_STAND2': direct,
                                           'LEVEL_CUTTHROAT_STRIKE1': direct})
            resources['sprites'] = {'LEVEL_CUTTHROAT': sprite(env, width=values[3], height=values[4],
                                                             origin=(values[5], values[6]))}
        tokens = world(env, resources=resources, bucket_count=1,
                       collision_step=(values[3], values[4]), idle_state=5,
                       owner_words={0x4C: values[5], 0x50: values[6], 0x40: values[7],
                                    0x148: values[8], 0x14C: values[9]},
                       state_words={0x2C: -107, 0x30: 113, 0x34: -211, 0x38: 223,
                                    0x64: values[10], 0x68: values[11], 0x168: values[12]})
        env.put(tokens['owner'] + 0x18C, tokens['owner'])
        env.put(0x537964, values[13])
        if change_owner:
            alternate = env.object(0x180, 'alternate-state', fill=0)
            env.put(alternate + 0x1C, 1000)
            env.put(alternate + 0x68, values[11] + 13)
            env.put(alternate + 0x168, values[12] + 17)
            def allocate(env, call):
                env.put(tokens['owner'] + 0x6C, alternate)
                env.put(tokens['state'] + 0x18, alternate)
                return env.object(call.arguments[0], 'constructed-child', fill=0xA5)
            env.override(NEW, allocate)
        return tokens
    return setup


def command(value, salt, mutate):
    def setup(env):
        owner = env.object(0x80, 'command-owner', fill=0xA5)
        state = env.object(0x40, 'command-state', fill=0xB6)
        child = env.object(0x480, 'lifecycle-child', fill=0)
        internal = env.object(0x40, 'child-state', fill=0)
        methods = env.object(0x24, 'lifecycle-methods', fill=0)
        alternate_methods = env.object(0x24, 'alternate-methods', fill=0)
        env.put(owner + 0x6C, state)
        env.put(state + 0x18, child, value)
        env.put(child, methods)
        env.put(child + 0x10, internal)
        env.put(internal + 0x1C, salt % 17)
        text = cstring(env, 'LS_IDLE', 'lifecycle-state-name')
        table = env.object(17 * 4, 'state-name-table', words=[text] * 17, fill=0)
        env.put(0x5376A0, 0, 16, table)
        env.put(0x5376B0, 4)
        def effect(index):
            def callback(env, call):
                env.put(state + 0x1C, salt + index)
                env.put(child + 0x24, salt ^ index)
                if mutate:
                    env.put(child, alternate_methods)
                    env.put(state + 0x18, internal)
                    env.put(internal + 0x1C, (salt + index) % 17)
                return salt ^ (index * 0x101)
            return callback
        for target, prefix in ((methods, 'first'), (alternate_methods, 'reloaded')):
            for offset, argc in ((4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
                env.put(target + offset, env.stub(prefix + str(offset), 'thiscall', argc, effect(offset)))
        return {'owner': owner}
    return setup


def cases(random_source):
    for value in (1, 2, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        for mutate in (False, True):
            yield Case(f'command {value:#x} mutate {mutate}', ENTRY,
                       command(value, random_source.randrange(1, 0x10000), mutate),
                       arguments=(lambda t: t['owner'],))
    for mode in ('miss', 'fallback', 'hit'):
        for change in (False, True):
            values = [random_source.choice((0, 32, 33, 99, 100)),
                      random_source.randrange(1, 500), random_source.randrange(1, 500),
                      random_source.randrange(8, 128), random_source.randrange(8, 128),
                      random_source.randrange(-200, 200), random_source.randrange(-200, 200),
                      random_source.choice((0, 2)), random_source.randrange(-3, 4),
                      random_source.randrange(-3, 4), random_source.choice((0, 1, 2)),
                      random_source.randrange(100, 10000), random_source.randrange(1, 100),
                      random_source.choice((2, 3, 4))]
            yield Case(f'construct {mode} change-owner {change}', ENTRY,
                       construct(mode, values, change), arguments=(lambda t: t['owner'],))
