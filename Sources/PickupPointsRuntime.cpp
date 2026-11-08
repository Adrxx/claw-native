#include "PickupPointsRuntime.h"
#include "ActorResourceBindings.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawPickupPointsContext *x;
    ClawPickupPointsDependency d;
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
uint32_t call(Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> a = {},
              const char *name = nullptr) {
    if (!r.d) {
        r.x->fault = 1;
        return 0;
    }
    ClawPickupPointsCall e{};
    e.function = f;
    e.receiver = receiver;
    e.argumentCount = uint32_t(a.size());
    e.name = name;
    std::copy(a.begin(), a.end(), e.arguments);
    return r.d(r.x, &e, r.user);
}
uint32_t frame(Run &r, uint32_t root, int32_t id) {
    auto *h = span(r, root, 27);
    if (!h)
        return 0;
    if (id < int32_t(h[25]) || id > int32_t(h[26]))
        return 0;
    return read(r, h[5] + uint32_t(id) * 4);
}
uint32_t resolvedImage(ClawActorResourceBindings *, ClawActorBindingContext *c, const ClawActorBindingCall *, void *) {
    return c->image.token;
}
uint32_t image(Run &r, uint32_t actor, bool useDefault, int32_t index) {
    auto *a = span(r, actor, 128);
    if (!a)
        return 0;
    const uint32_t registry = read(r, read(r, actor + 0xc) + 0x10) + 16;
    if (r.x->fault)
        return 0;
    const uint32_t token = call(r, 0x4f6286, registry, {0x52a6c0}, "GAME_POINTS");
    if (r.x->fault)
        return 0;
    ClawActorBindingContext c{};
    c.imageRegistryToken = registry;
    c.image.token = token;
    uint32_t selected = 0;
    if (token) {
        auto *h = span(r, token, 27);
        if (!h)
            return 0;
        c.image.minimum = int32_t(h[25]);
        c.image.maximum = int32_t(h[26]);
        if (useDefault)
            index = c.image.minimum;
        selected = frame(r, token, index);
        if (r.x->fault)
            return 0;
        c.image.firstImageIndex = index;
        c.image.images = &selected;
        c.image.imageCount = 1;
    }
    ClawActorResourceBindings b{};
    std::copy_n(a, 128, b.actor);
    const uint32_t status = useDefault
                                ? claw_actor_bind_default_image(&b, &c, "GAME_POINTS", resolvedImage, nullptr)
                                : claw_actor_bind_indexed_image(&b, &c, "GAME_POINTS", index, resolvedImage, nullptr);
    if (!status) {
        r.x->fault = 1;
        return 0;
    }
    std::copy_n(b.actor, 128, a);
    return 1;
}
uint32_t animCall(void *p, ClawSceneActorCall e) {
    auto &r = *static_cast<Run *>(p);
    if (e.function == 0x4f6286)
        return call(r, e.function, e.receiver, {e.arguments[0]}, e.arguments[0] == 0x52a6c0 ? "GAME_POINTS" : nullptr);
    if (e.argumentCount == 4)
        return call(r, e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2], e.arguments[3]});
    if (e.argumentCount == 2)
        return call(r, e.function, e.receiver, {e.arguments[0], e.arguments[1]});
    if (e.argumentCount == 1)
        return call(r, e.function, e.receiver, {e.arguments[0]});
    return call(r, e.function, e.receiver);
}
uint32_t *animLookup(void *p, uint32_t t, uint32_t n) {
    return span(*static_cast<Run *>(p), t, n);
}
void animation(Run &r, uint32_t f, uint32_t receiver, uint32_t arg, uint32_t eager = 0) {
    if (!r.x->composeAnimation) {
        if (f == 0x4c79e0)
            call(r, f, receiver, {arg, eager}, "GAME_POINTS");
        else
            call(r, f, receiver, {arg});
        return;
    }
    ClawActorAnimationGlobals g{r.x->animationDelta, r.x->audioPosition};
    auto h = r.x->scene;
    h.context = &r;
    h.lookup = animLookup;
    h.call = animCall;
    h.allocate = nullptr;
    h.free = nullptr;
    h.readClock = nullptr;
    uint32_t fault = 0, result = 0;
    if (!claw_actor_animation_entry(f, receiver, arg, eager, &g, h, &fault, &result) || fault)
        r.x->fault = 2;
    // Source animation advance evaluates its passed delta before callbacks. The
    // name setter eager0 does not read further global deltas after lookup.
}
uint32_t create(Run &r, uint32_t container, uint32_t x, uint32_t y) {
    if (!r.x->composeCreation)
        return call(r, 0x4c8da0, container, {0, x, y, 0x22c4, 0x522874, 0x40000}, "PointsIcon");
    uint32_t fault = 0;
    ClawSceneActorCreate a{0, x, y, 0x22c4, r.x->pointsEntryToken, 0x40000};
    uint32_t token = r.x->pointsEntryToken ? claw_scene_actor_create(container, a, r.x->scene, &fault)
                                           : claw_scene_actor_create_named(container, a, 0x522874, r.x->scene, &fault);
    if (fault)
        r.x->fault = 2;
    return token;
}
} // namespace
extern "C" uint32_t claw_pickup_points_entry(uint32_t f, uint32_t receiver, const uint32_t *args, uint32_t n,
                                             ClawPickupPointsContext *x, ClawPickupPointsDependency d, void *user,
                                             uint32_t *result) {
    if (!x || (n && !args))
        return 0;
    Run r{x, d, user};
    uint32_t value = 0;
    switch (f) {
    case 0x4737c0: {
        if (!n)
            return 0;
        const uint32_t item = args[0], parent = read(r, item + 0xc), container = read(r, parent + 8),
                       px = read(r, item + 0x4c), py = read(r, item + 0x50);
        if (x->fault)
            break;
        const uint32_t actor = create(r, container, px, py);
        if (x->fault || !actor)
            break;
        image(r, actor, true, 0);
        if (x->fault)
            break;
        const uint32_t score = read(r, item + 0xfc);
        int32_t index = -1;
        switch (score) {
        case 100:
            index = 1;
            break;
        case 500:
            index = 2;
            break;
        case 1500:
            index = 3;
            break;
        case 2500:
            index = 4;
            break;
        case 5000:
            index = 5;
            break;
        case 7500:
            index = 6;
            break;
        case 10000:
            index = 7;
            break;
        case 15000:
            index = 8;
            break;
        case 25000:
            index = 9;
            break;
        default:
            break;
        }
        if (index < 0) {
            image(r, actor, false, 0);
            break;
        }
        const uint32_t root = read(r, actor + 0x170);
        if (!root || x->fault)
            break;
        const uint32_t selected = frame(r, root, index);
        if (x->fault)
            break;
        write(r, actor + 0x16c, uint32_t(index));
        write(r, actor + 0x174, selected);
        break;
    }
    case 0x473a70: {
        if (!n)
            return 0;
        const uint32_t actor = args[0], logic = read(r, actor + 0x6c), mode = read(r, logic + 0x1c);
        if (x->fault)
            break;
        if (!mode) {
            write(r, actor + 8, read(r, actor + 8) | 0x21);
            animation(r, 0x4c79e0, actor, 0x52a6c0);
            write(r, logic + 0x1c, 5);
        } else if (mode == 5) {
            animation(r, 0x4c82a0, actor + 0x188, x->animationDelta);
            if (read(r, actor + 0x1a4) && !read(r, actor + 0x19c))
                write(r, actor + 8, read(r, actor + 8) | 0x10000);
        }
        value = 1;
        break;
    }
    case 0x40f680:
        if (!n)
            return 0;
        value = frame(r, receiver, int32_t(args[0]));
        break;
    case 0x4c7970:
    case 0x4c7900:
        if (n < (f == 0x4c7970 ? 1u : 2u) || args[0] != 0x52a6c0)
            return 0;
        image(r, receiver, f == 0x4c7970, f == 0x4c7900 ? int32_t(args[1]) : 0);
        break;
    default:
        return 0;
    }
    if (result)
        *result = value;
    return 1;
}
