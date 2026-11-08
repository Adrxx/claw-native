// PCX decoding and surface color conversion, recovered from original v1.0.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4b9e60: return 0;
    case 0x4b9e90: return 4;
    case 0x4ba2d0: return 3;
    case 0x4ba580: return 3;
    case 0x4babe0: return 1;
    case 0x4bad30: return 1;
    case 0x4bb040: return 0;
    case 0x4bb050: return 0;
    case 0x4bb0f0: return 1;
    case 0x4bebc0: return 3;
    case 0x4bef50: return 4;
    case 0x4bf070: return 4;
    default: return -1;
    }
}

// 0x4bb040. Surface width.
uint32_t function_4bb040(Run &run, uint32_t receiver) {
    return run.get(receiver + 0x18);
}

// 0x4bb050. Surface height.
uint32_t function_4bb050(Run &run, uint32_t receiver) {
    return run.get(receiver + 0x14);
}

// 0x4bb0f0. Pitch times row, retaining the low 32 bits.
uint32_t function_4bb0f0(Run &run, uint32_t receiver, uint32_t row) {
    return run.get(receiver + 0x1c) * row;
}

// 0x4b9e60. Optional cdecl restore callback at +0xb4.
uint32_t function_4b9e60(Run &run, uint32_t receiver) {
    uint32_t callback = run.get(receiver + 0xb4);
    if (callback && run.call(callback, 0, {receiver}))
        return 1;
    run.call(0x4bd0a0, 0, {});
    return 0;
}

void unlockCOM(Run &run, uint32_t receiver) {
    uint32_t surface = run.get(receiver + 0x08);
    uint32_t method = run.get(run.get(surface) + 0x80);
    run.call(method, 0, {surface, 0});
}

// The repeated RLE plane loops in 0x4babe0, 0x4bad30, 0x4bef50 and 0x4bf070.
// Runs are deliberately not clipped to the remaining row width.
void plane(Run &run, uint32_t &source, uint32_t destination, uint32_t remaining, uint32_t stride) {
    while (s32(remaining) > 0) {
        uint32_t value = run.get8(source);
        source += 1;
        if ((value & 0xc0) == 0xc0) {
            uint32_t count = value & 0x3f;
            value = run.get8(source);
            source += 1;
            for (uint32_t emitted = 0; s32(emitted) < s32(count); emitted += 1) {
                run.put8(destination, value);
                destination += stride;
            }
            remaining -= count;
        } else {
            run.put8(destination, value);
            destination += stride;
            remaining -= 1;
        }
    }
}

// 0x4babe0. Width and height are captured before locking.
uint32_t function_4babe0(Run &run, uint32_t receiver, uint32_t source) {
    if (!source)
        return 0;
    uint32_t columns = function_4bb040(run, receiver);
    uint32_t rows = function_4bb050(run, receiver);
    uint32_t pixels = run.call(0x4b9730, receiver, {0});
    if (!pixels)
        return 0;
    for (uint32_t row = 0; s32(row) < s32(rows); row += 1) {
        uint32_t destination = pixels + function_4bb0f0(run, receiver, row);
        plane(run, source, destination, columns, 1);
    }
    run.call(0x4bb0e0, receiver, {});
    return 1;
}

// 0x4bad30. Surface planes are ordered 2, 1, 0 and dimensions are reloaded.
uint32_t function_4bad30(Run &run, uint32_t receiver, uint32_t source) {
    if (!source)
        return 0;
    uint32_t pixels = run.call(0x4b9730, receiver, {0});
    if (!pixels)
        return 0;
    for (uint32_t row = 0; s32(row) < s32(function_4bb050(run, receiver)); row += 1) {
        uint32_t destination = pixels + 2 + function_4bb0f0(run, receiver, row);
        plane(run, source, destination, function_4bb040(run, receiver), 3);
        destination = pixels + 1 + function_4bb0f0(run, receiver, row);
        plane(run, source, destination, function_4bb040(run, receiver), 3);
        destination = pixels + function_4bb0f0(run, receiver, row);
        plane(run, source, destination, function_4bb040(run, receiver), 3);
    }
    run.call(0x4bb0e0, receiver, {});
    return 1;
}

