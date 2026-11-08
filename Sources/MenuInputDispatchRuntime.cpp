// Application menu input forwarding, recovered from the original v1.0 entries.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x429d60:
        return 2;
    case 0x429d80:
    case 0x429db0:
    case 0x429de0:
        return 3;
    default:
        return -1;
    }
}

// 0x429d60. Forward two arguments to the menu's virtual input method.
uint32_t function_429d60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Application +0x2c: current menu object.
    uint32_t menu = run.get(receiver + 0x2c);
    if (!menu)
        return 0;
    return run.vcall(menu, 0x30, {arguments[0], arguments[1]});
}

// 0x429d80. Forward three arguments to virtual slot +0x34.
uint32_t function_429d80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t menu = run.get(receiver + 0x2c);
    if (!menu)
        return 0;
    return run.vcall(menu, 0x34, {arguments[0], arguments[1], arguments[2]});
}

// 0x429db0. Forward three arguments to virtual slot +0x38.
uint32_t function_429db0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t menu = run.get(receiver + 0x2c);
    if (!menu)
        return 0;
    return run.vcall(menu, 0x38, {arguments[0], arguments[1], arguments[2]});
}

// 0x429de0. Forward three arguments to virtual slot +0x3c.
uint32_t function_429de0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t menu = run.get(receiver + 0x2c);
    if (!menu)
        return 0;
    return run.vcall(menu, 0x3c, {arguments[0], arguments[1], arguments[2]});
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x429d60:
        return function_429d60(run, receiver, arguments);
    case 0x429d80:
        return function_429d80(run, receiver, arguments);
    case 0x429db0:
        return function_429db0(run, receiver, arguments);
    case 0x429de0:
        return function_429de0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_menu_input_dispatch_entry, owned, body)
