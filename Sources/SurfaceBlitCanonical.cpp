// Original surface blit and color-key wrappers
//
// Translated from the original function packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4b9950:
        return 2;
    case 0x4b9ce0:
        return 5;
    case 0x4b9d80:
        return 5;
    default:
        return -1;
    }
}

// 0x4b9950 Surface::setColorKey. thiscall, 2 stack argument(s), returns u32.
uint32_t function_4b9950(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Wrapper +0x08 holds the COM surface; its +0x00 holds its vtable.
    uint32_t surface = run.get(receiver + 0x08);
    uint32_t method = run.get(run.get(surface + 0x00) + 0x74);
    uint32_t result = run.call(method, 0, {surface, arguments[0], arguments[1]});
    if (result != 0)
        run.call(0x4bd260, 0, {0x5324dc, 0x331, result});
    return result;
}

// 0x4b9ce0 Surface::blit. thiscall, 5 stack argument(s), returns u32.
uint32_t function_4b9ce0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t flags = arguments[3];
    uint32_t effects = arguments[4];
    uint32_t source = arguments[1];
    uint32_t surface = run.get(receiver + 0x08);
    uint32_t table = run.get(surface + 0x00);
    uint32_t sourceSurface = source ? run.get(source + 0x08) : 0;
    uint32_t method = run.get(table + 0x14);
    uint32_t result = run.call(method, 0, {surface, arguments[0], sourceSurface, arguments[2], flags, effects});
    if (result == 0x887601c2) {
        // Wrapper vtable +0x1c is the thiscall restore method.
        uint32_t restore = run.get(run.get(receiver + 0x00) + 0x1c);
        if (run.call(restore, receiver, {}) == 0)
            return 0x887601c2;
        uint32_t sourceRect = arguments[2];
        source = arguments[1];
        surface = run.get(receiver + 0x08);
        sourceSurface = run.get(source + 0x08);
        uint32_t destinationRect = arguments[0];
        method = run.get(run.get(surface + 0x00) + 0x14);
        result = run.call(method, 0, {surface, destinationRect, sourceSurface, sourceRect, flags, effects});
    }
    if (result != 0)
        run.call(0x4bd260, 0, {0x5324dc, 0x48e, result});
    return result;
}

// 0x4b9d80 Surface::blitFast. thiscall, 5 stack argument(s), returns u32.
uint32_t function_4b9d80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t rectangle = arguments[3];
    uint32_t source = arguments[2];
    uint32_t flags = arguments[4];
    uint32_t sourceSurface = run.get(source + 0x08);
    uint32_t surface = run.get(receiver + 0x08);
    uint32_t table = run.get(surface + 0x00);
    uint32_t method = run.get(table + 0x1c);
    uint32_t result = run.call(method, 0, {surface, arguments[0], arguments[1], sourceSurface, rectangle, flags});
    if (result == 0x887601c2) {
        uint32_t restore = run.get(run.get(receiver + 0x00) + 0x1c);
        if (run.call(restore, receiver, {}) == 0)
            return 0x887601c2;
        rectangle = arguments[3];
        sourceSurface = run.get(source + 0x08);
        surface = run.get(receiver + 0x08);
        uint32_t y = arguments[1];
        table = run.get(surface + 0x00);
        uint32_t x = arguments[0];
        method = run.get(table + 0x1c);
        result = run.call(method, 0, {surface, x, y, sourceSurface, rectangle, flags});
    }
    if (result != 0)
        run.call(0x4bd260, 0, {0x5324dc, 0x4b8, result});
    return result;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b9950:
        return function_4b9950(run, receiver, arguments);
    case 0x4b9ce0:
        return function_4b9ce0(run, receiver, arguments);
    case 0x4b9d80:
        return function_4b9d80(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_surface_blit_canonical_entry, owned, body)
