#include "ActorWrapperRuntime.h"
#include <initializer_list>
namespace {
struct Failure {};
struct Run {
    ClawActorWrapperContext &c;
    ClawActorWrapperDependency d;
    void *u;
    uint32_t *p(uint32_t t) {
        auto v = c.scene.lookup ? c.scene.lookup(c.scene.context, t, 1) : nullptr;
        if (!v) {
            c.fault = 1;
            throw Failure{};
        }
        return v;
    }
    uint32_t get(uint32_t t, uint32_t off = 0) {
        return *p(t + off);
    }
    void put(uint32_t t, uint32_t off, uint32_t v) {
        *p(t + off) = v;
    }
    void bounds(uint32_t actor, uint32_t offset) {
        auto image = get(actor, 0x174);
        if (!image)
            return;
        ClawSpriteGeometry g{};
        ClawSpriteRect r{};
        g.offsetX = get(image, 0x20);
        g.halfWidth = get(image, 0x18);
        claw_sprite_relative_bounds(&g, &r);
        put(actor, offset, r.left);
        g.offsetY = get(image, 0x24);
        g.halfHeight = get(image, 0x1c);
        claw_sprite_relative_bounds(&g, &r);
        put(actor, offset + 4, r.top);
        g.halfWidth = get(image, 0x18);
        g.offsetX = get(image, 0x20);
        claw_sprite_relative_bounds(&g, &r);
        put(actor, offset + 8, r.right);
        g.offsetY = get(image, 0x24);
        g.halfHeight = get(image, 0x1c);
        claw_sprite_relative_bounds(&g, &r);
        put(actor, offset + 12, r.bottom);
    }
    void indexed(uint32_t actor, uint32_t id) {
        auto root = get(actor, 0x170);
        if (!root)
            return;
        uint32_t frame = 0;
        if (int32_t(id) >= int32_t(get(root, 0x64)) && int32_t(id) <= int32_t(get(root, 0x68)))
            frame = get(get(root, 0x14) + id * 4);
        put(actor, 0x16c, id);
        put(actor, 0x174, frame);
    }
    uint32_t named(uint32_t registry, uint32_t name) {
        uint32_t output = 0;
        ClawActorWrapperCall e{};
        e.function = 0x4f6286;
        e.receiver = registry + 0x10;
        e.argumentCount = 2;
        e.arguments[0] = name;
        e.localMask = 2;
        e.output = &output;
        if (d)
            d(&c, &e, u);
        else if (c.scene.call) {
            ClawSceneActorCall q{};
            q.function = e.function;
            q.receiver = e.receiver;
            q.arguments[0] = name;
            q.argumentCount = 1;
            output = c.scene.call(c.scene.context, q);
        } else {
            c.fault = 1;
            throw Failure{};
        }
        return output;
    }
};
} // namespace
extern "C" uint32_t claw_actor_wrapper_entry(uint32_t fn, uint32_t t, const uint32_t *a, uint32_t n,
                                             ClawActorWrapperContext *c, ClawActorWrapperDependency d, void *u,
                                             uint32_t *out) {
    uint32_t need = 0;
    switch (fn) {
    case 0x406240:
    case 0x406290:
        break;
    case 0x40f6c0:
        need = 4;
        break;
    case 0x4209d0:
    case 0x4061b0:
    case 0x4062e0:
        need = 1;
        break;
    default:
        return 0;
    }
    if (!c || !out || n != need || (!a && n))
        return 0;
    c->fault = 0;
    *out = 0;
    Run r{*c, d, u};
    try {
        switch (fn) {
        case 0x406240:
            r.bounds(t, 0x128);
            break;
        case 0x406290:
            r.bounds(t, 0x118);
            break;
        case 0x40f6c0:
            for (uint32_t i = 0; i < 4; ++i)
                r.put(t, 0x118 + i * 4, a[i]);
            break;
        case 0x4209d0:
            r.indexed(t, a[0]);
            break;
        case 0x4061b0:
            *out = r.named(t, a[0]);
            break;
        case 0x4062e0:
            *out = r.named(r.get(r.get(r.get(t, 4), 12), 0x2c), a[0]);
            break;
        }
    } catch (Failure &) {
    }
    return 1;
}
