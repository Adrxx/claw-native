#ifndef CLAW_PLAYER_LOCOMOTION_H
#define CLAW_PLAYER_LOCOMOTION_H
#include "PlayerPhysics.h"
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
// Original actor/private field offsets are retained as words. Pointer fields
// are opaque tokens; only the dependency adapter may resolve them.
typedef struct ClawPlayerLocomotion {
    uint32_t actor[128], privateWords[78];
    uint32_t logicState, inputLatched, inputHeld;
    uint32_t stageDelta, animationDelta, powerup, pixelScratch;
    ClawPlayerPhysics physics;
    int32_t weaponLogicStatus;
    uint32_t weaponLogicCallback;
    uint32_t weaponDeleteCount, weaponDeleteFlags;
    uint32_t highJump, pixelScratchY, audioRegistryDisabled, audioPosition;
} ClawPlayerLocomotion;
// Dependencies are identified by original entry address. Values are portable:
// sequence selection uses the original string address, movement uses x/y/options,
// cleanup uses weapon token, animation restoration uses sequence token.
// 0x4f6286 returns the resolved sequence token. Callbacks may modify state.
typedef uint32_t (*ClawPlayerLocomotionDependency)(ClawPlayerLocomotion *state, uint32_t entry, uint32_t a, uint32_t b,
                                                   uint32_t c, void *context);
uint32_t claw_player_actor_word(const ClawPlayerLocomotion *state, uint32_t byteOffset);
void claw_player_set_actor_word(ClawPlayerLocomotion *state, uint32_t byteOffset, uint32_t value);
uint32_t claw_player_private_word(const ClawPlayerLocomotion *state, uint32_t index);
void claw_player_set_private_word(ClawPlayerLocomotion *state, uint32_t index, uint32_t value);
uint32_t claw_player_enter_stand(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_enter_walk_left(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_enter_walk_right(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency,
                                  void *context);
void claw_player_enter_jump(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_cleanup_move(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_update_walk_right(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency,
                                   void *context);
void claw_player_update_walk_left(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency,
                                  void *context);
void claw_player_update_jump(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_update_fall(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_enter_fall(ClawPlayerLocomotion *state, uint32_t skipAnimation,
                            ClawPlayerLocomotionDependency dependency, void *context);
#ifdef __cplusplus
}
#endif
#endif
