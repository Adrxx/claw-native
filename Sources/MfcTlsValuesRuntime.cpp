// Original MFC thread-local value retrieval and storage
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
    case 0x50335e:
        return 1;
    case 0x503167:
        return 2;
    default:
        return -1;
    }
}

// Physical outgoing frames are relative to the current owned entry ESP.
uint32_t outward(Run &run, int32_t offset, uint32_t target, uint32_t receiver,
                  std::initializer_list<uint32_t> arguments = {}) {
    run.stackPointer = run.automatic(offset);
    return run.call(target, receiver, arguments);
}

uint32_t function_503167(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x50335e. The receiver +0 is the slot ordinal; 0x540af0 publishes the manager.
uint32_t function_50335e(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(run.automatic(4), arguments[0]);
    if (run.get(receiver) == 0) {
        uint32_t manager = run.get(0x540af0);
        if (manager == 0) {
            manager = outward(run, -12, 0x502fb6, 0x540af8);
            run.put(0x540af0, manager);
        }
        uint32_t ordinal = outward(run, -12, 0x502ff8, manager);
        run.put(receiver, ordinal);
    }
    uint32_t manager = run.get(0x540af0);
    uint32_t ordinal = run.get(receiver);
    // Manager +0 is its physical TLS index.
    uint32_t container = outward(run, -16, 0x546a7c, 0, {run.get(manager)});
    uint32_t value = 0;
    // Container +8 is signed logical count; +0xc points to DWORD values.
    if (container != 0 && s32(ordinal) < s32(run.get(container + 8))) {
        uint32_t values = run.get(container + 0xc);
        value = run.get(values + ordinal * 4);
    }
    if (value == 0) {
        uint32_t factory = run.get(run.automatic(4));
        value = outward(run, -12, factory, 0);
        manager = run.get(0x540af0);
        uint32_t nestedArguments[] = {run.get(receiver), value};
        uint32_t parentFrame = run.frame;
        uint32_t parentStack = run.stackPointer;
        run.frame = run.automatic(-20);
        try {
            function_503167(run, manager, nestedArguments);
        } catch (...) {
            run.frame = parentFrame;
            run.stackPointer = parentStack;
            throw;
        }
        run.frame = parentFrame;
        run.stackPointer = parentStack;
    }
    return value;
}

// 0x503167. Retains the original unchecked final array store.
uint32_t function_503167(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(run.automatic(4), arguments[0]);
    run.put(run.automatic(8), arguments[1]);
    uint32_t container = outward(run, -16, 0x546a7c, 0, {run.get(receiver)});
    bool grow = true;
    if (container != 0) {
        uint32_t ordinal = run.get(run.automatic(4));
        if (s32(ordinal) < s32(run.get(container + 8))) {
            grow = false;
        } else if (run.get(run.automatic(8)) == 0) {
            grow = false;
        }
    } else {
        container = outward(run, -16, 0x502f84, 0, {16});
        if (container != 0) {
            run.put(container, 0x511a64);
        }
        run.put(container + 8, 0);
        run.put(container + 0xc, 0);
        // Manager +0x1c is its critical section, +0x14 its intrusive list.
        outward(run, -16, 0x546aac, 0, {receiver + 0x1c});
        outward(run, -16, 0x502f26, receiver + 0x14, {container});
        outward(run, -16, 0x546a9c, 0, {receiver + 0x1c});
    }
    if (grow) {
        uint32_t values = run.get(container + 0xc);
        // Manager +0xc is the required value count.
        uint32_t allocated;
        if (values == 0) {
            uint32_t size = run.get(receiver + 0xc) * 4;
            allocated = outward(run, -20, 0x546aa8, 0, {0, size});
        } else {
            uint32_t size = run.get(receiver + 0xc) * 4;
            allocated = outward(run, -24, 0x546a80, 0, {values, size, 2});
        }
        run.put(container + 0xc, allocated);
        if (allocated == 0) {
            outward(run, -12, 0x4f50fd, 0);
        }
        uint32_t oldCount = run.get(container + 8);
        uint32_t length = (oldCount * 0x3fffffffu + run.get(receiver + 0xc)) * 4;
        values = run.get(container + 0xc);
        outward(run, -24, 0x4a4a20, 0, {values + oldCount * 4, 0, length});
        run.put(container + 8, run.get(receiver + 0xc));
        outward(run, -20, 0x546a84, 0, {run.get(receiver), container});
    }
    uint32_t values = run.get(container + 0xc);
    uint32_t ordinal = run.get(run.automatic(4));
    uint32_t value = run.get(run.automatic(8));
    run.put(values + ordinal * 4, value);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x50335e:
        return function_50335e(run, receiver, arguments);
    case 0x503167:
        return function_503167(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

using CPU = ClawSourceContext;

uint32_t status(uint32_t value) {
    uint32_t parity = value & 0xff;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    return 2u | (value == 0 ? 0x40u : 0u) | (value & 0x80000000u ? 0x80u : 0u) |
           (!(parity & 1) ? 4u : 0u);
}

void test(CPU &cpu, uint32_t value) {
    cpu.eflags = status(value);
}

void compare(CPU &cpu, uint32_t left, uint32_t right) {
    uint32_t value = left - right;
    cpu.eflags = status(value) | (left < right ? 1u : 0u) |
                 ((left ^ right ^ value) & 0x10u) |
                 (((left ^ right) & (left ^ value) & 0x80000000u) ? 0x800u : 0u);
}

void add(CPU &cpu, uint32_t &destination, uint32_t operand) {
    uint32_t previous = destination;
    destination += operand;
    cpu.eflags = status(destination) | (destination < previous ? 1u : 0u) |
                 ((previous ^ operand ^ destination) & 0x10u) |
                 ((~(previous ^ operand) & (previous ^ destination) & 0x80000000u) ? 0x800u : 0u);
}

void shift_two(CPU &cpu, uint32_t &destination) {
    uint32_t previous = destination;
    destination <<= 2;
    uint32_t carry = (previous >> 30) & 1;
    cpu.eflags = status(destination) | carry |
                 (((destination >> 31) ^ carry) ? 0x800u : 0u);
}

void push(Run &run, CPU &cpu, uint32_t value) {
    cpu.esp -= 4;
    run.put(cpu.esp, value);
}

uint32_t pop(Run &run, CPU &cpu) {
    uint32_t value = run.get(cpu.esp);
    cpu.esp += 4;
    return value;
}

uint32_t preservation(uint32_t target) {
    if (target == 0x502fb6) {
        return 0x462;
    }
    if (target == 0x502ff8) {
        return 0x400;
    }
    if (target == 0x4a4a20) {
        return 0x452;
    }
    return 0x472;
}

void source_outward(Run &run, CPU &cpu, uint32_t target, uint32_t returnPC,
                     uint32_t receiver, std::initializer_list<uint32_t> arguments = {},
                     uint32_t popBytes = 0) {
    CPU child = cpu;
    child.preserveMask = preservation(target);
    child.eip = target;
    child.esp -= 4;
    run.source_call(target, receiver, returnPC, child, arguments, 0, popBytes);
    std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
}

void source_setter(Run &run, CPU &cpu) {
    const uint32_t frame = cpu.esp;
    push(run, cpu, cpu.esi);
    push(run, cpu, cpu.edi);
    cpu.edi = cpu.ecx;
    push(run, cpu, run.get(cpu.edi));
    source_outward(run, cpu, 0x546a7c, 0x503173, 0, {run.get(cpu.esp)}, 4);
    cpu.esi = cpu.eax;
    test(cpu, cpu.esi);
    bool grow = true;
    if (cpu.esi != 0) {
        cpu.eax = run.get(cpu.esp + 0xc);
        uint32_t count = run.get(cpu.esi + 8);
        compare(cpu, cpu.eax, count);
        if (s32(cpu.eax) < s32(count)) {
            grow = false;
        } else {
            uint32_t value = run.get(cpu.esp + 0x10);
            compare(cpu, value, 0);
            if (value == 0) {
                grow = false;
            } else {
                test(cpu, cpu.esi);
            }
        }
    } else {
        push(run, cpu, 16);
        source_outward(run, cpu, 0x502f84, 0x50319c, 0, {16}, 4);
        test(cpu, cpu.eax);
        if (cpu.eax != 0) {
            run.put(cpu.eax, 0x511a64);
            cpu.esi = cpu.eax;
        } else {
            cpu.esi = 0;
            test(cpu, cpu.esi);
        }
        run.put(cpu.esi + 8, 0);
        test(cpu, 0);
        run.put(cpu.esi + 0xc, 0);
        test(cpu, 0);
        cpu.eax = cpu.edi + 0x1c;
        push(run, cpu, cpu.eax);
        source_outward(run, cpu, 0x546aac, 0x5031be, 0, {run.get(cpu.esp)}, 4);
        push(run, cpu, cpu.esi);
        cpu.ecx = cpu.edi + 0x14;
        source_outward(run, cpu, 0x502f26, 0x5031c7, cpu.ecx, {run.get(cpu.esp)}, 4);
        cpu.eax = cpu.edi + 0x1c;
        push(run, cpu, cpu.eax);
        source_outward(run, cpu, 0x546a9c, 0x5031d1, 0, {run.get(cpu.esp)}, 4);
    }
    if (grow) {
        cpu.eax = run.get(cpu.esi + 0xc);
        test(cpu, cpu.eax);
        if (cpu.eax == 0) {
            cpu.eax = run.get(cpu.edi + 0xc);
            shift_two(cpu, cpu.eax);
            push(run, cpu, cpu.eax);
            push(run, cpu, 0);
            source_outward(run, cpu, 0x546aa8, 0x5031e7, 0,
                           {run.get(cpu.esp), run.get(cpu.esp + 4)}, 8);
        } else {
            cpu.ecx = run.get(cpu.edi + 0xc);
            push(run, cpu, 2);
            shift_two(cpu, cpu.ecx);
            push(run, cpu, cpu.ecx);
            push(run, cpu, cpu.eax);
            source_outward(run, cpu, 0x546a80, 0x5031f9, 0,
                           {run.get(cpu.esp), run.get(cpu.esp + 4), run.get(cpu.esp + 8)}, 12);
        }
        test(cpu, cpu.eax);
        run.put(cpu.esi + 0xc, cpu.eax);
        if (cpu.eax == 0) {
            source_outward(run, cpu, 0x4f50fd, 0x503205, 0);
        }
        cpu.eax = run.get(cpu.esi + 8);
        cpu.ecx = cpu.eax;
        int64_t product = int64_t(s32(cpu.ecx)) * int64_t(0x3fffffff);
        cpu.ecx *= 0x3fffffff;
        bool overflow = product != int64_t(s32(cpu.ecx));
        cpu.eflags = (cpu.eflags & ~0x801u) | (overflow ? 0x801u : 0u);
        add(cpu, cpu.ecx, run.get(cpu.edi + 0xc));
        shift_two(cpu, cpu.ecx);
        push(run, cpu, cpu.ecx);
        cpu.ecx = run.get(cpu.esi + 0xc);
        push(run, cpu, 0);
        cpu.eax = cpu.ecx + cpu.eax * 4;
        push(run, cpu, cpu.eax);
        source_outward(run, cpu, 0x4a4a20, 0x503225, 0,
                       {run.get(cpu.esp), run.get(cpu.esp + 4), run.get(cpu.esp + 8)});
        cpu.eax = run.get(cpu.edi + 0xc);
        add(cpu, cpu.esp, 12);
        run.put(cpu.esi + 8, cpu.eax);
        push(run, cpu, cpu.esi);
        push(run, cpu, run.get(cpu.edi));
        source_outward(run, cpu, 0x546a84, 0x503237, 0,
                       {run.get(cpu.esp), run.get(cpu.esp + 4)}, 8);
    }
    cpu.eax = run.get(cpu.esi + 0xc);
    cpu.edx = run.get(cpu.esp + 0xc);
    cpu.ecx = run.get(cpu.esp + 0x10);
    cpu.edi = pop(run, cpu);
    run.put(cpu.eax + cpu.edx * 4, cpu.ecx);
    cpu.esi = pop(run, cpu);
    if (cpu.esp != frame) {
        run.fail(CLAW_FAULT_ABI, 0x503167);
    }
}

void source_getter(Run &run, CPU &cpu) {
    push(run, cpu, cpu.esi);
    push(run, cpu, cpu.edi);
    cpu.edi = cpu.ecx;
    uint32_t ordinal = run.get(cpu.edi);
    compare(cpu, ordinal, 0);
    if (ordinal == 0) {
        cpu.ecx = run.get(0x540af0);
        test(cpu, cpu.ecx);
        if (cpu.ecx == 0) {
            cpu.ecx = 0x540af8;
            cpu.eax = cpu.ecx;
            test(cpu, cpu.eax);
            source_outward(run, cpu, 0x502fb6, 0x503381, cpu.ecx);
            cpu.ecx = cpu.eax;
            run.put(0x540af0, cpu.ecx);
        }
        source_outward(run, cpu, 0x502ff8, 0x503392, cpu.ecx);
        run.put(cpu.edi, cpu.eax);
    }
    cpu.eax = run.get(0x540af0);
    cpu.esi = run.get(cpu.edi);
    push(run, cpu, run.get(cpu.eax));
    source_outward(run, cpu, 0x546a7c, 0x5033a3, 0, {run.get(cpu.esp)}, 4);
    test(cpu, cpu.eax);
    bool missing = cpu.eax == 0;
    if (!missing) {
        uint32_t count = run.get(cpu.eax + 8);
        compare(cpu, cpu.esi, count);
        missing = s32(cpu.esi) >= s32(count);
        if (!missing) {
            cpu.eax = run.get(cpu.eax + 0xc);
            cpu.esi = run.get(cpu.eax + cpu.esi * 4);
        }
    }
    if (missing) {
        cpu.esi = 0;
        test(cpu, cpu.esi);
    }
    test(cpu, cpu.esi);
    if (cpu.esi == 0) {
        uint32_t factory = run.get(cpu.esp + 0xc);
        if (factory != 0x502335 && factory != 0x502369 && factory != 0x502301) {
            run.fail(CLAW_FAULT_ABI, factory);
        }
        source_outward(run, cpu, factory, 0x5033be, 0);
        cpu.ecx = run.get(0x540af0);
        cpu.esi = cpu.eax;
        push(run, cpu, cpu.esi);
        push(run, cpu, run.get(cpu.edi));
        CPU child = cpu;
        child.preserveMask = 0x442;
        child.eip = 0x503167;
        child.esp -= 4;
        run.put(child.esp, 0x5033ce);
        const CPU before = child;
        const uint32_t parentFrame = run.frame;
        const auto parentContext = run.host.sourceContext;
        const uint32_t parentEntryStack = run.host.entryStackPointer;
        const uint32_t parentReturnPC = run.host.sourceReturnPC;
        run.frame = child.esp;
        run.host.sourceContext = &child;
        run.host.entryStackPointer = child.esp;
        run.host.sourceReturnPC = 0x5033ce;
        const auto restoreParent = [&]() {
            run.frame = parentFrame;
            run.host.sourceContext = parentContext;
            run.host.entryStackPointer = parentEntryStack;
            run.host.sourceReturnPC = parentReturnPC;
        };
        try {
            source_setter(run, child);
            child.eip = run.get(child.esp);
            child.esp += 12;
            run.validate_source_output(child, before, 0x503167, 0x5033ce, 8);
        } catch (...) {
            restoreParent();
            throw;
        }
        restoreParent();
        std::memcpy(&cpu.eax, &child.eax, 11 * sizeof(uint32_t));
    }
    cpu.eax = cpu.esi;
    cpu.edi = pop(run, cpu);
    cpu.esi = pop(run, cpu);
}

ClawSourceContract contract(uint32_t function) {
    if (function == 0x50335e) {
        return {0x7ff, 0x7ff, 0x400, 4};
    }
    if (function == 0x503167) {
        return {0x7ff, 0x7ff, 0x442, 8};
    }
    return {};
}

bool optional(uint32_t function) {
    return owned(function) >= 0;
}

uint32_t source_body(Run &run, uint32_t function, uint32_t, const uint32_t *) {
    CPU &cpu = run.source();
    if (function == 0x50335e) {
        source_getter(run, cpu);
    } else {
        source_setter(run, cpu);
    }
    return cpu.eax;
}

} // namespace

CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_mfc_tls_values_entry, owned, contract, optional, body, source_body)
