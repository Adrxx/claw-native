// Level 1 loot and breakables, batch 2
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
    case 0x434170:
        return 0;
    case 0x434180:
        return 0;
    case 0x46f1e0:
        return 1;
    case 0x46f2a0:
        return 1;
    case 0x46f6a0:
        return 1;
    case 0x471530:
        return 1;
    case 0x471720:
        return 1;
    case 0x471750:
        return 1;
    case 0x48d560:
        return 1;
    case 0x48d6e0:
        return 2;
    case 0x48de40:
        return 1;
    default:
        return -1;
    }
}

uint32_t function_46f2a0(Run &run, uint32_t self, uint32_t world);
uint32_t function_48d6e0(Run &run, uint32_t self, uint32_t actor, uint32_t hitPoints);
void function_48de40(Run &run, uint32_t self, uint32_t crate);
uint32_t function_471530(Run &run, uint32_t actor);

// 0x434170. Tail jump through the receiver's vtable slot 0xb0.
uint32_t function_434170(Run &run, uint32_t receiver) {
    return run.vcall(receiver, 0xb0, {});
}

// 0x434180. Tail jump through the receiver's vtable slot 0xac.
uint32_t function_434180(Run &run, uint32_t receiver) {
    return run.vcall(receiver, 0xac, {});
}

// 0x46f1e0. Creator of the keg logic. Actor +0x6c is its state block; state
// +0x1c is the phase, +0x18 the logic object.
uint32_t function_46f1e0(Run &run, uint32_t actor) {
    uint32_t state = run.get(actor + 0x6c);
    uint32_t phase = run.get(state + 0x1c);
    if (phase > 0x1d) {
        if (phase == 0x1e) {
            uint32_t logic = run.get(state + 0x18);
            run.vcall(logic, 0x1c, {});
            return 1;
        }
        if (phase == 0x3e8)
            return 1;
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
        return 1;
    }
    if (phase == 0x1d) {
        uint32_t logic = run.get(state + 0x18);
        run.vcall(logic, 0x20, {});
        return 1;
    }
    if (phase != 0) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
        return 1;
    }
    run.put(state + 0x1c, 0x3e8);
    uint32_t block = run.call(0x4f63ec, 0, {0x410});
    uint32_t logic = 0;
    if (block)
        logic = function_46f2a0(run, block, actor);
    run.vcall(logic, 0x10, {});
    run.put(state + 0x18, logic);
    return 1;
}

