// Level 3 rope controller, recovered from the original v1.0 corpus.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x403100:
    case 0x4031c0:
    case 0x4035a0:
    case 0x403850:
        return 1;
    case 0x4038d0:
    case 0x465450:
        return 0;
    default:
        return -1;
    }
}

ClawX87State emptyFP() {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    return fp;
}

void receipt(ClawX87State &fp, uint32_t pop, uint32_t push) {
    fp.popCount = pop;
    fp.pushCount = push;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
}

// 0x465450. +0x10 logic owner; +0x24 previous state id.
uint32_t function_465450(Run &run, uint32_t self) {
    run.put(self + 0x24, run.get(run.get(self + 0x10) + 0x1c));
    uint32_t idle = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(self + 0x10) + 0x1c, idle);
    return 0;
}

// 0x4031c0. +0x08/+0x0c object; +0x28/+0x2c rope object;
// +0x30 rope logic; +0x48 through +0x134 motion state.
uint32_t function_4031c0(Run &run, uint32_t self, uint32_t object) {
    run.put(self + 0x00, 0x50b064);
    run.put(self + 0x08, object);
    run.put(self + 0x0c, object);
    run.put(self + 0x10, run.get(object + 0x6c));
    run.put(self + 0x04, 0);
    run.call(0x4c7fa0, object, {0x522d54});
    run.call(0x4c8060, run.get(self + 0x0c), {0x522d48});
    run.put(self + 0x14, 0);
    run.put(self + 0x18, 0);
    run.put(self + 0x1c, 0x3e9);
    run.put(self + 0x20, 2);
    run.put(self + 0x28, object);
    run.put(self + 0x2c, object);
    run.put(self + 0x30, run.get(object + 0x6c));
    run.put(self + 0x88, 0);
    run.put(self + 0x90, 0);
    run.put(self + 0x98, 0);
    run.put(self + 0x70, 0);
    run.put(self + 0x78, 0);
    run.put(self + 0x80, 0);
    run.put(self + 0x58, 0);
    run.put(self + 0x60, 0);
    run.put(self + 0x68, 0);
    run.put(self + 0x48, 0);
    run.put(self + 0x50, 0);
    run.put(self + 0xf0, 0);
    run.put(self + 0xf8, 0);
    run.put(self + 0x100, 0);
    run.put(self + 0x8c, 0);
    run.put(self + 0x94, 0);
    run.put(self + 0x9c, 0);
    run.put(self + 0x74, 0);
    run.put(self + 0x7c, 0);
    run.put(self + 0x84, 0);
    run.put(self + 0x5c, 0);
    run.put(self + 0x64, 0);
    run.put(self + 0x6c, 0);
    run.put(self + 0x4c, 0);
    run.put(self + 0x54, 0);
    run.put(self + 0xf4, 0);
    run.put(self + 0xfc, 0);
    run.put(self + 0x104, 0);
    run.put(self + 0xe8, 0);
    {
        uint32_t low = run.get(0x513e10);
        uint32_t high = run.get(0x513e14);
        run.put(self + 0xa0, low);
        run.put(self + 0xa4, high);
    }
    {
        uint32_t low = run.get(0x513e18);
        uint32_t high = run.get(0x513e1c);
        run.put(self + 0xb8, low);
        run.put(self + 0xbc, high);
    }
    {
        uint32_t low = run.get(0x513e10);
        uint32_t high = run.get(0x513e14);
        run.put(self + 0xa8, low);
        run.put(self + 0xac, high);
    }
    {
        uint32_t low = run.get(0x513e18);
        uint32_t high = run.get(0x513e1c);
        run.put(self + 0xc0, low);
        run.put(self + 0xc4, high);
    }
    {
        uint32_t low = run.get(0x513e10);
        uint32_t high = run.get(0x513e14);
        run.put(self + 0xb0, low);
        run.put(self + 0xb4, high);
    }
    {
        uint32_t low = run.get(0x513e18);
        uint32_t high = run.get(0x513e1c);
        run.put(self + 0xc8, low);
        run.put(self + 0xcc, high);
    }
    {
        uint32_t low = run.get(0x513e18);
        uint32_t high = run.get(0x513e1c);
        run.put(self + 0x108, low);
        run.put(self + 0x10c, high);
    }
    {
        uint32_t low = run.get(0x513e18);
        uint32_t high = run.get(0x513e1c);
        run.put(self + 0x110, low);
        run.put(self + 0x114, high);
    }
    {
        uint32_t low = run.get(0x513e18);
        uint32_t high = run.get(0x513e1c);
        run.put(self + 0x118, low);
        run.put(self + 0x11c, high);
    }
    {
        uint32_t low = run.get(0x513e18);
        uint32_t high = run.get(0x513e1c);
        run.put(self + 0x120, low);
        run.put(self + 0x124, high);
    }
    {
        uint32_t low = run.get(0x513e18);
        uint32_t high = run.get(0x513e1c);
        run.put(self + 0x128, low);
        run.put(self + 0x12c, high);
    }
    {
        uint32_t low = run.get(0x513e18);
        uint32_t high = run.get(0x513e1c);
        run.put(self + 0x130, low);
        run.put(self + 0x134, high);
    }
    run.put(self + 0x00, 0x50b03c);
    run.call(0x4c7970, run.get(self + 0x2c), {0x52313c});
    uint32_t owner = run.get(self + 0x0c);
    if (run.get(owner + 0x64) == 0 && run.get(owner + 0x64) != 0xf96) {
        run.put(owner + 0x64, 0xf96);
        run.put(owner + 0x08, run.get(owner + 0x08) | 0x20000);
    }
    owner = run.get(self + 0x0c);
    run.put(self + 0x138, 0);
    if (run.get(owner + 0x148) == 0)
        run.put(owner + 0x148, 0x5dc);
    run.put(run.get(self + 0x2c) + 0xd0, 0x100);
    run.put(run.get(self + 0x0c) + 0xfc, 0x26af);
    {
        uint32_t low = run.get(0x513e18);
        uint32_t high = run.get(0x513e1c);
        run.put(self + 0x108, low);
        run.put(self + 0x10c, high);
    }
    {
        uint32_t low = run.get(0x513e18);
        uint32_t high = run.get(0x513e1c);
        run.put(self + 0x110, low);
        run.put(self + 0x114, high);
    }
    {
        uint32_t low = run.get(0x513e18);
        uint32_t high = run.get(0x513e1c);
        run.put(self + 0x118, low);
        run.put(self + 0x11c, high);
    }
    uint32_t period = uint32_t(60000 / int64_t(run.gets(run.get(self + 0x0c) + 0x148)));
    uint32_t scale = run.get(run.get(self + 0x10) + 0xbc);
    run.put(self + 0x90, 0);
    run.put(self + 0x98, 0);
    run.put(self + 0x78, 0);
    run.put(self + 0x80, 0);
    run.put(self + 0x58, 0);
    run.put(self + 0x60, 0);
    run.put(self + 0x68, 0);
    run.put(self + 0x48, 0);
    run.put(self + 0x50, 0);
    run.put(self + 0x94, 0);
    run.put(self + 0x9c, 0);
    run.put(self + 0x7c, 0);
    run.put(self + 0x84, 0);
    run.put(self + 0x5c, 0);
    run.put(self + 0x64, 0);
    run.put(self + 0x6c, 0);
    run.put(self + 0x4c, 0);
    run.put(self + 0x54, 0);
    run.putd(self + 0x88, double(s32(scale * period) / 1000));
    run.putd(self + 0x70, double(s32(period)));
    function_465450(run, self);
    return self;
}

