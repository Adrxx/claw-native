#pragma once
#include "GenericEnemy.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t token, controllerToken; // Original resource root and root+0x10 value.
} ClawGenericEnemyStateResource;
typedef struct {
    uint32_t attackerToken, attackerActor[128], playerPrivate[78];
    uint32_t strikeCounter, audioEnabled, audioPosition;
    const ClawGenericEnemyStateResource *resources;
    size_t resourceCount;
} ClawGenericEnemyStatesContext;
// Original common states/methods by function identity. Uses the frozen generic
// runtime and dependency event ABI; the extra context supplies actually read
// attacker/player/audio/global resource words. A dependency can mutate that
// extra context through its caller-owned userdata. State IDs remain resolved
// named metadata in generic context, never guessed numeric assignments.
// Return1 means supported native completion,0 unsupported/invalid input. This
// support status is distinct from original state callbacks' zero EAX returns.
uint32_t claw_generic_enemy_state_entry(ClawGenericEnemy *, ClawGenericEnemyContext *, ClawGenericEnemyStatesContext *,
                                        uint32_t function, uint32_t argument, ClawGenericEnemyDependency, void *);
// Select the process-wide native app profile before issuing enemy callbacks.
// Oracle and legacy comparison processes retain v1.0 unless explicitly selected.
void claw_generic_enemy_states_use_v13(void);
// Retained app layouts with the always-on v1.3 death-bit change selected.
uint32_t claw_generic_enemy_state_entry_v13(ClawGenericEnemy *, ClawGenericEnemyContext *, ClawGenericEnemyStatesContext *,
                                            uint32_t function, uint32_t argument, ClawGenericEnemyDependency, void *);
// Dispatch a resolved common state ID through the shared-state entry layer.
// Uses generic context's exact name/function mapping; no FSM or scheduling copy.
uint32_t claw_generic_enemy_state_dispatch(ClawGenericEnemy *, ClawGenericEnemyContext *,
                                           ClawGenericEnemyStatesContext *, int32_t state, ClawGenericEnemyDependency,
                                           void *);
#ifdef __cplusplus
}
#endif
