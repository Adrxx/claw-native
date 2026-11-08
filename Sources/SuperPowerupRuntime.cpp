#include "SuperPowerupRuntime.h"
#include <algorithm>
#include <initializer_list>
namespace {
struct Run {
    ClawSuperPowerupContext &c;
    ClawSuperPowerupDependency d;
    void *user;
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (c.fault)
            return nullptr;
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p)
            c.fault = 1;
        return p;
    }
    uint32_t read(uint32_t t) {
        auto *p = span(t);
        return p ? *p : 0;
    }
    void put(uint32_t t, uint32_t v) {
        if (auto *p = span(t))
            *p = v;
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> args = {}, const char *name = nullptr) {
        if (c.fault)
            return 0;
        if (!d) {
            c.fault = 1;
            return 0;
        }
        ClawSuperPowerupCall e{};
        e.function = f;
        e.receiver = t;
        e.argumentCount = uint32_t(args.size());
        std::copy(args.begin(), args.end(), e.arguments);
        e.name = name;
        return d(&c, &e, user);
    }
    uint32_t invoke(uint32_t, uint32_t, std::initializer_list<uint32_t> = {}, const char * = nullptr);
};
uint32_t bridgeLoot(ClawWorldLootGlobals *, ClawWorldLootContext *, const ClawWorldLootCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    ClawSuperPowerupCall c{};
    c.function = e->function;
    c.receiver = e->receiver;
    c.argumentCount = e->argumentCount;
    std::copy_n(e->arguments, e->argumentCount, c.arguments);
    c.name = e->name;
    if (!r.d) {
        r.c.fault = 1;
        return 0;
    }
    return r.d(&r.c, &c, r.user);
}
uint32_t bridgeItem(ClawItemPickupContext *, const ClawItemPickupCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    ClawSuperPowerupCall c{};
    c.function = e->function;
    c.receiver = e->receiver;
    c.argumentCount = e->argumentCount;
    std::copy_n(e->arguments, e->argumentCount, c.arguments);
    c.name = e->name;
    if (!r.d) {
        r.c.fault = 1;
        return 0;
    }
    return r.d(&r.c, &c, r.user);
}
uint32_t lookup(void *u, uint32_t t, uint32_t n, uint32_t **out) {
    auto &r = *static_cast<Run *>(u);
    *out = r.span(t, n);
    return *out != nullptr;
}
uint32_t *sceneLookup(void *u, uint32_t t, uint32_t n) {
    uint32_t *p = nullptr;
    lookup(u, t, n, &p);
    return p;
}
uint32_t sceneCall(void *u, ClawSceneActorCall e) {
    auto &r = *static_cast<Run *>(u);
    switch (e.argumentCount) {
    case 0:
        return r.invoke(e.function, e.receiver);
    case 1:
        return r.invoke(e.function, e.receiver, {e.arguments[0]});
    case 2:
        return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1]});
    case 3:
        return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2]});
    default:
        return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2], e.arguments[3]});
    }
}
uint32_t sceneAllocate(void *u, uint32_t n) {
    auto &r = *static_cast<Run *>(u);
    if (!r.c.scene.allocate) {
        r.c.fault = 1;
        return 0;
    }
    return r.c.scene.allocate(r.c.scene.context, n);
}
void sceneFree(void *u, uint32_t t) {
    auto &r = *static_cast<Run *>(u);
    if (!r.c.scene.free) {
        r.c.fault = 1;
        return;
    }
    r.c.scene.free(r.c.scene.context, t);
}
uint32_t sceneClock(void *u) {
    auto &r = *static_cast<Run *>(u);
    if (!r.c.scene.readClock) {
        r.c.fault = 1;
        return 0;
    }
    return r.c.scene.readClock(r.c.scene.context);
}
ClawSceneActorHost host(Run &r) {
    return {&r, sceneLookup, sceneAllocate, sceneFree, sceneCall, sceneClock};
}
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> args, const char *name) {
    if (c.fault)
        return 0;
    uint32_t words[8]{};
    std::copy(args.begin(), args.end(), words);
    uint32_t result = 0;
    if (f == 0x4719e0) {
        if (!c.items || !c.items->loot) {
            c.fault = 1;
            return 0;
        }
        ClawWorldLootContext x{c.scene, c.composeCreation, 0};
        result = claw_world_loot_initialize(words[0], c.items->loot, &x, bridgeLoot, this);
        if (x.fault)
            c.fault = x.fault;
        return result;
    }
    if ((f == 0x4c79e0 || f == 0x4c82a0) && c.composeAnimation) {
        if (!c.animation) {
            c.fault = 1;
            return 0;
        }
        uint32_t fault = 0;
        claw_actor_animation_entry(f, t, words[0], words[1], c.animation, host(*this), &fault, &result);
        if (fault)
            c.fault = fault;
        return result;
    }
    return call(f, t, args, name);
}
uint32_t callback(Run &r, uint32_t a) {
    uint32_t l = r.read(a + 108), state = r.read(l + 28);
    if (!state) {
        if (!r.c.items || !r.c.items->loot) {
            r.c.fault = 1;
            return 0;
        }
        r.put(l + 0x168, 0);
        if (!r.read(a + 400))
            r.invoke(0x4c79e0, a, {0x52a198, 0}, "GAME_POWERUP");
        uint32_t flags = r.read(a + 8) | 0x80000, image = r.read(a + 0x174);
        r.put(a + 8, flags);
        r.put(a + 0xd0, 0x200000);
        if (image) {
            r.put(a + 0x138, r.read(image + 32) - r.read(image + 24));
            r.put(a + 0x13c, r.read(image + 36) - r.read(image + 28));
            r.put(a + 0x140, r.read(image + 32) - 1 + r.read(image + 24));
            r.put(a + 0x144, r.read(image + 36) - 1 + r.read(image + 28));
        }
        if (!r.read(a + 100)) {
            r.put(a + 100, 1000);
            r.put(a + 8, flags | 0x20000);
        }
        auto &g = *r.c.items->loot;
        if (!g.words[340])
            r.invoke(0x4719e0, 0, {r.read(a + 12)});
        uint32_t n = 0;
        while (int32_t(n) < int32_t(g.itemCount)) {
            if (n >= 66) {
                r.c.fault = 2;
                return 0;
            }
            if (g.words[n] == r.read(a + 0x170))
                break;
            ++n;
        }
        if (int32_t(n) < int32_t(g.itemCount)) {
            r.put(a + 4, n ? n : 33);
            r.put(a + 0xfc, g.words[66 + n]);
            r.put(r.read(a + 108) + 0x168, g.words[274 + n]);
            if (r.read(a + 0xd0) == 1)
                r.put(a + 0xd0, g.words[132 + n]);
        } else {
            r.put(a + 4, 0);
            r.put(a + 0xfc, 100);
            r.put(r.read(a + 108) + 0x168, 0);
        }
        uint32_t effect = 0;
        if (r.read(r.c.items->managerToken + 0x124)) {
            uint32_t container = r.read(r.read(a + 12) + 8);
            if (r.c.composeCreation) {
                uint32_t fault = 0;
                effect = claw_scene_actor_create_named(
                    container, {1, r.read(a + 76), r.read(a + 80), r.read(a + 100) + 1, 0, 0x40000}, 0x522950, host(r),
                    &fault);
                if (fault)
                    r.c.fault = fault;
            } else
                effect = r.invoke(0x4c8da0, container,
                                  {1, r.read(a + 76), r.read(a + 80), r.read(a + 100) + 1, 0x522950, 0x40000},
                                  "PowerupGlitter");
        }
        r.put(a + 200, effect);
        r.put(l + 28, 5);
    } else if (state == 5) {
        if (!r.c.animation) {
            r.c.fault = 1;
            return 0;
        }
        r.invoke(0x4c82a0, a + 392, {r.c.animation->animationDelta});
    } else if (state == 29) {
        uint32_t effect = r.read(a + 200);
        if (effect)
            r.put(effect + 8, r.read(effect + 8) | 0x10000);
    }
    return 1;
}
} // namespace
extern "C" uint32_t claw_super_powerup_entry(uint32_t actor, ClawSuperPowerupContext *c, ClawSuperPowerupDependency d,
                                             void *u, uint32_t *out) {
    if (!c)
        return 0;
    Run r{*c, d, u};
    uint32_t value = callback(r, actor);
    if (out)
        *out = value;
    return !c->fault;
}
extern "C" uint32_t claw_super_powerup_award(uint32_t item, ClawSuperPowerupContext *c, ClawSuperPowerupDependency d,
                                             void *u) {
    if (!c || !c->items)
        return 0;
    Run r{*c, d, u};
    if (r.read(item + 0xd0) != 0x200000) {
        c->fault = 2;
        return 0;
    }
    c->items->scene = c->scene;
    c->items->fault = 0;
    uint32_t ok = claw_item_pickup_award(item, c->items, bridgeItem, &r);
    if (c->items->fault)
        c->fault = c->items->fault;
    return ok && !c->fault;
}
