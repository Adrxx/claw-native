// v1.3 grayscale palette toggle and music tempo request
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x463bc0:
        return 1;
    case 0x463c90:
        return 1;
    case 0x4b55e0:
        return 2;
    default:
        return -1;
    }
}

// 0x463bc0. cdecl, 1 stack argument(s), returns u32.
uint32_t function_463bc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    if (!object)
        return 0;
    uint32_t palette = run.automatic(-0x400);
    // +0x10 is the palette service; its +0x04 is the COM palette.
    uint32_t interface = run.get(run.get(object + 0x10) + 0x04);
    uint32_t method = run.get(run.get(interface) + 0x10);
    run.call(method, 0, {interface, 0, 0, 256, palette});
    for (uint32_t index = 0; index < 256; ++index) {
        uint32_t entry = palette + index * 4;
        uint32_t green = run.get8(entry + 0x01) * 150 / 255;
        uint32_t blue = run.get8(entry + 0x02) * 28 / 255;
        uint32_t red = run.get8(entry + 0x00) * 76 / 255;
        uint8_t gray = uint8_t(green + blue + red);
        run.put8(entry + 0x00, gray);
        run.put8(entry + 0x01, gray);
        run.put8(entry + 0x02, gray);
    }
    run.call(0x4bc4f0, run.get(object + 0x10), {0, 256, palette, 0});
    return 1;
}

// 0x463c90. cdecl, 1 stack argument(s), returns u32.
uint32_t function_463c90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    if (!object)
        return 0;
    uint32_t service = run.get(object + 0x10);
    // +0x0c contains palette entries; entry at +0xdc selects the toggle.
    uint32_t color = run.get(run.get(service + 0x0c) + 0xdc);
    if (uint8_t(color) == uint8_t(color >> 8) && uint8_t(color >> 8) == uint8_t(color >> 16)) {
        run.call(0x4bc5b0, service, {0});
        return 1;
    }
    run.call(0x4bc560, service);
    uint32_t frame = run.frame;
    run.frame -= 0x0c;
    uint32_t nested[] = {object};
    function_463bc0(run, 0, nested);
    run.frame = frame;
    return 1;
}

// 0x4b55e0. thiscall, 2 stack argument(s), returns u32.
uint32_t function_4b55e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!run.vcall(receiver, 0x18))
        return 0;
    // +0x58 is the backend sequence and +0x54 stores the requested tempo.
    run.icall(0x50c61c, {run.get(receiver + 0x58), arguments[0], arguments[1]});
    run.put(receiver + 0x54, arguments[0]);
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x463bc0:
        return function_463bc0(run, receiver, arguments);
    case 0x463c90:
        return function_463c90(run, receiver, arguments);
    case 0x4b55e0:
        return function_4b55e0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_v13_cheat_presentation_entry, owned, body)
