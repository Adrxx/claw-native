#include "BreakableObjectRuntime.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawBreakableContext *c;
    ClawBreakableDependency d;
    void *user;
};
bool bad(Run &r) {
    return r.c->fault != 0;
}

uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    auto &h = r.c->scene;
    auto *p = h.lookup ? h.lookup(h.context, t, n) : nullptr;
    if (!p)
        r.c->fault = 1;
    return p;
}

uint32_t rd(Run &r, uint32_t t) {
    auto *p = span(r, t, 1);
    return p ? *p : 0;
}

void wr(Run &r, uint32_t t, uint32_t v) {
    if (bad(r))
        return;
    auto *p = span(r, t, 1);
    if (p)
        *p = v;
}

void bits(Run &r, uint32_t t, uint32_t b) {
    wr(r, t, rd(r, t) | b);
}

void clear(Run &r, uint32_t t, uint32_t b) {
    wr(r, t, rd(r, t) & ~b);
}

double dbl(Run &r, uint32_t t) {
    double v = 0;
    auto *p = span(r, t, 2);
    if (p)
        std::memcpy(&v, p, 8);
    return v;
}

void number(Run &r, uint32_t t, double v) {
    auto *p = span(r, t, 2);
    if (p && !bad(r))
        std::memcpy(p, &v, 8);
}

uint32_t ftol(double v) {
    uint64_t b;
    std::memcpy(&b, &v, 8);
    const int e = int((b >> 52) & 2047) - 1023;
    if (e < 0 || e >= 63)
        return 0;
    uint64_t m = (b & 0xfffffffffffffULL) | 0x10000000000000ULL;
    m = e >= 52 ? m << (e - 52) : m >> (52 - e);
    return b >> 63 ? 0u - uint32_t(m) : uint32_t(m);
}

uint32_t call(Run &r, uint32_t f, uint32_t recv, std::initializer_list<uint32_t> a = {}, const char *name = nullptr) {
    if (bad(r))
        return 0;
    if (!r.d) {
        r.c->fault = 1;
        return 0;
    }
    ClawBreakableCall e{};
    e.function = f;
    e.receiver = recv;
    e.argumentCount = uint32_t(a.size());
    e.name = name;
    std::copy(a.begin(), a.end(), e.arguments);
    return uint32_t(r.d(r.c, &e, r.user));
}

uint32_t vc(Run &r, uint32_t t, uint32_t slot) {
    return call(r, rd(r, rd(r, t) + slot), t);
}

void rect(Run &r, uint32_t t, uint32_t l, uint32_t top, uint32_t right, uint32_t bottom) {
    wr(r, t, l);
    wr(r, t + 4, top);
    wr(r, t + 8, right);
    wr(r, t + 12, bottom);
}

void imageRect(Run &r, uint32_t image, uint32_t t) {
    rect(r, t, rd(r, image + 0x20) - rd(r, image + 0x18), rd(r, image + 0x24) - rd(r, image + 0x1c),
         rd(r, image + 0x20) + rd(r, image + 0x18) - 1, rd(r, image + 0x24) + rd(r, image + 0x1c) - 1);
}

uint32_t image(Run &r, uint32_t manager, uint32_t id) {
    if (int32_t(id) < int32_t(rd(r, manager + 0x64)) || int32_t(rd(r, manager + 0x68)) < int32_t(id))
        return 0;
    return rd(r, rd(r, manager + 0x14) + id * 4);
}

void sound(Run &r, uint32_t manager, uint32_t name) {
    if (rd(r, manager + 0x30))
        return;
    const uint32_t root = call(r, 0x4f6286, manager + 0x10, {name});
    if (root && r.c->globals->audioEnabled)
        call(r, 0x4b45f0, rd(r, root + 0x10), {r.c->globals->audioPosition, 0, 0, 0});
}

