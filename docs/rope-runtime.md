# Original AniRope runtime

This additive module recovers the original v1.0 **AniRope** actor family and the bounded Captain Claw contact/swing/release graph. The executable is SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Original-disc resources come from CLAW.REZ SHA-256 `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`. It does not establish complete gameplay parity or add native scene registration.

## Identity, allocation, and source entry map

The source registry identity is `AniRope`, ID51, literal `522bf8`, callback `403100`, registration flags0. Images or scenery with rope names are not evidence of this controller. The original private allocation is **328 bytes / 82 words**, not an inferred physics prefix. The complete 240-byte embedded physics object begins at private+48. The final four private words are frame138, foldedIndex13c, grabOffsetX140, grabOffsetY144.

| Entry | Actual ABI and behavior |
| --- | --- |
| `403100` | cdecl(actor); initial allocation/construction, ordinary controller dispatch, deletion-state virtual callbacks. Returns1. |
| `4031c0` | thiscall(private, actor); complete constructor, resource binders, default depth/period, physics rate/phase, and initial state. Returnsprivate. |
| `4035a0` | thiscall(private, stateID); two original class-array selections, diagnostic/default-cell and null-function RTTI paths. Source void. |
| `403850` | thiscall(private, unusedNameToken); queued transition/cleanup callbacks, then embedded physics update. Source void. |
| `4038d0` | private receiver; frame/geometry, attached-player facing, indexed image selection. Returns0. |
| `465450` | private receiver; saves previous state, resolves `LS_IDLE`, publishes state. Returns0. |
| `403ab0`, `403ac0` | private receiver; raw actor position plus source grab offsets. Return wrapped32-bit coordinate. |
| `4181c0` | cdecl(player, primary, private); player swing update and pressed-bit1 jump release. Source void. |
| `41ee60` | cdecl(player, primary, private, electedRope); composes frozen PowerupObject selector, restricted to rope26af. Source void. |
| `41ce80` | cdecl(player); whole elected CaptainClawHit for attacker type100/fc26af through frozen award/selector. Meaningful source result. |
| `415df0` | cdecl(player), only initial5007; swing helper followed by unchanged public PlayerInputDispatch epilogue. Returns1. Other initial states return unsupported without writes. |
| `4dc870` | cdecl(private); composes frozen registered actor dispatcher. |

Vtable50b03c first9 slots are `484d90,4c9e30,4035a0,403850,4c96b0,4bb030,4bb030,4c96b0,4c96b0`. Source startup, state29/30 callbacks are empty4c96b0; freeing private memory occurs through the scalar-delete lifecycle484d90, composed from frozen StackedActorLifecycleRuntime. Original x86 SEH stack bookkeeping is a host runtime boundary, not a modeled heap field.

## Motion, geometry, and player ordering

Constructor writes `LEVEL_ROPE` through4c7970. Depth becomes3990 and flag20000 is added only when depth was0; actor+148 becomes1500 only when0. Type100 and subtype26af are source stores. The period is signed, rate is integer `60000 / period`, and phase uses wrapped32-bit `primary+bc * rate`, interpreted signed before integer division1000. Negative periods are preserved. No fixed timestep, sinusoid, inferred pendulum, or duration replaces these operations.

The controller converts physics.positionX with the original ftol low-word behavior, uses signed remainder120 plus1, folds frames61..120 to1..60, and uses the immutable original61-pair table522f08. Its stores update the raw actor attack rectangle and private grab offsets. If global player's private134 references this actor and its state is5007, it composes frozen418080/418120 facing. Image selection uses the frozen ActorWrapper4209d0 signed range/gap behavior.

The generic source controller invokes geometry **before** post403850 advances physics. Post delta is `double(unsigned tick537210)*.001 - physics.elapsed`; it is distinct from animation and stage deltas. Changing that ordering shifts the visible rope frame and attachment point. The raw source does not issue tile collision queries here.

The frozen rope grab branch accepts player motion3/4 and its source wrapped absolute-distance predicate, blocks same-rope regrab while cooldownprivate11c is nonzero, cleans held movement, selects CLAW_SWING, writes5007/motion8 and private134, places the player at getters±8/+20, and clears shared player physics remainders. Contact election and actor+74 publication remain outside this module.

Swing4181c0 updates ANI first, rereads live rope/private identities, and follows getter positions. Only pressed input+4 bit1 initiates release: cooldown500, two latched-input stores, optional held target queue421010 and bit420fc0, saved-animation cleanup, state4/CLAW_JUMP/motion3/rectangle stores and shared player jump physics. Private134 remains the rope identity. The common415df0 tail then decrements cooldown using **stage** delta; the retained18ms profile ends with482. Animation delta remains a separate alias. The source caller supplies an unused second private argument to4170b0; composition normalizes its actually used one-argument frozen helper ABI.

