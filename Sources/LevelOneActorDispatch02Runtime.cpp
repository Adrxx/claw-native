// Level one actor dispatch batch 2
//
// Recovered from original v1.0 disassembly; external callees remain original.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4080a0:
        return 0;
    case 0x408220:
        return 22;
    case 0x4082d0:
        return 2;
    case 0x4082f0:
        return 1;
    case 0x408370:
        return 1;
    case 0x40ab80:
        return 4;
    case 0x40abb0:
        return 1;
    case 0x40abf0:
        return 0;
    case 0x40f6c0:
        return 4;
    case 0x4209d0:
        return 1;
    default:
        return -1;
    }
}

// 0x4080a0. thiscall, 0 stack argument(s), returns void.
uint32_t function_4080a0(Run &run, uint32_t receiver, const uint32_t *) {
    // Physics vectors and scalar fields; preserve all unspecified gaps.
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x48, 0);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x28, 0);
    run.put(receiver + 0x30, 0);
    run.put(receiver + 0x38, 0);
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x00, 0);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0xa8, 0);
    run.put(receiver + 0xb0, 0);
    run.put(receiver + 0xb8, 0);
    run.put(receiver + 0x44, 0);
    run.put(receiver + 0x4c, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x2c, 0);
    run.put(receiver + 0x34, 0);
    run.put(receiver + 0x3c, 0);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x1c, 0);
    run.put(receiver + 0x24, 0);
    run.put(receiver + 0x04, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0xac, 0);
    run.put(receiver + 0xb4, 0);
    run.put(receiver + 0xbc, 0);
    run.put(receiver + 0xa0, 0);
    uint32_t low;
    uint32_t high;
    low = run.get(0x513e10);
    high = run.get(0x513e14);
    run.put(receiver + 0x58, low);
    run.put(receiver + 0x5c, high);
    low = run.get(0x513e18);
    high = run.get(0x513e1c);
    run.put(receiver + 0x70, low);
    run.put(receiver + 0x74, high);
    low = run.get(0x513e10);
    high = run.get(0x513e14);
    run.put(receiver + 0x60, low);
    run.put(receiver + 0x64, high);
    low = run.get(0x513e18);
    high = run.get(0x513e1c);
    run.put(receiver + 0x78, low);
    run.put(receiver + 0x7c, high);
    low = run.get(0x513e10);
    high = run.get(0x513e14);
    run.put(receiver + 0x68, low);
    run.put(receiver + 0x6c, high);
    low = run.get(0x513e18);
    high = run.get(0x513e1c);
    run.put(receiver + 0x80, low);
    run.put(receiver + 0x84, high);
    low = run.get(0x513e18);
    high = run.get(0x513e1c);
    run.put(receiver + 0xc0, low);
    run.put(receiver + 0xc4, high);
    low = run.get(0x513e18);
    high = run.get(0x513e1c);
    run.put(receiver + 0xc8, low);
    run.put(receiver + 0xcc, high);
    low = run.get(0x513e18);
    high = run.get(0x513e1c);
    run.put(receiver + 0xd0, low);
    run.put(receiver + 0xd4, high);
    low = run.get(0x513e18);
    high = run.get(0x513e1c);
    run.put(receiver + 0xd8, low);
    run.put(receiver + 0xdc, high);
    low = run.get(0x513e18);
    high = run.get(0x513e1c);
    run.put(receiver + 0xe0, low);
    run.put(receiver + 0xe4, high);
    low = run.get(0x513e18);
    high = run.get(0x513e1c);
    run.put(receiver + 0xe8, low);
    run.put(receiver + 0xec, high);
    return 0;
}

// 0x408220. thiscall, 22 stack argument(s), returns u32.
uint32_t function_408220(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Eleven raw qwords in the original physics-vector order.
    run.put(receiver + 0x40, arguments[0]);
    run.put(receiver + 0x44, arguments[1]);
    run.put(receiver + 0x48, arguments[2]);
    run.put(receiver + 0x4c, arguments[3]);
    run.put(receiver + 0x50, arguments[4]);
    run.put(receiver + 0x54, arguments[5]);
    run.put(receiver + 0x28, arguments[6]);
    run.put(receiver + 0x2c, arguments[7]);
    run.put(receiver + 0x30, arguments[8]);
    run.put(receiver + 0x34, arguments[9]);
    run.put(receiver + 0x38, arguments[10]);
    run.put(receiver + 0x3c, arguments[11]);
    run.put(receiver + 0x10, arguments[12]);
    run.put(receiver + 0x14, arguments[13]);
    run.put(receiver + 0x18, arguments[14]);
    run.put(receiver + 0x1c, arguments[15]);
    run.put(receiver + 0x20, arguments[16]);
    run.put(receiver + 0x24, arguments[17]);
    run.put(receiver + 0x00, arguments[18]);
    run.put(receiver + 0x04, arguments[19]);
    run.put(receiver + 0x08, arguments[20]);
    run.put(receiver + 0x0c, arguments[21]);
    return 1;
}

