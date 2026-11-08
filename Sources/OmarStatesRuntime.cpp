// Omar state transitions, translated from the original v1.0 instruction packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4645c0:
        return 0;
    case 0x4646e0:
        return 1;
    case 0x4646f0:
        return 0;
    case 0x464770:
        return 0;
    case 0x4648e0:
        return 0;
    case 0x464930:
        return 0;
    case 0x464a60:
        return 1;
    case 0x464b90:
        return 0;
    case 0x464c00:
        return 0;
    case 0x464c30:
        return 0;
    case 0x464cc0:
        return 0;
    case 0x464eb0:
        return 1;
    case 0x464ec0:
        return 1;
    case 0x464ed0:
        return 0;
    default:
        return -1;
    }
}

void flipBounds(Run &run, uint32_t object, uint32_t offset) {
    const uint32_t old = run.get(object + offset);
    run.put(object + offset, 0u - run.get(object + offset + 0x8));
    run.put(object + offset + 0x8, 0u - old);
}

void flipSprite(Run &run, uint32_t sprite) {
    if (run.get(sprite + 0x118) != 0x80000000u) {
        flipBounds(run, sprite, 0x118);
    }
    if (run.get(sprite + 0x128) != 0x80000000u) {
        flipBounds(run, sprite, 0x128);
    }
    if (run.get(sprite + 0x138) != 0x80000000u) {
        flipBounds(run, sprite, 0x138);
    }
}

void selectState(Run &run, uint32_t receiver, uint32_t name) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    const uint32_t state = run.call(0x4dba00, 0x537668, {name});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
}

// 0x464eb0. Set the saved horizontal coordinate.
uint32_t function_464eb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.putd(receiver + 0x68, double(s32(arguments[0])));
    return 0;
}

// 0x464ec0. Set the saved vertical coordinate.
uint32_t function_464ec0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.putd(receiver + 0x70, double(s32(arguments[0])));
    return 0;
}

// 0x464ed0. Play a random near-player vocalization.
uint32_t function_464ed0(Run &run, uint32_t receiver, const uint32_t *) {
    const uint32_t distance = run.get(receiver + 0x3c4);
    if (s32(distance) >= 0 && s32(distance) < 10) {
        const uint32_t random = run.call(0x4a3050, 0);
        const uint32_t sprite = run.get(receiver + 0x12c);
        const uint32_t voice = run.get(receiver + 0x464 + uint32_t(s32(random) % 5) * 4);
        if (run.get(sprite + 0x38) != 0xffffffffu) {
            run.call(0x48ce40, 0, {run.get(receiver + 0xc), voice, 0});
        }
    }
    return 0;
}

// 0x4645c0. Face the target and restore the saved position when the timer expires.
uint32_t function_4645c0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t sprite = run.get(receiver + 0x12c);
    if (run.get(receiver + 0x18c) == 2) {
        if (!(run.get8(sprite + 0x40) & 2)) {
            flipBounds(run, receiver, 0x138);
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
            sprite = run.get(receiver + 0x12c);
            run.call(0x406120, sprite);
            run.call(0x406150, sprite);
            run.call(0x406180, sprite);
        }
    } else if (run.get8(sprite + 0x40) & 2) {
        flipBounds(run, receiver, 0x138);
        run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffffdu);
        run.call(0x4060b0, run.get(receiver + 0x12c));
    }
    if (run.get(0x537210) - run.get(receiver + 0xd30) >= run.get(receiver + 0xd34)) {
        sprite = run.get(receiver + 0x12c);
        run.put(sprite + 0x8, run.get(sprite + 0x8) & 0xfffffffbu);
        sprite = run.get(receiver + 0x12c);
        run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffff7u);
        const uint32_t x = run.get(receiver + 0xd38);
        function_464eb0(run, receiver, &x);
        const uint32_t y = run.get(receiver + 0xd3c);
        function_464ec0(run, receiver, &y);
        run.vcall(receiver, 0x44);
    }
    return 0;
}

