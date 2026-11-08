// Hermit crab combat states and transitions
//
// Recovered combat state transitions; external game callees remain original-backed.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x44b130:
        return 0;
    case 0x44b200:
        return 0;
    case 0x44b2b0:
        return 0;
    case 0x44b300:
        return 0;
    case 0x44b480:
        return 1;
    case 0x44b6a0:
        return 0;
    case 0x44b780:
        return 0;
    case 0x44b7e0:
        return 0;
    case 0x44b860:
        return 1;
    case 0x44b960:
        return 0;
    case 0x44b9e0:
        return 0;
    case 0x44bb40:
        return 0;
    case 0x44bc50:
        return 0;
    default:
        return -1;
    }
}

// Receiver fields: +0x0c collision actor, +0x10 state, +0x24 previous state,
// +0x40 gravity, +0x50 velocity, +0x58/+0x60 acceleration, +0x68 position,
// +0x80/+0x98 bounds, +0x118 previous position, +0x120 collision flags,
// +0x128 physics actor, +0x12c animation actor, +0x130 scene context,
// +0x134 previous animation, +0x138 rectangle, +0x184 attack mode,
// +0x18c direction, +0x210 normal rectangle, +0x220 strike rectangle,
// +0x280 target X, +0x308/+0x310/+0x32c/+0x408 animation IDs,
// +0x3a0/+0x400/+0x404 sound handles, +0x418/+0x41c sound timer/duration,
// +0x420/+0x424 launch timer/duration, +0x428 launch enabled,
// +0x42c pending launch, +0x430 prior collision.
// Actor fields: +0x0c scene, +0x40 facing, +0x4c/+0x50 position, +0x64 layer,
// +0x6c logic table, +0x74 collision, +0xcc mode, +0xd0 kind, +0x100 damage,
// +0x124 bottom edge, +0x138 rectangle, +0x16c animation ID,
// +0x188 animation state, +0x190 previous frame, +0x19c/+0x1a4 flags.
void state(Run &run, uint32_t receiver, uint32_t name) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t value = run.call(0x4dba00, 0x537668, {name});
    run.put(run.get(receiver + 0x10) + 0x1c, value);
}

void animation(Run &run, uint32_t receiver, uint32_t offset) {
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t next = run.get(receiver + offset);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {next});
}

void advance(Run &run, uint32_t receiver) {
    uint32_t elapsed = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {elapsed});
}

void sound(Run &run, uint32_t receiver, uint32_t offset, int32_t entryOffset) {
    uint32_t handle = run.get(receiver + offset);
    if (handle && run.get(0x532c0c)) {
        // Original sound descendants expose a local pointer to physical callbacks.
        // Preserve the CALL entry ESP: caller saves, four arguments, return word.
        uint32_t savedStackPointer = run.stackPointer;
        run.stackPointer = run.automatic(entryOffset);
        run.call(0x4b45f0, run.get(handle + 0x10), {run.get(0x532c10), 0, 0, 0});
        run.stackPointer = savedStackPointer;
    }
}

void timedSound(Run &run, uint32_t receiver, uint32_t offset, int32_t entryOffset) {
    if (run.get(0x537210) - run.get(receiver + 0x418) >= run.get(receiver + 0x41c)) {
        run.put(receiver + 0x41c, 200);
        run.put(receiver + 0x418, run.get(0x537210));
        sound(run, receiver, offset, entryOffset);
    }
}

void rectangle(Run &run, uint32_t receiver, uint32_t offset) {
    uint32_t dest = run.get(receiver + 0x0c) + 0x138;
    run.put(dest, run.get(receiver + offset));
    run.put(dest + 0x04, run.get(receiver + offset + 0x04));
    run.put(dest + 0x08, run.get(receiver + offset + 0x08));
    run.put(dest + 0x0c, run.get(receiver + offset + 0x0c));
    if (run.get8(run.get(receiver + 0x12c) + 0x40) & 2) {
        uint32_t actor = run.get(receiver + 0x0c);
        uint32_t left = run.get(actor + 0x138);
        uint32_t right = run.get(actor + 0x140);
        run.put(actor + 0x138, 0u - right);
        run.put(run.get(receiver + 0x0c) + 0x140, 0u - left);
    }
}

