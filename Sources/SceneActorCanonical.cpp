#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4c8be0:
    case 0x4c8da0:
        return 6;
    case 0x4c8fc0:
    case 0x4c9320:
    case 0x4c9860:
        return 1;
    case 0x46ace0:
    case 0x46ad70:
        return 0;
    default:
        return -1;
    }
}

// Scene +0x14 list head, node +0x08 actor; actor +0x64 priority,
// +0x08 flags, +0x68 list position. Creation/reorder test the flags byte.
uint32_t insertPosition(Run &run, uint32_t scene, uint32_t actor, bool byteFlags) {
    uint32_t node = run.get(scene + 0x14);
    uint32_t priority = run.get(actor + 0x64);
    while (node) {
        uint32_t next = run.get(node);
        uint32_t other = run.get(node + 0x08);
        if (s32(run.get(other + 0x64)) > s32(priority)) {
            bool skip = byteFlags ? (run.get8(other + 0x0a) & 2) != 0 : (run.get(other + 0x08) & 0x20000) != 0;
            if (!skip)
                return run.call(0x4f572a, scene + 0x10, {node, actor});
        }
        node = next;
    }
    return run.call(0x4f51c5, scene + 0x10, {actor});
}

// 0x4c9860. Service +0x20 pending timer.
uint32_t function_4c9860(Run &run, uint32_t service, uint32_t elapsed) {
    uint32_t timer = run.get(service + 0x20);
    if (!timer)
        return 0;
    if (elapsed >= timer) {
        run.put(service + 0x20, 0);
        return 0;
    }
    run.put(service + 0x20, timer - elapsed);
    return 1;
}

// 0x4c8be0. Actor construction followed by initialization and scheduling.
uint32_t function_4c8be0(Run &run, uint32_t scene, const uint32_t *args) {
    uint32_t actor = run.call(0x4f63ec, 0, {0x1b4});
    if (actor) {
        uint32_t context = run.get(scene + 0x0c);
        run.call(0x4c9780, actor, {context, args[0], args[5]});
        run.call(0x4c96c0, actor + 0x88);
        run.call(0x4c9690, actor + 0xa4);
        run.put(actor, 0x513770);
        run.put(actor + 0x4c, 0x80000000);
        run.put(actor + 0x68, 0);
        uint32_t service = run.call(0x4f63ec, 0, {0x174});
        if (service)
            service = run.call(0x4c9830, service, {context, args[0], 0});
        run.put(actor + 0x6c, service);
        run.put(actor + 0x84, 0);
        run.put(actor + 0x80, 0);
        run.put(actor + 0x70, 0);
        run.put(actor + 0x78, 0);
        run.call(0x4c9ba0, actor + 0x188);
        run.put(actor, 0x5137f0);
        run.put(actor + 0x168, 0xffffffff);
        run.put(actor + 0x16c, 0xffffffff);
        run.put(actor + 0x174, 0);
        run.put(actor + 0x170, 0);
        run.put(actor + 0x178, 0);
        run.put(actor + 0x17c, 0);
        run.put(actor + 0x180, 0);
        run.put(actor + 0x184, 0);
    }
    if (!run.vcall(actor, 0x28, {args[1], args[2], args[3], args[4]})) {
        if (actor)
            run.vcall(actor, 0x04, {1});
        return 0;
    }
    uint32_t position = insertPosition(run, scene, actor, true);
    run.put(actor + 0x68, position);
    if (args[5] & 0x200000)
        run.call(run.get(run.get(actor + 0x6c) + 0x10), 0, {actor});
    return actor;
}

// 0x4c8da0. Lookup writes its result into an entry-relative stack local.
uint32_t function_4c8da0(Run &run, uint32_t scene, const uint32_t *args) {
    uint32_t local = run.automatic(-4);
    run.put(local, 0);
    uint32_t map = run.get(run.get(scene + 0x0c) + 0x14) + 0x10;
    run.call(0x4f6286, map, {args[4], local});
    uint32_t result = run.get(local);
    if (!result)
        return 0;
    uint32_t forwarded[] = {args[0], args[1], args[2], args[3], result, args[5]};
    return function_4c8be0(run, scene, forwarded);
}

// 0x4c9320. Insert an existing actor using the full flags word.
uint32_t function_4c9320(Run &run, uint32_t scene, uint32_t actor) {
    uint32_t position = insertPosition(run, scene, actor, false);
    run.put(actor + 0x68, position);
    return 0;
}

