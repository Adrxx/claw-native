#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

// Receiver: +0x10 state holder, +0x24 previous state, +0x12c actor,
// +0x134 saved animation, +0x138/+0x140 horizontal bounds.
void selectAnimation(Run &run, uint32_t self, uint32_t name, uint32_t field) {
    run.put(self + 0x24, run.get(run.get(self + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {name});
    run.put(run.get(self + 0x10) + 0x1c, state);
    uint32_t actor = run.get(self + 0x12c);
    uint32_t animation = run.get(self + field);
    uint32_t previous = run.get(actor + 0x190);
    run.put(self + 0x134, previous);
    run.call(0x4c8220, actor + 0x188, {animation});
}

void flipBounds(Run &run, uint32_t object, uint32_t first, uint32_t last) {
    uint32_t low = run.get(object + first);
    uint32_t high = run.get(object + last);
    run.put(object + first, 0u - high);
    run.put(object + last, 0u - low);
}

void flipActorPair(Run &run, uint32_t actor, uint32_t first, uint32_t last) {
    uint32_t low = run.get(actor + first);
    if (low != 0x80000000) {
        uint32_t high = run.get(actor + last);
        run.put(actor + first, 0u - high);
        run.put(actor + last, 0u - low);
    }
}

void clearFlags(Run &run, uint32_t self) {
    // +0x50c sound-fired, +0x510 action-fired.
    run.put(self + 0x50c, 0);
    run.put(self + 0x510, 0);
}

void setDelay(Run &run, uint32_t self) {
    // +0x504 attack timestamp, +0x508 delay.
    run.put(self + 0x508, 500);
    run.put(self + 0x504, run.get(0x537210));
}

void updateAnimation(Run &run, uint32_t self) {
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {run.get(0x5430c4)});
}

bool completed(Run &run, uint32_t self) {
    uint32_t cursor = run.get(self + 0x12c) + 0x188;
    return run.get(cursor + 0x1c) != 0 && run.get(cursor + 0x14) == 0;
}

// 0x483e40: enter the pirate's Gabriel attack.
uint32_t pirateAttack(Run &run, uint32_t self) {
    selectAnimation(run, self, 0x52ba88, 0x30c);
    run.put(self + 0x80, run.get(0x513e10));
    run.put(self + 0x84, run.get(0x513e14));
    run.put(self + 0x98, run.get(0x513e18));
    run.put(self + 0x9c, run.get(0x513e1c));
    run.put(self + 0x88, run.get(0x513e10));
    run.put(self + 0x8c, run.get(0x513e14));
    run.put(self + 0xa0, run.get(0x513e18));
    run.put(self + 0xa4, run.get(0x513e1c));
    run.put(self + 0x90, run.get(0x513e10));
    run.put(self + 0x94, run.get(0x513e14));
    run.put(self + 0xa8, run.get(0x513e18));
    run.put(self + 0xac, run.get(0x513e1c));
    // +0x404 horizontal speed, +0x50 binary64 velocity.
    uint32_t velocity = (0u - run.get(self + 0x404)) << 1;
    run.putd(self + 0x50, double(s32(velocity)));
    return 0;
}

// 0x4444d0: enter multibomb attack.
uint32_t multibombStart(Run &run, uint32_t self) {
    uint32_t actor = run.get(self + 0x12c);
    if (run.get8(actor + 0x40) & 2) {
        flipBounds(run, self, 0x138, 0x140);
        run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffd);
        actor = run.get(self + 0x12c);
        flipActorPair(run, actor, 0x118, 0x120);
        run.call(0x406150, actor);
        run.call(0x406180, actor);
    }
    selectAnimation(run, self, 0x52746c, 0x490);
    clearFlags(run, self);
    uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 3);
    run.call(0x405f60, self, {run.get(self + 0x498 + index * 4)});
    setDelay(run, self);
    return 0;
}

