#pragma once
#include "GenericEnemy.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef ClawGenericEnemy ClawRat;
typedef struct {
    ClawGenericEnemyContext generic;
    uint32_t playerPrivate[78], attackerToken, attackerActor[128];
    float damageScale, healthScale, rangeScale;
    int32_t imageMinimum;
    uint32_t imageHeader[16], soundPoolToken, audioManagerAvailable, masterVolume;
    uint32_t projectileToken, projectileActor[128], projectilePrimary[93], projectileEnemy[264];
    // Original scene animation dictionary+10/object manager, and created
    // projectile primary+18 identity. Keep all resource identities 32-bit.
    uint32_t sequenceRegistryToken, objectManagerToken, projectileEnemyToken;
    uint32_t projectileActivateFunction, projectileVisualActor[128];
    // Portable scope/allocation fault reporting; no corresponding original word.
    uint32_t fault;
} ClawRatContext;
// Copies hash-pinned original scale globals1.0 and Rat's45-slot vtable profile.
// Preserves caller tokens, snapshots, registry and resource bindings.
void claw_rat_context_defaults(ClawRatContext *);
// Original47c910 includes the recovered common4332f0 constructor. A successful
// original allocation is required; returned0 reports an explicit native scope
// or allocation failure rather than guessing the missing behavior.
uint32_t claw_rat_construct(ClawRat *, ClawRatContext *, ClawGenericEnemyDependency, void *);
// Whole registered Rat47c850 wrapper. Shared movement/dispatch runs through
// GenericEnemy and Rat overrides; resource/object bodies stay dependencies.
uint32_t claw_rat_tick(ClawRat *, ClawRatContext *, ClawGenericEnemyDependency, void *);
// Execute a supported Rat method by verified original entry. Returns1 when
// covered, with original scalar result in result (void entries produce0);
// 0 leaves an unknown entry
// untouched. Rat-specific methods are available for integration dispatch.
uint32_t claw_rat_entry(ClawRat *, ClawRatContext *, uint32_t function, uint32_t argument, ClawGenericEnemyDependency,
                        void *, uint32_t *result);
uint32_t claw_rat_actor_word(const ClawRat *, uint32_t byteOffset);
void claw_rat_set_actor_word(ClawRat *, uint32_t byteOffset, uint32_t value);
uint32_t claw_rat_enemy_word(const ClawRat *, uint32_t byteOffset);
void claw_rat_set_enemy_word(ClawRat *, uint32_t byteOffset, uint32_t value);
#ifdef __cplusplus
}
#endif
