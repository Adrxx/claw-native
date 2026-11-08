# Original v1.0 Rat callback and overrides

`Sources/RatLogic.h/.cpp` recovers registered Rat callback `0x47c850`, constructor `0x47c910`, and Rat-specific overrides from hash-pinned `Original/claw10/CLAW.EXE` SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. No reference gameplay implementation was used. Independent Ghidra artifacts/logs live in `work/rat-agent/`; instruction boundaries were checked against original i386 bytes.

## Covered control flow

| Original entry | Native behavior |
| --- | --- |
| 47c850 | Whole registered wrapper: state0 sets1000, allocates420 bytes, constructs, invokes initial virtual10, then stores primary18. State29 invokes virtual20;30 invokes virtual1c;1000 waits; other states execute shared FSM4dc870. Returns1 on original normal-return paths. |
| 47c910 | Shared4332f0 constructor, complete Rat defaults/scales/resources/rectangles/ground ordering. |
| 47cd70 | Four resolved Rat state overrides, otherwise genuine common43d490 dispatch. |
| 47d150 | HOME entry, previous-state capture, horizontal stop, optional GAME_EEHH sound. |
| 47d1b0 | HOME animation update, previous-state-name patrol choice or throw decision. |
| 47d470 /47d490 | Left/right Rat update: throw decision first, then genuine shared43fd10/43fdc0 when no throw. |
| 47d2f0 | Exact throw election, mirror ordering, powerup gating, signed geometry, unsigned cooldown, conditional random draw. |
| 47d4b0 /47d540 /47d5d0 | South/left/right throw entries, state/animation changes and projectile payload. |
| 47d660 | Animation marker, one-time projectile creation/init/velocity writes/activation, wrapping marker counter, completion HOME transition. |
| 47d780 | Player-private repeat-shot election, attacker flags, exact virtual5c argument0. |
| 405000 | Initial attack rectangle copy/mirror. |
| 4357a0 /406310 | Complete wrapper + actor bounding/hit/attack rectangle mirror; actor sentinels preserve INT_MIN, wrapper doesn't. |
| 4c96b0 /4bb030 | Verified trivial no-op /return0 methods. |

Shared pre/post/motion/walk bodies use frozen `GenericEnemy`, including its original captured-state ordering. Uncovered generic virtual/state methods remain dependencies with their actual original addresses; no replacement dynamics were invented. GenericEnemyStates may service those through the existing callback.

## ABI and setup

`ClawRat` aliases `ClawGenericEnemy`: actor128, primary93, secondary93, contact93 and enemy264 raw words. Context starts with `ClawGenericEnemyContext`; callbacks receive this first member and may recover the enclosing Rat context. Use context defaults to copy the original45-slot Rat vtable, common global defaults, and original initial three float scales1.0. This helper preserves identity tokens, state registry, resources and snapshots; caller zeros `fault` and owns all input lifetime.

The represented Rat wrapper aliases its stored actor pointers to the supplied actor; actor6c identifies primary, primary0c identifies scene, and actor74 identifies the supplied attacker. Supply actual player actor/private snapshots, absolute tick537210 and animation delta5430c4 separately. Constructor damage5 and health1 are multiplied as double by the float global5262b0/5262b4; range10 by float5262b8 with unsigned values below100 replaced by99. Preserve original uninitialized allocation words before construction if full-buffer identity is required.

Constructor profile is the frozen shared engine's initial empty534938 bit string and original533470 count32. Raw external backing is supplied for larger runtime bitsets; alternative constructor bit-string parsing remains outside the supported profile. No original difficulty/configuration policy was inferred from the float globals.

Named state tables are caller-supplied and verified, not baked numeric IDs. Four overrides are `LS_HOME`, `LS_MOVINGLEFT`, `LS_MOVINGRIGHT`, `LS_THROWING`. The original shared-only fresh registration profile assigns19 names2000..2018; a subsequent Rat-only new LS_THROWING would be2019. Complete retail boot ordering is not proved. Tests supply this explicit resolved profile plus empty-name default storage for1000. That empty default is a test/host storage profile, not a claim that retail missing-key error-handler initialization was recovered. HOME constructor captures previous1000, so its next update requires the corresponding storage/name profile.

Normal Rat defaults include actor flags OR40 (after common OR80000), D0=4, D4=3000022, depth adjustment5, speed60 only when148 was0, bbox(-10,20,10,33), actorY-32 then original ground placement and mode1. PhysicsY is separately decremented32 before resource callbacks; constructor doesn't synchronize it after ground placement. Shared base gravity is2000. Initial virtual405000 then replaces attack rect with enemy210..21c (normally zero), so standalone constructor and whole wrapper intentionally end with different attack rectangles.

## Explicit service calls

