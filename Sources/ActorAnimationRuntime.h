#ifndef CLAW_ACTOR_ANIMATION_RUNTIME_H
#define CLAW_ACTOR_ANIMATION_RUNTIME_H
#include "SceneActorRuntime.h"
#include "AnimationEngine.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawActorAnimationGlobals {
    uint32_t animationDelta; // Original5430c4, distinct from stage delta53720c.
    uint32_t audioPosition;  // Original532c10; not animation/stage timing.
} ClawActorAnimationGlobals;
// Actual caller ABI:79e0(actor,name,eager),7a40(actor,name),420a10(actor,ANI,eager),
// 8210(animation),8220(animation,ANI),8260(animation,clearDelay),82a0(animation,delta).
//420970(animation,index) seeks with source fallback0 and resets code/delay/stop.
// Animation is a raw11-word object, normally embedded at actor+188. ANI+0xc
// holds record-pointer array,ANI+0x10 signed count; records are12 raw words.
// Existing host.call4f6286 returns the resolved resource token. Audio services
// 4c88e0/4208e0 run at the original actor/state snapshot boundary. Their recovered
// routing has no gameplay writes; reentrant gameplay mutation is rejected with
// fault3 instead of claiming parity from the frozen engine's batched outputs.
// fault1 missing span/service,2 invalid/out-of-scope metadata are native safety
// extensions. Return support separately from meaningful original scalar EAX.
uint32_t claw_actor_animation_entry(uint32_t function, uint32_t receiver, uint32_t argument0, uint32_t argument1,
                                    ClawActorAnimationGlobals *, ClawSceneActorHost, uint32_t *fault, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
