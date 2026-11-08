// Level 1 respawn cleanup callback 0x46e340 (original v1.0).
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using claw::recovered::v10::RespawnCleanupActorFields;

constexpr uint32_t CleanupEligibleMask = 0x2000;
constexpr uint32_t DeferredRemovalMask = 0x10000;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x46e340:
        return 1;
    default:
        return -1;
    }
}

// 0x46e340. cdecl, 1 stack argument (actor), void. When the actor is non-null
// and bit 0x2000 of its flags at +0x164 is set, sets bit 0x10000 in the field
// at +0x08.
uint32_t markDeferredRemovalCallback(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    if (actor == 0)
        return 0;
    RespawnCleanupActorFields actorFields{run, actor};
    uint32_t flags = actorFields.cleanupFlags();
    if ((flags & CleanupEligibleMask) == 0)
        return 0;
    uint32_t state = actorFields.removalFlags();
    state = state | DeferredRemovalMask;
    actorFields.removalFlags(state);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x46e340:
        return markDeferredRemovalCallback(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_respawn_02_entry, owned, body)
