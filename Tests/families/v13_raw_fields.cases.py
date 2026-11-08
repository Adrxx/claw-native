"""Original-only raw actor/logic stream field observations."""
from clawparity.cases import Case

RAW_WRITE, RAW_READ = 0x4c7ab0, 0x4c7f10
LOGIC_WRITE, LOGIC_READ = 0x4d6680, 0x4d6aa0
REVERSE_NAME = 0x4d7010


def setup_for(entry, seed, null=False, size=0, private=True, text=b'',
              binding_mask=0, missing=0, result=1, change='', fail_alloc=False,
              positive=False, bind_result=1, observe=False, custom_empty=False):
    def setup(e):
        obj = e.object(0x200, 'owner', fill=0xa7)
        for off in range(0, 0x200, 4):
            e.put(obj + off, (seed ^ (off * 0x1020301)) & 0xffffffff)
        stream = e.object(4, 'native stream')
        methods = e.object(0x40, 'stream methods')
        replacement = e.object(0x40, 'replacement stream methods')
        trace = e.object(0x10000, 'callback observations', fill=0)
        if custom_empty:
            empty = e.object(32, 'live empty CString global', fill=0)
            e.put(empty, 5, 0, 19)
            e.put(0x52c668, empty + 12)
        data = e.object(256, 'private payload', data=bytes((seed + i * 17) & 255 for i in range(256)))
        alternate = e.object(256, 'replacement private payload', fill=0x39)
        scene = e.object(0x40, 'scene')
        registry = e.object(0x50, 'registry', fill=0)
        e.put(obj + 0xc, scene)
        e.put(scene + 0x14, registry)
        e.put(registry + 0x18, 17)
        # Valid empty CString backing, including the preceding MFC header.
        string = e.object(144, 'CString backing')
        e.put(string, 1, len(text), 128)
        e.write(string + 12, text + b'\0')
        other_string = e.object(144, 'replacement CString backing')
        e.put(other_string, 1, 7, 128)
        e.write(other_string + 12, b'changed\0')
        bindings = []
        configurations = []
        if entry in (RAW_READ, RAW_WRITE):
            e.put(obj + 0xdc, string + 12)
            for i, off in enumerate((0x80, 0x88, 0x90)):
                logic = e.object(0x180, 'binding %d' % i)
                e.put(logic + 0x10, seed ^ (i + 0x314))
                e.put(obj + off, logic if binding_mask & (1 << i) else 0)
                bindings.append(logic)
            if positive:
                buckets = e.object(68, 'string map buckets', fill=0)
                e.put(registry + 0x14, buckets)
                e.put(registry + 0x1c, 3)
                for i, logic in enumerate(bindings):
                    name = (b'Alpha', b'BetaLong', b'Gamma1234')[i]
                    key = e.object(144, 'map CString key', fill=0)
                    e.put(key, 1, len(name), len(name))
                    e.write(key + 12, name + b'\0')
                    h = 0
                    for ch in name:
                        h = (h * 33 + ch) & 0xffffffff
                    bucket = h % 17
                    node = e.object(16, 'map association', fill=0)
                    config = e.object(0x20, 'registered logic configuration', fill=0)
                    e.put(config + 0x10, e.get(logic + 0x10))
                    configurations.append(config)
                    e.put(node, e.get(buckets + bucket * 4), bucket, key + 12, config)
                    e.put(buckets + bucket * 4, node)
                    lvt = e.object(0x20, 'existing logic methods', fill=0)
                    e.put(logic, lvt)
                    def binding_callback(env, call, i=i, logic=logic):
                        n = env.get(trace + 0xc)
                        at = trace + 0xc000 + n * 0x40
                        env.put(at, i, call.receiver, *call.arguments)
                        env.put(at + 0x18, env.get(obj + 0x80), env.get(obj + 0x88), env.get(obj + 0x90))
                        env.put(trace + 0xc, n + 1)
                        if call.arguments:
                            env.put(logic + 0x10, call.arguments[0])
                        return bind_result
                    e.put(lvt + 0x14, e.stub('existing logic cleanup %d' % i, 'thiscall', 0, binding_callback))
                    e.put(lvt + 0x1c, e.stub('existing logic initialize %d' % i, 'thiscall', 2, binding_callback))
        else:
            e.put(obj + 0x14, data if private else 0)
            e.put(obj + 0x178, size)
        reading = entry in (RAW_READ, LOGIC_READ)
        raw = entry in (RAW_READ, RAW_WRITE)

        def io(env, call, tag):
            ptr, count = call.arguments
            n = env.get(trace)
            at = trace + 0x20 + n * 0x100
            env.put(at, tag, call.receiver, ptr, count,
                    env.get(obj + 0x14), env.get(obj + 0x178),
                    env.get(obj + 0x80), env.get(obj + 0x88), env.get(obj + 0x90))
            if observe and count == 128:
                # Actual caller scratch ends immediately below the root return word.
                env.write(at + 0xd0, env.read(ptr + 128, 4))
            if ptr and count <= 256:
                env.write(at + 0x30, env.read(ptr, min(count, 128)))
            env.put(trace, n + 1)
            if reading and ptr:
                if raw and count == 128:
                    seq = env.get(trace + 4)
                    env.put(trace + 4, seq + 1)
                    payload = text if seq == 0 else (b'absent' if seq == missing else ((b'Alpha', b'BetaLong', b'Gamma1234')[seq - 1] if positive else b''))
                    env.write(ptr, payload + b'\0' * (128 - len(payload)))
                elif not raw and ptr == obj + 0x178:
                    env.put(ptr, size)
                else:
                    env.write(ptr, bytes((seed + n * 29 + i * 11) & 255 for i in range(count)))
            if change == 'vtable' and n == 0:
                env.put(stream, replacement)
            elif change == 'fields' and n == 0:
                env.put(obj + 0x20, seed ^ 0x55667788)
                env.put(obj + 0x164, seed ^ 0x11223344)
            elif change == 'bindings' and n == 0:
                for index, off in enumerate((0x80, 0x88, 0x90)):
                    env.put(obj + off, bindings[(index + 1) % 3])
            elif change == 'string' and n == 0:
                env.put(obj + 0xdc, other_string + 12)
            elif change == 'payload' and ptr == obj + 0x178:
                env.put(obj + 0x14, alternate)
                env.put(obj + 0x178, 7)
            return result

        for table, tag in ((methods, 0x10), (replacement, 0x20)):
            for slot in (0x2c, 0x30):
                e.put(table + slot, e.stub('native IO %x %x' % (tag, slot), 'thiscall', 2,
                    lambda env, call, tag=tag + slot: io(env, call, tag)))
        e.put(stream, methods)
        e.override(0x50c318, lambda env, call: len(env.cstr(call.arguments[0])))
        def atomic(env, call, delta):
            if observe:
                n = env.get(trace + 0x1c)
                at = trace + 0xe000 + n * 0x40
                # Original direct reverse-helper automatic objects: CString,
                # candidate, iterator pair and EH phase, recorded at physical calls.
                env.write(at, env.read(0x02008000 - 28, 16))
                env.write(at + 16, env.read(0x02008000 - 4, 4))
                env.put(trace + 0x1c, n + 1)
            pointer = call.arguments[0]
            value = (env.get(pointer) + delta) & 0xffffffff
            env.put(pointer, value)
            return value
        e.override(0x50c310, lambda env, call: atomic(env, call, 1))
        e.override(0x50c314, lambda env, call: atomic(env, call, -1))
        if fail_alloc or change == 'allocate-size':
            def allocate(env, call):
                n = env.get(trace + 8)
                env.put(trace + 8, n + 1)
                env.put(trace + 0x10, call.arguments[0], env.get(obj + 0x14), env.get(obj + 0x178))
                if change == 'allocate-size':
                    env.put(obj + 0x178, 3)
                return 0 if fail_alloc else env.object(max(256, call.arguments[0]), 'allocation', fill=0x73)
            e.override(0x4fcaea, allocate)
        return dict(owner=obj, stream=0 if null else stream, registry=registry,
                    bindings=bindings, configurations=configurations)
    return setup


