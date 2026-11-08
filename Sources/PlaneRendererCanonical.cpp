// Original v1.0 plane and actor drawing, translated over guest memory.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4c91d0: return 1;
    case 0x4c9e00: return 1;
    case 0x4cb9b0: return 2;
    case 0x4d0d50: return 1;
    default: return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

void invokeVirtual(Run &run, uint32_t object, uint32_t slot, uint32_t frameBytes,
                   std::initializer_list<uint32_t> arguments) {
    const uint32_t target = run.get(run.get(object) + slot);
    if (owned(target) >= 0) {
        if (uint32_t(owned(target)) != arguments.size()) {
            run.fail(CLAW_FAULT_ABI, target);
        }
        const uint32_t savedFrame = run.frame;
        run.frame -= frameBytes;
        body(run, target, object, arguments.begin());
        run.frame = savedFrame;
    } else {
        const uint32_t savedStack = run.stackPointer;
        run.stackPointer = run.frame - frameBytes;
        run.call(target, object, arguments);
        run.stackPointer = savedStack;
    }
}

// 0x4c91d0: node +0 next, +8 actor; list +0x14 head.
uint32_t function_4c91d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t node = run.get(receiver + 0x14);
    while (node) {
        const uint32_t next = run.get(node);
        invokeVirtual(run, run.get(node + 0x8), 0x2c, 0x10, {arguments[0]});
        node = next;
    }
    return 0;
}

// 0x4c9e00: actor +0x174 drawing service.
uint32_t function_4c9e00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t service = run.get(receiver + 0x174);
    if (service) {
        invokeVirtual(run, service, 0x38, 0x10, {receiver, arguments[0]});
    }
    return 0;
}

// Rectangles stay at their original frame offsets, including writes by callees.
void rectangle(Run &run, uint32_t address, uint32_t left, uint32_t top, uint32_t right, uint32_t bottom) {
    run.put(address, left);
    run.put(address + 0x4, top);
    run.put(address + 0x8, right);
    run.put(address + 0xc, bottom);
}

// Original draw branches in 0x4d0d50. +0xa0 tilesets; +0x64/+0x68 frame bounds.
void tile(Run &run, uint32_t plane, uint32_t destination, uint32_t word,
          uint32_t x, uint32_t y, uint32_t source) {
    if (word == 0xeeeeeeee) {
        const uint32_t right = x - run.get(source) + run.get(source + 0x8);
        const uint32_t bottom = y - run.get(source + 0x4) + run.get(source + 0xc);
        rectangle(run, run.automatic(-0x8c), x, y, right, bottom);
        run.call(0x4b9ce0, destination, {run.automatic(-0x8c), 0, 0, 0x1000400, plane + 0xf4});
    } else if (word != 0xffffffff) {
        const uint32_t set = run.get(run.get(plane + 0xa0) + (word >> 16) * 4);
        const uint32_t index = word & 0xffff;
        uint32_t frame = 0;
        if (s32(index) >= run.gets(set + 0x64) && s32(index) <= run.gets(set + 0x68)) {
            frame = run.get(run.get(set + 0x14) + index * 4);
        }
        // +0x28 frame flags, +0x2c surface wrapper.
        const uint32_t flags = run.get(frame + 0x28);
        const uint32_t surface = run.get(frame + 0x2c);
        run.call(0x4b9d80, destination, {x, y, surface, source, flags});
    }
}

uint32_t tileWord(Run &run, uint32_t plane, uint32_t row, uint32_t column) {
    return run.get(run.get(plane + 0x20) + (row + column) * 4);
}

