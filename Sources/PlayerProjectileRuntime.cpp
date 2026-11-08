#include "PlayerProjectileRuntime.h"
#include "ActorAnimationRuntime.h"
#include "RawTileDescriptionRuntime.h"
#include "PlayerPhysics.h"
#include <algorithm>
#include <cstring>
#include <cmath>
#include <initializer_list>
#pragma STDC FP_CONTRACT OFF
namespace {
struct Run {
    ClawPlayerProjectileContext &c;
    ClawPlayerProjectileDependency d;
    void *u;
    uint32_t depth = 0;
};
uint32_t execute(Run &, uint32_t, uint32_t, const uint32_t *, uint32_t, uint32_t *);
uint32_t *span(Run &r, uint32_t t, uint32_t n = 1) {
    auto *p = r.c.scene.lookup ? r.c.scene.lookup(r.c.scene.context, t, n) : nullptr;
    if (!p)
        r.c.fault = 1;
    return p;
}
uint32_t rd(Run &r, uint32_t t) {
    auto *p = span(r, t);
    return p ? *p : 0;
}
void wr(Run &r, uint32_t t, uint32_t v) {
    if (auto *p = span(r, t))
        *p = v;
}
double ld(Run &r, uint32_t t) {
    double v = 0;
    if (auto *p = span(r, t, 2))
        std::memcpy(&v, p, 8);
    return v;
}
void st(Run &r, uint32_t t, double v) {
    if (auto *p = span(r, t, 2))
        std::memcpy(p, &v, 8);
}
double add(double a, double b) {
    volatile double v = a + b;
    return v;
}
double sub(double a, double b) {
    volatile double v = a - b;
    return v;
}
double mul(double a, double b) {
    volatile double v = a * b;
    return v;
}
uint32_t ftol(double x) {
    if (!std::isfinite(x) || x >= 0x1p63 || x < -0x1p63)
        return 0;
    return uint32_t(int64_t(x));
}
uint64_t call(Run &r, uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}, const char *name = nullptr) {
    ClawPlayerProjectileCall e{};
    e.function = f;
    e.receiver = t;
    e.argumentCount = uint32_t(a.size());
    std::copy(a.begin(), a.end(), e.arguments);
    e.name = name;
    if (!r.d) {
        r.c.fault = 1;
        return 0;
    }
    return r.d(&r.c, &e, r.u);
}
uint32_t invoke(Run &r, uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
    uint32_t v = 0;
    if (r.depth++ > 64) {
        r.c.fault = 3;
        --r.depth;
        return 0;
    }
    uint32_t owned = execute(r, f, t, a.begin(), uint32_t(a.size()), &v);
    --r.depth;
    if (!owned) {
        ClawPlayerProjectileCall e{};
        e.function = f;
        e.receiver = t;
        e.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), e.arguments);
        if (r.d)
            v = uint32_t(r.d(&r.c, &e, r.u));
        else
            r.c.fault = 1;
    }
    return v;
}
uint32_t virt(Run &r, uint32_t t, uint32_t off) {
    return invoke(r, rd(r, rd(r, t) + off), t);
}
const char *name(uint32_t t) {
    switch (t) {
    case 0x524130:
        return "GAME_BULLETS";
    case 0x52418c:
        return "GAME_MAGICCLAW";
    case 0x52417c:
        return "GAME_CYCLE50";
    case 0x526f78:
        return "GAME_DYNAMITELIT";
    case 0x526f64:
        return "GAME_DYNAMITEHORZ";
    case 0x526f50:
        return "GAME_DYNAMITEEXPLO";
    case 0x526f40:
        return "GAME_KEGBOOM";
    case 0x522e24:
        return "Flare";
    case 0x522594:
        return "GlitterBaby";
    default:
        return nullptr;
    }
}
uint32_t registry(Run &r, uint32_t a, uint32_t o) {
    return rd(r, rd(r, a + 12) + o) + 16;
}
uint32_t first(Run &r, uint32_t a) {
    uint32_t h = rd(r, a + 0x170);
    if (!h)
        return 0;
    uint32_t i = rd(r, h + 100);
    wr(r, a + 0x16c, i);
    wr(r, a + 0x174, int32_t(i) <= int32_t(rd(r, h + 104)) ? rd(r, rd(r, h + 20) + i * 4) : 0);
    return 1;
}
void image(Run &r, uint32_t a, uint32_t literal) {
    wr(r, a + 0x170, uint32_t(call(r, 0x4f6286, registry(r, a, 16), {}, name(literal))));
    first(r, a);
}
void geometry(Run &r, uint32_t a, uint32_t off) {
    uint32_t h = rd(r, a + 0x174);
    if (!h)
        return;
    wr(r, a + off, rd(r, h + 32) - rd(r, h + 24));
    wr(r, a + off + 4, rd(r, h + 36) - rd(r, h + 28));
    wr(r, a + off + 8, rd(r, h + 32) - 1 + rd(r, h + 24));
    wr(r, a + off + 12, rd(r, h + 28) - 1 + rd(r, h + 36));
}
uint32_t animator(Run &r, uint32_t f, uint32_t t, uint32_t arg) {
    if (!r.c.composeAnimation)
        return uint32_t(call(r, f, t, {arg}));
    ClawActorAnimationGlobals g{r.c.globals->animationDelta, r.c.globals->masterVolume};
    uint32_t out = 0;
    claw_actor_animation_entry(f, t, arg, 0, &g, r.c.scene, &r.c.fault, &out);
    return out;
}
uint32_t words(Run &r, uint32_t e) {
    switch (rd(r, e)) {
    case 0x50b784:
        return 86;
    case 0x50da04:
        return 98;
    case 0x50b2d4:
        return 91;
    default:
        return 84;
    }
}
struct Bridge {
    Run &r;
    uint32_t e, a, l, n, sec, contact;
};
void transfer(ClawBullet *b, Bridge &k, bool put) {
    auto cp = [&](uint32_t t, uint32_t *p, uint32_t n) {
        if (!t)
            return;
        if (auto *q = span(k.r, t, n)) {
            if (put)
                std::copy(p, p + n, q);
            else
                std::copy(q, q + n, p);
        }
    };
    cp(k.a, b->actor, 128);
    cp(k.l, b->primary, 93);
    cp(k.sec, b->secondary, 93);
    cp(k.contact, b->contact, 93);
    cp(k.e, b->enemy, k.n);
}
uint64_t bulletBridge(ClawGenericEnemy *b, ClawGenericEnemyContext *, const ClawGenericEnemyCall *ev, void *user) {
    auto &k = *static_cast<Bridge *>(user);
    transfer(b, k, true);
    uint32_t v = 0;
    uint32_t owned = 0;
    if (ev->receiver == k.e && ev->function != 0x4dc870 && ev->function != 0x4dca10 && ev->function != 0x4063b0)
        owned = execute(k.r, ev->function, ev->receiver, ev->arguments, ev->argumentCount, &v);
    uint64_t out = v;
    if (!owned && k.r.c.composeAnimation && (ev->function == 0x4c8220 || ev->function == 0x4c82a0)) {
        out = animator(k.r, ev->function, ev->receiver, ev->arguments[0]);
        owned = 1;
    }
    if (!owned) {
        ClawPlayerProjectileCall e{};
        e.function = ev->function;
        e.receiver = ev->receiver;
        e.argumentCount = ev->argumentCount;
        std::copy(ev->arguments, ev->arguments + 12, e.arguments);
        e.name = ev->name;
        if (k.r.d)
            out = k.r.d(&k.r.c, &e, k.r.u);
        else
            k.r.c.fault = 1;
    }
    transfer(b, k, false);
    k.r.c.bullet->generic->tick = k.r.c.globals->tick;
    k.r.c.bullet->generic->animationDelta = k.r.c.globals->animationDelta;
    return out;
}
uint32_t common(Run &r, uint32_t f, uint32_t e, uint32_t a, uint32_t n, uint32_t arg = 0) {
    if (!r.c.bullet || !r.c.bullet->generic) {
        r.c.fault = 1;
        return 0;
    }
    auto *x = r.c.bullet;
    auto *g = x->generic;
    uint32_t l = rd(r, a + 0x6c);
    Bridge k{r, e, a, l, n, rd(r, a + 0x70), rd(r, a + 0x78)};
    ClawBullet b{};
    transfer(&b, k, false);
    g->actorToken = a;
    g->primaryToken = l;
    g->enemyToken = e;
    g->secondaryToken = k.sec;
    g->contactToken = k.contact;
    g->tick = r.c.globals->tick;
    g->animationDelta = r.c.globals->animationDelta;
    g->sceneToken = rd(r, a + 12);
    g->tileManagerToken = rd(r, g->sceneToken + 36);
    if ((b.actor[2] & 0x10) && b.actor[0x80 / 4]) {
        if (auto *platform = span(r, b.actor[0x80 / 4] + 0x158, 2)) {
            g->platformActor[0x158 / 4] = platform[0];
            g->platformActor[0x15c / 4] = platform[1];
        }
    }
    x->scene = r.c.scene;
    uint32_t vt = rd(r, e);
    if (vt >= 0x400000 && vt < 0x520000)
        if (auto *p = span(r, vt, 12))
            std::copy(p, p + 12, g->virtualFunctions);
    uint32_t result = 0;
    uint32_t support = claw_bullet_entry(&b, x, f, arg, bulletBridge, &k, &result);
    transfer(&b, k, true);
    if (x->fault)
        r.c.fault = x->fault;
    if (!support)
        r.c.fault = 1;
    return result;
}
void begin(Run &r, uint32_t e, const char *state) {
    uint32_t l = rd(r, e + 16);
    wr(r, e + 36, rd(r, l + 28));
    wr(r, l + 28, uint32_t(call(r, 0x4dba00, 0x537668, {}, state)));
}
uint32_t select(Run &r, uint32_t table, uint32_t id) {
    wr(r, table + 32, 0);
    int32_t lo = int32_t(rd(r, table + 8)), hi = int32_t(rd(r, table + 12));
    uint32_t p = 0;
    if (int32_t(id) >= lo && int32_t(id) <= hi)
        p = rd(r, table + 16) + (id - uint32_t(lo)) * rd(r, table + 24);
    else {
        p = uint32_t(call(r, 0x4db6e0, table, {id, 0}));
        if (p) {
            p = rd(r, table + 16) + (id - rd(r, table + 8)) * rd(r, table + 24);
        } else {
            wr(r, 0x544b14, uint32_t(call(r, 0x4db5f0, 0)));
            call(r, 0x4db4d0, rd(r, table + 4), {table, rd(r, 0x544b4c), 12});
            p = rd(r, table + 20);
        }
    }
    return p;
}
void dispatch(Run &r, uint32_t e, uint32_t table, uint32_t id, uint32_t fallback) {
    uint32_t p = select(r, table, id), f = rd(r, p);
    if (f) {
        p = select(r, table, id);
        invoke(r, rd(r, p), e);
    } else if (fallback)
        invoke(r, fallback, e, {id});
    else
        call(r, 0x4a36f0, 0, {e});
}
uint32_t queryFoot(Run &r, uint32_t e) {
    uint32_t a = rd(r, e + 8), world = rd(r, rd(r, a + 12) + 36), plane = rd(r, world + 92);
    int32_t x = int32_t(ftol(ld(r, e + 0x68))), y = int32_t(ftol(ld(r, e + 0x70)) + rd(r, a + 0x124));
    int32_t width = int32_t(rd(r, plane + 48)), height = int32_t(rd(r, plane + 52));
    x = x < 0 ? 0 : x >= width ? width - 1 : x;
    y = y < 0 ? 0 : y >= height ? height - 1 : y;
    uint32_t sx = rd(r, plane + 140) & 31, sy = rd(r, plane + 144) & 31, ix = uint32_t(x >> sx), iy = uint32_t(y >> sy);
    uint32_t tile = rd(r, rd(r, plane + 32) + (rd(r, rd(r, plane + 36) + iy * 4) + ix) * 4);
    if (tile == 0xeeeeeeee || tile == 0xffffffff)
        return 0;
    uint32_t desc = rd(r, rd(r, world + 76) + (tile & 0xffff) * 4), out = 0;
    ClawRawTileArguments args{{uint32_t(x) - (ix << sx), uint32_t(y) - (iy << sy), 0, 0}, 2};
    claw_raw_tile_virtual(desc, 32, args, r.c.scene, &r.c.fault, &out);
    return out;
}
void sparkle(Run &r, uint32_t e, uint32_t countOffset) {
    int32_t count = int32_t(rd(r, e + countOffset));
    if (count > 4096) {
        r.c.fault = 3;
        return;
    }
    for (int32_t i = 0; i < int32_t(rd(r, e + countOffset)); ++i) {
        if (i >= 4096) {
            r.c.fault = 3;
            return;
        }
        uint32_t a = rd(r, e + 12);
        auto coordinate = [&](uint32_t off) {
            int32_t left = int32_t(rd(r, a + off)), right = int32_t(rd(r, a + off + 8));
            uint32_t width = uint32_t(right) - uint32_t(left) + 1;
            int32_t random = int32_t(call(r, 0x4a3050, 0));
            if (!width)
                return (random & 1) ? left : right;
            if (width == 0xffffffff && random == INT32_MIN) {
                r.c.fault = 2;
                return int32_t(0);
            }
            return int32_t(uint32_t(random % int32_t(width)) + uint32_t(left));
        };
        double px = ld(r, e + 0x68);
        int32_t xc = coordinate(0x118);
        if (r.c.fault)
            return;
        uint32_t x = ftol(add(px, double(xc)));
        double py = ld(r, e + 0x70);
        int32_t yc = coordinate(0x11c);
        if (r.c.fault)
            return;
        uint32_t y = ftol(add(py, double(yc))), l = rd(r, e + 0x130), container = rd(r, rd(r, l + 12) + 8);
        uint32_t child =
            uint32_t(call(r, 0x4c8da0, container, {0, x, y, rd(r, a + 100) - 1, 0x522594, 0x40000}, "GlitterBaby"));
        if (!child) {
            r.c.fault = 2;
            return;
        }
        uint32_t logic = rd(r, child + 108);
        invoke(r, rd(r, logic + 16), 0, {child});
    }
}
uint32_t execute(Run &r, uint32_t f, uint32_t e, const uint32_t *args, uint32_t count, uint32_t *out) {
    uint32_t arg = count ? args[0] : 0, value = 0, a = 0;
    switch (f) {
    case 0x40ff80:
    case 0x410040:
    case 0x43a850: {
        a = arg;
        uint32_t l = rd(r, a + 108), state = rd(r, l + 28);
        if (!state) {
            wr(r, l + 28, 1000);
            uint32_t bytes = claw_player_projectile_private_bytes(f);
            e = uint32_t(call(r, 0x4f63ec, 0, {bytes}));
            if (!e) {
                r.c.fault = 2;
                break;
            }
            invoke(r, f == 0x40ff80 ? 0x410870 : f == 0x410040 ? 0x410900 : 0x43a910, e, {a});
            virt(r, e, 16);
            wr(r, l + 24, e);
        } else if (state == 29 || state == 30) {
            e = rd(r, l + 24);
            virt(r, e, state == 29 ? 32 : 28);
        } else if (state != 1000) {
            e = rd(r, l + 24);
            invoke(r, 0x4dc870, e);
        }
        value = 1;
        break;
    }
    case 0x410870:
    case 0x410900: {
        a = arg;
        common(r, 0x4107c0, e, a, f == 0x410900 ? 86 : 84);
        wr(r, e, f == 0x410870 ? 0x50b74c : 0x50b784);
        image(r, a, f == 0x410870 ? 0x524130 : 0x52418c);
        if (f == 0x410870) {
            first(r, a);
            value = e;
            break;
        }
        wr(r, e + 0x148, uint32_t(call(r, 0x4f6286, registry(r, a, 44), {}, "GAME_CYCLE50")));
        wr(r, a + 8, rd(r, a + 8) | 0x80000);
        if (!r.c.globals->magicDisabled && rd(r, r.c.globals->ownerToken + 0x124)) {
            uint32_t l = rd(r, e + 0x130);
            wr(r, e + 0x154,
               uint32_t(call(r, 0x4c8da0, rd(r, rd(r, l + 12) + 8),
                             {0, rd(r, a + 76), rd(r, a + 80), rd(r, a + 100) - 1, 0x522e24, 0x40000}, "Flare")));
            wr(r, e + 0x150, 2);
        } else {
            wr(r, e + 0x154, 0);
            wr(r, e + 0x150, 1);
        }
        value = e;
        break;
    }
    case 0x4084b0:
        a = arg;
        common(r, 0x473c50, e, a, 91);
        wr(r, e, 0x50b2d4);
        for (uint32_t o : {0x160u, 0x164u, 0x150u, 0x158u, 0x15cu, 0x154u})
            wr(r, e + o, 0);
        wr(r, e + 0x168, 1250);
        wr(r, a + 8, rd(r, a + 8) | 0x40);
        value = e;
        break;
    case 0x43a910: {
        a = arg;
        invoke(r, 0x4084b0, e, {a});
        wr(r, e, 0x50da04);
        image(r, a, 0x526f78);
        for (auto item : {std::pair<uint32_t, uint32_t>{0x150, 0x526f78}, {0x178, 0x526f64}, {0x174, 0x526f50}})
            wr(r, e + item.first, uint32_t(call(r, 0x4f6286, registry(r, a, 44), {}, name(item.second))));
        wr(r, e + 0x17c, uint32_t(call(r, 0x4061b0, rd(r, rd(r, a + 12) + 40), {}, "GAME_KEGBOOM")));
        wr(r, e + 0x180, 0);
        wr(r, a + 0x138, uint32_t(-50));
        wr(r, a + 0x13c, uint32_t(-50));
        wr(r, a + 0x140, 50);
        wr(r, a + 0x144, 50);
        wr(r, a + 8, rd(r, a + 8) | 0x80);
        wr(r, a + 0xd0, 4);
        geometry(r, a, 0x118);
        geometry(r, a, 0x128);
        if (!rd(r, a + 100)) {
            wr(r, a + 100, 0x137e);
            wr(r, a + 8, rd(r, a + 8) | 0x20000);
        }
        wr(r, e + 0x124, 8);
        wr(r, e + 0x15c, 2);
        wr(r, e + 0x168, 1250);
        st(r, e + 64, 2000);
        ClawPlayerPhysics p{};
        if (auto *q = span(r, e + 40, sizeof p / 4))
            std::memcpy(&p, q, sizeof p);
        claw_physics_retarget(&p, add(p.position[0], double(int32_t(rd(r, a + 0x158)))), p.position[1], -0.0);
        st(r, e + 80, p.velocity[0]);
        st(r, e + 88, p.velocity[1]);
        st(r, e + 96, p.velocity[2]);
        uint32_t doubled = rd(r, a + 0x158) << 1, mask = uint32_t(int32_t(doubled) >> 31);
        st(r, e + 88, sub(ld(r, e + 88), double(int32_t((doubled ^ mask) - mask))));
        wr(r, e + 0x170, 1);
        value = e;
        break;
    }
    case 0x4dc870: {
        uint32_t l = rd(r, e + 16), id = rd(r, l + 28);
        auto stateName = [&]() {
            uint32_t cell = select(r, 0x537698, id), pending = rd(r, 0x5376b8), object = rd(r, 0x5376b4);
            if (pending > 4096) {
                r.c.fault = 3;
                return uint32_t(0);
            }
            for (uint32_t i = 0; i < pending; ++i, object += 4)
                if (object)
                    call(r, 0x4f6439, object);
            uint32_t chars = rd(r, cell);
            if (int32_t(rd(r, chars - 12)) <= 1 && int32_t(rd(r, chars - 4)) >= 0)
                return chars;
            return uint32_t(call(r, 0x4f6974, cell, {0}));
        };
        uint32_t nt = stateName();
        invoke(r, rd(r, rd(r, e) + 4), e, {nt});
        invoke(r, rd(r, rd(r, e) + 8), e, {id});
        nt = stateName();
        invoke(r, rd(r, rd(r, e) + 12), e, {nt});
        value = 1;
        break;
    }
    case 0x410a80:
        dispatch(r, e, 0x534ab0, arg, 0x473f40);
        break;
    case 0x408580:
        dispatch(r, e, 0x534910, arg, 0x473f40);
        break;
    case 0x43ad20:
        dispatch(r, e, 0x5375d8, arg, 0x408580);
        break;
    case 0x408860:
        value = virt(r, e, 40);
        break;
    case 0x408870:
        a = rd(r, e + 300);
        wr(r, e + 0x134, rd(r, a + 400));
        animator(r, 0x4c8220, a + 392, rd(r, e + 0x150));
        wr(r, rd(r, e + 12) + 204, 8);
        wr(r, a + 8, rd(r, a + 8) | 2);
        begin(r, e, "LS_FALLING");
        if (queryFoot(r, e) == 1)
            virt(r, e, 60);
        wr(r, e + 0x164, rd(r, e + 0x168));
        wr(r, e + 0x160, r.c.globals->tick);
        break;
    case 0x4089d0:
        a = rd(r, e + 300);
        animator(r, 0x4c82a0, a + 392, r.c.globals->animationDelta);
        if (rd(r, e + 0x164) <= r.c.globals->tick - rd(r, e + 0x160))
            virt(r, e, 56);
        a = rd(r, e + 12);
        if (rd(r, a + 204) == 1) {
            virt(r, e, 52);
            uint32_t sound = rd(r, e + 0x154);
            if (sound && r.c.globals->audioEnabled)
                call(r, 0x4b45f0, rd(r, sound + 16), {r.c.globals->masterVolume, 0, 0, 0});
            if (rd(r, e + 0x158) == rd(r, e + 0x15c)) {
                wr(r, e + 200, 1);
                virt(r, e, 48);
                break;
            }
            wr(r, e + 0x158, rd(r, e + 0x158) + 1);
            wr(r, a + 204, 8);
            double y = sub(ld(r, e + 112), 1), v = ld(r, e + 88), gravity = ld(r, e + 64);
            if (gravity != 0) {
                double sq = sub(mul(v, v), mul(mul(sub(y, ld(r, e + 112)), gravity), -2));
                if (sq < 0)
                    sq = 0;
                v = std::sqrt(sq);
                if (ld(r, e + 88) <= 0)
                    v = -v;
            }
            st(r, e + 88, mul(v, -0.5));
            st(r, e + 184, -1);
            st(r, e + 112, y);
            st(r, e + 80, mul(ld(r, e + 80), 0.5));
            st(r, e + 96, 0);
        }
        break;
    case 0x410d60:
        common(r, 0x4742f0, e, rd(r, e + 12), 86);
        sparkle(r, e, 0x150);
        if (r.c.fault)
            break;
        if (uint32_t flare = rd(r, e + 0x154)) {
            wr(r, flare + 76, ftol(ld(r, e + 104)));
            wr(r, rd(r, e + 0x154) + 80, ftol(ld(r, e + 112)));
        }
        break;
    case 0x414010:
        if (uint32_t flare = rd(r, e + 0x154))
            wr(r, flare + 8, rd(r, flare + 8) | 0x10000);
        break;
    case 0x43b120:
    case 0x43b160:
        a = rd(r, e + 300);
        if (f == 0x43b160)
            wr(r, e + 200, 1);
        if (rd(r, a + 400) != rd(r, e + 0x174)) {
            wr(r, e + 0x134, rd(r, a + 400));
            animator(r, 0x4c8220, a + 392, f == 0x43b120 ? rd(r, e + 0x178) : 0);
        }
        break;
    case 0x43b1a0:
        wr(r, e + 200, 1);
        if (uint32_t sound = rd(r, e + 0x17c))
            if (r.c.globals->audioEnabled)
                call(r, 0x4b45f0, rd(r, sound + 16), {r.c.globals->masterVolume, 0, 0, 0});
        virt(r, e, 44);
        break;
    case 0x43b1e0:
        a = rd(r, e + 12);
        if (rd(r, a + 100) != 0x2134) {
            wr(r, a + 100, 0x2134);
            wr(r, a + 8, rd(r, a + 8) | 0x20000);
        }
        wr(r, e + 200, 1);
        break;
    case 0x43b210:
        a = rd(r, e + 300);
        image(r, a, 0x526f50);
        begin(r, e, "LS_EXPLODING");
        wr(r, a + 0xd0, 0x1000000);
        wr(r, e + 0x134, rd(r, a + 400));
        animator(r, 0x4c8220, a + 392, rd(r, e + 0x174));
        wr(r, e + 0x180, 0);
        break;
    case 0x486e70:
        value = rd(r, 0x541328) + arg;
        if (rd(r, 0x53c260) <= value)
            wr(r, 0x53c260, value);
        break;
    case 0x43b290:
        a = rd(r, e + 300);
        wr(r, a + 8, rd(r, a + 8) | 0x80);
        if (animator(r, 0x4c82a0, a + 392, r.c.globals->animationDelta) == 1 && !rd(r, e + 0x180)) {
            wr(r, e + 0x180, 1);
            invoke(r, 0x486e70, 0, {500});
            wr(r, a + 8, rd(r, a + 8) & ~0x80u);
        }
        a = rd(r, e + 300);
        if (rd(r, a + 420) && !rd(r, a + 412))
            wr(r, a + 8, rd(r, a + 8) | 0x10000);
        break;
    case 0x43b320:
        invoke(r, 0x4089d0, e);
        sparkle(r, e, 0x170);
        break;
    case 0x484d90:
        wr(r, e, 0x50b014);
        if (arg & 1) {
            if (r.c.scene.free)
                r.c.scene.free(r.c.scene.context, e);
            else
                call(r, 0x4f6428, 0, {e});
        }
        value = e;
        break;
    case 0x456030:
        wr(r, e, 0x50b014);
        break;
    case 0x408510:
        a = rd(r, e + 300);
        wr(r, a + 8, rd(r, a + 8) | 0x10000);
        break;
    case 0x4c7970:
        if (!name(arg))
            return 0;
        image(r, e, arg);
        break;
    case 0x4742f0:
    case 0x473f40:
    case 0x474290:
    case 0x4741f0:
    case 0x4dca10:
    case 0x4063b0:
    case 0x4107c0:
    case 0x473c50:
        value = common(r, f, e, f == 0x4107c0 || f == 0x473c50 ? arg : rd(r, e + 12), words(r, e), arg);
        break;
    case 0x4c96b0:
    case 0x4c9e30:
    case 0x4bb030:
        break;
    default:
        return 0;
    }
    if (out)
        *out = value;
    return 1;
}
} // namespace
extern "C" uint32_t claw_player_projectile_private_bytes(uint32_t f) {
    return f == 0x40ff80 ? 0x150 : f == 0x410040 ? 0x158 : f == 0x43a850 ? 0x188 : 0;
}
extern "C" uint32_t claw_player_projectile_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                 ClawPlayerProjectileContext *c, ClawPlayerProjectileDependency d,
                                                 void *u, uint32_t *out) {
    if (!c || !c->globals || n > 12 || (n && !a))
        return 0;
    Run r{*c, d, u};
    uint32_t owned = execute(r, f, t, a, n, out);
    return owned && !c->fault;
}
