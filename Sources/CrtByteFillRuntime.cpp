// Original CRT byte fill
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4a4a20:
        return 3;
    default:
        return -1;
    }
}

// 0x4a4a20. cdecl, 3 stack argument(s), returns u32.
uint32_t function_4a4a20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t destination = arguments[0];
    uint32_t count = arguments[2];
    if (!count)
        return destination;
    const uint32_t byte = arguments[1] & 0xffu;
    if (count >= 4) {
        const uint32_t prefix = (0u - destination) & 3u;
        for (uint32_t i = 0; i < prefix; ++i) {
            run.put8(destination, uint8_t(byte));
            ++destination;
        }
        count -= prefix;
        const uint32_t pattern = byte | (byte << 8) | (byte << 16) | (byte << 24);
        const uint32_t words = count >> 2;
        for (uint32_t i = 0; i < words; ++i) {
            run.put(destination, pattern);
            destination += 4;
        }
        count &= 3u;
    }
    for (uint32_t i = 0; i < count; ++i) {
        run.put8(destination, uint8_t(byte));
        ++destination;
    }
    // A guest buffer can overlap incoming arguments; the source reloads this
    // word after filling rather than returning the captured pointer operand.
    return run.get(run.automatic(4));
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4a4a20:
        return function_4a4a20(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

ClawSourceContract contract(uint32_t) {
    return {0x7ffu, 0x7ffu, 0x452u, 0};
}

bool optional(uint32_t function) {
    return function == 0x4a4a20;
}

uint32_t source_body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (function != 0x4a4a20)
        run.fail(CLAW_FAULT_ABI, function);
    auto &cpu = run.source();
    const uint32_t frame = cpu.esp;
    cpu.edx = run.get(frame + 12);
    cpu.ecx = run.get(frame + 4);
    if (!cpu.edx) {
        cpu.eflags = 0x46u;
        return run.get(frame + 4);
    }
    cpu.eax = run.get8(frame + 8);
    cpu.esp -= 4;
    run.put(cpu.esp, cpu.edi);
    cpu.edi = cpu.ecx;
    uint32_t carry = 1;
    if (cpu.edx >= 4) {
        cpu.ecx = (0u - cpu.ecx) & 3u;
        cpu.edx -= cpu.ecx;
        while (cpu.ecx) {
            run.put8(cpu.edi, uint8_t(cpu.eax));
            ++cpu.edi;
            --cpu.ecx;
        }
        cpu.ecx = cpu.eax;
        cpu.eax = (cpu.eax << 8) + cpu.ecx;
        cpu.ecx = cpu.eax;
        cpu.eax = (cpu.eax << 16) + cpu.ecx;
        cpu.ecx = cpu.edx;
        cpu.edx &= 3u;
        carry = (cpu.ecx >> 1) & 1u;
        cpu.ecx >>= 2;
        if (cpu.ecx) {
            while (cpu.ecx) {
                run.put(cpu.edi, cpu.eax);
                cpu.edi += 4;
                --cpu.ecx;
            }
            // The subsequent tail test clears carry after any word stores.
            carry = 0;
        }
    }
    while (cpu.edx) {
        run.put8(cpu.edi, uint8_t(cpu.eax));
        ++cpu.edi;
        --cpu.edx;
    }
    // A terminating byte decrement (1 -> 0) retains carry; a zero-tail
    // logical test produces the same other arithmetic flags.
    cpu.eflags = 0x46u | carry;
    cpu.eax = run.get(cpu.esp + 8);
    cpu.edi = run.get(cpu.esp);
    cpu.esp += 4;
    return cpu.eax;
}

} // namespace

CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_crt_byte_fill_entry, owned, contract, optional, body, source_body)