The rich `ClawGenericEnemyCall` preserves original function, receiver, ordered scalar arguments and optional name. All calls are synchronous and may mutate full supplied snapshots.

- `4f63ec`, cdecl `[420]`: returns allocated enemy identity; native allocation storage remains in `ClawRat`.
- `4c7fa0` /`4c8060`: common secondary/contact binding; names LogicHit/LogicAttack. Shared test executes original binder with an explicit missing-metadata resolver profile.
- `4c7970(actor,"LEVEL_RAT")`: image binding, callback updates actor170/174 and image header context.
- `40f680(actor170,[12])`, later `[imageMinimum]`: original indexed image selection; imageMinimum represents manager64.
- `4f6286`: named resolution. As in GenericEnemy, its callback result represents the resolved out token, rather than the original function's boolean EAX. Receiver is `sequenceRegistryToken` for ANI and common soundRegistryToken for audio.
- ANI names: LEVEL_RAT_WALK, LEVEL_RAT_IDLE, LEVEL_RAT_THROWSOUTH, LEVEL_RAT_THROWEASTWEST, LEVEL_RAT_DEAD; each has GAME_NULL fallback. Rat sound names: GAME_EEHH, GAME_MOUSEKILL. Common constructor also requests GAME_SPLASH, GAME_HIT1..4, GAME_PURELEASE1.
- `4dba00(537668,name)`: resolved state ID lookup; no guessed numeric ID. If no callback exists, supplied named table is consulted.
- `4b45f0(soundPoolToken,[masterVolume,0,0,0])`: sound resource+10 contains pool identity; audioManagerAvailable is532c0c. masterVolume is532c10 **overall volume**, correcting earlier portable audioPosition terminology.
- `4c8220(actor+188,[sequence])` and `4c82a0(actor+188,[animationDelta])`: animation selection/updater; marker EAX is consumed exactly. Host uses recovered AnimationEngine.
- `4cda10(tileManager,[actorX,actorY,playerX,32])`: throw eligibility query. Its full EAX truth result is consumed; body remains explicit here.
- `4a3050`: original random return; integer signed remainder rules are retained. Caller may route to recovered LCG.
- `4cd800(tileManager,[actor,0])`: constructor ground placement. `4cbb60` and `4207f0` come from shared motion/post and retain their original argument order.
- `4c8da0(objectManager,[0,x+offsetX,y+offsetY,z-1,522d1c,40000],"RatBomb")`: object creation. Callback supplies projectile token and complete primary/enemy/actor/visual snapshots.
- Created primary10 callback: cdecl `[projectileToken]`, receiver normalized0. It runs **before** Rat writes enemy50 velocityX,58 velocityY,40 gravity. Horizontal bombs also set visualActor164|2020 and clear projectileActor8 bit80. If enemy12c aliases projectileToken, both actor snapshots are synchronized exactly before activation.
- Projectile virtual28: receiver projectileEnemyToken, function projectileActivateFunction, no arguments. RatBomb initialization/lifecycle itself is not recovered by this module.
- `48cf50`, cdecl `[actor]`: state29 destruction/lifecycle request from shared virtual20; engine body explicit.
- Pending generic state/virtual functions are forwarded unchanged, including hurt43f120(argument0/2/3), landing404f00(no arguments), and generic registered strike/death/jump/bounce/etc. Test adapters record exact arguments and full snapshots at these boundaries; they don't claim the body was executed natively.

Native `fault` is an extension:1 allocation failure,2 projectile creation failure,3 missing supported context/registry. Original allocation/creation failures dereference null and don't have normal returns. These native fault paths report missing scope instead of silently inventing successful original behavior.

## Evidence and limits

Run `work/test-env/bin/python Tests/compare_rat_logic.py` (own dylib compiled with `-O2 -Wall -Wextra -Werror -ffp-contract=off`). Hash-pinned original runs real i386 routines and CRT53-bit x87 environment. Original FS:[0] scratch mapping is for SEH emulation; every call asserts its linked-list head is restored.

Final suite compares2527 complete calls,9148 ordered dependency events with full actor/logic/enemy plus attacker/projectile/visual snapshots,3249 original instruction addresses. Includes371 directed mirror/sentinel/float-scale/cooldown/powerup/random/projectile-marker/wrap/alias checks,544 retained initializer→patrol→throw→marker→HOME/shared-FSM chain calls, and all12 actual Level1 Rat WWD records initialized through frozen WorldObjectRuntime. Their original/native ground-placement bodies execute against original CD tile descriptions/cells. Resource/audio/object bodies and unresolved generic families remain explicit adapters; callbacks deliberately mutate projectile buffers to prove initialization/activation order. This does not establish full-game identity or complete enemy combat/asset equivalence.
