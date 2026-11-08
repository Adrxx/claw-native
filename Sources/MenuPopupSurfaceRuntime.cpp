// Original popup backing surface and cursor transitions
// Recovered from the original decompile and disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x439480:
        return 0;
    case 0x439590:
        return 0;
    case 0x439630:
        return 0;
    case 0x4396f0:
        return 0;
    case 0x43a6e0:
        return 0;
    case 0x43a720:
        return 0;
    case 0x43a760:
        return 0;
    case 0x4cab10:
        return 0;
    case 0x452ae0:
        return 0;
    case 0x452af0:
        return 0;
    case 0x45fdc0:
        return 0;
    case 0x45fdd0:
        return 0;
    default:
        return -1;
    }
}

// Preserve the original entry ESP when one owned function calls another.
struct OwnedFrame {
    Run &run;
    uint32_t frame;
    uint32_t stackPointer;
    OwnedFrame(Run &run, uint32_t entry) : run(run), frame(run.frame), stackPointer(run.stackPointer) {
        run.frame = entry;
    }
    ~OwnedFrame() {
        run.frame = frame;
        run.stackPointer = stackPointer;
    }
};

uint32_t function_4cab10(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_43a720(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_452af0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_45fdd0(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x439480. +4 dimensions, +0xc application, +0x15c backing, +0x160 popup.
uint32_t function_439480(Run &run, uint32_t receiver, const uint32_t *) {
    if (!run.get(receiver + 0x04))
        return 0;
    if (!run.get(receiver + 0x160))
        return 0;
    uint32_t backing = run.get(receiver + 0x15c);
    if (backing) {
        uint32_t manager = run.get(run.get(receiver + 0x0c) + 0x1c);
        run.stackPointer = run.automatic(-0x40);
        run.call(0x4bc4f0, manager, {backing});
    }
    uint32_t dimensions = run.get(receiver + 0x04);
    uint32_t app = run.get(receiver + 0x0c);
    uint32_t width = run.get(dimensions + 0x7c);
    uint32_t height = run.get(dimensions + 0x80);
    uint32_t manager = run.get(app + 0x1c);
    run.stackPointer = run.automatic(-0x50);
    backing = run.call(0x4bc670, manager, {width, height, 0, 0, 0xffffffff});
    run.put(receiver + 0x15c, backing);
    if (!backing)
        return 0;
    uint32_t display = run.get(run.get(receiver + 0x0c) + 0x04);
    {
        OwnedFrame frame(run, run.automatic(-0x3c));
        function_4cab10(run, display, nullptr);
    }
    uint32_t surface = run.get(run.get(run.get(run.get(receiver + 0x0c) + 0x04) + 0x14) + 0x2c);
    backing = run.get(receiver + 0x15c);
    uint32_t source = run.automatic(-0x20);
    uint32_t copied = run.automatic(-0x30);
    uint32_t extent = run.automatic(-0x10);
    run.put(source + 0x00, run.get(backing + 0x7c));
    run.put(source + 0x04, run.get(backing + 0x80));
    run.put(source + 0x08, run.get(backing + 0x84));
    run.put(source + 0x0c, run.get(backing + 0x88));
    run.stackPointer = run.automatic(-0x44);
    run.icall(0x546d58, {copied, source});
    width = run.get(copied + 0x08) - run.get(copied + 0x00);
    height = run.get(copied + 0x0c) - run.get(copied + 0x04);
    run.put(extent + 0x08, width);
    backing = run.get(receiver + 0x15c);
    run.put(extent + 0x00, 0);
    run.put(extent + 0x04, 0);
    run.put(extent + 0x0c, height);
    run.stackPointer = run.automatic(-0x50);
    run.call(0x4b9ce0, backing, {copied, surface, extent, 0x1000000, 0});
    return 1;
}

// 0x439590. The cached display surface supplies the COM interface at +0x08.
uint32_t function_439590(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t popup = run.get(receiver + 0x160);
    if (!popup)
        return 0;
    run.stackPointer = run.automatic(-0x14);
    uint32_t result = run.vcall(popup, 0x1d8);
    if (!result)
        return 0;
    uint32_t surface = run.get(run.get(run.get(run.get(receiver + 0x0c) + 0x04) + 0x14) + 0x2c);
    uint32_t hdc = run.automatic(-0x04);
    run.put(hdc, 0);
    uint32_t interface = run.get(surface + 0x08);
    uint32_t method = run.get(run.get(interface) + 0x44);
    run.stackPointer = run.automatic(-0x1c);
    run.call(method, 0, {interface, hdc});
    uint32_t handle = run.get(hdc);
    if (handle) {
        run.stackPointer = run.automatic(-0x18);
        uint32_t wrapper = run.call(0x4fcfe9, 0, {handle});
        popup = run.get(receiver + 0x160);
        run.stackPointer = run.automatic(-0x1c);
        result = run.vcall(popup, 0x1dc, {wrapper, 1});
        handle = run.get(hdc);
        interface = run.get(surface + 0x08);
        method = run.get(run.get(interface) + 0x68);
        run.stackPointer = run.automatic(-0x1c);
        run.call(method, 0, {interface, handle});
    }
    if (!result)
        return 0;
    popup = run.get(receiver + 0x160);
    run.stackPointer = run.automatic(-0x14);
    result = run.vcall(popup, 0x1e0);
    if (!result)
        return 0;
    return result;
}

// 0x439630. Restore the backing rectangle onto the display holder's +0x2c surface.
uint32_t function_439630(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t backing = run.get(receiver + 0x15c);
    if (!backing)
        return 0;
    if (!run.get(receiver + 0x160))
        return 0;
    uint32_t display = run.get(run.get(receiver + 0x0c) + 0x04);
    uint32_t source = run.automatic(-0x20);
    uint32_t copied = run.automatic(-0x30);
    uint32_t extent = run.automatic(-0x10);
    run.put(source + 0x00, run.get(backing + 0x7c));
    uint32_t holder = run.get(display + 0x14);
    run.put(source + 0x04, run.get(backing + 0x80));
    run.put(source + 0x08, run.get(backing + 0x84));
    run.put(source + 0x0c, run.get(backing + 0x88));
    run.stackPointer = run.automatic(-0x44);
    run.icall(0x546d58, {copied, source});
    uint32_t width = run.get(copied + 0x08) - run.get(copied + 0x00);
    uint32_t height = run.get(copied + 0x0c) - run.get(copied + 0x04);
    run.put(extent + 0x08, width);
    backing = run.get(receiver + 0x15c);
    run.put(extent + 0x0c, height);
    run.put(extent + 0x00, 0);
    run.put(extent + 0x04, 0);
    uint32_t surface = run.get(holder + 0x2c);
    run.stackPointer = run.automatic(-0x50);
    run.call(0x4b9ce0, surface, {extent, backing, copied, 0x1000000, 0});
    return 1;
}

// 0x4396f0. +0x170 suppresses the first poll; +0x16c is the repeat timer.
uint32_t function_4396f0(Run &run, uint32_t receiver, const uint32_t *) {
    if (!run.get(receiver + 0x160))
        return 0;
    if (run.get(receiver + 0x170)) {
        run.put(receiver + 0x170, 0);
        return 1;
    }
    run.stackPointer = run.automatic(-0x0c);
    run.call(0x4b3490, run.get(0x537200));
    uint32_t input = run.get(0x537200);
    uint32_t bits = run.get(input + 0x210);
    uint32_t delay = 0x528a60;
    if (!(bits & 0xf0000000)) {
        if (bits & 0xffffff) {
            run.stackPointer = run.automatic(-0x0c);
            run.vcall(run.get(receiver + 0x160), 0x1f8);
            return 1;
        }
        if (!(run.get(input + 0x214) & 0xf0000000))
            return 1;
        uint32_t timer = run.get(receiver + 0x16c);
        uint32_t elapsed = run.get(0x53720c);
        if (elapsed < timer) {
            run.put(receiver + 0x16c, timer - elapsed);
        } else {
            run.put(receiver + 0x16c, 0);
        }
        if (run.get(receiver + 0x16c))
            return 1;
        bits = run.get(run.get(0x537200) + 0x214);
        delay = 0x528a64;
    }
    if (bits & 0xc0000000) {
        uint32_t popup = run.get(receiver + 0x160);
        run.stackPointer = run.automatic(-0x10);
        run.vcall(popup, 0x1f4, {bits & 0x40000000});
    } else if (bits & 0x20000000) {
        run.stackPointer = run.automatic(-0x14);
        run.vcall(receiver, 0x2c, {9, 0});
    } else if (bits & 0x10000000) {
        uint32_t popup = run.get(receiver + 0x160);
        run.put(popup + 0x2b8, 1);
        run.stackPointer = run.automatic(-0x14);
        run.vcall(receiver, 0x2c, {9, 0});
        popup = run.get(receiver + 0x160);
        run.put(popup + 0x2b8, 0);
    }
    run.put(receiver + 0x16c, run.get(delay));
    return 1;
}

// 0x43a6e0. +0x154 cursor owner: +0x40 visibility, +0x174 cursor policy.
uint32_t function_43a6e0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t owner = run.get(receiver + 0x154);
    if (owner) {
        run.put(owner + 0x40, run.get(owner + 0x40) & 0xfffffffe);
    }
    owner = run.get(receiver + 0x154);
    if (owner && run.get(owner + 0x174))
        return 0;
    uint32_t showCursor = run.get(0x546d54);
    do {
        run.stackPointer = run.automatic(-0x0c);
    } while (s32(run.call(showCursor, 0, {1})) < 0);
    return 0;
}

// 0x43a720.
uint32_t function_43a720(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t owner = run.get(receiver + 0x154);
    if (owner) {
        run.put(owner + 0x40, run.get(owner + 0x40) | 1);
    }
    owner = run.get(receiver + 0x154);
    if (owner && run.get(owner + 0x174))
        return 0;
    uint32_t showCursor = run.get(0x546d54);
    do {
        run.stackPointer = run.automatic(-0x0c);
    } while (s32(run.call(showCursor, 0, {0})) >= 0);
    return 0;
}

// 0x43a760. +0x164 previous popup is reloaded after each type query.
uint32_t function_43a760(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t popup = run.get(receiver + 0x164);
    if (!popup)
        return 0;
    run.stackPointer = run.automatic(-0x08);
    uint32_t type = run.vcall(popup, 0x10);
    uint32_t selected = 13;
    if (type != 13) {
        popup = run.get(receiver + 0x164);
        run.stackPointer = run.automatic(-0x08);
        type = run.vcall(popup, 0x10);
        selected = 5;
        if (type != 5) {
            popup = run.get(receiver + 0x164);
            run.stackPointer = run.automatic(-0x08);
            type = run.vcall(popup, 0x10);
            selected = 11;
            if (type != 11)
                return 0;
        }
    }
    popup = run.get(receiver + 0x164);
    if (!popup)
        return 0;
    {
        OwnedFrame frame(run, run.automatic(-0x08));
        if (selected == 13)
            function_43a720(run, popup, nullptr);
        else if (selected == 5)
            function_45fdd0(run, popup, nullptr);
        else
            function_452af0(run, popup, nullptr);
    }
    run.stackPointer = run.automatic(-0x08);
    run.vcall(popup, 0x14);
    return 0;
}

// 0x4cab10. +0x10/+0x14 surface holders; +0xc flags owner, byte +0x34.
uint32_t function_4cab10(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t first = run.get(receiver + 0x10);
    uint32_t second = run.get(receiver + 0x14);
    if (!first)
        return 0;
    uint32_t source = run.get(first + 0x2c);
    if (!source)
        return 0;
    uint32_t destination = run.get(second + 0x2c);
    if (!destination)
        return 0;
    run.stackPointer = run.automatic(-0x0c);
    uint32_t result = run.call(0x4b9c50, destination, {source}) == 0;
    if (!result)
        return 0;
    if (!(run.get8(run.get(receiver + 0x0c) + 0x34) & 2))
        return 1;
    source = run.get(run.get(receiver + 0x10) + 0x2c);
    run.stackPointer = run.automatic(-0x0c);
    run.call(0x4b98b0, source, {0});
    second = run.get(receiver + 0x14);
    first = run.get(receiver + 0x10);
    if (!first)
        return 0;
    source = run.get(first + 0x2c);
    if (!source)
        return 0;
    destination = run.get(second + 0x2c);
    if (!destination)
        return 0;
    run.stackPointer = run.automatic(-0x0c);
    return run.call(0x4b9c50, destination, {source}) == 0;
}

// 0x452ae0. +0x254 options surface; +0x40 visibility flags.
uint32_t function_452ae0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t surface = run.get(receiver + 0x254);
    if (surface) {
        run.put(surface + 0x40, run.get(surface + 0x40) & 0xfffffffe);
    }
    return 0;
}

// 0x452af0.
uint32_t function_452af0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t surface = run.get(receiver + 0x254);
    if (surface) {
        run.put(surface + 0x40, run.get(surface + 0x40) | 1);
    }
    return 0;
}

