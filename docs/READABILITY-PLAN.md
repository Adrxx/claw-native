# Recovered-code readability plan

Proposed on 2026-10-29 for owner review. This is a plan, not a code change or a
claim that gameplay or iPad acceptance is complete. The queue records all five
prerequisites of `readability-pass-plan` as done. Some finish notes retain limits:
raw-object standalone comparison is not proof of an app caller, and the semantic
closure and snapshot tasks still need separate work. Readability must not hide or
close those gaps.

## Approval and scope

The owner approved the plan on 2026-10-29 and requested an accessor-form second
round of the first pilot. `readability-pilot-review` remains the owner-only hold
before the rest of the rollout. Each remaining task waits for that review and
its predecessor. Queue order alone is not approval; this work does not authorize
a commit, push or merge.

The first rollout covers the mod-facing player, checkpoints and persistence,
then adjacent state, version 1.3, actor storage and collision families, then native
Swift hosts. Each numbered family is its own task, not one enormous cleanup.
Remaining enemy/boss/object, menu/resource and presentation families follow the
same procedure after the owner reviews an expanded family list. This is an
explicit first rollout, not a claim that these families exhaust the recovered
code. Do not recertify CRT, MFC or Windows implementations as part of it; keep
native platform replacements native. Do not implement mods or change game rules.

## Shared layouts without changing memory

The first player family pilots `Sources/ClawRecoveredLayout.h` and
`Sources/ClawRecoveredNames.h`; introduce only the definitions that family uses.
Keep them out of umbrella headers until consumers are deliberately migrated.
Add `docs/READABILITY-NAMES.json` as the reviewed naming map, not a new status log.
Subsequent tasks extend it only for their owned fields and functions.

Use transport-bound field views in the implementation: `ActorFields actor{run,
actorToken}` followed by `actor.holder()`, `LogicHolderFields` for logic/state,
and `ActorContextFields` for context writes. A token wrapper plus literal-offset
reads is not the intended style. Keep construction free of guest reads, and
leave each getter/setter at the original access point, including repeated reads
after callbacks. The pilot covers the six established prefix fields; other
layouts need evidence before naming them.

Use a shared actor prefix and separate player-private, checkpoint, save-manager
and profile-record definitions. Version 1.0 and version 1.3 layouts are separate
unless their equality is established. Reuse existing correct definitions first.
A token remains a 32-bit token; it never becomes a native pointer stored in the
recovered record. Preserve field width, signedness, byte order, alignment, size,
padding bytes, aliasing, allocation and lifetime. Check every materialized layout
with `sizeof`, `alignof` and `offsetof` assertions against its existing contract.
Do not cast arbitrary heap storage to a C++ struct: use named typed views over the
existing byte/token accessors where alignment, lifetime or aliasing is uncertain.
Do not replace packed flags with compiler bitfields or change the wire format.

Names require evidence from the owning implementation and existing specification.
Unknown fields remain `unknown_0x148`, not a guessed semantic name. Conflicting
interpretations get separate view types. The example `actor + 0x148` identifies
an offset to investigate; this plan does not assert what that field means.

## Naming map and arithmetic

Each map entry records family, executable profile, original entry or field offset,
old identifier, proposed name, width/signedness/units, evidence location and
confidence. For functions also record ABI, receiver, argument order, return and
fault behavior. Preserve original addresses in dispatch tables and comments so
oracle ownership remains traceable. Keep exported C ABI symbols and generated
entry points stable; put the implementation in behavior-named functions rather
than aliases to address-named bodies. Keep the original address-to-body switch
or registration table. Do not
hand-edit generated dispatch tables or broaden canonical ownership.

| Existing form | Planned readable form | Condition |
| --- | --- | --- |
| Actor plus a raw byte offset | Named field/view accessor | Same byte access and established meaning |
| Address-only internal function | Verb describing its actual action | Address/profile retained in map and dispatch |
| Millisecond counter | Name ending in `Milliseconds` | Proven units; preserve wrap and signed comparisons |
| `function`, `receiver`, `arguments` at ABI boundary | Keep ABI vocabulary; name local semantic values | Do not pretend a token is a host pointer |
| Multiply/shift division idiom | Ordinary division with explicit integer type | Proven equivalent on the complete reachable domain |

