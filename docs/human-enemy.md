# Original CHumanEnemy shared controller layer

`HumanEnemy.h/.cpp` recover the required Human base/constructor, state dispatch,
pre/post processing, typed hit routing, death/loot trigger, HOME entry, patrol
return, thrown entry and deletion handler, plus all twelve registered Human
state controllers. The layer composes the frozen GenericEnemy,
GenericEnemyStates and PlayerPhysics APIs. It does not claim complete Human
combat or whole-game parity: remaining gameplay bodies are named below.

Profile: `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Private evidence is `work/human-enemy-agent`; additional read-only bounded
decompiles are in `work/officer-agent`. Actual instructions and complete
buffer/callback snapshots supply the comparison oracle. Private Ghidra logs
were checked for script errors, and no shared project was opened.

## ABI and composition

`ClawHumanEnemy` aliases the unchanged `ClawGenericEnemy`. The separate
`ClawHumanEnemyContext` holds **pointer views** into the caller's generic,
shared-state, tail, effect, other-actor and platform-primary buffers. Officer
can point these directly into its frozen context; no Officer source/header
edit or copied structure ABI is required. Concatenate generic enemy264 and
the twenty tail words to represent original words0..283 at dependency
boundaries. The original Human allocation extends through `+0x44c`; Officer
adds its own fields through `+0x46c`. Those unrelated tail words are preserved.

`claw_human_enemy_entry` dispatches by verified original identity, returning
native support/completion separately from original integer results. Original
void routines' residual EAX is not presented as a meaningful gameplay result.
Constructor results are the original enemy identity token; registered state
callbacks and the recovered entry methods return their observed zero result.
`claw_human_enemy_dispatch` supplies `0x44c840`; the constructor convenience
supplies `0x44c000`. Unknown entries return zero without a generic substitute.

The original dependency ABI remains `ClawGenericEnemyDependency`. Callbacks
can mutate represented buffers; later reads preserve original order. The host
must keep duplicate views consistent when identities alias: shared attacker
and other actor, actor `+0x80` and represented platform, effect identity and
effect actor, player/private data, generic clock global and Human countdown.
Effects and cross-actor buffers are caller-owned views, not native pointer
casts of original 32-bit tokens.

Supply the captured complete Human class function table, including zero
callback entries for IDs with only common behavior. Missing metadata is an
explicit scope fault; an observed zero callback falls through to frozen
common state dispatch. Numeric IDs are runtime registration results, never
hardcoded guesses. Generic context supplies the global name/function metadata.

## Recovered entries

| Entry | Behavior |
| --- | --- |
| `44bc60` | Exact underlying base stores, LogicHit/LogicAttack binding, physics setup and common motion |
| `44c000` | Embedded wrappers, CString/bitset initialization profile, resources, masks/rectangles, Human extension and scaled health/damage/range |
| `44c840` | Captured Human class dispatch with common fallback |
| `44d000` | Random/pre processing, literal-pointer attack gates, attack rectangle/facing, spring/platform state changes, queued decisions |
| `44d3c0` | Queued saved/current callback order, virtual common post and existing effect lifetime/position |
| `44df60` | Attacker flag priority selects FIRE/ICE death sequence, fallback GAME_NULL, then frozen generic hit routing |
| `44e0c0` | Death mode store, loot trigger when bit4 is clear, then frozen generic death entry |
| `44d9f0` | Zero X velocity, save old state and enter HOME |
| `44edd0` | Bit2 HOME gate or asymmetric endpoint patrol selection and PACING animation |
| `44df10` | Exact signed random cue gate and common lifted/release dependency |
| `44cfd0` | Frozen actor deletion notification, then mark/clear existing effect |
| `44ebb0` / `4a1180` | Native fast-advance/advance entry: face, velocity, saved/current state and sequence |
| `44f840` | Queued virtual HOME selector |
| `44f6e0` | Spring release random horizontal velocity, corrected vertical position/velocity, flags/state/sequence |
| `44e120` | Wrapping integer distance gate, jump-at-Claw entry and exact ballistic velocity, otherwise bit2/HOME |
| `44d760` | Reset bounds, virtual acceleration initialization, then exact aim toward attacker primary `+2c/+34` |

Constructor tuning globals are supplied as the three original floats
damage/health/range. Integer conversion retains the low signed64 truncation
word and the original unsigned range clamp (`<100` becomes99), including
negative, zero and fractional scale cases. Original allocation seed words
not written by the constructor remain intact. The original initial empty
bit string/global size32 profile is used; arbitrary modified constructor bit
strings/growth are outside this API's scope.

Ghidra's signed-looking constructor clock decompilation is misleading. At
`44bf34` the high stack word is zero; `44bf42..48` writes `537210` as the low
word; `44bf50` executes **FILD qword**, zero-extending the 32-bit frame clock.
Likewise `513e40` maximum-delta input is zero-extended before FILD. Native
comparison at `0x80000000/0xffffffff` established this unsigned behavior.
The constructor uses the hash-pinned double `50e008=0.001`.

Aiming retains original scalar operation order and precision53. In particular,
acceleration and distance squares add X then Y then Z. Reversing those sums
failed complete velocity words by several ULPs on directed original cases.
Spring vertical correction preserves its own arithmetic order. Finite
constructed physics is the supported profile; unsupported/nonfinite aliasing
is not used to claim additional coverage.

## Twelve registered Human callbacks

The original class table at `537878` is registered by `44c950`:

| Name | Callback | Covered controller behavior |
| --- | --- | --- |
| LS_BOUNCE | `44dd30` | Saved PAUSE-name gate; timeout cue/loot/delete order; common bounce fallback |
| LS_THROWN | `44de50` | Animation, wrapping timeout cue/loot/delete order, grounded virtual selection |
| LS_JUMPATCLAW | `44e510` | Animation, facing normalization and grounded selection |
| LS_JUMPBACK | `44ea10` | Animation, grounded render-bit clear, virtual selection then mode2 |
| LS_ADVANCE | `44ea60` | Endpoint selection, facing, ordinary speed and situation branches |
| LS_FASTADVANCE | `44ec80` | Direction-sensitive endpoint test, animation/random order, situation branches and fast speed |
| LS_PACING | `44ef70` | Two independent endpoint/random tests, reversal, platform visibility and HOME gates |
| LS_IDLE | `44f290` | Platform visibility, random situation selection and wrapping return timer |
| LS_HITLOW | `44f490` | Animation completion virtual selection/mode2, otherwise fixed25 X deceleration |
| LS_HITHIGH | `44f660` | Same observed shared hit-controller body |
| LS_HOME | `44da20` | Current HOME-name gate, facing/random, movement/attack/sequence/pause branches |
| LS_JUMPOFFSPRINGBOARD | `44f800` | Animation, grounded zero X velocity then selection |

Hit deceleration is a fixed per-call amount, not multiplied by animation or
stage delta. Endpoint and timer comparisons, 32-bit wrap, equal-coordinate
cases, queue retention and callback order are reproduced.

## Name pointer identity

Human pre `44d000` compares its argument to seven original literal addresses:
STRIKE `52720c`, JUMP `527204`, JUMPBACK `527da0`, DEAD `5234f4`, LIFTED
`5271d8`, THROWN `5271cc`, DROPPED `5271b4`. It does **not** compare text.
The native layer retains these exact identity comparisons.

The registry worker's actual whole `401000` execution verified that every
nonempty name is copied by `4f66cc→4f6650` into allocated CString data;
`537698` stores those heap tokens, never the corresponding literals. With
its explicit allocator arena, LS_DEAD ID2004 had name data `300110c` versus
literal `5234f4`, and JUMPBACK ID2020 had data `3001b4c` versus `527da0`.
Heap addresses depend on allocation. Thus the exclusions are **unequal** when
the pre argument comes from actual registry CString data. Keep root's
host-owned CString name token distinct from a first-registration literal
token; replacing this with text equality would change game behavior.
Directed comparisons cover both copied-name and direct-literal arguments.

## Explicit remaining boundaries

Common lifted/release entry `440420`, common ledge query `43eab0`, and wrapper
loot `42df90` remain gameplay dependencies. Human typed attack methods
`44d460/44d570/44d5a0/44d700/44d730`, and hit-entry helpers `44f3c0/44f510`,
remain explicit calls when selected through the polymorphic hit path. Their
internal damage effects, effect creation, loot allocation and lift setup are
not replaced by guessed behavior. This module exposes the actual calls and
arguments while providing the surrounding controller state changes.

Other dependencies are animation/resource registry, audio pools, scene and
collision services, caller overrides and supported frozen common routines.
The helper harness uses an explicit Win32 SEH/rectangle and constructor
CString/empty-bitset profile; resource/animation/audio/loot/ledge responses
are adapters. The primary loop is not replaced with a new FSM or timestep.
The native unit performs no UI, Xcode, device or sound output work.

Diagnostic fault1 denotes missing required external views/resource metadata;
fault2 unsupported bitset growth; fault3 missing state mapping. Constructed
size32 and valid supplied larger bitsets are supported for tested bit reads.
Pointer aliasing must match the represented same-actor wrapper profile.

## Verification

Run `work/test-env/bin/python Tests/compare_human_enemy.py`.

The suite passes **7,090 complete original calls**, **16,653 ordered calls
with full snapshots**, and **4,086 original-image instruction addresses**.
It covers the full actor/primary/secondary/contact/enemy/tail buffers,
player/effect/other/platform-primary views, 64 retained constructor/HOME/
pre/state/post chains, queued callback mutations, scaling extremes, original
literal-versus-copied name identities, audio-pool argument/order cases and
unsigned clock extremes. A private dylib compiles with warnings as errors and
floating contraction disabled. Existing common-body suites independently
cover the frozen physics/common implementations; this controller evidence
does not establish full Officer combat or end-to-end native acceptance.
