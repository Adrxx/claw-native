#include "PlayerMenuManagementRuntime.h"
#include "PlayerDeathServices.h"
#include "ActorDestruction.h"
#include "CheckpointLogicRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
#include <vector>
namespace {
struct Failure {};
bool owned(uint32_t f) {
    switch (f) {
    case 0x426e30:
    case 0x49b160:
    case 0x49b630:
    case 0x49afd0:
    case 0x49b3a0:
    case 0x49b470:
    case 0x49c860:
    case 0x49aed0:
        return true;
    default:
        return false;
    }
}
uint32_t arity(uint32_t f) {
    if (f == 0x426e30)
        return 3;
    if (f == 0x49b160 || f == 0x49b630)
        return 4;
    if (f == 0x49afd0 || f == 0x49aed0)
        return 1;
    return 2;
}
int32_t signedWord(uint32_t v) {
    int32_t s;
    std::memcpy(&s, &v, 4);
    return s;
}
struct Run {
    ClawPlayerMenuManagementContext &c;
    ClawPlayerMenuManagementDependency d;
    void *u;
    uint32_t operations = 0;
    uint32_t partialToken = 0, partialBytes = 0;
    std::vector<uint32_t> partial;
    Run(ClawPlayerMenuManagementContext &context, ClawPlayerMenuManagementDependency dependency, void *user)
        : c(context), d(dependency), u(user) {
    }
    [[noreturn]] void fail(uint32_t fault = 1) {
        if (!c.fault)
            c.fault = fault;
        throw Failure{};
    }
    void step() {
        if (c.fault)
            throw Failure{};
        if (++operations > (c.maximumOperations ? c.maximumOperations : 65536))
            fail(3);
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        step();
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
    uint8_t *bytes(uint32_t t, uint32_t n) {
        step();
        if (c.strings && c.strings->bytes) {
            auto p = c.strings->bytes(c.strings->byteContext, t, n);
            if (!p)
                fail();
            return p;
        }
        if (c.playerCache && c.playerCache->saveLoad && c.playerCache->saveLoad->save.lookupBytes) {
            auto p = c.playerCache->saveLoad->save.lookupBytes(c.playerCache->saveLoad->save.scene.context, t, n);
            if (!p)
                fail();
            return p;
        }
        return reinterpret_cast<uint8_t *>(span(t & ~3u, (n + (t & 3u) + 3) / 4)) + (t & 3u);
    }
    uint32_t invoke(uint32_t, uint32_t, const uint32_t *, uint32_t);
    uint32_t invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        return invoke(f, t, a.begin(), uint32_t(a.size()));
    }
    void flushPartial() {
        if (!partialBytes)
            return;
        if (!c.strings || !c.strings->bytes)
            fail();
        auto p = c.strings->bytes(c.strings->byteContext, partialToken, partialBytes);
        if (!p)
            fail();
        std::memcpy(p, partial.data(), partialBytes);
        partialBytes = 0;
    }
    uint32_t event(ClawPlayerMenuManagementCall &q) {
        step();
        flushPartial();
        if (!d)
            fail();
        auto v = d(&c, &q, u);
        if (c.fault)
            throw Failure{};
        return v;
    }
    uint32_t service(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        ClawPlayerMenuManagementCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        std::copy_n(a, n, q.arguments);
        if (f == 0x4a3920 && n > 1)
            q.name = reinterpret_cast<char *>(bytes(a[1], 1));
        return event(q);
    }
    static uint32_t *lookup(void *p, uint32_t t, uint32_t n) {
        auto &r = *static_cast<Run *>(p);
        r.step();
        auto q = r.c.scene.lookup ? r.c.scene.lookup(r.c.scene.context, t, n) : nullptr;
        if (q)
            return q;
        if (r.c.strings && r.c.strings->bytes && n && n < 65536 && !(t & 3u)) {
            if (r.partialBytes && t == r.partialToken && n == r.partial.size())
                return r.partial.data();
            r.flushPartial();
            for (uint32_t tail = 1; tail <= 3 && tail < n * 4; ++tail) {
                auto valid = n * 4 - tail;
                auto b = r.c.strings->bytes(r.c.strings->byteContext, t, valid);
                if (b) {
                    r.partialToken = t;
                    r.partialBytes = valid;
                    r.partial.assign(n, 0);
                    std::memcpy(r.partial.data(), b, valid);
                    return r.partial.data();
                }
            }
        }
        return nullptr;
    }
    static uint32_t *strictLookup(void *p, uint32_t t, uint32_t n) {
        auto &r = *static_cast<Run *>(p);
        r.step();
        return r.c.scene.lookup ? r.c.scene.lookup(r.c.scene.context, t, n) : nullptr;
    }
    static uint8_t *strictBytes(void *p, uint32_t t, uint32_t n) {
        auto &r = *static_cast<Run *>(p);
        r.step();
        if (r.c.strings && r.c.strings->bytes)
            return r.c.strings->bytes(r.c.strings->byteContext, t, n);
        if (r.c.playerCache && r.c.playerCache->saveLoad && r.c.playerCache->saveLoad->save.lookupBytes)
            return r.c.playerCache->saveLoad->save.lookupBytes(r.c.playerCache->saveLoad->save.scene.context, t, n);
        auto q = strictLookup(p, t & ~3u, (n + (t & 3u) + 3) / 4);
        return q ? reinterpret_cast<uint8_t *>(q) + (t & 3u) : nullptr;
    }
    static uint8_t *byteLookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->bytes(t, n);
    }
    static uint32_t allocate(void *p, uint32_t n) {
        return static_cast<Run *>(p)->invoke(0x4f63ec, 0, {n});
    }
    static void release(void *p, uint32_t t) {
        static_cast<Run *>(p)->invoke(0x4f6428, 0, {t});
    }
    static uint32_t hostCall(void *p, ClawSceneActorCall q) {
        return static_cast<Run *>(p)->invoke(q.function, q.receiver, q.arguments, q.argumentCount);
    }
    static uint32_t clock(void *p) {
        auto &r = *static_cast<Run *>(p);
        if (!r.c.scene.readClock)
            r.fail();
        return r.c.scene.readClock(r.c.scene.context);
    }
    ClawSceneActorHost host() {
        return {this, lookup, allocate, release, hostCall, clock};
    }
    static uint32_t cacheDependency(ClawPlayerCacheApplicationContext *, const ClawPlayerCacheApplicationCall *e,
                                    void *p) {
        auto &r = *static_cast<Run *>(p);
        if (!e->localMask && !e->bufferCount)
            return r.invoke(e->function, e->receiver, e->arguments, e->argumentCount);
        auto q = *e;
        return r.event(q);
    }
    static uint32_t saveDependency(ClawSaveLoadContext *, const ClawSaveLoadCall *q, void *p) {
        return static_cast<Run *>(p)->invoke(q->function, q->receiver, q->arguments, q->argumentCount);
    }
    static uint32_t stringDependency(ClawCStringAssignmentContext *, const ClawCStringAssignmentCall *q, void *p) {
        return static_cast<Run *>(p)->invoke(q->function, q->receiver, q->arguments, q->argumentCount);
    }
    static uint32_t fadeDependency(ClawPlayerFadeContext *, const ClawPlayerFadeCall *q, void *p) {
        return static_cast<Run *>(p)->invoke(q->function, q->receiver, q->arguments, q->argumentCount);
    }
    static uint32_t checkpointDependency(ClawCheckpointContext *, const ClawCheckpointCall *q, void *p) {
        return static_cast<Run *>(p)->invoke(q->function, q->receiver, q->arguments, q->argumentCount);
    }
    static uint32_t deathDependency(ClawPlayerDeathServiceContext *, const ClawPlayerDeathServiceCall *q, void *p) {
        return static_cast<Run *>(p)->invoke(q->function, q->receiver, q->arguments, q->argumentCount);
    }
    static uint32_t startupDependency(ClawPlayerStartupContext *, const ClawPlayerStartupCall *e, void *p) {
        auto &r = *static_cast<Run *>(p);
        if (!e->localMask && !e->bufferCount)
            return r.invoke(e->function, e->receiver, e->arguments, e->argumentCount);
        ClawPlayerMenuManagementCall q{};
        q.function = e->function;
        q.receiver = e->receiver;
        q.argumentCount = e->argumentCount;
        std::copy_n(e->arguments, e->argumentCount, q.arguments);
        q.localMask = e->localMask;
        q.bufferCount = e->bufferCount;
        std::copy_n(e->buffers, e->bufferCount, q.buffers);
        std::copy_n(e->bufferBytes, e->bufferCount, q.bufferBytes);
        return r.event(q);
    }
    uint32_t body(uint32_t, uint32_t, const uint32_t *);
    uint32_t length(uint32_t t, uint32_t cap) {
        for (uint32_t i = 0; i < cap; ++i)
            if (!*bytes(t + i, 1))
                return i;
        fail(2);
    }
    void text(uint32_t w, uint32_t id, uint32_t value) {
        invoke(0x546d3c, 0, {w, id, value});
    }
    void number(uint32_t w, uint32_t id, uint32_t value) {
        invoke(0x546d1c, 0, {w, id, value, 0});
    }
    void end(uint32_t w, uint32_t value) {
        invoke(0x546d34, 0, {w, value});
    }
};
uint32_t Run::invoke(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
    step();
    if (n > 40)
        fail(3);
    if (owned(f)) {
        if (n != arity(f))
            fail(3);
        return body(f, t, a);
    }
    uint32_t out = 0;
    if (f == 0x49ae60) {
        ClawCheckpointGlobals g{};
        ClawCheckpointContext q{};
        q.scene = host();
        q.globals = &g;
        if (!claw_checkpoint_entry(f, t, a, n, &q, checkpointDependency, this, &out) || q.fault)
            fail(q.fault ? q.fault : 1);
        return out;
    }
    if (c.playerCache) {
        auto q = *c.playerCache;
        q.scene = host();
        q.fault = 0;
        if (claw_player_cache_application_entry(f, t, a, n, &q, cacheDependency, this, &out)) {
            if (q.fault)
                fail(q.fault);
            return out;
        }
        if (q.fault)
            fail(q.fault);
        if (q.composeSaveLoad && q.saveLoad) {
            auto s = *q.saveLoad;
            s.save.scene = host();
            s.save.lookupBytes = byteLookup;
            s.save.fault = s.fault = 0;
            if (claw_save_load_entry(f, t, a, n, &s, saveDependency, this, &out)) {
                if (s.fault || s.save.fault)
                    fail(s.fault ? s.fault : s.save.fault);
                return out;
            }
            if (s.fault || s.save.fault)
                fail(s.fault ? s.fault : s.save.fault);
        }
    }
    if (c.startup) {
        auto q = *c.startup;
        q.scene = host();
        q.fault = 0;
        if (claw_player_startup_entry(f, t, a, n, &q, startupDependency, this, &out)) {
            if (q.fault)
                fail(q.fault);
            return out;
        }
        if (q.fault)
            fail(q.fault);
    }
    if (c.composeStrings) {
        if (!c.strings)
            fail();
        auto q = *c.strings;
        q.scene = host();
        q.scene.lookup = strictLookup;
        q.byteContext = this;
        q.bytes = strictBytes;
        q.fault = 0;
        if (claw_cstring_assignment_entry(f, t, a, n, &q, stringDependency, this, &out)) {
            if (q.fault)
                fail(q.fault);
            return out;
        }
        if (q.fault)
            fail(q.fault);
        if (f == 0x4f65f2) {
            if (!q.allocation || !q.allocation->fade)
                fail();
            auto fade = *q.allocation->fade;
            fade.scene = host();
            fade.fault = 0;
            auto allocation = *q.allocation;
            allocation.fade = &fade;
            allocation.emptyStringToken = get(0x52e1cc);
            if (!claw_player_fade_blend_entry(f, t, a, n, &allocation, fadeDependency, this, &out) || fade.fault)
                fail(fade.fault ? fade.fault : 1);
            flushPartial();
            return out;
        }
        if (f == 0x4f6449) {
            ClawPlayerDeathServiceGlobals g{0, get(0x52e1cc)};
            ClawPlayerDeathServiceContext s{host(), &g, 0, 0};
            if (!claw_player_death_service_entry(f, t, a, n, &s, deathDependency, this, &out) || s.fault)
                fail(s.fault ? s.fault : 1);
            return out;
        }
        if (f == 0x4f6584) {
            ClawActorDestructionGlobals g{0, 0, get(0x52e1cc)};
            uint32_t fault = 0;
            if (!claw_actor_destruction_entry(f, t, 0, &g, host(), &fault, &out) || fault)
                fail(fault ? fault : 1);
            return out;
        }
    }
    return service(f, t, a, n);
}
uint32_t Run::body(uint32_t f, uint32_t t, const uint32_t *a) {
    switch (f) {
    case 0x426e30:
        if (!invoke(0x428c40, t, {13, 1, 1, a[2]}))
            invoke(0x429e10, t, {0x8005, 0x6ad});
        return 1;
    case 0x49afd0: {
        if (!a[0])
            return 0;
        auto index = invoke(0x546d44, 0, {a[0], 0x188, 0, 0});
        if (index == 0xffffffff)
            return 0;
        auto scratch = c.automaticToken + 128;
        *bytes(scratch, 1) = 0;
        if (invoke(0x546d44, 0, {a[0], 0x189, index, scratch}) == 0xffffffff)
            return 0;
        return invoke(0x49bee0, get(get(0x5371fc) + 96), {scratch});
    }
    case 0x49b630: {
        auto w = a[0];
        if (a[1] == 0x110) {
            auto app = get(0x5371fc);
            if (!app || !get(app + 96)) {
                end(w, 0);
                return 1;
            }
            put(0x53ebe0, get(app + 100));
            auto control = invoke(0x546d40, 0, {w, 0x43b});
            invoke(0x49c090, get(get(0x5371fc) + 96), {control, get(0x53ebe0), 1});
            invoke(0x49b050, 0, {w});
            return 1;
        }
        if (a[1] == 0x111) {
            if (a[2] == 1) {
                auto control = invoke(0x546d40, 0, {w, 0x43b});
                put(0x53ebe0, invoke(0x49afd0, 0, {control}));
                end(w, get(0x53ebe0) ? 1 : 0);
                return 1;
            }
            if (a[2] == 2) {
                end(w, 0);
                return 1;
            }
        }
        return 0;
    }
    case 0x49b160: {
        auto w = a[0];
        if (a[1] == 0x110) {
            auto app = get(0x5371fc);
            if (!app || !get(app + 100)) {
                end(w, 0);
                return 1;
            }
            auto record = get(app + 100);
            put(0x53ebe0, record);
            text(w, 0x408, record + 20);
            text(w, 0x437, record + 54);
            text(w, 0x438, record + 136);
            put(0x53ebe4, invoke(0x546d40, 0, {w, 0x443}));
            put(0x53ebe8, invoke(0x546d40, 0, {w, 0x446}));
            invoke(0x4a3920, 0, {c.automaticToken, 0x527000, record + 20});
            if (*bytes(record + 4, 1) & 4) {
                auto n = length(c.automaticToken, 128), suffix = length(0x526ff0, 128) + 1;
                if (n + suffix > 128)
                    fail(2);
                std::memcpy(bytes(c.automaticToken + n, suffix), bytes(0x526ff0, suffix), suffix);
            }
            text(w, 0x44b, c.automaticToken);
            for (uint32_t i = 0; i < 15; ++i) {
                invoke(0x4a3920, 0, {c.automaticToken, 0x526fcc, i});
                if (!i)
                    invoke(0x4a3920, 0, {c.automaticToken, 0x5280b8});
                invoke(0x546d44, 0, {get(0x53ebe4), 0x180, 0, c.automaticToken});
                invoke(0x546d44, 0, {get(0x53ebe8), 0x180, 0, c.automaticToken});
            }
            return 1;
        }
        if (a[1] != 0x111)
            return 0;
        if (a[2] == 1 || a[2] == 2) {
            end(w, 0);
            return 1;
        }
        auto control = get(0x53ebe4);
        if (control && a[3] == control) {
            if (uint16_t(a[2] >> 16) != 1)
                return 0;
            invoke(0x49b3a0, 0, {w, control});
            return 1;
        }
        control = get(0x53ebe8);
        if (!control || a[3] != control || uint16_t(a[2] >> 16) != 1)
            return 0;
        invoke(0x49b470, 0, {w, control});
        return 1;
    }
    case 0x49aed0:
        if (signedWord(a[0]) < 1)
            return 0;
        for (uint32_t kind = 0; kind < 3; ++kind)
            if (invoke(0x49af30, t, {a[0], kind}))
                return 1;
        return 0;
    case 0x49b3a0: {
        if (!get(0x53ebe0) || !a[1])
            return 0;
        auto index = invoke(0x546d44, 0, {a[1], 0x188, 0, 0});
        if (index == 0xffffffff || signedWord(index) < 0 || signedWord(index) >= 15)
            return 0;
        auto score = get(0x53ebe0) + 0x21c4 + index * 68;
        if (!score)
            return 0;
        number(a[0], 0x444, get(score + 4));
        auto cell = c.automaticToken + 384;
        invoke(0x49c860, 0, {cell, get(score + 8)});
        text(a[0], 0x445, get(cell));
        invoke(0x4f6584, cell);
        return 0;
    }
    case 0x49b470: {
        auto w = a[0];
        text(w, 0x450, 0x527024);
        number(w, 0x447, 0);
        text(w, 0x448, 0x523cd0);
        for (uint32_t id : {0x449u, 0x44au, 0x44cu, 0x44du, 0x44fu})
            number(w, id, 0);
        if (!get(0x53ebe0) || !a[1])
            return 0;
        auto index = invoke(0x546d44, 0, {a[1], 0x188, 0, 0});
        if (index == 0xffffffff || index == 0 || index == 1)
            return 0;
        if (!invoke(0x49aed0, get(0x53ebe0), {index}))
            return 0;
        auto cache = invoke(0x49ae60, get(0x53ebe0), {index - 1, 3});
        if (!cache)
            return 0;
        number(w, 0x447, get(cache + 16));
        auto cell = c.automaticToken + 384;
        invoke(0x49c860, 0, {cell, get(cache + 20)});
        text(w, 0x448, get(cell));
        static const uint32_t rows[][2] = {{0x449, 0xa4}, {0x44a, 0x98}, {0x44c, 0x9c}, {0x44d, 0xa0}, {0x44f, 0x94}};
        for (auto &row : rows)
            number(w, row[0], get(cache + row[1]));
        text(w, 0x450, 0x52700c);
        invoke(0x4f6584, cell);
        return 0;
    }
    case 0x49c860: {
        auto hours = a[1] / 3600000, remainder = a[1] - hours * 3600000, minutes = remainder / 60000,
             seconds = (remainder - minutes * 60000) / 1000;
        auto temporary = c.automaticToken + 388, format = c.automaticToken + 392;
        invoke(0x4a3920, 0, {format, 0x52dcf4, hours, minutes, seconds});
        invoke(0x4f65f2, temporary, {format});
        invoke(0x4f6449, a[0], {temporary});
        invoke(0x4f6584, temporary);
        return a[0];
    }
    default:
        fail(3);
    }
}
} // namespace
extern "C" uint32_t claw_player_menu_management_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                      ClawPlayerMenuManagementContext *c,
                                                      ClawPlayerMenuManagementDependency d, void *u, uint32_t *out) {
    if (!c || !out || !owned(f))
        return 0;
    if (n != arity(f) || (n && !a)) {
        c->fault = 3;
        return 0;
    }
    if (f == 0x426e30 && a[1] != 0x8090)
        return 0;
    try {
        Run r{*c, d, u};
        *out = r.body(f, t, a);
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
