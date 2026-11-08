// Original compressed eight-bit lighting dispatch
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4bffa0:
        return 5;
    default:
        return -1;
    }
}

// 0x4bffa0 LightPID::blit. Bounds +0x04/+0x08, mode +0x14,
// compressed flag +0x24; rectangle left/top/right at +0x00/+0x04/+0x08.
uint32_t function_4bffa0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t rectangle = arguments[2];
    if (run.gets(rectangle + 0x00) < 0)
        return 0;
    uint32_t width = run.get(receiver + 0x04);
    int32_t right = run.gets(rectangle + 0x08);
    if (right > s32(width - 1u))
        return 0;
    int32_t top = run.gets(rectangle + 0x04);
    if (top < 0)
        return 0;
    if (top > s32(run.get(receiver + 0x08) - 1u))
        return 0;
    uint32_t rasterizer;
    if (run.get(receiver + 0x14) == 1) {
        if (arguments[3] == 0) {
            if (arguments[4] == 0)
                rasterizer = 0x4c00b0;
            else
                rasterizer = 0x4c0920;
        } else {
            if (arguments[4] == 0)
                rasterizer = 0x4c0450;
            else
                rasterizer = 0x4c0cc0;
        }
    } else {
        if (run.get8(receiver + 0x24) != 1)
            return 0;
        if (arguments[3] == 0) {
            if (arguments[4] == 0)
                rasterizer = 0x4c1190;
            else
                rasterizer = 0x4c3800;
        } else {
            if (arguments[4] == 0)
                rasterizer = 0x4c25b0;
            else
                rasterizer = 0x4c4c20;
        }
    }
    run.call(rasterizer, receiver, {arguments[0], arguments[1], rectangle});
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4bffa0:
        return function_4bffa0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_light_pid_blitter_entry, owned, body)
