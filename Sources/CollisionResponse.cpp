#include "CollisionResponse.h"

// Coordinate operations wrap as on the original 32-bit x86. Comparisons are
// signed; tokens replace pointers without changing actor-list order.
static bool less(uint32_t a, uint32_t b) {
    return int32_t(a) < int32_t(b);
}
static bool greater(uint32_t a, uint32_t b) {
    return int32_t(a) > int32_t(b);
}
static uint32_t sample(const ClawCollisionWorld *w, uint32_t x, uint32_t y) {
    return claw_world_point_attribute(w->cells, w->rowOffsets, w->width, w->height, w->shiftX, w->shiftY,
                                      w->descriptions, w->descriptionCount, x, y, 0, 0);
}
static uint32_t nextProbe(uint32_t current, uint32_t end, uint32_t step) {
    return current == end ? current + 1 : current + step;
}

// 0x4cc420/0x4cc570: a solid side sample rejects the entire horizontal move.
static uint32_t side(const ClawCollisionWorld *w, const ClawCollisionActor *a, uint32_t x, uint32_t y, uint32_t *outX,
                     bool right) {
    const uint32_t edgeX = x + (right ? a->moveRect.right : a->moveRect.left);
    const uint32_t bottom = y + a->moveRect.bottom;
    uint32_t probe = y + a->moveRect.top;
    while (!greater(probe, bottom)) {
        if (sample(w, edgeX, probe) == 1) {
            *outX = a->x;
            return right ? 0x60000 : 0xa0000;
        }
        if (probe == bottom)
            ++probe;
        else {
            probe += a->stepY;
            if (greater(probe, bottom))
                probe = bottom;
        }
    }
    *outX = x;
    return 0;
}

// 0x4cc6c0: determine whether a standing/walking actor still has tile support.
static uint32_t ground(const ClawCollisionWorld *w, ClawCollisionActor *a, uint32_t x, uint32_t y) {
    const uint32_t right = x + a->moveRect.right, foot = y + a->moveRect.bottom + 1;
    for (uint32_t probe = x + a->moveRect.left; !greater(probe, right); probe = nextProbe(probe, right, a->stepX)) {
        const uint32_t attribute = sample(w, probe, foot);
        if (attribute == 1 || attribute == 2) {
            const uint32_t above = sample(w, probe, foot - 1);
            if (above != 1 && above != 2)
                return y;
        } else if (a->mode != 6 && attribute == 3 && sample(w, probe, foot) == 3 && sample(w, probe, foot - 1) != 3) {
            return y;
        }
    }
    a->mode = 4;
    return y;
}

// 0x4cc9a0: landing and hazard sampling while descending.
static uint32_t falling(const ClawCollisionWorld *w, ClawCollisionActor *a, uint32_t x, uint32_t y) {
    const uint32_t left = x + a->moveRect.left, right = x + a->moveRect.right;
    const uint32_t foot = y + a->moveRect.bottom + 1;
    if (sample(w, x, foot) == 4)
        a->flags |= 0x400000;
    for (uint32_t probe = left; !greater(probe, right); probe = nextProbe(probe, right, a->stepX)) {
        const uint32_t attribute = sample(w, probe, foot);
        if (attribute == 1 || attribute == 2) {
            const uint32_t oldFoot = a->y + a->moveRect.bottom;
            for (uint32_t scan = foot; !less(scan, oldFoot); --scan) {
                const uint32_t result = sample(w, probe, scan);
                if (result != 1 && result != 2) {
                    a->mode = 1;
                    return scan - a->moveRect.bottom;
                }
            }
        } else if (a->mode != 6 && attribute == 3) {
            const uint32_t oldFoot = foot - (y - a->y);
            if (less(oldFoot, foot)) {
                for (uint32_t scan = foot - 1; !less(scan, oldFoot); --scan) {
                    if (sample(w, probe, scan) != 3) {
                        a->mode = 1;
                        return scan - a->moveRect.bottom;
                    }
                }
            }
        }
    }
    return y;
}

// 0x4ccc50: upward movement; the backtracking query uses the rectangle's left
// edge even if a different horizontal probe first found the obstruction.
static uint32_t ceiling(const ClawCollisionWorld *w, ClawCollisionActor *a, uint32_t x, uint32_t y) {
    const uint32_t left = x + a->moveRect.left, right = x + a->moveRect.right;
    const uint32_t head = y + a->moveRect.top - 1;
    for (uint32_t probe = left; !greater(probe, right); probe = nextProbe(probe, right, a->stepX)) {
        if (sample(w, probe, head) == 1) {
            const uint32_t oldHead = a->y + a->moveRect.top - 1;
            for (uint32_t scan = head; !greater(scan, oldHead); ++scan) {
                if (sample(w, left, scan) != 1) {
                    a->mode = 4;
                    return scan - a->moveRect.top;
                }
            }
        }
    }
    return y;
}

