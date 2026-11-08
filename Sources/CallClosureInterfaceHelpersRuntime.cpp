// Original interface image-array and dialog preparation helpers.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t f) {
    switch (f) {
    case 0x4de560: return 1;
    case 0x4de830: return 3;
    case 0x4df250: case 0x4e29a0: case 0x4e2f70: case 0x4e3090: case 0x4e31f0: return 0;
    default: return -1;
    }
}

uint32_t callAt(Run &run, int32_t offset, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {}) {
    run.stackPointer = run.automatic(offset);
    return run.call(f, receiver, args);
}

uint32_t virtualAt(Run &run, int32_t offset, uint32_t receiver, uint32_t slot, std::initializer_list<uint32_t> args = {}) {
    return callAt(run, offset, run.get(run.get(receiver) + slot), receiver, args);
}

uint32_t importAt(Run &run, int32_t offset, uint32_t slot, std::initializer_list<uint32_t> args = {}) {
    return callAt(run, offset, slot, 0, args);
}

// 0x4de560. Receiver +4/+8/+c/+10 are array, count, capacity and growth;
// +0x48 is the image manager. The CString argument is destroyed by value.
uint32_t appendImage(Run &run, uint32_t self, const uint32_t *a) {
    const uint32_t argument = run.automatic(4);
    run.put(argument, a[0]);
    if (run.get(a[0] - 8) && !callAt(run, -56, 0x4f2190, 0, {a[0], 0})) {
        uint32_t text = callAt(run, -60, 0x4f6974, argument, {0});
        uint32_t image = callAt(run, -60, 0x4bc990, run.get(self + 0x48), {text, 0, 0xffffffff});
        uint32_t index = run.get(self + 0x08);
        callAt(run, -56, 0x4dee30, self, {index + 1, 0xffffffff});
        run.put(run.get(self + 0x04) + index * 4, image);
        uint32_t red = (0xffu >> (run.get(0x541368) & 31)) << (run.get(0x54135c) & 31);
        uint32_t key = (red & 0xffff) | ((0xffu >> (run.get(0x541370) & 31)) & 0xffff);
        uint32_t pair = run.automatic(-20);
        run.put(pair, key);
        run.put(pair + 4, key);
        callAt(run, -56, 0x4b9950, run.get(run.get(self + 0x04) + index * 4), {8, pair});
    } else {
        uint32_t oldCount = run.get(self + 0x08);
        uint32_t index = oldCount;
        uint32_t next = oldCount + 1;
        uint32_t array = run.get(self + 0x04);
        if (!next) {
            if (array) {
                callAt(run, -52, 0x4f6428, 0, {array});
                run.put(self + 0x04, 0);
            }
            run.put(self + 0x0c, 0);
            run.put(self + 0x08, 0);
        } else if (!array) {
            uint32_t bytes = next * 4;
            uint32_t block = callAt(run, -52, 0x4f63ec, 0, {bytes});
            run.put(self + 0x04, block);
            for (uint32_t i = 0; i < bytes / 4; ++i) {
                run.put(block + i * 4, 0);
            }
            run.put(self + 0x0c, next);
            run.put(self + 0x08, next);
        } else if (s32(next) <= s32(run.get(self + 0x0c))) {
            if (s32(next) > s32(oldCount)) {
                for (uint32_t i = 0; i != next - oldCount; ++i) {
                    run.put(array + (oldCount + i) * 4, 0);
                }
            }
            run.put(self + 0x08, next);
        } else {
            uint32_t growth = run.get(self + 0x10);
            if (!growth) {
                growth = uint32_t(s32(oldCount) / 8);
                if (s32(growth) < 4) growth = 4;
                else if (s32(growth) > 0x400) growth = 0x400;
            }
            uint32_t capacity = run.get(self + 0x0c) + growth;
            if (s32(next) >= s32(capacity)) capacity = next;
            uint32_t block = callAt(run, -52, 0x4f63ec, 0, {capacity * 4});
            uint32_t count = run.get(self + 0x08);
            uint32_t source = run.get(self + 0x04);
            for (uint32_t i = 0; i < (count * 4) / 4; ++i) {
                run.put(block + i * 4, run.get(source + i * 4));
            }
            uint32_t start = run.get(self + 0x08);
            for (uint32_t i = 0; i != next - start; ++i) {
                run.put(block + (start + i) * 4, 0);
            }
            callAt(run, -52, 0x4f6428, 0, {run.get(self + 0x04)});
            run.put(self + 0x04, block);
            run.put(self + 0x08, next);
            run.put(self + 0x0c, capacity);
            index = oldCount;
        }
        run.put(run.get(self + 0x04) + index * 4, 0);
    }
    callAt(run, -48, 0x4f6584, argument);
    return 0;
}

