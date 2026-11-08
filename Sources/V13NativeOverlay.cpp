#include "ClawRuntime.hpp"
#include "V13EnemyDeathSound.h"
#include "V13NativeOverlay.h"

namespace {
using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x4208e0:
        return 4;
    case 0x420910:
        return 1;
    case 0x4ca3b0:
        return 2;
    default:
        return -1;
    }
}

uint32_t playDirect(Run &run, uint32_t resource, const uint32_t *arguments) {
    if (!run.get(0x532c0c))
        return 0;
    uint32_t now = run.get(0x537210);
    if (!claw_v13_sound_elapsed(now, run.get(resource + 0x14), run.get(resource + 0x18)))
        return 0;
    run.put(resource + 0x14, now);
    run.stackPointer = run.frame - 0x14;
    return run.call(0x4b45f0, run.get(resource + 0x10),
                    {arguments[0], arguments[1], arguments[2], arguments[3]});
}

uint32_t playNamed(Run &run, uint32_t manager, uint32_t name) {
    if (run.get(manager + 0x30))
        return 0;
    uint32_t output = run.automatic(-4);
    run.put(output, 0);
    run.stackPointer = run.frame - 0x10;
    run.call(0x4f6286, manager + 0x10, {name, output});
    uint32_t resource = run.get(output);
    if (!resource)
        return 0;
    uint32_t enabled = run.get(0x532c0c);
    uint32_t volume = run.get(0x532c10);
    if (!enabled)
        return 0;
    uint32_t now = run.get(0x537210);
    if (!claw_v13_sound_elapsed(now, run.get(resource + 0x14), run.get(resource + 0x18)))
        return 0;
    run.put(resource + 0x14, now);
    run.stackPointer = run.frame - 0x18;
    return run.call(0x4b45f0, run.get(resource + 0x10), {volume, 0, 0, 0});
}

uint32_t createSound(Run &run, uint32_t manager, const uint32_t *arguments) {
    if (run.get(manager + 0x30))
        return 0;
    run.stackPointer = run.frame - 0x10;
    uint32_t resource = run.call(0x4f63ec, 0, {0x1c});
    if (!resource)
        return 0;
    uint32_t identity = run.get(manager + 0x1c);
    uint32_t scene = run.get(manager + 0x0c);
    run.put(resource + 0x04, identity);
    run.put(resource + 0x0c, scene);
    run.put(resource + 0x08, 0);
    run.put(resource, 0x5138b0);
    run.put(resource + 0x10, 0);
    run.put(resource + 0x18, 0);
    run.put(resource + 0x14, 0);
    run.stackPointer = run.frame - 0x10;
    if (!run.call(0x4c8850, resource, {arguments[1]})) {
        run.stackPointer = run.frame - 0x10;
        run.vcall(resource, 0x04, {1});
        return 0;
    }
    run.stackPointer = run.frame - 0x10;
    uint32_t slot = run.call(0x4f62a8, manager + 0x10, {arguments[0]});
    run.put(slot, resource);
    run.put(resource + 0x18, run.get(manager + 0x34));
    return resource;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4208e0:
        return playDirect(run, receiver, arguments);
    case 0x420910:
        return playNamed(run, receiver, arguments[0]);
    case 0x4ca3b0:
        return createSound(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_v13_native_overlay_entry, owned, body)
