#pragma once
#include "GenericEnemyStates.h"
#include "SceneActorRuntime.h"
#include "WorldLootRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
// Original private allocation1a0=104 words. Wider common snapshot storage is
// preserved above word103 and is never claimed to be original goodie memory.
typedef ClawGenericEnemy ClawBouncingGoodie;
typedef struct ClawBouncingGoodieContext {
    ClawGenericEnemyContext *generic;
    ClawGenericEnemyStatesContext *shared;
    ClawSceneActorHost scene;
    uint32_t sequenceRegistryToken;
    ClawWorldLootGlobals *loot; // Optional; enables native4736b0 table binding.
    const ClawGenericEnemyState *states;
    size_t stateCount;
    // Live image root bounds/leaf supplied by resource service. Header words
    //6..9 are original leaf18..24, used for move/hit rectangle generation.
    int32_t imageMinimum, imageMaximum;
    uint32_t minimumImageToken, imageHeader[16];
    uint32_t fault;
} ClawBouncingGoodieContext;
void claw_bouncing_goodie_context_defaults(ClawBouncingGoodieContext *);
//40e690 cdecl(actor) wrapper; allocates1a0 through scene.allocate or explicit
//CRT4f63ec dependency. The owner commits generic.enemyToken and primary18.
uint32_t claw_bouncing_goodie_callback(ClawBouncingGoodie *, ClawBouncingGoodieContext *, ClawGenericEnemyDependency,
                                       void *);
// Whole original constructor and bounded entry dispatch. Support is distinct
//from original result; constructor returns private token, states return0.
uint32_t claw_bouncing_goodie_entry(ClawBouncingGoodie *, ClawBouncingGoodieContext *, uint32_t function,
                                    uint32_t argument, ClawGenericEnemyDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
