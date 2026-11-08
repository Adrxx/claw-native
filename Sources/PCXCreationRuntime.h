#ifndef CLAW_PCX_CREATION_RUNTIME_H
#define CLAW_PCX_CREATION_RUNTIME_H
#include "PCXImageRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Whole original4be810(this,[manager,data,fileLength,loadFlags]),RET16.
   Borrows the existing PCX context and composes frozen decoder/conversion and
   GameImage initialization. Source init is elected via live vtable+0c.
   Dimensions/depth/admission and odd-width checks retain their source order.
   Global541fb0 palette scratch must be supplied by the same byte lookup.
   No archive/image-controller/window or physical DD acceptance is implied. */
uint32_t claw_pcx_creation_entry(uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                                 ClawPCXImageContext *, ClawPCXImageDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