// 0x403100. +0x6c logic; logic +0x18 controller, +0x1c state.
uint32_t function_403100(Run &run, uint32_t object) {
    uint32_t logic = run.get(object + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (state == 0) {
        run.put(logic + 0x1c, 0x3e8);
        uint32_t controller = run.call(0x4f63ec, 0, {0x148});
        if (controller)
            controller = function_4031c0(run, controller, object);
        run.vcall(controller, 0x10);
        run.put(logic + 0x18, controller);
    } else if (state == 0x1d) {
        run.vcall(run.get(logic + 0x18), 0x20);
    } else if (state == 0x1e) {
        run.vcall(run.get(logic + 0x18), 0x1c);
    } else if (state != 0x3e8) {
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
    }
    return 1;
}

uint32_t stateEntry(Run &run, uint32_t state) {
    uint32_t low = run.get(0x534828);
    if (s32(state) < s32(low) || s32(state) > run.gets(0x53482c)) {
        if (!run.call(0x4db6e0, 0x534820, {state, 0})) {
            uint32_t message = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0);
            run.put(0x544b14, error);
            run.call(0x4db4d0, run.get(0x534824), {0x534820, message, 0xc});
            return run.get(0x534834);
        }
        low = run.get(0x534828);
    }
    return (state - low) * run.get(0x534838) + run.get(0x534830);
}

