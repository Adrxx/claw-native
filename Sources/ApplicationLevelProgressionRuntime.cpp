#include "ApplicationLevelProgressionRuntime.h"
#include "MovieStateCleanupBridge.h"
#include <algorithm>
#include <cstring>
#include <cmath>
#include <initializer_list>
namespace {
struct Failure {};
int32_t si(uint32_t v) {
    int32_t s;
    std::memcpy(&s, &v, 4);
    return s;
}
[[maybe_unused]] uint32_t ftol(double v) {
    if (!std::isfinite(v) || v >= 0x1p63 || v < -0x1p63)
        return 0;
    return uint32_t(int64_t(v));
}
[[maybe_unused]] double mul(double a, double b) {
    volatile double v = a * b;
    return v;
}
[[maybe_unused]] double div(double a, double b) {
    volatile double v = a / b;
    return v;
}
bool owned(uint32_t);
struct Run {
    ClawApplicationLevelProgressionContext &c;
    ClawApplicationLevelProgressionDependency d;
    void *u;
    uint32_t operations = 0;
    ClawSpecialCommandGlobals *specialAliases = nullptr;
    [[noreturn]] void fail(uint32_t n = 1) {
        if (!c.fault)
            c.fault = n;
        throw Failure{};
    }
    void step() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 1000000))
            fail(3);
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (c.fault)
            throw Failure{};
        if (t < 4096)
            fail(2);
        auto p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
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
    double real(uint32_t t) {
        double v;
        std::memcpy(&v, span(t, 2), 8);
        return v;
    }
    void real(uint32_t t, double v) {
        std::memcpy(span(t, 2), &v, 8);
    }
    const char *text(uint32_t t) {
        return reinterpret_cast<const char *>(span(t & ~3)) + (t & 3);
    }
    uint32_t event(ClawApplicationLevelProgressionCall &q) {
        if (!d)
            fail();
        auto v = d(&c, &q, u);
        if (c.fault)
            throw Failure{};
        return v;
    }
    uint32_t call(uint32_t f, uint32_t p, const uint32_t *a, uint32_t n) {
        ClawApplicationLevelProgressionCall q{};
        q.function = f;
        q.receiver = p;
        q.argumentCount = n;
        if (n > 40)
            fail(3);
        std::copy_n(a, n, q.arguments);
        if (n && (f == 0x4f6286 || f == 0x4b7f20 || f == 0x4b7cd0 || f == 0x4b68c0 || f == 0x4b67f0 || f == 0x4f66cc ||
                  f == 0x4f65f2 || f == 0x4b54a0 || f == 0x4b54f0 || f == 0x4c7970 || f == 0x4c79e0))
            q.name = text(a[0]);
        return event(q);
    }
    uint32_t invoke(uint32_t, uint32_t, std::initializer_list<uint32_t> = {});
    uint32_t virt(uint32_t p, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        if (!p)
            fail(2);
        auto vt = get(p), f = claw_application_level_progression_function(vt, slot);
        if (!f)
            f = get(vt + slot);
        return invoke(f, p, a);
    }
    uint32_t allocate(uint32_t n) {
        return invoke(0x4f63ec, 0, {n});
    }
    void post(uint32_t p, uint32_t cmd) {
        invoke(0x546d50, 0, {get(get(p + 4) + 4), 0x111, cmd, 0});
    }
    void cursor() {
        while (si(invoke(0x546d54, 0, {0})) >= 0)
            step();
    }
    static uint32_t *lookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->span(t, n);
    }
    static uint32_t hostCall(void *p, ClawSceneActorCall e) {
        auto &r = *static_cast<Run *>(p);
        r.commitApplication();
        if (e.function == 0x546d5c && e.receiver && e.argumentCount == 4) {
            auto v =
                r.invoke(e.function, 0, {e.receiver, e.arguments[0], e.arguments[1], e.arguments[2], e.arguments[3]});
            r.loadApplication();
            return v;
        }
        uint32_t v = 0;
        switch (e.argumentCount) {
        case 0:
            v = r.invoke(e.function, e.receiver);
            break;
        case 1:
            v = r.invoke(e.function, e.receiver, {e.arguments[0]});
            break;
        case 2:
            v = r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1]});
            break;
        case 3:
            v = r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2]});
            break;
        default:
            v = r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2], e.arguments[3]});
            break;
        }
        r.loadApplication();
        return v;
    }
    static uint32_t hostAllocate(void *p, uint32_t n) {
        auto &r = *static_cast<Run *>(p);
        r.commitApplication();
        auto v = r.allocate(n);
        r.loadApplication();
        return v;
    }
    static void release(void *p, uint32_t t) {
        auto &r = *static_cast<Run *>(p);
        r.commitApplication();
        r.invoke(0x4f6428, 0, {t});
        r.loadApplication();
    }
    static uint32_t clock(void *p) {
        auto &r = *static_cast<Run *>(p);
        r.commitApplication();
        if (!r.c.scene.readClock)
            r.fail();
        auto v = r.c.scene.readClock(r.c.scene.context);
        r.loadApplication();
        return v;
    }
    ClawSceneActorHost host() {
        return {this, lookup, hostAllocate, release, hostCall, clock};
    }
    static constexpr uint32_t aliases[13] = {0x537e88, 0x532c10, 0x537204, 0x537200, 0x541328, 0x54132c, 0x541330,
                                             0x541334, 0x541338, 0x537208, 0x53720c, 0x5430c8, 0x5430c4};
    void commitApplication() {
        if (!c.application)
            return;
        if (specialAliases) {
            auto &g = *specialAliases;
            c.application->playerToken = g.playerToken;
            c.application->masterVolume = g.audioVolume;
            c.application->keyboardToken = g.inputMappingToken;
            c.application->mouseToken = g.mouseToken;
            c.application->clock = g.clock;
            c.application->stage = g.stage;
            c.application->animation = g.animation;
        }
        uint32_t a[13];
        std::memcpy(a, c.application, sizeof a);
        for (uint32_t i = 0; i < 13; ++i)
            put(aliases[i], a[i]);
    }
    void loadApplication() {
        if (!c.application)
            return;
        uint32_t a[13];
        for (uint32_t i = 0; i < 13; ++i)
            a[i] = get(aliases[i]);
        std::memcpy(c.application, a, sizeof a);
        if (specialAliases) {
            auto &g = *specialAliases;
            g.playerToken = c.application->playerToken;
            g.audioVolume = c.application->masterVolume;
            g.inputMappingToken = c.application->keyboardToken;
            g.mouseToken = c.application->mouseToken;
            g.clock = c.application->clock;
            g.stage = c.application->stage;
            g.animation = c.application->animation;
        }
    }
    static uint32_t constructor(uint32_t, uint32_t type, uint32_t, ClawSceneActorHost, uint32_t *f, void *p) {
        auto &r = *static_cast<Run *>(p);
        try {
            return r.construct(type);
        } catch (Failure &) {
            *f = r.c.fault;
            return 0;
        }
    }
    uint32_t construct(uint32_t type) {
        if (type == 3) {
            auto token = allocate(0x778);
            if (!token)
                return 0;
            if (!c.singlePlayer)
                fail();
            auto n = *c.singlePlayer;
            n.host = host();
            n.fault = 0;
            if (!claw_single_player_scene_construct(token, &n, sceneDependency, this) || n.fault)
                fail(n.fault ? n.fault : 1);
            return token;
        }
        if (type == 8) {
            auto token = allocate(0x1b8);
            if (!token)
                return 0;
            invoke(0x40b5c0, token);
            invoke(0x429710, token + 392);
            put(token + 392, 0x50c1cc);
            invoke(0x4f6439, token + 400);
            put(token + 408, 0);
            put(token + 416, 0);
            put(token, 0x50c174);
            for (auto off : {344u, 348u, 352u, 356u, 404u, 412u, 420u})
                put(token + off, 0);
            invoke(0x4296f0, token + 360, {0, 0, 640, 480});
            invoke(0x4296f0, token + 376, {0, 0, 640, 480});
            put(token + 428, 1);
            for (auto off : {432u, 424u, 340u})
                put(token + off, 0);
            return token;
        }
        fail(3);
    }
    void local(uint32_t f, uint32_t *cell, std::initializer_list<uint32_t> a = {}) {
        ClawApplicationLevelProgressionCall q{};
        q.function = f;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        q.localMask = 256;
        q.bufferCount = 1;
        q.buffers[0] = cell;
        q.bufferBytes[0] = 4;
        if (a.size())
            q.name = text(*a.begin());
        event(q);
    }
    static uint32_t sceneDependency(ClawSinglePlayerSceneContext *, ClawSinglePlayerSceneCall e, void *p) {
        auto &r = *static_cast<Run *>(p);
        if (owned(e.function) && !e.localMask && e.argumentCount <= 4)
            return hostCall(p, {e.function,
                                e.receiver,
                                {e.arguments[0], e.arguments[1], e.arguments[2], e.arguments[3]},
                                e.argumentCount});
        ClawApplicationLevelProgressionCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, 8, q.arguments);
        q.localMask = e.localMask;
        q.bufferCount = e.bufferCount;
        std::copy_n(e.buffers, 3, q.buffers);
        std::copy_n(e.bufferBytes, 3, q.bufferBytes);
        if (e.function == 0x4a3920)
            q.name = r.text(e.arguments[1]);
        return r.event(q);
    }
    static uint32_t specialDependency(ClawSpecialCommandContext *, const ClawSpecialCommandCall *e, void *p) {
        auto &r = *static_cast<Run *>(p);
        ClawApplicationLevelProgressionCall q{};
        q.function = e->function;
        q.receiver = e->receiver;
        q.argumentCount = e->argumentCount;
        std::copy_n(e->arguments, 8, q.arguments);
        q.name = e->name;
        q.localMask = e->localMask;
        if (e->buffer) {
            q.bufferCount = 1;
            q.buffers[0] = e->buffer;
            q.bufferBytes[0] = e->bufferWords * 4;
        }
        return r.event(q);
    }
    static uint32_t bootyDependency(ClawBootyProgressionContext *, const ClawBootyProgressionCall *e, void *p) {
        auto &r = *static_cast<Run *>(p);
        if (owned(e->function) && !e->localMask && e->argumentCount <= 4)
            return hostCall(p, {e->function,
                                e->receiver,
                                {e->arguments[0], e->arguments[1], e->arguments[2], e->arguments[3]},
                                e->argumentCount});
        auto q = *e;
        return r.event(q);
    }
    static uint32_t resultsDependency(ClawBootyResultsContext *, const ClawBootyResultsCall *e, void *p) {
        auto q = *e;
        return static_cast<Run *>(p)->event(q);
    }
    static uint32_t storyDependency(ClawBootyStoryContext *, const ClawBootyStoryCall *e, void *p) {
        auto &r = *static_cast<Run *>(p);
        ClawApplicationLevelProgressionCall q{};
        q.function = e->function;
        q.receiver = e->receiver;
        q.argumentCount = e->argumentCount;
        std::copy_n(e->arguments, 40, q.arguments);
        q.name = e->name;
        q.localMask = e->localMask;
        q.bufferCount = e->bufferCount;
        std::copy_n(e->buffers, 3, q.buffers);
        std::copy_n(e->bufferBytes, 3, q.bufferBytes);
        return r.event(q);
    }
    static uint32_t lifecycleDependency(ClawSceneLifecycleContext *, const ClawSceneLifecycleCall *e, void *p) {
        auto &r = *static_cast<Run *>(p);
        ClawApplicationLevelProgressionCall q{};
        q.function = e->function;
        q.receiver = e->receiver;
        q.argumentCount = e->argumentCount;
        std::copy_n(e->arguments, 8, q.arguments);
        q.localMask = e->localMask;
        q.bufferCount = e->bufferCount;
        for (uint32_t i = 0; i < 3; ++i) {
            q.buffers[i] = e->buffers[i];
            q.bufferBytes[i] = e->bufferBytes[i];
        }
        return r.event(q);
    }
    static uint32_t arrayDependency(ClawCArrayContext *, const ClawCArrayCall *e, void *p) {
        return hostCall(p, {e->function,
                            e->receiver,
                            {e->arguments[0], e->arguments[1], e->arguments[2], e->arguments[3]},
                            e->argumentCount});
    }
    void timeout(uint32_t p) {
        auto v = get(p), delta = get(0x53720c);
        put(p, delta < v ? v - delta : 0);
    }
};
uint32_t body(Run &, uint32_t, uint32_t, const uint32_t *);
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a) {
    step();
    uint32_t args[40]{};
    std::copy(a.begin(), a.end(), args);
    if (owned(f))
        return body(*this, f, t, args);
    if (f == 0x4efcd0 || f == 0x4efd00) {
        if (!a.size()) {
            auto result = clawMovieStateCleanup(*this, f, t);
            if (c.fault)
                throw Failure{};
            return result;
        }
        c.fault = 3;
        throw Failure{};
    }
    uint32_t out = 0;
    if (f == 0x428c40 && c.composeTransitions) {
        if (!c.application)
            fail();
        loadApplication();
        uint32_t fault = 0;
        out = claw_application_state_transition(t, args[0], args[1], args[2], args[3], c.application, host(),
                                                constructor, this, &fault);
        if (fault)
            fail(fault);
        commitApplication();
        return out;
    }
    if (c.composeSinglePlayer && c.singlePlayer) {
        if (!c.singlePlayer->globals)
            fail();
        auto s = *c.singlePlayer;
        s.host = host();
        s.fault = 0;
        if (claw_single_player_scene_entry(f, t, args, uint32_t(a.size()), &s, sceneDependency, this, &out)) {
            if (s.fault)
                fail(s.fault);
            return out;
        }
        if (s.fault)
            fail(s.fault);
    }
    if (f == 0x42d4c0) {
        ClawSpecialCommandGlobals g{};
        ClawBootyProgressionContext s{};
        s.scene = host();
        s.globals = &g;
        if (!claw_booty_progression_entry(f, t, args, uint32_t(a.size()), &s, bootyDependency, this, &out) || s.fault)
            fail(s.fault ? s.fault : 1);
        return out;
    }
    if (c.composeBooty && c.progression) {
        auto s = *c.progression;
        s.scene = host();
        s.fault = 0;
        if (claw_booty_progression_entry(f, t, args, uint32_t(a.size()), &s, bootyDependency, this, &out)) {
            if (s.fault)
                fail(s.fault);
            return out;
        }
        if (s.fault)
            fail(s.fault);
    }
    if (c.composeBooty && c.results) {
        auto s = *c.results;
        s.scene = host();
        s.fault = 0;
        if (claw_booty_results_entry(f, t, args, uint32_t(a.size()), &s, resultsDependency, this, &out)) {
            if (s.fault)
                fail(s.fault);
            return out;
        }
        if (s.fault)
            fail(s.fault);
    }
    if (c.composeBooty && c.story) {
        auto s = *c.story;
        s.scene = host();
        s.fault = 0;
        if (claw_booty_story_entry(f, t, args, uint32_t(a.size()), &s, storyDependency, this, &out)) {
            if (s.fault)
                fail(s.fault);
            return out;
        }
        if (s.fault)
            fail(s.fault);
    }
    if (f == 0x42abf0 && c.composeTransitions) {
        if (!c.application)
            fail();
        loadApplication();
        ClawSpecialCommandGlobals g{};
        if (c.special && c.special->globals)
            g = *c.special->globals;
        g.playerToken = c.application->playerToken;
        g.audioVolume = c.application->masterVolume;
        g.inputMappingToken = c.application->keyboardToken;
        g.mouseToken = c.application->mouseToken;
        g.clock = c.application->clock;
        g.stage = c.application->stage;
        g.animation = c.application->animation;
        ClawSpecialCommandContext s{host(), &g, 0};
        specialAliases = &g;
        auto supported = claw_special_command_entry(f, t, args, uint32_t(a.size()), &s, specialDependency, this, &out);
        commitApplication();
        specialAliases = nullptr;
        if (c.special && c.special->globals) {
            c.special->globals->playerToken = g.playerToken;
            c.special->globals->clock = g.clock;
            c.special->globals->stage = g.stage;
            c.special->globals->animation = g.animation;
        }
        if (!supported || s.fault)
            fail(s.fault ? s.fault : 1);
        return out;
    }
    if (c.special && (f == 0x42d420 || f == 0x42d440)) {
        auto s = *c.special;
        s.scene = host();
        s.fault = 0;
        if (claw_special_command_entry(f, t, args, uint32_t(a.size()), &s, specialDependency, this, &out)) {
            if (s.fault)
                fail(s.fault);
            return out;
        }
    }
    if (c.composeLifecycle && c.lifecycle) {
        auto s = *c.lifecycle;
        s.scene = host();
        s.fault = 0;
        if (claw_scene_lifecycle_entry(f, t, args, uint32_t(a.size()), &s, lifecycleDependency, this, &out)) {
            if (s.fault)
                fail(s.fault);
            return out;
        }
        if (s.fault)
            fail(s.fault);
    }
    if (c.arrays && (f == 0x4a4a80 || f == 0x4f582f || f == 0x4f5915)) {
        auto s = *c.arrays;
        s.scene = host();
        s.fault = 0;
        if (claw_carray_entry(f, t, args[0], args[1], args[2], &s, arrayDependency, this, &out)) {
            if (s.fault)
                fail(s.fault);
            return out;
        }
    }
    return call(f, t, args, uint32_t(a.size()));
}
uint32_t body(Run &r, uint32_t f, uint32_t p, const uint32_t *a) {
    switch (f) {
    case 0x426e30:
        if (a[1] == 0x8021) {
            if (r.virt(r.get(p + 44), 16) != 2 && r.virt(r.get(p + 44), 16) != 5 && r.virt(r.get(p + 44), 16) != 10)
                return 1;
            if (!r.invoke(0x428c40, p, {8, 1, 0, 0}) && !r.invoke(0x428c40, p, {5, 1, 0, 0}))
                r.invoke(0x429e10, p, {0x8005, 0x3f9});
        } else if (a[1] == 0x8036) {
            if (!r.invoke(0x429ac0, p))
                r.invoke(0x429e10, p, {0x8005, 0x3f8});
        } else if (a[1] == 0x8075) {
            if (!r.invoke(0x429be0, p))
                r.invoke(0x429e10, p, {0x8007, 0x6a7});
        }
        return 1;
    case 0x42bfd0:
        if (si(r.get(p + 228)) < 1)
            return 0;
        return r.get(r.get(p + 224) - 4 + r.get(p + 228) * 4);
    case 0x42c010: {
        if (!a[0] || si(r.get(p + 228)) < 1)
            return 0;
        auto index = r.get(p + 228) - 1, previous = r.get(r.get(p + 224) + index * 4);
        r.invoke(0x4f55e9, p + 220, {index, 1});
        return previous == a[0];
    }
    case 0x4f55e9: {
        auto count = r.get(p + 8) - a[0] - a[1];
        if (count)
            r.invoke(0x4a4a80, 0, {r.get(p + 4) + a[0] * 4, r.get(p + 4) + (a[0] + a[1]) * 4, count * 4});
        r.put(p + 8, r.get(p + 8) - a[1]);
        return 0;
    }
    case 0x429ac0: {
        if (!r.virt(p, 12))
            return 0;
        auto prior = r.invoke(0x42bfd0, p);
        if (!prior)
            return 0;
        auto current = r.get(p + 44);
        if (current == prior)
            return 0;
        uint32_t oldMode = 0;
        if (current) {
            oldMode = r.virt(current, 16);
            auto table = r.get(r.get(p + 44));
            auto nextMode = r.virt(prior, 16);
            r.invoke(r.get(table + 40), r.get(p + 44), {nextMode});
            if (r.get(p + 44))
                r.virt(r.get(p + 44), 0, {1});
            r.put(p + 44, 0);
        }
        r.put(p + 44, prior);
        r.invoke(0x42c010, p, {prior});
        if (!r.virt(r.get(p + 44), 36, {oldMode}) && !r.virt(r.get(p + 44), 28))
            return 0;
        r.put(r.get(p + 8) + 580, 1);
        r.invoke(0x42abf0, p);
        return 1;
    }
    case 0x429be0: {
        if (r.virt(r.get(p + 44), 16) != 3)
            return 0;
        r.invoke(0x4f650f, p + 192);
        auto owner = r.get(p + 44), old = r.get(owner + 20), next = old + 1, remaining = 13u;
        for (;;) {
            r.step();
            if (si(next) > 14)
                next = 1;
            if (next == old) {
                r.post(p, 0x8006);
                return 0;
            }
            auto table = r.get(owner), mode = r.invoke(r.get(table + 16), owner);
            r.invoke(r.get(table + 40), owner, {mode});
            if (r.invoke(0x46aeb0, owner, {next, 1})) {
                table = r.get(owner);
                mode = r.invoke(r.get(table + 16), owner);
                r.invoke(r.get(table + 36), owner, {mode});
                return 1;
            }
            ++next;
            auto before = remaining--;
            if (si(before) <= 0)
                break;
        }
        r.invoke(0x429e10, p, {0x8007, 0x401});
        return 0;
    }
    case 0x429b70: {
        if (r.virt(r.get(p + 44), 16) != 3)
            return r.invoke(0x428c40, p, {3, a[0], 0, 0});
        auto owner = r.get(p + 44), table = r.get(owner), mode = r.invoke(r.get(table + 16), owner);
        r.invoke(r.get(table + 40), r.get(p + 44), {mode});
        if (!r.invoke(0x46aeb0, owner, {a[0], 1}))
            return 0;
        auto current = r.get(p + 44);
        table = r.get(current);
        mode = r.invoke(r.get(table + 16), current);
        r.invoke(r.get(table + 36), r.get(p + 44), {mode});
        return 1;
    }
    case 0x429710:
        r.put(p, 0x50beb4);
        r.put(p + 4, 0);
        return 0;
    case 0x4295b0:
        return 8;
    case 0x429720:
        r.invoke(0x429740, p);
        if (a[0] & 1)
            r.invoke(0x4f6428, 0, {p});
        return p;
    case 0x429740:
        r.put(p, 0x50beb4);
        r.invoke(0x4fd732, p);
        r.put(p, 0x50becc);
        return 0;
    case 0x4295c0:
        r.invoke(0x4295e0, p);
        if (a[0] & 1)
            r.invoke(0x4f6428, 0, {p});
        return p;
    case 0x4295e0:
        r.put(p, 0x50c174);
        r.invoke(0x4359f0, p);
        r.invoke(0x4f6584, p + 400);
        r.put(p + 392, 0x50beb4);
        r.invoke(0x4fd732, p + 392);
        r.put(p + 392, 0x50becc);
        r.put(p, 0x50b4ec);
        r.invoke(0x48f180, p);
        return 0;
    case 0x435840: {
        if (!r.invoke(0x48f0d0, p, {a[0], a[1], a[2]}))
            return 0;
        r.invoke(0x546cd8, 0, {0});
        for (auto off : {344u, 348u, 352u, 356u})
            r.put(p + off, 0);
        r.invoke(0x42a000, r.get(p + 4), {1});
        r.put(p + 32, r.invoke(0x4b7f20, r.get(p + 8), {0x526a60}));
        if (!r.get(p + 32))
            return 0;
        r.put(p + 36, r.invoke(0x4b7f20, r.get(p + 8), {0x523734}));
        if (!r.get(p + 36))
            return 0;
        auto sounds = r.invoke(0x4b68c0, r.get(p + 32), {0x52372c});
        if (!sounds)
            return 0;
        r.invoke(0x4ca440, r.get(r.get(p + 12) + 40), {sounds, 0x534938, 0x523728});
        auto music = r.invoke(0x4b7cd0, r.get(p + 32), {0x526a58});
        if (music) {
            auto resource = r.invoke(0x4b67f0, music, {0x5256a8, 0x584d49});
            if (resource) {
                auto data = r.invoke(0x4b61c0, resource);
                if (data)
                    r.invoke(0x4b53f0, r.get(r.get(p + 4) + 80), {data, r.get(resource + 20), 0x526a50});
            }
        }
        auto game = r.invoke(0x4b7f20, r.get(p + 8), {0x5254ec});
        if (!game)
            return 0;
        music = r.invoke(0x4b7cd0, game, {0x526a58});
        if (music) {
            auto resource = r.invoke(0x4b67f0, music, {0x525948, 0x584d49});
            if (resource) {
                auto data = r.invoke(0x4b61c0, resource);
                if (data)
                    r.invoke(0x4b53f0, r.get(r.get(p + 4) + 80), {data, r.get(resource + 20), 0x525948});
            }
        }
        r.invoke(0x4361c0, p);
        r.put(p + 428, r.get(0x537360) ? 11 : 12);
        auto okay = r.invoke(0x436340, p);
        r.put(p + 340, 0);
        return okay ? r.invoke(0x435e60, p) : 0;
    }
    case 0x42b520:
        r.invoke(0x4f0120, p);
        r.invoke(0x42d4c0, p + 0x8680);
        r.invoke(0x4efcd0, p + 0x534);
        r.invoke(0x4f57f8, p + 0x66c);
        r.invoke(0x4f7369, p + 0x658);
        return 0;
    case 0x4359f0: {
        auto sound = r.get(r.get(r.get(p + 12) + 40) + 44);
        if (sound)
            r.invoke(0x4b4b40, sound);
        r.invoke(0x4ca300, r.get(r.get(p + 12) + 40));
        r.invoke(0x4b5340, r.get(r.get(p + 4) + 80));
        if (r.get(p + 432)) {
            r.invoke(0x4f0120, r.get(p + 432));
            auto movie = r.get(p + 432);
            if (movie) {
                r.invoke(0x42b520, movie);
                r.invoke(0x4f6428, 0, {movie});
            }
        }
        r.invoke(0x48f180, p);
        return 0;
    }
    case 0x435e60: {
        r.invoke(0x48ffa0, p, {0x526a50, 0, 0, 0});
        r.invoke(0x4caa90, r.get(r.get(p + 12) + 4));
        r.invoke(0x4caa20, r.get(r.get(p + 12) + 4), {1});
        if (r.get(p + 424)) {
            if (r.get(p + 44)) {
                r.invoke(0x4bb990, r.get(r.get(p + 44) + 16), {0, 256, 0, 0, 0, 500});
                for (uint32_t i = 0; i < 2; ++i) {
                    auto surface = r.get(r.get(p + 12) + 4);
                    r.invoke(0x4b97c0, r.get(r.get(surface + 20) + 44), {0});
                    r.invoke(0x4b98b0, r.get(r.get(surface + 16) + 44), {0});
                }
            }
            if (r.get(p + 432)) {
                auto object = r.get(r.get(r.get(r.get(r.get(p + 12) + 4) + 16) + 44) + 8);
                r.invoke(r.get(r.get(object) + 124), 0, {object, r.get(r.get(p + 432) + 32)});
            }
        }
        return 1;
    }
    case 0x435a50: {
        r.cursor();
        if (!r.get(p + 424)) {
            uint32_t delay = 500;
            switch (a[0]) {
            case 2:
            case 5:
            case 8:
            case 9:
                r.invoke(0x48f500, p, {700});
                delay = 0;
                break;
            default:
                break;
            }
            r.invoke(0x48f740, p, {0x526a50, 0, delay, delay, 700});
        }
        return 1;
    }
    case 0x435af0:
        if (si(a[0]) >= 3 && si(a[0]) <= 5 && (a[0] != 5 || r.get(p + 424)) && r.get(p + 44)) {
            r.invoke(0x4bb990, r.get(r.get(p + 44) + 16), {0, 256, 0, 0, 0, 500});
            for (uint32_t i = 0; i < 2; ++i) {
                auto surface = r.get(r.get(p + 12) + 4);
                r.invoke(0x4b97c0, r.get(r.get(surface + 20) + 44), {0});
                r.invoke(0x4b98b0, r.get(r.get(surface + 16) + 44), {0});
            }
        }
        return 1;
    case 0x435d10:
        if (r.invoke(0x4ca930, r.get(r.get(p + 12) + 4))) {
            r.cursor();
            return r.invoke(0x435e60, p);
        }
        return 0;
    case 0x435d50:
        if (!r.virt(p, 12) || !r.get(p + 44))
            return 0;
        r.cursor();
        {
            auto result = r.invoke(0x435e60, p);
            return r.invoke(0x48f470, p, {250}) ? result : 0;
        }
    case 0x435da0:
        if (a[0] == 27 || a[0] == 32 || a[0] == 13)
            r.post(r.get(p + 4), 0x8023);
        return 1;
    case 0x435de0: {
        uint32_t rect[4] = {0, 0, 100, 100};
        ClawApplicationLevelProgressionCall q{};
        q.function = 0x546cd4;
        q.argumentCount = 3;
        q.arguments[1] = a[1];
        q.arguments[2] = a[2];
        q.localMask = 1;
        q.bufferCount = 1;
        q.buffers[0] = rect;
        q.bufferBytes[0] = 16;
        if (r.event(q))
            r.invoke(0x4366c0, p);
        else
            r.post(r.get(p + 4), 0x8023);
        return 1;
    }
    case 0x436630: {
        if (!r.get(p + 356))
            return 0xffffff;
        if (r.get(p + 348))
            return r.get(p + 344);
        auto red = r.invoke(0x4a3050, 0), green = r.invoke(0x4a3050, 0), blue = r.invoke(0x4a3050, 0);
        r.put(p + 348, 300);
        auto colour = (red & 255) | ((green & 255) << 8) | ((blue & 255) << 16);
        r.put(p + 344, colour);
        return colour;
    }
    case 0x4366c0: {
        r.put(p + 356, !r.get(p + 356));
        if (!r.get(p + 356)) {
            r.put(p + 352, 0);
            auto playing = r.get(r.get(r.get(p + 4) + 80) + 28),
                 music = r.invoke(0x4b54a0, r.get(r.get(0x5371fc) + 80), {0x525948});
            if (playing == music && music && r.invoke(0x4b5bd0, music))
                r.virt(music, 48);
            music = r.invoke(0x4b54a0, r.get(r.get(p + 4) + 80), {0x526a50});
            if (music && playing != music) {
                r.put(r.get(r.get(p + 4) + 80) + 28, music);
                if (!r.invoke(0x4b5bd0, music))
                    r.virt(music, 44, {0});
            }
        } else {
            r.put(p + 348, 0);
            r.put(p + 352, 3000);
            auto music = r.invoke(0x4b54a0, r.get(r.get(p + 4) + 80), {0x526a50});
            if (music && r.invoke(0x4b5bd0, music))
                r.virt(music, 40);
            music = r.invoke(0x4b54a0, r.get(r.get(p + 4) + 80), {0x525948});
            if (music) {
                r.put(r.get(r.get(0x5371fc) + 80) + 28, music);
                r.invoke(0x4b5570, r.get(r.get(0x5371fc) + 80), {0});
            }
        }
        return 0;
    }
    case 0x435b80: {
        auto object = r.get(r.get(r.get(r.get(r.get(p + 12) + 4) + 16) + 44) + 8);
        if (!object || r.invoke(r.get(r.get(object) + 96), 0, {object})) {
            if (!r.virt(p, 24)) {
                r.invoke(0x429e10, r.get(p + 4), {0x8006, 4000});
                return 0;
            }
        }
        if (r.get(p + 44) && r.get(r.get(r.get(p + 44) + 16) + 52))
            r.invoke(0x4bbb70, r.get(r.get(p + 44) + 16));
        auto sound = r.get(r.get(r.get(p + 12) + 40) + 44);
        if (sound)
            r.invoke(0x4b4b80, sound);
        r.invoke(0x4b3490, r.get(0x537200));
        if (r.get(r.get(0x537200) + 528) & 0xffffff) {
            r.post(r.get(p + 4), 0x8023);
            r.put(r.get(r.get(p + 4) + 8) + 580, 0);
        }
        r.invoke(0x436590, p);
        r.invoke(0x435f30, p);
        auto scene = r.get(p + 12);
        r.virt(r.get(scene + 8), 36, {1});
        r.virt(r.get(scene + 12), 52, {r.get(r.get(scene + 4) + 20), r.get(r.get(scene + 4) + 24)});
        r.virt(r.get(scene + 8), 40, {r.get(r.get(scene + 4) + 20)});
        auto surface = r.get(r.get(p + 12) + 4);
        r.invoke(0x4b98b0, r.get(r.get(surface + 16) + 44), {0});
        r.invoke(0x4b9d80, r.get(r.get(surface + 20) + 44),
                 {0, 0, r.get(r.get(surface + 24) + 44), r.get(surface + 24) + 28, 16});
        if (!r.get(p + 340) && r.get(r.get(p + 4) + 20)) {
            r.invoke(0x4b54f0, r.get(r.get(p + 4) + 80), {0x526a50, 1});
            r.put(p + 340, 1);
        }
        if (r.get(p + 356)) {
            auto music = r.invoke(0x4b54a0, r.get(r.get(p + 4) + 80), {0x525948});
            if (music && !r.invoke(0x4b5bd0, music))
                r.invoke(0x4366c0, p);
        }
        return 1;
    }
    case 0x4361c0: {
        auto resource = r.invoke(0x4b67f0, r.get(p + 32), {0x526a50, 0x545854});
        if (resource) {
            auto data = r.invoke(0x4b61c0, resource);
            if (!data)
                return 0;
            auto length = r.get(resource + 20), copy = r.allocate(length + 1);
            if (!copy)
                return 0;
            if (length == 0xffffffff)
                r.fail(2);
            std::memcpy(r.span(copy), r.span(data), length);
            reinterpret_cast<uint8_t *>(r.span(copy))[length] = 0;
            r.invoke(0x4f66cc, p + 400, {copy});
            r.invoke(0x4b6230, resource);
            r.invoke(0x4f6428, 0, {copy});
        }
        auto region = r.invoke(0x54688c, 0, {50, 0, 590, 480});
        r.invoke(0x4fd6db, p + 392, {region});
        auto wrapper = r.get(r.get(r.get(r.get(p + 12) + 4) + 20) + 44), object = r.get(wrapper + 8);
        uint32_t dc = 0;
        ClawApplicationLevelProgressionCall q{};
        q.function = r.get(r.get(object) + 68);
        q.argumentCount = 2;
        q.arguments[0] = object;
        q.localMask = 2;
        q.bufferCount = 1;
        q.buffers[0] = &dc;
        q.bufferBytes[0] = 4;
        r.event(q);
        if (dc) {
            auto height = r.invoke(0x546d30, 0, {dc, r.get(p + 400), 0xffffffff, p + 376, 0x450});
            r.invoke(0x546d5c, 0, {p + 360, 50, 480, 590, height + 480});
            object = r.get(wrapper + 8);
            r.invoke(r.get(r.get(object) + 104), 0, {object, dc});
        }
        r.real(p + 408, 0);
        auto interval = ftol(div(r.real(0x50c910), r.real(0x50c908)));
        r.put(p + 404, interval);
        r.real(p + 416, div(mul(r.real(0x50c910), r.real(0x50c920)), double(interval)));
        return 1;
    }
    case 0x435f30: {
        if (!r.get(p + 12))
            return 0;
        auto wrapper = r.get(r.get(r.get(r.get(p + 12) + 4) + 20) + 44);
        r.timeout(p + 404);
        if (r.get(p + 356)) {
            r.timeout(p + 348);
            r.timeout(p + 352);
        }
        std::memcpy(r.span(p + 376, 4), r.span(p + 360, 4), 16);
        r.real(p + 408, mul(mul(double(r.get(0x53720c)), r.real(p + 416)), r.real(0x50c918)) + r.real(p + 408));
        auto pixels = ftol(r.real(p + 408));
        r.put(p + 380, r.get(p + 380) - pixels);
        r.put(p + 388, r.get(p + 388) - pixels);
        if (si(r.get(p + 388)) < 0) {
            r.real(p + 408, 0);
            std::memcpy(r.span(p + 376, 4), r.span(p + 360, 4), 16);
            r.put(p + 404, ftol(div(r.real(0x50c910), r.real(0x50c908))));
        }
        auto object = r.get(wrapper + 8);
        uint32_t dc = 0;
        ClawApplicationLevelProgressionCall q{};
        q.function = r.get(r.get(object) + 68);
        q.argumentCount = 2;
        q.arguments[0] = object;
        q.localMask = 2;
        q.bufferCount = 1;
        q.buffers[0] = &dc;
        q.bufferBytes[0] = 4;
        r.event(q);
        if (dc) {
            r.invoke(0x546888, 0, {dc, 1});
            if (r.get(0x53735c))
                r.invoke(0x546884, 0, {dc, p == uint32_t(-392) ? 0 : r.get(p + 396)});
            auto colour = r.invoke(0x436630, p);
            r.invoke(0x546880, 0, {dc, colour});
            r.invoke(0x546d30, 0, {dc, r.get(p + 400), 0xffffffff, p + 376, 0x50});
            if (r.get(p + 356) && r.get(p + 352)) {
                uint32_t temporary = 0;
                r.local(0x4f65f2, &temporary, {0x526a70});
                uint32_t rect[] = {0, 0, 640, 480};
                r.invoke(0x546880, 0, {dc, 0xffffff});
                ClawApplicationLevelProgressionCall draw{};
                draw.function = 0x546d30;
                draw.argumentCount = 5;
                draw.arguments[0] = dc;
                draw.arguments[1] = temporary;
                draw.arguments[2] = 0xffffffff;
                draw.arguments[4] = 0x75;
                draw.localMask = 8;
                draw.bufferCount = 1;
                draw.buffers[0] = rect;
                draw.bufferBytes[0] = 16;
                r.event(draw);
                r.local(0x4f6584, &temporary);
            }
            if (r.get(0x53735c))
                r.invoke(0x546884, 0, {dc, 0});
            object = r.get(wrapper + 8);
            r.invoke(r.get(r.get(object) + 104), 0, {object, dc});
        }
        return 1;
    }
    case 0x436560:
        r.invoke(0x4f6449, a[0], {p + 256});
        return a[0];
    case 0x436340: {
        r.put(p + 424, 0);
        uint32_t path = 0;
        ClawApplicationLevelProgressionCall copy{};
        copy.function = 0x4f6449;
        copy.argumentCount = 1;
        copy.arguments[0] = r.get(p + 4) + 256;
        copy.localMask = 256;
        copy.bufferCount = 1;
        copy.buffers[0] = &path;
        copy.bufferBytes[0] = 4;
        r.event(copy);
        if (r.get(path - 8) && r.invoke(0x48c190, 0, {path})) {
            if (!r.get(p + 432)) {
                auto movie = r.allocate(0x8698);
                if (movie) {
                    r.invoke(0x42b4b0, movie + 0x534);
                    r.invoke(0x42d4a0, movie + 0x8680);
                    for (auto off : {0u, 4u, 16u, 20u, 24u, 28u, 12u, 32u, 0x500u, 0x508u, 0x518u, 0x51cu, 0x528u,
                                     0x520u, 0x524u, 0x52cu, 0x504u, 0x530u, 0x4fcu})
                        r.put(movie + off, 0);
                }
                r.put(p + 432, movie);
                if (!movie) {
                    r.local(0x4f6584, &path);
                    return 0;
                }
                auto app = r.get(p + 4), scene = r.get(app + 48), directdraw = r.get(r.get(scene + 28)),
                     wrapper = r.get(r.get(r.get(scene + 4) + 20) + 44);
                auto palette = r.get(r.get(p + 12) + 32), kind = palette ? r.get(palette + 20) : 0;
                if (!wrapper || !directdraw) {
                    r.local(0x4f6584, &path);
                    return 0;
                }
                ClawApplicationLevelProgressionCall open{};
                open.function = 0x4f0000;
                open.receiver = movie;
                open.argumentCount = 31;
                open.arguments[0] = r.get(r.get(app + 4) + 4);
                open.arguments[1] = directdraw;
                open.arguments[2] = r.get(wrapper + 8);
                std::memcpy(open.arguments + 3, r.span(wrapper + 12, 27), 108);
                open.arguments[30] = kind;
                if (!r.event(open)) {
                    r.local(0x4f6584, &path);
                    return 1;
                }
            }
            if (r.invoke(0x4f02e0, r.get(p + 432),
                         {path, r.get(p + 428), 0, uint32_t(r.get(r.get(p + 4) + 288) != 0), 0, 0}))
                r.put(p + 424, 1);
        }
        r.local(0x4f6584, &path);
        return 1;
    }
    case 0x436590: {
        if (!r.get(p + 424))
            return 1;
        uint32_t result = 0;
        if (r.get(p + 432)) {
            auto surface = r.get(r.get(p + 12) + 4), front = r.get(surface + 20), back = r.get(surface + 24);
            if (!r.invoke(0x4f0610, r.get(p + 432), {r.get(r.get(front + 44) + 8), 0xffffffff})) {
                r.invoke(0x4f06e0, r.get(p + 432));
                result = r.invoke(0x436340, p);
                if (result) {
                    auto object = r.get(r.get(r.get(r.get(r.get(p + 12) + 4) + 16) + 44) + 8);
                    r.invoke(r.get(r.get(object) + 124), 0, {object, r.get(r.get(p + 432) + 32)});
                }
            }
            if (back && front)
                r.invoke(0x4b9d80, r.get(back + 44), {0, 0, r.get(front + 44), front + 28, 16});
        }
        return result;
    }
    default:
        r.fail(3);
    }
}
bool owned(uint32_t f) {
    switch (f) {
    case 0x426e30:
    case 0x42bfd0:
    case 0x42c010:
    case 0x4f55e9:
    case 0x429ac0:
    case 0x429be0:
    case 0x429b70:
    case 0x429710:
    case 0x4295b0:
    case 0x429720:
    case 0x429740:
    case 0x4295c0:
    case 0x4295e0:
    case 0x435840:
    case 0x4359f0:
    case 0x435e60:
    case 0x435a50:
    case 0x435af0:
    case 0x435d10:
    case 0x435d50:
    case 0x435da0:
    case 0x435de0:
    case 0x436630:
    case 0x4366c0:
    case 0x435b80:
    case 0x436590:
    case 0x4361c0:
    case 0x435f30:
    case 0x436340:
    case 0x436560:
    case 0x42b520:
        return true;
    default:
        return false;
    }
}
uint32_t arity(uint32_t f) {
    if (f == 0x426e30 || f == 0x435840 || f == 0x435de0)
        return 3;
    if (f == 0x436560 || f == 0x42c010 || f == 0x429b70 || f == 0x429720 || f == 0x4295c0 || f == 0x435a50 ||
        f == 0x435af0)
        return 1;
    if (f == 0x4f55e9 || f == 0x435da0)
        return 2;
    return 0;
}
} // namespace
extern "C" uint32_t claw_application_level_progression_entry(uint32_t f, uint32_t p, const uint32_t *a, uint32_t n,
                                                             ClawApplicationLevelProgressionContext *c,
                                                             ClawApplicationLevelProgressionDependency d, void *u,
                                                             uint32_t *out) {
    if (!c || !out || (!owned(f) && f != 0x428c40))
        return 0;
    if (f == 0x428c40 && !c->composeTransitions) {
        c->fault = 3;
        return 0;
    }
    if (n != (f == 0x428c40 ? 4 : arity(f)) || (n && !a)) {
        c->fault = 3;
        return 0;
    }
    if (f == 0x426e30 && !(a[1] == 0x8021 || a[1] == 0x8036 || a[1] == 0x8075))
        return 0;
    try {
        Run r{*c, d, u};
        uint32_t args[40]{};
        std::copy_n(a, n, args);
        *out = f == 0x428c40 ? r.invoke(f, p, {args[0], args[1], args[2], args[3]}) : body(r, f, p, args);
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
extern "C" uint32_t claw_application_level_progression_construct(uint32_t app, uint32_t type, uint32_t extra,
                                                                 ClawApplicationLevelProgressionContext *c,
                                                                 ClawApplicationLevelProgressionDependency d, void *u,
                                                                 uint32_t *out) {
    (void)app;
    (void)extra;
    if (!c || !out)
        return 0;
    try {
        Run r{*c, d, u};
        *out = r.construct(type);
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
extern "C" uint32_t claw_application_level_progression_function(uint32_t vt, uint32_t slot) {
    if (vt == 0x50c1cc && slot % 4 == 0 && slot < 16) {
        static const uint32_t a[] = {0x502506, 0x429720, 0x4c9e30, 0x4c96b0};
        return a[slot / 4];
    }
    if (vt == 0x50c174) {
        static const uint32_t a[] = {0x4295c0, 0x435840, 0x4359f0, 0x40af20, 0x4295b0, 0x435b80, 0x435d10,
                                     0x435d50, 0x490370, 0x435a50, 0x435af0, 0x40af40, 0x435da0, 0x435de0,
                                     0x40af50, 0x40af50, 0x4bb030, 0x4bb030, 0x48fcf0, 0x4bd250};
        if (slot % 4 == 0 && slot / 4 < 20)
            return a[slot / 4];
    }
    return 0;
}