// 0x4445d0: update multibomb attack.
uint32_t multibombUpdate(Run &run, uint32_t self) {
    if (run.get(0x537210) - run.get(self + 0x504) < run.get(self + 0x508))
        return 0;
    updateAnimation(run, self);
    if (run.get(run.get(self + 0x12c) + 0x16c) == 0x191 && run.get(self + 0x510) == 0) {
        run.put(self + 0x510, 1);
        uint32_t omitted = uint32_t(s32(run.call(0x4a3050, 0)) % 4);
        uint32_t offset = 0;
        for (uint32_t slot = 0; offset < 500; ++slot) {
            if (slot != omitted) {
                uint32_t actor = run.get(self + 0x12c);
                uint32_t layer = run.get(actor + 0x64) - 1;
                uint32_t y = run.get(actor + 0x50) - 0x4b;
                uint32_t x = run.get(actor + 0x4c) - 0x4b;
                uint32_t manager = run.get(run.get(run.get(self + 0x130) + 0xc) + 8);
                uint32_t created = run.call(0x4c8da0, manager, {0, x, y, layer, 0x522afc, 0x40000});
                uint32_t info = run.get(created + 0x6c);
                run.call(run.get(info + 0x10), 0, {created});
                info = run.get(created + 0x6c);
                run.call(0x446130, run.get(info + 0x18), {offset - 0x1db});
            }
            offset += 0x7d;
        }
    }
    if (completed(run, self))
        run.vcall(self, 0x48);
    return 0;
}

// 0x4446f0: enter thug attack unless two pirates already exist.
uint32_t thugStart(Run &run, uint32_t self) {
    if (s32(run.get(self + 0x524)) >= 2) {
        run.vcall(self, 0x48);
        return 0;
    }
    selectAnimation(run, self, 0x52745c, 0x478);
    clearFlags(run, self);
    return 0;
}

// 0x444760: update thug attack and create its pirate.
uint32_t thugUpdate(Run &run, uint32_t self) {
    updateAnimation(run, self);
    if (run.get(self + 0x50c) == 0) {
        run.put(self + 0x50c, 1);
        uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 4);
        run.call(0x405f60, self, {run.get(self + 0x4a4 + index * 4)});
    }
    if (completed(run, self) && run.get(self + 0x510) == 0) {
        run.put(self + 0x510, 1);
        uint32_t actor = run.get(self + 0x12c);
        uint32_t layer = run.get(actor + 0x64) - 1;
        uint32_t y = run.get(actor + 0x50) - 10;
        uint32_t x = run.get(actor + 0x4c) + 0x96;
        uint32_t manager = run.get(run.get(run.get(self + 0x130) + 0xc) + 8);
        uint32_t created = run.call(0x4c8da0, manager, {0, x, y, layer, 0x522c68, 0x40000});
        if (created) {
            uint32_t info = run.get(created + 0x6c);
            run.call(run.get(info + 0x10), 0, {created});
            info = run.get(created + 0x6c);
            pirateAttack(run, run.get(info + 0x18));
        }
        run.put(self + 0x524, run.get(self + 0x524) + 1);
        run.vcall(self, 0x48);
    }
    return 0;
}

// 0x444850: enter cannon attack facing the cannon.
uint32_t cannonStart(Run &run, uint32_t self) {
    selectAnimation(run, self, 0x52744c, 0x490);
    uint32_t actor = run.get(self + 0x12c);
    if (!(run.get8(actor + 0x40) & 2)) {
        flipBounds(run, self, 0x138, 0x140);
        run.put(actor + 0x40, run.get(actor + 0x40) | 2);
        actor = run.get(self + 0x12c);
        flipActorPair(run, actor, 0x118, 0x120);
        flipActorPair(run, actor, 0x128, 0x130);
        run.call(0x406180, actor);
    }
    run.put(self + 0x510, 0);
    uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 2);
    run.call(0x405f60, self, {run.get(self + 0x4b4 + index * 4)});
    setDelay(run, self);
    return 0;
}

