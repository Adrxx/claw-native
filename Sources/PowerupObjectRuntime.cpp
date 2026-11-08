#include "PowerupObjectRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
int32_t si(uint32_t x) {
    int32_t v;
    std::memcpy(&v, &x, 4);
    return v;
}
struct Run {
    ClawPowerupObjectContext *c;
    ClawPowerupObjectDependency dependency;
    void *user;
    uint32_t visits = 0;
    void fail(uint32_t f = 1) {
        if (!c->fault)
            c->fault = f;
    }
    uint32_t *span(uint32_t t, uint32_t n) {
        if (c->fault)
            return nullptr;
        auto *p = c->scene.lookup ? c->scene.lookup(c->scene.context, t, n) : nullptr;
        if (!p)
            fail();
        return p;
    }
    uint32_t read(uint32_t t) {
        auto *p = span(t, 1);
        return p ? *p : 0;
    }
    void put(uint32_t t, uint32_t x) {
        if (auto *p = span(t, 1))
            *p = x;
    }
    uint32_t manager() {
        if (c->powerups && c->powerups->globals)
            return c->powerups->globals->managerToken;
        if (c->items)
            return c->items->managerToken;
        fail();
        return 0;
    }
    bool next() {
        if (++visits > 1000000)
            fail(2);
        return !c->fault;
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}, const char *name = nullptr) {
        if (c->fault)
            return 0;
        if (!dependency || a.size() > 6) {
            fail();
            return 0;
        }
        ClawPowerupObjectCall e{};
        e.function = f;
        e.receiver = t;
        e.argumentCount = uint32_t(a.size());
        e.name = name;
        std::copy(a.begin(), a.end(), e.arguments);
        return dependency(c, &e, user);
    }
    uint32_t invoke(uint32_t, uint32_t, std::initializer_list<uint32_t>, const char * = nullptr);
    uint32_t mode() {
        uint32_t controller = read(manager() + 44);
        return invoke(read(read(controller) + 16), controller, {});
    }
};
uint32_t entry(Run &, uint32_t, uint32_t, const uint32_t *);
uint32_t itemDependency(ClawItemPickupContext *, const ClawItemPickupCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    if (e->argumentCount > 6) {
        r.fail(2);
        return 0;
    }
    ClawPowerupObjectCall call{};
    call.function = e->function;
    call.receiver = e->receiver;
    call.argumentCount = e->argumentCount;
    call.name = e->name;
    std::copy_n(e->arguments, e->argumentCount, call.arguments);
    if (!r.dependency) {
        r.fail();
        return 0;
    }
    return r.dependency(r.c, &call, r.user);
}
uint32_t powerDependency(ClawPlayerPowerupRuntimeContext *, const ClawPlayerPowerupCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    ClawPowerupObjectCall call{};
    call.function = e->function;
    call.receiver = e->receiver;
    call.argumentCount = e->argumentCount;
    call.name = e->name;
    std::copy_n(e->arguments, e->argumentCount, call.arguments);
    if (!r.dependency) {
        r.fail();
        return 0;
    }
    return r.dependency(r.c, &call, r.user);
}
uint32_t lootDependency(ClawWorldLootGlobals *, ClawWorldLootContext *, const ClawWorldLootCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    if (e->argumentCount > 6) {
        r.fail(2);
        return 0;
    }
    ClawPowerupObjectCall call{};
    call.function = e->function;
    call.receiver = e->receiver;
    call.argumentCount = e->argumentCount;
    call.name = e->name;
    std::copy_n(e->arguments, e->argumentCount, call.arguments);
    if (!r.dependency) {
        r.fail();
        return 0;
    }
    return r.dependency(r.c, &call, r.user);
}
uint32_t sceneCall(void *u, ClawSceneActorCall e) {
    auto &r = *static_cast<Run *>(u);
    switch (e.argumentCount) {
    case 0:
        return r.invoke(e.function, e.receiver, {});
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
uint32_t *sceneLookup(void *u, uint32_t t, uint32_t n) {
    return static_cast<Run *>(u)->span(t, n);
}
uint32_t sceneAllocate(void *u, uint32_t n) {
    auto &r = *static_cast<Run *>(u);
    if (!r.c->scene.allocate) {
        r.fail();
        return 0;
    }
    return r.c->scene.allocate(r.c->scene.context, n);
}
void sceneFree(void *u, uint32_t t) {
    auto &r = *static_cast<Run *>(u);
    if (!r.c->scene.free) {
        r.fail();
        return;
    }
    r.c->scene.free(r.c->scene.context, t);
}
uint32_t sceneClock(void *u) {
    auto &r = *static_cast<Run *>(u);
    if (!r.c->scene.readClock) {
        r.fail();
        return 0;
    }
    return r.c->scene.readClock(r.c->scene.context);
}
ClawSceneActorHost host(Run &r) {
    return {&r, sceneLookup, sceneAllocate, sceneFree, sceneCall, sceneClock};
}
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a, const char *name) {
    if (c->fault)
        return 0;
    uint32_t args[6]{};
    std::copy(a.begin(), a.end(), args);
    if (f == 0x40af90 || f == 0x417050 || f == 0x4170b0 || f == 0x436860)
        return entry(*this, f, t, args);
    if (f == 0x41f990 || f == 0x41fc00 || f == 0x41fc30) {
        if (!c->powerups) {
            fail();
            return 0;
        }
        c->powerups->scene = c->scene;
        c->powerups->fault = 0;
        uint32_t result = 0;
        if (!claw_player_powerup_entry(f, t, args, uint32_t(a.size()), c->powerups, powerDependency, this, &result) ||
            c->powerups->fault)
            fail(c->powerups->fault ? c->powerups->fault : 2);
        return result;
    }
    if (f == 0x41d6f0 || f == 0x473ae0 || f == 0x41f850 || f == 0x405f80) {
        if (!c->items) {
            fail();
            return 0;
        }
        c->items->scene = c->scene;
        c->items->fault = 0;
        uint32_t result = 0;
        if (!claw_item_pickup_entry(f, t, args, uint32_t(a.size()), c->items, itemDependency, this, &result) ||
            c->items->fault)
            fail(c->items->fault ? c->items->fault : 2);
        return result;
    }
    if (f == 0x4719e0) {
        if (!c->loot) {
            fail();
            return 0;
        }
        ClawWorldLootContext x{c->scene, c->composeCreation, 0};
        uint32_t result = claw_world_loot_initialize(args[0], c->loot, &x, lootDependency, this);
        if (x.fault)
            fail(x.fault);
        return result;
    }
    if ((f == 0x4c79e0 || f == 0x4c8220 || f == 0x4c82a0) && c->composeAnimation) {
        if (!c->animation) {
            fail();
            return 0;
        }
        uint32_t result = 0, fault = 0;
        if (!claw_actor_animation_entry(f, t, args[0], args[1], c->animation, host(*this), &fault, &result) || fault)
            fail(fault ? fault : 2);
        return result;
    }
    return call(f, t, a, name);
}
uint32_t imageLookup(Run &r, uint32_t actor, uint32_t name, const char *hint) {
    uint32_t registry = r.read(r.read(actor + 12) + 16) + 16;
    return r.invoke(0x4f6286, registry, {name}, hint);
}
void rect(Run &r, uint32_t actor) {
    uint32_t image = r.read(actor + 0x174);
    if (image) {
        r.put(actor + 0x138, r.read(image + 32) - r.read(image + 24));
        r.put(actor + 0x13c, r.read(image + 36) - r.read(image + 28));
        r.put(actor + 0x140, r.read(image + 32) - 1 + r.read(image + 24));
        r.put(actor + 0x144, r.read(image + 36) - 1 + r.read(image + 28));
    }
    r.put(actor + 0x138, r.read(actor + 0x138) - 6);
    r.put(actor + 0x13c, r.read(actor + 0x13c) - 10);
    r.put(actor + 0x140, r.read(actor + 0x140) + 6);
    r.put(actor + 0x144, r.read(actor + 0x144) + 2);
}
void loot(Run &r, uint32_t actor) {
    if (!r.c->loot) {
        r.fail();
        return;
    }
    auto &g = *r.c->loot;
    if (!g.words[340])
        r.invoke(0x4719e0, 0, {r.read(actor + 12)});
    uint32_t index = 0;
    for (; si(index) < si(g.itemCount) && r.next(); ++index) {
        if (index >= 66) {
            r.fail(2);
            return;
        }
        if (g.words[index] == r.read(actor + 0x170))
            break;
    }
    uint32_t logic = r.read(actor + 0x6c);
    if (si(index) < si(g.itemCount)) {
        r.put(actor + 4, index ? index : 33);
        r.put(actor + 0xfc, g.words[66 + index]);
        r.put(logic + 0x168, g.words[274 + index]);
        if (r.read(actor + 0xd0) == 1)
            r.put(actor + 0xd0, g.words[132 + index]);
    } else {
        r.put(actor + 4, 0);
        r.put(actor + 0xfc, 100);
        r.put(logic + 0x168, 0);
    }
}
void animate(Run &r, uint32_t actor) {
    if (!r.c->animation) {
        r.fail();
        return;
    }
    r.invoke(0x4c82a0, actor + 0x188, {r.c->animation->animationDelta});
}
uint32_t glitter(Run &r, uint32_t actor) {
    uint32_t container = r.read(r.read(actor + 12) + 8), x = r.read(actor + 76), y = r.read(actor + 80),
             z = r.read(actor + 100) + 1;
    if (r.c->composeCreation) {
        uint32_t fault = 0,
                 token = claw_scene_actor_create_named(container, {1, x, y, z, 0, 0x40000}, 0x522950, host(r), &fault);
        if (fault)
            r.fail(fault);
        return token;
    }
    return r.invoke(0x4c8da0, container, {1, x, y, z, 0x522950, 0x40000}, "PowerupGlitter");
}
uint32_t callback(Run &r, uint32_t actor, bool curse) {
    uint32_t logic = r.read(actor + 0x6c), mode = r.read(logic + 28);
    if (!mode) {
        r.put(logic + 0x168, 0);
        if (curse) {
            r.put(logic + 0x16c, 0);
            if (r.mode() != 4 || !r.c->curseEnabled || r.mode() != 4) {
                r.put(actor + 8, r.read(actor + 8) | 0x10000);
                return 0;
            }
            r.put(logic + 0x16c, r.read(r.read(r.manager() + 44) + 0xbd4));
        }
        r.put(actor + 200, 0);
        if (!r.read(actor + 100)) {
            r.put(actor + 100, 1000);
            r.put(actor + 8, r.read(actor + 8) | 0x20000);
        }
        if (!r.read(actor + 400)) {
            uint32_t image = r.read(actor + 0x170), coins = imageLookup(r, actor, 0x5279b8, "GAME_TREASURE_COINS");
            r.invoke(0x4c79e0, actor, {image == coins ? 0x5240d8u : 0x52a198u, 0});
        }
        r.put(actor + 8, r.read(actor + 8) | 0x80000);
        r.put(actor + 0xd0, 0x100);
        rect(r, actor);
        loot(r, actor);
        if (!curse && r.mode() == 4) {
            uint32_t image = r.read(actor + 0x170), life = imageLookup(r, actor, 0x52a1ec, "GAME_POWERUPS_EXTRALIFE");
            if (image == life) {
                r.put(actor + 8, r.read(actor + 8) | 0x10000);
                return 1;
            }
        }
        uint32_t effect = 0;
        if (r.read(logic + 16) != 0x470100 && r.read(r.manager() + 0x124)) {
            bool allowed = true;
            if (!curse) {
                uint32_t image = r.read(actor + 0x170);
                allowed = image != imageLookup(r, actor, 0x52a07c, "GAME_WARP");
            }
            if (allowed)
                effect = glitter(r, actor);
        }
        if (effect)
            r.put(actor + 200, effect);
        r.put(logic + 28, 5);
        return 1;
    }
    if (mode == 5) {
        animate(r, actor);
        if (curse) {
            uint32_t map = r.read(logic + 0x16c);
            if (map) {
                uint32_t args[2] = {r.read(actor + 76), r.read(actor + 80)};
                if (entry(r, 0x436860, map, args))
                    r.put(actor + 8, r.read(actor + 8) | 0x10000);
            }
        } else if (r.read(actor + 0x164) & 0x200)
            r.put(logic + 28, 9000);
    } else if (mode == 29) {
        uint32_t effect = r.read(actor + 200);
        if (effect)
            r.put(effect + 8, r.read(effect + 8) | 0x10000);
    } else if (!curse && mode == 9000) {
        r.put(actor + 8, r.read(actor + 8) | 0x21);
        uint32_t effect = r.read(actor + 200);
        if (effect) {
            r.put(effect + 8, r.read(effect + 8) | 0x10000);
            r.put(actor + 200, 0);
        }
        uint32_t plane = r.read(r.read(r.read(actor + 12) + 0x24) + 0x5c), x = r.read(plane + 0x84),
                 y = r.read(plane + 0x88);
        r.put(logic + 0x130, 400);
        r.put(logic + 100, ((x + 300) * 1000 - r.read(actor + 76) * 1000) / 400);
        uint32_t py = r.read(actor + 80);
        r.put(logic + 28, 9001);
        r.put(logic + 0x68, (py * 1000 - (y - 200) * 1000) / 400);
    } else if (!curse && mode == 9001) {
        if (!r.c->items) {
            r.fail();
            return 0;
        }
        uint32_t remaining = r.read(logic + 0x130), delta = r.c->items->stageDelta;
        r.put(logic + 0x130, delta < remaining ? remaining - delta : 0);
        if (!r.read(logic + 0x130))
            r.put(actor + 8, r.read(actor + 8) | 0x10000);
        uint32_t vx = r.read(logic + 100), vy = r.read(logic + 0x68);
        if (vx)
            r.put(actor + 76, r.read(actor + 76) + (delta * vx) / 1000);
        if (vy)
            r.put(actor + 80, r.read(actor + 80) - (delta * vy) / 1000);
        animate(r, actor);
    }
    return 1;
}
struct Cleanup {
    Run *r;
    ClawPlayerLocomotion *s;
    uint32_t actor, logic, privateToken;
};
void push(Cleanup &b) {
    auto *a = b.r->span(b.actor, 128), *p = b.r->span(b.privateToken, 78);
    if (a && p) {
        std::copy_n(b.s->actor, 128, a);
        std::copy_n(b.s->privateWords, 78, p);
        b.r->put(b.r->c->inputToken + 12, b.s->inputLatched);
    }
}
void pull(Cleanup &b) {
    auto *a = b.r->span(b.actor, 128), *p = b.r->span(b.privateToken, 78);
    if (a && p) {
        std::copy_n(a, 128, b.s->actor);
        std::copy_n(p, 78, b.s->privateWords);
        b.s->inputLatched = b.r->read(b.r->c->inputToken + 12);
    }
}
uint32_t cleanupDependency(ClawPlayerLocomotion *, uint32_t f, uint32_t a, uint32_t, uint32_t, void *u) {
    auto &b = *static_cast<Cleanup *>(u);
    push(b);
    uint32_t result = 0;
    if (f == 0x4c8220)
        result = b.r->invoke(f, b.actor + 0x188, {a});
    else
        b.r->fail(2);
    pull(b);
    return result;
}
void cleanup(Run &r, uint32_t actor, uint32_t logic, uint32_t priv) {
    if (r.read(priv + 300)) {
        r.invoke(0x41c4e0, 0, {actor, logic, priv});
        return;
    }
    auto *a = r.span(actor, 128), *p = r.span(priv, 78);
    if (!a || !p)
        return;
    ClawPlayerLocomotion s{};
    std::copy_n(a, 128, s.actor);
    std::copy_n(p, 78, s.privateWords);
    s.inputLatched = r.read(r.c->inputToken + 12);
    Cleanup b{&r, &s, actor, logic, priv};
    claw_player_cleanup_move(&s, cleanupDependency, &b);
    push(b);
}
void post(Run &r, uint32_t command) {
    uint32_t window = r.read(r.read(r.manager() + 4) + 4);
    r.invoke(0x546d50, 0, {window, 0x111, command, 0});
}
uint32_t selector(Run &r, const uint32_t *a) {
    uint32_t actor = a[0], logic = a[1], priv = a[2], item = a[3];
    if (!item)
        return 0;
    uint32_t type = r.read(item + 0xfc);
    if (type == 0x26ad) {
        post(r, 0x800e);
        r.put(logic + 36, 2);
        uint32_t sound = r.invoke(0x4f6286, r.read(r.read(actor + 12) + 40) + 16, {0x524d1c}, "GAME_MAPPIECE");
        if (sound) {
            if (!r.c->items) {
                r.fail();
                return 0;
            }
            if (r.c->items->audioEnabled)
                r.invoke(0x4b45f0, r.read(sound + 16), {r.c->items->masterVolume, 0, 0, 0});
            r.invoke(0x4b8960, 0, {r.read(r.read(sound + 16) + 40)});
        }
        uint32_t config = r.read(r.manager() + 44), mode = r.invoke(r.read(r.read(config) + 16), config, {});
        if (mode == 4 && r.read(config + 0xbcc) == 1)
            r.put(actor + 0xf8, r.read(actor + 0xf8) + 0x13ba);
        r.put(item + 8, r.read(item + 8) | 0x10000);
        return 0;
    }
    if (type == 0x26ae) {
        uint32_t x = r.read(item + 0x148), y = r.read(item + 0x14c);
        if (r.read(logic + 28) == 4) {
            uint32_t status = r.read(priv + 60);
            if (status == 8 || status == 9 || status == 10 || status == 18) {
                uint32_t sequence = r.invoke(0x4f6286, r.read(r.read(actor + 12) + 44) + 16, {0x5246dc}, "CLAW_FALL");
                r.put(priv + 0x124, sequence);
            } else {
                cleanup(r, actor, logic, priv);
                r.invoke(0x4c79e0, actor, {0x5246dc, 0});
            }
            r.put(logic + 28, 25);
            r.put(actor + 0xcc, 4);
            r.put(actor + 0x148, 0);
            r.put(actor + 0x14c, 0);
            r.put(actor + 8, r.read(actor + 8) & ~0x10u);
            uint32_t h[2] = {actor, priv};
            entry(r, 0x417050, 0, h);
            entry(r, 0x4170b0, 0, h);
            r.put(priv + 64, 0);
            if (!r.c->physics) {
                r.fail();
                return 0;
            }
            r.c->physics->velocity[1] = 0;
            r.c->physics->acceleration[1] = 2250;
        }
        if (si(x) > 0 && si(y) > 0) {
            r.c->warpX = x;
            r.c->warpY = y;
            post(r, 0x805c);
        }
        if (!r.read(item + 0x108))
            r.put(item + 8, r.read(item + 8) | 0x10000);
        return 0;
    }
    if (type == 0x26af) {
        if (r.read(priv + 0x11c) && r.read(priv + 0x134) == item)
            return 0;
        uint32_t motion = r.read(actor + 0xcc);
        if (motion != 3 && motion != 4)
            return 0;
        uint32_t object = r.read(r.read(item + 0x6c) + 24), y = r.invoke(0x403ac0, object, {}),
                 distance = r.read(actor + 80) - y - 16, sign = si(distance) < 0 ? 0xffffffff : 0;
        distance = (distance ^ sign) - sign;
        if (si(distance) > 47)
            return 0;
        cleanup(r, actor, logic, priv);
        r.put(logic + 28, 5007);
        r.invoke(0x4c79e0, actor, {0x524d2c, 0});
        r.put(actor + 0xcc, 8);
        r.put(priv + 0x134, item);
        r.put(priv + 0xf8, 0);
        uint32_t x = r.invoke(0x403ab0, r.read(r.read(item + 0x6c) + 24), {});
        r.put(actor + 76, x + (r.read(priv) ? 8 : 0u - 8));
        y = r.invoke(0x403ac0, r.read(r.read(r.read(priv + 0x134) + 0x6c) + 24), {});
        r.put(actor + 80, y + 20);
        if (!r.c->physics) {
            r.fail();
            return 0;
        }
        for (double &v : r.c->physics->remainder)
            v = 0;
        return 0;
    }
    if (type == 0x26b0) {
        if (!r.c->items) {
            r.fail();
            return 0;
        }
        auto *x = r.c->items;
        x->scene = r.c->scene;
        x->fault = 0;
        uint32_t result = 0;
        if (!claw_item_pickup_entry(0x41ee60, 0, a, 4, x, itemDependency, &r, &result) || x->fault)
            r.fail(x->fault ? x->fault : 2);
        return 0;
    }
    if (type >= 0x26b1 && type <= 0x26b6) {
        uint32_t controller = r.read(r.manager() + 44);
        if (controller && r.invoke(r.read(r.read(controller) + 0x58), controller, {item}))
            r.invoke(0x41d6f0, 0, {item});
        r.put(item + 8, r.read(item + 8) | 0x10000);
        return 0;
    }
    if (type == 0x26b7 || type == 0x26bd || type == 0x26b8 || type == 0x26b9 || type == 0x26ba) {
        if (!r.c->powerups || !r.c->powerups->globals) {
            r.fail();
            return 0;
        }
        uint32_t duration = r.read(item + 0x108);
        if (si(duration) <= 0)
            duration = 30000;
        bool persistent = type == 0x26b8 || type == 0x26b9 || type == 0x26ba;
        bool same = persistent && r.read(item + 0x104) && r.c->powerups->globals->powerup == type;
        if (!same) {
            r.invoke(0x41f990, 0, {actor, logic, priv, type, duration});
            r.invoke(0x41d6f0, 0, {item});
        }
        if (persistent && si(r.read(item + 0x104)) > 0) {
            r.c->powerups->globals->remaining = duration;
            return 0;
        }
        r.put(item + 8, r.read(item + 8) | 0x10000);
        return 0;
    }
    if (type == 0x26be) {
        if (si(r.read(priv + 124)) < 10) {
            r.put(priv + 124, r.read(priv + 124) + 1);
            r.invoke(0x41d6f0, 0, {item});
        }
        if (!r.invoke(0x473ae0, 0, {item}))
            r.put(item + 8, r.read(item + 8) | 0x10000);
    }
    return 0;
}
uint32_t entry(Run &r, uint32_t f, uint32_t t, const uint32_t *a) {
    if (f == 0x470430 || f == 0x470a20)
        return callback(r, a[0], f == 0x470a20);
    if (f == 0x41ee60)
        return selector(r, a);
    if (f == 0x40af90)
        return 3;
    if (f == 0x417050) {
        bool facing = r.read(a[1]) != 0;
        r.put(a[0] + 0x128, facing ? 0xffffffea : 0xfffffff1);
        r.put(a[0] + 0x12c, 0xffffffd3);
        r.put(a[0] + 0x130, facing ? 15 : 22);
        r.put(a[0] + 0x134, 52);
        return 0;
    }
    if (f == 0x4170b0) {
        r.put(a[0] + 0x118, 0xfffffff0);
        r.put(a[0] + 0x11c, 0xffffffcc);
        r.put(a[0] + 0x120, 16);
        r.put(a[0] + 0x124, 60);
        return 0;
    }
    if (f == 0x436860) {
        for (uint32_t node = r.read(t + 4); node && r.next();) {
            uint32_t data = r.read(node + 8);
            node = r.read(node);
            if (r.read(data) == a[0] && r.read(data + 4) == a[1])
                return data;
        }
        return 0;
    }
    r.fail(2);
    return 0;
}
} // namespace
extern "C" uint32_t claw_powerup_object_entry(uint32_t f, uint32_t t, ClawPowerupObjectArguments a,
                                              ClawPowerupObjectContext *c, ClawPowerupObjectDependency dependency,
                                              void *user, uint32_t *result) {
    uint32_t count = 0;
    switch (f) {
    case 0x470430:
    case 0x470a20:
    case 0x4170b0:
        count = 1;
        break;
    case 0x417050:
    case 0x436860:
        count = 2;
        break;
    case 0x41ee60:
        count = 4;
        break;
    case 0x40af90:
        break;
    default:
        return 0;
    }
    if (!c)
        return 0;
    if (a.count != count) {
        c->fault = 2;
        return 0;
    }
    Run r{c, dependency, user};
    uint32_t value = entry(r, f, t, a.words);
    if (result)
        *result = value;
    return c->fault ? 0 : 1;
}

