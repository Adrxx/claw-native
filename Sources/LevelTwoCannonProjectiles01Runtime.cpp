// Level 2 cannon projectiles
//
// Recovered from the original v1.0 instruction packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x414030:
        return 1;
    case 0x4141f0:
        return 1;
    case 0x414b20:
        return 1;
    case 0x414be0:
        return 1;
    case 0x495ec0:
        return 1;
    case 0x495f90:
        return 1;
    default:
        return -1;
    }
}

// 0x414030. thiscall, 1 stack argument(s), returns u32.
uint32_t function_414030(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    // +0x00 vtable, +0x08/+0x0c object, +0x10 object state, +0x04 flags.
    run.put(receiver, 0x50b064);
    run.put(receiver + 0x08, object);
    run.put(receiver + 0x0c, object);
    run.put(receiver + 0x10, run.get(object + 0x6c));
    run.put(receiver + 0x04, 0);
    run.call(0x4c7fa0, object, {0x522d54});
    run.call(0x4c8060, run.get(receiver + 0x0c), {0x522d48});
    // +0x14/+0x18 activity, +0x1c state, +0x20 mode, +0x28/+0x2c object.
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0x3e9);
    run.put(receiver + 0x20, 2);
    run.put(receiver + 0x28, object);
    run.put(receiver + 0x2c, object);
    run.put(receiver + 0x30, run.get(object + 0x6c));
    run.put(receiver + 0x74, 0);
    run.put(receiver + 0x78, 0);
    run.put(receiver, 0x50b9dc);
    uint32_t owner = run.get(receiver + 0x0c);
    if (!run.get(owner + 0x148)) {
        run.put(owner + 0x148, 0x1f4);
    }
    owner = run.get(receiver + 0x0c);
    if (!run.get(owner + 0x14c)) {
        run.put(owner + 0x14c, 0);
    }
    owner = run.get(receiver + 0x0c);
    if (!run.get(owner + 0x104)) {
        run.put(owner + 0x104, 0x0a);
    }
    owner = run.get(receiver + 0x0c);
    if (!run.get(owner + 0x64)) {
        run.put(owner + 0x64, 0xf96);
        run.put(owner + 0x08, run.get(owner + 0x08) | 0x20000);
    }
    // +0x48/+0x4c animations; +0x50/+0x70/+0x54 counters.
    run.put(receiver + 0x48, 0);
    run.put(receiver + 0x4c, 0);
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x70, 0);
    run.put(receiver + 0x54, 0);
    if (run.get8(run.get(receiver + 0x2c) + 0x40) & 2) {
        run.call(0x414a60, receiver);
    }
    // +0x5c/+0x60/+0x64/+0x68 projectile bounds.
    run.put(receiver + 0x5c, 0x32);
    run.put(receiver + 0x60, 0x0a);
    run.put(receiver + 0x64, 0xffffffe6);
    run.put(receiver + 0x68, 0xfffffff6);
    owner = run.get(receiver + 0x2c);
    run.put(owner + 0x08, run.get(owner + 0x08) | 1);
    owner = run.get(receiver + 0x2c);
    run.put(owner + 0x08, run.get(owner + 0x08) | 0x40);
    return receiver;
}

// Arithmetic flags for the recovered 32-bit CMP/TEST/ADD/SUB instructions.
uint32_t flags32(uint32_t left, uint32_t right, uint32_t value, bool subtract, bool logical = false) {
    uint32_t flags = 2;
    if (!value) {
        flags |= 0x40;
    }
    flags |= value & 0x80000000u ? 0x80 : 0;
    uint32_t parity = value & 0xff;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    if (!(parity & 1)) {
        flags |= 4;
    }
    if (!logical) {
        flags |= (left ^ right ^ value) & 0x10;
        bool carry = subtract ? left < right : value < left;
        bool overflow = subtract ? ((left ^ right) & (left ^ value) & 0x80000000u) != 0 : ((~(left ^ right)) & (left ^ value) & 0x80000000u) != 0;
        flags |= carry ? 1 : 0;
        flags |= overflow ? 0x800 : 0;
    }
    return flags;
}

void sourcePush(Run &run, uint32_t value) {
    auto &cpu = run.source();
    cpu.esp -= 4;
    run.put(cpu.esp, value);
}

void sourceCall(Run &run, uint32_t function, uint32_t receiver, uint32_t returnPC, std::initializer_list<uint32_t> arguments = {}, uint32_t popBytes = 0) {
    auto &cpu = run.source();
    sourcePush(run, returnPC);
    auto child = cpu;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0x472;
    child.eip = function;
    run.source_call(function, receiver, returnPC, child, arguments, 0, popBytes);
    std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
}

