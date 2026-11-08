#pragma once
#include "SceneActorRuntime.h"
#include "ActorAnimationRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPickupPointsContext {
    ClawSceneActorHost scene;
    uint32_t animationDelta, audioPosition;
    uint32_t composeCreation, composeAnimation, pointsEntryToken;
    uint32_t fault;
} ClawPickupPointsContext;
typedef struct ClawPickupPointsCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    const char *name;
} ClawPickupPointsCall;
typedef uint32_t (*ClawPickupPointsDependency)(ClawPickupPointsContext *, const ClawPickupPointsCall *, void *);
// Whole4737c0(item) and registered473a70(actor). Image setters/getter are
// bounded to actual GAME_POINTS literal52a6c0 and raw27-word image resources.
// Supported scope is separate from original EAX. Fault1missing service/span,
//2propagated creator/animation diagnostic. Null explicit creator is normal.
uint32_t claw_pickup_points_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                  uint32_t argumentCount, ClawPickupPointsContext *, ClawPickupPointsDependency, void *,
                                  uint32_t *result);
#ifdef __cplusplus
}
#endif