// 0x45fdc0. +0x258 controls surface.
uint32_t function_45fdc0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t surface = run.get(receiver + 0x258);
    if (surface) {
        run.put(surface + 0x40, run.get(surface + 0x40) & 0xfffffffe);
    }
    return 0;
}

// 0x45fdd0.
uint32_t function_45fdd0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t surface = run.get(receiver + 0x258);
    if (surface) {
        run.put(surface + 0x40, run.get(surface + 0x40) | 1);
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x439480:
        return function_439480(run, receiver, arguments);
    case 0x439590:
        return function_439590(run, receiver, arguments);
    case 0x439630:
        return function_439630(run, receiver, arguments);
    case 0x4396f0:
        return function_4396f0(run, receiver, arguments);
    case 0x43a6e0:
        return function_43a6e0(run, receiver, arguments);
    case 0x43a720:
        return function_43a720(run, receiver, arguments);
    case 0x43a760:
        return function_43a760(run, receiver, arguments);
    case 0x4cab10:
        return function_4cab10(run, receiver, arguments);
    case 0x452ae0:
        return function_452ae0(run, receiver, arguments);
    case 0x452af0:
        return function_452af0(run, receiver, arguments);
    case 0x45fdc0:
        return function_45fdc0(run, receiver, arguments);
    case 0x45fdd0:
        return function_45fdd0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_menu_popup_surface_entry, owned, body)
