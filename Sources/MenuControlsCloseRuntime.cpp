// Controls close dispatch and activation flags
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4247c0:
        return 0;
    case 0x4247e0:
        return 0;
    case 0x424800:
        return 0;
    case 0x42eab0:
        return 1;
    case 0x42eae0:
        return 1;
    default:
        return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

// 0x4247c0. Confirm the close choice, then tail-dispatch the virtual method.
uint32_t function_4247c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(0x52545c, 1);
    // Receiver +0x00 is the vtable; +0x1e8 is its close slot.
    uint32_t target = run.get(run.get(receiver) + 0x1e8);
    if (owned(target) == 0)
        return body(run, target, receiver, arguments);
    return run.call(target, receiver);
}

// 0x4247e0. Cancel the close choice, then tail-dispatch the virtual method.
uint32_t function_4247e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(0x52545c, 2);
    uint32_t target = run.get(run.get(receiver) + 0x1e8);
    if (owned(target) == 0)
        return body(run, target, receiver, arguments);
    return run.call(target, receiver);
}

// 0x424800. Close a modal menu or post the application close command.
uint32_t function_424800(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t modal = run.get(0x5375c4);
    if (modal) {
        run.put(0x5375c0, 1);
        return modal;
    }
    uint32_t application = run.get(0x5371fc);
    if (!application)
        return application;
    // Receiver +0x2b4 holds the close state.
    run.put(receiver + 0x2b4, 2);
    application = run.get(0x5371fc);
    // Application +0x04 points to the window object; its +0x04 is HWND.
    uint32_t window = run.get(application + 0x04);
    uint32_t handle = run.get(window + 0x04);
    return run.icall(0x546d50, {handle, 0x111, 0x8036, 0});
}

// 0x42eab0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_42eab0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // Receiver +0x2bc and +0x2c0 are optional controls, with flags at +0x40.
    uint32_t control = run.get(receiver + 0x2bc);
    if (control)
        run.put(control + 0x40, run.get(control + 0x40) & 0xfffffffeu);
    control = run.get(receiver + 0x2c0);
    if (control)
        run.put(control + 0x40, run.get(control + 0x40) & 0xfffffffeu);
    return 1;
}

// 0x42eae0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_42eae0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t control = run.get(receiver + 0x2bc);
    if (control)
        run.put(control + 0x40, run.get(control + 0x40) | 1u);
    control = run.get(receiver + 0x2c0);
    if (control)
        run.put(control + 0x40, run.get(control + 0x40) | 1u);
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4247c0:
        return function_4247c0(run, receiver, arguments);
    case 0x4247e0:
        return function_4247e0(run, receiver, arguments);
    case 0x424800:
        return function_424800(run, receiver, arguments);
    case 0x42eab0:
        return function_42eab0(run, receiver, arguments);
    case 0x42eae0:
        return function_42eae0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_menu_controls_close_entry, owned, body)
