// Level 7 bear sailor closure.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x409920:
    case 0x409ee0:
    case 0x40a040:
        return 1;
    case 0x409f70:
    case 0x40a490:
    case 0x40a610:
    case 0x40a690:
    case 0x40a740:
    case 0x40a7f0:
    case 0x40aa40:
    case 0x40aa70:
    case 0x40ab20:
    case 0x435130:
        return 0;
    default:
        return -1;
    }
}

struct OwnedFrame {
    Run &run;
    uint32_t before;
    OwnedFrame(Run &run, int32_t offset) : run(run), before(run.frame) {
        run.frame += uint32_t(offset);
    }
    ~OwnedFrame() {
        run.frame = before;
    }
};

uint32_t originalAt(Run &run, int32_t offset, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}) {
    const uint32_t before = run.stackPointer;
    run.stackPointer = run.frame + uint32_t(offset);
    try {
        const uint32_t value = run.call(function, receiver, arguments);
        run.stackPointer = before;
        return value;
    } catch (...) {
        run.stackPointer = before;
        throw;
    }
}

ClawX87State fpState() {
    ClawX87State state{};
    state.size = sizeof(state);
    state.version = CLAW_X87_VERSION;
    state.control = 0x023f;
    return state;
}

uint64_t widenFloat(uint32_t bits) {
    const uint64_t sign = uint64_t(bits >> 31) << 63;
    const uint32_t exponent = (bits >> 23) & 0xff;
    uint32_t fraction = bits & 0x7fffff;
    if (exponent == 0xff)
        return sign | 0x7ff0000000000000ull | (uint64_t(fraction) << 29);
    if (exponent)
        return sign | (uint64_t(exponent + 896) << 52) | (uint64_t(fraction) << 29);
    if (!fraction)
        return sign;
    uint32_t shift = 0;
    while (!(fraction & 0x800000)) {
        fraction <<= 1;
        ++shift;
    }
    return sign | (uint64_t(897 - shift) << 52) | (uint64_t(fraction & 0x7fffff) << 29);
}

void load64(Run &run, ClawX87State &state, uint64_t bits) {
    run.x87_step(CLAW_X87_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
}

void multiplyFloat(Run &run, ClawX87State &state, uint32_t address) {
    const uint64_t bits = widenFloat(run.get(address));
    run.x87_step(CLAW_X87_MUL_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
}

uint32_t integerResult(Run &run, ClawX87State &state) {
    state.popCount = 1;
    state.pushCount = 0;
    state.returned = 0;
    state.eax = 0;
    state.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, state);
}

uint32_t resourceManager(Run &run, uint32_t receiver) {
    return run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28);
}

uint32_t function_40a610(Run &run, uint32_t receiver);
uint32_t function_40a740(Run &run, uint32_t receiver);

