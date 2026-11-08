#ifndef CLAW_GAME_IMAGE_RUNTIME_H
#define CLAW_GAME_IMAGE_RUNTIME_H
#include "SceneActorRuntime.h"
#include "SpriteGeometry.h"
#include "ClawRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawGameImageArguments {
    uint32_t words[8], count;
} ClawGameImageArguments;
typedef struct ClawGameImageGlobals {
    uint32_t animationDelta;       // 5430c4
    uint32_t directDrawFX[25];     // 543108: flip word at index 1
    uint32_t surfaceLoadFlags;     // 54316c
    uint32_t surfaceColorKey;      // 543170, original eight-bit mode uses zero
    uint32_t compressedEffect[4];  // 5430b0/b4/b8/bc
    uint32_t embeddedPalette[256]; // 5427b0, packed RGB bytes from embedded PID palette
} ClawGameImageGlobals;
typedef struct ClawGameImageCall {
    uint32_t function, receiver, arguments[8], argumentCount;
    // Writable adapted stack rectangles/pairs. Their original stack tokens in
    // arguments are zero; heap pointers remain exact tokens. CopyRect uses
    // function 546d58 (original import-slot identity), destination/source here.
    // Graphics 4b9d80 uses source; 4b9ce0/4bffa0 use both spans. The color-key
    // service exposes its two-word pair through source. Null otherwise.
    uint32_t *destination, *source;
} ClawGameImageCall;
typedef uint32_t (*ClawGameImageService)(void *, ClawGameImageCall);
typedef struct ClawGameImageHost {
    ClawSceneActorHost heap;
    void *serviceContext;
    ClawGameImageService service;
} ClawGameImageHost;
// Raw original entry dispatch, receiver is an original 32-bit object token.
// 4d2890(image,[actor,target]); loader/factory inventory is documented with
// the final verified scope. No implicit parent, clip, surface or image IDs.
// Return is native supported/completed diagnostic, not void-entry EAX parity.
// Original value-returning entries write result. Fault 1 missing graph/service,
// 2 bounded unsupported/safety path. Initialize fault to zero; null allowed.
uint32_t claw_game_image_entry(uint32_t function, uint32_t receiver, ClawGameImageArguments, ClawGameImageGlobals *,
                               ClawGameImageHost, uint32_t *fault, uint32_t *result);
// Canonical raw 0x4d32e0, thiscall2(actor,target), semantic void. Unlike the
// legacy dispatcher, this always selects unflipped compressed drawing. Local
// coordinate/rectangle arguments retain their actual original stack tokens.
// Projection, CopyRect and the compressed dispatcher are explicit dependencies.
// Defined in GameImageRawRuntime.cpp and owned by game_image_raw.
// Source-only: this export is not yet elected by the native display.
uint32_t claw_game_image_raw_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                   uint32_t argumentCount, ClawHost *host, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
