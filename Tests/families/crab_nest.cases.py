"""Blind original-only cases for CrabNest dispatch and construction."""
from clawparity.cases import Case
from clawparity.world import world, cstring

ENTRY = 0x432570


def dispatch_setup(state_value, salt, change=False):
    def setup(env):
        tokens = world(env, idle_state=None)
        owner, state = tokens['owner'], tokens['state']
        target = env.object(0x58, 'existing-nest', words=[salt + i * 0x101 for i in range(22)])
        table = env.object(0x24, 'nest-methods', fill=0)
        env.put(target, table)
        env.put(target + 0x10, state)
        env.put(state + 0x18, target, state_value)
        env.put(state + 0x20, salt ^ 0x24681357)
        env.put(owner + 0x4c, salt, salt ^ 0x12345678)
        def method(offset):
            def effect(env, call):
                env.put(call.receiver + 0x40, salt ^ offset)
                env.put(state + 0x20, salt + offset)
                if change:
                    env.put(state + 0x18, replacement)
                    env.put(state + 0x1c, salt ^ 0xabcdef01)
                return salt ^ 0xfedcba98
            return effect
        replacement = env.object(0x58, 'alternate-nest', fill=0x6b)
        env.put(replacement, table)
        for offset, argc in ((4, 1), (8, 1), (12, 1), (0x1c, 0), (0x20, 0)):
            env.put(table + offset, env.stub('nest-method-%x' % offset, 'thiscall', argc, method(offset)))
        # Numeric-state lookup is real game code over a singleton CString table.
        text = cstring(env, 'distinct-state-%x' % salt)
        record = env.object(12, 'numeric-state-record', words=[text, salt ^ 0x9876, salt])
        env.put(0x5376a0, state_value, state_value, record, record, 12)
        return tokens
    return setup


def construction_setup(salt, count, redirect=False):
    def setup(env):
        sequence = env.object(0x30, 'hatch-animation-resource', fill=0x4d)
        sound = env.object(0x30, 'boink-sound-resource', fill=0x7a)
        tokens = world(env, resources={'animations': {'LEVEL_HATCHNEST': sequence},
                                        'sounds': {'GAME_BOINK': sound}}, owner_words={8: salt, 0x4c: salt & 255, 0x50: salt >> 8, 0x64: 2},
                       state_words={0x1c: 0, 0x2c: 11, 0x30: 37, 0x34: 53, 0x38: 89, 0x64: count},
                       idle_state=None)
        env.put(tokens['state'] + 0x18, env.object(0x58, 'prior-publication', fill=0x57))
        key = cstring(env, 'ES_IDLE', 'nest-idle-name')
        node = env.object(20, 'nest-idle-state', fill=0)
        env.put(node, node, node, 0, key, salt ^ 0x3956)
        env.put(0x537668 + 0x18, node)
        original_state = tokens['state']
        alternate_state = env.object(0x180, 'constructor-alternate-state', fill=0)
        env.put(alternate_state + 0x1c, salt, 0, 0, 0, 17, 23, 41, 59)
        env.put(alternate_state + 0x64, count)
        def allocate(env, call):
            address = env.object(call.arguments[0], 'constructor-allocation',
                                 words=[(salt + i * 0x1020305) & 0xffffffff
                                        for i in range(call.arguments[0] // 4)])
            env.put(original_state + 0x20, salt ^ 0x76543210)
            if redirect:
                env.put(tokens['owner'] + 0x6c, alternate_state)
            return address
        env.override(0x4f63ec, allocate)
        return tokens
    return setup


def cases(random_source):
    for value in (1, 28, 29, 30, 31, 999, 1000, 1001, 0x7fffffff, 0x80000000, 0xffffffff):
        for change in (False, True):
            salt = random_source.randrange(1, 0x7fffffff)
            yield Case('dispatch-%x-%s' % (value, change), ENTRY,
                       dispatch_setup(value, salt, change), arguments=(lambda t: t['owner'],))
    for count in (0, 1, 9, 10, 0xffffffff):
        salt = random_source.randrange(1, 0x7fffffff)
        for redirect in (False, True):
            yield Case('construct-count-%x-redirect-%s' % (count, redirect), ENTRY,
                       construction_setup(salt, count, redirect),
                       arguments=(lambda t: t['owner'],))

    for index in range(8):
        salt = random_source.randrange(1, 0x7fffffff)
        yield Case('aliased-construction-publication-%d' % index, ENTRY,
                   aliased_construction_setup(salt), arguments=(lambda t: t['owner'],))


def aliased_construction_setup(salt):
    def setup(env):
        tokens = world(env, idle_state=None,
                       owner_words={8: salt, 0x4c: salt & 255, 0x50: salt >> 8, 0x64: 2})
        backing = env.object(0x200, 'overlapping-state-allocation', fill=0)
        target = backing + 0x40
        state = target - 0x1c
        tokens['state'] = state
        env.put(tokens['owner'] + 0x6c, state)
        prior = env.object(0x58, 'aliased-prior-publication', fill=0x37)
        replacement = env.object(0x58, 'callback-publication-marker', fill=0x61)
        env.put(state + 0x18, prior, 0)
        methods = env.object(0x24, 'constructor-produced-methods', fill=0)
        def initialized(env, call):
            # Copy the publication state into surviving object data so the
            # order remains observable even after the callback returns.
            env.put(call.receiver + 0x40, env.get(state + 0x18), salt)
            env.put(state + 0x18, replacement)
            env.put(tokens['owner'] + 0x80, call.receiver, salt ^ 0x71359246)
            return salt
        env.put(methods + 0x10, env.stub('aliased-nest-initialize', 'thiscall', 0, initialized))
        key = cstring(env, 'ES_IDLE', 'aliased-idle-key')
        node = env.object(20, 'aliased-idle-registry', fill=0)
        env.put(node, node, node, 0, key, methods)
        env.put(0x537668 + 0x18, node)
        # The original constructor's final numeric state store overlaps its
        # vtable word. This is input aliasing, with all accesses backed by one
        # live object; no original function or code pointer is patched.
        def allocate(env, call):
            return target
        env.override(0x4f63ec, allocate)
        return tokens
    return setup