// 0x409920. Base actor, resources, collision rectangles and difficulty scaling.
uint32_t function_409920(Run &run, uint32_t receiver, uint32_t argument) {
    auto state = fpState();
    state.popCount = 0;
    state.pushCount = 0;
    run.call_x87_exact(0x44c000, receiver, state, {argument});
    run.put(receiver + 0x450, 0);
    run.put(receiver + 0x454, 0);
    run.put(receiver + 0x458, 0);
    run.put(receiver + 0x45c, 0);
    run.put(receiver + 0x460, 0);
    run.put(receiver + 0x464, 0);
    run.put(receiver, 0x50b38c);
    const uint32_t animationNames[] = {0x523a20, 0x523a00, 0x523a00, 0x5239e4, 0x5239cc, 0x5239b4, 0x52399c, 0x523980, 0x523980, 0x523964, 0x523948, 0x52392c, 0x523948, 0x523914, 0x5238fc};
    const uint32_t animationOffsets[] = {0x308, 0x30c, 0x34c, 0x338, 0x334, 0x350, 0x33c, 0x32c, 0x374, 0x378, 0x37c, 0x310, 0x380, 0x36c, 0x344};
    for (uint32_t index = 0; index < 15; ++index) {
        uint32_t value = run.call(0x4062e0, receiver + 0x128, {animationNames[index]});
        if (!value)
            value = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
        run.put(receiver + animationOffsets[index], value);
    }
    const uint32_t local = run.automatic(4);
    const uint32_t names[] = {0x5238e0, 0x5238c4, 0x5238a8, 0x52388c};
    for (uint32_t index = 0; index < 4; ++index) {
        run.put(local, 0);
        run.call(0x4f6286, resourceManager(run, receiver) + 0x10, {names[index], local});
        run.put(receiver + 0x468 + index * 4, run.get(local));
    }
    const uint32_t soundNames[] = {0x523870, 0x523854, 0x523838, 0x52381c, 0x523800, 0x5237e4, 0x5237c8, 0x5237ac};
    const uint32_t soundOffsets[] = {0x478, 0x47c, 0x480, 0x484, 0x488, 0x48c, 0x490, 0x3a4};
    for (uint32_t index = 0; index < 8; ++index) {
        const uint32_t value = run.call(0x4061b0, resourceManager(run, receiver), {soundNames[index]});
        run.put(receiver + soundOffsets[index], value);
    }
    // SetRect's address is loaded once into EBP by the original.
    const uint32_t setRect = run.get(0x546d5c);
    run.call(setRect, 0, {receiver + 0x230, 0xffffff9b, 0xffffffc4, 0xffffffd7, 0xffffffeb});
    run.call(setRect, 0, {receiver + 0x240, 0xffffffbd, 9, 4, 0x30});
    run.put(receiver + 0x220, run.get(receiver + 0x230));
    run.put(receiver + 0x224, run.get(receiver + 0x234));
    run.put(receiver + 0x228, run.get(receiver + 0x238));
    run.put(receiver + 0x22c, run.get(receiver + 0x23c));
    run.call(setRect, 0, {receiver + 0x210, 0xffffffff, 0xffffffff, 1, 1});
    run.call(setRect, 0, {receiver + 0x250, 0xffffffec, 0xffffffc4, 0x14, 0x3d});
    run.call(setRect, 0, {receiver + 0x260, 0xffffffec, 0xfffffff1, 0x14, 0xf});
    run.call(0x40ab80, receiver + 0x128, {0xffffffec, 0xffffffce, 0x14, 0x32});
    run.call(0x40abb0, receiver + 0x128, {receiver + 0x250});
    run.put(receiver + 0x290, 0x28);
    run.put(receiver + 0x2a0, 0x28);
    run.put(receiver + 0x2a8, 0x28);
    run.put(receiver + 0x28c, 0x1f4);
    run.put(receiver + 0x29c, 0x96);
    run.put(receiver + 0x2a4, 0x64);
    run.put(receiver + 0x2ac, 0x32);
    run.put(receiver + 0x2b0, 0xa);
    run.put(receiver + 0x498, 0);
    run.put(receiver + 0x494, 0);
    run.put(receiver + 0x404, 0x12c);
    run.put(receiver + 0x400, 0x78);
    run.put(receiver + 0x2b4, 0xa);
    run.put(receiver + 0x2b8, 0xfffffff6);
    run.put(receiver + 0x2bc, 0xffffffd3);
    run.put(receiver + 0x2c0, 0xffffffec);
    run.put(receiver + 0x2c4, 0x14);
    run.put(receiver + 0x2c8, 0xfffffff1);
    run.put(receiver + 0x2e4, 0x64);
    load64(run, state, widenFloat(run.get(0x5262b8)));
    multiplyFloat(run, state, 0x50b370);
    uint32_t value = integerResult(run, state);
    if (value <= 0x63)
        value = 0x63;
    run.put(receiver + 0x2e4, value);
    run.put(run.get(receiver + 0xc) + 0x10c, 0xa);
    const uint32_t healthObject = run.get(receiver + 0xc);
    run.x87_step(CLAW_X87_I32, state, {run.get(healthObject + 0x10c)});
    multiplyFloat(run, state, 0x5262b4);
    value = integerResult(run, state);
    run.put(healthObject + 0x10c, value);
    run.put(run.get(receiver + 0xc) + 0x104, 0xa);
    const uint32_t damageObject = run.get(receiver + 0xc);
    run.x87_step(CLAW_X87_I32, state, {run.get(damageObject + 0x104)});
    multiplyFloat(run, state, 0x5262b0);
    value = integerResult(run, state);
    run.put(damageObject + 0x104, value);
    run.call(0x40abf0, receiver + 0x128);
    run.call(0x40a440, receiver);
    return receiver;
}

