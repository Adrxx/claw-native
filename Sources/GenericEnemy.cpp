#include "GenericEnemy.h"
#include "PlayerPhysics.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
#pragma STDC FP_CONTRACT OFF
namespace {
double load(const uint32_t *p, size_t o) {
    double v;
    std::memcpy(&v, p + o / 4, 8);
    return v;
}
void store(uint32_t *p, size_t o, double v) {
    std::memcpy(p + o / 4, &v, 8);
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
uint32_t truncLow(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    int e = int((bits >> 52) & 0x7ff) - 1023;
    if (e < 0 || e >= 63)
        return 0;
    uint64_t m = (bits & 0xfffffffffffffULL) | 0x10000000000000ULL;
    m = e >= 52 ? m << (e - 52) : m >> (52 - e);
    return bits >> 63 ? 0u - uint32_t(m) : uint32_t(m);
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
const ClawGenericEnemyState *find(ClawGenericEnemyContext *c, int32_t id) {
    for (size_t i = 0; i < c->stateCount; ++i)
        if (c->states[i].state == id)
            return &c->states[i];
    return nullptr;
}
bool bit(ClawGenericEnemy *s, ClawGenericEnemyContext *c, uint32_t index) {
    const uint32_t size = s->enemy[0x2fc / 4];
    if (size <= index)
        return false;
    if (size <= 32)
        return (s->enemy[0x300 / 4] >> (index & 31)) & 1;
    return c->bitWords && index / 32 < c->bitWordCount && ((c->bitWords[index / 32] >> (index & 31)) & 1);
}
bool valid(ClawGenericEnemy *s, ClawGenericEnemyContext *c) {
    return s && c && (!c->stateCount || c->states) &&
           (s->enemy[0x2fc / 4] <= 32 || (c->bitWords && c->bitWordCount >= 1));
}
void virtualCall(ClawGenericEnemy *s, ClawGenericEnemyContext *c, uint32_t slot, uint32_t arg, bool hasArg,
                 ClawGenericEnemyDependency d, void *u) {
    const uint32_t f = c->virtualFunctions[slot / 4];
    // Supported common bodies execute natively; Rat and other overrides remain
    // explicit dispatch dependencies with original function identities.
    switch (f) {
    case 0x404fc0:
    case 0x4063b0:
    case 0x43dfa0:
    case 0x43e420:
    case 0x43d490:
    case 0x43fd10:
    case 0x43fdc0:
    case 0x43edd0:
    case 0x43fcb0:
    case 0x43fd60:
        claw_generic_enemy_entry(s, c, f, arg, d, u);
        break;
    default:
        if (hasArg)
            call(s, c, d, u, f, c->enemyToken, {arg});
        else
            call(s, c, d, u, f, c->enemyToken);
        break;
    }
}
double correctedVelocity(const uint32_t *e, size_t axis, double newPosition) {
    const double acceleration = load(e, 0x38 + axis * 8), velocity = load(e, 0x50 + axis * 8);
    if (acceleration == 0)
        return velocity;
    double v = sub(mul(velocity, velocity), mul(mul(sub(newPosition, load(e, 0x68 + axis * 8)), acceleration), -2));
    if (v < 0)
        v = 0;
    v = std::sqrt(v);
    return velocity <= 0 ? -v : v;
}
void correctPosition(uint32_t *e, size_t axis, double newPosition) {
    const double velocity = correctedVelocity(e, axis, newPosition);
    const double delta = sub(load(e, 0x68 + axis * 8), newPosition);
    store(e, 0x50 + axis * 8, velocity);
    store(e, 0x68 + axis * 8, newPosition);
    store(e, 0xb0 + axis * 8, sub(load(e, 0xb0 + axis * 8), delta));
}
} // namespace
void claw_generic_enemy_context_defaults(ClawGenericEnemyContext *c) {
    if (!c)
        return;
    const uint32_t values[24] = {0xffc00000, 0xc1dfffff, 0xff800000, 0x41dfffff, 0x9999999a, 0x3fb99999,
                                 0x4db6a0,   0x4dbb50,   0x4dbc80,   0x4dbd00,   0x4dc230,   0,
                                 24,         0,          0xd2f1a9fc, 0x3f50624d, 0,          0xbfe00000,
                                 0,          0,          0,          0xc0000000, 0x4dda50,   0x4ddb40};
    std::copy(values, values + 24, c->defaults);
    c->bitHandlerToken = 0x544b68;
    // CString's shared empty buffer identity is host supplied separately.
}
uint32_t claw_generic_enemy_motion(ClawGenericEnemy *s, ClawGenericEnemyContext *c, ClawGenericEnemyDependency d,
                                   void *u) {
    if (!valid(s, c))
        return 0;
    auto *e = s->enemy;
    auto *a = s->actor;
    e[0x118 / 4] = truncLow(load(e, 0x68));
    e[0x11c / 4] = truncLow(load(e, 0x70));
    ClawPlayerPhysics p;
    std::memcpy(&p, e + 0x28 / 4, sizeof p);
    claw_physics_update(&p, sub(mul(double(c->tick), load(c->defaults, 0x38)), p.elapsed));
    std::memcpy(e + 0x28 / 4, &p, sizeof p);
    if ((a[2] & 0x10) && a[0x80 / 4]) {
        a[0x4c / 4] += c->platformActor[0x158 / 4];
        store(e, 0x68, double(int32_t(a[0x4c / 4])));
        a[0x50 / 4] += c->platformActor[0x15c / 4];
        store(e, 0x70, double(int32_t(a[0x50 / 4])));
    }
    const bool grounded = a[0xcc / 4] == 1;
    if (!grounded)
        a[2] &= ~0x10u;
    e[0x120 / 4] = uint32_t(
        call(s, c, d, u, 0x4cbb60, c->tileManagerToken,
             {c->actorToken, truncLow(load(e, 0x68)), grounded ? a[0x50 / 4] : truncLow(load(e, 0x70)), e[0x124 / 4]}));
    if (grounded)
        store(e, 0x58, 0);
    if (truncLow(load(e, 0x68)) != a[0x4c / 4])
        correctPosition(e, 0, double(int32_t(a[0x4c / 4])));
    if (truncLow(load(e, 0x70)) != a[0x50 / 4])
        correctPosition(e, 1, double(int32_t(a[0x50 / 4])));
    if (a[0xcc / 4] != 7) {
        if (e[0x120 / 4] & 0x800000)
            store(e, 0x58, -load(e, 0x58));
        else if (e[0x120 / 4] & 0x40000) {
            store(e, 0x98, double(int32_t(e[0x118 / 4])));
            store(e, 0x50, mul(load(e, 0x50), load(c->defaults, 0x40)));
        } else if (e[0x120 / 4] & 0x80000) {
            store(e, 0x80, double(int32_t(e[0x118 / 4])));
            store(e, 0x50, mul(load(e, 0x50), load(c->defaults, 0x40)));
        }
    }
    return 1;
}
uint32_t claw_generic_enemy_pre(ClawGenericEnemy *s, ClawGenericEnemyContext *c, ClawGenericEnemyDependency, void *) {
    if (!valid(s, c))
        return 0;
    auto *e = s->enemy;
    const double x = load(e, 0x68), y = load(e, 0x70);
    if (x <= double(int32_t(c->playerActor[0x4c / 4])))
        e[0x18c / 4] = 2;
    if (double(int32_t(c->playerActor[0x4c / 4])) < x)
        e[0x18c / 4] = 3;
    if (c->levelWord == 0x26b7 || bit(s, c, 1))
        return 1;
    for (size_t i = 0; i < 5; ++i) {
        const double range = double(int32_t(e[(0x28c + i * 8) / 4])), clamp = double(int32_t(e[0x2a4 / 4]));
        const double right = std::min(add(x, range), add(load(e, 0x98), clamp));
        const double left = std::max(sub(x, range), sub(load(e, 0x80), clamp));
        const uint32_t height = e[(0x290 + i * 8) / 4];
        auto *r = e + (0x1c0 + i * 16) / 4;
        r[0] = truncLow(left);
        r[1] = truncLow(y) - height;
        r[2] = truncLow(right);
        r[3] = truncLow(y) + height;
    }
    for (int i = 4; i >= 0; --i) {
        const auto *r = e + (0x1c0 + i * 16) / 4;
        const int32_t px = int32_t(c->playerActor[0x4c / 4]), py = int32_t(c->playerActor[0x50 / 4]);
        if (px >= int32_t(r[0]) && px < int32_t(r[2]) && py >= int32_t(r[1]) && py < int32_t(r[3])) {
            e[0x184 / 4] = uint32_t(i);
            e[0x188 / 4] = 0;
            return 1;
        }
    }
    if (s->actor[0x38 / 4] == 0xffffffff) {
        e[0x184 / 4] = 6;
        e[0x188 / 4] = 0;
        return 1;
    }
    if (!e[0x188 / 4]) {
        e[0x3cc / 4] = 500;
        e[0x3c8 / 4] = c->tick;
        e[0x188 / 4] = 1;
    } else if (e[0x3cc / 4] <= c->tick - e[0x3c8 / 4])
        e[0x184 / 4] = 5;
    return 1;
}
uint32_t claw_generic_enemy_post(ClawGenericEnemy *s, ClawGenericEnemyContext *c, ClawGenericEnemyDependency d,
                                 void *u) {
    if (!valid(s, c))
        return 0;
    claw_generic_enemy_motion(s, c, d, u);
    auto *e = s->enemy;
    auto *a = s->actor;
    if (a[0xcc / 4] != 7) {
        if (e[0x120 / 4] & 0x100000) {
            const auto *state = find(c, int32_t(s->primary[0x1c / 4]));
            if (!state || !state->name)
                return 0;
            if (std::strcmp(state->name, "LS_DEAD") == 0 || bit(s, c, 4))
                return 1;
            if (c->hitMode == 0)
                virtualCall(s, c, 0x5c, 2, true, d, u);
            else if (c->hitMode == 1)
                virtualCall(s, c, 0x5c, 3, true, d, u);
            return 1;
        }
        if (a[0xcc / 4] == 1 && bit(s, c, 3) && !bit(s, c, 2)) {
            const double velocity = e[0xc8 / 4] ? 0 : load(e, 0xb0);
            // The left branch can fall through into the right branch if probes say
            // the tile edge is supported. Preserve repeated tile queries and order.
            for (int side = 0; side < 2; ++side) {
                if ((side == 0 && velocity >= 0) || (side == 1 && velocity <= 0))
                    continue;
                const uint32_t x = a[0x4c / 4] + a[(side ? 0x120 : 0x118) / 4];
                const uint32_t y = a[0x50 / 4] + 1 + a[0x124 / 4];
                auto tile = [&](uint32_t yy) {
                    return uint32_t(call(s, c, d, u, 0x4207f0, c->tileManagerToken, {x, yy}));
                };
                const bool floor = (tile(y) == 1 || tile(y) == 2 || tile(y) == 3) && tile(y - 1) == 0;
                if (floor)
                    continue;
                const double px = double(int32_t(e[0x118 / 4])), py = double(int32_t(e[0x11c / 4]));
                store(e, side ? 0x98 : 0x80, px);
                correctPosition(e, 0, px);
                correctPosition(e, 1, py);
                break;
            }
        }
    }
    a[0x4c / 4] = truncLow(load(e, 0x68));
    a[0x50 / 4] = truncLow(load(e, 0x70));
    if (bit(s, c, 0)) {
        const double playerFloor = double(int32_t(c->playerActor[0x124 / 4] + c->playerActor[0x50 / 4]));
        const uint32_t z =
            e[0x2d0 / 4] + (playerFloor <= add(double(int32_t(a[0x124 / 4])), load(e, 0x70)) ? 4000 : 3899);
        if (a[0x64 / 4] != z) {
            a[0x64 / 4] = z;
            a[2] |= 0x20000;
        }
    }
    return 1;
}
uint32_t claw_generic_enemy_dispatch(ClawGenericEnemy *s, ClawGenericEnemyContext *c, int32_t id,
                                     ClawGenericEnemyDependency d, void *u) {
    if (!valid(s, c))
        return 0;
    const auto *entry = find(c, id);
    if (!entry)
        return 0;
    if (entry->function) {
        if (!claw_generic_enemy_entry(s, c, entry->function, 0, d, u))
            call(s, c, d, u, entry->function, c->enemyToken);
    } else
        call(s, c, d, u, 0x4a36f0, 0, {c->enemyToken});
    return 1;
}
uint32_t claw_generic_enemy_tick(ClawGenericEnemy *s, ClawGenericEnemyContext *c, ClawGenericEnemyDependency d,
                                 void *u) {
    if (!valid(s, c))
        return 0;
    const int32_t id = int32_t(s->primary[0x1c / 4]);
    const auto *entry = find(c, id);
    if (!entry)
        return 0;
    uint32_t name = entry->nameToken;
    virtualCall(s, c, 4, name, true, d, u);
    virtualCall(s, c, 8, uint32_t(id), true, d, u);
    entry = find(c, id);
    if (!entry)
        return 0;
    name = entry->nameToken;
    virtualCall(s, c, 12, name, true, d, u);
    return 1;
}
uint32_t claw_generic_enemy_entry(ClawGenericEnemy *s, ClawGenericEnemyContext *c, uint32_t f, uint32_t arg,
                                  ClawGenericEnemyDependency d, void *u) {
    if (!valid(s, c))
        return 0;
    auto *e = s->enemy;
    switch (f) {
    case 0x43e420:
        return claw_generic_enemy_pre(s, c, d, u);
    case 0x43dfa0:
        return claw_generic_enemy_post(s, c, d, u);
    case 0x4dca10:
        return claw_generic_enemy_motion(s, c, d, u);
    case 0x43d490:
        return claw_generic_enemy_dispatch(s, c, int32_t(arg), d, u);
    case 0x404fc0:
        e[0x3c4 / 4] = c->forcedRandom ? 0x1fffffff : uint32_t(int32_t(call(s, c, d, u, 0x4a3050, 0)) % 1001);
        return claw_generic_enemy_pre(s, c, d, u);
    case 0x4063b0:
        if (e[5]) {
            if (e[6] && s->primary[7] == e[7]) {
                const uint32_t f2 = e[6];
                if (!claw_generic_enemy_entry(s, c, f2, 0, d, u))
                    call(s, c, d, u, f2, c->enemyToken);
                e[6] = 0;
            }
            const uint32_t f2 = e[5];
            if (!claw_generic_enemy_entry(s, c, f2, 0, d, u))
                call(s, c, d, u, f2, c->enemyToken);
            e[5] = 0;
            e[7] = 1001;
        }
        virtualCall(s, c, 0x24, 0, false, d, u);
        return 1;
    case 0x43fcb0:
    case 0x43fd60: {
        store(e, 0x50, double(int32_t(f == 0x43fcb0 ? 0u - arg : arg)));
        e[0x24 / 4] = s->primary[7];
        const char *name = f == 0x43fcb0 ? "LS_MOVINGLEFT" : "LS_MOVINGRIGHT";
        uint32_t id = 0;
        if (d)
            id = uint32_t(call(s, c, d, u, 0x4dba00, 0x537668, {}, name));
        else {
            const ClawGenericEnemyState *resolved = nullptr;
            for (size_t i = 0; i < c->stateCount; ++i)
                if (c->states[i].name && std::strcmp(c->states[i].name, name) == 0) {
                    resolved = &c->states[i];
                    break;
                }
            if (!resolved)
                return 0;
            id = uint32_t(resolved->state);
        }
        s->primary[7] = id;
        e[0x134 / 4] = s->actor[0x190 / 4];
        call(s, c, d, u, 0x4c8220, c->actorToken + 0x188, {e[0x354 / 4]});
        return 1;
    }
    case 0x43fd10:
    case 0x43fdc0:
    case 0x43edd0:
        call(s, c, d, u, 0x4c82a0, c->actorToken + 0x188, {c->animationDelta});
        if (f == 0x43edd0) {
            if (s->actor[0xcc / 4] == 1)
                virtualCall(s, c, 0x48, 0, false, d, u);
        } else if (load(e, 0x68) == load(e, f == 0x43fd10 ? 0x80 : 0x98))
            virtualCall(s, c, f == 0x43fd10 ? 0x70 : 0x6c, truncLow(f == 0x43fd10 ? -load(e, 0x50) : load(e, 0x50)),
                        true, d, u);
        return 1;
    case 0x4bb030:
        return 1;
    case 0x43e9b0:
        call(s, c, d, u, 0x48cf50, 0, {c->actorToken});
        return 1;
    default:
        return 0;
    }
}
uint32_t claw_generic_enemy_construct(ClawGenericEnemy *s, ClawGenericEnemyContext *c, ClawGenericEnemyDependency d,
                                      void *u) {
    if (!s || !c)
        return 0;
    auto *e = s->enemy;
    auto *a = s->actor;
    auto *l = s->primary;
    e[0] = 0x50b064;
    e[2] = e[3] = c->actorToken;
    e[4] = a[0x6c / 4];
    e[1] = 0;
    call(s, c, d, u, 0x4c7fa0, c->actorToken, {}, "LogicHit");
    call(s, c, d, u, 0x4c8060, c->actorToken, {}, "LogicAttack");
    e[5] = e[6] = 0;
    e[7] = 1001;
    e[8] = 2;
    ClawPlayerPhysics p;
    std::memcpy(&p, e + 0x28 / 4, sizeof p);
    claw_physics_construct(&p);
    for (int axis = 0; axis < 3; ++axis) {
        p.minimum[axis] = load(c->defaults, 0);
        p.maximum[axis] = p.maximumDelta[axis] = p.maximumVelocity[axis] = load(c->defaults, 8);
    }
    std::memcpy(e + 0x28 / 4, &p, sizeof p);
    e[0] = 0x50b2a4;
    for (const auto offset : {0x80, 0x88, 0x98, 0xa0}) {
        const size_t source = offset == 0x80 ? 0x2c : offset == 0x88 ? 0x34 : offset == 0x98 ? 0x30 : 0x38;
        store(e, offset, l[source / 4] ? double(int32_t(l[source / 4])) : load(c->defaults, offset < 0x90 ? 0 : 8));
    }
    store(e, 0x68, double(int32_t(a[0x4c / 4])));
    store(e, 0x70, double(int32_t(a[0x50 / 4])));
    store(e, 0x78, 0);
    store(e, 0x50, double(int32_t(a[0x148 / 4])));
    store(e, 0x58, double(int32_t(a[0x14c / 4])));
    store(e, 0x60, 0);
    store(e, 0x38, 0);
    store(e, 0x40, 0);
    store(e, 0x48, 0);
    store(e, 0x28, mul(double(c->tick), 0.001));
    store(e, 0x30, 0);
    for (const auto offset : {0xe8, 0xf0, 0xf8})
        store(e, offset, double(int32_t(c->defaults[0x30 / 4])));
    e[0x120 / 4] = e[0x124 / 4] = 0;
    a[0xcc / 4] = 7;
    claw_generic_enemy_motion(s, c, d, u);
    // Complete408370 embedded actor/primary wrapper; input buffers may change
    // across dependencies, so these reads occur after the motion boundary.
    e[0x128 / 4] = e[0x12c / 4] = e[0x178 / 4] = e[0x17c / 4] = c->actorToken;
    e[0x130 / 4] = e[0x180 / 4] = a[0x6c / 4];
    e[0x14c / 4] = e[0x150 / 4] = 0;
    const size_t inventory[] = {0xf0, 0xf8, 0xf4, 0xfc, 0x100, 0x108, 0x104, 0x10c, 0x100};
    // The final wrapper item is actor+0x100, whereas the preceding eight
    // entries come from primary logic. Exact original order is preserved.
    for (size_t i = 0; i < 9; ++i) {
        const uint32_t v = i == 8 ? a[inventory[i] / 4] : l[inventory[i] / 4];
        e[(0x154 + i * 4) / 4] = v;
        ++e[0x14c / 4];
        if (v)
            ++e[0x150 / 4];
    }
    e[0x190 / 4] = e[0x194 / 4] = c->actorToken;
    e[0x198 / 4] = a[0x6c / 4];
    e[0x1a4 / 4] = e[0x1a8 / 4] = c->emptyStringToken;
    e[0x2f4 / 4] = 0x513e34;
    e[0x2f8 / 4] = c->bitHandlerToken;
    e[0x2fc / 4] = 32;
    e[0x300 / 4] = 0;
    for (size_t o = 0x3c8; o <= 0x3fc; o += 4)
        e[o / 4] = 0;
    e[0] = 0x50b16c;
    a[2] |= 0x80000;
    e[1] = l[0x168 / 4];
    e[0x184 / 4] = 6;
    e[0x188 / 4] = 0;
    e[0x288 / 4] = 0;
    e[0x28c / 4] = 400;
    e[0x290 / 4] = 50;
    e[0x29c / 4] = 300;
    e[0x2a0 / 4] = 50;
    e[0x2a4 / 4] = 200;
    e[0x2a8 / 4] = 50;
    e[0x2ac / 4] = 100;
    e[0x2b0 / 4] = 50;
    e[0x2e4 / 4] = a[0x108 / 4];
    e[0x2e8 / 4] = a[0x114 / 4];
    e[0x2ec / 4] = e[0x2f0 / 4] = l[0x68 / 4];
    e[0x19c / 4] = 0xffffffff;
    e[0x1a0 / 4] = 0;
    for (size_t o = 0x210; o <= 0x26c; o += 4)
        e[o / 4] = 0;
    // This constructor profile uses the original initial empty534938 bit string
    // and default533470 size32; generalized parsing is outside this routine.
    if (int32_t(l[0x64 / 4]) > 0)
        e[0x300 / 4] |= 4;
    e[0x300 / 4] |= 0x200;
    for (size_t o = 0x2b4; o <= 0x2c8; o += 4)
        e[o / 4] = 0;
    e[0x1ac / 4] = e[0x2cc / 4] = e[0x2d0 / 4] = 0;
    for (size_t o = 0x308; o <= 0x320; o += 4)
        e[o / 4] = 0;
    for (size_t o = 0x32c; o <= 0x388; o += 4)
        e[o / 4] = 0;
    const char *resources[] = {"GAME_SPLASH", "GAME_HIT1", "GAME_HIT2", "GAME_HIT3", "GAME_HIT4", "GAME_PURELEASE1"};
    for (size_t i = 0; i < 6; ++i) {
        const uint32_t token = uint32_t(call(s, c, d, u, 0x4f6286, c->soundRegistryToken, {}, resources[i]));
        e[(i < 5 ? 0x38c + i * 4 : 0x148) / 4] = token;
    }
    for (size_t o = 0x3a0; o <= 0x3c0; o += 4)
        e[o / 4] = 0;
    store(e, 0x40, 2000);
    a[0x164 / 4] &= ~1u;
    // Final original branch compares the same render flag twice, so in the
    // represented same-actor wrapper profile its mirroring body is unreachable.
    return 1;
}
