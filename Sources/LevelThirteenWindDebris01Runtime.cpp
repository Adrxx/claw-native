// Level 13 wind debris, recovered from the original v1.0 instructions.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x49f0a0: return 1;
    case 0x49f1c0: return 1;
    case 0x49f470: return 1;
    case 0x49f770: return 0;
    case 0x49f7e0: return 0;
    default: return -1;
    }
}
ClawSourceContract contract(uint32_t function) {
    if (function == 0x49f1c0)
        return {0x7ff, 0x5f3, 0x472, 4};
    return {};
}

uint32_t function_49f470(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x49f0a0. Owner +0x6c points at dispatch state: +0x18 object, +0x1c state.
uint32_t function_49f0a0(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t owner = arguments[0];
    uint32_t state = run.get(owner + 0x6c);
    uint32_t value = run.get(state + 0x1c);
    if (value == 0) {
        run.put(state + 0x1c, 0x3e8);
        uint32_t object = run.call(0x4f63ec, 0, {0x1b0});
        if (object)
            object = function_49f470(run, object, &owner);
        run.vcall(object, 0x10);
        run.put(state + 0x18, object);
    } else if (value == 0x1d) {
        run.vcall(run.get(state + 0x18), 0x20);
    } else if (value == 0x1e) {
        run.vcall(run.get(state + 0x18), 0x1c);
    } else if (value != 0x3e8) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
    }
    return 1;
}

void flags(Run &run, uint32_t left, uint32_t right, uint32_t result, bool subtract) {
    auto &cpu = run.source();
    uint32_t f = 2;
    uint32_t parity = result & 0xff;
    parity ^= parity >> 4;
    parity &= 0xf;
    if ((0x9669u >> parity) & 1u)
        f |= 4;
    if (!result)
        f |= 0x40;
    if (result & 0x80000000u)
        f |= 0x80;
    if ((left ^ right ^ result) & 0x10)
        f |= 0x10;
    if (subtract ? left < right : result < left)
        f |= 1;
    if ((subtract ? ((left ^ right) & (left ^ result)) : (~(left ^ right) & (left ^ result))) & 0x80000000u)
        f |= 0x800;
    cpu.eflags = f;
}
void push(Run &run, uint32_t value) {
    auto &cpu = run.source();
    cpu.esp -= 4;
    run.put(cpu.esp, value);
}
uint32_t pop(Run &run) {
    auto &cpu = run.source();
    uint32_t value = run.get(cpu.esp);
    cpu.esp += 4;
    return value;
}
uint32_t sourceCall(Run &run, uint32_t function, uint32_t receiver, uint32_t returnPC,
                    std::initializer_list<uint32_t> arguments = {}, uint32_t popBytes = 0) {
    auto &cpu = run.source();
    push(run, returnPC);
    auto child = cpu;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0x472;
    child.eip = function;
    run.source_call(function, receiver, returnPC, child, arguments, 0, popBytes);
    std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
    return cpu.eax;
}