// 0x4bef50. Contiguous indexed rows.
uint32_t function_4bef50(Run &run, uint32_t destination, uint32_t source, uint32_t columns, uint32_t rows) {
    if (!destination || !source)
        return 0;
    for (uint32_t row = 0; s32(row) < s32(rows); row += 1) {
        plane(run, source, destination + columns * row, columns, 1);
    }
    return 1;
}

// 0x4bf070. Raw planes are ordered 0, 1, 2.
uint32_t function_4bf070(Run &run, uint32_t destination, uint32_t source, uint32_t columns, uint32_t rows) {
    if (!destination || !source)
        return 0;
    for (uint32_t row = 0; s32(row) < s32(rows); row += 1) {
        uint32_t offset = row * columns * 3;
        plane(run, source, destination + offset, columns, 3);
        plane(run, source, destination + offset + 1, columns, 3);
        plane(run, source, destination + offset + 2, columns, 3);
    }
    return 1;
}

// 0x4ba2d0. Expand indexed pixels to BGR triples.
uint32_t function_4ba2d0(Run &run, uint32_t receiver, uint32_t source, uint32_t palette, uint32_t orientation) {
    if (!palette)
        return 0;
    uint32_t pixels = run.call(0x4b9730, receiver, {0});
    if (!pixels)
        return 0;
    uint32_t row = orientation == 2 ? function_4bb050(run, receiver) - 1 : 0;
    while (orientation == 2 ? s32(row) >= 0 : s32(row) < s32(function_4bb050(run, receiver))) {
        uint32_t destination = pixels + row * run.get(receiver + 0x1c);
        for (uint32_t x = 0; s32(x) < s32(function_4bb040(run, receiver)); x += 1) {
            uint32_t entry = palette + run.get8(source) * 4;
            source += 1;
            run.put8(destination, run.get8(entry + 0x02));
            run.put8(destination + 0x01, run.get8(entry + 0x01));
            run.put8(destination + 0x02, run.get8(entry));
            destination += 3;
        }
        row += orientation == 2 ? 0xffffffffu : 1;
    }
    unlockCOM(run, receiver);
    return 1;
}

uint32_t distance(Run &run, uint32_t entry, uint32_t b, uint32_t g, uint32_t r) {
    uint32_t dg = g - run.get8(entry + 0x01);
    uint32_t db = b - run.get8(entry + 0x02);
    uint32_t dr = r - run.get8(entry);
    return dg * dg + db * db + dr * dr;
}

// 0x4ba580. Strict improvement preserves the earliest palette index on ties.
uint32_t function_4ba580(Run &run, uint32_t receiver, uint32_t source, uint32_t palette, uint32_t orientation) {
    if (!palette)
        return 0;
    uint32_t pixels = run.call(0x4b9730, receiver, {0});
    if (!pixels)
        return 0;
    uint32_t row = orientation == 2 ? function_4bb050(run, receiver) - 1 : 0;
    while (orientation == 2 ? s32(row) >= 0 : s32(row) < s32(function_4bb050(run, receiver))) {
        uint32_t destination = pixels + row * run.get(receiver + 0x1c);
        for (uint32_t x = 0; s32(x) < s32(function_4bb040(run, receiver)); x += 1) {
            uint32_t b = run.get8(source);
            uint32_t g = run.get8(source + 0x01);
            uint32_t r = run.get8(source + 0x02);
            source += 3;
            uint32_t bestIndex = 0;
            uint32_t best = distance(run, palette, b, g, r);
            for (uint32_t index = 1; s32(index) < 0x100; index += 1) {
                uint32_t candidate = distance(run, palette + index * 4, b, g, r);
                if (s32(candidate) < s32(best)) {
                    bestIndex = index;
                    best = candidate;
                    if (candidate == 0)
                        break;
                }
            }
            run.put8(destination, bestIndex);
            destination += 1;
        }
        row += orientation == 2 ? 0xffffffffu : 1;
    }
    unlockCOM(run, receiver);
    return 1;
}

