# Level 1 player projectile and dynamite helpers: review notes

## 2026-10-22, exemption and fault-replacement review

All six coverage exemptions in `0x408580` and `0x43ad20` were checked against the
original and are justified. The two functions have the same shape over different
tables (`0x534910` and `0x5375d8`).

- Realloc-failure ranges (`0x4085d5`-`0x408603`, `0x40864f`-`0x408682`,
  `0x43ad75`-`0x43ada3`, `0x43adef`-`0x43ae22`). They run only when the table grow
  routine `0x4db6e0` returns 0. That routine has a single zero-return exit, reached
  from both its grow-down and grow-up arms only when realloc returned 0, and at that
  exit EBP still holds the zero realloc result when it calls `0x4dc680`, which loads
  the word at EBP plus 4. The original therefore reads address 4 and faults before
  `0x4db6e0` can return. Confirmed under the harness: with the realloc stand-in told
  to fail, the original stops with "null pointer access at 0x4 from instruction
  0x4dc680" for both functions, for an index above the table (grow up) and below it
  (grow down), and never reaches the exempt blocks.
- Second range check ranges (`0x40861e`-`0x408635`, `0x43adbe`-`0x43add5`). Between
  the first and second bounds checks there is no call and no store to the bounds. If
  the first check passed, the second compares the same index with the same lower
  bound and the same stored upper bound. If the table grew, `0x4db6e0` set the lower
  bound to the index (grow down, index below the old lower bound, so at most the upper
  bound when lower is at most upper plus one) or the upper bound to the index (grow up,
  index not below the lower bound). Both tables are built only by their static
  constructors (`0x408530`, `0x43acd0`, through `0x403ad0`) with bounds 2000 to 2010
  and stride 4, and `0x4db6e0` is the only routine that changes their bounds, so the
  lower bound never exceeds the upper bound plus one and the second check cannot fail
  on any state the original can reach. A hand-built inconsistent table could reach
  it, which is not an input of the game.

The translation replaces both realloc-failure blocks with a native fault after
`0x4db6e0` returns 0 (`tableEntry` and `tableDispatch`). This is behaviour-identical
on every input the original can reach: the original faults inside `0x4db6e0` on
exactly those inputs, and under the harness the native side, which calls the
original `0x4db6e0`, faults at the same instruction first, so the native fault branch
is never reached. If `0x4db6e0` is later recovered natively, its failure exit must
still fault (or end the game) rather than return 0 and continue, or this branch
becomes reachable; the original game would crash there. The fault code used
(`CLAW_FAULT_ABI`) is a label only.

No translation, case or threshold change was made. Gate evidence is unchanged.
