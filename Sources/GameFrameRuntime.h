#ifndef CLAW_GAME_FRAME_RUNTIME_H
#define CLAW_GAME_FRAME_RUNTIME_H
#include "SceneCameraRuntime.h"
#include "SpatialGridRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawGameFrameContext {
    ClawSceneCameraHost host;
    // Caller-owned live original globals. Stage/animation remain distinct.
    // Camera stageDelta/animationNow/animationDelta/playerToken are mirrors
    // of stage/actors and are synchronized before recovered camera calls.
    ClawClockState *clock;
    ClawSceneStageState *stage;
    ClawSceneActorGlobals *actors;
    ClawSceneCameraGlobals *camera;
    uint32_t composeStage, composeCamera, composeSpatial, fault;
} ClawGameFrameContext;
typedef struct ClawGameFrameCall {
    uint32_t function, receiver, argumentCount, arguments[4];
} ClawGameFrameCall;
typedef uint32_t (*ClawGameFrameDependency)(ClawGameFrameContext *, const ClawGameFrameCall *, void *);
// Native composition policy defaults only; does not initialize original state.
void claw_game_frame_defaults(ClawGameFrameContext *);
// Whole ordinary outer46ac30; gameplay override475dc0; manager428b60.
// Original ABI is receiver in ECX, no stack arguments; all return0/1.
// Default composition runs frozen stage/camera/spatial/timing bodies. Unknown
// gameplay, interaction, render/audio/UI/platform bodies remain explicit calls.
// Render/presentation/UI calls precede final main-plane4d2000 residency.
// Manager428b60 publishes stage clocks even when manager+b0 pauses callback;
// manager+2c state vtable+14 selects outer body, then positive+6c decrements.
// Raw manager must cover45 words; owner474; scene10; map25; surface7;
// renderer1+vtable14; state1+vtable6; manager+5c service; device target12.
// Live vtable function identities must be represented by heap.lookup.
// Fault1 missing span/service;2 composed allocation/metadata/loop diagnostics.
uint32_t claw_game_frame_entry(uint32_t function, uint32_t receiver, ClawGameFrameContext *, ClawGameFrameDependency,
                               void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