uint32_t function_44b480(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x44b130. Stop horizontal velocity, then select attack or timed launch.
uint32_t function_44b130(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    if (!run.get(receiver + 0x428)) {
        state(run, receiver, 0x527b70);
        return 0;
    }
    if (run.get(0x537210) - run.get(receiver + 0x420) >= run.get(receiver + 0x424)) {
        run.put(receiver + 0x424, 4000);
        run.put(receiver + 0x420, run.get(0x537210));
        run.put(receiver + 0x42c, 1);
        state(run, receiver, 0x527b48);
        animation(run, receiver, 0x310);
        return 0;
    }
    run.vcall(receiver, 0x44);
    return 0;
}

// 0x44b200. Choose stationary strike or a moving attack.
uint32_t function_44b200(Run &run, uint32_t receiver, const uint32_t *) {
    advance(run, receiver);
    int32_t mode = run.gets(receiver + 0x184);
    if (mode >= 2 && mode <= 3) {
        uint32_t speed = uint32_t(s32(run.call(0x4a3050, 0)) % 201) + 300;
        function_44b480(run, receiver, &speed);
    } else if (mode == 4) {
        if (run.icall(0x546ce0, {run.automatic(-0x10), receiver + 0x220, run.get(0x537e88) + 0x128})) {
            run.vcall(receiver, 0x58);
        } else {
            uint32_t speed = 500;
            function_44b480(run, receiver, &speed);
        }
    } else {
        run.vcall(receiver, 0x44);
    }
    return 0;
}

// 0x44b2b0. Enter strike.
uint32_t function_44b2b0(Run &run, uint32_t receiver, const uint32_t *) {
    state(run, receiver, 0x5272f0);
    animation(run, receiver, 0x310);
    return 0;
}

// 0x44b300. Strike hitbox activation and restoration.
uint32_t function_44b300(Run &run, uint32_t receiver, const uint32_t *) {
    advance(run, receiver);
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t id = run.get(actor + 0x16c);
    if ((id == 203 || id == 204) && (!run.get(actor + 0x1a4) || run.get(actor + 0x19c))) {
        rectangle(run, receiver, 0x220);
        timedSound(run, receiver, 0x3a0, -0x18);
    } else if (run.get(actor + 0x1a4) && !run.get(actor + 0x19c)) {
        rectangle(run, receiver, 0x210);
        run.vcall(receiver, 0x44);
    }
    return 0;
}

// 0x44b480. Ground-checked attack target and velocity.
uint32_t function_44b480(Run &run, uint32_t receiver, const uint32_t *arguments) {
    bool left = run.get(receiver + 0x18c) == 3;
    uint32_t playerX = run.get(run.get(0x537e88) + 0x4c);
    uint32_t delta = uint32_t(s32(run.call(0x4a3050, 0)) % 41) + 40;
    uint32_t target = left ? playerX + delta : playerX - delta;
    run.put(receiver + 0x280, target);
    double coordinate = double(s32(target));
    if (left ? run.getd(receiver + 0x80) > coordinate : !(run.getd(receiver + 0x98) >= coordinate)) {
        return 0;
    }
    uint32_t actor = run.get(receiver + 0x128);
    uint32_t y = run.get(actor + 0x124) + run.get(actor + 0x50) + 1;
    uint32_t tile = run.call(0x4207f0, run.get(run.get(actor + 0x0c) + 0x24), {target, y});
    if (tile != 1) {
        actor = run.get(receiver + 0x128);
        tile = run.call(0x4207f0, run.get(run.get(actor + 0x0c) + 0x24), {target, y});
        if (tile != 2) {
            actor = run.get(receiver + 0x128);
            tile = run.call(0x4207f0, run.get(run.get(actor + 0x0c) + 0x24), {target, y});
            if (tile != 3) {
                return 0;
            }
        }
    }
    actor = run.get(receiver + 0x128);
    if (run.call(0x4207f0, run.get(run.get(actor + 0x0c) + 0x24), {target, y - 1})) {
        return 0;
    }
    uint32_t speed = left ? 0u - arguments[0] : arguments[0];
    run.putd(receiver + 0x50, double(s32(speed)));
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x5c, 0);
    run.put(receiver + 0x60, 0);
    run.put(receiver + 0x64, 0);
    if (run.get(receiver + 0x18c) == 2) {
        actor = run.get(receiver + 0x12c);
        if (!(run.get8(actor + 0x40) & 2)) {
            uint32_t oldLeft = run.get(receiver + 0x138);
            uint32_t oldRight = run.get(receiver + 0x140);
            run.put(receiver + 0x138, 0u - oldRight);
            run.put(receiver + 0x140, 0u - oldLeft);
            run.put(actor + 0x40, run.get(actor + 0x40) | 2);
            run.call(0x4060b0, run.get(receiver + 0x12c));
        }
    } else {
        run.call(0x406310, receiver + 0x128);
    }
    state(run, receiver, 0x527b60);
    animation(run, receiver, 0x308);
    return 0;
}

