#ifndef CLAW_SCENERY_LOGIC_RUNTIME_H
#define CLAW_SCENERY_LOGIC_RUNTIME_H
#include "ActorAnimationRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawSceneryLogicContext {
    ClawSceneActorHost scene;
    ClawActorAnimationGlobals animation;
    uint32_t settingsToken;    // Original global5371fc; reads raw settings+124.
    uint32_t composeAnimation; // Nonzero composes frozen ActorAnimationRuntime.
    uint32_t fault;            //1 missing span/service,2 unsupported metadata.
} ClawSceneryLogicContext;
// Whole registered original callbacks: DoNothing461730/Normal461750,
// FrontCandy461770, BehindCandy4617d0, GooCoverup461830, GooBubble461870,
// FrontAniCandy4618e0, BehindAniCandy461970. Actor+6c is primary logic.
// Original cdecl callback receives the actor as its sole stack argument;
// actorToken below expresses that identity, not an x86 ECX receiver.
// Return1 supported/completed,0 unsupported/fault; result preserves EAX1/2.
// Initialize fault to0. External lookup/audio services keep SceneActorHost ABI;
// direct animation calls remain explicit when composeAnimation is0.
uint32_t claw_scenery_logic_entry(uint32_t function, uint32_t actorToken, ClawSceneryLogicContext *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
