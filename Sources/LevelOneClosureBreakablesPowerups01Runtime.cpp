// Level 1 closure: breakables, bouncing goodie, Magic and Super powerups
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x46f5b0:
        return 1;
    case 0x46f5d0:
        return 0;
    case 0x46fbe0:
        return 0;
    case 0x46fc60:
        return 0;
    case 0x46fc90:
        return 1;
    case 0x404f30:
        return 1;
    case 0x404f50:
        return 0;
    case 0x40f390:
        return 0;
    case 0x470f00:
        return 1;
    case 0x471330:
        return 1;
    default:
        return -1;
    }
}

// Destructor body shared by 0x46f5d0 and 0x404f50 (different exception tables only).
void destroyBody(Run &run, uint32_t self) {
    // +0x00 vtable, +0x2f4 member, +0x1a8 and +0x1a4 members.
    run.put(self + 0x0, 0x50b16c);
    run.call(0x4dbcd0, self + 0x2f4);
    run.call(0x4f6584, self + 0x1a8);
    run.call(0x4f6584, self + 0x1a4);
    run.put(self + 0x0, 0x50b014);
}

// 0x46f5d0. Destructor.
uint32_t function_46f5d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    destroyBody(run, receiver);
    return 0;
}

// 0x46f5b0. Scalar deleting destructor.
uint32_t function_46f5b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_46f5d0(run, receiver, arguments);
    if ((arguments[0] & 1) != 0) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x46fbe0. Switches the logic's sound to LS_DROPPED.
uint32_t function_46fbe0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    // +0x10 sound owner (+0x1c current sound), +0x24 saved sound, +0xc owner object.
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t sound = run.call(0x4dba00, 0x537668, {0x5271b4});
    run.put(run.get(receiver + 0x10) + 0x1c, sound);
    run.put(run.get(receiver + 0xc) + 0xcc, 8);
    run.put(receiver + 0xc8, 0);
    return 0;
}

// 0x46fc60. Marks the object and raises its virtual slot 0x7c.
uint32_t function_46fc60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t sub = run.get(receiver + 0x12c);
    run.put(sub + 0x8, run.get(sub + 0x8) | 4);
    uint32_t owner = run.get(run.get(receiver + 0xc) + 0x74);
    if (run.get(owner + 0xd0) == 0x20) {
        run.put(owner + 0x8, run.get(owner + 0x8) | 0x10000);
    }
    run.vcall(receiver, 0x7c);
    return 1;
}

// 0x46fc90. State change handler.
uint32_t function_46fc90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t state = arguments[0];
    run.put(receiver + 0x304, state);
    if (state != 2) {
        run.call(0x43f120, receiver, {state});
        return 0;
    }
    uint32_t count = run.get(receiver + 0x2fc);
    if (count <= 4) {
        run.call(0x4dbd20, receiver + 0x2f4, {4});
        run.vcall(receiver, 0x7c);
        return 0;
    }
    if (count > 0x20) {
        uint32_t pointer = run.get(receiver + 0x300);
        run.put(pointer, run.get(pointer) | 0x10);
        run.vcall(receiver, 0x7c);
        return 0;
    }
    run.put(receiver + 0x300, run.get(receiver + 0x300) | 0x10);
    run.vcall(receiver, 0x7c);
    return 0;
}

// 0x404f30. Scalar deleting destructor.
uint32_t function_404f30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t self = receiver;
    destroyBody(run, self);
    if ((arguments[0] & 1) != 0) {
        run.call(0x4f6428, 0, {self});
    }
    return self;
}

// 0x404f50. Destructor.
uint32_t function_404f50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    destroyBody(run, receiver);
    return 0;
}

// 0x40f390. Switches the logic's sound to LS_DEAD.
uint32_t function_40f390(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t sound = run.call(0x4dba00, 0x537668, {0x5234f4});
    run.put(run.get(receiver + 0x10) + 0x1c, sound);
    run.put(receiver + 0x20, 1);
    run.put(receiver + 0xc8, 1);
    uint32_t sub = run.get(receiver + 0x12c);
    run.put(sub + 0x48, 0x1e);
    run.put(sub + 0x44, 0);
    sub = run.get(receiver + 0x12c);
    run.put(sub + 0x40, run.get(sub + 0x40) | 8);
    run.put(receiver + 0x19c, 0x3e8);
    run.put(receiver + 0x198, run.get(0x537210));
    return 0;
}

