#ifndef CLAW_PLAYER_STANDING_H
#define CLAW_PLAYER_STANDING_H
#include "PlayerLocomotion.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t inputPressed;        // input manager +4
    uint32_t randomState;         // original CRT thread state +0x14, default seed 1
    double liftedWeaponVelocityX; // lifted weapon physics +0x50
} ClawPlayerStandingContext;
// Complete 0x419030 control flow. Movement/animation/resources/attack/throw
// dependencies use the existing address-keyed adapter; animation update's
// return is significant (1 skips lift movement, 99 requests idle speech).
void claw_player_update_stand(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context,
                              ClawPlayerStandingContext *standing);
// Alternate standing/ledge callback 0x419c80. 0x4cd1c0 dependency receives
// the signed x-offset as argument a and returns original support predicate.
void claw_player_update_stand_edge(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency,
                                   void *context);
#ifdef __cplusplus
}
#endif
#endif