// 0x49f1c0. Physical source frames retain both table-error caller addresses.
uint32_t function_49f1c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    auto &cpu = run.source();
    push(run, cpu.ebp);
    cpu.ebp = receiver;
    cpu.ecx = run.get(0x53ec08);
    push(run, cpu.esi);
    cpu.esi = arguments[0];
    push(run, cpu.edi);
    flags(run, cpu.esi, cpu.ecx, cpu.esi - cpu.ecx, true);
    run.put(0x53ec20, 0);
    bool firstInRange = s32(cpu.esi) >= s32(cpu.ecx);
    if (firstInRange) {
        uint32_t high = run.get(0x53ec0c);
        flags(run, cpu.esi, high, cpu.esi - high, true);
        firstInRange = s32(cpu.esi) <= s32(high);
    }
    if (!firstInRange) {
        push(run, 0);
        push(run, cpu.esi);
        cpu.ecx = 0x53ec00;
        sourceCall(run, 0x4db6e0, cpu.ecx, 0x49f1f6, {cpu.esi, 0}, 8);
        flags(run, cpu.eax, 0, cpu.eax, false);
        if (cpu.eax)
            cpu.ecx = run.get(0x53ec08);
    }
    if (firstInRange || cpu.eax) {
        cpu.eax = cpu.esi - cpu.ecx;
        cpu.edx = run.get(0x53ec10);
        cpu.eax *= run.get(0x53ec18);
        uint32_t previous = cpu.eax;
        cpu.eax += cpu.edx;
        flags(run, previous, cpu.edx, cpu.eax, false);
    } else {
        cpu.edi = run.get(0x544b4c);
        sourceCall(run, 0x4db5f0, 0, 0x49f220);
        cpu.ecx = run.get(0x53ec04);
        push(run, 0xc);
        push(run, cpu.edi);
        push(run, 0x53ec00);
        run.put(0x544b14, cpu.eax);
        sourceCall(run, 0x4db4d0, cpu.ecx, 0x49f238, {0x53ec00, cpu.edi, 0xc}, 12);
        cpu.eax = run.get(0x53ec14);
        cpu.ecx = run.get(0x53ec08);
    }
    uint32_t callback = run.get(cpu.eax);
    flags(run, callback, 0, callback, true);
    if (callback) {
        flags(run, cpu.esi, cpu.ecx, cpu.esi - cpu.ecx, true);
        run.put(0x53ec20, 0);
        bool secondInRange = s32(cpu.esi) >= s32(cpu.ecx);
        if (secondInRange) {
            uint32_t high = run.get(0x53ec0c);
            flags(run, cpu.esi, high, cpu.esi - high, true);
            secondInRange = s32(cpu.esi) <= s32(high);
        }
        if (!secondInRange) {
            push(run, 0);
            push(run, cpu.esi);
            cpu.ecx = 0x53ec00;
            sourceCall(run, 0x4db6e0, cpu.ecx, 0x49f26b, {cpu.esi, 0}, 8);
            flags(run, cpu.eax, 0, cpu.eax, false);
            if (cpu.eax)
                cpu.ecx = run.get(0x53ec08);
        }
        if (secondInRange || cpu.eax) {
            cpu.esi -= cpu.ecx;
            cpu.eax = run.get(0x53ec10);
            cpu.esi *= run.get(0x53ec18);
            uint32_t previous = cpu.esi;
            cpu.esi += cpu.eax;
            flags(run, previous, cpu.eax, cpu.esi, false);
            cpu.ecx = cpu.ebp;
            sourceCall(run, run.get(cpu.esi), cpu.ecx, 0x49f289);
        } else {
            cpu.esi = run.get(0x544b4c);
            sourceCall(run, 0x4db5f0, 0, 0x49f29a);
            cpu.ecx = run.get(0x53ec04);
            push(run, 0xc);
            push(run, cpu.esi);
            push(run, 0x53ec00);
            run.put(0x544b14, cpu.eax);
            sourceCall(run, 0x4db4d0, cpu.ecx, 0x49f2b2, {0x53ec00, cpu.esi, 0xc}, 12);
            cpu.esi = run.get(0x53ec14);
            cpu.ecx = cpu.ebp;
            sourceCall(run, run.get(cpu.esi), cpu.ecx, 0x49f2bc);
        }
    } else {
        push(run, cpu.ebp);
        sourceCall(run, 0x4a36f0, 0, 0x49f2c8, {cpu.ebp});
        uint32_t previous = cpu.esp;
        cpu.esp += 4;
        flags(run, previous, 4, cpu.esp, false);
    }
    cpu.edi = pop(run);
    cpu.esi = pop(run);
    cpu.ebp = pop(run);
    return cpu.eax;
}

// 0x49f770. Sprite +0x190 is the saved cycle; owner +0x10 holds state.
uint32_t function_49f770(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c79e0, sprite, {0x52417c, 0});
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x52ddbc});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    run.put(run.get(receiver + 0xc) + 0xcc, 7);
    run.put(receiver + 0x1a8, 0x2710);
    run.put(receiver + 0x1a4, run.get(0x537210));
    return 0;
}

