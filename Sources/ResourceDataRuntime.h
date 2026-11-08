#ifndef CLAW_RESOURCE_DATA_RUNTIME_H
#define CLAW_RESOURCE_DATA_RUNTIME_H
#include "CArrayRuntime.h"
#include "AudioPCMTransfer.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawResourceDataContext {
    ClawSceneActorHost scene;
    ClawCArrayContext *allocator;      /* optional frozen4f63ec/4f6428 composition */
    uint32_t maximumOperations, fault; /*1 missing span/service,2 unsafe count,3 limit,4 args*/
} ClawResourceDataContext;
typedef struct ClawResourceDataCall {
    uint32_t function, receiver, argumentCount, arguments[10];
} ClawResourceDataCall;
typedef uint32_t (*ClawResourceDataDependency)(ClawResourceDataContext *, const ClawResourceDataCall *, void *);
/* Raw entry adapter composes frozen AudioPCMTransfer4b61c0/4b6230/4b7ab0.
 Owns missing96-byte resource constructor4b5ff0(10args), destructor4b6120,
 and type getter4b61b0. Borrowed resource views use actualoriginalfields.
 Scalar services retain exact source addresses:4f63ec,4f6428,4a7840(fseek),
 4a7260(fread), and current stream VT+8 retry. No refcount is synthesized.
 Return1 recognized/completed, result meaningful EAX separately; unknown/fault0.
 Setfault0 before each call; maximum0 selects100000 operations. Strings require
 a readable final containing word under aligned SceneActorHost lookup.
 Physical allocator/FILE/archive mapping ownership remains explicit. */
uint32_t claw_resource_data_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                  uint32_t argumentCount, ClawResourceDataContext *, ClawResourceDataDependency, void *,
                                  uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
