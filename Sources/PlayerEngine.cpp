#include "PlayerEngine.h"

static void mirror(ClawPlayerRect &r) {
    // The original treats INT32_MIN in the left field as an absent rectangle.
    if (r.left == 0x80000000u)
        return;
    const uint32_t oldLeft = r.left;
    r.left = 0u - r.right;
    r.right = 0u - oldLeft;
}

extern "C" void claw_player_face_left(ClawPlayerBody *b, ClawPlayerDirection *d) {
    // Original v1.0 0x418080, including its nonzero facing-state check.
    if (!d->facing)
        return;
    b->renderFlags |= 2u;
    mirror(b->moveRect);
    mirror(b->hitRect);
    mirror(b->attackRect);
    d->facing = 0;
    d->idleTimer = 1500;
}

extern "C" void claw_player_face_right(ClawPlayerBody *b, ClawPlayerDirection *d) {
    // Original v1.0 0x418120 only changes a zero facing state.
    if (d->facing)
        return;
    b->renderFlags &= ~2u;
    mirror(b->moveRect);
    mirror(b->hitRect);
    mirror(b->attackRect);
    d->facing = 1;
    d->idleTimer = 1500;
}
