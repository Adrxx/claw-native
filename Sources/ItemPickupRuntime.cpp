#include "ItemPickupRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawItemPickupContext *x;
    ClawItemPickupDependency dependency;
    void *user;
};
uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    auto *p = r.x->scene.lookup ? r.x->scene.lookup(r.x->scene.context, t, n) : nullptr;
    if (!p)
        r.x->fault = 1;
    return p;
}
uint32_t read(Run &r, uint32_t t) {
    auto *p = span(r, t, 1);
    return p ? *p : 0;
}
void write(Run &r, uint32_t t, uint32_t v) {
    auto *p = span(r, t, 1);
    if (p)
        *p = v;
}
void add(Run &r, uint32_t t, uint32_t v) {
    write(r, t, read(r, t) + v);
}
uint32_t call(Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {},
              const char *name = nullptr) {
    if (!r.dependency) {
        r.x->fault = 1;
        return 0;
    }
    ClawItemPickupCall c{};
    c.function = f;
    c.receiver = receiver;
    c.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), c.arguments);
    c.name = name;
    return r.dependency(r.x, &c, r.user);
}
uint32_t execute(Run &, uint32_t, uint32_t, const uint32_t *, uint32_t, uint32_t *);
void sequence(Run &r, uint32_t actor, uint32_t name) {
    call(r, 0x4c79e0, actor, {name, 0});
}
void animate(Run &r, uint32_t actor) {
    call(r, 0x4c82a0, actor + 0x188, {r.x->animationDelta});
}
uint32_t lookupImage(Run &r, uint32_t actor, uint32_t name) {
    uint32_t scene = read(r, actor + 0xc), manager = read(r, scene + 0x10);
    return call(r, 0x4f6286, manager + 0x10, {name});
}
void rect(Run &r, uint32_t actor) {
    uint32_t image = read(r, actor + 0x174);
    if (!image)
        return;
    auto *h = span(r, image, 10);
    if (!h)
        return;
    write(r, actor + 0x138, h[8] - h[6]);
    write(r, actor + 0x13c, h[9] - h[7]);
    write(r, actor + 0x140, h[8] - 1 + h[6]);
    write(r, actor + 0x144, h[9] - 1 + h[7]);
}
void depth(Run &r, uint32_t actor) {
    if (!read(r, actor + 0x64)) {
        write(r, actor + 0x64, 1000);
        write(r, actor + 8, read(r, actor + 8) | 0x20000);
    }
}
void bindLoot(Run &r, uint32_t actor) {
    auto *g = r.x->loot;
    if (!g) {
        r.x->fault = 1;
        return;
    }
    if (!g->words[340])
        call(r, 0x4719e0, 0, {read(r, actor + 0xc)});
    uint32_t n = 0;
    for (; int32_t(n) < int32_t(g->itemCount); ++n) {
        if (n >= 66) {
            r.x->fault = 1;
            return;
        }
        if (g->words[n] == read(r, actor + 0x170))
            break;
    }
    uint32_t logic = read(r, actor + 0x6c);
    if (int32_t(n) < int32_t(g->itemCount)) {
        write(r, actor + 4, n ? n : 33);
        write(r, actor + 0xfc, g->words[66 + n]);
        write(r, logic + 0x168, g->words[274 + n]);
        if (read(r, actor + 0xd0) == 1)
            write(r, actor + 0xd0, g->words[132 + n]);
    } else {
        write(r, actor + 4, 0);
        write(r, actor + 0xfc, 100);
        write(r, logic + 0x168, 0);
    }
}
void glitter(Run &r, uint32_t actor, uint32_t logic, bool treasure) {
    uint32_t token = 0;
    if ((!treasure || read(r, logic + 0x10) != 0x470100) && read(r, r.x->managerToken + 0x124)) {
        uint32_t container = read(r, read(r, actor + 0xc) + 8), x = read(r, actor + 0x4c), y = read(r, actor + 0x50),
                 z = read(r, actor + 0x64) + 1;
        if (r.x->composeCreation) {
            ClawSceneActorCreate args{1, x, y, z, 0, 0x40000};
            token = claw_scene_actor_create_named(container, args, 0x522950, r.x->scene, &r.x->fault);
        } else
            token = call(r, 0x4c8da0, container, {1, x, y, z, 0x522950, 0x40000});
    }
    if (token || !treasure)
        write(r, actor + 0xc8, token);
}
void removeGlitter(Run &r, uint32_t actor, bool clear) {
    uint32_t token = read(r, actor + 0xc8);
    if (token) {
        write(r, token + 8, read(r, token + 8) | 0x10000);
        if (clear)
            write(r, actor + 0xc8, 0);
    }
}
uint32_t pickupCallback(Run &r, uint32_t fn, uint32_t actor) {
    uint32_t logic = read(r, actor + 0x6c), mode = read(r, logic + 0x1c);
    bool treasure = fn == 0x46fd10 || fn == 0x470100, magic = fn == 0x470f00, ammo = fn == 0x471100;
    if (mode == 0) {
        write(r, logic + 0x168, 0);
        if (treasure)
            write(r, actor + 0xc8, 0);
        if (treasure || magic)
            depth(r, actor);
        if (!read(r, actor + 0x190)) {
            if (treasure) {
                uint32_t oldImage = read(r, actor + 0x170);
                uint32_t coins = lookupImage(r, actor, 0x5279b8);
                sequence(r, actor, oldImage == coins ? 0x5240d8 : 0x52a198);
            } else
                sequence(r, actor, 0x52a198);
        }
        if (!treasure && !magic)
            depth(r, actor);
        if (!ammo)
            write(r, actor + 8, read(r, actor + 8) | 0x80000);
        write(r, actor + 0xd0, treasure ? 0x40000 : magic ? 0x100000 : ammo ? 0x800000 : 0x10000);
        rect(r, actor);
        if (treasure) {
            add(r, actor + 0x138, 0u - 6);
            add(r, actor + 0x13c, 0u - 10);
            add(r, actor + 0x140, 6);
            add(r, actor + 0x144, 2);
        }
        if (ammo)
            write(r, actor + 8, read(r, actor + 8) | 0x80000);
        bindLoot(r, actor);
        if (ammo) {
            uint32_t oldImage = read(r, actor + 0x170);
            if (oldImage == lookupImage(r, actor, 0x5235d0))
                write(r, actor + 0xd0, 0x100);
        }
        glitter(r, actor, logic, treasure);
        write(r, logic + 0x1c, 5);
    } else if (mode == 5) {
        animate(r, actor);
        if (treasure && (read(r, actor + 0x164) & 0x200))
            write(r, logic + 0x1c, 9000);
    } else if (mode == 29)
        removeGlitter(r, actor, treasure);
    else if (treasure && mode == 9000) {
        write(r, actor + 8, read(r, actor + 8) | 0x21);
        removeGlitter(r, actor, true);
        uint32_t plane = read(r, read(r, read(r, actor + 0xc) + 0x24) + 0x5c);
        uint32_t cx = read(r, plane + 0x84), cy = read(r, plane + 0x88);
        write(r, logic + 0x130, 400);
        write(r, logic + 0x64, (read(r, actor + 0x4c) * 1000 - (cx - 300) * 1000) / 400);
        uint32_t y = read(r, actor + 0x50);
        write(r, logic + 0x1c, 9001);
        write(r, logic + 0x68, (y * 1000 - (cy - 280) * 1000) / 400);
        call(r, 0x4737c0, 0, {actor});
    } else if (treasure && mode == 9001) {
        uint32_t timer = read(r, logic + 0x130), delta = r.x->stageDelta;
        write(r, logic + 0x130, delta < timer ? timer - delta : 0);
        if (!read(r, logic + 0x130))
            write(r, actor + 8, read(r, actor + 8) | 0x10000);
        uint32_t vx = read(r, logic + 0x64);
        if (vx)
            write(r, actor + 0x4c, read(r, actor + 0x4c) - (r.x->stageDelta * vx) / 1000);
        uint32_t vy = read(r, logic + 0x68);
        if (vy)
            write(r, actor + 0x50, read(r, actor + 0x50) - (r.x->stageDelta * vy) / 1000);
        animate(r, actor);
    }
    return 1;
}
uint32_t execute(Run &r, uint32_t fn, uint32_t receiver, const uint32_t *args, uint32_t n, uint32_t *result) {
    uint32_t value = 0;
    if (fn == 0x46fd10 || fn == 0x470100 || fn == 0x470d00 || fn == 0x470f00 || fn == 0x471100) {
        if (!n)
            return 0;
        value = pickupCallback(r, fn, args[0]);
    } else if (fn == 0x41d6f0) {
        if (!n)
            return 0;
        uint32_t actor = args[0], token = read(r, read(r, actor + 0x6c) + 0x168);
        if (r.x->lastSoundTick != r.x->tick || r.x->lastSoundToken != token) {
            r.x->lastSoundTick = r.x->tick;
            r.x->lastSoundToken = token;
            if (token && r.x->audioEnabled)
                call(r, 0x4b45f0, read(r, token + 0x10), {r.x->masterVolume, 0, 0, 0});
        }
    } else if (fn == 0x41f850) {
        if (n < 2)
            return 0;
        int index = -1;
        uint32_t id = read(r, args[0] + 4);
        if (id == 33)
            index = 0;
        else if (id == 1)
            index = 1;
        else if (id >= 2 && id <= 5)
            index = 2;
        else if (id >= 41 && id <= 44)
            index = 3;
        else if (id >= 7 && id <= 10)
            index = 4;
        else if (id >= 11 && id <= 14)
            index = 5;
        else if (id >= 15 && id <= 18)
            index = 6;
        else if (id >= 45 && id <= 48)
            index = 7;
        else if (id >= 49 && id <= 52)
            index = 8;
        if (index >= 0) {
            add(r, args[1] + 0x88 + uint32_t(index) * 4, 1);
            add(r, args[1] + 0xb0 + uint32_t(index) * 4, 1);
        }
    } else if (fn == 0x473ae0) {
        if (!n)
            return 0;
        write(r, args[0] + 0x164, read(r, args[0] + 0x164) | 0x200);
        write(r, args[0] + 8, read(r, args[0] + 8) | 1);
        value = 1;
    } else if (fn == 0x41ee60) {
        if (n < 4 || !args[3] || read(r, args[3] + 0xfc) != 0x26b0)
            return 0;
        uint32_t amount = read(r, args[3] + 0x108);
        if (int32_t(amount) <= 0)
            amount = 5;
        uint32_t old = read(r, args[2] + 0x78), sum = old + amount;
        write(r, args[2] + 0x78, int32_t(sum) > 99 ? 99 : sum);
        uint32_t v;
        execute(r, 0x41d6f0, 0, args + 3, 1, &v);
        write(r, args[3] + 8, read(r, args[3] + 8) | 0x10000);
        if (r.x->auxiliaryManagerToken && read(r, r.x->auxiliaryManagerToken + 0xc) == r.x->auxiliarySceneToken)
            write(r, r.x->auxiliaryManagerToken + 0x4c8, 0);
    } else if (fn == 0x405f80)
        value = r.x->auxiliaryManagerToken && read(r, receiver + 0xc) == r.x->auxiliarySceneToken;
    else
        return 0;
    (void)receiver;
    if (result)
        *result = value;
    return 1;
}
struct Award {
    Run *run;
    ClawPlayerDamageContext damage;
};
void sync(Award &a, ClawPlayerLocomotion *s, bool out) {
    auto &r = *a.run;
    auto *actor = span(r, r.x->playerToken, 128);
    auto *body = span(r, r.x->playerPrivateToken, 78);
    auto *item = span(r, a.damage.attackerToken, 128);
    if (!actor || !body || !item)
        return;
    if (out) {
        std::copy(s->actor, s->actor + 128, actor);
        std::copy(s->privateWords, s->privateWords + 78, body);
        std::copy(a.damage.attackerActor, a.damage.attackerActor + 128, item);
    } else {
        std::copy(actor, actor + 128, s->actor);
        std::copy(body, body + 78, s->privateWords);
        std::copy(item, item + 128, a.damage.attackerActor);
    }
}
uint32_t playerBridge(ClawPlayerLocomotion *s, uint32_t fn, uint32_t x, uint32_t y, uint32_t z, void *user) {
    auto &a = *static_cast<Award *>(user);
    auto &r = *a.run;
    sync(a, s, true);
    uint32_t args[4] = {x, y, z, 0}, count = 1, result = 0;
    if (fn == 0x41f850) {
        args[1] = r.x->playerPrivateToken;
        count = 2;
    } else if (fn == 0x41ee60) {
        args[0] = r.x->playerToken;
        args[1] = r.x->playerPrimaryToken;
        args[2] = r.x->playerPrivateToken;
        args[3] = x;
        count = 4;
    }
    if (!execute(r, fn, 0, args, count, &result)) {
        r.x->fault = 2;
    }
    sync(a, s, false);
    return result;
}
} // namespace
extern "C" uint32_t claw_item_pickup_entry(uint32_t fn, uint32_t receiver, const uint32_t *args, uint32_t n,
                                           ClawItemPickupContext *x, ClawItemPickupDependency d, void *user,
                                           uint32_t *result) {
    if (!x || (n && !args))
        return 0;
    Run r{x, d, user};
    return execute(r, fn, receiver, args, n, result);
}
extern "C" uint32_t claw_item_pickup_award(uint32_t item, ClawItemPickupContext *x, ClawItemPickupDependency d,
                                           void *user) {
    if (!x || !x->player)
        return 0;
    Run r{x, d, user};
    auto *words = span(r, item, 128);
    if (!words)
        return 0;
    uint32_t type = words[0xd0 / 4];
    if (type != 0x40000 && type != 0x10000 && type != 0x800000 && type != 0x100000 && type != 0x200000 &&
        !(type == 0x100 && words[0xfc / 4] == 0x26b0))
        return 0;
    if (type == 0x10000 && int32_t(words[0xfc / 4]) > 100)
        return 0;
    Award a{&r, {}};
    a.damage.attackerToken = item;
    sync(a, x->player, false);
    if (x->player->actor[0x74 / 4] != item)
        return 0;
    ClawPlayerInputContext input{};
    uint32_t result = claw_player_hit(x->player, &a.damage, &input, playerBridge, &a);
    sync(a, x->player, true);
    return result && !x->fault;
}
