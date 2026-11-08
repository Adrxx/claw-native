"""Original actor and sound cleanup behavior, including callback publication."""
from clawparity.cases import Case


def cases(random_source):
    def patterned(env, size, name):
        return env.object(size, name, data=bytes(random_source.randrange(256) for _ in range(size)))

    def sound_setup(count=0, enabled=1, mutate=False, terminal=0):
        def setup(env):
            service = patterned(env, 0x40, 'service')
            owner = patterned(env, 0x80, 'sound owner')
            log = env.object(0x400, 'callback observations', fill=0)
            env.put(service + 0x10, owner)
            env.put(owner + 0x78, enabled)
            nodes = [patterned(env, 0x20, f'node {i}') for i in range(count)]
            def record(env, call, kind, node):
                index = env.get(log)
                env.put(log + 4 + index * 32, kind, call.receiver, call.arguments[0], env.get(service), env.get(service + 0x30), env.get(service + 0x34), env.get(node + 0xc), env.get(node))
                env.put(log, index + 1)
            for i, node in enumerate(nodes):
                interface = patterned(env, 8, f'interface {i}')
                methods = env.object(12, f'interface methods {i}')
                vt = env.object(4, f'node methods {i}')
                alternate = env.object(4, f'alternate methods {i}')
                def destroyed(env, call, node=node):
                    record(env, call, 2, node)
                    if terminal and node == nodes[-1]:
                        env.put(service + 0x30, terminal)
                    env.release(call.receiver)
                    return 0x87654321
                def alternate_destroyed(env, call, node=node):
                    record(env, call, 3, node)
                    if terminal and node == nodes[-1]:
                        env.put(service + 0x30, terminal)
                    env.release(call.receiver)
                    return 0xabcdef01
                env.put(vt, env.stub(f'node delete {i}', 'thiscall', 1, destroyed))
                env.put(alternate, env.stub(f'alternate delete {i}', 'thiscall', 1, alternate_destroyed))
                def interface_release(env, call, node=node, alternate=alternate):
                    record(env, call, 1, node)
                    if mutate:
                        env.put(node, alternate)
                        env.put(node + 0xc, call.arguments[0] + 4)
                    return 0x80004005
                env.put(methods + 8, env.stub(f'interface release {i}', 'stdcall', 1, interface_release))
                env.put(interface, methods)
                env.put(node, vt, nodes[i + 1] + 4 if i + 1 < count else 0, nodes[i - 1] + 4 if i else 0, interface)
            env.put(service + 0x30, nodes[0] + 4 if nodes else terminal, nodes[-1] + 4 if nodes else 0)
            return {'service': service, 'nodes': nodes}
        return setup

    for fn in (0x4b3d70, 0x4b4700):
        yield Case(f'{fn:x} preserves neighboring words', fn, lambda env: patterned(env, 32, 'receiver'), receiver=lambda t: t)
    for flag in (0, 1, 2, 3, 0x100, 0x101, 0x80000000, 0xffffffff):
        yield Case(f'leaf deletion flag {flag:x}', 0x4b46e0, lambda env: patterned(env, 32, 'leaf'), receiver=lambda t: t, arguments=(flag,))
        yield Case(f'list deletion flag {flag:x}', 0x4b4240, sound_setup(2 if flag & 1 else 0), receiver=lambda t: t['service'], arguments=(flag,))
    for count in (0, 1, 2, 4):
        for mutate in (False, True):
            yield Case(f'list destructor {count} nodes mutate {mutate}', 0x4b4260, sound_setup(count, mutate=mutate), receiver=lambda t: t['service'])
    for count in (0, 1, 3):
        yield Case(f'list sentinel four after {count} nodes', 0x4b4260, sound_setup(count, terminal=4), receiver=lambda t: t['service'])
    for enabled in (0, 1, 0xffffffff):
        for position in range(3):
            yield Case(f'release position {position} enabled {enabled:x}', 0x4b43e0, sound_setup(3, enabled, True), receiver=lambda t: t['service'], arguments=(lambda t, p=position: t['nodes'][p],))
    yield Case('disabled owner does not inspect null node', 0x4b43e0, sound_setup(enabled=0), receiver=lambda t: t['service'], arguments=(0,))

    def actor_setup(count, position, blocks=False):
        def setup(env):
            owner = patterned(env, 0x30, 'actor list owner')
            actor = patterned(env, 0x70, 'actor')
            block = env.object(64, 'allocation block') if blocks else 0
            other_block = env.object(48, 'older allocation block') if blocks else 0
            if blocks:
                env.put(block, other_block)
                env.put(other_block, 0)
            links = [block + 16] if blocks else [env.object(12, f'actor link {i}') for i in range(count)]
            free = env.object(8, 'old free link')
            log = env.object(40, 'actor callback observation')
            vt = env.object(8, 'actor methods')
            for i, link in enumerate(links):
                env.put(link, links[i + 1] if i + 1 < count else 0, links[i - 1] if i else 0, 0x10203040 + i)
            env.put(owner + 0x14, links[0], links[-1], count, free, block)
            env.put(actor, vt)
            env.put(actor + 0x68, links[position])
            def destroy(env, call):
                env.put(log, call.receiver, call.arguments[0], env.get(owner + 0x14), env.get(owner + 0x18), env.get(owner + 0x1c), env.get(owner + 0x20), 0 if blocks else env.get(links[position]), env.get(actor + 0x68))
                env.release(call.receiver)
                return 0xffffffff
            env.put(vt + 4, env.stub('actor deleting destructor', 'thiscall', 1, destroy))
            return owner, actor
        return setup
    for count in (1, 2, 4):
        for position in range(count):
            yield Case(f'actor unlink {position} of {count}', 0x4c92f0, actor_setup(count, position), receiver=lambda t: t[0], arguments=(lambda t: t[1],))

    yield Case('actor final link aliases released allocation block', 0x4c92f0, actor_setup(1, 0, True), receiver=lambda t: t[0], arguments=(lambda t: t[1],))