// 0x46f2a0. Keg logic constructor. self +0x12c is the actor, +0xc the world
// pointer of the base, +0x128 an actor pointer used for name lookups.
uint32_t function_46f2a0(Run &run, uint32_t self, uint32_t world) {
    run.call(0x4332f0, self, {world});
    run.put(self + 0x400, 0);
    run.put(self + 0x404, 0);
    run.put(self, 0x50edd4);
    run.put(self + 0x2d0, 0x14);
    run.call(0x4c7970, run.get(self + 0x12c), {0x52a174});
    uint32_t lookup = self + 0x128;
    uint32_t found = run.call(0x4062e0, lookup, {0x52a15c});
    if (found == 0)
        found = run.call(0x4062e0, lookup, {0x5234b4});
    run.put(self + 0x378, found);
    found = run.call(0x4062e0, lookup, {0x52a144});
    if (found == 0)
        found = run.call(0x4062e0, lookup, {0x5234b4});
    run.put(self + 0x37c, found);
    found = run.call(0x4062e0, lookup, {0x52a12c});
    if (found == 0)
        found = run.call(0x4062e0, lookup, {0x5234b4});
    run.put(self + 0x380, found);
    found = run.call(0x4062e0, lookup, {0x52a12c});
    if (found == 0)
        found = run.call(0x4062e0, lookup, {0x5234b4});
    run.put(self + 0x36c, found);
    found = run.call(0x4062e0, lookup, {0x52a114});
    if (found == 0)
        found = run.call(0x4062e0, lookup, {0x5234b4});
    run.put(self + 0x368, found);
    uint32_t registry = run.get(run.get(self + 0x12c) + 0xc);
    run.put(self + 0x3b8, run.call(0x4061b0, run.get(registry + 0x28), {0x52a104}));
    run.put(self + 0x408, 0);
    run.put(self + 0x2b4, 0xa);
    run.put(self + 0x2b8, 0xfffffff6);
    run.put(self + 0x2bc, 0xffffff97);
    run.put(self + 0x2c0, 0xffffffe2);
    run.put(self + 0x2c4, 0x1e);
    run.put(self + 0x2c8, 0xffffffba);
    run.call(0x4209d0, run.get(self + 0x12c), {9});
    uint32_t setRect = run.get(0x546d5c);
    run.call(setRect, 0, {self + 0x220, 0xffffffd6, 0xfffffff1, 0x2d, 0x3c});
    run.call(setRect, 0, {self + 0x210, 0x80000000, 0xffffffec, 0x14, 0x14});
    run.call(0x4209d0, run.get(self + 0x12c), {1});
    uint32_t rect = self + 0x250;
    run.call(setRect, 0, {rect, 0xffffffec, 0x17, 0x13, 0x3c});
    run.call(setRect, 0, {self + 0x260, 0xffffffe8, 0x19, 0x18, 0x40});
    uint32_t right = run.get(rect + 0xc);
    uint32_t bottom = run.get(rect + 0x8);
    uint32_t top = run.get(rect + 0x4);
    uint32_t left = run.get(rect);
    run.call(0x40f6c0, run.get(self + 0x12c), {left, top, bottom, right});
    run.call(0x406240, run.get(self + 0x12c), {});
    uint32_t base = run.get(self + 0xc);
    run.put(base + 0x104, 0x14);
    uint32_t scaled = run.get(self + 0xc);
    // fild, fmul by the float at 0x5262b0, then __ftol (truncate to 64 bits).
    double product = double(run.gets(scaled + 0x104)) * double(run.getf(0x5262b0));
    int64_t truncated = INT64_MIN;
    if (product > -9223372036854775808.0 && product < 9223372036854775808.0)
        truncated = int64_t(product);
    run.put(scaled + 0x104, uint32_t(truncated));
    uint32_t flags = self + 0x2f4;
    uint32_t size = run.get(flags + 0x8);
    if (size == 0) {
        run.call(0x4dbd20, flags, {0});
    } else {
        uint32_t word = flags + 0xc;
        if (size > 0x20)
            word = run.get(flags + 0xc);
        run.put(word, run.get(word) | 1);
    }
    uint32_t actor = run.get(self + 0x12c);
    run.put(actor + 0x8, run.get(actor + 0x8) | 0x40);
    run.put(self + 0x124, 8);
    actor = run.get(self + 0x12c);
    run.put(actor + 0x164, run.get(actor + 0x164) | 1);
    actor = run.get(self + 0x12c);
    run.put(actor + 0x164, run.get(actor + 0x164) | 4);
    actor = run.get(self + 0x12c);
    run.put(actor + 0xd0, 4);
    actor = run.get(self + 0x12c);
    run.put(actor + 0xd4, 0x1000020);
    actor = run.get(lookup + 0x4);
    run.put(actor + 0x50, run.get(actor + 0x50) + 0xffffffe0);
    uint32_t held = run.get(lookup);
    uint32_t heldWorld = run.get(held + 0xc);
    run.call(0x4cd800, run.get(heldWorld + 0x24), {held, 0});
    uint32_t again = run.get(lookup);
    run.put(again + 0xcc, 1);
    uint32_t info = run.get(self + 0x10);
    run.put(self + 0x24, run.get(info + 0x1c));
    uint32_t idle = run.call(0x4dba00, 0x537668, {0x523148});
    info = run.get(self + 0x10);
    run.put(info + 0x1c, idle);
    return self;
}

