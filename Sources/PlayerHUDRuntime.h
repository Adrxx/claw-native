#ifndef CLAW_PLAYER_HUD_RUNTIME_H
#define CLAW_PLAYER_HUD_RUNTIME_H
#include "CheckpointTimerRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawPlayerHUDGlobals {
    uint32_t initialScore, initialHealth, powerupRemaining, audioEnabled;
    // Original534cc4,534cc8,534ea8,532c0c. Remaining is the shared player
    // powerup deadline/countdown storage, not optional checkpoint remaining.
} ClawPlayerHUDGlobals;
typedef struct ClawPlayerHUDContext {
    ClawSceneActorHost scene;
    ClawCheckpointTimerContext *shared; // Borrow manager/player/bounds/cache,
    // frozen HUD/number creation, collection dispatch and teardown composition.
    ClawPlayerHUDGlobals *globals;
    uint32_t composeAnimation, composeImages, composeFormatting, composeControllers, fault;
} ClawPlayerHUDContext;
typedef struct ClawPlayerHUDCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    const char *name;
    uint32_t localMask;
    char *buffer;
    uint32_t bufferBytes;
} ClawPlayerHUDCall;
typedef uint32_t (*ClawPlayerHUDDependency)(ClawPlayerHUDContext *, const ClawPlayerHUDCall *, void *);
// Whole cdecl ScoreFrame4908b0/WeaponFrame490f80/HealthFrame490c50/
// LivesFrame4912a0/TimerFrame491540(actor). Primary18 owns a0x60-byte HUD,
// Weapon/Health primary168 retains a player private token; Health130 is the
// source heartbeat countdown. No new actor subclass/private allocator.
// Meaningful callback EAX is separate from recognized/completed return.
// The rich ABI retains normalized callback-scoped format output pointers.
// fault1 missing span/service,2 allocator/original unsafe prefix,
//3 unsupported arguments or native metadata/format rejection.
uint32_t claw_player_hud_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                               ClawPlayerHUDContext *, ClawPlayerHUDDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
