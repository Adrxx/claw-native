// Level 14 Omar core, recovered from the original instruction bodies.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x463a30: return 1;
    case 0x463a50: return 0;
    case 0x463b40: return 1;
    case 0x463fd0: return 0;
    case 0x4640b0: return 1;
    case 0x4642b0: return 1;
    case 0x464360: return 1;
    case 0x464500: return 2;
    default: return -1;
    }
}

ClawX87State floatingState() {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    return fp;
}

void loadDouble(Run &run, ClawX87State &fp, uint32_t address) {
    run.x87_step(CLAW_X87_F64, fp, {run.get(address), run.get(address + 0x4)});
}

uint32_t truncate(Run &run, ClawX87State &fp) {
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}

// 0x463a50. Tear down the nine motion records, bit array and two strings.
uint32_t destroy(Run &run, uint32_t receiver) {
    run.call(0x4a4450, 0, {receiver + 0x4a8, 0xf0, 9, 0x4c96b0});
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
    return 0;
}

// 0x463a30. Scalar deleting destructor; low flag bit controls deletion.
uint32_t deletingDestroy(Run &run, uint32_t receiver, uint32_t flags) {
    destroy(run, receiver);
    if (flags & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x463b40. Global state callback table: bounds, backing storage and stride
// are at 0x537bd8, 0x537be0 and 0x537be8 respectively.
uint32_t stateSlot(Run &run, uint32_t state) {
    uint32_t lower = run.get(0x537bd8);
    run.put(0x537bf0, 0);
    if (s32(state) < s32(lower) || s32(state) > s32(run.get(0x537bdc))) {
        uint32_t grown = run.call(0x4db6e0, 0x537bd0, {state, 0});
        if (!grown) {
            uint32_t error = run.get(0x544b4c);
            uint32_t site = run.call(0x4db5f0, 0);
            uint32_t context = run.get(0x537bd4);
            run.put(0x544b14, site);
            run.call(0x4db4d0, context, {0x537bd0, error, 0xc});
            return run.get(0x537be4);
        }
        lower = run.get(0x537bd8);
    }
    return run.get(0x537be0) + (state - lower) * run.get(0x537be8);
}

uint32_t dispatchState(Run &run, uint32_t receiver, uint32_t state) {
    uint32_t slot = stateSlot(run, state);
    if (run.get(slot)) {
        slot = stateSlot(run, state);
        run.call(run.get(slot), receiver);
    } else {
        run.call(0x40e280, receiver, {state});
    }
    return 0;
}

// 0x463fd0. +0x68/+0x70 position doubles are separately reloaded for the
// cached +0x118/+0x11c words and the actor at +0x0c.
uint32_t publishPosition(Run &run, uint32_t receiver) {
    auto fp = floatingState();
    loadDouble(run, fp, receiver + 0x68);
    uint32_t value = truncate(run, fp);
    run.put(receiver + 0x118, value);
    loadDouble(run, fp, receiver + 0x70);
    value = truncate(run, fp);
    run.put(receiver + 0x11c, value);
    loadDouble(run, fp, receiver + 0x68);
    value = truncate(run, fp);
    run.put(run.get(receiver + 0xc) + 0x4c, value);
    loadDouble(run, fp, receiver + 0x70);
    value = truncate(run, fp);
    run.put(run.get(receiver + 0xc) + 0x50, value);
    return 0;
}

// 0x4640b0. Advance nine motion records at +0x4a8, stride +0xf0, using
// the unsigned millisecond clock and each record's previous time double.
uint32_t advanceMotion(Run &run, uint32_t receiver, uint32_t argument) {
    run.call(0x44d3c0, receiver, {argument});
    auto fp = floatingState();
    uint32_t record = receiver + 0x4a8;
    for (uint32_t index = 0; index != 9; ++index) {
        const double clock = double(run.get(0x537210));
        uint64_t bits;
        std::memcpy(&bits, &clock, sizeof(bits));
        run.x87_step(CLAW_X87_F64, fp, {uint32_t(bits), uint32_t(bits >> 32)});
        run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50ead8), run.get(0x50eadc)});
        run.x87_step(CLAW_X87_SUB_F64, fp, {run.get(record), run.get(record + 0x4)});
        bits = run.x87_step(CLAW_X87_STP_F64, fp);
        run.call(0x403b40, record, {uint32_t(bits), uint32_t(bits >> 32)});
        record += 0xf0;
    }
    return 0;
}

