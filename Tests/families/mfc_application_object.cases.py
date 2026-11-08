"""Blind full-source constructor cases; physical service policy lives in owned memory."""
import ctypes
from clawparity.cases import Case
from clawparity.env import NativeSourceContext, Halt
from clawparity.fixtures import returns

ROOT = 0x50257f
PC = 0x4251ff


def setup_case(rng, name, alignment=0, static=False, malloc_fail=False,
               cursor=True, stop=0, failure=0, nth=1, profile=0, warm=False, growth=0, alias=None, rescan=False):
    pattern = rng.randbytes(0xc0 + 4)
    stack = rng.randbytes(0x20000)
    registers = [rng.getrandbits(32) for _ in range(7)]
    point = ((0x80000000, 0x7fffffff) if profile % 5 == 0 else
             (0xffffffff, 0) if profile % 5 == 1 else
             (rng.getrandbits(32), rng.getrandbits(32)))
    tid = (0x12345 + profile * 0x91) & 0xffffffff
    handle = 0xffffffff if profile % 2 == 0 else 0xa5c01234 ^ profile

    def setup(env):
        receiver = 0x537008 if static else env.object(len(pattern), 'receiver backing', data=pattern) + alignment
        source_name = 0x524eec if static else (env.object(len(name) + 1, 'bounded name', data=name + b'\0') if name is not None else 0)
        if alias is not None:
            source_name = receiver + alias
            env.write(source_name, b'initial name\0')
        service = env.object(0x8000, 'physical service identities', fill=0)
        log = env.object(0x18000, 'physical CPU and publication observations', fill=0)
        # Tables are independent OS storage, never fabricated MFC or CRT records.
        env.put(service, 7)
        env.write(0x1ff0000, stack)
        frame = 0x2008000 - (profile % 7) * 0x180
        fs = 0xffffffff
        if profile % 3:
            fs = frame + 0x300
            env.put(fs, 0xffffffff, 0x5086f4)
        source = NativeSourceContext(size=ctypes.sizeof(NativeSourceContext), version=1,
            inputMask=0x7ff, outputMask=0x7ff, preserveMask=0x472,
            eax=registers[0], ebx=registers[1], ecx=receiver, edx=registers[2],
            esi=registers[3], edi=registers[4], ebp=registers[5], esp=frame,
            eip=ROOT, eflags=(registers[6] & 0x8d5) | 2, fsHead=fs)

        def observed(effect):
            def physical(e, call):
                count = e.get(log)
                base = log + 4 + count * 0x180
                e.put(log, count + 1)
                e.put(base, call.function, call.receiver, call.source_return_pc,
                      len(call.arguments), *call.arguments)
                if call.source_context is not None:
                    e.write(base + 0x24, bytes(call.source_context))
                e.write(base + 0x70, e.read(receiver, 0xc0))
                e.put(base + 0x130, e.get(0x53eca0), e.get(0x540af0))
                if call.function == stop:
                    raise Halt()
                if call.function == failure and e.calls_so_far(call.function) == nth:
                    return 0xffffffff if failure == 0x546a90 else 0
                return effect(e, call)
            return physical

        def tls_alloc(e, c):
            index = e.get(service)
            e.put(service, index + 1)
            return index
        def tls_get(e, c):
            return e.get(service + 0x100 + c.arguments[0] * 4)
        def tls_set(e, c):
            e.put(service + 0x100 + c.arguments[0] * 4, c.arguments[1])
            return 1
        def initialize(e, c):
            e.put(c.arguments[0], 0, 0xffffffff, 0, 0, 0, 0)
            return 0
        def enter(e, c):
            address = c.arguments[0]
            e.put(address + 4, (e.get(address + 4) + 1) & 0xffffffff,
                  e.get(address + 8) + 1, tid)
            return 0
        def leave(e, c):
            address = c.arguments[0]
            depth = e.get(address + 8) - 1
            e.put(address + 4, (e.get(address + 4) - 1) & 0xffffffff, depth, tid if depth else 0)
            return 0
        def local_alloc(e, c):
            return e.object(c.arguments[1], 'physical local block', fill=0 if c.arguments[0] & 0x40 else 0xa7)
        def local_resize(e, c):
            old, size, flags = c.arguments
            new = e.object(size, 'physical resized local block', fill=0xa7)
            e.write(new, e.read(old, min(e.spans[old], size)))
            e.release(old)
            return new
        def global_alloc(e, c):
            data = e.object(c.arguments[1], 'physical movable data', fill=0)
            token = e.object(12, 'physical global handle', words=[data, c.arguments[1], 0])
            n = e.get(service + 4)
            e.put(service + 4, n + 1)
            e.put(service + 0x400 + n * 8, data, token)
            return token
        def global_handle(e, c):
            for i in range(e.get(service + 4)):
                slot = service + 0x400 + i * 8
                if e.get(slot) == c.arguments[0]:
                    return e.get(slot + 4)
            return 0
        def global_lock(e, c):
            if not c.arguments[0]:
                return 0
            token = c.arguments[0]
            e.put(token + 8, e.get(token + 8) + 1)
            return e.get(token)
        def global_unlock(e, c):
            token = c.arguments[0]
            if not token:
                return 0
            depth = max(0, e.get(token + 8) - 1)
            e.put(token + 8, depth)
            return int(depth != 0)
        def global_resize(e, c):
            token, size, flags = c.arguments
            old = e.get(token)
            new = e.object(size, 'physical relocated global data', fill=0)
            e.write(new, e.read(old, min(e.get(token + 4), size)))
            e.release(old)
            e.put(token, new, size, 0)
            for i in range(e.get(service + 4)):
                slot = service + 0x400 + i * 8
                if e.get(slot + 4) == token:
                    e.put(slot, new)
            return token
        def cursor_pos(e, c):
            if cursor:
                e.put(c.arguments[0], *point)
            return int(cursor)
        def malloc(e, c):
            if rescan:
                e.write(source_name, b'Q\0')
            return 0 if malloc_fail else e.object(c.arguments[0], 'exact strdup allocation', fill=0x93)
        def throwing(e, c):
            raise Halt()
        def readable(e, c):
            address, size = c.arguments
            if size == 0:
                return 0
            if address + size > 0x100000000:
                return 1
            valid = (e.program.base <= address and address + size <= e.program.base + e.program.size or
                     0x1ff0000 <= address and address + size <= 0x2010000 or
                     any(a <= address and address + size <= a+n for a,n in e.spans.items()))
            return int(not valid)
        def writable(e, c):
            address, size = c.arguments
            if e.program.base <= address < e.program.data_start:
                return int(size != 0)
            return readable(e, c)
        def executable(e, c):
            return int(not e.program.in_text(c.arguments[0]))
        services = {0x546a90: tls_alloc, 0x546a7c: tls_get, 0x546a84: tls_set,
            0x546aa4: initialize, 0x546aac: enter, 0x546a9c: leave,
            0x546b1c: global_alloc, 0x546a8c: global_handle,
            0x5469c8: global_unlock, 0x546a88: global_resize, 0x5469c4: global_lock,
            0x546aa8: local_alloc, 0x546a80: local_resize,
            0x546958: throwing, 0x546abc: returns(0x00000a04),
            0x546cd0: cursor_pos, 0x4a48e0: malloc,
            0x546b0c: lambda e,c: e.get(service + 8),
            0x546ab8: lambda e,c: (e.put(service + 8, c.arguments[0]) or 0),
            0x546a40: readable, 0x546984: writable, 0x546988: executable,
            0x5469bc: returns(handle), 0x5469c0: returns(tid)}
        for address, effect in services.items():
            env.override(address, observed(effect))
        if warm:
            # Execute the unchanged original constructor to obtain all cached MFC
            # owners; carry its physical heap/image ownership into the case.
            env._freeze()
            warm_source = NativeSourceContext.from_buffer_copy(source)
            result = env.run_original_context(ROOT, warm_source,
                source_return_pc=PC, source_convention='thiscall',
                receiver=receiver, arguments=(source_name,), check_objects=True)
            if result.errors or not result.completed:
                raise RuntimeError('original warming failed: ' + str(result.errors))
            env.backend, env.side = 'initial', 'setup'
            env._initial['heap'][:] = result.heap
            env._initial['image'][env.data_offset:] = result.image
            env.write(0x1ff0000, stack)
            if fs != 0xffffffff:
                env.put(fs, 0xffffffff, 0x5086f4)
            for slot_number in range(growth):
                slot = env.object(4, 'distinct genuine application TLS slot', fill=0)
                env._freeze()
                extra = NativeSourceContext.from_buffer_copy(source)
                extra.ecx, extra.eip, extra.preserveMask = slot, 0x50335e, 0x400
                expanded = env.run_original_context(0x50335e, extra,
                    source_return_pc=0x5025cf, source_convention='thiscall',
                    receiver=slot, arguments=(0x502301,), check_objects=True)
                if expanded.errors or not expanded.completed:
                    raise RuntimeError('original manager growth failed: ' + str(expanded.errors))
                env.backend, env.side = 'initial', 'setup'
                env._initial['heap'][:] = expanded.heap
                env._initial['image'][env.data_offset:] = expanded.image
            env.write(0x1ff0000, stack)
            if fs != 0xffffffff:
                env.put(fs, 0xffffffff, 0x5086f4)
            env.put(log, 0)
            if not static:
                receiver = env.object(len(pattern), 'new warm receiver', data=pattern) + alignment
                source.ecx = receiver
            # Existing root publications are nonzero witnesses for warm overwrite.
        return {'receiver': receiver, 'name': source_name, 'source': source}
    return setup


