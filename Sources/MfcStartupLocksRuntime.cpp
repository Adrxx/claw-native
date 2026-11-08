// Original MFC lock initialization acquire and release
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x502e47:
        return 0;
    case 0x502e95:
        return 1;
    case 0x502f05:
        return 1;
    default:
        return -1;
    }
}

// Scoped owned calls retain the caller frame even when a physical service faults.
struct EntryFrame {
    Run &run;
    uint32_t frame;
    uint32_t stackPointer;
    EntryFrame(Run &run, uint32_t childFrame)
        : run(run), frame(run.frame), stackPointer(run.stackPointer) {
        run.frame = childFrame;
        run.stackPointer = 0;
    }
    ~EntryFrame() {
        run.frame = frame;
        run.stackPointer = stackPointer;
    }
};

// 0x502e47. Publishes initialization before the version service is called.
uint32_t function_502e47(Run &run, uint32_t, const uint32_t *) {
    // 0x5408e8: initialized; 0x540a88: locks disabled; 0x540a90: master section.
    if (run.get(0x5408e8) == 0) {
        run.put(0x5408e8, 1);
        run.stackPointer = run.frame - 8;
        uint32_t version = run.icall(0x546abc);
        if ((version & 0xff) < 4 && (version & 0x80000000) != 0) {
            run.put(0x540a88, 1);
        } else {
            run.put(0x540a88, 0);
        }
        if (run.get(0x540a88) == 0) {
            run.stackPointer = run.frame - 12;
            run.icall(0x546aa4, {0x540a90});
        }
    }
    return run.get(0x5408e8);
}

// 0x502e95. stdcall acquire; no semantic EAX return.
uint32_t function_502e95(Run &run, uint32_t, const uint32_t *arguments) {
    if (run.get(0x5408e8) == 0) {
        EntryFrame child(run, run.frame - 20);
        function_502e47(run, 0, nullptr);
    }
    if (run.get(0x540a88) == 0) {
        uint32_t index = arguments[0];
        // 0x540aa8: numbered initialized flags; 0x5408f0: 24-byte sections.
        uint32_t ready = 0x540aa8 + index * 4;
        bool initialized = run.get(ready) != 0;
        uint32_t enter = run.get(0x546aac);
        run.stackPointer = run.frame - 24;
        if (!initialized) {
            run.call(enter, 0, {0x540a90});
            if (run.get(ready) == 0) {
                run.icall(0x546aa4, {0x5408f0 + index * 24});
                run.put(ready, run.get(ready) + 1);
            }
            run.icall(0x546a9c, {0x540a90});
        }
        run.call(enter, 0, {0x5408f0 + index * 24});
    }
    return 0;
}

