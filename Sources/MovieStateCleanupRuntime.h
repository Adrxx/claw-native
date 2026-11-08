#ifndef CLAW_MOVIE_STATE_CLEANUP_RUNTIME_H
#define CLAW_MOVIE_STATE_CLEANUP_RUNTIME_H
#include "ClawRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
/* 0x4efcd0: thiscall0 semantic void. 0x4efd00: thiscall0 boolean.
   Physical file close and array reset are required host services. */
uint32_t claw_movie_state_cleanup_entry(uint32_t, uint32_t, const uint32_t *, uint32_t, ClawHost *, uint32_t *);
#ifdef __cplusplus
}
#endif
#endif
