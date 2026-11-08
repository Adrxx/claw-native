#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t f) {
    switch (f) {
    case 0x4b3240:
        return 2;
    case 0x4b3430:
        return 1;
    case 0x430d30:
    case 0x430d80:
    case 0x430ec0:
    case 0x431300:
    case 0x4b3490:
    case 0x4b3ab0:
    case 0x4b3410:
        return 0;
    default:
        return -1;
    }
}

// Imported calls retain their IAT-slot identities for the host dispatcher.
// Calls carry the instruction-derived entry ESP relative to the owned frame.
uint32_t api(Run &r, uint32_t target, int32_t offset, std::initializer_list<uint32_t> args = {}) {
    uint32_t saved = r.stackPointer;
    r.stackPointer = r.automatic(offset);
    uint32_t value = r.call(target, 0, args);
    r.stackPointer = saved;
    return value;
}
void add(Run &r, uint32_t address, uint32_t bit) {
    r.put(address, r.get(address) | bit);
}

// Source +240/+244 are screen midpoints, refreshed before the cursor warp.
void center(Run &r, uint32_t s, int32_t savedBytes) {
    uint32_t metrics = 0x546c44;
    uint32_t x = uint32_t(s32(api(r, metrics, -savedBytes - 8, {0})) / 2);
    r.put(s + 0x240, x);
    uint32_t y = uint32_t(s32(api(r, metrics, -savedBytes - 8, {1})) / 2);
    r.put(s + 0x244, y);
    api(r, 0x546d9c, -savedBytes - 12, {r.get(s + 0x240), y});
}

// 0x4b3410. Only the JOYCAPSA and JOYINFOEX buffers are cleared.
uint32_t clearBuffers(Run &r, uint32_t s) {
    for (uint32_t i = 0; i < 101; ++i)
        r.put(s + 4 + i * 4, 0);
    for (uint32_t i = 0; i < 13; ++i)
        r.put(s + 0x198 + i * 4, 0);
    return 0;
}

// 0x4b3430. +1cc modes; +1d0 detected joystick availability.
uint32_t modes(Run &r, uint32_t s, uint32_t mode) {
    if ((mode & 2) && !r.get(s + 0x1d0))
        mode &= ~2u;
    if (mode & 4)
        center(r, s, 12);
    r.put(s + 0x1cc, mode);
    return 0;
}

// 0x4b3ab0. +210 events, +214 current, +20c previous/latch.
uint32_t resetSource(Run &r, uint32_t s) {
    uint32_t mode = r.get8(s + 0x1cc);
    r.put(s + 0x210, 0);
    r.put(s + 0x214, 0);
    r.put(s + 0x20c, 0);
    if (mode & 1) {
        uint32_t keyApi = 0x546ce4;
        for (uint32_t i = 0; i < 12; ++i)
            api(r, keyApi, -16, {r.get(s + 0x1dc + i * 4)});
    }
    if (r.get8(s + 0x1cc) & 4)
        center(r, s, 8);
    return 0;
}

void filterSource(Run &r, uint32_t s, uint32_t bit) {
    uint32_t raw = r.get(s + 0x214);
    uint32_t latch = r.get(s + 0x20c);
    if (!(raw & bit))
        r.put(s + 0x20c, latch & ~bit);
    else if (!(latch & bit))
        r.put(s + 0x20c, latch | bit);
    else
        r.put(s + 0x210, r.get(s + 0x210) & ~bit);
}

