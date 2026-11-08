#include "ResourceTableConstructionRuntime.h"
#include "AmbientAudioBackendRuntime.h"
#include <algorithm>
#include <initializer_list>
#include <cstring>
namespace {
struct Fault {};
struct Run {
    ClawResourceTableConstructionContext &c;
    ClawResourceTableConstructionDependency dependency;
    void *user;
    uint32_t operations = 0;
    void fail(uint32_t f) {
        c.fault = f;
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
        if (c.bytes) {
            auto *p = c.bytes(c.byteContext, t, n);
            if (!p)
                fail(1);
            return p;
        }
        uint64_t count = (uint64_t(n) + (t & 3) + 3) / 4;
        if (count > 0xffffffff)
            fail(2);
        return reinterpret_cast<uint8_t *>(span(t & ~3u, uint32_t(count))) + (t & 3);
    }
    uint32_t length(uint32_t t) {
        uint32_t n = 0;
        while (*bytes(t + n, 1)) {
            step();
            ++n;
        }
        return n;
    }
    uint32_t event(const ClawResourceTableConstructionCall &q) {
        step();
        uint32_t v = 0;
        if (dependency)
            v = dependency(&c, &q, user);
        else if (c.scene.call && q.argumentCount <= 4 && !q.localMask) {
            ClawSceneActorCall e{};
            e.function = q.function;
            e.receiver = q.receiver;
            e.argumentCount = q.argumentCount;
            std::copy_n(q.arguments, q.argumentCount, e.arguments);
            v = c.scene.call(c.scene.context, e);
        } else
            fail(1);
        if (c.fault)
            throw Fault{};
        return v;
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawResourceTableConstructionCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        return event(q);
    }
    static uint32_t arrayCall(ClawCArrayContext *, const ClawCArrayCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        ClawResourceTableConstructionCall e{};
        e.function = q->function;
        e.receiver = q->receiver;
        e.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, e.arguments);
        return r.event(e);
    }
    uint32_t alloc(uint32_t n) {
        if (!c.allocator)
            return call(0x4f63ec, 0, {n});
        uint32_t v = 0;
        c.allocator->fault = 0;
        if (!claw_carray_entry(0x4f63ec, 0, n, 0, 0, c.allocator, arrayCall, this, &v))
            fail(c.allocator->fault ? c.allocator->fault : 1);
        return v;
    }
    void free(uint32_t t) {
        if (!c.allocator) {
            call(0x4f6428, 0, {t});
            return;
        }
        uint32_t v = 0;
        c.allocator->fault = 0;
        if (!claw_carray_entry(0x4f6428, 0, t, 0, 0, c.allocator, arrayCall, this, &v))
            fail(c.allocator->fault ? c.allocator->fault : 1);
    }
    static uint32_t namespaceCall(ClawResourceNamespaceContext *, const ClawResourceNamespaceCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        ClawResourceTableConstructionCall e{};
        e.function = q->function;
        e.receiver = q->receiver;
        e.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, e.arguments);
        e.localMask = q->localMask;
        e.bufferCount = q->bufferCount;
        for (uint32_t i = 0; i < q->bufferCount; ++i) {
            e.buffers[i] = const_cast<void *>(static_cast<const void *>(q->buffers[i]));
            e.bufferBytes[i] = q->bufferBytes[i];
        }
        return r.event(e);
    }
    uint32_t ns(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawResourceNamespaceContext context{};
        context.scene = c.scene;
        context.maximumOperations = c.maximumOperations;
        uint32_t v = 0, args[4]{};
        std::copy(a.begin(), a.end(), args);
        if (!claw_resource_namespace_entry(f, t, args, uint32_t(a.size()), &context, namespaceCall, this, &v))
            fail(context.fault ? context.fault : 1);
        return v;
    }
    static uint32_t resourceCall(ClawResourceDataContext *, const ClawResourceDataCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        ClawResourceTableConstructionCall e{};
        e.function = q->function;
        e.receiver = q->receiver;
        e.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, e.arguments);
        return r.event(e);
    }
    uint32_t resource(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        ClawResourceDataContext context{};
        context.scene = c.scene;
        context.allocator = c.allocator;
        context.maximumOperations = c.maximumOperations;
        uint32_t v = 0;
        if (!claw_resource_data_entry(f, t, a, n, &context, resourceCall, this, &v))
            fail(context.fault ? context.fault : 1);
        return v;
    }
    uint32_t list(uint32_t f, uint32_t t, uint32_t node) {
        ClawAmbientAudioBackendContext context{};
        context.scene = c.scene;
        uint32_t v = 0;
        if (!claw_ambient_audio_backend_entry(f, t, &node, 1, &context, nullptr, nullptr, &v))
            fail(context.fault ? context.fault : 1);
        return v;
    }
    void map(uint32_t t, uint32_t count) {
        put(t, count);
        uint32_t block = alloc(count * 16 + 4), table = 0;
        if (block) {
            put(block, count);
            table = block + 4;
            for (uint32_t i = 0; int32_t(i) < int32_t(count); ++i) {
                step();
                put(table + i * 16 + 8, 0);
                put(table + i * 16 + 12, 0);
            }
        }
        put(t + 4, table);
    }
    void mapDestroy(uint32_t t) {
        uint32_t table = get(t + 4);
        if (table) {
            uint32_t count = get(table - 4);
            for (uint32_t i = count - 1; int32_t(i) >= 0; --i)
                step();
            free(table - 4);
        }
    }
    uint32_t hash(uint32_t f, uint32_t t) {
        uint32_t value = get(t + 20);
        if (f == 0x4b8050)
            return ns(0x4b8060, 0, {get(value + 4)});
        if (f == 0x4b80c0)
            return ns(0x4b80d0, 0, {get(value)});
        return ns(f == 0x4b8130 ? 0x4b8140 : 0x4b7f50, 0, {get(value)});
    }
    uint32_t invoke(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        if (owned(f))
            return entry(f, t, a, n);
        ClawResourceTableConstructionCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        std::copy_n(a, n, q.arguments);
        return event(q);
    }
    void insert(uint32_t t, uint32_t node) {
        uint32_t index = invoke(get(get(node)), node, nullptr, 0);
        put(node + 12, t);
        put(node + 16, index);
        list(0x4b5210, get(t + 4) + index * 16 + 8, node ? node + 4 : 0);
    }
    void remove(uint32_t t, uint32_t node) {
        uint32_t next = node ? node + 4 : 0;
        list(0x4b5270, get(t + 4) + get(node + 16) * 16 + 8, next);
    }
    uint32_t folder(uint32_t t, const uint32_t *a) {
        put(t + 36, 0x513574);
        put(t + 56, 0);
        map(t + 60, 5);
        map(t + 68, 9);
        uint32_t n = length(a[2]) + 1, p = alloc(n);
        put(t, p);
        if (p) {
            n = length(a[2]) + 1;
            uint32_t i = 0;
            for (; i + 4 <= n; i += 4) {
                uint32_t v = 0;
                std::memcpy(&v, bytes(a[2] + i, 4), 4);
                std::memcpy(bytes(p + i, 4), &v, 4);
            }
            for (; i < n; ++i)
                *bytes(p + i, 1) = *bytes(a[2] + i, 1);
        }
        put(t + 20, a[5]);
        put(t + 8, a[4]);
        put(t + 24, a[0]);
        put(t + 4, a[3]);
        put(t + 16, 0);
        put(t + 12, 0);
        put(t + 32, 0);
        put(t + 28, a[1]);
        put(t + 56, t);
        return t;
    }
    uint32_t type(uint32_t t, uint32_t tag) {
        put(t + 4, 0x513570);
        put(t + 24, 0);
        map(t + 28, 19);
        map(t + 36, 19);
        put(t, tag);
        put(t + 24, t);
        return t;
    }
    uint32_t time(uint32_t t) {
        uint32_t local = t;
        ClawResourceTableConstructionCall q{};
        q.function = 0x4a3b10;
        q.argumentCount = 1;
        q.localMask = 1;
        q.bufferCount = 1;
        q.buffers[0] = &local;
        q.bufferBytes[0] = 4;
        return event(q);
    }
    uint32_t createFolder(uint32_t t, uint32_t name) {
        if (ns(0x4b8170, t + 60, {name, 1}))
            return 0;
        uint32_t p = alloc(76);
        if (p) {
            uint32_t stamp = time(get(t + 24)), a[] = {get(t + 24), t, name, 0, 0, stamp};
            folder(p, a);
        }
        if (!p)
            return 0;
        insert(t + 60, p + 36);
        uint32_t owner = get(t + 24), n = length(name);
        if (get(owner + 56) <= n)
            put(owner + 56, n + 1);
        return p;
    }
    uint32_t createType(uint32_t t, uint32_t tag) {
        uint32_t p = ns(0x4b80e0, t + 68, {tag});
        if (p)
            return p;
        p = alloc(44);
        if (!p)
            return 0;
        type(p, tag);
        insert(t + 68, p + 4);
        return p;
    }
    uint32_t idLookup(uint32_t t, uint32_t id) {
        uint32_t index = ns(0x4b8060, 0, {id}), node = ns(0x4d54f0, t, {index});
        while (node) {
            step();
            if (get(get(node + 20) + 4) == id)
                return get(node + 20);
            uint32_t p = get(node + 4);
            node = p ? p - 4 : 0;
        }
        return 0;
    }
    uint32_t createResource(uint32_t t, const uint32_t *a) {
        uint32_t ty = createType(t, a[2]);
        if (idLookup(ty + 28, a[0]))
            return 0;
        if (ns(0x4b7f80, ty + 36, {a[1], 1}))
            return 0;
        uint32_t p = alloc(96);
        if (p) {
            uint32_t stamp = time(get(t + 24)), args[] = {t, a[1], a[0], ty, 0, 0, 0, stamp, 0, 0};
            resource(0x4b5ff0, p, args, 10);
        }
        if (!p)
            return 0;
        insert(ty + 28, p + 72);
        insert(ty + 36, p + 48);
        uint32_t owner = get(t + 24), n = length(a[1]);
        if (get(owner + 60) <= n)
            put(owner + 60, n + 1);
        return p;
    }
    void destroyType(uint32_t t) {
        uint32_t node = ns(0x4d54c0, t + 28);
        while (node) {
            step();
            uint32_t current = node;
            node = ns(0x4d5350, current);
            remove(t + 28, current);
        }
        node = ns(0x4d54c0, t + 36);
        while (node) {
            step();
            uint32_t current = node;
            node = ns(0x4d5350, current);
            remove(t + 36, current);
            uint32_t value = get(current + 20);
            if (value) {
                resource(0x4b6120, value, nullptr, 0);
                free(value);
            }
        }
        put(t, 0);
        put(t + 24, 0);
        mapDestroy(t + 36);
        mapDestroy(t + 28);
    }
    void destroyFolder(uint32_t t) {
        uint32_t node = ns(0x4d54c0, t + 68);
        while (node) {
            step();
            uint32_t current = node;
            node = ns(0x4d5350, current);
            remove(t + 68, current);
            uint32_t value = get(current + 20);
            if (value) {
                destroyType(value);
                free(value);
            }
        }
        node = ns(0x4d54c0, t + 60);
        while (node) {
            step();
            uint32_t current = node;
            node = ns(0x4d5350, current);
            remove(t + 60, current);
            uint32_t value = get(current + 20);
            if (value) {
                destroyFolder(value);
                free(value);
            }
        }
        uint32_t name = get(t);
        if (name)
            free(name);
        uint32_t aux = get(t + 32);
        if (aux)
            free(aux);
        for (uint32_t off : {0u, 20u, 8u, 4u, 16u, 12u, 32u, 24u, 28u, 56u})
            put(t + off, 0);
        mapDestroy(t + 68);
        mapDestroy(t + 60);
    }
    uint32_t entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        uint32_t required = f == 0x4b6600   ? 6
                            : f == 0x4b6a60 ? 3
                            : f == 0x4d53a0 || f == 0x4b64b0 || f == 0x4d5450 || f == 0x4d5490 || f == 0x4b69a0 ||
                                    f == 0x4b7170 || f == 0x4b8070
                                ? 1
                                : 0;
        if (n != required || (n && !a))
            fail(4);
        switch (f) {
        case 0x4b6600:
            return folder(t, a);
        case 0x4b64b0:
            return type(t, a[0]);
        case 0x4d53a0:
            map(t, a[0]);
            return t;
        case 0x4d5410:
            put(t + 8, 0);
            put(t + 12, 0);
            return t;
        case 0x4d5420:
            mapDestroy(t);
            return 0;
        case 0x4d5450:
            insert(t, a[0]);
            return 0;
        case 0x4d5490:
            remove(t, a[0]);
            return 0;
        case 0x4b7f40:
        case 0x4b8050:
        case 0x4b80c0:
        case 0x4b8130:
            return hash(f, t);
        case 0x4b69a0:
            return createFolder(t, a[0]);
        case 0x4b7170:
            return createType(t, a[0]);
        case 0x4b6a60:
            return createResource(t, a);
        case 0x4b8070:
            return idLookup(t, a[0]);
        case 0x4b7cc0:
            return time(t);
        case 0x4b6530:
            destroyType(t);
            return 0;
        case 0x4b66d0:
            destroyFolder(t);
            return 0;
        default:
            return 0;
        }
    }
    static bool owned(uint32_t f) {
        switch (f) {
        case 0x4b6600:
        case 0x4b64b0:
        case 0x4d53a0:
        case 0x4d5410:
        case 0x4d5420:
        case 0x4d5450:
        case 0x4d5490:
        case 0x4b7f40:
        case 0x4b8050:
        case 0x4b80c0:
        case 0x4b8130:
        case 0x4b69a0:
        case 0x4b7170:
        case 0x4b6a60:
        case 0x4b8070:
        case 0x4b7cc0:
        case 0x4b6530:
        case 0x4b66d0:
            return true;
        default:
            return false;
        }
    }
};
} // namespace
extern "C" uint32_t claw_resource_table_construction_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                           ClawResourceTableConstructionContext *c,
                                                           ClawResourceTableConstructionDependency d, void *u,
                                                           uint32_t *r) {
    if (!Run::owned(f) || !c || !r)
        return 0;
    try {
        Run run{*c, d, u};
        *r = run.entry(f, t, a, n);
        return c->fault ? 0 : 1;
    } catch (const Fault &) {
        return 0;
    }
}
