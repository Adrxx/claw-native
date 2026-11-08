# Original scene type2 fader

Additive recovery from the hash-pinned original Captain Claw v1.0 executable, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. `SceneFadeRuntime.h/.cpp` recovers the source type2 family used by48feb0/48fda0. It composes frozen PlayerFadeRuntime, PlayerFadeBlendRuntime, CArrayRuntime, ActorDestruction, and WorldLoot's shared RNG update. Frozen source files are untouched.

## Scope and exact identities

| Entry | Recovered behavior |
| --- | --- |
|4ec050|Whole factory path **bounded to type2**, including validation, construction, initialization, diagnostics, append and failure prefixes|
|4ed060|8023-word constructor, vtable514228, preserves unwritten words|
|4ed0b0|Five-word packet initialization,2000 RNG selections, permutation table|
|4ed1a0|Actual pixel sweep and row completion, locking/unlocking and per-row state|
|4ed5d0|Maximum step count, band size+height|
|4ed080 /4ed0a0|Deleting destructor / derived-to-base destruction|
|4efb00 /4efc40|Prime-modulus permutation / source trial-division predicate|
|4ecc00|Five-word packet defaults `[3,0,0,1,15]`|
|4c96b0|Verified literal RET, type2 pre/post callbacks|

The actual object allocation is `0x7d5c` bytes,32092 bytes,8023 words. Its virtual table is514228: delete4ed080, step4ed1a0, max4ed5d0, pre4c96b0, post4c96b0. Step/init/delete are thiscall with one stack argument and RET4; max/ctor/dtor/pre/post take none.4efb00 is cdecl `(outputToken,minimum,maximum,start)`;4efc40 is cdecl `(value)`.

Whole4ec9c0 `(duration,initialWait,verticalBlankFlag)`,4ec990,4ec600 removal,4ec8d0 base ctor,4ecb00 surface binding and4ecb20 DD binding are composed directly from frozen PlayerFadeRuntime. Diagnostic CString construction/destruction and embedded palette-owner destruction compose frozen Blend/ActorDestruction. This module does not duplicate the shared runner or approximate it with an opacity effect.

## Packet, RNG, and source pixel sweep

The factory accepts packet tag3. Packet words are tag,destination surface,source surface,outward flag,band percentage. Null surface words fall back to fader+24/+28. Missing source forces outward=1. Init stores step0, effective surfaces/flag, width from destination+18 and height from+14. Valid percentage is signed0..100; band height is original53-bit-precision truncation of percentage×source float0.009999999776482582×height. Thus percentages can truncate below an intuitive decimal result.

The fixed source arrays are:

-+5c:2000 integer row-progress counters;
-+1f9c:2000 integer permutation cursors selected by source RNG modulo width;
-+3edc:2000 single-precision fractional pixel residuals;
-+5e1c:2000 integer permutation entries.

Init clears the three source arrays and makes exactly2000 actual4a3050 RNG updates. The module invokes explicit4a7dc0 CRT-thread lookup and composes frozen `claw_world_loot_next_random` over the returned thread's live+14 seed. Other game RNG consumers must share that word; no new stream/seed is introduced. Thread lookup callbacks are compared at every source call and can change live receiver fields.

4efb00 searches for a prime modulus starting at maximum−minimum, allocates the exact temporary integer table, searches a multiplicative generator, emits the bounded source sequence, and frees the temporary. It can emit maximum+1 entries, hence the bounded safe type2 width1..1999 profile. Small modulus1/2/3 preserves the original allocator-token-dependent fallback multiplier; it is not replaced by a sensible shuffle. Temporary allocation failure leaves initialized permutation words unchanged and returns normally, so factory init still succeeds.

Step0 is a literal early return: no locks, state writes, or RNG. Positive step locks live destination/source surfaces, uses source signed row bounds and source float(width/band) scale, then applies its sine-driven pixel sweep. The original sine constant is float1.5707950592041016. Row progress remains integer; residuals round to float on their source stores. The row's outward/copy branch is captured before its RNG calls, while subsequent rows reload live height/band/width fields. Tests deliberately mutate these fields at CRT-thread lookups to verify that distinction. Source pixel selection includes its width endpoint and can touch stride padding; no clamping/repainting is added. Row completion copies or clears the exact source byte count with source-forward-copy order, including aliased buffers. Final step storage precedes live surface unlocks.

The safe native profile is width1..1999,height0..2000,bytesPerPixel0..4.0-byte pixels preserve source RNG/row state with no pixel transfer. Source unsafe larger array/format profiles receive fault2 at the reached prefix rather than an invented original normal return. Native libm sine plus original scalar store/truncation order matches the directed dimensions, percentage edges, retained and mutation profiles measured here; these tests are not an exhaustive proof of every possible x87/libm sine operand.

