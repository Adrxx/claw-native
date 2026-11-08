#ifndef CLAW_SAVE_LOAD_RUNTIME_H
#define CLAW_SAVE_LOAD_RUNTIME_H
#include "SaveFileRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawSaveLoadContext {
    ClawSaveFileContext save;
    // Original startup's260-byte automatic directory buffer; caller-owned.
    uint32_t directoryScratchToken, maximumTraversal, fault;
} ClawSaveLoadContext;
typedef ClawSaveFileCall ClawSaveLoadCall;
typedef uint32_t (*ClawSaveLoadDependency)(ClawSaveLoadContext *, const ClawSaveLoadCall *, void *);
// Whole thiscall entries:49b840(filename),49b9a0(),49b950()/49b970() cleanup,
// 49bdb0(name,description,email,flags),49be50(payload),49bee0(name),
// 49bf30(record),49a5a0(name,description,email,flags),49a6d0(payload),
// 49a8f0() validation,49ad50()/49adc0() bindings,4d5330(deleteFlag),423f00().
// Cdecl49a990(scoreRecord17) usesreceiver0. CFile4f7570(data,bytes),
// 4f774d()/4f75f5(distance,origin) arethiscall; physical ReadFile/seek explicit.
// Always composes frozen SaveFileRuntime, CPtrList and49a720 cache reset.
// Full manager0x58bytes/playerrecord0x2648bytes. No schema normalization, rollback,
// assumedshort-readfailure/versionrejection or guessed record zeroing.
// Fault1 span/service,2 ABI/domain,4 bounded traversal; dependencyfault preserved.
uint32_t claw_save_load_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
                              ClawSaveLoadContext *, ClawSaveLoadDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
