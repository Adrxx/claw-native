#include "PunkRatRuntime.h"
#include "ActorResourceBindings.h"
#include "ActorWrapperRuntime.h"
#include "ActorDestruction.h"
#include "CommonEnemyEntries.h"
#include <algorithm>
#include <cstring>
#include <cmath>
#include <initializer_list>
namespace {
struct Failure {};
int32_t si(uint32_t x) {
    int32_t y;
    std::memcpy(&y, &x, 4);
    return y;
}
uint32_t ftol(double v) {
    uint64_t b;
    std::memcpy(&b, &v, 8);
    int e = int((b >> 52) & 2047) - 1023;
    if (e < 0 || e >= 63)
        return 0;
    uint64_t m = (b & 0xfffffffffffffULL) | 0x10000000000000ULL;
    m = e >= 52 ? m << (e - 52) : m >> (52 - e);
    return b >> 63 ? 0u - uint32_t(m) : uint32_t(m);
}
const char *name(uint32_t t) {
    switch (t) {
    case 0x52a784:
        return "LEVEL_PUNKRAT";
    case 0x52a770:
        return "LEVEL_PUNKRAT_WALK";
    case 0x52a75c:
        return "LEVEL_PUNKRAT_IDLE";
    case 0x52a748:
        return "LEVEL_PUNKRAT_STAND";
    case 0x52a730:
        return "LEVEL_PUNKRAT_STRIKE";
    case 0x52a71c:
        return "LEVEL_PUNKRAT_HOME";
    case 0x52a704:
        return "LEVEL_PUNKRAT_RECOIL";
    case 0x52a6f8:
        return "GAME_EEHH";
    case 0x52a6e8:
        return "GAME_MOUSEKILL";
    case 0x5234b4:
        return "GAME_NULL";
    case 0x522d0c:
        return "GroundCannon";
    case 0x52a794:
        return "LS_RECOIL";
    case 0x524548:
        return "LS_FIRING";
    case 0x524538:
        return "LS_VERTFIRING";
    default:
        return nullptr;
    }
}
bool own(uint32_t f) {
    switch (f) {
    case 0x474330:
    case 0x4743f0:
    case 0x4746f0:
    case 0x474710:
    case 0x4747e0:
    case 0x474bc0:
    case 0x474c50:
    case 0x474d00:
    case 0x474db0:
    case 0x474e10:
    case 0x474e60:
    case 0x474ec0:
    case 0x414640:
    case 0x414660:
    case 0x414860:
    case 0x414a60:
        return true;
    default:
        return false;
    }
}
bool shared(uint32_t f) {
    switch (f) {
    case 0x404dd0:
    case 0x404eb0:
    case 0x43e9e0:
    case 0x440e20:
    case 0x43ed70:
    case 0x43efe0:
    case 0x43f030:
    case 0x43f640:
    case 0x43f740:
    case 0x43fa10:
    case 0x43fe00:
    case 0x43fe60:
    case 0x43ffa0:
    case 0x404e00:
    case 0x43f500:
    case 0x440b20:
    case 0x440c90:
    case 0x43f540:
    case 0x43f6e0:
    case 0x4dc830:
    case 0x4dc850:
    case 0x43f720:
    case 0x4332f0:
    case 0x404fc0:
    case 0x4063b0:
    case 0x43dfa0:
    case 0x43e420:
    case 0x43d490:
    case 0x43fd10:
    case 0x43fdc0:
    case 0x43edd0:
    case 0x43fcb0:
    case 0x43fd60:
    case 0x4dca10:
    case 0x4dc870:
    case 0x43e9b0:
    case 0x43f120:
    case 0x43f450:
    case 0x404ed0:
    case 0x404f00:
    case 0x4c9e30:
    case 0x4c96b0:
    case 0x4bb030:
        return true;
    default:
        return false;
    }
}
struct Run {
    ClawPunkRatContext &c;
    ClawPunkRatDependency d;
    void *u;
    uint32_t depth = 0;
    [[noreturn]] void fail(uint32_t n = 1) {
        if (!c.fault)
            c.fault = n;
        throw Failure{};
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (c.fault)
            throw Failure{};
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
    double real(uint32_t t) {
        double v;
        std::memcpy(&v, span(t, 2), 8);
        return v;
    }
    void real(uint32_t t, double v) {
        std::memcpy(span(t, 2), &v, 8);
    }
    uint32_t invoke(uint32_t, uint32_t, std::initializer_list<uint32_t> = {});
    uint64_t emit(const ClawPunkRatCall &e) {
        if (!d)
            fail();
        auto v = d(&c, &e, u);
        if (c.fault)
            throw Failure{};
        return v;
    }
    uint64_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawPunkRatCall e{};
        e.function = f;
        e.receiver = t;
        e.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), e.arguments);
        for (auto x : a)
            if (name(x)) {
                e.name = name(x);
                break;
            }
        return emit(e);
    }
    uint32_t virt(uint32_t t, uint32_t off) {
        return invoke(get(get(t) + off), t);
    }
    uint32_t virt(uint32_t t, uint32_t off, uint32_t a) {
        return invoke(get(get(t) + off), t, {a});
    }
    static uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
        return static_cast<Run *>(u)->span(t, n);
    }
    static uint32_t hostCall(void *u, ClawSceneActorCall e) {
        auto &r = *static_cast<Run *>(u);
        switch (e.argumentCount) {
        case 0:
            return r.invoke(e.function, e.receiver);
        case 1:
            return r.invoke(e.function, e.receiver, {e.arguments[0]});
        case 2:
            return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1]});
        case 3:
            return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2]});
        default:
            return r.invoke(e.function, e.receiver, {e.arguments[0], e.arguments[1], e.arguments[2], e.arguments[3]});
        }
    }
    static void release(void *u, uint32_t t) {
        auto &r = *static_cast<Run *>(u);
        if (r.c.scene.free)
            r.c.scene.free(r.c.scene.context, t);
        else
            r.call(0x4f6428, 0, {t});
    }
    ClawSceneActorHost host() {
        return {this, lookup, nullptr, release, hostCall, nullptr};
    }
    void transfer(ClawGenericEnemy &s, uint32_t t, bool exporting, uint32_t initialActor = 0) {
        uint32_t actor = exporting ? s.enemy[3] : (initialActor ? initialActor : get(t + 12)),
                 primary = get(actor + 108), secondary = get(actor + 112), contact = get(actor + 120);
        auto copy = [&](uint32_t token, uint32_t *p, uint32_t n) {
            if (token) {
                auto *q = span(token, n);
                if (exporting)
                    std::copy_n(p, n, q);
                else
                    std::copy_n(q, n, p);
            }
        };
        copy(actor, s.actor, 128);
        copy(primary, s.primary, 93);
        copy(secondary, s.secondary, 93);
        copy(contact, s.contact, 93);
        copy(t, s.enemy, 260);
    }
    struct Model {
        Run &r;
        uint32_t receiver;
    };
    static uint64_t dependency(ClawGenericEnemy *s, ClawGenericEnemyContext *, const ClawGenericEnemyCall *e, void *u) {
        auto &k = *static_cast<Model *>(u);
        auto &r = k.r;
        r.transfer(*s, k.receiver, true);
        uint64_t v = 0;
        if ((own(e->function) || shared(e->function)) && e->argumentCount <= 1) {
            v = e->argumentCount ? r.invoke(e->function, e->receiver, {e->arguments[0]})
                                 : r.invoke(e->function, e->receiver);
        } else if (r.c.composeAnimation &&
                   (e->function == 0x4c8220 || e->function == 0x4c82a0 || e->function == 0x420a10)) {
            v = e->argumentCount == 2 ? r.invoke(e->function, e->receiver, {e->arguments[0], e->arguments[1]})
                                      : r.invoke(e->function, e->receiver, {e->arguments[0]});
        } else {
            ClawPunkRatCall q{};
            q.function = e->function;
            q.receiver = e->receiver;
            q.argumentCount = e->argumentCount;
            std::copy_n(e->arguments, 12, q.arguments);
            q.name = e->name;
            v = r.emit(q);
        }
        r.transfer(*s, k.receiver, false);
        r.c.generic->tick = r.c.globals->tick;
        r.c.generic->animationDelta = r.c.globals->animationDelta;
        return v;
    }
    uint32_t common(uint32_t f, uint32_t t, uint32_t a) {
        if (!c.generic)
            fail();
        ClawGenericEnemy s{};
        transfer(s, t, false, f == 0x4332f0 ? a : 0);
        auto *g = c.generic;
        g->enemyToken = t;
        g->actorToken = f == 0x4332f0 ? a : get(t + 12);
        g->primaryToken = get(g->actorToken + 108);
        g->secondaryToken = get(g->actorToken + 112);
        g->contactToken = get(g->actorToken + 120);
        g->sceneToken = get(g->actorToken + 12);
        g->tileManagerToken = get(g->sceneToken + 36);
        g->soundRegistryToken = get(g->sceneToken + 40) + 16;
        g->tick = c.globals->tick;
        g->animationDelta = c.globals->animationDelta;
        g->levelWord = c.globals->powerup;
        g->forcedRandom = c.globals->randomDisabled;
        if (c.sharedStates) {
            c.sharedStates->audioEnabled = c.globals->audioEnabled;
            c.sharedStates->audioPosition = c.globals->masterVolume;
        }
        std::copy_n(span(get(t), 43), 43, g->virtualFunctions);
        Model k{*this, t};
        uint32_t supported = 0;
        if (f == 0x43d490) {
            if (si(a) < si(get(0x537640)) || si(a) > si(get(0x537644)))
                fail(3);
            put(0x537658, 0);
        }
        if (f == 0x4332f0)
            supported = claw_generic_enemy_construct(&s, g, dependency, &k);
        else if (f == 0x4dc870) {
            uint32_t id = s.primary[7], lo = get(0x5376a0), hi = get(0x5376a4);
            if (si(id) < si(lo) || si(id) > si(hi))
                fail(3);
            uint32_t chars = get(get(0x5376a8) + (id - lo) * 4);
            if (si(get(chars - 12)) > 1 || si(get(chars - 4)) < 0)
                fail(3);
            put(0x5376b8, 0);
            supported = claw_generic_enemy_tick(&s, g, dependency, &k);
        } else {
            if (c.sharedStates)
                supported = claw_generic_enemy_state_entry(&s, g, c.sharedStates, f, a, dependency, &k);
            if (!supported)
                supported = claw_generic_enemy_entry(&s, g, f, a, dependency, &k);
            if (!supported && c.sharedStates) {
                uint32_t tail[20]{};
                ClawHumanEnemyContext human{};
                human.generic = g;
                human.sharedStates = c.sharedStates;
                human.privateTail = tail;
                uint32_t result = 0;
                supported = claw_common_enemy_entry(&s, &human, f, a, dependency, &k, &result);
                if (human.fault)
                    fail(2);
            }
        }
        transfer(s, t, true);
        if (!supported)
            fail(2);
        return f == 0x4332f0 ? t : f == 0x4dc870 ? 1 : 0;
    }
    void image(uint32_t actor, uint32_t literal) {
        if (!c.composeImages) {
            call(0x4c7970, actor, {literal});
            return;
        }
        uint32_t root = uint32_t(call(0x4f6286, get(get(actor + 12) + 16) + 16, {literal}));
        ClawActorBindingContext b{};
        b.image.token = root;
        uint32_t leaf = 0;
        if (root) {
            b.image.minimum = si(get(root + 100));
            b.image.maximum = si(get(root + 104));
            b.image.firstImageIndex = b.image.minimum;
            if (b.image.minimum <= b.image.maximum)
                leaf = get(get(root + 20) + uint32_t(b.image.minimum) * 4);
            b.image.images = &leaf;
            b.image.imageCount = 1;
        }
        ClawActorResourceBindings s{};
        std::copy_n(span(actor, 128), 128, s.actor);
        if (!claw_actor_bind_default_image(
                &s, &b, name(literal),
                [](ClawActorResourceBindings *, ClawActorBindingContext *b, const ClawActorBindingCall *, void *) {
                    return b->image.token;
                },
                nullptr))
            fail(2);
        std::copy_n(s.actor, 128, span(actor, 128));
    }
};
uint32_t body(Run &r, uint32_t f, uint32_t t, const uint32_t *a) {
    if (f == 0x474330) {
        uint32_t actor = a[0], primary = r.get(actor + 108), state = r.get(primary + 28);
        if (!state) {
            r.put(primary + 28, 1000);
            uint32_t object = r.invoke(0x4f63ec, 0, {0x410});
            if (object)
                object = r.invoke(0x4743f0, object, {actor});
            if (!object)
                r.fail(2);
            r.virt(object, 16);
            r.put(primary + 24, object);
        } else if (state == 29 || state == 30)
            r.virt(r.get(primary + 24), state == 29 ? 32 : 28);
        else if (state != 1000)
            r.invoke(0x4dc870, r.get(primary + 24));
        return 1;
    }
    if (f == 0x4743f0) {
        r.invoke(0x4332f0, t, {a[0]});
        r.put(t, 0x50eee4);
        r.invoke(0x4c7970, r.get(t + 300), {0x52a784});
        if (!r.get(t + 0x2e4))
            r.put(t + 0x2e4, 10);
        uint32_t actor = r.get(t + 12);
        if (!r.get(actor + 0x148))
            r.put(actor + 0x148, 500);
        volatile double lo = r.real(t + 0x68) - r.real(0x50eec8), hi = r.real(t + 0x68) - r.real(0x50eed0);
        r.real(t + 0x80, lo);
        r.real(t + 0x98, hi);
        r.put(actor + 0x10c, 2);
        actor = r.get(t + 12);
        volatile double scaled = double(si(r.get(actor + 0x10c))) * double(r.c.globals->healthScale);
        r.put(actor + 0x10c, ftol(scaled));
        r.real(t + 0x40, 0);
        r.real(t + 0x50, 60);
        const uint32_t targets[] = {0x354, 0x350, 0x314, 0x310, 0x344, 0x400},
                       literals[] = {0x52a770, 0x52a75c, 0x52a748, 0x52a730, 0x52a71c, 0x52a704};
        for (unsigned i = 0; i < 6; ++i) {
            uint32_t value = i == 0 ? r.invoke(0x4061b0, r.get(r.get(r.get(t + 300) + 12) + 44), {literals[i]})
                                    : r.invoke(0x4062e0, t + 0x128, {literals[i]});
            if (!value)
                value = r.invoke(0x4062e0, t + 0x128, {0x5234b4});
            r.put(t + targets[i], value);
        }
        for (auto pair : {std::pair<uint32_t, uint32_t>{0x404, 0x52a6f8}, {0x3a4, 0x52a6e8}})
            r.put(t + pair.first, r.invoke(0x4f6286, r.get(r.get(r.get(t + 300) + 12) + 40) + 16, {pair.second}));
        r.invoke(0x43fd60, t, {60});
        r.put(r.get(t + 12) + 204, 2);
        r.put(t + 0x134, r.get(r.get(t + 300) + 400));
        r.invoke(0x4c8220, r.get(t + 300) + 392, {r.get(t + 0x314)});
        r.invoke(0x4c82a0, r.get(t + 300) + 392, {r.c.globals->animationDelta});
        if (r.get(t + 0x2fc) < 2)
            r.invoke(0x4dbd20, t + 0x2f4, {1});
        else {
            uint32_t bits = r.get(t + 0x2fc) < 33 ? t + 0x300 : r.get(t + 0x300);
            r.put(bits, r.get(bits) | 2);
        }
        actor = r.get(t + 300);
        r.put(actor + 8, r.get(actor + 8) | 0x40);
        r.put(actor + 0xd0, 4);
        r.put(actor + 0xd4, 0x3000032);
        const uint32_t move[] = {uint32_t(-20), uint32_t(-40), 20, 40}, hit[] = {uint32_t(-40), uint32_t(-40), 40, 40};
        std::copy_n(move, 4, r.span(r.get(t + 300) + 0x128, 4));
        std::copy_n(hit, 4, r.span(r.get(t + 300) + 0x118, 4));
        return t;
    }
    if (f == 0x4746f0) {
        r.invoke(0x474710, t);
        if (a[0] & 1)
            Run::release(&r, t);
        return t;
    }
    if (f == 0x474710) {
        r.put(t, 0x50b16c);
        r.invoke(0x4dbcd0, t + 0x2f4);
        r.invoke(0x4f6584, t + 0x1a8);
        r.invoke(0x4f6584, t + 0x1a4);
        r.put(t, 0x50b014);
        return 0;
    }
    if (f == 0x4747e0) {
        auto select = [&]() {
            uint32_t table = 0x538458, state = a[0];
            r.put(table + 32, 0);
            uint32_t cell;
            if (si(state) < si(r.get(table + 8)) || si(state) > si(r.get(table + 12))) {
                if (!r.invoke(0x4db6e0, table, {state, 0})) {
                    uint32_t text = r.get(0x544b4c);
                    r.put(0x544b14, r.invoke(0x4db5f0, 0));
                    r.invoke(0x4db4d0, r.get(table + 4), {table, text, 12});
                    cell = r.get(table + 20);
                } else
                    cell = r.get(table + 16) + (state - r.get(table + 8)) * r.get(table + 24);
            } else
                cell = r.get(table + 16) + (state - r.get(table + 8)) * r.get(table + 24);
            return r.get(cell);
        };
        if (select())
            r.invoke(select(), t);
        else
            r.invoke(0x43d490, t, {a[0]});
        return 0;
    }
    if (f == 0x474bc0) {
        uint32_t actor = r.get(t + 12);
        if (r.get(actor + 100) != 0xed8) {
            r.put(actor + 100, 0xed8);
            r.put(actor + 8, r.get(actor + 8) | 0x20000);
        }
        actor = r.get(t + 300);
        uint32_t child = r.invoke(0x4c8da0, r.get(r.get(r.get(t + 0x130) + 12) + 8),
                                  {0, r.get(actor + 76) + ((r.get(actor + 64) & 2) ? uint32_t(-20) : 0),
                                   r.get(actor + 80) + 15, r.get(actor + 100) - 1, 0x522d0c, 0x40000});
        r.put(t + 0x408, child);
        uint32_t primary = r.get(child + 108);
        r.invoke(r.get(primary + 16), 0, {child});
        if (r.get(r.get(t + 300) + 64) & 2)
            r.invoke(0x414a60, r.get(r.get(r.get(t + 0x408) + 108) + 24));
        return 0;
    }
    if (f == 0x474c50 || f == 0x474d00) {
        r.invoke(0x4c82a0, r.get(t + 300) + 392, {r.c.globals->animationDelta});
        bool speak = !r.c.globals->randomDisabled && si(r.invoke(0x4a3050, 0)) % 100 < 10;
        uint32_t sound = r.get(t + 0x404);
        if (speak && sound && r.c.globals->audioEnabled)
            r.invoke(0x4b45f0, r.get(sound + 16), {r.c.globals->masterVolume, 0, 0, 0});
        double position = r.real(t + 0x68), bound = r.real(t + (f == 0x474c50 ? 0x80 : 0x98));
        if (position == bound || std::isnan(position) || std::isnan(bound)) {
            bool mirrored = (r.get(r.get(t + 300) + 64) & 2) != 0;
            if ((f == 0x474c50 ? !mirrored : mirrored) && r.c.globals->powerup != 0x26b7)
                r.virt(t, 0x58);
            else
                r.virt(t, f == 0x474c50 ? 0x70 : 0x6c, 60);
        }
        return 0;
    }
    if (f == 0x474db0) {
        r.invoke(0x4c82a0, r.get(t + 300) + 392, {r.c.globals->animationDelta});
        uint32_t actor = r.get(t + 300);
        if (r.get(actor + 420) && !r.get(actor + 412)) {
            r.invoke(0x414640, r.get(r.get(r.get(t + 0x408) + 108) + 24));
            r.virt(t, 0xa8);
        }
        return 0;
    }
    if (f == 0x474e10) {
        r.put(t + 0x134, r.get(r.get(t + 300) + 400));
        r.invoke(0x4c8220, r.get(t + 300) + 392, {r.get(t + 0x400)});
        r.put(t + 36, r.get(r.get(t + 16) + 28));
        r.put(r.get(t + 16) + 28, r.invoke(0x4dba00, 0x537668, {0x52a794}));
        return 0;
    }
    if (f == 0x474e60) {
        r.invoke(0x4c82a0, r.get(t + 300) + 392, {r.c.globals->animationDelta});
        uint32_t actor = r.get(t + 300);
        if (r.get(actor + 420) && !r.get(actor + 412))
            r.virt(t, (r.get(actor + 64) & 2) ? 0x6c : 0x70, 60);
        return 0;
    }
    if (f == 0x474ec0) {
        r.virt(t, 0x5c, 0);
        return 0;
    }
    if (f == 0x414640)
        return r.invoke(r.get(t + 112) ? 0x414860 : 0x414660, t);
    if (f == 0x414660 || f == 0x414860) {
        r.put(t + 36, r.get(r.get(t + 16) + 28));
        r.put(r.get(t + 16) + 28, r.invoke(0x4dba00, 0x537668, {f == 0x414660 ? 0x524548u : 0x524538u}));
        r.put(t + 52, r.get(r.get(t + 44) + 400));
        r.invoke(0x4c8220, r.get(t + 44) + 392, {r.get(t + (f == 0x414660 ? 76 : 80))});
        r.put(t + 88, 0);
        return 0;
    }
    if (f == 0x414a60) {
        uint32_t actor = r.get(t + 44);
        if (!(r.get(actor + 64) & 2)) {
            uint32_t old = r.get(t + 56);
            r.put(t + 56, 0u - r.get(t + 64));
            r.put(t + 64, 0u - old);
            r.put(actor + 64, r.get(actor + 64) | 2);
            actor = r.get(t + 44);
            for (uint32_t offset : {0x118u, 0x128u, 0x138u}) {
                old = r.get(actor + offset);
                if (old != 0x80000000) {
                    r.put(actor + offset, 0u - r.get(actor + offset + 8));
                    r.put(actor + offset + 8, 0u - old);
                }
            }
        }
        actor = r.get(t + 12);
        if (si(r.get(actor + 0x148)) > 0) {
            r.put(r.get(t + 12) + 0x148, 0u - r.get(r.get(t + 12) + 0x148));
            r.put(t + 92, 0u - r.get(t + 92));
            r.put(t + 100, 0u - r.get(t + 100));
        }
        return 0;
    }
    r.fail(3);
}
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a) {
    if (++depth > 64)
        fail(3);
    uint32_t args[12]{};
    std::copy(a.begin(), a.end(), args);
    uint32_t v = 0;
    if (own(f))
        v = body(*this, f, t, args);
    else if (f == 0x4c7970)
        image(t, args[0]);
    else if (f == 0x4061b0 || f == 0x4062e0) {
        ClawActorWrapperContext x{host(), 0};
        if (!claw_actor_wrapper_entry(f, t, args, uint32_t(a.size()), &x, nullptr, nullptr, &v) || x.fault)
            fail(2);
    } else if (c.composeAnimation && (f == 0x4c8220 || f == 0x4c82a0 || f == 0x420a10)) {
        ClawActorAnimationGlobals g{c.globals->animationDelta, c.globals->masterVolume};
        uint32_t fault = 0;
        if (!claw_actor_animation_entry(f, t, args[0], args[1], &g, host(), &fault, &v) || fault)
            fail(2);
    } else if (f == 0x4dbcd0 || f == 0x4f6584) {
        ClawActorDestructionGlobals g{0, 0, c.generic ? c.generic->emptyStringToken : 0x52e1c4};
        uint32_t fault = 0;
        if (!claw_actor_destruction_entry(f, t, 0, &g, host(), &fault, &v) || fault)
            fail(2);
    } else if (shared(f)) {
        if (f == 0x4c96b0)
            v = 0;
        else
            v = common(f, t, args[0]);
    } else
        v = uint32_t(call(f, t, a));
    --depth;
    return v;
}
} // namespace
extern "C" uint32_t claw_punk_rat_private_bytes() {
    return 0x410;
}
extern "C" uint32_t claw_punk_rat_function(uint32_t vt, uint32_t slot) {
    if (vt != 0x50eee4 || slot % 4 || slot >= 172)
        return 0;
    static const uint32_t functions[] = {
        0x4746f0, 0x404fc0, 0x4747e0, 0x4063b0, 0x474bc0, 0x474ec0, 0x4bb030, 0x4c96b0, 0x43e9b0, 0x43dfa0, 0x404dd0,
        0x404eb0, 0x404eb0, 0x404eb0, 0x404eb0, 0x404eb0, 0x4c9e30, 0x404ed0, 0x404f00, 0x43ed70, 0x43eee0, 0x43ee10,
        0x43efe0, 0x43f120, 0x43f640, 0x43f740, 0x43fa10, 0x43fcb0, 0x43fd60, 0x43fe00, 0x43fe60, 0x43ffa0, 0x404e00,
        0x440120, 0x440420, 0x4407d0, 0x43f500, 0x4409d0, 0x440b20, 0x440c90, 0x440410, 0x4bb030, 0x474e10};
    return functions[slot / 4];
}
extern "C" uint32_t claw_punk_rat_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, ClawPunkRatContext *c,
                                        ClawPunkRatDependency d, void *u, uint32_t *out) {
    if (!own(f) && !shared(f))
        return 0;
    if (!c || !c->globals)
        return 0;
    uint32_t expected = f == 0x474330 || f == 0x4743f0 || f == 0x4746f0 || f == 0x4747e0 || f == 0x4332f0 ||
                                f == 0x4dc870 || f == 0x404fc0 || f == 0x4063b0 || f == 0x43d490 || f == 0x43fcb0 ||
                                f == 0x43fd60 || f == 0x43f120 || f == 0x404dd0 || f == 0x404eb0 || f == 0x440e20 ||
                                f == 0x404e00 || f == 0x43f500 || f == 0x4c9e30
                            ? 1
                            : 0;
    if (n != expected || (n && !a)) {
        c->fault = 3;
        return 0;
    }
    if (c->fault)
        return 0;
    Run r{*c, d, u};
    try {
        uint32_t value;
        if (f == 0x4dc870)
            value = r.invoke(f, a[0]);
        else if (n)
            value = r.invoke(f, t, {a[0]});
        else
            value = r.invoke(f, t);
        if (out)
            *out = value;
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
