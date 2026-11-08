// Level 1 actor collision probes
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4cc2b0:
        return 4;
    case 0x4ccdd0:
        return 4;
    case 0x4ccf80:
        return 6;
    case 0x4cd060:
        return 5;
    case 0x4cd120:
        return 4;
    default:
        return -1;
    }
}

// Arithmetic shift right by CL (the count is taken modulo 32, as on x86).
uint32_t sarBy(uint32_t value, uint32_t count) {
    return uint32_t(s32(value) >> (count & 0x1f));
}

uint32_t shlBy(uint32_t value, uint32_t count) {
    return value << (count & 0x1f);
}

// Tile map (the object at +0x5c of the receiver): +0x20 cell table, +0x24 row
// offset table, +0x30 width in tiles, +0x34 height in tiles, +0x8c column
// shift, +0x90 row shift. Receiver +0x4c is the table of tile objects.

// 0x4ccdd0. thiscall, 4 stack arguments (x, yHigh, yLow, out). Scans rows
// downwards from yHigh-1 to yLow, asking the tile object of each row to probe
// (x, y) inside the tile. Stores the row above the first probe answering
// something other than 3 and returns 1; returns 0 when every row answers 3.
uint32_t function_4ccdd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t xIn = arguments[0];
    uint32_t yHigh = arguments[1];
    uint32_t yLow = arguments[2];
    uint32_t out = arguments[3];
    if (s32(yHigh) <= s32(yLow))
        return 0;
    uint32_t row = yHigh - 1;
    if (s32(row) < s32(yLow))
        return 0;
    for (;;) {
        uint32_t x = xIn;
        if (s32(x) < 0) {
            x = 0;
        } else {
            uint32_t limit = run.get(run.get(receiver + 0x5c) + 0x30);
            if (s32(x) >= s32(limit))
                x = limit - 1;
        }
        uint32_t y = row;
        if (s32(y) < 0) {
            y = 0;
        } else {
            uint32_t limit = run.get(run.get(receiver + 0x5c) + 0x34);
            if (s32(y) >= s32(limit))
                y = limit - 1;
        }
        uint32_t map = run.get(receiver + 0x5c);
        uint32_t columnShift = run.get(map + 0x8c);
        uint32_t column = sarBy(x, columnShift);
        uint32_t rowShift = run.get(map + 0x90);
        uint32_t tileRow = sarBy(y, rowShift);
        uint32_t columnBase = shlBy(column, columnShift);
        rowShift = run.get(map + 0x90);
        x = x - columnBase;
        uint32_t rowBase = shlBy(tileRow, rowShift);
        uint32_t rowOffset = run.get(run.get(map + 0x24) + tileRow * 4);
        uint32_t cellIndex = rowOffset + column;
        uint32_t table = run.get(map + 0x20);
        y = y - rowBase;
        uint32_t cell = run.get(table + cellIndex * 4);
        uint32_t result = 0;
        if (cell != 0xeeeeeeee && cell != 0xffffffff) {
            uint32_t object = run.get(run.get(receiver + 0x4c) + (cell & 0xffff) * 4);
            result = run.vcall(object, 0x20, {x, y});
        }
        if (result != 3) {
            run.put(out, row + 1);
            return 1;
        }
        row = row - 1;
        if (s32(row) < s32(yLow))
            return 0;
    }
}

