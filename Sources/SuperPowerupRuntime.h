#ifndef CLAW_SUPER_POWERUP_RUNTIME_H
#define CLAW_SUPER_POWERUP_RUNTIME_H
#include "ItemPickupRuntime.h"
#include "ActorAnimationRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawSuperPowerupContext {
    ClawSceneActorHost scene;
    ClawItemPickupContext *items; // Borrow loot, manager5371fc and shared pickup sound globals.
    ClawActorAnimationGlobals *animation;
    uint32_t composeAnimation, composeCreation, fault;
} ClawSuperPowerupContext;
typedef struct ClawSuperPowerupCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    const char *name;
} ClawSuperPowerupCall;
typedef uint32_t (*ClawSuperPowerupDependency)(ClawSuperPowerupContext *, const ClawSuperPowerupCall *, void *);
// Complete registered471330 cdecl(actor). No private allocation or ability
// timer is introduced. All original actor/primary/glitter tokens remain live.
// Return supported/completed separately from actual callback EAX (1).
// fault1 missing raw span/service;2 bounded metadata/argument rejection.
uint32_t claw_super_powerup_entry(uint32_t actorToken, ClawSuperPowerupContext *, ClawSuperPowerupDependency, void *,
                                  uint32_t *result);
// Frozen ItemPickupRuntime → CaptainClawHit for exact type200000, after actual
// hit election has set player.actor+74=itemToken. Health-cap and sound/cache
// ordering remain source-owned; this does not elect contact or remove actors.
uint32_t claw_super_powerup_award(uint32_t itemToken, ClawSuperPowerupContext *, ClawSuperPowerupDependency, void *);
#ifdef __cplusplus
}
#endif
#endif
