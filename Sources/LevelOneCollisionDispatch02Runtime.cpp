// Level 1 tile collision movement resolvers
//
// Guest tokens, callback order and aliased argument slots follow the v1.0
// entries retained in the dispatch table below.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using claw::s32;
using namespace claw::recovered::v10;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4cbff0:
        return 4;
    case 0x4cc1b0:
        return 4;
    case 0x4cc420:
        return 5;
    case 0x4cc570:
        return 5;
    case 0x4cc6c0:
        return 4;
    case 0x4cc9a0:
        return 4;
    case 0x4ccc50:
        return 4;
    case 0x4ccef0:
        return 5;
    case 0x4cd1c0:
        return 2;
    case 0x4cd800:
        return 2;
    default:
        return -1;
    }
}

// Level object ("self", ECX): +0x4c table of tile type objects, +0x5c tile plane, +0xc platform holder.
// Tile plane: +0x20 tile id array, +0x24 row offset array, +0x30 width, +0x34 height,
// +0x8c column shift, +0x90 row shift.
// Actor: +0x08 flags, +0x4c x, +0x50 y, +0x80 platform, +0xcc state, +0xdc x step, +0xe0 y step,
// +0x118 left, +0x11c top, +0x120 right, +0x124 bottom.

uint32_t arithmeticShiftRight(uint32_t value, uint32_t count) {
    return uint32_t(s32(value) >> (count & 0x1f));
}

// Clamp a pixel column into the tile plane (inlined at many original sites).
uint32_t clampColumn(Run &run, uint32_t self, uint32_t value) {
    CollisionManagerFields manager{run, self};
    if (s32(value) < 0)
        return 0;
    uint32_t planeToken = manager.tilePlane();
    CollisionTilePlaneFields tilePlane{run, planeToken};
    uint32_t limit = tilePlane.widthPixels();
    if (s32(value) < s32(limit))
        return value;
    return limit - 1;
}

// Clamp a pixel row into the tile plane.
uint32_t clampRow(Run &run, uint32_t self, uint32_t value) {
    CollisionManagerFields manager{run, self};
    if (s32(value) < 0)
        return 0;
    uint32_t planeToken = manager.tilePlane();
    CollisionTilePlaneFields tilePlane{run, planeToken};
    uint32_t limit = tilePlane.heightPixels();
    if (s32(value) < s32(limit))
        return value;
    return limit - 1;
}

// The tile type at a pixel, as the original inlines it: clamp, split into tile and remainder,
// look the tile id up, and ask the tile object (virtual slot +0x20). Empty ids give 0.
uint32_t tileType(Run &run, uint32_t self, uint32_t x, uint32_t y) {
    CollisionManagerFields manager{run, self};
    uint32_t px = clampColumn(run, self, x);
    uint32_t py = clampRow(run, self, y);
    uint32_t plane = manager.tilePlane();
    CollisionTilePlaneFields tilePlane{run, plane};
    uint32_t columnShift = tilePlane.columnShift();
    uint32_t tx = arithmeticShiftRight(px, columnShift);
    uint32_t rowShift = tilePlane.rowShift();
    uint32_t ty = arithmeticShiftRight(py, rowShift);
    uint32_t rx = px - (tx << (columnShift & 0x1f));
    uint32_t rowShift2 = tilePlane.rowShift();
    uint32_t ry = py - (ty << (rowShift2 & 0x1f));
    uint32_t rowStart = run.get(tilePlane.rowOffsets() + ty * 4);
    uint32_t id = run.get(tilePlane.tileIds() + (rowStart + tx) * 4);
    if (id == 0xeeeeeeee)
        return 0;
    if (id == 0xffffffff)
        return 0;
    uint32_t object = run.get(manager.tileTypes() + (id & 0xffff) * 4);
    return run.vcall(object, 0x20, {rx, ry});
}

// Same lookup, but the tile id comes from the original accessor 0x4410f0 (used once by 0x4cc6c0).
uint32_t tileTypeViaAccessor(Run &run, uint32_t self, uint32_t x, uint32_t y) {
    CollisionManagerFields manager{run, self};
    uint32_t px = clampColumn(run, self, x);
    uint32_t py = clampRow(run, self, y);
    uint32_t plane = manager.tilePlane();
    CollisionTilePlaneFields tilePlane{run, plane};
    uint32_t columnShift = tilePlane.columnShift();
    uint32_t tx = arithmeticShiftRight(px, columnShift);
    uint32_t rowShift = tilePlane.rowShift();
    uint32_t ty = arithmeticShiftRight(py, rowShift);
    uint32_t rx = px - (tx << (columnShift & 0x1f));
    uint32_t rowShift2 = tilePlane.rowShift();
    uint32_t ry = py - (ty << (rowShift2 & 0x1f));
    uint32_t id = run.call(0x4410f0, plane, {tx, ty});
    if (id == 0xeeeeeeee)
        return 0;
    if (id == 0xffffffff)
        return 0;
    uint32_t object = run.get(manager.tileTypes() + (id & 0xffff) * 4);
    return run.vcall(object, 0x20, {rx, ry});
}

