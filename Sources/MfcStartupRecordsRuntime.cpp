// Original MFC startup record constructors and list linkage
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x501f01:
        return 0;
    case 0x501fde:
        return 1;
    case 0x502f26:
        return 1;
    default:
        return -1;
    }
}

// 0x501f01. Initializes the thread record and returns its receiver.
uint32_t function_501f01(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // +0xd4 and +0x104 are invalid-handle fields; +0 is the vtable.
    run.put(receiver + 0xd4, 0xffffffffu);
    run.put(receiver + 0x104, 0xffffffffu);
    run.put(receiver, 0x5101ec);
    return receiver;
}

// 0x501fde. Initializes the module record and returns its receiver.
uint32_t function_501fde(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // +0x1c through +0x28 are embedded record fields.
    run.put(receiver + 0x1c, 0);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x24, 0);
    run.put(receiver + 0x28, 0);
    // +0x103c and +0x1040 are embedded container fields.
    run.put(receiver + 0x103c, 0);
    run.put(receiver + 0x1040, 0);
    // +0x104c is an invalid-handle field.
    run.put(receiver + 0x104c, 0xffffffffu);
    // +0x1050, +0x1064 and +0x1068 are embedded state fields.
    run.put(receiver + 0x1050, 0);
    run.put(receiver + 0x1064, 0);
    run.put(receiver + 0x1068, 0);
    uint8_t flag = uint8_t(arguments[0]);
    // +0 is the vtable; the initialized embedded sizes are 0x1c and 0x14.
    run.put(receiver, 0x5101fc);
    run.put(receiver + 0x28, 0x1c);
    run.put(receiver + 0x20, 0x14);
    // +0x18 is a word and +0x14 is the byte flag; adjacent bytes survive.
    run.put16(receiver + 0x18, 0);
    run.put8(receiver + 0x14, flag);
    // +0x30 is initial enabled state; +0x1040 is the embedded size.
    run.put(receiver + 0x30, 1);
    run.put(receiver + 0x1040, 0x18);
    return receiver;
}

// 0x502f26. thiscall, 1 stack argument(s), returns void.
uint32_t function_502f26(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // +4 is the node link offset; +0 is the list head.
    uint32_t linkOffset = run.get(receiver + 4);
    uint32_t node = arguments[0];
    uint32_t previous = run.get(receiver);
    run.put(linkOffset + node, previous);
    run.put(receiver, node);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x501f01:
        return function_501f01(run, receiver, arguments);
    case 0x501fde:
        return function_501fde(run, receiver, arguments);
    case 0x502f26:
        return function_502f26(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x501f01:
        return {0x7ff, 0x7ff, 0x472, 0};
    case 0x501fde:
        return {0x7ff, 0x7ff, 0x472, 4};
    case 0x502f26:
        return {0x7ff, 0x7ff, 0x472, 4};
    default:
        return {};
    }
}

bool optional_selector(uint32_t function) {
    return owned(function) >= 0;
}

uint32_t source_body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    if (function != 0x501f01 && function != 0x501fde && function != 0x502f26)
        return body(run, function, receiver, arguments);
    auto &cpu = run.source();
    if (cpu.ecx != receiver)
        run.fail(CLAW_FAULT_ABI, function);
    if (function == 0x502f26) {
        cpu.edx = run.get(cpu.ecx + 4u);
        cpu.eax = run.get(cpu.esp + 4u);
        cpu.esp -= 4u;
        run.put(cpu.esp, cpu.esi);
        cpu.esi = run.get(cpu.ecx);
        run.put(cpu.edx + cpu.eax, cpu.esi);
        run.put(cpu.ecx, cpu.eax);
        cpu.esi = run.get(cpu.esp);
        cpu.esp += 4u;
        // The source wrapper transports machine EAX; ordinary void remains zero.
        return cpu.eax;
    }
    uint32_t result = body(run, function, receiver, arguments);
    // The last arithmetic instruction is OR with -1: SF and PF are set,
    // CF, OF and ZF are clear (the original machine clears AF as well).
    cpu.eflags = 0x86;
    if (function == 0x501fde) {
        // XOR EDX,EDX precedes the stores; LEA followed by MOV CL changes
        // only the low byte of the final embedded-record address.
        cpu.edx = 0;
        cpu.ecx = ((receiver + 0x1048u) & 0xffffff00u) | uint8_t(arguments[0]);
    }
    // Both MOV EAX,ECX entries return the receiver. EBX/ESI/EDI/EBP/FS
    // survive untouched; ESP and EIP are completed by the genuine RET wrapper.
    return result;
}

} // namespace

CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(claw_mfc_startup_records_entry, owned, source_contract,
                                  optional_selector, body, source_body)
