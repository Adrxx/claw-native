// Level 1 tile-manager collision dispatch
//
// Original v1.0 entry identities stay in the dispatch switch. Guest tokens,
// wrapping arithmetic and argument-slot aliases retain their original contracts.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using claw::s32;
using claw::recovered::v10::ActorInteractionFields;
using claw::recovered::v10::ActorFlagByteFields;
using claw::recovered::v10::CollisionActorFields;
using claw::recovered::v10::CollisionManagerFields;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4cbb60:
        return 4;
    case 0x4cbcd0:
        return 4;
    case 0x4cbe30:
        return 4;
    default:
        return -1;
    }
}

// Layout views do no reads at construction. Each accessor stays at the old
// access point, including re-reads after original callbacks.
uint32_t collideObject(Run &run, uint32_t manager, const uint32_t *arguments);

// Preserve the two's-complement absolute value, including INT_MIN wrapping.
uint32_t absolute(uint32_t value) {
    uint32_t sign = s32(value) < 0 ? 0xffffffffu : 0u;
    return (value ^ sign) - sign;
}

// 0x4cbcd0. Dispatches on the motion state of the object, then adds result bits.
uint32_t dispatchMotion(Run &run, uint32_t manager, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    uint32_t x = arguments[1];
    uint32_t y = arguments[2];
    uint32_t flags = arguments[3];
    ActorInteractionFields actor{run, object};
    CollisionActorFields collision{run, object};

    uint32_t result = 0;
    uint32_t oldX = actor.worldX();
    uint32_t oldY = actor.worldY();
    uint32_t state = collision.motionState();
    uint32_t index = state - 1;
    if (index <= 7) {
        switch (index) {
        case 0:
        case 1:
        case 4:
            result = collideObject(run, manager, arguments);
            break;
        case 2:
            result = run.call(0x4cc1b0, manager, {object, x, y, flags});
            if (collision.motionState() == 4)
                result = result | 0x800000;
            break;
        case 3:
            result = run.call(0x4cbff0, manager, {object, x, y, flags});
            if (collision.motionState() == 1)
                result = result | 0x1000000;
            break;
        case 5:
            result = run.call(0x4cc2b0, manager, {object, x, y, flags});
            break;
        case 6:
            actor.worldX(x);
            actor.worldY(y);
            break;
        case 7:
            if (s32(y) < s32(oldY)) {
                result = run.call(0x4cc1b0, manager, {object, x, y, flags});
                if (collision.motionState() == 4) {
                    result = result | 0x800000;
                    collision.motionState(8);
                }
            } else {
                result = run.call(0x4cbff0, manager, {object, x, y, flags});
                if (collision.motionState() == 1)
                    result = result | 0x1000000;
            }
            break;
        }
    }
    if (result & 0x1820000)
        result = result | 0x10000;
    uint32_t objectFlags = actor.flags();
    if (objectFlags & 0x400000)
        result = result | 0x100000;
    if (objectFlags & 0x10)
        result = result | 0x200000;
    if (actor.worldX() == oldX) {
        if (actor.worldY() == oldY)
            result = result | 0x400000;
    }
    return result;
}

// 0x4cbb60. Moves toward (x, y) in steps no longer than the manager's limits,
// stopping when the motion state changes or the dispatch reports a stop bit.
uint32_t stepToward(Run &run, uint32_t manager, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    uint32_t x = arguments[1];
    uint32_t y = arguments[2];
    uint32_t flags = arguments[3];
    ActorInteractionFields actor{run, object};
    CollisionActorFields collision{run, object};
    CollisionManagerFields managerFields{run, manager};
    ActorFlagByteFields flagBytes{run, object};

    uint32_t stepLimitX = managerFields.horizontalStepLimit();
    uint32_t currentX = actor.worldX();
    if (s32(absolute(currentX - x)) <= s32(stepLimitX)) {
        uint32_t distanceY = absolute(actor.worldY() - y);
        if (s32(distanceY) <= s32(run.gets(manager + 0x68))) {
            return dispatchMotion(run, manager, arguments);
        }
    }
    if (flagBytes.flags() & 0x10) {
        return dispatchMotion(run, manager, arguments);
    }
    uint32_t savedState = collision.motionState();
    if (savedState == 7) {
        return dispatchMotion(run, manager, arguments);
    }
    uint32_t stepX = stepLimitX;
    uint32_t stepY = managerFields.verticalStepLimit();
    bool keepGoing = true;
    if (s32(currentX) > s32(x))
        stepX = 0u - stepX;
    if (s32(actor.worldY()) > s32(y))
        stepY = 0u - stepY;
    for (;;) {
        uint32_t nextX = stepX + actor.worldX();
        if (s32(stepX) > 0) {
            if (s32(nextX) > s32(x))
                nextX = x;
        } else {
            if (s32(nextX) < s32(x))
                nextX = x;
        }
        uint32_t nextY = stepY + actor.worldY();
        if (s32(stepY) > 0) {
            if (s32(nextY) > s32(y))
                nextY = y;
        } else {
            if (s32(nextY) < s32(y))
                nextY = y;
        }
        uint32_t nextArguments[] = {object, nextX, nextY, flags};
        uint32_t result = dispatchMotion(run, manager, nextArguments);
        if (collision.motionState() != savedState) {
            keepGoing = false;
        } else if (result & 0x10000) {
            keepGoing = false;
        } else if (run.get(object + 0x4c) == x && run.get(object + 0x50) == y) {
            keepGoing = false;
        } else if (result & 0x400000) {
            keepGoing = false;
        }
        if (!keepGoing)
            return result;
    }
}

