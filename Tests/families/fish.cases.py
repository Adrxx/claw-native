"""Blind fish callback cases using original game callees."""
from clawparity.cases import Case
from clawparity.world import world, cstring, animation, sprite, set_rect_empty

ENTRY = 0x441BE0


def dispatch_setup(command, value, change=False):
    def setup(env):
        tokens = world(env, state_words={0x1C: command})
        state, owner = tokens['state'], tokens['owner']
        actor = env.object(0x430, 'fish-existing', fill=0)
        alternate = env.object(0x430, 'alternate-fish', fill=0)
        alternate_state = env.object(0x180, 'alternate-state', fill=0)
        methods = env.object(0x24, 'fish-methods', fill=0)
        env.put(actor, methods)
        env.put(actor + 0x10, state)
        env.put(actor + 0x24, value)
        env.put(state + 0x18, actor)
        # Valid singleton numeric-state table, with a real CString record.
        table = env.object(4, 'numeric-state-table', fill=0)
        env.put(table, cstring(env, 'FISH_TEST_STATE'))
        env.put(0x5376A0, command, command, table, table, 4, 0, 0)
        def effect(slot):
            def run(e, call):
                e.put(actor + 0x24 + slot, value ^ (0x10203 * (slot + 1)))
                if change:
                    e.put(owner + 0x6C, alternate_state)
                    e.put(state + 0x18, alternate)
                    e.put(state + 0x1C, 1000)
                return value
            return run
        for slot, argc in ((4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
            env.put(methods + slot, env.stub('fish-method-%x' % slot, 'thiscall', argc, effect(slot)))
        return tokens
    return setup


def construction_setup(value, resource_mode, mutate=False):
    def setup(env):
        env.override(0x546CDC, set_rect_empty)
        resources = {}
        if resource_mode:
            swim = animation(env, 71, 'swim-animation')
            null = animation(env, 113, 'fallback-animation')
            resources['animations'] = {'GAME_NULL': null}
            if resource_mode == 'hit':
                for name in ('SWIM', 'STRIKE1', 'KILLFALL', 'HIT', 'FLOUNDER'):
                    resources['animations']['LEVEL_FISH_' + name] = swim
                resources['sprites'] = {'LEVEL_FISH': sprite(env, 37, 29, (3, -5))}
        tokens = world(env, resources=resources,
                       owner_words={0x4C: value, 0x50: value + 11, 0x104: 0, 0x148: 1, 0x14C: 1},
                       state_words={0x1C: 0, 0x2C: 7, 0x30: 13, 0x34: 17, 0x38: 19, 0x168: value})
        if mutate:
            def allocate_with_effect(e, call):
                e.put(tokens['state'] + 0x1C, 31)
                e.put(tokens['owner'] + 0x4C, value + 23)
                e.put(tokens['owner'] + 0x50, value + 41)
                return e.object(call.arguments[0], 'fish-allocation-pattern', fill=0xA5)
            env.override(0x4F63EC, allocate_with_effect)
        return tokens
    return setup


def cases(random_source):
    for command in (1, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0xFFFFFFFE, 0xFFFFFFFF):
        for change in (False, True):
            value = random_source.randrange(1, 0x7FFFFFFF)
            yield Case('command %x effect %s' % (command, change), ENTRY,
                       dispatch_setup(command, value, change), arguments=(lambda t: t['owner'],))
    for resource_mode in (None, 'fallback', 'hit'):
        yield Case('original constructor resources %s' % resource_mode, ENTRY,
                   construction_setup(random_source.randrange(1, 300), resource_mode),
                   arguments=(lambda t: t['owner'],))

    yield Case('constructor allocation changes lifecycle and position', ENTRY,
               construction_setup(random_source.randrange(1, 300), 'hit', True),
               arguments=(lambda t: t['owner'],))
