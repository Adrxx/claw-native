#ifndef CLAW_PLAYER_INITIALIZATION_H
#define CLAW_PLAYER_INITIALIZATION_H
#include "PlayerInputDispatch.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t defaults[78], difficulty;
    uint32_t worldWidth, worldHeight, startX, startY, checkpointX, checkpointY;
    uint32_t privateToken, cachedX, cachedY, powerupRemaining, powerupAuxiliary;
    uint32_t accumulator, accumulatorMinimum, accumulatorStep;
    uint32_t imageOffsetsAdjusted, ladderImageTokens[7], ladderImageWord24[7];
    uint32_t configurationToken, resetObjectToken;
} ClawPlayerInitializationContext;
// Original0x415ce0 resets global saved/default private state, powerup globals,
// and the original replay accumulator. Does not zero actor or physics.
void claw_player_construct_defaults(ClawPlayerLocomotion *state, ClawPlayerInitializationContext *initialization);
uint32_t claw_player_default_word(const ClawPlayerInitializationContext *initialization, uint32_t index);
void claw_player_set_default_word(ClawPlayerInitializationContext *initialization, uint32_t index, uint32_t value);
uint32_t claw_player_initialization_image_word(const ClawPlayerInitializationContext *initialization, uint32_t index);
void claw_player_set_initialization_image_word(ClawPlayerInitializationContext *initialization, uint32_t index,
                                               uint32_t token, uint32_t value);
// Original CaptainClaw0x415df0 for initial logic0 (new level) or23 (respawn),
// including its common epilogue. Returns0 without mutations otherwise.
// Actor must come from the recovered generic object loader; preserved words
// and physics constructor state remain the caller's responsibility.
uint32_t claw_player_dispatch_initialization(ClawPlayerLocomotion *state,
                                             ClawPlayerInitializationContext *initialization,
                                             ClawPlayerInputContext *input, ClawPlayerLocomotionDependency dependency,
                                             void *context);
#ifdef __cplusplus
}
#endif
#endif
