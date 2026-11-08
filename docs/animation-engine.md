# Original v1.0 animation recovery

Binary: original-labeled Claw Recluse v1.0 CLAW.EXE, SHA-256
350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263.
Addresses below apply only to that input. The test rejects other hashes.

## Recovered routines

- Animation update: 0x4c82a0 through 0x4c879c, excluding jump tables.
  Ghidra 12.1.4 full analysis and decompilation were completed locally;
  docs/original-v10-animation-updater.c preserves the pseudocode observation.
  Native implementation is Sources/AnimationEngine.cpp, with pointer-free
  portable fields in AnimationEngine.h.
- ANI record decoder: 0x4d76e0 through 0x4d779b. Located through ANIS references,
  resource registration at 0x4ce0d0/0x4cdff0 and sequence load 0x4d6070/0x4d61b0.
  The record is 20 bytes followed by a null-terminated name when flags & 2.
  Command, image parameter, duration, code and dx/dy are sign-extended shorts.
  Flags and the final unused word are copied as shorts; their runtime upper
  halves are untouched. Native source stores only the meaningful flag bits
  and omits the unused word. Name length is in bytes, not characters.
- Sequence setup: 0x4c8220. Runtime adapter initializes record zero, remaining
  zero, stopped zero, current/previous code from record zero and rate 1.

## Runtime behavior

The updater maintains one pending delay. An untimed delay decrements once per
call and returns even when it reaches zero. A timed delay consumes the supplied
delta; expiry discards overshoot and executes one record. Zero-duration records
also execute once per call. These details rule out a generic elapsed-time loop.

Recovered commands select/increment/decrement image IDs, set or apply movement
fields, dispatch spatial/global sound events, advance/hold/reset records, and
stop a sequence. Stop retains the final image. Arithmetic uses 32-bit wrapping.
Duration scaling preserves binary32/x87 conversion behavior using integer
arithmetic with round-to-nearest-even at 53-bit precision before truncation.
CRT initialization 0x4a5730 calls the pointer at 0x52e978 (0x4a3080), which
reaches precision initializer 0x4a7ef0. Executing that initializer with its
unmodified helpers selects 53-bit precision. Earlier tests assumed the x87
reset default of 64 bits; a generated case then differed by one unit when
checked at the original precision. The native arithmetic and harness have
been corrected. Masked exceptions and round-to-nearest are the harness's
initial environment; a full Windows launch has not yet been observed.

The Swift app now calls this routine through ClawAnimationPlayback rather than
the previous cumulative-duration modulo animation picker. It supplies a timer
delta for the preview; the original game scheduler has not been recovered.
Symbolic event tokens identify names in this preview; no audio is played and
resource-registry lookup success is not claimed.

## Measured comparisons

Tests/compare_animation_engine.py compiles against the actual native routine and
executes the hash-pinned original instructions in Unicorn 2.1.4:

- 5,000 deterministic generated update cases pass: full actor/state buffers,
  return value and sound dispatch agree. Includes every command, image holes,
  wrapping integers, pause/delay boundaries and arbitrary binary32 rate bits.
  602 original instruction addresses are reached, including the precision
  initializer and its helpers. Both generated and real-record runs use the
  initializer's resulting control word (0x023f as exposed by Unicorn).
- Original image helpers, record lookup/reset helpers and x87 integer conversion
  execute. Only external audio bodies at 0x4c88e0 and 0x4208e0 are replaced with
  returns; their receiver, four arguments and spatial/global choice are checked.
- 2,000 generated ANI record decodes agree with original signed fields, flag
  tests, consumed lengths, name bytes and resolved event tokens. Original registry
  lookup 0x4f6286 is stubbed; its name and receiver are checked.
- 270 records from all 54 CLAW/ANIS files in the local CD-rip resource set agree
  with the original decoder. They then pass 33,480 chained original/native
  updater steps under two delta schedules. This checks evolving state, not only
  isolated calls. It does not prove those assets are identical to v1.0 assets.
- Swift/C integration checks initial image selection, SWIPE stopping and final
  image retention, replay/reset and WALK looping.

Malformed native inputs are bounded and rejected. The original loader's unsafe
out-of-bounds behavior is deliberately not executed or claimed as equivalent.
Neither emulator tests nor native preview establish original scheduling, audio
mixing, game movement/collision, combat, enemies, level completion or save behavior.
Whole-game identity requires comparisons against an actual original game run.
