// Level 10 marrow floor closure
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x45a400:
        return 1;
    case 0x45a7c0:
        return 1;
    case 0x45a940:
    case 0x45a980:
    case 0x45a9f0:
    case 0x45aa40:
    case 0x45aa90:
    case 0x45aae0:
    case 0x45ab40:
    case 0x45abc0:
    case 0x45ac40:
        return 0;
    default:
        return -1;
    }
}

// Global 0x537b14 is the optional player controller.
// Global 0x537e88 is the scene root used for the state serial.
// Receiver: +0xc actor, +0x10 logic object, +0x48 serial, +0x5c sound, +0x68 opened.

uint32_t movementStep(Run &run, uint32_t actor) {
    uint32_t product = run.get(actor + 0x148) * run.get(0x5430c4);
    uint64_t wide = uint64_t(product) * uint64_t(0x10624dd3u);
    return uint32_t(wide >> 32) >> 6;
}

uint32_t enterIdle(Run &run, uint32_t self);
uint32_t moveTowardLow(Run &run, uint32_t self);
uint32_t moveTowardHigh(Run &run, uint32_t self);

// 0x45a400. Dispatches through the state table at 0x537b20.
void dispatchState(Run &run, uint32_t self, uint32_t index) {
    uint32_t low = run.get(0x537b28);
    run.put(0x537b40, 0);
    uint32_t row = 0;
    if (s32(index) < s32(low) || s32(index) > s32(run.get(0x537b2c))) {
        uint32_t grown = run.call(0x4db6e0, 0x537b20, {index, 0});
        if (grown == 0) {
            uint32_t text = run.get(0x544b4c);
            uint32_t site = run.call(0x4db5f0, 0, {});
            uint32_t owner = run.get(0x537b24);
            run.put(0x544b14, site);
            run.call(0x4db4d0, owner, {0x537b20, text, 0xc});
            row = run.get(0x537b34);
            low = run.get(0x537b28);
        } else {
            low = run.get(0x537b28);
            row = (index - low) * run.get(0x537b38) + run.get(0x537b30);
        }
    } else {
        row = (index - low) * run.get(0x537b38) + run.get(0x537b30);
    }
    if (run.get(row) == 0) {
        run.call(0x4a36f0, 0, {self});
        return;
    }
    run.put(0x537b40, 0);
    if (s32(index) < s32(low) || s32(index) > s32(run.get(0x537b2c))) {
        uint32_t grown = run.call(0x4db6e0, 0x537b20, {index, 0});
        if (grown == 0) {
            uint32_t text = run.get(0x544b4c);
            uint32_t site = run.call(0x4db5f0, 0, {});
            uint32_t owner = run.get(0x537b24);
            run.put(0x544b14, site);
            run.call(0x4db4d0, owner, {0x537b20, text, 0xc});
            uint32_t fallback = run.get(0x537b34);
            run.call(run.get(fallback), self, {});
            return;
        }
        low = run.get(0x537b28);
    }
    uint32_t entry = (index - low) * run.get(0x537b38) + run.get(0x537b30);
    run.call(run.get(entry), self, {});
}

