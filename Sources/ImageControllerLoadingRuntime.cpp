#include "ImageControllerLoadingRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Fault {};
struct HostRestore {
    ClawSceneActorHost &target;
    ClawSceneActorHost old;
    explicit HostRestore(ClawSceneActorHost &t) : target(t), old(t) {
    }
    ~HostRestore() {
        target = old;
    }
};
struct Run {
    ClawImageControllerLoadingContext &c;
    ClawImageControllerLoadingDependency dependency;
    void *user;
    uint32_t operations = 0;
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
    void put(uint32_t t, uint32_t n) {
        *span(t) = n;
    }
    uint32_t byte(uint32_t t) {
        return reinterpret_cast<uint8_t *>(span(t & ~3u))[t & 3u];
    }
    uint32_t event(const ClawImageControllerLoadingCall &q) {
        step();
        if (!dependency)
            fail(1);
        auto result = dependency(&c, &q, user);
        if (c.fault)
            throw Fault{};
        return result;
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawImageControllerLoadingCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        return invoke(q);
    }
    static bool own(uint32_t f) {
        switch (f) {
        case 0x4f5d33:
        case 0x4f5d5c:
        case 0x4f615b:
        case 0x4f6226:
        case 0x4f6286:
        case 0x4f62a8:
        case 0x4f5db6:
            return true;
        default:
            return false;
        }
    }
    static bool publicSupported(uint32_t f, const ClawImageControllerLoadingContext &c) {
        if (own(f))
            return true;
        if (c.registry)
            switch (f) {
            case 0x4cff40:
            case 0x4d0120:
            case 0x4ce0d0:
            case 0x4cdff0:
            case 0x4ce5e0:
            case 0x4ce670:
            case 0x4ce770:
            case 0x4d0380:
            case 0x4cf080:
            case 0x4cf1f0:
            case 0x4cfaa0:
            case 0x4cfba0:
            case 0x4cfca0:
            case 0x4cfdb0:
            case 0x4cfec0:
            case 0x4cfee0:
            case 0x4cff00:
            case 0x4cff20:
            case 0x4ce320:
            case 0x4ce480:
            case 0x4ce530:
            case 0x4d2380:
            case 0x4d61b0:
            case 0x4d6070:
            case 0x4d76e0:
            case 0x4d6260:
            case 0x4d6210:
            case 0x4ce250:
            case 0x4ce270:
            case 0x4ce2d0:
            case 0x4d02f0:
            case 0x4d0310:
            case 0x4cf230:
                return true;
            default:
                break;
            }
        if (c.names)
            switch (f) {
            case 0x4b7540:
            case 0x4b7f20:
            case 0x4b7f00:
            case 0x4b7cd0:
            case 0x4b7dc0:
            case 0x4b68c0:
            case 0x4b67f0:
            case 0x4b8170:
            case 0x4b7f80:
            case 0x4b80e0:
            case 0x4b80d0:
            case 0x4b8060:
            case 0x4b8140:
            case 0x4b7f50:
            case 0x4d54f0:
            case 0x4d54c0:
            case 0x4d5350:
            case 0x4b68e0:
            case 0x4b6920:
            case 0x4b6900:
            case 0x4b6940:
            case 0x4b6980:
            case 0x4b6960:
                return true;
            default:
                break;
            }
        if (c.data)
            switch (f) {
            case 0x4b5ff0:
            case 0x4b6120:
            case 0x4b61b0:
            case 0x4b61c0:
            case 0x4b6230:
            case 0x4b7ab0:
                return true;
            default:
                break;
            }
        if (c.archive)
            switch (f) {
            case 0x4b7210:
            case 0x4b72e0:
            case 0x4b6b60:
            case 0x4b6ed0:
            case 0x4b7bd0:
            case 0x4b7c40:
            case 0x4b7c80:
            case 0x4b74d0:
            case 0x4b7250:
                return true;
            default:
                break;
            }
        return (c.arrays && (f == 0x4f63ec || f == 0x4f6428 || f == 0x4a4a20 || f == 0x4a4a80)) ||
               (c.pools && (f == 0x4f5aa8 || f == 0x4f5ac8));
    }
    uint32_t hash(uint32_t t, uint32_t key) {
        uint32_t n = 0;
        for (uint32_t b; (b = byte(key)); ++key) {
            step();
            n = n * 33 + uint32_t(int32_t(int8_t(b)));
        }
        uint32_t buckets = get(t + 8);
        if (!buckets)
            fail(2);
        return n % buckets;
    }
    uint32_t find(uint32_t t, uint32_t key, uint32_t &bucket, uint32_t hashCell = 0) {
        bucket = hash(t, key);
        if (hashCell)
            put(hashCell, bucket);
        uint32_t table = get(t + 4);
        if (table)
            for (uint32_t p = get(table + bucket * 4); p; p = get(p)) {
                step();
                if (!call(0x4a3810, 0, {get(p + 8), key}))
                    return p;
            }
        return 0;
    }
    uint32_t newAssoc(uint32_t t) {
        if (!get(t + 16)) {
            uint32_t count = get(t + 24), block = call(0x4f5aa8, 0, {t + 20, count, 16});
            count = get(t + 24);
            uint32_t p = block + count * 16 - 12;
            if (int32_t(count - 1) >= 0) {
                for (uint32_t i = count; i; --i) {
                    step();
                    put(p, get(t + 16));
                    put(t + 16, p);
                    p -= 16;
                }
            }
        }
        uint32_t p = get(t + 16), next = get(p);
        put(t + 12, get(t + 12) + 1);
        put(t + 16, next);
        uint32_t empty = call(0x4f6433, 0);
        call(0x4a4a80, 0, {p + 8, empty, 4});
        put(p + 12, 0);
        return p;
    }
    void freeAssoc(uint32_t t, uint32_t p) {
        call(0x4f6584, p + 8);
        uint32_t next = get(t + 16);
        put(p, next);
        put(t + 12, get(t + 12) - 1);
        put(t + 16, p);
        if (!get(t + 12))
            call(0x4f61a1, t);
    }
    void tableInit(uint32_t t, uint32_t buckets, uint32_t allocate) {
        uint32_t old = get(t + 4);
        if (old) {
            call(0x4f6428, 0, {old});
            put(t + 4, 0);
        }
        if (allocate) {
            uint32_t bytes = buckets * 4, p = call(0x4f63ec, 0, {bytes});
            put(t + 4, p);
            call(0x4a4a20, 0, {p, 0, bytes});
        }
        put(t + 8, buckets);
    }
    uint32_t dictionary(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        uint32_t required = f == 0x4f5d5c || f == 0x4f615b || f == 0x4f6286 ? 2 : f == 0x4f6226 ? 0 : 1;
        if (n != required || (n && !a))
            fail(2);
        if (f == 0x4f5d33) {
            freeAssoc(t, a[0]);
            return 0;
        }
        if (f == 0x4f615b) {
            tableInit(t, a[0], a[1]);
            return 0;
        }
        if (f == 0x4f6226)
            return newAssoc(t);
        uint32_t bucket = 0;
        if (f == 0x4f5d5c) {
            return find(t, a[0], bucket, a[1]);
        }
        if (f == 0x4f6286) {
            uint32_t p = find(t, a[0], bucket);
            if (p)
                put(a[1], get(p + 12));
            return p ? 1 : 0;
        }
        if (f == 0x4f62a8) {
            uint32_t p = find(t, a[0], bucket);
            if (!p) {
                if (!get(t + 4))
                    tableInit(t, get(t + 8), 1);
                p = newAssoc(t);
                put(p + 4, bucket);
                call(0x4f66cc, p + 8, {a[0]});
                uint32_t head = get(get(t + 4) + bucket * 4);
                put(p, head);
                put(get(t + 4) + bucket * 4, p);
            }
            return p + 12;
        }
        uint32_t table = get(t + 4);
        if (table) {
            bucket = hash(t, a[0]);
            uint32_t link = table + bucket * 4;
            for (uint32_t p = get(link); p; p = get(link)) {
                step();
                if (!call(0x4a3810, 0, {get(p + 8), a[0]})) {
                    put(link, get(p));
                    freeAssoc(t, p);
                    return 1;
                }
                link = p;
            }
        }
        return 0;
    }
    static uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
        auto &r = *static_cast<Run *>(u);
        return r.c.scene.lookup ? r.c.scene.lookup(r.c.scene.context, t, n) : nullptr;
    }
    static uint32_t allocate(void *u, uint32_t n) {
        return static_cast<Run *>(u)->call(0x4f63ec, 0, {n});
    }
    static void release(void *u, uint32_t t) {
        static_cast<Run *>(u)->call(0x4f6428, 0, {t});
    }
    static uint32_t hostCall(void *u, ClawSceneActorCall q) {
        auto &r = *static_cast<Run *>(u);
        if (q.function == 0x4f6286 && q.argumentCount == 1) {
            uint32_t bucket = 0, p = r.find(q.receiver, q.arguments[0], bucket);
            return p ? r.get(p + 12) : 0;
        }
        ClawImageControllerLoadingCall out{};
        out.function = q.function;
        out.receiver = q.receiver;
        out.argumentCount = q.argumentCount;
        std::copy_n(q.arguments, q.argumentCount, out.arguments);
        return r.invoke(out);
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
    static uint32_t tableDependency(ClawResourceTableConstructionContext *, const ClawResourceTableConstructionCall *q,
                                    void *u) {
        auto &r = *static_cast<Run *>(u);
        ClawImageControllerLoadingCall out{};
        out.function = q->function;
        out.receiver = q->receiver;
        out.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, out.arguments);
        out.localMask = q->localMask;
        out.bufferCount = q->bufferCount;
        for (uint32_t i = 0; i < q->bufferCount; ++i) {
            out.buffers[i] = q->buffers[i];
            out.bufferBytes[i] = q->bufferBytes[i];
        }
        return out.localMask ? r.event(out) : r.invoke(out);
    }
    static uint32_t namesDependency(ClawResourceNamespaceContext *, const ClawResourceNamespaceCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        ClawImageControllerLoadingCall out{};
        out.function = q->function;
        out.receiver = q->receiver;
        out.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, out.arguments);
        out.localMask = q->localMask;
        out.bufferCount = q->bufferCount;
        for (uint32_t i = 0; i < q->bufferCount; ++i) {
            out.buffers[i] = const_cast<void *>(q->buffers[i]);
            out.bufferBytes[i] = q->bufferBytes[i];
        }
        return out.localMask ? r.event(out) : r.invoke(out);
    }
    static uint32_t dataDependency(ClawResourceDataContext *, const ClawResourceDataCall *q, void *u) {
        ClawImageControllerLoadingCall out{};
        out.function = q->function;
        out.receiver = q->receiver;
        out.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, out.arguments);
        return static_cast<Run *>(u)->invoke(out);
    }
    static uint32_t arrayDependency(ClawCArrayContext *, const ClawCArrayCall *q, void *u) {
        ClawImageControllerLoadingCall out{};
        out.function = q->function;
        out.receiver = q->receiver;
        out.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, out.arguments);
        return static_cast<Run *>(u)->event(out);
    }
    static uint32_t poolDependency(ClawAmbientAudioBackendContext *, const ClawAmbientAudioBackendCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        if (q->outputWord)
            r.fail(2);
        ClawImageControllerLoadingCall out{};
        out.function = q->function;
        out.receiver = q->receiver;
        out.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, out.arguments);
        return r.invoke(out);
    }
    uint32_t invoke(const ClawImageControllerLoadingCall &q) {
        step();
        if (q.argumentCount > 10)
            fail(2);
        if (own(q.function))
            return dictionary(q.function, q.receiver, q.arguments, q.argumentCount);
        uint32_t v = 0;
        bool done = false;
        if (c.registry && q.argumentCount <= 5) {
            HostRestore restore(c.registry->scene);
            ClawSceneActorHost unused{};
            HostRestore arrayRestore(c.registry->arrays ? c.registry->arrays->scene : unused);
            c.registry->scene = host();
            ClawImageRegistryArguments a{};
            a.count = q.argumentCount;
            std::copy_n(q.arguments, q.argumentCount, a.words);
            done = claw_image_registry_entry(q.function, q.receiver, a, c.registry, &v) != 0;
            if (c.registry->fault)
                fail(c.registry->fault);
            if (done)
                return v;
        }
        if (c.names) {
            HostRestore restore(c.names->scene);
            c.names->scene = host();
            done = claw_resource_namespace_entry(q.function, q.receiver, q.arguments, q.argumentCount, c.names,
                                                 namesDependency, this, &v) != 0;
            if (c.names->fault)
                fail(c.names->fault);
            if (done)
                return v;
        }
        if (c.data) {
            HostRestore restore(c.data->scene);
            c.data->scene = host();
            done = claw_resource_data_entry(q.function, q.receiver, q.arguments, q.argumentCount, c.data,
                                            dataDependency, this, &v) != 0;
            if (c.data->fault)
                fail(c.data->fault);
            if (done)
                return v;
        }
        if (c.archive) {
            done = claw_resource_archive_loading_entry(q.function, q.receiver, q.arguments, q.argumentCount, c.archive,
                                                       tableDependency, this, &v) != 0;
            if (c.archive->table && c.archive->table->fault)
                fail(c.archive->table->fault);
            if (done)
                return v;
        }
        if (c.arrays &&
            (q.function == 0x4f63ec || q.function == 0x4f6428 || q.function == 0x4a4a20 || q.function == 0x4a4a80)) {
            HostRestore restore(c.arrays->scene);
            c.arrays->scene = host();
            done = claw_carray_entry(q.function, q.receiver, q.arguments[0], q.arguments[1], q.arguments[2], c.arrays,
                                     arrayDependency, this, &v) != 0;
            if (c.arrays->fault)
                fail(c.arrays->fault);
            if (done)
                return v;
        }
        if (c.pools && (q.function == 0x4f5aa8 || q.function == 0x4f5ac8)) {
            HostRestore restore(c.pools->scene);
            c.pools->scene = host();
            done = claw_ambient_audio_backend_entry(q.function, q.receiver, q.arguments, q.argumentCount, c.pools,
                                                    poolDependency, this, &v) != 0;
            if (c.pools->fault)
                fail(c.pools->fault);
            if (done)
                return v;
        }
        return event(q);
    }
};
} // namespace
extern "C" uint32_t claw_image_controller_loading_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                        ClawImageControllerLoadingContext *c,
                                                        ClawImageControllerLoadingDependency d, void *u, uint32_t *v) {
    if (!c || !v || n > 10 || (n && !a) || !Run::publicSupported(f, *c))
        return 0;
    uint32_t expected = f == 0x4f63ec || f == 0x4f6428                    ? 1
                        : f == 0x4a4a20 || f == 0x4a4a80 || f == 0x4f5aa8 ? 3
                        : f == 0x4f5ac8                                   ? 0
                                                                          : 0xffffffff;
    if (expected != 0xffffffff && n != expected) {
        c->fault = 2;
        return 0;
    }
    try {
        Run r{*c, d, u};
        ClawImageControllerLoadingCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        std::copy_n(a, n, q.arguments);
        *v = r.invoke(q);
        return c->fault ? 0 : 1;
    } catch (Fault &) {
    }
    return 0;
}
