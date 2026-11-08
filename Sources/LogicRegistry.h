#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    const char *name;
    uint32_t registrationOrdinal; // Stable host identity, one-based; not x86 heap address.
    uint32_t originalNameAddress;
    uint32_t callback, flags;
} ClawLogicRegistryEntry;
// Original-v1.0 built-in bindings observed in registration entry0x401000.
// Callbacks are x86 identities only; never invoke them as native function pointers.
uint32_t claw_logic_registry_count(void);
const ClawLogicRegistryEntry *claw_logic_registry_at(uint32_t index); // Zero-based.
// Exact byte-sensitive NUL-terminated lookup. Unknown names return null.
// Null input/out-of-range index safely return null (native safety extension).
const ClawLogicRegistryEntry *claw_logic_registry_find(const char *name);
#ifdef __cplusplus
}
#endif
