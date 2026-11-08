#pragma once
#include "GenericEnemyStates.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef ClawGenericEnemy ClawHumanEnemy;
// Views point directly into a caller's Officer or other Human-derived context.
// enemy[0..263] plus privateTail[0..19] represent original words0..283.
typedef struct ClawHumanEnemyContext {
    ClawGenericEnemyContext *generic;
    ClawGenericEnemyStatesContext *sharedStates;
    uint32_t *privateTail;
    float damageScale, healthScale, rangeScale;
    uint32_t sequenceRegistryToken, clockCountdown;
    const ClawGenericEnemyState *humanStates;
    size_t humanStateCount;
    uint32_t effectToken;
    uint32_t *effectActor;
    uint32_t *effectPrimary;
    uint32_t *effectPrivate;
    uint32_t otherActorToken;
    uint32_t *otherActor;
    uint32_t *otherPrimary;
    uint32_t *platformPrimary;
    // Native diagnostic, no corresponding original gameplay field.
    uint32_t fault;
} ClawHumanEnemyContext;
uint32_t claw_human_enemy_construct(ClawHumanEnemy *, ClawHumanEnemyContext *, ClawGenericEnemyDependency, void *);
// Original identity dispatch. Support/completion is separate from original
// EAX result. Unknown entries return0 without substituting a generic body.
uint32_t claw_human_enemy_entry(ClawHumanEnemy *, ClawHumanEnemyContext *, uint32_t function, uint32_t argument,
                                ClawGenericEnemyDependency, void *, uint32_t *result);
uint32_t claw_human_enemy_dispatch(ClawHumanEnemy *, ClawHumanEnemyContext *, int32_t state, ClawGenericEnemyDependency,
                                   void *);
uint32_t claw_human_enemy_private_word(const ClawHumanEnemy *, const ClawHumanEnemyContext *, uint32_t byteOffset);
void claw_human_enemy_set_private_word(ClawHumanEnemy *, ClawHumanEnemyContext *, uint32_t byteOffset, uint32_t value);
#ifdef __cplusplus
}
#endif
