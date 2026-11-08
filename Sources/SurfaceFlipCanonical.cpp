// Original surface Flip presentation wrapper
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4b98b0:
        return 1;
    default:
        return -1;
    }
}

// 0x4b98b0 Surface::flip. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4b98b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Wrapper +0x08 is its DirectDraw interface; capture the source once.
    uint32_t source = arguments[0] ? run.get(arguments[0] + 0x08) : 0;
    uint32_t surface = run.get(receiver + 0x08);
    // Interface vtable +0x2c is stdcall Flip(interface, source, flags).
    uint32_t method = run.get(run.get(surface) + 0x2c);
    // Three saved registers, three arguments and CALL's return word.
    run.stackPointer = run.frame - 0x1c;
    uint32_t result = run.call(method, 0, {surface, source, 1});
    if (!result)
        return 0;
    if (result != 0x887601c2) {
        run.call(0x4bd260, 0, {0x5324dc, 0x29a, result});
        return result;
    }
    // Wrapper vtable +0x1c is its restore method, reloaded after Flip.
    run.stackPointer = run.frame - 0x10;
    uint32_t restored = run.vcall(receiver, 0x1c, {});
    if (!restored)
        return result;
    surface = run.get(receiver + 0x08);
    method = run.get(run.get(surface) + 0x2c);
    run.stackPointer = run.frame - 0x1c;
    result = run.call(method, 0, {surface, source, 1});
    if (result)
        run.call(0x4bd260, 0, {0x5324dc, 0x294, result});
    return result;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b98b0:
        return function_4b98b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_surface_flip_canonical_entry, owned, body)
