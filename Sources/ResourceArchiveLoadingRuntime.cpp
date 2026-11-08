#include "ResourceArchiveLoadingRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Fault {};
struct Run {
    ClawResourceArchiveLoadingContext &c;
    ClawResourceTableConstructionDependency dependency;
    void *user;
    uint32_t operations = 0;
    ClawResourceTableConstructionContext &table() {
        return *c.table;
    }
    void fail(uint32_t f) {
        table().fault = f;
        throw Fault{};
    }
    void step() {
        if (table().fault)
            throw Fault{};
        if (++operations > (c.maximumOperations ? c.maximumOperations : 1000000))
            fail(3);
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        step();
        auto *p = table().scene.lookup ? table().scene.lookup(table().scene.context, t, n) : nullptr;
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
        if (table().bytes) {
            auto *p = table().bytes(table().byteContext, t, n);
            if (!p)
                fail(1);
            return p;
        }
        uint64_t count = (uint64_t(n) + (t & 3) + 3) / 4;
        if (count > 0xffffffff)
            fail(2);
        return reinterpret_cast<uint8_t *>(span(t & ~3u, uint32_t(count))) + (t & 3);
    }
    uint32_t rawWord(uint32_t t) {
        uint32_t v;
        std::memcpy(&v, bytes(t, 4), 4);
        return v;
    }
    uint32_t length(uint32_t t) {
        uint32_t n = 0;
        while (*bytes(t + n, 1)) {
            step();
            ++n;
        }
        return n;
    }
    void copy(uint32_t dst, uint32_t src, uint32_t n) {
        uint32_t i = 0;
        for (; i + 4 <= n; i += 4) {
            step();
            uint32_t v = rawWord(src + i);
            std::memcpy(bytes(dst + i, 4), &v, 4);
        }
        for (; i < n; ++i) {
            step();
            *bytes(dst + i, 1) = *bytes(src + i, 1);
        }
    }
    uint32_t event(ClawResourceTableConstructionCall q) {
        step();
        uint32_t v;
        if (dependency)
            v = dependency(&table(), &q, user);
        else if (table().scene.call && q.argumentCount <= 4 && !q.localMask) {
            ClawSceneActorCall e{};
            e.function = q.function;
            e.receiver = q.receiver;
            e.argumentCount = q.argumentCount;
            std::copy_n(q.arguments, q.argumentCount, e.arguments);
            v = table().scene.call(table().scene.context, e);
        } else {
            fail(1);
            return 0;
        }
        if (table().fault)
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
    static uint32_t route(ClawResourceTableConstructionContext *, const ClawResourceTableConstructionCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        if (r.owns(q->function))
            return r.entry(q->function, q->receiver, q->arguments, q->argumentCount);
        return r.event(*q);
    }
    uint32_t frozen(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        uint32_t args[10]{}, v = 0;
        std::copy(a.begin(), a.end(), args);
        if (!claw_resource_table_construction_entry(f, t, args, uint32_t(a.size()), &table(), route, this, &v))
            fail(table().fault ? table().fault : 1);
        return v;
    }
    uint32_t data(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        ClawResourceDataContext context{};
        context.scene = table().scene;
        context.allocator = table().allocator;
        context.maximumOperations = table().maximumOperations;
        uint32_t v = 0;
        if (!claw_resource_data_entry(f, t, a, n, &context, dataRoute, this, &v))
            fail(context.fault ? context.fault : 1);
        return v;
    }
    static uint32_t dataRoute(ClawResourceDataContext *, const ClawResourceDataCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        ClawResourceTableConstructionCall out{};
        out.function = q->function;
        out.receiver = q->receiver;
        out.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, out.arguments);
        if (q->function == 0x4a7260 && q->arguments[0] == r.c.headerToken) {
            out.arguments[0] = 0;
            out.localMask = 1;
            out.bufferCount = 1;
            out.buffers[0] = r.bytes(r.c.headerToken, 168);
            out.bufferBytes[0] = 168;
        }
        if (r.owns(out.function))
            return r.entry(out.function, out.receiver, out.arguments, out.argumentCount);
        return r.event(out);
    }
    static uint32_t namespaceRoute(ClawResourceNamespaceContext *, const ClawResourceNamespaceCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        ClawResourceTableConstructionCall out{};
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
        return r.event(out);
    }
    uint32_t ns(uint32_t f, uint32_t t) {
        ClawResourceNamespaceContext context{};
        context.scene = table().scene;
        context.maximumOperations = table().maximumOperations;
        uint32_t v = 0;
        if (!claw_resource_namespace_entry(f, t, nullptr, 0, &context, namespaceRoute, this, &v))
            fail(context.fault ? context.fault : 1);
        return v;
    }
    static uint32_t arrayRoute(ClawCArrayContext *, const ClawCArrayCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        ClawResourceTableConstructionCall out{};
        out.function = q->function;
        out.receiver = q->receiver;
        out.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, out.arguments);
        return r.event(out);
    }
    uint32_t alloc(uint32_t n) {
        if (!table().allocator)
            return call(0x4f63ec, 0, {n});
        auto &a = *table().allocator;
        a.fault = 0;
        uint32_t v = 0;
        if (!claw_carray_entry(0x4f63ec, 0, n, 0, 0, &a, arrayRoute, this, &v))
            fail(a.fault ? a.fault : 1);
        return v;
    }
    void free(uint32_t p) {
        if (!table().allocator) {
            call(0x4f6428, 0, {p});
            return;
        }
        auto &a = *table().allocator;
        a.fault = 0;
        uint32_t v = 0;
        if (!claw_carray_entry(0x4f6428, 0, p, 0, 0, &a, arrayRoute, this, &v))
            fail(a.fault ? a.fault : 1);
    }
    uint32_t read(uint32_t t, uint32_t offset, uint32_t count, uint32_t dst) {
        uint32_t a[] = {offset, count, dst};
        return data(0x4b7ab0, t, a, 3);
    }
    uint32_t retry(uint32_t t) {
        uint32_t f = get(get(t) + 8);
        if (owns(f))
            return entry(f, t, nullptr, 0);
        return call(f, t);
    }
    uint32_t fileOpen(uint32_t t, const uint32_t *a) {
        do {
            step();
            uint32_t mode;
            if (a[2]) {
                if (a[1])
                    return 0;
                mode = 0x5324d0;
            } else
                mode = a[1] ? 0x532298 : 0x5324cc;
            put(t + 12, call(0x4f1d90, 0, {a[0], mode}));
            if (get(t + 12))
                break;
            if (!retry(t))
                return 0;
        } while (!get(t + 12));
        put(t + 32, a[1]);
        return 1;
    }
    uint32_t fileEnd(uint32_t t, bool flush) {
        if (get(t + 12)) {
            do {
                step();
                if (!call(flush ? 0x4a7920 : 0x4a7ae0, 0, {get(t + 12)}))
                    return 1;
            } while (retry(t));
        }
        return 0;
    }
    uint32_t directory(uint32_t t, uint32_t offset, uint32_t size) {
        put(t + 16, 0);
        put(t + 12, 0xffffffff);
        uint32_t block = alloc(size);
        if (!block)
            return 0;
        if (read(get(t + 24), offset, size, block) != size) {
            free(block);
            return 0;
        }
        uint32_t at = block, end = block + size, maximum = 0;
        while (at < end) {
            step();
            uint32_t kind = rawWord(at);
            if (kind == 1) {
                uint32_t off = rawWord(at + 4), len = rawWord(at + 8), stamp = rawWord(at + 12), name = at + 16;
                at = name + length(name) + 1;
                uint32_t p = alloc(76);
                if (p)
                    p = frozen(0x4b6600, p, {get(t + 24), t, name, off, len, stamp});
                frozen(0x4d5450, t + 60, {p + 36});
            } else {
                uint32_t off = rawWord(at + 4), len = rawWord(at + 8), stamp = rawWord(at + 12), id = rawWord(at + 16),
                         tag = rawWord(at + 20), count = rawWord(at + 24), name = at + 28,
                         meta = name + length(name) + 1;
                at = meta + length(meta) + 1;
                if (!*bytes(meta, 1))
                    meta = 0;
                uint32_t aux = 0;
                if (count) {
                    aux = alloc(count * 4);
                    for (uint32_t i = 0; i < count; ++i) {
                        step();
                        put(aux + i * 4, rawWord(at));
                        at += 4;
                    }
                }
                uint32_t ty = frozen(0x4b7170, t, {tag}), p = alloc(96);
                if (p) {
                    uint32_t a[] = {t, name, id, ty, meta, len, off, stamp, count, aux};
                    p = data(0x4b5ff0, p, a, 10);
                }
                frozen(0x4d5450, ty + 28, {p + 72});
                frozen(0x4d5450, ty + 36, {p + 48});
                put(t + 16, get(t + 16) + get(p + 20));
                if (get(p + 40) < get(t + 12))
                    put(t + 12, get(p + 40));
                if (maximum < get(p + 40))
                    maximum = get(p + 40);
                if (aux)
                    free(aux);
            }
        }
        free(block);
        return 1;
    }
    uint32_t recursive(uint32_t t, uint32_t offset, uint32_t size) {
        if (!size)
            return 1;
        if (!directory(t, offset, size))
            return 0;
        uint32_t success = 1, node = ns(0x4d54c0, t + 60);
        while (node) {
            step();
            uint32_t p = get(node + 20);
            if (!recursive(p, get(p + 4), get(p + 8)))
                success = 0;
            node = ns(0x4d5350, node);
        }
        return success;
    }
    uint32_t open(uint32_t t, const uint32_t *a) {
        put(t + 32, a[1]);
        uint32_t n = length(a[0]) + 1, p = alloc(n);
        put(t + 68, p);
        n = length(a[0]) + 1;
        copy(p, a[0], n);
        if (!fileOpen(t, a))
            return 0;
        put(t + 8, 1);
        if (a[2]) {
            put(t + 28, 168);
            put(t + 44, 1);
            p = alloc(76);
            if (p) {
                uint32_t stamp = frozen(0x4b7cc0, t);
                p = frozen(0x4b6600, p, {t, 0, 0x534938, 0, 0, stamp});
            }
            put(t + 36, p);
        } else {
            read(t, 0, 168, c.headerToken);
            const uint32_t fields[][2] = {{16, 131}, {28, 143}, {40, 147}, {20, 135}, {24, 139},
                                          {56, 155}, {48, 127}, {52, 151}, {60, 159}, {64, 163}};
            for (auto &field : fields)
                put(t + field[0], rawWord(c.headerToken + field[1]));
            put(t + 4, *bytes(c.headerToken + 167, 1));
            p = alloc(76);
            if (p)
                p = frozen(0x4b6600, p, {t, 0, 0x534938, get(t + 16), get(t + 20), get(t + 24)});
            put(t + 36, p);
            recursive(p, get(t + 16), get(t + 20));
        }
        return 1;
    }
    uint32_t close(uint32_t t, uint32_t compact) {
        if (!get(t + 32))
            call(0x4b7550, t);
        uint32_t result = compact ? call(0x4b76b0, t) : fileEnd(t, false);
        uint32_t root = get(t + 36);
        if (root) {
            frozen(0x4b66d0, root);
            free(root);
            put(t + 36, 0);
        }
        uint32_t path = get(t + 68);
        if (path) {
            free(path);
            put(t + 68, 0);
        }
        put(t + 8, 0);
        return result;
    }
    void destroy(uint32_t t) {
        put(t, 0x513578);
        if (get(t + 8))
            close(t, 0);
        if (get(t + 12))
            fileEnd(t, false);
        uint32_t root = get(t + 36);
        if (root) {
            frozen(0x4b66d0, root);
            free(root);
            put(t + 36, 0);
        }
        if (get(t + 68)) {
            free(get(t + 68));
            put(t + 68, 0);
        }
        for (uint32_t off : {8u, 12u, 16u, 20u, 24u, 28u, 36u, 40u, 44u, 52u, 56u, 60u, 64u, 68u})
            put(t + off, 0);
        put(t + 32, 1);
        put(t + 48, 1);
        put(t + 4, 1);
    }
    uint32_t entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        uint32_t required = f == 0x4b72e0 || f == 0x4b7bd0   ? 3
                            : f == 0x4b6b60 || f == 0x4b6ed0 ? 2
                            : f == 0x4b74d0                  ? 1
                                                             : 0;
        if (n != required || (n && !a))
            fail(4);
        switch (f) {
        case 0x4b7210:
            put(t, 0x513578);
            for (uint32_t off : {8u, 12u, 16u, 28u, 36u, 40u, 44u, 48u, 52u, 56u, 60u, 64u, 68u})
                put(t + off, 0);
            put(t + 32, 1);
            put(t + 4, 1);
            return t;
        case 0x4b72e0:
            return open(t, a);
        case 0x4b6b60:
            return recursive(t, a[0], a[1]);
        case 0x4b6ed0:
            return directory(t, a[0], a[1]);
        case 0x4b7bd0:
            return fileOpen(t, a);
        case 0x4b7c40:
            return fileEnd(t, false);
        case 0x4b7c80:
            return fileEnd(t, true);
        case 0x4b74d0:
            return close(t, a[0]);
        case 0x4b7250:
            destroy(t);
            return 0;
        default:
            return 0;
        }
    }
    static bool owns(uint32_t f) {
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
            return false;
        }
    }
};
} // namespace
extern "C" uint32_t claw_resource_archive_loading_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                        ClawResourceArchiveLoadingContext *c,
                                                        ClawResourceTableConstructionDependency d, void *u,
                                                        uint32_t *r) {
    if (!c || !c->table || !r || !Run::owns(f))
        return 0;
    try {
        Run run{*c, d, u};
        *r = run.entry(f, t, a, n);
        return c->table->fault ? 0 : 1;
    } catch (Fault &) {
    }
    return 0;
}
