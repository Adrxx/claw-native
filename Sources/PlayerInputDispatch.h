#ifndef CLAW_PLAYER_INPUT_DISPATCH_H
#define CLAW_PLAYER_INPUT_DISPATCH_H
#include "PlayerLocomotion.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t pressed;
    uint32_t invulnerabilityTimer;
    uint32_t minimumX, maximumX, minimumY, maximumY;
    uint32_t ignoreHazards, cheat;
} ClawPlayerInputContext;
// Original0x415df0 movement branches and common epilogue. High-level recovered
// helper calls remain dependency operations, so the adapter may invoke their C
// implementations with the same live state. Unknown helpers stay explicit.
// Returns1 for covered initial logic states,0 without mutations otherwise.
uint32_t claw_player_dispatch_input(ClawPlayerLocomotion *state, ClawPlayerInputContext *input,
                                    ClawPlayerLocomotionDependency dependency, void *context);
// Source415df0 common tail, shared unchanged by additive carry-state dispatch.
void claw_player_input_epilogue(ClawPlayerLocomotion *state, ClawPlayerInputContext *input,
                                ClawPlayerLocomotionDependency dependency, void *context);
// Original normal-movement dependencies needed by the dispatcher.
void claw_player_update_jump_hold(ClawPlayerLocomotion *state);
uint32_t claw_player_left_ledge(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context);
uint32_t claw_player_right_ledge(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context);
int32_t claw_player_enter_teeter(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context);
typedef struct {
    uint32_t remaining, expired, overlaySequenceToken;
} ClawPlayerPowerupContext;
void claw_player_update_powerup_timer(ClawPlayerLocomotion *state, ClawPlayerPowerupContext *powerup, uint32_t delta,
                                      ClawPlayerLocomotionDependency dependency, void *context);
#ifdef __cplusplus
}
#endif
#endif
