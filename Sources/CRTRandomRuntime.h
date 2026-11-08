#pragma once
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_CRT_THREAD_BYTES 0x74u
#define CLAW_CRT_THREAD_WORDS 29u
#define CLAW_CRT_RANDOM_SEED_WORD 5u
#define CLAW_CRT_RANDOM_LEVEL_SEED 0x1b3cfu
/* Actual original52edd8 TLS index, initiallyFFFFFFFF. Thread objects are live
   host spans, not a separate scalar RNG. The seed at+14 is shared with frozen
   WorldLootRuntime and SceneFadeRuntime; random accesses require6 words,
   initializer/cleanup require21 words, actual calloc allocates29 words. */
typedef struct ClawCRTRandomGlobals {
    uint32_t tlsIndex;
} ClawCRTRandomGlobals;
typedef struct ClawCRTRandomContext {
    ClawSceneActorHost host;
    ClawCRTRandomGlobals *globals;
    uint32_t fault;
} ClawCRTRandomContext;
typedef struct ClawCRTRandomCall {
    uint32_t function, receiver, argumentCount, arguments[2];
} ClawCRTRandomCall;
typedef uint32_t (*ClawCRTRandomDependency)(ClawCRTRandomContext *, const ClawCRTRandomCall *, void *);
void claw_crt_random_defaults(ClawCRTRandomGlobals *);
/* Whole cdecl source entries:4a3040(seed),4a3050(),4a7da0(threadToken),
   4a7dc0() getter,4a7d40() CRT TLS initialization,4a7e40(threadTokenOr0)
   cleanup. Uses actual live thread+14, composing frozen WorldLoot LCG.
   All source stores/calls are ordered, including LastError restoration.
   Services use IAT slot identities:546b0c GetLastError,546a7c TlsGetValue,
   546a84 TlsSetValue,5469c0 GetCurrentThreadId,546ab8 SetLastError,
   546a90 TlsAlloc. CRT4adf50 calloc(count,bytes),4a49b0 free(pointer),
   4a7b90 lock initialization,4a4860 fatalRuntimeError(16) are explicit.
   These physical transports may mutate live globals/heap. fatalRuntimeError
   ordinarily never returns: set context fault to stop at its reached prefix;
   returning transport is followed by original fallthrough, not fake success.
   Rich callback preferred; host.call fallback preserves all raw arguments.
   Returns1 for covered completed source,0 on unsupported/fault. Fault1 missing
   span/service,2 invalid argument count; callback fault codes are preserved.
   Result exposes original EAX; srand/initializer/cleanup are source void APIs
   with incidental EAX, while rand/getter/init have meaningful return values.
   No startup seeding or random draw occurs merely by constructing this context. */
uint32_t claw_crt_random_entry(uint32_t function, const uint32_t *arguments, uint32_t argumentCount,
                               ClawCRTRandomContext *, ClawCRTRandomDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
