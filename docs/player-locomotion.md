# Original v1.0 player locomotion

`Sources/PlayerLocomotion.h/.cpp` recovers the following state transitions from the hash-pinned original v1.0 executable (`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`):

| Native entry | Original address |
| --- | --- |
| `claw_player_enter_stand` | `0x4171d0` |
| `claw_player_enter_walk_left` | `0x417dd0` |
| `claw_player_enter_walk_right` | `0x417f20` |
| `claw_player_enter_jump` | `0x417590` |
| `claw_player_cleanup_move` | `0x41c4e0` |
| `claw_player_enter_fall` | `0x417930` |
| `claw_player_update_walk_right` | `0x4183e0` |
| `claw_player_update_walk_left` | `0x418790` |
| `claw_player_update_jump` | `0x41b630` |
| `claw_player_update_fall` | `0x418b40` |

These routines do not recover the entire CaptainClaw callback, enemies, combat, world actor lifecycle, or scheduler. State 27 enters climbing but has no recovered climb update here; state 5002 enters a long-fall landing animation but has no recovered landing update here. A caller must handle or explicitly report unsupported states.

## Portable state

`ClawPlayerLocomotion` preserves the actor's 128-word test buffer and the original 78-word private state. Original pointer words are opaque tokens. `logicState`, input masks, the two distinct elapsed-time globals, powerup state, shared physics state, pixel conversion scratch globals, and relevant optional weapon/audio globals are explicit fields. C actor/private word getters and setters allow Swift to access those arrays without unsafe tuple operations. Bounds checks on these accessors are native safety extensions, not behavior recovered for invalid offsets.

Useful actor byte offsets: flags `0x08`, render flags `0x40`, x/y `0x4c/0x50`, supporting actor token `0x80`, collision mode `0xcc`, type `0xd0`, collision probe steps `0xdc/0xe0`, bounding rectangle `0x118`, hit rectangle `0x128`, attack rectangle `0x138`, x/y velocity words `0x148/0x14c`, platform deltas `0x158/0x15c`, animation rate bits `0x1b0`. Private word indices include facing 0 (0 left, nonzero right), attack state 1, sequence-specific state 15, fall distance 16, jump displacement 23, jump start y 24, jump target y 25, speed adjustment 33, walk counter 62, stand timer 63, idle/run timer 69, held-jump timer 70, restored animation token 73, and weapon actor token 75.

Logic states: stand 24, right walk 8, left walk 9, jump 4, fall 25, climb 27, long-fall landing 5002. Collision modes are a different state machine: grounded 1, walking 2, rising 3, falling 4, climbing 6.

The right-walk update decrements private idle timer 69 using animation delta `0x5430c4`; the left-walk update uses stage delta `0x53720c`. They must stay distinct. Held input is bit 1 for jump, `0x01000000` left, `0x02000000` right, `0x04000000` up; right has priority when both horizontal directions are held. Jump adds private speed adjustment 33; fall does not. Original unsigned wrapping and signed comparisons are preserved.

Jump entry contains an inlined retarget calculation whose addition order differs from general `0x420dd0`. Substituting the general helper changes some randomized velocities by one ULP. The native entry keeps its inline order; held-jump updates use the recovered general helper. Floating-point operations round separately at the original CRT's established 53-bit precision.

## Dependency adapter

The callback receives state, original entry ID, three portable argument words, and caller context. It may modify state; token-resolution callbacks return a portable token. Supplying no callback means these operations do nothing, and is not a complete gameplay implementation.

| Entry ID | Portable arguments / operation |
| --- | --- |
| `0x4c79e0` | `a=sequence-name address`, `b=immediate animation update flag`; select animation and optionally advance by animation delta |
| `0x4c82a0` | `a=animation delta`; update the actor's animation |
| `0x4cbb60` | `a=x`, `b=y`, `c=collision options`; run movement and copy the resulting actor fields back |
| `0x158`, `0x15c` | `a=support token`; return that platform's x/y delta (synthetic read IDs, not function addresses) |
| `0x4f6286`, `0x4061b0` | `a=sequence-name address`; return resolved animation/audio token |
| `0x420a10`, `0x4c8220` | `a=restored sequence token`; restore animation with no immediate update |
| `0x421010` | `a=weapon token`, `b=0x4207a0`, `c=1`; optional external weapon logic transition |
| `0x420fc0`, `0x4dbd20` | `a=weapon token`, `b=0`; external weapon cleanup / deletion resource operation |
| `0x41c5a0` | Attack animation update; all portable arguments zero; full original actor/logic/private buffers are in state |
| `0x4208e0` | `a=audio token`, `b=audio position`, `c=0`; original remaining three sound arguments are zero |
| `0x4209d0` | `a=401`; original fall-distance image selection |

Known sequence-name addresses: WALK `0x52469c`, JUMP `0x5246a8`, CLIMB `0x5246c4`, STAND `0x5246d0`, FALL `0x5246dc`, LAND `0x524718`, LEFTFOOT1 sound `0x524724`. These are source identifiers, never native pointers.

Weapon logic callback/status and deletion count/flags are modeled explicitly. The caller must map these optional fields back to a real external weapon actor. The count selects the original inline versus allocated resource-flag branch (1..32 versus >32); the portable flag word retains the same OR-with-1 operation.

For an initial movement integration, zero the native state, run `claw_physics_construct`, assign gravity y=2250, maximum x/y delta=32 and maximum velocity=1000, assign actor coordinates and collision probe steps from the actor loader, place the actor with the recovered ground-placement routine, then enter stand. This is an integration recipe, not a recovered replacement for the full original actor initializer. Original private constructor `0x415ce0` assigns word 12=1, word 18=100, words 28/29=10/5, words 30/31=3/3, word 59=1000000; a nonzero difficulty global assigns words 28..31=50/40/20/9. Stand entry itself sets timers and rectangles; it preserves unrelated private fields.

## Verification and limits

Run `work/test-env/bin/python Tests/compare_player_locomotion.py`. It builds an ARM64 native dylib in `work/player-agent/` and uses `Tests/original_v10.py` to execute the original instructions with the actual CRT precision initializer. It compares complete 512-byte actor, 312-byte private, and 240-byte physics buffers, logic state, input latch, pixel scratch globals, optional weapon fields, and ordered dependency argument events. The original scene pointer in actor word 3 is normalized to the preserved portable token; native mutations of that token still fail comparison. Stand return value is compared as well. Numerical tests use finite game-scale physics inputs; nonfinite or extreme exponent parity is not established.

The generated phase runs 1,000 calls per recovered entry (10,000 total), including all forced collision outcomes, signed wrapping, directions, speed adjustments, stopped physics, optional weapon and attack branches, and powerups. A directed unequal-clock case establishes the left/right timer asymmetry. Movement/collision bodies are stubbed in this phase; target x/y/options and their ordered position among the dependency calls are checked.

The chained phase runs 32 histories of 240 calls on a synthetic map and another 32 histories on the extracted CD-rip Level 1 map. It executes full original collision bodies and their native equivalents, including physics and pixel conversion. The synthetic map has ground, holes, ladder tiles, and a hazard tile; the Level 1 phase begins at the previously verified placed spawn (689,4730). These are scripted entry/update histories, not input dispatch through the complete original CaptainClaw callback. Original world actor objects are not instantiated in these maps.

Animation selection/update, registry, sound, optional weapon resources, and attack-animation dependencies are explicitly stubbed in both phases. Those dependency bodies are not proven by these tests, and a successful locomotion comparison does not establish full-game behavior, rendering, scheduler timing, physical iPad acceptance, or retail asset equivalence.
