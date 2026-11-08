"""Focused portable API regression; canonical family admission is separate."""
import random

from clawparity.program import claw

claw()  # Verify the pinned reference before the legacy transport opens it.
import sound_trigger_runtime_helpers as g


def main():
    values = [0, 1, 5, 6, 14, 15, 16, 100, 0x7fffffff, 0x80000000, 0xffffffff]
    rng = random.Random(0x4026a0)
    for index in range(120):
        g.setup(index)
        master = values[index % len(values)] if index < 88 else rng.getrandbits(32)
        old = master if index % 4 == 0 else master ^ 0x81920174
        g.put(g.ALLOC, [0x50b004, g.POOL, rng.getrandbits(32), old, values[(index + 3) % len(values)]])
        g.compare(0x4026a0, g.ALLOC, [master], f"master/{index}", void=True)
    for index in range(48):
        g.setup(index)
        master = values[index % len(values)]
        first, second, third = g.BASE + 0x9000, g.BASE + 0x9020, g.BASE + 0x9040
        obj1, obj2 = g.ALLOC, g.ALLOC + 0x100
        g.put(obj1, [0x50b004, g.POOL, 79, master if index % 3 == 0 else master + 1, 100])
        g.put(obj2, [0x50b004, g.POOL, 51, master ^ 1, 73])
        g.put(first, [second, 0, obj1])
        g.put(second, [third, first, 0])
        g.put(third, [0, second, obj2])
        g.put(g.AMBIENT + 0xc, [0 if index % 7 == 0 else first])
        g.put(g.AUDIO + 0x2c, [0 if index % 2 else g.BASE + 0x8000])
        g.compare(0x4024e0, g.AMBIENT, [master], f"manager-master/{index}", void=True)
    g.replayWriter.close()
    print('{"status":"pass","portable_master_cases":168,"canonical_admission":false}')


if __name__ == "__main__":
    main()
