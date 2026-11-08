"""Original compiler-scope unit witnesses for the native source graph owner."""
import hashlib
import json
import random
import struct
import sys
from pathlib import Path

from Tests.clawparity.env import NativeCompilerContext
from Tests.clawparity.kernel import Machine, STACK_BASE, STACK_SIZE, STACK_TOP
from Tests.clawparity.program import claw


def main():
    program = claw()
    rng = random.Random(0x4a48c0)
    names = ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp', 'esp',
             'eip', 'eflags', 'fsHead')
    rows = []
    for frame in (STACK_BASE + 16, STACK_TOP, STACK_BASE + STACK_SIZE - 0x200):
        for old_base in (0, 1, 0xffffffff, 0x12345678, frame + 0x41,
                         frame + 0x40, rng.getrandbits(32)):
            for nested in (False, True):
                for handler, continuation in ((0x508525, 0x50233f), (0x508539, 0x502373)):
                    machine = Machine(program, 0x64000000, 0x1000)
                    machine.write(STACK_BASE, bytes([0xa5]) * STACK_SIZE)
                    head = frame + 0x40 if nested else 0xffffffff
                    stores = [(frame, continuation)]
                    if nested:
                        stores += [(head, head + 0x20), (head + 4, 0x508bf8), (head + 8, 0xffffffff),
                                   (head + 0x20, head + 0x40), (head + 0x24, 0x508525),
                                   (head + 0x28, 0xffffffff), (head + 0x40, 0xffffffff),
                                   (head + 0x44, 0x508539), (head + 0x48, 0xffffffff)]
                    for address, value in stores:
                        machine.write(address, struct.pack('<I', value))
                    flags = 2 | (rng.getrandbits(32) & 0x8d5)
                    context = NativeCompilerContext(72, 1, 0x7ff, 0x7ff,
                        handler, *[rng.getrandbits(32) for _ in range(5)], old_base,
                        frame, 0x4a48c0, flags, head, continuation, 0, 0)
                    initial = {name: getattr(context, name) for name in names}
                    result = machine.call_context(0x4a48c0, context)
                    assert result.completed
                    rows.append(dict(initial=initial, continuation=continuation, stores=stores,
                        final={name: getattr(context, name) for name in names},
                        stack_sha256=hashlib.sha256(machine.read(STACK_BASE, STACK_SIZE)).hexdigest()))
    output = Path(sys.argv[1]).resolve()
    assert Path('work').resolve() in output.parents
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(sha256=program.sha256, stack_fill=0xa5, rows=rows), indent=2) + '\n')
    print(f'PASS {len(rows)} fresh original compiler-scope native-owner unit profiles')


if __name__ == '__main__':
    main()
