// Pause menu key release, refresh and state destruction
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
    case 0x44fe40:
        return 1;
    case 0x44fa80:
        return 0;
    case 0x429820:
        return 1;
    case 0x429810:
        return 0;
    case 0x429840:
        return 0;
    default:
        return -1;
    }
}

uint32_t function_429840(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_44fa80(Run &run, uint32_t receiver, const uint32_t *arguments);

// Sets the callee-entry ESP for the next outside call. `below` is the byte
// distance under this function's entry frame, including the return word.
void enter(Run &run, uint32_t below) {
    run.stackPointer = run.frame - below;
}

// Runs an owned function with the frame it has when called from here.
uint32_t owned_call(Run &run, uint32_t below, uint32_t (*function)(Run &, uint32_t, const uint32_t *),
                    uint32_t receiver, const uint32_t *arguments) {
    uint32_t saved = run.frame;
    run.frame = saved - below;
    uint32_t result = function(run, receiver, arguments);
    run.frame = saved;
    return result;
}

// Marks the widget in slot `slot` of the pause menu for destruction and clears
// the slot. Widget +0x08 flags, +0x0c owner whose +0x08 is the manager.
void releaseWidget(Run &run, uint32_t menu, uint32_t slot) {
    uint32_t widget = run.get(menu + slot);
    if (widget == 0)
        return;
    uint32_t flags = run.get(widget + 0x08);
    flags = flags | 0x10000;
    run.put(widget + 0x08, flags);
    widget = run.get(menu + slot);
    uint32_t owner = run.get(widget + 0x0c);
    uint32_t manager = run.get(owner + 0x08);
    enter(run, 24);
    run.call(0x4c92f0, manager, {widget});
    run.put(menu + slot, 0);
}

// 0x44fe40. Pause menu key release; argument is the key code.
uint32_t function_44fe40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t key = arguments[0];
    if (key == 0xd)
        return 1;
    // +0x2a8 menu active flag
    if (run.get(receiver + 0x2a8) != 0) {
        // +0x254 first widget, resized to 0x140 x 0xf0 before release
        uint32_t widget = run.get(receiver + 0x254);
        if (widget != 0) {
            run.put(widget + 0x4c, 0x140);
            widget = run.get(receiver + 0x254);
            run.put(widget + 0x50, 0xf0);
            releaseWidget(run, receiver, 0x254);
        }
        releaseWidget(run, receiver, 0x258);
        releaseWidget(run, receiver, 0x25c);
        releaseWidget(run, receiver, 0x260);
        releaseWidget(run, receiver, 0x264);
        releaseWidget(run, receiver, 0x268);
        releaseWidget(run, receiver, 0x26c);
    }
    // +0x274 selection object, its +0x2c is a panel
    uint32_t selection = 0;
    if (key == 9)
        selection = run.get(receiver + 0x274);
    if (key == 9 && selection != 0) {
        uint32_t panel = run.get(selection + 0x2c);
        if (panel != 0) {
            uint32_t effect = run.get(panel + 0x10);
            enter(run, 44);
            run.call(0x4bb990, effect, {0, 0x100, 0, 0, 0, 0x1f4});
            uint32_t group = run.get(run.get(receiver + 0x0c) + 0x04);
            enter(run, 24);
            run.call(0x4b97c0, run.get(run.get(group + 0x14) + 0x2c), {0});
            enter(run, 24);
            run.call(0x4b98b0, run.get(run.get(group + 0x10) + 0x2c), {0});
            group = run.get(run.get(receiver + 0x0c) + 0x04);
            enter(run, 24);
            run.call(0x4b97c0, run.get(run.get(group + 0x14) + 0x2c), {0});
            enter(run, 24);
            run.call(0x4b98b0, run.get(run.get(group + 0x10) + 0x2c), {0});
            enter(run, 24);
            run.call(0x4bb8c0, run.get(panel + 0x10), {0});
        }
    }
    if (s32(run.get(0x5370cc)) > 0) {
        uint32_t group = run.get(run.get(receiver + 0x0c) + 0x04);
        enter(run, 24);
        run.call(0x4caaa0, group, {0});
    }
    enter(run, 24);
    uint32_t count = run.icall(0x546d54, {0});
    while (s32(count) >= 0)
        count = run.icall(0x546d54, {0});
    enter(run, 20);
    run.call(0x452af0, receiver);
    return 1;
}

// 0x44fa80. Releases the menu's resources.
uint32_t function_44fa80(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(0x53789c, 0);
    enter(run, 8);
    run.call(0x4dce90, receiver + 0x154);
    if (run.get(receiver + 0x270) != 0) {
        uint32_t list = run.get(run.get(receiver + 0x0c) + 0x1c);
        enter(run, 12);
        run.call(0x4bc4f0, list, {run.get(receiver + 0x270)});
        run.put(receiver + 0x270, 0);
    }
    enter(run, 8);
    run.call(0x48f180, receiver);
    return 0;
}

// 0x429840. Destructor body: restores base vtables around member teardown.
uint32_t function_429840(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver, 0x50c044);
    owned_call(run, 24, function_44fa80, receiver, arguments);
    enter(run, 24);
    run.call(0x4f5d00, receiver + 0x2b4);
    run.call(0x4dccb0, receiver + 0x154);
    run.put(receiver, 0x50b4ec);
    run.call(0x48f180, receiver);
    return 0;
}

// 0x429820. Scalar deleting destructor; bit 0 of the flag frees the object.
uint32_t function_429820(Run &run, uint32_t receiver, const uint32_t *arguments) {
    owned_call(run, 8, function_429840, receiver, arguments);
    if ((arguments[0] & 1) != 0) {
        enter(run, 12);
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x429810.
uint32_t function_429810(Run &, uint32_t, const uint32_t *) {
    return 0xb;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x44fe40:
        return function_44fe40(run, receiver, arguments);
    case 0x44fa80:
        return function_44fa80(run, receiver, arguments);
    case 0x429820:
        return function_429820(run, receiver, arguments);
    case 0x429810:
        return function_429810(run, receiver, arguments);
    case 0x429840:
        return function_429840(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_pause_menu_entry_entry, owned, body)
