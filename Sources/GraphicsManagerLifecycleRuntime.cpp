#include "GraphicsManagerLifecycleRuntime.h"
#include "AmbientAudioBackendRuntime.h"
#include "CArrayRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failed {};
struct Run;
uint32_t arrayService(ClawCArrayContext *, const ClawCArrayCall *, void *);
uint32_t listService(ClawAmbientAudioBackendContext *, const ClawAmbientAudioBackendCall *, void *);
uint32_t paletteService(ClawPaletteResourceContext *, const ClawPaletteResourceCall *, void *);
struct Run {
    ClawGraphicsManagerLifecycleContext &c;
    ClawGraphicsManagerLifecycleDependency d;
    void *u;
    uint32_t operations = 0;
    static int32_t si(uint32_t x) {
        int32_t y;
        std::memcpy(&y, &x, 4);
        return y;
    }
    void tick() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 1000000)) {
            c.fault = 3;
            throw Failed{};
        }
    }
    uint32_t *p(uint32_t t, uint32_t n = 1) {
        if (c.fault)
            throw Failed{};
        auto *v = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!v) {
            c.fault = 1;
            throw Failed{};
        }
        return v;
    }
    uint32_t get(uint32_t t, uint32_t b = 0) {
        return *p(t + b);
    }
    void set(uint32_t t, uint32_t b, uint32_t x) {
        *p(t + b) = x;
    }
    uint32_t rich(ClawGraphicsManagerLifecycleCall &q) {
        if (c.fault)
            throw Failed{};
        if (d)
            return d(&c, &q, u);
        if (q.argumentCount <= 4 && !q.localMask && c.scene.call) {
            ClawSceneActorCall e{};
            e.function = q.function;
            e.receiver = q.receiver;
            e.argumentCount = q.argumentCount;
            std::copy_n(q.arguments, q.argumentCount, e.arguments);
            return c.scene.call(c.scene.context, e);
        }
        c.fault = 1;
        throw Failed{};
    }
    uint32_t call(uint32_t f, uint32_t r, std::initializer_list<uint32_t> a = {}) {
        ClawGraphicsManagerLifecycleCall q{};
        q.function = f;
        q.receiver = r;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        return rich(q);
    }
    uint32_t com(uint32_t object, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        ClawGraphicsManagerLifecycleCall q{};
        q.function = get(get(object), slot);
        q.argumentCount = uint32_t(a.size() + 1);
        q.arguments[0] = object;
        std::copy(a.begin(), a.end(), q.arguments + 1);
        return rich(q);
    }
    uint32_t localDisplay(uint32_t device, uint32_t *data) {
        ClawGraphicsManagerLifecycleCall q{};
        q.function = get(get(device), 0x30);
        q.argumentCount = 2;
        q.arguments[0] = device;
        q.localMask = 2;
        q.bufferCount = 1;
        q.buffers[0] = data;
        q.bufferBytes[0] = 108;
        return rich(q);
    }
    void diag(uint32_t file, uint32_t line, uint32_t hr) {
        call(0x4bd260, 0, {file, line, hr});
    }
    void array(uint32_t f, uint32_t t, uint32_t a, uint32_t b) {
        ClawCArrayContext x{};
        x.scene = c.scene;
        claw_carray_defaults(&x);
        uint32_t out = 0;
        if (!claw_carray_entry(f, t, a, b, 0, &x, arrayService, this, &out) || x.fault) {
            c.fault = x.fault ? x.fault : 2;
            throw Failed{};
        }
    }
    uint32_t list(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        ClawAmbientAudioBackendContext x{};
        x.scene = c.scene;
        x.maximumTraversal = c.maximumOperations;
        uint32_t out = 0;
        if (!claw_ambient_audio_backend_entry(f, t, a, n, &x, listService, this, &out) || x.fault) {
            c.fault = x.fault ? x.fault : 2;
            throw Failed{};
        }
        return out;
    }
    void palette(uint32_t t) {
        ClawPaletteResourceGlobals globals{c.globals->cooperativeHolder};
        ClawPaletteResourceContext local{};
        local.scene = c.scene;
        local.globals = &globals;
        claw_palette_resource_defaults(&local);
        auto *x = c.palette ? c.palette : &local;
        x->globals->cooperativeHolder = c.globals->cooperativeHolder;
        uint32_t out = 0;
        if (!claw_palette_resource_entry(0x4bb2a0, t, nullptr, 0, x, paletteService, this, &out) || x->fault) {
            c.fault = x->fault ? x->fault : 2;
            throw Failed{};
        }
        c.globals->cooperativeHolder = x->globals->cooperativeHolder;
    }
    void free(uint32_t t) {
        call(0x4f6428, 0, {t});
    }
    void clearModes(uint32_t t) {
        uint32_t i = 0;
        while (si(i) < si(get(t, 8))) {
            tick();
            free(get(get(t, 4), i * 4));
            ++i;
        }
        array(0x4f5915, t, 0, 0xffffffff);
    }
    uint32_t compare(uint32_t a, uint32_t b) {
        for (uint32_t offset : {12u, 8u, 0x54u}) {
            uint32_t x = get(a, offset), y = get(b, offset);
            if (x > y)
                return 1;
            if (x < y)
                return 0;
        }
        return 0;
    }
    uint32_t enumCallback(uint32_t descriptor) {
        uint32_t t = call(0x4f63ec, 0, {108});
        std::memcpy(p(t, 27), p(descriptor, 27), 108);
        array(0x4f582f, 0x541378, get(0x541378, 8), t);
        return 1;
    }
    void enumerate(uint32_t t) {
        clearModes(t + 0x3f0);
        array(0x4f5915, 0x541378, 0, 0xffffffff);
        uint32_t hr = com(get(t), 0x20, {0, 0, 0, 0x4bcda0});
        if (hr)
            diag(0x532524, 0x4a3, hr);
        uint32_t i = 0;
        while (si(i) < si(get(0x541378, 8))) {
            tick();
            array(0x4f582f, t + 0x3f0, get(t, 0x3f8), get(get(0x541378, 4), i * 4));
            ++i;
        }
        array(0x4f5915, 0x541378, 0, 0xffffffff);
        uint32_t count = get(t, 0x3f8);
        for (uint32_t left = 0; si(left) < si(count - 1) && si(count) > 1; ++left) {
            for (uint32_t right = left + 1; si(right) < si(count); ++right) {
                tick();
                uint32_t first = get(get(t, 0x3f4), left * 4), second = get(get(t, 0x3f4), right * 4);
                if (compare(first, second)) {
                    set(get(t, 0x3f4), left * 4, second);
                    set(get(t, 0x3f4), right * 4, first);
                }
            }
        }
    }
    uint32_t format(uint32_t t) {
        uint32_t descriptor[27]{};
        descriptor[0] = 108;
        uint32_t hr = localDisplay(get(t), descriptor);
        if (hr) {
            diag(0x532524, 0x7b8, hr);
            return 0;
        }
        for (uint32_t channel = 0; channel < 3; ++channel) {
            uint32_t mask = descriptor[22 + channel], shift = 0xffffffff, count = 0;
            for (uint32_t bit = 0; bit < 32; ++bit) {
                if (mask & 1) {
                    if (shift == 0xffffffff)
                        shift = bit;
                    ++count;
                }
                mask >>= 1;
            }
            c.globals->channelShift[channel] = shift;
            c.globals->channelReduction[channel] = 8 - count;
        }
        return 1;
    }
    uint32_t mode(uint32_t t, const uint32_t *a) {
        uint32_t hr = com(get(t), 0x54, {a[0], a[1], a[2]});
        if (hr) {
            diag(0x532524, 0x829, hr);
            if (!get(t, 0x880))
                set(t, 0x880, 1004);
            return hr;
        }
        if (!format(t)) {
            hr = 0x80004005;
            if (!get(t, 0x880))
                set(t, 0x880, 1005);
        }
        return hr;
    }
    uint32_t initialize(uint32_t t, const uint32_t *a) {
        set(t, 0x878, 0);
        set(t, 0x87c, 0);
        uint32_t hr;
        if (c.globals->sharedDevice)
            set(t, 0, c.globals->sharedDevice);
        else {
            hr = call(0x546850, 0, {a[1], t, 0});
            if (hr) {
                diag(0x532524, 0x87, hr);
                if (!get(t, 0x880))
                    set(t, 0x880, 1001);
                return 0;
            }
        }
        hr = com(get(t), 0x50, {a[0], a[5]});
        if (hr) {
            diag(0x532534, 0x119, hr);
            if (!get(t, 0x880))
                set(t, 0x880, 1002);
            return 0;
        }
        std::memset(p(t + 4, 79), 0, 316);
        std::memset(p(t + 0x140, 79), 0, 316);
        set(t, 4, 316);
        set(t, 0x140, 316);
        hr = com(get(t), 0x2c, {t + 4, t + 0x140});
        if (hr)
            diag(0x532524, 0xa4, hr);
        set(t, 0x470, get(t, 8) & 0x08000000);
        enumerate(t);
        if (si(a[2]) > 0 && si(a[3]) > 0) {
            uint32_t args[] = {a[2], a[3], a[4]};
            hr = mode(t, args);
            if (hr) {
                diag(0x532524, 0xb9, hr);
                if (!get(t, 0x880))
                    set(t, 0x880, 1004);
                return 0;
            }
            set(t, 0x474, a[4]);
        }
        if (!a[4]) {
            uint32_t descriptor[27]{};
            descriptor[0] = 108;
            if (!localDisplay(get(t), descriptor))
                set(t, 0x474, descriptor[21]);
        }
        c.globals->cooperativeHolder = t;
        return 1;
    }
    void destroySurface(uint32_t t, uint32_t flags) {
        uint32_t f = get(get(t));
        if (f == 0x4bc5f0) {
            uint32_t arg = flags;
            entry(f, t, &arg, 1);
        } else
            call(f, t, {flags});
    }
    void surfaces(uint32_t t) {
        uint32_t node = get(t, 0x3bc);
        while (node) {
            tick();
            uint32_t next = get(node), object = get(node, 8);
            if (object)
                destroySurface(object, 1);
            node = next;
        }
        list(0x4f5172, t + 0x3b8, nullptr, 0);
    }
    void palettes(uint32_t t) {
        uint32_t node = get(t, 0x3d8);
        while (node) {
            tick();
            uint32_t next = get(node), object = get(node, 8);
            if (object) {
                palette(object);
                free(object);
            }
            node = next;
        }
        list(0x4f5172, t + 0x3d4, nullptr, 0);
    }
    void teardown(uint32_t t, uint32_t restore) {
        if (restore && get(t))
            com(get(t), 0x4c);
        clearModes(t + 0x3f0);
        surfaces(t);
        palettes(t);
        c.globals->cooperativeHolder = 0;
        if (get(t)) {
            com(get(t), 8);
            set(t, 0, 0);
        }
        set(t, 0x470, 0);
    }
    void surfaceClear(uint32_t t) {
        uint32_t i = 0;
        while (i < get(t, 0x98)) {
            tick();
            uint32_t child = get(get(t, 0x94), i * 4);
            if (child)
                destroySurface(child, 1);
            ++i;
        }
        array(0x4f5915, t + 0x90, 0, 0xffffffff);
        if (get(t, 8)) {
            if (!(get(t, 0x78) & 1))
                com(get(t, 8), 8);
            set(t, 8, 0);
        }
        set(t, 0xb4, 0);
    }
    void arrayDelete(uint32_t t) {
        set(t, 0, 0x51079c);
        free(get(t, 4));
        set(t, 0, 0x50becc);
    }
    void listDelete(uint32_t t) {
        set(t, 0, 0x51000c);
        list(0x4f5172, t, nullptr, 0);
        set(t, 0, 0x50becc);
    }
    uint32_t entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        auto need = [&](uint32_t k) {
            if (n != k) {
                c.fault = 2;
                throw Failed{};
            }
        };
        switch (f) {
        case 0x4bc220:
            need(6);
            return initialize(t, a);
        case 0x4bc400:
            need(1);
            teardown(t, a[0]);
            return 0;
        case 0x4bc1b0:
            need(0);
            teardown(t, 1);
            arrayDelete(t + 0x3f0);
            listDelete(t + 0x3d4);
            listDelete(t + 0x3b8);
            return 0;
        case 0x4bcc50:
            need(0);
            enumerate(t);
            return 0;
        case 0x4bcda0:
            need(2);
            return enumCallback(a[0]);
        case 0x4bcde0:
            need(2);
            return compare(a[0], a[1]);
        case 0x4bd0c0:
            need(0);
            return format(t);
        case 0x4bd1c0:
            need(3);
            return mode(t, a);
        case 0x4bc4b0:
            need(0);
            surfaces(t);
            return 0;
        case 0x4bc9d0:
            need(0);
            palettes(t);
            return 0;
        case 0x4b9540:
            need(0);
            surfaceClear(t);
            return 0;
        case 0x4bc610:
            need(0);
            set(t, 0, 0x513588);
            surfaceClear(t);
            arrayDelete(t + 0x90);
            return 0;
        case 0x4bc5f0:
            need(1);
            entry(0x4bc610, t, nullptr, 0);
            if (a[0] & 1)
                free(t);
            return t;
        case 0x4f551d:
            need(0);
            arrayDelete(t);
            return 0;
        case 0x4f5192:
            need(0);
            listDelete(t);
            return 0;
        case 0x4bc120:
            need(0);
            {
                uint32_t out = 0;
                if (!claw_graphics_manager_construct(t, c.scene, &c.fault, &out))
                    throw Failed{};
                return out;
            }
        case 0x4bc100:
            need(0);
            arrayDelete(0x541378);
            return 0;
        case 0x4bc0e0:
            need(0);
            {
                uint32_t out = 0;
                if (!claw_graphics_string_array_construct(0x541378, c.scene, &c.fault, &out))
                    throw Failed{};
                return 0;
            }
        default:
            c.fault = 2;
            throw Failed{};
        }
    }
};
uint32_t arrayService(ClawCArrayContext *, const ClawCArrayCall *e, void *v) {
    auto &r = *static_cast<Run *>(v);
    ClawGraphicsManagerLifecycleCall q{};
    q.function = e->function;
    q.receiver = e->receiver;
    q.argumentCount = e->argumentCount;
    std::copy_n(e->arguments, e->argumentCount, q.arguments);
    return r.rich(q);
}
uint32_t listService(ClawAmbientAudioBackendContext *, const ClawAmbientAudioBackendCall *e, void *v) {
    auto &r = *static_cast<Run *>(v);
    ClawGraphicsManagerLifecycleCall q{};
    q.function = e->function;
    q.receiver = e->receiver;
    q.argumentCount = e->argumentCount;
    std::copy_n(e->arguments, e->argumentCount, q.arguments);
    return r.rich(q);
}
uint32_t paletteService(ClawPaletteResourceContext *pc, const ClawPaletteResourceCall *e, void *v) {
    auto &r = *static_cast<Run *>(v);
    ClawGraphicsManagerLifecycleCall q{};
    q.function = e->function;
    q.receiver = e->receiver;
    q.argumentCount = e->argumentCount;
    std::copy_n(e->arguments, e->argumentCount, q.arguments);
    q.localMask = e->localMask;
    q.bufferCount = e->bufferCount;
    for (uint32_t i = 0; i < 2; ++i) {
        q.buffers[i] = e->buffers[i];
        q.bufferBytes[i] = e->bufferBytes[i];
    }
    r.c.globals->cooperativeHolder = pc->globals->cooperativeHolder;
    const uint32_t value = r.rich(q);
    pc->globals->cooperativeHolder = r.c.globals->cooperativeHolder;
    return value;
}
} // namespace
extern "C" uint32_t claw_graphics_manager_lifecycle_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                          ClawGraphicsManagerLifecycleContext *c,
                                                          ClawGraphicsManagerLifecycleDependency d, void *u,
                                                          uint32_t *result) {
    if (!c || !c->globals || !result || (n && !a) || n > 8)
        return 0;
    switch (f) {
    case 0x4bc120:
    case 0x4bc220:
    case 0x4bc400:
    case 0x4bc1b0:
    case 0x4bcc50:
    case 0x4bcda0:
    case 0x4bcde0:
    case 0x4bd0c0:
    case 0x4bd1c0:
    case 0x4bc4b0:
    case 0x4bc9d0:
    case 0x4b9540:
    case 0x4bc610:
    case 0x4bc5f0:
    case 0x4f551d:
    case 0x4f5192:
    case 0x4bc0e0:
    case 0x4bc100:
        break;
    default:
        return 0;
    }
    if (c->fault)
        return 0;
    Run r{*c, d, u};
    try {
        *result = r.entry(f, t, a, n);
    } catch (Failed &) {
    }
    return c->fault ? 0 : 1;
}
