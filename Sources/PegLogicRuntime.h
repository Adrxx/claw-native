#pragma once
#include "ActorAnimationRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPegGlobals {
    uint32_t defaultsToken, playerToken, tick, animationDelta, gate, audioManagerToken, audioVolume, wrapperMode;
} ClawPegGlobals;
typedef struct ClawPegContext {
    ClawSceneActorHost scene;
    ClawPegGlobals *globals;
    uint32_t composeAnimation, fault;
} ClawPegContext;
typedef struct ClawPegCall {
    uint32_t function, receiver, argumentCount, arguments[4];
    const char *name;
} ClawPegCall;
typedef uint32_t (*ClawPegDependency)(ClawPegContext *, const ClawPegCall *, void *);
// Cdecl registered49d860/49d620/49e4e0/49e7b0/49e7d0/49e7f0(actor),
// helpers49e470(actor,primary),49e4b0(actor,primary,absoluteTick). Also bounded
// thiscall4ca610(registryReceiver,[name,sourceX,clamp,pan]) down to4c88e0.
// Globals map537960,537e88,537210,5430c4,53725c,532c0c,532c10,53ebf0.
// No private allocation or timer substitution. Scene's original primary20
// delay scheduling remains external. composeAnimation selects frozen ANI
// bodies; zero logs actual ANI services for directed boundary comparisons.
// fault1 missing heap/service,2 original unsigned division trap,3 args/profile.
// Return support separately from original meaningful result;49e470 is void.
uint32_t claw_peg_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                        ClawPegContext *, ClawPegDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
