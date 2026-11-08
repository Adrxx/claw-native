#include "InterfaceReadCompositionRuntime.h"
extern "C" uint32_t claw_interface_read_composition_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                          ClawInterfaceReadContext *c, ClawInterfaceReadDependency d,
                                                          void *u, uint32_t *out) {
    return claw_interface_file_entry(f, t, a, n, c, d, u, out);
}
extern "C" uint32_t claw_interface_read_memory(uint32_t t, const ClawInterfaceMemoryLoad *p,
                                               ClawInterfaceReadContext *c, ClawInterfaceReadDependency d, void *u,
                                               uint32_t *out) {
    if (!p) {
        if (out)
            *out = 0;
        if (c)
            c->fault = 3;
        return 0;
    }
    const uint32_t a[] = {p->graphics,    p->bytes,       p->length,     p->imageResolver,
                          p->trailing[0], p->trailing[1], p->trailing[2]};
    return claw_interface_file_entry(0x4dcdf0, t, a, 7, c, d, u, out);
}
extern "C" uint32_t claw_interface_read_file(uint32_t t, const ClawInterfaceFileLoad *p, ClawInterfaceReadContext *c,
                                             ClawInterfaceReadDependency d, void *u, uint32_t *out) {
    if (!p) {
        if (out)
            *out = 0;
        if (c)
            c->fault = 3;
        return 0;
    }
    const uint32_t a[] = {p->graphics, p->file, p->imageResolver, p->trailing[0], p->trailing[1], p->trailing[2]};
    return claw_interface_file_entry(0x4dcd10, t, a, 6, c, d, u, out);
}
