// Original single-player construction and startup, recovered from the packet.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x40b5c0: return 0;
    case 0x48f0d0: return 3;
    case 0x46a6d0: return 3;
    case 0x46aeb0: return 2;
    case 0x42af50: return 0;
    case 0x42aa50: return 0;
    case 0x4cea10: return 5;
    case 0x4cdf20: return 0;
    case 0x4cfa60: return 0;
    default: return -1;
    }
}

// Preserve physical original callee-entry stack addresses for escaped locals.
class Calls {
    Run &run;
    uint32_t previous;
    uint32_t steady;
public:
    Calls(Run &run, uint32_t depth) : run(run), previous(run.stackPointer), steady(run.frame - depth) {
        run.stackPointer = steady;
    }
    explicit Calls(Run &run) : run(run), previous(run.stackPointer), steady(run.stackPointer) {
    }
    ~Calls() {
        run.stackPointer = previous;
    }
    uint32_t call(uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}) {
        run.stackPointer = steady - 4 * (uint32_t(arguments.size()) + 1);
        uint32_t result = run.call(function, receiver, arguments);
        run.stackPointer = steady;
        return result;
    }
    uint32_t vcall(uint32_t object, uint32_t offset, std::initializer_list<uint32_t> arguments = {}) {
        return call(run.get(run.get(object) + offset), object, arguments);
    }
    uint32_t icall(uint32_t slot, std::initializer_list<uint32_t> arguments = {}) {
        return call(slot, 0, arguments);
    }
};

// 0x40b5c0. State table and initially empty owner/resource fields.
uint32_t construct(Run &run, uint32_t receiver) {
    run.put(receiver + 0x00, 0x50b4ec);
    run.put(receiver + 0x04, 0);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x1c, 0);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x24, 0);
    run.put(receiver + 0x2c, 0);
    run.put(receiver + 0x30, 0);
    run.put(receiver + 0x3c, 0);
    run.put(receiver + 0x40, 0);
    run.put(receiver + 0x34, 0);
    run.put8(receiver + 0x4c, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x150, 0);
    return receiver;
}

// 0x48f0d0. Owner +0x34 resources, +0x30 scene, +0x44 configuration.
uint32_t initializeState(Run &run, uint32_t receiver, uint32_t owner, uint32_t level, uint32_t mode) {
    Calls calls(run, 36);
    run.put(receiver + 0x04, owner);
    run.put(receiver + 0x08, run.get(owner + 0x34));
    run.put(receiver + 0x0c, run.get(owner + 0x30));
    run.put(receiver + 0x10, run.get(owner + 0x44));
    run.put(receiver + 0x14, level);
    run.put(receiver + 0x18, mode);
    run.put(receiver + 0x44, 0xffffffff);
    run.put(receiver + 0x48, 0xffffffff);
    run.put(receiver + 0x14c, 0);
    run.put(receiver + 0x2c, 0);
    run.put(receiver + 0x150, 0);
    calls.call(0x4a3920, 0, {receiver + 0x4c, 0x52c69c, run.get(0x53ec44)});
    uint32_t label = run.automatic(-32);
    calls.call(0x4a3920, 0, {label, 0x52a004, run.get(receiver + 0x14)});
    uint32_t directory = calls.call(0x4b7f20, run.get(receiver + 0x08), {label});
    run.put(receiver + 0x1c, directory);
    if (!directory)
        return 0;
    run.put(receiver + 0x34, 1);
    return 1;
}

// 0x42af50. Application +0x7c/+0x80 are the current dimensions.
uint32_t defaultDimensions(Run &run, uint32_t receiver) {
    if (run.get(receiver + 0x7c) != 640)
        return 0;
    return run.get(receiver + 0x80) == 480;
}

// 0x42aa50.
uint32_t resetGlobals(Run &run) {
    run.put(0x537268, 0);
    run.put(0x537214, 0);
    run.put(0x537218, 0);
    run.put(0x53721c, 0);
    run.put(0x537220, 0);
    run.put(0x537228, 0);
    run.put(0x537224, 0);
    run.put(0x53722c, 0);
    run.put(0x537230, 0);
    run.put(0x537264, 0);
    return 0;
}

// 0x4cdf20.
uint32_t initializeManager(Run &run) {
    (void)run;
    return 1;
}

// 0x4cfa60. Twenty-five effect weights, first weight 100.
uint32_t initializeEffects(Run &run) {
    for (uint32_t index = 0; index < 25; ++index) {
        run.put(0x543108 + index * 4, 0);
    }
    run.put(0x543108, 100);
    return 1;
}

