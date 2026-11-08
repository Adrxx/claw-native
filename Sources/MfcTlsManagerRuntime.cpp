#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x502fb6:
    case 0x502ff8:
        return 0;
    default:
        return -1;
    }
}

// 0x502fb6. Fields: TLS index +0, capacity +4, next slot +8,
// high water +0xc, table data +0x10, list head +0x14, link offset +0x18,
// and the physical critical section +0x1c.
uint32_t initialize(Run &run, uint32_t manager) {
    run.put(manager + 0x14, 0);
    run.put(manager + 0x18, 0);
    run.put(manager + 0x18, 4);
    run.put(manager + 4, 0);
    run.put(manager + 8, 1);
    run.put(manager + 0xc, 0);
    run.put(manager + 0x10, 0);
    run.stackPointer = run.frame - 8;
    uint32_t index = run.icall(0x546a90);
    run.put(manager, index);
    if (index == 0xffffffffu) {
        run.stackPointer = run.frame - 8;
        run.call(0x4f50fd, 0);
    }
    run.stackPointer = run.frame - 12;
    run.icall(0x546aa4, {manager + 0x1c});
    return manager;
}

// 0x502ff8. A slot is eight bytes; only flag bit zero determines use.
uint32_t allocateSlot(Run &run, uint32_t manager) {
    uint32_t critical = manager + 0x1c;
    run.stackPointer = run.frame - 32;
    run.icall(0x546aac, {critical});
    uint32_t capacity = run.get(manager + 4);
    uint32_t selected = run.get(manager + 8);
    bool grow = false;
    if (s32(selected) >= s32(capacity) || (run.get8(run.get(manager + 0x10) + selected * 8u) & 1u)) {
        selected = 1;
        if (s32(selected) < s32(capacity)) {
            uint32_t cursor = run.get(manager + 0x10) + 8;
            while (run.get8(cursor) & 1u) {
                ++selected;
                cursor += 8;
                if (s32(selected) >= s32(capacity))
                    break;
            }
        }
        grow = s32(selected) >= s32(capacity);
    }
    if (grow) {
        uint32_t oldData = run.get(manager + 0x10);
        capacity += 32;
        uint32_t handle;
        if (!oldData) {
            run.stackPointer = run.frame - 36;
            handle = run.icall(0x546b1c, {0x2002, capacity * 8u});
        } else {
            run.stackPointer = run.frame - 32;
            uint32_t oldHandle = run.icall(0x546a8c, {oldData});
            run.icall(0x5469c8, {oldHandle});
            run.stackPointer = run.frame - 40;
            handle = run.icall(0x546a88, {oldHandle, capacity * 8u, 0x2002});
        }
        uint32_t lock = run.get(0x5469c4);
        if (!handle) {
            run.stackPointer = run.frame - 32;
            uint32_t oldHandle = run.icall(0x546a8c, {run.get(manager + 0x10)});
            run.call(lock, 0, {oldHandle});
            run.icall(0x546a9c, {critical});
            run.stackPointer = run.frame - 28;
            run.call(0x4f50fd, 0);
        }
        run.stackPointer = run.frame - 32;
        uint32_t data = run.call(lock, 0, {handle});
        uint32_t oldCapacity = run.get(manager + 4);
        uint32_t count = (oldCapacity * 0x1fffffffu + capacity) * 8u;
        run.stackPointer = run.frame - 40;
        run.call(0x4a4a20, 0, {data + oldCapacity * 8u, 0, count});
        run.put(manager + 4, capacity);
        run.put(manager + 0x10, data);
    }
    if (s32(selected) >= s32(run.get(manager + 0xc)))
        run.put(manager + 0xc, selected + 1);
    uint32_t flag = run.get(manager + 0x10) + selected * 8u;
    run.put(flag, run.get(flag) | 1u);
    run.put(manager + 8, selected + 1);
    run.stackPointer = run.frame - 32;
    run.icall(0x546a9c, {critical});
    return selected;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *) {
    switch (function) {
    case 0x502fb6:
        return initialize(run, receiver);
    case 0x502ff8:
        return allocateSlot(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

// Physical arithmetic and addressable stack state for the optional source ABI.
uint32_t logicFlags(uint32_t value) {
    uint32_t parity = value & 255;
    parity ^= parity >> 4;
    parity &= 15;
    return 2u | (!value ? 0x40u : 0u) | (value & 0x80000000u ? 0x80u : 0u) | ((0x9669u >> parity) & 1u ? 4u : 0u);
}
void addFlags(ClawSourceContext &c, uint32_t a, uint32_t b, bool subtract = false) {
    uint32_t v = subtract ? a - b : a + b;
    c.eflags = logicFlags(v) | (((a ^ b ^ v) & 16u) ? 16u : 0u) |
               ((subtract ? a < b : uint64_t(a) + b > 0xffffffffu) ? 1u : 0u) |
               (((subtract ? (a ^ b) & (a ^ v) : ~(a ^ b) & (a ^ v)) & 0x80000000u) ? 0x800u : 0u);
}
void push(Run &run, ClawSourceContext &c, uint32_t value) {
    c.esp -= 4;
    run.put(c.esp, value);
}
uint32_t pop(Run &run, ClawSourceContext &c) {
    auto v = run.get(c.esp);
    c.esp += 4;
    return v;
}
void edge(Run &run, ClawSourceContext &c, uint32_t function, uint32_t pc, std::initializer_list<uint32_t> args = {},
          uint32_t preserve = 0x472, bool calleePop = true) {
    auto child = c;
    child.esp -= 4;
    child.eip = function;
    child.inputMask = child.outputMask = 0x7ff;
    child.preserveMask = preserve;
    run.source_call(function, 0, pc, child, args, 0, calleePop ? uint32_t(args.size() * 4) : 0);
    c.eax = child.eax;
    c.ebx = child.ebx;
    c.ecx = child.ecx;
    c.edx = child.edx;
    c.esi = child.esi;
    c.edi = child.edi;
    c.ebp = child.ebp;
    c.esp = child.esp;
    c.eip = child.eip;
    c.eflags = child.eflags;
    c.fsHead = child.fsHead;
}
uint32_t sourceBody(Run &run, uint32_t function, uint32_t, const uint32_t *) {
    auto &c = run.source();
    if (function == 0x502fb6) {
        push(run, c, c.esi);
        c.esi = c.ecx;
        c.eax = 0;
        c.eflags = logicFlags(0);
        run.put(c.esi + 0x14, c.eax);
        run.put(c.esi + 0x18, c.eax);
        run.put(c.esi + 0x18, 4);
        run.put(c.esi + 4, c.eax);
        run.put(c.esi + 8, 1);
        run.put(c.esi + 0xc, c.eax);
        run.put(c.esi + 0x10, c.eax);
        edge(run, c, 0x546a90, 0x502fde);
        addFlags(c, c.eax, 0xffffffffu, true);
        run.put(c.esi, c.eax);
        if (c.eax == 0xffffffffu)
            edge(run, c, 0x4f50fd, 0x502fea, {}, 0x472, false);
        c.eax = c.esi + 0x1c;
        push(run, c, c.eax);
        edge(run, c, 0x546aa4, 0x502ff4, {c.eax});
        c.eax = c.esi;
        c.esi = pop(run, c);
        return c.eax;
    }
    push(run, c, c.ecx);
    push(run, c, c.ecx);
    push(run, c, c.ebx);
    push(run, c, c.ebp);
    push(run, c, c.esi);
    c.esi = c.ecx;
    push(run, c, c.edi);
    c.eax = c.esi + 0x1c;
    push(run, c, c.eax);
    run.put(c.esp + 0x18, c.eax);
    edge(run, c, 0x546aac, 0x50300e, {c.eax});
    c.ebp = run.get(c.esi + 4);
    c.edi = run.get(c.esi + 8);
    addFlags(c, c.edi, c.ebp, true);
    bool scan = s32(c.edi) >= s32(c.ebp);
    if (!scan) {
        c.eax = run.get(c.esi + 0x10);
        c.eflags = logicFlags(run.get8(c.eax + c.edi * 8) & 1);
        scan = !(c.eflags & 0x40);
    }
    bool grow = false;
    if (scan) {
        push(run, c, 1);
        c.edi = pop(run, c);
        addFlags(c, c.edi, c.ebp, true);
        if (s32(c.edi) < s32(c.ebp)) {
            c.eax = run.get(c.esi + 0x10);
            addFlags(c, c.eax, 8);
            c.eax += 8;
            for (;;) {
                c.eflags = logicFlags(run.get8(c.eax) & 1);
                if (c.eflags & 0x40)
                    break;
                auto cf = c.eflags & 1;
                addFlags(c, c.edi, 1);
                c.eflags = (c.eflags & ~1u) | cf;
                ++c.edi;
                addFlags(c, c.eax, 8);
                c.eax += 8;
                addFlags(c, c.edi, c.ebp, true);
                if (s32(c.edi) >= s32(c.ebp))
                    break;
            }
            addFlags(c, c.edi, c.ebp, true);
        }
        grow = s32(c.edi) >= s32(c.ebp);
    }
    if (grow) {
        c.eax = run.get(c.esi + 0x10);
        addFlags(c, c.ebp, 32);
        c.ebp += 32;
        c.eflags = logicFlags(c.eax);
        if (!c.eax) {
            c.eax = c.ebp;
            c.eflags = logicFlags(c.eax << 3) | ((c.eax >> 29) & 1);
            c.eax <<= 3;
            push(run, c, c.eax);
            push(run, c, 0x2002);
            edge(run, c, 0x546b1c, 0x503062, {0x2002, c.eax});
        } else {
            push(run, c, c.eax);
            edge(run, c, 0x546a8c, 0x50306b, {c.eax});
            c.ebx = c.eax;
            push(run, c, c.ebx);
            edge(run, c, 0x5469c8, 0x503074, {c.ebx});
            c.eax = c.ebp;
            push(run, c, 0x2002);
            c.eflags = logicFlags(c.eax << 3) | ((c.eax >> 29) & 1);
            c.eax <<= 3;
            push(run, c, c.eax);
            push(run, c, c.ebx);
            edge(run, c, 0x546a88, 0x503086, {c.ebx, c.eax, 0x2002});
        }
        c.ebx = run.get(0x5469c4);
        run.put(c.esp + 0x10, c.eax);
        c.eflags = logicFlags(c.eax);
        if (!c.eax) {
            auto v = run.get(c.esi + 0x10);
            push(run, c, v);
            edge(run, c, 0x546a8c, 0x50309d, {v});
            push(run, c, c.eax);
            edge(run, c, c.ebx, 0x5030a0, {c.eax});
            v = run.get(c.esp + 0x14);
            push(run, c, v);
            edge(run, c, 0x546a9c, 0x5030aa, {v});
            edge(run, c, 0x4f50fd, 0x5030af, {}, 0x472, false);
        }
        auto h = run.get(c.esp + 0x10);
        push(run, c, h);
        edge(run, c, c.ebx, 0x5030b5, {h});
        c.ebx = c.eax;
        c.eax = run.get(c.esi + 4);
        c.ecx = c.eax;
        c.ecx *= 0x1fffffffu;
        addFlags(c, c.ecx, c.ebp);
        c.ecx += c.ebp;
        c.eax = c.ebx + c.eax * 8;
        c.eflags = logicFlags(c.ecx << 3) | ((c.ecx >> 29) & 1);
        c.ecx <<= 3;
        push(run, c, c.ecx);
        push(run, c, 0);
        push(run, c, c.eax);
        edge(run, c, 0x4a4a20, 0x5030d3, {c.eax, 0, c.ecx}, 0x452, false);
        addFlags(c, c.esp, 12);
        c.esp += 12;
        run.put(c.esi + 4, c.ebp);
        run.put(c.esi + 0x10, c.ebx);
    }
    addFlags(c, c.edi, run.get(c.esi + 0xc), true);
    if (s32(c.edi) >= s32(run.get(c.esi + 0xc))) {
        c.eax = c.edi + 1;
        run.put(c.esi + 0xc, c.eax);
    }
    c.eax = run.get(c.esi + 0x10);
    auto slot = c.eax + c.edi * 8;
    auto v = run.get(slot) | 1u;
    run.put(slot, v);
    c.eflags = logicFlags(v);
    v = run.get(c.esp + 0x14);
    push(run, c, v);
    c.eax = c.eax + c.edi * 8;
    c.eax = c.edi + 1;
    run.put(c.esi + 8, c.eax);
    edge(run, c, 0x546a9c, 0x503101, {v});
    c.eax = c.edi;
    c.edi = pop(run, c);
    c.esi = pop(run, c);
    c.ebp = pop(run, c);
    c.ebx = pop(run, c);
    c.ecx = pop(run, c);
    c.ecx = pop(run, c);
    return c.eax;
}
ClawSourceContract contract(uint32_t f) {
    return {0x7ff, 0x7ff, f == 0x502fb6 ? 0x462u : 0x400u, 0};
}
bool optional(uint32_t) {
    return true;
}
} // namespace

CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_mfc_tls_manager_entry, owned, contract, optional, body, sourceBody)
