// Level 1 palette preparation and world reset.
// Adapts the typed palette and world implementations to canonical guest memory.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x46e160:
    case 0x4cb5f0:
        return 0;
    case 0x4c6fa0:
        return 1;
    case 0x4c60a0:
    case 0x4c70b0:
        return 2;
    default:
        return -1;
    }
}

// 0x4c60a0. Select the installed light, average or rank table globals.
uint32_t install(Run &run, uint32_t table, uint32_t mode) {
    switch (mode) {
    case 2:
        run.put(0x5430b0, table);
        break;
    case 4:
        run.put(0x5430b4, table);
        break;
    case 8:
        run.put(0x5430b8, table);
        break;
    case 50:
        run.put(0x5430bc, table);
        break;
    default:
        break;
    }
    return 0;
}

// 0x4c70b0. Input bytes index the palette at 0x5430c0. The coefficients
// are exactly representable dyadics, as are every multiply and sum for byte
// channels. Conversion truncates before retaining the low byte, like __ftol.
uint32_t compare(Run &run, uint32_t left, uint32_t right) {
    uint32_t first = run.get8(left);
    uint32_t second = run.get8(right);
    uint32_t palette = run.get(0x5430c0);
    uint32_t firstBlue = run.get8(palette + first * 4 + 0x02);
    uint32_t firstGreen = run.get8(palette + first * 4 + 0x01);
    uint32_t firstRed = run.get8(palette + first * 4);
    double firstBlueTerm = double(firstBlue) * double(run.getf(0x513714));
    double firstGreenTerm = double(firstGreen) * double(run.getf(0x513710));
    double firstPartial = firstBlueTerm + firstGreenTerm;
    double firstRedTerm = double(firstRed) * double(run.getf(0x51370c));
    uint32_t firstValue = uint32_t(firstPartial + firstRedTerm) & 0xff;
    uint32_t secondGreen = run.get8(palette + second * 4 + 0x01);
    uint32_t secondBlue = run.get8(palette + second * 4 + 0x02);
    uint32_t secondRed = run.get8(palette + second * 4);
    double secondGreenTerm = double(secondGreen) * double(run.getf(0x513710));
    double secondBlueTerm = double(secondBlue) * double(run.getf(0x513714));
    double secondPartial = secondGreenTerm + secondBlueTerm;
    double secondRedTerm = double(secondRed) * double(run.getf(0x51370c));
    uint32_t secondValue = uint32_t(secondPartial + secondRedTerm) & 0xff;
    return firstValue < secondValue ? 0xffffffff : firstValue > secondValue ? 1 : 0;
}

// Native byte-domain specialization of the platform qsort used at 0x4c7068.
// Preserve its midpoint pivot, strict comparisons and selection-sort swaps:
// an unstable standard-library sort would change equal-luminance ranks.
void byteSort(Run &run, uint32_t start, uint32_t count) {
    if (count < 2)
        return;
    uint32_t low = start;
    uint32_t high = start + count - 1;
    struct Frame {
        uint32_t low;
        uint32_t high;
    } stack[30];
    uint32_t depth = 0;
    auto swap = [&](uint32_t a, uint32_t b) {
        if (a != b) {
            uint32_t y = run.get8(b);
            uint32_t x = run.get8(a);
            run.put8(a, y);
            run.put8(b, x);
        }
    };
    for (;;) {
        run.tick();
        uint32_t n = high - low + 1;
        if (n > 8) {
            swap(low + n / 2, low);
            uint32_t left = low;
            uint32_t right = high + 1;
            for (;;) {
                do {
                    ++left;
                } while (left <= high && s32(compare(run, left, low)) <= 0);
                do {
                    --right;
                } while (right > low && s32(compare(run, right, low)) >= 0);
                if (left > right)
                    break;
                swap(left, right);
            }
            swap(low, right);
            if (s32(right - low - 1) < s32(high - left)) {
                if (left < high) {
                    if (depth >= 30)
                        run.fail(CLAW_FAULT_BUDGET, 0x4c6fa0);
                    stack[depth++] = {left, high};
                }
                if (low + 1 < right) {
                    high = right - 1;
                    continue;
                }
            } else {
                if (low + 1 < right) {
                    if (depth >= 30)
                        run.fail(CLAW_FAULT_BUDGET, 0x4c6fa0);
                    stack[depth++] = {low, right - 1};
                }
                low = left;
                if (left < high)
                    continue;
            }
        } else {
            for (uint32_t end = high; low < end; --end) {
                uint32_t best = low;
                for (uint32_t p = low + 1; p <= end; ++p) {
                    if (s32(compare(run, p, best)) > 0)
                        best = p;
                }
                swap(best, end);
            }
        }
        if (!depth)
            return;
        auto frame = stack[--depth];
        low = frame.low;
        high = frame.high;
    }
}

