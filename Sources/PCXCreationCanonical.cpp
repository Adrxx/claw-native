// PCX image creation from memory
//
// Recovered from the v1.0 disassembly in the canonical task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4be810:
        return 4;
    default:
        return -1;
    }
}

// 0x4be810 PCXImage::createFromMemory. thiscall, 4 stack argument(s), returns u32.
uint32_t function_4be810(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t input = arguments[1];
    if (!input)
        return 0;
    // Header +0x04/+0x08 and +0x06/+0x0a are signed endpoint words.
    uint32_t xmax = (uint32_t(run.get16(input + 0x08)) ^ 0x8000u) - 0x8000u;
    uint32_t xmin = (uint32_t(run.get16(input + 0x04)) ^ 0x8000u) - 0x8000u;
    uint32_t ymax = (uint32_t(run.get16(input + 0x0a)) ^ 0x8000u) - 0x8000u;
    uint32_t ymin = (uint32_t(run.get16(input + 0x06)) ^ 0x8000u) - 0x8000u;
    uint32_t width = xmax - xmin + 1u;
    uint32_t planes = run.get8(input + 0x41); // Header plane count.
    uint32_t height = ymax - ymin + 1u;
    uint32_t inputDepth;
    if (planes == 1)
        inputDepth = 8;
    else if (planes == 3)
        inputDepth = 24;
    else
        return 0;
    uint32_t device = arguments[0];
    uint32_t deviceDepth = run.get(device + 0x474); // Destination depth.
    bool convert = deviceDepth != inputDepth;
    if (convert && deviceDepth == 8 && !run.get(device + 0x878)) // Palette-present flag.
        return 0;
    uint32_t palette = 0;
    if (convert && inputDepth == 8) {
        uint32_t source = input + arguments[2] - 0x300;
        uint32_t destination = 0x541fb1;
        do {
            uint32_t red = run.get8(source);
            source += 1;
            run.put8(destination - 0x01, red);
            destination += 4;
            uint32_t green = run.get8(source);
            source += 1;
            run.put8(destination - 0x04, green);
            uint32_t blue = run.get8(source);
            source += 1;
            run.put8(destination - 0x03, blue);
            run.put8(destination - 0x02, 0);
        } while (s32(destination) < s32(0x5423b1));
        palette = 0x541fb0;
    } else if (convert && deviceDepth == 8) {
        if (run.get(device + 0x878))
            palette = device + 0x478; // Destination RGB0 palette.
    }
    // Receiver +0x00 is its vtable; +0x0c creates the destination surface.
    if (!run.vcall(receiver, 0x0c, {device, width, height, 0, arguments[3]}))
        return 0;
    uint32_t payload = input + 0x80;
    uint32_t temporary = 0;
    if (!convert) {
        uint32_t decoder = inputDepth == 8 ? 0x4babe0 : 0x4bad30;
        if (!run.call(decoder, receiver, {payload}))
            return 0;
    } else {
        if (width & 1u)
            return 0;
        uint32_t bytes = height * width;
        if (inputDepth != 8)
            bytes *= 3u;
        temporary = run.call(0x4f63ec, 0, {bytes});
        if (!temporary)
            return 0;
        uint32_t decoder = inputDepth == 8 ? 0x4bef50 : 0x4bf070;
        // These raw decoders preserve unused ECX in their canonical thiscall ABI.
        if (!run.call(decoder, receiver, {temporary, payload, width, height})) {
            run.call(0x4f6428, 0, {temporary});
            return 0;
        }
    }
    if (convert && !run.call(0x4b9e90, receiver, {temporary, inputDepth, palette, 1})) {
        run.call(0x4f6428, 0, {temporary});
        return 0;
    }
    if (temporary)
        run.call(0x4f6428, 0, {temporary});
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4be810:
        return function_4be810(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_pcx_creation_canonical_entry, owned, body)
