// Screen dump command.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x495be0:
        return 2;
    default:
        return -1;
    }
}

// 0x495be0. cdecl, 2 stack argument(s), returns u32.
uint32_t function_495be0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t settings = arguments[0];
    uint32_t game = arguments[1];
    if (!settings)
        return 0;
    if (!game)
        return 0;
    // Game +0x30 leads through +0x04 and +0x10 to the display owner.
    uint32_t displayRoot = run.get(game + 0x30);
    if (!displayRoot)
        return 0;
    uint32_t display = run.get(run.get(displayRoot + 0x04) + 0x10);
    if (!display)
        return 0;
    // Display +0x2c is the surface used for the BMP write.
    if (!run.get(display + 0x2c))
        return 0;
    uint32_t count = run.call(0x4b5f30, settings, {0x52cdd0, 0});
    count += 1;
    run.call(0x4b5e50, settings, {0x52cdd0, count});
    // The first argument's stack slot becomes the temporary CString.
    uint32_t filename = run.automatic(0x04);
    run.call(0x4f6439, filename, {});
    run.call(0x4f4f58, 0, {filename, 0x52cdc0, count});
    // Game +0x2c, then +0x2c and +0x10, selects the optional palette.
    uint32_t paletteRoot = run.get(game + 0x2c);
    if (!paletteRoot) {
        run.call(0x4f6584, filename, {});
        return 0;
    }
    uint32_t paletteOwner = run.get(paletteRoot + 0x2c);
    uint32_t palette = 0;
    if (paletteOwner)
        palette = run.get(paletteOwner + 0x10);
    uint32_t result = run.call(0x4b9e10, run.get(display + 0x2c), {run.get(filename), 1, palette});
    run.call(0x4f6584, filename, {});
    return result;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x495be0:
        return function_495be0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_screen_dump_entry, owned, body)
