# Original common enemy states, damage and death

`Sources/GenericEnemyStates.h/.cpp` extends the frozen GenericEnemy runtime with original state and method bodies. It recovers all **14 previously unported registered common state callbacks**, so the two modules together support all **19 captured common state registrations**. It also recovers landing/home selection, death-mode entry, generic hit dispatch/health subtraction, hit-particle coordinate selection, and selected state-entry methods. It does not duplicate the shared FSM or scheduler.

Profile: `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. New bounded Ghidra evidence and a separately cloned project are private `work/generic-enemy-states-agent/`. No CrazyHook or reference gameplay implementation is copied. Frozen shared sources/tests and the Rat/RatBomb worker's sources are read-only.

## Stable API and dependencies

```c
uint32_t claw_generic_enemy_state_entry(state, common, extra,
    originalFunction, argument, dependency, user);
uint32_t claw_generic_enemy_state_dispatch(state, common, extra,
    resolvedStateID, dependency, user);
```

The API uses unchanged `ClawGenericEnemy`, `ClawGenericEnemyContext` and rich `ClawGenericEnemyDependency` types. New `ClawGenericEnemyStatesContext` supplies attacker identity/actor128, player private78, original strike counter52713c, audio enabled532c0c/audio position532c10, and resolved resource-root→root+0x10 controller identities. Every actual read is a mapped original field; no native pointer is cast to an original token. The host keeps original actor +0x74 and direct attacker arguments consistent with this represented attacker, and primary +0x18 consistent with the represented enemy object. Actor references inside the enemy/embedded wrapper continue to identify the same represented actor.

Returns are native support/completion status (one success, zero unsupported/invalid). Original state callbacks generally return zero, LogicHit/LogicAttack wrappers return one, and generic hit0x43e9e0 returns zero for rejected hits/one after its dispatch. Native support status is not claimed to be those original EAX values. Dependencies can modify common buffers/context and can modify the extra context through caller-owned userdata; subsequent reads preserve original ordering. Missing state/resource views can return zero after earlier stores, so no transactional rollback is claimed. Resource controller identities must be supplied for each present root actually used by an enabled0x4b45f0 path.

The death-entry profile requires original bitset size >=5. Normal recovered base construction gives size32; valid larger runtime backing is supported and checked. The original undersized/nonconstructed grow path calls heap resize0x4dc6d0 and has pointer/inline-size quirks; it is explicitly rejected before death-entry writes rather than replaced with an invented allocator. Nonfinite physics and arbitrary polymorphic aliasing/retargeting remain outside the finite constructed profile.

Unknown function identities return zero. State dispatch resolves the supplied exact metadata, uses this layer for recovered bodies and the frozen common layer for its existing bodies/dependency boundaries. Numeric state IDs remain caller-resolved named metadata. No fresh-registry IDs from the19-entry capture are presented as full retail startup IDs.

## Recovered registered callbacks

| Name | Original callback | Exact behavior covered |
| --- | --- | --- |
| LS_STRIKE | 0x43f030 | Advance animation; consume global strike counter on result1; optional cue; copy/mirror attack rectangle; completed-animation virtual+0x44 transition |
| LS_DEAD | 0x43f450 | Mode0 field+0x38==-1/cue gate; modes1/2 unsigned delay gate; actor deletion flag0x10000 |
| LS_JUMP | 0x43f6e0 | Advance animation; grounded cleanup0x43f720 then virtual+0x44 |
| LS_BOUNCE | 0x43ff60 | Advance animation; actor type1 invokes virtual+0x78 |
| LS_EXPLODING | 0x440070 | One-time attack rectangle activation on animation result1; completed-animation deletion |
| LS_LIFTED | 0x4405b0 | Player image IDs42/43 gates; animation selection; player-facing mirror and relative X/Y placement; virtual+0x8c release |
| LS_THROWN | 0x440260 | Grounded animation/geometry/type/flag restoration; virtual+0x44 |
| LS_PAUSE | 0x43f540 | Unsigned timeout; resolve saved state's original name before replacing saved/current state |
| LS_DROPPED | 0x440a50 | Grounded horizontal stop; unsigned timeout; geometry/flags restoration and virtual+0x44 |
| LS_MOVEBACK | 0x43f980 | Advance animation; signed velocity/target crossing, collision bit0x10000 or saved-X equality elects virtual+0x44 |
| LS_MOVEAHEAD | 0x43fc20 | Same actual branch rule as MOVEBACK, at its separate original entry |
| LS_BLOCKHIGH | 0x440be0 | Completed-animation flags/transition; otherwise original horizontal velocity subtraction by +25/-25 without clamping |
| LS_BLOCKLOW | 0x440d50 | Separate original entry with the same complete rule |
| LS_FLAILING | 0x440870 | Advance animation; mirror from player private word0; relative X/Y offsets and extra ±4/+5 displacement |

FALLING/MOVINGLEFT/MOVINGRIGHT and HOME/IDLE are already supported by the frozen common runtime. Tests invoke actual original **0x43d490** dispatch for all19 registered identities, not merely direct callback tests. Lift/flail/attack rectangle mirroring executes recovered wrapping stores from original **0x406120 / 0x406150 / 0x406180 / 0x4060b0 / 0x406310** rules; actor left INT_MIN sentinels are preserved while embedded wrapper raw X bounds use their original unconditional flip stores.

## Hit selection and death entry

Registered **LogicHit0x4dc830 / LogicAttack0x4dc850** take an actor cdecl argument, resolve its primary+0x18 object and invoke virtual slots+0x14/+0x18. They do not themselves subtract health. Rat's+0x14 override47d780 remains in the Rat module; generic base+0x14 is **0x43e9e0**.

Generic hit0x43e9e0:

1. Compare player private+0xe8 with enemy+0x19c. Equal returns immediately; otherwise store the new counter **before** checking cooldown.
2. Reject while unsigned `tick - enemy3d0 < enemy3d4`.
3. Read attacker from actor+0x74. Its type+0xd0 selects virtual slots:2→+0x2c,0x20→+0x30,0x2000000→+0x34,0x10→+0x38,0x1000000→+0x3c,0x1000→+0x40. No guessed mask/name gate is added.
4. After the selected callback, signed defender health+0x10c<1 elects death virtual+0x5c with argument0.

Generic **0x404dd0** subtracts attacker damage+0x104 only while signed defender health is positive; subtraction wraps32bits. **0x404eb0** invokes current virtual+0x28 with the attacker, then executes **0x440e20** hit-particle coordinate/RNG preparation. Particle Y uses attacker attack-rectangle center when its left is enabled, translated and clamped against defender hit top/bottom. Rect-center addition wraps before signed division by2. The routine captures defender Z before two RNG calls, obtains Y jitter first then X jitter with signed `%9 -4`, and emits **0x461a00** with exact scene/X/Y/Z+0x2135/zero/defender arguments. Actual particle creation remains a scene allocation dependency.

Death entry **0x43f120** records mode+0x304, captures previous state+0x24, resolves LS_DEAD, stores enemy+0x20=1, sets actor flag0x80 and invokes recovered timer reset **0x43e9c0** with zero:

- Mode0 toggles bit0, changes actor Z to0x2134 only when needed and sets flag0x20000, chooses original voice/cue path from signed RNG `%100 <25`, restores original default XYZ bounds, sets actor type7, selects death animation through0x420a10, sets gravity2000/horizontal speed±150/vertical speed-700/Z speed0.
- Mode1 plays its enabled cue, sets stopped+0xc8=1, actor words+0x48=30/+0x44=0, render flag8, and unsigned1000ms delay.
- Mode2 plays its own direct0x4208e0 resource path **without adding an audio-enabled gate**, then performs the same stop/hide/delay stores.
- Mode3 uses its enabled cue, stops motion and immediately sets actor deletion flag0x10000.
- Other mode values preserve those branch-specific fields. All supported modes finally set bit4.

The same counter can therefore remain rejected after cooldown expires because the rejected call already consumed it. Death update compares unsigned elapsed time and deletes at equality, not one tick later. Host scene removal on the deletion flag is separate scheduling/lifecycle work.

## Additional recovered methods

**0x404f00** captures prior primary state and resolves LS_IDLE; **0x404ed0** does the same for LS_HOME. **0x43f720** clears actor flag4 and stores enemy+0x20=2. Verified empty **0x4c9e30** is recognized for the generic type0x1000 hit slot.

Jump entry **0x43f640** requires actor type1, installs cleanup0x43f720, stores horizontal/Z speed0/vertical speed-600, sets phase1/flag4/type8, resolves LS_JUMP and selects its animation. Bounce entry **0x43fe60** resolves LS_BOUNCE, sets type8, selects animation, adjusts vertical position by-1 and recomputes velocity with original energy arithmetic; it sets deltaY=-1 and multiplies horizontal/vertical velocity by1/3 and-1/3 respectively. Explosion entry **0x43ffa0** performs original actor flags/property/type/state/animation/cue/stopped/attack-activation stores.

Move-back entry **0x43f740** captures its initial side branch, uses signed RNG `%51 +75` and original truncated X to store its destination before any rejection, checks the matching physics X bound, performs repeated original tile probes with exact short-circuit order, stores horizontal speed±150/vertical and Z speed0, applies mirroring using the current side after dependency effects, resolves LS_MOVEBACK and selects animation.

Additional virtual entry/init helpers not exposed by this module remain explicit dependencies until their complete bodies are recovered. Coverage of every registered update callback does not imply every generic enemy method, all enemy subclasses, animation/resource bodies or whole-game behavior is complete.

## Differential and native verification

`Tests/compare_generic_enemy_states.py` and its owned helper import frozen test types/setup without editing them, build optimized native sources and run the hash-pinned original bodies. It passes **6,646 complete original calls**, **9,692 ordered dependency events with complete snapshots**, and records **1,702 original instruction addresses** after excluding CRT initialization. Included are200 generated comparisons for each of29 state/method entries, all19 exact registered state dispatches (20 cases each),336 retained generic hit/duplicate/death calls, cooldown/equality/wrapping-delay cases, all mode values including unknown values, and mutable32/64-bit bitset storage.

Every comparison includes actor128 / primary93 / secondary93 / contact93 / enemy264, attacker128, player private78, strike/audio globals and ordered event arguments. Larger backing is compared at boundaries and completion. Callback policies mutate state, facing, counter, phase, attacker type and audio gates to check read/call ordering. Original shared helper arithmetic, geometry, health, state dispatch and timer branches execute. Animation/RNG/named-registry/audio/particle creation and deliberately supplied subtype virtuals are adapted and logged. The tests do not replace a state body with expected native output.

```sh
work/test-env/bin/python Tests/compare_generic_enemy_states.py
```

Optimized headless Swift C-bridge verification passes health subtraction and mode1 death deletion at exactly1000ms:

```sh
clang++ -std=c++17 -Wall -Wextra -Werror -ffp-contract=off -O2 -c Sources/GenericEnemyStates.cpp -o work/generic-enemy-states-agent/GenericEnemyStates.o
xcrun swiftc -import-objc-header Sources/GenericEnemyStates.h work/generic-enemy-states-agent/main.swift work/generic-enemy-states-agent/GenericEnemyStates.o work/generic-enemy-agent/GenericEnemy.o work/generic-enemy-agent/PlayerPhysics.o -lc++ -o work/generic-enemy-states-agent/swift-enemy-state-tests
work/generic-enemy-states-agent/swift-enemy-state-tests
```

Link the frozen GenericEnemy.cpp and PlayerPhysics.cpp; Rat forwards pending common function identities through its existing dependency and can be integrated without editing frozen Rat source. Root owns native scene/animation/audio adapters, lifecycle and acceptance. No shared project/analysis edits, Xcode/device/simulator driving or extra agents are used.
