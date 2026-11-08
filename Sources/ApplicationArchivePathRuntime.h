#ifndef CLAW_APPLICATION_ARCHIVE_PATH_RUNTIME_H
#define CLAW_APPLICATION_ARCHIVE_PATH_RUNTIME_H
#include "CStringAssignmentRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_APPLICATION_ARCHIVE_PATH_AUTOMATIC_BYTES 268u
#define CLAW_APPLICATION_ARCHIVE_PATH_OPEN_FILE_BYTES 136u
typedef struct ClawApplicationArchivePathContext {
    ClawSceneActorHost scene;
    /*Borrowed frozen CStringAssignment/PlayerFadeBlend/ActorDestruction owners.
   Null elects their exact addressed services; no fabricated strings.*/
    ClawCStringAssignmentContext *strings;
    /*Source automatics: directory256 then three4-byte CString cells.
   Source48c190 OpenFile's separate136-byte automatic OFSTRUCT.*/
    uint32_t automaticToken, openFileToken, maximumOperations, fault;
    void *byteContext;
    uint8_t *(*bytes)(void *, uint32_t token, uint32_t byteCount);
} ClawApplicationArchivePathContext;
typedef struct ClawApplicationArchivePathCall {
    uint32_t function, receiver, argumentCount, arguments[8], localMask, bufferCount;
    void *buffers[3];
    uint32_t bufferBytes[3];
    const char *name;
} ClawApplicationArchivePathCall;
typedef uint32_t (*ClawApplicationArchivePathDependency)(ClawApplicationArchivePathContext *,
                                                         const ClawApplicationArchivePathCall *, void *);
/*Whole original42cab0 thiscall(app) noargs/RET,777bytes; cdecl48c190(path),
 69bytes. Source filenames CL AW.REZ/CLAW24.REZ/CLAW.FEC and original ordered
 local/CD path probes, flags104/108/10c/110/114, errors and reverse CString
 cleanup. No REZ payload load is claimed. GetCurrentDirectory546a28 has
 arg1 localMask2/buffer256 (count255). OpenFile546a30 has arg1mask2/buffer136,
 OF_EXIST4000 and tests full result againstFFFFFFFF. Windows/file/mode and
 formatter services are isolated exact endpoints; no OS/user-file access.
 Formatter4f4f58 is cdecl(destinationCString,format,dirOrSignedDrive,name).
 Directory argument2 is localMask4/buffer256; destination is a raw app cell.
 Return1 recognized/completed, source EAX separately. fault1 span/service,
 2 ABI/domain,3 operation budget. Exceptional SEH unwinding is not adapted.
 Strict nullable word lookup plus exact bytes is required for odd CString
 allocation tails; one scoped constructor adapter owns each tail, while
 CStringAssignment receives the strict host and its own existing adapter.
 Setfault0. Borrowed host bindings never retain this call's stack.*/
uint32_t claw_application_archive_path_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                             uint32_t argumentCount, ClawApplicationArchivePathContext *,
                                             ClawApplicationArchivePathDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