// 0x4cd120 returns the containing tile width, not its attribute rectangle.
static bool ladderSpan(const ClawCollisionWorld *w, uint32_t x, uint32_t y, uint32_t *left, uint32_t *right) {
    int32_t px = int32_t(x), py = int32_t(y);
    if (px < 0)
        px = 0;
    else if (px >= w->width)
        px = w->width - 1;
    if (py < 0)
        py = 0;
    else if (py >= w->height)
        py = w->height - 1;
    const uint32_t column = uint32_t(px) >> w->shiftX, row = uint32_t(py) >> w->shiftY;
    const uint32_t cell = w->cells[w->rowOffsets[row] + column];
    if (cell == 0xffffffff || cell == 0xeeeeeeee)
        return false;
    const uint32_t id = cell & 0xffff;
    if (id >= w->descriptionCount)
        return false; // Native malformed-input extension.
    *left = column << w->shiftX;
    *right = *left + w->descriptions[id].width - 1;
    return true;
}
static uint32_t ladderX(const ClawCollisionWorld *w, uint32_t x, uint32_t y, uint32_t options) {
    if (!(options & 0x10))
        return x;
    uint32_t left, right;
    return ladderSpan(w, x, y, &left, &right) ? uint32_t(int32_t(left + right) / 2) : x;
}

// 0x4cd060: preserve support only when the actor still touches its platform.
static bool supported(const ClawCollisionWorld *w, const ClawCollisionActor *a, uint32_t x, uint32_t y,
                      uint32_t options) {
    if (!a->supportToken || !(options & 8))
        return false;
    for (uint32_t i = 0; i < w->actorCount; ++i) {
        const auto &platform = w->actors[i];
        if (platform.token != a->supportToken)
            continue;
        if (platform.type != 0x80 || platform.hitRect.left == 0xffffffff || a->moveRect.left == 0xffffffff)
            return false;
        if (less(x + a->moveRect.right, platform.x + platform.hitRect.left) ||
            less(platform.x + platform.hitRect.right, x + a->moveRect.left))
            return false;
        return y + a->moveRect.bottom == platform.y + platform.hitRect.top - 1;
    }
    return false;
}

// 0x4ccf80/0x4ccef0: platform acquisition uses actor-list order.
static bool acquirePlatform(const ClawCollisionWorld *w, ClawCollisionActor *a, uint32_t x, uint32_t y,
                            uint32_t options, uint32_t *outY) {
    if (!(options & 8))
        return false;
    for (uint32_t i = 0; i < w->actorCount; ++i) {
        const auto &p = w->actors[i];
        if (p.type != 0x80 || p.hitRect.left == 0xffffffff || a->moveRect.left == 0xffffffff || greater(a->y, y))
            continue;
        const uint32_t platformTop = p.y + p.hitRect.top;
        const uint32_t oldFoot = a->y + a->moveRect.bottom, newFoot = y + a->moveRect.bottom;
        const uint32_t upwardDelta = greater(p.deltaY, 0) ? 0 : p.deltaY;
        if (greater(oldFoot, platformTop - upwardDelta) || less(x + a->moveRect.right, p.x + p.hitRect.left) ||
            greater(x + a->moveRect.left, p.x + p.hitRect.right))
            continue;
        if (oldFoot == newFoot ? newFoot != platformTop - 1 : less(newFoot, platformTop - 1))
            continue;
        *outY = platformTop - a->moveRect.bottom - 1;
        a->mode = 1;
        a->supportToken = p.token;
        a->flags |= 0x10;
        return true;
    }
    return false;
}