// The sum wraps before CDQ. Keep the correction in uint32_t: even the
// INT_MIN bit pattern must avoid signed overflow before the arithmetic shift.
uint32_t halveWrappedSignedSum(uint32_t sum) {
    uint32_t sign = 0;
    if (s32(sum) < 0)
        sign = 0xffffffff;
    uint32_t adjusted = sum - sign;
    return uint32_t(s32(adjusted) >> 1);
}

// Shared body of 0x4cc420 and 0x4cc570: sweep the actor's vertical edge column at the target x
// and report the first blocked row. `edge` is the left (0x118) or right (0x120) offset.
uint32_t sweepColumn(Run &run, uint32_t self, uint32_t actor, uint32_t x, uint32_t y, uint32_t out,
                     uint32_t edge, uint32_t blocked) {
    ActorInteractionFields actorPosition{run, actor};
    CollisionActorFields actorCollision{run, actor};
    uint32_t column = run.get(actor + edge) + x;
    uint32_t last = actorCollision.probeOffset_0x124() + y;
    uint32_t row = actorCollision.probeOffset_0x11c() + y;
    while (s32(row) <= s32(last)) {
        uint32_t type = tileType(run, self, column, row);
        if (type == 1) {
            run.put(out, actorPosition.worldX());
            return blocked;
        }
        if (row == last) {
            row = row + 1;
        } else {
            row = row + actorCollision.verticalProbeStep();
            if (s32(row) > s32(last))
                row = last;
        }
    }
    run.put(out, x);
    return 0;
}

// 0x4cc420. thiscall, 5 stack argument(s), returns u32. Moving right: sweep the right edge.
uint32_t moveRight(Run &run, uint32_t self, uint32_t actor, uint32_t x, uint32_t y, uint32_t out) {
    return sweepColumn(run, self, actor, x, y, out, 0x120, 0x60000);
}

// 0x4cc570. thiscall, 5 stack argument(s), returns u32. Moving left: sweep the left edge.
uint32_t moveLeft(Run &run, uint32_t self, uint32_t actor, uint32_t x, uint32_t y, uint32_t out) {
    return sweepColumn(run, self, actor, x, y, out, 0x118, 0xa0000);
}

// 0x4ccef0. thiscall, 5 stack argument(s), returns u32. Looks for a platform (type 0x80 in the
// platform list) under the actor; on success sets state 1, the platform pointer and flag 0x10.
uint32_t scanPlatforms(Run &run, uint32_t self, uint32_t actor, uint32_t x, uint32_t y, uint32_t out,
                       uint32_t flags) {
    CollisionManagerFields manager{run, self};
    ActorInteractionFields actorPosition{run, actor};
    CollisionActorFields actorCollision{run, actor};
    if ((flags & 8) == 0)
        return 0;
    uint32_t node = run.get(run.get(manager.unknown_0xc() + 8) + 0x14);
    if (node == 0)
        return 0;
    uint32_t item = 0;
    for (;;) {
        uint32_t next = run.get(node);
        item = run.get(node + 8);
        if (run.get(item + 0xd0) == 0x80) {
            if (run.call(0x4ccf80, self, {actor, item, x, y, out, flags}) != 0)
                break;
        }
        node = next;
        if (node == 0)
            return 0;
    }
    actorCollision.motionState(1);
    actorCollision.unknown_0x80(item);
    uint32_t attachedFlags = actorPosition.flags();
    actorPosition.flags(attachedFlags | 0x10);
    return 1;
}

