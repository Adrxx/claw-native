// Per-thread application allocation failure policy.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x5022b5:
        return 0;
    case 0x4f63d8:
        return 1;
    default:
        return -1;
    }
}

void copyCPU(ClawSourceContext &to, const ClawSourceContext &from) {
    std::memcpy(&to.eax, &from.eax, 11 * sizeof(uint32_t));
}

void childCall(Run &run, uint32_t target, uint32_t receiver, uint32_t returnPC,
               std::initializer_list<uint32_t> arguments, uint32_t popBytes) {
    auto &context = run.source();
    auto child = context;
    child.preserveMask = 0x400;
    child.eip = target;
    try {
        run.source_call(target, receiver, returnPC, child, arguments, 0, popBytes);
    } catch (...) {
        copyCPU(context, child);
        throw;
    }
    copyCPU(context, child);
}

uint32_t addFlags(uint32_t left, uint32_t right, uint32_t result) {
    uint32_t low = result & 0xff;
    low ^= low >> 4;
    low ^= low >> 2;
    low ^= low >> 1;
    uint32_t flags = 2;
    flags |= uint32_t(uint64_t(left) + right > 0xffffffffu);
    flags |= ((low & 1) ^ 1) << 2;
    flags |= (left ^ right ^ result) & 0x10;
    flags |= uint32_t(result == 0) << 6;
    flags |= (result >> 24) & 0x80;
    flags |= ((~(left ^ right) & (left ^ result)) >> 20) & 0x800;
    return flags;
}

// 0x5022b5. The two children retain their actual source frames and CPU outputs.
uint32_t applicationThreadGet(Run &run) {
    auto &context = run.source();
    context.esp -= 0x4;
    run.put(context.esp, 0x5022ba);
    childCall(run, 0x50228f, 0, 0x5022ba, {}, 0);
    uint32_t previous = context.eax;
    context.eax += 0x1070;
    context.eflags = addFlags(previous, 0x1070, context.eax);
    context.esp -= 0x4;
    run.put(context.esp, 0x502301);
    context.ecx = context.eax;
    context.esp -= 0x4;
    run.put(context.esp, 0x5022cb);
    childCall(run, 0x50335e, context.ecx, 0x5022cb, {0x502301}, 0x4);
    return context.eax;
}

// 0x4f63d8. Application-thread +0x28 is the opaque allocation-handler word.
uint32_t applicationHandlerSet(Run &run) {
    auto &context = run.source();
    context.esp -= 0x4;
    run.put(context.esp, 0x4f63dd);
    context.eip = 0x5022b5;
    applicationThreadGet(run);
    context.eip = run.get(context.esp);
    context.esp += 0x4;
    context.edx = run.get(context.esp + 0x4);
    context.ecx = run.get(context.eax + 0x28);
    run.put(context.eax + 0x28, context.edx);
    context.eax = context.ecx;
    return context.eax;
}

uint32_t body(Run &run, uint32_t function, uint32_t, const uint32_t *) {
    switch (function) {
    case 0x5022b5:
        return applicationThreadGet(run);
    case 0x4f63d8:
        return applicationHandlerSet(run);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x5022b5:
        return {0x7ff, 0x7ff, 0, 0};
    case 0x4f63d8:
        return {0x7ff, 0x7ff, 0, 0x4};
    default:
        return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_application_new_policy_entry, owned, source_contract, body)
