#ifndef CLAW_RESOURCE_ARCHIVE_LOADING_RUNTIME_H
#define CLAW_RESOURCE_ARCHIVE_LOADING_RUNTIME_H
#include "ResourceTableConstructionRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_RESOURCE_ARCHIVE_CONTROLLER_BYTES 72u
#define CLAW_RESOURCE_ARCHIVE_HEADER_BYTES 168u
typedef struct ClawResourceArchiveLoadingContext {
    ClawResourceTableConstructionContext *table;
    /*Caller-owned synchronous source header local. Its transport is the real
  168-byte read destination; no source heap allocation identity is implied.*/
    uint32_t headerToken, maximumOperations;
} ClawResourceArchiveLoadingContext;
/*Whole72-byte4b7210 ctor,4b72e0(path,readOnly,create),4b6b60(offset,length)
  recursive loading,4b6ed0 actual record reader,4b7bd0 FILEopen,
 4b7c40 FILEclose,4b7c80 FILEflush,4b74d0(closeOrCompact),4b7250 destruction.
 Frozen table/namespace/data bodies compose over the SAME raw heap/allocator.
 Dependency ABI is frozen Table rich callback. Physical4f1d90 fopen,
 4a7840 fseek,4a7260 fread,4a7ae0 fclose,4a7920 fflush/virtual retry remain
 explicit; writer4b7550 and compaction4b76b0 are elected source boundaries.
 No record synthesis, editor-creator substitution or fake boot success.
 MeaningfulEAX separately; fullopen source returns1 evenifrecursive loadfails.
 Faults live in table->fault; native guards are not original safe exits.
 Header scratch is normalized as argument0 localMask1/buffer0 only when
 transported to FILEfread; bytes and uninitialized short-read tail survive.*/
uint32_t claw_resource_archive_loading_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                             uint32_t argumentCount, ClawResourceArchiveLoadingContext *,
                                             ClawResourceTableConstructionDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
