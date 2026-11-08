# Original player initialization and respawn

`PlayerInitialization.h/.cpp` reconstruct the original global defaults
constructor `0x415ce0` and the complete CaptainClaw callback `0x415df0` when
its initial logic state is0 or23. Logic0 starts a level; logic23 respawns the
existing player. The common callback epilogue is included, preserving weapon
cycling, timers, powerup callback, coordinate clamp, hazard checks, and cheats.
Other initial states return0 without mutations or dependency calls.

The original executable is `Original/claw10/CLAW.EXE`, SHA256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Evidence includes `work/player-callback.c`, owned
`work/player-init-agent/initialization-helpers.c`, observed instruction listings
in that directory, and `Tests/compare_player_initialization.py`. Ghidra's
private project and logs were checked for script errors. Original instruction
execution supplies the behavioral oracle.

## Startup inputs and ordering

The actor buffer must first come from the recovered generic actor constructor
and initializer in `WorldObjectRuntime.h/.cpp`. State0 preserves unrelated
actor words and never blanket-zeros the actor. The generic loader sets probe
steps `actor+0xdc/+0xe0` to10. Its memory seeds, registry metadata, scene token,
and actor/logic tokens belong to the object loader; this unit does not infer
their values. Initialize global physics with the separately recovered
`claw_physics_construct`, preserving its original written/untouched fields.

For a new game, `claw_player_construct_defaults` performs original `0x415ce0`:
zero all78 global default words, select weapon1, health100, pistol10, magic5,
dynamite3, lives3, private word59=1000000, reset the replay accumulator to
its configured minimum, and clear powerup globals `0x534ea8/0x534eac/0x534eb0`.
Nonzero difficulty instead assigns counters28..31 to50/40/20/9.
It does not zero the live actor, live private state, or physics.

Caller-supplied `ClawPlayerInitializationContext.defaults` represents all78
words of global `0x534c80`, including a saved-state snapshot. Word9 controls
whether inventory words34..43 survive state0: zero clears these10 words;
nonzero preserves them. This unit accepts an already populated snapshot;
the save-file decoder and decisions about when to replace that snapshot are
external. Bounds-checked C accessors expose these words without Swift tuple
indexing.

With live logic0, `claw_player_dispatch_initialization`:

1. Resets cached coordinates to `0xffffffff`, assigns minimum world bounds50
   and maxima `worldWidth-50` / `worldHeight-50`, and allocates the private
   buffer if its original token is zero.
2. Clears current powerup/time, copies all78 default words, transfers health
   to actor+`0x10c` and word17 to actor+`0xf8`, selects `CLAW` image11, writes
   the level start coordinates, sets z4000, and binds `CaptainClawHit`.
3. Sets original flags/type/filter/movement fields, installs initial movement,
   hit, and attack rectangles, and places the actor on the ground.
4. Saves that ground position in private19/20, clears transient fields, applies
   the inventory gate, enters stand, then performs the original unconditional
   rectangle mirror and right-facing normalization.
5. Queries game configuration; returned mode4 assigns lives9. Initializes
   physics, performs the external manager resource reset, and adjusts the
   original ladder image metadata when enabled.
6. Executes the original common epilogue.

Ground placement occurs before standing animation selection and before
physics initialization. The saved spawn is the ground position before the
common coordinate clamp. Actor type becomes2; filter actor+`0xd4` becomes
`0x01b50544`; actor+`0xf4` becomes1; support+`0x80` clears. Z changes set
actor flag `0x20000` only when z was different, matching `0x40f6a0`.

Initial movement rectangle is `(-16,-52,16,60)`. The pre-standing hit rectangle
is `(-25,-45,12,52)`; standing changes it to `(-22,-45,15,52)` for the final
right-facing state. Attack rectangle is `(-15,-45,22,34)` after the original
two mirrors. Rendering flip bit2 clears. Standing timers are private63=650,
69=1500,72=15000 and70=0; private11=5 and58=0. Unrelated fields survive.

Physics initialization supplies acceleration `(0,2250,0)`, velocity and
position `(0,0,0)`, elapsed/timestep0, maximum x/y delta32, and all maximum
velocities1000. It preserves bounds, delta, stopped/unused and maximum z
delta; stand entry clears remainders. On a fresh zeroed BSS physics buffer,
the separately recovered constructor supplies its documented bounds and
stopped0. Reinitialization preserves fields the original routines leave
untouched; it does not silently re-run the global physics constructor.

## Respawn and replay

Logic23 restores health100 in both private18 and actor+`0x10c`. If either
checkpoint coordinate is `0xffffffff`, both coordinates come from private19/20;
otherwise both use the checkpoint. It selects `CLAW` image11, writes position,
sets z4000, masks original actor/render flags, places on ground, and enters
stand. It clears invulnerability timing and original attack/climb/transient
fields, emits `GAME_FLAGWAVE` when the resulting x differs from saved spawn x,
and queries game mode again. Ammo is retained, subject to common cheat handling.
It does not reset all private words or initialize physics.

Original replay accumulator `0x53c9f8` adds configured step `0x52c6ec` with
32-bit wrap, then clamps against minimum `0x52c6e4` with an **unsigned**
comparison, verified at original instruction `0x4163ae` (`jae`). It calls the
manager resource reset and powerup reset request, then optionally invokes
the external reset object's virtual slot+`0xb0`.

