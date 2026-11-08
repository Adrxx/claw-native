"""Blind original cases for the ambient EBP word and independent physical RET."""
import ctypes

from clawparity.cases import Case
from clawparity.env import NativeSourceContext
from clawparity.kernel import STACK_BASE, STACK_SIZE

ENTRY = 0x4DC680
RETURNS = (0x4DB78D, 0x4DB803, 0x4DB8AB, 0x4DB9D5, 0x4DBA19,
           0x4DBBF3, 0x4DBC4C, 0x4DBDB4, 0x4DBF9F, 0x4DC141,
           0x4DC1D2, 0x4DC751)


def source_case(label, layout, value, witnesses, flags, continuation, fs_depth=1):
    def setup(env):
        # Dirty physical frames carry different PCs and locals. Only the leaf's
        # ESP word is its return; ancestor words are ordinary loaded u32 data.
        esp = 0x02004000
        outer = esp + 0x400
        parent = esp + 0x200
        env.put(esp - 16, 0xA1020304, 0xB2030405, 0xC3040506, 0xD4050607)
        env.put(esp, continuation, 0xE5060708, 0xF6070809, 0x1708090A)
        env.put(parent, outer, RETURNS[4], 0x28394A5B, 0x394A5B6C)
        env.put(outer, 0xFACED00D, RETURNS[9], 0x4A5B6C7D, 0x5B6C7D8E)
        if layout.startswith('heap'):
            size, offset = {'heap-first': (32, 0), 'heap-last': (32, 28),
                            'heap-interior': (32, 12), 'heap-unaligned': (32, 7),
                            'heap-exact4': (4, 0), 'heap-base8': (8, 4)}[layout]
            base = env.object(size, 'ambient-word-object', fill=0xA7)
            address = base + offset
            env.put(address, value)
        elif layout == 'nested-parent':
            address = parent + 4
            env.put(address, value)
        elif layout == 'nested-outer':
            address = outer + 4
            env.put(address, value)
        elif layout == 'stack-first':
            address = STACK_BASE
            env.put(address, value)
        elif layout == 'stack-last':
            address = STACK_BASE + STACK_SIZE - 4
            env.put(address, value)
        elif layout == 'stack-unaligned':
            address = esp - 123
            env.put(address, value)
        elif layout == 'return-alias':
            address = esp
        elif layout == 'data-pointer':
            address = env.object(8, 'pointer-word', fill=0x6B) + 4
            target = env.object(20, 'pointed-to-data', fill=0xD3)
            env.put(address, target + 7)
        elif layout == 'frame-pointer':
            address = env.object(8, 'frame-identity-word', fill=0x7C) + 4
            env.put(address, parent)
        else:
            raise ValueError(layout)
        fs = 0xFFFFFFFF
        for index in range(fs_depth):
            record = esp - 0x400 - 16 * index
            env.put(record, fs, RETURNS[index], 0xA5A50000 | index)
            fs = record
        context = NativeSourceContext(size=ctypes.sizeof(NativeSourceContext), version=1,
            inputMask=0x7FF, outputMask=0x7FF, preserveMask=0x472,
            eax=witnesses[0], ebx=witnesses[1], ecx=witnesses[2],
            edx=witnesses[3], esi=witnesses[4], edi=witnesses[5],
            ebp=(address - 4) & 0xFFFFFFFF, esp=esp, eip=ENTRY,
            eflags=flags, fsHead=fs)
        return {'source': context}
    return Case(label, ENTRY, setup, source_context=lambda t: t['source'],
                source_return_pc=continuation,
                covers=('raw-EBP-plus-four-u32', 'independent-one-RET',
                        'all-registers-flags-FS-and-stack-preserved'))


def cases(random_source):
    witnesses = (0xC1D2E3F4, 0x82345671, 0x93456782,
                 0xA4567893, 0xB56789A4, 0xC6789AB5)
    # Each byte and sign boundary differs from neighboring poison and EAX input.
    words = (0, 1, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF,
             0x89ABCDEF, 0x01020304, 0xFEEDC0DE)
    for index, word in enumerate(words):
        yield source_case(f'raw word {word:08x}', 'heap-base8', word,
                          witnesses, (2, 0x8D7)[index % 2], RETURNS[index], index % 3)
    for index, layout in enumerate(('heap-first', 'heap-last', 'heap-interior',
                                   'heap-unaligned', 'heap-exact4', 'stack-first',
                                   'stack-last', 'stack-unaligned', 'nested-parent',
                                   'nested-outer', 'return-alias', 'data-pointer',
                                   'frame-pointer')):
        yield source_case(layout, layout, 0xBADC0123 + index,
                          witnesses, 0x893, RETURNS[index % len(RETURNS)], 2)
    # Exercise each arithmetic flag in isolation and fresh register witnesses.
    for index, flag in enumerate((0, 1, 4, 0x10, 0x40, 0x80, 0x800, 0x8D5)):
        yield source_case(f'flags {flag | 2:03x}', 'heap-unaligned',
                          random_source.getrandbits(32),
                          tuple(random_source.getrandbits(32) for _ in range(6)),
                          flag | 2, RETURNS[index], index % 3)
    for index in range(12):
        layout = ('heap-interior', 'nested-parent', 'nested-outer', 'stack-unaligned')[index % 4]
        yield source_case(f'fresh {index} {layout}', layout,
                          random_source.getrandbits(32),
                          tuple(random_source.getrandbits(32) for _ in range(6)),
                          (random_source.getrandbits(12) & 0x8D5) | 2,
                          RETURNS[index], index % 3)
