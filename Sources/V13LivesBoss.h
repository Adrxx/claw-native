#pragma once
#include "ClawRuntime.h"
#include "PlayerInitialization.h"
#include "PlayerHUDRuntime.h"
#include "GenericEnemyStates.h"
#include <stdlib.h>
#include <string.h>
#ifdef __cplusplus
extern "C" {
#endif
// App composition only. Original module exports remain profile-pinned.
static inline uint32_t claw_native_v13_enabled(void) {
    const char *version = getenv("CLAW_GAME_VERSION");
    return !version || strcmp(version, "1.0") != 0;
}
static inline uint32_t claw_native_generic_enemy_state_entry(ClawGenericEnemy *state,
    ClawGenericEnemyContext *context, ClawGenericEnemyStatesContext *common,
    uint32_t function, uint32_t argument, ClawGenericEnemyDependency dependency, void *user) {
    return claw_native_v13_enabled()
        ? claw_generic_enemy_state_entry_v13(state, context, common, function, argument, dependency, user)
        : claw_generic_enemy_state_entry(state, context, common, function, argument, dependency, user);
}
uint32_t claw_v13_starting_lives(uint32_t easy);
uint32_t claw_v13_next_life_threshold(uint32_t score);
uint32_t claw_v13_boss_damage(uint32_t site, uint32_t supplied, uint32_t zero);
// Native composition selector; canonical entries retain their pinned profiles.
uint32_t claw_v13_lives_boss_enabled(void);
void claw_v13_player_construct_defaults(ClawPlayerLocomotion *, ClawPlayerInitializationContext *);
uint32_t claw_v13_lives_boss_compat_entry(uint32_t, uint32_t, const uint32_t *, uint32_t, ClawHost *, uint32_t *);
uint32_t claw_v13_player_startup_compat_entry(uint32_t, uint32_t, const uint32_t *, uint32_t, ClawHost *, uint32_t *);
uint32_t claw_v13_score_compat_entry(uint32_t, uint32_t, const uint32_t *, uint32_t, ClawHost *, uint32_t *);
uint32_t claw_v13_player_hud_entry(uint32_t, uint32_t, const uint32_t *, uint32_t, ClawPlayerHUDContext *, ClawPlayerHUDDependency, void *, uint32_t *);
#ifdef __cplusplus
}
#endif
