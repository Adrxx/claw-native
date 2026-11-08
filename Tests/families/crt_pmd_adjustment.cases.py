"""Blind inputs for the original CRT PMD adjustment leaf."""
from clawparity.cases import Case
from clawparity.env import NativeSourceContext

ENTRY = 0x4A8ED0
PCS = (0x4A8CDB, 0x4A8D48, 0x4A8D96, 0x4A8DE7, 0x4A8E04)
BASE, SIZE = 0x01FF0000, 0x20000
MASK = 0xFFFFFFFF


def cases(random_source):
    serial = 0

    def emit(label, builder, source):
        nonlocal serial
        serial += 1
        case_number = serial
        pc = PCS[case_number % len(PCS)]
        registers = [random_source.getrandbits(32) for _ in range(7)]
        flags = random_source.getrandbits(12) & 0x8D5 | 2
        frame = (BASE + 4, BASE + SIZE - 12, 0x02004000)[serial % 3]
        stack = bytes(random_source.getrandbits(8) for _ in range(128))

        def setup(env):
            if source:
                env.write(BASE, stack)
                env.write(BASE + SIZE - 128, stack[::-1])
                ctx = NativeSourceContext()
                ctx.size, ctx.version = 72, 1
                ctx.inputMask = ctx.outputMask = 0x7FF
                ctx.preserveMask = 0x472
                for field, value in zip(('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp'), registers):
                    setattr(ctx, field, value)
                ctx.esp, ctx.eip, ctx.eflags = frame, ENTRY, flags
                ctx.fsHead = 0xFFFFFFFF
                if case_number % 2:
                    ctx.fsHead = BASE + 0x200
                    env.put(ctx.fsHead, 0xFFFFFFFF, 0x13579BDF, 0x2468ACE0)
            else:
                ctx = None
            obj, desc = builder(env, frame, registers[4], pc)
            return {'object': obj, 'descriptor': desc, 'source': ctx}

        options = {'source_context': lambda t: t['source'], 'source_return_pc': pc} if source else {}
        return Case(label + (' source' if source else ' ordinary'), ENTRY, setup,
                    arguments=(lambda t: t['object'], lambda t: t['descriptor']), **options)

    def direct(obj, mdisp, pdisp, aligned=True):
        def build(env, frame, saved, pc):
            allocation = env.object(13 if not aligned else 8, 'direct-descriptor', fill=0xA7)
            desc = allocation + (1 if not aligned else 0)
            env.put(desc, mdisp, pdisp)
            return (desc if obj is None else obj), desc
        return build

    for source in (False, True):
        for pdisp in (0x80000000, 0x80000001, 0xFFFFFF00, 0xFFFFFFFE, 0xFFFFFFFF):
            for obj, mdisp in ((0, 0), (0, 1), (MASK, 1), (0x80000000, 0x80000000),
                               (0x7FFFFFFF, 1), (0xDEADC0DE, 0x12345678), (None, 0x87654321)):
                yield emit(f'direct {pdisp:08x} {obj} {mdisp:08x}', direct(obj, mdisp, pdisp), source)
        for i in range(32):
            yield emit(f'random direct {i}', direct(random_source.getrandbits(32),
                       random_source.getrandbits(32), random_source.getrandbits(31) | 0x80000000, False), source)

    def virtual(pdisp, vdisp, mdisp, adjustment, alias='separate'):
        def build(env, frame, saved, pc):
            desc = env.object(24, 'virtual-descriptor', fill=0xB3) + 1
            lookup = env.object(16, 'object-lookup', fill=0xC9) + 3
            cell = env.object(16, 'adjustment-cell', fill=0xD5) + 1
            env.put(desc, mdisp, pdisp, vdisp)
            if alias == 'lookup-descriptor':
                lookup = desc
            elif alias == 'cell-descriptor':
                cell = desc
            elif alias == 'same-cell':
                cell = lookup
            table = (cell - vdisp) & MASK
            env.put(lookup, table)
            if alias != 'same-cell':
                env.put(cell, adjustment)
            return (lookup - pdisp) & MASK, desc
        return build

    for source in (False, True):
        for pdisp in (0, 1, 16, 0x7FFFFFFF):
            for vdisp in (0, 1, 0xFFFFFFFC, 0x80000000):
                for mdisp, adjustment in ((0, 0), (MASK, 1), (0x7FFFFFFF, 1), (0x80000000, MASK)):
                    yield emit(f'virtual {pdisp:x} {vdisp:x} {mdisp:x} {adjustment:x}',
                               virtual(pdisp, vdisp, mdisp, adjustment), source)
        for alias in ('lookup-descriptor', 'cell-descriptor', 'same-cell'):
            yield emit('heap alias ' + alias, virtual(16, 0xFFFFFFFC, 0x12345678, 0x87654321, alias), source)
        for i in range(24):
            yield emit(f'random virtual {i}', virtual(random_source.getrandbits(31),
                       random_source.getrandbits(32), random_source.getrandbits(32),
                       random_source.getrandbits(32)), source)

    def stack_alias(kind):
        def build(env, frame, saved, pc):
            desc = env.object(12, 'alias-descriptor', words=[0xA1234567, 16, 0xFFFFFFFC])
            lookup = env.object(4, 'alias-lookup')
            cell = env.object(4, 'alias-adjustment', words=[0x76543210])
            obj = (lookup - 16) & MASK
            if kind == 'mdisp-saved':
                desc = frame - 4
                obj = (lookup - pc) & MASK
                env.put(lookup, (cell - obj) & MASK)
            elif kind == 'pdisp-saved':
                desc = frame - 8
                env.put(desc, 0x89ABCDEF)
                obj = (lookup - saved) & MASK
                env.put(lookup, (cell - pc) & MASK)
            elif kind == 'vdisp-saved':
                desc = frame - 12
                env.put(desc, 0x87654321, 16)
                env.put(lookup, (cell - saved) & MASK)
            elif kind == 'lookup-saved':
                obj = (frame - 4 - 16) & MASK
                env.put(desc + 8, (cell - saved) & MASK)
            elif kind == 'adjustment-saved':
                env.put(lookup, frame)
            elif kind == 'lookup-object-argument':
                obj = (frame + 4 - 16) & MASK
                env.put(desc + 8, (cell - obj) & MASK)
            elif kind == 'lookup-descriptor-argument':
                obj = (frame + 8 - 16) & MASK
                env.put(desc + 8, (cell - desc) & MASK)
            elif kind == 'lookup-return':
                obj = (frame - 16) & MASK
                env.put(desc + 8, (cell - pc) & MASK)
            return obj, desc
        return build

    # Descriptor-before-frame aliases need room below the lowest valid entry.
    for kind in ('mdisp-saved', 'pdisp-saved', 'vdisp-saved', 'lookup-saved',
                 'adjustment-saved', 'lookup-object-argument', 'lookup-descriptor-argument', 'lookup-return'):
        for i in range(9):
            # The builder cannot place multiword descriptors below the lower stack bound.
            def safe_builder(env, frame, saved, pc, kind=kind):
                if frame == BASE + 4 and kind in ('pdisp-saved', 'vdisp-saved'):
                    return direct(0xDEADC0DE, saved, 0x80000001)(env, frame, saved, pc)
                return stack_alias(kind)(env, frame, saved, pc)
            yield emit(f'stack alias {kind} {i}', safe_builder, True)
