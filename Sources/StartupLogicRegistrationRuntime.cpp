#include "StartupLogicRegistrationRuntime.h"
#include "LogicRegistry.h"
#include "WorldObjectRuntime.h"
#include "PlayerFadeBlendRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
#include "StartupLogicRegistrationProgram.inc"
struct Failure {};
template <class T> struct Restore {
    T &x;
    T old;
    explicit Restore(T &v) : x(v), old(v) {
    }
    ~Restore() {
        x = old;
    }
};
struct Run {
    ClawStartupLogicRegistrationContext &c;
    ClawStartupLogicRegistrationDependency d;
    void *u;
    uint32_t operations = 0;
    [[noreturn]] void fail(uint32_t n = 1) {
        if (!c.fault)
            c.fault = n;
        throw Failure{};
    }
    void tick() {
        if (c.fault)
            throw Failure{};
        if (++operations > (c.maximumOperations ? c.maximumOperations : 1000000))
            fail(3);
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        tick();
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
    uint32_t event(const ClawStartupLogicRegistrationCall &q) {
        tick();
        if (!d)
            fail();
        auto v = d(&c, &q, u);
        if (c.fault)
            throw Failure{};
        return v;
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawStartupLogicRegistrationCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        return invoke(q);
    }
    static uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
        auto &r = *static_cast<Run *>(u);
        return r.c.scene.lookup ? r.c.scene.lookup(r.c.scene.context, t, n) : nullptr;
    }
    static uint32_t allocate(void *u, uint32_t n) {
        return static_cast<Run *>(u)->call(0x4f63ec, 0, {n});
    }
    static void release(void *u, uint32_t p) {
        static_cast<Run *>(u)->call(0x4f6428, 0, {p});
    }
    static uint32_t hostCall(void *u, ClawSceneActorCall e) {
        ClawStartupLogicRegistrationCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, q.arguments);
        return static_cast<Run *>(u)->invoke(q);
    }
    static uint32_t clock(void *u) {
        auto &r = *static_cast<Run *>(u);
        if (!r.c.scene.readClock)
            r.fail();
        return r.c.scene.readClock(r.c.scene.context);
    }
    ClawSceneActorHost host() {
        return {this, lookup, allocate, release, hostCall, clock};
    }
    static uint32_t dictionaryService(ClawImageControllerLoadingContext *, const ClawImageControllerLoadingCall *q,
                                      void *u) {
        return static_cast<Run *>(u)->invoke(*q);
    }
    static uint32_t stringService(ClawCStringAssignmentContext *, const ClawCStringAssignmentCall *q, void *u) {
        ClawStartupLogicRegistrationCall e{};
        e.function = q->function;
        e.receiver = q->receiver;
        e.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, e.arguments);
        return static_cast<Run *>(u)->invoke(e);
    }
    static uint32_t lifecycleService(ClawSceneLifecycleContext *, const ClawSceneLifecycleCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        ClawStartupLogicRegistrationCall e{};
        e.function = q->function;
        e.receiver = q->receiver;
        e.argumentCount = q->argumentCount;
        if (q->bufferCount > 2 || e.argumentCount > 10)
            r.fail(2);
        std::copy_n(q->arguments, q->argumentCount, e.arguments);
        e.localMask = q->localMask;
        e.bufferCount = q->bufferCount;
        for (uint32_t i = 0; i < e.bufferCount; ++i) {
            e.buffers[i] = q->buffers[i];
            e.bufferBytes[i] = q->bufferBytes[i];
        }
        return e.localMask ? r.event(e) : r.invoke(e);
    }
    uint32_t initialize(uint32_t t, uint32_t callback, uint32_t flags) {
        if (!callback)
            return 0;
        ClawWorldObjectRuntime projection{};
        ClawWorldObjectContext context{};
        std::copy_n(span(t, 93), 93, projection.logic);
        context.entryCallback = callback;
        context.entryFlags = flags;
        auto result = claw_world_object_initialize(&projection, &context, 0, 0, 0);
        std::copy_n(projection.logic, 93, span(t, 93));
        return result;
    }
    uint32_t factory(uint32_t t, const uint32_t *a) {
        uint32_t object = call(0x4f63ec, 0, {372});
        if (object) {
            put(object + 4, get(t + 28));
            put(object + 8, 0);
            put(object + 12, get(t + 12));
            put(object, 0x513740);
            for (uint32_t i = 16; i <= 28; i += 4)
                put(object + i, 0);
        }
        uint32_t init = get(get(object) + 0x24);
        if (!call(init, object, {a[0], a[2]})) {
            if (object)
                call(get(get(object) + 4), object, {1});
            return 0;
        }
        uint32_t slot = call(0x4f62a8, t + 16, {a[1]});
        put(slot, object);
        return object;
    }
    void populate(uint32_t scene) {
        for (const auto &i : program) {
            tick();
            if (!i.ordinal) {
                call(i.function, 0);
                continue;
            }
            const auto *entry = claw_logic_registry_at(i.ordinal - 1);
            if (!entry || entry->callback != i.function)
                fail(2);
            uint32_t registry = get(scene + 20), f = get(get(registry) + 0x24);
            call(f, registry, {entry->callback, entry->originalNameAddress, entry->flags});
        }
    }
    uint32_t invoke(const ClawStartupLogicRegistrationCall &q) {
        tick();
        if (q.argumentCount > 10)
            fail(2);
        if (q.localMask)
            return event(q);
        if (q.function == 0x401000) {
            if (q.argumentCount != 1)
                fail(2);
            populate(q.arguments[0]);
            return 0;
        }
        if (q.function == 0x4d6340) {
            if (q.argumentCount != 3)
                fail(2);
            return factory(q.receiver, q.arguments);
        }
        if (q.function == 0x4c8160) {
            if (q.argumentCount != 2)
                fail(2);
            return initialize(q.receiver, q.arguments[0], q.arguments[1]);
        }
        if (q.function == 0x4f6433) {
            ClawPlayerFadeContext fade{};
            ClawPlayerFadeBlendContext blend{};
            blend.fade = &fade;
            uint32_t out = 0;
            if (!claw_player_fade_blend_entry(q.function, q.receiver, q.arguments, q.argumentCount, &blend, nullptr,
                                              nullptr, &out) ||
                fade.fault)
                fail(fade.fault ? fade.fault : 2);
            return out;
        }
        uint32_t out = 0, covered = 0;
        if (c.dictionary) {
            Restore<ClawSceneActorHost> r(c.dictionary->scene);
            c.dictionary->scene = host();
            covered = claw_image_controller_loading_entry(q.function, q.receiver, q.arguments, q.argumentCount,
                                                          c.dictionary, dictionaryService, this, &out);
            if (c.dictionary->fault)
                fail(c.dictionary->fault);
            if (covered)
                return out;
        }
        if (c.strings) {
            Restore<ClawSceneActorHost> r(c.strings->scene);
            c.strings->scene = host();
            covered = claw_cstring_assignment_entry(q.function, q.receiver, q.arguments, q.argumentCount, c.strings,
                                                    stringService, this, &out);
            if (c.strings->fault)
                fail(c.strings->fault);
            if (covered)
                return out;
        }
        if (c.lifecycle) {
            Restore<ClawSceneActorHost> r(c.lifecycle->scene);
            c.lifecycle->scene = host();
            covered = claw_scene_lifecycle_entry(q.function, q.receiver, q.arguments, q.argumentCount, c.lifecycle,
                                                 lifecycleService, this, &out);
            if (c.lifecycle->fault)
                fail(c.lifecycle->fault);
            if (covered)
                return out;
        }
        if (c.destruction) {
            covered = claw_actor_destruction_entry(q.function, q.receiver, q.argumentCount ? q.arguments[0] : 0,
                                                   c.destruction, host(), &c.fault, &out);
            if (c.fault)
                fail(c.fault);
            if (covered)
                return out;
        }
        return event(q);
    }
};
} // namespace
extern "C" uint32_t claw_startup_logic_registration_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                          ClawStartupLogicRegistrationContext *c,
                                                          ClawStartupLogicRegistrationDependency d, void *u,
                                                          uint32_t *out) {
    if (!c || !out || c->fault || n > 10 || (n && !a))
        return 0;
    if (f != 0x401000 && f != 0x4d6340 && f != 0x4c8160)
        return 0;
    try {
        Run r{*c, d, u};
        ClawStartupLogicRegistrationCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        std::copy_n(a, n, q.arguments);
        *out = r.invoke(q);
        return 1;
    } catch (Failure &) {
    }
    return 0;
}
