#pragma once
#include "GenericEnemyStates.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef ClawGenericEnemy ClawOfficer;
typedef struct {
    ClawGenericEnemyContext generic;
    ClawGenericEnemyStatesContext sharedStates;
    // Original allocation470bytes =284 words. Frozen generic runtime represents
    // words0...263; this tail represents words264...283, never portable padding.
    // Native heap adapters concatenate/split both spans at every dependency.
    uint32_t privateTail[20];
    float damageScale, healthScale, rangeScale;
    uint32_t difficulty, sequenceRegistryToken, audioManagerToken;
    uint32_t audioManagerAvailable, masterVolume;
    const ClawGenericEnemyState *patrolStates;
    size_t patrolStateCount;
    const ClawGenericEnemyState *officerStates;
    size_t officerStateCount;
    uint32_t effectToken, effectActor[128], effectPrimary[93], effectPrivate[92];
    uint32_t otherActorToken, otherActor[128], otherPrimary[93];
    uint32_t platformPrimary[93];
    // Portable fault/scope status, no corresponding original field.
    uint32_t fault;
} ClawOfficerContext;
void claw_officer_context_defaults(ClawOfficerContext *);
uint32_t claw_officer_construct(ClawOfficer *, ClawOfficerContext *, ClawGenericEnemyDependency, void *);
uint32_t claw_officer_tick(ClawOfficer *, ClawOfficerContext *, ClawGenericEnemyDependency, void *);
// Supported original method result is returned separately from native scope
// status. Unknown entries return0 without a fabricated common-body substitute.
uint32_t claw_officer_entry(ClawOfficer *, ClawOfficerContext *, uint32_t function, uint32_t argument,
                            ClawGenericEnemyDependency, void *, uint32_t *result);
uint32_t claw_officer_private_word(const ClawOfficer *, const ClawOfficerContext *, uint32_t byteOffset);
void claw_officer_set_private_word(ClawOfficer *, ClawOfficerContext *, uint32_t byteOffset, uint32_t value);
#ifdef __cplusplus
}
#endif
