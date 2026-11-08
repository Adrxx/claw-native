# Source checkpoint timer, HUD and command graph

`Sources/CheckpointTimerRuntime.h/.cpp` recovers the optional registered CheckpointTimer491b30, StatusNumberDigit4919f0, MultiStats491ed0, their actual actor/HUD creation graph, child update/draw ordering, cleanup, and the bounded expiry-command path. It executes against the unmodified original v1.0 EXE, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Entry-boundary checks, private Ghidra project, decompiles, xrefs, fixtures and oracle report are under `work/checkpoint-timer-agent/`.

## Actual caller and default profile

The original global53c9f8 starts **zero**. Immutable/current pinned52c6e4 is35000ms and52c6e8 is25000ms. The source timer callback publishes35000 during its state0 startup. Checkpoint contact adds25000 through the separate frozen CheckpointLogicRuntime and does not create or reset this HUD.

4254a0 initializes manager9c=0, manager68=2 and manager6c=0.46aeb0 creates MultiStats first through4c8f60(container,0,0,0,9999,literal52297c,200000). That creator executes the callback immediately;491ed0 publishes its actor identity into53c9fc. After dialog actors,46aeb0 creates CheckpointTimer through4c8da0(container,0,0,0,9999,literal522828,200000) **only when manager9c is nonzero**. No native default enablement or guessed countdown is warranted. The nonzero gate is reported by raw field identity, without assigning an inferred option name. Source command8062 clears manager9c and posts8025; this module exposes only the8063 command branch.

The actual registration literals/callbacks are `MultiStats`52297c/491ed0 flags0, `StatusNumberDigit`522994/4919f0 flags0, `CheckpointTimer`522828/491b30 flags2. MultiStats additionally creates ScoreFrame5229d8/4908b0 at z9998, WeaponFrame5229cc/490f80, HealthFrame5229c0/490c50, LivesFrame5229b4/4912a0 and TimerFrame5229a8/491540 at z9999. Only TimerFrame gets immediate200000. These five other HUD controller bodies are explicit original-address services; their creation/dispatch ordering is recovered, their display/stat behavior is not substituted here.

## Allocations, classes and source API

The C11 API uses `ClawSceneActorHost` token spans and rich calls with up to8 arguments. Source gameplay callbacks are cdecl(actor), receiver0. Listed constructor/controller helpers use actual thiscall receivers and original argument counts. Source address support and meaningful result are separate; void functions do not claim incidental EAX parity.

| Family | Actual size | Source identities |
|---|---:|---|
| MultiStats collection actor | 1d0 bytes/116 words | vtable513830; child CPtrList at1b4, block size10 |
| Timer and ordinary digit actor | 1b4 bytes/109 words | generic actor5137f0 |
| Generic primary logic | 174 bytes/93 words |513740 |
| HUD positioning/number object |60 bytes/24 words |50b5c4; embedded group+28 vtable50b5cc |

CheckpointTimer allocates one HUD object into its captured primary18 and creates three digit actors, each with another60-byte HUD associated object. Its primary14 private pointer is not allocated by this graph. The embedded number-group constructor490c40 writes only its vtable. Unused object words retain allocator seeds. The deleting HUD method40db30 calls40db50 (both vtables become50b014), optionally frees the object, and does not recursively delete digit actors. Digit actors belong to MultiStats' child list.

Recovered entry inventory:

- 491b30 timer,4919f0 digit,491ed0 MultiStats.
- 490c40 group constructor,490760 seven-argument HUD binder,490590 eight-argument digit-group initialization,490c00 immediate HUD render.
- 4d3ca0/4d3e50 plain child creation,4c8e00/4c8f60 scene collection-parent creation; common actor construction/initialization is composed with frozen WorldObjectRuntime and sorted scene insertion with frozen SceneActorRuntime.
- 4d3ef0 child callback dispatch;4d3f20 ordered virtual child drawing;4d3eb0 child cleanup;4f5172 CPtrList clear. AddTail/NewNode/CPlex allocation and exact list constructor/destructor stores are composed for this graph.
- 40db30/40db50 HUD teardown;4c9fc0/4c9fe0 collection teardown, composing frozen ActorDestruction for generic child/primary/animation/base cleanup.
- 41f490 kill helper,42a630 mode gate,426e30 bounded to raw command8063.

The collection initializer is4d3c40, which clears its list and calls generic4c7df0. It does not make the extra animation/entry stores of plain actor4c9d40. The portable composition restores those six fields around the frozen shared initializer. The original collection creator checks actual flags at entry-stack argument6 for200000; Ghidra's propagated parameter annotation incorrectly labels that operand as param2. Actual instructions and retained immediate-callback traces govern the implementation.

Actor allocation failure in plain child creation is a normal null result. Missing named metadata returns null. Zero metadata callback creates then destroys the rejected actor through the recovered generic/collection path. Missing primary, list-block or HUD allocations can enter actual original null-memory faults, after already visible source stores. The oracle moves FS to a valid TIB/GDT before unmapping the Windows null page so that these prove the real allocation failure prefix, not an artificial fault at the callback's SEH prologue. Native fault1 is a safety diagnostic, not an original successful return.

## Countdown, reset and visible digits

State0 binds `GAME_INTERFACE_TIME` literal52c8b4 indexed image1. It sets actor flags OR1, derives x offset32-image20-image18 when an image exists, constructs the HUD with current manager68, maximum99, horizontal mode3, that x offset, vertical mode4 and y offset15. Its three score-number digits use group offsets40,51,62, step11, parent z+1, and `GAME_INTERFACE_SCORENUMBERS`52c700. Resource interpretation uses frozen ActorResourceBindings/SpriteGeometry and the exact getter40f680 through frozen PickupPointsRuntime.