// 0x45a7c0. Constructor; returns the receiver.
uint32_t construct(Run &run, uint32_t self, uint32_t actor) {
    run.put(self + 0x0, 0x50b064);
    run.put(self + 0x8, actor);
    run.put(self + 0xc, actor);
    uint32_t logic = run.get(actor + 0x6c);
    run.put(self + 0x10, logic);
    run.put(self + 0x4, 0);
    run.call(0x4c7fa0, actor, {0x522d54});
    run.call(0x4c8060, run.get(self + 0xc), {0x522d48});
    run.put(self + 0x14, 0);
    run.put(self + 0x18, 0);
    run.put(self + 0x1c, 0x3e9);
    run.put(self + 0x20, 2);
    run.put(self + 0x28, actor);
    run.put(self + 0x2c, actor);
    run.put(self + 0x30, run.get(actor + 0x6c));
    run.put(self + 0x60, 0);
    run.put(self + 0x64, 0);
    run.put(self + 0x0, 0x50e864);
    run.call(0x4c7970, run.get(self + 0x2c), {0x528a4c});
    uint32_t scene = run.get(run.get(self + 0x2c) + 0xc);
    uint32_t table = run.get(scene + 0x28) + 0x10;
    uint32_t out = run.automatic(4);
    run.put(out, 0);
    run.call(0x4f6286, table, {0x528a3c, out});
    run.put(self + 0x5c, run.get(out));
    uint32_t flagged = run.get(self + 0x2c);
    uint32_t flags = run.get(flagged + 0x8);
    run.put(flagged + 0x8, flags | 1);
    run.put(run.get(self + 0x2c) + 0xd0, 0x80);
    run.put(run.get(self + 0x2c) + 0xd4, 0x3000072);
    run.call(0x406290, run.get(self + 0x2c), {});
    uint32_t source = run.get(0x537960) + 0x98;
    uint32_t dest = run.get(self + 0xc) + 0x128;
    run.put(dest + 0x0, run.get(source + 0x0));
    run.put(dest + 0x4, run.get(source + 0x4));
    run.put(dest + 0x8, run.get(source + 0x8));
    run.put(dest + 0xc, run.get(source + 0xc));
    uint32_t mover = run.get(self + 0xc);
    uint32_t extent = run.get(mover + 0x134);
    run.put(mover + 0x134, extent + 0x20);
    uint32_t body = run.get(self + 0xc);
    run.put(self + 0x4c, run.get(body + 0x4c));
    uint32_t root = run.get(0x537e88);
    uint32_t serialOwner = run.get(run.get(root + 0x6c) + 0x14);
    run.put(self + 0x48, run.get(serialOwner + 0x80));
    run.put(self + 0x54, run.get(body + 0x148));
    run.put(self + 0x68, 0);
    enterIdle(run, self);
    return self;
}

void lookupState(Run &run, uint32_t self, uint32_t name) {
    run.put(self + 0x24, run.get(run.get(self + 0x10) + 0x1c));
    uint32_t found = run.call(0x4dba00, 0x537668, {name});
    run.put(run.get(self + 0x10) + 0x1c, found);
}

void playSound(Run &run, uint32_t self) {
    uint32_t sound = run.get(self + 0x5c);
    if (sound == 0)
        return;
    uint32_t enabled = run.get(0x532c0c);
    uint32_t argument = run.get(0x532c10);
    if (enabled == 0)
        return;
    run.call(0x4b45f0, run.get(sound + 0x10), {argument, 0, 0, 0});
}

// 0x45a940.
uint32_t enterIdle(Run &run, uint32_t self) {
    run.put(run.get(self + 0xc) + 0x158, 0);
    run.put(run.get(self + 0xc) + 0x15c, 0);
    lookupState(run, self, 0x523604);
    return 0;
}

// 0x45ac40.
void reset(Run &run, uint32_t self) {
    if (run.get(0x537b14) == 0)
        return;
    uint32_t actor = run.get(self + 0xc);
    run.put(actor + 0x4c, run.get(self + 0x4c));
    actor = run.get(self + 0xc);
    run.put(actor + 0x158, 0);
    run.put(self + 0x68, 0);
    uint32_t player = run.get(0x537b14);
    run.put(player + 0x4bc, 0);
    uint32_t playerActor = run.get(player + 0xc);
    run.put(player + 0x4c0, run.get(playerActor + 0x10c));
    uint32_t root = run.get(0x537e88);
    uint32_t serialOwner = run.get(run.get(root + 0x6c) + 0x14);
    run.put(self + 0x48, run.get(serialOwner + 0x80));
    enterIdle(run, self);
}

// 0x45a9f0.
uint32_t enterOpening(Run &run, uint32_t self) {
    lookupState(run, self, 0x528a08);
    playSound(run, self);
    return 0;
}

// 0x45aa90.
uint32_t enterClosing(Run &run, uint32_t self) {
    lookupState(run, self, 0x528a14);
    playSound(run, self);
    return 0;
}

// 0x45a980.
uint32_t idle(Run &run, uint32_t self) {
    uint32_t player = run.get(0x537b14);
    if (player == 0)
        return 0;
    uint32_t root = run.get(0x537e88);
    uint32_t serialOwner = run.get(run.get(root + 0x6c) + 0x14);
    if (run.get(self + 0x48) != run.get(serialOwner + 0x80)) {
        reset(run, self);
        player = run.get(0x537b14);
    }
    if (player == 0)
        return 0;
    uint32_t pressed = run.get(player + 0x4b4);
    if (pressed != 0) {
        if (run.get(self + 0x68) == 0) {
            enterOpening(run, self);
            return 0;
        }
        return 0;
    }
    if (run.get(self + 0x68) != 0)
        enterClosing(run, self);
    return 0;
}

