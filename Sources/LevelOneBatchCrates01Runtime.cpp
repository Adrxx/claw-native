// Level 1 stacked crates, crate hits and powder keg states
//
// Recovered from the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x48d620:
        return 1;
    case 0x4717e0:
        return 1;
    case 0x40f450:
        return 7;
    case 0x40f540:
        return 4;
    case 0x4735b0:
        return 5;
    case 0x473610:
        return 1;
    case 0x46fa90:
        return 0;
    case 0x46fc20:
        return 0;
    case 0x40f400:
        return 0;
    default:
        return -1;
    }
}

// Globals: 0x52a190 goodie table size, 0x537ec8 goodie table (pointers),
// 0x538418 table-ready flag, 0x53721c random-spray flag, 0x5430c4 argument of
// the animation tick (0x4c82a0), 0x537210 clock, 0x532c0c / 0x532c10 sound
// enable flag and sound argument.

// 0x473610. cdecl, 1 stack argument. Goodie table lookup by index.
uint32_t lookupGoodie(Run &run, uint32_t index) {
    uint32_t size = run.get(0x52a190);
    if (s32(index) >= s32(size))
        return 0;
    if (s32(index) < 0)
        return 0;
    return run.get(0x537ec8 + index * 4);
}

// 0x40f450. cdecl, 7 stack arguments. Creates a bouncing goodie actor.
// Actor fields: +0x6c logic, +0x16c/+0x170/+0x174 animation cursor, list and
// current frame; logic +0x18 physics state.
uint32_t createGoodie(Run &run, uint32_t owner, uint32_t index, uint32_t a3, uint32_t a4, uint32_t a5, uint32_t vx, uint32_t vy) {
    uint32_t manager = run.get(owner + 0x8);
    uint32_t actor = run.call(0x4c8da0, manager, {1, a3, a4, a5, 0x522cc0, 0x40000});
    if (actor == 0)
        return 0;
    uint32_t list = lookupGoodie(run, index);
    if (list != 0) {
        uint32_t first = run.get(list + 0x64);
        run.put(actor + 0x170, list);
        uint32_t frame = run.call(0x40f680, list, {first});
        run.put(actor + 0x174, frame);
        run.put(actor + 0x16c, first);
    }
    uint32_t logic = run.get(actor + 0x6c);
    uint32_t method = run.get(logic + 0x10);
    run.call(method, 0, {actor});
    uint32_t physics;
    if (run.get(0x53721c) == 0) {
        physics = run.get(run.get(actor + 0x6c) + 0x18);
        run.putd(physics + 0x50, double(s32(vx)));
        run.putd(physics + 0x58, double(s32(vy)));
    } else {
        uint32_t random = run.call(0x4a3050, 0);
        physics = run.get(run.get(actor + 0x6c) + 0x18);
        run.putd(physics + 0x50, double(s32(vx)));
        int32_t lift = -(s32(random) % 0x3e9 + 0x1f4);
        run.putd(physics + 0x58, double(lift));
    }
    run.put(physics + 0x60, 0);
    run.put(physics + 0x64, 0);
    physics = run.get(run.get(actor + 0x6c) + 0x18);
    run.put(physics + 0x40, 0);
    run.put(physics + 0x44, 0x40890000);
    physics = run.get(run.get(actor + 0x6c) + 0x18);
    run.put(physics + 0x184, index);
    return actor;
}

// 0x40f540. cdecl, 4 stack arguments. Sprays the goodies a crate holds.
void sprayGoodies(Run &run, uint32_t crate, uint32_t a2, uint32_t a3, uint32_t a4) {
    uint32_t logic = run.get(crate + 0x6c);
    uint32_t slots[9];
    uint32_t count = 0;
    slots[0] = run.get(crate + 0x100);
    if (slots[0] != 0)
        count = 1;
    slots[1] = run.get(logic + 0xf0);
    if (slots[1] != 0)
        count = count + 1;
    slots[2] = run.get(logic + 0xf8);
    if (slots[2] != 0)
        count = count + 1;
    slots[3] = run.get(logic + 0xf4);
    if (slots[3] != 0)
        count = count + 1;
    slots[4] = run.get(logic + 0xfc);
    if (slots[4] != 0)
        count = count + 1;
    slots[5] = run.get(logic + 0x100);
    if (slots[5] != 0)
        count = count + 1;
    slots[6] = run.get(logic + 0x108);
    if (slots[6] != 0)
        count = count + 1;
    slots[7] = run.get(logic + 0x104);
    if (slots[7] != 0)
        count = count + 1;
    slots[8] = run.get(logic + 0x10c);
    if (slots[8] != 0)
        count = count + 1;
    uint32_t x = uint32_t(s32(count * 0xffffffe7u) / 2);
    for (int i = 0; i < 9; ++i) {
        uint32_t index = slots[i];
        if (s32(index) <= 0)
            continue;
        if (s32(index) >= s32(run.get(0x52a190)))
            continue;
        if (run.get(0x537ec8 + index * 4) == 0)
            continue;
        uint32_t random = run.call(0x4a3050, 0);
        uint32_t owner = run.get(crate + 0xc);
        uint32_t vy = uint32_t(-(s32(random) % 0x12d + 200));
        createGoodie(run, owner, index, a2, a3, a4, x, vy);
        x = x + 0x19;
    }
}

