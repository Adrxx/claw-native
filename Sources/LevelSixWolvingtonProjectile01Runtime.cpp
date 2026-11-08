// Original Level 6 Wolvington projectile entries.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x410340: return 1;
    case 0x411cf0: return 1;
    case 0x411e70: return 1;
    case 0x412150: return 0;
    case 0x458010: return 1;
    default: return -1;
    }
}

// 0x411cf0. Bullet constructor; +0x12c actor and +0x130 scene owner.
uint32_t bulletConstructor(Run &run, uint32_t self, uint32_t object) {
    run.call(0x4107c0, self, {object});
    run.put(self, 0x50b87c);
    run.call(0x4c7970, run.get(self + 0x12c), {0x5242f0});
    const uint32_t resultSlot = run.automatic(4);
    run.put(resultSlot, 0);
    uint32_t actor = run.get(self + 0x12c);
    uint32_t resources = run.get(run.get(actor + 0xc) + 0x2c);
    run.call(0x4f6286, resources + 0x10, {0x52417c, resultSlot});
    run.put(self + 0x148, run.get(resultSlot));
    uint32_t info = run.get(self + 0xc);
    run.put(info + 0x8, run.get(info + 0x8) | 0x80000);
    if (run.get(0x53724c) == 0 && run.get(run.get(0x5371fc) + 0x124) != 0) {
        actor = run.get(self + 0x12c);
        uint32_t z = run.get(actor + 0x64) - 1;
        uint32_t y = run.get(actor + 0x50);
        uint32_t x = run.get(actor + 0x4c);
        uint32_t scene = run.get(run.get(run.get(self + 0x130) + 0xc) + 0x8);
        uint32_t light = run.call(0x4c8da0, scene, {0, x, y, z, 0x522e14, 0x40000});
        run.put(self + 0x154, light);
        run.put(self + 0x150, 2);
    } else {
        run.put(self + 0x154, 0);
        run.put(self + 0x150, 1);
    }
    run.put(run.get(self + 0x12c) + 0xd0, 0x40);
    return self;
}

// 0x410340. Actor +0x6c holds logic, +0x1c its message, +0x18 its object.
uint32_t bulletLogic(Run &run, uint32_t actor) {
    uint32_t logic = run.get(actor + 0x6c);
    uint32_t message = run.get(logic + 0x1c);
    if (message == 0) {
        run.put(logic + 0x1c, 1000);
        uint32_t object = run.call(0x4f63ec, 0, {0x158});
        if (object) {
            uint32_t savedFrame = run.frame;
            run.frame -= 28;
            object = bulletConstructor(run, object, actor);
            run.frame = savedFrame;
        }
        run.vcall(object, 0x10);
        run.put(logic + 0x18, object);
    } else if (message == 0x1d) {
        run.vcall(run.get(logic + 0x18), 0x20);
    } else if (message == 0x1e) {
        run.vcall(run.get(logic + 0x18), 0x1c);
    } else if (message != 1000) {
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
    }
    return 1;
}

// 0x411e70. Dispatch a state from the MFC table rooted at 0x534ad8.
uint32_t selectStateSlot(Run &run, uint32_t state) {
    uint32_t first = run.get(0x534ae0);
    if (s32(state) < s32(first) || s32(state) > s32(run.get(0x534ae4))) {
        if (!run.call(0x4db6e0, 0x534ad8, {state, 0})) {
            uint32_t description = run.get(0x544b4c);
            run.put(0x544b14, run.call(0x4db5f0, 0));
            run.call(0x4db4d0, run.get(0x534adc), {0x534ad8, description, 0xc});
            return run.get(0x534aec);
        }
        first = run.get(0x534ae0);
    }
    return (state - first) * run.get(0x534af0) + run.get(0x534ae8);
}

uint32_t setBulletState(Run &run, uint32_t self, uint32_t state) {
    run.put(0x534af8, 0);
    uint32_t slot = selectStateSlot(run, state);
    if (run.get(slot)) {
        run.put(0x534af8, 0);
        slot = selectStateSlot(run, state);
        run.call(run.get(slot), self);
    } else {
        run.call(0x473f40, self, {state});
    }
    return 0;
}

ClawX87State floatingState() {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    return fp;
}

uint32_t convert(Run &run, ClawX87State &fp) {
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}

uint32_t randomCoordinate(Run &run, uint32_t lower, uint32_t upper) {
    uint32_t width = upper - lower + 1;
    uint32_t value = run.call(0x4a3050, 0);
    if (width == 0)
        return (value & 1) ? lower : upper;
    int64_t remainder = int64_t(s32(value)) % int64_t(s32(width));
    return lower + uint32_t(remainder);
}

