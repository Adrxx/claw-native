# Original duck and look-up updates

`Sources/PlayerPoseStates.h/.cpp` implement original v1.0 duck update
`0x00419fd0` and look-up update `0x0041a490`. Their entries are verified direct
call targets from the CaptainClaw dispatcher: logic state `26` invokes duck,
and state `5003` invokes look-up unless the dispatcher handles a pressed jump.

The original is `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Private decompilation, Ghidra logs, and test output are under
`work/pose-state-agent/`. The input executable is unchanged.

## Integration

Both APIs take the stable `ClawPlayerLocomotion` representation and existing
address-keyed dependency callback. Duck additionally takes a nonnull
`ClawPlayerPoseContext` containing the original input-manager pressed word at
`+4`; held and latched input remain in the shared locomotion struct.

```c
claw_player_update_duck(state, dependency, context, &poseContext);
claw_player_update_lookup(state, dependency, context);
```

These are update callbacks. Main dispatcher attack selection `0x0041d850`,
which precedes the duck update, remains outside this file. Main dispatcher jump
handling for look-up state is also outside this callback: a pressed jump takes
the existing jump entry/update path rather than calling `0x0041a490`.

The pose timer at private word `68` uses animation elapsed milliseconds with
unsigned saturation. Support-platform deltas are applied before private speed
bonus physics. A nonzero private speed bonus clears the three physics
remainders, sets signed x velocity, runs the recovered physics update with
stage elapsed milliseconds, and applies the recovered pixel converter. Both
callbacks request movement options `8` and preserve original falling transitions.

Duck zeroes actor x/y speed words before moving. Look-up preserves those speed
words during an ongoing pose, and clears them on its fall/stand exits. This
asymmetry is checked directly. Look-up keeps updating animation while up is
held; releasing up on ground executes the original weapon-transition cleanup,
restores stand animation/rectangles/timers, and returns logic state to `24`.

Duck release returns to stand only when the original attack gate allows the
transition and collision mode is `5`. Facing changes retain the original left
input priority, rectangle mirroring, render bit, and idle-timer effects.

## Duck animation markers

When private attack word `1` is nonzero, the animation update return drives the
original marker switch. The implementation preserves marker ordering and
complete actor/private side effects:

| Marker | Behavior |
| --- | --- |
| `1` | Clear actor flag `0x80`; set private word `7` |
| `2` | Set private word `7`; create the selected weapon effect once using private word `4` as the latch |
| `3` | Check pressed attack/weapon bits and signed pistol ammunition; increment wrapping repeat count, clear the latch, and seek the saved animation frame |
| `4` | Accumulate charge with **stage** elapsed time while held; on release retain the unsigned maximum of current/minimum charge and restore the saved animation |
| `5` | Set private word `7`; invoke the original release/throw effect |

Charge accumulation wraps at 32 bits before its unsigned maximum comparison.
Repeat count also wraps. Existing private word `7` permits cancellation on the
next update by setting private word `8`; setting word `7` in the current marker
does not prematurely change that order. Animation completion uses the original
actor fields at `+0x1a4` and `+0x19c` and invokes move cleanup.

The attack-effect dependency bodies remain explicit adapters. Their original
entry addresses and portable arguments are:

| Entry | Arguments `(a,b,c)` |
| --- | --- |
| `0x41c9f0` | `0,0,0` for weapon type `1` |
| `0x41cab0` | `0,0,0` for weapon type `2` |
| `0x41cb80` | `0,0,0` for weapon type `3` |
| `0x41cc60` | `0,0,0` for marker `5` |
| `0x420970` | saved animation frame index, `0,0` |
| `0x420a10` | saved sequence token, `0,0` |

Other movement, platform-delta, sequence-selection/lookup, animation-update,
and weapon-cleanup dependencies retain the existing locomotion contract.
Callbacks may mutate the supplied state. This recovery does not implement
projectile creation, damage, thrown-object behavior, or their audio.

## Verification

Run from the repository root:

```sh
work/test-env/bin/python Tests/compare_player_pose_states.py
```

The script compiles a separate native dylib under `work/pose-state-agent/`.
Each comparison executes fingerprinted original x86 instructions and checks
all actor/private words, physics bytes, input/logic state, pixel scratch words,
weapon cleanup state, and ordered dependency calls. Original dependency
receivers and argument lists are checked before portable token normalization.

Passing coverage:

- 4,500 generated duck updates and 4,500 generated look-up updates, including
  marker values `0..5` and `99`, attack/completion gates, both facings, platform
  offsets, physics speed bonuses, charge bounds, and weapon cleanup paths.
- Directed unequal-clock timer/charge checks, repeat/charge integer wrapping,
  weapon marker events, preserved look-up speeds, and release-to-stand paths.
- 2,880 chained duck calls and 2,538 chained look-up calls on a synthetic map.
- 2,880 chained duck calls and 2,880 chained look-up calls on the CD-rip Level 1
  map, with its preserved spawn `(689,4730)` and verified support boundary.

Generated tests adapt the movement body. Chained tests execute the complete
original movement/collision routines and compare native recovered collision.
Animation, weapon, resource, attack-effect, and seek dependency bodies are
adapted and their arguments/order recorded. Chained histories enter poses
through the recovered standing callback and repeat entry when leaving the
tested pose; they do not execute the full main input dispatcher. CD-rip asset
provenance retains its existing limitation.

The test reaches 2,167 distinct original instruction addresses. This is
callback-level evidence under explicit dependency contracts; whole-game
behavior and real audio/combat parity remain unverified.
