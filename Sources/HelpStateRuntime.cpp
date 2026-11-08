// Help screen state (F1 and in-game Help)
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
    case 0x449870:
        return 3;
    case 0x449930:
        return 0;
    case 0x449940:
        return 1;
    case 0x4499d0:
        return 1;
    case 0x449a60:
        return 0;
    case 0x449b30:
        return 0;
    case 0x449b70:
        return 0;
    case 0x449bd0:
        return 2;
    case 0x449c10:
        return 3;
    default:
        return -1;
    }
}

// Import slots: SetCursor, PostMessageA, ShowCursor.
constexpr uint32_t kSetCursor = 0x546cd8;
constexpr uint32_t kPostMessageA = 0x546d50;
constexpr uint32_t kShowCursor = 0x546d54;
// Global input object pointer.
constexpr uint32_t kInput = 0x537200;

// Callee-entry ESP (return word included) as a depth below the owned
// function's entry ESP.
void depth(Run &run, uint32_t bytes) {
    run.stackPointer = run.frame - bytes;
}

// ShowCursor(0) once, then again while the result is not negative.
void hideCursor(Run &run, uint32_t bytes) {
    depth(run, bytes);
    int32_t count = s32(run.icall(kShowCursor, {0}));
    if (count < 0)
        return;
    do {
        count = s32(run.icall(kShowCursor, {0}));
    } while (count >= 0);
}

// PostMessageA(hwnd, WM_COMMAND, 0x8036, 0) with hwnd = [[application + 4] + 4].
void postHelpCommand(Run &run, uint32_t application, uint32_t bytes) {
    uint32_t window = run.get(application + 0x04);
    uint32_t hwnd = run.get(window + 0x04);
    depth(run, bytes);
    run.icall(kPostMessageA, {hwnd, 0x111, 0x8036, 0});
}

// 0x449870. Init: base init, load HELP resources and sounds.
uint32_t function_449870(Run &run, uint32_t receiver, const uint32_t *arguments) {
    depth(run, 0x14);
    uint32_t first = run.call(0x48f0d0, receiver, {arguments[0], arguments[1], arguments[2]});
    if (first == 0)
        return first;
    depth(run, 0x0c);
    run.icall(kSetCursor, {0});
    // +0x04 application
    run.call(0x42a000, run.get(receiver + 0x04), {0});
    // +0x08 resource manager, +0x20 and +0x24 resource handles
    uint32_t help = run.call(0x4b7f20, run.get(receiver + 0x08), {0x527b34});
    run.put(receiver + 0x20, help);
    if (help == 0)
        return 0;
    uint32_t claw = run.call(0x4b7f20, run.get(receiver + 0x08), {0x523734});
    run.put(receiver + 0x24, claw);
    if (claw == 0)
        return 0;
    // +0x0c world, +0x28 sound manager, +0x2c sound list
    uint32_t soundManager = run.get(run.get(receiver + 0x0c) + 0x28);
    uint32_t list = run.get(soundManager + 0x2c);
    if (list != 0) {
        depth(run, 0x08);
        run.call(0x4b4b40, list, {});
    }
    depth(run, 0x0c);
    uint32_t node = run.call(0x4b68c0, run.get(receiver + 0x20), {0x52372c});
    if (node == 0)
        return 0;
    soundManager = run.get(run.get(receiver + 0x0c) + 0x28);
    depth(run, 0x14);
    run.call(0x4ca440, soundManager, {node, 0x534938, 0x523728});
    uint32_t application = run.get(receiver + 0x04);
    depth(run, 0x10);
    run.call(0x4b8910, run.get(application + 0x04), {0x100, 0x40});
    return 1;
}

// 0x449930. Tail jump to the base cleanup 0x48f180.
uint32_t function_449930(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    depth(run, 0);
    return run.call(0x48f180, receiver, {});
}

// 0x449940. Enter: hide cursor, start the transition, load the HELP screen.
uint32_t function_449940(Run &run, uint32_t receiver, const uint32_t *arguments) {
    hideCursor(run, 0x10);
    uint32_t index = arguments[0] - 2;
    // Jump table at 0x4499ac: arguments 2, 5, 8 and 9 take the transition path.
    bool transition = index <= 7 && ((0xC9u >> index) & 1) != 0;
    if (transition) {
        depth(run, 0x10);
        run.call(0x48f500, receiver, {700});
        depth(run, 0x20);
        run.call(0x48f740, receiver, {0x527b40, 0, 0, 0, 700});
    } else {
        depth(run, 0x20);
        run.call(0x48f740, receiver, {0x527b40, 0, 500, 500, 700});
    }
    return 1;
}

