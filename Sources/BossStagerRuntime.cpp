// BossStager object logic
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x48ded0:
        return 1;
    default:
        return -1;
    }
}

// 0x48ded0. Object fields: +0x6c state record, +0x0c world,
// +0x08 flags, +0x40 visibility, +0x4c/+0x50 position, +0x54 rectangle.
uint32_t function_48ded0(Run &run, uint32_t, const uint32_t *arguments) {
    run.stackPointer = run.frame - 48;
    uint32_t object = arguments[0];
    uint32_t record = run.get(object + 0x6c);
    uint32_t state = run.get(record + 0x1c);
    uint32_t out = run.automatic(4);
    auto clear = [&]() {
        run.put(0x52be14, 0xffffffffu);
        run.put(0x52be18, 0xffffffffu);
    };
    auto capture = [&]() {
        uint32_t enemy = run.get(0x5349dc);
        if (enemy) {
            uint32_t y = run.get(enemy + 0x50);
            uint32_t x = run.get(enemy + 0x4c);
            run.put(0x52be14, x);
            run.put(0x52be18, y);
        }
    };
    auto lookup = [&](uint32_t name) {
        uint32_t resources = run.get(run.get(object + 0x0c) + 0x28);
        run.put(out, 0);
        run.call(0x4f6286, resources + 0x10, {name, out});
        return run.get(out);
    };
    auto sound = [&](uint32_t name) {
        uint32_t resources = run.get(run.get(object + 0x0c) + 0x28);
        if (run.get(resources + 0x30) == 0) {
            uint32_t asset = lookup(name);
            if (asset) {
                uint32_t enabled = run.get(0x532c0c);
                uint32_t volume = run.get(0x532c10);
                if (enabled) {
                    run.stackPointer = run.frame - 68;
                    run.call(0x4b45f0, run.get(asset + 0x10), {volume, 0, 0, 0});
                    run.stackPointer = run.frame - 48;
                }
            }
        }
    };
    auto dimensions = [&]() {
        return run.get(run.get(run.get(object + 0x0c) + 4) + 0x10);
    };
    auto rectangle = [&](int32_t local) {
        run.stackPointer = run.frame - 56;
        uint32_t result = run.call(0x42a450, run.get(0x5371fc), {run.automatic(local)});
        run.stackPointer = run.frame - 48;
        for (uint32_t i = 0; i < 4; ++i)
            run.put(object + 0x54 + i * 4, run.get(result + i * 4));
    };
    if (state == 0) {
        run.call(0x42b000, run.get(0x5371fc));
        uint32_t visible = run.get(object + 0x40) | 1;
        uint32_t flags = run.get(object + 8) | 4;
        run.put(object + 0x138, 0xfffffff0u);
        run.put(object + 0x13c, 0xfffffff0u);
        run.put(object + 0x40, visible);
        run.put(object + 8, flags);
        run.put(object + 0xd0, 0x800);
        run.put(object + 0xd8, 2);
        run.put(object + 0x140, 16);
        run.put(object + 0x144, 16);
        run.call(0x4c8060, object, {0x522290});
        run.put(record + 0x1c, 5);
    } else if (state == 8000) {
        clear();
        run.call(0x4c7900, object, {0x52c66c, 1});
        uint32_t visible = run.get(object + 0x40) & 0xfffffffeu;
        uint32_t flags = run.get(object + 8) & 0xfffbffffu;
        run.put(object + 0x40, visible);
        uint32_t world = run.get(object + 0x0c);
        run.put(object + 8, flags);
        uint32_t size = run.get(run.get(run.get(world + 4) + 0x10) + 0x10);
        run.put(object + 0x50, 0xffffff24u);
        run.put(object + 0x4c, uint32_t(s32(size) / 2));
        if (run.get(object + 0x64) != 8000) {
            run.put(object + 0x64, 8000);
            run.put(object + 8, flags | 0x20000);
        }
        uint32_t resources = run.get(world + 0x28);
        if (!run.get(resources + 0x30)) {
            run.put(out, 0);
            run.call(0x4f6286, resources + 0x10, {0x52c660, out});
            uint32_t asset = run.get(out);
            if (asset) {
                run.stackPointer = run.frame - 68;
                run.call(0x4208e0, asset, {run.get(0x532c10), 0, 0, 0});
                run.stackPointer = run.frame - 48;
            }
        }
        run.put(record + 0x1c, 8001);
    } else if (state == 8001) {
        uint32_t oldY = run.get(object + 0x50);
        uint32_t target = uint32_t(run.gets(dimensions() + 0x14) / 3);
        uint32_t elapsed = run.get(0x5430c4) * 200u;
        run.put(object + 0x50, oldY + elapsed / 1000u);
        rectangle(-32);
        if (run.gets(object + 0x50) >= s32(target)) {
            run.call(0x486e70, 0, {750});
            run.put(object + 0x50, target);
            sound(0x52c62c);
            sound(0x52c61c);
            run.put(record + 0x20, 1500);
            run.put(record + 0x1c, 8002);
        }
    } else if (state == 8002) {
        double operand = double(run.gets(dimensions() + 0x10)) * run.getd(0x50f898);
        uint32_t target = run.call_x87(0x4a30e0, 0, operand);
        uint32_t elapsed = run.get(0x5430c4) * 600u;
        uint32_t oldX = run.get(object + 0x4c);
        run.put(object + 0x4c, oldX + elapsed / 1000u);
        rectangle(-16);
        if (run.gets(object + 0x4c) >= s32(target)) {
            run.put(object + 0x40, run.get(object + 0x40) | 1);
            run.put(record + 0x1c, 8004);
        }
    } else if (state == 8003) {
        run.put(0x53c9c0, 1);
        run.call(0x420170, 0);
        run.call(0x4c8da0, run.get(run.get(object + 0x0c) + 8), {0, 0, 0, 0, 0x522280, 0x200000});
        run.put(record + 0x20, 950);
        if (run.get(run.get(0x537960) + 0xbc))
            run.put(record + 0x1c, 8005);
        else {
            capture();
            run.put(record + 0x1c, 8006);
        }
    } else if (state == 8004) {
        run.put(0x53c9c0, 2);
        run.put(object + 8, run.get(object + 8) | 0x10000);
    } else if (state == 8005) {
        uint32_t asset = lookup(0x52c64c);
        if (asset) {
            run.call(0x48c820, 0, {asset, 1});
            run.put(record + 0x20, run.get(run.get(asset + 0x10) + 0x28) + 100);
        }
        run.put(record + 0x1c, 8007);
    } else if (state == 8006) {
        if (run.get(0x5349dc)) {
            uint32_t asset = lookup(0x52c638);
            if (asset) {
                run.call(0x48ce40, 0, {run.get(0x5349dc), asset, 1});
                run.put(record + 0x20, run.get(run.get(asset + 0x10) + 0x28) + 100);
            }
        }
        run.put(record + 0x1c, 8008);
    } else if (state == 8007) {
        if (!run.get(run.get(0x537960) + 0xbc)) {
            clear();
            run.put(record + 0x20, 200);
            run.put(record + 0x1c, 8000);
        } else {
            capture();
            run.put(record + 0x20, 850);
            run.put(record + 0x1c, 8006);
        }
    } else if (state == 8008) {
        uint32_t active = run.get(run.get(0x537960) + 0xbc);
        clear();
        run.put(record + 0x20, active ? 500 : 850);
        run.put(record + 0x1c, active ? 8000 : 8005);
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x48ded0:
        return function_48ded0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_boss_stager_entry, owned, body)
