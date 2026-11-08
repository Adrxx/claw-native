# Original CaptainClaw movement/input dispatch

`Sources/PlayerInputDispatch.h/.cpp` recovers the movement branches and common epilogue of the original v1.0 CaptainClaw callback `0x415df0`. The supported initial logic states are jump4, right/left walk8/9, stand24, fall25, duck26, climb27, landing5002, look-up5003, and teeter5006. Original initialization, respawn, death, carrying and other states are outside this bounded API. An unsupported initial state returns0 without mutations; that is a native scope guard, not the original callback's behavior for that state.

The original binary fingerprint remains `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Control flow comes from the original callback decompilation and observed instruction boundaries. Additional helpers were decompiled and inspected in the independent project under `work/input-agent/ghidra-project`; the log confirms each function and successful saves.

## Integration API

`claw_player_dispatch_input` takes the existing live `ClawPlayerLocomotion*`, a separate mutable `ClawPlayerInputContext*`, the existing address-keyed dependency callback, and caller context. The new input context contains pressed input (+4), logic invulnerability timer (+0x130), signed clamp bounds from logic +0x2c/+0x30/+0x34/+0x38, hazard-ignore global0x537230, and cheat global0x537214. Held (+8) and latched (+0xc) input remain in locomotion state. The dispatcher rereads its live fields after helper calls where the original does so.

High-level helper calls use their original function IDs through the existing dependency API. The adapter can invoke recovered native helper bodies on the same state, allowing those bodies to change the fields that later dispatch logic observes. Ordinary actor/logic/private helper arguments are implicit in the state and portable a/b/c words are zero. Special payloads are:

| Dependency | Portable payload / result |
| --- | --- |
| `0x417930` | a=skip-animation flag; recovered fall entry |
| `0x41fc30` | a=stage delta; powerup timer |
| `0x4cd1c0` | a=signed actor x-offset; return supporting-tile predicate |
| `0x4cd740` | a=foot x-offset (zero here); return attribute |
| `0x41e710`, `0x41e790` | Return left/right ledge predicate |
| `0x41d850` | Return original attack-selector result; subsequent transition depends on it |
| `0x4bb030` | Return external platform-edge condition |
| `0x4a3050` | Return original signed CRT random value |
| `0x48c8a0` | a=CLAW_1021 identifier0x524684, b=0; speech |
| `0x420910` | a=GAME_CLICK identifier0x524678; weapon-cycle sound |

Other external helper IDs include jump-hold0x41f4c0, stand/update0x419030, edge-standing0x419c80, teeter entry0x417480, attack transition0x417380, climb entry0x4170f0, and hazard death entry0x417c50. Previously recovered walk/jump/fall/duck/climb/landing/look-up callbacks and state entries retain their original IDs. Unknown helper bodies must remain visible rather than being reported as recovered merely because the dispatch selection is exact.

## Input and update order

Stand24 reacts to pressed horizontal masks, not held horizontal masks. Jump pressed bit1 wins before pressed Right, then pressed Left, provided attack private word1 is zero or private word8 allows interruption. Its jump and walk branches contain immediate movement/physics/animation work in the same callback. The native dispatcher recovers those inline operations directly; substituting a superficially similar state-entry helper changes cleanup and transition behavior.

Walk8/9 reacts to held input. Held Down interrupts either direction into stand entry plus stand update. Simultaneous held Left+Right preserves the current walking direction: state8 chooses Right; state9 chooses Left. Walking/standing updates occur before attack selection, then a pressed jump enters jump only if the attack selector returns zero. That walking jump entry does not also call the jump update in that callback. Look-up5003 and teeter5006 pressed jump do call jump entry followed by jump update. Jump4, fall25, and duck26 call attack selection before their respective update; climb27 and landing5002 directly call their updates.

The stand→walk inline branches preserve the original timer asymmetry: Right decrements idle timer69 using animation delta, Left uses stage delta. The stand→jump branch initializes a45-pixel target, uses general retarget0x420dd0, calls its separate jump-hold helper, then immediately advances physics and collision. Its position correction matches0x420c40, including velocity-at-position, physics delta correction, and position assignment.

The common epilogue cycles private weapon word12 on pressed bit8 when not attacking, applies the original invulnerability countdown/flag changes, decrements private timers62 and71, updates the powerup timer, clamps signed coordinates unless the helper changed logic to death5004, handles supported-platform hazard checks and flag0x400000, and applies the original cheat health/ammo values. All unsigned wrapping and original signed comparisons are retained.

## Separately recovered normal dependencies

| Native entry | Original entry |
| --- | --- |
| `claw_player_update_jump_hold` | `0x41f4c0` |
| `claw_player_left_ledge` | `0x41e710` |
| `claw_player_right_ledge` | `0x41e790` |
| `claw_player_enter_teeter` | `0x417480` |
| `claw_player_update_powerup_timer` | `0x41fc30` |

Jump-hold preserves release behavior (held jump absent sets timer70=0), animation-clock countdown, original float factors0.78/0.68/0.58, high-jump/powerup/run conditions, minimum target selection, and its inlined retarget operation order. General retarget substitution is not assumed equivalent for multi-axis acceleration. The ledge predicates preserve supporting-platform rejection, endpoint order, twelve-pixel initial inset and four-pixel scan, signed width comparisons, and final support inversion. Their tile-support dependency remains explicit; inspection confirms0x4cd1c0 samples x+offset,y+boundingBottom+1 with world clamping and returns1 for attributes1/2/3.

Teeter entry uses deletion-resource cleanup and animation restore0x420a10, selects the verified binary string CLAW_TEETER at0x524690, enters logic5006, and preserves signed random division/remainder and its return value. The dispatcher also has an inlined teeter path whose extra movement and opposite-side recheck remain distinct.

The powerup helper receives a separate `ClawPlayerPowerupContext` with remaining time (global0x534ea8), expiration signal (global0x534eb8), and optional actor+0x174 object's +0x30 overlay token. It recovers countdown and flag mutation. Expiration explicitly calls0x41f990 and0x4bc110; powerup0x26b7 emits0x4c6130(a=overlay token,b=2,c=0); powerup0x26bd emits0x420070(a=delta) then masks actor flags at0xd4. Those resource/effect helper bodies are not recovered here. The adapter must maintain the shared remaining time and restore/expire effect state through the actual dependency implementations.

The existing portable name `audioPosition` historically stores original global0x532c10. Later audio recovery established that this global is overall volume. Its value comparisons remain valid; the semantic name is scheduled for a coordinated change and is not a spatial coordinate.

## Verification and remaining limits

Run `work/test-env/bin/python Tests/compare_player_input_dispatch.py`. Private `Tests/input_dispatch_helpers.py` builds only into `work/input-agent/`. The suite executes the complete original top-level callback from each supported state, comparing complete actor/private/physics buffers, logic/input fields, pixel scratch, invulnerability timer, return value and ordered dependency arguments. Original scene and logic pointers are normalized to unchanged portable tokens; native mutations still fail. Inline physics, geometry, retarget and position-correction bodies execute normally.

The suite passes1000 callback calls per supported state (10,000 total),2000 calls per separately recovered helper (10,000 total), directed simultaneous input/order cases, and3840 chained callback calls. The dispatcher phase adapts high-level helper bodies, collision/resource/combat operations, and selected helper state changes identically on both sides; it proves control flow and inline side effects across those boundaries. The chained phase carries state, input, timers and physics between callbacks but uses the same explicit helper adapters. It is not a full original frame execution with all recovered helper bodies linked together. The separate helper phase compares full bodies of the five normal dependencies while logging their remaining resource/tile-support dependencies. Finite game-scale numeric inputs are covered; nonfinite/extreme exponent parity is not established.

These comparisons reach2160 original instruction addresses. They do not establish full-game identity, missing initial/death/carrying states, combat implementation, actor lifecycle, rendering, original scheduler pacing, physical iPad acceptance or retail asset equivalence. Root integration and full-body frame histories remain distinct verification work.