// 0x46f6a0. Looks up entry `index` in the table at 0x537ea0 (low bound
// +0x8, high bound +0xc, base +0x10, entry size +0x18) and calls the function
// stored in it with the receiver; a zero entry goes to 0x43d490 instead.
void function_46f6a0(Run &run, uint32_t receiver, uint32_t index) {
    uint32_t low = run.get(0x537ea8);
    run.put(0x537ec0, 0);
    uint32_t entry = 0;
    if (s32(index) < s32(low) || s32(index) > s32(run.get(0x537eac))) {
        uint32_t found = run.call(0x4db6e0, 0x537ea0, {index, 0});
        if (found == 0) {
            uint32_t handler = run.get(0x544b4c);
            uint32_t code = run.call(0x4db5f0, 0, {});
            uint32_t owner = run.get(0x537ea4);
            run.put(0x544b14, code);
            run.call(0x4db4d0, owner, {0x537ea0, handler, 0xc});
            entry = run.get(0x537eb4);
            low = run.get(0x537ea8);
        } else {
            low = run.get(0x537ea8);
            entry = (index - low) * run.get(0x537eb8) + run.get(0x537eb0);
        }
    } else {
        uint32_t base = run.get(0x537eb0);
        entry = (index - low) * run.get(0x537eb8) + base;
    }
    if (run.get(entry) == 0) {
        run.call(0x43d490, receiver, {index});
        return;
    }
    run.put(0x537ec0, 0);
    if (s32(index) < s32(low) || s32(index) > s32(run.get(0x537eac))) {
        uint32_t found = run.call(0x4db6e0, 0x537ea0, {index, 0});
        if (found == 0) {
            uint32_t handler = run.get(0x544b4c);
            uint32_t code = run.call(0x4db5f0, 0, {});
            uint32_t owner = run.get(0x537ea4);
            run.put(0x544b14, code);
            run.call(0x4db4d0, owner, {0x537ea0, handler, 0xc});
            uint32_t slot = run.get(0x537eb4);
            run.call(run.get(slot), receiver, {});
            return;
        }
        low = run.get(0x537ea8);
    }
    uint32_t base = run.get(0x537eb0);
    uint32_t slot = (index - low) * run.get(0x537eb8) + base;
    run.call(run.get(slot), receiver, {});
}

// 0x471530. Crate logic state machine. Actor +0x6c is the state block, state
// +0x1c the phase.
uint32_t function_471530(Run &run, uint32_t actor) {
    uint32_t state = run.get(actor + 0x6c);
    uint32_t phase = run.get(state + 0x1c);
    if (phase == 0) {
        run.put(state + 0x168, 0);
        run.put(state + 0x130, 0);
        uint32_t source = run.get(actor + 0x170);
        if (source) {
            uint32_t id = run.get(source + 0x64);
            run.put(actor + 0x16c, id);
            run.put(actor + 0x174, run.call(0x40f680, source, {id}));
        }
        run.put(actor + 0xd0, 0x200);
        run.put(actor + 0xd4, 0x3000072);
        run.call(0x4c7fa0, actor, {0x5228dc});
        uint32_t image = run.get(actor + 0x174);
        if (image) {
            run.put(actor + 0x128, run.get(image + 0x20) - run.get(image + 0x18));
            run.put(actor + 0x12c, run.get(image + 0x24) - run.get(image + 0x1c));
            run.put(actor + 0x130, run.get(image + 0x20) + run.get(image + 0x18) - 1);
            run.put(actor + 0x134, run.get(image + 0x24) + run.get(image + 0x1c) - 1);
        }
        bool start = run.get(state + 0x10) == 0x471720;
        uint32_t hitPoints = run.get(actor + 0x64);
        bool skip = false;
        if (start) {
            if (hitPoints != 0)
                skip = true;
            else
                run.put(actor + 0x64, 0x1388);
        } else {
            if (hitPoints != 0)
                skip = true;
            else
                run.put(actor + 0x64, 0x44c);
        }
        if (!skip)
            run.put(actor + 0x8, run.get(actor + 0x8) | 0x20000);
        uint32_t counter = run.get(actor + 0x10c);
        if (s32(counter) >= 0x3e7) {
            run.put(actor + 0x8, run.get(actor + 0x8) | 5);
            run.put(state + 0x1c, 5);
            return 1;
        }
        uint32_t next = (s32(counter) > 1 ? 1 : 0) + 1;
        run.put(actor + 0x10c, next);
        run.put(state + 0x1c, 5);
        return 1;
    }
    if (phase == 5) {
        uint32_t timer = run.get(state + 0x130);
        if (timer != 0) {
            uint32_t step = run.get(0x5430c4);
            if (step < timer)
                run.put(state + 0x130, timer - step);
            else
                run.put(state + 0x130, 0);
        }
        run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
        return 1;
    }
    if (phase == 0xa) {
        uint32_t hitPoints = run.get(state + 0x64);
        run.put(state + 0x1c, 5);
        if (hitPoints != 0)
            run.put(actor + 0x8, run.get(actor + 0x8) | 0x10000);
        return 1;
    }
    if (phase == 0x1f) {
        uint32_t animation = actor + 0x188;
        run.call(0x4c82a0, animation, {run.get(0x5430c4)});
        if (run.get(animation + 0x1c) == 0)
            return 1;
        if (run.get(animation + 0x14) != 0)
            return 1;
        run.put(state + 0x1c, 0xa);
        return 1;
    }
    return 1;
}

