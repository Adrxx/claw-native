// Level 13 Red Tail attacks, recovered from the original v1.0 instruction bodies.
#include "ClawRuntime.hpp"
#include <cmath>

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x480860:
    case 0x480aa0:
    case 0x480c40:
    case 0x480e50:
    case 0x480f20:
    case 0x480fd0:
    case 0x481180:
    case 0x481270:
    case 0x481400:
    case 0x4815b0:
    case 0x481720:
    case 0x481790:
    case 0x4817c0:
        return 0;
    case 0x4817e0:
    case 0x481810:
        return 1;
    default:
        return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

// +0x138/+0x140 are horizontal bounds; sprite +0x118, +0x128,
// +0x138 are optional bounds with INT_MIN denoting an absent rectangle.
void flipPair(Run &run, uint32_t object, uint32_t offset, bool optional = false, bool reverseStores = false) {
    const uint32_t first = run.get(object + offset);
    if (optional && first == 0x80000000u)
        return;
    const uint32_t second = run.get(object + offset + 0x8);
    if (reverseStores) {
        run.put(object + offset + 0x8, 0u - first);
        run.put(object + offset, 0u - second);
    } else {
        run.put(object + offset, 0u - second);
        run.put(object + offset + 0x8, 0u - first);
    }
}

// +0x12c is the sprite, whose +0x40 bit 1 indicates horizontal reflection.
void fullFacing(Run &run, uint32_t object, bool reflected, bool reverseLast = false, bool lastOriginal = false) {
    uint32_t sprite = run.get(object + 0x12c);
    if (bool(run.get8(sprite + 0x40) & 2) == reflected)
        return;
    flipPair(run, object, 0x138);
    run.put(sprite + 0x40, reflected ? run.get(sprite + 0x40) | 2u : run.get(sprite + 0x40) & ~2u);
    sprite = run.get(object + 0x12c);
    flipPair(run, sprite, 0x118, true);
    flipPair(run, sprite, 0x128, true);
    if (lastOriginal)
        run.call(0x406180, sprite);
    else
        flipPair(run, sprite, 0x138, true, reverseLast);
}

// +0x18c is facing direction; the original helper refreshes sprite bounds.
void attackFacing(Run &run, uint32_t object) {
    if (run.get(object + 0x18c) == 2) {
        const uint32_t sprite = run.get(object + 0x12c);
        if (!(run.get8(sprite + 0x40) & 2)) {
            flipPair(run, object, 0x138);
            run.put(sprite + 0x40, run.get(sprite + 0x40) | 2u);
            run.call(0x4060b0, run.get(object + 0x12c));
        }
    } else {
        run.call(0x406310, object + 0x128);
    }
}

void animation(Run &run, uint32_t object, uint32_t name) {
    // +0x10 state controller, +0x24 saved state controller value.
    run.put(object + 0x24, run.get(run.get(object + 0x10) + 0x1c));
    const uint32_t value = run.call(0x4dba00, 0x537668, {name});
    run.put(run.get(object + 0x10) + 0x1c, value);
}

void sequence(Run &run, uint32_t object, uint32_t offset) {
    const uint32_t sprite = run.get(object + 0x12c);
    const uint32_t selected = run.get(object + offset);
    // +0x134 saves the previous sprite sequence.
    run.put(object + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {selected});
}

void delay(Run &run, uint32_t object) {
    const uint32_t value = uint32_t(s32(run.call(0x4a3050, 0)) % 501) + 1000;
    // +0x4b4 delay, +0x4b0 timestamp.
    run.put(object + 0x4b4, value);
    run.put(object + 0x4b0, run.get(0x537210));
}

void randomVoice(Run &run, uint32_t object) {
    if (s32(run.call(0x4a3050, 0)) % 101 < 25) {
        const uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 4);
        const uint32_t sound = run.get(object + 0x484 + index * 4);
        run.call(0x48ce40, 0, {run.get(object + 0xc), sound, 0});
    }
}

void sound(Run &run, uint32_t object, uint32_t offset) {
    const uint32_t handle = run.get(object + offset);
    if (handle && run.get(0x532c0c))
        run.call(0x4b45f0, run.get(handle + 0x10), {run.get(0x532c10), 0, 0, 0});
}

