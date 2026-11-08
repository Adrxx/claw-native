#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4d7860:
    case 0x4d78f0:
        return 4;
    case 0x4d7990:
    case 0x4d7ba0:
    case 0x4d7db0:
    case 0x4d7fc0:
        return 5;
    case 0x4d81d0:
        return 3;
    default:
        return -1;
    }
}

struct EntryFrame {
    Run &run;
    uint32_t previous;
    EntryFrame(Run &run, uint32_t distance) : run(run), previous(run.frame) {
        run.frame -= distance;
    }
    ~EntryFrame() {
        run.frame = previous;
    }
};

// 0x4d81d0. Actor +0x08 flags; +0x5c/+0x60 position; +0x90 callback
// table; +0x94 contacted peer; +0xe8 category; +0xf4 category mask;
// +0x134/+0x138/+0x13c/+0x140 contact bounds. Manager +0x0c owns the
// scene, whose +0x08 collection has its linked-list head at +0x14.
uint32_t contact(Run &run, uint32_t manager, uint32_t mover, uint32_t x, uint32_t y) {
    if (!(run.get(mover + 0x08) & 0x100))
        return 0;
    uint32_t node = run.get(run.get(run.get(manager + 0x0c) + 0x08) + 0x14);
    while (node) {
        uint32_t next = run.get(node);
        uint32_t peer = run.get(node + 0x08);
        if (peer != mover && (run.get(peer + 0x08) & 0x100) &&
            (run.get(mover + 0xf4) & run.get(peer + 0xe8)) &&
            run.get(mover + 0x134) != 0x80000000 &&
            run.get(peer + 0x134) != 0x80000000) {
            uint32_t moverX = run.get(mover + 0x5c);
            uint32_t moverY = run.get(mover + 0x60);
            uint32_t left = run.get(mover + 0x134);
            uint32_t top = run.get(mover + 0x138);
            uint32_t right = run.get(mover + 0x13c);
            uint32_t bottom = run.get(mover + 0x140);
            uint32_t peerX = run.get(peer + 0x5c);
            uint32_t peerY = run.get(peer + 0x60);
            uint32_t peerLeft = peerX + run.get(peer + 0x134);
            uint32_t peerTop = peerY + run.get(peer + 0x138);
            uint32_t peerRight = peerX + run.get(peer + 0x13c);
            uint32_t peerBottom = peerY + run.get(peer + 0x140);
            bool already = s32(moverX + left) <= s32(peerRight) &&
                           s32(moverX + right) >= s32(peerLeft) &&
                           s32(moverY + top) <= s32(peerBottom) &&
                           s32(moverY + bottom) >= s32(peerTop);
            if (!already && s32(x + left) <= s32(peerRight) &&
                s32(x + right) >= s32(peerLeft) &&
                s32(y + top) <= s32(peerBottom) &&
                s32(y + bottom) >= s32(peerTop)) {
                uint32_t callback = run.get(mover + 0x90);
                uint32_t accepted = 1;
                if (callback) {
                    run.put(mover + 0x94, peer);
                    run.stackPointer = run.frame - 0x34;
                    accepted = run.call(run.get(callback + 0x10), 0, {mover});
                }
                if (accepted) {
                    if (run.get(mover + 0xf4) & run.get(peer + 0xe8)) {
                        uint32_t peerCallback = run.get(peer + 0x90);
                        if (peerCallback) {
                            run.put(peer + 0x94, mover);
                            run.stackPointer = run.frame - 0x34;
                            run.call(run.get(peerCallback + 0x10), 0, {peer});
                        }
                    }
                    return 1;
                }
            }
        }
        node = next;
    }
    return 0;
}