uint32_t single(Run &r, uint32_t a) {
    const uint32_t l = rd(r, a + 0x6c);
    switch (rd(r, l + 0x1c)) {
    case 0: {
        wr(r, l + 0x168, 0);
        wr(r, l + 0x130, 0);
        uint32_t im = rd(r, a + 0x170);
        if (im) {
            uint32_t id = rd(r, im + 0x64);
            wr(r, a + 0x16c, id);
            wr(r, a + 0x174, call(r, 0x40f680, im, {id}));
        }
        wr(r, a + 0xd0, 0x200);
        wr(r, a + 0xd4, 0x3000072);
        call(r, 0x4c7fa0, a, {0x5228dc}, "CrateHit");
        uint32_t i = rd(r, a + 0x174);
        if (i)
            imageRect(r, i, a + 0x128);
        if (!rd(r, a + 0x64)) {
            wr(r, a + 0x64, rd(r, l + 0x10) == 0x471720 ? 5000 : 1100);
            bits(r, a + 8, 0x20000);
        }
        if (int32_t(rd(r, a + 0x10c)) > 998)
            bits(r, a + 8, 5);
        else
            wr(r, a + 0x10c, 1 + (int32_t(rd(r, a + 0x10c)) > 1));
        wr(r, l + 0x1c, 5);
        break;
    }
    case 5: {
        uint32_t remaining = rd(r, l + 0x130);
        if (remaining)
            wr(r, l + 0x130, r.c->globals->animationDelta < remaining ? remaining - r.c->globals->animationDelta : 0);
        call(r, 0x4c82a0, a + 0x188, {r.c->globals->animationDelta});
        break;
    }
    case 10:
        wr(r, l + 0x1c, 5);
        if (rd(r, l + 0x64))
            bits(r, a + 8, 0x10000);
        break;
    case 31:
        call(r, 0x4c82a0, a + 0x188, {r.c->globals->animationDelta});
        if (rd(r, a + 0x1a4) && !rd(r, a + 0x19c))
            wr(r, l + 0x1c, 10);
        break;
    default:
        break;
    }
    return 1;
}

uint32_t singleHit(Run &r, uint32_t a) {
    const uint32_t l = rd(r, a + 0x6c), att = rd(r, a + 0x74);
    if (rd(r, att + 0xd0) == 0x20)
        bits(r, att + 8, 0x10000);
    if (rd(r, l + 0x130))
        return 1;
    uint32_t hp = rd(r, a + 0x10c) - 1;
    wr(r, a + 0x10c, hp);
    if (int32_t(hp) < 1) {
        call(r, 0x4c79e0, a, {0x5266b8, 0}, "LEVEL_CRATEBREAK");
        bits(r, a + 8, 4);
        wr(r, l + 0x1c, 31);
        const uint32_t z = rd(r, l + 0x64) ? rd(r, a + 0x64) - 1 : rd(r, l + 0x54) + rd(r, a + 0x64),
                       y = rd(r, a + 0x50) - 24;
        if (rd(r, l + 0x64))
            call(r, 0x4735b0, 0, {rd(r, a + 0xc), rd(r, a + 0x4c), y, z, rd(r, a + 0x100)});
        else
            call(r, 0x40f540, 0, {a, rd(r, a + 0x4c), y, z});
        uint32_t random = call(r, 0x4a3050, 0);
        sound(r, rd(r, rd(r, l + 0xc) + 0x28), int32_t(random) % 100 < 50 ? 0x526730 : 0x52671c);
    } else {
        sound(r, rd(r, rd(r, a + 0xc) + 0x28), 0x52a228);
        uint32_t im = rd(r, a + 0x170);
        if (im) {
            uint32_t id = rd(r, a + 0x16c) + 1;
            wr(r, a + 0x16c, id);
            wr(r, a + 0x174, image(r, im, id));
            if (!rd(r, a + 0x174)) {
                id = rd(r, im + 0x64);
                wr(r, a + 0x16c, id);
                wr(r, a + 0x174, image(r, im, id));
            }
        }
        wr(r, l + 0x130, 500);
    }
    return 1;
}

void bitSet(Run &r, uint32_t e, uint32_t index) {
    uint32_t n = rd(r, e + 0x2fc);
    if (n <= index) {
        call(r, 0x4dbd20, e + 0x2f4, {index});
        return;
    }
    uint32_t t = n <= 32 ? e + 0x300 : rd(r, e + 0x300);
    bits(r, t + (index / 32) * 4, 1u << (index & 31));
}

