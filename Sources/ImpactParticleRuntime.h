#ifndef CLAW_IMPACT_PARTICLE_RUNTIME_H
#define CLAW_IMPACT_PARTICLE_RUNTIME_H
#include "SceneActorRuntime.h"
#include "ActorAnimationRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawImpactParticleContext {
    ClawSceneActorHost scene;
    ClawActorAnimationGlobals animation;
    // Nonzero composes frozen complete scene creator / ANI wrappers.
    // Their resource/registry/audio services still retain exact identities.
    uint32_t composeCreation, composeAnimation, fault;
} ClawImpactParticleContext;
typedef struct ClawImpactParticleCall {
    uint32_t function, receiver, argumentCount, arguments[6];
    const char *name;
} ClawImpactParticleCall;
typedef uint32_t (*ClawImpactParticleDependency)(ClawImpactParticleContext *, const ClawImpactParticleCall *, void *);
// Entire original cdecl roots: 461a00(scene,x,y,z,style,sourceActor),
// 461c40(scene,x,y,z), HitBurst461a90(actor), Splash461bc0(actor).
// No subclass-private allocation: frozen generic creator allocates animated
// actor 0x1b4/common logic 0x174; controllers store state in those raw buffers.
// Return native support separately from meaningful original EAX. Fault 1:
// missing span/service; 2: invalid ABI; frozen creator/ANI faults propagate.
// animation globals preserve source 5430c4 delta and 532c10 audio position.
uint32_t claw_impact_particle_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                    uint32_t argumentCount, ClawImpactParticleContext *, ClawImpactParticleDependency,
                                    void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
