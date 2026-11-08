#pragma once
#include "ClawRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
// v1.3 raw-object serialization interface (producers 0x4c7930 and 0x4d6590).
// The receiver is a raw-layout actor or logic record in the parent's memory.
// The entry composes the admitted lifecycle producer, field I/O, reverse
// lookup, LogicBump setters and enemy child serializers with native stream,
// CString and map services. The parent supplies the binary stream, the
// allocator (0x4fcaea/0x4fcb13) and the lifecycle callback. The original has
// no shipped caller; this exposes the interface and does not add a save format.
uint32_t claw_v13_raw_object_entry(uint32_t function, uint32_t receiver,
    const uint32_t *arguments, uint32_t count, ClawHost *parent, uint32_t *result);
#ifdef __cplusplus
}
#endif
