#include "OfficerLogic.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
#pragma STDC FP_CONTRACT OFF
namespace {
double mul(double a, double b) {
    volatile double v = a * b;
    return v;
}
void store(uint32_t *p, size_t offset, double value) {
    std::memcpy(p + offset / 4, &value, 8);
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
struct Invocation {
    ClawOfficerContext *c;
    ClawGenericEnemyDependency d;
    void *user;
};
uint64_t call(ClawOfficer *s, Invocation &i, uint32_t function, uint32_t receiver,
              std::initializer_list<uint32_t> args = {}, const char *name = nullptr) {
    ClawGenericEnemyCall e{};
    e.function = function;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), e.arguments);
    e.name = name;
    return i.d ? i.d(s, &i.c->generic, &e, i.user) : 0;
}
uint32_t execute(ClawOfficer *, Invocation &, uint32_t, uint32_t, uint32_t *);
uint64_t bridge(ClawGenericEnemy *s, ClawGenericEnemyContext *, const ClawGenericEnemyCall *event, void *context) {
    auto &i = *static_cast<Invocation *>(context);
    uint32_t r = 0;
    if (event->receiver == i.c->generic.enemyToken &&
        execute(s, i, event->function, event->argumentCount ? event->arguments[0] : 0, &r))
        return r;
    return i.d ? i.d(s, &i.c->generic, event, i.user) : 0;
}
void virtualCall(ClawOfficer *s, Invocation &i, uint32_t slot, uint32_t arg = 0, bool hasArg = false) {
    const uint32_t f = i.c->generic.virtualFunctions[slot / 4];
    uint32_t result;
    if (execute(s, i, f, arg, &result))
        return;
    if (claw_generic_enemy_state_entry(s, &i.c->generic, &i.c->sharedStates, f, arg, bridge, &i))
        return;
    if (claw_generic_enemy_entry(s, &i.c->generic, f, arg, bridge, &i))
        return;
    if (hasArg)
        call(s, i, f, i.c->generic.enemyToken, {arg});
    else
        call(s, i, f, i.c->generic.enemyToken);
}
uint32_t lookup(ClawOfficer *s, Invocation &i, const char *name) {
    if (i.d)
        return uint32_t(call(s, i, 0x4dba00, 0x537668, {}, name));
    auto &g = i.c->generic;
    for (size_t n = 0; n < g.stateCount; ++n)
        if (g.states[n].name && std::strcmp(g.states[n].name, name) == 0)
            return uint32_t(g.states[n].state);
    i.c->fault = 3;
    return 0;
}
void mirror(ClawOfficer *s, bool desired) {
    auto *a = s->actor;
    auto *e = s->enemy;
    if (bool(a[0x40 / 4] & 2) == desired)
        return;
    const uint32_t old = e[0x138 / 4];
    e[0x138 / 4] = 0u - e[0x140 / 4];
    e[0x140 / 4] = 0u - old;
    a[0x40 / 4] = desired ? a[0x40 / 4] | 2 : a[0x40 / 4] & ~2u;
    for (size_t o : {0x118, 0x128, 0x138})
        if (a[o / 4] != 0x80000000) {
            const uint32_t left = a[o / 4];
            a[o / 4] = 0u - a[(o + 8) / 4];
            a[(o + 8) / 4] = 0u - left;
        }
}
uint32_t get(ClawOfficer *s, Invocation &i, uint32_t offset) {
    return claw_officer_private_word(s, i.c, offset);
}
void put(ClawOfficer *s, Invocation &i, uint32_t offset, uint32_t value) {
    claw_officer_set_private_word(s, i.c, offset, value);
}
uint32_t resource(ClawOfficer *s, Invocation &i, uint32_t registry, const char *name) {
    return uint32_t(call(s, i, 0x4f6286, registry, {}, name));
}
uint32_t execute(ClawOfficer *s, Invocation &i, uint32_t function, uint32_t argument, uint32_t *result) {
    auto *e = s->enemy;
    auto *a = s->actor;
    auto &c = *i.c;
    auto &g = c.generic;
    uint32_t r = 0;
    switch (function) {
    case 0x462af0: {
        const ClawGenericEnemyState *entry = nullptr;
        for (size_t n = 0; n < c.officerStateCount; ++n)
            if (c.officerStates[n].state == int32_t(argument)) {
                entry = c.officerStates + n;
                break;
            }
        if (!entry) {
            c.fault = 3;
            break;
        }
        if (entry->function) {
            if (!execute(s, i, entry->function, 0, &r))
                call(s, i, entry->function, g.enemyToken);
        } else
            call(s, i, 0x44c840, g.enemyToken, {argument});
        break;
    }
    case 0x462ef0:
        call(s, i, 0x44d000, g.enemyToken, {argument});
        std::copy(e + (g.playerActor[0xcc / 4] == 5 ? 0x240 : 0x230) / 4,
                  e + (g.playerActor[0xcc / 4] == 5 ? 0x250 : 0x240) / 4, e + 0x220 / 4);
        {
            const char *name = g.playerActor[0xcc / 4] == 5 ? "LEVEL_OFFICER_STRIKE1" : "LEVEL_OFFICER_STRIKE";
            uint32_t token = resource(s, i, c.sequenceRegistryToken, name);
            if (!token)
                token = resource(s, i, c.sequenceRegistryToken, "GAME_NULL");
            e[0x310 / 4] = token;
        }
        break;
    case 0x463020:
        mirror(s, e[0x18c / 4] == 2);
        call(s, i, 0x4a3050, 0);
        if (int32_t(e[0x184 / 4]) >= 0 && int32_t(e[0x184 / 4]) < 5) {
            if (int32_t(call(s, i, 0x4a3050, 0)) % 100 < 33 && a[0x38 / 4] != 0xffffffff)
                call(s, i, 0x48ceb0, 0, {g.actorToken, 0x529888, 0}, "LEVEL_OFFICER_00340024");
            virtualCall(s, i, 0x58);
        } else
            call(s, i, 0x44edd0, g.enemyToken);
        break;
    case 0x463120: {
        store(e, 0x50, 0);
        if (int32_t(call(s, i, 0x4a3050, 0)) % 100 < 33) {
            const uint32_t value = uint32_t(call(s, i, 0x4a3050, 0));
            const uint32_t sign = uint32_t(int32_t(value) >> 31);
            const int32_t which = int32_t((((value ^ sign) - sign) & 1) ^ sign) - int32_t(sign);
            if (a[0x38 / 4] != 0xffffffff)
                call(s, i, 0x48ce40, 0, {g.actorToken, get(s, i, uint32_t(0x450 + which * 4)), 0});
        }
        e[0x24 / 4] = s->primary[7];
        s->primary[7] = lookup(s, i, "LS_IDLE");
        e[0x134 / 4] = a[0x190 / 4];
        call(s, i, 0x4c8220, g.actorToken + 0x188, {e[0x318 / 4]});
        call(s, i, 0x4c82a0, g.actorToken + 0x188, {g.animationDelta});
        put(s, i, 0x46c, 4000);
        put(s, i, 0x468, g.tick);
        break;
    }
    case 0x4631e0:
        if (get(s, i, 0x45c) <= g.tick - get(s, i, 0x458)) {
            put(s, i, 0x45c, 1000);
            put(s, i, 0x458, g.tick);
            const int32_t which = int32_t(call(s, i, 0x4a3050, 0)) % 5;
            if (which >= 0 && which < 5) {
                e[0x134 / 4] = a[0x190 / 4];
                call(s, i, 0x4c8220, g.actorToken + 0x188, {e[(0x318 + which * 4) / 4]});
                call(s, i, 0x4c82a0, g.actorToken + 0x188, {g.animationDelta});
            }
        }
        if (e[0x184 / 4] < 5)
            virtualCall(s, i, 0x44);
        else if ((e[0x184 / 4] == 5 || e[0x184 / 4] == 6) && get(s, i, 0x46c) <= g.tick - get(s, i, 0x468) &&
                 int32_t(call(s, i, 0x4a3050, 0)) % 100 < 20)
            call(s, i, 0x44edd0, g.enemyToken);
        break;
    case 0x463310: {
        const char *name =
            int32_t(call(s, i, 0x4a3050, 0)) % 100 < 50 ? "LEVEL_OFFICER_00340017" : "LEVEL_OFFICER_00340018";
        e[0x410 / 4] = resource(s, i, g.soundRegistryToken, name);
        call(s, i, 0x44df10, g.enemyToken);
        break;
    }
    case 0x4c96b0:
        break; // Verified shared empty virtual destructor-stage callback.
    case 0x405000:
        std::copy(e + 0x210 / 4, e + 0x220 / 4, a + 0x138 / 4);
        if (a[0x40 / 4] & 2) {
            const uint32_t old = a[0x138 / 4];
            a[0x138 / 4] = 0u - a[0x140 / 4];
            a[0x140 / 4] = 0u - old;
        }
        break;
    case 0x462a20:
        e[0] = 0x50b16c;
        call(s, i, 0x4dbcd0, g.enemyToken + 0x2f4);
        call(s, i, 0x4f6584, g.enemyToken + 0x1a8);
        call(s, i, 0x4f6584, g.enemyToken + 0x1a4);
        e[0] = 0x50b014;
        break;
    case 0x462a00:
        execute(s, i, 0x462a20, 0, &r);
        if (argument & 1)
            call(s, i, 0x4f6428, 0, {g.enemyToken});
        r = g.enemyToken;
        break;
    default:
        return 0;
    }
    if (result)
        *result = r;
    return 1;
}
} // namespace
uint32_t claw_officer_private_word(const ClawOfficer *s, const ClawOfficerContext *c, uint32_t offset) {
    if (!s || !c || offset % 4 || offset >= 0x470)
        return 0;
    return offset < 0x420 ? s->enemy[offset / 4] : c->privateTail[(offset - 0x420) / 4];
}
void claw_officer_set_private_word(ClawOfficer *s, ClawOfficerContext *c, uint32_t offset, uint32_t value) {
    if (!s || !c || offset % 4 || offset >= 0x470)
        return;
    if (offset < 0x420)
        s->enemy[offset / 4] = value;
    else
        c->privateTail[(offset - 0x420) / 4] = value;
}
void claw_officer_context_defaults(ClawOfficerContext *c) {
    if (!c)
        return;
    claw_generic_enemy_context_defaults(&c->generic);
    c->damageScale = c->healthScale = c->rangeScale = 1;
    const uint32_t v[] = {0x462a00, 0x462ef0, 0x462af0, 0x44d3c0, 0x405000, 0x44df60, 0x4bb030, 0x4c96b0, 0x44cfd0,
                          0x43dfa0, 0x404dd0, 0x44d460, 0x44d570, 0x44d5a0, 0x44d700, 0x44d730, 0x44d760, 0x44d9f0,
                          0x463120, 0x43ed70, 0x43eee0, 0x43ee10, 0x43efe0, 0x44e0c0, 0x43f640, 0x43f740, 0x43fa10,
                          0x43fcb0, 0x43fd60, 0x43fe00, 0x44dbb0, 0x43ffa0, 0x404e00, 0x44de30, 0x463310, 0x4407d0,
                          0x43f500, 0x4409d0, 0x440b20, 0x440c90, 0x440410, 0x4bb030, 0x404e10};
    std::copy(v, v + 43, c->generic.virtualFunctions);
}
uint32_t claw_officer_construct(ClawOfficer *s, ClawOfficerContext *c, ClawGenericEnemyDependency dependency,
                                void *user) {
    if (!s || !c)
        return 0;
    Invocation i{c, dependency, user};
    auto *e = s->enemy;
    auto *a = s->actor;
    auto &g = c->generic;
    if (!dependency) {
        c->fault = 3;
        return 0;
    }
    call(s, i, 0x44c000, g.enemyToken, {g.actorToken});
    for (uint32_t offset = 0x458; offset <= 0x46c; offset += 4)
        put(s, i, offset, 0);
    e[0] = 0x50ea0c;
    call(s, i, 0x4c7970, g.actorToken, {}, "LEVEL_OFFICER");
    const char *names[] = {
        "LEVEL_OFFICER_ADVANCE", "LEVEL_OFFICER_FASTADVANCE", "LEVEL_OFFICER_STRIKE",  "LEVEL_OFFICER_STAND1",
        "LEVEL_OFFICER_STAND2",  "LEVEL_OFFICER_STAND3",      "LEVEL_OFFICER_STAND4",  "LEVEL_OFFICER_STAND5",
        "LEVEL_OFFICER_FALL",    "LEVEL_OFFICER_FALL",        "LEVEL_OFFICER_HITLOW",  "LEVEL_OFFICER_HITHIGH",
        "LEVEL_OFFICER_JUMP",    "LEVEL_OFFICER_JUMP",        "LEVEL_OFFICER_HOME",    "LEVEL_OFFICER_FASTADVANCE",
        "LEVEL_OFFICER_LIFTED",  "LEVEL_OFFICER_LIFTED2",     "LEVEL_OFFICER_LIFTED2", "LEVEL_OFFICER_THROWN"};
    const uint32_t offsets[] = {0x308, 0x30c, 0x310, 0x318, 0x31c, 0x320, 0x324, 0x328, 0x32c, 0x374,
                                0x334, 0x338, 0x33c, 0x340, 0x344, 0x34c, 0x378, 0x37c, 0x380, 0x36c};
    for (size_t n = 0; n < 20; ++n) {
        uint32_t token = resource(s, i, c->sequenceRegistryToken, names[n]);
        if (!token)
            token = resource(s, i, c->sequenceRegistryToken, "GAME_NULL");
        e[offsets[n] / 4] = token;
    }
    e[0x3a4 / 4] =
        resource(s, i, g.soundRegistryToken,
                 int32_t(call(s, i, 0x4a3050, 0)) % 100 < 50 ? "LEVEL_OFFICER_00340014" : "LEVEL_OFFICER_00340015");
    e[0x410 / 4] = resource(s, i, g.soundRegistryToken, "LEVEL_OFFICER_00340017");
    e[0x3a0 / 4] = resource(s, i, g.soundRegistryToken, "LEVEL_OFFICER_OFCSWSTB8-22");
    put(s, i, 0x450, resource(s, i, g.soundRegistryToken, "LEVEL_OFFICER_EHEM1"));
    put(s, i, 0x454, resource(s, i, g.soundRegistryToken, "LEVEL_OFFICER_EHEM2"));
    const uint32_t high[] = {uint32_t(-137), uint32_t(-27), 0, uint32_t(-7)}, low[] = {uint32_t(-137), 20, 0, 40},
                   tiny[] = {uint32_t(-1), uint32_t(-1), 1, 1}, movement[] = {uint32_t(-20), uint32_t(-60), 20, 51},
                   alternate[] = {uint32_t(-48), uint32_t(-44), 42, 19};
    std::copy(high, high + 4, e + 0x230 / 4);
    std::copy(low, low + 4, e + 0x240 / 4);
    std::copy(high, high + 4, e + 0x220 / 4);
    std::copy(tiny, tiny + 4, e + 0x210 / 4);
    std::copy(movement, movement + 4, e + 0x250 / 4);
    std::copy(alternate, alternate + 4, e + 0x260 / 4);
    for (size_t n = 0; n < 5; ++n) {
        e[(0x28c + n * 8) / 4] = 100;
        e[(0x290 + n * 8) / 4] = 40;
    }
    a[0x128 / 4] = uint32_t(-20);
    a[0x12c / 4] = uint32_t(-50);
    a[0x130 / 4] = 20;
    a[0x134 / 4] = 50;
    std::copy(e + 0x250 / 4, e + 0x260 / 4, a + 0x118 / 4);
    e[0x2b8 / 4] = uint32_t(-10);
    e[0x2b4 / 4] = 10;
    e[0x2bc / 4] = uint32_t(-45);
    e[0x2c0 / 4] = uint32_t(-20);
    e[0x2c4 / 4] = 20;
    e[0x2c8 / 4] = uint32_t(-15);
    e[0x2e4 / 4] = 50;
    const uint32_t range = truncLow(mul(double(c->rangeScale), 50));
    e[0x2e4 / 4] = range < 100 ? 99 : range;
    a[0x10c / 4] = c->difficulty == 1 ? 3 : 7;
    a[0x10c / 4] = truncLow(mul(double(int32_t(a[0x10c / 4])), double(c->healthScale)));
    a[0x104 / 4] = 10;
    a[0x104 / 4] = truncLow(mul(double(int32_t(a[0x104 / 4])), double(c->damageScale)));
    a[0x50 / 4] -= 32;
    call(s, i, 0x4cd800, g.tileManagerToken, {g.actorToken, 0});
    a[0xcc / 4] = 1;
    uint32_t result;
    execute(s, i, 0x463120, 0, &result);
    return g.enemyToken;
}
uint32_t claw_officer_tick(ClawOfficer *s, ClawOfficerContext *c, ClawGenericEnemyDependency dependency, void *user) {
    if (!s || !c)
        return 0;
    Invocation i{c, dependency, user};
    switch (s->primary[7]) {
    case 0: {
        s->primary[7] = 1000;
        const uint32_t token = uint32_t(call(s, i, 0x4f63ec, 0, {0x470}));
        if (!token) {
            c->fault = 1;
            return 0;
        }
        c->generic.enemyToken = token;
        if (!claw_officer_construct(s, c, dependency, user))
            return 0;
        virtualCall(s, i, 0x10);
        s->primary[0x18 / 4] = token;
        break;
    }
    case 29:
        virtualCall(s, i, 0x20);
        break;
    case 30:
        virtualCall(s, i, 0x1c);
        break;
    case 1000:
        break;
    default:
        if (!claw_generic_enemy_tick(s, &c->generic, bridge, &i)) {
            c->fault = 3;
            return 0;
        }
        break;
    }
    return 1;
}
uint32_t claw_officer_entry(ClawOfficer *s, ClawOfficerContext *c, uint32_t function, uint32_t argument,
                            ClawGenericEnemyDependency dependency, void *user, uint32_t *result) {
    if (!s || !c)
        return 0;
    Invocation i{c, dependency, user};
    if (function == 0x462410) {
        const uint32_t token = claw_officer_construct(s, c, dependency, user);
        if (result)
            *result = token;
        return token ? 1 : 0;
    }
    if (function == 0x462350) {
        const uint32_t status = claw_officer_tick(s, c, dependency, user);
        if (result)
            *result = status;
        return status;
    }
    return execute(s, i, function, argument, result);
}
