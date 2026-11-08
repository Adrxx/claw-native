"""Blind original-program cases for the LavaMouth command dispatcher."""
from clawparity.cases import Case
from clawparity.world import world, cstring, animation, sprite

ENTRY = 0x457620
NEW = 0x4F63EC


def lifecycle(env, owner, state, command, marker, change=False):
    record = env.object(0xB8, 'existing-lava', fill=0)
    for offset in (4, 0x14, 0x1C, 0x20, 0x24, 0x9C, 0xA0, 0xA4, 0xA8):
        env.put(record + offset, marker ^ offset)
    table = env.object(0x24, 'lava-methods', fill=0)
    env.put(record, table)
    env.put(record + 8, owner, owner, state)
    text = cstring(env, 'dispatch-state-' + str(command))
    row = env.object(4, 'state-row', words=[text])
    env.put(0x5376A0, command, command, row, row, 4, 0, 0)
    for offset, argc in ((4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
        def effect(e, call, off=offset):
            e.put(record + 0xA8, marker ^ off)
            e.put(state + 0x18, record)
            if change:
                e.put(state + 0x1C, 1000)
                e.put(owner + 0x6C, e.object(0x180, 'replacement-state', fill=0x35))
            return marker
        env.put(table + offset, env.stub('lava-vmethod-' + str(offset), 'thiscall', argc, effect))
    env.put(state + 0x18, record)
    return record


def setup_case(command, marker, resource_mode=0, change=False):
    def setup(env):
        resources = {}
        if resource_mode:
            image = sprite(env, 47, 29, (3, -7))
            if resource_mode == 1:
                frames = env.object(8, 'two-image-frames', fill=0)
                env.put(frames, env.get(env.get(image + 0x14)),
                        env.object(0x28, 'second-image-frame', fill=0))
                env.put(image + 0x14, frames)
                env.put(image + 0x64, 0, 1)
            resources['sprites'] = {'LEVEL_LAVAMOUTH': image}
            resources['animations'] = {
                ('GAME_CYCLE50' if resource_mode == 1 else 'GAME_NULL'): animation(env, 173)}
            resources['sounds'] = {'LEVEL_LAVAMOUTH1': marker, 'LEVEL_LAVAMOUTH2': marker ^ 0x1234}
        tokens = world(env, owner_words={0x104: marker, 0x100: marker ^ 33},
                       state_words={0x1C: command, 0xBC: marker, 0x64: marker ^ 21},
                       resources=resources, idle_state=None)
        owner, state = tokens['owner'], tokens['state']
        node = env.object(20, 'ES_IDLE-node', fill=0)
        env.put(node, node, node, 0, cstring(env, 'ES_IDLE'), 1)
        env.put(0x537668 + 0x18, node)
        player = env.object(0x80, 'player-owner', fill=0)
        player_state = env.object(0x20, 'player-state', fill=0)
        data = env.object(0x84, 'player-data', fill=0)
        env.put(player + 0x6C, player_state)
        env.put(player_state + 0x14, data)
        env.put(data + 0x80, marker ^ 0x156)
        env.put(0x537E88, player)
        env.put(0x537210, marker ^ 0x321)
        existing = lifecycle(env, owner, state, command, marker, change)
        if command == 0:
            def allocation(e, call):
                # Distinct preexisting bytes expose partial or misplaced stores.
                if change and call.arguments[0] == 0xB8:
                    replacement = e.object(0x180, 'allocation-state', fill=0)
                    e.put(replacement + 0xBC, marker ^ 0x876)
                    e.put(owner + 0x6C, replacement)
                    e.put(state + 0x18, existing)
                return e.object(call.arguments[0], 'allocation', fill=0x67)
            env.override(NEW, allocation)
        return tokens
    return setup


def cases(random_source):
    commands = (0, 1, 28, 29, 30, 31, 999, 1000, 1001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)
    for command in commands:
        for change in (False, True):
            marker = random_source.randrange(1, 0x7FFFFFFF)
            yield Case(f'command {command:#x} mutation {change}', ENTRY,
                       setup_case(command, marker, change=change), arguments=(lambda t: t['owner'],))
    for mode in (1, 2):
        yield Case(f'construct resource mode {mode}', ENTRY,
                   setup_case(0, random_source.randrange(1, 0x7FFFFFFF), mode),
                   arguments=(lambda t: t['owner'],))

    def initializer_alias(env):
        tokens = setup_case(0, random_source.randrange(1, 0x7FFFFFFF))(env)
        methods = env.object(0x24, 'aliased-initializer-methods', fill=0)
        def initialize(e, call):
            e.put(tokens['state'] + 0x18, 0x13579BDF)
            e.put(call.receiver + 0xA4, 0x2468ACE1)
            return 0x98765432
        env.put(methods + 0x10, env.stub('aliased-init', 'thiscall', 0, initialize))
        node = env.get(0x537668 + 0x18)
        env.put(node + 0x10, methods)
        def allocation(e, call):
            storage = e.object(0x220, 'aliased-parent-storage', fill=0)
            parent = storage + 0x20
            # The original idle-state store aliases the final parent vtable.
            e.put(tokens['owner'] + 0x6C, parent - 0x1C)
            return parent
        env.override(NEW, allocation)
        return tokens
    yield Case('constructor state aliases parent vtable before virtual init', ENTRY,
               initializer_alias, arguments=(lambda t: t['owner'],))