For the `0x10624dd3` multiply/shift example, do not mechanically write `/ 1000`:
first establish operand width, signedness, high-half operation, shift, correction
and rounding. Preserve overflow, negative-input truncation, wrap, x87 precision,
conversion behavior and evaluation/service order. If the existing tests cannot
establish the domain, retain the expression and explain it. Readability alone is
not authority to fix suspicious behavior or normalize error paths.

## Family verification contract

Owner rule, 2026-10-29: if the named-layout mutation mode exposes non-equivalent survivors that the unchanged
cases cannot kill, a fresh case-author worker may add original-backed cases covering those paths. Existing cases
are never removed, reseeded or weakened; the finish note records the survivor sites and the added cases.

Coordinator rule, 2026-10-30 (owner delegated overnight decisions): a new named-layout mutant may be recorded as
equivalent only when fresh translator and case-author audits both prove it unobservable in the original; otherwise
add original-backed cases. Scores are then compared over the remaining valid mutants.

1. Before editing, resolve the family's current specification, canonical sources,
   shared sources, sealed cases, fixtures and retained gate record. Confirm it is
   still the elected game-code owner; overlapping retired legacy bodies are not
   a substitute. Capture hashes of specification/cases/fixtures and the baseline
   oracle result, original-address coverage and exemptions, mutation score,
   killed/valid/invalid counts, mutation seed and sanitizer/compiler settings.
   Refresh only this baseline if its inputs are stale. Keep local evidence under
   `work/readability/<family>/`.
2. Use a fresh translator worker for source edits. The coordinator never edits
   recovered translation sources. A fresh case-author worker audits the unchanged
   cases/baseline read-only; it must not add, remove, reseed or reseal cases for
   this pass. Follow the existing role instructions. This is not new recovery.
3. Apply one coherent rename/layout/arithmetic/comment change at a time. Preserve
   all original reads, writes, call order, error behavior, outputs and ABI. Explain
   why nonobvious arithmetic and offsets are faithful; avoid narrating every line.
4. Run `make oracle FAMILY=<family>`, then
   `make gate FAMILY=<family> ARGS='--record --jobs 1'` for the changed family.
   Require admission, identical oracle outputs and original-address coverage,
   unchanged exemptions and equal or stronger mutation results with the same
   seed and controls. Opt each migrated family into `"mutation": "named-layout"`
   and list both recovered headers in its `sources`, as documented in
   `Tests/clawparity/README.md` under "Opt-in named-layout mutations". Use direct
   typed view variables, one accessor call per line, checked `offsetof` fields,
   and the default accessor delta. Use explicit integral enum values or literal
   integral `constexpr` constants. Preserve the legacy mutation sample and
   inspect the additional field, named-call and constant mutants; compare
   kills, invalids and survivors, not the aggregate score alone. The pilot floor
   is 36 kills and 0.947, with no new equivalence exclusions. A changed population
   requires this explicit review, never a lowered threshold. Preserve the
   baseline record before `--record` replaces it. Keep existing large case sets
   unchanged; the approximately 600-case rule is not permission to trim them.
5. Compare hashes to prove no case, fixture, executable profile, threshold,
   exemption or specification behavior contract changed. Only the named-layout
   opt-in, required header build inputs and generated admission evidence may
   change in the specification. If shared layout/header input changed, gate
   every actual admitted consumer whose inputs changed, sequentially. Pilot
   consumers narrowly to keep that set small. Generated membership changes use
   the existing generator and `make project-check`, never hand-edited registries.
6. Retain a change only after these checks pass. Revert only this task's failing
   edits if parity cannot be preserved; do not revert another session's work.
   Record the exact commands and comparison in the queue finish note. A needed
   behavior fix belongs to a separately authorized task, with its own check.

