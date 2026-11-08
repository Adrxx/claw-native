#ifndef CLAW_WORLD_FILE_RUNTIME_H
#define CLAW_WORLD_FILE_RUNTIME_H
#include "WorldPlaneRuntime.h"
#include "CArrayRuntime.h"
#include "SpatialGridRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawWorldFileArguments {
    uint32_t words[4], count;
} ClawWorldFileArguments;
typedef struct ClawWorldFileContext {
    ClawSceneActorHost scene;
    // Optional frozen CArray runtime context; null exposes metadata calls as
    // explicit services. Its caller-owned allocator/CRT profile is preserved.
    ClawCArrayContext *arrays;
    // Nonzero composes frozen 4d1620 grid construction; its 4d17e0 record
    // creation callback remains an exact service, not invented object logic.
    uint32_t composeSpatial, fault;
} ClawWorldFileContext;
typedef struct ClawWorldFileCall {
    uint32_t function, receiver, arguments[4], argumentCount;
    const char *name; // Plane registry temporary ANSI name, synchronous only.
    //4d5fe0 uncompress: adapted stack output-count pointer, argument1=0.
    uint32_t *size;
    // File wrapper's adapted four-word local CFile object. Receiver0 denotes
    // its native stack identity; file methods mutate/read this span.
    uint32_t *temporary;
} ClawWorldFileCall;
typedef uint32_t (*ClawWorldFileDependency)(ClawWorldFileContext *, const ClawWorldFileCall *, void *);
// Original raw4cb200(world,[WWD]), decompression/header wrapper4cd660,
// lifecycle/default/file wrapper and tile-description entries are enumerated
// in the final documented scope. Plane/Camera/CArray/Spatial bodies compose
// frozen modules. Codec/file/resource/platform services retain original names.
// Result preserves meaningful original return; void incidental EAX excluded.
// Return1 supported/completed;0 unsupported/fault. Context.fault1 missing graph
// or service,2 bounded unsafe/unsupported metadata. Initialize fault to zero.
uint32_t claw_world_file_entry(uint32_t function, uint32_t receiver, ClawWorldFileArguments, ClawWorldFileContext *,
                               ClawWorldFileDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
