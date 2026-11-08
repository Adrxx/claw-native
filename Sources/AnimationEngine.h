#ifndef CLAW_ANIMATION_ENGINE_H
#define CLAW_ANIMATION_ENGINE_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
// Portable fields recovered from original v1.0 runtime records. No x86 pointers.
typedef struct {
    uint32_t flags, imageCommand, controlCommand, movementCommand;
    uint32_t parameter, duration, code, dx, dy, event;
} ClawAnimationRecord;
typedef struct {
    int32_t recordIndex;
    uint32_t remaining, timed, stopped, code, previousCode;
    float rate;
    uint32_t hasSequence;
} ClawAnimationState;
typedef struct {
    uint32_t imageID, imageToken, flags, x, y, moveX, moveY;
} ClawAnimationActor;
typedef struct {
    uint32_t event, position, spatial, dispatched;
} ClawAnimationEvent;
// Decode a 20-byte ANI record plus an optional null-terminated event name.
// Returns consumed bytes, or zero for a truncated record. Event lookup is external.
uint32_t claw_animation_decode_record(const uint8_t *bytes, uint32_t size, uint32_t resolvedEvent,
                                      ClawAnimationRecord *record, uint32_t *eventNameLength);
uint32_t claw_animation_update(ClawAnimationState *state, ClawAnimationActor *actor, const ClawAnimationRecord *records,
                               uint32_t recordCount, const uint32_t *imageTokens, int32_t firstImage, int32_t lastImage,
                               uint32_t delta, uint32_t globalAudioPosition, ClawAnimationEvent *event);
#ifdef __cplusplus
}
#endif
#endif
