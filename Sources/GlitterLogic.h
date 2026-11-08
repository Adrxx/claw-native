#pragma once
#include "SceneActorRuntime.h"
#include "ActorAnimationRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawGlitterContext {
    ClawSceneActorHost scene;
    uint32_t managerToken;                  // Original5371fc; live manager+124 controls baby count.
    uint32_t animationDelta, audioPosition; // Original5430c4/532c10.
    uint32_t composeCreation, composeAnimation, fault;
} ClawGlitterContext;
typedef struct ClawGlitterCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    const char *name;
} ClawGlitterCall;
typedef uint32_t (*ClawGlitterDependency)(ClawGlitterContext *, const ClawGlitterCall *, void *);
// Whole registered448440 Mother,4485a0 Baby,470110 PowerupGlitter, each
// cdecl(actor). No class private allocation. Result is original meaningfulEAX1.
// Creation composition executes namedSceneActor factory and immediateBaby init.
// RNG4a3050 remains a shared service; no local independent random stream.
// Fault1 missing span/service;2 creator/animation or x86 signed-division fault.
uint32_t claw_glitter_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                            ClawGlitterContext *, ClawGlitterDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