// 0x4d0d50: byte +8 skip; +0x38/+0x3c tile size, +0x40..+0x4c viewport.
uint32_t function_4d0d50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (run.get8(receiver + 0x8) & 2) {
        return 0;
    }
    const uint32_t sx = run.get(receiver + 0x8c) & 31;
    const uint32_t sy = run.get(receiver + 0x90) & 31;
    const uint32_t left = uint32_t(run.gets(receiver + 0x40) >> sx);
    const uint32_t top = uint32_t(run.gets(receiver + 0x44) >> sy);
    const uint32_t right = uint32_t(run.gets(receiver + 0x48) >> sx);
    const uint32_t bottom = uint32_t(run.gets(receiver + 0x4c) >> sy);
    const uint32_t firstWidth = ((left + 1) << sx) - run.get(receiver + 0x40);
    const uint32_t firstHeight = ((top + 1) << sy) - run.get(receiver + 0x44);
    const uint32_t lastWidth = run.get(receiver + 0x48) - (right << sx) + 1;
    const uint32_t lastHeight = run.get(receiver + 0x4c) - (bottom << sy) + 1;
    const uint32_t columns = right - left - 1;
    const uint32_t rows = bottom - top - 1;
    const uint32_t width = run.get(receiver + 0x38);
    const uint32_t height = run.get(receiver + 0x3c);
    // Source edge rectangles: entry -0x74, -0x48, -0x38, -0x18, -0x28.
    rectangle(run, run.automatic(-0x74), width - firstWidth, height - firstHeight, width, height);
    rectangle(run, run.automatic(-0x48), 0, height - firstHeight, width, height);
    rectangle(run, run.automatic(-0x38), width - firstWidth, 0, width, height);
    rectangle(run, run.automatic(-0x18), 0, 0, lastWidth, height);
    const uint32_t destination = run.get(arguments[0] + 0x2c);
    uint32_t y = run.get(receiver + 0x54);
    uint32_t x = run.get(receiver + 0x50);
    uint32_t row = run.get(run.get(receiver + 0x24) + top * 4);
    const uint32_t savedStack = run.stackPointer;
    run.stackPointer = run.frame - 0xbc;
    tile(run, receiver, destination, tileWord(run, receiver, row, left), x, y, run.automatic(-0x74));
    x += firstWidth;
    uint32_t column = left + 1;
    if (s32(column) >= run.gets(receiver + 0x28)) {
        column = 0;
    }
    if (s32(columns) > 0) {
        uint32_t count = columns;
        do {
            tile(run, receiver, destination, tileWord(run, receiver, row, column), x, y, run.automatic(-0x48));
            x += run.get(receiver + 0x38);
            ++column;
            if (s32(column) >= run.gets(receiver + 0x28)) {
                column = 0;
            }
            --count;
        } while (count);
    }
    const uint32_t topRightHeight = run.get(receiver + 0x3c);
    rectangle(run, run.automatic(-0x74), 0, topRightHeight - firstHeight, lastWidth, topRightHeight);
    tile(run, receiver, destination, tileWord(run, receiver, row, column), x, y, run.automatic(-0x74));
    y += firstHeight;
    uint32_t rowIndex = top + 1;
    if (s32(rowIndex) >= run.gets(receiver + 0x2c)) {
        rowIndex = 0;
    }
    if (s32(rows) > 0) {
        uint32_t rowCount = rows;
        do {
            x = run.get(receiver + 0x50);
            row = run.get(run.get(receiver + 0x24) + rowIndex * 4);
            tile(run, receiver, destination, tileWord(run, receiver, row, left), x, y, run.automatic(-0x38));
            x += firstWidth;
            column = left + 1;
            if (s32(column) >= run.gets(receiver + 0x28)) {
                column = 0;
            }
            if (s32(columns) > 0) {
                uint32_t count = columns;
                do {
                    tile(run, receiver, destination, tileWord(run, receiver, row, column), x, y, receiver + 0x60);
                    x += run.get(receiver + 0x38);
                    ++column;
                    if (s32(column) >= run.gets(receiver + 0x28)) {
                        column = 0;
                    }
                    --count;
                } while (count);
            }
            tile(run, receiver, destination, tileWord(run, receiver, row, column), x, y, run.automatic(-0x18));
            y += run.get(receiver + 0x3c);
            ++rowIndex;
            if (s32(rowIndex) >= run.gets(receiver + 0x2c)) {
                rowIndex = 0;
            }
            --rowCount;
        } while (rowCount);
    }
    const uint32_t bottomWidth = run.get(receiver + 0x38);
    rectangle(run, run.automatic(-0x28), 0, 0, bottomWidth, lastHeight);
    x = run.get(receiver + 0x50);
    row = run.get(run.get(receiver + 0x24) + rowIndex * 4);
    rectangle(run, run.automatic(-0x74), bottomWidth - firstWidth, 0, bottomWidth, lastHeight);
    tile(run, receiver, destination, tileWord(run, receiver, row, left), x, y, run.automatic(-0x74));
    x += firstWidth;
    column = left + 1;
    if (s32(column) >= run.gets(receiver + 0x28)) {
        column = 0;
    }
    if (s32(columns) > 0) {
        uint32_t count = columns;
        do {
            tile(run, receiver, destination, tileWord(run, receiver, row, column), x, y, run.automatic(-0x28));
            x += run.get(receiver + 0x38);
            ++column;
            if (s32(column) >= run.gets(receiver + 0x28)) {
                column = 0;
            }
            --count;
        } while (count);
    }
    rectangle(run, run.automatic(-0x74), 0, 0, lastWidth, lastHeight);
    tile(run, receiver, destination, tileWord(run, receiver, row, column), x, y, run.automatic(-0x74));
    run.stackPointer = savedStack;
    return 0;
}

