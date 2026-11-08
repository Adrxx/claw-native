// Level 1 registry search, velocity flip and attack-state shim
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
    case 0x406120:
        return 0;
    case 0x4dc3d0:
        return 1;
    case 0x4dc850:
        return 1;
    case 0x4db5f0:
        return 0;
    default:
        return -1;
    }
}

// 0x406120. thiscall, 0 stack argument(s), returns void.
uint32_t function_406120(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // Object fields: +0x118 and +0x120 are a pair of signed values.
    uint32_t first = run.get(receiver + 0x118);
    if (first == 0x80000000u)
        return 0;
    uint32_t second = run.get(receiver + 0x120);
    uint32_t negatedSecond = 0u - second;
    uint32_t negatedFirst = 0u - first;
    run.put(receiver + 0x118, negatedSecond);
    run.put(receiver + 0x120, negatedFirst);
    return 0;
}

// 0x4dc3d0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4dc3d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // Registry: entries of 12 bytes at 0x544b98 whose first word is the key;
    // 0x544d18 holds the entry count. Receiver +0x04 receives the last probe.
    uint32_t key = arguments[0];
    uint32_t high = run.get(0x544d18) - 1;
    uint32_t low = 0;
    uint32_t middle = 0;
    if (s32(high) >= 0) {
        do {
            uint32_t sum = low + high;
            uint32_t sign = uint32_t(s32(sum) >> 31);
            middle = uint32_t(s32(sum - sign) >> 1);
            run.put(receiver + 0x04, middle);
            uint32_t entry = run.get(0x544b98 + middle * 12);
            uint32_t difference = entry - key;
            if (s32(difference) < 0) {
                low = middle + 1;
            } else {
                if (s32(difference) <= 0)
                    return middle;
                high = middle - 1;
            }
        } while (s32(low) <= s32(high));
    }
    run.put(receiver + 0x04, high + 1);
    return 0xffffffffu;
}

// 0x4dc850. cdecl, 1 stack argument(s), returns u32.
uint32_t function_4dc850(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    // Argument +0x6c holds an object whose +0x18 member is called through
    // its vtable slot +0x18 with no arguments.
    uint32_t owner = run.get(arguments[0] + 0x6c);
    uint32_t target = run.get(owner + 0x18);
    run.vcall(target, 0x18);
    return 1;
}

// 0x4db5f0. cdecl, 0 stack argument(s), returns u32.
uint32_t function_4db5f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    ClawSourceContext &cpu = run.source();
    // 0x4db5f0: pop eax
    cpu.eax = run.get(cpu.esp);
    cpu.esp = cpu.esp + 4;
    // 0x4db5f1: push eax
    cpu.esp = cpu.esp - 4;
    run.put(cpu.esp, cpu.eax);
    // 0x4db5f2: ret is performed by the entry wrapper at the original entry slot.
    cpu.eip = 0x4db5f2;
    return cpu.eax;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x406120:
        return function_406120(run, receiver, arguments);
    case 0x4dc3d0:
        return function_4dc3d0(run, receiver, arguments);
    case 0x4dc850:
        return function_4dc850(run, receiver, arguments);
    case 0x4db5f0:
        return function_4db5f0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x4db5f0: return {1473u, 1473u, 0u, 0u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_level_one_collision_dispatch_04_entry, owned, source_contract, body)