// 0x4de830. Receiver +0x38 is the eight-item enabled mask, +0x4c/+0x50
// supply fallback drawing resources, and +4 holds the image pointer array.
uint32_t labelImages(Run &run, uint32_t self, const uint32_t *a) {
    uint32_t first = a[1] ? a[1] : run.get(self + 0x4c);
    uint32_t second = a[2] ? a[2] : run.get(self + 0x50);
    uint32_t argument = run.automatic(4);
    run.put(argument, a[0]);
    for (uint32_t i = 0; i < 8; ++i) {
        if (run.get(run.get(self + 0x38) + i * 4)) {
            uint32_t resource = (i == 1 || i == 2) ? second : first;
            uint32_t color = i < 5 ? 0xffffff : 0x808080;
            uint32_t slot = callAt(run, -40, 0x4deda0, self, {i});
            uint32_t image = run.get(slot);
            uint32_t copy = run.automatic(-40);
            run.put(copy, image);
            callAt(run, -48, 0x4f6449, copy, {argument});
            callAt(run, -44, 0x4dea30, 0, {run.get(copy), image, resource, color});
        }
    }
    callAt(run, -28, 0x4f6584, argument);
    return 0;
}

void initializeControl(Run &run, uint32_t p) {
    run.put(p, 0);
    run.put(p + 0x04, 0);
    run.put(p + 0x08, 0);
    run.put(p + 0x0c, 0);
    run.put16(p + 0x10, 0);
    run.put16(p + 0x12, 0);
    run.put(p + 0x14, 0);
    run.put16(p + 0x18, 0);
    run.put(p + 0x1c, 0);
    run.put(p + 0x20, 0);
    run.put(p + 0x24, 0);
    importAt(run, -108, 0x546cdc, {p + 0x28});
    run.put(p + 0x38, 0);
    run.put(p + 0x3c, 0);
    for (uint32_t i = 0; i < 7; ++i) {
        run.put(p + 0x40 + i * 4, 0);
    }
}

void copyRect(Run &run, uint32_t dest, uint32_t source) {
    run.put(dest, run.get(source));
    run.put(dest + 0x04, run.get(source + 0x04));
    run.put(dest + 0x08, run.get(source + 0x08));
    run.put(dest + 0x0c, run.get(source + 0x0c));
}

uint32_t newControl(Run &run) {
    uint32_t p = callAt(run, -108, 0x4f63ec, 0, {0x5c});
    if (p) initializeControl(run, p);
    return p;
}

uint32_t newString(Run &run, uint32_t text) {
    uint32_t p = callAt(run, -108, 0x4f63ec, 0, {4});
    return p ? callAt(run, -108, 0x4f65f2, p, {text}) : 0;
}

