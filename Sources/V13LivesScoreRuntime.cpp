#include "ClawRuntime.hpp"

extern "C" uint32_t claw_v13_next_life_threshold(uint32_t score) {
    return (uint32_t(claw::s32(score) / 500000) + 1u) * 500000u;
}

extern "C" uint32_t claw_v13_starting_lives(uint32_t easy) {
    return easy ? 9u : 7u;
}

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x416dd0:
    case 0x46f840:
        return 0;
    case 0x493e90:
        return 1;
    default:
        return -1;
    }
}

// 0x416dd0. Reset the inventory, then apply the Easy inventory values.
uint32_t function_00416dd0(Run &run) {
    for (uint32_t i = 0; i < 0x4e; ++i)
        run.put(0x532bf8 + i * 4, 0);
    run.put(0x532c28, 1);
    run.put(0x53b130, run.get(0x52abe4));
    const uint32_t easy = run.get(0x535990);
    run.put(0x532c68, 10);
    run.put(0x532c6c, 5);
    run.put(0x532c70, 3);
    run.put(0x532c74, claw_v13_starting_lives(0));
    run.put(0x532c40, 100);
    run.put(0x532ce4, 500000);
    run.put(0x532d30, 0);
    run.put(0x532d34, 0);
    run.put(0x532d38, 0);
    if (easy) {
        run.put(0x532c68, 50);
        run.put(0x532c6c, 40);
        run.put(0x532c70, 20);
        run.put(0x532c74, claw_v13_starting_lives(easy));
    }
    return 0;
}

// Position fields: +0x08 flags, +0x10/+0x14 position, +0x18/+0x1c scale.
void position(Run &run, uint32_t object, uint32_t x, uint32_t y) {
    const bool direct = (run.get8(object + 0x08) & 1) != 0;
    const double xf = double(s32(x));
    const double yf = double(s32(y));
    run.putf(object + 0x10, float(direct ? xf : xf * double(run.getf(object + 0x18))));
    run.putf(object + 0x14, float(direct ? yf : yf * double(run.getf(object + 0x1c))));
    run.stackPointer = run.automatic(-0x20);
    run.call(0x4d1870, object);
}

// 0x46f840. Restore the saved inventory and optional saved world position.
uint32_t function_0046f840(Run &run, uint32_t receiver) {
    const uint32_t state = run.get(receiver + 0x04);
    if (!run.get(state + 0xac))
        return 0;
    const uint32_t saves = run.get(state + 0x64);
    if (!saves)
        return 0;
    if (run.gets(receiver + 0x14) < 1)
        return 0;
    const uint32_t kind = run.get(state + 0x158);
    run.put(state + 0xac, 0);
    run.stackPointer = run.automatic(-0x28);
    if (!run.call(0x49e960, saves, {run.get(receiver + 0x14), kind}))
        return 0;
    run.stackPointer = run.automatic(-0x28);
    const uint32_t record = run.call(0x49e9b0, saves, {run.get(receiver + 0x14), kind});
    if (!record)
        return 0;
    run.put(0x532c3c, run.get(record + 0x10));
    run.put(0x532c40, run.get(record + 0x94));
    run.put(0x532c68, run.get(record + 0x98));
    run.put(0x532c6c, run.get(record + 0x9c));
    run.put(0x532c70, run.get(record + 0xa0));
    run.put(0x532c74, run.get(record + 0xa4));
    const uint32_t x = run.get(record + 0x04);
    run.put(0x532c44, x);
    const uint32_t y = run.get(record + 0x08);
    run.put(0x532c48, y);
    const bool hasPosition = run.get(record + 0x04) > 0 && run.get(record + 0x08) > 0;
    if (s32(x) > 0 && s32(y) > 0) {
        run.put(receiver + 0x44, x);
        run.put(receiver + 0x48, run.get(0x532c48));
        const uint32_t world = run.get(run.get(receiver + 0x0c) + 0x24);
        position(run, run.get(world + 0x5c), run.get(0x532c44), run.get(0x532c48));
        const uint32_t primary = run.get(world + 0x5c);
        const uint32_t px = run.get(primary + 0x84);
        const uint32_t py = run.get(primary + 0x88);
        for (uint32_t i = 0; s32(i) < run.gets(world + 0x3c); ++i) {
            if (i != run.get(world + 0x60))
                position(run, run.get(run.get(world + 0x38) + i * 4), px, py);
        }
        run.put(0x534d94, 1);
        run.put(0x535928, run.get(record + 0x58));
    }
    run.put(0x532ce4, claw_v13_next_life_threshold(run.get(0x532c3c)));
    for (uint32_t i = 0; i < 9; ++i) {
        run.put(0x532ca8 + i * 4, run.get(record + 0x28 + i * 4));
        if (hasPosition)
            run.put(0x532c80 + i * 4, run.get(record + 0x6c + i * 4));
    }
    run.put(receiver + 0x160, run.get(record + 0x10));
    run.put(receiver + 0x164, run.get(record + 0x14));
    run.put(0x532c1c, hasPosition ? 1 : 0);
    return 1;
}

uint32_t midpoint(uint32_t low, uint32_t high, uint32_t offset) {
    return uint32_t(s32(high - low) / 2) + offset + low;
}

