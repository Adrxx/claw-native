#ifndef CLAW_PUNK_RAT_RUNTIME_H
#define CLAW_PUNK_RAT_RUNTIME_H
#include "GenericEnemyStates.h"
#include "ActorAnimationRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_PUNK_RAT_PRIVATE_BYTES 0x410u
#define CLAW_PUNK_RAT_PRIVATE_WORDS 260u
typedef struct ClawPunkRatGlobals {
    uint32_t tick, animationDelta, randomDisabled, audioEnabled, masterVolume, powerup;
    float healthScale;
} ClawPunkRatGlobals;
typedef struct ClawPunkRatContext {
    ClawSceneActorHost scene;
    ClawPunkRatGlobals *globals;
    // Borrowed frozen common model views. Only260 source private words are
    // transferred; compatibility padding in GenericEnemy is never raw-owned.
    ClawGenericEnemyContext *generic;
    ClawGenericEnemyStatesContext *sharedStates;
    uint32_t composeAnimation, composeImages, fault;
} ClawPunkRatContext;
typedef struct ClawPunkRatCall {
    uint32_t function, receiver, argumentCount, arguments[12];
    const char *name;
} ClawPunkRatCall;
typedef uint64_t (*ClawPunkRatDependency)(ClawPunkRatContext *, const ClawPunkRatCall *, void *);
// Registered474330 is cdecl(actor); constructor4743f0 is thiscall(actor).
// Class538458/VT50eee4, exactly260-word private and43-word VT. Scheduler
// 4dc870 public ABI is actualcdecl(receiver0,args{private}). Own movement,
// strike/recoil/startup and destructor retain raw actor/cannon identities.
// GroundCannon4493c0 and firing updates are explicit rich services; directly
// required414640 selector,414660/414860 setters and414a60 mirror are owned.
// Raw name/common table metadata is bridged to frozen model APIs. Initialized
// in-range unique CString/common-array profiles are validated; unusual name
// growth/COW or inherited array growth requires further transport (fault3).
// Borrow existing source common/ANI/resource helpers; don't substitute Rat AI.
// fault1 missing span/service,2 unchecked allocation/composed failure,
//3 ABI/traversal rejection. Completion differs from meaningful originalEAX.
uint32_t claw_punk_rat_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                             ClawPunkRatContext *, ClawPunkRatDependency, void *, uint32_t *result);
uint32_t claw_punk_rat_private_bytes(void);
uint32_t claw_punk_rat_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
