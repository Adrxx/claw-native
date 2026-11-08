#ifndef CLAW_KATHERINE_RUNTIME_H
#define CLAW_KATHERINE_RUNTIME_H
#include "RauxRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_KATHERINE_PRIVATE_BYTES 0x478u
#define CLAW_KATHERINE_PRIVATE_WORDS 286u
typedef ClawRauxGlobals ClawKatherineGlobals;
typedef struct ClawKatherineContext {
    ClawSceneActorHost scene;
    ClawKatherineGlobals *globals;
    uint32_t composeAnimation, composeImages, fault;
} ClawKatherineContext;
typedef struct ClawKatherineCall {
    uint32_t function, receiver, argumentCount, arguments[12];
    const char *name;
} ClawKatherineCall;
typedef uint64_t (*ClawKatherineDependency)(ClawKatherineContext *, const ClawKatherineCall *, void *);
/* Actual registry Katherine ID37/literal522c9c/callback453d30(flags0).
   Raw private478bytes/286words, vtable50e2a4, class array537980. Globals
   borrow Raux/CBoss live aliases:5371fc,537e88,537210,5430c4,534eac,
   532c0c/532c10,541334,5349dc, scales5262b0/b4/b8. No new defaults.
   All source IDs/name CString tokens/class arrays remain host-addressable.
   The pre4547c0 compares literal-pointer identities, not matching text.
   Reuses frozenRaux CBoss bodies; inherited Human/Generic/Combat/strike/loot
   are exact address services to the existing host composition. EndLevelGem
   owner supplies40e5c0; source death does not fabricate a gem or completion.
   Specialized bodies:453d30 cdecl(actor),453df0 thiscall(actor),4542f0(flags),
   454310(),4543e0(state),4547c0(nameToken),4548c0(hitMode),454a10(),454b90(),
   454c20(),454cb0(),4550e0(),455230(),455280(),4552d0(),455350(),
   455360(wrapper,ANI,eager),4553a0(stateName),40f780(wrapper,resourceName).
   Existing wrapper/ANI/physics helpers compose where actual source calls.
   Returns completion/support separately from meaningful EAX. Unknown0,
   fault1 missingspan/service,2 unsafeprefix,3 argument/domain. Clear fault.
   Physical RNG/scene collision/resource/audio remain exact address services;
   native root may route them through its frozen shared implementations. */
uint32_t claw_katherine_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                              ClawKatherineContext *, ClawKatherineDependency, void *, uint32_t *result);
uint32_t claw_katherine_private_bytes(void);
uint32_t claw_katherine_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
