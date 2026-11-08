#ifndef CLAW_GABRIEL_RUNTIME_H
#define CLAW_GABRIEL_RUNTIME_H
#include "RauxRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
// Exact retail family:Gabriel443290 private538, Cannon446550 private98,
// dynamicBomb4459d0 private198. Source pointers remain raw32-bit identities.
typedef struct ClawGabrielContext {
    ClawSceneActorHost scene;
    ClawRauxGlobals *globals;
    uint32_t composeBoss, composeAnimation, composeImages, maximumSteps, fault;
} ClawGabrielContext;
typedef struct ClawGabrielCall {
    uint32_t function, receiver, argumentCount, arguments[12];
    const char *name;
} ClawGabrielCall;
typedef uint64_t (*ClawGabrielDependency)(ClawGabrielContext *, const ClawGabrielCall *, void *);
// Borrowed inherited globals identical toCBoss; direct raw53774c is live
// Gabriel-private identity, distinct from5349dc generic boss-actor identity.
// Public supported inventory is documented after original comparison.
// Unknown identity returns0. Requirefault0 for actual completion; meaningful
// originalEAX is separate from native support/diagnostic status.
uint32_t claw_gabriel_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                            ClawGabrielContext *, ClawGabrielDependency, void *, uint32_t *result);
uint32_t claw_gabriel_allocation_bytes(uint32_t registeredCallback);
uint32_t claw_gabriel_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