// 0x471720. Marks the crate for the start variant and runs the state machine.
uint32_t function_471720(Run &run, uint32_t actor) {
    run.put(0x52a194, 5);
    uint32_t state = run.get(actor + 0x6c);
    run.put(state + 0x64, 1);
    return function_471530(run, actor);
}

// 0x471750. The same with the other global value.
uint32_t function_471750(Run &run, uint32_t actor) {
    run.put(0x52a194, 4);
    uint32_t state = run.get(actor + 0x6c);
    run.put(state + 0x64, 1);
    return function_471530(run, actor);
}

// 0x48d560. Creator of the crate logic, like 0x46f1e0 with size 0x4c.
uint32_t function_48d560(Run &run, uint32_t actor) {
    uint32_t state = run.get(actor + 0x6c);
    uint32_t phase = run.get(state + 0x1c);
    if (phase > 0x1d) {
        if (phase == 0x1e) {
            uint32_t logic = run.get(state + 0x18);
            run.vcall(logic, 0x1c, {});
            return 1;
        }
        if (phase == 0x3e8)
            return 1;
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
        return 1;
    }
    if (phase == 0x1d) {
        uint32_t logic = run.get(state + 0x18);
        run.vcall(logic, 0x20, {});
        return 1;
    }
    if (phase != 0) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
        return 1;
    }
    run.put(state + 0x1c, 0x3e8);
    uint32_t block = run.call(0x4f63ec, 0, {0x4c});
    uint32_t logic = 0;
    if (block) {
        function_48d6e0(run, block, actor, 0x1388);
        run.put(block, 0x50f824);
        logic = block;
    }
    run.vcall(logic, 0x10, {});
    run.put(state + 0x18, logic);
    return 1;
}

