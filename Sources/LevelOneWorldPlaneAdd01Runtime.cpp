// Level 1 world add-plane
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
    case 0x4cb7b0:
        return 3;
    default:
        return -1;
    }
}

// 0x4cb7b0. thiscall, 3 stack arguments (the third is unused), returns the new
// plane. Fields of the world (receiver): +0x0c value passed to the plane
// constructor, +0x10 embedded member whose address is passed to the plane's
// virtual method, +0x34 plane list, +0x3c plane count, +0x5c last flagged plane,
// +0x60 index of that plane. Plane fields: +0x08 flags.
uint32_t function_4cb7b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t world = receiver;
    uint32_t memory = run.call(0x4f63ec, 0, {0x158});
    uint32_t plane = 0;
    if (memory) {
        uint32_t count = run.get(world + 0x3c);
        uint32_t value = run.get(world + 0x0c);
        plane = run.call(0x4d03b0, memory, {value, count, 0});
    }
    uint32_t first = arguments[0];
    uint32_t second = arguments[1];
    run.get(plane);
    uint32_t added = run.vcall(plane, 0x28, {first, second, world + 0x10});
    if (!added) {
        if (plane)
            run.vcall(plane, 4, {1});
        return 0;
    }
    uint32_t count = run.get(world + 0x3c);
    run.call(0x4f582f, world + 0x34, {count, plane});
    uint32_t flags = run.get8(plane + 0x08);
    if (flags & 1) {
        run.put(world + 0x5c, plane);
        uint32_t last = run.get(world + 0x3c);
        run.put(world + 0x60, last - 1);
    }
    return plane;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4cb7b0:
        return function_4cb7b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_world_plane_add_01_entry, owned, body)