// 0x464500. Timed reaction: actor +0x12c, animation owner +0x10,
// timer +0xd30/+0xd34, and pending states +0xd38/+0xd3c.
uint32_t setReaction(Run &run, uint32_t receiver, uint32_t first, uint32_t second) {
    uint32_t owner = run.get(receiver + 0x10);
    run.put(receiver + 0x18, 0x4646c0);
    run.put(receiver + 0x1c, run.get(owner + 0x1c));
    uint32_t actor = run.get(receiver + 0x12c);
    run.put(actor + 0x8, run.get(actor + 0x8) | 4);
    owner = run.get(receiver + 0x10);
    run.put(receiver + 0x24, run.get(owner + 0x1c));
    uint32_t animation = run.call(0x4dba00, 0x537668, {0x529a24});
    run.put(run.get(receiver + 0x10) + 0x1c, animation);
    run.put(receiver + 0xd38, first);
    run.put(receiver + 0xd3c, second);
    run.put(receiver + 0xd34, 0x7d0);
    run.put(receiver + 0xd30, run.get(0x537210));
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x48, 0x1e);
    run.put(actor + 0x44, 0);
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x40, run.get(actor + 0x40) | 8);
    uint32_t sound = run.get(receiver + 0x47c);
    if (sound) {
        uint32_t enabled = run.get(0x532c0c);
        uint32_t channel = run.get(0x532c10);
        if (enabled) {
            run.call(0x4b45f0, run.get(sound + 0x10), {channel, 0, 0, 0});
        }
    }
    return 0;
}

// 0x4642b0. Normal vulnerable hit; +0xd1c guards this path and +0xd20
// alternates the pending reaction state.
uint32_t vulnerableHit(Run &run, uint32_t receiver, uint32_t argument) {
    if (run.get(receiver + 0xd1c)) {
        return 0;
    }
    run.vcall(receiver, 0x28, {argument});
    run.call(0x440e20, receiver, {argument});
    uint32_t manager = run.get(0x537e88);
    uint32_t selector = run.get(run.get(run.get(manager + 0x6c) + 0x14) + 0x14);
    run.call(selector ? 0x44f510 : 0x44f3c0, receiver);
    uint32_t actor = run.get(receiver + 0xc);
    uint32_t health = run.get(actor + 0x10c);
    if (s32(health) > 0) {
        run.put(actor + 0x10c, health - (run.get(argument + 0x104) << 1));
    }
    if (run.get(receiver + 0xd20) == 1) {
        setReaction(run, receiver, 0xa16d, 0x42b);
        run.put(receiver + 0xd20, 0);
    } else {
        setReaction(run, receiver, 0xa550, 0x42b);
        run.put(receiver + 0xd20, 1);
    }
    return 0;
}

// 0x464360. Shield hit alternates the +0xd18 shield mode and the nine
// motion-record angular speeds (+0x4d0, +0xf0 stride).
uint32_t shieldHit(Run &run, uint32_t receiver, uint32_t argument) {
    if (!run.get(receiver + 0xd1c)) {
        run.vcall(receiver, 0x9c);
        return 0;
    }
    run.call(0x43e9c0, receiver, {0x1f4});
    run.call(0x44d5a0, receiver, {argument});
    run.put(argument + 0x8, run.get(argument + 0x8) | 0x10000);
    run.call(0x44f3c0, receiver);
    uint32_t mode = run.get(receiver + 0xd18);
    if (mode == 1) {
        if (run.get(argument + 0x164) & 0x40000) {
            uint32_t actor = run.get(receiver + 0xc);
            run.put(actor + 0x10c, run.get(actor + 0x10c) - 0x19);
            setReaction(run, receiver, 0xa50a, 0x9ab);
            run.put(receiver + 0xd18, 0);
            uint32_t record = receiver + 0x4d0;
            for (uint32_t index = 0; index != 9; ++index) {
                run.put(record, 0);
                run.put(record + 0x4, 0xc06f4000);
                record += 0xf0;
            }
            return 0;
        }
    } else if (mode == 0) {
        if (run.get(argument + 0x164) & 0x80000) {
            uint32_t actor = run.get(receiver + 0xc);
            run.put(actor + 0x10c, run.get(actor + 0x10c) - 0x19);
            setReaction(run, receiver, 0xa1b8, 0x9ab);
            run.put(receiver + 0xd18, 1);
            uint32_t record = receiver + 0x4d0;
            for (uint32_t index = 0; index != 9; ++index) {
                run.put(record, 0);
                run.put(record + 0x4, 0x406f4000);
                record += 0xf0;
            }
            return 0;
        }
    } else {
        return 0;
    }
    uint32_t actor = run.get(receiver + 0xc);
    uint32_t health = run.get(actor + 0x10c) + 0x19;
    if (s32(health) >= 0x64) {
        health = 0x64;
    }
    run.put(actor + 0x10c, health);
    uint32_t sprite = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + 0x480);
    if (run.get(sprite + 0x38) != 0xffffffff) {
        run.call(0x48ce40, 0, {run.get(receiver + 0xc), animation, 0});
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x463a30: return deletingDestroy(run, receiver, arguments[0]);
    case 0x463a50: return destroy(run, receiver);
    case 0x463b40: return dispatchState(run, receiver, arguments[0]);
    case 0x463fd0: return publishPosition(run, receiver);
    case 0x4640b0: return advanceMotion(run, receiver, arguments[0]);
    case 0x4642b0: return vulnerableHit(run, receiver, arguments[0]);
    case 0x464360: return shieldHit(run, receiver, arguments[0]);
    case 0x464500: return setReaction(run, receiver, arguments[0], arguments[1]);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_fourteen_omar_core_01_entry, owned, body)
