#ifndef CLAW_RESOURCE_NAMESPACE_RUNTIME_H
#define CLAW_RESOURCE_NAMESPACE_RUNTIME_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawResourceNamespaceContext {
    ClawSceneActorHost scene;
    uint32_t maximumOperations, fault; /*1 span/service,2 original unsafe local copy,3 limit,4 args*/
} ClawResourceNamespaceContext;
typedef struct ClawResourceNamespaceCall {
    uint32_t function, receiver, argumentCount, arguments[4], localMask, bufferCount;
    const void *buffers[2];
    uint32_t bufferBytes[2];
} ClawResourceNamespaceCall;
typedef uint32_t (*ClawResourceNamespaceDependency)(ClawResourceNamespaceContext *, const ClawResourceNamespaceCall *,
                                                    void *);
/* Raw original tokens, original meaningful EAX through result. Return1 completed,
 0 unsupported/fault. Defaults: maximumOperations0 selects100000. ASCII CRT
 4a3cf0 is composed when raw540e88==0; nonzero locale delegates that exact
 cdecl comparison (local pointers normalized to0 and synchronous buffers).
 Lookup is aligned-word-only; byte strings are read through containing words.
 REZ parsing, table construction, payload acquisition/release stay caller-owned.
 Owns root/path/type/name/hash-bucket lookup and directory/type/file iteration;
 no synthesized alias or default folder. See docs for exact inventory/layout. */
uint32_t claw_resource_namespace_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                       uint32_t argumentCount, ClawResourceNamespaceContext *,
                                       ClawResourceNamespaceDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
