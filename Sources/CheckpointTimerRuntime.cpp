#include "CheckpointTimerRuntime.h"
#include "ActorResourceBindings.h"
#include "PickupPointsRuntime.h"
#include "ActorDestruction.h"
#include <algorithm>
#include <cstring>
#include <cstdio>
#include <initializer_list>
namespace {
struct Run {
    ClawCheckpointTimerContext *c;
    ClawCheckpointTimerDependency dependency;
    void *user;
};
bool bad(const Run &r) {
    return r.c->fault != 0;
}
uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    if (bad(r))
        return nullptr;
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
int32_t signedWord(uint32_t v) {
    int32_t out;
    std::memcpy(&out, &v, 4);
    return out;
}
uint32_t half(uint32_t v) {
    return uint32_t(signedWord(v) / 2);
}
const char *label(uint32_t t) {
    switch (t) {
    case 0x52c8b4:
        return "GAME_INTERFACE_TIME";
    case 0x52c700:
        return "GAME_INTERFACE_SCORENUMBERS";
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
    case 0x52c6f8:
        return "%010i";
    default:
        return nullptr;
    }
}
uint32_t invoke(Run &r, ClawCheckpointTimerCall e) {
    if (bad(r))
        return 0;
    if (r.dependency)
        return r.dependency(r.c, &e, r.user);
    if (e.function == 0x4f63ec && r.c->scene.allocate)
        return r.c->scene.allocate(r.c->scene.context, e.arguments[0]);
    if (e.function == 0x4f6428 && r.c->scene.free) {
        r.c->scene.free(r.c->scene.context, e.arguments[0]);
        return 0;
    }
    if (!e.buffer && e.argumentCount <= 4 && r.c->scene.call) {
        ClawSceneActorCall a{e.function, e.receiver, {0, 0, 0, 0}, e.argumentCount};
        std::copy_n(e.arguments, e.argumentCount, a.arguments);
        return r.c->scene.call(r.c->scene.context, a);
    }
    r.c->fault = 1;
    return 0;
}
uint32_t call(Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {}) {
    ClawCheckpointTimerCall e{};
    e.function = f;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), e.arguments);
    for (auto v : args)
        if (label(v))
            e.name = label(v);
    return invoke(r, e);
}
uint32_t *hostLookup(void *u, uint32_t t, uint32_t n) {
    static uint32_t actorDelete = 0x4c9be0, logicDelete = 0x4c80c0, hudDelete = 0x40db30;
    if (n == 1) {
        if (t == 0x5137f4)
            return &actorDelete;
        if (t == 0x513744)
            return &logicDelete;
        if (t == 0x50b5c4)
            return &hudDelete;
    }
    return span(*static_cast<Run *>(u), t, n);
}
uint32_t hudDestroy(Run &r, uint32_t receiver, uint32_t flags) {
    write(r, receiver + 0x28, 0x50b014);
    write(r, receiver, 0x50b014);
    if (flags & 1)
        call(r, 0x4f6428, 0, {receiver});
    return receiver;
}

