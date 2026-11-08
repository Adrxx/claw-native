# RatBomb original v1.0 recovery

`LogicRegistry` verifies RatBomb ordinal28, name address522d1c, callback47d7d0, flags0. This module recovers that entire callback, constructor, two registered state overrides, the projectile base it actually uses, and its destructor. Source authority is original `CLAW.EXE` SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`; independent decompilation and boundary evidence are in `work/rat-bomb-agent/`. No reference gameplay was copied.

## API / represented storage

`RatBombLogic.h` aliases the existing `ClawGenericEnemy` snapshot to simplify host transfer from Rat's projectile views. Actor128, primary93, secondary93 and contact93 retain the existing raw-token convention. **RatBomb allocates170 bytes /92 private words.** Only enemy0..91 represent that allocation. Wider enemy92..263 are portable storage, preserved through calls and included in test snapshots to catch accidental writes.

Context embeds `ClawGenericEnemyContext` first, keeping the existing rich dependency ABI. Its tail supplies sequenceRegistryToken, original float damageScale5262b0, image manager min/max/minimum selected image token and header, audio enabled/master volume and the bounce/explosion sound pool tokens. Defaults copy original common globals, the12-slot RatBomb vtable and damageScale1.0, preserving caller identity/state/resource fields. Fault1 reports failed allocation; fault3 reports missing resolved supported state scope. Original allocation failure dereferences null and has no normal return; the native fault is explicitly an extension.

`claw_rat_bomb_construct` is47d890, `claw_rat_bomb_tick` is47d7d0, and `claw_rat_bomb_entry` invokes covered original entries by identity. Entry returns covered1, writing scalar EAX to result; void entries produce0. Unknown entries return0 without replacement mechanics. Existing Rat actor/enemy word accessors can also be used because their aliased snapshot types are identical.

Shared frozen `PlayerPhysics` and `GenericEnemy` implement actual physics/motion4dca10, captured-state FSM4dc870, and queued post4063b0. The common APIs' CEnemy bitset validity word2fc lies outside RatBomb. A scoped native guard permits their reuse; every external callback sees the original preserved portable tail, and its mutations survive. The guard itself is never exposed as an original RatBomb field.

## Original control flow

| Entry | Behavior |
| --- | --- |
| 47d7d0 | State0 sets1000, allocates170, constructs, invokes virtual10 and stores primary18 afterward. State29 virtual20 and30 virtual1c are actual no-ops. State1000 waits. Other states run shared FSM. Normal return1. |
| 473c50 | Complete shared projectile constructor: base pointers/LogicHit+LogicAttack binding, embedded physics, first collision, actor flags40/20, render2000, animation flag148=0, and all three position bounds restored to original globals. |
| 47d890 | RatBomb constructor/resources/minimum image/hit rectangle, type40, temporary bbox(-10,-200,10,20), actor flags4/80, damage15 scaled, depth4990 only if previous depth0. |
| 4741f0 | Initial image-derived bounding+attack rectangles replace temporary bbox, then virtual28 activates the bomb. |
| 47e050 | Activation chooses FALL for zero X velocity or unordered NaN (original x87 C3 test); otherwise FALLEASTWEST. Positive velocity mirrors wrapper rectangle and all three actor rectangles when render2 wasn't set. ANI updates immediately, then captures previous state, looks up LS_FALLING and writes actor mode8. |
| 47db20 | RatBomb override lookup: LS_FALLING47e180, LS_EXPLODING47dfc0; other entries route actual projectile base473f40. |
| 473f40 /4742f0 | Base state lookup/assertion boundary and original base falling updater: animation only when148 nonzero, collision10000 sets actor deletion flag10000. |
| 47e180 | Updates ANI, then invokes explosion separately for mode1 and collision bit10000. **Both conditions can call explosion twice**; don't combine them. |
| 47df20 | Explosion entry captures previous state, looks up LS_EXPLODING, changes D0 to1000000, selects explosion ANI, stops physics (privateC8=1), optionally plays sound, clears private168. |
| 47dfc0 | Sets actor80 before ANI update. First marker1 sets168, inflates attack rectangle40 in both axes and clears80 for that update. Later calls set80 again. Animation completion (`1a4!=0 &&19c==0`) marks actor10000 for removal. |
| 47e1d0 /406240 | Exact minimum image selection and image-derived hit rectangle. |
| 406150 /406180 | Exact hit/attack rectangle mirror helpers with INT_MIN guard. |
| 4c9e30 /4c96b0 /4bb030 | Actual trivial pre/no-op/return0 methods. |
| 484d90 /456030 | Actual destructor: vtable becomes50b014, then optional free4f6428 when flags byte bit1 set; returns allocation token. No invented body cleanup. |

The original projectile-specific registrations are names LS_FALLING and LS_EXPLODING; IDs are assigned by runtime registration. The test supplies an explicit resolved name/storage profile. No full retail boot ordering or error/default dictionary implementation is claimed. Constructor does not call registration itself; its name lookup requires a host-provided original profile.

## Resources / explicit services

The rich callback logs original function, receiver, ordered arguments and name; it may change complete snapshots synchronously. `4f6286` follows the frozen GenericEnemy convention: callback result is its resolved out token, rather than the original function's boolean EAX.

- Allocation4f63ec cdecl `[170]`; free4f6428 cdecl `[enemyToken]`. Native storage lifetime is host-owned.
- Common LogicHit4c7fa0 /LogicAttack4c8060 secondary/contact binding. Tests execute actual original binder with explicit missing-metadata lookup, rather than assuming unobserved logic objects.
- Bitmap4c7970(actor,"LEVEL_RATBOMB") is requested only if actor170 was0. Callback supplies manager/image views.
- Sequence dictionary+10 requests LEVEL_RATBOMB_FALL, LEVEL_RATBOMB_FALLEASTWEST, LEVEL_RATBOMB_EXPLODE, LEVEL_RATBOMB_BOUNCE. **There is no GAME_NULL fallback** in this constructor.
- Sound dictionary+10 requests GAME_BOINKJR, GAME_BOMBEXP. Bounce sound is stored but no RatBomb bounce state is registered. Explosion uses4b45f0(explosion pool,[masterVolume,0,0,0]) only with nonzero resolved token and enabled532c0c. masterVolume532c10 is overall volume.
- Animation4c8220(actor+188,[sequence]) /4c82a0(actor+188,[animationDelta5430c4]); callbacks can route to recovered AnimationEngine. Activation consumes an immediate update, unlike deferred selection.
- Collision4cbb60(tileManager,[actor,newX,newY,options]) is the recovered common motion service. Tests execute original and native CollisionResponse against original CD tile descriptions/cells during flight histories. Absolute tick537210 controls physics, independently from ANI delta.
- State4dba00(537668,name) is explicit resolved registry lookup, or the supplied named table if no callback exists. Missing base state function goes to the exact4a36f0 assertion boundary, not a guessed state.
- The intrinsic Win32 InflateRect is represented by exact wrapping rectangle side effects; its unused BOOL return isn't a gameplay service.
- Rat's object-manager4c8da0 remains an explicit creation service. Joined tests actually execute whole original Rat47d660 and its real call into original RatBomb47d7d0. The service supplies the new generic actor/primary graph, while both initializer and activation bodies execute genuinely in original and native paths.

Rat calls the initializer before writing launch values. Its south payload is velocityX0, velocityY250, accelerationY1500; east/west payloads are velocityX±500, velocityY0, accelerationY0. Then it activates again. RatBomb's own constructor supplies no gravity; don't replace these payloads with the shared enemy gravity2000. Creation and animation callbacks are allowed to mutate the graph in between, and the code preserves their ordering.

The actor10000 deletion request and destructor are recovered; scene collection timing and object-manager lifetime are separate host services. Collision fixtures for horizontal contact are explicitly distinguished from real tile impacts. Full scene combat, animation assets and rendering equivalence are not established by this module.

## Verification

`work/test-env/bin/python Tests/compare_rat_bomb_logic.py` compiles its own optimized dylib (`-O2 -Wall -Wextra -Werror -ffp-contract=off`) and compares hash-pinned original i386/53-bit x87 execution. Every call asserts original SEH FS:[0] restoration.

Final suite passes4360 complete original calls,9896 ordered full-snapshot events,2527 original instruction addresses:

- 1500 generated routine calls across15 original entries, including full constructor/wrapper/destructor.
- 106 directed zero/NaN velocity/mirror/sentinel/image-range/scaled-damage/depth/double-impact/marker/overflow checks.
- 1584 retained initializer→launch→flight→impact/explosion/completion calls against original CD Level1 tile data, with contact fixtures declared.
- 18 whole Rat47d660→real RatBomb initializer→payload/activation comparisons, followed by1152 retained flight/impact/explosion calls. Both full Rat and bomb actor/logic/private graphs are compared at ordered boundaries.240 south-throw frames enter explosion automatically through true tile collision; horizontal contact is injected explicitly.

Private helpers are only `Tests/rat_bomb_helpers.py` and `Tests/rat_bomb_throw_helpers.py`; they don't import older worker harnesses or write older workers' libraries. Image/audio/object resource bodies stay documented adapters; this evidence does not imply full-game identity.
