#ifndef CLAW_NATIVE_MENU_RESOURCES_H
#define CLAW_NATIVE_MENU_RESOURCES_H
#include "ClawRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Finite admitted resource graph; zero with no fault means unowned. */
uint32_t claw_native_menu_resource_entry(uint32_t, uint32_t, const uint32_t *, uint32_t, ClawHost *, uint32_t *);
/* Reviewed original bodies that ignore extra caller-popped stack words. */
uint32_t claw_native_menu_argument_count(uint32_t function, uint32_t count);
/* Native byte-string searches; readable NUL-terminated storage, at most 1 MiB. */
uint32_t claw_native_menu_byte_search(ClawHost *, uint32_t token, uint32_t value,
                                     uint32_t last, uint32_t *out);
uint32_t claw_native_menu_substring(ClawHost *, uint32_t token, uint32_t needle, uint32_t *out);
#ifdef __cplusplus
}
#endif
#endif
