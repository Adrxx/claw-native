#include "ClawRuntime.hpp"

namespace {
using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x4b44f0:
    case 0x4b4a20:
        return 2;
    case 0x4b4ae0:
    case 0x4c8850:
        return 1;
    case 0x4c88b0:
        return 0;
    default:
        return -1;
    }
}

void copyPCM(Run &run, uint32_t destination, uint32_t source, uint32_t count) {
    uint32_t offset = 0;
    for (; offset < (count & ~3u); offset += 4) {
        run.put(destination + offset, run.get(source + offset));
    }
    for (; offset < count; ++offset) {
        run.put8(destination + offset, run.get8(source + offset));
    }
}

// 0x4b44f0. Pool +0x10 manager, +0xc DirectSound buffer; manager +0x78 availability.
uint32_t transferPCM(Run &run, uint32_t pool, uint32_t source, uint32_t count) {
    if (!run.get(run.get(pool + 0x10) + 0x78)) {
        return 0;
    }
    uint32_t first = run.automatic(-4);
    uint32_t firstSize = run.automatic(8);
    uint32_t second = run.automatic(-8);
    uint32_t secondSize = run.automatic(-12);
    uint32_t buffer = run.get(pool + 0xc);
    run.stackPointer = run.frame - 0x3c;
    uint32_t result = run.call(run.get(run.get(buffer) + 0x2c), 0,
                              {buffer, 0, count, first, firstSize, second, secondSize, 1});
    if (result) {
        run.stackPointer = run.frame - 0x28;
        run.call(0x4b4ed0, 0, {0x53228c, 0x200, 1});
        return 0;
    }
    uint32_t size1 = run.get(firstSize);
    // The source argument itself can alias the lock output cells.
    source = run.get(run.automatic(4));
    if (size1) {
        copyPCM(run, run.get(first), source, size1);
        size1 = run.get(firstSize);
    }
    uint32_t size2 = run.get(secondSize);
    if (size2) {
        copyPCM(run, run.get(second), source + size1, size2);
        size2 = run.get(secondSize);
        size1 = run.get(firstSize);
    }
    buffer = run.get(pool + 0xc);
    run.stackPointer = run.frame - 0x30;
    result = run.call(run.get(run.get(buffer) + 0x4c), 0,
                      {buffer, run.get(first), size1, run.get(second), size2});
    if (result) {
        run.stackPointer = run.frame - 0x28;
        run.call(0x4b4ed0, 0, {0x53228c, 0x213, 1});
        return 0;
    }
    return 1;
}

// 0x4b4ae0. Manager +0xc fade list, +4 resource list; pool +4 embedded node.
void destroyResource(Run &run, uint32_t manager, uint32_t pool) {
    if (!run.get(manager + 0x78)) {
        return;
    }
    run.stackPointer = run.frame - 0x14;
    run.call(0x4b4c80, manager + 0xc, {pool, 0xffff});
    uint32_t buffer = run.get(pool + 0xc);
    run.stackPointer = run.frame - 0x10;
    run.call(run.get(run.get(buffer) + 0x8), 0, {buffer});
    run.put(pool + 0xc, 0);
    run.stackPointer = run.frame - 0x10;
    run.call(0x4b5270, manager + 0x4, {pool ? pool + 0x4 : 0});
    if (pool) {
        run.stackPointer = run.frame - 0x10;
        run.vcall(pool, 0x0, {1});
    }
}

// 0x4b4a20. Locals are pointers to format/data and an aliased incoming count slot.
uint32_t loadPCM(Run &run, uint32_t manager, uint32_t source, uint32_t thirdWord) {
    if (!source) {
        return 0;
    }
    if (!run.get(manager + 0x78)) {
        return 0;
    }
    uint32_t format = run.automatic(-8);
    uint32_t data = run.automatic(-4);
    uint32_t count = run.automatic(4);
    run.put(format, 0);
    run.put(data, 0);
    run.put(count, 0);
    run.stackPointer = run.frame - 0x24;
    if (!run.call(0x4b4e30, 0, {source, format, data, count})) {
        return 0;
    }
    thirdWord = run.get(run.automatic(8));
    run.stackPointer = run.frame - 0x20;
    uint32_t pool = run.call(0x4b48b0, manager, {run.get(format), run.get(count), thirdWord});
    if (!pool) {
        return 0;
    }
    uint32_t bytes = run.get(count);
    uint32_t payload = run.get(data);
    uint32_t parentFrame = run.frame;
    run.frame = parentFrame - 0x1c;
    run.put(run.automatic(4), payload);
    run.put(run.automatic(8), bytes);
    uint32_t transferred = transferPCM(run, pool, payload, bytes);
    run.frame = parentFrame;
    if (!transferred) {
        run.frame = parentFrame - 0x18;
        destroyResource(run, manager, pool);
        run.frame = parentFrame;
        return 0;
    }
    return pool;
}

// 0x4c8850. Sound +0xc scene, +0x10 resource; scene +0x20 live manager.
uint32_t loadSound(Run &run, uint32_t sound, uint32_t file) {
    run.stackPointer = run.frame - 0xc;
    uint32_t source = run.call(0x4b61c0, file);
    if (!source) {
        return 0;
    }
    uint32_t manager = run.get(run.get(sound + 0xc) + 0x20);
    if (!manager) {
        run.stackPointer = run.frame - 0xc;
        run.call(0x4b6230, file);
        return 0;
    }
    uint32_t parentFrame = run.frame;
    run.frame = parentFrame - 0x14;
    run.put(run.automatic(4), source);
    run.put(run.automatic(8), 0);
    uint32_t pool = loadPCM(run, manager, source, 0);
    run.frame = parentFrame;
    run.put(sound + 0x10, pool);
    uint32_t result = pool != 0;
    run.stackPointer = run.frame - 0xc;
    run.call(0x4b6230, file);
    return result;
}

// 0x4c88b0.
void unloadSound(Run &run, uint32_t sound) {
    uint32_t pool = run.get(sound + 0x10);
    if (!pool) {
        return;
    }
    uint32_t manager = run.get(run.get(sound + 0xc) + 0x20);
    if (!manager) {
        return;
    }
    uint32_t parentFrame = run.frame;
    run.frame = parentFrame - 0xc;
    destroyResource(run, manager, pool);
    run.frame = parentFrame;
    run.put(sound + 0x10, 0);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b44f0:
        return transferPCM(run, receiver, arguments[0], arguments[1]);
    case 0x4b4a20:
        return loadPCM(run, receiver, arguments[0], arguments[1]);
    case 0x4b4ae0:
        destroyResource(run, receiver, arguments[0]);
        return 0;
    case 0x4c8850:
        return loadSound(run, receiver, arguments[0]);
    case 0x4c88b0:
        unloadSound(run, receiver);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_audio_pcm_transfer_entry, owned, body)
