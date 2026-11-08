# Original attack input, entries, and marker updater

This unit reconstructs the original Captain Claw v1.0 routines below from the
hash-pinned executable, rather than a reference game implementation. It extends
the existing portable actor/private/physics state without changing its layout.

| Original entry | Portable API |
| --- | --- |
| `0x41d850` | `claw_player_select_attack` |
| `0x41dd80` | `claw_player_select_weapon_attack` |
| `0x41de90` | `claw_player_start_attack` |
| `0x41c5a0` | `claw_player_update_attack` |
| `0x41d750` | `claw_player_nearest_attack_target` |
| `0x41e660` | `claw_player_can_lift` |
| `0x4207b0` | `claw_player_attack_random_range` |
| `0x4170f0` | `claw_player_enter_climb` |
| `0x417380` | `claw_player_enter_attack_stand` |

Evidence is in `work/attack-input-agent/attack-input.c`, the private closed
Ghidra project, and `Tests/compare_player_attack_input.py`. The original image
is `Original/claw10/CLAW.EXE`, SHA256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Ghidra logs were checked for script errors; original instruction execution is
the behavioral oracle. The additional walking attack stop `0x417380` was
reconstructed directly from its observed instructions `0x417380..0x417476`.

## Input and persistent context

The caller owns a persistent `ClawPlayerAttackContext`. Set `pressed` to the
original input object's `+4` word each tick. Held input uses the existing
`state.inputHeld`, and latched input uses `state.inputLatched`.
`difficulty`, `damage100`, and `damage0` correspond to original globals
`0x53725c`, `0x537218`, and `0x537228` respectively. Damage100 takes priority
when both damage cheats are nonzero. Context snapshots and tokens belong to
the external-object adapter; they do not represent original pointer ownership.

Selector priority is pressed melee `2`, selected-weapon fire `4`, direct
pistol `0x40`, magic `0x80`, dynamite `0x100`, then lift `0x20`. Held attack
buttons alone do not start a new attack. An already active private word1
returns zero before reading input or invoking a dependency. Ordinary empty
or held-only attack input therefore requires no combat callback.

Private word12 selects weapon1/2/3. Words28/29/30 are the original pistol,
magic, and dynamite counters in these routines. Attack entries choose empty
animations when the relevant signed counter is below1. The marker updater
decrements counters only after successful creation: pistol and magic only
when positive, dynamite unconditionally with wrapping subtraction.
The selector returns the actual attack-active private word1 after an entry,
except the explicit successful lift-button branch, which returns1 regardless
of the lift body's resulting private word1.

## External boundaries and exact arguments

All operations use `ClawPlayerLocomotionDependency`; arguments below are its
three payload words `(a,b,c)`. The address identifies the original routine.

| Entry | Portable payload | Adapter contract |
| --- | --- | --- |
| `0x41d750` | `(0,0,0)` | Return signed distance in uint32 representation; populate targetToken/targetActor. May invoke the recovered nearest-target API. |
| `0x41dc50` | `(targetToken,0,0)` | Original lift entry. Its object virtual lifecycle remains external. |
| `0x4a3050` | `(0,0,0)` | Original CRT random value, using the shared original random stream. The range helper calls this directly. |
| `0x48c8a0` | `(speechString,0,0)` | Original speech/audio request. |
| `0x4c79e0` | `(sequenceString,0,0)` | Select actor animation, with no immediate update. |
| `0x4f6286` | `(sequenceString,0,0)` | Resolve registry animation token. |
| `0x4c82a0` | `(animationDelta,0,0)` | Update actor animation and return original marker. |
| `0x4c8220` | `(sequenceToken,0,0)` | Restore saved sequence, with no immediate update. |
| `0x420a10` | `(sequenceToken,0,0)` | Release or auto-release charged dynamite animation. |
| `0x420970` | `(frameIndex,0,0)` | Original actor animation seek/repeat. |
| `0x421010` | `(weaponToken,0x4207a0,1)` | Weapon logic transition on finished attack. |
| `0x420fc0` | `(weaponToken,0,0)` | Original weapon-resource cleanup. |
| `0x4dbd20` | `(weaponToken,0,0)` | Zero-count weapon deletion; nonzero-count deletion flags are maintained directly in existing state. |
| `0x4c8da0` | `(spawnName,spawnX,spawnY)` | Original object creation. Also read spawnZ/spawnFlags from AttackContext; original leading creation argument is0. Return token and populate initial projectileActor/projectileLogicRepeat snapshots. |
| `0x4c7970` | `(projectileToken,0x524130,0)` | Select projectile images `GAME_BULLETS`. |
| `0x41cc60` | `(0,0,0)` | Original marker5 combat/powerup operation remains external. |

Creation sets original spawnFlags `0x40000`. After successful creation, the
native updater changes the projectile snapshot exactly; the adapter must
commit that resulting snapshot and projectileLogicRepeat to its live object.
A failed creation returns0, leaves the projectile snapshot unchanged, and
consumes no ammo. The attack's projectile-trigger word4 is still set.
No projectile lifecycle, damage application, lift-object virtual method, or
marker5 combat effect is claimed recovered by this unit.