// 0x4cc9a0. thiscall, 4 stack argument(s), returns u32. Floor scan: returns the adjusted y.
uint32_t floorScan(Run &run, uint32_t self, uint32_t actor, uint32_t x, uint32_t y) {
    ActorInteractionFields actorPosition{run, actor};
    CollisionActorFields actorCollision{run, actor};
    uint32_t left = actorCollision.leftProbeOffset() + x;
    uint32_t right = actorCollision.rightProbeOffset() + x;
    uint32_t bottom = y + actorCollision.probeOffset_0x124() + 1;
    uint32_t first = tileType(run, self, x, bottom);
    if (first == 4) {
        uint32_t contactFlags = actorPosition.flags();
        actorPosition.flags(contactFlags | 0x400000);
    }
    uint32_t drop = y - actorPosition.worldY();
    uint32_t column = left;
    for (;;) {
        if (s32(column) > s32(right))
            return y;
        uint32_t type = tileType(run, self, column, bottom);
        if (type == 1 || type == 2) {
            uint32_t currentY = actorPosition.worldY();
            uint32_t bottomOffset = actorCollision.probeOffset_0x124();
            uint32_t limit = currentY + bottomOffset;
            uint32_t probe = bottom;
            while (s32(probe) >= s32(limit)) {
                uint32_t below = run.call(0x4207f0, self, {column, probe});
                if (below != 1 && below != 2) {
                    actorCollision.motionState(1);
                    return probe - actorCollision.probeOffset_0x124();
                }
                probe = probe - 1;
            }
        } else if (actorCollision.motionState() != 6 && type == 3) {
            uint32_t low = bottom - drop;
            if (s32(bottom) > s32(low)) {
                uint32_t probe = bottom - 1;
                while (s32(probe) >= s32(low)) {
                    uint32_t below = run.call(0x4207f0, self, {column, probe});
                    if (below != 3) {
                        actorCollision.motionState(1);
                        return probe - actorCollision.probeOffset_0x124();
                    }
                    probe = probe - 1;
                }
            }
        }
        if (column == right)
            column = column + 1;
        else
            column = column + actorCollision.horizontalProbeStep();
    }
}

// 0x4ccc50. thiscall, 4 stack argument(s), returns u32. Ceiling scan: returns the adjusted y.
uint32_t ceilingScan(Run &run, uint32_t self, uint32_t actor, uint32_t x, uint32_t y) {
    ActorInteractionFields actorPosition{run, actor};
    CollisionActorFields actorCollision{run, actor};
    uint32_t left = actorCollision.leftProbeOffset() + x;
    uint32_t right = actorCollision.rightProbeOffset() + x;
    uint32_t top = y + actorCollision.probeOffset_0x11c() - 1;
    uint32_t column = left;
    for (;;) {
        if (s32(column) > s32(right))
            return y;
        uint32_t type = tileType(run, self, column, top);
        if (type == 1) {
            uint32_t currentY = actorPosition.worldY();
            uint32_t topOffset = actorCollision.probeOffset_0x11c();
            uint32_t limit = currentY + topOffset - 1;
            uint32_t probe = top;
            while (s32(probe) <= s32(limit)) {
                uint32_t above = run.call(0x4207f0, self, {left, probe});
                if (above != 1) {
                    actorCollision.motionState(4);
                    return probe - actorCollision.probeOffset_0x11c();
                }
                probe = probe + 1;
            }
        }
        if (column == right)
            column = column + 1;
        else
            column = column + actorCollision.horizontalProbeStep();
    }
}

// 0x4cbff0. thiscall, 4 stack argument(s), returns u32.
// Arguments (actor, x, y, flags). The original passes the addresses of its own argument slots as
// out parameters, so those slots are modelled at their physical stack addresses.
uint32_t resolveMovementWithFloorAndPlatforms(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    ActorInteractionFields actorPosition{run, actor};
    CollisionActorFields actorCollision{run, actor};
    uint32_t x = arguments[1];
    uint32_t y = arguments[2];
    uint32_t flags = arguments[3];
    uint32_t slotActor = run.automatic(4);
    uint32_t slotX = run.automatic(8);
    uint32_t slotY = run.automatic(0xc);
    run.put(slotActor, actor);
    run.put(slotX, x);
    run.put(slotY, y);
    uint32_t originalX = x;
    uint32_t result = 0;
    uint32_t current = actorPosition.worldX();
    if (s32(x) > s32(current)) {
        result = moveRight(run, receiver, actor, x, y, slotX);
        x = run.get(slotX);
    } else if (s32(x) < s32(current)) {
        result = moveLeft(run, receiver, actor, x, y, slotX);
        x = run.get(slotX);
    }
    if ((flags & 8) != 0) {
        if (scanPlatforms(run, receiver, actor, x, y, slotActor, flags) != 0)
            y = run.get(slotActor);
        x = run.get(slotX);
    }
    if (actorCollision.motionState() != 1) {
        y = floorScan(run, receiver, actor, x, y);
        x = run.get(slotX);
    }
    if ((flags & 1) != 0) {
        uint32_t savedX = x;
        uint32_t probeY = actorCollision.probeOffset_0x11c() + y - 1;
        if (run.call(0x4207f0, receiver, {x, probeY}) == 3) {
            uint32_t nudge = flags & 0x10;
            if (nudge != 0) {
                run.put(slotActor, savedX);
                run.put(slotY, savedX);
                if (run.call(0x4cd120, receiver, {savedX, probeY, slotActor, slotY}) != 0)
                    savedX = halveWrappedSignedSum(run.get(slotY) + run.get(slotActor));
                actorCollision.motionState(6);
                run.put(slotX, savedX);
                x = savedX;
            } else {
                actorCollision.motionState(6);
            }
        }
    }
    if (actorCollision.motionState() == 1) {
        if (x != originalX) {
            if ((result & 0x20000) != 0) {
                result = result & 0xfff1ffff;
                uint32_t position = actorPosition.worldX();
                if (s32(x) > s32(position)) {
                    result = result | moveRight(run, receiver, actor, x, y, slotX);
                    x = run.get(slotX);
                } else if (s32(x) < s32(position)) {
                    result = result | moveLeft(run, receiver, actor, x, y, slotX);
                    x = run.get(slotX);
                }
            }
        }
    }
    actorPosition.worldX(x);
    actorPosition.worldY(y);
    return result;
}