// One extra crate of 0x48d6e0: the one for the loot slot at info +slot,
// chained after `previous`. Returns the new crate.
uint32_t spawnLinkedCrate(Run &run, uint32_t self, uint32_t slot, uint32_t previous) {
    uint32_t actor = run.get(self + 0x2c);
    uint32_t count = run.get(self + 0x48);
    uint32_t z = run.get(actor + 0x64) + count + 1;
    uint32_t y = run.get(actor + 0x50) - count * 0x28;
    uint32_t x = run.get(actor + 0x4c);
    uint32_t holder = run.get(run.get(run.get(self + 0x30) + 0xc) + 0x8);
    uint32_t crate = run.call(0x4c8da0, holder, {0, x, y, z, 0x522c28, 0x40000});
    uint32_t info = run.get(self + 0x10);
    run.put(crate + 0x100, run.get(info + slot));
    function_48de40(run, self, crate);
    uint32_t crateState = run.get(crate + 0x6c);
    run.call(run.get(crateState + 0x10), 0, {crate});
    crateState = run.get(crate + 0x6c);
    uint32_t previousState = run.get(previous + 0x6c);
    uint32_t logic = run.get(crateState + 0x18);
    run.put(logic + 0x404, run.get(previousState + 0x18));
    crateState = run.get(crate + 0x6c);
    uint32_t number = run.get(self + 0x48);
    logic = run.get(crateState + 0x18);
    run.put(logic + 0x408, number);
    number = run.get(self + 0x48);
    uint32_t owner = run.get(self + 0xc);
    run.put(self + 0x48, number + 1);
    crateState = run.get(crate + 0x6c);
    uint32_t order = run.get(owner + 0x50);
    logic = run.get(crateState + 0x18);
    run.put(logic + 0x40c, order);
    previousState = run.get(previous + 0x6c);
    crateState = run.get(crate + 0x6c);
    logic = run.get(previousState + 0x18);
    run.put(logic + 0x400, run.get(crateState + 0x18));
    return crate;
}

// 0x48d6e0. Crate logic constructor: builds the first crate and one more per
// non-zero loot slot at info +0xf0..+0x10c, chained through logic +0x400.
uint32_t function_48d6e0(Run &run, uint32_t self, uint32_t actor, uint32_t hitPoints) {
    run.put(self, 0x50b064);
    run.put(self + 0x8, actor);
    run.put(self + 0xc, actor);
    run.put(self + 0x10, run.get(actor + 0x6c));
    run.put(self + 0x4, 0);
    run.call(0x4c7fa0, actor, {0x522d54});
    run.call(0x4c8060, run.get(self + 0xc), {0x522d48});
    run.put(self + 0x14, 0);
    run.put(self + 0x18, 0);
    run.put(self + 0x1c, 0x3e9);
    run.put(self + 0x20, 2);
    run.put(self + 0x28, actor);
    run.put(self + 0x2c, actor);
    run.put(self + 0x30, run.get(actor + 0x6c));
    uint32_t owner = run.get(self + 0xc);
    run.put(self, 0x50f874);
    if (run.get(owner + 0x64) == 0) {
        uint32_t current = run.get(owner + 0x64);
        if (current != hitPoints) {
            run.put(owner + 0x64, hitPoints);
            run.put(owner + 0x8, run.get(owner + 0x8) | 0x20000);
        }
    }
    run.put(self + 0x48, 0);
    uint32_t target = run.get(self + 0x2c);
    run.put(target + 0x8, run.get(target + 0x8) | 1);
    target = run.get(self + 0x2c);
    run.put(target + 0x40, run.get(target + 0x40) | 1);
    target = run.get(self + 0x2c);
    uint32_t z = run.get(target + 0x64) + 1;
    uint32_t y = run.get(target + 0x50);
    uint32_t x = run.get(target + 0x4c);
    uint32_t holder = run.get(run.get(run.get(self + 0x30) + 0xc) + 0x8);
    uint32_t last = run.call(0x4c8da0, holder, {0, x, y, z, 0x522c28, 0x40000});
    uint32_t forced = run.get(run.get(self + 0xc) + 0x100);
    if (forced != 0) {
        run.put(last + 0x100, forced);
    } else {
        uint32_t info = run.get(self + 0x10);
        run.put(last + 0x100, run.get(info + 0xf0));
    }
    function_48de40(run, self, last);
    uint32_t lastState = run.get(last + 0x6c);
    run.call(run.get(lastState + 0x10), 0, {last});
    lastState = run.get(last + 0x6c);
    uint32_t logic = run.get(lastState + 0x18);
    run.put(logic + 0x404, 0);
    lastState = run.get(last + 0x6c);
    uint32_t number = run.get(self + 0x48);
    logic = run.get(lastState + 0x18);
    run.put(logic + 0x408, number);
    number = run.get(self + 0x48);
    owner = run.get(self + 0xc);
    run.put(self + 0x48, number + 1);
    lastState = run.get(last + 0x6c);
    uint32_t order = run.get(owner + 0x50);
    logic = run.get(lastState + 0x18);
    run.put(logic + 0x40c, order);
    owner = run.get(self + 0xc);
    uint32_t info = run.get(self + 0x10);
    if (run.get(owner + 0x100) != 0 && run.get(info + 0xf0) != 0)
        last = spawnLinkedCrate(run, self, 0xf0, last);
    info = run.get(self + 0x10);
    if (run.get(info + 0xf4) != 0)
        last = spawnLinkedCrate(run, self, 0xf4, last);
    info = run.get(self + 0x10);
    if (run.get(info + 0xf8) != 0)
        last = spawnLinkedCrate(run, self, 0xf8, last);
    info = run.get(self + 0x10);
    if (run.get(info + 0xfc) != 0)
        last = spawnLinkedCrate(run, self, 0xfc, last);
    info = run.get(self + 0x10);
    if (run.get(info + 0x100) != 0)
        last = spawnLinkedCrate(run, self, 0x100, last);
    info = run.get(self + 0x10);
    if (run.get(info + 0x104) != 0)
        last = spawnLinkedCrate(run, self, 0x104, last);
    info = run.get(self + 0x10);
    if (run.get(info + 0x108) != 0)
        last = spawnLinkedCrate(run, self, 0x108, last);
    info = run.get(self + 0x10);
    if (run.get(info + 0x10c) != 0)
        last = spawnLinkedCrate(run, self, 0x10c, last);
    lastState = run.get(last + 0x6c);
    logic = run.get(lastState + 0x18);
    run.put(logic + 0x400, 0);
    target = run.get(self + 0x2c);
    run.put(target + 0x8, run.get(target + 0x8) | 0x10000);
    return self;
}

