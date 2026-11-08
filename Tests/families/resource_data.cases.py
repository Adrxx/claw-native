"""Original-backed resource lifetime and stream cases, including CRT FILE state."""
from clawparity.cases import Case

NEW, DELETE = 0x4F63EC, 0x4F6428
SEEK, READ, ERROR, TLS = 0x546AF4, 0x546AFC, 0x546B0C, 0x546A7C


def resource(env):
    return env.object(0x60, 'resource', data=bytes((i * 37 + 19) & 255 for i in range(0x60)))


def recorder(env):
    log = env.object(4096, 'observable callback history', fill=0)
    def record(env, call, tag, target=0):
        n = env.get(log)
        env.put(log, n + 1)
        at = log + 4 + n * 128
        env.put(at, tag, call.receiver, len(call.arguments), *call.arguments)
        if target:
            env.write(at + 32, env.read(target, 0x60))
    return record


def constructor(primary, secondary, count, words, fail=0, mutate=False):
    def setup(env):
        obj = resource(env)
        owner = env.object(0x24, 'owner', fill=0)
        typ = env.object(4, 'type', words=[0xD83A109F])
        def string(s, name):
            return 0 if s is None else env.object(len(s) + 2, name, data=b'!' + s + b'\0') + 1
        p, s = string(primary, 'primary source'), string(secondary, 'secondary source')
        arr = 0 if words is None else env.object(max(4, len(words) * 4), 'word source', words=words)
        log = recorder(env)
        def allocation(env, call):
            n = env.calls_so_far(NEW)
            log(env, call, n, obj)
            if mutate:
                if n == 1 and p:
                    env.write(p, b'Q\0')
                if n == 2 and s:
                    env.write(s, b'Z\0')
            if n == fail or call.arguments[0] > 4096:
                return 0
            return env.object(max(1, call.arguments[0]), 'allocation', fill=0xCD)
        env.override(NEW, allocation)
        return dict(obj=obj, args=(owner, p, 0x8ABC0123, typ, s, 0x37, 0xFEDC4321, 0x76540219, count, arr))
    return setup


def destructor(owner_kind, present, mutate=False):
    def setup(env):
        obj = resource(env)
        owner = env.object(0x24, 'owner', fill=0)
        env.put(owner + 0x20, 0x12345678 if owner_kind == 'mapped' else 0)
        ptrs = [env.object(24, 'owned block ' + str(i), fill=0x30 + i) if present else 0 for i in range(4)]
        env.put(obj, ptrs[0])
        env.put(obj + 0xC, ptrs[1])
        env.put(obj + 0x18, ptrs[2])
        env.put(obj + 0x20, ptrs[3])
        env.put(obj + 0x24, 0 if owner_kind == 'null' else owner)
        replacements = [env.object(24, 'replacement ' + str(i), fill=0x90 + i) for i in range(3)] if mutate else []
        log = recorder(env)
        def release(env, call):
            log(env, call, env.calls_so_far(DELETE), obj)
            env.release(call.arguments[0])
            if mutate:
                n = env.calls_so_far(DELETE)
                if n == 1:
                    env.put(obj + 0xC, replacements[0])
                    env.put(obj + 0x24, 0)
                elif n == 2:
                    env.put(obj + 0x18, replacements[1])
                elif n == 3:
                    env.put(obj + 0x20, replacements[2])
            return 0
        env.override(DELETE, release)
        return dict(obj=obj)
    return setup


def stream_setup(env, count, seek_results=(), read_results=(), retry_results=(), switch=False, resource_obj=0, mutation=None, os_error=0):
    """Only Win32 imports are scripted: fseek/fread and their CRT callees run intact."""
    stream = env.object(0x10, 'stream', fill=0)
    files = []
    table = env.object(0x48, 'initialized descriptors', fill=0)
    for i in range(2):
        buf = env.object(max(8, count), 'FILE buffer ' + str(i), fill=0xAC)
        f = env.object(0x38, 'FILE ' + str(i), fill=0)
        env.put(f, buf, 0, buf, 0x105, i, 0, 1)
        env.put(table + i * 0x24, 0x1234 + i)
        env.write(table + i * 0x24 + 4, b'\x01')
        env.put(table + i * 0x24 + 8, 1)
        files.append(f)
    env.put(0x545EC0, table)
    env.put(0x545FC0, 2)
    tls = env.object(0x74, 'existing CRT TLS', fill=0)
    env.override(TLS, lambda e, c: tls)
    env.override(ERROR, lambda e, c: os_error)
    destination = env.object(max(1, count) + 16, 'destination with tail guards', fill=0xE7)
    log = recorder(env)
    def seek(env, call):
        n = env.calls_so_far(SEEK)
        log(env, call, 0x100 + n, resource_obj)
        return seek_results[n - 1] if n <= len(seek_results) else call.arguments[1]
    def read(env, call):
        n = env.calls_so_far(READ)
        log(env, call, 0x200 + n, resource_obj)
        amount = read_results[n - 1] if n <= len(read_results) else call.arguments[2]
        amount = min(amount, call.arguments[2])
        env.write(call.arguments[1], bytes(((n * 41 + i * 23 + call.arguments[0]) & 255) for i in range(amount)))
        env.put(call.arguments[3], amount)
        if mutation:
            mutation(env, resource_obj, n)
        return 1
    def retry(tag):
        def effect(env, call):
            n = env.get(history)
            env.put(history, n + 1)
            log(env, call, tag + n, resource_obj)
            if switch:
                env.put(stream + 0xC, files[(n + 1) % 2])
                env.put(stream, vtables[(n + 1) % 2])
            else:
                # Real CRT sets EOF on short reads; user retry clears it.
                f = env.get(stream + 0xC)
                env.put(f + 0xC, 0x105)
            return retry_results[n] if n < len(retry_results) else 0
        return effect
    history = env.object(4, 'retry count', fill=0)
    vtables = [env.object(12, 'retry vtable ' + str(i), fill=0) for i in range(2)]
    for i in range(2):
        env.put(vtables[i] + 8, env.stub('retry ' + str(i), 'thiscall', 0, retry(0x300 + i * 0x100)))
    env.put(stream, vtables[0])
    env.put(stream + 0xC, files[0])
    env.override(SEEK, seek)
    env.override(READ, read)
    return dict(stream=stream, destination=destination, files=files)


