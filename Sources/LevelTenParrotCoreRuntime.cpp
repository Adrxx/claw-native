// Canonical Level 10 parrot construction and core states.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x465640:
    case 0x465cc0:
    case 0x465db0:
    case 0x466730:
        return 1;
    case 0x465ce0:
    case 0x4663d0:
    case 0x4664d0:
    case 0x466580:
        return 0;
    default:
        return -1;
    }
}

uint32_t balancedCall(Run &run, ClawX87State &fp, uint32_t function, uint32_t receiver,
                      std::initializer_list<uint32_t> arguments = {}) {
    fp.popCount = 0;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(function, receiver, fp, arguments);
}

uint64_t bits(double value) {
    uint64_t result;
    std::memcpy(&result, &value, sizeof(result));
    return result;
}

void loadDouble(Run &run, ClawX87State &fp, uint32_t address) {
    run.x87_step(CLAW_X87_F64, fp, {run.get(address), run.get(address + 0x4)});
}

void loadFloat(Run &run, ClawX87State &fp, uint32_t address) {
    uint64_t value = bits(double(run.getf(address)));
    run.x87_step(CLAW_X87_F64, fp, {uint32_t(value), uint32_t(value >> 32)});
}

void mulFloat(Run &run, ClawX87State &fp, uint32_t address) {
    uint64_t value = bits(double(run.getf(address)));
    run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(value), uint32_t(value >> 32)});
}

uint32_t ftol(Run &run, ClawX87State &fp) {
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}

void negateSpeed(Run &run, ClawX87State &fp, uint32_t target) {
    loadDouble(run, fp, 0x50ebe0);
    run.x87_step(CLAW_X87_CHS, fp);
    uint64_t value = run.x87_step(CLAW_X87_STP_F64, fp);
    run.put(target, uint32_t(value));
    run.put(target + 0x4, uint32_t(value >> 32));
}

// Mirrors receiver and actor horizontal ranges, then recomputes actor geometry.
void facing(Run &run, uint32_t receiver, uint32_t actor, bool right) {
    uint32_t left = run.get(receiver + 0x138);
    uint32_t other = run.get(receiver + 0x140);
    run.put(receiver + 0x138, 0u - other);
    run.put(receiver + 0x140, 0u - left);
    uint32_t flags = run.get(actor + 0x40);
    run.put(actor + 0x40, right ? (flags | 2u) : (flags & 0xfffffffdu));
    actor = run.get(receiver + 0x12c);
    left = run.get(actor + 0x118);
    if (left != 0x80000000) {
        other = run.get(actor + 0x120);
        run.put(actor + 0x118, 0u - other);
        run.put(actor + 0x120, 0u - left);
    }
    run.call(0x406150, actor);
    run.call(0x406180, actor);
}

void selectAnimation(Run &run, uint32_t receiver, uint32_t offset) {
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + offset);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
}

// 0x466580. Enter flying state, preserving original unordered comparisons.
uint32_t fly(Run &run, uint32_t receiver, ClawX87State &fp) {
    loadDouble(run, fp, receiver + 0x70);
    run.x87_step(CLAW_X87_COMP_F64, fp, {run.get(receiver + 0x88), run.get(receiver + 0x8c)});
    if (!(fp.status & 0x4000)) {
        negateSpeed(run, fp, receiver + 0x58);
        run.put(receiver + 0x50, 0);
        run.put(receiver + 0x54, 0);
    } else {
        loadDouble(run, fp, receiver + 0x68);
        run.x87_step(CLAW_X87_COMP_F64, fp, {run.get(0x50ebf0), run.get(0x50ebf4)});
        bool right = (fp.status & 0x4100) != 0;
        if (right) {
            uint32_t low = run.get(0x50ebe0);
            uint32_t high = run.get(0x50ebe4);
            run.put(receiver + 0x50, low);
            run.put(receiver + 0x54, high);
        } else {
            negateSpeed(run, fp, receiver + 0x50);
        }
        uint32_t actor = run.get(receiver + 0x12c);
        if (bool(run.get8(actor + 0x40) & 2) != right)
            facing(run, receiver, actor, right);
        run.put(receiver + 0x58, 0);
        run.put(receiver + 0x5c, 0);
    }
    uint32_t world = run.get(receiver + 0xc);
    run.put(world + 0x138, run.get(receiver + 0x210));
    run.put(world + 0x13c, run.get(receiver + 0x214));
    run.put(world + 0x140, run.get(receiver + 0x218));
    run.put(world + 0x144, run.get(receiver + 0x21c));
    if (run.get8(run.get(receiver + 0x12c) + 0x40) & 2) {
        world = run.get(receiver + 0xc);
        uint32_t other = run.get(world + 0x140);
        uint32_t left = run.get(world + 0x138);
        run.put(world + 0x138, 0u - other);
        world = run.get(receiver + 0xc);
        run.put(world + 0x140, 0u - left);
    }
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x529c08});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    selectAnimation(run, receiver, 0x410);
    return 0;
}