// 0x4b3490. +1dc starts twelve keyboard codes; +230/+234 mouse deltas
// and +238/+23c tolerances are independent of the unused cursor POINT.
uint32_t pollSource(Run &r, uint32_t s) {
    uint32_t keyApi = 0x546ce4;
    r.put(s + 0x210, 0);
    r.put(s + 0x214, 0);
    const uint32_t bits[] = {0x10000000, 0x20000000, 0x40000000, 0x80000000, 1, 2, 4, 8, 0x10, 0x20, 0x40, 0x80};
    if (r.get8(s + 0x1cc) & 1) {
        for (uint32_t i = 0; i < 12; ++i) {
            uint32_t state = api(r, keyApi, -28, {r.get(s + 0x1dc + i * 4)});
            if (state & (i < 4 ? 0x8000u : 0x8001u))
                add(r, s + 0x210, bits[i]);
        }
    }
    if (r.get8(s + 0x1cc) & 4) {
        api(r, 0x546cd0, -28, {r.automatic(-8)});
        uint32_t tolerance = r.get(s + 0x238);
        uint32_t delta = r.get(s + 0x230);
        if (s32(delta) < s32(0u - tolerance))
            add(r, s + 0x210, 0x10000000);
        if (s32(delta) > s32(tolerance))
            add(r, s + 0x210, 0x20000000);
        tolerance = r.get(s + 0x23c);
        delta = r.get(s + 0x234);
        if (s32(delta) < s32(0u - tolerance))
            add(r, s + 0x210, 0x40000000);
        if (s32(delta) > s32(tolerance))
            add(r, s + 0x210, 0x80000000);
        if (api(r, keyApi, -28, {1}) & 0x8001)
            add(r, s + 0x210, 1);
        if (api(r, keyApi, -28, {2}) & 0x8001)
            add(r, s + 0x210, 2);
        api(r, 0x546d9c, -32, {r.get(s + 0x240), r.get(s + 0x244)});
    }
    if (r.get8(s + 0x1cc) & 2) {
        uint32_t id = r.get(s);
        r.put(s + 0x19c, 0x83);
        api(r, 0x546de8, -32, {id, s + 0x198});
        uint32_t x = r.get(s + 0x1a0);
        if (x < r.get(s + 0x220))
            add(r, s + 0x210, 0x10000000);
        if (x > r.get(s + 0x224))
            add(r, s + 0x210, 0x20000000);
        uint32_t y = r.get(s + 0x1a4);
        if (y < r.get(s + 0x228))
            add(r, s + 0x210, 0x40000000);
        if (y > r.get(s + 0x22c))
            add(r, s + 0x210, 0x80000000);
        uint32_t buttons = r.get(s + 0x1b8);
        for (uint32_t bit = 1; bit <= 8; bit <<= 1)
            if (buttons & bit)
                add(r, s + 0x210, bit);
        if (r.get(s + 0x1d4)) {
            for (uint32_t bit = 0x10; bit <= 0x80; bit <<= 1)
                if (buttons & bit)
                    add(r, s + 0x210, bit);
            if (r.get(s + 0x40) >= 9 && !r.get(s + 0x1d8) && (buttons & 0x100))
                add(r, s + 0x210, 0x100);
        }
    }
    r.put(s + 0x214, r.get(s + 0x210));
    for (uint32_t i = 0; i < 8; ++i)
        filterSource(r, s, bits[i]);
    if (r.get(s + 0x1d4)) {
        for (uint32_t bit = 0x10; bit <= 0x100; bit <<= 1)
            filterSource(r, s, bit);
    }
    return 0;
}

// 0x4b3240. +0 ID; +1d4 extended buttons; +218/+21c half-spans;
// +220..+22c unsigned thresholds; +1d8 ninth-button inhibition.
uint32_t initialize(Run &r, uint32_t s, const uint32_t *a) {
    clearBuffers(r, s);
    r.put(s + 0x198, 52);
    r.put(s, a[1]);
    r.put(s + 0x214, 0);
    r.put(s + 0x210, 0);
    r.put(s + 0x20c, 0);
    r.put(s + 0x1d8, 0);
    const uint32_t keys[] = {0x25, 0x27, 0x26, 0x28, 0x20, 0x2d, 0, 0, 0, 0, 0, 0};
    for (uint32_t i = 0; i < 12; ++i)
        r.put(s + 0x1dc + 4 * i, keys[i]);
    r.put(s + 0x1d0, 0);
    if (!api(r, 0x546df8, -28) || api(r, 0x546de8, -36, {r.get(s), s + 0x198}) || api(r, 0x546df4, -40, {r.get(s), s + 4, 404})) {
        uint32_t mode = r.get(s + 0x1cc) & ~2u;
        r.put(s + 0x1cc, mode);
        if (!mode)
            r.put(s + 0x1cc, 1);
        return 1;
    }
    uint32_t count = r.get(s + 0x40);
    uint32_t maxX = r.get(s + 0x2c);
    uint32_t minX = r.get(s + 0x28);
    uint32_t minY = r.get(s + 0x30);
    uint32_t maxY = r.get(s + 0x34);
    uint32_t halfX = (maxX - minX) >> 1;
    uint32_t halfY = (maxY - minY) >> 1;
    r.put(r.automatic(-8), halfX);
    r.put(r.automatic(-4), 0);
    r.put(s + 0x1d0, 1);
    r.put(s + 0x218, halfX);
    double x = double(halfX) * double(r.getf(0x5134e0));
    r.put(s + 0x1d4, count > 4 ? 1 : 0);
    r.put(s + 0x21c, halfY);
    uint32_t saved = r.stackPointer;
    r.stackPointer = r.automatic(-28);
    uint32_t lowX = r.call_x87(0x4a30e0, 0, x);
    r.stackPointer = saved;
    r.put(r.automatic(-8), halfY);
    r.put(r.automatic(-4), 0);
    r.put(s + 0x220, lowX);
    r.put(s + 0x224, maxX - lowX);
    double y = double(halfY) * double(r.getf(0x5134e0));
    r.stackPointer = r.automatic(-28);
    uint32_t lowY = r.call_x87(0x4a30e0, 0, y);
    r.stackPointer = saved;
    r.put(s + 0x228, lowY);
    r.put(s + 0x22c, maxY - lowY);
    r.put(s + 0x238, 6);
    r.put(s + 0x23c, 6);
    uint32_t parent = r.frame;
    r.frame = r.automatic(-32);
    modes(r, s, a[0]);
    r.frame = parent;
    return 1;
}

