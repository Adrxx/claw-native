// Original saved-player startup and message queue
// Recovered from the original packet; external callees retain original bodies.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x415ce0:
        return 0;
    case 0x46c790:
        return 0;
    case 0x46d8e0:
        return 0;
    case 0x49af30:
        return 2;
    case 0x49af90:
        return 2;
    case 0x4222a0:
        return 2;
    case 0x422370:
        return 2;
    case 0x42af70:
        return 1;
    default:
        return -1;
    }
}

// 0x415ce0 resetPlayerGlobals. cdecl, 0 stack argument(s), returns void.
uint32_t function_415ce0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    (void)receiver;
    for (uint32_t offset = 0; offset < 0x138; offset += 4)
        run.put(0x534c80 + offset, 0);
    uint32_t initial = run.get(0x52c6e4);
    run.put(0x534cf8, 3);
    run.put(0x534cfc, 3);
    run.put(0x53c9f8, initial);
    uint32_t extra = run.get(0x53725c);
    run.put(0x534cb0, 1);
    run.put(0x534cf0, 10);
    run.put(0x534cf4, 5);
    run.put(0x534cc8, 100);
    run.put(0x534d6c, 1000000);
    run.put(0x534ea8, 0);
    run.put(0x534eac, 0);
    run.put(0x534eb0, 0);
    if (extra) {
        run.put(0x534cf0, 50);
        run.put(0x534cf4, 40);
        run.put(0x534cf8, 20);
        run.put(0x534cfc, 9);
    }
    return 0;
}

// 0x46c790 clearSavedPlayerFields. thiscall, 0 stack argument(s), returns void.
uint32_t function_46c790(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // Saved-player fields occupy +0x160 through +0x24c.
    for (uint32_t offset = 0x160; offset < 0x250; offset += 4)
        run.put(receiver + offset, 0);
    return 0;
}

uint32_t function_49af30(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_49af90(Run &run, uint32_t receiver, const uint32_t *arguments);

// Camera flags +0x08, scale factors +0x18/+0x1c, position +0x10/+0x14.
void restoreCamera(Run &run, uint32_t camera, uint32_t x, uint32_t y) {
    double px = double(s32(x));
    double py = double(s32(y));
    if (!(run.get8(camera + 0x08) & 1)) {
        px *= double(run.getf(camera + 0x18));
        py *= double(run.getf(camera + 0x1c));
    }
    run.putf(camera + 0x10, float(px));
    run.putf(camera + 0x14, float(py));
    run.call(0x4d0a60, camera);
}

// 0x46d8e0 restoreSavedPlayer. thiscall, 0 stack argument(s), returns u32.
uint32_t function_46d8e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // Receiver: application +0x04, world link +0x0c, current level +0x14.
    uint32_t application = run.get(receiver + 0x04);
    // Application: pending +0xa8, checkpoint cache +0x64, kind +0xd8.
    if (!run.get(application + 0xa8))
        return 0;
    uint32_t cache = run.get(application + 0x64);
    if (!cache || run.gets(receiver + 0x14) < 1)
        return 0;
    uint32_t kind = run.get(application + 0xd8);
    run.put(application + 0xa8, 0);
    uint32_t lookupArguments[] = {run.get(receiver + 0x14), kind};
    if (!function_49af30(run, cache, lookupArguments))
        return 0;
    lookupArguments[0] = run.get(receiver + 0x14);
    uint32_t record = function_49af90(run, cache, lookupArguments);
    if (!record)
        return 0;
    // Checkpoint score +0x10, statistics +0x94..+0xa4, position +0x04/+0x08.
    run.put(0x534cc4, run.get(record + 0x10));
    run.put(0x534cc8, run.get(record + 0x94));
    run.put(0x534cf0, run.get(record + 0x98));
    run.put(0x534cf4, run.get(record + 0x9c));
    run.put(0x534cf8, run.get(record + 0xa0));
    run.put(0x534cfc, run.get(record + 0xa4));
    uint32_t x = run.get(record + 0x04);
    run.put(0x534ccc, x);
    uint32_t y = run.get(record + 0x08);
    run.put(0x534cd0, y);
    bool secondary = run.get(record + 0x04) > 0 && run.get(record + 0x08) > 0;
    if (s32(x) > 0 && s32(y) > 0) {
        uint32_t world = run.get(receiver + 0x0c);
        // Restored receiver coordinates +0x44/+0x48.
        run.put(receiver + 0x44, x);
        run.put(receiver + 0x48, run.get(0x534cd0));
        // World camera collection +0x24; primary +0x5c, array +0x38,
        // signed count +0x3c, excluded index +0x60.
        uint32_t collection = run.get(world + 0x24);
        uint32_t cameraX = run.get(0x534ccc);
        uint32_t cameraY = run.get(0x534cd0);
        restoreCamera(run, run.get(collection + 0x5c), cameraX, cameraY);
        uint32_t primary = run.get(collection + 0x5c);
        // Camera post-update integer coordinates +0x84/+0x88.
        cameraX = run.get(primary + 0x84);
        cameraY = run.get(primary + 0x88);
        if (run.gets(collection + 0x3c) > 0) {
            uint32_t index = 0;
            do {
                if (index != run.get(collection + 0x60)) {
                    uint32_t camera = run.get(run.get(collection + 0x38) + index * 4);
                    restoreCamera(run, camera, cameraX, cameraY);
                }
                uint32_t count = run.get(collection + 0x3c);
                ++index;
                if (s32(index) >= s32(count))
                    break;
            } while (true);
        }
        // Saved camera state +0x58.
        uint32_t state = run.get(record + 0x58);
        run.put(0x536f00, 1);
        run.put(0x537210, state);
    }
    uint32_t nextMillion = uint32_t(run.gets(0x534cc4) / 1000000) + 1;
    run.put(0x534d6c, nextMillion * 1000000u);
    // Nine primary words +0x28..+0x48 and secondary +0x6c..+0x8c.
    for (uint32_t index = 0; index < 9; ++index) {
        run.put(0x534d30 + index * 4, run.get(record + 0x28 + index * 4));
        if (secondary)
            run.put(0x534d08 + index * 4, run.get(record + 0x6c + index * 4));
    }
    // Receiver saved scores +0x160/+0x164; checkpoint second score +0x14.
    run.put(receiver + 0x160, run.get(record + 0x10));
    run.put(receiver + 0x164, run.get(record + 0x14));
    run.put(0x534ca4, secondary ? 1 : 0);
    return 1;
}

