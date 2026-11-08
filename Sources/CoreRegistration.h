#ifndef CLAW_CORE_REGISTRATION_H
#define CLAW_CORE_REGISTRATION_H
#include "SceneActorRuntime.h"
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
// Exact contiguous original globals 544b14..544d1b: diagnostics, four handler
// objects, 32 three-word registration rows, and count at final word129.
typedef struct ClawCoreRegistrationGlobals {
    uint32_t words[130];
    uint32_t defaultBitCount; // Original533470, image32; may be configured.
    uint32_t errorLocation;   // Supplies4dc680 return when a diagnostic occurs.
    // Explicit CRT allocator profile used by4a49b0. Original545fc4 heap handle
    // and resolved HeapFree IAT546964 function identity, plus two scratch cells.
    uint32_t heapHandle, heapFreeFunction, freeScratchTokens[2];
} ClawCoreRegistrationGlobals;
// Copies only the verified image default bit count; preserves live raw globals
// and host allocator identities. Does not manufacture registration entries.
void claw_core_registration_defaults(ClawCoreRegistrationGlobals *);
// Actual five core-handler CRT wrappers in PE52222c..52223c order. Original
// constructors preserve count/rows, handler search index and upper status word.
uint32_t claw_core_registration_initialize(ClawCoreRegistrationGlobals *, ClawSceneActorHost, uint32_t *fault);
// 4dc3a0 handler constructor;4dc3d0 lookup;4dc560 register/update/unregister;
// 4db620 base constructor;4db6c0 base destructor;4dc180/default bitset,
// 4dc7b0 explicit bitset allocation;4dbe10 empty/null-string constructor paths;
// Five CRT handler wrappers;4f6428 and4a49b0 free wrappers.
// Unknown function/nonempty parser returns0 before mutation. Result is original
// meaningful EAX only; base/bitset constructors return receiver; void bodies return0.
// Fault 1 missing span/service,2 invalid represented count/index are native safety
// extensions. Host.call retains lock9, small-block lookup/release, HeapFree and
// diagnostic bodies; host.allocate supplies the actual allocation boundary.
uint32_t claw_core_registration_entry(uint32_t function, uint32_t receiver, uint32_t argument0, uint32_t argument1,
                                      ClawCoreRegistrationGlobals *, ClawSceneActorHost, uint32_t *fault,
                                      uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
