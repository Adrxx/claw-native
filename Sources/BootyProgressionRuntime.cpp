#include "BootyProgressionRuntime.h"
#include "MovieStateCleanupBridge.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
const uint32_t movieVT[] = {0x40afa0, 0x40b6a0, 0x40b700, 0x40af20, 0x40af90, 0x40b740, 0x40b780,
                            0x40b7a0, 0x40b7c0, 0x40b720, 0x48d320, 0x40af40, 0x40b7d0, 0x40af50,
                            0x40af50, 0x40af50, 0x4bb030, 0x4bb030, 0x48fcf0, 0x4bd250};
const uint32_t resultsVT[] = {0x40b020, 0x40d470, 0x40dc10, 0x40af20, 0x4bd240, 0x40dd50, 0x40de90,
                              0x40df00, 0x40df60, 0x40dca0, 0x40dcb0, 0x40af40, 0x40e020, 0x40af50,
                              0x40af50, 0x40af50, 0x4bb030, 0x4bb030, 0x48fcf0, 0x4bd250};
const uint32_t storyVT[] = {0x40b600, 0x40b860, 0x40bc80, 0x40af20, 0x4bd250, 0x40bd60, 0x40be60,
                            0x40bed0, 0x40df60, 0x40bca0, 0x40bd50, 0x40af40, 0x40bf30, 0x40af50,
                            0x40af50, 0x40af50, 0x4bb030, 0x4bb030, 0x48fcf0, 0x4bd250};
