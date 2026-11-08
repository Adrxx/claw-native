// Original popup lifecycle and frame dispatch.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4299b0:
    case 0x438e90:
    case 0x438f10:
        return 1;
    case 0x438e10:
    case 0x438fa0:
    case 0x4390c0:
    case 0x439130:
    case 0x43a7f0:
        return 0;
    default:
        return -1;
    }
}

// Receiver fields: +0x04 parent, +0x0c services, +0x2c resource,
// +0x154 cursor, +0x15c backing surface, +0x160 dialog, +0x164 child.
// Services +0x04 graphics, whose +0x10 front wrapper has +0x2c surface.
uint32_t frontSurface(Run &run, uint32_t receiver) {
    return run.get(run.get(run.get(run.get(receiver + 0x0c) + 0x04) + 0x10) + 0x2c);
}

// 0x4299b0. Deleting destructor; the original destructor retains its reentry.
uint32_t function_4299b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.stackPointer = run.automatic(-8);
    run.call(0x4299d0, receiver);
    if (arguments[0] & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x438e10. Release owned resources, then base cleanup.
uint32_t function_438e10(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t cursor = run.get(receiver + 0x154);
    if (cursor) {
        // Cursor +0x08 resource flags.
        run.put(cursor + 0x08, run.get(cursor + 0x08) | 0x10000);
        run.call(0x4c92f0, run.get(run.get(receiver + 0x0c) + 0x08), {run.get(receiver + 0x154)});
        run.put(receiver + 0x154, 0);
    }
    uint32_t surface = run.get(receiver + 0x15c);
    if (surface) {
        run.call(0x4bc4f0, run.get(run.get(receiver + 0x0c) + 0x1c), {surface});
        run.put(receiver + 0x15c, 0);
    }
    uint32_t dialog = run.get(receiver + 0x160);
    if (dialog) {
        run.vcall(dialog, 0x00, {1});
        run.put(receiver + 0x160, 0);
    }
    run.call(0x48f180, receiver);
    run.put(0x5375bc, 0);
    return 0;
}

// 0x438e90. Enter popup state.
uint32_t function_438e90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!run.get(receiver + 0x160)) {
        return 0;
    }
    if (!run.get(receiver + 0x04)) {
        return 0;
    }
    while (s32(run.icall(0x546d54, {0})) >= 0) {
    }
    run.call(0x43a6e0, receiver);
    if (arguments[0] == 13) {
        uint32_t dialog = run.get(receiver + 0x160);
        // Dialog +0x2b4 mode.
        if (run.get(dialog + 0x2b4) == 3) {
            run.vcall(dialog, 0x1e8);
        }
    }
    run.put(0x5375bc, receiver);
    return run.vcall(run.get(receiver + 0x160), 0x1d0, {arguments[0]});
}

// 0x43a7f0. Restore cursor for the current child state.
uint32_t function_43a7f0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t child = run.get(receiver + 0x164);
    if (!child) {
        return 0;
    }
    uint32_t state = run.vcall(child, 0x10);
    child = run.get(receiver + 0x164);
    if (state == 13) {
        if (child) {
            run.call(0x43a6e0, child);
        }
        return 0;
    }
    state = run.vcall(child, 0x10);
    child = run.get(receiver + 0x164);
    if (state == 5) {
        if (child) {
            run.call(0x45fdc0, child);
        }
        return 0;
    }
    state = run.vcall(child, 0x10);
    if (state == 11) {
        child = run.get(receiver + 0x164);
        if (child) {
            run.call(0x452ae0, child);
        }
    }
    return 0;
}

// 0x438f10. Leave popup state.
uint32_t function_438f10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x43a720, receiver);
    uint32_t dialog = run.get(receiver + 0x160);
    if (dialog) {
        run.vcall(dialog, 0x1d4, {arguments[0]});
    }
    if (arguments[0] == 13) {
        run.stackPointer = run.automatic(-12);
        run.call(0x439590, receiver);
        run.call(0x4b98b0, frontSurface(run, receiver), {0});
    } else {
        run.stackPointer = run.automatic(-12);
        if (!run.call(0x439630, receiver)) {
            return 0;
        }
        run.call(0x4b98b0, frontSurface(run, receiver), {0});
        run.call(0x4cab10, run.get(run.get(receiver + 0x0c) + 0x04));
    }
    run.put(0x5375bc, 0);
    function_43a7f0(run, receiver, nullptr);
    return 1;
}

