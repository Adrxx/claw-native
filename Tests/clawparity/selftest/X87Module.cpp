// Independent synthetic client of the canonical register-argument bridge.
#include "ClawRuntime.hpp"

namespace {
int owned(uint32_t function) {
    return function == 0x401080 ? 2 : -1;
}
uint32_t body(claw::Run &run, uint32_t, uint32_t, const uint32_t *arguments) {
    double operand = run.getd(arguments[0]);
    (void)operand;
#ifdef SELFTEST_X87_WRONG_OPERAND
    operand += 0.125;
#endif
#ifdef SELFTEST_X87_WRONG_MEMORY
    run.put(arguments[0] + 12, 1);
#endif
#ifdef SELFTEST_X87_MISSING
    return run.call(arguments[1], 0);
#else
    return run.call_x87(arguments[1], 0, operand);
#endif
}
}
CLAW_MODULE_ENTRY(claw_x87_selftest_entry, owned, body)


namespace {
int exact_owned(uint32_t function) { return function == 0x401090 ? 3 : -1; }
uint32_t exact_body(claw::Run &run, uint32_t, uint32_t, const uint32_t *args) {
    auto state = run.load<ClawX87State>(args[0]);
    const uint32_t value = run.call_x87_exact(args[1], 0, state);
    run.store(args[2], state);
    return value;
}
}
CLAW_MODULE_ENTRY(claw_x87_exact_selftest_entry, exact_owned, exact_body)

namespace {
int stack_result_owned(uint32_t f) { return f == 0x4010d0 ? 6 : -1; }
uint32_t stack_result_body(claw::Run &run, uint32_t, uint32_t, const uint32_t *a) {
    auto fp = run.load<ClawX87State>(a[0]);
    const uint32_t value = run.call_x87_exact(a[1], a[5], fp, {a[2], a[3]});
    run.store(a[4], fp);
    return value;
}
}
CLAW_MODULE_ENTRY(claw_x87_stack_result_selftest_entry, stack_result_owned, stack_result_body)

namespace {
int arithmetic_owned(uint32_t f) { return f == 0x4010a0 ? 4 : -1; }
uint32_t arithmetic_body(claw::Run &r, uint32_t, uint32_t, const uint32_t *a) {
    ClawX87State fp{};
    fp.size = sizeof(fp); fp.version = CLAW_X87_VERSION; fp.control = a[3];
    uint32_t output = a[2];
    auto call = [&](uint32_t target, uint32_t pop, uint32_t push) {
        fp.popCount = pop; fp.pushCount = push; fp.returned = fp.eax = fp.edx = 0;
        r.store(output, fp); output += sizeof(fp);
        const uint32_t result = r.call_x87_exact(target, 0, fp);
        r.store(output, fp); output += sizeof(fp);
        return result;
    };
    auto two = [&]() { r.x87_step(CLAW_X87_F64, fp, {0, 0x40000000}); };
    auto logarithm = [&](uint32_t n) {
        r.x87_step(CLAW_X87_LN2, fp);
        r.x87_step(CLAW_X87_I32, fp, {n});
        r.x87_step(CLAW_X87_YL2X, fp);
        r.x87_step(CLAW_X87_DIV_ST1, fp);
        return call(0x4a30e0, 1, 0);
    };
    r.x87_step(CLAW_X87_LN2, fp);
    two(); r.x87_step(CLAW_X87_YL2X, fp);
    const uint32_t width = logarithm(a[0]), height = logarithm(a[1]);
    r.x87_step(CLAW_X87_POP, fp);
    for (auto exponent : {width, height}) {
        two(); r.x87_step(CLAW_X87_I32, fp, {exponent});
        call(0x4f1b30, 2, 1);
        call(0x4a30e0, 1, 0);
    }
    return fp.eax;
}
}
CLAW_MODULE_ENTRY(claw_x87_arithmetic_selftest_entry, arithmetic_owned, arithmetic_body)