// 0x430d30. Binding +10..+34 are the ten default source masks.
uint32_t defaultMasks(Run &r, uint32_t b) {
    const uint32_t values[] = {1, 2, 4, 8, 0, 0x10, 0x20, 0x40, 0x80, 0};
    for (uint32_t i = 0; i < 10; ++i)
        r.put(b + 0x10 + i * 4, values[i]);
    return 0;
}
// 0x430d80. Binding +38..+6c are the fourteen default key codes.
uint32_t defaultKeys(Run &r, uint32_t b) {
    const uint32_t values[] = {0x25, 0x27, 0x26, 0x28, 0x20, 0x11, 0x12, 0x10, 0, 0x5a, 0x31, 0x32, 0x33, 0x34};
    for (uint32_t i = 0; i < 14; ++i)
        r.put(b + 0x38 + i * 4, values[i]);
    return 0;
}
// 0x431300. Binding +0 source; +4 events, +8 current, +c latch, +70 snapshot.
uint32_t resetBindings(Run &r, uint32_t b) {
    uint32_t s = r.get(b);
    uint32_t parent = r.frame;
    r.frame = r.automatic(-8);
    resetSource(r, s);
    r.frame = parent;
    r.put(b + 4, 0);
    r.put(b + 8, 0);
    r.put(b + 12, 0);
    r.put(b + 0x70, 0);
    // Original 0x431318 publishes success; the scene compatibility surface observes it.
    return 1;
}
// 0x430ec0. Source raw state feeds masks before the independent key queries.
uint32_t pollBindings(Run &r, uint32_t b) {
    uint32_t s = r.get(b);
    uint32_t parent = r.frame;
    r.frame = r.automatic(-12);
    pollSource(r, s);
    r.frame = parent;
    r.put(b + 8, 0);
    r.put(b + 4, 0);
    s = r.get(b);
    const uint32_t bits[] = {0x01000000, 0x02000000, 0x04000000, 0x08000000, 1, 2, 4, 8, 0x20, 0x40, 0x80, 0x100, 0x200};
    for (uint32_t i = 0; i < 4; ++i)
        if (r.get(s + 0x214) & (0x10000000u << i))
            add(r, b + 8, bits[i]);
    const uint32_t maskOffsets[] = {0x10, 0x14, 0x18, 0x1c, 0x24, 0x28, 0x2c, 0x30, 0x34};
    for (uint32_t i = 0; i < 9; ++i) {
        uint32_t mask = r.get(b + maskOffsets[i]);
        if (r.get(s + 0x214) & mask)
            add(r, b + 8, bits[i + 4]);
    }
    uint32_t keyApi = 0x546ce4;
    const uint32_t keyOffsets[] = {0x38, 0x3c, 0x40, 0x44, 0x48, 0x4c, 0x50, 0x54, 0x5c, 0x60, 0x64, 0x68, 0x6c};
    for (uint32_t i = 0; i < 13; ++i)
        if (api(r, keyApi, -16, {r.get(b + keyOffsets[i])}) & 0x8000)
            add(r, b + 8, bits[i]);
    uint32_t current = r.get(b + 8);
    r.put(b + 0x70, current);
    for (uint32_t i = 0; i < 13; ++i) {
        uint32_t bit = bits[i];
        uint32_t latch = r.get(b + 12);
        if (!(current & bit))
            r.put(b + 12, latch & ~bit);
        else if (!(latch & bit)) {
            uint32_t event = r.get(b + 4) | bit;
            if (i == 12) {
                r.put(b + 12, latch | bit);
                r.put(b + 4, event);
            } else {
                r.put(b + 4, event);
                r.put(b + 12, latch | bit);
            }
        }
    }
    // Both original exits (0x4312dc and 0x4312eb) publish success.
    return 1;
}

uint32_t body(Run &r, uint32_t f, uint32_t s, const uint32_t *a) {
    switch (f) {
    case 0x430d30:
        return defaultMasks(r, s);
    case 0x430d80:
        return defaultKeys(r, s);
    case 0x430ec0:
        return pollBindings(r, s);
    case 0x431300:
        return resetBindings(r, s);
    case 0x4b3430:
        return modes(r, s, a[0]);
    case 0x4b3490:
        return pollSource(r, s);
    case 0x4b3ab0:
        return resetSource(r, s);
    case 0x4b3410:
        return clearBuffers(r, s);
    case 0x4b3240:
        return initialize(r, s, a);
    default:
        r.fail(CLAW_FAULT_ABI, f);
    }
}
}
CLAW_MODULE_ENTRY(claw_application_input_configuration_entry, owned, body)