uint32_t managerInitialize(Run &run, uint32_t object) {
    Calls calls(run);
    uint32_t target = run.get(run.get(object) + 0x18);
    if (target == 0x4cdf20)
        return initializeManager(run);
    if (target == 0x4cfa60)
        return initializeEffects(run);
    return calls.call(target, object);
}

uint32_t sceneFailure(Run &run, uint32_t receiver, uint32_t error) {
    if (!run.get(receiver + 0x38)) {
        run.put(receiver + 0x38, error);
    }
    return 0;
}

// 0x4cea10. Scene +0x30 window, +0x34 flags, +0x38 sticky error.
uint32_t initializeScene(Run &run, uint32_t receiver, const uint32_t *arguments) {
    Calls calls(run, 32);
    run.put(receiver + 0x30, arguments[0]);
    run.put(receiver + 0x34, arguments[4]);
    uint32_t child = calls.call(0x4f63ec, 0, {0x1c});
    if (child) {
        calls.call(0x45fde0, child, {receiver, 0, 0});
        run.put(child + 0x00, 0x513c68);
        run.put(child + 0x10, 0);
        run.put(child + 0x14, 0);
        run.put(child + 0x18, 0);
    }
    run.put(receiver + 0x04, child);
    child = calls.call(0x4f63ec, 0, {0x2c});
    if (child) {
        run.put(child + 0x00, 0x50e924);
        run.put(child + 0x04, 0);
        run.put(child + 0x08, 0);
        run.put(child + 0x0c, receiver);
        calls.call(0x4f5620, child + 0x10, {10});
        run.put(child + 0x00, 0x513c20);
    }
    run.put(receiver + 0x08, child);
    child = calls.call(0x4f63ec, 0, {0x2c});
    if (child) {
        calls.call(0x45fde0, child, {receiver, 0, 0});
        calls.call(0x4f5620, child + 0x10, {10});
        run.put(child + 0x00, 0x513be8);
    }
    run.put(receiver + 0x0c, child);
    child = calls.call(0x4f63ec, 0, {0x2c});
    if (child) {
        run.put(child + 0x00, 0x50e924);
        run.put(child + 0x04, 0);
        run.put(child + 0x08, 0);
        run.put(child + 0x0c, receiver);
        calls.call(0x4f6118, child + 0x10, {10});
        run.put(child + 0x00, 0x513b88);
    }
    run.put(receiver + 0x10, child);
    child = calls.call(0x4f63ec, 0, {0x2c});
    if (child) {
        run.put(child + 0x00, 0x50e924);
        run.put(child + 0x04, 0);
        run.put(child + 0x08, 0);
        run.put(child + 0x0c, receiver);
        calls.call(0x4f6118, child + 0x10, {10});
        run.put(child + 0x00, 0x513b60);
    }
    run.put(receiver + 0x14, child);
    child = calls.call(0x4f63ec, 0, {0x68});
    if (child) {
        calls.call(0x45fde0, child, {receiver, 0, 0});
        calls.call(0x4f6118, child + 0x10, {10});
        calls.call(0x4f6118, child + 0x2c, {10});
        calls.call(0x4f6118, child + 0x48, {10});
        run.put(child + 0x00, 0x513b28);
        run.put(child + 0x64, 0);
    }
    run.put(receiver + 0x18, child);
    child = calls.call(0x4f63ec, 0, {0xe0});
    if (child)
        child = calls.call(0x4cace0, child, {receiver, 0, 0});
    run.put(receiver + 0x24, child);
    child = calls.call(0x4f63ec, 0, {0x34});
    if (child) {
        run.put(child + 0x00, 0x50e924);
        run.put(child + 0x04, 0);
        run.put(child + 0x08, 0);
        run.put(child + 0x0c, receiver);
        calls.call(0x4f5cbd, child + 0x10, {10});
        run.put(child + 0x00, 0x513b00);
        run.put(child + 0x2c, 0);
    }
    run.put(receiver + 0x28, child);
    child = calls.call(0x4f63ec, 0, {0x2c});
    if (child) {
        run.put(child + 0x00, 0x50e924);
        run.put(child + 0x04, 0);
        run.put(child + 0x08, 0);
        run.put(child + 0x0c, receiver);
        calls.call(0x4f5cbd, child + 0x10, {10});
        run.put(child + 0x00, 0x513ad8);
    }
    run.put(receiver + 0x2c, child);
    child = calls.call(0x4f63ec, 0, {0x884});
    if (child)
        child = calls.call(0x4bc120, child);
    run.put(receiver + 0x1c, child);
    child = calls.call(0x4f63ec, 0, {0x80});
    if (child)
        child = calls.call(0x4b4710, child);
    run.put(receiver + 0x20, child);
    const uint32_t slots[] = {0x08, 0x0c, 0x10, 0x14, 0x18, 0x2c};
    for (uint32_t index = 0; index < 6; ++index) {
        if (!managerInitialize(run, run.get(receiver + slots[index])))
            return sceneFailure(run, receiver, 1001 + index);
    }
    if (!calls.vcall(run.get(receiver + 0x24), 0x34, {arguments[1], arguments[2]}))
        return sceneFailure(run, receiver, 1007);
    if (!calls.vcall(run.get(receiver + 0x04), 0x24, {arguments[1], arguments[2], arguments[3], arguments[4]}))
        return sceneFailure(run, receiver, 1008);
    if (!calls.call(0x4b47e0, run.get(receiver + 0x20), {arguments[0], 1})) {
        child = run.get(receiver + 0x20);
        if (child)
            calls.vcall(child, 0x00, {1});
        run.put(receiver + 0x20, 0);
        if (arguments[4] & 8)
            return sceneFailure(run, receiver, 1009);
    }
    child = run.get(receiver + 0x20);
    if (child && (arguments[4] & 4)) {
        calls.vcall(child, 0x00, {1});
        run.put(receiver + 0x20, 0);
    }
    if (!calls.call(0x4ca280, run.get(receiver + 0x28), {1}))
        return sceneFailure(run, receiver, 1010);
    return 1;
}

