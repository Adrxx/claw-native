#include "CStringAssignmentRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
#include <vector>
namespace {
struct Fault {};
struct RestoreHost {
    ClawSceneActorHost &target;
    ClawSceneActorHost old;
    explicit RestoreHost(ClawSceneActorHost &t) : target(t), old(t) {
    }
    ~RestoreHost() {
        target = old;
    }
};
struct ByteView {
    uint32_t token;
    std::vector<uint32_t> words;
};
struct Run {
    ClawCStringAssignmentContext &c;
    ClawCStringAssignmentDependency dependency;
    void *user;
    uint32_t operations = 0;
    uint32_t partialToken = 0, partialBytes = 0, partialWord = 0;
    std::vector<ByteView> copyViews;
    bool copying = false, allocating = false;
    uint32_t allocationLength = 0, allocationTerminator = 0;
    Run(ClawCStringAssignmentContext &context, ClawCStringAssignmentDependency callback, void *data)
        : c(context), dependency(callback), user(data) {
    }
    void fail(uint32_t n) {
        c.fault = n;
        throw Fault{};
    }
    void step() {
        if (c.fault)
            throw Fault{};
        if (++operations > (c.maximumOperations ? c.maximumOperations : 1000000))
            fail(3);
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        step();
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p)
            fail(1);
        return p;
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    uint8_t *bytes(uint32_t t, uint32_t n) {
        step();
        if (!n)
            return nullptr;
        if (c.bytes) {
            auto *p = c.bytes(c.byteContext, t, n);
            if (!p)
                fail(1);
            return p;
        }
        uint64_t count = (uint64_t(n) + (t & 3u) + 3) / 4;
        if (count > 0xffffffffu)
            fail(2);
        return reinterpret_cast<uint8_t *>(span(t & ~3u, uint32_t(count))) + (t & 3u);
    }
    void flushPartial() {
        if (!partialBytes)
            return;
        uint32_t t = partialToken, n = partialBytes;
        partialBytes = 0;
        auto *p = c.bytes ? c.bytes(c.byteContext, t, n) : nullptr;
        if (!p)
            fail(1);
        std::memcpy(p, &partialWord, n);
    }
    uint32_t *adaptLookup(uint32_t t, uint32_t n) {
        flushPartial();
        if (copying)
            for (auto &v : copyViews)
                if (t >= v.token && uint64_t(t) + uint64_t(n) * 4 <= uint64_t(v.token) + v.words.size() * 4)
                    return v.words.data() + (t - v.token) / 4;
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (p)
            return p;
        if (c.bytes && allocating && allocationTerminator && t == (allocationTerminator & ~3u) && n == 1 && !(t & 3u)) {
            for (uint32_t valid = 4; valid; --valid) {
                auto *b = c.bytes(c.byteContext, t, valid);
                if (b) {
                    partialToken = t;
                    partialBytes = valid;
                    partialWord = 0;
                    std::memcpy(&partialWord, b, valid);
                    return &partialWord;
                }
            }
        }
        return nullptr;
    }
    static uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
        return static_cast<Run *>(u)->adaptLookup(t, n);
    }
    static uint32_t allocate(void *u, uint32_t n) {
        return static_cast<Run *>(u)->call(0x4f63ec, 0, {n});
    }
    static void release(void *u, uint32_t t) {
        static_cast<Run *>(u)->call(0x4f6428, 0, {t});
    }
    static uint32_t hostCall(void *u, ClawSceneActorCall q) {
        ClawCStringAssignmentCall out{};
        out.function = q.function;
        out.receiver = q.receiver;
        out.argumentCount = q.argumentCount;
        std::copy_n(q.arguments, q.argumentCount, out.arguments);
        return static_cast<Run *>(u)->invoke(out);
    }
    static uint32_t clock(void *u) {
        auto &r = *static_cast<Run *>(u);
        if (!r.c.scene.readClock)
            r.fail(1);
        return r.c.scene.readClock(r.c.scene.context);
    }
    ClawSceneActorHost host() {
        return {this, lookup, allocate, release, hostCall, clock};
    }
    uint32_t event(const ClawCStringAssignmentCall &q) {
        step();
        flushPartial();
        if (!dependency)
            fail(1);
        auto value = dependency(&c, &q, user);
        if (c.fault)
            throw Fault{};
        return value;
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawCStringAssignmentCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        return invoke(q);
    }
    static uint32_t fadeDependency(ClawPlayerFadeContext *, const ClawPlayerFadeCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        if (q->argumentCount > 4)
            r.fail(2);
        ClawCStringAssignmentCall out{};
        out.function = q->function;
        out.receiver = q->receiver;
        out.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, out.arguments);
        return r.invoke(out);
    }
    static uint32_t lifecycleDependency(ClawSceneLifecycleContext *, const ClawSceneLifecycleCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        if (q->argumentCount > 4 || q->localMask || q->bufferCount)
            r.fail(2);
        ClawCStringAssignmentCall out{};
        out.function = q->function;
        out.receiver = q->receiver;
        out.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, out.arguments);
        return r.invoke(out);
    }
    static uint32_t arrayDependency(ClawCArrayContext *, const ClawCArrayCall *q, void *u) {
        ClawCStringAssignmentCall out{};
        out.function = q->function;
        out.receiver = q->receiver;
        out.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, out.arguments);
        return static_cast<Run *>(u)->event(out);
    }
    void prepareCopy(uint32_t dst, uint32_t src, uint32_t n) {
        copyViews.clear();
        if (!c.bytes || !n)
            return;
        if (n > 1000000 || uint64_t(dst) + n > 0xffffffffu || uint64_t(src) + n > 0xffffffffu)
            fail(2);
        auto *a = bytes(dst, n);
        auto *b = bytes(src, n);
        uint32_t d0 = dst & ~3u, s0 = src & ~3u;
        uint64_t d1 = (uint64_t(dst) + n + 3) & ~uint64_t(3), s1 = (uint64_t(src) + n + 3) & ~uint64_t(3);
        if (d0 < s1 && s0 < d1) {
            uint32_t begin = std::min(d0, s0);
            copyViews.push_back({begin, std::vector<uint32_t>((std::max(d1, s1) - begin) / 4)});
        } else {
            copyViews.push_back({d0, std::vector<uint32_t>((d1 - d0) / 4)});
            copyViews.push_back({s0, std::vector<uint32_t>((s1 - s0) / 4)});
        }
        for (auto &v : copyViews) {
            if (dst >= v.token && uint64_t(dst) + n <= uint64_t(v.token) + v.words.size() * 4)
                std::memcpy(reinterpret_cast<uint8_t *>(v.words.data()) + dst - v.token, a, n);
            if (src >= v.token && uint64_t(src) + n <= uint64_t(v.token) + v.words.size() * 4)
                std::memcpy(reinterpret_cast<uint8_t *>(v.words.data()) + src - v.token, b, n);
        }
        copying = true;
    }
    void finishCopy(uint32_t dst, uint32_t n) {
        if (copying) {
            for (auto &v : copyViews)
                if (dst >= v.token && uint64_t(dst) + n <= uint64_t(v.token) + v.words.size() * 4) {
                    std::memcpy(bytes(dst, n), reinterpret_cast<uint8_t *>(v.words.data()) + dst - v.token, n);
                    break;
                }
            copying = false;
            copyViews.clear();
        }
    }
    uint32_t primitive(uint32_t f, uint32_t t, const uint32_t *a) {
        ClawCArrayContext local{};
        auto *x = c.arrays ? c.arrays : &local;
        RestoreHost restore(x->scene);
        x->scene = host();
        uint32_t value = 0;
        if (f == 0x4a4a80)
            prepareCopy(a[0], a[1], a[2]);
        bool ok = claw_carray_entry(f, t, a[0], a[1], a[2], x, arrayDependency, this, &value) != 0;
        flushPartial();
        if (!ok || x->fault)
            fail(x->fault ? x->fault : 1);
        if (f == 0x4a4a80)
            finishCopy(a[0], a[2]);
        return value;
    }
    uint32_t invoke(const ClawCStringAssignmentCall &q) {
        step();
        if (q.argumentCount > 4)
            fail(2);
        if (own(q.function))
            return entry(q.function, q.receiver, q.arguments, q.argumentCount);
        uint32_t value = 0;
        if (q.function == 0x4f64ba && c.lifecycle) {
            RestoreHost restore(c.lifecycle->scene);
            c.lifecycle->scene = host();
            if (!claw_scene_lifecycle_entry(q.function, q.receiver, q.arguments, q.argumentCount, c.lifecycle,
                                            lifecycleDependency, this, &value) ||
                c.lifecycle->fault)
                fail(c.lifecycle->fault ? c.lifecycle->fault : 1);
            flushPartial();
            return value;
        }
        if (q.function == 0x4f6480 && c.allocation) {
            if (!c.allocation->fade)
                fail(1);
            RestoreHost restore(c.allocation->fade->scene);
            c.allocation->fade->scene = host();
            c.allocation->emptyStringToken = get(0x52e1cc);
            allocating = true;
            allocationLength = q.arguments[0];
            allocationTerminator = 0;
            if (!claw_player_fade_blend_entry(q.function, q.receiver, q.arguments, q.argumentCount, c.allocation,
                                              fadeDependency, this, &value) ||
                c.allocation->fade->fault)
                fail(c.allocation->fade->fault ? c.allocation->fade->fault : 1);
            flushPartial();
            allocating = false;
            return value;
        }
        if (q.function == 0x4a4a80 || (c.arrays && (q.function == 0x4f63ec || q.function == 0x4f6428))) {
            value = primitive(q.function, q.receiver, q.arguments);
            if (q.function == 0x4f63ec && allocating && value)
                allocationTerminator = value + allocationLength + 12;
            return value;
        }
        value = event(q);
        if (q.function == 0x4f63ec && allocating && value)
            allocationTerminator = value + allocationLength + 12;
        return value;
    }
    static bool own(uint32_t f) {
        return f == 0x4f66cc || f == 0x4f6650 || f == 0x4f655b;
    }
    uint32_t entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        uint32_t expected = f == 0x4f6650 ? 2 : 1;
        if (n != expected || (n && !a))
            fail(2);
        uint32_t count = a[0], source = f == 0x4f6650 ? a[1] : 0;
        if (f == 0x4f66cc) {
            source = a[0];
            count = source ? call(0x5469e4, 0, {source}) : 0;
            uint32_t args[] = {count, source};
            entry(0x4f6650, t, args, 2);
            return t;
        }
        if (f == 0x4f655b) {
            uint32_t data = get(t);
            if (int32_t(get(data - 12)) > 1 || int32_t(get(data - 4)) < int32_t(count)) {
                call(0x4f64ba, t);
                call(0x4f6480, t, {count});
            }
            return 0;
        }
        uint32_t prepare[] = {count};
        entry(0x4f655b, t, prepare, 1);
        call(0x4a4a80, 0, {get(t), source, count});
        put(get(t) - 8, count);
        *bytes(get(t) + count, 1) = 0;
        return 0;
    }
};
} // namespace
extern "C" uint32_t claw_cstring_assignment_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                  ClawCStringAssignmentContext *c, ClawCStringAssignmentDependency d,
                                                  void *u, uint32_t *v) {
    if (!c || !v || !Run::own(f))
        return 0;
    try {
        Run r{*c, d, u};
        *v = r.entry(f, t, a, n);
        r.flushPartial();
        return c->fault ? 0 : 1;
    } catch (Fault &) {
    }
    return 0;
}
