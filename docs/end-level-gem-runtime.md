# Original EndLevelGem and EndOfLevelPowerup

This additive module recovers the original dynamic boss gem, its embedded physics/controller, the ordinary end-of-level pickup callback, and the player restoration used during the transition. It requests the original end-level command. A request does not establish that the later scene transition or complete original single-player game is implemented.

Original executable SHA256: `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Archive SHA256: `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`. Source evidence is bounded disassembly and private Ghidra output under `work/end-level-gem-agent`. No CrazyHook or reference gameplay implementation is used.

## Registry and actual world scope

The original logic registry contains `EndLevelGem` at ordinal78, literal522aac, callback43ca60, flags0; `EndOfLevelPowerup` at ordinal106, literal52293c, callback4701b0, flags2. The first is dynamic-only in the14 extracted retail worlds: zero EndLevelGem records among34,784 records. The second has five records, in levels3,5,7,9,11. `inventory.py` retains their complete71-word records, four strings, plane/index/offset, and decoded-world hashes. These records initially use GAME_MAPPIECE. Dynamic boss gems use loot index31 and LEVEL_GEM, with the ordinary callback selecting GAME_MAPPIECE, LEVEL_GEM, or GAME_CHECKEDFLAG according to original mode/configuration/saved-file checks.

The retail archive is an input fixture. Its exact identity relative to every asset originally shipped with the pinned v1.0 executable remains a separate question. This module does not claim asset identity from successful format decoding.

## Entry and allocation contract

`Sources/EndLevelGemRuntime.h` is a C11 raw-token API. Tokens are original32-bit identities. Caller-owned `ClawSceneActorHost` resolves spans and supplies allocation/free/services. `entry` returns support separately from `context.fault`; fault0 is required for completion. Fault1 is a missing span/service, fault2 is an invalid argument count, missing supplied state, or bounded traversal rejection. These checked stops are native extensions. Unsafe original prefixes are compared only up to their first unchecked dereference.

| Source identity | Original ABI | Native scope |
| --- | --- | --- |
|40e5c0|ECX boss private, no stack args|Whole dynamic creator orchestration; requires boss storage through45f|
|43ca60|cdecl(actor)|Whole registered wrapper and0/29/30/1000/controller branches|
|43cb20|ECX private, actor arg, RET4|Whole0x150-byte/84-word gem constructor|
|4082f0|ECX private, actor arg, RET4|Whole shared base stores and exact logic binding services|
|43cdc0|ECX private, state arg, RET4|Whole class-function dispatch including range/error/fallback branches|
|43d070|ECX private, no args|Whole LS_IDLE forced-camera and landing/rebind controller; EAX0|
|43d0f0|ECX private, targetX/targetY, RET8|Whole inline targeting calculation and zero-target restore/rebind order|
|4205b0|cdecl(), no args|Whole guarded state5010 player restoration|
|4701b0|cdecl(actor)|Whole EndOfLevelPowerup startup/update/cleanup callback; EAX1|
|4dc870|cdecl(private)|Frozen common FSM composition plus original raw ID-name lookup bookkeeping|
|4dca10|ECX private, no args|Frozen common physics/movement body composition|
|4063b0|ECX private, unused name arg, RET4|Frozen queued callback/post/motion composition|
|484d90/456030|ECX private, deleting flag RET4 / no args|Frozen actual base/deleting lifecycle; no generic264-word destructor|
|4c9e30/4c96b0/4bb030|ECX private, unused arg RET4 / no args / no args|Verified source no-ops|
|4719e0|cdecl(scene)|Frozen original WorldLoot initializer composition|

The original private object is exactly84 words. Its vtable is50db2c with ten entries:
`484d90,4c9e30,43cdc0,4063b0,4c96b0,4bb030,4bb030,4c96b0,4c96b0,4dca10`.
The physics/base stage uses50b2a4, whose slot8 is4041a0 instead of43cdc0. The common portable object is264 words internally, but the raw bridge reads/writes only84 private words and109 actor words (actual animated actor1b4 bytes), plus93 primary-logic words. Unused portable private tail is zero and is never committed to heap. The inherited deleting wrapper only writes50b014 and optionally frees the real private token.

`award(item)` composes frozen CaptainClawHit and the frozen PowerupObject selector for exact item type100/value26ad. Original hit election and actor+74 binding remain ActorInteractions-owned. This frozen pickup composition currently needs the existing portable128-word player/item backing profile; that extra backing is not an assertion that original animated actors allocate512 bytes. Borrowed pickup host identity is restored after the synchronous call.

## Integration object graph

1. Supply the real scene, actor,93-word primary logic and84-word allocation. Actor+c is the scene, actor+6c the primary. Scene+24 is the world used as the collision receiver. Set the common context's `tileManagerToken` to that world, not its main-plane token.
2. Bind `loot` to the synchronized original WorldLoot views:341 words537ec8..53841b, itemCount52a190, audioVolume532c10, highLaunch53721c, and configurationWord = first word through the pointer at537960. Index31's metadata+10 must be4701b0. Its name token is image-root+0x24. Do not initialize unrelated resource words by guesswork.
3. Initialize/bootstrap the frozen LogicStateRegistry. Its original constructor profile includes43cd60/table537608; the existing bootstrap registers EndLevelGem and LS_IDLE→43d070. Supply actual ID/name/function views in the common context and synchronize the corresponding raw tables537608/537668/537698. The suite's original bootstrap profile resolves LS_IDLE to2000; the API does not hardcode that as a universal ID. The allocated ID-name CString identity differs from the source name literal.
4. Raw globals used by this graph are537210 tick,537e88 player,5371fc application,537204 input,532c0c audio gate,532c10 volume,52be14/18 forced camera,534e60[6] physics remainder words, and5430c4 animation delta. Application+2c supplies the real config virtual+10 mode, config+14 supplies level/config bits, app+c0 is a CString data token with length at data−8, and app+124 gates glitter creation. Keep these live aliases synchronized during services.
5. For boss creation, provide private+c and+12c actor aliases, +130 primary, +458 optional sound resource and+45c latch. The source initially reads position/Z through+12c, follows +130→primary+c→scene+8 for the container, creates flags40000, invokes new primary+10 immediately, then rereads private+c for actor+148/+14c target fields. Those aliases may change in callbacks. The latch is set before creation and is not cleared on failed creation.
6. Constructor defaults/limits come from the pinned original: minimum−2147483647, maximum2147483646, maximum movement delta24, accelerationY100, original unsigned tick×.001. Original motion runs before the wrapper aliases128/12c/130 are stored. Preserve allocator-seeded unwritten fields; a native zero allocator is a declared allocation profile, not the original heap identity.
7. For restoration, use the live player's78-word private buffer via primary+14. Source guards actor/primary and state5010. It clears two input bits, handles attached-child cleanup, restores saved ANI if present, selects CLAW_STAND, sets state24 and original motion/hit/move rectangles/timers/remainders. Child helpers421010/420fc0 and the facing0 move-rectangle helper40f6c0 retain exact service identities.

Composition flags default to1. Creation1 composes frozen SceneActorRuntime; creation0 exports exact4c8da0 six-argument calls. Animation1 composes frozen ActorAnimationRuntime/AnimationEngine; animation0 exposes the exact selection/update identity. Common1 composes frozen FSM/post/motion; common0 exposes those exact entries. Loot1 composes frozen initialize/name/rebind; loot0 exposes473630/473660/4719e0. The whole-call suite intentionally uses creation0 for an explicit scene-factory boundary, common1 and loot1, and both animation0 and animation1 with real source-decoded ANI. Independent frozen creator validation and native scene integration remain parent-owned.

## Exact source behavior

The dynamic gem is not an immediate pickup. Its controller publishes truncated physics X/Y to the forced-camera globals. Only when Y velocity is positive and positionY exceeds signed targetY does it set stopped, clear actorflag1, restore player control, rebind loot31, then reset both forced-camera words toFFFFFFFF. A zero target invokes restore/rebind before storing target words and calculating velocities.

43d0f0 is a distinct inline specialization of the frozen targeting helper. It uses unary negative positionZ, preserving negative zero. Original x87 instruction order sums squares X,Y,Z; the decompiler expression reverses that visually. Tests caught the difference at the byte level. Native operations round individually with FMA disabled. Finite generated3D/tiny acceleration/extreme signed-coordinate profiles are tested. This is not a claim of every NaN/exceptional CRT numeric profile.

The ordinary callback initializes sound/animation/image/Z/attack rectangle, scans the initialized loot table, then always overrides value to26ad and interaction type to100. Glitter is created with flags240000, selected GAME_CYCLE50, and bound GAME_GREENGLITTER. State5 updates ANI. State29 only marks the glitter for deletion. The cached initial primary is used for the final state5 store even if a resource service changes actor+6c.

The award sends the original WM_COMMAND800e request, sets primary+24=2, resolves/plays the GAME_MAPPIECE sound and its source duration transport, applies the original mode4/config score bonus, and marks the item for deletion. No additional success, transition timing, invented scene fade, reward, radius or lifetime is added.

## Explicit services and limits

Resource/image bindings4c7fa0/4c8060/4c7970, state-name lookup4dba00, original CString buffer lookup4f6974/construction4f6439, registry growth/error4db6e0/4db5f0/4db4d0, collision4cbb60, optional sound4b45f0, attached-child421010/420fc0, facing0 rectangle40f6c0, physical PostMessage and duration transport remain exact-address dependencies. Their other frozen modules can be composed by the native host. The tested collision adapter commits supplied coordinates and optionally corrected positions; it does not claim complete world collision here. Source window/file/device/COM lifetimes remain separate.

The raw common-name adapter is verified for the real ten-slot gem vtable, including growth/pending CString cells, class growth and error fallback. Arbitrarily replacing all vtable functions while retaining a different common actor profile is not covered. Invalid raw pointers, insufficient backing, counts beyond bounded spans, or unknown state views stop checked native execution; the original often dereferences unchecked. Source unsafe-prefix comparisons preserve already committed state without pretending normal returns.

## Verification

Run `work/test-env/bin/python Tests/compare_end_level_gem_runtime.py`. It verifies the unchanged executable hash, executes whole roots and supported original descendants with the original CRT53-bit precision, compares a complete1MiB heap and320KiB original image/global view, ordered snapshots at exact service boundaries, meaningful EAX and source stack-pop behavior. It covers creator→init→target→retained physics/FSM→landing→rebind, mode/config/image/missing/glitter branches, all five real WWD pickup profiles, source4d76e0-decoded GAME_POWERUP records, actual map-fragment image IDs, retained ANI steps, actual41ce80 award→800e, whole first-use WorldLoot initialization, cached/fresh callback aliases, registry range/error/growth, no-op/reset/destructor and two stopped unsafe prefixes.

Final evidence:5,719 paired whole-call comparisons (11,438 native/original invocations),11,600 paired ordered complete snapshots,3,532 original instruction addresses,20 source-decoded ANI records, five actual WWD placements, and two stopped unsafe prefixes. `work/end-level-gem-agent/verification.json` and `verify.log` retain the measured evidence. Counts distinguish paired comparisons from both native/original invocations. `work/end-level-gem-agent/smoke.py` runs strictC11 import, standalone Swift import/link, and ASAN/UBSAN with200 exact-sized native constructor/target/motion/landing/rebind/destructor histories. These are source/runtime checks, not Mac/iPad end-to-end acceptance or whole-game equivalence.