// 0x48de40. Copies the owner's position words into a crate that carries
// item 0x20, then clears the loot slots in the crate's state block.
void function_48de40(Run &run, uint32_t self, uint32_t crate) {
    if (run.get(crate + 0x100) == 0x20) {
        uint32_t owner = run.get(self + 0xc);
        uint32_t x = run.get(owner + 0x148);
        run.put(crate + 0x148, x);
        owner = run.get(self + 0xc);
        uint32_t y = run.get(owner + 0x14c);
        run.put(crate + 0xfc, 0x26ae);
        run.put(crate + 0x14c, y);
    }
    uint32_t state = run.get(crate + 0x6c);
    run.put(state + 0xf0, 0);
    state = run.get(crate + 0x6c);
    run.put(state + 0xf4, 0);
    state = run.get(crate + 0x6c);
    run.put(state + 0xf8, 0);
    state = run.get(crate + 0x6c);
    run.put(state + 0xfc, 0);
    state = run.get(crate + 0x6c);
    run.put(state + 0x100, 0);
    state = run.get(crate + 0x6c);
    run.put(state + 0x104, 0);
    state = run.get(crate + 0x6c);
    run.put(state + 0x108, 0);
    state = run.get(crate + 0x6c);
    run.put(state + 0x10c, 0);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x434170:
        return function_434170(run, receiver);
    case 0x434180:
        return function_434180(run, receiver);
    case 0x46f1e0:
        return function_46f1e0(run, arguments[0]);
    case 0x46f2a0:
        return function_46f2a0(run, receiver, arguments[0]);
    case 0x46f6a0:
        function_46f6a0(run, receiver, arguments[0]);
        return 0;
    case 0x471530:
        return function_471530(run, arguments[0]);
    case 0x471720:
        return function_471720(run, arguments[0]);
    case 0x471750:
        return function_471750(run, arguments[0]);
    case 0x48d560:
        return function_48d560(run, arguments[0]);
    case 0x48d6e0:
        return function_48d6e0(run, receiver, arguments[0], arguments[1]);
    case 0x48de40:
        function_48de40(run, receiver, arguments[0]);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_loot_breakables_02_entry, owned, body)
