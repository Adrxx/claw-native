"""Independent field-order and serializer cases for the v1.3 child roots."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, returns

DERIVED, BASE, WRITE, READ = 0x4df6f0, 0x4df240, 0x4dd9e0, 0x4ddc10
DOUBLES = tuple(range(0, 0x58, 8)) + tuple(range(0x70, 0xb8, 8)) + tuple(range(0xc0, 0x108, 8))


def setup_case(words, operation=0, length=13, backwards=False, mutate=False,
               failure=0, no_allocation=False):
    def setup(env):
        obj = env.object(0x150, 'child', words=words)
        owner = env.object(0x80, 'restored owner', words=list(reversed(words[:32])))
        stream = env.object(0x40, 'external stream')
        record = env.object(0x2000, 'callback observations')
        state = env.object(16, 'fixture counters', fill=0)
        payload = env.object(256, 'formatted bytes', data=bytes((i * 37 + 19) & 255 for i in range(256)))
        vb = env.object(8, 'virtual base table', words=[0, 0])
        buf = env.object(32, 'native stream buffer')
        env.put(buf + 24, payload + (1 if backwards else 0), payload + (0 if backwards else length))
        env.put(0x5acd54, words[2])

        def observe(env, call, tag):
            n = env.get(state)
            env.put(record + n * 24, tag, call.receiver, len(call.arguments), *(tuple(call.arguments) + (0, 0, 0))[:3])
            env.put(state, n + 1)

        def construct_output(env, call):
            observe(env, call, 1)
            env.put(call.receiver, vb, buf)
            return call.receiver

        def construct_input(env, call):
            observe(env, call, 2)
            return call.receiver

        def write_double(env, call):
            observe(env, call, 3)
            if mutate:
                n = env.calls_so_far(0x4f8db1)
                if n < len(DOUBLES):
                    env.put(obj + 0x38 + DOUBLES[n], words[n] ^ 0xa54ff53a, words[n + 1] ^ 0x510e527f)
            return failure or payload

        def read_double(env, call):
            observe(env, call, 4)
            n = env.calls_so_far(0x4f8f70)
            env.put(call.arguments[0], words[n % len(words)], words[(n + 17) % len(words)])
            return failure or payload

        def integer(env, call):
            observe(env, call, 5)
            if operation == 7:
                env.put(call.arguments[0], 0x80000000 ^ words[7])
            return failure or payload

        def bitset(env, call):
            observe(env, call, 6)
            if operation == 7:
                env.put(call.arguments[1] + 12, words[5])
            return failure or payload

        def destroy(env, call):
            observe(env, call, 7)
            return 0

        def read_bytes(env, call):
            observe(env, call, 8)
            n = env.get(state + 4)
            env.put(state + 4, n + 1)
            if not call.arguments[0]:
                return 0xffffffff
            # Each serialized section contains a length, bytes and four DWORDs.
            part = n % 6
            if part == 0:
                env.put(call.arguments[0], length)
            else:
                env.write(call.arguments[0], bytes((words[(n + j) % len(words)] & 255) for j in range(call.arguments[1])))
            if mutate:
                env.put(stream, tables[(n + 1) % 2])
            return failure

        def write_bytes(env, call):
            observe(env, call, 9)
            n = env.get(state + 4)
            env.put(state + 4, n + 1)
            if call.arguments[1]:
                data = env.read(call.arguments[0], call.arguments[1])
                env.write(record + 0x1800 + n * 64, data)
            if mutate:
                env.put(stream, tables[(n + 1) % 2])
                env.put(obj + 0x144, words[n] ^ 0xfedcba98)
                env.put(owner + 0x7c, words[n] ^ 0x3456789a)
            return failure

        tables = [env.object(0x34, 'stream methods one'), env.object(0x34, 'stream methods two')]
        for i, table in enumerate(tables):
            env.put(table + 44, env.stub('stream read %d' % i, 'thiscall', 2, read_bytes),
                    env.stub('stream write %d' % i, 'thiscall', 2, write_bytes))
        env.put(stream, tables[0])
        for address, effect in ((0x4f9463, construct_output), (0x4f9398, construct_input),
                                (0x4f8db1, write_double), (0x4f8f70, read_double),
                                (0x4f8d00, integer), (0x4f8ed3, integer),
                                (0x4fa4f0, bitset), (0x4fa5a0, bitset),
                                (0x4f9425, destroy), (0x4f9511, destroy), (0x4f959e, destroy)):
            env.override(address, effect)
        env.override(0x4f90c7, lambda env, call: payload)
        if no_allocation:
            env.override(0x4fcaea, allocate(fail=True))
        return {'obj': obj, 'stream': stream, 'owner': owner}
    return setup


def cases(random_source):
    for trial in range(8):
        words = [random_source.getrandbits(32) for _ in range(84)]
        for function in (WRITE, READ):
            for mutate in (False, True):
                yield Case('numeric %x trial %d mutate %s' % (function, trial, mutate), function,
                           setup_case(words, operation=7 if function == READ else 4, mutate=mutate),
                           arguments=(lambda t: t['stream'], lambda t: t['obj'] + 0x38))
        for function in (BASE, DERIVED):
            for op in (0, 1, 3, 4, 5, 6, 7, 8, 0xffffffff):
                yield Case('serializer %x op %x trial %d' % (function, op, trial), function,
                           setup_case(words, operation=op, length=(0, 1, 13, 31)[trial % 4],
                                      backwards=bool(trial & 1), mutate=bool(trial & 2),
                                      failure=(0, 0xffffffff)[trial % 2]),
                           receiver=lambda t: t['obj'], arguments=(lambda t: t['stream'], op, 0x12345678, lambda t: t['owner']))
            yield Case('null stream %x trial %d' % (function, trial), function,
                       setup_case(words), receiver=lambda t: t['obj'], arguments=(0, 7, 0xabcdef, 0))
            for mode in ('allocation',):
                yield Case('allocation failure %x %s trial %d' % (function, mode, trial), function,
                           setup_case(words, operation=7, no_allocation=True),
                           receiver=lambda t: t['obj'], arguments=(lambda t: t['stream'], 7, 0x1badb002, lambda t: t['owner']),
                           expect='return')