// 0x4646e0. Mark an object for removal.
uint32_t function_4646e0(Run &run, uint32_t, const uint32_t *arguments) {
    run.put(arguments[0] + 0x8, run.get(arguments[0] + 0x8) | 0x10000);
    return 0;
}

// 0x4646f0. Enter idle.
uint32_t function_4646f0(Run &run, uint32_t receiver, const uint32_t *) {
    selectState(run, receiver, 0x523148);
    const uint32_t sprite = run.get(receiver + 0x12c);
    const uint32_t animation = run.get(receiver + 0x350);
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    const uint32_t sound = run.get(receiver + 0x478);
    if (sound) {
        const uint32_t player = run.get(0x5371fc);
        const uint32_t enabled = run.get(0x532c0c);
        const uint32_t playerSprite = run.get(player + 0x12c);
        if (enabled) {
            run.call(0x4b3dc0, run.get(sound + 0x10), {playerSprite, 0, 0, 1});
        }
    }
    return 0;
}

// 0x464770. Advance idle and synchronize facing rectangles.
uint32_t function_464770(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    function_464ed0(run, receiver, nullptr);
    const uint32_t sprite = run.get(receiver + 0x12c);
    if (run.get(receiver + 0x18c) == 2) {
        if (run.get8(sprite + 0x40) & 2) {
            return 0;
        }
        flipBounds(run, receiver, 0x138);
        run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
    } else {
        if (!(run.get8(sprite + 0x40) & 2)) {
            return 0;
        }
        flipBounds(run, receiver, 0x138);
        run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffffdu);
    }
    flipSprite(run, run.get(receiver + 0x12c));
    return 0;
}

// 0x4648e0. Enter home.
uint32_t function_4648e0(Run &run, uint32_t receiver, const uint32_t *) {
    selectState(run, receiver, 0x5234ec);
    const uint32_t sprite = run.get(receiver + 0x12c);
    const uint32_t animation = run.get(receiver + 0x350);
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    run.put(receiver + 0x50, 0);
    run.put(receiver + 0x54, 0);
    return 0;
}

// 0x464c30. Enter magic attack.
uint32_t function_464c30(Run &run, uint32_t receiver, const uint32_t *) {
    selectState(run, receiver, 0x529a38);
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c79e0, sprite, {0x529a58, 0});
    sprite = run.get(receiver + 0x12c);
    if (run.get8(sprite + 0x40) & 2) {
        run.put(receiver + 0xd24, 0x41);
        run.put(receiver + 0xd2c, 0x12c);
    } else {
        run.put(receiver + 0xd24, 0xffffffbf);
        run.put(receiver + 0xd2c, 0xfffffed4);
    }
    run.put(receiver + 0xd28, 0xffffffec);
    run.put(receiver + 0x1a0, 0);
    return 0;
}

// 0x464930. Advance home, orient and start an attack in range.
uint32_t function_464930(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    function_464ed0(run, receiver, nullptr);
    uint32_t sprite = run.get(receiver + 0x12c);
    if (run.get(receiver + 0x18c) == 2) {
        if (!(run.get8(sprite + 0x40) & 2)) {
            flipBounds(run, receiver, 0x138);
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2);
            sprite = run.get(receiver + 0x12c);
            if (run.get(sprite + 0x118) != 0x80000000u) {
                flipBounds(run, sprite, 0x118);
            }
            if (run.get(sprite + 0x128) != 0x80000000u) {
                flipBounds(run, sprite, 0x128);
            }
            run.call(0x406180, sprite);
        }
    } else if (run.get8(sprite + 0x40) & 2) {
        flipBounds(run, receiver, 0x138);
        run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffffdu);
        sprite = run.get(receiver + 0x12c);
        run.call(0x406120, sprite);
        run.call(0x406150, sprite);
        run.call(0x406180, sprite);
    }
    if (run.get(receiver + 0xd1c) == 0) {
        const uint32_t facingRange = run.get(receiver + 0x184);
        if (s32(facingRange) >= 0 && s32(facingRange) <= 6) {
            const uint32_t distance = run.get(receiver + 0x3c4);
            if (s32(distance) >= 0 && s32(distance) < 0x32) {
                function_464c30(run, receiver, nullptr);
            }
        }
    }
    return 0;
}

