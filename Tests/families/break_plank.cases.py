"""Original-code cases for BreakPlank's command dispatcher."""
from clawparity.cases import Case
from clawparity.world import world, cstring, resource_manager

ENTRY = 0x40F7B0
NEW = 0x4F63EC


def command_setup(command, salt, change=False):
    def setup(env):
        tokens = world(env, state_words={0x1C: command})
        state = tokens['state']
        obj = env.object(0xA4, 'existing-plank', fill=0)
        methods = env.object(0x24, 'plank-methods', fill=0)
        env.put(obj, methods)
        env.put(obj + 0x10, state)
        env.put(obj + 0x14, salt, salt + 1, salt + 2, salt + 3)
        env.put(state + 0x18, obj)
        label = cstring(env, b'LS_TEST_' + str(salt).encode(), 'dispatch-state-name')
        table = env.object(4, 'state-name-table', words=[label])
        env.put(0x5376A0, command, command, table, 0, 4, 0, 0)
        def effect(slot):
            def call(env, invocation):
                env.put(obj + 0x40 + slot, salt + slot)
                if change:
                    env.put(state + 0x1C, 30)
                    env.put(obj + 0x10, state)
                return salt ^ (slot + 1)
            return call
        for offset, argc in ((4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
            env.put(methods + offset, env.stub('plank-slot-' + str(offset), 'thiscall', argc, effect(offset)))
        return tokens
    return setup


def construct_setup(salt, count=1, hits=False, replace_state=False, dynamic_initializer=False):
    def setup(env):
        tokens = world(env, owner_words={0x4C: 3, 0x50: 5, 0x64: 7},
                       state_words={0x1C: 0, 0xB8: salt, 0xC8: count})
        env.put(tokens['state'] + 0xC, tokens['world'])
        descriptor = env.object(0x20, 'SinglePlank-logic-descriptor', fill=0)
        env.put(descriptor + 0x10, 0x488E30)
        entries = {b'SinglePlank': descriptor}
        if hits:
            entries[b'LogicHit'] = descriptor
            entries[b'LogicAttack'] = descriptor
        manager = resource_manager(env, entries)
        env.put(tokens['world'] + 0x14, manager)
        scene = env.object(0x100, 'scene-object-list', fill=0)
        env.put(scene + 0xC, tokens['world'])
        env.put(scene + 0x28, 4)
        env.put(tokens['world'] + 8, scene)
        context = env.object(0x200, 'game-context', fill=0)
        env.put(context + 0xA8, 32, 0)
        env.put(0x537960, context)
        player = env.object(0x100, 'player', fill=0)
        player_state = env.object(0x40, 'player-state', fill=0)
        player_runtime = env.object(0x100, 'player-runtime', fill=0)
        env.put(player + 0x6C, player_state)
        env.put(player_state + 0x14, player_runtime)
        env.put(player_runtime + 0x80, salt + 11)
        env.put(0x537E88, player)
        plane = env.object(0x100, 'collision-plane', fill=0)
        row = env.object(32, 'collision-row', fill=0)
        rows = env.object(32, 'collision-rows', fill=0)
        env.put(plane + 0x20, row, rows)
        env.put(plane + 0x8C, 4, 4)
        env.put(tokens['collision'] + 0x5C, plane)
        tracker = env.object(4, 'allocator-parent-tracker', fill=0)
        observations = env.object(16, 'initializer-observations', words=[salt + 31, salt + 32, salt + 33, salt + 34])
        replacement_vtable = env.object(0x24, 'callback-supplied-parent-vtable',
            words=[0x484D90, 0x4C9E30, 0x40FB30, 0x4041B0, 0,
                   0x4BB030, 0x4BB030, 0x4C96B0, 0x4C96B0])
        def initialize(env, call):
            state = env.get(call.receiver + 0x10)
            env.put(observations, salt + 35, env.get(state + 0x18),
                    call.receiver, env.get(call.receiver + 0xA0))
            return salt + 36
        env.put(replacement_vtable + 0x10, env.stub('parent-observable-initialize', 'thiscall', 0, initialize))
        def allocate(env, call):
            if dynamic_initializer and call.arguments[0] == 0x6C:
                allocated_parent = env.get(tracker)
                preceding_child = env.get(allocated_parent + 0xA0)
                if preceding_child:
                    published_parent = env.get(preceding_child + 4)
                    if published_parent != allocated_parent:
                        raise ValueError('original child back-link must identify its parent')
                    env.put(published_parent, replacement_vtable)
            if replace_state and env.calls_so_far(NEW) == 1:
                replacement = env.object(0x180, 'replacement-state', data=env.read(tokens['state'], 0x180))
                env.put(replacement + 0xB8, salt + 19)
                env.put(tokens['owner'] + 0x6C, replacement)
            allocation = env.object(call.arguments[0], 'initialized-allocation', fill=0)
            if env.calls_so_far(NEW) == 1:
                env.put(tracker, allocation)
            return allocation
        env.override(NEW, allocate)
        return tokens
    return setup


def cases(random_source):
    for command in (1, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        salt = random_source.randrange(100, 0xFFFF)
        yield Case('command-' + str(command), ENTRY, command_setup(command, salt),
                   arguments=(lambda t: t['owner'],))
    for command in (1, 29, 30):
        yield Case('callback-changes-state-' + str(command), ENTRY,
                   command_setup(command, random_source.randrange(0x10000, 0x20000), True),
                   arguments=(lambda t: t['owner'],))
    for count in (-1, 0, 1, 2, 3):
        for hits in (False, True):
            yield Case('construct-original-count-' + str(count) + '-hits-' + str(hits), ENTRY,
                       construct_setup(random_source.randrange(0x20000, 0x30000), count, hits),
                       arguments=(lambda t: t['owner'],))
    yield Case('allocation-replaces-owner-state', ENTRY,
               construct_setup(random_source.randrange(0x30000, 0x40000), 2, True, True),
               arguments=(lambda t: t['owner'],))
    for count in (2, 3):
        yield Case('published-child-replaces-parent-initializer-' + str(count), ENTRY,
                   construct_setup(random_source.randrange(0x50000, 0x60000), count,
                                   dynamic_initializer=True),
                   arguments=(lambda t: t['owner'],))
    for _ in range(5):
        command = random_source.randrange(2, 28)
        yield Case('random-command-' + str(command), ENTRY,
                   command_setup(command, random_source.randrange(0x40000, 0x50000)),
                   arguments=(lambda t: t['owner'],))
