#include "ClawRuntime.hpp"
namespace {
using claw::Run;
using claw::s32;
int owned(uint32_t function) {
    switch (function) {
    case 0x407500: case 0x4078b0: case 0x407bd0: case 0x407c10:
        return 1;
    case 0x407bf0: case 0x407c40: case 0x407cc0: case 0x407d50:
    case 0x407e40: case 0x407e90: case 0x407f20: case 0x407f80: case 0x407fb0:
        return 0;
    default:
        return -1;
    }
}
uint64_t doubleBits(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}
// Original state-table lookup, with signed bounds and byte stride.
uint32_t stateSlot(Run &run, uint32_t state) {
    if (s32(state) < run.gets(0x5348f0) || s32(state) > run.gets(0x5348f4)) {
        if (!run.call(0x4db6e0, 0x5348e8, {state, 0})) {
            uint32_t error = run.get(0x544b4c);
            uint32_t result = run.call(0x4db5f0, 0);
            run.put(0x544b14, result);
            run.call(0x4db4d0, run.get(0x5348ec), {0x5348e8, error, 0xc});
            return run.get(0x5348fc);
        }
    }
    return (state - run.get(0x5348f0)) * run.get(0x534900) + run.get(0x5348f8);
}
// 0x407500. Dispatch callback on the receiver, or execute original RTTI path.
void dispatchState(Run &run, uint32_t self, uint32_t state) {
    run.put(0x534908, 0);
    uint32_t slot = stateSlot(run, state);
    if (run.get(slot)) {
        run.put(0x534908, 0);
        slot = stateSlot(run, state);
        run.call(run.get(slot), self);
    } else {
        run.call(0x4a36f0, 0, {self});
    }
}
// 0x407bf0. Restore base vtable and decrement live ordinal.
void destruct(Run &run, uint32_t self) {
    run.put(self, 0x50b26c);
    run.put(0x53490c, run.get(0x53490c) - 1);
    run.put(self, 0x50b014);
}
// 0x407bd0. Scalar deleting destructor.
uint32_t deleteObject(Run &run, uint32_t self, uint32_t flags) {
    destruct(run, self);
    if (flags & 1) {
        run.call(0x4f6428, 0, {self});
    }
    return self;
}
// 0x407c40. +0x10 logic, +0x24 saved state, +0x12c sprite, +0x134 saved animation.
uint32_t enterIdle(Run &run, uint32_t self) {
    run.put(self + 0x24, run.get(run.get(self + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523604});
    run.put(run.get(self + 0x10) + 0x1c, state);
    uint32_t sprite = run.get(self + 0x12c);
    uint32_t animation = run.get(self + 0x19c);
    run.put(self + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    uint32_t clock = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {clock});
    uint32_t boss = run.get(0x534874);
    if (boss) {
        run.put(boss + 0x4c4, 0);
    }
    return 0;
}
// 0x407d50. Start falling only while the boss is active.
uint32_t enterFalling(Run &run, uint32_t self) {
    uint32_t boss = run.get(0x534874);
    if (!boss || !run.call(0x405f80, boss)) {
        return 0;
    }
    if (!run.get(run.get(0x534874) + 0x4b8)) {
        return 0;
    }
    uint32_t clock = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {clock});
    run.put(self + 0x24, run.get(run.get(self + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x5235f8});
    run.put(run.get(self + 0x10) + 0x1c, state);
    run.put(run.get(self + 0xc) + 0xcc, 8);
    // Physics velocity and acceleration doubles retain the original store order.
    run.put(self + 0x50, 0);
    run.put(self + 0x58, 0);
    run.put(self + 0x60, 0);
    run.put(self + 0x54, 0);
    run.put(self + 0x5c, 0);
    run.put(self + 0x64, 0);
    run.put(self + 0x40, 0);
    run.put(self + 0x44, 0x409f4000);
    run.put(self + 0xc8, 0);
    uint32_t sprite = run.get(self + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) & 0xfffffffe);
    uint32_t sound = run.get(self + 0x1b4);
    if (sound) {
        uint32_t enabled = run.get(0x532c0c);
        uint32_t volume = run.get(0x532c10);
        if (enabled) {
            run.call(0x4b45f0, run.get(sound + 0x10), {volume, 0, 0, 0});
        }
    }
    run.put(run.get(0x534874) + 0x4bc, 0);
    run.put(run.get(0x534874) + 0x4c4, 1);
    return 0;
}
// 0x407cc0. Tick animation and advance the release sequence.
uint32_t tickIdle(Run &run, uint32_t self) {
    uint32_t clock = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {clock});
    uint32_t boss = run.get(0x534874);
    if (!boss || !run.call(0x405f80, boss)) {
        return 0;
    }
    boss = run.get(0x534874);
    if (!run.get(boss + 0x4b8) || !run.call(0x405f80, boss)) {
        return 0;
    }
    boss = run.get(0x534874);
    if (!run.get(boss + 0x4b8)) {
        return 0;
    }
    uint32_t object = run.get(self + 0xc);
    if (!object || !run.get(boss + 0x4bc)) {
        return 0;
    }
    uint32_t sequence = run.get(0x5235e0);
    if (sequence == run.get(object + 0x108)) {
        run.put(0x5235e0, sequence + 1);
        enterFalling(run, self);
    }
    return 0;
}
// 0x407e90. Publish death and select crumble animation and sound.
uint32_t enterDead(Run &run, uint32_t self) {
    run.put(self + 0x24, run.get(run.get(self + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x5235f0});
    run.put(run.get(self + 0x10) + 0x1c, state);
    run.put(self + 0x20, 1);
    run.put(self + 0xc8, 1);
    uint32_t sprite = run.get(self + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) | 1);
    sprite = run.get(self + 0x12c);
    uint32_t animation = run.get(self + 0x1a0);
    run.put(self + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    uint32_t sound = run.get(self + 0x1b0);
    if (sound) {
        uint32_t enabled = run.get(0x532c0c);
        uint32_t volume = run.get(0x532c10);
        if (enabled) {
            run.call(0x4b45f0, run.get(sound + 0x10), {volume, 0, 0, 0});
        }
    }
    return 0;
}
// 0x407e40. x87 unordered follows the same path as less/equal.
uint32_t tickFalling(Run &run, uint32_t self) {
    uint32_t boss = run.get(0x534874);
    if (!boss || !run.call(0x405f80, boss)) {
        return 0;
    }
    boss = run.get(0x534874);
    if (!run.get(boss + 0x4b8)) {
        return 0;
    }
    double y = run.getd(self + 0x70);
    double threshold = double(run.gets(boss + 0x4b0));
    if (!(threshold > y)) {
        run.put(boss + 0x4c4, 0);
        enterDead(run, self);
    }
    return 0;
}
// 0x407f80. Publish waiting state.
uint32_t enterWaiting(Run &run, uint32_t self) {
    run.put(self + 0x24, run.get(run.get(self + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x5235e4});
    run.put(run.get(self + 0x10) + 0x1c, state);
    run.put(self + 0x20, 1);
    return 0;
}
// 0x407f20. Stop sprite after crumble animation has completed.
uint32_t tickDead(Run &run, uint32_t self) {
    uint32_t boss = run.get(0x534874);
    if (!boss || !run.call(0x405f80, boss)) {
        return 0;
    }
    uint32_t clock = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {clock});
    uint32_t sprite = run.get(self + 0x12c);
    if (run.get(sprite + 0x1a4) && !run.get(sprite + 0x19c)) {
        run.put(sprite + 0x40, run.get(sprite + 0x40) | 1);
        enterWaiting(run, self);
    }
    return 0;
}
// 0x407fb0. Restore saved coordinates, notify sprite and re-enter idle.
uint32_t reset(Run &run, uint32_t self) {
    uint32_t sprite = run.get(self + 0x12c);
    run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffffe);
    sprite = run.get(self + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) & 0xfffffffe);
    run.putd(self + 0x68, double(run.gets(self + 0x1a4)));
    run.putd(self + 0x70, double(run.gets(self + 0x1a8)));
    run.put(run.get(self + 0xc) + 0xcc, 7);
    run.put(self + 0x50, 0);
    run.put(self + 0x58, 0);
    run.put(self + 0x60, 0);
    run.put(self + 0x54, 0);
    run.put(self + 0x5c, 0);
    run.put(self + 0x64, 0);
    run.put(self + 0x40, 0);
    run.put(self + 0x44, 0);
    run.vcall(self, 0x24);
    uint32_t boss = run.get(0x534874);
    run.put(0x5235e0, 1);
    if (boss) {
        run.put(boss + 0x4ec, run.get(boss + 0x4ec) & ~run.get(self + 0x1ac));
    }
    enterIdle(run, self);
    return 0;
}
// 0x407c10. The incoming word is removed but never read.
void message(Run &run, uint32_t self) {
    uint32_t boss = run.get(0x534874);
    if (boss && (run.get(boss + 0x4ec) & run.get(self + 0x1ac))) {
        reset(run, self);
    }
}
// 0x4078b0. Construct physics, entity and stalactite resources.
uint32_t construct(Run &run, uint32_t self, uint32_t parent) {
    run.call(0x4082f0, self, {parent});
    uint32_t physics = self + 0x28;
    run.call(0x4080a0, physics);
    run.put(self, 0x50b2a4);
    const uint32_t sourceOffsets[] = {0x2c, 0x34, 0x30, 0x38};
    const uint32_t targetOffsets[] = {0x80, 0x88, 0x98, 0xa0};
    for (uint32_t i = 0; i < 4; ++i) {
        uint32_t value = run.get(run.get(self + 0x10) + sourceOffsets[i]);
        uint32_t target = self + targetOffsets[i];
        if (!value) {
            uint32_t fallback = i < 2 ? 0x513e10 : 0x513e18;
            uint32_t low = run.get(fallback);
            uint32_t high = run.get(fallback + 0x4);
            run.put(target, low);
            run.put(target + 0x4, high);
        } else {
            run.putd(target, double(s32(value)));
        }
    }
    // Original zero-extends these globals before FILD qword.
    double scaled = double(run.get(0x537210)) * run.getd(0x50b298);
    uint32_t object = run.get(self + 0xc);
    uint64_t dy = doubleBits(double(run.gets(object + 0x14c)));
    uint64_t dx = doubleBits(double(run.gets(object + 0x148)));
    uint64_t y = doubleBits(double(run.gets(object + 0x50)));
    uint64_t x = doubleBits(double(run.gets(object + 0x4c)));
    uint64_t scale = doubleBits(scaled);
    run.call(0x408220, physics, {
        uint32_t(x), uint32_t(x >> 32), uint32_t(y), uint32_t(y >> 32), 0, 0,
        uint32_t(dx), uint32_t(dx >> 32), uint32_t(dy), uint32_t(dy >> 32),
        0, 0, 0, 0, 0, 0, 0, 0, uint32_t(scale), uint32_t(scale >> 32), 0, 0});
    uint64_t damping = doubleBits(double(run.get(0x513e40)));
    run.call(0x4082d0, physics, {uint32_t(damping), uint32_t(damping >> 32)});
    object = run.get(self + 0xc);
    run.put(self + 0x120, 0);
    run.put(self + 0x124, 0);
    run.put(object + 0xcc, 7);
    run.call(0x4dca10, self);
    uint32_t component = self + 0x128;
    run.call(0x408370, component, {parent});
    run.put(component + 0x68, parent);
    run.put(component + 0x6c, parent);
    run.put(component + 0x70, run.get(parent + 0x6c));
    run.put(self, 0x50b26c);
    run.call(0x4c7970, run.get(self + 0x12c), {0x523698});
    run.put(run.get(self + 0x12c) + 0xd0, 4);
    run.put(run.get(self + 0x12c) + 0xd4, 1);
    uint32_t animation = run.call(0x4062e0, component, {0x523680});
    if (!animation) {
        animation = run.call(0x4062e0, component, {0x5234b4});
    }
    run.put(self + 0x19c, animation);
    animation = run.call(0x4062e0, component, {0x523664});
    if (!animation) {
        animation = run.call(0x4062e0, component, {0x5234b4});
    }
    run.put(self + 0x1a0, animation);
    uint32_t manager = run.get(run.get(run.get(self + 0x12c) + 0xc) + 0x28);
    uint32_t sound = run.call(0x4061b0, manager, {0x52364c});
    run.put(self + 0x1b0, sound);
    manager = run.get(run.get(run.get(self + 0x12c) + 0xc) + 0x28);
    sound = run.call(0x4061b0, manager, {0x523634});
    run.put(self + 0x1b4, sound);
    uint32_t home = run.call_x87(0x4a30e0, 0, run.getd(self + 0x68));
    run.put(self + 0x1a4, home);
    home = run.call_x87(0x4a30e0, 0, run.getd(self + 0x70));
    run.put(self + 0x1a8, home);
    run.call(0x406290, run.get(self + 0x12c));
    run.call(0x406240, run.get(self + 0x12c));
    run.call(0x408050, run.get(self + 0x12c));
    run.put(self + 0x1ac, 0);
    uint32_t index = run.get(0x53490c);
    if (s32(index) < run.gets(0x5231f4)) {
        run.put(self + 0x1ac, run.get(0x5231e0 + index * 4));
        run.put(0x53490c, run.get(0x53490c) + 1);
    }
    uint32_t sprite = run.get(self + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) | 2);
    enterIdle(run, self);
    return self;
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x407500:
        dispatchState(run, receiver, arguments[0]);
        return 0;
    case 0x4078b0:
        return construct(run, receiver, arguments[0]);
    case 0x407bd0:
        return deleteObject(run, receiver, arguments[0]);
    case 0x407bf0:
        destruct(run, receiver);
        return 0;
    case 0x407c10:
        message(run, receiver);
        return 0;
    case 0x407c40:
        return enterIdle(run, receiver);
    case 0x407cc0:
        return tickIdle(run, receiver);
    case 0x407d50:
        return enterFalling(run, receiver);
    case 0x407e40:
        return tickFalling(run, receiver);
    case 0x407e90:
        return enterDead(run, receiver);
    case 0x407f20:
        return tickDead(run, receiver);
    case 0x407f80:
        return enterWaiting(run, receiver);
    case 0x407fb0:
        return reset(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace
CLAW_MODULE_ENTRY(claw_level_twelve_aquatis_stalactite_01_entry, owned, body)