// 0x4c8fc0. Service +0x10 callback, +0x24 skipped updates,
// +0x1c notification reason; actor +0x6c service.
uint32_t function_4c8fc0(Run &run, uint32_t scene, uint32_t timestamp) {
    if (!(run.get8(0x5430d0) & 1)) {
        run.put8(0x5430d0, run.get8(0x5430d0) | 1);
        run.call(0x4f58ab, 0x5430f0);
        run.call(0x4a35f0, 0, {0x4c91c0});
    }
    if (!(run.get8(0x5430d0) & 2)) {
        run.put8(0x5430d0, run.get8(0x5430d0) | 2);
        run.call(0x4f58ab, 0x5430d8);
        run.call(0x4a35f0, 0, {0x4c91b0});
    }
    run.call(0x4f5915, 0x5430f0, {0, 0xffffffff});
    run.call(0x4f5915, 0x5430d8, {0, 0xffffffff});
    if (timestamp) {
        uint32_t now = run.icall(0x546df0);
        uint32_t delta = now - run.get(0x5430c8);
        run.put(0x5430c8, now);
        run.put(0x5430c4, delta);
    }
    uint32_t node = run.get(scene + 0x14);
    while (node) {
        uint32_t next = run.get(node);
        uint32_t actor = run.get(node + 0x08);
        uint32_t service = run.get(actor + 0x6c);
        if (!function_4c9860(run, service, run.get(0x5430c4))) {
            uint32_t skip = run.get(service + 0x24);
            if (skip) {
                run.put(service + 0x24, skip - 1);
            } else {
                run.call(run.get(service + 0x10), 0, {actor});
            }
        }
        uint32_t flags = run.get(actor + 0x08);
        if (flags & 0x10000) {
            run.call(0x4f582f, 0x5430f0, {run.get(0x5430f8), actor});
        } else if (flags & 0x20000) {
            run.call(0x4f582f, 0x5430d8, {run.get(0x5430e0), actor});
        }
        node = next;
    }
    for (uint32_t index = 0; s32(index) < s32(run.get(0x5430f8)); ++index) {
        uint32_t actor = run.get(run.get(0x5430f4) + index * 4);
        if (run.get(actor + 0x08) & 0x80000) {
            uint32_t service = run.get(actor + 0x6c);
            run.put(service + 0x1c, 0x1d);
            run.call(run.get(service + 0x10), 0, {actor});
        }
        run.call(0x4f5212, scene + 0x10, {run.get(actor + 0x68)});
        if (actor)
            run.vcall(actor, 0x04, {1});
    }
    for (uint32_t index = 0; s32(index) < s32(run.get(0x5430e0)); ++index) {
        uint32_t actor = run.get(run.get(0x5430dc) + index * 4);
        uint32_t position = run.get(actor + 0x68);
        run.put(actor + 0x08, run.get(actor + 0x08) & 0xfffdffff);
        run.call(0x4f5212, scene + 0x10, {position});
        position = insertPosition(run, scene, actor, true);
        run.put(actor + 0x68, position);
    }
    return 0;
}

// Stage +0x0c context; context +0x24 subcontext, +0x08 renderer;
// subcontext +0x5c optional effect.
uint32_t effect(Run &run, uint32_t stage) {
    return run.get(run.get(run.get(stage + 0x0c) + 0x24) + 0x5c);
}

void render(Run &run, uint32_t stage, uint32_t argument) {
    run.vcall(run.get(run.get(stage + 0x0c) + 0x08), 0x24, {argument});
    run.vcall(run.get(run.get(stage + 0x0c) + 0x08), 0x40);
}

// Stage +0x764 flag; global +0x170 range, +0x16c selected index,
// +0x174 selected data; range +0x64/+0x68 bounds and +0x14 data.
void selectRange(Run &run, uint32_t stage, bool reverse) {
    if (!run.get(stage + 0x764))
        return;
    uint32_t global = run.get(0x537e88);
    uint32_t range = run.get(global + 0x170);
    if (!range)
        return;
    uint32_t data = 0;
    if (s32(run.get(range + 0x64)) <= 100 && s32(run.get(range + 0x68)) >= 100)
        data = run.get(run.get(range + 0x14) + 0x190);
    if (reverse) {
        run.put(global + 0x174, data);
        run.put(global + 0x16c, 100);
    } else {
        run.put(global + 0x16c, 100);
        run.put(global + 0x174, data);
    }
}

// 0x46ace0.
uint32_t function_46ace0(Run &run, uint32_t stage) {
    run.call(0x46c860, stage);
    uint32_t object = effect(run, stage);
    if (object)
        run.call(0x4d1fd0, object);
    render(run, stage, 1);
    selectRange(run, stage, false);
    return 0;
}

// 0x46ad70. Clock triplet is restored after the substeps.
uint32_t function_46ad70(Run &run, uint32_t stage) {
    uint32_t delta = run.get(0x53720c);
    uint32_t position = run.get(0x537208);
    uint32_t third = run.get(0x537210);
    uint32_t count = delta / 18;
    uint32_t remainder = delta % 18;
    if (remainder)
        ++count;
    uint32_t current = position - delta;
    uint32_t currentThird = third - delta;
    for (uint32_t index = 0; s32(index) < s32(count); ++index) {
        uint32_t step = index == count - 1 && remainder ? remainder : 18;
        currentThird += step;
        current += step;
        run.call(0x42ae40, run.get(stage + 0x04), {current, step, currentThird});
        if (s32(index) > 0 && s32(index) < s32(count - 1)) {
            uint32_t object = effect(run, stage);
            if (object)
                run.call(0x4d2000, object);
        }
        run.call(0x46c860, stage);
        uint32_t object = effect(run, stage);
        if (object)
            run.call(0x4d1fd0, object);
        render(run, stage, 0);
    }
    run.call(0x42ae40, run.get(stage + 0x04), {position, delta, third});
    selectRange(run, stage, true);
    return count;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *args) {
    switch (function) {
    case 0x4c8be0:
        return function_4c8be0(run, receiver, args);
    case 0x4c8da0:
        return function_4c8da0(run, receiver, args);
    case 0x4c8fc0:
        return function_4c8fc0(run, receiver, args[0]);
    case 0x4c9320:
        return function_4c9320(run, receiver, args[0]);
    case 0x4c9860:
        return function_4c9860(run, receiver, args[0]);
    case 0x46ace0:
        return function_46ace0(run, receiver);
    case 0x46ad70:
        return function_46ad70(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_scene_actor_entry, owned, body)