// Inline tile queries in the four probes. Manager +0x5c is the map;
// map +0x30/+0x34 dimensions, +0x8c/+0x90 tile shifts, +0x20 tile ids,
// +0x24 row starts. Manager +0x4c holds the tile-classifier objects.
uint32_t sampleTile(Run &run, uint32_t manager, uint32_t x, uint32_t y) {
    uint32_t clampedX = x;
    if (s32(x) < 0)
        clampedX = 0;
    else {
        uint32_t width = run.get(run.get(manager + 0x5c) + 0x30);
        if (s32(x) >= s32(width))
            clampedX = width - 1;
    }
    uint32_t clampedY = y;
    if (s32(y) < 0)
        clampedY = 0;
    else {
        uint32_t height = run.get(run.get(manager + 0x5c) + 0x34);
        if (s32(y) >= s32(height))
            clampedY = height - 1;
    }
    uint32_t map = run.get(manager + 0x5c);
    uint32_t shiftX = run.get(map + 0x8c) & 31;
    uint32_t shiftY = run.get(map + 0x90) & 31;
    uint32_t tileX = uint32_t(s32(clampedX) >> shiftX);
    uint32_t tileY = uint32_t(s32(clampedY) >> shiftY);
    uint32_t row = run.get(run.get(map + 0x24) + tileY * 4);
    uint32_t tile = run.get(run.get(map + 0x20) + (row + tileX) * 4);
    if (tile == 0xeeeeeeee || tile == 0xffffffff)
        return 0;
    uint32_t classifier = run.get(run.get(manager + 0x4c) + (tile & 0xffff) * 4);
    run.stackPointer = run.frame - 0x34;
    return run.vcall(classifier, 0x18, {clampedX - (tileX << shiftX), clampedY - (tileY << shiftY)});
}

// 0x4d7990/0x4d7ba0/0x4d7db0/0x4d7fc0. Sample a destination edge,
// backtrack solid tiles, then test contact at the resulting proposed position.
uint32_t probe(Run &run, uint32_t manager, uint32_t mover, uint32_t x, uint32_t y,
               uint32_t output, bool horizontal, bool positive, uint32_t edgeOffset,
               uint32_t tileMask, uint32_t bumpMask) {
    uint32_t coordinateOffset = horizontal ? 0x5c : 0x60;
    uint32_t spanStartOffset = horizontal ? 0x138 : 0x134;
    uint32_t spanEndOffset = horizontal ? 0x140 : 0x13c;
    uint32_t spanBase = horizontal ? y : x;
    uint32_t proposed = horizontal ? x : y;
    uint32_t edge = proposed + run.get(mover + edgeOffset);
    uint32_t limit = spanBase + run.get(mover + spanEndOffset);
    uint32_t sample = spanBase + run.get(mover + spanStartOffset);
    uint32_t flags = 0;
    while (s32(sample) <= s32(limit)) {
        uint32_t kind = sampleTile(run, manager, horizontal ? edge : sample, horizontal ? sample : edge);
        if (kind == 1 || (kind == 2 && !(run.get(mover + 0x08) & 0x400))) {
            uint32_t currentEdge = run.get(mover + coordinateOffset) + run.get(mover + edgeOffset);
            uint32_t back = edge + (positive ? 0xffffffff : 1);
            flags |= tileMask;
            for (;;) {
                if (positive ? s32(back) <= s32(currentEdge) : s32(back) >= s32(currentEdge)) {
                    proposed = run.get(mover + coordinateOffset);
                    break;
                }
                run.stackPointer = run.frame - 0x34;
                uint32_t backKind = run.call(0x421ad0, manager, {horizontal ? back : sample, horizontal ? sample : back});
                if (!backKind) {
                    proposed = back - run.get(mover + edgeOffset);
                    break;
                }
                back += positive ? 0xffffffff : 1;
            }
            if (proposed == run.get(mover + coordinateOffset)) {
                run.put(output, run.get(mover + coordinateOffset));
                return flags;
            }
        }
        if (sample == limit)
            sample += 1;
        else {
            sample += run.get(mover + (horizontal ? 0xfc : 0xf8));
            if (s32(sample) > s32(limit))
                sample = limit;
        }
    }
    uint32_t accepted;
    {
        EntryFrame frame(run, 0x38);
        accepted = contact(run, manager, mover, horizontal ? proposed : x, horizontal ? y : proposed);
    }
    if (accepted) {
        run.put(output, run.get(mover + coordinateOffset));
        return flags | bumpMask;
    }
    run.put(output, proposed);
    return flags;
}