// 0x4141f0. Dispatches a cannon event through the global logic table.
uint32_t function_4141f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &cpu = run.source();
    sourcePush(run, cpu.ebp);
    cpu.ebp = cpu.ecx;
    cpu.ecx = run.get(0x534c00);
    sourcePush(run, cpu.esi);
    cpu.esi = run.get(cpu.esp + 0x0c);
    sourcePush(run, cpu.edi);
    cpu.eflags = flags32(cpu.esi, cpu.ecx, cpu.esi - cpu.ecx, true);
    run.put(0x534c18, 0);
    bool outside = s32(cpu.esi) < s32(cpu.ecx);
    if (!outside) {
        uint32_t upper = run.get(0x534c04);
        cpu.eflags = flags32(cpu.esi, upper, cpu.esi - upper, true);
        outside = s32(cpu.esi) > s32(upper);
    }
    bool found = !outside;
    if (outside) {
        sourcePush(run, 0);
        sourcePush(run, cpu.esi);
        cpu.ecx = 0x534bf8;
        sourceCall(run, 0x4db6e0, cpu.ecx, 0x414226, {cpu.esi, 0}, 8);
        cpu.eflags = flags32(cpu.eax, cpu.eax, cpu.eax, false, true);
        found = cpu.eax != 0;
        if (found) {
            cpu.ecx = run.get(0x534c00);
        }
    }
    if (found) {
        cpu.eax = cpu.esi;
        uint32_t previous = cpu.eax;
        cpu.eax -= cpu.ecx;
        cpu.eflags = flags32(previous, cpu.ecx, cpu.eax, true);
        cpu.edx = run.get(0x534c08);
        cpu.eax *= run.get(0x534c10);
        previous = cpu.eax;
        cpu.eax += cpu.edx;
        cpu.eflags = flags32(previous, cpu.edx, cpu.eax, false);
    } else {
        cpu.edi = run.get(0x544b4c);
        sourceCall(run, 0x4db5f0, 0, 0x414250);
        cpu.ecx = run.get(0x534bfc);
        sourcePush(run, 0x0c);
        sourcePush(run, cpu.edi);
        sourcePush(run, 0x534bf8);
        run.put(0x544b14, cpu.eax);
        sourceCall(run, 0x4db4d0, cpu.ecx, 0x414268, {0x534bf8, cpu.edi, 0x0c}, 0x0c);
        cpu.eax = run.get(0x534c0c);
        cpu.ecx = run.get(0x534c00);
    }
    uint32_t method = run.get(cpu.eax);
    cpu.eflags = flags32(method, 0, method, true);
    if (!method) {
        sourcePush(run, cpu.ebp);
        sourceCall(run, 0x4a36f0, 0, 0x4142f8, {cpu.ebp});
        uint32_t previous = cpu.esp;
        cpu.esp += 4;
        cpu.eflags = flags32(previous, 4, cpu.esp, false);
    } else {
        cpu.eflags = flags32(cpu.esi, cpu.ecx, cpu.esi - cpu.ecx, true);
        run.put(0x534c18, 0);
        outside = s32(cpu.esi) < s32(cpu.ecx);
        if (!outside) {
            uint32_t upper = run.get(0x534c04);
            cpu.eflags = flags32(cpu.esi, upper, cpu.esi - upper, true);
            outside = s32(cpu.esi) > s32(upper);
        }
        found = !outside;
        if (outside) {
            sourcePush(run, 0);
            sourcePush(run, cpu.esi);
            cpu.ecx = 0x534bf8;
            sourceCall(run, 0x4db6e0, cpu.ecx, 0x41429b, {cpu.esi, 0}, 8);
            cpu.eflags = flags32(cpu.eax, cpu.eax, cpu.eax, false, true);
            found = cpu.eax != 0;
            if (found) {
                cpu.ecx = run.get(0x534c00);
            }
        }
        if (found) {
            uint32_t previous = cpu.esi;
            cpu.esi -= cpu.ecx;
            cpu.eflags = flags32(previous, cpu.ecx, cpu.esi, true);
            cpu.eax = run.get(0x534c08);
            cpu.esi *= run.get(0x534c10);
            previous = cpu.esi;
            cpu.esi += cpu.eax;
            cpu.eflags = flags32(previous, cpu.eax, cpu.esi, false);
            cpu.ecx = cpu.ebp;
            sourceCall(run, run.get(cpu.esi), cpu.ecx, 0x4142b9);
        } else {
            cpu.esi = run.get(0x544b4c);
            sourceCall(run, 0x4db5f0, 0, 0x4142ca);
            cpu.ecx = run.get(0x534bfc);
            sourcePush(run, 0x0c);
            sourcePush(run, cpu.esi);
            sourcePush(run, 0x534bf8);
            run.put(0x544b14, cpu.eax);
            sourceCall(run, 0x4db4d0, cpu.ecx, 0x4142e2, {0x534bf8, cpu.esi, 0x0c}, 0x0c);
            cpu.esi = run.get(0x534c0c);
            cpu.ecx = cpu.ebp;
            sourceCall(run, run.get(cpu.esi), cpu.ecx, 0x4142ec);
        }
    }
    cpu.edi = run.get(cpu.esp);
    cpu.esp += 4;
    cpu.esi = run.get(cpu.esp);
    cpu.esp += 4;
    cpu.ebp = run.get(cpu.esp);
    cpu.esp += 4;
    return cpu.eax;
}

