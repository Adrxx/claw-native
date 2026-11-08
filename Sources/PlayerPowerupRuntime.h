#ifndef CLAW_PLAYER_POWERUP_RUNTIME_H
#define CLAW_PLAYER_POWERUP_RUNTIME_H
#include "SceneActorRuntime.h"
#include "PlayerInputDispatch.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlayerPowerupGlobals {
    uint32_t managerToken;                //5371fc
    uint32_t playerToken;                 //537e88;41fc00 wrapper only
    uint32_t powerup, remaining, expired; //534eac,534ea8,534eb8
    uint32_t musicDisabled;               //53c9c0
    uint32_t cycleRemaining, cycleIndex;  //534ec8,534ecc;420070
} ClawPlayerPowerupGlobals;
typedef struct ClawPlayerPowerupRuntimeContext {
    ClawSceneActorHost scene;
    ClawPlayerPowerupGlobals *globals;
    uint32_t fault;
} ClawPlayerPowerupRuntimeContext;
typedef struct ClawPlayerPowerupCall {
    uint32_t function, receiver, argumentCount, arguments[6];
    const char *name; // Original literal name, synchronous optional text.
} ClawPlayerPowerupCall;
typedef uint32_t (*ClawPlayerPowerupDependency)(ClawPlayerPowerupRuntimeContext *, const ClawPlayerPowerupCall *,
                                                void *);
//41f990 cdecl(actor,primary,private,powerup,duration);41fc00(type,duration).
//41fc30(actor,primary,private,delta) composes frozen PlayerInputDispatch.
//Additional finite helpers:4ce7b0(imageManager,[effect]),448400(actor),
//420070(actor,delta), and confirmed single-RET4bc110.
//All raw actor/private/image/music/effect spans retain caller token identities.
//Physical audio/image effect/scene creation stay exact dependency calls.
//Return1 completed/covered;0 unsupported/fault. Meaningful original result is
//separate; void incidental EAX excluded. fault1 missing graph/service,
//fault2 argument/bounded traversal rejection; clear fault before a new call.
uint32_t claw_player_powerup_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                   uint32_t argumentCount, ClawPlayerPowerupRuntimeContext *,
                                   ClawPlayerPowerupDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