// 0x49af30 savedCheckpointAvailable. thiscall, 2 stack argument(s), returns u32.
uint32_t function_49af30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t level = arguments[0];
    uint32_t kind = arguments[1];
    if (s32(level) <= 0 || kind == 3)
        return 0;
    if (!kind && level == 1)
        return 0;
    uint32_t record = kind ? run.call(0x49ae60, receiver, {level, kind})
                           : run.call(0x49ae60, receiver, {level - 1, 3});
    if (!record)
        return 0;
    return run.get(record) & 2;
}

// 0x49af90 savedCheckpointRecord. thiscall, 2 stack argument(s), returns u32.
uint32_t function_49af90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t level = arguments[0];
    uint32_t kind = arguments[1];
    if (s32(level) < 0 || s32(level) >= 15 || kind == 3)
        return 0;
    if (kind)
        return run.call(0x49ae60, receiver, {level, kind});
    if (level == 1)
        return 0;
    return run.call(0x49ae60, receiver, {level - 1, 3});
}

// 0x4222a0 initializeMessageDisplay. thiscall, 2 stack argument(s), returns u32.
uint32_t function_4222a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t createFont = run.get(0x546918);
    // Display configuration and font handle at +0x20..+0x34.
    run.put(receiver + 0x24, arguments[0]);
    run.put(receiver + 0x28, arguments[1]);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x2c, 0);
    run.put(receiver + 0x30, 0);
    uint32_t font = run.call(createFont, 0, {12, 8, 0, 0, 100, 0, 0, 0, 1, 0, 0, 0, 0, 0x5250b0});
    run.put(receiver + 0x34, font);
    if (!font) {
        font = run.call(createFont, 0, {12, 8, 0, 0, 100, 0, 0, 0, 1, 0, 0, 0, 0, 0});
        run.put(receiver + 0x34, font);
    }
    return 1;
}

// 0x422370 queueStatusMessage. thiscall, 2 stack argument(s), returns u32.
uint32_t function_422370(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t text = arguments[0];
    if (!text || !run.get8(text))
        return 0;
    uint8_t flags = uint8_t(arguments[1]);
    // CStringList signed count at +0x0c.
    if ((flags & 1) && run.gets(receiver + 0x0c) > 7)
        return 0;
    if (flags & 4)
        run.call(0x4f5288, receiver);
    if (flags & 2)
        run.call(0x4f5382, receiver, {text});
    else
        run.call(0x4f53b7, receiver, {text});
    return 1;
}

// 0x42af70 replaceStatusMessage. thiscall, 1 stack argument(s), returns u32.
uint32_t function_42af70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Message-list pointer at +0x4c.
    uint32_t list = run.get(receiver + 0x4c);
    if (!list)
        return 0;
    uint32_t queueArguments[] = {arguments[0], 4};
    return function_422370(run, list, queueArguments);
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x415ce0:
        return function_415ce0(run, receiver, arguments);
    case 0x46c790:
        return function_46c790(run, receiver, arguments);
    case 0x46d8e0:
        return function_46d8e0(run, receiver, arguments);
    case 0x49af30:
        return function_49af30(run, receiver, arguments);
    case 0x49af90:
        return function_49af90(run, receiver, arguments);
    case 0x4222a0:
        return function_4222a0(run, receiver, arguments);
    case 0x422370:
        return function_422370(run, receiver, arguments);
    case 0x42af70:
        return function_42af70(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_player_startup_canonical_entry, owned, body)