def byte_setup(size, mode='read', seek_results=(), read_results=(), retry_results=(), mutation=None):
    def setup(env):
        obj = resource(env)
        owner = env.object(0x24, 'owner', fill=0)
        env.put(obj + 0x24, owner)
        env.put(obj + 0x14, size)
        env.put(obj + 0x18, 0)
        env.put(obj + 0x28, 0x987)
        if mode == 'mapped':
            env.put(owner + 0xC, 0xFFFFFE23)
            env.put(owner + 0x20, size)
            env.put(obj + 0x18, 0xBADCAFE)
        elif mode == 'cached':
            env.put(obj + 0x18, env.object(17, 'cache', fill=0xA1))
        else:
            st = stream_setup(env, max(1, size), seek_results, read_results, retry_results, resource_obj=obj,
                              mutation=mutation if mode == 'read-mutation' else None)
            env.put(owner + 0x18, st['stream'])
            alternate_owner = env.object(0x24, 'replacement owner', fill=0)
            if mode == 'alloc-mutation':
                replacement_stream = stream_setup(env, max(1, size), resource_obj=obj)
                env.put(alternate_owner + 0x18, replacement_stream['stream'])
            else:
                env.put(alternate_owner + 0x18, st['stream'])
            log = recorder(env)
            def alloc(env, call):
                log(env, call, 0x700, obj)
                if mode == 'fail':
                    return 0
                if mode == 'alloc-mutation':
                    env.put(obj + 0x24, alternate_owner)
                    env.put(obj + 0x14, max(1, size - 2))
                    env.put(obj + 0x28, 0xF1234567)
                return env.object(call.arguments[0], 'allocated bytes', fill=0xD3)
            env.override(NEW, alloc)
        return dict(obj=obj)
    return setup