// 0x409f70. Destroy state container and the two reference-counted strings.
uint32_t function_409f70(Run &run, uint32_t receiver) {
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
    return 0;
}

// 0x409ee0. Scalar deleting destructor.
uint32_t function_409ee0(Run &run, uint32_t receiver, uint32_t argument) {
    {
        OwnedFrame child(run, -0x8);
        function_409f70(run, receiver);
    }
    if (argument & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// Integer condition flags carried to original physical callees.
void flagsSZP(ClawSourceContext &cpu, uint32_t value) {
    uint32_t byte = value & 0xff;
    byte ^= byte >> 4;
    byte ^= byte >> 2;
    byte ^= byte >> 1;
    cpu.eflags = (cpu.eflags & ~0xc4u) | (value & 0x80000000 ? 0x80 : 0) | (!value ? 0x40 : 0) | (!(byte & 1) ? 4 : 0);
}

uint32_t sourceSub(ClawSourceContext &cpu, uint32_t left, uint32_t right) {
    const uint32_t result = left - right;
    cpu.eflags = (cpu.eflags & ~0x8d5u) | 2 | (left < right ? 1 : 0) | (((left ^ right ^ result) & 0x10) ? 0x10 : 0) | (((left ^ right) & (left ^ result) & 0x80000000) ? 0x800 : 0);
    flagsSZP(cpu, result);
    return result;
}

uint32_t sourceAdd(ClawSourceContext &cpu, uint32_t left, uint32_t right) {
    const uint32_t result = left + right;
    cpu.eflags = (cpu.eflags & ~0x8d5u) | 2 | (result < left ? 1 : 0) | (((left ^ right ^ result) & 0x10) ? 0x10 : 0) | ((~(left ^ right) & (left ^ result) & 0x80000000) ? 0x800 : 0);
    flagsSZP(cpu, result);
    return result;
}

void sourceTest(ClawSourceContext &cpu, uint32_t value) {
    cpu.eflags = (cpu.eflags & ~0x8d5u) | 2;
    flagsSZP(cpu, value);
}

uint32_t sourceMultiply(ClawSourceContext &cpu, uint32_t left, uint32_t right) {
    const int64_t product = int64_t(s32(left)) * int64_t(s32(right));
    const uint32_t result = uint32_t(product);
    const bool overflow = product != int64_t(s32(result));
    cpu.eflags = (cpu.eflags & ~0x8d5u) | 2 | (overflow ? 0x801 : 0);
    flagsSZP(cpu, result);
    return result;
}

void sourcePush(Run &run, ClawSourceContext &cpu, uint32_t value) {
    cpu.esp -= 4;
    run.put(cpu.esp, value);
}

uint32_t sourcePop(Run &run, ClawSourceContext &cpu) {
    const uint32_t value = run.get(cpu.esp);
    cpu.esp += 4;
    return value;
}

void sourceCall(Run &run, ClawSourceContext &cpu, uint32_t target, uint32_t receiver, uint32_t pc, std::initializer_list<uint32_t> arguments = {}, uint32_t popBytes = 0) {
    sourcePush(run, cpu, pc);
    cpu.eip = target;
    auto child = cpu;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0x472;
    run.source_call(target, receiver, pc, child, arguments, 0, popBytes);
    std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
}

// 0x40a040. The physical dispatch frame retains diagnostic return addresses.
uint32_t function_40a040(Run &run, uint32_t, uint32_t) {
    auto &cpu = run.source();
    sourcePush(run, cpu, cpu.ebp);
    cpu.ebp = cpu.ecx;
    cpu.ecx = run.get(0x534980);
    sourcePush(run, cpu, cpu.esi);
    cpu.esi = run.get(cpu.esp + 0xc);
    sourcePush(run, cpu, cpu.edi);
    sourceSub(cpu, cpu.esi, cpu.ecx);
    run.put(0x534998, 0);
    if (s32(cpu.esi) < s32(cpu.ecx))
        goto growFirst;
    sourceSub(cpu, cpu.esi, run.get(0x534984));
    if (s32(cpu.esi) > run.gets(0x534984))
        goto growFirst;
    cpu.eax = cpu.esi;
    goto rowFirst;
growFirst:
    sourcePush(run, cpu, 0);
    sourcePush(run, cpu, cpu.esi);
    cpu.ecx = 0x534978;
    sourceCall(run, cpu, 0x4db6e0, cpu.ecx, 0x40a076, {cpu.esi, 0}, 8);
    sourceTest(cpu, cpu.eax);
    if (!cpu.eax)
        goto failFirst;
    cpu.ecx = run.get(0x534980);
    cpu.eax = cpu.esi;
rowFirst:
    cpu.eax = sourceSub(cpu, cpu.eax, cpu.ecx);
    cpu.edx = run.get(0x534988);
    cpu.eax = sourceMultiply(cpu, cpu.eax, run.get(0x534990));
    cpu.eax = sourceAdd(cpu, cpu.eax, cpu.edx);
    goto testRow;
failFirst:
    cpu.edi = run.get(0x544b4c);
    sourceCall(run, cpu, 0x4db5f0, 0, 0x40a0a0);
    cpu.ecx = run.get(0x53497c);
    sourcePush(run, cpu, 0xc);
    sourcePush(run, cpu, cpu.edi);
    sourcePush(run, cpu, 0x534978);
    run.put(0x544b14, cpu.eax);
    sourceCall(run, cpu, 0x4db4d0, cpu.ecx, 0x40a0b8, {0x534978, cpu.edi, 0xc}, 12);
    cpu.eax = run.get(0x53498c);
    cpu.ecx = run.get(0x534980);
testRow:
    sourceSub(cpu, run.get(cpu.eax), 0);
    if (!run.get(cpu.eax))
        goto baseDispatch;
    sourceSub(cpu, cpu.esi, cpu.ecx);
    run.put(0x534998, 0);
    if (s32(cpu.esi) < s32(cpu.ecx))
        goto growSecond;
    sourceSub(cpu, cpu.esi, run.get(0x534984));
    if (s32(cpu.esi) <= run.gets(0x534984))
        goto rowSecond;
growSecond:
    sourcePush(run, cpu, 0);
    sourcePush(run, cpu, cpu.esi);
    cpu.ecx = 0x534978;
    sourceCall(run, cpu, 0x4db6e0, cpu.ecx, 0x40a0eb, {cpu.esi, 0}, 8);
    sourceTest(cpu, cpu.eax);
    if (!cpu.eax)
        goto failSecond;
    cpu.ecx = run.get(0x534980);
rowSecond:
    cpu.esi = sourceSub(cpu, cpu.esi, cpu.ecx);
    cpu.eax = run.get(0x534988);
    cpu.esi = sourceMultiply(cpu, cpu.esi, run.get(0x534990));
    cpu.esi = sourceAdd(cpu, cpu.esi, cpu.eax);
    cpu.ecx = cpu.ebp;
    sourceCall(run, cpu, run.get(cpu.esi), cpu.ecx, 0x40a109);
    goto epilogue;
failSecond:
    cpu.esi = run.get(0x544b4c);
    sourceCall(run, cpu, 0x4db5f0, 0, 0x40a11a);
    cpu.ecx = run.get(0x53497c);
    sourcePush(run, cpu, 0xc);
    sourcePush(run, cpu, cpu.esi);
    sourcePush(run, cpu, 0x534978);
    run.put(0x544b14, cpu.eax);
    sourceCall(run, cpu, 0x4db4d0, cpu.ecx, 0x40a132, {0x534978, cpu.esi, 0xc}, 12);
    cpu.esi = run.get(0x53498c);
    cpu.ecx = cpu.ebp;
    sourceCall(run, cpu, run.get(cpu.esi), cpu.ecx, 0x40a13c);
    goto epilogue;
baseDispatch:
    sourcePush(run, cpu, cpu.esi);
    cpu.ecx = cpu.ebp;
    sourceCall(run, cpu, 0x44c840, cpu.ecx, 0x40a14a, {cpu.esi}, 4);
epilogue:
    cpu.edi = sourcePop(run, cpu);
    cpu.esi = sourcePop(run, cpu);
    cpu.ebp = sourcePop(run, cpu);
    return cpu.eax;
}

// 0x40a610. Begin the grab animation and lock player control.
uint32_t function_40a610(Run &run, uint32_t receiver) {
    uint32_t sound = run.get(receiver + 0x490);
    if (sound && run.get(0x532c0c))
        run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    const uint32_t state = run.call(0x4dba00, 0x537668, {0x523a50});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    const uint32_t actor = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c79e0, actor, {0x523a74, 0});
    run.call(0x41fce0, 0);
    return 0;
}

// 0x40a490. Idle/home: notice player, orient, and begin an eligible grab.
uint32_t function_40a490(Run &run, uint32_t receiver) {
    if (!run.get(receiver + 0x498)) {
        bool notice = false;
        if (run.get(0x534eac) != 0x26b7) {
            const uint32_t player = run.get(0x537e88);
            const uint32_t actor = run.get(receiver + 0x194);
            const uint32_t world = run.get(run.get(run.get(receiver + 0x190) + 0xc) + 0x24);
            if (run.call(0x4cda10, world, {run.get(actor + 0x4c), run.get(actor + 0x50), run.get(player + 0x4c), 0x20})) {
                const uint32_t currentActor = run.get(receiver + 0x194);
                const uint32_t y = run.get(currentActor + 0x50);
                const uint32_t playerY = run.get(run.get(0x537e88) + 0x50);
                notice = s32(playerY) < s32(y + 0x32) && s32(playerY) > s32(y - 0x32) && run.get(currentActor + 0x38) != 0xffffffff;
            }
        }
        if (notice) {
            if (s32(run.call(0x4a3050, 0)) % 100 < 0x46) {
                const int32_t index = s32(run.call(0x4a3050, 0)) % 2;
                const uint32_t sound = run.get(receiver + 0x468 + uint32_t(index) * 4);
                run.call(0x48ce40, 0, {run.get(receiver + 0xc), sound, 0});
            }
            run.put(receiver + 0x498, 1);
        }
    }
    if (run.get(receiver + 0x18c) == 2) {
        const uint32_t actor = run.get(receiver + 0x12c);
        if (!(run.get8(actor + 0x40) & 2)) {
            const uint32_t left = run.get(receiver + 0x138);
            const uint32_t right = run.get(receiver + 0x140);
            run.put(receiver + 0x138, 0 - right);
            run.put(receiver + 0x140, 0 - left);
            run.put(actor + 0x40, run.get(actor + 0x40) | 2);
            const uint32_t changed = run.get(receiver + 0x12c);
            run.call(0x406120, changed);
            run.call(0x406150, changed);
            run.call(0x406180, changed);
        }
    } else {
        run.call(0x406310, receiver + 0x128);
    }
    run.call(0x4a3050, 0);
    if (run.get(receiver + 0x184) == 4 && run.get(0x537210) - run.get(receiver + 0x458) >= run.get(receiver + 0x45c) && run.gets(run.get(0x537e88) + 0x10c) > 0) {
        OwnedFrame child(run, -0xc);
        function_40a610(run, receiver);
    }
    run.call(0x44da20, receiver);
    return 0;
}

// 0x40a740. Enter hug state and start its repeating sound.
uint32_t function_40a740(Run &run, uint32_t receiver) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    const uint32_t state = run.call(0x4dba00, 0x537668, {0x523a48});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    run.put(receiver + 0x18, 0x40aa40);
    run.put(receiver + 0x1c, run.get(run.get(receiver + 0x10) + 0x1c));
    const uint32_t actor = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c79e0, actor, {0x523a90, 0});
    run.put(receiver + 0x454, 0xbb8);
    run.put(receiver + 0x450, run.get(0x537210));
    const uint32_t sound = run.get(receiver + 0x48c);
    if (sound && !originalAt(run, -0x8, 0x4b3e70, run.get(sound + 0x10))) {
        if (run.get(0x532c0c))
            run.call(0x4b3dc0, run.get(run.get(receiver + 0x48c) + 0x10), {0x64, 0, 0, 1});
    }
    run.put(receiver + 0x494, 0);
    return 0;
}

