#ifndef CLAW_ACTOR_DESTRUCTION_H
#define CLAW_ACTOR_DESTRUCTION_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawActorDestructionGlobals {
    uint32_t holderActorToken; // Original53c9ac; may be zero.
    uint32_t heldActorToken;   // Original53c9b0.
    uint32_t emptyStringToken; // Original shared CString data identity.
} ClawActorDestructionGlobals;
// Complete bounded original entries over live token-addressed heap spans.
// Known nested destructors execute here; unknown private vtables call host.call
// with the actual slot identity. RatBomb484d90 is deliberately delegated to its
// frozen module. host.free replaces original CRT4f6428 allocator operation.
// Returns native support, original meaningful EAX separately (deleting methods
// return receiver). Void incidental EAX is not represented as gameplay output.
// fault1 means missing span/service (native safety extension, not parity claim).
uint32_t claw_actor_destruction_entry(uint32_t function, uint32_t receiver, uint32_t argument,
                                      ClawActorDestructionGlobals *, ClawSceneActorHost, uint32_t *fault,
                                      uint32_t *result);
// Select actual actor vtable+4, never assume all scene actors use5137f0.
uint32_t claw_actor_destroy(uint32_t actorToken, uint32_t deleteFlag, ClawActorDestructionGlobals *, ClawSceneActorHost,
                            uint32_t *fault);
#ifdef __cplusplus
}
#endif
#endif
