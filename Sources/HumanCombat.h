#pragma once
#include "HumanEnemy.h"
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawHumanCombatContext {
    ClawHumanEnemyContext *human;
    uint32_t actorContainerToken;
    // Supplied host composes the recovered named scene creator. Without lookup,
    // creator4c8da0 is an explicit dependency with all six original arguments.
    ClawSceneActorHost scene;
    // Native fault1 missing state/resource view,2 missing FX/null-create path.
    uint32_t fault;
} ClawHumanCombatContext;
// Whole typed entries44d460/570/5a0/700/730 and hit entries44f3c0/510.
// Support status is separate from original EAX (only hit entries return zero).
// Calls reuse the frozen Human/Common bodies; unknown virtuals and resource,
// audio, hit-particle461a00 services retain their exact dependency identities.
uint32_t claw_human_combat_entry(ClawHumanEnemy *, ClawHumanCombatContext *, uint32_t function, uint32_t attacker,
                                 ClawGenericEnemyDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
