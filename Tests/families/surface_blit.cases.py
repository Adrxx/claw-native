"""Original-only cases for surface blit dispatch, retries and diagnostics."""
from clawparity.cases import Case

COLOR = 0x4B9950
BLIT = 0x4B9CE0
FAST = 0x4B9D80
LOST = 0x887601C2
BEEP = 0x546CA4


def setup_surface(words, function, results, restore_result=1, null_source=False,
                  mutation=0, beep=0):
    def setup(env):
        # Only the early-return/beep diagnostic paths are elected.
        for flag in (0x54139C, 0x5413A0, 0x5413A8):
            env.put(flag, 0)
        env.put(0x5413A4, beep)
        receipt = env.object(2048, 'callback-observations', fill=0xCD)
        env.put(receipt, 0)
        wrapper = env.object(32, 'destination-wrapper', words=words[:8])
        source = env.object(32, 'source-wrapper', words=words[8:16])
        wrapper_vtables = [env.object(32, f'wrapper-vtable-{i}', fill=0xA0+i) for i in range(2)]
        interfaces = [env.object(16, f'COM-surface-{i}', words=words[16+i:20+i]) for i in range(4)]
        tables = [env.object(120, f'COM-vtable-{i}', fill=0x70+i) for i in range(4)]
        rect1 = env.object(16, 'destination-rectangle', words=words[20:24])
        rect2 = env.object(16, 'source-rectangle', words=words[24:28])
        effects = env.object(100, 'blit-effects', data=b''.join(w.to_bytes(4, 'little') for w in words[:25]))
        key = env.object(8, 'color-key-range', words=words[28:30])
        env.put(wrapper, wrapper_vtables[0])
        env.put(wrapper+8, interfaces[0])
        env.put(source+8, interfaces[2])
        for interface, table in zip(interfaces, tables):
            env.put(interface, table)

        def observe(env, call, tag):
            n = env.get(receipt)
            env.put(receipt+4+n*128, tag, call.receiver, len(call.arguments),
                    *call.arguments)
            env.put(receipt+4+n*128+40, env.get(wrapper), env.get(wrapper+8),
                    env.get(source+8), *[env.get(p) for p in interfaces])
            # Copy pointed-to payloads into surviving memory, so incorrect
            # callbacks/payload publication cannot hide behind fixture assertions.
            env.write(receipt+4+n*128+72, env.read(rect1, 16)+env.read(rect2, 16)+env.read(key, 8))
            env.put(receipt, n+1)

        def com_effect(index):
            def effect(env, call):
                observe(env, call, 0xC000+index)
                n = sum(env.calls_so_far(address) for address in com_stubs)
                if n == 1:
                    if mutation & 1:
                        env.put(wrapper, wrapper_vtables[1])
                    if mutation & 2:
                        env.put(wrapper+8, interfaces[1])
                        env.put(source+8, interfaces[3])
                    if mutation & 4:
                        env.put(interfaces[0], tables[1])
                    # These pointed-to arguments survive all outside calls.
                    if mutation & 8:
                        env.put(rect1+4, words[30])
                        env.put(rect2+8, words[31])
                        env.put(key, words[29], words[28])
                return results[min(n-1, len(results)-1)]
            return effect

        com_stubs = [env.stub(f'COM-method-{i}', 'stdcall', 3 if function == COLOR else 6,
                              com_effect(i)) for i in range(4)]
        slot = 0x74 if function == COLOR else (0x14 if function == BLIT else 0x1C)
        for table, stub in zip(tables, com_stubs):
            env.put(table+slot, stub)

        def restore_effect(index):
            def effect(env, call):
                observe(env, call, 0xD000+index)
                if mutation & 16:
                    env.put(wrapper+8, interfaces[1])
                    env.put(source+8, interfaces[3])
                if mutation & 32:
                    env.put(interfaces[0], tables[1])
                    env.put(interfaces[1], tables[2])
                if mutation & 64:
                    env.put(rect1, words[31])
                    env.put(rect2+12, words[30])
                    env.put(effects+12, words[28])
                return restore_result
            return effect
        for index, table in enumerate(wrapper_vtables):
            env.put(table+0x1C, env.stub(f'restore-{index}', 'thiscall', 0, restore_effect(index)))

        def beep_effect(env, call):
            observe(env, call, 0xBEEF)
            # Logger effects must not replace the saved COM HRESULT.
            env.put(wrapper+12, words[31])
            return 0xDEADBEEF
        env.override(BEEP, beep_effect)
        if function == COLOR:
            args = (words[0], key)
        elif function == BLIT:
            args = (rect1, 0 if null_source else source, rect2, words[1], effects)
        else:
            args = (words[0], words[1], source, rect2, words[2])
        return {'wrapper': wrapper, 'arguments': args}
    return setup


def cases(random_source):
    def emit(label, function, results, **options):
        words = [random_source.getrandbits(32) for _ in range(32)]
        return Case(label, function, setup_surface(words, function, results, **options),
                    receiver=lambda t: t['wrapper'], arguments=tuple(
                        (lambda t, i=i: t['arguments'][i]) for i in range(2 if function == COLOR else 5)))

    for result in (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, LOST, LOST-1, LOST+1):
        yield emit(f'color HRESULT {result:#x}', COLOR, (result,), beep=result & 1,
                   mutation=10)
    for function, name in ((BLIT, 'blit'), (FAST, 'fast')):
        for result in (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, LOST-1, LOST+1):
            yield emit(f'{name} immediate {result:#x}', function, (result,), beep=1,
                       mutation=15)
        for restored in (0, 1, 0x80000000, 0xFFFFFFFF):
            for final in (0, 1, 0x80004005, LOST):
                yield emit(f'{name} restore {restored:#x} retry {final:#x}',
                           function, (LOST, final), restore_result=restored,
                           mutation=127, beep=1)
        # Isolate reloading a changed surface versus the same surface's new vtable.
        for mutation in (1, 2, 4, 8, 16, 32, 64):
            yield emit(f'{name} independent mutation {mutation}', function,
                       (LOST, 0x12345678), mutation=mutation, beep=1)
    for result in (0, 1, 0x80004005, LOST):
        yield emit(f'null source {result:#x}', BLIT, (result,), null_source=True,
                   restore_result=0, beep=1)