// 0x40a690. On grab animation completion, position the player and start hugging.
uint32_t function_40a690(Run &run, uint32_t receiver) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    const uint32_t animation = run.get(receiver + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) && !run.get(animation + 0x14)) {
        const uint32_t facing = run.get(receiver + 0x18c);
        auto state = fpState();
        load64(run, state, uint64_t(run.get(receiver + 0x68)) | (uint64_t(run.get(receiver + 0x6c)) << 32));
        const uint32_t player = run.get(0x537e88);
        const uint32_t constant = facing == 3 ? 0x50b378 : 0x50b380;
        run.x87_step(CLAW_X87_SUB_F64, state, {run.get(constant), run.get(constant + 4)});
        const uint32_t x = integerResult(run, state);
        run.put(player + 0x4c, x);
        const uint32_t currentPlayer = run.get(0x537e88);
        const uint32_t logic = run.get(currentPlayer + 0x6c);
        run.call(facing == 3 ? 0x418120 : 0x418080, 0, {currentPlayer, logic, run.get(logic + 0x14)});
        load64(run, state, uint64_t(run.get(receiver + 0x70)) | (uint64_t(run.get(receiver + 0x74)) << 32));
        const uint32_t yPlayer = run.get(0x537e88);
        const uint32_t y = integerResult(run, state);
        run.put(yPlayer + 0x50, y);
        {
            OwnedFrame child(run, -0xc);
            function_40a740(run, receiver);
        }
    }
    return 0;
}

