#ifndef CLAW_RAUX_RUNTIME_H
#define CLAW_RAUX_RUNTIME_H
#include "ActorAnimationRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawRauxGlobals {
    uint32_t managerToken, playerToken, tick, animationDelta, levelWord;
    uint32_t audioEnabled, masterVolume, jumpDisabled, bossActorToken;
    float damageScale, healthScale, rangeScale;
    // Source5371fc/537e88/537210/5430c4/534eac,532c0c/532c10,
    //541334/5349dc and5262b0/b4/b8. Identities remain actual raw tokens.
} ClawRauxGlobals;
typedef struct ClawRauxContext {
    ClawSceneActorHost scene;
    ClawRauxGlobals *globals;
    uint32_t composeAnimation, composeImages, fault;
} ClawRauxContext;
typedef struct ClawRauxCall {
    uint32_t function, receiver, argumentCount, arguments[12];
    const char *name;
} ClawRauxCall;
typedef uint64_t (*ClawRauxDependency)(ClawRauxContext *, const ClawRauxCall *, void *);
// Original registered Raux47e210(actor), private constructor47e2d0(actor),
// raw0x478-byte/286-word allocation, vtable50f1ac. The first0x460 bytes are
// inherited CBoss40e0d0→CHuman44c000; all specialized methods retain raw spans.
// Shared Human/Generic/Combat/Loot/BossMeter bodies use explicit original
// address calls so the host can compose their frozen implementations.
// Completion/support is separate from meaningful original scalar result.
// Clear fault before entry.1 missing span/service (including unsafe prefixes),
//2 composed-layer scope diagnostic,
//3 bounded unsupported metadata/argument diagnostic.
uint32_t claw_raux_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                         ClawRauxContext *, ClawRauxDependency, void *, uint32_t *result);
uint32_t claw_raux_private_bytes(void);
uint32_t claw_raux_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
