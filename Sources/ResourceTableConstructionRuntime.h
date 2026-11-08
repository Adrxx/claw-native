#ifndef CLAW_RESOURCE_TABLE_CONSTRUCTION_RUNTIME_H
#define CLAW_RESOURCE_TABLE_CONSTRUCTION_RUNTIME_H
#include "ResourceDataRuntime.h"
#include "ResourceNamespaceRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_RESOURCE_FOLDER_BYTES 76u
#define CLAW_RESOURCE_TYPE_BYTES 44u
#define CLAW_RESOURCE_MAP_BYTES 8u
#define CLAW_RESOURCE_BUCKET_BYTES 16u
#define CLAW_RESOURCE_ITERATOR_BYTES 24u
typedef struct ClawResourceTableConstructionContext {
    ClawSceneActorHost scene;
    ClawCArrayContext *allocator;
    uint32_t maximumOperations, fault;
    /* Optional exact byte spans for source folder-name copying. Frozen resource
    and namespace APIs still require readable containing words for strings. */
    void *byteContext;
    uint8_t *(*bytes)(void *, uint32_t token, uint32_t byteCount);
} ClawResourceTableConstructionContext;
typedef struct ClawResourceTableConstructionCall {
    uint32_t function, receiver, argumentCount, arguments[10];
    /* Bit i denotes a synchronous local argument i; its argument token is0 and
    buffers hold exact bytes.4a3b10 time has one4-byte local, initialized with
    source ECX. Namespace locale calls can expose two borrowed name buffers. */
    uint32_t localMask, bufferCount;
    void *buffers[2];
    uint32_t bufferBytes[2];
} ClawResourceTableConstructionCall;
typedef uint32_t (*ClawResourceTableConstructionDependency)(ClawResourceTableConstructionContext *,
                                                            const ClawResourceTableConstructionCall *, void *);
/* Whole constructors4b6600(6args),4b64b0(tag), map4d53a0(count), bucket4d5410;
   creators4b69a0(name),4b7170(type),4b6a60(id,name,type), insertion/removal,
   recursive folder/type destruction and required hashing/ID/time wrappers.
   Embedded iterators are borrowed class interiors, not separately allocated
   nodes. Buckets prepend; allocation is4+16*count, table pointer allocation+4.
   Namespace/ResourceData/Ambient list bodies are composed, not duplicated.
   Physical CRT time/allocator/archive I/O and nonnormal locale remain exact
   addressed services. Full REZ archive boot is not claimed.
   Returns1 recognized/completed, result meaningful EAX separately. Unknown
   leaves result unchanged. Setfault0 before call. Fault1 missing span/service,
   2 unchecked/ABI domain,3 operation limit,4 unsupported arity. */
uint32_t claw_resource_table_construction_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                                uint32_t argumentCount, ClawResourceTableConstructionContext *,
                                                ClawResourceTableConstructionDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
