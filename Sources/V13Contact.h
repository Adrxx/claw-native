#pragma once
#include "CollisionResponse.h"
#ifdef __cplusplus
extern "C" {
#endif
// Native boundary records retain stable app identities and existing layouts.
typedef struct {
    ClawCollisionActor actor;
    uint32_t mask, otherToken, hasCallback;
} ClawV13ContactActor;
typedef uint32_t (*ClawV13BumpCallback)(ClawV13ContactActor *, uint32_t, uint32_t, void *);
uint32_t claw_v13_contact_resolve(const ClawCollisionWorld *, ClawV13ContactActor *, uint32_t count,
    uint32_t mover, uint32_t x, uint32_t y, uint32_t options, ClawV13BumpCallback, void *, uint32_t *fault);
uint32_t claw_v13_collision_resolve(const ClawCollisionWorld *, uint32_t managerFlags,
    ClawV13ContactActor *, uint32_t count, uint32_t mover, uint32_t x, uint32_t y,
    uint32_t options, ClawV13BumpCallback, void *, uint32_t *fault);
uint32_t claw_v13_collision_move(const ClawCollisionWorld *, uint32_t managerFlags,
    ClawV13ContactActor *, uint32_t count, uint32_t mover, uint32_t x, uint32_t y,
    uint32_t options, ClawV13BumpCallback, void *, uint32_t *fault);
void *claw_v13_bump_create(uint32_t identity, uint32_t scene, uint32_t *fault);
void claw_v13_bump_destroy(void *);
uint32_t claw_v13_bump_invoke(void *, uint32_t *fault);
#ifdef __cplusplus
}
#endif