// 0x465640. Construct the base actors, resources, tuning, and flying state.
uint32_t construct(Run &run, uint32_t receiver, uint32_t argument, ClawX87State &fp) {
    balancedCall(run, fp, 0x44bc60, receiver, {argument});
    uint32_t base = receiver + 0x128;
    run.call(0x44aaf0, base, {argument});
    run.call(0x4f6439, receiver + 0x1a4);
    run.call(0x4f6439, receiver + 0x1a8);
    run.call(0x4dc180, receiver + 0x2f4);
    for (uint32_t offset = 0x3c8; offset <= 0x3fc; offset += 0x4)
        run.put(receiver + offset, 0);
    run.put(receiver, 0x50b16c);
    uint32_t world = run.get(receiver + 0xc);
    run.put(world + 0x8, run.get(world + 0x8) | 0x80000);
    run.put(receiver + 0x4, run.get(run.get(receiver + 0x10) + 0x168));
    run.put(receiver + 0x184, 6);
    run.put(receiver + 0x188, 0);
    run.put(receiver + 0x288, 0);
    run.put(receiver + 0x28c, 0x190);
    run.put(receiver + 0x290, 0x32);
    run.put(receiver + 0x29c, 0x12c);
    run.put(receiver + 0x2a0, 0x32);
    run.put(receiver + 0x2a4, 0xc8);
    run.put(receiver + 0x2a8, 0x32);
    run.put(receiver + 0x2ac, 0x64);
    run.put(receiver + 0x2b0, 0x32);
    run.put(receiver + 0x2e4, run.get(run.get(receiver + 0xc) + 0x108));
    run.put(receiver + 0x2e8, run.get(run.get(receiver + 0xc) + 0x114));
    run.put(receiver + 0x2ec, run.get(run.get(receiver + 0x10) + 0x68));
    run.put(receiver + 0x2f0, run.get(run.get(receiver + 0x10) + 0x68));
    run.put(receiver + 0x19c, 0xffffffff);
    run.put(receiver + 0x1a0, 0);
    run.icall(0x546cdc, {receiver + 0x210});
    run.icall(0x546cdc, {receiver + 0x220});
    run.icall(0x546cdc, {receiver + 0x230});
    run.icall(0x546cdc, {receiver + 0x240});
    run.icall(0x546cdc, {receiver + 0x250});
    run.icall(0x546cdc, {receiver + 0x260});
    uint32_t temporary = run.automatic(-0x1c);
    run.call(0x4dbe10, temporary, {0x534938, 0});
    run.call(0x4dbd60, receiver + 0x2f4, {temporary});
    run.call(0x4dbcd0, temporary);
    if (run.gets(run.get(receiver + 0x10) + 0x64) > 0)
        run.call(0x420fc0, receiver + 0x2f4, {2});
    run.call(0x420fc0, receiver + 0x2f4, {9});
    for (uint32_t offset = 0x2b4; offset <= 0x2c8; offset += 0x4)
        run.put(receiver + offset, 0);
    run.put(receiver + 0x1ac, 0);
    run.put(receiver + 0x2cc, 0);
    run.put(receiver + 0x2d0, 0);
    for (uint32_t offset = 0x308; offset <= 0x320; offset += 0x4)
        run.put(receiver + offset, 0);
    for (uint32_t offset = 0x32c; offset <= 0x388; offset += 0x4)
        run.put(receiver + offset, 0);
    uint32_t resource = run.call(0x40f780, base, {0x5266ec});
    run.put(receiver + 0x38c, resource);
    resource = run.call(0x40f780, base, {0x524870});
    run.put(receiver + 0x390, resource);
    resource = run.call(0x40f780, base, {0x524864});
    run.put(receiver + 0x394, resource);
    resource = run.call(0x40f780, base, {0x524858});
    run.put(receiver + 0x398, resource);
    resource = run.call(0x40f780, base, {0x52484c});
    run.put(receiver + 0x39c, resource);
    resource = run.call(0x40f780, base, {0x5266dc});
    run.put(receiver + 0x148, resource);
    for (uint32_t offset = 0x3a0; offset <= 0x3c0; offset += 0x4)
        run.put(receiver + offset, 0);
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x44, 0x409f4000);
    uint32_t actor = run.get(receiver + 0x12c);
    run.put(actor + 0x164, run.get(actor + 0x164) & 0xfffffffe);
    if (run.get8(run.get(receiver + 0x12c) + 0x40) & 2)
        run.call(0x4357a0, base);
    run.put(receiver + 0x400, 0);
    run.put(receiver + 0x404, 0);
    run.put(receiver, 0x50ec6c);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x529ba8});
    resource = run.call(0x4062e0, base, {0x529b94});
    if (!resource)
        resource = run.call(0x4062e0, base, {0x5234b4});
    run.put(receiver + 0x350, resource);
    resource = run.call(0x4062e0, base, {0x529b80});
    if (!resource)
        resource = run.call(0x4062e0, base, {0x5234b4});
    run.put(receiver + 0x410, resource);
    resource = run.call(0x44aa90, base, {0x529b6c});
    run.put(receiver + 0x414, resource);
    resource = run.call(0x44aa90, base, {0x529b54});
    run.put(receiver + 0x408, resource);
    resource = run.call(0x44aa90, base, {0x529b3c});
    run.put(receiver + 0x40c, resource);
    resource = run.call(0x40f780, base, {0x529b24});
    run.put(receiver + 0x418, resource);
    resource = run.call(0x40f780, base, {0x529b08});
    run.put(receiver + 0x41c, resource);
    resource = run.call(0x40f780, base, {0x529af0});
    run.put(receiver + 0x420, resource);
    resource = run.call(0x40f780, base, {0x529adc});
    run.put(receiver + 0x424, resource);
    resource = run.call(0x40f780, base, {0x529ac8});
    run.put(receiver + 0x428, resource);
    run.call(0x4296f0, receiver + 0x220, {0xffffffe6, 0xfffffffb, 0xfffffffb, 0x16});
    run.call(0x4296f0, receiver + 0x210, {0x80000000, 0, 0, 0});
    run.call(0x406290, run.get(receiver + 0x12c));
    run.call(0x40ab80, base, {0xffffffe2, 0xffffffe2, 0x1e, 0x1e});
    run.put(receiver + 0x28c, 0x1f4);
    run.put(receiver + 0x290, 0x28);
    run.put(receiver + 0x29c, 0xc8);
    run.put(receiver + 0x2a0, 0x28);
    run.put(receiver + 0x2a4, 0x96);
    run.put(receiver + 0x2a8, 0x28);
    run.put(receiver + 0x2ac, 0x64);
    run.put(receiver + 0x2b0, 0x28);
    world = run.get(receiver + 0xc);
    if (!run.get(world + 0x64))
        run.call(0x40f6a0, world, {0x2134});
    run.put(receiver + 0x2e4, 0x32);
    loadFloat(run, fp, 0x5262b8);
    mulFloat(run, fp, 0x50ebe8);
    uint32_t converted = ftol(run, fp);
    if (converted <= 0x63)
        converted = 0x63;
    run.put(receiver + 0x2e4, converted);
    run.put(run.get(receiver + 0xc) + 0x10c, 1);
    world = run.get(receiver + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(world + 0x10c)});
    mulFloat(run, fp, 0x5262b4);
    converted = ftol(run, fp);
    run.put(world + 0x10c, converted);
    run.put(run.get(receiver + 0xc) + 0x104, 0xa);
    world = run.get(receiver + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(world + 0x104)});
    mulFloat(run, fp, 0x5262b0);
    converted = ftol(run, fp);
    run.put(world + 0x104, converted);
    run.put(run.get(receiver + 0xc) + 0xcc, 7);
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x8, run.get(actor + 0x8) | 0x40);
    run.put(run.get(receiver + 0x12c) + 0xd0, 4);
    run.put(run.get(receiver + 0x12c) + 0xd4, 0x3000032);
    world = run.get(receiver + 0xc);
    run.put(receiver + 0x434, run.get(world + 0x4c));
    run.put(receiver + 0x438, run.get(world + 0x50));
    run.put(receiver + 0x430, 0);
    run.put(receiver + 0x2ec, run.get(run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14) + 0x80));
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x44, 0);
    fly(run, receiver, fp);
    return receiver;
}