// 0x4b9e90. The first comparison really uses the boolean depth-is-zero.
uint32_t function_4b9e90(Run &run, uint32_t receiver, uint32_t source, uint32_t depth, uint32_t palette, uint32_t orientation) {
    uint32_t target = run.get(receiver + 0xa4);
    if (uint32_t(target == 0) == depth)
        return run.call(0x4b9b00, receiver, {source, orientation});
    if (target == 8) {
        if (depth == 16)
            return run.call(0x4ba890, receiver, {source, palette, orientation});
        if (depth == 24)
            return function_4ba580(run, receiver, source, palette, orientation);
        return 0;
    }
    if (target == 16) {
        if (depth == 8)
            return run.call(0x4b9fa0, receiver, {source, palette, orientation});
        if (depth == 24)
            return run.call(0x4ba150, receiver, {source, orientation});
        return 0;
    }
    if (target == 24) {
        if (depth == 8)
            return function_4ba2d0(run, receiver, source, palette, orientation);
        if (depth == 16)
            return run.call(0x4ba3f0, receiver, {source, orientation});
    }
    return 0;
}

uint32_t signedWord(Run &run, uint32_t address) {
    uint32_t value = run.get16(address);
    return value & 0x8000 ? value | 0xffff0000u : value;
}

// 0x4bebc0. Header geometry, optional palette, raw temporary, conversion.
uint32_t function_4bebc0(Run &run, uint32_t receiver, uint32_t context, uint32_t header, uint32_t length) {
    if (!header)
        return 0;
    uint32_t columns = signedWord(run, header + 0x08) - signedWord(run, header + 0x04) + 1;
    uint32_t rows = signedWord(run, header + 0x0a) - signedWord(run, header + 0x06) + 1;
    uint32_t planes = run.get8(header + 0x41);
    uint32_t depth = planes == 1 ? 8 : planes == 3 ? 24 : 0;
    if (!depth || run.get(receiver + 0x18) != columns || run.get(receiver + 0x14) != rows)
        return 0;
    uint32_t target = run.get(context + 0x474);
    bool conversion = target != depth;
    if (conversion && target == 8 && !run.get(context + 0x878))
        return 0;
    uint32_t palette = 0;
    if (conversion) {
        if (depth == 8) {
            uint32_t input = header + length - 0x300;
            for (uint32_t output = 0x541bb0; s32(output) < 0x541fb0; output += 4) {
                run.put8(output, run.get8(input));
                input += 1;
                run.put8(output + 0x01, run.get8(input));
                input += 1;
                run.put8(output + 0x02, run.get8(input));
                input += 1;
                run.put8(output + 0x03, 0);
            }
            palette = 0x541bb0;
        } else if (target == 8) {
            palette = run.get(context + 0x878) ? context + 0x478 : 0;
        }
    }
    uint32_t source = header + 0x80;
    uint32_t temporary = 0;
    if (conversion) {
        uint32_t size = rows * columns;
        if (depth != 8)
            size *= 3;
        temporary = run.call(0x4f63ec, 0, {size});
        if (!temporary)
            return 0;
        uint32_t decoded = depth == 8 ? function_4bef50(run, temporary, source, columns, rows) : function_4bf070(run, temporary, source, columns, rows);
        if (!decoded) {
            run.call(0x4f6428, 0, {temporary});
            return 0;
        }
    } else {
        uint32_t decoded = depth == 8 ? function_4babe0(run, receiver, source) : function_4bad30(run, receiver, source);
        if (!decoded)
            return 0;
    }
    if (conversion && !function_4b9e90(run, receiver, temporary, depth, palette, 1)) {
        run.call(0x4f6428, 0, {temporary});
        return 0;
    }
    if (temporary)
        run.call(0x4f6428, 0, {temporary});
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b9e60: return function_4b9e60(run, receiver);
    case 0x4b9e90: return function_4b9e90(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3]);
    case 0x4ba2d0: return function_4ba2d0(run, receiver, arguments[0], arguments[1], arguments[2]);
    case 0x4ba580: return function_4ba580(run, receiver, arguments[0], arguments[1], arguments[2]);
    case 0x4babe0: return function_4babe0(run, receiver, arguments[0]);
    case 0x4bad30: return function_4bad30(run, receiver, arguments[0]);
    case 0x4bb040: return function_4bb040(run, receiver);
    case 0x4bb050: return function_4bb050(run, receiver);
    case 0x4bb0f0: return function_4bb0f0(run, receiver, arguments[0]);
    case 0x4bebc0: return function_4bebc0(run, receiver, arguments[0], arguments[1], arguments[2]);
    case 0x4bef50: return function_4bef50(run, arguments[0], arguments[1], arguments[2], arguments[3]);
    case 0x4bf070: return function_4bf070(run, arguments[0], arguments[1], arguments[2], arguments[3]);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_pcx_image_canonical_entry, owned, body)
