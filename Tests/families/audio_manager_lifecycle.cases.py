"""Original-backed audio manager lifecycle cases; COM alone is physical."""
from clawparity.cases import Case


def quiet(env):
    env.put(0x54130C, 0, 0, 0, 0)


def record(env, log, tag, call, manager):
    at = env.get(log)
    env.put(log + 4 + at * 32, tag, call.receiver,
            *(list(call.arguments) + [0, 0, 0])[:3],
            env.get(manager), env.get(manager + 0x78), env.get(manager + 0x7C))
    env.put(log, at + 1)


def manager_setup(fill, enabled=0, head=0, create_result=0, cooperative=0,
                  replace_device=False, diagnostic=False):
    def setup(env):
        quiet(env)
        manager = env.object(0x90, 'manager', data=fill)
        log = env.object(4096, 'physical-observations', fill=0)
        env.put(manager + 4, head, 0, 0, 0)
        env.put(manager + 0x78, enabled)

        def device(name):
            obj = env.object(4, name)
            table = env.object(0x1C, name + '-vtable')
            env.put(obj, table)

            def release(env, call):
                record(env, log, 2, call, manager)
                # Publication during the callback must be overwritten by shutdown.
                env.put(manager + 0x78, 0xCAFEBABE)
                return 0x87654321

            env.put(table + 8, env.stub(name + '::Release', 'stdcall', 1, release))
            return obj, table

        first, methods = device('directsound')
        second, _ = device('replacement-directsound')
        env.put(manager + 0x14, first)

        def set_cooperative(env, call):
            record(env, log, 1, call, manager)
            if replace_device:
                env.put(manager + 0x14, second)
            return cooperative

        env.put(methods + 0x18, env.stub('SetCooperativeLevel', 'stdcall', 3, set_cooperative))

        def create(env, call):
            record(env, log, 0, call, manager)
            env.put(call.arguments[1], first)
            return create_result

        env.override(0x546864, create)
        if diagnostic:
            env.put(0x541314, 1)

            def beep(env, call):
                record(env, log, 3, call, manager)
                # The original diagnostic executes between the COM methods.
                env.put(manager + 0x14, second)
                return 0x12345678

            env.override(0x546CA4, beep)
        return {'manager': manager, 'log': log, 'device': first}
    return setup


def lists(fill, entry, count=0, terminal=0, enabled=1, mutate=False,
          stop_error=0, ambient=False, children=False, voice_enabled=None):
    def setup(env):
        tokens = manager_setup(fill, enabled=enabled)(env)
        manager, log = tokens['manager'], tokens['log']
        voice_manager = manager
        if voice_enabled is not None:
            voice_manager = env.object(0x80, 'independent-voice-manager', fill=0)
            env.put(voice_manager + 0x78, voice_enabled)
        nodes = [env.object(0x38, f'voice-{i}', fill=0x51+i) for i in range(count)]
        for i, node in enumerate(nodes):
            interface = env.object(4, f'buffer-{i}')
            methods = env.object(0x4C, f'buffer-vtable-{i}')
            env.put(interface, methods)
            env.put(node, 0x513508, nodes[i+1]+4 if i+1<count else terminal,
                    nodes[i-1]+4 if i else 0, interface, voice_manager)
            env.put(node + 0x30, 0)
            if children:
                child = env.object(0x38, f'child-voice-{i}', fill=0x91+i)
                child_buffer = env.object(4, f'child-buffer-{i}')
                child_methods = env.object(0x4C, f'child-vtable-{i}')
                env.put(child, 0x513508, 0, 0, child_buffer, voice_manager)
                env.put(child + 0x30, 0)
                env.put(child_buffer, child_methods)

                def child_stop(env, call, node=node, i=i):
                    record(env, log, 30+i, call, manager)
                    if mutate and i == 0:
                        env.put(node + 4, terminal)
                    return stop_error

                env.put(child_methods + 0x48,
                        env.stub(f'child-{i}::Stop', 'stdcall', 1, child_stop))
                env.put(node + 0x30, child+4)

            def stop(env, call, node=node, i=i):
                record(env, log, 10+i, call, manager)
                if mutate and i == 0 and not children:
                    env.put(node + 4, terminal)
                return stop_error

            def buffer_release(env, call, i=i):
                record(env, log, 20+i, call, manager)
                return 0

            env.put(methods + 0x48, env.stub(f'buffer-{i}::Stop', 'stdcall', 1, stop))
            env.put(methods + 8, env.stub(f'buffer-{i}::Release', 'stdcall', 1, buffer_release))
        root = env.object(0x38, 'voice-root', fill=0xAE)
        env.put(root + 0x10, manager)
        env.put(root + 0x30, nodes[0]+4 if nodes else terminal)
        env.put(manager + 4, nodes[0]+4 if nodes else terminal,
                nodes[-1]+4 if nodes else 0, 0, 0)
        if ambient and nodes:
            item = env.object(0x14, 'ambient-registration')
            env.put(item, 0x513518, 0, 0, 0x1234, nodes[0])
            env.put(manager + 0xC, item+4, item+4)
        tokens['receiver'] = root if entry == 0x4B4670 else manager
        return tokens
    return setup


