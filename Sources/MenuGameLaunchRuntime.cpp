#include "MenuGameLaunchRuntime.h"
#include "CheckpointLogicRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failed {};
int32_t signedWord(uint32_t v) {
    int32_t s;
    std::memcpy(&s, &v, 4);
    return s;
}
bool owned(uint32_t);
uint32_t count(uint32_t);
struct Run {
    ClawMenuGameLaunchContext &c;
    ClawMenuGameLaunchDependency d;
    void *u;
    uint32_t operations = 0;
    ClawSinglePlayerSceneGlobals *activeSingle = nullptr;
    ClawSpecialCommandGlobals *activeSpecial = nullptr;
    static constexpr uint32_t selected[21] = {0x538418, 0x54316c, 0x537210, 0x53c9c0, 0x5349dc, 0x537e88, 0x534ca4,
                                              0x52be14, 0x52be18, 0x537204, 0x53ec44, 0x537268, 0x537214, 0x537218,
                                              0x53721c, 0x537220, 0x537228, 0x537224, 0x53722c, 0x537230, 0x537264};
    static constexpr uint32_t applicationAliases[13] = {0x537e88, 0x532c10, 0x537204, 0x537200, 0x541328,
                                                        0x54132c, 0x541330, 0x541334, 0x541338, 0x537208,
                                                        0x53720c, 0x5430c8, 0x5430c4};
    [[noreturn]] void fail(uint32_t f = 1) {
        if (!c.fault)
            c.fault = f;
        throw Failed{};
    }
    void step() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 1000000))
            fail(3);
    }
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        if (c.fault)
            throw Failed{};
        if (t < 4096)
            fail(2);
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
    void applicationImport() {
        if (!c.progression || !c.progression->application)
            return;
        uint32_t values[13];
        for (uint32_t i = 0; i < 13; ++i)
            values[i] = get(applicationAliases[i]);
        std::memcpy(c.progression->application, values, sizeof values);
    }
    void singleExport() {
        if (activeSingle) {
            uint32_t values[21];
            std::memcpy(values, activeSingle, sizeof values);
            for (uint32_t i = 0; i < 21; ++i)
                put(selected[i], values[i]);
        }
        if (activeSpecial) {
            auto &g = *activeSpecial;
            uint32_t values[13] = {g.playerToken, g.audioVolume, g.inputMappingToken, g.mouseToken};
            std::memcpy(values + 4, &g.clock, 20);
            std::memcpy(values + 9, &g.stage, 8);
            std::memcpy(values + 11, &g.animation, 8);
            for (uint32_t i = 0; i < 13; ++i)
                put(applicationAliases[i], values[i]);
        }
        applicationImport();
    }
    void singleImport() {
        if (activeSingle) {
            uint32_t values[21];
            for (uint32_t i = 0; i < 21; ++i)
                values[i] = get(selected[i]);
            std::memcpy(activeSingle, values, sizeof values);
        }
        applicationImport();
        if (activeSpecial && c.progression && c.progression->application) {
            auto &a = *c.progression->application;
            activeSpecial->playerToken = a.playerToken;
            activeSpecial->audioVolume = a.masterVolume;
            activeSpecial->inputMappingToken = a.keyboardToken;
            activeSpecial->mouseToken = a.mouseToken;
            activeSpecial->clock = a.clock;
            activeSpecial->stage = a.stage;
            activeSpecial->animation = a.animation;
        }
    }
    uint32_t event(ClawMenuGameLaunchCall &e) {
        step();
        singleExport();
        if (!d)
            fail();
        auto v = d(&c, &e, u);
        singleImport();
        if (c.fault)
            throw Failed{};
        return v;
    }
    const char *text(uint32_t t) {
        return reinterpret_cast<const char *>(span(t & ~3u)) + (t & 3u);
    }
    uint32_t invoke(uint32_t, uint32_t, const uint32_t *, uint32_t);
    uint32_t invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        return invoke(f, t, a.begin(), uint32_t(a.size()));
    }
    uint32_t service(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        ClawMenuGameLaunchCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        if (n > 40)
            fail(3);
        std::copy_n(a, n, q.arguments);
        if (n && (f == 0x4f6286 || f == 0x4b7f20 || f == 0x4b7cd0 || f == 0x4b7dc0 || f == 0x4b68c0 || f == 0x4b67f0 ||
                  f == 0x4f66cc || f == 0x4f65f2))
            q.name = text(a[0]);
        return event(q);
    }
    static uint32_t *lookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->span(t, n);
    }
    static uint32_t allocate(void *p, uint32_t n) {
        return static_cast<Run *>(p)->invoke(0x4f63ec, 0, {n});
    }
    static void free(void *p, uint32_t t) {
        static_cast<Run *>(p)->invoke(0x4f6428, 0, {t});
    }
    static uint32_t call(void *p, ClawSceneActorCall q) {
        return static_cast<Run *>(p)->invoke(q.function, q.receiver, q.arguments, q.argumentCount);
    }
    static uint32_t clock(void *p) {
        auto &r = *static_cast<Run *>(p);
        r.singleExport();
        if (!r.c.scene.readClock)
            r.fail();
        auto v = r.c.scene.readClock(r.c.scene.context);
        r.singleImport();
        return v;
    }
    ClawSceneActorHost host() {
        return {this, lookup, allocate, free, call, clock};
    }
    uint32_t cell(uint32_t f, uint32_t &value) {
        ClawMenuGameLaunchCall q{};
        q.function = f;
        q.localMask = 256;
        q.bufferCount = 1;
        q.buffers[0] = &value;
        q.bufferBytes[0] = 4;
        return event(q);
    }
    uint32_t fileCall(uint32_t f, uint32_t *file, std::initializer_list<uint32_t> a = {}, void *buffer = nullptr,
                      uint32_t bytes = 0) {
        ClawMenuGameLaunchCall q{};
        q.function = f;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        q.localMask = 256;
        q.bufferCount = 1;
        q.buffers[0] = file;
        q.bufferBytes[0] = 16;
        if (buffer) {
            q.localMask |= 1;
            q.bufferCount = 2;
            q.buffers[1] = buffer;
            q.bufferBytes[1] = bytes;
        }
        return event(q);
    }
    uint32_t header(uint32_t path, void *output, uint32_t capacity, uint32_t outputToken = 0) {
        if (!path || (!output && !outputToken))
            return 0;
        uint32_t file[4]{};
        fileCall(0x4f72c9, file);
        if (!fileCall(0x4f7448, file, {path, 0, 0})) {
            fileCall(0x4f7369, file);
            return 0;
        }
        alignas(uint32_t) uint8_t data[1524]{};
        auto read = fileCall(0x4f7570, file, {0, 1524}, data, 1524);
        uint32_t result = 0;
        if (read == 1524) {
            uint32_t size;
            std::memcpy(&size, data, 4);
            if (size < 1525) {
                uint32_t length = 0;
                for (; length < 1508 && data[16 + length]; ++length)
                    step();
                if (length == 1508 || length + 1 > capacity)
                    fail(2);
                if (outputToken)
                    output = reinterpret_cast<uint8_t *>(
                                 span(outputToken & ~3u, (length + 1 + (outputToken & 3u) + 3) / 4)) +
                             (outputToken & 3u);
                std::memcpy(output, data + 16, length + 1);
                result = 1;
            }
        }
        fileCall(0x4f7369, file);
        return result;
    }
    uint32_t route(ClawMenuGameLaunchCall q) {
        if (!q.localMask && !q.bufferCount)
            return invoke(q.function, q.receiver, q.arguments, q.argumentCount);
        return event(q);
    }
    static uint32_t progression(ClawApplicationLevelProgressionContext *, const ClawApplicationLevelProgressionCall *q,
                                void *p) {
        return static_cast<Run *>(p)->route(*q);
    }
    static uint32_t menu(ClawStateFiveContext *, const ClawStateFiveCall *q, void *p) {
        return static_cast<Run *>(p)->route(*q);
    }
    static uint32_t single(ClawSinglePlayerSceneContext *, ClawSinglePlayerSceneCall e, void *p) {
        ClawMenuGameLaunchCall q{};
        q.function = e.function;
        q.receiver = e.receiver;
        q.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, 8, q.arguments);
        q.localMask = e.localMask;
        q.bufferCount = e.bufferCount;
        std::copy_n(e.buffers, 3, q.buffers);
        std::copy_n(e.bufferBytes, 3, q.bufferBytes);
        auto &r = *static_cast<Run *>(p);
        if (e.function == 0x4a3920)
            q.name = r.text(e.arguments[1]);
        else if (e.argumentCount && (e.function == 0x4b7f20 || e.function == 0x4b7dc0 || e.function == 0x4b7cd0 ||
                                     e.function == 0x4b67f0)) {
            q.name = (e.localMask & 1) ? reinterpret_cast<const char *>(e.buffers[0]) : r.text(e.arguments[0]);
        }
        return r.route(q);
    }
    static uint32_t special(ClawSpecialCommandContext *, const ClawSpecialCommandCall *e, void *p) {
        ClawMenuGameLaunchCall q{};
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
        return static_cast<Run *>(p)->event(q);
    }
    static uint32_t startup(ClawPlayerStartupContext *, const ClawPlayerStartupCall *q, void *p) {
        return single(nullptr, *q, p);
    }
};
uint32_t body(Run &r, uint32_t f, uint32_t t, const uint32_t *a) {
    switch (f) {
    case 0x436e60: {
        uint32_t incoming = a[0], result = 0xffffffff;
        if (r.get(incoming - 8) && r.get(r.get(r.get(0x5371fc) + 48) + 36)) {
            uint8_t name[256]{};
            if (r.header(incoming, name, 256)) {
                uint32_t at = 0;
                while (name[0] && (int8_t(name[0]) < '0' || int8_t(name[0]) > '9')) {
                    ++at;
                    if (at == 256)
                        r.fail(2);
                    name[0] = name[at];
                }
                ClawMenuGameLaunchCall q{};
                q.function = 0x4a3ce0;
                q.argumentCount = 1;
                q.localMask = 1;
                q.bufferCount = 1;
                q.buffers[0] = name + at;
                q.bufferBytes[0] = uint32_t(std::strlen(reinterpret_cast<const char *>(name + at))) + 1;
                result = r.event(q);
            }
        }
        r.cell(0x4f6584, incoming);
        return result;
    }
    case 0x4cd530: {
        if (!a[0] || !a[1])
            return 0;
        return r.header(a[0], nullptr, 1508, a[1]);
    }
    case 0x426e30: {
        auto checkpoint = a[1] == 0x807e;
        auto level = checkpoint ? r.get(t + 0xd4) : a[2];
        if (!r.invoke(0x429b70, t, {level})) {
            if (checkpoint)
                r.put(t + 0xa8, 0);
            r.invoke(0x429e10, t, {0x8005, checkpoint ? 0x6abu : 0x6acu});
        }
        return 1;
    }
    case 0x42ba10: {
        if (signedWord(a[0]) < 1 || signedWord(a[0]) > 14)
            return 0;
        if (a[0] == 1)
            return 1;
        auto player = r.get(t + 100);
        if (!player)
            return 0;
        auto record = r.invoke(0x49ae60, player, {a[0] - 1, 3});
        return record ? uint32_t((r.get(record) & 1) != 0) : 0;
    }
    case 0x42ba70: {
        if (signedWord(a[0]) < 1 || signedWord(a[0]) > 14)
            return 0;
        auto player = r.get(t + 100);
        if (!player)
            return 0;
        if (a[0] == 1 && !a[1])
            return 1;
        return r.invoke(0x49af30, player, {a[0], a[1]}) != 0;
    }
    case 0x42bab0:
        if (!r.get(t + 100))
            return 0;
        return signedWord(r.get(r.get(t + 96) + 12)) > 1;
    case 0x42bad0:
        if (!r.get(t + 100))
            return 0;
        return r.invoke(0x4a3cf0, 0, {r.get(t + 100) + 20, 0x5255e8}) != 0;
    default:
        r.fail(3);
    }
}
uint32_t Run::invoke(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
    step();
    if (n > 40)
        fail(3);
    if (owned(f)) {
        if (n != count(f))
            fail(3);
        return body(*this, f, t, a);
    }
    uint32_t out = 0;
    // Admit each composed family explicitly to avoid recursive dependency fallback.
    if (c.composeSinglePlayer && c.singlePlayer && (f != 0x46aeb0 || c.singlePlayer->composeLevel) &&
        (f == 0x46a6d0 || f == 0x46aeb0 || f == 0x48f0d0 || f == 0x40b5c0 || f == 0x42aa50 || f == 0x42af50)) {
        if (!c.singlePlayer->globals)
            fail();
        auto q = *c.singlePlayer;
        q.host = host();
        q.fault = 0;
        auto previous = activeSingle;
        activeSingle = q.globals;
        singleImport();
        uint32_t supported = 0;
        if (f == 0x46a6d0)
            q.composeLevel = 0;
        if (f == 0x46aeb0 && c.composeStartup && c.startup) {
            auto s = *c.startup;
            s.scene = host();
            s.singlePlayer = &q;
            s.fault = 0;
            supported = claw_player_startup_entry(f, t, a, n, &s, startup, this, &out);
            if (s.fault)
                fail(s.fault);
        } else
            supported = claw_single_player_scene_entry(f, t, a, n, &q, single, this, &out);
        if (!supported || q.fault)
            fail(q.fault ? q.fault : 1);
        singleExport();
        activeSingle = previous;
        return out;
    }
    if (c.composeStartup && c.startup &&
        (f == 0x415ce0 || f == 0x46c790 || f == 0x46d8e0 || f == 0x49af30 || f == 0x49af90)) {
        auto q = *c.startup;
        q.scene = host();
        q.fault = 0;
        if (!claw_player_startup_entry(f, t, a, n, &q, startup, this, &out) || q.fault)
            fail(q.fault ? q.fault : 1);
        singleImport();
        return out;
    }
    if (f == 0x49ae60 && c.composeStartup && c.startup && c.startup->composeCache) {
        ClawCheckpointGlobals globals{};
        ClawCheckpointContext q{};
        q.scene = host();
        q.globals = &globals;
        if (!claw_checkpoint_entry(f, t, a, n, &q, nullptr, nullptr, &out) || q.fault)
            fail(q.fault ? q.fault : 1);
        return out;
    }
    if (f == 0x42abf0 && c.composeProgression && c.progression && c.progression->application) {
        applicationImport();
        auto &app = *c.progression->application;
        ClawSpecialCommandGlobals g{};
        if (c.progression->special && c.progression->special->globals)
            g = *c.progression->special->globals;
        g.playerToken = app.playerToken;
        g.audioVolume = app.masterVolume;
        g.inputMappingToken = app.keyboardToken;
        g.mouseToken = app.mouseToken;
        g.clock = app.clock;
        g.stage = app.stage;
        g.animation = app.animation;
        ClawSpecialCommandContext q{host(), &g, 0};
        auto previous = activeSpecial;
        activeSpecial = &g;
        auto covered = claw_special_command_entry(f, t, a, n, &q, special, this, &out);
        singleExport();
        activeSpecial = previous;
        if (c.progression->special && c.progression->special->globals) {
            auto &dest = *c.progression->special->globals;
            dest.playerToken = g.playerToken;
            dest.audioVolume = g.audioVolume;
            dest.inputMappingToken = g.inputMappingToken;
            dest.mouseToken = g.mouseToken;
            dest.clock = g.clock;
            dest.stage = g.stage;
            dest.animation = g.animation;
        }
        if (!covered || q.fault)
            fail(q.fault ? q.fault : 1);
        return out;
    }
    if (c.composeMenu && c.menu && f != 0x426e30) {
        auto q = *c.menu;
        q.scene = host();
        q.application = nullptr;
        q.composeBase = q.composeShared = q.composeScene = 0;
        q.fault = 0;
        if (claw_state_five_entry(f, t, a, n, &q, menu, this, &out)) {
            if (q.fault)
                fail(q.fault);
            return out;
        }
        if (q.fault)
            fail(q.fault);
    }
    if (c.composeProgression && c.progression && f != 0x426e30 &&
        (f != 0x428c40 || c.progression->composeTransitions)) {
        auto q = *c.progression;
        q.scene = host();
        q.composeSinglePlayer = q.composeBooty = q.composeLifecycle = 0;
        q.fault = 0;
        applicationImport();
        if (claw_application_level_progression_entry(f, t, a, n, &q, progression, this, &out)) {
            if (q.fault)
                fail(q.fault);
            return out;
        }
        if (q.fault)
            fail(q.fault);
    }
    return service(f, t, a, n);
}
bool owned(uint32_t f) {
    return f == 0x436e60 || f == 0x4cd530 || f == 0x426e30 || f == 0x42ba10 || f == 0x42ba70 || f == 0x42bab0 ||
           f == 0x42bad0;
}
uint32_t count(uint32_t f) {
    return f == 0x436e60 ? 1 : f == 0x4cd530 ? 2 : f == 0x426e30 ? 3 : f == 0x42ba70 ? 2 : f == 0x42ba10 ? 1 : 0;
}
} // namespace
extern "C" uint32_t claw_menu_game_launch_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                ClawMenuGameLaunchContext *c, ClawMenuGameLaunchDependency d, void *u,
                                                uint32_t *out) {
    if (!c || !out || !owned(f))
        return 0;
    if (n != count(f) || (n && !a)) {
        c->fault = 3;
        return 0;
    }
    if (f == 0x426e30 && a[1] != 0x807e && a[1] != 0x807f)
        return 0;
    try {
        Run r{*c, d, u};
        *out = body(r, f, t, a);
        return 1;
    } catch (Failed &) {
        return 0;
    }
}