## Native integration recipe

Use `ClawRopeContext` with a live `ClawSceneActorHost`. Allocator/resource/registry/audio transports are rich `ClawRopeDependency` calls carrying actual function, receiver, raw arguments and optional literal-name hint. Preserve heap identities and the source class table534820/ID-name array537698/CString arena. The `LS_IDLE` name obtained from full401000 is an allocated CString token, distinct from its literal523148; equality must not be substituted by text or literal tokens.

Publish these live aliases into `ClawRopeGlobals`:

| Original address | Context alias |
| --- | --- |
| `537e88` | playerToken |
| `537210` | tick |
| `53720c` | stageDelta |
| `537230`, `537214` | ignoreHazards, cheat |
| `544e8c` | pixelScratch |
| `513e10..513e1f` | physicsDefaults[4] |

`claw_rope_defaults` copies only the four pinned default double halves. Player paths borrow the existing PowerupObject context: inputToken537204, animation delta5430c4/audioPosition532c10, PlayerPowerup globals534eac/ea8/eb8 etc., full shared534db8 player physics, and ItemPickup player identities for CaptainClawHit. The source rope uses no random draw. Optional LiftThrow context composes held cleanup/queue/bitset; otherwise those exact address services must be supplied. Its live input/clock/powerup aliases are synchronized at nested dependency boundaries. Temporary borrowed host adapters are restored before return.

For scene registration, allocate all82 words and dispatch the source actor callback; do not force a private constructor flag or startup state. Register an actor component before callbacks, map the original class/name state arenas, preserve source generic scheduling, and route elected CaptainClawHit/initial5007 player update through the bounded public entries. Ordinary states remain the existing player dispatcher’s responsibility.

Fault1 is missing span/service; fault2 is argument/profile/table domain safety; fault3 is missing required composition. A null allocator preserves the initial primary1000 write and allocation call before the source's null vtable access. A negative table index outside0..60 preserves source frame/index stores before stopping at the unsafe read. These are explicitly guarded original prefixes, not claimed successful original lifetimes. Unsupported category/state entries preserve caller state/result.

## Retail inventory and verification

`work/rope-agent/wwd-profile.json` captures the original raw71-word WWD records, strings and per-record/world hashes across all14 worlds. AniRope counts: Level3=9, Level6=15, Level8=29, Level9=26, Level10=27, Level13=22, Level14=9; all other levels, including Level1, have0. Each used level contains120 original rope PID images, 840 captured headers/hashes total. Level3’s image11 is actually named `FRAME11.PID`; its numeric ID is preserved without renaming the file.

`Tests/compare_rope_runtime.py` executes whole original instructions and compares complete512KiB heap +192KiB global snapshots, ordered service snapshots, and meaningful EAX. Padding/unwritten fields are retained. The floating-point oracle uses the original CRT initialization to53-bit precision. Real401000 state/class fixture uses the frozen registry module's raw CString arena, with physical allocation policy explicit. Original WWD parsing composes frozen WorldObject loader with explicit metadata/resource transport; its independent frozen original evidence is not rerun or newly claimed here.

All137 actual WWD profiles retain startup→unheld actor frames→synthetically elected source grab→source rope/player swing→jump release→same-rope cooldown→private destruction. Actual PID headers feed frozen SpriteGeometry. Additional histories compose real SWING/JUMP ANI (4/27 records), each record decoded and compared with original4d76e0, and real player PID tokens. They use separate35ms animation/17ms stage deltas. Held-target cleanup, signed periods/wrapped phase, unsigned tick endpoints, full frame/reflection/getter branches, diagnostics and exact null/unsafe prefixes are covered.

Final evidence: **4,041 whole original calls**, **2,615 ordered full snapshots**, **1,712 distinct original executed instruction addresses**, **137 retail retained actor histories**, **496 original ANI record decode calls**, and **3 guarded original prefixes**. Native C++ ASAN/UBSAN replay passes110 original-verified retained calls/73 source boundary events; the Swift ASAN C11 ABI smoke passes. Results are in `work/rope-agent/verification.json`. Run original comparisons with `work/test-env/bin/python Tests/compare_rope_runtime.py`; then run private native checks with `work/test-env/bin/python work/rope-agent/run-sanitizers.py`. The private C++ ASAN/UBSAN replay reuses original-verified raw snapshots and ordered transport mutations; a Swift ASAN smoke compiles the C11 ABI and runs82-word construction/geometry/getters/source clock update.

Physical resource dictionaries, allocation/free, audio, hazard/scene contact election remain transport boundaries. Retained player placement/contact selection is synthetic, not a collision scanner proof; no full level playthrough, pregame schedule, platform renderer/audio output, or whole-game behavior equivalence is claimed. Shared Swift registration/project/device integration remains root-owned.
