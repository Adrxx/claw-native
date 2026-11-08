#ifndef CLAW_PLAYER_RANGED_HELPERS_RUNTIME_H
#define CLAW_PLAYER_RANGED_HELPERS_RUNTIME_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlayerRangedHelpersGlobals {
    uint32_t powerup, masterVolume;
} ClawPlayerRangedHelpersGlobals;
typedef struct ClawPlayerRangedHelpersContext {
    ClawSceneActorHost scene;
    ClawPlayerRangedHelpersGlobals *globals;
    uint32_t composeCreation, composeImages, fault;
} ClawPlayerRangedHelpersContext;
typedef struct ClawPlayerRangedHelpersCall {
    uint32_t function, receiver, argumentCount, arguments[12];
    const char *name;
} ClawPlayerRangedHelpersCall;
typedef uint64_t (*ClawPlayerRangedHelpersDependency)(ClawPlayerRangedHelpersContext *,
                                                      const ClawPlayerRangedHelpersCall *, void *);
/* Whole original cdecl41c9f0/41cab0/41cb80/41cc60(actor,primary,private), RET.
   Primary is passed by actual standing/duck caller but unused in these bodies.
   Live raw actor/private are borrowed; no allocation of a surrogate player.
   Globals534eac/532c10 are borrowed live aliases, with no host defaults.
   Physical six-argument4c8da0 creation, resource/image binding/audio retain
   exact transports. Optional creation composes frozen SceneActorRuntime; its
   leaf services use the same host. Marker5 null creation is unchecked original
   prefix; native fault stops after reached stores. Dynamite INT_MIN/-1 idiv
   traps reportfault2 before any creation. fault1 missing span/service;3 args.
   Covered completed entry returns1, unsupported/fault0; meaningful original
   EAX success0/1 is returned separately. Clear fault before a new invocation.
   Normal actor allocation1b4 bytes and primary174 bytes remain host-owned;
   requested image composition uses frozen128-word portable actor backing.
   Projectile private allocation/startup/update belong to PlayerProjectileRuntime
   and the host's deferred original callback graph; emit doesn't invent startup. */
uint32_t claw_player_ranged_helpers_entry(uint32_t function, const uint32_t *arguments, uint32_t argumentCount,
                                          ClawPlayerRangedHelpersContext *, ClawPlayerRangedHelpersDependency, void *,
                                          uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
