# Original shared enemy runtime

`Sources/GenericEnemy.h/.cpp` recovers a bounded original v1.0 common enemy layer: complete base constructor **0x4332f0**, shared FSM **0x4dc870**, generic state dispatch **0x43d490**, sensing **0x43e420**, movement/collision response **0x4dca10 / 0x43dfa0**, pre/post wrappers **0x404fc0 / 0x4063b0**, actual walk starts/updates **0x43fcb0 / 0x43fd60 / 0x43fd10 / 0x43fdc0**, falling update **0x43edd0**, deletion wrapper **0x43e9b0**, and actual empty common callback **0x4bb030**. Gameplay subtype overrides, resource/binder dependencies, remaining common state families, collision queries/resolution and animation bodies remain explicit adapters.

Profile: `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Branches, stores, callback identities and ordering come from original instructions. No CrazyHook or reference gameplay implementation is copied. Starting Rat decompilations were read without editing; further bounded output and a separately cloned Ghidra project are private `work/generic-enemy-agent/`.

## Stable runtime and integration

`ClawGenericEnemy` retains complete **actor128 / primary93 / secondary93 / contact93 / enemy264** word snapshots. Enemy allocation is 0x420 bytes. All pointer fields remain opaque 32-bit identities. `ClawGenericEnemyContext` supplies represented object identities, player/platform actor snapshots, absolute tick537210, animation delta5430c4, level word534eac, forced RNG flag541334, hit mode from537960+44, original default words513e10..513e6f, current virtual function identities, and a resolved state registry view.

The header's `soundRegistryToken` denotes only the observed **actor scene+0x28 manager -> +0x10 registry**. That historical API field label does not prove the GAME_ entries are audio. `tileManagerToken` denotes scene+0x24. The host maps these identities to supported native dependencies.

```c
void claw_generic_enemy_context_defaults(context);
uint32_t claw_generic_enemy_construct(state, context, dependency, user);
uint32_t claw_generic_enemy_tick(state, context, dependency, user);
uint32_t claw_generic_enemy_dispatch(state, context, stateID, dependency, user);
uint32_t claw_generic_enemy_pre(state, context, dependency, user);
uint32_t claw_generic_enemy_post(state, context, dependency, user);
uint32_t claw_generic_enemy_motion(state, context, dependency, user);
uint32_t claw_generic_enemy_entry(state, context, originalFunction, argument, dependency, user);
```

Return one is native completion/support status and zero is unsupported or invalid native input. Most original callbacks return zero or are void, and the constructor returns its original receiver; the wrapper's status is not claimed to be those incidental EAX values. FSM0x4dc870 itself originally returns one. Unsupported entries preserve the API boundary rather than inventing gameplay. Named starts without an adapter can resolve through the supplied state-name view; a missing name can return zero after velocity/saved-state stores, so no rollback is claimed. Callers must supply valid state entries and callback identities for paths they execute.

The actor references inside the enemy and embedded wrapper correspond to the same represented actor, and primary references correspond to the supplied primary buffer. Constructor callbacks must preserve those identities. Arbitrary polymorphic aliasing, retargeting pointers, malformed original buffers, exception unwinding and allocation-failure behavior outside declared adapters are not included. Runtime sensing/motion comparisons use finite valid embedded physics values. A supplied <=32-bit bitset uses enemy+0x300; larger valid bitsets use the caller's backing pointer, representing its original +0x300 identity. Current shared routines inspect bits zero through four and preserve that backing.

Rat can include this header and wrap its context with Rat-specific globals, image metadata and attacker/projectile snapshots. Its dependency dispatcher receives rich `ClawGenericEnemyCall { function, receiver, argumentCount, arguments[12], name }`. Each argument is the original 32-bit scalar/token value. The callback returns low32 for EAX; the API also reserves IEEE double bits for explicitly floating dependencies, although the presently recovered common layer computes its floating helpers natively. Callbacks may mutate represented buffers/context before subsequent original reads. OS/resource callbacks remain distinct from recovered field stores and movement branches.

## Constructor and preserved allocation words

Complete **0x4332f0** calls and recovers its common actor wrapper **0x4082f0**, physics constructor **0x4080a0**, physics initializer **0x408220**, initial motion **0x4dca10**, embedded actor/inventory wrapper **0x408370**, CString empty initialization, and inline bitset setup/copy/set bodies. Its earlier LogicHit/LogicAttack binders **0x4c7fa0 / 0x4c8060** are explicit dependencies; no callback body runs during binding. The comparison executes their actual original bodies for the missing-metadata profile and adapts only registry lookup. Present binding effects remain the host's responsibility, with secondary binding separately recovered in ActorResourceBindings.

The constructor profile uses the original initial empty534938 bit string and default533470 size32. It sets inline bit9, and bit2 when signed primary+0x64 is positive. General user-modified default bit strings or larger constructor bitset allocations are outside this constructor profile; runtime larger backing is independently covered.

Important observed stores include actor type+0xcc=7, actor flags |=0x80000, generic vtable0x50b16c, saved configuration ID from primary+0x168, sensed region+0x184=6, delay gate+0x188=0, common embedded actor identities+0x128/+0x12c, and primary identity+0x130. Inventory wrapper takes eight primary values in order f0/f8/f4/fc/100/108/104/10c, followed by actor+100; count and nonzero-count stores are retained. It looks up GAME_SPLASH, GAME_HIT1 through GAME_HIT4, and GAME_PURELEASE1 in original order. Final vertical acceleration is **2000**. Fields with no original store remain caller allocation seeds, including the second sensing range/height+0x294/+0x298; zero-filled native allocation is a separate host policy.

The final mirroring branch checks the same actor render flag twice. In this constructor's same-actor wrapper profile it is unreachable; no fabricated rectangle flip is inserted.

## Exact shared FSM and movement

FSM **0x4dc870** captures primary state+0x1c once. It resolves that state's string buffer, calls current virtual+4 with the name token, current virtual+8 with the captured ID, resolves the **same captured ID** again, and calls current virtual+c with its name token. Callback mutations to primary state do not replace the captured ID. Virtual function identities are reread for each stage through context.

Pre wrapper **0x404fc0** stores signed original RNG `%1001` at enemy+0x3c4, or0x1fffffff when the global forced flag is nonzero, then executes sensing. Sensing first sets side+0x18c by player X, and skips rectangle/region updates for level word0x26b7 or bit1. It builds five rectangles clamped to physics X bounds plus/minus common range+0x2a4, selects innermost first using Win32 **right/bottom-exclusive** point inclusion, then handles actor+0x38==-1 and the unsigned500ms delayed far-region transition.

Post wrapper **0x4063b0** executes queued cleanup+0x18 only when queued transition+0x14 exists and primary state matches+0x1c, clears cleanup after the callback, invokes the current queued transition, clears it, sets expected state1001, then invokes current virtual+0x24. Reads and clears occur after callbacks in original order.

Motion **0x4dca10** saves truncated prior X/Y+0x118/+0x11c, updates the existing recovered **0x403b40** physics body for `unsigned(tick)*global513e48 - elapsed`, applies platform deltas when actor flag0x10 and platform identity are present, and invokes actual collision resolver boundary **0x4cbb60** with actor/X/Y/options. Type1 uses current actor Y and clears vertical velocity; other types clear flag0x10 and pass physics Y. It adjusts physics position, velocity and delta when collision changes integer actor coordinates, using recovered original **0x420af0 / 0x420b60** energy helpers. Collision flags0x800000/0x40000/0x80000 preserve vertical bounce, upper/lower X-bound stores, and original global speed scaling with precedence.

Post **0x43dfa0** first executes that actual motion body. Its0x100000 collision gate resolves current state name, excludes LS_DEAD or bit4, and dispatches virtual+0x5c with original hit-mode arguments2/3. Otherwise grounded bit3 with bit2 clear probes original tile query **0x4207f0**, retaining repeated queries and short-circuit order, and can restore saved position and set the matching X boundary. Final actor positions use original truncation. Bit0 chooses Z with saved base+0x2d0 and offsets4000/3899 using player/actor floor relation, setting actor0x20000 only when Z changes.

Walk-start **0x43fcb0 / 0x43fd60** stores signed horizontal speed (left uses wrapping unary negation), captures previous primary state in enemy+0x24, resolves LS_MOVINGLEFT/LS_MOVINGRIGHT by name, stores primary state, copies actor+0x190 to enemy+0x134, and selects enemy+0x354 animation through **0x4c8220**. Walk updates execute **0x4c82a0** first. At minimum X, left walk invokes virtual+0x70 with `ftol(-velocityX)`; at maximum X, right walk invokes virtual+0x6c with `ftol(velocityX)`. These endpoint arguments cannot be recovered from the decompiler's unbound `__ftol` result alone; they were verified against actual instructions and directed comparisons. Falling update advances animation and invokes virtual+0x48 when actor type1. Common0x4bb030 is actual `xor eax,eax; ret`; deletion wrapper0x43e9b0 invokes0x48cf50(actor).

## State-registration evidence and remaining families

Private `capture_shared_registration.py` executes original **0x43d5b0** with explicit dictionary/value-storage/CString adapters and captures **19 ordered name→callback registrations**, including HOME/IDLE→0x4bb030, MOVINGLEFT→0x43fd10, MOVINGRIGHT→0x43fdc0 and FALLING→0x43edd0. Repeating registration leaves names/IDs unchanged. Original image nextID52712c starts2000. The generated `shared-registrations.json` records fresh shared-only IDs2000..2018 and clearly labels the profile. **Those numbers are not proof of the full game's boot ordering.** The runtime requires the host's verified resolved metadata and does not hardcode these IDs.

Shared registered strike/dead/jump/bounce/explosion/lift/throw/pause/drop/moveback/moveahead/block/flail bodies remain separate required recovery. Their recovered registration identities may be dispatched only through explicit host adapters until their complete bodies are proved. Rat constructors and Rat-specific overrides are owned by the Rat worker. Scene list traversal, scheduling and game acceptance are owned by the coordinator.

## Verification

`Tests/compare_generic_enemy.py` builds optimized C++ with floating contraction disabled and executes the hash-pinned original routines in Unicorn. It passes **3,835 complete original calls**, including200 generated calls for each of15 entries, **259 directed cases**, and **576 retained-buffer chain calls**. It compares all actor128 / primary93 / secondary93 / contact93 / enemy264 words and **7,317 ordered dependency events with complete snapshots at each event**, recording **2,607 original instruction addresses** after excluding CRT initialization.

Coverage includes random allocation seeds; subtype/current state/type/flag/bit combinations; collision response precedence; tile-query short circuits; platform motion; callback state changes; constructor/resource ordering; signed speed including INT_MIN wrapping; walk endpoints; sensing region edges and500ms unsigned wrap; queued transitions; captured-state pre/state/post mutation; inline and larger bit storage; and32 histories with consecutive common constructor/start/ticks. Win32 SetRect/SetRectEmpty/PtInRect and external collision/tile/animation/resource/subtype callbacks are adapted. Original constructor subhelpers, arithmetic, shared loops/branches, energy helpers and physics bodies execute rather than being replaced by their native output. Complete original higher-level collision/animation/subtype gameplay behavior is therefore not claimed.

```sh
work/test-env/bin/python Tests/compare_generic_enemy.py
work/test-env/bin/python work/generic-enemy-agent/capture_shared_registration.py
```

Optimized native Swift C-bridge verification also passes same-actor wrapper construction, type7/default bitset, right-walk named state selection, and fractional position/gravity accumulation across two collision-adapted ticks. It runs headlessly and uses no application sources or device.

```sh
clang++ -std=c++17 -Wall -Wextra -Werror -ffp-contract=off -O2 -c Sources/GenericEnemy.cpp -o work/generic-enemy-agent/GenericEnemy.o
clang++ -std=c++17 -Wall -Wextra -Werror -ffp-contract=off -O2 -c Sources/PlayerPhysics.cpp -o work/generic-enemy-agent/PlayerPhysics.o
xcrun swiftc -import-objc-header Sources/GenericEnemy.h work/generic-enemy-agent/main.swift work/generic-enemy-agent/GenericEnemy.o work/generic-enemy-agent/PlayerPhysics.o -lc++ -o work/generic-enemy-agent/swift-enemy-tests
work/generic-enemy-agent/swift-enemy-tests
```

The new C++ source links the already recovered PlayerPhysics.cpp without editing it. No shared source/project/analysis writes, Xcode builds, device/simulator driving or extra agents are used. This bounded shared layer does not establish full enemy or game parity.
