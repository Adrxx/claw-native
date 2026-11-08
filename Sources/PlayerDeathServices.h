#ifndef CLAW_PLAYER_DEATH_SERVICES_H
#define CLAW_PLAYER_DEATH_SERVICES_H
#include "ActorDestruction.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlayerDeathServiceGlobals {
    uint32_t managerToken;     //5371fc
    uint32_t emptyStringToken; //Shared original CString data identity.
} ClawPlayerDeathServiceGlobals;
typedef struct ClawPlayerDeathServiceContext {
    ClawSceneActorHost scene;
    ClawPlayerDeathServiceGlobals *globals;
    //Caller-owned four-byte scratch object replacing the original local
    //CString's stack identity. Required only for reached name-copy branches.
    //Public479f10 later reuses that dead local cell as packet-text pointer.
    uint32_t temporaryStringToken, fault;
} ClawPlayerDeathServiceContext;
typedef struct ClawPlayerDeathServiceCall {
    uint32_t function, receiver, argumentCount, arguments[4];
    //Adapted synchronous native stack buffers. Their argument token is0.
    //4a3920: buffers0=output256,1=phrase/input; arguments2=name data token.
    //Public sender preserves raw input token in argument3 when applicable.
    //422370: buffers0=complete displayed text; argument0=0.
    uint8_t *buffers[2];
    uint32_t bufferBytes[2];
} ClawPlayerDeathServiceCall;
typedef uint32_t (*ClawPlayerDeathServiceDependency)(ClawPlayerDeathServiceContext *,
                                                     const ClawPlayerDeathServiceCall *, void *);
//Complete41ebd0 notification and confirmed4b7aa0 RET4 (no audio effects).
//Finite named-string wrapper41ee40/CString shared-copy4f6449, plus notification
//send479f10. CString locked-copy assignment, RNG, format, UI and network
//platform bodies remain explicit services; shared destruction composes frozen
//ActorDestruction4f6584. Finite send gate47a220 is native; player lookup4e0c60
//and original1024-byte allocation remain exact services/scene allocator.
//Raw41ebd0/4b7aa0 are void: incidental EAX is excluded. Other meaningful
//original returns are separate. Return1 covered/completed;0 unsupported/fault.
//fault1 missing graph/service,2 bounded string/argument domain rejection.
uint32_t claw_player_death_service_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                         uint32_t argumentCount, ClawPlayerDeathServiceContext *,
                                         ClawPlayerDeathServiceDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
