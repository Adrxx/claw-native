#include "EndLevelGemRuntime.h"
#include "StackedActorLifecycleRuntime.h"
#include <algorithm>
#include <cstring>
#include <cmath>
#include <initializer_list>
#pragma STDC FP_CONTRACT OFF
namespace {
struct Failed {};
struct Run {
    ClawEndLevelGemContext &c;
    ClawEndLevelGemDependency dependency;
    void *user;
    uint32_t visits = 0;
    static int32_t si(uint32_t v) {
        int32_t x;
        std::memcpy(&x, &v, 4);
        return x;
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Failed{};
        }
        return p;
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    double number(uint32_t t) {
        double x;
        std::memcpy(&x, span(t, 2), 8);
        return x;
    }
    void number(uint32_t t, double x) {
        std::memcpy(span(t, 2), &x, 8);
    }
    void step() {
        if (++visits > (c.maximumSteps ? c.maximumSteps : 65536)) {
            c.fault = 2;
            throw Failed{};
        }
    }
    uint64_t external(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}, const char *name = nullptr) {
        ClawEndLevelGemCall e{};
        e.function = f;
        e.receiver = t;
        e.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), e.arguments);
        e.name = name;
        return external(e);
    }
    uint64_t external(const ClawEndLevelGemCall &e) {
        uint64_t value = 0;
        if (dependency)
            value = dependency(&c, &e, user);
        else if (c.scene.call && e.argumentCount <= 4) {
            ClawSceneActorCall q{};
            q.function = e.function;
            q.receiver = e.receiver;
            q.argumentCount = e.argumentCount;
            std::copy_n(e.arguments, e.argumentCount, q.arguments);
            value = c.scene.call(c.scene.context, q);
        } else {
            c.fault = 1;
            throw Failed{};
        }
        if (c.fault)
            throw Failed{};
        return value;
    }
    static uint32_t *lookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->span(t, n);
    }
    static uint32_t allocate(void *p, uint32_t n) {
        auto &r = *static_cast<Run *>(p);
        if (!r.c.scene.allocate) {
            r.c.fault = 1;
            throw Failed{};
        }
        return r.c.scene.allocate(r.c.scene.context, n);
    }
    static void release(void *p, uint32_t t) {
        auto &r = *static_cast<Run *>(p);
        if (!r.c.scene.free) {
            r.c.fault = 1;
            throw Failed{};
        }
        r.c.scene.free(r.c.scene.context, t);
    }
    static uint32_t hostCall(void *p, ClawSceneActorCall e) {
        auto &r = *static_cast<Run *>(p);
        return uint32_t(r.invoke(e.function, e.receiver, e.arguments, e.argumentCount));
    }
    static uint32_t clock(void *p) {
        auto &r = *static_cast<Run *>(p);
        if (!r.c.scene.readClock) {
            r.c.fault = 1;
            throw Failed{};
        }
        return r.c.scene.readClock(r.c.scene.context);
    }
    ClawSceneActorHost host() {
        return {this, lookup, allocate, release, hostCall, clock};
    }
    static uint32_t lootCall(ClawWorldLootGlobals *, ClawWorldLootContext *q, const ClawWorldLootCall *e, void *p) {
        auto &r = *static_cast<Run *>(p);
        uint32_t value = uint32_t(r.invoke(e->function, e->receiver, e->arguments, e->argumentCount, e->name));
        if (r.c.fault)
            q->fault = r.c.fault;
        return value;
    }
    uint32_t rebind(uint32_t actor, uint32_t item) {
        if (!c.composeLoot)
            return uint32_t(external(0x473660, 0, {actor, item}));
        if (!c.loot) {
            c.fault = 1;
            throw Failed{};
        }
        ClawWorldLootContext q{};
        q.scene = host();
        q.composeCreation = c.composeCreation;
        uint32_t value = claw_world_loot_rebind_actor(actor, si(item), c.loot, &q, lootCall, this);
        if (q.fault) {
            c.fault = q.fault;
            throw Failed{};
        }
        return value;
    }
    uint32_t lootName(uint32_t item) {
        if (!c.composeLoot)
            return uint32_t(external(0x473630, 0, {item}));
        if (!c.loot) {
            c.fault = 1;
            throw Failed{};
        }
        return claw_world_loot_name_token(si(item), c.loot);
    }
    uint32_t create(uint32_t container, uint32_t id, uint32_t x, uint32_t y, uint32_t z, uint32_t name,
                    uint32_t flags) {
        if (!c.composeCreation)
            return uint32_t(external(0x4c8da0, container, {id, x, y, z, name, flags}));
        uint32_t fault = 0,
                 value = claw_scene_actor_create_named(container, {id, x, y, z, 0, flags}, name, host(), &fault);
        if (fault) {
            c.fault = fault;
            throw Failed{};
        }
        return value;
    }
    uint64_t animation(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        if (!c.composeAnimation) {
            ClawEndLevelGemCall e{};
            e.function = f;
            e.receiver = t;
            e.argumentCount = n;
            std::copy_n(a, n, e.arguments);
            return external(e);
        }
        if (!c.animation) {
            c.fault = 1;
            throw Failed{};
        }
        uint32_t fault = 0, value = 0;
        if (!claw_actor_animation_entry(f, t, n ? a[0] : 0, n > 1 ? a[1] : 0, c.animation, host(), &fault, &value) ||
            fault) {
            c.fault = fault ? fault : 1;
            throw Failed{};
        }
        return value;
    }
    struct Common {
        Run *r;
        uint32_t privateToken, phase;
        bool ticking;
        ClawGenericEnemyState stateView;
        ClawGenericEnemy state;
        ClawGenericEnemyContext context;
    };
    void transfer(Common &q, bool push) {
        auto *p = span(q.privateToken, 84);
        auto *a = span(q.context.actorToken, 109);
        auto *l = span(q.context.primaryToken, 93);
        if (push) {
            std::copy_n(q.state.enemy, 84, p);
            std::copy_n(q.state.actor, 109, a);
            std::copy_n(q.state.primary, 93, l);
        } else {
            std::copy_n(p, 84, q.state.enemy);
            std::copy_n(a, 109, q.state.actor);
            std::copy_n(l, 93, q.state.primary);
            q.context.tick = get(0x537210);
        }
    }
    static uint64_t commonCall(ClawGenericEnemy *s, ClawGenericEnemyContext *g, const ClawGenericEnemyCall *e,
                               void *p) {
        auto &q = *static_cast<Common *>(p);
        q.state = *s;
        q.context = *g;
        q.r->transfer(q, true);
        uint64_t value = q.r->invoke(e->function, e->receiver, e->arguments, e->argumentCount, e->name);
        q.r->transfer(q, false);
        if (q.ticking && ++q.phase == 2)
            q.stateView.nameToken = q.r->nameToken(uint32_t(q.stateView.state));
        *s = q.state;
        *g = q.context;
        return value;
    }
    uint32_t common(uint32_t f, uint32_t p, uint32_t argument = 0) {
        if (!c.composeCommon) {
            if (f == 0x4dc870)
                return uint32_t(external(f, 0, {p}));
            if (f == 0x4063b0)
                return uint32_t(external(f, p, {argument}));
            return uint32_t(external(f, p));
        }
        if (!c.common) {
            c.fault = 1;
            throw Failed{};
        }
        Common q{};
        q.r = this;
        q.privateToken = p;
        q.context = *c.common;
        q.context.actorToken = get(p + 12);
        q.context.primaryToken = get(p + 16);
        q.context.enemyToken = p;
        std::copy_n(span(get(p), 10), 10, q.context.virtualFunctions);
        transfer(q, false);
        if (f == 0x4dc870) {
            q.ticking = true;
            bool found = false;
            for (size_t i = 0; i < q.context.stateCount; ++i)
                if (q.context.states[i].state == si(q.state.primary[7])) {
                    q.stateView = q.context.states[i];
                    found = true;
                    break;
                }
            if (!found) {
                c.fault = 2;
                throw Failed{};
            }
            q.stateView.nameToken = nameToken(uint32_t(q.stateView.state));
            q.context.states = &q.stateView;
            q.context.stateCount = 1;
        }
        uint32_t ok = f == 0x4dc870 ? claw_generic_enemy_tick(&q.state, &q.context, commonCall, &q)
                                    : claw_generic_enemy_entry(&q.state, &q.context, f, argument, commonCall, &q);
        if (!ok) {
            c.fault = 2;
            throw Failed{};
        }
        transfer(q, true);
        return 0;
    }
    uint32_t nameToken(uint32_t state) {
        constexpr uint32_t table = 0x537698;
        put(table + 32, 0);
        int32_t low = si(get(table + 8));
        uint32_t cell = 0;
        if (si(state) < low || si(state) > si(get(table + 12))) {
            uint32_t found = uint32_t(external(0x4db6e0, table, {state, 0}));
            if (!found) {
                uint32_t message = get(0x544b4c);
                put(0x544b14, uint32_t(external(0x4db5f0, 0)));
                external(0x4db4d0, get(table + 4), {table, message, 12});
                cell = get(table + 20);
            } else {
                low = si(get(table + 8));
                cell = get(table + 16) + (state - uint32_t(low)) * get(table + 24);
            }
        } else
            cell = get(table + 16) + (state - uint32_t(low)) * get(table + 24);
        uint32_t n = get(table + 32), at = get(table + 28);
        for (uint32_t i = 0; i < n; ++i, at += 4) {
            step();
            if (at)
                external(0x4f6439, at);
        }
        return uint32_t(external(0x4f6974, cell, {0}));
    }
    uint32_t classCell(uint32_t state) {
        put(0x537628, 0);
        int32_t low = si(get(0x537610));
        if (si(state) < low || si(state) > si(get(0x537614))) {
            uint32_t found = uint32_t(external(0x4db6e0, 0x537608, {state, 0}));
            if (!found) {
                uint32_t name = get(0x544b4c);
                put(0x544b14, uint32_t(external(0x4db5f0, 0)));
                external(0x4db4d0, get(0x53760c), {0x537608, name, 12});
                return get(0x53761c);
            }
            low = si(get(0x537610));
        }
        return get(0x537618) + (state - uint32_t(low)) * get(0x537620);
    }
    uint32_t dispatch(uint32_t p, uint32_t state) {
        uint32_t slot = classCell(state);
        if (get(slot)) {
            slot = classCell(state);
            return uint32_t(invoke(get(slot), p, nullptr, 0));
        }
        external(0x4a36f0, 0, {p});
        return 0;
    }
    void base(uint32_t p, uint32_t actor) {
        put(p, 0x50b064);
        put(p + 8, actor);
        put(p + 12, actor);
        put(p + 16, get(actor + 0x6c));
        put(p + 4, 0);
        external(0x4c7fa0, actor, {0x522d54}, "LogicHit");
        external(0x4c8060, get(p + 12), {0x522d48}, "LogicAttack");
        put(p + 0x14, 0);
        put(p + 0x18, 0);
        put(p + 0x1c, 1001);
        put(p + 0x20, 2);
    }
    uint32_t construct(uint32_t p, uint32_t actor) {
        base(p, actor);
        ClawPlayerPhysics physics;
        std::memcpy(&physics, span(p + 0x28, 60), sizeof physics);
        claw_physics_construct(&physics);
        std::memcpy(span(p + 0x28, 60), &physics, sizeof physics);
        put(p, 0x50b2a4);
        uint32_t primary = get(p + 16);
        for (uint32_t i = 0; i < 4; ++i) {
            uint32_t value = get(primary + uint32_t((i % 2 ? 0x34 : 0x2c) + (i / 2) * 4));
            if (value)
                number(p + (i < 2 ? 0x80 : 0x98) + (i % 2) * 8, double(si(value)));
        }
        uint32_t a = get(p + 12);
        number(p + 0x28, double(get(0x537210)) * 0.001);
        number(p + 0x30, 0);
        for (uint32_t i = 0; i < 3; ++i) {
            number(p + 0x68 + i * 8, i < 2 ? double(si(get(a + 0x4c + i * 4))) : 0);
            number(p + 0x50 + i * 8, i < 2 ? double(si(get(a + 0x148 + i * 4))) : 0);
            number(p + 0x38 + i * 8, 0);
            number(p + 0xe8 + i * 8, 24);
        }
        put(p + 0x120, 0);
        put(p + 0x124, 0);
        put(a + 0xcc, 7);
        common(0x4dca10, p);
        put(p + 0x128, actor);
        put(p + 0x12c, actor);
        put(p + 0x130, get(actor + 0x6c));
        put(p, 0x50db2c);
        external(0x4c7970, get(p + 0x12c), {lootName(31)});
        a = get(p + 0x12c);
        put(a + 8, get(a + 8) | 3);
        number(p + 0x40, 100);
        put(p + 0x24, get(get(p + 16) + 28));
        put(get(p + 16) + 28, uint32_t(external(0x4dba00, 0x537668, {0x523148}, "LS_IDLE")));
        return p;
    }
    uint32_t wrapper(uint32_t actor) {
        uint32_t primary = get(actor + 0x6c), state = get(primary + 28);
        if (state == 0) {
            put(primary + 28, 1000);
            uint32_t p = allocate(this, 0x150);
            if (p)
                construct(p, actor);
            uint32_t fn = get(get(p) + 16);
            invoke(fn, p, nullptr, 0);
            put(primary + 24, p);
        } else if (state == 29 || state == 30) {
            uint32_t p = get(primary + 24);
            invoke(get(get(p) + (state == 29 ? 32 : 28)), p, nullptr, 0);
        } else if (state != 1000)
            common(0x4dc870, get(primary + 24));
        return 1;
    }
    static uint32_t low(double value) {
        uint64_t b;
        std::memcpy(&b, &value, 8);
        int e = int((b >> 52) & 2047) - 1023;
        if (e < 0 || e >= 63)
            return 0;
        uint64_t v = (b & 0xfffffffffffffULL) | 0x10000000000000ULL;
        v = e >= 52 ? v << (e - 52) : v >> (52 - e);
        return b >> 63 ? 0u - uint32_t(v) : uint32_t(v);
    }
    uint32_t idle(uint32_t p) {
        put(0x52be14, low(number(p + 0x68)));
        put(0x52be18, low(number(p + 0x70)));
        if (number(p + 0x58) > 0 && double(si(get(p + 0x14c))) < number(p + 0x70)) {
            put(p + 0xc8, 1);
            uint32_t actor = get(p + 0x12c);
            put(actor + 8, get(actor + 8) & ~1u);
            restore();
            rebind(get(p + 8), 31);
            put(0x52be14, 0xffffffff);
            put(0x52be18, 0xffffffff);
        }
        return 0;
    }
    static double add(double a, double b) {
        volatile double v = a + b;
        return v;
    }
    static double sub(double a, double b) {
        volatile double v = a - b;
        return v;
    }
    static double mul(double a, double b) {
        volatile double v = a * b;
        return v;
    }
    static double div(double a, double b) {
        volatile double v = a / b;
        return v;
    }
    void target(uint32_t p, uint32_t x, uint32_t y) {
        if (!x && !y) {
            restore();
            rebind(get(p + 8), 31);
        }
        put(p + 0x148, x);
        put(p + 0x14c, y);
        //43d0f0 is a distinct inline specialization of420dd0. It negates Z
        //rather than subtracting from0. The x87 sum order is X,Y,Z.
        const double dx = sub(double(si(x)), number(p + 0x68)), dy = sub(double(si(y)), number(p + 0x70)),
                     dz = -number(p + 0x78);
        const double ax = number(p + 0x38), ay = number(p + 0x40), az = number(p + 0x48);
        const double dot = sub(sub(-mul(ax, dx), mul(ay, dy)), mul(az, dz));
        double square = add(add(mul(ax, ax), mul(ay, ay)), mul(az, az));
        const double distance = add(add(mul(dx, dx), mul(dy, dy)), mul(dz, dz));
        const double speed = std::sqrt(mul(sub(std::sqrt(mul(mul(distance, square), 4)), mul(dot, -2)), .5));
        if (speed < .1) {
            number(p + 0x50, 0);
            number(p + 0x58, 0);
            number(p + 0x60, 0);
            return;
        }
        square = mul(square, .25);
        if (-.1 <= square && square <= .1) {
            const double total = add(add(std::abs(dx), std::abs(dy)), std::abs(dz));
            number(p + 0x50, mul(div(dx, total), speed));
            number(p + 0x58, mul(div(dy, total), speed));
            number(p + 0x60, mul(div(dz, total), speed));
            return;
        }
        const double timeSquare = div(sub(mul(speed, speed), dot), add(square, square)), time = std::sqrt(timeSquare);
        const double vy = mul(mul(timeSquare, ay), .5), vz = mul(mul(timeSquare, az), .5);
        number(p + 0x50, div(sub(dx, mul(mul(timeSquare, ax), .5)), time));
        number(p + 0x58, div(sub(dy, vy), time));
        number(p + 0x60, div(sub(dz, vz), time));
    }
    void creator(uint32_t p) {
        if (get(p + 0x45c))
            return;
        put(p + 0x45c, 1);
        uint32_t actor = get(p + 0x12c), container = get(get(get(p + 0x130) + 12) + 8);
        uint32_t gem =
            create(container, 0, get(actor + 0x4c), get(actor + 0x50), get(actor + 0x64) + 1, 0x522aac, 0x40000);
        uint32_t primary = get(gem + 0x6c);
        uint32_t args[] = {gem};
        invoke(get(primary + 16), 0, args, 1);
        actor = get(p + 12);
        uint32_t x = get(actor + 0x148), y = get(actor + 0x14c);
        target(get(get(gem + 0x6c) + 24), x, y);
        uint32_t sound = get(p + 0x458);
        if (sound && get(0x532c0c))
            external(0x4b45f0, get(sound + 16), {get(0x532c10), 0, 0, 0});
    }
    void restore() {
        uint32_t actor = get(0x537e88);
        if (!actor)
            return;
        uint32_t primary = get(actor + 0x6c);
        if (!primary || get(primary + 28) != 5010)
            return;
        uint32_t priv = get(primary + 20);
        uint32_t input = get(0x537204);
        put(input + 12, get(input + 12) & 0xfdffffff);
        input = get(0x537204);
        put(input + 12, get(input + 12) & 0xfeffffff);
        uint32_t other = get(priv + 300);
        if (other) {
            uint32_t resource = get(get(other + 0x6c) + 24);
            external(0x421010, resource, {0x4207a0, 1});
            external(0x420fc0, resource + 0x2f4, {0});
            put(priv + 300, 0);
        }
        put(priv + 60, 0);
        put(priv + 32, 1);
        if (get(priv + 4)) {
            put(priv + 4, 0);
            uint32_t args[] = {get(priv + 0x124)};
            animation(0x4c8220, actor + 0x188, args, 1);
            put(actor + 8, get(actor + 8) | 0x80);
        }
        put(primary + 28, 24);
        uint32_t ani[] = {0x5246d0, 1};
        animation(0x4c79e0, actor, ani, 2);
        put(actor + 0xcc, 1);
        put(actor + 0x148, 0);
        put(actor + 0x14c, 0);
        put(actor + 0x104, 0);
        put(actor + 8, get(actor + 8) | 0x80);
        bool facing = get(priv) != 0;
        put(actor + 0x128, facing ? 0xffffffea : 0xfffffff1);
        put(actor + 0x12c, 0xffffffd3);
        put(actor + 0x130, facing ? 15 : 22);
        put(actor + 0x134, 52);
        if (!facing)
            external(0x40f6c0, actor, {0xfffffff0, 0xffffffcc, 16, 60});
        else {
            put(actor + 0x118, 0xfffffff0);
            put(actor + 0x11c, 0xffffffcc);
            put(actor + 0x120, 16);
            put(actor + 0x124, 60);
        }
        put(priv + 0xfc, 650);
        put(priv + 0x114, 1500);
        put(priv + 0x120, 15000);
        put(priv + 0x118, 0);
        std::fill_n(span(0x534e60, 6), 6, 0);
        put(actor + 0x1b0, 0x3f800000);
    }
    uint32_t pickup(uint32_t actor) {
        uint32_t primary = get(actor + 0x6c), state = get(primary + 28);
        if (state == 5) {
            uint32_t a[] = {get(0x5430c4)};
            animation(0x4c82a0, actor + 0x188, a, 1);
            return 1;
        }
        if (state == 29) {
            uint32_t effect = get(actor + 200);
            if (effect)
                put(effect + 8, get(effect + 8) | 0x10000);
            return 1;
        }
        if (state)
            return 1;
        put(primary + 0x168, 0);
        if (!get(actor + 0x190)) {
            uint32_t a[] = {0x52a198, 0};
            animation(0x4c79e0, actor, a, 2);
        }
        external(0x4c7970, actor, {0x52a1e0}, "LEVEL_GEM");
        if (!get(actor + 100)) {
            put(actor + 100, 1000);
            put(actor + 8, get(actor + 8) | 0x20000);
        }
        uint32_t app = get(0x5371fc), config = get(app + 44), mode = uint32_t(external(get(get(config) + 16), config));
        if (mode == 4 || get(get(get(0x5371fc) + 0xc0) - 8))
            external(0x4c7970, actor, {0x52a1cc}, "GAME_CHECKEDFLAG");
        else {
            external(0x4c7970, actor, {get(config + 20) & 1 ? 0x524d1cu : 0x52a1e0u});
            if (get(config + 20) == 13)
                external(0x4c7970, actor, {0x52a1e0}, "LEVEL_GEM");
        }
        uint32_t image = get(actor + 0x174);
        if (image) {
            put(actor + 0x138, get(image + 32) - get(image + 24));
            put(actor + 0x13c, get(image + 36) - get(image + 28));
            put(actor + 0x140, get(image + 24) - 1 + get(image + 32));
            put(actor + 0x144, get(image + 36) - 1 + get(image + 28));
        }
        put(actor + 8, get(actor + 8) | 0x80000);
        if (!c.loot) {
            c.fault = 1;
            throw Failed{};
        }
        if (!c.loot->words[340]) {
            uint32_t args[] = {get(actor + 12)};
            invoke(0x4719e0, 0, args, 1);
        }
        uint32_t count = c.loot->itemCount, index = 0, root = get(actor + 0x170);
        for (; si(index) < si(count); ++index) {
            step();
            if (index >= 66) {
                c.fault = 2;
                throw Failed{};
            }
            if (c.loot->words[index] == root)
                break;
        }
        uint32_t current = get(actor + 0x6c);
        if (si(index) < si(count)) {
            put(actor + 4, index ? index : 33);
            put(actor + 0xfc, c.loot->words[66 + index]);
            put(current + 0x168, c.loot->words[274 + index]);
            if (get(actor + 0xd0) == 1)
                put(actor + 0xd0, c.loot->words[132 + index]);
        } else {
            put(actor + 4, 0);
            put(actor + 0xfc, 100);
            put(current + 0x168, 0);
        }
        put(actor + 0xfc, 0x26ad);
        put(actor + 0xd0, 0x100);
        uint32_t effect = 0;
        if (get(get(0x5371fc) + 0x124))
            effect = create(get(get(actor + 12) + 8), 1, get(actor + 76), get(actor + 80), get(actor + 100) + 1,
                            0x522950, 0x240000);
        if (effect) {
            uint32_t a[] = {0x52417c, 0};
            animation(0x4c79e0, effect, a, 2);
            external(0x4c7970, effect, {0x52a1b8}, "GAME_GREENGLITTER");
        }
        put(actor + 200, effect);
        put(primary + 28, 5);
        return 1;
    }
    uint64_t invoke(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, const char *name = nullptr) {
        uint32_t need = 0;
        switch (f) {
        case 0x43ca60:
        case 0x4701b0:
        case 0x43cb20:
        case 0x4082f0:
        case 0x43cdc0:
        case 0x484d90:
        case 0x4c9e30:
        case 0x4063b0:
        case 0x4dc870:
        case 0x4719e0:
            need = 1;
            break;
        case 0x43d0f0:
            need = 2;
            break;
        case 0x4c79e0:
        case 0x420a10:
            need = 2;
            break;
        case 0x4c8220:
        case 0x4c82a0:
            need = 1;
            break;
        default:
            break;
        }
        if (n != need) {
            ClawEndLevelGemCall e{};
            e.function = f;
            e.receiver = t;
            e.argumentCount = n;
            std::copy_n(a, n, e.arguments);
            e.name = name;
            return external(e);
        }
        switch (f) {
        case 0x4719e0: {
            if (!c.composeLoot)
                return external(f, t, {a[0]});
            if (!c.loot) {
                c.fault = 1;
                throw Failed{};
            }
            ClawWorldLootContext q{};
            q.scene = host();
            q.composeCreation = c.composeCreation;
            uint32_t value = claw_world_loot_initialize(a[0], c.loot, &q, lootCall, this);
            if (q.fault) {
                c.fault = q.fault;
                throw Failed{};
            }
            return value;
        }
        case 0x43ca60:
            return wrapper(a[0]);
        case 0x4701b0:
            return pickup(a[0]);
        case 0x43cb20:
            return construct(t, a[0]);
        case 0x4082f0:
            base(t, a[0]);
            return t;
        case 0x43cdc0:
            return dispatch(t, a[0]);
        case 0x43d070:
            return idle(t);
        case 0x43d0f0:
            target(t, a[0], a[1]);
            return 0;
        case 0x40e5c0:
            creator(t);
            return 0;
        case 0x4205b0:
            restore();
            return 0;
        case 0x4dc870:
            return common(f, a[0]);
        case 0x4dca10:
            return common(f, t);
        case 0x4063b0:
            return common(f, t, a[0]);
        case 0x4c96b0:
        case 0x4bb030:
        case 0x4c9e30:
            return 0;
        case 0x484d90:
        case 0x456030: {
            ClawStackedActorLifecycleContext q{};
            q.scene = host();
            uint32_t out = 0;
            claw_stacked_actor_lifecycle_entry(f, t, a, n, &q, &out);
            if (q.fault) {
                c.fault = q.fault;
                throw Failed{};
            }
            return out;
        }
        case 0x4c79e0:
        case 0x4c8220:
        case 0x4c82a0:
        case 0x420a10:
            return animation(f, t, a, n);
        default: {
            ClawEndLevelGemCall e{};
            e.function = f;
            e.receiver = t;
            e.argumentCount = n;
            std::copy_n(a, n, e.arguments);
            e.name = name;
            return external(e);
        }
        }
    }
};
bool supported(uint32_t f, uint32_t &n) {
    n = 0;
    switch (f) {
    case 0x40e5c0:
    case 0x43d070:
    case 0x4205b0:
    case 0x4dca10:
    case 0x456030:
    case 0x4c96b0:
    case 0x4bb030:
        return true;
    case 0x43ca60:
    case 0x4701b0:
    case 0x43cb20:
    case 0x43cdc0:
    case 0x4082f0:
    case 0x4dc870:
    case 0x4063b0:
    case 0x484d90:
    case 0x4c9e30:
    case 0x4719e0:
        n = 1;
        return true;
    case 0x43d0f0:
        n = 2;
        return true;
    default:
        return false;
    }
}
} // namespace
extern "C" void claw_end_level_gem_defaults(ClawEndLevelGemContext *c) {
    if (c) {
        c->composeCreation = c->composeAnimation = c->composeCommon = c->composeLoot = 1;
        c->maximumSteps = 65536;
    }
}
extern "C" uint32_t claw_end_level_gem_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                             ClawEndLevelGemContext *c, ClawEndLevelGemDependency d, void *u,
                                             uint32_t *out) {
    uint32_t count;
    if (!supported(f, count))
        return 0;
    if (out)
        *out = 0;
    if (!c)
        return 1;
    c->fault = 0;
    if (n != count || (n && !a)) {
        c->fault = 2;
        return 1;
    }
    Run r{*c, d, u};
    uint64_t value = 0;
    try {
        value = r.invoke(f, t, a, n);
    } catch (Failed &) {
    }
    if (out)
        *out = uint32_t(value);
    return 1;
}
namespace {
uint32_t awardCall(ClawPowerupObjectContext *q, const ClawPowerupObjectCall *e, void *p) {
    auto &r = *static_cast<Run *>(p);
    uint32_t out = uint32_t(r.invoke(e->function, e->receiver, e->arguments, e->argumentCount, e->name));
    if (r.c.fault)
        q->fault = r.c.fault;
    return out;
}
} // namespace
extern "C" uint32_t claw_end_level_gem_award(uint32_t item, ClawEndLevelGemContext *c, ClawEndLevelGemDependency d,
                                             void *u, uint32_t *out) {
    if (!c || !c->pickups)
        return 0;
    c->fault = 0;
    Run r{*c, d, u};
    uint32_t result = 0;
    try {
        if (r.get(item + 0xfc) != 0x26ad)
            return 0;
        auto *q = c->pickups;
        struct RestoreHost {
            ClawPowerupObjectContext *q;
            ClawSceneActorHost previous;
            ~RestoreHost() {
                q->scene = previous;
            }
        } restore{q, q->scene};
        q->scene = r.host();
        q->fault = 0;
        if (!claw_powerup_object_award(item, q, awardCall, &r, &result) || q->fault)
            c->fault = q->fault ? q->fault : 1;
    } catch (Failed &) {
    }
    if (out)
        *out = result;
    return c->fault ? 0 : 1;
}
