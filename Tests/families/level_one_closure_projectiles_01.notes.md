# Level 1 closure projectile helpers: review notes

## 2026-10-22, exemption review

The five dispatchers (`0x410a80`, `0x411030`, `0x4114e0`, `0x411990`, `0x458280`)
have the same shape as `0x408580` (see `level_one_closure_dynamite_01.notes.md`) over
tables `0x534ab0`, `0x534ba0`, `0x534a38`, `0x534b00` and `0x537ac0`. Each table is
built only by its static constructor through `0x403ad0`, with bounds 2000 to 2010 and
stride 4, and only `0x4db6e0` changes the bounds.

- Ten realloc-failure ranges, two per dispatcher (the blocks after each `0x4db6e0`
  call returns 0). Justified: `0x4db6e0` returns 0 only after realloc fails, and on
  that exit it calls `0x4dc680` with EBP equal to the zero realloc result, so the
  original reads address 4 and faults first. The same mechanism was confirmed under
  the harness for `0x408580` and `0x43ad20`.
- Five second-range-check ranges, one per dispatcher (`0x410b1e`, `0x4110ce`,
  `0x41157e`, `0x411a2e`, `0x45831e`, each up to the join after its second grow call).
  Justified, but they were recorded with the failure-path reason. Their reason now
  states why the second check cannot fail on any state the original can reach.
- One range was not justified and was removed: `0x4582a9`-`0x4582c2` in `0x458280` is
  the first out-of-range grow call, the normal path for an index outside the table.
  The existing cases already run it (the "grows for" and "regrown entry" cases), so
  removing the exemption needed no new cases.

The translation's `lookupEntry` returns 0 after `0x4db6e0` returns 0, in place of the
original's error report and default-entry path. That branch cannot run without the
original faulting first, and under the harness the native side faults inside the
original `0x4db6e0` before it returns. Under docs/ADMISSION.md rule 5 the unexecuted
bytes may be exempt with a reason; the translation of an unreachable branch is not
compared and does not affect admission. If reached anyway, the native side then reads
address 0 and faults, which matches the original crashing. If `0x4db6e0` is later
recovered natively, its failure exit must still fault rather than return 0.

Re-gated on 2026-10-22 with `make gate FAMILY=level_one_closure_projectiles_01
ARGS='--record --jobs 1'`: admitted, 220 cases, every required byte executed
(`0x458280` now 153 required bytes), mutation score 1.0 (29 of 29 valid mutants
killed).
