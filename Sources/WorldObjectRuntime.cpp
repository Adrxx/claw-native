#include "WorldObjectRuntime.h"
#include <array>
#include <cstring>

namespace {
uint32_t word(const uint8_t *p) {
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
}
uint32_t call(ClawWorldObjectDependency dependency, void *user, ClawWorldObjectRuntime *state,
              ClawWorldObjectContext *context, uint32_t function, uint32_t receiver, uint32_t a = 0, uint32_t b = 0,
              uint32_t count = 0, const char *text = nullptr) {
    if (!dependency)
        return 0;
    const ClawWorldObjectCall event{function, receiver, {a, b, 0, 0}, count, text};
    return dependency(state, context, &event, user);
}
void set(uint32_t *p, std::initializer_list<size_t> offsets, uint32_t value = 0) {
    for (size_t offset : offsets)
        p[offset / 4] = value;
}
} // namespace

void claw_world_object_construct(ClawWorldObjectRuntime *state, const ClawWorldObjectContext *c, uint32_t id) {
    if (!state || !c)
        return;
    auto *a = state->actor;
    auto *l = state->logic;
    a[0] = 0x5137f0;
    a[1] = id;
    a[2] = 0;
    a[3] = c->sceneToken;
    set(a, {0x20, 0x4c, 0x54, 0xac}, 0x80000000);
    set(a, {0x38, 0xc4, 0x168, 0x16c}, 0xffffffff);
    set(a, {0x3c, 0x40, 0x90, 0x94, 0xa0, 0x68, 0x84, 0x80, 0x70, 0x78, 0x18c, 0x190, 0x194, 0x174, 0x170, 0x178, 0x17c,
            0x180, 0x184});
    a[0x6c / 4] = c->logicToken;
    a[0x188 / 4] = 0x513870;
    l[0] = 0x513740;
    l[1] = id;
    l[2] = 0;
    l[3] = c->sceneToken;
    set(l, {0x10, 0x14, 0x18, 0x1c});
}

uint32_t claw_world_object_initialize(ClawWorldObjectRuntime *state, const ClawWorldObjectContext *c, uint32_t x,
                                      uint32_t y, uint32_t z) {
    if (!state || !c)
        return 0;
    auto *a = state->actor;
    auto *l = state->logic;
    a[0x180 / 4] = c->entryToken;
    a[0x184 / 4] = 0;
    a[0x18c / 4] = c->actorToken;
    a[0x190 / 4] = 0;
    a[0x1a4 / 4] = 1;
    a[0x1b0 / 4] = 0x3f800000;
    a[0x4c / 4] = x;
    a[0x50 / 4] = y;
    a[0x64 / 4] = z;
    a[0x48 / 4] = 50;
    a[0x3c / 4] = c->sceneDefaultType;
    a[0xf0 / 4] = z;
    a[0xec / 4] = y;
    a[0xe8 / 4] = x;
    set(a, {0xdc, 0xe0}, 10);
    set(a, {0x10, 0x14, 0x40, 0x44, 0xfc, 0xf8, 0x10c, 0x108, 0x100, 0x104, 0x110, 0x114, 0x148, 0x14c, 0xc8, 0x164});
    // Complete original4c8160, including rejection before clearing when callback0.
    if (!c->entryCallback)
        return 0;
    l[0x10 / 4] = c->entryCallback;
    set(l, {0x14, 0x18, 0x20, 0x24, 0x2c, 0x34, 0x30, 0x38, 0x168, 0x16c, 0x28});
    l[2] = c->entryFlags;
    set(a, {0x70, 0x78, 0x74, 0x7c, 0xd0, 0xd4, 0xd8});
    set(a, {0x118, 0x128, 0x138}, 0x80000000);
    a[0xa0 / 4] = c->actorToken;
    a[0x98 / 4] = a[0x4c / 4];
    a[0x9c / 4] = a[0x50 / 4];
    if (l[2] & 1)
        a[2] |= 0x800000;
    else if (l[2] & 2)
        a[2] |= 0x1000000;
    return 1;
}

