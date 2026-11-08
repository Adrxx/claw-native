"""Original-only inputs for RobberThief dispatch and construction."""
from clawparity.cases import Case
from clawparity.fixtures import returns
from clawparity.world import animation, cstring, rectangle_services, sprite, world

ENTRY = 0x485270


def constructor(mode, values):
    def setup(env):
        rectangle_services(env)
        env.override(0x4A3050, returns(values[0]))
        resources = {}
        if mode != 'miss':
            resources['animations'] = {'GAME_NULL': animation(env, values[1])}
        if mode == 'hit':
            resources['sprites'] = {'LEVEL_ROBBERTHIEF': sprite(env, values[2], values[3], (7, 11))}
            for index, suffix in enumerate(('FASTADVANCE', 'STRIKE1', 'FALL', 'HITLOW', 'HITHIGH', 'HOME', 'IDLE', 'LIFTED', 'LIFTED2', 'JUMP', 'THROWN')):
                resources['animations']['LEVEL_ROBBERTHIEF_' + suffix] = animation(env, values[1] + index + 1, 'robber-sequence-' + suffix)
        return world(env, resources=resources, bucket_count=values[4],
                     owner_words={0x4C: values[5], 0x50: values[6], 0x40: values[7]},
                     state_words={0x2C: -101, 0x30: 103, 0x34: -107, 0x38: 109, 0x64: values[8], 0x68: 127, 0x168: 131}, idle_state=5)
    return setup


def dispatch(command, marker, change):
    def setup(env):
        owner = env.object(0x200, 'dispatch-owner', fill=0x29)
        state = env.object(0x180, 'dispatch-state', fill=0x37)
        child = env.object(0x80, 'lifecycle-child', fill=0x43)
        methods = env.object(0x24, 'lifecycle-vtable', fill=0)
        alternate = env.object(0x24, 'alternate-lifecycle-vtable', fill=0)
        env.put(owner + 0x6C, state)
        env.put(state + 0x18, child, command)
        env.put(child, methods)
        env.put(child + 0x10, state)
        # The original lifecycle reads the state ID through child + 0x10.
        # Use a bounded one-element CString table for that exact ID.
        text = cstring(env, 'robber lifecycle', 'lifecycle-state-name')
        table = env.object(4, 'state-cstring-table', words=[text])
        env.put(0x5376A0, command, command, table, table, 4, 0, 0)
        def effect(offset):
            def callback(env, call):
                env.put(child + 0x40 + offset, marker ^ offset)
                if change:
                    env.put(state + 0x18, owner)
                    env.put(state + 0x1C, 1000)
                    env.put(child, alternate)
                return marker
            return callback
        for slot, argc in ((4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
            env.put(methods + slot, env.stub('child-method-' + str(slot), 'thiscall', argc, effect(slot)))
            env.put(alternate + slot, env.stub('changed-child-method-' + str(slot), 'thiscall', argc, effect(slot + 1)))
        return {'owner': owner}
    return setup


def cases(random_source):
    for command in (1, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        for change in (False, True):
            yield Case('dispatch %08x change %s' % (command, change), ENTRY,
                       dispatch(command, random_source.randrange(1, 0xFFFFFFFF), change),
                       arguments=(lambda tokens: tokens['owner'],))
    for mode in ('miss', 'fallback', 'hit'):
        for index in range(3):
            values = (random_source.randrange(0, 32768), random_source.randrange(1, 1000),
                      random_source.randrange(12, 90), random_source.randrange(13, 100),
                      (1, 17, 31)[index], random_source.randrange(-300, 301),
                      random_source.randrange(-300, 301), (0, 2, 0)[index], index)
            yield Case('construct %s %s' % (mode, index), ENTRY, constructor(mode, values),
                       arguments=(lambda tokens: tokens['owner'],))
