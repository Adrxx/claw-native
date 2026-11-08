#ifndef CLAW_AQUATIS_RUNTIME_H
#define CLAW_AQUATIS_RUNTIME_H
#include "GabrielRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
// Actual retail Aquatis callback4041f0 /flags1, private0x4f0, VT50b0b4.
// Raw534874 is boss-private; raw534878 is the inherited frenzy alternator.
// Fingerprinted canonical WWD places this family in Level12 (not13).
typedef struct ClawAquatisContext {
    ClawSceneActorHost scene;
    ClawRauxGlobals *globals;
    uint32_t composeBoss, composeAnimation, composeImages, maximumSteps, fault;
} ClawAquatisContext;
typedef struct ClawAquatisCall {
    uint32_t function, receiver, argumentCount, arguments[12];
    const char *name;
} ClawAquatisCall;
typedef uint64_t (*ClawAquatisDependency)(ClawAquatisContext *, const ClawAquatisCall *, void *);
// cdecl facade args=(actor),receiver0; ctor thiscall args=(actor).
// Method/state receiver is private; selector takescaptured numericstate.
// Explicit named dynamic controllers/physical resources/audio/scene services
// retain their original identities. Unknown0; requirefault0 forcompletion;
// original meaningfulEAX is separate. Fault1 span/service,2 unsafeprefix,
//3 ABI/boundedloop. Source-sized109word actors are shadowed forportableANI.
uint32_t claw_aquatis_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                            ClawAquatisContext *, ClawAquatisDependency, void *, uint32_t *result);
uint32_t claw_aquatis_allocation_bytes(uint32_t registeredCallback);
uint32_t claw_aquatis_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