// 0x502f05. stdcall release; no semantic EAX return.
uint32_t function_502f05(Run &run, uint32_t, const uint32_t *arguments) {
    if (run.get(0x540a88) == 0) {
        run.stackPointer = run.frame - 8;
        run.icall(0x546a9c, {0x5408f0 + arguments[0] * 24});
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x502e47:
        return function_502e47(run, receiver, arguments);
    case 0x502e95:
        return function_502e95(run, receiver, arguments);
    case 0x502f05:
        return function_502f05(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}


// Arithmetic flags follow the original operand width.
uint32_t commonFlags(uint32_t value, uint32_t sign) {
    uint32_t low = value & 255;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    return 2u | (!(low & 1) ? 4u : 0u) | (!value ? 64u : 0u) | (value & sign ? 128u : 0u);
}
void compare(ClawSourceContext &cpu, uint32_t a, uint32_t b, bool byte = false) {
    uint32_t mask = byte ? 255u : 0xffffffffu;
    uint32_t sign = byte ? 128u : 0x80000000u;
    a &= mask;
    b &= mask;
    uint32_t result = (a - b) & mask;
    cpu.eflags = commonFlags(result, sign) | (a < b ? 1u : 0u) |
        ((a ^ b ^ result) & 16u) | (((a ^ b) & (a ^ result) & sign) ? 2048u : 0u);
}
void push(Run &run, ClawSourceContext &cpu, uint32_t value) {
    cpu.esp -= 4;
    run.put(cpu.esp, value);
}
uint32_t pop(Run &run, ClawSourceContext &cpu) {
    uint32_t value = run.get(cpu.esp);
    cpu.esp += 4;
    return value;
}
void physical(Run &run, ClawSourceContext &cpu, uint32_t target, uint32_t pc,
              bool argument, uint32_t value = 0) {
    if (argument) push(run, cpu, value);
    push(run, cpu, pc);
    cpu.eip = target;
    ClawSourceContext child = cpu;
    try {
        if (argument) run.source_call(target, 0, pc, child, {value}, 0, 4);
        else run.source_call(target, 0, pc, child);
    } catch (...) {
        cpu = child;
        throw;
    }
    cpu = child;
}
// 0x502e47: source initializer with its physical save and service frames.
void sourceInitialize(Run &run, ClawSourceContext &cpu) {
    compare(cpu, run.get(0x5408e8), 0);
    bool warm = !(cpu.eflags & 64);
    push(run, cpu, cpu.esi);
    if (!warm) {
        push(run, cpu, 1);
        cpu.esi = pop(run, cpu);
        run.put(0x5408e8, cpu.esi);
        physical(run, cpu, 0x546abc, 0x502e60, false);
        compare(cpu, cpu.eax, 4, true);
        bool old = cpu.eflags & 1;
        if (old) {
            cpu.eflags = commonFlags(cpu.eax & 0x80000000u, 0x80000000u);
            old = !(cpu.eflags & 64);
        }
        if (old) run.put(0x540a88, cpu.esi);
        else {
            run.put(0x540a88, run.get(0x540a88) & 0u);
            cpu.eflags = commonFlags(0, 0x80000000u);
        }
        compare(cpu, run.get(0x540a88), 0);
        if (cpu.eflags & 64) physical(run, cpu, 0x546aa4, 0x502e8e, true, 0x540a90);
    }
    cpu.eax = run.get(0x5408e8);
    cpu.esi = pop(run, cpu);
}
// A native owned CALL borrows a distinct source envelope and restores host scope on unwind.
struct SourceBorrow {
    Run &run;
    ClawSourceContext *source;
    uint32_t returnPC, entry, frame, stack;
    SourceBorrow(Run &r, ClawSourceContext &child, uint32_t pc)
        : run(r), source(r.host.sourceContext), returnPC(r.host.sourceReturnPC),
          entry(r.host.entryStackPointer), frame(r.frame), stack(r.stackPointer) {
        r.host.sourceContext = &child;
        r.host.sourceReturnPC = pc;
        r.host.entryStackPointer = child.esp;
        r.frame = child.esp;
        r.stackPointer = 0;
    }
    ~SourceBorrow() {
        run.host.sourceContext = source;
        run.host.sourceReturnPC = returnPC;
        run.host.entryStackPointer = entry;
        run.frame = frame;
        run.stackPointer = stack;
    }
};
void ownedInitialize(Run &run, ClawSourceContext &cpu) {
    push(run, cpu, 0x502ea8);
    cpu.eip = 0x502e47;
    ClawSourceContext child = cpu;
    const auto before = child;
    SourceBorrow scope(run, child, 0x502ea8);
    try {
        run.validate_source(child, 0x502e47, 0x502ea8);
        sourceInitialize(run, child);
        if (child.esp != before.esp || run.get(child.esp) != 0x502ea8 ||
            run.host.sourceContext != &child || run.host.sourceReturnPC != 0x502ea8)
            run.fail(CLAW_FAULT_ABI, 0x502e47);
        child.eip = pop(run, child);
        run.validate_source_output(child, before, 0x502e47, 0x502ea8, 0);
    } catch (...) {
        cpu = child;
        throw;
    }
    cpu = child;
}
// 0x502e95: source acquire keeps the import cache and live guest save slots.
void sourceAcquire(Run &run, ClawSourceContext &cpu) {
    push(run, cpu, cpu.ebx);
    cpu.ebx = 0;
    cpu.eflags = commonFlags(0, 0x80000000u);
    compare(cpu, run.get(0x5408e8), cpu.ebx);
    bool cold = cpu.eflags & 64;
    push(run, cpu, cpu.ebp);
    push(run, cpu, cpu.esi);
    push(run, cpu, cpu.edi);
    if (cold) ownedInitialize(run, cpu);
    compare(cpu, run.get(0x540a88), cpu.ebx);
    if (cpu.eflags & 64) {
        cpu.edi = run.get(cpu.esp + 0x14);
        compare(cpu, run.get(0x540aa8 + cpu.edi * 4), cpu.ebx);
        cpu.ebx = run.get(0x546aac);
        cpu.esi = 0x540aa8 + cpu.edi * 4;
        if (cpu.eflags & 64) {
            cpu.ebp = 0x540a90;
            physical(run, cpu, cpu.ebx, 0x502ed2, true, cpu.ebp);
            compare(cpu, run.get(cpu.esi), 0);
            if (cpu.eflags & 64) {
                cpu.eax = cpu.edi + cpu.edi * 2;
                cpu.eax = cpu.eax * 8 + 0x5408f0;
                physical(run, cpu, 0x546aa4, 0x502ee8, true, cpu.eax);
                uint32_t previous = run.get(cpu.esi);
                uint32_t next = previous + 1;
                run.put(cpu.esi, next);
                cpu.eflags = commonFlags(next, 0x80000000u) | (cpu.eflags & 1) |
                    ((previous ^ next ^ 1u) & 16u) | (previous == 0x7fffffffu ? 2048u : 0u);
            }
            physical(run, cpu, 0x546a9c, 0x502ef1, true, cpu.ebp);
        }
        cpu.eax = cpu.edi + cpu.edi * 2;
        cpu.eax = cpu.eax * 8 + 0x5408f0;
        physical(run, cpu, cpu.ebx, 0x502efe, true, cpu.eax);
    }
    cpu.edi = pop(run, cpu);
    cpu.esi = pop(run, cpu);
    cpu.ebp = pop(run, cpu);
    cpu.ebx = pop(run, cpu);
}
// 0x502f05: source release propagates even semantic-void EAX and service state.
uint32_t sourceBody(Run &run, uint32_t function, uint32_t, const uint32_t *) {
    auto &cpu = run.source();
    if (function == 0x502e47) sourceInitialize(run, cpu);
    else if (function == 0x502e95) sourceAcquire(run, cpu);
    else {
        compare(cpu, run.get(0x540a88), 0);
        if (cpu.eflags & 64) {
            cpu.eax = run.get(cpu.esp + 4);
            cpu.eax = cpu.eax + cpu.eax * 2;
            cpu.eax = cpu.eax * 8 + 0x5408f0;
            physical(run, cpu, 0x546a9c, 0x502f23, true, cpu.eax);
        }
    }
    return cpu.eax;
}
ClawSourceContract contract(uint32_t function) {
    return {0x7ff, 0x7ff, 0, function == 0x502e47 ? 0u : 4u};
}
bool optional(uint32_t function) {
    return owned(function) >= 0;
}

} // namespace

CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_mfc_startup_locks_entry, owned, contract, optional, body, sourceBody)
