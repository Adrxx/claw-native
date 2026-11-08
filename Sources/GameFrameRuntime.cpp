#include "GameFrameRuntime.h"
#include <algorithm>
#include <cstring>
#include <initializer_list>
namespace {
struct Run {
    ClawGameFrameContext *c;
    ClawGameFrameDependency d;
    void *user;
};
uint32_t entry(Run &, uint32_t, uint32_t);
uint32_t *span(Run &r, uint32_t t, uint32_t n) {
    if (!r.c->host.heap.lookup) {
        r.c->fault = 1;
        return nullptr;
    }
    auto *p = r.c->host.heap.lookup(r.c->host.heap.context, t, n);
    if (!p)
        r.c->fault = 1;
    return p;
}
uint32_t read(Run &r, uint32_t t) {
    auto *p = span(r, t, 1);
    return p ? *p : 0;
}
uint32_t service(Run &r, uint32_t f, uint32_t receiver, std::initializer_list<uint32_t> args = {}) {
    ClawGameFrameCall e{};
    e.function = f;
    e.receiver = receiver;
    e.argumentCount = uint32_t(args.size());
    std::copy(args.begin(), args.end(), e.arguments);
    if (r.d)
        return r.d(r.c, &e, r.user);
    if (r.c->host.heap.call) {
        ClawSceneActorCall c{};
        c.function = f;
        c.receiver = receiver;
        c.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, c.arguments);
        return r.c->host.heap.call(r.c->host.heap.context, c);
    }
    r.c->fault = 1;
    return 0;
}
void synchronize(Run &r) {
    if (r.c->camera && r.c->stage && r.c->actors) {
        r.c->camera->playerToken = r.c->stage->playerToken;
        r.c->camera->stageDelta = r.c->stage->stage.deltaMilliseconds;
        r.c->camera->animationNow = r.c->actors->animation.nowMilliseconds;
        r.c->camera->animationDelta = r.c->actors->animation.deltaMilliseconds;
    }
}
uint32_t *lookup(void *u, uint32_t token, uint32_t n) {
    return span(*static_cast<Run *>(u), token, n);
}
uint32_t allocate(void *u, uint32_t n) {
    auto &r = *static_cast<Run *>(u);
    if (!r.c->host.heap.allocate) {
        r.c->fault = 1;
        return 0;
    }
    return r.c->host.heap.allocate(r.c->host.heap.context, n);
}
void release(void *u, uint32_t token) {
    auto &r = *static_cast<Run *>(u);
    if (!r.c->host.heap.free) {
        r.c->fault = 1;
        return;
    }
    r.c->host.heap.free(r.c->host.heap.context, token);
}
uint32_t clock(void *u) {
    auto &r = *static_cast<Run *>(u);
    if (!r.c->host.heap.readClock) {
        r.c->fault = 1;
        return 0;
    }
    return r.c->host.heap.readClock(r.c->host.heap.context);
}
ClawSceneActorHost host(Run &);
uint32_t invoke(void *u, ClawSceneActorCall e) {
    auto &r = *static_cast<Run *>(u);
    uint32_t result = 0;
    if ((e.function == 0x46c860 || e.function == 0x486240) && r.c->composeCamera) {
        if (!r.c->camera || !r.c->stage || !r.c->actors) {
            r.c->fault = 1;
            return 0;
        }
        synchronize(r);
        ClawSceneCameraHost h = r.c->host;
        h.heap = host(r);
        const uint32_t receiver = e.function == 0x486240 ? e.arguments[0] : e.receiver;
        claw_scene_camera_entry(e.function, receiver, 0, 0, r.c->camera, h, &r.c->fault, &result);
        return result;
    }
    if ((e.function == 0x4d1fd0 || e.function == 0x4d2000) && r.c->composeSpatial) {
        ClawSpatialGridArguments a{};
        a.count = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, a.words);
        claw_spatial_grid_entry(e.function, e.receiver, a, host(r), &r.c->fault, &result);
        return result;
    }
    if (e.function == 0x46ac30 || e.function == 0x475dc0)
        return entry(r, e.function, e.receiver);
    if (r.d) {
        ClawGameFrameCall c{};
        c.function = e.function;
        c.receiver = e.receiver;
        c.argumentCount = e.argumentCount;
        std::copy_n(e.arguments, e.argumentCount, c.arguments);
        return r.d(r.c, &c, r.user);
    }
    if (!r.c->host.heap.call) {
        r.c->fault = 1;
        return 0;
    }
    return r.c->host.heap.call(r.c->host.heap.context, e);
}
ClawSceneActorHost host(Run &r) {
    return {&r, lookup, allocate, release, invoke, clock};
}
void runStage(Run &r, uint32_t owner) {
    if (!r.c->stage || !r.c->actors) {
        r.c->fault = 1;
        return;
    }
    const uint32_t delta = r.c->stage->stage.deltaMilliseconds;
    const bool sub = delta > 18 && delta < 100;
    if (r.c->composeStage)
        claw_scene_stage_run(owner, r.c->stage, r.c->actors, uint32_t(sub), host(r), &r.c->fault);
    else
        service(r, sub ? 0x46ad70 : 0x46ace0, owner);
}
uint32_t outer(Run &r, uint32_t fn, uint32_t owner) {
    if (fn == 0x475dc0) {
        service(r, 0x4774f0, owner);
        if (r.c->fault)
            return 0;
        service(r, 0x477840, owner);
        if (r.c->fault)
            return 0;
        service(r, 0x478290, owner, {0});
        if (r.c->fault)
            return 0;
    }
    runStage(r, owner);
    if (r.c->fault)
        return 0;
    uint32_t parent = read(r, owner + 0xc), map = read(r, parent + 0x24), plane = read(r, map + 0x5c);
    const uint32_t manager = read(r, owner + 4), bounds = read(r, manager + 0x5c), centerX = read(r, plane + 0x84),
                   centerY = read(r, plane + 0x88);
    if (r.c->fault)
        return 0;
    service(r, 0x4025c0, bounds, {centerX, centerY});
    if (r.c->fault)
        return 0;
    parent = read(r, owner + 0xc);
    map = read(r, parent + 0x24);
    uint32_t surface = read(r, parent + 4);
    const uint32_t imageTarget = read(r, surface + 0x14), actors = read(r, parent + 8);
    if (r.c->fault)
        return 0;
    service(r, 0x4cb9b0, map, {imageTarget, actors});
    if (r.c->fault)
        return 0;
    parent = read(r, owner + 0xc);
    surface = read(r, parent + 4);
    const uint32_t renderer = read(r, parent + 0xc), presentFunction = read(r, read(r, renderer) + 0x34),
                   presentTarget = read(r, surface + 0x14), presentArgument = read(r, surface + 0x18);
    if (r.c->fault)
        return 0;
    service(r, presentFunction, renderer, {presentTarget, presentArgument});
    if (r.c->fault)
        return 0;
    if (fn == 0x475dc0) {
        const uint32_t currentManager = read(r, owner + 4), config = read(r, currentManager + 0x4c);
        if (r.c->fault)
            return 0;
        service(r, 0x4224f0, config, {r.c->stage->stage.deltaMilliseconds});
        if (r.c->fault)
            return 0;
    }
    service(r, 0x46c2c0, owner);
    if (r.c->fault)
        return 0;
    parent = read(r, owner + 0xc);
    surface = read(r, parent + 4);
    const uint32_t device = read(r, surface + 0x10), target = read(r, device + 0x2c);
    if (r.c->fault)
        return 0;
    service(r, 0x4b98b0, target, {0});
    if (r.c->fault)
        return 0;
    parent = read(r, owner + 0xc);
    map = read(r, parent + 0x24);
    plane = read(r, map + 0x5c);
    if (r.c->fault)
        return 0;
    if (plane) {
        ClawSceneActorCall call{};
        call.function = 0x4d2000;
        call.receiver = plane;
        invoke(&r, call);
    }
    return r.c->fault ? 0 : 1;
}
uint32_t entry(Run &r, uint32_t fn, uint32_t receiver) {
    if (fn == 0x46ac30 || fn == 0x475dc0)
        return outer(r, fn, receiver);
    if (fn != 0x428b60)
        return 0;
    if (!r.c->clock || !r.c->stage || !r.c->actors || !r.c->host.heap.readClock) {
        r.c->fault = 1;
        return 0;
    }
    auto *manager = span(r, receiver, 45);
    if (!manager)
        return 0;
    static_assert(sizeof(ClawTimingManager) == 20, "Original manager timing view");
    auto *timing = reinterpret_cast<ClawTimingManager *>(manager + 0x18 / 4);
    ClawTimingHost h{&r, clock, nullptr};
    claw_timing_update(timing, r.c->clock, h);
    if (r.c->fault)
        return 0;
    claw_timing_publish_stage(r.c->clock, &r.c->stage->stage, &r.c->stage->accumulatedMilliseconds);
    synchronize(r);
    if (manager[0xb0 / 4])
        return 0;
    const uint32_t state = manager[0x2c / 4], callback = read(r, read(r, state) + 0x14);
    if (r.c->fault)
        return 0;
    if (callback == 0x46ac30 || callback == 0x475dc0)
        entry(r, callback, state);
    else
        service(r, callback, state);
    if (r.c->fault)
        return 0;
    if (manager[0x6c / 4] && manager[0x6c / 4] < 0x80000000)
        --manager[0x6c / 4];
    return 1;
}
} // namespace
void claw_game_frame_defaults(ClawGameFrameContext *c) {
    if (c)
        c->composeStage = c->composeCamera = c->composeSpatial = 1;
}
uint32_t claw_game_frame_entry(uint32_t function, uint32_t receiver, ClawGameFrameContext *c, ClawGameFrameDependency d,
                               void *user, uint32_t *result) {
    if (!c)
        return 0;
    if (function != 0x46ac30 && function != 0x475dc0 && function != 0x428b60)
        return 0;
    Run r{c, d, user};
    const uint32_t value = entry(r, function, receiver);
    synchronize(r);
    if (result)
        *result = value;
    return 1;
}