// 0x4e29a0. Controls are 0x5c-byte records; receiver +0x14 is the count,
// +0x3c the control array, +0x64 selected control and +0x128 scrollbar width.
uint32_t prepareControls(Run &run, uint32_t self) {
    uint32_t index = 0;
    uint32_t displacement = 0;
    if (!run.get16(self + 0x14)) return 1;
    do {
        uint32_t p = run.get(self + 0x3c) + displacement;
        uint32_t kind = run.get16(p + 0x12);
        if (kind == 0x80) {
            if (run.get8(p) == 1) {
                run.put(self + 0x64, p);
            }
        } else if (kind == 0x81) {
            uint32_t text = newString(run, 0x510d30);
            run.put(run.get(self + 0x3c) + displacement + 0x40, text);
            run.put(run.get(self + 0x3c) + displacement + 0x44, 0);
            run.put(run.get(self + 0x3c) + displacement + 0x48, 0);
            run.put(run.get(self + 0x3c) + displacement + 0x4c, 0xffffffff);
            run.put(run.get(self + 0x3c) + displacement + 0x50, 0);
        } else if (kind == 0x83) {
            run.put(p + 0x40, 0);
            run.put(run.get(self + 0x3c) + displacement + 0x44, 0);
            run.put(run.get(self + 0x3c) + displacement + 0x48, 0);
            run.put(run.get(self + 0x3c) + displacement + 0x4c, 0);
            run.put(run.get(self + 0x3c) + displacement + 0x50, 0);
            uint32_t scrollbar = newControl(run);
            uint32_t flags = run.get(run.get(self + 0x3c) + displacement);
            run.put16(scrollbar + 0x12, 0x84);
            run.put(scrollbar, (flags & 0x1000 ? 0x18000000 : 0) | 1);
            copyRect(run, scrollbar + 0x28, run.get(self + 0x3c) + displacement + 0x28);
            if (run.get(scrollbar) & 0x800000) importAt(run, -116, 0x546d24, {scrollbar + 0x28, 0xfffffffe, 0xfffffffe});
            run.put(scrollbar + 0x34, run.get(scrollbar + 0x34) + 1);
            run.put(scrollbar + 0x28, run.get(scrollbar + 0x30) - run.get(self + 0x128));
            run.put(scrollbar + 0x58, run.get(self + 0x3c) + displacement);
            run.put(run.get(self + 0x3c) + displacement + 0x54, scrollbar);
        } else if (kind == 0x84) {
            run.put(p + 0x40, 0);
            run.put(run.get(self + 0x3c) + displacement + 0x44, 0);
            run.put(run.get(self + 0x3c) + displacement + 0x48, 0);
            run.put(run.get(self + 0x3c) + displacement + 0x4c, 0);
            run.put(run.get(self + 0x3c) + displacement + 0x50, 0);
            run.put(run.get(self + 0x3c) + displacement + 0x54, 0);
        } else if (kind == 0x85) {
            uint32_t text = newString(run, 0x534010);
            run.put(run.get(self + 0x3c) + displacement + 0x40, text);
            run.put(run.get(self + 0x3c) + displacement + 0x44, 0);
            run.put(run.get(self + 0x3c) + displacement + 0x48, 0);
            run.put(run.get(self + 0x3c) + displacement + 0x4c, 0);
            uint32_t flags = run.get(run.get(self + 0x3c) + displacement);
            uint32_t listFlags = (((flags >> 5) & 8) | (flags & 0x400)) >> 2;
            listFlags |= (flags & 0xf) == 1 ? 0x10800000 : 0;
            listFlags |= (flags & 0x800) << 1;
            uint32_t dc = virtualAt(run, -104, self, 0x04);
            uint32_t font = virtualAt(run, -108, dc, 0x30, {self + 0x114});
            uint32_t metrics = run.automatic(-68);
            importAt(run, -112, 0x546900, {run.get(dc + 0x08), metrics});
            virtualAt(run, -108, dc, 0x30, {font});
            virtualAt(run, -108, self, 0x08, {dc});
            uint32_t list = newControl(run);
            run.put(list, listFlags);
            run.put16(list + 0x12, 0x83);
            uint32_t ascent = run.get(run.automatic(-68));
            p = run.get(self + 0x3c) + displacement;
            importAt(run, -124, 0x546d5c, {list + 0x28, run.get(p + 0x28), run.get(p + 0x2c) + ascent + 9, run.get(p + 0x30), run.get(p + 0x34) - 3});
            run.put(list + 0x58, run.get(self + 0x3c) + displacement);
            run.put(run.get(self + 0x3c) + displacement + 0x50, list);
            uint32_t scrollbar = newControl(run);
            uint32_t scrollbarFlags = run.get(list);
            run.put16(scrollbar + 0x12, 0x84);
            run.put(scrollbar, (scrollbarFlags & 0x1000 ? 0x18000000 : 0) | 1);
            copyRect(run, scrollbar + 0x28, list + 0x28);
            if (run.get(scrollbar) & 0x800000) importAt(run, -116, 0x546d24, {scrollbar + 0x28, 0xfffffffe, 0xfffffffe});
            run.put(scrollbar + 0x34, run.get(scrollbar + 0x34) + 1);
            run.put(scrollbar + 0x58, list);
            run.put(scrollbar + 0x28, run.get(scrollbar + 0x30) - run.get(self + 0x128));
            run.put(list + 0x54, scrollbar);
            uint32_t edit = newControl(run);
            uint32_t mode = run.get(run.get(self + 0x3c) + displacement) & 0xf;
            run.put16(edit + 0x12, 0x81);
            run.put(edit, 0x10000000 | (mode == 3 ? 0x800 : 0));
            p = run.get(self + 0x3c) + displacement;
            uint32_t top = run.get(p + 0x2c);
            importAt(run, -124, 0x546d5c, {edit + 0x28, run.get(p + 0x28), top + 1, run.get(p + 0x30), run.get(run.automatic(-68)) + top + 9});
            text = callAt(run, -108, 0x4f63ec, 0, {4});
            if (text) text = callAt(run, -108, 0x4f65f2, text, {run.get(run.get(self + 0x3c) + displacement + 0x1c)});
            run.put(edit + 0x40, text);
            run.put(edit + 0x44, 0);
            run.put(edit + 0x48, 0);
            run.put(edit + 0x4c, 0xffffffff);
            run.put(edit + 0x50, run.get(self + 0x3c) + displacement);
            run.put(run.get(self + 0x3c) + displacement + 0x54, edit);
        }
        ++index;
        displacement += 0x5c;
    } while (s32(index) < s32(run.get16(self + 0x14)));
    return 1;
}

