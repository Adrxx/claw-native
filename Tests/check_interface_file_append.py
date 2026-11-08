"""Focused original/native check of the legacy controller append adapter.

This validates the existing CArray composition on its ordinary array domain;
canonical family admission is a separate gate.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Tests.clawparity.program import claw

claw()  # Verify the reference executable before the legacy helper reads it.
import interface_file_helpers as h

h.fresh()
assert h.compare(0x4dd2c0, 0, [0], "null component before receiver access") == 0
for count, capacity, grow in (
    (0, 0, 0), (0, 4, 0), (1, 4, 0), (4, 4, 0),
    (4, 4, 1), (4, 4, 19), (40, 40, 0), (8192, 8192, 0),
):
    h.fresh(count + grow)
    data = h.BASE + 0x200000 if capacity else 0
    h.put(h.MENU + 12, [data, count, capacity, grow])
    if data:
        h.put(data, [(0x12345678 + i * 17) & 0xffffffff for i in range(capacity)])
    assert h.compare(
        0x4dd2c0, h.MENU, [h.IMAGE], f"append {count}/{capacity}/{grow}"
    ) == 1
print("PASS raw append", h.calls, "calls", h.snapshots, "snapshots")
