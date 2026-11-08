#ifndef CLAW_CSTRING_ASSIGNMENT_RUNTIME_H
#define CLAW_CSTRING_ASSIGNMENT_RUNTIME_H
#include "SceneLifecycleRuntime.h"
#include "PlayerFadeBlendRuntime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawCStringAssignmentContext {
    ClawSceneActorHost scene;
    ClawSceneLifecycleContext *lifecycle;
    ClawPlayerFadeBlendContext *allocation;
    ClawCArrayContext *arrays;
    /*Optional exact byte-span transport. Native synchronous scratch adapts the
  frozen word-only allocator/copy interface without adding string tail bytes.*/
    void *byteContext;
    uint8_t *(*bytes)(void *, uint32_t token, uint32_t length);
    uint32_t maximumOperations, fault;
} ClawCStringAssignmentContext;
typedef struct ClawCStringAssignmentCall {
    uint32_t function, receiver, argumentCount, arguments[4];
} ClawCStringAssignmentCall;
typedef uint32_t (*ClawCStringAssignmentDependency)(ClawCStringAssignmentContext *, const ClawCStringAssignmentCall *,
                                                    void *);
/*Whole original4f66cc(LPCSTR)RET4 returns receiver;4f6650(length,data)RET8
 and4f655b(length)RET4 are void. Length import identity5469e4 is explicit.
 Borrowed views compose frozen4f64ba release/clear,4f6480 allocation and
 overlap-safe4a4a80; no duplicate destructor, clear, constructor or retain.
 Shared52e1c8/cc remain raw source aliases. Callback mutations are read in
 source order. Return1 completed/recognized,0 unsupported/fault; EAX separate.
 fault1 span/service,2 ABI/unsafe domain,3 traversal guard are extensions,
 not original safe failure returns. Initialize all borrowed faults tozero.
 Views and byte scratch are synchronous; no concurrent use during a call.*/
uint32_t claw_cstring_assignment_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                       uint32_t argumentCount, ClawCStringAssignmentContext *,
                                       ClawCStringAssignmentDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
