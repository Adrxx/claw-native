#include "MusicRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawMusicContext *c;
    ClawMusicDependency d;
    void *user;
};
bool bad(Run &r) {
    return r.c->fault != 0;
}
uint32_t *words(Run &r, uint32_t t, uint32_t n) {
    auto &h = r.c->scene;
    auto *p = h.lookup ? h.lookup(h.context, t, n) : nullptr;
    if (!p)
        r.c->fault = 1;
    return p;
}
uint8_t *bytes(Run &r, uint32_t t, uint32_t n) {
    auto *p = r.c->lookupBytes ? r.c->lookupBytes(r.c->scene.context, t, n)
                               : reinterpret_cast<uint8_t *>(words(r, t, (n + 3) / 4));
    if (!p)
        r.c->fault = 1;
    return p;
}
uint32_t rd(Run &r, uint32_t t) {
    auto *p = words(r, t, 1);
    return p ? *p : 0;
}
void wr(Run &r, uint32_t t, uint32_t v) {
    if (bad(r))
        return;
    auto *p = words(r, t, 1);
    if (p)
        *p = v;
}
uint32_t call(Run &r, uint32_t f, uint32_t recv, std::initializer_list<uint32_t> a = {}, uint32_t transport = 0,
              uint32_t *out = nullptr, uint32_t outCount = 0) {
    if (bad(r))
        return 0;
    if (!r.d) {
        r.c->fault = 1;
        return 0;
    }
    ClawMusicCall e{};
    e.function = f;
    e.receiver = recv;
    e.argumentCount = uint32_t(a.size());
    std::copy(a.begin(), a.end(), e.arguments);
    e.transport = transport;
    e.outputs = out;
    e.outputCount = outCount;
    return r.d(r.c, &e, r.user);
}
uint32_t entry(Run &, uint32_t, uint32_t, const uint32_t *, uint32_t, uint32_t *);
uint32_t invoke(Run &r, uint32_t f, uint32_t recv, std::initializer_list<uint32_t> a = {}) {
    uint32_t result = 0;
    if (entry(r, f, recv, a.begin(), uint32_t(a.size()), &result))
        return result;
    return call(r, f, recv, a);
}
uint32_t method(Run &r, uint32_t t, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
    const uint32_t vt = rd(r, t), fn = rd(r, vt + slot);
    if (bad(r))
        return 0;
    return invoke(r, fn, t, a);
}
uint32_t alloc(Run &r, uint32_t n) {
    if (!r.c->scene.allocate) {
        r.c->fault = 1;
        return 0;
    }
    return r.c->scene.allocate(r.c->scene.context, n);
}
void free(Run &r, uint32_t t) {
    if (bad(r))
        return;
    if (!r.c->scene.free) {
        r.c->fault = 1;
        return;
    }
    r.c->scene.free(r.c->scene.context, t);
}
ClawMusicGlobals *globals(Run &r) {
    if (!r.c->globals)
        r.c->fault = 1;
    return r.c->globals;
}
bool guard(Run &r, uint32_t &n) {
    if (n++ >= (r.c->maximumTraversal ? r.c->maximumTraversal : 65536)) {
        r.c->fault = 3;
        return false;
    }
    return !bad(r);
}
uint32_t stringLength(Run &r, uint32_t t) {
    for (uint32_t i = 0; i < 4096; ++i) {
        auto *p = bytes(r, t + i, 1);
        if (!p)
            return 0;
        if (!*p)
            return i + 1;
    }
    r.c->fault = 2;
    return 0;
}
uint32_t lookup(Run &r, uint32_t m, uint32_t name) {
    if (!rd(r, m + 0x20) || !name || bad(r))
        return 0;
    auto *b = bytes(r, name, 1);
    if (!b || !*b)
        return 0;
    uint32_t out = 0;
    return call(r, 0x4f6286, m, {name}, 1, &out, 1) ? out : 0;
}
void clear(Run &r, uint32_t m) {
    uint32_t current = rd(r, m + 0x1c);
    if (current)
        method(r, current, 0x30);
    uint32_t pos = rd(r, m + 0xc) ? 0xffffffff : 0, n = 0;
    while (pos && !bad(r)) {
        if (!guard(r, n))
            return;
        uint32_t out[3] = {pos, 0x52e1c4, 0};
        call(r, 0x4f5e1e, m, {pos}, 2, out, 3);
        pos = out[0];
        if (out[2])
            method(r, out[2], 4, {1});
        call(r, 0x4f6584, 0, {out[1]}, 3);
    }
    call(r, 0x4f61a1, m);
    wr(r, m + 0x1c, 0);
}
uint32_t load(Run &r, uint32_t t, const uint32_t *a) {
    if (!a[0] || a[1] < 4)
        return 0;
    auto *g = globals(r);
    if (!g || !g->midiDriver)
        return 0;
    g->resourceOrdinal += 1;
    wr(r, t + 0x48, 0);
    wr(r, t + 0x54, 100);
    wr(r, t + 0x50, 100);
    if (a[2]) {
        uint32_t n = stringLength(r, a[2]);
        if (bad(r))
            return 0;
        auto *src = bytes(r, a[2], n);
        auto *dst = bytes(r, t + 4, n);
        if (!src || !dst)
            return 0;
        std::memcpy(dst, src, n);
    } else
        call(r, 0x4a3920, 0, {t + 4, 0x53244c, g->resourceOrdinal});
    if (!rd(r, t + 0x5c) && !bad(r)) {
        uint32_t buffer = alloc(r, a[1]);
        wr(r, t + 0x5c, buffer);
        if (!buffer || bad(r))
            return 0;
        auto *src = bytes(r, a[0], a[1]);
        auto *dst = bytes(r, buffer, a[1]);
        if (!src || !dst)
            return 0;
        std::memcpy(dst, src, a[1]);
    }
    if (bad(r))
        return 0;
    const uint32_t handle = call(r, 0x546e9c, 0, {g->midiDriver});
    wr(r, t + 0x58, handle);
    if (call(r, 0x546e98, 0, {handle, rd(r, t + 0x5c), 0}))
        return 1;
    call(r, 0x546e94, 0, {rd(r, t + 0x58)});
    wr(r, t + 0x58, 0);
    return 0;
}
uint32_t entry(Run &r, uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, uint32_t *result) {
    uint32_t required = 0;
    switch (f) {
    case 0x4b52a0:
    case 0x4b53f0:
    case 0x4b58a0:
        required = 3;
        break;
    case 0x4b54f0:
    case 0x4b5a80:
    case 0x4b59c0:
        required = 2;
        break;
    case 0x4b5470:
    case 0x4b54a0:
    case 0x4b5570:
    case 0x4b55b0:
    case 0x4b55e0:
    case 0x4b56b0:
    case 0x4b5b40:
        required = 1;
        break;
    case 0x4b5300:
    case 0x4b5340:
    case 0x4b5550:
    case 0x4b55a0:
    case 0x4b55d0:
    case 0x4b5650:
    case 0x4b56a0:
    case 0x4b56d0:
    case 0x4b5a40:
    case 0x4b5ad0:
    case 0x4b5b00:
    case 0x4b5b90:
    case 0x4b5bd0:
        break;
    default:
        return 0;
    }
    if (n != required || (n && !a)) {
        r.c->fault = 2;
        return 1;
    }
    if (bad(r))
        return 1;
    uint32_t value = 0, current = 0;
    ClawMusicGlobals *g = nullptr;
    switch (f) {
    case 0x4b52a0:
        g = globals(r);
        if (!g)
            break;
        wr(r, t + 0x24, a[0]);
        wr(r, t + 0x20, a[1]);
        wr(r, t + 0x1c, 0);
        wr(r, t + 0x28, 1);
        g->instance = a[0];
        if (!a[2]) {
            call(r, 0x546e70, 0);
            const uint32_t failure = call(r, 0x546e74, 0, {0x54131c, 0, 0xffffffff}, 0, &g->midiDriver, 1);
            if (!failure && g->midiDriver) {
                value = 1;
                break;
            }
        }
        wr(r, t + 0x28, 0);
        value = 1;
        break;
    case 0x4b5340:
        clear(r, t);
        break;
    case 0x4b5300:
        clear(r, t);
        current = rd(r, t + 0x1c);
        if (current)
            method(r, current, 0x30);
        clear(r, t);
        wr(r, t + 0x20, 0);
        wr(r, t + 0x1c, 0);
        g = globals(r);
        if (g)
            g->midiDriver = 0;
        call(r, 0x546e68, 0);
        break;
    case 0x4b53f0: {
        uint32_t resource = alloc(r, 96);
        if (resource) {
            wr(r, resource, 0x513528);
            auto *p = bytes(r, resource + 4, 1);
            if (p)
                *p = 0;
            for (uint32_t off : {0x44u, 0x48u, 0x4cu, 0x58u, 0x5cu})
                wr(r, resource + off, 0);
            wr(r, resource + 0x54, 100);
            wr(r, resource + 0x50, 100);
        }
        if (!method(r, resource, 0x14, {a[0], a[1], a[2]})) {
            if (resource)
                method(r, resource, 4, {1});
            break;
        }
        invoke(r, 0x4b5470, t, {resource});
        value = resource;
        break;
    }
    case 0x4b5470: {
        uint32_t at = call(r, 0x4f62a8, t, {a[0] + 4});
        wr(r, at, a[0]);
        if (!rd(r, t + 0x1c))
            wr(r, t + 0x1c, a[0]);
        break;
    }
    case 0x4b54a0:
        value = lookup(r, t, a[0]);
        break;
    case 0x4b54f0:
        if (!rd(r, t + 0x28))
            break;
        current = lookup(r, t, a[0]);
        if (!current || bad(r))
            break;
        invoke(r, 0x4b5550, t);
        if (!method(r, current, 0x24, {rd(r, t + 0x20), a[1]}))
            break;
        wr(r, t + 0x1c, current);
        value = 1;
        break;
    case 0x4b5550:
        current = rd(r, t + 0x1c);
        if (current) {
            method(r, current, 0x30);
            wr(r, t + 0x1c, 0);
        }
        break;
    case 0x4b5570:
        current = rd(r, t + 0x1c);
        if (current) {
            method(r, current, 0x30);
            current = rd(r, t + 0x1c);
            value = method(r, current, 0x24, {rd(r, t + 0x20), a[0]});
        }
        break;
    case 0x4b55a0:
        current = rd(r, t + 0x1c);
        if (current)
            value = method(r, current, 0x28);
        break;
    case 0x4b55b0:
        current = rd(r, t + 0x1c);
        if (current)
            value = method(r, current, 0x2c, {a[0]});
        break;
    case 0x4b55d0:
        current = rd(r, t + 0x1c);
        if (current)
            value = method(r, current, 0x30);
        break;
    case 0x4b55e0:
        g = globals(r);
        if (!g || !g->midiDriver)
            break;
        {
            const int32_t v = int32_t(a[0]);
            uint32_t volume = v <= 0 ? 0 : v >= 100 ? 127 : uint32_t(v) * 127 / 100;
            call(r, 0x546e6c, 0, {g->midiDriver, volume});
            value = 1;
        }
        break;
    case 0x4b5650:
        g = globals(r);
        if (!g)
            break;
        if (!g->midiDriver) {
            value = 100;
            break;
        }
        {
            int32_t v = int32_t(call(r, 0x546e8c, 0, {g->midiDriver}));
            value = v <= 0 ? 0 : v >= 127 ? 100 : uint32_t(v) * 100 / 127;
        }
        break;
    case 0x4b56a0:
        value = rd(r, t + 0x58) != 0;
        break;
    case 0x4b58a0:
        value = load(r, t, a);
        break;
    case 0x4b56b0:
        invoke(r, 0x4b56d0, t);
        if (a[0] & 1)
            free(r, t);
        value = t;
        break;
    case 0x4b56d0:
        wr(r, t, 0x513528);
        invoke(r, 0x4b5a40, t);
        wr(r, t, 0x50becc);
        break;
    case 0x4b5a40:
        method(r, t, 0x30);
        current = rd(r, t + 0x58);
        if (current) {
            call(r, 0x546e94, 0, {current});
            wr(r, t + 0x58, 0);
        }
        current = rd(r, t + 0x5c);
        if (current) {
            free(r, current);
            wr(r, t + 0x5c, 0);
        }
        break;
    case 0x4b59c0:
        g = globals(r);
        if (!g)
            break;
        {
            uint32_t found = call(r, 0x546ac8, 0, {g->instance, a[0], 0x532454});
            if (!found)
                break;
            uint32_t handle = call(r, 0x546acc, 0, {g->instance, found});
            if (!handle)
                break;
            uint32_t data = call(r, 0x546ac4, 0, {handle});
            if (!data)
                break;
            uint32_t size = call(r, 0x546a54, 0, {g->instance, found});
            value = method(r, t, 0x14, {data, size, a[1]});
        }
        break;
    case 0x4b5a80:
        if (!method(r, t, 0x20))
            break;
        wr(r, t + 0x4c, a[0]);
        wr(r, t + 0x48, a[1]);
        call(r, 0x546e90, 0, {rd(r, t + 0x58)});
        if (a[1])
            call(r, 0x546e88, 0, {rd(r, t + 0x58), 0});
        wr(r, t + 0x44, 0);
        value = 1;
        break;
    case 0x4b5ad0:
        if (method(r, t, 0x20)) {
            call(r, 0x546e78, 0, {rd(r, t + 0x58)});
            wr(r, t + 0x44, 0);
            value = 1;
        }
        break;
    case 0x4b5bd0:
        if (method(r, t, 0x20)) {
            uint32_t status = call(r, 0x546e7c, 0, {rd(r, t + 0x58)});
            value = status == 4 || status == 16;
        }
        break;
    case 0x4b5b00:
        if (!method(r, t, 0x20) || !invoke(r, 0x4b5bd0, t))
            break;
        if (!rd(r, t + 0x44))
            call(r, 0x546e84, 0, {rd(r, t + 0x58)});
        wr(r, t + 0x44, rd(r, t + 0x44) + 1);
        value = 1;
        break;
    case 0x4b5b40:
        if (!method(r, t, 0x20))
            break;
        if (!invoke(r, 0x4b5bd0, t) && int32_t(rd(r, t + 0x44)) > 0) {
            wr(r, t + 0x44, rd(r, t + 0x44) - 1);
            if (a[0])
                wr(r, t + 0x44, 0);
            if (int32_t(rd(r, t + 0x44)) <= 0)
                call(r, 0x546e80, 0, {rd(r, t + 0x58)});
        }
        value = 1;
        break;
    case 0x4b5b90:
        if (!method(r, t, 0x20) || invoke(r, 0x4b5bd0, t))
            break;
        {
            uint32_t loop = rd(r, t + 0x48), target = rd(r, t + 0x4c);
            wr(r, t + 0x44, 0);
            method(r, t, 0x24, {target, loop});
            value = 1;
        }
        break;
    default:
        break;
    }
    if (result)
        *result = value;
    return 1;
}
} // namespace
extern "C" uint32_t claw_music_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, ClawMusicContext *c,
                                     ClawMusicDependency d, void *user, uint32_t *result) {
    if (result)
        *result = 0;
    if (!c)
        return 0;
    Run r{c, d, user};
    uint32_t supported = entry(r, f, t, a, n, result);
    return supported && !bad(r);
}
