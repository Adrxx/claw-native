#ifndef CLAW_IMAGE_CONTROLLER_LOADING_RUNTIME_H
#define CLAW_IMAGE_CONTROLLER_LOADING_RUNTIME_H
#include "ImageRegistryRuntime.h"
#include "ResourceArchiveLoadingRuntime.h"
#include "AmbientAudioBackendRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawImageControllerLoadingContext {
    ClawSceneActorHost scene;
    ClawImageRegistryContext *registry;
    ClawResourceNamespaceContext *names;
    ClawResourceDataContext *data;
    ClawResourceArchiveLoadingContext *archive;
    ClawCArrayContext *arrays;
    ClawAmbientAudioBackendContext *pools;
    uint32_t maximumOperations, fault;
} ClawImageControllerLoadingContext;
typedef struct ClawImageControllerLoadingCall {
    uint32_t function, receiver, argumentCount, arguments[10], localMask, bufferCount;
    void *buffers[2];
    uint32_t bufferBytes[2];
} ClawImageControllerLoadingCall;
typedef uint32_t (*ClawImageControllerLoadingDependency)(ClawImageControllerLoadingContext *,
                                                         const ClawImageControllerLoadingCall *, void *);
/* Exact original28-byte CString/value map:4f6286(name,outCell) returns BOOL
 and leaves missed output untouched;4f62a8(name) returns writable value slot;
4f5db6(name) removes; helpers4f5d5c(name,hashCell),4f615b(buckets,allocate),
4f6226(),4f5d33(association). Ctor4f6118 and clear4f61a1 remain frozen owners.
 Optional borrowed contexts compose frozen registry/resource/allocator/pool
 bodies on SAME scene heap. The registry's existing one-arg lookup adaptation
 is translated here into the actual original dictionary; public entry retains
 true two-arg BOOL/output-cell ABI. CString assignment/destruction/comparison
 and uncomposed physical source services remain addressed rich dependencies.
 Return1 completed/supported, source EAX separately. Fault1 span/service,
2 unsafe/ABI,3 native traversal guard; initializefault0. Contexts are borrowed
 synchronous views and must not be used concurrently during composition. */
uint32_t claw_image_controller_loading_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                             uint32_t argumentCount, ClawImageControllerLoadingContext *,
                                             ClawImageControllerLoadingDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
