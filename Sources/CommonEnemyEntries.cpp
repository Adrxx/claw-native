#include "CommonEnemyEntries.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawHumanEnemyContext *h;
    ClawGenericEnemyDependency d;
    void *user;
};
uint32_t execute(ClawGenericEnemy *, Run &, uint32_t, uint32_t, uint32_t *);
uint64_t call(ClawGenericEnemy *s, Run &r, uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {},
              const char *name = nullptr) {
    ClawGenericEnemyCall e{};
    e.function = f;
    e.receiver = t;
    e.argumentCount = uint32_t(a.size());
    e.name = name;
    std::copy(a.begin(), a.end(), e.arguments);
    if (!r.d) {
        r.h->fault = 1;
        return 0;
    }
    return r.d(s, r.h->generic, &e, r.user);
}
uint64_t bridge(ClawGenericEnemy *s, ClawGenericEnemyContext *g, const ClawGenericEnemyCall *e, void *p) {
    auto &r = *static_cast<Run *>(p);
    uint32_t result;
    if (e->receiver == g->enemyToken && execute(s, r, e->function, e->argumentCount ? e->arguments[0] : 0, &result))
        return result;
    if (!r.d) {
        r.h->fault = 1;
        return 0;
    }
    return r.d(s, g, e, r.user);
}
void invoke(ClawGenericEnemy *s, Run &r, uint32_t fn, uint32_t arg = 0, bool hasArg = false) {
    uint32_t value;
    auto *h = r.h;
    auto *g = h->generic;
    if (execute(s, r, fn, arg, &value))
        return;
    if (claw_human_enemy_entry(s, h, fn, arg, bridge, &r, &value))
        return;
    if (claw_generic_enemy_state_entry(s, g, h->sharedStates, fn, arg, bridge, &r))
        return;
    if (claw_generic_enemy_entry(s, g, fn, arg, bridge, &r))
        return;
    if (hasArg)
        call(s, r, fn, g->enemyToken, {arg});
    else
        call(s, r, fn, g->enemyToken);
}
void virt(ClawGenericEnemy *s, Run &r, uint32_t off, uint32_t arg = 0, bool hasArg = false) {
    invoke(s, r, r.h->generic->virtualFunctions[off / 4], arg, hasArg);
}
void store(uint32_t *p, uint32_t off, double value) {
    std::memcpy(p + off / 4, &value, 8);
}
double load(const uint32_t *p, uint32_t off) {
    double value;
    std::memcpy(&value, p + off / 4, 8);
    return value;
}
uint32_t stateID(ClawGenericEnemy *s, Run &r, const char *name) {
    if (r.d)
        return uint32_t(call(s, r, 0x4dba00, 0x537668, {}, name));
    auto *g = r.h->generic;
    for (size_t n = 0; n < g->stateCount; ++n)
        if (g->states[n].name && !std::strcmp(g->states[n].name, name))
            return uint32_t(g->states[n].state);
    r.h->fault = 1;
    return 0;
}
void transition(ClawGenericEnemy *s, Run &r, const char *name) {
    s->enemy[9] = s->primary[7];
    s->primary[7] = stateID(s, r, name);
}
void sequence(ClawGenericEnemy *s, Run &r, uint32_t off) {
    s->enemy[0x134 / 4] = s->actor[0x190 / 4];
    call(s, r, 0x4c8220, r.h->generic->actorToken + 0x188, {s->enemy[off / 4]});
}
void audio(ClawGenericEnemy *s, Run &r, uint32_t off) {
    uint32_t t = s->enemy[off / 4];
    auto *x = r.h->sharedStates;
    if (!t || !x->audioEnabled)
        return;
    for (size_t n = 0; n < x->resourceCount; ++n)
        if (x->resources[n].token == t) {
            call(s, r, 0x4b45f0, x->resources[n].controllerToken, {x->audioPosition, 0, 0, 0});
            return;
        }
    r.h->fault = 1;
}
void mirrorRect(uint32_t *p, uint32_t off) {
    if (p[off / 4] == 0x80000000)
        return;
    uint32_t old = p[off / 4];
    p[off / 4] = 0u - p[(off + 8) / 4];
    p[(off + 8) / 4] = 0u - old;
}
void face(ClawGenericEnemy *s, bool left) {
    auto *a = s->actor;
    auto *e = s->enemy;
    if (bool(a[0x40 / 4] & 2) == left)
        return;
    uint32_t old = e[0x138 / 4];
    e[0x138 / 4] = 0u - e[0x140 / 4];
    e[0x140 / 4] = 0u - old;
    a[0x40 / 4] = left ? a[0x40 / 4] | 2 : a[0x40 / 4] & ~2u;
    for (uint32_t o : {0x118u, 0x128u, 0x138u})
        mirrorRect(a, o);
}
uint32_t execute(ClawGenericEnemy *s, Run &r, uint32_t fn, uint32_t arg, uint32_t *result) {
    auto *e = s->enemy;
    auto *a = s->actor;
    auto *h = r.h;
    auto *g = h->generic;
    switch (fn) {
    case 0x43ed70:
        sequence(s, r, 0x32c);
        transition(s, r, "LS_FALLING");
        a[0xcc / 4] = 8;
        break;
    case 0x43efe0:
        e[8] = 1;
        transition(s, r, "LS_STRIKE");
        sequence(s, r, 0x310);
        break;
    case 0x43fe00:
        store(e, 0x50, 0);
        transition(s, r, "LS_STANDING");
        sequence(s, r, 0x314);
        break;
    case 0x43f500:
        transition(s, r, "LS_PAUSE");
        e[0x3e4 / 4] = arg;
        e[0x3e0 / 4] = g->tick;
        break;
    case 0x404e00:
        e[0x1ac / 4] = arg;
        break;
    case 0x404e10:
        a[0x10c / 4] -= 4;
        break;
    case 0x44de30:
        claw_human_enemy_set_private_word(s, h, 0x42c, 2000);
        claw_human_enemy_set_private_word(s, h, 0x428, g->tick);
        invoke(s, r, 0x440120);
        break;
    case 0x440c70:
        e[8] = 2;
        a[2] &= ~4u;
        break;
    case 0x440b20:
    case 0x440c90:
        e[8] = 1;
        e[6] = 0x440c70;
        e[7] = s->primary[7];
        transition(s, r, fn == 0x440b20 ? "LS_BLOCKHIGH" : "LS_BLOCKLOW");
        sequence(s, r, fn == 0x440b20 ? 0x384 : 0x388);
        audio(s, r, fn == 0x440b20 ? 0x3c0 : 0x3bc);
        a[2] |= 4;
        store(e, 0x50, e[0x18c / 4] == 3 ? 200 : -200);
        break;
    case 0x44dbb0: {
        uint32_t counter = claw_human_enemy_private_word(s, h, 0x424) + 1;
        claw_human_enemy_set_private_word(s, h, 0x424, counter);
        if (counter == 1)
            audio(s, r, 0x408);
        counter = claw_human_enemy_private_word(s, h, 0x424);
        if (int32_t(counter) < 3) {
            invoke(s, r, 0x43fe60);
            break;
        }
        store(e, 0x50, 0);
        if (counter == 3) {
            virt(s, r, 0x90, 500, true);
            break;
        }
        virt(s, r, 0xa8);
        if (int32_t(a[0x10c / 4]) < 1) {
            virt(s, r, 0x5c, 1, true);
            break;
        }
        claw_human_enemy_set_private_word(s, h, 0x424, 0);
        a[0xd0 / 4] = 4;
        a[2] &= ~4u;
        uint32_t rectangle[4];
        std::copy(e + 0x270 / 4, e + 0x280 / 4, rectangle);
        a[0x50 / 4] += a[0x124 / 4] - rectangle[3];
        std::copy(rectangle, rectangle + 4, a + 0x118 / 4);
        a[2] &= ~2u;
        sequence(s, r, 0x344);
        call(s, r, 0x4c82a0, g->actorToken + 0x188, {g->animationDelta});
        virt(s, r, 0x44);
        e[8] = 2;
        claw_human_enemy_set_private_word(s, h, 0x444, 1500);
        claw_human_enemy_set_private_word(s, h, 0x440, g->tick);
        break;
    }
    case 0x43fa10: {
        uint32_t px = g->playerActor[0x4c / 4], distance = uint32_t(int32_t(call(s, r, 0x4a3050, 0)) % 41 + 40);
        uint32_t x = e[0x18c / 4] == 3 ? px + distance : px - distance;
        e[0x280 / 4] = x;
        if (e[0x18c / 4] == 3 ? double(int32_t(x)) < load(e, 0x80) : load(e, 0x98) < double(int32_t(x)))
            break;
        uint32_t y = a[0x50 / 4] + a[0x124 / 4] + 1;
        auto tile = [&](uint32_t yy) {
            return uint32_t(call(s, r, 0x4207f0, g->tileManagerToken, {x, yy}));
        };
        if (tile(y) != 1 && tile(y) != 2 && tile(y) != 3)
            break;
        if (tile(y - 1))
            break;
        store(e, 0x50, e[0x18c / 4] == 3 ? -150 : 150);
        store(e, 0x58, 0);
        store(e, 0x60, 0);
        face(s, e[0x18c / 4] == 2);
        transition(s, r, "LS_MOVEAHEAD");
        sequence(s, r, 0x308);
        break;
    }
    default:
        return 0;
    }
    if (result)
        *result = 0;
    return 1;
}
} // namespace
extern "C" uint32_t claw_common_enemy_entry(ClawGenericEnemy *s, ClawHumanEnemyContext *h, uint32_t fn, uint32_t arg,
                                            ClawGenericEnemyDependency d, void *user, uint32_t *result) {
    if (!s || !h || !h->generic || !h->sharedStates || !h->privateTail)
        return 0;
    Run r{h, d, user};
    return execute(s, r, fn, arg, result);
}
