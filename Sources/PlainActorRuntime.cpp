#include "PlainActorRuntime.h"
#include <algorithm>
#include <cstring>
namespace {
uint32_t *span(ClawSceneActorHost h, uint32_t token, uint32_t count, uint32_t *f) {
    auto *p = h.lookup(h.context, token, count);
    if (!p && f)
        *f = 1;
    return p;
}
uint32_t call(ClawSceneActorHost h, uint32_t fn, uint32_t receiver, uint32_t a, uint32_t n) {
    return h.call(h.context, {fn, receiver, {a, 0, 0, 0}, n});
}
} // namespace
uint32_t claw_plain_actor_create(uint32_t container, ClawPlainActorCreate args, ClawSceneActorHost h, uint32_t *fault) {
    if (fault)
        *fault = 0;
    auto *c = span(h, container, 11, fault);
    if (!c)
        return 0;
    const uint32_t token = h.allocate(h.context, 0x168);
    if (!token) {
        if (fault)
            *fault = 2;
        return 0;
    }
    auto *a = span(h, token, 128, fault);
    if (!a)
        return 0;
    const uint32_t parentToken = c[3];
    ClawWorldObjectRuntime s{};
    std::copy_n(a, 128, s.actor);
    ClawWorldObjectContext ctx{};
    ctx.sceneToken = parentToken;
    ctx.actorToken = token;
    claw_world_object_construct(&s, &ctx, args.id);
    s.actor[2] = args.flags;
    // Actual constructor/member stores visible before the primary allocation.
    for (uint32_t o : {4u, 8u, 12u, 0x20u, 0x38u, 0x4cu, 0x54u, 0x3cu, 0x40u, 0x90u, 0x94u, 0xa0u, 0xacu, 0xc4u, 0x68u})
        a[o / 4] = s.actor[o / 4];
    a[0] = 0x513770;
    const uint32_t logic = h.allocate(h.context, 0x174);
    auto *l = logic ? span(h, logic, 93, fault) : nullptr;
    if (!logic) {
        a[27] = 0;
        a[33] = a[32] = a[28] = a[30] = 0;
        a[0] = 0x5137b0;
        if (fault)
            *fault = 2;
        return 0;
    }
    if (!l)
        return 0;
    auto *parent = span(h, parentToken, 10, fault);
    auto *entry = span(h, args.entryToken, 5, fault);
    if (!parent || !entry)
        return 0;
    std::copy_n(a, 128, s.actor);
    std::copy_n(l, 93, s.logic);
    ctx.logicToken = logic;
    ctx.entryToken = args.entryToken;
    ctx.entryFlags = entry[2];
    ctx.entryCallback = entry[4];
    ctx.sceneDefaultType = parent[9];
    claw_world_object_construct(&s, &ctx, args.id);
    s.actor[2] = args.flags;
    s.actor[0] = 0x5137b0;
    // The frozen common actor stores are shared; animated-only stores never
    // belong to the original90-word plain actor and retain supplied padding.
    std::copy_n(s.actor, 90, a);
    std::copy_n(s.logic, 93, l);
    const uint32_t initialized = claw_world_object_initialize(&s, &ctx, 0, 0, args.z);
    std::copy_n(s.actor, 90, a);
    std::copy_n(s.logic, 93, l);
    if (!initialized) {
        call(h, 0x4c9e60, token, 1, 1);
        return 0;
    }
    claw_scene_actor_insert(container, token, h, fault);
    if (fault && *fault)
        return 0;
    if (args.flags & 0x200000)
        call(h, l[4], 0, token, 1);
    return token;
}
uint32_t claw_plain_actor_create_named(uint32_t container, ClawPlainActorCreate args, uint32_t name,
                                       ClawSceneActorHost h, uint32_t *fault) {
    if (fault)
        *fault = 0;
    auto *c = span(h, container, 4, fault);
    if (!c)
        return 0;
    auto *p = span(h, c[3], 6, fault);
    if (!p)
        return 0;
    args.entryToken = call(h, 0x4f6286, p[5] + 16, name, 1);
    if (!args.entryToken) {
        if (fault)
            *fault = 1;
        return 0;
    }
    return claw_plain_actor_create(container, args, h, fault);
}
