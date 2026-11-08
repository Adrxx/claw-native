// Level 12 stalactite dispatch, construction and state transitions.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x48e5c0:
    case 0x48e990:
        return 1;
    case 0x48ed10:
    case 0x48ed70:
    case 0x48edd0:
    case 0x48ee10:
    case 0x48ee30:
    case 0x48eee0:
    case 0x48ef00:
    case 0x48ef90:
    case 0x48efd0:
    case 0x48f040:
        return 0;
    default:
        return -1;
    }
}

uint64_t bits(double value) {
    uint64_t result;
    std::memcpy(&result, &value, sizeof(result));
    return result;
}

// Receiver +0x10 is its definition, +0x24 its previous state.
void state(Run &run, uint32_t object, uint32_t name) {
    run.put(object + 0x24, run.get(run.get(object + 0x10) + 0x1c));
    uint32_t next = run.call(0x4dba00, 0x537668, {name});
    run.put(run.get(object + 0x10) + 0x1c, next);
}

// +0x12c is the sprite; +0x134 saves the previous animation.
void animation(Run &run, uint32_t object, uint32_t offset) {
    uint32_t sprite = run.get(object + 0x12c);
    uint32_t next = run.get(object + offset);
    run.put(object + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {next});
}

// 0x48ed10: idle entry.
uint32_t idle(Run &run, uint32_t object) {
    state(run, object, 0x523604);
    animation(run, object, 0x19c);
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    return 0;
}

// 0x48edd0: begin delay; +0x1c0 duration, +0x1bc start tick.
uint32_t delay(Run &run, uint32_t object) {
    state(run, object, 0x527278);
    run.put(object + 0x1c0, run.get(run.get(object + 0x10) + 0xbc));
    run.put(object + 0x1bc, run.get(0x537210));
    return 0;
}

// 0x48ed70: check the placed trigger rectangle against the player point.
uint32_t idleTick(Run &run, uint32_t object) {
    if (run.get(0x537e88) && run.get(object + 0x10)) {
        uint32_t rectangle = run.automatic(-16);
        run.icall(0x546d58, {rectangle, run.get(object + 0x10) + 0xf0});
        uint32_t player = run.get(0x537e88);
        uint32_t x = run.get(player + 0x4c);
        uint32_t y = run.get(player + 0x50);
        if (run.icall(0x546cd4, {rectangle, x, y}))
            delay(run, object);
    }
    return 0;
}

// 0x48ee30: falling entry. +0xc physics, +0x50..0x64 motion,
// +0x40 acceleration, +0xc8 collision flag, +0x1b8 snap sound.
uint32_t falling(Run &run, uint32_t object) {
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    state(run, object, 0x5235f8);
    run.put(run.get(object + 0xc) + 0xcc, 8);
    run.put(object + 0x50, 0);
    run.put(object + 0x58, 0);
    run.put(object + 0x60, 0);
    run.put(object + 0x54, 0);
    run.put(object + 0x5c, 0);
    run.put(object + 0x64, 0);
    run.put(object + 0x40, 0);
    run.put(object + 0x44, 0x409f4000);
    run.put(object + 0xc8, 0);
    uint32_t sprite = run.get(object + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) & 0xfffffffe);
    uint32_t sound = run.get(object + 0x1b8);
    if (sound && run.get(0x532c0c))
        run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    return 0;
}

// 0x48ee10: unsigned tick subtraction includes wraparound.
uint32_t delayTick(Run &run, uint32_t object) {
    if (run.get(0x537210) - run.get(object + 0x1bc) >= run.get(object + 0x1c0))
        falling(run, object);
    return 0;
}

// 0x48ef00: dead entry; +0x20 dead flag, +0x1a0 crumble sequence,
// +0x1b4 impact sound.
uint32_t dead(Run &run, uint32_t object) {
    state(run, object, 0x5235f0);
    run.put(object + 0x20, 1);
    run.put(object + 0xc8, 1);
    uint32_t sprite = run.get(object + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) | 1);
    animation(run, object, 0x1a0);
    uint32_t sound = run.get(object + 0x1b4);
    if (sound && run.get(0x532c0c))
        run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    return 0;
}

// 0x48eee0: physics mode one means impact.
uint32_t fallingTick(Run &run, uint32_t object) {
    if (run.get(run.get(object + 0xc) + 0xcc) == 1)
        dead(run, object);
    return 0;
}

// 0x48efd0: restart entry; +0x1a8 saves player state.
uint32_t restart(Run &run, uint32_t object) {
    state(run, object, 0x52726c);
    animation(run, object, 0x19c);
    uint32_t sprite = run.get(object + 0x12c);
    run.put(sprite + 0x40, run.get(sprite + 0x40) | 1);
    uint32_t playerState = run.get(run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14) + 0x80);
    run.put(object + 0x1a8, playerState);
    return 0;
}

