#include "WorldFileRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawWorldFileContext *c;
    ClawWorldFileDependency dependency;
    void *user;
    uint32_t visits = 0;
};
void fail(Run &r, uint32_t n = 1) {
    r.c->fault = n;
}
int32_t signedWord(uint32_t v) {
    int32_t x;
    std::memcpy(&x, &v, 4);
    return x;
}
uint32_t *span(Run &r, uint32_t token, uint32_t count) {
    auto *p = r.c->scene.lookup ? r.c->scene.lookup(r.c->scene.context, token, count) : nullptr;
    if (!p)
        fail(r);
    return p;
}
uint8_t *bytes(Run &r, uint32_t token, uint32_t count) {
    uint32_t offset = token & 3;
    auto *p = span(r, token & ~3u, (count + offset + 3) / 4);
    return p ? reinterpret_cast<uint8_t *>(p) + offset : nullptr;
}
uint32_t word(Run &r, uint32_t token) {
    auto *p = bytes(r, token, 4);
    uint32_t value = 0;
    if (p)
        std::memcpy(&value, p, 4);
    return value;
}
bool limit(Run &r) {
    if (++r.visits > 1000000) {
        fail(r, 2);
        return false;
    }
    return !r.c->fault;
}
uint32_t call(Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {},
              const char *name = nullptr, uint32_t *size = nullptr, uint32_t *temporary = nullptr) {
    if (r.c->fault)
        return 0;
    if (!r.dependency) {
        fail(r);
        return 0;
    }
    ClawWorldFileCall c{};
    c.function = f;
    c.receiver = receiver;
    c.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), c.arguments);
    c.name = name;
    c.size = size;
    c.temporary = temporary;
    return r.dependency(r.c, &c, r.user);
}
uint32_t allocate(Run &r, uint32_t bytes) {
    if (!r.c->scene.allocate) {
        fail(r);
        return 0;
    }
    return r.c->scene.allocate(r.c->scene.context, bytes);
}
void release(Run &r, uint32_t token) {
    if (!r.c->scene.free) {
        fail(r);
        return;
    }
    r.c->scene.free(r.c->scene.context, token);
}
uint32_t vt(Run &r, uint32_t t, uint32_t offset) {
    uint32_t v = word(r, t);
    if (r.c->fault)
        return 0;
    switch (v) {
    case 0x513938:
        if (offset == 4)
            return 0x4cdd10;
        if (offset == 0x38)
            return 0x4cb200;
        if (offset == 0x44)
            return 0x4cb5f0;
        break;
    case 0x513980:
        if (offset == 4)
            return 0x4d5330;
        if (offset == 0x14)
            return 0x4d5840;
        if (offset == 0x24)
            return 0x4cde00;
        break;
    case 0x5139c8:
        if (offset == 4)
            return 0x4d5330;
        if (offset == 0x14)
            return 0x4d5c30;
        if (offset == 0x24)
            return 0x4cde40;
        break;
    case 0x513a10:
        if (offset == 4)
            return 0x4cde70;
        if (offset == 0x14)
            return 0x4d5870;
        if (offset == 0x24)
            return 0x4cdf10;
        break;
    case 0x513d40:
        if (offset == 4)
            return 0x4d2210;
        break;
    default:
        break;
    }
    return word(r, v + offset);
}
uint32_t entry(Run &, uint32_t, uint32_t, const uint32_t *);
bool supported(uint32_t f) {
    switch (f) {
    case 0x4cdd10:
    case 0x4cdd30:
    case 0x4d2210:
    case 0x4d2230:
    case 0x4d0a00:
    case 0x4f58de:
    case 0x4cb200:
    case 0x4cd660:
    case 0x4cb180:
    case 0x4cb5f0:
    case 0x4cace0:
    case 0x4cb700:
    case 0x4d5840:
    case 0x4d5c30:
    case 0x4d5870:
    case 0x4cde00:
    case 0x4cde40:
    case 0x4cdf10:
    case 0x4cde70:
    case 0x4cde90:
    case 0x4d5330:
    case 0x423f00:
    case 0x4cb470:
    case 0x4cb5a0:
        return true;
    default:
        return false;
    }
}
uint32_t invoke(Run &r, uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
    uint32_t args[4]{};
    std::copy(a.begin(), a.end(), args);
    return supported(f) ? entry(r, f, t, args) : call(r, f, t, a);
}
uint32_t arrayDependency(ClawCArrayContext *, const ClawCArrayCall *c, void *user) {
    auto &r = *static_cast<Run *>(user);
    if (c->function == 0x4f63ec)
        return allocate(r, c->arguments[0]);
    if (c->function == 0x4f6428) {
        release(r, c->arguments[0]);
        return 0;
    }
    switch (c->argumentCount) {
    case 0:
        return call(r, c->function, c->receiver);
    case 1:
        return call(r, c->function, c->receiver, {c->arguments[0]});
    case 2:
        return call(r, c->function, c->receiver, {c->arguments[0], c->arguments[1]});
    default:
        return call(r, c->function, c->receiver, {c->arguments[0], c->arguments[1], c->arguments[2]});
    }
}
uint32_t array(Run &r, uint32_t f, uint32_t t, uint32_t a = 0, uint32_t b = 0) {
    if (!r.c->arrays)
        return call(r, f, t, f == 0x4f58ab ? std::initializer_list<uint32_t>{} : std::initializer_list<uint32_t>{a, b});
    auto &ctx = *r.c->arrays;
    ctx.scene = r.c->scene;
    uint32_t result = 0;
    if (!claw_carray_entry(f, t, a, b, 0, &ctx, arrayDependency, &r, &result))
        fail(r, 2);
    if (ctx.fault)
        r.c->fault = ctx.fault;
    return result;
}
uint32_t spatialCall(void *user, ClawSceneActorCall c) {
    auto &r = *static_cast<Run *>(user);
    switch (c.argumentCount) {
    case 0:
        return call(r, c.function, c.receiver);
    case 1:
        return call(r, c.function, c.receiver, {c.arguments[0]});
    case 2:
        return call(r, c.function, c.receiver, {c.arguments[0], c.arguments[1]});
    case 3:
        return call(r, c.function, c.receiver, {c.arguments[0], c.arguments[1], c.arguments[2]});
    default:
        return call(r, c.function, c.receiver, {c.arguments[0], c.arguments[1], c.arguments[2], c.arguments[3]});
    }
}
uint32_t *spatialLookup(void *u, uint32_t token, uint32_t n) {
    auto &r = *static_cast<Run *>(u);
    return span(r, token, n);
}
uint32_t spatialAllocate(void *u, uint32_t n) {
    return allocate(*static_cast<Run *>(u), n);
}
void spatialFree(void *u, uint32_t n) {
    release(*static_cast<Run *>(u), n);
}
uint32_t spatial(Run &r, uint32_t f, uint32_t t, std::initializer_list<uint32_t> args = {}) {
    ClawSceneActorHost host = r.c->scene;
    host.context = &r;
    host.lookup = spatialLookup;
    host.allocate = spatialAllocate;
    host.free = spatialFree;
    host.call = spatialCall;
    ClawSpatialGridArguments a{};
    a.count = uint32_t(args.size());
    std::copy(args.begin(), args.end(), a.words);
    uint32_t value = 0;
    if (!claw_spatial_grid_entry(f, t, a, host, &r.c->fault, &value))
        fail(r, 2);
    return value;
}
uint32_t planeDependency(ClawWorldPlaneContext *, const ClawWorldPlaneCall *c, void *u) {
    auto &r = *static_cast<Run *>(u);
    if (c->function == 0x4d2210)
        return invoke(r, c->function, c->receiver, {c->arguments[0]});
    if (c->function == 0x4f582f)
        return array(r, c->function, c->receiver, c->arguments[0], c->arguments[1]);
    if (c->function == 0x4d1620 && r.c->composeSpatial) {
        ClawSceneActorHost host = r.c->scene;
        host.context = &r;
        host.lookup = spatialLookup;
        host.allocate = spatialAllocate;
        host.free = spatialFree;
        host.call = spatialCall;
        ClawSpatialGridArguments a{};
        a.count = c->argumentCount;
        std::copy_n(c->arguments, c->argumentCount, a.words);
        uint32_t value = 0;
        claw_spatial_grid_entry(c->function, c->receiver, a, host, &r.c->fault, &value);
        return value;
    }
    if (c->name)
        return call(r, c->function, c->receiver, {}, c->name);
    switch (c->argumentCount) {
    case 0:
        return call(r, c->function, c->receiver);
    case 1:
        return call(r, c->function, c->receiver, {c->arguments[0]});
    case 2:
        return call(r, c->function, c->receiver, {c->arguments[0], c->arguments[1]});
    default:
        return call(r, c->function, c->receiver, {c->arguments[0], c->arguments[1], c->arguments[2]});
    }
}
void clamp(Run &r, uint32_t token) {
    ClawSceneCameraGlobals g{};
    ClawSceneCameraHost h{};
    h.heap = r.c->scene;
    uint32_t result = 0;
    claw_scene_camera_entry(0x4d0a60, token, 0, 0, &g, h, &r.c->fault, &result);
}
void center(Run &r, uint32_t plane, uint32_t x, uint32_t y) {
    auto *p = span(r, plane, 86);
    if (!p)
        return;
    double fx = double(signedWord(x)), fy = double(signedWord(y));
    if (!(p[2] & 1)) {
        float scaleX, scaleY;
        std::memcpy(&scaleX, p + 6, 4);
        std::memcpy(&scaleY, p + 7, 4);
        volatile double xx = fx * double(scaleX), yy = fy * double(scaleY);
        fx = xx;
        fy = yy;
    }
    const float outX = float(fx), outY = float(fy);
    std::memcpy(p + 4, &outX, 4);
    std::memcpy(p + 5, &outY, 4);
    clamp(r, plane);
}
void clear(Run &r, uint32_t token, bool resetViewport) {
    auto *w = span(r, token, 56);
    if (!w)
        return;
    for (uint32_t offset : {0x34u, 0x48u}) {
        uint32_t i = 0;
        while (signedWord(i) < signedWord(w[(offset + 8) / 4]) && limit(r)) {
            uint32_t object = word(r, w[(offset + 4) / 4] + i * 4);
            if (r.c->fault)
                return;
            if (object)
                invoke(r, vt(r, object, 4), object, {1});
            if (r.c->fault)
                return;
            ++i;
        }
        array(r, 0x4f5915, token + offset, 0, 0xffffffff);
        if (r.c->fault)
            return;
    }
    if (resetViewport)
        w[4] = 0x80000000;
    w[23] = 0;
    w[24] = 0xffffffff;
}
uint32_t decode(Run &r, uint32_t source, uint32_t destination, uint32_t capacity) {
    if (!source || !destination)
        return 0;
    auto *h = span(r, source, 188);
    if (!h)
        return 0;
    const uint32_t header = h[0], declared = h[186];
    if (header > 0x5f4 || !(h[2] & 2) || !declared || capacity + header < declared)
        return 0;
    if (header > 0x4000000 || capacity < header) {
        fail(r, 2);
        return 0;
    }
    auto *output = span(r, destination, (header + 3) / 4);
    if (!output)
        return 0;
    auto *input = bytes(r, source, header);
    if (!input)
        return 0;
    std::memmove(output, input, header);
    uint32_t size = capacity - header;
    const uint32_t result = call(r, 0x4d5fe0, 0, {destination + header, 0, source + header, declared}, nullptr, &size);
    if (result)
        return 0;
    return size == h[186] ? destination : 0;
}
uint32_t load(Run &r, uint32_t receiver, uint32_t input) {
    invoke(r, vt(r, receiver, 0x44), receiver);
    if (r.c->fault)
        return 0;
    auto *h = span(r, input, 188);
    auto *w = span(r, receiver, 56);
    if (!h || !w)
        return 0;
    if (h[0] > 0x5f4)
        return 0;
    uint32_t decoded = input, allocated = 0;
    if (h[2] & 2) {
        uint32_t capacity = h[186] + 32 + h[0];
        if (uint64_t(h[186]) + h[0] + 64 > 0x4000000) {
            fail(r, 2);
            return 0;
        }
        allocated = allocate(r, capacity + 32);
        if (!allocated)
            return 0;
        decoded = decode(r, input, allocated, capacity);
        if (!decoded) {
            release(r, allocated);
            return 0;
        }
    }
    // Original name, flags, checksum/start metadata come from the input header.
    uint32_t n = 0;
    for (; n < 64; ++n) {
        auto *source = span(r, (input + 16 + n) & ~3u, 1);
        auto *destination = span(r, (receiver + 0x6c + n) & ~3u, 1);
        if (!source || !destination)
            return 0;
        uint8_t b = reinterpret_cast<uint8_t *>(source)[(input + 16 + n) & 3];
        reinterpret_cast<uint8_t *>(destination)[(receiver + 0x6c + n) & 3] = b;
        if (!b)
            break;
    }
    if (n == 64) {
        fail(r, 2);
        return 0;
    }
    w[2] = h[2];
    w[43] = h[187];
    uint32_t at = decoded + h[184];
    for (uint32_t i = 0; i < h[183] && limit(r); ++i) {
        ClawWorldPlaneContext p{};
        p.scene = r.c->scene;
        if (!claw_world_plane_add(receiver, at, decoded, receiver + 0x10, &p, planeDependency, &r)) {
            if (p.fault)
                r.c->fault = p.fault;
            if (allocated)
                release(r, allocated);
            return 0;
        }
        if (p.fault) {
            r.c->fault = p.fault;
            return 0;
        }
        at += 160;
    }
    if (h[185]) {
        uint32_t table = decoded + h[185], record = table + 32;
        uint32_t done = 0;
        if (!record || !table)
            done = 0xffffffff;
        else
            for (uint32_t i = 0; i < word(r, table + 8) && limit(r); ++i) {
                uint32_t description = invoke(r, 0x4cb700, receiver, {record});
                if (!description) {
                    done = 0xffffffff;
                    break;
                }
                ++done;
                record += invoke(r, vt(r, description, 0x24), description);
                array(r, 0x4f582f, receiver + 0x48, i, description);
                if (r.c->fault)
                    return 0;
            }
        if (signedWord(done) < 0) {
            if (allocated)
                release(r, allocated);
            return 0;
        }
    }
    center(r, w[23], h[180], h[181]);
    if (r.c->fault)
        return 0;
    auto *main = span(r, w[23], 86);
    if (!main)
        return 0;
    const uint32_t x = main[33], y = main[34];
    for (uint32_t i = 0; signedWord(i) < signedWord(w[15]) && limit(r); ++i)
        if (i != w[24]) {
            center(r, word(r, w[14] + i * 4), x, y);
            if (r.c->fault)
                return 0;
        }
    if (allocated)
        release(r, allocated);
    return r.c->fault ? 0 : 1;
}
uint32_t entry(Run &r, uint32_t f, uint32_t token, const uint32_t *a) {
    if (f == 0x4cdd30) {
        auto *w = span(r, token, 56);
        if (!w)
            return 0;
        w[0] = 0x513938;
        invoke(r, 0x4cb180, token);
        for (uint32_t offset : {0x48u, 0x34u, 0x20u})
            invoke(r, 0x4f58de, token + offset);
        w[1] = 0xffffffff;
        w[2] = w[3] = 0;
        w[0] = 0x50becc;
        return 0;
    }
    if (f == 0x4cdd10) {
        invoke(r, 0x4cdd30, token);
        if (a[0] & 1)
            release(r, token);
        return token;
    }
    if (f == 0x4f58de) {
        auto *a = span(r, token, 5);
        if (!a)
            return 0;
        a[0] = 0x5108fc;
        release(r, a[1]);
        a[0] = 0x50becc;
        return 0;
    }
    if (f == 0x4d0a00) {
        auto *p = span(r, token, 86);
        if (!p)
            return 0;
        if (p[44])
            spatial(r, 0x4d50e0, p[44]);
        if (p[44]) {
            spatial(r, 0x4d4b00, p[44]);
            release(r, p[44]);
        }
        if (p[8]) {
            release(r, p[8]);
            p[8] = 0;
        }
        if (p[9]) {
            release(r, p[9]);
            p[9] = 0;
        }
        return 0;
    }
    if (f == 0x4d2230) {
        auto *p = span(r, token, 86);
        if (!p)
            return 0;
        p[0] = 0x513d40;
        invoke(r, 0x4d0a00, token);
        invoke(r, 0x4f58de, token + 0x9c);
        p[1] = 0xffffffff;
        p[2] = p[3] = 0;
        p[0] = 0x50becc;
        return 0;
    }
    if (f == 0x4d2210) {
        invoke(r, 0x4d2230, token);
        if (a[0] & 1)
            release(r, token);
        return token;
    }
    if (f == 0x4cb200)
        return load(r, token, a[0]);
    if (f == 0x4cd660)
        return decode(r, a[0], a[1], a[2]);
    if (f == 0x4cb180 || f == 0x4cb5f0) {
        clear(r, token, f == 0x4cb180);
        return 0;
    }
    if (f == 0x4cace0) {
        auto *w = span(r, token, 56);
        if (!w)
            return 0;
        w[0] = 0x50e924;
        w[1] = a[1];
        w[2] = a[2];
        w[3] = a[0];
        for (uint32_t offset : {0x20u, 0x34u, 0x48u})
            array(r, 0x4f58ab, token + offset);
        w[25] = w[26] = 64;
        w[0] = 0x513938;
        w[4] = 0x80000000;
        w[23] = 0;
        w[24] = 0xffffffff;
        w[43] = 0;
        constexpr uint32_t defaults[] = {500, 250, 1000, 1000, 250, 125, 1600, 1200, 2560, 1920, 768, 576};
        std::copy_n(defaults, 12, w + 44);
        return token;
    }
    if (f == 0x4d5840 || f == 0x4d5c30) {
        const uint32_t count = f == 0x4d5840 ? 3 : 8;
        auto *out = span(r, token + 4, count);
        if (!out)
            return 0;
        for (uint32_t i = 0; i < count; ++i)
            out[i] = word(r, a[0] + 8 + i * 4);
        return r.c->fault ? 0 : 1;
    }
    if (f == 0x4d5870) {
        auto *p = span(r, token, 6);
        if (!p)
            return 0;
        p[1] = word(r, a[0] + 8);
        p[2] = word(r, a[0] + 12);
        if (r.c->fault)
            return 0;
        p[3] = 0;
        p[4] = p[1] * p[2];
        for (uint32_t h = p[2]; signedWord(h) > 1; h = uint32_t(signedWord(h) >> 1))
            ++p[3];
        if ((1u << (p[3] & 31)) != p[1])
            return 0;
        if (p[4] > 0x4000000) {
            fail(r, 2);
            return 0;
        }
        p[5] = allocate(r, p[4]);
        if (!p[5])
            return 0;
        auto *output = span(r, p[5], (p[4] + 3) / 4);
        auto *input = bytes(r, a[0] + 16, p[4]);
        if (!output || !input)
            return 0;
        std::memcpy(output, input, p[4]);
        return 1;
    }
    if (f == 0x4cde00)
        return 20;
    if (f == 0x4cde40)
        return 40;
    if (f == 0x4cdf10) {
        auto *p = span(r, token, 3);
        return p ? p[1] * p[2] + 16 : 0;
    }
    if (f == 0x4cb700) {
        if (!a[0])
            return 0;
        uint32_t kind = word(r, a[0]);
        if (kind < 1 || kind > 3)
            return 0;
        uint32_t bytes = kind == 1 ? 16 : kind == 2 ? 36 : 24;
        uint32_t object = allocate(r, bytes);
        if (!object) {
            fail(r, 2);
            return 0;
        }
        auto *p = span(r, object, bytes / 4);
        if (!p)
            return 0;
        p[0] = kind == 1 ? 0x513980 : kind == 2 ? 0x5139c8 : 0x513a10;
        p[1] = 0;
        if (kind == 3)
            p[5] = 0;
        if (!invoke(r, vt(r, object, 0x14), object, {a[0]})) {
            invoke(r, vt(r, object, 4), object, {1});
            return 0;
        }
        return object;
    }
    if (f == 0x423f00) {
        auto *p = span(r, token, 1);
        if (p)
            *p = 0x50becc;
        return 0;
    }
    if (f == 0x4cde90) {
        auto *p = span(r, token, 6);
        if (!p)
            return 0;
        p[0] = 0x513a10;
        if (p[5])
            release(r, p[5]);
        p[5] = 0;
        p[0] = 0x50becc;
        return 0;
    }
    if (f == 0x4d5330 || f == 0x4cde70) {
        invoke(r, f == 0x4d5330 ? 0x423f00 : 0x4cde90, token);
        if (a[0] & 1)
            release(r, token);
        return token;
    }
    if (f == 0x4cb5a0) {
        uint32_t raw = call(r, 0x4b61c0, a[0]);
        if (!raw)
            return 0;
        uint32_t result = invoke(r, vt(r, token, 0x38), token, {raw});
        call(r, 0x4b6230, a[0]);
        return result ? 1 : 0;
    }
    if (f == 0x4cb470) {
        uint32_t file[4]{};
        call(r, 0x4f72c9, 0, {}, nullptr, nullptr, file);
        if (!call(r, 0x4f7448, 0, {a[0], 0, 0}, nullptr, nullptr, file)) {
            call(r, 0x4f7369, 0, {}, nullptr, nullptr, file);
            return 0;
        }
        uint32_t length = call(r, 0x4f774d, 0, {}, nullptr, nullptr, file);
        uint32_t raw = allocate(r, length);
        if (!raw) {
            call(r, 0x4f7369, 0, {}, nullptr, nullptr, file);
            return 0;
        }
        length = call(r, 0x4f774d, 0, {}, nullptr, nullptr, file);
        call(r, 0x4f7570, 0, {raw, length}, nullptr, nullptr, file);
        uint32_t result = invoke(r, vt(r, token, 0x38), token, {raw});
        release(r, raw);
        call(r, 0x4f7369, 0, {}, nullptr, nullptr, file);
        return result ? 1 : 0;
    }
    fail(r, 2);
    return 0;
}
} // namespace
uint32_t claw_world_file_entry(uint32_t function, uint32_t receiver, ClawWorldFileArguments args,
                               ClawWorldFileContext *c, ClawWorldFileDependency dependency, void *user,
                               uint32_t *result) {
    if (!c)
        return 0;
    if (result)
        *result = 0;
    if (!supported(function))
        return 0;
    uint32_t required = 0;
    switch (function) {
    case 0x4cd660:
    case 0x4cace0:
        required = 3;
        break;
    case 0x4cdd10:
    case 0x4d2210:
    case 0x4cb200:
    case 0x4cb700:
    case 0x4d5840:
    case 0x4d5c30:
    case 0x4d5870:
    case 0x4d5330:
    case 0x4cde70:
    case 0x4cb470:
    case 0x4cb5a0:
        required = 1;
        break;
    default:
        break;
    }
    Run r{c, dependency, user};
    if (args.count < required || args.count > 4) {
        fail(r, 2);
        return 0;
    }
    uint32_t value = entry(r, function, receiver, args.words);
    if (result)
        *result = value;
    return !c->fault;
}