uint32_t function_414be0(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x414b20. cdecl, 1 stack argument(s), returns u32.
uint32_t function_414b20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t state = run.get(object + 0x6c);
    uint32_t command = run.get(state + 0x1c);
    if (!command) {
        run.put(state + 0x1c, 0x3e8);
        uint32_t allocation = run.call(0x4f63ec, 0, {0x150});
        uint32_t projectile = 0;
        if (allocation) {
            uint32_t entry = run.frame;
            run.frame -= 0x1c;
            projectile = function_414be0(run, allocation, &object);
            run.frame = entry;
        }
        run.vcall(projectile, 0x10);
        run.put(state + 0x18, projectile);
    } else if (command == 0x1d) {
        run.vcall(run.get(state + 0x18), 0x20);
    } else if (command == 0x1e) {
        run.vcall(run.get(state + 0x18), 0x1c);
    } else if (command != 0x3e8) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}

// 0x414be0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_414be0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    run.call(0x473c50, receiver, {object});
    run.put(receiver, 0x50ba04);
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x44, 0);
    // +0x170 selects a preexisting image set; +0x12c is the sprite owner.
    if (!run.get(object + 0x170)) {
        run.call(0x4c7970, run.get(receiver + 0x12c), {0x52458c});
    }
    uint32_t local = run.automatic(0x04);
    uint32_t sprite = run.get(receiver + 0x12c);
    uint32_t image = run.get(sprite + 0x0c);
    run.put(local, 0);
    run.call(0x4f6286, run.get(image + 0x2c) + 0x10, {0x524574, local});
    run.put(receiver + 0x148, run.get(local));
    run.put(run.get(receiver + 0x12c) + 0xd0, 0x40);
    run.put(run.get(receiver + 0x12c) + 0xd4, 2);
    uint32_t owner = run.get(receiver + 0x0c);
    if (!run.get(owner + 0x104)) {
        run.put(owner + 0x104, 0x0a);
    }
    run.call(0x474290, receiver);
    return receiver;
}

// 0x495ec0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_495ec0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_414030(run, receiver, arguments);
    run.put(receiver, 0x50fa64);
    run.call(0x4c7970, run.get(receiver + 0x2c), {0x52ce44});
    uint32_t local = run.automatic(0x04);
    run.put(local, 0);
    uint32_t owner = run.get(receiver + 0x0c);
    run.put(owner + 0x148, 0u - run.get(owner + 0x148));
    run.put(receiver + 0x5c, 0u - run.get(0x50b9c4));
    uint32_t sprite = run.get(receiver + 0x2c);
    uint32_t image = run.get(sprite + 0x0c);
    run.call(0x4f6286, run.get(image + 0x2c) + 0x10, {0x52ce24, local});
    run.put(receiver + 0x4c, run.get(local));
    sprite = run.get(receiver + 0x2c);
    image = run.get(sprite + 0x0c);
    run.put(local, 0);
    run.call(0x4f6286, run.get(image + 0x2c) + 0x10, {0x52ce08, local});
    run.put(receiver + 0x48, run.get(local));
    run.call(0x4145b0, receiver);
    return receiver;
}

// 0x495f90. thiscall, 1 stack argument(s), returns u32.
uint32_t function_495f90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_414030(run, receiver, arguments);
    run.put(receiver, 0x50fa8c);
    run.call(0x4c7970, run.get(receiver + 0x2c), {0x52cebc});
    uint32_t local = run.automatic(0x04);
    run.put(local, 0);
    uint32_t sprite = run.get(receiver + 0x2c);
    uint32_t image = run.get(sprite + 0x0c);
    run.call(0x4f6286, run.get(image + 0x2c) + 0x10, {0x52ce9c, local});
    run.put(receiver + 0x4c, run.get(local));
    sprite = run.get(receiver + 0x2c);
    image = run.get(sprite + 0x0c);
    run.put(local, 0);
    run.call(0x4f6286, run.get(image + 0x2c) + 0x10, {0x52ce80, local});
    run.put(receiver + 0x48, run.get(local));
    run.call(0x4145b0, receiver);
    return receiver;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x414030:
        return function_414030(run, receiver, arguments);
    case 0x4141f0:
        return function_4141f0(run, receiver, arguments);
    case 0x414b20:
        return function_414b20(run, receiver, arguments);
    case 0x414be0:
        return function_414be0(run, receiver, arguments);
    case 0x495ec0:
        return function_495ec0(run, receiver, arguments);
    case 0x495f90:
        return function_495f90(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

ClawSourceContract contract(uint32_t function) {
    if (function == 0x4141f0) {
        return {0x7ff, 0x5f3, 0x472, 4};
    }
    return {};
}

} // namespace

CLAW_SOURCE_MODULE_ENTRY(claw_level_two_cannon_projectiles_01_entry, owned, contract, body)
