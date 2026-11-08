# Original outer game-frame runtime

`GameFrameRuntime.h/.cpp` recover complete ordinary outer callback `46ac30`, gameplay override `475dc0`, and manager callback `428b60` from original v1.0 EXE SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private original caller/xref inventory and Ghidra logs identify verified boundaries:163,204 and82 instruction bytes respectively, with no script errors. This module composes frozen timing, actor-stage, camera/input and spatial bodies rather than introducing a new frame schedule.

The missing ordinary residency call is in the **outer tail**, after rendering/presentation/UI. It is not an additional step inside `46ace0`. The original interior substep residency calls still occur in `46ad70`; the final outer call is additional and occurs for both ordinary and subdivided frames.

## Stable API and live state

`claw_game_frame_entry(function,receiver,context,dependency,user,result)` supports the three whole callbacks, all with receiver in ECX and no stack arguments. It returns1 for a supported function and writes original0/1 through result. Unsupported function returns0 before mutation. Context fault is a separate native diagnostic; callers clear it deliberately before each operation.

`ClawGameFrameContext` holds the frozen `ClawSceneCameraHost` and caller-owned pointers to existing `ClawClockState`, `ClawSceneStageState`, `ClawSceneActorGlobals`, and `ClawSceneCameraGlobals`. These objects remain mutable across retained frames. `claw_game_frame_defaults` selects native composition of stage/camera/spatial only; it does **not** manufacture original timers, settings or scene objects. Manager timing initialization can use the already recovered `GameTiming` initializer; minimum frame duration and countdown initialization still belong to an explicit supplied profile.

The stage clock (`537208/53720c`), accumulated tick (`537210`), manager clock (`541328..541338`), and animation clock (`5430c8/5430c4`) remain distinct. Camera's playerToken/stageDelta/animationNow/animationDelta fields mirror the canonical stage and actor globals; they are synchronized before recovered camera calls and after the entry returns. They are not independent second copies of original global clocks.

The raw graph requires manager45 words (through+b0), owner474 words, scene10, map25, surface7, device target12, renderer instance1 plus vtable14, and current state instance1 plus vtable6. `heap.lookup` supplies stable aligned raw word spans, including actual virtual function slots. No platform class or arbitrary original function pointer is silently replaced by a guessed value. Known manager state callbacks `46ac30/475dc0` dispatch natively; other state callback identities remain explicit dependencies.

## Complete outer order

`46ac30(owner)` executes this sequence:

1. Read unsigned stageDelta. Select `46ad70` only when `18 < delta <100`; otherwise select `46ace0`. Frozen stage performs original input, activation, actor updates, pair scan, clock replay/restoration and optional player image override.
2. Read owner+c scene→scene+24 world→world+5c main plane. Call `4025c0(owner+4.manager+5c, mainPlane+84, mainPlane+88)` using integer center fields.
3. Reread the owner/scene graph. Call `4cb9b0(world, surface+14, scene+8 actorContainer)`.
4. Reread scene+4 surface and scene+c renderer. Invoke renderer vtable+34 with `(surface+14,surface+18)`.
5. Call `46c2c0(owner)`.
6. Reread scene+4 surface→surface+10 device→device+2c target. Call `4b98b0(target,0)`.
7. Reread world+5c. If nonzero, execute actual `4d2000(mainPlane)` residency.
8. Return1.

`475dc0(owner)` has the same complete tail, with two additions: before stage selection it calls `4774f0(owner)`, `477840(owner)`, `478290(owner,0)` in that order; after renderer virtual+34 and before `46c2c0`, it calls `4224f0(manager+4c,live stageDelta)`. The pre-stage helpers can change stageDelta before selection; later services can change graph pointers/fields before the following reads. The port preserves those callback mutation boundaries.

All renderer/audio/UI calls retain original function/receiver/ordered arguments. This module does not infer their business meaning from an address alone. `4cb9b0` can route into the separately recovered plane renderer. Physical presentation and remaining bodies are supplied by the host. Capturing immutable native draw commands at this original render boundary and presenting them later in Canvas is a host policy; rendering must not migrate the final residency call into an arbitrary UI callback.