// 0x4cc2b0. thiscall, 4 stack arguments (actor, x, y, extra). Locals: the
// argument slot at entry+4 is reused to hold a candidate row and the slot at
// entry+8 (x) is passed by address to the sweep helpers.
// Actor fields: +0x4c x, +0x50 y, +0xcc state, +0x11c, +0x124 box rows.
uint32_t function_4cc2b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    uint32_t xSlot = run.automatic(0x8);
    uint32_t rowSlot = run.automatic(0x4);
    uint32_t resultSlot = run.automatic(-0x4);
    uint32_t extra = arguments[3];
    uint32_t y = arguments[2];
    run.put(resultSlot, 0);
    uint32_t row;
    if (s32(run.get(actor + 0x50)) < s32(y)) {
        row = run.call(0x4cc9a0, receiver, {actor, arguments[1], y, extra});
        if (run.get(actor + 0xcc) != 1) {
            uint32_t bottom = run.get(actor + 0x124);
            uint32_t top = run.get(actor + 0x11c);
            run.put(rowSlot, bottom + row + 1);
            uint32_t first = run.call(0x4207f0, receiver, {arguments[1], top + row - 1});
            if (first != 3) {
                uint32_t second = run.call(0x4207f0, receiver, {arguments[1], run.get(rowSlot)});
                if (second != 3)
                    run.put(actor + 0xcc, 4);
            }
        }
    } else {
        row = run.call(0x4ccc50, receiver, {actor, arguments[1], y, extra});
        uint32_t bottom = run.get(actor + 0x124);
        uint32_t top = run.get(actor + 0x11c);
        run.put(rowSlot, row + bottom + 1);
        uint32_t first = run.call(0x4207f0, receiver, {arguments[1], top + row - 1});
        if (first != 3) {
            uint32_t second = run.call(0x4207f0, receiver, {arguments[1], run.get(rowSlot)});
            if (second != 3) {
                uint32_t bottom2 = run.get(actor + 0x124);
                uint32_t current = run.get(actor + 0x50);
                uint32_t limit = row + bottom2 + 1;
                uint32_t scanArguments[4] = {arguments[1], limit - row + current, limit, rowSlot};
                uint32_t found = function_4ccdd0(run, receiver, scanArguments);
                if (found != 0) {
                    uint32_t newRow = run.get(rowSlot);
                    if (s32(newRow) > s32(row)) {
                        uint32_t bottom3 = run.get(actor + 0x124);
                        run.put(actor + 0xcc, 1);
                        row = newRow - bottom3 - 1;
                    }
                }
            }
        }
    }
    uint32_t x = run.get(xSlot);
    uint32_t oldX = run.get(actor + 0x4c);
    uint32_t value = x;
    if (s32(x) > s32(oldX)) {
        uint32_t returned = run.call(0x4cc420, receiver, {actor, x, row, xSlot, extra});
        run.put(resultSlot, returned);
        value = run.get(xSlot);
    } else if (s32(x) < s32(oldX)) {
        uint32_t returned = run.call(0x4cc570, receiver, {actor, x, row, xSlot, extra});
        run.put(resultSlot, returned);
        value = run.get(xSlot);
    }
    run.put(actor + 0x4c, value);
    uint32_t finalResult = run.get(resultSlot);
    run.put(actor + 0x50, row);
    return finalResult;
}

// 0x4ccf80. stdcall, 6 stack arguments, the sixth unused. Tests whether actor
// (a1) at offset (a3, a4) lands on top of object a2; stores a landing row in
// *a5 and returns 1 when it does.
uint32_t function_4ccf80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t a1 = arguments[0];
    uint32_t a2 = arguments[1];
    uint32_t a3 = arguments[2];
    uint32_t a4 = arguments[3];
    uint32_t out = arguments[4];
    uint32_t left2 = run.get(a2 + 0x128);
    if (left2 == 0xffffffff)
        return 0;
    uint32_t top1 = run.get(a1 + 0x118);
    if (top1 == 0xffffffff)
        return 0;
    uint32_t y1 = run.get(a1 + 0x50);
    if (s32(y1) > s32(a4))
        return 0;
    uint32_t x2 = run.get(a2 + 0x4c);
    uint32_t right2 = run.get(a2 + 0x130);
    left2 = left2 + x2;
    right2 = right2 + x2;
    uint32_t y2 = run.get(a2 + 0x50);
    uint32_t bottom2 = run.get(a2 + 0x12c);
    uint32_t extent2 = run.get(a2 + 0x15c);
    bottom2 = bottom2 + y2;
    uint32_t top = top1 + a3;
    uint32_t bottom1 = run.get(a1 + 0x124);
    uint32_t left1 = run.get(a1 + 0x120);
    uint32_t reach = bottom1 + a4;
    left1 = left1 + a3;
    uint32_t low = reach - a4 + y1;
    if (s32(extent2) > 0)
        extent2 = 0;
    uint32_t limit = bottom2 - extent2;
    if (s32(low) > s32(limit))
        return 0;
    if (s32(left1) < s32(left2))
        return 0;
    if (s32(top) > s32(right2))
        return 0;
    uint32_t landing = bottom2 - 1;
    if (low == reach) {
        if (reach != landing)
            return 0;
    } else if (s32(reach) < s32(landing)) {
        return 0;
    }
    run.put(out, bottom2 - bottom1 - 1);
    return 1;
}

