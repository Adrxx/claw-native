#ifndef CLAW_STACKED_ACTOR_LIFECYCLE_RUNTIME_H
#define CLAW_STACKED_ACTOR_LIFECYCLE_RUNTIME_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawStackedActorLifecycleContext {
    ClawSceneActorHost scene;
    // Native bounded extensions:1 missing span/service;2 invalid caller ABI.
    // A dependency may set fault before returning; later source writes stop.
    uint32_t fault;
} ClawStackedActorLifecycleContext;
// Whole original thiscall entries. Caller args are original stack arguments:
// 484d90(deleteFlag),4041b0(unusedMap),4041a0(unusedMap),4c9e30(unusedMap);
// 456030(),4c96b0(),4bb030(). Stack private allocation is only0x4c/19 words.
// 4041b0 invokes actual queued function identities via scene.call, receiver
// privateToken, zero stack args; cleanup/transition fields are read and cleared
// after callbacks. No common-enemy buffer or invented embedded destructor.
// 4041a0 calls external CRT RTTI helper4a36f0 cdecl(privateToken), which may
// return normally or throw. Physical Windows exception handling is a service.
// Native support/completion is separate from meaningful original EAX: deleting
// wrapper returns receiver;4bb030 returns0; source void entries normalize0.
// Unsupported function returns0 without fault; each call resets fault.
uint32_t claw_stacked_actor_lifecycle_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                            uint32_t argumentCount, ClawStackedActorLifecycleContext *,
                                            uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
