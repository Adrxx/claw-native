#include "PlayerDeathCommands.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
struct Runtime {
    ClawSceneActorHost h;
    uint32_t *fault;
    ClawPlayerDeathCommandGlobals *g;
    uint32_t *p(uint32_t t, uint32_t n) {
        auto *v = h.lookup ? h.lookup(h.context, t, n) : nullptr;
        if (!v) {
            *fault = 1;
            throw Failure{};
        }
        return v;
    }
    uint32_t get(uint32_t t, uint32_t b) {
        return *p(t + b, 1);
    }
    void set(uint32_t t, uint32_t b, uint32_t v) {
        *p(t + b, 1) = v;
    }
    uint32_t call(uint32_t fn, uint32_t receiver, std::initializer_list<uint32_t> a = {}) {
        ClawSceneActorCall c{};
        c.function = fn;
        c.receiver = receiver;
        c.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), c.arguments);
        return h.call ? h.call(h.context, c) : 0;
    }
    uint32_t virt(uint32_t t, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        uint32_t fn = get(get(t, 0), slot);
        if (slot == 0x10 && fn == 0x40af90)
            return 3;
        if (slot == 0x10 && fn == 0x4c9bd0)
            return 5;
        if (slot == 0x10 && fn == 0x4298c0)
            return 12;
        if (fn == 0x4bd250 || fn == 0x40af30)
            return 1;
        return call(fn, t, a);
    }
    uint32_t alloc(uint32_t n) {
        return h.allocate ? h.allocate(h.context, n) : 0;
    }
    void free(uint32_t t) {
        if (h.free)
            h.free(h.context, t);
    }
    void reset(uint32_t app) {
        ClawTimingHost th{h.context, h.readClock, nullptr};
        claw_timing_reset_clock(&g->clock, th);
        if (get(app, 0x30)) {
            g->animation.nowMilliseconds = h.readClock(h.context);
            g->animation.deltaMilliseconds = 0;
        }
        g->stage.nowMilliseconds = g->clock.nowMilliseconds;
        g->stage.deltaMilliseconds = g->clock.deltaMilliseconds;
        if (g->playerToken) {
            uint32_t l = get(g->playerToken, 0x6c), v = get(l, 0x14);
            if (v)
                set(v, 0x120, 0x4e20);
        }
    }
    void history(uint32_t app, uint32_t token) {
        if (!token)
            return;
        auto *a = p(app + 0xdc, 5);
        uint32_t count = a[2], need = count + 1;
        if (!a[1]) {
            a[1] = alloc(need * 4);
            if (!a[1]) {
                *fault = 2;
                throw Failure{};
            }
            std::memset(p(a[1], need), 0, need * 4);
            a[3] = need;
        } else if (int32_t(need) > int32_t(a[3])) {
            uint32_t grow = a[4];
            if (!grow)
                grow = uint32_t(std::max(4, std::min(1024, int32_t(count) / 8)));
            uint32_t capacity = a[3] + grow;
            if (int32_t(need) >= int32_t(capacity))
                capacity = need;
            uint32_t t = alloc(capacity * 4);
            if (!t) {
                *fault = 2;
                throw Failure{};
            }
            std::memcpy(p(t, capacity), p(a[1], count), count * 4);
            std::memset(p(t + count * 4, need - count), 0, (need - count) * 4);
            free(a[1]);
            a[1] = t;
            a[3] = capacity;
        } else if (int32_t(need) > int32_t(count))
            std::memset(p(a[1] + count * 4, need - count), 0, (need - count) * 4);
        a[2] = need;
        set(a[1], count * 4, token);
    }
    void clear(uint32_t app) {
        int32_t i = 0;
        while (i < int32_t(get(app, 0xe4))) {
            uint32_t t = get(get(app, 0xe0), uint32_t(i) * 4);
            if (t)
                virt(t, 0, {1});
            ++i;
        }
        free(get(app, 0xe0));
        set(app, 0xe0, 0);
        set(app, 0xe8, 0);
        set(app, 0xe4, 0);
    }
    void cleanupActor(uint32_t actor) {
        if (actor && (get(actor, 0x164) & 0x2000))
            set(actor, 8, get(actor, 8) | 0x10000);
    }
    void cleanup(uint32_t owner) {
        uint32_t parent = get(owner, 0xc);
        if (!parent)
            return;
        uint32_t list = get(parent, 8) + 0x10;
        if (list) {
            uint32_t node = get(list, 4);
            while (node) {
                uint32_t actor = get(node, 8);
                node = get(node, 0);
                cleanupActor(actor);
            }
        }
        parent = get(owner, 0xc);
        uint32_t map = get(parent, 0x24);
        if (map) {
            uint32_t plane = get(map, 0x5c);
            if (plane) {
                uint32_t tree = get(plane, 0xb0);
                if (tree)
                    call(0x4d51f0, tree, {0x46e340});
            }
        }
    }
    uint32_t plane(uint32_t owner) {
        return get(get(get(owner, 0xc), 0x24), 0x5c);
    }
    uint32_t wrap(uint32_t value, uint32_t planeToken, uint32_t sizeOffset, uint32_t lowOffset, uint32_t highOffset) {
        uint32_t size = get(planeToken, sizeOffset);
        if (int32_t(value) < 0)
            value += size;
        else if (int32_t(value) >= int32_t(size))
            value -= size;
        uint32_t hi = get(planeToken, highOffset);
        if (int32_t(hi) >= int32_t(size) && int32_t(value) < int32_t(get(planeToken, lowOffset)) &&
            int32_t(value) <= int32_t(hi - size))
            value += size;
        return value;
    }
    void project(uint32_t planeToken, uint32_t &x, uint32_t &y) {
        if (get(planeToken, 8) & 4)
            x = wrap(x, planeToken, 0x30, 0x40, 0x48);
        if (get(planeToken, 8) & 8)
            y = wrap(y, planeToken, 0x34, 0x44, 0x4c);
        x += get(planeToken, 0x50) - get(planeToken, 0x40);
        y += get(planeToken, 0x54) - get(planeToken, 0x44);
    }
    void sound(uint32_t owner, uint32_t name) {
        uint32_t registry = get(get(owner, 0xc), 0x28);
        if (get(registry, 0x30))
            return;
        uint32_t s = call(0x4061b0, registry, {name});
        if (s)
            call(0x4208e0, s, {g->masterVolume, 0, 0, 0});
    }
    uint32_t respawn(uint32_t owner) {
        if (!g->playerToken || !get(owner, 0x2c))
            return 0;
        // Exact gating inside42d420/42d440 is retained; their audio transport
        // functions are services shared with the application music controller.
        uint32_t app = get(owner, 4);
        if (get(app, 0x50) && get(app, 0x14))
            call(0x4b55a0, get(app, 0x50));
        uint32_t firstPlane = plane(owner);
        if (firstPlane) {
            uint32_t x = get(g->playerToken, 0x4c) + ((get(g->playerToken, 0x40) & 2) ? uint32_t(-30) : 30);
            uint32_t y = get(g->playerToken, 0x50) + 55;
            project(firstPlane, x, y);
            if (int32_t(x) >= int32_t(get(app, 0x7c)))
                x = get(app, 0x7c) - 32;
            if (int32_t(y) >= int32_t(get(app, 0x80)))
                y = get(app, 0x80) - 32;
            if (int32_t(x) <= 0)
                x = 32;
            if (int32_t(y) <= 0)
                y = 32;
            sound(owner, 0x52a00c);
            call(0x48fae0, owner, {x, y, 1250, 0});
        }
        set(get(g->playerToken, 0x6c), 0x1c, 23);
        call(get(get(g->playerToken, 0x6c), 0x10), 0, {g->playerToken});
        cleanup(owner);
        uint32_t t = plane(owner);
        if (t)
            call(0x4d2000, t);
        t = plane(owner);
        if (t)
            call(0x4d1fd0, t);
        virt(get(get(owner, 0xc), 8), 0x24, {1});
        t = plane(owner);
        if (t)
            call(0x4d2000, t);
        t = plane(owner);
        if (t)
            call(0x4d1fd0, t);
        virt(get(get(owner, 0xc), 8), 0x24, {1});
        uint32_t parent = get(owner, 0xc);
        call(0x4cb9b0, get(parent, 0x24), {get(get(parent, 4), 0x14), get(parent, 8)});
        parent = get(owner, 0xc);
        virt(get(parent, 0xc), 0x34, {get(get(parent, 4), 0x14), get(get(parent, 4), 0x18)});
        if (firstPlane) {
            uint32_t x = get(g->playerToken, 0x4c), y = get(g->playerToken, 0x50) - 32;
            project(firstPlane, x, y);
            if (get(owner, 0x44) == 0xffffffff)
                sound(owner, 0x5246b4);
            call(0x48fbe0, owner, {x, y, 1000, 500});
        }
        app = get(owner, 4);
        if (get(app, 0x50) && get(app, 0x14))
            call(0x4b55b0, get(app, 0x50), {0});
        reset(get(owner, 4));
        return 1;
    }
    uint32_t construct(uint32_t type) {
        uint32_t t = alloc(0x2c8);
        if (!t)
            return 0;
        call(0x40b5c0, t);
        if (type == 5) {
            call(0x4dcc40, t + 0x154, {640, 480});
            set(t, 0x154, 0x50c23c);
            call(0x4f5cbd, t + 0x2ac, {10});
            set(t, 0, 0x50c1e4);
            for (uint32_t b : {0x25cu, 0x260u, 0x264u, 0x26cu, 0x268u, 0x270u, 0x274u, 0x278u, 0x294u, 0x298u, 0x29cu})
                set(t, b, 0);
            set(t, 0x2a8, 1000);
            for (uint32_t b : {0x2a0u, 0x2a4u, 0x28cu, 0x290u})
                set(t, b, 0);
            call(0x546d5c, t + 0x27c, {480, 0, 640, 0});
        } else {
            call(0x429980, t + 0x154);
            call(0x4f5cbd, t + 0x2a4, {10});
            set(t, 0, 0x50bfec);
            for (uint32_t b : {0x254u, 0x258u, 0x25cu, 0x260u, 0x264u})
                set(t, b, 0);
            set(t, 0x29c, 640);
            set(t, 0x2a0, 480);
            for (uint32_t b : {0x268u, 0x27cu, 0x280u})
                set(t, b, 0);
            set(t, 0x284, 1000);
            set(t, 0x288, 1000);
            set(t, 0x28c, 1000);
            set(t, 0x290, 10);
            set(t, 0x294, 0);
            set(t, 0x298, 0);
            call(0x4296f0, t + 0x26c, {160, 120, 480, 360});
        }
        return t;
    }
    uint32_t transition(uint32_t app, uint32_t type, uint32_t parameter, uint32_t retain, uint32_t extra = 0,
                        ClawApplicationStateConstructor constructor = nullptr, void *user = nullptr) {
        const bool extended = type == 3 || type == 8;
        if (type != 5 && type != 12 && (!extended || !constructor)) {
            *fault = 3;
            throw Failure{};
        }
        uint32_t oldType = 0, t = get(app, 0x2c);
        if (t) {
            oldType = virt(t, 0x10);
            virt(get(app, 0x2c), 0x28, {type});
            if (retain) {
                history(app, get(app, 0x2c));
                set(app, 0x2c, 0);
            } else {
                t = get(app, 0x2c);
                if (t)
                    virt(t, 0, {1});
                clear(app);
                set(app, 0x2c, 0);
            }
        } else if (!retain)
            clear(app);
        if (get(app, 0xa0)) {
            t = alloc(0x154);
            if (t) {
                set(t, 0, 0x50b4ec);
                for (uint32_t b : {4u, 8u, 12u, 0x1cu, 0x20u, 0x24u, 0x2cu, 0x30u, 0x3cu, 0x40u, 0x34u})
                    set(t, b, 0);
                auto *byte = reinterpret_cast<unsigned char *>(p(t + 0x4c, 1));
                byte[0] = 0;
                set(t, 0x18, 0);
                set(t, 0x150, 0);
            }
            set(app, 0x2c, t);
            return 1;
        }
        t = extended ? constructor(app, type, extra, h, fault, user) : construct(type);
        if (*fault)
            throw Failure{};
        set(app, 0x2c, t);
        if (!t) {
            set(get(app, 8), 0x244, 0);
            return 0;
        }
        reset(app);
        uint32_t ok = virt(get(app, 0x2c), 4, {app, parameter, oldType});
        t = get(app, 0x2c);
        if (!ok) {
            if (t)
                virt(t, 0, {1});
            set(app, 0x2c, 0);
            return 0;
        }
        virt(t, 0x24, {oldType});
        set(get(app, 8), 0x244, 1);
        call(0x431300, g->keyboardToken);
        set(g->keyboardToken, 0xc, 0xffffffff);
        call(0x4b3ab0, g->mouseToken);
        set(g->mouseToken, 0x20c, 0xffffffff);
        reset(app);
        return 1;
    }
    uint32_t command(uint32_t app, uint32_t command) {
        if (command == 0x803a) {
            uint32_t t = get(app, 0x2c);
            if (!t)
                return 1;
            bool allowed = virt(t, 0x10) == 3;
            if (!allowed)
                allowed = virt(get(app, 0x2c), 0x10) == 4;
            if (!allowed)
                allowed = virt(get(app, 0x2c), 0x10) == 6;
            if (allowed && !respawn(get(app, 0x2c)))
                call(0x429e10, app, {0x8005, 0x3fb});
            return 1;
        }
        if (command == 0x8006) {
            uint32_t type = get(app, 0x9c) ? 12 : 5;
            if (type == 5)
                set(get(app, 0x2c), 0x38, 1);
            if (!transition(app, type, 1, type == 12))
                call(0x429e10, app, {0x8005, type == 12 ? 0x6adu : 0x3fcu});
            return 1;
        }
        return 0;
    }
};
} // namespace
extern "C" uint32_t claw_player_death_command(uint32_t a, uint32_t c, ClawPlayerDeathCommandGlobals *g,
                                              ClawSceneActorHost h, uint32_t *f) {
    *f = 0;
    try {
        return Runtime{h, f, g}.command(a, c);
    } catch (Failure &) {
        return 0;
    }
}
extern "C" uint32_t claw_player_respawn(uint32_t a, ClawPlayerDeathCommandGlobals *g, ClawSceneActorHost h,
                                        uint32_t *f) {
    *f = 0;
    try {
        return Runtime{h, f, g}.respawn(a);
    } catch (Failure &) {
        return 0;
    }
}
extern "C" uint32_t claw_player_game_over_transition(uint32_t a, uint32_t t, uint32_t p, uint32_t r,
                                                     ClawPlayerDeathCommandGlobals *g, ClawSceneActorHost h,
                                                     uint32_t *f) {
    *f = 0;
    try {
        return Runtime{h, f, g}.transition(a, t, p, r);
    } catch (Failure &) {
        return 0;
    }
}
extern "C" void claw_player_death_cleanup(uint32_t a, ClawSceneActorHost h, uint32_t *f) {
    *f = 0;
    try {
        Runtime{h, f, nullptr}.cleanup(a);
    } catch (Failure &) {
    }
}
extern "C" void claw_player_death_cleanup_actor(uint32_t a, ClawSceneActorHost h, uint32_t *f) {
    *f = 0;
    try {
        Runtime{h, f, nullptr}.cleanupActor(a);
    } catch (Failure &) {
    }
}
extern "C" void claw_player_death_clear_history(uint32_t a, ClawSceneActorHost h, uint32_t *f) {
    *f = 0;
    try {
        Runtime{h, f, nullptr}.clear(a);
    } catch (Failure &) {
    }
}

extern "C" uint32_t claw_application_state_transition(uint32_t a, uint32_t t, uint32_t p, uint32_t r, uint32_t extra,
                                                      ClawPlayerDeathCommandGlobals *g, ClawSceneActorHost h,
                                                      ClawApplicationStateConstructor ctor, void *user, uint32_t *f) {
    if (!f)
        return 0;
    *f = 0;
    try {
        return Runtime{h, f, g}.transition(a, t, p, r, extra, ctor, user);
    } catch (Failure &) {
        return 0;
    }
}