// 0x4035a0. The global state table stores one callback per entry.
uint32_t function_4035a0(Run &run, uint32_t self, uint32_t state) {
    run.put(0x534840, 0);
    uint32_t entry = stateEntry(run, state);
    if (run.get(entry)) {
        run.put(0x534840, 0);
        entry = stateEntry(run, state);
        return run.call(run.get(entry), self);
    }
    return run.call(0x4a36f0, 0, {self});
}

// 0x403850. +0x14 current callback, +0x18 leave callback, +0x1c state.
uint32_t function_403850(Run &run, uint32_t self) {
    if (run.get(self + 0x14)) {
        uint32_t leave = run.get(self + 0x18);
        if (leave && run.get(run.get(self + 0x10) + 0x1c) == run.get(self + 0x1c)) {
            run.call(leave, self);
            run.put(self + 0x18, 0);
        }
        run.call(run.get(self + 0x14), self);
        run.put(self + 0x14, 0);
        run.put(self + 0x1c, 0x3e9);
    }
    double clock = double(run.get(0x537210));
    uint64_t bits;
    std::memcpy(&bits, &clock, sizeof(bits));
    auto fp = emptyFP();
    run.x87_step(CLAW_X87_F64, fp, {uint32_t(bits), uint32_t(bits >> 32)});
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50b088), run.get(0x50b08c)});
    run.x87_step(CLAW_X87_SUB_F64, fp, {run.get(self + 0x48), run.get(self + 0x4c)});
    uint64_t delta = run.x87_step(CLAW_X87_STP_F64, fp);
    receipt(fp, 0, 0);
    return run.call_x87_exact(0x403b40, self + 0x48, fp, {uint32_t(delta), uint32_t(delta >> 32)});
}

// 0x4038d0. +0x88 phase, +0x138 animation frame, +0x13c half-cycle;
// object +0x138..+0x144 bounds, controller +0x140/+0x144 anchor.
uint32_t function_4038d0(Run &run, uint32_t self) {
    auto fp = emptyFP();
    run.x87_step(CLAW_X87_F64, fp, {run.get(self + 0x88), run.get(self + 0x8c)});
    receipt(fp, 1, 0);
    uint32_t phase = run.call_x87_exact(0x4a30e0, 0, fp);
    uint32_t frame = uint32_t(s32(phase) % 120) + 1;
    run.put(self + 0x138, frame);
    bool reverse = s32(frame) > 60;
    uint32_t half = reverse ? frame - 60 : frame;
    run.put(self + 0x13c, half);
    uint32_t y = run.get(0x522f0c + half * 8);
    uint32_t x = run.get(0x522f08 + half * 8);
    uint32_t object = run.get(self + 0x2c);
    if (reverse) {
        run.put(object + 0x138, 0xa7 - x);
        run.put(object + 0x13c, y - 0x9e);
        run.put(object + 0x140, 0xc1 - x);
        run.put(object + 0x144, y - 0x7d);
    } else {
        run.put(object + 0x138, x - 0xc1);
        run.put(object + 0x13c, y - 0x9e);
        run.put(object + 0x140, x - 0xa7);
        run.put(object + 0x144, y - 0x7d);
    }
    half = run.get(self + 0x13c);
    uint32_t owner = run.get(self + 0x0c);
    x = run.get(0x522f08 + half * 8);
    run.put(self + 0x140, reverse ? 0xb4 - x : x - 0xb4);
    y = run.get(0x522f0c + half * 8);
    run.put(self + 0x144, y - 0x96);
    uint32_t player = run.get(0x537e88);
    uint32_t logic = run.get(player + 0x6c);
    uint32_t playerState = run.get(logic + 0x14);
    if (run.get(playerState + 0x134) == owner && run.get(logic + 0x1c) == 0x138f)
        run.call(reverse ? 0x418080 : 0x418120, 0, {player, logic, playerState});
    frame = run.get(self + 0x138);
    object = run.get(self + 0x2c);
    uint32_t animation = run.get(object + 0x170);
    if (animation) {
        uint32_t image = 0;
        if (s32(frame) >= run.gets(animation + 0x64) && s32(frame) <= run.gets(animation + 0x68))
            image = run.get(run.get(animation + 0x14) + frame * 4);
        run.put(object + 0x16c, frame);
        run.put(object + 0x174, image);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x403100:
        return function_403100(run, arguments[0]);
    case 0x4031c0:
        return function_4031c0(run, receiver, arguments[0]);
    case 0x4035a0:
        return function_4035a0(run, receiver, arguments[0]);
    case 0x403850:
        return function_403850(run, receiver);
    case 0x4038d0:
        return function_4038d0(run, receiver);
    case 0x465450:
        return function_465450(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_three_rope_entry, owned, body)
