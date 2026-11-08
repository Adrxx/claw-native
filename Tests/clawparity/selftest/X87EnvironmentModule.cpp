// Independent harness clients. Synthetic owners and an original-callee transport probe.
#include "ClawRuntime.hpp"

namespace {
constexpr uint32_t DIRECT = 0x401000, FACTORY = 0x401040;
constexpr uint32_t BALANCED = 0x401200, CONVERT = 0x401240;
int owned(uint32_t f) {
    return f == DIRECT || f == FACTORY || f == 0x401080 || f == 0x4010c0 || f == 0x4dca5c ? 2 : -1;
}
uint32_t body(claw::Run &run, uint32_t function, uint32_t receiver, const uint32_t *a) {
    auto fp = run.x87_entry(function);
    if (function == 0x4010c0) {
        run.x87_finish(function, fp);
        return 0;
    }
    if (function == 0x401080) {
        run.x87_step(CLAW_X87_F64, fp, {a[0], a[1]});
        run.x87_step(CLAW_X87_ADD_F64, fp, {0, 0x3ff00000});
        const auto value = run.x87_step(CLAW_X87_STP_F64, fp);
        run.x87_finish(function, fp);
        return static_cast<uint32_t>(value);
    }
    if (function == 0x4dca5c) {
        fp.popCount = fp.pushCount = 0;
        const auto value = run.call_x87_exact(0x403b40, receiver, fp, {a[0], a[1]});
        run.x87_finish(function, fp);
        return value;
    }
    const auto mode = a[0];
    if (mode == 1) fp.status = 0; // loses inherited flags at the first boundary
    if (mode == 9) fp = run.x87_entry(function);
    fp.popCount = fp.pushCount = 0;
    run.call_x87_exact(BALANCED, 0, fp);
    if (mode == 2) fp.status = 0x100; // fitted constant loses actual post-callee flags
    run.x87_step(CLAW_X87_I32, fp, {a[1]});
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = fp.eax = fp.edx = 0;
    const auto value = run.call_x87_exact(CONVERT, 0, fp);
    switch (mode) {
    case 3: fp.status ^= 0x20; break;
    case 4: return value;
    case 7: fp.status ^= 0x800; break;
    case 8: fp.control ^= 0x400; break;
    case 10: run.x87_step(CLAW_X87_I32, fp, {1}); break;
    case 11: fp.slots[7].significand = 1; break;
    case 12: run.x87_step(CLAW_X87_I32, fp, {1}); run.x87_return(function, fp); return value;
    default: break;
    }
    run.x87_finish(mode == 13 ? FACTORY : function, fp);
    if (mode == 5) run.x87_finish(function, fp);
    if (mode == 6) run.x87_step(CLAW_X87_I32, fp, {1});
    return mode == 14 ? value ^ 1 : value;
}
}
CLAW_MODULE_ENTRY(claw_x87_environment_selftest_entry, owned, body)