// 0x464a60. Reset a remaining phase or enter the death animation.
uint32_t function_464a60(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(receiver + 0xd1c)) {
        for (uint32_t i = 0; i < 9; ++i) {
            const uint32_t slot = receiver + 0x484 + i * 4;
            const uint32_t object = run.get(slot);
            run.put(object + 0x8, run.get(object + 0x8) | 0x10000);
            run.put(slot, 0);
        }
        run.call(0x464500, receiver, {0xa550, 0x42b});
        const uint32_t remaining = run.get(receiver + 0xd1c) - 1;
        const uint32_t player = run.get(receiver + 0xc);
        run.put(receiver + 0xd20, 1);
        run.put(receiver + 0xd1c, remaining);
        run.put(player + 0x10c, 0x64);
        const uint32_t refreshedPlayer = run.get(receiver + 0xc);
        const double operand = double(run.gets(refreshedPlayer + 0x10c)) * double(run.getf(0x5262b4));
        const uint32_t health = run.call_x87(0x4a30e0, 0, operand);
        run.put(refreshedPlayer + 0x10c, health);
        const uint32_t sound = run.get(receiver + 0x478);
        if (sound) {
            run.call(0x4b3e30, run.get(sound + 0x10));
        }
    } else {
        selectState(run, receiver, 0x5234f4);
        uint32_t sprite = run.get(receiver + 0x12c);
        run.put(sprite + 0x40, run.get(sprite + 0x40) & 0xfffffff7u);
        sprite = run.get(receiver + 0x12c);
        run.put(sprite + 0x8, run.get(sprite + 0x8) | 1);
        sprite = run.get(receiver + 0x12c);
        const uint32_t animation = run.get(receiver + 0x460);
        run.put(receiver + 0x134, run.get(sprite + 0x190));
        run.call(0x4c8220, sprite + 0x188, {animation});
        sprite = run.get(receiver + 0x12c);
        const uint32_t voice = run.get(receiver + 0x3a4);
        if (run.get(sprite + 0x38) != 0xffffffffu) {
            run.call(0x48ce40, 0, {run.get(receiver + 0xc), voice, 1});
        }
    }
    return 0;
}

// 0x464c00. Enter wait.
uint32_t function_464c00(Run &run, uint32_t receiver, const uint32_t *) {
    selectState(run, receiver, 0x529a48);
    return 0;
}

// 0x464b90. Complete the death sequence once.
uint32_t function_464b90(Run &run, uint32_t receiver, const uint32_t *) {
    run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    const uint32_t animation = run.get(receiver + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) && run.get(animation + 0x14) == 0 && run.get(receiver + 0xd40) == 0) {
        run.put(receiver + 0xd40, 1);
        const uint32_t player = run.get(0x537e88);
        if (run.gets(player + 0x10c) > 0) {
            run.call(0x420590, 0);
            run.call(0x40e5c0, receiver);
            function_464c00(run, receiver, nullptr);
        }
    }
    return 0;
}