// 0x46aeb0. Scene/resource child fields are reloaded at every original access.
uint32_t loadLevel(Run &run, uint32_t receiver, uint32_t level) {
    Calls calls(run, 80);
    run.put(receiver + 0x14, level);
    run.put(0x538418, 0);
    run.put(0x54316c, 0);
    run.put(receiver + 0x44, 0xffffffff);
    run.put(receiver + 0x48, 0xffffffff);
    run.put(receiver + 0x764, 0);
    run.put(0x537210, 0);
    run.put(0x53c9c0, 0);
    run.put(0x5349dc, 0);
    calls.call(0x4a3040, 0, {0x1b3cf});
    if (!defaultDimensions(run, run.get(receiver + 0x04)))
        calls.call(0x42a000, run.get(receiver + 0x04), {0});
    uint32_t owner = run.get(receiver + 0x04);
    if (run.get(run.get(owner + 0xc0) - 8)) {
        uint32_t temporary = run.automatic(-84);
        run.put(run.automatic(4), temporary);
        calls.call(0x46a840, owner, {temporary});
        level = calls.call(0x436e60, 0, {run.get(temporary)});
        run.put(run.automatic(4), level);
        if (level != run.get(receiver + 0x14)) {
            calls.call(0x4f650f, run.get(receiver + 0x04) + 0xc0);
            run.put(receiver + 0x258, 0);
        }
    }
    uint32_t label = run.automatic(-44);
    calls.call(0x4a3920, 0, {label, 0x52a004, run.get(receiver + 0x14)});
    uint32_t directory = calls.call(0x4b7f20, run.get(receiver + 0x08), {label});
    run.put(receiver + 0x1c, directory);
    if (!directory)
        return 0;
    uint32_t resource = calls.call(0x4b7dc0, directory, {0x529ff4, 0x50414c});
    if (!resource)
        return 0;
    uint32_t palette = run.get(receiver + 0x2c);
    if (palette) {
        calls.call(0x4d46f0, run.get(run.get(receiver + 0x0c) + 0x18), {palette});
        run.put(receiver + 0x2c, 0);
    }
    palette = calls.vcall(run.get(run.get(receiver + 0x0c) + 0x18), 0x24, {resource, 0, 0});
    run.put(receiver + 0x2c, palette);
    if (!palette)
        return 0;
    uint32_t surface = run.get(run.get(palette + 0x10) + 0x04);
    calls.call(run.get(run.get(surface) + 0x10), 0, {surface, 0, 0, 0x100, receiver + 0x360});
    calls.call(0x4bb870, run.get(run.get(receiver + 0x2c) + 0x10));
    calls.call(0x4bb990, run.get(run.get(receiver + 0x2c) + 0x10), {0, 0x100, 0, 0, 0, 250});
    uint32_t display = run.get(run.get(receiver + 0x0c) + 0x04);
    calls.call(0x4b97c0, run.get(run.get(display + 0x14) + 0x2c), {0});
    calls.call(0x4b98b0, run.get(run.get(display + 0x10) + 0x2c), {0});
    palette = run.get(receiver + 0x2c);
    run.put(run.get(run.get(receiver + 0x0c) + 0x18) + 0x64, palette);
    calls.vcall(palette, 0x34);
    calls.call(0x4bb910, run.get(run.get(receiver + 0x2c) + 0x10), {0, 0x100, 0, 0, 0, 0});
    calls.call(0x46db30, receiver);
    uint32_t previousDirectory = run.get(receiver + 0x20);
    run.put(receiver + 0x20, run.get(receiver + 0x1c));
    calls.icall(0x546ccc, {run.get(run.get(run.get(receiver + 0x04) + 0x04) + 0x04)});
    calls.call(0x48f3e0, receiver, {0x529fec, 1, 1, 1, 0});
    calls.call(0x46f040, receiver);
    uint32_t cursor = run.get(0x546d54);
    while (s32(calls.call(cursor, 0, {0})) >= 0) {
    }
    run.put(receiver + 0x20, previousDirectory);
    calls.call(0x46e100, receiver);
    calls.call(0x46b7b0, receiver);
    calls.call(0x46dff0, receiver, {5});
    calls.call(0x46bb80, receiver);
    calls.call(0x46dff0, receiver, {10});
    if (!calls.call(0x46e160, receiver))
        return 0;
    calls.call(0x46dff0, receiver, {15});
    run.put(0x54316c, 0);
    directory = calls.call(0x4b7cd0, run.get(receiver + 0x1c), {0x529fe4});
    if (!directory)
        return 0;
    calls.vcall(run.get(run.get(receiver + 0x0c) + 0x10), 0x48, {directory, 0x534938, 0x523728});
    calls.call(0x46dff0, receiver, {20});
    const uint32_t directorySlots[] = {0x1c, 0x24, 0x28};
    const uint32_t prefixes[] = {0x524d80, 0x523734, 0x5254ec};
    for (uint32_t index = 0; index < 3; ++index) {
        directory = calls.call(0x4b7cd0, run.get(receiver + directorySlots[index]), {0x52372c});
        if (!directory)
            return 0;
        calls.call(0x4ca440, run.get(run.get(receiver + 0x0c) + 0x28), {directory, prefixes[index], 0x523728});
        calls.call(0x46dff0, receiver, {25 + index * 5});
    }
    for (uint32_t index = 0; index < 3; ++index) {
        run.put(0x54316c, 1);
        directory = calls.call(0x4b7cd0, run.get(receiver + directorySlots[index]), {0x523ce0});
        if (!directory)
            return 0;
        calls.vcall(run.get(run.get(receiver + 0x0c) + 0x10), 0x48, {directory, prefixes[index], 0x523728});
        run.put(0x54316c, 0);
        calls.call(0x46dff0, receiver, {40 + index * 10});
        directory = calls.call(0x4b7cd0, run.get(receiver + directorySlots[index]), {0x523cd8});
        if (!directory)
            return 0;
        calls.call(0x4ce0d0, run.get(run.get(receiver + 0x0c) + 0x2c), {directory, prefixes[index], 0x523728});
        calls.call(0x46dff0, receiver, {45 + index * 10});
    }
    calls.call(0x42abf0, run.get(receiver + 0x04));
    owner = run.get(receiver + 0x04);
    if (run.get(run.get(owner + 0xc0) - 8)) {
        uint32_t temporary = run.automatic(-64);
        uint32_t copy = calls.call(0x46a840, owner, {temporary});
        uint32_t loaded = calls.vcall(run.get(run.get(receiver + 0x0c) + 0x24), 0x40, {run.get(copy)});
        calls.call(0x4f6584, temporary);
        if (!loaded)
            return 0;
        cursor = run.get(0x546d54);
    } else {
        resource = calls.call(0x4b7dc0, run.get(receiver + 0x1c), {0x529fd4, 0x575744});
        if (!resource)
            return 0;
        if (!calls.vcall(run.get(run.get(receiver + 0x0c) + 0x24), 0x3c, {resource}))
            return 0;
    }
    calls.call(0x4cdcb0, run.get(run.get(receiver + 0x0c) + 0x24));
    calls.call(0x46dff0, receiver, {70});
    calls.call(0x42ae70, run.get(receiver + 0x04));
    if (!calls.call(0x452b00, 0, {level}))
        return 0;
    calls.call(0x46dff0, receiver, {75});
    uint32_t actor = calls.call(0x4c8da0, run.get(run.get(receiver + 0x0c) + 0x08), {1, 0x140, 0x15e, 100, 0x522e80, 0x40002});
    run.put(0x537e88, actor);
    if (!actor)
        return 0;
    if (run.get(receiver + 0x154)) {
        run.put(receiver + 0x154, 0);
        calls.call(0x415ce0, 0);
        calls.call(0x46c790, receiver);
        calls.call(0x46d8e0, receiver);
        actor = run.get(0x537e88);
    } else {
        run.put(0x534ca4, 0);
    }
    calls.call(run.get(run.get(actor + 0x6c) + 0x10), 0, {actor});
    calls.call(0x46dff0, receiver, {80});
    calls.call(0x4c8b90, run.get(run.get(receiver + 0x0c) + 0x08), {0, 9999, 0x522e3c, 0});
    run.put(0x52be14, 0xffffffff);
    run.put(0x52be18, 0xffffffff);
    calls.call(0x486d30, 0);
    calls.call(0x4c8f60, run.get(run.get(receiver + 0x0c) + 0x08), {0, 0, 0, 9999, 0x52297c, 0x200000});
    calls.call(0x4c8da0, run.get(run.get(receiver + 0x0c) + 0x08), {0, 0, 0, 1000, 0x5223cc, 0x40000});
    calls.call(0x4c8da0, run.get(run.get(receiver + 0x0c) + 0x08), {0, 0, 0, 1000, 0x5223b8, 0x40000});
    if (run.get(run.get(receiver + 0x04) + 0x9c))
        calls.call(0x4c8da0, run.get(run.get(receiver + 0x0c) + 0x08), {0, 0, 0, 9999, 0x522828, 0x200000});
    calls.call(0x4719e0, 0, {run.get(receiver + 0x0c)});
    calls.call(0x42a450, run.get(receiver + 0x04), {run.automatic(-60)});
    if (run.gets(run.automatic(-56)) > 0)
        calls.call(0x4b97c0, run.get(run.get(run.get(run.get(receiver + 0x0c) + 0x04) + 0x14) + 0x2c), {0});
    calls.call(0x46dff0, receiver, {85});
    calls.call(0x431300, run.get(0x537204));
    while (s32(calls.call(cursor, 0, {0})) >= 0) {
    }
    calls.call(0x42abf0, run.get(receiver + 0x04));
    run.put(receiver + 0x158, 0);
    calls.call(0x46caf0, receiver);
    calls.call(0x46dff0, receiver, {90});
    if (!run.get(run.get(receiver + 0x04) + 0x124))
        calls.call(0x46ef80, receiver);
    uint32_t plane = run.get(run.get(run.get(receiver + 0x0c) + 0x24) + 0x5c);
    if (plane)
        calls.call(0x4d2030, plane);
    plane = run.get(run.get(run.get(receiver + 0x0c) + 0x24) + 0x5c);
    if (plane)
        calls.call(0x4d1fd0, plane);
    calls.call(0x46dff0, receiver, {95});
    uint32_t musicMode = calls.call(0x48bfd0, 0);
    run.put(run.automatic(4), musicMode);
    calls.call(0x4b5340, run.get(run.get(receiver + 0x04) + 0x50));
    directory = calls.call(0x4b7cd0, run.get(receiver + 0x1c), {0x526a58});
    if (directory) {
        const uint32_t preferred[] = {0x529fcc, 0x529fc4};
        const uint32_t fallback[] = {0x5256a8, 0x529fbc};
        const uint32_t names[] = {0x524d80, 0x529fbc};
        for (uint32_t index = 0; index < 2; ++index) {
            resource = 0;
            if (!musicMode)
                resource = calls.call(0x4b67f0, directory, {preferred[index], 0x584d49});
            if (!resource)
                resource = calls.call(0x4b67f0, directory, {fallback[index], 0x584d49});
            if (resource) {
                uint32_t data = calls.call(0x4b61c0, resource);
                if (data)
                    calls.call(0x4b53f0, run.get(run.get(receiver + 0x04) + 0x50), {data, run.get(resource + 0x14), names[index]});
            }
        }
    }
    directory = calls.call(0x4b7cd0, run.get(receiver + 0x28), {0x526a58});
    if (directory) {
        resource = 0;
        if (!musicMode)
            resource = calls.call(0x4b67f0, directory, {0x529fb0, 0x584d49});
        if (!resource)
            resource = calls.call(0x4b67f0, directory, {0x524d78, 0x584d49});
        if (resource) {
            uint32_t data = calls.call(0x4b61c0, resource);
            if (data)
                calls.call(0x4b53f0, run.get(run.get(receiver + 0x04) + 0x50), {data, run.get(resource + 0x14), 0x524d78});
        }
        resource = calls.call(0x4b67f0, directory, {0x525948, 0x584d49});
        if (resource) {
            uint32_t data = calls.call(0x4b61c0, resource);
            if (data)
                calls.call(0x4b53f0, run.get(run.get(receiver + 0x04) + 0x50), {data, run.get(resource + 0x14), 0x525948});
        }
    }
    calls.call(0x4b8910, run.get(run.get(receiver + 0x04) + 0x04), {0x100, 0x40});
    calls.call(0x46dff0, receiver, {100});
    calls.call(0x4b8960, 0, {200});
    return 1;
}