// 0x4735b0. cdecl, 5 stack arguments. Creates a goodie by index with default
// velocity, after making sure the table is ready.
uint32_t createGoodieChecked(Run &run, uint32_t owner, uint32_t a2, uint32_t a3, uint32_t a4, uint32_t index) {
    if (run.get(0x538418) == 0)
        run.call(0x4719e0, 0, {owner});
    if (s32(index) < 0)
        index = 0;
    if (s32(index) >= s32(run.get(0x52a190)))
        return 0;
    if (run.get(0x537ec8 + index * 4) == 0)
        return 0;
    return createGoodie(run, owner, index, a2, a3, a4, 0, 0xfffffed4u);
}

// Reads the animation list entry for a cursor, or 0 outside the list bounds.
uint32_t listEntry(Run &run, uint32_t list, uint32_t cursor) {
    if (s32(cursor) < s32(run.get(list + 0x64)))
        return 0;
    if (s32(cursor) > s32(run.get(list + 0x68)))
        return 0;
    uint32_t items = run.get(list + 0x14);
    return run.get(items + cursor * 4);
}

// 0x4717e0. cdecl, 1 stack argument. A crate is hit.
// Crate fields: +0x6c logic, +0x74 attacker, +0x10c hit points, +0x16c..0x174
// animation cursor; logic +0x130 hit cooldown, +0x1c state.
uint32_t crateHit(Run &run, uint32_t crate) {
    uint32_t attacker = run.get(crate + 0x74);
    uint32_t logic = run.get(crate + 0x6c);
    if (run.get(attacker + 0xd0) == 0x20)
        run.put(attacker + 0x8, run.get(attacker + 0x8) | 0x10000);
    if (run.get(logic + 0x130) != 0)
        return 1;
    uint32_t hits = run.get(crate + 0x10c) - 1;
    run.put(crate + 0x10c, hits);
    if (s32(hits) > 0) {
        uint32_t world = run.get(crate + 0xc);
        uint32_t found = run.get(world + 0x28);
        if (run.get(found + 0x30) == 0) {
            uint32_t local = run.automatic(4);
            run.put(local, 0);
            run.call(0x4f6286, found + 0x10, {0x52a228, local});
            uint32_t entry = run.get(local);
            if (entry != 0) {
                uint32_t enabled = run.get(0x532c0c);
                uint32_t argument = run.get(0x532c10);
                if (enabled != 0)
                    run.call(0x4b45f0, run.get(entry + 0x10), {argument, 0, 0, 0});
            }
        }
        uint32_t list = run.get(crate + 0x170);
        if (list != 0) {
            uint32_t cursor = run.get(crate + 0x16c) + 1;
            run.put(crate + 0x16c, cursor);
            uint32_t frame = listEntry(run, list, cursor);
            run.put(crate + 0x174, frame);
            if (frame == 0) {
                uint32_t wrap = run.get(list + 0x64);
                run.put(crate + 0x16c, wrap);
                uint32_t wrapped = listEntry(run, list, wrap);
                run.put(crate + 0x174, wrapped);
            }
        }
        run.put(logic + 0x130, 0x1f4);
        return 1;
    }
    run.call(0x4c79e0, crate, {0x5266b8, 0});
    run.put(crate + 0x8, run.get(crate + 0x8) | 4);
    uint32_t mode = run.get(logic + 0x64);
    run.put(logic + 0x1c, 0x1f);
    uint32_t y;
    if (mode != 0)
        y = run.get(crate + 0x64) - 1;
    else
        y = run.get(logic + 0x54) + run.get(crate + 0x64);
    uint32_t x = run.get(crate + 0x4c);
    uint32_t top = run.get(crate + 0x50) - 0x18;
    if (mode != 0)
        createGoodieChecked(run, run.get(crate + 0xc), x, top, y, run.get(crate + 0x100));
    else
        sprayGoodies(run, crate, x, top, y);
    uint32_t random = run.call(0x4a3050, 0);
    uint32_t remainder = uint32_t(s32(random) % 100);
    uint32_t world = run.get(logic + 0xc);
    uint32_t found = run.get(world + 0x28);
    uint32_t sounds = run.get(found + 0x30);
    uint32_t name = 0x526730;
    if (s32(remainder) >= 0x32)
        name = 0x52671c;
    if (sounds != 0)
        return 1;
    uint32_t local = run.automatic(4);
    run.put(local, 0);
    run.call(0x4f6286, found + 0x10, {name, local});
    uint32_t entry = run.get(local);
    if (entry == 0)
        return 1;
    uint32_t enabled = run.get(0x532c0c);
    uint32_t argument = run.get(0x532c10);
    if (enabled == 0)
        return 1;
    run.call(0x4b45f0, run.get(entry + 0x10), {argument, 0, 0, 0});
    return 1;
}