// 0x444960: update cannon attack, publish shot flag and restore orientation.
uint32_t cannonUpdate(Run &run, uint32_t self) {
    if (run.get(0x537210) - run.get(self + 0x504) < run.get(self + 0x508))
        return 0;
    updateAnimation(run, self);
    if (run.get(run.get(self + 0x12c) + 0x16c) == 0x191 && run.get(self + 0x510) == 0) {
        run.put(self + 0x518, 1);
        run.put(self + 0x510, 1);
    }
    if (completed(run, self)) {
        uint32_t actor = run.get(self + 0x12c);
        if (run.get8(actor + 0x40) & 2) {
            flipBounds(run, self, 0x138, 0x140);
            run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffd);
            actor = run.get(self + 0x12c);
            flipActorPair(run, actor, 0x118, 0x120);
            flipActorPair(run, actor, 0x128, 0x130);
            flipActorPair(run, actor, 0x138, 0x140);
        }
        run.vcall(self, 0x48);
    }
    return 0;
}

// 0x444aa0: enter cannon hit, increment count and choose its sound.
uint32_t cannonHitStart(Run &run, uint32_t self) {
    selectAnimation(run, self, 0x52743c, 0x338);
    uint32_t hits = run.get(self + 0x514) + 1;
    run.put(self + 0x514, hits);
    if (s32(hits) < 5) {
        uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 2);
        uint32_t sound = run.get(self + 0x4c8 + index * 4);
        if (sound && run.get(0x532c0c)) {
            // 0x444aa0 pushes ESI, four arguments, and CALL's return word.
            // Preserve that physical entry for the sound callee's escaped local.
            uint32_t savedStackPointer = run.stackPointer;
            run.stackPointer = run.automatic(-24);
            run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
            run.stackPointer = savedStackPointer;
        }
        setDelay(run, self);
    }
    clearFlags(run, self);
    return 0;
}

// 0x444f80: enter death animation and mark the actor.
uint32_t deathStart(Run &run, uint32_t self) {
    selectAnimation(run, self, 0x5231f8, 0x468);
    uint32_t actor = run.get(self + 0x12c);
    if (run.get(self + 0x18c) == 2) {
        if (!(run.get8(actor + 0x40) & 2)) {
            flipBounds(run, self, 0x138, 0x140);
            run.put(actor + 0x40, run.get(actor + 0x40) | 2);
            actor = run.get(self + 0x12c);
            run.call(0x406120, actor);
            run.call(0x406150, actor);
            run.call(0x406180, actor);
        }
    } else if (run.get8(actor + 0x40) & 2) {
        flipBounds(run, self, 0x138, 0x140);
        run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffd);
        run.call(0x4060b0, run.get(self + 0x12c));
    }
    actor = run.get(self + 0x12c);
    run.put(actor + 8, run.get(actor + 8) | 0x80);
    actor = run.get(self + 0x12c);
    run.put(actor + 8, run.get(actor + 8) | 4);
    clearFlags(run, self);
    return 0;
}

// 0x444b70: update cannon-hit animation, apply damage, then attack or die.
uint32_t cannonHitUpdate(Run &run, uint32_t self) {
    if (run.get(0x537210) - run.get(self + 0x504) < run.get(self + 0x508))
        return 0;
    updateAnimation(run, self);
    if (completed(run, self) && run.get(self + 0x510) == 0) {
        uint32_t data = run.get(self + 0xc);
        run.put(self + 0x510, 1);
        run.put(data + 0x10c, run.get(data + 0x10c) - 0x14);
        if (s32(run.get(self + 0x514)) >= 5) {
            run.put(run.get(self + 0xc) + 0x10c, 0);
            deathStart(run, self);
            return 0;
        }
        multibombStart(run, self);
    }
    return 0;
}

// 0x444c20: enter blocked animation, matching the selected direction.
uint32_t blockedStart(Run &run, uint32_t self) {
    uint32_t actor = run.get(self + 0x12c);
    bool right = run.get(self + 0x18c) == 2;
    if ((right && !(run.get8(actor + 0x40) & 2)) || (!right && (run.get8(actor + 0x40) & 2))) {
        flipBounds(run, self, 0x138, 0x140);
        uint32_t flags = run.get(actor + 0x40);
        run.put(actor + 0x40, right ? flags | 2 : flags & 0xfffffffd);
        actor = run.get(self + 0x12c);
        run.call(0x406120, actor);
        run.call(0x406150, actor);
        run.call(0x406180, actor);
    }
    selectAnimation(run, self, 0x527430, 0x494);
    clearFlags(run, self);
    return 0;
}

