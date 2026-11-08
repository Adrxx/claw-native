#include "GenericEnemyStates.h"
#include "V13EnemyDeathSound.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
#pragma STDC FP_CONTRACT OFF
static uint32_t stateEntry(ClawGenericEnemy *, ClawGenericEnemyContext *, ClawGenericEnemyStatesContext *,
                           uint32_t, uint32_t, ClawGenericEnemyDependency, void *, bool);
namespace {
// Selected once by the native app; oracle processes retain the v1.0 default.
bool useV13 = false;
double load(const uint32_t *p, size_t o) {
    double v;
    std::memcpy(&v, p + o / 4, 8);
    return v;
}
void store(uint32_t *p, size_t o, double v) {
    std::memcpy(p + o / 4, &v, 8);
}
double sub(double a, double b) {
    volatile double v = a - b;
    return v;
}
double mul(double a, double b) {
    volatile double v = a * b;
    return v;
}
uint32_t truncLow(double value) {
    uint64_t b;
    std::memcpy(&b, &value, 8);
    int e = int((b >> 52) & 0x7ff) - 1023;
    if (e < 0 || e >= 63)
        return 0;
    uint64_t m = (b & 0xfffffffffffffULL) | 0x10000000000000ULL;
    m = e >= 52 ? m << (e - 52) : m >> (52 - e);
    return b >> 63 ? 0u - uint32_t(m) : uint32_t(m);
}
uint64_t call(ClawGenericEnemy *s, ClawGenericEnemyContext *c, ClawGenericEnemyDependency d, void *u, uint32_t f,
              uint32_t receiver, std::initializer_list<uint32_t> args = {}, const char *name = nullptr) {
    ClawGenericEnemyCall e{};
    e.function = f;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    e.name = name;
    std::copy(args.begin(), args.end(), e.arguments);
    return d ? d(s, c, &e, u) : 0;
}
bool valid(ClawGenericEnemy *s, ClawGenericEnemyContext *c, ClawGenericEnemyStatesContext *x) {
    return s && c && x && (!c->stateCount || c->states) && (!x->resourceCount || x->resources) &&
           (s->enemy[0x2fc / 4] <= 32 || (c->bitWords && c->bitWordCount >= 1));
}
const ClawGenericEnemyState *state(ClawGenericEnemyContext *c, int32_t id) {
    for (size_t i = 0; i < c->stateCount; ++i)
        if (c->states[i].state == id)
            return &c->states[i];
    return nullptr;
}
bool transition(ClawGenericEnemy *s, ClawGenericEnemyContext *c, const char *name, ClawGenericEnemyDependency d,
                void *u) {
    s->enemy[0x24 / 4] = s->primary[7];
    uint32_t id = 0;
    if (d)
        id = uint32_t(call(s, c, d, u, 0x4dba00, 0x537668, {}, name));
    else {
        const ClawGenericEnemyState *found = nullptr;
        for (size_t i = 0; i < c->stateCount; ++i)
            if (c->states[i].name && std::strcmp(c->states[i].name, name) == 0) {
                found = &c->states[i];
                break;
            }
        if (!found)
            return false;
        id = uint32_t(found->state);
    }
    s->primary[7] = id;
    return true;
}
void virtualCall(ClawGenericEnemy *s, ClawGenericEnemyContext *c, ClawGenericEnemyStatesContext *x, uint32_t slot,
                 uint32_t arg, bool hasArg, ClawGenericEnemyDependency d, void *u, bool v13) {
    const uint32_t f = c->virtualFunctions[slot / 4];
    if (stateEntry(s, c, x, f, arg, d, u, v13))
        return;
    if (claw_generic_enemy_entry(s, c, f, arg, d, u))
        return;
    if (hasArg)
        call(s, c, d, u, f, c->enemyToken, {arg});
    else
        call(s, c, d, u, f, c->enemyToken);
}
uint32_t animate(ClawGenericEnemy *s, ClawGenericEnemyContext *c, ClawGenericEnemyDependency d, void *u) {
    return uint32_t(call(s, c, d, u, 0x4c82a0, c->actorToken + 0x188, {c->animationDelta}));
}
void select(ClawGenericEnemy *s, ClawGenericEnemyContext *c, size_t offset, ClawGenericEnemyDependency d, void *u) {
    s->enemy[0x134 / 4] = s->actor[0x190 / 4];
    call(s, c, d, u, 0x4c8220, c->actorToken + 0x188, {s->enemy[offset / 4]});
}
void mirrorRect(uint32_t *words, size_t left) {
    const uint32_t old = words[left / 4];
    if (old != 0x80000000) {
        words[left / 4] = 0u - words[(left + 8) / 4];
        words[(left + 8) / 4] = 0u - old;
    }
}
void mirrorActor(uint32_t *words) {
    for (size_t offset : {0x118, 0x128, 0x138})
        mirrorRect(words, offset);
}
void mirror(ClawGenericEnemy *s, bool desired) {
    const bool current = (s->actor[0x40 / 4] & 2) != 0;
    if (current == desired)
        return;
    auto *e = s->enemy;
    const uint32_t old = e[0x138 / 4];
    e[0x138 / 4] = 0u - e[0x140 / 4];
    e[0x140 / 4] = 0u - old;
    s->actor[0x40 / 4] = desired ? s->actor[0x40 / 4] | 2 : s->actor[0x40 / 4] & ~2u;
    mirrorActor(s->actor);
}
void attackRect(ClawGenericEnemy *s, size_t source) {
    std::copy(s->enemy + source / 4, s->enemy + source / 4 + 4, s->actor + 0x138 / 4);
    if (s->actor[0x40 / 4] & 2) {
        const uint32_t old = s->actor[0x138 / 4];
        s->actor[0x138 / 4] = 0u - s->actor[0x140 / 4];
        s->actor[0x140 / 4] = 0u - old;
    }
}
bool audio(ClawGenericEnemy *s, ClawGenericEnemyContext *c, ClawGenericEnemyStatesContext *x, size_t offset,
           ClawGenericEnemyDependency d, void *u, bool v13 = false) {
    const uint32_t token = s->enemy[offset / 4];
    if (!token || !x->audioEnabled)
        return true;
    if (v13) {
        call(s, c, d, u, 0x4208e0, token, {x->audioPosition, 0, 0, 0});
        return true;
    }
    uint32_t receiver = 0;
    bool found = false;
    for (size_t i = 0; i < x->resourceCount; ++i)
        if (x->resources[i].token == token) {
            receiver = x->resources[i].controllerToken;
            found = true;
            break;
        }
    if (!found)
        return false;
    call(s, c, d, u, 0x4b45f0, receiver, {x->audioPosition, 0, 0, 0});
    return true;
}
void restoreMovementRect(ClawGenericEnemy *s) {
    s->actor[0x50 / 4] += s->actor[0x124 / 4] - s->enemy[0x27c / 4];
    std::copy(s->enemy + 0x270 / 4, s->enemy + 0x280 / 4, s->actor + 0x118 / 4);
}
} // namespace
uint32_t claw_generic_enemy_state_dispatch(ClawGenericEnemy *s, ClawGenericEnemyContext *c,
                                           ClawGenericEnemyStatesContext *x, int32_t id, ClawGenericEnemyDependency d,
                                           void *u) {
    if (!valid(s, c, x))
        return 0;
    const auto *entry = state(c, id);
    if (!entry)
        return 0;
    if (claw_generic_enemy_state_entry(s, c, x, entry->function, 0, d, u))
        return 1;
    return claw_generic_enemy_dispatch(s, c, id, d, u);
}
static uint32_t stateEntry(ClawGenericEnemy *s, ClawGenericEnemyContext *c,
                           ClawGenericEnemyStatesContext *x, uint32_t f, uint32_t arg,
                           ClawGenericEnemyDependency d, void *u, bool v13) {
    if (!valid(s, c, x))
        return 0;
    auto *e = s->enemy;
    auto *a = s->actor;
    switch (f) {
    case 0x404ed0:
        return transition(s, c, "LS_HOME", d, u);
    case 0x404f00:
        return transition(s, c, "LS_IDLE", d, u);
    case 0x4c9e30:
        return 1;
    case 0x43e9c0:
        e[0x3d4 / 4] = arg;
        e[0x3d0 / 4] = c->tick;
        return 1;
    case 0x43f120: {
        // Constructed common enemies have size32. Original undersized bitset growth
        // performs heap allocation and is outside this declared state profile.
        if (e[0x2fc / 4] < 5)
            return 0;
        e[0x304 / 4] = arg;
        if (!transition(s, c, "LS_DEAD", d, u))
            return 0;
        e[8] = 1;
        a[2] |= 0x80;
        e[0x3d4 / 4] = 0;
        e[0x3d0 / 4] = c->tick;
        switch (e[0x304 / 4]) {
        case 0:
            if (e[0x2fc / 4] <= 32)
                e[0x300 / 4] = v13 ? claw_v13_enemy_dead_bits(e[0x300 / 4]) : e[0x300 / 4] ^ 1;
            else
                c->bitWords[0] = v13 ? claw_v13_enemy_dead_bits(c->bitWords[0]) : c->bitWords[0] ^ 1;
            if (a[0x64 / 4] != 0x2134) {
                a[0x64 / 4] = 0x2134;
                a[2] |= 0x20000;
            }
            if (int32_t(call(s, c, d, u, 0x4a3050, 0)) % 100 < 25)
                call(s, c, d, u, 0x420370, 0, {x->attackerActor[0xd0 / 4]});
            else if (e[0x3a4 / 4])
                call(s, c, d, u, 0x4208e0, e[0x3a4 / 4], {x->audioPosition, 0, 0, 0});
            for (size_t axis = 0; axis < 3; ++axis) {
                store(e, 0x80 + axis * 8, load(c->defaults, 0));
                store(e, 0x98 + axis * 8, load(c->defaults, 8));
            }
            a[0xcc / 4] = 7;
            e[0x134 / 4] = a[0x190 / 4];
            call(s, c, d, u, 0x420a10, c->actorToken, {e[0x374 / 4], 0});
            store(e, 0x40, 2000);
            store(e, 0x50, e[0x18c / 4] == 3 ? 150 : -150);
            store(e, 0x58, -700);
            store(e, 0x60, 0);
            break;
        case 1:
            if (!audio(s, c, x, 0x3b0, d, u, v13))
                return 0;
            [[fallthrough]];
        case 2:
            if (e[0x304 / 4] == 2 && e[0x3a8 / 4])
                call(s, c, d, u, 0x4208e0, e[0x3a8 / 4], {x->audioPosition, 0, 0, 0});
            e[0xc8 / 4] = 1;
            a[0x48 / 4] = 30;
            a[0x44 / 4] = 0;
            a[0x40 / 4] |= 8;
            e[0x3dc / 4] = 1000;
            e[0x3d8 / 4] = c->tick;
            break;
        case 3:
            if (!audio(s, c, x, 0x3ac, d, u, v13))
                return 0;
            e[0xc8 / 4] = 1;
            a[2] |= 0x10000;
            break;
        default:
            break;
        }
        if (e[0x2fc / 4] <= 32)
            e[0x300 / 4] |= 16;
        else
            c->bitWords[0] |= 16;
        return 1;
    }
    case 0x43f030:
        if (animate(s, c, d, u) == 1 && x->strikeCounter) {
            --x->strikeCounter;
            if (!audio(s, c, x, 0x3a0, d, u))
                return 0;
            attackRect(s, 0x220);
        }
        if (a[0x1a4 / 4] && a[0x19c / 4] == 0) {
            x->strikeCounter = 1;
            virtualCall(s, c, x, 0x44, 0, false, d, u, v13);
            e[8] = 2;
        }
        return 1;
    case 0x43f450:
        animate(s, c, d, u);
        if (e[0x304 / 4] == 0) {
            if (a[0x38 / 4] != 0xffffffff)
                return 1;
            if (!audio(s, c, x, 0x38c, d, u))
                return 0;
        } else if (e[0x304 / 4] == 1 || e[0x304 / 4] == 2) {
            if (c->tick - e[0x3d8 / 4] < e[0x3dc / 4])
                return 1;
        } else
            return 1;
        a[2] |= 0x10000;
        return 1;
    case 0x43f720:
        a[2] &= ~4u;
        e[8] = 2;
        return 1;
    case 0x43f6e0:
        animate(s, c, d, u);
        if (a[0xcc / 4] == 1) {
            a[2] &= ~4u;
            e[8] = 2;
            virtualCall(s, c, x, 0x44, 0, false, d, u, v13);
        }
        return 1;
    case 0x43ff60:
        animate(s, c, d, u);
        if (a[0xcc / 4] == 1)
            virtualCall(s, c, x, 0x78, 0, false, d, u, v13);
        return 1;
    case 0x440070:
        if (animate(s, c, d, u) == 1 && !e[0x1a0 / 4]) {
            e[0x1a0 / 4] = 1;
            attackRect(s, 0x220);
        }
        if (a[0x1a4 / 4] && a[0x19c / 4] == 0)
            a[2] |= 0x10000;
        return 1;
    case 0x4405b0:
        if (c->playerActor[0x16c / 4] == 42) {
            select(s, c, 0x378, d, u);
            animate(s, c, d, u);
            const bool left = x->playerPrivate[0] == 0;
            mirror(s, left);
            store(e, 0x68, double(int32_t(e[(left ? 0x2c0 : 0x2c4) / 4] + c->playerActor[0x4c / 4])));
            store(e, 0x70, double(int32_t(e[0x2c8 / 4] + c->playerActor[0x50 / 4])));
        }
        if (c->playerActor[0x16c / 4] == 43)
            virtualCall(s, c, x, 0x8c, 0, false, d, u, v13);
        return 1;
    case 0x440260:
        animate(s, c, d, u);
        if (a[0xcc / 4] == 1) {
            e[8] = 2;
            a[2] &= ~2u;
            select(s, c, 0x380, d, u);
            animate(s, c, d, u);
            store(e, 0x50, 0);
            restoreMovementRect(s);
            a[0xd0 / 4] = 4;
            a[2] &= ~4u;
            virtualCall(s, c, x, 0x44, 0, false, d, u, v13);
        }
        return 1;
    case 0x43f540:
        if (e[0x3e4 / 4] <= c->tick - e[0x3e0 / 4]) {
            const auto *saved = state(c, int32_t(e[0x24 / 4]));
            if (!saved || !saved->name)
                return 0;
            return transition(s, c, saved->name, d, u);
        }
        return 1;
    case 0x440a50:
        animate(s, c, d, u);
        if (a[0xcc / 4] == 1)
            store(e, 0x50, 0);
        if (e[0x3f4 / 4] <= c->tick - e[0x3f0 / 4]) {
            a[2] &= ~2u;
            restoreMovementRect(s);
            a[2] &= ~4u;
            virtualCall(s, c, x, 0x44, 0, false, d, u, v13);
            a[2] &= ~1u;
            e[8] = 2;
        }
        return 1;
    case 0x43f980:
    case 0x43fc20: {
        animate(s, c, d, u);
        const double velocity = load(e, 0x50), position = load(e, 0x68), target = double(int32_t(e[0x280 / 4]));
        if ((velocity < 0 && position <= target) || (0 <= velocity && target < position) || (e[0x120 / 4] & 0x10000) ||
            position == double(int32_t(e[0x118 / 4])))
            virtualCall(s, c, x, 0x44, 0, false, d, u, v13);
        return 1;
    }
    case 0x440be0:
    case 0x440d50:
        animate(s, c, d, u);
        if (a[0x1a4 / 4] && a[0x19c / 4] == 0) {
            a[2] &= ~4u;
            virtualCall(s, c, x, 0x44, 0, false, d, u, v13);
            e[8] = 2;
            return 1;
        }
        if (load(e, 0x50) != 0)
            store(e, 0x50, sub(load(e, 0x50), e[0x18c / 4] == 3 ? 25 : -25));
        return 1;
    case 0x440870: {
        animate(s, c, d, u);
        const bool left = x->playerPrivate[0] == 0;
        mirror(s, left);
        const uint32_t step = e[0x2cc / 4] ? (left ? 4u : 0u - 4u) : 0;
        store(e, 0x68, double(int32_t(e[(left ? 0x2b4 : 0x2b8) / 4] + step + c->playerActor[0x4c / 4])));
        store(e, 0x70, double(int32_t(e[0x2bc / 4] + (e[0x2cc / 4] ? 5u : 0u) + c->playerActor[0x50 / 4])));
        return 1;
    }
    case 0x4dc830:
        virtualCall(s, c, x, 0x14, 0, false, d, u, v13);
        return 1;
    case 0x4dc850:
        virtualCall(s, c, x, 0x18, 0, false, d, u, v13);
        return 1;
    case 0x43e9e0: {
        const uint32_t counter = x->playerPrivate[0xe8 / 4];
        if (counter == e[0x19c / 4])
            return 1;
        e[0x19c / 4] = counter;
        if (c->tick - e[0x3d0 / 4] < e[0x3d4 / 4])
            return 1;
        uint32_t slot = 0;
        switch (x->attackerActor[0xd0 / 4]) {
        case 2:
            slot = 0x2c;
            break;
        case 0x20:
            slot = 0x30;
            break;
        case 0x2000000:
            slot = 0x34;
            break;
        case 0x10:
            slot = 0x38;
            break;
        case 0x1000000:
            slot = 0x3c;
            break;
        case 0x1000:
            slot = 0x40;
            break;
        }
        if (slot)
            virtualCall(s, c, x, slot, a[0x74 / 4], true, d, u, v13);
        if (int32_t(a[0x10c / 4]) < 1)
            virtualCall(s, c, x, 0x5c, 0, true, d, u, v13);
        return 1;
    }
    case 0x404dd0:
        if (int32_t(a[0x10c / 4]) > 0)
            a[0x10c / 4] -= x->attackerActor[0x104 / 4];
        return 1;
    case 0x404eb0:
        virtualCall(s, c, x, 0x28, arg, true, d, u, v13);
        return stateEntry(s, c, x, 0x440e20, arg, d, u, v13);
    case 0x440e20: {
        const uint32_t px = truncLow(load(e, 0x68)), py = truncLow(load(e, 0x70));
        uint32_t y = py;
        if (x->attackerActor[0x138 / 4] != 0x80000000) {
            y = uint32_t(int32_t(x->attackerActor[0x13c / 4] + x->attackerActor[0x144 / 4]) / 2) +
                x->attackerActor[0x50 / 4];
            const uint32_t top = a[0x12c / 4] + py, bottom = a[0x134 / 4] + py;
            if (int32_t(y) <= int32_t(top))
                y = top;
            if (int32_t(bottom) <= int32_t(y))
                y = bottom;
        }
        const uint32_t z = a[0x64 / 4];
        const int32_t dy = int32_t(call(s, c, d, u, 0x4a3050, 0)) % 9 - 4,
                      dx = int32_t(call(s, c, d, u, 0x4a3050, 0)) % 9 - 4;
        call(s, c, d, u, 0x461a00, 0, {a[0xc / 4], px + uint32_t(dx), y + uint32_t(dy), z + 0x2135, 0, c->actorToken});
        return 1;
    }
    case 0x43f640:
        if (a[0xcc / 4] == 1) {
            e[6] = 0x43f720;
            store(e, 0x50, 0);
            store(e, 0x58, -600);
            store(e, 0x60, 0);
            e[8] = 1;
            a[2] |= 4;
            a[0xcc / 4] = 8;
            if (!transition(s, c, "LS_JUMP", d, u))
                return 0;
            select(s, c, 0x33c, d, u);
        }
        return 1;
    case 0x43fe60: {
        if (!transition(s, c, "LS_BOUNCE", d, u))
            return 0;
        a[0xcc / 4] = 8;
        select(s, c, 0x36c, d, u);
        const double position = sub(load(e, 0x70), 1), acceleration = load(e, 0x40), velocity = load(e, 0x58);
        double result = velocity;
        if (acceleration != 0) {
            result = sub(mul(velocity, velocity), mul(mul(sub(position, load(e, 0x70)), acceleration), -2));
            if (result < 0)
                result = 0;
            result = std::sqrt(result);
            if (velocity <= 0)
                result = -result;
        }
        store(e, 0x58, result);
        store(e, 0x70, position);
        store(e, 0xb8, -1);
        const double vx = mul(load(e, 0x50), 1.0 / 3.0);
        store(e, 0x58, mul(load(e, 0x58), -1.0 / 3.0));
        store(e, 0x60, 0);
        store(e, 0x50, vx);
        return 1;
    }
    case 0x43f740: {
        const bool right = e[0x18c / 4] == 3;
        const int32_t distance = int32_t(call(s, c, d, u, 0x4a3050, 0)) % 51 + 75;
        const uint32_t destination =
            right ? truncLow(load(e, 0x68)) + uint32_t(distance) : truncLow(load(e, 0x68)) - uint32_t(distance);
        e[0x280 / 4] = destination;
        if (right ? load(e, 0x98) < double(int32_t(destination)) : double(int32_t(destination)) < load(e, 0x80))
            return 1;
        const uint32_t y = a[0x50 / 4] + 1 + a[0x124 / 4];
        auto tile = [&](uint32_t yy) {
            return uint32_t(call(s, c, d, u, 0x4207f0, c->tileManagerToken, {destination, yy}));
        };
        if (!(tile(y) == 1 || tile(y) == 2 || tile(y) == 3) || tile(y - 1) != 0)
            return 1;
        store(e, 0x50, right ? 150 : -150);
        store(e, 0x58, 0);
        store(e, 0x60, 0);
        mirror(s, e[0x18c / 4] == 2);
        if (!transition(s, c, "LS_MOVEBACK", d, u))
            return 0;
        select(s, c, 0x308, d, u);
        return 1;
    }
    case 0x43ffa0:
        a[2] |= 2;
        a[0x164 / 4] |= 0x2000;
        if (!transition(s, c, "LS_EXPLODING", d, u))
            return 0;
        a[2] |= 4;
        a[0xd0 / 4] = 0x1000000;
        select(s, c, 0x368, d, u);
        if (!audio(s, c, x, 0x3b8, d, u))
            return 0;
        e[0xc8 / 4] = 1;
        e[0x1a0 / 4] = 0;
        return 1;
    default:
        return 0;
    }
}

uint32_t claw_generic_enemy_state_entry(ClawGenericEnemy *s, ClawGenericEnemyContext *c,
                                        ClawGenericEnemyStatesContext *x, uint32_t f, uint32_t arg,
                                        ClawGenericEnemyDependency d, void *u) {
    return stateEntry(s, c, x, f, arg, d, u, useV13);
}
uint32_t claw_generic_enemy_state_entry_v13(ClawGenericEnemy *s, ClawGenericEnemyContext *c,
                                            ClawGenericEnemyStatesContext *x, uint32_t f, uint32_t arg,
                                            ClawGenericEnemyDependency d, void *u) {
    return stateEntry(s, c, x, f, arg, d, u, true);
}

void claw_generic_enemy_states_use_v13(void) {
    useV13 = true;
}
