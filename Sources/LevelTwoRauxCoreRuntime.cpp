// Level 2 Raux core
// Recovered from the original function packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x47e210:
        return 1;
    case 0x47e2d0:
        return 1;
    case 0x47e7f0:
        return 1;
    case 0x47e810:
        return 0;
    case 0x47e8e0:
        return 1;
    case 0x47ece0:
        return 1;
    case 0x47eeb0:
        return 0;
    case 0x47eef0:
        return 1;
    default:
        return -1;
    }
}

// Object layout: +0x0c entity, +0x10 state, +0x14 behavior callback,
// +0x20 action phase, +0x128 animation lookup and +0x12c resource object.
// +0x184 mode and +0x18c facing govern combat. +0x210/+0x220/+0x250/+0x260
// are rectangles; +0x28c..+0x2c8 are motion/combat parameters, +0x2e4 attack
// chance, +0x2fc bit count, +0x300 inline bits or bit-storage pointer.
// +0x308..+0x388 animation handles, +0x3a0/+0x3a4/+0x3bc/+0x410 sound
// handles, +0x3c4 target distance, +0x460..+0x474 derived state.
// Entity +0x6c is logic state; entity +0x104 damage and +0x10c health.
// Load float memory operands exactly into the binary64 primitive channel.
uint64_t floatBits(Run &run, uint32_t address) {
    double value = run.getf(address);
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}
ClawX87State floatingState() {
    ClawX87State state{};
    state.size = sizeof(state);
    state.version = CLAW_X87_VERSION;
    state.control = 0x023f;
    return state;
}
void multiplyFloat(Run &run, ClawX87State &state, uint32_t address) {
    uint64_t bits = floatBits(run, address);
    run.x87_step(CLAW_X87_MUL_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
}
uint32_t convert(Run &run, ClawX87State &state) {
    state.popCount = 1;
    state.pushCount = 0;
    state.returned = 0;
    state.eax = 0;
    state.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, state);
}
uint32_t resource(Run &run, uint32_t receiver, uint32_t name, uint32_t local) {
    run.put(local, 0);
    uint32_t manager = run.get(run.get(run.get(receiver + 0x12c) + 0x0c) + 0x28) + 0x10;
    run.call(0x4f6286, manager, {name, local});
    return run.get(local);
}
uint32_t animation(Run &run, uint32_t receiver, uint32_t name) {
    uint32_t value = run.call(0x4062e0, receiver + 0x128, {name});
    if (!value)
        value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    return value;
}
// 0x47e2d0. Base construction, animation/resource bindings, geometry and combat values.
uint32_t function_47e2d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    auto state = floatingState();
    state.popCount = 0;
    state.pushCount = 0;
    run.call_x87_exact(0x40e0d0, receiver, state, {arguments[0]});
    run.put(receiver + 0x460, 0);
    run.put(receiver + 0x464, 0);
    run.put(receiver + 0x468, 0);
    run.put(receiver + 0x46c, 0);
    run.put(receiver + 0x470, 0);
    run.put(receiver + 0x474, 0);
    run.put(receiver, 0x50f1ac);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x52b2f0});
    run.put(receiver + 0x308, animation(run, receiver, 0x52b2dc));
    run.put(receiver + 0x30c, animation(run, receiver, 0x52b2c4));
    run.put(receiver + 0x310, animation(run, receiver, 0x52b2b0));
    run.put(receiver + 0x318, 0);
    run.put(receiver + 0x31c, 0);
    run.put(receiver + 0x320, 0);
    run.put(receiver + 0x32c, animation(run, receiver, 0x52b2a0));
    run.put(receiver + 0x374, animation(run, receiver, 0x52b290));
    run.put(receiver + 0x334, animation(run, receiver, 0x52b27c));
    run.put(receiver + 0x338, animation(run, receiver, 0x52b268));
    run.put(receiver + 0x33c, animation(run, receiver, 0x52b258));
    run.put(receiver + 0x340, animation(run, receiver, 0x52b244));
    run.put(receiver + 0x344, animation(run, receiver, 0x52b234));
    run.put(receiver + 0x348, animation(run, receiver, 0x52b220));
    run.put(receiver + 0x34c, animation(run, receiver, 0x52b2c4));
    run.put(receiver + 0x350, animation(run, receiver, 0x52b210));
    run.put(receiver + 0x378, animation(run, receiver, 0x52b1fc));
    run.put(receiver + 0x37c, animation(run, receiver, 0x52b1e8));
    run.put(receiver + 0x380, animation(run, receiver, 0x52b1e8));
    run.put(receiver + 0x36c, animation(run, receiver, 0x52b1d4));
    run.put(receiver + 0x384, animation(run, receiver, 0x52b1bc));
    run.put(receiver + 0x388, animation(run, receiver, 0x52b1a8));
    uint32_t local = run.automatic(4);
    run.put(receiver + 0x3a4, resource(run, receiver, 0x52b194, local));
    run.put(receiver + 0x410, resource(run, receiver, 0x52b184, local));
    run.icall(0x546d5c, {receiver + 0x220, uint32_t(-0x75), uint32_t(-4), uint32_t(-0x1e), 0x15});
    run.icall(0x546d5c, {receiver + 0x210, uint32_t(-1), uint32_t(-1), 1, 1});
    run.icall(0x546d5c, {receiver + 0x250, uint32_t(-0xf), uint32_t(-0x3c), 0xf, 0x34});
    run.icall(0x546d5c, {receiver + 0x260, uint32_t(-0xf), uint32_t(-0x3c), 0xf, 0x34});
    run.put(receiver + 0x28c, 500);
    run.put(receiver + 0x290, 20);
    run.put(receiver + 0x29c, 300);
    run.put(receiver + 0x2a0, 20);
    run.put(receiver + 0x2a4, 150);
    run.put(receiver + 0x2a8, 20);
    run.put(receiver + 0x2ac, 100);
    run.put(receiver + 0x2b0, 20);
    run.put(receiver + 0x2b4, 0);
    run.put(receiver + 0x2b8, 0);
    run.put(receiver + 0x2bc, uint32_t(-60));
    run.put(receiver + 0x2c0, uint32_t(-20));
    run.put(receiver + 0x2c4, 20);
    run.put(receiver + 0x2c8, uint32_t(-15));
    run.put(receiver + 0x2e4, 100);
    uint64_t bits = floatBits(run, 0x5262b8);
    run.x87_step(CLAW_X87_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
    multiplyFloat(run, state, 0x50f178);
    uint32_t value = convert(run, state);
    if (value <= 99)
        value = 99;
    run.put(receiver + 0x2e4, value);
    run.put(run.get(receiver + 0x0c) + 0x10c, 100);
    run.x87_step(CLAW_X87_I32, state, {run.get(run.get(receiver + 0x0c) + 0x10c)});
    multiplyFloat(run, state, 0x5262b4);
    value = convert(run, state);
    run.put(run.get(receiver + 0x0c) + 0x10c, value);
    run.put(run.get(receiver + 0x0c) + 0x104, 10);
    run.x87_step(CLAW_X87_I32, state, {run.get(run.get(receiver + 0x0c) + 0x104)});
    multiplyFloat(run, state, 0x5262b0);
    value = convert(run, state);
    run.put(run.get(receiver + 0x0c) + 0x104, value);
    uint32_t count = run.get(receiver + 0x2fc);
    if (count > 9) {
        uint32_t flags = count <= 32 ? receiver + 0x300 : run.get(receiver + 0x300);
        run.put(flags, run.get(flags) ^ 0x200);
    }
    run.call(0x40f6c0, run.get(receiver + 0x12c), {run.get(receiver + 0x250), run.get(receiver + 0x254), run.get(receiver + 0x258), run.get(receiver + 0x25c)});
    run.call(0x4208b0, run.get(receiver + 0x12c), {0, uint32_t(-60), 20, 35});
    run.call(0x40abf0, receiver + 0x128);
    run.call(0x405060, receiver);
    return receiver;
}
// 0x47e210. Entity logic-state factory.
uint32_t function_47e210(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t entity = arguments[0];
    uint32_t logic = run.get(entity + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (!state) {
        run.put(logic + 0x1c, 1000);
        uint32_t object = run.call(0x4f63ec, 0, {0x478});
        if (object) {
            uint32_t savedFrame = run.frame;
            run.frame = run.automatic(-28);
            object = function_47e2d0(run, object, &entity);
            run.frame = savedFrame;
        }
        run.vcall(object, 0x10);
        run.put(logic + 0x18, object);
    } else if (state == 29) {
        run.vcall(run.get(logic + 0x18), 0x20);
    } else if (state == 30) {
        run.vcall(run.get(logic + 0x18), 0x1c);
    } else if (state != 1000) {
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
    }
    return 1;
}
// 0x47e810. Embedded containers and strings are destroyed in order.
uint32_t function_47e810(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
    return 0;
}
// 0x47e7f0. Scalar deleting destructor.
uint32_t function_47e7f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_47e810(run, receiver, nullptr);
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}
uint32_t captureReturn(Run &run, uint32_t receiver, uint32_t continuation) {
    ClawCompilerContext context{};
    context.size = sizeof(context);
    context.version = CLAW_CONTEXT_VERSION;
    context.inputMask = 0x5c1;
    context.outputMask = 0x5c1;
    context.continuation = continuation;
    context.eip = 0x4db5f0;
    context.esp = run.automatic(-16);
    context.ebp = receiver;
    context.fsHead = 0xffffffff;
    run.put(context.esp, continuation);
    return run.context_call(0x4db5f0, context);
}
uint32_t dispatchSlot(Run &run, uint32_t receiver, uint32_t state, uint32_t continuation) {
    uint32_t low = run.get(0x53c150);
    run.put(0x53c168, 0);
    if ((s32(state) < s32(low) || s32(state) > run.gets(0x53c154)) && !run.call(0x4db6e0, 0x53c148, {state, 0})) {
        uint32_t text = run.get(0x544b4c);
        uint32_t pc = captureReturn(run, receiver, continuation);
        run.put(0x544b14, pc);
        run.call(0x4db4d0, run.get(0x53c14c), {0x53c148, text, 12});
        return run.get(0x53c15c);
    }
    return (state - run.get(0x53c150)) * run.get(0x53c160) + run.get(0x53c158);
}
// 0x47e8e0. Registry dispatch repeats lookup before invoking the callback.
uint32_t function_47e8e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t state = arguments[0];
    uint32_t slot = dispatchSlot(run, receiver, state, 0x47e940);
    if (run.get(slot)) {
        slot = dispatchSlot(run, receiver, state, 0x47e9ba);
        run.call(run.get(slot), receiver);
    } else {
        run.call(0x40e280, receiver, {state});
    }
    return 0;
}
// 0x47ece0. Choose sounds and the permitted attack callback.
uint32_t function_47ece0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x44d000, receiver, {arguments[0]});
    int32_t choice = s32(run.call(0x4a3050, 0)) % 3;
    uint32_t local = run.automatic(4);
    if (choice >= 0 && choice <= 2) {
        uint32_t sound = choice == 0 ? 0x52b318 : choice == 1 ? 0x528510 : 0x528504;
        run.put(receiver + 0x3a0, resource(run, receiver, sound, local));
        if (choice < 2)
            run.put(receiver + 0x3bc, resource(run, receiver, choice ? 0x52b324 : 0x52b304, local));
    }
    uint32_t player = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    if (!run.get(player + 0x04))
        return 0;
    uint32_t facing = run.get(receiver + 0x18c);
    if (!((facing == 3 && run.get(player)) || (facing == 2 && !run.get(player))))
        return 0;
    uint32_t mode = run.get(receiver + 0x184);
    if (mode != 3 && mode != 4)
        return 0;
    int32_t threshold = run.gets(receiver + 0x2e4);
    if (s32(run.call(0x4a3050, 0)) % 100 >= threshold)
        return 0;
    int32_t distance = run.gets(receiver + 0x3c4);
    if (distance >= 0 && distance < 100) {
        if (run.gets(receiver + 0x20) >= 2)
            run.put(receiver + 0x14, 0x44e620);
    } else if (distance >= 100 && distance < 200) {
        if (run.gets(receiver + 0x20) >= 2)
            run.put(receiver + 0x14, 0x455350);
    } else if (distance >= 200 && distance < 500) {
        if (run.gets(receiver + 0x20) >= 2)
            run.put(receiver + 0x14, 0x47f290);
    }
    return 0;
}
// 0x47eeb0. Restore health scaled by the global difficulty factor.
uint32_t function_47eeb0(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x40e560, receiver);
    run.put(run.get(receiver + 0x0c) + 0x10c, 100);
    uint32_t entity = run.get(receiver + 0x0c);
    auto state = floatingState();
    run.x87_step(CLAW_X87_I32, state, {run.get(entity + 0x10c)});
    multiplyFloat(run, state, 0x5262b4);
    uint32_t value = convert(run, state);
    run.put(entity + 0x10c, value);
    return 0;
}
uint32_t hitName(Run &run, uint32_t receiver) {
    uint32_t value = run.call(0x441030, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
    uint32_t strings = run.get(0x5376b4);
    uint32_t count = run.get(0x5376b8);
    for (uint32_t index = 0; index != count; ++index) {
        if (strings)
            run.call(0x4f6439, strings);
        strings += 4;
    }
    return run.get(value);
}
// 0x47eef0. Hit animation check, dodge and follow-up state behavior.
uint32_t function_47eef0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x43e9c0, receiver, {0x15e});
    uint32_t name = hitName(run, receiver);
    if (!run.call(0x4a3810, 0, {name, 0x523204})) {
        run.vcall(receiver, 0x44);
        return 0;
    }
    name = hitName(run, receiver);
    if (!run.call(0x4a3810, 0, {name, 0x523210})) {
        run.vcall(receiver, 0x44);
        return 0;
    }
    int32_t distance = run.gets(receiver + 0x3c4);
    if (distance >= 0 && distance < 100) {
        run.vcall(receiver, 0x9c);
        return 0;
    }
    uint32_t player = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    run.call(run.get(player + 0x14) ? 0x44f510 : 0x44f3c0, receiver);
    run.vcall(receiver, 0x28, {arguments[0]});
    run.call(0x440e20, receiver, {arguments[0]});
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x47e210:
        return function_47e210(run, receiver, arguments);
    case 0x47e2d0:
        return function_47e2d0(run, receiver, arguments);
    case 0x47e7f0:
        return function_47e7f0(run, receiver, arguments);
    case 0x47e810:
        return function_47e810(run, receiver, arguments);
    case 0x47e8e0:
        return function_47e8e0(run, receiver, arguments);
    case 0x47ece0:
        return function_47ece0(run, receiver, arguments);
    case 0x47eeb0:
        return function_47eeb0(run, receiver, arguments);
    case 0x47eef0:
        return function_47eef0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_two_raux_core_entry, owned, body)