// 0x48ef90: wait for the crumble animation to complete.
uint32_t deadTick(Run &run, uint32_t object) {
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    uint32_t animationObject = run.get(object + 0x12c) + 0x188;
    if (run.get(animationObject + 0x1c) && !run.get(animationObject + 0x14))
        restart(run, object);
    return 0;
}

// 0x48f040: reset when player state changes; +0x1ac/+0x1b0 original
// integer position, +0x68/+0x70 current position.
uint32_t restartTick(Run &run, uint32_t object) {
    uint32_t playerState = run.get(run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14) + 0x80);
    if (run.get(object + 0x1a8) != playerState) {
        uint32_t sprite = run.get(object + 0x12c);
        run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffffe);
        sprite = run.get(object + 0x12c);
        run.put(sprite + 0x8, run.get(sprite + 0x8) & 0xfffffffe);
        run.putd(object + 0x68, double(s32(run.get(object + 0x1ac))));
        run.putd(object + 0x70, double(s32(run.get(object + 0x1b0))));
        run.put(run.get(object + 0xc) + 0xcc, 7);
        run.put(object + 0x50, 0);
        run.put(object + 0x58, 0);
        run.put(object + 0x60, 0);
        run.put(object + 0x54, 0);
        run.put(object + 0x5c, 0);
        run.put(object + 0x64, 0);
        run.put(object + 0x40, 0);
        run.put(object + 0x44, 0);
        run.vcall(object, 0x24);
        idle(run, object);
    }
    return 0;
}

// 0x48e5c0: signed-index dispatch table lookup.
uint32_t dispatch(Run &run, uint32_t object, uint32_t index) {
    uint32_t lower = run.get(0x53c9d8);
    run.put(0x53c9f0, 0);
    uint32_t slot;
    if (s32(index) < s32(lower) || s32(index) > s32(run.get(0x53c9dc))) {
        uint32_t grown = run.call(0x4db6e0, 0x53c9d0, {index, 0});
        if (!grown) {
            uint32_t message = run.get(0x544b4c);
            uint32_t context = run.call(0x4db5f0, 0);
            uint32_t owner = run.get(0x53c9d4);
            run.put(0x544b14, context);
            run.call(0x4db4d0, owner, {0x53c9d0, message, 12});
            slot = run.get(0x53c9e4);
            lower = run.get(0x53c9d8);
        } else {
            lower = run.get(0x53c9d8);
            slot = (index - lower) * run.get(0x53c9e8) + run.get(0x53c9e0);
        }
    } else {
        slot = (index - lower) * run.get(0x53c9e8) + run.get(0x53c9e0);
    }
    if (run.get(slot)) {
        run.put(0x53c9f0, 0);
        if (s32(index) < s32(lower) || s32(index) > s32(run.get(0x53c9dc))) {
            uint32_t grown = run.call(0x4db6e0, 0x53c9d0, {index, 0});
            if (!grown) {
                uint32_t message = run.get(0x544b4c);
                uint32_t context = run.call(0x4db5f0, 0);
                uint32_t owner = run.get(0x53c9d4);
                run.put(0x544b14, context);
                run.call(0x4db4d0, owner, {0x53c9d0, message, 12});
                run.call(run.get(run.get(0x53c9e4)), object);
                return 0;
            }
            lower = run.get(0x53c9d8);
        }
        slot = (index - lower) * run.get(0x53c9e8) + run.get(0x53c9e0);
        run.call(run.get(slot), object);
    } else {
        run.call(0x4a36f0, 0, {object});
    }
    return 0;
}