## Complete manager order

`428b60(manager)` first executes frozen `4b82f0` timing directly over the raw manager timing words+18..28 and live clock globals. This preserves intermediate manager writes visible at subsequent time callbacks. The injected clock must satisfy original wrapping millisecond sampling and pacing semantics; pacing uses the original busy-poll helper, not a host sleep.

It then publishes manager clock now/delta into stage now/delta and adds delta to the accumulated tick. **Publication occurs before pause**. If manager+b0 is nonzero, return0 without invoking the state callback or decrementing the counter. Otherwise read current state at manager+2c, invoke its vtable+14 callback, reread manager+6c, decrement it only when signed positive, and return1. A state callback may change that counter; the decrement uses its post-callback value.

This recovers the finite ordinary manager gate and full outer callback. It does not recover the full application message pump, state transitions, menu entry/exit, scene constructors, saved settings, or extra gameplay helper bodies.

## Native composition and explicit services

Default `composeStage=1` executes frozen `claw_scene_stage_run`. Its nested host callback routes `46c860` and actor callback `486240` into frozen `SceneCameraRuntime` when composeCamera=1. Input platform calls retain the frozen platform ABI. `4d1fd0` and `4d2000` route directly into frozen `SpatialGridRuntime` when composeSpatial=1, using the same live scene/list/grid buffers. Stage animation refresh reads host time only on the normal stage path; substep replay restores the original stage values and writes the restored values into animation globals exactly as the frozen body specifies.

Other actor/gameplay and interaction calls retain `ClawGameFrameCall` function/receiver/argument contracts and can route into their existing native modules. A rich dependency is optional: unresolved services fall back to frozen `scene.call`. Allocations, frees, raw lookup and clocks proxy the caller's original host callbacks without inventing new token identities. Render/UI/audio and the four additional gameplay-override calls remain explicit boundaries until their own bodies are supplied.

Fault1 reports a missing span, clock or service. Fault2 can propagate a frozen composed module's allocation/metadata/loop diagnostic. These are native safety extensions, not new original normal returns. Clock pacing still requires a sample eventually greater than its unsigned deadline; impossible or nonadvancing clock profiles do not acquire successful-return claims.

## Whole-call evidence

Run `work/test-env/bin/python Tests/compare_game_frame_runtime.py`. The optimized portable library builds with warnings treated as errors and contraction disabled. The public header also compiles as C11.

Final evidence:496 complete original outer/manager calls;25,509 ordered complete raw384KiB heap plus live-global snapshots;1,773 executed original addresses;208 directed cases;288 retained manager frames. EAX, zero-argument SP cleanup, allocator/list/grid changes, ordered service arguments, distinct clocks and FS exception-chain restoration are compared.

The fixture builds real grid/list buffers using frozen constructors and verified original Level1 main-plane extent24576×6144 with original world default size pairs. Nine represented actors populate ordinary/800000/1000000 layers, plus a real camera actor. Eight ordinary directed frames move an actor during rendering and measure its **actual removal from the scene list and reinsertion into a dormant cell by final `4d2000`**. No no-op ordinary-grid adapter is used. Retained histories move camera/player coordinates and alternate normal/substep durations, exercising activation, updates and residency over the same buffers.

Thirty-six pause cases still sample/publish/accumulate clocks and preserve the post-state counter. Directed cases cover stage threshold boundaries, interior versus final residency counts, render-time main-plane removal, stageDelta mutation before selection, post-callback counter mutation, positive/negative counters, unknown state callbacks, original pacing reads, frame-rate reset writes visible at clock callbacks, unsigned wrap and distinct animation samples.

Rendering, presentation, UI/audio, extra gameplay and ordinary actor gameplay callbacks are declared finite services in the oracle. Keyboard samples are supplied as zero; platform time has explicit scripted values. The native interaction body is real, but these fixture masks have no eligible damage/contact pair. Thus this suite proves the outer schedule and populated spatial composition, not renderer pixels, combat behavior, the unknown helper bodies or complete retail application startup. Measured counts are saved in private `work/game-frame-agent/verification.json`.
