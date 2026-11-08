// BossStager scene rectangle and boss music selection.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x42a450:
        return 1;
    case 0x42b000:
    case 0x46cab0:
        return 0;
    default:
        return -1;
    }
}

struct NestedFrame {
    Run &run;
    uint32_t frame;
    uint32_t stackPointer;
    explicit NestedFrame(Run &run, uint32_t entry) : run(run), frame(run.frame), stackPointer(run.stackPointer) {
        run.frame = entry;
        run.stackPointer = 0;
    }
    ~NestedFrame() {
        run.frame = frame;
        run.stackPointer = stackPointer;
    }
};

// 0x42a450. Manager +0x30 links the scene, whose +0x24 links its
// description. Description +0x10..+0x1c holds the scene rectangle.
uint32_t function_42a450(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t temporary = run.automatic(-0x10);
    run.stackPointer = run.frame - 0x2c;
    run.icall(0x546d5c, {temporary, 0, 0, 0x27f, 0x1df});
    uint32_t scene = run.get(receiver + 0x30);
    uint32_t output = arguments[0];
    if (!scene) {
        run.put(output + 0x00, run.get(temporary + 0x00));
        run.put(output + 0x04, run.get(temporary + 0x04));
        run.put(output + 0x08, run.get(temporary + 0x08));
        run.put(output + 0x0c, run.get(temporary + 0x0c));
        return output;
    }
    uint32_t rectangle = run.get(scene + 0x24) + 0x10;
    run.put(temporary + 0x00, run.get(rectangle + 0x00));
    run.put(temporary + 0x04, run.get(rectangle + 0x04));
    run.put(temporary + 0x08, run.get(rectangle + 0x08));
    run.put(temporary + 0x0c, run.get(rectangle + 0x0c));
    run.put(output + 0x00, run.get(rectangle + 0x00));
    run.put(output + 0x04, run.get(rectangle + 0x04));
    run.put(output + 0x08, run.get(rectangle + 0x08));
    run.put(output + 0x0c, run.get(rectangle + 0x0c));
    return output;
}

// 0x46cab0. Interface +0x04 is its manager; manager +0x14 is the
// physical music controller, +0x50 the registry; registry +0x1c is current.
uint32_t function_46cab0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t manager = run.get(receiver + 0x04);
    if (run.get(manager + 0x14)) {
        uint32_t registry = run.get(manager + 0x50);
        run.stackPointer = run.frame - 0x0c;
        return run.call(0x4b54f0, registry, {0x529fbc, 1});
    }
    uint32_t registry = run.get(manager + 0x50);
    run.stackPointer = run.frame - 0x0c;
    uint32_t track = run.call(0x4b54a0, registry, {0x529fbc});
    if (!track)
        return 0;
    run.put(registry + 0x1c, track);
    return 1;
}

// 0x42b000. Manager +0x2c is the current scene interface.
uint32_t function_42b000(Run &run, uint32_t receiver, const uint32_t *) {
    run.stackPointer = run.frame - 0x08;
    uint32_t mode = run.call(0x42a630, receiver);
    if (!mode)
        return 0;
    uint32_t scene = run.get(receiver + 0x2c);
    uint32_t method = run.get(run.get(scene) + 0x60);
    uint32_t result;
    if (method == 0x46cab0) {
        NestedFrame nested(run, run.frame - 0x08);
        result = function_46cab0(run, scene, nullptr);
    } else {
        run.stackPointer = run.frame - 0x08;
        result = run.call(method, scene);
    }
    return result != 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x42a450:
        return function_42a450(run, receiver, arguments);
    case 0x42b000:
        return function_42b000(run, receiver, arguments);
    case 0x46cab0:
        return function_46cab0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_boss_scene_services_entry, owned, body)
