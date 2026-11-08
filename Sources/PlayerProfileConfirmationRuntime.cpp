#include "PlayerProfileConfirmationRuntime.h"
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
    case 0x438c40:
    case 0x4399d0:
    case 0x43a760:
    case 0x439480:
    case 0x485160:
    case 0x4247c0:
    case 0x4247e0:
    case 0x424800:
    case 0x4299a0:
        return true;
    default:
        return false;
    }
}
uint32_t arity(uint32_t f) {
    if (f == 0x438c40)
        return 3;
    if (f == 0x4399d0)
        return 1;
    return 0;
}
int32_t signedWord(uint32_t v) {
    int32_t s;
    std::memcpy(&s, &v, 4);
    return s;
}
struct Run {
    ClawPlayerProfileConfirmationContext &c;
    ClawPlayerProfileConfirmationDependency d;
    void *u;
    uint32_t operations = 0;
    uint32_t partialToken = 0, partialBytes = 0;
    std::vector<uint32_t> partial;
    Run(ClawPlayerProfileConfirmationContext &context, ClawPlayerProfileConfirmationDependency dependency, void *user)
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
        if (++operations > (c.maximumOperations ? c.maximumOperations : 5000000))
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
        if (c.menu && c.menu->strings && c.menu->strings->bytes) {
            auto p = c.menu->strings->bytes(c.menu->strings->byteContext, t, n);
            if (!p)
                fail();
            return p;
        }
        if (c.menu && c.menu->playerCache && c.menu->playerCache->saveLoad &&
            c.menu->playerCache->saveLoad->save.lookupBytes) {
            auto p = c.menu->playerCache->saveLoad->save.lookupBytes(c.menu->playerCache->saveLoad->save.scene.context,
                                                                     t, n);
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
        if (!c.menu || !c.menu->strings || !c.menu->strings->bytes)
            fail();
        auto p = c.menu->strings->bytes(c.menu->strings->byteContext, partialToken, partialBytes);
        if (!p)
            fail();
        std::memcpy(p, partial.data(), partialBytes);
        partialBytes = 0;
    }
    uint32_t event(ClawPlayerProfileConfirmationCall &q) {
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
        ClawPlayerProfileConfirmationCall q{};
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
        if (r.c.menu && r.c.menu->strings && r.c.menu->strings->bytes && n && n < 65536 && !(t & 3u)) {
            if (r.partialBytes && t == r.partialToken && n == r.partial.size())
                return r.partial.data();
            r.flushPartial();
            for (uint32_t tail = 1; tail <= 3 && tail < n * 4; ++tail) {
                auto valid = n * 4 - tail;
                auto b = r.c.menu->strings->bytes(r.c.menu->strings->byteContext, t, valid);
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
        if (r.c.menu && r.c.menu->strings && r.c.menu->strings->bytes)
            return r.c.menu->strings->bytes(r.c.menu->strings->byteContext, t, n);
        if (r.c.menu && r.c.menu->playerCache && r.c.menu->playerCache->saveLoad &&
            r.c.menu->playerCache->saveLoad->save.lookupBytes)
            return r.c.menu->playerCache->saveLoad->save.lookupBytes(
                r.c.menu->playerCache->saveLoad->save.scene.context, t, n);
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
    static uint32_t fileDependency(ClawSaveFileContext *, const ClawSaveFileCall *q, void *p) {
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
        ClawPlayerProfileConfirmationCall q{};
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
    static uint32_t baseDependency(ClawSinglePlayerSceneContext *, ClawSinglePlayerSceneCall e, void *p) {
        auto &r = *static_cast<Run *>(p);
        if (!e.localMask && !e.bufferCount)
            return r.invoke(e.function, e.receiver, e.arguments, e.argumentCount);
        ClawPlayerProfileConfirmationCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, q.arguments);
        q.localMask = e.localMask;
        q.bufferCount = e.bufferCount;
        std::copy_n(e.buffers, e.bufferCount, q.buffers);
        std::copy_n(e.bufferBytes, e.bufferCount, q.bufferBytes);
        return r.event(q);
    }
    uint32_t virt(uint32_t t, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        return invoke(get(get(t) + slot), t, a);
    }
    uint32_t construct(uint32_t t, uint32_t data) {
        invoke(0x40b5c0, t);
        put(t, 0x50bf94);
        put(t + 344, data);
        for (uint32_t off : {348u, 352u, 356u, 340u, 360u})
            put(t + off, 0);
        put(t + 364, 1000);
        for (uint32_t off : {368u, 372u, 376u})
            put(t + off, 0);
        return t;
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
    if (!c.menu)
        fail();
    if (c.composeBase && c.base) {
        if (!c.base->globals)
            fail();
        auto q = *c.base;
        q.host = host();
        q.fault = 0;
        if (claw_single_player_scene_entry(f, t, a, n, &q, baseDependency, this, &out)) {
            if (q.fault)
                fail(q.fault);
            return out;
        }
        if (q.fault)
            fail(q.fault);
    }
    if (f == 0x49ae60) {
        ClawCheckpointGlobals g{};
        ClawCheckpointContext q{};
        q.scene = host();
        q.globals = &g;
        if (!claw_checkpoint_entry(f, t, a, n, &q, checkpointDependency, this, &out) || q.fault)
            fail(q.fault ? q.fault : 1);
        return out;
    }
    if (c.menu->playerCache) {
        auto q = *c.menu->playerCache;
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
            if (claw_save_file_entry(f, t, a, n, &s.save, fileDependency, this, &out)) {
                if (s.save.fault)
                    fail(s.save.fault);
                return out;
            }
            if (s.save.fault)
                fail(s.save.fault);
        }
    }
    if (c.menu->startup) {
        auto q = *c.menu->startup;
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
        if (!c.menu->strings)
            fail();
        auto q = *c.menu->strings;
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
    case 0x4299a0:
        return 13;
    case 0x4247c0:
    case 0x4247e0:
        put(0x52545c, f == 0x4247c0 ? 1 : 2);
        virt(t, 0x1e8);
        return 0;
    case 0x424800:
        if (get(0x5375c4)) {
            put(0x5375c0, 1);
            return 0;
        }
        if (auto app = get(0x5371fc)) {
            put(t + 692, 2);
            invoke(0x546d50, 0, {get(get(app + 4) + 4), 0x111, 0x8036, 0});
        }
        return 0;
    case 0x485160: {
        if (!get(0x5371fc) || !get(0x53ebe0))
            return 0;
        if (!invoke(0x4a3cf0, 0, {get(0x53ebe0) + 20, 0x5255e8}))
            return 0;
        auto app = get(0x5371fc);
        if (get(0x53ebe0) == get(app + 100)) {
            auto player = invoke(0x49bee0, get(app + 96), {0x5255e8});
            invoke(0x42bf90, get(0x5371fc), {player});
        }
        invoke(0x49bf30, get(get(0x5371fc) + 96), {get(0x53ebe0)});
        invoke(0x49bbc0, get(get(0x5371fc) + 96));
        if (!get(get(0x5371fc) + 100)) {
            auto player = invoke(0x49bee0, get(get(0x5371fc) + 96), {0x5255e8});
            invoke(0x42bf90, get(0x5371fc), {player});
            if (!get(get(0x5371fc) + 100)) {
                player = invoke(0x49bdb0, get(get(0x5371fc) + 96), {0x5255e8, 0x534938, 0x534938, 0});
                invoke(0x42bf90, get(0x5371fc), {player});
            }
        }
        invoke(0x4247c0, t);
        return 0;
    }
    case 0x43a760: {
        if (!get(t + 356))
            return 0;
        uint32_t helper = 0;
        auto mode = virt(get(t + 356), 16);
        if (mode == 13)
            helper = 0x43a720;
        else if (virt(get(t + 356), 16) == 5)
            helper = 0x45fdd0;
        else if (virt(get(t + 356), 16) == 11)
            helper = 0x452af0;
        if (helper && get(t + 356)) {
            auto previous = get(t + 356);
            invoke(helper, previous);
            virt(previous, 20);
        }
        return 0;
    }
    case 0x439480: {
        if (!get(t + 4) || !get(t + 352))
            return 0;
        auto scene = get(t + 12);
        if (get(t + 348))
            invoke(0x4bc4f0, get(scene + 28), {get(t + 348)});
        auto bitmap =
            invoke(0x4bc670, get(get(t + 12) + 28), {get(get(t + 4) + 124), get(get(t + 4) + 128), 0, 0, 0xffffffff});
        put(t + 348, bitmap);
        if (!bitmap)
            return 0;
        invoke(0x4cab10, get(get(t + 12) + 4));
        auto source = get(get(get(get(t + 12) + 4) + 20) + 44);
        auto rect = c.automaticToken + 20, sourceRect = rect + 16, targetRect = rect + 32;
        for (uint32_t i = 0; i < 4; ++i)
            put(sourceRect + i * 4, get(get(t + 348) + 124 + i * 4));
        invoke(0x546d58, 0, {rect, sourceRect});
        put(targetRect, 0);
        put(targetRect + 4, 0);
        put(targetRect + 8, get(rect + 8) - get(rect));
        put(targetRect + 12, get(rect + 12) - get(rect + 4));
        invoke(0x4b9ce0, get(t + 348), {rect, source, targetRect, 0x1000000, 0});
        return 1;
    }
    case 0x438c40: {
        auto previous = get(t + 356);
        if (!previous)
            previous = invoke(0x42bfd0, a[0]);
        put(t + 356, previous);
        for (uint32_t off : {340u, 348u, 352u, 360u})
            put(t + off, 0);
        put(t + 364, get(0x528a60));
        put(t + 372, 0);
        put(t + 376, 0);
        put(0x5375bc, 0);
        if (!get(t + 356))
            return 0;
        if (!invoke(0x48f0d0, t, {a[0], a[1], a[2]}))
            return 0;
        if (!invoke(0x4399d0, t, {get(t + 344)}))
            return 0;
        invoke(0x43a760, t);
        if (!invoke(0x439480, t))
            return 0;
        auto point = c.automaticToken + 12;
        invoke(0x546cd0, 0, {point});
        auto cursor = invoke(0x4c8da0, get(get(t + 12) + 8), {0, 0xffffff9c, 0xffffff9c, 0x4e1e, 0x522658, 0});
        put(t + 340, cursor);
        auto mode = virt(get(t + 356), 16);
        bool game = mode == 11;
        if (!game)
            game = virt(get(t + 356), 16) == 3;
        if (!game)
            game = virt(get(t + 356), 16) == 4;
        auto resource = game ? 0x526d90u : 0x526dacu, sequence = game ? 0x526d90u : 0x526d9cu;
        invoke(0x4c7970, get(t + 340), {resource});
        invoke(0x4c79e0, get(t + 340), {sequence, 0});
        auto image = get(get(t + 340) + 372);
        if (image) {
            put(t + 372, uint32_t(signedWord(get(image + 16)) / 2));
            put(t + 376, uint32_t(signedWord(get(image + 20)) / 2));
        }
        put(get(t + 340) + 76, get(t + 372) + get(point));
        put(get(t + 340) + 80, get(point + 4) + get(t + 376));
        put(0x5375bc, t);
        return 1;
    }
    case 0x4399d0: {
        if (get(t + 352)) {
            virt(get(t + 352), 0, {1});
            put(t + 352, 0);
        }
        auto window = get(get(get(t + 4) + 4) + 4), cell = c.automaticToken, copy = cell + 4;
        invoke(0x4f6439, cell);
        uint32_t literal = 0, vt = 0, size = 700;
        switch (a[0]) {
        case 0:
            literal = 0x526f14;
            vt = 0x50d794;
            size = 708;
            break;
        case 1:
            literal = 0x526edc;
            vt = 0x50ce74;
            break;
        case 2:
            literal = 0x526ed0;
            vt = 0x50cc2c;
            break;
        case 3:
            literal = 0x525454;
            vt = 0x50d54c;
            break;
        case 4:
            literal = 0x526ec4;
            vt = 0x50c9e4;
            size = 772;
            break;
        case 5:
            literal = 0x526eec;
            vt = 0x50d0bc;
            break;
        case 6:
            literal = 0x526ef4;
            vt = 0x50d304;
            break;
        case 7:
            literal = 0x526f08;
            size = 724;
            break;
        default:
            break;
        }
        if (literal) {
            auto child = invoke(0x4f63ec, 0, {size});
            if (child) {
                if (a[0] == 7)
                    child = invoke(0x499e70, child, {window, 0});
                else {
                    invoke(0x4236c0, child, {window, 0});
                    if (a[0] == 4) {
                        for (uint32_t off = 724; off <= 768; off += 4)
                            invoke(0x4f6439, child + off);
                    }
                    put(child, vt);
                    if (a[0] == 4)
                        for (uint32_t off = 700; off <= 720; off += 4)
                            put(child + off, 0);
                }
            }
            put(t + 352, child);
            invoke(0x4f66cc, cell, {literal});
        }
        uint32_t result = 0;
        if (get(t + 352)) {
            invoke(0x4f6449, copy, {cell});
            result = virt(get(t + 352), 0x1c8, {t, get(t + 8), get(copy)});
        }
        invoke(0x4f6584, cell);
        return result;
    }
    default:
        fail(3);
    }
}
} // namespace
extern "C" uint32_t claw_player_profile_confirmation_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                           ClawPlayerProfileConfirmationContext *c,
                                                           ClawPlayerProfileConfirmationDependency d, void *u,
                                                           uint32_t *out) {
    if (!c || !out || !owned(f))
        return 0;
    if (n != arity(f) || (n && !a)) {
        c->fault = 3;
        return 0;
    }
    try {
        Run r{*c, d, u};
        *out = r.body(f, t, a);
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
extern "C" uint32_t claw_player_profile_confirmation_construct(uint32_t t, uint32_t data,
                                                               ClawPlayerProfileConfirmationContext *c,
                                                               ClawPlayerProfileConfirmationDependency d, void *u,
                                                               uint32_t *out) {
    if (!c || !out)
        return 0;
    try {
        Run r{*c, d, u};
        *out = r.construct(t, data);
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
extern "C" uint32_t claw_player_profile_confirmation_function(uint32_t vt, uint32_t slot) {
    if (vt != 0x50bf94 || slot % 4 || slot >= 80)
        return 0;
    static const uint32_t methods[] = {0x4299b0, 0x438c40, 0x438e10, 0x40af20, 0x4299a0, 0x438fa0, 0x4390c0,
                                       0x439130, 0x439170, 0x438e90, 0x438f10, 0x439390, 0x4392d0, 0x4393c0,
                                       0x439400, 0x439440, 0x4bb030, 0x4bb030, 0x48fcf0, 0x4bd250};
    return methods[slot / 4];
}
