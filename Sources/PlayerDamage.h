#ifndef CLAW_PLAYER_DAMAGE_H
#define CLAW_PLAYER_DAMAGE_H
#include "PlayerInputDispatch.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t attackerToken, attackerActor[128];
    uint32_t configurationToken, configurationWord764;
    uint32_t logicWord20, infiniteLives, overlayMode, overlayOffsetY;
    uint32_t windowToken, audioManagerAvailable, resolvedSoundPoolToken;
} ClawPlayerDamageContext;
uint32_t claw_player_damage_attacker_word(const ClawPlayerDamageContext *damage, uint32_t byteOffset);
void claw_player_set_damage_attacker_word(ClawPlayerDamageContext *damage, uint32_t byteOffset, uint32_t value);
// Original CaptainClawHit0x41ce80, after the external actor-hit engine has
// populated actor+74 and elected to invoke this callback. No guessed immunity
// gate is inserted here. Attacker snapshot must correspond to actor+74 token.
uint32_t claw_player_hit(ClawPlayerLocomotion *state, ClawPlayerDamageContext *damage, ClawPlayerInputContext *input,
                         ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_enter_fall_death(ClawPlayerLocomotion *state, ClawPlayerDamageContext *damage, uint32_t deathNotice,
                                  ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_enter_spike_death(ClawPlayerLocomotion *state, ClawPlayerDamageContext *damage,
                                   ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_update_hurt(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_update_fall_death(ClawPlayerLocomotion *state, ClawPlayerDamageContext *damage,
                                   ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_update_spike_death(ClawPlayerLocomotion *state, ClawPlayerDamageContext *damage,
                                    ClawPlayerLocomotionDependency dependency, void *context);
// Original0x415df0 for initial28 (epilogue only),31,5004,5005, including the
// common epilogue. Other initial states return0 without mutations.
uint32_t claw_player_dispatch_damage(ClawPlayerLocomotion *state, ClawPlayerDamageContext *damage,
                                     ClawPlayerInputContext *input, ClawPlayerLocomotionDependency dependency,
                                     void *context);
#ifdef __cplusplus
}
#endif
#endif
