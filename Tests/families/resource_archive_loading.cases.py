"""Original archive records and physical file-service outcomes."""
import struct

from clawparity.cases import Case
from clawparity.fixtures import allocate, returns, sequence

NEW = 0x4F63EC
OPEN = 0x4F1D90
SEEK = 0x4A7840
READ = 0x4A7260
WRITE = 0x4A73E0
CLOSE = 0x4A7AE0
FLUSH = 0x4A7920
TIME = 0x4A3B10


def words(*values):
    return struct.pack('<' + 'I' * len(values), *values)


def directory_record(name=b'child', offset=777, size=0, stamp=0x12345678):
    return words(1, offset, size, stamp) + name + b'\0'


def resource_record(name=b'item', metadata=b'', offset=900, length=13, tag=0x53505249, aux=()):
    return words(0, offset, length, 0xABCDEF12, 0x76543210, tag, len(aux)) + name + b'\0' + metadata + b'\0' + words(*aux)


def controller(env, fill=0):
    target = env.object(72, 'controller', fill=fill)
    env.put(target + 4, 1, 0, 0x11002200)
    env.put(target + 32, 1)
    trace = env.object(512, 'service-observations')
    methods = env.object(12, 'retry-vtable')
    env.put(target, methods)
    env.put(methods + 8, env.stub('retry', 'thiscall', 0, returns(0)))
    env.override(OPEN, returns(0x11002200))
    env.override(SEEK, returns(0))
    env.override(CLOSE, returns(0))
    env.override(FLUSH, returns(0))
    env.override(WRITE, lambda env, call: call.arguments[2])

    def clock(env, call):
        env.put(call.arguments[0], 0x634512AB)
        return 0x634512AB

    env.override(TIME, clock)
    return {'target': target, 'trace': trace, 'methods': methods}


def directory(env, owner):
    target = env.object(76, 'directory', fill=0)
    env.put(target + 24, owner)
    env.put(target + 36, 0x513574)
    env.put(target + 56, target)
    for offset, count in ((60, 5), (68, 9)):
        buckets = env.object(4 + 16 * count, 'directory-buckets', fill=0)
        env.put(buckets, count)
        env.put(target + offset, count, buckets + 4)
    return target


def archive_setup(payload=b'', short=False, fail=False):
    def setup(env):
        tokens = controller(env)
        tokens['target'] = directory(env, tokens['target'])
        def read(env, call):
            amount = min(len(payload), call.arguments[2])
            env.write(call.arguments[0], payload[:amount])
            return amount if short else call.arguments[2]
        env.override(READ, read)
        if fail:
            env.override(NEW, allocate(fail=True))
        return tokens
    return setup


def entry(label, address, setup, args=(), **kw):
    return Case(label, address, setup, receiver=lambda t: t['target'], arguments=args, **kw)


