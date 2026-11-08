"""Original-only Siren command dispatch and constructor worlds."""
from clawparity.cases import Case
from clawparity.fixtures import returns
from clawparity.world import world, rectangle_services, animation, sprite, cstring

ENTRY = 0x489730
NEW = 0x4F63EC
KEYS = ('IDLE', 'ADVANCE', 'FASTADVANCE', 'HITHIGH', 'HITLOW', 'JUMP',
        'KILLFALL', 'LIFTED1', 'LIFTED2', 'STRIKE1', 'THROWN')


def setup_case(command, values, mode='empty', mutate=False):
    def setup(env):
        rectangle_services(env)
        env.override(0x4A3050, returns(50))
        resources = {}
        if mode != 'empty':
            seq = animation(env, duration=values[0])
            resources['animations'] = {'GAME_NULL': seq}
        if mode == 'hit':
            resources['animations'].update({
                'LEVEL_SIREN_' + key: animation(env, duration=values[0] + n + 1,
                                              name='siren-' + key)
                for n, key in enumerate(KEYS)})
            resources['sprites'] = {'LEVEL_SIREN': sprite(env, width=47, height=63,
                                                         origin=(13, 19))}
        tokens = world(env, resources=resources, bucket_count=1,
                       owner_words={0x4C: values[1], 0x50: values[2],
                                    0x148: values[3], 0x14C: values[4]},
                       state_words={0x1C: command, 0x2C: -111, 0x30: 222,
                                    0x34: -333, 0x38: 444, 0x68: values[5], 0x168: 77})
        state, owner = tokens['state'], tokens['owner']
        child = env.object(0x4B0, 'existing-child', fill=0)
        vt = env.object(0x24, 'dispatch-methods', fill=0)
        alt = env.object(0x24, 'changed-methods', fill=0)
        env.put(child, vt)
        env.put(child + 0xC, owner, state)
        env.put(child + 0x18, 0xAABBCCDD, 1001, 2, 0x12345678)
        env.put(state + 0x18, child)
        # Original 4dc870 uses the numeric-state CString table. Both bounds
        # contain exactly the incoming command, avoiding arithmetic-wrap spans.
        text = cstring(env, 'LS_TEST', 'numeric-state-name')
        table = env.object(4, 'numeric-state-table', words=[text])
        env.put(0x5376A0, command, command, table, table, 4, 0, 0)
        def effect(offset, changed=False):
            def invoke(env, call):
                env.put(child + 0x24, values[6] + offset)
                if mutate:
                    env.put(child, alt)
                    env.put(state + 0x18, owner)
                    env.put(state + 0x1C, values[7])
                    env.put(owner + 0x6C, child)
                return values[8] + offset + changed
            return invoke
        for offset, argc in ((4, 1), (8, 1), (12, 1), (16, 0), (28, 0), (32, 0)):
            env.put(vt + offset, env.stub('child-%x' % offset, 'thiscall', argc, effect(offset)))
            env.put(alt + offset, env.stub('changed-%x' % offset, 'thiscall', argc, effect(offset, True)))
        if command == 0 and mutate:
            def alloc(env, call):
                if call.arguments[0] == 0x4B0 and env.calls_so_far(NEW) == 1:
                    env.put(state + 0x18, owner)
                    env.put(state + 0x1C, 0x3E8)
                    env.put(state + 0x24, values[6])
                return env.object(call.arguments[0], 'allocation', fill=0)
            env.override(NEW, alloc)
        return tokens
    return setup


def cases(random_source):
    commands = (0, 1, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)
    for command in commands:
        for mutate in (False, True):
            values = random_source.sample(range(1, 10000), 9)
            yield Case('command-%x-mutate-%s' % (command, mutate), ENTRY,
                       setup=setup_case(command, values, mutate=mutate),
                       arguments=(lambda t: t['owner'],))
    for mode in ('fallback', 'hit'):
        for mutate in (False, True):
            values = random_source.sample(range(1, 10000), 9)
            yield Case('constructor-' + mode + '-mutate-' + str(mutate), ENTRY,
                       setup=setup_case(0, values, mode, mutate),
                       arguments=(lambda t: t['owner'],))