// 0x438fa0. Render one popup frame.
uint32_t function_438fa0(Run &run, uint32_t receiver, const uint32_t *) {
    // Front surface +0x08 is the COM interface; its calls are stdcall.
    uint32_t interface = run.get(frontSurface(run, receiver) + 0x08);
    if (!interface || run.call(run.get(run.get(interface) + 0x60), 0, {interface}) != 0) {
        if (!run.vcall(receiver, 0x18)) {
            run.call(0x429e10, run.get(receiver + 0x04), {0x8006, 3000});
            return 0;
        }
    }
    uint32_t audio = run.get(run.get(run.get(receiver + 0x0c) + 0x28) + 0x2c);
    if (audio) {
        run.call(0x4b4b80, audio);
    }
    run.stackPointer = run.automatic(-16);
    run.call(0x4396f0, receiver);
    if (!run.call(0x439630, receiver)) {
        return 0;
    }
    if (!run.call(0x439590, receiver)) {
        return 0;
    }
    uint32_t first = run.get(0x53720c);
    uint32_t second = run.get(0x537208);
    run.put(0x5430c4, first);
    run.put(0x5430c8, second);
    uint32_t cursor = run.get(receiver + 0x154);
    if (cursor) {
        // Cursor +0x6c callback table; callback +0x10 is cdecl.
        run.call(run.get(run.get(cursor + 0x6c) + 0x10), 0, {cursor});
        uint32_t point = run.automatic(-8);
        run.icall(0x546cd0, {point});
        // Receiver +0x174/+0x178 cursor coordinate offsets.
        uint32_t x = run.get(point) + run.get(receiver + 0x174);
        uint32_t y = run.get(point + 0x04) + run.get(receiver + 0x178);
        run.put(point, x);
        run.put(point + 0x04, y);
        // Cursor +0x4c/+0x50 coordinates.
        run.put(run.get(receiver + 0x154) + 0x4c, x);
        run.put(run.get(receiver + 0x154) + 0x50, run.get(point + 0x04));
        uint32_t services = run.get(receiver + 0x0c);
        cursor = run.get(receiver + 0x154);
        // Graphics +0x14 back wrapper is passed to cursor drawing.
        uint32_t back = run.get(run.get(services + 0x04) + 0x14);
        run.vcall(cursor, 0x2c, {back});
    }
    run.call(0x4b98b0, frontSurface(run, receiver), {0});
    return 1;
}

// 0x4390c0. Restore child and popup backing state.
uint32_t function_4390c0(Run &run, uint32_t receiver, const uint32_t *) {
    if (!run.call(0x4ca930, run.get(run.get(receiver + 0x0c) + 0x04))) {
        return 0;
    }
    if (!run.get(receiver + 0x164)) {
        return 0;
    }
    run.call(0x43a720, receiver);
    run.vcall(run.get(receiver + 0x164), 0x18);
    run.call(0x43a760, receiver);
    run.stackPointer = run.automatic(-8);
    run.call(0x439480, receiver);
    uint32_t dialog = run.get(receiver + 0x160);
    if (!dialog) {
        return 0;
    }
    if (!run.vcall(dialog, 0x1e4)) {
        return 0;
    }
    run.stackPointer = run.automatic(-8);
    run.call(0x439590, receiver);
    run.call(0x43a6e0, receiver);
    return 1;
}

// 0x439130. Redraw child and rebuild backing.
uint32_t function_439130(Run &run, uint32_t receiver, const uint32_t *) {
    if (!run.vcall(receiver, 0x0c)) {
        return 0;
    }
    if (!run.get(receiver + 0x2c)) {
        return 0;
    }
    uint32_t child = run.get(receiver + 0x164);
    if (!child) {
        return 0;
    }
    run.vcall(child, 0x1c);
    run.stackPointer = run.automatic(-8);
    run.call(0x439480, receiver);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4299b0:
        return function_4299b0(run, receiver, arguments);
    case 0x438e10:
        return function_438e10(run, receiver, arguments);
    case 0x438e90:
        return function_438e90(run, receiver, arguments);
    case 0x438f10:
        return function_438f10(run, receiver, arguments);
    case 0x438fa0:
        return function_438fa0(run, receiver, arguments);
    case 0x4390c0:
        return function_4390c0(run, receiver, arguments);
    case 0x439130:
        return function_439130(run, receiver, arguments);
    case 0x43a7f0:
        return function_43a7f0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_menu_popup_lifecycle_entry, owned, body)
