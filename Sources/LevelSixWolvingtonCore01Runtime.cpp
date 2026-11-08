// Level 6 Wolvington core, recovered from the original instruction bodies.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x49fb30:
    case 0x49fbf0:
    case 0x4a0140:
    case 0x4a0230:
    case 0x4a0740:
        return 1;
    case 0x4a0160:
    case 0x4a0800:
        return 0;
    default:
        return -1;
    }
}

void floatStep(Run &run, ClawX87State &fp, uint32_t operation, uint32_t address) {
    double value = double(run.getf(address));
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    run.x87_step(operation, fp, {uint32_t(bits), uint32_t(bits >> 32)});
}

uint32_t convert(Run &run, ClawX87State &fp) {
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}

uint32_t sounds(Run &run, uint32_t receiver) {
    // +0x12c render parent, parent +0x0c world, world +0x28 sounds.
    return run.get(run.get(run.get(receiver + 0x12c) + 0x0c) + 0x28);
}

uint32_t animation(Run &run, uint32_t receiver, uint32_t name) {
    uint32_t value = run.call(0x4062e0, receiver + 0x128, {name});
    if (value == 0)
        value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    return value;
}

// 0x49fbf0. Constructor, one parent argument.
uint32_t function_49fbf0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    // Preserve the base constructor's actual empty-stack status word.
    run.call_x87_exact(0x40e0d0, receiver, fp, {arguments[0]});
    run.put(receiver + 0x00, 0x50ff2c);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x52e090});
    run.put(receiver + 0x308, animation(run, receiver, 0x52e074));
    run.put(receiver + 0x30c, animation(run, receiver, 0x52e054));
    run.put(receiver + 0x338, animation(run, receiver, 0x52e038));
    run.put(receiver + 0x334, animation(run, receiver, 0x52e020));
    run.put(receiver + 0x350, animation(run, receiver, 0x52e008));
    run.put(receiver + 0x33c, animation(run, receiver, 0x52dff0));
    run.put(receiver + 0x340, animation(run, receiver, 0x52dff0));
    run.put(receiver + 0x32c, animation(run, receiver, 0x52dfd4));
    run.put(receiver + 0x374, animation(run, receiver, 0x52dfd4));
    run.put(receiver + 0x378, animation(run, receiver, 0x52dfbc));
    run.put(receiver + 0x37c, animation(run, receiver, 0x52dfa0));
    run.put(receiver + 0x310, animation(run, receiver, 0x52df84));
    run.put(receiver + 0x380, animation(run, receiver, 0x52dfa0));
    run.put(receiver + 0x36c, animation(run, receiver, 0x52df6c));
    run.put(receiver + 0x34c, animation(run, receiver, 0x52e054));
    run.put(receiver + 0x384, animation(run, receiver, 0x52df54));
    run.put(receiver + 0x388, animation(run, receiver, 0x52df54));
    uint32_t output = run.automatic(0x04);
    run.put(output, 0);
    run.call(0x4f6286, sounds(run, receiver) + 0x10, {0x52df38, output});
    run.put(receiver + 0x3a4, run.get(output));
    run.put(output, 0);
    run.call(0x4f6286, sounds(run, receiver) + 0x10, {0x52df1c, output});
    run.put(receiver + 0x410, run.get(output));
    run.put(receiver + 0x40c, run.call(0x4061b0, sounds(run, receiver), {0x52df00}));
    run.put(receiver + 0x3bc, run.call(0x4061b0, sounds(run, receiver), {0x52def0}));
    run.put(receiver + 0x3c0, run.call(0x4061b0, sounds(run, receiver), {0x52def0}));
    run.put(receiver + 0x474, run.call(0x4061b0, sounds(run, receiver), {0x52ded4}));
    uint32_t setRect = run.get(0x546d5c);
    run.call(setRect, 0, {receiver + 0x230, uint32_t(-101), uint32_t(-60), uint32_t(-41), uint32_t(-21)});
    run.call(setRect, 0, {receiver + 0x240, uint32_t(-67), 9, 4, 48});
    // +0x220 default attack rectangle, copied from +0x230 high attack.
    run.put(receiver + 0x220, run.get(receiver + 0x230));
    run.put(receiver + 0x224, run.get(receiver + 0x234));
    run.put(receiver + 0x228, run.get(receiver + 0x238));
    run.put(receiver + 0x22c, run.get(receiver + 0x23c));
    run.call(setRect, 0, {receiver + 0x210, uint32_t(-1), uint32_t(-1), 1, 1});
    run.call(setRect, 0, {receiver + 0x250, uint32_t(-20), uint32_t(-60), 20, 61});
    run.call(setRect, 0, {receiver + 0x260, uint32_t(-20), uint32_t(-15), 20, 15});
    run.call(0x4208b0, run.get(receiver + 0x12c), {uint32_t(-20), uint32_t(-50), 20, 50});
    run.call(0x40f6c0, run.get(receiver + 0x12c), {run.get(receiver + 0x250), run.get(receiver + 0x254), run.get(receiver + 0x258), run.get(receiver + 0x25c)});
    // +0x28c..+0x2c8 attack timing, distances and offsets; +0x2e4 reaction chance.
    run.put(receiver + 0x2b4, 0xa);
    run.put(receiver + 0x2b8, 0xfffffff6);
    run.put(receiver + 0x2bc, 0xffffffd3);
    run.put(receiver + 0x2c0, 0xffffffec);
    run.put(receiver + 0x2c4, 0x14);
    run.put(receiver + 0x2c8, 0xfffffff1);
    run.put(receiver + 0x28c, 0x1f4);
    run.put(receiver + 0x290, 0x28);
    run.put(receiver + 0x294, 0x12c);
    run.put(receiver + 0x298, 0x28);
    run.put(receiver + 0x29c, 0xc8);
    run.put(receiver + 0x2a0, 0x28);
    run.put(receiver + 0x2a4, 0x38);
    run.put(receiver + 0x2a8, 0x28);
    run.put(receiver + 0x2ac, 0x38);
    run.put(receiver + 0x2b0, 0x28);
    run.put(receiver + 0x2e4, 0x32);
    floatStep(run, fp, CLAW_X87_F64, 0x5262b8);
    floatStep(run, fp, CLAW_X87_MUL_F64, 0x50ff20);
    uint32_t chance = convert(run, fp);
    if (chance <= 99)
        chance = 99;
    run.put(receiver + 0x2e4, chance);
    // +0x0c parent; parent +0x10c health and +0x104 attack strength.
    run.put(run.get(receiver + 0x0c) + 0x10c, 100);
    uint32_t parent = run.get(receiver + 0x0c);
    run.x87_step(CLAW_X87_I32, fp, {run.get(parent + 0x10c)});
    floatStep(run, fp, CLAW_X87_MUL_F64, 0x5262b4);
    run.put(parent + 0x10c, convert(run, fp));
    run.put(run.get(receiver + 0x0c) + 0x104, 30);
    parent = run.get(receiver + 0x0c);
    run.x87_step(CLAW_X87_I32, fp, {run.get(parent + 0x104)});
    floatStep(run, fp, CLAW_X87_MUL_F64, 0x5262b0);
    run.put(parent + 0x104, convert(run, fp));
    run.put(receiver + 0x460, 0);
    uint32_t render = run.get(receiver + 0x12c);
    run.put(render + 0x164, run.get(render + 0x164) & 0xfffffffe);
    run.call(0x40abf0, receiver + 0x128);
    run.call(0x405060, receiver);
    return receiver;
}

