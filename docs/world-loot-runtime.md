# Original world loot runtime

`WorldLootRuntime.h/.cpp` recover original v1.0 `42df90` (inventory release), `4719e0` (loot metadata bootstrap), `473630` (image name), `473660` (actor callback replacement), and the `4a3050` RNG state update after its thread-local lookup. The oracle pins `Original/claw10/CLAW.EXE` SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Original instructions establish each entry boundary; private Ghidra output corroborates the bodies.

The wrapper releases every nonzero inventory ID. It does not choose a random item. RNG selects launch velocity after creation and initialization.

## Raw state and host contract

The API is C11-compatible. `ClawWorldLootContext.scene` uses frozen `ClawSceneActorHost` sized raw heap spans. Tokens identify original pointer identities or caller-owned translated addresses. Lookup must be read-only and returned buffer addresses must remain stable while creation or callbacks allocate. Callbacks can change live wrapper fields, actor/logic links, table globals, configuration, and RNG seed; the recovered code rereads fields at the original boundaries.

`ClawWorldLootGlobals.words[341]` represents contiguous `537ec8..53841b`. The ten-word gap is real and preserved.

| Words | Original base | Meaning |
| --- | --- | --- |
| 0–65 | `537ec8` | Image resource roots; name is root + `24` |
| 66–131 | `537fd0` | Pickup values |
| 132–197 | `5380d8` | Interaction masks |
| 198–207 | `5381e0` | Preserved gap |
| 208–273 | `538208` | Logic metadata pointers |
| 274–339 | `538310` | Sound resource pointers |
| 340 | `538418` | Initialized flag |

Other fields represent `52a190` item count, `532c10` overall volume, `53721c` launch mode, and the configuration word dereferenced through `537960`. `claw_world_loot_defaults` writes only original image defaults count=66, volume=100, launch mode=0; the caller initializes other storage deliberately.

`4719e0` clears all 66 image and value entries, performs ordered resource lookups, populates IDs 0–61, then writes count=62 and initialized=1. It preserves the last four mask/logic/sound entries and the gap. `Tests/world_loot_initializer_profile.json` pins the source-derived store/lookup program and decoded record names, values and masks. Configuration oddness replaces gem ID31 with `GAME_MAPPIECE`; configuration exactly13 then replaces it with `LEVEL_GEM`. Configuration is checked again after intervening callbacks. This initializer is callable repeatedly; it does not itself skip work because the initialized flag was already set.

`473630` compares signed ID/count. A valid image root of zero still returns token `24`, exactly as the original; an invalid ID returns the original literal `5279b8`, `GAME_TREASURE_COINS`. `473660` selects metadata+`10`, stores it into actor primary+`10`, resets primary state+`1c` to zero, invokes that callback with the actor as one cdecl argument, and returns1. An invalid signed ID returns0. It does not award items itself.

## Inventory release and ownership

The normal enemy receiver is enemy private+`128`. Generic enemy construction provides these aliases:

| Receiver offset | Meaning |
| --- | --- |
| `0`, `4` | Owner actor |
| `8` | Owner primary logic; its `c` points to scene |
| `20` | Release sound resource |
| `24` | Slot count |
| `28` | Declared nonzero item count |
| `2c` | Item ID array |
| `6c` | Source actor |

The nine generic inventory slots come from primary logic fields `f0,f8,f4,fc,100,108,104,10c`, then actor `100`. Exact WWD record indices are `35,37,36,38,39,41,40,42,15`.

The release sound plays first only for a positive signed declared count and nonzero resource, with `(overallVolume,0,0,0)`. Fan velocity starts at wrapped 32-bit `declaredCount * -25`, divided by2 with truncation toward zero. Each slot advances it by25, including empty slots. Each nonzero slot creates `BouncingGoodie` (literal `522cc0`, callback `40e690`) at source coordinates, z=4001, flags=`40000`, id=0. Creation uses owner logic→scene→actor container. `composeCreation=1` executes frozen `claw_scene_actor_create_named`, including actual allocation, constructor, metadata binding and list insertion; zero exposes exact six-argument `4c8da0` as a dependency.

