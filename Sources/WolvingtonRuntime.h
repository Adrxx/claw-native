#ifndef CLAW_WOLVINGTON_RUNTIME_H
#define CLAW_WOLVINGTON_RUNTIME_H
#include "RauxRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
// Original Wolvington49fb30, literal522c54, private478 bytes, vtable50ff2c.
// Uses the identical inherited CBoss source globals without assigning new IDs.
typedef struct ClawWolvingtonContext {
    ClawSceneActorHost scene;
    ClawRauxGlobals *globals;
    uint32_t composeAnimation, composeImages, composeBoss, fault;
} ClawWolvingtonContext;
typedef struct ClawWolvingtonCall {
    uint32_t function, receiver, argumentCount, arguments[12];
    const char *name;
} ClawWolvingtonCall;
typedef uint64_t (*ClawWolvingtonDependency)(ClawWolvingtonContext *, const ClawWolvingtonCall *, void *);
// Raw source identities remain tokens; dependency preserves exact call ABI.
// Native support/fault is distinct from meaningful original EAX. No fallback
// gameplay is substituted for an unknown original method or missing service.
uint32_t claw_wolvington_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                               ClawWolvingtonContext *, ClawWolvingtonDependency, void *, uint32_t *result);
uint32_t claw_wolvington_private_bytes(void);
// Owned allocations:410340=158,49fb30=478; LFX458010 is FlareRuntime.
uint32_t claw_wolvington_allocation_bytes(uint32_t registeredCallback);
uint32_t claw_wolvington_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
