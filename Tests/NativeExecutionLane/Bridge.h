#include "CRTRandomRuntime.h"
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif
typedef struct LaneBorrowedCall {
    uint32_t arguments[40];
    uint64_t localMask;
    uint8_t *outer;
    uint8_t *inner;
    uint8_t *alias;
    uint32_t outerBytes;
    uint32_t innerBytes;
} LaneBorrowedCall;
typedef int32_t (*LaneBorrowCallback)(void *, LaneBorrowedCall *);
uint32_t lane_borrow_probe(void *, LaneBorrowCallback, int32_t);

#ifdef __cplusplus
}
#endif