uint32_t claw_world_object_load(const uint8_t *record, size_t length, ClawWorldObjectRuntime *state,
                                ClawWorldObjectContext *c, ClawWorldObjectDependency dependency, void *user,
                                ClawWorldObjectInfo *info) {
    if (!record || !state || !c || !c->actorToken || !c->logicToken || length < 284)
        return 0;
    std::array<uint32_t, 71> w{};
    for (size_t i = 0; i < w.size(); ++i)
        w[i] = word(record + 4 * i);
    size_t cursor = 284;
    std::array<std::array<char, 1024>, 4> strings{};
    for (size_t i = 0; i < 4; ++i) {
        const size_t count = w[i + 1];
        if (count > 1023 || count > length - cursor)
            return 0;
        std::memcpy(strings[i].data(), record + cursor, count);
        cursor += count;
    }
    claw_world_object_construct(state, c, w[0]);
    auto destroy = [&] {
        call(dependency, user, state, c, 0x4c9be0, c->actorToken, 1, 0, 1);
    };
    auto finish = [&](uint32_t consumed, uint32_t created) {
        if (info)
            *info = {consumed, created};
        return consumed;
    };
    const int32_t x = int32_t(w[5]), y = int32_t(w[6]);
    if (x < 0 || x >= c->worldWidth || y < 0 || y >= c->worldHeight) {
        destroy();
        return finish(uint32_t(cursor), 0);
    }
    if (!strings[1][0]) {
        destroy();
        return finish(uint32_t(cursor), 0);
    }
    c->entryToken = call(dependency, user, state, c, 0x4f6286, c->registryToken, 0, 0, 0, strings[1].data());
    if (!c->entryToken) {
        destroy();
        return finish(uint32_t(cursor), 0);
    }
    if (!claw_world_object_initialize(state, c, w[5], w[6], w[7])) {
        destroy();
        return finish(0, 0);
    }
    auto *a = state->actor;
    auto *l = state->logic;
    a[2] |= 0x40000;
    // A dependency may alter the actor's attached logic. The API's single logic
    // plane supports its supplied nonzero identity or zero, not another object.
    if (!a[0x6c / 4]) {
        destroy();
        return finish(0, 0);
    }
    if (strings[2][0]) {
        if (w[8] == 0xffffffff)
            call(dependency, user, state, c, 0x4c7970, c->actorToken, 0, 0, 0, strings[2].data());
        else
            call(dependency, user, state, c, 0x4c7900, c->actorToken, w[8], 0, 1, strings[2].data());
    }
    if (strings[3][0]) {
        call(dependency, user, state, c, 0x4c79e0, c->actorToken, 0, 0, 1, strings[3].data());
        call(dependency, user, state, c, 0x4c7a40, c->actorToken, 0, 0, 0, strings[3].data());
    }
    a[2] |= w[10];
    a[0x40 / 4] = w[11];
    l[0x28 / 4] = w[12];
    for (size_t i = 13; i <= 18; ++i)
        a[(0xf8 / 4) + i - 13] = w[i];
    for (size_t i = 19; i <= 30; ++i)
        a[(0x118 / 4) + i - 19] = w[i];
    for (size_t i = 31; i <= 34; ++i)
        a[(0x54 / 4) + i - 31] = w[i];
    for (size_t offset : {0x128u, 0x118u, 0x54u, 0x138u})
        if (!a[offset / 4] && !a[offset / 4 + 2])
            a[offset / 4] = 0x80000000;
    for (size_t i = 35; i <= 42; ++i)
        l[(0xf0 / 4) + i - 35] = w[i];
    for (size_t i = 43; i <= 50; ++i)
        l[(0x64 / 4) + i - 43] = w[i];
    l[0x2c / 4] = w[51];
    l[0x34 / 4] = w[52];
    l[0x30 / 4] = w[53];
    l[0x38 / 4] = w[54];
    a[0x148 / 4] = w[55];
    a[0x14c / 4] = w[56];
    l[0x44 / 4] = w[57];
    l[0x48 / 4] = w[58];
    l[0xb8 / 4] = w[59];
    l[0xbc / 4] = w[60];
    l[0xc8 / 4] = w[61];
    l[0xcc / 4] = w[62];
    a[0x110 / 4] = w[63];
    a[0x114 / 4] = w[64];
    l[0x20 / 4] = w[65];
    l[0x24 / 4] = w[66];
    a[0xd0 / 4] = w[67];
    a[0xd4 / 4] = w[68];
    if (w[69])
        a[0xdc / 4] = w[69];
    if (w[70])
        a[0xe0 / 4] = w[70];
    const size_t layer = a[2] & 0x800000 ? 1 : a[2] & 0x1000000 ? 2 : 0;
    call(dependency, user, state, c, 0x4f4630, c->layerTokens[layer], c->actorToken + 0x88, 0, 1);
    return finish(uint32_t(cursor), 1);
}
