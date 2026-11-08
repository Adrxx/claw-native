#ifndef CLAW_APPLICATION_STATE_FACTORY_RUNTIME_H
#define CLAW_APPLICATION_STATE_FACTORY_RUNTIME_H
#include "ClawRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Native seam for the existing inlined 0x428c40 mode-5 constructor after
   successful 0x2c8 allocation. Runs the same body as the state factory;
   this is not an original entry address or a completed state transition.
   Returns 1 on completion; missing child owners set host->fault and return 0. */
uint32_t claw_application_menu_construct(uint32_t state, ClawHost *host);
#ifdef __cplusplus
}
#endif
#endif
