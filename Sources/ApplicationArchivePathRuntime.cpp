#include "ApplicationArchivePathRuntime.h"
#include "ActorDestruction.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
#include <vector>
namespace {
struct Failure {};
struct Run {
    ClawApplicationArchivePathContext &c;
    ClawApplicationArchivePathDependency d;
    void *u;
    uint32_t operations = 0;
    uint32_t partialToken = 0, partialBytes = 0;
    std::vector<uint32_t> partial;
    Run(ClawApplicationArchivePathContext &c, ClawApplicationArchivePathDependency d, void *u) : c(c), d(d), u(u) {
    }
    [[noreturn]] void fail(uint32_t f = 1) {
        if (!c.fault)
            c.fault = f;
        throw Failure{};
    }
    void step() {
        if (c.fault)
            throw Failure{};
        if (++operations > (c.maximumOperations ? c.maximumOperations : 1000000))
            fail(3);
    }
    uint32_t *strict(uint32_t t, uint32_t n) {
        step();
        return c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        auto *p = strict(t, n);
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
    uint8_t *strictBytes(uint32_t t, uint32_t n) {
        step();
        if (c.bytes)
            return c.bytes(c.byteContext, t, n);
        if (c.strings && c.strings->bytes)
            return c.strings->bytes(c.strings->byteContext, t, n);
        auto *p = strict(t & ~3u, (n + (t & 3u) + 3) / 4);
        return p ? reinterpret_cast<uint8_t *>(p) + (t & 3u) : nullptr;
    }
    uint8_t *bytes(uint32_t t, uint32_t n) {
        auto *p = strictBytes(t, n);
        if (!p)
            fail();
        return p;
    }
    void flush() {
        if (!partialBytes)
            return;
        auto n = partialBytes;
        partialBytes = 0;
        std::memcpy(bytes(partialToken, n), partial.data(), n);
    }
    uint32_t *constructorLookup(uint32_t t, uint32_t n) {
        auto *p = strict(t, n);
        if (p)
            return p;
        if (!(t & 3u) && n && n < 65536) {
            if (partialBytes && partialToken == t && partial.size() == n)
                return partial.data();
            flush();
            for (uint32_t tail = 1; tail <= 3 && tail < n * 4; ++tail) {
                auto valid = n * 4 - tail;
                auto *b = strictBytes(t, valid);
                if (b) {
                    partialToken = t;
                    partialBytes = valid;
                    partial.assign(n, 0);
                    std::memcpy(partial.data(), b, valid);
                    return partial.data();
                }
            }
        }
        return nullptr;
    }
    static uint32_t *lookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->strict(t, n);
    }
    static uint32_t *ctorLookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->constructorLookup(t, n);
    }
    static uint8_t *byteLookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->strictBytes(t, n);
    }
    static uint32_t allocate(void *p, uint32_t n) {
        return static_cast<Run *>(p)->invoke(0x4f63ec, 0, {n});
    }
    static void release(void *p, uint32_t t) {
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
    ClawSceneActorHost host(bool constructor = false) {
        return {this, constructor ? ctorLookup : lookup, allocate, release, call, clock};
    }
    uint32_t event(ClawApplicationArchivePathCall &q) {
        step();
        flush();
        if (!d)
            fail();
        auto v = d(&c, &q, u);
        if (c.fault)
            throw Failure{};
        return v;
    }
    uint32_t external(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        if (n > 8)
            fail(2);
        ClawApplicationArchivePathCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        std::copy_n(a, n, q.arguments);
        return event(q);
    }
    static uint32_t stringService(ClawCStringAssignmentContext *, const ClawCStringAssignmentCall *q, void *p) {
        return static_cast<Run *>(p)->invoke(q->function, q->receiver, q->arguments, q->argumentCount);
    }
    static uint32_t fadeService(ClawPlayerFadeContext *, const ClawPlayerFadeCall *q, void *p) {
        return static_cast<Run *>(p)->invoke(q->function, q->receiver, q->arguments, q->argumentCount);
    }
    uint32_t invoke(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        step();
        if (f == 0x42cab0) {
            if (n)
                fail(2);
            return admission(t);
        }
        if (f == 0x48c190) {
            if (n != 1)
                fail(2);
            return exists(a[0]);
        }
        uint32_t v = 0;
        if (c.strings) {
            flush();
            auto q = *c.strings;
            q.scene = host();
            q.byteContext = this;
            q.bytes = byteLookup;
            q.fault = 0;
            if (claw_cstring_assignment_entry(f, t, a, n, &q, stringService, this, &v)) {
                if (q.fault)
                    fail(q.fault);
                return v;
            }
            if (q.fault)
                fail(q.fault);
            if (f == 0x4f65f2) {
                if (!q.allocation || !q.allocation->fade)
                    fail();
                auto fade = *q.allocation->fade;
                fade.scene = host(true);
                fade.fault = 0;
                auto allocation = *q.allocation;
                allocation.fade = &fade;
                allocation.emptyStringToken = get(0x52e1cc);
                if (!claw_player_fade_blend_entry(f, t, a, n, &allocation, fadeService, this, &v) || fade.fault)
                    fail(fade.fault ? fade.fault : 1);
                flush();
                return v;
            }
            if (f == 0x4f6584) {
                if (n)
                    fail(2);
                ClawActorDestructionGlobals globals{0, 0, get(0x52e1cc)};
                uint32_t fault = 0;
                if (!claw_actor_destruction_entry(f, t, 0, &globals, host(), &fault, &v) || fault)
                    fail(fault ? fault : 1);
                return v;
            }
        }
        return external(f, t, a, n);
    }
    uint32_t invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        return invoke(f, t, a.begin(), uint32_t(a.size()));
    }
    uint32_t local(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a, uint32_t mask, void *b, uint32_t size) {
        ClawApplicationArchivePathCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        q.localMask = mask;
        q.bufferCount = 1;
        q.buffers[0] = b;
        q.bufferBytes[0] = size;
        return event(q);
    }
    uint32_t exists(uint32_t path) {
        if (!path || !*bytes(path, 1))
            return 0;
        return local(0x546a30, 0, {path, 0, 0x4000}, 2, bytes(c.openFileToken, 136), 136) != 0xffffffffu;
    }
    void destroy(uint32_t token) {
        invoke(0x4f6584, token + 8);
        invoke(0x4f6584, token + 4);
        invoke(0x4f6584, token);
    }
    uint32_t admission(uint32_t app) {
        put(app + 0x104, get(0x53724c) || get(0x537250) ? 1 : 0);
        auto directory = c.automaticToken, strings = directory + 256;
        if (!local(0x546a28, 0, {255, 0}, 2, bytes(directory, 256), 256))
            return 0;
        uint8_t drive = uint8_t(invoke(0x42b020, app));
        put(app + 0x108, drive == *bytes(directory, 1));
        put(app + 0x10c, 0);
        put(app + 0x110, 0);
        put(app + 0x114, 0);
        const uint32_t names[] = {0x526244, 0x526238, 0x52622c};
        for (uint32_t i = 0; i < 3; ++i)
            invoke(0x4f65f2, strings + 4 * i, {names[i]});
        for (uint32_t i = 0; i < 3; ++i)
            local(0x4f4f58, 0, {app + 0xf8 + 4 * i, 0x525f78, 0, get(strings + 4 * i)}, 4, bytes(directory, 256), 256);
        uint32_t hires = 1, base = 1;
        auto signedDrive = uint32_t(int32_t(int8_t(drive)));
        if (!invoke(0x48c190, 0, {get(app + 0xfc)})) {
            if (!get(app + 0x108) && drive) {
                invoke(0x4f4f58, 0, {app + 0xfc, 0x52621c, signedDrive, get(strings + 4)});
                if (invoke(0x48c190, 0, {get(app + 0xfc)})) {
                    put(app + 0x110, 1);
                    goto baseProbe;
                }
            }
            hires = 0;
        }
    baseProbe:
        if (!invoke(0x48c190, 0, {get(app + 0xf8)})) {
            if (!get(app + 0x108) && drive) {
                invoke(0x4f4f58, 0, {app + 0xf8, 0x526210, signedDrive, get(strings)});
                if (invoke(0x48c190, 0, {get(app + 0xf8)})) {
                    put(app + 0x10c, 1);
                    goto movieProbe;
                }
            }
            base = 0;
        }
    movieProbe:
        if (!invoke(0x48c190, 0, {get(app + 0x100)}) && !get(app + 0x108) && drive) {
            invoke(0x4f4f58, 0, {app + 0x100, 0x526200, signedDrive, get(strings + 8)});
            if (invoke(0x48c190, 0, {get(app + 0x100)}))
                put(app + 0x114, 1);
        }
        uint32_t error = 0;
        if (get(app + 0x104) && !hires) {
            if (!invoke(0x42ce90, app, {8}))
                error = 0x8010;
        } else if (!base)
            error = 0x800b;
        if (error)
            invoke(0x429e10, app, {error, 0x3eb});
        destroy(strings);
        return error ? 0 : 1;
    }
};
} // namespace
extern "C" uint32_t claw_application_archive_path_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                        ClawApplicationArchivePathContext *c,
                                                        ClawApplicationArchivePathDependency d, void *u,
                                                        uint32_t *out) {
    if (!c || !out || c->fault || (f != 0x42cab0 && f != 0x48c190))
        return 0;
    if (n != (f == 0x48c190 ? 1u : 0u) || (n && !a)) {
        c->fault = 2;
        return 0;
    }
    try {
        Run r{*c, d, u};
        *out = r.invoke(f, t, a, n);
        r.flush();
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