// 0x45aa40.
uint32_t opening(Run &run, uint32_t self) {
    if (run.get(0x537b14) == 0)
        return 0;
    uint32_t actor = run.get(self + 0xc);
    uint32_t direction = run.get(actor + 0x110);
    uint32_t done = 0;
    if (s32(direction) < 0)
        done = moveTowardHigh(run, self);
    else
        done = moveTowardLow(run, self);
    if (done == 0)
        return 0;
    run.put(self + 0x68, 1);
    uint32_t player = run.get(0x537b14);
    run.put(player + 0x4bc, 1);
    enterIdle(run, self);
    return 0;
}

// 0x45aae0.
uint32_t closing(Run &run, uint32_t self) {
    if (run.get(0x537b14) == 0)
        return 0;
    uint32_t actor = run.get(self + 0xc);
    uint32_t direction = run.get(actor + 0x110);
    uint32_t done = 0;
    if (s32(direction) >= 0)
        done = moveTowardHigh(run, self);
    else
        done = moveTowardLow(run, self);
    if (done == 0)
        return 0;
    run.put(self + 0x68, 0);
    uint32_t player = run.get(0x537b14);
    run.put(player + 0x4bc, 0);
    uint32_t playerActor = run.get(player + 0xc);
    run.put(player + 0x4c0, run.get(playerActor + 0x10c));
    enterIdle(run, self);
    return 0;
}

// 0x45ab40.
uint32_t moveTowardLow(Run &run, uint32_t self) {
    uint32_t logic = run.get(self + 0x10);
    uint32_t actor = run.get(self + 0xc);
    uint32_t limit = run.get(logic + 0x2c);
    uint32_t position = run.get(actor + 0x4c);
    if (s32(position) > s32(limit)) {
        uint32_t step = movementStep(run, actor);
        run.put(actor + 0x158, 0u - step);
    } else {
        run.put(actor + 0x158, 0);
    }
    actor = run.get(self + 0xc);
    uint32_t step = run.get(actor + 0x158);
    if (s32(step) < -0x10)
        step = 0xfffffff0u;
    run.put(actor + 0x158, step);
    actor = run.get(self + 0xc);
    step = run.get(actor + 0x158);
    uint32_t moved = run.get(actor + 0x4c) + step;
    run.put(actor + 0x4c, moved);
    logic = run.get(self + 0x10);
    actor = run.get(self + 0xc);
    uint32_t target = run.get(logic + 0x2c);
    uint32_t now = run.get(actor + 0x4c);
    return s32(now) <= s32(target) ? 1 : 0;
}

// 0x45abc0.
uint32_t moveTowardHigh(Run &run, uint32_t self) {
    uint32_t logic = run.get(self + 0x10);
    uint32_t actor = run.get(self + 0xc);
    uint32_t limit = run.get(logic + 0x30);
    uint32_t position = run.get(actor + 0x4c);
    if (s32(position) < s32(limit)) {
        uint32_t step = movementStep(run, actor);
        run.put(actor + 0x158, step);
    } else {
        run.put(actor + 0x158, 0);
    }
    actor = run.get(self + 0xc);
    uint32_t step = run.get(actor + 0x158);
    if (s32(step) > 0x10)
        step = 0x10;
    run.put(actor + 0x158, step);
    actor = run.get(self + 0xc);
    step = run.get(actor + 0x158);
    uint32_t moved = run.get(actor + 0x4c) + step;
    run.put(actor + 0x4c, moved);
    logic = run.get(self + 0x10);
    actor = run.get(self + 0xc);
    uint32_t target = run.get(logic + 0x30);
    uint32_t now = run.get(actor + 0x4c);
    return s32(now) >= s32(target) ? 1 : 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x45a400:
        dispatchState(run, receiver, arguments[0]);
        return 0;
    case 0x45a7c0:
        return construct(run, receiver, arguments[0]);
    case 0x45a940:
        return enterIdle(run, receiver);
    case 0x45a980:
        return idle(run, receiver);
    case 0x45a9f0:
        return enterOpening(run, receiver);
    case 0x45aa40:
        return opening(run, receiver);
    case 0x45aa90:
        return enterClosing(run, receiver);
    case 0x45aae0:
        return closing(run, receiver);
    case 0x45ab40:
        return moveTowardLow(run, receiver);
    case 0x45abc0:
        return moveTowardHigh(run, receiver);
    case 0x45ac40:
        reset(run, receiver);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_ten_marrow_floor_entry, owned, body)
