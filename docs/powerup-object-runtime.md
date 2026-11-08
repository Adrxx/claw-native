# Original SpecialPowerup and CursePowerup objects

`PowerupObjectRuntime.h/.cpp` translates the hash-pinned original v1.0 bodies. It does not introduce a new private object, guessed powerup IDs, multiplayer effects, or a direct warp. Generic object construction and world-record decoding belong to frozen `WorldObjectRuntime`; animation, ordinary sound/marker helpers, loot initialization, and player timed powerups compose their frozen modules.

Original EXE SHA256: `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Original REZ SHA256: `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`.

## Source inventory and entry ABI

| Entry | Original meaning | Receiver / arguments |
|---|---|---|
| `470430` | Registered `SpecialPowerup`, metadata flags2 | receiver0, cdecl(actor) |
| `470a20` | Registered `CursePowerup`, metadata flags2 | receiver0, cdecl(actor) |
| `41ee60` | Full special/curse/warp/rope pickup selector | receiver0, cdecl(player,primary,private,pickup) |
| `436860` | CPtrList coordinate-pair search | list header, x/y; original callee pops8 |
| `417050` | Player hit rectangle from private facing | receiver0, actor/private |
| `4170b0` | Player movement rectangle | receiver0, actor |
| `40af90` | SinglePlayer controller type getter | controller, no arguments; returns3 |

Private Ghidra `callbacks.log` confirms complete callback boundaries1088/722 bytes. `helpers-verified.log` confirms1506/42/96/53/6-byte helper bodies. An earlier exploratory `helpers.log` requested interior473900 and contains a SCRIPT ERROR; that batch is not whole-function evidence. The verified batch supersedes it. All analysis projects and generated binaries remain private under `work/powerup-object-agent/`.

Level1 has exactly10 SpecialPowerup (8 GAME_WARP,1 GAME_POWERUPS_EXTRALIFE,1 GAME_MAPPIECE) and8 CursePowerup. Exact71-word records, sized strings and source hashes are captured in private `level1-records.json`. Python REZ inventory is read-only format transport; original REZ enumeration is not claimed here.

These callbacks operate on the generic animation actor vtable5137f0 and primary vtable513740. Generic allocation sizes are actor1b4 and primary174. There is no special/curse private allocation or subclass constructor. The suite executes original4c98c0 and the actual derived caller block4d18a7..4d1905, then4c9d40, using declared primary allocation outcomes. Eighteen safe null-primary prefixes preserve untouched primary seeds; no malloc implementation is substituted as recovered. The typed actual-record setup composes frozen4d17e0 decoding with declared resource/list services; this suite does not re-prove that whole decoder's transport graph.

## Actual singleplayer and configuration

Original SinglePlayer vtable50c264 slot10 is40af90 returning3. Curse state0 clears primary168/16c, then requires mode4, original52550c nonzero, and a second mode4 query. Failure adds actorflag10000, returns0, and does not initialize ANI, depth, rectangles, loot or glitter. All eight actual Level1 curses therefore reject. Mode4 remains a separate directed fixture with exact controller calls, without inventing multiplayer gameplay.

Actual Level1 uses the parent-established selected profile537960→5378a0 with first word1. The context's `loot.configurationWord` must mirror that live selected profile. Whole lazy4719e0 is compared under0/1/13: configuration1 binds GAME_MAPPIECE row31 to26ad; configuration0 uses LEVEL_GEM, while configuration13's later LEVEL_GEM override also replaces that row. No arbitrary map-piece fallback is inserted.

## Object states and side effects

Special state0 clears primary168 and actorc8, changes zero depth to1000/flag20000, and selects GAME_CYCLE100 for the captured coins image-root identity or GAME_POWERUP otherwise when no existing ANI. It adds flag80000/type100, derives attack rectangle138..144 from image20/24 and18/1c, then expands -6/-10/+6/+2 even with no image. Loot lookup uses exact root identity and first match, storing item ID, actorfc and primary168 sound. Coins index0 becomes actorID33. Missing roots produce actorID0/value100/sound0.

Mode4 extra-life objects mark deletion immediately and retain state0. Other eligible special objects create PowerupGlitter through exact4c8da0(container,1,x,y,z+1,name522950,40000), except GAME_WARP; Curse has no warp exclusion. The original470100 callback and manager124 gates remain exact. Nonnull glitter token goes into actorc8. State5 animates; Special collected164&200 advances to9000. Curse searches controllerbd4 CPtrList pairs for its current x/y and deletes the object on a match.

State29 marks attached glitter10000 and **retains actorc8**. Special9000 marks actorflags21, deletes and clears glitter, reads main-plane center84/88, sets400ms, and computes wrapped **unsigned** velocities toward(centerX+300,centerY-200). State9001 saturates the stage timer, adds/subtracts wrapped delta×velocity/1000, marks deletion at zero, then animates with the separate animation delta. It does not call the ordinary Treasure points-icon service.

## Whole selector41ee60

| Source value | Effect |
|---|---|
| `26ad` | Queue WM_COMMAND800e first, primary24=2, lookup GAME_MAPPIECE sound, optional play, then duration wait4b8960 even with audio off. Mode4/bcc1 adds5050 score. Mark item10000. |
| `26ae` | Capture item148/14c. Standing logic4 enters source fall25, cleans movement or changes pending ANI according to private3c, sets rectangles/mode/remainders and physics velocityY0/accelerationY2250. Positive signed captured x/y publish529fa0/a4 and queue805c. Item108 controls retention. **No coordinate teleport.** |
| `26af` | Original rope latch/motion/distance gates; rope getters403ab0/ac0 remain explicit. Eligible contact selects CLAW_SWING, logic5007, mode8, rope token/privatef8 and zero physics remainders. Logic5007 update is outside this module. |
| `26b0` | Compose frozen dynamite branch. |
| `26b1..26b6` | Call current controller virtual58(item); accepted call plays source item sound. Delete regardless of acceptance. Actual multiplayer effect body remains explicit. |
| `26b7`,`26bd` | Whole frozen41f990 setter and sound; signed-positive item108 duration or30000; delete. |
| `26b8..26ba` | Same duration/setter, with source item104 persistence and same-type skip semantics. Positive signed104 refreshes remaining and retains item; otherwise delete. The field is re-read after services. |
| `26be` | Signed private7c<10 increments lives and plays sound. Whole473ae0 marks collection200/disabled1 and retains the item for the9000 visual. |
| `26bb`,`26bc`,other | No selector effect; no guessed plasma/unused mechanics. |

Map/warp platform requests use original IAT546d50(window from manager+4+4, WM111,command,lParam0). Resource bodies, OS delivery, map UI handler, warp command handler, and blocking physical wait remain declared services. Command publishing is distinct from command execution.

## Host contract and composition

Supply a `ClawPowerupObjectContext` with caller-owned `SceneActorHost`, live loot globals, ItemPickup sound-cache/stage/audio aliases, PlayerPowerup shared globals, and optional physics/animation objects. Raw32-bit tokens preserve pointer identities. Host lookup returns aligned complete word spans; the source callbacks access aligned words only. Clear fault before a call. Return1 means completed/covered; original meaningful EAX is separate. Void helper/selector incidental EAX is excluded. Unsupported entries preserve output and state; wrong arity is fault2; missing graph/service is fault1. Native list traversal is bounded at1M iterations.

`composeAnimation=1` invokes frozen actual4c79e0/4c8220/4c82a0, requiring live sequence/record/image tables. `composeCreation=1` invokes frozen SceneActor named creation; otherwise their exact original service calls remain exposed. Lazy4719e0 always composes frozen WorldLoot initialization. Setter/reset/timer41f990/fc00/fc30, sound41d6f0, marker473ae0, and dynamite helpers compose existing bodies over the same live heap and globals.

Unarmed41c4e0 composes frozen movement cleanup, committing live actor/private/input+12 before ANI restoration and reloading afterwards. Armed cleanup (private300 nonzero) remains an explicit41c4e0 dependency; no weapon shadow is invented.

`claw_powerup_object_award` is a bounded composition of frozen CaptainClawHit→selector for exact attacker type100. It requires player actor74 already equal the item token. ActorInteractions owns contact election and immunity; this helper does not infer a contact from proximity. It commits/reloads complete player/item views at the selector boundary and preserves live logic/private side effects.

Required aliases: manager5371fc/player537e88 and powerup534eac/remaining534ea8/expired534eb8/music53c9c0/cycle534ec8/cc from PlayerPowerup; stage53720c/tick537210/audio532c0c/volume532c10 and sound-cache534ec0/4 from ItemPickup; animation5430c4; input537204 points to context.inputToken; curseEnabled52550c; warp529fa0/a4 from this context. `audioPosition` in the older animation struct represents **overall volume532c10**, not a spatial coordinate. Physics object534db8 is needed for the warp/rope branches and is shared with the player.

External calls carry original function, receiver, all args (up to6) and optional synchronous literal text. Physical music/speech/image effects/GlitterMother creation, dictionary name transport, sound playback/duration wait, rope getters, multiplayervirtual58, armed cleanup, and OS messages remain explicit. The original4c6130 image-effect body executes in oracle tests, and the native private adapter composes frozen GameImage. Resource callbacks are allowed to mutate fields; tests preserve observed reentrant ordering rather than assuming immutable results.

## Evidence and limits

Run `work/test-env/bin/python Tests/compare_powerup_object_runtime.py`; then `work/powerup-object-agent/run-sanitizers.sh`. `verification.json` records exact addresses, resource hashes, service identities and counts.

Current full oracle passes1974 object/selector/helper/hit calls,60 whole timer calls,54 generic constructor/caller/init profiles,18 source image-binding calls and18 actual GAME_POWERUP ANI record decodes. Each callback comparison includes the complete262144-byte heap,147456-byte global image, ordered callback snapshots, meaningful returns and exact return-stack convention. There are5498 ordered full snapshots and3506 original instruction addresses excluding adapted boundaries. All18 actual Level1 profiles use configuration1, with120 retained Special ticks and real CaptainClawHit composition. Null resources/creator outcomes, signed life boundaries, wrapped timers, simultaneous field mutation, mode gates, CPtrList matches and hit→powerup→timer→expiry/reset chains are directed checks. Two invalid original pointer fault prefixes compare separately from completed bodies.

The ASAN/UBSAN corpus replays318 callback-free original histories, including live source ANI and singleplayer vtable profiles. This covers memory/arithmetic safety for those finite profiles, not physical allocators or external services. C11 header and C++ warning checks pass. Actual PID dimensions/offsets and original first-ASCII-digit filename ID rules feed source image-binding tests; pixel decoding/display, retail resource traversal, multiplayer effects, warp command execution and rope updates remain outside this module. These bounded comparisons do not establish full-game equivalence.