// 0x4c6fa0. Manager +0x0c is its table count; +0x08 holds table pointers.
// A table's +0x08 is the byte buffer: ordered indices then inverse ranks.
uint32_t rank(Run &run, uint32_t owner, uint32_t palette) {
    uint32_t allocation = run.call(0x4f63ec, 0, {0x0c});
    uint32_t table = allocation ? run.call(0x4c76d0, allocation) : 0;
    if (!table)
        return 0;
    if (!run.call(0x4c76f0, table, {0x200}))
        return 0;
    uint32_t index = run.get(owner + 0x0c);
    run.call(0x4dee30, owner + 0x04, {index + 1, 0xffffffff});
    run.put(run.get(owner + 0x08) + index * 4, table);
    uint32_t destination = run.get(table + 0x08);
    run.put(0x5430c0, palette);
    for (uint32_t i = 0; i < 0x100; ++i)
        run.put8(destination + i, i);
    byteSort(run, destination, 0x100);
    for (uint32_t i = 0; i < 0x100; ++i) {
        for (uint32_t j = 0; j < 0x100; ++j) {
            if (run.get8(destination + j) == i) {
                run.put8(destination + 0x100 + i, j);
                break;
            }
        }
    }
    return table;
}

// 0x46e160. Application +0x78 is display depth, +0x58 palette manager.
// Owner +0x360 is palette data, +0x1c resources, +0x768/+0x76c/+0x770
// retain light, average and rank tables respectively.
uint32_t startup(Run &run, uint32_t owner) {
    uint32_t app = run.get(owner + 0x04);
    if (run.get(app + 0x78) != 8)
        return 1;
    uint32_t manager = run.get(app + 0x58);
    if (!manager)
        return 0;
    uint32_t palette = owner + 0x360;
    uint32_t resources = run.get(owner + 0x1c);
    run.put(owner + 0x768, 0);
    run.put(owner + 0x76c, 0);
    run.put(owner + 0x770, 0);
    for (uint32_t i = 0; i < 2; ++i) {
        if (i)
            resources = run.get(owner + 0x1c);
        uint32_t resource = run.call(0x4b7dc0, resources, {i ? 0x52a088u : 0x52a09cu, 0x434c54});
        if (resource) {
            uint32_t data = run.call(0x4b61c0, resource);
            uint32_t size = run.get(resource + 0x14);
            if (data) {
                // The unchanged loader exposes a CMemFile local through its
                // physical boundary. Match this caller's four saved registers,
                // two arguments and CALL return word when entering that loader.
                uint32_t previousStack = run.stackPointer;
                run.stackPointer = run.automatic(-0x1c);
                uint32_t value = run.call(0x4c7360, manager, {data, size});
                run.stackPointer = previousStack;
                run.put(owner + 0x768 + i * 4, value);
            }
            run.call(0x4b6230, resource);
        }
        if (!run.get(owner + 0x768 + i * 4)) {
            uint32_t value;
            if (i)
                value = run.call(0x4c6d90, manager, {palette, 100, 100});
            else
                value = run.call(0x4c68e0, manager, {palette, 0x100, 400, 1, 16});
            run.put(owner + 0x768 + i * 4, value);
            if (!value)
                return 0;
        }
    }
    uint32_t value = rank(run, manager, palette);
    run.put(owner + 0x770, value);
    if (!value)
        return 0;
    uint32_t average = run.get(owner + 0x76c);
    if (average)
        install(run, average, 2);
    average = run.get(owner + 0x76c);
    if (average)
        install(run, average, 4);
    value = run.get(owner + 0x770);
    if (value)
        install(run, value, 50);
    return 1;
}

// 0x4cb5f0. Two owned object arrays at +0x34 and +0x48, with storage
// at +0x04 and signed count at +0x08. Reset active plane and its index last.
uint32_t clear(Run &run, uint32_t world) {
    for (uint32_t offset : {0x34u, 0x48u}) {
        uint32_t index = 0;
        while (s32(index) < s32(run.get(world + offset + 0x08))) {
            uint32_t object = run.get(run.get(world + offset + 0x04) + index * 4);
            if (object)
                run.vcall(object, 0x04, {1});
            ++index;
        }
        run.call(0x4f5915, world + offset, {0, 0xffffffff});
    }
    run.put(world + 0x5c, 0);
    run.put(world + 0x60, 0xffffffff);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x46e160:
        return startup(run, receiver);
    case 0x4c60a0:
        return install(run, arguments[0], arguments[1]);
    case 0x4c6fa0:
        return rank(run, receiver, arguments[0]);
    case 0x4c70b0:
        return compare(run, arguments[0], arguments[1]);
    case 0x4cb5f0:
        return clear(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_load_assets_entry, owned, body)