No task edits `Tests/clawparity/`. Serialize gates/builds/emulation and check
`sysctl -n vm.loadavg` before each; wait while it is 16 or higher. Do not run a
full gate sweep or full app regression suite for a local readability change.

## Per-family order

The family IDs below come from existing queue ownership/results, not a new census.
The current specification is authoritative at execution time. If ownership has
moved, update this plan and task to the actual owner before editing; never revive
a retired overlapping implementation just because its name sounds suitable.

| Order | Family | Focus |
| --- | --- | --- |
| 1 | `level_one_player_actions_01` | Player actions and the first layout/name pilot |
| 2 | `level_one_player_actions_02` | Player carry and action dispatch |
| 3 | `level_one_player_actions_03` | Player animation, powerups and action state |
| 4 | `level_one_player_actions_04` | Player service and state helpers |
| 5 | `level_one_player_actions_04b` | Player x87-return helpers |
| 6 | `level_one_claw_states_01` | Player standing and input states |
| 7 | `level_one_claw_states_02` | Player air and pose states |
| 8 | `checkpoint_logic` | Ordinary and super-checkpoint interactions |
| 9 | `level_one_timers_checkpoints_02` | Checkpoint and timer state |
| 10 | `level_one_hud_timers_01` | HUD timer display and units |
| 11 | `level_one_super_checkpoint_01` | Persistent super-checkpoint records |
| 12 | `save_load` | Save manager, profile selection and load |
| 13 | `player_cache_application` | Selected-player cache and application handoff |
| 14 | `v13_profiles` | Version 1.3 profile changes |
| 15 | `level_one_batch_claw_death_01` | Player death state and services |
| 16 | `level_one_batch_respawn_01` | Death and restart transitions |
| 17 | `level_one_batch_respawn_02` | Respawn actor cleanup |
| 18 | `level_one_batch_claw_powerups_01` | Player powerup lifecycle |
| 19 | `v13_cheat_movement` | Version 1.3 movement and turbo |
| 20 | `v13_cheat_attack` | Version 1.3 attack bounds |
| 21 | `v13_cheat_input` | Version 1.3 cheat input |
| 22 | `v13_cheat_dispatch` | Version 1.3 command dispatch |
| 23 | `v13_contact_bindings` | Version 1.3 contact bindings |
| 24 | `v13_raw_lifecycle` | Version 1.3 raw-object lifecycle |
| 25 | `v13_raw_fields` | Version 1.3 raw-object fields |
| 26 | `v13_raw_children` | Version 1.3 child serialization |
| 27 | `level_one_actor_storage_01` | Actor allocation and storage |
| 28 | `level_one_actor_storage_02` | Actor containers and ownership |
| 29 | `level_one_collision_dispatch_01` | Collision dispatch |
| 30 | `level_one_collision_dispatch_02` | Collision response |
| 31 | `level_one_world_collision_03` | World and tile collision |


## Native Swift naming, layout and comments

Native tasks follow the families in the table, in the order below. Keep the
current `ClawNative*.swift` service boundaries. Begin by expanding compressed
statements, naming constants/locals and grouping methods into lifecycle,
entry/dispatch, physical services and snapshot persistence sections. Extract a
private helper only when call, fault and lifetime order remain obvious. Split a
file only when one responsibility can move intact; preserve visibility and use
the existing project generator for membership. No global directory reorganization.

Keep callback numbers as stable dispatch identities, with named constants beside
them where useful. Distinguish actor tokens, byte counts and word counts; retain
`&+`/`&-`, truncating conversions and bit patterns. Document `Unmanaged` ownership,
pointer validity during synchronous calls, fault propagation, source-vs-native
service responsibilities and clocks. Do not change actor isolation, scheduling,
callback capture ownership, collection traversal order or initialization order.

In checkpoints, distinguish ordinary death checkpoints from persistent super
checkpoints. In saving, retain recovered ownership of CLAW.USR and native ownership
of transport and app metadata. A rename of a Codable property can change disk
bytes: preserve keys explicitly or retain the property name. Preserve snapshot
schemas, token identities, save bytes/checksums, paths, native selectors,
accessibility identifiers, UI text, diagnostics and CLI flags. Do not rewrite stale
product wording during this structural pass.