uint32_t sequence(Run &r, uint32_t e, uint32_t name) {
    uint32_t t = call(r, 0x4062e0, e + 0x128, {name});
    return t ? t : call(r, 0x4062e0, e + 0x128, {0x5234b4}, "GAME_NULL");
}

uint32_t construct(Run &r, uint32_t e, uint32_t a, bool keg) {
    call(r, 0x4332f0, e, {a});
    if (bad(r))
        return 0;
    uint32_t bound = rd(r, e + 0x12c);
    if (keg) {
        wr(r, e + 0x400, 0);
        wr(r, e + 0x404, 0);
        wr(r, e, 0x50edd4);
        wr(r, e + 0x2d0, 20);
        call(r, 0x4c7970, bound, {0x52a174}, "LEVEL_POWDERKEG");
        const uint32_t offsets[] = {0x378, 0x37c, 0x380, 0x36c, 0x368},
                       names[] = {0x52a15c, 0x52a144, 0x52a12c, 0x52a12c, 0x52a114};
        for (unsigned i = 0; i < 5; ++i)
            wr(r, e + offsets[i], sequence(r, e, names[i]));
        wr(r, e + 0x3b8, call(r, 0x4061b0, rd(r, rd(r, bound + 0xc) + 0x28), {0x52a104}, "LEVEL_KEGBOOM"));
        wr(r, e + 0x408, 0);
        const uint32_t vals[] = {10, uint32_t(-10), uint32_t(-105), uint32_t(-30), 30, uint32_t(-70)};
        for (unsigned i = 0; i < 6; ++i)
            wr(r, e + 0x2b4 + i * 4, vals[i]);
        call(r, 0x4209d0, bound, {9});
        rect(r, e + 0x220, uint32_t(-42), uint32_t(-15), 45, 60);
        rect(r, e + 0x210, 0x80000000, uint32_t(-20), 20, 20);
        call(r, 0x4209d0, bound, {1});
        rect(r, e + 0x250, uint32_t(-20), 23, 19, 60);
        rect(r, e + 0x260, uint32_t(-24), 25, 24, 64);
        call(r, 0x40f6c0, bound, {rd(r, e + 0x250), rd(r, e + 0x254), rd(r, e + 0x258), rd(r, e + 0x25c)});
        call(r, 0x406240, bound);
        uint32_t own = rd(r, e + 0xc);
        wr(r, own + 0x104, 20);
        wr(r, own + 0x104, ftol(double(int32_t(rd(r, own + 0x104))) * double(r.c->globals->damageScale)));
        bitSet(r, e, 0);
        bits(r, rd(r, e + 0x12c) + 8, 0x40);
        wr(r, e + 0x124, 8);
        bits(r, rd(r, e + 0x12c) + 0x164, 1);
        bits(r, rd(r, e + 0x12c) + 0x164, 4);
        wr(r, rd(r, e + 0x12c) + 0xd0, 4);
        wr(r, rd(r, e + 0x12c) + 0xd4, 0x1000020);
        wr(r, rd(r, e + 0x12c) + 0x50, rd(r, rd(r, e + 0x12c) + 0x50) - 32);
        call(r, 0x4cd800, rd(r, rd(r, rd(r, e + 0x128) + 0xc) + 0x24), {rd(r, e + 0x128), 0});
        wr(r, rd(r, e + 0x128) + 0xcc, 1);
        wr(r, e + 0x24, rd(r, rd(r, e + 0x10) + 0x1c));
        wr(r, rd(r, e + 0x10) + 0x1c, call(r, 0x4dba00, 0x537668, {0x523148}, "LS_IDLE"));
    } else {
        wr(r, e, 0x50c77c);
        call(r, 0x4c7970, bound, {0x5266cc}, "LEVEL_CRATES");
        bitSet(r, e, 1);
        wr(r, e + 0x400, 0);
        wr(r, e + 0x404, 0);
        wr(r, e + 0x408, 0);
        call(r, 0x406290, bound);
        rect(r, rd(r, e + 0x12c) + 0x128, uint32_t(-20), uint32_t(-20), 20, 20);
        rect(r, e + 0x220, 0x80000000, 0, 0, 0);
        rect(r, e + 0x210, 0x80000000, 0, 0, 0);
        wr(r, rd(r, e + 0x12c) + 0xd0, 0x200);
        wr(r, rd(r, e + 0x12c) + 0xd4, 0x3000072);
        uint32_t seq = call(r, 0x4061b0, rd(r, rd(r, bound + 0xc) + 0x2c), {0x5266b8}, "LEVEL_CRATEBREAK");
        if (!seq)
            seq = call(r, 0x4062e0, e + 0x128, {0x5234b4}, "GAME_NULL");
        wr(r, e + 0x410, seq);
        uint32_t own = rd(r, e + 0xc);
        wr(r, own + 0x10c, 1);
        wr(r, own + 0x10c, ftol(double(int32_t(rd(r, own + 0x10c))) * double(r.c->globals->healthScale)));
        for (uint32_t o = 0x50; o <= 0x64; o += 4)
            wr(r, e + o, 0);
        number(r, e + 0x40, 2000);
        number(r, e + 0x108, 500);
        wr(r, own + 0xcc, 7);
        number(r, e + 0xa0, double(int32_t(ftol(dbl(r, e + 0x70)))));
        wr(r, e + 0x24, rd(r, rd(r, e + 0x10) + 0x1c));
        wr(r, rd(r, e + 0x10) + 0x1c, call(r, 0x4dba00, 0x537668, {0x5266f8}, "LS_FALL"));
    }
    return e;
}

