#pragma once
#include "HumanEnemy.h"
#include "CollisionResponse.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawEnemyMotionAuxContext {
    ClawHumanEnemyContext *human;
    // The ledge body's first left-side point probe is inlined in the original;
    // this immutable world supplies its actual cell/description data. Remaining
    // 4207f0 calls are explicit dependency queries when a callback is supplied.
    const ClawCollisionWorld *world;
    uint32_t strongThrow; // Original global537224.
    uint32_t fault;
} ClawEnemyMotionAuxContext;
// Native lift440420, release callbacks440710/440350, throw440120,
// flailing4407d0, dropped4409d0, marker440410, ledge43eab0. Existing
// lifted/thrown/flailing/dropped updates compose frozen GenericEnemyStates.
// Support status is separate from original result (ledge bool, others zero).
uint32_t claw_enemy_motion_aux_entry(ClawGenericEnemy *, ClawEnemyMotionAuxContext *, uint32_t function,
                                     uint32_t argument, ClawGenericEnemyDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
