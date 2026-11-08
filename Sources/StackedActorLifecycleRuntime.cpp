#include "StackedActorLifecycleRuntime.h"
namespace {
uint32_t *word(ClawStackedActorLifecycleContext &c, uint32_t t) {
    if (c.fault)
        return nullptr;
    auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, 1) : nullptr;
    if (!p)
        c.fault = 1;
    return p;
}
uint32_t read(ClawStackedActorLifecycleContext &c, uint32_t t) {
    auto *p = word(c, t);
    return p ? *p : 0;
}
void write(ClawStackedActorLifecycleContext &c, uint32_t t, uint32_t v) {
    auto *p = word(c, t);
    if (p)
        *p = v;
}
void call(ClawStackedActorLifecycleContext &c, uint32_t f, uint32_t t, uint32_t count = 0, uint32_t a = 0) {
    if (c.fault)
        return;
    if (!f || !c.scene.call) {
        c.fault = 1;
        return;
    }
    c.scene.call(c.scene.context, {f, t, {a, 0, 0, 0}, count});
}
} // namespace
uint32_t claw_stacked_actor_lifecycle_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                            ClawStackedActorLifecycleContext *cp, uint32_t *result) {
    if (result)
        *result = 0;
    if (!cp)
        return 0;
    auto &c = *cp;
    c.fault = 0;
    uint32_t wanted = 0;
    switch (f) {
    case 0x484d90:
    case 0x4041b0:
    case 0x4041a0:
    case 0x4c9e30:
        wanted = 1;
        break;
    case 0x456030:
    case 0x4c96b0:
    case 0x4bb030:
        break;
    default:
        return 0;
    }
    if (n != wanted || (n && !a)) {
        c.fault = 2;
        return 0;
    }
    switch (f) {
    case 0x484d90:
        write(c, t, 0x50b014);
        if (!c.fault && (a[0] & 1)) {
            if (c.scene.free)
                c.scene.free(c.scene.context, t);
            else
                c.fault = 1;
        }
        if (!c.fault && result)
            *result = t;
        break;
    case 0x456030:
        write(c, t, 0x50b014);
        break;
    case 0x4041b0:
        if (read(c, t + 0x14)) {
            const uint32_t cleanup = read(c, t + 0x18);
            if (cleanup) {
                const uint32_t primary = read(c, t + 0x10);
                const uint32_t state = read(c, primary + 0x1c);
                const uint32_t expected = read(c, t + 0x1c);
                if (!c.fault && state == expected) {
                    call(c, cleanup, t);
                    write(c, t + 0x18, 0);
                }
            }
            const uint32_t queued = read(c, t + 0x14);
            call(c, queued, t);
            write(c, t + 0x14, 0);
            write(c, t + 0x1c, 1001);
        }
        break;
    case 0x4041a0:
        call(c, 0x4a36f0, 0, 1, t);
        break;
    case 0x4c96b0:
    case 0x4c9e30:
    case 0x4bb030:
        break;
    }
    return c.fault ? 0 : 1;
}
