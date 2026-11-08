#ifndef CLAW_PLAYER_POSE_STATES_H
#define CLAW_PLAYER_POSE_STATES_H
#include "PlayerLocomotion.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t inputPressed;
} ClawPlayerPoseContext;
// Original 0x419fd0. Animation marker return values 1..5 drive the attack
// branches. Attack creation/throw and animation seek remain adapter effects.
void claw_player_update_duck(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context,
                             const ClawPlayerPoseContext *pose);
// Original 0x41a490. Dispatcher jump handling is outside this callback.
void claw_player_update_lookup(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context);
#ifdef __cplusplus
}
#endif
#endif
