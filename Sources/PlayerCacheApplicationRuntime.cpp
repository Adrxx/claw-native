#include "PlayerCacheApplicationRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
bool owned(uint32_t);
uint32_t arity(uint32_t);
int32_t si(uint32_t v) {
    int32_t s;
    std::memcpy(&s, &v, 4);
    return s;
}
struct Run {
    ClawPlayerCacheApplicationContext &c;
    ClawPlayerCacheApplicationDependency d;
    void *u;
    uint32_t operations = 0;
    [[noreturn]] void fail(uint32_t v = 1) {
        if (!c.fault)
            c.fault = v;
        throw Failure{};
    }
    void step() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 65536))
            fail(3);
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (c.fault)
            throw Failure{};
        if (t < 4096)
            fail(2);
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p)
            fail();
        return p;
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    uint8_t *bytes(uint32_t t, uint32_t n) {
        return reinterpret_cast<uint8_t *>(span(t & ~3u, (n + (t & 3u) + 3) / 4)) + (t & 3u);
    }
    uint32_t event(ClawPlayerCacheApplicationCall &q) {
        step();
        if (!d)
            fail();
        auto v = d(&c, &q, u);
        if (c.fault)
            throw Failure{};
        return v;
    }
    uint32_t invoke(uint32_t, uint32_t, const uint32_t *, uint32_t);
    uint32_t invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        return invoke(f, t, a.begin(), uint32_t(a.size()));
    }
    uint32_t service(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        ClawPlayerCacheApplicationCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        std::copy_n(a, n, q.arguments);
        if (n && (f == 0x49bee0 || f == 0x49b840 || f == 0x49bdb0 || f == 0x4a3cf0))
            q.name = reinterpret_cast<const char *>(bytes(a[0], 1));
        return event(q);
    }
    static uint32_t *lookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->span(t, n);
    }
    static uint8_t *lookupBytes(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->bytes(t, n);
    }
    static uint32_t allocate(void *p, uint32_t n) {
        return static_cast<Run *>(p)->invoke(0x4f63ec, 0, {n});
    }
    static void free(void *p, uint32_t t) {
        static_cast<Run *>(p)->invoke(0x4f6428, 0, {t});
    }
    static uint32_t call(void *p, ClawSceneActorCall q) {
        return static_cast<Run *>(p)->invoke(q.function, q.receiver, q.arguments, q.argumentCount);
    }
    static uint32_t clock(void *p) {
        auto &r = *static_cast<Run *>(p);
        if (!r.c.scene.readClock)
            r.fail();
        return r.c.scene.readClock(r.c.scene.context);
    }
    ClawSceneActorHost host() {
        return {this, lookup, allocate, free, call, clock};
    }
    static uint32_t saved(ClawSaveLoadContext *, const ClawSaveLoadCall *q, void *p) {
        return static_cast<Run *>(p)->invoke(q->function, q->receiver, q->arguments, q->argumentCount);
    }
    uint32_t local(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, uint32_t mask, void *buffer, uint32_t size) {
        ClawPlayerCacheApplicationCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        std::copy_n(a, n, q.arguments);
        q.localMask = mask;
        q.bufferCount = 1;
        q.buffers[0] = buffer;
        q.bufferBytes[0] = size;
        return event(q);
    }
    void registryField(uint32_t app, uint32_t key, uint32_t token) {
        *bytes(token, 1) = 0;
        put(c.automaticToken + 300, 80);
        uint32_t a[] = {key, token, c.automaticToken + 300, 0};
        invoke(0x4b5e90, get(app + 0x38), a, 4);
    }
    uint32_t modal(uint32_t app, uint32_t name, uint32_t procedure) {
        if (!name || !procedure)
            return 0;
        auto scene = get(app + 0x30);
        if (scene) {
            auto holder = get(scene + 4);
            invoke(0x4ca9e0, holder, {get(holder + 0x14)});
            auto surface = get(get(get(app + 0x30) + 0x1c));
            invoke(get(get(surface) + 0x28), 0, {surface});
        }
        auto initial = invoke(0x546d54, 0, {1});
        while (si(invoke(0x546d54, 0, {1})) < 0)
            step();
        auto v = invoke(0x546d2c, 0, {get(get(app + 8) + 12), name, get(get(app + 4) + 4), procedure, 0});
        if (si(initial) < 1)
            while (si(invoke(0x546d54, 0, {0})) >= 0)
                step();
        invoke(0x42abf0, app);
        return v;
    }
    uint32_t startup(uint32_t app, uint32_t name) {
        auto manager = invoke(0x4f63ec, 0, {88});
        if (manager) {
            if (!c.saveLoad)
                fail();
            auto q = c.saveLoad->save;
            q.scene = host();
            q.lookupBytes = lookupBytes;
            q.emptyStringToken = get(0x52e1cc);
            q.fault = 0;
            if (!claw_save_file_initialize_manager(manager, &q) || q.fault)
                fail(q.fault ? q.fault : 1);
        }
        put(app + 0x60, manager);
        if (!invoke(0x49b840, manager, {0x525618})) {
            invoke(0x429e10, app, {0x800a, 0x6aa});
            return 0;
        }
        invoke(0x42bf90, app, {invoke(0x49bee0, get(app + 0x60), {name})});
        if (!get(app + 0x64)) {
            auto first = c.automaticToken;
            registryField(app, 0x52560c, first);
            registryField(app, 0x5255fc, first + 100);
            registryField(app, 0x5255f0, first + 200);
            if (*bytes(first, 1)) {
                auto record = invoke(0x49bee0, get(app + 0x60), {first});
                if (!record)
                    record = invoke(0x49bdb0, get(app + 0x60), {first, first + 100, first + 200, 0});
                invoke(0x42bf90, app, {record});
            }
            for (uint32_t key : {0x52560cu, 0x5255fcu, 0x5255f0u})
                invoke(0x4b5f80, get(app + 0x38), {key});
            if (!get(app + 0x64))
                invoke(0x42bf90, app, {invoke(0x49bee0, get(app + 0x60), {0x5255e8})});
        }
        return 1;
    }
};
uint32_t body(Run &r, uint32_t f, uint32_t t, const uint32_t *a) {
    switch (f) {
    case 0x42bf90:
        r.put(0x53725c, 0);
        r.put(t + 100, a[0]);
        if (a[0]) {
            auto input = r.get(0x537204);
            if (input)
                r.invoke(0x430ac0, input, {a[0]});
            r.put(0x53725c, (r.get(r.get(t + 100) + 4) & 4) >> 2);
        }
        return 0;
    case 0x430ac0:
        if (!a[0] || a[0] + 0x2604 == 0)
            return 0;
        for (uint32_t i = 0; i < 10; ++i)
            r.put(t + 0x10 + i * 4, r.get(a[0] + 0x2618 + i * 4));
        if (a[0] + 0x25c0 == 0)
            return 0;
        for (uint32_t i = 0; i < 10; ++i)
            r.put(t + 0x48 + i * 4, r.get(a[0] + 0x25d4 + i * 4));
        return 1;
    case 0x42bbb0:
        r.invoke(0x546d50, 0, {r.get(r.get(t + 4) + 4), 0x111, 0x8090, 5});
        return 0;
    case 0x42bbd0:
        r.modal(t, 0x525f30, 0x49b730);
        return 0;
    case 0x42bbe0:
        r.modal(t, 0x525f3c, 0x49b160);
        return 0;
    case 0x42bbf0:
        if (r.get(t + 100) && si(r.get(r.get(t + 96) + 12)) > 1 && si(r.modal(t, 0x525f48, 0x49b630)) > 0)
            r.invoke(0x546d50, 0, {r.get(r.get(t + 4) + 4), 0x111, 0x8090, 6});
        return 0;
    case 0x42bb00:
        return r.modal(t, a[0], a[1]);
    case 0x49b050: {
        if (!a[0])
            return 0;
        auto app = r.get(0x5371fc), selected = r.get(app + 100);
        if (selected) {
            r.invoke(0x546d3c, 0, {a[0], 0x441, selected + 20});
            return 1;
        }
        r.invoke(0x42bf90, app, {r.invoke(0x49bee0, r.get(app + 96), {0x5255e8})});
        r.invoke(0x546d3c, 0, {a[0], 0x441, 0x5255e8});
        return 1;
    }
    case 0x49b0c0: {
        if (!a[0])
            return 0;
        auto index = r.invoke(0x546d44, 0, {a[0], 0x188, 0, 0});
        if (index == 0xffffffff)
            return 0;
        auto text = r.bytes(r.c.automaticToken, 256);
        text[0] = 0;
        uint32_t args[] = {a[0], 0x189, index, 0};
        if (r.local(0x546d44, 0, args, 4, 8, text, 256) == 0xffffffff)
            return 0;
        auto app = r.get(0x5371fc);
        auto selected = r.invoke(0x49bee0, r.get(app + 96), {r.c.automaticToken});
        if (!selected)
            return 0;
        r.invoke(0x42bf90, app, {selected});
        return 1;
    }
    case 0x49c090: {
        if (!a[0])
            return 0;
        r.invoke(0x546d44, 0, {a[0], 0x184, 0, 0});
        if (si(r.get(t + 12)) < 1)
            return 0;
        uint32_t count = 0;
        for (auto node = r.get(t + 4); node;) {
            r.step();
            auto next = r.get(node), record = r.get(node + 8);
            if (a[2] && r.invoke(0x4a3cf0, 0, {record + 20, 0x5255e8}) == 0)
                record = 0;
            node = next;
            if (record && r.invoke(0x546d44, 0, {a[0], 0x180, 0, record + 20}) != 0xffffffff)
                ++count;
        }
        if (a[1]) {
            auto index = r.invoke(0x546d44, 0, {a[0], 399, 0, a[1] + 20});
            if (index != 0xffffffff)
                r.invoke(0x546d44, 0, {a[0], 0x186, index, 0});
        }
        return count;
    }
    case 0x49b730: {
        auto window = a[0];
        if (a[1] == 0x110) {
            r.put(0x53ebec, r.invoke(0x546d40, 0, {window, 0x43b}));
            auto app = r.get(0x5371fc);
            if (!app || !r.get(app + 96)) {
                r.invoke(0x546d34, 0, {window, 0});
                return 1;
            }
            r.put(0x53ebe0, r.get(app + 100));
            r.invoke(0x49c090, r.get(app + 96), {r.get(0x53ebec), r.get(0x53ebe0), 0});
            r.invoke(0x49b050, 0, {window});
            return 1;
        }
        if (a[1] == 0x111) {
            if (a[2] == 1) {
                r.invoke(0x49b0c0, 0, {r.get(0x53ebec)});
                r.invoke(0x546d34, 0, {window, 0});
                return 1;
            }
            if (a[2] == 2) {
                r.invoke(0x546d34, 0, {window, 0});
                return 1;
            }
            if (r.get(0x53ebec) && a[3] == r.get(0x53ebec) && int16_t(a[2] >> 16) == 2) {
                r.invoke(0x49b0c0, 0, {r.get(0x53ebec)});
                r.invoke(0x546d34, 0, {window, 0});
                return 1;
            }
        }
        return 0;
    }
    default:
        r.fail(3);
    }
}
uint32_t Run::invoke(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
    step();
    if (n > 40)
        fail(3);
    if (owned(f)) {
        if (n != arity(f))
            fail(3);
        return body(*this, f, t, a);
    }
    if (c.composeSaveLoad && c.saveLoad) {
        auto q = *c.saveLoad;
        q.save.scene = host();
        q.save.lookupBytes = lookupBytes;
        q.save.fault = q.fault = 0;
        uint32_t out = 0;
        if (claw_save_load_entry(f, t, a, n, &q, saved, this, &out)) {
            if (q.fault || q.save.fault)
                fail(q.fault ? q.fault : q.save.fault);
            return out;
        }
        if (q.fault || q.save.fault)
            fail(q.fault ? q.fault : q.save.fault);
    }
    return service(f, t, a, n);
}
bool owned(uint32_t f) {
    switch (f) {
    case 0x42bf90:
    case 0x430ac0:
    case 0x42bbb0:
    case 0x42bbd0:
    case 0x42bbe0:
    case 0x42bbf0:
    case 0x42bb00:
    case 0x49b050:
    case 0x49b0c0:
    case 0x49c090:
    case 0x49b730:
        return true;
    default:
        return false;
    }
}
uint32_t arity(uint32_t f) {
    if (f == 0x42bf90 || f == 0x430ac0 || f == 0x49b050 || f == 0x49b0c0)
        return 1;
    if (f == 0x42bb00)
        return 2;
    if (f == 0x49c090)
        return 3;
    if (f == 0x49b730)
        return 4;
    return 0;
}
} // namespace
extern "C" uint32_t claw_player_cache_application_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                        ClawPlayerCacheApplicationContext *c,
                                                        ClawPlayerCacheApplicationDependency d, void *u,
                                                        uint32_t *out) {
    if (!c || !out || !owned(f))
        return 0;
    if (n != arity(f) || (n && !a)) {
        c->fault = 3;
        return 0;
    }
    try {
        Run r{*c, d, u};
        *out = body(r, f, t, a);
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
extern "C" uint32_t claw_player_cache_application_startup_span(uint32_t app, uint32_t name,
                                                               ClawPlayerCacheApplicationContext *c,
                                                               ClawPlayerCacheApplicationDependency d, void *u,
                                                               uint32_t *out) {
    if (!c || !out)
        return 0;
    try {
        Run r{*c, d, u};
        *out = r.startup(app, name);
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
