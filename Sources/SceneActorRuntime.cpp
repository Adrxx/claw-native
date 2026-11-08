#include "SceneActorRuntime.h"
#include <algorithm>
#include <cstring>
namespace {
int32_t signedWord(uint32_t x) {
    int32_t y;
    std::memcpy(&y, &x, 4);
    return y;
}
uint32_t *span(ClawSceneActorHost h, uint32_t t, uint32_t n, uint32_t *fault) {
    uint32_t *p = h.lookup(h.context, t, n);
    if (!p && fault)
        *fault = 1;
    return p;
}
uint32_t invoke(ClawSceneActorHost h, uint32_t fn, uint32_t receiver, uint32_t a = 0, uint32_t b = 0,
                uint32_t count = 0) {
    return h.call(h.context, {fn, receiver, {a, b, 0, 0}, count});
}
bool bad(const uint32_t *f) {
    return f && *f;
}
bool destroy(uint32_t actor, ClawSceneActorHost h, uint32_t *f) {
    uint32_t *a = span(h, actor, 1, f);
    if (!a)
        return false;
    uint32_t function = 0x4c9be0;
    if (a[0] != 0x5137f0) {
        uint32_t *entry = span(h, a[0] + 4, 1, f);
        if (!entry)
            return false;
        function = *entry;
    }
    invoke(h, function, actor, 1, 0, 1);
    return true;
}
uint32_t node(uint32_t *c, uint32_t previous, uint32_t next, ClawSceneActorHost h, uint32_t *fault) {
    if (!c[8]) {
        uint32_t block = h.allocate(h.context, c[10] * 12 + 4);
        if (!block) {
            if (fault)
                *fault = 2;
            return 0;
        }
        uint32_t *p = span(h, block, c[10] * 3 + 1, fault);
        if (!p)
            return 0;
        p[0] = c[9];
        c[9] = block;
        for (uint32_t i = c[10]; i > 0; --i) {
            uint32_t at = block + 4 + (i - 1) * 12;
            uint32_t *q = span(h, at, 3, fault);
            if (!q)
                return 0;
            q[0] = c[8];
            c[8] = at;
        }
    }
    uint32_t token = c[8];
    uint32_t *p = span(h, token, 3, fault);
    if (!p)
        return 0;
    c[8] = p[0];
    p[1] = previous;
    p[0] = next;
    ++c[7];
    p[2] = 0;
    return token;
}
uint32_t append(uint32_t *c, uint32_t actor, ClawSceneActorHost h, uint32_t *f) {
    uint32_t t = node(c, c[6], 0, h, f);
    if (!t)
        return 0;
    span(h, t, 3, f)[2] = actor;
    if (c[6]) {
        uint32_t *p = span(h, c[6], 3, f);
        if (!p)
            return 0;
        p[0] = t;
    } else
        c[5] = t;
    c[6] = t;
    return t;
}
uint32_t before(uint32_t *c, uint32_t at, uint32_t actor, ClawSceneActorHost h, uint32_t *f) {
    uint32_t *old = span(h, at, 3, f);
    if (!old)
        return 0;
    uint32_t t = node(c, old[1], at, h, f);
    if (!t)
        return 0;
    span(h, t, 3, f)[2] = actor;
    if (old[1]) {
        uint32_t *p = span(h, old[1], 3, f);
        if (!p)
            return 0;
        p[0] = t;
    } else
        c[5] = t;
    old[1] = t;
    return t;
}
bool remove(uint32_t *c, uint32_t t, ClawSceneActorHost h, uint32_t *f) {
    if (!t) {
        if (f)
            *f = 2;
        return false;
    }
    uint32_t *p = span(h, t, 3, f);
    if (!p)
        return false;
    if (t == c[5])
        c[5] = p[0];
    else {
        uint32_t *q = span(h, p[1], 3, f);
        if (!q)
            return false;
        q[0] = p[0];
    }
    if (t == c[6])
        c[6] = p[1];
    else {
        uint32_t *q = span(h, p[0], 3, f);
        if (!q)
            return false;
        q[1] = p[1];
    }
    p[0] = c[8];
    --c[7];
    c[8] = t;
    if (!c[7]) {
        uint32_t block = c[9];
        c[7] = c[8] = c[6] = c[5] = 0;
        while (block) {
            uint32_t *q = span(h, block, 1, f);
            if (!q)
                return false;
            uint32_t next = q[0];
            h.free(h.context, block);
            block = next;
        }
        c[9] = 0;
    }
    return true;
}
void resetArray(uint32_t *a, ClawSceneActorHost h) {
    h.free(h.context, a[1]);
    a[1] = a[2] = a[3] = 0;
}
bool addArray(uint32_t *a, uint32_t actor, ClawSceneActorHost h, uint32_t *f) {
    uint32_t size = a[2] + 1;
    if (!a[1]) {
        uint32_t t = h.allocate(h.context, size * 4);
        if (!t) {
            if (f)
                *f = 2;
            return false;
        }
        a[1] = t;
        uint32_t *p = span(h, t, size, f);
        if (!p)
            return false;
        std::fill_n(p, size, 0);
        a[3] = size;
    } else if (size > a[3]) {
        uint32_t grow = a[4] ? a[4] : std::min(1024u, std::max(4u, a[2] / 8));
        uint32_t capacity = std::max(size, a[3] + grow), t = h.allocate(h.context, capacity * 4);
        if (!t) {
            if (f)
                *f = 2;
            return false;
        }
        uint32_t *p = span(h, t, capacity, f), *old = span(h, a[1], a[2], f);
        if (!p || !old)
            return false;
        std::copy_n(old, a[2], p);
        std::fill_n(p + a[2], size - a[2], 0);
        h.free(h.context, a[1]);
        a[1] = t;
        a[3] = capacity;
    } else {
        uint32_t *p = span(h, a[1], size, f);
        if (!p)
            return false;
        std::fill_n(p + a[2], size - a[2], 0);
    }
    a[2] = size;
    uint32_t *p = span(h, a[1], size, f);
    if (!p)
        return false;
    p[size - 1] = actor;
    return true;
}
} // namespace
extern "C" void claw_scene_actor_insert(uint32_t container, uint32_t actor, ClawSceneActorHost h, uint32_t *fault) {
    if (fault)
        *fault = 0;
    uint32_t *c = span(h, container, 11, fault), *a = span(h, actor, 128, fault);
    if (!c || !a)
        return;
    uint32_t at = c[5];
    while (at) {
        uint32_t *n = span(h, at, 3, fault);
        if (!n)
            return;
        uint32_t *b = span(h, n[2], 128, fault);
        if (!b)
            return;
        if (signedWord(b[0x64 / 4]) > signedWord(a[0x64 / 4]) && !(b[2] & 0x20000))
            break;
        at = n[0];
    }
    uint32_t t = at ? before(c, at, actor, h, fault) : append(c, actor, h, fault);
    if (!bad(fault))
        a[0x68 / 4] = t;
}
extern "C" uint32_t claw_scene_actor_create(uint32_t container, ClawSceneActorCreate args, ClawSceneActorHost h,
                                            uint32_t *fault) {
    if (fault)
        *fault = 0;
    uint32_t *c = span(h, container, 11, fault);
    if (!c)
        return 0;
    uint32_t actor = h.allocate(h.context, 0x1b4);
    if (!actor) {
        if (fault)
            *fault = 2;
        return 0;
    }
    uint32_t *a = span(h, actor, 128, fault);
    if (!a)
        return 0;
    // Project the frozen constructor's fields already written before the
    // nested logic allocation; this preserves heap-boundary observations.
    ClawWorldObjectRuntime staged{};
    std::copy_n(a, 128, staged.actor);
    ClawWorldObjectContext partial{};
    partial.sceneToken = c[3];
    partial.actorToken = actor;
    claw_world_object_construct(&staged, &partial, args.id);
    staged.actor[2] = args.flags;
    for (uint32_t offset :
         {4u, 8u, 12u, 0x20u, 0x38u, 0x4cu, 0x54u, 0x3cu, 0x40u, 0x90u, 0x94u, 0xa0u, 0xacu, 0xc4u, 0x68u})
        a[offset / 4] = staged.actor[offset / 4];
    a[0] = 0x513770;
    uint32_t logic = h.allocate(h.context, 0x174);
    uint32_t *l = logic ? span(h, logic, 93, fault) : nullptr, *parent = span(h, c[3], 10, fault),
             *entry = span(h, args.entryToken, 5, fault);
    if ((logic && !l) || !parent || !entry)
        return 0;
    ClawWorldObjectRuntime state{};
    std::copy_n(a, 128, state.actor);
    if (l)
        std::copy_n(l, 93, state.logic);
    ClawWorldObjectContext context{};
    context.sceneToken = c[3];
    context.actorToken = actor;
    context.logicToken = logic;
    context.sceneDefaultType = parent[9];
    context.entryToken = args.entryToken;
    context.entryCallback = entry[4];
    context.entryFlags = entry[2];
    claw_world_object_construct(&state, &context, args.id);
    state.actor[2] = args.flags;
    if (!logic)
        context.entryCallback = 0;
    uint32_t initialized = claw_world_object_initialize(&state, &context, args.x, args.y, args.z);
    std::copy_n(state.actor, 128, a);
    if (l)
        std::copy_n(state.logic, 93, l);
    if (!logic) {
        if (fault)
            *fault = 2;
        return 0;
    }
    if (!initialized) {
        destroy(actor, h, fault);
        return 0;
    }
    claw_scene_actor_insert(container, actor, h, fault);
    if (bad(fault))
        return 0;
    if (args.flags & 0x200000)
        invoke(h, l[4], 0, actor, 0, 1);
    return actor;
}
extern "C" uint32_t claw_scene_actor_create_named(uint32_t container, ClawSceneActorCreate args, uint32_t name,
                                                  ClawSceneActorHost h, uint32_t *fault) {
    if (fault)
        *fault = 0;
    uint32_t *c = span(h, container, 4, fault);
    if (!c)
        return 0;
    uint32_t *parent = span(h, c[3], 6, fault);
    if (!parent)
        return 0;
    args.entryToken = invoke(h, 0x4f6286, parent[5] + 16, name, 0, 1);
    if (!args.entryToken)
        return 0;
    return claw_scene_actor_create(container, args, h, fault);
}
extern "C" void claw_scene_actor_update(uint32_t container, ClawSceneActorGlobals *g, uint32_t refresh,
                                        ClawSceneActorHost h, uint32_t *fault) {
    if (fault)
        *fault = 0;
    if (!(g->initializationFlags & 1)) {
        g->initializationFlags |= 1;
        std::fill_n(g->deletionArray, 5, 0);
        g->deletionArray[0] = 0x5108fc;
        invoke(h, 0x4a35f0, 0, 0x4c91c0, 0, 1);
    }
    if (!(g->initializationFlags & 2)) {
        g->initializationFlags |= 2;
        std::fill_n(g->reorderArray, 5, 0);
        g->reorderArray[0] = 0x5108fc;
        invoke(h, 0x4a35f0, 0, 0x4c91b0, 0, 1);
    }
    resetArray(g->deletionArray, h);
    resetArray(g->reorderArray, h);
    ClawTimingHost clock{h.context, h.readClock, nullptr};
    claw_timing_update_animation(&g->animation, refresh, clock);
    uint32_t *c = span(h, container, 11, fault);
    if (!c)
        return;
    uint32_t at = c[5];
    while (at) {
        uint32_t *n = span(h, at, 3, fault);
        if (!n)
            return;
        uint32_t actor = n[2], next = n[0];
        uint32_t *a = span(h, actor, 128, fault);
        if (!a)
            return;
        uint32_t *l = span(h, a[0x6c / 4], 93, fault);
        if (!l)
            return;
        bool timerActive = false;
        if (l[8]) {
            if (g->animation.deltaMilliseconds >= l[8])
                l[8] = 0;
            else {
                l[8] -= g->animation.deltaMilliseconds;
                timerActive = true;
            }
        }
        if (!timerActive) {
            if (l[9])
                --l[9];
            else
                invoke(h, l[4], 0, actor, 0, 1);
        }
        if (a[2] & 0x10000) {
            if (!addArray(g->deletionArray, actor, h, fault))
                return;
        } else if (a[2] & 0x20000) {
            if (!addArray(g->reorderArray, actor, h, fault))
                return;
        }
        at = next;
    }
    for (uint32_t i = 0; i < g->deletionArray[2]; ++i) {
        uint32_t *q = span(h, g->deletionArray[1], g->deletionArray[2], fault);
        if (!q)
            return;
        uint32_t actor = q[i];
        uint32_t *a = span(h, actor, 128, fault);
        if (!a)
            return;
        if (a[2] & 0x80000) {
            uint32_t *l = span(h, a[0x6c / 4], 93, fault);
            if (!l)
                return;
            l[7] = 29;
            invoke(h, l[4], 0, actor, 0, 1);
        }
        if (!remove(c, a[0x68 / 4], h, fault))
            return;
        if (!destroy(actor, h, fault))
            return;
    }
    for (uint32_t i = 0; i < g->reorderArray[2]; ++i) {
        uint32_t *q = span(h, g->reorderArray[1], g->reorderArray[2], fault);
        if (!q)
            return;
        uint32_t actor = q[i];
        uint32_t *a = span(h, actor, 128, fault);
        if (!a)
            return;
        a[2] &= ~0x20000u;
        if (!remove(c, a[0x68 / 4], h, fault))
            return;
        claw_scene_actor_insert(container, actor, h, fault);
        if (bad(fault))
            return;
    }
}
extern "C" uint32_t claw_scene_stage_run(uint32_t owner, ClawSceneStageState *stage, ClawSceneActorGlobals *g,
                                         uint32_t subdivide, ClawSceneActorHost h, uint32_t *fault) {
    if (fault)
        *fault = 0;
    uint32_t *w = span(h, owner, 474, fault);
    if (!w)
        return 0;
    uint32_t passes = 1, delta = stage->stage.deltaMilliseconds;
    ClawFrameClock saved = stage->stage;
    uint32_t savedAccumulated = stage->accumulatedMilliseconds;
    if (subdivide)
        passes = delta / 18 + (delta % 18 != 0);
    uint32_t now = saved.nowMilliseconds - delta, accumulated = savedAccumulated - delta;
    for (uint32_t i = 0; i < passes; ++i) {
        if (subdivide) {
            uint32_t part = (i == passes - 1 && delta % 18) ? delta % 18 : 18;
            now += part;
            accumulated += part;
            claw_timing_set_replay(&stage->stage, &stage->accumulatedMilliseconds, &g->animation, now, part,
                                   accumulated);
        }
        uint32_t *parent = nullptr, *map = nullptr;
        if (subdivide && i > 0 && i < passes - 1) {
            parent = span(h, w[3], 10, fault);
            if (!parent)
                return 0;
            map = span(h, parent[9], 24, fault);
            if (!map)
                return 0;
            if (map[0x5c / 4])
                invoke(h, 0x4d2000, map[0x5c / 4]);
        }
        invoke(h, 0x46c860, owner);
        parent = span(h, w[3], 10, fault);
        if (!parent)
            return 0;
        map = span(h, parent[9], 24, fault);
        if (!map)
            return 0;
        if (map[0x5c / 4])
            invoke(h, 0x4d1fd0, map[0x5c / 4]);
        parent = span(h, w[3], 10, fault);
        if (!parent)
            return 0;
        claw_scene_actor_update(parent[2], g, subdivide ? 0 : 1, h, fault);
        if (bad(fault))
            return 0;
        parent = span(h, w[3], 10, fault);
        if (!parent)
            return 0;
        invoke(h, 0x4c9390, parent[2]);
    }
    if (subdivide)
        claw_timing_set_replay(&stage->stage, &stage->accumulatedMilliseconds, &g->animation, saved.nowMilliseconds,
                               saved.deltaMilliseconds, savedAccumulated);
    if (w[0x764 / 4]) {
        uint32_t *a = span(h, stage->playerToken, 128, fault);
        if (!a)
            return 0;
        if (a[0x170 / 4]) {
            uint32_t *image = span(h, a[0x170 / 4], 27, fault);
            if (!image)
                return 0;
            uint32_t frame = 0;
            if (signedWord(image[0x64 / 4]) <= 100 && signedWord(image[0x68 / 4]) >= 100) {
                uint32_t *p = span(h, image[0x14 / 4] + 400, 1, fault);
                if (!p)
                    return 0;
                frame = *p;
            }
            a[0x174 / 4] = frame;
            a[0x16c / 4] = 100;
        }
    }
    return passes;
}
extern "C" uint32_t claw_scene_stage_update(uint32_t owner, ClawSceneStageState *stage, ClawSceneActorGlobals *g,
                                            ClawSceneActorHost h, uint32_t *fault) {
    uint32_t delta = stage->stage.deltaMilliseconds;
    return claw_scene_stage_run(owner, stage, g, delta > 18 && delta < 100, h, fault);
}
