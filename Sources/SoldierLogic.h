#pragma once
#include "HumanCombat.h"
#include "EnemyMotionAux.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef ClawGenericEnemy ClawSoldier;
// Pointer views compose caller-owned common/Human buffers. human.privateTail
// must provide24 words: Soldier's original480-byte allocation is264+24 words;
// Human methods use the first20. No portable padding belongs to that allocation.
typedef struct ClawSoldierContext {
    ClawHumanEnemyContext *human;
    ClawHumanCombatContext *combat;
    ClawEnemyMotionAuxContext *motion;
    ClawSceneActorHost scene;
    const ClawGenericEnemyState *soldierStates;
    size_t soldierStateCount;
    uint32_t difficulty, actorContainerToken;
    // Projectile services refresh these exact token-addressed views after
    // create and callback. With scene.lookup, live heap views are used instead.
    uint32_t bulletToken;
    uint32_t *bulletActor;
    uint32_t *bulletPrimary;
    uint32_t *bulletPrivate; // At least81 words; Bullet allocation is not inferred.
    uint32_t fault;
} ClawSoldierContext;
// Install the original43-entry Soldier vtable after common defaults.
void claw_soldier_context_defaults(ClawSoldierContext *);
uint32_t claw_soldier_construct(ClawSoldier *, ClawSoldierContext *, ClawGenericEnemyDependency, void *);
uint32_t claw_soldier_tick(ClawSoldier *, ClawSoldierContext *, ClawGenericEnemyDependency, void *);
// Supports exact Soldier and composed common/Human/combat/motion identities.
// Completion is separate from original EAX. Unknown methods return0.
uint32_t claw_soldier_entry(ClawSoldier *, ClawSoldierContext *, uint32_t function, uint32_t argument,
                            ClawGenericEnemyDependency, void *, uint32_t *result);
uint32_t claw_soldier_private_word(const ClawSoldier *, const ClawSoldierContext *, uint32_t byteOffset);
void claw_soldier_set_private_word(ClawSoldier *, ClawSoldierContext *, uint32_t byteOffset, uint32_t value);
#ifdef __cplusplus
}
#endif
