#ifndef CLAW_POWERUP_OBJECT_RUNTIME_H
#define CLAW_POWERUP_OBJECT_RUNTIME_H
#include "ItemPickupRuntime.h"
#include "PlayerPowerupRuntime.h"
#include "ActorAnimationRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPowerupObjectArguments {
    uint32_t words[6], count;
} ClawPowerupObjectArguments;
typedef struct ClawPowerupObjectCall {
    uint32_t function, receiver, arguments[6], argumentCount;
    const char *name;
} ClawPowerupObjectCall;
typedef struct ClawPowerupObjectContext {
    ClawSceneActorHost scene;
    ClawWorldLootGlobals *loot;
    ClawItemPickupContext *items;              // Borrow existing sound-cache/stage/audio aliases.
    ClawPlayerPowerupRuntimeContext *powerups; // Borrow shared534eac/ea8/eb8 etc.
    ClawPlayerPhysics *physics;                // Original534db8 complete object; warp/swing stores only.
    ClawActorAnimationGlobals *animation;
    uint32_t inputToken;   // Original537204, cleanup input+0xc.
    uint32_t curseEnabled; // Original52550c.
    uint32_t warpX, warpY; // Original529fa0/529fa4; published before WM_COMMAND805c.
    uint32_t composeAnimation, composeCreation, fault;
} ClawPowerupObjectContext;
typedef uint32_t (*ClawPowerupObjectDependency)(ClawPowerupObjectContext *, const ClawPowerupObjectCall *, void *);
// Source registered callbacks470430 SpecialPowerup /470a20 CursePowerup are
// cdecl(actor), receiver0 + one actor-token arg. Curse rejects original mode3
// singleplayer; mode4 dependencies remain explicit, never simulated effects.
// Shared selector41ee60 is cdecl(player,primary,private,pickup), with frozen
// powerup setter/sound/marker bodies composed over live caller heap/globals.
// Completion status is separate from meaningful original EAX; clear fault0.
uint32_t claw_powerup_object_entry(uint32_t function, uint32_t receiver, ClawPowerupObjectArguments,
                                   ClawPowerupObjectContext *, ClawPowerupObjectDependency, void *, uint32_t *result);
// Composition of frozen CaptainClawHit for the exact item type0x100 only.
// Actor+74 must already identify itemToken; actor-hit election stays external.
uint32_t claw_powerup_object_award(uint32_t itemToken, ClawPowerupObjectContext *, ClawPowerupObjectDependency, void *,
                                   uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
