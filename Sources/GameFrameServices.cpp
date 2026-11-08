#include "GameFrameServices.h"
#include <initializer_list>
#include <cstring>
namespace {
struct Missing {};
struct Runtime {
    ClawGameFrameServiceContext &c;
    ClawGameFrameServiceDependency dependency;
    void *user;
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        auto p = c.host.lookup ? c.host.lookup(c.host.context, t, n) : nullptr;
        if (!p) {
            c.fault = 1;
            throw Missing{};
        }
        return p;
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    uint32_t vt(uint32_t t, uint32_t off) {
        return get(get(t) + off);
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}, uint32_t mask = 0,
                  std::initializer_list<void *> b = {}, std::initializer_list<uint32_t> sizes = {}) {
        if (f == 0x40af90)
            return 3;
        if (f == 0x4750d0)
            return 4;
        if (f == 0x4bb030)
            return 0;
        if (f == 0x4750e0)
            return get(get(t + 0x780) + 0x60);
        if (f == 0x46ca50) {
            messageDraw(t, a.size() ? *a.begin() : 0);
            return 0;
        }
        ClawGameFrameServiceCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = static_cast<uint32_t>(a.size());
        uint32_t i = 0;
        for (auto v : a)
            q.arguments[i++] = v;
        q.localMask = mask;
        i = 0;
        for (auto v : b)
            q.buffers[i++] = v;
        q.bufferCount = i;
        i = 0;
        for (auto v : sizes)
            q.bufferBytes[i++] = v;
        if (dependency)
            return dependency(&c, q, user);
        if (mask || q.argumentCount > 4) {
            c.fault = 3;
            throw Missing{};
        }
        if (c.host.call) {
            ClawSceneActorCall s{};
            s.function = f;
            s.receiver = t;
            s.argumentCount = q.argumentCount;
            for (i = 0; i < q.argumentCount; ++i)
                s.arguments[i] = q.arguments[i];
            return c.host.call(c.host.context, s);
        }
        c.fault = 3;
        throw Missing{};
    }
    void messages(uint32_t t, uint32_t delta) {
        if (get(t + 0x30)) {
            uint32_t v = get(t + 0x2c) + delta;
            put(t + 0x2c, v);
            if (v > 10000) {
                put(t + 0x30, 0);
                call(0x4f650f, t + 0x1c);
            }
        }
        uint32_t count = get(t + 0xc);
        if (!count)
            put(t + 0x20, 0);
        uint32_t timer = get(t + 0x20) + delta;
        put(t + 0x20, timer);
        if ((static_cast<int32_t>(count) > 3 && timer >= get(t + 0x28)) ||
            (static_cast<int32_t>(count) <= 3 && timer >= get(t + 0x24) && count)) {
            uint32_t temp = 0;
            call(0x4f53eb, t, {0}, 1, {&temp}, {4});
            call(0x4f6584, 0, {}, 256, {&temp}, {4});
            put(t + 0x20, 0);
        }
    }
    void messageDraw(uint32_t t, uint32_t hdc) {
        uint32_t config = get(get(t + 4) + 0x4c);
        if (c.composeMessages)
            messages(config, c.globals->stageDelta);
        else
            call(0x4224f0, config, {c.globals->stageDelta});
        auto &g = *c.globals;
        uint32_t rect[4] = {g.overlayRect[0], g.overlayRect[1] + 110, g.overlayRect[2], g.overlayRect[1] + 174};
        config = get(get(t + 4) + 0x4c);
        call(0x4226b0, config, {1, hdc, 0, 1}, 4, {rect}, {16});
    }
    void pose(uint32_t t) {
        auto &g = *c.globals;
        uint32_t v = get(t + 0xbf4);
        put(t + 0xbf4, g.stageDelta < v ? v - g.stageDelta : 0);
        if (get(t + 0xbf4))
            return;
        put(t + 0xbf4, get(t + 0xc00) * (get(get(t + 0x780) + 0x60) - 1) + get(t + 0xbfc));
        uint32_t p = g.playerToken;
        g.posePacket[0] = 1001;
        g.posePacket[1] = get(p + 0x4c);
        g.posePacket[2] = get(p + 0x50);
        g.posePacket[3] = get(p + 0xf8);
        g.posePacket[4] = get(get(get(p + 0x6c) + 0x14)) == 0;
        if (std::memcmp(g.lastPose, g.posePacket + 1, 16) == 0) {
            v = get(t + 0xbf8);
            put(t + 0xbf8, g.stageDelta < v ? v - g.stageDelta : 0);
            if (get(t + 0xbf8))
                return;
        } else
            std::memcpy(g.lastPose, g.posePacket + 1, 16);
        put(t + 0xbf8, 10000);
        v = get(t + 0xc04);
        if (!v)
            call(0x4e0d70, get(t + 0x780), {get(t + 0x784), 0, 0x53abc0, 20}, 0, {g.posePacket}, {20});
        else if (v != get(t + 0x784))
            call(0x477790, t, {v, 0x53abc0, 0}, 0, {g.posePacket}, {20});
    }
    uint32_t poll(uint32_t t) {
        auto &g = *c.globals;
        uint32_t pending = 0, peer = get(t + 0x784);
        if (peer) {
            uint32_t n = get(get(t + 0x780) + 0x18);
            uint32_t result = call(vt(n, 0x44), 0, {n, get(peer + 4), 0}, 4, {&pending}, {4});
            if (result)
                pending = 0;
        }
        put(t + 0x14c, pending);
        if (static_cast<int32_t>(pending) < 1) {
            if (get(t + 0x7ac) && static_cast<int32_t>(call(vt(t, 0x50), t)) > 1) {
                uint32_t v = get(t + 0xbf0);
                put(t + 0xbf0, g.stageDelta < v ? v - g.stageDelta : 0);
                if (!get(t + 0xbf0)) {
                    put(t + 0xbf0, 60000);
                    call(0x422370, get(get(t + 4) + 0x4c), {0x52a9d4, 2});
                    uint32_t sound = get(get(t + 0xc) + 0x28);
                    if (!get(sound + 0x30)) {
                        uint32_t resource = 0;
                        call(0x4f6286, sound + 0x10, {0x52a824, 0}, 2, {&resource}, {4});
                        if (resource && g.audioEnabled)
                            call(0x4b45f0, get(resource + 0x10), {g.overallVolume, 0, 0, 0});
                    }
                }
            }
            return 0;
        }
        put(t + 0xbf0, 60000);
        peer = get(t + 0x784);
        uint32_t buffer = get(peer + 0x18);
        if (!buffer)
            return 0;
        uint32_t processed = 0, from = 0;
        while (static_cast<int32_t>(pending) > 0) {
            peer = get(t + 0x784);
            uint32_t length = get(peer + 0x1c), to = get(peer + 4), n = get(get(t + 0x780) + 0x18);
            uint32_t error = call(vt(n, 0x64), 0, {n, 0, 0, 1, buffer, 0}, 38, {&from, &to, &length}, {4, 4, 4});
            if (error) {
                call(0x4e10d0, 0, {0x52a9bc, 0x12e, error, 0});
                break;
            }
            --pending;
            ++processed;
            if (from != get(get(t + 0x784) + 4))
                call(0x477a10, t, {from, buffer, length});
        }
        return processed;
    }
    uint32_t actorOf(uint32_t item) {
        return get(get(item + 0x14));
    }
    void ranks(uint32_t t, uint32_t force) {
        auto &g = *c.globals;
        if (!get(t + 0x7ac))
            return;
        if (!force && !get(t + 0x794)) {
            if (g.stageDelta < g.rankingTimer) {
                g.rankingTimer -= g.stageDelta;
                return;
            }
            g.rankingTimer = 500;
        }
        if (get(t + 0x794)) {
            uint32_t n = get(t + 0x780), node = get(n + 0x58), count = 0;
            put(n + 0x84, node);
            uint32_t item = 0;
            if (node) {
                put(n + 0x84, get(node));
                item = get(node + 8);
            }
            while (item) {
                put(t + 0x7c0 + 4 * count, item);
                ++count;
                n = get(t + 0x780);
                node = get(n + 0x84);
                if (node) {
                    item = get(node + 8);
                    put(n + 0x84, get(node));
                } else
                    item = 0;
            }
            put(t + 0xbc0, count);
            put(t + 0x794, 0);
        }
        if (get(t + 0xbcc) == 2)
            return;
        int32_t count = static_cast<int32_t>(get(t + 0xbc0));
        for (int32_t i = 0; i < count - 1; ++i) {
            uint32_t at = t + 0x7c0 + 4 * static_cast<uint32_t>(i), best = actorOf(get(at));
            for (int32_t j = i + 1; j < static_cast<int32_t>(get(t + 0xbc0)); ++j) {
                uint32_t jt = t + 0x7c0 + 4 * static_cast<uint32_t>(j), other = actorOf(get(jt));
                if (static_cast<int32_t>(get(other + 0xf8)) > static_cast<int32_t>(get(best + 0xf8))) {
                    uint32_t old = get(at);
                    put(at, get(jt));
                    put(jt, old);
                    best = other;
                }
            }
            count = static_cast<int32_t>(get(t + 0xbc0));
        }
        uint32_t rank = 0, tied = 0, previous = 0xffffffff;
        for (int32_t i = 0; i < static_cast<int32_t>(get(t + 0xbc0)); ++i) {
            uint32_t p = actorOf(get(t + 0x7c0 + 4 * static_cast<uint32_t>(i))), score = get(p + 0xf8);
            if (get(t + 0xbcc) == 1) {
                if (!force && static_cast<int32_t>(score) <= 0)
                    put(p + 0xfc, 0);
                else if (score == previous) {
                    ++tied;
                    put(p + 0xfc, rank);
                } else {
                    rank += 1 + tied;
                    tied = 0;
                    put(p + 0xfc, rank);
                    previous = score;
                }
            } else
                put(p + 0xfc, 0);
        }
    }
    void append(char *out, const char *s) {
        size_t a = std::strlen(out), b = std::strlen(s);
        if (a + b >= 512) {
            c.fault = 2;
            throw Missing{};
        }
        std::memcpy(out + a, s, b + 1);
    }
    void appendToken(char *out, uint32_t t) {
        char tmp[512];
        size_t i = 0;
        do {
            uint32_t word = get(t & ~3u);
            tmp[i] = static_cast<char>(word >> (8 * (t & 3)));
            ++t;
            if (tmp[i] == 0)
                break;
            ++i;
        } while (i < 511);
        if (i == 511) {
            c.fault = 2;
            throw Missing{};
        }
        append(out, tmp);
    }
    void format(char *out, uint32_t literal, std::initializer_list<uint32_t> args) {
        char temp[64]{};
        ClawGameFrameServiceCall q{};
        q.function = 0x4a3920;
        q.argumentCount = 2 + static_cast<uint32_t>(args.size());
        q.arguments[0] = 0;
        q.arguments[1] = literal;
        uint32_t i = 2;
        for (auto a : args)
            q.arguments[i++] = a;
        q.localMask = 1;
        q.bufferCount = 1;
        q.buffers[0] = temp;
        q.bufferBytes[0] = 64;
        if (!dependency) {
            c.fault = 3;
            throw Missing{};
        }
        dependency(&c, q, user);
        temp[63] = 0;
        append(out, temp);
    }
    void overlay(uint32_t t) {
        auto &g = *c.globals;
        uint8_t flags = static_cast<uint8_t>(g.debugFlags);
        if (flags & 32)
            return;
        char text[512]{};
        if (flags & 16) {
            format(text, 0x52a044, {get(get(t + 4) + 0x18)});
            flags = static_cast<uint8_t>(g.debugFlags);
        }
        if (flags & 1) {
            format(text, 0x52a070, {get(get(get(t + 0xc) + 8) + 0x1c)});
            flags = static_cast<uint8_t>(g.debugFlags);
        }
        if (flags & 4) {
            uint32_t p = g.playerToken;
            format(text, 0x52a060, {get(p + 0x4c), get(p + 0x50)});
            flags = static_cast<uint8_t>(g.debugFlags);
        }
        if (flags & 64)
            append(text, " Timing = On ");
        if (flags & 128) {
            uint32_t temp = 0;
            call(0x49c860, 0, {0, g.accumulatedTick}, 1, {&temp}, {4});
            call(0x4f6920, 0, {0x52a040}, 256, {&temp}, {4});
            appendToken(text, temp);
            call(0x4f6920, 0, {0x52a040}, 256, {&temp}, {4});
            call(0x4f6584, 0, {}, 256, {&temp}, {4});
            flags = static_cast<uint8_t>(g.debugFlags);
        }
        if (flags & 2) {
            uint32_t objects = get(get(get(get(t + 4) + 0x30) + 8) + 0x1c), messages = get(t + 0x14c);
            uint32_t racers = call(vt(t, 0x50), t);
            format(text, 0x52a01c, {racers, messages, objects});
        }
        uint32_t state = call(vt(t, 0x10), t);
        if (state != 4 && !text[0] && !get(get(get(t + 4) + 0x4c) + 0xc)) {
            uint32_t config = get(get(t + 4) + 0x4c);
            if (c.composeMessages)
                messages(config, g.stageDelta);
            else
                call(0x4224f0, config, {g.stageDelta});
            return;
        }
        uint32_t backend = get(get(get(get(t + 0xc) + 4) + 0x14) + 0x2c), iface = get(backend + 8), hdc = 0;
        call(vt(iface, 0x44), 0, {iface, 0}, 2, {&hdc}, {4});
        if (!hdc)
            return;
        call(0x546888, 0, {hdc, 1});
        call(0x546880, 0, {hdc, 0xffffff});
        call(vt(t, 0x64), t, {hdc});
        if (text[0]) {
            uint32_t rect[4] = {g.overlayRect[0], g.overlayRect[3] - 28, g.overlayRect[2], g.overlayRect[3]};
            if (static_cast<int32_t>(rect[0]) > 0)
                call(0x546d30, 0, {hdc, 0, 0xffffffff, 0, 32}, 10, {text, rect},
                     {static_cast<uint32_t>(std::strlen(text) + 1), 16});
            else
                call(0x546890, 0, {hdc, 0, rect[1], 0, static_cast<uint32_t>(std::strlen(text))}, 8, {text},
                     {static_cast<uint32_t>(std::strlen(text) + 1)});
        }
        iface = get(backend + 8);
        call(vt(iface, 0x68), 0, {iface, hdc});
    }
};
} // namespace
extern "C" void claw_game_frame_service_defaults(ClawGameFrameServiceContext *c) {
    if (c)
        c->composeMessages = 1;
}
extern "C" uint32_t claw_game_frame_service_entry(uint32_t f, uint32_t t, uint32_t a, ClawGameFrameServiceContext *c,
                                                  ClawGameFrameServiceDependency d, void *u, uint32_t *out) {
    if (f != 0x4774f0 && f != 0x477840 && f != 0x478290 && f != 0x46c2c0 && f != 0x4224f0 && f != 0x46ca50 &&
        f != 0x40af90 && f != 0x4750d0 && f != 0x4750e0 && f != 0x4bb030)
        return 0;
    if (out)
        *out = 0;
    if (!c)
        return 1;
    if (!c->globals) {
        c->fault = 1;
        return 1;
    }
    c->fault = 0;
    Runtime r{*c, d, u};
    try {
        if (f == 0x4774f0)
            r.pose(t);
        else if (f == 0x477840) {
            uint32_t result = r.poll(t);
            if (out)
                *out = result;
        } else if (f == 0x478290)
            r.ranks(t, a);
        else if (f == 0x46c2c0)
            r.overlay(t);
        else if (f == 0x4224f0)
            r.messages(t, a);
        else if (f == 0x46ca50)
            r.messageDraw(t, a);
        else {
            uint32_t result = r.call(f, t);
            if (out)
                *out = result;
        }
    } catch (Missing &) {
    }
    return 1;
}