// C0 includes unordered, and C3 means equal or unordered in these x87 tests.
bool movementComplete(Run &run, uint32_t receiver, bool collision) {
    double velocity = run.getd(receiver + 0x50);
    double zero = run.getd(0x50e000);
    if (!(velocity >= zero)) {
        double position = run.getd(receiver + 0x68);
        double target = double(run.gets(receiver + 0x280));
        if (target >= position) {
            return true;
        }
    }
    velocity = run.getd(receiver + 0x50);
    zero = run.getd(0x50e000);
    if (velocity >= zero) {
        double position = run.getd(receiver + 0x68);
        double target = double(run.gets(receiver + 0x280));
        if (!(target > position)) {
            return true;
        }
    }
    if (collision && (run.get(receiver + 0x120) & 0x10000)) {
        return true;
    }
    double previous = double(run.gets(receiver + 0x118));
    double position = run.getd(receiver + 0x68);
    return !(position < previous) && !(position > previous);
}

// 0x44b6a0. Moving attack update.
uint32_t function_44b6a0(Run &run, uint32_t receiver, const uint32_t *) {
    advance(run, receiver);
    timedSound(run, receiver, 0x400, -0x18);
    if (movementComplete(run, receiver, true)) {
        function_44b130(run, receiver, nullptr);
    }
    return 0;
}

// 0x44b780. Enter falling state.
uint32_t function_44b780(Run &run, uint32_t receiver, const uint32_t *) {
    animation(run, receiver, 0x32c);
    state(run, receiver, 0x5235f8);
    run.put(run.get(receiver + 0x0c) + 0xcc, 8);
    return 0;
}

// 0x44b7e0. Land and restore actor position.
uint32_t function_44b7e0(Run &run, uint32_t receiver, const uint32_t *) {
    advance(run, receiver);
    if (run.get(run.get(receiver + 0x0c) + 0xcc) == 1) {
        run.put(receiver + 0x50, 0);
        run.put(receiver + 0x54, 0);
        run.put(receiver + 0x58, 0);
        run.put(receiver + 0x5c, 0);
        run.put(receiver + 0x40, 0);
        run.put(receiver + 0x44, 0x409f4000);
        uint32_t actor = run.get(receiver + 0x12c);
        run.put(actor + 0x50, run.get(actor + 0x50) - 0x20);
        actor = run.get(receiver + 0x128);
        run.call(0x4cd800, run.get(run.get(actor + 0x0c) + 0x24), {actor, 0});
        run.put(run.get(receiver + 0x128) + 0xcc, 1);
        run.vcall(receiver, 0x44);
    }
    return 0;
}

// 0x44b860. Collision nudge with directional bounds.
uint32_t function_44b860(Run &run, uint32_t receiver, const uint32_t *arguments) {
    state(run, receiver, 0x527b54);
    animation(run, receiver, 0x408);
    bool left = arguments[0] == 1;
    uint32_t playerX = run.get(run.get(0x537e88) + 0x4c);
    uint32_t delta = uint32_t(s32(run.call(0x4a3050, 0)) % 21) + 20;
    uint32_t target = left ? playerX + delta : playerX - delta;
    run.put(receiver + 0x280, target);
    double coordinate = double(s32(target));
    if (left ? run.getd(receiver + 0x80) > coordinate : !(run.getd(receiver + 0x98) >= coordinate)) {
        return 0;
    }
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, left ? 0xc072c000 : 0x4072c000);
    run.put(receiver + 0x58, 0);
    run.put(receiver + 0x5c, 0);
    run.put(receiver + 0x60, 0);
    run.put(receiver + 0x64, 0);
    return 0;
}

// 0x44b960. Nudge completion.
uint32_t function_44b960(Run &run, uint32_t receiver, const uint32_t *) {
    advance(run, receiver);
    if (movementComplete(run, receiver, false)) {
        run.vcall(receiver, 0x44);
    }
    return 0;
}