def cases(random_source):
    for a, b in ((None, None), (b'', b''), (b'a', b'XY'), (b'abc', b'defg'), (b'abcdef', b'0123456789')):
        for count in (0, 1, 5):
            words = [random_source.getrandbits(32) for _ in range(max(1, count))]
            yield Case(f'construct names {a!r}/{b!r} words {count}', 0x4B5FF0, constructor(a, b, count, words), receiver=lambda t:t['obj'], arguments=tuple((lambda t,i=i:t['args'][i]) for i in range(10)))
    for label, setup in [('null array', constructor(b'one', b'two', 9, None)), ('rescan names', constructor(b'first-name', b'second-name', 3, [7, 0xABC, 0xFEDCBA98], mutate=True))] + [(f'allocation {i} fails', constructor(b'first', b'second', 3, [9,8,7], fail=i)) for i in (1,2,3)] + [(f'wrapped array {n:#x}', constructor(None, None, n, [0xDEAD], fail=1)) for n in (0xFFFFFFFF, 0x40000000, 0x80000001)]:
        yield Case('construct ' + label, 0x4B5FF0, setup, receiver=lambda t:t['obj'], arguments=tuple((lambda t,i=i:t['args'][i]) for i in range(10)))
    def array_destination_reload(env):
        t = constructor(None, None, 3, [0, 0xC3D2E1F0, 0x91827364])(env)
        alternate = env.object(20, 'redirected array', fill=0x6D)
        env.put(t['args'][9], alternate, 0xC3D2E1F0, 0x91827364)
        log = recorder(env)
        def allocate_alias(env, call):
            log(env, call, 0xA01, t['obj'])
            return t['obj'] + 0x20
        env.override(NEW, allocate_alias)
        return t
    yield Case('construct array destination reread every word', 0x4B5FF0, array_destination_reload, receiver=lambda t:t['obj'], arguments=tuple((lambda t,i=i:t['args'][i]) for i in range(10)))
    for owner in ('null', 'unmapped', 'mapped'):

        for present in (False, True):
            yield Case(f'destroy {owner} present {present}', 0x4B6120, destructor(owner, present), receiver=lambda t:t['obj'])
    yield Case('destroy rereads fields after each delete', 0x4B6120, destructor('mapped', True, True), receiver=lambda t:t['obj'])
    for value in (0, 1, 0xFFFFFFFF, random_source.getrandbits(32)):
        def typed(env, value=value):
            p = env.object(12, 'type cell', words=[value, value ^ 0xFFFFFFFF, 0x11223344])
            obj = resource(env)
            env.put(obj + 8, p)
            return dict(obj=obj)
        yield Case(f'type word {value:#x}', 0x4B61B0, typed, receiver=lambda t:t['obj'])
    for size, mode in ((0,'read'), (1,'cached'), (0,'cached'), (1,'fail'), (17,'fail'), (0xFFFFFFF0,'mapped'), (0x12345678,'mapped'), (1,'read'), (9,'read'), (13,'alloc-mutation')):
        yield Case(f'bytes size {size} {mode}', 0x4B61C0, byte_setup(size, mode), receiver=lambda t:t['obj'])
    yield Case('bytes failed read frees cache', 0x4B61C0, byte_setup(7, read_results=(0,)), receiver=lambda t:t['obj'])
    yield Case('bytes seek fails and abandons', 0x4B61C0, byte_setup(7, seek_results=(0xFFFFFFFF,)), receiver=lambda t:t['obj'])
    def change_size(env, obj, n):
        if n == 1:
            env.put(obj + 0x14, 3)
    yield Case('bytes rereads size after read', 0x4B61C0, byte_setup(7, 'read-mutation', mutation=change_size), receiver=lambda t:t['obj'])
    def change_cache(env, obj, n):
        if n == 1:
            env.put(obj + 0x18, env.object(19, 'published replacement cache', fill=0x5D))
    yield Case('bytes returns cache republished during read', 0x4B61C0, byte_setup(7, 'read-mutation', mutation=change_cache), receiver=lambda t:t['obj'])
    def cleanup_reloads(env):
        def replace_and_shrink(env, obj, n):
            if n == 1:
                env.put(obj + 0x18, env.object(23, 'replacement requiring cleanup', fill=0x4E))
                env.put(obj + 0x14, 2)
        t = byte_setup(7, 'read-mutation', mutation=replace_and_shrink)(env)
        replacement = env.object(21, 'delete callback republishes cache', fill=0x83)
        log = recorder(env)
        def release(env, call):
            log(env, call, 0xA02, t['obj'])
            env.release(call.arguments[0])
            env.put(t['obj'] + 0x18, replacement)
            return 0
        env.override(DELETE, release)
        return t
    yield Case('bytes rereads cleanup pointer and clears republished cache', 0x4B61C0, cleanup_reloads, receiver=lambda t:t['obj'])
    for present in (False, True):
        for mutate in (False, True):
            def release_setup(env, present=present, mutate=mutate):
                obj = resource(env)
                env.put(obj + 0x18, env.object(12,'cache',fill=0x71) if present else 0)
                replacement = env.object(12,'replacement cache',fill=0xA9)
                log = recorder(env)
                def release(env, call):
                    log(env, call, 0x900, obj)
                    env.release(call.arguments[0])
                    if mutate:
                        env.put(obj + 0x18, replacement)
                    return 0
                env.override(DELETE, release)
                return dict(obj=obj)
            yield Case(f'release bytes present {present} mutation {mutate}', 0x4B6230, release_setup, receiver=lambda t:t['obj'])
    scenarios = [
        ('zero',0,(),(),(),False,0), ('one',1,(),(),(),False,0),
        ('full',13,(),(),(),False,0), ('seek abandon',7,(0xFFFFFFFF,),(),(0,),False,0),
        ('seek retry abandon',7,(0xFFFFFFFF,0xFFFFFFFF),(),(1,0),False,0),
        ('seek repeated success',7,(0xFFFFFFFF,0xFFFFFFFF,17),(),(1,1),False,0),
        ('seek reload FILE and vtable',9,(0xFFFFFFFF,0xFFFFFFFF,4),(),(1,1),True,0),
        ('seek TLS error',7,(0xFFFFFFFF,12),(),(1,),False,5),
        ('read abandon',9,(),(0,),(0,),False,0),
        ('partial read abandon',9,(),(3,0),(0,),False,0),
        ('read retry success',9,(),(0,9),(1,),False,0),
        ('read retry repeated success',9,(),(0,0,9),(1,1),False,0),
        ('read retry then abandon',9,(),(0,0),(1,0),False,0),
        ('read reload FILE and vtable',9,(),(0,0,9),(1,1),True,0),
    ]
    scenarios += [(f'random {i}',random_source.randrange(2,45),(),(),(),False,0) for i in range(6)]
    for label,count,seeks,reads,retries,switch,error in scenarios:
        def setup(env, count=count,seeks=seeks,reads=reads,retries=retries,switch=switch,error=error):
            return stream_setup(env,count,seeks,reads,retries,switch,os_error=error)
        offset = random_source.getrandbits(32)
        yield Case('readAt ' + label, 0x4B7AB0, setup, receiver=lambda t:t['stream'], arguments=(offset,count,lambda t:t['destination']))
