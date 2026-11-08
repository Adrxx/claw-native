#ifndef CLAW_COLLISION_RESPONSE_H
#define CLAW_COLLISION_RESPONSE_H
#include "TileCollision.h"
#include "PlayerEngine.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t flags, x, y, mode, type, stepX, stepY;
    uint32_t supportToken, token, deltaX, deltaY;
    ClawPlayerRect moveRect, hitRect;
} ClawCollisionActor;
typedef struct {
    const uint32_t *cells;
    const uint32_t *rowOffsets;
    int32_t width, height;
    uint32_t shiftX, shiftY;
    const ClawTileDescription *descriptions;
    uint32_t descriptionCount;
    const ClawCollisionActor *actors;
    uint32_t actorCount, maximumStepX, maximumStepY;
} ClawCollisionWorld;
uint32_t claw_collision_resolve(const ClawCollisionWorld *world, ClawCollisionActor *actor, uint32_t x, uint32_t y,
                                uint32_t options);
uint32_t claw_collision_move(const ClawCollisionWorld *world, ClawCollisionActor *actor, uint32_t x, uint32_t y,
                             uint32_t options);
typedef uint32_t (*ClawCollisionResolver)(const ClawCollisionWorld *, ClawCollisionActor *, uint32_t, uint32_t, uint32_t, void *);
uint32_t claw_collision_move_with_resolver(const ClawCollisionWorld *, ClawCollisionActor *, uint32_t, uint32_t,
                                          uint32_t, ClawCollisionResolver, void *);
// Native joins for the four retained movement helpers used by the v1.3 dispatcher.
uint32_t claw_collision_response_helper(uint32_t, const ClawCollisionWorld *, ClawCollisionActor *, uint32_t, uint32_t, uint32_t);
// Original 0x4cd800 positions the actor immediately above the first supporting
// tile below its center foot. Returns 0 without moving when none is found.
uint32_t claw_collision_place_on_ground(const ClawCollisionWorld *world, ClawCollisionActor *actor);
// Whole4cda10: inclusive horizontal point probes at fixed Y, including the
// final target probe. Only attribute1 blocks. Step must be positive; invalid
// native/non-progressing loop inputs report fault1, not an original completion.
uint32_t claw_collision_horizontal_clear(const ClawCollisionWorld *, uint32_t x, uint32_t y, uint32_t targetX,
                                         uint32_t step, uint32_t *fault);
#ifdef __cplusplus
}
#endif
#endif
