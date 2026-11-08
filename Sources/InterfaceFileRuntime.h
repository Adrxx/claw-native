#ifndef CLAW_INTERFACE_FILE_RUNTIME_H
#define CLAW_INTERFACE_FILE_RUNTIME_H
#include "SceneLifecycleRuntime.h"
#include "CArrayRuntime.h"
#include "ActorDestruction.h"
#ifdef __cplusplus
extern "C" {
#endif
#define CLAW_INTERFACE_CONTROLLER_BYTES 256u
#define CLAW_INTERFACE_NODE_BYTES 176u
#define CLAW_INTERFACE_COMPONENT_BYTES 108u
typedef struct ClawInterfaceFileContext {
    ClawSceneActorHost scene;
    ClawCArrayContext *arrays;
    ClawSceneLifecycleContext *strings;
    ClawActorDestructionGlobals *destruction;
    /* Caller-owned source automatic-storage aliases; do not overlap live data.
    memoryFileToken40 bytes; archiveToken68 bytes; stringScratchToken4 bytes.
    Their raw seeds remain caller-owned. Stack receiver/argument identities are
    normalized in rich dependency calls with synchronous buffers. */
    uint32_t memoryFileToken, archiveToken, stringScratchToken;
    uint32_t maximumOperations, fault;
} ClawInterfaceFileContext;
typedef struct ClawInterfaceFileCall {
    uint32_t function, receiver, argumentCount, arguments[10], localMask, bufferCount;
    void *buffers[3];
    uint32_t bufferBytes[3];
} ClawInterfaceFileCall;
typedef uint32_t (*ClawInterfaceFileDependency)(ClawInterfaceFileContext *, const ClawInterfaceFileCall *, void *);
/* Raw source entry interface. Loader4dcdf0 uses7 words/RET28:
 graphicsManager,data,size,imageResolver,argument4,argument5,argument6.
 File loader4dcd10 takes6 words/RET24 (data/size replaced by file object).
 Interface constructor4dcc40(width,height), embeddedroot VT513ed8; StateFive
 overrides controller VT50c23c externally. Resource/window/physical drawing and
 image acquisition endpoints remain source-address services.
 Append 0x4dd2c0 takes one component: null returns false without receiver access;
 nonnull appends through the existing embedded CArray at controller +8.
 Meaningful source EAX is separate from completion status; void method EAX has no host meaning.
 Unknown/fault returns0.
 Requirefault0; fault1 missing span/service,2 original unsafe/EOF prefix,
 3 operation/ABI limit. Final supported inventory follows verified docs. */
uint32_t claw_interface_file_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                   uint32_t argumentCount, ClawInterfaceFileContext *, ClawInterfaceFileDependency,
                                   void *, uint32_t *result);
uint32_t claw_interface_file_function(uint32_t vtableToken, uint32_t slot);
#ifdef __cplusplus
}
#endif
#endif
