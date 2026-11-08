#ifndef CLAW_GABRIEL_WEAPONS_RUNTIME_H
#define CLAW_GABRIEL_WEAPONS_RUNTIME_H
#include "GabrielRuntime.h"
#include "PlayerProjectileRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
// Exact registered Cannon446550(0x98), Bomb4459d0(0x198), and source-elected
// CannonBall414b20(0x150). Live pointers, including53774c, remain raw tokens.
typedef struct ClawGabrielWeaponsContext {
    ClawSceneActorHost scene;
    ClawRauxGlobals *globals;
    // Borrowed generic Bullet registry/physics context for inherited bodies.
    // Its real named-state profile must come from original registry startup.
    ClawBulletContext *bullet;
    uint32_t composeCore, composeProjectiles, composeAnimation, composeImages;
    uint32_t maximumSteps, fault;
} ClawGabrielWeaponsContext;
typedef struct ClawGabrielWeaponsCall {
    uint32_t function, receiver, argumentCount, arguments[12];
    const char *name;
} ClawGabrielWeaponsCall;
typedef uint64_t (*ClawGabrielWeaponsDependency)(ClawGabrielWeaponsContext *, const ClawGabrielWeaponsCall *, void *);
// Unknown source identity returns0; requirefault0 for completion. Physical
// allocation/actor creation, registry/resource transport, sound and collision
// services retain original address/receiver/argument order. MeaningfulEAX is
// separate from native support. Fault1 missing span/service,2 unsafe source
// prefix,3 ABI/bounded-loop rejection. No substitute terminal success.
uint32_t claw_gabriel_weapons_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                    uint32_t argumentCount, ClawGabrielWeaponsContext *, ClawGabrielWeaponsDependency,
                                    void *, uint32_t *result);
uint32_t claw_gabriel_weapons_allocation_bytes(uint32_t registeredCallback);
uint32_t claw_gabriel_weapons_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