namespace {
int step_owned(uint32_t f) { return f == 0x4010b0 ? 5 : -1; }
uint32_t step_body(claw::Run &r, uint32_t, uint32_t, const uint32_t *a) {
    auto fp = r.load<ClawX87State>(a[0]);
    if (a[1] == CLAW_X87_I32) r.x87_step(a[1], fp, {a[2]});
    else if (a[1] == CLAW_X87_F64 || a[1] == CLAW_X87_SUBR_F64 ||
             a[1] == CLAW_X87_MUL_F64 || a[1] == CLAW_X87_DIV_F64 ||
             a[1] == CLAW_X87_ADD_F64)
        r.x87_step(a[1], fp, {a[2], a[3]});
    else r.x87_step(a[1], fp);
    r.store(a[4], fp);
    return 0;
}
}
CLAW_MODULE_ENTRY(claw_x87_step_selftest_entry, step_owned, step_body)

namespace {
// Test-only client: select owned arithmetic here; both CRT calls stay original.
int volume_owned(uint32_t f) { return f == 0x4010c0 ? 3 : -1; }
uint32_t volume_body(claw::Run &r, uint32_t, uint32_t, const uint32_t *a) {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    uint32_t output = a[2];
    auto save = [&]() { r.store(output, fp); output += sizeof(fp); };
    auto memory = [&](uint32_t op, uint32_t index) {
        r.x87_step(op, fp, {r.get(a[1] + index * 8), r.get(a[1] + index * 8 + 4)});
    };
    auto call = [&](uint32_t target, uint32_t pop, uint32_t push) {
        fp.popCount = pop;
        fp.pushCount = push;
        fp.returned = fp.eax = fp.edx = 0;
        r.call_x87_exact(target, 0, fp);
        save();
    };
    const bool negative = claw::s32(a[0]) < 0;
    const uint32_t magnitude = negative ? 0u - a[0] : a[0];
    const int32_t quotient = claw::s32(magnitude) / 100;
    memory(CLAW_X87_F64, 3);
    r.x87_step(CLAW_X87_I32, fp, {uint32_t(quotient)});
    r.x87_step(CLAW_X87_ROUND_F64, fp);
    save();
    r.x87_step(CLAW_X87_CHS, fp);
    save();
    memory(CLAW_X87_DIV_F64, 2);
    save();
    call(0x4f1b30, 2, 1);
    memory(CLAW_X87_SUBR_F64, 1);
    save();
    memory(CLAW_X87_MUL_F64, 0);
    save();
    memory(CLAW_X87_SUBR_F64, 0);
    save();
    r.x87_step(CLAW_X87_ROUND_F64, fp);
    save();
    if (!negative) r.x87_step(CLAW_X87_CHS, fp);
    save();
    call(0x4a30e0, 1, 0);
    return fp.eax;
}
}
CLAW_MODULE_ENTRY(claw_x87_volume_selftest_entry, volume_owned, volume_body)

namespace {
// Register-indexed, compare and m64 store primitives. a[5] is the operand word count.
int register_owned(uint32_t f) { return f == 0x4010e0 ? 6 : -1; }
uint32_t register_body(claw::Run &r, uint32_t, uint32_t, const uint32_t *a) {
    auto fp = r.load<ClawX87State>(a[0]);
    uint64_t bits = 0;
    if (a[5] == 2) bits = r.x87_step(a[1], fp, {a[2], a[3]});
    else if (a[5] == 1) bits = r.x87_step(a[1], fp, {a[2]});
    else bits = r.x87_step(a[1], fp);
    if (bits != (uint64_t(fp.edx) << 32 | fp.eax)) r.fail(CLAW_FAULT_ABI);
    r.store(a[4], fp);
    return 0;
}
}
CLAW_MODULE_ENTRY(claw_x87_register_selftest_entry, register_owned, register_body)