// 0x4d78f0. Horizontal resolution precedes vertical resolution. The argument
// slots are the original temporary outputs, so vertical contact sees adjusted x.
uint32_t moveAxes(Run &run, uint32_t manager, uint32_t mover, uint32_t x, uint32_t y) {
    uint32_t flags = 0;
    uint32_t xSlot = run.frame + 0x08;
    uint32_t ySlot = run.frame + 0x0c;
    run.put(xSlot, x);
    run.put(ySlot, y);
    if (s32(x) > run.gets(mover + 0x5c)) {
        EntryFrame frame(run, 0x28);
        flags = probe(run, manager, mover, x, y, xSlot, true, true, 0x13c, 0x60000, 0x22000000);
        x = run.get(xSlot);
    } else if (s32(x) < run.gets(mover + 0x5c)) {
        EntryFrame frame(run, 0x28);
        flags = probe(run, manager, mover, x, y, xSlot, true, false, 0x134, 0xa0000, 0x82000000);
        x = run.get(xSlot);
    }
    if (s32(y) > run.gets(mover + 0x60)) {
        EntryFrame frame(run, 0x28);
        flags |= probe(run, manager, mover, x, y, ySlot, false, true, 0x140, 0x1020000, 0x42000000);
        y = run.get(ySlot);
        x = run.get(xSlot);
    } else if (s32(y) < run.gets(mover + 0x60)) {
        EntryFrame frame(run, 0x28);
        flags |= probe(run, manager, mover, x, y, ySlot, false, false, 0x138, 0x820000, 0x12000000);
        y = run.get(ySlot);
        x = run.get(xSlot);
    }
    run.put(mover + 0x5c, x);
    run.put(mover + 0x60, y);
    return flags;
}

// 0x4d7860. Alternate movement types 1 and 2 resolve axes; type 7 teleports.
uint32_t move(Run &run, uint32_t manager, uint32_t mover, uint32_t x, uint32_t y) {
    uint32_t type = run.get(mover + 0xe4);
    uint32_t oldX = run.get(mover + 0x5c);
    uint32_t oldY = run.get(mover + 0x60);
    uint32_t flags = 0;
    if (s32(type) > 0 && s32(type) <= 2) {
        EntryFrame frame(run, 0x20);
        flags = moveAxes(run, manager, mover, x, y);
    } else if (type == 7) {
        run.put(mover + 0x5c, x);
        run.put(mover + 0x60, y);
    }
    if (flags & 0x20000)
        flags |= 0x10000;
    uint32_t actorFlags = run.get(mover + 0x08);
    if (actorFlags & 0x400000)
        flags |= 0x100000;
    if (actorFlags & 0x10)
        flags |= 0x200000;
    if (run.get(mover + 0x5c) == oldX && run.get(mover + 0x60) == oldY)
        flags |= 0x400000;
    return flags;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4d7860:
        return move(run, receiver, arguments[0], arguments[1], arguments[2]);
    case 0x4d78f0:
        return moveAxes(run, receiver, arguments[0], arguments[1], arguments[2]);
    case 0x4d7990:
        return probe(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3], true, true, 0x13c, 0x60000, 0x22000000);
    case 0x4d7ba0:
        return probe(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3], true, false, 0x134, 0xa0000, 0x82000000);
    case 0x4d7db0:
        return probe(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3], false, true, 0x140, 0x1020000, 0x42000000);
    case 0x4d7fc0:
        return probe(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3], false, false, 0x138, 0x820000, 0x12000000);
    case 0x4d81d0:
        return contact(run, receiver, arguments[0], arguments[1], arguments[2]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_v13_contact_entry, owned, body)
