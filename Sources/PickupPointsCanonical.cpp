// Original pickup points actor, translated from the reference packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x40f680:
    case 0x4737c0:
    case 0x473a70:
    case 0x4c7970:
        return 1;
    case 0x4c7900:
        return 2;
    default:
        return -1;
    }
}

// 0x40f680. Collection +0x64/+0x68 are signed inclusive bounds;
// +0x14 is the absolute-index frame table.
uint32_t imageFrameAt(Run &run, uint32_t collection, uint32_t index) {
    if (s32(index) < s32(run.get(collection + 0x64)))
        return 0;
    if (s32(index) > s32(run.get(collection + 0x68)))
        return 0;
    return run.get(run.get(collection + 0x14) + index * 4u);
}

// 0x4c7900. Actor +0x0c is its world, world +0x10 its image manager.
// Actor +0x170 collection, +0x16c selected index, +0x174 selected frame.
void selectImageFrame(Run &run, uint32_t actor, uint32_t name, uint32_t index) {
    uint32_t local = run.automatic(-4);
    run.put(local, 0);
    uint32_t manager = run.get(run.get(actor + 0x0c) + 0x10);
    run.call(0x4f6286, manager + 0x10, {name, local});
    uint32_t collection = run.get(local);
    run.put(actor + 0x170, collection);
    if (!collection)
        return;
    uint32_t frame = imageFrameAt(run, collection, index);
    run.put(actor + 0x16c, index);
    run.put(actor + 0x174, frame);
}

// 0x4c7970. The index store can alias the collection's bounds or table.
void selectFirstImageFrame(Run &run, uint32_t actor, uint32_t name) {
    uint32_t local = run.automatic(-4);
    run.put(local, 0);
    uint32_t manager = run.get(run.get(actor + 0x0c) + 0x10);
    run.call(0x4f6286, manager + 0x10, {name, local});
    uint32_t collection = run.get(local);
    run.put(actor + 0x170, collection);
    if (!collection)
        return;
    uint32_t index = run.get(collection + 0x64);
    run.put(actor + 0x16c, index);
    uint32_t frame = imageFrameAt(run, collection, index);
    run.put(actor + 0x174, frame);
}

// 0x4737c0. Input +0x4c/+0x50 position, +0xfc point value;
// world +0x08 is the actor manager.
void spawnPickupPoints(Run &run, uint32_t input) {
    uint32_t y = run.get(input + 0x50);
    uint32_t x = run.get(input + 0x4c);
    uint32_t world = run.get(input + 0x0c);
    uint32_t actor = run.call(0x4c8da0, run.get(world + 0x08), {0, x, y, 0x22c4, 0x522874, 0x40000});
    if (!actor)
        return;
    uint32_t parentFrame = run.frame;
    run.frame = parentFrame - 0x10;
    selectFirstImageFrame(run, actor, 0x52a6c0);
    run.frame = parentFrame;
    uint32_t points = run.get(input + 0xfc);
    uint32_t index = 0;
    switch (points) {
    case 100:
        index = 1;
        break;
    case 500:
        index = 2;
        break;
    case 1500:
        index = 3;
        break;
    case 2500:
        index = 4;
        break;
    case 5000:
        index = 5;
        break;
    case 7500:
        index = 6;
        break;
    case 10000:
        index = 7;
        break;
    case 15000:
        index = 8;
        break;
    case 25000:
        index = 9;
        break;
    default:
        run.frame = parentFrame - 0x14;
        selectImageFrame(run, actor, 0x52a6c0, 0);
        run.frame = parentFrame;
        return;
    }
    uint32_t collection = run.get(actor + 0x170);
    if (!collection)
        return;
    uint32_t frame = imageFrameAt(run, collection, index);
    if (index >= 8) {
        run.put(actor + 0x174, frame);
        run.put(actor + 0x16c, index);
        return;
    }
    run.put(actor + 0x16c, index);
    run.put(actor + 0x174, frame);
}

// 0x473a70. Actor +0x6c state, state +0x1c status; actor +0x08 flags.
// Embedded animation +0x188 has remaining time +0x14 and finished +0x1c.
uint32_t updatePickupPoints(Run &run, uint32_t actor) {
    uint32_t state = run.get(actor + 0x6c);
    uint32_t status = run.get(state + 0x1c);
    if (!status) {
        run.put(actor + 0x08, run.get(actor + 0x08) | 0x21u);
        run.call(0x4c79e0, actor, {0x52a6c0, 0});
        run.put(state + 0x1c, 5);
    } else if (status == 5) {
        run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
        if (run.get(actor + 0x1a4) && !run.get(actor + 0x19c))
            run.put(actor + 0x08, run.get(actor + 0x08) | 0x10000u);
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40f680:
        return imageFrameAt(run, receiver, arguments[0]);
    case 0x4737c0:
        spawnPickupPoints(run, arguments[0]);
        return 0;
    case 0x473a70:
        return updatePickupPoints(run, arguments[0]);
    case 0x4c7900:
        selectImageFrame(run, receiver, arguments[0], arguments[1]);
        return 0;
    case 0x4c7970:
        selectFirstImageFrame(run, receiver, arguments[0]);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_pickup_points_canonical_entry, owned, body)