void stopHugSound(Run &run, uint32_t receiver, int32_t callOffset) {
    const uint32_t sound = run.get(receiver + 0x48c);
    if (sound && originalAt(run, callOffset, 0x4b3e70, run.get(sound + 0x10)))
        run.call(0x4b3e30, run.get(run.get(receiver + 0x48c) + 0x10));
}

// 0x40a7f0. Damage during a hug, map paired frames, or release the player.
uint32_t function_40a7f0(Run &run, uint32_t receiver) {
    if (run.get(run.get(0x537204) + 4) & 0x0f000fff)
        run.put(receiver + 0x494, run.get(receiver + 0x494) + 1);
    const uint32_t player = run.get(0x537e88);
    if (run.get(run.get(player + 0x6c) + 0x1c) == 0x1390 && run.get(0x537210) - run.get(receiver + 0x450) < run.get(receiver + 0x454) && run.gets(receiver + 0x494) < 0xa) {
        if (run.get(0x537210) - run.get(receiver + 0x460) >= run.get(receiver + 0x464)) {
            uint32_t currentPlayer = player;
            if (run.get(0x534eac) != 0x26bd) {
                run.put(currentPlayer + 0x10c, run.get(currentPlayer + 0x10c) - 1);
                currentPlayer = run.get(0x537e88);
            }
            if (run.gets(currentPlayer + 0x10c) <= 0) {
                stopHugSound(run, receiver, -0xc);
                run.call(0x41fe80, 0);
                currentPlayer = run.get(0x537e88);
                const uint32_t logic = run.get(currentPlayer + 0x6c);
                run.call(0x417b00, 0, {currentPlayer, logic, run.get(logic + 0x14), 1});
                run.vcall(receiver, 0x44);
            }
            run.put(receiver + 0x464, 0x64);
            run.put(receiver + 0x460, run.get(0x537210));
        }
        run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
        const uint32_t frame = run.get(run.get(receiver + 0x12c) + 0x16c);
        if (frame >= 0x12e && frame <= 0x130) {
            const uint32_t currentPlayer = run.get(0x537e88);
            const uint32_t animation = run.get(currentPlayer + 0x170);
            if (animation) {
                const uint32_t target = frame - 0x12e + 0x1c2;
                uint32_t result = 0;
                if (run.gets(animation + 0x64) <= s32(target) && run.gets(animation + 0x68) >= s32(target))
                    result = run.get(run.get(animation + 0x14) + 0x708 + (frame - 0x12e) * 4);
                run.put(currentPlayer + 0x174, result);
                run.put(currentPlayer + 0x16c, target);
            }
        }
    } else {
        stopHugSound(run, receiver, -0xc);
        run.call(0x41fe80, 0);
        run.vcall(receiver, 0x44);
        run.put(receiver + 0x45c, 0x32);
        run.put(receiver + 0x458, run.get(0x537210));
    }
    return 0;
}