bool owned(uint32_t);
struct Run {
    ClawBootyProgressionContext &c;
    ClawBootyProgressionDependency d;
    void *u;
    uint32_t steps = 0;
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (c.fault)
            throw Failure{};
        auto p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Failure{};
        }
        return p;
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    uint32_t call(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, const char *name = nullptr) {
        if (!d) {
            c.fault = 1;
            throw Failure{};
        }
        if (n > 40) {
            c.fault = 3;
            throw Failure{};
        }
        ClawBootyProgressionCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        std::copy_n(a, n, q.arguments);
        q.name = name;
        return d(&c, &q, u);
    }
    uint32_t invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {});
    uint32_t virt(uint32_t t, uint32_t slot, std::initializer_list<uint32_t> a = {}) {
        if (!t) {
            c.fault = 2;
            throw Failure{};
        }
        auto vt = get(t), f = claw_booty_progression_function(vt, slot);
        if (!f)
            f = get(vt + slot);
        return invoke(f, t, a);
    }
    void post(uint32_t app, uint32_t command) {
        invoke(0x546d50, 0, {get(get(app + 4) + 4), 0x111, command, 0});
    }
    void cleanMovie(uint32_t s) {
        invoke(0x4f0120, s);
        invoke(0x42d4c0, s + 0x8680);
        invoke(0x4efcd0, s + 0x534);
        invoke(0x4f57f8, s + 0x66c);
        invoke(0x4f7369, s + 0x658);
    }
};
uint32_t body(Run &, uint32_t, uint32_t, const uint32_t *);
uint32_t baseDependency(ClawSinglePlayerSceneContext *, ClawSinglePlayerSceneCall e, void *u) {
    auto &r = *static_cast<Run *>(u);
    if (!r.d) {
        r.c.fault = 1;
        throw Failure{};
    }
    ClawBootyProgressionCall q{};
    q.function = e.function;
    q.receiver = e.receiver;
    q.argumentCount = e.argumentCount;
    std::copy_n(e.arguments, 8, q.arguments);
    q.localMask = e.localMask;
    q.bufferCount = e.bufferCount;
    std::copy_n(e.buffers, 3, q.buffers);
    std::copy_n(e.bufferBytes, 3, q.bufferBytes);
    return r.d(&r.c, &q, r.u);
}
uint32_t Run::invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a) {
    if (++steps > (c.maximumSteps ? c.maximumSteps : 65536)) {
        c.fault = 3;
        throw Failure{};
    }
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
    if (c.composeBase && (f == 0x48f0d0 || f == 0x40b5c0)) {
        if (!c.base) {
            c.fault = 1;
            throw Failure{};
        }
        auto b = *c.base;
        b.host = c.scene;
        uint32_t out = 0;
        if (claw_single_player_scene_entry(f, t, args, uint32_t(a.size()), &b, baseDependency, this, &out)) {
            if (b.fault) {
                c.fault = b.fault;
                throw Failure{};
            }
            return out;
        }
    }
    const char *name = nullptr;
    for (auto x : a)
        if (x == 0x523b1c)
            name = "STATES_BOOTY";
        else if (x == 0x523734)
            name = "CLAW";
    return call(f, t, args, uint32_t(a.size()), name);
}
uint32_t body(Run &r, uint32_t f, uint32_t p, const uint32_t *a) {
    switch (f) {
    case 0x40b6a0:
        if (!r.invoke(0x48f0d0, p, {a[0], a[1], a[2]}))
            return 0;
        r.put(p + 32, r.invoke(0x4b7f20, r.get(p + 8), {0x523b1c}));
        if (!r.get(p + 32))
            return 0;
        r.put(p + 36, r.invoke(0x4b7f20, r.get(p + 8), {0x523734}));
        return !!r.get(p + 36);
    case 0x40b720:
        r.invoke(0x42b140, r.get(p + 4), {r.get(p + 20)});
        return 1;
    case 0x40b740:
    case 0x40b7d0:
        if ((f == 0x40b740 || a[0] == 0x1b || a[0] == 0x20 || a[0] == 13) && !r.get(p + 0x154)) {
            r.put(p + 0x154, 1);
            r.post(r.get(p + 4), 0x807c);
        }
        return 1;
    case 0x40b780:
        return !!r.invoke(0x4ca930, r.get(r.get(p + 12) + 4));
    case 0x40b7a0:
        if (!r.virt(p, 12))
            return 0;
        return !!r.get(p + 44);
    case 0x40b7c0:
        return !!r.virt(p, 12);
    case 0x40af20:
        return r.get(p + 52);
    case 0x40af30:
        return 1;
    case 0x40af90:
        return 3;
    case 0x4bd250:
        return 1;
    case 0x4bd240:
        return 2;
    case 0x4ce8b0:
        return 10;
    case 0x40af40:
    case 0x40af50:
    case 0x4bb030:
        return 0;
    case 0x40b700: {
        auto sound = r.get(r.get(r.get(p + 12) + 40) + 44);
        if (sound)
            r.invoke(0x4b4b40, sound);
        r.invoke(0x48f180, p);
        return 0;
    }
    case 0x40afc0:
        r.put(p, 0x50b43c);
        r.invoke(0x40b700, p);
        r.put(p, 0x50b4ec);
        r.invoke(0x48f180, p);
        return 0;
    case 0x40afa0:
        r.invoke(0x40afc0, p);
        if (a[0] & 1)
            r.invoke(0x4f6428, 0, {p});
        return p;
    case 0x48f180:
        if (r.get(p + 12) && r.get(p + 44)) {
            r.invoke(0x4d46f0, r.get(r.get(p + 12) + 24), {r.get(p + 44)});
            r.put(p + 44, 0);
        }
        if (r.get(p + 12)) {
            if (r.get(p + 60)) {
                r.invoke(0x4bc4f0, r.get(r.get(p + 12) + 28), {r.get(p + 60)});
                r.put(p + 60, 0);
            }
            if (r.get(p + 64)) {
                r.invoke(0x4bc4f0, r.get(r.get(p + 12) + 28), {r.get(p + 64)});
                r.put(p + 64, 0);
            }
        }
        r.put(p + 52, 0);
        return 0;
    case 0x4ca930:
        if (r.get(p + 16) && !r.invoke(0x4d56d0, r.get(p + 16)))
            return 0;
        if (r.get(p + 24) && !r.invoke(0x4d4240, r.get(p + 24)))
            return 0;
        return 1;
    case 0x48d320:
        if (r.get(p + 44)) {
            r.invoke(0x4bb990, r.get(r.get(p + 44) + 16), {0, 256, 0, 0, 0, 500});
            for (unsigned i = 0; i < 2; ++i) {
                auto holder = r.get(r.get(p + 12) + 4);
                r.invoke(0x4b97c0, r.get(r.get(holder + 20) + 44), {0});
                r.invoke(0x4b98b0, r.get(r.get(holder + 16) + 44), {0});
            }
        }
        return 1;
    case 0x42b4b0:
        r.invoke(0x4f72c9, p + 0x124);
        r.invoke(0x4f57c5, p + 0x138);
        r.put(p, 0);
        r.put(p + 4, 0);
        r.put(p + 8, 0);
        r.put(p + 0x134, 0);
        r.invoke(0x4a3040, 0, {r.invoke(0x4a3b10, 0, {0})});
        return p;
    case 0x42d4a0:
        r.put(p, 0x50c364);
        r.put(p + 4, 0);
        r.put(p + 16, 0);
        r.put(p + 12, 0);
        r.put(p + 8, 0);
        return 0;
    case 0x42d4c0:
        r.put(p, 0x50c364);
        if (r.get(p + 4))
            r.invoke(0x4f6428, 0, {r.get(p + 4)});
        r.put(p, 0x50becc);
        return 0;
    case 0x42b140: {
        if (!r.invoke(0x48c190, 0, {r.get(p + 0x100)}))
            return 0;
        uint32_t movie = 0;
        if (!r.get(p + 0x9c)) {
            auto index = a[0] + 1;
            if (int32_t(index) < 0 || int32_t(index) > 16)
                return 0;
            movie = r.get(0x525520 + index * 4);
            if (int32_t(movie) < 0)
                return 1;
        } else {
            if (a[0] != 0xfffffffe)
                return 0;
            movie = 1;
        }
        auto s = r.c.scratchToken;
        if (!s) {
            r.c.fault = 1;
            throw Failure{};
        }
        r.span(s, 0x86a8 / 4);
        r.invoke(0x42b4b0, s + 0x534);
        r.invoke(0x42d4a0, s + 0x8680);
        for (auto off : {0u, 4u, 0x10u, 0x14u, 0x18u, 0x1cu, 0xcu, 0x20u, 0x500u, 0x508u, 0x518u, 0x51cu, 0x528u,
                         0x520u, 0x524u, 0x52cu, 0x504u, 0x530u, 0x4fcu})
            r.put(s + off, 0);
        auto scene = r.get(p + 48), holder = r.get(scene + 4), target = r.get(r.get(holder + 16) + 44),
             palette = r.get(r.get(scene + 28)), extra = r.get(scene + 32);
        uint32_t device = extra ? r.get(extra + 20) : 0;
        if (!target || !palette) {
            r.cleanMovie(s);
            return 0;
        }
        uint32_t args[31]{};
        args[0] = r.get(r.get(p + 4) + 4);
        args[1] = palette;
        args[2] = r.get(target + 8);
        std::copy_n(r.span(target + 12, 27), 27, args + 3);
        args[30] = device;
        uint32_t good = r.call(0x4f0000, s, args, 31);
        if (good)
            good = r.invoke(0x4f02e0, s, {r.get(p + 0x100), movie, 0, uint32_t(r.get(p + 0x120) != 0), 0, 0});
        if (good)
            r.invoke(0x4f0380, s, {1, 1, 0});
        r.invoke(0x4f0120, s);
        r.cleanMovie(s);
        return !!good;
    }
    case 0x40b330: {
        auto mode = r.virt(r.get(p + 0x154), 16), old = r.get(p + 0x154);
        if (mode == 2) {
            if (!r.get(p + 0x158)) {
                auto prior = r.invoke(0x42bfd0, r.get(p + 4));
                if (prior && r.virt(prior, 16) == 3) {
                    if (!r.get(prior + 0x258)) {
                        if (!r.get(prior + 0x25c)) {
                            r.post(r.get(p + 4), 0x8036);
                            r.post(r.get(p + 4), 0x8075);
                        } else {
                            r.put(0x537360, 0);
                            r.post(r.get(p + 4), 0x8021);
                        }
                    } else
                        r.post(r.get(p + 4), 0x8023);
                    r.put(p + 0x158, 1);
                    return 1;
                }
                r.put(p + 0x158, 1);
                return 1;
            } // source falls through if already sent
        } else if (mode != 1 && mode != 3)
            return 0;
        if (mode == 1 || mode == 3) {
            auto child = r.invoke(0x4f63ec, 0, {mode == 1 ? 0x184u : 0x16cu});
            if (child) {
                r.invoke(0x40b5c0, child);
                if (mode == 1) {
                    r.invoke(0x4f6439, child + 0x180);
                    r.put(child, 0x50b494);
                    r.put(child + 0x154, 0);
                    r.put(child + 0x158, 0);
                    for (uint32_t off = 0x15c; off < 0x180; off += 4)
                        r.put(child + off, 0);
                } else {
                    r.invoke(0x4f6439, child + 0x15c);
                    r.invoke(0x4f6439, child + 0x168);
                    r.put(child, 0x50b544);
                    for (auto off : {0x154u, 0x158u, 0x160u, 0x164u})
                        r.put(child + off, 0);
                }
            }
            r.put(p + 0x154, child);
        }
        auto oldVT = r.get(old);
        auto nextMode = r.virt(r.get(p + 0x154), 16);
        r.invoke(r.get(oldVT + 40), old, {nextMode});
        if (old)
            r.virt(old, 0, {1});
        r.virt(r.get(p + 0x154), 4, {r.get(p + 4), r.get(p + 20), mode});
        r.virt(r.get(p + 0x154), 36, {mode});
        return 1;
    }
    case 0x426e30:
        if (r.virt(r.get(p + 44), 16) == 10 && !r.invoke(0x40b330, r.get(p + 44)))
            r.invoke(0x429e10, p, {0x8005, 0x6a8});
        return 1;
    default:
        r.c.fault = 3;
        throw Failure{};
    }
}
bool owned(uint32_t f) {
    switch (f) {
    case 0x40b6a0:
    case 0x40b720:
    case 0x40b740:
    case 0x40b780:
    case 0x40b7a0:
    case 0x40b7c0:
    case 0x40b700:
    case 0x40b7d0:
    case 0x40b330:
    case 0x42b140:
    case 0x42b4b0:
    case 0x42d4a0:
    case 0x42d4c0:
    case 0x40af20:
    case 0x40af30:
    case 0x40af40:
    case 0x40af50:
    case 0x40af90:
    case 0x40afa0:
    case 0x40afc0:
    case 0x48f180:
    case 0x4ca930:
    case 0x48d320:
    case 0x4bd240:
    case 0x4bd250:
    case 0x4ce8b0:
    case 0x4bb030:
    case 0x426e30:
        return true;
    default:
        return false;
    }
}
} // namespace
extern "C" uint32_t claw_booty_progression_function(uint32_t vt, uint32_t slot) {
    if (slot % 4 || slot / 4 >= 20)
        return 0;
    return vt == 0x50b43c   ? movieVT[slot / 4]
           : vt == 0x50b494 ? resultsVT[slot / 4]
           : vt == 0x50b544 ? storyVT[slot / 4]
                            : 0;
}
extern "C" uint32_t claw_booty_progression_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                 ClawBootyProgressionContext *c, ClawBootyProgressionDependency d,
                                                 void *u, uint32_t *out) {
    if (!c || !c->globals || !owned(f))
        return 0;
    uint32_t need = f == 0x40b6a0 || f == 0x426e30 || f == 0x40af50                                     ? 3
                    : f == 0x40af40 || f == 0x40b7d0                                                    ? 2
                    : f == 0x40b720 || f == 0x40af30 || f == 0x42b140 || f == 0x40afa0 || f == 0x48d320 ? 1
                                                                                                        : 0;
    if (n != need || (n && !a) || (f == 0x426e30 && (a[0] || a[1] != 0x807c || a[2]))) {
        c->fault = 3;
        return 0;
    }
    if (c->fault)
        return 0;
    uint32_t args[40]{};
    if (n)
        std::copy_n(a, n, args);
    Run r{*c, d, u};
    try {
        auto v = body(r, f, t, args);
        if (out)
            *out = v;
        return !c->fault;
    } catch (Failure &) {
        return 0;
    }
}
