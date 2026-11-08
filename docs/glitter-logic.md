# Original glitter controllers

`GlitterLogic` implements whole original registered callbacks `448440` (GlitterMother), `4485a0` (GlitterBaby), and the directly required ordinary-pickup controller `470110` (PowerupGlitter). It composes frozen `SceneActorRuntime`, `ActorResourceBindings` and `ActorAnimationRuntime`; generic cleanup remains `ActorDestruction`. All evidence comes from retail v1.0 `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private Ghidra recovery checked real function boundaries and its logs contain no script error.

## Registered identities and ownership

| Actor | Registration | Literal | Callback | Metadata flags |
| --- | --- | --- | --- | --- |
|GlitterMother|165|5225a0|448440|2|
|GlitterBaby|166|522594|4485a0|2|
|PowerupGlitter|105|522950|470110|2|

All three use generic animated actor allocation `1b4` and primary `174` bytes. None allocates a class private buffer or registers class-specific states/destructors. Mother primary+170 is a raw owner actor identity written by the already-frozen `448400` creator. That wrapper creates `(id1,x100,y100,z0,nameGlitterMother,flags0)`, then writes the owner pointer after a successful creation. This module does not duplicate the frozen wrapper.

Ordinary pickup startup creates **PowerupGlitter**, not GlitterMother. The frozen ItemPickupRuntime owns those callers and their later effect deletion. The proposed address473840 is inside the already-frozen Points wrapper4737c0, not a separate callable entry; no function was recovered there.

## Mother and Baby behavior

Mother state0 waits for nonzero primary.owner170. It then sets primary.state to10, actor.flags8|1 and actor.flags40|1. Other non10 states return1 without effects.

State10 reads the manager pointer from global5371fc and chooses one Baby when manager+124 is zero, otherwise two. That count is captured for the whole emission. For each Baby, it reads the owner's relative rectangle118/11c/120/124 and x/y, calls shared RNG4a3050 twice, and produces coordinates with **signed remainder of a wrapped32-bit inclusive width**. A width of zero uses the random low bit to choose one endpoint. X bounds/origin are captured before the X RNG service. The owner pointer and Y bounds/origin are re-read afterward; owner depth and Mother's parent/container are read after the Y RNG service. The module preserves those asymmetric reads, including mutations at explicit RNG services.

It creates `(id1,x,y,owner.z+1,nameGlitterBaby,flags240020)`. Flags include200000, so the actual scene creator invokes Baby startup immediately **after list insertion and before creation returns**. Null/missing Baby creation is ignored and later emissions continue. After the captured emission count, Mother writes primary+20=15. This is the generic scene callback countdown; no independent timer is invented here.

Mother does not track its babies, inspect owner.Delete/liveness, self-expire or clean itself up automatically. The frozen powerup reset/timer caller controls its Delete flag. Host code must preserve that ownership, rather than adding an inferred orphan cleanup rule.

Baby state0 sets flags8|21, binds image `GAME_SPARKLE` (527a50), selects `GAME_GLITTER1` ANI (527a40, eager0), then stores5 through its previously captured primary pointer. State5 advances ANI with global5430c4. It reads live stopped1a4 and delay19c afterward and sets Delete10000 only for nonzero stopped and zero delay. All states return original EAX1. No guessed TTL, motion or fade is added; the actual six-record GLITTER1 ANI controls the sequence.

## Ordinary pickup glitter

PowerupGlitter state0 zeros captured primary+168, binds `GAME_GLITTER` (52a1a8), and, when actor.depth64 is zero after resource lookup, sets depth1001 and Reorder20000. When the live actor.sequence190 is zero, it selects `GAME_CYCLE100` (5240d8, eager0). It writes captured primary.state5, then shared RNG result signed-remainder251 into captured primary+20. An already selected sequence is retained. State5 only advances ANI; it does not set Delete when ANI is stopped. Other states are no-ops returning1. Pickup award/removal owns the effect lifetime.

## Integration ABI and boundaries

`GlitterLogic.h` is C11-compatible. Invoke `claw_glitter_entry` with one cdecl actor argument for the three registered callbacks. The receiver parameter is ignored for these original cdecl entries. Support is returned separately from meaningful original EAX1. Set context managerToken/animationDelta/audioPosition from original shared globals and clear fault before entry.

With composeCreation1, named creation executes the frozen creator and immediate Baby callback internally. Its host uses the context.scene heap allocator/spans; registry/resource/audio calls use `ClawGlitterDependency`. Resolve actual literal identities through `scene.entry(named:)` and resource registries. A shared RNG4a3050 service must use the same thread-local seed as player/enemy/loot consumers; this module has no independent RNG state. Callback service arguments and receiver/name identities are explicit. With composition disabled, creation and image/ANI services are forwarded with exact arguments for host routing.

With composeAnimation1, image selection uses the frozen image binder and live27-word roots/absolute-index leaf tables; ANI selection/update executes the frozen runtime. Missing image lookup clears root170 and preserves previous image selection. Resource lookup transport adapts original bool/out arguments into a resolved token. Audio remains ordered leaf4c88e0/4208e0 with its exact four arguments. As in the frozen animator, changing actor/record/sequence/image buffers during an audio callback is diagnosed as unsupported; external audio globals may mutate.

Fault1 means missing span/service; fault2 denotes composed allocation/animation failures or original signed-IDIV overflow. These are native safety diagnostics, not original normal returns. Allocation failures in the original fault after visible state/service prefixes; this module does not pretend they returned normally. No image pixels, renderer, DirectSound mixer, Windows TLS allocator or resource registry implementation is duplicated here. Root owns Swift callback registrations and native presentation.

## Verification

Run `work/test-env/bin/python Tests/compare_glitter_logic.py`. Final evidence in `work/glitter-logic-agent/verification.json`: **1,557 whole original calls, 1,459 ordered full524,288-byte heap snapshots, 1,031 original instruction addresses**. Complete heap, manager/animation/audio globals, actor list identities, allocation cursor and callback snapshots agree. Shared RNG executes the actual original4a3050 body with an explicit TLS adapter; native runs the frozen matching LCG. TLS argument/return/full snapshots are compared separately.

Tests include all state gates, enabled/disabled one/two emissions, wrapped/reversed/zero-width rectangles, retained shared RNG and live owner mutations, null/missing metadata creators, resource failures, captured primary rebinding, source depth/sequence gates and random startup delays. Twenty-four retained Mother emissions compose actual scene creation and immediate Baby startup; all36 Babies run real retail GLITTER1 ANI to Delete and then whole generic actor/primary destruction. Eight PowerupGlitter histories run the actual retail CYCLE100 sequence for30 updates without inventing self-deletion. All198 actual ANI record decodes used in fixtures are independently compared with original4d76e0.

Three null-allocation cases compare the full prefix through original actor/primary/list-block faults at4c8d02/4c7e8b/4f5ac1 with null page unmapped and explicit Windows FS/TEB setup. An out-of-domain RNG result80000000 with signed divisor-1 tests the exact IDIV fault prefix at4484c3; the retail LCG normally returns0..32767.

The fixture image ranges match actual SPARKLE frames1..6 and GLITTER CIR1..16, but resource root/leaf tokens and allocator locations are declared adapters. The tests invoke controller visits directly: the generic scene countdown decrement, scene-node removal scheduling, frozen448400 powerup wrapper and frozen pickup caller are separately recovered modules, not additional whole integration claims from this suite. No GUI/device/render acceptance or whole-game equivalence is claimed.