// 0x49fb30. Factory/state forwarding.
uint32_t function_49fb30(Run &run, uint32_t, const uint32_t *arguments) {
    // Parent +0x6c logic, logic +0x1c state and +0x18 actor.
    uint32_t logic = run.get(arguments[0] + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (state == 0) {
        run.put(logic + 0x1c, 1000);
        uint32_t actor = run.call(0x4f63ec, 0, {0x478});
        if (actor != 0) {
            uint32_t savedFrame = run.frame;
            run.frame = savedFrame - 0x1c;
            actor = function_49fbf0(run, actor, arguments);
            run.frame = savedFrame;
        }
        run.vcall(actor, 0x10);
        run.put(logic + 0x18, actor);
    } else if (state == 29) {
        run.vcall(run.get(logic + 0x18), 0x20);
    } else if (state == 30) {
        run.vcall(run.get(logic + 0x18), 0x1c);
    } else if (state != 1000) {
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
    }
    return 1;
}

// 0x4a0160. Base destruction in original order.
uint32_t function_4a0160(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x00, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver + 0x00, 0x50b014);
    return 0;
}

// 0x4a0140. Deleting destructor, low flag bit selects release.
uint32_t function_4a0140(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4a0160(run, receiver, nullptr);
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

uint32_t diagnostic(Run &run, uint32_t receiver, uint32_t continuation) {
    ClawCompilerContext context{};
    context.size = sizeof(context);
    context.version = CLAW_CONTEXT_VERSION;
    context.inputMask = 0x5c1;
    context.outputMask = 0x5c1;
    context.ebp = receiver;
    context.esp = run.automatic(-0x10);
    context.eip = 0x4db5f0;
    context.fsHead = 0xffffffff;
    context.continuation = continuation;
    run.put(context.esp, continuation);
    return run.context_call(0x4db5f0, context);
}

uint32_t stateCell(Run &run, uint32_t receiver, uint32_t index, uint32_t continuation) {
    run.put(0x53ec88, 0);
    uint32_t lower = run.get(0x53ec70);
    if (s32(index) < s32(lower) || s32(index) > run.gets(0x53ec74)) {
        if (run.call(0x4db6e0, 0x53ec68, {index, 0}) == 0) {
            uint32_t message = run.get(0x544b4c);
            uint32_t pc = diagnostic(run, receiver, continuation);
            run.put(0x544b14, pc);
            run.call(0x4db4d0, run.get(0x53ec6c), {0x53ec68, message, 12});
            return run.get(0x53ec7c);
        }
        lower = run.get(0x53ec70);
    }
    return (index - lower) * run.get(0x53ec80) + run.get(0x53ec78);
}

// 0x4a0230. Table dispatch with a second independent lookup.
uint32_t function_4a0230(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t index = arguments[0];
    uint32_t cell = stateCell(run, receiver, index, 0x4a0290);
    if (run.get(cell) == 0) {
        run.call(0x40e280, receiver, {index});
    } else {
        cell = stateCell(run, receiver, index, 0x4a030a);
        run.call(run.get(cell), receiver);
    }
    return 0;
}

// 0x4a0740. Reaction to player action and facing direction.
uint32_t function_4a0740(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x44d000, receiver, {arguments[0]});
    uint32_t status = run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14);
    if (run.get(status + 0x04) == 0)
        return 0;
    uint32_t orientation = run.get(receiver + 0x18c);
    if (!(orientation == 3 && run.get(status + 0x00) != 0)) {
        if (orientation != 2 || run.get(status + 0x00) != 0)
            return 0;
    }
    uint32_t action = run.get(status + 0x3c);
    if (action - 1 > 7)
        return 0;
    if (action != 1 && action != 2 && action != 7 && action != 8)
        return 0;
    uint32_t range = run.get(receiver + 0x184);
    if (range != 3 && range != 4)
        return 0;
    int32_t threshold = run.gets(receiver + 0x2e4);
    int32_t random = s32(run.call(0x4a3050, 0));
    if (random % 100 >= threshold)
        return 0;
    if (run.gets(receiver + 0x20) < 2)
        return 0;
    run.put(receiver + 0x14, 0x44e620);
    return 0;
}

