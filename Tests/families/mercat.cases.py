"""Original-only Mercat command and construction inputs."""
from clawparity.cases import Case
from clawparity.world import world, rectangle_services, sprite, cstring

ENTRY = 0x45FF00


def animation(env, duration, name):
    sequence = env.object(0x14, name, fill=0)
    frames = env.object(4, name + '-frames', fill=0)
    frame = env.object(0x30, name + '-frame', fill=0)
    env.put(sequence + 0xC, frames, 1)
    env.put(frames, frame)
    env.put(frame + 0x1C, duration)
    return sequence


def construction(mode, roll, marker, mutate=False):
    def setup(env):
        resources = {}
        if mode != 'miss':
            names = ('ADVANCE', 'FASTADVANCE', 'HITHIGH', 'HITLOW', 'IDLE1',
                     'IDLE2', 'IDLE3', 'IDLE4', 'JUMP', 'KILLFALL', 'LIFTED1',
                     'LIFTED2', 'STRIKE1', 'THROWN', 'HOME', 'BLOCK')
            animations = {'GAME_NULL': animation(env, 137, 'fallback-animation')}
            if mode == 'hit':
                animations.update({'LEVEL_MERCAT_' + name: animation(env, 73 + i, name)
                                   for i, name in enumerate(names)})
            resources = {'animations': animations,
                         'sprites': {'LEVEL_MERCAT': sprite(env, 43, 57, (-7, 9))}}
        t = world(env, resources=resources, state_words={0x1C: 0},
                  owner_words={0x190: marker, 0x68: 37})
        env.put(t['owner'] + 0x18C, t['owner'])
        rectangle_services(env)
        env.override(0x4A3050, lambda e, c: roll)
        if mutate:
            def allocate_and_change_state(e, call):
                e.put(t['state'] + 0x18, marker, marker + 1)
                e.put(t['state'] + 0x20, marker + 2)
                return e.object(call.arguments[0], 'mutating-allocation', fill=0x73)
            env.override(0x4F63EC, allocate_and_change_state)
        return t
    return setup


def command(value, marker, mutate):
    def setup(env):
        owner = env.object(0x200, 'command-owner', fill=0x53)
        state = env.object(0x180, 'command-state', fill=0x67)
        child = env.object(0x40, 'lifecycle-child', fill=0x29)
        alternate = env.object(0x40, 'alternate-child', fill=0x39)
        methods = env.object(0x24, 'lifecycle-methods', fill=0)
        other_methods = env.object(0x24, 'alternate-methods', fill=0)
        env.put(owner + 0x6C, state)
        env.put(state + 0x18, child, value)
        env.put(child, methods)
        env.put(child + 0x10, state)
        env.put(alternate, other_methods)
        env.put(alternate + 0x10, state)
        env.put(state + 0x1C, value)
        # Original dispatch indexes its numeric-state string table twice.
        text = cstring(env, 'MERCAT_CASE_STATE')
        table = env.object(4, 'state-name-table', words=[text])
        env.put(0x5376A0, value, value, table, table, 4, 0, 0)
        def callback(offset):
            def effect(e, call):
                e.put(call.receiver + 0x30, marker ^ offset)
                if mutate:
                    e.put(owner + 0x6C, alternate)
                    e.put(state + 0x18, alternate)
                    e.put(state + 0x1C, marker)
                    e.put(child, other_methods)
                return marker + offset
            return effect
        for offset, argc in ((4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
            env.put(methods + offset, env.stub('child-method-' + str(offset), 'thiscall', argc, callback(offset)))
            env.put(other_methods + offset, env.stub('alternate-method-' + str(offset), 'thiscall', argc, callback(offset + 0x40)))
        return {'owner': owner}
    return setup


def cases(random_source):
    for mode in ('miss', 'fallback', 'hit'):
        for roll in (0, 49, 50, 99):
            yield Case(f'construct {mode} rand {roll}', ENTRY,
                       construction(mode, roll, random_source.randrange(1, 1000)),
                       arguments=(lambda t: t['owner'],))
    for mode in ('miss', 'hit'):
        yield Case(f'construct {mode} allocation changes state', ENTRY,
                   construction(mode, random_source.randrange(0, 100),
                                random_source.randrange(1001, 100000), True),
                   arguments=(lambda t: t['owner'],))
    for value in (1, 2, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0xFFFFFFFF):
        for mutate in (False, True):
            yield Case(f'command {value:#x} mutate {mutate}', ENTRY,
                       command(value, random_source.randrange(1001, 100000), mutate),
                       arguments=(lambda t: t['owner'],))
