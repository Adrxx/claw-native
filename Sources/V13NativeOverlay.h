#pragma once
#include "ClawRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
// App-only adapters retain established native layouts and select the reviewed
// always-on v1.3 changes. They do not change the v1.0 oracle exports.
uint32_t claw_v13_native_overlay_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                       uint32_t argumentCount, ClawHost *host, uint32_t *result);
uint32_t claw_v13_enemy_death_compat_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                         uint32_t argumentCount, ClawHost *host, uint32_t *result);
#ifdef __cplusplus
}
#endif