uint32_t hostCall(void *u, ClawSceneActorCall e) {
    auto &r = *static_cast<Run *>(u);
    if (e.function == 0x40db30)
        return hudDestroy(r, e.receiver, e.arguments[0]);
    ClawCheckpointTimerCall v{};
    v.function = e.function;
    v.receiver = e.receiver;
    v.argumentCount = e.argumentCount;
    std::copy_n(e.arguments, e.argumentCount, v.arguments);
    for (uint32_t i = 0; i < e.argumentCount; ++i)
        if (label(e.arguments[i]))
            v.name = label(e.arguments[i]);
    return invoke(r, v);
}
uint32_t hostAllocate(void *u, uint32_t bytes) {
    return call(*static_cast<Run *>(u), 0x4f63ec, 0, {bytes});
}
void hostFree(void *u, uint32_t t) {
    call(*static_cast<Run *>(u), 0x4f6428, 0, {t});
}
ClawSceneActorHost adapted(Run &r) {
    auto h = r.c->scene;
    h.context = &r;
    h.lookup = hostLookup;
    h.call = hostCall;
    h.allocate = hostAllocate;
    h.free = hostFree;
    return h;
}
void animation(Run &r, uint32_t actor) {
    if (!r.c->composeAnimation) {
        call(r, 0x4c82a0, actor + 0x188, {r.c->globals->animationDelta});
        return;
    }
    ClawActorAnimationGlobals g{r.c->globals->animationDelta, r.c->globals->audioPosition};
    uint32_t f = 0, result = 0;
    if (!claw_actor_animation_entry(0x4c82a0, actor + 0x188, g.animationDelta, 0, &g, adapted(r), &f, &result))
        f = 3;
    if (f)
        r.c->fault = f;
}
uint32_t frame(Run &r, uint32_t root, uint32_t index) {
    ClawPickupPointsContext c{};
    c.scene = adapted(r);
    uint32_t out = 0;
    if (!claw_pickup_points_entry(0x40f680, root, &index, 1, &c, nullptr, nullptr, &out) || c.fault)
        r.c->fault = c.fault ? c.fault : 3;
    return out;
}
uint32_t resolvedImage(ClawActorResourceBindings *, ClawActorBindingContext *c, const ClawActorBindingCall *, void *) {
    return c->image.token;
}
void image(Run &r, uint32_t actor, uint32_t name, bool indexed, uint32_t index) {
    if (!r.c->composeImages) {
        if (indexed)
            call(r, 0x4c7900, actor, {name, index});
        else
            call(r, 0x4c7970, actor, {name});
        return;
    }
    const uint32_t registry = read(r, read(r, actor + 0xc) + 0x10) + 16;
    const uint32_t root = call(r, 0x4f6286, registry, {name});
    if (bad(r))
        return;
    ClawActorBindingContext c{};
    c.imageRegistryToken = registry;
    c.image.token = root;
    uint32_t selected = 0;
    if (root) {
        auto *h = span(r, root, 27);
        if (!h)
            return;
        c.image.minimum = signedWord(h[25]);
        c.image.maximum = signedWord(h[26]);
        if (!indexed)
            index = h[25];
        selected = frame(r, root, index);
        c.image.firstImageIndex = signedWord(index);
        c.image.images = &selected;
        c.image.imageCount = 1;
    }
    auto *a = span(r, actor, 109);
    if (!a)
        return;
    ClawActorResourceBindings state{};
    std::copy_n(a, 109, state.actor);
    const uint32_t ok =
        indexed ? claw_actor_bind_indexed_image(&state, &c, label(name), signedWord(index), resolvedImage, nullptr)
                : claw_actor_bind_default_image(&state, &c, label(name), resolvedImage, nullptr);
    if (!ok) {
        r.c->fault = 3;
        return;
    }
    std::copy_n(state.actor, 109, a);
}
void renderHUD(Run &r, uint32_t h) {
    const uint32_t actor = read(r, h + 0x24), screen = read(r, read(r, actor + 0xc) + 0xc),
                   function = read(r, read(r, screen) + 0x28);
    call(r, function, screen, {read(r, actor + 0x4c), read(r, actor + 0x50), read(r, actor + 0x174)});
    const uint32_t live = read(r, h + 0x24);
    write(r, live + 0x40, read(r, live + 0x40) | 1);
    write(r, h + 0x20, 0);
    write(r, h + 0x1c, 1);
}
void position(Run &r, uint32_t h) {
    auto &g = *r.c->globals;
    const uint32_t horizontal = read(r, h + 4), x = read(r, h + 8), actor = read(r, h + 0x24);
    if (horizontal == 1)
        write(r, actor + 0x4c, x + g.left);
    else if (horizontal == 2)
        write(r, actor + 0x4c, x + g.right);
    else if (horizontal == 3)
        write(r, actor + 0x4c, half(g.right - g.left) + x + g.left);
    const uint32_t vertical = read(r, h + 0xc), y = read(r, h + 0x10);
    if (vertical == 3)
        write(r, read(r, h + 0x24) + 0x50, half(g.bottom - g.top) + y + g.top);
    else if (vertical == 4)
        write(r, read(r, h + 0x24) + 0x50, y + g.top);
    else if (vertical == 5)
        write(r, read(r, h + 0x24) + 0x50, y + g.bottom);
}
uint32_t bindHUD(Run &r, uint32_t h, const uint32_t *a) {
    write(r, h + 0xc, a[5]);
    write(r, h + 0x10, a[6]);
    write(r, h + 0x24, a[0]);
    write(r, h + 4, a[3]);
    write(r, h + 8, a[4]);
    write(r, h + 0x18, a[2]);
    write(r, h + 0x20, 1);
    write(r, h + 0x1c, 0);
    write(r, h + 0x5c, 0xffffcfc7);
    write(r, h + 0x14, 0xffffff9d);
    if ((a[1] != 0xffffff9d || signedWord(read(r, r.c->globals->managerToken + 0x6c)) > 0) && !bad(r)) {
        write(r, h + 0x14, a[1]);
        if (signedWord(a[1]) <= signedWord(a[2])) {
            position(r, h);
            if (!read(r, h + 0x14) && !bad(r)) {
                write(r, h + 0x14, a[1]);
                renderHUD(r, h);
            }
        }
    }
    return 1;
}
void refreshHUD(Run &r, uint32_t h) {
    const uint32_t mode = read(r, r.c->globals->managerToken + 0x68);
    if (read(r, h + 0x14) == mode && signedWord(read(r, r.c->globals->managerToken + 0x6c)) < 1)
        return;
    write(r, h + 0x14, mode);
    if (signedWord(read(r, h + 0x18)) < signedWord(mode) || bad(r))
        return;
    position(r, h);
    if (!read(r, h + 0x14) && !bad(r)) {
        write(r, h + 0x14, mode);
        renderHUD(r, h);
    }
}
void listCtor(Run &r, uint32_t list, uint32_t block) {
    for (uint32_t offset : {12u, 16u, 8u, 4u, 20u})
        write(r, list + offset, 0);
    write(r, list, 0x5107bc);
    write(r, list + 24, block);
}
uint32_t append(Run &r, uint32_t list, uint32_t actor) {
    if (!read(r, list + 16) && !bad(r)) {
        const uint32_t block = read(r, list + 24), token = call(r, 0x4f63ec, 0, {block * 12 + 4});
        write(r, token, read(r, list + 20));
        write(r, list + 20, token);
        if (signedWord(block) > 0)
            for (uint32_t i = block; i > 0 && !bad(r); --i) {
                const uint32_t node = token + 4 + (i - 1) * 12;
                write(r, node, read(r, list + 16));
                write(r, list + 16, node);
            }
    }
    const uint32_t node = read(r, list + 16);
    write(r, list + 16, read(r, node));
    write(r, node + 4, read(r, list + 8));
    write(r, node, 0);
    write(r, list + 12, read(r, list + 12) + 1);
    write(r, node + 8, 0);
    write(r, node + 8, actor);
    const uint32_t tail = read(r, list + 8);
    if (tail)
        write(r, tail, node);
    else
        write(r, list + 4, node);
    write(r, list + 8, node);
    return node;
}
uint32_t dispatch(Run &r, uint32_t actor);
void collectionDestroy(Run &, uint32_t);
void destroyKnown(Run &, uint32_t, uint32_t, uint32_t);
uint32_t constructActor(Run &r, uint32_t parent, uint32_t id, uint32_t flags, uint32_t bytes) {
    const uint32_t actor = call(r, 0x4f63ec, 0, {bytes});
    if (!actor)
        return 0;
    auto *a = span(r, actor, 109);
    if (!a)
        return 0;
    const uint32_t scene = read(r, parent + 0xc);
    ClawWorldObjectRuntime state{};
    std::copy_n(a, 109, state.actor);
    ClawWorldObjectContext c{};
    c.sceneToken = scene;
    c.actorToken = actor;
    claw_world_object_construct(&state, &c, id);
    state.actor[2] = flags;
    for (uint32_t offset :
         {4u, 8u, 12u, 0x20u, 0x38u, 0x4cu, 0x54u, 0x3cu, 0x40u, 0x90u, 0x94u, 0xa0u, 0xacu, 0xc4u, 0x68u})
        a[offset / 4] = state.actor[offset / 4];
    a[0] = 0x513770;
    const uint32_t logic = call(r, 0x4f63ec, 0, {0x174});
    std::copy_n(a, 109, state.actor);
    if (logic) {
        auto *l = span(r, logic, 93);
        if (!l)
            return 0;
        std::copy_n(l, 93, state.logic);
    }
    c.logicToken = logic;
    claw_world_object_construct(&state, &c, id);
    state.actor[2] = flags;
    std::copy_n(state.actor, 109, a);
    if (logic)
        std::copy_n(state.logic, 93, span(r, logic, 93));
    if (bytes == 0x1d0) {
        listCtor(r, actor + 0x1b4, 10);
        write(r, actor, 0x513830);
    }
    return actor;
}
uint32_t create(Run &r, uint32_t parent, const uint32_t *a, bool collection) {
    const uint32_t actor = constructActor(r, parent, a[0], a[5], collection ? 0x1d0 : 0x1b4);
    if (!actor) {
        if (collection && !bad(r))
            r.c->fault = 1;
        return 0;
    }
    const uint32_t scene = read(r, parent + 0xc), logic = read(r, actor + 0x6c);
    auto *metadata = span(r, a[4], 5);
    auto *actorData = span(r, actor, 109);
    if (!metadata || !actorData)
        return 0;
    ClawWorldObjectRuntime state{};
    std::copy_n(actorData, 109, state.actor);
    if (logic)
        std::copy_n(span(r, logic, 93), 93, state.logic);
    ClawWorldObjectContext c{};
    c.sceneToken = scene;
    c.actorToken = actor;
    c.logicToken = logic;
    c.sceneDefaultType = read(r, scene + 0x24);
    c.entryToken = a[4];
    c.entryCallback = metadata[4];
    c.entryFlags = metadata[2];
    const uint32_t originalCallback = c.entryCallback;
    if (!logic)
        c.entryCallback = 0;
    const uint32_t unchangedOffsets[6] = {0x180, 0x184, 0x18c, 0x190, 0x1a4, 0x1b0};
    uint32_t saved[6];
    for (uint32_t i = 0; i < 6; ++i)
        saved[i] = state.actor[unchangedOffsets[i] / 4];
    const uint32_t initialized = claw_world_object_initialize(&state, &c, a[1], a[2], a[3]);
    if (collection)
        for (uint32_t i = 0; i < 6; ++i)
            state.actor[unchangedOffsets[i] / 4] = saved[i];
    std::copy_n(state.actor, 109, actorData);
    if (logic)
        std::copy_n(state.logic, 93, span(r, logic, 93));
    if (!logic && originalCallback) {
        r.c->fault = 1;
        return 0;
    }
    if (!initialized) {
        if (collection) {
            collectionDestroy(r, actor);
            call(r, 0x4f6428, 0, {actor});
        } else
            destroyKnown(r, 0x4c9be0, actor, 1);
        return 0;
    }
    uint32_t node = 0;
    if (collection) {
        uint32_t fault = 0;
        claw_scene_actor_insert(parent, actor, adapted(r), &fault);
        if (fault) {
            r.c->fault = fault;
            return 0;
        }
        node = read(r, actor + 0x68);
    } else {
        node = append(r, parent + 0x1b4, actor);
        write(r, actor + 0x68, node);
    }
    if (!node || bad(r))
        return 0;
    if (read(r, actor + 8) & 0x200000)
        dispatch(r, actor);
    return actor;
}
uint32_t namedCreate(Run &r, uint32_t parent, const uint32_t *a, bool collection) {
    if (!r.c->composeHierarchy && !collection)
        return call(r, 0x4d3e50, parent, {a[0], a[1], a[2], a[3], a[4], a[5]});
    const uint32_t meta = call(r, 0x4f6286, read(r, read(r, parent + 0xc) + 0x14) + 16, {a[4]});
    if (!meta || bad(r))
        return 0;
    uint32_t v[6];
    std::copy_n(a, 6, v);
    v[4] = meta;
    return create(r, parent, v, collection);
}
void destroyKnown(Run &r, uint32_t function, uint32_t receiver, uint32_t flags) {
    ClawActorDestructionGlobals g{};
    uint32_t fault = 0, result = 0;
    if (!claw_actor_destruction_entry(function, receiver, flags, &g, adapted(r), &fault, &result)) {
        call(r, function, receiver, {flags});
        return;
    }
    if (fault)
        r.c->fault = fault;
}
void clearList(Run &r, uint32_t list) {
    for (uint32_t offset : {12u, 16u, 8u, 4u})
        write(r, list + offset, 0);
    uint32_t block = read(r, list + 20);
    while (block && !bad(r)) {
        const uint32_t next = read(r, block);
        call(r, 0x4f6428, 0, {block});
        block = next;
    }
    write(r, list + 20, 0);
}
void clearChildren(Run &r, uint32_t parent) {
    uint32_t at = read(r, parent + 0x1b8);
    while (at && !bad(r)) {
        const uint32_t next = read(r, at), actor = read(r, at + 8);
        if (actor) {
            const uint32_t table = read(r, actor);
            destroyKnown(r, table == 0x5137f0 ? 0x4c9be0 : read(r, table + 4), actor, 1);
        }
        at = next;
    }
    clearList(r, parent + 0x1b4);
}
void collectionDestroy(Run &r, uint32_t actor) {
    write(r, actor, 0x513830);
    clearChildren(r, actor);
    write(r, actor + 0x168, 0xffffffff);
    write(r, actor + 0x16c, 0xffffffff);
    write(r, actor + 0x174, 0);
    write(r, actor + 0x170, 0);
    for (uint32_t offset : {0x6cu, 0x70u, 0x78u}) {
        const uint32_t token = read(r, actor + offset);
        if (token) {
            const uint32_t table = read(r, token);
            destroyKnown(r, table == 0x513740 ? 0x4c80c0 : read(r, table + 4), token, 1);
            write(r, actor + offset, 0);
        }
    }
    write(r, actor + 0xc4, 0xffffffff);
    write(r, actor + 0xac, 0x80000000);
    write(r, actor + 0x4c, 0x80000000);
    write(r, actor + 0x20, 0x80000000);
    write(r, actor + 0x38, 0xffffffff);
    write(r, actor + 0x1b4, 0x5107bc);
    clearList(r, actor + 0x1b4);
    write(r, actor + 0x1b4, 0x50becc);
    destroyKnown(r, 0x4c9c00, actor, 0);
}
void formatted(Run &r, char *buffer, uint32_t value) {
    if (r.c->composeFormatting) {
        std::snprintf(buffer, 16, "%010i", signedWord(value));
        return;
    }
    ClawCheckpointTimerCall e{};
    e.function = 0x4a3920;
    e.argumentCount = 3;
    e.arguments[1] = 0x52c6f8;
    e.arguments[2] = value;
    e.name = "%010i";
    e.localMask = 1;
    e.buffer = buffer;
    e.bufferBytes = 16;
    invoke(r, e);
}
void digits(Run &r, uint32_t group, uint32_t value, bool callGetter) {
    char buffer[16]{};
    formatted(r, buffer, value);
    if (bad(r))
        return;
    const uint32_t length = uint32_t(std::strlen(buffer));
    uint32_t i = 0;
    while (signedWord(i) < signedWord(read(r, group + 8)) && !bad(r)) {
        const uint32_t count = read(r, group + 8);
        if (count > length) {
            r.c->fault = 3;
            return;
        }
        const uint32_t index = uint32_t(int32_t(buffer[length - count + i]) - 48), actor = read(r, group + 12 + i * 4),
                       root = read(r, actor + 0x170);
        if (root) {
            uint32_t imageToken;
            if (callGetter)
                imageToken = frame(r, root, index);
            else
                imageToken = frame(r, root, index);
            write(r, actor + 0x174, imageToken);
            write(r, actor + 0x16c, index);
        }
        write(r, read(r, actor + 0x6c) + 0x68, 0xffffffff);
        ++i;
    }
}
uint32_t numbers(Run &r, uint32_t group, const uint32_t *a) {
    const uint32_t actor = a[1];
    if (!read(r, read(r, actor + 0x6c) + 0x18) || bad(r))
        return 0;
    uint32_t count = a[3];
    if (signedWord(count) > 9)
        count = 10;
    write(r, group + 8, count);
    const uint32_t ownerHUD = read(r, read(r, actor + 0x6c) + 0x18);
    uint32_t i = 0, x = a[5];
    while (signedWord(i) < signedWord(read(r, group + 8)) && !bad(r)) {
        const uint32_t values[6] = {0, 0, 0, read(r, actor + 0x64) + 1, 0x522994, 0};
        const uint32_t child = namedCreate(r, a[0], values, false);
        if (!child || bad(r))
            return 0;
        write(r, group + 12 + i * 4, child);
        const uint32_t logic = read(r, child + 0x6c);
        if (!logic || bad(r))
            return 0;
        image(r, child, a[7], false, 0);
        const uint32_t h = call(r, 0x4f63ec, 0, {0x60});
        if (h) {
            write(r, h + 0x28, 0x50b5cc);
            write(r, h, 0x50b5c4);
        }
        const uint32_t props[7] = {
            child, read(r, ownerHUD + 0x14), read(r, ownerHUD + 0x18),       read(r, ownerHUD + 4),
            x,     read(r, ownerHUD + 0xc),  read(r, ownerHUD + 0x10) + a[6]};
        bindHUD(r, h, props);
        write(r, logic + 0x18, h);
        x += a[4];
        ++i;
    }
    write(r, group + 4, 0xffffcfc7);
    if (a[2] != 0xffffcfc7) {
        write(r, group + 4, a[2]);
        digits(r, group, a[2], false);
    }
    return 1;
}
void timer(Run &r, uint32_t actor) {
    auto &g = *r.c->globals;
    const uint32_t p = read(r, actor + 0x6c), mode = read(r, p + 0x1c);
    if (!mode) {
        image(r, actor, 0x52c8b4, true, 1);
        const uint32_t imageToken = read(r, actor + 0x174);
        write(r, actor + 8, read(r, actor + 8) | 1);
        uint32_t x = 32;
        if (imageToken)
            x -= read(r, imageToken + 0x20) + read(r, imageToken + 0x18);
        const uint32_t hud = call(r, 0x4f63ec, 0, {0x60});
        if (hud) {
            write(r, hud, 0x50b014);
            write(r, hud + 0x28, 0x50b5cc);
            write(r, hud, 0x50b5c4);
        }
        const uint32_t props[7] = {actor, read(r, g.managerToken + 0x68), 99, 3, x, 4, 15};
        bindHUD(r, hud, props);
        write(r, p + 0x18, hud);
        write(r, p + 0x1c, 1);
        if (!bad(r))
            g.remaining = g.initialDuration;
        const uint32_t n[8] = {g.multiStatsToken, actor, g.initialDuration / 1000, 3, 11, 40, 0, 0x52c700};
        numbers(r, hud + 0x28, n);
    } else if (mode == 1) {
        const uint32_t limited = std::min(g.remaining, 999000u);
        g.remaining = g.stageDelta < limited ? limited - g.stageDelta : 0;
        if (!g.remaining && g.playerToken) {
            if (signedWord(read(r, g.playerToken + 0x10c)) > 0) {
                g.expired = 1;
                call(r, 0x546d50, 0, {read(r, read(r, g.managerToken + 4) + 4), 0x111, 0x8063, 0});
            }
            write(r, p + 0x1c, 31);
        }
        const uint32_t hud = read(r, p + 0x18);
        if (!hud || bad(r))
            return;
        animation(r, actor);
        refreshHUD(r, hud);
        const uint32_t value = (g.remaining + 500) / 1000;
        if (read(r, hud + 0x2c) != value) {
            write(r, hud + 0x2c, value);
            digits(r, hud + 0x28, value, true);
        }
    } else if (mode == 31) {
        if (g.playerToken && signedWord(read(r, g.playerToken + 0x10c)) < 1)
            write(r, p + 0x1c, 5);
    } else if (mode == 5) {
        if (g.playerToken && signedWord(read(r, g.playerToken + 0x10c)) > 0) {
            g.expired = 0;
            g.remaining = g.initialDuration;
            write(r, p + 0x1c, 1);
        }
    }
}
void digit(Run &r, uint32_t actor) {
    const uint32_t p = read(r, actor + 0x6c), state = read(r, p + 0x1c);
    if (!state) {
        write(r, actor + 8, read(r, actor + 8) | 1);
        write(r, p + 0x1c, 5);
    } else if (state == 5) {
        const uint32_t hud = read(r, p + 0x18);
        if (hud)
            refreshHUD(r, hud);
    }
}
uint32_t children(Run &r, uint32_t parent) {
    uint32_t at = read(r, parent + 0x1b8), count = 0;
    while (at && !bad(r)) {
        const uint32_t next = read(r, at), actor = read(r, at + 8);
        dispatch(r, actor);
        ++count;
        at = next;
    }
    return count;
}
void drawChildren(Run &r, uint32_t parent, uint32_t target) {
    uint32_t at = read(r, parent + 0x1b8);
    while (at && !bad(r)) {
        const uint32_t next = read(r, at), actor = read(r, at + 8), table = read(r, actor);
        const uint32_t fn = table == 0x5137f0 ? 0x4c9e00 : read(r, table + 0x2c);
        call(r, fn, actor, {target});
        at = next;
    }
}
void multiStats(Run &r, uint32_t actor) {
    const uint32_t p = read(r, actor + 0x6c), state = read(r, p + 0x1c);
    if (!state) {
        r.c->globals->multiStatsToken = actor;
        write(r, actor + 8, read(r, actor + 8) | 1);
        write(r, p + 0x1c, 5);
        const uint32_t names[5] = {0x5229d8, 0x5229cc, 0x5229c0, 0x5229b4, 0x5229a8};
        for (uint32_t i = 0; i < 5 && !bad(r); ++i) {
            const uint32_t a[6] = {0, 0, 0, i ? 9999u : 9998u, names[i], i == 4 ? 0x200000u : 0u};
            namedCreate(r, actor, a, false);
        }
    } else if (state == 5)
        children(r, actor);
}
uint32_t dispatch(Run &r, uint32_t actor) {
    const uint32_t fn = read(r, read(r, actor + 0x6c) + 0x10);
    if (r.c->composeHierarchy) {
        if (fn == 0x4919f0) {
            digit(r, actor);
            return 1;
        }
        if (fn == 0x491ed0) {
            multiStats(r, actor);
            return 1;
        }
        if (fn == 0x491b30) {
            timer(r, actor);
            return 1;
        }
    }
    return call(r, fn, 0, {actor});
}
void kill(Run &r, uint32_t actor) {
    if (actor && signedWord(read(r, actor + 0x10c)) > 0) {
        write(r, actor + 0x10c, 0);
        const uint32_t logic = read(r, actor + 0x6c);
        call(r, 0x417b00, 0, {actor, logic, read(r, logic + 0x14), 0});
    }
}
uint32_t mode(Run &r, uint32_t owner) {
    const uint32_t f = read(r, read(r, owner) + 0x10);
    return f == 0x40af90 ? 3 : call(r, f, owner);
}
bool ready(Run &r, uint32_t application) {
    const uint32_t owner = read(r, application + 0x2c);
    if (!owner)
        return false;
    if (mode(r, owner) == 3)
        return true;
    if (mode(r, owner) == 4)
        return true;
    return mode(r, owner) == 6;
}
} // namespace
extern "C" uint32_t claw_checkpoint_timer_entry(uint32_t f, uint32_t receiver, const uint32_t *args, uint32_t n,
                                                ClawCheckpointTimerContext *c, ClawCheckpointTimerDependency dependency,
                                                void *user, uint32_t *result) {
    if (!c || !c->globals)
        return 0;
    uint32_t count = 0;
    switch (f) {
    case 0x491b30:
    case 0x4919f0:
    case 0x491ed0:
    case 0x41f490:
    case 0x40db30:
    case 0x40f680:
    case 0x4d3f20:
    case 0x4c9fc0:
        count = 1;
        break;
    case 0x490760:
        count = 7;
        break;
    case 0x490590:
        count = 8;
        break;
    case 0x4d3ca0:
    case 0x4d3e50:
    case 0x4c8e00:
    case 0x4c8f60:
        count = 6;
        break;
    case 0x426e30:
        count = 3;
        break;
    case 0x490c40:
    case 0x490c00:
    case 0x40db50:
    case 0x4d3ef0:
    case 0x42a630:
    case 0x4c9fe0:
    case 0x4d3eb0:
    case 0x4f5172:
        break;
    default:
        return 0;
    }
    if (n != count || (count && !args)) {
        c->fault = 3;
        return 0;
    }
    if (c->fault)
        return 0;
    Run r{c, dependency, user};
    uint32_t value = 1;
    switch (f) {
    case 0x491b30:
        timer(r, args[0]);
        break;
    case 0x4919f0:
        digit(r, args[0]);
        break;
    case 0x491ed0:
        multiStats(r, args[0]);
        break;
    case 0x490c40:
        write(r, receiver, 0x50b5cc);
        value = 0;
        break;
    case 0x490760:
        value = bindHUD(r, receiver, args);
        break;
    case 0x490590:
        value = numbers(r, receiver, args);
        break;
    case 0x490c00:
        renderHUD(r, receiver);
        value = 0;
        break;
    case 0x40db30:
        value = hudDestroy(r, receiver, args[0]);
        break;
    case 0x40db50:
        hudDestroy(r, receiver, 0);
        value = 0;
        break;
    case 0x4d3e50:
    case 0x4c8f60:
        value = namedCreate(r, receiver, args, f == 0x4c8f60);
        break;
    case 0x4d3ca0:
    case 0x4c8e00:
        value = create(r, receiver, args, f == 0x4c8e00);
        break;
    case 0x4c9fc0:
    case 0x4c9fe0:
        collectionDestroy(r, receiver);
        value = 0;
        if (f == 0x4c9fc0) {
            if (args[0] & 1)
                call(r, 0x4f6428, 0, {receiver});
            value = receiver;
        }
        break;
    case 0x4d3eb0:
        clearChildren(r, receiver);
        value = 0;
        break;
    case 0x4f5172:
        clearList(r, receiver);
        value = 0;
        break;
    case 0x4d3ef0:
        value = children(r, receiver);
        break;
    case 0x4d3f20:
        drawChildren(r, receiver, args[0]);
        value = 0;
        break;
    case 0x40f680:
        value = frame(r, receiver, args[0]);
        break;
    case 0x41f490:
        kill(r, args[0]);
        value = 0;
        break;
    case 0x42a630:
        value = ready(r, receiver);
        break;
    case 0x426e30:
        if (args[1] != 0x8063)
            return 0;
        if (ready(r, receiver) && c->globals->playerToken)
            kill(r, c->globals->playerToken);
        break;
    }
    if (result)
        *result = value;
    return 1;
}