uint32_t hitNameEquals(Run &run, uint32_t receiver, uint32_t name) {
    uint32_t cell = run.call(0x441030, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
    uint32_t cleanup = run.get(0x5376b4);
    uint32_t count = run.get(0x5376b8);
    while (count != 0) {
        if (cleanup != 0)
            run.call(0x4f6439, cleanup);
        cleanup += 4;
        --count;
    }
    return run.call(0x4a3810, 0, {run.get(cell), name}) == 0;
}

// 0x4a0800. Hit response or transition back home.
uint32_t function_4a0800(Run &run, uint32_t receiver, const uint32_t *) {
    if (hitNameEquals(run, receiver, 0x523210) || hitNameEquals(run, receiver, 0x523204)) {
        run.call(0x43e9c0, receiver, {500});
        run.call(0x4a10b0, receiver);
        return 0;
    }
    if (hitNameEquals(run, receiver, 0x5240e8)) {
        run.call(0x4a0a90, receiver);
        return 0;
    }
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t home = run.call(0x4dba00, 0x537668, {0x5234ec});
    run.put(run.get(receiver + 0x10) + 0x1c, home);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x49fb30:
        return function_49fb30(run, receiver, arguments);
    case 0x49fbf0:
        return function_49fbf0(run, receiver, arguments);
    case 0x4a0140:
        return function_4a0140(run, receiver, arguments);
    case 0x4a0160:
        return function_4a0160(run, receiver, arguments);
    case 0x4a0230:
        return function_4a0230(run, receiver, arguments);
    case 0x4a0740:
        return function_4a0740(run, receiver, arguments);
    case 0x4a0800:
        return function_4a0800(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_six_wolvington_core_01_entry, owned, body)
