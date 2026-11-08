#include "ClawRuntime.hpp"

namespace {
using claw::Run;

struct Registration {
    uint32_t entry;
    uint32_t callback;
    bool popECX;
};

constexpr Registration registrations[] = {
    {0x403570, 0x403580, false},
    {0x4042e0, 0x4042f0, false},
    {0x4064f0, 0x406500, false},
    {0x406ec0, 0x406ed0, false},
    {0x4074d0, 0x4074e0, false},
    {0x408550, 0x408560, false},
    {0x409180, 0x409190, false},
    {0x40a010, 0x40a020, false},
    {0x40b840, 0x40b850, false},
    {0x40e250, 0x40e260, false},
    {0x40ebb0, 0x40ebc0, false},
    {0x40fb00, 0x40fb10, false},
    {0x410a50, 0x410a60, false},
    {0x411000, 0x411010, false},
    {0x4114b0, 0x4114c0, false},
    {0x411960, 0x411970, false},
    {0x411e40, 0x411e50, false},
    {0x412430, 0x412440, false},
    {0x4129a0, 0x4129b0, false},
    {0x412e50, 0x412e60, false},
    {0x413630, 0x413640, false},
    {0x413b50, 0x413b60, false},
    {0x4141c0, 0x4141d0, false},
    {0x414db0, 0x414dc0, false},
    {0x415440, 0x415450, false},
    {0x415cc0, 0x415cd0, false},
    {0x4212f0, 0x421300, false},
    {0x425200, 0x425210, false},
    {0x425280, 0x425290, false},
    {0x4252c0, 0x4252d0, false},
    {0x425300, 0x425310, false},
    {0x425340, 0x425350, false},
    {0x425380, 0x425390, false},
    {0x4253c0, 0x4253d0, false},
    {0x425400, 0x425410, false},
    {0x425440, 0x425450, false},
    {0x425480, 0x425490, false},
    {0x431410, 0x431420, false},
    {0x431dc0, 0x431dd0, false},
    {0x432660, 0x432670, false},
    {0x433aa0, 0x433ab0, false},
    {0x434920, 0x434930, false},
    {0x4368b0, 0x4368c0, false},
    {0x4368f0, 0x436900, false},
    {0x436930, 0x436940, false},
    {0x437520, 0x437530, false},
    {0x437570, 0x437580, false},
    {0x4380d0, 0x4380e0, false},
    {0x43acf0, 0x43ad00, false},
    {0x43cd90, 0x43cda0, false},
    {0x43d350, 0x43d360, false},
    {0x43d410, 0x43d420, false},
    {0x43d460, 0x43d470, false},
    {0x4412a0, 0x4412b0, false},
    {0x441cd0, 0x441ce0, false},
    {0x443380, 0x443390, false},
    {0x445ac0, 0x445ad0, false},
    {0x446640, 0x446650, false},
    {0x448820, 0x448830, false},
    {0x448e00, 0x448e10, false},
    {0x449560, 0x449570, false},
    {0x449d30, 0x449d40, false},
    {0x44c810, 0x44c820, false},
    {0x4543b0, 0x4543c0, false},
    {0x4555d0, 0x4555e0, false},
    {0x455ad0, 0x455ae0, false},
    {0x4562b0, 0x4562c0, false},
    {0x456bf0, 0x456c00, false},
    {0x457710, 0x457720, false},
    {0x458250, 0x458260, false},
    {0x458770, 0x458780, false},
    {0x45a3d0, 0x45a3e0, false},
    {0x4606e0, 0x4606f0, false},
    {0x462ac0, 0x462ad0, false},
    {0x463b10, 0x463b20, false},
    {0x465170, 0x465180, false},
    {0x465d80, 0x465d90, false},
    {0x468aa0, 0x468ab0, false},
    {0x46f670, 0x46f680, false},
    {0x473f10, 0x473f20, false},
    {0x4747b0, 0x4747c0, false},
    {0x474ef0, 0x474f00, false},
    {0x474f40, 0x474f50, false},
    {0x474f80, 0x474f90, false},
    {0x47cd40, 0x47cd50, false},
    {0x47daf0, 0x47db00, false},
    {0x47e8b0, 0x47e8c0, false},
    {0x47f7d0, 0x47f7e0, false},
    {0x483150, 0x483160, false},
    {0x4843a0, 0x4843b0, false},
    {0x4848a0, 0x4848b0, false},
    {0x485930, 0x485940, false},
    {0x487370, 0x487380, false},
    {0x4889b0, 0x4889c0, false},
    {0x4890c0, 0x4890d0, false},
    {0x489820, 0x489830, false},
    {0x48b090, 0x48b0a0, false},
    {0x48d1f0, 0x48d200, false},
    {0x48e590, 0x48e5a0, false},
    {0x4923b0, 0x4923c0, false},
    {0x493fa0, 0x493fb0, false},
    {0x497100, 0x497110, false},
    {0x498190, 0x4981a0, false},
    {0x49f190, 0x49f1a0, false},
    {0x49f870, 0x49f880, false},
    {0x49f8b0, 0x49f8c0, false},
    {0x4a0200, 0x4a0210, false},
    {0x4b9130, 0x4b9140, false},
    {0x4bc0f0, 0x4bc100, false},
    {0x4f824a, 0x4f8256, true},
    {0x4f8288, 0x4f8294, true},
    {0x4f82c6, 0x4f82d2, true},
    {0x4f8304, 0x4f8310, true},
    {0x4ff95c, 0x4ff968, true},
    {0x501fc8, 0x501fd4, true},
    {0x502279, 0x502285, true},
    {0x502442, 0x50244e, true},
    {0x50247a, 0x502486, true},
    {0x502881, 0x50288d, true},
    {0x502c5c, 0x502c68, true},
    {0x502ca4, 0x502cb0, true},
    {0x502ce2, 0x502cee, true},
    {0x502d1a, 0x502d26, true},
    {0x502d44, 0x502d50, true},
    {0x50372d, 0x503739, true},
    {0x503753, 0x50375f, true},
};

const Registration *registration(uint32_t function) {
    for (const auto &item : registrations) {
        if (item.entry == function)
            return &item;
    }
    return nullptr;
}

int owned(uint32_t function) {
    return registration(function) ? 0 : -1;
}

ClawSourceContract contract(uint32_t) {
    return {0x7ff, 0x7ff, 0x472, 0};
}

uint32_t addFlags(uint32_t flags, uint32_t left, uint32_t right, uint32_t result) {
    uint32_t arithmetic = result < left ? 0x01u : 0u;
    uint32_t low = result & 0xff;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    if (!(low & 1))
        arithmetic |= 0x04;
    if ((left ^ right ^ result) & 0x10)
        arithmetic |= 0x10;
    if (!result)
        arithmetic |= 0x40;
    if (result & 0x80000000)
        arithmetic |= 0x80;
    if ((~(left ^ right) & (left ^ result)) & 0x80000000)
        arithmetic |= 0x800;
    return (flags & ~0x8d5u) | arithmetic;
}

// Each entry performs PUSH callback, CALL original atexit, then its own cleanup.
uint32_t body(Run &run, uint32_t function, uint32_t, const uint32_t *) {
    const Registration *item = registration(function);
    if (!item)
        run.fail(CLAW_FAULT_ABI, function);
    auto &cpu = run.source();
    cpu.esp -= 0x04;
    run.put(cpu.esp, item->callback);
    cpu.eip = function + 0x05;
    ClawSourceContext child = cpu;
    child.esp -= 0x04;
    child.eip = 0x4a35f0;
    const uint32_t returnPC = function + 0x0a;
    run.put(child.esp, returnPC);
    run.source_call(0x4a35f0, 0, returnPC, child, {item->callback});
    cpu = child;
    if (item->popECX) {
        cpu.ecx = run.get(cpu.esp);
        cpu.esp += 0x04;
        cpu.eip = returnPC + 0x01;
    } else {
        const uint32_t previousESP = cpu.esp;
        cpu.esp += 0x04;
        cpu.eflags = addFlags(cpu.eflags, previousESP, 0x04, cpu.esp);
        cpu.eip = returnPC + 0x03;
    }
    return cpu.eax;
}

} // namespace

CLAW_SOURCE_MODULE_ENTRY(claw_static_exit_registrations_entry, owned, contract, body)
