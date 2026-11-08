"""Original dispatcher cases for RedTailPirate."""
from clawparity.cases import Case
from clawparity.world import world, rectangle_services, animation, sprite, cstring

ENTRY = 0x482820


def lifecycle(command, marker):
    def setup(env):
        t = world(env, state_words={0x1c: command})
        child = env.object(0x4b8, 'lifecycle-child', fill=0)
        table = env.object(0x24, 'child-methods', fill=0)
        alternate = env.object(0x24, 'alternate-methods', fill=0)
        state = env.object(0x180, 'child-state', fill=0)
        env.put(child, table)
        env.put(child + 0x10, state)
        env.put(state + 0x1c, 7)
        env.put(t['state'] + 0x18, child)
        text = cstring(env, 'LS_IDLE', 'lifecycle-state-name')
        entries = env.object(4, 'state-name-table', words=[text], fill=0)
        env.put(0x5376a0, 7, 7, entries, entries, 4, 0, 0)
        def effect(env, call):
            env.put(t['state'] + 0x1c, marker)
            env.put(child + 0x44, marker ^ 0xabcddcba)
            env.put(child, alternate)
            return marker
        for target, prefix in ((table, 'first'), (alternate, 'reload')):
            for off, argc in ((4, 1), (8, 1), (12, 1), (0x1c, 0), (0x20, 0)):
                env.put(target + off, env.stub(f'{prefix}-{off:x}', 'thiscall', argc, effect))
        return t
    return setup


def construct(mode, salt):
    def setup(env):
        resources = {}
        if mode != 'miss':
            anims = {}
            names = ['ADVANCE', 'FASTADVANCE', 'HITHIGH', 'HITLOW', 'IDLE', 'JUMP',
                     'KILLFALL', 'LIFTED1', 'LIFTED2', 'STRIKE1', 'THROWN', 'BLOCK',
                     'HOME', 'QUICKBLOCK'] if mode == 'hit' else []
            for index, name in enumerate(names):
                anims['LEVEL_REDTAILPIRATE_' + name] = animation(env, salt + index + 1, name)
            anims['GAME_NULL'] = animation(env, salt + 71, 'fallback')
            resources['animations'] = anims
            resources['sprites'] = {'LEVEL_REDTAILPIRATE': sprite(env, salt + 20, salt + 30)}
            sounds = {}
            for index, name in enumerate(['00490005', '00490010', '00490011', '00490012',
                '00490013', '00490018', '00490021', '00490022', '00490016', '00490008',
                '00490001', '00490019', '00490014', '00490028', 'BLOCK1', 'BLOCK2']):
                sounds['LEVEL_REDTAILPIRATE_' + name] = env.object(0x20, 'sound-' + name, fill=0)
            resources['sounds'] = sounds
        t = world(env, resources=resources, owner_words={0x108: salt + 40, 0x104: salt + 3},
                  state_words={0x1c: 0, 0x68: salt, 0x168: salt + 17})
        rectangle_services(env)
        env.override(0x4a3050, lambda env, call: salt)
        env.put(0x53774c, 0)
        sentinel = env.object(0x4b8, 'previous-child', fill=0)
        env.put(t['state'] + 0x18, sentinel)
        def allocate_and_mutate(env, call):
            env.put(t['state'] + 0x18, sentinel + 4)
            env.put(t['state'] + 0x20, salt ^ 0xdefaced)
            return env.object(call.arguments[0], 'allocation', fill=0)
        env.override(0x4f63ec, allocate_and_mutate)
        return t
    return setup


def cases(random_source):
    for mode in ('miss', 'hit', 'fallback'):
        yield Case('constructor-' + mode, ENTRY, construct(mode, random_source.randrange(1, 60)),
                   arguments=(lambda t: t['owner'],))
    for command in (1, 2, 28, 29, 30, 31, 999, 1000, 1001, 0x7fffffff, 0xffffffff):
        yield Case(f'command-{command:x}-callback-reloads', ENTRY,
                   lifecycle(command, random_source.randrange(1, 0xffffffff)),
                   arguments=(lambda t: t['owner'],))
