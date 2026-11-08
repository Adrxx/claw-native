#ifndef CLAW_LIFT_THROW_RUNTIME_H
#define CLAW_LIFT_THROW_RUNTIME_H
#include "SceneActorRuntime.h"
#include "PlayerAttackInput.h"
#include "CoreRegistration.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawLiftThrowGlobals {
    uint32_t playerToken, inputToken, stageDelta, animationDelta, tick, powerup;
    uint32_t pixelScratch, audioEnabled, masterVolume, strongThrow;
    uint32_t physicsDefaults[24]; // Original513e10..513e6f, caller live values.
} ClawLiftThrowGlobals;
typedef struct ClawLiftThrowContext {
    ClawSceneActorHost scene;
    ClawLiftThrowGlobals *globals;
    ClawPlayerPhysics *playerPhysics; // Whole original534db8 object.
    ClawPlayerAttackContext *attack;  // Existing selector adapter, only input entries.
    uint32_t enemyWordCount;          // Actual raw private allocation; keg260, Rat264.
    uint32_t composeAnimation, fault;
    ClawCoreRegistrationGlobals *core; // Shared diagnostics; resize failure reads raw virtual(wordCount+4).
} ClawLiftThrowContext;
typedef struct ClawLiftThrowCall {
    uint32_t function, receiver, argumentCount, arguments[12];
    const char *name;
} ClawLiftThrowCall;
typedef uint64_t (*ClawLiftThrowDependency)(ClawLiftThrowContext *, const ClawLiftThrowCall *, void *);
// Copies only the original physics defaults, preserving caller clock/aliases.
void claw_lift_throw_defaults(ClawLiftThrowGlobals *);
// Source thiscall enemy entries use receiver=private token; player cdecl entries
// use receiver0 and actual actor/primary/private/target stack argument tokens.
// Known inherited enemy bodies compose frozenEnemyMotionAux/GenericEnemyStates.
// Support status is distinct from original meaningful EAX; clear fault0 first.
uint32_t claw_lift_throw_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                               ClawLiftThrowContext *, ClawLiftThrowDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