## Runner timing and transport

The frozen runner gets maxsteps once, executes pre and step0, performs the original GetTickCount-based initial wait, captures a baseline as source float, and busy-polls steps computed from elapsed/duration. It dispatches changed signed-positive steps through max, applies the source final maximum step when required, computes its frame-rate word+34, then executes post. Both pre/post are the original single RET. No synthetic timestep, Sleep, redraw cadence or expiry is installed.

The clock import is546a24/GetTickCount, distinct from546df0/timeGetTime used by other game routines. Real UInt32 trajectories, including source float precision and unsigned wrap, must be preserved by the host. Zero duration or a stationary clock can stall the original loop; borrowed maximumClockReads provides a diagnostic fault2 at the matching original instruction prefix. It is not a source timeout or successful fade completion.

When the third runner argument is nonzero and fader+2c is present, the source performs DD vtable+58 `(dd,1,0)` before intermediate step updates. That interface boundary is vertical-blank synchronization, with no window-message pumping in these recovered bodies. Microsoft's [WaitForVerticalBlank documentation](https://learn.microsoft.com/en-us/windows/win32/api/ddraw/nf-ddraw-idirectdraw7-waitforverticalblank) describes the interval-wait flags. SpecialCommand's48feb0/48fda0 wrappers pass the source third argument0. Physical vertical-blank waiting, surface4b9730 lock, COM unlock+80, GetTickCount, allocator/CRT-thread and CString atomic-decrement transports remain explicit adapters. There is no separate invented PeekMessage/DispatchMessage/presentation loop.

## Stable integration recipe

Construct `ClawSceneFadeContext` borrowing a live `ClawPlayerFadeBlendContext`, which borrows the existing `ClawPlayerFadeContext`. Preserve source surface/DD identities, sized token spans, and mutable RNG thread+14 alias. Borrowed temporaryDescriptorToken must provide five scratch words for a null packet; temporaryStringToken/emptyStringToken must describe the real CString scratch/empty-data profile. These represent automatic locals, with no game-heap ownership claim.

For a rich SpecialCommand4ec050 callback, copy its live five-word packet to borrowed scratch and call `claw_scene_fade_entry(4ec050,manager,[2,scratch],2,...)`. The factory allocates the actual object and appends it to the manager's original CArray. For4ec9c0 route all three arguments unchanged to the same context; its frozen virtual dispatch routes type2 methods internally. Route4ec600 there for real list removal and deletion. Root need not edit the frozen runner. Other factory types remain fault3; existing type1 belongs to frozen PlayerFadeBlendRuntime.

Callbacks use the existing six-argument `ClawPlayerFadeDependency`. Native faults reside in borrowed fade->fault and are caller-managed; recognized calls return1 only without a fault. Caller must clear a previous diagnostic before starting another source operation. Actual fader allocation and source list ownership are distinct from physical pixels/DD/native display presentation. Read-only analysis lives in `work/scene-fade-agent/ghidra-project`; no shared project was opened.

## Verification

`work/test-env/bin/python Tests/compare_scene_fade_runtime.py` executes complete original entries, retaining objects through factory→runner→list removal/destruction. Every ordered service snapshot preserves all1179648 heap bytes plus114688 original-global bytes. Lossless4096-byte block interning shares equal bytes to reduce memory; it does not replace comparison with selected fields or hashes. Meaningful EAX and full final heap/globals also match. Original4a3050 instructions execute between each adapted CRT-thread lookup; the native side composes the already frozen LCG. The CString InterlockedDecrement adapter performs the original atomic word update without adding a native service event, matching frozen ActorDestruction's direct word operation.

Coverage includes12 completed dimension/direction profiles (including640×480), byte widths0..4, retained nonadjacent/repeated step values, row padding, percentage0/1/15/80/100 and rejection edges, small/prime/composite/permutation widths through1999, duration1/17/1450, initial waits, optional DD waits, object/permutation/list/CString allocation failures, default/mismatched descriptors, callback receiver mutation and two original stalled-clock prefixes. Allocation faults are compared with a valid SEH/TIB adapter and unmapped null page; native diagnostic failures do not masquerade as original returns.

Final checks pass216 whole original calls,145651 ordered full snapshots and1135 original instruction addresses, plus two stopped original clock prefixes. These measured counts are recorded in `work/scene-fade-agent/verification.json`. Strict C11 header and C++ compilation pass. The private ASAN/UBSAN program executes the real ctor/init and43 multibyte pixel steps followed by deletion. These tests establish the finite recovered type2 graph under explicit transports, not physical DirectDraw/Mac/iPad display equivalence or complete gameplay.