// 0x465ce0. Destroy owned string and bitset members.
uint32_t destroy(Run &run, uint32_t receiver) {
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
    return 0;
}

// 0x465db0. Resolve a state handler and invoke it, or base dispatch.
uint32_t invokeState(Run &run, uint32_t function, uint32_t receiver, ClawX87State &fp);

uint32_t dispatch(Run &run, uint32_t receiver, uint32_t state, ClawX87State &fp) {
    uint32_t minimum = run.get(0x537c38);
    run.put(0x537c50, 0);
    uint32_t slot;
    if (s32(state) < s32(minimum) || s32(state) > run.gets(0x537c3c)) {
        if (!run.call(0x4db6e0, 0x537c30, {state, 0})) {
            uint32_t error = run.get(0x544b4c);
            uint32_t value = run.call(0x4db5f0, 0);
            run.put(0x544b14, value);
            run.call(0x4db4d0, run.get(0x537c34), {0x537c30, error, 0xc});
            slot = run.get(0x537c44);
            minimum = run.get(0x537c38);
        } else {
            minimum = run.get(0x537c38);
            slot = (state - minimum) * run.get(0x537c48) + run.get(0x537c40);
        }
    } else {
        slot = (state - minimum) * run.get(0x537c48) + run.get(0x537c40);
    }
    if (!run.get(slot)) {
        balancedCall(run, fp, 0x43d490, receiver, {state});
        return 0;
    }
    run.put(0x537c50, 0);
    if (s32(state) < s32(minimum) || s32(state) > run.gets(0x537c3c)) {
        if (!run.call(0x4db6e0, 0x537c30, {state, 0})) {
            uint32_t error = run.get(0x544b4c);
            uint32_t value = run.call(0x4db5f0, 0);
            run.put(0x544b14, value);
            run.call(0x4db4d0, run.get(0x537c34), {0x537c30, error, 0xc});
            invokeState(run, run.get(run.get(0x537c44)), receiver, fp);
            return 0;
        }
        minimum = run.get(0x537c38);
    }
    slot = (state - minimum) * run.get(0x537c48) + run.get(0x537c40);
    invokeState(run, run.get(slot), receiver, fp);
    return 0;
}

