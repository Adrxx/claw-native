#ifndef CLAW_WORLD_LOOT_RUNTIME_H
#define CLAW_WORLD_LOOT_RUNTIME_H
#include "SceneActorRuntime.h"
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_WORLD_LOOT_ITEM_CAPACITY 66
// Exact contiguous537ec8..53841b: 66 image-root tokens, values, interaction
// masks, ten preserved gap words, logic metadata, sound resources, and flag.
// Offsets: images0,values66,masks132,logic208,sounds274,flag340. Other
// fields represent original52a190 count,532c10 volume and53721c launch mode.
typedef struct ClawWorldLootGlobals {
    uint32_t words[341], itemCount, audioVolume, highLaunch, configurationWord;
} ClawWorldLootGlobals;
typedef struct ClawWorldLootContext {
    ClawSceneActorHost scene;
    // When1, named creation composes frozenSceneActorRuntime directly. When0,
    //4c8da0 is an exact six-argument dependency returning a live actor token.
    uint32_t composeCreation, fault;
} ClawWorldLootContext;
typedef struct ClawWorldLootCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    const char *name; // Optional text for a supplied literal/resource name.
} ClawWorldLootCall;
typedef uint32_t (*ClawWorldLootDependency)(ClawWorldLootGlobals *, ClawWorldLootContext *, const ClawWorldLootCall *,
                                            void *);
// Only pinned image values: count66, volume100 and launchMode0.
void claw_world_loot_defaults(ClawWorldLootGlobals *);
// Actual4719e0 initializer clears66 image/value slots, fills62 records, then
// sets itemCount62. configurationWord is the first word at original537960.
uint32_t claw_world_loot_initialize(uint32_t sceneToken, ClawWorldLootGlobals *, ClawWorldLootContext *,
                                    ClawWorldLootDependency, void *);
// Whole42df90 inventory wrapper. Receiver layout: ownerLogic+8,sound+20,
// slotCount+24,nonzeroCount+28,IDs+2c,sourceActor+6c. All are raw live words.
// Resource image binding and actual created-actor callback remain services;
// no approximate pickup, projectile or resource behavior is substituted.
uint32_t claw_world_loot_drop(uint32_t receiver, ClawWorldLootGlobals *, ClawWorldLootContext *,
                              ClawWorldLootDependency, void *);
// Actual473630: valid index returns imageRootToken+24, including null-root+24;
// invalid signed index returns originalGAME_TREASURE_COINS literal5279b8.
uint32_t claw_world_loot_name_token(int32_t item, const ClawWorldLootGlobals *);
// Actual473660: select the initialized loot metadata callback, reset primary
// state to0 and invoke it. Pickup/award callback bodies remain explicit.
uint32_t claw_world_loot_rebind_actor(uint32_t actorToken, int32_t item, ClawWorldLootGlobals *, ClawWorldLootContext *,
                                      ClawWorldLootDependency, void *);
// Recovered4a3050 state update after its explicit thread-local context lookup.
// Caller shares this mutable seed with other original RNG consumers.
uint32_t claw_world_loot_next_random(uint32_t *seed);
#ifdef __cplusplus
}
#endif
#endif
