#ifndef CLAW_END_LEVEL_GEM_RUNTIME_H
#define CLAW_END_LEVEL_GEM_RUNTIME_H
#include "PowerupObjectRuntime.h"
#include "GenericEnemy.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_END_LEVEL_GEM_PRIVATE_BYTES 0x150u
#define CLAW_END_LEVEL_GEM_PRIVATE_WORDS 84u
typedef struct ClawEndLevelGemContext {
    ClawSceneActorHost scene;
    ClawWorldLootGlobals *loot;
    ClawActorAnimationGlobals *animation;
    // Verified original ID/name mapping and common service identities. Motion,
    // queued post and FSM marshal84 private/109 actor words; no264-word heap.
    ClawGenericEnemyContext *common;
    ClawPowerupObjectContext *pickups;
    uint32_t composeCreation, composeAnimation, composeCommon, composeLoot;
    uint32_t maximumSteps, fault;
} ClawEndLevelGemContext;
typedef struct ClawEndLevelGemCall {
    uint32_t function, receiver, argumentCount, arguments[12];
    const char *name;
} ClawEndLevelGemCall;
typedef uint64_t (*ClawEndLevelGemDependency)(ClawEndLevelGemContext *, const ClawEndLevelGemCall *, void *);
void claw_end_level_gem_defaults(ClawEndLevelGemContext *);
//43ca60(actor)/4701b0(actor) cdecl callbacks;43cb20(actor) ECX private ctor;
//40e5c0() ECX boss private (requires0x460 bytes);43cdc0(state),43d070(),
//43d0f0(targetX,targetY) ECX gem private.4205b0() cdecl player restoration.
//Raw source globals:537210 tick,537e88 player,5371fc app,537204 input,
//532c0c/532c10 audio gate/volume,52be14/18 forced camera,534e60[6] remainders.
//Class function array537608, name trie537668 and ID CString array537698
//are live identities. Bootstrap them through frozen LogicStateRegistry.
//Physical resource/image binding, registry growth, collision/audio/OS services
//retain exact addresses. Rebinding31 composes frozenWorldLoot; pickup26ad
//composes frozenPowerupObject and requests800e without inventing success.
//Also supported:4082f0(actor),4dc870(private)cdecl,4dca10(),
//4063b0(unusedName),484d90(deleteFlag),456030(),4c9e30(unusedName),
//4c96b0(),4bb030(),4719e0(scene)cdecl. Unknown identities return0.
//Supported identity returns1; requirefault0 for completion.
uint32_t claw_end_level_gem_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                  uint32_t argumentCount, ClawEndLevelGemContext *, ClawEndLevelGemDependency, void *,
                                  uint32_t *result);
//Requires original hit election/player+74 binding. Frozen pickup composition
//needs existing portable128-word actor/item backing, distinct from original
//1b4-byte actor allocation. This helper restores the borrowed pickup host.
uint32_t claw_end_level_gem_award(uint32_t itemToken, ClawEndLevelGemContext *, ClawEndLevelGemDependency, void *,
                                  uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
