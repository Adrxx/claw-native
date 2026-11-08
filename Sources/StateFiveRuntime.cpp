#include "StateFiveRuntime.h"
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
double mul(double a, double b) {
    volatile double v = a * b;
    return v;
}
uint32_t ftol(double v) {
    if (!std::isfinite(v) || v >= 0x1p63 || v < -0x1p63)
        return 0;
    return uint32_t(int64_t(v));
}
bool owned(uint32_t);
uint32_t arity(uint32_t);
struct Run {
    ClawStateFiveContext &c;
    ClawStateFiveDependency d;
    void *u;
    uint32_t steps = 0;
    [[noreturn]] void fail(uint32_t n = 1) {
        if (!c.fault)
            c.fault = n;
        throw Failure{};
    }
    void step() {
        if (++steps > (c.maximumOperations ? c.maximumOperations : 1000000))
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
    double real(uint32_t t) {
        double v;
        std::memcpy(&v, span(t, 2), 8);
        return v;
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    const char *text(uint32_t t) {
        return reinterpret_cast<const char *>(span(t & ~3)) + (t & 3);
    }
    uint32_t event(ClawStateFiveCall &q) {
        step();
        if (!d)
            fail();
        auto v = d(&c, &q, u);
        if (c.fault)
            throw Failure{};
        return v;
    }
    uint32_t invoke(uint32_t, uint32_t, std::initializer_list<uint32_t> = {});
    uint32_t call(uint32_t f, uint32_t p, const uint32_t *a, uint32_t n) {
        ClawStateFiveCall q{};
        q.function = f;
        q.receiver = p;
        q.argumentCount = n;
        if (n > 40)
            fail(3);
        std::copy_n(a, n, q.arguments);
        if (n && (f == 0x4b7f20 || f == 0x4b7cd0 || f == 0x4b68c0 || f == 0x4b67f0 || f == 0x4c7970 || f == 0x4c79e0 ||
                  f == 0x4c7900 || f == 0x4f6286 || f == 0x4f62a8))
            q.name = text(a[0]);
        return event(q);
    }
    uint32_t virt(uint32_t p, uint32_t s, std::initializer_list<uint32_t> a = {}) {
        auto vt = get(p), f = claw_state_five_function(vt, s);
        if (!f)
            f = get(vt + s);
        return invoke(f, p, a);
    }
    uint32_t local(uint32_t f, uint32_t p, const uint32_t *a, uint32_t n, uint32_t mask, void *b, uint32_t bytes) {
        ClawStateFiveCall q{};
        q.function = f;
        q.receiver = p;
        q.argumentCount = n;
        std::copy_n(a, n, q.arguments);
        q.localMask = mask;
        q.bufferCount = 1;
        q.buffers[0] = b;
        q.bufferBytes[0] = bytes;
        if (n && a[0] && (f == 0x4f6286))
            q.name = text(a[0]);
        return event(q);
    }
    uint32_t object(uint32_t f, void *b, uint32_t size, std::initializer_list<uint32_t> a = {}) {
        ClawStateFiveCall q{};
        q.function = f;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        q.localMask = 256;
        q.bufferCount = 1;
        q.buffers[0] = b;
        q.bufferBytes[0] = size;
        return event(q);
    }
    uint32_t cell(uint32_t f, uint32_t &value, std::initializer_list<uint32_t> a = {}, uint32_t *source = nullptr) {
        ClawStateFiveCall q{};
        q.function = f;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        q.localMask = 256;
        q.bufferCount = 1;
        q.buffers[0] = &value;
        q.bufferBytes[0] = 4;
        if (source) {
            q.localMask |= 1;
            q.bufferCount = 2;
            q.buffers[1] = source;
            q.bufferBytes[1] = 4;
            q.arguments[0] = 0;
        }
        return event(q);
    }
    uint32_t resolve(uint32_t p, uint32_t incoming, uint32_t &output, uint32_t &frame, uint32_t outputToken = 0) {
        uint32_t value = 0;
        cell(0x4f6449, value, {0}, &incoming);
        frame = invoke(0x4a3ce0, 0, {value});
        cell(0x4f6a1d, value);
        static const uint32_t rows[][2] = {{0x527fa0, 0x528d60}, {0x528d50, 0x528d38}, {0x528d24, 0x528d04},
                                           {0x528cf0, 0x528d04}, {0x528cd8, 0x528cb0}, {0x528c9c, 0x528c80},
                                           {0x528c70, 0x528c58}, {0x528c40, 0x528c20}, {0x528c14, 0x528bfc},
                                           {0x527f50, 0x528be8}, {0x528bd8, 0x528bc0}, {0x528bac, 0x528b8c},
                                           {0x527f20, 0x528ae8}, {0x527ee8, 0x528b70}, {0x528b58, 0x528b48}};
        uint32_t matched = 15;
        for (uint32_t i = 0; i < 15; ++i)
            if (cell(0x4f4c93, value, {rows[i][0]}) != 0xffffffff) {
                matched = i;
                if (outputToken)
                    invoke(0x4f66cc, outputToken, {rows[i][1]});
                else
                    cell(0x4f66cc, output, {rows[i][1]});
                break;
            }
        if (matched == 12 && frame != 31 && frame != 36) {
            static const uint32_t options[][2] = {{0x527f18, 16}, {0x527f10, 20}, {0x527f08, 0x118}, {0x527efc, 0x11c}};
            for (auto &row : options)
                if (cell(0x4f4c93, value, {row[0]}) != 0xffffffff) {
                    if (!get(get(p + 4) + row[1]))
                        ++frame;
                    break;
                }
        } else if (matched == 13) {
            static const uint32_t options[][2] = {
                {0x528b68, 0x78}, {0x528b60, 0x124}, {0x527eb8, 0x128}, {0x527eb0, 0x120}};
            for (uint32_t i = 0; i < 4; ++i)
                if (cell(0x4f4c93, value, {options[i][0]}) != 0xffffffff) {
                    auto flag = get(get(p + 4) + options[i][1]);
                    if (i == 0 ? flag != 8 : i == 1 ? flag != 0 : flag == 0)
                        ++frame;
                    break;
                }
        }
        cell(0x4f6584, value);
        cell(0x4f6584, incoming);
        return matched != 15;
    }
    uint32_t lookup(uint32_t p, uint32_t name) {
        uint32_t out = 0, a[] = {name, 0};
        local(0x4f6286, p, a, 2, 2, &out, 4);
        return out;
    }
    void cursor() {
        while (si(invoke(0x546d54, 0, {0})) >= 0)
            step();
    }
    void timer(uint32_t p, uint32_t delta) {
        auto before = get(p);
        put(p, delta < before ? before - delta : 0);
    }
    void idle(uint32_t p) {
        put(p + 0x254, 120000 + (get(p + 0x29c) != 10000 ? 60000 : 0));
    }
    void post(uint32_t p, uint32_t command, uint32_t data = 0) {
        invoke(0x546d50, 0, {get(get(get(p + 4) + 4) + 4), 0x111, command, data});
    }
    uint32_t part(uint32_t p, uint32_t off) {
        return get(get(p + 12) + off);
    }
    uint32_t surface(uint32_t p) {
        return part(p, 4);
    }
    uint32_t wrapper(uint32_t p, uint32_t off) {
        return get(get(surface(p) + off) + 44);
    }
    void clear(uint32_t p) {
        for (uint32_t i = 0; i < 2; ++i) {
            auto s = surface(p);
            invoke(0x4b97c0, get(get(s + 20) + 44), {0});
            invoke(0x4b98b0, get(get(s + 16) + 44), {0});
        }
    }
    uint32_t actor(uint32_t p, uint32_t x, uint32_t y, uint32_t z, uint32_t name) {
        return invoke(0x4c8da0, part(p, 8), {0, x, y, z, name, 0});
    }
    void render(uint32_t p) {
        auto scene = get(p + 12);
        virt(get(scene + 12), 52, {get(get(scene + 4) + 20), get(get(scene + 4) + 24)});
        virt(get(scene + 8), 40, {get(get(scene + 4) + 20)});
    }
    void present(uint32_t p) {
        auto s = surface(p);
        invoke(0x4b98b0, get(get(s + 16) + 44), {0});
        invoke(0x4b9d80, get(get(s + 20) + 44), {0, 0, get(get(s + 24) + 44), get(s + 24) + 28, 16});
    }
    void overlay(uint32_t, uint32_t target) {
        invoke(0x45fbb0, 0, {target, get(0x537b48), get(0x537b4c), get(0x537b50), get(0x537b54)});
    }
    static uint32_t *lookupHost(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->span(t, n);
    }
    static uint32_t alloc(void *p, uint32_t n) {
        return static_cast<Run *>(p)->invoke(0x4f63ec, 0, {n});
    }
    static void release(void *p, uint32_t t) {
        static_cast<Run *>(p)->invoke(0x4f6428, 0, {t});
    }
    static uint32_t hostCall(void *p, ClawSceneActorCall e) {
        auto &r = *static_cast<Run *>(p);
        switch (e.argumentCount) {
        case 0:
            return r.invoke(e.function, e.receiver);
        case 1:
            return r.invoke(e.function, e.receiver, {e.arguments[0]});
        case 2:
            return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1]});
        case 3:
            return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2]});
        case 4:
            return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2], e.arguments[3]});
        default:
            r.fail(3);
        }
    }
    static uint32_t clock(void *p) {
        auto &r = *static_cast<Run *>(p);
        if (!r.c.scene.readClock)
            r.fail();
        return r.c.scene.readClock(r.c.scene.context);
    }
    ClawSceneActorHost host() {
        return {this, lookupHost, alloc, release, hostCall, clock};
    }
    static uint32_t baseDependency(ClawSinglePlayerSceneContext *, ClawSinglePlayerSceneCall e, void *p) {
        auto &r = *static_cast<Run *>(p);
        ClawStateFiveCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, 8, q.arguments);
        q.localMask = e.localMask;
        q.bufferCount = e.bufferCount;
        std::copy_n(e.buffers, 3, q.buffers);
        std::copy_n(e.bufferBytes, 3, q.bufferBytes);
        return r.event(q);
    }
    static uint32_t sharedDependency(ClawBootyResultsContext *, const ClawBootyResultsCall *e, void *p) {
        auto q = *e;
        return static_cast<Run *>(p)->event(q);
    }
    static uint32_t storyDependency(ClawBootyStoryContext *, const ClawBootyStoryCall *e, void *p) {
        ClawStateFiveCall q{};
        q.function = e->function;
        q.receiver = e->receiver;
        q.argumentCount = e->argumentCount;
        std::copy_n(e->arguments, 40, q.arguments);
        q.name = e->name;
        q.localMask = e->localMask;
        q.bufferCount = e->bufferCount;
        std::copy_n(e->buffers, 3, q.buffers);
        std::copy_n(e->bufferBytes, 3, q.bufferBytes);
        return static_cast<Run *>(p)->event(q);
    }
    static uint32_t applicationDependency(ClawApplicationLevelProgressionContext *,
                                          const ClawApplicationLevelProgressionCall *e, void *p) {
        auto q = *e;
        return static_cast<Run *>(p)->event(q);
    }
};
uint32_t body(Run &r, uint32_t f, uint32_t p, const uint32_t *a);
uint32_t Run::invoke(uint32_t f, uint32_t p, std::initializer_list<uint32_t> a) {
    step();
    uint32_t args[40]{};
    std::copy(a.begin(), a.end(), args);
    if (owned(f))
        return body(*this, f, p, args);
    uint32_t out = 0;
    if (c.composeBase && c.base) {
        auto s = *c.base;
        s.host = host();
        s.fault = 0;
        if (claw_single_player_scene_entry(f, p, args, uint32_t(a.size()), &s, baseDependency, this, &out)) {
            if (s.fault)
                fail(s.fault);
            return out;
        }
    }
    if (c.composeShared && c.results) {
        auto s = *c.results;
        s.scene = host();
        s.fault = 0;
        if (claw_booty_results_entry(f, p, args, uint32_t(a.size()), &s, sharedDependency, this, &out)) {
            if (s.fault)
                fail(s.fault);
            return out;
        }
    }
    if (c.composeShared && c.story) {
        auto s = *c.story;
        s.scene = host();
        s.fault = 0;
        if (claw_booty_story_entry(f, p, args, uint32_t(a.size()), &s, storyDependency, this, &out)) {
            if (s.fault)
                fail(s.fault);
            return out;
        }
    }
    if (c.application) {
        auto s = *c.application;
        s.scene = host();
        s.fault = 0;
        if (claw_application_level_progression_entry(f, p, args, uint32_t(a.size()), &s, applicationDependency, this,
                                                     &out)) {
            if (s.fault)
                fail(s.fault);
            return out;
        }
    }
    if (c.composeScene && f == 0x4c8da0) {
        uint32_t fault = 0;
        out =
            claw_scene_actor_create_named(p, {args[0], args[1], args[2], args[3], 0, args[5]}, args[4], host(), &fault);
        if (fault)
            fail(fault);
        return out;
    }
    return call(f, p, args, uint32_t(a.size()));
}
uint32_t body(Run &r, uint32_t f, uint32_t p, const uint32_t *a) {
    switch (f) {
    case 0x45fbb0: {
        auto target = a[0];
        if (!target)
            return 0;
        auto object = r.get(target + 8);
        uint32_t dc = 0, args[] = {object, 0};
        r.local(r.get(r.get(object) + 68), 0, args, 2, 2, &dc, 4);
        if (!dc)
            return 0;
        r.invoke(0x546888, 0, {dc, 1});
        uint32_t rect[] = {a[1], a[2], a[3], a[4]}, name = 0, version = 0;
        auto profile = r.get(r.get(0x5371fc) + 100);
        r.cell(0x4f65f2, name, {profile + 20});
        if (r.get(profile + 4) & 4)
            r.cell(0x4f6920, name, {0x526ff0});
        auto draw = [&](uint32_t text, uint32_t flags) {
            uint32_t call[] = {dc, text, 0xffffffff, 0, flags};
            ++rect[0];
            ++rect[1];
            r.invoke(0x546880, 0, {dc, 0});
            r.local(0x546d30, 0, call, 5, 8, rect, 16);
            --rect[0];
            --rect[1];
            r.invoke(0x546880, 0, {dc, 0xffffff});
            r.local(0x546d30, 0, call, 5, 8, rect, 16);
        };
        draw(name, 0x20);
        r.cell(0x4f6439, version);
        uint32_t format[] = {0, r.get(0x53ec3c) ? 0x5291c4u : 0x5291d0u, r.get(0x53ec38),
                             r.get(0x53ec3c) ? r.get(0x53ec3c) : r.get(0x53ec40), r.get(0x53ec40)};
        r.local(0x4f4f58, 0, format, r.get(0x53ec3c) ? 5 : 4, 1, &version, 4);
        draw(version, 0x22);
        object = r.get(target + 8);
        r.invoke(r.get(r.get(object) + 104), 0, {object, dc});
        r.cell(0x4f6584, version);
        r.cell(0x4f6584, name);
        return 0;
    }
    case 0x45cd60:
        r.invoke(0x4f6449, a[0], {p + 252});
        return a[0];
    case 0x45c880: {
        auto app = r.get(p + 4), flags = p + 0x28c;
        switch (a[0]) {
        case 0x3459: {
            if (r.get(p + 12)) {
                auto sound = r.get(r.part(p, 40) + 44);
                if (sound)
                    r.invoke(0x4b4b40, sound);
                auto enabled = r.get(app + 16) ^ 1;
                r.put(0x532c0c, enabled);
                r.put(app + 16, enabled);
            }
            r.put(flags, r.get(flags) | 13);
            auto enabled = r.get(app + 16);
            r.invoke(0x4dceb0, p + 0x154, {0x345a, enabled});
            r.invoke(0x4dceb0, p + 0x154, {0x345b, enabled});
            if (enabled) {
                r.invoke(0x45f490, p, {0x5254dc, 0});
                r.invoke(0x402570, r.get(app + 92));
                auto sound = r.lookup(r.get(r.get(app + 48) + 40) + 16, 0x528b38);
                if (sound && !r.invoke(0x4b3e70, r.get(sound + 16))) {
                    if (r.get(0x532c0c))
                        r.invoke(0x4b3dc0, r.get(sound + 16), {0, 0, 0, 1});
                    r.invoke(0x4b3fe0, r.get(sound + 16), {40, 2000, 0});
                }
            }
            break;
        }
        case 0x345a:
        case 0x345b: {
            auto off = a[0] == 0x345a ? 0x118u : 0x11cu, bit = a[0] == 0x345a ? 4u : 8u;
            r.put(app + off, r.get(app + off) ^ 1);
            if (a[0] == 0x345b) {
                auto mixer = r.get(app + 92);
                if (!r.get(app + off)) {
                    if (r.get(mixer + 36)) {
                        r.put(mixer + 36, 0);
                        r.invoke(0x402520, mixer);
                    }
                } else if (!r.get(mixer + 36)) {
                    r.put(mixer + 36, 1);
                    r.invoke(0x402570, mixer);
                }
            }
            r.invoke(0x45f490, p, {0x5254dc, 0});
            auto sound = r.lookup(r.get(r.get(app + 48) + 40) + 16, a[0] == 0x345a ? 0x528da8 : 0x528d9c);
            if (!r.get(app + off)) {
                if (sound && r.invoke(0x4b3e70, r.get(sound + 16)))
                    r.invoke(0x4b3e30, r.get(sound + 16));
            } else if (sound && !r.invoke(0x4b3e70, r.get(sound + 16)) && r.get(0x532c0c))
                r.invoke(0x4b3d80, r.get(sound + 16));
            r.put(flags, r.get(flags) | bit);
            break;
        }
        case 0x345c:
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.put(app + 20, r.get(app + 20) ^ 1);
            r.put(flags, r.get(flags) | 2);
            break;
        case 0x345d:
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.invoke(0x45d3f0, p, {0x2714});
            return 1;
        default:
            return 0;
        }
        r.invoke(0x45e370, p);
        return 1;
    }
    case 0x45cb90: {
        auto app = r.get(p + 4);
        if (!app)
            return 0;
        uint32_t bit = 0;
        switch (a[0]) {
        case 0x34bd: {
            r.invoke(0x45f490, p, {0x5254dc, 0});
            uint32_t value = 0;
            r.cell(0x4f6449, value, {app + 252});
            auto exists = r.invoke(0x48c190, 0, {value});
            r.cell(0x4f6584, value);
            if (exists)
                r.post(p, 0x8095);
            bit = 1;
            break;
        }
        case 0x34be:
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.put(app + 0x124, r.get(app + 0x124) ^ 1);
            bit = 2;
            break;
        case 0x34bf:
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.invoke(0x42cdf0, app);
            bit = 4;
            break;
        case 0x34c0:
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.invoke(0x45e5c0, p);
            return 1;
        case 0x34c1:
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.put(app + 0x120, r.get(app + 0x120) ^ 1);
            bit = 8;
            break;
        case 0x34c2:
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.invoke(0x45d3f0, p, {0x2714});
            return 1;
        default:
            return 0;
        }
        r.put(p + 0x290, r.get(p + 0x290) | bit);
        r.invoke(0x45e5c0, p);
        return 1;
    }
    case 0x45fde0:
        r.put(p + 4, a[1]);
        r.put(p, 0x50e924);
        r.put(p + 8, a[2]);
        r.put(p + 12, a[0]);
        return 0;
    case 0x45fe60:
        r.put(p, 0x50e8e4);
        r.invoke(0x4d4160, p);
        r.put(p + 16, 0);
        r.put(p + 8, 0);
        r.put(p + 12, 0);
        r.put(p + 4, 0xffffffff);
        r.put(p, 0x50becc);
        return 0;
    case 0x45fe40:
        r.invoke(0x45fe60, p);
        if (a[0] & 1)
            r.invoke(0x4f6428, 0, {p});
        return p;
    case 0x45fee0:
        r.invoke(0x4b9d80, r.get(p + 44), {0, 0, r.get(a[0] + 44), a[0] + 28, 16});
        return 0;
    case 0x45dc90: {
        auto manager = r.get(p + 16);
        if (!manager)
            return 0;
        auto graphics = r.part(p, 28);
        if (!graphics)
            return 0;
        auto target = r.wrapper(p, 16);
        if (!target)
            return 0;
        auto height = r.get(target + 24), width = r.get(target + 20);
        char name[64]{};
        uint32_t fmt[] = {0, 0x528e54, 0x525698};
        r.local(0x4a3920, 0, fmt, 3, 1, name, 64);
        ClawStateFiveCall query{};
        query.function = 0x4b7dc0;
        query.receiver = r.get(p + 32);
        query.argumentCount = 2;
        query.arguments[1] = 0x504358;
        query.name = name;
        query.localMask = 1;
        query.bufferCount = 1;
        query.buffers[0] = name;
        query.bufferBytes[0] = 64;
        auto resource = r.event(query);
        if (!resource)
            return 0;
        auto data = r.invoke(0x4b61c0, resource);
        if (!data)
            return 0;
        auto image = r.invoke(0x4bc520, graphics, {data, 2, r.get(resource + 20), 0x800, 0xffffffff});
        r.put(p + 60, image);
        if (!image)
            return 0;
        auto box = p + 0x154;
        r.invoke(0x4dd800, box, {1, r.get(p + 0x280), r.get(p + 0x288)});
        r.invoke(0x4dd270, box, {r.get(p + 60)});
        auto item = r.invoke(0x4dd450, box, {r.invoke(0x4dd480, box)});
        if (item)
            r.invoke(0x45ef30, p, {r.get(item + 20)});
        r.invoke(0x45d750, p, {a[0]});
        r.overlay(p, r.get(p + 60));
        auto child = r.invoke(0x4f63ec, 0, {52});
        if (child) {
            r.invoke(0x45fde0, child, {r.get(p + 12), 99, 0});
            r.put(child + 16, 0);
            r.put(child, 0x50e8e4);
            r.put(child + 44, 0);
            r.put(child + 48, 1);
        }
        if (r.virt(child, 44, {r.get(p + 60)}))
            r.virt(r.part(p, 8), 40, {child});
        if (!r.get(p + 44)) {
            auto palette = r.virt(r.part(p, 24), 48, {resource, 0, 0});
            r.put(p + 44, palette);
            if (!palette)
                return 0;
        }
        r.invoke(0x4b6230, resource);
        auto palette = r.get(p + 44);
        r.put(r.part(p, 24) + 100, palette);
        r.virt(palette, 52);
        auto paper = r.get(p + 64);
        if (!paper) {
            auto paperFile = r.invoke(0x4b7f00, r.get(p + 8), {0x528e38, 0x504358});
            if (paperFile) {
                auto bytes = r.invoke(0x4b61c0, paperFile);
                if (bytes) {
                    paper = r.invoke(0x4bc520, graphics, {bytes, 2, r.get(paperFile + 20), 0x800, 0xffffffff});
                    r.put(p + 64, paper);
                    r.invoke(0x4b6230, paperFile);
                    paper = r.get(p + 64);
                }
            }
        }
        if (!paper || r.get(paper + 24) != height || r.get(paper + 20) != width)
            return 0;
        auto roller = r.invoke(0x42a4f0, r.get(p + 4));
        uint32_t descriptor[13]{};
        r.object(0x4ecb40, descriptor, 44);
        descriptor[2] = r.get(p + 60);
        descriptor[6] = 1;
        descriptor[3] = r.get(p + 64);
        descriptor[7] = uint32_t(roller != 0);
        descriptor[4] = 40;
        descriptor[5] = 3;
        descriptor[1] = target;
        descriptor[8] = roller;
        uint32_t request[] = {0, 0};
        auto fade = r.local(0x4ec050, manager, request, 2, 2, descriptor, 44);
        if (!fade) {
            r.cell(0x4f6584, descriptor[9]);
            return 0;
        }
        if (!r.get(0x537238)) {
            r.invoke(0x45f490, p, {0x528e30, 0});
            r.invoke(0x4ec9c0, fade, {700, 0, 0});
        } else {
            r.invoke(0x4b8960, 0, {700});
            r.invoke(0x4b9c50, r.wrapper(p, 16), {r.get(child + 44)});
        }
        if (child)
            r.virt(child, 4, {1});
        r.invoke(0x4ec600, manager, {fade});
        r.invoke(0x4bc4f0, graphics, {r.get(p + 60)});
        r.put(p + 60, 0);
        r.cell(0x4f6584, descriptor[9]);
        return 1;
    }
    case 0x45f100: {
        auto node = r.invoke(0x4dd020, p + 0x154, {a[1]});
        if (!node || !uint32_t(node + 60))
            return 0;
        uint32_t rect[4]{}, arg = 0;
        r.local(0x4ded40, node + 60, &arg, 1, 1, rect, 16);
        static const uint32_t xs[] = {328, 346, 366, 386, 406, 426, 446, 466, 486, 506, 524};
        if (a[1] == 0x3459) {
            if (a[0] && !r.get(r.get(p + 4) + 16))
                return 0;
            auto value = r.get(0x532c10) + (a[0] == 2 ? uint32_t(-8) : a[0] == 1 ? 8u : 0u);
            if (si(value) < 0)
                value = 0;
            else if (si(value) > 80)
                value = 80;
            if (value != r.get(0x532c10)) {
                r.invoke(0x42cdc0, r.get(p + 4), {value});
                r.invoke(0x45f490, p, {0x5254e4, 0});
            }
            auto rank = 0 - ftol(mul(double(si(value)), r.real(0x50e8b0)));
            if (rank >= 11)
                r.fail(2);
            r.put(r.get(p + 0x270) + 76, xs[rank] + rect[0]);
            r.put(r.get(p + 0x270) + 80, rect[1] + 14);
        } else if (a[1] == 0x345c) {
            auto app = r.get(p + 4);
            if (a[0] && !r.get(app + 20))
                return 0;
            auto music = r.get(app + 80);
            if (!music)
                return 0;
            auto old = r.invoke(0x4b5650, music);
            auto scaled = mul(double(si(old)), r.real(0x50e8a8));
            auto rounded = ftol(si(old) % 10 < 5 ? std::floor(scaled) : std::ceil(scaled)) * 10;
            auto value = rounded + (a[0] == 2 ? uint32_t(-10) : a[0] == 1 ? 10u : 0u);
            if (si(value) < 0)
                value = 0;
            else if (si(value) > 100)
                value = 100;
            if (value != rounded) {
                r.invoke(0x4b55e0, music, {value});
                r.invoke(0x4b54f0, music, {0x528b00, 0});
            }
            auto rank = ftol(std::ceil(mul(double(si(value)), r.real(0x50e8a8))));
            if (rank >= 11)
                r.fail(2);
            r.put(r.get(p + 0x274) + 76, xs[rank] - 8 + rect[0]);
            r.put(r.get(p + 0x274) + 80, rect[1] + 14);
        }
        return 0;
    }
    case 0x45f360: {
        auto node = r.invoke(0x4dd020, p + 0x154, {a[1]});
        if (!node || !uint32_t(node + 60))
            return 0;
        uint32_t rect[4]{}, arg = 0;
        r.local(0x4ded40, node + 60, &arg, 1, 1, rect, 16);
        if (a[1] != 0x34c0)
            return 0;
        auto old = r.get(r.get(p + 4) + 104), value = old + (a[0] == 2 ? uint32_t(-1) : uint32_t(a[0] == 1));
        if (si(value) < 1)
            value = 1;
        else if (si(value) > 10)
            value = 10;
        if (value != old) {
            r.invoke(0x429ed0, r.get(p + 4), {value, 1, 0});
            r.invoke(0x45f490, p, {0x5254e4, 0});
        }
        static const uint32_t xs[] = {348, 366, 386, 406, 426, 446, 466, 486, 506, 526};
        auto rank = 0 - ftol(mul(double(si(value)), r.real(0x50e8b8)));
        if (rank >= 10)
            r.fail(2);
        r.put(r.get(p + 0x278) + 76, xs[rank] + rect[0]);
        r.put(r.get(p + 0x278) + 80, rect[1] + 14);
        return 0;
    }
    case 0x45e370:
    case 0x45e5c0: {
        auto offset = f == 0x45e370 ? 0x28cu : 0x290u, prior = r.get(p + offset);
        static const uint32_t audio[][6] = {{1, 0x3459, 0x528098, 0x528080, 0, 0},
                                            {4, 0x345a, 0x528068, 0x528050, 0x528038, 0},
                                            {8, 0x345b, 0x52801c, 0x528000, 0x527fe4, 0},
                                            {2, 0x345c, 0x527fcc, 0x527fb4, 0, 0}};
        static const uint32_t display[][6] = {{1, 0x34bd, 0x528f24, 0x528f08, 0, 0},
                                              {2, 0x34be, 0x528eec, 0x528ed0, 0, 0},
                                              {4, 0x34bf, 0x528eb4, 0x528e98, 0, 0},
                                              {8, 0x34c1, 0x528e7c, 0x528e60, 0, 0}};
        auto rows = f == 0x45e370 ? audio : display;
        for (uint32_t i = 0; i < 4; ++i) {
            auto bits = i == 0 ? prior : r.get(p + offset) & 255;
            if (bits & rows[i][0]) {
                auto node = r.invoke(0x4dd020, p + 0x154, {rows[i][1]});
                if (node && uint32_t(node + 60)) {
                    auto item = node + 60;
                    for (uint32_t j = 0; j < 3 && rows[i][j + 2]; ++j) {
                        uint32_t value = 0;
                        r.cell(0x4f65f2, value, {rows[i][j + 2]});
                        auto image = r.invoke(0x45f940, 0, {value});
                        r.invoke(0x4de4d0, item, {image, j == 0 ? 0u : j == 1 ? 3u : 5u});
                    }
                    r.invoke(0x4dec60, item, {r.invoke(0x4ed050, item)});
                }
            }
        }
        r.put(p + offset, 0);
        return prior;
    }
    case 0x45be10: {
        auto &output = *r.span(a[1]);
        auto &frame = *r.span(a[2]);
        return r.resolve(p, a[0], output, frame, a[1]);
    }
    case 0x45f940: {
        uint32_t incoming = a[0], output = 0, frame = 0, result = 0;
        if (!r.get(0x537b58)) {
            r.cell(0x4f6584, incoming);
            return 0;
        }
        r.cell(0x4f6439, output);
        uint32_t copy = 0;
        r.cell(0x4f6449, copy, {0}, &incoming);
        if (r.resolve(r.get(0x537b58), copy, output, frame) && si(frame) > 0 && r.get(output - 8)) {
            auto metadata = r.lookup(r.get(r.get(r.get(0x5371fc) + 48) + 16) + 16, output);
            if (metadata && si(frame) >= si(r.get(metadata + 100)) && si(frame) <= si(r.get(metadata + 104))) {
                auto image = r.get(r.get(metadata + 20) + frame * 4);
                if (image)
                    result = r.get(image + 44);
            }
        }
        r.cell(0x4f6584, output);
        r.cell(0x4f6584, incoming);
        return result;
    }
    case 0x45ef00: {
        uint32_t output = 0, args[] = {a[0], 0};
        auto found = r.local(0x4f6286, p + 0x2ac, args, 2, 2, &output, 4);
        return found ? output : 0;
    }
    case 0x45e990: {
        auto box = p + 0x154, page = r.invoke(0x4dd0c0, box);
        if (page) {
            auto count = r.invoke(0x4df480, page);
            for (uint32_t i = 0; si(i) < si(count); ++i) {
                auto node = r.invoke(0x4df260, page, {i});
                if (node) {
                    uint32_t value = 0, arg = 0;
                    r.local(0x4df460, node, &arg, 1, 1, &value, 4);
                    auto key = r.invoke(0x45ef00, p, {value});
                    r.cell(0x4f6584, value);
                    if (key == a[0]) {
                        auto item = node + 60;
                        if (item && !(r.invoke(0x4ed050, item) & 32)) {
                            r.invoke(0x4dd520, box, {item});
                            r.invoke(0x4ddbc0, box);
                        }
                        break;
                    }
                }
            }
        }
        return 0;
    }
    case 0x45fa80: {
        uint32_t first = 0, count = 0, x0 = 0, x1 = 0, y = 0, dy = 0;
        if (a[0] == 0x2713) {
            first = 0x3a99;
            count = 10;
            x0 = 53;
            x1 = 351;
            y = 204;
            dy = 40;
        } else if (a[0] >= 0x2af9 && a[0] <= 0x2afa) {
            first = 0x2b5d + (a[0] != 0x2af9 ? 100 : 0);
            count = 14;
            x0 = 37;
            x1 = 308;
            y = 213;
            dy = 28;
        } else
            return 0;
        auto page = r.invoke(0x4dd020, p, {a[0]});
        if (page) {
            auto children = r.invoke(0x4df480, page);
            for (uint32_t i = 0; si(i) < si(children); ++i) {
                auto node = r.invoke(0x4df260, page, {i});
                if (node && node + 60) {
                    auto rank = r.get(node + 80) - first, x = x0;
                    if (si(rank) >= si(count / 2)) {
                        if (si(rank) >= si(count))
                            return 0;
                        rank -= count / 2;
                        x = x1;
                    }
                    r.invoke(0x4ded00, node + 60, {x, rank * dy + y});
                }
            }
        }
        return 0;
    }
    case 0x45ace0: {
        if (!a[0] || !r.virt(a[0], 12))
            return 0;
        r.put(0x537b58, p);
        for (auto off : {600u, 0x268u, 0x25cu, 0x260u, 0x26cu, 0x264u, 0x270u, 0x274u, 0x278u, 0x294u, 0x298u})
            r.put(p + off, 0);
        r.put(p + 0x29c, 10000);
        r.put(p + 0x2a8, r.get(0x528a60));
        for (auto off : {0x28cu, 0x290u, 0x2a0u, 0x2a4u})
            r.put(p + off, 0);
        if (!r.invoke(0x48f0d0, p, {a[0], a[1], a[2]}))
            return 0;
        r.invoke(0x42a000, r.get(p + 4), {0});
        r.put(p + 32, r.invoke(0x4b7f20, r.get(p + 8), {0x528b08}));
        if (!r.get(p + 32))
            return 0;
        auto res = r.invoke(0x4b68c0, r.get(p + 32), {0x52372c});
        if (!res)
            return 0;
        r.invoke(0x4ca440, r.part(p, 40), {res, 0x534938, 0x523728});
        res = r.invoke(0x4b7cd0, r.get(p + 32), {0x523ce0});
        if (!res)
            return 0;
        r.virt(r.part(p, 16), 72, {res, 0x525698, 0x523728});
        r.invoke(0x4ca930, r.surface(p));
        res = r.invoke(0x4b7cd0, r.get(p + 32), {0x523cd8});
        if (!res)
            return 0;
        r.invoke(0x4ce0d0, r.part(p, 44), {res, 0x525698, 0x523728});
        res = r.invoke(0x4b67f0, r.get(p + 32), {0x523734, 0x494643});
        if (!res)
            return 0;
        auto data = r.invoke(0x4b61c0, res);
        if (!data)
            return 0;
        auto okay = r.invoke(0x4dcdf0, p + 0x154, {r.part(p, 28), data, r.get(res + 20), 0x45f940, 0, 0, 0});
        r.invoke(0x4b6230, res);
        if (!okay)
            return 0;
        auto music = r.invoke(0x4b7cd0, r.get(p + 32), {0x526a58});
        if (music) {
            res = r.invoke(0x4b67f0, music, {0x528b00, 0x584d49});
            if (res) {
                data = r.invoke(0x4b61c0, res);
                if (data)
                    r.invoke(0x4b53f0, r.get(r.get(p + 4) + 80), {data, r.get(res + 20), 0x528b00});
            }
        }
        r.invoke(0x45ea80, p);
        r.invoke(0x45d500, p, {10000});
        r.invoke(0x45d750, p, {10000});
        r.invoke(0x4dd0d0, p + 0x154, {0});
        r.put(p + 0x174, 1);
        for (auto f2 : {0x45cd90u, 0x45ce60u, 0x45ce80u, 0x45cee0u})
            r.invoke(f2, p);
        if (!r.invoke(0x45b240, p) || !r.part(p, 8))
            return 0;
        auto container = r.part(p, 8);
        for (auto pair : {std::pair<uint32_t, uint32_t>{0x270, 42}, {0x274, 41}, {0x278, 45}}) {
            auto actor = r.invoke(0x4c8da0, container, {0, 0xffffffce, 0xffffffce, 9999, 0x5225e8, 0});
            r.put(p + pair.first, actor);
            if (!actor)
                return 0;
            r.invoke(0x4c7900, actor, {0x528ae8, pair.second});
        }
        r.invoke(0x45db40, p, {10000});
        r.put(p + 0x254, 120000);
        r.invoke(0x4b8910, r.get(r.get(p + 4) + 4), {256, 64});
        r.invoke(0x4b8910, r.get(r.get(p + 4) + 4), {513, 64});
        r.invoke(0x45b880, p);
        return 1;
    }
    case 0x45b3f0: {
        r.invoke(0x42abf0, r.get(p + 4));
        r.cursor();
        switch (a[0]) {
        case 2:
        case 5:
        case 9:
            r.invoke(0x48f500, p, {700});
            r.invoke(0x45dc90, p, {r.get(p + 0x29c)});
            break;
        case 8:
            if (r.get(p + 44)) {
                r.invoke(0x4bb870, r.get(r.get(p + 44) + 16));
                r.invoke(0x45e1b0, p);
            }
            break;
        case 13:
            r.invoke(0x45cd90, p);
            r.invoke(0x45ce80, p);
            break;
        default:
            r.invoke(0x45dc90, p, {r.get(p + 0x29c)});
            break;
        }
        if (r.get(0x525508)) {
            r.put(0x525508, 0);
            r.invoke(0x45f490, p, {0x528b40, 0});
        }
        r.invoke(0x4b8910, r.get(r.get(p + 4) + 4), {256, 64});
        auto sound = r.lookup(r.get(r.get(r.get(p + 4) + 48) + 40) + 16, 0x528b38);
        if (sound && !r.invoke(0x4b3e70, r.get(sound + 16))) {
            if (r.get(0x532c0c))
                r.invoke(0x4b3dc0, r.get(sound + 16), {0, 0, 0, 1});
            r.invoke(0x4b3fe0, r.get(sound + 16), {40, 2000, 0});
        }
        return 1;
    }
    case 0x45b540: {
        if ((a[0] == 3 || a[0] == 4 || a[0] == 14 || a[0] == 15) && r.get(p + 44)) {
            r.invoke(0x4bb990, r.get(r.get(p + 44) + 16), {0, 256, 0, 0, 0, 500});
            r.clear(p);
        }
        if (si(a[0]) > 2 && si(a[0]) < 5) {
            auto sound = r.lookup(r.get(r.get(r.get(p + 4) + 48) + 40) + 16, 0x528b38);
            if (sound && r.invoke(0x4b3e70, r.get(sound + 16)))
                r.invoke(0x4b3fe0, r.get(sound + 16), {0, 1000, 0});
        }
        r.invoke(0x42abf0, r.get(p + 4));
        return 1;
    }
    case 0x45ce60:
        r.invoke(0x4dceb0, p + 0x154, {0x2ee2, 1});
        return 0;
    case 0x45cd90: {
        auto box = p + 0x154;
        auto available = r.invoke(0x42bab0, r.get(p + 4));
        r.invoke(0x4dceb0, box, {0x3330, available});
        for (uint32_t level = 1, slot = 0x1b58c; slot < 0x1b60f; ++level, slot += 10) {
            available = r.invoke(0x42ba10, r.get(p + 4), {level});
            r.invoke(0x4dceb0, box, {level + 0x2b5c, available});
            available = r.invoke(0x42ba70, r.get(p + 4), {level, 0});
            r.invoke(0x4dceb0, box, {level + 0x2bc0, available});
            available = r.invoke(0x42ba70, r.get(p + 4), {level, 0});
            r.invoke(0x4dceb0, box, {slot - 1, available});
            available = r.invoke(0x42ba70, r.get(p + 4), {level, 1});
            r.invoke(0x4dceb0, box, {slot, available});
            available = r.invoke(0x42ba70, r.get(p + 4), {level, 2});
            r.invoke(0x4dceb0, box, {slot + 1, available});
        }
        available = r.invoke(0x42bad0, r.get(p + 4));
        r.invoke(0x4dceb0, box, {0x2afd, available});
        return 0;
    }
    case 0x45ce80: {
        auto box = p + 0x154;
        r.invoke(0x4dceb0, box, {0x2713, r.invoke(0x42c0a0, r.get(p + 4))});
        for (uint32_t id = 0x3a9b, token = 0x50e888; token < 0x50e8a8; ++id, token += 4) {
            auto enabled = r.invoke(0x42c280, r.get(p + 4), {r.get(token)});
            r.invoke(0x4dceb0, box, {id, enabled});
        }
        return 0;
    }
    case 0x45cee0: {
        auto sound = r.lookup(r.part(p, 40) + 16, 0x5254dc);
        auto app = r.get(p + 4), audio = r.get(app + 16), music = r.get(r.get(app + 80) + 40), box = p + 0x154;
        uint32_t enabled = sound != 0;
        r.invoke(0x4dceb0, box, {0x32cc, uint32_t(enabled || music)});
        r.invoke(0x4dceb0, box, {0x3459, enabled});
        r.invoke(0x4dceb0, box, {0x345a, uint32_t(enabled && audio)});
        r.invoke(0x4dceb0, box, {0x345b, uint32_t(enabled && audio)});
        r.invoke(0x4dceb0, box, {0x345c, music});
        return 0;
    }
    case 0x45b240: {
        if (!r.get(p + 12))
            return 0;
        uint32_t point[2]{}, arg = 0;
        r.local(0x546cd0, 0, &arg, 1, 1, point, 8);
        auto actor = r.actor(p, point[0], point[1], 0x4e1e, 0x522658);
        r.put(p + 600, actor);
        r.invoke(0x4c7970, actor, {0x526dac});
        r.invoke(0x4c79e0, r.get(p + 600), {0x526dac, 0});
        auto image = r.get(r.get(p + 600) + 0x174);
        if (image) {
            r.put(p + 0x2a0, uint32_t(si(r.get(image + 16)) / 2));
            r.put(p + 0x2a4, uint32_t(si(r.get(image + 20)) / 2));
        }
        r.put(r.get(p + 600) + 76, r.get(p + 0x2a0) + point[0]);
        r.put(r.get(p + 600) + 80, r.get(p + 0x2a4) + point[1]);
        actor = r.actor(p, uint32_t(-30), 100, 9999, 0x522460);
        r.put(p + 0x264, actor);
        r.invoke(0x4c7970, actor, {0x528b2c});
        r.invoke(0x4c79e0, r.get(p + 0x264), {0x528b20, 0});
        r.invoke(0x45e8f0, p);
        actor = r.actor(p, r.get(p + 0x27c) - 30, r.get(p + 0x280) + 17, 0x270e, 0x5224d8);
        r.put(p + 0x25c, actor);
        r.invoke(0x4c7970, actor, {0x528b14});
        r.invoke(0x4c79e0, r.get(p + 0x25c), {0x526d9c, 0});
        actor = r.actor(p, r.get(p + 0x284) + 30, r.get(p + 0x280) + 17, 0x270e, 0x5224d8);
        r.put(p + 0x260, actor);
        r.invoke(0x4c7970, actor, {0x528b14});
        r.invoke(0x4c79e0, r.get(p + 0x260), {0x526d9c, 0});
        return 1;
    }
    case 0x45e8f0: {
        if (r.get(p + 0x26c)) {
            for (uint32_t i = 0; i < 60; i += 4) {
                auto actor = r.get(r.get(p + 0x26c) + i);
                if (actor)
                    r.put(actor + 8, r.get(actor + 8) | 0x10000);
            }
            r.invoke(0x4f6428, 0, {r.get(p + 0x26c)});
        }
        auto list = r.invoke(0x4f63ec, 0, {60});
        r.put(p + 0x26c, list);
        if (list && r.part(p, 8)) {
            auto container = r.part(p, 8);
            for (uint32_t i = 0; i < 15; ++i) {
                auto actor = r.invoke(0x4c8da0, container,
                                      {0, r.get(0x528a70 + i * 8), r.get(0x528a74 + i * 8), 0x270e, 0x52246c, 0});
                r.put(r.get(p + 0x26c) + i * 4, actor);
            }
        }
        return 0;
    }
    case 0x45d500: {
        r.invoke(0x546d5c, 0, {p + 0x27c, 640, 220, 0, 442});
        bool align = true;
        uint32_t top = 220, bottom = 442, id = a[0];
        if (id > 11000 && id < 0x2afb) {
            r.put(p + 0x280, 220);
            r.put(p + 0x288, 442);
            align = false;
            r.invoke(0x45d720, p, {id});
        } else {
            if (id == 10000) {
                top = 215;
                bottom = 474;
            } else if (id == 0x2713) {
                top = 200;
                bottom = 474;
            } else if (id == 0x2716) {
                top = 294;
                bottom = 368;
            } else if (id >= 0x2bc1 && id < 0x2bcf) {
                top = 220;
                bottom = 368;
            } else if (id == 0x2afc) {
                top = 319;
                bottom = 356;
            } else if (id == 0x2712 || id == 0x2714 || id == 0x32c9 || id == 0x32cc || id == 0x32cd) {
                top = 220;
                bottom = 405;
            } else if (id == 0x2ee2) {
                top = 294;
                bottom = 383;
            } else if (id == 0x32ca) {
                top = 294;
                bottom = 331;
            }
            r.put(p + 0x280, top);
            r.put(p + 0x288, bottom);
        }
        auto box = p + 0x154;
        for (uint32_t i = 0; si(i) < si(r.invoke(0x4df630, box)); ++i) {
            r.step();
            auto item = r.invoke(0x4dd450, box, {i});
            if (item) {
                uint32_t rect[4]{}, arg = 0;
                r.local(0x4ded40, item, &arg, 1, 1, rect, 16);
                if (si(rect[0]) < si(r.get(p + 0x27c)))
                    r.put(p + 0x27c, rect[0]);
                if (si(r.get(p + 0x284)) < si(rect[2]))
                    r.put(p + 0x284, rect[2]);
            }
        }
        if (align)
            r.invoke(0x4dd800, box, {1, r.get(p + 0x280), r.get(p + 0x288)});
        return 0;
    }
    case 0x45d720:
        r.invoke(0x4dd800, p + 0x154, {1, r.get(p + 0x280), r.get(p + 0x288)});
        r.invoke(0x45fa80, p + 0x154, {a[0]});
        return 0;
    case 0x45d410: {
        r.invoke(0x45d500, p, {a[0]});
        auto box = p + 0x154;
        r.invoke(0x4dd270, box, {r.wrapper(p, 20)});
        auto item = r.invoke(0x4dd450, box, {r.invoke(0x4dd480, box)});
        if (item)
            r.invoke(0x45ef30, p, {r.get(item + 20)});
        r.invoke(0x45d750, p, {a[0]});
        if (a[0] == 0x32cc) {
            r.invoke(0x45f100, p, {0, 0x3459});
            r.invoke(0x45f100, p, {0, 0x345c});
        } else if (a[0] == 0x32cd)
            r.invoke(0x45f360, p, {0, 0x34c0});
        r.overlay(p, r.wrapper(p, 20));
        r.put(p + 0x29c, a[0]);
        r.idle(p);
        return 0;
    }
    case 0x45d750: {
        auto old = r.get(p + 0x268);
        if (old) {
            r.put(old + 8, r.get(old + 8) | 0x10000);
            r.put(p + 0x268, 0);
        }
        uint32_t name = 0, index = 0, y = 180, id = a[0];
        switch (id) {
        case 10000:
            name = 0x528d60;
            index = 14;
            break;
        case 0x2711:
            name = 0x528d38;
            index = 14;
            break;
        case 0x2712:
            name = 0x528c58;
            index = 10;
            break;
        case 0x2713:
            name = 0x528bfc;
            index = 33;
            break;
        case 0x2714:
            name = 0x528be8;
            index = 14;
            break;
        case 0x2716:
            name = 0x528b48;
            index = 5;
            y = 220;
            break;
        case 0x2af9:
            name = 0x528dcc;
            index = 1;
            break;
        case 0x2afa:
            name = 0x528db0;
            index = 1;
            break;
        case 0x2afc:
            name = 0x528c80;
            index = 3;
            y = 230;
            break;
        case 0x32c9:
            name = 0x528bc0;
            index = 12;
            break;
        case 0x2ee2:
            name = 0x528c20;
            index = 5;
            y = 220;
            break;
        case 0x32ca:
            name = 0x528b8c;
            index = 3;
            y = 220;
            break;
        case 0x32cc:
            name = 0x528ae8;
            index = 19;
            break;
        case 0x32cd:
            name = 0x528b70;
            index = 21;
            break;
        default:
            if (id >= 0x2bc1 && id < 0x2bcf) {
                name = 0x528cb0;
                index = id - 0x2bb6;
            }
            break;
        }
        if (name) {
            auto actor = r.actor(p, 320, y, 0x270e, 0x5225e8);
            r.put(p + 0x268, actor);
            r.invoke(0x4c7900, actor, {name, index});
        }
        return 0;
    }
    case 0x45e040: {
        if (r.get(p + 0x294) && r.get(p + 4) && r.get(p + 0x298) > 15000 && r.get(p + 0x298) < 0x3aa4) {
            auto id = r.get(p + 0x298);
            if (id == 0x3a99) {
                r.invoke(0x45e0e0, p);
                r.invoke(0x42b5d0, r.get(p + 4));
            } else {
                if (!r.invoke(0x42c0a0, r.get(p + 4)))
                    return 0;
                r.invoke(0x45e0e0, p);
                r.invoke(0x42b140, r.get(p + 4),
                         {id == 0x3a9a
                              ? 0u
                              : (id >= 0x3a9b && id < 0x3aa3 ? r.get(0x50e888 + (id - 0x3a9b) * 4) : 0xffffffffu)});
            }
            r.put(p + 0x294, 0);
            r.put(p + 0x298, 0);
            r.invoke(0x45e1b0, p);
        }
        return 0;
    }
    case 0x45ea80: {
        static const uint32_t rows[][2] = {
            {0x529188, 0x53}, {0x52917c, 0x4d}, {0x52916c, 0x52}, {0x528100, 0x4f}, {0x529164, 0x43}, {0x5280f8, 0x48},
            {0x52915c, 0x51}, {0x529150, 0x4e}, {0x529144, 0x4c}, {0x529130, 0x43}, {0x529124, 0x53}, {0x529114, 0x55},
            {0x5280c8, 0x42}, {0x529108, 0x52}, {0x5290fc, 0x41}, {0x5290f0, 0x46}, {0x5290e4, 0x57}, {0x5290d8, 0x4f},
            {0x5290cc, 0x4c}, {0x5290c0, 0x44}, {0x5290b4, 0x53}, {0x5290a8, 0x50}, {0x52909c, 0x43}, {0x52908c, 0x56},
            {0x52907c, 0x55}, {0x52906c, 0x49}, {0x52905c, 0x54}, {0x526fc4, 0x53}, {0x52904c, 0x31}, {0x52903c, 0x32},
            {0x529034, 0x52}, {0x529028, 0x50}, {0x529014, 0x45}, {0x529004, 0x55}, {0x528ff4, 0x49}, {0x528fec, 0x45},
            {0x528fd8, 0x4f}, {0x528fcc, 0x54}, {0x528fc0, 0x48}, {0x528fb8, 0x52}, {0x528fa8, 0x47}, {0x528f98, 0x57},
            {0x528f88, 0x43}, {0x528f78, 0x45}, {0x528f6c, 0x44}, {0x5280e0, 0x43}, {0x5280d8, 0x49}, {0x5280d0, 0x41},
            {0x528f68, 0x4e}, {0x528f60, 0x49}, {0x528f58, 0x43}, {0x528f50, 0x52}, {0x525704, 0x53}, {0x5256fc, 0x56},
            {0x5256f4, 0x41}, {0x52570c, 0x4d}, {0x528f48, 0x43}, {0x528f40, 0x44}, {0x5280c0, 0x46}, {0x5280b8, 0x47},
            {0x5280b0, 0x4d}, {0x52700c, 0x59}, {0x527024, 0x4e}};
        for (auto &row : rows) {
            auto value = r.invoke(0x4f62a8, p + 0x2ac, {row[0]});
            r.put(value, row[1]);
        }
        return 0;
    }
    case 0x45b880:
        r.invoke(0x48ffa0, p, {0x525698, 0, 0, 0});
        r.invoke(0x4caa90, r.surface(p));
        r.invoke(0x4caa20, r.surface(p), {1});
        return 1;
    case 0x45b130: {
        for (auto off : {600u, 0x264u, 0x25cu, 0x260u}) {
            auto actor = r.get(p + off);
            if (actor) {
                r.put(actor + 8, r.get(actor + 8) | 0x10000);
                if (off == 0x260)
                    r.put(actor + 8, r.get(actor + 8) | 0x10000);
                r.invoke(0x4c92f0, r.part(p, 8), {r.get(p + off)});
                r.put(p + off, 0);
            }
        }
        if (r.get(p + 0x26c)) {
            for (uint32_t i = 0; i < 60; i += 4) {
                auto actor = r.get(r.get(p + 0x26c) + i);
                if (actor)
                    r.put(actor + 8, r.get(actor + 8) | 0x10000);
                r.invoke(0x4c92f0, r.part(p, 8), {r.get(r.get(p + 0x26c) + i)});
            }
            r.invoke(0x4f6428, 0, {r.get(p + 0x26c)});
            r.put(p + 0x26c, 0);
        }
        return 0;
    }
    case 0x45b050:
        r.invoke(0x45b130, p);
        for (auto off : {0x268u, 0x270u, 0x274u, 0x278u}) {
            auto actor = r.get(p + off);
            if (actor) {
                r.put(actor + 8, r.get(actor + 8) | 0x10000);
                r.put(p + off, 0);
            }
        }
        if (r.get(p + 12)) {
            auto sound = r.get(r.part(p, 40) + 44);
            if (sound)
                r.invoke(0x4b4b40, sound);
            r.invoke(0x4ca300, r.part(p, 40));
            r.invoke(0x4caa90, r.surface(p));
            r.virt(r.part(p, 16), 88);
            r.invoke(0x4cdf40, r.part(p, 44));
            r.invoke(0x4c89e0, r.part(p, 8));
        }
        r.invoke(0x4dce90, p + 0x154);
        r.put(0x537b58, 0);
        r.invoke(0x48f180, p);
        return 0;
    case 0x429510:
        r.invoke(0x429530, p);
        if (a[0] & 1)
            r.invoke(0x4f6428, 0, {p});
        return p;
    case 0x429530:
        r.put(p, 0x50c1e4);
        r.invoke(0x45b050, p);
        r.invoke(0x4f5d00, p + 0x2ac);
        r.invoke(0x4dccb0, p + 0x154);
        r.put(p, 0x50b4ec);
        r.invoke(0x48f180, p);
        return 0;
    case 0x45b8c0:
        if (!r.virt(p, 12))
            return 0;
        r.cursor();
        r.idle(p);
        if (!r.invoke(0x4ca930, r.surface(p)))
            return 0;
        {
            auto okay = r.invoke(0x45b880, p);
            if (okay) {
                auto images = r.invoke(0x4b7cd0, r.get(p + 32), {0x523ce0});
                if (!images || r.virt(r.part(p, 16), 76, {images, 0x525698, 0x523728}) == 0xffffffff)
                    return 0;
            }
            return okay;
        }
    case 0x45b960:
        if (!r.virt(p, 12) || !r.get(p + 44))
            return 0;
        {
            auto okay = r.invoke(0x45b880, p);
            return r.invoke(0x48f470, p, {250}) ? okay : 0;
        }
    case 0x45b9a0:
        if (!r.virt(p, 12) || !r.invoke(0x490370, p))
            return 0;
        {
            auto s = r.surface(p), back = r.get(s + 24), front = r.get(s + 20);
            if (back && front)
                r.invoke(0x4b9d80, r.get(front + 44), {0, 0, r.get(back + 44), back + 28, 16});
        }
        r.render(p);
        r.present(p);
        return 1;
    case 0x45b650: {
        auto delta = r.get(0x54132c);
        if (delta < r.get(p + 0x254))
            r.put(p + 0x254, r.get(p + 0x254) - delta);
        else {
            if (!r.get(0x528a68) || !r.invoke(0x42c0a0, r.get(p + 4))) {
                r.post(p, 0x8027);
                r.put(r.get(r.get(p + 4) + 8) + 580, 0);
            } else {
                r.put(p + 0x294, 1);
                r.put(p + 0x298, 0x3a9a);
            }
            r.put(0x528a68, !r.get(0x528a68));
        }
        if (r.get(p + 0x294)) {
            r.invoke(0x45e040, p);
            return 1;
        }
        auto object = r.get(r.wrapper(p, 16) + 8);
        if (!object || r.invoke(r.get(r.get(object) + 96), 0, {object})) {
            if (!r.virt(p, 24)) {
                r.invoke(0x429e10, r.get(p + 4), {0x8006, 2000});
                return 0;
            }
        }
        if (r.get(p + 44) && r.get(r.get(p + 44) + 16) && r.get(r.get(r.get(p + 44) + 16) + 52))
            r.invoke(0x4bbb70, r.get(r.get(p + 44) + 16));
        auto sound = r.get(r.part(p, 40) + 44);
        if (sound)
            r.invoke(0x4b4b80, sound);
        r.invoke(0x45bbc0, p);
        r.invoke(0x4dd270, p + 0x154, {r.wrapper(p, 20)});
        r.overlay(p, r.wrapper(p, 20));
        r.invoke(0x45db40, p, {r.get(p + 0x29c)});
        uint32_t point[2]{};
        uint32_t pointArg = 0;
        r.local(0x546cd0, 0, &pointArg, 1, 1, point, 8);
        if (r.get(p + 600)) {
            r.put(r.get(p + 600) + 76, r.get(p + 0x2a0) + point[0]);
            r.put(r.get(p + 600) + 80, r.get(p + 0x2a4) + point[1]);
        }
        r.virt(r.part(p, 8), 36, {1});
        r.render(p);
        r.present(p);
        return 1;
    }
    case 0x45ba50: {
        auto box = p + 0x154, old = r.invoke(0x4dd480, box);
        uint32_t changed = 1;
        switch (a[0]) {
        case 13:
        case 32:
            r.invoke(0x4ddbc0, box);
            changed = 0;
            break;
        case 27: {
            changed = 0;
            auto page = r.invoke(0x4dd0c0, box);
            if (page) {
                r.invoke(0x45f490, p, {0x5254dc, 0});
                auto parent = r.invoke(0x4df630, page);
                if (!parent) {
                    r.invoke(0x4dd490, box, {6});
                    r.invoke(0x4ddbc0, box);
                } else
                    r.invoke(0x45d3f0, p, {r.get(parent + 80)});
            }
            break;
        }
        case 37:
            r.invoke(0x45eff0, p, {1});
            break;
        case 38:
            r.virt(box, 0);
            break;
        case 39:
            r.invoke(0x45eff0, p, {0});
            break;
        case 40:
            r.virt(box, 4);
            break;
        default:
            r.invoke(0x45e990, p, {a[0], a[1]});
            break;
        }
        if (changed && old != r.invoke(0x4dd480, box)) {
            auto item = r.invoke(0x4dd450, box, {r.invoke(0x4dd480, box)});
            if (item) {
                r.invoke(0x45f490, p, {0x5254e4, 0});
                r.invoke(0x45ef30, p, {r.get(item + 20)});
            }
        }
        r.idle(p);
        return changed;
    }
    case 0x45bd90: {
        auto box = p + 0x154, old = r.invoke(0x4dd480, box);
        r.invoke(0x4ddc30, box);
        if (old != r.invoke(0x4dd480, box)) {
            auto item = r.invoke(0x4dd450, box, {r.invoke(0x4dd480, box)});
            if (item)
                r.invoke(0x45ef30, p, {r.get(item + 20)});
            r.idle(p);
        }
        return 1;
    }
    case 0x45bbc0: {
        r.invoke(0x4b3490, r.get(0x537200));
        auto box = p + 0x154, old = r.invoke(0x4dd480, box), bits = r.get(r.get(0x537200) + 528);
        uint32_t changed = 1;
        bool action = true;
        if (bits & 0x80000000)
            r.virt(box, 4);
        else if (bits & 0x40000000)
            r.virt(box, 0);
        else if (bits & 0x10000000)
            r.invoke(0x45eff0, p, {1});
        else if (bits & 0x20000000)
            r.invoke(0x45eff0, p, {0});
        else {
            action = false;
            if (bits & 0xffffff)
                r.invoke(0x4ddbc0, box);
            else if (r.get(r.get(0x537200) + 532) & 0xf0000000) {
                r.timer(p + 0x2a8, r.get(0x53720c));
                if (!r.get(p + 0x2a8)) {
                    bits = r.get(r.get(0x537200) + 532);
                    if (bits & 0x80000000)
                        r.virt(box, 4);
                    else if (bits & 0x40000000)
                        r.virt(box, 0);
                    else
                        r.invoke(0x45eff0, p, {uint32_t((bits & 0x10000000) != 0)});
                    r.put(p + 0x2a8, r.get(0x528a64));
                    action = true;
                }
            }
            if (!action)
                changed = 0;
        }
        if (action && (r.get(r.get(0x537200) + 528) & 0xf0000000))
            r.put(p + 0x2a8, r.get(0x528a60));
        if (changed && old != r.invoke(0x4dd480, box)) {
            auto item = r.invoke(0x4dd450, box, {r.invoke(0x4dd480, box)});
            if (item) {
                r.invoke(0x45f490, p, {0x5254e4, 0});
                r.invoke(0x45ef30, p, {r.get(item + 20)});
            }
            r.idle(p);
        }
        return changed;
    }
    case 0x45f490:
        if (r.get(p + 12) && r.part(p, 40)) {
            auto sound = r.lookup(r.part(p, 40) + 16, a[0]);
            if (sound) {
                if (r.get(0x532c0c))
                    r.invoke(0x4b45f0, r.get(sound + 16), {r.get(0x532c10), 0, 0, 0});
                if (a[1])
                    r.invoke(0x4b8960, 0, {r.get(r.get(sound + 16) + 40)});
            }
        }
        return 0;
    case 0x45d3f0:
        r.invoke(0x4dd030, p + 0x154);
        r.invoke(0x45d410, p, {a[0]});
        return 0;
    case 0x45ef30: {
        auto box = p + 0x154, item = r.invoke(0x4dd450, box, {r.invoke(0x4dd480, box)});
        if (item) {
            uint32_t pos[2]{}, rect[4]{};
            uint32_t arg = 0;
            r.local(0x4ded20, item, &arg, 1, 1, pos, 8);
            auto y = pos[1];
            if ((a[0] < 0x2b5d || a[0] > 0x2b6b) && (a[0] < 0x2bc1 || a[0] > 0x2bcf)) {
                rect[0] = r.get(p + 0x27c) - 30;
                rect[2] = r.get(p + 0x284) + 30;
                y += 17;
            } else {
                r.local(0x4ded40, item, &arg, 1, 1, rect, 16);
                rect[0] -= 18;
                rect[2] += 18;
                y += 14;
            }
            r.put(r.get(p + 0x25c) + 76, rect[0]);
            r.put(r.get(p + 0x25c) + 80, y);
            r.put(r.get(p + 0x260) + 76, rect[2]);
            r.put(r.get(p + 0x260) + 80, y);
        }
        return 0;
    }
    case 0x45eff0: {
        auto box = p + 0x154, item = r.invoke(0x4dd450, box, {r.invoke(0x4dd480, box)});
        if (!item)
            return 0;
        auto id = r.get(item + 20);
        if (id > 0x3458 && id < 0x345d) {
            r.invoke(0x45f100, p, {1 + uint32_t(a[0] != 0), id});
            return 0;
        }
        if (id > 0x34bc && id < 0x34c2) {
            r.invoke(0x45f360, p, {1 + uint32_t(a[0] != 0), id});
            return 0;
        }
        uint32_t low, high, amount = 7;
        if (id >= 0x2b5d && id <= 0x2b6a) {
            low = 0x2b5d;
            high = 0x2b6a;
        } else if (id >= 0x2bc1 && id <= 0x2bce) {
            low = 0x2bc1;
            high = 0x2bce;
        } else if (id >= 0x3a99 && id <= 0x3aa2) {
            low = 0x3a99;
            high = 0x3aa2;
            amount = 5;
        } else
            return 0;
        auto next = id + (a[0] ? 0 - amount : amount);
        if (next >= low && next <= high) {
            auto node = r.invoke(0x4dd020, box, {next});
            if (node && node + 60 && !((r.invoke(0x4ed050, node + 60)) & 32))
                r.invoke(0x4dd520, box, {node + 60});
        }
        return 0;
    }
    case 0x45fa50:
        if (!r.get(0x537b58))
            return 0;
        return r.invoke(0x45c240, r.get(0x537b58), {a[0], a[1]});
    case 0x45c3d0:
        r.invoke(0x45f490, p, {0x5254dc, 0});
        if (si(a[1]) > 0)
            r.post(p, a[1]);
        if (a[2])
            r.invoke(0x45d410, p, {a[0]});
        return 1;
    case 0x42b990:
        if (si(a[0]) > 0 && si(a[0]) < 15)
            r.invoke(0x546d50, 0, {r.get(r.get(p + 4) + 4), 0x111, 0x807f, a[0]});
        return 0;
    case 0x42b9c0:
        if (si(a[0]) > 0 && si(a[0]) < 15) {
            r.put(p + 0xd4, a[0]);
            r.put(p + 0xa8, 1);
            r.put(p + 0xd8, a[1]);
            r.invoke(0x546d50, 0, {r.get(r.get(p + 4) + 4), 0x111, 0x807e, 0});
        }
        return 0;
    case 0x45c420:
        if (a[0] == 0x2715) {
            r.invoke(0x45f490, p, {0x5254dc, 1});
            r.post(p, 0x8035);
            return 1;
        }
        if (a[0] == 0x2717) {
            r.put(0x537360, 1);
            r.invoke(0x45f490, p, {0x5254dc, 1});
            r.post(p, 0x8021);
            return 1;
        }
        return r.invoke(0x45c3d0, p, {a[0], 0xffffffff, 1});
    case 0x45c4a0:
        switch (a[0]) {
        case 0x2afd:
            return r.invoke(0x45c3d0, p, {a[0], 0x8039, 0});
        case 0x2af9:
        case 0x2afa:
        case 0x2afc:
            return r.invoke(0x45c3d0, p, {a[0], 0xffffffff, 1});
        case 0x2afe:
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.invoke(0x45d3f0, p, {10000});
            return 1;
        case 0x2afb:
            if (!r.invoke(0x4f2360, 0, {0x526ab8})) {
                r.invoke(0x4f2360, 0, {0x526aac});
                return r.invoke(0x45c3d0, p, {a[0], 0x8042, 0});
            }
            r.invoke(0x42a710, r.get(p + 4), {0x528d6c});
            return r.invoke(0x45c3d0, p, {a[0], 0xffffffff, 0});
        default:
            return 0;
        }
    case 0x45d070:
        if (a[0] > 0x2b5c && a[0] < 0x2b6b) {
            auto level = a[0] - 0x2b5c;
            if (r.invoke(0x42ba10, r.get(p + 4), {level})) {
                r.invoke(0x45f490, p, {0x5254dc, 1});
                r.invoke(0x42b990, r.get(p + 4), {level});
            }
            return 1;
        }
        if (a[0] == 0x2b6b) {
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.invoke(0x45d3f0, p, {0x2711});
            return 1;
        }
        return 0;
    case 0x45d0f0:
        if (a[0] > 0x2bc0 && a[0] < 0x2bcf) {
            r.invoke(0x45c3d0, p, {a[0], 0xffffffff, 1});
            return 1;
        }
        if (a[0] == 0x2bcf) {
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.invoke(0x45d3f0, p, {0x2711});
            return 1;
        }
        return 0;
    case 0x45d150: {
        auto offset = a[0] - 0x1b58b, level = offset / 10 + 1, slot = offset % 10;
        if (level >= 1 && level <= 14 && slot < 3) {
            if (r.invoke(0x42ba70, r.get(p + 4), {level, slot})) {
                r.invoke(0x45f490, p, {0x5254dc, 1});
                r.invoke(0x42b9c0, r.get(p + 4), {level, slot});
            }
            return 1;
        }
        if (level >= 1 && level <= 14 && slot == 3) {
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.invoke(0x45d3f0, p, {0x2afa});
            return 1;
        }
        return 0;
    }
    case 0x45d3b0:
    case 0x45c7c0:
        if (a[0] != (f == 0x45d3b0 ? 0x2c89u : 0x3391u))
            return 0;
        r.invoke(0x45f490, p, {0x5254dc, 0});
        r.invoke(0x45d3f0, p, {f == 0x45d3b0 ? 0x2711u : 0x2714u});
        return 1;
    case 0x45c580:
        switch (a[0]) {
        case 0x2ee1:
            return r.invoke(0x45c3d0, p, {a[0], 0x8025, 0});
        case 0x2ee2:
            return r.invoke(0x42d460, r.get(p + 4), {0x528d94});
        case 0x2ee3:
            return r.invoke(0x45c3d0, p, {a[0], 0x8059, 0});
        case 0x2ee4:
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.invoke(0x45d3f0, p, {10000});
            return 1;
        default:
            return 0;
        }
    case 0x45d000:
        if (a[0] == 0x2fa9) {
            r.invoke(0x45f490, p, {0x5254dc, 1});
            if (r.invoke(0x42bc40, 0, {0}))
                r.invoke(0x42be30, r.get(p + 4), {1});
            return 1;
        }
        if (a[0] == 0x2faa) {
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.invoke(0x45d3f0, p, {0x2712});
            return 1;
        }
        return 0;
    case 0x45c800:
        if (a[0] > 15000 && a[0] < 0x3aa3) {
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.put(p + 0x294, 1);
            r.put(p + 0x298, a[0]);
            return 1;
        }
        if (a[0] == 0x3aa3) {
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.invoke(0x45d3f0, p, {10000});
            return 1;
        }
        return 0;
    case 0x45c610:
        switch (a[0]) {
        case 0x32c9:
        case 0x32cb:
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.post(p, 0x8090, a[0] == 0x32c9 ? 4 : 0);
            return 1;
        case 0x32ca:
        case 0x32cc:
        case 0x32cd:
            return r.invoke(0x45c3d0, p, {a[0], 0xffffffff, 1});
        case 0x32ce:
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.invoke(0x45d3f0, p, {10000});
            return 1;
        default:
            return 0;
        }
    case 0x45c6f0: {
        uint32_t method = 0;
        switch (a[0]) {
        case 0x332d:
            method = 0x42bbb0;
            break;
        case 0x332e:
            method = 0x42bbe0;
            break;
        case 0x332f:
            method = 0x42bbd0;
            break;
        case 0x3330:
            method = 0x42bbf0;
            break;
        case 0x3331:
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.invoke(0x45d3f0, p, {0x2714});
            return 1;
        default:
            return 0;
        }
        r.invoke(0x45f490, p, {0x5254dc, 0});
        r.invoke(method, r.get(p + 4));
        r.invoke(0x45cd90, p);
        r.invoke(0x45ce80, p);
        return 1;
    }
    case 0x45cfa0:
        if (a[0] == 0x36b1) {
            r.post(p, 0x8008);
            return 1;
        }
        if (a[0] == 0x36b2) {
            r.invoke(0x45f490, p, {0x5254dc, 0});
            r.invoke(0x45d3f0, p, {10000});
            return 1;
        }
        return 0;
    case 0x45e7c0: {
        if (r.get(p + 0x29c) != 0x32cc || !r.get(p + 4) || !r.get(p + 0x270) || !r.get(p + 0x274))
            return 0;
        for (auto pair : {std::pair<uint32_t, uint32_t>{0x3459, 0x270}, {0x345c, 0x274}}) {
            auto node = r.invoke(0x4dd020, p + 0x154, {pair.first});
            if (node && node + 60) {
                auto flags = r.invoke(0x4ed050, node + 60),
                     index = pair.first == 0x3459 ? ((flags & 6) ? 42u : 41u) : ((flags & 6) ? 44u : 43u);
                r.invoke(0x4c7900, r.get(p + pair.second), {0x528ae8, index});
            }
        }
        return 1;
    }
    case 0x45e880: {
        if (r.get(p + 0x29c) != 0x32cd || !r.get(p + 4) || !r.get(p + 0x278))
            return 0;
        auto node = r.invoke(0x4dd020, p + 0x154, {0x34c0});
        if (node && node + 60) {
            auto flags = r.invoke(0x4ed050, node + 60);
            r.invoke(0x4c7900, r.get(p + 0x278), {0x528ae8, (flags & 6) ? 46u : 45u});
        }
        return 1;
    }
    case 0x45db40: {
        if (a[0] == 0x32cc) {
            if (r.get(p + 0x270)) {
                auto node = r.invoke(0x4dd020, p + 0x154, {0x3459});
                if (node && node + 60) {
                    auto flags = r.invoke(0x4ed050, node + 60), actor = r.get(p + 0x270);
                    r.put(actor + 64, (flags & 32) ? r.get(actor + 64) | 1 : r.get(actor + 64) & ~1u);
                }
            }
            if (r.get(p + 0x274)) {
                auto node = r.invoke(0x4dd020, p + 0x154, {0x345c});
                if (node && node + 60) {
                    auto flags = r.invoke(0x4ed050, node + 60), actor = r.get(p + 0x274);
                    r.put(actor + 64, (flags & 32) ? r.get(actor + 64) | 1 : r.get(actor + 64) & ~1u);
                }
            }
            r.invoke(0x45e7c0, p);
        } else if (a[0] == 0x32cd) {
            if (r.get(p + 0x278)) {
                auto node = r.invoke(0x4dd020, p + 0x154, {0x34c0});
                if (node && node + 60) {
                    auto flags = r.invoke(0x4ed050, node + 60), actor = r.get(p + 0x278);
                    r.put(actor + 64, (flags & 32) ? r.get(actor + 64) | 1 : r.get(actor + 64) & ~1u);
                }
            }
            r.invoke(0x45e880, p);
        } else
            for (auto off : {0x270u, 0x274u, 0x278u})
                if (r.get(p + off))
                    r.put(r.get(p + off) + 64, r.get(r.get(p + off) + 64) | 1);
        return 0;
    }
    case 0x45e0e0:
        if (!r.get(p + 12) || !r.get(p + 44))
            return 0;
        r.invoke(0x4bb870, r.get(r.get(p + 44) + 16));
        r.invoke(0x4bb990, r.get(r.get(p + 44) + 16), {0, 256, 0, 0, 0, 500});
        r.clear(p);
        {
            auto sound = r.lookup(r.get(r.get(r.get(p + 4) + 48) + 40) + 16, 0x528b38);
            if (sound && r.invoke(0x4b3e70, r.get(sound + 16)))
                r.invoke(0x4b3e30, r.get(sound + 16));
        }
        return 1;
    case 0x45e1b0:
        if (!r.get(p + 12) || !r.get(p + 44))
            return 0;
        {
            auto s = r.surface(p), back = r.get(s + 24), front = r.get(s + 20);
            if (back && front)
                r.invoke(0x4b9d80, r.get(front + 44), {0, 0, r.get(back + 44), back + 28, 16});
            r.invoke(0x4dd270, p + 0x154, {r.get(front + 44)});
            r.overlay(p, r.get(front + 44));
        }
        r.invoke(0x45db40, p, {r.get(p + 0x29c)});
        r.render(p);
        r.invoke(0x4bb910, r.get(r.get(p + 44) + 16), {0, 256, 0, 0, 0, 0});
        r.put(r.part(p, 24) + 100, r.get(p + 44));
        r.virt(r.get(p + 44), 52);
        {
            auto s = r.surface(p);
            r.invoke(0x4b98b0, r.get(r.get(s + 16) + 44), {0});
            r.invoke(0x45fee0, r.get(s + 20), {r.get(s + 24)});
        }
        {
            auto manager = r.get(r.get(p + 44) + 16);
            r.invoke(0x4bbd90, manager, {0, 256, r.get(manager + 16), 1000});
        }
        r.invoke(0x42abf0, r.get(p + 4));
        r.idle(p);
        {
            auto sound = r.lookup(r.get(r.get(r.get(p + 4) + 48) + 40) + 16, 0x528b38);
            if (sound && !r.invoke(0x4b3e70, r.get(sound + 16))) {
                if (r.get(0x532c0c))
                    r.invoke(0x4b3dc0, r.get(sound + 16), {0, 0, 0, 1});
                r.invoke(0x4b3fe0, r.get(sound + 16), {40, 2000, 0});
            }
        }
        return 1;
    case 0x45c240: {
        auto id = a[0];
        if (!a[1]) {
            r.invoke(0x45f490, p, {0x525c04, 0});
            return 0;
        }
        static const uint32_t ranges[][3] = {
            {10000, 0x2718, 0x45c420},  {11000, 0x2aff, 0x45c4a0},    {0x2b5c, 0x2b6c, 0x45d070},
            {0x2bc0, 0x2bd0, 0x45d0f0}, {0x1b58a, 0x1b611, 0x45d150}, {0x2c88, 0x2c8a, 0x45d3b0},
            {12000, 0x2ee5, 0x45c580},  {0x2fa8, 0x2fab, 0x45d000},   {15000, 0x3aa4, 0x45c800},
            {13000, 0x32cf, 0x45c610},  {0x332c, 0x3332, 0x45c6f0},   {0x3390, 0x3392, 0x45c7c0},
            {0x3458, 0x345e, 0x45c880}, {0x34bc, 0x34c3, 0x45cb90},   {14000, 0x36b3, 0x45cfa0}};
        for (auto &row : ranges)
            if (id > row[0] && id < row[1])
                return r.invoke(row[2], p, {id});
        return 0;
    }
    default:
        r.fail(3);
    }
}
bool owned(uint32_t f) {
    switch (f) {
    case 0x45fbb0:
    case 0x45cd60:
    case 0x45c880:
    case 0x45cb90:
    case 0x45fde0:
    case 0x45fe60:
    case 0x45fe40:
    case 0x45fee0:
    case 0x45dc90:
    case 0x45f100:
    case 0x45f360:
    case 0x45e370:
    case 0x45e5c0:
    case 0x45be10:
    case 0x45f940:
    case 0x45ef00:
    case 0x45e990:
    case 0x45fa80:
    case 0x45ace0:
    case 0x45b880:
    case 0x45b130:
    case 0x45b050:
    case 0x429510:
    case 0x429530:
    case 0x45b8c0:
    case 0x45b960:
    case 0x45b9a0:
    case 0x45b650:
    case 0x45ba50:
    case 0x45bd90:
    case 0x45bbc0:
    case 0x45f490:
    case 0x45d3f0:
    case 0x45ef30:
    case 0x45eff0:
    case 0x45fa50:
    case 0x45c240:
    case 0x45b3f0:
    case 0x45b540:
    case 0x45ce60:
    case 0x45cd90:
    case 0x45ce80:
    case 0x45cee0:
    case 0x45b240:
    case 0x45e8f0:
    case 0x45d500:
    case 0x45d720:
    case 0x45d410:
    case 0x45d750:
    case 0x45ea80:
    case 0x45e040:
    case 0x45c3d0:
    case 0x42b990:
    case 0x42b9c0:
    case 0x45c420:
    case 0x45c4a0:
    case 0x45d070:
    case 0x45d0f0:
    case 0x45d150:
    case 0x45d3b0:
    case 0x45c7c0:
    case 0x45c580:
    case 0x45d000:
    case 0x45c800:
    case 0x45c610:
    case 0x45c6f0:
    case 0x45cfa0:
    case 0x45e7c0:
    case 0x45e880:
    case 0x45db40:
    case 0x45e0e0:
    case 0x45e1b0:
        return true;
    default:
        return false;
    }
}
uint32_t arity(uint32_t f) {
    if (f == 0x45fbb0)
        return 5;
    if (f == 0x45cd60 || f == 0x45c880 || f == 0x45cb90)
        return 1;
    if (f == 0x45fde0)
        return 3;
    if (f == 0x45fe40 || f == 0x45fee0 || f == 0x45dc90)
        return 1;
    if (f == 0x45f100 || f == 0x45f360)
        return 2;
    if (f == 0x45e990)
        return 2;
    if (f == 0x45be10)
        return 3;
    if (f == 0x45f940 || f == 0x45ef00 || f == 0x45fa80)
        return 1;
    if (f == 0x45db40)
        return 1;
    if (f == 0x45c3d0)
        return 3;
    if (f == 0x42b9c0)
        return 2;
    if (f == 0x42b990 || f == 0x45c420 || f == 0x45c4a0 || f == 0x45d070 || f == 0x45d0f0 || f == 0x45d150 ||
        f == 0x45d3b0 || f == 0x45c7c0 || f == 0x45c580 || f == 0x45d000 || f == 0x45c800 || f == 0x45c610 ||
        f == 0x45c6f0 || f == 0x45cfa0)
        return 1;
    if (f == 0x45ace0 || f == 0x45bd90)
        return 3;
    if (f == 0x45ba50 || f == 0x45f490 || f == 0x45fa50 || f == 0x45c240)
        return 2;
    if (f == 0x45b3f0 || f == 0x45b540 || f == 0x45d500 || f == 0x45d720 || f == 0x45d410 || f == 0x45d750 ||
        f == 0x429510 || f == 0x45d3f0 || f == 0x45eff0 || f == 0x45ef30)
        return 1;
    return 0;
}
} // namespace
extern "C" uint32_t claw_state_five_entry(uint32_t f, uint32_t p, const uint32_t *a, uint32_t n,
                                          ClawStateFiveContext *c, ClawStateFiveDependency d, void *u, uint32_t *out) {
    if (!c || !out || !owned(f))
        return 0;
    if (n != arity(f) || (n && !a)) {
        c->fault = 3;
        return 0;
    }
    try {
        Run r{*c, d, u};
        uint32_t args[40]{};
        std::copy_n(a, n, args);
        *out = body(r, f, p, args);
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
extern "C" uint32_t claw_state_five_function(uint32_t vt, uint32_t slot) {
    if (slot % 4)
        return 0;
    if (vt == 0x50c1e4 && slot < 80) {
        static const uint32_t v[] = {0x429510, 0x45ace0, 0x45b050, 0x40af20, 0x4c9bd0, 0x45b650, 0x45b8c0,
                                     0x45b960, 0x45b9a0, 0x45b3f0, 0x45b540, 0x40af40, 0x45ba50, 0x45bd90,
                                     0x40af50, 0x40af50, 0x4bb030, 0x4bb030, 0x48fcf0, 0x4bd250};
        return v[slot / 4];
    }
    if (vt == 0x50e8e4 && slot < 56) {
        static const uint32_t v[] = {0x4f701d, 0x45fe40, 0x4c9e30, 0x4c96b0, 0x4c9e30, 0x4cacb0, 0x4bd250,
                                     0x4d4160, 0x40af90, 0x4d4000, 0x4d4280, 0x4d4100, 0x4d4190, 0x4d4220};
        return v[slot / 4];
    }
    if (vt == 0x50c23c && slot < 32) {
        static const uint32_t v[] = {0x4dda50, 0x4ddb40, 0x4ddac0, 0x4ddb40, 0x4bc110, 0x4bc110, 0x4dd0e0, 0x45fa50};
        return v[slot / 4];
    }
    return 0;
}
