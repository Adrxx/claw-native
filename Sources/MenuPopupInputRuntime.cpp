// Original popup input forwarding and saved-state stack

#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4392d0:
        return 2;
    case 0x439390:
        return 2;
    case 0x4393c0:
        return 3;
    case 0x439400:
        return 3;
    case 0x439440:
        return 3;
    case 0x42bfd0:
        return 0;
    case 0x42bff0:
        return 1;
    case 0x42c010:
        return 1;
    default:
        return -1;
    }
}

// 0x4392d0. thiscall, 2 stack argument(s), returns u32.
uint32_t function_4392d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Receiver +0x160 is the active popup.
    uint32_t popup = run.get(receiver + 0x160);
    if (!popup)
        return 1;
    uint32_t key = arguments[0];
    switch (key) {
    case 0x1b:
        run.call(0x4398c0, receiver, {0x5254dc, 0});
        popup = run.get(receiver + 0x160);
        run.vcall(popup, 0x1f0);
        break;
    case 0x0d:
    case 0x20:
    case 0x23:
    case 0x24:
    case 0x25:
    case 0x26:
    case 0x27:
    case 0x28:
    case 0x2e:
        run.vcall(popup, 0x198, {key, arguments[1]});
        break;
    default:
        run.call(0x424de0, popup, {key, arguments[1]});
        break;
    }
    return 1;
}

// 0x439390. thiscall, 2 stack argument(s), returns u32.
uint32_t function_439390(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t popup = run.get(receiver + 0x160);
    if (popup)
        run.vcall(popup, 0x19c, {arguments[0], arguments[1]});
    return 1;
}

// 0x4393c0. thiscall, 3 stack argument(s), returns u32.
uint32_t function_4393c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t popup = run.get(receiver + 0x160);
    if (popup) {
        // Popup +0x294 and +0x298 are the coordinate origin.
        uint32_t x = arguments[1] - run.get(popup + 0x294);
        uint32_t y = arguments[2] - run.get(popup + 0x298);
        run.vcall(popup, 0x190, {x, y});
    }
    return 1;
}

// 0x439400. thiscall, 3 stack argument(s), returns u32.
uint32_t function_439400(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t popup = run.get(receiver + 0x160);
    if (popup) {
        // Popup +0x294 and +0x298 are the coordinate origin.
        uint32_t x = arguments[1] - run.get(popup + 0x294);
        uint32_t y = arguments[2] - run.get(popup + 0x298);
        run.vcall(popup, 0x194, {x, y});
    }
    return 1;
}

// 0x439440. thiscall, 3 stack argument(s), returns u32.
uint32_t function_439440(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t popup = run.get(receiver + 0x160);
    if (popup) {
        // Popup +0x294 and +0x298 are the coordinate origin.
        uint32_t x = arguments[1] - run.get(popup + 0x294);
        uint32_t y = arguments[2] - run.get(popup + 0x298);
        run.vcall(popup, 0x18c, {x, y});
    }
    return 1;
}

// 0x42bfd0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_42bfd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Saved array +0xe4 is its signed count; +0xe0 is its word buffer.
    (void)arguments;
    uint32_t count = run.get(receiver + 0xe4);
    if (s32(count) <= 0)
        return 0;
    return run.get(run.get(receiver + 0xe0) + count * 4 - 4);
}

// 0x42bff0. thiscall, 1 stack argument(s), returns void.
uint32_t function_42bff0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Saved array object starts at receiver +0xdc.
    if (arguments[0])
        run.call(0x4f582f, receiver + 0xdc, {run.get(receiver + 0xe4), arguments[0]});
    return 0;
}

// 0x42c010. thiscall, 1 stack argument(s), returns u32.
uint32_t function_42c010(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!arguments[0])
        return 0;
    uint32_t count = run.get(receiver + 0xe4);
    if (s32(count) <= 0)
        return 0;
    uint32_t index = count - 1;
    uint32_t last = run.get(run.get(receiver + 0xe0) + index * 4);
    run.call(0x4f55e9, receiver + 0xdc, {index, 1});
    return last == arguments[0] ? 1 : 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4392d0:
        return function_4392d0(run, receiver, arguments);
    case 0x439390:
        return function_439390(run, receiver, arguments);
    case 0x4393c0:
        return function_4393c0(run, receiver, arguments);
    case 0x439400:
        return function_439400(run, receiver, arguments);
    case 0x439440:
        return function_439440(run, receiver, arguments);
    case 0x42bfd0:
        return function_42bfd0(run, receiver, arguments);
    case 0x42bff0:
        return function_42bff0(run, receiver, arguments);
    case 0x42c010:
        return function_42c010(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_menu_popup_input_entry, owned, body)
