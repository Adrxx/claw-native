// Level 8 Gabriel death states, recovered from original v1.0 entries.
#include "ClawRuntime.hpp"
namespace {
using claw::Run;
using claw::s32;
int owned(uint32_t function) {
    switch (function) {
    case 0x445090: case 0x4452d0: case 0x4455b0: case 0x445600:
    case 0x445660: case 0x4456c0: case 0x445720: case 0x445810: case 0x445950:
        return 0;
    case 0x48cf90:
        return 1;
    default:
        return -1;
    }
}
ClawX87State floatingState() {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    return fp;
}
void step(Run &run, ClawX87State &fp, uint32_t operation) {
    run.x87_step(operation, fp);
}
void operand(Run &run, ClawX87State &fp, uint32_t operation, uint64_t value) {
    run.x87_step(operation, fp, {uint32_t(value), uint32_t(value >> 32)});
}
uint64_t bits(Run &run, uint32_t address) {
    return uint64_t(run.get(address)) | (uint64_t(run.get(address + 4)) << 32);
}
void memory(Run &run, ClawX87State &fp, uint32_t operation, uint32_t address) {
    operand(run, fp, operation, bits(run, address));
}
uint64_t store(Run &run, ClawX87State &fp, bool pop) {
    return run.x87_step(pop ? CLAW_X87_STP_F64 : CLAW_X87_ST_F64, fp);
}
void publish(Run &run, ClawX87State &fp, uint32_t address) {
    const uint64_t value = store(run, fp, true);
    run.put(address, uint32_t(value));
    run.put(address + 4, uint32_t(value >> 32));
}
void exchange(Run &run, ClawX87State &fp, uint32_t index) {
    step(run, fp, CLAW_X87_ST(CLAW_X87_XCH_ST, index));
}
void duplicate(Run &run, ClawX87State &fp, uint32_t index) {
    step(run, fp, CLAW_X87_ST(CLAW_X87_LD_ST, index));
}
void clearVelocity(Run &run, uint32_t object) {
    // +0x50, +0x58, +0x60: velocity vector.
    run.put(object + 0x50, 0);
    run.put(object + 0x58, 0);
    run.put(object + 0x60, 0);
    run.put(object + 0x54, 0);
    run.put(object + 0x5c, 0);
    run.put(object + 0x64, 0);
}
void reflectPair(Run &run, uint32_t object, uint32_t left, uint32_t right) {
    const uint32_t oldLeft = run.get(object + left);
    const uint32_t oldRight = run.get(object + right);
    run.put(object + left, 0u - oldRight);
    run.put(object + right, 0u - oldLeft);
}
void optionalReflect(Run &run, uint32_t object, uint32_t left, uint32_t right) {
    if (run.get(object + left) != 0x80000000)
        reflectPair(run, object, left, right);
}
// 0x48cf90. Whether this actor is the current speech actor.
uint32_t speechActor(Run &run, uint32_t actor) {
    return actor == run.get(0x53c9b0);
}
// 0x4452d0. Enter second death action and compute launch velocity.
uint32_t deadAct2(Run &run, uint32_t object) {
    // +0x10 state controller, +0x12c sprite, +0x134 saved frame.
    run.put(object + 0x24, run.get(run.get(object + 0x10) + 0x1c));
    const uint32_t state = run.call(0x4dba00, 0x537668, {0x527424});
    run.put(run.get(object + 0x10) + 0x1c, state);
    uint32_t sprite = run.get(object + 0x12c);
    run.put(object + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {run.get(object + 0x46c)});
    sprite = run.get(object + 0x12c);
    if (!(run.get8(sprite + 0x40) & 2)) {
        reflectPair(run, object, 0x138, 0x140);
        run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
        sprite = run.get(object + 0x12c);
        optionalReflect(run, sprite, 0x118, 0x120);
        optionalReflect(run, sprite, 0x128, 0x130);
        run.call(0x406180, sprite);
    }
    run.put(run.get(object + 0xc) + 0xcc, 8);
    auto fp = floatingState();
    // Preserve extended intermediates and the original binary64 spills.
    uint64_t local[10]{};
    run.x87_step(CLAW_X87_I32, fp, {run.get(object + 0x52c)});
    run.x87_step(CLAW_X87_I32, fp, {run.get(object + 0x530) - 0x64});
    memory(run, fp, CLAW_X87_F64, object + 0x38);
    memory(run, fp, CLAW_X87_F64, object + 0x40);
    exchange(run, fp, 3);
    memory(run, fp, CLAW_X87_SUB_F64, object + 0x68);
    exchange(run, fp, 2);
    memory(run, fp, CLAW_X87_SUB_F64, object + 0x70);
    memory(run, fp, CLAW_X87_F64, object + 0x78);
    memory(run, fp, CLAW_X87_F64, object + 0x48);
    exchange(run, fp, 4);
    local[2] = store(run, fp, false);
    exchange(run, fp, 2);
    local[3] = store(run, fp, false);
    exchange(run, fp, 1);
    step(run, fp, CLAW_X87_CHS);
    local[4] = store(run, fp, false);
    exchange(run, fp, 3);
    local[5] = store(run, fp, false);
    exchange(run, fp, 5);
    local[6] = store(run, fp, false);
    exchange(run, fp, 4);
    local[7] = store(run, fp, false);
    operand(run, fp, CLAW_X87_F64, local[5]);
    operand(run, fp, CLAW_X87_MUL_F64, local[2]);
    step(run, fp, CLAW_X87_CHS);
    operand(run, fp, CLAW_X87_F64, local[6]);
    operand(run, fp, CLAW_X87_MUL_F64, local[3]);
    step(run, fp, CLAW_X87_ST(CLAW_X87_SUBP, 1));
    operand(run, fp, CLAW_X87_F64, local[7]);
    operand(run, fp, CLAW_X87_MUL_F64, local[4]);
    step(run, fp, CLAW_X87_ST(CLAW_X87_SUBP, 1));
    local[9] = store(run, fp, true);
    exchange(run, fp, 5);
    operand(run, fp, CLAW_X87_MUL_F64, local[5]);
    operand(run, fp, CLAW_X87_F64, local[9]);
    exchange(run, fp, 5);
    operand(run, fp, CLAW_X87_MUL_F64, local[6]);
    step(run, fp, CLAW_X87_ST(CLAW_X87_ADDP, 1));
    exchange(run, fp, 5);
    operand(run, fp, CLAW_X87_MUL_F64, local[7]);
    step(run, fp, CLAW_X87_ST(CLAW_X87_ADDP, 5));
    exchange(run, fp, 1);
    operand(run, fp, CLAW_X87_MUL_F64, local[2]);
    exchange(run, fp, 4);
    local[8] = store(run, fp, true);
    operand(run, fp, CLAW_X87_MUL_F64, local[3]);
    exchange(run, fp, 1);
    operand(run, fp, CLAW_X87_MUL_F64, local[4]);
    exchange(run, fp, 1);
    step(run, fp, CLAW_X87_ST(CLAW_X87_ADDP, 3));
    exchange(run, fp, 1);
    memory(run, fp, CLAW_X87_MUL_F64, 0x50ddf8);
    exchange(run, fp, 1);
    step(run, fp, CLAW_X87_ST(CLAW_X87_ADDP, 2));
    exchange(run, fp, 1);
    operand(run, fp, CLAW_X87_MUL_F64, local[8]);
    memory(run, fp, CLAW_X87_MUL_F64, 0x50ddf0);
    step(run, fp, CLAW_X87_SQRT);
    exchange(run, fp, 1);
    step(run, fp, CLAW_X87_ST(CLAW_X87_SUBP, 1));
    memory(run, fp, CLAW_X87_MUL_F64, 0x50de00);
    step(run, fp, CLAW_X87_SQRT);
    local[1] = store(run, fp, false);
    memory(run, fp, CLAW_X87_COMP_F64, 0x513e20);
    if (fp.status & 0x100) {
        clearVelocity(run, object);
        return 0;
    }
    operand(run, fp, CLAW_X87_F64, local[8]);
    memory(run, fp, CLAW_X87_MUL_F64, 0x50de08);
    memory(run, fp, CLAW_X87_F64, 0x513e20);
    step(run, fp, CLAW_X87_CHS);
    duplicate(run, fp, 1);
    step(run, fp, CLAW_X87_COMPP);
    bool regular = (fp.status & 0x100) != 0;
    if (!regular) {
        memory(run, fp, CLAW_X87_COM_F64, 0x513e20);
        regular = !(fp.status & 0x4100);
    }
    if (!regular) {
        step(run, fp, CLAW_X87_POP);
        operand(run, fp, CLAW_X87_F64, local[2]);
        operand(run, fp, CLAW_X87_F64, local[4]);
        operand(run, fp, CLAW_X87_F64, local[3]);
        exchange(run, fp, 2);
        step(run, fp, CLAW_X87_ABS);
        exchange(run, fp, 1);
        step(run, fp, CLAW_X87_ABS);
        step(run, fp, CLAW_X87_ST(CLAW_X87_ADDP, 1));
        exchange(run, fp, 1);
        step(run, fp, CLAW_X87_ABS);
        operand(run, fp, CLAW_X87_F64, local[2]);
        exchange(run, fp, 1);
        step(run, fp, CLAW_X87_ST(CLAW_X87_ADDP, 2));
        operand(run, fp, CLAW_X87_F64, local[3]);
        operand(run, fp, CLAW_X87_F64, local[4]);
        exchange(run, fp, 2);
        step(run, fp, CLAW_X87_ST(CLAW_X87_DIV_TO0, 3));
        exchange(run, fp, 1);
        step(run, fp, CLAW_X87_ST(CLAW_X87_DIV_TO0, 3));
        exchange(run, fp, 2);
        step(run, fp, CLAW_X87_ST(CLAW_X87_DIV_TO0, 3));
        exchange(run, fp, 1);
        operand(run, fp, CLAW_X87_MUL_F64, local[1]);
        exchange(run, fp, 2);
        operand(run, fp, CLAW_X87_MUL_F64, local[1]);
        exchange(run, fp, 1);
        operand(run, fp, CLAW_X87_MUL_F64, local[1]);
        exchange(run, fp, 2);
        publish(run, fp, object + 0x50);
        publish(run, fp, object + 0x58);
        publish(run, fp, object + 0x60);
        step(run, fp, CLAW_X87_POP);
        return 0;
    }
    operand(run, fp, CLAW_X87_F64, local[1]);
    operand(run, fp, CLAW_X87_MUL_F64, local[1]);
    exchange(run, fp, 1);
    step(run, fp, CLAW_X87_ST(CLAW_X87_ADD_TOI, 0));
    exchange(run, fp, 1);
    operand(run, fp, CLAW_X87_SUB_F64, local[9]);
    exchange(run, fp, 1);
    step(run, fp, CLAW_X87_ST(CLAW_X87_DIVP, 1));
    duplicate(run, fp, 0);
    step(run, fp, CLAW_X87_SQRT);
    duplicate(run, fp, 1);
    duplicate(run, fp, 2);
    exchange(run, fp, 1);
    operand(run, fp, CLAW_X87_MUL_F64, local[5]);
    exchange(run, fp, 2);
    exchange(run, fp, 3);
    exchange(run, fp, 1);
    operand(run, fp, CLAW_X87_MUL_F64, local[6]);
    exchange(run, fp, 1);
    operand(run, fp, CLAW_X87_MUL_F64, local[7]);
    exchange(run, fp, 2);
    memory(run, fp, CLAW_X87_MUL_F64, 0x50de00);
    exchange(run, fp, 1);
    memory(run, fp, CLAW_X87_MUL_F64, 0x50de00);
    exchange(run, fp, 1);
    operand(run, fp, CLAW_X87_SUBR_F64, local[2]);
    exchange(run, fp, 2);
    memory(run, fp, CLAW_X87_MUL_F64, 0x50de00);
    exchange(run, fp, 1);
    operand(run, fp, CLAW_X87_SUBR_F64, local[3]);
    exchange(run, fp, 1);
    operand(run, fp, CLAW_X87_SUBR_F64, local[4]);
    exchange(run, fp, 2);
    step(run, fp, CLAW_X87_ST(CLAW_X87_DIV_TO0, 3));
    exchange(run, fp, 1);
    step(run, fp, CLAW_X87_ST(CLAW_X87_DIV_TO0, 3));
    exchange(run, fp, 2);
    step(run, fp, CLAW_X87_ST(CLAW_X87_DIV_TO0, 3));
    exchange(run, fp, 1);
    publish(run, fp, object + 0x50);
    exchange(run, fp, 1);
    publish(run, fp, object + 0x58);
    publish(run, fp, object + 0x60);
    step(run, fp, CLAW_X87_POP);
    return 0;
}
// 0x445090. First death-action update, dialogue and timed facing changes.
uint32_t deadAct1Update(Run &run, uint32_t object) {
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (!run.get(object + 0x50c) && !speechActor(run, run.get(object + 0xc))) {
        run.call(0x405f60, object, {run.get(object + 0x4d0)});
        run.put(object + 0x50c, 1);
        run.put(object + 0x4e8, 4000);
        run.put(object + 0x4e4, run.get(0x537210));
    }
    uint32_t sprite = run.get(object + 0x12c);
    if (run.get(sprite + 0x16c) == 900 && run.get(0x537210) - run.get(object + 0x4fc) >= run.get(object + 0x500)) {
        run.put(object + 0x500, 100);
        run.put(object + 0x4fc, run.get(0x537210));
        sprite = run.get(object + 0x12c);
        const bool facing = (run.get8(sprite + 0x40) & 2) != 0;
        reflectPair(run, object, 0x138, 0x140);
        run.put(sprite + 0x40, facing ? run.get(sprite + 0x40) & ~2u : run.get(sprite + 0x40) | 2u);
        sprite = run.get(object + 0x12c);
        optionalReflect(run, sprite, 0x118, 0x120);
        optionalReflect(run, sprite, 0x128, 0x130);
        optionalReflect(run, sprite, 0x138, 0x140);
    }
    if (run.get(object + 0x50c) && run.get(0x537210) - run.get(object + 0x4e4) >= run.get(object + 0x4e8) && !run.get(object + 0x510)) {
        run.put(object + 0x510, 1);
        deadAct2(run, object);
    }
    return 0;
}
// 0x445600. Enter the third death action.
uint32_t deadAct3(Run &run, uint32_t object) {
    run.put(object + 0x24, run.get(run.get(object + 0x10) + 0x1c));
    const uint32_t state = run.call(0x4dba00, 0x537668, {0x527418});
    run.put(run.get(object + 0x10) + 0x1c, state);
    const uint32_t sprite = run.get(object + 0x12c);
    run.put(object + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {run.get(object + 0x470)});
    run.put(object + 0x510, 0);
    return 0;
}
// 0x4455b0. Wait for arrival, stop velocity and advance the action.
uint32_t deadAct2Update(Run &run, uint32_t object) {
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (run.get(run.get(object + 0xc) + 0xcc) == 1) {
        clearVelocity(run, object);
        deadAct3(run, object);
    }
    return 0;
}
// 0x4456c0. Enter the fourth death action.
uint32_t deadAct4(Run &run, uint32_t object) {
    run.put(object + 0x24, run.get(run.get(object + 0x10) + 0x1c));
    const uint32_t state = run.call(0x4dba00, 0x537668, {0x52740c});
    run.put(run.get(object + 0x10) + 0x1c, state);
    const uint32_t sprite = run.get(object + 0x12c);
    run.put(object + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {run.get(object + 0x474)});
    run.put(object + 0x50c, 0);
    run.put(object + 0x510, 0);
    return 0;
}
// 0x445660. Advance when the third action's animation completes.
uint32_t deadAct3Update(Run &run, uint32_t object) {
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    const uint32_t animation = run.get(object + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) && !run.get(animation + 0x14) && !run.get(object + 0x510)) {
        run.put(object + 0x510, 1);
        deadAct4(run, object);
    }
    return 0;
}
// 0x445720. Final dialogue followed by defeat publication.
uint32_t deadAct4Update(Run &run, uint32_t object) {
    if (!run.get(object + 0x50c)) {
        if (!speechActor(run, run.get(object + 0xc))) {
            run.call(0x405f60, object, {run.get(object + 0x4d8)});
            run.put(object + 0x50c, 1);
        }
        if (!run.get(object + 0x50c))
            return 0;
    }
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
    const uint32_t animation = run.get(object + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) && !run.get(animation + 0x14) && !run.get(object + 0x510)) {
        run.put(object + 0x510, 1);
        if (s32(run.get(run.get(0x537e88) + 0x10c)) > 0) {
            run.call(0x420590, 0);
            run.call(0x40e5c0, object);
            run.put(object + 0x520, 1);
            const uint32_t count = run.get(object + 0x2fc);
            if (count <= 4) {
                run.call(0x4dbd20, object + 0x2f4, {4});
                return 0;
            }
            if (count > 0x20) {
                const uint32_t words = run.get(object + 0x300);
                run.put(words, run.get(words) | 0x10);
                return 0;
            }
            run.put(object + 0x300, run.get(object + 0x300) | 0x10);
        }
    }
    return 0;
}
// 0x445810. Initialize defeat sequence once and invoke the death virtual.
uint32_t beginDeath(Run &run, uint32_t object) {
    if (run.get(object + 0x520)) {
        run.vcall(object, 0x48);
        return 0;
    }
    run.put(run.get(object + 0xc) + 0x10c, 100);
    const uint32_t actor = run.get(object + 0xc);
    auto fp = floatingState();
    run.x87_step(CLAW_X87_I32, fp, {run.get(actor + 0x10c)});
    const double factor = double(run.getf(0x5262b4));
    uint64_t factorBits;
    std::memcpy(&factorBits, &factor, sizeof(factorBits));
    operand(run, fp, CLAW_X87_MUL_F64, factorBits);
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = fp.eax = fp.edx = 0;
    const uint32_t health = run.call_x87_exact(0x4a30e0, 0, fp);
    run.put(actor + 0x10c, health);
    run.put(run.get(object + 0xc) + 0xcc, 7);
    run.call(0x40e560, object);
    run.vcall(object, 0x24);
    run.put(run.get(object + 0xc) + 0xcc, 8);
    clearVelocity(run, object);
    run.put(object + 0x38, 0);
    run.put(object + 0x3c, 0);
    run.put(object + 0x40, 0);
    run.put(object + 0x44, 0x409f4000);
    uint32_t sprite = run.get(object + 0x12c);
    run.put(sprite + 0x50, run.get(sprite + 0x50) - 0x20);
    const uint32_t companion = run.get(object + 0x128);
    run.call(0x4cd800, run.get(run.get(companion + 0xc) + 0x24), {companion, 0});
    run.put(run.get(object + 0x128) + 0xcc, 1);
    sprite = run.get(object + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) & ~0x80u);
    sprite = run.get(object + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) & ~4u);
    run.put(object + 0x514, 0);
    run.put(object + 0x524, 0);
    fp = floatingState();
    memory(run, fp, CLAW_X87_F64, object + 0x68);
    memory(run, fp, CLAW_X87_SUB_F64, 0x50dde8);
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = fp.eax = fp.edx = 0;
    const uint32_t x = run.call_x87_exact(0x4a30e0, 0, fp);
    const uint32_t method = run.get(run.get(object) + 0x48);
    run.put(object + 0x528, x);
    run.put(object + 0x52c, x - 0x96);
    run.put(object + 0x530, 0x1472);
    run.put(object + 0x518, 0);
    run.put(object + 0x51c, 0);
    run.put(object + 0x520, 0);
    run.put(object + 0x534, 1);
    run.call(method, object);
    return 0;
}
// 0x445950. Normal destructor route; exception registration has no escaped state.
uint32_t destroy(Run &run, uint32_t object) {
    run.put(0x53774c, 0);
    run.put(object, 0x50b16c);
    run.call(0x4dbcd0, object + 0x2f4);
    run.call(0x4f6584, object + 0x1a8);
    run.call(0x4f6584, object + 0x1a4);
    run.put(object, 0x50b014);
    return 0;
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x445090: return deadAct1Update(run, receiver);
    case 0x4452d0: return deadAct2(run, receiver);
    case 0x4455b0: return deadAct2Update(run, receiver);
    case 0x445600: return deadAct3(run, receiver);
    case 0x445660: return deadAct3Update(run, receiver);
    case 0x4456c0: return deadAct4(run, receiver);
    case 0x445720: return deadAct4Update(run, receiver);
    case 0x445810: return beginDeath(run, receiver);
    case 0x445950: return destroy(run, receiver);
    case 0x48cf90: return speechActor(run, arguments[0]);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_level_eight_gabriel_death_entry, owned, body)