namespace {
struct Hit {
    Run *r;
    ClawPlayerLocomotion *s;
    ClawPlayerDamageContext *d;
    uint32_t actor, logic, priv, item;
};
void pushHit(Hit &b) {
    auto *a = b.r->span(b.actor, 128), *p = b.r->span(b.priv, 78), *item = b.r->span(b.item, 128);
    if (a && p && item) {
        std::copy_n(b.s->actor, 128, a);
        std::copy_n(b.s->privateWords, 78, p);
        std::copy_n(b.d->attackerActor, 128, item);
        b.r->put(b.logic + 28, b.s->logicState);
        b.r->c->powerups->globals->powerup = b.s->powerup;
    }
}
void pullHit(Hit &b) {
    auto *a = b.r->span(b.actor, 128), *p = b.r->span(b.priv, 78), *item = b.r->span(b.item, 128);
    if (a && p && item) {
        std::copy_n(a, 128, b.s->actor);
        std::copy_n(p, 78, b.s->privateWords);
        std::copy_n(item, 128, b.d->attackerActor);
        b.s->logicState = b.r->read(b.logic + 28);
        b.s->powerup = b.r->c->powerups->globals->powerup;
    }
}
uint32_t hitDependency(ClawPlayerLocomotion *, uint32_t f, uint32_t a, uint32_t, uint32_t, void *u) {
    auto &b = *static_cast<Hit *>(u);
    pushHit(b);
    uint32_t result = 0;
    if (f == 0x41ee60) {
        uint32_t args[] = {b.actor, b.logic, b.priv, a};
        result = selector(*b.r, args);
    } else
        b.r->fail(2);
    pullHit(b);
    return result;
}
} // namespace
extern "C" uint32_t claw_powerup_object_award(uint32_t item, ClawPowerupObjectContext *c,
                                              ClawPowerupObjectDependency dependency, void *user, uint32_t *result) {
    if (!c || !c->items || !c->powerups || !c->powerups->globals)
        return 0;
    Run r{c, dependency, user};
    uint32_t actor = c->items->playerToken, logic = c->items->playerPrimaryToken, priv = c->items->playerPrivateToken;
    auto *a = r.span(actor, 128), *p = r.span(priv, 78), *i = r.span(item, 128);
    if (!a || !p || !i)
        return 0;
    if (i[0xd0 / 4] != 0x100 || a[0x74 / 4] != item) {
        r.fail(2);
        return 0;
    }
    ClawPlayerLocomotion s{};
    ClawPlayerDamageContext d{};
    ClawPlayerInputContext input{};
    std::copy_n(a, 128, s.actor);
    std::copy_n(p, 78, s.privateWords);
    std::copy_n(i, 128, d.attackerActor);
    s.logicState = r.read(logic + 28);
    s.powerup = c->powerups->globals->powerup;
    d.attackerToken = item;
    Hit h{&r, &s, &d, actor, logic, priv, item};
    uint32_t value = claw_player_hit(&s, &d, &input, hitDependency, &h);
    pushHit(h);
    if (result)
        *result = value;
    return c->fault ? 0 : 1;
}
