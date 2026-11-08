#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;
using CPU = ClawSourceContext;
int owned(uint32_t f) {
    switch (f) {
    case 0x403ad0: return 2;
    case 0x4dbb10: return 4;
    case 0x4dbb90: return 4;
    case 0x4db620: return 1;
    default: return -1;
    }
}
uint32_t common(uint32_t v) {
    uint32_t p = v & 255;
    p ^= p >> 4;
    p ^= p >> 2;
    p ^= p >> 1;
    return 2u | (v == 0 ? 0x40u : 0u) | (v & 0x80000000u ? 0x80u : 0u) | (!(p & 1) ? 4u : 0u);
}
void test(CPU &c, uint32_t v) {
    c.eflags = common(v);
}
uint32_t sub(CPU &c, uint32_t a, uint32_t b) {
    uint32_t v = a - b;
    c.eflags = common(v) | (a < b ? 1u : 0u) | ((a ^ b ^ v) & 16u) | (((a ^ b) & (a ^ v) & 0x80000000u) ? 0x800u : 0u);
    return v;
}
uint32_t add(CPU &c, uint32_t a, uint32_t b) {
    uint32_t v = a + b;
    c.eflags = common(v) | (v < a ? 1u : 0u) | ((a ^ b ^ v) & 16u) | ((~(a ^ b) & (a ^ v) & 0x80000000u) ? 0x800u : 0u);
    return v;
}
uint32_t inc(CPU &c, uint32_t a) {
    uint32_t carry = c.eflags & 1;
    uint32_t v = add(c, a, 1);
    c.eflags = (c.eflags & ~1u) | carry;
    return v;
}
void push(Run &run, CPU &c, uint32_t v) {
    c.esp -= 4;
    run.put(c.esp, v);
}
uint32_t pop(Run &run, CPU &c) {
    uint32_t v = run.get(c.esp);
    c.esp += 4;
    return v;
}
void execute(Run &, CPU &, uint32_t);
void child(Run &run, CPU &c, uint32_t f, uint32_t pc, std::initializer_list<uint32_t> args) {
    push(run, c, pc);
    c.eip = f;
    if (owned(f) >= 0) {
        execute(run, c, f);
        c.eip = pop(run, c);
        c.esp += uint32_t(args.size()) * 4;
    } else {
        CPU out = c;
        run.source_call(f, f == 0x4db4d0 ? c.ecx : 0, pc, out, args, 0, uint32_t(args.size()) * 4);
        c = out;
    }
}
uint32_t mallocCall(Run &run, CPU &c, uint32_t pc, uint32_t bytes) {
    push(run, c, bytes);
    push(run, c, pc);
    c.eip = 0x4a48e0;
    CPU out = c;
    run.source_call(0x4a48e0, 0, pc, out, {bytes});
    c = out;
    return c.eax;
}
// 0x4db620. Base fields: +4 error manager, +0 vtable.
void base(Run &run, CPU &c) {
    c.eax = c.ecx;
    c.ecx = run.get(c.esp + 0x4);
    test(c, c.ecx);
    if (!c.ecx) c.ecx = 0x544b18;
    run.put(c.eax + 0x4, c.ecx);
    run.put(c.eax, 0x513e28);
    c.ecx = run.get(0x544b4c);
    test(c, c.ecx);
    if (!c.ecx) {
        run.put(0x544b4c, 0x533418);
        run.put(0x544b30, 0x5333fc);
        run.put(0x544b34, 0x5333f0);
        run.put(0x544b48, 0x5333d0);
        run.put(0x544b38, 0x5333c0);
        run.put(0x544b40, 0x5333a8);
        run.put(0x544b3c, 0x533390);
        run.put(0x544b44, 0x53337c);
    }
}
// 0x4dbb90. Range fields: +8 lower, +12 upper, +16 data, +20 auxiliary, +24 element size.
void storage(Run &run, CPU &c) {
    push(run, c, 0xffffffff);
    push(run, c, 0x50a038);
    c.eax = c.fsHead;
    push(run, c, c.eax);
    c.fsHead = c.esp;
    push(run, c, c.ecx);
    push(run, c, c.ebx);
    push(run, c, c.esi);
    push(run, c, c.edi);
    c.esi = c.ecx;
    push(run, c, 0x544b50);
    run.put(c.esp + 0x10, c.esi);
    child(run, c, 0x4db620, 0x4dbbb9, {0x544b50});
    c.edx = run.get(c.esp + 0x2c);
    c.ecx = run.get(c.esp + 0x24);
    c.eax = run.get(c.esp + 0x28);
    run.put(c.esi + 0x14, c.edx);
    c.edx = run.get(c.esp + 0x20);
    sub(c, c.ecx, c.eax);
    run.put(c.esp + 0x18, 0);
    run.put(c.esi + 0x8, c.ecx);
    run.put(c.esi + 0xc, c.eax);
    run.put(c.esi + 0x10, 0);
    run.put(c.esi + 0x18, c.edx);
    run.put(c.esi, 0x513e30);
    uint32_t error = 0;
    uint32_t message = 0;
    if (s32(c.ecx) > s32(c.eax)) {
        child(run, c, 0x4dc680, 0x4dbbf3, {});
        error = 22;
        message = 0x533458;
    } else {
        c.eax = sub(c, c.eax, c.ecx);
        c.eax = inc(c, c.eax);
        int64_t product = int64_t(s32(c.eax)) * int64_t(s32(c.edx));
        c.eax = uint32_t(product);
        c.eflags = common(c.eax) | ((product != int64_t(s32(c.eax))) ? 0x801u : 0u);
        c.ebx = c.eax;
        mallocCall(run, c, 0x4dbc0f, c.ebx);
        c.edi = c.eax;
        c.esp = add(c, c.esp, 4);
        test(c, c.edi);
        run.put(c.esi + 0x10, c.edi);
        bool firstFailed = !c.edi;
        if (c.edi) {
            c.ecx = c.ebx;
            c.eax = 0;
            test(c, 0);
            c.edx = c.ecx;
            uint32_t before = c.ecx;
            c.ecx >>= 2;
            c.eflags = common(c.ecx) | ((before >> 1) & 1u);
            while (c.ecx) {
                run.put(c.edi, c.eax);
                c.edi += 4;
                --c.ecx;
            }
            c.ecx = c.edx;
            c.ecx &= 3;
            test(c, c.ecx);
            while (c.ecx) {
                run.put8(c.edi, uint8_t(c.eax));
                ++c.edi;
                --c.ecx;
            }
            c.eax = run.get(c.esi + 0x14);
            test(c, c.eax);
            if (!c.eax) {
                c.eax = run.get(c.esi + 0x18);
                mallocCall(run, c, 0x4dbc3d, c.eax);
                c.esp = add(c, c.esp, 4);
                run.put(c.esi + 0x14, c.eax);
                test(c, c.eax);
            }
        }
        if (firstFailed || !c.eax) {
            child(run, c, 0x4dc680, 0x4dbc4c, {});
            error = 12;
            message = 0x533428;
        }
    }
    if (error) {
        push(run, c, error);
        run.put(0x544b14, c.eax);
        push(run, c, message);
        c.ecx = run.get(c.esi + 0x4);
        push(run, c, c.esi);
        child(run, c, 0x4db4d0, 0x4dbc61, {c.esi, message, error});
    }
    c.ecx = run.get(c.esp + 0x10);
    c.eax = c.esi;
    c.edi = pop(run, c);
    c.esi = pop(run, c);
    c.fsHead = c.ecx;
    c.ebx = pop(run, c);
    c.esp = add(c, c.esp, 16);
}
// 0x4dbb10. Array fields: +28 data, +32 element count.
void array(Run &run, CPU &c) {
    c.eax = run.get(c.esp + 0x10);
    c.edx = run.get(c.esp + 0x8);
    push(run, c, c.esi);
    c.esi = c.ecx;
    c.ecx = run.get(c.esp + 0x10);
    push(run, c, c.eax);
    c.eax = run.get(c.esp + 0xc);
    push(run, c, c.ecx);
    push(run, c, c.edx);
    push(run, c, c.eax);
    c.ecx = c.esi;
    child(run, c, 0x4dbb90, 0x4dbb2e, {run.get(c.esp), run.get(c.esp + 0x4), run.get(c.esp + 0x8), run.get(c.esp + 0xc)});
    c.ecx = run.get(c.esi + 0x10);
    c.edx = run.get(c.esi + 0xc);
    run.put(c.esi + 0x1c, c.ecx);
    c.ecx = run.get(c.esi + 0x8);
    c.edx = sub(c, c.edx, c.ecx);
    run.put(c.esi, 0x513e2c);
    c.edx = inc(c, c.edx);
    c.eax = c.esi;
    run.put(c.esi + 0x20, c.edx);
    c.esi = pop(run, c);
}
// 0x403ad0.
void outer(Run &run, CPU &c) {
    c.eax = run.get(c.esp + 0x8);
    push(run, c, c.esi);
    c.esi = c.ecx;
    push(run, c, 1);
    c.ecx = run.get(c.esp + 0xc);
    push(run, c, c.eax);
    push(run, c, c.ecx);
    push(run, c, 4);
    c.ecx = c.esi;
    child(run, c, 0x4dbb10, 0x403ae8, {4, run.get(c.esp + 0x4), run.get(c.esp + 0x8), 1});
    c.edx = run.get(c.esi + 0x1c);
    run.put(c.esi, 0x50b0ac);
    c.eax = c.esi;
    run.put(c.esp + 0xc, c.edx);
    c.esi = pop(run, c);
}
void execute(Run &run, CPU &c, uint32_t f) {
    switch (f) {
    case 0x403ad0:
        outer(run, c);
        break;
    case 0x4dbb10:
        array(run, c);
        break;
    case 0x4dbb90:
        storage(run, c);
        break;
    case 0x4db620:
        base(run, c);
        break;
    default: run.fail(CLAW_FAULT_ABI, f);
    }
}
uint32_t body(Run &run, uint32_t f, uint32_t, const uint32_t *) {
    auto &c = run.source();
    execute(run, c, f);
    return c.eax;
}
}
static ClawSourceContract source_contract(uint32_t f) {
    return owned(f) < 0 ? ClawSourceContract{} : ClawSourceContract{2047u, 2047u, 1138u, uint32_t(owned(f)) * 4};
}
CLAW_SOURCE_MODULE_ENTRY(claw_static_range_constructors_entry, owned, source_contract, body)