// World calls Plane::drawTiles with 16 saved bytes and one pushed argument.
void drawPlane(Run &run, uint32_t plane, uint32_t context) {
    const uint32_t savedFrame = run.frame;
    run.frame -= 0x18;
    const uint32_t args[] = {context};
    function_4d0d50(run, plane, args);
    run.frame = savedFrame;
}

// 0x4cb9b0: +8 flags; +0x38 planes; +0x3c count; +0x60 insertion index.
uint32_t function_4cb9b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t context = arguments[0];
    const uint32_t list = arguments[1];
    if ((run.get8(receiver + 0x8) & 1) && list + 0x10 != 0) {
        uint32_t plane = 0;
        if (run.gets(receiver + 0x3c) > 0) {
            plane = run.get(run.get(receiver + 0x38));
        }
        if (plane) {
            drawPlane(run, plane, context);
            uint32_t node = run.get(list + 0x14);
            uint32_t index = 1;
            while (s32(index) < run.gets(receiver + 0x3c)) {
                plane = 0;
                if (s32(index) >= 0 && s32(index) < run.gets(receiver + 0x3c)) {
                    plane = run.get(run.get(receiver + 0x38) + index * 4);
                }
                const int32_t depth = run.gets(plane + 0x80);
                while (node) {
                    const uint32_t next = run.get(node);
                    const uint32_t actor = run.get(node + 0x8);
                    if (run.gets(actor + 0x64) >= depth) {
                        break;
                    }
                    invokeVirtual(run, actor, 0x2c, 0x18, {context});
                    node = next;
                }
                plane = 0;
                if (s32(index) >= 0 && s32(index) < run.gets(receiver + 0x3c)) {
                    plane = run.get(run.get(receiver + 0x38) + index * 4);
                }
                drawPlane(run, plane, context);
                ++index;
            }
            while (node) {
                const uint32_t next = run.get(node);
                invokeVirtual(run, run.get(node + 0x8), 0x2c, 0x18, {context});
                node = next;
            }
            return 0;
        }
    }
    uint32_t index = 0;
    while (s32(index) <= run.gets(receiver + 0x60)) {
        drawPlane(run, run.get(run.get(receiver + 0x38) + index * 4), context);
        ++index;
    }
    invokeVirtual(run, list, 0x28, 0x18, {context});
    index = run.get(receiver + 0x60) + 1;
    while (s32(index) < run.gets(receiver + 0x3c)) {
        drawPlane(run, run.get(run.get(receiver + 0x38) + index * 4), context);
        ++index;
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4c91d0: return function_4c91d0(run, receiver, arguments);
    case 0x4c9e00: return function_4c9e00(run, receiver, arguments);
    case 0x4cb9b0: return function_4cb9b0(run, receiver, arguments);
    case 0x4d0d50: return function_4d0d50(run, receiver, arguments);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace
CLAW_MODULE_ENTRY(claw_plane_renderer_entry, owned, body)