uint32_t stacked(Run &, uint32_t, uint32_t, uint32_t);
uint32_t wrapper(Run &r, uint32_t a, uint32_t kind) {
    uint32_t l = rd(r, a + 0x6c), s = rd(r, l + 0x1c);
    if (s == 0) {
        wr(r, l + 0x1c, 1000);
        uint32_t n = kind == 0 ? 0x410 : kind == 1 ? 0x418 : 0x4c;
        uint32_t e = 0;
        if (r.c->scene.allocate)
            e = r.c->scene.allocate(r.c->scene.context, n);
        else
            e = call(r, 0x4f63ec, 0, {n});
        if (e) {
            if (kind < 2)
                construct(r, e, a, kind == 0);
            else
                stacked(r, e, a, kind == 2 ? 5000u : 1000u);
        }
        if (bad(r))
            return 0;
        if (!e) {
            r.c->fault = 1;
            return 0;
        }
        if (kind >= 2)
            wr(r, e, kind == 2 ? 0x50f824 : 0x50f84c);
        vc(r, e, 0x10);
        wr(r, l + 0x18, e);
    } else if (s == 29)
        vc(r, rd(r, l + 0x18), 0x20);
    else if (s == 30)
        vc(r, rd(r, l + 0x18), 0x1c);
    else if (s != 1000)
        call(r, 0x4dc870, 0, {rd(r, l + 0x18)});
    return 1;
}

void inherit(Run &r, uint32_t e, uint32_t a) {
    if (rd(r, a + 0x100) == 32) {
        wr(r, a + 0x148, rd(r, rd(r, e + 0xc) + 0x148));
        uint32_t v = rd(r, rd(r, e + 0xc) + 0x14c);
        wr(r, a + 0xfc, 0x26ae);
        wr(r, a + 0x14c, v);
    }
    for (uint32_t o = 0xf0; o <= 0x10c; o += 4)
        wr(r, rd(r, a + 0x6c) + o, 0);
}

