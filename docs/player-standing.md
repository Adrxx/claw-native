# Original standing and idle callbacks

`Sources/PlayerStanding.h/.cpp` recover the complete control flow of original
v1.0 standing callback `0x00419030` and alternate standing/ledge callback
`0x00419c80`. The implementation consumes the existing
`ClawPlayerLocomotion` actor/private/physics/input representation and its
address-keyed dependency adapter. It does not change that shared struct.

The fingerprinted source executable is `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Entry points and constants were verified against original instructions and
the private analysis project under `work/timing-agent/ghidra-project`.
Recovered dependency decompilation and native test artifacts are under
`work/standing-agent/`.

## API and behavior

`claw_player_update_stand(state, dependency, context, standingContext)` takes a
nonnull extra context with three fields:

- `inputPressed`: original input-manager word at `+4`. Lift/throw logic checks
  its `0x22` mask separately from held/latched input.
- `randomState`: original CRT thread record's random seed at `+0x14`. The CRT
  starts at seed `1`. Idle speech advances it with wrapping
  `state = state * 214013 + 2531011`, takes `(state >> 16) & 0x7fff`, then
  selects remainder modulo 12. This must eventually share the game's single
  original RNG stream with other recovered callers; a stand-only seed does not
  establish global random-event ordering parity.
- `liftedWeaponVelocityX`: the lifted weapon physics record's double at `+0x50`.
  Lift-fall paths write `-225`, `0`, or `225` according to player physics x
  velocity. The field models an external weapon object, not player physics.

Normal standing zeroes actor x/y speeds, chooses movement options `24`, `25`
(held up), or `26` (held down), applies the private speed bonus through the
original physics arithmetic, adds support-platform movement, and invokes the
movement resolver. Falling/climbing transitions retain exact cleanup, sequence,
rectangle, logic-state, and physics side effects. Attack animation uses the
separate attack callback. Duck transitions mirror all three actor rectangles
when the original facing condition requires it.

Timers retain their different clock sources. The look-up timer uses animation
elapsed time; the ordinary idle timer uses stage elapsed time. Held up/down
reloads the idle timer to 15,000 before the current stage elapsed time is
subtracted. These differences are tested with unequal clock values.

The look-up entry helper `0x004197e0` is implemented within this source, including
weapon cleanup, optional animation restoration, logic state `5003`, sequence
selection, and its 250 ms timer. That recovers entry into look-up; later updates
of look-up logic state `5003` remain a separate task.

Animation update return `99` invokes the recovered idle-speech selection helper
`0x00420480`; return `1` suppresses physics movement in lift logic state `5000`.
The callback also preserves the original animation-completion checks and stand
sequence restoration. Lift logic includes facing, lift-walk speed changes,
saved rectangle restoration, weapon-release calls, timeout behavior, and the
distinct lift-fall transition. Throw and lift-fall dependency bodies remain
outside this source.

`claw_player_update_stand_edge(state, dependency, context)` implements the
alternate callback and left ledge predicate `0x0041e790`. It probes support at
the rectangle edge, then scans inward in four-pixel increments after an initial
twelve-pixel offset. The left and right paths retain their asymmetric cleanup
and resource lookup behavior. Original `0x004bb030`, called for the right-facing
platform branch, is verified to return constant zero; it is not a random
function and needs no adapter.

## Dependency contract

Callbacks may mutate the supplied state, as existing locomotion adapters do.
The following entries are external dependencies. Other small helpers, facing,
physics, cleanup, lookup entry, left ledge control flow, and random choice are
executed natively.

| Entry | Portable arguments `(a,b,c)` | Required behavior |
| --- | --- | --- |
| `0x4cbb60` | target x, target y, movement options | Move actor and update collision state |
| `0x158`, `0x15c` | support token, 0, 0 | Return support-platform x/y delta |
| `0x4c82a0` | animation elapsed ms, 0, 0 | Update animation; preserve original return value |
| `0x4c79e0` | original string token, option, 0 | Select sequence |
| `0x4061b0`, `0x4f6286` | original string token, 0, 0 | Return resource/sequence token |
| `0x420a10`, `0x4c8220` | sequence token, 0, 0 | Restore sequence |
| `0x421010` | weapon token, callback token, option | Weapon transition |
| `0x420fc0`, `0x4dbd20` | weapon token, option, 0 | Weapon cleanup |
| `0x41c5a0` | 0, 0, 0 | Attack update |
| `0x41b1f0` | 0, 0, 0 | Lift/throw transition |
| `0x417930` | skip-animation option, 0, 0 | Lift-fall entry |
| `0x4cd1c0` | signed x offset as wrapping word, 0, 0 | Support predicate below the actor |
| `0x48c8a0` | original sound string token, 0, 0 | Play selected idle sound |

Foot support `0x4cd1c0` checks the tile attribute at actor x plus supplied offset,
actor y plus move-rectangle bottom **plus one**. Attributes `1`, `2`, or `3`
return true; other attributes return false. The original clamps coordinates and
handles sentinel tile values using its world point-query conventions. Real-map
tests execute this original body and compare a native adapter composed from the
recovered `claw_world_point_attribute` query.

Verified sequence string tokens are:

| Token | Name |
| --- | --- |
| `0x524734` | `CLAW_IDLE` |
| `0x524740` | `CLAW_DUCK` |
| `0x52474c` | `CLAW_LIFT2` |
| `0x524758` | `CLAW_LIFTWALK` |
| `0x524768` | `CLAW_LOOKUP` |

Idle speech chooses the original strings `CLAW_1054`, `CLAW_1056`, `CLAW_1057`,
`CLAW_1058`, `CLAW_1062`, `CLAW_1110035`, `CLAW_1110037`, `CLAW_1110038`,
`CLAW_1110043`, `CLAW_1110045`, `CLAW_1110056`, and `CLAW_1110057`. The adapter
receives their verified binary string addresses; sound playback itself is not
recovered or proven here.

## Original-instruction comparison

Run from the repository root:

```sh
work/test-env/bin/python Tests/compare_player_standing.py
```

The test builds an independent native dylib in `work/standing-agent/`. Original
actor, private words, physics, input/logic state, scratch words, weapon cleanup
state, weapon x velocity, RNG state, and ordered dependency arguments are
compared after every call. Original `rand` instructions execute with an adapted
CRT thread-record getter at `0x004a7dc0`; the random-number routine is not
stubbed. The sound-choice helper's original instructions also execute.

Validation includes 3,500 generated calls to each callback, directed unequal
clock timer checks, all twelve sound choices, 3,840 chained standing calls on a
synthetic map and 3,840 on the CD-rip Level 1 map, and 1,000 alternate ledge calls
on each map. Generated calls adapt movement and support queries; the real-map
tests execute original movement and support-query bodies. Animation, weapon,
resource, attack, throw, and audio dependency bodies are adapted and their
receiver/arguments/order checked.

The chained cases are callback histories with explicit stand re-entry after
state transitions. They do not execute the main CaptainClaw input dispatcher,
populated object interactions, or the complete game loop. CD-rip assets retain
their existing provenance limitation. This evidence establishes callback
behavior under the tested dependency contracts, not whole-game identity.
