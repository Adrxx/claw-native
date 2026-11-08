#include "PlayerHUDRuntime.h"
#include "ActorResourceBindings.h"
#include "ActorWrapperRuntime.h"
#include "PickupPointsRuntime.h"
#include "PlayerPowerupRuntime.h"
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <initializer_list>
#ifndef CLAW_SCORE_LIFE_INTERVAL
#define CLAW_SCORE_LIFE_INTERVAL 1000000
#endif
namespace {
struct Run {
    ClawPlayerHUDContext &c;
    ClawPlayerHUDDependency d;
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
    uint32_t invoke(uint32_t, uint32_t, std::initializer_list<uint32_t> = {});
};
int32_t sign(uint32_t v) {
    int32_t n;
    std::memcpy(&n, &v, 4);
    return n;
}
const char *label(uint32_t t) {
    switch (t) {
    case 0x52c734:
        return "GAME_INTERFACE_TREASURECHEST";
    case 0x52c71c:
        return "GAME_INTERFACE_CHEST";
    case 0x52c700:
        return "GAME_INTERFACE_SCORENUMBERS";
    case 0x52c6f8:
        return "%010i";
    case 0x52c7c4:
        return "GAME_INTERFACE_WEAPONS_PISTOL";
    case 0x52c790:
        return "GAME_INTERFACE_SMALLNUMBERS";
    case 0x52c7ac:
        return "GAME_INTERFACE_PISTOL";
    case 0x52c7fc:
        return "GAME_INTERFACE_WEAPONS_MAGIC";
    case 0x52c7e4:
        return "GAME_INTERFACE_MAGIC";
    case 0x52c834:
        return "GAME_INTERFACE_WEAPONS_DYNAMITE";
    case 0x52c81c:
        return "GAME_INTERFACE_DYNAMITE";
    case 0x52c774:
        return "GAME_INTERFACE_HEALTHHEART";
    case 0x52c754:
        return "GAME_INTERFACE_HEALTHNUMBERS";
    case 0x52c86c:
        return "GAME_INTERFACE_LIVESHEAD";
    case 0x52c854:
        return "GAME_INTERFACE_LIVES";
    case 0x52c888:
        return "GAME_INTERFACE_STOPWATCH";
    case 0x5240d8:
        return "GAME_CYCLE100";
    case 0x52a2b8:
        return "GAME_EXTRALIFE";
    case 0x522994:
        return "StatusNumberDigit";
    case 0x52297c:
        return "MultiStats";
    case 0x5229d8:
        return "ScoreFrame";
    case 0x5229cc:
        return "WeaponFrame";
    case 0x5229c0:
        return "HealthFrame";
    case 0x5229b4:
        return "LivesFrame";
    case 0x5229a8:
        return "TimerFrame";
    default:
        return nullptr;
    }
}
uint32_t dependency(Run &r, ClawPlayerHUDCall e) {
    if (r.c.fault)
        return 0;
    if (r.d)
        return r.d(&r.c, &e, r.user);
    if (e.function == 0x4f63ec && r.c.scene.allocate)
        return r.c.scene.allocate(r.c.scene.context, e.arguments[0]);
    if (e.function == 0x4f6428 && r.c.scene.free) {
        r.c.scene.free(r.c.scene.context, e.arguments[0]);
        return 0;
    }
    if (!e.buffer && e.argumentCount <= 4 && r.c.scene.call) {
        ClawSceneActorCall v{e.function, e.receiver, {0, 0, 0, 0}, e.argumentCount};
        std::copy_n(e.arguments, e.argumentCount, v.arguments);
        return r.c.scene.call(r.c.scene.context, v);
    }
    r.c.fault = 1;
    return 0;
}
uint32_t callback(Run &, uint32_t, uint32_t);
uint32_t *hostLookup(void *u, uint32_t t, uint32_t n) {
    return static_cast<Run *>(u)->span(t, n);
}
uint32_t hostCall(void *u, ClawSceneActorCall e) {
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
uint32_t hostAllocate(void *u, uint32_t n) {
    return static_cast<Run *>(u)->invoke(0x4f63ec, 0, {n});
}
void hostFree(void *u, uint32_t t) {
    static_cast<Run *>(u)->invoke(0x4f6428, 0, {t});
}
uint32_t hostClock(void *u) {
    auto &r = *static_cast<Run *>(u);
    if (!r.c.scene.readClock) {
        r.c.fault = 1;
        return 0;
    }
    return r.c.scene.readClock(r.c.scene.context);
}
ClawSceneActorHost host(Run &r) {
    return {&r, hostLookup, hostAllocate, hostFree, hostCall, hostClock};
}
uint32_t bridgeShared(ClawCheckpointTimerContext *, const ClawCheckpointTimerCall *e, void *u) {
    auto &r = *static_cast<Run *>(u);
    if (e->buffer) {
        ClawPlayerHUDCall v{};
        v.function = e->function;
        v.receiver = e->receiver;
        v.argumentCount = e->argumentCount;
        std::copy_n(e->arguments, e->argumentCount, v.arguments);
        v.name = e->name;
        v.localMask = e->localMask;
        v.buffer = e->buffer;
        v.bufferBytes = e->bufferBytes;
        return dependency(r, v);
    }
    switch (e->argumentCount) {
    case 0:
        return r.invoke(e->function, e->receiver);
    case 1:
        return r.invoke(e->function, e->receiver, {e->arguments[0]});
    case 2:
        return r.invoke(e->function, e->receiver, {e->arguments[0], e->arguments[1]});
    case 3:
        return r.invoke(e->function, e->receiver, {e->arguments[0], e->arguments[1], e->arguments[2]});
    case 4:
        return r.invoke(e->function, e->receiver, {e->arguments[0], e->arguments[1], e->arguments[2], e->arguments[3]});
    case 6:
        return r.invoke(
            e->function, e->receiver,
            {e->arguments[0], e->arguments[1], e->arguments[2], e->arguments[3], e->arguments[4], e->arguments[5]});
    default:
        r.c.fault = 3;
        return 0;
    }
}
uint32_t resolved(ClawActorResourceBindings *, ClawActorBindingContext *c, const ClawActorBindingCall *, void *) {
    return c->image.token;
}
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a) {
    if (c.fault)
        return 0;
    uint32_t args[8]{};
    std::copy(a.begin(), a.end(), args);
    uint32_t out = 0;
    if (f == 0x4908b0 || f == 0x490f80 || f == 0x490c50 || f == 0x4912a0 || f == 0x491540)
        return callback(*this, f, args[0]);
    if (f == 0x40af90)
        return 3;
    if (f == 0x4bc110) {
        ClawPlayerPowerupGlobals g{};
        ClawPlayerPowerupRuntimeContext x{host(*this), &g, 0};
        claw_player_powerup_entry(f, t, nullptr, 0, &x, nullptr, nullptr, &out);
        if (x.fault)
            c.fault = x.fault;
        return out;
    }
    if ((f == 0x4c79e0 || f == 0x4c82a0) && c.composeAnimation) {
        ClawActorAnimationGlobals g{c.shared->globals->animationDelta, c.shared->globals->audioPosition};
        uint32_t fault = 0;
        claw_actor_animation_entry(f, t, args[0], args[1], &g, host(*this), &fault, &out);
        if (fault)
            c.fault = fault;
        return out;
    }
    if (f == 0x4209d0) {
        ClawActorWrapperContext x{host(*this), 0};
        claw_actor_wrapper_entry(f, t, args, uint32_t(a.size()), &x, nullptr, nullptr, &out);
        if (x.fault)
            c.fault = x.fault;
        return out;
    }
    if (f == 0x40f680) {
        ClawPickupPointsContext x{};
        x.scene = host(*this);
        claw_pickup_points_entry(f, t, args, uint32_t(a.size()), &x, nullptr, nullptr, &out);
        if (x.fault)
            c.fault = x.fault;
        return out;
    }
    if (f == 0x4c7970 && c.composeImages) {
        uint32_t registry = read(read(t + 12) + 0x10) + 16;
        uint32_t root = invoke(0x4f6286, registry, {args[0]});
        ClawActorBindingContext x{};
        x.imageRegistryToken = registry;
        x.image.token = root;
        uint32_t image = 0;
        if (root) {
            x.image.minimum = sign(read(root + 100));
            x.image.maximum = sign(read(root + 104));
            image = invoke(0x40f680, root, {uint32_t(x.image.minimum)});
            x.image.firstImageIndex = x.image.minimum;
            x.image.images = &image;
            x.image.imageCount = 1;
        }
        auto *p = span(t, 109);
        if (!p)
            return 0;
        ClawActorResourceBindings state{};
        std::copy_n(p, 109, state.actor);
        if (!claw_actor_bind_default_image(&state, &x, label(args[0]), resolved, nullptr)) {
            c.fault = 3;
            return 0;
        }
        std::copy_n(state.actor, 109, p);
        return 1;
    }
    if (c.composeControllers &&
        (f == 0x490c40 || f == 0x490760 || f == 0x490590 || f == 0x490c00 || f == 0x40db30 || f == 0x40db50 ||
         f == 0x4919f0 || f == 0x491ed0 || f == 0x491b30 || f == 0x4d3ef0 || f == 0x4d3f20 || f == 0x4c9fc0 ||
         f == 0x4c9fe0 || f == 0x4d3eb0 || f == 0x4f5172 ||
         ((f == 0x4d3e50 || f == 0x4d3ca0 || f == 0x4c8f60 || f == 0x4c8e00) && c.shared->composeHierarchy))) {
        auto &x = *c.shared;
        auto old = x.scene;
        uint32_t oldAnimation = x.composeAnimation, oldImages = x.composeImages, oldFormatting = x.composeFormatting;
        x.scene = host(*this);
        x.composeAnimation = 0;
        x.composeImages = 0;
        x.composeFormatting = c.composeFormatting;
        uint32_t ok = claw_checkpoint_timer_entry(f, t, args, uint32_t(a.size()), &x, bridgeShared, this, &out);
        x.scene = old;
        x.composeAnimation = oldAnimation;
        x.composeImages = oldImages;
        x.composeFormatting = oldFormatting;
        if (ok) {
            if (x.fault)
                c.fault = x.fault;
            return out;
        }
    }
    ClawPlayerHUDCall e{};
    e.function = f;
    e.receiver = t;
    e.argumentCount = uint32_t(a.size());
    std::copy(a.begin(), a.end(), e.arguments);
    for (auto v : a)
        if (label(v))
            e.name = label(v);
    return dependency(*this, e);
}
uint32_t hud(Run &r, uint32_t a, uint32_t l, bool baseCtor, uint32_t horizontal, uint32_t x, uint32_t y, uint32_t value,
             uint32_t digits, uint32_t spacing, uint32_t digitX, uint32_t digitY, uint32_t digitName) {
    uint32_t h = r.invoke(0x4f63ec, 0, {0x60});
    if (h) {
        if (baseCtor) {
            r.put(h, 0x50b014);
            r.invoke(0x490c40, h + 0x28);
        } else
            r.put(h + 0x28, 0x50b5cc);
        r.put(h, 0x50b5c4);
    }
    r.invoke(0x490760, h, {a, r.read(r.c.shared->globals->managerToken + 0x68), 99, horizontal, x, 4, y});
    r.put(l + 0x18, h);
    r.invoke(0x490590, h + 0x28,
             {r.c.shared->globals->multiStatsToken, a, value, digits, spacing, digitX, digitY, digitName});
    return h;
}
void refresh(Run &r, uint32_t h, bool inlineDraw) {
    auto &g = *r.c.shared->globals;
    uint32_t mode = r.read(g.managerToken + 0x68);
    if (r.read(h + 0x14) == mode && sign(r.read(g.managerToken + 0x6c)) < 1)
        return;
    r.put(h + 0x14, mode);
    if (sign(mode) > sign(r.read(h + 0x18)) || r.c.fault)
        return;
    uint32_t x = r.read(h + 4);
    if (x == 1)
        r.put(r.read(h + 0x24) + 76, r.read(h + 8) + g.left);
    else if (x == 2)
        r.put(r.read(h + 0x24) + 76, r.read(h + 8) + g.right);
    else if (x == 3)
        r.put(r.read(h + 0x24) + 76, uint32_t(sign(g.right - g.left) / 2) + r.read(h + 8) + g.left);
    uint32_t y = r.read(h + 12);
    if (y == 3)
        r.put(r.read(h + 0x24) + 80, uint32_t(sign(g.bottom - g.top) / 2) + r.read(h + 16) + g.top);
    else if (y == 4)
        r.put(r.read(h + 0x24) + 80, r.read(h + 16) + g.top);
    else if (y == 5)
        r.put(r.read(h + 0x24) + 80, r.read(h + 16) + g.bottom);
    if (r.read(h + 0x14) == 0) {
        r.put(h + 0x14, mode);
        if (!inlineDraw)
            r.invoke(0x490c00, h);
        else {
            uint32_t a = r.read(h + 0x24), screen = r.read(r.read(a + 12) + 12), f = r.read(r.read(screen) + 0x28);
            r.invoke(f, screen, {r.read(a + 76), r.read(a + 80), r.read(a + 0x174)});
            uint32_t live = r.read(h + 0x24);
            r.put(live + 0x40, r.read(live + 0x40) | 1);
            r.put(h + 0x20, 0);
            r.put(h + 0x1c, 1);
        }
    }
}
void format(Run &r, char *buffer, uint32_t value) {
    if (r.c.composeFormatting) {
        std::snprintf(buffer, 16, "%010i", sign(value));
        return;
    }
    ClawPlayerHUDCall e{};
    e.function = 0x4a3920;
    e.argumentCount = 3;
    e.arguments[1] = 0x52c6f8;
    e.arguments[2] = value;
    e.name = "%010i";
    e.localMask = 1;
    e.buffer = buffer;
    e.bufferBytes = 16;
    dependency(r, e);
}
void digits(Run &r, uint32_t h, uint32_t value, uint32_t method) {
    char text[16]{};
    format(r, text, value);
    if (r.c.fault)
        return;
    uint32_t length = uint32_t(std::strlen(text));
    for (uint32_t i = 0; sign(i) < sign(r.read(h + 0x30)) && !r.c.fault; ++i) {
        uint32_t count = r.read(h + 0x30);
        if (count > length || count > 10) {
            r.c.fault = 3;
            return;
        }
        uint32_t a = r.read(h + 0x34 + i * 4), index = uint32_t(int32_t(text[length - count + i]) - 48);
        if (method == 1)
            r.invoke(0x4209d0, a, {index});
        else {
            uint32_t root = r.read(a + 0x170);
            if (root) {
                uint32_t frame = method == 2 ? r.invoke(0x40f680, root, {index}) : 0;
                if (!method && sign(index) >= sign(r.read(root + 100)) && sign(index) <= sign(r.read(root + 104)))
                    frame = r.read(r.read(root + 20) + index * 4);
                r.put(a + 0x174, frame);
                r.put(a + 0x16c, index);
            }
        }
        r.put(r.read(a + 108) + 0x68, 0xffffffff);
    }
}
void hideDigits(Run &r, uint32_t h, bool hide) {
    for (uint32_t i = 0; sign(i) < sign(r.read(h + 0x30)) && !r.c.fault; ++i) {
        if (i >= 10) {
            r.c.fault = 3;
            return;
        }
        uint32_t a = r.read(h + 0x34 + i * 4);
        r.put(a + 0x40, hide ? r.read(a + 0x40) | 1 : r.read(a + 0x40) & ~1u);
    }
}
uint32_t privateToken(Run &r, uint32_t player) {
    return r.read(r.read(player + 108) + 0x14);
}
uint32_t callback(Run &r, uint32_t f, uint32_t a) {
    auto &g = *r.c.shared->globals;
    auto &e = *r.c.globals;
    uint32_t l = r.read(a + 108), state = r.read(l + 28);
    if (!state) {
        uint32_t x = 0;
        if (f == 0x4908b0) {
            r.invoke(0x4c7970, a, {0x52c734});
            r.invoke(0x4c79e0, a, {0x52c71c, 0});
            r.put(a + 0xfc, CLAW_SCORE_LIFE_INTERVAL);
            r.put(a + 8, r.read(a + 8) | 1);
            uint32_t image = r.read(a + 0x174);
            r.put(a + 0xfc, (uint32_t(sign(e.initialScore) / CLAW_SCORE_LIFE_INTERVAL) + 1) * CLAW_SCORE_LIFE_INTERVAL);
            if (image)
                x = r.read(image + 24) - r.read(image + 32);
            hud(r, a, l, true, 1, x, 15, e.initialScore, 8, 11, 36, 0, 0x52c700);
            r.put(l + 28, 5);
            return 1;
        }
        if (f == 0x490f80 || f == 0x490c50) {
            if (!g.playerToken)
                return 0;
            uint32_t p = privateToken(r, g.playerToken);
            if (!p)
                return 0;
            r.put(l + 0x168, p);
            r.invoke(0x4c7970, a, {f == 0x490f80 ? 0x52c7c4u : 0x52c774u});
            uint32_t image = r.read(a + 0x174);
            r.put(a + 8, r.read(a + 8) | 1);
            if (image)
                x = (f == 0x490f80 ? 1u : 3u) - r.read(image + 32) - r.read(image + 24);
            if (f == 0x490f80)
                hud(r, a, l, false, 2, x, 46, 99, 2, 8, uint32_t(-42), 0, 0x52c790);
            else
                hud(r, a, l, false, 2, x, 15, e.initialHealth, 3, 11, uint32_t(-52), uint32_t(-1), 0x52c754);
            r.put(l + 28, 5);
            if (f == 0x490c50)
                r.put(l + 0x130, 0);
            return 1;
        }
        if (f == 0x4912a0) {
            r.invoke(0x4c7970, a, {0x52c86c});
            r.invoke(0x4c79e0, a, {0x52c854, 0});
            r.put(a + 8, r.read(a + 8) | 1);
            uint32_t owner = r.read(g.managerToken + 0x2c), mode = r.invoke(r.read(r.read(owner) + 0x10), owner);
            if (mode == 4) {
                r.put(l + 28, 11);
                r.put(a + 0x40, r.read(a + 0x40) | 1);
                return 1;
            }
            uint32_t image = r.read(a + 0x174);
            if (image)
                x = 3 - r.read(image + 32) - r.read(image + 24);
            hud(r, a, l, false, 2, x, 72, 9, 1, 8, uint32_t(-32), 1, 0x52c790);
            r.put(l + 28, 5);
            return 1;
        }
        r.invoke(0x4c7970, a, {0x52c888});
        r.invoke(0x4c79e0, a, {0x5240d8, 0});
        uint32_t image = r.read(a + 0x174);
        r.put(a + 8, r.read(a + 8) | 1);
        r.put(a + 0x40, r.read(a + 0x40) | 1);
        if (image)
            x = r.read(image + 24) - r.read(image + 32);
        uint32_t h = hud(r, a, l, true, 1, x, 48, 0, 3, 11, 36, 1, 0x52c700);
        hideDigits(r, h, true);
        r.put(l + 28, 5);
        return 1;
    }
    if (state != 5)
        return 1;
    if (f == 0x4908b0 || f == 0x4912a0)
        r.invoke(0x4c82a0, a + 0x188, {g.animationDelta});
    uint32_t h = r.read(l + 0x18);
    if (!h || r.c.fault)
        return 1;
    if (f == 0x4908b0) {
        refresh(r, h, false);
        if (g.playerToken) {
            uint32_t score = r.read(g.playerToken + 0xf8);
            if (r.read(h + 0x2c) != score) {
                r.put(h + 0x2c, score);
                digits(r, h, score, 1);
            }
            if (sign(r.read(a + 0xfc)) <= sign(r.read(h + 0x2c))) {
                uint32_t p = privateToken(r, g.playerToken);
                if (sign(r.read(p + 0x7c)) < 10) {
                    uint32_t registry = r.read(r.read(a + 12) + 0x28);
                    if (!r.read(registry + 0x30)) {
                        uint32_t sound = r.invoke(0x4f6286, registry + 0x10, {0x52a2b8});
                        if (sound && e.audioEnabled)
                            r.invoke(0x4b45f0, r.read(sound + 16), {g.audioPosition, 0, 0, 0});
                    }
                    r.put(p + 0x7c, r.read(p + 0x7c) + 1);
                }
                r.put(a + 0xfc, r.read(a + 0xfc) + CLAW_SCORE_LIFE_INTERVAL);
            }
        }
        return 1;
    }
    if (f == 0x490f80) {
        uint32_t p = r.read(l + 0x168);
        if (!p)
            return 1;
        uint32_t weapon = r.read(p + 0x30);
        if (r.read(h + 0x5c) != weapon) {
            r.put(h + 0x5c, weapon);
            if (weapon == 1) {
                r.invoke(0x4c7970, a, {0x52c7c4});
                r.invoke(0x4c79e0, a, {0x52c7ac, 0});
            } else if (weapon == 2) {
                r.invoke(0x4c7970, a, {0x52c7fc});
                r.invoke(0x4c79e0, a, {0x52c7e4, 0});
            } else if (weapon == 3) {
                r.invoke(0x4c7970, a, {0x52c834});
                r.invoke(0x4c79e0, a, {0x52c81c, 0});
            }
        }
        weapon = r.read(p + 0x30);
        uint32_t amount = weapon == 1   ? r.read(p + 0x70)
                          : weapon == 2 ? r.read(p + 0x74)
                          : weapon == 3 ? r.read(p + 0x78)
                                        : a;
        refresh(r, h, true);
        if (r.read(h + 0x2c) != amount) {
            r.put(h + 0x2c, amount);
            digits(r, h, amount, 0);
        }
        r.invoke(0x4c82a0, a + 0x188, {g.animationDelta});
        return 1;
    }
    if (f == 0x490c50) {
        refresh(r, h, false);
        if (g.playerToken) {
            uint32_t health = r.read(g.playerToken + 0x10c);
            if (r.read(h + 0x2c) != health) {
                r.put(h + 0x2c, health);
                digits(r, h, health, 1);
            }
        }
        uint32_t timer = r.read(l + 0x130);
        r.put(l + 0x130, g.animationDelta < timer ? timer - g.animationDelta : 0);
        if (!r.read(l + 0x130)) {
            r.put(l + 0x130, 300 - r.read(g.playerToken + 0x10c) * 2);
            uint32_t root = r.read(a + 0x170);
            if (root) {
                uint32_t index = r.read(a + 0x16c) + 1;
                r.put(a + 0x16c, index);
                uint32_t image = 0;
                if (sign(index) >= sign(r.read(root + 100)) && sign(index) <= sign(r.read(root + 104)))
                    image = r.read(r.read(root + 20) + index * 4);
                r.put(a + 0x174, image);
                if (!image) {
                    index = r.read(root + 100);
                    r.put(a + 0x16c, index);
                    image = 0;
                    if (sign(index) >= sign(r.read(root + 100)) && sign(index) <= sign(r.read(root + 104)))
                        image = r.read(r.read(root + 20) + index * 4);
                    r.put(a + 0x174, image);
                }
            }
        }
        return 1;
    }
    if (f == 0x4912a0) {
        refresh(r, h, false);
        if (g.playerToken) {
            uint32_t count = r.read(privateToken(r, g.playerToken) + 0x7c) - 1;
            if (sign(count) < 0)
                count = 0;
            if (r.read(h + 0x2c) != count) {
                r.put(h + 0x2c, count);
                digits(r, h, count, 0);
            }
        }
        return 1;
    }
    if (!e.powerupRemaining) {
        if (!(r.read(a + 0x40) & 1)) {
            if (g.playerToken && !r.read(privateToken(r, g.playerToken) + 0x18))
                r.invoke(0x4bc110, 0);
            r.put(a + 0x40, r.read(a + 0x40) | 1);
            hideDigits(r, h, true);
        }
        return 1;
    }
    r.put(a + 0x40, r.read(a + 0x40) & ~1u);
    hideDigits(r, h, false);
    r.invoke(0x4c82a0, a + 0x188, {g.animationDelta});
    refresh(r, h, false);
    uint32_t value = e.powerupRemaining / 1000;
    if (r.read(h + 0x2c) != value) {
        r.put(h + 0x2c, value);
        digits(r, h, value, 2);
    }
    return 1;
}
} // namespace
extern "C" uint32_t claw_player_hud_entry(uint32_t f, uint32_t receiver, const uint32_t *args, uint32_t n,
                                          ClawPlayerHUDContext *c, ClawPlayerHUDDependency d, void *user,
                                          uint32_t *result) {
    if (!c || !c->shared || !c->shared->globals || !c->globals)
        return 0;
    if (f != 0x4908b0 && f != 0x490f80 && f != 0x490c50 && f != 0x4912a0 && f != 0x491540)
        return 0;
    if (n != 1 || !args) {
        c->fault = 3;
        return 0;
    }
    (void)receiver;
    Run r{*c, d, user};
    uint32_t out = callback(r, f, args[0]);
    if (result)
        *result = out;
    return !c->fault;
}
