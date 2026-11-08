#include "ResourceDataRuntime.h"
#include <initializer_list>
#include <algorithm>
#include <cstdint>
namespace {
struct Fault {};
struct Run {
    ClawResourceDataContext &c;
    ClawResourceDataDependency dependency;
    void *user;
    uint32_t operations = 0, function = 0, receiver = 0, audioLookups = 0;
    void fail(uint32_t f) {
        c.fault = f;
        throw Fault{};
    }
    void step() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 100000))
            fail(3);
    }
    uint32_t *span(uint32_t t, uint32_t n) {
        step();
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p)
            fail(1);
        return p;
    }
    uint32_t get(uint32_t t) {
        return *span(t, 1);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t, 1) = v;
    }
    uint8_t byte(uint32_t t) {
        return reinterpret_cast<uint8_t *>(span(t & ~3u, 1))[t & 3u];
    }
    void byte(uint32_t t, uint8_t b) {
        reinterpret_cast<uint8_t *>(span(t & ~3u, 1))[t & 3u] = b;
    }
    uint32_t length(uint32_t t) {
        uint32_t n = 0;
        while (byte(t + n)) {
            step();
            ++n;
        }
        return n;
    }
    uint32_t event(const ClawResourceDataCall &q) {
        step();
        if (!dependency)
            fail(1);
        return dependency(&c, &q, user);
    }
    uint32_t call(uint32_t f, uint32_t t = 0, std::initializer_list<uint32_t> a = {}) {
        ClawResourceDataCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = static_cast<uint32_t>(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        return event(q);
    }
    static uint32_t arrayService(ClawCArrayContext *, const ClawCArrayCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        ClawResourceDataCall out{};
        out.function = q->function;
        out.receiver = q->receiver;
        out.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, out.arguments);
        return r.event(out);
    }
    uint32_t allocation(uint32_t bytes) {
        if (!c.allocator)
            return call(0x4f63ec, 0, {bytes});
        uint32_t result = 0;
        c.allocator->fault = 0;
        claw_carray_entry(0x4f63ec, 0, bytes, 0, 0, c.allocator, arrayService, this, &result);
        if (c.allocator->fault)
            fail(c.allocator->fault);
        return result;
    }
    uint32_t release(uint32_t t) {
        if (!c.allocator)
            return call(0x4f6428, 0, {t});
        uint32_t result = 0;
        c.allocator->fault = 0;
        claw_carray_entry(0x4f6428, 0, t, 0, 0, c.allocator, arrayService, this, &result);
        if (c.allocator->fault)
            fail(c.allocator->fault);
        return result;
    }
    void clone(uint32_t t, uint32_t field, uint32_t source) {
        uint32_t bytes = length(source) + 1, p = allocation(bytes);
        put(t + field, p);
        if (p) {
            bytes = length(source) + 1;
            for (uint32_t i = 0; i < bytes; ++i)
                byte(p + i, byte(source + i));
        }
    }
    uint32_t construct(uint32_t t, const uint32_t *a) {
        put(t + 48, 0x51356c);
        put(t + 68, 0);
        put(t + 72, 0x513568);
        put(t + 92, 0);
        put(t + 36, a[0]);
        if (a[1])
            clone(t, 0, a[1]);
        put(t + 4, a[2]);
        put(t + 8, a[3]);
        if (a[4])
            clone(t, 12, a[4]);
        else
            put(t + 12, 0);
        put(t + 20, a[5]);
        put(t + 40, a[6]);
        put(t + 16, a[7]);
        put(t + 28, a[8]);
        if (!a[9])
            put(t + 32, 0);
        else {
            uint32_t p = allocation(a[8] * 4);
            put(t + 32, p);
            if (p)
                for (uint32_t i = 0; i < a[8]; ++i) {
                    step();
                    put(get(t + 32) + i * 4, get(a[9] + i * 4));
                }
        }
        put(t + 24, 0);
        put(t + 44, 0);
        put(t + 92, t);
        put(t + 68, t);
        return t;
    }
    uint32_t destroy(uint32_t t) {
        uint32_t p = get(t);
        if (p)
            release(p);
        p = get(t + 12);
        if (p)
            release(p);
        p = get(t + 36);
        if (!p || !get(p + 32)) {
            p = get(t + 24);
            if (p)
                release(p);
        }
        p = get(t + 32);
        uint32_t result = p ? release(p) : 0;
        for (uint32_t i = 0; i < 12; ++i)
            put(t + i * 4, 0);
        put(t + 92, 0);
        put(t + 68, 0);
        return result;
    }
    static uint32_t *audioLookup(void *u, uint32_t t) {
        auto &r = *static_cast<Run *>(u);
        if (r.function == 0x4b7ab0)
            return r.span(t, 4);
        if (r.function == 0x4b6230)
            return r.span(t, 7);
        ++r.audioLookups;
        if (r.audioLookups == 1)
            return r.span(t, 11);
        if (r.audioLookups <= 3)
            return r.span(t, 9);
        return r.span(t, 4);
    }
    static uint32_t audioAllocate(void *u, uint32_t bytes) {
        return static_cast<Run *>(u)->allocation(bytes);
    }
    static void audioFree(void *u, uint32_t t) {
        static_cast<Run *>(u)->release(t);
    }
    static uint32_t audioSeek(void *u, uint32_t handle, uint32_t off, uint32_t whence) {
        return static_cast<Run *>(u)->call(0x4a7840, 0, {handle, off, whence});
    }
    static uint32_t audioRead(void *u, uint32_t dst, uint32_t size, uint32_t count, uint32_t handle) {
        return static_cast<Run *>(u)->call(0x4a7260, 0, {dst, size, count, handle});
    }
    static uint32_t audioRetry(void *u, uint32_t t) {
        auto &r = *static_cast<Run *>(u);
        return r.call(r.get(r.get(t) + 8), t);
    }
    uint32_t entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        function = f;
        receiver = t;
        uint32_t count = f == 0x4b5ff0 ? 10 : f == 0x4b7ab0 ? 3 : 0;
        if (n != count || (count && !a))
            fail(4);
        if (f == 0x4b5ff0)
            return construct(t, a);
        if (f == 0x4b6120)
            return destroy(t);
        if (f == 0x4b61b0)
            return get(get(t + 8));
        ClawAudioPCMHost host{};
        host.resource.context = this;
        host.resource.lookup = audioLookup;
        host.resource.allocate = audioAllocate;
        host.free = audioFree;
        host.seek = audioSeek;
        host.read = audioRead;
        host.retry = audioRetry;
        uint32_t fault = 0, result = 0;
        if (f == 0x4b61c0)
            result = claw_audio_acquire_file(host, t, &fault);
        else if (f == 0x4b6230)
            result = claw_audio_release_file(host, t, &fault);
        else
            result = claw_audio_read_file(host, t, a[0], a[1], a[2], &fault);
        if (fault)
            fail(1);
        return result;
    }
};
bool owned(uint32_t f) {
    return f == 0x4b5ff0 || f == 0x4b6120 || f == 0x4b61b0 || f == 0x4b61c0 || f == 0x4b6230 || f == 0x4b7ab0;
}
} // namespace
extern "C" uint32_t claw_resource_data_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                             ClawResourceDataContext *c, ClawResourceDataDependency d, void *u,
                                             uint32_t *r) {
    if (!owned(f) || !c || !r)
        return 0;
    try {
        Run run{*c, d, u};
        *r = run.entry(f, t, a, n);
        return 1;
    } catch (const Fault &) {
        return 0;
    }
}