void copyBounds(Run &run, uint32_t object, uint32_t from) {
    run.put(object + 0x220, run.get(object + from));
    run.put(object + 0x224, run.get(object + from + 0x4));
    run.put(object + 0x228, run.get(object + from + 0x8));
    run.put(object + 0x22c, run.get(object + from + 0xc));
}

void advance(Run &run, uint32_t object) {
    run.call(0x4c82a0, run.get(object + 0x12c) + 0x188, {run.get(0x5430c4)});
}

bool finished(Run &run, uint32_t object) {
    const uint32_t sprite = run.get(object + 0x12c);
    return run.get(sprite + 0x1a4) && !run.get(sprite + 0x19c);
}

void attackBounds(Run &run, uint32_t object, uint32_t frame) {
    if (run.get(run.get(object + 0x12c) + 0x16c) != frame)
        return;
    const uint32_t target = run.get(object + 0xc) + 0x138;
    run.put(target, run.get(object + 0x220));
    run.put(target + 0x4, run.get(object + 0x224));
    run.put(target + 0x8, run.get(object + 0x228));
    run.put(target + 0xc, run.get(object + 0x22c));
    if (run.get8(run.get(object + 0x12c) + 0x40) & 2) {
        const uint32_t entity = run.get(object + 0xc);
        const uint32_t first = run.get(entity + 0x138);
        run.put(entity + 0x138, 0u - run.get(entity + 0x140));
        run.put(run.get(object + 0xc) + 0x140, 0u - first);
    }
}

// Projectile creation shared by the knife and gun update instruction bodies.
void projectile(Run &run, uint32_t object, uint32_t name, uint32_t damage, uint32_t dx, uint32_t dy, bool bullet) {
    const uint32_t sprite = run.get(object + 0x12c);
    const uint32_t created = run.call(0x4c8da0, run.get(run.get(run.get(object + 0x130) + 0xc) + 0x8),
        {0, run.get(sprite + 0x4c) + run.get(object + 0x4f4), run.get(sprite + 0x50) + run.get(object + 0x4f8), run.get(sprite + 0x64) - 1, name, 0x40000});
    const uint32_t method = run.get(run.get(created + 0x6c) + 0x10);
    run.put(created + 0x104, damage);
    run.call(method, 0, {created});
    run.putd(run.get(run.get(created + 0x6c) + 0x18) + 0x50, double(s32(run.get(object + 0x4fc) + dx)));
    run.putd(run.get(run.get(created + 0x6c) + 0x18) + 0x58, double(s32(run.get(object + 0x500) + dy)));
    const uint32_t logic = run.get(run.get(created + 0x6c) + 0x18);
    run.put(logic + 0x40, 0);
    run.put(logic + 0x44, 0);
    if (run.gets(object + 0x4fc) < 0)
        fullFacing(run, run.get(run.get(created + 0x6c) + 0x18), true, false, bullet);
}

// 0x480860. Select an attack after the unsigned cooldown expires.
uint32_t selectAttack(Run &run, uint32_t object) {
    if (run.get(0x537210) - run.get(object + 0x4b0) < run.get(object + 0x4b4)) {
        run.vcall(object, 0x44);
        return 0;
    }
    const int32_t choice = s32(run.call(0x4a3050, 0)) % 101;
    fullFacing(run, object, run.get(object + 0x18c) == 2);
    switch (run.get(object + 0x184)) {
    case 0:
    case 1:
        if (choice < 40)
            return body(run, 0x480aa0, object, nullptr);
        if (choice < 80)
            return body(run, 0x481270, object, nullptr);
        if (choice < 90)
            return body(run, 0x480fd0, object, nullptr);
        break;
    case 2:
    case 3:
        if (choice < 20)
            return body(run, 0x480aa0, object, nullptr);
        if (choice < 40)
            return body(run, 0x481270, object, nullptr);
        if (choice < 80)
            return body(run, 0x480fd0, object, nullptr);
        break;
    case 4:
        if (choice < 70)
            return body(run, 0x480e50, object, nullptr);
        break;
    default:
        run.vcall(object, 0x44);
        return 0;
    }
    return body(run, 0x4815b0, object, nullptr);
}