// 0x40aa40. Hug exit action.
uint32_t function_40aa40(Run &run, uint32_t receiver) {
    stopHugSound(run, receiver, -0x8);
    run.call(0x41fe80, 0);
    return 0;
}

// 0x40aa70. Release animation and restore player control.
uint32_t function_40aa70(Run &run, uint32_t receiver) {
    if (run.get(run.get(run.get(0x537e88) + 0x6c) + 0x1c) != 0x1390) {
        run.vcall(receiver, 0x44);
        run.call(0x41fe80, 0);
        return 0;
    }
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    const uint32_t animation = run.get(receiver + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) && !run.get(animation + 0x14))
        run.vcall(receiver, 0x44);
    run.call(0x41fe80, 0);
    run.put(receiver + 0x45c, 0x3e8);
    run.put(receiver + 0x458, run.get(0x537210));
    return 0;
}

// 0x40ab20. Select one of the two hit reactions then apply it.
uint32_t function_40ab20(Run &run, uint32_t receiver) {
    run.call(0x48cf50, 0, {run.get(receiver + 0xc)});
    const uint32_t random = run.call(0x4a3050, 0);
    const uint32_t sound = run.get(receiver + (s32(random) % 100 < 0x23 ? 0x484 : 0x480));
    run.call(0x48ce40, 0, {run.get(receiver + 0xc), sound, 0});
    run.call(0x440420, receiver);
    return 0;
}