// 0x4e2f70. Recreate the background bitmap and DC, then draw into them.
uint32_t background(Run &run, uint32_t self) {
    uint32_t dc = self + 0xd4;
    uint32_t bitmap = self + 0xcc;
    if (dc && run.get(dc + 0x04)) {
        uint32_t old = run.get(self + 0x100);
        if (old) callAt(run, -28, 0x4fd150, 0, {run.get(self + 0xd8), run.get(old + 0x04)});
    }
    callAt(run, -20, 0x4fd067, dc);
    callAt(run, -20, 0x4fd732, bitmap);
    uint32_t acquired = virtualAt(run, -20, self, 0x04);
    uint32_t compatible = importAt(run, -24, 0x54687c, {acquired ? run.get(acquired + 0x04) : acquired});
    if (!callAt(run, -24, 0x4fcfff, dc, {compatible})) return 0;
    uint32_t height = run.get(self + 0x78) - run.get(self + 0x70);
    uint32_t width = run.get(self + 0x74) - run.get(self + 0x6c);
    uint32_t handle = importAt(run, -32, 0x54690c, {run.get(acquired + 0x04), width, height});
    if (!callAt(run, -24, 0x4fd6db, bitmap, {handle})) return 0;
    copyRect(run, self + 0xbc, self + 0x6c);
    importAt(run, -32, 0x546b7c, {self + 0xbc, 0 - run.get(self + 0x6c), 0 - run.get(self + 0x70)});
    uint32_t old = callAt(run, -28, 0x4fd150, 0, {run.get(self + 0xd8), bitmap ? run.get(bitmap + 0x04) : bitmap});
    run.put(self + 0x100, old);
    virtualAt(run, -24, self, 0x08, {acquired});
    virtualAt(run, -28, self, 0x0c, {self + 0xd4, self + 0x6c});
    return 0;
}

