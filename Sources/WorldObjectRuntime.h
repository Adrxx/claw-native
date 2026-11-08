#pragma once
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t actor[128], logic[93];
} ClawWorldObjectRuntime;
typedef struct {
    uint32_t sceneToken, actorToken, logicToken, sceneDefaultType;
    int32_t worldWidth, worldHeight;
    uint32_t registryToken, layerTokens[3];
    // Lookup adapter returns entryToken and supplies entryCallback/entryFlags.
    // The common initializer binds this callback; it does not invoke it.
    uint32_t entryToken, entryCallback, entryFlags;
} ClawWorldObjectContext;
typedef struct {
    uint32_t function, receiver, arguments[4], argumentCount;
    const char *text; // Optional bounded, temporary NUL-terminated string.
} ClawWorldObjectCall;
typedef uint32_t (*ClawWorldObjectDependency)(ClawWorldObjectRuntime *, ClawWorldObjectContext *,
                                              const ClawWorldObjectCall *, void *);
typedef struct {
    uint32_t consumed, created;
} ClawWorldObjectInfo;
// Whole 71-word WWD object record followed by its four byte-length strings.
// Actor/logic caller seeds are preserved except exact recovered stores. Tokens
// are original-profile opaque 32-bit identities, never host pointer casts.
// Return original consumed byte count, or 0 on init/parse rejection. Info records
// whether a successful generic actor was registered; destroyed/skipped objects
// can consume input while created=0. Missing registry/resource/destruction and
// spatial insertion are explicit dependencies, not inferred gameplay logic.
// Native safety validates strings <=1023 and complete input before mutation.
uint32_t claw_world_object_load(const uint8_t *record, size_t length, ClawWorldObjectRuntime *runtime,
                                ClawWorldObjectContext *context, ClawWorldObjectDependency dependency, void *user,
                                ClawWorldObjectInfo *info);
// Common generic actor construction/initialization, useful for the separate
// player startup path. complete original 4c98c0-derived animation actor stores,
// and complete4c9d40/4c7df0/4d5800/4c8160 initialization with supplied entry.
void claw_world_object_construct(ClawWorldObjectRuntime *, const ClawWorldObjectContext *, uint32_t id);
uint32_t claw_world_object_initialize(ClawWorldObjectRuntime *, const ClawWorldObjectContext *, uint32_t x, uint32_t y,
                                      uint32_t z);
#ifdef __cplusplus
}
#endif
