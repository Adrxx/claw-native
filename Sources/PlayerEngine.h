#ifndef CLAW_PLAYER_ENGINE_H
#define CLAW_PLAYER_ENGINE_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t left, top, right, bottom;
} ClawPlayerRect;
typedef struct {
    uint32_t renderFlags;
    ClawPlayerRect moveRect, hitRect, attackRect;
} ClawPlayerBody;
typedef struct {
    uint32_t facing, idleTimer;
} ClawPlayerDirection;
void claw_player_face_left(ClawPlayerBody *body, ClawPlayerDirection *direction);
void claw_player_face_right(ClawPlayerBody *body, ClawPlayerDirection *direction);
#ifdef __cplusplus
}
#endif
#endif