// 0x444d00: update blocked animation.
uint32_t blockedUpdate(Run &run, uint32_t self) {
    updateAnimation(run, self);
    if (run.get(self + 0x50c) == 0) {
        run.put(self + 0x50c, 1);
        uint32_t index = uint32_t(s32(run.call(0x4a3050, 0)) % 3);
        run.call(0x405f60, self, {run.get(self + 0x4bc + index * 4)});
    }
    if (completed(run, self) && run.get(self + 0x510) == 0) {
        uint32_t method = run.get(run.get(self) + 0x48);
        run.put(self + 0x510, 1);
        run.call(method, self);
    }
    return 0;
}

// 0x444d90: inspect incoming damage and current state.
uint32_t receiveHit(Run &run, uint32_t self) {
    if (run.get(self + 0x520))
        return 0;
    uint32_t incoming = run.get(run.get(self + 0xc) + 0x74);
    if (!incoming)
        return 0;
    if (run.get(incoming + 0xd0) != 0x40) {
        uint32_t identity = run.get(run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14) + 0xe8);
        if (identity == run.get(self + 0x19c))
            return 0;
        run.put(self + 0x19c, identity);
        const uint32_t names[] = {0x527430, 0x52743c, 0x5231f8, 0x527424, 0x527418, 0x52740c};
        for (uint32_t name : names) {
            uint32_t slot = run.call(0x406020, 0x537698, {run.get(run.get(self + 0x10) + 0x1c)});
            uint32_t equal = run.call(0x4a3810, 0, {run.get(slot), name});
            if (equal == 0)
                return 0;
        }
        if (run.get(0x537210) - run.get(self + 0x4f4) < run.get(self + 0x4f8))
            return 0;
        if (run.get(incoming + 0xd0) != 0x40) {
            run.put(self + 0x4f8, 500);
            run.put(self + 0x4f4, run.get(0x537210));
            blockedStart(run, self);
            uint32_t kind = run.get(incoming + 0xd0);
            if (kind == 0x20 || kind == 0x2000000)
                run.put(incoming + 8, run.get(incoming + 8) | 0x10000);
            return 0;
        }
    }
    run.put(self + 0x4f8, 1000);
    run.put(self + 0x4f4, run.get(0x537210));
    // 0x444d90 has pushed ESI and EDI before CALL 0x444aa0 at 0x444f30.
    uint32_t savedFrame = run.frame;
    run.frame = run.automatic(-12);
    cannonHitStart(run, self);
    run.frame = savedFrame;
    run.call(0x440e20, self, {incoming});
    run.put(incoming + 8, run.get(incoming + 8) | 0x10000);
    uint32_t kind = run.get(incoming + 0xd0);
    if (kind == 0x20 || kind == 0x2000000)
        run.put(incoming + 8, run.get(incoming + 8) | 0x10000);
    return 0;
}

int owned(uint32_t function) {
    switch (function) {
    case 0x483e40:
    case 0x4444d0:
    case 0x4445d0:
    case 0x4446f0:
    case 0x444760:
    case 0x444850:
    case 0x444960:
    case 0x444aa0:
    case 0x444b70:
    case 0x444c20:
    case 0x444d00:
    case 0x444d90:
    case 0x444f80:
        return 0;
    default:
        return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *) {
    switch (function) {
    case 0x483e40:
        return pirateAttack(run, receiver);
    case 0x4444d0:
        return multibombStart(run, receiver);
    case 0x4445d0:
        return multibombUpdate(run, receiver);
    case 0x4446f0:
        return thugStart(run, receiver);
    case 0x444760:
        return thugUpdate(run, receiver);
    case 0x444850:
        return cannonStart(run, receiver);
    case 0x444960:
        return cannonUpdate(run, receiver);
    case 0x444aa0:
        return cannonHitStart(run, receiver);
    case 0x444b70:
        return cannonHitUpdate(run, receiver);
    case 0x444c20:
        return blockedStart(run, receiver);
    case 0x444d00:
        return blockedUpdate(run, receiver);
    case 0x444d90:
        return receiveHit(run, receiver);
    case 0x444f80:
        return deathStart(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_level_eight_gabriel_attacks_pirate_01_entry, owned, body)
