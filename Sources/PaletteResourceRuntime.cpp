#include "PaletteResourceRuntime.h"
#include "AmbientAudioBackendRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failed {};
struct Run {
    ClawPaletteResourceContext &c;
    ClawPaletteResourceDependency dependency;
    void *user;
    uint32_t steps = 0;
    static int32_t si(uint32_t x) {
        int32_t v;
        std::memcpy(&v, &x, 4);
        return v;
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Failed{};
        }
        return p;
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    uint8_t *bytes(uint32_t t, uint32_t n) {
        uint64_t count = (uint64_t(n) + (t & 3) + 3) / 4;
        if (count > 0xffffffff) {
            c.fault = 2;
            throw Failed{};
        }
        return reinterpret_cast<uint8_t *>(span(t & ~3u, uint32_t(count))) + (t & 3);
    }
    uint32_t byte(uint32_t t) {
        return *bytes(t, 1);
    }
    void byte(uint32_t t, uint32_t v) {
        *bytes(t, 1) = uint8_t(v);
    }
    void next() {
        if (++steps > (c.maximumSteps ? c.maximumSteps : 1000000)) {
            c.fault = 3;
            throw Failed{};
        }
    }
    uint32_t external(ClawPaletteResourceCall q) {
        uint32_t value = 0;
        if (dependency)
            value = dependency(&c, &q, user);
        else if (c.scene.call && q.argumentCount <= 4 && !q.localMask) {
            ClawSceneActorCall e{};
            e.function = q.function;
            e.receiver = q.receiver;
            e.argumentCount = q.argumentCount;
            std::copy_n(q.arguments, q.argumentCount, e.arguments);
            value = c.scene.call(c.scene.context, e);
        } else {
            c.fault = 1;
            throw Failed{};
        }
        if (c.fault)
            throw Failed{};
        return value;
    }
    uint32_t external(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawPaletteResourceCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        return external(q);
    }
    uint32_t alloc(uint32_t n) {
        return external(0x4f63ec, 0, {n});
    }
    void free(uint32_t t) {
        external(0x4f6428, 0, {t});
    }
    uint32_t vt(uint32_t t, uint32_t off) {
        return get(get(t) + off);
    }
    static uint32_t *lookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->span(t, n);
    }
    static uint32_t listCall(ClawAmbientAudioBackendContext *c, const ClawAmbientAudioBackendCall *e, void *p) {
        auto &r = *static_cast<Run *>(p);
        uint32_t v = r.invoke(e->function, e->receiver, e->arguments, e->argumentCount);
        if (r.c.fault)
            c->fault = r.c.fault;
        return v;
    }
    uint32_t list(uint32_t f, uint32_t t, uint32_t arg) {
        if (!c.composeLists)
            return external(f, t, {arg});
        ClawAmbientAudioBackendContext ctx{};
        ctx.scene = c.scene;
        ctx.scene.context = this;
        ctx.scene.lookup = lookup;
        ctx.maximumTraversal = c.maximumSteps;
        uint32_t v = 0;
        try {
            if (!claw_ambient_audio_backend_entry(f, t, &arg, 1, &ctx, listCall, this, &v) || ctx.fault) {
                c.fault = ctx.fault ? ctx.fault : 1;
                throw Failed{};
            }
        } catch (Failed &) {
            throw;
        }
        return v;
    }
    uint32_t com(uint32_t token, uint32_t off, std::initializer_list<uint32_t> a = {}, uint32_t *buffer = nullptr,
                 uint32_t size = 0, uint32_t localMask = 0) {
        ClawPaletteResourceCall q{};
        q.function = vt(token, off);
        q.argumentCount = uint32_t(a.size()) + 1;
        q.arguments[0] = token;
        std::copy(a.begin(), a.end(), q.arguments + 1);
        q.localMask = localMask;
        if (buffer) {
            q.bufferCount = 1;
            q.buffers[0] = buffer;
            q.bufferBytes[0] = size;
        }
        return external(q);
    }
    uint32_t backend() {
        uint32_t p = alloc(56);
        if (p)
            for (uint32_t off : {4u, 0u, 8u, 12u, 16u, 52u, 24u, 20u, 44u, 48u})
                put(p + off, 0);
        return p;
    }
    uint32_t create(uint32_t t, uint32_t device, uint32_t entries, uint32_t flags, uint32_t *local = nullptr) {
        uint32_t data = alloc(1024);
        put(t + 12, data);
        for (uint32_t i = 0; i < 256; ++i) {
            next();
            put(get(t + 12) + i * 4, local ? local[i] : get(entries + i * 4));
        }
        put(t + 16, alloc(1024));
        uint32_t hr = com(device, 20, {flags, local ? 0u : entries, t + 4, 0}, local ? local : span(entries, 256), 1024,
                          local ? 4u : 0u);
        if (!hr)
            return 1;
        external(0x4bd260, 0, {0x532500, 0x4b, hr});
        return 0;
    }
    uint32_t triples(uint32_t t, uint32_t device, uint32_t data, uint32_t flags) {
        uint32_t entries[256];
        for (uint32_t i = 0; i < 256; ++i) {
            next();
            entries[i] = byte(data + i * 3) | byte(data + i * 3 + 1) << 8 | byte(data + i * 3 + 2) << 16;
        }
        return create(t, device, 0, flags, entries);
    }
    uint32_t factory(uint32_t f, uint32_t manager, const uint32_t *a) {
        uint32_t p = backend();
        uint32_t ok = f == 0x4bcbc0   ? invoke(0x4bb5a0, p, {get(manager), a[0], a[1], a[2]})
                      : f == 0x4bcac0 ? invoke(0x4bb240, p, {get(manager), a[0], a[1]})
                                      : invoke(0x4bb100, p, {get(manager), a[0], a[1]});
        if (!ok) {
            if (p) {
                destroy(p);
                free(p);
            }
            return 0;
        }
        invoke(0x4bc9b0, manager, {p});
        return p;
    }
    void destroy(uint32_t t) {
        put(t + 4, 0);
        put(t, 0);
        put(t + 8, 0);
        for (uint32_t off : {12u, 16u, 24u}) {
            uint32_t p = get(t + off);
            if (p) {
                free(p);
                put(t + off, 0);
            }
        }
        put(t + 52, 0);
    }
    void release(uint32_t t) {
        uint32_t p = get(t + 16);
        if (p) {
            invoke(0x4bca10, get(get(t + 12) + 28), {p});
            put(t + 16, 0);
        }
    }
    uint32_t wrapper(uint32_t manager) {
        uint32_t p = alloc(20);
        if (p) {
            put(p + 4, get(manager + 28));
            put(p + 8, 0);
            put(p + 12, get(manager + 12));
            put(p, 0x513d78);
            put(p + 16, 0);
        }
        return p;
    }
    uint32_t registerName(uint32_t manager, uint32_t name, uint32_t object, bool local) {
        uint32_t storage[20];
        auto *text = reinterpret_cast<uint8_t *>(storage);
        uint32_t n = 0;
        do {
            next();
            if (n >= (local ? 80u : 4096u)) {
                c.fault = 2;
                throw Failed{};
            }
            if (local)
                text[n] = uint8_t(byte(name + n));
        } while (byte(name + n++));
        ClawPaletteResourceCall q{};
        q.function = 0x4f62a8;
        q.receiver = manager + 16;
        q.argumentCount = 1;
        q.arguments[0] = local ? 0u : name;
        q.localMask = local ? 1u : 0u;
        q.bufferCount = 1;
        q.buffers[0] = local ? storage : reinterpret_cast<uint32_t *>(bytes(name, n));
        q.bufferBytes[0] = n;
        uint32_t slot = external(q);
        put(slot, object);
        return object;
    }
    uint32_t resourceFactory(uint32_t f, uint32_t manager, const uint32_t *a) {
        uint32_t data = a[0];
        if (f == 0x4d4420) {
            data = external(0x4b61c0, a[0]);
            if (!data)
                return 0;
        }
        uint32_t p = wrapper(manager);
        uint32_t ok = invoke(vt(p, f == 0x4d4570 ? 44 : 40), p, {data, a[2]});
        if (f == 0x4d4420)
            external(0x4b6230, a[0]);
        if (!ok) {
            if (p)
                invoke(vt(p, 4), p, {1});
            return 0;
        }
        uint32_t name = a[1];
        if (!name && f == 0x4d4420)
            name = get(a[0]);
        return registerName(manager, name, p, f == 0x4d4420);
    }
    uint32_t loadWrapper(uint32_t f, uint32_t t, const uint32_t *a) {
        uint32_t manager = get(get(t + 12) + 28);
        uint32_t p = f == 0x4d6620   ? invoke(0x4bcbc0, manager, {a[0], a[1], 0x44})
                     : f == 0x4d65e0 ? invoke(0x4bcb40, manager, {a[0], 0x44})
                                     : invoke(0x4bcac0, manager, {a[0], 0x44});
        put(t + 16, p);
        if (!p)
            return 0;
        uint32_t flags = a[f == 0x4d6620 ? 2 : 1];
        if (flags & 1) {
            put(t + 8, get(t + 8) | 1);
            invoke(0x4bbf60, p, {});
        }
        return 1;
    }
    uint32_t setEntries(uint32_t t, const uint32_t *a) {
        uint32_t start = a[0], count = a[1], entries = a[2], end = start + count;
        if (start < end)
            for (uint32_t i = 0; i < count; ++i) {
                next();
                put(get(t + 12) + (start + i) * 4, get(entries + i * 4));
            }
        if (!c.globals) {
            c.fault = 1;
            throw Failed{};
        }
        uint32_t holder = c.globals->cooperativeHolder;
        if (holder) {
            uint32_t dd = get(holder);
            com(dd, 0x58, {1, 0});
        }
        return com(get(t + 4), 24, {0, start, count, entries}, count ? span(entries, count) : nullptr, count * 4);
    }
    uint32_t getEntries(uint32_t t) {
        uint32_t p = get(t + 16);
        if (!p) {
            p = alloc(1024);
            put(t + 16, p);
            if (!p)
                return 0;
        }
        uint32_t hr = com(get(t + 4), 16, {0, 0, 256, p}, span(p, 256), 1024);
        if (hr)
            external(0x4bd260, 0, {0x532500, 0x261, hr});
        return 0;
    }
    uint32_t fill(uint32_t t, const uint32_t *a) {
        uint32_t end = a[0] + a[1];
        for (uint32_t i = a[0]; si(i) < si(end); ++i) {
            next();
            for (uint32_t k = 0; k < 3; ++k)
                byte(get(t + 12) + i * 4 + k, a[2 + k]);
        }
        uint32_t p = get(t + 12) + a[0] * 4;
        uint32_t hr = com(get(t + 4), 24, {a[5], a[0], a[1], p}, a[1] ? span(p, a[1]) : nullptr, a[1] * 4);
        if (hr)
            external(0x4bd260, 0, {0x532500, 0x29f, hr});
        return hr;
    }
    uint32_t fade(uint32_t t, const uint32_t *a) {
        uint32_t p = get(t + 12);
        uint32_t hr = com(get(t + 4), 16, {0, 0, 256, p}, span(p, 256), 1024);
        if (hr)
            external(0x4bd260, 0, {0x532500, 700, hr});
        uint32_t saved = alloc(1024);
        for (uint32_t i = 0; i < 256; ++i)
            put(saved + i * 4, get(get(t + 12) + i * 4));
        uint32_t begin = external(0x546df0, 0, {}), elapsed = 10, previous = 9;
        while (elapsed < a[5]) {
            next();
            if (elapsed != previous) {
                uint32_t end = a[0] + a[1];
                for (uint32_t i = a[0]; si(i) < si(end); ++i) {
                    next();
                    for (uint32_t k = 0; k < 3; ++k) {
                        uint32_t old = byte(saved + i * 4 + k);
                        int32_t divisor = si(a[5]);
                        if (!divisor) {
                            c.fault = 2;
                            throw Failed{};
                        }
                        int32_t product = si((uint32_t(uint8_t(a[k + 2])) - old) * elapsed);
                        if (product == int32_t(0x80000000) && divisor == -1) {
                            c.fault = 2;
                            throw Failed{};
                        }
                        int32_t scaled = product / divisor;
                        byte(get(t + 12) + i * 4 + k, uint32_t(scaled) + old);
                    }
                }
                uint32_t dst = get(t + 12) + a[0] * 4;
                com(get(t + 4), 24, {0, a[0], a[1], dst}, a[1] ? span(dst, a[1]) : nullptr, a[1] * 4);
            }
            previous = elapsed;
            elapsed = external(0x546df0, 0, {}) - begin;
        }
        uint32_t args[6] = {a[0], a[1], a[2], a[3], a[4], 0};
        fill(t, args);
        free(saved);
        return 0;
    }
    uint32_t systemPalette(uint32_t t) {
        uint32_t dc = external(0x546910, 0, {0x53251c, 0, 0, 0});
        if (!dc)
            return 0;
        uint32_t size = external(0x546894, 0, {dc, 104});
        int32_t half = si(external(0x546894, 0, {dc, 106})) / 2;
        if (half < 0 || half > 256 || size > 256 || size < uint32_t(half)) {
            c.fault = 2;
            throw Failed{};
        }
        if (!c.systemPaletteScratchToken) {
            c.fault = 1;
            throw Failed{};
        }
        auto getSystem = [&](uint32_t start, uint32_t at) {
            ClawPaletteResourceCall q{};
            q.function = 0x546914;
            q.argumentCount = 4;
            q.arguments[0] = dc;
            q.arguments[1] = start;
            q.arguments[2] = uint32_t(half);
            q.localMask = 8;
            q.bufferCount = 1;
            q.buffers[0] = span(c.systemPaletteScratchToken + at * 4, uint32_t(half));
            q.bufferBytes[0] = uint32_t(half) * 4;
            return external(q);
        };
        if (!getSystem(0, 0))
            return 0;
        uint32_t start = size - uint32_t(half);
        if (!getSystem(start, 256 - uint32_t(half)))
            return 0;
        external(0x5468b0, 0, {dc});
        uint32_t data = get(t + 12);
        if (!data)
            return 0;
        for (uint32_t i = 0; i < uint32_t(half); ++i)
            for (uint32_t k = 0; k < 3; ++k)
                byte(data + i * 4 + k, byte(c.systemPaletteScratchToken + i * 4 + k));
        for (uint32_t i = start; si(i) < si(size); ++i)
            for (uint32_t k = 0; k < 3; ++k)
                byte(data + i * 4 + k, byte(c.systemPaletteScratchToken + i * 4 + k));
        uint32_t args[] = {0, 256, data, 0};
        uint32_t hr = setEntries(t, args);
        if (!hr)
            return 1;
        external(0x4bd260, 0, {0x532500, 0x491, hr});
        return 0;
    }
    uint32_t invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a) {
        uint32_t args[8]{};
        std::copy(a.begin(), a.end(), args);
        return invoke(f, t, args, uint32_t(a.size()));
    }
    uint32_t invoke(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        switch (f) {
        case 0x4bcac0:
        case 0x4bcbc0:
        case 0x4bcb40:
            return factory(f, t, a);
        case 0x4bb240:
            return triples(t, a[0], a[1], a[2]);
        case 0x4bb5a0:
            if (a[2] < 768)
                return 0;
            return triples(t, a[0], a[1] + a[2] - 768, a[3]);
        case 0x4bb100:
            return create(t, a[0], a[1], a[2]);
        case 0x4bc9b0: {
            uint32_t node = list(0x4f51c5, t + 0x3d4, a[0]);
            put(a[0], node);
            return 0;
        }
        case 0x4bca10:
            list(0x4f5212, t + 0x3d4, get(a[0]));
            if (a[0]) {
                destroy(a[0]);
                free(a[0]);
            }
            return 0;
        case 0x4bb2a0:
            destroy(t);
            return 0;
        case 0x4d65a0:
        case 0x4d65e0:
        case 0x4d6620:
            return loadWrapper(f, t, a);
        case 0x4d4420:
        case 0x4d44f0:
        case 0x4d4570:
            return resourceFactory(f, t, a);
        case 0x4d6670:
            release(t);
            return 0;
        case 0x4d4810:
            put(t, 0x513d78);
            release(t);
            put(t + 4, 0xffffffff);
            put(t + 8, 0);
            put(t + 12, 0);
            put(t, 0x50becc);
            return 0;
        case 0x4d47f0:
            invoke(0x4d4810, t, {});
            if (a[0] & 1)
                free(t);
            return t;
        case 0x4bb800:
            return setEntries(t, a);
        case 0x4bb870:
            return getEntries(t);
        case 0x4bb910:
            return fill(t, a);
        case 0x4bb990:
            return fade(t, a);
        case 0x4bbf60:
            return systemPalette(t);
        case 0x4b96f0: {
            uint32_t hr = com(get(t + 8), 0x7c, {get(a[0] + 4)});
            if (!hr)
                return 1;
            external(0x4bd260, 0, {0x5324dc, 0x1b8, hr});
            return 0;
        }
        case 0x4d6690: {
            uint32_t target = get(get(get(t + 12) + 4) + 16);
            if (get(target + 24) != 8)
                return 1;
            return invoke(0x4b96f0, get(target + 44), {get(t + 16), 0});
        }
        default: {
            ClawPaletteResourceCall q{};
            q.function = f;
            q.receiver = t;
            q.argumentCount = n;
            std::copy_n(a, n, q.arguments);
            return external(q);
        }
        }
    }
};
bool supported(uint32_t f, uint32_t &n) {
    n = 0;
    switch (f) {
    case 0x4bb2a0:
    case 0x4d4810:
    case 0x4d6670:
    case 0x4d6690:
    case 0x4bb870:
    case 0x4bbf60:
        return true;
    case 0x4bc9b0:
    case 0x4bca10:
    case 0x4d47f0:
        n = 1;
        return true;
    case 0x4bcac0:
    case 0x4bcb40:
    case 0x4d65a0:
    case 0x4d65e0:
    case 0x4b96f0:
        n = 2;
        return true;
    case 0x4d6620:
    case 0x4d4420:
    case 0x4d44f0:
    case 0x4d4570:
    case 0x4bcbc0:
    case 0x4bb100:
    case 0x4bb240:
        n = 3;
        return true;
    case 0x4bb5a0:
    case 0x4bb800:
        n = 4;
        return true;
    case 0x4bb910:
    case 0x4bb990:
        n = 6;
        return true;
    default:
        return false;
    }
}
} // namespace
extern "C" void claw_palette_resource_defaults(ClawPaletteResourceContext *c) {
    if (c) {
        c->composeLists = 1;
        c->maximumSteps = 1000000;
    }
}
extern "C" uint32_t claw_palette_resource_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                ClawPaletteResourceContext *c, ClawPaletteResourceDependency d, void *u,
                                                uint32_t *result) {
    uint32_t required;
    if (!supported(f, required))
        return 0;
    if (result)
        *result = 0;
    if (!c)
        return 1;
    c->fault = 0;
    if (n != required || (n && !a)) {
        c->fault = 2;
        return 1;
    }
    Run r{*c, d, u};
    uint32_t value = 0;
    try {
        value = r.invoke(f, t, a, n);
    } catch (Failed &) {
        if (!c->fault)
            c->fault = 2;
    }
    if (result)
        *result = value;
    return 1;
}
extern "C" uint32_t claw_palette_resource_capture_owner(uint32_t owner, ClawPaletteResourceContext *c,
                                                        ClawPaletteResourceDependency d, void *u, uint32_t *result) {
    if (result)
        *result = 0;
    if (!c)
        return 0;
    c->fault = 0;
    Run r{*c, d, u};
    try {
        uint32_t palette = r.get(r.get(owner + 44) + 16);
        uint32_t hr = r.com(r.get(palette + 4), 16, {0, 0, 256, owner + 864}, r.span(owner + 864, 256), 1024);
        if (result)
            *result = hr;
    } catch (Failed &) {
        return 0;
    }
    return c->fault ? 0 : 1;
}