// Shared tail of the two powerup initializers, from the table lookup onward
// (0x471002 / 0x471432). `object` is esi, `state` is ebp.
uint32_t powerupLookup(Run &run, uint32_t object, uint32_t state) {
    uint32_t count = run.get(0x52a190);
    uint32_t key = run.get(object + 0x170);
    uint32_t index = 0;
    bool found = false;
    if (s32(count) > 0) {
        uint32_t cursor = 0x537ec8;
        do {
            if (run.get(cursor) == key) {
                found = true;
                break;
            }
            index = index + 1;
            cursor = cursor + 4;
        } while (s32(index) < s32(count));
    }
    if (found) {
        run.put(object + 0x4, index);
        if (index == 0) {
            run.put(object + 0x4, 0x21);
        }
        run.put(object + 0xfc, run.get(0x537fd0 + index * 4));
        uint32_t owner = run.get(object + 0x6c);
        run.put(owner + 0x168, run.get(0x538310 + index * 4));
        if (run.get(object + 0xd0) == 1) {
            run.put(object + 0xd0, run.get(0x5380d8 + index * 4));
        }
    } else {
        uint32_t owner = run.get(object + 0x6c);
        run.put(object + 0x4, 0);
        run.put(object + 0xfc, 0x64);
        run.put(owner + 0x168, 0);
    }
    uint32_t glitter = 0;
    if (run.get(run.get(0x5371fc) + 0x124) != 0) {
        uint32_t target = run.get(run.get(object + 0xc) + 0x8);
        uint32_t depth = run.get(object + 0x64) + 1;
        glitter = run.call(0x4c8da0, target, {1, run.get(object + 0x4c), run.get(object + 0x50), depth, 0x522950, 0x40000});
    }
    if (glitter != 0) {
        run.put(object + 0xc8, glitter);
        run.put(state + 0x1c, 5);
        return 1;
    }
    run.put(object + 0xc8, 0);
    run.put(state + 0x1c, 5);
    return 1;
}

// Rectangle fields copied from the sprite at +0x174.
void powerupRect(Run &run, uint32_t object, uint32_t sprite) {
    run.put(object + 0x138, run.get(sprite + 0x20) - run.get(sprite + 0x18));
    run.put(object + 0x13c, run.get(sprite + 0x24) - run.get(sprite + 0x1c));
    run.put(object + 0x140, run.get(sprite + 0x20) + run.get(sprite + 0x18) - 1);
    run.put(object + 0x144, run.get(sprite + 0x24) + run.get(sprite + 0x1c) - 1);
}

// Common state 5 and 0x1d handling. Returns true when handled (result 1).
bool powerupOtherStates(Run &run, uint32_t object, uint32_t phase) {
    if (phase == 5) {
        run.call(0x4c82a0, object + 0x188, {run.get(0x5430c4)});
        return true;
    }
    if (phase == 0x1d) {
        uint32_t attached = run.get(object + 0xc8);
        if (attached != 0) {
            run.put(attached + 0x8, run.get(attached + 0x8) | 0x10000);
        }
    }
    return true;
}

// 0x470f00. Magic powerup logic.
uint32_t function_470f00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t state = run.get(object + 0x6c);
    uint32_t phase = run.get(state + 0x1c);
    if (phase != 0) {
        powerupOtherStates(run, object, phase);
        return 1;
    }
    run.put(state + 0x168, 0);
    if (run.get(object + 0x64) == 0) {
        uint32_t flags = run.get(object + 0x8);
        run.put(object + 0x64, 0x3e8);
        run.put(object + 0x8, flags | 0x20000);
    }
    if (run.get(object + 0x190) == 0) {
        run.call(0x4c79e0, object, {0x52a198, 0});
    }
    uint32_t flags = run.get(object + 0x8) | 0x80000;
    uint32_t sprite = run.get(object + 0x174);
    run.put(object + 0x8, flags);
    run.put(object + 0xd0, 0x100000);
    if (sprite != 0) {
        powerupRect(run, object, sprite);
    }
    if (run.get(0x538418) == 0) {
        run.call(0x4719e0, 0, {run.get(object + 0xc)});
    }
    return powerupLookup(run, object, state);
}

// 0x471330. Super powerup logic.
uint32_t function_471330(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t state = run.get(object + 0x6c);
    uint32_t phase = run.get(state + 0x1c);
    if (phase != 0) {
        powerupOtherStates(run, object, phase);
        return 1;
    }
    run.put(state + 0x168, 0);
    if (run.get(object + 0x190) == 0) {
        run.call(0x4c79e0, object, {0x52a198, 0});
    }
    uint32_t flags = run.get(object + 0x8) | 0x80000;
    uint32_t sprite = run.get(object + 0x174);
    run.put(object + 0x8, flags);
    run.put(object + 0xd0, 0x200000);
    if (sprite != 0) {
        powerupRect(run, object, sprite);
    }
    if (run.get(object + 0x64) == 0) {
        run.put(object + 0x64, 0x3e8);
        run.put(object + 0x8, flags | 0x20000);
    }
    if (run.get(0x538418) == 0) {
        run.call(0x4719e0, 0, {run.get(object + 0xc)});
    }
    return powerupLookup(run, object, state);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x46f5b0:
        return function_46f5b0(run, receiver, arguments);
    case 0x46f5d0:
        return function_46f5d0(run, receiver, arguments);
    case 0x46fbe0:
        return function_46fbe0(run, receiver, arguments);
    case 0x46fc60:
        return function_46fc60(run, receiver, arguments);
    case 0x46fc90:
        return function_46fc90(run, receiver, arguments);
    case 0x404f30:
        return function_404f30(run, receiver, arguments);
    case 0x404f50:
        return function_404f50(run, receiver, arguments);
    case 0x40f390:
        return function_40f390(run, receiver, arguments);
    case 0x470f00:
        return function_470f00(run, receiver, arguments);
    case 0x471330:
        return function_471330(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_closure_breakables_powerups_01_entry, owned, body)
