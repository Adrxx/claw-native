#include "ClawRuntime.hpp"

extern "C" uint32_t claw_v13_boss_damage(uint32_t site, uint32_t supplied, uint32_t zero) {
    switch (site) {
    case 0x48111e:
    case 0x455ba7:
    case 0x4a3cea:
    case 0x4a4941:
    case 0x483521:
        return 5;
    case 0x40508e:
        return 10;
    case 0x4474f1:
        return supplied == zero ? 5 : supplied;
    default:
        return supplied;
    }
}

namespace {

using claw::Run;

bool owned(uint32_t function) {
    switch (function) {
    case 0x48111e:
    case 0x455ba7:
    case 0x4a3cea:
    case 0x40508e:
    case 0x4a4941:
    case 0x4474f1:
    case 0x483521:
        return true;
    default:
        return false;
    }
}

uint32_t compareFlags(uint32_t left, uint32_t right, uint32_t previous) {
    const uint32_t difference = left - right;
    uint32_t parity = difference & 0xff;
    parity ^= parity >> 4;
    parity ^= parity >> 2;
    parity ^= parity >> 1;
    uint32_t flags = previous & ~0x8d5u;
    flags |= left < right ? 0x1u : 0u;
    flags |= (parity & 1) == 0 ? 0x4u : 0u;
    flags |= (left ^ right ^ difference) & 0x10;
    flags |= difference == 0 ? 0x40u : 0u;
    flags |= (difference >> 24) & 0x80;
    flags |= ((left ^ right) & (left ^ difference) & 0x80000000u) >> 20;
    return flags;
}

// The owned v1.3 intervals contain only these stores and the Gabriel CMP/JNE.
void body(Run &run, uint32_t function, ClawCompilerContext &context) {
    switch (function) {
    // 0x48111e, 0x455ba7, 0x4a3cea: outgoing contact damage.
    case 0x48111e:
    case 0x455ba7:
    case 0x4a3cea:
        // +0x120 is the original v1.3 outgoing damage field.
        run.put(context.ecx + 0x120, claw_v13_boss_damage(function, 0, 0));
        break;
    // 0x40508e: Aquatis contact damage.
    case 0x40508e:
        run.put(context.edx + 0x120, claw_v13_boss_damage(function, 0, 0));
        break;
    // 0x4a4941, 0x483521: magic and knife damage.
    case 0x4a4941:
    case 0x483521:
        run.put(context.esi + 0x120, claw_v13_boss_damage(function, 0, 0));
        break;
    // 0x4474f1: preserve supplied damage unless it equals EDI.
    case 0x4474f1: {
        const uint32_t supplied = run.get(context.eax + 0x120);
        context.eflags = compareFlags(supplied, context.edi, context.eflags);
        if (supplied == context.edi) {
            run.put(context.eax + 0x120, claw_v13_boss_damage(function, supplied, context.edi));
        }
        break;
    }
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
    context.eip = context.continuation;
}

} // namespace

CLAW_COMPILER_MODULE_ENTRY(claw_v13_boss_damage_entry, owned, body)