For targets, pass candidates in the original linked-list traversal order;
equal distances preserve the first candidate. Each candidate must have a
nonzero stable token and all128 actor words. Only type4 or `0x200` qualifies.
Original signed comparisons, edge allowances, wrapping subtraction, and
the signed absolute-value overflow case are preserved. With count0, a null
candidate array is valid and returns999999, sets targetToken0, and leaves
targetActor unchanged. Can-lift executes the original mode/facing/bottom
geometry conditions directly from the target snapshot; it has no external
dependency. There is no guessed distance or lift mechanics.

The random-range helper preserves signed division/remainder and the
zero-span coin-flip branch. Actual original CRT random values are0..32767.
Projectile dynamite interpolation preserves wrapping 32-bit multiplication
before signed division, clamps0..200, and reverses horizontal direction for
left facing. This API is verified where the original returns normally;
the original `INT_MIN / -1` integer-divide trap is outside that domain.

Climb entry clears the original horizontal latch bits, cleans up carried
weapon state with its original conditional callback write, restores an
interrupted attack with `0x4c8220`, sets logic27/mode6, zeros actor movement,
clears climb words11/26 and vertical physics acceleration. Walking attack
stop preserves an in-progress attack animation while resolving `CLAW_STAND`
into private73 for restoration. It returns without changes for lift logic5000.

The stable locomotion field named `audioPosition` represents original global
`0x532c10`, which the audio worker verified is **overall volume**. This unit
does not rename that shared field or use it for positional audio.

## Verified strings

All animation strings below use the `CLAW_` prefix:

| Address | Animation suffix |
| --- | --- |
| `0x5246c4` | CLIMB |
| `0x5246d0` | STAND |
| `0x524898` | KICK |
| `0x5248a4` | PUNCH |
| `0x5248b0` | UPPERCUT |
| `0x5248c0` | EMPTYJUMPDYNAMITE |
| `0x5248d8` | JUMPDYNAMITE |
| `0x5248ec` | POSTDYNAMITE |
| `0x524900` | EMPTYDYNAMITE |
| `0x524914` | PREDYNAMITE |
| `0x524928` | DUCKPOSTDYNAMITE |
| `0x524940` | DUCKEMPTYDYNAMITE |
| `0x524958` | DUCKPREDYNAMITE |
| `0x52497c` | EMPTYJUMPMAGIC |
| `0x524990` | JUMPMAGIC |
| `0x5249a0` | EMPTYMAGIC |
| `0x5249b0` | MAGIC |
| `0x5249bc` | DUCKEMPTYMAGIC |
| `0x5249d0` | DUCKMAGIC |
| `0x5249e0` | EMPTYJUMPPISTOL |
| `0x5249f8` | JUMPPISTOL |
| `0x524a08` | DUCKEMPTYPISTOL |
| `0x524a20` | DUCKPISTOL |
| `0x524a30` | EMPTYPISTOL |
| `0x524a44` | PISTOL |
| `0x524a5c` | JUMPPOWERUPSWIPE |
| `0x524a74` | JUMPSWIPE |
| `0x524a84` | POWERUPSWIPE |
| `0x524a98` | SWIPE |
| `0x524aa4` | DUCKPOWERUPSWIPE |
| `0x524abc` | DUCKSWIPE |

Other verified original strings: `0x524970 CLAW_1009`, `0x524a50 CLAW_1003`,
`0x522bec Dynamite`, `0x522dc8 PistolBullet`, `0x522e00 MagicBullet`,
and `0x524130 GAME_BULLETS`. These were read from the hash-pinned original
mapped image, not inferred from nearby resource names.

## Verification scope

Run `work/test-env/bin/python Tests/compare_player_attack_input.py`.
The harness compiles into its owned `work/attack-input-agent` directory.
It compares all128 actor words, all78 private words, complete physics bytes,
logic, pressed/held/latched input, weapon cleanup state, all128 projectile
and target words, projectile repeat state, creation arguments, RNG call count,
and ordered dependency events. Events also capture callback-time attack
state, damage, and private words5..8, catching mutation ordering around
powerup animation selection. Every adapted original call checks the original
receiver and full argument vector; no unlogged dependency is skipped.

Directed checks cover simultaneous inputs, pressed versus held, all selected
weapons and supported movement modes, creation failure/success, signed ammo
guards, charge thresholds, rectangle sentinels, and the lift-state stop guard.
Chained histories retain charge, repeat, ammo, saved sequence tokens, and
latched input through selector/attack entry, marker updates, walking stop,
and completion cleanup with unequal and wrapping tick deltas. Separate tests
execute the complete original linked target scan and random-range helper.

This establishes equivalence for these routines under the documented
adapters, not full-game equivalence. Original asset timing, target/projectile
lifecycles, player startup, combat and animation integration, rendering, and
native execution of the whole game require their own evidence.