static uint32_t groundedMove(const ClawCollisionWorld *w, ClawCollisionActor *a, uint32_t x, uint32_t y,
                             uint32_t options) {
    uint32_t result = 0;
    if (greater(x, a->x))
        result = side(w, a, x, y, &x, true);
    else if (less(x, a->x))
        result = side(w, a, x, y, &x, false);
    if (less(y, a->y))
        y = ceiling(w, a, x, y);
    if (options & 1) {
        const uint32_t head = y + a->moveRect.top - 1;
        if (sample(w, x, head) == 3) {
            x = ladderX(w, x, head, options);
            a->mode = 6;
            a->x = x;
            a->y = y;
            return result;
        }
    } else if (options & 2) {
        const uint32_t foot = y + a->moveRect.bottom + 2;
        if (sample(w, x, foot) == 3) {
            x = ladderX(w, x, foot, options);
            a->mode = 6;
            a->x = x;
            a->y = y;
            return result;
        }
    }
    if (!(a->flags & 0x10))
        y = ground(w, a, x, y);
    else if (!supported(w, a, x, y, options))
        a->mode = 4;
    a->x = x;
    a->y = y;
    return result;
}
static uint32_t fallingMove(const ClawCollisionWorld *w, ClawCollisionActor *a, uint32_t x, uint32_t y,
                            uint32_t options) {
    const uint32_t requestedX = x;
    uint32_t result = 0;
    if (greater(x, a->x))
        result = side(w, a, x, y, &x, true);
    else if (less(x, a->x))
        result = side(w, a, x, y, &x, false);
    acquirePlatform(w, a, x, y, options, &y);
    if (a->mode != 1)
        y = falling(w, a, x, y);
    if ((options & 1) && sample(w, x, y + a->moveRect.top - 1) == 3) {
        x = ladderX(w, x, y + a->moveRect.top - 1, options);
        a->mode = 6;
    }
    if (a->mode == 1 && x != requestedX && (result & 0x20000)) {
        result &= 0xfff1ffff;
        if (greater(x, a->x))
            result |= side(w, a, x, y, &x, true);
        else if (less(x, a->x))
            result |= side(w, a, x, y, &x, false);
    }
    a->x = x;
    a->y = y;
    return result;
}
static uint32_t risingMove(const ClawCollisionWorld *w, ClawCollisionActor *a, uint32_t x, uint32_t y,
                           uint32_t options) {
    uint32_t result = 0;
    if (greater(x, a->x))
        result = side(w, a, x, y, &x, true);
    else if (less(x, a->x))
        result = side(w, a, x, y, &x, false);
    y = ceiling(w, a, x, y);
    const uint32_t head = y + a->moveRect.top - 1;
    if ((options & 1) && sample(w, x, head) == 3) {
        x = ladderX(w, x, head, options);
        a->mode = 6;
    }
    a->x = x;
    a->y = y;
    return result;
}

// 0x4ccdd0 scans upward for the first non-ladder sample.
static bool ladderFloor(const ClawCollisionWorld *w, uint32_t x, uint32_t start, uint32_t end, uint32_t *out) {
    if (!less(end, start))
        return false;
    for (uint32_t scan = start - 1; !less(scan, end); --scan) {
        if (sample(w, x, scan) != 3) {
            *out = scan + 1;
            return true;
        }
    }
    return false;
}
static uint32_t climbingMove(const ClawCollisionWorld *w, ClawCollisionActor *a, uint32_t x, uint32_t y) {
    if (greater(y, a->y)) {
        y = falling(w, a, x, y);
        if (a->mode != 1 && sample(w, x, y + a->moveRect.top - 1) != 3 && sample(w, x, y + a->moveRect.bottom + 1) != 3)
            a->mode = 4;
    } else {
        y = ceiling(w, a, x, y);
        const uint32_t foot = y + a->moveRect.bottom + 1;
        uint32_t floor;
        if (sample(w, x, y + a->moveRect.top - 1) != 3 && sample(w, x, foot) != 3 &&
            ladderFloor(w, x, (foot - y) + a->y, foot, &floor) && less(y, floor)) {
            a->mode = 1;
            y = floor - a->moveRect.bottom - 1;
        }
    }
    uint32_t result = 0;
    if (greater(x, a->x))
        result = side(w, a, x, y, &x, true);
    else if (less(x, a->x))
        result = side(w, a, x, y, &x, false);
    a->x = x;
    a->y = y;
    return result;
}

extern "C" uint32_t claw_collision_resolve(const ClawCollisionWorld *w, ClawCollisionActor *a, uint32_t x, uint32_t y,
                                           uint32_t options) {
    // Original 0x4cbcd0, with original nested response helpers recovered above.
    const uint32_t oldX = a->x, oldY = a->y;
    uint32_t result = 0;
    switch (a->mode) {
    case 1:
    case 2:
    case 5:
        result = groundedMove(w, a, x, y, options);
        break;
    case 3:
        result = risingMove(w, a, x, y, options);
        if (a->mode == 4)
            result |= 0x800000;
        break;
    case 4:
        result = fallingMove(w, a, x, y, options);
        if (a->mode == 1)
            result |= 0x1000000;
        break;
    case 6:
        result = climbingMove(w, a, x, y);
        break;
    case 7:
        a->x = x;
        a->y = y;
        break;
    case 8:
        if (less(y, oldY)) {
            result = risingMove(w, a, x, y, options);
            if (a->mode == 4) {
                result |= 0x800000;
                a->mode = 8;
            }
        } else {
            result = fallingMove(w, a, x, y, options);
            if (a->mode == 1)
                result |= 0x1000000;
        }
        break;
    default:
        break;
    }
    if (result & 0x1820000)
        result |= 0x10000;
    if (a->flags & 0x400000)
        result |= 0x100000;
    if (a->flags & 0x10)
        result |= 0x200000;
    if (a->x == oldX && a->y == oldY)
        result |= 0x400000;
    return result;
}