// 0x4cd060. stdcall, 5 stack arguments (a1, object a2, a3, a4, flags).
// Returns 1 when a1 at (a3, a4) overlaps a2 horizontally and its bottom row
// sits on a2's top, for a2 of kind 0x80 and flag bit 8.
uint32_t function_4cd060(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t a1 = arguments[0];
    uint32_t a2 = arguments[1];
    uint32_t a3 = arguments[2];
    uint32_t a4 = arguments[3];
    uint32_t flags = arguments[4];
    if (a2 == 0)
        return 0;
    if ((flags & 8) == 0)
        return 0;
    if (run.get(a2 + 0xd0) != 0x80)
        return 0;
    uint32_t left2 = run.get(a2 + 0x128);
    if (left2 == 0xffffffff)
        return 0;
    uint32_t top1 = run.get(a1 + 0x118);
    if (top1 == 0xffffffff)
        return 0;
    uint32_t x2 = run.get(a2 + 0x4c);
    uint32_t y2 = run.get(a2 + 0x50);
    uint32_t leftEdge2 = x2 + left2;
    uint32_t rightEdge2 = run.get(a2 + 0x130) + x2;
    uint32_t bottom2 = run.get(a2 + 0x12c);
    uint32_t bottom1 = run.get(a1 + 0x124);
    uint32_t left1 = run.get(a1 + 0x120);
    bottom1 = bottom1 + a4;
    bottom2 = bottom2 + y2;
    left1 = left1 + a3;
    top1 = top1 + a3;
    if (s32(left1) < s32(leftEdge2))
        return 0;
    if (s32(top1) > s32(rightEdge2))
        return 0;
    bottom2 = bottom2 - 1;
    return bottom1 == bottom2 ? 1 : 0;
}

// 0x4cd120. thiscall, 4 stack arguments (x, y, outLeft, outRight). Finds the
// tile under (x, y) after clamping to the map; when it holds an object stores
// the tile's left edge and its right edge (object width +4) and returns 1.
uint32_t function_4cd120(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t x = arguments[0];
    uint32_t y = arguments[1];
    if (s32(x) < 0) {
        x = 0;
    } else {
        uint32_t limit = run.get(run.get(receiver + 0x5c) + 0x30);
        if (s32(x) >= s32(limit))
            x = limit - 1;
    }
    if (s32(y) < 0) {
        y = 0;
    } else {
        uint32_t limit = run.get(run.get(receiver + 0x5c) + 0x34);
        if (s32(y) >= s32(limit))
            y = limit - 1;
    }
    uint32_t map = run.get(receiver + 0x5c);
    uint32_t columnShift = run.get(map + 0x8c);
    uint32_t column = sarBy(x, columnShift);
    uint32_t left = shlBy(column, columnShift);
    uint32_t rowShift = run.get(map + 0x90);
    uint32_t tileRow = sarBy(y, rowShift);
    uint32_t rowOffset = run.get(map + 0x24);
    uint32_t table = run.get(map + 0x20);
    uint32_t rowBase = run.get(rowOffset + tileRow * 4);
    uint32_t cell = run.get(table + (rowBase + column) * 4);
    if (cell == 0xeeeeeeee || cell == 0xffffffff)
        return 0;
    uint32_t object = run.get(run.get(receiver + 0x4c) + (cell & 0xffff) * 4);
    run.put(arguments[2], left);
    uint32_t width = run.get(object + 0x4);
    run.put(arguments[3], width + left - 1);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4cc2b0:
        return function_4cc2b0(run, receiver, arguments);
    case 0x4ccdd0:
        return function_4ccdd0(run, receiver, arguments);
    case 0x4ccf80:
        return function_4ccf80(run, receiver, arguments);
    case 0x4cd060:
        return function_4cd060(run, receiver, arguments);
    case 0x4cd120:
        return function_4cd120(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_collision_dispatch_03_entry, owned, body)