uint32_t body(Run &run, uint32_t function, uint32_t object, const uint32_t *arguments) {
    switch (function) {
    case 0x480860:
        return selectAttack(run, object);
    // 0x480aa0. Knife attack setup.
    case 0x480aa0: {
        attackFacing(run, object);
        if (run.call(0x482510, object) && run.get(object + 0x184) == 4)
            return body(run, 0x480e50, object, nullptr);
        if (run.call(0x482510, object))
            return body(run, 0x481270, object, nullptr);
        const uint32_t facing = run.call(0x4824f0, 0);
        run.put(object + 0x4f4, 35);
        run.put(object + 0x4f8, 4);
        const uint32_t selected = run.get(object + (facing ? 0x464 : 0x468));
        run.put(object + 0x500, facing ? 300u : uint32_t(-300));
        const uint32_t sprite = run.get(object + 0x12c);
        run.put(object + 0x134, run.get(sprite + 0x190));
        run.call(0x4c8220, sprite + 0x188, {selected});
        animation(run, object, 0x52b3a4);
        delay(run, object);
        run.put(object + 0x4ec, 0);
        if (run.get8(run.get(object + 0x12c) + 0x40) & 2) {
            run.put(object + 0x4fc, 250);
        } else {
            run.put(object + 0x4fc, uint32_t(-250));
            run.put(object + 0x4f4, 0u - run.get(object + 0x4f4));
        }
        randomVoice(run, object);
        return 0;
    }
    // 0x480c40. Three-knife fan emitted on sequence completion.
    case 0x480c40: {
        advance(run, object);
        if (finished(run, object)) {
            uint32_t dx = 0;
            uint32_t dy = 0;
            run.put(object + 0x4ec, run.get(object + 0x4ec) + 1);
            for (uint32_t index = 0; index < 3; ++index) {
                projectile(run, object, 0x522d70, 10, dx, dy, false);
                if (index == 0) {
                    sound(run, object, 0x4ac);
                    dx -= 150;
                } else if (index == 1) {
                    dy -= 150;
                }
            }
            run.vcall(object, 0x44);
        }
        return 0;
    }
    // 0x480e50. Kick setup, otherwise route to movement peers.
    case 0x480e50:
        if (!run.call(0x482510, object)) {
            const uint32_t near = run.call(0x4824c0, object);
            run.call(near ? 0x481880 : 0x481c90, object, {5});
        } else if (run.get(object + 0x184) != 4) {
            run.call(0x482550, object, {5});
        } else {
            animation(run, object, 0x52b394);
            sequence(run, object, 0x478);
            delay(run, object);
            copyBounds(run, object, 0x4d0);
        }
        return 0;
    // 0x480f20. Kick frame hitbox and completion.
    case 0x480f20:
        advance(run, object);
        attackBounds(run, object, 0x192);
        if (finished(run, object))
            run.vcall(object, 0x44);
        return 0;
    // 0x480fd0. Slide setup.
    case 0x480fd0:
        if (!run.call(0x4824f0, 0))
            return selectAttack(run, object);
        if (!run.call(0x4824c0, object)) {
            run.call(0x481c90, object, {4});
            return 0;
        }
        if (run.get(object + 0x184) != 4) {
            run.call(0x482550, object, {4});
            return 0;
        }
        run.call(run.get(object + 0x18c) == 2 ? 0x4357a0 : 0x406310, object + 0x128);
        animation(run, object, 0x52b384);
        sequence(run, object, 0x474);
        delay(run, object);
        run.putd(object + 0x50, run.get(object + 0x18c) == 3 ? -280.0 : 280.0);
        run.put(object + 0x4f0, run.get(run.get(0x537e88) + 0x4c) + (run.get(object + 0x18c) == 3 ? uint32_t(-150) : 150u));
        randomVoice(run, object);
        sound(run, object, 0x4a8);
        copyBounds(run, object, 0x4c0);
        return 0;
    // 0x481180. Slide hitbox and position/boundary stop checks.
    case 0x481180: {
        advance(run, object);
        attackBounds(run, object, 0x12e);
        const int32_t position = s32(run.call_x87(0x4a30e0, 0, run.getd(object + 0x68)));
        const uint32_t direction = run.get(object + 0x18c);
        if ((direction == 3 && position <= run.gets(object + 0x4f0)) ||
            (direction == 2 && position >= run.gets(object + 0x4f0))) {
            run.vcall(object, 0x44);
        } else {
            // FCOMP's C3 bit is set for equality and unordered operands.
            const double position1 = run.getd(object + 0x68);
            const double bound1 = run.getd(object + 0x80);
            if ((position1 == bound1 || std::isnan(position1) || std::isnan(bound1)) && direction == 3) {
                run.vcall(object, 0x44);
            } else {
                const double position2 = run.getd(object + 0x68);
                const double bound2 = run.getd(object + 0x98);
                if ((position2 == bound2 || std::isnan(position2) || std::isnan(bound2)) && direction == 2)
                    run.vcall(object, 0x44);
            }
        }
        return 0;
    }
    // 0x481270. Gun setup.
    case 0x481270:
        if (run.call(0x4824f0, 0) && !run.call(0x4824c0, object)) {
            run.call(0x481c90, object, {2});
            return 0;
        }
        if (!run.call(0x4824f0, 0) && run.call(0x4824c0, object)) {
            run.call(0x481880, object, {2});
            return 0;
        }
        delay(run, object);
        animation(run, object, 0x52b374);
        sequence(run, object, 0x46c);
        run.put(object + 0x50, 0);
        run.put(object + 0x54, 0);
        attackFacing(run, object);
        randomVoice(run, object);
        run.put(object + 0x4ec, 0);
        run.put(object + 0x4f8, uint32_t(-9));
        run.put(object + 0x500, 0);
        if (run.get8(run.get(object + 0x12c) + 0x40) & 2) {
            run.put(object + 0x4f4, 66);
            run.put(object + 0x4fc, 500);
        } else {
            run.put(object + 0x4f4, uint32_t(-66));
            run.put(object + 0x4fc, uint32_t(-500));
        }
        return 0;
    // 0x481400. Gun emission and completion.
    case 0x481400:
        advance(run, object);
        if (run.get(run.get(object + 0x12c) + 0x16c) == 0xd1 && !run.get(object + 0x4ec)) {
            run.put(object + 0x4ec, 1);
            projectile(run, object, 0x522d60, 15, 0, 0, true);
            sound(run, object, 0x480);
        }
        if (finished(run, object))
            run.vcall(object, 0x44);
        return 0;
    // 0x4815b0. Wind attack setup.
    case 0x4815b0: {
        if (!run.call(0x4824f0, 0) || run.get(object + 0x4e4))
            return selectAttack(run, object);
        if (run.call(0x4824c0, object)) {
            run.call(0x481880, object, {1});
            return 0;
        }
        run.put(object + 0x4e4, 1);
        animation(run, object, 0x52b364);
        sequence(run, object, 0x470);
        const uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 2);
        run.call(0x48ce40, 0, {run.get(object + 0xc), run.get(object + 0x494 + index * 4), 0});
        fullFacing(run, object, true, true);
        return 0;
    }
    // 0x481720. Wind completion cooldown.
    case 0x481720:
        advance(run, object);
        if (finished(run, object)) {
            run.vcall(object, 0x44);
            const uint32_t value = uint32_t(s32(run.call(0x4a3050, 0)) % 501) + 2000;
            run.put(object + 0x4bc, value);
            run.put(object + 0x4b8, run.get(0x537210));
        }
        return 0;
    // 0x481790. Reset and select movement peer.
    case 0x481790: {
        run.call(0x481fe0, object);
        const uint32_t facing = run.call(0x4824f0, 0);
        run.call(facing ? 0x481880 : 0x481c90, object, {0});
        return 0;
    }
    // 0x4817c0. Reset and invoke original death peer.
    case 0x4817c0:
        run.call(0x481fe0, object);
        run.call(0x44e620, object);
        return 0;
    // 0x4817e0. Route the requested attack through a movement peer.
    case 0x4817e0: {
        const uint32_t near = run.call(0x4824c0, object);
        run.call(near ? 0x481880 : 0x481c90, object, {arguments[0]});
        return 0;
    }
    // 0x481810. Dispatch attack IDs to owned implementations.
    case 0x481810:
        switch (arguments[0]) {
        case 1:
            return body(run, 0x4815b0, object, nullptr);
        case 2:
            return body(run, 0x481270, object, nullptr);
        case 3:
            return body(run, 0x480aa0, object, nullptr);
        case 4:
            return body(run, 0x480fd0, object, nullptr);
        case 5:
            return body(run, 0x480e50, object, nullptr);
        case 6:
            return run.vcall(object, 0x5c, {0});
        default:
            return run.vcall(object, 0x44);
        }
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_thirteen_red_tail_attacks_01_entry, owned, body)