def field_case(label, entry, seed, scratch_seed=False, **options):
    return Case(label, entry, setup_for(entry, seed, **options),
                receiver=lambda t: t['owner'], arguments=(lambda t: t['stream'],),
                initial_stack=(lambda t: ((-132, t['configurations'][0].to_bytes(4, 'little')),)) if scratch_seed else ())


def field_cases(random_source):
    seed = lambda: random_source.getrandbits(32)
    for entry in (RAW_WRITE, RAW_READ, LOGIC_WRITE, LOGIC_READ):
        yield field_case('%x null stream' % entry, entry, seed(), null=True)
        for result in (0, 1, 0x80004005, 0xffffffff):
            yield field_case('%x ignored IO result %x' % (entry, result), entry, seed(), result=result)
        for change in ('vtable', 'fields'):
            yield field_case('%x callback changes %s' % (entry, change), entry, seed(), change=change)
    for entry in (RAW_WRITE, RAW_READ):
        for length in (1, 2, 3, 4, 7, 31, 126, 127):
            text = bytes(random_source.randrange(33, 127) for _ in range(length))
            yield field_case('%x name length %d' % (entry, length), entry, seed(), text=text)
    yield field_case('write rereads name after first callback', RAW_WRITE, seed(), change='string')
    for mask in range(1, 8):
        yield field_case('write binding mask %d' % mask, RAW_WRITE, seed(), binding_mask=mask)
    for mask in range(1, 8):
        yield field_case('write actual registry names mask %d' % mask, RAW_WRITE, seed(), binding_mask=mask, positive=True)
    yield field_case('write callback permutes registered binding receivers', RAW_WRITE, seed(), binding_mask=7, positive=True, change='bindings')
    for status in (0, 1, 0xffffffff):
        yield field_case('read resolves three registered bindings result%x' % status, RAW_READ, seed(), binding_mask=7, positive=True, bind_result=status)
    for index in (1, 2, 3):
        yield field_case('read missing binding %d' % index, RAW_READ, seed(), missing=index)
    for entry in (LOGIC_WRITE, LOGIC_READ):
        for size in (0, 1, 2, 3, 4, 7, 15, 31, 128, 255):
            for private in (False, True):
                yield field_case('%x private%d size%d' % (entry, private, size), entry, seed(), size=size, private=private)
        yield field_case('%x callback redirects payload' % entry, entry, seed(), size=13, change='payload')
    yield field_case('read publishes failed allocation and still calls IO', LOGIC_READ, seed(), size=13, fail_alloc=True)
    yield field_case('read reloads length after allocation', LOGIC_READ, seed(), size=13, change='allocate-size')