// 0x493e90. Score actor initialization, display refresh and one extra-life award.
uint32_t function_00493e90(Run &run, uint32_t actor) {
    const uint32_t data = run.get(actor + 0x7c);
    const uint32_t state = run.get(data + 0x1c);
    if (!state) {
        run.stackPointer = run.automatic(-0x2c);
        run.call(0x4c6dd0, actor, {0x52ac34});
        run.stackPointer = run.automatic(-0x30);
        run.call(0x4c6e40, actor, {0x52ac1c, 0});
        run.put(actor + 0x118, 500000);
        run.put(actor + 0x08, run.get(actor + 0x08) | 1);
        run.put(actor + 0x118, claw_v13_next_life_threshold(run.get(0x532c3c)));
        uint32_t height = 0;
        const uint32_t image = run.get(actor + 0x198);
        if (image)
            height = run.get(image + 0x18) - run.get(image + 0x20);
        run.stackPointer = run.automatic(-0x2c);
        uint32_t display = run.call(0x4fcaea, 0, {0x60});
        if (display) {
            run.put(display, 0x50c688);
            run.stackPointer = run.automatic(-0x28);
            run.call(0x494210, display + 0x28);
            run.put(display, 0x50cd4c);
        }
        run.stackPointer = run.automatic(-0x44);
        run.call(0x493d50, display, {actor, run.get(run.get(0x535910) + 0x68), 99, 1, height, 4, 15});
        run.put(data + 0x18, display);
        run.stackPointer = run.automatic(-0x48);
        run.call(0x493b90, display + 0x28, {run.get(0x53b134), actor, run.get(0x532c3c), 8, 11, 0x24, 0, 0x52ac00});
        run.put(data + 0x1c, 5);
        return 1;
    }
    if (state != 5)
        return 1;
    run.stackPointer = run.automatic(-0x2c);
    run.call(0x4c8550, actor + 0x1a0, {run.get(0x5aafd8)});
    const uint32_t display = run.get(data + 0x18);
    if (!display)
        return 1;
    const uint32_t engine = run.get(0x535910);
    const uint32_t camera = run.get(engine + 0x68);
    if (run.get(display + 0x14) != camera || run.gets(engine + 0x6c) > 0) {
        const uint32_t limit = run.get(display + 0x18);
        run.put(display + 0x14, camera);
        if (s32(camera) <= s32(limit)) {
            const uint32_t horizontal = run.get(display + 0x04);
            uint32_t x = 0;
            bool setX = true;
            if (horizontal == 1)
                x = run.get(display + 0x08) + run.get(0x535840);
            else if (horizontal == 2)
                x = run.get(display + 0x08) + run.get(0x535848);
            else if (horizontal == 3)
                x = midpoint(run.get(0x535840), run.get(0x535848), run.get(display + 0x08));
            else
                setX = false;
            if (setX)
                run.put(run.get(display + 0x24) + 0x5c, x);
            const uint32_t vertical = run.get(display + 0x0c);
            uint32_t y = 0;
            bool setY = true;
            if (vertical == 3)
                y = midpoint(run.get(0x535844), run.get(0x53584c), run.get(display + 0x10));
            else if (vertical == 4)
                y = run.get(display + 0x10) + run.get(0x535844);
            else if (vertical == 5)
                y = run.get(display + 0x10) + run.get(0x53584c);
            else
                setY = false;
            if (setY)
                run.put(run.get(display + 0x24) + 0x60, y);
            if (!run.get(display + 0x14)) {
                run.put(display + 0x14, camera);
                run.stackPointer = run.automatic(-0x28);
                run.call(0x4941d0, display);
            }
        }
    }
    uint32_t player = run.get(0x5365d4);
    if (!player)
        return 1;
    const uint32_t score = run.get(player + 0x114);
    if (run.get(display + 0x2c) != score) {
        run.put(display + 0x2c, score);
        const uint32_t buffer = run.automatic(-0x10);
        run.stackPointer = run.automatic(-0x34);
        run.call(0x4a5b6e, 0, {buffer, 0x52abf8, score});
        uint32_t length = 0;
        while (run.get8(buffer + length))
            ++length;
        uint32_t cursor = buffer + length - run.get(display + 0x30);
        for (uint32_t i = 0; s32(i) < run.gets(display + 0x30); ++i) {
            const uint32_t digit = run.get(display + 0x34 + i * 4);
            const int32_t character = int8_t(run.get8(cursor));
            run.stackPointer = run.automatic(-0x2c);
            run.call(0x421cd0, digit, {uint32_t(character) - 0x30});
            ++cursor;
            run.put(run.get(digit + 0x7c) + 0x68, 0xffffffff);
        }
        player = run.get(0x5365d4);
    }
    if (run.gets(display + 0x2c) < run.gets(actor + 0x118))
        return 1;
    const uint32_t inventory = run.get(run.get(player + 0x7c) + 0x14);
    if (run.gets(inventory + 0x7c) < 10) {
        const uint32_t sounds = run.get(run.get(actor + 0x0c) + 0x28);
        if (!run.get(sounds + 0x30)) {
            const uint32_t local = run.automatic(0x04);
            run.put(local, 0);
            run.stackPointer = run.automatic(-0x30);
            run.call(0x4fc6b4, sounds + 0x10, {0x5285e0, local});
            const uint32_t resource = run.get(local);
            if (resource) {
                const uint32_t enabled = run.get(0x53098c);
                const uint32_t device = run.get(0x530990);
                if (enabled) {
                    const uint32_t now = run.get(0x5aafdc);
                    if (now - run.get(resource + 0x14) >= run.get(resource + 0x18)) {
                        run.put(resource + 0x14, now);
                        run.stackPointer = run.automatic(-0x38);
                        run.call(0x4b3da0, run.get(resource + 0x10), {device, 0, 0, 0});
                    }
                }
            }
        }
        run.put(inventory + 0x7c, run.get(inventory + 0x7c) + 1);
    }
    run.put(actor + 0x118, run.get(actor + 0x118) + 500000);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x416dd0:
        return function_00416dd0(run);
    case 0x46f840:
        return function_0046f840(run, receiver);
    case 0x493e90:
        return function_00493e90(run, arguments[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_v13_lives_score_entry, owned, body)