// 0x4499d0. Palette fade and two flips for arguments 3, 4 and 11.
uint32_t function_4499d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    int32_t mode = s32(arguments[0]);
    if (mode < 3)
        return 1;
    if (mode > 4 && mode != 0xb)
        return 1;
    // +0x2c screen image, +0x10 palette
    uint32_t image = run.get(receiver + 0x2c);
    if (image == 0)
        return 1;
    uint32_t palette = run.get(image + 0x10);
    depth(run, 0x24);
    run.call(0x4bb990, palette, {0, 0x100, 0, 0, 0, 0x1f4});
    for (int pass = 0; pass < 2; ++pass) {
        // +0x0c world, +0x04 display, +0x10 and +0x14 primary and secondary
        uint32_t display = run.get(run.get(receiver + 0x0c) + 0x04);
        uint32_t second = run.get(run.get(display + 0x14) + 0x2c);
        depth(run, 0x10);
        run.call(0x4b97c0, second, {0});
        uint32_t first = run.get(run.get(display + 0x10) + 0x2c);
        depth(run, 0x10);
        run.call(0x4b98b0, first, {0});
    }
    return 1;
}

// 0x449a60. Per-frame update.
uint32_t function_449a60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t display = run.get(run.get(receiver + 0x0c) + 0x04);
    uint32_t surface = run.get(run.get(run.get(display + 0x10) + 0x2c) + 0x08);
    bool restore = true;
    if (surface != 0) {
        uint32_t method = run.get(run.get(surface) + 0x60);
        depth(run, 0x0c);
        uint32_t lost = run.call(method, 0, {surface});
        if (lost == 0)
            restore = false;
    }
    if (restore) {
        depth(run, 0x08);
        uint32_t result = run.vcall(receiver, 0x18, {});
        if (result == 0) {
            depth(run, 0x10);
            run.call(0x429e10, run.get(receiver + 0x04), {0x8006, 0x1388});
            return 0;
        }
    }
    uint32_t image = run.get(receiver + 0x2c);
    if (image != 0) {
        uint32_t palette = run.get(image + 0x10);
        if (run.get(palette + 0x34) != 0) {
            depth(run, 0x08);
            run.call(0x4bbb70, palette, {});
            uint32_t again = run.get(run.get(receiver + 0x2c) + 0x10);
            if (run.get(again + 0x34) == 0) {
                depth(run, 0x0c);
                run.icall(kSetCursor, {0});
            }
        }
    }
    uint32_t soundManager = run.get(run.get(receiver + 0x0c) + 0x28);
    uint32_t list = run.get(soundManager + 0x2c);
    if (list != 0) {
        depth(run, 0x08);
        run.call(0x4b4b80, list, {});
    }
    depth(run, 0x08);
    run.call(0x4b3490, run.get(kInput), {});
    uint32_t input = run.get(kInput);
    if ((run.get(input + 0x210) & 0x00ffffff) != 0) {
        uint32_t application = run.get(receiver + 0x04);
        postHelpCommand(run, application, 0x18);
        run.put(run.get(application + 0x08) + 0x244, 0);
    }
    return 1;
}

// 0x449b30. Redraw.
uint32_t function_449b30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t display = run.get(run.get(receiver + 0x0c) + 0x04);
    depth(run, 0x08);
    if (run.call(0x4ca930, display, {}) == 0)
        return 0;
    depth(run, 0x10);
    run.icall(kSetCursor, {0});
    depth(run, 0x20);
    uint32_t result = run.call(0x48f3e0, receiver, {0x527b40, 0, 0, 1, 0});
    depth(run, 0x10);
    run.icall(kSetCursor, {0});
    return result;
}

// 0x449b70. Resume.
uint32_t function_449b70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    depth(run, 0x0c);
    uint32_t ready = run.vcall(receiver, 0x0c, {});
    if (ready == 0)
        return ready;
    if (run.get(receiver + 0x2c) == 0)
        return 0;
    hideCursor(run, 0x10);
    depth(run, 0x20);
    uint32_t result = run.call(0x48f3e0, receiver, {0x527b40, 0, 0, 1, 0});
    depth(run, 0x10);
    uint32_t done = run.call(0x48f470, receiver, {0xfa});
    return done != 0 ? result : 0;
}

// 0x449bd0. Key handler: Esc, Space and Enter post the command.
uint32_t function_449bd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t key = arguments[0];
    if (key == 0x1b || key == 0x20 || key == 0x0d)
        postHelpCommand(run, run.get(receiver + 0x04), 0x14);
    return 1;
}

// 0x449c10. Mouse handler: always posts the command.
uint32_t function_449c10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    postHelpCommand(run, run.get(receiver + 0x04), 0x14);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x449870:
        return function_449870(run, receiver, arguments);
    case 0x449930:
        return function_449930(run, receiver, arguments);
    case 0x449940:
        return function_449940(run, receiver, arguments);
    case 0x4499d0:
        return function_4499d0(run, receiver, arguments);
    case 0x449a60:
        return function_449a60(run, receiver, arguments);
    case 0x449b30:
        return function_449b30(run, receiver, arguments);
    case 0x449b70:
        return function_449b70(run, receiver, arguments);
    case 0x449bd0:
        return function_449bd0(run, receiver, arguments);
    case 0x449c10:
        return function_449c10(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_help_state_entry, owned, body)
