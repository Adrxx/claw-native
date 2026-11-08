// Level 1 registration wrappers. Callback addresses are stored as data.
#include "ClawRuntime.hpp"
#include "LogicStateRegistryCoreRuntime.h"

namespace {
using claw::Run;
using claw::state_registry::registerBinding;

int owned(uint32_t function) {
    switch (function) {
    case 0x474060:
    case 0x4748f0:
    case 0x47ce80:
    case 0x47dc30:
    case 0x47e9f0:
    case 0x47f910:
    case 0x483290:
    case 0x4844f0:
    case 0x4849f0:
    case 0x485a70:
    case 0x4874b0:
        return 0;
    default:
        return -1;
    }
}

// Parent checks compare NUL-terminated unsigned byte strings.
bool equal(Run &run, uint32_t first, uint32_t second) {
    for (;;) {
        const auto byte = run.get8(first++);
        if (byte != run.get8(second++))
            return false;
        if (!byte)
            return true;
    }
}

// 0x474060: projectile falling registration.
void registerProjectile(Run &run) {
    registerBinding(run, 0x538428, 0x5236fc, 0x4742f0, 0, 0, 0x4740fb, 0x4741c4);
}

uint32_t body(Run &run, uint32_t function, uint32_t, const uint32_t *) {
    switch (function) {
    case 0x474060:
        registerProjectile(run);
        return 0;
    // 0x4748f0: PunkRat.
    case 0x4748f0:
        if (!equal(run, 0x52670c, 0x52a7a0))
            run.call(0x43d5b0, 0);
        registerBinding(run, 0x538458, 0x5271e4, 0x474d00, 1, 1);
        registerBinding(run, 0x538458, 0x5271f4, 0x474c50, 1, 1);
        registerBinding(run, 0x538458, 0x52720c, 0x474db0, 1, 1);
        registerBinding(run, 0x538458, 0x52a794, 0x474e60, 0, 1, 1);
        return 0;
    // 0x47ce80: Rat.
    case 0x47ce80:
        if (!equal(run, 0x52670c, 0x52b0bc))
            run.call(0x43d5b0, 0);
        registerBinding(run, 0x53c0e8, 0x5234ec, 0x47d1b0, 1, 1);
        registerBinding(run, 0x53c0e8, 0x5271e4, 0x47d490, 1, 1);
        registerBinding(run, 0x53c0e8, 0x5271f4, 0x47d470, 1, 1);
        registerBinding(run, 0x53c0e8, 0x52b0b0, 0x47d660, 0, 1, 1);
        return 0;
    // 0x47dc30: RatBomb, including its owned projectile parent.
    case 0x47dc30:
        if (!equal(run, 0x523708, 0x52b160))
            registerProjectile(run);
        registerBinding(run, 0x53c118, 0x5236fc, 0x47e180, 0, 0, 1, 1);
        registerBinding(run, 0x53c118, 0x524418, 0x47dfc0, 0, 0, 0x47de36, 1);
        return 0;
    // 0x47e9f0: RedTail.
    case 0x47e9f0:
        if (!equal(run, 0x523274, 0x52b2fc))
            run.call(0x40e390, 0);
        registerBinding(run, 0x53c148, 0x5234ec, 0x47f160, 1, 1);
        registerBinding(run, 0x53c148, 0x523148, 0x47f0c0, 1, 1);
        registerBinding(run, 0x53c148, 0x52874c, 0x47f600, 1, 1);
        registerBinding(run, 0x53c148, 0x523210, 0x47f680, 1, 1);
        registerBinding(run, 0x53c148, 0x523204, 0x47f6b0, 1, 1);
        return 0;
    // 0x47f910: RedTail boss; the last name uses 0x406020.
    case 0x47f910:
        if (!equal(run, 0x523274, 0x52b3cc))
            run.call(0x40e390, 0);
        registerBinding(run, 0x53c178, 0x527d84, 0x482620, 1, 1);
        registerBinding(run, 0x53c178, 0x52b3c0, 0x481c10, 1, 1);
        registerBinding(run, 0x53c178, 0x52b3b4, 0x481f70, 1, 1);
        registerBinding(run, 0x53c178, 0x523268, 0x4441b0, 1, 1);
        registerBinding(run, 0x53c178, 0x526a38, 0x482180, 1, 1);
        registerBinding(run, 0x53c178, 0x5234ec, 0x4806c0, 1, 1);
        registerBinding(run, 0x53c178, 0x52b3a4, 0x480c40, 1, 1);
        registerBinding(run, 0x53c178, 0x52b394, 0x480f20, 1, 1);
        registerBinding(run, 0x53c178, 0x52b384, 0x481180, 1, 1);
        registerBinding(run, 0x53c178, 0x52b374, 0x481400, 1, 1);
        registerBinding(run, 0x53c178, 0x52b364, 0x481720, 1, 1);
        registerBinding(run, 0x53c178, 0x5234f4, 0x482260, 2, 1);
        return 0;
    // 0x483290: RedTailPirate.
    case 0x483290:
        if (!equal(run, 0x523a5c, 0x52ba9c))
            run.call(0x44c950, 0);
        registerBinding(run, 0x53c1a8, 0x523148, 0x435130, 1, 1);
        registerBinding(run, 0x53c1a8, 0x5234ec, 0x4837b0, 1, 1);
        registerBinding(run, 0x53c1a8, 0x526a38, 0x483dc0, 1, 1);
        registerBinding(run, 0x53c1a8, 0x52ba88, 0x483f30, 0, 1, 1);
        return 0;
    // 0x4844f0: effect idle.
    case 0x4844f0:
        registerBinding(run, 0x53c1d8, 0x523604, 0x42a680, 0, 0, 0x48458b, 0x484654);
        return 0;
    // 0x4849f0: idle and blow effects.
    case 0x4849f0:
        registerBinding(run, 0x53c208, 0x523604, 0x484e10, 0, 0, 1, 1);
        registerBinding(run, 0x53c208, 0x52bb28, 0x484ea0, 0, 0, 0x484bb8, 1);
        return 0;
    // 0x485a70: RobberThief.
    case 0x485a70:
        if (!equal(run, 0x523a5c, 0x52bdc0))
            run.call(0x44c950, 0);
        registerBinding(run, 0x53c238, 0x5234ec, 0x485d90, 0, 0, 1, 1);
        registerBinding(run, 0x53c238, 0x524548, 0x486090, 0, 0, 0x485c76, 1);
        return 0;
    // 0x4874b0: Seagull.
    case 0x4874b0:
        if (!equal(run, 0x52bf8c, 0x52bf9c))
            run.call(0x43d5b0, 0);
        registerBinding(run, 0x53c270, 0x523148, 0x4879a0, 1, 1);
        registerBinding(run, 0x53c270, 0x52720c, 0x487f20, 1, 1);
        registerBinding(run, 0x53c270, 0x52bf80, 0x488330, 1, 1);
        registerBinding(run, 0x53c270, 0x529bb8, 0x488420, 1, 1);
        registerBinding(run, 0x53c270, 0x5234f4, 0x488750, 1, 1);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_logic_state_registrations_06_entry, owned, body)
