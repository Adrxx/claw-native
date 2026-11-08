# Original scene input and camera runtime

This module translates the original v1.0 instructions for the input stage, input polling/reset, camera actor, world follow, and plane viewport/clamp. It does not recover the complete renderer or platform input backend. The comparison executable is hash pinned to SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`; neither CrazyHook code nor reference gameplay code supplies these bodies.

## API and function inventory

`SceneCameraRuntime.h` exposes a C11 raw-token host, twelve distinct original globals, an entry dispatcher, and a plane-to-`ClawSpriteProjection` getter. Its heap ABI is the frozen `ClawSceneActorHost`; the platform callback exposes original IAT slot identities and adapted pointed-to buffers. Do not conflate stage delta (`53720c`) with animation delta (`5430c4`).

| Entry | Original calling convention | Native receiver / arguments |
| --- | --- | --- |
| `46c860` | thiscall owner, no arguments | owner token |
| `430ec0`, `431300` | input map poll/reset, no arguments | mapping token |
| `430d30`, `430d80` | register-ECX default mask/key stores | mapping token |
| `4b3490`, `4b3ab0` | device poll/reset, no arguments | device token |
| `4b3430` | thiscall device, mode argument | device token, argument0 mode |
| `486240`, `486d70` | cdecl actor pointer argument | **actor token in native receiver** |
| `486d30` | detached cancellation | no meaningful receiver |
| `42d5f0` | thiscall world, signed x/y arguments | world token, argument0/1 |
| `4d0a60` | thiscall plane, no arguments | plane token |
| `4d0c50` | thiscall plane, rectangle pointer | plane token, argument0 rectangle token |

Internal follow helpers `486620`, `486650`, `4868e0`, `486910`, `486940`, and `486a00` are translated into the corresponding complete camera paths. Meaningful Boolean returns are compared; incidental EAX from original void routines is not claimed. A supported entry returns one independently of its original result, which is written through `result`. Unsupported entries return zero. Caller initializes `fault` to zero; fault 1 means a missing span/service and fault 2 means invalid float/wrap metadata or the native repeat-wrap bound. Valid original cases preserve 32-bit arithmetic, original float stores, and the CRT's observed 53-bit x87 arithmetic. The safety bound does not claim original parity for invalid metadata.

## Verified behavior

`46c860` polls or resets input. It follows owner+4 → manager+4c → configuration+30; an active configuration gate resets input and leaves owner+764 unchanged. Otherwise it subtracts the unsigned stage delta from owner+764 with saturation, resetting while a remainder exists. After a poll, device pressed bit `100` and a clear menu-blocked global cause `PostMessageA(hwnd,111,8080,0)`. The window comes from owner+4 → manager+4 → window+4. Naming this bit Escape is not established by this body.

The camera is a separately scheduled actor: original registry ordinal 4, name `CaptainClawScreenPosition` at `522e3c`, callback `486240`, flags zero. Startup `46aeb0` creates it after CaptainClaw through `4c8b90` with z `9999`. Its first state-0 call allocates **20 bytes**, stores the token in primary logic+14, clears five words, and initializes x/y from the player. Camera private words are current x, current y, target x, target y, and shake delay. The ordinary state is 24. The actor's actual scene order governs when it observes the player; the native host must retain that order.

Ordinary follow uses player actor+cc to select speed: modes 3/4 use 4000, mode 8 uses 99999, others use 500. The step is unsigned `(speed * animationDelta mod 2^32) / 1000`, followed by original signed endpoint comparisons. An absolute wrapped target difference strictly greater than 500 teleports. The signed `INT_MIN` absolute-value quirk is preserved. Player states 26 and 5003 with player private+110 zero produce camera targets y+200 and y-200 and speed 250. Player state 5004 suppresses the ordinary follow update. Forced x/y select camera state 8888 and speed 400; clearing forced x to `ffffffff` returns to ordinary follow. The state-0 body resets both forced globals.

Shake runs while unsigned animationNow < shakeUntil. The delay test is strict `< animationDelta`; when true, three ordered RNG `4a3050` calls supply signed remainders for delay `%36` and x/y `%13-6`. The host owns the RNG state. Detached follow uses the observed global owner → +14 cell → actor chain and cancels on missing targets or input held mask `0f000003`.

### Parallax and viewport

`42d5f0` sets and clamps the main plane, reads its **integer center** at +84/+88, and applies that center to each other plane. Plane flags bit 1 bypasses scaling; otherwise signed center integers multiply binary32 factors at +18/+1c using 53-bit arithmetic, then store binary32 centers. Scaling the main plane's top-left is incorrect. For example, main center 689 with a 640-wide viewport gives left 369; factor 0.5 produces other center 344.5, integer center 344, and other left 24.

`4d0a60` handles independent wrap bits 4/8, world extents, center truncation, and inclusive viewport endpoints. Tiny worlds can produce a **negative top-left** after the final nonwrapping extent correction. Do not add an extra zero clamp. Negative wrap loops add the signed integer extent; positive loops subtract the float-rounded extent. `4d0c50` copies a four-word inclusive rectangle to plane+50..5c, calculates width/height and signed halves, and clamps. A rectangle beginning with `80000000` is ignored.

Four actual `42ce90` instruction witnesses reach renderer virtual+18 with `(HWND,640,480,8-or-16,1-or-5)`. The test forces renderer initialization failure to exit before resource bootstrap. This establishes the original initialization contract; it does **not** claim the full renderer has been ported. Native window resizing/letterboxing is a host presentation policy. The projection getter exposes flags, extents, per-plane left/top/end, and screen offsets to the frozen original `4c96d0` translation.

## Minimal native host object graph

All offsets below are byte offsets into little-endian word spans; tokens are opaque 32-bit host identities. Preserve other already-recovered fields and ownership when extending these spans.

| Object | Minimum words for this module | Links/fields |
| --- | ---: | --- |
| Stage owner | 474 | +4 manager, +c parent, +764 input countdown |
| Manager | 20 | +4 window, +4c configuration |
| Window | 2 | +4 HWND adapter identity |
| Configuration | 13 | +30 input-reset gate |
| Parent | 10 (existing 12 sufficient) | +8 scene actors, +24 world |
| World | **25** | +38 plane-token array, +3c count, +5c main plane, **+60 main index** |
| Plane | 45 | layout below |
| Input device | 146 | poll/reset/configuration fields below |
| Input mapping | 29 active words; original allocation 36 | word0 device, default masks/keys, pressed/held/latch |
| Camera actor / primary logic | 128 / 93 | actor+c parent, actor+6c primary; primary+10 callback, +14 private, +1c state |
| Camera private | 5, allocated on first callback | x, y, target x, target y, shake delay |
| Player actor / primary / private | 128 / 93 / 78 | actor+4c/50 x/y, +6c primary, +cc mode; primary+1c state, +14 private; private+110 flag |

The root host's former 24-word world is insufficient: +60 is word 24. Its parent `10001000`/12 words and owner `60002000`/474 words can be reused. Its world `60003000` must be extended while retaining tile-collision metadata. The camera module itself does not populate the unrelated world+10..1c drawing clip; the existing original projection pipeline should supply its verified inclusive `0,0,639,479` profile.

Each plane requires flags+8; binary32 center+10/+14; binary32 factors+18/+1c; positive pixel extents+30/+34; world viewport+40..4c; screen rectangle+50..5c; width/height+70/+74; halves+78/+7c; integer centers+84/+88. Allocate a rectangle token `[0,0,639,479]` and invoke `4d0c50` for each plane to establish 640/480 and 320/240. Supply main plane token/index and the entire pointer array before world follow. **WWD percentage/flag fields to runtime plane construction has not been recovered here**: feed verified runtime factors/flags or clearly label the loader's source-reference conversion. This module proves what the runtime fields do, not their original loader mapping.

Create the camera through frozen generic actor/logic construction and scene insertion, binding the verified registration entry (callback `486240`, flags zero), state zero, private token zero, z 9999. Route its original cdecl callback event's argument0 to the native entry's receiver. Do not allocate its five-word private storage preemptively. Host allocation/free must preserve original logic private ownership through frozen ActorDestruction. Capture stage and animation globals at their respective original frame boundaries and retain them between normal/substep calls; do not tick the camera separately per UI refresh.

| Native global | Original storage |
| --- | --- |
| playerToken | `537e88` |
| inputDeviceToken / inputMappingToken | `537200` / `537204` |
| stageDelta / menuBlocked | `53720c` / `537258` |
| animationNow / animationDelta | `5430c8` / `5430c4` |
| forcedX / forcedY | `52be14` / `52be18` |
| detachedMode / shakeUntil / detachedOwnerToken | `53c25c` / `53c260` / `53c264` |

The ordinary bounded host profile starts forcedX/Y at `ffffffff`, detachedMode/shakeUntil/detachedOwner at zero, and explicitly supplies player/input tokens and distinct stage/animation clocks. These are profile inputs, not a recovered whole-application constructor. State zero resets forcedX/Y in the actual callback, and detached cancellation resets its mode/owner globals.

### Input initialization recipe and boundary

The API now recovers exact default mapping stores `430d30` and `430d80`, plus mode setter `4b3430`; these are complete-buffer tested over nonzero seeded storage. Set mapping word0 to the device and its pressed/held/latch/+70 words to zero as observed at `430590`, then call both default entries. Default masks at +10..34 are `[1,2,4,8,0,10,20,40,80,0]` (hex). Default keys at +38..6c are `[25,27,26,28,20,11,12,10,0,5a,31,32,33,34]` (hex). Reserved mask +20 and key +58 are not polled. Original mapping allocation is 90 hex bytes: its trailing dictionary is outside these runtime spans.

Device config+1cc bits are keyboard 1, joystick 2, mouse 4; +1d0 records joystick availability, +1d4 extended buttons, +1d8 extra-button disable. `4b3430` strips joystick bit 2 if availability is zero, centers a configured mouse through ordered system calls, and stores the requested mode. `4b3ab0` clears device pressed+210, held+214, latch+20c, discards twelve configured keyboard reads when bit1 is enabled, and recenters mouse when bit4 is enabled. Then `431300` resets the mapping. Native platform translation must preserve repeated key queries and their low-bit consumption.

Original startup `42637f..4263a9` sets deviceID `ffffffff`, zeros config/availability/extended/edge fields, then `4b3410` clears the 101 capability words at +4 and 13 JOY words at +198. `4b3240(mode,deviceID)` clears those spans again, sets JOY size 34 hex, deviceID, edge state, extra-disable zero, physical keys `[25,27,26,28,20,2d,0,0,0,0,0,0]`, and availability zero. It calls `joyGetNumDevs`, `joyGetPosEx`, and `joyGetDevCapsA`; success populates thresholds/capabilities and configures mode. On joystick failure it removes config bit2 and selects keyboard bit1 if nothing remains. Startup then overrides device keys +1ec/+1f0/+1f4/+1f8 to Space/Control/Alt/Shift and optionally sets +1d8 for menuBlocked. Mapping initialization `430590` again calls mode setter with joystick-only mode2 when global53723c is zero, or mode0 otherwise; unavailable joystick therefore yields mode0. Mapping keyboard polling still operates with device mode0.

These startup observations are disassembly/decompile evidence in private `input-initialization.c`/`input-defaults.c`; **full `4b3240` capability initialization and `430590` dictionary bootstrap are not native recovered entries or complete-call claims**. A bounded keyboard-only host can provide the observed physical keys, zero availability/extended/latches, select verified mode0 after the mapping constructor's adjustment, install the mapping defaults, and reset. Its key state adapter still feeds the mapping's thirteen high-bit reads. Selecting a different device mode or loading saved user settings is caller-owned; do not claim an invented Mac key layout is the original startup profile.

## Input and service fidelity

Mapping words 1/2/3 are pressed/held/latch; +70 preserves the raw held copy. Device direction bits `10000000..80000000` map to logical `01000000..08000000`. Mask/key-selected buttons map to `1,2,4,8,20,40,80,100,200`. Mapping edge mask is `0f0003ef`; unrelated latch bits are preserved. Device direction keys use high bit only, buttons high-or-low (`8001`); mapping keys use high only. Device edge mask always includes directions/first four buttons and includes `1f0` only when +1d4 is nonzero. The ninth joystick button can produce system bit100 only with more than eight buttons and extra-disable zero.

Mouse `GetCursorPos` writes a discarded local POINT; comparisons use existing device relative fields +230/+234 and thresholds +238/+23c. Do not substitute the returned cursor coordinate into them. JOY output spans +198..1c8 and flag+19c is set to83 before each poll. The platform callback carries output buffers rather than guessed native pointer identities.

| Original IAT slot | Explicit host service |
| --- | --- |
| `546ce4` | GetAsyncKeyState |
| `546cd0` | GetCursorPos, two-word local output |
| `546d9c` | SetCursorPos |
| `546de8` | joyGetPosEx, deviceID + thirteen-word output |
| `546c44` | GetSystemMetrics |
| `546d50` | PostMessageA |

Camera RNG `4a3050` and camera private allocation remain explicit host services. Pure CopyRect is an exact memory adaptation. Original scene spatial callbacks `4d1fd0`/`4d2000`, reaching grid bodies `4d4b50`/`4d4d10`, remain explicit services in joined-frame evidence. `SceneActorRuntime` preserves their order. The joined fixture has one camera with no eligible interaction peer; it does not prove a substituted no-op grid for a populated gameplay scene. Full rendering, platform event delivery, saved settings, WWD runtime plane construction, and the complete camera/startup resource graph remain separate recovery work.

## Verification

Run `work/test-env/bin/python Tests/compare_scene_camera_runtime.py` from the repository. The helper builds optimized C++17 with `-Wall -Wextra -Werror -ffp-contract=off`, executes real original function bodies with deterministic platform/heap adapters, and compares all 128 KiB of raw host heap and all twelve globals at final return and every ordered service boundary. It retains key consumption state, restores/compares original SEH state, and composes frozen SceneActorRuntime/GameTiming/SpriteGeometry rather than duplicating their bodies.

The suite includes generated input/device/plane/camera cases, seeded mapping default/mode-setting cases, directed world edges/tiny-world/wrap, death/forced/shake/detached cases, 96 real normal/18ms-substep frame graphs, 120 retained frame histories, 100 actual `4c96d0` projection comparisons, and four renderer-viewport witnesses. Final counts and the hash invariant are saved under `work/scene-camera-agent/verification.json`. This is bounded CPU behavior evidence, not whole-game completion or native UI acceptance.

Final optimized run: **2,858 complete original calls**, **20,965 ordered full-heap events**, and **2,332 distinct original instruction addresses**, with 128 KiB compared per snapshot. C11 header compilation passes. The separate native Swift bridge executable passes 25-word world access, actual viewport setup, center-based main/background projection, and recovered input default stores; it links this module's native C ABI without Xcode or UI driving. Its private sources and executable are under `work/scene-camera-agent/bridge-smoke.*`.

Coordinator integration now creates CaptainClawScreenPosition through recovered
plain4c8b90/4c8a20, with5137b0 and a90-word original actor allocation. See
plain-actor-runtime.md for creator/destructor comparison scope. WorldPlaneRuntime
now supplies complete original runtime plane stores and owned tile/row buffers;
the initial main start point propagates after all plane records. Native input
uses the documented keyboard-only profile and physical semantic-key adapter.
Camera/input follow and player delay/look-down/release pass native scene tests;
latest source builds for Mac Catalyst and iPad simulator. Full grid residency,
original tile command rendering and OS timing remain separate work.
