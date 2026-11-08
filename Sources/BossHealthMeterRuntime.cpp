#include "ClawRuntime.hpp"
#include <cmath>

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x491fa0:
        return 1;
    case 0x4b9830:
        return 2;
    default:
        return -1;
    }
}

// 0x4b9830. Surface rectangle fill with a stack-local effects record.
uint32_t fillRectangle(Run &run, uint32_t receiver, uint32_t rectangle, uint32_t color) {
    if (!rectangle)
        return 0;
    uint32_t effects = run.automatic(-100);
    for (uint32_t offset = 0; offset < 100; offset += 4) {
        run.put(effects + offset, 0);
    }
    run.put(effects + 0x00, 100);
    run.put(effects + 0x50, color);
    run.stackPointer = run.automatic(-132);
    uint32_t error = run.call(0x4b9ce0, receiver, {rectangle, 0, 0, 0x1000400, effects});
    if (error) {
        run.stackPointer = run.automatic(-124);
        run.call(0x4bd260, 0, {0x5324dc, 0x253, error});
    }
    return error == 0;
}

void draw(Run &run, uint32_t surface, uint32_t rectangle, uint32_t color) {
    uint32_t parentFrame = run.frame;
    uint32_t parentStack = run.stackPointer;
    run.frame = run.automatic(-64);
    try {
        fillRectangle(run, surface, rectangle, color);
    } catch (...) {
        run.frame = parentFrame;
        run.stackPointer = parentStack;
        throw;
    }
    run.frame = parentFrame;
    run.stackPointer = parentStack;
}

// 0x491fa0. Actor +0x6c record, +0x10c initial health, +0x174 image.
uint32_t meter(Run &run, uint32_t actor) {
    uint32_t record = run.get(actor + 0x6c);
    uint32_t state = run.get(record + 0x1c);
    uint32_t camera = run.automatic(-16);
    uint32_t rectangle = run.automatic(-32);
    run.put(run.automatic(4), record);
    if (state == 0) {
        run.stackPointer = run.automatic(-60);
        run.call(0x4c7970, actor, {0x52c8c8});
        // +0x64 image ID and +0x08 flags.
        if (run.get(actor + 0x64) != 0x2704) {
            run.put(actor + 0x64, 0x2704);
            run.put(actor + 0x08, run.get(actor + 0x08) | 0x20000);
        }
    } else if (state != 5) {
        return 1;
    }
    run.stackPointer = run.automatic(-60);
    run.call(0x42a450, run.get(0x5371fc), {camera});
    uint32_t center = uint32_t(s32(run.get(camera + 0x08) - run.get(camera + 0x00)) / 2) + 1;
    uint32_t bottom = run.get(camera + 0x0c) - 0x20;
    if (state == 0) {
        run.put(actor + 0x4c, center);
        run.put(actor + 0x50, bottom);
        uint32_t boss = run.get(0x5349dc);
        if (boss) {
            run.put(actor + 0x10c, run.get(boss + 0x10c));
        }
        uint32_t app = run.get(0x5371fc);
        uint32_t depth = run.get(app + 0x78);
        if (depth == 8) {
            run.put(0x52c6f0, 0x34);
        } else if (depth == 16) {
            uint32_t red = (0xffu >> (run.get(0x541368) & 31)) << (run.get(0x54135c) & 31);
            run.put(0x52c6f0, red & 0xffff);
        } else if (depth == 24) {
            run.put(0x52c6f0, 0xff);
        }
        depth = run.get(app + 0x78);
        if (depth == 8) {
            run.put(0x52c6f4, 0x7e);
        } else if (depth == 16 || depth == 24) {
            run.put(0x52c6f4, 0);
        }
        run.put(record + 0x1c, 5);
        return 1;
    }
    run.put(actor + 0x50, bottom);
    run.put(actor + 0x4c, center);
    uint32_t boss = run.get(0x5349dc);
    if (!boss) {
        run.put(actor + 0x08, run.get(actor + 0x08) | 0x10000);
        return 1;
    }
    uint32_t image = run.get(actor + 0x174);
    if (!image)
        return 1;
    uint32_t surface = run.get(image + 0x2c);
    if (!surface)
        return 1;
    uint32_t left = run.get(image + 0x20);
    uint32_t top = run.get(image + 0x24);
    double scaled = double(run.gets(boss + 0x10c)) * double(run.getf(0x50f8d8));
    double ratio = scaled / double(run.gets(actor + 0x10c));
    if (std::isnan(ratio))
        ratio = std::copysign(ratio, -1.0);
    run.stackPointer = run.automatic(-56);
    uint32_t percent = run.call_x87(0x4a30e0, 0, ratio);
    if (s32(percent) > 100)
        percent = 100;
    if (s32(percent) < 0)
        percent = 0;
    run.put(run.automatic(4), percent);
    run.put(rectangle + 0x00, left + 0x12);
    run.put(rectangle + 0x04, top + 0x0b);
    run.put(rectangle + 0x08, left + 0xf4);
    run.put(rectangle + 0x0c, top + 0x12);
    if (percent >= 100) {
        draw(run, surface, rectangle, run.get(0x52c6f0));
    } else if (percent > 0) {
        draw(run, surface, rectangle, run.get(0x52c6f4));
        uint32_t currentLeft = run.get(rectangle + 0x00);
        uint32_t width = run.get(rectangle + 0x08) - currentLeft;
        run.put(run.automatic(-36), width);
        double fraction = double(s32(run.get(run.automatic(4)))) * double(run.getf(0x50f8dc));
        double fill = double(s32(width)) * fraction;
        run.stackPointer = run.automatic(-56);
        uint32_t extent = run.call_x87(0x4a30e0, 0, fill);
        run.put(rectangle + 0x08, extent + currentLeft);
        draw(run, surface, rectangle, run.get(0x52c6f0));
    } else {
        draw(run, surface, rectangle, run.get(0x52c6f4));
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x491fa0:
        return meter(run, arguments[0]);
    case 0x4b9830:
        return fillRectangle(run, receiver, arguments[0], arguments[1]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_boss_health_meter_entry, owned, body)
