#ifndef CLAW_CARRAY_RUNTIME_H
#define CLAW_CARRAY_RUNTIME_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
// Original pointer CArray: vtable,data,size,capacity,growBy (five raw words).
// Other words are untouched. Lookup uses the shared aligned-word host ABI.
typedef struct ClawCArrayContext {
    ClawSceneActorHost scene;
    //0:4f63ec/4f6428 services.1:real wrappers, CRT4a48e0/4a49b0 services.
    //2:also compose real4a48e0/4a4900/4a4950 CRT allocation branches, keeping
    // lock9, small-block allocator, HeapAlloc and new-handler bodies explicit.
    uint32_t composeAllocator, globalNewHandler, fault;
    uint32_t crtNewMode, smallBlockThreshold, heapHandle, heapAllocFunction;
} ClawCArrayContext;
typedef struct ClawCArrayCall {
    uint32_t function, receiver, argumentCount, arguments[4];
} ClawCArrayCall;
typedef uint32_t (*ClawCArrayDependency)(ClawCArrayContext *, const ClawCArrayCall *, void *);
// Original image defaults:510020=ffffffff,540fe8=0,5312d4=480.
// Preserves host/mode/fault/heap handle and resolved HeapAlloc identity.
void claw_carray_defaults(ClawCArrayContext *);
//4f58ab ctor(noargs);4f582f SetAtGrow(index,value), which overwrites without
// shifting;4f5915 SetSize(size,growBy;ffffffff preserves growBy);
//4f63ec allocator(bytes),4f6428 free(pointer),4a4a20 memset(dst,byte,count),
//4a4a80 overlap-safe copy(dst,source,count). Cdecl helper arguments occupy
// arg0..2; thiscall array methods use receiver and arg0..1.
// CRT4a48e0(bytes),4a4900(bytes,newMode),4a4950(bytes) are also exposed.
// Return1 means recognized. Result preserves observed EAX; SetSize/free are
// void originally, so their machine result must not acquire host semantics.
// Allocator callbacks may mutate raw headers/globals; reads follow original
// boundaries. Fault1 missing span/service,2 unsafe/null/loop bounds are native
// diagnostics and do not establish safe original failure behavior.
uint32_t claw_carray_entry(uint32_t function, uint32_t receiver, uint32_t arg0, uint32_t arg1, uint32_t arg2,
                           ClawCArrayContext *, ClawCArrayDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
