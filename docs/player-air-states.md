# Original v1.0 climbing and long-fall landing

`Sources/PlayerAirStates.h/.cpp` adds two original player update routines without modifying the stable locomotion state or dependency API:

| Native entry | Original entry | Player logic state |
| --- | --- | --- |
| `claw_player_update_climb` | `0x41bb70` | 27 |
| `claw_player_update_land` | `0x4198d0` | 5002 |

The boundaries are observed calls from the original CaptainClaw callback `0x415df0`, recovered in `work/player-callback.c`. Both routines were decompiled from the hash-pinned original v1.0 executable (`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`) in an independent APFS-cloned Ghidra project under `work/air-state-agent/`. The Ghidra log confirms 1209-byte climbing and 929-byte landing functions and successful saves; headless exit status alone was not used as evidence.

## API and dependencies

`claw_player_update_climb` receives the existing `ClawPlayerLocomotion*`, separate `ClawPlayerAirInput*` containing only the original input+4 pressed mask, existing dependency callback, and context. The held and latched masks remain in locomotion state. `claw_player_update_land` needs no new input context.

The only new dependency is `0x4207f0`: sample a world point, with portable arguments `a=x`, `b=y`, `c=0`, returning its tile attribute. It is the world point sampler, not the actor-foot sampler. Existing movement, animation selection/update, registry, image, weapon cleanup, and animation restoration operations retain their established callback signatures.

Two newly selected animation identifiers are `CLAW_CLIMBIDLE` at `0x524790` and `CLAW_CLIMBDOWN` at `0x5247a0`. `CLAW_CLIMB` uses the existing `0x5246c4`. Ladder-edge imagery uses image IDs 383 through 389 via the existing `0x4209d0` dependency.

The caller must supply working callbacks. Omitting or stubbing them does not implement complete gameplay. These routines do not invent an animation completion timer; landing observes the actual animation fields after the animation updater returns.

## Preserved behavior

Climbing gives held Up (`0x04000000`) priority over held Down (`0x08000000`). Normal vertical velocity is -200/+200; powerup `0x26bc` changes it to -250/+250. The private climbing animation state (word11) is 8 for Up, 2 for Down, and 5 for idle. A sequence changes only when that state changes.

A pressed jump (bit1) exits climbing only when Up is not held. That branch uses recovered movement cleanup, selects jump, assigns its original geometry/timers, sets gravity2250, and calls the general recovered `0x420dd0` retarget helper. It is different from blindly calling the existing jump-entry routine, whose optional weapon cleanup and inline retarget order differ.

When private word26 is zero, the routine samples the bounding rectangle's top point and scans downward one pixel at a time for ladder attribute3. If the top point is already a ladder, it stores zero, so the original routine samples again on later updates. Signed rectangle-height checks and wrapping additions remain intact.

After movement, the distance from cached ladder edge to actor foot selects image389 for distances0..16,388 for17..33,387 for34..50,386 for51..67,385 for68..84,384 for85..101, and383 for102..120. That image-selection path suppresses ordinary animation advancement. Falling transitions preserve attack-specific sequence restoration branches; grounded collision mode1 sets private walk counter62=1000 and enters stand.

Landing first zeros its velocity words and applies a supporting platform's x/y delta when the original support flag and token are present. It moves with collision options24. Falling and climbing collision outcomes enter those respective states. Otherwise animation advances, and completion requires actor word at byte offset `0x1a4` nonzero and record-index word at `0x19c` equal to zero. Completed landing enters stand or left/right walk from held horizontal inputs, with Right priority when both are held. The native code composes established cleanup and stand/walk entries; duplicate cleanup has no extra dependency calls after the first cleanup clears its guarded fields.

## Verification

Run `work/test-env/bin/python Tests/compare_player_air_states.py`. The private `Tests/air_state_helpers.py` harness builds a native dylib solely under `work/air-state-agent/`, uses the shared hash-pinned original-instruction harness, and captures ordered dependency events. It does not modify the stable locomotion harness or its output directory.

The generated phase compares 5000 climbing and 5000 landing calls, including directional priority, jump interruption, optional weapon/attack cleanup, animation completion fields, collision outcomes, powerups, stopped physics, signed/wrapped coordinates, and ladder scanning. Complete actor/private/physics buffers, logic state, input latch, pixel scratch and optional weapon fields agree. The original scene pointer is normalized to the portable token, while native token mutations still fail the comparison. Directed tests cover every ladder-image threshold and animation suppression, plus completed landing direction priority.

The chained phase compares 32 scripted histories of 240 calls (7680 steps), executing the full original and native point sampler, collision manager/resolver/helpers, physics and pixel conversion. It includes climbing on the synthetic ladder map, scripted ladder re-entry and jump interruptions, and scripted landing-animation completion. Input scheduling and re-entry/completion triggers are test inputs; they do not establish original whole-frame input dispatch or world actor lifecycle. Nested collision point-sampler calls are executed normally and are excluded only from the outer player dependency event log.

Animation, registry, audio, optional weapon-resource, and attack-animation bodies remain explicitly stubbed in these comparisons. Generated tests also stub point sampling and collision, checking their arguments; chained tests execute those bodies. Numerical inputs are finite game-scale values. These tests do not establish full-game identity, rendering, original scheduler timing, physical iPad acceptance, or retail asset equivalence.
