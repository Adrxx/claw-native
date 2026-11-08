#include <cstdint>
// Recovered from the animation updater's bounded movement block.
// Offsets are abstracted, arithmetic remains modulo 2^32 like x86.
// This is animation-record movement, not player physics or collision.
extern "C" void claw_animation_movement(uint32_t *actor, uint32_t mode, uint32_t dx, uint32_t dy) {
    actor[0x10 / 4] = 0;
    actor[0x14 / 4] = 0;
    switch (mode) {
    case 1:
        actor[0x10 / 4] = dx;
        actor[0x14 / 4] = dy;
        break;
    case 2:
        actor[0x4c / 4] += (actor[0x40 / 4] & 2) ? uint32_t(0) - dx : dx;
        actor[0x50 / 4] += dy;
        break;
    case 3:
        actor[0x4c / 4] = dx;
        actor[0x50 / 4] = dy;
        break;
    default:
        break;
    }
}
// Recovered prefix: return -1 for no sequence; otherwise consume a pending
// delay. ready is a boundary signal, not the original routine's return value.
extern "C" uint32_t claw_animation_delay(uint32_t *state, uint32_t delta, uint32_t *ready) {
    *ready = 0;
    if (!state[0x08 / 4])
        return 0xffffffff;
    auto &remaining = state[0x14 / 4];
    if (remaining) {
        if (!state[0x18 / 4]) {
            --remaining;
            return state[0x24 / 4];
        }
        if (delta < remaining) {
            remaining -= delta;
            return state[0x24 / 4];
        }
        remaining = 0;
    }
    state[0x24 / 4] = state[0x20 / 4];
    *ready = 1;
    return state[0x24 / 4];
}
