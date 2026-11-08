#ifndef CLAW_SAVE_FILE_RUNTIME_H
#define CLAW_SAVE_FILE_RUNTIME_H
#include "SceneActorRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawSaveFileContext {
    ClawSceneActorHost scene;
    uint8_t *(*lookupBytes)(void *, uint32_t token, uint32_t bytes);
    uint32_t emptyStringToken;
    // Explicit caller-owned representation of original automatic stack locals:
    // CFile16bytes, resolved path260bytes, SECURITY_ATTRIBUTES12bytes,
    // WriteFile's4-byte in/out count. Not source heap allocations.
    uint32_t fileScratchToken, pathScratchToken, securityScratchToken, countScratchToken;
    uint32_t maximumTraversal, maximumSteps, fault;
} ClawSaveFileContext;
typedef struct ClawSaveFileCall {
    uint32_t function, receiver, argumentCount, arguments[8];
} ClawSaveFileCall;
// Exact source identities/arity. Windows IAT identities identify imports;
// pointer args are raw tokens, including scratch spans available via lookup.
// CString assignment/release, path resolution, thread-local RNG and exception
// transports remain explicit; hosts can compose verified existing modules.
// Throwing transport sets context.fault (recommended3), then later writes stop.
typedef uint32_t (*ClawSaveFileDependency)(ClawSaveFileContext *, const ClawSaveFileCall *, void *);
// Whole writer49bbc0(), checksum49bf70(data,bytes), permutation49bfb0(limit),
// next49c000(), xor49c030/49c070(data,bytes), CFile4f72c9/4f7369(),
// open4f7448(name,flags,errorObject), write4f75aa(data,bytes), close4f766e(),
// CString clear4f650f(). Meaningful EAX is separate from support/completion;
// source void functions normalize0. fault1 missing span/service,2 ABI/domain,
// 4 traversal/step bound are native safety extensions; unsupported leaves0.
uint32_t claw_save_file_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                              ClawSaveFileContext *, ClawSaveFileDependency, void *, uint32_t *result);
// Exact inline426565..42658d manager constructor stores, not a whole startup
// implementation: CPtrList(block10), CString+1c, header8words zero,+40zero,
// +44=4d505255. Preserves +48..54 heap seed. Caller allocates actual0x58bytes.
uint32_t claw_save_file_initialize_manager(uint32_t receiver, ClawSaveFileContext *);
#ifdef __cplusplus
}
#endif
#endif