// 0x4082d0. thiscall, 2 stack argument(s), returns void.
uint32_t function_4082d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // FLD/FST quiets signaling NaNs while preserving sign and payload.
    uint32_t low = arguments[0];
    uint32_t high = arguments[1];
    if ((high & 0x7ff00000u) == 0x7ff00000u && ((high & 0x000fffffu) || low))
        high |= 0x00080000u;
    // Shared qword copied to the three physics coefficients.
    run.put(receiver + 0xc0, low);
    run.put(receiver + 0xc4, high);
    run.put(receiver + 0xc8, low);
    run.put(receiver + 0xcc, high);
    run.put(receiver + 0xd0, low);
    run.put(receiver + 0xd4, high);
    return 0;
}

// 0x4082f0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4082f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    // Vtable, incoming actor aliases, primary, and resource state.
    run.put(receiver + 0x00, 0x50b064);
    run.put(receiver + 0x08, actor);
    run.put(receiver + 0x0c, actor);
    uint32_t primary = run.get(actor + 0x6c);
    run.put(receiver + 0x10, primary);
    run.put(receiver + 0x04, 0);
    run.call(0x4c7fa0, actor, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0x0c), {0x522d48});
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9);
    run.put(receiver + 0x20, 2);
    return receiver;
}

// 0x408370. thiscall, 1 stack argument(s), returns void.
uint32_t function_408370(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    // Actor aliases, primary aliases, inventory counts and inventory words.
    run.put(receiver + 0x00, actor);
    run.put(receiver + 0x04, actor);
    uint32_t primary = run.get(actor + 0x6c);
    run.put(receiver + 0x50, actor);
    run.put(receiver + 0x08, primary);
    run.put(receiver + 0x54, actor);
    run.put(receiver + 0x58, run.get(actor + 0x6c));
    primary = run.get(receiver + 0x58);
    run.put(receiver + 0x28, 0);
    run.put(receiver + 0x24, 0);
    uint32_t item = run.get(primary + 0xf0);
    run.put(receiver + 0x2c, item);
    uint32_t count = run.get(receiver + 0x24);
    item = run.get(receiver + count * 4 + 0x2c);
    ++count;
    run.put(receiver + 0x24, count);
    if (item)
        run.put(receiver + 0x28, run.get(receiver + 0x28) + 1);
    primary = run.get(receiver + 0x58);
    item = run.get(primary + 0xf8);
    run.put(receiver + count * 4 + 0x2c, item);
    count = run.get(receiver + 0x24);
    item = run.get(receiver + count * 4 + 0x2c);
    ++count;
    run.put(receiver + 0x24, count);
    if (item)
        run.put(receiver + 0x28, run.get(receiver + 0x28) + 1);
    primary = run.get(receiver + 0x58);
    item = run.get(primary + 0xf4);
    run.put(receiver + count * 4 + 0x2c, item);
    count = run.get(receiver + 0x24);
    item = run.get(receiver + count * 4 + 0x2c);
    ++count;
    run.put(receiver + 0x24, count);
    if (item)
        run.put(receiver + 0x28, run.get(receiver + 0x28) + 1);
    primary = run.get(receiver + 0x58);
    item = run.get(primary + 0xfc);
    run.put(receiver + count * 4 + 0x2c, item);
    count = run.get(receiver + 0x24);
    item = run.get(receiver + count * 4 + 0x2c);
    ++count;
    run.put(receiver + 0x24, count);
    if (item)
        run.put(receiver + 0x28, run.get(receiver + 0x28) + 1);
    primary = run.get(receiver + 0x58);
    item = run.get(primary + 0x100);
    run.put(receiver + count * 4 + 0x2c, item);
    count = run.get(receiver + 0x24);
    item = run.get(receiver + count * 4 + 0x2c);
    ++count;
    run.put(receiver + 0x24, count);
    if (item)
        run.put(receiver + 0x28, run.get(receiver + 0x28) + 1);
    primary = run.get(receiver + 0x58);
    item = run.get(primary + 0x108);
    run.put(receiver + count * 4 + 0x2c, item);
    count = run.get(receiver + 0x24);
    item = run.get(receiver + count * 4 + 0x2c);
    ++count;
    run.put(receiver + 0x24, count);
    if (item)
        run.put(receiver + 0x28, run.get(receiver + 0x28) + 1);
    primary = run.get(receiver + 0x58);
    item = run.get(primary + 0x104);
    run.put(receiver + count * 4 + 0x2c, item);
    count = run.get(receiver + 0x24);
    item = run.get(receiver + count * 4 + 0x2c);
    ++count;
    run.put(receiver + 0x24, count);
    if (item)
        run.put(receiver + 0x28, run.get(receiver + 0x28) + 1);
    primary = run.get(receiver + 0x58);
    item = run.get(primary + 0x10c);
    run.put(receiver + count * 4 + 0x2c, item);
    count = run.get(receiver + 0x24);
    item = run.get(receiver + count * 4 + 0x2c);
    ++count;
    run.put(receiver + 0x24, count);
    if (item)
        run.put(receiver + 0x28, run.get(receiver + 0x28) + 1);
    primary = run.get(receiver + 0x54);
    item = run.get(primary + 0x100);
    run.put(receiver + count * 4 + 0x2c, item);
    count = run.get(receiver + 0x24);
    item = run.get(receiver + count * 4 + 0x2c);
    ++count;
    run.put(receiver + 0x24, count);
    if (item)
        run.put(receiver + 0x28, run.get(receiver + 0x28) + 1);
    return 0;
}