Context field `powerupAuxiliary` corresponds specifically to global
`0x534eb0`; its wider semantic purpose is not established here. The existing
powerup expiration signal is a distinct global, `0x534eb8`, and is not cleared
by `0x415ce0` or the state0 body. Adapters must synchronize the shared remaining
powerup time with their recovered powerup timer context.

## Dependency contracts

Payloads use existing `ClawPlayerLocomotionDependency` `(entry,a,b,c)`.
Opaque tokens are original-profile 32-bit identities, not cast host pointers.

| Entry | Payload | Meaning |
| --- | --- | --- |
| `0x4f63ec` | `(0x138,0,0)` | Allocate private buffer token when initialization.privateToken0; portable state already holds its78 words. Original normal-return path requires a successful nonzero allocation. |
| `0x4c7900` | `(0x523734,11,0)` | Select image registry `CLAW` and original initial image11; adapter writes actual image-manager/image tokens. |
| `0x4c7fa0` | `(0x522e70,0,0)` | Bind `CaptainClawHit` through original resource/callback registry. |
| `0x4cd800` | `(0,0,0)` | Ground placement; original thiscall receiver is collision manager and real args are `(actor,0)`. The second word is observed, although unused by the recovered body. Adapter can invoke `claw_collision_place_on_ground`. |
| `0x4c79e0` | `(0x5246d0,1,0)` | Stand animation `CLAW_STAND`, with immediate original animation update. |
| `0x420a10` | `(savedSequence,0,0)` | Stand entry's interrupted-attack restoration, when needed on respawn. |
| `0x420fc0` | `(weaponToken,0,0)` | Original weapon-resource cleanup. |
| `0x10` | `(configurationToken,0,0)` | Synthetic address-keyed representation of original configuration virtual slot+`0x10`; return its original mode. Tests execute and adapt a real virtual call. |
| `0x4bc110` | `(0,0,0)` | Original game-manager resource reset; body remains external. |
| `0x40f680` | `(imageManagerToken,imageID,0)` | Resolve ladder image metadata; return token and populate its context word24 snapshot. |
| `0x420910` | `(0x5246b4,0,0)` | Respawn checkpoint sound `GAME_FLAGWAVE`. Common weapon cycling uses `0x524678 GAME_CLICK`. |
| `0x41f990` | `(0,0,0)` | Original respawn powerup/resource reset; body remains external. |
| `0xb0` | `(resetObjectToken,0,0)` | Synthetic representation of reset object's actual virtual slot+`0xb0`. |
| `0x41fc30` | `(stageDelta,0,0)` | Existing recovered powerup-timer helper in common epilogue. |
| `0x4cd740` | `(0,0,0)` | Common foot hazard query. |
| `0x417c50` | `(0,0,0)` | Original hazard/death transition, explicitly external. |

Context configuration/reset tokens determine virtual receivers. Original
logic state/private pointer/bounds/timer are represented by live state,
initialization.privateToken, and `ClawPlayerInputContext`. Every other original
logic word is preserved. The parent adapter should use persistent context
storage when callbacks populate resource snapshots to avoid reentrant Swift
`inout` access.

Stand cleanup changes the carried object's logic callback to `0x4207a0`
directly only when its signed logic status is positive; it does not invoke
`0x421010` in this initialization/reset path. Existing portable weapon status
and callback fields preserve that conditional write.

When `imageOffsetsAdjusted` (original `0x534eb4`) is0 and actor+`0x170` is
nonzero, resolve image IDs383..389 in order and add4/8/12/16/40/54/58 to each
nonzero image's original word+`0x24`. The adapter must commit the resulting
metadata words to its image objects. The state0 body does not set the gate
global itself. Repeated state0 therefore repeats these additions unless the
external resource system changes the gate or replaces the images; tests retain
this behavior rather than inventing a once-only policy.

The resource, hit-callback binder, manager reset, powerup-reset body, and
external object's virtual reset are explicit adapter boundaries. This unit
does not claim equivalent behavior for absent implementations of those bodies.

## Verification

Run `work/test-env/bin/python Tests/compare_player_initialization.py`.
The harness compiles only into owned `work/player-init-agent/` and compares
the complete original callback, not a manually selected instruction fragment.

The suite checks all128 actor words, all78 private/default words, complete
physics bytes, all93 original logic words, both complete portable context
buffers, input, powerup/replay/cache globals, weapon callback, and ladder
metadata. Ordered dependency events capture the complete actor, private,
physics, input and relevant global snapshot **at callback entry**, so placement,
standing, configuration, physics initialization and resource ordering are tested.
Each adapted original call verifies its full real argument vector and receiver;
no dependency is silently skipped. The only pointer normalization is original
actor scene/logic pointer versus its preserved portable token.

Directed and chained cases cover fresh allocation versus reuse, difficulty,
saved-state inventory, checkpoint fallback, config mode4, repeated startup,
respawn with active attack/carrying cleanup, unsigned replay wrap, unequal tick
deltas, image gate/missing image tokens, hazards/cheats, and unsupported states.
128 integration cases combine the separately recovered generic loader baseline,
global physics constructor, defaults and full state0 with the real original
Level1 tile collision data and unmodified original ground-placement body.
They verify spawn `(689,4723)` becomes `(689,4730)`, saved spawn matches,
probe steps are10, weapon/health/ammo defaults and physics limits are exact.

This evidence establishes the covered initialization/reset callback behavior
under the documented adapters. It does not establish complete save-file
loading, generic registry identity, image/callback resource equivalence,
combat/death behavior, or whole-game identity.