// 0x4cbe30. Resolves horizontal then vertical motion, probing the tile map.
// The original keeps x, flags and the probe outputs in its own argument slots
// (entry+8 x, entry+0xc and entry+0x10 probe outputs) because it passes their
// addresses to callees.
uint32_t collideObject(Run &run, uint32_t manager, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    uint32_t x = arguments[1];
    uint32_t y = arguments[2];
    uint32_t flags = arguments[3];
    ActorInteractionFields actor{run, object};
    CollisionActorFields collision{run, object};
    ActorFlagByteFields flagBytes{run, object};

    uint32_t slotX = run.automatic(8);
    uint32_t slotA = run.automatic(0xc);
    uint32_t slotB = run.automatic(0x10);
    uint32_t result = 0;
    run.put(slotX, x);
    uint32_t currentX = actor.worldX();
    if (s32(x) > s32(currentX)) {
        result = run.call(0x4cc420, manager, {object, x, y, slotX, flags});
        x = run.get(slotX);
    } else if (s32(x) < s32(currentX)) {
        result = run.call(0x4cc570, manager, {object, x, y, slotX, flags});
        x = run.get(slotX);
    }
    if (s32(y) < s32(actor.worldY())) {
        y = run.call(0x4ccc50, manager, {object, x, y, flags});
        x = run.get(slotX);
    }
    bool probed = false;
    uint32_t probeY = 0;
    if (flags & 1) {
        run.put(slotB, x);
        probeY = collision.probeOffset_0x11c() + y - 1;
        probed = true;
    } else if (flags & 2) {
        run.put(slotB, x);
        probeY = collision.probeOffset_0x124() + y + 2;
        probed = true;
    }
    if (probed) {
        uint32_t tile = run.call(0x4207f0, manager, {x, probeY});
        if (tile == 3) {
            uint32_t refine = flags & 0x10;
            uint32_t chosenX = 0;
            if (refine) {
                uint32_t probeX = run.get(slotB);
                run.put(slotB, probeX);
                run.put(slotA, probeX);
                uint32_t found = run.call(0x4cd120, manager, {probeX, probeY, slotB, slotA});
                chosenX = probeX;
                if (found != 0) {
                    uint32_t sum = run.get(slotA) + run.get(slotB);
                    // The original wraps the sum before signed division toward zero.
                    chosenX = uint32_t(s32(sum) / 2);
                }
            } else {
                chosenX = run.get(slotX);
            }
            if (refine)
                run.put(slotX, chosenX);
            collision.motionState(6);
            actor.worldX(run.get(slotX));
            actor.worldY(y);
            return result;
        }
        x = run.get(slotX);
    }
    if ((flagBytes.flags() & 0x10) == 0) {
        y = run.call(0x4cc6c0, manager, {object, x, y, flags});
    } else {
        uint32_t clear = run.call(0x4cd060, manager, {object, collision.unknown_0x80(), x, y, flags});
        if (clear == 0)
            collision.motionState(4);
    }
    actor.worldX(run.get(slotX));
    actor.worldY(y);
    return result;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4cbb60:
        return stepToward(run, receiver, arguments);
    case 0x4cbcd0:
        return dispatchMotion(run, receiver, arguments);
    case 0x4cbe30:
        return collideObject(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_collision_dispatch_01_entry, owned, body)
