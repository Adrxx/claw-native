# CaptainClaw initial carry/throw dispatch

`PlayerCarryDispatchRuntime` covers the **whole original `415df0` call for initial state 5000 or 5001**. It composes the frozen `LiftThrowRuntime` bodies and the public `claw_player_input_epilogue` extracted unchanged by the parent. It does not elect another update from a state written during the first update, or use state 28 to reach the common tail.

The original executable is `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private Ghidra output is `work/player-carry-dispatch-agent/dispatcher.c`; its whole entry begins by capturing actor, primary (`actor+6c`), private (`primary+14`), and initial primary state (`primary+1c`). No source was recovered from a gameplay reference implementation.

| Initial state | Exact first body | Following path |
|---|---|---|
| 5000 | `41a850(actor, primary, private)` | common input epilogue |
| 5001 | `41b280(actor, primary, private)` | common input epilogue |

Both first bodies are already recovered in frozen `LiftThrowRuntime`. Their real timer, charge, held-target, bitset, virtual-method, physics, platform-offset, movement, and animation order is preserved by calling that module directly. The source tail cycles the weapon only on pressed bit 8 and private word 1 zero, consumes **stage** delta for invulnerability/private timers, invokes `41fc30`, applies signed coordinate clamps except state 5004, elects hazard damage through `4cd740`/`417c50`, clears the hazard flag on the original branches, and finally applies the cheat stores. Animation delta remains a separate live alias.

## Native integration

Call `claw_player_dispatch_carry(&model, &input, &context, liftService, commonService, user)` for the model's initial 5000/5001. Borrow the existing live `ClawLiftThrowContext`, physics, attack context, scene heap, and rich lift service. Set `actorToken`, `primaryToken`, and `privateToken` to the **original captured identities**, backed by at least 128/93/78 words. The model's actor primary pointer and heap's primary private pointer must initially match them.

The incoming model and input are authoritative at entry. The dispatcher exports actor/private buffers, state, bounds, invulnerability, the pressed/held/latched input words, physics, and source clock/powerup/pixel aliases. After the first original carry/throw body it imports those live values, then calls the frozen common epilogue. Every common dependency exports pending stores, passes original raw arguments, and imports callback changes before continuing. Captured primary/private identity stays fixed for this call even if a service changes actor pointer fields. Root can commit the returned model using its existing player/heap write-back hook.

| Common callback | ABI/receiver | Arguments |
|---|---|---|
| `420910` | thiscall scene sound registry, `*(actor+c)+28` | literal `524678` (`GAME_CLICK`) |
| `41fc30` | cdecl, receiver zero | actor, captured primary, captured private, current stage delta |
| `4cd740` | thiscall world, `*(actor+c)+24` | actor, 0 |
| `417c50` | cdecl, receiver zero | actor, captured primary, captured private |

The rich `ClawPlayerCarryDispatchDependency` should mutate the raw heap and borrowed physics/globals. Live `537230` (ignore hazards) and `537214` (cheat) are represented by the context's corresponding fields and imported after each callback. All other globals consumed by the carry/throw bodies remain in the borrowed lift context. The legacy `scene.call` fallback supports these four callbacks with their full argument lists, but still needs live alias publication.

Covered calls return 1; unsupported initial states return 0 without writes. `fault` distinguishes guarded invalid spans/identities (1) and propagated frozen lift failure. A service can set context `fault` to stop after importing its reached mutations. EAX=1 represents ordinary original completion only when fault is zero. No allocation or new player private lifetime is introduced by this adapter.

## Evidence and limits

Run:

```
work/test-env/bin/python Tests/compare_player_carry_dispatch_runtime.py
work/test-env/bin/python work/player-carry-dispatch-agent/run-sanitizers.py
```

The oracle executes the **whole original `415df0`** entry rather than calling only the carry/throw subroutine. It compares every byte of a 262144-byte raw token heap and the 196608-byte global image, meaningful EAX, and ordered service records containing those complete images. Directed cases cover input combinations, zero/positive/high-bit/wrapped deltas, separate clocks, timer expiry, throw charge/release, signed bounds, hazard flags, cheats, and callbacks that change the live input, delta, timers, bounds, state, and hazard/cheat aliases.

Retained histories load all 58 actual Level1 PowderKeg WWD records, execute the source derived Keg constructor and frozen source lift selector/target controller, then run complete `415df0` calls through carry, charge, release, and enemy flight/restore. The generic base constructor is a declared source-backed fixture at `4332f0`, already recovered elsewhere; its original instructions are not newly claimed here. Resource lookup/ANI completion, elected target, placement/collision, sound, powerup update, and damage remain finite explicit transports in this suite. Thus these profiles prove the scheduler/control/alias composition under those services; they do not establish retail ANI timing, real tile movement, physical sound, or full level behavior.

An original unmapped scene-root dereference after the carry update matches the guarded native reached prefix, including prior raw mutations. An explicitly cancelled external service also matches the complete original prefix stopped at that same boundary, with no subsequent hazard/cheat path. Unsupported-state immutability is checked separately. The private sanitizer runner replays a sampled set of original-verified full input/output histories and their exact top-level service mutation tapes against the same C++ implementation; ASAN/UBSAN confirms those native lifetimes, not another original execution. Final measured evidence: 832 complete dispatcher calls, 348 additional frozen lift/enemy calls, 58 source derived Keg constructors, 4309 ordered complete snapshots, and 2021 executed original instruction addresses. There are 52 sampled sanitizer histories. The JSON report records the exact scope and checks.

No shared player/input/lift sources, native host, project, device, or build files were edited by this worker. Parent integration and runtime acceptance remain separate.