// 0x40ab80. thiscall, 4 stack argument(s), returns void.
uint32_t function_40ab80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Wrapper actor and its destination rectangle.
    uint32_t actor = run.get(receiver + 0x04);
    run.put(actor + 0x128, arguments[0]);
    run.put(actor + 0x12c, arguments[1]);
    run.put(actor + 0x130, arguments[2]);
    run.put(actor + 0x134, arguments[3]);
    return 0;
}

// 0x40abb0. thiscall, 1 stack argument(s), returns void.
uint32_t function_40abb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t source = arguments[0];
    uint32_t actor = run.get(receiver + 0x04);
    // Snapshot the whole input rectangle before reverse-order stores.
    uint32_t bottom = run.get(source + 0x0c);
    uint32_t top = run.get(source + 0x04);
    uint32_t left = run.get(source + 0x00);
    uint32_t right = run.get(source + 0x08);
    run.put(actor + 0x124, bottom);
    run.put(actor + 0x120, right);
    run.put(actor + 0x11c, top);
    run.put(actor + 0x118, left);
    return 0;
}

// 0x40abf0. thiscall, 0 stack argument(s), returns void.
uint32_t function_40abf0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t actor = run.get(receiver + 0x04);
    // Vertical displacement, scene dispatch, and actor flag after dispatch.
    run.put(actor + 0x50, run.get(actor + 0x50) - 0x20u);
    actor = run.get(receiver + 0x00);
    uint32_t owner = run.get(actor + 0x0c);
    uint32_t scene = run.get(owner + 0x24);
    run.call(0x4cd800, scene, {actor, 0});
    actor = run.get(receiver + 0x00);
    run.put(actor + 0xcc, 1);
    return 0;
}

// 0x40f6c0. thiscall, 4 stack argument(s), returns void.
uint32_t function_40f6c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Actor rectangle in four raw words.
    run.put(receiver + 0x118, arguments[0]);
    run.put(receiver + 0x11c, arguments[1]);
    run.put(receiver + 0x120, arguments[2]);
    run.put(receiver + 0x124, arguments[3]);
    return 0;
}

// 0x4209d0. thiscall, 1 stack argument(s), returns void.
uint32_t function_4209d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Optional animation root, inclusive signed bounds, absolute-index table.
    uint32_t root = run.get(receiver + 0x170);
    if (root) {
        uint32_t index = arguments[0];
        uint32_t value = 0;
        if (s32(index) >= run.gets(root + 0x64) && s32(index) <= run.gets(root + 0x68)) {
            uint32_t table = run.get(root + 0x14);
            value = run.get(table + index * 4);
        }
        run.put(receiver + 0x16c, index);
        run.put(receiver + 0x174, value);
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4080a0:
        return function_4080a0(run, receiver, arguments);
    case 0x408220:
        return function_408220(run, receiver, arguments);
    case 0x4082d0:
        return function_4082d0(run, receiver, arguments);
    case 0x4082f0:
        return function_4082f0(run, receiver, arguments);
    case 0x408370:
        return function_408370(run, receiver, arguments);
    case 0x40ab80:
        return function_40ab80(run, receiver, arguments);
    case 0x40abb0:
        return function_40abb0(run, receiver, arguments);
    case 0x40abf0:
        return function_40abf0(run, receiver, arguments);
    case 0x40f6c0:
        return function_40f6c0(run, receiver, arguments);
    case 0x4209d0:
        return function_4209d0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_actor_dispatch_02_entry, owned, body)