// 0x48d620. cdecl, 1 stack argument. Drives the crate-stack logic state machine.
uint32_t logicSpawn(Run &run, uint32_t owner) {
    uint32_t logic = run.get(owner + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (state > 0x1d) {
        if (state == 0x1e) {
            uint32_t object = run.get(logic + 0x18);
            run.vcall(object, 0x1c);
            return 1;
        }
        if (state == 0x3e8)
            return 1;
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
        return 1;
    }
    if (state == 0x1d) {
        uint32_t object = run.get(logic + 0x18);
        run.vcall(object, 0x20);
        return 1;
    }
    if (state != 0) {
        run.call(0x4dc870, 0, {run.get(logic + 0x18)});
        return 1;
    }
    run.put(logic + 0x1c, 0x3e8);
    uint32_t object = run.call(0x4f63ec, 0, {0x4c});
    if (object != 0) {
        run.call(0x48d6e0, object, {owner, 0x3e8});
        run.put(object, 0x50f84c);
    } else {
        object = 0;
    }
    run.vcall(object, 0x10);
    run.put(logic + 0x18, object);
    return 1;
}

// 0x46fa90. thiscall. Hit tick.
uint32_t hitUpdate(Run &run, uint32_t self) {
    uint32_t actor = run.get(self + 0x12c);
    run.put(actor + 0x8, run.get(actor + 0x8) | 0x80);
    uint32_t argument = run.get(0x5430c4);
    uint32_t result = run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {argument});
    if (result == 1 && run.get(self + 0x1a0) == 0) {
        run.put(self + 0x1a0, 1);
        run.call(0x486e70, 0, {500});
        uint32_t holder = run.get(self + 0x12c);
        uint32_t frame = run.get(holder + 0x174);
        if (frame != 0) {
            run.put(self + 0x220, run.get(frame + 0x20) - run.get(frame + 0x18));
            frame = run.get(holder + 0x174);
            run.put(self + 0x224, run.get(frame + 0x24) - run.get(frame + 0x1c));
            frame = run.get(holder + 0x174);
            run.put(self + 0x228, run.get(frame + 0x20) + run.get(frame + 0x18) - 1);
            frame = run.get(holder + 0x174);
            run.put(self + 0x22c, run.get(frame + 0x24) + run.get(frame + 0x1c) - 1);
        }
        uint32_t rect = run.get(self + 0xc) + 0x138;
        run.put(rect, run.get(self + 0x220));
        run.put(rect + 0x4, run.get(self + 0x224));
        run.put(rect + 0x8, run.get(self + 0x228));
        run.put(rect + 0xc, run.get(self + 0x22c));
        uint32_t flags = run.get(self + 0x12c);
        if ((run.get8(flags + 0x40) & 2) != 0) {
            uint32_t world = run.get(self + 0xc);
            uint32_t right = run.get(world + 0x140);
            uint32_t left = run.get(world + 0x138);
            run.put(world + 0x138, 0u - right);
            world = run.get(self + 0xc);
            run.put(world + 0x140, 0u - left);
        }
        actor = run.get(self + 0x12c);
        run.put(actor + 0x8, run.get(actor + 0x8) & 0xffffff7fu);
    }
    uint32_t last = run.get(self + 0x12c);
    if (run.get(last + 0x1a4) != 0) {
        if (run.get(last + 0x19c) == 0)
            run.put(last + 0x8, run.get(last + 0x8) | 0x10000);
    }
    return 0;
}

// 0x46fc20. thiscall. Tick, then call the virtual handler at +0x7c when the
// world state is 1.
uint32_t hitTick(Run &run, uint32_t self) {
    uint32_t argument = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {argument});
    uint32_t world = run.get(self + 0xc);
    if (run.get(world + 0xcc) == 1)
        run.vcall(self, 0x7c);
    return 0;
}

// 0x40f400. thiscall. Tick, then mark the actor when its lifetime elapsed.
uint32_t bounceTick(Run &run, uint32_t self) {
    uint32_t argument = run.get(0x5430c4);
    run.call(0x4c82a0, run.get(self + 0x12c) + 0x188, {argument});
    uint32_t clock = run.get(0x537210);
    uint32_t born = run.get(self + 0x198);
    uint32_t life = run.get(self + 0x19c);
    if (clock - born >= life) {
        uint32_t actor = run.get(self + 0x12c);
        run.put(actor + 0x8, run.get(actor + 0x8) | 0x10000);
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x48d620:
        return logicSpawn(run, arguments[0]);
    case 0x4717e0:
        return crateHit(run, arguments[0]);
    case 0x40f450:
        return createGoodie(run, arguments[0], arguments[1], arguments[2], arguments[3], arguments[4], arguments[5], arguments[6]);
    case 0x40f540:
        sprayGoodies(run, arguments[0], arguments[1], arguments[2], arguments[3]);
        return 0;
    case 0x4735b0:
        return createGoodieChecked(run, arguments[0], arguments[1], arguments[2], arguments[3], arguments[4]);
    case 0x473610:
        return lookupGoodie(run, arguments[0]);
    case 0x46fa90:
        return hitUpdate(run, receiver);
    case 0x46fc20:
        return hitTick(run, receiver);
    case 0x40f400:
        return bounceTick(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_crates_01_entry, owned, body)