// 0x435130. Bear idle delegates to the common enemy idle behavior.
uint32_t function_435130(Run &run, uint32_t receiver) {
    run.call(0x44f290, receiver);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x409920:
        return function_409920(run, receiver, arguments[0]);
    case 0x409ee0:
        return function_409ee0(run, receiver, arguments[0]);
    case 0x409f70:
        return function_409f70(run, receiver);
    case 0x40a040:
        return function_40a040(run, receiver, arguments[0]);
    case 0x40a490:
        return function_40a490(run, receiver);
    case 0x40a610:
        return function_40a610(run, receiver);
    case 0x40a690:
        return function_40a690(run, receiver);
    case 0x40a740:
        return function_40a740(run, receiver);
    case 0x40a7f0:
        return function_40a7f0(run, receiver);
    case 0x40aa40:
        return function_40aa40(run, receiver);
    case 0x40aa70:
        return function_40aa70(run, receiver);
    case 0x40ab20:
        return function_40ab20(run, receiver);
    case 0x435130:
        return function_435130(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

ClawSourceContract contract(uint32_t function) {
    if (function == 0x40a040)
        return {0x7ff, 0x5f3, 0x472, 4};
    return {};
}

CLAW_SOURCE_MODULE_ENTRY(claw_level_seven_bear_sailor_01_entry, owned, contract, body)