// 0x44b9e0. Collision response and damage.
uint32_t function_44b9e0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t name = run.call(0x406020, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
    if (!run.call(0x4a3810, 0, {run.get(name), 0x5234f4})) {
        return 0;
    }
    uint32_t other = run.get(run.get(receiver + 0x0c) + 0x74);
    if (other == run.get(receiver + 0x430) && run.get(other + 0xd0) == 0x1000000) {
        return 0;
    }
    run.put(receiver + 0x430, other);
    bool respond = true;
    uint32_t id = run.get(run.get(receiver + 0x12c) + 0x16c);
    if (id == 800) {
        run.call(0x44ad10, receiver, {1000, 3000});
    } else if ((id != 801 && id != 802) || run.get(other + 0xd0) == 0x2000000) {
        respond = false;
        run.vcall(receiver, 0x5c, {0});
        uint32_t actor = run.get(receiver + 0x0c);
        if (run.gets(actor + 0x100) > 0) {
            run.call(0x4735b0, 0, {run.get(actor + 0x0c), run.get(actor + 0x4c), run.get(actor + 0x50), run.get(actor + 0x64), run.get(actor + 0x100)});
        }
    }
    if (respond) {
        timedSound(run, receiver, 0x404, -0x20);
        uint32_t direction = run.gets(other + 0x4c) >= run.gets(run.get(receiver + 0x0c) + 0x4c);
        function_44b860(run, receiver, &direction);
    }
    if (run.get(other + 0xd0) == 0x20) {
        run.put(other + 0x08, run.get(other + 0x08) | 0x10000);
    }
    return 0;
}

// 0x44bb40. Launch the original bomb object and advance completion.
uint32_t function_44bb40(Run &run, uint32_t receiver, const uint32_t *) {
    advance(run, receiver);
    uint32_t actor = run.get(receiver + 0x12c);
    if (run.get(actor + 0x16c) == 201 && (!run.get(actor + 0x1a4) || run.get(actor + 0x19c)) && run.get(receiver + 0x42c)) {
        sound(run, receiver, 0x3a0, -0x1c);
        actor = run.get(receiver + 0x12c);
        uint32_t world = run.get(run.get(run.get(receiver + 0x130) + 0x0c) + 0x08);
        uint32_t bomb = run.call(0x4c8da0, world, {0, run.get(actor + 0x4c), run.get(actor + 0x50), run.get(actor + 0x64) - 1, 0x522b58, 0x40000});
        run.call(run.get(run.get(bomb + 0x6c) + 0x10), 0, {bomb});
        uint32_t speed = run.get(receiver + 0x18c) == 3 ? 0xffffff6a : 150;
        run.call(0x432250, run.get(run.get(bomb + 0x6c) + 0x18), {speed});
        run.put(receiver + 0x42c, 0);
    }
    actor = run.get(receiver + 0x12c);
    if (run.get(actor + 0x1a4) && !run.get(actor + 0x19c)) {
        run.vcall(receiver, 0x44);
    }
    return 0;
}

// 0x44bc50. Original tail virtual dispatch; its result is unused.
uint32_t function_44bc50(Run &run, uint32_t receiver, const uint32_t *) {
    run.vcall(receiver, 0x18);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x44b130:
        return function_44b130(run, receiver, arguments);
    case 0x44b200:
        return function_44b200(run, receiver, arguments);
    case 0x44b2b0:
        return function_44b2b0(run, receiver, arguments);
    case 0x44b300:
        return function_44b300(run, receiver, arguments);
    case 0x44b480:
        return function_44b480(run, receiver, arguments);
    case 0x44b6a0:
        return function_44b6a0(run, receiver, arguments);
    case 0x44b780:
        return function_44b780(run, receiver, arguments);
    case 0x44b7e0:
        return function_44b7e0(run, receiver, arguments);
    case 0x44b860:
        return function_44b860(run, receiver, arguments);
    case 0x44b960:
        return function_44b960(run, receiver, arguments);
    case 0x44b9e0:
        return function_44b9e0(run, receiver, arguments);
    case 0x44bb40:
        return function_44bb40(run, receiver, arguments);
    case 0x44bc50:
        return function_44bc50(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_hermit_crab_combat_entry, owned, body)
