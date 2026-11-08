#pragma once
#include "GenericEnemy.h"
#ifdef __cplusplus
extern "C" {
#endif
// The original projectile allocation is0x170 (92 words). The shared snapshot
// keeps the wider enemy plane for existing host adapters; words92..263 are
// portable storage and preserved, never claimed to belong to RatBomb.
typedef ClawGenericEnemy ClawRatBomb;
typedef struct {
    ClawGenericEnemyContext generic;
    uint32_t sequenceRegistryToken;
    float damageScale;
    int32_t imageMinimum, imageMaximum;
    uint32_t minimumImageToken, imageHeader[16];
    uint32_t audioManagerAvailable, masterVolume, bounceSoundPoolToken, explosionSoundPoolToken;
    uint32_t fault;
} ClawRatBombContext;
void claw_rat_bomb_context_defaults(ClawRatBombContext *);
uint32_t claw_rat_bomb_construct(ClawRatBomb *, ClawRatBombContext *, ClawGenericEnemyDependency, void *);
uint32_t claw_rat_bomb_tick(ClawRatBomb *, ClawRatBombContext *, ClawGenericEnemyDependency, void *);
// Supported entry returns1; its scalar EAX (void entries0) is written to result.
// Unsupported function returns0 without guessing an implementation.
uint32_t claw_rat_bomb_entry(ClawRatBomb *, ClawRatBombContext *, uint32_t function, uint32_t argument,
                             ClawGenericEnemyDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