1. `app-readability-player`: Player and input hosts. Files: `Sources/ClawNativePlayer.swift`, `Sources/ClawNativePlayerServices.swift`, `Sources/ClawNativePlayerView.swift`, `Sources/ClawNativeWindowInputQueue.swift`. Focused checks: `scripts/check-native-player.sh`, `CLAW_CONFIG=Release work/new-game/regressions.sh menu_controls`.
2. `app-readability-checkpoints`: Checkpoint and respawn hosts. Files: `Sources/ClawNativeCheckpoints.swift`, `Sources/ClawNativeRespawn.swift`. Focused checks: `CLAW_CONFIG=Release work/new-game/regressions.sh level_two pause_gameover`.
3. `app-readability-save`: Save transport and profile host. Files: `Sources/ClawNativeSave.swift`. Focused checks: `work/test-env/bin/python work/save-load/check-round-trip.py`, `CLAW_CONFIG=Release work/new-game/regressions.sh save_load`, `work/test-env/bin/python scripts/check-v13-profiles.py`.
4. `app-readability-scene`: Canonical dispatch and scene orchestration. Files: `Sources/ClawNativeCanonicalHost.swift`, `Sources/ClawNativeScene.swift`, `Sources/ClawNativeObjectConnections.swift`, `Sources/ClawNativeObjectLoader.swift`, `Sources/ClawNativeFrame.swift`. Focused checks: `scripts/check-native-player.sh`, `work/test-env/bin/python scripts/check-v13-contact.py`, `work/test-env/bin/python scripts/check-v13-enemy-lifecycle.py`, `work/test-env/bin/python scripts/check-v13-raw-object-join.py`.
5. `app-readability-presentation`: Rendering, audio and native view boundaries. Files: `Sources/ClawNativeRendering.swift`, `Sources/ClawNativeCamera.swift`, `Sources/ClawNativeHUD.swift`, `Sources/ClawNativeAudio.swift`, `Sources/ClawNativeDisplay.swift`. Focused checks: `CLAW_CONFIG=Release work/new-game/regressions.sh ingame_audio`, `work/test-env/bin/python scripts/check-v13-enemy-death-sound.py`.

For each native task, capture a passing baseline of its listed focused checks
before editing, then rerun only those checks after editing. Read the check's
invocation before use; preserve authentic original references and version
selection. A baseline failure must be isolated and reported, never rebased away.
Check join boundaries with the existing original/native comparisons, including
missing-service controls; do not claim that a family gate proves a Swift host.
If any recovered family inputs change, apply the family gate contract as well.
Keep owner saves intact and use isolated test storage. Launch only through
`scripts/run-mac.sh`, always `--mute` for execution, and close only owned PIDs.
Use `scripts/real_input.py` for any input acceptance the selected check requires.

Every task changing app code leaves a fresh Release build through
`CLAW_CONFIG=Release scripts/run-mac.sh --version-only`, using its assigned
`CLAW_DERIVED_DATA`, and verifies the canonical output at
`work/MacCatalyst/Build/Products/Release-maccatalyst`. Build success is separate
from comparison, real-input and device acceptance. A documentation-only task
runs no app checks, gate or build.

## Review checklist and completion

The owner reviews the layout policy, evidence-backed naming, arithmetic limits,
family sequence, native file boundaries and exact unchanged-test gate rule. The
owner may narrow the remaining rollout in `readability-pilot-review`. Each
subsequent task requires that approval plus its finished predecessor;
release blocked tasks through the queue workflow, not by assuming dependencies
are enforced by ordering. No implementation or merge is authorized by a planning
finish note alone.

The planning task is complete when this document exists, every table row and all
five native batches have corresponding ordered queue tasks, all implementation
tasks have the owner-review hold, and the queue parses with unique task IDs. No
owner review, implementation, admission refresh or gameplay acceptance is claimed
by this plan's existence. Later rollout expansion must name actual current
families and checks before creating its per-family tasks; do not add a broad
unbounded cleanup task.
