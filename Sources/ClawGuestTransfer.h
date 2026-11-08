#ifndef CLAW_GUEST_TRANSFER_H
#define CLAW_GUEST_TRANSFER_H
#include "ClawRuntime.h"
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#define CLAW_GUEST_NOEXCEPT noexcept
#else
#define CLAW_GUEST_NOEXCEPT
#endif
enum { CLAW_GUEST_VERSION = 1, CLAW_GUEST_FAULT = 0, CLAW_GUEST_RETURNED = 1,
       CLAW_GUEST_TRANSFER = 2, CLAW_GUEST_RAISE = 1 };
typedef struct ClawGuestSession ClawGuestSession;
typedef struct ClawGuestConfig {
    uint32_t size, version, rootFunction, textBegin, textEnd, raiseSlot, raiseStub;
} ClawGuestConfig;
typedef struct ClawGuestPhysicalEvent {
    uint32_t size, version, kind, slot, stub, code, flags, count, returnPC;
    ClawSourceContext cpu;
    uint32_t information[15];
} ClawGuestPhysicalEvent;
typedef struct ClawGuestOutcome {
    uint32_t size, version, kind, reserved;
    uint64_t generation, payload;
    ClawGuestPhysicalEvent event;
} ClawGuestOutcome;
typedef struct ClawGuestEHContract {
    uint32_t size, version, ownerEntry, entryPC, handler, funcInfo, handlerTable, callSite, returnPC;
} ClawGuestEHContract;
typedef struct ClawGuestEHInvocation {
    uint32_t size, version, ownerEntry, entryPC, establisher, exceptionRecord, contextRecord;
    uint64_t serial;
    ClawSourceContext cpu;
} ClawGuestEHInvocation;
typedef uint32_t (*ClawGuestEHEntry)(const ClawGuestEHInvocation *, ClawHost *);
ClawGuestSession *claw_guest_create(ClawHost *, const ClawGuestConfig *) CLAW_GUEST_NOEXCEPT;
uint64_t claw_guest_generation(ClawGuestSession *, ClawHost *) CLAW_GUEST_NOEXCEPT;
uint32_t claw_guest_destroy(ClawGuestSession *, ClawHost *, uint64_t) CLAW_GUEST_NOEXCEPT;
/* Status: 0 ordinary, 1 pending, 2 invalid. Faults always take priority. */
uint32_t claw_guest_status(ClawHost *) CLAW_GUEST_NOEXCEPT;
uint32_t claw_guest_lease_enter(ClawHost *, const ClawCall *) CLAW_GUEST_NOEXCEPT;
void claw_guest_lease_leave(ClawHost *, const ClawCall *) CLAW_GUEST_NOEXCEPT;
uint32_t claw_guest_capture_original(ClawGuestSession *, ClawHost *, uint64_t,
    const ClawCall *, const ClawGuestPhysicalEvent *, uint64_t payload) CLAW_GUEST_NOEXCEPT;
uint32_t claw_guest_run(ClawGuestSession *, ClawHost *, uint64_t, ClawEntry,
    uint32_t function, uint32_t receiver, const uint32_t *arguments, uint32_t argumentCount,
    uint32_t *result, ClawGuestOutcome *) CLAW_GUEST_NOEXCEPT;
/* The graph owner binds one finite nonreturning funclet before execution.
   run_eh is a driver operation after stopped original selection; the exported
   funclet accepts only its private live invocation, never a copied record. */
uint32_t claw_guest_bind_eh(ClawGuestSession *, ClawHost *, uint64_t,
    const ClawGuestEHContract *, ClawGuestEHEntry) CLAW_GUEST_NOEXCEPT;
uint32_t claw_guest_run_eh(ClawGuestSession *, ClawHost *, uint64_t,
    const ClawGuestEHInvocation *, ClawGuestOutcome *) CLAW_GUEST_NOEXCEPT;
uint32_t claw_guest_prepare_eh(ClawGuestSession *, ClawHost *, uint64_t,
    const ClawGuestEHInvocation *) CLAW_GUEST_NOEXCEPT;
uint32_t claw_guest_validate_eh(ClawHost *, const ClawGuestEHInvocation *) CLAW_GUEST_NOEXCEPT;
size_t claw_guest_sizeof(uint32_t kind) CLAW_GUEST_NOEXCEPT;
size_t claw_guest_offset(uint32_t kind, uint32_t field) CLAW_GUEST_NOEXCEPT;
#ifdef __cplusplus
}
#endif
#undef CLAW_GUEST_NOEXCEPT
#endif
