#include "SpecialCommandRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
struct Runtime {
    ClawSpecialCommandContext &c;
    ClawSpecialCommandDependency d;
    void *u;
    ClawSpecialCommandGlobals &g;
    uint32_t *p(uint32_t t, uint32_t n = 1) {
        auto v = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!v) {
            c.fault = 1;
            throw Failure{};
        }
        return v;
    }
    uint32_t get(uint32_t t, uint32_t b = 0) {
        return *p(t + b);
    }
    void set(uint32_t t, uint32_t b, uint32_t v) {
        *p(t + b) = v;
    }
    uint32_t call(uint32_t f, uint32_t r, std::initializer_list<uint32_t> a = {}, const char *name = nullptr,
                  uint32_t mask = 0, uint32_t *buf = nullptr, uint32_t n = 0) {
        ClawSpecialCommandCall e{};
        e.function = f;
        e.receiver = r;
        e.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), e.arguments);
        e.name = name;
        e.localMask = mask;
        e.buffer = buf;
        e.bufferWords = n;
        if (d)
            return d(&c, &e, u);
        if (e.argumentCount > 4) {
            c.fault = 3;
            throw Failure{};
        }
        ClawSceneActorCall v{};
        v.function = f;
        v.receiver = r;
        v.argumentCount = e.argumentCount;
        std::copy(a.begin(), a.end(), v.arguments);
        return c.scene.call ? c.scene.call(c.scene.context, v) : 0;
    }
    uint32_t virt(uint32_t r, uint32_t b, std::initializer_list<uint32_t> a = {}) {
        auto f = get(get(r), b);
        if (f == 0x40af90)
            return 3;
        if (f == 0x40b120)
            return enter(r, *a.begin());
        if (f == 0x46c630)
            return warp(r);
        if (f == 0x46c900)
            return map(r);
        if (f == 0x40ac20) {
            auto it = a.begin();
            uint32_t x = *it++, y = *it++, z = *it;
            return booty(r, x, y, z);
        }
        return call(f, r, a);
    }
    bool ready(uint32_t app) {
        if (!get(app, 0x2c))
            return false;
        if (virt(get(app, 0x2c), 0x10) == 3)
            return true;
        if (virt(get(app, 0x2c), 0x10) == 4)
            return true;
        return virt(get(app, 0x2c), 0x10) == 6;
    }
    uint32_t clock() {
        return c.scene.readClock ? c.scene.readClock(c.scene.context) : 0;
    }
    void reset(uint32_t app) {
        if (!c.scene.readClock) {
            c.fault = 3;
            throw Failure{};
        }
        ClawTimingHost h{c.scene.context, c.scene.readClock, nullptr};
        claw_timing_reset_clock(&g.clock, h);
        if (get(app, 0x30)) {
            g.animation.nowMilliseconds = clock();
            g.animation.deltaMilliseconds = 0;
        }
        g.stage.nowMilliseconds = g.clock.nowMilliseconds;
        g.stage.deltaMilliseconds = g.clock.deltaMilliseconds;
        if (g.playerToken) {
            auto v = get(get(g.playerToken, 0x6c), 0x14);
            if (v)
                set(v, 0x120, 20000);
        }
    }
    void music(uint32_t app, bool resume) {
        if (get(app, 0x50) && get(app, 0x14)) {
            auto t = get(app, 0x50);
            if (resume)
                call(0x4b55b0, t, {0});
            else
                call(0x4b55a0, t);
        }
    }
    uint32_t fade(uint32_t owner, uint32_t steps, uint32_t duration, uint32_t flag, bool in) {
        auto fm = get(owner, 0x10);
        if (!fm)
            return 0;
        if (!get(get(owner, 12), 0x1c))
            return 0;
        auto surface = get(get(owner, 12), 4), back = get(get(surface, 0x10), 0x2c);
        if (!back)
            return 0;
        uint32_t front = 0;
        if (in) {
            front = get(get(surface, 0x14), 0x2c);
            if (!front)
                return 0;
        }
        uint32_t packet[5] = {3, back, front, in ? 0u : 1u, steps};
        auto f = call(0x4ec050, fm, {2, 0}, nullptr, 2, packet, 5);
        if (!f)
            return 0;
        music(get(owner, 4), false);
        if (!g.fadeBypass)
            call(0x4ec9c0, f, {duration, flag, 0});
        else {
            call(0x4b8960, 0, {duration});
            auto live = get(get(get(get(owner, 12), 4), 0x10), 0x2c);
            if (in)
                call(0x4b9c50, live, {front});
            else
                call(0x4b97c0, live, {0});
        }
        music(get(owner, 4), true);
        removeFader(fm, f);
        return 1;
    }
    void removeFader(uint32_t m, uint32_t f) {
        bool found = false;
        int32_t i = 0;
        while (i < int32_t(get(m, 0x18))) {
            auto data = get(m, 0x14);
            if (get(data, uint32_t(i) * 4) == f) {
                auto count = get(m, 0x18);
                if (int32_t(count - i - 1) > 0)
                    std::memmove(p(data + uint32_t(i) * 4, count - i - 1), p(data + uint32_t(i + 1) * 4, count - i - 1),
                                 (count - i - 1) * 4);
                set(m, 0x18, count - 1);
                found = true;
                break;
            }
            ++i;
        }
        if (found && f)
            virt(f, 0, {1});
    }
    uint32_t plane(uint32_t o) {
        return get(get(get(o, 12), 0x24), 0x5c);
    }
    uint32_t warp(uint32_t o) {
        if (int32_t(g.warpX) <= 0 || int32_t(g.warpY) <= 0 || !g.playerToken)
            return 0;
        set(g.playerToken, 0x4c, g.warpX);
        set(g.playerToken, 0x50, g.warpY);
        g.warpX = g.warpY = 0xffffffff;
        auto registry = get(get(o, 12), 0x28);
        if (!get(registry, 0x30)) {
            auto sound = call(0x4f6286, registry + 0x10, {0x52a07c}, "GAME_WARP");
            if (sound)
                call(0x4208e0, sound, {g.audioVolume, 0, 0, 0});
        }
        fade(o, 80, 1450, 0, false);
        reset(get(o, 4));
        for (int i = 0; i < 2; ++i) {
            auto t = plane(o);
            if (t)
                call(0x4d2000, t);
            t = plane(o);
            if (t)
                call(0x4d1fd0, t);
            virt(get(get(o, 12), 8), 0x24, {1});
        }
        auto sc = get(o, 12);
        call(0x4cb9b0, get(sc, 0x24), {get(get(sc, 4), 0x14), get(sc, 8)});
        sc = get(o, 12);
        auto surface = get(sc, 4);
        virt(get(sc, 12), 0x34, {get(surface, 0x14), get(surface, 0x18)});
        if (fade(o, 80, 1450, 0, true)) {
            reset(get(o, 4));
            return 1;
        }
        return 0;
    }
    void settings(uint32_t o) {
        if (virt(o, 12) && get(o, 4)) {
            auto t = get(get(o, 4), 0x38);
            if (t) {
                call(0x4b5e50, t, {0x5258a8, get(get(o, 4), 0x68)}, "Status Layout");
                call(0x4b5e50, t, {0x525860, g.displayRankings}, "Display Rankings");
            }
        }
    }
    void stats(uint32_t o, uint32_t player) {
        auto level = get(o, 0x14);
        if (!player || int32_t(level) <= 0 || int32_t(level) >= 15 || get(o, level * 16 + 0x164))
            return;
        auto previous = get(o, 0x160);
        set(o, 0x160, get(player, 0xf8));
        set(o, 0x164, get(o, 0x164) + g.accumulatedTick);
        set(o, (level + 0x16) * 16, get(player, 0xf8) - previous);
        set(o, level * 16 + 0x164, g.accumulatedTick);
        if (get(get(get(o, 4), 0x48), 0x128)) {
            set(o, level * 16 + 0x168, get(o, level * 16 + 0x168) | 1);
            set(o, 0x168, get(o, 0x168) | 1);
        }
    }
    void capture(uint32_t player) {
        if (!player)
            return;
        auto primary = get(player, 0x6c);
        if (!primary)
            return;
        auto priv = get(primary, 0x14);
        if (!priv)
            return;
        set(priv, 0x44, get(player, 0xf8));
        set(priv, 0x48, get(player, 0x10c));
        set(priv, 4, 0);
        std::memcpy(g.capturedPlayer, p(priv, 78), 312);
        auto o = get(g.managerToken, 0x2c);
        if (o && ready(g.managerToken))
            stats(o, player);
    }
    void teardown(uint32_t o) {
        settings(o);
        capture(g.playerToken);
        auto manager = get(o, 4);
        if (manager) {
            auto service = get(manager, 0x58);
            if (service)
                for (uint32_t b : {0x768u, 0x76cu, 0x770u, 0x150u})
                    if (get(o, b)) {
                        call(0x4c7510, service, {get(o, b)});
                        set(o, b, 0);
                    }
        }
        if (get(o, 12)) {
            auto registry = get(get(o, 12), 0x28), audio = get(registry, 0x2c);
            if (audio)
                call(0x4b4b40, audio);
            call(0x4ca300, get(get(o, 12), 0x28));
        }
        manager = get(o, 4);
        if (manager && get(manager, 0x3c)) {
            call(0x4b5c10, get(manager, 0x3c));
            set(get(get(o, 4), 0x3c), 0x44, 0);
        }
        if (get(o, 4)) {
            call(0x4b5340, get(get(o, 4), 0x50));
            call(0x4022a0, get(get(o, 4), 0x5c));
        }
        if (get(o, 12))
            virt(get(get(o, 12), 0x10), 0x58);
        if (get(o, 12))
            call(0x4cdf40, get(get(o, 12), 0x2c));
        if (get(o, 12))
            virt(get(get(o, 12), 0x24), 0x44);
        if (get(o, 12))
            call(0x4c89e0, get(get(o, 12), 8));
        manager = get(o, 4);
        if (manager && get(manager, 0x4c))
            call(0x422350, get(manager, 0x4c));
        g.playerToken = 0;
    }
    void history(uint32_t app, uint32_t token) {
        if (!token)
            return;
        auto a = p(app + 0xdc, 5);
        auto count = a[2], need = count + 1;
        if (!a[1]) {
            a[1] = alloc(need * 4);
            if (!a[1]) {
                c.fault = 2;
                throw Failure{};
            }
            std::memset(p(a[1], need), 0, need * 4);
            a[3] = need;
        } else if (int32_t(need) > int32_t(a[3])) {
            auto grow = a[4];
            if (!grow)
                grow = uint32_t(std::max(4, std::min(1024, int32_t(count) / 8)));
            auto cap = a[3] + grow;
            if (int32_t(need) >= int32_t(cap))
                cap = need;
            auto t = alloc(cap * 4);
            if (!t) {
                c.fault = 2;
                throw Failure{};
            }
            std::memcpy(p(t, cap), p(a[1], count), count * 4);
            std::memset(p(t + count * 4, need - count), 0, (need - count) * 4);
            free(a[1]);
            a[1] = t;
            a[3] = cap;
        } else if (int32_t(need) > int32_t(count))
            std::memset(p(a[1] + count * 4, need - count), 0, (need - count) * 4);
        a[2] = need;
        set(a[1], count * 4, token);
    }
    uint32_t alloc(uint32_t n) {
        return c.scene.allocate ? c.scene.allocate(c.scene.context, n) : 0;
    }
    void free(uint32_t t) {
        if (c.scene.free)
            c.scene.free(c.scene.context, t);
    }
    void clear(uint32_t app) {
        int32_t i = 0;
        while (i < int32_t(get(app, 0xe4))) {
            auto t = get(get(app, 0xe0), uint32_t(i) * 4);
            if (t)
                virt(t, 0, {1});
            ++i;
        }
        free(get(app, 0xe0));
        set(app, 0xe0, 0);
        set(app, 0xe8, 0);
        set(app, 0xe4, 0);
    }
    void base(uint32_t t) {
        call(0x40b5c0, t);
    }
    void inlineBase(uint32_t t, bool table = true) {
        if (table)
            set(t, 0, 0x50b4ec);
        for (uint32_t b : {4u, 8u, 12u, 0x1cu, 0x20u, 0x24u, 0x2cu, 0x30u, 0x3cu, 0x40u, 0x34u, 0x18u, 0x150u})
            set(t, b, 0);
        set(t, 0x4c, get(t, 0x4c) & 0xffffff00);
    }
    uint32_t transition(uint32_t app, uint32_t level, uint32_t retain) {
        uint32_t previous = 0;
        auto o = get(app, 0x2c);
        if (o) {
            previous = virt(o, 0x10);
            virt(get(app, 0x2c), 0x28, {10});
            if (retain) {
                history(app, get(app, 0x2c));
                set(app, 0x2c, 0);
            } else {
                auto t = get(app, 0x2c);
                if (t)
                    virt(t, 0, {1});
                clear(app);
                set(app, 0x2c, 0);
            }
        } else if (!retain)
            clear(app);
        if (get(app, 0xa0)) {
            auto t = alloc(0x154);
            if (t)
                inlineBase(t);
            set(app, 0x2c, t);
            return 1;
        }
        auto t = alloc(0x160);
        if (t) {
            base(t);
            set(t, 0, 0x50c0c4);
            set(t, 0x158, 0);
            set(t, 0x154, 0);
            set(t, 0x15c, 10);
        }
        set(app, 0x2c, t);
        if (!t) {
            set(get(app, 8), 0x244, 0);
            return 0;
        }
        reset(app);
        auto ok = virt(get(app, 0x2c), 4, {app, level, previous});
        t = get(app, 0x2c);
        if (!ok) {
            if (t)
                virt(t, 0, {1});
            set(app, 0x2c, 0);
            return 0;
        }
        virt(t, 0x24, {previous});
        set(get(app, 8), 0x244, 1);
        call(0x431300, g.inputMappingToken);
        set(g.inputMappingToken, 12, 0xffffffff);
        call(0x4b3ab0, g.mouseToken);
        set(g.mouseToken, 0x20c, 0xffffffff);
        reset(app);
        return 1;
    }
    uint32_t map(uint32_t o) {
        teardown(o);
        g.playerToken = 0;
        if (!get(o, 0x258)) {
            call(0x46d620, o, {0, 0, 3});
            call(0x49bbc0, get(get(o, 4), 0x60));
        }
        if (get(o, 0x14) == 14)
            set(o, 0x25c, 1);
        auto manager = get(o, 4);
        if (get(manager, 0x9c)) {
            if (get(o, 0x25c)) {
                if (get(o, 12) && get(o, 0x2c)) {
                    call(0x4bb870, get(get(o, 0x2c), 0x10));
                    call(0x4bb990, get(get(o, 0x2c), 0x10), {0, 256, 0, 0, 0, 500});
                    for (int i = 0; i < 2; ++i) {
                        auto surface = get(get(o, 12), 4);
                        call(0x4b97c0, get(get(surface, 0x14), 0x2c), {0});
                        call(0x4b98b0, get(get(surface, 0x10), 0x2c), {0});
                    }
                }
                call(0x42b910, get(o, 4));
                call(0x42abb0, get(o, 4));
                return 1;
            }
            call(0x546d50, 0, {get(get(manager, 4), 4), 0x111, 0x8075, 0});
            return 1;
        }
        if (!transition(manager, get(o, 0x14), 1)) {
            call(0x429e10, get(o, 4), {0x8005, 0x702});
            return 0;
        }
        return 1;
    }
    uint32_t enter(uint32_t o, uint32_t previous) {
        auto child = get(o, 0x154);
        return child ? virt(child, 0x24, {previous}) : 1;
    }
    uint32_t booty(uint32_t o, uint32_t app, uint32_t level, uint32_t previous) {
        if (previous != 3)
            return 0;
        if (!call(0x42bfd0, app))
            return 0;
        if (!call(0x48f0d0, o, {app, level, 3}))
            return 0;
        if (!call(0x42af50, get(o, 4)))
            call(0x42a000, get(o, 4), {0});
        set(o, 0x15c, get(get(o, 4), 0x68));
        call(0x429ed0, get(o, 4), {10, 0, 1});
        auto data = call(0x4b7f20, get(o, 8), {0x523b1c}, "STATES_BOOTY");
        set(o, 0x20, data);
        if (!data)
            return 0;
        data = call(0x4b7f20, get(o, 8), {0x523734}, "CLAW");
        set(o, 0x24, data);
        if (!data)
            return 0;
        call(0x4c89e0, get(get(o, 12), 8));
        call(0x4ca300, get(get(o, 12), 0x28));
        data = call(0x4b68c0, get(o, 0x20), {0x52372c}, "SOUNDS");
        if (!data)
            return 0;
        call(0x4ca440, get(get(o, 12), 0x28), {data, 0x523b14, 0x523728}, "BOOTY");
        while (int32_t(call(0x546d54, 0, {0})) >= 0) {
        }
        call(0x4b8910, get(get(o, 4), 4), {0x100, 0x40});
        uint32_t child;
        if (!get(get(o, 4), 0x130)) {
            child = alloc(0x158);
            if (child) {
                inlineBase(child, false);
                set(child, 0, 0x50b43c);
                set(child, 0x154, 0);
            }
        } else {
            child = alloc(0x184);
            if (child) {
                inlineBase(child);
                call(0x4f6439, child + 0x180);
                set(child, 0, 0x50b494);
                set(child, 0x154, 0);
                set(child, 0x158, 0);
                std::memset(p(child + 0x15c, 9), 0, 36);
            }
        }
        set(o, 0x154, child);
        if (virt(child, 4, {app, level, 3})) {
            set(o, 0x158, 0);
            call(0x4b3ab0, g.mouseToken);
            return 1;
        }
        return 0;
    }
    uint32_t command(uint32_t app, uint32_t command) {
        if (command == 0x805c) {
            if (ready(app))
                virt(get(app, 0x2c), 0x54);
            return 1;
        }
        if (command == 0x800e) {
            if (ready(app) && !virt(get(app, 0x2c), 0x40))
                call(0x546d44, 0, {get(get(app, 4), 4), 0x111, 0x8023, 0});
            return 1;
        }
        if (command == 0x8023) {
            if (!call(0x428c40, app, {5, 1, 0, 0}))
                call(0x429e10, app, {0x8005, 0x3f7});
            return 1;
        }
        return 0;
    }
};
} // namespace
extern "C" uint32_t claw_special_command_entry(uint32_t f, uint32_t r, const uint32_t *a, uint32_t n,
                                               ClawSpecialCommandContext *c, ClawSpecialCommandDependency d, void *u,
                                               uint32_t *out) {
    if (!c || !c->globals || !out || (n && !a))
        return 0;
    Runtime x{*c, d, u, *c->globals};
    c->fault = 0;
    *out = 0;
    try {
        switch (f) {
        case 0x426e30:
            if (n != 3 || !(a[1] == 0x805c || a[1] == 0x800e || a[1] == 0x8023))
                return 0;
            *out = x.command(r, a[1]);
            break;
        case 0x46c630:
            *out = x.warp(r);
            break;
        case 0x46c900:
            *out = x.map(r);
            break;
        case 0x42abf0:
            x.reset(r);
            break;
        case 0x42d420:
        case 0x42d440:
            x.music(r, f == 0x42d440);
            break;
        case 0x48feb0:
        case 0x48fda0:
            if (n != 3)
                return 0;
            *out = x.fade(r, a[0], a[1], a[2], f == 0x48fda0);
            break;
        case 0x46b7b0:
            x.teardown(r);
            break;
        case 0x46bbc0:
            x.settings(r);
            break;
        case 0x415d90:
            if (n != 1)
                return 0;
            x.capture(a[0]);
            break;
        case 0x46c7b0:
            if (n != 1)
                return 0;
            x.stats(r, a[0]);
            break;
        case 0x428c40:
            if (n != 4 || a[0] != 10)
                return 0;
            *out = x.transition(r, a[1], a[2]);
            break;
        case 0x40ac20:
            if (n != 3)
                return 0;
            *out = x.booty(r, a[0], a[1], a[2]);
            break;
        case 0x40b120:
            if (n != 1)
                return 0;
            *out = x.enter(r, a[0]);
            break;
        case 0x4ecc00: {
            const uint32_t packet[5] = {3, 0, 0, 1, 15};
            std::copy(packet, packet + 5, x.p(r, 5));
            *out = r;
            break;
        }
        case 0x4ec600:
            if (n != 1)
                return 0;
            x.removeFader(r, a[0]);
            break;
        default:
            return 0;
        }
    } catch (Failure &) {
    }
    return 1;
}
