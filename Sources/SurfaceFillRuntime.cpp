// Surface color-fill wrapper.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4b97c0:
        return 1;
    default:
        return -1;
    }
}

// 0x4b97c0 Surface::fill. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4b97c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t fx = run.automatic(-100);
    for (uint32_t offset = 0; offset < 0x64; offset += 4) {
        run.put(fx + offset, 0);
    }
    // DDBLTFX: +0x00 structure size, +0x50 full fill-color word.
    run.put(fx + 0x00, 0x64);
    run.put(fx + 0x50, arguments[0]);
    // Two saved registers, five arguments and the callee return slot.
    run.stackPointer = run.automatic(-132);
    uint32_t result = run.call(0x4b9ce0, receiver, {0, 0, 0, 0x01000400, fx});
    if (result != 0) {
        run.stackPointer = run.automatic(-124);
        run.call(0x4bd260, 0, {0x5324dc, 0x212, result});
    }
    return result == 0 ? 1 : 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b97c0:
        return function_4b97c0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_surface_fill_entry, owned, body)
