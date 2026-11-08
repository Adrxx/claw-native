"""Independent original static-range CPU, memory and allocation cases."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.kernel import STACK_BASE, STACK_TOP

ROOTS = (0x403ad0, 0x4dbb10, 0x4dbb90, 0x4db620)
PCS = {0x403ad0: 0x4a01f4, 0x4dbb10: 0x403ae8,
       0x4dbb90: 0x4dbb2e, 0x4db620: 0x4dbbb9}
MALLOC = 0x4a48e0


def make_case(rng, root, size=4, lower=0, upper=2, fourth=1,
              failure=0, warm=False, mode=4, change=None, manager_null=False,
              index=0):
    registers = [rng.getrandbits(32) for _ in range(6)]
    flags = 2 | (rng.getrandbits(32) & 0x8d5)
    frame = (STACK_TOP, STACK_BASE + 0x1800, STACK_TOP - 0x384)[index % 3]
    head = 0xffffffff if index % 2 else frame + 0x100
    witness = rng.getrandbits(32)
    pattern = bytes(rng.getrandbits(8) for _ in range(64))
    strings = [rng.getrandbits(32) for _ in range(8)]

    def setup(env):
        count = 8 if root == 0x4db620 else 28 if root == 0x4dbb90 else 36
        receiver = env.object(count, 'patterned receiver', data=pattern[:count])
        manager = env.object(32, 'independent unit manager', data=pattern[:32])
        trace = env.object(512, 'allocation CPU and request witnesses', fill=0)
        alternate = env.object(128, 'postcall data witness', fill=0x93)
        env.write(frame - 0x500, bytes((i * 37 + index * 11) & 255 for i in range(0x700)))
        old_base = frame + 0x200 + (index % 4)
        env.put(old_base, 0x10293847, witness)
        if head != 0xffffffff:
            env.put(head, head + 0x30, 0x50a038, 0xffffffff)
            env.put(head + 0x30, 0xffffffff, 0x50a038, 0xffffffff)
        env.put(0x544b30, *strings)
        env.put(0x544b4c, strings[-1] or 1 if warm else 0)
        env.write(0x544b50, bytes(32))
        env.put(0x544b50 + 0xc, mode)
        env.put(manager + 0xc, mode)
        env.put(0x544d18, 0)
        env.put(0x544b14, witness ^ 0x5a5a5a5a)
        context = NativeSourceContext(72, 1, 0x7ff, 0x7ff, *registers,
                                      old_base, frame, root, flags, head, 0x472, 0, 0)

        def allocation(e, call):
            ordinal = e.calls_so_far(MALLOC)
            request = call.arguments[0]
            result = 0 if ordinal == failure else e.object(max(1, request),
                         'physical allocation', fill=0xa7)
            state = call.source_context
            fields = ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp',
                      'esp', 'eip', 'eflags', 'fsHead')
            values = [getattr(state, f) for f in fields] if state is not None else [0]*11
            e.put(trace, ordinal)
            e.put(trace + 4 + (ordinal - 1)*96, request, result, call.receiver,
                  call.stack_pointer, call.source_return_pc, *values)
            e.write(trace + 240 + (ordinal - 1)*64, e.read(receiver, count))
            if ordinal == 1 and change == 'fourth':
                e.put(receiver + 0x14, alternate)
            if ordinal == 1 and change == 'element':
                e.put(receiver + 0x18, 7)
            if ordinal == 2 and change == 'array':
                e.put(receiver + 8, 0xfffffffc, 9, alternate)
            return result

        context.ecx = receiver
        incoming = ((lower & 0xffffffff, upper & 0xffffffff) if root == 0x403ad0 else
                    (0 if manager_null else manager,) if root == 0x4db620 else
                    (size & 0xffffffff, lower & 0xffffffff, upper & 0xffffffff, fourth))
        env.put(frame, PCS[root], *incoming)
        env.override(MALLOC, allocation)
        return {'receiver': receiver, 'manager': 0 if manager_null else manager,
                'source': context}

    arguments = ((lower & 0xffffffff, upper & 0xffffffff) if root == 0x403ad0 else
                 (lambda t: t['manager'],) if root == 0x4db620 else
                 (size & 0xffffffff, lower & 0xffffffff, upper & 0xffffffff, fourth))
    label = (f'{root:x} size{size:x} bounds{lower}:{upper} fourth{fourth:x} '
             f'failure{failure} mode{mode} warm{warm} change{change} cpu{index}')
    return Case(label, root, setup, receiver=lambda t: t['receiver'],
                arguments=arguments, source_context=lambda t: t['source'],
                source_return_pc=PCS[root])


def cases(random_source):
    index = 0
    def case(root, **kw):
        nonlocal index
        index += 1
        return make_case(random_source, root, index=index, **kw)

    for warm in (False, True):
        for null in (False, True):
            for _ in range(8):
                yield case(0x4db620, warm=warm, manager_null=null)
    for root in ROOTS[:3]:
        for warm in (False, True):
            for mode in (0, 1, 4):
                for lower, upper in ((0, 0), (-3, 2), (7, 6),
                                     (0x7fffffff, -0x80000000)):
                    for failure in (0, 1):
                        yield case(root, lower=lower, upper=upper, warm=warm,
                                   mode=mode, failure=failure)
    for root in (0x4dbb10, 0x4dbb90):
        for size in (0, 1, 2, 3, 4, 5, 7, 16, 31):
            for fourth in (0, 1, 0x81234567):
                yield case(root, size=size, lower=-2, upper=0, fourth=fourth)
            yield case(root, size=size, fourth=0, failure=2)
        # Products wrap to bounded zero/small requests despite large signed spans.
        for size, lower, upper in ((0, -0x80000000, 0x7fffffff),
                                  (4, 0, 0x40000000),
                                  (0x80000001, 0, 1),
                                  (0xffffffff, 3, 2)):
            yield case(root, size=size, lower=lower, upper=upper)
        for change in ('fourth', 'element', 'array'):
            yield case(root, size=3, lower=-1, upper=2, fourth=0, change=change)
        for _ in range(32):
            lower = random_source.randrange(-200, 201)
            yield case(root, size=random_source.randrange(0, 32), lower=lower,
                       upper=lower + random_source.randrange(0, 17),
                       fourth=random_source.choice((0, 1, 0xffffffff)),
                       failure=random_source.choice((0, 0, 1, 2)),
                       mode=random_source.choice((0, 1, 4)),
                       warm=bool(random_source.getrandbits(1)))