def reverse_setup(seed, choice, populated=True, duplicate=False, null_value=False, observe=False, custom_empty=False):
    def setup(env):
        tokens = setup_for(RAW_WRITE, seed, binding_mask=7, positive=populated, observe=observe, custom_empty=custom_empty)(env)
        probe = env.object(0x20, 'reverse lookup probe', fill=0)
        env.put(probe + 0x10, seed ^ 0x13579bdf)
        if choice < 3:
            probe = tokens['bindings'][choice]
        if duplicate:
            for config in tokens['configurations']:
                env.put(config + 0x10, env.get(probe + 0x10))
        if null_value:
            buckets = env.get(tokens['registry'] + 0x14)
            for bucket in range(17):
                node = env.get(buckets + bucket * 4)
                if node:
                    env.put(node + 0xc, 0)
                    break
        tokens['probe'] = probe
        tokens['output'] = env.object(4, 'reverse lookup output', fill=0xa9)
        return tokens
    return setup


def cases(random_source):
    yield from field_cases(random_source)
    for populated in (False, True):
        for choice in range(4):
            yield Case('reverse registry populated%d choice%d' % (populated, choice),
                REVERSE_NAME, reverse_setup(random_source.getrandbits(32), choice, populated),
                receiver=lambda t: t['registry'],
                arguments=(lambda t: t['output'], lambda t: t['probe']))
    yield Case('reverse registry duplicate function IDs retain traversal order',
        REVERSE_NAME, reverse_setup(random_source.getrandbits(32), 1, duplicate=True),
        receiver=lambda t: t['registry'],
        arguments=(lambda t: t['output'], lambda t: t['probe']))
    yield Case('reverse registry skips association with null configuration',
        REVERSE_NAME, reverse_setup(random_source.getrandbits(32), 3, null_value=True),
        receiver=lambda t: t['registry'],
        arguments=(lambda t: t['output'], lambda t: t['probe']))
    for populated in (False, True):
        for choice in range(4):
            yield Case('reverse physical local observations populated%d choice%d' % (populated, choice),
                REVERSE_NAME, reverse_setup(random_source.getrandbits(32), choice, populated, observe=True, custom_empty=True),
                receiver=lambda t: t['registry'],
                arguments=(lambda t: t['output'], lambda t: t['probe']),
                initial_stack=((-32, bytes(random_source.randrange(1, 256) for _ in range(32))),))
    for length in (0, 1, 2, 3, 4, 7, 126, 127):
        yield field_case('write scratch adjacent return word name%d' % length,
            RAW_WRITE, random_source.getrandbits(32), text=b'Q' * length, observe=True)
    for missing in (1, 2, 3):
        yield field_case('read clears previously nonzero lookup output missing%d' % missing,
            RAW_READ, random_source.getrandbits(32), positive=True, binding_mask=7,
            missing=missing, scratch_seed=True)
