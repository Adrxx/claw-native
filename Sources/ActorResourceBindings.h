#pragma once
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t actor[128], secondary[93];
} ClawActorResourceBindings;
typedef struct {
    uint32_t token;
    int32_t minimum, maximum, firstImageIndex;
    const uint32_t *images;
    size_t imageCount;
} ClawActorImageBinding;
typedef struct {
    uint32_t imageRegistryToken, logicRegistryToken;
    ClawActorImageBinding image;
    uint32_t metadataToken, metadataCallback, metadataFlags;
    // Original virtual destructor address/identity for secondary+0x18 resource.
    uint32_t associatedDestructor;
} ClawActorBindingContext;
typedef struct {
    uint32_t function, receiver, argument;
    const char *name;
} ClawActorBindingCall;
typedef uint32_t (*ClawActorBindingDependency)(ClawActorResourceBindings *, ClawActorBindingContext *,
                                               const ClawActorBindingCall *, void *);
// Complete original indexed/default image field updates after explicit lookup.
// Lookup4f6286 returns the image token and fills context.image. Signed IDs map
// into images[firstImageIndex...], a bounded view of original absolute-ID table.
// Return1 for completed update; return0 for native invalid-table safety rejection.
// On missing lookup, root170 clears but previous16c/174 remain, as original.
uint32_t claw_actor_bind_indexed_image(ClawActorResourceBindings *, ClawActorBindingContext *, const char *name,
                                       int32_t imageID, ClawActorBindingDependency, void *);
uint32_t claw_actor_bind_default_image(ClawActorResourceBindings *, ClawActorBindingContext *, const char *name,
                                       ClawActorBindingDependency, void *);
// Complete original4c7f20 / named4c7fa0 for generic secondary logic (actor+70).
// Constructor allocation/frees/associated destructor and named lookup are
// dependencies. Secondary flags initialize to0 even if metadataFlags nonzero.
// Existing actor70 must refer to this secondary buffer; identities must stay
// stable during dependencies. Raw pointer/vtable polymorphism is not emulated.
// Return original binder result (0/1). A zero callback leaves binding failed
// after allocation or reset stores; failure is not automatically rolled back.
uint32_t claw_actor_bind_secondary_logic(ClawActorResourceBindings *, ClawActorBindingContext *,
                                         ClawActorBindingDependency, void *);
uint32_t claw_actor_bind_secondary_logic_name(ClawActorResourceBindings *, ClawActorBindingContext *, const char *name,
                                              ClawActorBindingDependency, void *);
void claw_actor_reset_secondary_logic(ClawActorResourceBindings *, ClawActorBindingContext *,
                                      ClawActorBindingDependency, void *);
// Original4c7fe0/4c8060 contact binding at actor+78. The same93-word
// `secondary` API buffer represents the selected contact logic for this call;
// callers keep secondary/contact ownership separate. Flags initialize to0.
uint32_t claw_actor_bind_contact_logic(ClawActorResourceBindings *, ClawActorBindingContext *,
                                       ClawActorBindingDependency, void *);
uint32_t claw_actor_bind_contact_logic_name(ClawActorResourceBindings *, ClawActorBindingContext *, const char *name,
                                            ClawActorBindingDependency, void *);
#ifdef __cplusplus
}
#endif
