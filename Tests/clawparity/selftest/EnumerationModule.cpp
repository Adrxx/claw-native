// Independently authored transport controls. No recovered game implementation.
#include "ClawRuntime.hpp"
using claw::Run;

static int owned(uint32_t f) {
    if (f == 0x401000 || f == 0x401100) return 1;
    if (f == 0x401200) return 2;
    return -1;
}

static uint32_t body(Run &run, uint32_t f, uint32_t, const uint32_t *a) {
    if (f == 0x401100) return run.call(0x401000, 0, {a[0]});
    if (f == 0x401000) {
        uint32_t context = a[0];
        run.put(context + 24, run.automatic(4));
        run.call(run.get(context), 0, {run.get(context + 8), 0, 0, context, run.get(context + 4)});
        return run.get(context + 16);
    }
    uint32_t descriptor = a[0];
    uint32_t context = a[1];
    if (run.get(run.automatic(4)) != descriptor || run.get(run.automatic(8)) != context)
        run.fail(CLAW_FAULT_ABI);
#ifdef ENUM_REJECT
    run.fail(CLAW_FAULT_UNIMPLEMENTED, f);
#endif
#ifdef ENUM_FALLBACK
    return run.call(f, 0, {descriptor, context});
#endif
    run.put(context + 16, run.get(context + 16) * 10 + run.get(descriptor));
#ifdef ENUM_MUTANT
    run.put(context + 16, run.get(context + 16) + 1);
#endif
    run.put(run.get(context + 24), 0xface);
    run.call(run.get(context + 28), 0, {descriptor, context});
    return 1;
}

CLAW_MODULE_ENTRY(claw_enumeration_test_entry, owned, body)