uint32_t stacked(Run &r, uint32_t e, uint32_t a, uint32_t z) {
    wr(r, e, 0x50b064);
    wr(r, e + 8, a);
    wr(r, e + 0xc, a);
    wr(r, e + 0x10, rd(r, a + 0x6c));
    wr(r, e + 4, 0);
    call(r, 0x4c7fa0, a, {0x522d54}, "LogicHit");
    call(r, 0x4c8060, rd(r, e + 0xc), {0x522d48}, "LogicAttack");
    wr(r, e + 0x14, 0);
    wr(r, e + 0x18, 0);
    wr(r, e + 0x1c, 1001);
    wr(r, e + 0x20, 2);
    wr(r, e + 0x28, a);
    wr(r, e + 0x2c, a);
    wr(r, e + 0x30, rd(r, a + 0x6c));
    wr(r, e, 0x50f874);
    uint32_t own = rd(r, e + 0xc);
    if (!rd(r, own + 0x64) && rd(r, own + 0x64) != z) {
        wr(r, own + 0x64, z);
        bits(r, own + 8, 0x20000);
    }
    wr(r, e + 0x48, 0);
    bits(r, rd(r, e + 0x2c) + 8, 1);
    bits(r, rd(r, e + 0x2c) + 0x40, 1);
    uint32_t previous = 0, first = 0;
    for (uint32_t i = 0; i < 9; ++i) {
        uint32_t value;
        if (i == 0) {
            value = rd(r, rd(r, e + 0xc) + 0x100);
            if (!value)
                value = rd(r, rd(r, e + 0x10) + 0xf0);
        } else {
            if (i == 1 && !rd(r, rd(r, e + 0xc) + 0x100))
                continue;
            value = rd(r, rd(r, e + 0x10) + 0xf0 + (i - 1) * 4);
            if (!value)
                continue;
        }

        uint32_t source = rd(r, e + 0x2c), index = rd(r, e + 0x48),
                 aNew = call(r, 0x4c8da0, rd(r, rd(r, rd(r, e + 0x30) + 0xc) + 8),
                             {0, rd(r, source + 0x4c), rd(r, source + 0x50) - index * 40,
                              rd(r, source + 0x64) + 1 + index, 0x522c28, 0x40000},
                             "Crate");
        wr(r, aNew + 0x100, value);
        inherit(r, e, aNew);
        call(r, rd(r, rd(r, aNew + 0x6c) + 0x10), 0, {aNew});
        if (bad(r))
            return 0;
        uint32_t brain = rd(r, rd(r, aNew + 0x6c) + 0x18);
        wr(r, brain + 0x404, previous ? rd(r, rd(r, previous + 0x6c) + 0x18) : 0);
        wr(r, brain + 0x408, rd(r, e + 0x48));
        wr(r, e + 0x48, rd(r, e + 0x48) + 1);
        wr(r, brain + 0x40c, rd(r, rd(r, e + 0xc) + 0x50));
        if (previous)
            wr(r, rd(r, rd(r, previous + 0x6c) + 0x18) + 0x400, brain);
        else
            first = aNew;
        previous = aNew;
    }
    (void)first;
    wr(r, rd(r, rd(r, previous + 0x6c) + 0x18) + 0x400, 0);
    bits(r, rd(r, e + 0x2c) + 8, 0x10000);
    return e;
}
uint32_t lootImage(Run &r, uint32_t index) {
    if (!r.c->loot) {
        r.c->fault = 1;
        return 0;
    }
    if (int32_t(index) < 0 || int32_t(index) >= int32_t(r.c->loot->itemCount))
        return 0;
    if (index >= 341) {
        r.c->fault = 2;
        return 0;
    }
    return r.c->loot->words[index];
}
uint32_t lootCreate(Run &r, const uint32_t *a) {
    uint32_t created = call(r, 0x4c8da0, rd(r, a[0] + 8), {1, a[2], a[3], a[4], 0x522cc0, 0x40000}, "BouncingGoodie");
    if (!created)
        return 0;
    uint32_t manager = call(r, 0x473610, 0, {a[1]});
    if (manager) {
        uint32_t id = rd(r, manager + 0x64);
        wr(r, created + 0x170, manager);
        wr(r, created + 0x174, call(r, 0x40f680, manager, {id}));
        wr(r, created + 0x16c, id);
    }
    call(r, rd(r, rd(r, created + 0x6c) + 0x10), 0, {created});
    if (!r.c->loot) {
        r.c->fault = 1;
        return 0;
    }
    uint32_t vy = a[6], brain;
    if (!r.c->loot->highLaunch) {
        brain = rd(r, rd(r, created + 0x6c) + 0x18);
        number(r, brain + 0x50, double(int32_t(a[5])));
    } else {
        uint32_t random = call(r, 0x4a3050, 0);
        brain = rd(r, rd(r, created + 0x6c) + 0x18);
        number(r, brain + 0x50, double(int32_t(a[5])));
        vy = 0u - uint32_t(int32_t(random) % 1001 + 500);
    }
    number(r, brain + 0x58, double(int32_t(vy)));
    number(r, brain + 0x60, 0);
    number(r, brain + 0x40, 800);
    wr(r, rd(r, rd(r, created + 0x6c) + 0x18) + 0x184, a[1]);
    return created;
}