// 0x4663d0. Return to spawn and enter idle.
uint32_t idle(Run &run, uint32_t receiver, ClawX87State &fp) {
    run.x87_step(CLAW_X87_I32, fp, {run.get(receiver + 0x434)});
    run.put(receiver + 0x430, 0);
    uint64_t value = run.x87_step(CLAW_X87_STP_F64, fp);
    run.put(receiver + 0x68, uint32_t(value));
    run.put(receiver + 0x6c, uint32_t(value >> 32));
    run.x87_step(CLAW_X87_I32, fp, {run.get(receiver + 0x438)});
    value = run.x87_step(CLAW_X87_STP_F64, fp);
    run.put(receiver + 0x70, uint32_t(value));
    run.put(receiver + 0x74, uint32_t(value >> 32));
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x60, 0);
    run.put(receiver + 0x54, 0);
    run.put(receiver + 0x5c, 0);
    run.put(receiver + 0x64, 0);
    uint32_t actor = run.get(receiver + 0x12c);
    if (run.get8(actor + 0x40) & 2)
        facing(run, receiver, actor, false);
    selectAnimation(run, receiver, 0x350);
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x8, run.get(actor + 0x8) | 1);
    uint32_t player = run.get(0x537b14);
    if (player)
        run.put(player + 0x4b4, 0);
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    return 0;
}

