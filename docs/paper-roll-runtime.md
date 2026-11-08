# Source paper-roll transition

`PaperRollRuntime` recovers the original v1.0 Credits roller wrappers and their type0 fader. It composes the frozen fade runner, pause/resume/wait, pointer-array, diagnostic CString and light-table ownership bodies. The two pixel bodies write indexed or multibyte surfaces directly; no native opacity or animation is substituted.

This module is additive. `PCXImageRuntime` remains unfinished and is neither compiled nor retried by this task. Physical file/resource acquisition, PCX surface creation, DirectDraw locks/unlocks, palette effects, optional table construction and CString transport are exact addressed dependencies. Those services must report actual results; this module does not make a device or missing source callee succeed.

## Original identity and entries

Original `Original/claw10/CLAW.EXE` SHA256 is `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private Ghidra and instruction notes are under `work/paper-roll-agent`; no shared analysis project is modified.

| Entry | Source interface |
| --- | --- |
| `48f500` | owner, `(duration)`, RET4: capture and roll up |
| `48f740` | owner, `(screenName,grayscale,paletteFadeDuration,initialWait,rollDuration)`, RET20 |
| `42a4f0` | application, no args: readiness-gated cached roller table |
| `4ecb40` | constructor of 52-byte descriptor; preserves words11/12 |
| `4ec050` | fade manager, `(type,descriptorOr0)`, RET8; **only type0** in this module |
| `4ee880` | 1172-byte fader constructor |
| `4ee8c0` / `4ee8e0` | deleting `(flags)` / base destructor |
| `4ee9a0` | fader, `(descriptor)`, RET4: geometry/tables/row offsets |
| `4eecc0` | fader, `(step)`, RET4: whole lock/draw/store/unlock |
| `4ef010` / `4ef7d0` | curved / straight strip, `(position,delta)`, RET8 |
| `4efac0` | fader, no args: maximum progress |

Vtable `514270` is `[4ee8c0,4eecc0,4efac0,4c96b0,4c96b0]`; the two no-ops retain their original dispatch identities. A public unknown entry returns unsupported without changing the result. Meaningful return values are distinct from the supported/safe flag; original incidental EAX from void methods is excluded.

## Native graph and scratch recipe

Use a `ClawPaperRollContext` with the same `ClawPlayerFadeBlendContext` and raw `ClawSceneActorHost` as existing fades. Provide **separate** caller-owned 52-byte descriptor, 64-byte name buffer, four-byte lookup output, and four-byte by-value CString storage. These represent synchronous original stack locals and do not establish source heap identity. The frozen circle descriptor is only36 bytes and must not be reused as a52-byte allocation. Provide pointers to live original sound gate `532c0c` and volume `532c10`; bypass remains the shared `537238` alias in the common fade context.

An optional exact-byte lookup handles non-word-sized physical pixels/scratch. Without it the existing word lookup must cover rounded containing words; callers must not conceal missing physical storage. A zero `maximumOperations` permits64 million native loop operations; common `maximumClockReads` is still independently enforced. These diagnostics stop unsafe/stalled prefixes and are not original safe returns.

The owner graph is `owner+c` scene, `scene+4` holder, `holder+10` primary wrapper, `wrapper+2c` primary surface. `scene+1c` is graphics, `owner+10` fade manager, `owner+8` resource namespace, `owner+20` screen namespace, `scene+18` palette controller and `scene+28` sound registry. Raw surface height is `+14`, width `+18`, pitch `+1c`, pixel depth `+a4`, and bytes per pixel `+ac`.

`owner+3c` is the created capture/screen surface; `owner+40` is cached PAPER surface; `owner+2c` is cached screen palette. Both wrappers require PAPER dimensions to equal the initially captured target dimensions. They create a descriptor with target/source/paper, radius40, roller mode3, direction0 for rollup or1 for unroll, and the optional `42a4f0` table. The source runner is **`4ec9c0(effect,duration,initialWait,0)`**. Its third argument is zero in both wrappers.

`42a4f0` checks application virtual+c readiness, `app+58` manager, and `app+8c` cache. With no cache it looks up `STATES_ROLLER_PALETTES_ROLLER` through `app+34`, acquires bytes, calls frozen light-table `4c7360(manager,bytes,resource+14)`, stores `app+8c`, releases the resource and returns the reread cache. Hosts may compose that frozen loader in the dependency callback.

## Source ordering and ownership

Rollup creates `4bc670(graphics,width,height,8,800,FFFFFFFF)`, stores it in `owner+3c`, and accepts `4b9c50(capture,target)` only when its HRESULT is zero. Unroll formats `_SCREENS_%s`, finds a PCX, creates its surface and optionally loads its palette. The source does **not** release the locked PCX resource after a failed screen surface or palette creation. These prefixes are preserved, without invented recovery.

Both load PAPER through `4b7f00`, `4b61c0`, `4bc520(graphics,data,2,length,800,FFFFFFFF)`, and `4b6230`. In the normal path they pause music, elect `ROLLUP`/`UNROLL`/`DELAYUNROLL` sound under original gates, run the fader, resume, remove/delete the fader, delete `owner+3c`, clear that field and destroy the descriptor CString. Bypass uses original wait and clear/copy distinctions. Factory failure destroys the local CString but leaves created/cached surfaces intact.

The type0 factory allocates exactly`0x494`, runs constructor and common binders, initializes a supplied or local descriptor, appends to the source pointer array on success, and performs original diagnostic/deleting dispatch on failed initialization. Allocation failure can reach an unchecked null store; the native missing-span fault preserves that prefix.

The destructor frees nonzero `+478,+44,+48,+4c,+488,+48c` in that order **without clearing those fields**, then composes common table cleanup. Repeat deletion of such an object is not made safe by zeroing or fabricated ownership. Supplied lighting tables are borrowed: initializer sets `+30=0`. Other table paths retain their actual `4f2190`, by-value CString, `4c7180` or `4c62e0` calls and remain explicit dependencies.

## Pixel behavior

The initializer requires equal target/source/paper dimensions and mode1..3. It creates `2*radius` signed curve offsets using original CRT acos and float-radius conversion. The immutable width/threshold constant is double **3.14159**, rather than exact pi. Lighting shade bytes use source float **3.140000104904175** and double **-32**: `16-lowByte(ftol(sin(angle)*-32))`. The supplied roller table is a three-word object with its payload at+8, indexed as `paperIndex*64+shade`.

Both finite pixel bodies retain source byte order, scratch writes, direction-specific clear/copy regions and row padding. Forward copies preserve aliases. Mode3 temporarily becomes mode1/2 for two strips and returns to3. First rollup step0 copies the lesser target/source pitch, not merely visible width. Repeated/reversed steps still lock/store/unlock while nonpositive delta avoids strip writes. Four-byte unlit pixels intentionally leave strip scratch unpopulated while still copying it; that measured source behavior is not repaired.

There is no clipping API: source positions and row pointers must supply the physical capacity elected by the original loops. Missing spans stop a native prefix; they do not represent an original clipping branch or success.

## Validation

Run `work/test-env/bin/python Tests/compare_paper_roll_runtime.py`, then `work/test-env/bin/python work/paper-roll-agent/checks.py`. Final measured counts and resource hashes are recorded in `work/paper-roll-agent/verification.json` and the logs after validation.

The oracle executes the unchanged original bodies and compares complete heap/global bytes, meaningful EAX, original RET arity, ordered callback snapshots and freed-token history. CString/local transport locations are normalized explicitly. Actual PAPER/CREDITS pixel inputs are read-only prior original captures from the unfinished PCX work; no PCX codec is invoked. The actual ROLLER.CLT payload and full640x480 source pixel progression are exercised. This establishes the finite paper effect and wrapper behavior, not full-game or physical presentation acceptance.

Final frozen evidence: **1,320 paired whole original calls,6,789 ordered full snapshot pairs,2 unsafe prefixes,2,639 instrumented original `.text` addresses and2,647 total instrumented addresses**. Strict C11 import, C++17 warnings-as-errors, Swift C11 import (64-byte native context), and **12 exact-allocation ASAN/UBSAN whole pixel replays** pass. The sanitizer replays cover mode1/3, direction0/1 and1/3/4-byte output, with exact1172-byte fader,188-byte surfaces, row arrays, curve/shade/scratch, table and physical pixel spans. They do not claim whole physical-device lifecycle or ASAN coverage of every wrapper service.

The actual640×480 resource cases use already captured source-decoded PAPER/CREDITS pixels and retail ROLLER.CLT. Their whole-fader progression is measured, while the joined wrapper success/failure and repeated-clock runner cases use smaller generated physical surfaces. No joined full retail PCX loading or complete Credits screen/device acceptance is claimed. Optional fallback table builders `4c7180/4c62e0`, formatter `4a3920`, palette fade/grayscale and physical resource/surface/clock/audio transport remain addressed callee boundaries; caller ordering is recovered and tested where stated, but those delegated bodies are not claimed as recovered by this module.
# Root acceptance

Root independently reran the unchanged-original oracle and strict/sanitizer
checks, both exiting0:1320 whole calls,6789 ordered snapshots,two unsafe prefixes
and12 exact-size ASAN/UBSAN pixel replays. This family is accepted as source-only;
native Credits/menu transitions and PCX transport remain pending.