uint32_t lootOne(Run &r, const uint32_t *a) {
    if (!r.c->loot) {
        r.c->fault = 1;
        return 0;
    }
    if (!r.c->loot->words[340])
        call(r, 0x4719e0, 0, {a[0]});
    uint32_t item = int32_t(a[4]) < 0 ? 0 : a[4];
    if (int32_t(r.c->loot->itemCount) <= int32_t(item) || !lootImage(r, item))
        return 0;
    uint32_t args[] = {a[0], item, a[1], a[2], a[3], 0, uint32_t(-300)};
    return lootCreate(r, args);
}

void lootMany(Run &r, const uint32_t *a) {
    if (!r.c->loot) {
        r.c->fault = 1;
        return;
    }
    uint32_t l = rd(r, a[0] + 0x6c),
             items[] = {rd(r, a[0] + 0x100), rd(r, l + 0xf0),  rd(r, l + 0xf8),  rd(r, l + 0xf4), rd(r, l + 0xfc),
                        rd(r, l + 0x100),    rd(r, l + 0x108), rd(r, l + 0x104), rd(r, l + 0x10c)},
             count = 0;
    for (uint32_t v : items)
        count += v != 0;
    uint32_t vx = uint32_t(int32_t(count * uint32_t(-25)) / 2);
    for (uint32_t item : items) {
        if (int32_t(item) > 0 && int32_t(item) < int32_t(r.c->loot->itemCount) && lootImage(r, item)) {
            uint32_t random = call(r, 0x4a3050, 0),
                     args[] = {
                         rd(r, a[0] + 0xc), item, a[1], a[2], a[3], vx, 0u - uint32_t(int32_t(random) % 301 + 200)};
            lootCreate(r, args);
            vx += 25;
        }
    }
}

