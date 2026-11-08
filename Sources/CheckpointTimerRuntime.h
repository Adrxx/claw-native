#pragma once
#include "ActorAnimationRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawCheckpointTimerGlobals {
    uint32_t managerToken, playerToken, stageDelta, animationDelta;
    uint32_t remaining, initialDuration, expired, multiStatsToken;
    uint32_t left, top, right, bottom, audioPosition;
} ClawCheckpointTimerGlobals;
typedef struct ClawCheckpointTimerContext {
    ClawSceneActorHost scene;
    ClawCheckpointTimerGlobals *globals;
    uint32_t composeAnimation, composeImages, composeHierarchy, composeFormatting, fault;
} ClawCheckpointTimerContext;
typedef struct ClawCheckpointTimerCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    const char *name;
    uint32_t localMask;
    char *buffer;
    uint32_t bufferBytes;
} ClawCheckpointTimerCall;
typedef uint32_t (*ClawCheckpointTimerDependency)(ClawCheckpointTimerContext *, const ClawCheckpointTimerCall *,
                                                  void *);
// Raw cdecl491b30(timer),4919f0(digit),491ed0(MultiStats),41f490(player).
// HUD/number thiscall490760(7args),490590(8args),490c40/490c00(0args),
// destructor40db30(delete),40db50(0args); collection4c9fc0(delete),
//4c9fe0/4d3eb0/4f5172(0args) compose frozen generic child destruction; hierarchy4d3e50/4d3ca0(6args),
//4d3ef0(0args),4d3f20(target: child virtual draw services); collection parent4c8e00/4c8f60(6args),42a630(0args). Command426e30 is bounded to8063, args(0,command,0).
// Initial source remaining53c9f8=0; actual491b30 startup publishes35000.
// Globals aliases5371fc,537e88,53720c,5430c4,53c9f8,52c6e4,53c9f4,
//53c9fc,5370c8,5370cc,5370d0,5370d4,532c10. Checkpoint bonus52c6e8
// remains owned by live CheckpointLogic globals and shares remaining storage.
// Source46aeb0 creates timer only whenmanager9c!=0;4254a0 sets that field0.
// Original cdecl graphics/player services remain exact addresses, no inferred
// game-over command, expiry delay or HUD-child placement. Fault1 missing span,
//2 allocation exception/profile failure,3 unsupported args/unsafe profile.
uint32_t claw_checkpoint_timer_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                     uint32_t argumentCount, ClawCheckpointTimerContext *,
                                     ClawCheckpointTimerDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
