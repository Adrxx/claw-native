#pragma once
#include "ClawRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
// Compose the admitted child game routines with native, synchronous standard
// streams. The parent retains binary I/O, heap allocation and object storage.
// This is the raw virtual interface, not the profile or scene archive format.
uint32_t claw_v13_raw_child_native_entry(uint32_t function, uint32_t receiver,
    const uint32_t *arguments, uint32_t count, ClawHost *parent, uint32_t *result);
#ifdef __cplusplus
}
#endif