// 0x4cc1b0. thiscall, 4 stack argument(s), returns u32.
// Arguments (actor, x, y, flags). Same shape as 0x4cbff0 without the platform and floor passes
// but with a ceiling scan; argument slots again serve as out parameters.
uint32_t resolveMovementWithCeiling(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    ActorInteractionFields actorPosition{run, actor};
    CollisionActorFields actorCollision{run, actor};
    uint32_t x = arguments[1];
    uint32_t y = arguments[2];
    uint32_t flags = arguments[3];
    uint32_t slotActor = run.automatic(4);
    uint32_t slotX = run.automatic(8);
    uint32_t slotY = run.automatic(0xc);
    uint32_t slotFlags = run.automatic(0x10);
    run.put(slotActor, actor);
    run.put(slotX, x);
    run.put(slotY, y);
    run.put(slotFlags, flags);
    uint32_t result = 0;
    uint32_t current = actorPosition.worldX();
    if (s32(x) > s32(current)) {
        result = moveRight(run, receiver, actor, x, y, slotX);
        x = run.get(slotX);
    } else if (s32(x) < s32(current)) {
        result = moveLeft(run, receiver, actor, x, y, slotX);
        x = run.get(slotX);
    }
    y = ceilingScan(run, receiver, actor, x, y);
    run.put(slotY, y);
    if ((flags & 1) != 0) {
        uint32_t probeY = actorCollision.probeOffset_0x11c() + y - 1;
        if (run.call(0x4207f0, receiver, {x, probeY}) == 3) {
            uint32_t nudge = flags & 0x10;
            uint32_t target = x;
            if (nudge != 0) {
                run.put(slotActor, x);
                run.put(slotFlags, x);
                if (run.call(0x4cd120, receiver, {x, probeY, slotActor, slotFlags}) != 0)
                    target = halveWrappedSignedSum(run.get(slotFlags) + run.get(slotActor));
            }
            if (nudge != 0)
                run.put(slotX, target);
            actorCollision.motionState(6);
        }
    }
    actorPosition.worldX(run.get(slotX));
    actorPosition.worldY(run.get(slotY));
    return result;
}

// 0x4cc420. thiscall, 5 stack argument(s), returns u32. Arguments (actor, x, y, out, unused).
uint32_t resolveRightwardSweep(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return moveRight(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3]);
}

// 0x4cc570. thiscall, 5 stack argument(s), returns u32. Arguments (actor, x, y, out, unused).
uint32_t resolveLeftwardSweep(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return moveLeft(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3]);
}

// 0x4cc6c0. thiscall, 4 stack argument(s), returns u32. Arguments (actor, x, y, unused).
// Landing check one row below the feet; sets state 4 when the whole width is clear.
uint32_t checkSupportAcrossFeet(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    CollisionActorFields actorCollision{run, actor};
    uint32_t x = arguments[1];
    uint32_t y = arguments[2];
    uint32_t right = actorCollision.rightProbeOffset() + x;
    uint32_t column = actorCollision.leftProbeOffset() + x;
    uint32_t below = actorCollision.probeOffset_0x124() + 1 + y;
    for (;;) {
        if (s32(column) > s32(right)) {
            actorCollision.motionState(4);
            return y;
        }
        uint32_t type = tileType(run, receiver, column, below);
        if (type == 1 || type == 2) {
            uint32_t above = tileType(run, receiver, column, below - 1);
            if (above != 1) {
                uint32_t accessor = tileTypeViaAccessor(run, receiver, column, below - 1);
                if (accessor != 2)
                    return y;
            }
        } else if (actorCollision.motionState() != 6 && type == 3) {
            if (run.call(0x4207f0, receiver, {column, below}) == 3) {
                if (run.call(0x4207f0, receiver, {column, below - 1}) != 3)
                    return y;
            }
        }
        if (column == right)
            column = column + 1;
        else
            column = column + actorCollision.horizontalProbeStep();
    }
}

