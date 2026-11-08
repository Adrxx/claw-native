# level_eight_gabriel_core_01 notes

Coverage exemptions were checked against the original with fault probes (work/packets/level_eight_gabriel_core_01/fault-probes.cases.py, log in fault-probes.log):

- 0x4432ec to 0x4432ee: operator new returning 0 leads to a null read at 0x4432ee. The probe faults there.
- 0x443405 to 0x443433, 0x44347f to 0x4434b2: reached only if the grow routine 0x4db6e0 returns 0, and every zero return first calls 0x4dc680, which faults on a null pointer. The probe faults at 0x4dc680.
- 0x44344e to 0x443465: second lookup with the same index and unchanged bounds after the first lookup succeeded or grew the table; cannot be out of range.

The translation seeds the x87 status word with condition bit C0 (0x100) before the first conversion in 0x443ab0, because the original carries that bit from earlier original callees.
