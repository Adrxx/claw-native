#ifndef CLAW_STARTUP_LOGIC_REGISTRATION_RUNTIME_H
#define CLAW_STARTUP_LOGIC_REGISTRATION_RUNTIME_H
#include "ImageControllerLoadingRuntime.h"
#include "CStringAssignmentRuntime.h"
#include "ActorDestruction.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ClawStartupLogicRegistrationContext {
    ClawSceneActorHost scene;
    ClawImageControllerLoadingContext *dictionary;
    ClawCStringAssignmentContext *strings;
    ClawSceneLifecycleContext *lifecycle;
    ClawActorDestructionGlobals *destruction;
    uint32_t maximumOperations, fault;
} ClawStartupLogicRegistrationContext;
typedef ClawImageControllerLoadingCall ClawStartupLogicRegistrationCall;
typedef uint32_t (*ClawStartupLogicRegistrationDependency)(ClawStartupLogicRegistrationContext *,
                                                           const ClawStartupLogicRegistrationCall *, void *);
/* Whole401000 is cdecl(scene), receiver0, no callee stack pop:212 virtual
 registrations and84 interleaved no-arg class/state initializer calls. Those
 helper effects stay explicit exact ordered services; metadata is not bootstrap.
 Whole4d6340(registry,[callback,name,flags]),RET12 creates372-byte metadata,
 initializes and inserts via frozen map/CString. Duplicate replaces value without
 deleting previous object. Null allocation reaches source invalid dereference;
 native fault1 is a stopped safety prefix, not source failure success.
 4c8160(logic,[callback,flags]),RET8 composes frozen WorldObject pure logic slice
 via private synchronous dummy actor projection; no allocator/event is invented.
 Strict byte providers owned by borrowed CString views remain unchanged. Set
 borrowed faults0; synchronous contexts cannot be borrowed concurrently.
 Return1 completion, original meaningful factory/init EAX separately;401000void
 output0. Fault1 missing graph/service/span,2ABI,3budget are native diagnostics.*/
uint32_t claw_startup_logic_registration_entry(uint32_t function, uint32_t receiver, const uint32_t *arguments,
                                               uint32_t argumentCount, ClawStartupLogicRegistrationContext *,
                                               ClawStartupLogicRegistrationDependency, void *, uint32_t *result);
#ifdef __cplusplus
}
#endif
#endif
