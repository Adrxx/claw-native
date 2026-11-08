#ifndef CLAW_IMAGE_REGISTRY_RUNTIME_H
#define CLAW_IMAGE_REGISTRY_RUNTIME_H
#include "CArrayRuntime.h"
#include "GameImageRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawImageRegistryArguments {
    uint32_t words[5], count;
} ClawImageRegistryArguments;
typedef struct ClawImageRegistryContext {
    ClawSceneActorHost scene;
    ClawCArrayContext *arrays; // Optional frozen raw CArray composition.
    ClawGameImageGlobals *images;
    ClawGameImageHost *imageHost; // Both nonnull compose supported GameImage bodies.
    uint32_t fault;               //1 missing span/service,2 bounded unsafe metadata,3 iteration/name limit.
    uint32_t eventNameBytes;      // Original ANI-decoder global543174, visible at lookup.
} ClawImageRegistryContext;
// Raw original controller/root methods. Controller513b88 +48=4cff40 recursively
// registers image groups; ANI controller513ad8 uses direct4ce0d0. A root513cf8
// +28=4ce5e0 selects FIRST numeric substring of each exact resource leaf name;
// names without digits select0. No suffix convention or REZ numeric-ID inference.
// Args are original heap tokens/scalars. Name formatting writes the original
// allocated256-byte heap buffer; resource transport/map lookup remain services.
// Return1 supported/completed,0 unsupported/fault; original EAX separately.
// Initialize fault0. Actual supported inventory is documented with verification.
uint32_t claw_image_registry_entry(uint32_t function, uint32_t receiver, ClawImageRegistryArguments,
                                   ClawImageRegistryContext *, uint32_t *result);
uint32_t claw_image_registry_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