uint32_t dispatch(Run &r, uint32_t e, uint32_t state, bool keg) {
    uint32_t *table = keg ? r.c->globals->kegStates : r.c->globals->crateStates;
    const uint32_t token = keg ? 0x537ea0 : 0x537308;
    table[8] = 0;
    auto slot = [&]() -> uint32_t {
        if (int32_t(state) < int32_t(table[2]) || int32_t(table[3]) < int32_t(state)) {
            if (!call(r, 0x4db6e0, token, {state, 0})) {
                r.c->fault = 2;
                return 0;
            }
        }
        return (state - table[2]) * table[6] + table[4];
    };
    uint32_t p = slot();
    if (bad(r))
        return 0;
    if (rd(r, p)) {
        table[8] = 0;
        p = slot();
        if (!bad(r))
            call(r, rd(r, p), e);
    } else
        call(r, 0x43d490, e, {state});
    return 0;
}
} // namespace
extern "C" uint32_t claw_breakable_entry(uint32_t f, uint32_t recv, const uint32_t *a, uint32_t n,
                                         ClawBreakableContext *c, ClawBreakableDependency d, void *u,
                                         uint32_t *result) {
    if (result)
        *result = 0;
    if (!c || !c->globals)
        return 0;
    uint32_t required;
    switch (f) {
    case 0x473610:
        required = 1;
        break;
    case 0x40f450:
        required = 7;
        break;
    case 0x4735b0:
        required = 5;
        break;
    case 0x40f540:
        required = 4;
        break;
    case 0x46f1e0:
    case 0x433070:
    case 0x48d560:
    case 0x48d620:
    case 0x471720:
    case 0x471750:
    case 0x471530:
    case 0x4717e0:
    case 0x46f2a0:
    case 0x433130:
    case 0x48de40:
    case 0x46fc90:
    case 0x433f70:
    case 0x46f6a0:
    case 0x433ad0:
    case 0x46f5b0:
    case 0x4339e0:
        required = 1;
        break;
    case 0x48d6e0:
        required = 2;
        break;
    case 0x46fc60:
    case 0x46fbe0:
    case 0x46fa90:
    case 0x46fc20:
    case 0x434050:
    case 0x433ed0:
    case 0x433f30:
    case 0x433fb0:
    case 0x434170:
    case 0x434180:
    case 0x46f5d0:
    case 0x433a00:
        required = 0;
        break;
    default:
        return 0;
    }
    if (n != required || (n && !a)) {
        c->fault = 2;
        return 0;
    }
    Run r{c, d, u};
    if (bad(r))
        return 0;
    uint32_t value = 0;
    switch (f) {
    case 0x473610:
        value = lootImage(r, a[0]);
        break;
    case 0x40f450:
        value = lootCreate(r, a);
        break;
    case 0x4735b0:
        value = lootOne(r, a);
        break;
    case 0x40f540:
        lootMany(r, a);
        break;
    case 0x471720:
    case 0x471750:
        c->globals->crateImageChoice = f == 0x471720 ? 5 : 4;
        wr(r, rd(r, a[0] + 0x6c) + 0x64, 1);
        value = single(r, a[0]);
        break;
    case 0x471530:
        value = single(r, a[0]);
        break;
    case 0x4717e0:
        value = singleHit(r, a[0]);
        break;
    case 0x46f1e0:
    case 0x433070:
    case 0x48d560:
    case 0x48d620:
        value = wrapper(r, a[0], f == 0x46f1e0 ? 0 : f == 0x433070 ? 1 : f == 0x48d560 ? 2 : 3);
        break;
    case 0x46f2a0:
    case 0x433130:
        value = construct(r, recv, a[0], f == 0x46f2a0);
        break;
    case 0x48d6e0:
        value = stacked(r, recv, a[0], a[1]);
        break;
    case 0x48de40:
        inherit(r, recv, a[0]);
        break;
    case 0x46f6a0:
    case 0x433ad0:
        value = dispatch(r, recv, a[0], f == 0x46f6a0);
        break;
    case 0x46fc60: {
        bits(r, rd(r, recv + 0x12c) + 8, 4);
        uint32_t att = rd(r, rd(r, recv + 0xc) + 0x74);
        if (rd(r, att + 0xd0) == 32)
            bits(r, att + 8, 0x10000);
        vc(r, recv, 0x7c);
        value = 1;
        break;
    }
    case 0x46fc90:
        wr(r, recv + 0x304, a[0]);
        if (a[0] != 2)
            call(r, 0x43f120, recv, {a[0]});
        else {
            bitSet(r, recv, 4);
            vc(r, recv, 0x7c);
        }
        break;
    case 0x46fbe0:
        wr(r, recv + 0x24, rd(r, rd(r, recv + 0x10) + 0x1c));
        wr(r, rd(r, recv + 0x10) + 0x1c, call(r, 0x4dba00, 0x537668, {0x5271b4}, "LS_DROPPED"));
        wr(r, rd(r, recv + 0xc) + 0xcc, 8);
        wr(r, recv + 0xc8, 0);
        break;
    case 0x46fc20:
        call(r, 0x4c82a0, rd(r, recv + 0x12c) + 0x188, {c->globals->animationDelta});
        if (rd(r, rd(r, recv + 0xc) + 0xcc) == 1)
            vc(r, recv, 0x7c);
        break;
    case 0x46fa90: {
        bits(r, rd(r, recv + 0x12c) + 8, 0x80);
        uint32_t step = call(r, 0x4c82a0, rd(r, recv + 0x12c) + 0x188, {c->globals->animationDelta});
        if (step == 1 && !rd(r, recv + 0x1a0)) {
            wr(r, recv + 0x1a0, 1);
            call(r, 0x486e70, 0, {500});
            uint32_t im = rd(r, rd(r, recv + 0x12c) + 0x174);
            if (im)
                imageRect(r, im, recv + 0x220);
            for (uint32_t o = 0; o < 16; o += 4)
                wr(r, rd(r, recv + 0xc) + 0x138 + o, rd(r, recv + 0x220 + o));
            if (rd(r, rd(r, recv + 0x12c) + 0x40) & 2) {
                uint32_t own = rd(r, recv + 0xc), left = rd(r, own + 0x138);
                wr(r, own + 0x138, 0u - rd(r, own + 0x140));
                wr(r, rd(r, recv + 0xc) + 0x140, 0u - left);
            }
            clear(r, rd(r, recv + 0x12c) + 8, 0x80);
        }
        uint32_t own = rd(r, recv + 0x12c);
        if (rd(r, own + 0x1a4) && !rd(r, own + 0x19c))
            bits(r, own + 8, 0x10000);
        break;
    }
    case 0x434050: {
        wr(r, recv + 0x134, rd(r, rd(r, recv + 0x12c) + 0x190));
        call(r, 0x4c8220, rd(r, recv + 0x12c) + 0x188, {rd(r, recv + 0x410)});
        bits(r, rd(r, recv + 0x12c) + 8, 4);
        bits(r, rd(r, recv + 0x12c) + 8, 2);
        vc(r, recv, 0xa8);
        uint32_t att = rd(r, rd(r, recv + 0xc) + 0x74);
        if (rd(r, att + 0xd0) == 32)
            bits(r, att + 8, 0x10000);
        call(r, 0x42df90, recv + 0x128);
        uint32_t random = call(r, 0x4a3050, 0);
        sound(r, rd(r, rd(r, rd(r, recv + 0x10) + 0xc) + 0x28), int32_t(random) % 100 < 50 ? 0x526730 : 0x52671c);
        value = 1;
        break;
    }
    case 0x433ed0:
        wr(r, recv + 0xc8, 1);
        if (rd(r, recv + 0x400))
            wr(r, rd(r, recv + 0x400) + 0x404, rd(r, recv + 0x404));
        if (rd(r, recv + 0x404))
            wr(r, rd(r, recv + 0x404) + 0x400, rd(r, recv + 0x400));
        wr(r, recv + 0x24, rd(r, rd(r, recv + 0x10) + 0x1c));
        wr(r, rd(r, recv + 0x10) + 0x1c, call(r, 0x4dba00, 0x537668, {0x526700}, "LS_DAMAGE"));
        break;
    case 0x433f30:
        call(r, 0x4c82a0, rd(r, recv + 0x12c) + 0x188, {c->globals->animationDelta});
        if (rd(r, rd(r, recv + 0x12c) + 0x1a4) && !rd(r, rd(r, recv + 0x12c) + 0x19c))
            bits(r, rd(r, recv + 0x12c) + 8, 0x10000);
        break;
    case 0x433f70:
        number(r, recv + 0xa0, double(int32_t(a[0])));
        wr(r, recv + 0x24, rd(r, rd(r, recv + 0x10) + 0x1c));
        wr(r, rd(r, recv + 0x10) + 0x1c, call(r, 0x4dba00, 0x537668, {0x5266f8}, "LS_FALL"));
        break;
    case 0x433fb0:
        wr(r, recv + 0xc8, 0);
        bits(r, rd(r, recv + 0x12c) + 8, 2);
        if (!rd(r, recv + 0x404))
            number(r, recv + 0xa0, double(int32_t(rd(r, recv + 0x40c))));
        if (rd(r, recv + 0x400))
            number(r, rd(r, recv + 0x400) + 0xa0, dbl(r, recv + 0x70) - 40);
        if (dbl(r, recv + 0x70) == dbl(r, recv + 0xa0)) {
            if (dbl(r, recv + 0x58) > 200)
                number(r, recv + 0x58, dbl(r, recv + 0x58) * -0.5);
            else {
                number(r, recv + 0x58, 0);
                wr(r, recv + 0xc8, 1);
                clear(r, rd(r, recv + 0x12c) + 8, 2);
            }
        }
        break;
    case 0x434170:
        vc(r, recv, 0xb0);
        break;
    case 0x434180:
        vc(r, recv, 0xac);
        break;
    case 0x46f5d0:
    case 0x433a00:
    case 0x46f5b0:
    case 0x4339e0:
        wr(r, recv, 0x50b16c);
        call(r, 0x4dbcd0, recv + 0x2f4);
        call(r, 0x4f6584, recv + 0x1a8);
        call(r, 0x4f6584, recv + 0x1a4);
        wr(r, recv, 0x50b014);
        if (n) {
            if (a[0] & 1) {
                if (c->scene.free)
                    c->scene.free(c->scene.context, recv);
                else
                    call(r, 0x4f6428, 0, {recv});
            }
            value = recv;
        }
        break;
    default:
        break;
    }
    if (result)
        *result = value;
    return !bad(r);
}
