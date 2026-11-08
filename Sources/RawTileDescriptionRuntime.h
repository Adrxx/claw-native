#ifndef CLAW_RAW_TILE_DESCRIPTION_RUNTIME_H
#define CLAW_RAW_TILE_DESCRIPTION_RUNTIME_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawRawTileArguments {
    uint32_t words[4], count;
} ClawRawTileArguments;
// Actual vtable slots1c(type),20(point attribute),24(record advance),28..44
// (left/up/right/down transition/target scans). Returns0 for unowned slots.
uint32_t claw_raw_tile_function(uint32_t vtableToken, uint32_t slot);
// Point:args=(x,y). Transition scan:(x,y,coordinateOutToken,attributeOutToken).
// Target scan:(x,y,full32bit targetAttribute,coordinateOutToken).
// Metadata has no args. Preserves complete raw descriptor/mask/output bytes.
// WorldFile owns construction/destruction and record-advance bodies; this
// module composes them, and the proven simple/rect point forms, where applicable.
// Return1 supported/completed,0 unsupported/fault; result is original EAX.
// fault1 missing readable/writable span,2 argument/slot metadata,3 loop bound.
// Bounds faults are diagnostics, not substituted original out-of-range returns.
uint32_t claw_raw_tile_entry(uint32_t function, uint32_t descriptionToken, ClawRawTileArguments, ClawSceneActorHost,
                             uint32_t *fault, uint32_t *result);
uint32_t claw_raw_tile_virtual(uint32_t descriptionToken, uint32_t slot, ClawRawTileArguments, ClawSceneActorHost,
                               uint32_t *fault, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
