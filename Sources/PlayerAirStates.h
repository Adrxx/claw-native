#ifndef CLAW_PLAYER_AIR_STATES_H
#define CLAW_PLAYER_AIR_STATES_H
#include "PlayerLocomotion.h"
#ifdef __cplusplus
extern "C" {
#endif
// Original input+4 pressed mask; held/latched masks are in locomotion state.
typedef struct {
    uint32_t pressed;
} ClawPlayerAirInput;
// 0x41bb70, logic 27. New dependency0x4207f0 samples world point(a=x,b=y).
void claw_player_update_climb(ClawPlayerLocomotion *state, const ClawPlayerAirInput *input,
                              ClawPlayerLocomotionDependency dependency, void *context);
// 0x4198d0, logic5002. Uses the same dependencies as existing locomotion.
void claw_player_update_land(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context);
#ifdef __cplusplus
}
#endif
#endif