// 0x46a6d0. +0x258 custom world, +0x15c timeout; nested owned frames are physical.
uint32_t initializeSinglePlayer(Run &run, uint32_t receiver, const uint32_t *arguments) {
    Calls calls(run, 16);
    uint32_t owner = arguments[0];
    uint32_t level = arguments[1];
    if (!owner)
        return 0;
    if (!run.get(run.get(owner + 0xc0) - 8)) {
        run.put(owner + 0x130, 0);
        run.put(receiver + 0x258, 0);
    } else {
        uint32_t temporary = run.automatic(-20);
        run.put(run.automatic(8), temporary);
        calls.call(0x46a840, owner, {temporary});
        level = calls.call(0x436e60, 0, {run.get(temporary)});
        run.put(run.automatic(8), level);
        if (s32(level) < 1)
            return 0;
        run.put(receiver + 0x258, 1);
        run.put(owner + 0x130, 1);
    }
    uint32_t frame = run.frame;
    run.frame = frame - 32;
    uint32_t initialized = initializeState(run, receiver, owner, level, arguments[2]);
    run.frame = frame;
    if (!initialized)
        return 0;
    uint32_t cursor = run.get(0x546d54);
    while (s32(calls.call(cursor, 0, {0})) >= 0) {
    }
    run.put(receiver + 0x38, 0);
    run.put(receiver + 0x25c, 0);
    run.put(receiver + 0x770, 0);
    run.put(receiver + 0x76c, 0);
    run.put(receiver + 0x768, 0);
    resetGlobals(run);
    run.put(run.get(owner + 0x48) + 0x128, 0);
    run.put(receiver + 0x760, 0);
    if (!defaultDimensions(run, run.get(receiver + 0x04)))
        calls.call(0x42a000, run.get(receiver + 0x04), {0});
    uint32_t directory = calls.call(0x4b7f20, run.get(receiver + 0x08), {0x523734});
    run.put(receiver + 0x24, directory);
    if (!directory)
        return 0;
    directory = calls.call(0x4b7f20, run.get(receiver + 0x08), {0x5254ec});
    run.put(receiver + 0x28, directory);
    if (!directory)
        return 0;
    run.frame = frame - 28;
    initialized = loadLevel(run, receiver, level);
    run.frame = frame;
    if (!initialized)
        return 0;
    if (run.get(run.get(receiver + 0x04) + 0x9c)) {
        run.put(receiver + 0x15c, 180000);
    } else {
        run.put(receiver + 0x15c, 3600000);
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40b5c0: return construct(run, receiver);
    case 0x48f0d0: return initializeState(run, receiver, arguments[0], arguments[1], arguments[2]);
    case 0x46a6d0: return initializeSinglePlayer(run, receiver, arguments);
    case 0x46aeb0: return loadLevel(run, receiver, arguments[0]);
    case 0x42af50: return defaultDimensions(run, receiver);
    case 0x42aa50: return resetGlobals(run);
    case 0x4cea10: return initializeScene(run, receiver, arguments);
    case 0x4cdf20: return initializeManager(run);
    case 0x4cfa60: return initializeEffects(run);
    default: run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_single_player_scene_canonical_entry, owned, body)