// 0x4cc9a0. thiscall, 4 stack argument(s), returns u32. Arguments (actor, x, y, unused).
uint32_t resolveFloorHeight(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return floorScan(run, receiver, arguments[0], arguments[1], arguments[2]);
}

// 0x4ccc50. thiscall, 4 stack argument(s), returns u32. Arguments (actor, x, y, unused).
uint32_t resolveCeilingHeight(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return ceilingScan(run, receiver, arguments[0], arguments[1], arguments[2]);
}

// 0x4ccef0. thiscall, 5 stack argument(s), returns u32. Arguments (actor, x, y, out, flags).
uint32_t attachToSupportingPlatform(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return scanPlatforms(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3], arguments[4]);
}

// 0x4cd1c0. thiscall, 2 stack argument(s), returns u32. Arguments (actor, dx).
// Foot probe: three tile lookups one row below the feet at x + dx.
uint32_t hasSupportAtHorizontalOffset(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    ActorInteractionFields actorPosition{run, actor};
    CollisionActorFields actorCollision{run, actor};
    uint32_t dx = arguments[1];
    uint32_t bottomOffset = actorCollision.probeOffset_0x124();
    uint32_t currentY = actorPosition.worldY();
    // Re-probe and reload X after each callback, even at the same pixel.
    uint32_t row = bottomOffset + currentY + 1;
    if (tileType(run, receiver, dx + actorPosition.worldX(), row) == 1)
        return 1;
    if (tileType(run, receiver, dx + actorPosition.worldX(), row) == 2)
        return 1;
    if (tileType(run, receiver, dx + actorPosition.worldX(), row) != 3)
        return 0;
    return 1;
}

// 0x4cd800. thiscall, 2 stack argument(s), returns u32. Arguments (actor, unused).
// Scans down from the feet for the first solid tile and adds the distance to the actor's y.
uint32_t snapFeetToNextSupport(Run &run, uint32_t receiver, const uint32_t *arguments) {
    CollisionManagerFields manager{run, receiver};
    uint32_t actor = arguments[0];
    ActorInteractionFields actorPosition{run, actor};
    CollisionActorFields actorCollision{run, actor};
    if (actorCollision.leftProbeOffset() == 0x80000000)
        return 0;
    if (manager.tilePlane() == 0)
        return 0;
    uint32_t x = actorPosition.worldX();
    uint32_t bottomOffset = actorCollision.probeOffset_0x124();
    uint32_t currentY = actorPosition.worldY();
    uint32_t start = bottomOffset + currentY;
    uint32_t type = tileType(run, receiver, x, start);
    uint32_t planeToken = manager.tilePlane();
    CollisionTilePlaneFields tilePlane{run, planeToken};
    // The first tile callback precedes this height read; later scans keep it.
    uint32_t height = tilePlane.heightPixels();
    uint32_t row = start;
    while (type != 1 && type != 2 && type != 3) {
        row = row + 1;
        if (s32(row) >= s32(height))
            return 0;
        type = tileType(run, receiver, x, row);
    }
    uint32_t finalY = actorPosition.worldY();
    actorPosition.worldY(finalY + (row - start) - 1);
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4cbff0:
        return resolveMovementWithFloorAndPlatforms(run, receiver, arguments);
    case 0x4cc1b0:
        return resolveMovementWithCeiling(run, receiver, arguments);
    case 0x4cc420:
        return resolveRightwardSweep(run, receiver, arguments);
    case 0x4cc570:
        return resolveLeftwardSweep(run, receiver, arguments);
    case 0x4cc6c0:
        return checkSupportAcrossFeet(run, receiver, arguments);
    case 0x4cc9a0:
        return resolveFloorHeight(run, receiver, arguments);
    case 0x4ccc50:
        return resolveCeilingHeight(run, receiver, arguments);
    case 0x4ccef0:
        return attachToSupportingPlatform(run, receiver, arguments);
    case 0x4cd1c0:
        return hasSupportAtHorizontalOffset(run, receiver, arguments);
    case 0x4cd800:
        return snapFeetToNextSupport(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_collision_dispatch_02_entry, owned, body)
