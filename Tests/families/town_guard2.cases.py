"""Original-only TownGuard2 dispatch inputs."""
from clawparity.cases import Case
from clawparity.fixtures import returns
from clawparity.world import world, rectangle_services, animation, sprite, cstring

ENTRY = 0x4968D0


def constructor(mode, draw, x, y, mutation=False):
    def setup(env):
        rectangle_services(env)
        env.override(0x4A3050, returns(draw))
        resources = {}
        if mode != 'miss':
            names = ('ADVANCE', 'FASTADVANCE', 'STRIKE1', 'KILLFALL', 'IDLE1', 'IDLE2',
                     'HITLOW', 'HITHIGH', 'JUMP', 'HOME', 'LIFTED1', 'LIFTED2', 'THROWN')
            keys = ['GAME_NULL'] if mode == 'fallback' else ['LEVEL_TOWNGUARD2_' + n for n in names] + ['LEVEL_TOWNGUARD1_STRIKE1', 'GAME_NULL']
            resources['animations'] = {key: animation(env, 70 + i * 7, key) for i, key in enumerate(keys)}
            resources['sprites'] = {'LEVEL_TOWNGUARD2': sprite(env, 35, 57, (-3, 8))}
        tokens = world(env, resources=resources, owner_words={0x14:x, 0x18:y},
                       state_words={0x18:0x12345678, 0x1C:0})
        if mutation:
            alternate_state = env.object(0x180, 'replacement-owner-state', fill=0)
            env.put(alternate_state + 0x18, 0xCAFEBABE, 1000)
            def allocate_and_change(env, call):
                result = env.object(call.arguments[0], 'constructor-allocation', fill=0)
                if env.calls_so_far(0x4F63EC) == 1:
                    env.put(tokens['state'] + 0x18, 0xBADF00D, 29)
                    env.put(tokens['owner'] + 0x6C, alternate_state)
                return result
            env.override(0x4F63EC, allocate_and_change)
        return tokens
    return setup


def dispatch(command, mutation, key):
    def setup(env):
        tokens = world(env, state_words={0x1C:command})
        state = tokens['state']
        child = env.object(0x80, 'lifecycle-child', fill=0)
        alternate = env.object(0x80, 'alternate-child', fill=0)
        child_state = env.object(0x40, 'child-state', fill=0)
        table = env.object(0x24, 'callbacks', fill=0)
        env.put(child, table)
        env.put(alternate, table)
        env.put(child + 0x10, child_state)
        env.put(alternate + 0x10, child_state)
        env.put(child_state + 0x1C, key)
        env.put(state + 0x18, child)
        text = cstring(env, 'guard-lifecycle-' + str(key))
        rows = env.object(4, 'state-string-table', words=[text], fill=0)
        env.put(0x5376A0, key, key, rows, rows, 4, 0, 0)
        def effect(env, call):
            if mutation:
                env.put(state + 0x1C, 0x87654321)
                env.put(state + 0x18, alternate)
                env.put(child + 0x34, 0xABCDEF01)
                env.put(alternate + 0x38, 0x23456789)
            return 0x7EADF00D
        for offset, argc in ((4,1),(8,1),(12,1),(0x1C,0),(0x20,0)):
            env.put(table + offset, env.stub('lifecycle-' + str(offset), 'thiscall', argc, effect))
        return tokens
    return setup


def cases(random_source):
    for mode in ('miss','fallback','hit'):
        for draw in (0,49,50,99):
            yield Case(f'construct {mode} rand {draw}', ENTRY,
                       constructor(mode,draw,random_source.randrange(-200,200),random_source.randrange(-200,200)),
                       arguments=(lambda t:t['owner'],))
    for mode in ('miss','fallback','hit'):
        yield Case(f'construct {mode} allocation changes state pointer', ENTRY,
                   constructor(mode, random_source.randrange(100), 17, -43, True),
                   arguments=(lambda t:t['owner'],))
    for command in (1,28,29,30,31,999,1000,1001,0x7FFFFFFF,0x80000000,0xFFFFFFFF):
        for mutation in (False,True):
            yield Case(f'command {command:#x} mutate {mutation}', ENTRY,
                       dispatch(command,mutation,random_source.randrange(-100,100)),
                       arguments=(lambda t:t['owner'],))