uint64_t doubleBits(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

// 0x49f470. Receiver is 0x1b0 bytes; +0x28 motion, +0x128 sprite owner.
uint32_t function_49f470(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t owner = arguments[0];
    run.call(0x4082f0, receiver, {owner});
    run.call(0x4080a0, receiver + 0x28);
    run.put(receiver, 0x50b2a4);
    uint32_t source = run.get(run.get(receiver + 0x10) + 0x2c);
    if (!source) {
        run.put(receiver + 0x80, run.get(0x513e10));
        run.put(receiver + 0x84, run.get(0x513e14));
    } else {
        run.putd(receiver + 0x80, double(s32(source)));
    }
    source = run.get(run.get(receiver + 0x10) + 0x34);
    if (!source) {
        run.put(receiver + 0x88, run.get(0x513e10));
        run.put(receiver + 0x8c, run.get(0x513e14));
    } else {
        run.putd(receiver + 0x88, double(s32(source)));
    }
    source = run.get(run.get(receiver + 0x10) + 0x30);
    if (!source) {
        run.put(receiver + 0x98, run.get(0x513e18));
        run.put(receiver + 0x9c, run.get(0x513e1c));
    } else {
        run.putd(receiver + 0x98, double(s32(source)));
    }
    source = run.get(run.get(receiver + 0x10) + 0x38);
    if (!source) {
        run.put(receiver + 0xa0, run.get(0x513e18));
        run.put(receiver + 0xa4, run.get(0x513e1c));
    } else {
        run.putd(receiver + 0xa0, double(s32(source)));
    }
    uint32_t data = run.get(receiver + 0xc);
    uint64_t x = doubleBits(double(run.gets(data + 0x4c)));
    uint64_t y = doubleBits(double(run.gets(data + 0x50)));
    uint64_t vx = doubleBits(double(run.gets(data + 0x148)));
    uint64_t vy = doubleBits(double(run.gets(data + 0x14c)));
    uint64_t time = doubleBits(double(run.get(0x537210)) * run.getd(0x50ff18));
    run.call(0x408220, receiver + 0x28, {uint32_t(x), uint32_t(x >> 32), uint32_t(y), uint32_t(y >> 32), 0, 0,
        uint32_t(vx), uint32_t(vx >> 32), uint32_t(vy), uint32_t(vy >> 32), 0, 0, 0, 0, 0, 0, 0, 0,
        uint32_t(time), uint32_t(time >> 32), 0, 0});
    double drag = double(run.get(0x513e40));
    run.putd(receiver + 0xe8, drag);
    run.putd(receiver + 0xf0, drag);
    run.putd(receiver + 0xf8, drag);
    run.put(receiver + 0x120, 0);
    run.put(receiver + 0x124, 0);
    run.put(run.get(receiver + 0xc) + 0xcc, 7);
    run.call(0x4dca10, receiver);
    run.call(0x408370, receiver + 0x128, {owner});
    run.put(receiver + 0x190, owner);
    run.put(receiver + 0x194, owner);
    run.put(receiver + 0x198, run.get(owner + 0x6c));
    run.put(receiver + 0x1a4, 0);
    run.put(receiver + 0x1a8, 0);
    run.put(receiver, 0x50feec);
    uint32_t random = run.call(0x4a3050, 0);
    int32_t remainder = s32(random) % 3;
    uint32_t name = remainder == 0 ? 0x52dde4 : remainder == 1 ? 0x52ddf4 : 0x52de04;
    run.call(0x4c7970, run.get(receiver + 0x12c), {name});
    run.put(receiver + 0x19c, 0);
    run.put(receiver + 0x1a0, 0);
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x164, run.get(sprite + 0x164) | 0x2000);
    sprite = run.get(receiver + 0x12c);
    run.put(sprite + 0x8, run.get(sprite + 0x8) | 3);
    sprite = run.get(receiver + 0x12c);
    uint32_t image = run.get(sprite + 0x174);
    if (image) {
        run.put(sprite + 0x118, run.get(image + 0x20) - run.get(image + 0x18));
        run.put(sprite + 0x11c, run.get(image + 0x24) - run.get(image + 0x1c));
        run.put(sprite + 0x120, run.get(image + 0x20) + run.get(image + 0x18) - 1);
        run.put(sprite + 0x124, run.get(image + 0x1c) + run.get(image + 0x24) - 1);
    }
    sprite = run.get(receiver + 0x12c);
    image = run.get(sprite + 0x174);
    if (image) {
        run.put(sprite + 0x128, run.get(image + 0x20) - run.get(image + 0x18));
        run.put(sprite + 0x12c, run.get(image + 0x24) - run.get(image + 0x1c));
        run.put(sprite + 0x130, run.get(image + 0x20) + run.get(image + 0x18) - 1);
        run.put(sprite + 0x134, run.get(image + 0x24) + run.get(image + 0x1c) - 1);
    }
    function_49f770(run, receiver, nullptr);
    return receiver;
}

// 0x49f7e0. Motion +0x68 is height; +0x1a0 threshold and +0x1a4/+0x1a8 timer.
uint32_t function_49f7e0(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (double(run.gets(receiver + 0x1a0)) > run.getd(receiver + 0x68)) {
        run.put(receiver + 0xc8, 1);
        uint32_t sprite = run.get(receiver + 0x12c);
        run.put(sprite + 0x8, run.get(sprite + 0x8) | 0x10000);
    }
    uint32_t elapsed = run.get(0x537210) - run.get(receiver + 0x1a4);
    if (elapsed >= run.get(receiver + 0x1a8)) {
        uint32_t sprite = run.get(receiver + 0x12c);
        run.put(sprite + 0x8, run.get(sprite + 0x8) | 0x10000);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x49f0a0: return function_49f0a0(run, receiver, arguments);
    case 0x49f1c0: return function_49f1c0(run, receiver, arguments);
    case 0x49f470: return function_49f470(run, receiver, arguments);
    case 0x49f770: return function_49f770(run, receiver, arguments);
    case 0x49f7e0: return function_49f7e0(run, receiver, arguments);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_SOURCE_MODULE_ENTRY(claw_level_thirteen_wind_debris_01_entry, owned, contract, body)
