#ifndef CLAW_PLAYER_ATTACK_INPUT_H
#define CLAW_PLAYER_ATTACK_INPUT_H
#include "PlayerLocomotion.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t pressed, difficulty, damage100, damage0;
    // 0x41d750 returns signed distance and fills targetToken/targetActor through
    // the adapter. 0x4c8da0 returns projectileToken and fills projectileActor.
    uint32_t targetToken, targetActor[128];
    uint32_t projectileToken, projectileActor[128], projectileLogicRepeat;
    uint32_t spawnX, spawnY, spawnZ, spawnName, spawnFlags;
} ClawPlayerAttackContext;
typedef struct {
    uint32_t token, actor[128];
} ClawPlayerAttackCandidate;
int32_t claw_player_nearest_attack_target(ClawPlayerLocomotion *state, ClawPlayerAttackContext *attack,
                                          const ClawPlayerAttackCandidate *candidates, uint32_t count);
uint32_t claw_player_select_attack(ClawPlayerLocomotion *state, ClawPlayerAttackContext *attack,
                                   ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_select_weapon_attack(ClawPlayerLocomotion *state, ClawPlayerAttackContext *attack,
                                      ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_start_attack(ClawPlayerLocomotion *state, ClawPlayerAttackContext *attack, uint32_t code,
                              ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_update_attack(ClawPlayerLocomotion *state, ClawPlayerAttackContext *attack,
                               ClawPlayerLocomotionDependency dependency, void *context);
uint32_t claw_player_can_lift(ClawPlayerLocomotion *state, const ClawPlayerAttackContext *attack);
uint32_t claw_player_attack_random_range(ClawPlayerLocomotion *state, uint32_t minimum, uint32_t maximum,
                                         ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_enter_climb(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency, void *context);
void claw_player_enter_attack_stand(ClawPlayerLocomotion *state, ClawPlayerLocomotionDependency dependency,
                                    void *context);
#ifdef __cplusplus
}
#endif
#endif
