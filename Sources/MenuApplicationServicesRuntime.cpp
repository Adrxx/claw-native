// Menu application volume and full-palette forwarding services
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x42cdc0:
        return 1;
    case 0x42d590:
        return 4;
    default:
        return -1;
    }
}

// 0x42cdc0 Application::setVolume. thiscall, 1 stack argument(s), returns void.
uint32_t function_42cdc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Application fields: +0x30 scene, +0x12c volume, +0x5c audio.
    uint32_t scene = run.get(receiver + 0x30);
    uint32_t volume = arguments[0];
    run.put(receiver + 0x12c, volume);
    // Scene +0x28 enables the global volume update.
    if (scene && run.get(scene + 0x28))
        run.put(0x532c10, volume);
    uint32_t audio = run.get(receiver + 0x5c);
    if (audio)
        run.call(0x4024e0, audio, {volume});
    return 0;
}

// 0x42d590 Palette::fadeAll. thiscall, 4 stack argument(s), returns void.
uint32_t function_42d590(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x4bb990, receiver, {0, 0x100, arguments[0], arguments[1], arguments[2], arguments[3]});
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x42cdc0:
        return function_42cdc0(run, receiver, arguments);
    case 0x42d590:
        return function_42d590(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_menu_application_services_entry, owned, body)
