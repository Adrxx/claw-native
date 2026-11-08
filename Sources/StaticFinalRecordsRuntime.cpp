// Final static platform and core records
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x502dac:
        return 0;
    case 0x4fb3ba:
        return 0;
    case 0x4fb376:
        return 0;
    case 0x502d5a:
        return 0;
    case 0x502d8a:
        return 0;
    case 0x4ffce9:
        return 0;
    case 0x4ffd0c:
        return 0;
    case 0x4db610:
        return 0;
    case 0x4dbb80:
        return 0;
    case 0x4dc170:
        return 0;
    case 0x4dc270:
        return 0;
    case 0x4dc390:
        return 0;
    case 0x4dc3a0:
        return 1;
    case 0x503818:
        return 0;
    default:
        return -1;
    }
}


void push(Run &run, uint32_t value) {
    auto &c = run.source();
    c.esp -= 4;
    run.put(c.esp, value);
}
uint32_t pop(Run &run) {
    auto &c = run.source();
    uint32_t value = run.get(c.esp);
    c.esp += 4;
    return value;
}
void flags(Run &run, uint32_t value, unsigned bits, bool cf, bool of, bool af) {
    uint32_t mask = bits == 32 ? 0xffffffffu : ((1u << bits) - 1);
    value &= mask;
    uint32_t low = value & 0xff;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    run.source().eflags = 2 | uint32_t(cf) | ((!(low & 1)) ? 4 : 0) | (af ? 0x10 : 0) | (!value ? 0x40 : 0) | ((value & (1u << (bits - 1))) ? 0x80 : 0) | (of ? 0x800 : 0);
}
uint32_t sub(Run &run, uint32_t a, uint32_t b, unsigned bits = 32) {
    uint32_t mask = bits == 32 ? 0xffffffffu : ((1u << bits) - 1);
    a &= mask;
    b &= mask;
    uint32_t r = (a - b) & mask;
    flags(run, r, bits, a < b, ((a ^ b) & (a ^ r) & (1u << (bits - 1))) != 0, ((a ^ b ^ r) & 0x10) != 0);
    return r;
}
uint32_t inc(Run &run, uint32_t a) {
    bool cf = run.source().eflags & 1;
    uint32_t r = a + 1;
    flags(run, r, 32, cf, a == 0x7fffffff, ((a ^ 1 ^ r) & 0x10) != 0);
    return r;
}
void logic(Run &run, uint32_t value, unsigned bits = 32) {
    flags(run, value, bits, false, false, false);
}
void external(Run &run, uint32_t target, uint32_t pc, std::initializer_list<uint32_t> args = {}) {
    auto &c = run.source();
    push(run, pc);
    auto child = c;
    child.eip = target;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    try {
        run.source_call(target, 0, pc, child, args, 0, uint32_t(args.size()) * 4);
    } catch (...) {
        std::memcpy(&c.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&c.eax, &child.eax, 11 * sizeof(uint32_t));
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);
void internal(Run &run, uint32_t target, uint32_t pc, uint32_t popBytes = 0) {
    auto &c = run.source();
    push(run, pc);
    body(run, target, c.ecx, nullptr);
    c.eip = pop(run);
    c.esp += popBytes;
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &c = run.source();
    switch (function) {
    case 0x4dc390:
        break;
    case 0x4dc3a0:
        c.eax = c.ecx;
        c.ecx = 2;
        run.put(c.eax + 0x0c, c.ecx);
        run.put(c.eax + 0x10, c.ecx);
        c.ecx = run.get(c.esp + 0x04);
        run.put(c.eax + 0x00, 0x4dc420);
        run.put16(c.eax + 0x08, 0);
        run.put(c.eax + 0x14, c.ecx);
        break;
    case 0x4db610:
    case 0x4dbb80:
    case 0x4dc170:
    case 0x4dc270: {
        uint32_t label = function == 0x4db610 ? 0x53336c : function == 0x4dbb80 ? 0x533448 : function == 0x4dc170 ? 0x533474 : 0x533480;
        push(run, label);
        c.ecx = function == 0x4db610 ? 0x544b18 : function == 0x4dbb80 ? 0x544b50 : function == 0x4dc170 ? 0x544b68 : 0x544b80;
        internal(run, 0x4dc3a0, function + 0x0f, 4);
        break;
    }
    case 0x503818: {
        push(run, 0x5345a0);
        c.ecx = 0x544e80;
        push(run, 0x503827);
        auto child = c;
        child.eip = 0x4f709b;
        try {
            run.source_call(0x4f709b, c.ecx, 0x503827, child, {0x5345a0}, 0, 4);
        } catch (...) {
            std::memcpy(&c.eax, &child.eax, 11 * sizeof(uint32_t));
            throw;
        }
        std::memcpy(&c.eax, &child.eax, 11 * sizeof(uint32_t));
        break;
    }
    case 0x4ffce9:
        run.put(0x540b50, 0);
        logic(run, 0);
        run.put(0x540b54, 0);
        logic(run, 0);
        c.eax = 0x80000000;
        run.put(0x540b48, c.eax);
        run.put(0x540b4c, c.eax);
        break;
    case 0x502d5a:
    case 0x502d8a: {
        bool modern = function == 0x502d5a;
        if (modern) {
            sub(run, run.get(0x5408d4), 0);
            if (c.eflags & 0x40) break;
        }
        push(run, c.esi);
        c.esi = run.get(0x546c44);
        push(run, 2);
        external(run, 0x546c44, modern ? 0x502d6e : 0x502d95, {2});
        if (modern) c.eax = inc(run, c.eax);
        push(run, 3);
        run.put(0x540878, c.eax);
        external(run, 0x546c44, modern ? 0x502d78 : 0x502d9e, {3});
        if (modern) c.eax = inc(run, c.eax);
        run.put(0x5408e0, modern ? 1 : 0);
        if (!modern) logic(run, 0);
        run.put(0x54087c, c.eax);
        c.esi = pop(run);
        break;
    }
    case 0x4fb376: {
        push(run, c.esi);
        push(run, c.edi);
        c.edi = run.get(0x546d20);
        c.esi = c.ecx;
        const uint32_t selectors[] = {15,16,20,18,6,15,6};
        const uint32_t pcs[] = {0x4fb384,0x4fb38b,0x4fb392,0x4fb399,0x4fb3a0,0x4fb3ad,0x4fb3b4};
        const uint32_t offsets[] = {0x28,0x2c,0x30,0x34,0x38,0x24,0x20};
        push(run, selectors[0]);
        for (unsigned i = 0; i < 7; ++i) {
            external(run, i < 5 ? 0x546d20 : 0x546b64, pcs[i], {selectors[i]});
            if (i == 4) c.edi = run.get(0x546b64);
            if (i < 6) push(run, selectors[i + 1]);
            run.put(c.esi + offsets[i], c.eax);
        }
        c.edi = pop(run);
        c.esi = pop(run);
        break;
    }
    case 0x4fb3ba:
        push(run, c.ebx);
        push(run, c.esi);
        push(run, c.edi);
        c.edi = run.get(0x546c44);
        c.esi = c.ecx;
        push(run, 11);
        external(run, 0x546c44, 0x4fb3c9, {11});
        push(run, 12);
        run.put(c.esi + 0x08, c.eax);
        external(run, 0x546c44, 0x4fb3d0, {12});
        sub(run, run.get(c.esi + 0x68), 0);
        run.put(c.esi + 0x0c, c.eax);
        if (c.eflags & 0x40) internal(run, 0x502d8a, 0x4fb3e5);
        else internal(run, 0x502d5a, 0x4fb3de);
        push(run, 0);
        external(run, 0x546c7c, 0x4fb3ed, {0});
        c.ebx = run.get(0x546894);
        c.edi = c.eax;
        push(run, 88);
        push(run, c.edi);
        external(run, 0x546894, 0x4fb3fa, {c.edi,88});
        push(run, 90);
        push(run, c.edi);
        run.put(c.esi + 0x18, c.eax);
        external(run, 0x546894, 0x4fb402, {c.edi,90});
        push(run, c.edi);
        push(run, 0);
        run.put(c.esi + 0x1c, c.eax);
        external(run, 0x546c80, 0x4fb40e, {0,c.edi});
        c.edi = pop(run);
        c.esi = pop(run);
        c.ebx = pop(run);
        break;
    case 0x4ffd0c: {
        push(run, c.esi);
        c.esi = run.get(0x546abc);
        push(run, c.edi);
        external(run, 0x546abc, 0x4ffd16);
        c.edi = 0x80000000;
        logic(run, c.edi & c.eax);
        bool named = false;
        auto equalVersion = [&](uint32_t expected) {
            uint32_t ax = sub(run, c.eax, expected, 16);
            c.eax = (c.eax & 0xffff0000) | ax;
            uint32_t neg = sub(run, 0, ax, 16);
            c.eax = (c.eax & 0xffff0000) | neg;
            bool carry = c.eflags & 1;
            c.eax = carry ? 0xffffffff : 0;
            flags(run, c.eax, 32, carry, false, carry);
            c.eax = inc(run, c.eax);
            logic(run, c.eax & 0xff, 8);
            return c.eax != 0;
        };
        if (!(c.eflags & 0x40)) {
            external(run, 0x546abc, 0x4ffd21);
            named = equalVersion(4);
        }
        if (!named) {
            external(run, 0x546abc, 0x4ffd31);
            logic(run, c.edi & c.eax);
            if (c.eflags & 0x40) {
                external(run, 0x546abc, 0x4ffd37);
                named = equalVersion(3);
            }
        }
        if (named) {
            push(run, 0x5122d0);
            external(run, 0x546c2c, 0x4ffd50, {0x5122d0});
            run.put(0x540b58, c.eax);
        } else {
            run.put(0x540b58, 0);
            logic(run, 0);
        }
        c.edi = pop(run);
        c.esi = pop(run);
        break;
    }
    case 0x502dac: {
        push(run, c.ebx);
        push(run, c.esi);
        push(run, c.edi);
        c.esi = c.ecx;
        external(run, 0x546abc, 0x502db7);
        c.ecx = 0;
        logic(run, 0);
        push(run, 1);
        c.ecx = (c.eax >> 8) & 0xff;
        c.edx = c.eax & 0xff;
        c.edx <<= 8;
        logic(run, c.edx);
        uint32_t old = c.ecx;
        c.ecx += c.edx;
        flags(run, c.ecx, 32, c.ecx < old, ((~(old ^ c.edx) & (old ^ c.ecx)) >> 31) != 0, ((old ^ c.edx ^ c.ecx) & 0x10) != 0);
        run.put(c.esi + 0x54, c.ecx);
        c.ecx = c.eax >> 31;
        sub(run, c.eax & 0xff, 4, 8);
        run.put(c.esi + 0x58, c.ecx);
        c.eax = (c.eflags & 1) ? 0xffffffff : 0;
        c.ecx = pop(run);
        c.eax = inc(run, c.eax);
        c.ebx = 0;
        logic(run, 0);
        c.ecx = sub(run, c.ecx, c.eax);
        sub(run, c.eax, c.ebx);
        run.put(c.esi + 0x5c, c.eax);
        run.put(c.esi + 0x60, c.ecx);
        run.put(c.esi + 0x64, c.eax);
        run.put(c.esi + 0x68, c.ebx);
        if (!(c.eflags & 0x40)) {
            push(run, c.ebx);
            external(run, 0x546a94, 0x502df4, {c.ebx});
            sub(run, c.eax, 0x40000);
            bool carry = c.eflags & 1;
            c.eax = carry ? 0xffffffff : 0;
            flags(run, c.eax, 32, carry, false, carry);
            c.eax = inc(run, c.eax);
            run.put(c.esi + 0x68, c.eax);
        }
        c.ecx = c.esi;
        internal(run, 0x4fb3ba, 0x502e06);
        c.ecx = c.esi;
        run.put(c.esi + 0x24, c.ebx);
        internal(run, 0x4fb376, 0x502e10);
        c.edi = run.get(0x546b60);
        push(run, 0x7f02);
        push(run, c.ebx);
        external(run, 0x546b60, 0x502e1e, {c.ebx,0x7f02});
        push(run, 0x7f00);
        push(run, c.ebx);
        run.put(c.esi + 0x3c, c.eax);
        external(run, 0x546b60, 0x502e29, {c.ebx,0x7f00});
        run.put(c.esi + 0x40, c.eax);
        c.eax = 0;
        logic(run, 0);
        sub(run, run.get(c.esi + 0x5c), c.ebx);
        run.put(c.esi + 0x50, c.ebx);
        run.put(c.esi + 0x44, c.ebx);
        c.edi = pop(run);
        c.eax = (c.eflags & 0x40) ? 0 : 1;
        c.eax = inc(run, c.eax);
        run.put(c.esi + 0x10, c.eax);
        run.put(c.esi + 0x14, c.eax);
        c.eax = c.esi;
        c.esi = pop(run);
        c.ebx = pop(run);
        break;
    }
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
    return c.eax;
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x502dac: return {2047u, 2047u, 0u, 0u};
    case 0x4fb3ba: return {2047u, 2047u, 0u, 0u};
    case 0x4fb376: return {2047u, 2047u, 0u, 0u};
    case 0x502d5a: return {2047u, 2047u, 0u, 0u};
    case 0x502d8a: return {2047u, 2047u, 0u, 0u};
    case 0x4ffce9: return {2047u, 2047u, 0u, 0u};
    case 0x4ffd0c: return {2047u, 2047u, 0u, 0u};
    case 0x4db610: return {2047u, 2047u, 0u, 0u};
    case 0x4dbb80: return {2047u, 2047u, 0u, 0u};
    case 0x4dc170: return {2047u, 2047u, 0u, 0u};
    case 0x4dc270: return {2047u, 2047u, 0u, 0u};
    case 0x4dc390: return {2047u, 2047u, 0u, 0u};
    case 0x4dc3a0: return {2047u, 2047u, 0u, 4u};
    case 0x503818: return {2047u, 2047u, 0u, 0u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_static_final_records_entry, owned, source_contract, body)
