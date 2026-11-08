// Level 9 PegLeg core, reconstructed from original v1.0 behavior.
#include "ClawRuntime.hpp"
namespace {
using claw::Run;
using claw::s32;
// Actor fields: +0xc object, +0x10 state record, +0x12c animated object,
// +0x134 cached animation value, +0x184 state selector, +0x18c facing.
// +0x50 is velocity, +0x68 position, +0x80/+0x98 collision positions.
// Resource pointers occupy +0x308..+0x490; timestamp/duration pairs begin
// at +0x494. +0x4bc is roll destination; +0x4c0/+0x4c4 muzzle offsets;
// +0x4c8 projectile speed, +0x4cc fired, +0x4d0 repetition count, and
// +0x4d8/+0x4dc/+0x4e0 reaction and alternating-shot flags.
int owned(uint32_t f) {
    switch (f) {
    case 0x468ad0: case 0x468eb0: case 0x469480:
        return 1;
    case 0x4694a0: case 0x469510: case 0x469570: case 0x469840:
    case 0x469a40: case 0x469c40: case 0x469e20:
        return 0;
    default:
        return -1;
    }
}
ClawX87State floating() {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    return fp;
}
void loadDouble(Run &run, ClawX87State &fp, uint32_t address) {
    run.x87_step(CLAW_X87_F64, fp, {run.get(address), run.get(address + 0x4)});
}
uint64_t floatBits(Run &run, uint32_t address) {
    uint32_t bits = run.get(address);
    if ((bits & 0x7f800000) == 0x7f800000)
        return (uint64_t(bits & 0x80000000) << 32) | UINT64_C(0x7ff0000000000000) | (uint64_t(bits & 0x7fffff) << 29);
    double value = static_cast<double>(run.getf(address));
    uint64_t result;
    std::memcpy(&result, &value, sizeof(result));
    return result;
}
void loadFloat(Run &run, ClawX87State &fp, uint32_t address) {
    uint64_t bits = floatBits(run, address);
    run.x87_step(CLAW_X87_F64, fp, {uint32_t(bits), uint32_t(bits >> 32)});
}
void multiplyFloat(Run &run, ClawX87State &fp, uint32_t address) {
    uint64_t bits = floatBits(run, address);
    run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(bits), uint32_t(bits >> 32)});
}
uint32_t convert(Run &run, ClawX87State &fp) {
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}
void integerDouble(Run &run, ClawX87State &fp, uint32_t address, uint32_t value) {
    run.x87_step(CLAW_X87_I32, fp, {value});
    uint64_t bits = run.x87_step(CLAW_X87_STP_F64, fp);
    run.put(address, uint32_t(bits));
    run.put(address + 0x4, uint32_t(bits >> 32));
}
uint32_t stateSlot(Run &run, uint32_t state) {
    uint32_t first = run.get(0x537c68);
    if (s32(state) < s32(first) || s32(state) > s32(run.get(0x537c6c))) {
        if (!run.call(0x4db6e0, 0x537c60, {state, 0})) {
            uint32_t text = run.get(0x544b4c);
            uint32_t result = run.call(0x4db5f0, 0);
            run.put(0x544b14, result);
            run.call(0x4db4d0, run.get(0x537c64), {0x537c60, text, 0xc});
            return run.get(0x537c74);
        }
        first = run.get(0x537c68);
    }
    return (state - first) * run.get(0x537c78) + run.get(0x537c70);
}
// 0x468ad0: dispatch an owned actor state through its global state table.
uint32_t function_468ad0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t state = arguments[0];
    run.put(0x537c80, 0);
    uint32_t slot = stateSlot(run, state);
    if (run.get(slot)) {
        run.put(0x537c80, 0);
        slot = stateSlot(run, state);
        run.call(run.get(slot), receiver);
    } else {
        run.call(0x44c840, receiver, {state});
    }
    return 0;
}
// 0x4694a0: destroy the table and both reference-counted strings.
uint32_t function_4694a0(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
    return 0;
}
// 0x469480: deleting destructor; low flag bit controls deallocation.
uint32_t function_469480(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4694a0(run, receiver, nullptr);
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}
// 0x469510: select idle animation and reset its random delay.
uint32_t function_469510(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x44d9f0, receiver);
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + 0x350);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
    run.call(0x46a000, receiver);
    uint32_t random = run.call(0x4a3050, 0);
    run.put(receiver + 0x498, uint32_t(s32(random) % 0x3e9) + 0x5dc);
    run.put(receiver + 0x494, run.get(0x537210));
    return 0;
}
uint32_t animationResource(Run &run, uint32_t receiver, uint32_t name) {
    uint32_t resource = run.call(0x4062e0, receiver + 0x128, {name});
    if (!resource)
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    return resource;
}
uint32_t resourceManager(Run &run, uint32_t receiver) {
    return run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28);
}
// 0x468eb0: construct PegLeg and its animation, sound and roll state.
uint32_t function_468eb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    auto fp = run.x87_entry(0x468eb0);
    fp.popCount = 0;
    fp.pushCount = 0;
    run.call_x87_exact(0x44c000, receiver, fp, {arguments[0]});
    run.put(receiver + 0x494, 0);
    run.put(receiver + 0x498, 0);
    run.put(receiver + 0x49c, 0);
    run.put(receiver + 0x4a0, 0);
    run.put(receiver + 0x4a4, 0);
    run.put(receiver + 0x4a8, 0);
    run.put(receiver + 0x4ac, 0);
    run.put(receiver + 0x4b0, 0);
    run.put(receiver + 0x4b4, 0);
    run.put(receiver + 0x4b8, 0);
    run.put(receiver, 0x50ed1c);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x529f90});
    run.put(receiver + 0x344, animationResource(run, receiver, 0x529f7c));
    run.put(receiver + 0x308, animationResource(run, receiver, 0x529f64));
    run.put(receiver + 0x34c, animationResource(run, receiver, 0x529f64));
    run.put(receiver + 0x30c, animationResource(run, receiver, 0x529f48));
    run.put(receiver + 0x338, animationResource(run, receiver, 0x529f30));
    run.put(receiver + 0x334, animationResource(run, receiver, 0x529f1c));
    run.put(receiver + 0x350, animationResource(run, receiver, 0x529f08));
    run.put(receiver + 0x33c, animationResource(run, receiver, 0x529ef4));
    run.put(receiver + 0x32c, animationResource(run, receiver, 0x529edc));
    run.put(receiver + 0x374, animationResource(run, receiver, 0x529edc));
    run.put(receiver + 0x378, animationResource(run, receiver, 0x529ec4));
    run.put(receiver + 0x37c, animationResource(run, receiver, 0x529eac));
    run.put(receiver + 0x310, animationResource(run, receiver, 0x529e94));
    run.put(receiver + 0x458, animationResource(run, receiver, 0x529e7c));
    run.put(receiver + 0x380, animationResource(run, receiver, 0x529e68));
    run.put(receiver + 0x36c, animationResource(run, receiver, 0x529e68));
    run.put(receiver + 0x450, animationResource(run, receiver, 0x529e4c));
    run.put(receiver + 0x454, animationResource(run, receiver, 0x529e30));
    uint32_t local = run.automatic(4);
    run.put(local, 0);
    run.call(0x4f6286, resourceManager(run, receiver) + 0x10, {0x529e14, local});
    run.put(receiver + 0x45c, run.get(local));
    run.put(receiver + 0x414, run.call(0x4061b0, resourceManager(run, receiver), {0x529dfc}));
    run.put(receiver + 0x3a4, run.call(0x4061b0, resourceManager(run, receiver), {0x529de4}));
    run.put(receiver + 0x460, run.call(0x4061b0, resourceManager(run, receiver), {0x529dcc}));
    run.put(receiver + 0x464, run.call(0x4061b0, resourceManager(run, receiver), {0x529db4}));
    run.put(receiver + 0x468, run.call(0x4061b0, resourceManager(run, receiver), {0x529d9c}));
    run.put(receiver + 0x46c, run.call(0x4061b0, resourceManager(run, receiver), {0x529d84}));
    run.put(receiver + 0x470, run.call(0x4061b0, resourceManager(run, receiver), {0x529d6c}));
    run.put(receiver + 0x474, run.call(0x4061b0, resourceManager(run, receiver), {0x529d54}));
    run.put(receiver + 0x478, run.call(0x4061b0, resourceManager(run, receiver), {0x529d3c}));
    run.put(receiver + 0x47c, run.call(0x4061b0, resourceManager(run, receiver), {0x529d24}));
    run.put(receiver + 0x480, run.call(0x4061b0, resourceManager(run, receiver), {0x529d0c}));
    run.put(receiver + 0x484, run.call(0x4061b0, resourceManager(run, receiver), {0x529cf4}));
    run.put(receiver + 0x488, run.call(0x4061b0, resourceManager(run, receiver), {0x529cdc}));
    run.put(receiver + 0x48c, run.call(0x4061b0, resourceManager(run, receiver), {0x529cc4}));
    run.put(receiver + 0x490, run.call(0x4061b0, resourceManager(run, receiver), {0x529cb0}));
    run.call(0x4208b0, run.get(receiver + 0x12c), {uint32_t(-20), uint32_t(-50), 20, 50});
    run.call(0x406290, run.get(receiver + 0x12c));
    run.call(0x4296f0, receiver + 0x260, {uint32_t(-37), 17, 48, 49});
    run.call(0x4296f0, receiver + 0x270, {uint32_t(-37), 17, 48, 49});
    run.call(0x420fc0, receiver + 0x2f4, {8});
    loadDouble(run, fp, receiver + 0x68);
    run.put(receiver + 0x4bc, convert(run, fp));
    run.put(receiver + 0x4d8, 0);
    run.put(receiver + 0x4dc, 0);
    run.put(receiver + 0x4d0, 0);
    run.put(receiver + 0x4e0, 0);
    run.put(receiver + 0x2e4, 50);
    loadFloat(run, fp, 0x5262b8);
    multiplyFloat(run, fp, 0x50ed14);
    uint32_t health = convert(run, fp);
    if (health <= 99)
        health = 99;
    run.put(receiver + 0x2e4, health);
    run.put(run.get(receiver + 0xc) + 0x10c, 7);
    uint32_t object = run.get(receiver + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(object + 0x10c)});
    multiplyFloat(run, fp, 0x5262b4);
    run.put(object + 0x10c, convert(run, fp));
    run.put(run.get(receiver + 0xc) + 0x104, 10);
    object = run.get(receiver + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(object + 0x104)});
    multiplyFloat(run, fp, 0x5262b0);
    run.put(object + 0x104, convert(run, fp));
    run.call(0x40abf0, receiver + 0x128);
    function_469510(run, receiver, nullptr);
    run.x87_finish(0x468eb0, fp);
    return receiver;
}
bool seesPlayer(Run &run, uint32_t receiver) {
    if (run.get(0x534eac) == 0x26b7)
        return false;
    uint32_t player = run.get(0x537e88);
    uint32_t actor = run.get(receiver + 0x194);
    uint32_t world = run.get(run.get(run.get(receiver + 0x190) + 0xc) + 0x24);
    if (!run.call(0x4cda10, world, {run.get(actor + 0x4c), run.get(actor + 0x50), run.get(player + 0x4c), 0x20}))
        return false;
    actor = run.get(receiver + 0x194);
    player = run.get(0x537e88);
    uint32_t y = run.get(actor + 0x50);
    uint32_t py = run.get(player + 0x50);
    return s32(py) < s32(y + 50) && s32(py) > s32(y - 50) && run.get(actor + 0x38) != UINT32_MAX;
}
uint32_t function_469c40(Run &run, uint32_t receiver, const uint32_t *);
// 0x469570: home sight reactions and movement selection.
uint32_t function_469570(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (!run.get(receiver + 0x4d8)) {
        if (!run.get(receiver + 0x4e0) && seesPlayer(run, receiver)) {
            if (s32(run.call(0x4a3050, 0)) % 101 < 50) {
                int32_t index = s32(run.call(0x4a3050, 0)) % 2;
                run.call(0x48ce40, 0, {run.get(receiver + 0xc), run.get(receiver + 0x480 + uint32_t(index) * 4), 0});
            }
            run.put(receiver + 0x4e0, 1);
        }
    }
    if (run.get(receiver + 0x4d8) && seesPlayer(run, receiver)) {
        int32_t index = s32(run.call(0x4a3050, 0)) % 2;
        run.call(0x48ce40, 0, {run.get(receiver + 0xc), run.get(receiver + 0x488 + uint32_t(index) * 4), 0});
        run.put(receiver + 0x4d8, 0);
        run.put(receiver + 0x4b0, 3000);
        run.put(receiver + 0x4ac, run.get(0x537210));
        run.vcall(receiver, 0x58);
        return 0;
    }
    switch (run.get(receiver + 0x184)) {
    case 0: case 1:
        if (s32(run.call(0x4a3050, 0)) % 101 < 50)
            run.call(0x4a1180, receiver);
        else
            function_469c40(run, receiver, nullptr);
        break;
    case 2:
        if (s32(run.call(0x4a3050, 0)) % 101 < 70)
            run.vcall(receiver, 0x58);
        else
            run.call(0x46a040, receiver);
        break;
    case 3: case 4:
        if (s32(run.call(0x4a3050, 0)) % 101 < 70)
            run.call(0x46a040, receiver);
        break;
    case 5: case 6:
        if (!seesPlayer(run, receiver))
            run.call(0x44edd0, receiver);
        break;
    }
    return 0;
}
void selectAnimation(Run &run, uint32_t receiver, uint32_t offset) {
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + offset);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
}
// 0x469840: enter firing, choose muzzle offset and facing velocity.
uint32_t function_469840(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    if (run.get(0x537210) - run.get(receiver + 0x4a4) < run.get(receiver + 0x4a8)) {
        run.vcall(receiver, 0x44);
        return 0;
    }
    run.call(run.get(receiver + 0x18c) == 2 ? 0x4357a0 : 0x406310, receiver + 0x128);
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x524548});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    if (s32(run.call(0x4a3050, 0)) % 101 < 25) {
        int32_t index = s32(run.call(0x4a3050, 0)) % 4;
        run.call(0x48ce40, 0, {run.get(receiver + 0xc), run.get(receiver + 0x470 + uint32_t(index) * 4), 0});
    }
    bool toggle = run.get(0x537210) - run.get(receiver + 0x4ac) < run.get(receiver + 0x4b0) || run.get(0x537964) == 10;
    bool high = toggle ? run.get(receiver + 0x4dc) != 0 : run.get(run.get(0x537e88) + 0xcc) == 5;
    selectAnimation(run, receiver, high ? 0x458 : 0x310);
    run.put(receiver + 0x4c4, high ? 15 : uint32_t(-24));
    if (toggle)
        run.put(receiver + 0x4dc, run.get(receiver + 0x4dc) == 0);
    bool facing = (run.get8(run.get(receiver + 0x12c) + 0x40) & 2) != 0;
    run.put(receiver + 0x4c0, facing ? 55 : uint32_t(-55));
    run.put(receiver + 0x4c8, facing ? 500 : uint32_t(-500));
    run.put(receiver + 0x4cc, 0);
    return 0;
}
void sound(Run &run, uint32_t receiver, uint32_t offset) {
    uint32_t record = run.get(receiver + offset);
    if (record && run.get(0x532c0c))
        run.call(0x4b45f0, run.get(record + 0x10), {run.get(0x532c10), 0, 0, 0});
}
// 0x469a40: create a projectile once and leave on animation completion.
uint32_t function_469a40(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t progress = run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (progress == 1 && !run.get(receiver + 0x4cc)) {
        uint32_t yOffset = run.get(receiver + 0x4c4);
        run.put(receiver + 0x4cc, 1);
        uint32_t actor = run.get(receiver + 0x12c);
        uint32_t bullet = run.call(0x4c8da0, run.get(run.get(run.get(receiver + 0x130) + 0xc) + 0x8), {0, run.get(receiver + 0x4c0) + run.get(actor + 0x4c), yOffset + run.get(actor + 0x50), run.get(actor + 0x64) - 1, 0x522e0c, 0x40000});
        run.call(0x4c7970, bullet, {0x524130});
        uint32_t callback = run.get(bullet + 0x6c);
        run.put(bullet + 0x104, 10);
        run.put(bullet + 0xd0, 0x40);
        run.call(run.get(callback + 0x10), 0, {bullet});
        uint32_t data = run.get(run.get(bullet + 0x6c) + 0x18);
        run.putd(data + 0x50, double(s32(run.get(receiver + 0x4c8))));
        data = run.get(run.get(bullet + 0x6c) + 0x18);
        run.put(data + 0x58, 0);
        run.put(data + 0x5c, 0);
        data = run.get(run.get(bullet + 0x6c) + 0x18);
        run.put(data + 0x40, 0);
        run.put(data + 0x44, 0);
        if (s32(run.get(receiver + 0x4c8)) < 0) {
            data = run.get(run.get(bullet + 0x6c) + 0x18);
            actor = run.get(data + 0x12c);
            if (!(run.get8(actor + 0x40) & 2)) {
                uint32_t old = run.get(data + 0x138);
                run.put(data + 0x138, 0 - run.get(data + 0x140));
                run.put(data + 0x140, 0 - old);
                run.put(actor + 0x40, run.get(actor + 0x40) | 2);
                actor = run.get(data + 0x12c);
                run.call(0x406120, actor);
                run.call(0x406150, actor);
                run.call(0x406180, actor);
            }
        }
        sound(run, receiver, 0x45c);
        run.put(receiver + 0x4a8, 1000);
        run.put(receiver + 0x4a4, run.get(0x537210));
    }
    uint32_t animation = run.get(receiver + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) && !run.get(animation + 0x14)) {
        bool elapsed = run.get(0x537210) - run.get(receiver + 0x4ac) >= run.get(receiver + 0x4b0);
        if (run.get(0x537964) == 10 && elapsed) {
            uint32_t count = run.get(receiver + 0x4d0) + 1;
            run.put(receiver + 0x4d0, count);
            if (s32(count) >= 2) {
                run.put(receiver + 0x4d0, 0);
                run.vcall(receiver, 0x44);
                return 0;
            }
        } else if (elapsed) {
            run.vcall(receiver, 0x44);
            return 0;
        }
        run.put(receiver + 0x4a8, 0);
        run.put(receiver + 0x4a4, run.get(0x537210));
        run.vcall(receiver, 0x58);
    }
    return 0;
}
void restoreBounds(Run &run, uint32_t receiver) {
    uint32_t actor = run.get(receiver + 0x12c);
    run.put(actor + 0x128, uint32_t(-20));
    run.put(actor + 0x12c, uint32_t(-50));
    run.put(actor + 0x130, 20);
    run.put(actor + 0x134, 50);
    run.vcall(receiver, 0x58);
}
// 0x469c40: begin rolling with a direction-dependent destination.
uint32_t function_469c40(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(0x537210) - run.get(receiver + 0x49c) < run.get(receiver + 0x4a0)) {
        run.vcall(receiver, 0x44);
        return 0;
    }
    run.call(run.get(receiver + 0x18c) == 2 ? 0x4357a0 : 0x406310, receiver + 0x128);
    auto fp = floating();
    integerDouble(run, fp, receiver + 0x50, run.get(receiver + 0x18c) == 3 ? uint32_t(-250) : 250);
    uint32_t direction = run.get(receiver + 0x18c);
    uint32_t delta = direction == 3 ? uint32_t(-150) : 150;
    loadDouble(run, fp, receiver + 0x68);
    uint32_t destination = convert(run, fp) + delta;
    run.put(receiver + 0x4bc, destination);
    if (run.get(0x537964) == 9) {
        uint32_t player = run.get(0x537e88);
        if (direction == 3 && s32(run.get(player + 0x4c)) >= s32(destination)) {
            destination = run.get(player + 0x4c) + 35;
            run.put(receiver + 0x4bc, destination);
            run.x87_step(CLAW_X87_I32, fp, {destination});
            loadDouble(run, fp, receiver + 0x68);
            run.x87_step(CLAW_X87_COMPP, fp);
            if (fp.status & 0x4100) {
                run.vcall(receiver, 0x58);
                return 0;
            }
        } else if (direction == 2 && s32(run.get(player + 0x4c)) <= s32(destination)) {
            destination = run.get(player + 0x4c) - 35;
            run.put(receiver + 0x4bc, destination);
            run.x87_step(CLAW_X87_I32, fp, {destination});
            loadDouble(run, fp, receiver + 0x68);
            run.x87_step(CLAW_X87_COMPP, fp);
            if (!(fp.status & 0x100)) {
                run.vcall(receiver, 0x58);
                return 0;
            }
        }
    }
    sound(run, receiver, 0x490);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0x406f4000);
    run.put(receiver + 0x18, 0x46a000);
    run.put(receiver + 0x20, 1);
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x529c7c});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    selectAnimation(run, receiver, 0x450);
    uint32_t actor = run.get(receiver + 0x12c);
    run.put(actor + 0x128, 0x80000000);
    run.put(actor + 0x12c, 0);
    run.put(actor + 0x130, 0);
    run.put(actor + 0x134, 0);
    run.put(receiver + 0x4b8, 1500);
    run.put(receiver + 0x4b4, run.get(0x537210));
    return 0;
}
// 0x469e20: restore bounds at destination, obstacle or timeout.
uint32_t function_469e20(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    auto fp = floating();
    integerDouble(run, fp, receiver + 0x50, run.get(receiver + 0x18c) == 3 ? uint32_t(-250) : 250);
    loadDouble(run, fp, receiver + 0x68);
    uint32_t position = convert(run, fp);
    uint32_t direction = run.get(receiver + 0x18c);
    bool reached = false;
    if (run.get(0x537964) == 9) {
        uint32_t player = run.get(0x537e88);
        reached = (direction == 3 && (s32(position) <= s32(run.get(receiver + 0x4bc)) || s32(position) <= s32(run.get(player + 0x4c) + 35))) ||
                  (direction == 2 && (s32(position) >= s32(run.get(receiver + 0x4bc)) || s32(position) >= s32(run.get(player + 0x4c) - 35)));
    } else {
        reached = (direction == 3 && s32(position) <= s32(run.get(receiver + 0x4bc))) ||
                  (direction == 2 && s32(position) >= s32(run.get(receiver + 0x4bc)));
    }
    if (reached) {
        restoreBounds(run, receiver);
        return 0;
    }
    bool obstacle = false;
    if (direction == 3 || direction == 2) {
        loadDouble(run, fp, receiver + 0x68);
        uint32_t other = receiver + (direction == 3 ? 0x80 : 0x98);
        run.x87_step(CLAW_X87_COMP_F64, fp, {run.get(other), run.get(other + 0x4)});
        obstacle = (fp.status & 0x4000) != 0;
    }
    if (obstacle)
        restoreBounds(run, receiver);
    if (run.get(0x537210) - run.get(receiver + 0x4b4) >= run.get(receiver + 0x4b8))
        restoreBounds(run, receiver);
    return 0;
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x468ad0:
        return function_468ad0(run, receiver, arguments);
    case 0x468eb0:
        return function_468eb0(run, receiver, arguments);
    case 0x469480:
        return function_469480(run, receiver, arguments);
    case 0x4694a0:
        return function_4694a0(run, receiver, arguments);
    case 0x469510:
        return function_469510(run, receiver, arguments);
    case 0x469570:
        return function_469570(run, receiver, arguments);
    case 0x469840:
        return function_469840(run, receiver, arguments);
    case 0x469a40:
        return function_469a40(run, receiver, arguments);
    case 0x469c40:
        return function_469c40(run, receiver, arguments);
    case 0x469e20:
        return function_469e20(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_level_nine_peg_leg_core_01_entry, owned, body)
