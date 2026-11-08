#ifndef CLAW_PCX_IMAGE_RUNTIME_H
#define CLAW_PCX_IMAGE_RUNTIME_H
#include "GameImageRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef uint8_t *(*ClawPCXImageByteLookup)(void *, uint32_t, uint32_t);
typedef struct ClawPCXImageContext {
    ClawSceneActorHost scene;
    void *byteContext;
    ClawPCXImageByteLookup bytes;
    ClawGameImageGlobals *image;
    uint32_t composeImage, maximumOperations, fault;
} ClawPCXImageContext;
typedef struct ClawPCXImageCall {
    uint32_t function, receiver, argumentCount, arguments[8];
    //Original GameImage stack spans, synchronous borrowed views. Zero arguments
    //represent locals; ordinary tokens remain raw. No PCX header is normalized.
    uint32_t *destination;
    uint32_t *source;
} ClawPCXImageCall;
typedef uint32_t (*ClawPCXImageDependency)(ClawPCXImageContext *, const ClawPCXImageCall *, void *);
//Whole4bebc0(surface,[graphicsManager,data,byteLength]), original RET12.
//Other elected raw entries and limits are inventoried in docs at freeze.
//A byte-exact lookup is required for exact-sized inputs/destinations; it may
//return overlapping views, preserving source run and alias behavior. Otherwise
//scene.lookup is used at aligned word boundaries and must cover those words.
//composeImage elects frozen4b9730/4bb0e0 using the supplied image globals.
//Source global palette541bb0 and manager+478/+878 remain caller-owned spans.
//Return1 means supported body completed; original EAX is result. Native fault
//1 missing span/service,2 unsupported ABI,3 operation bound is not source EAX.
uint32_t claw_pcx_image_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                              ClawPCXImageContext *, ClawPCXImageDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
