#include "GlitterLogic.h"
#include "ActorResourceBindings.h"
#include <algorithm>
#include <initializer_list>
#include <limits>
namespace {
struct Run {
    ClawGlitterContext *c;
    ClawGlitterDependency dependency;
    void *user;
};
bool bad(Run &r) {
    return r.c->fault != 0;
}
uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    auto *p = r.c->scene.lookup ? r.c->scene.lookup(r.c->scene.context, t, n) : nullptr;
    if (!p)
        r.c->fault = 1;
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
const char *name(uint32_t t) {
    switch (t) {
    case 0x522594:
        return "GlitterBaby";
    case 0x527a50:
        return "GAME_SPARKLE";
    case 0x527a40:
        return "GAME_GLITTER1";
    case 0x52a1a8:
        return "GAME_GLITTER";
    case 0x5240d8:
        return "GAME_CYCLE100";
    default:
        return nullptr;
    }
}
uint32_t call(Run &r, uint32_t f, uint32_t recv, std::initializer_list<uint32_t> args = {},
              const char *text = nullptr) {
    if (bad(r))
        return 0;
    if (!r.dependency) {
        r.c->fault = 1;
        return 0;
    }
    ClawGlitterCall e{};
    e.function = f;
    e.receiver = recv;
    e.argumentCount = uint32_t(args.size());
    e.name = text;
    std::copy(args.begin(), args.end(), e.arguments);
    return r.dependency(r.c, &e, r.user);
}
uint32_t entry(Run &, uint32_t, uint32_t);
uint32_t *hostLookup(void *p, uint32_t t, uint32_t n) {
    return span(*static_cast<Run *>(p), t, n);
}
uint32_t hostAllocate(void *p, uint32_t n) {
    auto &r = *static_cast<Run *>(p);
    if (!r.c->scene.allocate) {
        r.c->fault = 1;
        return 0;
    }
    return r.c->scene.allocate(r.c->scene.context, n);
}
void hostFree(void *p, uint32_t t) {
    auto &r = *static_cast<Run *>(p);
    if (!r.c->scene.free) {
        r.c->fault = 1;
        return;
    }
    r.c->scene.free(r.c->scene.context, t);
}
uint32_t hostClock(void *p) {
    auto &r = *static_cast<Run *>(p);
    if (!r.c->scene.readClock) {
        r.c->fault = 1;
        return 0;
    }
    return r.c->scene.readClock(r.c->scene.context);
}
uint32_t hostCall(void *p, ClawSceneActorCall e) {
    auto &r = *static_cast<Run *>(p);
    if (e.function == 0x4485a0 && e.argumentCount == 1)
        return entry(r, e.function, e.arguments[0]);
    if (e.argumentCount == 4)
        return call(r, e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2], e.arguments[3]});
    if (e.argumentCount == 2)
        return call(r, e.function, e.receiver, {e.arguments[0], e.arguments[1]});
    if (e.argumentCount == 1)
        return call(r, e.function, e.receiver, {e.arguments[0]},
                    e.function == 0x4f6286 ? name(e.arguments[0]) : nullptr);
    return call(r, e.function, e.receiver);
}
ClawSceneActorHost host(Run &r) {
    return {&r, hostLookup, hostAllocate, hostFree, hostCall, hostClock};
}
void animation(Run &r, uint32_t f, uint32_t actor, uint32_t arg) {
    if (!r.c->composeAnimation) {
        if (f == 0x4c79e0)
            call(r, f, actor, {arg, 0}, name(arg));
        else
            call(r, f, actor, {arg});
        return;
    }
    ClawActorAnimationGlobals globals{r.c->animationDelta, r.c->audioPosition};
    uint32_t fault = 0, result = 0;
    if (!claw_actor_animation_entry(f, actor, arg, 0, &globals, host(r), &fault, &result) || fault)
        r.c->fault = 2;
}
uint32_t resolved(ClawActorResourceBindings *, ClawActorBindingContext *c, const ClawActorBindingCall *, void *) {
    return c->image.token;
}
void image(Run &r, uint32_t actor, uint32_t literal) {
    if (!r.c->composeAnimation) {
        call(r, 0x4c7970, actor, {literal}, name(literal));
        return;
    }
    auto *a = span(r, actor, 128);
    if (!a)
        return;
    const uint32_t registry = read(r, read(r, actor + 0xc) + 0x10) + 16;
    const uint32_t root = call(r, 0x4f6286, registry, {literal}, name(literal));
    if (bad(r))
        return;
    ClawActorBindingContext c{};
    c.imageRegistryToken = registry;
    c.image.token = root;
    uint32_t leaf = 0;
    if (root) {
        auto *h = span(r, root, 27);
        if (!h)
            return;
        c.image.minimum = int32_t(h[25]);
        c.image.maximum = int32_t(h[26]);
        c.image.firstImageIndex = c.image.minimum;
        c.image.imageCount = 1;
        c.image.images = &leaf;
        if (c.image.minimum <= c.image.maximum)
            leaf = read(r, h[5] + uint32_t(c.image.minimum) * 4);
        if (bad(r))
            return;
    }
    ClawActorResourceBindings b{};
    std::copy_n(a, 128, b.actor);
    if (!claw_actor_bind_default_image(&b, &c, name(literal), resolved, nullptr)) {
        r.c->fault = 1;
        return;
    }
    std::copy_n(b.actor, 128, a);
}
uint32_t coordinate(Run &r, uint32_t minimum, uint32_t maximum) {
    const uint32_t width = maximum - minimum + 1;
    const uint32_t random = call(r, 0x4a3050, 0);
    if (bad(r))
        return 0;
    if (!width)
        return random & 1 ? minimum : maximum;
    const int32_t dividend = int32_t(random), divisor = int32_t(width);
    if (dividend == std::numeric_limits<int32_t>::min() && divisor == -1) {
        r.c->fault = 2;
        return 0;
    }
    return uint32_t(dividend % divisor) + minimum;
}
void create(Run &r, uint32_t container, uint32_t x, uint32_t y, uint32_t z) {
    if (!r.c->composeCreation) {
        call(r, 0x4c8da0, container, {1, x, y, z, 0x522594, 0x240020}, "GlitterBaby");
        return;
    }
    uint32_t fault = 0;
    claw_scene_actor_create_named(container, {1, x, y, z, 0, 0x240020}, 0x522594, host(r), &fault);
    if (fault)
        r.c->fault = 2;
}
uint32_t entry(Run &r, uint32_t f, uint32_t actor) {
    const uint32_t logic = read(r, actor + 0x6c), state = read(r, logic + 0x1c);
    if (bad(r))
        return 0;
    if (f == 0x448440) {
        if (!state) {
            if (read(r, logic + 0x170)) {
                write(r, logic + 0x1c, 10);
                write(r, actor + 8, read(r, actor + 8) | 1);
                write(r, actor + 0x40, read(r, actor + 0x40) | 1);
            }
        } else if (state == 10) {
            const uint32_t count = read(r, r.c->managerToken + 0x124) ? 2 : 1;
            for (uint32_t i = 0; i < count && !bad(r); ++i) {
                uint32_t owner = read(r, logic + 0x170);
                const uint32_t maximum = read(r, owner + 0x120), px = read(r, owner + 0x4c),
                               minimum = read(r, owner + 0x118);
                const uint32_t x = coordinate(r, minimum, maximum) + px;
                if (bad(r))
                    break;
                owner = read(r, logic + 0x170);
                const uint32_t bottom = read(r, owner + 0x124), top = read(r, owner + 0x11c),
                               py = read(r, owner + 0x50);
                const uint32_t y = coordinate(r, top, bottom) + py;
                if (bad(r))
                    break;
                owner = read(r, logic + 0x170);
                const uint32_t z = read(r, owner + 0x64) + 1, container = read(r, read(r, actor + 0xc) + 8);
                if (!bad(r))
                    create(r, container, x, y, z);
            }
            if (!bad(r))
                write(r, logic + 0x20, 15);
        }
    } else if (f == 0x4485a0) {
        if (!state) {
            write(r, actor + 8, read(r, actor + 8) | 0x21);
            image(r, actor, 0x527a50);
            if (!bad(r))
                animation(r, 0x4c79e0, actor, 0x527a40);
            if (!bad(r))
                write(r, logic + 0x1c, 5);
        } else if (state == 5) {
            animation(r, 0x4c82a0, actor + 0x188, r.c->animationDelta);
            if (!bad(r) && read(r, actor + 0x1a4) && !read(r, actor + 0x19c))
                write(r, actor + 8, read(r, actor + 8) | 0x10000);
        }
    } else if (f == 0x470110) {
        if (!state) {
            write(r, logic + 0x168, 0);
            image(r, actor, 0x52a1a8);
            if (bad(r))
                return 0;
            if (!read(r, actor + 0x64)) {
                write(r, actor + 0x64, 1001);
                write(r, actor + 8, read(r, actor + 8) | 0x20000);
            }
            if (!read(r, actor + 0x190))
                animation(r, 0x4c79e0, actor, 0x5240d8);
            if (bad(r))
                return 0;
            write(r, logic + 0x1c, 5);
            const uint32_t random = call(r, 0x4a3050, 0);
            if (!bad(r))
                write(r, logic + 0x20, uint32_t(int32_t(random) % 251));
        } else if (state == 5)
            animation(r, 0x4c82a0, actor + 0x188, r.c->animationDelta);
    }
    return 1;
}
} // namespace
extern "C" uint32_t claw_glitter_entry(uint32_t f, uint32_t receiver, const uint32_t *a, uint32_t n,
                                       ClawGlitterContext *c, ClawGlitterDependency d, void *user, uint32_t *result) {
    (void)receiver;
    if (!c || !a || n < 1 || (f != 0x448440 && f != 0x4485a0 && f != 0x470110))
        return 0;
    Run r{c, d, user};
    const uint32_t value = entry(r, f, a[0]);
    if (result)
        *result = value;
    return 1;
}