State1 first caps unsigned remaining at999000ms, then subtracts **stage delta53720c**, saturating at zero. It separately advances embedded actor188 ANI using5430c4. Remaining is not decremented by ANI delta or by a fixed native frequency. The display is unsigned `(remaining+500)/1000`. A changed displayed value updates the three rightmost characters of the source `%010i` formatted value, selects the corresponding image IDs and writes each digit primary68=ffffffff. Number initialization caps signed requested count above9 to10, supports the originalffffcfc7 (-12345) no-value sentinel, and uses sequential allocation/initialization. Negative counts skip creation, preserving the source's scalar count behavior.

HUD fields4/8 select horizontal anchor/offset; c/10 select vertical anchor/offset;14 caches manager68;18 is its signed maximum mode;24 identifies the live actor;20/1c record draw status. Anchors use source globals5370c8/cc/d0/d4 and signed wrapping differences divided toward zero. A changed mode or positive manager6c requests positioning. Mode0 calls the actual scene+c renderer's vtable+28 with x,y,image token, then ORs the *live* HUD actor40 with1 and writes HUD20=0,HUD1c=1. Source callback mutations at this render boundary are compared.

MultiStats state5 invokes every child callback in list order, capturing next before each call.4d3f20 does the same for each child's virtual draw+2c. Generic child drawing4c9e00 remains a host service that Root can connect to its existing frozen renderer/GameImage graph. The module does not invent projection or draw flags. Collection teardown deletes children in list order, frees pooled nodes, performs the source repeated primary cleanup passes, tears down the embedded list and composes frozen generic animation/base destruction.

## Expiry action and player gates

When state1 reaches zero and player537e88 is nonzero, it enters state31. If player actor10c health is **signed positive**, it first sets53c9f4=1 and posts IAT546d50 `(HWND,111,8063,0)`, taking HWND from manager4+4. Posting is asynchronous. Its result does not gate state31; the main callback can still update its HUD/digits after posting. A null player leaves it in state1 at zero, and health<=0 does not post the kill command.

The actual426e30 command8063 branch calls42a630. That source helper accepts owner modes3,4,6, re-reading the virtual getter up to three times in order. The single-player40af90 constant3 body is composed. On success with a live player it invokes41f490: positive health becomes0, then cdecl417b00 receives `(playerActor,primaryLogic,privateToken,notice0)`. Root already owns the frozen PlayerDamage implementation of that fall-death body; this raw service exposes its exact arguments. No immediate game-over or respawn state is invented by the timer.

State31 waits until live player health<=0, then enters5. State5 waits until health>0, clears expired53c9f4, publishes52c6e4 to remaining and enters1. These are source observation gates; the test's revival/command dequeue elections are explicit inputs, not recovered Windows scheduling or proof that the player death/respawn leaf executed in this module.

## Host globals and explicit boundaries

Global ABI order (13 words):5371fc manager,537e88 player,53720c stageDelta,5430c4 animationDelta,53c9f8 remaining,52c6e4 initialDuration,53c9f4 expired,53c9fc MultiStatsToken,5370c8/cc/d0/d4 screen bounds,532c10 audioPosition. Share53c9f8 with live CheckpointLogicRuntime remaining; do not maintain divergent native counters. Screen bounds and manager identities are supplied as original profile links; this module does not infer them from the Mac window.

`composeAnimation`, `composeImages`, `composeHierarchy`, `composeFormatting` select frozen/recovered bodies; zero exposes the corresponding original services for directed comparisons. The fixed source `%010i` formatting is composed with C integer formatting, and the oracle executes the actual original4a3920 formatter; the optional service exposes a callback-scoped16-byte buffer and normalized local pointer argument. Resource/file transport, renderer virtual draw, PostMessage/window delivery,417b00 player death, and five other MultiStats HUD controller bodies remain explicit. The independent original and native allocator adapters retain histories but do not claim Windows heap internals.

Generic vtable method identities used for frozen destruction are pinned5137f0+4→4c9be0,513740+4→4c80c0 and50b5c4 slot0→40db30. Other polymorphic vtables require raw lookup/services. Invalid graph spans fault1, propagated allocation/profile issues fault2 and invalid argument/unsafe number profiles fault3 are native safety extensions. Frozen ANI rejects reentrant gameplay mutation at its audio boundary. None of the checks is device, display-raster, actual OS message-loop or whole-game parity evidence.

## Verification

Run `work/test-env/bin/python Tests/compare_checkpoint_timer_runtime.py`. The final report records **1,912 whole original calls,7,267 ordered full snapshots,2,367 original addresses and310 actual original formatter executions**, comparing524,288 heap bytes and13 global words across five retained creator histories. It covers state0/1/5/31 and inert states; player/health/HUD gates; unsigned cap/subtraction/rounding; signed anchors/status modes; callback mutations; source constructors, actual retail TIME1 and all ten SCORENUMBERS PID geometries; number count/sentinel/value behavior; meaningful allocation failure prefixes; typed creation/null metadata/zero callbacks; source command mode read order; HUD and collection teardown.

Five retained status-mode profiles use actual4c8f60 collection and frozen4c8da0 CheckpointTimer named creation, both with source200000 flags. They retain startup→countdown/digit dispatch/draw→zero/post8063→elected command drain→observed death→elected revival→35000 reset→source cleanup. The strict C11 header/strict C++17 compile and private ASAN+UBSAN smoke over all five real resource/creator fixtures pass. ASAN composes creation, controllers, draw dispatch, command prefix and collection cleanup; physical renderer and player-death leaf remain adapters.