// 0x464cc0. Publish the magic projectile and finish the attack animation.
uint32_t function_464cc0(Run &run, uint32_t receiver, const uint32_t *) {
    const uint32_t movement = receiver + 0x128;
    if (run.get(receiver + 0x18c) == 2) {
        run.call(0x4357a0, movement);
    } else {
        run.call(0x406310, movement);
    }
    const uint32_t advanced = run.call(0x4c82a0, run.get(receiver + 0x12c) + 0x188, {run.get(0x5430c4)});
    if (advanced == 1 && run.get(receiver + 0x1a0) == 0) {
        const uint32_t sound = run.get(receiver + 0x474);
        if (sound) {
            run.call(0x4208e0, sound, {run.get(0x532c10), 0, 0, 0});
        }
        const uint32_t count = run.get(receiver + 0x1a0) + 1;
        uint32_t y = run.get(receiver + 0xd28);
        run.put(receiver + 0x1a0, count);
        const uint32_t sprite = run.get(movement + 0x4);
        const uint32_t depth = run.get(sprite + 0x64) - 1;
        y += run.get(sprite + 0x50);
        const uint32_t x = run.get(receiver + 0xd24) + run.get(sprite + 0x4c);
        const uint32_t world = run.get(run.get(run.get(movement + 0x8) + 0xc) + 0x8);
        const uint32_t projectile = run.call(0x4c8da0, world, {0, x, y, depth, 0x522d9c, 0x40000});
        if (run.get(projectile + 0x64) != 0x1388) {
            run.put(projectile + 0x64, 0x1388);
            run.put(projectile + 0x8, run.get(projectile + 0x8) | 0x20000);
        }
        const uint32_t logic = run.get(projectile + 0x6c);
        run.put(projectile + 0x104, 0xf);
        run.put(projectile + 0xd0, 0x40);
        run.call(run.get(logic + 0x10), 0, {projectile});
        uint32_t projectileLogic = run.get(projectile + 0x6c);
        const uint32_t velocity = run.get(receiver + 0xd2c);
        uint32_t projectileState = run.get(projectileLogic + 0x18);
        run.putd(projectileState + 0x50, double(s32(velocity)));
        projectileLogic = run.get(projectile + 0x6c);
        projectileState = run.get(projectileLogic + 0x18);
        run.put(projectileState + 0x58, 0);
        run.put(projectileState + 0x5c, 0);
        projectileLogic = run.get(projectile + 0x6c);
        projectileState = run.get(projectileLogic + 0x18);
        run.put(projectileState + 0x40, 0);
        run.put(projectileState + 0x44, 0);
        if (run.gets(receiver + 0xd2c) < 0) {
            projectileState = run.get(run.get(projectile + 0x6c) + 0x18);
            const uint32_t projectileSprite = run.get(projectileState + 0x12c);
            if (!(run.get8(projectileSprite + 0x40) & 2)) {
                flipBounds(run, projectileState, 0x138);
                run.put(projectileSprite + 0x40, run.get(projectileSprite + 0x40) | 2);
                flipSprite(run, run.get(projectileState + 0x12c));
            }
        }
    }
    const uint32_t animation = run.get(receiver + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) && run.get(animation + 0x14) == 0) {
        run.vcall(receiver, 0x44);
    }
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4645c0:
        return function_4645c0(run, receiver, arguments);
    case 0x4646e0:
        return function_4646e0(run, receiver, arguments);
    case 0x4646f0:
        return function_4646f0(run, receiver, arguments);
    case 0x464770:
        return function_464770(run, receiver, arguments);
    case 0x4648e0:
        return function_4648e0(run, receiver, arguments);
    case 0x464930:
        return function_464930(run, receiver, arguments);
    case 0x464a60:
        return function_464a60(run, receiver, arguments);
    case 0x464b90:
        return function_464b90(run, receiver, arguments);
    case 0x464c00:
        return function_464c00(run, receiver, arguments);
    case 0x464c30:
        return function_464c30(run, receiver, arguments);
    case 0x464cc0:
        return function_464cc0(run, receiver, arguments);
    case 0x464eb0:
        return function_464eb0(run, receiver, arguments);
    case 0x464ec0:
        return function_464ec0(run, receiver, arguments);
    case 0x464ed0:
        return function_464ed0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_omar_states_entry, owned, body)
