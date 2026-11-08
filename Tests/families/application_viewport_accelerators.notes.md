# Application viewport accelerators: equivalent-mutant evidence

Reviewed on 2026-10-23 against the hash-checked v1.0 executable. The probe script and its full output stay local under `work/review-viewport-equivalents/` (`probe.py`, `probe-result.json`). It runs the original bytes under Unicorn, then a copy patched at the machine-code level with the same mutation, and compares the return point, every register a caller may rely on, all data-section and heap memory and the live stack.

All four equivalent reasons in the specification were proven. The earlier wording of the two shift-offset reasons described a one-byte shift; the mutation operator actually adds 4 to the offset, so the reasons were rewritten. The drop-statement reasons named the third argument of 0x429ed0 where the second is read; that was corrected too.

## Shift-offset, lines 32 and 51 (0x429e30 and 0x429e70)

The mutant reads the scene pointer at +0x30 where the original reads the state pointer at +0x2c, so the first test repeats the second. Split on whether each word is zero:

- Both zero, or +0x2c set and +0x30 zero: both versions return 0 at the same test.
- Both set: both versions take the same path.
- +0x2c zero, +0x30 set: the original returns 0 at once. The mutant calls 0x42a630, which loads +0x2c, finds zero and returns 0 without any store or call, so the function returns 0. The only difference is the scratch register ECX (zero instead of the receiver).

The two callers, at 0x427541 (increase) and 0x427564 (decrease), set EAX to 1 right after the call and restore their own registers without reading ECX. The probe patched the displacement byte at 0x429e35 and 0x429e75 to 0x30 and ran 36 inputs per function (state pointer and scene pointer each present or absent, state query 3, 0 and 6, sizes 1, 5 and 10), stopping at the 0x429ed0 entry or at the return. No run differed in stop point, memory or any register other than ECX; ECX differed in exactly the 9 runs per function with no state object and a scene.

## Drop-statement, lines 42 and 61 (the caller's store to +0x68)

The caller passes (size, 1, 1) to 0x429ed0. That function clamps its first argument to 1 through 10, compares it with +0x68 only to choose between two branches, and both branches reach 0x429f02 because its second argument is 1. At 0x429f05 it stores the clamped size to +0x68, before any call or other read of +0x68. The caller's own store therefore cannot be observed.

The probe replaced the store (0x429e5a and 0x429e9a) with NOPs and compared the whole machine at 0x429f08 for 21 starting sizes per function (minus 4 through 13, 40, the largest and the smallest 32-bit signed values). Memory and every register matched in all runs, including those where the starting size made the function return early. Since the state is identical at 0x429f08, the rest of the run is identical.