// 0x48e990: constructor; +0x28 physics subobject, +0x128 sprite subobject.
uint32_t construct(Run &run, uint32_t object, uint32_t configuration) {
    run.call(0x4082f0, object, {configuration});
    run.call(0x4080a0, object + 0x28);
    run.put(object, 0x50b2a4);
    uint32_t value = run.get(run.get(object + 0x10) + 0x2c);
    run.putd(object + 0x80, value ? double(s32(value)) : run.getd(0x513e10));
    value = run.get(run.get(object + 0x10) + 0x34);
    run.putd(object + 0x88, value ? double(s32(value)) : run.getd(0x513e10));
    value = run.get(run.get(object + 0x10) + 0x30);
    run.putd(object + 0x98, value ? double(s32(value)) : run.getd(0x513e18));
    value = run.get(run.get(object + 0x10) + 0x38);
    run.putd(object + 0xa0, value ? double(s32(value)) : run.getd(0x513e18));
    uint64_t clock = bits(double(run.get(0x537210)) * run.getd(0x50f8d0));
    uint32_t physics = run.get(object + 0xc);
    uint64_t yExtent = bits(double(s32(run.get(physics + 0x14c))));
    uint64_t xExtent = bits(double(s32(run.get(physics + 0x148))));
    uint64_t y = bits(double(s32(run.get(physics + 0x50))));
    uint64_t x = bits(double(s32(run.get(physics + 0x4c))));
    run.call(0x408220, object + 0x28, {
        uint32_t(x), uint32_t(x >> 32), uint32_t(y), uint32_t(y >> 32), 0, 0,
        uint32_t(xExtent), uint32_t(xExtent >> 32), uint32_t(yExtent), uint32_t(yExtent >> 32),
        0, 0, 0, 0, 0, 0, 0, 0, uint32_t(clock), uint32_t(clock >> 32), 0, 0});
    uint64_t duration = bits(double(run.get(0x513e40)));
    run.call(0x4082d0, object + 0x28, {uint32_t(duration), uint32_t(duration >> 32)});
    run.put(object + 0x120, 0);
    run.put(object + 0x124, 0);
    run.put(run.get(object + 0xc) + 0xcc, 7);
    run.call(0x4dca10, object);
    run.call(0x408370, object + 0x128, {configuration});
    run.put(object + 0x190, configuration);
    run.put(object + 0x194, configuration);
    run.put(object + 0x198, run.get(configuration + 0x6c));
    run.put(object + 0x1bc, 0);
    run.put(object + 0x1c0, 0);
    run.put(object, 0x50f8a4);
    run.call(0x4c7970, run.get(object + 0x12c), {0x523698});
    run.put(run.get(object + 0x12c) + 0xd0, 4);
    run.put(run.get(object + 0x12c) + 0xd4, 1);
    uint32_t sequence = run.call(0x4062e0, object + 0x128, {0x523680});
    if (!sequence)
        sequence = run.call(0x4062e0, object + 0x128, {0x5234b4});
    run.put(object + 0x19c, sequence);
    sequence = run.call(0x4062e0, object + 0x128, {0x523664});
    if (!sequence)
        sequence = run.call(0x4062e0, object + 0x128, {0x5234b4});
    run.put(object + 0x1a0, sequence);
    uint32_t soundOut = run.automatic(4);
    run.put(soundOut, 0);
    uint32_t resources = run.get(run.get(run.get(object + 0x12c) + 0xc) + 0x28);
    run.call(0x4f6286, resources + 0x10, {0x52364c, soundOut});
    run.put(object + 0x1b4, run.get(soundOut));
    resources = run.get(run.get(run.get(object + 0x12c) + 0xc) + 0x28);
    uint32_t sound = run.call(0x4061b0, resources, {0x523634});
    run.put(object + 0x1b8, sound);
    run.put(object + 0x1a4, run.get(run.get(object + 0x10) + 0xb8));
    uint32_t integer = run.call_x87(0x4a30e0, 0, run.getd(object + 0x68));
    run.put(object + 0x1ac, integer);
    integer = run.call_x87(0x4a30e0, 0, run.getd(object + 0x70));
    run.put(object + 0x1b0, integer);
    run.call(0x406290, run.get(object + 0x12c));
    run.call(0x406240, run.get(object + 0x12c));
    uint32_t sprite = run.get(object + 0x12c);
    uint32_t image = run.get(sprite + 0x174);
    if (image) {
        run.put(sprite + 0x138, run.get(image + 0x20) - run.get(image + 0x18));
        run.put(sprite + 0x13c, run.get(image + 0x24) - run.get(image + 0x1c));
        run.put(sprite + 0x140, run.get(image + 0x18) + run.get(image + 0x20) - 1);
        run.put(sprite + 0x144, run.get(image + 0x24) + run.get(image + 0x1c) - 1);
    }
    run.put(run.get(object + 0xc) + 0x104, 5);
    physics = run.get(object + 0xc);
    integer = run.call_x87(0x4a30e0, 0, double(s32(run.get(physics + 0x104))) * double(run.getf(0x5262b0)));
    run.put(physics + 0x104, integer);
    idle(run, object);
    return object;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x48e5c0:
        return dispatch(run, receiver, arguments[0]);
    case 0x48e990:
        return construct(run, receiver, arguments[0]);
    case 0x48ed10:
        return idle(run, receiver);
    case 0x48ed70:
        return idleTick(run, receiver);
    case 0x48edd0:
        return delay(run, receiver);
    case 0x48ee10:
        return delayTick(run, receiver);
    case 0x48ee30:
        return falling(run, receiver);
    case 0x48eee0:
        return fallingTick(run, receiver);
    case 0x48ef00:
        return dead(run, receiver);
    case 0x48ef90:
        return deadTick(run, receiver);
    case 0x48efd0:
        return restart(run, receiver);
    case 0x48f040:
        return restartTick(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_twelve_stalactite_states_01_entry, owned, body)