def cases(random_source):
    yield entry('constructor preserves distinct untouched fields', 0x4B7210,
                lambda env: controller(env, fill=0xB7))
    yield entry('recursive zero size leaves directory unchanged', 0x4B6B60,
                archive_setup(), (0x1234, 0))
    yield entry('directory allocation fails after resetting summary', 0x4B6ED0,
                archive_setup(fail=True), (0x2468, 32))
    yield entry('recursive allocation failure propagates', 0x4B6B60,
                archive_setup(fail=True), (0x1357, 32))
    yield entry('directory short physical read fails and frees', 0x4B6ED0,
                archive_setup(b'bad', short=True), (0x2345, 19))
    yield entry('empty directory direct', 0x4B6ED0, archive_setup(), (0x9876, 0))
    payloads = [directory_record(), resource_record(),
                resource_record(b'a', b'metadata', 0x80000001, aux=(0xABCDEF01, 0x10293847)),
                resource_record(b'zero', offset=0, length=0),
                resource_record(b'first', offset=100) + resource_record(b'second', offset=90) + resource_record(b'third', offset=200),
                directory_record(b'first-child') + directory_record(b'next-child', 888),
                resource_record(b'same-tag') + resource_record(b'tag-reused', offset=10)]
    payloads.append(words(0x80000002) + resource_record(b'non-one-kind')[4:])
    for index in range(8):
        payloads.append(resource_record(bytes([65+index]) * (index+1), b'meta' if index & 1 else b'',
                                       random_source.getrandbits(32), random_source.getrandbits(32),
                                       random_source.getrandbits(32), tuple(random_source.getrandbits(32) for _ in range(index % 4))))
    for index, payload in enumerate(payloads):
        yield entry(f'parse original records {index}', 0x4B6ED0, archive_setup(payload), (0x321, len(payload)))
    for failing_child in (False, True):
        payload = directory_record(b'child-a', 777, 4 if failing_child else 0) + directory_record(b'child-b', 888)
        def setup(env, payload=payload):
            tokens = archive_setup(payload)(env)
            def read(env, call):
                index = env.calls_so_far(READ)
                if index == 1:
                    env.write(call.arguments[0], payload)
                    return len(payload)
                return 0
            env.override(READ, read)
            return tokens
        yield entry(f'recursive siblings continue after child failure {failing_child}', 0x4B6B60, setup, (123, len(payload)))

    for readonly, create in ((0, 0), (7, 0), (0, 1), (1, 1)):
        for outcome in ('success', 'abort', 'retry', 'publish'):
            def setup(env, outcome=outcome):
                tokens = controller(env)
                tokens['path'] = env.object(17, 'path', data=b'archive-name.rez\0')
                target, trace = tokens['target'], tokens['trace']
                env.override(OPEN, sequence(0, 0x11224488) if outcome == 'retry' else returns(0x55113377 if outcome == 'success' else 0))
                def retry(env, call):
                    env.put(trace, call.receiver, env.get(target + 12), env.get(target + 32))
                    if outcome == 'publish':
                        env.put(target + 12, 0x88776655)
                    return int(outcome in ('retry', 'publish') and env.calls_so_far(call.function) == 1)
                env.put(tokens['methods'] + 8, env.stub('retry', 'thiscall', 0, retry))
                return tokens
            yield entry(f'fopen mode {readonly}/{create} {outcome}', 0x4B7BD0, setup,
                        (lambda t: t['path'], readonly, create))

    for address, service in ((0x4B7C40, CLOSE), (0x4B7C80, FLUSH)):
        for scenario in ('null', 'success', 'failure', 'retry-success', 'retry-twice', 'retry-clears-file'):
            def setup(env, scenario=scenario, service=service):
                tokens = controller(env)
                target, trace = tokens['target'], tokens['trace']
                if scenario == 'null':
                    env.put(target + 12, 0)
                values = (0,) if scenario in ('null', 'success') else ((7, 9, 0) if scenario == 'retry-twice' else (0xFFFFFFFF, 0))
                env.override(service, sequence(*values))
                def retry(env, call):
                    n = env.calls_so_far(call.function)
                    env.put(trace + n * 16, call.receiver, env.get(target + 12), env.get(target + 32))
                    env.put(target + 12, 0 if scenario == 'retry-clears-file' else 0x44556600 + n)
                    return int(scenario != 'failure' and n <= (2 if scenario == 'retry-twice' else 1))
                env.put(tokens['methods'] + 8, env.stub('retry', 'thiscall', 0, retry))
                return tokens
            yield entry(f'{service:x} {scenario}', address, setup)

    for create, failure in ((1, False), (1, True), (0, False), (0, True)):
        for path in (b'x', b'four', b'long-archive-name.rez'):
            def setup(env, create=create, failure=failure, path=path):
                tokens = controller(env)
                tokens['path'] = env.object(len(path)+1, 'path', data=path+b'\0')
                if failure:
                    def alloc(env, call):
                        return 0 if call.arguments[0] == 76 else env.object(call.arguments[0], 'allocation')
                    env.override(NEW, alloc)
                header = bytearray(bytes(random_source.randrange(256) for _ in range(168)))
                for offset, value in ((131, 0x220), (135, 0), (139, 0x12345678)):
                    struct.pack_into('<I', header, offset, value)
                env.override(READ, lambda env, call: (env.write(call.arguments[0], bytes(header)), call.arguments[2])[1])
                return tokens
            yield entry(f'open archive create={create} root-failure={failure} path={path!r}', 0x4B72E0, setup,
                        (lambda t: t['path'], 0, create))
    def open_fail(env):
        tokens = controller(env)
        tokens['path'] = env.object(8, 'path', data=b'bad.rez\0')
        env.override(OPEN, returns(0))
        return tokens
    yield entry('open failure retains copied path', 0x4B72E0, open_fail, (lambda t: t['path'], 1, 0))

    header_residue = bytearray(random_source.getrandbits(8) for _ in range(168))
    struct.pack_into('<I', header_residue, 131, 0xAABBCCDD)
    struct.pack_into('<I', header_residue, 135, 0)
    def short_header(env):
        tokens = controller(env)
        tokens['path'] = env.object(9, 'path', data=b'tail.rez\0')
        def read(env, call):
            env.write(call.arguments[0], b'H' * 127)
            return 127
        env.override(READ, read)
        return tokens
    yield entry('short header read preserves original initialized local tail', 0x4B72E0, short_header,
                (lambda t: t['path'], 1, 0), initial_stack=((-184, bytes(header_residue)),))

    payload = resource_record(b'root-resource', b'proof', offset=0x88002211, aux=(9, 8, 7))
    def populated_header(env):
        tokens = controller(env)
        tokens['path'] = env.object(9, 'path', data=b'full.rez\0')
        header = bytearray(168)
        struct.pack_into('<I', header, 131, 0x12345678)
        struct.pack_into('<I', header, 135, len(payload))
        struct.pack_into('<I', header, 139, 0x50607080)
        def read(env, call):
            data = bytes(header) if env.calls_so_far(READ) == 1 else payload
            env.write(call.arguments[0], data)
            return len(data)
        env.override(READ, read)
        return tokens
    yield entry('existing archive recursively parses genuine root records', 0x4B72E0, populated_header,
                (lambda t: t['path'], 1, 0))

    def recursive_failure_ignored(env):
        tokens = populated_header(env)
        def alloc(env, call):
            return 0 if env.calls_so_far(NEW) == 6 else env.object(call.arguments[0], 'allocation')
        env.override(NEW, alloc)
        return tokens
    yield entry('existing archive publishes open despite recursive allocation failure', 0x4B72E0,
                recursive_failure_ignored, (lambda t: t['path'], 1, 0))

    payload = directory_record(b'reload-owner')
    def changed_owner(env):
        tokens = archive_setup(payload)(env)
        other = controller(env)['target']
        target = tokens['target']
        def alloc(env, call):
            if env.calls_so_far(NEW) == 2:
                env.put(target + 24, other)
            return env.object(call.arguments[0], 'allocation')
        env.override(NEW, alloc)
        return tokens
    yield entry('directory owner reloaded after allocation service', 0x4B6ED0,
                changed_owner, (0x777, len(payload)))

    def close_publishes_cleanup(env):
        tokens = controller(env)
        target = tokens['target']
        root = directory(env, target)
        path = env.object(14, 'new-owned-path', data=b'published.rez\0')
        def close(env, call):
            env.put(tokens['trace'], env.get(target + 8), env.get(target + 36), env.get(target + 68))
            env.put(target + 36, root)
            env.put(target + 68, path)
            return 0
        env.override(CLOSE, close)
        return tokens
    yield entry('close rereads resources published by physical service', 0x4B74D0,
                close_publishes_cleanup, (0,))

    def failed_close(env):
        tokens = controller(env)
        env.put(tokens['target'] + 8, 1)
        env.put(tokens['target'] + 68, env.object(8, 'owned-path', data=b'bad.rez\0'))
        env.override(CLOSE, returns(0xFFFFFFFF))
        return tokens
    yield entry('cleanup frees path and clears open despite close failure', 0x4B74D0, failed_close, (0,))

    for address in (0x4B7250, 0x4B74D0):
        for opened, root, path, writable, compact in ((0,False,False,False,0), (1,False,False,False,0),
                                                   (0,True,True,False,0), (1,True,True,True,0),
                                                   (1,True,True,False,1)):
            def setup(env, opened=opened, root=root, path=path, writable=writable):
                tokens = controller(env)
                target = tokens['target']
                env.put(target + 8, opened)
                env.put(target + 32, 0 if writable else 1)
                if root:
                    env.put(target + 36, directory(env, target))
                if path:
                    env.put(target + 68, env.object(8, 'owned-path', data=b'ab.rez\0'))
                return tokens
            yield entry(f'cleanup {address:x} open={opened} root={root} path={path} write={writable} compact={compact}',
                        address, setup, (compact,) if address == 0x4B74D0 else ())