// 0x4e3090. Recreate the foreground bitmap, select its font and copy the
// background before the final virtual paint callback.
uint32_t foreground(Run &run, uint32_t self) {
    uint32_t dc = self + 0xec;
    if (dc && run.get(dc + 0x04)) {
        uint32_t old = run.get(self + 0xfc);
        if (old) callAt(run, -28, 0x4fd150, 0, {run.get(self + 0xf0), run.get(old + 0x04)});
    }
    callAt(run, -20, 0x4fd067, dc);
    callAt(run, -20, 0x4fd732, self + 0xcc);
    uint32_t acquired = virtualAt(run, -20, self, 0x04);
    uint32_t compatible = importAt(run, -24, 0x54687c, {acquired ? run.get(acquired + 0x04) : acquired});
    if (!callAt(run, -24, 0x4fcfff, dc, {compatible})) return 0;
    uint32_t height = run.get(self + 0x78) - run.get(self + 0x70);
    uint32_t width = run.get(self + 0x74) - run.get(self + 0x6c);
    uint32_t handle = importAt(run, -32, 0x54690c, {run.get(acquired + 0x04), width, height});
    if (!callAt(run, -24, 0x4fd6db, self + 0xcc, {handle})) return 0;
    copyRect(run, self + 0xbc, self + 0x6c);
    importAt(run, -32, 0x546b7c, {self + 0xbc, 0 - run.get(self + 0x6c), 0 - run.get(self + 0x70)});
    uint32_t bitmap = self + 0xcc;
    uint32_t old = callAt(run, -28, 0x4fd150, 0, {run.get(self + 0xf0), bitmap ? run.get(bitmap + 0x04) : bitmap});
    run.put(self + 0xfc, old);
    uint32_t font = virtualAt(run, -24, dc, 0x30, {self + 0x114});
    run.put(self + 0x11c, font);
    virtualAt(run, -24, self, 0x08, {acquired});
    height = run.get(self + 0x78) - run.get(self + 0x70);
    width = run.get(self + 0x74) - run.get(self + 0x6c);
    uint32_t source = self + 0xd4;
    importAt(run, -56, 0x546870, {run.get(self + 0xf0), 0, 0, width, height, source ? run.get(source + 0x04) : source, 0, 0, 0xcc0020});
    virtualAt(run, -20, self, 0x10);
    return 0;
}

// 0x4e31f0. Allocate the fixed-size cursor bitmap and install the cursor.
uint32_t cursorBitmap(Run &run, uint32_t self) {
    uint32_t bitmap = self + 0x104;
    if (bitmap && run.get(bitmap + 0x04)) callAt(run, -16, 0x4fd732, bitmap);
    uint32_t dc = virtualAt(run, -16, self, 0x04);
    uint32_t image = importAt(run, -28, 0x54690c, {run.get(dc + 0x04), 32, 32});
    callAt(run, -20, 0x4fd6db, bitmap, {image});
    virtualAt(run, -20, self, 0x08, {dc});
    uint32_t cursor = importAt(run, -24, 0x546b60, {0, 0x7f00});
    run.put(self + 0x58, cursor);
    virtualAt(run, -20, self, 0xd4, {1});
    return 0;
}

uint32_t body(Run &run, uint32_t f, uint32_t self, const uint32_t *a) {
    switch (f) {
    case 0x4de560: return appendImage(run, self, a);
    case 0x4de830: return labelImages(run, self, a);
    case 0x4df250: return run.get(self + 0x2c);
    case 0x4e29a0: return prepareControls(run, self);
    case 0x4e2f70: return background(run, self);
    case 0x4e3090: return foreground(run, self);
    case 0x4e31f0: return cursorBitmap(run, self);
    default: run.fail(CLAW_FAULT_ABI, f);
    }
}
}
CLAW_MODULE_ENTRY(claw_call_closure_interface_helpers_entry, owned, body)
