#ifndef CLAW_NATIVE_LEVEL_SERVICES_H
#define CLAW_NATIVE_LEVEL_SERVICES_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Native C runtime and MFC services the Level 1 load and play use, with the
   semantics of the Level 1 tracer's stand-ins (Tests/NativeLevelOne/trace.py,
   Tests/NativeLevelOne/native_join.py, Tests/NativeMenuBase/trace.py).
   Pure functions over host memory; the app host applies them in
   ClawNativeMenuInterface/ClawNativeMenuResources. Checked by
   scripts/check-level-one-services.py. */

/* CRT rand: the original linear congruential sequence, 15-bit results. */
uint32_t claw_level_rand(uint32_t *state);

/* CRT isdigit 0x4b0d30, isspace 0x4b0d60, isprint 0x4b0d90 in the elected
   ASCII C locale. Returns 0 (refused) outside 0..127 and EOF. */
uint32_t claw_level_ctype(uint32_t function, uint32_t value, uint32_t *result);

/* MFC CRect::InflateRect(l, t, r, b) on four signed words. */
void claw_level_inflate_rect(uint32_t rect[4], uint32_t left, uint32_t top, uint32_t right, uint32_t bottom);

/* zlib uncompress of at most `available` source bytes into `capacity`
   output bytes. Returns the zlib status as an unsigned word (0 complete,
   0xfffffffb output limit before the stream end, 0xfffffffd data error)
   and the produced byte count in *written (unchanged on a data error). */
uint32_t claw_level_uncompress(uint8_t *destination, uint32_t capacity, const uint8_t *source,
                               uint32_t available, uint32_t *written);

/* CRT qsort as the tracer's deterministic adjacent insertion sort over
   one-byte elements. `compare` receives the indices (j-1, j), stores the
   comparator's EAX and returns 1, or returns 0 to stop (fault). A value in
   1..0x7fffffff swaps the pair. Returns 1 when complete. */
typedef uint32_t (*ClawLevelCompare)(void *context, uint32_t left, uint32_t right, uint32_t *value);
uint32_t claw_level_adjacent_sort(uint8_t *base, uint32_t count, ClawLevelCompare compare, void *context,
                                  uint32_t *comparisons, uint32_t *swaps);
#ifdef __cplusplus
}
#endif
#endif
