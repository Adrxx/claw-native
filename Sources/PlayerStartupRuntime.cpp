#include "PlayerStartupRuntime.h"
#include "PlayerInitialization.h"
#include "CheckpointLogicRuntime.h"
#include "AmbientAudioBackendRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
#pragma STDC FP_CONTRACT OFF
namespace {
struct Failed {};
struct Run {
    ClawPlayerStartupContext &c;
    ClawPlayerStartupDependency dependency;
    void *user;
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Failed{};
        }
        return p;
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    static int32_t si(uint32_t v) {
        int32_t x;
        std::memcpy(&x, &v, 4);
        return x;
    }
    uint32_t invoke(const ClawPlayerStartupCall &a) {
        if (!dependency) {
            c.fault = 1;
            throw Failed{};
        }
        auto result = dependency(&c, &a, user);
        if (c.fault)
            throw Failed{};
        return result;
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> args = {}) {
        ClawPlayerStartupCall e{};
        e.function = f;
        e.receiver = t;
        e.argumentCount = uint32_t(args.size());
        std::copy(args.begin(), args.end(), e.arguments);
        return invoke(e);
    }
    uint32_t cache(uint32_t t, uint32_t level, uint32_t kind) {
        if (!c.composeCache)
            return call(0x49ae60, t, {level, kind});
        ClawCheckpointGlobals g{};
        ClawCheckpointContext q{};
        q.scene = c.scene;
        q.globals = &g;
        uint32_t args[] = {level, kind}, out = 0;
        if (!claw_checkpoint_entry(0x49ae60, t, args, 2, &q, nullptr, nullptr, &out) || q.fault) {
            c.fault = q.fault ? q.fault : 1;
            throw Failed{};
        }
        return out;
    }
    uint32_t select(uint32_t f, uint32_t t, uint32_t level, uint32_t kind) {
        if (f == 0x49af30) {
            if (si(level) < 1 || kind == 3 || (kind == 0 && level == 1))
                return 0;
            uint32_t rec = cache(t, kind == 0 ? level - 1 : level, kind == 0 ? 3 : kind);
            return rec ? get(rec) & 2 : 0;
        }
        if (si(level) < 0 || level >= 15 || kind == 3 || (kind == 0 && level == 1))
            return 0;
        return cache(t, kind == 0 ? level - 1 : level, kind == 0 ? 3 : kind);
    }
    void clamp(uint32_t t) {
        if (!c.composeCamera) {
            call(0x4d0a60, t);
            return;
        }
        ClawSceneCameraGlobals g{};
        ClawSceneCameraHost h{};
        h.heap = c.scene;
        uint32_t fault = 0, out = 0;
        claw_scene_camera_entry(0x4d0a60, t, 0, 0, &g, h, &fault, &out);
        if (fault) {
            c.fault = fault;
            throw Failed{};
        }
    }
    void position(uint32_t t, uint32_t x, uint32_t y) {
        double a = double(si(x)), b = double(si(y));
        if (!(get(t + 8) & 1)) {
            float sx, sy;
            uint32_t bits = get(t + 0x18);
            std::memcpy(&sx, &bits, 4);
            bits = get(t + 0x1c);
            std::memcpy(&sy, &bits, 4);
            volatile double ax = a * double(sx), by = b * double(sy);
            a = ax;
            b = by;
        }
        float fx = float(a), fy = float(b);
        uint32_t bits;
        std::memcpy(&bits, &fx, 4);
        put(t + 0x10, bits);
        std::memcpy(&bits, &fy, 4);
        put(t + 0x14, bits);
        clamp(t);
    }
    uint32_t pool(uint32_t f, uint32_t t, std::initializer_list<uint32_t> args = {}) {
        ClawAmbientAudioBackendContext q{};
        q.scene = c.scene;
        q.maximumTraversal = c.maximumPlanes;
        uint32_t raw[3]{}, out = 0;
        std::copy(args.begin(), args.end(), raw);
        if (!claw_ambient_audio_backend_entry(f, t, raw, uint32_t(args.size()), &q, nullptr, nullptr, &out) ||
            q.fault) {
            c.fault = q.fault ? q.fault : 1;
            throw Failed{};
        }
        return out;
    }
    uint32_t node(uint32_t list, uint32_t previous, uint32_t next) {
        if (!get(list + 0x10)) {
            uint32_t n = get(list + 0x18);
            if (n > 65536) {
                c.fault = 4;
                throw Failed{};
            }
            uint32_t block = pool(0x4f5aa8, 0, {list + 0x14, n, 12});
            uint32_t at = block - 8 + n * 12;
            if (si(n - 1) >= 0)
                for (uint32_t left = n; left; --left) {
                    put(at, get(list + 0x10));
                    put(list + 0x10, at);
                    at -= 12;
                }
        }
        uint32_t at = get(list + 0x10);
        put(list + 0x10, get(at));
        put(at + 4, previous);
        put(at, next);
        put(list + 0xc, get(list + 0xc) + 1);
        put(at + 8, get(0x52e1cc));
        return at;
    }
    void clear(uint32_t list) {
        uint32_t visits = 0;
        for (uint32_t n = get(list + 4); n;) {
            if (++visits > (c.maximumPlanes ? c.maximumPlanes : 65536)) {
                c.fault = 4;
                throw Failed{};
            }
            call(0x4f6584, n + 8);
            n = get(n);
        }
        put(list + 0xc, 0);
        put(list + 0x10, 0);
        put(list + 8, 0);
        put(list + 4, 0);
        pool(0x4f5ac8, get(list + 0x14));
        put(list + 0x14, 0);
    }
    void local(uint32_t f, uint32_t receiver, uint32_t argument, uint32_t mask, uint32_t &temp) {
        ClawPlayerStartupCall e{};
        e.function = f;
        e.receiver = receiver;
        e.argumentCount = f == 0x4f6584 ? 0 : 1;
        e.arguments[0] = argument;
        e.localMask = mask;
        e.bufferCount = 1;
        e.buffers[0] = &temp;
        e.bufferBytes[0] = 4;
        invoke(e);
    }
    void releaseNode(uint32_t list, uint32_t nodeToken) {
        call(0x4f6584, nodeToken + 8);
        put(nodeToken, get(list + 0x10));
        put(list + 0xc, get(list + 0xc) - 1);
        put(list + 0x10, nodeToken);
        if (!get(list + 0xc))
            clear(list);
    }
    uint32_t removeHead(uint32_t list, uint32_t output) {
        uint32_t nodeToken = get(list + 4), temp = 0;
        local(0x4f6449, 0, nodeToken + 8, 256, temp);
        uint32_t next = get(nodeToken);
        put(list + 4, next);
        if (next)
            put(next + 4, 0);
        else
            put(list + 8, 0);
        releaseNode(list, nodeToken);
        local(0x4f6449, output, 0, 1, temp);
        local(0x4f6584, 0, 0, 256, temp);
        return output;
    }
    uint32_t initializeMessages(uint32_t t, uint32_t duration, uint32_t delay) {
        put(t + 0x24, duration);
        put(t + 0x28, delay);
        put(t + 0x20, 0);
        put(t + 0x2c, 0);
        put(t + 0x30, 0);
        uint32_t fontArguments[14] = {12, 8, 0, 0, 100, 0, 0, 0, 1, 0, 0, 0, 0, 0x5250b0};
        ClawPlayerStartupCall e{};
        e.function = 0x546918;
        e.bufferCount = 1;
        e.buffers[0] = fontArguments;
        e.bufferBytes[0] = 56;
        uint32_t font = invoke(e);
        put(t + 0x34, font);
        if (!font) {
            fontArguments[13] = 0;
            put(t + 0x34, invoke(e));
        }
        return 1;
    }
    uint32_t append(uint32_t list, uint32_t text, bool head) {
        uint32_t n = node(list, head ? 0 : get(list + 8), head ? get(list + 4) : 0);
        call(0x4f66cc, n + 8, {text});
        uint32_t old = get(list + (head ? 4 : 8));
        if (old)
            put(old + (head ? 4 : 0), n);
        else
            put(list + (head ? 8 : 4), n);
        put(list + (head ? 4 : 8), n);
        return n;
    }
    uint32_t message(uint32_t list, uint32_t text, uint32_t flags) {
        if (!text)
            return 0;
        uint32_t word = get(text & ~3u);
        if (!((word >> ((text & 3u) * 8)) & 255))
            return 0;
        if ((flags & 1) && si(get(list + 0xc)) > 7)
            return 0;
        if (flags & 4)
            clear(list);
        append(list, text, (flags & 2) != 0);
        return 1;
    }
    void defaults() {
        ClawPlayerLocomotion s{};
        ClawPlayerInitializationContext j{};
        j.difficulty = get(0x53725c);
        j.accumulatorMinimum = get(0x52c6e4);
        claw_player_construct_defaults(&s, &j);
        std::copy_n(j.defaults, 78, span(0x534c80, 78));
        put(0x53c9f8, j.accumulator);
        put(0x534ea8, j.powerupRemaining);
        put(0x534eac, s.powerup);
        put(0x534eb0, j.powerupAuxiliary);
    }
    uint32_t bind(uint32_t owner) {
        uint32_t app = get(owner + 4);
        if (!get(app + 0xa8))
            return 0;
        uint32_t player = get(app + 0x64);
        if (!player || si(get(owner + 0x14)) < 1)
            return 0;
        uint32_t kind = get(app + 0xd8);
        put(app + 0xa8, 0);
        if (!select(0x49af30, player, get(owner + 0x14), kind))
            return 0;
        uint32_t record = select(0x49af90, player, get(owner + 0x14), kind);
        if (!record)
            return 0;
        put(0x534cc4, get(record + 0x10));
        put(0x534cc8, get(record + 0x94));
        for (uint32_t i = 0; i < 4; ++i)
            put(0x534cf0 + i * 4, get(record + 0x98 + i * 4));
        put(0x534ccc, get(record + 4));
        put(0x534cd0, get(record + 8));
        const bool saved = get(record + 4) != 0 && get(record + 8) != 0;
        uint32_t x = get(0x534ccc), y = get(0x534cd0);
        if (si(x) > 0 && si(y) > 0) {
            put(owner + 0x44, x);
            put(owner + 0x48, get(0x534cd0));
            uint32_t world = get(get(owner + 0xc) + 0x24);
            position(get(world + 0x5c), get(0x534ccc), get(0x534cd0));
            uint32_t main = get(world + 0x5c);
            x = get(main + 0x84);
            y = get(main + 0x88);
            for (uint32_t i = 0; si(i) < si(get(world + 0x3c)); ++i) {
                if (i >= (c.maximumPlanes ? c.maximumPlanes : 65536)) {
                    c.fault = 4;
                    throw Failed{};
                }
                if (i != get(world + 0x60)) {
                    uint32_t p = get(get(world + 0x38) + i * 4);
                    position(p, x, y);
                }
            }
            put(0x536f00, 1);
            put(0x537210, get(record + 0x58));
        }
        put(0x534d6c, uint32_t(si(get(0x534cc4)) / 1000000 + 1) * 1000000u);
        for (uint32_t i = 0; i < 9; ++i) {
            put(0x534d30 + i * 4, get(record + 0x28 + i * 4));
            if (saved)
                put(0x534d08 + i * 4, get(record + 0x6c + i * 4));
        }
        put(owner + 0x160, get(record + 0x10));
        put(owner + 0x164, get(record + 0x14));
        put(0x534ca4, saved ? 1 : 0);
        return 1;
    }
    static uint32_t facade(ClawSinglePlayerSceneContext *q, ClawSinglePlayerSceneCall a, void *p) {
        auto &r = *static_cast<Run *>(p);
        uint32_t value = 0;
        if (a.function == 0x415ce0 || a.function == 0x46c790 || a.function == 0x46d8e0) {
            if (!q->globals) {
                q->fault = 1;
                return 0;
            }
            r.put(0x537210, q->globals->accumulatedTick);
            r.put(0x534ca4, q->globals->word534ca4);
            if (!claw_player_startup_entry(a.function, a.receiver, a.arguments, a.argumentCount, &r.c, r.dependency,
                                           r.user, &value) ||
                r.c.fault)
                q->fault = r.c.fault ? r.c.fault : 1;
            q->globals->accumulatedTick = r.get(0x537210);
            q->globals->word534ca4 = r.get(0x534ca4);
            return value;
        }
        value = r.invoke(a);
        return value;
    }
};
} // namespace
extern "C" void claw_player_startup_defaults(ClawPlayerStartupContext *c) {
    if (c) {
        c->composeCache = c->composeCamera = 1;
        c->maximumPlanes = 65536;
    }
}
extern "C" uint32_t claw_player_startup_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                              ClawPlayerStartupContext *c, ClawPlayerStartupDependency d, void *u,
                                              uint32_t *out) {
    if (f != 0x415ce0 && f != 0x46c790 && f != 0x46d8e0 && f != 0x49af30 && f != 0x49af90 && f != 0x46aeb0 &&
        f != 0x42af70 && f != 0x422370 && f != 0x4f5249 && f != 0x4f5288 && f != 0x4f52f0 && f != 0x4f5382 &&
        f != 0x4f53b7 && f != 0x4222a0 && f != 0x4f5359 && f != 0x4f53eb)
        return 0;
    if (out)
        *out = 0;
    if (!c)
        return 1;
    c->fault = 0;
    uint32_t need =
        (f == 0x49af30 || f == 0x49af90 || f == 0x46aeb0 || f == 0x422370 || f == 0x4f52f0 || f == 0x4222a0)   ? 2
        : (f == 0x42af70 || f == 0x4f5249 || f == 0x4f5382 || f == 0x4f53b7 || f == 0x4f5359 || f == 0x4f53eb) ? 1
                                                                                                               : 0;
    if (n != need || (n && !a)) {
        c->fault = 3;
        return 1;
    }
    Run r{*c, d, u};
    uint32_t value = 0;
    try {
        if (f == 0x415ce0)
            r.defaults();
        else if (f == 0x46c790)
            std::fill_n(r.span(t + 0x160, 60), 60, 0);
        else if (f == 0x46d8e0)
            value = r.bind(t);
        else if (f == 0x49af30 || f == 0x49af90)
            value = r.select(f, t, a[0], a[1]);
        else if (f == 0x42af70) {
            uint32_t config = r.get(t + 0x4c);
            value = config ? r.message(config, a[0], 4) : 0;
        } else if (f == 0x422370)
            value = r.message(t, a[0], a[1]);
        else if (f == 0x4222a0)
            value = r.initializeMessages(t, a[0], a[1]);
        else if (f == 0x4f5359)
            r.releaseNode(t, a[0]);
        else if (f == 0x4f53eb)
            value = r.removeHead(t, a[0]);
        else if (f == 0x4f5288)
            r.clear(t);
        else if (f == 0x4f5382 || f == 0x4f53b7)
            value = r.append(t, a[0], f == 0x4f5382);
        else if (f == 0x4f52f0)
            value = r.node(t, a[0], a[1]);
        else if (f == 0x4f5249) {
            for (uint32_t off : {12u, 16u, 8u, 4u, 20u})
                r.put(t + off, 0);
            r.put(t, 0x510224);
            r.put(t + 24, a[0]);
            value = t;
        } else {
            if (!c->singlePlayer) {
                c->fault = 1;
                throw Failed{};
            }
            claw_single_player_scene_entry(f, t, a, n, c->singlePlayer, Run::facade, &r, &value);
            if (c->singlePlayer->fault)
                c->fault = c->singlePlayer->fault;
        }
    } catch (Failed &) {
    }
    if (out)
        *out = value;
    return 1;
}