// 0x4664d0. Animate idle, select speech, and allow the combat transition.
uint32_t idleTick(Run &run, uint32_t receiver, ClawX87State &fp) {
    uint32_t delta = run.get(0x5430c4);
    balancedCall(run, fp, 0x4c82a0, run.get(receiver + 0x12c) + 0x188, {delta});
    uint32_t animation = run.get(receiver + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) && !run.get(animation + 0x14)) {
        selectAnimation(run, receiver, 0x350);
        if (s32(run.call(0x4a3050, 0)) % 100 < 10) {
            uint32_t which = uint32_t(s32(run.call(0x4a3050, 0)) % 2);
            uint32_t sound = run.get(receiver + which * 4 + 0x424);
            run.call(0x48ce40, 0, {run.get(receiver + 0xc), sound, 0});
        }
    }
    uint32_t player = run.get(0x537b14);
    if (player && run.get(player + 0x4b8))
        balancedCall(run, fp, 0x467530, receiver);
    return 0;
}

// 0x466730. Set update delay and react to a changed scene clock.
uint32_t update(Run &run, uint32_t receiver, ClawX87State &fp) {
    uint32_t delay;
    if (run.get(0x541334))
        delay = 0x1fffffff;
    else
        delay = uint32_t(s32(run.call(0x4a3050, 0)) % 1001);
    run.put(receiver + 0x3c4, delay);
    balancedCall(run, fp, 0x43e420, receiver);
    uint32_t root = run.get(0x537e88);
    uint32_t scene = run.get(root + 0x6c);
    uint32_t time = run.get(run.get(scene + 0x14) + 0x80);
    if (run.get(receiver + 0x2ec) != time)
        balancedCall(run, fp, 0x467e30, receiver);
    return 0;
}

uint32_t invokeState(Run &run, uint32_t function, uint32_t receiver, ClawX87State &fp) {
    switch (function) {
    case 0x4663d0:
        return idle(run, receiver, fp);
    case 0x4664d0:
        return idleTick(run, receiver, fp);
    case 0x466580:
        return fly(run, receiver, fp);
    default:
        return run.call(function, receiver);
    }
}

uint32_t inheritedBody(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments,
                       ClawX87State &fp) {
    switch (function) {
    case 0x465640:
        return construct(run, receiver, arguments[0], fp);
    case 0x465cc0:
        destroy(run, receiver);
        if (arguments[0] & 1)
            run.call(0x4f6428, 0, {receiver});
        return receiver;
    case 0x465ce0:
        return destroy(run, receiver);
    case 0x465db0:
        return dispatch(run, receiver, arguments[0], fp);
    case 0x4663d0:
        return idle(run, receiver, fp);
    case 0x4664d0:
        return idleTick(run, receiver, fp);
    case 0x466580:
        return fly(run, receiver, fp);
    case 0x466730:
        return update(run, receiver, fp);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    auto fp = run.x87_entry(function);
    uint32_t value = inheritedBody(run, function, receiver, arguments, fp);
    run.x87_finish(function, fp);
    return value;
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_ten_parrot_core_entry, owned, body)