def cases(random_source):
    def random_fill():
        return bytes(random_source.randrange(1, 256) for _ in range(0x90))

    def table_setup(env):
        quiet(env)
        env.write(0x541174, bytes([0xA5]) * 412)
        quiet(env)
    yield Case('volume table overwrites all 101 distinct words', 0x4B3C80, table_setup)
    for _ in range(3):
        initial = random_fill()
        initial_table = bytes(random_source.randrange(1, 256) for _ in range(404))

        def constructor_setup(env, initial=initial, initial_table=initial_table):
            quiet(env)
            env.write(0x541178, initial_table)
            return {'manager': env.object(0x90, 'uninitialized-manager', data=initial)}

        yield Case('construct random manager and replace dirty table', 0x4B4710,
                   constructor_setup, receiver=lambda t: t['manager'])
    for function in (0x4B4770, 0x4B4790, 0x4B4860):
        for enabled in (0, 1, 0x80000000):
            for head in (0, 4):
                flags = (0, 1, 0xFFFFFF00, 0xFFFFFF01, 0x100, 0x101) if function == 0x4B4770 else (None,)
                for flag in flags:
                    yield Case(f'lifecycle {function:x} enabled {enabled:x} head {head} flags {flag}',
                               function, manager_setup(random_fill(), enabled=enabled, head=head),
                               receiver=lambda t: t['manager'], arguments=() if flag is None else (flag,))
    for create_result, cooperative in ((0, 0), (1, 0), (0x80004005, 0),
                                       (0xFFFFFFFF, 0), (0, 1), (0, 0x80004005), (0, 0xFFFFFFFF)):
        for replace in (False, True):
            args = (random_source.getrandbits(32), random_source.getrandbits(32))
            yield Case(f'initialize create {create_result:x} cooperative {cooperative:x} replace {replace}',
                       0x4B47E0, manager_setup(random_fill(), enabled=0x76543210,
                       create_result=create_result, cooperative=cooperative, replace_device=replace),
                       receiver=lambda t:t['manager'], arguments=args)
    for function in (0x4B4670, 0x4B4B40):
        for enabled, count, terminal, mutate, error in (
            (0, 2, 0, False, 0), (1, 0, 0, False, 0), (1, 0, 4, False, 0),
            (1, 1, 0, False, 0), (1, 1, 4, False, 1), (0x80000000, 3, 0, False, 0),
            (1, 3, 4, False, 0x80004005), (1, 3, 4, True, 0), (1, 3, 0, True, 0)):
            yield Case(f'walk {function:x} enabled {enabled:x} nodes {count} end {terminal} mutate {mutate} error {error:x}',
                       function, lists(random_fill(), function, count, terminal, enabled, mutate, error),
                       receiver=lambda t:t['receiver'])
    for function in (0x4B4860, 0x4B4790, 0x4B4770):
        for count in (1, 3):
            for ambient in (False, True):
                yield Case(f'real removal {function:x} nodes {count} ambient {ambient}', function,
                           lists(random_fill(), function, count=count, ambient=ambient),
                           receiver=lambda t:t['receiver'], arguments=(1,) if function==0x4B4770 else ())

    for terminal in (0, 4):
        for mutate in (False, True):
            yield Case(f'main walk observes child stops end {terminal} mutate {mutate}',
                       0x4B4B40, lists(random_fill(), 0x4B4B40, count=3,
                       terminal=terminal, mutate=mutate, children=True),
                       receiver=lambda t:t['receiver'])

    for function in (0x4B4670, 0x4B4B40):
        for enabled, voice_enabled in ((0, 1), (1, 0), (0x80000000, 1)):
            yield Case(f'independent guards {function:x} root {enabled:x} voice {voice_enabled}',
                       function, lists(random_fill(), function, count=3, enabled=enabled,
                       voice_enabled=voice_enabled, children=True),
                       receiver=lambda t:t['receiver'])

    for error in (1, 0x80004005, 0xFFFFFFFF):
        yield Case(f'cooperative error executes physical diagnostic {error:x}',
                   0x4B47E0, manager_setup(random_fill(), enabled=0x1234,
                   cooperative=error, diagnostic=True),
                   receiver=lambda t:t['manager'],
                   arguments=(random_source.getrandbits(32), random_source.getrandbits(32)))