extern "C" uint32_t claw_collision_response_helper(uint32_t function, const ClawCollisionWorld *w,
    ClawCollisionActor *a, uint32_t x, uint32_t y, uint32_t options) {
    switch (function) {
    case 0x4cca90: return groundedMove(w, a, x, y, options);
    case 0x4ccc60: return fallingMove(w, a, x, y, options);
    case 0x4cce20: return risingMove(w, a, x, y, options);
    case 0x4ccf20: return climbingMove(w, a, x, y);
    default: return 0;
    }
}

static uint32_t absolute32(uint32_t v) {
    const uint32_t sign = int32_t(v) < 0 ? 0xffffffff : 0;
    return (v ^ sign) - sign;
}
extern "C" uint32_t claw_collision_move(const ClawCollisionWorld *w, ClawCollisionActor *a, uint32_t x, uint32_t y,
                                        uint32_t options) {
    return claw_collision_move_with_resolver(w, a, x, y, options,
        [](const ClawCollisionWorld *world, ClawCollisionActor *actor, uint32_t px, uint32_t py, uint32_t flags, void *) {
            return claw_collision_resolve(world, actor, px, py, flags);
        }, nullptr);
}
extern "C" uint32_t claw_collision_move_with_resolver(const ClawCollisionWorld *w, ClawCollisionActor *a,
    uint32_t x, uint32_t y, uint32_t options, ClawCollisionResolver resolve, void *user) {
    // Original 0x4cbb60 splits large displacement into bounded resolver calls.
    if ((!greater(absolute32(a->x - x), w->maximumStepX) && !greater(absolute32(a->y - y), w->maximumStepY)) ||
        (a->flags & 0x10) || a->mode == 7) {
        return resolve(w, a, x, y, options, user);
    }
    const uint32_t originalMode = a->mode;
    const uint32_t stepX = less(x, a->x) ? 0u - w->maximumStepX : w->maximumStepX;
    const uint32_t stepY = less(y, a->y) ? 0u - w->maximumStepY : w->maximumStepY;
    for (;;) {
        uint32_t nextX = a->x + stepX, nextY = a->y + stepY;
        if (int32_t(stepX) < 1 ? less(nextX, x) : less(x, nextX))
            nextX = x;
        if (int32_t(stepY) < 1 ? less(nextY, y) : less(y, nextY))
            nextY = y;
        const uint32_t result = resolve(w, a, nextX, nextY, options, user);
        if (a->mode != originalMode || (result & 0x10000) || (a->x == x && a->y == y) || (result & 0x400000))
            return result;
    }
}

extern "C" uint32_t claw_collision_horizontal_clear(const ClawCollisionWorld *w, uint32_t x, uint32_t y,
                                                    uint32_t target, uint32_t step, uint32_t *fault) {
    if (fault)
        *fault = 0;
    if (!w || !w->cells || !w->rowOffsets || !w->descriptions || w->width < 1 || w->height < 1 || int32_t(step) < 1) {
        if (fault)
            *fault = 1;
        return 0;
    }
    const bool right = less(x, target);
    uint32_t current = x, iterations = 0;
    while (right ? !less(target, current) : !less(current, target)) {
        if (sample(w, current, y) == 1)
            return 0;
        uint32_t next = right ? current + step : current - step;
        if ((right && !less(current, next)) || (!right && !less(next, current)) || ++iterations > 2000000) {
            if (fault)
                *fault = 1;
            return 0;
        }
        current = next;
    }
    return sample(w, target, y) != 1;
}

extern "C" uint32_t claw_collision_place_on_ground(const ClawCollisionWorld *w, ClawCollisionActor *a) {
    // Original 0x4cd800. It samples the initial foot before checking the lower
    // world boundary, and accepts ladder as well as solid/platform attributes.
    if (a->moveRect.left == 0x80000000u || !w->cells)
        return 0;
    const uint32_t foot = a->y + a->moveRect.bottom;
    uint32_t scan = foot;
    for (;;) {
        const uint32_t attribute = sample(w, a->x, scan);
        if (attribute == 1 || attribute == 2 || attribute == 3) {
            a->y += scan - foot - 1;
            return 1;
        }
        ++scan;
        if (!less(scan, uint32_t(w->height)))
            return 0;
    }
}
