#pragma once
#include "WorldLootRuntime.h"
#include "PlayerDamage.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawItemPickupContext {
    ClawSceneActorHost scene;
    ClawWorldLootGlobals *loot;
    ClawPlayerLocomotion *player;
    uint32_t playerToken, playerPrimaryToken, playerPrivateToken;
    uint32_t managerToken; // Original5371fc; startup reads manager+124.
    uint32_t animationDelta, stageDelta, tick, audioEnabled, masterVolume;
    uint32_t lastSoundTick, lastSoundToken; // Original534ec0/534ec4 dedup cache.
    uint32_t auxiliaryManagerToken;         // Original534874 (dynamite branch).
    uint32_t auxiliarySceneToken;           // Original5349dc compared by whole405f80.
    uint32_t composeCreation, fault;
} ClawItemPickupContext;
typedef struct ClawItemPickupCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    const char *name;
} ClawItemPickupCall;
typedef uint32_t (*ClawItemPickupDependency)(ClawItemPickupContext *, const ClawItemPickupCall *, void *);
// Raw actor/logic/resource/player spans retain original token identities.
// Unknown/out-of-scope entries return0; original result is separate.
uint32_t claw_item_pickup_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                                ClawItemPickupContext *, ClawItemPickupDependency, void *, uint32_t *result);
// Compose frozen CaptainClawHit for ordinary supported pickup categories.
// Requires exact player/attacker binding and commits live item/player views at
//each dependency boundary. Gate/scheduling remains ActorInteractions-owned.
uint32_t claw_item_pickup_award(uint32_t itemToken, ClawItemPickupContext *, ClawItemPickupDependency, void *);
#ifdef __cplusplus
}
#endif
