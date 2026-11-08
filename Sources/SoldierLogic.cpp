#include "SoldierLogic.h"
#include "CommonEnemyEntries.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
#pragma STDC FP_CONTRACT OFF
namespace {
struct Run {
    ClawSoldierContext *x;
    ClawGenericEnemyDependency d;
    void *user;
};
void propagate(ClawSoldierContext *x) {
    if (x->human->fault || (x->combat && x->combat->fault) || (x->motion && x->motion->fault))
        x->fault = 3;
}
uint32_t execute(ClawSoldier *, Run &, uint32_t, uint32_t, uint32_t *);
uint32_t word(const ClawSoldier *s, const Run &r, uint32_t off) {
    return claw_soldier_private_word(s, r.x, off);
}
void put(ClawSoldier *s, Run &r, uint32_t off, uint32_t value) {
    claw_soldier_set_private_word(s, r.x, off, value);
}
uint64_t call(ClawSoldier *s, Run &r, uint32_t fn, uint32_t receiver, std::initializer_list<uint32_t> args = {},
              const char *name = nullptr) {
    if (!r.d) {
        r.x->fault = 1;
        return 0;
    }
    ClawGenericEnemyCall e{};
    e.function = fn;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    e.name = name;
    std::copy(args.begin(), args.end(), e.arguments);
    return r.d(s, r.x->human->generic, &e, r.user);
}
uint64_t forward(ClawGenericEnemy *s, ClawGenericEnemyContext *g, const ClawGenericEnemyCall *e, void *p) {
    auto &r = *static_cast<Run *>(p);
    uint32_t value = 0;
    if (e->receiver == g->enemyToken && execute(s, r, e->function, e->argumentCount ? e->arguments[0] : 0, &value))
        return value;
    if (!r.d) {
        r.x->fault = 1;
        return 0;
    }
    return r.d(s, g, e, r.user);
}
void invoke(ClawSoldier *s, Run &r, uint32_t fn, uint32_t arg = 0, bool hasArg = false) {
    uint32_t value = 0;
    if (execute(s, r, fn, arg, &value))
        return;
    if (hasArg)
        call(s, r, fn, r.x->human->generic->enemyToken, {arg});
    else
        call(s, r, fn, r.x->human->generic->enemyToken);
}
void virt(ClawSoldier *s, Run &r, uint32_t slot, uint32_t arg = 0, bool hasArg = false) {
    invoke(s, r, r.x->human->generic->virtualFunctions[slot / 4], arg, hasArg);
}
uint32_t stateID(ClawSoldier *s, Run &r, const char *name) {
    if (r.d)
        return uint32_t(call(s, r, 0x4dba00, 0x537668, {}, name));
    auto *g = r.x->human->generic;
    for (size_t n = 0; n < g->stateCount; ++n)
        if (g->states[n].name && !std::strcmp(g->states[n].name, name))
            return uint32_t(g->states[n].state);
    r.x->fault = 1;
    return 0;
}
uint32_t resource(ClawSoldier *s, Run &r, uint32_t registry, const char *name) {
    return uint32_t(call(s, r, 0x4f6286, registry, {}, name));
}
void store(uint32_t *p, uint32_t off, double value) {
    std::memcpy(p + off / 4, &value, 8);
}
double mul(double a, double b) {
    volatile double v = a * b;
    return v;
}
uint32_t truncLow(double value) {
    uint64_t b;
    std::memcpy(&b, &value, 8);
    int e = int((b >> 52) & 2047) - 1023;
    if (e < 0 || e >= 63)
        return 0;
    uint64_t m = (b & 0xfffffffffffffULL) | 0x10000000000000ULL;
    m = e >= 52 ? m << (e - 52) : m >> (52 - e);
    return b >> 63 ? 0u - uint32_t(m) : uint32_t(m);
}
void mirrorRect(uint32_t *p, uint32_t off) {
    if (p[off / 4] == 0x80000000)
        return;
    uint32_t left = p[off / 4];
    p[off / 4] = 0u - p[(off + 8) / 4];
    p[(off + 8) / 4] = 0u - left;
}
void mirror(ClawSoldier *s, bool left) {
    auto *a = s->actor;
    auto *e = s->enemy;
    if (bool(a[0x40 / 4] & 2) == left)
        return;
    uint32_t old = e[0x138 / 4];
    e[0x138 / 4] = 0u - e[0x140 / 4];
    e[0x140 / 4] = 0u - old;
    a[0x40 / 4] = left ? a[0x40 / 4] | 2 : a[0x40 / 4] & ~2u;
    for (uint32_t off : {0x118u, 0x128u, 0x138u})
        mirrorRect(a, off);
}
void animate(ClawSoldier *s, Run &r) {
    auto *g = r.x->human->generic;
    call(s, r, 0x4c82a0, g->actorToken + 0x188, {g->animationDelta});
}
const uint32_t *other(ClawSoldier *s, Run &r) {
    auto *h = r.x->human;
    auto *g = h->generic;
    uint32_t t = s->enemy[0x194 / 4];
    if (t == g->actorToken)
        return s->actor;
    if (t == g->playerToken)
        return g->playerActor;
    if (t == h->otherActorToken && h->otherActor)
        return h->otherActor;
    r.x->fault = 1;
    return nullptr;
}
bool nearPlayer(ClawSoldier *s, Run &r) {
    auto *g = r.x->human->generic;
    if (g->levelWord == 0x26b7)
        return false;
    const uint32_t *a = other(s, r);
    if (!a)
        return false;
    if (!call(s, r, 0x4cda10, g->tileManagerToken, {a[0x4c / 4], a[0x50 / 4], g->playerActor[0x4c / 4], 32}))
        return false;
    a = other(s, r);
    if (!a)
        return false;
    uint32_t y = a[0x50 / 4], py = g->playerActor[0x50 / 4];
    return int32_t(py) < int32_t(y + 50) && int32_t(y - 50) < int32_t(py) && a[0x38 / 4] != 0xffffffff;
}
uint32_t *bulletSpan(Run &r, uint32_t token, uint32_t count, int which) {
    if (r.x->scene.lookup) {
        auto *p = r.x->scene.lookup(r.x->scene.context, token, count);
        if (!p)
            r.x->fault = 2;
        return p;
    }
    uint32_t *p = which == 0 ? r.x->bulletActor : which == 1 ? r.x->bulletPrimary : r.x->bulletPrivate;
    if (!p)
        r.x->fault = 2;
    return p;
}
bool projectile(ClawSoldier *s, Run &r) {
    auto *x = r.x;
    auto *g = x->human->generic;
    auto *a = s->actor;
    uint32_t container = x->actorContainerToken;
    if (x->scene.lookup) {
        auto *p = x->scene.lookup(x->scene.context, s->primary[3] + 8, 1);
        if (!p) {
            x->fault = 2;
            return false;
        }
        container = *p;
    }
    uint32_t token;
    if (x->scene.lookup) {
        ClawSceneActorCreate args{
            0, a[0x4c / 4] + word(s, r, 0x454), a[0x50 / 4] + word(s, r, 0x458), a[0x64 / 4] - 1, 0, 0x40000};
        token = claw_scene_actor_create_named(container, args, 0x522e0c, x->scene, &x->fault);
    } else
        token = uint32_t(call(
            s, r, 0x4c8da0, container,
            {0, a[0x4c / 4] + word(s, r, 0x454), a[0x50 / 4] + word(s, r, 0x458), a[0x64 / 4] - 1, 0x522e0c, 0x40000}));
    x->bulletToken = token;
    if (!token) {
        x->fault = 2;
        return false;
    }
    call(s, r, 0x4c7970, token, {}, "LEVEL_MUSKETBALL");
    auto *b = bulletSpan(r, token, 128, 0);
    if (!b)
        return false;
    b[0x104 / 4] = 10;
    b[0xd0 / 4] = 0x40;
    auto *primary = bulletSpan(r, b[0x6c / 4], 93, 1);
    if (!primary)
        return false;
    call(s, r, primary[0x10 / 4], 0, {token});
    b = bulletSpan(r, token, 128, 0);
    if (!b)
        return false;
    primary = bulletSpan(r, b[0x6c / 4], 93, 1);
    if (!primary)
        return false;
    auto *body = bulletSpan(r, primary[0x18 / 4], 81, 2);
    if (!body)
        return false;
    store(body, 0x50, double(int32_t(word(s, r, 0x45c))));
    // The original reloads the actor's primary/private identities for each pair.
    primary = bulletSpan(r, b[0x6c / 4], 93, 1);
    if (!primary)
        return false;
    body = bulletSpan(r, primary[0x18 / 4], 81, 2);
    if (!body)
        return false;
    store(body, 0x58, 0);
    primary = bulletSpan(r, b[0x6c / 4], 93, 1);
    if (!primary)
        return false;
    body = bulletSpan(r, primary[0x18 / 4], 81, 2);
    if (!body)
        return false;
    store(body, 0x40, 0);
    if (int32_t(word(s, r, 0x45c)) < 0) {
        primary = bulletSpan(r, b[0x6c / 4], 93, 1);
        if (!primary)
            return false;
        body = bulletSpan(r, primary[0x18 / 4], 81, 2);
        if (!body)
            return false;
        auto *actual = bulletSpan(r, body[0x12c / 4], 128, 0);
        if (!actual)
            return false;
        if (!(actual[0x40 / 4] & 2)) {
            uint32_t old = body[0x138 / 4];
            body[0x138 / 4] = 0u - body[0x140 / 4];
            body[0x140 / 4] = 0u - old;
            actual[0x40 / 4] |= 2;
            mirrorRect(actual, 0x118);
            mirrorRect(actual, 0x128);
            mirrorRect(actual, 0x138);
        }
    }
    const uint32_t sound = s->enemy[0x3b4 / 4];
    auto *shared = x->human->sharedStates;
    if (sound && shared->audioEnabled) {
        uint32_t pool = 0;
        for (size_t n = 0; n < shared->resourceCount; ++n)
            if (shared->resources[n].token == sound)
                pool = shared->resources[n].controllerToken;
        if (x->scene.lookup) {
            auto *p = x->scene.lookup(x->scene.context, sound + 0x10, 1);
            if (p)
                pool = *p;
            else
                x->fault = 2;
        }
        if (!pool) {
            x->fault = 2;
            return false;
        }
        call(s, r, 0x4b45f0, pool, {shared->audioPosition, 0, 0, 0});
    }
    (void)g;
    return true;
}
uint32_t execute(ClawSoldier *s, Run &r, uint32_t fn, uint32_t arg, uint32_t *result) {
    auto *x = r.x;
    auto *h = x->human;
    auto *g = h->generic;
    auto *e = s->enemy;
    auto *a = s->actor;
    uint32_t value = 0;
    switch (fn) {
    case 0x48b0c0: {
        const ClawGenericEnemyState *entry = nullptr;
        for (size_t n = 0; n < x->soldierStateCount; ++n)
            if (x->soldierStates[n].state == int32_t(arg)) {
                entry = x->soldierStates + n;
                break;
            }
        if (!entry) {
            x->fault = 1;
            break;
        }
        if (entry->function)
            invoke(s, r, entry->function);
        else
            invoke(s, r, 0x44c840, arg, true);
        break;
    }
    case 0x48b4b0:
        mirror(s, e[0x18c / 4] == 2);
        call(s, r, 0x4a3050, 0);
        switch (e[0x184 / 4]) {
        case 3:
        case 4:
            virt(s, r, 0x58);
            break;
        case 0:
        case 1:
        case 2:
            if (!nearPlayer(s, r))
                virt(s, r, 0x48);
            if (!word(s, r, 0x450)) {
                if (a[0x38 / 4] != 0xffffffff)
                    call(s, r, 0x48ce40, 0, {g->actorToken, word(s, r, 0x460), 0});
                put(s, r, 0x450, 1);
            }
            [[fallthrough]];
        default:
            if (!nearPlayer(s, r))
                invoke(s, r, 0x44da20);
            else
                virt(s, r, 0xa4);
            break;
        }
        break;
    case 0x48b670:
        if (word(s, r, 0x470) <= g->tick - word(s, r, 0x46c)) {
            invoke(s, r, 0x48b880);
            put(s, r, 0x470, 500);
            put(s, r, 0x46c, g->tick);
        }
        break;
    case 0x48b6b0:
        store(e, 0x50, 0);
        e[9] = s->primary[7];
        s->primary[7] = stateID(s, r, "LS_IDLE");
        e[0x134 / 4] = a[0x190 / 4];
        call(s, r, 0x4c8220, g->actorToken + 0x188, {e[0x318 / 4]});
        put(s, r, 0x478, 4000);
        put(s, r, 0x474, g->tick);
        animate(s, r);
        break;
    case 0x48b730:
        if (word(s, r, 0x468) <= g->tick - word(s, r, 0x464)) {
            put(s, r, 0x468, 1000);
            put(s, r, 0x464, g->tick);
            int32_t which = int32_t(call(s, r, 0x4a3050, 0)) % 2;
            if (which == 0 || which == 1) {
                e[0x134 / 4] = a[0x190 / 4];
                call(s, r, 0x4c8220, g->actorToken + 0x188, {e[(0x318 + uint32_t(which) * 4) / 4]});
                animate(s, r);
            }
        }
        if (nearPlayer(s, r))
            virt(s, r, 0x44);
        else if (word(s, r, 0x478) <= g->tick - word(s, r, 0x474) && !h->clockCountdown &&
                 int32_t(call(s, r, 0x4a3050, 0)) % 100 < 5)
            invoke(s, r, 0x44edd0);
        break;
    case 0x48b880: {
        e[9] = s->primary[7];
        s->primary[7] = stateID(s, r, "LS_FIRING");
        mirror(s, e[0x18c / 4] == 2);
        uint32_t ani;
        if (x->difficulty == 2 && g->playerActor[0xcc / 4] == 5) {
            ani = resource(s, r, h->sequenceRegistryToken, "LEVEL_SOLDIER_STRIKE2");
            if (!ani)
                ani = resource(s, r, h->sequenceRegistryToken, "GAME_NULL");
        } else {
            ani = resource(s, r, h->sequenceRegistryToken, "LEVEL_SOLDIER_STRIKE");
            if (!ani)
                ani = resource(s, r, h->sequenceRegistryToken, "GAME_NULL");
        }
        e[0x370 / 4] = ani;
        bool left = a[0x40 / 4] & 2;
        put(s, r, 0x454, left ? 65 : uint32_t(-65));
        put(s, r, 0x45c, left ? 500 : uint32_t(-500));
        put(s, r, 0x458, x->difficulty == 2 && g->playerActor[0xcc / 4] == 5 ? 10 : uint32_t(-38));
        e[0x134 / 4] = a[0x190 / 4];
        call(s, r, 0x4c8220, g->actorToken + 0x188, {e[0x370 / 4]});
        e[0x1a0 / 4] = 0;
        break;
    }
    case 0x48ba00: {
        uint32_t ani = uint32_t(call(s, r, 0x4c82a0, g->actorToken + 0x188, {g->animationDelta}));
        if (ani == 1 && !e[0x1a0 / 4]) {
            e[0x1a0 / 4] = 1;
            if (!projectile(s, r))
                break;
        }
        if (a[0x1a4 / 4] && !a[0x19c / 4])
            virt(s, r, 0x44);
    } break;
    case 0x48aff0:
        e[0] = 0x50b16c;
        call(s, r, 0x4dbcd0, g->enemyToken + 0x2f4);
        call(s, r, 0x4f6584, g->enemyToken + 0x1a8);
        call(s, r, 0x4f6584, g->enemyToken + 0x1a4);
        e[0] = 0x50b014;
        break;
    case 0x48afd0: {
        uint32_t receiver = g->enemyToken;
        invoke(s, r, 0x48aff0);
        if (arg & 1)
            call(s, r, 0x4f6428, 0, {receiver});
        value = receiver;
        break;
    }
    case 0x405000:
        std::copy(e + 0x210 / 4, e + 0x220 / 4, a + 0x138 / 4);
        if (a[0x40 / 4] & 2) {
            uint32_t old = a[0x138 / 4];
            a[0x138 / 4] = 0u - a[0x140 / 4];
            a[0x140 / 4] = 0u - old;
        }
        break;
    case 0x4c96b0:
        break;
    default:
        if (claw_common_enemy_entry(s, h, fn, arg, forward, &r, &value))
            break;
        if (claw_human_enemy_entry(s, h, fn, arg, forward, &r, &value))
            break;
        if (x->combat && claw_human_combat_entry(s, x->combat, fn, arg, forward, &r, &value))
            break;
        if (x->motion && claw_enemy_motion_aux_entry(s, x->motion, fn, arg, forward, &r, &value))
            break;
        if (claw_generic_enemy_state_entry(s, g, h->sharedStates, fn, arg, forward, &r))
            break;
        if (claw_generic_enemy_entry(s, g, fn, arg, forward, &r))
            break;
        return 0;
    }
    if (result)
        *result = value;
    return 1;
}
} // namespace
extern "C" uint32_t claw_soldier_private_word(const ClawSoldier *s, const ClawSoldierContext *x, uint32_t off) {
    if (!s || !x || !x->human || off % 4 || off >= 0x480)
        return 0;
    return off < 0x420 ? s->enemy[off / 4] : x->human->privateTail[(off - 0x420) / 4];
}
extern "C" void claw_soldier_set_private_word(ClawSoldier *s, ClawSoldierContext *x, uint32_t off, uint32_t value) {
    if (!s || !x || !x->human || off % 4 || off >= 0x480)
        return;
    if (off < 0x420)
        s->enemy[off / 4] = value;
    else
        x->human->privateTail[(off - 0x420) / 4] = value;
}
extern "C" void claw_soldier_context_defaults(ClawSoldierContext *x) {
    if (!x || !x->human || !x->human->generic)
        return;
    const uint32_t v[] = {0x48afd0, 0x44d000, 0x48b0c0, 0x44d3c0, 0x405000, 0x44df60, 0x4bb030, 0x4c96b0, 0x44cfd0,
                          0x43dfa0, 0x404dd0, 0x44d460, 0x44d570, 0x44d5a0, 0x44d700, 0x44d730, 0x44d760, 0x44d9f0,
                          0x48b6b0, 0x43ed70, 0x43eee0, 0x43ee10, 0x43efe0, 0x44e0c0, 0x43f640, 0x43f740, 0x43fa10,
                          0x43fcb0, 0x43fd60, 0x43fe00, 0x44dbb0, 0x43ffa0, 0x404e00, 0x44de30, 0x44df10, 0x4407d0,
                          0x43f500, 0x4409d0, 0x440b20, 0x440c90, 0x440410, 0x48b670, 0x404e10};
    std::copy(v, v + 43, x->human->generic->virtualFunctions);
}
extern "C" uint32_t claw_soldier_construct(ClawSoldier *s, ClawSoldierContext *x, ClawGenericEnemyDependency d,
                                           void *user) {
    if (!s || !x || !x->human || !x->human->generic || !x->human->sharedStates || !x->human->privateTail)
        return 0;
    Run r{x, d, user};
    auto *h = x->human;
    auto *g = h->generic;
    auto *e = s->enemy;
    auto *a = s->actor;
    uint32_t value;
    invoke(s, r, 0x44c000, g->actorToken, true);
    for (uint32_t off = 0x464; off <= 0x478; off += 4)
        put(s, r, off, 0);
    e[0] = 0x50f774;
    call(s, r, 0x4c7970, g->actorToken, {}, "LEVEL_SOLDIER");
    if (e[0x2fc / 4] <= 8)
        call(s, r, 0x4dbd20, g->enemyToken + 0x2f4, {8});
    else if (e[0x2fc / 4] <= 32)
        e[0x300 / 4] |= 0x100;
    else if (g->bitWords && g->bitWordCount)
        g->bitWords[0] |= 0x100;
    else
        x->fault = 1;
    put(s, r, 0x450, 0);
    const char *names[] = {"LEVEL_SOLDIER_ADVANCE",     "LEVEL_SOLDIER_FASTADVANCE", "LEVEL_SOLDIER_STRIKE1",
                           "LEVEL_SOLDIER_STRIKE",      "LEVEL_SOLDIER_STAND",       "LEVEL_SOLDIER_STAND1",
                           "LEVEL_SOLDIER_FALL",        "LEVEL_SOLDIER_FALL",        "LEVEL_SOLDIER_HITLOW",
                           "LEVEL_SOLDIER_HITHIGH",     "LEVEL_SOLDIER_JUMP",        "LEVEL_SOLDIER_HOME",
                           "LEVEL_SOLDIER_FASTADVANCE", "LEVEL_SOLDIER_LIFTED",      "LEVEL_SOLDIER_LIFTED2",
                           "LEVEL_SOLDIER_LIFTED2",     "LEVEL_SOLDIER_THROWN"};
    const uint32_t offsets[] = {0x308, 0x30c, 0x310, 0x370, 0x318, 0x31c, 0x32c, 0x374, 0x334,
                                0x338, 0x33c, 0x344, 0x34c, 0x378, 0x37c, 0x380, 0x36c};
    for (size_t n = 0; n < 17; ++n) {
        uint32_t t = resource(s, r, h->sequenceRegistryToken, names[n]);
        if (!t)
            t = resource(s, r, h->sequenceRegistryToken, "GAME_NULL");
        e[offsets[n] / 4] = t;
    }
    const char *sounds[] = {"LEVEL_SOLDIER_00320006", "LEVEL_SOLDIER_00340016",     "LEVEL_SOLDIER_00320005",
                            "LEVEL_SOLDIER_00320005", "LEVEL_SOLDIER_RFHEADBT8-22", "LEVEL_SOLDIER_SOLGUNFR8-22",
                            "LEVEL_SOLDIER_00320020"};
    const uint32_t soundOffsets[] = {0x3a4, 0x410, 0x414, 0x418, 0x3a0, 0x3b4, 0x460};
    for (size_t n = 0; n < 7; ++n)
        put(s, r, soundOffsets[n], resource(s, r, g->soundRegistryToken, sounds[n]));
    const uint32_t attack[] = {uint32_t(-77), uint32_t(-50), 0, uint32_t(-30)},
                   tiny[] = {uint32_t(-1), uint32_t(-1), 1, 1}, movement[] = {uint32_t(-11), uint32_t(-60), 11, 50},
                   alternate[] = {uint32_t(-41), uint32_t(-23), 43, 31}, hit[] = {uint32_t(-15), uint32_t(-50), 15, 50};
    std::copy(attack, attack + 4, e + 0x220 / 4);
    std::copy(tiny, tiny + 4, e + 0x210 / 4);
    std::copy(movement, movement + 4, e + 0x250 / 4);
    std::copy(alternate, alternate + 4, e + 0x260 / 4);
    std::copy(movement, movement + 4, a + 0x118 / 4);
    std::copy(hit, hit + 4, a + 0x128 / 4);
    const uint32_t ranges[] = {400, 50, 300, 50, 300, 50, 80, 50, 80, 50};
    std::copy(ranges, ranges + 10, e + 0x28c / 4);
    e[0x2b4 / 4] = e[0x2b8 / 4] = 0;
    e[0x2bc / 4] = uint32_t(-65);
    e[0x2c0 / 4] = uint32_t(-20);
    e[0x2c4 / 4] = 20;
    e[0x2c8 / 4] = uint32_t(-15);
    e[0x2e4 / 4] = 25;
    uint32_t range = truncLow(mul(double(h->rangeScale), 25));
    e[0x2e4 / 4] = range < 100 ? 99 : range;
    a[0x10c / 4] = x->difficulty == 1 ? 3 : 7;
    a[0x10c / 4] = truncLow(mul(double(int32_t(a[0x10c / 4])), double(h->healthScale)));
    a[0x104 / 4] = 10;
    a[0x104 / 4] = truncLow(mul(double(int32_t(a[0x104 / 4])), double(h->damageScale)));
    a[0x50 / 4] -= 32;
    call(s, r, 0x4cd800, g->tileManagerToken, {g->actorToken, 0});
    a[0xcc / 4] = 1;
    execute(s, r, 0x48b6b0, 0, &value);
    propagate(x);
    return g->enemyToken;
}
extern "C" uint32_t claw_soldier_tick(ClawSoldier *s, ClawSoldierContext *x, ClawGenericEnemyDependency d, void *user) {
    if (!s || !x || !x->human || !x->human->generic)
        return 0;
    Run r{x, d, user};
    auto *g = x->human->generic;
    switch (s->primary[7]) {
    case 0: {
        s->primary[7] = 1000;
        uint32_t token = uint32_t(call(s, r, 0x4f63ec, 0, {0x480}));
        if (!token) {
            x->fault = 2;
            return 0;
        }
        g->enemyToken = token;
        if (!claw_soldier_construct(s, x, d, user))
            return 0;
        virt(s, r, 0x10);
        s->primary[0x18 / 4] = token;
        break;
    }
    case 29:
        virt(s, r, 0x20);
        break;
    case 30:
        virt(s, r, 0x1c);
        break;
    case 1000:
        break;
    default:
        if (!claw_generic_enemy_tick(s, g, forward, &r)) {
            x->fault = 1;
            return 0;
        }
        break;
    }
    propagate(x);
    return 1;
}
extern "C" uint32_t claw_soldier_entry(ClawSoldier *s, ClawSoldierContext *x, uint32_t fn, uint32_t arg,
                                       ClawGenericEnemyDependency d, void *user, uint32_t *result) {
    if (!s || !x || !x->human || !x->human->generic || !x->human->sharedStates || !x->human->privateTail)
        return 0;
    Run r{x, d, user};
    if (fn == 0x48aa40) {
        uint32_t t = claw_soldier_construct(s, x, d, user);
        if (result)
            *result = t;
        return t ? 1 : 0;
    }
    if (fn == 0x48a980) {
        uint32_t status = claw_soldier_tick(s, x, d, user);
        if (result)
            *result = status;
        return status;
    }
    uint32_t support = execute(s, r, fn, arg, result);
    propagate(x);
    return support;
}
