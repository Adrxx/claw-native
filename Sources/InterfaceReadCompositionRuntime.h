#ifndef CLAW_INTERFACE_READ_COMPOSITION_RUNTIME_H
#define CLAW_INTERFACE_READ_COMPOSITION_RUNTIME_H
#include "InterfaceFileRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
/*Composition only: all archive/IFC/memory-file bodies remain owned by the
 frozen InterfaceFileRuntime. No independently parsed IFC records or implicit
 constructor, allocation, success, exception unwinding or filename is added.*/
typedef ClawInterfaceFileContext ClawInterfaceReadContext;
typedef ClawInterfaceFileCall ClawInterfaceReadCall;
typedef ClawInterfaceFileDependency ClawInterfaceReadDependency;
typedef struct ClawInterfaceMemoryLoad {
    uint32_t graphics, bytes, length, imageResolver, trailing[3];
} ClawInterfaceMemoryLoad;
typedef struct ClawInterfaceFileLoad {
    uint32_t graphics, file, imageResolver, trailing[3];
} ClawInterfaceFileLoad;
/*Whole source4dcdf0 RET28 /4dcd10 RET24 through the frozen reader. Caller
 constructs controller first. Automatic aliases: memoryFile40, archive68,
 scratchCString4; retain borrowed bytes until the synchronous call completes.
 Dependency receives unchanged rich buffers/localMask, including4fc139's
 file/status/filename service (receiver0/mask257, buffers40 and4). EOF throw
 request4fe675(3,0) remains a stopped source prefix, never an empty menu.
 Completion and meaningful original EAX are separate; underlying fault shared.*/
uint32_t claw_interface_read_memory(uint32_t controller, const ClawInterfaceMemoryLoad *, ClawInterfaceReadContext *,
                                    ClawInterfaceReadDependency, void *, uint32_t *result);
uint32_t claw_interface_read_file(uint32_t controller, const ClawInterfaceFileLoad *, ClawInterfaceReadContext *,
                                  ClawInterfaceReadDependency, void *, uint32_t *result);
/*Raw typed composition for source constructor/tree lifecycle and already
 recovered CMemFile readers4ff79f/4ff822/4ff8a8. Coverage/fault semantics are
 exactly those of the borrowed frozen context; no new original bodies.*/
uint32_t claw_interface_read_composition_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                               uint32_t argumentCount, ClawInterfaceReadContext *,
                                               ClawInterfaceReadDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
