"""Independent original-only destruction inputs and callback observations."""
from clawparity.cases import Case

DELETE = 0x4F6428
FREE = 0x4A49B0
DECREMENT = 0x5469E8
SLOTS = (0x6C, 0x70, 0x78)
WRAPPERS = ((0x47CC80, 0x47CCA0), (0x4C80C0, 0x4C80E0),
            (0x4C99A0, 0x4C99C0), (0x4C9B30, 0x4C9B50),
            (0x4C9BE0, 0x4C9C00), (0x4C9E60, 0x4C9E80))


def actor_setup(body, salt, mask=0, mutation=False, capacity=32,
                string_refs=None, string_reload=False, registry='empty'):
    def setup(env):
        size = {0x47CCA0: 0x304, 0x4C80E0: 0x1C,
                0x4C9B50: 0x10, 0x4C9C00: 0x198,
                0x4DBCD0: 0x10}.get(body, 0xC8)
        words = [((salt + 0x1020305 * (i + 1)) & 0xFFFFFFFF) or 7
                 for i in range(size // 4)]
        actor = env.object(size, 'actor', words=words)
        log = env.object(8192, 'surviving-observations', fill=0)

        def observe(env, kind, receiver, arguments):
            index = env.get(log)
            at = log + 4 + index * (size + 24)
            env.put(at, kind, receiver, len(arguments), *(tuple(arguments) + (0, 0))[:2])
            env.write(at + 24, env.read(actor, size))
            env.put(log, index + 1)

        def release(env, call):
            observe(env, 0xD311, call.receiver, call.arguments)
            if mutation and body == 0x4C80E0 and call.arguments[0] != actor:
                env.put(actor + 0x18, children[1])
                env.put(actor + 0x10, 0xBEEF0123)
            env.release(call.arguments[0])
            return 0xF00D3210

        env.override(DELETE, release)
        env.override(FREE, release)
        env.put(0x544D18, 0)
        children = []
        if body in (0x4C80E0, 0x4C99C0, 0x4C9A70, 0x4C9C00, 0x4C9E80):
            for i in range(6):
                child = env.object(16, f'child-{i}', words=[0, salt ^ (i + 1), 0xC0010000 + i, 0xBAD00000 + i])
                table = env.object(8, f'child-vtable-{i}')

                def callback(env, call, i=i):
                    observe(env, 0xCA110000 + i, call.receiver, call.arguments)
                    env.put(call.receiver + 8, env.get(call.receiver + 8) + 1)
                    if mutation and body != 0x4C80E0:
                        if i == 0:
                            env.put(actor + 0x70, children[3])
                        elif i == 3:
                            env.put(actor + 0x78, children[2])
                        elif i == 2:
                            # Earlier slots have been cleared: revive them for round two.
                            env.put(actor + 0x6C, children[4])
                            env.put(actor + 0x70, children[5])
                        elif i == 5:
                            env.put(actor + 0x78, children[1])
                        env.put(actor + 0x20, 0xABCD0000 + i)
                    return (0, 1, 0xFFFFFFFF, 0x80004005, salt, 0x12345678)[i]

                method = env.stub(f'child-{i}-destroy', 'thiscall', 1, callback)
                env.put(table, method, method)
                env.put(child, table)
                children.append(child)
            if body == 0x4C80E0:
                env.put(actor + 0x14, env.object(27, 'buffer', fill=0xA7) if mask & 1 else 0)
                env.put(actor + 0x18, children[0] if mask & 2 else 0)
            else:
                for i, offset in enumerate(SLOTS):
                    env.put(actor + offset, children[i] if mask & (1 << i) else 0)

        if body in (0x47CCA0, 0x4DBCD0):
            nested = actor + 0x2F4 if body == 0x47CCA0 else actor
            registry_object = env.object(12, 'registry', words=[salt, 0x51515151, 0x62626262])
            env.put(nested + 4, registry_object, capacity,
                    env.object(48, 'capacity-buffer', fill=0xAC))
            if registry != 'empty':
                # Numeric identities are sorted, and the middle entry can be removed.
                identities = [nested - 8, nested, nested + 8]
                if registry == 'miss':
                    identities = [nested - 8, nested + 4, nested + 8]
                env.put(0x544D18, 3)
                for i, identity in enumerate(identities):
                    env.put(0x544B98 + i * 12, identity, 0xDADA0010 + i, 0xBABA0020 + i)
            if body == 0x47CCA0:
                empty = env.object(16, 'shared-empty-header', words=[0xFFFFFFFF, 0, 0, 0])
                env.put(0x52E1C8, empty)
                string_headers = []
                for i, offset in enumerate((0x1A8, 0x1A4)):
                    if string_refs is None:
                        env.put(actor + offset, empty + 12)
                    else:
                        header = env.object(24, f'string-{i}', words=[string_refs[i], 8 + i, 9 + i, salt, salt ^ 0x78, 0xAB])
                        string_headers.append(header)
                        env.put(actor + offset, header + 12)
                replacement = env.object(24, 'replacement-string', words=[1, 4, 5, salt, 0, 0])

                def decrement(env, call):
                    observe(env, 0xDEC, call.receiver, call.arguments)
                    at = call.arguments[0]
                    value = (env.get(at) - 1) & 0xFFFFFFFF
                    env.put(at, value)
                    if string_reload and at == string_headers[0]:
                        env.put(actor + 0x1A8, replacement + 12)
                        env.put(actor + 0x1A4, empty + 12)
                    return value

                env.override(DECREMENT, decrement)
        return {'actor': actor}
    return setup


def cases(random_source):
    salt = random_source.getrandbits(32)
    for wrapper, body in WRAPPERS:
        for flags in (0, 1, 2, 3, 0x100, 0xFFFFFFFE, 0x80000101):
            yield Case(f'{wrapper:x} delete flags {flags:x}', wrapper,
                       actor_setup(body, salt ^ flags, mask=7),
                       receiver=lambda t: t['actor'], arguments=(flags,))
    for body in (0x4C99C0, 0x4C9A70, 0x4C9C00, 0x4C9E80):
        for mask in range(8):
            yield Case(f'{body:x} child presence {mask}', body,
                       actor_setup(body, random_source.getrandbits(32), mask=mask),
                       receiver=lambda t: t['actor'])
        yield Case(f'{body:x} callbacks replace later slots and repopulate earlier slots', body,
                   actor_setup(body, salt, mask=7, mutation=True), receiver=lambda t: t['actor'])
    for mask in range(4):
        yield Case(f'buffer/child presence {mask}', 0x4C80E0,
                   actor_setup(0x4C80E0, salt, mask=mask), receiver=lambda t: t['actor'])
    yield Case('buffer release replaces child before its load', 0x4C80E0,
               actor_setup(0x4C80E0, salt, mask=3, mutation=True), receiver=lambda t: t['actor'])
    yield Case('animation reset retains zero index', 0x4C9B50,
               actor_setup(0x4C9B50, salt), receiver=lambda t: t['actor'])
    for capacity in (0, 1, 31, 32, 33, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        for registry in ('empty', 'found', 'miss'):
            yield Case(f'capacity {capacity:x} registry {registry}', 0x4DBCD0,
                       actor_setup(0x4DBCD0, salt, capacity=capacity, registry=registry),
                       receiver=lambda t: t['actor'])
    for refs in (None, (1, 1), (2, 3), (0, 0x80000000), (0x80000001, 1)):
        yield Case(f'compound strings references {refs}', 0x47CCA0,
                   actor_setup(0x47CCA0, salt, capacity=33, string_refs=refs, registry='found'),
                   receiver=lambda t: t['actor'])
    yield Case('CString decrement changes string pointers before reload', 0x47CCA0,
               actor_setup(0x47CCA0, salt, string_refs=(1, 1), string_reload=True),
               receiver=lambda t: t['actor'])
    for state in ('null-global', 'different-id', 'null-child', 'wrong-kind', 'matching', 'zero-id'):
        identity = random_source.getrandbits(32) or 71

        def setup(env, state=state, identity=identity):
            outer = env.object(0x70, 'global-owner', fill=0x59)
            inner = env.object(0x134, 'global-child', fill=0xA3)
            selected = 0 if state == 'zero-id' else identity
            env.put(0x53C9AC, 0 if state == 'null-global' else outer)
            env.put(0x53C9B0, selected)
            env.put(outer + 0x6C, 0 if state == 'null-child' else inner)
            env.put(inner + 0x1C, 16 if state == 'wrong-kind' else 15)
            return {'identity': selected ^ 1 if state == 'different-id' else selected}

        yield Case(f'global invalidation {state}', 0x48CF50, setup,
                   arguments=(lambda t: t['identity'],))
