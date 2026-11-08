#include "MessageDrawingRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failed {};
constexpr uint32_t temporaryToken = 0xfffff000u;
struct Run {
    ClawMessageDrawingContext &c;
    ClawMessageDrawingDependency dependency;
    void *user;
    uint32_t temporary = 0;
    [[noreturn]] void fail(uint32_t code) {
        if (!c.fault)
            c.fault = code;
        throw Failed{};
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (c.fault)
            throw Failed{};
        if (t == temporaryToken && n <= 1)
            return &temporary;
        auto *p = c.scene.lookup ? c.scene.lookup(c.scene.context, t, n) : nullptr;
        if (!p)
            fail(1);
        return p;
    }
    uint32_t get(uint32_t t) {
        return *span(t);
    }
    void put(uint32_t t, uint32_t v) {
        *span(t) = v;
    }
    uint8_t *byte(uint32_t t) {
        return reinterpret_cast<uint8_t *>(span(t & ~3u)) + (t & 3);
    }
    uint32_t limit() {
        return c.textLimit ? c.textLimit : 65536;
    }
    uint32_t length(uint32_t t) {
        for (uint32_t i = 0; i < limit(); ++i)
            if (!*byte(t + i))
                return i;
        fail(2);
    }
    uint32_t call(ClawMessageDrawingCall e) {
        uint32_t out;
        if (dependency)
            out = dependency(&c, e, user);
        else if (!e.localMask && !e.bufferCount && e.argumentCount <= 4 && c.scene.call) {
            ClawSceneActorCall q{};
            q.function = e.function;
            q.receiver = e.receiver;
            q.argumentCount = e.argumentCount;
            std::copy_n(e.arguments, e.argumentCount, q.arguments);
            out = c.scene.call(c.scene.context, q);
        } else
            fail(3);
        if (c.fault)
            throw Failed{};
        return out;
    }
    uint32_t call(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        ClawMessageDrawingCall e{};
        e.function = f;
        e.receiver = t;
        e.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), e.arguments);
        return call(e);
    }
    static uint32_t *lookup(void *u, uint32_t t, uint32_t n) {
        return static_cast<Run *>(u)->span(t, n);
    }
    static uint32_t sceneCall(void *u, ClawSceneActorCall q) {
        auto &r = *static_cast<Run *>(u);
        ClawMessageDrawingCall e{};
        e.function = q.function;
        e.receiver = q.receiver;
        e.argumentCount = q.argumentCount;
        std::copy_n(q.arguments, q.argumentCount, e.arguments);
        return r.call(e);
    }
    static void release(void *u, uint32_t t) {
        static_cast<Run *>(u)->call(0x4f6428, 0, {t});
    }
    ClawSceneActorHost host() {
        return {this, lookup, nullptr, release, sceneCall, nullptr};
    }
    static uint32_t stringService(ClawPlayerDeathServiceContext *, const ClawPlayerDeathServiceCall *q, void *u) {
        auto &r = *static_cast<Run *>(u);
        ClawMessageDrawingCall e{};
        e.function = q->function;
        e.receiver = q->receiver;
        e.argumentCount = q->argumentCount;
        std::copy_n(q->arguments, q->argumentCount, e.arguments);
        if (e.receiver == temporaryToken) {
            e.receiver = 0;
            e.localMask = 256;
            e.bufferCount = 1;
            e.buffers[0] = &r.temporary;
            e.bufferBytes[0] = 4;
        }
        return r.call(e);
    }
    void copy(uint32_t source) {
        if (!c.composeStrings) {
            ClawMessageDrawingCall e{};
            e.function = 0x4f6449;
            e.argumentCount = 1;
            e.arguments[0] = source;
            e.localMask = 256;
            e.bufferCount = 1;
            e.buffers[0] = &temporary;
            e.bufferBytes[0] = 4;
            call(e);
            return;
        }
        ClawPlayerDeathServiceGlobals g{0, c.emptyStringToken};
        ClawPlayerDeathServiceContext x{host(), &g, temporaryToken, 0};
        uint32_t out = 0;
        if (!claw_player_death_service_entry(0x4f6449, temporaryToken, &source, 1, &x, stringService, this, &out) ||
            x.fault)
            fail(x.fault ? x.fault : 1);
    }
    void destroy() {
        if (!c.composeStrings) {
            ClawMessageDrawingCall e{};
            e.function = 0x4f6584;
            e.localMask = 256;
            e.bufferCount = 1;
            e.buffers[0] = &temporary;
            e.bufferBytes[0] = 4;
            call(e);
            return;
        }
        ClawActorDestructionGlobals g{};
        g.emptyStringToken = c.emptyStringToken;
        uint32_t out = 0, fault = 0;
        if (!claw_actor_destruction_entry(0x4f6584, temporaryToken, 0, &g, host(), &fault, &out) || fault)
            fail(fault ? fault : 1);
    }
    void append(uint32_t source) {
        uint32_t n = length(source) + 1, at = length(0x534ef8);
        if (uint64_t(at) + n > limit())
            fail(2);
        uint32_t i = 0;
        for (; i + 4 <= n; i += 4) {
            uint8_t word[4];
            for (uint32_t j = 0; j < 4; ++j)
                word[j] = *byte(source + i + j);
            for (uint32_t j = 0; j < 4; ++j)
                *byte(0x534ef8 + at + i + j) = word[j];
        }
        for (; i < n; ++i)
            *byte(0x534ef8 + at + i) = *byte(source + i);
    }
    uint32_t draw(uint32_t config, const uint32_t *a, uint32_t *localRect) {
        uint32_t hdc = a[1];
        if (!hdc)
            return 0;
        int32_t count = int32_t(get(config + 12));
        if (count < 1)
            return 0;
        count = std::min(count, int32_t(a[0]));
        if (count < 1)
            return 0;
        *byte(0x534ef8) = 0;
        uint32_t node = get(config + 4);
        for (int32_t n = 0; n < count; ++n) {
            if (node) {
                uint32_t source = node + 8;
                node = get(node);
                copy(source);
                append(temporary);
                if (n < count - 1)
                    append(0x5250d8);
                destroy();
            }
        }
        uint32_t oldFont = 0, font = get(config + 0x34);
        if (font)
            oldFont = call(0x54691c, 0, {hdc, font});
        uint32_t size = length(0x534ef8);
        ClawMessageDrawingCall e{};
        e.function = 0x546d30;
        e.argumentCount = 5;
        e.arguments[0] = hdc;
        e.arguments[1] = 0x534ef8;
        e.arguments[2] = size;
        e.arguments[3] = a[2];
        e.arguments[4] = a[3];
        if (!a[2] && localRect) {
            e.localMask = 8;
            e.buffers[e.bufferCount] = localRect;
            e.bufferBytes[e.bufferCount++] = 16;
        }
        e.buffers[e.bufferCount] = reinterpret_cast<uint8_t *>(span(0x534ef8, (size + 4) / 4));
        e.bufferBytes[e.bufferCount++] = size + 1;
        call(e);
        if (oldFont)
            call(0x54691c, 0, {hdc, oldFont});
        return 1;
    }
};
} // namespace
extern "C" void claw_message_drawing_defaults(ClawMessageDrawingContext *c) {
    if (c) {
        c->composeStrings = 1;
        c->textLimit = 0;
    }
}
extern "C" uint32_t claw_message_drawing_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, uint32_t *rect,
                                               ClawMessageDrawingContext *c, ClawMessageDrawingDependency d, void *u,
                                               uint32_t *out) {
    if (f != 0x4226b0 || !c)
        return 0;
    if (n != 4 || !a) {
        c->fault = 4;
        return 0;
    }
    if (c->fault)
        return 0;
    Run r{*c, d, u, 0};
    try {
        uint32_t result = r.draw(t, a, rect);
        if (out)
            *out = result;
        return 1;
    } catch (Failed &) {
        return 0;
    }
}