def cases(random_source):
    profiles = [(b'Claw', 0, True, False, True)]
    profiles += [(name, i % 4, False, failed, i % 3 != 0)
                 for i, name in enumerate([None, b''] + [bytes((0x81+j*17) % 255 + 1 for j in range(n)) for n in range(1, 10)] + [random_source.randbytes(63).replace(b'\0', b'X'), b'Claw'])
                 for failed in (False, True)]
    for i, (name, alignment, static, failed, cursor) in enumerate(profiles):
        yield Case(f'cold original profile {i}', ROOT,
            setup_case(random_source, name, alignment, static, failed, cursor, profile=i),
            receiver=lambda t: t['receiver'], arguments=(lambda t: t['name'],),
            source_context=lambda t: t['source'], source_return_pc=PC)
    for address in (0x546cd0, 0x546a90, 0x546aa4, 0x546b1c, 0x546aa8, 0x5469bc, 0x5469c0):
        yield Case(f'physical stop {address:x}', ROOT,
            setup_case(random_source, b'Claw', stop=address),
            receiver=lambda t: t['receiver'], arguments=(lambda t: t['name'],),
            source_context=lambda t: t['source'], source_return_pc=PC, expect='halt')

    for i in range(12):
        yield Case(f'warmed by original constructor {i}', ROOT,
            setup_case(random_source, b'Warm' + bytes([65+i]), alignment=i % 4,
                       cursor=i % 2 == 0, profile=i, warm=True, growth=33 if i == 0 else 0),
            receiver=lambda t: t['receiver'], arguments=(lambda t: t['name'],),
            source_context=lambda t: t['source'], source_return_pc=PC)
    for address, count in ((0x546a90, 1), (0x546b1c, 1),
                           (0x546aa8, 1), (0x546aa8, 2),
                           (0x546aa8, 3), (0x546aa8, 4),
                           (0x546a80, 1)):
        yield Case(f'physical allocation failure {address:x} occurrence {count}', ROOT,
            setup_case(random_source, b'Failure', failure=address, nth=count),
            receiver=lambda t: t['receiver'], arguments=(lambda t: t['name'],),
            source_context=lambda t: t['source'], source_return_pc=PC, expect='halt')

    for offset in (0, 0x38):
        yield Case(f'receiver name alias {offset:x}', ROOT,
            setup_case(random_source, b'Alias', alignment=1, alias=offset),
            receiver=lambda t: t['receiver'], arguments=(lambda t: t['name'],),
            source_context=lambda t: t['source'], source_return_pc=PC)
    yield Case('malloc changes bounded name before original rescan', ROOT,
        setup_case(random_source, b'long original bounded name', rescan=True),
        receiver=lambda t: t['receiver'], arguments=(lambda t: t['name'],),
        source_context=lambda t: t['source'], source_return_pc=PC)
