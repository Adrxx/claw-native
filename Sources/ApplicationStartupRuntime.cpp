#include "ApplicationStartupRuntime.h"
#include "GameTiming.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Failure {};
int32_t signedWord(uint32_t v) {
    int32_t s;
    std::memcpy(&s, &v, 4);
    return s;
}
struct Run {
    ClawApplicationStartupContext &c;
    ClawApplicationStartupDependency d;
    void *u;
    uint32_t operations = 0;
    ClawTimingManager timing{};
    ClawClockState timingClock{};
    uint32_t timingToken = 0;
    [[noreturn]] void fail(uint32_t f = 1) {
        if (!c.fault)
            c.fault = f;
        throw Failure{};
    }
    void step() {
        if (++operations > (c.maximumOperations ? c.maximumOperations : 1000000))
            fail(3);
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
    uint8_t *bytes(uint32_t t, uint32_t n) {
        if (c.bytes) {
            auto *p = c.bytes(c.byteContext, t, n);
            if (!p)
                fail();
            return p;
        }
        return reinterpret_cast<uint8_t *>(span(t & ~3u, (n + (t & 3u) + 3) / 4)) + (t & 3u);
    }
    uint32_t length(uint32_t t) {
        uint32_t n = 0;
        while (*bytes(t + n, 1)) {
            step();
            ++n;
        }
        return n;
    }
    void copyString(uint32_t dst, uint32_t src, uint32_t capacity) {
        auto n = length(src) + 1;
        if (n > capacity)
            fail(2);
        std::memmove(bytes(dst, n), bytes(src, n), n);
    }
    static uint32_t *lookup(void *p, uint32_t t, uint32_t n) {
        return static_cast<Run *>(p)->span(t, n);
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
    static uint32_t call(void *p, ClawSceneActorCall q) {
        return static_cast<Run *>(p)->invoke(q.function, q.receiver, q.arguments, q.argumentCount);
    }
    static uint32_t clock(void *p) {
        return static_cast<Run *>(p)->invoke(0x546df0, 0, {});
    }
    ClawSceneActorHost host() {
        return {this, lookup, allocate, release, call, clock};
    }
    void timingSync(bool write) {
        uint32_t m[5], g[5];
        if (write) {
            std::memcpy(m, &timing, 20);
            std::memcpy(g, &timingClock, 20);
        }
        for (uint32_t i = 0; i < 5; ++i)
            if (write) {
                put(timingToken + 24 + 4 * i, m[i]);
                put(0x541328 + 4 * i, g[i]);
            } else {
                m[i] = get(timingToken + 24 + 4 * i);
                g[i] = get(0x541328 + 4 * i);
            }
        if (!write) {
            std::memcpy(&timing, m, 20);
            std::memcpy(&timingClock, g, 20);
        }
    }
    static uint32_t timingRead(void *p) {
        auto &r = *static_cast<Run *>(p);
        r.timingSync(true);
        auto v = r.invoke(0x546df0, 0);
        r.timingSync(false);
        return v;
    }
    uint32_t event(ClawApplicationStartupCall &q) {
        step();
        if (!d)
            fail();
        auto v = d(&c, &q, u);
        if (c.fault)
            throw Failure{};
        return v;
    }
    uint32_t external(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        if (n > 40)
            fail(2);
        ClawApplicationStartupCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = n;
        std::copy_n(a, n, q.arguments);
        return event(q);
    }
    template <class T> static auto nameOf(const T &q, int) -> decltype(q.name) {
        return q.name;
    }
    template <class T> static const char *nameOf(const T &, long) {
        return nullptr;
    }
    template <class T> uint32_t forward(const T &q) {
        uint32_t v = 0;
        if (!q.localMask && dispatch(q.function, q.receiver, q.arguments, q.argumentCount, v))
            return v;
        ClawApplicationStartupCall e{};
        e.function = q.function;
        e.receiver = q.receiver;
        e.argumentCount = q.argumentCount;
        e.name = nameOf(q, 0);
        if (e.argumentCount > 40 || q.bufferCount > 3)
            fail(2);
        std::copy_n(q.arguments, q.argumentCount, e.arguments);
        e.localMask = q.localMask;
        e.bufferCount = q.bufferCount;
        for (uint32_t i = 0; i < q.bufferCount; ++i) {
            e.buffers[i] = const_cast<void *>(static_cast<const void *>(q.buffers[i]));
            e.bufferBytes[i] = q.bufferBytes[i];
        }
        return event(e);
    }
    static uint32_t graphicsService(ClawSceneStartupCompositionContext *, const ClawSceneStartupCompositionCall *q,
                                    void *p) {
        return static_cast<Run *>(p)->forward(*q);
    }
    static uint32_t archiveService(ClawResourceTableConstructionContext *, const ClawResourceTableConstructionCall *q,
                                   void *p) {
        return static_cast<Run *>(p)->forward(*q);
    }
    static uint32_t namespaceService(ClawResourceNamespaceContext *, const ClawResourceNamespaceCall *q, void *p) {
        return static_cast<Run *>(p)->forward(*q);
    }
    static uint32_t dataService(ClawResourceDataContext *, const ClawResourceDataCall *q, void *p) {
        return static_cast<Run *>(p)->invoke(q->function, q->receiver, q->arguments, q->argumentCount);
    }
    static uint32_t playerService(ClawPlayerCacheApplicationContext *, const ClawPlayerCacheApplicationCall *q,
                                  void *p) {
        return static_cast<Run *>(p)->forward(*q);
    }
    static uint32_t messagesService(ClawPlayerStartupContext *, const ClawPlayerStartupCall *q, void *p) {
        return static_cast<Run *>(p)->forward(*q);
    }
    static uint32_t fadeService(ClawPlayerFadeContext *, const ClawPlayerFadeCall *q, void *p) {
        return static_cast<Run *>(p)->invoke(q->function, q->receiver, q->arguments, q->argumentCount);
    }
    static uint64_t lightService(ClawLightPaletteContext *, const ClawLightPaletteCall *q, void *p) {
        return static_cast<Run *>(p)->forward(*q);
    }
    static uint32_t ambientService(ClawSoundTriggerContext *context, const ClawSoundTriggerCall *q, void *p) {
        auto &r = *static_cast<Run *>(p);
        if (q->temporary)
            r.fail(2);
        auto v = r.invoke(q->function, q->receiver, q->arguments, q->argumentCount);
        const uint32_t addresses[] = {0x5371fc, 0x537e88, 0x532c0c, 0x53c9a0, 0x53c9a4,
                                      0x53c9a8, 0x53c9ac, 0x53c9b0, 0x53720c};
        uint32_t values[9];
        for (uint32_t i = 0; i < 9; ++i)
            values[i] = r.get(addresses[i]);
        std::memcpy(context->globals, values, 36);
        context->masterVolume = r.get(0x532c10);
        return v;
    }
    static uint32_t musicService(ClawMusicContext *context, const ClawMusicCall *q, void *p) {
        auto &r = *static_cast<Run *>(p);
        r.musicGlobals(*context, true);
        if (q->transport)
            r.fail(2);
        auto v = r.invoke(q->function, q->receiver, q->arguments, q->argumentCount);
        r.musicGlobals(*context, false);
        return v;
    }
    static uint32_t randomService(ClawCRTRandomContext *context, const ClawCRTRandomCall *q, void *p) {
        auto &r = *static_cast<Run *>(p);
        if (context->globals)
            r.put(0x52edd8, context->globals->tlsIndex);
        auto v = r.invoke(q->function, 0, q->arguments, q->argumentCount);
        if (context->globals)
            context->globals->tlsIndex = r.get(0x52edd8);
        return v;
    }
    void musicGlobals(ClawMusicContext &q, bool write) {
        if (!q.globals)
            fail();
        uint32_t values[3];
        if (write)
            std::memcpy(values, q.globals, 12);
        for (uint32_t i = 0; i < 3; ++i)
            if (write)
                put(0x54131c + 4 * i, values[i]);
            else
                values[i] = get(0x54131c + 4 * i);
        if (!write)
            std::memcpy(q.globals, values, 12);
    }
    bool dispatch(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n, uint32_t &v) {
        step();
        auto h = host();
        if (f == 0x4b8280) {
            if (n != 2)
                fail(2);
            v = 0;
            if (!a[0] || !get(a[0] + 4))
                return true;
            put(t + 4, a[0]);
            put(t + 8, get(a[0] + 8));
            put(t + 28, 0);
            timingToken = t;
            timingSync(false);
            ClawTimingHost th{this, timingRead, nullptr};
            claw_timing_reset_rate(&timing, 1, th);
            timingSync(true);
            claw_timing_reset_clock(&timingClock, th);
            timingSync(true);
            put(0x541338, 100);
            put(0x541334, 100);
            v = 1;
            return true;
        }
        if (c.archive) {
            if (!c.archive->table)
                fail();
            auto table = *c.archive->table;
            table.scene = h;
            table.byteContext = this;
            table.bytes = byteLookup;
            table.fault = 0;
            ClawCArrayContext allocator{};
            if (table.allocator) {
                allocator = *table.allocator;
                allocator.scene = h;
                allocator.fault = 0;
                table.allocator = &allocator;
            }
            auto q = *c.archive;
            q.table = &table;
            if (claw_resource_archive_loading_entry(f, t, a, n, &q, archiveService, this, &v)) {
                if (table.fault)
                    fail(table.fault);
                return true;
            }
            if (table.fault)
                fail(table.fault);
            if (claw_resource_table_construction_entry(f, t, a, n, &table, archiveService, this, &v)) {
                if (table.fault)
                    fail(table.fault);
                return true;
            }
            if (table.fault)
                fail(table.fault);
            ClawResourceNamespaceContext ns{};
            ns.scene = h;
            ns.maximumOperations = c.maximumOperations;
            if (claw_resource_namespace_entry(f, t, a, n, &ns, namespaceService, this, &v)) {
                if (ns.fault)
                    fail(ns.fault);
                return true;
            }
            if (ns.fault)
                fail(ns.fault);
            ClawResourceDataContext data{};
            data.scene = h;
            data.allocator = table.allocator;
            data.maximumOperations = c.maximumOperations;
            if (claw_resource_data_entry(f, t, a, n, &data, dataService, this, &v)) {
                if (data.fault)
                    fail(data.fault);
                return true;
            }
            if (data.fault)
                fail(data.fault);
        }
        if (c.graphics) {
            auto q = *c.graphics;
            q.scene = h;
            q.fault = 0;
            if (claw_scene_startup_composition_entry(f, t, a, n, &q, graphicsService, this, &v)) {
                if (q.fault)
                    fail(q.fault);
                return true;
            }
            if (q.fault)
                fail(q.fault);
        }
        if (c.players) {
            auto q = *c.players;
            q.scene = h;
            q.fault = 0;
            q.automaticToken = c.automaticToken + 896;
            if (claw_player_cache_application_entry(f, t, a, n, &q, playerService, this, &v)) {
                if (q.fault)
                    fail(q.fault);
                return true;
            }
            if (q.fault)
                fail(q.fault);
        }
        if (c.messages) {
            auto q = *c.messages;
            q.scene = h;
            q.fault = 0;
            if (claw_player_startup_entry(f, t, a, n, &q, messagesService, this, &v)) {
                if (q.fault)
                    fail(q.fault);
                return true;
            }
            if (q.fault)
                fail(q.fault);
        }
        if (c.fades && f == 0x4ebf80) {
            auto q = *c.fades;
            q.scene = h;
            q.fault = 0;
            if (!claw_player_fade_entry(f, t, a, n, &q, fadeService, this, &v) || q.fault)
                fail(q.fault ? q.fault : 1);
            return true;
        }
        if (c.light && (f == 0x4c61d0 || f == 0x4c6260)) {
            auto q = *c.light;
            q.scene = h;
            q.fault = 0;
            if (!claw_light_palette_entry(f, t, a, n, &q, lightService, this, &v) || q.fault)
                fail(q.fault ? q.fault : 1);
            return true;
        }
        if (c.ambient && (f == 0x4f5133 || f == 0x402240 || f == 0x402270 || f == 0x402520 || f == 0x402570)) {
            auto q = *c.ambient;
            q.scene = h;
            q.fault = 0;
            ClawEnemySpeechGlobals globals{};
            const uint32_t addresses[] = {0x5371fc, 0x537e88, 0x532c0c, 0x53c9a0, 0x53c9a4,
                                          0x53c9a8, 0x53c9ac, 0x53c9b0, 0x53720c};
            uint32_t values[9];
            for (uint32_t i = 0; i < 9; ++i)
                values[i] = get(addresses[i]);
            std::memcpy(&globals, values, 36);
            q.globals = &globals;
            q.masterVolume = get(0x532c10);
            ClawSoundTriggerArguments b{};
            if (n > 9)
                fail(2);
            b.count = n;
            std::copy_n(a, n, b.words);
            if (!claw_sound_trigger_entry(f, t, b, &q, ambientService, this, &v) || q.fault)
                fail(q.fault ? q.fault : 1);
            return true;
        }
        if (c.music && (f == 0x4b52a0 || f == 0x4b55e0)) {
            auto q = *c.music;
            q.scene = h;
            q.lookupBytes = byteLookup;
            q.fault = 0;
            musicGlobals(q, false);
            if (!claw_music_entry(f, t, a, n, &q, musicService, this, &v) || q.fault)
                fail(q.fault ? q.fault : 1);
            musicGlobals(q, true);
            return true;
        }
        if (c.random && f == 0x4a3040) {
            auto q = *c.random;
            q.host = h;
            q.fault = 0;
            if (q.globals)
                q.globals->tlsIndex = get(0x52edd8);
            if (!claw_crt_random_entry(f, a, n, &q, randomService, this, &v) || q.fault)
                fail(q.fault ? q.fault : 1);
            if (q.globals)
                put(0x52edd8, q.globals->tlsIndex);
            return true;
        }
        return false;
    }
    uint32_t invoke(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n) {
        uint32_t v = 0;
        return dispatch(f, t, a, n, v) ? v : external(f, t, a, n);
    }
    uint32_t invoke(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a = {}) {
        return invoke(f, t, a.begin(), uint32_t(a.size()));
    }
    uint32_t local(uint32_t f, uint32_t t, std::initializer_list<uint32_t> a, uint32_t mask,
                   std::initializer_list<std::pair<void *, uint32_t>> buffers) {
        ClawApplicationStartupCall q{};
        q.function = f;
        q.receiver = t;
        q.argumentCount = uint32_t(a.size());
        std::copy(a.begin(), a.end(), q.arguments);
        q.localMask = mask;
        q.bufferCount = uint32_t(buffers.size());
        uint32_t i = 0;
        for (auto b : buffers) {
            q.buffers[i] = b.first;
            q.bufferBytes[i++] = b.second;
        }
        return event(q);
    }
    uint32_t option(uint32_t app, uint32_t key, uint32_t fallback) {
        return invoke(0x4b5f30, get(app + 0x38), {key, fallback});
    }
    uint32_t error(uint32_t app, uint32_t code, uint32_t line) {
        invoke(0x429e10, app, {code, line});
        return 0;
    }
    uint32_t construct(uint32_t size, uint32_t ctor) {
        auto p = invoke(0x4f63ec, 0, {size});
        return p ? invoke(ctor, p) : 0;
    }
    uint32_t body(uint32_t app, const uint32_t *a) {
        const auto scratch = c.automaticToken;
        span(scratch, 300);
        if (!invoke(0x4b8280, app, {a[0], a[1]}))
            return error(app, 0x800a, 1000);
        auto time = invoke(0x546df0, 0);
        auto tick = invoke(0x546a24, 0);
        invoke(0x4a3040, 0, {(time + tick) >> 1});
        put(0x541338, 0x21);
        while (signedWord(invoke(0x546d54, 0, {0})) >= 0)
            step();
        auto config = invoke(0x4f63ec, 0, {540});
        if (config)
            put(config, 0);
        put(app + 0x38, config);
        if (!invoke(0x4b5c50, config, {0x5258b8, 0x524eec, 0x5258d0, 0, 0x80000002, 0}))
            return error(app, 0x800a, 0x3e9);
        put(app + 0x84, 640);
        put(app + 0x88, 480);
        put(app + 0x68, option(app, 0x5258a8, 10));
        put(app + 0x70, option(app, 0x52589c, 0));
        put(app + 0x74, option(app, 0x525890, 0));
        const uint32_t keys[] = {0x525880, 0x525874, 0x525860, 0x525850, 0x525840, 0x52582c, 0x525818,
                                 0x5257fc, 0x5257ec, 0x5257dc, 0x5257c8, 0x5257b4, 0x525798};
        const uint32_t globals[] = {0x525510, 0x525514, 0x525518, 0x537234, 0x537238, 0x53723c, 0x537240,
                                    0x537244, 0x537248, 0x53724c, 0x537250, 0x537254, 0x537258};
        for (uint32_t i = 0; i < 13; ++i)
            put(globals[i], option(app, keys[i], i < 3 ? 1 : 0));
        const uint32_t tuningKeys[] = {0x525784, 0x525770, 0x525758, 0x525744, 0x525730, 0x52571c};
        const uint32_t tuningGlobals[] = {0x52c6e4, 0x52c6e8, 0x52c6ec, 0x527134, 0x527130, 0x527138};
        for (uint32_t i = 0; i < 6; ++i)
            put(tuningGlobals[i], option(app, tuningKeys[i], get(tuningGlobals[i])));
        *bytes(scratch, 1) = 0;
        put(scratch + 892, 30);
        local(0x4b5e90, get(app + 0x38), {0x525714, 0, 0, 0}, 6, {{bytes(scratch, 32), 32}, {span(scratch + 892), 4}});
        auto music = option(app, 0x52570c, get(app + 20)), sound = option(app, 0x525704, get(app + 16)),
             voice = option(app, 0x5256fc, get(app + 0x118)), ambient = option(app, 0x5256f4, get(app + 0x11c)),
             interlaced = option(app, 0x5256e8, get(app + 0x120)), detail = option(app, 0x5256dc, get(app + 0x124)),
             front = option(app, 0x5256d0, get(app + 0x128)), musicVolume = option(app, 0x5256c0, 50),
             soundVolume = option(app, 0x5256b0, 80);
        put(app + 300, soundVolume);
        put(app + 0x70, get(app + 0x70) + 1);
        if (get(0x537244)) {
            put(0x537238, 1);
            put(0x537254, 1);
        }
        for (uint32_t off : {0xacu, 0xb0u, 0xd0u})
            put(app + off, 0);
        *bytes(app + 0xcc, 1) = 0;
        invoke(0x42b020, app);
        uint32_t state = 2, cmd = scratch + 32, userCmd = scratch + 332;
        if (a[1]) {
            copyString(cmd, a[1], 300);
            local(0x4f21e0, 0, {0}, 1, {{bytes(cmd, 300), 300}});
            auto find = [&](uint32_t token, uint32_t key) {
                return local(0x4a3990, 0, {0, key}, 1, {{bytes(token, 300), 300}});
            };
            if (find(cmd, 0x5256a8))
                state = 3;
            if (find(cmd, 0x5256a0))
                state = 4;
            if (find(cmd, 0x525698))
                state = 5;
            find(cmd, 0x525690);
            if (find(cmd, 0x52568c)) {
                state = 4;
                put(app + 0xb4, 1);
            }
            if (find(cmd, 0x525684)) {
                put(0x537250, 0);
                put(0x53724c, 0);
            }
            if (find(cmd, 0x52567c)) {
                put(0x537250, 0);
                put(0x53724c, 1);
            }
            if (find(cmd, 0x525674)) {
                copyString(userCmd, cmd, 300);
                auto p = find(userCmd, 0x525674); /*Transport returns source byte offset+1 for a local strstr result.*/
                if (p) {
                    auto off = p - 1;
                    if (off >= 300)
                        fail(2);
                    p = userCmd + off;
                    if (length(p) > 5) {
                        p += 5;
                        uint32_t n = 0;
                        while (*bytes(p + n, 1) && *bytes(p + n, 1) != ' ') {
                            step();
                            ++n;
                        }
                        *bytes(p + n, 1) = 0;
                        for (uint32_t i = 0; i < n; ++i)
                            if (*bytes(p + i, 1) == '_' || *bytes(p + i, 1) == '+')
                                *bytes(p + i, 1) = ' ';
                        copyString(scratch, p, 32);
                    }
                }
            }
        }
        if (invoke(0x42a680, app)) {
            state = 4;
            put(app + 0xb4, 0);
        }
        put(0x537070, get(get(app + 8) + 12));
        copyString(scratch + 632, a[1], c.pregraphicsSourceFrame ? 300 : 256);
        local(0x5028ec, 0, {get(get(app + 8) + 12), 0, 0, 1}, 4, {{bytes(scratch + 632, 256), 256}});
        invoke(0x4f650f, app + 0xc0);
        auto scene = construct(60, 0x4ce960);
        put(app + 0x30, scene);
        auto flags = get(0x537234) ? 5u : 1u;
        if (get(0x537254))
            flags |= 16;
        put(app + 0x78, get(0x53724c) ? 16 : 8);
        auto open = [&]() {
            auto s = get(app + 0x30);
            return invoke(get(get(s) + 24), s, {get(get(app + 4) + 4), 640, 480, get(app + 0x78), flags});
        };
        if (!open() && get(app + 0x78) != 8) {
            put(app + 0x78, 8);
            auto s = get(app + 0x30);
            invoke(get(get(s) + 28), s);
            if (!open()) {
                invoke(0x42c0b0, app, {0x3ea});
                return 0;
            }
            put(0x53724c, 0);
        }
        put(app + 0x7c, 640);
        put(app + 0x80, 480);
        invoke(0x4cf010, get(app + 0x30), {0x428bc0});
        auto tiles = get(get(app + 0x30) + 0x24);
        put(tiles + 100, 14);
        put(tiles + 104, 14);
        invoke(0x401000, 0, {get(app + 0x30)});
        if (!invoke(0x42cab0, app))
            return 0;
        auto old = get(app + 0x34);
        if (old) {
            invoke(0x4b7250, old);
            invoke(0x4f6428, 0, {old});
            put(app + 0x34, 0);
        }
        put(app + 0x34, construct(72, 0x4b7210));
        /*4268b0 returns a CString receiver. A source local result remains local.*/
        auto temp = scratch + 888;
        put(temp, get(app + 0x34));
        local(0x4268b0, app, {0}, 1, {{span(temp), 4}});
        auto opened = invoke(0x4b72e0, get(app + 0x34), {get(temp), 1, 0});
        local(0x4f6584, 0, {}, 256, {{span(temp), 4}});
        if (!opened) {
            if (!get(app + 0x104))
                return error(app, 0x800b, 0x3eb);
            if (!invoke(0x42ce90, app, {8}))
                return error(app, 0x8010, 0x3eb);
        }
        invoke(0x42c640, app, {get(app + 0x78)});
        auto folder = invoke(0x4b7f20, get(app + 0x34), {0x5254ec});
        auto resource = invoke(0x4b67f0, folder, {get(app + 0x9c) ? 0x525668u : 0x525660u, 0x494643});
        put(app + 0xf0, resource);
        if (resource)
            invoke(0x4b61c0, resource);
        resource = invoke(0x4b67f0, folder, {get(app + 0x9c) ? 0x525650u : 0x525644u, 0x494643});
        put(app + 0xf4, resource);
        if (resource)
            invoke(0x4b61c0, resource);
        auto p = invoke(0x4f63ec, 0, {8});
        if (p) {
            put(p, 0x50bf24);
            put(p + 4, 0);
        }
        put(app + 0x40, p);
        if (!invoke(0x493c20, p))
            return error(app, 0x800a, 0x3ec);
        p = construct(40, 0x4ebf80);
        put(app + 0x44, p);
        if (!invoke(0x4ec010, p, {0, 0, 0}))
            return error(app, 0x800a, 0x3ed);
        p = invoke(0x4f63ec, 0, {300});
        if (p) {
            invoke(0x4f5cbd, p + 4, {10});
            put(p, 0);
            *bytes(p + 32, 1) = 0;
            for (uint32_t off : {288u, 292u, 296u})
                put(p + off, 0);
        }
        put(app + 0x48, p);
        if (!invoke(0x422890, p, {get(get(app + 4) + 4)}))
            return error(app, 0x800a, 0x3ee);
        p = invoke(0x4f63ec, 0, {56});
        if (p) {
            invoke(0x4f5249, p, {10});
            invoke(0x4f6439, p + 28);
            put(p + 48, 0);
            put(p + 52, 0);
        }
        put(app + 0x4c, p);
        if (!invoke(0x4222a0, p, {5000, 2000}))
            return error(app, 0x800a, 0x3ef);
        if (!get(0x537234) && !get(0x537240) && invoke(0x48bbb0, 0)) {
            auto token = invoke(0x42b020, app);
            if (!invoke(0x48c030, 0, {token}))
                invoke(0x48bf70, 0);
        }
        p = invoke(0x4f63ec, 0, {44});
        if (p) {
            invoke(0x4f6118, p, {10});
            put(p + 28, 0);
            put(p + 32, 0);
            put(0x54131c, 0);
        }
        put(app + 0x50, p);
        if (!invoke(0x4b52a0, p, {get(get(app + 8) + 12), get(get(app + 4) + 4), 0}))
            return error(app, 0x800a, 0x449);
        if (!get(0x537234))
            invoke(0x4b55e0, get(app + 0x50), {musicVolume});
        else
            put(get(app + 0x50) + 40, 0);
        old = get(app + 0x5c);
        if (old) {
            invoke(0x402270, old);
            invoke(0x4f5192, old + 8);
            invoke(0x4f6428, 0, {old});
            put(app + 0x5c, 0);
        }
        p = invoke(0x4f63ec, 0, {48});
        if (p) {
            invoke(0x4f5133, p + 8, {10});
            put(p, 0);
            put(p + 4, 100);
        }
        put(app + 0x5c, p);
        if (!invoke(0x402240, p, {get(get(app + 0x30) + 40), soundVolume}))
            return error(app, 0x800a, 0x6af);
        if (!ambient) {
            if (get(p + 36)) {
                put(p + 36, 0);
                invoke(0x402520, p);
            }
        } else if (!get(p + 36)) {
            put(p + 36, 1);
            invoke(0x402570, p);
        }
        invoke(0x42cdc0, app, {soundVolume});
        auto inputFlags = get(0x53723c) ? 1u : 3u;
        p = invoke(0x4f63ec, 0, {584});
        if (p) {
            put(p, 0xffffffff);
            for (uint32_t off : {464u, 468u, 460u, 528u, 532u, 524u})
                put(p + off, 0);
            invoke(0x4b3410, p);
        }
        put(0x537200, p);
        if (!invoke(0x4b3240, p, {inputFlags, 0})) {
            auto saved = get(0x537200);
            if (saved) {
                invoke(0x4b3410, saved);
                invoke(0x4f6428, 0, {saved});
            }
            return error(app, 0x800a, 0x3f0);
        }
        p = get(0x537200);
        for (uint32_t i = 0; i < 4; ++i)
            put(p + 492 + 4 * i, i == 0 ? 32 : i == 1 ? 17 : i == 2 ? 18 : 16);
        if (get(0x537258))
            put(p + 472, 1);
        p = construct(24, 0x4c61d0);
        put(app + 0x58, p);
        if (!invoke(0x4c6260, p))
            return error(app, 0x800a, 0x6ae);
        p = invoke(0x4f63ec, 0, {144});
        if (p) {
            invoke(0x4f5cbd, p + 116, {10});
            put(p, 0);
        }
        put(0x537204, p);
        auto skip = option(app, 0x525624, 0);
        if (!invoke(0x430590, p, {get(0x537200), skip})) {
            auto saved = get(0x537204);
            if (saved) {
                put(saved, 0);
                invoke(0x4f5d00, saved + 116);
                invoke(0x4f6428, 0, {saved});
            }
            return error(app, 0x800a, 0x3f1);
        }
        if (!c.players)
            fail();
        auto players = *c.players;
        players.scene = host();
        players.automaticToken = scratch + 896;
        players.fault = 0;
        uint32_t reached = 0;
        if (!claw_player_cache_application_startup_span(app, scratch, &players, playerService, this, &reached) ||
            players.fault)
            fail(players.fault ? players.fault : 1);
        if (!reached)
            return 0;
        put(0x5371fc, app);
        put(0x537208, invoke(0x546df0, 0));
        put(0x53720c, 0);
        put(app + 20, music);
        put(app + 16, sound);
        put(0x532c0c, sound);
        put(app + 0x118, voice);
        put(app + 0x11c, ambient);
        put(app + 0x124, detail);
        put(app + 0x120, interlaced);
        invoke(0x42ce20, app, {front});
        if (!get(app + 0x9c) && !invoke(0x42a680, app)) {
            if (signedWord(get(app + 0x74)) < 1 || signedWord(get(app + 0x70)) < 2) {
                invoke(0x42b900, app);
                auto movie = invoke(0x42b140, app, {0});
                put(0x53ec58, movie);
                if (movie)
                    put(app + 0x74, get(app + 0x74) + 1);
            } else if (!option(app, 0x5255d4, 0))
                invoke(0x42b900, app);
        }
        if (state == 2 && option(app, 0x5255c0, 0))
            state = 5;
        if (!invoke(0x428c40, app, {state, 1, 0, 0})) {
            if (state != 4)
                return error(app, 0x8005, 0x3f4);
            if (!invoke(0x428c40, app, {2, 1, 0, 0}))
                return error(app, 0x8005, 0x3f3);
        }
        put(0x537208, invoke(0x546df0, 0));
        put(0x53720c, 0);
        if (get(get(0x5371fc) + 0x9c)) {
            for (uint32_t i = 0; i < 3; ++i) {
                float value = float(get(0x527130 + 4 * i) / 100u);
                uint32_t bits;
                std::memcpy(&bits, &value, 4);
                put(0x5262b0 + 4 * i, bits);
            }
        }
        return 1;
    }
};
} // namespace
extern "C" uint32_t claw_application_startup_entry(uint32_t f, uint32_t app, const uint32_t *a, uint32_t n,
                                                   ClawApplicationStartupContext *c, ClawApplicationStartupDependency d,
                                                   void *u, uint32_t *out) {
    if (f != 0x425730 || !c || !out || c->fault)
        return 0;
    if (n != 2 || !a) {
        c->fault = 2;
        return 0;
    }
    try {
        Run r{*c, d, u};
        *out = r.body(app, a);
        return 1;
    } catch (Failure &) {
        return 0;
    }
}
