"""Original-only lifecycle and construction inputs for LavaGeyser."""
from clawparity.cases import Case
from clawparity.world import world, cstring, animation, sprite

ENTRY = 0x4559E0
NEW = 0x4F63EC


def setup_case(command, salt, resources='miss', perturb=False):
    def setup(env):
        anim = animation(env, 37 + salt % 100)
        image = sprite(env, 11 + salt % 51, 19 + salt % 29)
        maps = {}
        if resources == 'hit':
            maps = {'sprites': {'LEVEL_LAVAGEYSER': image},
                    'animations': {'LEVEL_LAVAGEYSER': anim}}
        elif resources == 'fallback':
            maps = {'animations': {'GAME_NULL': anim}}
        tokens = world(env, resources=maps, idle_state=None,
                       owner_words={0x4C: salt, 0x50: salt ^ 0x12345, 0x104: salt},
                       state_words={0x1C: command, 0xBC: salt, 0xF0: 3, 0xF4: 7,
                                    0xF8: 11, 0xFC: 13, 0x100: 17})
        owner, state = tokens['owner'], tokens['state']
        player = env.object(0x80, 'player', fill=0)
        player_state = env.object(0x80, 'player-state', fill=0)
        player_logic = env.object(0x84, 'player-logic', fill=0)
        env.put(player + 0x6C, player_state)
        env.put(player_state + 0x14, player_logic)
        env.put(player_logic + 0x80, salt ^ 0xBADC0DE)
        env.put(0x537E88, player)
        env.put(0x537210, salt)
        # Registry entries are CString objects, with valid ownership headers.
        key = cstring(env, 'ES_IDLE')
        node = env.object(20, 'state-registry', words=[0, 0, 0, key, 9], fill=0)
        env.put(node, node, node)
        env.put(0x537668 + 0x18, node)
        if command == 0:
            if perturb == 'alias':
                methods = env.object(0x24, 'alias-init-vtable', fill=0)
                def init(e, call):
                    e.put(call.receiver + 0x14, e.get(state + 0x18))
                    e.put(state + 0x18, salt ^ 0xAABB)
                    return 0
                env.put(methods + 0x10, env.stub('alias-init', 'thiscall', 0, init))
                env.put(player_logic + 0x80, methods)
                def alias_alloc(e, call):
                    if call.arguments[0] == 0xA8:
                        block = e.object(0x180, 'allocation-with-state-prefix', fill=0)
                        e.put(owner + 0x6C, block)
                        e.put(block + 0x1C, 733)
                        return block + 0x64
                    return e.object(call.arguments[0], 'allocation', fill=0)
                env.override(NEW, alias_alloc)
            elif perturb:
                replacement = env.object(0x180, 'replacement-state', fill=0)
                env.put(replacement + 0x1C, 733, 0, 0)
                env.put(replacement + 0xBC, salt ^ 99)
                def alloc(e, call):
                    result = e.object(call.arguments[0], 'allocation', fill=0xA7)
                    if call.arguments[0] == 0xA8:
                        e.put(owner + 0x6C, replacement)
                        e.put(state + 0x18, salt ^ 0x9988)
                    return result
                env.override(NEW, alloc)
        else:
            target = env.object(0xA8, 'lifecycle',
                                words=[(salt ^ (i * 0x1020305)) & 0xFFFFFFFF
                                       for i in range(0xA8 // 4)], fill=0)
            table = env.object(0x24, 'lifecycle-vtable', fill=0)
            env.put(target, table)
            env.put(target + 0x10, state)
            env.put(state + 0x18, target)
            text = cstring(env, 'ES_SYNTHETIC')
            registry = env.object(4, 'numeric-state-entry', words=[text], fill=0)
            env.put(0x5376A0, command, command, registry, registry, 4, 0, 0)
            for offset, argc in ((4, 1), (8, 1), (12, 1), (0x1C, 0), (0x20, 0)):
                def effect(e, call, off=offset):
                    e.put(call.receiver + 0x14, salt ^ off)
                    e.put(state + 0x18, target)
                    e.put(call.receiver + 0x24, salt ^ 0xFACE ^ off)
                    return salt ^ (off + 77)
                env.put(table + offset, env.stub('lifecycle-%x' % offset, 'thiscall', argc, effect))
        return tokens
    return setup


def cases(random_source):
    for command in (1, 28, 29, 30, 31, 999, 1000, 1001, 0xFFFFFFFF, 0x80000000):
        for _ in range(2):
            salt = random_source.randrange(1, 0x7FFFFFFF)
            yield Case('command-%x-salt-%x' % (command, salt), ENTRY,
                       setup_case(command, salt), arguments=(lambda t: t['owner'],))
    for mode in ('miss', 'hit', 'fallback'):
        for perturb in (False, True, 'alias'):
            salt = random_source.randrange(1, 0x7FFFFFFF)
            yield Case('construct-%s-perturb-%s' % (mode, perturb), ENTRY,
                       setup_case(0, salt, mode, perturb), arguments=(lambda t: t['owner'],))