Image binding follows creation. If source actor `100` equals32, source `148`, `14c`, `fc` are copied before the created actor's primary callback runs. Initialization must supply primary+`18` private storage. Only then does release write private vx+`50`, vy+`58`, gravity+`40`=800, and item ID+`184`.

A current declared count of1 consumes an extra RNG call for vx=`rand %401 -200`; otherwise vx uses the fan. Each released item consumes one RNG call for vy: launch mode zero gives `-(rand %301 +200)`, otherwise `-(rand %1001 +500)`. The launch mode is sampled before its RNG call. `claw_world_loot_next_random` wraps seed=`seed*214013+2531011` and returns `(seed>>16)&7fff`. The host must share its mutable seed with every other original RNG consumer. The original oracle executes `4a3050`, with only thread-local lookup `4a7dc0` adapted; that lookup's arguments, result and complete state are compared separately.

Created actors are inserted into the scene's actual list by the composed creator. This wrapper neither removes the enemy nor immediately deletes the loot. Deferred deletion remains the frozen scene lifecycle's responsibility. BouncingGoodie and award callback bodies are separate recovered modules, dispatched by the host rather than replaced here.

## Explicit services and limitations

Rich dependency calls preserve original function, receiver, ordered arguments, and optional decoded name. Required services are sound `4208e0`, image binding `4c7970`, RNG `4a3050`, and actual created/pickup callbacks. Initializer lookup `4f6286` is a declared adapter: the original bool plus output pointer is represented by a returned entry token. Frozen `ActorResourceBindings`, audio, `BouncingGoodieLogic`, and `ItemPickupRuntime` can implement those services in the native host. When composing creation, `scene.call/allocate` also supply frozen creator resource lookup/allocation services; resource metadata must identify the real callback.

The comparison fixtures deliberately provide finite, documented image and actor-initializer effects. Those fixtures are not proofs of image resource or BouncingGoodie gameplay. Every adapted event includes a complete pre-call state snapshot and final heap comparison. No arbitrary award, pickup, collision or projectile behavior is implemented by this module.

Context fault1 reports missing sized spans/services or valid rebind IDs beyond the 66-entry physical table; fault2 reports the creator returning a null actor at an original unsafe dereference. These are native diagnostics, not original safe failure behavior. Normal initialized count62 is recovered. Corrupt counts allowing arbitrary memory outside the represented global span are not claimed equivalent: the pure name API only represents image offsets through the 341-word view, and rebind is bounded to66 metadata slots. Callers must not continue a failed native operation as a successful original return.

## Verification

Run `work/test-env/bin/python Tests/compare_world_loot_runtime.py`. It compiles optimized portable code with warnings treated as errors, then runs both independent wrapper checks and retained Human death chains against original x86 instructions.

The wrapper/table suite has 1,115 complete operations, 27,506 ordered complete callback snapshots, 1,365 separately compared TLS lookup snapshots, and 2,236 executed original addresses. Each operation compares all 341 raw global words, scalar globals, the entire 512KiB raw heap, and original exception-chain restoration. Tests cover repeated initialization, missing resource lookups, configuration mutation during lookup, signed limits, empty slots, unequal declared/actual counts, overflow fan arithmetic, low/high launch modes, mutable initializer histories, callback replacement, and both adapted/composed creators.

Original CD Level1 contains 54 Rat/Officer/Soldier records with 137 nonzero inventory items. All 54 inventories are tested with original positions, IDs and relevant source fields through composed named creation. The twelve Level1 Rat inventories contain no nonzero loot.

The retained suite compares 48 histories /192 calls through actual original Human hit `44e0c0`→loot `42df90`→shared hurt `43f120`→dead update `43f450`. It adds720 ordered complete callback snapshots,96 TLS snapshots and645 executed original addresses. It checks original bit4 suppression, repeated-hit guards, current scene/list creation and the 1000ms death deletion request, preserving buffers across calls. Named registry and animation remain declared adapters. Results are saved in private `verification.json` and `death-loot-chain-proof.json`.

These bounded comparisons establish recovered body behavior within the supplied service contracts. They do not establish complete retail scene execution, asset equivalence, or whole-game behavioral identity.