// 0x412150. Falling state: +0x150 glitter count, +0x154 attached light.
uint32_t falling(Run &run, uint32_t self) {
    run.call(0x4742f0, self);
    ClawX87State fp = floatingState();
    uint32_t index = 0;
    if (s32(run.get(self + 0x150)) > 0) {
        do {
            uint32_t xLow = run.get(self + 0x68);
            uint32_t xHigh = run.get(self + 0x6c);
            uint32_t info = run.get(self + 0xc);
            uint32_t upper = run.get(info + 0x120);
            uint32_t lower = run.get(info + 0x118);
            uint32_t coordinate = randomCoordinate(run, lower, upper);
            run.x87_step(CLAW_X87_I32, fp, {coordinate});
            run.x87_step(CLAW_X87_ADD_F64, fp, {xLow, xHigh});
            uint32_t x = convert(run, fp);
            uint32_t yLow = run.get(self + 0x70);
            info = run.get(self + 0xc);
            uint32_t yHigh = run.get(self + 0x74);
            upper = run.get(info + 0x124);
            lower = run.get(info + 0x11c);
            coordinate = randomCoordinate(run, lower, upper);
            info = run.get(self + 0xc);
            run.x87_step(CLAW_X87_I32, fp, {coordinate});
            uint32_t z = run.get(info + 0x64) - 1;
            run.x87_step(CLAW_X87_ADD_F64, fp, {yLow, yHigh});
            uint32_t y = convert(run, fp);
            uint32_t scene = run.get(run.get(run.get(self + 0x130) + 0xc) + 0x8);
            uint32_t glitter = run.call(0x4c8da0, scene, {0, x, y, z, 0x522594, 0x40000});
            uint32_t callback = run.get(run.get(glitter + 0x6c) + 0x10);
            run.call(callback, 0, {glitter});
            index += 1;
        } while (s32(index) < s32(run.get(self + 0x150)));
    }
    uint32_t light = run.get(self + 0x154);
    if (light) {
        run.x87_step(CLAW_X87_F64, fp, {run.get(self + 0x50), run.get(self + 0x54)});
        run.x87_step(CLAW_X87_COMP_F64, fp, {run.get(0x50b7f0), run.get(0x50b7f4)});
        if (fp.status & 0x100) {
            uint32_t shape = run.get(run.get(light + 0x6c) + 0x18) + 0x28;
            uint32_t info = run.get(shape + 0x4);
            if (!(run.get8(info + 0x40) & 2)) {
                uint32_t left = run.get(shape + 0x10);
                uint32_t right = run.get(shape + 0x18);
                run.put(shape + 0x10, 0u - right);
                run.put(shape + 0x18, 0u - left);
                run.put(info + 0x40, run.get(info + 0x40) | 2);
                info = run.get(shape + 0x4);
                uint32_t lower = run.get(info + 0x118);
                if (lower != 0x80000000) {
                    uint32_t upper = run.get(info + 0x120);
                    run.put(info + 0x118, 0u - upper);
                    run.put(info + 0x120, 0u - lower);
                }
                run.call(0x406150, info);
                run.call(0x406180, info);
            }
        }
        run.x87_step(CLAW_X87_F64, fp, {run.get(self + 0x68), run.get(self + 0x6c)});
        uint32_t x = convert(run, fp);
        run.put(run.get(self + 0x154) + 0x4c, x);
        run.x87_step(CLAW_X87_F64, fp, {run.get(self + 0x70), run.get(self + 0x74)});
        uint32_t y = convert(run, fp);
        run.put(run.get(self + 0x154) + 0x50, y);
    }
    return 0;
}

// 0x458010. Wolvington light-effect lifecycle callback.
uint32_t lightLogic(Run &run, uint32_t actor) {
    uint32_t logic = run.get(actor + 0x6c);
    uint32_t message = run.get(logic + 0x1c);
    if (message == 0) {
        run.put(logic + 0x1c, 1000);
        uint32_t object = run.call(0x4f63ec, 0, {0x4c});
        if (object) {
            run.call(0x458120, object, {actor});
            run.put(object, 0x50e724);
            run.call(0x4c7970, run.get(object + 0x2c), {0x528720});
            uint32_t actorLink = run.get(object + 0x2c);
            uint32_t slot = run.automatic(4);
            run.put(slot, 0);
            uint32_t resources = run.get(run.get(actorLink + 0xc) + 0x2c);
            run.call(0x4f6286, resources + 0x10, {0x528720, slot});
            run.put(object + 0x48, run.get(slot));
        }
        run.vcall(object, 0x10);
        run.put(logic + 0x18, object);
    } else if (message == 0x1d) {
        run.vcall(run.get(logic + 0x18), 0x20);
    } else if (message == 0x1e) {
        run.vcall(run.get(logic + 0x18), 0x1c);
    } else if (message != 1000) {
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x410340: return bulletLogic(run, arguments[0]);
    case 0x411cf0: return bulletConstructor(run, receiver, arguments[0]);
    case 0x411e70: return setBulletState(run, receiver, arguments[0]);
    case 0x412150: return falling(run, receiver);
    case 0x458010: return lightLogic(run, arguments[0]);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_six_wolvington_projectile_01_entry, owned, body)
