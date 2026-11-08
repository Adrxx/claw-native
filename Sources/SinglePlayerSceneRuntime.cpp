#include "SinglePlayerSceneRuntime.h"
#include "WorldFileRuntime.h"
#include <initializer_list>
#include <cstring>
namespace {
struct Failure {};
struct Run {
    ClawSinglePlayerSceneContext &c;
    ClawSinglePlayerSceneDependency dependency;
    void *user;
    uint32_t *span(uint32_t t, uint32_t n = 1) {
        auto *p = c.host.lookup ? c.host.lookup(c.host.context, t, n) : nullptr;
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
    uint32_t method(uint32_t t, uint32_t slot) {
        return get(get(t) + slot);
    }
    uint32_t call(uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {}, uint32_t mask = 0,
                  std::initializer_list<void *> buffers = {}, std::initializer_list<uint32_t> sizes = {}) {
        if (f == 0x4bd250 || f == 0x4cdf20)
            return 1;
        if (f == 0x4cfa60) {
            auto *p = span(0x543108, 25);
            std::memset(p, 0, 100);
            p[0] = 100;
            return 1;
        }
        if (f == 0x4f5620 || f == 0x4f6118 || f == 0x4f5cbd)
            return collectionCtor(f, receiver, args.size() ? *args.begin() : 0);
        ClawSinglePlayerSceneCall e{};
        e.function = f;
        e.receiver = receiver;
        e.argumentCount = static_cast<uint32_t>(args.size());
        uint32_t i = 0;
        for (auto v : args)
            e.arguments[i++] = v;
        e.localMask = mask;
        i = 0;
        for (auto p : buffers)
            e.buffers[i++] = p;
        e.bufferCount = i;
        i = 0;
        for (auto n : sizes)
            e.bufferBytes[i++] = n;
        if (dependency)
            return dependency(&c, e, user);
        if (!mask && e.argumentCount <= 4 && c.host.call) {
            ClawSceneActorCall h{};
            h.function = f;
            h.receiver = receiver;
            h.argumentCount = e.argumentCount;
            for (i = 0; i < h.argumentCount; ++i)
                h.arguments[i] = e.arguments[i];
            return c.host.call(c.host.context, h);
        }
        c.fault = 2;
        throw Failure{};
    }
    uint32_t collectionCtor(uint32_t f, uint32_t t, uint32_t grow) {
        for (uint32_t off : {4u, 12u, 16u, 20u})
            put(t + off, 0);
        if (f == 0x4f5620) {
            put(t + 8, 0);
            put(t, 0x5107bc);
        } else {
            put(t, f == 0x4f6118 ? 0x5105c4 : 0x510054);
            put(t + 8, 17);
        }
        put(t + 24, grow);
        return t;
    }
    uint32_t applicationCtor(uint32_t t) {
        timingCtor(t);
        uint32_t empty = get(0x52e1cc);
        put(t + 0xc0, empty);
        put(t + 0xdc, 0x51079c);
        for (uint32_t off : {0xe0u, 0xecu, 0xe8u, 0xe4u})
            put(t + off, 0);
        for (uint32_t off : {0xf8u, 0xfcu, 0x100u})
            put(t + off, empty);
        put(t, 0x50bee4);
        for (uint32_t off :
             {0x2cu, 0x30u, 0x34u, 0x38u, 0x3cu, 0x40u, 0x44u, 0x48u,  0x4cu,  0x50u,  0x54u,  0x60u,  0x58u, 0x64u,
              0x8cu, 0xb8u, 0x5cu, 0x9cu, 0x94u, 0x98u, 0xa0u, 0xa4u,  0xa8u,  0xacu,  0xb0u,  0xb4u,  0xbcu, 0x6cu,
              0x70u, 0x74u, 0xc4u, 0x7cu, 0x80u, 0xf4u, 0xf0u, 0x104u, 0x10cu, 0x110u, 0x114u, 0x120u, 0x130u})
            put(t + off, 0);
        for (uint32_t off : {0x90u, 0x108u, 0x14u, 0x10u, 0x118u, 0x11cu, 0x124u, 0x128u})
            put(t + off, 1);
        put(t + 0x68, 2);
        put(t + 0xc8, 30);
        put(t + 0x78, 8);
        return t;
    }
    uint32_t timingCtor(uint32_t t) {
        put(t + 0x10, 1);
        put(t + 0x14, 1);
        put(t, 0x50bf04);
        put(t + 4, 0);
        put(t + 8, 0);
        put(t + 0xc, 0);
        auto *m = reinterpret_cast<ClawTimingManager *>(span(t + 0x18, 5));
        auto *clockState = reinterpret_cast<ClawClockState *>(span(0x541328, 5));
        ClawTimingHost h{this, clock, nullptr};
        claw_timing_initialize(m, clockState, h);
        return t;
    }
    void objectCtor(uint32_t t, uint32_t parent, uint32_t type, uint32_t flags) {
        put(t + 4, type);
        put(t, 0x50e924);
        put(t + 8, flags);
        put(t + 0xc, parent);
    }
    void sceneCtor(uint32_t t) {
        put(t, 0x513ab8);
        for (uint32_t off : {4u, 8u, 12u, 16u, 20u, 24u, 28u, 32u, 36u, 40u, 44u, 52u, 56u})
            put(t + off, 0);
        if (!c.camera) {
            c.fault = 1;
            throw Failure{};
        }
        c.camera->animationNow = c.camera->animationDelta = 0;
    }
    uint32_t worldCtor(uint32_t t, uint32_t parent, uint32_t type, uint32_t flags) {
        ClawCArrayContext arrays{};
        arrays.scene = host();
        ClawWorldFileContext world{host(), &arrays, c.composeSpatial, 0};
        ClawWorldFileArguments args{{parent, type, flags, 0}, 3};
        uint32_t result = 0;
        if (!claw_world_file_entry(0x4cace0, t, args, &world, nullptr, nullptr, &result) || world.fault) {
            c.fault = world.fault ? world.fault : 2;
            throw Failure{};
        }
        return result;
    }
    uint32_t sceneInit(uint32_t t, const uint32_t *args) {
        put(t + 0x30, args[0]);
        put(t + 0x34, args[4]);
        const uint32_t offsets[12] = {4, 8, 12, 16, 20, 24, 36, 40, 44, 28, 32, 0},
                       sizes[11] = {28, 44, 44, 44, 44, 104, 224, 52, 44, 2180, 128},
                       tables[9] = {0x513c68, 0x513c20, 0x513be8, 0x513b88, 0x513b60,
                                    0x513b28, 0x513938, 0x513b00, 0x513ad8};
        for (uint32_t i = 0; i < 11; ++i) {
            uint32_t token = call(0x4f63ec, 0, {sizes[i]});
            if (token) {
                if (i == 6)
                    worldCtor(token, t, 0, 0);
                else if (i == 9)
                    token = call(0x4bc120, token);
                else if (i == 10)
                    token = call(0x4b4710, token);
                else {
                    objectCtor(token, t, 0, 0);
                    if (i == 1 || i == 2)
                        call(0x4f5620, token + 16, {10});
                    else if (i == 3 || i == 4 || i == 5)
                        call(0x4f6118, token + 16, {10});
                    else if (i == 7 || i == 8)
                        call(0x4f5cbd, token + 16, {10});
                    if (i == 5) {
                        call(0x4f6118, token + 44, {10});
                        call(0x4f6118, token + 72, {10});
                    }
                    put(token, tables[i]);
                    if (i == 0) {
                        put(token + 16, 0);
                        put(token + 20, 0);
                        put(token + 24, 0);
                    }
                    if (i == 5)
                        put(token + 100, 0);
                    if (i == 7)
                        put(token + 44, 0);
                }
            }
            put(t + offsets[i], token);
        }
        const uint32_t initOffsets[6] = {8, 12, 16, 20, 24, 44};
        for (uint32_t i = 0; i < 6; ++i) {
            uint32_t object = get(t + initOffsets[i]);
            if (!call(method(object, 24), object)) {
                if (!get(t + 56))
                    put(t + 56, 1001 + i);
                return 0;
            }
        }
        uint32_t world = get(t + 36), fn = method(world, 52), result = 0;
        if (c.composeSpatial && fn == 0x4cb040) {
            ClawSpatialGridArguments a{};
            a.count = 2;
            a.words[0] = args[1];
            a.words[1] = args[2];
            uint32_t fault = 0;
            claw_spatial_grid_entry(fn, world, a, host(), &fault, &result);
            if (fault) {
                c.fault = fault;
                throw Failure{};
            }
        } else
            result = call(fn, world, {args[1], args[2]});
        if (!result) {
            if (!get(t + 56))
                put(t + 56, 1007);
            return 0;
        }
        uint32_t surface = get(t + 4);
        if (!call(method(surface, 36), surface, {args[1], args[2], args[3], args[4]})) {
            if (!get(t + 56))
                put(t + 56, 1008);
            return 0;
        }
        uint32_t audio = get(t + 32);
        if (!call(0x4b47e0, audio, {args[0], 1})) {
            if (get(t + 32)) {
                audio = get(t + 32);
                call(method(audio, 0), audio, {1});
            }
            put(t + 32, 0);
            if (args[4] & 8) {
                if (!get(t + 56))
                    put(t + 56, 1009);
                return 0;
            }
        }
        audio = get(t + 32);
        if (audio && (args[4] & 4)) {
            call(method(audio, 0), audio, {1});
            put(t + 32, 0);
        }
        if (!call(0x4ca280, get(t + 40), {1})) {
            if (!get(t + 56))
                put(t + 56, 1010);
            return 0;
        }
        return 1;
    }
    uint32_t manager(uint32_t owner) {
        return get(owner + 4);
    }
    uint32_t scene(uint32_t owner) {
        return get(owner + 0xc);
    }
    uint32_t scenePart(uint32_t owner, uint32_t offset) {
        return get(scene(owner) + offset);
    }
    void reset() {
        for (auto &v : c.globals->resetFlags)
            v = 0;
    }
    uint32_t viewport(uint32_t t) {
        return get(t + 0x7c) == 640 && get(t + 0x80) == 480;
    }
    uint32_t savedPath(uint32_t managerToken) {
        uint32_t temp = 0;
        call(0x4f6449, 0, {managerToken + 0xc0}, 256, {&temp}, {4});
        return temp;
    }
    uint32_t decodedLevel(uint32_t m) {
        return call(0x436e60, 0, {savedPath(m)});
    }
    void cursor() {
        while (static_cast<int32_t>(call(0x546d54, 0, {0})) >= 0) {
        }
    }
    void progress(uint32_t owner, uint32_t p) {
        call(0x46dff0, owner, {p});
    }
    void baseCtor(uint32_t t) {
        put(t, 0x50b4ec);
        for (uint32_t off : {4u, 8u, 12u, 0x1cu, 0x20u, 0x24u, 0x2cu, 0x30u, 0x3cu, 0x40u, 0x34u})
            put(t + off, 0);
        *reinterpret_cast<uint8_t *>(span(t + 0x4c)) = 0;
        put(t + 0x18, 0);
        put(t + 0x150, 0);
    }
    void construct(uint32_t t) {
        baseCtor(t);
        put(t + 0x250, get(0x52e1cc));
        put(t, 0x50c264);
        put(t + 0x154, 1);
        for (uint32_t off : {0x258u, 0x25cu, 0x764u, 0x768u, 0x76cu, 0x770u, 0x774u})
            put(t + off, 0);
    }
    void formatLevel(char *out, uint32_t level) {
        call(0x4a3920, 0, {0, 0x52a004, level}, 1, {out}, {32});
    }
    uint32_t lookupLevel(uint32_t owner, uint32_t level) {
        char name[32]{};
        formatLevel(name, level);
        uint32_t resource = call(0x4b7f20, get(owner + 8), {0}, 1, {name}, {32});
        put(owner + 0x1c, resource);
        return resource;
    }
    uint32_t baseInit(uint32_t t, uint32_t m, uint32_t level, uint32_t parameter) {
        put(t + 4, m);
        put(t + 8, get(m + 0x34));
        put(t + 0xc, get(m + 0x30));
        put(t + 0x10, get(m + 0x44));
        put(t + 0x14, level);
        put(t + 0x18, parameter);
        put(t + 0x44, 0xffffffff);
        put(t + 0x48, 0xffffffff);
        put(t + 0x14c, 0);
        put(t + 0x2c, 0);
        put(t + 0x150, 0);
        call(0x4a3920, 0, {t + 0x4c, 0x52c69c, c.globals->buildNumber}, 0, {span(t + 0x4c, 65)}, {260});
        uint32_t resource = lookupLevel(t, get(t + 0x14));
        if (resource)
            put(t + 0x34, 1);
        return resource ? 1 : 0;
    }
    uint32_t initialize(uint32_t t, uint32_t m, uint32_t level, uint32_t parameter) {
        if (!m)
            return 0;
        if (get(get(m + 0xc0) - 8)) {
            level = decodedLevel(m);
            if (static_cast<int32_t>(level) <= 0)
                return 0;
            put(t + 0x258, 1);
            put(m + 0x130, 1);
        } else {
            put(m + 0x130, 0);
            put(t + 0x258, 0);
        }
        uint32_t success = c.composeBase ? baseInit(t, m, level, parameter) : call(0x48f0d0, t, {m, level, parameter});
        if (!success)
            return 0;
        cursor();
        put(t + 0x38, 0);
        for (uint32_t off : {0x25cu, 0x770u, 0x76cu, 0x768u})
            put(t + off, 0);
        reset();
        put(get(m + 0x48) + 0x128, 0);
        put(t + 0x760, 0);
        if (!viewport(manager(t)))
            call(0x42a000, manager(t), {0});
        uint32_t resource = call(0x4b7f20, get(t + 8), {0x523734});
        put(t + 0x24, resource);
        if (!resource)
            return 0;
        resource = call(0x4b7f20, get(t + 8), {0x5254ec});
        put(t + 0x28, resource);
        if (!resource)
            return 0;
        success = c.composeLevel ? levelStart(t, level) : call(0x46aeb0, t, {level, 1});
        if (success)
            put(t + 0x15c, get(manager(t) + 0x9c) ? 180000 : 3600000);
        return success ? 1 : 0;
    }
    static uint32_t *lookup(void *p, uint32_t token, uint32_t words) {
        return static_cast<Run *>(p)->span(token, words);
    }
    static uint32_t allocate(void *p, uint32_t n) {
        auto &r = *static_cast<Run *>(p);
        if (!r.c.host.allocate) {
            r.c.fault = 2;
            throw Failure{};
        }
        return r.c.host.allocate(r.c.host.context, n);
    }
    static void release(void *p, uint32_t t) {
        auto &r = *static_cast<Run *>(p);
        if (!r.c.host.free) {
            r.c.fault = 2;
            throw Failure{};
        }
        r.c.host.free(r.c.host.context, t);
    }
    static uint32_t invoke(void *p, ClawSceneActorCall a) {
        auto &r = *static_cast<Run *>(p);
        switch (a.argumentCount) {
        case 0:
            return r.call(a.function, a.receiver);
        case 1:
            return r.call(a.function, a.receiver, {a.arguments[0]});
        case 2:
            return r.call(a.function, a.receiver, {a.arguments[0], a.arguments[1]});
        case 3:
            return r.call(a.function, a.receiver, {a.arguments[0], a.arguments[1], a.arguments[2]});
        default:
            return r.call(a.function, a.receiver, {a.arguments[0], a.arguments[1], a.arguments[2], a.arguments[3]});
        }
    }
    static uint32_t clock(void *p) {
        auto &r = *static_cast<Run *>(p);
        if (!r.c.host.readClock) {
            r.c.fault = 2;
            throw Failure{};
        }
        return r.c.host.readClock(r.c.host.context);
    }
    ClawSceneActorHost host() {
        return {this, lookup, allocate, release, invoke, clock};
    }
    static uint32_t platform(void *p, ClawSceneCameraPlatformCall a) {
        auto &r = *static_cast<Run *>(p);
        switch (a.argumentCount) {
        case 0:
            return r.call(a.importSlot, 0);
        case 1:
            return r.call(a.importSlot, 0, {a.arguments[0]});
        case 2:
            return r.call(a.importSlot, 0, {a.arguments[0], a.arguments[1]});
        case 3:
            return r.call(a.importSlot, 0, {a.arguments[0], a.arguments[1], a.arguments[2]});
        default:
            return r.call(a.importSlot, 0, {a.arguments[0], a.arguments[1], a.arguments[2], a.arguments[3]});
        }
    }
    void camera(uint32_t fn, uint32_t t) {
        if (!c.composeCamera) {
            call(fn, t);
            return;
        }
        if (!c.camera) {
            c.fault = 1;
            throw Failure{};
        }
        auto &g = *c.globals;
        c.camera->playerToken = g.playerToken;
        c.camera->inputMappingToken = g.inputMappingToken;
        c.camera->forcedX = g.forcedX;
        c.camera->forcedY = g.forcedY;
        ClawSceneCameraHost h{host(), this, platform};
        uint32_t fault = 0, result = 0;
        claw_scene_camera_entry(fn, t, 0, 0, c.camera, h, &fault, &result);
        if (fault) {
            c.fault = fault;
            throw Failure{};
        }
        g.forcedX = c.camera->forcedX;
        g.forcedY = c.camera->forcedY;
    }
    void spatial(uint32_t fn, uint32_t t) {
        if (!c.composeSpatial) {
            call(fn, t);
            return;
        }
        ClawSpatialGridArguments a{};
        uint32_t fault = 0, result = 0;
        claw_spatial_grid_entry(fn, t, a, host(), &fault, &result);
        if (fault) {
            c.fault = fault;
            throw Failure{};
        }
    }
    void music(uint32_t owner, uint32_t group, uint32_t variant, uint32_t alternate, uint32_t normal, uint32_t tag) {
        uint32_t resource = 0;
        if (!variant)
            resource = call(0x4b67f0, group, {alternate, 0x584d49});
        if (!resource)
            resource = call(0x4b67f0, group, {normal, 0x584d49});
        if (resource) {
            uint32_t data = call(0x4b61c0, resource);
            if (data)
                call(0x4b53f0, get(manager(owner) + 0x50), {data, get(resource + 0x14), tag});
        }
    }
    uint32_t levelStart(uint32_t t, uint32_t level) {
        auto &g = *c.globals;
        put(t + 0x14, level);
        g.lootInitialized = 0;
        g.imageLoading = 0;
        put(t + 0x44, 0xffffffff);
        put(t + 0x48, 0xffffffff);
        put(t + 0x764, 0);
        g.accumulatedTick = g.word53c9c0 = g.word5349dc = 0;
        call(0x4a3040, 0, {0x1b3cf});
        if (!viewport(manager(t)))
            call(0x42a000, manager(t), {0});
        uint32_t m = manager(t);
        if (get(get(m + 0xc0) - 8)) {
            level = decodedLevel(m);
            if (level != get(t + 0x14)) {
                call(0x4f650f, manager(t) + 0xc0);
                put(t + 0x258, 0);
            }
        }
        if (!lookupLevel(t, get(t + 0x14)))
            return 0;
        uint32_t resource = call(0x4b7dc0, get(t + 0x1c), {0x529ff4, 0x50414c});
        if (!resource)
            return 0;
        if (get(t + 0x2c)) {
            call(0x4d46f0, scenePart(t, 0x18), {get(t + 0x2c)});
            put(t + 0x2c, 0);
        }
        uint32_t controller = scenePart(t, 0x18),
                 palette = call(method(controller, 0x24), controller, {resource, 0, 0});
        put(t + 0x2c, palette);
        if (!palette)
            return 0;
        uint32_t iface = get(get(palette + 0x10) + 4);
        call(method(iface, 0x10), 0, {iface, 0, 0, 256, t + 0x360}, 0, {span(t + 0x360, 256)}, {1024});
        call(0x4bb870, get(get(t + 0x2c) + 0x10));
        call(0x4bb990, get(get(t + 0x2c) + 0x10), {0, 256, 0, 0, 0, 250});
        uint32_t surface = scenePart(t, 4);
        call(0x4b97c0, get(get(surface + 0x14) + 0x2c), {0});
        call(0x4b98b0, get(get(surface + 0x10) + 0x2c), {0});
        palette = get(t + 0x2c);
        put(scenePart(t, 0x18) + 0x64, palette);
        call(method(palette, 0x34), palette);
        call(0x4bb910, get(get(t + 0x2c) + 0x10), {0, 256, 0, 0, 0, 0});
        call(0x46db30, t);
        uint32_t oldResource = get(t + 0x20);
        put(t + 0x20, get(t + 0x1c));
        call(0x546ccc, 0, {get(get(manager(t) + 4) + 4)});
        call(0x48f3e0, t, {0x529fec, 1, 1, 1, 0});
        call(0x46f040, t);
        cursor();
        put(t + 0x20, oldResource);
        call(0x46e100, t);
        call(0x46b7b0, t);
        progress(t, 5);
        call(0x46bb80, t);
        progress(t, 10);
        if (!call(0x46e160, t))
            return 0;
        progress(t, 15);
        g.imageLoading = 0;
        resource = call(0x4b7cd0, get(t + 0x1c), {0x529fe4});
        if (!resource)
            return 0;
        controller = scenePart(t, 0x10);
        call(method(controller, 0x48), controller, {resource, 0x534938, 0x523728});
        progress(t, 20);
        const uint32_t sources[3] = {0x1c, 0x24, 0x28}, prefixes[3] = {0x524d80, 0x523734, 0x5254ec};
        for (uint32_t i = 0; i < 3; ++i) {
            resource = call(0x4b7cd0, get(t + sources[i]), {0x52372c});
            if (!resource)
                return 0;
            call(0x4ca440, scenePart(t, 0x28), {resource, prefixes[i], 0x523728});
            progress(t, 25 + 5 * i);
        }
        for (uint32_t i = 0; i < 3; ++i) {
            g.imageLoading = 1;
            resource = call(0x4b7cd0, get(t + sources[i]), {0x523ce0});
            if (!resource)
                return 0;
            controller = scenePart(t, 0x10);
            call(method(controller, 0x48), controller, {resource, prefixes[i], 0x523728});
            g.imageLoading = 0;
            progress(t, 40 + 10 * i);
            resource = call(0x4b7cd0, get(t + sources[i]), {0x523cd8});
            if (!resource)
                return 0;
            call(0x4ce0d0, scenePart(t, 0x2c), {resource, prefixes[i], 0x523728});
            progress(t, 45 + 10 * i);
        }
        call(0x42abf0, manager(t));
        m = manager(t);
        uint32_t world = scenePart(t, 0x24), success;
        if (get(get(m + 0xc0) - 8)) {
            uint32_t temp = savedPath(m);
            success = call(method(world, 0x40), world, {temp});
            call(0x4f6584, 0, {}, 256, {&temp}, {4});
        } else {
            resource = call(0x4b7dc0, get(t + 0x1c), {0x529fd4, 0x575744});
            if (!resource)
                return 0;
            world = scenePart(t, 0x24);
            success = call(method(world, 0x3c), world, {resource});
        }
        if (!success)
            return 0;
        call(0x4cdcb0, scenePart(t, 0x24));
        progress(t, 70);
        call(0x42ae70, manager(t));
        if (!call(0x452b00, 0, {level}))
            return 0;
        progress(t, 75);
        g.playerToken = call(0x4c8da0, scenePart(t, 8), {1, 320, 350, 100, 0x522e80, 0x40002});
        if (!g.playerToken)
            return 0;
        if (get(t + 0x154)) {
            put(t + 0x154, 0);
            call(0x415ce0, 0);
            call(0x46c790, t);
            call(0x46d8e0, t);
        } else
            g.word534ca4 = 0;
        uint32_t player = g.playerToken;
        call(get(get(player + 0x6c) + 0x10), 0, {player});
        progress(t, 80);
        call(0x4c8b90, scenePart(t, 8), {0, 9999, 0x522e3c, 0});
        g.forcedX = g.forcedY = 0xffffffff;
        camera(0x486d30, 0);
        call(0x4c8f60, scenePart(t, 8), {0, 0, 0, 9999, 0x52297c, 0x200000});
        call(0x4c8da0, scenePart(t, 8), {0, 0, 0, 1000, 0x5223cc, 0x40000});
        call(0x4c8da0, scenePart(t, 8), {0, 0, 0, 1000, 0x5223b8, 0x40000});
        if (get(manager(t) + 0x9c))
            call(0x4c8da0, scenePart(t, 8), {0, 0, 0, 9999, 0x522828, 0x200000});
        call(0x4719e0, 0, {scene(t)});
        uint32_t screenSize[2]{};
        call(0x42a450, manager(t), {0}, 1, {screenSize}, {8});
        if (static_cast<int32_t>(screenSize[1]) > 0) {
            surface = scenePart(t, 4);
            call(0x4b97c0, get(get(surface + 0x14) + 0x2c), {0});
        }
        progress(t, 85);
        camera(0x431300, g.inputMappingToken);
        cursor();
        call(0x42abf0, manager(t));
        put(t + 0x158, 0);
        call(0x46caf0, t);
        progress(t, 90);
        if (!get(manager(t) + 0x124))
            call(0x46ef80, t);
        uint32_t plane = get(scenePart(t, 0x24) + 0x5c);
        if (plane)
            spatial(0x4d2030, plane);
        plane = get(scenePart(t, 0x24) + 0x5c);
        if (plane)
            spatial(0x4d1fd0, plane);
        progress(t, 95);
        uint32_t variant = call(0x48bfd0, 0);
        call(0x4b5340, get(manager(t) + 0x50));
        uint32_t group = call(0x4b7cd0, get(t + 0x1c), {0x526a58});
        if (group) {
            music(t, group, variant, 0x529fcc, 0x5256a8, 0x524d80);
            music(t, group, variant, 0x529fc4, 0x529fbc, 0x529fbc);
        }
        group = call(0x4b7cd0, get(t + 0x28), {0x526a58});
        if (group) {
            music(t, group, variant, 0x529fb0, 0x524d78, 0x524d78);
            music(t, group, 1, 0, 0x525948, 0x525948);
        }
        call(0x4b8910, get(manager(t) + 4), {256, 64});
        progress(t, 100);
        call(0x4b8960, 0, {200});
        return 1;
    }
};
} // namespace
extern "C" void claw_single_player_scene_defaults(ClawSinglePlayerSceneContext *c) {
    if (c)
        c->composeBase = c->composeLevel = c->composeCamera = c->composeSpatial = 1;
}
extern "C" uint32_t claw_single_player_scene_construct(uint32_t t, ClawSinglePlayerSceneContext *c,
                                                       ClawSinglePlayerSceneDependency d, void *u) {
    if (!c)
        return 0;
    c->fault = 0;
    Run r{*c, d, u};
    try {
        r.construct(t);
    } catch (Failure &) {
        return 0;
    }
    return t;
}
extern "C" uint32_t claw_single_player_scene_entry(uint32_t f, uint32_t t, const uint32_t *a, uint32_t n,
                                                   ClawSinglePlayerSceneContext *c, ClawSinglePlayerSceneDependency d,
                                                   void *u, uint32_t *out) {
    if (f != 0x40b5c0 && f != 0x48f0d0 && f != 0x46a6d0 && f != 0x46aeb0 && f != 0x42af50 && f != 0x42aa50 &&
        f != 0x4ce960 && f != 0x4cace0 && f != 0x45fde0 && f != 0x4cea10 && f != 0x4f5620 && f != 0x4f6118 &&
        f != 0x4f5cbd && f != 0x4bd250 && f != 0x4cdf20 && f != 0x4cfa60 && f != 0x4254a0 && f != 0x4b8240)
        return 0;
    if (out)
        *out = 0;
    if (!c || !c->globals)
        return 1;
    c->fault = 0;
    if ((f == 0x48f0d0 || f == 0x46a6d0 || f == 0x4cace0 || f == 0x45fde0) && (n != 3 || !a)) {
        c->fault = 3;
        return 1;
    }
    if (f == 0x46aeb0 && (n != 2 || !a)) {
        c->fault = 3;
        return 1;
    }
    if (f == 0x4cea10 && (n != 5 || !a)) {
        c->fault = 3;
        return 1;
    }
    if ((f == 0x4f5620 || f == 0x4f6118 || f == 0x4f5cbd) && (n != 1 || !a)) {
        c->fault = 3;
        return 1;
    }
    Run r{*c, d, u};
    uint32_t result = 0;
    try {
        if (f == 0x4f5620 || f == 0x4f6118 || f == 0x4f5cbd)
            result = r.collectionCtor(f, t, a[0]);
        else if (f == 0x4254a0)
            result = r.applicationCtor(t);
        else if (f == 0x4b8240)
            result = r.timingCtor(t);
        else if (f == 0x4bd250 || f == 0x4cdf20 || f == 0x4cfa60)
            result = r.call(f, t);
        else if (f == 0x4ce960) {
            r.sceneCtor(t);
            result = t;
        } else if (f == 0x4cace0)
            result = r.worldCtor(t, a[0], a[1], a[2]);
        else if (f == 0x45fde0)
            r.objectCtor(t, a[0], a[1], a[2]);
        else if (f == 0x4cea10)
            result = r.sceneInit(t, a);
        else if (f == 0x40b5c0) {
            r.baseCtor(t);
            result = t;
        } else if (f == 0x48f0d0)
            result = r.baseInit(t, a[0], a[1], a[2]);
        else if (f == 0x46a6d0)
            result = r.initialize(t, a[0], a[1], a[2]);
        else if (f == 0x46aeb0)
            result = r.levelStart(t, a[0]);
        else if (f == 0x42af50)
            result = r.viewport(t);
        else
            r.reset();
    } catch (Failure &) {
    }
    if (out)
        *out = result;
    return 1;
}
